"""Offline evaluation of the AI Assistant's answers: no remote model, no spend.

    cd apps/assistant
    ../../.venv/bin/python scripts/evaluate_answers.py check
    ../../.venv/bin/python scripts/evaluate_answers.py snapshot --write-fixture
    ../../.venv/bin/python scripts/evaluate_answers.py stubs
    ../../.venv/bin/python scripts/evaluate_answers.py worksheet
    ../../.venv/bin/python scripts/evaluate_answers.py lock
    ../../.venv/bin/python scripts/evaluate_answers.py run --model self-test-perfect
    ../../.venv/bin/python scripts/evaluate_answers.py run --model self-test-random --reps 2
    ../../.venv/bin/python scripts/evaluate_answers.py run --model local \\
        --base-url http://127.0.0.1:11434/v1 --model-name ministral-3:8b
    ../../.venv/bin/python scripts/evaluate_answers.py preflight \\
        --owner-attests-auto-topup-off --owner-attests-prompt-logging-off
    ../../.venv/bin/python scripts/evaluate_answers.py run --model openrouter \\
        --scenarios tests/fixtures/eval/phase_b_questions.json --only P00 \\
        --owner-attests-auto-topup-off --owner-attests-prompt-logging-off

check      are the frozen snapshots (tests/fixtures/eval/snapshots.json) still what the
           service offers? A prompt, catalog or retrieval change makes them drift.
snapshot   rebuild the snapshots (to data/eval/, or the fixture with --write-fixture).
stubs      write gold stubs for every snapshot turn into tests/fixtures/eval/gold.json,
           keeping turns the owner/team already labelled. The harness never labels.
worksheet  a Markdown list of each question's allowed lines with their ids, for labelling.
lock       freeze the owner/team labels against the snapshots (gold.lock.json).
run        ask every question and score it. Self-test models check the harness only and use
           synthetic self-test gold; a local model is scored against locked owner gold when
           there is one, otherwise label-free only. Reports go to data/eval/ (not in Git).
preflight  Phase B (D-092, proposed): every check a live run needs, without inference.
recheck    Phase B: a read-only second look at quarantined calls' generation metadata (no
           inference; changes neither the calls' verification nor the breaker).

A local model URL must be a literal loopback address and no proxy may be set; anything else
is refused before any request. ``--model openrouter`` (Phase B, synthetic scenarios only) needs
OPENROUTER_API_KEY, AI_ASSISTANT_REMOTE_INFERENCE_DECISION and AI_ASSISTANT_REMOTE_LIVE_DECISION
in the process environment, an initialised budget ledger, and a passing preflight in the same
run; it spends real credits. Its answers go to answers.jsonl, its content-free telemetry,
ledger and provider-verification rows to calls.json (both under data/eval/phase_b/).
"""

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.budget import BudgetLedger, LedgerError  # noqa: E402
from ai_assistant.config import AiAssistantSettings  # noqa: E402
from ai_assistant.llm import ChatModel  # noqa: E402
from ai_assistant.model_factory import (  # noqa: E402
    build_account_client,
    build_chat_model,
    ledger_path,
)
from ai_assistant.model_profiles import (  # noqa: E402
    APPROVED_PROFILES,
    OPENROUTER_PROFILE_ID,
    ProfileConfigError,
)
from ai_assistant.openrouter_account import AccountCheckError, OpenRouterAccount  # noqa: E402
from assistant_eval import gold as gold_mod  # noqa: E402
from assistant_eval import live  # noqa: E402
from assistant_eval.models import (  # noqa: E402
    SELF_TESTS,
    Capture,
    GoldSelector,
    RemoteModelRefusedError,
    SelectorModel,
    local_model,
)
from assistant_eval.report import write  # noqa: E402
from assistant_eval.runner import Workspace, build_snapshots, run  # noqa: E402
from assistant_eval.scenarios import (  # noqa: E402
    EVAL_FIXTURES,
    SCENARIOS_FILE,
    ScenarioSet,
    load_scenarios,
)
from assistant_eval.scoring import score  # noqa: E402
from assistant_eval.snapshot import SnapshotSet  # noqa: E402

