from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from langdetect import DetectorFactory, LangDetectException, detect_langs


# Keep language detection results consistent between runs.
DetectorFactory.seed = 0

TRANSLATABLE_FIELDS = (
    "advertised_job_title",
    "job_description",
    "location",
)

NON_LATIN_SCRIPTS = {
    "ar": ((0x0600, 0x06FF),),
    "el": ((0x0370, 0x03FF),),
    "he": ((0x0590, 0x05FF),),
    "ja": ((0x3040, 0x30FF),),
    "ko": ((0xAC00, 0xD7AF),),
    "ru": ((0x0400, 0x052F),),
    "th": ((0x0E00, 0x0E7F),),
    "zh": ((0x3400, 0x4DBF), (0x4E00, 0x9FFF)),
}


def _non_latin_language(text: str) -> str | None:
    for character in text:
        codepoint = ord(character)
        for language, ranges in NON_LATIN_SCRIPTS.items():
            if any(start <= codepoint <= end for start, end in ranges):
                return language
    return None


@lru_cache(maxsize=100_000)
def detect_non_english(text: Any) -> dict[str, Any] | None:
    """Return a language finding when a non-empty value is confidently non-English."""
    if not isinstance(text, str) or not text.strip():
        return None

    value = text.strip()
    script_language = _non_latin_language(value)
    if script_language:
        return {"language": script_language, "confidence": 1.0}

    letters = "".join(character for character in value if character.isalpha())
    if len(letters) < 8:
        return None

    try:
        candidates = detect_langs(value)
    except LangDetectException:
        return None
    if not candidates:
        return None

    best = candidates[0]
    if best.lang != "en" and best.prob >= 0.90:
        return {
            "language": best.lang,
            "confidence": round(float(best.prob), 4),
        }
    return None


def find_non_english_fields(data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the translated fields in one job that appear to be non-English."""
    findings: dict[str, dict[str, Any]] = {}
    description_finding = detect_non_english(data.get("job_description"))
    for field in TRANSLATABLE_FIELDS:
        value = data.get(field)
        finding = description_finding if field == "job_description" else detect_non_english(value)
        if not finding:
            continue

        if isinstance(value, str) and field == "advertised_job_title":
            # Avoid treating short English technical titles as another language.
            letters = "".join(character for character in value if character.isalpha())
            has_non_ascii_letter = any(
                character.isalpha() and not character.isascii()
                for character in value
            )
            is_long_single_word = " " not in value.strip() and len(letters) >= 15
            if not (
                _non_latin_language(value)
                or description_finding
                or has_non_ascii_letter
                or is_long_single_word
            ):
                continue

        if (
            isinstance(value, str)
            and field == "location"
            and _non_latin_language(value) is None
            and description_finding is None
        ):
            # Short place names are unreliable input for statistical detection.
            continue

        findings[field] = {"value": value, **finding}
    return findings


def find_non_english_records(
    records: list[dict[str, Any]],
    *,
    first_seen_date: str | None = None,
) -> list[dict[str, Any]]:
    """Find job-history records containing fields that appear non-English."""
    results: list[dict[str, Any]] = []
    for record in records:
        metadata = record.get("metadata")
        data = record.get("data")
        if not isinstance(metadata, dict) or not isinstance(data, dict):
            continue
        if first_seen_date and metadata.get("first_seen_date") != first_seen_date:
            continue

        fields = find_non_english_fields(data)
        if fields:
            results.append(
                {
                    "source_key": metadata.get("source_key"),
                    "company": metadata.get("company"),
                    "first_seen_date": metadata.get("first_seen_date"),
                    "fields": fields,
                }
            )
    return results


def load_job_history(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path} does not contain a JSON list")
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find non-English fields in a job-history JSON file."
    )
    parser.add_argument("input", type=Path, help="Job-history JSON file to check")
    parser.add_argument("--first-seen-date", help="Only check jobs first seen on this date")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    findings = find_non_english_records(
        load_job_history(args.input),
        first_seen_date=args.first_seen_date,
    )
    report = json.dumps(findings, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    print(f"Records containing non-English fields: {len(findings)}")
    if args.output:
        print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
