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
    candidate: bool = False


@dataclass(frozen=True)
class ReleaseActivation:
    """An explicit compare-and-switch request; None means no previous selection."""

    release_key: str
    expected_week_release: str | None
    expected_current_release: str | None
    reason: str
    actor: str
    historical: bool = False
