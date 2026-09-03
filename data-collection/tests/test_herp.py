from av_jobs.collectors.herp import (
    herp_detail_data,
    herp_job_urls,
    herp_location,
    normalize_herp_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small HERP source for the tests."""
    return SourceConfig(
        source_id="example_japan_herp",
        company="Example",
        region="Japan",
        company_url="https://example.com",
        career_url="https://herp.careers/v1/example",
        platform="herp",
        transport="html",
        method="GET",
        endpoint="https://herp.careers/v1/example",
        notes="",
    )


def test_herp_job_urls_are_unique() -> None:
    page = """
    <a href="/v1/example/job-one">One</a>
    <a href="/v1/example/job-one">One again</a>
    <a href="/v1/example/job_two">Two</a>
    <a href="/v1/example/requisition-groups/other">Other group</a>
    """
    assert herp_job_urls(page, make_source().endpoint) == [
        "https://herp.careers/v1/example/job-one",
        "https://herp.careers/v1/example/job_two",
    ]


def test_herp_detail_data_reads_json_scripts() -> None:
    page = """
    <script id="herp-react-props" type="application/json">
    {"salary":{"type":"text/plain","text":"JPY 500,000 per month"}}
    </script>
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Engineer"}
    </script>
    """
    raw_job, page_data = herp_detail_data(page)
    assert raw_job["title"] == "Engineer"
    assert page_data["salary"]["text"] == "JPY 500,000 per month"


def test_herp_location_uses_page_data() -> None:
    raw_job = {"jobLocation": {"address": "Tokyo"}}
    page_data = {"location": {"type": "text/plain", "text": "Tokyo and remote"}}
    assert herp_location(raw_job, page_data) == "Tokyo and remote"


def test_herp_mapping() -> None:
    raw_job = {
        "@type": "JobPosting",
        "title": "Autonomous Driving Engineer",
        "description": "<p>Build driving software.</p>",
        "datePosted": "2026-09-01T00:00:00.000Z",
        "jobLocation": {"address": "Tokyo"},
    }
    page_data = {
        "salary": {"type": "text/plain", "text": "JPY 500,000 per month"},
        "canonicalUrl": "https://herp.careers/v1/example/job-one",
    }
    result = normalize_herp_job(
        raw_job,
        page_data,
        make_source(),
        "2026-09-03T00:00:00+00:00",
        "https://herp.careers/v1/example/job-one",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "job-one"
    assert result["data"]["advertised_job_title"] == "Autonomous Driving Engineer"
    assert result["data"]["job_description"] == "Build driving software."
    assert result["data"]["job_url"] == "https://herp.careers/v1/example/job-one"
    assert result["data"]["location"] == "Tokyo"
    assert result["data"]["salary"] == "JPY 500,000 per month"
    assert result["data"]["date_posted"] == "2026-09-01T00:00:00.000Z"
