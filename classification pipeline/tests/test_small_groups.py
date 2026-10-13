"""Offline tests for small and empty relevance groups (no API calls, no model downloads).

The tuned settings in config.CLUSTER_PARAMS ask UMAP for up to 10 dimensions, which
its spectral start cannot give for a group of fewer than 12 postings. These tests run
the real UMAP and HDBSCAN on synthetic vectors, and the whole pipeline on synthetic
postings with the model and the embedder replaced by fakes.

    .venv/bin/python -m unittest tests.test_small_groups -v
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import run_pipeline_v2 as pipeline  # noqa: E402
from avjobs import cluster, embed, llm  # noqa: E402
from avjobs import config as cfg  # noqa: E402
from tests.test_store import fake_record  # noqa: E402

AV = cfg.CLUSTER_PARAMS["av_relevant"]
WORDS = ("lidar perception planning calibration safety simulation mapping localisation "
         "embedded firmware validation tooling fleet telemetry data pipeline robotics "
         "controls radar camera fusion testing release compliance recruiting finance").split()

warnings.filterwarnings("ignore")   # UMAP warns about small n and n_jobs; not under test here


def vectors(n: int, dim: int = 32, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).normal(size=(n, dim))


class FitGroupTest(unittest.TestCase):
    """cluster.fit_group with the tuned AV settings (10 UMAP dimensions)."""

    def test_empty_group(self):
        labels, used = cluster.fit_group(vectors(0), AV)
        self.assertEqual(labels.shape, (0,))
        self.assertIn("small_group", used)

    def test_singleton(self):
        labels, used = cluster.fit_group(vectors(1), AV)
        self.assertEqual(labels.tolist(), [-1])
        self.assertIn("small_group", used)

    def test_eight_rows_below_min_cluster_size_are_noise(self):
        labels, used = cluster.fit_group(vectors(8), AV)
        self.assertEqual(labels.tolist(), [-1] * 8)
        self.assertEqual(used["umap_components"], AV["umap_components"], "nothing ran, nothing shrunk")

    def test_eight_rows_with_small_min_cluster_size_shrink_umap(self):
        # This exact input raised "Cannot use scipy.linalg.eigh for sparse A with k >= N".
        labels, used = cluster.fit_group(vectors(8), AV | {"min_cluster_size": 2})
        self.assertEqual(labels.shape, (8,))
        self.assertEqual((used["umap_n_neighbors"], used["umap_components"]), (7, 6))
        self.assertIn("UMAP reduced", used["small_group"])

    def test_two_rows_cannot_be_reduced(self):
        labels, _ = cluster.fit_group(vectors(2), AV | {"min_cluster_size": 2})
        self.assertEqual(labels.tolist(), [-1, -1])

    def test_full_size_group_keeps_tuned_settings(self):
        self.assertEqual(cluster.fit_umap_settings(AV["min_cluster_size"], AV["umap_n_neighbors"],
                                                   AV["umap_components"]),
                         (AV["umap_n_neighbors"], AV["umap_components"]))

    def test_sweep_on_eight_rows(self):
        settings = cluster.fit_umap_settings(8, AV["umap_n_neighbors"], AV["umap_components"])
        table = cluster.sweep_min_cluster_size(cluster.reduce_dimensions(vectors(8), *settings))
        self.assertEqual(len(table), len(cfg.SWEEP_MIN_CLUSTER_SIZES) * len(cfg.SWEEP_MIN_SAMPLES))

    def test_summaries_of_empty_and_tiny_groups(self):
        self.assertEqual(len(cluster.summarize_clusters(pd.DataFrame(), np.array([], dtype=int))), 0)
        tiny = pd.DataFrame({"cluster_text": ["lidar perception", "radar fusion", "finance"],
                             "name": ["A", "B", "C"], "company": ["X", "X", "Y"]})
        summary = cluster.summarize_clusters(tiny, np.array([-1, -1, -1]))
        self.assertEqual(summary["size"].tolist(), [3])


class FakeModel:
    """Schema-valid records; titles starting with "Sales" are the only non-AV postings."""

    def __call__(self, df, model, use_cache=True):
        out = []
        for i, title in enumerate(df["name"]):
            rec = fake_record(title, i) | {"av_relevant": not title.startswith("Sales"),
                                           "relevance_confidence": "High"}
            out.append({"record": rec, "error": None, "raw_reply": None, "cached": False,
                        "prompt_tokens": 100, "output_tokens": 50, "reasoning_tokens": 0,
                        "cost_usd": 0.0})
        return out


def fake_embed(texts, use_cache=True) -> np.ndarray:
    """Deterministic vectors per text, so no sentence-transformer model is downloaded."""
    return np.stack([np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:8], 16))
                     .normal(size=32) for t in texts])


def posting(i: int, title: str) -> dict:
    rng = np.random.default_rng(i)
    description = f"{title}. " + " ".join(rng.choice(WORDS, size=80))
    return {
        "metadata": {"source_key": f"test|co{i % 3}|id:{i}", "source_id": f"co{i % 3}_test",
                     "source_job_id": str(i), "company": f"Company {i % 3}", "platform": "test",
                     "region": "Test", "collected_at": "2026-09-25T00:00:00Z",
                     "first_seen_date": "2026-09-01", "last_seen_date": "2026-09-25",
                     "is_active": True, "is_new_in_latest_run": False},
        "data": {"advertised_job_title": title, "job_description": description,
                 "job_url": f"https://example.test/{i}", "location": "Remote", "salary": None,
                 "date_posted": "2026-09-01"},
    }


class SmallSampleRunTest(unittest.TestCase):
    """The whole pipeline on limited samples, ending in run_metadata.json and the output files."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (cfg.CACHE_DIR, cfg.LLM_CACHE_DIR, llm.normalise_postings, embed.embed_postings)
        cfg.CACHE_DIR = self.tmp / "cache"
        cfg.LLM_CACHE_DIR = self.tmp / "cache" / "llm"
        llm.normalise_postings, embed.embed_postings = FakeModel(), fake_embed
        os.environ["OPENROUTER_API_KEY"] = ""          # any real call would fail loudly

    def tearDown(self):
        cfg.CACHE_DIR, cfg.LLM_CACHE_DIR, llm.normalise_postings, embed.embed_postings = self.saved

    def run_pipeline(self, titles: list[str], *extra) -> Path:
        source = self.tmp / "input.json"
        source.write_text(json.dumps([posting(i, t) for i, t in enumerate(titles)]), encoding="utf-8")
        out = self.tmp / "out"
        argv, sys.argv = sys.argv, ["run_pipeline_v2.py", "--input", str(source),
                                    "--output-dir", str(out), *extra]
        try:
            self.assertEqual(pipeline.main(), 0)
        finally:
            sys.argv = argv
        return out

    def test_limited_sample_with_an_empty_group(self):
        out = self.run_pipeline([f"Perception Engineer {i}" for i in range(12)], "--limit", "8")
        meta = json.loads((out / "run_metadata.json").read_text())
        self.assertEqual(meta["groups"]["av_relevant"]["n_postings"], 8)
        self.assertEqual(meta["groups"]["not_av_relevant"]["n_postings"], 0)
        self.assertIn("small_group", meta["cluster_params"]["not_av_relevant"])
        self.assertEqual(len(json.loads((out / "postings_all.json").read_text())), 8)
        self.assertEqual(len(pd.read_csv(out / "not_av_relevant" / "cluster_summary.csv")), 0)

    def test_singleton_group(self):
        out = self.run_pipeline([f"Perception Engineer {i}" for i in range(8)] + ["Sales Lead"])
        meta = json.loads((out / "run_metadata.json").read_text())
        self.assertEqual(meta["groups"]["not_av_relevant"], {"n_postings": 1, "n_clusters": 0, "n_noise": 1})

    def test_limited_sample_with_min_cluster_size_override(self):
        out = self.run_pipeline([f"Perception Engineer {i}" for i in range(8)] + ["Sales Lead"],
                                "--limit", "9", "--min-cluster-size", "2")
        used = json.loads((out / "run_metadata.json").read_text())["cluster_params"]["av_relevant"]
        self.assertEqual((used["umap_n_neighbors"], used["umap_components"]), (7, 6))

    def test_sweep_on_small_groups(self):
        out = self.run_pipeline([f"Perception Engineer {i}" for i in range(8)] + ["Sales Lead"], "--sweep")
        self.assertTrue((out / "av_relevant" / "cluster_sweep.csv").exists())
        self.assertFalse((out / "not_av_relevant" / "cluster_sweep.csv").exists(), "one posting: skipped")


if __name__ == "__main__":
    unittest.main()
