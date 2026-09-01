from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "AV_company_sources_cleaned.xlsx"
DEFAULT_SHEET = "In Scope"

REQUIRED_COLUMNS = (
    "source_id",
    "company",
    "region",
    "company_url",
    "career_url",
    "platform",
    "transport",
    "method",
    "endpoint",
    "notes",
)


@dataclass(frozen=True, slots=True)
class SourceConfig:
    source_id: str
    company: str
    region: str
    company_url: str
    career_url: str
    platform: str
    transport: str
    method: str
    endpoint: str
    notes: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "SourceConfig":
        def text(name: str) -> str:
            value = row.get(name, "")
            return "" if pd.isna(value) else str(value).strip()

        return cls(
            source_id=text("source_id"),
            company=text("company"),
            region=text("region"),
            company_url=text("company_url"),
            career_url=text("career_url"),
            platform=text("platform").lower(),
            transport=text("transport").lower(),
            method=text("method").upper(),
            endpoint=text("endpoint"),
            notes=text("notes"),
        )


def load_sources(
    config_path: Path = DEFAULT_CONFIG_PATH,
    sheet_name: str = DEFAULT_SHEET,
) -> list[SourceConfig]:
    """Load one configuration sheet and validate its structure."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration workbook not found: {config_path}")

    frame = pd.read_excel(config_path, sheet_name=sheet_name, dtype=object)
    missing_columns = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    sources = [SourceConfig.from_row(row) for row in frame.to_dict("records")]
    validate_sources(sources)
    return sources


def validate_sources(sources: list[SourceConfig]) -> None:
    """Stop the run when required configuration is missing or repeated."""
    errors: list[str] = []
    seen: set[str] = set()

    for row_number, source in enumerate(sources, start=2):
        if not source.source_id:
            errors.append(f"row {row_number}: source_id is empty")
        elif source.source_id in seen:
            errors.append(f"row {row_number}: duplicate source_id {source.source_id!r}")
        seen.add(source.source_id)

        if not source.company:
            errors.append(f"row {row_number}: company is empty")
        if not source.platform:
            errors.append(f"row {row_number}: platform is empty")
        if source.method not in {"GET", "POST"}:
            errors.append(f"row {row_number}: unsupported method {source.method!r}")
        if not source.endpoint:
            errors.append(f"row {row_number}: endpoint is empty")
        elif not source.endpoint.startswith(("https://", "http://")):
            errors.append(f"row {row_number}: endpoint is not an HTTP URL")

    if errors:
        raise ValueError("Invalid source configuration:\n- " + "\n- ".join(errors))
