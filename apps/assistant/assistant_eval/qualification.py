"""Technical qualification of a local model for model management (D-093), run in its own
process by ``scripts/qualify_model.py`` so this dev-only harness never loads into the service.

The service validates the request, records a ``running`` qualification and starts this
process with the qualification id and its own state database and profiles file. The process
re-reads the profile, refuses to run if its settings or the answer code changed since the
request (``CONFIG_MISMATCH``), and asks the synthetic scenarios through the real service with
the candidate model (``runner.run``: a mock CLM backend; no case, customer or sponsor data).
It then checks the context window from the server's own token counts and applies the gates
in ``ai_assistant.model_qualification``. Only counts, rates, timings and closed codes are
stored; no answer text. Cancellation and the time limit are checked before every turn; the
service also stops the process if it overruns.
"""

import logging
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anyio

from ai_assistant import anthropic_runtime
from ai_assistant.config import AiAssistantSettings, external_conversational
from ai_assistant.llm import ChatModel, OpenAICompatibleChatModel
from ai_assistant.model_admin_store import (
    ModelAdminStore,
    apply_claude_controls,
    apply_controls,
)
from ai_assistant.model_catalog import (
    BASELINE_ID,
    MESSAGE_OVERHEAD_TOKENS,
    build_baseline_adapter,
    build_profile_model,
    load_catalogue,
)
from ai_assistant.model_factory import ASSISTANT_DIR
from ai_assistant.model_profiles import ProfileConfigError
from ai_assistant.model_qualification import (
    EVAL_FIXTURES,
    HARNESS_VERSION,
    QualificationStopped,
    WatchedModel,
    connection_test,
    gates,
    line_breakdown,
    probe_target,
    qualification_basis,
    verify_capacity,
)
from ai_assistant.remote_test import RemoteTestModel, connection_check, qualification_manifest
from ai_assistant.synthetic_eligibility import mode as synthetic_dev_mode

from . import gold as gold_mod
from . import guard_reasons
from .hosted_paths import run_paths
from .runner import EMBEDDER, Workspace, run
from .runner import settings as runner_settings
from .scenarios import load_scenarios
from .scoring import gold_based, label_free
from .snapshot import SnapshotSet

log = logging.getLogger("assistant_eval.qualification")


def gold_state() -> tuple[str, str | None, Any, Any]:
    """("SCORED", None, gold, lock) only when owner gold is labelled and its lock verifies;
    otherwise ("NOT_SCORED", reason, None, None)."""

    gold_file = EVAL_FIXTURES / "gold.json"
    lock_file = EVAL_FIXTURES / "gold.lock.json"
    if not gold_file.exists():
        return "NOT_SCORED", "OWNER_GOLD_MISSING", None, None
    gold = gold_mod.GoldSet.model_validate_json(gold_file.read_text(encoding="utf-8"))
    if gold.kind != "owner" or any(turn.status != "labelled" for turn in gold.turns.values()):
        return "NOT_SCORED", "OWNER_GOLD_NOT_LABELLED", None, None
    if not lock_file.exists():
        return "NOT_SCORED", "OWNER_GOLD_NOT_LOCKED", None, None
    try:
        lock = gold_mod.GoldLock.model_validate_json(lock_file.read_text(encoding="utf-8"))
        snapshots = SnapshotSet.model_validate_json(
            (EVAL_FIXTURES / "snapshots.json").read_text(encoding="utf-8")
        )
        gold_mod.verify(gold, lock, snapshots)
    except (gold_mod.GoldError, ValueError):
        return "NOT_SCORED", "OWNER_GOLD_NOT_LOCKED", None, None
    return "SCORED", None, gold, lock


