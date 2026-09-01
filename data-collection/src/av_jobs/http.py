from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "AVJobPipeline/0.1 (+public job-board collector)",
}


class HttpRequestError(RuntimeError):
    """Raised when a public job-board request fails."""


def get_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers=DEFAULT_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise HttpRequestError(f"GET {url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise HttpRequestError(f"GET {url} failed: {exc.reason}") from exc

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpRequestError(f"GET {url} did not return valid UTF-8 JSON") from exc
