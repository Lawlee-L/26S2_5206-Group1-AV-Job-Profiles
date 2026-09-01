from __future__ import annotations

from datetime import datetime, timezone
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


def timestamp_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return str(value)
    if timestamp > 10_000_000_000:
        timestamp /= 1000
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def format_salary(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    minimum = value.get("min")
    maximum = value.get("max")
    currency = value.get("currency")
    interval = value.get("interval")
    if minimum is None and maximum is None:
        return None
    amount = f"{minimum}-{maximum}" if minimum is not None and maximum is not None else str(minimum or maximum)
    parts = [str(currency or "").strip(), amount]
    salary = " ".join(part for part in parts if part)
    return f"{salary} per {interval}" if interval else salary


def build_description(raw_job: dict[str, Any]) -> str | None:
    """Combine the main text, responsibilities, requirements, and extra text."""
    parts: list[str] = []

    for plain_key, html_key in (
        ("openingPlain", "opening"),
        ("descriptionPlain", "description"),
        ("descriptionBodyPlain", "descriptionBody"),
    ):
        value = raw_job.get(plain_key) or html_to_text(raw_job.get(html_key))
        if value and value.strip() not in parts:
            parts.append(value.strip())

    lists = raw_job.get("lists")
    if isinstance(lists, list):
        for section in lists:
            if not isinstance(section, dict):
                continue
            heading = str(section.get("text") or "").strip()
            content = html_to_text(section.get("content"))
            section_text = "\n".join(part for part in (heading, content) if part)
            if section_text and section_text not in parts:
                parts.append(section_text)

    additional = raw_job.get("additionalPlain") or html_to_text(raw_job.get("additional"))
    if additional and additional.strip() not in parts:
        parts.append(additional.strip())
    return "\n\n".join(parts) or None


def normalize_lever_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    source_job_id = str(raw_job["id"]) if raw_job.get("id") is not None else None
    title = raw_job.get("text") or raw_job.get("title")
    job_url = raw_job.get("hostedUrl") or raw_job.get("applyUrl")
    categories = raw_job.get("categories")
    location = categories.get("location") if isinstance(categories, dict) else None
    description = build_description(raw_job)

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
            salary=format_salary(raw_job.get("salaryRange")),
            date_posted=timestamp_to_iso(raw_job.get("createdAt")),
        ),
    )


def collect_lever(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    payload = get_json(source.endpoint)
    if not isinstance(payload, list):
        raise ValueError(f"{source.source_id}: Lever response is not a job list")
    collected_at = utc_now_iso()
    jobs = [
        normalize_lever_job(raw_job, source, collected_at)
        for raw_job in payload
        if isinstance(raw_job, dict)
    ]
    return payload, jobs
