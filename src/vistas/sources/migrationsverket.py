"""Migrationsverket guidance-page ingestion.

Compliance (ADR-0004, 2026-07-18 update; docs/research/migrationsverket-villkor.md):
migrationsverket.se's own copyright notice permits full-text reuse and
redistribution of website prose, conditioned on citing Migrationsverket as
the source — cleared for GUIDANCE_PAGES below. rättsliga ställningstaganden
(the Lifos subdomain) are NOT covered by that verification and must not be
added here without a separate check.

The site's CMS wraps headings in several different container types (plain
portlets, collapsible accordions) with no single reliable DOM pattern, so
guidance is regularized via markdownify (HTML -> Markdown) rather than a
hand-rolled DOM walk — every heading comes out as a uniform `##`/`###` line
regardless of its source container, the same "regularize before chunking"
idea as the plan's markitdown choice, without pulling in markitdown's ML
dependency stack (only beautifulsoup4 + markdownify are needed here).

Coverage: the plan §1 target visa-question set (study extension, job-seeking
permit, study-to-work conversion, work permit, PUT, family permit) plus
tourism/visiting-friends-and-family, one seed page per topic, each verified
end-to-end. GUIDANCE_PAGES is a plain URL->area map — extending coverage
further is adding entries, not new mechanism.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

from vistas.model import Anchor, ObservedChunk, SourceType
from vistas.sources.common import FetchResult, PoliteClient

USER_AGENT = "vistas-mcp/0.1 (+https://github.com/Jobfromearth/vistas; haobo5869@gmail.com)"

# URL -> area tag (plan §3.3 topic routing), same mechanism as riksdagen.AREA_MAPS.
# "job_seeking" and "family" have no Riksdagen chapter counterpart yet
# (AREA_MAPS in riksdagen.py doesn't tag those chapters) — until it does,
# those two areas only ever surface guidance content, not law text.
_BASE = "https://www.migrationsverket.se/en/you-want-to-apply"
GUIDANCE_PAGES: dict[str, str] = {
    # 工签 work permit
    f"{_BASE}/work/employee-or-self-employed/employees.html": "work_permit",
    # 学签 study permit (university-level studies)
    f"{_BASE}/study/higher-education.html": "study",
    # 求职签 job-seeking permit after graduation. Note: under
    # you-want-to-extend, not you-want-to-apply — the apply-tree page for
    # this topic is a thin stub pointing here; this is the real content.
    "https://www.migrationsverket.se/en/you-want-to-extend/study/"
    "look-for-work-after-completing-your-studies-in-sweden.html": "job_seeking",
    # 学签转工签 study-to-work conversion
    f"{_BASE}/work/employee-or-self-employed/students-who-have-found-work.html": "work_permit",
    # PUT permanent residence
    f"{_BASE}/permanent-residence-permit.html": "put",
    # 家属签 family of a work-permit holder
    f"{_BASE}/work/employee-or-self-employed/"
    "family-of-an-employee-or-self-employed-person-who-apply-afterwards.html": "family",
    # 旅游 tourism / short visits (Schengen entry visa)
    f"{_BASE}/visiting-sweden/visiting-sweden-for-up-to-90-days-entry-visa.html": "visa",
    # 探亲访友 visiting friends or family
    f"{_BASE}/visiting-sweden/invite-family-friends-or-partners.html": "visa",
}

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_LINK_WRAP_RE = re.compile(r"^\[(.+)]\([^)]*\)$")
_LINK_RE = re.compile(r"\[([^\]]*)]\([^)]*\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_MIN_SECTION_CHARS = 40  # drops nav-only headings (e.g. a bare card-grid link list)


@dataclass(frozen=True)
class ParsedPage:
    url: str
    chunks: list[ObservedChunk]


@dataclass
class _OpenSection:
    heading: str
    lines: list[str]


def _clean_heading(raw: str) -> str:
    """CMS headings that are themselves anchor-linked come through as
    markdown links, e.g. "[Requirements to get a work permit](#anchor)" —
    the citation anchor must be the plain visible text."""
    m = _LINK_WRAP_RE.match(raw.strip())
    return m.group(1) if m else raw.strip()


def _clean_prose(lines: list[str]) -> str:
    text = " ".join(line for line in lines if line.strip())
    text = _LINK_RE.sub(r"\1", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_guidance_page(
    html: str, url: str, *, language: str = "en", area: str | None = None
) -> ParsedPage:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    for noise in main.select("script, style, nav, footer"):
        noise.decompose()
    markdown = markdownify(str(main), heading_style="ATX")

    chunks: list[ObservedChunk] = []
    open_section: _OpenSection | None = None
    seen: dict[str, int] = {}
    page_slug = _slug(url.rsplit("/", 1)[-1].removesuffix(".html"))

    def flush() -> None:
        nonlocal open_section
        if open_section is None:
            return
        content = _clean_prose(open_section.lines)
        if len(content) >= _MIN_SECTION_CHARS:
            section = open_section.heading
            n = seen.get(section, 0)
            seen[section] = n + 1
            suffix = f"#{n + 1}" if n else ""
            chunks.append(
                ObservedChunk(
                    chunk_id=f"guid/{page_slug}/{_slug(section)}{suffix}/{language}",
                    content=content,
                    language=language,
                    anchor=Anchor(SourceType.GUIDANCE, url, section=section),
                    source_url=url,
                    area=area,
                )
            )
        open_section = None

    for line in markdown.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            flush()
            open_section = _OpenSection(heading=_clean_heading(m.group(2)), lines=[])
            continue
        if open_section is not None:
            open_section.lines.append(line)
    flush()

    return ParsedPage(url=url, chunks=chunks)


class MigrationsverketClient(PoliteClient):
    """Polite client for migrationsverket.se guidance pages.

    Crawl etiquette per plan §2.2: self-throttled to <= 1 request/second, and
    conditional requests via ETag so an unchanged page isn't re-downloaded —
    though verified 2026-07-18, migrationsverket.se sends no ETag or
    Last-Modified for these pages (unlike data.riksdagen.se), so in practice
    every build refetches in full; see test_migrationsverket_client.py.
    robots.txt (checked 2026-07-18) does not disallow the GUIDANCE_PAGES paths.
    """

    def __init__(self, http: httpx.Client | None = None) -> None:
        super().__init__(USER_AGENT, http)

    def fetch_page(self, url: str, *, etag: str | None = None) -> FetchResult:
        return self._fetch(url, etag=etag)
