import av_jobs.collectors.tensor as tensor_module
from av_jobs.collectors.tensor import (
    collect_tensor,
    normalize_tensor_job,
    tensor_detail,
    tensor_job_urls,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small Tensor source for the tests."""
    return SourceConfig(
        source_id="tensor_autox_usa_singapore_custom",
        company="Tensor (AutoX)",
        region="Global",
        company_url="https://www.tensor.auto/",
        career_url="https://www.tensor.auto/careers",
        platform="tensor",
        transport="html",
        method="GET",
        endpoint="https://www.tensor.auto/careers",
        notes="",
    )


def test_tensor_job_urls_are_unique() -> None:
    page = """
    <a href="/careers">Careers</a>
    <a href="/careers/jd01">First job</a>
    <a href="/careers/jd01">First job again</a>
    <a href="/careers/jd203">Second job</a>
    """
    assert tensor_job_urls(page, make_source().endpoint) == [
        "https://www.tensor.auto/careers/jd01",
        "https://www.tensor.auto/careers/jd203",
    ]


def test_tensor_detail_reads_description_locations_and_salary() -> None:
    page = """
    <h1 class="cms-job-title">Perception Engineer</h1>
    <div class="w-layout-grid grid-33">
      <p>Build autonomous driving software.</p>
    </div>
    <div class="w-layout-grid grid-33">
      <h1>Locations</h1>
      <div><ul>
        <li>San Jose, California, US (Salary Range: $75k—$300k USD)</li>
        <li>Singapore</li>
      </ul></div>
    </div>
    <div class="w-layout-grid grid-33">
      <h1>Responsibilities</h1><div><ul><li>Develop perception models.</li></ul></div>
    </div>
    """
    result = tensor_detail(page)
    assert result["title"] == "Perception Engineer"
    assert "Build autonomous driving software." in result["description"]
    assert "Develop perception models." in result["description"]
    assert result["location"] == "San Jose, California, US | Singapore"
    assert result["salary"] == "San Jose, California, US: $75k—$300k USD"
    assert result["date_posted"] is None


def test_tensor_mapping_keeps_missing_date_null() -> None:
    raw_job = {
        "title": "Perception Engineer",
        "description": "Build autonomous driving software.",
        "location": "Singapore",
        "salary": None,
        "date_posted": None,
    }
    result = normalize_tensor_job(
        raw_job,
        make_source(),
        "2026-09-03T00:00:00+00:00",
        "https://www.tensor.auto/careers/jd01",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "jd01"
    assert result["data"]["advertised_job_title"] == "Perception Engineer"
    assert result["data"]["job_description"] == "Build autonomous driving software."
    assert result["data"]["job_url"] == "https://www.tensor.auto/careers/jd01"
    assert result["data"]["location"] == "Singapore"
    assert result["data"]["salary"] is None
    assert result["data"]["date_posted"] is None


def test_tensor_collector_reads_all_links(monkeypatch) -> None:
    list_page = '<a href="/careers/jd01">One</a><a href="/careers/jd02">Two</a>'
    detail_one = """
    <h1 class="cms-job-title">One</h1>
    <div class="w-layout-grid grid-33"><p>First description.</p></div>
    """
    detail_two = """
    <h1 class="cms-job-title">Two</h1>
    <div class="w-layout-grid grid-33"><p>Second description.</p></div>
    """
    pages = {
        make_source().endpoint: list_page,
        "https://www.tensor.auto/careers/jd01": detail_one,
        "https://www.tensor.auto/careers/jd02": detail_two,
    }
    monkeypatch.setattr(tensor_module, "get_text", pages.__getitem__)

    raw_payload, jobs = collect_tensor(make_source())
    assert len(raw_payload["jobs"]) == 2
    assert [job.data.advertised_job_title for job in jobs] == ["One", "Two"]
