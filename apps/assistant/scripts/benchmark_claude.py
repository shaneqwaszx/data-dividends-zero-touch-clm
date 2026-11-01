"""Claude API model benchmark over the 17 Phase B questions (evaluation only, synthetic data).

    cd apps/assistant
    python -m pip install --target data/anthropic-sdk anthropic==2.3.0   # once, git-ignored
    python scripts/benchmark_claude.py prompts                  # offline: approve the prompts
    python scripts/benchmark_claude.py init-ledger --cap-usd 6 --per-call-usd 0.10 --calls 51
    python scripts/benchmark_claude.py preflight --models haiku,sonnet,opus \\
        --owner-attests-credit-balance-usd <console balance> --owner-attests-auto-reload-off
    python scripts/benchmark_claude.py run --models haiku,sonnet,opus --expect-calls 51
    python scripts/benchmark_claude.py status
    python scripts/benchmark_claude.py reconcile --console-usage-usd <console usage>
    python scripts/benchmark_claude.py report --run <run folder> --baseline <gpt-oss folder>...
    python scripts/benchmark_claude.py scoring --run <run folder>

prompts     builds every outgoing prompt with the real service and a recording model (no
            network), checks each against the D-094 synthetic text boundary and the Messages
            API mapping, and approves them by SHA-256 (data/eval/claude/approved_prompts.json)
            with a full-text copy for review (prompts_review.md).
init-ledger creates the benchmark's own spending ledger (never the OpenRouter ledger).
preflight   free requests only (Models API, token counting): checks every model, counts every
            approved prompt per model, prices the worst case of every call against the per-call
            ceiling, the ledger and the owner's attested credit balance. No inference.
run         the paid run: one request per model and question, no retries, models interleaved
            (the order rotates per question). Needs a passing preflight under 12 hours old for
            exactly these models, settings and prompts, and stops all requests when the ledger
            breaker opens. Answers go to answers.jsonl; content-free records to calls.json.
reconcile   records the Console's reported usage for the benchmark key/workspace and opens the
            breaker when it is above the ledger.
report      speed, cost and guard metrics per model, beside the saved GPT-OSS runs (read only).
scoring     a new blinded owner-scoring set for the run's answers (existing ratings untouched).

The key is read only from AI_ASSISTANT_ANTHROPIC_API_KEY in this process's environment.
"""

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.synthetic_boundary import check_messages  # noqa: E402
from ai_assistant.telemetry import prompt_version  # noqa: E402
from assistant_eval import claude_bench as cb  # noqa: E402
from assistant_eval.models import Capture  # noqa: E402
from assistant_eval.runner import TurnResult, Workspace, run  # noqa: E402
from assistant_eval.scenarios import EVAL_FIXTURES, ScenarioSet, load_scenarios  # noqa: E402
from assistant_eval.snapshot import offered_lines  # noqa: E402

QUESTIONS = EVAL_FIXTURES / "phase_b_questions.json"
OUT = HERE / "data" / "eval" / "claude"
APPROVED = OUT / "approved_prompts.json"
PREFLIGHT = OUT / "preflight.json"
LEDGER = OUT / "ledger.sqlite3"
PREFLIGHT_MAX_AGE = timedelta(hours=12)
DECLINE = "I can't answer that from this case's data."
# Project-provisional expectation (not owner-approved answerability labels, D-093 M4 G-5):
# the two off-topic questions should be declined; the others should get case-grounded lines.
EXPECTED_DECLINE = frozenset({"P07#0", "P07#1"})


def _usd(micro: int | None) -> str:
    return "n/a" if micro is None else f"{Decimal(micro) / Decimal(1_000_000):.6f}"


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _scenarios() -> ScenarioSet:
    return load_scenarios(QUESTIONS)


def _questions(scenarios: ScenarioSet) -> dict[str, str]:
    return {
        scenario.turn_key(index): question
        for scenario in scenarios.scenarios
        for index, question in enumerate(scenario.questions)
    }


def _configs(args: argparse.Namespace) -> list[cb.BenchConfig]:
    aliases = [alias.strip() for alias in args.models.split(",") if alias.strip()]
    if not aliases or len(set(aliases)) != len(aliases):
        raise cb.BenchConfigError("--models must list distinct approved models")
    return [
        cb.BenchConfig(
            alias, effort=args.effort, thinking=args.thinking, max_tokens=args.max_tokens
        )
        for alias in aliases
    ]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")


