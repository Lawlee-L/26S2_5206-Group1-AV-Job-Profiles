"""Lever Postings API adapter shared by company-specific spiders."""

from __future__ import annotations

import json

import scrapy
from scrapy.exceptions import CloseSpider

from ...base import AtsApiSpider, join_values


class LeverSpider(AtsApiSpider):
    """Map one public Lever board to the shared raw-job schema."""

    source_name = "lever"
    board_token: str
    api_origin = "https://api.lever.co"

    async def start(self):
        url = f"{self.api_origin}/v0/postings/{self.board_token}?mode=json"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response, **kwargs):
        self.snapshot_response(response)
        jobs = response.json()
        if not isinstance(jobs, list):
            raise CloseSpider("invalid_lever_payload")
        for job in self.selected_jobs(jobs):
            categories = job.get("categories") or {}
            description_parts = [
                job.get("description") or job.get("descriptionPlain") or ""
            ]
            for section in job.get("lists") or []:
                description_parts.extend(
                    (section.get("text") or "", section.get("content") or "")
                )
            description_parts.append(
                job.get("additional") or job.get("additionalPlain") or ""
            )
            salary = job.get("salaryRange")
            yield self.common_item(
                source_job_id=str(job.get("id", "")),
                company=self.company,
                original_title=job.get("text", ""),
                location_raw=join_values(
                    categories.get("allLocations") or [categories.get("location") or ""]
                ),
                description_raw="\n".join(description_parts),
                source_url=job.get("hostedUrl") or response.url,
                posted_at=job.get("createdAt"),
                updated_at=None,
                employment_type=categories.get("commitment"),
                department=categories.get("department"),
                team=categories.get("team"),
                workplace_type=job.get("workplaceType"),
                salary_raw=(json.dumps(salary, ensure_ascii=False) if salary else None),
            )
