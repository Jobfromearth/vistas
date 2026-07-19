"""PoliteClient retry-on-transient-failure.

Discovered via real Migrationsverket flakiness while running the QA-set
eval (2026-07-19): identical code succeeded 3/3 runs, then failed 2/2 with
httpx.RemoteProtocolError("Server disconnected without sending a
response.") — real, intermittent server-side flakiness, not a client bug,
confirmed by retrying outside pytest with no code changes. Cheap and worth
retrying for, since the daily pipeline shouldn't fail an entire build over
one dropped connection.
"""

from __future__ import annotations

import httpx
import pytest

from vistas.sources.common import PoliteClient


def _client(handler):  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    client = PoliteClient("test-agent/1", http=httpx.Client(transport=transport))
    client._min_interval = 0.0
    client._retry_backoff = 0.0
    return client


class TestRetry:
    def test_retries_transient_failure_then_succeeds(self) -> None:
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
            return httpx.Response(200, text="ok", headers={"ETag": '"v1"'})

        client = _client(handler)
        result = client._fetch("https://example.com/page")
        assert result.text == "ok"
        assert attempts["n"] == 3

    def test_gives_up_after_max_retries(self) -> None:
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

        client = _client(handler)
        with pytest.raises(httpx.RemoteProtocolError):
            client._fetch("https://example.com/page")
        assert attempts["n"] == client._max_retries + 1

    def test_http_status_errors_are_not_retried(self) -> None:
        """A real 500/404 is not a transient connection problem — retrying
        it wastes requests against a server that already gave a definite
        answer."""
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            return httpx.Response(500)

        client = _client(handler)
        with pytest.raises(httpx.HTTPStatusError):
            client._fetch("https://example.com/page")
        assert attempts["n"] == 1

    def test_retry_still_throttles_each_attempt(self) -> None:
        import time

        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 2:
                raise httpx.RemoteProtocolError("Server disconnected without sending a response.")
            return httpx.Response(200, text="ok")

        client = _client(handler)
        client._min_interval = 0.15
        start = time.monotonic()
        client._fetch("https://example.com/page")
        assert time.monotonic() - start >= 0.15
