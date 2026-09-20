from __future__ import annotations

import argparse
import getpass
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from av_jobs.translation.azure import (
    _find_failed_fields,
    _load_list,
    _write_list,
    translate_source_batch,
)


DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731:free"

SYSTEM_PROMPT = """Translate every input string into clear English for downstream LLM job analysis.
Use one fast, direct translation pass. Do not review, refine, or polish the wording. Literal wording
is acceptable when the meaning remains clear. Translate only non-English text and copy existing
English unchanged. Preserve the complete meaning, especially job titles, responsibilities,
qualifications, and skills. Keep company and product names, technical terms, abbreviations, URLs,
identifiers, numbers, list structure, and line breaks unchanged. Do not summarise, omit, interpret,
explain, or add information. Return exactly one translation for every input string in the same
order, using only the required JSON structure."""

REPAIR_PROMPT = """The inputs are previous English translations that may contain small untranslated
fragments. Make one direct repair pass and return English-only text. Translate every remaining
non-English fragment. When an English translation and its source-language text both appear, keep
only the English meaning and remove the repeated source-language text, including source text in
parentheses. Preserve all other content, technical terms, numbers, names, URLs, list structure, and
line breaks. Do not summarise, rewrite, explain, or add information. Return exactly one repaired
string for every input string in the same order, using only the required JSON structure."""


def _parse_translations(content: str, expected_count: int) -> list[str]:
    """Read the structured translations returned by the model."""
    value = content.strip()
    if value.startswith("```"):
        value = value.removeprefix("```json").removeprefix("```")
        value = value.removesuffix("```").strip()

    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise RuntimeError("DeepSeek returned invalid JSON") from error

    translations = payload.get("translations") if isinstance(payload, dict) else None
    if not isinstance(translations, list) or len(translations) != expected_count:
        raise RuntimeError(
            "DeepSeek returned an unexpected number of translations: "
            f"expected {expected_count}"
        )
    if not all(isinstance(item, str) and item.strip() for item in translations):
        raise RuntimeError("DeepSeek returned an empty or invalid translation")
    return translations


def _request_translation(
    texts: list[str],
    *,
    key: str,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    repair: bool = False,
    max_retries: int = 6,
) -> list[str]:
    """Translate one small text batch through the OpenRouter API."""
    # Send the API key only in the request header.
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Title": "AV Job Translation Pipeline",
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": REPAIR_PROMPT if repair else SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps({"texts": texts}, ensure_ascii=False),
            },
        ],
        "temperature": 0,
        "max_tokens": 8_192,
        # Translation does not need a long reasoning trace.
        "reasoning": {"enabled": False, "exclude": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "translation_batch",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "translations": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["translations"],
                    "additionalProperties": False,
                },
            },
        },
    }

    # Retry temporary network, rate-limit, and server errors.
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=body,
                timeout=180,
            )
        except requests.RequestException as error:
            if attempt == max_retries:
                raise RuntimeError(
                    "DeepSeek translation failed after repeated network errors"
                ) from error
            wait_seconds = min(2**attempt, 30)
            print(
                "OpenRouter connection failed; "
                f"retrying in {wait_seconds} seconds."
            )
            time.sleep(wait_seconds)
            continue

        if response.status_code == 200:
            try:
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise RuntimeError("OpenRouter returned an unexpected response") from error
            if not isinstance(content, str):
                raise RuntimeError("OpenRouter returned an empty response")
            return _parse_translations(content, len(texts))

        if response.status_code != 429 and response.status_code < 500:
            raise RuntimeError(
                f"OpenRouter returned HTTP {response.status_code}: {response.text}"
            )
        if attempt == max_retries:
            raise RuntimeError(
                "DeepSeek translation failed after retries: "
                f"HTTP {response.status_code}"
            )

        retry_after = response.headers.get("Retry-After")
        wait_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        wait_seconds = min(max(wait_seconds, 1), 30)
        print(f"OpenRouter is busy; retrying in {wait_seconds} seconds.")
        time.sleep(wait_seconds)

    raise RuntimeError("DeepSeek translation did not return a result")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate a prepared job batch with DeepSeek through OpenRouter."
    )
    parser.add_argument("source_batch", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args()

    source_batch = _load_list(args.source_batch)
    partial_path = args.output.with_name(args.output.stem + ".partial.json")
    # Resume completed records instead of translating them again.
    existing = _load_list(partial_path) if partial_path.exists() else []

    # The key stays in memory and is never saved in the repository.
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        key = getpass.getpass("Paste OpenRouter API key (hidden): ").strip()
    if not key:
        raise ValueError("OpenRouter API key is required")

    def translate_chunks(texts: list[str]) -> list[str]:
        return _request_translation(
            texts,
            key=key,
            endpoint=args.endpoint,
            model=args.model,
        )

    def repair_chunks(texts: list[str]) -> list[str]:
        # Use a focused prompt when normal translation leaves source text behind.
        return _request_translation(
            texts,
            key=key,
            endpoint=args.endpoint,
            model=args.model,
            repair=True,
        )

    try:
        # Reuse the shared batching, checkpoint, and validation workflow.
        result = translate_source_batch(
            source_batch,
            translate_chunks,
            repair_chunks=repair_chunks,
            existing=existing,
            checkpoint=lambda records: _write_list(partial_path, records),
        )
    except ValueError as error:
        # Missing records, fields, or malformed data are fatal validation errors.
        if not str(error).startswith("Non-English content remains"):
            raise
        saved = _load_list(partial_path) if partial_path.exists() else []
        failed = _find_failed_fields(saved)
        if not failed:
            raise

        # Report record-level problems without discarding the completed run.
        for source_key, fields in sorted(failed.items()):
            field_names = ", ".join(sorted(fields))
            print(
                f"[WARNING] source_key={source_key}; fields={field_names}; "
                "non-English content remains after 3 repair passes."
            )
        _write_list(args.output, saved)
        print("Translation completed with warnings; remaining records were preserved.")
        print(f"Translated records: {len(saved)}")
        print(f"Records requiring attention: {len(failed)}")
        print(f"Output: {args.output}")
        return

    _write_list(args.output, result)
    print(f"Translated records: {len(result)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
