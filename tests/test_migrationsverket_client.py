"""Live smoke tests against the real migrationsverket.se pages in
GUIDANCE_PAGES. Deselected by default (`pytest -m "not live"`) — this is
what makes claims like "verified end-to-end against the real page"
reproducible rather than resting on an ad-hoc, uncommitted run.
"""

from __future__ import annotations

import datetime as dt

import pytest

from vistas.retrieval import search
from vistas.sources.migrationsverket import (
    GUIDANCE_PAGES,
    MigrationsverketClient,
    parse_guidance_page,
)
from vistas.store import Store


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
def test_all_p0_pages_fetch_and_parse_with_real_content() -> None:
    """Every page in GUIDANCE_PAGES (the plan §1 target visa-question set)
    must still yield real content — catches a page moving/changing layout
    silently, not just the one seed page test_fetch_and_parse_seed_page
    already covers in more depth.

    Also pins down that each page's <main> has exactly one <h1> (verified
    2026-07-19 across all 8 current pages): _HEADING_RE was widened to
    treat h1 as a section-opening heading too, so it captures lead
    paragraphs before the first h2/h3 (see TestIntroContent in
    test_migrationsverket.py). A page with a second, non-content h1 (e.g.
    breadcrumb markup not stripped by the script/style/nav/footer noise
    filter) would silently split that intro text across two headings
    instead of raising — this canary is what would actually notice.
    """
    from bs4 import BeautifulSoup

    client = MigrationsverketClient()
    for url, area in GUIDANCE_PAGES.items():
        result = client.fetch_page(url)
        assert result.not_modified is False, url
        assert result.text is not None, url

        soup = BeautifulSoup(result.text, "html.parser")
        main = soup.find("main") or soup
        for noise in main.select("script, style, nav, footer"):
            noise.decompose()
        assert len(main.find_all("h1")) == 1, f"unexpected h1 count on {url}"

        page = parse_guidance_page(result.text, url, area=area)
        assert len(page.chunks) > 0, f"parsed 0 chunks for {url}"
        assert all(c.area == area for c in page.chunks)


@pytest.mark.live
def test_heading_phrased_query_finds_real_content(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Closes the loop on the store._fts_text fix: a query phrased like the
    real 'students who have found work' guidance heading must find it, even
    though the body prose never repeats the word 'found' (verified 2026-07-19
    — this exact case is why the heading text was added to the FTS index).
    """
    client = MigrationsverketClient()
    url = next(u for u, a in GUIDANCE_PAGES.items() if a == "work_permit" and "found-work" in u)
    result = client.fetch_page(url)
    assert result.text is not None
    page = parse_guidance_page(result.text, url, area="work_permit")

    store = Store.open(tmp_path / "t.db")
    store.ingest(url, page.chunks, observed=dt.date.today())
    hits = search(store, query="students found work")
    assert hits
    store.close()


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
