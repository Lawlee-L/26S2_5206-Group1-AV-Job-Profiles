from av_jobs.collectors.smartrecruiters import (
    normalize_smartrecruiters_job,
    smartrecruiters_description,
    smartrecruiters_page_url,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small SmartRecruiters source for the tests."""
    return SourceConfig(
        source_id="example_us_smartrecruiters",
        company="Example",
        region="US",
        company_url="https://example.com",
        career_url="https://example.com/careers",
        platform="smartrecruiters",
        transport="json_api",
        method="GET",
        endpoint="https://api.smartrecruiters.com/v1/companies/example/postings?country=us",
        notes="",
    )


def test_smartrecruiters_page_url_keeps_country() -> None:
    result = smartrecruiters_page_url(make_source().endpoint, limit=100, offset=200)
    assert "country=us" in result
    assert "limit=100" in result
    assert "offset=200" in result


def test_smartrecruiters_description_skips_company_text() -> None:
    raw = {
        "jobAd": {
            "sections": {
                "companyDescription": {"title": "Company", "text": "<p>General text.</p>"},
                "jobDescription": {"title": "Job Description", "text": "<p>Build software.</p>"},
                "qualifications": {"title": "Qualifications", "text": "<p>Know Python.</p>"},
            }
        }
    }
    result = smartrecruiters_description(raw)
    assert result == "Job Description\nBuild software.\n\nQualifications\nKnow Python."
    assert "General text" not in result


def test_smartrecruiters_mapping() -> None:
    raw = {
        "id": "job-123",
        "name": "Vehicle Software Engineer",
        "postingUrl": "https://jobs.smartrecruiters.com/example/job-123",
        "releasedDate": "2026-09-02T00:00:00Z",
        "location": {"fullLocation": "Detroit, MI, United States"},
        "jobAd": {
            "sections": {
                "jobDescription": {"title": "Job Description", "text": "<p>Build software.</p>"},
                "additionalInformation": {
                    "title": "Additional Information",
                    "text": "<p>The base salary range is $100,000-$130,000.</p>",
                },
            }
        },
    }

    result = normalize_smartrecruiters_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "job-123"
    assert result["data"]["advertised_job_title"] == "Vehicle Software Engineer"
    assert result["data"]["location"] == "Detroit, MI, United States"
    assert result["data"]["salary"] == "The base salary range is $100,000-$130,000."
    assert result["data"]["date_posted"] == "2026-09-02T00:00:00Z"
