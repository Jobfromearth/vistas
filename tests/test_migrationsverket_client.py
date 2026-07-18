"""Live smoke test against the real migrationsverket.se seed page. Deselected
by default (`pytest -m "not live"`) — this is what makes the plan doc's
"verified end-to-end against the real page" claim reproducible rather than
resting on an ad-hoc, uncommitted run.
"""

from __future__ import annotations

import pytest

from vistas.sources.migrationsverket import (
    GUIDANCE_PAGES,
    MigrationsverketClient,
    parse_guidance_page,
)


@pytest.mark.live
def test_fetch_and_parse_seed_page() -> None:
    url, area = next(iter(GUIDANCE_PAGES.items()))
    client = MigrationsverketClient()
    result = client.fetch_page(url)
    assert result.not_modified is False
    assert result.text is not None

    page = parse_guidance_page(result.text, url, area=area)
    assert len(page.chunks) > 20  # the real page has dozens of substantive sections
    assert all(c.area == area for c in page.chunks)
    assert any("salary" in c.content.lower() or "lön" in c.content.lower() for c in page.chunks)


@pytest.mark.live
def test_no_etag_from_server_means_every_run_refetches() -> None:
    """migrationsverket.se (unlike data.riksdagen.se) sends no ETag or
    Last-Modified for this page — verified via a direct HEAD request
    2026-07-18. Conditional caching degrades to "always refetch," which is
    correct (if bandwidth-wasteful) rather than broken; this test pins that
    down so a future silent change either way — the site adding ETag support,
    or our client silently breaking — gets noticed."""
    url = next(iter(GUIDANCE_PAGES))
    client = MigrationsverketClient()
    result = client.fetch_page(url)
    assert result.not_modified is False
    assert result.etag is None