@dataclass
class QualificationJob:
    """One technical qualification (run in the qualification process)."""

    store: ModelAdminStore
    qualification_id: str
    profile_id: str
    model: OpenAICompatibleChatModel
    model_id: str
    declared_tokens: int
    max_answer_tokens: int
    basis: str
    started_by: str
    deadline: float
    on_finish: Callable[[str, str | None], None] = lambda status, code: None

    def _stop(self, done_turns: int) -> None:
        if time.monotonic() > self.deadline:
            raise QualificationStopped("DEADLINE")
        if not self.store.heartbeat(self.qualification_id, done_turns):
            raise QualificationStopped("CANCELLED")

    def harness_model(self, capture: Any, watched: WatchedModel) -> ChatModel:
        """The model each scenario is asked through (the candidate, watched). Tests replace
        it to drive the harness with a fixed-rule selector."""

        return watched

    def run(self) -> None:
        status: str = "error"
        code: str | None = "HARNESS_ERROR"
        summary: dict[str, Any] | None = None
        try:
            status, code, summary = self._run()
        except QualificationStopped as exc:
            status = "cancelled" if exc.code == "CANCELLED" else "error"
            code = exc.code
        except Exception as exc:  # the run must always be closed; no detail is kept
            log.error("model qualification failed: %s", type(exc).__name__)
        finally:
            self.store.finish_qualification(self.qualification_id, status, code, summary)
            self.on_finish(status, code)

    def _run(self) -> tuple[str, str | None, dict[str, Any]]:
        started = time.monotonic()
        scenarios = load_scenarios()
        expected = len(scenarios.turn_keys())
        self.store.heartbeat(self.qualification_id, 0, total_turns=expected)
        connection = anyio.run(connection_test, self.model, self.model_id)
        self._stop(0)
        quality, quality_reason, gold, _lock = gold_state()
        summary: dict[str, Any] = {
            "connection": connection,
            "quality": {"status": quality, "reason": quality_reason},
            "reproducibility": {
                "harness_version": HARNESS_VERSION,
                "basis": self.basis[:16],
                "scenarios": len(scenarios.scenarios),
                "turns": expected,
                "reps": 1,
                "retrieval": EMBEDDER,
                "model_id": self.model_id,
            },
        }
        if connection["outcome"] != "passed":
            summary["gates"] = gates(
                connection=connection,
                completed=False,
                turns=[],
                expected_turns=expected,
                overall={},
                capacity=None,
                largest_bound=0,
            )
            return "failed", "CONNECTION_FAILED", summary
        # D-142 R2 (D-1): a model on an endpoint that is not literal loopback is qualified
        # through the privacy boundary, as it runs once activated (model_admin): every turn,
        # token count and capacity probe sends only the protected payload, and the prompt bound
        # is the protected payload's. A loopback model is unchanged.
        target = probe_target(self.model, retain_largest=True)
        bounded = target is not self.model
        watched = WatchedModel(target, self._stop)
        snapshots = SnapshotSet.model_validate_json(
            (EVAL_FIXTURES / "snapshots.json").read_text(encoding="utf-8")
        )
        try:
            with Workspace() as workspace, guard_reasons.recording():
                result = run(
                    scenarios,
                    lambda capture: self.harness_model(capture, watched),
                    snapshots=snapshots,
                    workspace=workspace,
                )
            turns = list(result.turns)
            overall = label_free(turns)
            capacity = verify_capacity(
                target,
                declared_tokens=self.declared_tokens,
                max_answer_tokens=self.max_answer_tokens,
                largest_prompt=None if bounded else watched.largest,
                stop=lambda: self._stop(len(turns)),
            )
            largest_bound = (
                target.largest_bytes + MESSAGE_OVERHEAD_TOKENS * target.largest_messages
                if bounded
                else watched.largest_bound
            )
        finally:
            if bounded:
                target.forget()  # the retained identity map lives no longer than the run
        summary["capacity"] = capacity
        summary["metrics"] = {
            key: overall.get(key)
            for key in (
                "answers",
                "fallback_rate",
                "fallback_reasons",
                "line_validity_rate",
                "unsafe_display",
                "cut_short_rate",
                "latency_total_ms_p50",
                "latency_total_ms_p95",
                "latency_first_shown_ms_p50",
                "latency_first_shown_ms_p95",
                "mean_offered_lines",
            )
        }
        summary["metrics"]["largest_prompt_bound"] = largest_bound
        # R0: which guard rule left each sentence out (closed codes and counts only).
        summary["lines"] = {**line_breakdown(turns), **guard_reasons.reason_breakdown(turns)}
        if quality == "SCORED" and gold is not None:
            summary["quality"]["gold"] = gold_based(turns, gold, snapshots)
        summary["gates"] = gates(
            connection=connection,
            completed=True,
            turns=turns,
            expected_turns=expected,
            overall=overall,
            capacity=capacity,
            largest_bound=largest_bound,
        )
        summary["reproducibility"]["prompt_version"] = result.manifest.get("prompt_version")
        summary["reproducibility"]["drifted_turns"] = sum(1 for turn in turns if turn.drift)
        summary["duration_ms"] = round((time.monotonic() - started) * 1000)
        passed = all(item["passed"] for item in summary["gates"] if item["gating"])
        failed = [
            item["gate"] for item in summary["gates"] if item["gating"] and not item["passed"]
        ]
        return (
            ("passed", None, summary)
            if passed
            else ("failed", "GATES_FAILED:" + ",".join(failed), summary)
        )


