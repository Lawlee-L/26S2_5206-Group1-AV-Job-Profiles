"""Validate frozen payloads without rewriting or borrowing mutable source text."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from .errors import ImportErrorSafe

_KEYS = {
    "job": ("job_id",),
    "job_skill": ("job_id", "skill_id"),
    "cluster": ("cluster_pk",),
}


def check_snapshot_rows(
    rows: list[dict[str, Any]], expected_digest: str, stable_json: Callable[[Any], str]
) -> dict[str, int]:
    """Check canonical row hashes, entity keys, AV boundaries and overall digest."""
    grouped: dict[str, list[tuple[tuple[int, ...], str, str, dict[str, Any]]]] = {
        kind: [] for kind in _KEYS
    }
    seen: set[tuple[str, str]] = set()
    for row in rows:
        kind, key = row["row_kind"], row["entity_key"]
        if kind not in _KEYS or (kind, key) in seen:
            raise ImportErrorSafe("Snapshot has an unknown kind or a duplicate entity")
        seen.add((kind, key))
        payload = row["payload_json"]
        if isinstance(payload, (str, bytes, bytearray)):
            try:
                payload = json.loads(payload)
            except (ValueError, UnicodeError) as exc:
                raise ImportErrorSafe("Snapshot payload is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ImportErrorSafe("Snapshot payload must be a JSON object")
        values = tuple(payload.get(field) for field in _KEYS[kind])
        if any(type(value) is not int or value <= 0 for value in values):
            raise ImportErrorSafe("Snapshot entity IDs must be positive integers")
        if key != ":".join(str(value) for value in values):
            raise ImportErrorSafe("Snapshot entity key does not match its payload IDs")
        row_hash = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
        if row_hash != row["row_sha256"]:
            raise ImportErrorSafe(f"Snapshot row hash mismatch: {kind}:{key}")
        if kind == "job" and payload.get("av_relevant") not in (True, 1):
            raise ImportErrorSafe("Frozen job snapshot contains a non-AV job")
        if kind == "cluster" and payload.get("population") != "av_relevant":
            raise ImportErrorSafe("Frozen cluster snapshot contains a non-AV cluster")
        grouped[kind].append((values, key, row_hash, payload))

    jobs = {values[0]: payload for values, _, _, payload in grouped["job"]}
    if not jobs:
        raise ImportErrorSafe("Frozen snapshot has no AV jobs")
    for values, _, _, payload in grouped["job_skill"]:
        job = jobs.get(values[0])
        if job is None or payload.get("source_key") != job.get("source_key"):
            raise ImportErrorSafe("Frozen skill references a missing or different job")

    digest = hashlib.sha256()
    # Publication orders each kind by its numeric IDs, not SQL text-key order.
    for kind, entries in grouped.items():
        for _, key, row_hash, _ in sorted(entries, key=lambda entry: entry[0]):
            digest.update(f"{kind}:{key}:{row_hash}\n".encode("utf-8"))
    if digest.hexdigest() != expected_digest:
        raise ImportErrorSafe("Frozen snapshot aggregate hash mismatch")
    return {
        **{kind: len(entries) for kind, entries in grouped.items()},
        "skilled_jobs": len({values[0] for values, _, _, _ in grouped["job_skill"]}),
    }


def verify_frozen_snapshot(
    engine: Any, connection: Any, release: dict[str, Any]
) -> dict[str, int]:
    if not release.get("snapshot_frozen_at") or not release.get("snapshot_sha256"):
        raise ImportErrorSafe("Release does not have a complete frozen snapshot")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT row_kind,entity_key,payload_json,row_sha256 "
            "FROM dashboard_release_snapshot_rows WHERE dashboard_release_id=%s",
            (release["dashboard_release_id"],),
        )
        rows = list(cursor.fetchall())
    return check_snapshot_rows(rows, release["snapshot_sha256"], engine.stable_json)
