"""SQLite store: bitemporal version chains (ADR-0002) + FTS5 index (ADR-0003).

The store is the snapshot: the pipeline writes it, the MCP server opens it
read-only. Old versions are never deleted; windows are only opened and closed.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from vistas.model import Anchor, ChangeRecord, ObservedChunk, RuleVersion, SourceType

_SCHEMA = """
CREATE TABLE IF NOT EXISTS versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    content TEXT NOT NULL,
    language TEXT NOT NULL,
    source_type TEXT NOT NULL,
    anchor_document TEXT NOT NULL,
    anchor_chapter TEXT,
    anchor_paragraph TEXT,
    anchor_section TEXT,
    source_url TEXT NOT NULL,
    area TEXT,
    profiles TEXT NOT NULL DEFAULT '',
    valid_from TEXT,
    valid_to TEXT,
    amended_by TEXT,
    observed_from TEXT NOT NULL,
    observed_to TEXT,
    supersedes INTEGER REFERENCES versions(version_id)
);
CREATE INDEX IF NOT EXISTS idx_versions_open
    ON versions(chunk_id) WHERE observed_to IS NULL;
CREATE INDEX IF NOT EXISTS idx_versions_scope_open
    ON versions(scope) WHERE observed_to IS NULL;
-- remove_diacritics=0: å/ä/ö are distinct Swedish letters, not accented
-- variants — SQLite's own default (1) folds them together (e.g. lån/län).
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    content, tokenize='unicode61 remove_diacritics 0'
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


@dataclass(frozen=True)
class IngestReport:
    added: int
    changed: int
    removed: int


def _iso(d: dt.date | None) -> str | None:
    return d.isoformat() if d is not None else None


def _date(s: str | None) -> dt.date | None:
    return dt.date.fromisoformat(s) if s is not None else None


def _meta_params(c: ObservedChunk) -> tuple[str | None, str, str | None, str | None, str | None]:
    """The mutable-metadata columns shared by a fresh insert and an in-place
    enrich of an unchanged version: area, profiles, valid_from/to, amended_by.
    """
    return (c.area, ",".join(c.profiles), _iso(c.valid_from), _iso(c.valid_to), c.amended_by)


