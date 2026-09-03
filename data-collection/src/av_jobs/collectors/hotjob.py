"""Collect HotJob jobs and convert them to the standard format."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

from av_jobs.collectors.greenhouse import html_to_text
from av_jobs.collectors.workable import workable_salary
from av_jobs.config import SourceConfig
from av_jobs.http import post_form_json
from av_jobs.models import (
    JobData,
    JobMetadata,
    StandardJob,
    build_source_key,
    utc_now_iso,
)


PAGE_SIZE = 50
DETAIL_WORKERS = 8


def hotjob_detail_endpoint(list_endpoint: str) -> str:
    """Change the list endpoint into the detail endpoint."""
    return list_endpoint.replace("/listPosition/", "/listPositionDetail/", 1)


def hotjob_public_url(source: SourceConfig, post_id: str) -> str:
    """Build the public detail page URL for one HotJob position."""
    parts = urlsplit(source.career_url)
    detail_path = re.sub(r"/social\.html$", "/posDetail.html", parts.path)
    query = urlencode({"postId": post_id, "postType": "society"})
    return urlunsplit((parts.scheme, parts.netloc, detail_path, query, ""))


def hotjob_description(raw_job: dict[str, Any]) -> str | None:
    """Join the public responsibilities and requirements."""
    sections: list[str] = []
    for title, field in (
        ("Responsibilities", "workContent"),
        ("Requirements", "serviceCondition"),
        ("Additional information", "applyPositionContent"),
    ):
        text = html_to_text(raw_job.get(field))
        if text:
            sections.append(f"{title}\n{text}")
    return "\n\n".join(sections) or None


def normalize_hotjob_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    """Convert one HotJob position to the standard job format."""
    source_job_id_value = raw_job.get("postId") or raw_job.get("externalPostId")
    source_job_id = str(source_job_id_value) if source_job_id_value else None
    title = raw_job.get("postName")
    location = raw_job.get("workPlaceStr")
    description = hotjob_description(raw_job)
    job_url = hotjob_public_url(source, source_job_id) if source_job_id else source.career_url

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
            date_posted=raw_job.get("publishFirstDate") or raw_job.get("publishDate"),
        ),
    )


def collect_hotjob(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect all HotJob pages and full position details."""
    list_pages: list[dict[str, Any]] = []
    listings: list[dict[str, Any]] = []
    current_page = 1
    total_pages = 1

    # This collector does not filter jobs. Data cleaning is a later step.
    while current_page <= total_pages:
        payload = post_form_json(
            source.endpoint,
            {
                "isFrompb": "true",
                "recruitType": 2,
                "pageSize": PAGE_SIZE,
                "currentPage": current_page,
            },
        )
        if not isinstance(payload, dict) or str(payload.get("state")) != "200":
            raise ValueError(f"{source.source_id}: HotJob list request was not successful")
        data = payload.get("data")
        page_form = data.get("pageForm") if isinstance(data, dict) else None
        page_data = page_form.get("pageData") if isinstance(page_form, dict) else None
        if not isinstance(page_data, list):
            raise ValueError(f"{source.source_id}: HotJob response has no pageData list")

        list_pages.append(payload)
        listings.extend(item for item in page_data if isinstance(item, dict))
        total_pages_value = page_form.get("totalPage")
        total_pages = int(total_pages_value) if total_pages_value else current_page
        current_page += 1

    post_ids = [str(item.get("postId")) for item in listings if item.get("postId")]
    if len(post_ids) != len(listings):
        raise ValueError(f"{source.source_id}: A HotJob listing has no postId")

    detail_endpoint = hotjob_detail_endpoint(source.endpoint)

    def fetch_detail(post_id: str) -> dict[str, Any]:
        payload = post_form_json(detail_endpoint, {"postId": post_id, "recruitType": 2})
        if not isinstance(payload, dict) or str(payload.get("state")) != "200":
            raise ValueError(f"{source.source_id}: HotJob detail request failed for {post_id}")
        detail = payload.get("data")
        if not isinstance(detail, dict):
            raise ValueError(f"{source.source_id}: HotJob detail has no data object")
        return detail

    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        details = list(executor.map(fetch_detail, post_ids))

    collected_at = utc_now_iso()
    jobs = [normalize_hotjob_job(detail, source, collected_at) for detail in details]
    raw_payload = {
        "list_pages": list_pages,
        "jobs": details,
    }
    return raw_payload, jobs
