"""Command-line adapter for the importer application service."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time as monotonic_time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from . import AnalysisFiles, CollectionFiles, ImportErrorSafe, ImporterService, MySQLImporterBackend


ROOT = Path(__file__).resolve().parents[2]


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      default=_json_default)


def _operation_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """Return safe, JSON-serializable CLI arguments for the local audit record."""
    safe: dict[str, Any] = {}
    for key, value in vars(args).items():
        if any(secret_word in key.lower() for secret_word in ("password", "secret", "token", "credential")):
            safe[key] = "[REDACTED]"
        elif isinstance(value, Path):
            safe[key] = str(value)
        else:
            safe[key] = value
    return safe


def _persist_operation_audit(record: dict[str, Any], audit_dir: Path) -> tuple[Path, Path]:
    """Write one immutable JSON report and append one JSONL local log record."""
    logs_dir = audit_dir / "logs"
    reports_dir = audit_dir / "reports"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{record['operation_id']}.json"
    log_path = logs_dir / "weekly_import.jsonl"
    line = (json.dumps(record, ensure_ascii=False, indent=2, default=_json_default) + "\n").encode("utf-8")
    with report_path.open("x", encoding="utf-8", newline="\n") as report_file:
        report_file.write(line.decode("utf-8"))
        report_file.flush()
        os.fsync(report_file.fileno())
    descriptor = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        compact_line = (_stable_json(record) + "\n").encode("utf-8")
        os.write(descriptor, compact_line)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return report_path, log_path


def _analysis_files_from_args(args: argparse.Namespace) -> AnalysisFiles:
    return AnalysisFiles(
        postings=args.postings,
        metadata=args.metadata,
        source_snapshot=args.source_input,
        av_cluster_summary=args.av_summary,
        other_cluster_summary=args.other_summary,
        duplicates=args.duplicates,
        failures=args.failures,
    )


def make_parser(description: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    subs = parser.add_subparsers(dest="command", required=True)

    def add_audit_dir(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument(
            "--audit-dir", type=Path, default=ROOT / "database" / "operation_logs",
            help="local directory for per-run JSON reports and the append-only JSONL log",
        )

    plan = subs.add_parser("plan-collection", help="validate/count a Li snapshot without connecting to MySQL")
    add_audit_dir(plan)
    plan.add_argument("--input", required=True, type=Path)
    plan.add_argument("--previous", type=Path)
    plan_analysis = subs.add_parser("plan-analysis", help="validate output files and source_key joins without MySQL")
    add_audit_dir(plan_analysis)
    for name in ("postings", "metadata", "source-input", "av-summary", "other-summary"):
        plan_analysis.add_argument("--" + name, required=True, type=Path)
    plan_analysis.add_argument("--duplicates", required=True, type=Path)
    plan_analysis.add_argument("--failures", required=True, type=Path)
    collection = subs.add_parser("import-collection", help="back up and import one cumulative Li snapshot")
    add_audit_dir(collection)
    collection.add_argument("--input", required=True, type=Path)
    collection.add_argument("--backup-dir", type=Path, default=ROOT / "database" / "backups")
    analysis = subs.add_parser("import-analysis", help="back up and import validated Sunjol pipeline outputs")
    add_audit_dir(analysis)
    for name in ("postings", "metadata", "source-input", "av-summary", "other-summary"):
        analysis.add_argument("--" + name, required=True, type=Path)
    analysis.add_argument("--duplicates", required=True, type=Path)
    analysis.add_argument("--failures", required=True, type=Path)
    analysis.add_argument("--backup-dir", type=Path, default=ROOT / "database" / "backups")
    analysis.add_argument("--git-commit", required=True,
                          help="classification pipeline Git commit SHA (7–64 hex characters)")
    backup = subs.add_parser("backup", help="create a compressed full-database backup")
    add_audit_dir(backup)
    backup.add_argument("--backup-dir", type=Path, default=ROOT / "database" / "backups")
    restore = subs.add_parser("restore", help="restore a backup into a new, empty database")
    add_audit_dir(restore)
    restore.add_argument("--file", required=True, type=Path)
    restore.add_argument("--target-db", required=True)
    rollback = subs.add_parser("rollback", help="undo the latest successful import batch")
    add_audit_dir(rollback)
    rollback.add_argument("--batch-id", type=int)
    rollback.add_argument("--backup-dir", type=Path, default=ROOT / "database" / "backups")
    return parser


def main(argv: list[str] | None = None, *, implementation: ModuleType | None = None) -> int:
    if implementation is None:
        from importlib import import_module

        implementation = import_module("database.weekly_import")
    args = make_parser(implementation.__doc__).parse_args(argv)
    service = ImporterService(MySQLImporterBackend(implementation=implementation))
    started_at = datetime.now(timezone.utc)
    started_clock = monotonic_time.monotonic()
    operation_id = f"{started_at.strftime('%Y%m%dT%H%M%S.%fZ')}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    result: dict[str, Any] | None = None
    error: str | None = None
    exit_code = 0
    try:
        if args.command == "plan-collection":
            result = service.plan_collection(CollectionFiles(args.input, args.previous))
        elif args.command == "plan-analysis":
            result = service.plan_analysis(_analysis_files_from_args(args))
        elif args.command == "import-collection":
            result = service.import_collection(CollectionFiles(args.input), args.backup_dir)
        elif args.command == "import-analysis":
            result = service.import_analysis(_analysis_files_from_args(args), args.backup_dir, args.git_commit)
        elif args.command == "backup":
            result = service.backup(args.backup_dir)
        elif args.command == "restore":
            result = service.restore(args.file, args.target_db)
        elif args.command == "rollback":
            result = service.rollback(args.batch_id, args.backup_dir)
        else:
            raise ImportErrorSafe("Unknown command")
    except ImportErrorSafe as exc:
        print(f"Import stopped: {exc}", file=sys.stderr)
        error = f"{type(exc).__name__}: {exc}"
        exit_code = 2
    except Exception as exc:
        print(f"Import failed; the transaction was rolled back: {type(exc).__name__}: {exc}", file=sys.stderr)
        error = f"{type(exc).__name__}: {exc}"
        password = os.environ.get("AVDB_PASSWORD")
        if password:
            error = error.replace(password, "[REDACTED]")
        exit_code = 1

    finished_at = datetime.now(timezone.utc)
    record = {
        "operation_id": operation_id,
        "operation": args.command,
        "status": "succeeded" if exit_code == 0 else "failed",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round(monotonic_time.monotonic() - started_clock, 3),
        "exit_code": exit_code,
        "arguments": _operation_arguments(args),
        "result": result,
        "error": error,
    }
    try:
        report_path, log_path = _persist_operation_audit(record, args.audit_dir)
    except Exception as audit_exc:
        print(f"WARNING: could not write the local operation report/log: {type(audit_exc).__name__}: {audit_exc}",
              file=sys.stderr)
        if exit_code == 0:
            exit_code = 3
    else:
        if exit_code == 0:
            print(json.dumps({
                "operation_id": operation_id,
                "status": "succeeded",
                "result": result,
                "local_report": str(report_path),
                "local_log": str(log_path),
            }, ensure_ascii=False, indent=2, default=_json_default))
        else:
            print(f"Operation report: {report_path}\nOperation log: {log_path}", file=sys.stderr)
    return exit_code
