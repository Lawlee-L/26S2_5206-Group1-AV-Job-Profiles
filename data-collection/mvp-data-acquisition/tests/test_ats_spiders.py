"""Offline parser-contract tests for each supported ATS family."""

from __future__ import annotations

import json
from pathlib import Path

from scrapy.http import TextResponse
from scrapy.settings import Settings
from scrapy.spiderloader import SpiderLoader

from av_jobs import settings as project_settings
from av_jobs.models import RawJob
from av_jobs.registry import MVP_SOURCES, MVP_SPIDERS
from av_jobs.snapshots import write_response_snapshot
from av_jobs.spiders.ats.ashby.aurora import AuroraSpider
from av_jobs.spiders.ats.ashby.base import AshbySpider
from av_jobs.spiders.ats.greenhouse.base import GreenhouseSpider
from av_jobs.spiders.ats.greenhouse.kodiak import KodiakSpider
from av_jobs.spiders.ats.lever.base import LeverSpider
from av_jobs.spiders.ats.lever.zoox import ZooxSpider

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def json_response(url: str, payload: object) -> TextResponse:
    return TextResponse(
        url=url,
        body=json.dumps(payload).encode("utf-8"),
        encoding="utf-8",
        headers={"Content-Type": "application/json"},
    )


def disable_snapshot(spider) -> None:
    spider.snapshot_response = lambda response: Path("fixture.json")


def test_greenhouse_spider_maps_shared_schema(tmp_path: Path) -> None:
    spider = KodiakSpider(run_id="test-run", data_root=tmp_path)
    disable_snapshot(spider)
    response = json_response(
        "https://boards-api.greenhouse.io/v1/boards/kodiak/jobs?content=true",
        {
            "jobs": [
                {
                    "id": 123,
                    "title": "Perception Engineer",
                    "location": {"name": "Mountain View, CA"},
                    "content": "<p>Build perception systems with C++.</p>",
                    "absolute_url": "https://job-boards.greenhouse.io/kodiak/jobs/123",
                    "first_published": "2026-08-01T00:00:00Z",
                    "updated_at": "2026-08-02T00:00:00Z",
                    "departments": [{"name": "Autonomy"}],
                }
            ]
        },
    )
    item = next(iter(spider.parse(response)))
    job = RawJob.model_validate(item).with_content_hash()
    assert job.company == "Kodiak"
    assert job.source_name == "greenhouse"
    assert job.source_job_id == "123"
    assert job.department == "Autonomy"
    assert job.content_hash


def test_lever_spider_maps_shared_schema(tmp_path: Path) -> None:
    spider = ZooxSpider(run_id="test-run", data_root=tmp_path)
    disable_snapshot(spider)
    response = json_response(
        "https://api.lever.co/v0/postings/zoox?mode=json",
        [
            {
                "id": "job-456",
                "text": "Motion Planning Engineer",
                "categories": {
                    "location": "Foster City, CA",
                    "allLocations": ["Foster City, CA"],
                    "commitment": "Full-time",
                    "department": "Autonomy",
                    "team": "Planning",
                },
                "createdAt": 1785542400000,
                "description": "<p>Plan safe autonomous motion.</p>",
                "lists": [{"text": "Requirements", "content": "<li>Python</li>"}],
                "hostedUrl": "https://jobs.lever.co/zoox/job-456",
                "workplaceType": "hybrid",
            }
        ],
    )
    item = next(iter(spider.parse(response)))
    job = RawJob.model_validate(item)
    assert job.company == "Zoox"
    assert job.source_name == "lever"
    assert job.posted_at is not None
    assert "Requirements" in job.description_raw


def test_ashby_spider_maps_shared_schema(tmp_path: Path) -> None:
    spider = AuroraSpider(run_id="test-run", data_root=tmp_path)
    disable_snapshot(spider)
    response = json_response(
        "https://api.ashbyhq.com/posting-api/job-board/aurora-operations-inc",
        {
            "jobs": [
                {
                    "id": "job-789",
                    "title": "Senior Controls Engineer",
                    "location": "Pittsburgh, PA",
                    "descriptionPlain": "Develop autonomous truck control software.",
                    "jobUrl": "https://jobs.ashbyhq.com/aurora-operations-inc/job-789",
                    "publishedAt": "2026-08-01T00:00:00Z",
                    "employmentType": "FullTime",
                    "department": "Engineering",
                    "team": "Controls",
                    "workplaceType": "OnSite",
                }
            ]
        },
    )
    item = next(iter(spider.parse(response)))
    job = RawJob.model_validate(item)
    assert job.company == "Aurora"
    assert job.source_name == "ashby"
    assert job.team == "Controls"


def test_mvp_registry_has_one_loadable_spider_per_company() -> None:
    settings = Settings()
    settings.setmodule(project_settings, priority="project")
    loader = SpiderLoader.from_settings(settings)
    loaded_names = set(loader.list())
    assert set(MVP_SPIDERS) <= loaded_names
    assert len(MVP_SPIDERS) == 16
    assert len({source.company for source in MVP_SOURCES}) == 16

    expected_base = {
        "ashby": AshbySpider,
        "greenhouse": GreenhouseSpider,
        "lever": LeverSpider,
    }
    for source in MVP_SOURCES:
        spider_class = loader.load(source.spider)
        assert spider_class.company == source.company
        assert spider_class.source_name == source.platform
        assert issubclass(spider_class, expected_base[source.platform])
        assert spider_class.board_token


def test_raw_snapshot_has_auditable_metadata(tmp_path: Path) -> None:
    response = json_response("https://example.test/jobs", {"jobs": []})
    path = write_response_snapshot(
        response,
        data_root=tmp_path,
        run_id="test-run",
        company="Example AV",
        company_slug="example-av",
        source_name="greenhouse",
    )
    metadata = json.loads(
        path.with_suffix(path.suffix + ".meta.json").read_text(encoding="utf-8")
    )
    assert path.read_bytes() == response.body
    assert metadata["url"] == response.url
    assert metadata["http_status"] == 200
    assert len(metadata["response_sha256"]) == 64
