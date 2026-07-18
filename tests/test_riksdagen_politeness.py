"""Crawl etiquette (plan §2.2): ≤1 req/sec self-throttling and conditional
requests (ETag/Last-Modified) so unchanged sources aren't re-downloaded.
"""

from __future__ import annotations

import time

import httpx
import pytest

from vistas.sources.riksdagen import RiksdagenClient


def _client(handler):  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    return RiksdagenClient(http=httpx.Client(transport=transport))


class TestRateLimit:
    def test_second_request_is_throttled(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="ok")

        client = _client(handler)
        client._min_interval = 0.2  # keep the test fast
        start = time.monotonic()
        client.fetch_sfs_text("2005:716")
        client.fetch_sfs_text("2005:716")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.2


class TestConditionalRequests:
    def test_sends_known_etag_and_skips_reparse_on_304(self) -> None:
        seen_headers: list[httpx.Headers] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_headers.append(request.headers)
            return httpx.Response(304)

        client = _client(handler)
        result = client.fetch_sfs_text("2005:716", etag='"abc123"')
        assert seen_headers[0].get("if-none-match") == '"abc123"'
        assert result.not_modified is True
        assert result.text is None

    def test_response_carries_new_etag_for_next_run(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="lag text", headers={"ETag": '"new-etag"'})

        client = _client(handler)
        result = client.fetch_sfs_text("2005:716")
        assert result.not_modified is False
        assert result.text == "lag text"
        assert result.etag == '"new-etag"'

    @pytest.mark.parametrize("etag", [None])
    def test_no_etag_sends_plain_request(self, etag: str | None) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "if-none-match" not in request.headers
            return httpx.Response(200, text="ok")

        client = _client(handler)
        client.fetch_sfs_text("2005:716", etag=etag)
