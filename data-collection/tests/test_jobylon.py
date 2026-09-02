from av_jobs.collectors.jobylon import (
    jobylon_job_urls,
    jobylon_json_ld,
    jobylon_location,
    normalize_jobylon_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small Jobylon source for the tests."""
    return SourceConfig(
        source_id="example_sweden_jobylon",
        company="Example",
        region="Sweden",
        company_url="https://example.com",
        career_url="https://example.com/careers",
        platform="jobylon",
        transport="html",
        method="GET",
        endpoint="https://cdn.jobylon.com/jobs/companies/1/embed/v2/",
        notes="",
    )


def test_jobylon_job_urls_are_unique() -> None:
    widget = """
    url: '/jobs/123-example-engineer/',
    url: '/jobs/123-example-engineer/',
    url: '/jobs/456-example-manager/',
    """
    assert jobylon_job_urls(widget) == [
        "https://emp.jobylon.com/jobs/123-example-engineer/",
        "https://emp.jobylon.com/jobs/456-example-manager/",
    ]


def test_jobylon_json_ld_reads_job_posting() -> None:
    page = """
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"JobPosting","title":"Engineer"}
    </script>
    """
    assert jobylon_json_ld(page)["title"] == "Engineer"


def test_jobylon_location_uses_street_address() -> None:
    raw = {
        "jobLocation": [
            {
                "address": {
                    "streetAddress": "Stockholm, Sweden",
                    "addressLocality": "Stockholm",
                }
            }
        ]
    }
    assert jobylon_location(raw) == "Stockholm, Sweden"


def test_jobylon_mapping() -> None:
    raw = {
        "@type": "JobPosting",
        "title": "Autonomous Vehicle Engineer",
        "description": "<p>Build autonomous trucks.</p>",
        "datePosted": "2026-09-01T12:00:00+00:00",
        "jobLocation": {"address": {"addressLocality": "Stockholm", "addressCountry": "Sweden"}},
    }
    result = normalize_jobylon_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
        "https://emp.jobylon.com/jobs/123-example-engineer/",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "123"
    assert result["data"]["advertised_job_title"] == "Autonomous Vehicle Engineer"
    assert result["data"]["job_description"] == "Build autonomous trucks."
    assert result["data"]["job_url"] == "https://emp.jobylon.com/jobs/123-example-engineer/"
    assert result["data"]["location"] == "Stockholm, Sweden"
    assert result["data"]["date_posted"] == "2026-09-01T12:00:00+00:00"
