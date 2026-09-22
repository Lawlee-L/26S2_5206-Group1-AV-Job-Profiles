from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from av_jobs.models import StandardJob


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
TRANSLATED_FIELDS = (
    "advertised_job_title",
    "job_description",
    "location",
)


def _write_json(path: Path, payload: Any) -> None:
    """Write JSON safely without damaging an older file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def save_raw_snapshot(
    run_date: str,
    source_id: str,
    payload: Any,
) -> Path:
    """Save the unmodified response from one source."""
    output_dir = DATA_DIR / "raw" / run_date
    output_path = output_dir / f"{source_id}.json"
    _write_json(output_path, payload)
    return output_path


def save_standardized_jobs(
    run_date: str,
    jobs: Iterable[StandardJob],
    filename: str = "jobs.json",
) -> Path:
    """Save all standardized jobs from one pipeline run."""
    output_dir = DATA_DIR / "standardized" / run_date
    output_path = output_dir / filename
    _write_json(output_path, [job.to_dict() for job in jobs])
    return output_path


def merge_history_records(
    history: list[dict[str, Any]],
    current_jobs: list[dict[str, Any]],
    run_date: str,
    successful_source_ids: set[str] | None = None,
    *,
    preserve_existing_translation: bool = False,
) -> list[dict[str, Any]]:
    """Keep old jobs, add new jobs, and update jobs seen again."""
    records: dict[str, dict[str, Any]] = {}
    for job in history:
        metadata = job.get("metadata") if isinstance(job, dict) else None
        source_key = metadata.get("source_key") if isinstance(metadata, dict) else None
        if source_key:
            first_seen = str(metadata.get("first_seen_date") or "")
            metadata["is_new_in_latest_run"] = first_seen == run_date
            if successful_source_ids and metadata.get("source_id") in successful_source_ids:
                metadata["is_active"] = False
            records[str(source_key)] = job

    for job in current_jobs:
        metadata = job.get("metadata") if isinstance(job, dict) else None
        source_key = metadata.get("source_key") if isinstance(metadata, dict) else None
        if not source_key:
            continue

        previous = records.get(str(source_key))
        first_seen = run_date
        if previous:
            previous_metadata = previous.get("metadata")
            if isinstance(previous_metadata, dict):
                first_seen = str(previous_metadata.get("first_seen_date") or run_date)

        updated_data = dict(job.get("data") or {})
        if previous and preserve_existing_translation:
            previous_data = previous.get("data")
            if isinstance(previous_data, dict):
                for field in TRANSLATED_FIELDS:
                    if field in previous_data:
                        updated_data[field] = previous_data[field]

        updated_job = {
            "metadata": dict(metadata),
            "data": updated_data,
        }
        updated_job["metadata"]["first_seen_date"] = first_seen
        updated_job["metadata"]["last_seen_date"] = run_date
        updated_job["metadata"]["is_new_in_latest_run"] = first_seen == run_date
        updated_job["metadata"]["is_active"] = True
        records[str(source_key)] = updated_job

    return list(records.values())


def update_job_history(
    run_date: str,
    jobs: Iterable[StandardJob],
    *,
    successful_source_ids: set[str] | None = None,
    data_dir: Path = DATA_DIR,
    deliverables_dir: Path | None = None,
) -> Path:
    """Merge a collection onto the latest earlier English history when available."""
    history_path = data_dir / "history" / "jobs_history.json"
    resolved_deliverables_dir = deliverables_dir or data_dir.parent / "deliverables"
    translated_candidates = sorted(
        path
        for path in resolved_deliverables_dir.glob("*/jobs_history_translated.json")
        if path.parent.name < run_date
    )
    translated_path = translated_candidates[-1] if translated_candidates else None

    base_path = translated_path if translated_path else history_path
    if base_path.exists():
        loaded = json.loads(base_path.read_text(encoding="utf-8"))
        history = loaded if isinstance(loaded, list) else []
    else:
        history = []

    current_jobs = [job.to_dict() for job in jobs]
    merged = merge_history_records(
        history,
        current_jobs,
        run_date,
        successful_source_ids,
        preserve_existing_translation=translated_path is not None,
    )
    _write_json(history_path, merged)
    return history_path


def rebuild_job_history(*, data_dir: Path = DATA_DIR) -> Path:
    """Rebuild history from every dated standardized jobs.json file."""
    history: list[dict[str, Any]] = []
    snapshots = sorted((data_dir / "standardized").glob("*/jobs.json"))
    if not snapshots:
        raise FileNotFoundError("No dated jobs.json snapshots were found")

    for snapshot in snapshots:
        loaded = json.loads(snapshot.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            raise ValueError(f"{snapshot} does not contain a JSON job list")
        report_path = data_dir / "run_reports" / snapshot.parent.name / "jobs_report.json"
        successful_source_ids: set[str] = set()
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if isinstance(report, list):
                successful_source_ids = {
                    str(item.get("source_id"))
                    for item in report
                    if isinstance(item, dict) and item.get("status") == "success"
                }
        if not successful_source_ids:
            successful_source_ids = {
                str(job["metadata"]["source_id"])
                for job in loaded
                if isinstance(job, dict)
                and isinstance(job.get("metadata"), dict)
                and job["metadata"].get("source_id")
            }
        history = merge_history_records(
            history,
            loaded,
            snapshot.parent.name,
            successful_source_ids,
        )

    history_path = data_dir / "history" / "jobs_history.json"
    _write_json(history_path, history)
    return history_path
