from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from av_jobs.models import StandardJob


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def save_raw_snapshot(
    run_date: str,
    source_id: str,
    payload: Any,
) -> Path:
    """Save the unmodified response from one source."""
    output_dir = DATA_DIR / "raw" / run_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{source_id}.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def save_standardized_jobs(
    run_date: str,
    jobs: Iterable[StandardJob],
    filename: str = "jobs.json",
) -> Path:
    """Save all standardized jobs from one pipeline run."""
    output_dir = DATA_DIR / "standardized" / run_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(
        json.dumps([job.to_dict() for job in jobs], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
