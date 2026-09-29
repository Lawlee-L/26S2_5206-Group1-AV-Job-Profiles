"""Offline tests for the SQLite store and database reuse (no API calls).

The model is replaced by a fake that builds schema-valid records and counts
calls; everything else (dedupe, embeddings, clustering, store) runs for real on
40 of Li's postings plus two planted exact duplicates, in a temporary folder.

    .venv/bin/python -m unittest tests.test_store -v
"""

from __future__ import annotations

import copy
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import run_pipeline_v2 as pipeline  # noqa: E402
from avjobs import clean, llm, store  # noqa: E402
from avjobs import config as cfg  # noqa: E402

FAIL_TITLE_INDEX = 3   # this posting's fake call always fails


def fake_record(title: str, i: int) -> dict:
    """A schema-valid record whose values vary with i, including skills that test merging."""
    rec = {
        "role_summary": f"Works on {title}.", "responsibilities": ["Build things"],
        "requirements": ["Experience"],
        "skills": {
            # "Python" / "python" -> one skill; the repeat within a posting -> one job_skills row.
            "tools": [{"name": "Python" if i % 2 else "python", "evidence": "Python"},
                      {"name": "C++", "evidence": "C++"}, {"name": "C++", "evidence": "C++ again"}],
            "domain": [{"name": f"Domain {i % 5}", "evidence": "domain"}],
            "qualifications": [{"name": "Bachelor's degree", "evidence": "degree"}],
        },
        "seniority": "Senior", "experience_min": 3, "experience_max": None,
        "language_of_posting": "English", "relevance_reason": "Because.",
        "av_relevant": i % 3 == 0, "relevance_confidence": "Low" if i % 3 == 1 else "High",
    }
    jsonschema.validate(rec, llm.SCHEMA)
    return rec


