"""Reuse records already in the team's MySQL database instead of paying for them again.

The importer (../database/weekly_import.py) is the only writer: it loads each
pipeline run into job_analyses, keeping the full record (raw_response_json), the
model and prompt version (analysis_runs), and the hash of the posting text it
was made from (input_content_hash, the same hash as clean._content_hash). Here
the pipeline only reads: a posting whose text, model and exact prompt all match
an earlier successful analysis gets that record back, from any machine,
whether or not the local answer cache exists.

Connection settings are the importer's AVDB_* variables. A read-only account
with SELECT on jobs, job_analyses and analysis_runs is enough.
"""

from __future__ import annotations

import json
import os

import jsonschema
import pandas as pd

from .llm import PROMPT_ID, SCHEMA

KEY_BATCH = 500   # source_keys per query


def connect():
    """Open a MySQL connection from AVDB_HOST/PORT/USER/PASSWORD/NAME."""
    import pymysql

    missing = [name for name in ("AVDB_USER", "AVDB_PASSWORD") if os.environ.get(name) is None]
    if missing:
        raise SystemExit("--db needs MySQL credentials: set " + ", ".join(missing)
                         + " (and AVDB_HOST/AVDB_PORT/AVDB_NAME if not the defaults) in .env")
    try:
        return pymysql.connect(
            host=os.environ.get("AVDB_HOST", "127.0.0.1"),
            port=int(os.environ.get("AVDB_PORT", "3306")),
            user=os.environ["AVDB_USER"], password=os.environ["AVDB_PASSWORD"],
            database=os.environ.get("AVDB_NAME", "av_job_profiles"),
            charset="utf8mb4", connect_timeout=8, autocommit=True)
    except pymysql.MySQLError as exc:
        # Stop rather than fall back: carrying on would pay for answers the database holds.
        raise SystemExit(f"--db could not connect to MySQL: {exc}") from exc


def reusable_records(conn, df: pd.DataFrame, model: str) -> dict[str, dict]:
    """Records already stored for these postings, keyed by source_key, in normalise_postings' shape.

    Only a successful model answer qualifies (manual corrections are not model output), from
    the same model and exact prompt (PROMPT_ID), on text that still hashes the same, so a
    posting whose text has changed is analysed again. The latest matching analysis wins.
    """
    wanted = dict(zip(df["source_key"], df["content_hash"]))
    keys = list(wanted)
    latest = {}
    with conn.cursor() as cur:
        for start in range(0, len(keys), KEY_BATCH):
            batch = keys[start:start + KEY_BATCH]
            cur.execute(f"""
                SELECT j.source_key, a.input_content_hash, a.raw_response_json
                FROM job_analyses a
                JOIN jobs j ON j.job_id = a.job_id
                JOIN analysis_runs r ON r.analysis_run_id = a.analysis_run_id
                WHERE r.model_name = %s AND r.prompt_version = %s
                  AND a.analysis_status = 'success' AND a.result_origin <> 'manual'
                  AND j.source_key IN ({", ".join(["%s"] * len(batch))})
                ORDER BY a.job_analysis_id""", (model, PROMPT_ID, *batch))
            for key, text_hash, record in cur.fetchall():
                if text_hash == wanted[key]:
                    latest[key] = record
    reused = {}
    for key, record in latest.items():
        record = json.loads(record) if isinstance(record, (str, bytes)) else record
        try:
            jsonschema.validate(record, SCHEMA)
        except jsonschema.ValidationError:
            continue   # not a complete model record: analyse the posting again
        reused[key] = {"record": record, "error": None, "raw_reply": None, "cached": True,
                       "prompt_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0,
                       "cost_usd": 0.0}
    return reused
