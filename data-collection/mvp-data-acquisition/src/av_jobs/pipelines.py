"""Scrapy item validation and validated-record export."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError
from scrapy.exceptions import DropItem

from .models import RawJob


class ValidationExportPipeline:
    """Validate every spider item and write a per-company JSONL snapshot."""

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self) -> None:
        spider = self.crawler.spider
        validated_dir = (
            Path(spider.data_root)
            / "validated"
            / f"run_id={spider.run_id}"
            / f"company={spider.company_slug}"
        )
        validated_dir.mkdir(parents=True, exist_ok=True)
        self._issues_path = validated_dir / "validation_issues.json"
        self._stream = (validated_dir / "jobs.jsonl").open("w", encoding="utf-8")
        self._issues: list[dict] = []

    def process_item(self, item):
        spider = self.crawler.spider
        self.crawler.stats.inc_value("av_jobs/items_received")
        try:
            job = RawJob.model_validate(item).with_content_hash()
        except ValidationError as exc:
            self.crawler.stats.inc_value("av_jobs/validation_errors")
            self._issues.append(
                {
                    "spider": spider.name,
                    "company": spider.company,
                    "source_job_id": item.get("source_job_id"),
                    "error": exc.errors(include_url=False),
                }
            )
            raise DropItem(f"Shared job schema validation failed: {exc}") from exc

        self._stream.write(job.model_dump_json() + "\n")
        self.crawler.stats.inc_value("av_jobs/validated_items")
        return job.model_dump(mode="json")

    def close_spider(self) -> None:
        self._stream.close()
        self._issues_path.write_text(
            json.dumps(self._issues, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