class FakeModel:
    """Stands in for llm.normalise_postings and records which postings it was asked for."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, df, model, use_cache=True):
        self.calls.append(list(df["source_key"]))
        out = []
        for key, title in zip(df["source_key"], df["name"]):
            i = int(key.rsplit("#", 1)[1])
            ok = i != FAIL_TITLE_INDEX
            out.append({"record": fake_record(title, i) if ok else None,
                        "error": None if ok else "fake failure", "raw_reply": None,
                        "cached": False, "prompt_tokens": 100, "output_tokens": 50,
                        "reasoning_tokens": 0, "cost_usd": 0.0001 if ok else 0.0})
        return out


class StoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "jobs_history_translated.json").exists():
            raise unittest.SkipTest("needs jobs_history_translated.json (the dataset is not in the repo)")
        cls.tmp = Path(tempfile.mkdtemp())
        cfg.CACHE_DIR = cls.tmp / "cache"            # keep the real caches untouched
        cfg.LLM_CACHE_DIR = cls.tmp / "cache" / "llm"
        os.environ["OPENROUTER_API_KEY"] = ""          # any real call would fail loudly

        source = json.loads((ROOT / "jobs_history_translated.json").read_text(encoding="utf-8"))
        seen, picked = set(), []
        for rec in source:                              # 40 postings with distinct text
            h = clean._content_hash(clean.normalize_text(rec["data"]["job_description"] or ""))
            if h not in seen and len(rec["data"]["job_description"] or "") > 500:
                seen.add(h)
                picked.append(copy.deepcopy(rec))
            if len(picked) == 40:
                break
        # Unique, readable keys ending in "#<n>" so the fake model can vary its answer.
        for n, rec in enumerate(picked):
            rec["metadata"]["source_key"] += f"#{n}"
            rec["metadata"]["source_job_id"] = f"{rec['metadata']['source_job_id']}#{n}"
        for n in (0, 1):                                # two planted exact duplicates
            dup = copy.deepcopy(picked[n])
            dup["metadata"]["source_key"] += "-dup#99"
            dup["metadata"]["source_job_id"] += "-dup"
            picked.append(dup)
        cls.records = picked
        cls.input = cls.tmp / "input.json"
        cls.input.write_text(json.dumps(picked), encoding="utf-8")
        cls.out = cls.tmp / "out"

    # -- helpers --------------------------------------------------------------
    def run_pipeline(self, *extra) -> FakeModel:
        fake = FakeModel()
        real, llm.normalise_postings = llm.normalise_postings, fake
        argv, sys.argv = sys.argv, ["run_pipeline_v2.py", "--input", str(self.input),
                                    "--output-dir", str(self.out), "--db", *extra]
        try:
            self.assertEqual(pipeline.main(), 0)
        finally:
            llm.normalise_postings, sys.argv = real, argv
        return fake

    def db(self) -> sqlite3.Connection:
        return sqlite3.connect(self.out / "av_job_profiles.sqlite")

    def one(self, sql, *args):
        return self.db().execute(sql, args).fetchone()[0]

    # -- tests (run in name order) --------------------------------------------
    def test_1_first_run_generates_everything(self):
        fake = self.run_pipeline()
        called = fake.calls[0]
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn(self.records[-1]["metadata"]["source_key"], called, "duplicates are not sent")

        self.assertEqual(self.one("SELECT COUNT(*) FROM jobs"), 42)
        self.assertEqual(self.one("SELECT COUNT(*) FROM jobs WHERE duplicate_type = 'exact'"), 2)
        n_sent = len(called)
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_analyses"), n_sent)
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_analyses WHERE analysis_status = 'failed'"), 1)
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_analyses WHERE result_origin = 'generated'"), n_sent)
        # Low confidence moves a posting into the AV group; the model's verdict stays in the record.
        self.assertEqual(self.one("""SELECT COUNT(*) FROM job_analyses WHERE relevance_confidence_label = 'Low'
                                     AND av_relevant = 0"""), 0)
        # Skills: case variants merge, a repeat within one posting is stored once.
        self.assertEqual(self.one("SELECT COUNT(*) FROM skills WHERE normalized_name = 'python'"), 1)
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_skills"), 4 * (n_sent - 1))
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_skills WHERE evidence IS NULL"), 0)
        # Every analysed posting sits in exactly one cluster of its own group.
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_cluster_assignments"), n_sent - 1)
        self.assertEqual(self.one("""SELECT COUNT(*) FROM job_cluster_assignments x
            JOIN job_analyses a USING (job_analysis_id) JOIN cluster_runs r USING (cluster_run_id)
            WHERE r.population <> CASE a.av_relevant WHEN 1 THEN 'av_relevant' ELSE 'not_av_relevant' END"""), 0)
        self.assertEqual(self.one("SELECT COUNT(*) FROM job_analyses WHERE input_content_hash IS NULL "
                                  "AND analysis_status = 'success'"), 0)

    def test_2_second_run_reuses_all_but_the_failure(self):
        fake = self.run_pipeline()
        failed_key = self.records[FAIL_TITLE_INDEX]["metadata"]["source_key"]
        self.assertEqual(fake.calls, [[failed_key]], "only the earlier failure is sent again")
        run2 = self.one("SELECT MAX(analysis_run_id) FROM analysis_runs")
        reused = self.one("SELECT COUNT(*) FROM job_analyses WHERE analysis_run_id = ? "
                          "AND result_origin = 'reused'", run2)
        self.assertEqual(reused, self.one("SELECT COUNT(*) FROM job_analyses WHERE analysis_run_id = 1 "
                                          "AND analysis_status = 'success'"))
        # Each reused row points at the same job's original, with the identical record and no cost.
        self.assertEqual(self.one("""SELECT COUNT(*) FROM job_analyses r JOIN job_analyses g
            ON g.job_analysis_id = r.reused_from_job_analysis_id
            WHERE r.analysis_run_id = ? AND (g.job_id <> r.job_id OR g.result_origin <> 'generated'
                  OR g.raw_response_json <> r.raw_response_json OR r.cost_usd <> 0)""", run2), 0)
        self.assertEqual(self.one("SELECT COUNT(*) FROM jobs"), 42, "jobs are updated, not duplicated")

    def test_3_edited_posting_is_analysed_again(self):
        edited = json.loads(self.input.read_text(encoding="utf-8"))
        edited[5]["data"]["job_description"] += "\n\nNew requirement: ten years of Rust."
        self.input.write_text(json.dumps(edited), encoding="utf-8")
        try:
            fake = self.run_pipeline()
        finally:
            self.input.write_text(json.dumps(self.records), encoding="utf-8")
        failed_key = self.records[FAIL_TITLE_INDEX]["metadata"]["source_key"]
        self.assertEqual(sorted(fake.calls[0]),
                         sorted([failed_key, self.records[5]["metadata"]["source_key"]]))

    def test_4_no_cache_sends_everything(self):
        fake = self.run_pipeline("--no-cache")
        self.assertEqual(len(fake.calls[0]), self.one("SELECT COUNT(*) FROM job_analyses WHERE analysis_run_id = 1"))

    def test_5_reuse_needs_same_model_and_prompt(self):
        df = clean.load_postings(self.input)
        df, _ = clean.dedupe(df)
        conn = self.db()
        self.assertGreater(len(store.reusable_records(conn, df, cfg.LLM_MODEL)), 0)
        self.assertEqual(store.reusable_records(conn, df, "openai/gpt-4o-mini"), {})
        real, store.PROMPT_ID = store.PROMPT_ID, "p999-00000000"
        try:
            self.assertEqual(store.reusable_records(conn, df, cfg.LLM_MODEL), {})
        finally:
            store.PROMPT_ID = real

    def test_6_missing_job_is_refused_and_nothing_written(self):
        conn = self.db()
        before = conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]
        df = pd.DataFrame({"source_key": ["not-a-real-key"]})
        empty = pd.DataFrame({"source_key": []})
        with self.assertRaises(SystemExit):
            store.save_run(conn, df, empty, empty, {}, {})
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0], before)

    def test_7_bad_value_rolls_back_the_whole_run(self):
        conn = self.db()
        conn.execute("PRAGMA foreign_keys = ON")
        before = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("analysis_runs", "job_analyses", "job_skills")]
        key = self.records[0]["metadata"]["source_key"]
        text_hash = conn.execute("SELECT content_hash FROM jobs WHERE source_key = ?", (key,)).fetchone()[0]
        df = pd.DataFrame([{"source_key": key, "row_index": 0, "record": fake_record("x", 0),
                            "av_relevant": True, "content_hash": text_hash, "cluster_id": 0,
                            "prompt_tokens": 1, "output_tokens": 1, "cost_usd": 0.0}])
        empty = pd.DataFrame({"source_key": []})
        bad = pd.DataFrame([{"cluster_id": 0, "size": 1, "is_noise": False, "technical_score": 0.5,
                             "lean": "not-a-lean", "top_terms": "", "example_titles": "", "top_companies": ""}])
        meta = {"model": "m", "prompt_version": "p", "input": "x", "limit": None, "temperature": 0,
                "n_records": 1, "n_llm_failures": 0, "embedding_model": "e", "min_cluster_size": 8,
                "min_samples": 2, "prompt_tokens": 1, "output_tokens": 1, "cost_usd": 0.0,
                "started_at": "2026-01-01T00:00:00+00:00"}
        with self.assertRaises(sqlite3.IntegrityError):
            store.save_run(conn, df, empty, empty, {"av_relevant": bad}, meta)
        after = [conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in ("analysis_runs", "job_analyses", "job_skills")]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
