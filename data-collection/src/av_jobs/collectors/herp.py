"""Collect HERP jobs and convert them to the standard format."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

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


DETAIL_WORKERS = 8


class HerpScriptParser(HTMLParser):
    """Read useful JSON script blocks from a HERP detail page."""

    def __init__(self) -> None:
        super().__init__()
        self._script_id: str | None = None
        self._script_type: str | None = None
        self._parts: list[str] = []
        self.react_props: list[str] = []
        self.json_ld: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attributes = dict(attrs)
        self._script_id = attributes.get("id")
        self._script_type = attributes.get("type", "").lower()
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._script_type:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self._script_type:
            return
        text = "".join(self._parts)
        if self._script_id == "herp-react-props":
            self.react_props.append(text)
        elif self._script_type == "application/ld+json":
            self.json_ld.append(text)
        self._script_id = None
        self._script_type = None
        self._parts = []


def herp_job_urls(list_html: str, endpoint: str) -> list[str]:
    """Read unique HERP job links from one public list page."""
    path = urlsplit(endpoint).path.rstrip("/")
    match = re.match(r"(/v1/[^/]+)", path)
    if not match:
        return []
    company_path = re.escape(match.group(1))
    links = re.findall(rf'href=["\']({company_path}/[A-Za-z0-9_-]+)["\']', list_html)

    urls: list[str] = []
    for link in links:
        url = urljoin(endpoint, link)
        if url not in urls:
            urls.append(url)
    return urls


def herp_detail_data(detail_html: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read the JobPosting and HERP page data from one detail page."""
    parser = HerpScriptParser()
    parser.feed(detail_html)

    page_data: dict[str, Any] = {}
    for block in parser.react_props:
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            page_data = value
            break

    for block in parser.json_ld:
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("@type") == "JobPosting":
            return value, page_data
    raise ValueError("HERP detail page has no JobPosting JSON-LD")


def _page_text(page_data: dict[str, Any], name: str) -> str | None:
    value = page_data.get(name)
    if isinstance(value, dict):
        text = value.get("text")
    else:
        text = value
    if not isinstance(text, str):
        return None
    cleaned = text.strip()
    return cleaned or None


def herp_location(raw_job: dict[str, Any], page_data: dict[str, Any]) -> str | None:
    """Read the location from HERP page data or JSON-LD."""
    location = _page_text(page_data, "location")
    if location:
        return location
    value = raw_job.get("jobLocation")
    if isinstance(value, dict):
        address = value.get("address")
        if isinstance(address, str) and address.strip():
            return address.strip()
    return None


def normalize_herp_job(
    raw_job: dict[str, Any],
    page_data: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
    job_url: str,
) -> StandardJob:
    """Convert one HERP job to the standard job format."""
    source_job_id = urlsplit(job_url).path.rstrip("/").split("/")[-1] or None
    title = raw_job.get("title")
    description = html_to_text(raw_job.get("description"))
    location = herp_location(raw_job, page_data)
    canonical_url = page_data.get("canonicalUrl")
    if isinstance(canonical_url, str) and canonical_url.strip():
        job_url = canonical_url.strip()

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
            salary=_page_text(page_data, "salary"),
            date_posted=raw_job.get("datePosted"),
        ),
    )


def collect_herp(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect HERP links and read each public job detail page."""
    list_html = get_text(source.endpoint)
    job_urls = herp_job_urls(list_html, source.endpoint)
    if not job_urls:
        raise ValueError(f"{source.source_id}: HERP list page has no job links")

    # This collector does not filter jobs. Data cleaning is a later step.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        detail_pages = list(executor.map(get_text, job_urls))

    parsed_jobs = [herp_detail_data(page) for page in detail_pages]
    collected_at = utc_now_iso()
    jobs = [
        normalize_herp_job(raw_job, page_data, source, collected_at, job_url)
        for (raw_job, page_data), job_url in zip(parsed_jobs, job_urls, strict=True)
    ]
    raw_payload = {
        "list_url": source.endpoint,
        "list_html": list_html,
        "jobs": [
            {"job_url": job_url, "job_posting": raw_job, "page_data": page_data}
            for job_url, (raw_job, page_data) in zip(job_urls, parsed_jobs, strict=True)
        ],
    }
    return raw_payload, jobs
