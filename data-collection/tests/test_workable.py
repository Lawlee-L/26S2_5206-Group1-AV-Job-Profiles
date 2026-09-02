from av_jobs.collectors.workable import normalize_workable_job, workable_salary
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small Workable source for the tests."""
    return SourceConfig(
        source_id="example_us_workable",
        company="Example",
        region="US",
        company_url="https://example.com",
        career_url="https://apply.workable.com/example",
        platform="workable",
        transport="json_api",
        method="GET",
        endpoint="https://www.workable.com/api/accounts/example?details=true",
        notes="",
    )


def test_workable_mapping() -> None:
    raw = {
        "title": "Autonomous Driving Engineer",
        "shortcode": "ABC123",
        "url": "https://apply.workable.com/j/ABC123",
        "published_on": "2026-09-01",
        "locations": [
            {
                "city": "Fremont",
                "region": "California",
                "country": "United States",
                "hidden": False,
            }
        ],
        "description": "<p>Build driving software.</p><p>Annual salary is $130,000.</p>",
    }

    result = normalize_workable_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "ABC123"
    assert result["data"]["advertised_job_title"] == "Autonomous Driving Engineer"
    assert result["data"]["location"] == "Fremont, California, United States"
    assert result["data"]["salary"] == "Annual salary is $130,000."
    assert result["data"]["date_posted"] == "2026-09-01"


def test_workable_joins_multiple_locations() -> None:
    raw = {
        "title": "Engineer",
        "shortcode": "XYZ789",
        "locations": [
            {"city": "Fremont", "country": "United States", "hidden": False},
            {"city": "Remote", "country": "United States", "hidden": False},
            {"city": "Secret", "country": "United States", "hidden": True},
        ],
    }

    result = normalize_workable_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
    ).to_dict()

    assert result["data"]["location"] == "Fremont, United States; Remote, United States"


def test_workable_salary_requires_a_number() -> None:
    description = "We offer competitive compensation and useful benefits."
    assert workable_salary(description) is None
