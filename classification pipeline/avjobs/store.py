"""Write a pipeline run to SQLite, in the tables and columns of ../schema.mysql.sql.

A stand-in for MySQL while the team checks that every value lands in the right
column: schema.sql copies the MySQL tables the pipeline fills, with the same
names. Jobs come from the input file via load_jobs(), a temporary step until
the team's own job import exists. Everything joins on jobs.source_key.

The database is also where finished records are reused from: reusable_records()
finds a posting's earlier record from the same model and exact prompt on the
same text, so the pipeline stores a 'reused' copy instead of calling the model.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import clean
from .llm import PROMPT_ID, SKILL_CATEGORIES

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SKILL_TYPES = {"tools": "tool", "domain": "domain", "qualifications": "qualification"}


def connect(path) -> sqlite3.Connection:
    """Open (or create) the database file and make sure the tables exist."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _utc(value) -> str | None:
    """A date in any of the scrapers' formats as ISO 8601 UTC, or None."""
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    return None if pd.isna(ts) else ts.isoformat()


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _plain(value):
    """numpy scalars and pandas NA -> plain Python values sqlite3 can bind."""
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    return value.item() if hasattr(value, "item") else value


def _split(text, sep: str) -> list[str]:
    return [p for p in str(text or "").split(sep) if p]


# --------------------------------------------------------------------------
# Jobs (temporary loader)
# --------------------------------------------------------------------------
def load_jobs(conn: sqlite3.Connection, input_path) -> None:
    """TEMPORARY: companies, job_sources and jobs straight from the input file.

    Upserts by source_key, so re-running updates rows instead of duplicating
    them. The team's own job import will replace this.
    """
    records = json.loads(Path(input_path).read_text(encoding="utf-8"))
    with conn:
        for rec in records:
            meta, data = rec["metadata"], rec["data"]
            slug = re.sub(r"[^a-z0-9]+", "-", meta["company"].lower()).strip("-")
            conn.execute("INSERT OR IGNORE INTO companies (company_name, company_slug) VALUES (?, ?)",
                         (meta["company"], slug))
            conn.execute("""
                INSERT OR IGNORE INTO job_sources (source_id, company_id, platform, region)
                SELECT ?, company_id, ?, ? FROM companies WHERE company_name = ?""",
                         (meta["source_id"], meta["platform"], meta["region"], meta["company"]))
            description = data.get("job_description") or ""
            salary = data.get("salary")
            conn.execute("""
                INSERT INTO jobs (source_key, source_id, source_job_id, advertised_job_title,
                    job_description, job_url, location_raw, salary_raw, date_posted,
                    first_seen_date, last_seen_date, latest_collected_at, is_active,
                    is_new_in_latest_run, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (source_key) DO UPDATE SET
                    advertised_job_title = excluded.advertised_job_title,
                    job_description = excluded.job_description, job_url = excluded.job_url,
                    location_raw = excluded.location_raw, salary_raw = excluded.salary_raw,
                    date_posted = excluded.date_posted, last_seen_date = excluded.last_seen_date,
                    latest_collected_at = excluded.latest_collected_at,
                    is_active = excluded.is_active,
                    is_new_in_latest_run = excluded.is_new_in_latest_run,
                    content_hash = excluded.content_hash, updated_at = CURRENT_TIMESTAMP""",
                (meta["source_key"], meta["source_id"], str(meta["source_job_id"]),
                 data.get("advertised_job_title"), description, data.get("job_url"),
                 data.get("location"),
                 salary if salary is None or isinstance(salary, str) else _json(salary),
                 _utc(data.get("date_posted")), meta["first_seen_date"], meta["last_seen_date"],
                 _utc(meta["collected_at"]), meta["is_active"], meta["is_new_in_latest_run"],
                 clean._content_hash(clean.normalize_text(description))))


