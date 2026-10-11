from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "AVJobPipeline/0.1 (+public job-board collector)",
}

HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "User-Agent": "AVJobPipeline/0.1 (+public job-board collector)",
}

REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1
RETRYABLE_HTTP_STATUS = {408, 429, 500, 502, 503, 504}


class HttpRequestError(RuntimeError):
    """Raised when a public job-board request fails."""


def _request_bytes(
    request: urllib.request.Request,
    *,
    timeout: int,
) -> tuple[bytes, str | None]:
    """Read a public URL, retrying only temporary request failures."""
    last_error: BaseException | None = None

    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                charset = response.headers.get_content_charset()
                return body, charset
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_HTTP_STATUS or attempt == REQUEST_ATTEMPTS:
                raise HttpRequestError(
                    f"{request.method} {request.full_url} returned HTTP {exc.code}"
                ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == REQUEST_ATTEMPTS:
                reason = getattr(exc, "reason", exc)
                raise HttpRequestError(
                    f"{request.method} {request.full_url} failed after "
                    f"{REQUEST_ATTEMPTS} attempts: {reason}"
                ) from exc

        # A short increasing delay avoids immediately repeating the same failure.
        time.sleep(RETRY_DELAY_SECONDS * attempt)

    raise HttpRequestError(
        f"{request.method} {request.full_url} failed: {last_error}"
    )


def get_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(url, headers=DEFAULT_HEADERS, method="GET")
    body, _charset = _request_bytes(request, timeout=timeout)

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpRequestError(f"GET {url} did not return valid UTF-8 JSON") from exc


def get_text(url: str, timeout: int = 30) -> str:
    """Get a public web page as text."""
    request = urllib.request.Request(url, headers=HTML_HEADERS, method="GET")
    body, response_charset = _request_bytes(request, timeout=timeout)
    charset = response_charset or "utf-8"

    try:
        return body.decode(charset)
    except (LookupError, UnicodeDecodeError) as exc:
        raise HttpRequestError(f"GET {url} did not return readable text") from exc


def post_form_json(url: str, data: dict[str, Any], timeout: int = 30) -> Any:
    """Send a public form request and read its JSON response."""
    body = urllib.parse.urlencode(data).encode("utf-8")
    headers = {
        **DEFAULT_HEADERS,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    response_body, _charset = _request_bytes(request, timeout=timeout)

    try:
        return json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpRequestError(f"POST {url} did not return valid UTF-8 JSON") from exc
