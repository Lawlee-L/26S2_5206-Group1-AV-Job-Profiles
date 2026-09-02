"""Collect Jobylon jobs and convert them to the standard format."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from av_jobs.collectors.greenhouse import html_to_text
from av_jobs.collectors.workable import workable_salary
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
JOBYLON_BASE_URL = "https://emp.jobylon.com"


class JsonLdParser(HTMLParser):
    """Read JSON-LD script blocks from an HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self._inside_json_ld = False
        self._parts: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag.lower() == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._inside_json_ld = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._inside_json_ld:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._inside_json_ld:
            self.blocks.append("".join(self._parts))
            self._inside_json_ld = False
            self._parts = []


def jobylon_job_urls(widget_html: str) -> list[str]:
    """Read unique job detail URLs from a Jobylon widget page."""
    paths = re.findall(r"\burl:\s*['\"]([^'\"]+/jobs/[^'\"]+|/jobs/[^'\"]+)['\"]", widget_html)
    if not paths:
        # Current widgets normally use relative paths beginning with /jobs/.
        paths = re.findall(r"\burl:\s*['\"](/jobs/[^'\"]+)['\"]", widget_html)

    urls: list[str] = []
    for path in paths:
        url = urljoin(JOBYLON_BASE_URL, path)
        if url not in urls:
            urls.append(url)
    return urls


def jobylon_json_ld(detail_html: str) -> dict[str, Any]:
    """Read the JobPosting object from one Jobylon detail page."""
    parser = JsonLdParser()
    parser.feed(detail_html)

    for block in parser.blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("@type") == "JobPosting":
                return candidate
            graph = candidate.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        return item
    raise ValueError("Jobylon detail page has no JobPosting JSON-LD")


def jobylon_location(raw_job: dict[str, Any]) -> str | None:
    """Build a readable location from Jobylon JSON-LD."""
    locations = raw_job.get("jobLocation")
    if isinstance(locations, dict):
        locations = [locations]
    if not isinstance(locations, list):
        return None

    rendered: list[str] = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        address = location.get("address")
        if isinstance(address, str):
            text = address.strip()
        elif isinstance(address, dict):
            street = str(address.get("streetAddress") or "").strip()
            if street:
                text = street
            else:
                parts = [
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("addressCountry"),
                ]
                text = ", ".join(str(part).strip() for part in parts if part)
        else:
            text = ""
        if text and text not in rendered:
            rendered.append(text)
    return "; ".join(rendered) or None


def jobylon_salary(raw_job: dict[str, Any], description: str | None) -> str | None:
    """Read structured salary data or an explicit salary sentence."""
    salary = raw_job.get("baseSalary")
    if isinstance(salary, str) and salary.strip():
        return salary.strip()
    if isinstance(salary, dict):
        currency = str(salary.get("currency") or "").strip()
        value = salary.get("value")
        if isinstance(value, dict):
            minimum = value.get("minValue")
            maximum = value.get("maxValue")
            unit = str(value.get("unitText") or "").strip()
            numbers = " - ".join(str(item) for item in (minimum, maximum) if item is not None)
            rendered = " ".join(item for item in (currency, numbers, unit) if item)
            if rendered:
                return rendered
        elif value is not None:
            rendered = " ".join(item for item in (currency, str(value)) if item)
            if rendered:
                return rendered
    return workable_salary(description)


def normalize_jobylon_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
    job_url: str,
) -> StandardJob:
    """Convert one Jobylon job to the standard job format."""
    identifier = raw_job.get("identifier")
    source_job_id: str | None = None
    if isinstance(identifier, dict) and identifier.get("value") is not None:
        source_job_id = str(identifier["value"])
    elif identifier is not None:
        source_job_id = str(identifier)
    if source_job_id is None:
        match = re.search(r"/jobs/(\d+)-", job_url)
        source_job_id = match.group(1) if match else None

    title = raw_job.get("title")
    description = html_to_text(raw_job.get("description"))
    location = jobylon_location(raw_job)

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
            salary=jobylon_salary(raw_job, description),
            date_posted=raw_job.get("datePosted"),
        ),
    )


def collect_jobylon(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect all Jobylon links and read each full job detail page."""
    widget_html = get_text(source.endpoint)
    job_urls = jobylon_job_urls(widget_html)
    if not job_urls:
        raise ValueError(f"{source.source_id}: Jobylon widget has no job links")

    # This collector does not filter jobs. Data cleaning is a later step.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        detail_pages = list(executor.map(get_text, job_urls))

    raw_jobs = [jobylon_json_ld(page) for page in detail_pages]
    collected_at = utc_now_iso()
    jobs = [
        normalize_jobylon_job(raw_job, source, collected_at, job_url)
        for raw_job, job_url in zip(raw_jobs, job_urls, strict=True)
    ]
    raw_payload = {
        "widget_url": source.endpoint,
        "widget_html": widget_html,
        "jobs": [
            {"job_url": job_url, "job_posting": raw_job}
            for job_url, raw_job in zip(job_urls, raw_jobs, strict=True)
        ],
    }
    return raw_payload, jobs
