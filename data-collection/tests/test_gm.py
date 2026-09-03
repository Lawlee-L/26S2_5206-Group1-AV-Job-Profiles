from av_jobs.collectors.gm import (
    gm_feed_jobs,
    gm_location,
    gm_salary,
    normalize_gm_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small GM source for the tests."""
    return SourceConfig(
        source_id="gm_usa_happydance",
        company="GM",
        region="USA",
        company_url="https://www.gm.com/innovation/autonomous-driving",
        career_url="https://search-careers.gm.com/en/teams/autonomy/",
        platform="gm",
        transport="xml_api",
        method="GET",
        endpoint="https://search-careers.gm.com/en/jobs/xml/?rss=true",
        notes="",
    )


def test_gm_feed_keeps_only_marked_jobs() -> None:
    feed = """
    <source>
      <job><title>AV Engineer</title><description><![CDATA[<p>Build AV tools.</p><p>#GM-AV-1</p>]]></description></job>
      <job><title>Other Engineer</title><description><![CDATA[<p>Other work.</p>]]></description></job>
    </source>
    """
    jobs = gm_feed_jobs(feed)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "AV Engineer"


def test_gm_salary_reads_clear_range() -> None:
    description = "The salary range for this role is $128,700 to $261,300."
    assert gm_salary(description) == "$128,700 to $261,300"
    assert gm_salary("No salary amount is provided.") is None


def test_gm_location_keeps_remote_type() -> None:
    raw_job = {
        "city": "Austin",
        "state": "Texas",
        "country": "United States of America",
        "remotetype": "Fully remote",
    }
    assert gm_location(raw_job) == "Austin, Texas, United States of America (Fully remote)"


def test_gm_mapping_uses_public_feed_fields() -> None:
    raw_job = {
        "title": "AV Software Engineer",
        "requisitionid": "JR-123",
        "url": "https://search-careers.gm.com/en/jobs/jr-123/example/",
        "description": "<p>Build driving software.</p><p>#GM-AV-1</p>",
        "city": "Sunnyvale",
        "state": "California",
        "country": "United States of America",
        "date": "Thu, 26 Feb 2026 08:00:00 GMT",
    }
    result = normalize_gm_job(
        raw_job,
        make_source(),
        "2026-09-03T00:00:00+00:00",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "JR-123"
    assert result["data"]["advertised_job_title"] == "AV Software Engineer"
    assert "Build driving software." in result["data"]["job_description"]
    assert result["data"]["job_url"].endswith("/jr-123/example/")
    assert result["data"]["location"] == "Sunnyvale, California, United States of America"
    assert result["data"]["salary"] is None
    assert result["data"]["date_posted"] == "2026-02-26"
