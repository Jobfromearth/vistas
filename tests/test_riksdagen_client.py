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
def test_conditional_refetch_returns_304() -> None:
    client = RiksdagenClient()
    first = client.fetch_sfs_text("2005:716")
    assert first.etag is not None
    second = client.fetch_sfs_text("2005:716", etag=first.etag)
    assert second.not_modified is True
    assert second.text is None
