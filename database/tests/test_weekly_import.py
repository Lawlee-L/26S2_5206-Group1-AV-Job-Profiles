import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from database.weekly_import import (
    ImportErrorSafe,
    apply_analysis,
    load_analysis,
    load_collection,
    main,
    read_duplicates,
    verify_gzip_backup,
)


def source_record(key: str, title: str, job_id: str) -> dict:
    return {
        "metadata": {
            "source_key": key, "source_id": "wayve_uk_greenhouse", "source_job_id": job_id,
            "company": "Wayve", "platform": "greenhouse", "region": "UK",
            "collected_at": "2026-09-25T10:00:00Z", "first_seen_date": "2026-09-20",
            "last_seen_date": "2026-09-25", "is_active": True, "is_new_in_latest_run": False,
        },
        "data": {
            "advertised_job_title": title, "job_description": "Build AV software",
            "job_url": f"https://example.test/{job_id}", "location": "London",
            "salary": None, "date_posted": "2026-09-20T08:00:00Z",
        },
    }


def analysis_row(source: dict, relevant: bool, cluster_id: int) -> dict:
    meta, data = source["metadata"], source["data"]
    return {
        "source_key": meta["source_key"], "row_index": 0, "company": meta["company"],
        "name": data["advertised_job_title"], "date_posted": data["date_posted"],
        "cluster_id": cluster_id, "cluster_lean": "technical" if relevant else "n/a (noise)",
        "av_relevant": relevant, "av_relevant_model": relevant, "relevance_confidence": "High",
        "relevance_reason": "Evidence in posting", "seniority": "Senior", "seniority_source": "model",
        "experience_min": 3, "experience_max": 5, "experience_evidence": "3-5 years",
        "skills_tools": "Python", "skills_domain": "Perception", "skills_qualifications": "",
        "language_of_posting": "English", "role_summary": "Build AV systems",
        "platform": meta["platform"], "region": meta["region"], "location": data["location"],
        "job_url": data["job_url"],
        "record": {
            "role_summary": "Build AV systems", "responsibilities": ["Build AV software"],
            "requirements": ["Python experience"],
            "skills": {
                "tools": [{"name": "Python", "evidence": "Use Python"}],
                "domain": [{"name": "Perception", "evidence": "Perception systems"}],
                "qualifications": [],
            },
            "seniority": "Senior", "experience_min": 3, "experience_max": 5,
            "relevance_confidence": "High", "relevance_reason": "Evidence in posting",
        },
    }


def summary_row(cluster_id: int, size: int, noise: bool) -> dict:
    return {
        "cluster_id": cluster_id, "size": size, "is_noise": str(noise),
        "technical_score": "" if noise else "0.9", "lean": "n/a (noise)" if noise else "technical",
        "top_companies": "Wayve (1)", "top_terms": "perception, autonomy",
        "example_titles": "AV Engineer", "job_family": "", "specialisation": "", "notes": "",
    }


