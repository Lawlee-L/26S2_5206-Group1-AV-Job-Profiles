from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from av_jobs.config import SourceConfig
from av_jobs.http import get_json
from av_jobs.models import (
    JobData,
    JobMetadata,
    StandardJob,
    build_source_key,
    utc_now_iso,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def html_to_text(value: str | None) -> str | None:
    if not value:
        return None
    parser = _TextExtractor()
    parser.feed(unescape(value))
    text = "\n".join(parser.parts).strip()
    return text or None


def extract_salary(metadata: Any) -> str | None:
    """Read salary information only when Greenhouse provides it."""
    if not isinstance(metadata, list):
        return None
    salary_parts: list[str] = []
    for item in metadata:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        value = item.get("value")
        if not name or not any(word in name.lower() for word in ("salary", "compensation", "pay")):
            continue
        if isinstance(value, list):
            rendered = ", ".join(str(part) for part in value if part is not None)
        else:
            rendered = str(value) if value is not None else ""
        if rendered:
            salary_parts.append(f"{name}: {rendered}")
    return "; ".join(salary_parts) or None


def endpoint_with_content(endpoint: str) -> str:
    """Add content=true so Greenhouse returns the full job description."""
    parts = urlsplit(endpoint)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["content"] = "true"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def normalize_greenhouse_job(
    raw_job: dict[str, Any],
    source: SourceConfig,
    collected_at: str,
) -> StandardJob:
    source_job_id = str(raw_job["id"]) if raw_job.get("id") is not None else None
    title = raw_job.get("title")
    job_url = raw_job.get("absolute_url")
    location_value = raw_job.get("location")
    location = location_value.get("name") if isinstance(location_value, dict) else None

    source_key = build_source_key(
        platform=source.platform,
        company=source.company,
        source_job_id=source_job_id,
        job_url=job_url,
        title=title,
        location=location,
    )

    return StandardJob(
        metadata=JobMetadata(
            source_id=source.source_id,
            platform=source.platform,
            company=source.company,
            region=source.region,
            source_job_id=source_job_id,
            source_key=source_key,
            collected_at=collected_at,
        ),
        data=JobData(
            advertised_job_title=title,
            job_description=html_to_text(raw_job.get("content")),
            job_url=job_url,
            location=location,
            salary=extract_salary(raw_job.get("metadata")),
            date_posted=raw_job.get("first_published"),
        ),
    )


def collect_greenhouse(source: SourceConfig) -> tuple[Any, list[StandardJob]]:
    payload = get_json(endpoint_with_content(source.endpoint))
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError(f"{source.source_id}: Greenhouse response has no jobs list")

    collected_at = utc_now_iso()
    jobs = [
        normalize_greenhouse_job(raw_job, source, collected_at)
        for raw_job in payload["jobs"]
        if isinstance(raw_job, dict)
    ]
    return payload, jobs
