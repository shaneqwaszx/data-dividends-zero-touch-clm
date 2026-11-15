"""Verify the exact approved source commit, a clean release state, and run the local checks.

The check list mirrors the job list in ``.github/workflows/ci.yml`` so a release never depends
on GitHub-hosted Actions being able to run. A check that was not executed is recorded as
``NOT_RUN`` and is never reported as a pass.
"""

from __future__ import annotations

import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .core import Command, Effect, Gate, ReleaseError, StopCondition, sha256_bytes

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _git(gate: Gate, root: Path, *args: str, purpose: str) -> str:
    result = gate.run(
        Command(("git", *args), Effect.LOCAL_READ, purpose, cwd=str(root), timeout=60, quiet=True)
    )
    if result.returncode != 0:
        raise ReleaseError("GIT_FAILED", f"git {args[0]} failed")
    return result.stdout.strip()


@dataclass(frozen=True)
class SourceState:
    commit: str
    tree: str
    base_ref: str


def verify_source(
    gate: Gate,
    root: Path,
    *,
    commit: str,
    tree: str | None = None,
    base_ref: str = "origin/main",
    allow_untracked: tuple[str, ...] = (),
) -> SourceState:
    """Refuse anything but the exact approved commit in a clean checkout."""

    if not FULL_SHA.match(commit):
        raise StopCondition("COMMIT_NOT_EXACT", "give the full 40-character approved commit")
    head = _git(gate, root, "rev-parse", "HEAD", purpose="read HEAD")
    if head != commit:
        raise StopCondition(
            "WRONG_COMMIT", f"checkout is at {head[:12]}, not the approved {commit[:12]}"
        )
    actual_tree = _git(gate, root, "rev-parse", "HEAD^{tree}", purpose="read tree id")
    if tree is not None and actual_tree != tree:
        raise StopCondition("WRONG_TREE", "the checked-out tree is not the approved tree")
    status = _git(
        gate,
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        purpose="check for uncommitted or untracked files",
    )
    dirty = []
    for line in status.splitlines():
        path = line[3:].strip().strip('"')
        if line.startswith("??") and path.startswith(allow_untracked) and allow_untracked:
            continue
        dirty.append(path)
    if dirty:
        raise StopCondition(
            "SOURCE_NOT_CLEAN", f"{len(dirty)} uncommitted or untracked path(s), first: {dirty[0]}"
        )
    base = _git(gate, root, "rev-parse", "--verify", base_ref, purpose="read base ref")
    merged = gate.run(
        Command(
            ("git", "merge-base", "--is-ancestor", commit, base),
            Effect.LOCAL_READ,
            "confirm the commit is on the integration baseline",
            cwd=str(root),
        )
    )
    if merged.returncode != 0:
        raise StopCondition(
            "COMMIT_NOT_ON_BASE", f"the commit is not contained in {base_ref} as last fetched"
        )
    return SourceState(commit=commit, tree=actual_tree, base_ref=base_ref)


def compose_file_hashes(
    gate: Gate, root: Path, commit: str, files: tuple[str, ...]
) -> list[dict[str, str]]:
    """Hash each Compose file as stored in the commit, so a CRLF checkout cannot change it."""

    hashes = []
    for name in files:
        blob = gate.run(
            Command(
                ("git", "show", f"{commit}:{name}"),
                Effect.LOCAL_READ,
                f"read {name} from the commit",
                cwd=str(root),
                quiet=True,
                binary=True,
            )
        )
        if blob.returncode != 0:
            raise ReleaseError("COMPOSE_FILE_MISSING", f"{name} is not in the commit")
        hashes.append({"path": name, "sha256": sha256_bytes(blob.raw)})
    return hashes


# --------------------------------------------------------------------------------------------
# Local checks
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    name: str
    argv: tuple[str, ...]
    cwd: str = "."
    timeout: float = 900.0
    git_bash: bool = False
    pythonpath_root: bool = False
    ci_job: str = ""


