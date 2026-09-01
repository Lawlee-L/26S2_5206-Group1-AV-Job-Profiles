from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class JobMetadata:
    source_id: str
    platform: str
    company: str
    region: str
    source_job_id: str | None
    source_key: str
    collected_at: str


@dataclass(frozen=True, slots=True)
class JobData:
    advertised_job_title: str | None
    job_description: str | None
    job_url: str | None
    location: str | None
    salary: str | None
    date_posted: str | None


@dataclass(frozen=True, slots=True)
class StandardJob:
    metadata: JobMetadata
    data: JobData

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": asdict(self.metadata),
            "data": asdict(self.data),
        }


def utc_now_iso() -> str:
    """Return the current UTC time for the collection record."""
    return datetime.now(timezone.utc).isoformat()


def build_source_key(
    *,
    platform: str,
    company: str,
    source_job_id: str | None,
    job_url: str | None,
    title: str | None,
    location: str | None,
) -> str:
    """Create a stable key for tracking the same source job each week."""
    prefix = f"{platform.strip().lower()}|{company.strip().lower()}"
    if source_job_id:
        return f"{prefix}|id:{source_job_id.strip()}"
    if job_url:
        return f"{prefix}|url:{job_url.strip()}"
    return f"{prefix}|fallback:{(title or '').strip().lower()}|{(location or '').strip().lower()}"
