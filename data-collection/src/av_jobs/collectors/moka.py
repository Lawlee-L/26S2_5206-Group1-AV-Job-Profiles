"""Collect Moka jobs and convert them to the standard format."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from av_jobs.collectors.greenhouse import html_to_text
from av_jobs.config import SourceConfig
from av_jobs.http import get_json
from av_jobs.models import (
    JobData,
    JobMetadata,
    StandardJob,
    build_source_key,
    utc_now_iso,
)


PAGE_SIZE = 100


def moka_page_url(endpoint: str, *, limit: int, offset: int) -> str:
    """Add Moka pagination values without removing other query values."""
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["limit"] = str(limit)
    query["offset"] = str(offset)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def moka_location(raw_job: dict[str, Any]) -> str | None:
    """Join all public Moka job locations into one readable value."""
    locations = raw_job.get("locations")
    if not isinstance(locations, list):
        return None

    rendered_locations: list[str] = []
    for item in locations:
        if not isinstance(item, dict):
            continue
        parts: list[str] = []
        for key in ("country", "province", "city", "area"):
            value = item.get(key)
            text = str(value).strip() if value else ""
            if text and text not in parts:
                parts.append(text)
        location = ", ".join(parts)
        if location and location not in rendered_locations:
            rendered_locations.append(location)
    return "; ".join(rendered_locations) or None


def moka_job_url(source: SourceConfig, source_job_id: str | None) -> str | None:
    """Build the public Moka job page from the source career URL."""
    if not source_job_id or not source.career_url:
        return None
    return f"{source.career_url.rstrip('/')}#/job/{source_job_id}"


def normalize_moka_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    """Convert one Moka job to the standard job format."""
    source_job_id_value = raw_job.get("id") or raw_job.get("mjCode")
    source_job_id = str(source_job_id_value) if source_job_id_value else None
    title = raw_job.get("title")
    job_url = moka_job_url(source, source_job_id)
    location = moka_location(raw_job)

    return StandardJob(
        metadata=JobMetadata(
            source_id=source.source_id,
            platform=source.platform,
            company=source.company,
            region=source.region,
            source_job_id=source_job_id,
            source_key=build_source_key(
                platform=source.platform,
                company=source.company,
                source_job_id=source_job_id,
                job_url=job_url,
                title=title,
                location=location,
            ),
            collected_at=collected_at,
        ),
        data=JobData(
            advertised_job_title=title,
            job_description=html_to_text(raw_job.get("description")),
            job_url=job_url,
            location=location,
            # Moka returns some salary numbers without a clear public unit.
            salary=None,
            date_posted=raw_job.get("publishedAt") or raw_job.get("openedAt"),
        ),
    )


def collect_moka(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect all Moka pages and standardize every unique job."""
    all_raw_jobs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    offset = 0
    total = 0
    first_payload: dict[str, Any] | None = None

    while True:
        payload = get_json(moka_page_url(source.endpoint, limit=PAGE_SIZE, offset=offset))
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError(f"{source.source_id}: Moka response has no jobs list")
        if first_payload is None:
            first_payload = payload

        page_jobs = [job for job in payload["jobs"] if isinstance(job, dict)]
        for raw_job in page_jobs:
            job_id = str(raw_job.get("id") or raw_job.get("mjCode") or "")
            if job_id and job_id in seen_ids:
                continue
            if job_id:
                seen_ids.add(job_id)
            all_raw_jobs.append(raw_job)

        total_value = payload.get("total")
        total = int(total_value) if isinstance(total_value, (int, float)) else len(all_raw_jobs)
        if not page_jobs or len(all_raw_jobs) >= total:
            break
        offset += PAGE_SIZE

    combined_payload = dict(first_payload or {})
    combined_payload["jobs"] = all_raw_jobs
    combined_payload["total"] = total

    collected_at = utc_now_iso()
    jobs = [normalize_moka_job(raw_job, source, collected_at) for raw_job in all_raw_jobs]
    return combined_payload, jobs
