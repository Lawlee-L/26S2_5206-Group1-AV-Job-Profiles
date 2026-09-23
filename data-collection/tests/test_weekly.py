import json
from pathlib import Path

from av_jobs.pipeline import SourceRunResult
from av_jobs.weekly import run_weekly_workflow


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def make_record(source_key: str, title: str) -> dict:
    return {
        "metadata": {
            "source_key": source_key,
            "company": "Example",
            "first_seen_date": "2026-09-26",
            "last_seen_date": "2026-09-26",
            "is_active": True,
            "is_new_in_latest_run": True,
        },
        "data": {
            "advertised_job_title": title,
            "job_description": "English description",
            "location": "Perth, Australia",
        },
    }


def test_weekly_workflow_merges_passed_and_retains_review_original(tmp_path) -> None:
    data_dir = tmp_path / "data"
    deliverables_dir = tmp_path / "deliverables"
    history = [
        make_record("job-1", "软件工程师"),
        make_record("job-2", "会计师"),
    ]

    def fake_collect(*, run_date):
        write_json(data_dir / "history" / "jobs_history.json", history)
        output = data_dir / "standardized" / run_date / "jobs.json"
        write_json(output, [])
        results = [
            SourceRunResult("example", "Example", "test", "success", 2)
        ]
        return [], results, output

    def fake_translate(texts: list[str]) -> list[str]:
        return ["Software Engineer" if text == "软件工程师" else text for text in texts]

    result = run_weekly_workflow(
        region="australiaeast",
        run_date="2026-09-26",
        data_dir=data_dir,
        deliverables_dir=deliverables_dir,
        collect_pipeline=fake_collect,
        translate_chunks=fake_translate,
    )

    final = json.loads(result.deliverable_path.read_text(encoding="utf-8"))
    assert final[0]["data"]["advertised_job_title"] == "Software Engineer"
    assert final[1]["data"]["advertised_job_title"] == "会计师"
    assert result.translation_records == 2
    assert result.review_records == 1

    review_path = (
        data_dir / "translation" / "2026-09-26" / "translation_result.review.json"
    )
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review[0]["source_key"] == "job-2"
    assert review[0]["failed_fields"] == ["advertised_job_title"]


def test_weekly_workflow_skips_azure_when_history_is_already_english(tmp_path) -> None:
    data_dir = tmp_path / "data"
    deliverables_dir = tmp_path / "deliverables"
    history = [make_record("job-1", "Software Engineer")]
    work_dir = data_dir / "translation" / "2026-09-26"
    write_json(work_dir / "translation_result.partial.json", [{"old": True}])
    write_json(work_dir / "translation_result.passed.json", [{"old": True}])
    write_json(work_dir / "translation_result.review.json", [{"old": True}])

    def fake_collect(*, run_date):
        write_json(data_dir / "history" / "jobs_history.json", history)
        output = data_dir / "standardized" / run_date / "jobs.json"
        write_json(output, [])
        results = [
            SourceRunResult("example", "Example", "test", "success", 1)
        ]
        return [], results, output

    def unexpected_translate(texts: list[str]) -> list[str]:
        raise AssertionError("Azure should not run for an English-only history")

    result = run_weekly_workflow(
        region="australiaeast",
        run_date="2026-09-26",
        data_dir=data_dir,
        deliverables_dir=deliverables_dir,
        collect_pipeline=fake_collect,
        translate_chunks=unexpected_translate,
    )

    assert result.translation_records == 0
    assert result.review_records == 0
    assert json.loads(result.deliverable_path.read_text(encoding="utf-8")) == history
    assert not (work_dir / "translation_result.partial.json").exists()
    assert not (work_dir / "translation_result.passed.json").exists()
    assert not (work_dir / "translation_result.review.json").exists()
