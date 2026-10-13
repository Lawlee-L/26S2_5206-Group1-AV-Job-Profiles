"""Release detail payloads must preserve text, arrays and version boundaries."""

import json
import unittest

from database.importer.errors import ImportErrorSafe
from database.importer.job_details import job_detail_payload


class JobDetailPayloadTests(unittest.TestCase):
    def test_mysql_json_strings_become_arrays_not_double_encoded_strings(self):
        original = {
            "job_id": 7, "source_key": "source|7", "job_description": "Original description",
            "role_summary": "Analysed summary", "responsibilities_json": '["Build AV systems"]',
            "requirements_json": '["Python", "Three years experience"]',
        }
        result = job_detail_payload(original)
        self.assertEqual(result["responsibilities_json"], ["Build AV systems"])
        self.assertEqual(json.loads(json.dumps(result))["requirements_json"],
                         ["Python", "Three years experience"])
        self.assertEqual(original["responsibilities_json"], '["Build AV systems"]')
        self.assertEqual(result["job_id"], 7)

    def test_already_decoded_arrays_preserve_quotes_and_unicode(self):
        result = job_detail_payload({"responsibilities_json": ['Use "C++"', "协作"],
                                     "requirements_json": ["Python\nLinux"]})
        self.assertEqual(result["responsibilities_json"], ['Use "C++"', "协作"])
        self.assertEqual(result["requirements_json"], ["Python\nLinux"])

    def test_missing_content_remains_unknown_instead_of_invented(self):
        result = job_detail_payload({"responsibilities_json": None, "requirements_json": "null"})
        self.assertIsNone(result["job_description"])
        self.assertIsNone(result["role_summary"])
        self.assertEqual(result["responsibilities_json"], [])
        self.assertEqual(result["requirements_json"], [])

    def test_full_length_description_is_not_truncated(self):
        description = "AV description 中文 " * 10000
        self.assertEqual(job_detail_payload({"job_description": description})["job_description"], description)

    def test_invalid_json_refuses_publication(self):
        with self.assertRaises(ImportErrorSafe):
            job_detail_payload({"source_key": "x", "requirements_json": "not JSON"})

    def test_sections_must_be_arrays_of_text(self):
        for invalid in ({"skill": "Python"}, [None], [12], '"Python"'):
            with self.subTest(invalid=invalid), self.assertRaises(ImportErrorSafe):
                job_detail_payload({"responsibilities_json": invalid})

    def test_description_and_summary_must_be_text_or_null(self):
        for field in ("job_description", "role_summary"):
            with self.subTest(field=field), self.assertRaises(ImportErrorSafe):
                job_detail_payload({field: ["do not silently join this"]})


if __name__ == "__main__":
    unittest.main()
