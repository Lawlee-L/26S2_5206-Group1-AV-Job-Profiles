"""Collect SmartRecruiters jobs and convert them to the standard format."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from av_jobs.collectors.greenhouse import html_to_text
from av_jobs.collectors.workable import workable_salary
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
DETAIL_WORKERS = 8


def smartrecruiters_page_url(endpoint: str, *, limit: int, offset: int) -> str:
    """Add pagination values without removing the country filter."""
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["limit"] = str(limit)
    query["offset"] = str(offset)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def smartrecruiters_location(raw_job: dict[str, Any]) -> str | None:
    """Read the full public location from a SmartRecruiters job."""
    location = raw_job.get("location")
    if not isinstance(location, dict):
        return None

    full_location = location.get("fullLocation")
    if isinstance(full_location, str) and full_location.strip():
        return full_location.strip()

    parts = [location.get("city"), location.get("region"), location.get("country")]
    rendered = ", ".join(str(part).strip() for part in parts if part)
    return rendered or None


def smartrecruiters_description(raw_job: dict[str, Any]) -> str | None:
    """Join the useful job advertisement sections into one description."""
    job_ad = raw_job.get("jobAd")
    sections = job_ad.get("sections") if isinstance(job_ad, dict) else None
    if not isinstance(sections, dict):
        return None

    # Company description is general company text, not the job description.
    section_names = ("jobDescription", "qualifications", "additionalInformation")
    rendered_sections: list[str] = []
    for section_name in section_names:
        section = sections.get(section_name)
        if not isinstance(section, dict):
            continue
        text = html_to_text(section.get("text"))
        if not text:
            continue
        title = str(section.get("title") or "").strip()
        rendered_sections.append(f"{title}\n{text}" if title else text)
    return "\n\n".join(rendered_sections) or None


def normalize_smartrecruiters_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    """Convert one SmartRecruiters job to the standard job format."""
    source_job_id_value = raw_job.get("id") or raw_job.get("uuid")
    source_job_id = str(source_job_id_value) if source_job_id_value else None
    title = raw_job.get("name")
    job_url = raw_job.get("postingUrl") or raw_job.get("applyUrl")
    location = smartrecruiters_location(raw_job)
    description = smartrecruiters_description(raw_job)

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
            date_posted=raw_job.get("releasedDate"),
        ),
    )


def collect_smartrecruiters(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect every list page and full job detail from one source."""
    listings: list[dict[str, Any]] = []
    offset = 0
    total = 0

    # This collector does not filter jobs. Data cleaning is a later step.
    while True:
        payload = get_json(
            smartrecruiters_page_url(source.endpoint, limit=PAGE_SIZE, offset=offset)
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
            raise ValueError(f"{source.source_id}: SmartRecruiters response has no content list")

        page_jobs = [job for job in payload["content"] if isinstance(job, dict)]
        listings.extend(page_jobs)
        total_value = payload.get("totalFound")
        total = int(total_value) if isinstance(total_value, (int, float)) else len(listings)
        if not page_jobs or len(listings) >= total:
            break
        offset += PAGE_SIZE

    detail_urls = [listing.get("ref") for listing in listings]
    if any(not isinstance(url, str) or not url for url in detail_urls):
        raise ValueError(f"{source.source_id}: A SmartRecruiters job has no detail URL")

    # A small worker pool makes large sources faster without changing the data.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        details = list(executor.map(get_json, detail_urls))
    if any(not isinstance(detail, dict) for detail in details):
        raise ValueError(f"{source.source_id}: A SmartRecruiters detail is not an object")

    raw_jobs = [detail for detail in details if isinstance(detail, dict)]
    raw_payload = {"totalFound": total, "content": raw_jobs}
    collected_at = utc_now_iso()
    jobs = [
        normalize_smartrecruiters_job(raw_job, source, collected_at)
        for raw_job in raw_jobs
    ]
    return raw_payload, jobs
