"""Protocol-agnostic implementations of the four MCP tools (plan §4.1).

Kept separate from vistas.server so the logic is testable without spinning up
the MCP protocol. Every function returns a JSON-serializable dict with an
explicit "status": "ok" | "no_data" — never free-form generation, never a
padded result when nothing was found (plan §3, boundary rules).
"""

from __future__ import annotations

import datetime as dt
import difflib
from typing import Any

from vistas.model import Anchor, ChangeRecord, RuleVersion
from vistas.retrieval import search
from vistas.store import Store

# Explicit attribution string per source, keyed by domain. Migrationsverket's
# own terms make this a hard redistribution condition, not just courtesy —
# "förutsatt att du anger Migrationsverket som källa" (docs/research/
# migrationsverket-villkor.md). source_url alone identifies the source, but
# an explicit name survives even if a downstream consumer only renders
# `content` and drops the URL.
_ATTRIBUTION_BY_DOMAIN: dict[str, str] = {
    "migrationsverket.se": "Migrationsverket",
    "riksdagen.se": "Sveriges riksdag",
}


def _attribution(source_url: str) -> str | None:
    for domain, name in _ATTRIBUTION_BY_DOMAIN.items():
        if domain in source_url:
            return name
    return None


def _version_dict(v: RuleVersion) -> dict[str, Any]:
    c = v.chunk
    return {
        "chunk_id": c.chunk_id,
        "content": c.content,
        "language": c.language,
        "anchor": c.anchor.canonical(),
        "anchor_level": c.anchor.level,
        # ADR-0002: tool output must say which time axis it's reporting.
        # source_type names it explicitly; anchor shape implies it too.
        "source_type": c.anchor.source_type.value,
        "source_url": c.source_url,
        "attribution": _attribution(c.source_url),
        "area": c.area,
        "version_id": v.version_id,
        "supersedes": v.supersedes,
        "observed_from": v.observed_from.isoformat(),
        "observed_to": v.observed_to.isoformat() if v.observed_to else None,
        "valid_from": c.valid_from.isoformat() if c.valid_from else None,
        "valid_to": c.valid_to.isoformat() if c.valid_to else None,
        "amended_by": c.amended_by,
    }


def _change_dict(c: ChangeRecord) -> dict[str, Any]:
    return {
        "chunk_id": c.chunk_id,
        "kind": c.kind,
        "observed": c.observed.isoformat(),
        "anchor": c.anchor,
        "new_version_id": c.new_version_id,
        "old_version_id": c.old_version_id,
    }


def _with_snapshot_meta(store: Store, payload: dict[str, Any]) -> dict[str, Any]:
    return payload | {"snapshot_built_at": store.get_meta("built_at")}


def search_rules(
    store: Store,
    query: str,
    *,
    profile: str | None = None,
    language: str | None = None,
    as_of_date: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    as_of = dt.date.fromisoformat(as_of_date) if as_of_date else None
    hits = search(store, query, language=language, profile=profile, as_of=as_of, limit=limit)
    if not hits:
        return {"status": "no_data", "query": query}
    return _with_snapshot_meta(
        store,
        {
            "status": "ok",
            "results": [_version_dict(h.version) | {"score": h.score} for h in hits],
        },
    )


def rule_timeline(store: Store, chunk_id: str) -> dict[str, Any]:
    """History of one rule unit. `chunk_id` only for now — resolving a free-text
    `topic` to a chunk_id (plan §4.1) needs a topic index and is M3 work.
    """
    versions = store.timeline(chunk_id)
    if not versions:
        return {"status": "no_data", "chunk_id": chunk_id}
    entries = [_version_dict(v) for v in versions]
    for prev, cur in zip(entries, entries[1:], strict=False):
        cur["diff"] = "\n".join(
            difflib.unified_diff(
                prev["content"].split(), cur["content"].split(), lineterm="", n=2
            )
        )
    return _with_snapshot_meta(
        store, {"status": "ok", "chunk_id": chunk_id, "versions": entries}
    )


def recent_changes(store: Store, *, since: str, area: str | None = None) -> dict[str, Any]:
    since_date = dt.date.fromisoformat(since)
    changes = store.recent_changes(since=since_date, area=area)
    if not changes:
        return {"status": "no_data", "since": since, "area": area}
    return _with_snapshot_meta(
        store, {"status": "ok", "changes": [_change_dict(c) for c in changes]}
    )


def get_source(store: Store, anchor: str) -> dict[str, Any]:
    parsed = Anchor.parse(anchor)
    sections = store.parent_versions(parsed.document, parsed.chapter)
    if not sections:
        return {"status": "no_data", "anchor": anchor}
    return _with_snapshot_meta(
        store,
        {"status": "ok", "anchor": anchor, "sections": [_version_dict(v) for v in sections]},
    )