# --- prompts (offline) ----------------------------------------------------------------------


def build_prompts(scenarios: ScenarioSet) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any]]:
    recorder = cb.PromptRecorder()
    preps: dict[str, Any] = {}

    def make(capture: Capture) -> Any:
        original = recorder.stream

        async def stream(messages: list[dict[str, str]]) -> Any:
            preps[recorder._turn] = capture.latest
            async for piece in original(messages):
                yield piece

        recorder.stream = stream  # type: ignore[method-assign]
        return recorder

    with Workspace() as workspace:
        run(scenarios, make, workspace=workspace)
    return recorder.prompts, preps


def cmd_prompts(args: argparse.Namespace) -> int:
    scenarios = _scenarios()
    prompts, _ = build_prompts(scenarios)
    keys = scenarios.turn_keys()
    approved: dict[str, Any] = {}
    review = [
        "# Claude benchmark: every outgoing prompt (synthetic Phase B questions)",
        "",
        f"Prompt version `{prompt_version()}`; git `{_git_head()}`;"
        f" built {datetime.now(UTC):%Y-%m-%dT%H:%MZ}.",
        "",
    ]
    failures = []
    for key in keys:
        messages = prompts.get(key)
        if messages is None:
            failures.append(f"{key}: no prompt was built")
            continue
        boundary = check_messages(messages)
        try:
            system, conversation = cb.to_anthropic(messages)
            shape = "ok"
        except cb.UnsupportedPromptError as error:
            system, conversation, shape = [], [], str(error)
        sha = cb.prompt_sha(messages)
        if boundary is not None or shape != "ok":
            failures.append(f"{key}: boundary {boundary or 'ok'}, shape {shape}")
        approved[sha] = {
            "key": key,
            "chars": sum(len(m["content"]) for m in messages),
            "roles": [m["role"] for m in messages],
            "system_blocks": len(system),
            "conversation_turns": len(conversation),
            "synthetic_boundary": boundary or "passed",
            "shape": shape,
        }
        review += [f"## {key} (sha256 {sha[:16]}, boundary {boundary or 'passed'})", ""]
        for message in messages:
            review += [f"### {message['role']}", "", "```text", message["content"], "```", ""]
    if failures or len(approved) != len(keys):
        print("REFUSED: prompts not approved\n" + "\n".join(failures))
        return 2
    _write_json(
        APPROVED,
        {
            "note": "Synthetic Phase B prompts approved for the Claude benchmark (no content).",
            "prompt_version": prompt_version(),
            "git_head": _git_head(),
            "built_at": datetime.now(UTC).isoformat(),
            "questions_file": QUESTIONS.name,
            "prompts": approved,
        },
    )
    (OUT / "prompts_review.md").write_text("\n".join(review), encoding="utf-8")
    print(f"approved {len(approved)} prompts, all inside the synthetic boundary -> {APPROVED}")
    return 0


# --- ledger ---------------------------------------------------------------------------------


def _micro(text: str, name: str) -> int:
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise SystemExit(f"{name} must be a US$ amount") from None
    if not value.is_finite() or value < 0:
        raise SystemExit(f"{name} must be a US$ amount")
    return cb.to_micro(value)


def cmd_init_ledger(args: argparse.Namespace) -> int:
    try:
        cb.ClaudeLedger.create(
            LEDGER,
            cap_micro_usd=_micro(args.cap_usd, "--cap-usd"),
            per_call_micro_usd=_micro(args.per_call_usd, "--per-call-usd"),
            call_limit=args.calls,
        )
    except cb.LedgerRefusedError as error:
        print(f"refused: {error.code}")
        return 2
    print(f"ledger created: {LEDGER}")
    return cmd_status(args)


def cmd_status(_: argparse.Namespace) -> int:
    try:
        status = cb.ClaudeLedger(LEDGER).status()
    except cb.LedgerRefusedError as error:
        print(f"refused: {error.code}")
        return 2
    print(
        f"cap US${_usd(status.cap_micro_usd)}, per call US${_usd(status.per_call_micro_usd)},"
        f" calls {status.calls}/{status.call_limit} (open {status.open_calls}),"
        f" committed US${_usd(status.committed_micro_usd)} (settled"
        f" {_usd(status.settled_micro_usd)}, charged at reservation"
        f" {_usd(status.conservative_micro_usd)}), breaker"
        f" {'OPEN ' + str(status.breaker_code) if status.breaker_open else 'closed'},"
        f" console usage {_usd(status.provider_reported_micro_usd)}"
    )
    return 0


