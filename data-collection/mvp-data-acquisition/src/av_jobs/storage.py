"""Persistence adapters for JSON, Parquet, DuckDB and publication manifests."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd


def write_json(path: Path, value: object) -> None:
    """Write deterministic, human-readable UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    """Write an immutable Zstandard-compressed analytical snapshot."""

    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, engine="pyarrow", compression="zstd", index=False)


def _sql_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def build_duckdb(
    jobs_parquet: Path, source_status_parquet: Path, database_path: Path
) -> dict:
    """Build and summarise a run-specific DuckDB analytical database."""

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("SET TimeZone='UTC'")
        connection.execute(
            "CREATE OR REPLACE TABLE jobs AS "
            f"SELECT * FROM read_parquet('{_sql_path(jobs_parquet)}')"
        )
        connection.execute(
            "CREATE OR REPLACE TABLE source_status AS "
            f"SELECT * FROM read_parquet('{_sql_path(source_status_parquet)}')"
        )
        connection.execute(
            "CREATE OR REPLACE VIEW active_jobs AS SELECT * FROM jobs WHERE is_active"
        )
        connection.execute(
            "CREATE OR REPLACE VIEW jobs_with_quality_flags AS "
            "SELECT *, "
            "original_title IS NULL OR trim(original_title) = '' AS missing_title, "
            "source_url IS NULL OR trim(source_url) = '' AS missing_source_url, "
            "description_word_count < 30 AS short_description "
            "FROM jobs"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS jobs_source_key_idx "
            "ON jobs(company, source_job_id)"
        )

        def rows(sql: str) -> list[dict]:
            return connection.execute(sql).fetchdf().to_dict(orient="records")

        return {
            "active_jobs": connection.execute(
                "SELECT count(*) FROM active_jobs"
            ).fetchone()[0],
            "historical_jobs": connection.execute(
                "SELECT count(*) FROM jobs"
            ).fetchone()[0],
            "companies": connection.execute(
                "SELECT count(DISTINCT company) FROM active_jobs"
            ).fetchone()[0],
            "jobs_by_company": rows(
                "SELECT company, count(*) AS jobs FROM active_jobs "
                "GROUP BY company ORDER BY jobs DESC, company"
            ),
            "jobs_by_platform": rows(
                "SELECT source_name, count(*) AS jobs FROM active_jobs "
                "GROUP BY source_name ORDER BY jobs DESC"
            ),
            "source_status": rows(
                "SELECT spider, company, status, source_items_seen, validated_items "
                "FROM source_status ORDER BY company"
            ),
            "posting_date_range": rows(
                "SELECT min(posted_at_utc) AS earliest, max(posted_at_utc) AS latest "
                "FROM active_jobs"
            )[0],
            "quality_flags": rows(
                "SELECT "
                "sum(missing_title::INTEGER) AS missing_titles, "
                "sum(missing_source_url::INTEGER) AS missing_source_urls, "
                "sum(short_description::INTEGER) AS short_descriptions "
                "FROM jobs_with_quality_flags WHERE is_active"
            )[0],
        }
    finally:
        connection.close()


def load_latest_jobs(latest_manifest: Path) -> pd.DataFrame | None:
    """Load the previous published job snapshot, if one exists."""

    if not latest_manifest.exists():
        return None
    payload = json.loads(latest_manifest.read_text(encoding="utf-8"))
    jobs_path = Path(payload["jobs_parquet"])
    if not jobs_path.is_absolute():
        jobs_path = latest_manifest.parents[2] / jobs_path
    if not jobs_path.exists():
        raise FileNotFoundError(
            f"Latest manifest points to missing Parquet snapshot: {jobs_path}"
        )
    return pd.read_parquet(jobs_path)


def publish_latest(latest_manifest: Path, payload: dict) -> None:
    """Replace the pointer only after every output has been verified."""

    latest_manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = latest_manifest.with_suffix(".json.tmp")
    write_json(temporary, payload)
    temporary.replace(latest_manifest)
