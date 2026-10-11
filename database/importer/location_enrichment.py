"""Pure location enrichment and quality counts; no SQL or command-line effects."""

from collections import Counter
from dataclasses import asdict
from typing import Any, Iterable, Mapping

from .location_parser import LOCATION_PARSER_VERSION, parse_location

LOCATION_FIELDS = ("city", "state_region", "country_code", "remote_type")


def location_fields(location_raw: str | None) -> dict[str, str | None]:
    """Derive optional fields without changing the original text or identifiers."""
    fields = asdict(parse_location(location_raw))
    # Do not truncate an inferred locality into a misleading name.
    for field in ("city", "state_region"):
        if fields[field] is not None and len(fields[field]) > 191:
            fields[field] = None
    return fields


def enrich_snapshot_job(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Create a new versioned representation; never mutate an existing snapshot."""
    enriched = dict(payload)
    enriched.update(location_fields(payload.get("location_raw")))
    enriched["location_parser_version"] = LOCATION_PARSER_VERSION
    return enriched


def location_quality(rows: Iterable[Mapping[str, Any]], *, sample_limit: int = 30,
                     parser_version: str | None = LOCATION_PARSER_VERSION,
                     scope: str = "all input rows; includes inactive and non-AV postings, not dashboard totals") -> dict[str, Any]:
    """Describe coverage, not guaranteed geocoding accuracy; null is legitimate."""
    counters = Counter()
    countries = Counter()
    work_modes = Counter()
    unresolved = []
    for row in rows:
        counters["rows"] += 1
        has_raw = bool((row.get("location_raw") or "").strip())
        counters["raw_location_missing"] += not has_raw
        for field in ("city", "state_region", "country_code", "remote_type"):
            counters[field + "_populated"] += bool(row.get(field))
        countries[row.get("country_code") or "unknown"] += 1
        work_modes[row.get("remote_type") or "unknown"] += 1
        if has_raw and not row.get("country_code"):
            counters["unresolved_nonempty_location"] += 1
            if len(unresolved) < sample_limit:
                unresolved.append({"source_key": row.get("source_key"), "location_raw": row.get("location_raw")})
    return {
        "parser_version": parser_version,
        "counts": {name: counters[name] for name in (
            "rows", "raw_location_missing", "city_populated", "state_region_populated",
            "country_code_populated", "remote_type_populated", "unresolved_nonempty_location")},
        "country_counts": dict(sorted(countries.items())),
        "work_mode_counts": dict(sorted(work_modes.items())),
        "unresolved_samples": unresolved,
        "unresolved_sample_limit": sample_limit,
        "scope": scope,
    }