class WeeklyImportTests(unittest.TestCase):
    def write_json(self, path: Path, value) -> Path:
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def write_summary(self, path: Path, row: dict) -> Path:
        columns = ["cluster_id", "size", "is_noise", "technical_score", "lean", "top_companies",
                   "top_terms", "example_titles", "job_family", "specialisation", "notes"]
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerow(row)
        return path

    def write_empty_csv(self, path: Path, columns: list[str]) -> Path:
        with path.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerow(columns)
        return path

    def test_load_collection_requires_unique_source_key(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "collection.json"
            self.write_json(path, [source_record("same", "One", "1"), source_record("same", "Two", "2")])
            with self.assertRaisesRegex(ImportErrorSafe, "Duplicate source_key"):
                load_collection(path)

    def test_analysis_validates_exact_join_and_cluster_sizes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = [source_record("greenhouse|wayve|id:1", "AV Engineer", "1"),
                      source_record("greenhouse|wayve|id:2", "Accountant", "2")]
            source_path = self.write_json(directory / "jobs.json", source)
            postings = [analysis_row(source[0], True, 1), analysis_row(source[1], False, -1)]
            metadata = {
                "input": "jobs.json", "n_input_rows": 2, "n_after_dedupe": 2,
                "n_duplicates_removed": 0, "n_records": 2, "n_llm_failures": 0,
            }
            posts_path = self.write_json(directory / "postings_all.json", postings)
            meta_path = self.write_json(directory / "run_metadata.json", metadata)
            av_path = self.write_summary(directory / "av.csv", summary_row(1, 1, False))
            other_path = self.write_summary(directory / "other.csv", summary_row(-1, 1, True))
            dup_path = self.write_empty_csv(directory / "duplicates.csv", [
                "source_key", "row_index", "duplicate_of_source_key", "duplicate_type", "similarity"])
            failures_path = self.write_empty_csv(directory / "failures.csv", ["source_key", "row_index", "error"])
            report = load_analysis(posts_path, meta_path, source_path, av_path, other_path,
                                   dup_path, failures_path)
            self.assertEqual(report["postings"], 2)
            self.assertEqual(report["av_relevant"], 1)
            self.assertEqual(report["not_av_relevant"], 1)

    def test_analysis_blocks_unknown_source_key(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = [source_record("greenhouse|wayve|id:1", "AV Engineer", "1")]
            source_path = self.write_json(directory / "jobs.json", source)
            row = analysis_row(source[0], True, 1)
            row["source_key"] = "sha1:old-key"
            meta = {"input": "jobs.json", "n_input_rows": 1, "n_after_dedupe": 1,
                    "n_duplicates_removed": 0, "n_records": 1, "n_llm_failures": 0}
            dup_path = self.write_empty_csv(directory / "duplicates.csv", [
                "source_key", "row_index", "duplicate_of_source_key", "duplicate_type", "similarity"])
            failures_path = self.write_empty_csv(directory / "failures.csv", ["source_key", "row_index", "error"])
            with self.assertRaisesRegex(ImportErrorSafe, "does not exist in the supplied Li input"):
                load_analysis(self.write_json(directory / "postings.json", [row]),
                              self.write_json(directory / "meta.json", meta), source_path,
                              self.write_summary(directory / "av.csv", summary_row(1, 1, False)),
                              self.write_summary(directory / "other.csv", summary_row(-1, 0, True)),
                              dup_path, failures_path)

    def test_analysis_blocks_summary_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = [source_record("greenhouse|wayve|id:1", "AV Engineer", "1"),
                      source_record("greenhouse|wayve|id:2", "Accountant", "2")]
            source_path = self.write_json(directory / "jobs.json", source)
            meta = {"input": "jobs.json", "n_input_rows": 2, "n_after_dedupe": 2,
                    "n_duplicates_removed": 0, "n_records": 2, "n_llm_failures": 0}
            dup_path = self.write_empty_csv(directory / "duplicates.csv", [
                "source_key", "row_index", "duplicate_of_source_key", "duplicate_type", "similarity"])
            failures_path = self.write_empty_csv(directory / "failures.csv", ["source_key", "row_index", "error"])
            with self.assertRaisesRegex(ImportErrorSafe, "does not match"):
                load_analysis(self.write_json(directory / "postings.json", [
                                  analysis_row(source[0], True, 1), analysis_row(source[1], False, -1)]),
                              self.write_json(directory / "meta.json", meta), source_path,
                              self.write_summary(directory / "av.csv", summary_row(1, 9, False)),
                              self.write_summary(directory / "other.csv", summary_row(-1, 1, True)),
                              dup_path, failures_path)

    def test_duplicate_chain_is_preserved_when_acyclic(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicates.csv"
            path.write_text(
                "source_key,row_index,company,name,duplicate_of_source_key,duplicate_type,similarity\n"
                "k1,1,Wayve,One,k2,exact,1.0\n"
                "k2,2,Wayve,Two,k3,near,0.97\n",
                encoding="utf-8",
            )
            source_by_key = {
                "k1": {"company": "Wayve", "advertised_job_title": "One"},
                "k2": {"company": "Wayve", "advertised_job_title": "Two"},
                "k3": {"company": "Wayve", "advertised_job_title": "Three"},
            }
            duplicates = read_duplicates(path, source_by_key)
            self.assertEqual([row["kept_source_key"] for row in duplicates], ["k2", "k3"])

    def test_duplicate_cycle_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duplicates.csv"
            path.write_text(
                "source_key,row_index,company,name,duplicate_of_source_key,duplicate_type,similarity\n"
                "k1,1,Wayve,One,k2,exact,1.0\n"
                "k2,2,Wayve,Two,k1,exact,1.0\n",
                encoding="utf-8",
            )
            source_by_key = {
                "k1": {"company": "Wayve", "advertised_job_title": "One"},
                "k2": {"company": "Wayve", "advertised_job_title": "Two"},
            }
            with self.assertRaisesRegex(ImportErrorSafe, "cyclic duplicate chain"):
                read_duplicates(path, source_by_key)

    def test_corrupt_backup_is_rejected_before_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corrupt.sql.gz"
            path.write_bytes(b"not a gzip backup")
            with self.assertRaisesRegex(ImportErrorSafe, "complete readable gzip"):
                verify_gzip_backup(path)

    def test_analysis_import_requires_pipeline_commit_for_provenance(self):
        with self.assertRaisesRegex(ImportErrorSafe, "--git-commit"):
            apply_analysis(Path("missing-postings.json"), Path("missing-metadata.json"),
                           Path("missing-source.json"), Path("missing-av.csv"),
                           Path("missing-other.csv"), Path("missing-duplicates.csv"),
                           Path("missing-failures.csv"), Path("backups"))

    def test_plan_command_writes_per_run_report_and_append_only_log(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            input_path = self.write_json(directory / "jobs.json", [source_record("key-1", "AV Engineer", "1")])
            audit_dir = directory / "audit"
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["plan-collection", "--input", str(input_path),
                                  "--audit-dir", str(audit_dir)])
            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertTrue(Path(result["local_report"]).is_file())
            log_path = Path(result["local_log"])
            records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["operation"], "plan-collection")
            self.assertEqual(records[0]["status"], "succeeded")
            self.assertEqual(records[0]["result"]["rows"], 1)


if __name__ == "__main__":
    unittest.main()
