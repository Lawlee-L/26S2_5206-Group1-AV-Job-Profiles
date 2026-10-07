"""Transactional, immutable snapshots for dashboard publication.

Candidate views are build inputs; public views read only snapshot rows. This
module accepts the database engine as an argument so CLI/GUI adapters can use
the same application operation without importing MySQL themselves.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .errors import ImportErrorSafe
from .job_details import job_detail_payload
from .location_enrichment import enrich_snapshot_job
from .release_metrics import release_qa_report


_KINDS = (
    ("job", "v_candidate_dashboard_jobs", ("job_id",)),
    ("job_skill", "v_candidate_dashboard_job_skills", ("job_id", "skill_id")),
    ("cluster", "v_candidate_dashboard_clusters", ("cluster_pk",)),
)


def _materialize(engine: Any, connection: Any, release_id: int) -> dict[str, int]:
    totals: dict[str, int] = {}
    digest = hashlib.sha256()
    with connection.cursor() as reader, connection.cursor() as writer:
        writer.execute(
            "SELECT COUNT(*) AS n FROM dashboard_release_snapshot_rows WHERE dashboard_release_id=%s",
            (release_id,),
        )
        if writer.fetchone()["n"]:
            raise ImportErrorSafe("Release already has snapshot rows; publication never rewrites a frozen release")
        for kind, view, key_fields in _KINDS:
            # View names are constants above, never user input.
            order_by = ",".join(key_fields)
            reader.execute(
                f"SELECT * FROM {view} WHERE dashboard_release_id=%s ORDER BY {order_by}",
                (release_id,),
            )
            count = 0
            batch: list[tuple[Any, ...]] = []
            for row in reader.fetchall():
                payload = {key: value for key, value in row.items()
                           if key not in {"dashboard_release_id", "release_key"}}
                if kind == "job":
                    payload = job_detail_payload(payload)
                    payload = enrich_snapshot_job(payload)
                key = ":".join(str(payload[field]) for field in key_fields)
                encoded = engine.stable_json(payload)
                row_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
                digest.update(f"{kind}:{key}:{row_hash}\n".encode("utf-8"))
                batch.append((release_id, kind, key, encoded, row_hash))
                count += 1
                if len(batch) >= 500:
                    writer.executemany(
                        "INSERT INTO dashboard_release_snapshot_rows "
                        "(dashboard_release_id,row_kind,entity_key,payload_json,row_sha256) "
                        "VALUES (%s,%s,%s,%s,%s)", batch)
                    batch.clear()
            if batch:
                writer.executemany(
                    "INSERT INTO dashboard_release_snapshot_rows "
                    "(dashboard_release_id,row_kind,entity_key,payload_json,row_sha256) "
                    "VALUES (%s,%s,%s,%s,%s)", batch)
            totals[kind] = count
        if not totals["job"]:
            raise ImportErrorSafe("Refusing to freeze an empty AV dashboard release")
        writer.execute(
            "UPDATE dashboard_releases SET snapshot_frozen_at=UTC_TIMESTAMP(6),snapshot_sha256=%s "
            "WHERE dashboard_release_id=%s AND snapshot_frozen_at IS NULL",
            (digest.hexdigest(), release_id),
        )
        if writer.rowcount != 1:
            raise ImportErrorSafe("Release snapshot was already frozen")
    return totals


def publish_release(engine: Any, release_key: str, backup_dir: Path,
                    *, freeze_existing: bool = False, historical: bool = False) -> dict[str, Any]:
    """Compatibility entry point: first publication or explicit legacy freezing.

    Same-week revisions must use the compare-and-switch activation request.
    Imports are local to avoid coupling snapshot construction to lifecycle SQL.
    """
    from .contracts import ReleaseActivation
    from .release_revisions import activate_release, record_operation
    from .snapshot_integrity import verify_frozen_snapshot

    if freeze_existing and historical:
        raise ImportErrorSafe("An existing published release cannot be frozen as a historical draft")
    if not freeze_existing:
        read = engine.db_connect()
        try:
            engine.verify_schema(read)
            with read.cursor() as cursor:
                cursor.execute("SELECT release_key FROM dashboard_releases WHERE status='published'")
                current = cursor.fetchone()
        finally:
            read.close()
        return activate_release(engine, ReleaseActivation(
            release_key=release_key,expected_week_release=None,
            expected_current_release=current["release_key"] if current else None,
            reason="First publication after QA",actor="publish-release",historical=historical),
            backup_dir,first_publication=True)

    connection = engine.db_connect()
    try:
        engine.acquire_import_lock(connection)
        engine.verify_schema(connection)
        backup = engine.backup_database(backup_dir)
        backup_hash = engine.sha256_file(backup)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * "
                "FROM dashboard_releases WHERE release_key=%s FOR UPDATE", (release_key,))
            release = cursor.fetchone()
            if not release:
                raise ImportErrorSafe(f"Unknown release key: {release_key}")
            if release["status"] != "published":
                raise ImportErrorSafe("freeze-release only handles a currently published legacy release")
            if release["snapshot_frozen_at"] is not None:
                raise ImportErrorSafe("Release is already frozen; refusing to change its snapshot")
            cursor.execute("SELECT * FROM weekly_versions WHERE week_date=%s FOR UPDATE",
                           (release["data_cutoff_date"],))
            week = cursor.fetchone()
            if not week or week["collection_run_id"] != release["collection_run_id"] or \
                    week["selected_analysis_run_id"] != release["analysis_run_id"] or \
                    week["selected_release_id"] not in (None, release["dashboard_release_id"]):
                raise ImportErrorSafe("Legacy release does not match the official weekly selection")
            release_id = int(release["dashboard_release_id"])
            _materialize(engine, connection, release_id)
            cursor.execute("UPDATE weekly_versions SET selected_release_id=%s WHERE week_date=%s",
                           (release_id, release["data_cutoff_date"]))
            final_qa = release_qa_report(connection, release_key)
            if final_qa["status"] != "passed":
                raise ImportErrorSafe("Frozen release failed QA: " + ", ".join(final_qa["errors"]))
            cursor.execute("SELECT * FROM dashboard_releases WHERE dashboard_release_id=%s", (release_id,))
            frozen = cursor.fetchone()
            counts = verify_frozen_snapshot(engine, connection, frozen)
            op = record_operation(engine,cursor,action="freeze_legacy",release=frozen,week=week,
                                  current=release,next_current_id=release_id,reason="Freeze legacy published release",
                                  actor="freeze-release",backup=backup,backup_hash=backup_hash,
                                  details={"snapshot_rows":counts})
        connection.commit()
        return {"release_key": release_key, "snapshot_rows": counts,
                "qa_status": final_qa["status"], "backup": str(backup),
                "backup_sha256": backup_hash,"database_operation_id":op,"action":"freeze_existing"}
    except Exception:
        connection.rollback()
        raise
    finally:
        engine.release_import_lock(connection)
        connection.close()
