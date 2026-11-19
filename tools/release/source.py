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


INTEGRATION_BASE = "origin/main"
# T-1 (owner-approved 2026-11-17, N7-A finding P2 N-1): the only bases other than the
# integration baseline, each an exact remote-tracking release branch with a stated reason. A
# release from one of them is the branch tip exactly, with a mandatory approved tree, and its
# parent must already be on the integration baseline, so only the reviewed delta is outside it.
RELEASE_BASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^origin/release/n7a-reader-[0-9]{8}$"), "N7A_READER_LINEAGE"),
    # F-2 (owner-approved 2026-11-19): the frontend-only AI Insights + compact external-AI notice release on the deployed
    # C10 + OPQ release c5a1c7f4. One exact branch, pinned to the one qualified commit and tree
    # below, and frontend only (manifest rule). GitHub's main ruleset squash-merges, so the
    # qualified commit cannot become an ancestor of main.
    (re.compile(r"^origin/release/f2-ai-insights-notice-c5a1c7f4$"), "F2_FRONTEND_LINEAGE"),
    # Combined assistant + backend release on c5a1c7f4 (owner-directed 2026-11-19): UBO_CALCULATION
    # (U-1..U-5), G-6 R0/R1, the D-144 ownership wording fix and inert C11 hooks (A), or A plus
    # the C11 enabling values (B, owner approval pending). Each branch pinned to one commit and tree,
    # assistant and backend only.
    (
        re.compile(r"^origin/release/c10-opq-assistant-backend-insights-c5a1c7f4$"),
        "C10_OPQ_ASSISTANT_BACKEND_INSIGHTS_LINEAGE",
    ),
    # The frontend for B2: the deployed F-2 + notice frontend plus the reviewed C11 fallback (P-C).
    (re.compile(r"^origin/release/f2-c11-fallback-c5a1c7f4$"), "F2_C11_FALLBACK_FRONTEND_LINEAGE"),
    # Combined B3 follow-up (owner-directed 2026-11-19): D-147 standing GoldTier Sandbox writes
    # on B3 (QG PASS e4cf2c6f; tree = B3 + D-147, committed on c5a1c7f4), backend only.
    (re.compile(r"^origin/release/b3-d147-c5a1c7f4$"), "B3_D147_BACKEND_LINEAGE"),
    # Synthetic case reasoning on origin/main b409077a (QG PASS, reviewed identity 2703e572),
    # assistant only. One commit whose parent is on main.
    (
        re.compile(r"^origin/release/nl-synthetic-reasoning-b409077a$"),
        "NL_SYNTHETIC_REASONING_ASSISTANT_LINEAGE",
    ),
    # C4 closeout (owner-approved 2026-11-19): NL plus OPQ PTE. LTD. registered as an approved
    # synthetic company (independent delta review PASS WITH NOTES, candidate f6e59a4a),
    # assistant only. One commit on b409077a.
    (re.compile(r"^origin/release/nl-opq-b409077a$"), "NL_OPQ_ASSISTANT_LINEAGE"),
)
# A lineage listed here accepts only this exact (commit, tree): never a later commit on the branch.
PINNED_RELEASE_IDENTITIES: dict[str, tuple[str, str]] = {
    "F2_FRONTEND_LINEAGE": (
        "8454370251e010d4dc93331263a61d3f57b1f1e0",
        "b2121b9976358ed7f43a54e87518982bb0dcdf0f",
    ),
    "C10_OPQ_ASSISTANT_BACKEND_INSIGHTS_LINEAGE": (
        "5ad86fb527f82c8c430af19ea2e2b1213d1b7407",
        "9be9b86015d503bab37ab5dee7d0c68596c1f573",
    ),
    "F2_C11_FALLBACK_FRONTEND_LINEAGE": (
        "5dd4d3cf6026541c9f7e9221a23fc4ba8f1437be",
        "7efa88622ef1bddb1a710feb97b25474321c06c2",
    ),
    "B3_D147_BACKEND_LINEAGE": (
        "320fe7efc53a1f99e5d207107b9e39072f4bb0c4",
        "88b14d5dfa6331fd1e696587b07d78c83edf0f71",
    ),
    "NL_SYNTHETIC_REASONING_ASSISTANT_LINEAGE": (
        "bb7820614d4e1711fb5d25840214989e2d50d103",
        "aeeb96ad78c12652cec8303193c6cee00af544ec",
    ),
    "NL_OPQ_ASSISTANT_LINEAGE": (
        "1db9106fce7fee01b5f8ffe888c5f8da838fbea5",
        "884028dd10c273965fe11044b0bec9379a8a2cf9",
    ),
}
# A lineage listed here may change only these services.
RELEASE_SERVICES: dict[str, frozenset[str]] = {
    "F2_FRONTEND_LINEAGE": frozenset({"frontend"}),
    "C10_OPQ_ASSISTANT_BACKEND_INSIGHTS_LINEAGE": frozenset({"assistant", "backend"}),
    "F2_C11_FALLBACK_FRONTEND_LINEAGE": frozenset({"frontend"}),
    "B3_D147_BACKEND_LINEAGE": frozenset({"backend"}),
    "NL_SYNTHETIC_REASONING_ASSISTANT_LINEAGE": frozenset({"assistant"}),
    "NL_OPQ_ASSISTANT_LINEAGE": frozenset({"assistant"}),
}
INTEGRATION_REASON = "INTEGRATION_BASELINE"


