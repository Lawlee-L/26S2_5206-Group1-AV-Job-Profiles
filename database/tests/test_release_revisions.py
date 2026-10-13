import copy
import hashlib
import json
import os
import unittest
from contextlib import redirect_stderr
from datetime import date
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from database.importer.cli import _analysis_files_from_args, make_parser
from database.importer.contracts import ReleaseActivation
from database.importer.errors import ImportErrorSafe
from database.importer.mysql_backend import MySQLImporterBackend
from database.importer.release_revisions import (
    check_activation,
    check_frozen_counts,
    validate_reason,
)
from database.importer.service import ImporterService
from database.importer.snapshot_integrity import check_snapshot_rows
from database.importer.weekly_versions import selected_collection
from database.tests.test_weekly_versions import CursorStub
from database.weekly_import import stable_json, env_config


def snapshot_fixture():
    payloads = [
        ("job", "2", {"job_id": 2, "source_key": "x|2", "av_relevant": True}),
        ("job", "10", {"job_id": 10, "source_key": "x|10", "av_relevant": 1}),
        ("job_skill", "2:3", {"job_id": 2, "skill_id": 3, "source_key": "x|2"}),
        ("cluster", "4", {"cluster_pk": 4, "population": "av_relevant"}),
    ]
    digest = hashlib.sha256()
    rows = []
    for kind, key, payload in payloads:
        row_hash = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
        rows.append(
            {
                "row_kind": kind,
                "entity_key": key,
                "payload_json": json.dumps(payload),
                "row_sha256": row_hash,
            }
        )
        digest.update(f"{kind}:{key}:{row_hash}\n".encode("utf-8"))
    return rows, digest.hexdigest()


class ReleaseRevisionTests(unittest.TestCase):
    def test_importer_connections_use_utc_for_audit_timestamps(self):
        with patch.dict(
            os.environ, {"AVDB_USER": "test-user", "AVDB_PASSWORD": "test-secret"}
        ):
            self.assertEqual(env_config()["init_command"], "SET time_zone = '+00:00'")

    def setUp(self):
        self.release = {
            "status": "draft",
            "data_cutoff_date": date(2026, 9, 25),
            "snapshot_frozen_at": None,
        }
        self.week = {"release_key": "A"}
        self.current = {
            "release_key": "A",
            "data_cutoff_date": date(2026, 9, 25),
            "snapshot_frozen_at": "frozen",
        }
        self.request = ReleaseActivation("B", "A", "A", "Reviewed new output", "Nyx")

    def test_same_week_upgrade_guards_accept_expected_selections(self):
        check_activation(self.request, self.release, self.week, self.current)

    def test_stale_week_selection_stops(self):
        with self.assertRaisesRegex(ImportErrorSafe, "Weekly selection changed"):
            check_activation(
                self.request, self.release, {"release_key": "C"}, self.current
            )

    def test_stale_current_selection_stops(self):
        with self.assertRaisesRegex(ImportErrorSafe, "Current dashboard changed"):
            check_activation(
                self.request,
                self.release,
                self.week,
                {**self.current, "release_key": "C"},
            )

    def test_first_candidate_can_be_activated_from_no_selection(self):
        check_activation(
            ReleaseActivation("B", None, None, "First review", "Nyx"),
            self.release,
            {"release_key": None},
            None,
        )

    def test_history_cannot_change_current_week_without_current_switch(self):
        with self.assertRaisesRegex(ImportErrorSafe, "omit --historical"):
            check_activation(
                ReleaseActivation("B", "A", "A", "History", "Nyx", True),
                self.release,
                self.week,
                self.current,
            )

    def test_older_week_requires_historical_flag(self):
        older = {**self.release, "data_cutoff_date": date(2026, 9, 19)}
        with self.assertRaisesRegex(ImportErrorSafe, "must use --historical"):
            check_activation(self.request, older, self.week, self.current)
        check_activation(
            ReleaseActivation("B", "A", "A", "History update", "Nyx", True),
            older,
            self.week,
            self.current,
        )

    def test_legacy_current_must_be_frozen(self):
        with self.assertRaisesRegex(ImportErrorSafe, "freeze-release"):
            check_activation(
                self.request,
                self.release,
                self.week,
                {**self.current, "snapshot_frozen_at": None},
            )

    def test_retired_target_must_have_snapshot(self):
        with self.assertRaisesRegex(ImportErrorSafe, "not frozen"):
            check_activation(
                self.request,
                {**self.release, "status": "retired"},
                self.week,
                self.current,
            )

    def test_reason_and_actor_required(self):
        for reason, actor in (
            (" ", "Nyx"),
            ("Reason", ""),
            ("x" * 4001, "Nyx"),
            ("Reason", "x" * 129),
        ):
            with self.subTest(reason=reason[:10], actor=actor[:10]), self.assertRaises(
                ImportErrorSafe
            ):
                validate_reason(reason, actor)

    def test_candidate_does_not_relax_collection_pairing(self):
        selected_collection(
            CursorStub({"collection_run_id": 1, "selected_analysis_run_id": 10}),
            date(2026, 9, 25),
            1,
            candidate=True,
        )
        with self.assertRaisesRegex(ImportErrorSafe, "not the official collection"):
            selected_collection(
                CursorStub({"collection_run_id": 2, "selected_analysis_run_id": 10}),
                date(2026, 9, 25),
                1,
                candidate=True,
            )

    def test_activation_cli_requires_compare_and_switch_arguments(self):
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            make_parser().parse_args(
                ["activate-release", "--release-key", "B", "--reason", "Review"]
            )
        args = make_parser().parse_args(
            [
                "activate-release",
                "--release-key",
                "B",
                "--reason",
                "Review",
                "--expected-week-release",
                "A",
                "--expected-current-release",
                "A",
            ]
        )
        self.assertEqual(args.command, "activate-release")

    def test_candidate_flag_survives_cli_and_backend_adapter(self):
        args = make_parser().parse_args(
            [
                "import-analysis",
                "--candidate",
                "--week-date",
                "2026-09-25",
                "--git-commit",
                "abcdef0",
                "--postings",
                "p.json",
                "--metadata",
                "m.json",
                "--source-input",
                "li.json",
                "--av-summary",
                "av.csv",
                "--other-summary",
                "other.csv",
                "--duplicates",
                "d.csv",
                "--failures",
                "f.csv",
            ]
        )
        files = _analysis_files_from_args(args)
        self.assertTrue(files.candidate)
        calls = []
        engine = SimpleNamespace(
            apply_analysis=lambda *a, **kw: calls.append(kw) or {"ok": True}
        )
        MySQLImporterBackend(engine).import_analysis(files, Path("backups"), "abcdef0")
        self.assertTrue(calls[0]["candidate"])

    def test_service_forwards_requests_without_sql_or_cli_dependencies(self):
        calls = []
        backend = SimpleNamespace(
            activate_release=lambda request, path: calls.append((request, path))
            or {"ok": True}
        )
        result = ImporterService(backend).activate_release(
            self.request, Path("backups")
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, [(self.request, Path("backups"))])

    def test_frozen_counts_check_skill_and_cluster_coverage(self):
        counts = {"job": 2, "cluster": 1, "skilled_jobs": 1}
        qa = {
            "metrics": {
                "av_postings": 2,
                "av_clusters": 1,
                "av_postings_without_skills": 1,
            }
        }
        check_frozen_counts(counts, qa)
        for field in counts:
            with self.subTest(field=field), self.assertRaises(ImportErrorSafe):
                check_frozen_counts({**counts, field: 0}, qa)


