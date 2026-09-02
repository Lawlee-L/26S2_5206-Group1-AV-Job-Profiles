from av_jobs.collectors.comeet import (
    comeet_description,
    endpoint_with_details,
    normalize_comeet_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small Comeet source for the tests."""
    return SourceConfig(
        source_id="example_comeet",
        company="Example",
        region="Israel",
        company_url="https://example.com",
        career_url="https://www.comeet.com/jobs/example/12.345",
        platform="comeet",
        transport="json_api",
        method="GET",
        endpoint="https://www.comeet.co/api/positions?token=public&details=false",
        notes="",
    )


def test_comeet_adds_full_details() -> None:
    result = endpoint_with_details(make_source().endpoint)
    assert "token=public" in result
    assert "details=true" in result
    assert "details=false" not in result


def test_comeet_joins_description_sections() -> None:
    raw = {
        "details": [
            {"name": "Requirements", "value": "<p>Know Python.</p>", "order": 2},
            {"name": "Description", "value": "<p>Build AV software.</p>", "order": 1},
            {"name": "Empty", "value": None, "order": 3},
        ]
    }
    assert comeet_description(raw) == (
        "Description\nBuild AV software.\n\nRequirements\nKnow Python."
    )


def test_comeet_mapping() -> None:
    raw = {
        "uid": "0C.F6C",
        "name": "Embedded Software Engineer",
        "url_active_page": "https://www.comeet.com/jobs/example/12.345/job/0C.F6C",
        "location": {"name": "Tel Aviv", "country": "IL"},
        "time_updated": "2026-08-10T09:13:30Z",
        "details": [
            {"name": "Description", "value": "<p>Build embedded systems.</p>", "order": 1}
        ],
    }

    result = normalize_comeet_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "0C.F6C"
    assert result["data"]["advertised_job_title"] == "Embedded Software Engineer"
    assert result["data"]["location"] == "Tel Aviv"
    assert result["data"]["job_description"] == "Description\nBuild embedded systems."
    assert result["data"]["date_posted"] is None
