import json
from dataclasses import replace
from pathlib import Path

from av_jobs.models import JobData, JobMetadata, StandardJob
from av_jobs.storage import merge_history_records, rebuild_job_history, update_job_history


def make_job(source_key: str, title: str, collected_at: str) -> StandardJob:
    return StandardJob(
        metadata=JobMetadata(
            source_id="example_greenhouse",
            platform="greenhouse",
            company="Example",
            region="Global",
            source_job_id=source_key,
            source_key=source_key,
            collected_at=collected_at,
        ),
        data=JobData(
            advertised_job_title=title,
            job_description="Description",
            job_url=f"https://example.com/{source_key}",
            location="Perth",
            salary=None,
            date_posted=None,
        ),
    )


def test_history_keeps_old_jobs_and_adds_new_jobs(tmp_path: Path) -> None:
    first_job = make_job("job-1", "First title", "2026-09-01T00:00:00Z")
    update_job_history("2026-09-01", [first_job], data_dir=tmp_path)

    second_job = make_job("job-2", "Second title", "2026-09-08T00:00:00Z")
    path = update_job_history(
        "2026-09-08",
        [second_job],
        successful_source_ids={"example_greenhouse"},
        data_dir=tmp_path,
    )
    history = json.loads(path.read_text(encoding="utf-8"))

    assert len(history) == 2
    assert {job["metadata"]["source_key"] for job in history} == {"job-1", "job-2"}
    old_job = next(job for job in history if job["metadata"]["source_key"] == "job-1")
    assert old_job["metadata"]["last_seen_date"] == "2026-09-01"
    assert old_job["metadata"]["is_active"] is False
    new_job = next(job for job in history if job["metadata"]["source_key"] == "job-2")
    assert new_job["metadata"]["is_new_in_latest_run"] is True


def test_history_updates_existing_job_without_a_duplicate() -> None:
    old = make_job("job-1", "Old title", "2026-09-01T00:00:00Z").to_dict()
    old["metadata"]["first_seen_date"] = "2026-09-01"
    old["metadata"]["last_seen_date"] = "2026-09-01"
    current = make_job("job-1", "Updated title", "2026-09-08T00:00:00Z").to_dict()

    history = merge_history_records(
        [old],
        [current],
        "2026-09-08",
        {"example_greenhouse"},
    )

    assert len(history) == 1
    assert history[0]["data"]["advertised_job_title"] == "Updated title"
    assert history[0]["metadata"]["first_seen_date"] == "2026-09-01"
    assert history[0]["metadata"]["last_seen_date"] == "2026-09-08"
    assert history[0]["metadata"]["is_active"] is True
    assert history[0]["metadata"]["is_new_in_latest_run"] is False


def test_same_day_rerun_preserves_new_job_flag() -> None:
    first_run = make_job("job-1", "First title", "2026-09-13T01:00:00Z").to_dict()
    first_history = merge_history_records([], [first_run], "2026-09-13")

    retry = make_job("job-1", "Updated title", "2026-09-13T02:00:00Z").to_dict()
    history = merge_history_records(
        first_history,
        [retry],
        "2026-09-13",
        {"example_greenhouse"},
    )

    assert len(history) == 1
    assert history[0]["data"]["advertised_job_title"] == "Updated title"
    assert history[0]["metadata"]["first_seen_date"] == "2026-09-13"
    assert history[0]["metadata"]["last_seen_date"] == "2026-09-13"
    assert history[0]["metadata"]["is_new_in_latest_run"] is True
    assert history[0]["metadata"]["is_active"] is True


def test_weekly_history_reuses_previous_english_translation(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    deliverables_dir = tmp_path / "deliverables"
    translated_path = (
        deliverables_dir / "2026-09-13" / "jobs_history_translated.json"
    )
    translated_path.parent.mkdir(parents=True)

    translated_old = make_job(
        "job-1",
        "Control Algorithm Engineer",
        "2026-09-13T00:00:00Z",
    ).to_dict()
    translated_old["data"]["job_description"] = "English description"
    translated_old["data"]["location"] = "Shanghai"
    translated_old["metadata"]["first_seen_date"] = "2026-09-13"
    translated_old["metadata"]["last_seen_date"] = "2026-09-13"
    translated_path.write_text(json.dumps([translated_old]), encoding="utf-8")

    current_old = make_job(
        "job-1",
        "控制算法工程师",
        "2026-09-19T00:00:00Z",
    )
    current_old = replace(
        current_old,
        data=replace(
            current_old.data,
            job_description="中文描述",
            location="上海市",
            job_url="https://example.com/job-1-updated",
        ),
    )
    current_new = make_job(
        "job-2",
        "新岗位",
        "2026-09-19T00:00:00Z",
    )

    path = update_job_history(
        "2026-09-19",
        [current_old, current_new],
        successful_source_ids={"example_greenhouse"},
        data_dir=data_dir,
        deliverables_dir=deliverables_dir,
    )
    history = json.loads(path.read_text(encoding="utf-8"))
    by_key = {item["metadata"]["source_key"]: item for item in history}

    assert by_key["job-1"]["data"]["advertised_job_title"] == "Control Algorithm Engineer"
    assert by_key["job-1"]["data"]["job_description"] == "English description"
    assert by_key["job-1"]["data"]["location"] == "Shanghai"
    assert by_key["job-1"]["data"]["job_url"] == "https://example.com/job-1-updated"
    assert by_key["job-1"]["metadata"]["last_seen_date"] == "2026-09-19"
    assert by_key["job-1"]["metadata"]["is_new_in_latest_run"] is False
    assert by_key["job-2"]["data"]["advertised_job_title"] == "新岗位"
    assert by_key["job-2"]["metadata"]["is_new_in_latest_run"] is True


def test_rebuild_history_combines_existing_snapshots(tmp_path: Path) -> None:
    first_path = tmp_path / "standardized" / "2026-09-01" / "jobs.json"
    second_path = tmp_path / "standardized" / "2026-09-08" / "jobs.json"
    first_path.parent.mkdir(parents=True)
    second_path.parent.mkdir(parents=True)
    first_path.write_text(
        json.dumps([make_job("job-1", "First", "2026-09-01T00:00:00Z").to_dict()]),
        encoding="utf-8",
    )
    second_path.write_text(
        json.dumps([make_job("job-2", "Second", "2026-09-08T00:00:00Z").to_dict()]),
        encoding="utf-8",
    )

    history_path = rebuild_job_history(data_dir=tmp_path)
    history = json.loads(history_path.read_text(encoding="utf-8"))

    assert len(history) == 2
