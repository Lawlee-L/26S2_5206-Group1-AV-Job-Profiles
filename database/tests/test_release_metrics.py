import unittest

from database.importer.release_metrics import summarize_outcomes


class ReleaseMetricSummaryTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