class Store:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    @classmethod
    def open(cls, path: Path | str, *, read_only: bool = False) -> Store:
        if read_only:
            conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
            store = cls(conn)
        else:
            conn = sqlite3.connect(str(path))
            conn.executescript(_SCHEMA)
            store = cls(conn)
        return store

    def close(self) -> None:
        self._conn.close()

    # -- meta ---------------------------------------------------------------

    def set_meta(self, key: str, value: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO meta(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    # -- ingest (version chain) --------------------------------------------

    def ingest(
        self, scope: str, chunks: list[ObservedChunk], *, observed: dt.date
    ) -> IngestReport:
        """One crawl of one scope (a document or page): diff against the open
        versions in that scope, open/close windows, link supersedes chains.
        """
        incoming = {c.chunk_id: c for c in chunks}
        added = changed = removed = 0
        with self._conn:
            open_rows = {
                row["chunk_id"]: row
                for row in self._conn.execute(
                    "SELECT * FROM versions WHERE scope = ? AND observed_to IS NULL", (scope,)
                )
            }
            for chunk_id, chunk in incoming.items():
                current = open_rows.get(chunk_id)
                if current is None:
                    self._insert(scope, chunk, observed, supersedes=None)
                    added += 1
                elif current["content"] != chunk.content:
                    self._close(current["version_id"], observed)
                    self._insert(scope, chunk, observed, supersedes=current["version_id"])
                    changed += 1
                else:
                    self._enrich(current, chunk)
            for chunk_id, row in open_rows.items():
                if chunk_id not in incoming:
                    self._close(row["version_id"], observed)
                    removed += 1
        return IngestReport(added=added, changed=changed, removed=removed)

    def _insert(
        self, scope: str, c: ObservedChunk, observed: dt.date, supersedes: int | None
    ) -> None:
        cur = self._conn.execute(
            """INSERT INTO versions (
                chunk_id, scope, content, language, source_type,
                anchor_document, anchor_chapter, anchor_paragraph, anchor_section,
                source_url, area, profiles, valid_from, valid_to, amended_by,
                observed_from, observed_to, supersedes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
            (
                c.chunk_id,
                scope,
                c.content,
                c.language,
                c.anchor.source_type.value,
                c.anchor.document,
                c.anchor.chapter,
                c.anchor.paragraph,
                c.anchor.section,
                c.source_url,
                *_meta_params(c),
                observed.isoformat(),
                supersedes,
            ),
        )
        self._conn.execute(
            "INSERT INTO fts(rowid, content) VALUES (?, ?)", (cur.lastrowid, c.content)
        )

    def _close(self, version_id: int, observed: dt.date) -> None:
        self._conn.execute(
            "UPDATE versions SET observed_to = ? WHERE version_id = ?",
            (observed.isoformat(), version_id),
        )

    def _enrich(self, row: sqlite3.Row, c: ObservedChunk) -> None:
        """Content unchanged: refresh metadata on the open version in place
        (e.g. a legal-axis date extracted on a later crawl). No new version.
        """
        self._conn.execute(
            """UPDATE versions SET area = ?, profiles = ?, valid_from = ?,
               valid_to = ?, amended_by = ? WHERE version_id = ?""",
            (*_meta_params(c), row["version_id"]),
        )

    # -- reads --------------------------------------------------------------

    def current_versions(self) -> list[RuleVersion]:
        rows = self._conn.execute(
            "SELECT * FROM versions WHERE observed_to IS NULL ORDER BY version_id"
        ).fetchall()
        return [_to_version(r) for r in rows]

    def get_version(self, version_id: int) -> RuleVersion | None:
        row = self._conn.execute(
            "SELECT * FROM versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        return _to_version(row) if row else None

    def timeline(self, chunk_id: str) -> list[RuleVersion]:
        rows = self._conn.execute(
            "SELECT * FROM versions WHERE chunk_id = ? ORDER BY version_id", (chunk_id,)
        ).fetchall()
        return [_to_version(r) for r in rows]

    def recent_changes(self, *, since: dt.date, area: str | None = None) -> list[ChangeRecord]:
        records: list[ChangeRecord] = []
        area_sql = " AND area = ?" if area else ""
        area_arg: tuple[str, ...] = (area,) if area else ()

        for row in self._conn.execute(
            f"SELECT * FROM versions WHERE observed_from >= ?{area_sql} ORDER BY version_id",
            (since.isoformat(), *area_arg),
        ):
            records.append(
                ChangeRecord(
                    chunk_id=row["chunk_id"],
                    kind="changed" if row["supersedes"] is not None else "added",
                    observed=dt.date.fromisoformat(row["observed_from"]),
                    anchor=_row_anchor(row).canonical(),
                    new_version_id=row["version_id"],
                    old_version_id=row["supersedes"],
                )
            )
        for row in self._conn.execute(
            f"""SELECT * FROM versions v WHERE observed_to >= ?{area_sql}
                AND NOT EXISTS (SELECT 1 FROM versions s WHERE s.supersedes = v.version_id)
                ORDER BY version_id""",
            (since.isoformat(), *area_arg),
        ):
            records.append(
                ChangeRecord(
                    chunk_id=row["chunk_id"],
                    kind="removed",
                    observed=dt.date.fromisoformat(row["observed_to"]),
                    anchor=_row_anchor(row).canonical(),
                    old_version_id=row["version_id"],
                )
            )
        return records

    def search_raw(
        self,
        match_query: str,
        *,
        language: str | None = None,
        profile: str | None = None,
        as_of: dt.date | None = None,
        limit: int = 10,
    ) -> list[tuple[RuleVersion, float]]:
        """FTS5 BM25 search. `match_query` is a prebuilt FTS5 MATCH expression
        (query building + synonym expansion live in vistas.retrieval).
        """
        conditions = ["fts MATCH ?"]
        args: list[str] = [match_query]
        if as_of is None:
            conditions.append("v.observed_to IS NULL")
        else:
            conditions.append(
                "v.observed_from <= ? AND (v.observed_to IS NULL OR v.observed_to > ?)"
            )
            args += [as_of.isoformat(), as_of.isoformat()]
        if language:
            conditions.append("v.language = ?")
            args.append(language)
        if profile:
            conditions.append("(v.profiles = '' OR ',' || v.profiles || ',' LIKE ?)")
            args.append(f"%,{profile},%")
        rows = self._conn.execute(
            f"""SELECT v.*, bm25(fts) AS score FROM fts
                JOIN versions v ON v.version_id = fts.rowid
                WHERE {" AND ".join(conditions)}
                ORDER BY score LIMIT ?""",
            (*args, limit),
        ).fetchall()
        return [(_to_version(r), r["score"]) for r in rows]

    def parent_versions(self, document: str, chapter: str | None) -> list[RuleVersion]:
        """Parent block for get_source: all current chunks of a chapter (legal)
        or of a whole document/page (guidance or chapterless laws)."""
        if chapter is None:
            rows = self._conn.execute(
                """SELECT * FROM versions WHERE anchor_document = ?
                   AND observed_to IS NULL ORDER BY version_id""",
                (document,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM versions WHERE anchor_document = ? AND anchor_chapter = ?
                   AND observed_to IS NULL ORDER BY version_id""",
                (document, chapter),
            ).fetchall()
        return [_to_version(r) for r in rows]


def _row_anchor(row: sqlite3.Row) -> Anchor:
    return Anchor(
        source_type=SourceType(row["source_type"]),
        document=row["anchor_document"],
        chapter=row["anchor_chapter"],
        paragraph=row["anchor_paragraph"],
        section=row["anchor_section"],
    )


def _to_version(row: sqlite3.Row) -> RuleVersion:
    profiles = tuple(p for p in row["profiles"].split(",") if p)
    chunk = ObservedChunk(
        chunk_id=row["chunk_id"],
        content=row["content"],
        language=row["language"],
        anchor=_row_anchor(row),
        source_url=row["source_url"],
        area=row["area"],
        profiles=profiles,
        valid_from=_date(row["valid_from"]),
        valid_to=_date(row["valid_to"]),
        amended_by=row["amended_by"],
    )
    return RuleVersion(
        version_id=row["version_id"],
        chunk=chunk,
        observed_from=dt.date.fromisoformat(row["observed_from"]),
        observed_to=_date(row["observed_to"]),
        supersedes=row["supersedes"],
    )
