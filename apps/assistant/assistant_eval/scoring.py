"""Deterministic scores for a run: no model is used to judge another.

Because an answer can only show allowed lines, most measures are exact:

- label-free (any run): fallback rate and reasons, line validity (kept lines over all model
  lines), unsafe display (shown lines that are not allowed lines of the question; must be 0),
  cut-short rate, latency, prompt size, stability across repetitions, consistency of the
  same question asked late in a conversation and on its own;
- gold-based (only with gold): precision, recall and F1 of the shown lines against the
  relevant lines, primary-line hits, must-not violations, correct case-data answers, and
  whether the model's cited entries are relevant ones.

Conventions: a question where nothing was shown has precision 0 (and so F1 0) when it had
relevant lines; two selections that are both empty (both answers fell back) count as
consistent (Jaccard 1.0). Owner gold is used only once its lock verifies.

Result kinds keep evaluator checks apart from model results:

- ``EVALUATOR_SELF_TEST``: a fixed-rule selector or synthetic gold; says nothing about a model;
- ``MODEL_RUN_UNLABELLED``: a real (local) model without locked owner gold; label-free only;
- ``MODEL_EVALUATION``: a real (local) model scored against locked owner/team gold.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Literal

from .gold import GoldError, GoldLock, GoldSet, verify
from .runner import RunResult, TurnResult
from .scenarios import ScenarioSet
from .snapshot import SnapshotSet

ResultKind = Literal["EVALUATOR_SELF_TEST", "MODEL_RUN_UNLABELLED", "MODEL_EVALUATION"]
BANNERS: dict[ResultKind, str] = {
    "EVALUATOR_SELF_TEST": (
        "EVALUATOR SELF-TEST: a fixed-rule selector and/or synthetic gold checks the harness. "
        "These numbers say nothing about any real model."
    ),
    "MODEL_RUN_UNLABELLED": (
        "MODEL RUN WITHOUT LOCKED OWNER GOLD: label-free measurements only; no quality score."
    ),
    "MODEL_EVALUATION": (
        "MODEL EVALUATION against locked owner/team gold on synthetic scenarios (LOCAL "
        "evidence, not Live)."
    ),
}


@dataclass(frozen=True)
class Scores:
    result_kind: ResultKind
    banner: str
    overall: dict[str, Any]
    gold: dict[str, Any] | None
    by_tag: dict[str, dict[str, Any]]
    stability: float | None
    consistency: float | None
    drifted_turns: tuple[str, ...]


def result_kind(model: str, gold: GoldSet | None) -> ResultKind:
    if model.startswith("self-test") or (gold is not None and gold.kind != "owner"):
        return "EVALUATOR_SELF_TEST"
    if gold is None:
        return "MODEL_RUN_UNLABELLED"
    return "MODEL_EVALUATION"


def _rate(part: float, whole: float) -> float | None:
    return round(part / whole, 4) if whole else None


def _percentile(values: Sequence[int], share: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def label_free(turns: Sequence[TurnResult]) -> dict[str, Any]:
    kept = sum(int(t.metrics["kept_lines"]) for t in turns)
    left_out = sum(int(t.metrics["left_out_lines"]) for t in turns)
    totals = [
        int(t.metrics["timings_ms"]["total"])
        for t in turns
        if t.metrics["timings_ms"]["total"] is not None
    ]
    firsts = [
        int(t.metrics["timings_ms"]["first_displayed_line"])
        for t in turns
        if t.metrics["timings_ms"]["first_displayed_line"] is not None
    ]
    parts: dict[str, float] = defaultdict(float)
    for turn in turns:
        for name, size in turn.metrics["part_chars"].items():
            parts[name] += int(size)
    count = len(turns)
    return {
        "answers": count,
        "model_answers": sum(1 for t in turns if t.answered_by == "model"),
        "fallback_rate": _rate(sum(1 for t in turns if t.answered_by == "case_data"), count),
        "fallback_reasons": dict(sorted(Counter(t.fallback_reason for t in turns).items())),
        "line_validity_rate": _rate(kept, kept + left_out),
        "unsafe_display": sum(t.unmapped for t in turns),
        "cut_short_rate": _rate(sum(1 for t in turns if t.metrics["cut_short"]), count),
        "latency_total_ms_p50": _percentile(totals, 0.5),
        "latency_total_ms_p95": _percentile(totals, 0.95),
        "latency_first_shown_ms_p50": _percentile(firsts, 0.5),
        "latency_first_shown_ms_p95": _percentile(firsts, 0.95),
        "mean_offered_lines": round(sum(len(t.offered) for t in turns) / count, 2)
        if count
        else None,
        "mean_prompt_chars": {
            name: round(total / count, 1) for name, total in sorted(parts.items())
        }
        if count
        else {},
    }


def _entries_of(lines: Iterable[str], snapshots: SnapshotSet) -> set[str]:
    out: set[str] = set()
    for line_id in lines:
        line = snapshots.lines.get(line_id)
        if line is not None and line.entry_id:
            out.add(line.entry_id)
    return out


def gold_based(
    turns: Sequence[TurnResult], gold: GoldSet, snapshots: SnapshotSet
) -> dict[str, Any]:
    labelled = gold.labelled()
    tp = shown_total = relevant_total = 0
    f1s: list[float] = []
    primary_hits = primary_turns = must_not = 0
    fallback_expected = fallback_correct = missed_answers = 0
    cited_turns = cited_correct = 0
    scored = drifted = unlabelled = 0
    for turn in turns:
        label = labelled.get(turn.key)
        if label is None:
            unlabelled += 1
            continue
        if turn.drift:
            drifted += 1
            continue
        scored += 1
        if label.expect_fallback:
            fallback_expected += 1
            fallback_correct += turn.answered_by == "case_data"
            continue
        if turn.answered_by != "model":
            missed_answers += 1
        selected = set(turn.shown)
        relevant = set(label.relevant)
        hits = len(selected & relevant)
        tp += hits
        shown_total += len(selected)
        relevant_total += len(relevant)
        precision = hits / len(selected) if selected else 0.0
        recall = hits / len(relevant)
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
        if label.primary:
            primary_turns += 1
            primary_hits += bool(turn.shown) and turn.shown[0] in label.primary
        must_not += len(selected & set(label.must_not))
        # Only the model's own citations: a case-data answer cites by a fixed rule.
        if turn.answered_by == "model" and turn.cited_entries:
            cited_turns += 1
            cited_correct += set(turn.cited_entries) <= _entries_of(label.relevant, snapshots)
    # Nothing shown where something was relevant is precision 0, not "undefined".
    precision_micro = _rate(tp, shown_total) if shown_total else (0.0 if relevant_total else None)
    recall_micro = _rate(tp, relevant_total)
    f1_micro: float | None = None
    if precision_micro is not None and recall_micro is not None:
        total = precision_micro + recall_micro
        f1_micro = round(2 * precision_micro * recall_micro / total, 4) if total else 0.0
    return {
        "gold_kind": gold.kind,
        "turns_scored": scored,
        "turns_unlabelled": unlabelled,
        "turns_excluded_for_drift": drifted,
        "precision_micro": precision_micro,
        "recall_micro": recall_micro,
        "f1_micro": f1_micro,
        "f1_macro": round(sum(f1s) / len(f1s), 4) if f1s else None,
        "primary_hit_rate": _rate(primary_hits, primary_turns),
        "must_not_violations": must_not,
        "expected_case_data_turns": fallback_expected,
        "expected_case_data_correct_rate": _rate(fallback_correct, fallback_expected),
        "expected_model_answer_but_fell_back": missed_answers,
        "citation_turns": cited_turns,
        "citation_correct_rate": _rate(cited_correct, cited_turns),
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def stability(turns: Sequence[TurnResult]) -> float | None:
    by_key: dict[str, list[set[str]]] = defaultdict(list)
    for turn in turns:
        by_key[turn.key].append(set(turn.shown))
    values = [
        _jaccard(a, b)
        for runs in by_key.values()
        if len(runs) > 1
        for a, b in combinations(runs, 2)
    ]
    return round(sum(values) / len(values), 4) if values else None


def consistency(turns: Sequence[TurnResult], scenario_set: ScenarioSet) -> float | None:
    shown = {(turn.key, turn.rep): set(turn.shown) for turn in turns}
    reps = {turn.rep for turn in turns}
    values = [
        _jaccard(shown[(pair.conversation, rep)], shown[(pair.single, rep)])
        for pair in scenario_set.consistency_pairs
        for rep in sorted(reps)
        if (pair.conversation, rep) in shown and (pair.single, rep) in shown
    ]
    return round(sum(values) / len(values), 4) if values else None


def score(
    run: RunResult,
    scenario_set: ScenarioSet,
    snapshots: SnapshotSet,
    gold: GoldSet | None = None,
    gold_lock: GoldLock | None = None,
) -> Scores:
    """Score a run. Owner gold is used only with its lock, which is verified here."""

    if gold is not None and gold.kind == "owner":
        if gold_lock is None:
            raise GoldError("owner gold is used only once it is locked")
        verify(gold, gold_lock, snapshots)
    kind = result_kind(run.model, gold)
    tags_of = {
        scenario.turn_key(index): scenario.tags
        for scenario in scenario_set.scenarios
        for index in range(len(scenario.questions))
    }
    by_tag: dict[str, list[TurnResult]] = defaultdict(list)
    for turn in run.turns:
        for tag in tags_of.get(turn.key, ()):
            by_tag[tag].append(turn)
    tag_scores: dict[str, dict[str, Any]] = {}
    for name, turns in sorted(by_tag.items()):
        entry = label_free(turns)
        if gold is not None:
            entry["gold"] = gold_based(turns, gold, snapshots)
        tag_scores[name] = entry
    return Scores(
        result_kind=kind,
        banner=BANNERS[kind],
        overall=label_free(run.turns),
        gold=gold_based(run.turns, gold, snapshots) if gold is not None else None,
        by_tag=tag_scores,
        stability=stability(run.turns),
        consistency=consistency(run.turns, scenario_set),
        drifted_turns=tuple(sorted({turn.key for turn in run.turns if turn.drift})),
    )
