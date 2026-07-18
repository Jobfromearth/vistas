"""Retrieval correctness — the other CI-gate seam from plan §6.

ADR-0003: no embedding model. Cross-language reach comes from a Swedish/English
synonym table the caller's query is expanded against; FTS5/BM25 does the rest.
"""

from __future__ import annotations

import datetime as dt

import pytest

from vistas.model import Anchor, ObservedChunk, SourceType
from vistas.retrieval import build_match_query, search
from vistas.store import Store

D1 = dt.date(2026, 7, 1)


_PROFILES = {"work_permit": ("worker",), "study": ("student",), "put": ()}


def legal_chunk(
    chunk_id: str, chapter: str, paragraph: str, content: str, area: str
) -> ObservedChunk:
    return ObservedChunk(
        chunk_id=chunk_id,
        content=content,
        language="sv",
        anchor=Anchor(SourceType.LEGAL, "sfs-2005:716", chapter=chapter, paragraph=paragraph),
        source_url="https://data.riksdagen.se/dokument/sfs-2005-716",
        area=area,
        profiles=_PROFILES[area],
    )


@pytest.fixture
def store(tmp_path) -> Store:  # type: ignore[no-untyped-def]
    s = Store.open(tmp_path / "t.db")
    s.ingest(
        "sfs-2005:716",
        [
            legal_chunk(
                "sfs-2005:716/6/2/sv", "6", "2",
                "Arbetstillstånd i Sverige får ges till en utlänning som har ett "
                "anställningsavtal om lönen inte är sämre än kollektivavtal.",
                "work_permit",
            ),
            legal_chunk(
                "sfs-2005:716/5/6/sv", "5", "6",
                "Uppehållstillstånd i Sverige för studier på högskolenivå får ges till "
                "en student som är antagen till utbildning.",
                "study",
            ),
            legal_chunk(
                "sfs-2005:716/5 a/1/sv", "5 a", "1",
                "Ställning som varaktigt bosatt kräver fem års sammanhängande "
                "uppehållstillstånd i Sverige.",
                "put",
            ),
        ],
        observed=D1,
    )
    return s


class TestSynonymExpansion:
    def test_english_query_reaches_swedish_content(self, store: Store) -> None:
        hits = search(store, query="work permit salary", language=None)
        assert any(h.version.chunk.chunk_id == "sfs-2005:716/6/2/sv" for h in hits)

    def test_unmapped_term_still_searches_literally(self, store: Store) -> None:
        query = build_match_query("anställningsavtal")
        assert "anställningsavtal" in query

    def test_build_match_query_expands_known_terms(self) -> None:
        query = build_match_query("work permit")
        assert "arbetstillstånd" in query
        assert "OR" in query


class TestFiltering:
    def test_area_appropriate_results_only(self, store: Store) -> None:
        hits = search(store, query="uppehållstillstånd student")
        top_ids = {h.version.chunk.chunk_id for h in hits}
        assert "sfs-2005:716/5/6/sv" in top_ids

    def test_profile_filters_out_inapplicable_rules(self, store: Store) -> None:
        hits = search(store, query="sverige", profile="worker")
        ids = {h.version.chunk.chunk_id for h in hits}
        assert "sfs-2005:716/5/6/sv" not in ids  # tagged 'student', not 'worker'
        assert "sfs-2005:716/6/2/sv" in ids  # tagged 'worker'
        assert "sfs-2005:716/5 a/1/sv" in ids  # untagged: applies to everyone

    def test_as_of_date_reaches_historical_versions(self, store: Store) -> None:
        store.ingest(
            "sfs-2005:716",
            [
                legal_chunk(
                    "sfs-2005:716/6/2/sv", "6", "2", "Ny lydelse om arbetstillstånd.",
                    "work_permit",
                )
            ],
            observed=dt.date(2026, 8, 1),
        )
        current = search(store, query="arbetstillstånd")
        historical = search(store, query="arbetstillstånd", as_of=D1)
        assert "Ny lydelse" in current[0].version.chunk.content
        assert "kollektivavtal" in historical[0].version.chunk.content


class TestNoData:
    def test_no_hits_returns_empty_not_padded(self, store: Store) -> None:
        hits = search(store, query="skatteverket sink gränspendlare")
        assert hits == []


class TestHeadingIsSearchable:
    def test_query_matching_only_the_heading_still_finds_the_chunk(self, store: Store) -> None:
        """Regression: a guidance chunk's heading is often the most natural
        phrasing a user/agent would search with, but the body prose doesn't
        always repeat it — e.g. Migrationsverket's real "Students who have
        found work are exempt from the salary requirement" heading, whose
        body text never says "found". The heading itself must be searchable,
        not just the body content that gets displayed.
        """
        chunk = ObservedChunk(
            chunk_id="guid/mv/found-work/en",
            content="If you hold a residence permit as a student, you are exempt "
            "from the usual income threshold for your first application.",
            language="en",
            anchor=Anchor(
                SourceType.GUIDANCE,
                "https://mv.se/students-found-work",
                section="Students who have found work are exempt from the salary requirement",
            ),
            source_url="https://mv.se/students-found-work",
            area="work_permit",
        )
        store.ingest("https://mv.se/students-found-work", [chunk], observed=D1)
        hits = search(store, query="students found work")
        assert any(h.version.chunk.chunk_id == "guid/mv/found-work/en" for h in hits)
