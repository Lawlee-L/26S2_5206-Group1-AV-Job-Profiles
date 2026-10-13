"""Versioned hashes for classifier input identity and canonical job changes.

The description hash mirrors classification-pipeline ``clean.py`` v2:
NFKC/punctuation/whitespace normalization followed by SHA-1 over lower-case,
whitespace-collapsed UTF-8 text. The SHA-256 record hash covers the six
canonical collection fields and is independent of classifier deduplication.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping


HASH_CONTRACT_VERSION = "av-job-hash-v1"
DESCRIPTION_HASH_ALGORITHM = "sha1"
RECORD_HASH_ALGORITHM = "sha256"
RECORD_HASH_FIELDS = (
    "advertised_job_title",
    "job_description",
    "job_url",
    "location_raw",
    "salary_raw",
    "date_posted",
)

_WS_RE = re.compile(r"[ \t ]+")
_MULTINL_RE = re.compile(r"\n{3,}")
_BULLET_RE = re.compile(r"^\s*[•●▪‣⁃*·]\s*", re.M)
_UNICODE_FIXES = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", "\u00a0": " ",
    "…": "...", "\ufeff": "",
}


def normalize_classifier_text(text: str | None) -> str:
    """Mirror the classifier's v2 text normalization before it hashes input."""
    text = unicodedata.normalize("NFKC", text or "")
    for bad, good in _UNICODE_FIXES.items():
        text = text.replace(bad, good)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _BULLET_RE.sub("- ", text)
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTINL_RE.sub("\n\n", text)
    return text.strip()


def classifier_description_sha1(text: str | None) -> str:
    """Return the pipeline-compatible SHA-1 for one raw job description."""
    normalized = normalize_classifier_text(text)
    collapsed = re.sub(r"\s+", " ", normalized.lower()).strip()
    return hashlib.sha1(collapsed.encode("utf-8")).hexdigest()


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def canonical_record_sha256(values: Mapping[str, Any]) -> str:
    """Hash canonical collection fields for change detection, not job identity."""
    selected = {name: values.get(name) for name in RECORD_HASH_FIELDS}
    payload = json.dumps(
        selected,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
