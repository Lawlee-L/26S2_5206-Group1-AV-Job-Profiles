"""Ashby Job Board API adapter shared by company-specific spiders."""

from __future__ import annotations

import json

import scrapy
from scrapy.exceptions import CloseSpider

from ...base import AtsApiSpider, join_values


class AshbySpider(AtsApiSpider):
    """Map one public Ashby board to the shared raw-job schema."""

    source_name = "ashby"
    board_token: str

    async def start(self):
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.board_token}"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        self.snapshot_response(response)
        jobs = response.json().get("jobs")
        if not isinstance(jobs, list):
            raise CloseSpider("invalid_ashby_payload")
        for job in self.selected_jobs(jobs):
            locations = [job.get("location") or ""]
            locations.extend(
                location.get("location", "")
                if isinstance(location, dict)
                else str(location)
                for location in job.get("secondaryLocations") or []
            )
            compensation = job.get("compensation")
            yield self.common_item(
                source_job_id=str(job.get("id", "")),
                company=self.company,
                original_title=job.get("title", ""),
                location_raw=join_values(locations),
                description_raw=(
                    job.get("descriptionPlain") or job.get("descriptionHtml") or ""
                ),
                source_url=job.get("jobUrl") or response.url,
                posted_at=job.get("publishedAt"),
                updated_at=None,
                employment_type=job.get("employmentType"),
                department=job.get("department"),
                team=job.get("team"),
                workplace_type=job.get("workplaceType"),
                salary_raw=(
                    json.dumps(compensation, ensure_ascii=False)
                    if compensation
                    else None
                ),
            )
