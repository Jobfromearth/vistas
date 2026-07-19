# Contributing to Vistas

Vistas has no telemetry by design — it can't learn from real usage automatically, on purpose. It only gets better through things people do on purpose and in public: reporting a bad answer, or contributing a verified QA pair. Both are welcome.

## Report a bad or outdated answer

If a citation looks wrong, a rule seems out of date, or `search_rules` should have found something and didn't, open an issue: **https://github.com/Jobfromearth/vistas/issues**

Include, if you have them:
- The exact query you sent
- The `chunk_id` and/or `anchor` of the result in question (or "no result" if it should have found something)
- What looks wrong, and what the correct answer should be if you know it

There's no other reporting channel and nothing is collected automatically — this is the only way an incorrect answer gets noticed and fixed.

## Contribute a QA pair

[`tests/eval/qa_set.yaml`](tests/eval/qa_set.yaml) is the project's retrieval-accuracy eval (plan §6, "检索正确性"/"无数据行为") — real questions, checked against a real snapshot on the [daily pipeline](.github/workflows/daily-pipeline.yml). It's small (17 entries) and the plan's target is 50–100, so more entries — especially ones covering topics or phrasings not yet represented, or in Swedish/Chinese — are genuinely useful, not just a formality.

### The rule: ground truth is a real, already-ingested chunk

Every entry's "correct answer" is the actual chunk the question was written *from* — not an independent legal judgment call. This keeps the eval honest about what it's testing (does retrieval find real ingested content) without requiring anyone to verify Migrationsverket's or Riksdagen's own text is correct — that's out of scope by design.

To add an entry:

1. Build a local snapshot if you don't have one: `uv sync && uv run vistas-build`
2. Find a real chunk to write a question about. Either browse `tests/eval/qa_set.yaml` for examples of what's already covered, or query your local snapshot directly:
   ```python
   from vistas.store import Store
   s = Store.open("path/to/snapshot.db", read_only=True)
   for v in s.current_versions():
       if v.chunk.area == "study":  # or whatever area you're targeting
           print(v.chunk.chunk_id, "|", v.chunk.content[:150])
   ```
3. Write a natural question from that chunk's actual content, in `tests/eval/qa_set.yaml`'s format:
   ```yaml
   - id: qa-018  # next number in sequence
     area: study
     chunk_id: "<the real chunk_id you found>"
     expect: hit
     question_en: <natural English phrasing>
     question_zh: <natural Chinese phrasing — documentation only, not sent to search>
     query: <keywords you'd actually send to search_rules — Swedish for legal-source chunks, English for guidance-source chunks; see SKILL.md §2>
     note: <anything worth knowing — what fact the answer contains, a citation detail, etc.>
   ```
   For an out-of-scope question that should return `no_data` (nothing ingested covers it), set `expect: no_data` and `chunk_id: null` instead — see the existing `qa-016`/`qa-017` entries.
4. **Verify it actually passes before opening the PR**:
   ```
   VISTAS_EVAL_DB=path/to/snapshot.db uv run pytest "tests/eval/test_qa_set.py::test_qa_entry[qa-018]" -m live -v
   ```
   If it fails, that's not necessarily wrong — see the regression notes already in `qa_set.yaml` for two real examples (near-duplicate content across pages, and the pure-AND query design's sensitivity to extra words) where the fix was adjusting the query, not the code, before assuming it's a bug.

### Code changes

Standard flow: fork, branch, `uv run pytest -m "not live"` + `uv run mypy` + `uv run ruff check` before opening a PR. See [SKILL.md](SKILL.md) for how the MCP tools are meant to be used — worth reading before proposing a structural change.
