"""Location enrichment must not alter identity, classifier inputs or old releases."""

import json
import tempfile
import unittest
from pathlib import Path

from database import weekly_import as engine
from database.importer.errors import ImportErrorSafe
from database.importer.hashing import canonical_record_sha256, classifier_description_sha1
from database.importer.location_enrichment import enrich_snapshot_job, location_fields, location_quality
from database.importer.location_parser import LOCATION_PARSER_VERSION, parse_location
from database.tests.test_weekly_import import source_record


class LocationRegressionTests(unittest.TestCase):
    def test_country_codes_do_not_become_north_american_regions(self):
        for text, country in (("Berlin, DE", "DE"), ("Bangalore, IN", "IN"),
                              ("Tel Aviv, IL", "IL"), ("Amsterdam, NL", "NL")):
            with self.subTest(text=text):
                result = parse_location(text)
                self.assertEqual(result.country_code, country)
                self.assertIsNone(result.state_region)

    def test_ambiguous_suffix_without_context_remains_null(self):
        for text in ("Unknown City, DE", "Unknown City, IN", "Unknown City, IL",
                     "Unknown City, NL", "Unknown City, CA", "Perth, WA"):
            with self.subTest(text=text):
                self.assertIsNone(parse_location(text).country_code)

    def test_real_us_regions_and_explicit_countries_keep_hierarchy(self):
        for text, city, region, country in (
            ("Dover, DE", "Dover", "DE", "US"),
            ("Indianapolis, IN", "Indianapolis", "IN", "US"),
            ("Chicago, IL", "Chicago", "IL", "US"),
            ("San Francisco, CA, US", "San Francisco", "CA", "US"),
            ("San Francisco, California, United States (Hybrid)", "San Francisco", "CA", "US"),
            ("Stuttgart, BW, Germany", "Stuttgart", "BW", "DE"),
        ):
            with self.subTest(text=text):
                result = parse_location(text)
                self.assertEqual((result.city, result.state_region, result.country_code), (city, region, country))

    def test_partial_multi_location_is_not_treated_as_single_country(self):
        self.assertIsNone(parse_location("Austin, TX | Unspecified office").country_code)
        self.assertIsNone(parse_location("Austin, TX | Berlin, Germany").country_code)

    def test_comma_lists_of_different_countries_stay_unresolved(self):
        for text in ("Berlin, Germany, Austin, United States", "Berlin, DE, Austin, TX",
                     "Berlin, DE, London, UK", "Remote - US, Berlin, Germany",
                     "London, Berlin, Germany"):
            with self.subTest(text=text):
                parsed = parse_location(text)
                self.assertIsNone(parsed.country_code)
                self.assertIsNone(parsed.city)

    def test_remote_country_prefix_and_onsite_suffix(self):
        parsed = parse_location("Remote - U.S, Ann Arbor, MI")
        self.assertEqual((parsed.city, parsed.state_region, parsed.country_code, parsed.remote_type),
                         ("Ann Arbor", "MI", "US", "remote"))
        parsed = parse_location("Berlin, Germany (On-site)")
        self.assertEqual((parsed.city, parsed.country_code, parsed.remote_type), ("Berlin", "DE", "onsite"))

    def test_multi_location_never_invents_single_city_or_state(self):
        parsed = parse_location("Pittsburgh, PA, Palo Alto, CA, Detroit, MI")
        self.assertEqual(parsed.country_code, "US")
        self.assertIsNone(parsed.city)
        self.assertIsNone(parsed.state_region)
        self.assertIsNone(parse_location("Beijing, Nanjing, China").city)

    def test_district_is_not_used_as_a_chinese_city(self):
        self.assertIsNone(parse_location("China, Guangdong, Haizhu District").city)
        self.assertEqual(parse_location("China, Shanghai, Xuhui District").city, "Shanghai")

    def test_work_mode_needs_positive_unambiguous_evidence(self):
        for text in ("Berlin, Germany", "Berlin, Germany - not remote",
                     "Berlin, Germany - Remote or Hybrid", "Berlin, Germany - hybridized team",
                     "Berlin, Germany - not onsite", "Berlin, Germany - hybrid not available"):
            with self.subTest(text=text):
                self.assertIsNone(parse_location(text).remote_type)
        self.assertEqual(parse_location("Berlin, Germany (Hybrid)").remote_type, "hybrid")
        self.assertEqual(parse_location("Berlin, Germany - On-site").remote_type, "onsite")


