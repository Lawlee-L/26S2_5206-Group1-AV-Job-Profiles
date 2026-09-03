"""Collect GM autonomous-driving jobs from the public XML feed."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any

from av_jobs.collectors.greenhouse import html_to_text
from av_jobs.config import SourceConfig
from av_jobs.http import get_text
from av_jobs.models import (
    JobData,
    JobMetadata,
    StandardJob,
    build_source_key,
    utc_now_iso,
)


GM_AV_MARKER = "#gm-av-1"
MONEY_AMOUNT = r"\$\s*[\d,]+(?:\.\d{2})?"
SALARY_RANGE = re.compile(
    rf"(?:salary range for this role|expected base compensation for this role)"
    rf"(?:\s*:)?\s*(?:is\s*:?\s*)?(?:\(\s*)?"
    rf"({MONEY_AMOUNT})\s*(?:to|and|[-–—])\s*({MONEY_AMOUNT})",
    re.IGNORECASE,
)


def gm_feed_jobs(feed_xml: str) -> list[dict[str, str | None]]:
    """Read GM AV jobs from the public XML feed."""
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError as exc:
        raise ValueError("GM feed did not return valid XML") from exc

    jobs: list[dict[str, str | None]] = []
    for item in root.findall("job"):
        raw_job = {child.tag: child.text for child in item}
        description = raw_job.get("description") or ""
        if GM_AV_MARKER not in description.casefold():
            continue
        jobs.append(raw_job)
    return jobs


def gm_salary(description: str | None) -> str | None:
    """Read a clear salary range from the public description."""
    text = html_to_text(description)
    if not text:
        return None
    match = SALARY_RANGE.search(" ".join(text.split()))
    if not match:
        return None
    low = re.sub(r"\$\s+", "$", match.group(1))
    high = re.sub(r"\$\s+", "$", match.group(2))
    return f"{low} to {high}"


def gm_location(raw_job: dict[str, str | None]) -> str | None:
    """Combine the public GM location fields."""
    parts: list[str] = []
    for name in ("city", "state", "country"):
        value = (raw_job.get(name) or "").strip()
        if value and value not in parts:
            parts.append(value)
    location = ", ".join(parts)
    remote_type = (raw_job.get("remotetype") or "").strip()
    if remote_type:
        location = f"{location} ({remote_type})" if location else remote_type
    return location or None


def gm_date_posted(value: str | None) -> str | None:
    """Convert a public feed date to an ISO date."""
    if not value or not value.strip():
        return None
    try:
        return parsedate_to_datetime(value.strip()).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return value.strip()


def normalize_gm_job(
    raw_job: dict[str, str | None],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    """Convert one GM feed record to the standard job format."""
    source_job_id = (raw_job.get("requisitionid") or raw_job.get("apijobid") or "").strip() or None
    title = (raw_job.get("title") or "").strip() or None
    job_url = (raw_job.get("url") or "").strip() or None
    description_html = raw_job.get("description")
    location = gm_location(raw_job)

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
            job_description=html_to_text(description_html),
            job_url=job_url,
            location=location,
            salary=gm_salary(description_html),
            date_posted=gm_date_posted(raw_job.get("date")),
        ),
    )


def collect_gm(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect every GM job marked for the AV source."""
    feed_xml = get_text(source.endpoint)
    raw_jobs = gm_feed_jobs(feed_xml)
    if not raw_jobs:
        raise ValueError(f"{source.source_id}: GM feed has no jobs marked {GM_AV_MARKER}")

    collected_at = utc_now_iso()
    jobs = [normalize_gm_job(raw_job, source, collected_at) for raw_job in raw_jobs]
    raw_payload = {
        "feed_url": source.endpoint,
        "selection_marker": GM_AV_MARKER,
        "feed_xml": feed_xml,
        "selected_jobs": raw_jobs,
    }
    return raw_payload, jobs
