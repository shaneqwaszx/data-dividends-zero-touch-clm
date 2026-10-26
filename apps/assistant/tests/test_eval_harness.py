"""Offline evaluation harness (assistant_eval): E0 evaluator self-tests and safeguards.

E0 checks the harness, not a model: fixed-rule selectors with synthetic self-test gold must
score exactly as their rule predicts. Nothing here is a model-quality result. No test may
open a connection to a non-loopback host (``_no_remote_connections``).
"""

import asyncio
import socket
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import anyio
import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guide import RULE_PLAIN
from ai_assistant.llm import ChatModel, ModelAnswer, Piece
from assistant_eval import gold as gold_mod
from assistant_eval.models import (
    Capture,
    GoldSelector,
    InjectionSelector,
    ProseSelector,
    RandomSelector,
    RemoteModelRefusedError,
    SelectorModel,
    local_model,
)
from assistant_eval.report import markdown, report_data, write
from assistant_eval.runner import RunResult, Workspace, build_snapshots, run
from assistant_eval.scenarios import EVAL_FIXTURES, ScenarioSet, load_scenarios
from assistant_eval.scoring import score
from assistant_eval.snapshot import (
    SnapshotSet,
    knowledge_line_id,
    prompt_fingerprint,
)
from assistant_eval.variants import INJECTED_INSTRUCTION, case_inputs

ASSISTANT = Path(__file__).resolve().parents[1]
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class RemoteConnectionBlocked(AssertionError):
    """A test tried to reach a host that is not this machine."""


@pytest.fixture(scope="module", autouse=True)
def _no_remote_connections() -> Iterator[list[object]]:
    """Fail on any attempt to reach a host that is not this machine: blocking and
    non-blocking sockets, asyncio connections (the async HTTP client) and name lookups."""

    attempts: list[object] = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo
    real_create_connection = asyncio.base_events.BaseEventLoop.create_connection

    def check(host: object, what: object) -> None:
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host is not None and host not in LOOPBACK:
            attempts.append(what)
            raise RemoteConnectionBlocked("the evaluation harness tried to reach a remote host")

    def connect(self: socket.socket, address: Any) -> None:
        check(address[0] if isinstance(address, tuple) else None, address)
        real_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        check(address[0] if isinstance(address, tuple) else None, address)
        return real_connect_ex(self, address)

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        check(host, host)
        return real_getaddrinfo(host, *args, **kwargs)

    async def create_connection(self: Any, *args: Any, **kwargs: Any) -> Any:
        host = kwargs.get("host", args[1] if len(args) > 1 else None)
        check(host, host)
        return await real_create_connection(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, "connect", connect)
        patch.setattr(socket.socket, "connect_ex", connect_ex)
        patch.setattr(socket, "getaddrinfo", getaddrinfo)
        patch.setattr(asyncio.base_events.BaseEventLoop, "create_connection", create_connection)
        yield attempts
    assert attempts == []


def _blocked(error: BaseException | None, depth: int = 0) -> bool:
    """Whether the guard's refusal is ``error`` or inside it (anyio wraps connection errors)."""

    if error is None or depth > 10:
        return False
    if isinstance(error, RemoteConnectionBlocked):
        return True
    if isinstance(error, BaseExceptionGroup) and any(
        _blocked(inner, depth + 1) for inner in error.exceptions
    ):
        return True
    return _blocked(error.__cause__, depth + 1) or _blocked(error.__context__, depth + 1)


def test_the_connection_guard_blocks_remote_hosts(_no_remote_connections: list[object]) -> None:
    """192.0.2.1 is reserved for documentation: nothing is there even if the guard failed."""

    async def connect_async() -> None:
        with anyio.fail_after(5):
            await anyio.connect_tcp("192.0.2.1", 80)

    try:
        with pytest.raises(BaseException) as raised:
            anyio.run(connect_async)
        assert _blocked(raised.value)
        with pytest.raises(RemoteConnectionBlocked):
            socket.create_connection(("192.0.2.1", 80), timeout=5)
        with pytest.raises(RemoteConnectionBlocked):
            socket.getaddrinfo("example.com", 443)
    finally:
        _no_remote_connections.clear()


@pytest.fixture(scope="module")
def scenarios() -> ScenarioSet:
    return load_scenarios()


@pytest.fixture(scope="module")
def workspace() -> Iterator[Workspace]:
    with Workspace() as space:
        yield space


@pytest.fixture(scope="module")
def snapshots(scenarios: ScenarioSet, workspace: Workspace) -> SnapshotSet:
    """Freshly built from the current code (not the committed fixture)."""

    return build_snapshots(scenarios, workspace=workspace)