# --------------------------------------------------------------------------
# One pipeline run
# --------------------------------------------------------------------------
def _skill_id(conn: sqlite3.Connection, name: str, skill_type: str) -> int:
    """One skills row per (name ignoring case and spacing, type); the first spelling is kept."""
    normalized = " ".join(name.lower().split())
    conn.execute("INSERT OR IGNORE INTO skills (canonical_name, normalized_name, skill_type) "
                 "VALUES (?, ?, ?)", (name, normalized, skill_type))
    return conn.execute("SELECT skill_id FROM skills WHERE normalized_name = ? AND skill_type = ?",
                        (normalized, skill_type)).fetchone()[0]


def reusable_records(conn: sqlite3.Connection, df: pd.DataFrame, model: str) -> dict[str, dict]:
    """Records already stored for these postings, keyed by source_key, in normalise_postings' shape.

    Only an original ('generated') record qualifies, from the same model and exact prompt
    (PROMPT_ID), on text that still hashes the same, so a posting whose text has changed
    is analysed again and a reused row always points at its source.
    """
    rows = conn.execute("""
        SELECT j.source_key, a.job_analysis_id, a.input_content_hash, a.raw_response_json
        FROM job_analyses a
        JOIN jobs j USING (job_id)
        JOIN analysis_runs r USING (analysis_run_id)
        WHERE r.model_name = ? AND r.prompt_version = ?
          AND a.analysis_status = 'success' AND a.result_origin = 'generated'
        ORDER BY a.job_analysis_id""", (model, PROMPT_ID))
    latest = {key: (analysis_id, text_hash, record) for key, analysis_id, text_hash, record in rows}
    wanted = dict(zip(df["source_key"], df["content_hash"]))
    return {key: {"record": json.loads(record), "error": None, "raw_reply": None, "cached": True,
                  "reused_from": analysis_id, "prompt_tokens": 0, "output_tokens": 0,
                  "reasoning_tokens": 0, "cost_usd": 0.0}
            for key, (analysis_id, text_hash, record) in latest.items()
            if key in wanted and wanted[key] == text_hash}


