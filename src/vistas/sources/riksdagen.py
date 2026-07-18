"""Riksdagen open data: fetch SFS law text and chunk it into § units.

The .text rendition of an SFS document carries explicit validity markers —
`/Träder i kraft I:YYYY-MM-DD/` and `/Upphör att gälla U:YYYY-MM-DD/` — which
are the only sources for the legal validity axis (ADR-0002). Paragraphs without
markers get no legal dates; the observation axis comes from the ingest crawl.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, replace

import httpx

from vistas.model import Anchor, ObservedChunk, SourceType
from vistas.sources.common import FetchResult, PoliteClient

USER_AGENT = "vistas-mcp/0.1 (+https://github.com/Jobfromearth/vistas; haobo5869@gmail.com)"

# Chapter → area tags per document, used for topic routing (plan §3.3).
# `ObservedChunk.profiles` (eu/non_eu, student/worker/graduate, family) is
# deliberately left empty here: chapters don't map 1:1 to applicability, and
# guessing would risk hiding a relevant rule from the wrong profile — a worse
# failure than the current "profile filter is a no-op on real data" gap.
# Real profile tagging needs its own domain pass; M3 work.
AREA_MAPS: dict[str, dict[str, str]] = {
    "2005:716": {  # Utlänningslagen
        "2": "entry_and_stay",
        "3": "visa",
        "4": "protection",
        "5": "residence_permit",
        "5 a": "put",
        "5 b": "study",
        "6": "work_permit",
        "6 a": "eu_blue_card",
        "6 b": "ict_permit",
        "6 c": "seasonal_work",
        "7": "revocation",
    },
}

_CHAPTER_RE = re.compile(r"^(\d+(?: [a-z])?) kap\.(?:\s+(.*))?$")
_PARAGRAPH_RE = re.compile(r"^(\d+(?: [a-z])?) §\s*(.*)$")
# Validity markers come in several spellings: "U:2026-07-12", "I:2026-07-12",
# a missing U/I letter, or a non-date like "I:den dag som regeringen bestämmer".
_MARKER_RE = re.compile(r"^/(Upphör att gälla|Träder i kraft)\s*[UI]?:?\s*([^/]*)/\s*(.*)$")
_HEADING_MARKER_RE = re.compile(
    r"^/(?:Rubriken|Kapitlet)\s+(upphör att gälla|träder i kraft)\s*[UI]?:?\s*([^/]*)/\s*$"
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_AMENDED_RE = re.compile(r"Lag \((\d{4}:\d+)\)\.?\s*$")
_SFS_NR_RE = re.compile(r"SFS nr:\s*(\d{4}:\d+)")


def _marker_date(text: str) -> dt.date | None:
    match = _DATE_RE.search(text)
    return dt.date.fromisoformat(match.group()) if match else None


def _marker_effect(kind: str, date: dt.date | None) -> tuple[str, dt.date | None, str]:
    """Which legal-axis field a validity marker sets, its value, and (for an
    entry-into-force marker only) the chunk-identity suffix distinguishing
    the incoming wording from what it replaces — undated markers ("den dag
    som regeringen bestämmer") still get a suffix so the two versions don't
    collide, they just can't be dated yet.
    """
    if kind.lower().startswith("träder"):
        return "valid_from", date, f"@{date.isoformat() if date else 'pending'}"
    return "valid_to", date, ""


@dataclass(frozen=True)
class ParsedLaw:
    sfs_nr: str
    title: str
    chunks: list[ObservedChunk]


@dataclass
class _OpenParagraph:
    chapter: str | None  # plain kapitel number, used for the citation anchor
    chapter_key: str | None  # kapitel + version suffix, used for chunk identity
    paragraph: str
    id_suffix: str  # from the paragraph's own /Träder i kraft/ marker only
    valid_from: dt.date | None
    valid_to: dt.date | None
    lines: list[str]


def parse_sfs_text(text: str, *, language: str = "sv") -> ParsedLaw:
    lines = text.splitlines()
    title = next((line.strip() for line in lines if line.strip()), "")
    nr_match = _SFS_NR_RE.search(text)
    if nr_match:
        sfs_nr = nr_match.group(1)
    else:
        title_nr = re.search(r"\((\d{4}:\d+)\)", title)
        if not title_nr:
            raise ValueError("cannot determine SFS number from document text")
        sfs_nr = title_nr.group(1)

    document = f"sfs-{sfs_nr}"
    source_url = f"https://data.riksdagen.se/dokument/sfs-{sfs_nr.replace(':', '-')}"
    area_map = AREA_MAPS.get(sfs_nr, {})

    chunks: list[ObservedChunk] = []
    chapter: str | None = None
    chapter_key: str | None = None
    chapter_valid_from: dt.date | None = None  # chapter-level träder marker
    chapter_valid_to: dt.date | None = None  # chapter-level upphör marker
    pending_rubrik: tuple[str, dt.date | None] | None = None
    open_para: _OpenParagraph | None = None
    prev_blank = True  # headings/paragraphs only open after a blank line

    def flush() -> None:
        nonlocal open_para
        if open_para is None:
            return
        content = re.sub(r"\s+", " ", " ".join(open_para.lines)).strip()
        if content:
            amended = _AMENDED_RE.search(content)
            suffix = open_para.id_suffix
            chap_part = open_para.chapter_key if open_para.chapter_key is not None else "-"
            chunks.append(
                ObservedChunk(
                    chunk_id=(
                        f"{document}/{chap_part}/{open_para.paragraph}{suffix}/{language}"
                    ),
                    content=content,
                    language=language,
                    anchor=Anchor(
                        SourceType.LEGAL,
                        document,
                        chapter=open_para.chapter,
                        paragraph=open_para.paragraph,
                    ),
                    source_url=source_url,
                    area=area_map.get(open_para.chapter or ""),
                    valid_from=open_para.valid_from,
                    valid_to=open_para.valid_to,
                    amended_by=amended.group(1) if amended else None,
                )
            )
        open_para = None

    for raw in lines:
        line = raw.rstrip()
        if not line:
            prev_blank = True
            continue

        rubrik = _HEADING_MARKER_RE.match(line)
        if rubrik:
            # Marker refers to the *next* heading; it never belongs to § content.
            flush()
            pending_rubrik = (rubrik.group(1), _marker_date(rubrik.group(2)))
            prev_blank = True  # the heading follows directly, without a blank line
            continue

        if prev_blank:
            chap = _CHAPTER_RE.match(line)
            if chap and "§" not in line:
                flush()
                chapter = chap.group(1)
                chapter_key = chapter
                chapter_valid_from = chapter_valid_to = None
                if pending_rubrik is not None:
                    kind, date = pending_rubrik
                    axis, value, suffix = _marker_effect(kind, date)
                    if axis == "valid_from":
                        chapter_valid_from = value
                        chapter_key = f"{chapter}{suffix}"
                    else:
                        chapter_valid_to = value
                pending_rubrik = None
                prev_blank = False
                continue
            para = _PARAGRAPH_RE.match(line)
            if para:
                flush()
                rest = para.group(2)
                valid_from = chapter_valid_from
                valid_to = chapter_valid_to
                id_suffix = ""
                marker = _MARKER_RE.match(rest)
                if marker:
                    # An explicit § marker overrides the chapter default for its
                    # axis — an undated marker means "unknown", never the
                    # chapter's date (ADR-0002: no faked legal dates).
                    date = _marker_date(marker.group(2))
                    axis, value, id_suffix = _marker_effect(marker.group(1), date)
                    if axis == "valid_from":
                        valid_from = value
                    else:
                        valid_to = value
                    rest = marker.group(3)
                open_para = _OpenParagraph(
                    chapter=chapter,
                    chapter_key=chapter_key,
                    paragraph=para.group(1),
                    id_suffix=id_suffix,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    lines=[rest] if rest else [],
                )
                pending_rubrik = None
                prev_blank = False
                continue

        # A /Rubriken .../ marker followed by a section subheading (not a
        # chapter) applies to that subheading only — drop it.
        pending_rubrik = None
        if open_para is not None:
            open_para.lines.append(line)
        prev_blank = False

    flush()

    # Source-text edge cases can still yield an identical id twice (e.g. the
    # same § printed with two markers carrying the same date). Disambiguate
    # deterministically by document order instead of dropping data.
    seen: dict[str, int] = {}
    deduped: list[ObservedChunk] = []
    for c in chunks:
        n = seen.get(c.chunk_id, 0)
        seen[c.chunk_id] = n + 1
        if n == 0:
            deduped.append(c)
        else:
            base, _, lang = c.chunk_id.rpartition("/")
            deduped.append(replace(c, chunk_id=f"{base}#{n + 1}/{lang}"))
    return ParsedLaw(sfs_nr=sfs_nr, title=title, chunks=deduped)


class RiksdagenClient(PoliteClient):
    """Polite client for data.riksdagen.se (official API, no scraping needed).

    Crawl etiquette per plan §2.2: self-throttled to <= 1 request/second, and
    conditional requests via ETag so an unchanged law isn't re-downloaded.
    """

    BASE = "https://data.riksdagen.se"

    def __init__(self, http: httpx.Client | None = None) -> None:
        super().__init__(USER_AGENT, http)

    def fetch_sfs_text(self, sfs_nr: str, *, etag: str | None = None) -> FetchResult:
        """Fetch the plain-text rendition of an SFS law, e.g. sfs_nr='2005:716'.
        Pass the ETag from a previous fetch to make this a conditional request.
        """
        dok_id = f"sfs-{sfs_nr.replace(':', '-')}"
        return self._fetch(f"{self.BASE}/dokument/{dok_id}.text", etag=etag)
