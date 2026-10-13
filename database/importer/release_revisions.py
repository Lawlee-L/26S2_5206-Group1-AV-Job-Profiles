"""Staged release revisions and atomic compare-and-switch selection.

Import and snapshot construction never remove the current release. A short
transaction switches weekly/current pointers together with database evidence.
CLI/GUI callers use the service port; only this adapter knows the SQL.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from .contracts import ReleaseActivation
from .errors import ImportErrorSafe
from .location_parser import LOCATION_PARSER_VERSION
from .publication import _materialize
from .release_metrics import release_qa_report
from .snapshot_integrity import verify_frozen_snapshot


def validate_reason(reason: str, actor: str) -> None:
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 4000:
        raise ImportErrorSafe("Supply a non-empty reason of at most 4000 characters")
    if not isinstance(actor, str) or not actor.strip() or len(actor) > 128:
        raise ImportErrorSafe("Actor must be non-empty and at most 128 characters")


def _release(cursor: Any, key: str, *, lock: bool = False) -> dict[str, Any]:
    cursor.execute(
        "SELECT * FROM dashboard_releases WHERE release_key=%s"
        + (" FOR UPDATE" if lock else ""),
        (key,),
    )
    row = cursor.fetchone()
    if not row:
        raise ImportErrorSafe(f"Unknown release key: {key}")
    return row


def _selection(
    cursor: Any, release: dict[str, Any], *, lock: bool = False
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    suffix = " FOR UPDATE" if lock else ""
    cursor.execute(
        "SELECT * FROM weekly_versions WHERE week_date=%s" + suffix,
        (release["data_cutoff_date"],),
    )
    week = cursor.fetchone()
    if not week or week["collection_run_id"] != release["collection_run_id"]:
        raise ImportErrorSafe(
            "Release is not based on the official collection for its week"
        )
    cursor.execute("SELECT * FROM dashboard_releases WHERE status='published'" + suffix)
    current = cursor.fetchone()
    if week["selected_release_id"] is not None:
        cursor.execute(
            "SELECT release_key FROM dashboard_releases WHERE dashboard_release_id=%s",
            (week["selected_release_id"],),
        )
        selected = cursor.fetchone()
        if not selected:
            raise ImportErrorSafe("Weekly release selection is broken")
        week = {**week, "release_key": selected["release_key"]}
    else:
        week = {**week, "release_key": None}
    return week, current


def check_activation(
    request: ReleaseActivation,
    release: dict[str, Any],
    week: dict[str, Any],
    current: dict[str, Any] | None,
) -> None:
    """Pure guards reused before backup and immediately before the switch."""
    validate_reason(request.reason, request.actor)
    if week["release_key"] != request.expected_week_release:
        raise ImportErrorSafe(
            "Weekly selection changed; expected "
            f"{request.expected_week_release!r}, found {week['release_key']!r}. "
            "Run list-releases and review before retrying"
        )
    current_key = current["release_key"] if current else None
    if current_key != request.expected_current_release:
        raise ImportErrorSafe(
            "Current dashboard changed; expected "
            f"{request.expected_current_release!r}, found {current_key!r}"
        )
    if release["status"] not in {"draft", "retired", "published"}:
        raise ImportErrorSafe("Release has an unsupported lifecycle state")
    if release["status"] != "draft" and not release.get("snapshot_frozen_at"):
        raise ImportErrorSafe(
            "Legacy published/retired release is not frozen; freeze it first"
        )
    if current and not current.get("snapshot_frozen_at"):
        raise ImportErrorSafe(
            "Current legacy release is not frozen; run freeze-release first"
        )
    if (
        request.historical
        and current
        and current["data_cutoff_date"] == release["data_cutoff_date"]
    ):
        raise ImportErrorSafe(
            "This is the current dashboard week; omit --historical so both selections switch together"
        )
    if (
        not request.historical
        and current
        and release["data_cutoff_date"] < current["data_cutoff_date"]
    ):
        raise ImportErrorSafe(
            "An older week must use --historical; do not rewind the current dashboard"
        )


def _contract_hash() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for name in (
        "views.mysql.sql",
        "importer/publication.py",
        "importer/job_details.py",
        "importer/location_parser.py",
        "importer/location_enrichment.py",
    ):
        digest.update(name.encode("utf-8") + b"\0" + (root / name).read_bytes())
    return digest.hexdigest()


def check_frozen_counts(counts: dict[str, int], qa: dict[str, Any]) -> None:
    metrics = qa["metrics"]
    if (
        counts["job"] != metrics["av_postings"]
        or counts["cluster"] != metrics["av_clusters"]
        or counts["skilled_jobs"]
        != metrics["av_postings"] - metrics["av_postings_without_skills"]
    ):
        raise ImportErrorSafe(
            "Frozen job/cluster/skill coverage does not match release QA"
        )


def record_operation(
    engine: Any,
    cursor: Any,
    *,
    action: str,
    release: dict[str, Any],
    week: dict[str, Any],
    current: dict[str, Any] | None,
    next_current_id: int | None,
    reason: str,
    actor: str,
    backup: Path,
    backup_hash: str,
    details: dict[str, Any],
) -> str:
    operation_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO release_operations (operation_id,action,week_date,target_release_id,"
        "previous_week_release_id,previous_current_release_id,next_current_release_id,reason,actor,"
        "backup_file,backup_sha256,details_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            operation_id,
            action,
            release["data_cutoff_date"],
            release["dashboard_release_id"],
            week["selected_release_id"],
            current["dashboard_release_id"] if current else None,
            next_current_id,
            reason.strip(),
            actor.strip(),
            str(backup),
            backup_hash,
            engine.stable_json(details),
        ),
    )
    return operation_id


def create_release(
    engine: Any, source_key: str, reason: str, actor: str, backup_dir: Path
) -> dict[str, Any]:
    """Create a new draft from existing analysis; never copy an old snapshot."""
    validate_reason(reason, actor)
    connection = engine.db_connect()
    try:
        engine.acquire_import_lock(connection)
        engine.verify_schema(connection)
        with connection.cursor() as cursor:
            source = _release(cursor, source_key)
            week, current = _selection(cursor, source)
            if not source["snapshot_frozen_at"] or source["status"] not in {
                "published",
                "retired",
            }:
                raise ImportErrorSafe(
                    "create-release requires a previously frozen published/historical release"
                )
        verify_frozen_snapshot(engine, connection, source)
        connection.rollback()  # Close the read transaction before the external backup.
        backup = engine.backup_database(backup_dir)
        backup_hash = engine.sha256_file(backup)
        key = f"revision-{source['data_cutoff_date']:%Y%m%d}-{uuid.uuid4().hex[:16]}"
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO dashboard_releases (release_key,collection_run_id,analysis_run_id,"
                "cluster_run_id,data_cutoff_date,parent_release_id,status,notes) "
                "VALUES (%s,%s,%s,%s,%s,%s,'draft',%s)",
                (
                    key,
                    source["collection_run_id"],
                    source["analysis_run_id"],
                    source["cluster_run_id"],
                    source["data_cutoff_date"],
                    source["dashboard_release_id"],
                    reason.strip(),
                ),
            )
            created = _release(cursor, key)
            op = record_operation(
                engine,
                cursor,
                action="create",
                release=created,
                week=week,
                current=current,
                next_current_id=current["dashboard_release_id"] if current else None,
                reason=reason,
                actor=actor,
                backup=backup,
                backup_hash=backup_hash,
                details={
                    "source_release_key": source_key,
                    "snapshot_contract_sha256": _contract_hash(),
                    "location_parser_version": LOCATION_PARSER_VERSION,
                },
            )
        connection.commit()
        return {
            "release_key": key,
            "parent_release_key": source_key,
            "status": "draft",
            "analysis_reused": True,
            "official_selection_changed": False,
            "database_operation_id": op,
            "backup": str(backup),
            "backup_sha256": backup_hash,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        engine.release_import_lock(connection)
        connection.close()


def activate_release(
    engine: Any,
    request: ReleaseActivation,
    backup_dir: Path,
    *,
    first_publication: bool = False,
) -> dict[str, Any]:
    """Prepare invisibly, then atomically switch selected analysis/release and current."""
    validate_reason(request.reason, request.actor)
    connection = engine.db_connect()
    try:
        engine.acquire_import_lock(connection)
        engine.verify_schema(connection)
        with connection.cursor() as cursor:
            release = _release(cursor, request.release_key)
            week, current = _selection(cursor, release)
            check_activation(request, release, week, current)
            if first_publication and (
                release["status"] != "draft"
                or week["selected_release_id"] is not None
                or week["selected_analysis_run_id"] != release["analysis_run_id"]
            ):
                raise ImportErrorSafe(
                    "publish-release is for the first selected analysis only; use activate-release for revisions"
                )
        qa = release_qa_report(connection, request.release_key)
        if qa["status"] != "passed":
            raise ImportErrorSafe("Release failed QA: " + ", ".join(qa["errors"]))
        connection.rollback()
        backup = engine.backup_database(backup_dir)
        backup_hash = engine.sha256_file(backup)
        freeze_operation_id = None
        # Expensive preparation commits as a still-invisible frozen draft.
        # A later stale-selection failure may leave that draft for a safe retry.
        if not release["snapshot_frozen_at"]:
            with connection.cursor() as cursor:
                release = _release(cursor, request.release_key, lock=True)
                _materialize(engine, connection, release["dashboard_release_id"])
                release = _release(cursor, request.release_key)
            counts = verify_frozen_snapshot(engine, connection, release)
            check_frozen_counts(counts, qa)
            with connection.cursor() as cursor:
                freeze_operation_id = record_operation(
                    engine,
                    cursor,
                    action="freeze_candidate",
                    release=release,
                    week=week,
                    current=current,
                    next_current_id=(
                        current["dashboard_release_id"] if current else None
                    ),
                    reason=request.reason,
                    actor=request.actor,
                    backup=backup,
                    backup_hash=backup_hash,
                    details={
                        "snapshot_rows": counts,
                        "snapshot_contract_sha256": _contract_hash(),
                        "location_parser_version": LOCATION_PARSER_VERSION,
                    },
                )
            connection.commit()
        else:
            counts = verify_frozen_snapshot(engine, connection, release)
            check_frozen_counts(counts, qa)
            connection.rollback()

        with connection.cursor() as cursor:
            release = _release(cursor, request.release_key, lock=True)
            week, current = _selection(cursor, release, lock=True)
            check_activation(request, release, week, current)
            if first_publication and (
                release["status"] != "draft"
                or week["selected_release_id"] is not None
                or week["selected_analysis_run_id"] != release["analysis_run_id"]
            ):
                raise ImportErrorSafe(
                    "First-publication selection changed; use an explicitly reviewed activation"
                )
            previous_week_key = week["release_key"]
            previous_current_key = current["release_key"] if current else None
            already_selected = (
                week["selected_release_id"] == release["dashboard_release_id"]
            )
            action = (
                "publish"
                if first_publication
                else ("reactivate" if release["status"] == "retired" else "activate")
            )
            if request.historical:
                next_current_id = current["dashboard_release_id"] if current else None
                if release["status"] == "draft":
                    cursor.execute(
                        "UPDATE dashboard_releases SET status='retired' WHERE dashboard_release_id=%s",
                        (release["dashboard_release_id"],),
                    )
            else:
                next_current_id = release["dashboard_release_id"]
                cursor.execute(
                    "UPDATE dashboard_releases SET status='retired' WHERE status='published' "
                    "AND dashboard_release_id<>%s",
                    (release["dashboard_release_id"],),
                )
                cursor.execute(
                    "UPDATE dashboard_releases SET status='published',"
                    "published_at=COALESCE(published_at,UTC_TIMESTAMP(6)) WHERE dashboard_release_id=%s",
                    (release["dashboard_release_id"],),
                )
            cursor.execute(
                "UPDATE weekly_versions SET selected_analysis_run_id=%s,selected_release_id=%s "
                "WHERE week_date=%s AND collection_run_id=%s",
                (
                    release["analysis_run_id"],
                    release["dashboard_release_id"],
                    release["data_cutoff_date"],
                    release["collection_run_id"],
                ),
            )
            op = record_operation(
                engine,
                cursor,
                action=action,
                release=release,
                week=week,
                current=current,
                next_current_id=next_current_id,
                reason=request.reason,
                actor=request.actor,
                backup=backup,
                backup_hash=backup_hash,
                details={
                    "previous_week_release_key": previous_week_key,
                    "previous_current_release_key": previous_current_key,
                    "target_release_key": request.release_key,
                    "historical": request.historical,
                    "qa_warnings": qa["warnings"],
                    "snapshot_rows": counts,
                },
            )
        connection.commit()
        return {
            "release_key": request.release_key,
            "week_date": str(release["data_cutoff_date"]),
            "previous_week_release_key": previous_week_key,
            "previous_current_release_key": previous_current_key,
            "current_release_key": (
                previous_current_key if request.historical else request.release_key
            ),
            "historical": request.historical,
            "selection_changed": not already_selected,
            "snapshot_rows": counts,
            "qa_status": qa["status"],
            "qa_warnings": qa["warnings"],
            "location_quality": qa["location_quality"],
            "database_operation_id": op,
            "freeze_operation_id": freeze_operation_id,
            "backup": str(backup),
            "backup_sha256": backup_hash,
            "action": action,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        engine.release_import_lock(connection)
        connection.close()


def list_releases(engine: Any, week_date: date | None = None) -> dict[str, Any]:
    connection = engine.db_connect()
    try:
        engine.verify_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT dr.release_key,dr.data_cutoff_date AS week_date,dr.analysis_run_id,"
                "dr.collection_run_id,dr.status,dr.snapshot_frozen_at,dr.snapshot_sha256,"
                "parent.release_key AS parent_release_key,dr.created_at,"
                "COALESCE(wv.selected_release_id=dr.dashboard_release_id,0) AS selected_for_week,"
                "(dr.status='published') AS current_dashboard "
                "FROM dashboard_releases dr LEFT JOIN weekly_versions wv "
                "ON wv.collection_run_id=dr.collection_run_id "
                "LEFT JOIN dashboard_releases parent ON parent.dashboard_release_id=dr.parent_release_id "
                + ("WHERE dr.data_cutoff_date=%s " if week_date else "")
                + "ORDER BY dr.data_cutoff_date,dr.created_at,dr.dashboard_release_id",
                (week_date,) if week_date else (),
            )
            rows = list(cursor.fetchall())
        return {"releases": rows, "count": len(rows)}
    finally:
        connection.close()
