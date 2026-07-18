# Vistas

**[中文](README-zh.md)**

Swedish immigration & work-regulation data service for the agent ecosystem — every answer carries an official citation and a timeline of when the rule changed.

Not a chatbot, not a web app: a **local MCP server**. `uvx vistas-mcp` runs on your own machine against an openly licensed SQLite snapshot. Your queries never leave your machine — there is no backend to send them to.

- **Not legal advice** (inte juridisk rådgivning) — a sourced regulatory data service only. Doesn't judge individual cases ("will my application be approved"); returns only the rules themselves, each with a citation. No citable answer → explicit "no data," never a guess.
- **Layered citations, honestly.** Legal sources (SFS via Riksdagen open data) are cited to paragraph level (kap. + §). Agency guidance is cited to page + section level. Every result says which kind it is — no pretending guidance has the precision of statute.
- **Two time axes, not one.** Every rule version carries an *observed* window (when our crawl saw this content) and, only where the source states it explicitly, a *legal validity* window (when it actually took effect). The two are never conflated — see [ADR-0002](docs/adr/0002-bitemporal-rule-model.md).
- **Zero personal data by construction**, not by policy. Your query never leaves your machine, so there's nothing to collect. See [ADR-0001](docs/adr/0001-local-first-mcp-distribution.md).
- **Fully open dataset.** The versioned snapshot ships under **CC-BY** (attribution to source, required by Migrationsverket's own terms — see [`docs/research/migrationsverket-villkor.md`](docs/research/migrationsverket-villkor.md)) — copy it, fork it, build on it. See [ADR-0004](docs/adr/0004-fully-open-dataset.md).

## Status

Implemented and tested end-to-end against the real [Riksdagen open data API](https://data.riksdagen.se) and [migrationsverket.se](https://www.migrationsverket.se):

| Milestone | What | Status |
|---|---|---|
| M1 — data pipeline | Riksdagen SFS ingestion (Utlänningslagen 2005:716), §-level chunking with legal-date extraction; Migrationsverket guidance-page ingestion (seed page), section-level chunking; bitemporal version chains for both | ✅ done |
| M2 — MCP minimal | FTS5 lexical retrieval, stdio server | ✅ done |
| M3 — versioning tools | `rule_timeline`, `recent_changes` (ahead of schedule); SKILL.md (also served as the `vistas://skill` MCP resource); `topic` lookup, real profile tagging still to-do | 🚧 partial |
| M4 — eval & CI gates | GitHub Actions CI (mypy/ruff/pytest); curated QA set + Chinese end-to-end eval | 🚧 CI skeleton only |
| M5 — release | Publish to PyPI, ship snapshot on GitHub Releases | ⏳ not yet published |
| M6 — expansion | Cross-border tax (Skatteverket/SINK), more Migrationsverket P0 pages, rättsliga ställningstaganden | ⏳ not implemented |

**Compliance status:** unlike statute text, agency-authored prose isn't automatically copyright-free, so per [ADR-0004](docs/adr/0004-fully-open-dataset.md) full-text redistribution required verifying each site's terms first. That verification is done for migrationsverket.se's main site — full-text redistribution under **CC-BY** (attribution required) is confirmed permitted, see [`docs/research/migrationsverket-villkor.md`](docs/research/migrationsverket-villkor.md) — and one seed page (work-permit requirements for employees) is ingested end-to-end; extending coverage to more P0 guidance pages is adding URLs, not new mechanism. The `rättsliga ställningstaganden` legal-position documents (hosted on the separate Lifos platform) remain unverified and stay excluded until checked separately.

Not on PyPI yet — clone and run from source (below) until M5.

## The four tools

| Tool | Purpose |
|---|---|
| `search_rules` | Search current (or historical, via `as_of_date`) rules by keyword, filtered by area/profile |
| `get_source` | Fetch the full parent section (whole kapitel, or whole guidance page) for deeper reading |
| `rule_timeline` | Full version history of one rule unit, with a diff between consecutive versions |
| `recent_changes` | What changed since a given date, optionally filtered by area |

Every result carries: content, a layered citation anchor, the official source URL, both time axes, and the snapshot's build timestamp.

## Quick start (from source)

```
git clone https://github.com/Jobfromearth/vistas.git
cd vistas
uv sync
uv run vistas-build          # builds a local snapshot from Riksdagen + Migrationsverket
uv run vistas-mcp            # starts the stdio MCP server against it
```

Point your MCP client (Claude Code, Codex, etc.) at `uv run vistas-mcp` in this directory.

## Development

```
uv sync
uv run pytest -m "not live"  # offline test suite
uv run mypy
uv run ruff check
```

## Learn more

- [SKILL.md](SKILL.md) — how to use the four tools well (also served live as the `vistas://skill` MCP resource, so any connected client can read it without a local checkout)
- [瑞典移民助手-项目计划书.md](瑞典移民助手-项目计划书.md) — full project plan (Chinese)
- [CONTEXT.md](CONTEXT.md) — domain glossary
- [docs/adr/](docs/adr/) — architecture decisions
