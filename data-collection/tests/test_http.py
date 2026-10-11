import io
import urllib.error

import pytest

import av_jobs.http as http_module
from av_jobs.http import HttpRequestError, get_json, get_text


class FakeHeaders:
    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body
        self.headers = FakeHeaders()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def disable_retry_delay(monkeypatch):
    monkeypatch.setattr(http_module.time, "sleep", lambda _seconds: None)


def test_get_text_retries_a_timeout_and_then_succeeds(monkeypatch):
    """A temporary timeout should be retried without failing the source."""
    disable_retry_delay(monkeypatch)
    outcomes = iter(
        [
            TimeoutError("temporary timeout"),
            TimeoutError("temporary timeout"),
            FakeResponse(b"<html>jobs</html>"),
        ]
    )
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        outcome = next(outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fake_urlopen)

    assert get_text("https://example.com/jobs") == "<html>jobs</html>"
    assert calls == [("https://example.com/jobs", 30)] * 3


def test_get_json_retries_a_temporary_http_error(monkeypatch):
    """A temporary server error should be retried, then decoded normally."""
    disable_retry_delay(monkeypatch)
    outcomes = iter(
        [
            urllib.error.HTTPError(
                "https://example.com/jobs",
                503,
                "Service Unavailable",
                {},
                io.BytesIO(),
            ),
            FakeResponse(b'{"jobs": [1]}'),
        ]
    )

    def fake_urlopen(_request, timeout):
        del timeout
        outcome = next(outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fake_urlopen)

    assert get_json("https://example.com/jobs") == {"jobs": [1]}


def test_non_retryable_http_error_fails_immediately(monkeypatch):
    """A permanent error such as HTTP 404 must not be requested three times."""
    disable_retry_delay(monkeypatch)
    calls = 0

    def fake_urlopen(_request, timeout):
        del timeout
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError(
            "https://example.com/missing",
            404,
            "Not Found",
            {},
            io.BytesIO(),
        )

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(HttpRequestError, match="returned HTTP 404"):
        get_text("https://example.com/missing")

    assert calls == 1


def test_repeated_timeout_fails_after_three_attempts(monkeypatch):
    """A source should report failure after the bounded retry limit."""
    disable_retry_delay(monkeypatch)
    calls = 0

    def fake_urlopen(_request, timeout):
        del timeout
        nonlocal calls
        calls += 1
        raise TimeoutError("read timed out")

    monkeypatch.setattr(http_module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(HttpRequestError, match="failed after 3 attempts"):
        get_text("https://example.com/slow")

    assert calls == 3
