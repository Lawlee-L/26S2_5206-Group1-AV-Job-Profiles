"""Input contracts shared by CLI, GUI, and future importer adapters."""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class CollectionFiles:
    """One source snapshot and an optional earlier snapshot for comparison."""

    snapshot: Path
    previous_snapshot: Path | None = None
    snapshot_generated_at: datetime | None = None
    week_date: date | None = None
    historical: bool = False


@dataclass(frozen=True)
class AnalysisFiles:
    """All files that must come from the same classification pipeline run."""

    postings: Path
    metadata: Path
    source_snapshot: Path
    av_cluster_summary: Path
    other_cluster_summary: Path
    duplicates: Path
    failures: Path
    week_date: date | None = None
