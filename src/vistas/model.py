"""Domain model. Terms follow CONTEXT.md; time semantics follow ADR-0002."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from enum import StrEnum


class SourceType(StrEnum):
    LEGAL = "legal"
    GUIDANCE = "guidance"


@dataclass(frozen=True)
class Anchor:
    """Layered citation anchor (ADR: layered honesty).

    Legal sources anchor to document + kapitel + paragraf; guidance sources
    anchor to URL + section title. `level` in tool output is derived, never guessed.
    """

    source_type: SourceType
    document: str  # legal: "sfs-2005:716"; guidance: page URL
    chapter: str | None = None  # legal: kapitel number, e.g. "5"
    paragraph: str | None = None  # legal: paragraf, e.g. "5" or "5 a"
    section: str | None = None  # guidance: section heading

    def canonical(self) -> str:
        if self.source_type is SourceType.LEGAL:
            parts = [self.document]
            if self.chapter:
                parts.append(f"kap.{self.chapter}")
            if self.paragraph:
                parts.append(f"§{self.paragraph}")
            return " ".join(parts)
        return f"{self.document}#{self.section}" if self.section else self.document

    @property
    def level(self) -> str:
        """Honest citation granularity: 'paragraph' only when a real § exists."""
        if self.source_type is SourceType.LEGAL and self.paragraph:
            return "paragraph"
        return "section"

    @staticmethod
    def parse(canonical: str) -> Anchor:
        """Inverse of canonical(); used by the get_source tool."""
        if canonical.startswith(("http://", "https://")):
            doc, _, section = canonical.partition("#")
            return Anchor(SourceType.GUIDANCE, doc, section=section or None)
        parts = canonical.split()
        chapter = None
        paragraph = None
        for part in parts[1:]:
            if part.startswith("kap."):
                chapter = part.removeprefix("kap.")
            elif part.startswith("§"):
                paragraph = part.removeprefix("§")
        return Anchor(SourceType.LEGAL, parts[0], chapter=chapter, paragraph=paragraph)


@dataclass(frozen=True)
class ObservedChunk:
    """A rule unit as seen by one crawl, before versioning."""

    chunk_id: str  # stable rule-unit identity, e.g. "sfs-2005:716/5/5/sv"
    content: str
    language: str  # "sv" | "en"
    anchor: Anchor
    source_url: str
    area: str | None = None  # work_permit / study / put / family / ...
    profiles: tuple[str, ...] = ()  # applicability tags; empty = applies to all
    valid_from: dt.date | None = None  # legal axis: only when reliably extracted
    valid_to: dt.date | None = None
    amended_by: str | None = None  # e.g. "2022:303" — amendment reference, if any


@dataclass(frozen=True)
class RuleVersion:
    """One stored version of a rule unit (a row in the version chain)."""

    version_id: int
    chunk: ObservedChunk
    observed_from: dt.date  # observation axis: always present
    observed_to: dt.date | None  # None = currently observed
    supersedes: int | None  # version_id of the version this one replaced


@dataclass(frozen=True)
class ChangeRecord:
    """One entry in the change log derived from the version chain."""

    chunk_id: str
    kind: str  # "added" | "changed" | "removed"
    observed: dt.date
    anchor: str
    new_version_id: int | None = None
    old_version_id: int | None = None


@dataclass(frozen=True)
class SearchHit:
    version: RuleVersion
    score: float