PHASE_B_QUESTIONS = EVAL_FIXTURES / "phase_b_questions.json"
G8_RULE = "every remote call verified (serving provider, model and cost)"
# D-099 Option B: Anthropic has no separate per-call record, so a Claude call is verified from
# its own reply (not equivalent to the GPT-OSS generation metadata check).
CLAUDE_G8_RULE = (
    "every Claude call verified in-band (workspace, model and standard routing named in the"
    " reply; cost settled from its complete reported usage)"
)


@dataclass
class RemoteQualificationJob:
    """D-094: the remote model's qualification. A paid run, so only the configured, counted
    Phase B question manifest is asked (synthetic fixture cases through the mock CLM backend),
    after a passing preflight; every call must then be verified from its generation metadata
    (gate G-8). The prompt bound is the adapter's own enforced byte limit, not a probe."""

    store: ModelAdminStore
    qualification_id: str
    model: RemoteTestModel | anthropic_runtime.ClaudeTestModel
    settings: AiAssistantSettings
    manifest: tuple[str, ...]
    basis: str
    deadline: float
    options: dict[str, Any]
    # D-099: a Claude run's own free preflight (reconciled within 24 hours) and G-8 rule.
    connection: Callable[[], dict[str, Any]] | None = None
    g8_rule: str = G8_RULE

    def _stop(self, done_turns: int) -> None:
        if time.monotonic() > self.deadline:
            raise QualificationStopped("DEADLINE")
        if not self.store.heartbeat(self.qualification_id, done_turns):
            raise QualificationStopped("CANCELLED")

    def run(self) -> None:
        status: str = "error"
        code: str | None = "HARNESS_ERROR"
        summary: dict[str, Any] | None = None
        try:
            status, code, summary = self._run()
        except QualificationStopped as exc:
            status = "cancelled" if exc.code == "CANCELLED" else "error"
            code = exc.code
        except Exception as exc:  # the run must always be closed; no detail is kept
            log.error("remote qualification failed: %s", type(exc).__name__)
        finally:
            self.store.finish_qualification(self.qualification_id, status, code, summary)

    def _run(self) -> tuple[str, str | None, dict[str, Any]]:
        started = time.monotonic()
        scenarios = load_scenarios(PHASE_B_QUESTIONS)
        expected = len(self.manifest)
        # D-130: hosted Claude also answers one turn on each hosted chat path it enables.
        hosted_keys = (
            anthropic_runtime.hosted_qualification_turns()
            if isinstance(self.model, anthropic_runtime.ClaudeTestModel)
            else ()
        )
        self.store.heartbeat(self.qualification_id, 0, total_turns=expected + len(hosted_keys))
        connection = (
            self.connection()
            if self.connection is not None
            else connection_check(self.settings, **self.options)
        )
        self._stop(0)
        summary: dict[str, Any] = {
            "connection": connection,
            # Owner gold covers the default scenarios, not the Phase B questions asked here.
            "quality": {"status": "NOT_SCORED", "reason": "REMOTE_MANIFEST_NOT_GOLD_LABELLED"},
            "reproducibility": {
                "harness_version": HARNESS_VERSION,
                "basis": self.basis[:16],
                "scenarios": "phase_b_questions.json",
                "turns": expected,
                "question_manifest": ",".join(self.manifest),
                "reps": 1,
                "retrieval": EMBEDDER,
                "model_id": self.model.name,
                "endpoint": self.model.endpoint_slug,
            },
        }
        capacity = {
            "status": "verified",
            "code": "REMOTE_PROMPT_BYTES_ENFORCED",
            "declared_tokens": None,
            "target_tokens": None,
            "probed_tokens": None,
            "prompt_limit": self.settings.remote_max_prompt_bytes,
        }
        if connection["outcome"] != "passed":
            summary["gates"] = _remote_gates(
                gates(
                    connection=connection,
                    completed=False,
                    turns=[],
                    expected_turns=expected,
                    overall={},
                    capacity=None,
                    largest_bound=0,
                ),
                None,
                self.g8_rule,
            )
            return "failed", "CONNECTION_FAILED", summary
        answers_freely = external_conversational(self.settings)
        watched = WatchedModel(
            self.model,
            self._stop,
            synthetic=answers_freely,
            development=lambda: synthetic_dev_mode(self.settings),
        )
        # The harness answers as the service will: the same answer mode and D-095 mode.
        harness = runner_settings().model_copy(
            update={
                "answer_mode": self.settings.answer_mode if answers_freely else "exact_lines",
                "synthetic_dev_decision": self.settings.synthetic_dev_decision,
            }
        )
        with Workspace() as workspace, guard_reasons.recording():
            result = run(
                scenarios,
                lambda capture: watched,
                workspace=workspace,
                harness_settings=harness,
                # Free-text answers go to the external model only for verified synthetic
                # cases: the case's document is the tracked fixture file it is checked against.
                verified_documents=answers_freely,
                turns=frozenset(self.manifest),
            )
            hosted_turns = (
                run_paths(
                    watched,
                    hosted_keys,
                    workspace=workspace,
                    harness_settings=harness,
                    verified_documents=answers_freely,
                    begin=lambda key: watched.begin(key, 0),
                )
                if hosted_keys
                else []
            )
        turns = list(result.turns)
        # The final turn count (each turn's own heartbeat is taken before it is asked).
        self._stop(len(turns) + len(hosted_turns))
        overall = label_free(turns)
        verification = self.model.verify_now()
        calls = self.model.calls_since_start()
        verified = sum(1 for call in calls if call.verification == "verified")
        summary["capacity"] = capacity
        summary["metrics"] = {
            key: overall.get(key)
            for key in (
                "answers",
                "fallback_rate",
                "fallback_reasons",
                "line_validity_rate",
                "unsafe_display",
                "cut_short_rate",
                "latency_total_ms_p50",
                "latency_total_ms_p95",
                "latency_first_shown_ms_p50",
                "latency_first_shown_ms_p95",
                "mean_offered_lines",
            )
        }
        summary["metrics"]["largest_prompt_bound"] = watched.largest_bound
        summary["metrics"]["remote_calls"] = len(calls)
        summary["metrics"]["remote_calls_verified"] = verified
        # D-098: each failed call's closed error class (rate_limited, timeout, payment, ...),
        # so HR is told whether the provider, the budget or the answers failed.
        summary["metrics"]["call_errors"] = dict(
            sorted(Counter(call.error_class for call in calls if call.error_class).items())
        )
        # R0: which guard rule left each sentence out (closed codes and counts only).
        summary["lines"] = {**line_breakdown(turns), **guard_reasons.reason_breakdown(turns)}
        summary["gates"] = _remote_gates(
            gates(
                connection=connection,
                completed=True,
                turns=turns,
                expected_turns=expected,
                overall=overall,
                capacity=capacity,
                largest_bound=watched.largest_bound,
            ),
            {
                "calls": len(calls),
                "verified": verified,
                "passed": verification.passed and bool(calls) and verified == len(calls),
            },
            self.g8_rule,
        )
        if hosted_keys:
            summary["hosted_paths"] = [turn.to_dict() for turn in hosted_turns]
            summary["reproducibility"]["hosted_turns"] = ",".join(hosted_keys)
            summary["gates"].append(
                {
                    "gate": "G-9",
                    "rule": "each hosted chat path (D-130) answered by the model, not cut short",
                    "value": f"{sum(t.passed for t in hosted_turns)}/{len(hosted_keys)}",
                    "passed": len(hosted_turns) == len(hosted_keys)
                    and all(turn.passed for turn in hosted_turns),
                    "gating": True,
                }
            )
        # C11 (C-1b): the paths this run answered and passed, read back before a hosted path
        # (dashboard insights) may use the activated configuration.
        summary["paths"] = ["case_chat", *[turn.path for turn in hosted_turns if turn.passed]]
        summary["reproducibility"]["prompt_version"] = result.manifest.get("prompt_version")
        summary["duration_ms"] = round((time.monotonic() - started) * 1000)
        failed = [
            item["gate"] for item in summary["gates"] if item["gating"] and not item["passed"]
        ]
        if failed:
            return "failed", "GATES_FAILED:" + ",".join(failed), summary
        return "passed", None, summary


