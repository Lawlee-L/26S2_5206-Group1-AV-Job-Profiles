import unittest
from contextlib import redirect_stderr
from datetime import date
from io import StringIO
from pathlib import Path

from database.importer.cli import _analysis_files_from_args, make_parser
from database.importer.errors import ImportErrorSafe
from database.importer.weekly_versions import (
    checked_week_date,
    file_week_date,
    ensure_unselected_week,
    selected_collection,
)


class CursorStub:
    def __init__(self, row):
        self.row = row
        self.query = None
        self.params = None

    def execute(self, query, params):
        self.query, self.params = query, params

    def fetchone(self):
        return self.row


class WeeklyVersionTests(unittest.TestCase):
    def test_requested_date_must_match_file(self):
        actual = date(2026, 9, 6)
        self.assertEqual(checked_week_date(actual, actual), actual)
        with self.assertRaisesRegex(ImportErrorSafe, "does not match"):
            checked_week_date(actual, date(2026, 9, 13))

    def test_week_label_is_file_date_not_last_source_collection(self):
        self.assertEqual(
            file_week_date(Path("deliverables/2026-09-06/jobs.json"),
                           date(2026, 9, 5), date(2026, 9, 6)),
            date(2026, 9, 6),
        )
        with self.assertRaisesRegex(ImportErrorSafe, "predates source content"):
            file_week_date(Path("deliverables/2026-09-06/jobs.json"),
                           date(2026, 9, 7), date(2026, 9, 6))

    def test_existing_week_cannot_be_replaced_silently(self):
        with self.assertRaisesRegex(ImportErrorSafe, "already has an official collection"):
            ensure_unselected_week(CursorStub({"collection_run_id": 1}), date(2026, 9, 6))

    def test_classification_must_target_selected_collection(self):
        week = date(2026, 9, 6)
        with self.assertRaisesRegex(ImportErrorSafe, "not the official collection"):
            selected_collection(CursorStub({"collection_run_id": 2,
                                            "selected_analysis_run_id": None}), week, 1)
        with self.assertRaisesRegex(ImportErrorSafe, "already has a selected classification"):
            selected_collection(CursorStub({"collection_run_id": 1,
                                            "selected_analysis_run_id": 10}), week, 1)
        selected_collection(CursorStub({"collection_run_id": 1,
                                        "selected_analysis_run_id": None}), week, 1)

    def test_analysis_cli_requires_explicit_week(self):
        parser = make_parser()
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args([
                "import-analysis", "--postings", "postings.json", "--metadata", "meta.json",
                "--source-input", "li.json", "--av-summary", "av.csv",
                "--other-summary", "other.csv", "--duplicates", "duplicates.csv",
                "--failures", "failures.csv", "--git-commit", "abcdef0",
            ])

    def test_plan_analysis_cli_does_not_need_week(self):
        args = make_parser().parse_args([
            "plan-analysis", "--postings", "postings.json", "--metadata", "meta.json",
            "--source-input", "li.json", "--av-summary", "av.csv",
            "--other-summary", "other.csv", "--duplicates", "duplicates.csv",
            "--failures", "failures.csv",
        ])
        self.assertEqual(args.command, "plan-analysis")
        self.assertFalse(hasattr(args, "week_date"))
        self.assertIsNone(_analysis_files_from_args(args).week_date)


if __name__ == "__main__":
    unittest.main()
