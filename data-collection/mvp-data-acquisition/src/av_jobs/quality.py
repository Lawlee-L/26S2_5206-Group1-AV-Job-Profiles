"""Data-quality gates for candidate processed snapshots."""

from __future__ import annotations

import pandas as pd


def _blank_count(series: pd.Series) -> int:
    """Count null and whitespace-only values without double-counting nulls."""

    nulls = series.isna()
    blanks = series.astype("string").str.strip().eq("").fillna(False)
    return int((nulls | blanks).sum())


def build_quality_report(
    frame: pd.DataFrame,
    source_status: pd.DataFrame,
    selected_companies: set[str],
) -> dict:
    """Evaluate the strict publication gates for one candidate snapshot."""

    active = frame[frame["is_active"]]
    required_columns = (
        "source_job_id",
        "company",
        "original_title",
        "description_text",
        "source_url",
    )
    missing_required = {
        column: _blank_count(active[column]) for column in required_columns
    }
    duplicate_active_keys = int(
        active.duplicated(subset=["company", "source_job_id"]).sum()
    )
    failed_sources = source_status.loc[
        source_status["status"] != "success", "spider"
    ].tolist()
    missing_companies = sorted(
        selected_companies - set(active["company"].dropna().unique())
    )
    passed = (
        not failed_sources
        and not missing_companies
        and duplicate_active_keys == 0
        and all(value == 0 for value in missing_required.values())
    )
    return {
        "passed": passed,
        "active_jobs": int(len(active)),
        "all_historical_jobs": int(len(frame)),
        "missing_required": missing_required,
        "duplicate_active_keys": duplicate_active_keys,
        "failed_sources": failed_sources,
        "missing_companies": missing_companies,
    }
