import unittest
from unittest.mock import MagicMock, patch

from database import bootstrap_website as bootstrap


class BootstrapWebsiteTests(unittest.TestCase):
    def invoke(self, values, args=None, failure=None):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = values
        with patch.object(bootstrap.engine, "db_connect", return_value=conn), \
             patch.object(bootstrap, "run", side_effect=failure) as run, \
             patch("sys.argv", ["bootstrap", *(args or ["--git-commit", "780b2c3"])]):
            try:
                result = bootstrap.main()
            finally:
                conn.close.assert_called_once()
        return result, run

    def test_published_database_is_not_modified(self):
        result, run = self.invoke([{"acquired": 1}, {"n": 1}])
        self.assertEqual(result, 0)
        run.assert_not_called()

    def test_empty_database_check_does_not_import(self):
        result, run = self.invoke([{"acquired": 1}] + [{"n": 0}] * 5, ["--check-only"])
        self.assertEqual(result, 0)
        run.assert_not_called()

    def test_incomplete_database_stops(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete imports"):
            self.invoke([{"acquired": 1}, {"n": 0}, {"n": 1}])

    def test_concurrent_initialisation_stops(self):
        with self.assertRaisesRegex(RuntimeError, "Another website"):
            self.invoke([{"acquired": 0}])

    def test_validates_both_pairs_before_import_and_publishes(self):
        _, run = self.invoke([{"acquired": 1}] + [{"n": 0}] * 5)
        calls = [c.args for c in run.call_args_list]
        self.assertEqual([c[0] for c in calls], ["plan-collection", "plan-analysis"] * 2
                         + ["import-collection", "import-analysis"] * 2)
        for call, week in zip(calls[5::2], ("2026-09-25", "2026-10-13")):
            self.assertIn("--publish", call)
            self.assertEqual(call[call.index("--week-date") + 1], week)

    def test_validation_failure_stops_before_import(self):
        with self.assertRaisesRegex(RuntimeError, "invalid dataset"):
            self.invoke([{"acquired": 1}] + [{"n": 0}] * 5,
                        failure=RuntimeError("invalid dataset"))


if __name__ == "__main__":
    unittest.main()
