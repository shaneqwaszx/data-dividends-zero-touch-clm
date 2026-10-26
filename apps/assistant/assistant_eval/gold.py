"""Gold labels: which allowed lines a good answer to each question shows.

Labels belong to the owner/team (decision A-6). The harness only writes **stubs** (every
turn ``status: "stub"``, nothing selected) and checks labels the owner writes. A labelled
turn names line ids from the frozen snapshot:

- ``relevant``: the lines a good answer may show;
- ``primary``: the line(s) a good answer should start with (a subset of ``relevant``);
- ``must_not``: lines that would mislead here (never also relevant);
- ``expect_fallback``: true when no allowed line answers the question, so the case-data
  answer is the right outcome.

``lock`` freezes labelled gold against its snapshot. Model-quality scores use only locked
owner labels. ``synthetic-self-test`` gold is made by a fixed rule in tests and the
``--self-test`` run; it checks the harness and is never a model-quality label.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .snapshot import SnapshotSet

SCHEMA = "assistant-eval-gold/1"
STUB_NOTE = (
    "STUB - NOT LABELLED. Gold labels are written by the owner/team only (decision A-6). "
    "Fill relevant/primary/must_not/expect_fallback with line ids from snapshots.json "
    "(scripts/evaluate_answers.py worksheet), set status to labelled and labelled_by, then "
    "run scripts/evaluate_answers.py lock."
)
SELF_TEST_LABELLER = "SYNTHETIC-SELF-TEST (fixed rule; not a model-quality label)"


class GoldTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["stub", "labelled"] = "stub"
    relevant: tuple[str, ...] = ()
    primary: tuple[str, ...] = ()
    must_not: tuple[str, ...] = ()
    expect_fallback: bool | None = None
    labelled_by: str | None = None
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _coherent(self) -> "GoldTurn":
        if self.status == "stub":
            if self.relevant or self.primary or self.must_not or self.labelled_by:
                raise ValueError("a stub selects nothing and has no labeller")
            if self.expect_fallback is not None:
                raise ValueError("a stub has no expected outcome")
            return self
        if not (self.labelled_by or "").strip():
            raise ValueError("a labelled turn names who labelled it")
        if self.expect_fallback is None:
            raise ValueError("a labelled turn says whether the case-data answer is expected")
        if not set(self.primary) <= set(self.relevant):
            raise ValueError("primary lines must also be relevant")
        if set(self.relevant) & set(self.must_not):
            raise ValueError("a line cannot be both relevant and must_not")
        if self.expect_fallback and self.relevant:
            raise ValueError("an expected case-data answer has no relevant line")
        if not self.expect_fallback and not self.relevant:
            raise ValueError("a model answer needs at least one relevant line")
        return self


class GoldSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_: Literal["assistant-eval-gold/1"] = Field(
        default="assistant-eval-gold/1", alias="schema"
    )
    kind: Literal["owner", "synthetic-self-test"]
    note: str
    snapshot_sha256: str
    turns: dict[str, GoldTurn]

    def labelled(self) -> dict[str, GoldTurn]:
        return {key: turn for key, turn in self.turns.items() if turn.status == "labelled"}

    def to_json(self) -> str:
        return (
            json.dumps(self.model_dump(mode="json", by_alias=True), indent=1, sort_keys=True) + "\n"
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def check_against(gold: GoldSet, snapshots: SnapshotSet) -> list[str]:
    """Problems that stop this gold from scoring against these snapshots (empty: none)."""

    problems: list[str] = []
    if gold.snapshot_sha256 != snapshots.sha256():
        problems.append("gold was written for different snapshots")
    for key, turn in gold.labelled().items():
        frozen = snapshots.turns.get(key)
        if frozen is None:
            problems.append(f"{key}: not a snapshot turn")
            continue
        offered = set(frozen.offered_ids())
        unknown = set(turn.relevant) | set(turn.must_not)
        if unknown - offered:
            problems.append(f"{key}: names lines this question did not offer")
    return problems


def stubs(snapshots: SnapshotSet, existing: GoldSet | None = None) -> GoldSet:
    """A stub for every snapshot turn. Labelled turns of ``existing`` owner gold are kept
    unchanged (a later ``lock`` reports any that no longer fit the snapshots)."""

    kept = existing.labelled() if existing is not None and existing.kind == "owner" else {}
    return GoldSet(
        kind="owner",
        note=STUB_NOTE,
        snapshot_sha256=snapshots.sha256(),
        turns={key: kept.get(key, GoldTurn()) for key in snapshots.turns},
    )


class GoldLock(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gold_sha256: str
    snapshot_sha256: str
    labelled_turns: int
    total_turns: int
    locked_at: str


class GoldError(ValueError):
    """Gold that cannot be locked or used for scoring."""


def lock(gold: GoldSet, snapshots: SnapshotSet) -> GoldLock:
    if gold.kind != "owner":
        raise GoldError("only owner/team gold can be locked")
    if not gold.labelled():
        raise GoldError("nothing is labelled yet: the owner/team writes the labels")
    problems = check_against(gold, snapshots)
    if problems:
        raise GoldError("; ".join(problems))
    return GoldLock(
        gold_sha256=gold.sha256(),
        snapshot_sha256=snapshots.sha256(),
        labelled_turns=len(gold.labelled()),
        total_turns=len(gold.turns),
        locked_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def verify(gold: GoldSet, gold_lock: GoldLock, snapshots: SnapshotSet) -> None:
    if gold.kind != "owner":
        raise GoldError("model-quality scores need owner/team gold")
    if gold_lock.gold_sha256 != gold.sha256():
        raise GoldError("the gold changed after it was locked")
    if gold_lock.snapshot_sha256 != snapshots.sha256():
        raise GoldError("the gold was locked against different snapshots")
    problems = check_against(gold, snapshots)
    if problems:
        raise GoldError("; ".join(problems))


def self_test_gold(snapshots: SnapshotSet) -> GoldSet:
    """Gold made by a fixed rule, to check the evaluator only (never model quality).

    Rule: the first offered line of each question is primary and relevant; the first offered
    knowledge line is relevant too (or, when no knowledge was offered, the second line), so
    knowledge selection and citations are exercised; the last offered line is must_not when
    it is not already relevant and there are at least three lines.
    """

    turns: dict[str, GoldTurn] = {}
    for key, frozen in snapshots.turns.items():
        ids = frozen.offered_ids()
        if not ids:
            turns[key] = GoldTurn(
                status="labelled", expect_fallback=True, labelled_by=SELF_TEST_LABELLER
            )
            continue
        knowledge = [item.id for item in frozen.offered if item.tag is not None]
        relevant = [ids[0]]
        second = knowledge[0] if knowledge else (ids[1] if len(ids) > 1 else None)
        if second is not None and second not in relevant:
            relevant.append(second)
        last = ids[-1]
        turns[key] = GoldTurn(
            status="labelled",
            relevant=tuple(relevant),
            primary=(ids[0],),
            must_not=(last,) if len(ids) >= 3 and last not in relevant else (),
            expect_fallback=False,
            labelled_by=SELF_TEST_LABELLER,
        )
    return GoldSet(
        kind="synthetic-self-test",
        note="SYNTHETIC EVALUATOR SELF-TEST GOLD - checks the harness only.",
        snapshot_sha256=snapshots.sha256(),
        turns=turns,
    )
