"""Offline tests for parallel model calls in llm.normalise_postings (no API calls).

normalise_one is replaced by a fake that sleeps like a real call, so the tests
check ordering, how many calls run at once, error handling and the cache.

    .venv/bin/python -m unittest tests.test_llm_parallel -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openrouter import errors  # noqa: E402

from avjobs import config as cfg, llm  # noqa: E402

CALL_SECONDS = 0.3


def postings(n: int) -> pd.DataFrame:
    return pd.DataFrame({"source_key": [f"k{i}" for i in range(n)],
                         "name": [f"title {i}" for i in range(n)],
                         "description": [f"description {i}" for i in range(n)]})


def too_many_requests() -> errors.TooManyRequestsResponseError:
    req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    data = errors.TooManyRequestsResponseErrorData.model_validate(
        {"error": {"code": 429, "message": "offline test"}})
    return errors.TooManyRequestsResponseError(data=data, raw_response=httpx.Response(429, request=req))


class FakeCall:
    """Stands in for llm.normalise_one; tracks calls and how many run at once."""

    def __init__(self, fail_titles=(), fatal_title=None):
        self.fail_titles, self.fatal_title = set(fail_titles), fatal_title
        self.lock, self.running, self.peak, self.started = threading.Lock(), 0, 0, []

    def __call__(self, client, model, title, description):
        with self.lock:
            self.started.append(title)
            self.running += 1
            self.peak = max(self.peak, self.running)
        try:
            time.sleep(CALL_SECONDS)
            if title == self.fatal_title:
                raise too_many_requests()
            if title in self.fail_titles:
                raise RuntimeError("one posting's problem")
            return {"record": {"title": title}, "error": None, "raw_reply": None,
                    "prompt_tokens": 10, "output_tokens": 5, "reasoning_tokens": 0, "cost_usd": 0.001}
        finally:
            with self.lock:
                self.running -= 1


class ParallelTest(unittest.TestCase):
    def setUp(self):
        cfg.LLM_CACHE_DIR = Path(tempfile.mkdtemp())   # keep the real cache untouched
        os.environ["OPENROUTER_API_KEY"] = "fake-offline-test"
        self.real = llm.normalise_one

    def tearDown(self):
        llm.normalise_one = self.real

    def run_with(self, fake, df):
        llm.normalise_one = fake
        return llm.normalise_postings(df, "fake/model")

    def test_results_in_order_and_10_at_a_time(self):
        fake, df = FakeCall(), postings(30)
        t0 = time.time()
        results = self.run_with(fake, df)
        elapsed = time.time() - t0
        self.assertEqual([r["record"]["title"] for r in results], list(df["name"]))
        self.assertEqual(fake.peak, cfg.LLM_WORKERS)
        self.assertLess(elapsed, 30 * CALL_SECONDS / 3, "should be far faster than one at a time")

    def test_one_failure_does_not_stop_the_run(self):
        fake, df = FakeCall(fail_titles={"title 4"}), postings(12)
        results = self.run_with(fake, df)
        self.assertIsNone(results[4]["record"])
        self.assertIn("one posting's problem", results[4]["error"])
        self.assertEqual(sum(r["record"] is not None for r in results), 11)
        self.assertEqual(len(list(cfg.LLM_CACHE_DIR.glob("*.json"))), 11, "failures are not cached")

    def test_fatal_error_stops_and_cancels_the_queue(self):
        fake, df = FakeCall(fatal_title="title 0"), postings(60)
        with self.assertRaises(errors.TooManyRequestsResponseError):
            self.run_with(fake, df)
        time.sleep(3 * CALL_SECONDS)   # let the calls already running finish
        self.assertLess(len(fake.started), 60, "queued postings must not be sent")
        cached = len(list(cfg.LLM_CACHE_DIR.glob("*.json")))
        self.assertEqual(cached, len(fake.started) - 1, "calls already running finish and are cached")

    def test_rerun_uses_the_cache(self):
        df = postings(15)
        self.run_with(FakeCall(), df)
        fake = FakeCall()
        results = self.run_with(fake, df)
        self.assertEqual(fake.started, [])
        self.assertTrue(all(r["cached"] for r in results))


if __name__ == "__main__":
    unittest.main()
