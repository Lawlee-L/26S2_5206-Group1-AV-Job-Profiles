"""Adapter interfaces for persistence and external side effects."""

from pathlib import Path
from typing import Any, Protocol

from .contracts import AnalysisFiles, CollectionFiles


class ImportBackend(Protocol):
    """Operations implemented by MySQL today and replaceable by another backend."""

    def plan_collection(self, files: CollectionFiles) -> dict[str, Any]: ...

    def plan_analysis(self, files: AnalysisFiles) -> dict[str, Any]: ...

    def import_collection(self, files: CollectionFiles, backup_dir: Path) -> dict[str, Any]: ...

    def import_analysis(
        self, files: AnalysisFiles, backup_dir: Path, git_commit: str
    ) -> dict[str, Any]: ...

    def backup(self, backup_dir: Path) -> dict[str, Any]: ...

    def restore(self, backup_path: Path, target_database: str) -> dict[str, Any]: ...

    def rollback(self, batch_id: int | None, backup_dir: Path) -> dict[str, Any]: ...