def check_pinned_identity(reason: str, commit: str, tree: str | None) -> None:
    """Refuse a pinned lineage unless the commit and tree are exactly the qualified ones."""

    pinned = PINNED_RELEASE_IDENTITIES.get(reason)
    if pinned is not None and (commit, tree) != pinned:
        raise StopCondition(
            "RELEASE_IDENTITY_NOT_PINNED",
            f"{reason} accepts only commit {pinned[0][:12]} with tree {pinned[1][:12]}",
        )


@dataclass(frozen=True)
class SourceState:
    commit: str
    tree: str
    base_ref: str
    base_reason: str = INTEGRATION_REASON


def release_base_reason(base_ref: str) -> str:
    """The recorded reason for an allowed base, or refuse any other base."""

    if base_ref == INTEGRATION_BASE:
        return INTEGRATION_REASON
    for pattern, reason in RELEASE_BASES:
        if pattern.fullmatch(base_ref):
            return reason
    raise StopCondition("BASE_REF_NOT_ALLOWED", "only origin/main or an allow-listed release branch")


def remote_tracking_commit(gate: Gate, root: Path, base_ref: str, *, purpose: str) -> str:
    """Read a direct commit ref from the exact remote-tracking name."""

    refname = f"refs/remotes/{base_ref}"
    fields = _git(
        gate,
        root,
        "for-each-ref",
        "--format=%(refname) %(objectname) %(objecttype) %(symref)",
        "--",
        refname,
        purpose=purpose,
    ).split(maxsplit=3)
    # Git's pattern can also match descendants, so check the returned name.
    if len(fields) < 3 or fields[0] != refname:
        raise ReleaseError("GIT_FAILED", "the exact remote-tracking ref is missing")
    if len(fields) == 4:
        raise ReleaseError("GIT_FAILED", "the remote-tracking ref is symbolic")
    _, commit, object_type = fields
    if object_type != "commit":
        raise ReleaseError("GIT_FAILED", "the remote-tracking ref does not point to a commit")
    return commit


def verify_source(
    gate: Gate,
    root: Path,
    *,
    commit: str,
    tree: str | None = None,
    base_ref: str = INTEGRATION_BASE,
    allow_untracked: tuple[str, ...] = (),
) -> SourceState:
    """Refuse anything but the exact approved commit in a clean checkout, on origin/main or,
    for an allow-listed release branch, as that branch's exact tip with the approved tree and a
    parent already on origin/main."""

    reason = release_base_reason(base_ref)
    release_branch = reason != INTEGRATION_REASON
    if release_branch and tree is None:
        raise StopCondition("TREE_REQUIRED", "a release-branch base needs the approved --tree")
    check_pinned_identity(reason, commit, tree)
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
    if release_branch:
        # Only the remote-tracking ref counts (a local branch of the same name is ignored), and
        # the approved commit must be its tip: the shared, pushed history, nothing later.
        tip = remote_tracking_commit(gate, root, base_ref, purpose="read the release branch tip")
        if tip != commit:
            raise StopCondition(
                "COMMIT_NOT_BRANCH_TIP", f"the commit is not the tip of {base_ref} as last fetched"
            )
        parents = _git(gate, root, "rev-list", "--parents", "-n", "1", commit, purpose="read parents")
        parent_ids = parents.split()[1:]
        if len(parent_ids) != 1:
            raise StopCondition("RELEASE_COMMIT_SHAPE", "a release-branch commit has one parent")
        integration = remote_tracking_commit(gate, root, INTEGRATION_BASE, purpose="read base ref")
        on_main = gate.run(
            Command(
                ("git", "merge-base", "--is-ancestor", parent_ids[0], integration),
                Effect.LOCAL_READ,
                "confirm the release commit's parent is on the integration baseline",
                cwd=str(root),
            )
        )
        if on_main.returncode != 0:
            raise StopCondition(
                "PARENT_NOT_ON_BASE", "the release commit's parent is not in origin/main"
            )
        return SourceState(
            commit=commit, tree=actual_tree, base_ref=base_ref, base_reason=reason
        )
    base = remote_tracking_commit(gate, root, base_ref, purpose="read base ref")
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
