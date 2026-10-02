import unittest

from database.importer.release_metrics import release_qa_report, summarize_outcomes


class ReleaseMetricSummaryTests(unittest.TestCase):
    def test_empty_snapshot_fails_qa(self):
        self.assertFalse(summarize_outcomes([], [], [])["checks"]["source_snapshot_not_empty"])

    def test_partition_and_av_counts_accept_mysql_boolean_integers(self):
        source = [
            {"job_id": 1, "company_id": 10},
            {"job_id": 2, "company_id": 10},
            {"job_id": 3, "company_id": 11},
            {"job_id": 4, "company_id": 10},
        ]
        analyses = [
            {"job_id": 1, "analysis_status": "success", "av_relevant": 1},
            {"job_id": 2, "analysis_status": "success", "av_relevant": 0},
            {"job_id": 3, "analysis_status": "failed", "av_relevant": None},
        ]
        duplicates = [{
            "duplicate_job_id": 4, "kept_job_id": 1,
            "duplicate_company_id": 10, "kept_company_id": 10,
        }]

        report = summarize_outcomes(source, analyses, duplicates)

        self.assertEqual(report["metrics"]["source_postings"], 4)
        self.assertEqual(report["metrics"]["deduplicated_postings"], 1)
        self.assertEqual(report["metrics"]["analysed_postings"], 2)
        self.assertEqual(report["metrics"]["av_postings"], 1)
        self.assertEqual(report["metrics"]["non_av_postings"], 1)
        self.assertEqual(report["metrics"]["failed_or_pending"], 1)
        self.assertEqual(report["metrics"]["unaccounted"], 0)
        self.assertTrue(all(report["checks"].values()))

    def test_unknown_relevance_is_not_counted_as_non_av(self):
        source = [{"job_id": 1, "company_id": 10}, {"job_id": 2, "company_id": 10}]
        analyses = [
            {"job_id": 1, "analysis_status": "success", "av_relevant": None},
            {"job_id": 2, "analysis_status": "success", "av_relevant": False},
        ]

        metrics = summarize_outcomes(source, analyses, [])["metrics"]

        self.assertEqual(metrics["analysed_postings"], 2)
        self.assertEqual(metrics["av_postings"], 0)
        self.assertEqual(metrics["non_av_postings"], 1)
        self.assertEqual(metrics["unknown_relevance"], 1)

    def test_overlap_cycle_cross_company_and_unaccounted_are_reported(self):
        source = [{"job_id": 1, "company_id": 10}, {"job_id": 2, "company_id": 11},
                  {"job_id": 3, "company_id": 10}]
        analyses = [{"job_id": 1, "analysis_status": "success", "av_relevant": True}]
        duplicates = [
            {"duplicate_job_id": 1, "kept_job_id": 2,
             "duplicate_company_id": 10, "kept_company_id": 11},
            {"duplicate_job_id": 2, "kept_job_id": 1,
             "duplicate_company_id": 11, "kept_company_id": 10},
        ]

        report = summarize_outcomes(source, analyses, duplicates)

        self.assertEqual(report["metrics"]["unaccounted"], 1)
        self.assertEqual(report["metrics"]["duplicate_analysis_overlap"], 1)
        self.assertEqual(report["metrics"]["duplicate_cycles"], 2)
        self.assertEqual(report["metrics"]["duplicate_company_mismatches"], 2)
        self.assertEqual(report["metrics"]["av_postings"], 0)
        self.assertFalse(report["checks"]["source_partition_balanced"])
        self.assertFalse(report["checks"]["no_unaccounted_source_jobs"])
        self.assertFalse(report["checks"]["duplicate_chains_acyclic"])
        self.assertFalse(report["checks"]["duplicate_targets_same_company"])

    def test_missing_duplicate_target_and_external_analysis_are_reported(self):
        source = [{"job_id": 1, "company_id": 10}]
        analyses = [{"job_id": 9, "analysis_status": "success", "av_relevant": True}]
        duplicates = [{
            "duplicate_job_id": 1, "kept_job_id": 8,
            "duplicate_company_id": 10, "kept_company_id": 10,
        }]

        report = summarize_outcomes(source, analyses, duplicates)

        self.assertEqual(report["metrics"]["analysis_rows_outside_snapshot"], 1)
        self.assertEqual(report["metrics"]["duplicate_broken_targets"], 1)
        self.assertFalse(report["checks"]["duplicate_targets_in_snapshot"])
        self.assertFalse(report["checks"]["no_analysis_outside_collection_snapshot"])


