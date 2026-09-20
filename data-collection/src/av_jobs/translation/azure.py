from __future__ import annotations

import argparse
import getpass
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import requests

from av_jobs.translation.language_check import find_non_english_records
from av_jobs.translation.workflow import validate_translation_batch


DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
# Use conservative limits that work with the Translator REST endpoint.
MAX_REQUEST_CHARACTERS = 4_500
MAX_REQUEST_ITEMS = 25


def split_text(text: str, limit: int = MAX_REQUEST_CHARACTERS) -> list[str]:
    """Split long text without losing characters."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = max(
            remaining.rfind("\n", 0, limit),
            remaining.rfind(". ", 0, limit),
            remaining.rfind(" ", 0, limit),
        )
        if split_at < limit // 2:
            split_at = limit
        else:
            split_at += 1
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]
    if remaining:
        chunks.append(remaining)
    return chunks


def _request_translation(
    texts: list[str],
    *,
    key: str,
    region: str,
    endpoint: str,
    max_retries: int = 7,
) -> list[str]:
    url = endpoint.rstrip("/") + "/translate"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }
    params = {"api-version": "3.0", "to": "en"}
    body = [{"Text": text} for text in texts]

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                params=params,
                json=body,
                timeout=120,
            )
        except requests.RequestException as error:
            if attempt == max_retries:
                raise RuntimeError(
                    "Azure translation failed after repeated network errors"
                ) from error
            # Temporary connection failures use the same safe retry delay.
            wait_seconds = min(2**attempt, 30)
            print(
                "Azure request timed out or lost connection; "
                f"retrying in {wait_seconds} seconds."
            )
            time.sleep(wait_seconds)
            continue

        if response.status_code == 200:
            payload = response.json()
            if not isinstance(payload, list) or len(payload) != len(texts):
                raise RuntimeError("Azure returned an unexpected response size")
            return [str(item["translations"][0]["text"]) for item in payload]

        if response.status_code != 429 and response.status_code < 500:
            raise RuntimeError(
                f"Azure returned HTTP {response.status_code}: {response.text}"
            )
        if attempt == max_retries:
            raise RuntimeError(
                f"Azure translation failed after retries: HTTP {response.status_code}"
            )

        # Respect Azure's delay when available, otherwise use exponential backoff.
        retry_after = response.headers.get("Retry-After")
        wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        wait_seconds = min(max(wait_seconds, 1), 30)
        print(f"Azure rate limited the request; retrying in {wait_seconds} seconds.")
        time.sleep(wait_seconds)

    raise RuntimeError("Azure translation did not return a result")


def _translate_unique_texts(
    texts: list[str],
    translate_chunks: Callable[[list[str]], list[str]],
) -> dict[str, str]:
    chunk_tasks: list[tuple[str, int, str]] = []
    chunks_by_text: dict[str, list[str]] = {}
    for text in texts:
        chunks = split_text(text)
        chunks_by_text[text] = [""] * len(chunks)
        chunk_tasks.extend((text, index, chunk) for index, chunk in enumerate(chunks))

    batch: list[tuple[str, int, str]] = []
    batch_characters = 0

    def submit() -> None:
        nonlocal batch, batch_characters
        if not batch:
            return
        translated = translate_chunks([task[2] for task in batch])
        if len(translated) != len(batch):
            raise RuntimeError("Translator returned an unexpected number of items")
        for (source, index, _), value in zip(batch, translated, strict=True):
            chunks_by_text[source][index] = value
        batch = []
        batch_characters = 0

    for task in chunk_tasks:
        chunk_length = len(task[2])
        if batch and (
            len(batch) >= MAX_REQUEST_ITEMS
            or batch_characters + chunk_length > MAX_REQUEST_CHARACTERS
        ):
            submit()
        batch.append(task)
        batch_characters += chunk_length
    submit()

    return {source: "".join(chunks) for source, chunks in chunks_by_text.items()}


def _find_failed_fields(
    translated_batch: list[dict[str, Any]],
) -> dict[str, set[str]]:
    failed: dict[str, set[str]] = {}
    for item in translated_batch:
        source_key = str(item.get("source_key", ""))
        findings = find_non_english_records(
            [
                {
                    "metadata": {
                        "source_key": source_key,
                        "company": item.get("company"),
                    },
                    "data": item.get("fields", {}),
                }
            ]
        )
        if findings:
            failed[source_key] = set(findings[0]["fields"])
    return failed


def _retry_failed_fields(
    source_batch: list[dict[str, Any]],
    translated_batch: list[dict[str, Any]],
    translate_chunks: Callable[[list[str]], list[str]],
    checkpoint: Callable[[list[dict[str, Any]]], None] | None,
    *,
    repair_chunks: Callable[[list[str]], list[str]] | None = None,
    max_attempts: int = 3,
) -> None:
    source_by_key = {str(item["source_key"]): item for item in source_batch}
    translated_by_key = {
        str(item["source_key"]): item for item in translated_batch
    }

    for attempt in range(max_attempts):
        failed = _find_failed_fields(translated_batch)
        if not failed:
            return

        retry_inputs: list[str] = []
        field_inputs: list[tuple[dict[str, Any], str, str]] = []
        for source_key, fields in failed.items():
            source_fields = source_by_key[source_key]["fields"]
            translated_fields = translated_by_key[source_key]["fields"]
            for field in fields:
                value = source_fields[field] if attempt == 0 else translated_fields[field]
                # Separators can make Azure treat a mixed-language title as an ID.
                value = re.sub(r"(?<=\w):(?=\w)", " ", value.replace("_", " "))
                retry_inputs.append(value)
                field_inputs.append((translated_fields, field, value))

        translated_values = _translate_unique_texts(
            list(dict.fromkeys(retry_inputs)),
            repair_chunks or translate_chunks,
        )
        for fields, field, retry_input in field_inputs:
            fields[field] = translated_values[retry_input]

        # Keep repaired fields in the same resumable checkpoint.
        if checkpoint:
            checkpoint(translated_batch)
        print(
            f"Retried {len(field_inputs)} field(s) that still appeared non-English "
            f"(repair pass {attempt + 1}/{max_attempts})."
        )


def translate_source_batch(
    source_batch: list[dict[str, Any]],
    translate_chunks: Callable[[list[str]], list[str]],
    *,
    repair_chunks: Callable[[list[str]], list[str]] | None = None,
    existing: list[dict[str, Any]] | None = None,
    checkpoint: Callable[[list[dict[str, Any]]], None] | None = None,
    group_size: int = 20,
) -> list[dict[str, Any]]:
    """Translate a prepared batch with deduplication and resumable checkpoints."""
    completed = {
        str(item["source_key"]): item
        for item in (existing or [])
        if isinstance(item, dict) and item.get("source_key")
    }
    source_by_key = {
        str(item["source_key"]): item
        for item in source_batch
        if isinstance(item, dict) and item.get("source_key")
    }
    if len(source_by_key) != len(source_batch):
        raise ValueError("Source batch contains missing or duplicate source_key values")

    # Rebuild the cache from the checkpoint so repeated text is not charged twice.
    cache: dict[str, str] = {}
    for source_key, translated_item in completed.items():
        source_item = source_by_key.get(source_key)
        if not source_item:
            continue
        source_fields = source_item.get("fields")
        translated_fields = translated_item.get("fields")
        if isinstance(source_fields, dict) and isinstance(translated_fields, dict):
            for field, source_text in source_fields.items():
                translated_text = translated_fields.get(field)
                if isinstance(source_text, str) and isinstance(translated_text, str):
                    cache[source_text] = translated_text

    pending = [
        item for item in source_batch if str(item["source_key"]) not in completed
    ]
    translated_characters = 0
    for start in range(0, len(pending), group_size):
        group = pending[start : start + group_size]
        new_texts: list[str] = []
        seen_texts: set[str] = set()
        for item in group:
            fields = item.get("fields")
            if not isinstance(fields, dict):
                raise ValueError(f"Invalid fields for {item.get('source_key')}")
            for value in fields.values():
                if not isinstance(value, str) or not value:
                    raise ValueError(f"Invalid source text for {item.get('source_key')}")
                if value not in cache and value not in seen_texts:
                    seen_texts.add(value)
                    new_texts.append(value)

        cache.update(_translate_unique_texts(new_texts, translate_chunks))
        translated_characters += sum(len(text) for text in new_texts)
        for item in group:
            fields = item["fields"]
            completed[str(item["source_key"])] = {
                "source_key": item["source_key"],
                "company": item.get("company"),
                "fields": {field: cache[value] for field, value in fields.items()},
            }

        ordered = [completed[str(item["source_key"])] for item in source_batch if str(item["source_key"]) in completed]
        if checkpoint:
            # Save each completed group so an interrupted run can resume safely.
            checkpoint(ordered)
        print(
            f"Completed {len(ordered)}/{len(source_batch)} records; "
            f"{translated_characters:,} new characters translated in this run."
        )

    result = [completed[str(item["source_key"])] for item in source_batch]
    _retry_failed_fields(
        source_batch,
        result,
        translate_chunks,
        checkpoint,
        repair_chunks=repair_chunks,
    )
    # Reuse the shared checker before any Azure result can be accepted.
    validate_translation_batch(source_batch, result)
    return result


def _load_list(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"{path} does not contain a JSON list")
    return loaded


def _write_list(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate a prepared job batch with Azure Translator."
    )
    parser.add_argument("source_batch", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--region", required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args()

    source_batch = _load_list(args.source_batch)
    partial_path = args.output.with_name(args.output.stem + ".partial.json")
    existing = _load_list(partial_path) if partial_path.exists() else []
    key = getpass.getpass("Paste Azure Translator KEY 1 (hidden): ").strip()
    if not key:
        raise ValueError("Azure Translator key is required")

    def translate_chunks(texts: list[str]) -> list[str]:
        return _request_translation(
            texts,
            key=key,
            region=args.region,
            endpoint=args.endpoint,
        )

    try:
        result = translate_source_batch(
            source_batch,
            translate_chunks,
            existing=existing,
            checkpoint=lambda records: _write_list(partial_path, records),
        )
    except ValueError as error:
        saved = _load_list(partial_path) if partial_path.exists() else []
        failed = _find_failed_fields(saved)
        if not failed:
            raise

        passed_path = args.output.with_name(args.output.stem + ".passed.json")
        review_path = args.output.with_name(args.output.stem + ".review.json")
        passed = [
            item for item in saved if str(item.get("source_key")) not in failed
        ]
        review = [
            {
                **item,
                "failed_fields": sorted(failed[str(item["source_key"])]),
            }
            for item in saved
            if str(item.get("source_key")) in failed
        ]
        # Keep successful output separate from fields that still need review.
        _write_list(passed_path, passed)
        _write_list(review_path, review)
        print(f"English validation passed: {len(passed)} records")
        print(f"Still needs review after retries: {len(review)} records")
        print(f"Passed results: {passed_path}")
        print(f"Review results: {review_path}")
        raise SystemExit(str(error)) from None

    _write_list(args.output, result)
    print(f"Azure translation complete: {len(result)} records")
    print(f"Output: {args.output}")
    print(f"Checkpoint: {partial_path}")


if __name__ == "__main__":
    main()
