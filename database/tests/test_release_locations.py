import json
import unittest

from database.importer.release_locations import release_location_report


class ReleaseLocationReportTests(unittest.TestCase):
    def report(self, rows, *, frozen):
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, sql, params):
                self.sql = sql
                assert params == (1,)
            def fetchall(self): return rows

        class Connection:
            def cursor(self): return Cursor()

        return release_location_report(Connection(), {
            "dashboard_release_id": 1, "snapshot_frozen_at": "2026-09-25" if frozen else None,
        })

    def test_draft_preview_derives_fields_and_separates_active_population(self):
        rows = [{"source_key": "a", "location_raw": "Berlin, Germany (Hybrid)", "is_active": 1},
                {"source_key": "b", "location_raw": "Remote - US", "is_active": 0}]
        report = self.report(rows, frozen=False)
        self.assertEqual(report["all_av_jobs"]["counts"]["rows"], 2)
        self.assertEqual(report["active_av_jobs"]["country_counts"], {"DE": 1})
        self.assertEqual(report["active_av_jobs"]["work_mode_counts"], {"hybrid": 1})
        self.assertNotIn("country_code", rows[0])

    def test_old_frozen_release_is_not_reparsed_using_new_rules(self):
        payload = {"source_key": "a", "location_raw": "Berlin, Germany (Hybrid)",
                   "is_active": 1, "country_code": None, "remote_type": None}
        report = self.report([{"payload_json": json.dumps(payload)}], frozen=True)
        self.assertEqual(report["representation"], "frozen snapshot")
        self.assertEqual(report["parser_versions"], {"legacy/unrecorded": 1})
        self.assertIsNone(report["all_av_jobs"]["parser_version"])
        self.assertEqual(report["all_av_jobs"]["country_counts"], {"unknown": 1})
        self.assertEqual(report["all_av_jobs"]["work_mode_counts"], {"unknown": 1})

    def test_frozen_report_reads_recorded_version_and_fields(self):
        payload = {"source_key": "a", "location_raw": "Remote - US", "is_active": 1,
                   "country_code": "US", "remote_type": "remote", "location_parser_version": "saved-rules"}
        report = self.report([{"payload_json": payload}], frozen=True)
        self.assertEqual(report["parser_versions"], {"saved-rules": 1})
        self.assertEqual(report["all_av_jobs"]["parser_version"], "saved-rules")
        self.assertEqual(report["active_av_jobs"]["country_counts"], {"US": 1})
