"""Version-chain correctness — the CI-gate seam from plan §6.

Simulated rule changes must produce: diff detection, correct open/close of
observed windows, intact supersedes chains, and never a deleted old version.
"""

from __future__ import annotations

import datetime as dt

import pytest

from vistas.model import Anchor, ObservedChunk, SourceType
from vistas.store import Store

D1 = dt.date(2026, 7, 1)
D2 = dt.date(2026, 7, 8)
D3 = dt.date(2026, 7, 15)

ANCHOR = Anchor(SourceType.LEGAL, "sfs-2005:716", chapter="5", paragraph="5")


def chunk(content: str, chunk_id: str = "sfs-2005:716/5/5/sv") -> ObservedChunk:
    return ObservedChunk(
        chunk_id=chunk_id,
        content=content,
        language="sv",
        anchor=ANCHOR,
        source_url="https://data.riksdagen.se/dokument/sfs-2005-716",
        area="work_permit",
    )


@pytest.fixture
def store(tmp_path) -> Store:  # type: ignore[no-untyped-def]
    return Store.open(tmp_path / "test.db")


class TestIngest:
    def test_first_observation_opens_window(self, store: Store) -> None:
        report = store.ingest("sfs-2005:716", [chunk("Lön minst 27 360 kr.")], observed=D1)
        assert report.added == 1 and report.changed == 0 and report.removed == 0
        [v] = store.current_versions()
        assert v.observed_from == D1
        assert v.observed_to is None
        assert v.supersedes is None

    def test_unchanged_content_is_a_noop(self, store: Store) -> None:
        store.ingest("sfs-2005:716", [chunk("Lön minst 27 360 kr.")], observed=D1)
        report = store.ingest("sfs-2005:716", [chunk("Lön minst 27 360 kr.")], observed=D2)
        assert report.added == report.changed == report.removed == 0
        [v] = store.current_versions()
        assert v.observed_from == D1  # window extends, no new version

    def test_changed_content_closes_old_and_links_chain(self, store: Store) -> None:
        store.ingest("sfs-2005:716", [chunk("Lön minst 27 360 kr.")], observed=D1)
        report = store.ingest("sfs-2005:716", [chunk("Lön minst 28 480 kr.")], observed=D2)
        assert report.changed == 1

        [current] = store.current_versions()
        assert current.chunk.content == "Lön minst 28 480 kr."
        assert current.observed_from == D2

        old = store.get_version(current.supersedes)  # type: ignore[arg-type]
        assert old is not None, "old versions must never be deleted"
        assert old.chunk.content == "Lön minst 27 360 kr."
        assert old.observed_to == D2  # window closed exactly at change observation

    def test_removed_chunk_closes_window_without_successor(self, store: Store) -> None:
        store.ingest("sfs-2005:716", [chunk("A"), chunk("B", "sfs-2005:716/5/6/sv")], observed=D1)
        report = store.ingest("sfs-2005:716", [chunk("A")], observed=D2)
        assert report.removed == 1
        assert len(store.current_versions()) == 1

    def test_removal_scoped_to_document(self, store: Store) -> None:
        """A crawl of one document must not close chunks of another."""
        store.ingest("sfs-2005:716", [chunk("A")], observed=D1)
        other = ObservedChunk(
            chunk_id="guid/x/sv",
            content="Guidance text",
            language="sv",
            anchor=Anchor(SourceType.GUIDANCE, "https://mv.se/x", section="Krav"),
            source_url="https://mv.se/x",
        )
        store.ingest("https://mv.se/x", [other], observed=D1)
        store.ingest("sfs-2005:716", [chunk("A")], observed=D2)
        assert len(store.current_versions()) == 2

    def test_three_version_chain_is_walkable(self, store: Store) -> None:
        store.ingest("sfs-2005:716", [chunk("v1")], observed=D1)
        store.ingest("sfs-2005:716", [chunk("v2")], observed=D2)
        store.ingest("sfs-2005:716", [chunk("v3")], observed=D3)

        timeline = store.timeline("sfs-2005:716/5/5/sv")
        assert [v.chunk.content for v in timeline] == ["v1", "v2", "v3"]
        assert [v.observed_to for v in timeline] == [D2, D3, None]
        assert timeline[1].supersedes == timeline[0].version_id
        assert timeline[2].supersedes == timeline[1].version_id


class TestTimeAxes:
    def test_valid_from_never_faked_from_observation(self, store: Store) -> None:
        """ADR-0002: legal axis stays empty unless the source provided it."""
        store.ingest("sfs-2005:716", [chunk("text")], observed=D1)
        [v] = store.current_versions()
        assert v.chunk.valid_from is None
        assert v.observed_from == D1

    def test_extracted_valid_from_is_stored(self, store: Store) -> None:
        c = ObservedChunk(
            chunk_id="sfs-2005:716/6/2/sv",
            content="text",
            language="sv",
            anchor=Anchor(SourceType.LEGAL, "sfs-2005:716", chapter="6", paragraph="2"),
            source_url="https://data.riksdagen.se/dokument/sfs-2005-716",
            valid_from=dt.date(2023, 11, 1),
            amended_by="2023:648",
        )
        store.ingest("sfs-2005:716", [c], observed=D1)
        [v] = store.current_versions()
        assert v.chunk.valid_from == dt.date(2023, 11, 1)
        assert v.chunk.amended_by == "2023:648"


class TestChanges:
    def test_recent_changes_reports_all_kinds(self, store: Store) -> None:
        store.ingest("sfs-2005:716", [chunk("A"), chunk("B", "sfs-2005:716/5/6/sv")], observed=D1)
        store.ingest("sfs-2005:716", [chunk("A2"), chunk("C", "sfs-2005:716/5/7/sv")], observed=D2)

        changes = store.recent_changes(since=D2)
        kinds = {(c.chunk_id, c.kind) for c in changes}
        assert kinds == {
            ("sfs-2005:716/5/5/sv", "changed"),
            ("sfs-2005:716/5/7/sv", "added"),
            ("sfs-2005:716/5/6/sv", "removed"),
        }

    def test_recent_changes_filters_by_area(self, store: Store) -> None:
        store.ingest("sfs-2005:716", [chunk("A")], observed=D2)
        assert store.recent_changes(since=D1, area="work_permit")
        assert not store.recent_changes(since=D1, area="study")
