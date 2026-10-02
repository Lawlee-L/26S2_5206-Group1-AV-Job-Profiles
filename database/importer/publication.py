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
    """Freeze a draft for current or historical display without rewriting old snapshots."""
    if freeze_existing and historical:
        raise ImportErrorSafe("An existing published release cannot be frozen as a historical draft")
    connection = engine.db_connect()
    try:
        engine.acquire_import_lock(connection)
        engine.verify_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT dashboard_release_id,status,snapshot_frozen_at "
                "FROM dashboard_releases WHERE release_key=%s FOR UPDATE", (release_key,))
            release = cursor.fetchone()
            if not release:
                raise ImportErrorSafe(f"Unknown release key: {release_key}")
            expected = "published" if freeze_existing else "draft"
            if release["status"] != expected:
                raise ImportErrorSafe(f"Release must be {expected}, not {release['status']}")
            if release["snapshot_frozen_at"] is not None:
                raise ImportErrorSafe("Release is already frozen; refusing to change its snapshot")
            if not freeze_existing:
                cursor.execute(
                    "SELECT 1 FROM weekly_versions wv JOIN dashboard_releases dr "
                    "ON dr.collection_run_id=wv.collection_run_id "
                    "AND dr.analysis_run_id=wv.selected_analysis_run_id "
                    "WHERE dr.release_key=%s",
                    (release_key,),
                )
                if cursor.fetchone() is None:
                    raise ImportErrorSafe("Release is not the selected classification for an official week")
                qa = release_qa_report(connection, release_key)
                if qa["status"] != "passed":
                    raise ImportErrorSafe("Draft release failed QA: " + ", ".join(qa["errors"]))
                if not historical:
                    cursor.execute("SELECT release_key,snapshot_frozen_at FROM dashboard_releases "
                                   "WHERE status='published' FOR UPDATE")
                    current = cursor.fetchone()
                    if current and current["snapshot_frozen_at"] is None:
                        raise ImportErrorSafe(
                            "Existing published release is not frozen; run freeze-release on it first")
            # The backup is a recovery point, not a substitute for the transaction.
            backup = engine.backup_database(backup_dir)
            backup_hash = engine.sha256_file(backup)
            release_id = int(release["dashboard_release_id"])
            counts = _materialize(engine, connection, release_id)
            if historical:
                cursor.execute("UPDATE dashboard_releases SET status='retired' "
                               "WHERE dashboard_release_id=%s", (release_id,))
            elif not freeze_existing:
                cursor.execute("UPDATE dashboard_releases SET status='retired' WHERE status='published'")
                cursor.execute(
                    "UPDATE dashboard_releases SET status='published',published_at=UTC_TIMESTAMP(6) "
                    "WHERE dashboard_release_id=%s", (release_id,))
            final_qa = release_qa_report(connection, release_key)
            if final_qa["status"] != "passed":
                raise ImportErrorSafe("Frozen release failed QA: " + ", ".join(final_qa["errors"]))
            expected_jobs = int(final_qa["metrics"]["av_postings"])
            if counts["job"] != expected_jobs:
                raise ImportErrorSafe(f"Snapshot has {counts['job']} jobs, QA expects {expected_jobs}")
        connection.commit()
        return {"release_key": release_key, "snapshot_rows": counts,
                "qa_status": final_qa["status"], "backup": str(backup),
                "backup_sha256": backup_hash,
                "action": "freeze_existing" if freeze_existing else (
                    "freeze_historical" if historical else "publish")}
    except Exception:
        connection.rollback()
        raise
    finally:
        engine.release_import_lock(connection)
        connection.close()
