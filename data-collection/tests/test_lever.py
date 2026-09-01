from av_jobs.collectors.lever import normalize_lever_job
from av_jobs.config import SourceConfig


def test_lever_mapping() -> None:
    source = SourceConfig(
        source_id="example_lever",
        company="Example",
        region="USA",
        company_url="https://example.com",
        career_url="https://jobs.lever.co/example",
        platform="lever",
        transport="json_api",
        method="GET",
        endpoint="https://api.lever.co/v0/postings/example",
        notes="",
    )
    raw = {
        "id": "abc-123",
        "text": "Autonomy Engineer",
        "descriptionPlain": "Build autonomous systems.",
        "hostedUrl": "https://jobs.lever.co/example/abc-123",
        "categories": {"location": "Toronto, Canada"},
        "salaryRange": {"min": 100000, "max": 120000, "currency": "CAD", "interval": "year"},
        "createdAt": 1788278400000,
    }
    result = normalize_lever_job(raw, source, "2026-09-02T00:00:00+00:00").to_dict()
    assert result["metadata"]["source_job_id"] == "abc-123"
    assert result["data"]["advertised_job_title"] == "Autonomy Engineer"
    assert result["data"]["location"] == "Toronto, Canada"
    assert result["data"]["salary"] == "CAD 100000-120000 per year"
    assert result["data"]["date_posted"].endswith("+00:00")


def test_lever_uses_list_sections_when_main_description_is_empty() -> None:
    source = SourceConfig(
        source_id="example_lever",
        company="Example",
        region="USA",
        company_url="",
        career_url="",
        platform="lever",
        transport="json_api",
        method="GET",
        endpoint="https://api.lever.co/v0/postings/example",
        notes="",
    )
    raw = {
        "id": "job-2",
        "text": "Data Annotator",
        "description": "",
        "hostedUrl": "https://jobs.lever.co/example/job-2",
        "categories": {"location": "Malaysia"},
        "lists": [
            {"text": "Requirements", "content": "<li>Fluent in English</li>"},
        ],
    }
    result = normalize_lever_job(raw, source, "2026-09-02T00:00:00+00:00").to_dict()
    assert "Requirements" in result["data"]["job_description"]
    assert "Fluent in English" in result["data"]["job_description"]
