"""QA-set evaluation — plan §6's "检索正确性" and "无数据行为" dimensions,
run as real script-verified checks against a curated question set
(tests/eval/qa_set.yaml), not yet the full 50-100-question target but a
real first installment grounded in actually-ingested content.

Live-marked (needs a full snapshot build: network + ~10-20s) — deliberately
NOT part of the fast per-PR CI gate (ci.yml stays network-free by design).
Runs on the daily-pipeline schedule instead, against a freshly built
snapshot, so drift/regressions get caught continuously without adding
network flakiness to every PR. Set VISTAS_EVAL_DB to point this at an
already-built snapshot instead of building a fresh one (what the daily
pipeline does, to avoid building twice).

What this does NOT test: whether an LLM can correctly translate the
`question_zh` field into the `query` field — `query` is a pre-vetted,
already-translated keyword string (ADR-0003: translation is the calling
agent's job, not Vistas'). Testing real translation quality needs a live
model call and belongs in the separate, non-CI-gated end-to-end tier
(plan §6's LLM-as-Judge row) — not built yet.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from vistas.pipeline.build import build_guidance_snapshot, build_snapshot
from vistas.retrieval import search
from vistas.store import Store

QA_SET: list[dict[str, Any]] = yaml.safe_load(
    (Path(__file__).parent / "qa_set.yaml").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def store(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Store]:
    db_path = os.environ.get("VISTAS_EVAL_DB")
    if db_path:
        s = Store.open(db_path, read_only=True)
        yield s
        s.close()
        return

    # pytest's own tmp_path_factory (not tempfile.TemporaryDirectory): the
    # latter tries to force-delete its directory as soon as the fixture
    # generator resumes past `yield`, which races Windows' SQLite file lock
    # even after store.close() — PermissionError: WinError 32. pytest
    # manages its own retention instead of an immediate forced unlink.
    db_file = tmp_path_factory.mktemp("eval") / "eval.db"
    s = Store.open(db_file)
    build_snapshot(s)
    build_guidance_snapshot(s)
    yield s
    s.close()


@pytest.mark.live
@pytest.mark.parametrize("entry", QA_SET, ids=[e["id"] for e in QA_SET])
def test_qa_entry(store: Store, entry: dict[str, Any]) -> None:
    hits = search(store, query=entry["query"], limit=10)
    if entry["expect"] == "hit":
        found = [h.version.chunk.chunk_id for h in hits]
        assert entry["chunk_id"] in found, (
            f"{entry['id']}: expected chunk {entry['chunk_id']!r} in top-10 for "
            f"query {entry['query']!r}, got {found}"
        )
    elif entry["expect"] == "no_data":
        found = [h.version.chunk.chunk_id for h in hits]
        assert hits == [], f"{entry['id']}: expected no_data, got hits: {found}"
    else:
        raise ValueError(f"{entry['id']}: unknown expect value {entry['expect']!r}")