SNAPSHOTS = EVAL_FIXTURES / "snapshots.json"
GOLD = EVAL_FIXTURES / "gold.json"
PHASE_B_QUESTIONS = EVAL_FIXTURES / "phase_b_questions.json"
LOCK = EVAL_FIXTURES / "gold.lock.json"
OUT = HERE / "data" / "eval"


def _snapshots(path: Path = SNAPSHOTS) -> SnapshotSet:
    return SnapshotSet.model_validate_json(path.read_text(encoding="utf-8"))


def _gold() -> gold_mod.GoldSet | None:
    if not GOLD.exists():
        return None
    return gold_mod.GoldSet.model_validate_json(GOLD.read_text(encoding="utf-8"))


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def cmd_check(_: argparse.Namespace) -> int:
    frozen = _snapshots()
    current = build_snapshots(load_scenarios())
    if current.sha256() == frozen.sha256():
        print(f"snapshots are current ({len(frozen.turns)} turns, sha256 {frozen.sha256()[:16]})")
        return 0
    changed = sorted(
        key
        for key in set(frozen.turns) | set(current.turns)
        if frozen.turns.get(key) != current.turns.get(key)
    )
    print(f"snapshots drifted: {len(changed)} turns differ ({', '.join(changed[:12])} ...)")
    if frozen.built_with != current.built_with:
        print("  built_with changed:", {k: v for k, v in current.built_with.items()})
    print("Rebuild with `snapshot --write-fixture`, then `stubs`; owner labels need review.")
    return 1


def cmd_snapshot(args: argparse.Namespace) -> int:
    snapshots = build_snapshots(load_scenarios())
    target = SNAPSHOTS if args.write_fixture else OUT / "snapshots.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(snapshots.to_json(), encoding="utf-8")
    print(f"wrote {target} ({len(snapshots.turns)} turns, {len(snapshots.lines)} lines)")
    return 0


def cmd_stubs(_: argparse.Namespace) -> int:
    existing = _gold()
    gold = gold_mod.stubs(_snapshots(), existing)
    GOLD.write_text(gold.to_json(), encoding="utf-8")
    labelled = len(gold.labelled())
    print(f"wrote {GOLD}: {len(gold.turns)} turns, {labelled} labelled by the owner/team")
    return 0


def cmd_worksheet(args: argparse.Namespace) -> int:
    snapshots = _snapshots()
    scenarios = load_scenarios()
    rows = [
        "# Gold labelling worksheet (synthetic scenarios)",
        "",
        "Write labels in tests/fixtures/eval/gold.json (decision A-6: owner/team only).",
        "",
    ]
    for scenario in scenarios.scenarios:
        rows += [f"## {scenario.id} - {scenario.description}", ""]
        for index, question in enumerate(scenario.questions):
            key = scenario.turn_key(index)
            rows += [f"### {key}: {question}", ""]
            for item in snapshots.turns[key].offered:
                line = snapshots.lines[item.id]
                tag = f" [{item.tag}]" if item.tag else ""
                rows.append(f"- `{item.id}`{tag} {line.text}")
            rows.append("")
    target = Path(args.out) / "LABELLING_WORKSHEET.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(rows), encoding="utf-8")
    print(f"wrote {target}")
    return 0


def cmd_lock(_: argparse.Namespace) -> int:
    gold = _gold()
    if gold is None:
        print("no gold.json: run `stubs` first")
        return 1
    try:
        locked = gold_mod.lock(gold, _snapshots())
    except gold_mod.GoldError as exc:
        print(f"not locked: {exc}")
        return 1
    LOCK.write_text(locked.model_dump_json(indent=1) + "\n", encoding="utf-8")
    print(f"locked {locked.labelled_turns}/{locked.total_turns} labelled turns")
    return 0


def _owner_gold(
    snapshots: SnapshotSet,
) -> tuple[gold_mod.GoldSet, gold_mod.GoldLock] | None:
    gold = _gold()
    if gold is None or not LOCK.exists():
        return None
    locked = gold_mod.GoldLock.model_validate_json(LOCK.read_text(encoding="utf-8"))
    gold_mod.verify(gold, locked, snapshots)
    return gold, locked