def cmd_reconcile(args: argparse.Namespace) -> int:
    ledger = cb.ClaudeLedger(LEDGER)
    verdict = ledger.record_provider_usage(
        _micro(args.console_usage_usd, "--console-usage-usd"),
        _micro(args.tolerance_usd, "--tolerance-usd"),
    )
    print(f"console usage {verdict}")
    cmd_status(args)
    return 0 if verdict == "within_ledger" else 4


# --- preflight (free requests only) ---------------------------------------------------------


def _capabilities(info: Any) -> dict[str, Any]:
    raw = getattr(info, "capabilities", None)
    if raw is None:
        return {}
    dump = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
    return dump if isinstance(dump, dict) else {}


def _supported(capabilities: Mapping[str, Any], *path: str) -> bool | None:
    node: Any = capabilities
    for part in path:
        if not isinstance(node, Mapping) or part not in node:
            return None
        node = node[part]
    if isinstance(node, Mapping) and isinstance(node.get("supported"), bool):
        return bool(node["supported"])
    return None


def cmd_preflight(args: argparse.Namespace) -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}")

    configs = _configs(args)
    approved = _read_json(APPROVED) if APPROVED.exists() else {"prompts": {}}
    check(
        "prompts.approved",
        approved.get("prompt_version") == prompt_version() and len(approved["prompts"]) == 17,
        f"{len(approved['prompts'])} approved prompts for prompt version"
        f" {approved.get('prompt_version')} (current {prompt_version()})",
    )
    try:
        status = cb.ClaudeLedger(LEDGER).status()
        check(
            "ledger.healthy",
            not status.breaker_open and status.open_calls == 0,
            f"breaker {'open' if status.breaker_open else 'closed'},"
            f" open calls {status.open_calls}",
        )
    except cb.LedgerRefusedError as error:
        check("ledger.healthy", False, error.code)
        status = None
    check(
        "owner.auto_reload_off",
        args.owner_attests_auto_reload_off,
        "the owner attests Console auto-reload is off",
    )
    balance = _micro(args.owner_attests_credit_balance_usd, "--owner-attests-credit-balance-usd")
    try:
        key = cb.read_key(os.environ)
        check("credential.present", True, f"{cb.KEY_VARIABLE} is set and key-shaped (not shown)")
    except cb.LedgerRefusedError:
        check(
            "credential.present",
            False,
            f"{cb.KEY_VARIABLE} refused: {cb.key_problem(os.environ)} (value not shown)",
        )
        _write_json(PREFLIGHT, {"passed": False, "checks": checks})
        return 3
    sdk = cb.load_sdk()
    client = cb.make_client(key)
    counted: dict[str, dict[str, int]] = {}
    models: dict[str, Any] = {}
    worst_total = 0
    try:
        for config in configs:
            model = config.model
            try:
                info = client.models.retrieve(model.model_id)
            except Exception as error:  # noqa: BLE001 - reported by class only
                check(f"{config.alias}.models_api", False, type(error).__name__)
                continue
            capabilities = _capabilities(info)
            max_output = getattr(info, "max_tokens", None)
            max_input = getattr(info, "max_input_tokens", None)
            check(
                f"{config.alias}.models_api",
                getattr(info, "id", None) == model.model_id,
                f"id {getattr(info, 'id', None)}, display {getattr(info, 'display_name', None)},"
                f" max_input {max_input}, max_output {max_output}",
            )
            check(
                f"{config.alias}.output_limit",
                isinstance(max_output, int) and max_output >= config.max_tokens,
                f"model max_tokens {max_output} >= requested {config.max_tokens}",
            )
            if config.thinking == "off":
                thinking_type = str(model.thinking_off)
                supported = _supported(capabilities, "thinking", "types", thinking_type)
                check(
                    f"{config.alias}.thinking_off",
                    supported is not False,
                    f"thinking {thinking_type} supported: {supported}",
                )
            models[config.alias] = {
                "id": getattr(info, "id", None),
                "display_name": getattr(info, "display_name", None),
                "created_at": str(getattr(info, "created_at", "")),
                "max_input_tokens": max_input,
                "max_tokens": max_output,
                "capabilities": capabilities,
            }
            per_model: dict[str, int] = {}
            worst = 0
            for sha, prompt in approved["prompts"].items():
                messages = _prompt_messages(sha)
                if messages is None:
                    check(f"{config.alias}.count.{prompt['key']}", False, "prompt not rebuilt")
                    continue
                if check_messages(messages) is not None:
                    # Never sent: the boundary may have become stricter since the approval.
                    check(f"{config.alias}.count.{prompt['key']}", False, "outside the boundary")
                    continue
                system, conversation = cb.to_anthropic(messages)
                try:
                    tokens = client.messages.count_tokens(
                        model=model.model_id,
                        system=system,
                        messages=conversation,
                        thinking=config.request_fields()["thinking"],
                        output_config=config.request_fields()["output_config"],
                    ).input_tokens
                except Exception as error:  # noqa: BLE001 - reported by class only
                    check(f"{config.alias}.count.{prompt['key']}", False, type(error).__name__)
                    continue
                per_model[sha] = int(tokens)
                reserved = cb.reservation_micro(model, int(tokens), config.max_tokens)
                worst = max(worst, reserved)
                worst_total += reserved
                if reserved > cb.PER_CALL_CEILING_MICRO_USD or tokens > cb.MAX_INPUT_TOKENS:
                    check(
                        f"{config.alias}.reservation.{prompt['key']}",
                        False,
                        f"{tokens} input tokens -> US${_usd(reserved)}",
                    )
            counted[config.alias] = per_model
            check(
                f"{config.alias}.counted",
                len(per_model) == len(approved["prompts"]),
                f"{len(per_model)} prompts counted; input tokens"
                f" {min(per_model.values(), default=0)}-{max(per_model.values(), default=0)};"
                f" largest reservation US${_usd(worst)}",
            )
    finally:
        client.close()
    calls = len(configs) * len(approved["prompts"])
    if status is not None:
        check(
            "ledger.room",
            status.committed_micro_usd + worst_total <= status.cap_micro_usd
            and status.calls + calls <= status.call_limit,
            f"worst case US${_usd(worst_total)} for {calls} calls; ledger committed"
            f" US${_usd(status.committed_micro_usd)} of US${_usd(status.cap_micro_usd)},"
            f" calls {status.calls}/{status.call_limit}",
        )
    check(
        "owner.credit_balance",
        balance >= worst_total,
        f"attested Console credit balance US${_usd(balance)} >= worst case US${_usd(worst_total)}",
    )
    passed = all(c["passed"] for c in checks)
    _write_json(
        PREFLIGHT,
        {
            "passed": passed,
            "at": datetime.now(UTC).isoformat(),
            "sdk": getattr(sdk, "__version__", "unknown"),
            "prompt_version": prompt_version(),
            "configs": {c.alias: {**c.describe(), "fingerprint": c.fingerprint()} for c in configs},
            "models": models,
            "counted": counted,
            "worst_case_micro_usd": worst_total,
            "attested_balance_micro_usd": balance,
            "checks": checks,
        },
    )
    print(f"PREFLIGHT {'PASS' if passed else 'FAIL'} -> {PREFLIGHT}")
    return 0 if passed else 3


