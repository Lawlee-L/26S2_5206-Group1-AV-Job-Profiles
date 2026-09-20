import json

import pytest
import requests

import av_jobs.translation.azure as azure_module
import av_jobs.translation.deepseek as deepseek_module
from av_jobs.translation.azure import split_text, translate_source_batch
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
            "Stellenbeschreibung: Sie entwickeln moderne Fahrerassistenzsysteme und arbeiten mit verschiedenen Teams an sicheren Softwarelösungen.",
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


def test_does_not_treat_japanese_bullet_as_japanese_text() -> None:
    records = [
        make_record(
            "english-bullets",
            "Data Engineer",
            "・Build data pipelines\n・Maintain autonomous driving systems",
            "Tokyo, Japan",
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


def test_azure_batch_splits_deduplicates_and_preserves_structure() -> None:
    long_text = "German text " * 500
    source_batch = [
        {
            "source_key": "job-1",
            "company": "Example",
            "fields": {"job_description": long_text, "location": "München"},
        },
        {
            "source_key": "job-2",
            "company": "Example",
            "fields": {"job_description": long_text},
        },
    ]
    calls: list[str] = []

    def fake_translate(texts: list[str]) -> list[str]:
        calls.extend(texts)
        return [
            text.replace("German", "English").replace("München", "Munich")
            for text in texts
        ]

    result = translate_source_batch(source_batch, fake_translate, group_size=20)

    assert "".join(split_text(long_text)) == long_text
    assert all(len(chunk) <= 4_500 for chunk in split_text(long_text))
    assert sum(chunk.count("German") for chunk in calls) == long_text.count("German")
    assert result[0]["fields"]["job_description"].startswith("English text")
    assert result[1]["fields"]["job_description"] == result[0]["fields"]["job_description"]
    assert result[0]["source_key"] == "job-1"


def test_azure_batch_rejects_remaining_non_english_text() -> None:
    source_batch = [
        {
            "source_key": "job-1",
            "company": "Example",
            "fields": {"job_description": "负责自动驾驶软件开发。"},
        }
    ]

    with pytest.raises(ValueError, match="Non-English content remains"):
        translate_source_batch(source_batch, lambda texts: texts)


def test_azure_batch_retries_only_the_failed_field() -> None:
    source_batch = [
        {
            "source_key": "job-1",
            "company": "Example",
            "fields": {"advertised_job_title": "软件_工程师"},
        }
    ]
    calls: list[list[str]] = []

    def fake_translate(texts: list[str]) -> list[str]:
        calls.append(texts)
        return [
            "Software Engineer" if text == "软件 工程师" else text
            for text in texts
        ]

    result = translate_source_batch(source_batch, fake_translate)

    assert result[0]["fields"]["advertised_job_title"] == "Software Engineer"
    assert calls == [["软件_工程师"], ["软件 工程师"]]


def test_azure_request_retries_a_network_timeout(monkeypatch) -> None:
    attempts = 0

    class SuccessfulResponse:
        status_code = 200

        def json(self) -> list[dict]:
            return [{"translations": [{"text": "English text"}]}]

    def fake_post(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise requests.Timeout("temporary timeout")
        return SuccessfulResponse()

    monkeypatch.setattr(azure_module.requests, "post", fake_post)
    monkeypatch.setattr(azure_module.time, "sleep", lambda seconds: None)

    result = azure_module._request_translation(
        ["Deutscher Text"],
        key="test-key",
        region="australiaeast",
        endpoint=azure_module.DEFAULT_ENDPOINT,
    )

    assert result == ["English text"]
    assert attempts == 2


def test_deepseek_request_preserves_order_and_disables_reasoning(monkeypatch) -> None:
    captured: dict = {}

    class SuccessfulResponse:
        status_code = 200

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"translations": ["Software Engineer", "Munich"]}
                            )
                        }
                    }
                ]
            }

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return SuccessfulResponse()

    monkeypatch.setattr(deepseek_module.requests, "post", fake_post)

    result = deepseek_module._request_translation(
        ["软件工程师", "München"],
        key="test-key",
    )

    assert result == ["Software Engineer", "Munich"]
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["reasoning"]["enabled"] is False
    assert captured["json"]["model"] == deepseek_module.DEFAULT_MODEL


def test_deepseek_rejects_missing_translation() -> None:
    content = json.dumps({"translations": ["Only one result"]})

    with pytest.raises(RuntimeError, match="unexpected number"):
        deepseek_module._parse_translations(content, expected_count=2)


def test_deepseek_repair_prompt_removes_repeated_source_text(monkeypatch) -> None:
    captured: dict = {}

    class SuccessfulResponse:
        status_code = 200

        def json(self) -> dict:
            return {
                "choices": [
                    {"message": {"content": '{"translations":["employee pension"]}'}}
                ]
            }

    def fake_post(*args, **kwargs):
        captured.update(kwargs)
        return SuccessfulResponse()

    monkeypatch.setattr(deepseek_module.requests, "post", fake_post)

    result = deepseek_module._request_translation(
        ["employee pension (厚生年金)"],
        key="test-key",
        repair=True,
    )

    assert result == ["employee pension"]
    prompt = captured["json"]["messages"][0]["content"]
    assert "remove the repeated source-language text" in prompt