def _remote_settings(args: argparse.Namespace) -> AiAssistantSettings:
    """The remote profile's settings: decisions from the process environment (an operator
    act), everything else from the command line; ``.env`` files are never read."""

    return AiAssistantSettings.model_construct(
        llm_enabled=True,
        knowledge_enabled=True,
        llm_profile=OPENROUTER_PROFILE_ID,
        remote_inference_decision=os.environ.get("AI_ASSISTANT_REMOTE_INFERENCE_DECISION", ""),
        remote_live_decision=os.environ.get("AI_ASSISTANT_REMOTE_LIVE_DECISION", ""),
        openrouter_endpoint=args.endpoint,
        llm_reasoning_effort=args.reasoning_effort,
        llm_reasoning_allowance_tokens=args.reasoning_allowance,
        llm_max_answer_tokens=args.answer_tokens,
    )


Session = tuple[live.Preflight, AiAssistantSettings, BudgetLedger | None, OpenRouterAccount | None]


def _preflight(args: argparse.Namespace) -> Session:
    """Every live-run check, failing closed at the first one that cannot be evaluated."""

    report = live.Preflight()
    settings = _remote_settings(args)
    endpoint = APPROVED_PROFILES[OPENROUTER_PROFILE_ID].endpoint(settings.openrouter_endpoint)
    if endpoint is None:
        report.add("endpoint.approved", False, "the endpoint is not in the approved registry")
        return report, settings, None, None
    try:
        account = build_account_client(settings, allow_live_network=True)
    except ProfileConfigError as error:
        report.add("gate.account", False, f"refused: {error.code}")
        return report, settings, None, None
    report.add("gate.account", True, "live gate and decisions named; key present (not shown)")
    try:
        listing = live.fetch_public("/models/openai/gpt-oss-120b/endpoints")
        zdr = live.fetch_public("/endpoints/zdr")
    except Exception as error:  # noqa: BLE001 - any failure to read the listing refuses
        report.add("endpoint.listing", False, f"unreadable ({type(error).__name__})")
        return report, settings, None, account
    live.check_endpoint(report, endpoint, listing, zdr)
    try:
        key = account.key_status()
    except AccountCheckError as error:
        report.add("key.status", False, f"refused: {error.code}")
        return report, settings, None, account
    max_tokens = settings.llm_max_answer_tokens + settings.llm_reasoning_allowance_tokens
    reservation = live.typical_reservation(endpoint, max_tokens)
    live.check_key(report, key, reservation)
    live.check_owner(
        report, args.owner_attests_auto_topup_off, args.owner_attests_prompt_logging_off
    )
    try:
        ledger = BudgetLedger.open(ledger_path(settings))
        ledger.recover()
        status = ledger.status()
    except LedgerError as error:
        report.add("ledger.healthy", False, f"refused: {error.code}")
        return report, settings, None, account
    report.add("ledger.healthy", True, f"profile {status.profile_id}, alias {status.key_alias}")
    try:
        live.verify_earlier_calls(report, ledger, account, endpoint)
        status = ledger.status()
    except LedgerError as error:
        report.add("ledger.earlier_calls_verified", False, f"refused: {error.code}")
        return report, settings, None, account
    live.check_ledger(report, key, status, ledger.last_call_id() > 0, reservation)
    return report, settings, ledger, account


def cmd_preflight(args: argparse.Namespace) -> int:
    report, *_ = _preflight(args)
    print("\n".join(report.lines()))
    print("PREFLIGHT " + ("PASS" if report.passed else "FAIL"))
    return 0 if report.passed else 1


