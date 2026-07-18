"""Migrationsverket guidance-page parsing.

The fixture is a real, trimmed slice of migrationsverket.se's work-permit
guidance page (fetched 2026-07-18) — the site's CMS wraps headings in
several different container types (plain portlets, collapsible accordions),
so we regularize via markdownify (HTML → Markdown, ADR-0004-adjacent: a
lightweight sibling of the plan's markitdown choice, without pulling in
markitdown's ML dependency stack) rather than walking the DOM by hand,
which turned out fragile against the real page's heading-container variety.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vistas.model import SourceType
from vistas.sources.migrationsverket import parse_guidance_page

FIXTURE = (Path(__file__).parent / "fixtures" / "migrationsverket_sample.html").read_text(
    encoding="utf-8"
)
URL = "https://www.migrationsverket.se/en/you-want-to-apply/work/employee-or-self-employed/employees.html"
SALARY_HEADING = "How high a salary/wages do I need to have to meet the salary requirement?"


@pytest.fixture(scope="module")
def page():  # type: ignore[no-untyped-def]
    return parse_guidance_page(FIXTURE, URL, area="work_permit")


def _section(page, heading: str):  # type: ignore[no-untyped-def]
    return next(c for c in page.chunks if c.anchor.section == heading)


class TestChunking:
    def test_finds_all_real_headings(self, page) -> None:  # type: ignore[no-untyped-def]
        sections = [c.anchor.section for c in page.chunks]
        assert "Occupations that cannot qualify for a work permit" in sections
        assert "Requirements to get a work permit" in sections
        assert SALARY_HEADING in sections
        assert "Certain professions are exempt from the salary requirement" in sections
        assert len(page.chunks) == 4

    def test_heading_link_syntax_is_stripped(self, page) -> None:  # type: ignore[no-untyped-def]
        # Source markdown has "[Requirements to get a work permit](#anchor)"
        # for this one — the citation anchor must be the plain heading text.
        sections = [c.anchor.section for c in page.chunks]
        assert not any(s.startswith("[") for s in sections)

    def test_h3_content_excludes_parent_h2_intro_text(self, page) -> None:  # type: ignore[no-untyped-def]
        salary = next(c for c in page.chunks if c.anchor.section == SALARY_HEADING)
        assert "SEK 34,470" in salary.content
        assert "valid passport" not in salary.content  # that's the parent h2's own text

    def test_h2_content_excludes_nested_h3_text(self, page) -> None:  # type: ignore[no-untyped-def]
        req = _section(page, "Requirements to get a work permit")
        assert "valid passport" in req.content
        assert "SEK 34,470" not in req.content  # that belongs to the nested h3

    def test_content_is_plain_text_not_raw_markdown(self, page) -> None:  # type: ignore[no-untyped-def]
        req = _section(page, "Requirements to get a work permit")
        assert "**" not in req.content
        assert "[" not in req.content


class TestAnchorAndMetadata:
    def test_anchor_is_section_level_guidance(self, page) -> None:  # type: ignore[no-untyped-def]
        c = page.chunks[0]
        assert c.anchor.source_type is SourceType.GUIDANCE
        assert c.anchor.document == URL
        assert c.anchor.level == "section"
        assert c.anchor.canonical() == f"{URL}#{c.anchor.section}"

    def test_source_url_and_area_propagate(self, page) -> None:  # type: ignore[no-untyped-def]
        for c in page.chunks:
            assert c.source_url == URL
            assert c.area == "work_permit"

    def test_chunk_ids_are_unique(self, page) -> None:  # type: ignore[no-untyped-def]
        ids = [c.chunk_id for c in page.chunks]
        assert len(ids) == len(set(ids))


class TestIntroContent:
    def test_lead_paragraph_before_first_heading_is_not_dropped(self) -> None:
        """Regression: a real page (permanent-residence-permit.html) has its
        core eligibility explanation as a lead paragraph before any h2 — an
        earlier version of this parser silently discarded all content before
        the first heading, keeping only a minor edge-case subsection."""
        html = """
        <main>
          <h1>Permanent residence permit</h1>
          <p>You have a residence permit in Sweden and now want to apply for
          a permanent residence permit. To be granted one, you must meet
          special requirements relating to financial maintenance and conduct.</p>
          <h2>A permanent residence permit can be revoked</h2>
          <p>If you are no longer resident in Sweden, the Migration Agency
          can revoke your permit under certain circumstances described here.</p>
        </main>
        """
        page = parse_guidance_page(html, "https://example.com/put.html")
        sections = {c.anchor.section: c.content for c in page.chunks}
        assert "Permanent residence permit" in sections
        assert "special requirements" in sections["Permanent residence permit"]
        assert "A permanent residence permit can be revoked" in sections


class TestNoiseFiltering:
    def test_short_nav_only_section_is_dropped(self) -> None:
        html = """
        <main>
          <h2>News</h2>
          <a href="/news">See all news</a>
          <h2>Real content heading</h2>
          <p>This paragraph has enough substantive text to survive the
          minimum-length filter that exists to drop nav-only sections
          like bare card-grid link lists.</p>
        </main>
        """
        page = parse_guidance_page(html, "https://example.com/page.html")
        sections = [c.anchor.section for c in page.chunks]
        assert "News" not in sections
        assert "Real content heading" in sections


class TestDeduplication:
    def test_repeated_heading_text_gets_distinct_chunk_ids(self) -> None:
        html = """
        <main>
          <h2>What does it cost to apply?</h2>
          <p>First occurrence: this section explains the fee for the first
          application type, with enough text to clear the length filter.</p>
          <h2>What does it cost to apply?</h2>
          <p>Second occurrence: this section explains a different fee for a
          different application type, also with enough text to pass.</p>
        </main>
        """
        page = parse_guidance_page(html, "https://example.com/page.html")
        matching = [c for c in page.chunks if c.anchor.section == "What does it cost to apply?"]
        assert len(matching) == 2
        assert len({c.chunk_id for c in matching}) == 2
        assert "First occurrence" in matching[0].content
        assert "Second occurrence" in matching[1].content
