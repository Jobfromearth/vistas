"""Snapshot build: fetch legal sources, parse, ingest into the version chain,
stamp the snapshot with a build timestamp (plan §5 — the freshness promise).

M1 scope only: Riksdagen SFS law text. Migrationsverket guidance-page
ingestion is gated behind the per-site villkor check (ADR-0004, plan §2.2)
and is not wired in here yet — adding it before that check would put
unverified guidance content straight into a publicly distributed snapshot.
"""

from __future__ import annotations

import argparse
import datetime as dt
from collections.abc import Callable
from pathlib import Path

from vistas.config import DB_PATH_ENV, default_db_path
from vistas.sources.riksdagen import FetchResult, RiksdagenClient, parse_sfs_text
from vistas.store import IngestReport, Store

# P0 legal sources tracked from day one (plan §2.1).
DEFAULT_LAWS: tuple[str, ...] = ("2005:716",)  # Utlänningslagen


def build_snapshot(
    store: Store,
    *,
    laws: tuple[str, ...] | list[str] = DEFAULT_LAWS,
    fetch: Callable[[str, str | None], FetchResult] | None = None,
    observed: dt.date | None = None,
) -> dict[str, IngestReport]:
    """Fetch each law's text (conditionally, via the snapshot's stored ETag —
    plan §2.2), parse it into §-anchored chunks, and ingest into the version
    chain. `fetch` is injectable for offline testing; the real pipeline
    passes RiksdagenClient.fetch_sfs_text.
    """
    if fetch is None:
        client = RiksdagenClient()
        fetch = lambda nr, etag: client.fetch_sfs_text(nr, etag=etag)  # noqa: E731
    observed = observed or dt.datetime.now(dt.UTC).date()

    reports: dict[str, IngestReport] = {}
    for sfs_nr in laws:
        etag_key = f"etag:sfs-{sfs_nr}"
        result = fetch(sfs_nr, store.get_meta(etag_key))
        if result.not_modified:
            reports[sfs_nr] = IngestReport(added=0, changed=0, removed=0)
            continue

        assert result.text is not None
        law = parse_sfs_text(result.text)
        if not law.chunks:
            # Parser health signal (plan §5): a law with zero parsed §§ means
            # the source format changed under us, not that the law is empty.
            raise RuntimeError(f"parsed 0 chunks for SFS {sfs_nr} — check for a format change")
        scope = f"sfs-{law.sfs_nr}"
        reports[sfs_nr] = store.ingest(scope, law.chunks, observed=observed)
        if result.etag:
            store.set_meta(etag_key, result.etag)

    store.set_meta("built_at", dt.datetime.now(dt.UTC).isoformat())
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Build/update the Vistas snapshot database.")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help=f"Snapshot path (default: ${DB_PATH_ENV} or ~/.vistas/snapshot.db)",
    )
    parser.add_argument(
        "--law",
        action="append",
        dest="laws",
        help="SFS number to ingest, e.g. 2005:716 (repeatable)",
    )
    args = parser.parse_args()

    db_path = args.db or default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    store = Store.open(db_path)
    try:
        reports = build_snapshot(store, laws=tuple(args.laws) if args.laws else DEFAULT_LAWS)
    finally:
        store.close()

    for sfs_nr, report in reports.items():
        print(f"{sfs_nr}: +{report.added} ~{report.changed} -{report.removed}")


if __name__ == "__main__":
    main()
