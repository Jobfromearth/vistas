# Vistas

Swedish immigration & work-regulation data service for the agent ecosystem.

Every answer carries an official citation anchor and a timeline of when the rule changed. Distributed as a **local MCP server** (`uvx vistas-mcp`) with an openly licensed SQLite snapshot — queries never leave your machine, no server involved.

- Not legal advice (juridisk rådgivning): a sourced regulatory data service.
- Legal sources (SFS via Riksdagen open data) are cited to paragraph level (kap. + §); agency guidance is cited to page + section level, and every result says which.
- Rules are versioned on two time axes: when we observed the content, and (where reliably extractable) when it legally took effect. Old versions are never deleted.

See `瑞典移民助手-项目计划书.md` (project plan, Chinese), `CONTEXT.md` (domain glossary) and `docs/adr/` for the architecture decisions.

## Development

```
uv sync
uv run pytest
uv run mypy
uv run ruff check
```
