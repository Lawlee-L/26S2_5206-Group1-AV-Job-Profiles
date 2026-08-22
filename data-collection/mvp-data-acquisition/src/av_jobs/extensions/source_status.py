"""Per-source completion status written after each spider closes."""

from __future__ import annotations

from pathlib import Path

from scrapy import signals

from av_jobs.models import SourceStatus


class SourceStatusExtension:
    """Persist source counts and failures independently of item validation."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        return extension

    def spider_closed(self, spider, reason) -> None:
        stats = self.crawler.stats.get_stats()
        response_errors = int(stats.get("downloader/exception_count", 0))
        response_errors += int(stats.get("spider_exceptions/count", 0))
        validated_items = int(stats.get("av_jobs/validated_items", 0))
        validation_errors = int(stats.get("av_jobs/validation_errors", 0))
        finish_reason = str(reason)
        succeeded = (
            finish_reason == "finished"
            and validated_items > 0
            and validation_errors == 0
            and response_errors == 0
        )
        status = SourceStatus(
            run_id=spider.run_id,
            spider=spider.name,
            company=spider.company,
            source_name=spider.source_name,
            finish_reason=finish_reason,
            source_items_seen=int(getattr(spider, "source_total", 0)),
            validated_items=validated_items,
            validation_errors=validation_errors,
            response_count=int(stats.get("downloader/response_count", 0)),
            response_errors=response_errors,
            snapshot_files=int(stats.get("av_jobs/snapshot_files", 0)),
            status="success" if succeeded else "failed",
        )
        path = (
            Path(spider.data_root)
            / "status"
            / f"run_id={spider.run_id}"
            / f"{spider.company_slug}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(status.model_dump_json(indent=2) + "\n", encoding="utf-8")
