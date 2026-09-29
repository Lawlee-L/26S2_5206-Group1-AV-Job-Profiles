"""MySQL adapter for the importer service.

The adapter is kept separate from the CLI so a GUI can compose the same
service. Database operations are delegated to the existing implementation
module; this adapter owns only port translation and result shaping.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

from .contracts import AnalysisFiles, CollectionFiles
from .release_metrics import release_qa_report
from .publication import publish_release
from .trends import trend_readiness_report


class MySQLImporterBackend:
    """Implement ``ImportBackend`` by adapting the current MySQL operations."""

    def __init__(self, implementation: ModuleType | None = None) -> None:
        self._implementation = implementation

    def _engine(self) -> ModuleType:
        if self._implementation is None:
            self._implementation = import_module("database.weekly_import")
        return self._implementation

    def plan_collection(self, files: CollectionFiles) -> dict[str, Any]:
        engine = self._engine()
        rows, digest = engine.load_collection(files.snapshot)
        return engine.collection_plan(rows, digest, files.previous_snapshot)

    def plan_analysis(self, files: AnalysisFiles) -> dict[str, Any]:
        engine = self._engine()
        report = engine.load_analysis(
            files.postings, files.metadata, files.source_snapshot,
            files.av_cluster_summary, files.other_cluster_summary,
            files.duplicates, files.failures,
        )
        hidden = {"metadata", "rows_by_key", "source_by_key", "cluster_summaries", "duplicates", "failures"}
        return {key: value for key, value in report.items() if key not in hidden}

    def import_collection(self, files: CollectionFiles, backup_dir: Path) -> dict[str, Any]:
        return self._engine().apply_collection(files.snapshot, backup_dir, files.snapshot_generated_at)

    def import_analysis(
        self, files: AnalysisFiles, backup_dir: Path, git_commit: str
    ) -> dict[str, Any]:
        return self._engine().apply_analysis(
            files.postings, files.metadata, files.source_snapshot,
            files.av_cluster_summary, files.other_cluster_summary,
            files.duplicates, files.failures, backup_dir, git_commit,
        )

    def backup(self, backup_dir: Path) -> dict[str, Any]:
        engine = self._engine()
        backup_path = engine.backup_database(backup_dir)
        return {
            "backup": str(backup_path),
            "backup_sha256": engine.sha256_file(backup_path),
            "size_bytes": backup_path.stat().st_size,
        }

    def restore(self, backup_path: Path, target_database: str) -> dict[str, Any]:
        engine = self._engine()
        engine.restore_to_new_database(backup_path, target_database)
        return {
            "restored_to_new_database": target_database,
            "backup": str(backup_path),
            "backup_sha256": engine.sha256_file(backup_path),
        }

    def rollback(self, batch_id: int | None, backup_dir: Path) -> dict[str, Any]:
        return self._engine().rollback_latest(batch_id, backup_dir)

    def qa_release(self, release_key: str) -> dict[str, Any]:
        engine = self._engine()
        connection = engine.db_connect()
        try:
            engine.verify_schema(connection)
            return release_qa_report(connection, release_key)
        finally:
            connection.close()

    def publish_release(self, release_key: str, backup_dir: Path,
                        freeze_existing: bool = False) -> dict[str, Any]:
        return publish_release(self._engine(), release_key, backup_dir,
                               freeze_existing=freeze_existing)

    def trend_readiness(self) -> dict[str, Any]:
        engine = self._engine()
        connection = engine.db_connect()
        try:
            engine.verify_schema(connection)
            return trend_readiness_report(connection)
        finally:
            connection.close()