PY = "{python}"
_GOVERNANCE = (
    "check_project_state",
    "check_architecture",
    "check_tooling_config",
    "check_policy_authority",
    "check_external_provider_readiness",
    "check_secrets",
)
CHECKS: dict[str, Check] = {
    "release-ruff": Check(
        "release-ruff",
        (
            PY,
            "-m",
            "ruff",
            "check",
            "--select",
            "E,F,I,UP,B,SIM",
            "--line-length",
            "100",
            "--target-version",
            "py312",
            "tools/release",
            "tests/release",
        ),
    ),  # fmt: skip
    "release-mypy": Check("release-mypy", (PY, "-m", "mypy", "--strict", "-p", "tools.release")),
    "release-pytest": Check(
        "release-pytest", (PY, "-m", "pytest", "tests/release", "-q", "-p", "no:cacheprovider")
    ),
    # tests/deploy must be launched from Git Bash: one test fails when started from PowerShell.
    "deploy-pytest": Check(
        "deploy-pytest",
        (PY, "-m", "pytest", "tests/deploy", "-q", "-p", "no:cacheprovider"),
        git_bash=True,
    ),
    **{name: Check(name, (PY, f"scripts/{name}.py"), ci_job="security") for name in _GOVERNANCE},
    "security-unittests": Check(
        "security-unittests",
        (
            PY,
            "-m",
            "unittest",
            "tests.test_check_secrets",
            "tests.test_pre_pr_check",
            "tests.test_dev_context",
            "tests.test_check_project_state",
            "tests.test_check_architecture",
            "tests.test_check_policy_authority",
            "tests.test_check_external_provider_readiness",
        ),
        ci_job="security",
    ),
    "backend-ruff": Check(
        "backend-ruff", (PY, "-m", "ruff", "check", "."), cwd="apps/backend", ci_job="backend"
    ),
    "backend-mypy": Check(
        "backend-mypy", (PY, "-m", "mypy", "app"), cwd="apps/backend", ci_job="backend"
    ),
    "backend-pytest": Check(
        "backend-pytest",
        (PY, "-m", "pytest", "-o", "faulthandler_timeout=600"),
        cwd="apps/backend",
        timeout=3600,
        pythonpath_root=True,
        ci_job="backend",
    ),
    "contract-tests": Check(
        "contract-tests",
        (PY, "-m", "unittest", "discover", "-s", "../../tests/contract", "-p", "test_*.py"),
        cwd="apps/backend",
        pythonpath_root=True,
        ci_job="backend",
    ),
    "assistant-ruff": Check(
        "assistant-ruff",
        (
            PY,
            "-m",
            "ruff",
            "check",
            "ai_assistant",
            "assistant_eval",
            "assistant_hosting",
            "tests",
            "scripts",
        ),
        cwd="apps/assistant",
        ci_job="assistant",
    ),
    "assistant-mypy": Check(
        "assistant-mypy",
        (PY, "-m", "mypy", "ai_assistant", "assistant_eval", "assistant_hosting"),
        cwd="apps/assistant",
        ci_job="assistant",
    ),
    "assistant-pytest": Check(
        "assistant-pytest",
        (PY, "-m", "pytest"),
        cwd="apps/assistant",
        timeout=3600,
        ci_job="assistant",
    ),
    "frontend-typecheck": Check(
        "frontend-typecheck", ("npm", "run", "typecheck"), cwd="apps/frontend", ci_job="frontend"
    ),
    "frontend-test": Check(
        "frontend-test", ("npm", "test"), cwd="apps/frontend", timeout=1800, ci_job="frontend"
    ),
    "frontend-build": Check(
        "frontend-build", ("npm", "run", "build"), cwd="apps/frontend", ci_job="frontend"
    ),
    "pre-pr-check": Check("pre-pr-check", (PY, "scripts/pre_pr_check.py")),
}
# CI jobs with no automatic local mirror. They are always listed, as NOT_RUN, so a release
# record can never imply they passed. Run them by hand when the change class needs them.
MANUAL_CI_JOBS = {
    "local-ocr": "docker build -f scripts/ocr_validation.Dockerfile, then the offline OCR test",
    "phase12-mongo": "python scripts/run_physical_mongo_tests.py against a disposable mongo:7",
    "e2e": "python scripts/run_e2e.py --timeout-seconds 180 (disposable mongo:7 and Tesseract)",
    "demo-lifecycle-windows": (
        "python -m unittest discover -s tests -p test_demo_lifecycle_windows.py"
    ),
}

