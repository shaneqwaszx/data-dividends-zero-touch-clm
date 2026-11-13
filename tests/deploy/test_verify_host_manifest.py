"""DQ-1 (= DN-3) regression tests for the reviewed-manifest check in verify_host_firewall.sh.

The production paths are fixed in the script (`R3_INSTALLED_FILES`); these tests source the script
(which then defines its functions and runs nothing) and call `check_manifest` with six temporary
files standing in for the installed set. Requires a POSIX bash with GNU sha256sum; skipped if none
can read the temporary directory (for example only WSL's bash.exe on a Windows PATH).
"""

from __future__ import annotations

import hashlib
import itertools
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy" / "egress" / "host" / "verify_host_firewall.sh"
EXPECTED_INSTALLED = [
    "/etc/clm/r3/clm_r3.nft",
    "/usr/local/lib/clm-r3/clm_r3_watch.py",
    "/usr/local/lib/clm-r3/clm_r3_stop_containers.sh",
    "/usr/local/lib/clm-r3/verify_host_firewall.sh",
    "/etc/systemd/system/clm-r3-egress-firewall.service",
    "/etc/systemd/system/clm-r3-firewall-watch.service",
]


def _bash_candidates() -> list[str]:
    found = [shutil.which("bash") or "", r"C:\Program Files\Git\bin\bash.exe", "/bin/bash"]
    return [c for c in found if c and Path(c).exists()]


