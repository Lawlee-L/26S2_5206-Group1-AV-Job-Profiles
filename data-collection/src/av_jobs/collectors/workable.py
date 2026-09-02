"""Collect Workable jobs and convert them to the standard format."""

from __future__ import annotations

import re
from typing import Any

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


def workable_location(raw_job: dict[str, Any]) -> str | None:
    """Build a readable location from Workable location fields."""
    locations = raw_job.get("locations")
    if isinstance(locations, list):
        rendered_locations: list[str] = []
        for item in locations:
            if not isinstance(item, dict) or item.get("hidden") is True:
                continue
            parts = [item.get("city"), item.get("region"), item.get("country")]
            location = ", ".join(str(part).strip() for part in parts if part)
            if location and location not in rendered_locations:
                rendered_locations.append(location)
        if rendered_locations:
            return "; ".join(rendered_locations)

    # Some Workable responses only use the main city, state, and country fields.
    parts = [raw_job.get("city"), raw_job.get("state"), raw_job.get("country")]
    location = ", ".join(str(part).strip() for part in parts if part)
    return location or None


def workable_salary(description: str | None) -> str | None:
    """Read a salary sentence when it is written in the job description."""
    if not description:
        return None

    salary_words = ("salary", "pay range", "compensation")
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", description):
        lowered = sentence.lower()
        has_salary_word = any(word in lowered for word in salary_words)
        has_number = bool(re.search(r"[$€£]\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:usd|eur|gbp)", sentence, re.I))
        if has_salary_word and has_number:
            return sentence.strip()
    return None


def normalize_workable_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    """Convert one Workable job to the standard job format."""
    source_job_id_value = raw_job.get("shortcode") or raw_job.get("code")
    source_job_id = str(source_job_id_value) if source_job_id_value else None
    title = raw_job.get("title")
    job_url = raw_job.get("url") or raw_job.get("shortlink") or raw_job.get("application_url")
    location = workable_location(raw_job)
    description = html_to_text(raw_job.get("description"))

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
            job_description=description,
            job_url=job_url,
            location=location,
            salary=workable_salary(description),
            date_posted=raw_job.get("published_on") or raw_job.get("created_at"),
        ),
    )


def collect_workable(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect and standardize all jobs from one Workable source."""
    # Request the full job list. The endpoint uses details=true.
    payload = get_json(source.endpoint)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError(f"{source.source_id}: Workable response has no jobs list")

    collected_at = utc_now_iso()
    jobs = [
        normalize_workable_job(raw_job, source, collected_at)
        for raw_job in payload["jobs"]
        if isinstance(raw_job, dict)
    ]
    return payload, jobs
