from av_jobs.collectors.hotjob import (
    hotjob_description,
    hotjob_detail_endpoint,
    hotjob_public_url,
    normalize_hotjob_job,
)
from av_jobs.config import SourceConfig


def make_source() -> SourceConfig:
    """Create a small HotJob source for the tests."""
    return SourceConfig(
        source_id="example_china_hotjob",
        company="Example",
        region="China",
        company_url="https://example.com",
        career_url="https://wecruit.hotjob.cn/SU123/pb/social.html",
        platform="hotjob",
        transport="json_api",
        method="POST",
        endpoint="https://wecruit.hotjob.cn/wecruit/positionInfo/listPosition/SU123?iSaJAx=isAjax",
        notes="",
    )


def test_hotjob_detail_endpoint() -> None:
    assert hotjob_detail_endpoint(make_source().endpoint) == (
        "https://wecruit.hotjob.cn/wecruit/positionInfo/"
        "listPositionDetail/SU123?iSaJAx=isAjax"
    )


def test_hotjob_public_url() -> None:
    assert hotjob_public_url(make_source(), "abc123") == (
        "https://wecruit.hotjob.cn/SU123/pb/"
        "posDetail.html?postId=abc123&postType=society"
    )


def test_hotjob_description() -> None:
    raw = {
        "workContent": "<p>Build vehicle software.</p>",
        "serviceCondition": "Know Python.",
        "applyPositionContent": "",
    }
    assert hotjob_description(raw) == (
        "Responsibilities\nBuild vehicle software.\n\nRequirements\nKnow Python."
    )


def test_hotjob_mapping() -> None:
    raw = {
        "postId": "abc123",
        "postName": "Autonomous Driving Engineer",
        "workPlaceStr": "Beijing",
        "workContent": "Build driving software.",
        "serviceCondition": "Know Python.",
        "publishFirstDate": "2026-08-01 12:00:00",
    }
    result = normalize_hotjob_job(
        raw,
        make_source(),
        "2026-09-02T00:00:00+00:00",
    ).to_dict()

    assert result["metadata"]["source_job_id"] == "abc123"
    assert result["data"]["advertised_job_title"] == "Autonomous Driving Engineer"
    assert result["data"]["location"] == "Beijing"
    assert result["data"]["job_url"].endswith(
        "posDetail.html?postId=abc123&postType=society"
    )
    assert result["data"]["date_posted"] == "2026-08-01 12:00:00"
