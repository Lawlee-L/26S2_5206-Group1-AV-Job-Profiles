"""Read-only location coverage for a draft or an immutable release snapshot."""

import json
from collections import Counter
from typing import Any

from .location_enrichment import enrich_snapshot_job, location_quality


def release_location_report(connection: Any, release: dict[str, Any]) -> dict[str, Any]:
    """Preview current rules for unfrozen drafts; never reinterpret frozen history."""
    frozen = bool(release.get("snapshot_frozen_at"))
    with connection.cursor() as cursor:
        if frozen:
            cursor.execute(
                "SELECT payload_json FROM dashboard_release_snapshot_rows "
                "WHERE dashboard_release_id=%s AND row_kind='job' ORDER BY entity_key",
                (release["dashboard_release_id"],),
            )
            rows = []
            for row in cursor.fetchall():
                payload = row["payload_json"]
                rows.append(json.loads(payload) if isinstance(payload, (str, bytes, bytearray)) else payload)
        else:
            cursor.execute(
                "SELECT source_key,location_raw,is_active FROM v_candidate_dashboard_jobs "
                "WHERE dashboard_release_id=%s ORDER BY job_id",
                (release["dashboard_release_id"],),
            )
            rows = [enrich_snapshot_job(row) for row in cursor.fetchall()]
    versions = Counter(row.get("location_parser_version") or "legacy/unrecorded" for row in rows)
    active = [row for row in rows if row.get("is_active") in (True, 1)]
    recorded_version = next(iter(versions)) if len(versions) == 1 and "legacy/unrecorded" not in versions else None
    return {
        "representation": "frozen snapshot" if frozen else "preview using current parser; not published",
        "parser_versions": dict(sorted(versions.items())),
        "all_av_jobs": location_quality(rows, parser_version=recorded_version,
                                        scope="all non-duplicate AV jobs in this release, including inactive"),
        "active_av_jobs": location_quality(active, parser_version=recorded_version,
                                           scope="active non-duplicate AV jobs in this release"),
    }