@pytest.fixture(scope="module")
def bash(tmp_path_factory: pytest.TempPathFactory) -> str:
    probe = tmp_path_factory.mktemp("probe") / "x"
    probe.write_text("x", encoding="ascii")
    for candidate in _bash_candidates():
        result = subprocess.run(
            [candidate, "-c", f'test -r "{probe.as_posix()}" && command -v sha256sum'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    pytest.skip("no POSIX bash with sha256sum that can read the test directory")


@pytest.fixture()
def files(tmp_path: Path) -> list[Path]:
    out = []
    for i in range(6):
        f = tmp_path / f"installed-{i}.txt"
        f.write_bytes(f"reviewed content {i}\n".encode())
        out.append(f)
    return out


def line(path: Path, digest: str | None = None) -> str:
    return f"{digest or hashlib.sha256(path.read_bytes()).hexdigest()}  {path.as_posix()}"


def run(
    bash: str, manifest: str, required: list[Path], env: dict[str, str] | None = None
) -> tuple[int, str]:
    script = f'source "{SCRIPT.as_posix()}"; check_manifest "$@"'
    args = [bash, "-c", script, "check", manifest, *[p.as_posix() for p in required]]
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        env=env if env is not None else dict(os.environ),
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def write(tmp_path: Path, name: str, content: str | bytes) -> str:
    m = tmp_path / name
    m.write_bytes(content.encode() if isinstance(content, str) else content)
    return m.as_posix()


# --- positive -----------------------------------------------------------------------------------


def test_complete_exact_manifest_passes(bash: str, tmp_path: Path, files: list[Path]) -> None:
    m = write(tmp_path, "ok.txt", "\n".join(line(f) for f in files) + "\n")
    rc, out = run(bash, m, files)
    assert (rc, out) == (0, "6 of 6 required files listed and matching")


def test_order_and_missing_final_newline_do_not_matter(
    bash: str, tmp_path: Path, files: list[Path]
) -> None:
    m = write(tmp_path, "ok2.txt", "\n".join(line(f) for f in reversed(files)))
    assert run(bash, m, files)[0] == 0


# --- negative: completeness ---------------------------------------------------------------------


def test_no_proper_subset_of_the_six_files_can_pass(
    bash: str, tmp_path: Path, files: list[Path]
) -> None:
    """DQ-1 core property: every one of the 63 incomplete manifests (including empty) FAILs."""
    checked = 0
    for size in range(0, 6):
        for subset in itertools.combinations(files, size):
            m = write(tmp_path, f"subset-{checked}.txt", "".join(line(f) + "\n" for f in subset))
            rc, out = run(bash, m, files)
            assert rc != 0, f"incomplete manifest passed: {[f.name for f in subset]} -> {out}"
            checked += 1
    assert checked == 63


def test_dq1_reproduction_two_valid_lines_plus_garbage_fails(
    bash: str, tmp_path: Path, files: list[Path]
) -> None:
    m = write(
        tmp_path, "dq1.txt", f"{line(files[0])}\n{line(files[1])}\nthis is not a manifest line\n"
    )
    rc, out = run(bash, m, files)
    assert rc == 1 and "malformed manifest line 3" in out


# --- negative: structure ------------------------------------------------------------------------


def test_duplicate_path_fails_even_when_count_is_six(
    bash: str, tmp_path: Path, files: list[Path]
) -> None:
    lines = [line(f) for f in files[:5]] + [line(files[0])]
    rc, out = run(bash, write(tmp_path, "dup.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "duplicate path" in out


def test_seven_lines_with_a_duplicate_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    lines = [line(f) for f in files] + [line(files[3])]
    rc, out = run(bash, write(tmp_path, "dup7.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "duplicate path" in out


def test_unexpected_path_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    extra = tmp_path / "extra.txt"
    extra.write_bytes(b"extra\n")
    lines = [line(f) for f in files] + [line(extra)]
    rc, out = run(bash, write(tmp_path, "extra.txt.m", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "unexpected path" in out


def test_replacing_a_required_path_with_another_file_fails(
    bash: str, tmp_path: Path, files: list[Path]
) -> None:
    other = tmp_path / "other.txt"
    other.write_bytes(b"reviewed content 0\n")  # same bytes as files[0], different path
    lines = [line(other)] + [line(f) for f in files[1:]]
    rc, out = run(bash, write(tmp_path, "swap.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "unexpected path" in out


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda ln: ln.upper(), id="uppercase-hex"),
        pytest.param(lambda ln: ln.replace("  ", " ", 1), id="single-space"),
        pytest.param(lambda ln: ln.replace("  ", "\t", 1), id="tab-separator"),
        pytest.param(lambda ln: ln.replace("  ", "  *", 1), id="binary-marker"),
        pytest.param(lambda ln: ln + " ", id="trailing-space"),
        pytest.param(lambda ln: " " + ln, id="leading-space"),
        pytest.param(lambda ln: ln + "\r", id="crlf"),
        pytest.param(lambda ln: ln[2:], id="short-hash"),
        pytest.param(lambda ln: "ab" + ln, id="long-hash"),
        pytest.param(lambda ln: ln + "  extra-field", id="extra-field"),
        pytest.param(lambda ln: "# " + ln, id="comment"),
        pytest.param(
            lambda ln: "SHA256 (" + ln.split("  ")[1] + ") = " + ln.split("  ")[0], id="bsd-format"
        ),
    ],
)
def test_malformed_line_fails(  # type: ignore[no-untyped-def]
    bash: str, tmp_path: Path, files: list[Path], mutate
) -> None:
    lines = [line(f) for f in files]
    lines[2] = mutate(lines[2])
    rc, out = run(bash, write(tmp_path, "bad.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "malformed manifest line 3" in out


def test_blank_line_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    lines = [line(f) for f in files[:3]] + [""] + [line(f) for f in files[3:]]
    rc, out = run(bash, write(tmp_path, "blank.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "malformed manifest line 4" in out


def test_shell_metacharacters_in_a_path_are_data_not_code(
    bash: str, tmp_path: Path, files: list[Path]
) -> None:
    marker = tmp_path / "pwned"
    lines = [line(f) for f in files[:5]] + [f"{'0' * 64}  $(touch${{IFS}}{marker.as_posix()})"]
    rc, out = run(bash, write(tmp_path, "meta.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "unexpected path" in out
    assert not marker.exists()


# --- negative: files and hashes -----------------------------------------------------------------


def test_missing_listed_file_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    m = write(tmp_path, "gone.txt", "\n".join(line(f) for f in files) + "\n")
    files[4].unlink()
    rc, out = run(bash, m, files)
    assert rc == 1 and "listed file missing" in out


def test_directory_in_place_of_a_file_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    m = write(tmp_path, "dir.txt", "\n".join(line(f) for f in files) + "\n")
    files[1].unlink()
    files[1].mkdir()
    rc, out = run(bash, m, files)
    assert rc == 1 and "not a regular file" in out


def test_symlink_in_place_of_a_file_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    m = write(tmp_path, "link.txt", "\n".join(line(f) for f in files) + "\n")
    real = tmp_path / "real.txt"
    real.write_bytes(files[2].read_bytes())
    files[2].unlink()
    try:
        files[2].symlink_to(real)
    except OSError:
        pytest.skip("symlinks not permitted on this platform")
    rc, out = run(bash, m, files)
    if (
        rc == 0
        and "symlink"
        not in subprocess.run(
            [bash, "-c", f'test -L "{files[2].as_posix()}" && echo symlink'],
            capture_output=True,
            text=True,
        ).stdout
    ):
        pytest.skip("this bash does not see the link as a symlink")
    assert rc == 1 and "not a regular file" in out


def test_hash_mismatch_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    m = write(tmp_path, "tamper.txt", "\n".join(line(f) for f in files) + "\n")
    files[0].write_bytes(b"tampered after review\n")
    rc, out = run(bash, m, files)
    assert rc == 1 and "hash verification failed" in out


def test_wrong_digest_in_manifest_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    lines = [line(f) for f in files]
    lines[5] = line(files[5], "0" * 64)
    rc, out = run(bash, write(tmp_path, "wrong.txt", "\n".join(lines) + "\n"), files)
    assert rc == 1 and "hash verification failed" in out


# --- negative: fail closed ----------------------------------------------------------------------


def test_unset_manifest_fails(bash: str, files: list[Path]) -> None:
    rc, out = run(bash, "", files)
    assert rc == 1 and "not set (required)" in out


def test_absent_manifest_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    rc, out = run(bash, (tmp_path / "nope.txt").as_posix(), files)
    assert rc == 1 and "missing or unreadable" in out


def test_manifest_that_is_a_directory_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    rc, out = run(bash, tmp_path.as_posix(), files)
    assert rc == 1 and "missing or unreadable" in out


def test_empty_manifest_fails(bash: str, tmp_path: Path, files: list[Path]) -> None:
    rc, out = run(bash, write(tmp_path, "empty.txt", ""), files)
    assert rc == 1 and "incomplete (0 of 6)" in out


def test_unavailable_hash_tool_fails_closed(bash: str, tmp_path: Path, files: list[Path]) -> None:
    m = write(tmp_path, "ok.txt", "\n".join(line(f) for f in files) + "\n")
    env = dict(os.environ)
    env["PATH"] = str(tmp_path / "empty-bin")  # no sha256sum reachable; bash builtins still work
    rc, out = run(bash, m, files, env=env)
    assert rc == 1 and "sha256sum not available" in out


def test_no_required_paths_fails(bash: str, tmp_path: Path) -> None:
    rc, out = run(bash, write(tmp_path, "x.txt", ""), [])
    assert rc == 1 and "no required paths" in out


# --- production wiring (static) -----------------------------------------------------------------


def test_production_path_set_is_exactly_the_six_installed_files() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    block = re.search(r"R3_INSTALLED_FILES=\(\n(.*?)\n\)", text, re.S)
    assert block is not None
    assert [p.strip() for p in block.group(1).splitlines()] == EXPECTED_INSTALLED
    stack = (ROOT / "tests" / "deploy" / "egress_harness" / "vm" / "stack.sh").read_text(
        encoding="utf-8"
    )
    for path in EXPECTED_INSTALLED:
        assert path.rsplit("/", 1)[0] in stack  # the harness installs into the same directories


def test_main_requires_the_manifest_and_has_no_optional_path() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(x for x in text.splitlines() if not x.lstrip().startswith("#"))
    assert 'check_manifest "${R3_REVIEWED_MANIFEST:-}" "${R3_INSTALLED_FILES[@]}"' in code
    assert "sha256sum --strict --quiet -c" in code
    assert "not checked" not in code and "grep -c ." not in code
    assert "R3_VERIFY_ROOT" not in code  # no environment override of production paths
    assert code.count("/tmp/.clm_r3_manifest") == 0  # the new check writes no temporary file
    assert "LiveRestoreEnabled" in code


# --- R-1 pin (fast-track A2): the verify script's pinned-set parser --------------------------


def _pin(bash: str, table: Path) -> tuple[int, str]:
    script = f'source "{SCRIPT.as_posix()}"; pinned_from_table "$1"'
    result = subprocess.run(
        [bash, "-c", script, "pin", table.as_posix()], capture_output=True, text=True, check=False
    )
    return result.returncode, result.stdout.strip()


def test_pin_parser_reads_the_reviewed_table(bash: str) -> None:
    rc, out = _pin(bash, ROOT / "deploy" / "egress" / "host" / "clm_r3.nft")
    assert rc == 0
    assert out.splitlines() == ["13.42.220.164", "18.135.200.6"]


@pytest.mark.parametrize(
    "body",
    [
        "table inet clm_r3 {\n}\n",  # no pinned set
        "table inet clm_r3 {\n  set goldtier_dst_v4 {\n    type ipv4_addr\n  }\n}\n",  # empty
        "table inet clm_r3 {\n  set goldtier_dst_v4 {\n    type ipv4_addr\n"
        "    elements = { }\n  }\n}\n",
    ],
)
def test_pin_parser_fails_closed_without_a_pinned_set(bash: str, tmp_path: Path, body: str) -> None:
    table = tmp_path / "t.nft"
    table.write_text(body, encoding="ascii")
    rc, out = _pin(bash, table)
    assert rc == 1 and out == ""


def test_pin_parser_and_normaliser_agree_on_order(bash: str, tmp_path: Path) -> None:
    table = tmp_path / "t.nft"
    table.write_text(
        "table inet clm_r3 {\n  set goldtier_dst_v4 {\n    type ipv4_addr\n"
        "    elements = { 18.135.200.6, 13.42.220.164, 9.9.9.9 }\n  }\n}\n",
        encoding="ascii",
    )
    script = (
        f'source "{SCRIPT.as_posix()}"; '
        '[ "$(pinned_from_table "$1")" = "$(normalise_dst_list "$2")" ]'
    )
    ok = subprocess.run(
        [bash, "-c", script, "x", table.as_posix(), "13.42.220.164,9.9.9.9,18.135.200.6"],
        check=False,
    )
    bad = subprocess.run(
        [bash, "-c", script, "x", table.as_posix(), "13.42.220.164,18.135.200.6"], check=False
    )
    assert ok.returncode == 0 and bad.returncode != 0
