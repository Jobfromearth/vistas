"""MCP tool logic (protocol-agnostic layer under vistas.server).

Plan §3.6 / §4.1: every result is structured (content + layered anchor +
official link + dual time axis + snapshot build time), never free generation;
no hits returns an explicit "no_data" status rather than padding.
"""

from __future__ import annotations

import datetime as dt

import pytest

from vistas.model import Anchor, ObservedChunk, SourceType
from vistas.store import Store
from vistas.tools import get_source, recent_changes, rule_timeline, search_rules

D1 = dt.date(2026, 7, 1)
D2 = dt.date(2026, 8, 1)


def legal(chunk_id: str, chapter: str, paragraph: str, content: str, area: str) -> ObservedChunk:
    return ObservedChunk(
        chunk_id=chunk_id,
        content=content,
        language="sv",
        anchor=Anchor(SourceType.LEGAL, "sfs-2005:716", chapter=chapter, paragraph=paragraph),
        source_url="https://data.riksdagen.se/dokument/sfs-2005-716",
        area=area,
        valid_from=dt.date(2023, 11, 1) if chunk_id.endswith("6/2/sv") else None,
    )


def guidance(chunk_id: str, section: str, content: str) -> ObservedChunk:
    return ObservedChunk(
        chunk_id=chunk_id,
        content=content,
        language="sv",
        anchor=Anchor(SourceType.GUIDANCE, "https://mv.se/arbetstillstand", section=section),
        source_url="https://mv.se/arbetstillstand",
        area="work_permit",
    )


@pytest.fixture
def store(tmp_path) -> Store:  # type: ignore[no-untyped-def]
    s = Store.open(tmp_path / "t.db")
    s.set_meta("built_at", "2026-07-18T00:00:00Z")
    s.ingest(
        "sfs-2005:716",
        [
            legal(
                "sfs-2005:716/6/1/sv", "6", "1",
                "Arbetstillstånd ska ges för viss tid.", "work_permit",
            ),
            legal(
                "sfs-2005:716/6/2/sv", "6", "2",
                "Lönen ska minst uppgå till kollektivavtalsenlig nivå.", "work_permit",
            ),
        ],
        observed=D1,
    )
    s.ingest(
        "https://mv.se/arbetstillstand",
        [guidance("guid/arbetstillstand/krav/sv", "Krav", "Du behöver ett jobberbjudande.")],
        observed=D1,
    )
    return s


class TestSearchRules:
    def test_hit_carries_layered_anchor_and_dual_axis(self, store: Store) -> None:
        result = search_rules(store, "kollektivavtal")
        assert result["status"] == "ok"
        hit = result["results"][0]
        assert hit["anchor"] == "sfs-2005:716 kap.6 §2"
        assert hit["anchor_level"] == "paragraph"
        assert hit["source_url"] == "https://data.riksdagen.se/dokument/sfs-2005-716"
        assert hit["observed_from"] == "2026-07-01"
        assert hit["valid_from"] == "2023-11-01"
        assert result["snapshot_built_at"] == "2026-07-18T00:00:00Z"

    def test_guidance_hit_has_section_level_anchor(self, store: Store) -> None:
        result = search_rules(store, "jobberbjudande")
        hit = result["results"][0]
        assert hit["anchor"] == "https://mv.se/arbetstillstand#Krav"
        assert hit["anchor_level"] == "section"

    def test_no_hits_is_explicit_no_data(self, store: Store) -> None:
        result = search_rules(store, "skatteverket sink")
        assert result == {"status": "no_data", "query": "skatteverket sink"}


class TestRuleTimeline:
    def test_unknown_chunk_is_no_data(self, store: Store) -> None:
        assert rule_timeline(store, "sfs-2005:716/9/9/sv")["status"] == "no_data"

    def test_known_chunk_returns_version_list(self, store: Store) -> None:
        store.ingest(
            "sfs-2005:716",
            [legal("sfs-2005:716/6/1/sv", "6", "1", "Ny lydelse.", "work_permit")],
            observed=D2,
        )
        result = rule_timeline(store, "sfs-2005:716/6/1/sv")
        assert result["status"] == "ok"
        assert len(result["versions"]) == 2
        assert result["versions"][0]["observed_to"] == "2026-08-01"
        assert result["versions"][1]["observed_to"] is None


class TestRecentChanges:
    def test_since_filters_and_reports_kind(self, store: Store) -> None:
        result = recent_changes(store, since="2026-06-01")
        assert result["status"] == "ok"
        assert {c["kind"] for c in result["changes"]} == {"added"}

    def test_far_future_since_is_no_data(self, store: Store) -> None:
        result = recent_changes(store, since="2099-01-01")
        assert result["status"] == "no_data"


class TestGetSource:
    def test_legal_anchor_returns_whole_chapter(self, store: Store) -> None:
        result = get_source(store, "sfs-2005:716 kap.6 §2")
        assert result["status"] == "ok"
        ids = {s["chunk_id"] for s in result["sections"]}
        assert ids == {"sfs-2005:716/6/1/sv", "sfs-2005:716/6/2/sv"}

    def test_guidance_anchor_returns_whole_page(self, store: Store) -> None:
        result = get_source(store, "https://mv.se/arbetstillstand#Krav")
        assert result["status"] == "ok"
        assert len(result["sections"]) == 1

    def test_unknown_anchor_is_no_data(self, store: Store) -> None:
        result = get_source(store, "sfs-9999:1 kap.1 §1")
        assert result["status"] == "no_data"
