"""Print deterministic, read-only development context without loading secrets."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_BLOCK = re.compile(r"```json project-state\s*\n(?P<body>.*?)\n```", re.DOTALL)
SKILL_ROW = re.compile(r"^\| `(?P<name>[a-z0-9-]+)` \|", re.MULTILINE)
HEADING = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$", re.MULTILINE)

CANONICAL_CONTEXT_PATHS = (
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "docs/PROJECT_STATE.md",
)
BENCHMARK_BASE_SHA = "83f46e20a9ad36ae61aacb0f470c1404c4732d64"
FULL_CONTEXT_PATHS = (
    *CANONICAL_CONTEXT_PATHS,
    ".agents/skills/README.md",
    ".ai-pipeline/README.md",
    "docs/CODEX_WORKFLOW.md",
    "docs/development/BRANCH_MERGE_PROTOCOL.md",
    "docs/sponsor-questions/OPEN_QUESTIONS.md",
)
CHANGE_CLASSES = (
    "DOCS_ONLY",
    "FRONTEND_UI",
    "FRONTEND_STATE_CACHE",
    "BACKEND_DOMAIN",
    "BACKEND_API",
    "AUTH_RBAC_SECURITY",
    "PERSISTENCE",
    "EXTERNAL_PROVIDER",
    "ARCHITECTURE_REFACTOR",
    "CI_TOOLING",
)
ROUTINE_CHANGE_CLASSES = ("DOCS_ONLY", "FRONTEND_UI", "CI_TOOLING")
HIGH_RISK_CHANGE_CLASSES = (
    "AUTH_RBAC_SECURITY",
    "PERSISTENCE",
    "EXTERNAL_PROVIDER",
)
SELECTIVE_CHANGE_CLASSES = (
    *ROUTINE_CHANGE_CLASSES,
    "FRONTEND_STATE_CACHE",
)

COMMON_SECTION_CONTEXT: dict[str, tuple[str, ...] | None] = {
    "AGENTS.md": None,
    "docs/ARCHITECTURE.md": (
        "1. Purpose and scope",
        "15. Security boundaries",
        "16. Provider/integration matrix",
        "17. Architecture invariants",
        "18. Explicit non-goals and prohibited assumptions",
        "20. Rules for changing architecture",
    ),
    "docs/DEVELOPMENT_WORKFLOW.md": (
        "Lifecycle",
        "Task start",
        "Context tiers and deterministic retrieval",
        "Planning, handoffs and evidence identity",
        "Coordination and model routing",
        "Change classes and required verification",
        "Focused, broad and independent evidence",
        "Specialized skill routing",
        "Stop conditions",
        "Sponsor-authority criteria",
        "Integration and PR readiness",
    ),
    "docs/PROJECT_STATE.md": (
        "Verification metadata",
        "Current External Integration Truth",
        "Evidence authority labels",
        "Current explicit non-capabilities",
        "Current open sponsor blockers",
    ),
}

CLASS_SECTION_CONTEXT: dict[str, dict[str, tuple[str, ...]]] = {
    "DOCS_ONLY": {},
    "FRONTEND_UI": {
        "docs/ARCHITECTURE.md": (
            "3. Bounded-context and canonical-owner map",
            "14. Frontend and React Query architecture",
            "19. Known hotspots and debt",
        ),
        "docs/PROJECT_STATE.md": ("Phase 15C frontend URL navigation",),
    },
    "FRONTEND_STATE_CACHE": {
        "docs/ARCHITECTURE.md": (
            "3. Bounded-context and canonical-owner map",
            "14. Frontend and React Query architecture",
            "19. Known hotspots and debt",
        ),
        "docs/PROJECT_STATE.md": (
            "Authentication, authorization and administration",
            "Phase 15C frontend URL navigation",
        ),
    },
    "CI_TOOLING": {
        "docs/ARCHITECTURE.md": ("19. Known hotspots and debt",),
        "docs/DEVELOPMENT_WORKFLOW.md": ("Conditional retrieval/RAG decision gate",),
        "docs/PROJECT_STATE.md": ("Repository and development tooling",),
    },
}

CLASS_SKILLS: dict[str, tuple[str, ...]] = {
    "FRONTEND_STATE_CACHE": (".agents/skills/frontend-state-cache-change/SKILL.md",),
    "AUTH_RBAC_SECURITY": (".agents/skills/integration-security-review/SKILL.md",),
    "PERSISTENCE": (".agents/skills/persistence-schema-change/SKILL.md",),
    "EXTERNAL_PROVIDER": (
        ".agents/skills/external-provider-integration/SKILL.md",
        ".agents/skills/integration-security-review/SKILL.md",
    ),
    "ARCHITECTURE_REFACTOR": (".agents/skills/architecture-change-review/SKILL.md",),
}


class ContextSelectionError(ValueError):
    """A safe narrow selection cannot be produced for the requested input."""


@dataclass(frozen=True)
class ContextReference:
    path: str
    sections: tuple[str, ...] | None
    tier: int
    reason: str


@dataclass(frozen=True)
class Footprint:
    documents: int
    sections: int
    characters: int
    bytes: int
    lines: int


# Frozen from BENCHMARK_BASE_SHA so shallow CI checkouts can rerun the comparison.
BENCHMARK_BASELINE = Footprint(
    documents=4,
    sections=67,
    characters=84891,
    bytes=84999,
    lines=1366,
)


@dataclass(frozen=True)
class BenchmarkRow:
    change_class: str
    baseline: Footprint
    selected: Footprint
    reduction_percent: float


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


def _level_two_sections(text: str) -> dict[str, str]:
    matches = [
        match for match in HEADING.finditer(text) if len(match.group("marks")) == 2
    ]
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("title")] = text[match.start() : end]
    return sections


def _merge_references(references: list[ContextReference]) -> list[ContextReference]:
    merged: dict[str, ContextReference] = {}
    for reference in references:
        existing = merged.get(reference.path)
        if existing is None:
            merged[reference.path] = reference
            continue
        sections: tuple[str, ...] | None
        if existing.sections is None or reference.sections is None:
            sections = None
        else:
            sections = tuple(sorted(set(existing.sections) | set(reference.sections)))
        merged[reference.path] = ContextReference(
            path=reference.path,
            sections=sections,
            tier=min(existing.tier, reference.tier),
            reason="; ".join(sorted({existing.reason, reference.reason})),
        )
    return [merged[path] for path in sorted(merged)]


def _full_references(change_classes: tuple[str, ...]) -> list[ContextReference]:
    reason = "full diagnostic context"
    if change_classes:
        reason = "expanded context for " + ", ".join(change_classes)
    references = [
        ContextReference(
            path=path,
            sections=None,
            tier=0 if path == "AGENTS.md" else 1,
            reason=reason,
        )
        for path in FULL_CONTEXT_PATHS
    ]
    for change_class in change_classes:
        references.extend(
            ContextReference(
                path=path, sections=None, tier=1, reason=f"{change_class} skill"
            )
            for path in CLASS_SKILLS.get(change_class, ())
        )
    return _merge_references(references)


def select_context(
    root: Path, change_classes: list[str] | tuple[str, ...], *, full: bool = False
) -> list[ContextReference]:
    root = root.resolve()
    stripped = tuple(value.strip() for value in change_classes)
    if any(not value for value in stripped):
        raise ContextSelectionError("empty change class; use --full")
    normalized = tuple(sorted({value.upper() for value in stripped}))
    unknown = sorted(set(normalized) - set(CHANGE_CLASSES))
    if unknown:
        raise ContextSelectionError("unknown change class; use --full")
    if full or any(value not in SELECTIVE_CHANGE_CLASSES for value in normalized):
        references = _full_references(normalized)
    else:
        references = [
            ContextReference(
                path=path,
                sections=sections,
                tier=0 if path == "AGENTS.md" else 1,
                reason="mandatory constitution"
                if path == "AGENTS.md"
                else "current task truth",
            )
            for path, sections in COMMON_SECTION_CONTEXT.items()
        ]
        for change_class in normalized:
            for path, sections in CLASS_SECTION_CONTEXT.get(change_class, {}).items():
                references.append(
                    ContextReference(
                        path=path,
                        sections=sections,
                        tier=1,
                        reason=f"{change_class} current owner",
                    )
                )
            references.extend(
                ContextReference(
                    path=path,
                    sections=None,
                    tier=1,
                    reason=f"{change_class} required skill",
                )
                for path in CLASS_SKILLS.get(change_class, ())
            )
        references = _merge_references(references)
    errors = validate_context_references(root, references)
    if errors:
        raise ContextSelectionError("context manifest is invalid; use --full")
    return references


def validate_context_references(
    root: Path, references: list[ContextReference]
) -> list[str]:
    errors: list[str] = []
    for reference in references:
        path = root / reference.path
        try:
            text = _read_text(path)
        except OSError:
            errors.append(f"missing context path: {reference.path}")
            continue
        if reference.sections is None:
            continue
        available = _level_two_sections(text)
        for section in reference.sections:
            if section not in available:
                errors.append(f"missing section: {reference.path}#{section}")
    return errors


def validate_context_manifest(root: Path) -> list[str]:
    errors: list[str] = []
    for change_class in CHANGE_CLASSES:
        try:
            select_context(root, [change_class])
        except ContextSelectionError as error:
            errors.append(f"{change_class}: {error}")
    return errors


def _selected_text(text: str, sections: tuple[str, ...] | None) -> str:
    if sections is None:
        return text
    available = _level_two_sections(text)
    first_section = min(
        (
            match.start()
            for match in HEADING.finditer(text)
            if len(match.group("marks")) == 2
        ),
        default=len(text),
    )
    return text[:first_section] + "".join(available[section] for section in sections)


def measure_context_footprint(
    root: Path,
    references: list[ContextReference],
    *,
    canonical_only: bool = False,
) -> Footprint:
    selected = [
        reference
        for reference in references
        if not canonical_only or reference.path in CANONICAL_CONTEXT_PATHS
    ]
    characters = 0
    byte_count = 0
    line_count = 0
    section_count = 0
    for reference in selected:
        text = _read_text(root / reference.path)
        chosen = _selected_text(text, reference.sections)
        characters += len(chosen)
        byte_count += len(chosen.encode("utf-8"))
        line_count += len(chosen.splitlines())
        if reference.sections is None:
            section_count += len(HEADING.findall(text))
        else:
            section_count += len(reference.sections) + 1
    return Footprint(
        documents=len(selected),
        sections=section_count,
        characters=characters,
        bytes=byte_count,
        lines=line_count,
    )


def build_context_benchmark(root: Path) -> dict[str, BenchmarkRow]:
    root = _repository_root(root)
    baseline = BENCHMARK_BASELINE
    rows: dict[str, BenchmarkRow] = {}
    scenarios = (*ROUTINE_CHANGE_CLASSES, *HIGH_RISK_CHANGE_CLASSES)
    for change_class in scenarios:
        selected = measure_context_footprint(
            root,
            select_context(root, [change_class]),
            canonical_only=True,
        )
        reduction = 100.0 * (1.0 - selected.bytes / baseline.bytes)
        rows[change_class] = BenchmarkRow(
            change_class=change_class,
            baseline=baseline,
            selected=selected,
            reduction_percent=reduction,
        )
    return rows


def render_benchmark(root: Path) -> str:
    rows = build_context_benchmark(root)
    lines = [
        "CONTEXT FOOTPRINT BENCHMARK",
        f"Baseline: {BENCHMARK_BASE_SHA}",
        "Proxy: LF-normalized UTF-8 bytes/characters/physical lines from the fixed canonical governance set.",
        "Task-variable skills, planner, owning source, and tests are reported separately and excluded.",
        "class | before_bytes | after_bytes | reduction | before_lines | after_lines | after_sections",
    ]
    for change_class in (*ROUTINE_CHANGE_CLASSES, *HIGH_RISK_CHANGE_CLASSES):
        row = rows[change_class]
        lines.append(
            f"{change_class} | {row.baseline.bytes} | {row.selected.bytes} | "
            f"{row.reduction_percent:.1f}% | {row.baseline.lines} | "
            f"{row.selected.lines} | {row.selected.sections}"
        )
    mean = sum(rows[value].reduction_percent for value in ROUTINE_CHANGE_CLASSES) / len(
        ROUTINE_CHANGE_CLASSES
    )
    lines.append(f"Routine mean reduction: {mean:.1f}%")
    lines.append("High-risk controls intentionally retain the full canonical set.")
    return "\n".join(lines)


def render_context(
    root: Path,
    *,
    change_classes: list[str] | tuple[str, ...] = (),
    full: bool = False,
) -> str:
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
    if change_classes or full:
        references = select_context(root, change_classes, full=full)
        normalized = tuple(
            sorted({value.strip().upper() for value in change_classes if value.strip()})
        )
        lines.extend(
            [
                "",
                "CONTEXT SELECTION",
                "Selection mode: full diagnostic"
                if full
                else "Selection mode: task scoped",
                "Change classes: " + (", ".join(normalized) if normalized else "FULL"),
                "Tier 0: read the full constitution and task/Git identity first.",
                "Tier 1: read every selected current section, triggered authority source, skill, owner, and test.",
                "Tier 2: on demand for one named unanswered question; history never overrides current truth.",
            ]
        )
        for reference in references:
            selector = (
                "FULL" if reference.sections is None else " | ".join(reference.sections)
            )
            lines.append(
                f"Reference: {reference.path} # {selector} [Tier {reference.tier}; {reference.reason}]"
            )
        lines.extend(
            [
                "Task additions: active planner, exact owning source/tests, triggered contracts/decisions/questions.",
                "Escalation: use --full whenever classification, authority, or section sufficiency is uncertain.",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--change-class",
        action="append",
        default=[],
        help="select deterministic task context; repeat for multiple classes",
    )
    parser.add_argument(
        "--full", action="store_true", help="emit the safe full diagnostic read-set"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="measure the fixed before/after canonical context proxy",
    )
    args = parser.parse_args(argv)
    try:
        if args.full and args.benchmark:
            raise ContextSelectionError("choose --full or --benchmark")
        if args.benchmark:
            print(render_benchmark(args.root.resolve()))
        else:
            print(
                render_context(
                    args.root.resolve(),
                    change_classes=args.change_class,
                    full=args.full,
                )
            )
    except ContextSelectionError as error:
        print(f"DEVELOPMENT CONTEXT ERROR: {error}")
        return 1
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"DEVELOPMENT CONTEXT ERROR: {type(error).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
