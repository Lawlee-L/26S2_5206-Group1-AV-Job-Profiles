"""Command-line export of the accepted DuckDB snapshot to team CSV format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from av_jobs.exports import TEAM_CSV_COLUMNS, export_team_jobs_csv

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "published" / "latest.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export active AV jobs from DuckDB to the team CSV contract."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Accepted snapshot manifest used when --database is omitted.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Optional explicit DuckDB file; otherwise read it from the manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output CSV path; defaults to exports/av_jobs_<run_id>.csv.",
    )
    return parser.parse_args()


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, str]:
    """Resolve the database, output and run ID from CLI inputs."""

    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Latest manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = str(manifest["run_id"])

    if args.database:
        database_path = args.database.resolve()
    else:
        database_path = Path(manifest["duckdb_file"])
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path
        database_path = database_path.resolve()

    output_path = (
        args.output.resolve()
        if args.output
        else PROJECT_ROOT / "exports" / f"av_jobs_{run_id}.csv"
    )
    return database_path, output_path, run_id


def main() -> int:
    """Generate one CSV and report its stable schema and row count."""

    try:
        database_path, output_path, run_id = _resolve_paths(_parse_args())
        row_count = export_team_jobs_csv(database_path, output_path)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc

    try:
        display_path = output_path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        display_path = str(output_path)

    print(
        json.dumps(
            {
                "run_id": run_id,
                "rows": row_count,
                "columns": list(TEAM_CSV_COLUMNS),
                "output": display_path,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
