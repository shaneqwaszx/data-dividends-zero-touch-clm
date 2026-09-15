"""Print deterministic, read-only development context without loading secrets."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_BLOCK = re.compile(r"```json project-state\s*\n(?P<body>.*?)\n```", re.DOTALL)
SKILL_ROW = re.compile(r"^\| `(?P<name>[a-z0-9-]+)` \|", re.MULTILINE)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        shell=False,
    )


def _git_value(root: Path, *args: str) -> str:
    result = _git(root, *args)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def _repository_root(candidate: Path) -> Path:
    result = _git(candidate.resolve(), "rev-parse", "--show-toplevel")
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("not a Git worktree")
    return Path(result.stdout.strip()).resolve()


def _branch_label(root: Path) -> str:
    result = _git(root, "branch", "--show-current")
    if result.returncode != 0:
        return "UNAVAILABLE"
    return result.stdout.strip() or "DETACHED"


def load_state(root: Path) -> dict[str, object]:
    match = STATE_BLOCK.search(_read_text(root / "docs" / "PROJECT_STATE.md"))
    if match is None:
        raise ValueError("PROJECT_STATE metadata block is missing")
    value = json.loads(match.group("body"))
    if not isinstance(value, dict):
        raise TypeError("PROJECT_STATE metadata must be an object")
    return value


def render_context(root: Path) -> str:
    root = _repository_root(root)
    state = load_state(root)
    branch = _branch_label(root)
    head = _git_value(root, "rev-parse", "HEAD")
    origin = _git_value(root, "rev-parse", "origin/main")
    merge_base = _git_value(root, "merge-base", "HEAD", "origin/main")
    relationship = _git_value(
        root, "rev-list", "--left-right", "--count", "origin/main...HEAD"
    )
    status = _git_value(root, "status", "--short", "--untracked-files=no")
    providers = state.get("providers", {})
    questions = state.get("open_sponsor_questions", [])
    skill_index = _read_text(root / ".agents" / "skills" / "README.md")
    skills = sorted(set(SKILL_ROW.findall(skill_index)))

    lines = [
        "DEVELOPMENT CONTEXT",
        f"Repository root: {root.resolve()}",
        f"Branch: {branch}",
        f"HEAD: {head}",
        f"origin/main: {origin}",
        f"Merge base: {merge_base}",
        f"Ahead/behind (origin/main...HEAD): {relationship}",
        f"Tracked working tree: {status or 'clean'}",
        f"Project-state verified date: {state.get('verified_date', 'UNAVAILABLE')}",
        f"Project-state main baseline: {state.get('verified_main_sha', 'UNAVAILABLE')}",
        "Documented providers:",
    ]
    if isinstance(providers, dict):
        for key in sorted(providers):
            value = providers[key]
            if isinstance(value, dict):
                lines.append(
                    f"  {key}: {value.get('name', 'UNKNOWN')} / "
                    f"mode={value.get('mode', 'UNKNOWN')} / "
                    f"classification={value.get('classification', 'UNKNOWN')}"
                )
    lines.extend(
        [
            "Open sponsor questions: " + ", ".join(map(str, questions)),
            "Workflow: docs/DEVELOPMENT_WORKFLOW.md",
            "Repository skills: " + ", ".join(skills),
            "Pre-PR command: python scripts/pre_pr_check.py",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        print(render_context(args.root.resolve()))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"DEVELOPMENT CONTEXT ERROR: {type(error).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
