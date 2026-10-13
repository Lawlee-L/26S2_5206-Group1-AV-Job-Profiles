"""Conservative data-readiness gate for historical dashboard trends."""

from __future__ import annotations

from typing import Any


def trend_readiness_report(connection: Any) -> dict[str, Any]:
    """Require two comparable, verified crawls with matching classification.

    A cumulative export or a publication timestamp is never a crawl point.
    This reports readiness only; it does not invent a time series.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT dr.release_key,dr.status,dr.snapshot_frozen_at,"
            "cr.collection_run_id,cr.run_kind,cr.status AS collection_status,"
            "cr.time_quality,cr.snapshot_generated_at,cr.source_report_available,"
            "ar.collection_run_id AS analysis_collection_run_id,"
            "ar.status AS analysis_status "
            "FROM dashboard_releases dr "
            "JOIN collection_runs cr ON cr.collection_run_id=dr.collection_run_id "
            "JOIN analysis_runs ar ON ar.analysis_run_id=dr.analysis_run_id "
            "WHERE dr.status IN ('published','retired') "
            "ORDER BY cr.snapshot_generated_at,cr.collection_run_id"
        )
        releases = list(cursor.fetchall())
        candidates = []
        for release in releases:
            eligible = (
                release["snapshot_frozen_at"] is not None
                and release["run_kind"] == "verified_crawl"
                and release["collection_status"] == "completed"
                and release["time_quality"] == "exact_utc"
                and release["snapshot_generated_at"] is not None
                and bool(release["source_report_available"])
                and release["analysis_collection_run_id"] == release["collection_run_id"]
                and release["analysis_status"] == "completed"
            )
            if not eligible:
                continue
            cursor.execute(
                "SELECT source_id,status,job_count FROM source_run_results "
                "WHERE collection_run_id=%s ORDER BY source_id",
                (release["collection_run_id"],),
            )
            sources = list(cursor.fetchall())
            if not sources or any(row["status"] != "success" for row in sources):
                continue
            # A zero-result source needs explicit investigation before trends;
            # otherwise a broken endpoint looks like a real disappearance.
            if any(int(row["job_count"]) == 0 for row in sources):
                continue
            candidates.append({
                "release_key": release["release_key"],
                "snapshot_generated_at": str(release["snapshot_generated_at"]),
                "source_ids": tuple(row["source_id"] for row in sources),
            })
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for candidate in candidates:
        groups.setdefault(candidate["source_ids"], []).append(candidate)
    comparable = max(groups.values(), key=len, default=[])
    ready = len(comparable) >= 2
    return {
        "ready": ready,
        "qualifying_release_count": len(candidates),
        "comparable_release_count": len(comparable),
        "comparable_release_keys": [item["release_key"] for item in comparable],
        "source_count": len(comparable[0]["source_ids"]) if comparable else 0,
        "reason": None if ready else (
            "Need at least two frozen releases from completed, exact-time crawls "
            "with matching successful non-empty source sets and linked classification; "
            "cumulative exports do not qualify."
        ),
    }
