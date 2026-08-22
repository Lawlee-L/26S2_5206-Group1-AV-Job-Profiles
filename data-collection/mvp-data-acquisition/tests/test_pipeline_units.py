"""Unit tests for cleaning, history, quality gates and analytical storage."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from av_jobs.cleaning import clean_current_jobs, merge_history
from av_jobs.exports import TEAM_CSV_COLUMNS, export_team_jobs_csv
from av_jobs.models import RawJob, SourceStatus
from av_jobs.quality import build_quality_report
from av_jobs.storage import (
    build_duckdb,
    load_latest_jobs,
    publish_latest,
    write_parquet,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sample_job(
    *, run_id: str, scraped_at: str, description: str = "Build AV systems"
) -> RawJob:
    return RawJob(
        source_job_id="job-123",
        company="Kodiak",
        original_title=" Senior Software Engineer, Perception ",
        location_raw=" Mountain View, CA ",
        description_raw=f"<p>{description} with Python and C++.</p>",
        source_url="https://job-boards.greenhouse.io/kodiak/jobs/123",
        posted_at="2026-08-01T00:00:00Z",
        updated_at="2026-08-02T00:00:00Z",
        source_name="greenhouse",
        scraped_at=scraped_at,
        run_id=run_id,
    ).with_content_hash()


def status_frame(run_id: str) -> pd.DataFrame:
    status = SourceStatus(
        run_id=run_id,
        spider="kodiak",
        company="Kodiak",
        source_name="greenhouse",
        finish_reason="finished",
        source_items_seen=1,
        validated_items=1,
        validation_errors=0,
        response_count=1,
        response_errors=0,
        snapshot_files=1,
        status="success",
    )
    return pd.DataFrame([status.model_dump(mode="json")])


def test_clean_history_parquet_and_duckdb(tmp_path: Path) -> None:
    first = clean_current_jobs(
        [sample_job(run_id="run-1", scraped_at="2026-08-20T00:00:00Z")],
        "run-1",
    )
    second_current = clean_current_jobs(
        [
            sample_job(
                run_id="run-2",
                scraped_at="2026-08-21T00:00:00Z",
                description="Build safer AV perception",
            )
        ],
        "run-2",
    )
    second = merge_history(
        second_current,
        first,
        refreshed_companies={"Kodiak"},
        snapshot_run_id="run-2",
    )
    assert len(second) == 1
    assert second.loc[0, "first_seen_utc"] == pd.Timestamp("2026-08-20T00:00:00Z")
    assert second.loc[0, "last_seen_utc"] == pd.Timestamp("2026-08-21T00:00:00Z")
    assert second.loc[0, "original_title"] == "Senior Software Engineer, Perception"
    assert second.loc[0, "is_active"]

    statuses = status_frame("run-2")
    report = build_quality_report(second, statuses, {"Kodiak"})
    assert report["passed"]

    jobs_path = tmp_path / "jobs.parquet"
    status_path = tmp_path / "source_status.parquet"
    database_path = tmp_path / "jobs.duckdb"
    write_parquet(second, jobs_path)
    write_parquet(statuses, status_path)
    summary = build_duckdb(jobs_path, status_path, database_path)
    assert summary["active_jobs"] == 1
    with duckdb.connect(str(database_path), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM active_jobs").fetchone()[0] == 1


def test_disappeared_job_becomes_inactive() -> None:
    previous = clean_current_jobs(
        [sample_job(run_id="run-1", scraped_at="2026-08-20T00:00:00Z")],
        "run-1",
    )
    other = sample_job(run_id="run-2", scraped_at="2026-08-21T00:00:00Z")
    other = other.model_copy(
        update={
            "source_job_id": "job-999",
            "source_url": "https://job-boards.greenhouse.io/kodiak/jobs/999",
        }
    ).with_content_hash()
    current = clean_current_jobs([other], "run-2")
    combined = merge_history(
        current,
        previous,
        refreshed_companies={"Kodiak"},
        snapshot_run_id="run-2",
    )
    assert len(combined) == 2
    assert set(combined["status"]) == {"active", "inactive"}


def test_partial_refresh_preserves_unselected_company_state() -> None:
    previous = clean_current_jobs(
        [sample_job(run_id="run-1", scraped_at="2026-08-20T00:00:00Z")],
        "run-1",
    )
    current_job = sample_job(run_id="run-2", scraped_at="2026-08-21T00:00:00Z")
    current_job = current_job.model_copy(
        update={
            "company": "Zoox",
            "source_job_id": "zoox-1",
            "source_name": "lever",
            "source_url": "https://jobs.lever.co/zoox/zoox-1",
        }
    ).with_content_hash()
    current = clean_current_jobs([current_job], "run-2")
    combined = merge_history(
        current,
        previous,
        refreshed_companies={"Zoox"},
        snapshot_run_id="run-2",
    )
    kodiak = combined.loc[combined["company"] == "Kodiak"].iloc[0]
    assert kodiak["status"] == "active"
    assert bool(kodiak["is_active"])


def test_quality_gate_rejects_failed_source() -> None:
    frame = clean_current_jobs(
        [sample_job(run_id="run-1", scraped_at="2026-08-20T00:00:00Z")],
        "run-1",
    )
    statuses = status_frame("run-1")
    statuses.loc[0, "status"] = "failed"
    report = build_quality_report(frame, statuses, {"Kodiak"})
    assert not report["passed"]
    assert report["failed_sources"] == ["kodiak"]


def test_relative_latest_manifest_can_be_reopened(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    jobs_path = project_root / "data" / "processed" / "run_id=test" / "jobs.parquet"
    frame = clean_current_jobs(
        [sample_job(run_id="test", scraped_at="2026-08-20T00:00:00Z")],
        "test",
    )
    write_parquet(frame, jobs_path)
    manifest = project_root / "data" / "published" / "latest.json"
    publish_latest(
        manifest,
        {"jobs_parquet": "data/processed/run_id=test/jobs.parquet"},
    )
    reopened = load_latest_jobs(manifest)
    assert reopened is not None
    assert len(reopened) == 1


def test_team_csv_export_has_excel_safe_contract(tmp_path: Path) -> None:
    database_path = tmp_path / "jobs.duckdb"
    output_path = tmp_path / "jobs.csv"
    with duckdb.connect(str(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE active_jobs AS
            SELECT
                'ACME, Inc.'::VARCHAR AS company,
                'Engineer "AV"'::VARCHAR AS original_title,
                '=Line one\nLine two, with comma'::VARCHAR AS description_text,
                TIMESTAMPTZ '2026-08-22 08:30:00+08:00' AS posted_at_utc,
                'job-1'::VARCHAR AS source_job_id
            """
        )

    row_count = export_team_jobs_csv(database_path, output_path)

    assert row_count == 1
    assert output_path.read_bytes().startswith(b"\xef\xbb\xbf")
    frame = pd.read_csv(output_path, encoding="utf-8-sig")
    assert tuple(frame.columns) == TEAM_CSV_COLUMNS
    assert frame.iloc[0].to_dict() == {
        "company": "ACME, Inc.",
        "name": 'Engineer "AV"',
        "description": "'=Line one\nLine two, with comma",
        "date_posted": "2026-08-22T00:30:00Z",
    }


def test_team_csv_export_rejects_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "empty.duckdb"
    with duckdb.connect(str(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE active_jobs (
                company VARCHAR,
                original_title VARCHAR,
                description_text VARCHAR,
                posted_at_utc TIMESTAMPTZ,
                source_job_id VARCHAR
            )
            """
        )

    with pytest.raises(ValueError, match="contains no rows"):
        export_team_jobs_csv(database_path, tmp_path / "empty.csv")
