"""Opt-in integration test: creates its own database, never clears an existing one.

Set AVDB_RUN_MYSQL_TESTS=1 and normal AVDB_* connection credentials. It leaves
the small generated test database for inspection and makes real local backups.
No model calls or downloaded data are involved.
"""

import io
import json
import os
import re
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import date
from pathlib import Path
from unittest.mock import patch

from database import weekly_import as engine
from database.importer.cli import main as cli_main
from database.importer.contracts import (
    AnalysisFiles,
    CollectionFiles,
    ReleaseActivation,
)
from database.importer.errors import ImportErrorSafe
from database.importer.mysql_backend import MySQLImporterBackend
from database.importer.service import ImporterService
from database.importer import publication, release_revisions
from database.importer.location_parser import LOCATION_PARSER_VERSION
from database.tests import test_weekly_import as fixtures
from database.tests.test_weekly_import import source_record, analysis_row, summary_row


@unittest.skipUnless(
    os.environ.get("AVDB_RUN_MYSQL_TESTS") == "1",
    "opt-in isolated MySQL integration test",
)
class MySQLReleaseRevisionTests(unittest.TestCase):
    def setUp(self):
        import pymysql

        self.temp = tempfile.TemporaryDirectory(prefix="av-revision-test-")
        self.directory = Path(self.temp.name)
        self.backups = self.directory / "backups"
        self.database_name = "av_revision_test_" + uuid.uuid4().hex[:16]
        self.previous_name = os.environ.get("AVDB_NAME")
        config = engine.env_config()
        config.pop("database")
        config["cursorclass"] = pymysql.cursors.DictCursor
        admin = pymysql.connect(**config)
        try:
            with admin.cursor() as cursor:
                cursor.execute(
                    "SELECT SCHEMA_NAME FROM information_schema.schemata WHERE SCHEMA_NAME=%s",
                    (self.database_name,),
                )
                self.assertIsNone(cursor.fetchone(), "Test target must be new")
                for name in ("schema.mysql.sql", "views.mysql.sql"):
                    sql = (engine.ROOT / "database" / name).read_text(encoding="utf-8")
                    sql = re.sub(r"(?m)^\s*--.*$", "", sql).replace(
                        "av_job_profiles", self.database_name
                    )
                    for statement in sql.split(";"):
                        if statement.strip():
                            cursor.execute(statement)
        finally:
            admin.close()
        os.environ["AVDB_NAME"] = self.database_name
        self.service = ImporterService(MySQLImporterBackend(engine))
        self.writer = fixtures.WeeklyImportTests()

    def tearDown(self):
        print("Isolated MySQL integration database retained:", self.database_name)
        if self.previous_name is None:
            os.environ.pop("AVDB_NAME", None)
        else:
            os.environ["AVDB_NAME"] = self.previous_name
        self.temp.cleanup()

    def query(self, sql, params=()):
        connection = engine.db_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        finally:
            connection.close()

    def files(self, week, revision, source=None):
        folder = self.directory / week.isoformat()
        folder.mkdir(exist_ok=True)
        if source is None:
            source = [
                source_record("greenhouse|wayve|id:1", "AV Engineer", "1"),
                source_record("greenhouse|wayve|id:2", "Accountant", "2"),
            ]
            for record in source:
                record["metadata"]["last_seen_date"] = week.isoformat()
                record["metadata"]["collected_at"] = week.isoformat() + "T10:00:00Z"
        source_path = self.writer.write_json(
            folder / "jobs_history_translated.json", source
        )
        output = folder / revision
        output.mkdir(exist_ok=True)
        postings = [
            analysis_row(source[0], True, 1),
            analysis_row(source[1], False, -1),
        ]
        postings[0]["role_summary"] = "Revision " + revision
        postings[0]["record"]["role_summary"] = "Revision " + revision
        if revision == "B":
            postings[0]["skills_tools"] = "Rust"
            postings[0]["record"]["skills"]["tools"] = [
                {"name": "Rust", "evidence": "Updated test analysis"}
            ]
        return (
            AnalysisFiles(
                self.writer.write_json(output / "postings.json", postings),
                self.writer.write_json(
                    output / "metadata.json",
                    {
                        "input": str(source_path),
                        "n_input_rows": 2,
                        "n_after_dedupe": 2,
                        "n_duplicates_removed": 0,
                        "n_records": 2,
                        "n_llm_failures": 0,
                    },
                ),
                source_path,
                self.writer.write_summary(output / "av.csv", summary_row(1, 1, False)),
                self.writer.write_summary(
                    output / "other.csv", summary_row(-1, 1, True)
                ),
                self.writer.write_empty_csv(
                    output / "duplicates.csv",
                    [
                        "source_key",
                        "row_index",
                        "duplicate_of_source_key",
                        "duplicate_type",
                        "similarity",
                    ],
                ),
                self.writer.write_empty_csv(
                    output / "failures.csv", ["source_key", "row_index", "error"]
                ),
                week_date=week,
            ),
            source,
        )

    def selection(self, week):
        return self.query(
            "SELECT release_key FROM v_weekly_versions WHERE week_date=%s", (week,)
        )[0]["release_key"]

    def current(self):
        return self.query(
            "SELECT release_key FROM dashboard_releases WHERE status='published'"
        )[0]["release_key"]

    def hashes(self, key):
        return self.query(
            "SELECT row_kind,entity_key,row_sha256 FROM dashboard_release_snapshot_rows r "
            "JOIN dashboard_releases dr ON dr.dashboard_release_id=r.dashboard_release_id "
            "WHERE dr.release_key=%s ORDER BY row_kind,entity_key",
            (key,),
        )

    def activation(self, key, week_key, current_key, historical=False):
        return ReleaseActivation(
            key,
            week_key,
            current_key,
            "Integration test review",
            "test-operator",
            historical,
        )

    def test_real_import_upgrade_revert_history_and_atomic_failure(self):
        week = date(2026, 9, 25)
        a_files, source = self.files(week, "A")
        self.service.import_collection(
            CollectionFiles(a_files.source_snapshot, week_date=week), self.backups
        )
        a = self.service.import_analysis(a_files, self.backups, "abcdef0")[
            "release_key"
        ]
        self.service.publish_release(a, self.backups)
        original_hashes = self.hashes(a)
        self.assertEqual(self.current(), a)
        self.assertEqual(self.selection(week), a)

        # Same analysis, new release: no AI rerun or duplicate analysis import.
        clone = self.service.create_release(
            a, "Add detail read contract", "test-operator", self.backups
        )["release_key"]
        self.assertEqual(self.current(), a)
        self.assertFalse(
            self.service.list_releases(week)["releases"][-1]["selected_for_week"]
        )

        # A real, differently classified output is staged without replacing A.
        b_files, _ = self.files(week, "B", source)
        with self.assertRaisesRegex(
            ImportErrorSafe, "already has a selected classification"
        ):
            self.service.import_analysis(b_files, self.backups, "abcdef1")
        b = self.service.import_analysis(
            replace(b_files, candidate=True), self.backups, "abcdef1"
        )["release_key"]
        self.assertEqual(self.current(), a)
        self.assertEqual(self.selection(week), a)
        self.service.activate_release(self.activation(b, a, a), self.backups)
        self.assertEqual(self.current(), b)
        self.assertEqual(self.selection(week), b)
        self.assertEqual(self.hashes(a), original_hashes)
        b_hashes = self.hashes(b)
        self.assertEqual(
            self.query("SELECT role_summary FROM v_dashboard_job_details")[0][
                "role_summary"
            ],
            "Revision B",
        )
        self.assertIn(
            "Rust",
            {
                row["skill_name"]
                for row in self.query("SELECT skill_name FROM v_dashboard_job_skills")
            },
        )
        self.assertEqual(
            self.query(
                "SELECT COUNT(*) AS n FROM v_weekly_av_jobs WHERE week_date=%s", (week,)
            )[0]["n"],
            1,
        )
        self.assertEqual(
            self.query(
                "SELECT COUNT(*) AS n FROM v_weekly_versions WHERE week_date=%s",
                (week,),
            )[0]["n"],
            1,
        )
        with self.assertRaisesRegex(ImportErrorSafe, "already been imported"):
            self.service.import_analysis(
                replace(b_files, candidate=True), self.backups, "abcdef1"
            )

        # Fail after status/pointer updates: transaction must restore B. A
        # prepared frozen draft may remain, and is reusable on the next attempt.
        real_record = release_revisions.record_operation

        def fail_activation(*args, **kwargs):
            if kwargs["action"] == "activate":
                raise RuntimeError("Injected activation evidence failure")
            return real_record(*args, **kwargs)

        command = [
            "activate-release",
            "--release-key",
            clone,
            "--expected-week-release",
            b,
            "--expected-current-release",
            b,
            "--reason",
            "Test atomic failure",
            "--backup-dir",
            str(self.backups),
            "--audit-dir",
            str(self.directory / "audit"),
        ]
        with patch.object(
            release_revisions, "record_operation", side_effect=fail_activation
        ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli_main(command, implementation=engine), 1)
        self.assertEqual(self.current(), b)
        self.assertEqual(self.selection(week), b)
        self.assertEqual(
            self.query(
                "SELECT status FROM dashboard_releases WHERE release_key=%s", (clone,)
            )[0]["status"],
            "draft",
        )
        self.assertTrue(
            self.hashes(clone), "Prepared snapshot may remain but is not official"
        )
        reports = list((self.directory / "audit" / "reports").glob("*.json"))
        self.assertEqual(
            json.loads(reports[0].read_text(encoding="utf-8"))["status"], "failed"
        )
        log = self.directory / "audit/logs/weekly_import.jsonl"
        self.assertEqual(
            json.loads(log.read_text(encoding="utf-8").splitlines()[0])["status"],
            "failed",
        )
        with patch.object(
            release_revisions,
            "_materialize",
            side_effect=AssertionError("Must reuse frozen candidate"),
        ):
            self.service.activate_release(self.activation(clone, b, b), self.backups)
        self.assertEqual(self.current(), clone)
        self.service.activate_release(self.activation(b, clone, clone), self.backups)
        self.assertEqual(self.current(), b)
        self.assertEqual(self.hashes(b), b_hashes)
        with self.assertRaisesRegex(ImportErrorSafe, "Weekly selection changed"):
            self.service.activate_release(self.activation(a, "stale", b), self.backups)
        self.assertEqual(self.current(), b)

        # A newer current week must remain current while an older week reverts.
        newer = date(2026, 10, 2)
        d_files, _ = self.files(newer, "D")
        self.service.import_collection(
            CollectionFiles(d_files.source_snapshot, week_date=newer), self.backups
        )
        d = self.service.import_analysis(d_files, self.backups, "abcdef2")[
            "release_key"
        ]
        self.service.publish_release(d, self.backups)
        self.service.activate_release(self.activation(a, b, d, True), self.backups)
        self.assertEqual(self.current(), d)
        self.assertEqual(self.selection(week), a)
        self.assertEqual(self.selection(newer), d)
        self.assertEqual(self.hashes(a), original_hashes)
        self.assertEqual(
            self.query(
                "SELECT role_summary FROM v_weekly_av_job_details WHERE week_date=%s",
                (week,),
            )[0]["role_summary"],
            "Revision A",
        )
        with self.assertRaisesRegex(ImportErrorSafe, "must use --historical"):
            self.service.activate_release(self.activation(b, a, d), self.backups)
        self.assertEqual(self.current(), d)
        self.assertGreaterEqual(
            len(self.query("SELECT operation_id FROM release_operations")), 10
        )
        self.assertEqual(
            self.query("SELECT @@session.time_zone AS zone")[0]["zone"], "+00:00"
        )
        for backup in self.backups.glob("*.sql.gz"):
            engine.verify_gzip_backup(backup)

    def test_migration_preserves_ambiguous_history_for_explicit_review(self):
        import pymysql

        target = "av_revision_migration_" + uuid.uuid4().hex[:12]
        config = engine.env_config()
        config["cursorclass"] = pymysql.cursors.DictCursor
        connection = pymysql.connect(**config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT SCHEMA_NAME FROM information_schema.schemata WHERE SCHEMA_NAME=%s",
                    (target,),
                )
                self.assertIsNone(cursor.fetchone())
                cursor.execute(
                    f"CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
                )
                cursor.execute(f"USE `{target}`")
                cursor.execute(
                    "CREATE TABLE dashboard_releases (dashboard_release_id BIGINT UNSIGNED PRIMARY KEY,"
                    "collection_run_id BIGINT UNSIGNED,analysis_run_id BIGINT UNSIGNED NOT NULL,"
                    "status VARCHAR(24) NOT NULL,snapshot_frozen_at DATETIME(6)) ENGINE=InnoDB"
                )
                cursor.execute(
                    "CREATE TABLE weekly_versions (week_date DATE PRIMARY KEY,"
                    "collection_run_id BIGINT UNSIGNED NOT NULL,selected_analysis_run_id BIGINT UNSIGNED) ENGINE=InnoDB"
                )
                cursor.executemany(
                    "INSERT INTO weekly_versions VALUES (%s,%s,%s)",
                    [
                        ("2026-09-25", 1, 11),
                        ("2026-09-19", 2, 22),
                        ("2026-09-13", 3, 33),
                        ("2026-09-06", 4, 44),
                    ],
                )
                cursor.executemany(
                    "INSERT INTO dashboard_releases VALUES (%s,%s,%s,%s,%s)",
                    [
                        (1, 1, 11, "retired", "2026-09-26"),
                        (2, 1, 11, "published", "2026-09-27"),
                        (3, 2, 22, "retired", "2026-09-20"),
                        (4, 2, 22, "retired", "2026-09-21"),
                        (5, 3, 33, "retired", "2026-09-14"),
                        (6, 4, 44, "retired", None),
                    ],
                )
                connection.commit()
                sql = (
                    engine.ROOT / "database/migrations/007_release_revisions.sql"
                ).read_text(encoding="utf-8")
                sql = re.sub(r"(?m)^\s*--.*$", "", sql)
                for statement in sql.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
                connection.commit()
                cursor.execute(
                    "SELECT collection_run_id,selected_release_id FROM weekly_versions"
                )
                selected = {
                    row["collection_run_id"]: row["selected_release_id"]
                    for row in cursor.fetchall()
                }
                self.assertEqual(selected, {1: 2, 2: None, 3: 5, 4: None})
                with self.assertRaises(pymysql.err.IntegrityError):
                    cursor.execute(
                        "UPDATE weekly_versions SET selected_release_id=5 WHERE collection_run_id=1"
                    )
                connection.rollback()
        finally:
            connection.close()
            print("Isolated migration-selection test database retained:", target)

    def test_location_upgrade_reuses_analysis_preserves_history_and_reverts(self):
        week = date(2026, 9, 25)
        source = [source_record("greenhouse|wayve|id:1", "AV Engineer", "1"),
                  source_record("greenhouse|wayve|id:2", "Accountant", "2")]
        source[0]["data"]["location"] = "San Francisco, California, United States (Hybrid)"
        source[1]["data"]["location"] = "Berlin, DE"
        files, _ = self.files(week, "A", source)
        empty = {field: None for field in ("city", "state_region", "country_code", "remote_type")}
        # Emulate the old importer and its already-frozen, null-location release.
        with patch.object(engine, "location_fields", return_value=empty):
            imported = self.service.import_collection(
                CollectionFiles(files.source_snapshot, week_date=week), self.backups)
        old = self.service.import_analysis(files, self.backups, "abcdef0")["release_key"]
        with patch.object(publication, "enrich_snapshot_job", side_effect=dict):
            self.service.publish_release(old, self.backups)
        self.assertIsNone(self.query("SELECT country_code FROM v_dashboard_jobs")[0]["country_code"])
        old_hashes = self.hashes(old)
        old_jobs = self.query("SELECT * FROM jobs ORDER BY job_id")
        old_observations = self.query("SELECT * FROM job_observations ORDER BY job_id")
        self.assertEqual(self.service.qa_release(old)["location_quality"]["all_av_jobs"]
                         ["counts"]["country_code_populated"], 0)

        new = self.service.create_release(old, "Location enrichment", "test-operator", self.backups)["release_key"]
        preview = self.service.qa_release(new)["location_quality"]
        self.assertEqual(preview["active_av_jobs"]["country_counts"], {"US": 1})
        self.service.activate_release(self.activation(new, old, old), self.backups)
        visible = self.query("SELECT * FROM v_dashboard_jobs")[0]
        self.assertEqual((visible["city"], visible["state_region"], visible["country_code"], visible["remote_type"]),
                         ("San Francisco", "CA", "US", "hybrid"))
        self.assertEqual(visible["location_parser_version"], LOCATION_PARSER_VERSION)
        self.assertEqual(visible["location_raw"], source[0]["data"]["location"])
        self.assertEqual(self.hashes(old), old_hashes)
        self.assertEqual(self.query("SELECT * FROM jobs ORDER BY job_id"), old_jobs)
        self.assertEqual(self.query("SELECT * FROM job_observations ORDER BY job_id"), old_observations)
        runs = self.query("SELECT analysis_run_id,collection_run_id FROM dashboard_releases WHERE release_key IN (%s,%s)", (old,new))
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(self.query("SELECT country_code FROM v_weekly_av_jobs WHERE week_date=%s", (week,))[0]["country_code"], "US")
        self.assertIsNone(self.query("SELECT country_code FROM v_weekly_jobs WHERE week_date=%s", (week,))[0]["country_code"])
        final_qa = self.service.qa_release(new)
        self.assertEqual(final_qa["status"], "passed")
        self.assertEqual(final_qa["location_quality"]["representation"], "frozen snapshot")

        new_hashes = self.hashes(new)
        self.service.activate_release(self.activation(old, new, new), self.backups)
        self.assertIsNone(self.query("SELECT country_code FROM v_dashboard_jobs")[0]["country_code"])
        self.service.activate_release(self.activation(new, old, old), self.backups)
        self.assertEqual(self.hashes(new), new_hashes)
        self.assertEqual(self.hashes(old), old_hashes)

        # A new collection writes both latest and observed fields; rollback
        # must restore every previous field rather than keep the new geography.
        later = date(2026, 10, 2)
        later_files, _ = self.files(later, "D")
        changed = self.service.import_collection(
            CollectionFiles(later_files.source_snapshot, week_date=later), self.backups)
        self.assertEqual(changed["location_quality"]["country_counts"], {"GB": 2})
        self.assertEqual(self.query("SELECT country_code FROM v_weekly_jobs WHERE week_date=%s", (later,))[0]["country_code"], "GB")
        self.assertEqual(self.query("SELECT country_code FROM jobs LIMIT 1")[0]["country_code"], "GB")
        self.service.rollback(changed["import_batch_id"], self.backups)
        self.assertEqual(self.query("SELECT * FROM jobs ORDER BY job_id"), old_jobs)
        self.assertEqual(self.query("SELECT * FROM job_observations ORDER BY job_id"), old_observations)
        metadata = self.query("SELECT metadata_json FROM import_batches WHERE import_batch_id=%s", (imported["import_batch_id"],))[0]["metadata_json"]
        self.assertIn("location_quality", json.loads(metadata))


if __name__ == "__main__":
    unittest.main()