def cmd_recheck(args: argparse.Namespace) -> int:
    """Read-only: fetch generation metadata again for quarantined calls. No inference."""

    report = live.Preflight()
    settings = _remote_settings(args)
    endpoint = APPROVED_PROFILES[OPENROUTER_PROFILE_ID].endpoint(settings.openrouter_endpoint)
    rows: list[live.CallRow] = []
    try:
        if endpoint is None:
            report.add("endpoint.approved", False, "the endpoint is not in the approved registry")
            return 1
        try:
            account = build_account_client(settings, allow_live_network=True)
            ledger = BudgetLedger.open(ledger_path(settings))
            key = account.key_status()
        except (ProfileConfigError, LedgerError, AccountCheckError) as error:
            report.add("recheck.ready", False, f"refused: {error.code}")
            return 1
        rows = live.recheck_quarantined(report, ledger, account, endpoint, key)
        return 0 if report.passed else 1
    finally:
        print("\n".join(report.lines()))
        print("RECHECK " + ("PASS" if report.passed else "FAIL"))
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        folder = Path(args.out) / "phase_b" / f"{stamp}-recheck"
        folder.mkdir(parents=True, exist_ok=True)
        record = {
            "note": "Content-free. Read-only recheck of quarantined Phase B calls (D-092).",
            "git_head": _git_head(),
            "checks": [vars(check) for check in report.checks],
            "calls": [vars(row) for row in rows],
        }
        target = folder / "recheck.json"
        target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {target}")


def _run_openrouter(args: argparse.Namespace, scenarios: ScenarioSet, only: set[str] | None) -> int:
    # Live runs ask only the reviewed Phase B questions, and only the named scenarios.
    if Path(args.scenarios).resolve() != PHASE_B_QUESTIONS.resolve() or not only:
        print(f"refused: a live run needs --scenarios {PHASE_B_QUESTIONS.name} and --only")
        return 2
    report, settings, ledger, account = _preflight(args)
    print("\n".join(report.lines()))
    endpoint = APPROVED_PROFILES[OPENROUTER_PROFILE_ID].endpoint(settings.openrouter_endpoint)
    if not report.passed or ledger is None or account is None or endpoint is None:
        print("PREFLIGHT FAIL: no request was made")
        return 3
    try:
        model = build_chat_model(
            settings, budget_ledger=ledger_path(settings), allow_live_network=True
        )
    except ProfileConfigError as error:
        print(f"refused: {error.code}")
        return 3
    monitor = live.LiveMonitor(model, ledger, account, endpoint)
    before = ledger.status()
    try:
        with Workspace() as workspace:
            result = run(scenarios, lambda capture: monitor, workspace=workspace, only=only)
    finally:
        # Verify what was spent even when the run stops early; leftovers (for example after
        # Ctrl-C here) are verified by the next preflight before any new call.
        monitor.finish()
        for row in monitor.rows:
            print(f"call {row.call_id} {row.turn}: {row.state} {row.verification}")
    after = ledger.status()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    questions = {
        scenario.turn_key(index): question
        for scenario in scenarios.scenarios
        for index, question in enumerate(scenario.questions)
    }
    answers, calls = live.write_artifacts(
        Path(args.out) / "phase_b" / f"{stamp}-{args.label}",
        run=result,
        questions=questions,
        monitor=monitor,
        preflight=report,
        settings={
            "endpoint": settings.openrouter_endpoint,
            "reasoning_effort": settings.llm_reasoning_effort,
            "reasoning_allowance_tokens": settings.llm_reasoning_allowance_tokens,
            "answer_tokens": settings.llm_max_answer_tokens,
            "temperature": settings.llm_temperature,
            "timeout_seconds": settings.llm_timeout_seconds,
        },
        ledger_before=before,
        ledger_after=after,
        extra={"git_head": _git_head(), "scenarios_file": str(args.scenarios), "label": args.label},
    )
    quarantined = sum(1 for row in monitor.rows if row.verification == "quarantined")
    print(
        f"calls {len(monitor.rows)}, quarantined {quarantined}, breaker open {after.breaker_open}"
    )
    print(f"wrote {answers}\nwrote {calls}")
    return 0 if quarantined == 0 and not after.breaker_open else 4


