"""Greenhouse Job Board API adapter shared by company-specific spiders."""

from __future__ import annotations

import scrapy
from scrapy.exceptions import CloseSpider

from ...base import AtsApiSpider, join_values


class GreenhouseSpider(AtsApiSpider):
    """Map one public Greenhouse board to the shared raw-job schema."""

    source_name = "greenhouse"
    board_token: str

    async def start(self):
        url = (
            "https://boards-api.greenhouse.io/v1/boards/"
            f"{self.board_token}/jobs?content=true"
        )
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        self.snapshot_response(response)
        jobs = response.json().get("jobs")
        if not isinstance(jobs, list):
            raise CloseSpider("invalid_greenhouse_payload")
        for job in self.selected_jobs(jobs):
            departments = job.get("departments") or []
            yield self.common_item(
                source_job_id=str(job.get("id", "")),
                company=self.company,
                original_title=job.get("title", ""),
                location_raw=(job.get("location") or {}).get("name"),
                description_raw=job.get("content") or "",
                source_url=job.get("absolute_url") or response.url,
                posted_at=job.get("first_published"),
                updated_at=job.get("updated_at"),
                employment_type=None,
                department=join_values(
                    department.get("name", "") for department in departments
                ),
                team=None,
                workplace_type=None,
                salary_raw=None,
            )
