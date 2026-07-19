# Vistas

[![CI](https://github.com/Jobfromearth/vistas/actions/workflows/ci.yml/badge.svg)](https://github.com/Jobfromearth/vistas/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**[中文](README-zh.md)**

Swedish immigration & work-regulation data service for the agent ecosystem — every answer carries an official citation and a timeline of when the rule changed.

Not a chatbot, not a web app: a **local MCP server**. It runs on your own machine against an openly licensed SQLite snapshot. Your queries never leave your machine — there is no backend to send them to. (Not on PyPI yet, so it's `uv run vistas-mcp` from a clone today, not `uvx vistas-mcp` — see Quick Start.)

- **Not legal advice** (inte juridisk rådgivning) — a sourced regulatory data service only. Doesn't judge individual cases ("will my application be approved"); returns only the rules themselves, each with a citation. No citable answer → explicit "no data," never a guess.
- **Layered citations, honestly.** Legal sources (SFS via Riksdagen open data) are cited to paragraph level (kap. + §). Agency guidance is cited to page + section level. Every result says which kind it is — no pretending guidance has the precision of statute.
- **Two time axes, not one.** Every rule version carries an *observed* window (when our crawl saw this content) and, only where the source states it explicitly, a *legal validity* window (when it actually took effect). The two are never conflated — see [ADR-0002](docs/adr/0002-bitemporal-rule-model.md).
- **Zero personal data by construction**, not by policy. Your query never leaves your machine, so there's nothing to collect. See [ADR-0001](docs/adr/0001-local-first-mcp-distribution.md).
- **Fully open dataset.** The versioned snapshot ships under **CC-BY** (attribution to source, required by Migrationsverket's own terms — see [`docs/research/migrationsverket-villkor.md`](docs/research/migrationsverket-villkor.md)) — copy it, fork it, build on it. See [ADR-0004](docs/adr/0004-fully-open-dataset.md).

## Status

Implemented and tested end-to-end against the real [Riksdagen open data API](https://data.riksdagen.se) and [migrationsverket.se](https://www.migrationsverket.se):

| Milestone | What | Status |
|---|---|---|
| M1 — data pipeline | Riksdagen SFS ingestion (Utlänningslagen 2005:716), §-level chunking with legal-date extraction; Migrationsverket guidance-page ingestion — full coverage of the plan's target visa-question set (study permit, job-seeking permit, study-to-work conversion, work permit, PUT, family permit, tourism, visiting friends/family — 8 pages), section-level chunking; bitemporal version chains for both. Two of those areas (`job_seeking`, `family`) are guidance-only for now — Riksdagen's chapter-to-area map hasn't been extended to tag matching statute chapters, so a search filtered to those areas won't surface law text, only guidance | ✅ done |
| M2 — MCP minimal | FTS5 lexical retrieval, stdio server | ✅ done |
| M3 — versioning tools | `rule_timeline`, `recent_changes` (ahead of schedule); SKILL.md (also served as the `vistas://skill` MCP resource); `topic` lookup, real profile tagging still to-do | 🚧 partial |
| M4 — eval & CI gates | GitHub Actions CI (mypy/ruff/pytest, citation-accuracy and version-chain gates); curated QA set (`tests/eval/`, retrieval-correctness + no-data dimensions, runs on the daily pipeline); real Chinese-translation eval, response-time tracking still to-do | 🚧 partial |
| M5 — release | Publish to PyPI, ship snapshot on GitHub Releases | ⏳ not yet published |
| M6 — expansion | Cross-border tax (Skatteverket/SINK), more Migrationsverket P0 pages, rättsliga ställningstaganden | ⏳ not implemented |

**Compliance status:** unlike statute text, agency-authored prose isn't automatically copyright-free, so per [ADR-0004](docs/adr/0004-fully-open-dataset.md) full-text redistribution required verifying each site's terms first. That verification is done for migrationsverket.se's main site — full-text redistribution under **CC-BY** (attribution required) is confirmed permitted, see [`docs/research/migrationsverket-villkor.md`](docs/research/migrationsverket-villkor.md). The `rättsliga ställningstaganden` legal-position documents (hosted on the separate Lifos platform) got a follow-up check ([`docs/research/migrationsverket-lifos-villkor.md`](docs/research/migrationsverket-lifos-villkor.md)): no explicit license was found, but there's a real statutory argument (Swedish Copyright Act §9 or §26a — the same copyright-exemption category already used for SFS law text) that they're free to reproduce regardless. That's a legal inference, not case law, so ingestion stays gated until a pre-M5 legal review confirms it.

**Retrieval accuracy check:** a real, scripted evaluation now exists — [`tests/eval/qa_set.yaml`](tests/eval/qa_set.yaml), 17 questions grounded in actually-ingested content (each one's "correct answer" is the real chunk it was written from), including two `no_data` cases for out-of-scope questions. Runs on the daily pipeline against a freshly built snapshot (network-dependent, so it's not in the fast per-PR `ci.yml` gate — see the workflow's comments for why). Currently 17/17. Not the full 50-100-question target from the plan yet, and it tests "does retrieval find the right chunk given an already-correctly-translated query," not "can an LLM translate a Chinese question correctly" — that needs a live model call and is still a manual/nightly-tier gap, not automated. Building this surfaced two real, worth-knowing retrieval quirks (documented inline in the YAML): near-duplicate boilerplate across pages defeats generic queries, and the pure-AND query design (ADR-0003) means one extra word not in the source text can turn a hit into a miss — both are why [SKILL.md](SKILL.md) tells a calling agent to retry with different keywords on `no_data` rather than giving up.

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

Aimed at both humans and coding agents (Claude Code, Codex, etc.) — if you're
an agent reading this to set Vistas up, run these in order; the last step
fails on purpose with a self-explanatory message if you skip the first two.

```
git clone https://github.com/Jobfromearth/vistas.git
cd vistas
uv sync                      # installs dependencies
uv run vistas-build          # builds a local snapshot from Riksdagen + Migrationsverket (~10s, live network)
uv run vistas-mcp            # sanity check: starts the stdio server: Ctrl-C once it's running
```

### Connect an MCP client

**Claude Code** — this repo ships a project-level `.mcp.json`, so opening
this directory in Claude Code (or pointing it at the clone) offers to connect
automatically. To register it manually instead, or from outside the repo:

```
claude mcp add vistas -- uv run --directory /path/to/vistas vistas-mcp
```

**Codex CLI** — add to `~/.codex/config.toml` (check `codex mcp --help` for
your installed version's exact syntax, this has moved before):

```toml
[mcp_servers.vistas]
command = "uv"
args = ["run", "--directory", "/path/to/vistas", "vistas-mcp"]
```

**Any other MCP client** — point it at the command `uv run vistas-mcp` with
this repo as the working directory (stdio transport).

Once connected, read the `vistas://skill` resource (or [SKILL.md](SKILL.md)
directly) before making tool calls — it covers query phrasing and how to
present citations correctly.

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
