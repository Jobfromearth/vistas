"""Live smoke test against the real Riksdagen API. Deselected by default
(`pytest -m "not live"`) so CI and offline dev don't depend on the network.
"""

from __future__ import annotations

import pytest

from vistas.sources.riksdagen import RiksdagenClient, parse_sfs_text


@pytest.mark.live
def test_fetch_and_parse_utlanningslagen() -> None:
    client = RiksdagenClient()
    result = client.fetch_sfs_text("2005:716")
    assert result.not_modified is False
    assert result.text is not None
    law = parse_sfs_text(result.text)
    assert law.sfs_nr == "2005:716"
    assert len(law.chunks) > 100
    assert any(c.area == "work_permit" for c in law.chunks)


@pytest.mark.live
def test_no_etag_from_server_means_every_run_refetches() -> None:
    """As of 2026-07-19, data.riksdagen.se sends no ETag/Last-Modified for
    this endpoint (verified via a direct HEAD request) — despite an earlier
    check in this project appearing to show 304 behavior, which on closer
    look was actually store.ingest's content-diff reporting "no changes",
    not an HTTP-level 304. Conditional caching degrades to "always
    refetch," correct if bandwidth-wasteful; this test pins down the
    current reality so a real regression (or the server adding ETag
    support) gets noticed rather than assumed."""
    client = RiksdagenClient()
    result = client.fetch_sfs_text("2005:716")
    assert result.not_modified is False
    assert result.etag is None
