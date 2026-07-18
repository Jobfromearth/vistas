"""Lexical retrieval: FTS5/BM25 + a Swedish/English domain synonym table.

ADR-0003: no embedding model ships with the package. Cross-language reach is
the caller agent's job (SKILL.md instructs it to send sv/en keywords); this
module's synonym table is a second line of defense for the common terms, not
a translator. A term with no match here still searches literally.
"""

from __future__ import annotations

import datetime as dt
import re

from vistas.model import SearchHit
from vistas.store import Store

# Two-token phrases recognised as a single domain concept. Matching consumes
# both tokens so "work permit" isn't also expanded word-by-word into noise.
_PHRASES: dict[tuple[str, str], tuple[str, ...]] = {
    ("work", "permit"): ("arbetstillstånd",),
    ("residence", "permit"): ("uppehållstillstånd",),
    ("study", "permit"): ("uppehållstillstånd",),
    ("permanent", "residence"): ("varaktigt", "put"),
    ("blue", "card"): ("blåkort",),
    ("collective", "agreement"): ("kollektivavtal",),
    ("processing", "time"): ("handläggningstid",),
    ("job", "offer"): ("anställningsavtal",),
}

# Single-word synonyms, keyed by lowercase token. Symmetric: looking up either
# side of an EN/SV pair finds the other.
_WORDS: dict[str, tuple[str, ...]] = {
    "salary": ("lön",),
    "wage": ("lön",),
    "lön": ("salary", "wage"),
    "employer": ("arbetsgivare",),
    "arbetsgivare": ("employer",),
    "income": ("inkomst",),
    "inkomst": ("income",),
    "family": ("familj", "anhörig"),
    "familj": ("family",),
    "visa": ("visering",),
    "visering": ("visa",),
    "deportation": ("utvisning",),
    "utvisning": ("deportation",),
    "extension": ("förlängning",),
    "förlängning": ("extension",),
    "application": ("ansökan",),
    "ansökan": ("application",),
    "threshold": ("gräns", "tröskel"),
    "arbetstillstånd": ("work", "permit"),
    "uppehållstillstånd": ("residence", "permit"),
}

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _fts_term(alt: str) -> str:
    return f'"{alt}"' if " " in alt else f"{alt}*"


def build_match_query(text: str) -> str:
    """Turn a free-text query into an FTS5 MATCH expression: one OR-group of
    synonym alternatives per recognised concept, ANDed together.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    groups: list[tuple[str, ...]] = []
    i = 0
    while i < len(tokens):
        pair = (tokens[i], tokens[i + 1]) if i + 1 < len(tokens) else None
        if pair is not None and pair in _PHRASES:
            groups.append((tokens[i], tokens[i + 1], *_PHRASES[pair]))
            i += 2
        else:
            word = tokens[i]
            groups.append((word, *_WORDS.get(word, ())))
            i += 1
    return " AND ".join(
        "(" + " OR ".join(dict.fromkeys(_fts_term(alt) for alt in group)) + ")"
        for group in groups
    )


def search(
    store: Store,
    query: str,
    *,
    language: str | None = None,
    profile: str | None = None,
    as_of: dt.date | None = None,
    limit: int = 10,
) -> list[SearchHit]:
    """Rank current (or, with `as_of`, historically current) rule versions
    matching `query`. Returns [] rather than padding with weak matches —
    callers must be able to say "no data" (plan §3, boundary rules).
    """
    match_query = build_match_query(query)
    if not match_query:
        return []
    results = store.search_raw(
        match_query, language=language, profile=profile, as_of=as_of, limit=limit
    )
    return [SearchHit(version=version, score=score) for version, score in results]