_PROMPT_CACHE: dict[str, list[dict[str, str]]] = {}


def _prompt_messages(sha: str) -> list[dict[str, str]] | None:
    if not _PROMPT_CACHE:
        prompts, _ = build_prompts(_scenarios())
        for messages in prompts.values():
            _PROMPT_CACHE[cb.prompt_sha(messages)] = messages
    return _PROMPT_CACHE.get(sha)


# --- run (paid) -----------------------------------------------------------------------------


def _usable_preflight(configs: list[cb.BenchConfig]) -> dict[str, Any] | str:
    if not PREFLIGHT.exists():
        return "no preflight"
    data = _read_json(PREFLIGHT)
    if not data.get("passed"):
        return "the last preflight failed"
    age = datetime.now(UTC) - datetime.fromisoformat(data["at"])
    if age > PREFLIGHT_MAX_AGE or age < timedelta(0):
        return "the preflight is older than 12 hours"
    if data.get("prompt_version") != prompt_version():
        return "the prompt code changed since the preflight"
    for config in configs:
        recorded = data["configs"].get(config.alias)
        if recorded is None or recorded["fingerprint"] != config.fingerprint():
            return f"{config.alias}: settings differ from the preflight"
        if len(data["counted"].get(config.alias, {})) != 17:
            return f"{config.alias}: prompts not counted"
    return dict(data)