def save_run(conn: sqlite3.Connection, df: pd.DataFrame, failed: pd.DataFrame,
             dropped: pd.DataFrame, summaries: dict[str, pd.DataFrame], meta: dict) -> str:
    """Store one run: its analyses, skills, dedupe links and clusters. Returns the run key.

    `df` holds the postings with a record (as written to postings_all.json), `failed`
    the LLM failures, `dropped` the duplicates, `summaries` each group's cluster summary.
    All or nothing: any error rolls the whole run back.
    """
    job_id = dict(conn.execute("SELECT source_key, job_id FROM jobs"))
    needed = set(df["source_key"]) | set(failed["source_key"]) | set(dropped["source_key"])
    missing = sorted(needed - set(job_id))
    if missing:
        raise SystemExit(f"{len(missing)} source_keys are not in jobs (e.g. {missing[0]}); "
                         "load the jobs first")

    now = _now()
    # Microseconds keep keys unique even for two runs within the same second.
    run_key = f"v2-{meta['model']}-{meta['prompt_version']}-" \
              f"{datetime.now(timezone.utc).isoformat(timespec='microseconds')}"
    cluster_params = {k: meta[k] for k in ("embedding_model", "min_cluster_size", "min_samples")}
    with conn:
        run_id = conn.execute("""
            INSERT INTO analysis_runs (run_key, method, provider, model_name, prompt_version,
                source_dataset_version, parameters_json, prompt_tokens, output_tokens, cost_usd,
                status, started_at, completed_at)
            VALUES (?, 'llm', 'openrouter', ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)""",
            (run_key, meta["model"], meta["prompt_version"], Path(meta["input"]).name,
             _json({k: meta[k] for k in ("limit", "temperature", "n_records", "n_llm_failures")}
                   | cluster_params),
             meta["prompt_tokens"], meta["output_tokens"], meta["cost_usd"],
             meta["started_at"], now)).lastrowid

        conn.executemany("""
            UPDATE jobs SET duplicate_of_job_id = ?, duplicate_type = ?, duplicate_similarity = ?
            WHERE job_id = ?""",
            [(job_id[d["duplicate_of_source_key"]], d["duplicate_type"], float(d["similarity"]),
              job_id[d["source_key"]]) for d in dropped.to_dict("records")])

        analysis_id = {}
        for row in df.to_dict("records"):
            rec = row["record"]
            reused_from = _plain(row.get("reused_from"))
            analysis_id[row["source_key"]] = conn.execute("""
                INSERT INTO job_analyses (job_id, analysis_run_id, source_row_index, result_origin,
                    reused_from_job_analysis_id, av_relevant,
                    relevance_confidence_label, relevance_reason, role_summary,
                    responsibilities_json, requirements_json, language_of_posting, seniority_code,
                    seniority_source, experience_min_years, experience_max_years,
                    raw_response_json, input_content_hash, prompt_tokens, output_tokens, cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'model', ?, ?, ?, ?, ?, ?, ?)""",
                # av_relevant is the final group (after the Low -> AV rule); the model's
                # own verdict stays inside raw_response_json.
                (job_id[row["source_key"]], run_id, _plain(row["row_index"]),
                 "reused" if reused_from else "generated", reused_from,
                 bool(row["av_relevant"]), rec["relevance_confidence"], rec["relevance_reason"],
                 rec["role_summary"], _json(rec["responsibilities"]),
                 _json(rec["requirements"]), rec["language_of_posting"], rec["seniority"],
                 rec["experience_min"], rec["experience_max"], _json(rec), row["content_hash"],
                 _plain(row["prompt_tokens"]), _plain(row["output_tokens"]),
                 _plain(row["cost_usd"]))).lastrowid
            for cat in SKILL_CATEGORIES:
                for rank, skill in enumerate(rec["skills"][cat], 1):
                    # OR IGNORE: a name repeated within one posting is stored once.
                    conn.execute("""
                        INSERT OR IGNORE INTO job_skills
                            (job_analysis_id, skill_id, raw_skill_text, evidence, skill_rank)
                        VALUES (?, ?, ?, ?, ?)""",
                        (analysis_id[row["source_key"]],
                         _skill_id(conn, skill["name"], SKILL_TYPES[cat]),
                         skill["name"], skill["evidence"], rank))

        conn.executemany("""
            INSERT INTO job_analyses (job_id, analysis_run_id, source_row_index,
                analysis_status, raw_response_json)
            VALUES (?, ?, ?, 'failed', ?)""",
            [(job_id[f["source_key"]], run_id, _plain(f["row_index"]), _json({"error": f["error"]}))
             for f in failed.to_dict("records")])

        for population, summary in summaries.items():
            cluster_run_id = conn.execute("""
                INSERT INTO cluster_runs (run_key, analysis_run_id, population, algorithm,
                    produced_cluster_count, includes_noise, parameters_json, status,
                    started_at, completed_at)
                VALUES (?, ?, ?, 'umap+hdbscan', ?, ?, ?, 'completed', ?, ?)""",
                (f"{run_key}-{population}", run_id, population,
                 int((~summary["is_noise"]).sum()), bool(summary["is_noise"].any()),
                 _json(cluster_params), meta["started_at"], now)).lastrowid
            cluster_pk = {}
            for c in summary.to_dict("records"):
                # Names, job families and specialisations are left for a human to fill.
                cluster_pk[int(c["cluster_id"])] = conn.execute("""
                    INSERT INTO clusters (cluster_run_id, cluster_number, lean, is_noise,
                        size_cached, technical_score, top_terms_json, example_titles_json,
                        top_companies_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (cluster_run_id, int(c["cluster_id"]),
                     "noise" if c["is_noise"] else c["lean"], bool(c["is_noise"]),
                     int(c["size"]), _plain(c["technical_score"]),
                     _json(_split(c["top_terms"], ", ")),
                     _json(_split(c["example_titles"], " | ")),
                     _json(_split(c["top_companies"], "; ")))).lastrowid
            part = df[df["av_relevant"] == (population == "av_relevant")]
            conn.executemany("""
                INSERT INTO job_cluster_assignments
                    (job_analysis_id, analysis_run_id, cluster_run_id, cluster_pk)
                VALUES (?, ?, ?, ?)""",
                [(analysis_id[k], run_id, cluster_run_id, cluster_pk[int(cid)])
                 for k, cid in zip(part["source_key"], part["cluster_id"])])
    return run_key


def row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [t for (t,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid")]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