@pytest.fixture(scope="module")
def self_test_gold(snapshots: SnapshotSet) -> gold_mod.GoldSet:
    return gold_mod.self_test_gold(snapshots)


def _run(
    scenarios: ScenarioSet,
    workspace: Workspace,
    selector: Any,
    snapshots: SnapshotSet,
    reps: int = 1,
) -> RunResult:
    return run(
        scenarios,
        lambda capture: SelectorModel(selector, capture),
        reps=reps,
        snapshots=snapshots,
        workspace=workspace,
    )


# --- scenarios and variants ----------------------------------------------------------------


def test_the_scenario_set_covers_the_planned_situations(scenarios: ScenarioSet) -> None:
    single = [s for s in scenarios.scenarios if not s.conversation]
    conversations = [s for s in scenarios.scenarios if s.conversation]
    assert len(single) >= 15 and all(len(s.questions) == 4 for s in single)
    assert len(conversations) >= 5 and all(len(s.questions) == 4 for s in conversations)
    assert sum(1 for s in scenarios.scenarios if "adversarial" in s.tags) >= 5
    assert {tag for s in scenarios.scenarios for tag in s.tags} == {
        "normal",
        "ambiguous",
        "missing_evidence",
        "conflicting_evidence",
        "adversarial",
        "multi_turn",
    }
    assert scenarios.consistency_pairs


def _facts(base: str, *variants: str) -> dict[str, Any]:
    case = case_inputs(base, variants)
    return build_case_facts(CaseSnapshot(case.summary, case.documents, case.actor))


def test_variants_change_the_case_as_described() -> None:
    assert _facts("garden_address_conflict", "no_documents")["documents"] == []
    done = _facts("garden_address_conflict", "completed")
    assert done["overall"]["status"] == "completed" and done["blockers"] == []
    assert done["still_needed_before_goldtier"] == []
    no_action = _facts("garden_address_conflict", "no_action_for_viewer")["blockers"][0]
    assert no_action["actions_available_to_this_user"] == [] and no_action["why_no_action"]
    failed = _facts("garden_address_conflict", "technical_failure")
    assert failed["system_problem"]["code"] == "SYNTHETIC_REGISTRY_TIMEOUT"
    uncertain = _facts("garden_address_conflict", "goldtier_uncertain")["blockers"][0]
    assert uncertain["plain_explanation"] == RULE_PLAIN["BPD-TARGET-UNCERTAIN-1"]
    assert uncertain["where_on_the_case_page"] == "Final review & send"
    assert uncertain["actions_available_to_this_user"] == []
    injected = _facts("garden_address_conflict", "instruction_in_document_value")
    values = [f["value_read_from_document"] for d in injected["documents"] for f in d["fields"]]
    assert INJECTED_INSTRUCTION in values
    with pytest.raises(ValueError):
        case_inputs("garden_waiting_for_documents", ("goldtier_uncertain",))


def test_variants_never_change_the_saved_fixtures() -> None:
    before = case_inputs("garden_address_conflict")
    case_inputs("garden_address_conflict", ("completed", "instruction_in_document_value"))
    assert case_inputs("garden_address_conflict") == before


# --- snapshots -----------------------------------------------------------------------------


def test_the_committed_snapshots_and_gold_stubs_fit_the_scenarios(scenarios: ScenarioSet) -> None:
    committed = SnapshotSet.model_validate_json(
        (EVAL_FIXTURES / "snapshots.json").read_text(encoding="utf-8")
    )
    assert sorted(committed.turns) == sorted(scenarios.turn_keys())
    for turn in committed.turns.values():
        assert all(item.id in committed.lines for item in turn.offered)
    gold = gold_mod.GoldSet.model_validate_json(
        (EVAL_FIXTURES / "gold.json").read_text(encoding="utf-8")
    )
    assert gold.kind == "owner"
    assert gold.snapshot_sha256 == committed.sha256()
    assert sorted(gold.turns) == sorted(committed.turns)
    # Decision A-6: the harness never labels; the owner/team writes every label.
    assert gold.labelled() == {}
    assert "STUB" in gold.note
    assert not (EVAL_FIXTURES / "gold.lock.json").exists()


def test_snapshots_are_deterministic(
    scenarios: ScenarioSet, workspace: Workspace, snapshots: SnapshotSet
) -> None:
    again = build_snapshots(scenarios, workspace=workspace)
    assert again.sha256() == snapshots.sha256()


