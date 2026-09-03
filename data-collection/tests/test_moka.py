from av_jobs.collectors.moka import (
    collect_moka,
    moka_job_url,
    moka_page_url,
    normalize_moka_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small Moka source for the tests."""
    return SourceConfig(
        source_id="example_china_moka",
        company="Example",
        region="China",
        company_url="https://example.com",
        career_url="https://app.mokahr.com/social-recruitment/example/123456",
        platform="moka",
        transport="json_api",
        method="GET",
        endpoint="https://api.mokahr.com/api-platform/v1/jobs/example?siteId=123456",
        notes="",
    )


def test_moka_page_url_keeps_existing_values() -> None:
    result = moka_page_url(make_source().endpoint, limit=100, offset=200)
    assert "siteId=123456" in result
    assert "limit=100" in result
    assert "offset=200" in result


def test_moka_job_url() -> None:
    result = moka_job_url(make_source(), "job-123")
    assert result == "https://app.mokahr.com/social-recruitment/example/123456#/job/job-123"


def test_moka_mapping() -> None:
    raw = {
        "id": "job-123",
        "title": "Planning Engineer",
        "description": "<p>Build planning software.</p>",
        "publishedAt": "2026-09-01T03:00:00Z",
        "locations": [
            {"country": "中国", "province": "广东", "city": "深圳市", "area": "福田区"},
            {"country": "中国", "province": "上海市", "area": "徐汇区"},
        ],
    }

    result = normalize_moka_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "job-123"
    assert result["data"]["advertised_job_title"] == "Planning Engineer"
    assert result["data"]["location"] == "中国, 广东, 深圳市, 福田区; 中国, 上海市, 徐汇区"
    assert result["data"]["job_description"] == "Build planning software."
    assert result["data"]["date_posted"] == "2026-09-01T03:00:00Z"


def test_moka_collects_more_than_one_page(monkeypatch) -> None:
    first_page = {
        "jobs": [{"id": "1", "title": "One"}, {"id": "2", "title": "Two"}],
        "total": 3,
        "code": 0,
    }
    second_page = {
        "jobs": [{"id": "3", "title": "Three"}],
        "total": 3,
        "code": 0,
    }
    responses = iter([first_page, second_page])
    requested_urls: list[str] = []

    def fake_get_json(url: str):
        requested_urls.append(url)
        return next(responses)

    monkeypatch.setattr("av_jobs.collectors.moka.get_json", fake_get_json)
    raw, jobs = collect_moka(make_source())

    assert len(raw["jobs"]) == 3
    assert len(jobs) == 3
    assert "offset=0" in requested_urls[0]
    assert "offset=100" in requested_urls[1]

