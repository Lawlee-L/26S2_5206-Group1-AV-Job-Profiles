"""Collect AImotive jobs and convert them to the standard format."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from av_jobs.config import SourceConfig
from av_jobs.http import get_text
from av_jobs.models import (
    JobData,
    JobMetadata,
    StandardJob,
    build_source_key,
    utc_now_iso,
)


DETAIL_WORKERS = 5
BLOCK_TAGS = {"br", "h1", "h2", "h3", "h4", "li", "p"}


class AImotiveListParser(HTMLParser):
    """Read job links from the AImotive careers page."""

    def __init__(self) -> None:
        super().__init__()
        self._position_depth = 0
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag.lower() == "div" and "position-list-item" in classes:
            self._position_depth = 1
            return
        if self._position_depth and tag.lower() == "div":
            self._position_depth += 1
        if self._position_depth and tag.lower() == "a":
            href = attributes.get("href")
            if href and "/w/" in href and href not in self.urls:
                self.urls.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self._position_depth and tag.lower() == "div":
            self._position_depth -= 1


class AImotiveDetailParser(HTMLParser):
    """Read standard fields from one AImotive detail page."""

    def __init__(self) -> None:
        super().__init__()
        self._field: str | None = None
        self._field_tag: str | None = None
        self._field_parts: list[str] = []
        self._content_depth = 0
        self._content_parts: list[str] = []
        self.title: str | None = None
        self.location: str | None = None
        self.description: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        editable_id = attributes.get("data-lfr-editable-id")
        if editable_id in {"post-title", "post-location"}:
            self._field = editable_id
            self._field_tag = tag.lower()
            self._field_parts = []
        if editable_id == "post-content":
            self._content_depth = 1
        elif self._content_depth and tag.lower() == "div":
            self._content_depth += 1
        if self._content_depth and tag.lower() in BLOCK_TAGS:
            self._content_parts.append("\n")
            if tag.lower() == "li":
                self._content_parts.append("- ")

    def handle_data(self, data: str) -> None:
        if self._field:
            self._field_parts.append(data)
        if self._content_depth:
            self._content_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        lower_tag = tag.lower()
        if self._field and lower_tag == self._field_tag:
            text = " ".join("".join(self._field_parts).split()) or None
            if self._field == "post-title":
                self.title = text
            else:
                self.location = text
            self._field = None
            self._field_tag = None
            self._field_parts = []
        if self._content_depth and lower_tag == "div":
            self._content_depth -= 1
            if self._content_depth == 0:
                lines = [" ".join(line.split()) for line in "".join(self._content_parts).splitlines()]
                self.description = "\n".join(line for line in lines if line) or None


def aimotive_job_urls(list_html: str, endpoint: str) -> list[str]:
    """Return unique job detail URLs from the careers page."""
    parser = AImotiveListParser()
    parser.feed(list_html)
    return [urljoin(endpoint, url) for url in parser.urls]


def aimotive_detail(detail_html: str) -> dict[str, str | None]:
    """Read one public job detail page."""
    parser = AImotiveDetailParser()
    parser.feed(detail_html)
    if not parser.title or not parser.description:
        raise ValueError("AImotive detail page is missing its title or description")
    return {
        "title": parser.title,
        "description": parser.description,
        "location": parser.location,
    }


def normalize_aimotive_job(
    raw_job: dict[str, str | None],
    source: SourceConfig,
    collected_at: str,
    job_url: str,
) -> StandardJob:
    """Convert one AImotive job to the standard job format."""
    source_job_id = unquote(urlsplit(job_url).path.rstrip("/").split("/")[-1]).strip() or None
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
            salary=None,
            date_posted=None,
        ),
    )


def collect_aimotive(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    """Collect every public job from the AImotive careers page."""
    list_html = get_text(source.endpoint)
    job_urls = aimotive_job_urls(list_html, source.endpoint)
    if not job_urls:
        raise ValueError(f"{source.source_id}: AImotive careers page has no job links")

    # This collector does not filter jobs. Data cleaning is a later step.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        detail_pages = list(executor.map(get_text, job_urls))

    raw_jobs = [aimotive_detail(page) for page in detail_pages]
    collected_at = utc_now_iso()
    jobs = [
        normalize_aimotive_job(raw_job, source, collected_at, job_url)
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