class SnapshotIntegrityTests(unittest.TestCase):
    def test_numeric_order_and_mysql_json_reformatting_do_not_break_hashes(self):
        rows, digest = snapshot_fixture()
        counts = check_snapshot_rows(list(reversed(rows)), digest, stable_json)
        self.assertEqual(
            counts, {"job": 2, "job_skill": 1, "cluster": 1, "skilled_jobs": 1}
        )

    def test_row_tampering_stops_activation(self):
        rows, digest = snapshot_fixture()
        payload = json.loads(rows[0]["payload_json"])
        payload["source_key"] = "tampered"
        rows[0]["payload_json"] = json.dumps(payload)
        with self.assertRaisesRegex(ImportErrorSafe, "row hash mismatch"):
            check_snapshot_rows(rows, digest, stable_json)

    def test_removed_row_fails_aggregate_hash(self):
        rows, digest = snapshot_fixture()
        with self.assertRaisesRegex(ImportErrorSafe, "aggregate hash"):
            check_snapshot_rows(rows[:-1], digest, stable_json)

    def test_duplicate_entities_and_unknown_kinds_stop(self):
        rows, digest = snapshot_fixture()
        with self.assertRaisesRegex(ImportErrorSafe, "duplicate"):
            check_snapshot_rows(rows + [copy.deepcopy(rows[0])], digest, stable_json)
        rows[0]["row_kind"] = "unexpected"
        with self.assertRaisesRegex(ImportErrorSafe, "unknown kind"):
            check_snapshot_rows(rows, digest, stable_json)

    def test_payload_key_must_match_entity_key(self):
        rows, digest = snapshot_fixture()
        rows[0]["entity_key"] = "7"
        with self.assertRaisesRegex(ImportErrorSafe, "entity key"):
            check_snapshot_rows(rows, digest, stable_json)

    def test_skill_must_reference_same_frozen_job(self):
        rows, digest = snapshot_fixture()
        payload = json.loads(rows[2]["payload_json"])
        payload["source_key"] = "different"
        rows[2]["payload_json"] = stable_json(payload)
        rows[2]["row_sha256"] = hashlib.sha256(
            stable_json(payload).encode()
        ).hexdigest()
        with self.assertRaisesRegex(ImportErrorSafe, "different job"):
            check_snapshot_rows(rows, digest, stable_json)

    def test_non_av_snapshot_job_rejected_even_if_row_hash_matches(self):
        rows, digest = snapshot_fixture()
        payload = json.loads(rows[0]["payload_json"])
        payload["av_relevant"] = False
        rows[0]["payload_json"] = stable_json(payload)
        rows[0]["row_sha256"] = hashlib.sha256(
            stable_json(payload).encode()
        ).hexdigest()
        with self.assertRaisesRegex(ImportErrorSafe, "non-AV"):
            check_snapshot_rows(rows, digest, stable_json)


if __name__ == "__main__":
    unittest.main()