def _remote_gates(
    items: list[dict[str, Any]], verification: dict[str, Any] | None, rule: str = G8_RULE
) -> list[dict[str, Any]]:
    """The local gates, with G-7 restated for the adapter's enforced prompt limit, plus G-8."""

    for item in items:
        if item["gate"] == "G-7":
            item["rule"] = (
                "prompts inside the remote adapter's enforced byte limit, cut short <= 10%"
            )
    items.append(
        {
            "gate": "G-8",
            "rule": rule,
            "value": None
            if verification is None
            else f"{verification['verified']}/{verification['calls']}",
            "passed": verification is not None and verification["passed"],
            "gating": True,
        }
    )
    return items


def _run_remote(
    store: ModelAdminStore,
    qualification_id: str,
    item: dict[str, Any],
    settings: AiAssistantSettings,
    environ: Mapping[str, str] | None,
    transport: object,
    basis: str,
    fetch: Callable[[str], Any] | None,
    claude: str | None = None,
) -> None:
    manifest = qualification_manifest(settings)
    known = set(load_scenarios(PHASE_B_QUESTIONS).turn_keys())
    if manifest is None or not set(manifest) <= known:
        store.finish_qualification(qualification_id, "error", "REMOTE_MANIFEST_MISSING", None)
        return
    options: dict[str, Any] = {"environ": environ, "transport": transport}
    if fetch is not None and claude is None:
        options["fetch"] = fetch
    paid = anthropic_runtime.PAID_RECONCILE_SECONDS
    model: RemoteTestModel | anthropic_runtime.ClaudeTestModel
    try:
        # Verification runs after each call, before the next turn (as the Phase B harness).
        # D-099: a Claude configuration (``claude``, its profile id) under its own safeguards,
        # with a reconciliation no older than 24 hours for this paid run.
        model = (
            anthropic_runtime.ClaudeTestModel(
                settings, claude, within_seconds=paid, purpose="qualification", **options
            )
            if claude is not None
            else RemoteTestModel(settings, background=False, purpose="qualification", **options)
        )
    except ProfileConfigError as exc:
        store.finish_qualification(qualification_id, "error", exc.code, None)
        return
    extra: dict[str, Any] = {}
    if claude is not None:
        extra = {
            "connection": lambda: anthropic_runtime.connection_check(
                settings, within_seconds=paid, **options
            ),
            "g8_rule": CLAUDE_G8_RULE,
        }
    RemoteQualificationJob(
        store=store,
        qualification_id=qualification_id,
        model=model,
        settings=settings,
        manifest=tuple(manifest),
        basis=basis,
        deadline=time.monotonic() + settings.model_qualification_max_seconds,
        options=options,
        **extra,
    ).run()


