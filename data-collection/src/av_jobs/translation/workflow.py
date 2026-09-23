from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from av_jobs.translation.language_check import find_non_english_records


def prepare_translation_batch(
    records: list[dict[str, Any]],
    *,
    first_seen_date: str | None = None,
) -> list[dict[str, Any]]:
    """Create a compact translation batch from a job-history list."""
    findings = find_non_english_records(
        records,
        first_seen_date=first_seen_date,
    )
    return [
        {
            "source_key": item["source_key"],
            "company": item["company"],
            "fields": {
                field: finding["value"]
                for field, finding in item["fields"].items()
            },
        }
        for item in findings
    ]


def _index_batch(batch: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in batch:
        source_key = item.get("source_key")
        if not isinstance(source_key, str) or not source_key:
            raise ValueError(f"{label} contains an item without source_key")
        if source_key in indexed:
            raise ValueError(f"{label} contains duplicate source_key: {source_key}")
        indexed[source_key] = item
    return indexed


def validate_translation_batch(
    source_batch: list[dict[str, Any]],
    translated_batch: list[dict[str, Any]],
) -> None:
    """Confirm that a translation batch is complete and appears fully English."""
    source = _index_batch(source_batch, "Source batch")
    translated = _index_batch(translated_batch, "Translated batch")

    # Never merge a response that lost or invented a job.
    missing = sorted(source.keys() - translated.keys())
    extra = sorted(translated.keys() - source.keys())
    if missing or extra:
        raise ValueError(
            f"Translation source_key mismatch; missing={missing}, extra={extra}"
        )

    for source_key, source_item in source.items():
        expected_fields = source_item.get("fields")
        translated_fields = translated[source_key].get("fields")
        if not isinstance(expected_fields, dict) or not isinstance(translated_fields, dict):
            raise ValueError(f"Invalid fields object for {source_key}")

        missing_fields = sorted(expected_fields.keys() - translated_fields.keys())
        extra_fields = sorted(translated_fields.keys() - expected_fields.keys())
        if missing_fields or extra_fields:
            raise ValueError(
                f"Translation field mismatch for {source_key}; "
                f"missing={missing_fields}, extra={extra_fields}"
            )
        for field, value in translated_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Empty translated field for {source_key}: {field}")

    # Reuse the same language check before accepting translated text.
    remaining = []
    for item in translated_batch:
        fields = item.get("fields")
        if not isinstance(fields, dict):
            continue
        checks = find_non_english_records(
            [
                {
                    "metadata": {
                        "source_key": item["source_key"],
                        "company": item.get("company"),
                    },
                    "data": fields,
                }
            ]
        )
        remaining.extend(checks)
    if remaining:
        keys = sorted(str(item["source_key"]) for item in remaining)
        raise ValueError(f"Non-English content remains for source_key values: {keys}")


def merge_translation_batch(
    records: list[dict[str, Any]],
    source_batch: list[dict[str, Any]],
    translated_batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and merge translated fields into a copy of the job history."""
    validate_translation_batch(source_batch, translated_batch)
    translations = _index_batch(translated_batch, "Translated batch")
    merged = deepcopy(records)
    seen: set[str] = set()

    for record in merged:
        metadata = record.get("metadata")
        data = record.get("data")
        if not isinstance(metadata, dict) or not isinstance(data, dict):
            continue
        source_key = metadata.get("source_key")
        if source_key not in translations:
            continue
        data.update(translations[source_key]["fields"])
        seen.add(str(source_key))

    missing_records = sorted(translations.keys() - seen)
    if missing_records:
        raise ValueError(f"History is missing source_key values: {missing_records}")
    return merged


def _load_list(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path} does not contain a JSON list")
    return loaded


def _write_list(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare, validate, and merge job-history translations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("history", type=Path)
    prepare_parser.add_argument("output", type=Path)
    prepare_parser.add_argument("--first-seen-date")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("source_batch", type=Path)
    validate_parser.add_argument("translated_batch", type=Path)

    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("history", type=Path)
    merge_parser.add_argument("source_batch", type=Path)
    merge_parser.add_argument("translated_batch", type=Path)
    merge_parser.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "prepare":
        batch = prepare_translation_batch(
            _load_list(args.history),
            first_seen_date=args.first_seen_date,
        )
        _write_list(args.output, batch)
        print(f"Records prepared for translation: {len(batch)}")
        print(f"Batch: {args.output}")
    elif args.command == "validate":
        validate_translation_batch(
            _load_list(args.source_batch),
            _load_list(args.translated_batch),
        )
        print("Translation batch is complete and contains no detected non-English fields.")
    else:
        merged = merge_translation_batch(
            _load_list(args.history),
            _load_list(args.source_batch),
            _load_list(args.translated_batch),
        )
        _write_list(args.output, merged)
        print(f"Merged records: {len(merged)}")
        print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