def _always(model: cb.ClaudeBenchModel) -> Callable[[Capture], Any]:
    return lambda capture: model


def cmd_run(args: argparse.Namespace) -> int:
    configs = _configs(args)
    scenarios = _scenarios()
    keys = scenarios.turn_keys()
    planned = len(configs) * len(keys)
    if args.expect_calls != planned:
        print(f"refused: {planned} calls planned but --expect-calls is {args.expect_calls}")
        return 2
    preflight = _usable_preflight(configs)
    if isinstance(preflight, str):
        print(f"refused: {preflight}; no request was made")
        return 3
    ledger = cb.ClaudeLedger(LEDGER)
    before = ledger.status()
    if before.breaker_open or before.open_calls or before.calls + planned > before.call_limit:
        print("refused: ledger breaker open, a call open, or not enough calls left")
        return 3
    try:
        cb.read_key(os.environ)
    except cb.LedgerRefusedError as error:
        print(f"refused: {error.code}")
        return 3
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    label = f"{stamp}-{args.label}"
    models = {
        config.alias: cb.ClaudeBenchModel(
            config,
            ledger,
            counted=preflight["counted"][config.alias],
            run_label=label,
            environ=os.environ,
        )
        for config in configs
    }
    turns: dict[str, list[TurnResult]] = {config.alias: [] for config in configs}
    stopped = None
    seen = dict.fromkeys(models, 0)
    with Workspace() as workspace:
        for index, key in enumerate(keys):
            order = configs[index % len(configs) :] + configs[: index % len(configs)]
            for config in order:
                if ledger.status().breaker_open:
                    stopped = ledger.status().breaker_code
                    break
                result = run(
                    scenarios,
                    _always(models[config.alias]),
                    workspace=workspace,
                    turns=frozenset({key}),
                )
                turns[config.alias].extend(result.turns)
                fresh = models[config.alias].records[seen[config.alias] :]
                seen[config.alias] = len(models[config.alias].records)
                record = fresh[-1] if fresh else None
                outcome = (
                    "no call"
                    if record is None
                    else f"refused {record.refused}"
                    if record.refused
                    else str(record.error_class or record.stop_reason)
                )
                print(
                    f"{key} {config.alias}: {result.turns[0].answered_by}"
                    f" ({result.turns[0].fallback_reason}), {outcome},"
                    f" US${_usd(record.charged_micro_usd if record else None)}"
                )
            if stopped:
                print(f"STOPPED: ledger breaker open ({stopped}); no further requests")
                break
    after = ledger.status()
    folder = OUT / "runs" / label
    questions = _questions(scenarios)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "answers.jsonl").open("w", encoding="utf-8") as handle:
        for alias, results in turns.items():
            for turn in results:
                handle.write(
                    json.dumps(
                        {
                            "model": alias,
                            "model_id": cb.APPROVED_MODELS[alias].model_id,
                            "key": turn.key,
                            "question": questions[turn.key],
                            "answered_by": turn.answered_by,
                            "fallback_reason": turn.fallback_reason,
                            "answer": turn.answer_text,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    _write_json(
        folder / "calls.json",
        {
            "note": "Content-free. Synthetic Claude API benchmark; answers are separate.",
            "label": label,
            "git_head": _git_head(),
            "prompt_version": prompt_version(),
            "questions_file": QUESTIONS.name,
            "order": "interleaved; the model order rotates by one per question",
            "configs": {c.alias: {**c.describe(), "fingerprint": c.fingerprint()} for c in configs},
            "preflight_at": preflight["at"],
            "models_api": preflight["models"],
            "ledger_before": before.__dict__,
            "ledger_after": after.__dict__,
            "stopped": stopped,
            "turns": {
                alias: [
                    {
                        "key": turn.key,
                        "answered_by": turn.answered_by,
                        "fallback_reason": turn.fallback_reason,
                        "shown": list(turn.shown),
                        "unmapped": turn.unmapped,
                        "offered": len(turn.offered),
                        "cited_entries": list(turn.cited_entries),
                        "metrics": {
                            **turn.metrics,
                            "profile": "claude_benchmark (evaluation only; not a runtime profile)",
                        },
                    }
                    for turn in results
                ]
                for alias, results in turns.items()
            },
            "calls": {
                alias: [record.__dict__ for record in model.records]
                for alias, model in models.items()
            },
        },
    )
    print(f"spent (ledger) US${_usd(after.committed_micro_usd - before.committed_micro_usd)}")
    cmd_status(args)
    print(f"wrote {folder}")
    settled = sum(
        1 for call in ledger.calls() if call["run_label"] == label and call["state"] == "settled"
    )
    print(f"settled calls in this run: {settled} of {planned} planned")
    return 0 if settled == planned and not after.breaker_open else 4


# --- report ---------------------------------------------------------------------------------


def _pct(values: list[int], share: float) -> int | None:
    """Nearest-rank percentile, as assistant_eval.scoring computes it."""

    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def _summary(turns: list[dict[str, Any]], calls: list[dict[str, Any]] | None) -> dict[str, Any]:
    count = len(turns)
    model_answers = [t for t in turns if t["answered_by"] == "model"]
    kept = sum(int(t["metrics"]["kept_lines"]) for t in turns)
    left = sum(int(t["metrics"]["left_out_lines"]) for t in turns)
    totals = [t["metrics"]["timings_ms"]["total"] for t in turns]
    firsts = [t["metrics"]["timings_ms"]["first_displayed_line"] for t in turns]
    first_piece = [t["metrics"]["timings_ms"]["first_model_piece"] for t in turns]
    usage = [t["metrics"].get("usage") or {} for t in turns]
    out: dict[str, Any] = {
        "questions": count,
        "model_answers": len(model_answers),
        "fallbacks": count - len(model_answers),
        "fallback_reasons": dict(
            sorted(
                {
                    r: sum(1 for t in turns if t["fallback_reason"] == r)
                    for r in {t["fallback_reason"] for t in turns}
                }.items()
            )
        ),
        "line_validity": round(kept / (kept + left), 3) if kept + left else None,
        "lines_kept": kept,
        "lines_withheld": left,
        "unsafe_displayed_lines": sum(int(t["unmapped"]) for t in turns),
        "cut_short": sum(1 for t in turns if t["metrics"]["cut_short"]),
        "mean_lines_selected": round(statistics.mean(len(t["shown"]) for t in model_answers), 2)
        if model_answers
        else None,
        "service_total_ms_p50": _pct([v for v in totals if v is not None], 0.5),
        "service_total_ms_p95": _pct([v for v in totals if v is not None], 0.95),
        "first_displayed_line_ms_p50": _pct([v for v in firsts if v is not None], 0.5),
        "first_displayed_line_ms_p95": _pct([v for v in firsts if v is not None], 0.95),
        "first_model_piece_ms_p50": _pct([v for v in first_piece if v is not None], 0.5),
        "prompt_tokens_mean": round(statistics.mean(u.get("prompt_tokens") or 0 for u in usage), 1)
        if usage
        else None,
        "output_tokens_mean": round(
            statistics.mean(u.get("completion_tokens") or 0 for u in usage), 1
        )
        if usage
        else None,
        "cost_micro_usd": sum(int(u.get("cost_micro_usd") or 0) for u in usage),
    }
    out["cost_per_model_answer_usd"] = (
        _usd(out["cost_micro_usd"] // len(model_answers)) if model_answers else None
    )
    if calls is not None:
        made = [c for c in calls if c.get("call_id") is not None]
        out["calls"] = len(made)
        out["call_errors"] = sum(1 for c in made if c.get("error_class"))
        out["refusals_before_send"] = sum(1 for c in calls if c.get("refused"))
        out["ttft_any_ms_p50"] = _pct(
            [c["timings_ms"]["first_block"] for c in made if c["timings_ms"].get("first_block")],
            0.5,
        )
        out["ttft_text_ms_p50"] = _pct(
            [c["timings_ms"]["first_text"] for c in made if c["timings_ms"].get("first_text")], 0.5
        )
        out["ttft_text_ms_p95"] = _pct(
            [c["timings_ms"]["first_text"] for c in made if c["timings_ms"].get("first_text")],
            0.95,
        )
        out["api_total_ms_p50"] = _pct(
            [c["timings_ms"]["total"] for c in made if c["timings_ms"].get("total")], 0.5
        )
        out["api_total_ms_p95"] = _pct(
            [c["timings_ms"]["total"] for c in made if c["timings_ms"].get("total")], 0.95
        )
        out["charged_usd"] = _usd(sum(int(c.get("charged_micro_usd") or 0) for c in made))
        out["output_tokens_max"] = max(
            ((c.get("usage") or {}).get("output_tokens") or 0 for c in made), default=0
        )
    return out


def _declines(answers: list[dict[str, Any]]) -> dict[str, Any]:
    alone = {
        a["key"] for a in answers if a["answered_by"] == "model" and a["answer"].strip() == DECLINE
    }
    return {
        "declined_alone": sorted(alone),
        "correct_declines": sorted(alone & EXPECTED_DECLINE),
        "unexpected_declines": sorted(alone - EXPECTED_DECLINE),
        "missed_declines": sorted(EXPECTED_DECLINE - alone),
    }


def _baseline(folders: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    turns: dict[str, dict[str, Any]] = {}
    answers: dict[str, dict[str, Any]] = {}
    versions = set()
    for folder in folders:
        calls = _read_json(folder / "calls.json")
        versions.add(calls["manifest"]["prompt_version"])
        for turn in calls["turns"]:
            turns[turn["key"]] = turn
        for line in (folder / "answers.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                answers[item["key"]] = item
    return list(turns.values()), list(answers.values()), ",".join(sorted(versions))


def cmd_report(args: argparse.Namespace) -> int:
    folder = Path(args.run)
    calls = _read_json(folder / "calls.json")
    answers = [
        json.loads(line)
        for line in (folder / "answers.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report: dict[str, Any] = {
        "run": calls["label"],
        "prompt_version": calls["prompt_version"],
        "models": {},
    }
    for alias, turns in calls["turns"].items():
        summary = _summary(turns, calls["calls"][alias])
        summary.update(_declines([a for a in answers if a["model"] == alias]))
        summary["config"] = calls["configs"][alias]
        report["models"][alias] = summary
    if args.baseline:
        base_turns, base_answers, version = _baseline([Path(p) for p in args.baseline])
        summary = _summary(base_turns, None)
        summary.update(_declines([{**a, "model": "gpt-oss"} for a in base_answers]))
        summary["prompt_version"] = version
        summary["version_matched"] = version == calls["prompt_version"]
        report["gpt_oss_baseline"] = summary
    _write_json(folder / "report.json", report)
    print(json.dumps(report, indent=1, default=str))
    return 0


# --- scoring (owner, offline) ---------------------------------------------------------------


def cmd_scoring(args: argparse.Namespace) -> int:
    import secrets

    folder = Path(args.run)
    calls = _read_json(folder / "calls.json")
    if calls["prompt_version"] != prompt_version():
        print("refused: the prompt code differs from the run's; scoring context would differ")
        return 2
    answers: dict[tuple[str, str], dict[str, Any]] = {}
    for line in (folder / "answers.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            answers[(item["key"], item["model"])] = item
    shown = {
        (turn["key"], alias): turn["shown"]
        for alias, turns in calls["turns"].items()
        for turn in turns
    }
    aliases = sorted(calls["turns"])
    scenarios = _scenarios()
    _, preps = build_prompts(scenarios)
    target = Path(args.out) if args.out else OUT / "scoring" / calls["label"]
    if (target / "scores.json").exists():
        print("refused: scores.json exists there; ratings are never overwritten")
        return 2
    items, blind = [], {}
    slots = [chr(ord("A") + i) for i in range(len(aliases))]
    for scenario in scenarios.scenarios:
        for index, question in enumerate(scenario.questions):
            key = scenario.turn_key(index)
            prep = preps[key]
            order = aliases[:]
            secrets.SystemRandom().shuffle(order)
            offered = [
                {"id": line.id, "source": line.source, "text": text, "entry": line.entry_id}
                for line, _, text in offered_lines(prep)
            ]
            item_answers = {}
            for slot, alias in zip(slots, order, strict=True):
                answer = answers.get((key, alias))
                if answer is None:
                    continue
                item_answers[slot] = {
                    "text": answer["answer"],
                    "answered_by": answer["answered_by"],
                    "fallback_reason": answer["fallback_reason"],
                    "model_chosen_ids": shown.get((key, alias), []),
                }
                blind[f"{key}|{slot}"] = {
                    "model": cb.APPROVED_MODELS[alias].model_id,
                    "run": calls["label"],
                }
            knowledge = next(
                (m["content"] for m in prep.messages if m["content"].startswith("KNOWLEDGE")), ""
            )
            items.append(
                {
                    "key": key,
                    "scenario": scenario.id,
                    "description": scenario.description,
                    "case": scenario.base,
                    "question": question,
                    "case_facts": prep.messages[1]["content"],
                    "knowledge": knowledge,
                    "offered": offered,
                    "gaps": [
                        "Anything not in the allowed lines below could not be shown"
                        " (exact-line guard)."
                    ],
                    "answers": dict(sorted(item_answers.items())),
                }
            )
    target.mkdir(parents=True, exist_ok=True)
    meta = {
        "note": "Claude API benchmark; blinded. Separate from the original Phase B ratings.",
        "prompt_version": calls["prompt_version"],
        "questions": len(items),
        "answers": sum(len(i["answers"]) for i in items),
    }
    _write_json(target / "items.json", {"meta": meta, "items": items})
    _write_json(target / "blind.json", blind)
    _write_json(target / "runs.json", {"included_runs": [calls["label"]]})
    if args.tool:
        tool = Path(args.tool)
        for name in ("scoring.py", "index.html"):
            shutil.copyfile(tool / name, target / name)
        _adapt_page(target / "index.html", len(slots))
    print(f"items {len(items)}, answers {meta['answers']} -> {target}")
    return 0


def _adapt_page(page: Path, slots: int) -> None:
    """The original page was written for two answers (A, B); allow ``slots`` of them."""

    text = page.read_text(encoding="utf-8")
    text = text.replace("return n===2?", "return n===Object.keys(it.answers).length?")
    text = text.replace(
        "Two answers, A and B, from two different models.",
        f"{slots} answers from {slots} different models.",
    )
    text = text.replace(
        ".sB{background:var(--chipB)}",
        ".sB{background:var(--chipB)}.sC{background:var(--chipA);outline:1px dashed}",
    )
    page.write_text(text, encoding="utf-8")


# --- CLI ------------------------------------------------------------------------------------


def _select_ledger(name: str) -> None:
    """Each experiment keeps its own ledger and preflight (``ledger`` is the first run's)."""

    global LEDGER, PREFLIGHT
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", name):
        raise SystemExit("--ledger must be 1-32 lower-case letters, digits or '-'")
    LEDGER = OUT / f"{name}.sqlite3"
    PREFLIGHT = OUT / ("preflight.json" if name == "ledger" else f"preflight-{name}.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--ledger",
        default="ledger",
        help="ledger name: data/eval/claude/<name>.sqlite3, with its own preflight file",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prompts").set_defaults(handler=cmd_prompts)
    init = sub.add_parser("init-ledger")
    init.add_argument("--cap-usd", required=True)
    init.add_argument("--per-call-usd", required=True)
    init.add_argument("--calls", type=int, required=True)
    init.set_defaults(handler=cmd_init_ledger)
    sub.add_parser("status").set_defaults(handler=cmd_status)
    rec = sub.add_parser("reconcile")
    rec.add_argument("--console-usage-usd", required=True)
    rec.add_argument("--tolerance-usd", default="0.01")
    rec.set_defaults(handler=cmd_reconcile)

    def model_options(command: argparse.ArgumentParser) -> None:
        command.add_argument("--models", required=True, help="haiku,sonnet,opus")
        command.add_argument("--effort", default="medium", choices=cb.EFFORTS)
        command.add_argument("--thinking", default="adaptive", choices=("adaptive", "off"))
        command.add_argument("--max-tokens", type=int, default=3000)

    pre = sub.add_parser("preflight")
    model_options(pre)
    pre.add_argument("--owner-attests-credit-balance-usd", required=True)
    pre.add_argument("--owner-attests-auto-reload-off", action="store_true")
    pre.set_defaults(handler=cmd_preflight)
    go = sub.add_parser("run")
    model_options(go)
    go.add_argument("--expect-calls", type=int, required=True)
    go.add_argument("--label", default="initial")
    go.set_defaults(handler=cmd_run)
    rep = sub.add_parser("report")
    rep.add_argument("--run", required=True)
    rep.add_argument("--baseline", nargs="*", default=[])
    rep.set_defaults(handler=cmd_report)
    sco = sub.add_parser("scoring")
    sco.add_argument("--run", required=True)
    sco.add_argument("--out", default="")
    sco.add_argument("--tool", default="", help="folder holding scoring.py and index.html")
    sco.set_defaults(handler=cmd_scoring)
    args = parser.parse_args(argv)
    _select_ledger(args.ledger)
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except cb.BenchConfigError as error:
        print(f"refused: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
