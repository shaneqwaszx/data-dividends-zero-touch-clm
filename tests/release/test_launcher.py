"""The Windows launcher ``tools/release.ps1`` picks the intended Python interpreter.

Regression for D-1: with exactly one candidate, PowerShell unwrapped the filtered list to a
string and ``$candidates[0]`` was its first character ("C"), so the launcher failed.

Each case copies the real launcher into a throwaway Git checkout (paths contain spaces) next
to a stand-in ``tools.release`` package that reports which interpreter ran it. Real virtual
environments are created so the launcher's ``.venv\\Scripts\\python.exe`` paths exist. Nothing
here runs the real toolchain, the host or the registry.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from .fakes import REPO

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows launcher")

SHELLS = [s for s in (shutil.which("pwsh"), shutil.which("powershell")) if s]

STAND_IN = """\
import json
import sys

args = sys.argv[1:]
print(json.dumps({"prefix": sys.prefix, "args": args, "no_bytecode": sys.dont_write_bytecode}))
raise SystemExit(int(args[args.index("--exit") + 1]) if "--exit" in args else 0)
"""


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def make_venv(path: Path) -> Path:
    base = getattr(sys, "_base_executable", sys.executable)
    subprocess.run([base, "-m", "venv", "--without-pip", str(path)], check=True)
    return path


class Layout:
    def __init__(self, base: Path) -> None:
        self.main = base / "main checkout"
        self.worktree = base / "linked worktree"
        self.worktree_own = base / "worktree with venv"
        self.bare = base / "checkout without venv"
        self.override = base / "override env" / "venv dir"


@pytest.fixture(scope="module")
def layout(tmp_path_factory: pytest.TempPathFactory) -> Layout:
    lay = Layout(tmp_path_factory.mktemp("launcher") / "dir with space")
    for checkout in (lay.main, lay.bare):
        (checkout / "tools" / "release").mkdir(parents=True)
        shutil.copyfile(REPO / "tools" / "release.ps1", checkout / "tools" / "release.ps1")
        (checkout / "tools" / "__init__.py").write_text("", encoding="utf-8")
        (checkout / "tools" / "release" / "__init__.py").write_text("", encoding="utf-8")
        (checkout / "tools" / "release" / "__main__.py").write_text(STAND_IN, encoding="utf-8")
        git(checkout, "init", "-q", "-b", "main")
        git(checkout, "add", "tools")
        git(checkout, "commit", "-q", "-m", "launcher")
    git(lay.main, "worktree", "add", "-q", "--detach", str(lay.worktree))
    git(lay.main, "worktree", "add", "-q", "--detach", str(lay.worktree_own))
    # Virtual environments are created after the commit, so no checkout tracks them.
    make_venv(lay.main / ".venv")
    make_venv(lay.worktree_own / ".venv")
    make_venv(lay.override)
    return lay


def launch(
    shell: str, checkout: Path, *args: str, override: Path | str | None = None
) -> tuple[int, dict[str, Any]]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"CLM_RELEASE_PYTHON", "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
    }
    if override is not None:
        env["CLM_RELEASE_PYTHON"] = str(override)
    done = subprocess.run(
        [
            shell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(checkout / "tools" / "release.ps1"),
            *args,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    assert lines, f"launcher produced no report (exit {done.returncode}): {done.stderr}"
    return done.returncode, json.loads(lines[-1])


def ran_in(report: dict[str, Any], venv: Path) -> bool:
    return os.path.normcase(os.path.realpath(report["prefix"])) == os.path.normcase(
        os.path.realpath(venv)
    )


@pytest.fixture(params=SHELLS or [None], ids=lambda s: Path(s).stem if s else "none")
def shell(request: pytest.FixtureRequest) -> str:
    if request.param is None:
        pytest.skip("no PowerShell on this machine")
    return str(request.param)


def test_one_candidate_main_checkout_venv_from_a_linked_worktree(
    shell: str, layout: Layout
) -> None:
    """The D-1 case: the worktree has no .venv, only the main checkout's exists."""
    code, report = launch(shell, layout.worktree, "status")
    assert code == 0
    assert ran_in(report, layout.main / ".venv")


def test_one_candidate_explicit_override_only(shell: str, layout: Layout) -> None:
    code, report = launch(
        shell, layout.bare, "status", override=layout.override / "Scripts" / "python.exe"
    )
    assert code == 0
    assert ran_in(report, layout.override)


def test_multiple_candidates_own_venv_before_main_checkout(shell: str, layout: Layout) -> None:
    code, report = launch(shell, layout.worktree_own, "status")
    assert code == 0
    assert ran_in(report, layout.worktree_own / ".venv")


def test_multiple_candidates_in_the_main_checkout(shell: str, layout: Layout) -> None:
    """Own .venv and main .venv are the same path here: the pre-D-1 working case."""
    code, report = launch(shell, layout.main, "status")
    assert code == 0
    assert ran_in(report, layout.main / ".venv")


def test_explicit_override_wins_over_every_venv(shell: str, layout: Layout) -> None:
    python = layout.override / "Scripts" / "python.exe"
    for checkout in (layout.main, layout.worktree, layout.worktree_own):
        code, report = launch(shell, checkout, "status", override=python)
        assert code == 0
        assert ran_in(report, layout.override)


def test_override_that_does_not_exist_is_skipped(shell: str, layout: Layout) -> None:
    code, report = launch(
        shell, layout.worktree, "status", override=layout.bare / "no such" / "python.exe"
    )
    assert code == 0
    assert ran_in(report, layout.main / ".venv")


def test_arguments_and_exit_code_pass_through_unchanged(shell: str, layout: Layout) -> None:
    code, report = launch(
        shell, layout.worktree, "plan", "--manifest", r"C:\a dir\m.json", "--exit", "7"
    )
    assert code == 7
    assert report["args"] == ["plan", "--manifest", r"C:\a dir\m.json", "--exit", "7"]
    assert report["no_bytecode"] is True
