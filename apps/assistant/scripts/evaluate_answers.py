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

A local model URL must be a literal loopback address and no proxy may be set; anything else
is refused before any request.
"""

import argparse
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from ai_assistant.llm import ChatModel  # noqa: E402
from assistant_eval import gold as gold_mod  # noqa: E402
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
from assistant_eval.scenarios import EVAL_FIXTURES, load_scenarios  # noqa: E402
from assistant_eval.scoring import score  # noqa: E402
from assistant_eval.snapshot import SnapshotSet  # noqa: E402

SNAPSHOTS = EVAL_FIXTURES / "snapshots.json"
GOLD = EVAL_FIXTURES / "gold.json"
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


def cmd_run(args: argparse.Namespace) -> int:
    scenarios = load_scenarios()
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
    with Workspace() as workspace:
        result = run(scenarios, make, reps=args.reps, snapshots=snapshots, workspace=workspace)
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
    go.add_argument("--model", required=True, choices=["self-test-perfect", *SELF_TESTS, "local"])
    go.add_argument("--base-url", default="http://127.0.0.1:11434/v1")
    go.add_argument("--model-name", default="ministral-3:8b")
    go.add_argument("--reps", type=int, default=1)
    go.add_argument("--out", default=str(OUT))
    go.set_defaults(func=cmd_run)
    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
