"""Regression checks for the conservative historical trend gate."""

import unittest

from database.importer.trends import trend_readiness_report


class _Cursor:
    def __init__(self, releases, sources):
        self.releases = releases
        self.sources = sources
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query, params=None):
        self.rows = self.releases if params is None else self.sources[params[0]]

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, releases, sources):
        self.releases = releases
        self.sources = sources

    def cursor(self):
        return _Cursor(self.releases, self.sources)


def _release(number, *, run_kind="verified_crawl", report=True):
    return {
        "release_key": f"r{number}", "snapshot_frozen_at": "2026-09-29",
        "collection_run_id": number, "run_kind": run_kind,
        "collection_status": "completed", "time_quality": "exact_utc",
        "snapshot_generated_at": f"2026-09-{number:02d} 12:00:00",
        "source_report_available": report,
        "analysis_collection_run_id": number, "analysis_status": "completed",
    }


class TrendReadinessTests(unittest.TestCase):
    def test_cumulative_exports_never_become_trend_points(self):
        releases = [_release(1, run_kind="cumulative_state_export"),
                    _release(2, run_kind="cumulative_state_export")]
        report = trend_readiness_report(_Connection(releases, {}))
        self.assertFalse(report["ready"])
        self.assertEqual(report["qualifying_release_count"], 0)

    def test_two_comparable_verified_runs_are_ready(self):
        releases = [_release(1), _release(2)]
        sources = {number: [{"source_id": "a", "status": "success", "job_count": 2}]
                   for number in (1, 2)}
        report = trend_readiness_report(_Connection(releases, sources))
        self.assertTrue(report["ready"])
        self.assertEqual(report["comparable_release_keys"], ["r1", "r2"])

    def test_failed_source_or_changed_scope_blocks_comparison(self):
        releases = [_release(1), _release(2)]
        sources = {
            1: [{"source_id": "a", "status": "success", "job_count": 2}],
            2: [{"source_id": "b", "status": "success", "job_count": 2}],
        }
        self.assertFalse(trend_readiness_report(_Connection(releases, sources))["ready"])
        sources[2] = [{"source_id": "a", "status": "failed", "job_count": 0}]
        self.assertFalse(trend_readiness_report(_Connection(releases, sources))["ready"])


if __name__ == "__main__":
    unittest.main()