@pytest.mark.parametrize("days", [1, 180])
def test_snapshots_do_not_change_with_the_date(
    days: int,
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retrieval recency reads "now"; the harness fixes it, so a later date changes nothing."""

    later = datetime.now(UTC) + timedelta(days=days)

    class Later(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> "Later":
            return cls.fromtimestamp(later.timestamp(), tz)

    monkeypatch.setattr("ai_assistant.knowledge.retrieval.datetime", Later)
    assert build_snapshots(scenarios, workspace=workspace).sha256() == snapshots.sha256()


class RecordingModel:
    """Records the exact messages the service sent for each turn."""

    name = "self-test-recording"

    def __init__(self) -> None:
        self.key = ""
        self.sent: dict[str, list[dict[str, str]]] = {}

    def begin(self, key: str, rep: int) -> None:
        self.key = key

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.sent[self.key] = messages
        return ModelAnswer("")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self.sent[self.key] = messages
        yield Piece(cut_short=False)

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


def test_a_snapshot_is_exactly_what_the_model_was_sent(
    scenarios: ScenarioSet, workspace: Workspace, snapshots: SnapshotSet
) -> None:
    recorders: list[RecordingModel] = []

    def make(capture: Capture) -> ChatModel:
        recorders.append(RecordingModel())
        return recorders[-1]

    run(scenarios, make, workspace=workspace)
    sent = {key: messages for r in recorders for key, messages in r.sent.items()}
    assert sorted(sent) == sorted(snapshots.turns)
    for key, messages in sent.items():
        assert prompt_fingerprint(messages) == snapshots.turns[key].prompt_fingerprint
        offered = snapshots.turns[key]
        knowledge = next(
            (m["content"] for m in messages if m["content"].startswith("KNOWLEDGE")), ""
        )
        for item in offered.offered:
            if item.tag is not None:
                line = snapshots.lines[item.id]
                assert f"{line.text} [{item.tag}]" in knowledge


def test_line_ids_do_not_depend_on_retrieval_order(snapshots: SnapshotSet) -> None:
    assert knowledge_line_id("guidance.x", 1, "A sentence.") == knowledge_line_id(
        "guidance.x", 1, "A sentence."
    )
    assert knowledge_line_id("guidance.x", 1, "A sentence.") != knowledge_line_id(
        "guidance.x", 2, "A sentence."
    )
    # The same sentence carries different tags on different questions, under one id.
    tags_by_id: dict[str, set[str]] = {}
    for turn in snapshots.turns.values():
        for item in turn.offered:
            if item.tag:
                tags_by_id.setdefault(item.id, set()).add(item.tag)
    assert any(len(tags) > 1 for tags in tags_by_id.values())


# --- E0: evaluator self-tests ----------------------------------------------------------------


def test_e0_a_perfect_selector_scores_exactly_one(
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    self_test_gold: gold_mod.GoldSet,
) -> None:
    choices = {
        key: [*turn.primary, *(x for x in turn.relevant if x not in turn.primary)]
        for key, turn in self_test_gold.turns.items()
    }
    result = _run(scenarios, workspace, GoldSelector(choices), snapshots)
    scores = score(result, scenarios, snapshots, self_test_gold)
    assert scores.result_kind == "EVALUATOR_SELF_TEST"
    assert scores.gold is not None
    assert scores.gold["f1_micro"] == 1.0 and scores.gold["f1_macro"] == 1.0
    assert scores.gold["primary_hit_rate"] == 1.0
    assert scores.gold["must_not_violations"] == 0
    # The self-test rule includes a knowledge line, so citations are scored too.
    assert scores.gold["citation_turns"] > 0
    assert scores.gold["citation_correct_rate"] == 1.0
    assert scores.overall["line_validity_rate"] == 1.0
    assert scores.overall["fallback_rate"] == 0.0
    assert scores.overall["unsafe_display"] == 0
    assert scores.drifted_turns == ()
    assert scores.consistency == 1.0


def test_e0_a_random_selector_is_reproducible_and_scores_low(
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    self_test_gold: gold_mod.GoldSet,
) -> None:
    first = _run(scenarios, workspace, RandomSelector(seed=7), snapshots, reps=2)
    second = _run(scenarios, workspace, RandomSelector(seed=7), snapshots, reps=2)
    assert [t.shown for t in first.turns] == [t.shown for t in second.turns]
    scores = score(first, scenarios, snapshots, self_test_gold)
    assert scores.gold is not None
    assert scores.gold["f1_micro"] is not None and scores.gold["f1_micro"] < 0.5
    assert scores.overall["line_validity_rate"] == 1.0  # random lines are still allowed lines
    assert scores.overall["unsafe_display"] == 0
    assert scores.stability is not None and scores.stability < 1.0


def test_e0_free_prose_is_always_withheld(
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    self_test_gold: gold_mod.GoldSet,
) -> None:
    result = _run(scenarios, workspace, ProseSelector(), snapshots)
    scores = score(result, scenarios, snapshots, self_test_gold)
    assert scores.overall["line_validity_rate"] == 0.0
    assert scores.overall["fallback_rate"] == 1.0
    assert scores.overall["fallback_reasons"] == {"policy_no_allowed_line": len(result.turns)}
    assert scores.overall["unsafe_display"] == 0
    assert all("own words" not in turn.answer_text for turn in result.turns)
    # Nothing shown where lines were relevant: precision 0 and F1 0, not "undefined".
    assert scores.gold is not None
    assert scores.gold["precision_micro"] == 0.0 and scores.gold["f1_micro"] == 0.0
    assert scores.gold["f1_macro"] == 0.0 and scores.gold["citation_turns"] == 0


def test_e0_injected_instructions_never_reach_the_answer(
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    self_test_gold: gold_mod.GoldSet,
) -> None:
    result = _run(scenarios, workspace, InjectionSelector(), snapshots)
    scores = score(result, scenarios, snapshots, self_test_gold)
    assert scores.overall["unsafe_display"] == 0
    assert scores.overall["line_validity_rate"] == 0.2  # 1 allowed line of 5 written
    for turn in result.turns:
        for injected in InjectionSelector.INJECTED:
            assert injected not in turn.answer_text


# --- result kinds and gold safeguards ------------------------------------------------------


class NamedSelector(RandomSelector):
    name = "pretend-real-model"


def test_a_model_run_without_owner_gold_has_no_quality_score(
    scenarios: ScenarioSet, workspace: Workspace, snapshots: SnapshotSet
) -> None:
    result = run(
        scenarios,
        lambda capture: SelectorModel(NamedSelector(seed=1), capture),
        snapshots=snapshots,
        workspace=workspace,
        only={"S01"},
    )
    scores = score(result, scenarios, snapshots, None)
    assert scores.result_kind == "MODEL_RUN_UNLABELLED"
    assert scores.gold is None
    assert "NOT LABELLED" in markdown(report_data(result, scores, {}))


def test_stub_and_self_test_gold_cannot_be_locked(
    snapshots: SnapshotSet, self_test_gold: gold_mod.GoldSet
) -> None:
    with pytest.raises(gold_mod.GoldError, match="nothing is labelled"):
        gold_mod.lock(gold_mod.stubs(snapshots), snapshots)
    with pytest.raises(gold_mod.GoldError, match="owner"):
        gold_mod.lock(self_test_gold, snapshots)


def _owner_gold_for_lock_test(snapshots: SnapshotSet) -> gold_mod.GoldSet:
    """In-memory labels for testing the lock mechanism only (never written to a fixture)."""

    key, turn = next(iter(snapshots.turns.items()))
    stub = gold_mod.stubs(snapshots)
    labelled = gold_mod.GoldTurn(
        status="labelled",
        relevant=(turn.offered[0].id,),
        primary=(turn.offered[0].id,),
        expect_fallback=False,
        labelled_by="unit-test (lock mechanics only)",
    )
    return stub.model_copy(update={"turns": {**stub.turns, key: labelled}})


def test_locked_owner_gold_is_verified_and_any_change_is_refused(snapshots: SnapshotSet) -> None:
    gold = _owner_gold_for_lock_test(snapshots)
    locked = gold_mod.lock(gold, snapshots)
    gold_mod.verify(gold, locked, snapshots)
    assert locked.labelled_turns == 1
    key = next(iter(gold.labelled()))
    changed = gold.model_copy(
        update={"turns": {**gold.turns, key: gold.turns[key].model_copy(update={"notes": "x"})}}
    )
    with pytest.raises(gold_mod.GoldError, match="changed"):
        gold_mod.verify(changed, locked, snapshots)
    assert gold_mod.stubs(snapshots, gold).labelled() == gold.labelled()


def test_owner_gold_is_scored_only_with_its_lock(
    scenarios: ScenarioSet, workspace: Workspace, snapshots: SnapshotSet
) -> None:
    gold = _owner_gold_for_lock_test(snapshots)
    key = next(iter(gold.labelled()))
    result = run(
        scenarios,
        lambda capture: SelectorModel(ProseSelector(), capture),
        snapshots=snapshots,
        workspace=workspace,
        only={key.split("#")[0]},
    )
    with pytest.raises(gold_mod.GoldError, match="locked"):
        score(result, scenarios, snapshots, gold)
    scores = score(result, scenarios, snapshots, gold, gold_mod.lock(gold, snapshots))
    assert scores.gold is not None and scores.gold["turns_scored"] == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "labelled", "relevant": ("C-1",), "expect_fallback": False},
        {"status": "stub", "relevant": ("C-1",)},
        {
            "status": "labelled",
            "relevant": ("C-1",),
            "primary": ("C-2",),
            "expect_fallback": False,
            "labelled_by": "x",
        },
        {
            "status": "labelled",
            "relevant": ("C-1",),
            "must_not": ("C-1",),
            "expect_fallback": False,
            "labelled_by": "x",
        },
        {"status": "labelled", "relevant": (), "expect_fallback": False, "labelled_by": "x"},
        {"status": "labelled", "relevant": ("C-1",), "expect_fallback": True, "labelled_by": "x"},
    ],
)
def test_incoherent_gold_turns_are_refused(fields: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        gold_mod.GoldTurn(**fields)


def test_gold_naming_lines_a_question_never_offered_is_refused(snapshots: SnapshotSet) -> None:
    gold = _owner_gold_for_lock_test(snapshots)
    key = next(iter(gold.labelled()))
    wrong = gold.turns[key].model_copy(update={"must_not": ("C-not-offered",)})
    bad = gold.model_copy(update={"turns": {**gold.turns, key: wrong}})
    with pytest.raises(gold_mod.GoldError, match="did not offer"):
        gold_mod.lock(bad, snapshots)


def test_drifted_questions_are_flagged_and_left_out_of_gold_scores(
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    self_test_gold: gold_mod.GoldSet,
) -> None:
    key = "S01#0"
    stale = snapshots.turns[key].model_copy(update={"prompt_fingerprint": "0" * 16})
    drifted = snapshots.model_copy(update={"turns": {**snapshots.turns, key: stale}})
    result = run(
        scenarios,
        lambda capture: SelectorModel(ProseSelector(), capture),
        snapshots=drifted,
        workspace=workspace,
        only={"S01"},
    )
    scores = score(result, scenarios, snapshots, self_test_gold)
    assert scores.drifted_turns == (key,)
    assert scores.gold is not None and scores.gold["turns_excluded_for_drift"] == 1


# --- no remote model -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://openrouter.ai/api/v1",
        "http://localhost:11434/v1",
        "http://10.0.0.5:11434/v1",
        "http://127.0.0.1.example.com/v1",
        "http://user:pw@127.0.0.1:11434/v1",
    ],
)
def test_only_a_literal_loopback_model_can_be_evaluated(url: str) -> None:
    with pytest.raises(RemoteModelRefusedError):
        local_model(base_url=url, model="any", environ={})


def test_a_local_model_is_refused_when_a_proxy_is_set() -> None:
    with pytest.raises(RemoteModelRefusedError, match="proxy"):
        local_model(
            base_url="http://127.0.0.1:11434/v1",
            model="ministral-3:8b",
            environ={"HTTPS_PROXY": "http://proxy.example:8080"},
        )
    model = local_model(base_url="http://127.0.0.1:11434/v1", model="ministral-3:8b", environ={})
    assert model.name == "ministral-3:8b"  # built, but nothing was requested


def test_a_local_model_is_refused_when_a_system_proxy_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("all_proxy", raising=False)
    monkeypatch.setattr("urllib.request.getproxies", lambda: {"https": "http://proxy.example:8080"})
    with pytest.raises(RemoteModelRefusedError, match="system proxies"):
        local_model(base_url="http://127.0.0.1:11434/v1", model="ministral-3:8b")


def test_the_runtime_package_never_imports_the_harness() -> None:
    for path in (ASSISTANT / "ai_assistant").rglob("*.py"):
        assert "assistant_eval" not in path.read_text(encoding="utf-8"), path.name


def test_a_report_says_what_kind_of_result_it_is(
    scenarios: ScenarioSet,
    workspace: Workspace,
    snapshots: SnapshotSet,
    self_test_gold: gold_mod.GoldSet,
    tmp_path: Path,
) -> None:
    result = run(
        scenarios,
        lambda capture: SelectorModel(ProseSelector(), capture),
        snapshots=snapshots,
        workspace=workspace,
        only={"S13"},
    )
    json_path, md_path = write(
        result, score(result, scenarios, snapshots, self_test_gold), tmp_path, {}
    )
    text = md_path.read_text(encoding="utf-8")
    assert text.startswith("# AI Assistant offline evaluation - EVALUATOR_SELF_TEST")
    assert "say nothing about any real model" in text
    assert '"result_kind": "EVALUATOR_SELF_TEST"' in json_path.read_text(encoding="utf-8")
