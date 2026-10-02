import pytest

import app.repositories.jobs as jobs_module
from app.repositories.jobs import JobRepository, _detail_array


def test_detail_array_accepts_json_array():
    value = '["Python", "C++", "ROS"]'

    assert _detail_array(value) == [
        "Python",
        "C++",
        "ROS",
    ]


def test_detail_array_none_becomes_empty_list():
    assert _detail_array(None) == []


def test_detail_array_rejects_invalid_structure():
    with pytest.raises(ValueError):
        _detail_array('{"skill": "Python"}')


def test_candidate_job_returns_empty_detail_fields(monkeypatch):
    repository = JobRepository("candidate")

    monkeypatch.setattr(
        jobs_module,
        "fetch_one",
        lambda query, params: {
            "job_id": 101,
            "source_key": "test|job|101",
            "dashboard_release_id": 7,
        },
    )

    monkeypatch.setattr(
        repository,
        "_skills_for_job_ids",
        lambda job_ids: {101: []},
    )

    monkeypatch.setattr(
        repository,
        "_job_to_api",
        lambda row, skills: {
            "id": row["source_key"],
            "jobId": row["job_id"],
        },
    )

    result = repository.get_job("test|job|101")

    assert result["description"] is None
    assert result["roleSummary"] is None
    assert result["responsibilities"] == []
    assert result["requirements"] == []
    assert result["detailSnapshotAvailable"] is False


def test_published_job_adds_frozen_details(monkeypatch):
    repository = JobRepository("published")

    responses = iter(
        [
            {
                "job_id": 101,
                "source_key": "test|job|101",
                "dashboard_release_id": 7,
            },
            {
                "job_description": "Original collected description",
                "role_summary": "Autonomous vehicle software role",
                "responsibilities_json": '["Develop planning software"]',
                "requirements_json": '["Python", "C++"]',
                "detail_snapshot_available": 1,
            },
        ]
    )

    calls = []

    def fake_fetch_one(query, params):
        calls.append((query, params))
        return next(responses)

    monkeypatch.setattr(
        jobs_module,
        "fetch_one",
        fake_fetch_one,
    )

    monkeypatch.setattr(
        repository,
        "_skills_for_job_ids",
        lambda job_ids: {101: []},
    )

    monkeypatch.setattr(
        repository,
        "_job_to_api",
        lambda row, skills: {
            "id": row["source_key"],
            "jobId": row["job_id"],
        },
    )

    result = repository.get_job("test|job|101")

    assert result["description"] == "Original collected description"
    assert result["roleSummary"] == "Autonomous vehicle software role"
    assert result["responsibilities"] == [
        "Develop planning software"
    ]
    assert result["requirements"] == [
        "Python",
        "C++",
    ]
    assert result["detailSnapshotAvailable"] is True

    # The detail lookup must use the same release and job.
    assert calls[1][1] == (7, 101)


def test_missing_detail_row_does_not_remove_job(monkeypatch):
    repository = JobRepository("published")

    responses = iter(
        [
            {
                "job_id": 101,
                "source_key": "test|job|101",
                "dashboard_release_id": 7,
            },
            None,
        ]
    )

    monkeypatch.setattr(
        jobs_module,
        "fetch_one",
        lambda query, params: next(responses),
    )

    monkeypatch.setattr(
        repository,
        "_skills_for_job_ids",
        lambda job_ids: {101: []},
    )

    monkeypatch.setattr(
        repository,
        "_job_to_api",
        lambda row, skills: {
            "id": row["source_key"],
            "jobId": row["job_id"],
        },
    )

    result = repository.get_job("test|job|101")

    assert result is not None
    assert result["description"] is None
    assert result["roleSummary"] is None
    assert result["responsibilities"] == []
    assert result["requirements"] == []
    assert result["detailSnapshotAvailable"] is False