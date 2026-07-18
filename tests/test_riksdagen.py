"""SFS text parsing: § chunking, layered anchors, legal-axis extraction.

Citation accuracy is a CI gate (plan §6): anchors must point at real
kapitel/paragraf, and the legal validity axis is filled only from explicit
markers in the source text (ADR-0002), never inferred.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from vistas.model import SourceType
from vistas.sources.riksdagen import parse_sfs_text

FIXTURE = Path(__file__).parent / "fixtures" / "sfs_sample.txt"


@pytest.fixture(scope="module")
def law():  # type: ignore[no-untyped-def]
    return parse_sfs_text(FIXTURE.read_text(encoding="utf-8"))


class TestDocumentMetadata:
    def test_sfs_number_and_title(self, law) -> None:  # type: ignore[no-untyped-def]
        assert law.sfs_nr == "2005:716"
        assert law.title == "Utlänningslag (2005:716)"


class TestChunking:
    def test_all_paragraphs_found(self, law) -> None:  # type: ignore[no-untyped-def]
        ids = [c.chunk_id for c in law.chunks]
        assert "sfs-2005:716/1/1/sv" in ids  # current 1 kap. 1 §
        assert "sfs-2005:716/1/1@2026-07-12/sv" in ids  # pending version
        assert "sfs-2005:716/1/1 a/sv" in ids
        assert "sfs-2005:716/1/2/sv" in ids
        assert "sfs-2005:716/1/3/sv" in ids
        assert "sfs-2005:716/6/1/sv" in ids
        assert "sfs-2005:716/6/2/sv" in ids
        assert "sfs-2005:716/6 a/1/sv" in ids
        assert "sfs-2005:716/2/1/sv" in ids  # expiring chapter version
        assert "sfs-2005:716/2@2026-07-12/1/sv" in ids  # incoming chapter version
        assert "sfs-2005:716/4/1/sv" in ids  # /Kapitlet upphör .../
        assert "sfs-2005:716/4@2026-07-12/1/sv" in ids  # /Kapitlet träder .../
        assert "sfs-2005:716/4@2026-07-12/5@pending/sv" in ids  # date not yet set
        assert len(ids) == len(set(ids)) == 13

    def test_wrapped_reference_is_not_a_heading(self, law) -> None:  # type: ignore[no-untyped-def]
        """'6 kap. 2 § andra stycket' at line start inside 1 kap. 3 § must not
        open a chapter or paragraph."""
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/1/3/sv")
        assert "hamnar i början av en rad" in c.content

    def test_anchor_is_paragraph_level(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/6/2/sv")
        assert c.anchor.source_type is SourceType.LEGAL
        assert c.anchor.canonical() == "sfs-2005:716 kap.6 §2"
        assert c.anchor.level == "paragraph"

    def test_content_excludes_marker_and_keeps_text(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/6/2/sv")
        assert c.content.startswith("Arbetstillstånd enligt 1 §")
        assert "kollektivavtal" in c.content


class TestLegalAxis:
    def test_expiry_marker_sets_valid_to(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/1/1/sv")
        assert c.valid_to == dt.date(2026, 7, 12)
        assert c.valid_from is None

    def test_entry_into_force_marker_sets_valid_from(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/1/1@2026-07-12/sv")
        assert c.valid_from == dt.date(2026, 7, 12)

    def test_no_marker_means_no_legal_dates(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/1/2/sv")
        assert c.valid_from is None and c.valid_to is None

    def test_amendment_reference_extracted(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/6/2/sv")
        assert c.amended_by == "2022:303"

    def test_chapter_level_markers_propagate_to_paragraphs(self, law) -> None:  # type: ignore[no-untyped-def]
        """/Rubriken upphör|träder .../ before a chapter heading versions the
        whole chapter: expiring §§ get valid_to, incoming §§ get valid_from."""
        old = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/2/1/sv")
        new = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/2@2026-07-12/1/sv")
        assert old.valid_to == dt.date(2026, 7, 12)
        assert new.valid_from == dt.date(2026, 7, 12)
        assert "främlingspass" in new.content
        assert "främlingspass" not in old.content

    def test_rubrik_marker_not_glued_into_content(self, law) -> None:  # type: ignore[no-untyped-def]
        c = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/6 a/1/sv")
        assert "Rubriken" not in c.content

    def test_kapitlet_markers_version_whole_chapter(self, law) -> None:  # type: ignore[no-untyped-def]
        old = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/4/1/sv")
        new = next(c for c in law.chunks if c.chunk_id == "sfs-2005:716/4@2026-07-12/1/sv")
        assert old.valid_to == dt.date(2026, 7, 12)
        assert new.valid_from == dt.date(2026, 7, 12)

    def test_undated_entry_into_force_gets_pending_suffix(self, law) -> None:  # type: ignore[no-untyped-def]
        """'I:den dag som regeringen bestämmer' — pending version, date unknown:
        no legal date is faked, identity stays distinct."""
        c = next(c for c in law.chunks if "5@pending" in c.chunk_id)
        assert c.valid_from is None
        assert "ytterligare föreskrifter" in c.content


class TestAreaTagging:
    def test_chapter_area_map(self, law) -> None:  # type: ignore[no-untyped-def]
        by_id = {c.chunk_id: c for c in law.chunks}
        assert by_id["sfs-2005:716/6/2/sv"].area == "work_permit"
        assert by_id["sfs-2005:716/6 a/1/sv"].area == "eu_blue_card"
        assert by_id["sfs-2005:716/1/2/sv"].area is None
