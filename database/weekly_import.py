#!/usr/bin/env python3
"""Validate, import, back up, restore, and undo AV job data in MySQL.

Credentials are read from AVDB_HOST, AVDB_PORT, AVDB_USER, AVDB_PASSWORD,
AVDB_NAME. The importer joins stages only by source_key and never deactivates a
job merely because it is missing from an input file.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

if __package__:
    from .importer import ImportErrorSafe
    from .importer.hashing import (
        HASH_CONTRACT_VERSION,
        canonical_record_sha256,
        classifier_description_sha1,
    )
else:  # Support the documented ``python database/weekly_import.py`` entry point.
    from importer import ImportErrorSafe
    from importer.hashing import (
        HASH_CONTRACT_VERSION,
        canonical_record_sha256,
        classifier_description_sha1,
    )


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "database" / "schema.mysql.sql"
SENIORITY_CODES = {
    "intern": "intern", "internship": "intern", "graduate": "graduate",
    "new graduate": "graduate", "entry": "entry", "entry level": "entry",
    "junior": "junior", "mid": "mid", "mid-level": "mid",
    "senior": "senior", "lead": "lead", "staff": "staff",
    "principal": "principal", "manager": "manager",
    "senior manager": "senior_manager", "director": "director",
    "vp": "vp", "vice president": "vp", "executive": "other",
    "other": "other", "unknown": "unknown",
}
JOB_COLUMNS = (
    "source_key", "source_id", "source_job_id", "advertised_job_title",
    "job_description", "job_url", "location_raw", "city", "state_region",
    "country_code", "remote_type", "salary_raw", "salary_min", "salary_max",
    "salary_currency", "salary_period", "date_posted", "first_seen_date",
    "last_seen_date", "latest_collected_at", "is_active",
    "is_new_in_latest_run", "content_hash", "record_hash_sha256", "import_batch_id",
)
JOB_VALUE_COLUMNS = JOB_COLUMNS[:-1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_gzip_backup(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ImportErrorSafe(f"Backup does not exist or is empty: {path}")
    try:
        with gzip.open(path, "rb") as stream:
            while stream.read(1024 * 1024):
                pass
    except (OSError, EOFError) as exc:
        raise ImportErrorSafe(f"Backup is not a complete readable gzip file: {path.name}") from exc


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      default=json_default)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportErrorSafe(f"Cannot read JSON file {path.name}: {exc}") from exc


def parse_date(value: Any, field: str, *, required: bool = False) -> date | None:
    if value in (None, ""):
        if required:
            raise ImportErrorSafe(f"Missing required date: {field}")
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ImportErrorSafe(f"Invalid date in {field}: {value!r}") from exc


def parse_datetime(value: Any, field: str, *, required: bool = False) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ImportErrorSafe(f"Missing required timestamp: {field}")
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportErrorSafe(f"Invalid timestamp in {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def load_collection(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = load_json(path)
    if not isinstance(raw, list) or not raw:
        raise ImportErrorSafe("Collection input must be a non-empty JSON list")
    rows: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    seen_source_jobs: set[tuple[str, str]] = set()
    company_for_source: dict[str, tuple[str, str, str]] = {}
    for index, record in enumerate(raw, start=1):
        if not isinstance(record, dict):
            raise ImportErrorSafe(f"Row {index}: expected an object")
        meta, data = record.get("metadata"), record.get("data")
        if not isinstance(meta, dict) or not isinstance(data, dict):
            raise ImportErrorSafe(f"Row {index}: expected metadata and data objects")
        source_key = str(meta.get("source_key") or "").strip()
        source_id = str(meta.get("source_id") or "").strip()
        company = str(meta.get("company") or "").strip()
        platform = str(meta.get("platform") or "").strip().lower()
        region = str(meta.get("region") or "").strip()
        if not all((source_key, source_id, company, platform, region)):
            raise ImportErrorSafe(f"Row {index}: source_key/source_id/company/platform/region required")
        if len(source_key) > 191 or len(source_id) > 64:
            raise ImportErrorSafe(f"Row {index}: identifier exceeds MySQL schema length")
        if source_key in seen_keys:
            raise ImportErrorSafe(f"Duplicate source_key in input: {source_key}")
        seen_keys.add(source_key)
        source_job_id = meta.get("source_job_id")
        source_job_id = str(source_job_id) if source_job_id not in (None, "") else None
        if source_job_id and len(source_job_id) > 255:
            raise ImportErrorSafe(f"Row {index}: source_job_id exceeds the MySQL schema length")
        if source_job_id and (source_id, source_job_id) in seen_source_jobs:
            raise ImportErrorSafe(f"Duplicate source_id/source_job_id in input: {source_id}/{source_job_id}")
        if source_job_id:
            seen_source_jobs.add((source_id, source_job_id))
        source_identity = (company, platform, region)
        if source_id in company_for_source and company_for_source[source_id] != source_identity:
            raise ImportErrorSafe(f"source_id {source_id!r} maps to inconsistent company/platform/region")
        company_for_source[source_id] = source_identity
        active, is_new = meta.get("is_active"), meta.get("is_new_in_latest_run", False)
        if not isinstance(active, bool) or not isinstance(is_new, bool):
            raise ImportErrorSafe(f"Row {index}: is_active and is_new_in_latest_run must be booleans")
        first_seen = parse_date(meta.get("first_seen_date"), f"row {index} first_seen_date", required=True)
        last_seen = parse_date(meta.get("last_seen_date"), f"row {index} last_seen_date", required=True)
        if last_seen < first_seen:
            raise ImportErrorSafe(f"Row {index}: last_seen_date precedes first_seen_date")
        collected_at = parse_datetime(meta.get("collected_at"), f"row {index} collected_at", required=True)
        date_posted = parse_datetime(data.get("date_posted"), f"row {index} date_posted")
        salary = data.get("salary")
        if salary is not None and not isinstance(salary, (str, int, float, dict, list)):
            raise ImportErrorSafe(f"Row {index}: salary must be a string, number, object, array, or null")
        values = {
            "source_key": source_key, "source_id": source_id, "source_job_id": source_job_id,
            "advertised_job_title": data.get("advertised_job_title"),
            "job_description": data.get("job_description"), "job_url": data.get("job_url"),
            "location_raw": data.get("location"), "city": None, "state_region": None,
            "country_code": None, "remote_type": None,
            "salary_raw": salary if isinstance(salary, str) else (stable_json(salary) if salary is not None else None),
            "salary_min": None, "salary_max": None, "salary_currency": None, "salary_period": None,
            "date_posted": date_posted, "first_seen_date": first_seen, "last_seen_date": last_seen,
            "latest_collected_at": collected_at, "is_active": active,
            "is_new_in_latest_run": is_new, "import_batch_id": None,
            "company": company, "platform": platform, "region": region,
            "raw_record": record,
        }
        for text_field in ("advertised_job_title", "job_description", "job_url", "location_raw"):
            value = values[text_field]
            if value is not None and not isinstance(value, str):
                raise ImportErrorSafe(f"Row {index}: {text_field} must be a string or null")
        if not values["advertised_job_title"]:
            raise ImportErrorSafe(f"Row {index}: advertised_job_title is empty")
        max_lengths = {"company": 191, "platform": 40, "region": 80,
                       "advertised_job_title": 512, "job_url": 2048,
                       "location_raw": 1024, "salary_raw": 1024}
        for field, limit in max_lengths.items():
            if values.get(field) is not None and len(str(values[field])) > limit:
                raise ImportErrorSafe(f"Row {index}: {field} exceeds the MySQL schema length {limit}")
        values["content_hash"] = classifier_description_sha1(values["job_description"])
        values["record_hash_sha256"] = canonical_record_sha256(values)
        rows.append(values)
    return rows, sha256_file(path)


def collection_plan(rows: list[dict[str, Any]], digest: str,
                    previous_path: Path | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "file": "collection snapshot", "sha256": digest, "rows": len(rows),
        "hash_contract_version": HASH_CONTRACT_VERSION,
        "unique_source_keys": len({r["source_key"] for r in rows}),
        "sources": len({r["source_id"] for r in rows}),
        "companies": len({r["company"] for r in rows}),
        "active": sum(r["is_active"] for r in rows),
        "inactive": sum(not r["is_active"] for r in rows),
        "missing_description": sum(not r["job_description"] for r in rows),
        "snapshot_date": max(r["latest_collected_at"] for r in rows).date().isoformat(),
    }
    if previous_path:
        old, _ = load_collection(previous_path)
        old_by_key = {r["source_key"]: r for r in old}
        new_by_key = {r["source_key"]: r for r in rows}
        shared = old_by_key.keys() & new_by_key.keys()
        report["previous_rows"] = len(old)
        report["new_keys"] = len(new_by_key.keys() - old_by_key.keys())
        report["missing_from_new_file"] = len(old_by_key.keys() - new_by_key.keys())
        report["changed_existing"] = sum(
            any(old_by_key[k].get(field) != new_by_key[k].get(field)
                for field in (*JOB_VALUE_COLUMNS, "company", "platform", "region"))
            for k in shared
        )
        report["deactivated"] = sum(old_by_key[k]["is_active"] and not new_by_key[k]["is_active"]
                                    for k in shared)
        report["reactivated"] = sum(not old_by_key[k]["is_active"] and new_by_key[k]["is_active"]
                                    for k in shared)
    return report


def env_config() -> dict[str, Any]:
    required = ("AVDB_USER", "AVDB_PASSWORD")
    missing = [name for name in required if os.environ.get(name) is None]
    if missing:
        raise ImportErrorSafe("Set database credentials in environment variables: " + ", ".join(missing))
    return {
        "host": os.environ.get("AVDB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("AVDB_PORT", "3306")),
        "user": os.environ["AVDB_USER"], "password": os.environ["AVDB_PASSWORD"],
        "database": os.environ.get("AVDB_NAME", "av_job_profiles"),
        "charset": "utf8mb4", "autocommit": False, "connect_timeout": 8,
        "cursorclass": None,
    }


def db_connect():
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:
        raise ImportErrorSafe("Install database/requirements-import.txt in the active Python environment") from exc
    config = env_config()
    config["cursorclass"] = DictCursor
    try:
        return pymysql.connect(**config)
    except Exception as exc:
        raise ImportErrorSafe(f"Cannot connect to configured MySQL database: {exc}") from exc


def mysql_cli(name: str) -> str:
    configured = os.environ.get(name)
    if configured:
        return configured
    found = shutil.which("mysqldump" if name == "AVDB_MYSQLDUMP" else "mysql")
    if found:
        return found
    default = Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin") / (
        "mysqldump.exe" if name == "AVDB_MYSQLDUMP" else "mysql.exe")
    if default.exists():
        return str(default)
    raise ImportErrorSafe(f"Could not find {name}; install MySQL client tools or set its path")


def mysql_cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MYSQL_PWD"] = env_config()["password"]
    return env


def backup_database(backup_dir: Path) -> Path:
    config = env_config()
    command = [mysql_cli("AVDB_MYSQLDUMP"), "--single-transaction", "--triggers", "--routines",
               "--events", "--skip-lock-tables", "--set-gtid-purged=OFF",
               "--host", config["host"], "--port", str(config["port"]),
               "--user", config["user"], config["database"]]
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    final = backup_dir / f"{config['database']}_{stamp}_{os.getpid()}.sql.gz"
    temp = final.with_suffix(final.suffix + ".tmp")
    stderr_file = tempfile.TemporaryFile()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=stderr_file,
                            env=mysql_cli_env())
    try:
        with gzip.open(temp, "wb", compresslevel=6) as out:
            assert proc.stdout is not None
            shutil.copyfileobj(proc.stdout, out)
        proc.wait()
        stderr_file.seek(0)
        stderr = stderr_file.read()
        if proc.returncode:
            raise ImportErrorSafe(f"mysqldump failed: {stderr.decode(errors='replace').strip()}")
        verify_gzip_backup(temp)
        temp.replace(final)
        return final
    except Exception:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        temp.unlink(missing_ok=True)
        raise
    finally:
        stderr_file.close()


def restore_to_new_database(backup_path: Path, target: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", target):
        raise ImportErrorSafe("Target database name must use only letters, digits, and underscores")
    verify_gzip_backup(backup_path)
    config = env_config()
    check = db_connect()
    try:
        with check.cursor() as cur:
            cur.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s", (target,))
            if cur.fetchone():
                raise ImportErrorSafe(f"Target database {target!r} already exists; restore never overwrites a database")
    finally:
        check.close()
    create = [mysql_cli("AVDB_MYSQL"), "--host", config["host"], "--port", str(config["port"]),
              "--user", config["user"], "-e",
              f"CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"]
    created = subprocess.run(create, env=mysql_cli_env(), capture_output=True, text=True)
    if created.returncode:
        raise ImportErrorSafe(f"Could not create restore target: {created.stderr.strip()}")
    load = [mysql_cli("AVDB_MYSQL"), "--host", config["host"], "--port", str(config["port"]),
            "--user", config["user"], target]
    proc = subprocess.Popen(load, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=mysql_cli_env())
    try:
        with gzip.open(backup_path, "rb") as source:
            assert proc.stdin is not None
            shutil.copyfileobj(source, proc.stdin)
            proc.stdin.close()
        stdout = proc.stdout.read() if proc.stdout else b""
        stderr = proc.stderr.read() if proc.stderr else b""
        proc.wait()
        if proc.returncode:
            raise ImportErrorSafe(f"Restore failed; inspect {target!r}: {stderr.decode(errors='replace').strip()}")
    except Exception:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        raise


def acquire_import_lock(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT GET_LOCK('av_job_profiles_weekly_import', 10) AS locked")
        if cur.fetchone()["locked"] != 1:
            raise ImportErrorSafe("Another importer operation is running; retry after it finishes")


def release_import_lock(conn) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT RELEASE_LOCK('av_job_profiles_weekly_import')")
    except Exception:
        pass


def verify_schema(conn) -> None:
    required = {"import_batches", "import_job_undo", "companies", "job_sources", "collection_runs",
                "jobs", "job_observations", "analysis_runs", "job_analyses", "skills", "job_skills",
                "job_deduplication_links", "cluster_runs", "clusters", "cluster_label_revisions", "job_cluster_assignments",
                "cluster_skills", "dashboard_releases"}
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION() AS version")
        version = cur.fetchone()["version"]
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
        if "mariadb" in version.casefold() or not match or tuple(map(int, match.groups())) < (8, 0, 16):
            raise ImportErrorSafe(f"MySQL 8.0.16 or later is required; connected server reports {version!r}")
        cur.execute("SELECT TABLE_NAME,ENGINE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE()")
        table_rows = cur.fetchall()
        present = {row["TABLE_NAME"] for row in table_rows}
        missing = sorted(required - present)
        if missing:
            raise ImportErrorSafe(
                "Database schema is incomplete. For a new empty database, apply schema.mysql.sql; "
                "for an existing database, back up and apply only the missing migrations. "
                "Missing: " + ", ".join(missing)
            )
        non_transactional = sorted(row["TABLE_NAME"] for row in table_rows
                                   if row["TABLE_NAME"] in required and row["ENGINE"] != "InnoDB")
        if non_transactional:
            raise ImportErrorSafe("Rollback requires InnoDB tables; incompatible tables: " + ", ".join(non_transactional))
        cur.execute("SELECT TABLE_NAME,COLUMN_NAME,CHARACTER_MAXIMUM_LENGTH,COLLATION_NAME "
                    "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND "
                    "((TABLE_NAME='jobs' AND COLUMN_NAME IN "
                    "('source_key','source_job_id','content_hash','record_hash_sha256')) OR "
                    "(TABLE_NAME='job_observations' AND COLUMN_NAME IN ('content_hash','record_hash_sha256')) OR "
                    "(TABLE_NAME='job_analyses' AND COLUMN_NAME IN "
                    "('input_content_hash','role_summary','responsibilities_json','requirements_json',"
                    "'language_of_posting','served_by','prompt_tokens','output_tokens','cost_usd')) OR "
                    "(TABLE_NAME='analysis_runs' AND COLUMN_NAME IN "
                    "('run_key','prompt_tokens','output_tokens','cost_usd'))) ")
        columns = {(row["TABLE_NAME"], row["COLUMN_NAME"]): row for row in cur.fetchall()}
    required_columns = (
        ("jobs", "source_key"), ("jobs", "source_job_id"),
        ("jobs", "content_hash"), ("jobs", "record_hash_sha256"),
        ("job_observations", "content_hash"), ("job_observations", "record_hash_sha256"),
        ("job_analyses", "input_content_hash"), ("job_analyses", "role_summary"),
        ("job_analyses", "responsibilities_json"), ("job_analyses", "requirements_json"),
        ("job_analyses", "language_of_posting"), ("job_analyses", "served_by"),
        ("job_analyses", "prompt_tokens"), ("job_analyses", "output_tokens"),
        ("job_analyses", "cost_usd"), ("analysis_runs", "run_key"),
        ("analysis_runs", "prompt_tokens"), ("analysis_runs", "output_tokens"),
        ("analysis_runs", "cost_usd"),
    )
    for key in required_columns:
        if key not in columns:
            raise ImportErrorSafe(f"Required schema column {key[0]}.{key[1]} is missing")
    if columns[("jobs", "source_key")]["CHARACTER_MAXIMUM_LENGTH"] != 191 or not (
            columns[("jobs", "source_key")]["COLLATION_NAME"] or "").endswith("_bin"):
        raise ImportErrorSafe("jobs.source_key must be VARCHAR(191) with a case-sensitive binary collation; "
                              "apply migration 003_exact_source_key_collation.sql")
    hash_lengths = {
        ("jobs", "content_hash"): 40,
        ("jobs", "record_hash_sha256"): 64,
        ("job_observations", "content_hash"): 40,
        ("job_observations", "record_hash_sha256"): 64,
        ("job_analyses", "input_content_hash"): 40,
    }
    for key, expected_length in hash_lengths.items():
        if columns[key]["CHARACTER_MAXIMUM_LENGTH"] != expected_length:
            raise ImportErrorSafe(
                f"{key[0]}.{key[1]} must be CHAR({expected_length}) under the unified hash contract; "
                "apply migration 004_unified_hash_and_analysis_contract.sql"
            )
        if not (columns[key]["COLLATION_NAME"] or "").endswith("_bin"):
            raise ImportErrorSafe(f"{key[0]}.{key[1]} must use a binary hash collation; "
                                  "apply migration 004_unified_hash_and_analysis_contract.sql")
    for key in (("jobs", "source_job_id"), ("analysis_runs", "run_key")):
        if not (columns[key]["COLLATION_NAME"] or "").endswith("_bin"):
            raise ImportErrorSafe(f"{key[0]}.{key[1]} must use a case-sensitive binary collation; "
                                  "apply migration 004_unified_hash_and_analysis_contract.sql")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ImportErrorSafe(f"Company name cannot be converted to a stable slug: {value!r}")
    return slug[:191]


def ensure_source(cur, company: str, source_id: str, platform: str, region: str,
                  created_company_ids: list[int], created_source_ids: list[str]) -> None:
    slug = slugify(company)
    cur.execute("SELECT company_id, company_name FROM companies WHERE company_name=%s", (company,))
    company_row = cur.fetchone()
    if company_row is None:
        cur.execute("SELECT company_id, company_name FROM companies WHERE company_slug=%s", (slug,))
        collision = cur.fetchone()
        if collision:
            raise ImportErrorSafe(f"Company slug {slug!r} already belongs to {collision['company_name']!r}")
        cur.execute("INSERT INTO companies (company_name, company_slug) VALUES (%s, %s)", (company, slug))
        company_id = cur.lastrowid
        created_company_ids.append(company_id)
    else:
        company_id = company_row["company_id"]
    cur.execute("SELECT company_id, platform, region FROM job_sources WHERE source_id=%s", (source_id,))
    source_row = cur.fetchone()
    if source_row:
        if (source_row["company_id"] != company_id or source_row["platform"] != platform
                or source_row["region"] != region):
            raise ImportErrorSafe(f"Existing source {source_id!r} conflicts with company/platform/region")
    else:
        cur.execute("INSERT INTO job_sources (source_id, company_id, platform, region) VALUES (%s,%s,%s,%s)",
                    (source_id, company_id, platform, region))
        created_source_ids.append(source_id)


def row_fingerprint(row: dict[str, Any]) -> str:
    return hashlib.sha256(stable_json(row).encode("utf-8")).hexdigest()


def fetch_jobs_by_keys(cur, keys: list[str]) -> dict[str, dict[str, Any]]:
    result = {}
    for offset in range(0, len(keys), 400):
        group = keys[offset:offset + 400]
        placeholders = ",".join(["%s"] * len(group))
        cur.execute(f"SELECT * FROM jobs WHERE source_key IN ({placeholders})", group)
        result.update((row["source_key"], row) for row in cur.fetchall())
    return result


def insert_job_undo(cur, batch_id: int, key: str, kind: str,
                    previous: dict[str, Any] | None, after_hash: str) -> None:
    cur.execute(
        "INSERT INTO import_job_undo (import_batch_id, source_key, change_kind, previous_row_json, applied_row_sha256) "
        "VALUES (%s,%s,%s,%s,%s)",
        (batch_id, key, kind, stable_json(previous) if previous is not None else None, after_hash),
    )


def apply_collection(path: Path, backup_dir: Path) -> dict[str, Any]:
    rows, digest = load_collection(path)
    conn = db_connect()
    try:
        acquire_import_lock(conn)
        verify_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT import_batch_id FROM import_batches WHERE batch_type='collection' AND file_sha256=%s",
                        (digest,))
            if cur.fetchone():
                raise ImportErrorSafe("This exact collection file has already been imported; refusing to duplicate it")
            latest_collected = max(r["latest_collected_at"] for r in rows)
            run_date = latest_collected.date()
            cur.execute("SELECT metadata_json FROM import_batches WHERE batch_type='collection' "
                        "AND status IN ('completed','partial') ORDER BY import_batch_id DESC LIMIT 1")
            prior = cur.fetchone()
            if prior:
                prior_meta = as_object(prior["metadata_json"])
                prior_date = parse_date(prior_meta.get("snapshot_date"), "prior batch snapshot_date")
                prior_collected = parse_datetime(prior_meta.get("latest_collected_at"),
                                                 "prior batch latest_collected_at")
                if prior_date and run_date < prior_date:
                    raise ImportErrorSafe(f"This snapshot is older than the latest imported date {prior_date}")
                if prior_collected and latest_collected <= prior_collected:
                    raise ImportErrorSafe("This snapshot is not newer than the latest imported collection")
            backup_path = backup_database(backup_dir)
            backup_digest = sha256_file(backup_path)
            as_of = datetime.combine(run_date, time(23, 59, 59))
            run_key = f"history-{run_date:%Y%m%d}-{digest[:12]}"
            source_ids = sorted({r["source_id"] for r in rows})
            cur.execute(
                "INSERT INTO import_batches (batch_type,source_filename,file_sha256,status,total_rows,metadata_json) "
                "VALUES ('collection',%s,%s,'running',%s,%s)",
                (path.name, digest, len(rows), stable_json({"backup_file": str(backup_path),
                 "backup_sha256": backup_digest, "run_key": run_key,
                 "snapshot_date": run_date.isoformat(), "snapshot_sha256": digest,
                 "latest_collected_at": latest_collected.isoformat(),
                 "source_ids": source_ids, "synthetic_snapshot": True})),
            )
            batch_id = cur.lastrowid
            cur.execute(
                "INSERT INTO collection_runs (run_key,status,pipeline_version,source_scope_json,notes,started_at,completed_at) "
                "VALUES (%s,'partial','importer-v1',%s,%s,%s,%s)",
                (run_key, stable_json({"source_ids": source_ids, "input_sha256": digest}),
                 "Synthetic state snapshot from cumulative translated job history. Per-source crawl success records "
                 "were not supplied; absent keys are never treated as removals.", as_of, as_of),
            )
            collection_run_id = cur.lastrowid
            created_company_ids: list[int] = []
            created_source_ids: list[str] = []
            for source_id in source_ids:
                record = next(r for r in rows if r["source_id"] == source_id)
                ensure_source(cur, record["company"], source_id, record["platform"], record["region"],
                              created_company_ids, created_source_ids)

            current = fetch_jobs_by_keys(cur, [r["source_key"] for r in rows])
            stats = Counter()
            job_ids: dict[str, int] = {}
            columns = list(JOB_VALUE_COLUMNS)
            insert_columns = columns + ["import_batch_id"]
            insert_sql = (f"INSERT INTO jobs ({','.join(insert_columns)}) VALUES "
                          f"({','.join(['%s'] * len(insert_columns))})")
            update_columns = [c for c in columns if c != "source_key"] + ["import_batch_id"]
            update_sql = "UPDATE jobs SET " + ",".join(f"{c}=%s" for c in update_columns) + " WHERE job_id=%s"
            for record in rows:
                key = record["source_key"]
                values = tuple(record[c] for c in columns)
                old = current.get(key)
                if old is not None and old["source_id"] != record["source_id"]:
                    raise ImportErrorSafe(f"source_key {key!r} already belongs to another source_id")
                if old is None:
                    cur.execute(insert_sql, values + (batch_id,))
                    job_id = cur.lastrowid
                    cur.execute("SELECT * FROM jobs WHERE job_id=%s", (job_id,))
                    after = cur.fetchone()
                    insert_job_undo(cur, batch_id, key, "insert", None, row_fingerprint(after))
                    stats["inserted"] += 1
                else:
                    job_id = old["job_id"]
                    differs = any(old.get(c) != record.get(c) for c in columns)
                    if differs:
                        insert_job_undo(cur, batch_id, key, "update", old, "pending")
                        cur.execute(update_sql, tuple(record[c] for c in update_columns) + (job_id,))
                        cur.execute("SELECT * FROM jobs WHERE job_id=%s", (job_id,))
                        after = cur.fetchone()
                        cur.execute("UPDATE import_job_undo SET applied_row_sha256=%s "
                                    "WHERE import_batch_id=%s AND source_key=%s",
                                    (row_fingerprint(after), batch_id, key))
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1
                job_ids[key] = job_id
                cur.execute(
                    "INSERT INTO job_observations (job_id,collection_run_id,advertised_job_title,job_description,job_url,"
                    "location_raw,salary_raw,date_posted,collected_at,is_active_at_run,content_hash,"
                    "record_hash_sha256,raw_payload_json) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (job_id, collection_run_id, record["advertised_job_title"], record["job_description"],
                     record["job_url"], record["location_raw"], record["salary_raw"], record["date_posted"],
                     as_of, record["is_active"], record["content_hash"], record["record_hash_sha256"],
                     stable_json(record["raw_record"])),
                )
            metadata = {"backup_file": str(backup_path), "backup_sha256": backup_digest, "run_key": run_key,
                        "collection_run_id": collection_run_id, "snapshot_date": run_date.isoformat(),
                        "latest_collected_at": latest_collected.isoformat(),
                        "hash_contract_version": HASH_CONTRACT_VERSION,
                        "snapshot_sha256": digest, "source_ids": source_ids,
                        "created_company_ids": created_company_ids, "created_source_ids": created_source_ids,
                        "inserted": stats["inserted"], "updated": stats["updated"],
                        "unchanged": stats["unchanged"], "synthetic_snapshot": True}
            cur.execute("UPDATE import_batches SET status='completed',accepted_rows=%s,completed_at=UTC_TIMESTAMP(6),"
                        "metadata_json=%s WHERE import_batch_id=%s",
                        (len(rows), stable_json(metadata), batch_id))
        conn.commit()
        return {"status": "completed", "import_batch_id": batch_id, "collection_run_id": collection_run_id,
                "run_key": run_key, "rows": len(rows), **dict(stats), "backup": str(backup_path),
                "backup_sha256": backup_digest}
    except Exception:
        conn.rollback()
        raise
    finally:
        release_import_lock(conn)
        conn.close()


def read_cluster_summary(path: Path, group: str) -> dict[int, dict[str, Any]]:
    required = {"cluster_id", "size", "is_noise", "technical_score", "lean",
                "top_companies", "top_terms", "example_titles", "job_family",
                "specialisation", "notes"}
    result: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ImportErrorSafe(f"{group} cluster summary missing columns: {missing}")
        for line, row in enumerate(reader, start=2):
            try:
                cluster_id = int(row["cluster_id"])
                size = int(row["size"])
                score = Decimal(row["technical_score"]) if row["technical_score"].strip() else None
            except (ValueError, InvalidOperation, AttributeError) as exc:
                raise ImportErrorSafe(f"{path.name}:{line} has invalid cluster number, size, or score") from exc
            if cluster_id in result or size < 0 or (score is not None and not 0 <= score <= 1):
                raise ImportErrorSafe(f"{path.name}:{line} has duplicate cluster ID or invalid range")
            noise = row["is_noise"].strip().casefold() in {"true", "1", "yes"}
            if noise != (cluster_id == -1):
                raise ImportErrorSafe(f"{path.name}:{line}: this pipeline requires cluster -1 to be noise")
            lean = (row["lean"] or "").strip().casefold()
            lean = "noise" if noise or lean in {"n/a (noise)", "n/a", ""} else lean
            if lean not in {"technical", "corporate", "mixed", "noise"}:
                raise ImportErrorSafe(f"{path.name}:{line}: unsupported cluster lean {lean!r}")
            result[cluster_id] = {
                "cluster_id": cluster_id, "size": size, "is_noise": noise,
                "technical_score": score, "lean": lean,
                "top_companies": [v.strip() for v in (row["top_companies"] or "").split(";") if v.strip()],
                "top_terms": [v.strip() for v in (row["top_terms"] or "").split(",") if v.strip()],
                "example_titles": [v.strip() for v in (row["example_titles"] or "").split("|") if v.strip()],
                "job_family": (row["job_family"] or "").strip() or None,
                "specialisation": (row["specialisation"] or "").strip() or None,
                "notes": (row["notes"] or "").strip() or None,
                "group": group,
            }
    return result


def decimal_or_none(value: Any, field: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ImportErrorSafe(f"Invalid numeric value for {field}: {value!r}") from exc
    if not number.is_finite():
        raise ImportErrorSafe(f"Non-finite numeric value for {field}")
    return number


def token_count_or_none(value: Any, field: str, *, maximum: int) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ImportErrorSafe(f"{field} must be a non-negative whole number")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ImportErrorSafe(f"{field} must be a non-negative whole number") from exc
    if number < 0 or number > maximum or str(value).strip() not in (str(number), f"{number}.0"):
        raise ImportErrorSafe(f"{field} is outside the supported non-negative integer range")
    return number


def normalized_skill(value: str) -> str:
    return " ".join(value.casefold().split())


def seniority_code(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return SENIORITY_CODES.get(" ".join(str(value).casefold().split()), "other")


def read_failures(path: Path) -> list[dict[str, Any]]:
    result = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"source_key", "error"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise ImportErrorSafe(f"{path.name} must include source_key and error columns")
        seen: set[str] = set()
        for line, row in enumerate(reader, start=2):
            key = (row.get("source_key") or "").strip()
            if not key or key in seen:
                raise ImportErrorSafe(f"{path.name}:{line} has a blank or duplicate source_key")
            seen.add(key)
            try:
                row_index = int(row["row_index"]) if row.get("row_index") else None
            except ValueError as exc:
                raise ImportErrorSafe(f"{path.name}:{line} has invalid row_index") from exc
            result.append({"source_key": key, "error": (row.get("error") or "LLM returned no result"),
                           "row_index": row_index, "raw_record": dict(row)})
    return result


def read_duplicates(path: Path, source_by_key: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"source_key", "row_index", "duplicate_of_source_key", "duplicate_type", "similarity"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ImportErrorSafe(f"duplicates_removed.csv missing columns: {missing}")
        seen: set[str] = set()
        for line, row in enumerate(reader, start=2):
            key = (row.get("source_key") or "").strip()
            kept_key = (row.get("duplicate_of_source_key") or "").strip()
            if not key or not kept_key or key == kept_key or key in seen:
                raise ImportErrorSafe(f"{path.name}:{line} has invalid or repeated duplicate keys")
            if key not in source_by_key or kept_key not in source_by_key:
                raise ImportErrorSafe(f"{path.name}:{line} refers to a source_key absent from Li's input")
            duplicate, kept = source_by_key[key], source_by_key[kept_key]
            if duplicate["company"] != kept["company"]:
                raise ImportErrorSafe(f"Cross-company dedupe {key!r} -> {kept_key!r} requires human review")
            try:
                row_index = int(row["row_index"])
                similarity = Decimal(row["similarity"])
            except (ValueError, InvalidOperation) as exc:
                raise ImportErrorSafe(f"{path.name}:{line} has invalid row_index or similarity") from exc
            duplicate_type = row["duplicate_type"].strip().casefold()
            if duplicate_type not in {"exact", "near"} or not 0 <= similarity <= 1:
                raise ImportErrorSafe(f"{path.name}:{line} has invalid duplicate_type or similarity")
            if row.get("company") and row["company"].strip() != duplicate["company"]:
                raise ImportErrorSafe(f"{path.name}:{line} company does not match Li's source record")
            if row.get("name") and row["name"].strip() != (duplicate["advertised_job_title"] or "").strip():
                raise ImportErrorSafe(f"{path.name}:{line} title does not match Li's source record")
            seen.add(key)
            result.append({"source_key": key, "kept_source_key": kept_key, "duplicate_type": duplicate_type,
                           "similarity": similarity, "row_index": row_index})
    parent_by_key = {row["source_key"]: row["kept_source_key"] for row in result}
    for start_key in parent_by_key:
        visited: set[str] = set()
        current_key = start_key
        while current_key in parent_by_key:
            if current_key in visited:
                raise ImportErrorSafe(f"{path.name} contains a cyclic duplicate chain at {current_key!r}")
            visited.add(current_key)
            current_key = parent_by_key[current_key]
    return result


def load_analysis(postings_path: Path, metadata_path: Path, source_path: Path,
                  av_summary_path: Path, other_summary_path: Path,
                  duplicates_path: Path, failures_path: Path):
    postings = load_json(postings_path)
    metadata = load_json(metadata_path)
    if not isinstance(postings, list) or not postings or not isinstance(metadata, dict):
        raise ImportErrorSafe("postings_all.json must be a non-empty list and run_metadata.json an object")
    source_rows, source_digest = load_collection(source_path)
    source_by_key = {r["source_key"]: r for r in source_rows}
    output_by_key: dict[str, dict[str, Any]] = {}
    cluster_summaries = {
        "av_relevant": read_cluster_summary(av_summary_path, "av_relevant"),
        "not_av_relevant": read_cluster_summary(other_summary_path, "not_av_relevant"),
    }
    membership_counts: dict[str, Counter] = {name: Counter() for name in cluster_summaries}
    for index, row in enumerate(postings, start=1):
        key = str(row.get("source_key") or "").strip()
        if not key or key in output_by_key:
            raise ImportErrorSafe(f"postings_all row {index}: source_key is blank or duplicated")
        if key not in source_by_key:
            raise ImportErrorSafe(f"postings_all source_key does not exist in the supplied Li input: {key}")
        raw = source_by_key[key]
        if (row.get("company") or "").strip() != raw["company"] or \
                (row.get("name") or "").strip() != (raw["advertised_job_title"] or "").strip():
            raise ImportErrorSafe(f"postings_all row {index}: company/title do not match Li's source record for {key}")
        for output_field, input_field in (("platform", "platform"), ("region", "region"),
                                          ("location", "location_raw"), ("job_url", "job_url")):
            out_value, in_value = row.get(output_field) or "", raw.get(input_field) or ""
            if output_field == "platform":
                out_value, in_value = str(out_value).lower(), str(in_value).lower()
            if out_value != in_value:
                raise ImportErrorSafe(f"postings_all row {index}: {output_field} does not match Li's record for {key}")
        output_date = parse_datetime(row.get("date_posted"), f"postings_all row {index} date_posted")
        if output_date != raw.get("date_posted"):
            raise ImportErrorSafe(f"postings_all row {index}: date_posted does not match Li's record for {key}")
        if not isinstance(row.get("av_relevant"), bool):
            raise ImportErrorSafe(f"postings_all row {index}: av_relevant must be a JSON boolean")
        record = row.get("record")
        if not isinstance(record, dict) or not isinstance(record.get("skills"), dict):
            raise ImportErrorSafe(f"postings_all row {index}: full LLM record with skills is required")
        expected_input_hash = raw["content_hash"]
        exported_input_hash = row.get("input_content_hash") or row.get("content_hash")
        if exported_input_hash and exported_input_hash != expected_input_hash:
            raise ImportErrorSafe(
                f"postings_all row {index}: classifier input content_hash does not match the supplied source description for {key}"
            )
        group = "av_relevant" if row["av_relevant"] else "not_av_relevant"
        try:
            cluster_id = int(row["cluster_id"])
        except (TypeError, ValueError) as exc:
            raise ImportErrorSafe(f"postings_all row {index}: invalid cluster_id") from exc
        if cluster_id not in cluster_summaries[group]:
            raise ImportErrorSafe(f"postings_all row {index}: cluster {cluster_id} missing from {group} summary")
        membership_counts[group][cluster_id] += 1
        output_by_key[key] = {
            **row,
            "cluster_id": cluster_id,
            "group": group,
            "record": record,
            "classifier_input_hash": expected_input_hash,
        }
    for group, summaries in cluster_summaries.items():
        counts = membership_counts[group]
        if set(counts) != set(summaries):
            raise ImportErrorSafe(f"{group} cluster summary contains a cluster with no matching postings, or vice versa")
        for cluster_id, summary in summaries.items():
            if counts[cluster_id] != summary["size"]:
                raise ImportErrorSafe(f"{group} cluster {cluster_id}: summary size {summary['size']} "
                                      f"does not match {counts[cluster_id]} assignments")
    duplicates = read_duplicates(duplicates_path, source_by_key)
    failures = read_failures(failures_path)
    output_keys = set(output_by_key)
    duplicate_keys = {row["source_key"] for row in duplicates}
    failure_keys = {row["source_key"] for row in failures}
    if output_keys & duplicate_keys or output_keys & failure_keys or duplicate_keys & failure_keys:
        raise ImportErrorSafe("A source_key appears in more than one pipeline outcome")
    if output_keys | duplicate_keys | failure_keys != set(source_by_key):
        uncovered = set(source_by_key) - (output_keys | duplicate_keys | failure_keys)
        unknown = (output_keys | duplicate_keys | failure_keys) - set(source_by_key)
        raise ImportErrorSafe(f"Pipeline outcomes do not cover the Li input; uncovered={len(uncovered)}, unknown={len(unknown)}")
    required_counts = ("n_input_rows", "n_after_dedupe", "n_duplicates_removed", "n_records", "n_llm_failures")
    if any(name not in metadata for name in required_counts):
        raise ImportErrorSafe("run_metadata.json lacks required row-count fields")
    counts = {name: int(metadata[name]) for name in required_counts}
    recorded_input = Path(str(metadata.get("input") or "")).name
    if recorded_input and recorded_input != source_path.name:
        raise ImportErrorSafe(f"run_metadata input is {recorded_input!r}, but supplied Li file is {source_path.name!r}")
    if counts["n_records"] != len(postings):
        raise ImportErrorSafe("run_metadata n_records does not match postings_all.json")
    if counts["n_input_rows"] != len(source_rows):
        raise ImportErrorSafe("run_metadata n_input_rows does not match the supplied Li input")
    if counts["n_after_dedupe"] + counts["n_duplicates_removed"] != counts["n_input_rows"]:
        raise ImportErrorSafe("run_metadata dedupe counts do not reconcile")
    if counts["n_records"] + counts["n_llm_failures"] != counts["n_after_dedupe"]:
        raise ImportErrorSafe("postings_all plus LLM failures do not cover the deduplicated input")
    if counts["n_duplicates_removed"] != len(duplicates) or counts["n_llm_failures"] != len(failures):
        raise ImportErrorSafe("run_metadata dedupe/failure totals do not match the detail CSV files")
    if counts["n_records"] + counts["n_duplicates_removed"] + counts["n_llm_failures"] != counts["n_input_rows"]:
        raise ImportErrorSafe("classified, deduplicated, and failed records do not cover the original input")
    hashes = {
        "postings": sha256_file(postings_path), "metadata": sha256_file(metadata_path),
        "source_input": source_digest, "av_summary": sha256_file(av_summary_path),
        "other_summary": sha256_file(other_summary_path), "duplicates": sha256_file(duplicates_path),
        "failures": sha256_file(failures_path),
    }
    report = {
        "postings": len(postings), "unique_source_keys": len(output_by_key),
        "source_input_rows": len(source_rows), "source_input_sha256": source_digest,
        "analysis_sha256": hashlib.sha256(stable_json(hashes).encode("utf-8")).hexdigest(),
        "av_relevant": sum(r["av_relevant"] for r in postings),
        "not_av_relevant": sum(not r["av_relevant"] for r in postings),
        "llm_failures": counts["n_llm_failures"], "duplicates_removed": counts["n_duplicates_removed"],
        "av_clusters": len(cluster_summaries["av_relevant"]),
        "other_clusters": len(cluster_summaries["not_av_relevant"]),
        "metadata": metadata, "rows_by_key": output_by_key,
        "source_by_key": source_by_key, "cluster_summaries": cluster_summaries,
        "duplicates": duplicates, "failures": failures,
    }
    return report


def get_or_create_skill(cur, name: str, skill_type: str,
                        created_skill_ids: list[int]) -> int:
    normalized = normalized_skill(name)
    if not normalized or len(name) > 191 or len(normalized) > 191:
        raise ImportErrorSafe(f"Invalid or overlong skill name: {name!r}")
    cur.execute("SELECT skill_id FROM skills WHERE normalized_name=%s AND skill_type=%s", (normalized, skill_type))
    found = cur.fetchone()
    if found:
        return found["skill_id"]
    cur.execute("INSERT INTO skills (canonical_name,normalized_name,skill_type) VALUES (%s,%s,%s)",
                (name.strip(), normalized, skill_type))
    skill_id = cur.lastrowid
    created_skill_ids.append(skill_id)
    return skill_id


def apply_analysis(postings_path: Path, metadata_path: Path, source_path: Path,
                   av_summary_path: Path, other_summary_path: Path,
                   duplicates_path: Path, failures_path: Path, backup_dir: Path,
                   git_commit: str | None = None) -> dict[str, Any]:
    if not git_commit or not re.fullmatch(r"[0-9a-fA-F]{7,64}", git_commit):
        raise ImportErrorSafe("Provide the classification pipeline Git commit with --git-commit (7–64 hex characters)")
    report = load_analysis(postings_path, metadata_path, source_path, av_summary_path, other_summary_path,
                           duplicates_path, failures_path)
    digest = report["analysis_sha256"]
    metadata = report["metadata"]
    conn = db_connect()
    try:
        acquire_import_lock(conn)
        verify_schema(conn)
        backup_path = backup_database(backup_dir)
        backup_digest = sha256_file(backup_path)
        with conn.cursor() as cur:
            cur.execute("SELECT import_batch_id FROM import_batches WHERE batch_type='analysis' AND file_sha256=%s",
                        (digest,))
            if cur.fetchone():
                raise ImportErrorSafe("This exact analysis output has already been imported")
            digest_source = report["source_input_sha256"]
            current_jobs = fetch_jobs_by_keys(cur, list(report["source_by_key"]))
            missing = sorted(set(report["source_by_key"]) - set(current_jobs))
            if missing:
                raise ImportErrorSafe(f"{len(missing)} Li input keys are not in canonical jobs; first: {missing[0]}")
            for key, source in report["source_by_key"].items():
                current = current_jobs[key]
                if current["record_hash_sha256"] != source["record_hash_sha256"]:
                    raise ImportErrorSafe(f"Li source record {key!r} differs from current database state; re-collect/reclassify")
                if current["content_hash"] != source["content_hash"]:
                    raise ImportErrorSafe(f"Classifier description hash for {key!r} differs from current database state; reclassify")
                if current["source_id"] != source["source_id"]:
                    raise ImportErrorSafe(f"Li source_id for {key!r} differs from current database state")
            cur.execute("SELECT metadata_json FROM import_batches "
                        "WHERE batch_type='collection' AND JSON_UNQUOTE(JSON_EXTRACT(metadata_json,'$.snapshot_sha256'))=%s "
                        "AND status='completed' ORDER BY import_batch_id DESC LIMIT 1", (digest_source,))
            source_batch = cur.fetchone()
            if not source_batch:
                raise ImportErrorSafe("The supplied Li snapshot is not imported as a collection batch in this database")
            source_meta = source_batch["metadata_json"]
            if isinstance(source_meta, str):
                source_meta = json.loads(source_meta)
            collection_run_id = source_meta.get("collection_run_id")
            if not collection_run_id:
                raise ImportErrorSafe("The matching collection batch has no collection_run_id")
            run_key = f"sunjol-{digest[:20]}"
            analysis_method = str(metadata.get("method") or "hybrid").strip().lower()
            provider = str(metadata.get("provider") or "openrouter").strip()
            if analysis_method not in {"llm", "dictionary", "hybrid", "manual"}:
                raise ImportErrorSafe(f"Unsupported run_metadata.method: {analysis_method!r}")
            if len(provider) > 64:
                raise ImportErrorSafe("run_metadata.provider exceeds 64 characters")
            cur.execute("INSERT INTO import_batches (batch_type,source_filename,file_sha256,status,total_rows,metadata_json) "
                        "VALUES ('analysis',%s,%s,'running',%s,%s)",
                        (postings_path.name, digest, int(metadata["n_input_rows"]),
                         stable_json({"backup_file": str(backup_path), "backup_sha256": backup_digest,
                                      "collection_run_id": collection_run_id,
                                      "source_input_sha256": digest_source, "analysis_sha256": digest})))
            batch_id = cur.lastrowid
            started = parse_datetime(metadata.get("started_at"), "run_metadata.started_at") or datetime.now(timezone.utc).replace(tzinfo=None)
            completed = started + __import__("datetime").timedelta(seconds=float(metadata.get("runtime_seconds", 0) or 0))
            parameters = {key: metadata.get(key) for key in (
                "embedding_model", "embedded_text", "min_cluster_size", "min_samples", "n_input_rows",
                "n_after_dedupe", "n_duplicates_removed", "n_records", "n_llm_failures", "languages", "groups",
                "temperature", "n_api_postings", "n_cached", "prompt_tokens", "output_tokens", "cost_usd")}
            parameters["hash_contract_version"] = HASH_CONTRACT_VERSION
            cur.execute(
                "INSERT INTO analysis_runs (run_key,method,provider,model_name,model_version,prompt_version,"
                "taxonomy_version,code_version,source_dataset_version,parameters_json,prompt_tokens,output_tokens,"
                "cost_usd,status,notes,"
                "started_at,completed_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (run_key, analysis_method, provider, metadata.get("model"), metadata.get("model_version"),
                 metadata.get("prompt_version"), metadata.get("taxonomy_version"), git_commit,
                 Path(str(metadata.get("input") or source_path.name)).name, stable_json(parameters),
                 token_count_or_none(metadata.get("prompt_tokens"), "run_metadata.prompt_tokens",
                                     maximum=18_446_744_073_709_551_615),
                 token_count_or_none(metadata.get("output_tokens"), "run_metadata.output_tokens",
                                     maximum=18_446_744_073_709_551_615),
                 decimal_or_none(metadata.get("cost_usd"), "run_metadata.cost_usd"),
                 "partial" if report["llm_failures"] else "completed",
                 "LLM per-posting extraction with local embeddings/clustering. Cluster naming remains a separate "
                 "manual review step. Per-posting cache status is unavailable, so results are recorded as imported.",
                 started, completed),
            )
            analysis_run_id = cur.lastrowid
            cur.execute("INSERT INTO cluster_runs (run_key,analysis_run_id,algorithm,algorithm_version,"
                        "requested_cluster_count,produced_cluster_count,includes_noise,parameters_json,status,notes,"
                        "started_at,completed_at) VALUES (%s,%s,'UMAP+HDBSCAN','pipeline-v2',%s,%s,TRUE,%s,'completed',%s,%s,%s)",
                        (run_key + "-clusters", analysis_run_id,
                         int(metadata.get("min_cluster_size", 0) or 0),
                         sum(1 for group in report["cluster_summaries"].values()
                             for summary in group.values() if not summary["is_noise"]),
                         stable_json({"min_samples": metadata.get("min_samples"),
                                      "av_relevant_and_other_clustered_separately": True,
                                      "non_av_noise_cluster_number": -2}),
                         "Non-AV clusters are kept in this combined run. Their noise ID -1 is remapped to -2 "
                         "to preserve both populations in the single-run release schema.", started, completed))
            cluster_run_id = cur.lastrowid

            cluster_pks: dict[tuple[str, int], int] = {}
            cluster_sizes: dict[int, int] = {}
            for group, summaries in report["cluster_summaries"].items():
                for original_id, summary in summaries.items():
                    db_cluster_id = -2 if group == "not_av_relevant" and original_id == -1 else original_id
                    cur.execute("INSERT INTO clusters (cluster_run_id,cluster_number,job_family,specialisation,lean,"
                                "is_noise,size_cached,technical_score,top_terms_json,example_titles_json,"
                                "top_companies_json,notes) VALUES (%s,%s,NULL,NULL,%s,%s,%s,%s,%s,%s,%s,%s)",
                                (cluster_run_id, db_cluster_id, summary["lean"], summary["is_noise"],
                                 summary["size"], summary["technical_score"], stable_json(summary["top_terms"]),
                                 stable_json(summary["example_titles"]), stable_json(summary["top_companies"]),
                                 summary["notes"]))
                    cluster_pk = cur.lastrowid
                    cluster_pks[(group, original_id)] = cluster_pk
                    cluster_sizes[cluster_pk] = summary["size"]
                    family, specialisation = summary["job_family"], summary["specialisation"]
                    if family or specialisation:
                        label = " / ".join(v for v in (family, specialisation) if v)
                        cur.execute("INSERT INTO cluster_label_revisions (cluster_pk,revision_number,label_source,"
                                    "label_status,proposed_cluster_name,proposed_job_family,proposed_specialisation,"
                                    "rationale,labelled_by) VALUES (%s,1,'imported','proposed',%s,%s,%s,%s,%s)",
                                    (cluster_pk, label, family, specialisation, summary["notes"],
                                     "Sunjol pipeline import"))

            skill_ids_created: list[int] = []
            skill_usage: dict[int, Counter] = {cluster_pk: Counter() for cluster_pk in cluster_pks.values()}
            for key, row in report["rows_by_key"].items():
                source_job = current_jobs[key]
                rec = row["record"]
                responsibilities = rec.get("responsibilities") or []
                requirements = rec.get("requirements") or []
                seniority_raw = rec.get("seniority")
                evidence = []
                cur.execute(
                    "INSERT INTO job_analyses (job_id,analysis_run_id,source_row_index,analysis_status,result_origin,"
                    "av_relevant,relevance_confidence_label,relevance_reason,technical_responsibilities,role_summary,"
                    "responsibilities_json,requirements_json,language_of_posting,generic_job_title,"
                    "seniority_code,seniority_raw,seniority_source,experience_min_years,experience_max_years,"
                    "experience_evidence,key_evidence_json,raw_response_json,input_content_hash,served_by,"
                    "prompt_tokens,output_tokens,cost_usd,import_batch_id) "
                    "VALUES (%s,%s,%s,'success','imported',%s,%s,%s,%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                    "%s,%s,%s,%s,%s)",
                    (source_job["job_id"], analysis_run_id, row.get("row_index"), row["av_relevant"],
                     row.get("relevance_confidence"), row.get("relevance_reason"),
                     "\n".join(str(v) for v in responsibilities) or None,
                     rec.get("role_summary"), stable_json(responsibilities), stable_json(requirements),
                     rec.get("language_of_posting") or row.get("language_of_posting"),
                     seniority_code(seniority_raw), str(seniority_raw) if seniority_raw is not None else None,
                     row.get("seniority_source"), decimal_or_none(rec.get("experience_min"), "experience_min"),
                     decimal_or_none(rec.get("experience_max"), "experience_max"), row.get("experience_evidence"),
                     stable_json([skill.get("evidence") for cat in ("tools", "domain", "qualifications")
                                  for skill in (rec.get("skills", {}).get(cat) or []) if skill.get("evidence")]),
                     stable_json(rec), row["classifier_input_hash"], row.get("served_by"),
                     token_count_or_none(row.get("prompt_tokens"), "postings_all.prompt_tokens",
                                         maximum=4_294_967_295),
                     token_count_or_none(row.get("output_tokens"), "postings_all.output_tokens",
                                         maximum=4_294_967_295),
                     decimal_or_none(row.get("cost_usd"), "postings_all.cost_usd"), batch_id),
                )
                job_analysis_id = cur.lastrowid
                cluster_pk = cluster_pks[(row["group"], row["cluster_id"])]
                cur.execute("INSERT INTO job_cluster_assignments (job_analysis_id,analysis_run_id,cluster_run_id,cluster_pk) "
                            "VALUES (%s,%s,%s,%s)", (job_analysis_id, analysis_run_id, cluster_run_id, cluster_pk))
                for category, skill_type in (("tools", "tool"), ("domain", "domain"),
                                             ("qualifications", "qualification")):
                    unique_skills: dict[int, tuple[str, str]] = {}
                    for skill in rec.get("skills", {}).get(category, []) or []:
                        if not isinstance(skill, dict) or not isinstance(skill.get("name"), str) or not skill["name"].strip():
                            raise ImportErrorSafe(f"Invalid {category} skill for source_key {key}")
                        name = skill["name"].strip()
                        skill_id = get_or_create_skill(cur, name, skill_type, skill_ids_created)
                        unique_skills.setdefault(skill_id, (name, skill.get("evidence", "")))
                    for rank, (skill_id, (name, proof)) in enumerate(unique_skills.items(), start=1):
                        cur.execute("INSERT INTO job_skills (job_analysis_id,skill_id,raw_skill_text,evidence,skill_rank) "
                                    "VALUES (%s,%s,%s,%s,%s)", (job_analysis_id, skill_id, name, proof or None, rank))
                        skill_usage[cluster_pk][skill_id] += 1
            for failure in report["failures"]:
                source_job = current_jobs[failure["source_key"]]
                failure_hash = report["source_by_key"][failure["source_key"]]["content_hash"]
                cur.execute("INSERT INTO job_analyses (job_id,analysis_run_id,source_row_index,analysis_status,"
                            "result_origin,raw_response_json,input_content_hash,import_batch_id) "
                            "VALUES (%s,%s,%s,'failed','imported',%s,%s,%s)",
                            (source_job["job_id"], analysis_run_id, failure["row_index"],
                             stable_json({"error": failure["error"], "source_row": failure["raw_record"]}),
                             failure_hash, batch_id))
            for duplicate in report["duplicates"]:
                duplicate_job = current_jobs[duplicate["source_key"]]
                kept_job = current_jobs[duplicate["kept_source_key"]]
                cur.execute("INSERT INTO job_deduplication_links (analysis_run_id,duplicate_job_id,kept_job_id,"
                            "duplicate_type,similarity,source_row_index) VALUES (%s,%s,%s,%s,%s,%s)",
                            (analysis_run_id, duplicate_job["job_id"], kept_job["job_id"],
                             duplicate["duplicate_type"], duplicate["similarity"], duplicate["row_index"]))
            for cluster_pk, frequencies in skill_usage.items():
                for rank, (skill_id, count) in enumerate(frequencies.most_common(), start=1):
                    cluster_size = cluster_sizes[cluster_pk]
                    cur.execute("INSERT INTO cluster_skills (cluster_pk,skill_id,skill_rank,score,job_frequency) "
                                "VALUES (%s,%s,%s,%s,%s)",
                                (cluster_pk, skill_id, rank, Decimal(count) / max(cluster_size, 1), count))

            release_key = f"draft-{digest[:24]}"
            cutoff = max(r["last_seen_date"] for r in report["source_by_key"].values())
            cur.execute("INSERT INTO dashboard_releases (release_key,collection_run_id,analysis_run_id,cluster_run_id,"
                        "data_cutoff_date,status,notes) VALUES (%s,%s,%s,%s,%s,'draft',%s)",
                        (release_key, collection_run_id, analysis_run_id, cluster_run_id, cutoff,
                         "Candidate release from imported Sunjol analysis. It requires QA and approval before publication."))
            release_id = cur.lastrowid
            batch_metadata = {"backup_file": str(backup_path), "backup_sha256": backup_digest,
                              "analysis_run_id": analysis_run_id,
                              "cluster_run_id": cluster_run_id, "dashboard_release_id": release_id,
                              "collection_run_id": collection_run_id, "source_input_sha256": digest_source,
                              "analysis_sha256": digest, "created_skill_ids": skill_ids_created,
                              "analysis_key_count": report["postings"], "release_key": release_key}
            cur.execute("UPDATE import_batches SET status=%s,accepted_rows=%s,rejected_rows=%s,completed_at=UTC_TIMESTAMP(6),"
                        "metadata_json=%s WHERE import_batch_id=%s",
                        ("partial" if report["llm_failures"] else "completed", int(metadata["n_input_rows"]),
                         0, stable_json(batch_metadata), batch_id))
        conn.commit()
        return {"status": "partial" if report["llm_failures"] else "completed",
                "import_batch_id": batch_id, "analysis_run_id": analysis_run_id,
                "cluster_run_id": cluster_run_id, "draft_release_id": release_id,
                "postings": report["postings"], "av_relevant": report["av_relevant"],
                "not_av_relevant": report["not_av_relevant"], "duplicates_mapped": report["duplicates_removed"],
                "llm_failures_recorded": report["llm_failures"], "backup": str(backup_path),
                "backup_sha256": backup_digest}
    except Exception:
        conn.rollback()
        raise
    finally:
        release_import_lock(conn)
        conn.close()


def as_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise ImportErrorSafe("Database audit metadata is not a JSON object")


def rollback_latest(batch_id: int | None, backup_dir: Path) -> dict[str, Any]:
    conn = db_connect()
    backup_path: Path | None = None
    try:
        acquire_import_lock(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM import_batches WHERE status IN ('completed','partial') "
                        "ORDER BY import_batch_id DESC LIMIT 1")
            latest = cur.fetchone()
            if not latest:
                raise ImportErrorSafe("There is no completed or partial batch to roll back")
            if batch_id is not None and int(latest["import_batch_id"]) != batch_id:
                raise ImportErrorSafe(f"Only the latest batch can be rolled back safely; latest is {latest['import_batch_id']}")
            batch_id = int(latest["import_batch_id"])
            metadata = as_object(latest["metadata_json"])
            cur.execute("SELECT COUNT(*) AS n FROM import_batches WHERE import_batch_id>%s "
                        "AND status IN ('completed','partial')", (batch_id,))
            if cur.fetchone()["n"]:
                raise ImportErrorSafe("A newer successful batch exists; roll back newer work first")
            backup_path = backup_database(backup_dir)
            backup_digest = sha256_file(backup_path)
            if latest["batch_type"] == "collection":
                collection_run_id = metadata.get("collection_run_id")
                if not collection_run_id:
                    raise ImportErrorSafe("Collection batch lacks its collection_run_id; cannot undo safely")
                cur.execute("SELECT COUNT(*) AS n FROM dashboard_releases WHERE collection_run_id=%s",
                            (collection_run_id,))
                if cur.fetchone()["n"]:
                    raise ImportErrorSafe("A dashboard release uses this collection snapshot; retire that release first")
                cur.execute("SELECT source_key,change_kind,previous_row_json,applied_row_sha256 "
                            "FROM import_job_undo WHERE import_batch_id=%s", (batch_id,))
                undo_rows = cur.fetchall()
                keys = [row["source_key"] for row in undo_rows]
                current = fetch_jobs_by_keys(cur, keys)
                for undo in undo_rows:
                    key = undo["source_key"]
                    now_row = current.get(key)
                    if now_row is None or row_fingerprint(now_row) != undo["applied_row_sha256"]:
                        raise ImportErrorSafe(f"Job {key!r} changed after this batch; refusing to overwrite later work")
                inserted_keys = [u["source_key"] for u in undo_rows if u["change_kind"] == "insert"]
                if inserted_keys:
                    cur.execute("SELECT COUNT(*) AS n FROM job_analyses ja JOIN jobs j USING (job_id) "
                                "WHERE j.source_key IN (" + ",".join(["%s"] * len(inserted_keys)) + ")",
                                inserted_keys)
                    if cur.fetchone()["n"]:
                        raise ImportErrorSafe("A later classification references jobs created by this batch")
                cur.execute("SELECT COUNT(*) AS n FROM job_analyses ja JOIN analysis_runs ar USING (analysis_run_id) "
                            "JOIN jobs j USING (job_id) JOIN import_job_undo u USING (source_key) "
                            "WHERE u.import_batch_id=%s AND ar.created_at>%s", (batch_id, latest["completed_at"]))
                if cur.fetchone()["n"]:
                    raise ImportErrorSafe("A later analysis references jobs changed by this batch")
                cur.execute("DELETE FROM job_observations WHERE collection_run_id=%s", (collection_run_id,))
                cur.execute("DELETE FROM jobs WHERE import_batch_id=%s AND source_key IN "
                            "(SELECT source_key FROM import_job_undo WHERE import_batch_id=%s AND change_kind='insert')",
                            (batch_id, batch_id))
                update_undo = [u for u in undo_rows if u["change_kind"] == "update"]
                if update_undo:
                    placeholders = ",".join(["%s"] * len(update_undo))
                    cur.execute(f"UPDATE jobs SET source_job_id=NULL WHERE source_key IN ({placeholders})",
                                [u["source_key"] for u in update_undo])
                restore_columns = list(JOB_COLUMNS) + ["created_at", "updated_at"]
                assignment = ",".join(f"{column}=%s" for column in restore_columns if column != "job_id")
                restore_columns = [column for column in restore_columns if column != "job_id"]
                for undo in update_undo:
                    previous = as_object(undo["previous_row_json"])
                    cur.execute(f"UPDATE jobs SET {assignment} WHERE job_id=%s",
                                tuple(previous.get(column) for column in restore_columns) + (previous["job_id"],))
                for source_id in metadata.get("created_source_ids", []):
                    cur.execute("DELETE FROM job_sources WHERE source_id=%s AND NOT EXISTS "
                                "(SELECT 1 FROM jobs WHERE source_id=%s) AND NOT EXISTS "
                                "(SELECT 1 FROM source_run_results WHERE source_id=%s)",
                                (source_id, source_id, source_id))
                for company_id in metadata.get("created_company_ids", []):
                    cur.execute("DELETE FROM companies WHERE company_id=%s AND NOT EXISTS "
                                "(SELECT 1 FROM job_sources WHERE company_id=%s)", (company_id, company_id))
                cur.execute("DELETE FROM collection_runs WHERE collection_run_id=%s", (collection_run_id,))
            elif latest["batch_type"] == "analysis":
                analysis_run_id = metadata.get("analysis_run_id")
                cluster_run_id = metadata.get("cluster_run_id")
                release_id = metadata.get("dashboard_release_id")
                if not all((analysis_run_id, cluster_run_id, release_id)):
                    raise ImportErrorSafe("Analysis batch audit metadata is incomplete; cannot undo safely")
                cur.execute("SELECT status FROM dashboard_releases WHERE dashboard_release_id=%s", (release_id,))
                release = cur.fetchone()
                if release and release["status"] == "published":
                    raise ImportErrorSafe("This candidate release has been published; create a new corrective release instead")
                cur.execute("SELECT COUNT(*) AS n FROM clusters c JOIN cluster_label_revisions l USING (cluster_pk) "
                            "WHERE c.cluster_run_id=%s AND (l.label_status='approved' OR c.current_label_revision_id=l.cluster_label_revision_id)",
                            (cluster_run_id,))
                if cur.fetchone()["n"]:
                    raise ImportErrorSafe("A cluster label from this run has been approved; preserve it and create a new run")
                cur.execute("DELETE FROM dashboard_releases WHERE dashboard_release_id=%s", (release_id,))
                cur.execute("DELETE FROM job_deduplication_links WHERE analysis_run_id=%s", (analysis_run_id,))
                cur.execute("DELETE FROM job_cluster_assignments WHERE cluster_run_id=%s", (cluster_run_id,))
                cur.execute("DELETE FROM cluster_skills WHERE cluster_pk IN "
                            "(SELECT cluster_pk FROM clusters WHERE cluster_run_id=%s)", (cluster_run_id,))
                cur.execute("DELETE FROM cluster_label_revisions WHERE cluster_pk IN "
                            "(SELECT cluster_pk FROM clusters WHERE cluster_run_id=%s)", (cluster_run_id,))
                cur.execute("DELETE FROM cluster_runs WHERE cluster_run_id=%s", (cluster_run_id,))
                cur.execute("DELETE FROM job_analyses WHERE analysis_run_id=%s", (analysis_run_id,))
                cur.execute("DELETE FROM analysis_runs WHERE analysis_run_id=%s", (analysis_run_id,))
                for skill_id in metadata.get("created_skill_ids", []):
                    cur.execute("DELETE FROM skills WHERE skill_id=%s AND NOT EXISTS "
                                "(SELECT 1 FROM job_skills WHERE skill_id=%s) AND NOT EXISTS "
                                "(SELECT 1 FROM cluster_skills WHERE skill_id=%s)",
                                (skill_id, skill_id, skill_id))
            else:
                raise ImportErrorSafe(f"Unsupported batch type for rollback: {latest['batch_type']!r}")
            old_metadata = metadata.copy()
            old_metadata.update({"rolled_back_at": datetime.now(timezone.utc).isoformat(),
                                 "rollback_backup_file": str(backup_path),
                                 "rollback_backup_sha256": backup_digest,
                                 "original_file_sha256": latest["file_sha256"]})
            cur.execute("UPDATE import_batches SET status='rolled_back',file_sha256=NULL,metadata_json=%s "
                        "WHERE import_batch_id=%s", (stable_json(old_metadata), batch_id))
        conn.commit()
        return {"status": "rolled_back", "import_batch_id": batch_id,
                "batch_type": latest["batch_type"], "backup": str(backup_path),
                "backup_sha256": backup_digest}
    except Exception:
        conn.rollback()
        raise
    finally:
        release_import_lock(conn)
        conn.close()


def main(argv: list[str] | None = None) -> int:
    """Keep the old script entry point while delegating CLI concerns outward."""
    if __package__:
        from .importer.cli import main as cli_main
    else:
        from importer.cli import main as cli_main
    return cli_main(argv, implementation=sys.modules[__name__])


if __name__ == "__main__":
    raise SystemExit(main())