_ALWAYS = (*_GOVERNANCE, "deploy-pytest", "pre-pr-check")
_BACKEND = ("backend-ruff", "backend-mypy", "backend-pytest", "contract-tests")
_ASSISTANT = ("assistant-ruff", "assistant-mypy", "assistant-pytest")
_FRONTEND = ("frontend-typecheck", "frontend-test", "frontend-build")
_RELEASE = ("release-ruff", "release-mypy", "release-pytest")
SELECTION: dict[str, tuple[str, ...]] = {
    "DOCS_ONLY": _ALWAYS,
    "FRONTEND_UI": (*_ALWAYS, *_FRONTEND),
    "FRONTEND_STATE_CACHE": (*_ALWAYS, *_FRONTEND),
    "BACKEND_DOMAIN": (*_ALWAYS, *_BACKEND),
    "BACKEND_API": (*_ALWAYS, *_BACKEND, *_FRONTEND),
    "AUTH_RBAC_SECURITY": (*_ALWAYS, *_BACKEND, *_FRONTEND, "security-unittests"),
    "PERSISTENCE": (*_ALWAYS, *_BACKEND, "security-unittests"),
    "EXTERNAL_PROVIDER": (*_ALWAYS, *_BACKEND, "security-unittests"),
    "ARCHITECTURE_REFACTOR": (*_ALWAYS, *_BACKEND, *_FRONTEND, "security-unittests"),
    "CI_TOOLING": (*_ALWAYS, *_RELEASE, "security-unittests"),
    # Not a workflow change class: selects the assistant job for an assistant-only release.
    "ASSISTANT": (*_ALWAYS, *_ASSISTANT),
}


def select_checks(change_classes: list[str], extra: tuple[str, ...] = ()) -> list[str]:
    if not change_classes:
        raise ReleaseError("CHANGE_CLASS_REQUIRED", "name at least one change class")
    chosen: list[str] = []
    for change_class in change_classes:
        if change_class not in SELECTION:
            raise ReleaseError("CHANGE_CLASS_UNKNOWN", f"unknown change class {change_class!r}")
        chosen += SELECTION[change_class]
    for name in extra:
        if name not in CHECKS:
            raise ReleaseError("CHECK_UNKNOWN", f"unknown check {name!r}")
        chosen.append(name)
    return list(dict.fromkeys(chosen))


def git_bash() -> str | None:
    """Git for Windows' bash, never WSL's ``bash.exe`` from System32."""

    git = shutil.which("git")
    if git is None:
        return None
    for parent in Path(git).resolve().parents:
        candidate = parent / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)
    return shutil.which("bash") if sys.platform != "win32" else None


def run_checks(gate: Gate, root: Path, names: list[str]) -> list[dict[str, str]]:
    """Run each selected check once. Returns manifest ``checks`` entries."""

    records: list[dict[str, str]] = []
    for name in names:
        check = CHECKS[name]
        argv = tuple(sys.executable if part == PY else part for part in check.argv)
        if argv[0] == "npm":
            npm = shutil.which("npm")
            if npm is None:
                records.append({"name": name, "status": "NOT_RUN", "detail": "npm not found"})
                continue
            argv = (npm, *argv[1:])
        if check.git_bash and sys.platform == "win32":
            bash = git_bash()
            if bash is None:
                records.append({"name": name, "status": "NOT_RUN", "detail": "Git Bash not found"})
                continue
            quoted = " ".join(f"'{part.replace(chr(92), '/')}'" for part in argv)
            argv = (bash, "-lc", quoted)
        env = {"PYTHONPATH": str(root)} if check.pythonpath_root else None
        started = time.monotonic()
        result = gate.run(
            Command(
                argv,
                Effect.LOCAL_WRITE,  # checks write caches and build output on this machine
                f"check {name}",
                cwd=str(root / check.cwd),
                env=env,
                timeout=check.timeout,
            )
        )
        seconds = int(time.monotonic() - started)
        if result.skipped:
            records.append({"name": name, "status": "NOT_RUN", "detail": "skipped in this mode"})
        elif result.returncode == 0:
            records.append({"name": name, "status": "PASS", "detail": f"{seconds}s"})
        else:
            tail = (
                result.stdout.strip().splitlines() or result.stderr.strip().splitlines() or [""]
            )[-1]
            records.append(
                {
                    "name": name,
                    "status": "FAIL",
                    "detail": f"exit {result.returncode}: {tail[:200]}",
                }
            )
    for job, how in MANUAL_CI_JOBS.items():
        records.append({"name": f"ci-job:{job}", "status": "NOT_RUN", "detail": f"manual: {how}"})
    return records
