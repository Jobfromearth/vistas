"""Pipeline build for guidance sources: fetch -> parse -> ingest -> stamp.

Mirrors test_pipeline_build.py's shape for legal sources. Only
migrationsverket.se's main site is compliance-cleared (ADR-0004 update,
2026-07-18) — this pipeline function must never be pointed at anything else
without a separate villkor check.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from vistas.pipeline.build import build_guidance_snapshot
from vistas.sources.common import FetchResult
from vistas.store import Store

FIXTURE = (Path(__file__).parent / "fixtures" / "migrationsverket_sample.html").read_text(
    encoding="utf-8"
)
URL = "https://example.com/work-permit-guidance.html"


def _fixture_fetch(_url: str, _etag: str | None) -> FetchResult:
    return FetchResult(not_modified=False, text=FIXTURE, etag=None)


def test_build_guidance_snapshot_ingests_and_stamps_metadata(tmp_path: Path) -> None:
    db = tmp_path / "snap.db"
    store = Store.open(db)
    reports = build_guidance_snapshot(
        store, pages={URL: "work_permit"}, fetch=_fixture_fetch, observed=dt.date(2026, 7, 18)
    )
    assert reports[URL].added == 4
    versions = store.current_versions()
    assert versions
    assert all(v.chunk.area == "work_permit" for v in versions)
    assert store.get_meta("built_at") is not None
    store.close()


def test_build_guidance_snapshot_is_incremental_across_runs(tmp_path: Path) -> None:
    db = tmp_path / "snap.db"
    store = Store.open(db)
    build_guidance_snapshot(
        store, pages={URL: "work_permit"}, fetch=_fixture_fetch, observed=dt.date(2026, 7, 18)
    )
    first_count = len(store.current_versions())

    reports = build_guidance_snapshot(
        store, pages={URL: "work_permit"}, fetch=_fixture_fetch, observed=dt.date(2026, 7, 19)
    )
    assert reports[URL].added == 0
    assert reports[URL].changed == 0
    assert len(store.current_versions()) == first_count
    store.close()


def test_build_guidance_snapshot_sends_stored_etag_and_skips_unmodified(tmp_path: Path) -> None:
    db = tmp_path / "snap.db"
    store = Store.open(db)
    calls: list[str | None] = []

    def fetch(_url: str, etag: str | None) -> FetchResult:
        calls.append(etag)
        if etag == '"v1"':
            return FetchResult(not_modified=True, text=None, etag=etag)
        return FetchResult(not_modified=False, text=FIXTURE, etag='"v1"')

    build_guidance_snapshot(
        store, pages={URL: "work_permit"}, fetch=fetch, observed=dt.date(2026, 7, 18)
    )
    assert calls[0] is None

    reports = build_guidance_snapshot(
        store, pages={URL: "work_permit"}, fetch=fetch, observed=dt.date(2026, 7, 19)
    )
    assert calls[1] == '"v1"'
    assert reports[URL].added == reports[URL].changed == 0
    store.close()
