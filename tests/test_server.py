"""Server wiring: the four tools are actually registered on the MCP protocol
layer, carry the boundary declaration, and a real call round-trips correctly.
Business logic itself is covered by test_tools.py against the pure functions.
"""

from __future__ import annotations

import datetime as dt
import json

import pytest

from vistas.model import Anchor, ObservedChunk, SourceType
from vistas.server import build_server
from vistas.store import Store


@pytest.fixture
def store(tmp_path):  # type: ignore[no-untyped-def]
    s = Store.open(tmp_path / "t.db")
    s.ingest(
        "sfs-2005:716",
        [
            ObservedChunk(
                chunk_id="sfs-2005:716/6/2/sv",
                content="Lönen ska minst uppgå till kollektivavtalsenlig nivå.",
                language="sv",
                anchor=Anchor(SourceType.LEGAL, "sfs-2005:716", chapter="6", paragraph="2"),
                source_url="https://data.riksdagen.se/dokument/sfs-2005-716",
                area="work_permit",
            )
        ],
        observed=dt.date(2026, 7, 1),
    )
    return s


@pytest.mark.anyio
async def test_all_four_tools_registered_with_boundary(store: Store) -> None:
    server = build_server(store)
    registered = await server.list_tools()
    names = {t.name for t in registered}
    assert names == {"search_rules", "rule_timeline", "recent_changes", "get_source"}
    for t in registered:
        assert "not legal advice" in (t.description or "").lower()


@pytest.mark.anyio
async def test_search_rules_round_trip_returns_structured_payload(store: Store) -> None:
    server = build_server(store)
    result = await server.call_tool("search_rules", {"query": "kollektivavtal"})
    payload = _unwrap(result)
    assert payload["status"] == "ok"
    assert payload["results"][0]["anchor"] == "sfs-2005:716 kap.6 §2"


@pytest.mark.anyio
async def test_unknown_chunk_round_trip_is_no_data(store: Store) -> None:
    server = build_server(store)
    result = await server.call_tool("rule_timeline", {"chunk_id": "sfs-9999:1/1/1/sv"})
    assert _unwrap(result)["status"] == "no_data"


def _unwrap(result: object) -> dict:  # type: ignore[type-arg]
    """call_tool returns either a dict directly or (content_blocks, dict)."""
    if isinstance(result, tuple):
        _, structured = result
        return structured  # type: ignore[no-any-return]
    if isinstance(result, dict):
        return result
    text = result[0].text  # type: ignore[index, union-attr]
    return json.loads(text)  # type: ignore[no-any-return]
