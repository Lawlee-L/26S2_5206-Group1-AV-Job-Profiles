from av_jobs.collectors.aimotive import (
    aimotive_detail,
    aimotive_job_urls,
    normalize_aimotive_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small AImotive source for the tests."""
    return SourceConfig(
        source_id="aimotive_hungary",
        company="AImotive",
        region="Hungary",
        company_url="https://aimotive.com/",
        career_url="https://aimotive.com/career",
        platform="aimotive",
        transport="html",
        method="GET",
        endpoint="https://aimotive.com/career",
        notes="",
    )


def test_aimotive_job_urls_are_unique() -> None:
    page = """
    <div class="position-list-item">
      <a href="https://aimotive.com/w/example-engineer"><h3>Engineer</h3></a>
      <a href="https://aimotive.com/w/example-engineer">Apply</a>
    </div>
    """
    assert aimotive_job_urls(page, make_source().endpoint) == [
        "https://aimotive.com/w/example-engineer"
    ]


def test_aimotive_detail_reads_public_fields() -> None:
    page = """
    <span data-lfr-editable-id="post-location">Budapest, Hungary</span>
    <h1 data-lfr-editable-id="post-title">AI Engineer</h1>
    <div data-lfr-editable-id="post-content">
      <p>Build driving software.</p><h4>Requirements</h4><ul><li>Python</li></ul>
    </div>
    """
    result = aimotive_detail(page)
    assert result["title"] == "AI Engineer"
    assert result["location"] == "Budapest, Hungary"
    assert "Build driving software." in (result["description"] or "")
    assert "- Python" in (result["description"] or "")


def test_aimotive_mapping_keeps_missing_fields_null() -> None:
    raw_job = {
        "title": "AI Engineer",
        "description": "Build driving software.",
        "location": "Budapest, Hungary",
    }
    result = normalize_aimotive_job(
        raw_job,
        make_source(),
        "2026-09-03T00:00:00+00:00",
        "https://aimotive.com/w/ai-engineer",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "ai-engineer"
    assert result["data"]["advertised_job_title"] == "AI Engineer"
    assert result["data"]["job_description"] == "Build driving software."
    assert result["data"]["job_url"] == "https://aimotive.com/w/ai-engineer"
    assert result["data"]["location"] == "Budapest, Hungary"
    assert result["data"]["salary"] is None
    assert result["data"]["date_posted"] is None
