"""Strict data contracts shared by spiders, pipelines and orchestration."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

SourceName = Literal["greenhouse", "lever", "ashby"]


class RawJob(BaseModel):
    """Shared contract returned by every company spider."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_job_id: str
    company: str
    original_title: str
    location_raw: str | None = None
    description_raw: str
    source_url: HttpUrl
    posted_at: datetime | None = None
    updated_at: datetime | None = None
    employment_type: str | None = None
    department: str | None = None
    team: str | None = None
    workplace_type: str | None = None
    salary_raw: str | None = None
    source_type: Literal["ats_api"] = "ats_api"
    source_name: SourceName
    scraped_at: datetime
    run_id: str
    content_hash: str | None = None

    @field_validator(
        "source_job_id", "company", "original_title", "description_raw", "run_id"
    )
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    def with_content_hash(self) -> RawJob:
        digest = hashlib.sha256(
            "\n".join(
                (
                    self.source_job_id,
                    self.company,
                    self.original_title,
                    self.description_raw,
                    str(self.source_url),
                )
            ).encode("utf-8")
        ).hexdigest()
        return self.model_copy(update={"content_hash": digest})


class SourceStatus(BaseModel):
    """Per-company evidence used by the publication quality gate."""

    run_id: str
    spider: str
    company: str
    source_name: SourceName
    finish_reason: str
    source_items_seen: int = Field(ge=0)
    validated_items: int = Field(ge=0)
    validation_errors: int = Field(ge=0)
    response_count: int = Field(ge=0)
    response_errors: int = Field(ge=0)
    snapshot_files: int = Field(ge=0)
    status: Literal["success", "failed"]
