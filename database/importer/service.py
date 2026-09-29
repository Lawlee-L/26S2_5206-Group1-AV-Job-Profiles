"""Application API used by command-line, GUI, and automation front ends."""

from pathlib import Path
from typing import Any

from .contracts import AnalysisFiles, CollectionFiles
from .ports import ImportBackend


class ImporterService:
    """Run importer use cases without depending on argparse, print, or MySQL."""

    def __init__(self, backend: ImportBackend) -> None:
        self._backend = backend

    def plan_collection(self, files: CollectionFiles) -> dict[str, Any]:
        return self._backend.plan_collection(files)

    def plan_analysis(self, files: AnalysisFiles) -> dict[str, Any]:
        return self._backend.plan_analysis(files)

    def import_collection(self, files: CollectionFiles, backup_dir: Path) -> dict[str, Any]:
        return self._backend.import_collection(files, backup_dir)

    def import_analysis(
        self, files: AnalysisFiles, backup_dir: Path, git_commit: str
    ) -> dict[str, Any]:
        return self._backend.import_analysis(files, backup_dir, git_commit)

    def backup(self, backup_dir: Path) -> dict[str, Any]:
        return self._backend.backup(backup_dir)

    def restore(self, backup_path: Path, target_database: str) -> dict[str, Any]:
        return self._backend.restore(backup_path, target_database)

    def rollback(self, batch_id: int | None, backup_dir: Path) -> dict[str, Any]:
        return self._backend.rollback(batch_id, backup_dir)

    def qa_release(self, release_key: str) -> dict[str, Any]:
        """Read and validate release metrics without mutating the database."""
        return self._backend.qa_release(release_key)

    def publish_release(self, release_key: str, backup_dir: Path,
                        *, freeze_existing: bool = False) -> dict[str, Any]:
        return self._backend.publish_release(release_key, backup_dir, freeze_existing)

    def trend_readiness(self) -> dict[str, Any]:
        return self._backend.trend_readiness()
