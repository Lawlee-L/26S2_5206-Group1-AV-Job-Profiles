from av_jobs.collectors.greenhouse import endpoint_with_content, normalize_greenhouse_job
from av_jobs.config import SourceConfig


def test_greenhouse_mapping() -> None:
    source = SourceConfig(
        source_id="example_greenhouse",
        company="Example",
        region="USA",
        company_url="https://example.com",
        career_url="https://example.com/careers",
        platform="greenhouse",
        transport="json_api",
        method="GET",
        endpoint="https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true",
        notes="",
    )
    raw = {
        "id": 123,
        "title": "Software Engineer",
        "content": "<p>Build <strong>safe</strong> systems.</p>",
        "absolute_url": "https://example.com/jobs/123",
        "location": {"name": "Austin, TX"},
        "first_published": "2026-09-01T00:00:00Z",
        "metadata": [{"name": "Salary Range", "value": "$100,000-$120,000"}],
    }
    job = normalize_greenhouse_job(raw, source, "2026-09-02T00:00:00+00:00")
    result = job.to_dict()
    assert result["metadata"]["source_job_id"] == "123"
    assert result["data"]["advertised_job_title"] == "Software Engineer"
    assert result["data"]["job_description"] == "Build\nsafe\nsystems."
    assert result["data"]["location"] == "Austin, TX"
    assert result["data"]["salary"] == "Salary Range: $100,000-$120,000"


def test_greenhouse_endpoint_always_requests_content() -> None:
    assert endpoint_with_content(
        "https://boards-api.greenhouse.io/v1/boards/vay/jobs"
    ).endswith("?content=true")
    assert "content=true" in endpoint_with_content(
        "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=false"
    )