def store_path(settings: AiAssistantSettings) -> Path:
    path = Path(settings.model_admin_db_path)
    return path if path.is_absolute() else ASSISTANT_DIR / path


def run_job(
    qualification_id: str,
    settings: AiAssistantSettings,
    *,
    environ: Mapping[str, str] | None = None,
    transport: object = None,
    job_class: type[QualificationJob] = QualificationJob,
    fetch: Callable[[str], Any] | None = None,
) -> None:
    """Run the recorded qualification ``qualification_id`` to its end (always closed)."""

    store = ModelAdminStore(store_path(settings))
    item = store.qualification(qualification_id)
    if item is None or item["status"] != "running":
        return
    entry = load_catalogue(settings).get(item["profile_id"])
    basis = qualification_basis()
    if (
        entry is None
        or entry.status != "selectable"
        or entry.fingerprint != item["fingerprint"]
        or basis != item["basis"]
    ):
        store.finish_qualification(qualification_id, "error", "CONFIG_MISMATCH", None)
        return
    if entry.deployment == "anthropic":
        # D-099: the Anthropic settings as configured; D-102: Claude's own HR daily allowance
        # applies too (its call count stays the environment's, as for GPT-OSS below).
        _run_remote(
            store,
            qualification_id,
            item,
            apply_claude_controls(settings, store.claude_spending_controls(), calls=False),
            environ,
            transport,
            basis,
            None,
            claude=entry.profile_id,
        )
        return
    if entry.source == "code":
        # D-096: the HR daily allowance applies to the paid qualification too (its own call
        # count stays the environment's, so a low chat call limit cannot break a run).
        # The configuration's own settings (its reasoning effort) are the ones qualified.
        remote = entry.settings_for(
            apply_controls(settings, store.spending_controls(), calls=False)
        )
        _run_remote(store, qualification_id, item, remote, environ, transport, basis, fetch)
        return
    try:
        model = (
            build_baseline_adapter(settings, environ=environ, transport=transport, loopback=True)
            if entry.profile_id == BASELINE_ID
            else build_profile_model(entry, environ=environ, transport=transport)
        )
    except ProfileConfigError as exc:
        store.finish_qualification(qualification_id, "error", exc.code, None)
        return
    job_class(
        store=store,
        qualification_id=qualification_id,
        profile_id=entry.profile_id,
        model=model,
        model_id=model.name,
        # The baseline declares no window; its capacity is checked at the probe cap.
        declared_tokens=entry.context_window_tokens or 32768,
        max_answer_tokens=entry.max_answer_tokens or settings.llm_max_answer_tokens,
        basis=basis,
        started_by=item["started_by"],
        deadline=time.monotonic() + settings.model_qualification_max_seconds,
    ).run()
