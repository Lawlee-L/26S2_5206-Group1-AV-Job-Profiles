"""Application service that coordinates collection, validation and publication.

The command-line entry point delegates here so that orchestration can be tested
without coupling the domain modules to ``argparse`` or console output.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
from scrapy.spiderloader import SpiderLoader

from . import settings as project_settings
from .cleaning import clean_current_jobs, merge_history
from .models import RawJob, SourceStatus
from .quality import build_quality_report
from .registry import SOURCE_BY_SPIDER
from .storage import (
    build_duckdb,
    load_latest_jobs,
    publish_latest,
    write_json,
    write_parquet,
)

Reporter = Callable[[str], None]


@dataclass(frozen=True)
class RunConfig:
    """Immutable inputs for one pipeline execution."""

    project_root: Path
    data_root: Path
    output_root: Path
    run_id: str
    spider_names: tuple[str, ...]
    max_jobs: int = 0
    no_publish: bool = False
    log_level: str = "INFO"

    @property
    def sampled(self) -> bool:
        """Return whether the run intentionally limits jobs per source."""

        return self.max_jobs > 0


@dataclass(frozen=True)
class RunOutcome:
    """Machine-readable workflow result returned to the CLI or another caller."""

    exit_code: int
    summary: dict


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _portable_path(path: Path, project_root: Path) -> str:
    """Prefer repository-relative manifest paths while supporting custom roots."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _crawl_sources(config: RunConfig) -> None:
    """Run all selected spiders in one Scrapy reactor."""

    settings = Settings()
    settings.setmodule(project_settings, priority="project")
    settings.set("LOG_LEVEL", config.log_level, priority="cmdline")
    loader = SpiderLoader.from_settings(settings)
    process = CrawlerProcess(settings)

    for spider_name in config.spider_names:
        process.crawl(
            loader.load(spider_name),
            run_id=config.run_id,
            data_root=str(config.data_root),
            max_jobs=config.max_jobs,
        )
    process.start(stop_after_crawl=True, install_signal_handlers=False)


def _read_source_statuses(
    data_root: Path, run_id: str, spider_names: Sequence[str]
) -> tuple[list[SourceStatus], list[dict]]:
    status_dir = data_root / "status" / f"run_id={run_id}"
    statuses_by_spider: dict[str, SourceStatus] = {}
    for path in status_dir.glob("*.json"):
        status = SourceStatus.model_validate_json(path.read_text(encoding="utf-8"))
        statuses_by_spider[status.spider] = status

    statuses: list[SourceStatus] = []
    issues: list[dict] = []
    for spider_name in spider_names:
        status = statuses_by_spider.get(spider_name)
        if status is None:
            source = SOURCE_BY_SPIDER[spider_name]
            status = SourceStatus(
                run_id=run_id,
                spider=spider_name,
                company=source.company,
                source_name=source.platform,
                finish_reason="missing_status",
                source_items_seen=0,
                validated_items=0,
                validation_errors=0,
                response_count=0,
                response_errors=1,
                snapshot_files=0,
                status="failed",
            )
        statuses.append(status)
        if status.status != "success":
            issues.append(
                {
                    "stage": "source",
                    "spider": status.spider,
                    "company": status.company,
                    "finish_reason": status.finish_reason,
                    "validated_items": status.validated_items,
                    "validation_errors": status.validation_errors,
                    "response_errors": status.response_errors,
                }
            )
    return statuses, issues