class LocationEnrichmentTests(unittest.TestCase):
    def test_collection_preserves_keys_raw_data_and_both_hashes(self):
        record = source_record("greenhouse|wayve|id:1", "AV Engineer", "1")
        record["data"]["location"] = "San Francisco, California, United States (Hybrid)"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "jobs.json"
            path.write_text(json.dumps([record]), encoding="utf-8")
            rows, digest = engine.load_collection(path)
            row = rows[0]
            self.assertEqual(digest, engine.sha256_file(path))
            self.assertEqual(row["raw_record"], record)
            self.assertEqual(row["source_key"], record["metadata"]["source_key"])
            self.assertEqual(row["location_raw"], record["data"]["location"])
            self.assertEqual((row["city"], row["state_region"], row["country_code"], row["remote_type"]),
                             ("San Francisco", "CA", "US", "hybrid"))
            self.assertEqual(row["content_hash"], classifier_description_sha1(record["data"]["job_description"]))
            old_row = dict(row, city=None, state_region=None, country_code=None, remote_type=None)
            self.assertEqual(row["record_hash_sha256"], canonical_record_sha256(old_row))
            self.assertEqual(engine.collection_plan(rows, digest)["location_quality"]["counts"]["country_code_populated"], 1)

    def test_new_snapshot_does_not_mutate_older_payload(self):
        original = {"source_key": "stable:1", "location_raw": "Berlin, Germany (Hybrid)",
                    "country_code": None, "city": None, "state_region": None, "remote_type": None}
        enriched = enrich_snapshot_job(original)
        self.assertIsNone(original["country_code"])
        self.assertEqual(enriched["country_code"], "DE")
        self.assertEqual(enriched["remote_type"], "hybrid")
        self.assertEqual(enriched["source_key"], "stable:1")
        self.assertEqual(enriched["location_parser_version"], LOCATION_PARSER_VERSION)

    def test_overlong_locality_remains_null_instead_of_truncation(self):
        fields = location_fields("A" * 192 + ", Germany")
        self.assertIsNone(fields["city"])
        self.assertEqual(fields["country_code"], "DE")

    def test_location_quality_reports_missing_and_unresolved_separately(self):
        rows = []
        for key, raw in (("1", "Berlin, Germany - Hybrid"), ("2", None),
                         ("3", "Unknown office"), ("4", "Austin, TX | Berlin, Germany")):
            rows.append({"source_key": key, "location_raw": raw, **location_fields(raw)})
        report = location_quality(rows, sample_limit=1)
        self.assertEqual(report["counts"]["rows"], 4)
        self.assertEqual(report["counts"]["raw_location_missing"], 1)
        self.assertEqual(report["counts"]["unresolved_nonempty_location"], 2)
        self.assertEqual(report["country_counts"], {"DE": 1, "unknown": 3})
        self.assertEqual(report["work_mode_counts"], {"hybrid": 1, "unknown": 3})
        self.assertEqual(len(report["unresolved_samples"]), 1)

    def test_non_string_location_still_fails_validation(self):
        record = source_record("greenhouse|wayve|id:1", "AV Engineer", "1")
        record["data"]["location"] = {"city": "Berlin"}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "jobs.json"
            path.write_text(json.dumps([record]), encoding="utf-8")
            with self.assertRaises(ImportErrorSafe):
                engine.load_collection(path)
