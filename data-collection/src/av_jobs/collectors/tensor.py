"""Collect Tensor jobs and convert them to the standard format."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

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
BLOCK_TAGS = {"br", "h1", "h2", "h3", "h4", "li", "p"}
DETAIL_PATH = re.compile(r"^/careers/jd\d+/?$")
SALARY_TEXT = re.compile(r"\s*\(Salary Range:\s*(.+?)\)\s*$", re.IGNORECASE)


class TensorListParser(HTMLParser):
    """Read unique Tensor job links from the careers page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href and DETAIL_PATH.match(urlsplit(href).path) and href not in self.links:
            self.links.append(href)


class TensorDetailParser(HTMLParser):
    """Read the title and content sections from one Tensor job page."""

    def __init__(self) -> None:
        super().__init__()
        self._title_tag: str | None = None
        self._title_parts: list[str] = []
        self._grid_depth = 0
        self._grid_parts: list[str] = []
        self._item_depth = 0
        self._item_parts: list[str] = []
        self.title: str | None = None
        self.grids: list[tuple[str, list[str]]] = []
        self._grid_items: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower_tag = tag.lower()
        classes = (dict(attrs).get("class") or "").split()

        if lower_tag == "h1" and "cms-job-title" in classes:
            self._title_tag = lower_tag
            self._title_parts = []

        if lower_tag == "div" and "grid-33" in classes and not self._grid_depth:
            self._grid_depth = 1
            self._grid_parts = []
            self._grid_items = []
        elif self._grid_depth and lower_tag == "div":
            self._grid_depth += 1

        if self._grid_depth and lower_tag in BLOCK_TAGS:
            self._grid_parts.append("\n")
            if lower_tag == "li":
                self._grid_parts.append("- ")
                self._item_depth = 1
                self._item_parts = []
        elif self._item_depth:
            self._item_depth += 1

    def handle_data(self, data: str) -> None:
        if self._title_tag:
            self._title_parts.append(data)
        if self._grid_depth:
            self._grid_parts.append(data)
        if self._item_depth:
            self._item_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower_tag = tag.lower()
        if self._title_tag == lower_tag:
            self.title = " ".join("".join(self._title_parts).split()) or None
            self._title_tag = None
            self._title_parts = []

        if self._item_depth:
            self._item_depth -= 1
            if self._item_depth == 0:
                item = " ".join("".join(self._item_parts).split())
                if item:
                    self._grid_items.append(item)
                self._item_parts = []

        if self._grid_depth and lower_tag in BLOCK_TAGS:
            self._grid_parts.append("\n")
        if self._grid_depth and lower_tag == "div":
            self._grid_depth -= 1
            if self._grid_depth == 0:
                lines = [" ".join(line.split()) for line in "".join(self._grid_parts).splitlines()]
                text = "\n".join(line for line in lines if line)
                self.grids.append((text, list(self._grid_items)))
                self._grid_parts = []
                self._grid_items = []


def tensor_job_urls(list_html: str, endpoint: str) -> list[str]:
    """Return unique Tensor job detail URLs."""
    parser = TensorListParser()
    parser.feed(list_html)
    return [urljoin(endpoint, link) for link in parser.links]


def tensor_detail(detail_html: str) -> dict[str, Any]:
    """Read the standard source fields from one Tensor detail page."""
    parser = TensorDetailParser()
    parser.feed(detail_html)
    if not parser.title:
        raise ValueError("Tensor detail page is missing its job title")

    description_parts: list[str] = []
    locations: list[str] = []
    salary_parts: list[str] = []
    for text, items in parser.grids:
        first_line = text.splitlines()[0] if text else ""
        if first_line.casefold() == "locations":
            for item in items:
                salary_match = SALARY_TEXT.search(item)
                location = SALARY_TEXT.sub("", item).strip()
                if location and location not in locations:
                    locations.append(location)
                if salary_match:
                    salary = salary_match.group(1).strip()
                    label = f"{location}: {salary}" if location else salary
                    if label not in salary_parts:
                        salary_parts.append(label)
        elif text:
            description_parts.append(text)

    description = "\n\n".join(description_parts) or None
    if not description:
        raise ValueError("Tensor detail page is missing its job description")
    return {
        "title": parser.title,
        "description": description,
        "location": " | ".join(locations) or None,
        "salary": " | ".join(salary_parts) or None,
        "date_posted": None,
    }


def normalize_tensor_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
    job_url: str,
) -> StandardJob:
    """Convert one Tensor job to the standard job format."""
    source_job_id = urlsplit(job_url).path.rstrip("/").split("/")[-1] or None
    title = raw_job.get("title")
    location = raw_job.get("location")

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
            job_description=raw_job.get("description"),
            job_url=job_url,
            location=location,
            salary=raw_job.get("salary"),
            date_posted=None,
        ),
    )


def collect_tensor(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect every public job from the Tensor careers page."""
    list_html = get_text(source.endpoint)
    job_urls = tensor_job_urls(list_html, source.endpoint)
    if not job_urls:
        raise ValueError(f"{source.source_id}: Tensor careers page has no job links")

    # This collector keeps every public role for later data cleaning.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        detail_pages = list(executor.map(get_text, job_urls))

    raw_jobs = [tensor_detail(page) for page in detail_pages]
    collected_at = utc_now_iso()
    jobs = [
        normalize_tensor_job(raw_job, source, collected_at, job_url)
        for raw_job, job_url in zip(raw_jobs, job_urls, strict=True)
    ]
    raw_payload = {
        "list_url": source.endpoint,
        "list_html": list_html,
        "jobs": [
            {"job_url": job_url, "detail_html": page, "parsed_fields": raw_job}
            for job_url, page, raw_job in zip(job_urls, detail_pages, raw_jobs, strict=True)
        ],
    }
    return raw_payload, jobs
