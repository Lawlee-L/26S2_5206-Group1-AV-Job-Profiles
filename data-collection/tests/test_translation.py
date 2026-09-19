import pytest

from av_jobs.translation.language_check import find_non_english_records
from av_jobs.translation.workflow import (
    merge_translation_batch,
    prepare_translation_batch,
    validate_translation_batch,
)


def make_record(
    source_key: str,
    title: str,
    description: str,
    location: str = "Stuttgart, BW, Germany",
    first_seen_date: str = "2026-09-19",
) -> dict:
    return {
        "metadata": {
            "source_key": source_key,
            "company": "Example",
            "first_seen_date": first_seen_date,
        },
        "data": {
            "advertised_job_title": title,
            "job_description": description,
            "location": location,
            "job_url": f"https://example.com/{source_key}",
        },
    }


def test_finds_latin_and_non_latin_languages() -> None:
    records = [
        make_record(
            "german",
            "Entwicklungsingenieur für Fahrerassistenzsysteme",
            "Stellenbeschreibung: Sie entwickeln moderne Fahrerassistenzsysteme.",
        ),
        make_record(
            "japanese",
            "自動運転ソフトウェアエンジニア",
            "We build autonomous driving software.",
            "東京、日本",
        ),
        make_record(
            "english",
            "Software Engineer",
            "We build autonomous driving software for production vehicles.",
        ),
    ]

    findings = find_non_english_records(records)
    by_key = {item["source_key"]: item for item in findings}

    assert set(by_key) == {"german", "japanese"}
    assert "job_description" in by_key["german"]["fields"]
    assert "advertised_job_title" in by_key["japanese"]["fields"]
    assert "location" in by_key["japanese"]["fields"]


def test_does_not_flag_english_place_names_or_technical_titles() -> None:
    records = [
        make_record(
            "english",
            "Deep Learning Developer - REM Modeling",
            "We build autonomous driving software for production vehicles.",
            "Pittsburgh, PA",
        )
    ]

    assert find_non_english_records(records) == []


def test_date_filter_only_returns_weekly_jobs() -> None:
    records = [
        make_record("old", "软件工程师", "负责自动驾驶软件开发。", first_seen_date="2026-09-13"),
        make_record("new", "软件工程师", "负责自动驾驶软件开发。"),
    ]

    findings = find_non_english_records(records, first_seen_date="2026-09-19")

    assert [item["source_key"] for item in findings] == ["new"]


def test_prepares_validates_and_merges_translation() -> None:
    records = [make_record("job-1", "软件工程师", "负责自动驾驶软件开发。", "上海市")]
    source_batch = prepare_translation_batch(records)
    translated_batch = [
        {
            "source_key": "job-1",
            "company": "Example",
            "fields": {
                "advertised_job_title": "Software Engineer",
                "job_description": "Develop autonomous driving software.",
                "location": "Shanghai",
            },
        }
    ]

    merged = merge_translation_batch(records, source_batch, translated_batch)

    assert merged[0]["data"]["advertised_job_title"] == "Software Engineer"
    assert merged[0]["data"]["job_url"] == "https://example.com/job-1"
    assert records[0]["data"]["advertised_job_title"] == "软件工程师"


def test_validation_rejects_missing_or_untranslated_output() -> None:
    records = [make_record("job-1", "软件工程师", "负责自动驾驶软件开发。", "上海市")]
    source_batch = prepare_translation_batch(records)

    with pytest.raises(ValueError, match="source_key mismatch"):
        validate_translation_batch(source_batch, [])

    with pytest.raises(ValueError, match="Non-English content remains"):
        validate_translation_batch(source_batch, source_batch)

