"""Shared HTTP client plumbing for polite, conditional-request clients
against Swedish government sources (plan §2.2 crawl etiquette): self-
throttled to <= 1 request/second, with ETag-based conditional requests so
an unchanged source isn't re-downloaded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class FetchResult:
    """A fetch outcome: either fresh text with its new ETag, or 304 Not
    Modified (text is None — the caller should keep using its cached copy).
    """

    not_modified: bool
    text: str | None
    etag: str | None


class PoliteClient:
    """Base for source-specific clients (RiksdagenClient, MigrationsverketClient).
    Subclasses add their own URL construction on top of `_fetch`.
    """

    def __init__(self, user_agent: str, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(
            headers={"User-Agent": user_agent}, timeout=30.0, follow_redirects=True
        )
        self._min_interval = 1.0
        self._last_request: float | None = None

    def _throttle(self) -> None:
        if self._last_request is not None:
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
        self._last_request = time.monotonic()

    def _fetch(self, url: str, *, etag: str | None = None) -> FetchResult:
        self._throttle()
        headers = {"If-None-Match": etag} if etag else {}
        response = self._http.get(url, headers=headers)
        if response.status_code == 304:
            return FetchResult(not_modified=True, text=None, etag=etag)
        response.raise_for_status()
        return FetchResult(
            not_modified=False, text=response.text, etag=response.headers.get("ETag")
        )
