import pytest

import app.repositories.jobs as jobs_module
from app.repositories.jobs import JobRepository


def test_locations_endpoint(client):
    response = client.get("/api/locations")

    assert response.status_code == 200

    payload = response.get_json()["data"]

    assert payload["releaseId"] == 7
    assert payload["releaseKey"] == "test-release"

    assert payload["locations"][0] == {
        "countryCode": "AU",
        "stateRegion": "WA",
        "city": "Perth",
        "jobCount": 3,
    }

    assert payload["workArrangements"][0]["value"] == "hybrid"


def test_repository_returns_location_options(monkeypatch):
    repository = JobRepository()

    responses = iter(
        [
            [
                {
                    "dashboard_release_id": 7,
                    "release_key": "release-7",
                }
            ],
            [
                {
                    "country_code": "US",
                    "state_region": "CA",
                    "city": "San Francisco",
                    "job_count": 12,
                },
                {
                    "country_code": "US",
                    "state_region": "TX",
                    "city": "Austin",
                    "job_count": 8,
                },
            ],
            [
                {
                    "remote_type": "hybrid",
                    "job_count": 15,
                },
                {
                    "remote_type": "remote",
                    "job_count": 10,
                },
            ],
        ]
    )

    calls = []

    def fake_fetch_all(query, params=None):
        calls.append((query, params))
        return next(responses)

    monkeypatch.setattr(
        jobs_module,
        "fetch_all",
        fake_fetch_all,
    )

    result = repository.list_locations()

    assert result["releaseId"] == 7
    assert result["releaseKey"] == "release-7"

    assert result["locations"] == [
        {
            "countryCode": "US",
            "stateRegion": "CA",
            "city": "San Francisco",
            "jobCount": 12,
        },
        {
            "countryCode": "US",
            "stateRegion": "TX",
            "city": "Austin",
            "jobCount": 8,
        },
    ]

    assert result["workArrangements"] == [
        {
            "value": "hybrid",
            "jobCount": 15,
        },
        {
            "value": "remote",
            "jobCount": 10,
        },
    ]

    # Both option queries must be pinned to release 7.
    assert calls[1][1] == (7,)
    assert calls[2][1] == (7,)

    assert "dashboard_release_id = %s" in calls[1][0]
    assert "dashboard_release_id = %s" in calls[2][0]


def test_locations_reject_mixed_releases(monkeypatch):
    repository = JobRepository()

    monkeypatch.setattr(
        jobs_module,
        "fetch_all",
        lambda query, params=None: [
            {
                "dashboard_release_id": 7,
                "release_key": "release-7",
            },
            {
                "dashboard_release_id": 8,
                "release_key": "release-8",
            },
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="multiple dashboard releases",
    ):
        repository.list_locations()


def test_locations_handles_no_active_release(monkeypatch):
    repository = JobRepository()

    monkeypatch.setattr(
        jobs_module,
        "fetch_all",
        lambda query, params=None: [],
    )

    result = repository.list_locations()

    assert result == {
        "releaseId": None,
        "releaseKey": None,
        "locations": [],
        "workArrangements": [],
    }