"""Normalise detail fields before they become an immutable release payload."""

from __future__ import annotations

import json
from typing import Any

from .errors import ImportErrorSafe


def job_detail_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep full source text and publish extracted sections as JSON arrays.

    MySQL drivers return JSON columns as either strings or decoded values.
    Normalize that difference at publication, without guessing missing text
    or consulting a different collection/analysis version.
    """
    result = payload.copy()
    key = payload.get("source_key", payload.get("job_id", "unknown"))
    for field in ("job_description", "role_summary"):
        value = payload.get(field)
        if value is not None and not isinstance(value, str):
            raise ImportErrorSafe(f"Job {key}: {field} must be text or null")
        result[field] = value
    for field in ("responsibilities_json", "requirements_json"):
        value = payload.get(field)
        if isinstance(value, (str, bytes, bytearray)):
            try:
                value = json.loads(value)
            except (ValueError, UnicodeError) as exc:
                raise ImportErrorSafe(f"Job {key}: invalid {field}") from exc
        if value is None:
            value = []
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ImportErrorSafe(f"Job {key}: {field} must be an array of text")
        result[field] = value
    return result
