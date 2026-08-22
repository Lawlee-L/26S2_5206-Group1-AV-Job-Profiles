"""Stable downstream exports derived from the accepted DuckDB database."""

from __future__ import annotations

import csv
from pathlib import Path

import duckdb

TEAM_CSV_COLUMNS = ("company", "name", "description", "date_posted")
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _excel_safe_text(value: object) -> object:
    """Prevent untrusted source text from becoming an Excel formula."""

    if isinstance(value, str) and value.lstrip().startswith(CSV_FORMULA_PREFIXES):
        return "'" + value
    return value


def export_team_jobs_csv(database_path: Path, output_path: Path) -> int:
    """Export active jobs in the four-column format requested by the team.

    The query runs against DuckDB rather than Parquet so this function verifies
    the documented analytical handoff. UTF-8 with BOM is used because teammates
    are expected to open the result directly in Microsoft Excel.
    """

    if not database_path.is_file():
        raise FileNotFoundError(f"DuckDB database not found: {database_path}")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        connection.execute("SET TimeZone='UTC'")
        frame = connection.execute(
            """
            SELECT
                company,
                original_title AS name,
                description_text AS description,
                strftime(
                    posted_at_utc AT TIME ZONE 'UTC',
                    '%Y-%m-%dT%H:%M:%SZ'
                ) AS date_posted
            FROM active_jobs
            ORDER BY lower(company), lower(original_title), source_job_id
            """
        ).fetchdf()

    if frame.empty:
        raise ValueError("DuckDB active_jobs contains no rows to export")
    if tuple(frame.columns) != TEAM_CSV_COLUMNS:
        raise RuntimeError(
            "Unexpected team CSV columns: " + ", ".join(map(str, frame.columns))
        )

    for column in ("company", "name", "description"):
        frame[column] = frame[column].map(_excel_safe_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    frame.to_csv(
        temporary_path,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
        quoting=csv.QUOTE_MINIMAL,
    )
    temporary_path.replace(output_path)
    return len(frame)
