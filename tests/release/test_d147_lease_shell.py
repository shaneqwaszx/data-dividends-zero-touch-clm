"""D-147 R2: the lease and settings checks, run as real shell commands (not mocked replies).

Each remote command the Host builds is executed by a local POSIX shell with a stand-in
``sudo`` on PATH that can allow, deny (permission) or fail (command failure). Reproduces the
R1 finding: the old lease command reported "closed" when sudo was refused.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.release import catalog
from tools.release.core import AuditLog, Command, Gate, Mode, Result
from tools.release.host import Host, SshTarget

SHELL = shutil.which("sh") or shutil.which("bash")
pytestmark = pytest.mark.skipif(SHELL is None, reason="needs a POSIX shell")

SUDO = """#!/bin/sh
mode=$(cat "$(dirname "$0")/mode")
case "$mode" in
  allow) [ "$1" = "-n" ] && shift; exec "$@" ;;
  deny) echo "sudo: a password is required" >&2; exit 1 ;;
  *) exit 127 ;;
esac
"""
OLD_R1_LEASE_COMMAND = "sudo -n test -e {path} && echo lease-open || echo lease-closed"


class LocalShell:
    """Runs the remote part of an ssh Command in a local shell."""

    def __init__(self, env: dict[str, str]) -> None:
        self.env = env

    def run(self, command: Command) -> Result:
        assert command.argv[0] == "ssh"
        done = subprocess.run(
            [str(SHELL), "-c", command.argv[-1]],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=30,
            check=False,
        )
        return Result(done.returncode, done.stdout, done.stderr)


@pytest.fixture()
def shim(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sudo = bin_dir / "sudo"
    sudo.write_text(SUDO, encoding="ascii", newline="\n")
    sudo.chmod(0o755)
    (bin_dir / "mode").write_text("allow", encoding="ascii")
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir.as_posix()}{os.pathsep}{env.get('PATH', '')}"
    return bin_dir, env


def host_for(env: dict[str, str], state: Path, compose_env: Path) -> Host:
    profile = catalog.HostProfile(
        acra_lease_state=state.as_posix(), compose_env=compose_env.as_posix()
    )
    return Host(Gate(LocalShell(env), Mode.EXECUTE, AuditLog()), SshTarget("t@h"), profile)


def set_mode(bin_dir: Path, mode: str) -> None:
    (bin_dir / "mode").write_text(mode, encoding="ascii")


def run_text(env: dict[str, str], text: str) -> str:
    return LocalShell(env).run(Command(("ssh", "--", text), None, "test")).stdout.strip()  # type: ignore[arg-type]


def test_lease_states_are_distinguished_by_the_real_command(
    tmp_path: Path, shim: tuple[Path, dict[str, str]]
) -> None:
    bin_dir, env = shim
    lease_dir = tmp_path / "clm-acra-window"
    state = lease_dir / "state"
    host = host_for(env, state, tmp_path / "compose.env")

    assert host.acra_lease_open() is None  # controller directory missing: unknown
    lease_dir.mkdir()
    assert host.acra_lease_open() is False  # confirmed closed
    state.write_text("WINDOW_ID=x\n", encoding="ascii")
    assert host.acra_lease_open() is True  # open
    set_mode(bin_dir, "deny")
    assert host.acra_lease_open() is None  # permission denied: unknown, never "closed"
    set_mode(bin_dir, "fail")
    assert host.acra_lease_open() is None  # command failure: unknown
    state.unlink()
    for mode in ("deny", "fail"):
        set_mode(bin_dir, mode)
        assert host.acra_lease_open() is None


def test_r1_finding_reproduced_the_old_command_said_closed_when_sudo_was_refused(
    tmp_path: Path, shim: tuple[Path, dict[str, str]]
) -> None:
    bin_dir, env = shim
    lease_dir = tmp_path / "clm-acra-window"
    lease_dir.mkdir()
    state = lease_dir / "state"
    state.write_text("WINDOW_ID=x\n", encoding="ascii")  # a lease IS open
    set_mode(bin_dir, "deny")
    old = run_text(env, OLD_R1_LEASE_COMMAND.format(path=state.as_posix()))
    assert old == "lease-closed"  # the R1 defect: fail-open
    assert host_for(env, state, tmp_path / "compose.env").acra_lease_open() is None


def test_setting_lines_are_read_strictly_by_the_real_command(
    tmp_path: Path, shim: tuple[Path, dict[str, str]]
) -> None:
    bin_dir, env = shim
    compose_env = tmp_path / "compose.env"
    host = host_for(env, tmp_path / "state", compose_env)
    writes = "CLM_GOLDTIER_SANDBOX_ALLOW_WRITES"

    assert host.compose_env_setting_lines(writes) is None  # file missing: unreadable
    compose_env.write_text("BACKEND_IMAGE=x\n", encoding="ascii")
    assert host.compose_env_setting_lines(writes) == []  # absent
    compose_env.write_text(f"{writes}=true\nCLM_GOLDTIER_CONNECTOR_MODE=sandbox\n", "ascii")
    assert host.compose_env_setting_lines(writes) == [f"{writes}=true"]
    assert host.compose_env_setting_lines("CLM_GOLDTIER_CONNECTOR_MODE") == [
        "CLM_GOLDTIER_CONNECTOR_MODE=sandbox"
    ]
    compose_env.write_text(
        f"{writes}=true\nexport {writes}=false\n  {writes} = true\n{writes}X=1\n", "ascii"
    )
    assert host.compose_env_setting_lines(writes) == [
        f"{writes}=true", f"export {writes}=false", f"  {writes} = true"
    ]  # duplicates and ambiguous forms are all visible; the similar name is not
    set_mode(bin_dir, "deny")
    assert host.compose_env_setting_lines(writes) is None  # permission denied
    set_mode(bin_dir, "fail")
    assert host.compose_env_setting_lines(writes) is None  # command failure