class ReleaseViewQATests(unittest.TestCase):
    def report(self, status="published", company_count=1, skilled_count=1, job_rows=1,
               noise=False):
        """Script the read-only DB responses for one AV job with a skill."""
        published = status == "published"
        responses = iter([
            dict(dashboard_release_id=1, release_key="test", status=status,
                 collection_run_id=1, analysis_run_id=1, cluster_run_id=1,
                 data_cutoff_date="2026-09-25", collection_run_key="source",
                 collection_run_status="partial", analysis_run_key="analysis",
                 analysis_collection_run_id=1,
                 snapshot_frozen_at="2026-09-26" if published else None,
                 snapshot_sha256="a" * 64 if published else None,
                 analysis_run_status="completed", cluster_run_key="clusters",
                 cluster_run_status="completed"),
            [dict(job_id=1, company_id=1)],
            dict(mismatches=0),
            [dict(job_id=1, job_analysis_id=1, analysis_status="success", av_relevant=1)],
            [],
            [dict(job_id=1, job_analysis_id=1, analysis_status="success", av_relevant=1,
                  cluster_pk=1, population="av_relevant", size_cached=1)],
            [dict(cluster_pk=1, population="av_relevant", size_cached=1, member_count=1,
                  is_noise=int(noise), cluster_name=None, label_status=None)],
            dict(skillless_av_jobs=0),
            dict(visible_job_rows=job_rows if published else 0,
                 visible_job_count=1 if published else 0,
                 visible_company_count=company_count if published else 0),
            dict(visible_skilled_job_count=skilled_count if published else 0),
            dict(violations=0), dict(violations=0),
            dict(visible_cluster_count=1 if published else 0, visible_non_av_cluster_count=0),
        ])

        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, *args): self.response = next(responses)
            def fetchone(self): return self.response
            def fetchall(self): return self.response

        class Connection:
            def cursor(self): return Cursor()

        result = release_qa_report(Connection(), "test")
        self.assertEqual(list(responses), [])
        return result

    def test_published_counts_pass_and_missing_labels_warn(self):
        result = self.report()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["metrics"]["av_clusters_without_approved_names"], 1)
        self.assertEqual(result["metrics"]["av_noise_clusters"], 0)
        self.assertIn("no approved name", result["warnings"][0])

    def test_noise_cluster_is_not_counted_as_a_missing_approved_name(self):
        result = self.report(noise=True)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["metrics"]["av_clusters_without_approved_names"], 0)
        self.assertEqual(result["metrics"]["av_noise_clusters"], 1)
        self.assertEqual(result["metrics"]["av_noise_postings"], 1)

    def test_missing_skills_or_companies_fail_even_when_job_count_matches(self):
        self.assertIn("published_skilled_job_count_matches_av_skills", self.report(skilled_count=0)["errors"])
        self.assertIn("published_company_count_matches_av_companies", self.report(company_count=0)["errors"])

    def test_duplicate_public_rows_fail(self):
        self.assertIn("public_job_rows_are_unique", self.report(job_rows=2)["errors"])

    def test_draft_empty_views_do_not_fail_completeness_checks(self):
        self.assertEqual(self.report(status="draft")["status"], "passed")


if __name__ == "__main__":
    unittest.main()
