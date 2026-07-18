"""Pipeline build: fetch → parse → ingest → stamp snapshot metadata.

Network access is injected as a callable so this stays a fast, offline unit
test; the live client itself is covered by test_riksdagen_client.py.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from vistas.pipeline.build import build_snapshot
from vistas.sources.riksdagen import FetchResult
from vistas.store import Store

FIXTURE = (Path(__file__).parent / "fixtures" / "sfs_sample.txt").read_text(encoding="utf-8")


def _fixture_fetch(_nr: str, _etag: str | None) -> FetchResult:
    return FetchResult(not_modified=False, text=FIXTURE, etag=None)


def test_build_snapshot_ingests_and_stamps_metadata(tmp_path: Path) -> None:
    db = tmp_path / "snap.db"
    store = Store.open(db)
    reports = build_snapshot(
        store, laws=["2005:716"], fetch=_fixture_fetch, observed=dt.date(2026, 7, 18)
    )
    assert reports["2005:716"].added > 0
    assert store.current_versions()
    built_at = store.get_meta("built_at")
    assert built_at is not None
    dt.datetime.fromisoformat(built_at)  # real wall-clock stamp, parses as ISO
    store.close()


def test_build_snapshot_is_incremental_across_runs(tmp_path: Path) -> None:
    db = tmp_path / "snap.db"
    store = Store.open(db)
    build_snapshot(store, laws=["2005:716"], fetch=_fixture_fetch, observed=dt.date(2026, 7, 18))
    first_count = len(store.current_versions())

    reports = build_snapshot(
        store, laws=["2005:716"], fetch=_fixture_fetch, observed=dt.date(2026, 7, 19)
    )
    assert reports["2005:716"].added == 0
    assert reports["2005:716"].changed == 0
    assert len(store.current_versions()) == first_count
    store.close()


def test_build_snapshot_sends_stored_etag_and_skips_unmodified(tmp_path: Path) -> None:
    """Plan §2.2: conditional requests — an unchanged source (304) shouldn't
    be reparsed, and the ETag round-trips through the snapshot's meta table.
    """
    db = tmp_path / "snap.db"
    store = Store.open(db)
    calls: list[str | None] = []

    def fetch(_nr: str, etag: str | None) -> FetchResult:
        calls.append(etag)
        if etag == '"v1"':
            return FetchResult(not_modified=True, text=None, etag=etag)
        return FetchResult(not_modified=False, text=FIXTURE, etag='"v1"')

    build_snapshot(store, laws=["2005:716"], fetch=fetch, observed=dt.date(2026, 7, 18))
    assert calls[0] is None  # nothing stored yet on the first run

    reports = build_snapshot(store, laws=["2005:716"], fetch=fetch, observed=dt.date(2026, 7, 19))
    assert calls[1] == '"v1"'  # second run sends back the ETag we stored
    assert reports["2005:716"].added == reports["2005:716"].changed == 0  # 304, not reparsed
    store.close()
