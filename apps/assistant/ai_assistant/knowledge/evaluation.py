"""Measure retrieval on a labelled set of questions (recall@k and correct "nothing applies")."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .retrieval import CaseContext, Retriever


@dataclass(frozen=True)
class EvalResult:
    questions: int
    recall_at_k: float
    # Questions that expect nothing: share where retrieval returned no confident entry.
    correct_nothing_rate: float
    misses: list[dict[str, Any]]


def load_labelled(path: Path) -> list[dict[str, Any]]:
    return list(json.loads(path.read_text(encoding="utf-8")))


def evaluate(
    retriever: Retriever,
    items: list[dict[str, Any]],
    *,
    k: int = 3,
    role: str | None = "RELATIONSHIP_MANAGER",
    team: str | None = "TEAM_A",
) -> EvalResult:
    found = expected = 0
    nothing_ok = nothing_total = 0
    misses: list[dict[str, Any]] = []
    for item in items:
        ctx = CaseContext(
            blocker_codes=tuple(item["context"].get("blocker_codes", ())),
            fields=tuple(item["context"].get("fields", ())),
            stages=tuple(item["context"].get("stages", ())),
        )
        result = retriever.retrieve(item["question"], ctx, role=role, team=team)
        ranked = sorted(result.hits, key=lambda h: -h.score)
        top = [hit.entry.entry_id for hit in ranked[:k]]
        want = item["expect"]
        if not want:
            nothing_total += 1
            if result.confidence != "high":
                nothing_ok += 1
            else:
                misses.append({"question": item["question"], "expected": [], "got": top})
            continue
        hit_count = sum(1 for entry_id in want if entry_id in top)
        found += hit_count
        expected += len(want)
        if hit_count < len(want):
            misses.append({"question": item["question"], "expected": want, "got": top})
    return EvalResult(
        questions=len(items),
        recall_at_k=found / expected if expected else 1.0,
        correct_nothing_rate=nothing_ok / nothing_total if nothing_total else 1.0,
        misses=misses,
    )
