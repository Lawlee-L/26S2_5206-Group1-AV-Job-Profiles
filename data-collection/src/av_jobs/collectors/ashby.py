from __future__ import annotations

import json
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


def ashby_location(raw_job: dict[str, Any]) -> str | None:
    location = raw_job.get("location")
    if isinstance(location, str) and location.strip():
        return location.strip()

    address = raw_job.get("address")
    if not isinstance(address, dict):
        return None
    parts = [
        address.get("locality"),
        address.get("region"),
        address.get("country"),
    ]
    rendered = ", ".join(str(part).strip() for part in parts if part)
    return rendered or None


def ashby_salary(raw_job: dict[str, Any]) -> str | None:
    summary = raw_job.get("compensationTierSummary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    # Keep other public compensation fields when no summary is available.
    for key in ("compensation", "compensationTier", "salary"):
        value = raw_job.get(key)
        if isinstance(value, dict):
            nested_summary = value.get("compensationTierSummary") or value.get("scrapeableCompensationSalarySummary")
            if isinstance(nested_summary, str) and nested_summary.strip():
                return nested_summary.strip()
        if has_real_value(value):
            return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return None


def has_real_value(value: Any) -> bool:
    """Return True when a nested value contains useful text or a number."""
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, dict):
        return any(has_real_value(item) for item in value.values())
    if isinstance(value, list):
        return any(has_real_value(item) for item in value)
    return True


def normalize_ashby_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    source_job_id_value = raw_job.get("id") or raw_job.get("jobPostingId")
    source_job_id = str(source_job_id_value) if source_job_id_value is not None else None
    title = raw_job.get("title")
    job_url = raw_job.get("jobUrl") or raw_job.get("applyUrl")
    location = ashby_location(raw_job)
    description = raw_job.get("descriptionPlain")
    if not description:
        description = html_to_text(raw_job.get("descriptionHtml"))

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
            salary=ashby_salary(raw_job),
            date_posted=raw_job.get("publishedAt"),
        ),
    )


def collect_ashby(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    payload = get_json(source.endpoint)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError(f"{source.source_id}: Ashby response has no jobs list")
    collected_at = utc_now_iso()
    jobs = [
        normalize_ashby_job(raw_job, source, collected_at)
        for raw_job in payload["jobs"]
        if isinstance(raw_job, dict)
    ]
    return payload, jobs
