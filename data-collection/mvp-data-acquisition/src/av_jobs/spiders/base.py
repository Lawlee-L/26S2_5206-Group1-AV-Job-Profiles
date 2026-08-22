"""Shared behaviour for structured public ATS spiders."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import scrapy
from scrapy.exceptions import CloseSpider

from av_jobs.snapshots import write_response_snapshot


def utc_now() -> datetime:
    """Return an aware UTC timestamp for collected records."""

    return datetime.now(UTC)


def slugify(value: str) -> str:
    """Convert a display name to a stable directory component."""

    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "source"


def join_values(values: Iterable[object]) -> str | None:
    """Join unique, nonblank source values without changing their text."""

    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return " | ".join(dict.fromkeys(cleaned)) or None


class AtsApiSpider(scrapy.Spider):
    """Base class for one-company spiders backed by a public structured API."""

    company: str
    source_name: str
    source_total = 0

    def __init__(
        self,
        run_id: str | None = None,
        data_root: str | Path | None = None,
        max_jobs: int | str = 0,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.run_id = run_id or utc_now().strftime("%Y%m%dT%H%M%SZ")
        self.data_root = Path(data_root or "data").resolve()
        self.max_jobs = max(0, int(max_jobs))
        self.company_slug = slugify(self.company)

    def snapshot_response(self, response: scrapy.http.Response) -> Path:
        """Persist the raw response before any platform-specific parsing."""

        path = write_response_snapshot(
            response,
            data_root=self.data_root,
            run_id=self.run_id,
            company=self.company,
            company_slug=self.company_slug,
            source_name=self.source_name,
        )
        self.crawler.stats.inc_value("av_jobs/snapshot_files")
        return path

    def selected_jobs(self, jobs: list[dict]) -> list[dict]:
        """Apply an optional smoke-test limit while recording the source total."""

        self.source_total = len(jobs)
        if not jobs:
            raise CloseSpider("empty_source")
        return jobs[: self.max_jobs] if self.max_jobs else jobs

    def common_item(self, **values) -> dict:
        """Add provenance fields required by the shared Pydantic contract."""

        return {
            **values,
            "source_type": "ats_api",
            "source_name": self.source_name,
            "scraped_at": utc_now().isoformat(),
            "run_id": self.run_id,
            "content_hash": None,
        }
