"""Collect Comeet jobs and convert them to the standard format."""

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


def endpoint_with_details(endpoint: str) -> str:
    """Set details=true so Comeet returns the full job description."""
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["details"] = "true"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def comeet_location(raw_job: dict[str, Any]) -> str | None:
    """Read the public location name from a Comeet job."""
    location = raw_job.get("location")
    if not isinstance(location, dict):
        return None

    name = location.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()

    parts = [location.get("city"), location.get("state"), location.get("country")]
    rendered = ", ".join(str(part).strip() for part in parts if part)
    return rendered or None


def comeet_description(raw_job: dict[str, Any]) -> str | None:
    """Join all useful Comeet detail sections into one description."""
    details = raw_job.get("details")
    if not isinstance(details, list):
        return None

    sections: list[str] = []
    for item in sorted(
        (item for item in details if isinstance(item, dict)),
        key=lambda item: item.get("order") if isinstance(item.get("order"), int) else 999,
    ):
        value = html_to_text(item.get("value"))
        if not value:
            continue
        name = str(item.get("name") or "").strip()
        sections.append(f"{name}\n{value}" if name else value)
    return "\n\n".join(sections) or None


def normalize_comeet_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    """Convert one Comeet job to the standard job format."""
    source_job_id_value = raw_job.get("uid") or raw_job.get("internal_use_custom_id")
    source_job_id = str(source_job_id_value) if source_job_id_value else None
    title = raw_job.get("name")
    job_url = (
        raw_job.get("url_active_page")
        or raw_job.get("url_comeet_hosted_page")
        or raw_job.get("url_recruit_hosted_page")
    )
    location = comeet_location(raw_job)

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
            job_description=comeet_description(raw_job),
            job_url=job_url,
            location=location,
            salary=None,
            # Comeet provides an updated time, but not a published date.
            date_posted=None,
        ),
    )


def collect_comeet(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect and standardize all jobs from one Comeet source."""
    payload = get_json(endpoint_with_details(source.endpoint))
    if not isinstance(payload, list):
        raise ValueError(f"{source.source_id}: Comeet response is not a jobs list")

    collected_at = utc_now_iso()
    jobs = [
        normalize_comeet_job(raw_job, source, collected_at)
        for raw_job in payload
        if isinstance(raw_job, dict)
    ]
    return payload, jobs
