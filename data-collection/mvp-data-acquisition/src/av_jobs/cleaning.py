"""Deterministic text cleaning, deduplication and history merging."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC
from html import unescape

import pandas as pd
from bs4 import BeautifulSoup

from .models import RawJob

WHITESPACE_RE = re.compile(r"\s+")


def normalise_text(value: str | None) -> str | None:
    """Normalise Unicode and whitespace while preserving source wording."""

    if value is None:
        return None
    value = unicodedata.normalize("NFKC", value)
    value = WHITESPACE_RE.sub(" ", value).strip()
    return value or None


def html_to_text(value: str) -> str:
    """Convert source HTML or entity-escaped HTML to compact plain text.

    Some ATS APIs return markup encoded as text (for example, ``&lt;p&gt;``).
    Decode at most twice before parsing so normal source text is retained while
    escaped tags do not leak into downstream CSV, Parquet or DuckDB fields.
    """

    decoded = value
    for _ in range(2):
        unescaped = unescape(decoded)
        if unescaped == decoded:
            break
        decoded = unescaped
    soup = BeautifulSoup(decoded, "html.parser")
    return normalise_text(soup.get_text(" ", strip=True)) or ""


def utc_timestamp(value):
    """Convert supported source timestamps to pandas UTC timestamps."""

    if value is None:
        return pd.NaT
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(UTC)
    return timestamp.tz_convert(UTC)


def job_to_record(job: RawJob, snapshot_run_id: str) -> dict:
    """Convert a validated raw job into the processed column contract."""

    description = html_to_text(job.description_raw)
    scraped_at = utc_timestamp(job.scraped_at)
    return {
        "snapshot_run_id": snapshot_run_id,
        "collected_run_id": job.run_id,
        "source_job_id": normalise_text(job.source_job_id),
        "company": normalise_text(job.company),
        "original_title": normalise_text(job.original_title),
        "location_raw": normalise_text(job.location_raw),
        "description_text": description,
        "employment_type": normalise_text(job.employment_type),
        "department": normalise_text(job.department),
        "team": normalise_text(job.team),
        "workplace_type": normalise_text(job.workplace_type),
        "salary_raw": normalise_text(job.salary_raw),
        "posted_at_utc": utc_timestamp(job.posted_at),
        "updated_at_utc": utc_timestamp(job.updated_at),
        "source_url": str(job.source_url),
        "source_type": job.source_type,
        "source_name": job.source_name,
        "scraped_at_utc": scraped_at,
        "first_seen_utc": scraped_at,
        "last_seen_utc": scraped_at,
        "status": "active",
        "is_active": True,
        "description_word_count": len(description.split()),
        "description_character_count": len(description),
        "content_hash": job.content_hash,
    }


def clean_current_jobs(jobs: list[RawJob], snapshot_run_id: str) -> pd.DataFrame:
    """Clean and deduplicate the jobs observed in the current run."""

    if not jobs:
        raise ValueError("No validated jobs were supplied to pandas cleaning")
    frame = pd.DataFrame(job_to_record(job, snapshot_run_id) for job in jobs)
    frame = frame.drop_duplicates(subset=["company", "source_job_id"], keep="first")
    frame = frame.sort_values(
        ["company", "original_title", "source_job_id"], kind="stable"
    ).reset_index(drop=True)
    return frame


def merge_history(
    current: pd.DataFrame,
    previous: pd.DataFrame | None,
    *,
    refreshed_companies: set[str],
    snapshot_run_id: str,
) -> pd.DataFrame:
    """Carry history forward and mark disappeared jobs inactive.

    Sources not refreshed by this run are copied unchanged. This makes small
    smoke runs safe: they cannot accidentally mark every unselected company as
    inactive.
    """

    if previous is None or previous.empty:
        return current.reset_index(drop=True)

    previous = previous.copy()
    for column in (
        "posted_at_utc",
        "updated_at_utc",
        "scraped_at_utc",
        "first_seen_utc",
        "last_seen_utc",
    ):
        previous[column] = pd.to_datetime(previous[column], utc=True, errors="coerce")

    key_columns = ["company", "source_job_id"]
    previous_by_key = {
        (row["company"], row["source_job_id"]): row for _, row in previous.iterrows()
    }
    current_keys: set[tuple[str, str]] = set()
    current_rows: list[dict] = []
    for _, row in current.iterrows():
        record = row.to_dict()
        key = (record["company"], record["source_job_id"])
        current_keys.add(key)
        old = previous_by_key.get(key)
        if old is not None:
            record["first_seen_utc"] = old["first_seen_utc"]
        current_rows.append(record)

    carried_rows: list[dict] = []
    for _, row in previous.iterrows():
        record = row.to_dict()
        key = (record["company"], record["source_job_id"])
        if key in current_keys:
            continue
        record["snapshot_run_id"] = snapshot_run_id
        if record["company"] in refreshed_companies:
            record["status"] = "inactive"
            record["is_active"] = False
        carried_rows.append(record)

    combined = pd.DataFrame(current_rows + carried_rows)
    combined = combined.drop_duplicates(subset=key_columns, keep="first")
    return combined.sort_values(
        ["company", "is_active", "original_title", "source_job_id"],
        ascending=[True, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
