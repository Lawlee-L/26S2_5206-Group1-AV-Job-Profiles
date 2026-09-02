from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from av_jobs.collectors.ashby import collect_ashby
from av_jobs.collectors.comeet import collect_comeet
from av_jobs.collectors.greenhouse import collect_greenhouse
from av_jobs.collectors.jobylon import collect_jobylon
from av_jobs.collectors.lever import collect_lever
from av_jobs.collectors.moka import collect_moka
from av_jobs.collectors.smartrecruiters import collect_smartrecruiters
from av_jobs.collectors.workable import collect_workable
from av_jobs.config import SourceConfig, load_sources
from av_jobs.models import StandardJob
from av_jobs.storage import DATA_DIR, save_raw_snapshot, save_standardized_jobs


@dataclass(slots=True)
class SourceRunResult:
    source_id: str
    company: str
    platform: str
    status: str
    job_count: int
    error: str | None = None


COLLECTORS = {
    "ashby": collect_ashby,
    "comeet": collect_comeet,
    "greenhouse": collect_greenhouse,
    "jobylon": collect_jobylon,
    "lever": collect_lever,
    "moka": collect_moka,
    "smartrecruiters": collect_smartrecruiters,
    "workable": collect_workable,
}


def run_pipeline(
    *,
    platform: str | None = None,
    source_id: str | None = None,
    run_date: str | None = None,
) -> tuple[list[StandardJob], list[SourceRunResult], Path]:
    run_date = run_date or date.today().isoformat()
    sources = load_sources()
    if platform:
        sources = [source for source in sources if source.platform == platform]
    if source_id:
        sources = [source for source in sources if source.source_id == source_id]
    if not sources:
        raise ValueError("No In Scope sources matched the requested filters")

    # Collect every public job from each selected source.
    # AV relevance filtering belongs to the later data cleaning stage.
    all_jobs: list[StandardJob] = []
    results: list[SourceRunResult] = []
    for source in sources:
        collector = COLLECTORS.get(source.platform)
        if collector is None:
            results.append(SourceRunResult(source.source_id, source.company, source.platform, "unsupported", 0))
            continue
        try:
            raw_payload, jobs = collector(source)
            save_raw_snapshot(run_date, source.source_id, raw_payload)
            all_jobs.extend(jobs)
            results.append(SourceRunResult(source.source_id, source.company, source.platform, "success", len(jobs)))
        except Exception as exc:
            results.append(SourceRunResult(source.source_id, source.company, source.platform, "failed", 0, str(exc)))

    # Keep test batches separate. A full run uses jobs.json for all platforms.
    output_stem = source_id or platform or "jobs"
    standardized_path = save_standardized_jobs(run_date, all_jobs, f"{output_stem}.json")
    report_dir = DATA_DIR / "run_reports" / run_date
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{output_stem}_report.json"
    report_path.write_text(
        json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return all_jobs, results, standardized_path
