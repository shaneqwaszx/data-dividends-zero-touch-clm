"""Write a run's scores as JSON and Markdown.

Every report starts with its result kind and banner, so an evaluator self-test can never be
read as a model result. Per-turn rows carry line ids, codes and counts only.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .runner import RunResult
from .scoring import Scores


def report_data(run: RunResult, scores: Scores, extra: dict[str, str]) -> dict[str, Any]:
    return {
        "result_kind": scores.result_kind,
        "banner": scores.banner,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "manifest": {**run.manifest, **extra, "model": run.model, "reps": str(run.reps)},
        "overall": scores.overall,
        "gold": scores.gold,
        "stability": scores.stability,
        "consistency": scores.consistency,
        "drifted_turns": list(scores.drifted_turns),
        "by_tag": scores.by_tag,
        "turns": [
            {
                "key": turn.key,
                "rep": turn.rep,
                "answered_by": turn.answered_by,
                "fallback_reason": turn.fallback_reason,
                "shown": list(turn.shown),
                "unmapped": turn.unmapped,
                "offered": len(turn.offered),
                "cited_entries": list(turn.cited_entries),
                "drift": turn.drift,
            }
            for turn in run.turns
        ],
    }


def _value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items()) or "-"
    return str(value)


def markdown(data: dict[str, Any]) -> str:
    lines = [
        f"# AI Assistant offline evaluation - {data['result_kind']}",
        "",
        f"> {data['banner']}",
        "",
        "| Run | Value |",
        "|---|---|",
        *(f"| {key} | {_value(value)} |" for key, value in sorted(data["manifest"].items())),
        f"| generated_at | {data['generated_at']} |",
        "",
        "## Label-free measures (all turns)",
        "",
        "| Measure | Value |",
        "|---|---|",
        *(f"| {key} | {_value(value)} |" for key, value in data["overall"].items()),
        f"| stability (mean Jaccard across reps) | {_value(data['stability'])} |",
        f"| consistency (conversation vs single) | {_value(data['consistency'])} |",
        "",
        "## Gold-based measures",
        "",
    ]
    if data["gold"] is None:
        lines.append(
            "NOT LABELLED: no locked owner/team gold was given, so there is no quality score."
        )
    else:
        lines += ["| Measure | Value |", "|---|---|"]
        lines += [f"| {key} | {_value(value)} |" for key, value in data["gold"].items()]
    lines += [
        "",
        "## By scenario tag",
        "",
        "| Tag | Answers | Fallback rate | Validity | Unsafe | F1 micro |",
        "|---|---|---|---|---|---|",
    ]
    for tag, entry in data["by_tag"].items():
        gold = entry.get("gold") or {}
        lines.append(
            f"| {tag} | {entry['answers']} | {_value(entry['fallback_rate'])} | "
            f"{_value(entry['line_validity_rate'])} | {entry['unsafe_display']} | "
            f"{_value(gold.get('f1_micro'))} |"
        )
    lines += [
        "",
        "## Snapshot drift",
        "",
        ", ".join(data["drifted_turns"]) or "None: every question offered its frozen lines.",
        "",
    ]
    return "\n".join(lines)


def write(
    run: RunResult, scores: Scores, out_dir: Path, extra: dict[str, str]
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = report_data(run, scores, extra)
    stamp = data["generated_at"].replace(":", "").replace("-", "")
    model = run.model.replace("/", "_").replace(":", "_")
    stem = f"eval-{data['result_kind'].lower()}-{model}-{stamp}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    md_path.write_text(markdown(data), encoding="utf-8")
    return json_path, md_path
