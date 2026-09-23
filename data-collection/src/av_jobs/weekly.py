from __future__ import annotations

import getpass
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from av_jobs.pipeline import SourceRunResult, run_pipeline
from av_jobs.storage import DATA_DIR, PROJECT_ROOT
from av_jobs.translation.azure import (
    DEFAULT_ENDPOINT,
    _find_failed_fields,
    _request_translation,
    translate_source_batch,
)
from av_jobs.translation.workflow import (
    merge_translation_batch,
    prepare_translation_batch,
)


@dataclass(slots=True)
class WeeklyWorkflowResult:
    run_date: str
    deliverable_path: Path
    collected_jobs: int
    translation_records: int
    review_records: int


def _load_list(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path} does not contain a JSON list")
    return loaded


def _write_list(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def merge_completed_translations(
    history: list[dict[str, Any]],
    source_batch: list[dict[str, Any]],
    translated_batch: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge valid translations and leave review records unchanged."""
    failed = _find_failed_fields(translated_batch)
    passed = [
        item
        for item in translated_batch
        if str(item.get("source_key")) not in failed
    ]
    passed_keys = {str(item["source_key"]) for item in passed}
    passed_source = [
        item for item in source_batch if str(item.get("source_key")) in passed_keys
    ]
    review = [
        {
            **item,
            "failed_fields": sorted(failed[str(item["source_key"])]),
        }
        for item in translated_batch
        if str(item.get("source_key")) in failed
    ]

    if not passed:
        return deepcopy(history), passed, review
    merged = merge_translation_batch(history, passed_source, passed)
    return merged, passed, review


def run_weekly_workflow(
    *,
    region: str,
    run_date: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    data_dir: Path = DATA_DIR,
    deliverables_dir: Path | None = None,
    collect_pipeline: Callable[..., tuple[list[Any], list[SourceRunResult], Path]] = run_pipeline,
    translate_chunks: Callable[[list[str]], list[str]] | None = None,
) -> WeeklyWorkflowResult:
    """Run collection, Azure translation, validation, and final history output."""
    resolved_date = run_date or date.today().isoformat()
    resolved_deliverables = deliverables_dir or PROJECT_ROOT / "deliverables"

    jobs, source_results, standardized_path = collect_pipeline(run_date=resolved_date)
    for result in source_results:
        suffix = f" ({result.error})" if result.error else ""
        print(
            f"{result.source_id}: {result.status}, "
            f"{result.job_count} jobs{suffix}"
        )
    successful_sources = [
        result for result in source_results if result.status == "success"
    ]
    if not successful_sources:
        raise RuntimeError("Weekly collection produced no successful sources")

    failed_sources = [result for result in source_results if result.status == "failed"]
    if failed_sources:
        print(
            f"[WARNING] {len(failed_sources)} source(s) failed. "
            "Their previous history records remain unchanged."
        )

    history_path = data_dir / "history" / "jobs_history.json"
    history = _load_list(history_path)
    source_batch = prepare_translation_batch(history)

    work_dir = data_dir / "translation" / resolved_date
    source_path = work_dir / "translation_source.json"
    result_path = work_dir / "translation_result.json"
    partial_path = work_dir / "translation_result.partial.json"
    passed_path = work_dir / "translation_result.passed.json"
    review_path = work_dir / "translation_result.review.json"

    # Resume only when the prepared source batch is exactly the same.
    previous_source = _load_list(source_path) if source_path.exists() else None
    existing = (
        _load_list(partial_path)
        if previous_source == source_batch and partial_path.exists()
        else []
    )
    if partial_path.exists() and previous_source != source_batch:
        print("Existing translation checkpoint does not match this batch; starting fresh.")
    _write_list(source_path, source_batch)

    translated_batch: list[dict[str, Any]] = []
    if source_batch:
        if translate_chunks is None:
            key = getpass.getpass("Paste Azure Translator KEY 1 (hidden): ").strip()
            if not key:
                raise ValueError("Azure Translator key is required")

            def translate_chunks(texts: list[str]) -> list[str]:
                return _request_translation(
                    texts,
                    key=key,
                    region=region,
                    endpoint=endpoint,
                )

        try:
            translated_batch = translate_source_batch(
                source_batch,
                translate_chunks,
                existing=existing,
                checkpoint=lambda records: _write_list(partial_path, records),
            )
        except ValueError as error:
            if not str(error).startswith("Non-English content remains"):
                raise
            translated_batch = _load_list(partial_path)
    else:
        partial_path.unlink(missing_ok=True)
    _write_list(result_path, translated_batch)

    merged, passed, review = merge_completed_translations(
        history,
        source_batch,
        translated_batch,
    )
    if review:
        _write_list(passed_path, passed)
        _write_list(review_path, review)
        for item in review:
            print(
                f"[WARNING] source_key={item['source_key']}; "
                f"fields={','.join(item['failed_fields'])}; "
                "original content was retained."
            )
    else:
        # Remove review files left by an earlier same-day attempt.
        passed_path.unlink(missing_ok=True)
        review_path.unlink(missing_ok=True)

    deliverable_path = (
        resolved_deliverables / resolved_date / "jobs_history_translated.json"
    )
    _write_list(deliverable_path, merged)

    print(f"Standardized jobs: {len(jobs)}")
    print(f"Standardized output: {standardized_path}")
    print(f"Translation records: {len(source_batch)}")
    print(f"Records needing review: {len(review)}")
    print(f"Final deliverable: {deliverable_path}")
    return WeeklyWorkflowResult(
        run_date=resolved_date,
        deliverable_path=deliverable_path,
        collected_jobs=len(jobs),
        translation_records=len(source_batch),
        review_records=len(review),
    )
