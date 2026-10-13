"""Offline tests for reusing answers from MySQL (no database server, no API calls).

A fake connection stands in for MySQL: it returns the rows the reuse query would
select, so these tests cover the matching rules and the --db path through the
pipeline. Checking the SQL against a real database is a separate, manual step.

    .venv/bin/python -m unittest tests.test_store -v
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import jsonschema
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from avjobs import llm, store  # noqa: E402


def fake_record(title: str, i: int) -> dict:
    """A schema-valid record whose values vary with i."""
    rec = {
        "role_summary": f"Works on {title}.", "responsibilities": ["Build things"],
        "requirements": ["Experience"],
        "skills": {
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


class FakeConnection:
    """Returns stored (source_key, input_content_hash, raw_response_json) rows in id order.

    Like the real query, only rows whose source_key is in the requested batch come back;
    the model / prompt / status filters are the SQL's job and are checked via the params.
    """

    def __init__(self, rows):
        self.rows, self.queries = rows, []

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.queries.append(params)
        model, prompt, *keys = params
        self.result = [row for row in self.rows if row[0] in keys]

    def fetchall(self):
        return self.result

    def close(self):
        pass


def postings(keys_and_hashes) -> pd.DataFrame:
    return pd.DataFrame(keys_and_hashes, columns=["source_key", "content_hash"])


class ReusableRecordsTest(unittest.TestCase):
    def test_matching_text_is_reused_at_no_cost(self):
        conn = FakeConnection([("k1", "h1", json.dumps(fake_record("A", 1)))])
        reused = store.reusable_records(conn, postings([("k1", "h1")]), "some/model")
        self.assertEqual(reused["k1"]["record"], fake_record("A", 1))
        self.assertTrue(reused["k1"]["cached"])
        self.assertEqual(reused["k1"]["cost_usd"], 0.0)
        self.assertEqual(conn.queries[0][:2], ("some/model", llm.PROMPT_ID), "same model and prompt only")

    def test_changed_text_is_analysed_again(self):
        conn = FakeConnection([("k1", "old-hash", json.dumps(fake_record("A", 1)))])
        self.assertEqual(store.reusable_records(conn, postings([("k1", "new-hash")]), "m"), {})

    def test_latest_matching_analysis_wins(self):
        conn = FakeConnection([("k1", "h1", json.dumps(fake_record("Old", 1))),
                               ("k1", "h1", json.dumps(fake_record("New", 1)))])
        reused = store.reusable_records(conn, postings([("k1", "h1")]), "m")
        self.assertEqual(reused["k1"]["record"]["role_summary"], "Works on New.")

    def test_incomplete_record_is_not_reused(self):
        conn = FakeConnection([("k1", "h1", json.dumps({"role_summary": "partial"}))])
        self.assertEqual(store.reusable_records(conn, postings([("k1", "h1")]), "m"), {})

    def test_keys_are_queried_in_batches(self):
        keys = [(f"k{i}", f"h{i}") for i in range(store.KEY_BATCH + 1)]
        conn = FakeConnection([("k0", "h0", json.dumps(fake_record("A", 0)))])
        self.assertEqual(list(store.reusable_records(conn, postings(keys), "m")), ["k0"])
        self.assertEqual(len(conn.queries), 2)

    def test_missing_credentials_stop_the_run(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit):
            store.connect()


class PipelineReuseTest(unittest.TestCase):
    """--db through the whole pipeline: reused postings are never sent to the model."""

    def test_db_reuses_and_only_calls_the_model_for_the_rest(self):
        from avjobs import clean
        from tests.test_small_groups import SmallSampleRunTest, posting

        titles = [f"Perception Engineer {i}" for i in range(10)]
        stored = [posting(i, t) for i, t in enumerate(titles[:6])]
        rows = [(p["metadata"]["source_key"],
                 clean._content_hash(clean.normalize_text(p["data"]["job_description"])),
                 json.dumps(fake_record(p["data"]["advertised_job_title"], 0)))
                for p in stored]
        harness = SmallSampleRunTest("test_singleton_group")
        harness.setUp()
        sent = []
        model = llm.normalise_postings
        llm.normalise_postings = lambda df, *a, **k: (sent.extend(df["source_key"]), model(df, *a, **k))[1]
        try:
            with mock.patch.object(store, "connect", return_value=FakeConnection(rows)):
                out = harness.run_pipeline(titles, "--db")
        finally:
            harness.tearDown()
        meta = json.loads((out / "run_metadata.json").read_text())
        self.assertEqual(meta["n_reused_from_db"], 6)
        self.assertEqual(len(sent), 4, "only the postings not in MySQL are sent to the model")
        self.assertEqual(meta["n_records"], 10)


if __name__ == "__main__":
    unittest.main()
