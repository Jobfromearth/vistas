"""FastMCP stdio server exposing the four Vistas tools over MCP.

Boundary declaration (plan §1, §4.1) lives in every tool description, not
just in a README an agent might not read: this is not legal advice, only a
sourced regulatory data service; individual-case outcomes are out of scope.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from vistas import tools
from vistas.config import DB_PATH_ENV, default_db_path
from vistas.store import Store

_BOUNDARY = (
    "Not legal advice (inte juridisk rådgivning) — a sourced regulatory data "
    "service only. Does not judge individual cases (e.g. 'will my application "
    "be approved'); returns only the rules themselves, each with an official "
    "citation. If no citable result exists, returns status='no_data' rather "
    "than guessing."
)

def build_server(store: Store) -> FastMCP:
    mcp: FastMCP = FastMCP(
        name="vistas",
        instructions=(
            "Swedish immigration & work-regulation rule lookup. "
            "Queries must be Swedish or English keywords — translate the "
            "user's question before calling. " + _BOUNDARY
        ),
    )

    @mcp.tool(
        description=(
            "Search versioned Swedish immigration/work-permit rules. query: "
            "Swedish or English keywords (translate first). profile: optional "
            "applicability filter (e.g. 'student', 'worker', 'graduate', "
            "'family'). as_of_date: optional ISO date to search historical "
            "rules instead of current ones. Returns each hit with its layered "
            "citation anchor (paragraph-level for law, section-level for "
            "guidance), official source URL, and both time axes (observed vs. "
            "legal validity). " + _BOUNDARY
        )
    )
    def search_rules(
        query: str,
        profile: str | None = None,
        language: str | None = None,
        as_of_date: str | None = None,
    ) -> dict:  # type: ignore[type-arg]
        return tools.search_rules(
            store, query, profile=profile, language=language, as_of_date=as_of_date
        )

    @mcp.tool(
        description=(
            "Get the full version history of one rule unit: every past "
            "wording with its observed and legal-validity windows, newest "
            "last. Use the chunk_id from a search_rules hit. " + _BOUNDARY
        )
    )
    def rule_timeline(chunk_id: str) -> dict:  # type: ignore[type-arg]
        return tools.rule_timeline(store, chunk_id)

    @mcp.tool(
        description=(
            "List rule changes observed since a given ISO date, optionally "
            "filtered by area (e.g. 'work_permit', 'study', 'put'). "
            + _BOUNDARY
        )
    )
    def recent_changes(since: str, area: str | None = None) -> dict:  # type: ignore[type-arg]
        return tools.recent_changes(store, since=since, area=area)

    @mcp.tool(
        description=(
            "Fetch the full parent section for a citation anchor returned by "
            "search_rules (the whole kapitel for a law anchor, the whole page "
            "for a guidance anchor) — for deeper reading beyond one "
            "paragraph. " + _BOUNDARY
        )
    )
    def get_source(anchor: str) -> dict:  # type: ignore[type-arg]
        return tools.get_source(store, anchor)

    return mcp


def main() -> None:
    db_path = default_db_path()
    if not db_path.exists():
        raise SystemExit(
            f"No snapshot database at {db_path}. Set {DB_PATH_ENV} to point "
            "at a vistas snapshot, or run `vistas-build` first."
        )
    store = Store.open(db_path, read_only=True)
    server = build_server(store)
    server.run()


if __name__ == "__main__":
    main()