def _read_validated_jobs(data_root: Path, run_id: str) -> list[RawJob]:
    validated_dir = data_root / "validated" / f"run_id={run_id}"
    jobs: list[RawJob] = []
    for path in sorted(validated_dir.glob("company=*/jobs.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                jobs.append(RawJob.model_validate_json(line))
    return jobs


def _read_validation_issues(data_root: Path, run_id: str) -> list[dict]:
    validated_dir = data_root / "validated" / f"run_id={run_id}"
    issues: list[dict] = []
    for path in sorted(validated_dir.glob("company=*/validation_issues.json")):
        issues.extend(json.loads(path.read_text(encoding="utf-8")))
    return issues


def _failure_outcome(
    *,
    status: str,
    config: RunConfig,
    output_run_dir: Path,
    issues: list[dict],
    **details,
) -> RunOutcome:
    summary = {
        "run_id": config.run_id,
        "status": status,
        "selected_spiders": list(config.spider_names),
        "issues": issues,
        **details,
    }
    write_json(output_run_dir / "issues.json", issues)
    write_json(output_run_dir / "run_summary.json", summary)
    return RunOutcome(exit_code=1, summary=summary)


def execute_run(config: RunConfig, reporter: Reporter = print) -> RunOutcome:
    """Execute one quality-gated collection-to-DuckDB workflow.

    The latest manifest is replaced only after both Parquet files and DuckDB
    have been written and independently reopened. Any earlier failure returns a
    non-zero outcome without changing the previous published pointer.
    """

    output_run_dir = config.output_root / f"run_id={config.run_id}"
    output_run_dir.mkdir(parents=True, exist_ok=True)
    latest_manifest = config.data_root / "published" / "latest.json"

    reporter(
        f"[1/6] Run {config.run_id}: starting "
        f"{len(config.spider_names)} independent Scrapy spider(s)"
    )
    _crawl_sources(config)

    statuses, issues = _read_source_statuses(
        config.data_root, config.run_id, config.spider_names
    )
    issues.extend(_read_validation_issues(config.data_root, config.run_id))
    status_frame = pd.DataFrame(status.model_dump(mode="json") for status in statuses)
    successful_sources = int((status_frame["status"] == "success").sum())
    reporter(
        f"[2/6] Source collection complete: {successful_sources}/"
        f"{len(config.spider_names)} source(s) passed"
    )

    jobs = _read_validated_jobs(config.data_root, config.run_id)
    reporter(f"[3/6] Pydantic validation complete: {len(jobs)} valid job record(s)")
    if not jobs:
        reporter("[4/6] Quality gate failed: no validated jobs; latest unchanged")
        return _failure_outcome(
            status="failed",
            config=config,
            output_run_dir=output_run_dir,
            issues=issues,
            validated_jobs=0,
        )

    current = clean_current_jobs(jobs, config.run_id)
    previous = None if config.sampled else load_latest_jobs(latest_manifest)
    selected_companies = {
        SOURCE_BY_SPIDER[name].company for name in config.spider_names
    }
    combined = merge_history(
        current,
        previous,
        refreshed_companies=selected_companies,
        snapshot_run_id=config.run_id,
    )
    quality = build_quality_report(combined, status_frame, selected_companies)
    reporter(
        f"[4/6] pandas and quality checks: {quality['active_jobs']} active / "
        f"{quality['all_historical_jobs']} historical; passed={quality['passed']}"
    )
    write_json(output_run_dir / "issues.json", issues)
    write_json(output_run_dir / "quality_report.json", quality)
    if not quality["passed"]:
        reporter("[5/6] Publication stopped; previous latest snapshot is unchanged")
        return _failure_outcome(
            status="failed_quality_gate",
            config=config,
            output_run_dir=output_run_dir,
            issues=issues,
            validated_jobs=len(jobs),
            quality_report=quality,
            latest_manifest_unchanged=str(latest_manifest),
        )

    processed_dir = config.data_root / "processed" / f"run_id={config.run_id}"
    jobs_parquet = processed_dir / "jobs.parquet"
    status_parquet = processed_dir / "source_status.parquet"
    database_path = output_run_dir / "av_jobs.duckdb"
    analysis_path = output_run_dir / "duckdb_analysis.json"
    write_parquet(combined, jobs_parquet)
    write_parquet(status_frame, status_parquet)
    analysis = build_duckdb(jobs_parquet, status_parquet, database_path)
    write_json(analysis_path, analysis)

    with duckdb.connect(str(database_path), read_only=True) as connection:
        reopened_count = connection.execute("SELECT count(*) FROM jobs").fetchone()[0]
    if reopened_count != len(combined):
        raise RuntimeError(
            f"DuckDB verification failed: expected {len(combined)}, "
            f"found {reopened_count}"
        )
    reporter(
        f"[5/6] Parquet and DuckDB complete: {reopened_count} row(s) "
        "verified after reopening"
    )

    publish_allowed = not config.no_publish and not config.sampled
    if publish_allowed:
        publish_latest(
            latest_manifest,
            {
                "run_id": config.run_id,
                "status": "published",
                "published_at": _utc_now().isoformat(),
                "jobs_parquet": _portable_path(jobs_parquet, config.project_root),
                "source_status_parquet": _portable_path(
                    status_parquet, config.project_root
                ),
                "duckdb_file": _portable_path(database_path, config.project_root),
                "selected_spiders": list(config.spider_names),
                "active_jobs": quality["active_jobs"],
                "historical_jobs": quality["all_historical_jobs"],
            },
        )
        final_status = "published"
        reporter(f"[6/6] Published latest manifest: {latest_manifest}")
    else:
        final_status = "verified_not_published"
        reason = "sampled run" if config.sampled else "--no-publish"
        reporter(f"[6/6] Outputs verified; latest unchanged ({reason})")

    summary = {
        "run_id": config.run_id,
        "status": final_status,
        "selected_spiders": list(config.spider_names),
        "successful_sources": successful_sources,
        "validated_jobs": len(jobs),
        "active_jobs": quality["active_jobs"],
        "historical_jobs": quality["all_historical_jobs"],
        "jobs_parquet": str(jobs_parquet),
        "source_status_parquet": str(status_parquet),
        "duckdb_file": str(database_path),
        "analysis_file": str(analysis_path),
        "latest_manifest": str(latest_manifest) if publish_allowed else None,
        "analysis": analysis,
    }
    write_json(output_run_dir / "run_summary.json", summary)
    return RunOutcome(exit_code=0, summary=summary)