def cmd_run(args: argparse.Namespace) -> int:
    scenario_file = Path(args.scenarios)
    scenarios = load_scenarios(scenario_file)
    default_set = scenario_file.resolve() == SCENARIOS_FILE.resolve()
    only = set(args.only.split(",")) if args.only else None
    if args.model == "openrouter":
        return _run_openrouter(args, scenarios, only)
    snapshots = _snapshots()
    make: Callable[[Capture], ChatModel]
    gold: gold_mod.GoldSet | None
    gold_lock: gold_mod.GoldLock | None = None
    if args.model == "local":
        try:
            model = local_model(base_url=args.base_url, model=args.model_name)
        except RemoteModelRefusedError as exc:
            print(f"refused: {exc}")
            return 2
        make = lambda capture: model  # noqa: E731
        try:
            owner = _owner_gold(snapshots)
        except gold_mod.GoldError as exc:
            print(f"owner gold not used: {exc}")
            owner = None
        gold, gold_lock = owner if owner is not None else (None, None)
    else:
        gold = gold_mod.self_test_gold(snapshots)
        if args.model == "self-test-perfect":
            choices = {
                key: [*turn.primary, *(x for x in turn.relevant if x not in turn.primary)]
                for key, turn in gold.turns.items()
            }
            make = lambda capture: SelectorModel(GoldSelector(choices), capture)  # noqa: E731
        else:
            selector = SELF_TESTS[args.model]
            make = lambda capture: SelectorModel(selector(), capture)  # noqa: E731
    if not default_set and args.model == "local":
        # No snapshots or owner gold exist for another scenario file: label-free only.
        gold, gold_lock = None, None
    with Workspace() as workspace:
        result = run(
            scenarios,
            make,
            reps=args.reps,
            snapshots=snapshots if default_set else None,
            workspace=workspace,
            only=only,
        )
    if args.save_answers:
        _save_answers(Path(args.out) / "answers", args.model, result.turns)
    scores = score(result, scenarios, snapshots, gold, gold_lock)
    json_path, md_path = write(
        result,
        scores,
        Path(args.out),
        {"git_head": _git_head(), "snapshots_sha256": snapshots.sha256()[:16]},
    )
    print(scores.banner)
    print(f"wrote {json_path}\nwrote {md_path}")
    return 0


def _save_answers(folder: Path, label: str, turns: list) -> None:  # type: ignore[type-arg]
    """Synthetic answer text for a local comparison run (kept apart from the report)."""

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = folder / f"{stamp}-{label}" / "answers.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "key": turn.key,
            "rep": turn.rep,
            "answered_by": turn.answered_by,
            "fallback_reason": turn.fallback_reason,
            "answer": turn.answer_text,
            "total_ms": turn.metrics["timings_ms"]["total"],
        }
        for turn in turns
    ]
    target.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    print(f"wrote {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--write-fixture", action="store_true")
    snap.set_defaults(func=cmd_snapshot)
    sub.add_parser("stubs").set_defaults(func=cmd_stubs)
    sheet = sub.add_parser("worksheet")
    sheet.add_argument("--out", default=str(OUT))
    sheet.set_defaults(func=cmd_worksheet)
    sub.add_parser("lock").set_defaults(func=cmd_lock)
    go = sub.add_parser("run")
    go.add_argument(
        "--model", required=True, choices=["self-test-perfect", *SELF_TESTS, "local", "openrouter"]
    )
    go.add_argument("--scenarios", default=str(SCENARIOS_FILE))
    go.add_argument("--only", default="", help="comma-separated scenario ids")
    go.add_argument("--save-answers", action="store_true", help="keep answer text (local runs)")
    go.add_argument("--label", default="run", help="folder label (openrouter runs)")
    go.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    go.add_argument("--model-name", default="ministral-3:8b")
    go.add_argument("--reps", type=int, default=1)
    go.add_argument("--out", default=str(OUT))
    check = sub.add_parser("preflight")
    recheck = sub.add_parser("recheck")
    recheck.add_argument("--out", default=str(OUT))
    for command in (go, check, recheck):
        command.add_argument("--endpoint", default="deepinfra/bf16")
        command.add_argument(
            "--reasoning-effort", default="medium", choices=["low", "medium", "high"]
        )
        command.add_argument("--reasoning-allowance", type=int, default=1400)
        command.add_argument("--answer-tokens", type=int, default=600)
        command.add_argument("--owner-attests-auto-topup-off", action="store_true")
        command.add_argument("--owner-attests-prompt-logging-off", action="store_true")
    go.set_defaults(func=cmd_run)
    check.set_defaults(func=cmd_preflight)
    recheck.set_defaults(func=cmd_recheck)
    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
