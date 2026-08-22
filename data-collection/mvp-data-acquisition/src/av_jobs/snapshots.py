"""Immutable raw-response snapshot persistence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from scrapy.http import Response


def write_response_snapshot(
    response: Response,
    *,
    data_root: Path,
    run_id: str,
    company: str,
    company_slug: str,
    source_name: str,
) -> Path:
    """Store an unmodified response and an auditable metadata sidecar."""

    content_type = response.headers.get("Content-Type", b"").decode(
        "latin-1", errors="ignore"
    )
    extension = "json" if "json" in content_type.lower() else "html"
    request_hash = hashlib.sha256(response.url.encode("utf-8")).hexdigest()[:16]
    path = (
        data_root
        / "raw"
        / f"run_id={run_id}"
        / f"company={company_slug}"
        / f"{source_name}-{request_hash}.{extension}"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.body)

    metadata = {
        "run_id": run_id,
        "company": company,
        "source_name": source_name,
        "url": response.url,
        "http_status": response.status,
        "content_type": content_type,
        "stored_at": datetime.now(UTC).isoformat(),
        "response_bytes": len(response.body),
        "response_sha256": hashlib.sha256(response.body).hexdigest(),
    }
    path.with_suffix(path.suffix + ".meta.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
