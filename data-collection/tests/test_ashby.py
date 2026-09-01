from av_jobs.collectors.ashby import normalize_ashby_job
from av_jobs.config import SourceConfig


def test_ashby_mapping() -> None:
    source = SourceConfig(
        source_id="example_ashby",
        company="Example",
        region="Korea",
        company_url="https://example.com",
        career_url="https://example.com/careers",
        platform="ashby",
        transport="json_api",
        method="GET",
        endpoint="https://api.ashbyhq.com/posting-api/job-board/example",
        notes="",
    )
    raw = {
        "id": "job-123",
        "title": "Machine Learning Engineer",
        "descriptionPlain": "Build driving models.",
        "jobUrl": "https://jobs.ashbyhq.com/example/job-123",
        "location": "Seoul, South Korea",
        "compensationTierSummary": "$100,000-$130,000",
        "publishedAt": "2026-09-01T00:00:00Z",
    }
    result = normalize_ashby_job(raw, source, "2026-09-02T00:00:00+00:00").to_dict()
    assert result["metadata"]["source_job_id"] == "job-123"
    assert result["data"]["advertised_job_title"] == "Machine Learning Engineer"
    assert result["data"]["location"] == "Seoul, South Korea"
    assert result["data"]["salary"] == "$100,000-$130,000"
    assert result["data"]["date_posted"] == "2026-09-01T00:00:00Z"


def test_ashby_ignores_empty_compensation_objects() -> None:
    source = SourceConfig(
        source_id="example_ashby",
        company="Example",
        region="USA",
        company_url="",
        career_url="",
        platform="ashby",
        transport="json_api",
        method="GET",
        endpoint="https://api.ashbyhq.com/posting-api/job-board/example",
        notes="",
    )
    raw = {
        "id": "job-2",
        "title": "Engineer",
        "descriptionPlain": "Description",
        "jobUrl": "https://jobs.ashbyhq.com/example/job-2",
        "location": "Remote",
        "compensation": {
            "compensationTierSummary": None,
            "compensationTiers": [],
        },
    }
    result = normalize_ashby_job(raw, source, "2026-09-02T00:00:00+00:00").to_dict()
    assert result["data"]["salary"] is None


def test_ashby_prefers_nested_salary_summary() -> None:
    source = SourceConfig(
        source_id="example_ashby",
        company="Example",
        region="USA",
        company_url="",
        career_url="",
        platform="ashby",
        transport="json_api",
        method="GET",
        endpoint="https://api.ashbyhq.com/posting-api/job-board/example",
        notes="",
    )
    raw = {
        "id": "job-3",
        "title": "Engineer",
        "descriptionPlain": "Description",
        "jobUrl": "https://jobs.ashbyhq.com/example/job-3",
        "location": "Remote",
        "compensation": {
            "compensationTierSummary": "$133K-$254K • Offers Bonus",
            "compensationTiers": [{"title": "Base Salary"}],
        },
    }
    result = normalize_ashby_job(raw, source, "2026-09-02T00:00:00+00:00").to_dict()
    assert result["data"]["salary"] == "$133K-$254K • Offers Bonus"
