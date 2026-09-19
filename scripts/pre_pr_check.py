"""Read-only, fail-closed checks for local pull-request readiness.

This checker inspects Git and source files but never changes the worktree or history.
A PASS is evidence for deterministic hazards only, not semantic merge safety.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_SCAN_BYTES = 2 * 1024 * 1024
MIN_PARTIAL_MARKER_WIDTH = 7
START_CONFLICT_MARKER = re.compile(r"^(?P<marker><+)(?: .*)?$")
MIDDLE_CONFLICT_MARKER = re.compile(r"^(?P<marker>=+)$")
END_CONFLICT_MARKER = re.compile(r"^(?P<marker>>+)(?: .*)?$")
DIFF_CHECK_MARKER = re.compile(
    r"^(?P<path>.+):(?P<line>[1-9][0-9]*): leftover conflict marker$"
)
CHANGE_FILTER = "ACMRDT"

HOTSPOTS = {
    ".github/workflows/ci.yml",
    "README.md",
    "apps/backend/app/composition.py",
    "apps/backend/app/main.py",
    "apps/frontend/src/App.tsx",
    "apps/frontend/src/api.ts",
    "apps/frontend/src/types.ts",
}
LOCKFILE_NAMES = {
    "bun.lock",
    "bun.lockb",
    "composer.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}
MANIFEST_NAMES = {
    "Cargo.toml",
    "Pipfile",
    "composer.json",
    "package.json",
    "pyproject.toml",
}
SENSITIVE_SUFFIXES = {
    ".cer",
    ".crt",
    ".der",
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
}
SENSITIVE_STRUCTURED_STEMS = {
    "credential",
    "credentials",
    "secret",
    "secrets",
    "service-account",
    "service-account-key",
    "service_account",
    "service_account_key",
}
SENSITIVE_STRUCTURED_SUFFIXES = {".json", ".yaml", ".yml"}


@dataclass(frozen=True)
class Change:
    status: str
    path: str
    previous_path: str | None = None

    @property
    def kind(self) -> str:
        return self.status[0]

    @property
    def classification_paths(self) -> tuple[str, ...]:
        if self.previous_path is None:
            return (self.path,)
        return (self.previous_path, self.path)

    @property
    def has_current_content(self) -> bool:
        return self.kind != "D"

    def render(self) -> str:
        if self.previous_path is None:
            return f"{self.status}\t{self.path}"
        return f"{self.status}\t{self.previous_path} -> {self.path}"


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def detail(self, message: str) -> None:
        self.details.append(message)


def _git(root: Path, *args: str, binary: bool = False) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
        env=environment,
    )


def _paths_from_nul(result: subprocess.CompletedProcess) -> set[str]:
    return {os.fsdecode(value) for value in result.stdout.split(b"\0") if value}


def _required_paths(
    report: Report, result: subprocess.CompletedProcess, operation: str
) -> set[str]:
    if result.returncode != 0:
        report.fail(f"Unable to inspect {operation}.")
        return set()
    return _paths_from_nul(result)


def _changes_from_name_status(result: subprocess.CompletedProcess) -> list[Change]:
    fields = [value for value in result.stdout.split(b"\0") if value]
    changes: list[Change] = []
    index = 0
    while index < len(fields):
        status = os.fsdecode(fields[index])
        index += 1
        if not status or status[0] not in CHANGE_FILTER:
            raise ValueError("invalid change status")
        if status[0] in {"C", "R"}:
            if index + 1 >= len(fields):
                raise ValueError("incomplete rename/copy record")
            previous_path = os.fsdecode(fields[index])
            path = os.fsdecode(fields[index + 1])
            index += 2
            changes.append(
                Change(status=status, path=path, previous_path=previous_path)
            )
        else:
            if index >= len(fields):
                raise ValueError("incomplete change record")
            changes.append(Change(status=status, path=os.fsdecode(fields[index])))
            index += 1
    return changes


def _required_changes(
    report: Report, result: subprocess.CompletedProcess, operation: str
) -> list[Change]:
    if result.returncode != 0:
        report.fail(f"Unable to inspect {operation}.")
        return []
    try:
        return _changes_from_name_status(result)
    except ValueError:
        report.fail(f"Git returned an invalid change inventory for {operation}.")
        return []


def _paths_from_numstat(result: subprocess.CompletedProcess) -> set[str]:
    paths: set[str] = set()
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        fields = record.split(b"\t", 2)
        if len(fields) != 3:
            raise ValueError("invalid numstat record")
        paths.add(os.fsdecode(fields[2]))
    return paths


def _unstaged_changes(root: Path, report: Report) -> list[Change]:
    candidates = _required_changes(
        report,
        _git(
            root,
            "diff-files",
            "--name-status",
            "--no-renames",
            "-z",
            f"--diff-filter={CHANGE_FILTER}",
            binary=True,
        ),
        "unstaged tracked files",
    )
    content_result = _git(
        root,
        "diff-files",
        "--numstat",
        "--no-renames",
        "-z",
        f"--diff-filter={CHANGE_FILTER}",
        binary=True,
    )
    if content_result.returncode != 0:
        report.fail("Unable to inspect unstaged tracked file content changes.")
        return []
    try:
        content_paths = _paths_from_numstat(content_result)
    except ValueError:
        report.fail("Git returned an invalid unstaged content inventory.")
        return []
    return [change for change in candidates if change.path in content_paths]


def _changed_files(
    root: Path, report: Report
) -> tuple[list[Change], list[Change], list[Change], list[Change]]:
    branch = _required_changes(
        report,
        _git(
            root,
            "diff",
            "--name-status",
            "-z",
            f"--diff-filter={CHANGE_FILTER}",
            "origin/main...HEAD",
            binary=True,
        ),
        "the committed branch delta",
    )
    unstaged = _unstaged_changes(root, report)
    staged = _required_changes(
        report,
        _git(
            root,
            "diff",
            "--cached",
            "--name-status",
            "-z",
            f"--diff-filter={CHANGE_FILTER}",
            binary=True,
        ),
        "staged files",
    )
    untracked_paths = _required_paths(
        report,
        _git(root, "ls-files", "--others", "--exclude-standard", "-z", binary=True),
        "untracked files",
    )
    untracked = [Change(status="??", path=path) for path in sorted(untracked_paths)]
    return branch, unstaged, staged, untracked


def _read_text(path: Path) -> str | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_SCAN_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _marker_lines(text: str) -> list[int]:
    lines = text.splitlines()

    def matches_by_width(pattern: re.Pattern[str]) -> dict[int, set[int]]:
        matches: dict[int, set[int]] = {}
        for line_number, line in enumerate(lines, start=1):
            match = pattern.fullmatch(line)
            if match is not None:
                matches.setdefault(len(match.group("marker")), set()).add(line_number)
        return matches

    starts = matches_by_width(START_CONFLICT_MARKER)
    middles = matches_by_width(MIDDLE_CONFLICT_MARKER)
    ends = matches_by_width(END_CONFLICT_MARKER)
    suspicious = {
        line_number
        for marker_family in (starts, ends)
        for marker_width, marker_lines in marker_family.items()
        if marker_width >= MIN_PARTIAL_MARKER_WIDTH
        for line_number in marker_lines
    }
    for marker_width in starts.keys() & middles.keys() & ends.keys():
        for middle in middles[marker_width]:
            preceding_starts = {line for line in starts[marker_width] if line < middle}
            following_ends = {line for line in ends[marker_width] if middle < line}
            if preceding_starts and following_ends:
                suspicious.update(preceding_starts)
                suspicious.add(middle)
                suspicious.update(following_ends)
    return sorted(suspicious)


def _git_object_text(root: Path, object_name: str) -> tuple[bool, str | None]:
    result = _git(root, "show", object_name, binary=True)
    if result.returncode != 0:
        return False, None
    if b"\0" in result.stdout or len(result.stdout) > MAX_SCAN_BYTES:
        return True, None
    try:
        return True, result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return True, None


def _non_marker_diff_check_output(
    output: str, source_texts: dict[str, str | None]
) -> str:
    retained: list[str] = []
    marker_lines = {
        path: set(_marker_lines(text))
        for path, text in source_texts.items()
        if text is not None
    }
    for line in output.splitlines():
        diagnostic = DIFF_CHECK_MARKER.fullmatch(line)
        if diagnostic is not None:
            path = diagnostic.group("path")
            line_number = int(diagnostic.group("line"))
            text = source_texts.get(path)
            source_lines = text.splitlines() if text is not None else []
            if (
                line_number <= len(source_lines)
                and MIDDLE_CONFLICT_MARKER.fullmatch(source_lines[line_number - 1])
                and line_number not in marker_lines.get(path, set())
            ):
                continue
        retained.append(line)
    return "\n".join(retained).rstrip()


def _check_diff_whitespace(
    report: Report,
    result: subprocess.CompletedProcess,
    label: str,
    source_texts: dict[str, str | None],
) -> None:
    if result.returncode == 0:
        return
    relevant_output = _non_marker_diff_check_output(result.stdout, source_texts)
    if relevant_output:
        report.fail(f"git diff --check failed for {label}:\n{relevant_output}")
    elif not result.stdout.rstrip():
        report.fail(f"Unable to run git diff --check for {label}.")


def _is_dependency_file(path: str) -> bool:
    name = Path(path).name
    return (
        name in LOCKFILE_NAMES
        or name in MANIFEST_NAMES
        or name.startswith("requirements")
        and name.endswith(".txt")
    )


def _is_api_config_or_shared_type(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    name = Path(normalized).name.lower()
    if normalized in {
        "apps/backend/app/api_models.py",
        "apps/backend/app/config.py",
        "apps/backend/app/main.py",
        "apps/frontend/src/api.ts",
        "apps/frontend/src/shared.ts",
        "apps/frontend/src/types.ts",
    }:
        return True
    return normalized.startswith("apps/") and (
        name.startswith(("api.", "config.", "settings."))
        or name in {"types.py", "types.ts", "types.tsx"}
        or "/api/" in normalized.lower()
    )


def _is_obvious_sensitive_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    name = Path(normalized).name.lower()
    allowed_environment_examples = {".env.example", ".env.sample", ".env.template"}
    if name in allowed_environment_examples:
        return False
    return (
        name == ".env"
        or name.startswith(".env.")
        or Path(name).suffix in SENSITIVE_SUFFIXES
        or (
            Path(name).stem in SENSITIVE_STRUCTURED_STEMS
            and Path(name).suffix in SENSITIVE_STRUCTURED_SUFFIXES
        )
    )


def _classification_paths(changes: list[Change]) -> set[str]:
    return {path for change in changes for path in change.classification_paths}


def _scan_git_changes(
    root: Path, report: Report, changes: list[Change], object_prefix: str, label: str
) -> dict[str, str | None]:
    source_texts: dict[str, str | None] = {}
    for change in changes:
        if not change.has_current_content:
            continue
        inspected, text = _git_object_text(root, f"{object_prefix}{change.path}")
        source_texts[change.path] = text
        if not inspected:
            report.fail(f"Unable to inspect {label} text content for {change.path}.")
        elif text is not None and (lines := _marker_lines(text)):
            report.fail(
                f"Conflict marker structure in {label} {change.path} "
                f"at line(s) {', '.join(map(str, lines))}."
            )
    return source_texts


def _scan_worktree_changes(
    root: Path, report: Report, changes: list[Change]
) -> dict[str, str | None]:
    source_texts: dict[str, str | None] = {}
    for change in changes:
        if not change.has_current_content:
            continue
        text = _read_text(root / change.path)
        source_texts[change.path] = text
        if text is not None and (lines := _marker_lines(text)):
            report.fail(
                f"Conflict marker structure in unstaged file {change.path} "
                f"at line(s) {', '.join(map(str, lines))}."
            )
    return source_texts


def _run_governance_check(root: Path, report: Report, script_name: str) -> None:
    script = root / "scripts" / script_name
    if not script.is_file():
        return
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        shell=False,
    )
    if result.returncode == 0:
        report.detail(f"{script_name}: PASS")
    else:
        diagnostics: list[str] = []
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            diagnostics.append(f"stdout:\n{stdout[:2000]}")
        if stderr:
            diagnostics.append(f"stderr:\n{stderr[:2000]}")
        if not diagnostics:
            diagnostics.append("no checker diagnostics")
        report.fail(
            f"{script_name}: FAIL (exit {result.returncode})\n" + "\n".join(diagnostics)
        )


def audit_repository(root: Path) -> Report:
    report = Report()

    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        report.fail("Current directory is not a Git worktree.")
        return report

    branch_result = _git(root, "branch", "--show-current")
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    if not branch:
        report.fail("HEAD is detached; a named feature branch is required.")
    elif branch == "main":
        report.fail("Current branch is main; feature work must use a separate branch.")
    else:
        report.detail(f"Feature branch: {branch}")

    origin_main = _git(root, "rev-parse", "--verify", "origin/main^{commit}")
    if origin_main.returncode != 0:
        report.fail("origin/main does not exist or is not a commit.")
        return report
    origin_sha = origin_main.stdout.strip()
    report.detail(f"origin/main SHA: {origin_sha}")

    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        report.fail("HEAD does not resolve to a commit.")
        return report
    report.detail(f"HEAD SHA: {head.stdout.strip()}")

    ancestry = _git(root, "merge-base", "--is-ancestor", "origin/main", "HEAD")
    if ancestry.returncode != 0:
        report.fail("Current branch does not contain the latest origin/main commit.")

    relationship = _git(
        root, "rev-list", "--left-right", "--count", "origin/main...HEAD"
    )
    if relationship.returncode == 0:
        values = relationship.stdout.split()
        if len(values) == 2:
            report.detail(f"Branch relationship: ahead {values[1]}, behind {values[0]}")
        else:
            report.fail("Git returned an invalid branch ahead/behind relationship.")
    else:
        report.fail("Unable to determine branch ahead/behind relationship.")

    unresolved = _required_paths(
        report,
        _git(
            root,
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=U",
            "-z",
            binary=True,
        ),
        "unresolved Git conflicts",
    )
    if unresolved:
        report.fail("Unresolved Git conflicts: " + ", ".join(sorted(unresolved)))

    branch_changes, unstaged_changes, staged_changes, untracked_changes = (
        _changed_files(root, report)
    )
    all_changes = branch_changes + unstaged_changes + staged_changes + untracked_changes
    changed_paths = _classification_paths(all_changes)

    if unstaged_changes:
        report.fail(
            "Unstaged tracked changes must be committed before the pre-PR check."
        )
    if staged_changes:
        report.fail("Staged changes must be committed before the pre-PR check.")
    if untracked_changes:
        report.fail(
            "Untracked files must be committed, ignored, or removed before the pre-PR check."
        )

    branch_texts = _scan_git_changes(
        root, report, branch_changes, "HEAD:", "changed file"
    )
    staged_texts = _scan_git_changes(root, report, staged_changes, ":", "staged file")
    unstaged_texts = _scan_worktree_changes(root, report, unstaged_changes)

    _check_diff_whitespace(
        report,
        _git(root, "diff", "--check", "origin/main...HEAD"),
        "the branch delta",
        branch_texts,
    )
    _check_diff_whitespace(
        report,
        _git(root, "diff", "--cached", "--check", "HEAD"),
        "staged changes",
        staged_texts,
    )
    _check_diff_whitespace(
        report,
        _git(root, "diff-files", "--check"),
        "unstaged tracked changes",
        unstaged_texts,
    )

    tracked = _required_paths(
        report, _git(root, "ls-files", "-z", binary=True), "tracked files"
    )
    sensitive = sorted(path for path in tracked if _is_obvious_sensitive_file(path))
    if sensitive:
        report.fail("Tracked obvious secret/environment files: " + ", ".join(sensitive))

    if branch_changes:
        report.detail("Committed branch delta:")
        report.details.extend(
            f"  {change.render()}"
            for change in sorted(
                branch_changes, key=lambda item: (item.path, item.status)
            )
        )
    else:
        report.detail("Committed branch delta: none")

    status = _git(root, "status", "--short")
    if status.returncode != 0:
        report.fail("Unable to inspect working-tree status.")
    elif status.stdout.rstrip():
        report.detail("Working-tree inventory:")
        report.details.extend(
            f"  {line}" for line in status.stdout.rstrip().splitlines()
        )
    else:
        report.detail("Working-tree inventory: clean")

    hotspots = sorted(changed_paths & HOTSPOTS)
    if hotspots:
        report.warn("Integration hotspot files changed: " + ", ".join(hotspots))
    dependencies = sorted(path for path in changed_paths if _is_dependency_file(path))
    if dependencies:
        report.warn(
            "Dependency manifests/lockfiles changed: " + ", ".join(dependencies)
        )
    ci_files = sorted(
        path
        for path in changed_paths
        if path.replace("\\", "/").startswith(".github/workflows/")
    )
    if ci_files:
        report.warn("CI workflow changed: " + ", ".join(ci_files))
    shared_contracts = sorted(
        path for path in changed_paths if _is_api_config_or_shared_type(path)
    )
    if shared_contracts:
        report.warn(
            "API/config/shared type files changed: " + ", ".join(shared_contracts)
        )
    _run_governance_check(root, report, "check_project_state.py")
    _run_governance_check(root, report, "check_architecture.py")
    _run_governance_check(root, report, "check_tooling_config.py")
    return report


def _render(report: Report) -> None:
    print("Pre-PR merge-safety audit")
    for message in report.details:
        print(f"INFO: {message}")
    for message in report.warnings:
        print(f"WARN: {message}")
    for message in report.failures:
        print(f"FAIL: {message}")
    if report.failures:
        print(
            f"SUMMARY: FAIL ({len(report.failures)} unsafe condition(s), {len(report.warnings)} warning(s))"
        )
    else:
        print(f"SUMMARY: PASS (0 unsafe conditions, {len(report.warnings)} warning(s))")
    print("NOTE: PASS does not prove semantic merge safety.")


def main(argv: Sequence[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    report = audit_repository(root)
    _render(report)
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
