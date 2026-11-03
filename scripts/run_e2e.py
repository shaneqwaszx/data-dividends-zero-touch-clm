"""Run the authenticated Playwright smoke with owned local processes."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import IO, Protocol, TypedDict, cast

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "apps" / "frontend"
BACKEND_SERVER = ROOT / "scripts" / "e2e_backend_server.py"
DEFAULT_BACKEND_PORT = 8765
DEFAULT_FRONTEND_PORT = 4173
MAX_CAPTURE_CHARS = 64_000
PROCESS_STOP_POLL_SECONDS = 0.05
PROCESS_STOP_TIMEOUT_SECONDS = 5.0
# Three owned processes can each require six 5-second stop phases. Reserve
# 120 seconds per lifecycle for those bounded phases, capture joins and dispatch.
LIFECYCLE_OVERHEAD_SECONDS = 120.0
DISCOVERY_TIMEOUT_SECONDS = 60.0
# Chromium refuses navigation to these ports (ERR_UNSAFE_PORT). Pinned from
# chromium/src net/base/port_util.cc kRestrictedPorts on 2026-10-22. That list
# omits 4190 and 6679, so the default 8765/4173 lifecycle ranges stay valid.
CHROMIUM_RESTRICTED_PORTS = frozenset({
    0, 1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 69, 77, 79,
    87, 95, 101, 102, 103, 104, 109, 110, 111, 113, 115, 117, 119, 123, 135, 137,
    139, 143, 161, 179, 389, 427, 465, 512, 513, 514, 515, 526, 530, 531, 532, 540,
    548, 554, 556, 563, 587, 601, 636, 989, 990, 993, 995, 1719, 1720, 1723, 2049,
    3659, 4045, 5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080,
})
RESULTS_SCHEMA_VERSION = 1
LIFECYCLE_RESULTS = (
    "PASS", "PORT_UNAVAILABLE", "READINESS_FAILURE", "ASSERTION_FAILURE",
    "INDIVIDUAL_SELECTION_TIMEOUT", "CLEANUP_FAILURE", "INTERRUPTED", "NOT_RUN",
)
SETUP_FAILURE_STAGES = ("DISCOVERY", "SELECTION", "PORT_ALLOCATION", "PORT_PREFLIGHT")
RECOVERY_DEMO_MODES = ("optional-amend", "stale-policy", "retained-recovery", "search-recheck", "document-refresh")
SANDBOX_DEMO_MODES = (
    "success", "uncertain-shell", "uncertain-policy", "failed-policy", "existing-customer",
    "garden-existing-customer", "database-alpha", "database-partnership", "database-government",
    "sponsor-aurora", "sponsor-pacific", "sponsor-straits", "sponsor-meridian",
    "sponsor-garden", "sponsor-merlion", "sponsor-multiple", "sponsor-multilevel",
)
_URI_PATTERN = re.compile(r"(?i)(?:mongodb(?:\+srv)?|https?)://[^\s\]\[<>{}\"']+")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(password|secret|token|authorization|cookie)\s*[:=]\s*[^\s,;]+"
)
_SYSTEM_ENV_KEYS = (
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "LC_ALL",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMPDIR",
    "TMP",
    "USERPROFILE",
    "WINDIR",
)


class _PosixOS(Protocol):
    def killpg(self, process_group_id: int, signal_number: int) -> None: ...


class _PlatformSignals(Protocol):
    CTRL_BREAK_EVENT: int
    SIGKILL: int


class _WindowsSubprocess(Protocol):
    CREATE_NEW_PROCESS_GROUP: int


# Typed module views preserve guarded platform calls without absent-stub errors.
_POSIX_OS = cast(_PosixOS, os)
_PLATFORM_SIGNALS = cast(_PlatformSignals, signal)
_WINDOWS_SUBPROCESS = cast(_WindowsSubprocess, subprocess)


class _PopenOptions(TypedDict, total=False):
    start_new_session: bool


class OutputCapture:
    """Drain a child pipe while retaining only a bounded tail."""

    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream
        self._chunks: deque[str] = deque()
        self._length = 0
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self) -> None:
        for line in self._stream:
            self._chunks.append(line)
            self._length += len(line)
            while self._length > MAX_CAPTURE_CHARS and self._chunks:
                self._length -= len(self._chunks.popleft())

    def text(self) -> str:
        self._thread.join(timeout=2)
        return "".join(self._chunks)


class OwnedProcess:
    """A process and the exact process group created for this run."""

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
    ) -> None:
        creationflags = 0
        kwargs: _PopenOptions = {}
        if os.name == "nt":
            creationflags = _WINDOWS_SUBPROCESS.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        self.name = name
        self.process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            **kwargs,
        )
        if self.process.stdout is None:
            raise RuntimeError(f"Unable to capture {name} output")
        self.capture = OutputCapture(self.process.stdout)
        self.process_group_id = None if os.name == "nt" else self.process.pid

    def stop(self) -> None:
        if os.name == "nt":
            if self.process.poll() is not None:
                return
            try:
                self.process.send_signal(_PLATFORM_SIGNALS.CTRL_BREAK_EVENT)
                self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
            except (OSError, subprocess.TimeoutExpired):
                if self.process.poll() is None:
                    subprocess.run(
                        ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=10,
                    )
            try:
                self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
            if self.process.poll() is None:
                raise RuntimeError(f"Task-owned {self.name} process did not terminate")
            return

        process_group_id = self.process_group_id
        if process_group_id is None:
            raise RuntimeError(f"Task-owned {self.name} process group is unavailable")
        try:
            _POSIX_OS.killpg(process_group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        try:
            _wait_for_posix_process_group_exit(
                process_group_id,
                deadline=time.monotonic() + PROCESS_STOP_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            try:
                _POSIX_OS.killpg(process_group_id, _PLATFORM_SIGNALS.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                pass
            try:
                _wait_for_posix_process_group_exit(
                    process_group_id,
                    deadline=time.monotonic() + PROCESS_STOP_TIMEOUT_SECONDS,
                )
            except TimeoutError as exc:
                raise RuntimeError(
                    f"Task-owned {self.name} process group did not terminate"
                ) from exc
        try:
            self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
        if self.process.poll() is None:
            raise RuntimeError(f"Task-owned {self.name} process did not terminate")


def _wait_for_posix_process_group_exit(
    process_group_id: int,
    *,
    deadline: float,
) -> None:
    """Prove the exact task-created POSIX process group no longer exists."""

    while True:
        try:
            _POSIX_OS.killpg(process_group_id, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            pass
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Task-owned POSIX process group is still present")
        time.sleep(min(PROCESS_STOP_POLL_SECONDS, remaining))


def _parse_port(value: str, name: str) -> int:
    if not value.isascii() or not value.isdecimal():
        raise argparse.ArgumentTypeError(f"{name} must be a decimal integer")
    port = int(value)
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"{name} must be between 1024 and 65535")
    return port


def _allocate_lifecycle_ports(
    backend_port: int,
    frontend_port: int,
    selection_count: int,
) -> list[tuple[int, int]]:
    """Derive one deterministic, non-overlapping port pair per selection."""

    if (
        isinstance(selection_count, bool)
        or not isinstance(selection_count, int)
        or selection_count < 1
    ):
        raise ValueError("E2E selection count must be a positive integer")
    if any(
        isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535
        for port in (backend_port, frontend_port)
    ):
        raise ValueError("Configured E2E ports must be between 1024 and 65535")

    allocated: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for index in range(selection_count):
        pair = (backend_port + index, frontend_port + index)
        if any(
            isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535
            for port in pair
        ):
            raise ValueError("Derived E2E ports must be between 1024 and 65535")
        if pair[0] == pair[1] or pair[0] in allocated or pair[1] in allocated:
            raise ValueError("Derived E2E lifecycle port collision")
        _reject_restricted_ports(*pair, lifecycle=index + 1)
        allocated.update(pair)
        pairs.append(pair)
    return pairs


def _reject_restricted_ports(
    backend_port: int, frontend_port: int, *, lifecycle: int | None = None,
) -> None:
    for name, port in (("backend", backend_port), ("frontend", frontend_port)):
        if port in CHROMIUM_RESTRICTED_PORTS:
            where = f" for lifecycle {lifecycle}" if lifecycle is not None else ""
            raise ValueError(
                f"E2E {name} port {port}{where} is restricted by Chromium "
                "(ERR_UNSAFE_PORT); choose a different base port"
            )


def _assert_ports_available(
    backend_port: int, frontend_port: int, *, tolerate_time_wait: bool = False,
) -> None:
    if backend_port == frontend_port:
        raise ValueError("Backend and frontend ports must be distinct")
    sockets: list[socket.socket] = []
    try:
        for port in (backend_port, frontend_port):
            candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets.append(candidate)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                candidate.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            elif tolerate_time_wait:
                # POSIX bind otherwise rejects a recently used port in TIME_WAIT;
                # a live listener still makes the bind fail.
                candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            candidate.bind(("127.0.0.1", port))
    except OSError as exc:
        raise RuntimeError("An assigned E2E loopback port is already occupied") from exc
    finally:
        for candidate in sockets:
            candidate.close()


def _preflight_lifecycle_ports(pairs: Sequence[tuple[int, int]]) -> None:
    """Reject unsafe or occupied lifecycle ports before any lifecycle starts.

    Each lifecycle still probes its own pair at startup; this only moves a
    deterministic conflict from the middle of a long suite to its start.
    """

    for index, (backend_port, frontend_port) in enumerate(pairs, start=1):
        _reject_restricted_ports(backend_port, frontend_port, lifecycle=index)
        try:
            _assert_ports_available(backend_port, frontend_port, tolerate_time_wait=True)
        except RuntimeError as exc:
            raise RuntimeError(
                f"Assigned E2E loopback ports for lifecycle {index} "
                f"({backend_port}/{frontend_port}) are already occupied"
            ) from exc


def _base_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    current = os.environ if source is None else source
    result = {key: current[key] for key in _SYSTEM_ENV_KEYS if key in current}
    result["PYTHONIOENCODING"] = "utf-8"
    return result


def _sanitize(value: str, secrets_to_remove: Sequence[str] = ()) -> str:
    sanitized = value
    for secret in sorted((item for item in secrets_to_remove if item), key=len, reverse=True):
        sanitized = sanitized.replace(secret, "[REDACTED]")
    sanitized = _URI_PATTERN.sub("[REDACTED_URI]", sanitized)
    sanitized = _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", sanitized)
    bounded = sanitized[-12_000:]
    return bounded.encode("ascii", errors="backslashreplace").decode("ascii")


def _wait_for_http(
    url: str,
    process: OwnedProcess,
    deadline: float,
    *,
    expected_text: str | None = None,
) -> None:
    while time.monotonic() < deadline:
        return_code = process.process.poll()
        if return_code is not None:
            raise RuntimeError(f"{process.name} exited before readiness (code {return_code})")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                body = response.read(64_000).decode("utf-8", errors="replace")
            if response.status == 200 and (expected_text is None or expected_text in body):
                return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.2)
    raise TimeoutError(f"{process.name} readiness timed out")


def _wait_for_test(process: OwnedProcess, deadline: float) -> int:
    while time.monotonic() < deadline:
        return_code = process.process.poll()
        if return_code is not None:
            return return_code
        time.sleep(0.2)
    raise TimeoutError("Playwright test execution timed out")


def _find_node() -> str:
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is not available on PATH")
    return node


def _selectors_from_listing(
    payload: object, *, garden_selectors: set[str] | None = None,
    registry_selectors: dict[str, str] | None = None,
    recovery_selectors: dict[str, str] | None = None,
    sandbox_selectors: dict[str, str] | None = None,
) -> list[str]:
    if not isinstance(payload, dict):
        raise TypeError("Playwright test discovery returned an invalid document")
    if payload.get("errors"):
        raise RuntimeError("Playwright test discovery reported configuration errors")

    selectors: list[str] = []
    fixture_modes: dict[str, tuple[bool, str | None, str | None, str | None]] = {}

    def visit(suites: object) -> None:
        if not isinstance(suites, list):
            raise TypeError("Playwright test discovery returned invalid suites")
        for suite in suites:
            if not isinstance(suite, dict):
                raise TypeError("Playwright test discovery returned an invalid suite")
            specs = suite.get("specs", [])
            if not isinstance(specs, list):
                raise TypeError("Playwright test discovery returned invalid specs")
            for spec in specs:
                if not isinstance(spec, dict):
                    raise TypeError("Playwright test discovery returned an invalid test")
                if spec.get("ok") is not True:
                    raise RuntimeError("Playwright test discovery returned an invalid test")
                file_name = spec.get("file")
                line = spec.get("line")
                if not isinstance(file_name, str) or not isinstance(line, int) or line < 1:
                    raise RuntimeError("Playwright test discovery omitted a test location")
                relative = PurePosixPath(file_name.replace("\\", "/"))
                if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".ts":
                    raise RuntimeError("Playwright test discovery returned an unsafe path")
                selector = f"{(PurePosixPath('e2e') / relative).as_posix()}:{line}"
                tags = spec.get("tags", [])
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise RuntimeError("Playwright test discovery returned invalid fixture tags")
                tags = [tag.removeprefix("@") for tag in tags]
                garden = "garden-protocol" in tags or selector.startswith("e2e/garden-happy-path.e2e.ts:")
                registry_modes = [
                    mode for mode in ("garden-partnership", "garden-declaration", "five-layer-hybrid", "synthetic-cache", "synthetic-seed")
                    if f"slice-b-{mode}" in tags
                ]
                for suffix in ("ambiguity", "reuse"):
                    if f"slice-f-target-{suffix}" in tags:
                        registry_modes.append(f"synthetic-target-{suffix}")
                if any(tag.startswith("slice-f-target-") and tag not in {
                    "slice-f-target-ambiguity", "slice-f-target-reuse"
                } for tag in tags):
                    raise RuntimeError("Playwright test discovery returned an unknown target fixture")
                recovery_modes = [mode for mode in RECOVERY_DEMO_MODES
                                  if f"slice-c-{mode}" in tags]
                sandbox_modes = [mode for mode in SANDBOX_DEMO_MODES
                                 if f"s3-sandbox-{mode}" in tags]
                if any(tag.startswith("s3-sandbox-") and tag not in {
                    f"s3-sandbox-{mode}" for mode in SANDBOX_DEMO_MODES
                } for tag in tags):
                    raise RuntimeError("Playwright discovery returned an unknown Sandbox fixture")
                if any(tag.startswith("slice-c-") and tag not in {
                    f"slice-c-{mode}" for mode in RECOVERY_DEMO_MODES
                } for tag in tags):
                    raise RuntimeError("Playwright test discovery returned an unknown recovery fixture")
                if (len(registry_modes) + len(recovery_modes) + len(sandbox_modes) + int(garden)) > 1:
                    raise RuntimeError("Playwright test discovery returned conflicting fixture modes")
                registry_mode = registry_modes[0] if registry_modes else None
                recovery_mode = recovery_modes[0] if recovery_modes else None
                sandbox_mode = sandbox_modes[0] if sandbox_modes else None
                mode_identity = (garden, registry_mode, recovery_mode, sandbox_mode)
                if selector in fixture_modes and fixture_modes[selector] != mode_identity:
                    raise RuntimeError("Playwright test discovery returned conflicting fixture modes")
                fixture_modes[selector] = mode_identity
                if registry_mode and registry_selectors is not None:
                    registry_selectors[selector] = registry_mode
                if garden and garden_selectors is not None:
                    garden_selectors.add(selector)
                if recovery_mode and recovery_selectors is not None:
                    recovery_selectors[selector] = recovery_mode
                if sandbox_mode and sandbox_selectors is not None:
                    sandbox_selectors[selector] = sandbox_mode
                if selector not in selectors:
                    selectors.append(selector)
            visit(suite.get("suites", []))

    visit(payload.get("suites", []))
    if not selectors:
        raise RuntimeError("Playwright test discovery found no configured tests")
    return selectors


def _list_test_selectors(
    frontend_port: int, *, garden_selectors: set[str] | None = None,
    registry_selectors: dict[str, str] | None = None,
    recovery_selectors: dict[str, str] | None = None,
    sandbox_selectors: dict[str, str] | None = None,
) -> list[str]:
    node = _find_node()
    playwright_cli = FRONTEND_ROOT / "node_modules" / "@playwright" / "test" / "cli.js"
    if not playwright_cli.is_file():
        raise RuntimeError(
            f"Required local dependency is missing: {playwright_cli.relative_to(ROOT)}"
        )
    environment = {
        **_base_environment(),
        "PLAYWRIGHT_BASE_URL": f"http://127.0.0.1:{frontend_port}",
    }
    completed = subprocess.run(
        [
            node,
            str(playwright_cli),
            "test",
            "--config",
            "playwright.config.ts",
            "--list",
            "--reporter=json",
        ],
        cwd=FRONTEND_ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=DISCOVERY_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        detail = _sanitize(completed.stdout + completed.stderr)
        raise RuntimeError(f"Playwright test discovery failed: {detail}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Playwright test discovery returned invalid JSON") from exc
    return _selectors_from_listing(payload, garden_selectors=garden_selectors,
                                   registry_selectors=registry_selectors,
                                   recovery_selectors=recovery_selectors,
                                   sandbox_selectors=sandbox_selectors)


def _cleanup_classification_database(database: str, port: int = 27185) -> None:
    """Parent-owned cleanup survives a forcibly stopped Windows test server."""
    from pymongo import MongoClient

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.mongo_test_safety import (
        cleanup_ephemeral_mongo_database,
        require_ephemeral_mongo_database,
    )

    require_ephemeral_mongo_database(database)
    with MongoClient(host="127.0.0.1", port=port, serverSelectionTimeoutMS=3000) as client:
        cleanup_ephemeral_mongo_database(client, database)
    print("CLASSIFICATION_DATABASE_CLEANUP=VERIFIED")


def run(
    *,
    backend_port: int,
    frontend_port: int,
    timeout_seconds: float,
    headed: bool = False,
    grep: str | None = None,
    selection: str | None = None,
    diagnostics: bool = False,
    garden_protocol: bool = False,
    registry_demo: str | None = None,
    recovery_demo: str | None = None,
    sandbox_demo: str | None = None,
    outcome: dict[str, object] | None = None,
) -> int:
    # Optional caller-owned record of the result kind and phase durations.
    record: dict[str, object] = {} if outcome is None else outcome
    phases: dict[str, float | None] = {
        "backend_ready_seconds": None,
        "frontend_ready_seconds": None,
        "playwright_seconds": None,
        "cleanup_seconds": None,
    }
    record["result"] = "PORT_UNAVAILABLE"
    record["phases"] = phases
    if sandbox_demo not in {None, *SANDBOX_DEMO_MODES}:
        raise ValueError("Unknown isolated Sandbox fixture")
    if sandbox_demo and (not (grep or selection) or garden_protocol or registry_demo or recovery_demo):
        raise ValueError("Sandbox fixture requires focused selection and separate composition")
    if registry_demo not in {None, "garden-partnership", "garden-declaration", "five-layer-hybrid", "synthetic-cache", "synthetic-seed", "synthetic-target-ambiguity", "synthetic-target-reuse"}:
        raise ValueError("Unknown Slice-B registry fixture")
    if registry_demo is not None and (not (grep or selection) or garden_protocol):
        raise ValueError("Slice-B registry fixture requires a focused grep and separate composition")
    if recovery_demo not in {None, *RECOVERY_DEMO_MODES}:
        raise ValueError("Unknown Slice-C recovery fixture")
    if recovery_demo and (not (grep or selection) or garden_protocol or registry_demo):
        raise ValueError("Slice-C recovery fixture requires a focused grep and separate composition")
    if grep is not None and selection is not None:
        raise ValueError("grep and exact test selection are mutually exclusive")
    try:
        _reject_restricted_ports(backend_port, frontend_port)
        _assert_ports_available(backend_port, frontend_port)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"E2E FAILED: {_sanitize(str(exc))}", file=sys.stderr)
        return 1
    record["result"] = "READINESS_FAILURE"
    node = _find_node()
    vite_cli = FRONTEND_ROOT / "node_modules" / "vite" / "bin" / "vite.js"
    playwright_cli = FRONTEND_ROOT / "node_modules" / "@playwright" / "test" / "cli.js"
    for required in (vite_cli, playwright_cli):
        if not required.is_file():
            raise RuntimeError(f"Required local dependency is missing: {required.relative_to(ROOT)}")

    backend_origin = f"http://127.0.0.1:{backend_port}"
    frontend_origin = f"http://127.0.0.1:{frontend_port}"
    ephemeral_credential = secrets.token_urlsafe(32)
    common = _base_environment()
    # Default matches CI's Mongo service. Local concurrent work can reserve its own port.
    synthetic_seed_port = int(os.environ.get("CLM_E2E_SYNTHETIC_MONGO_PORT", "27185"))
    if not 1024 <= synthetic_seed_port <= 65535:
        raise RuntimeError("Synthetic seed Mongo port is outside the allowed range")
    classification_database = (
        f"clm_{'uat' if sandbox_demo and sandbox_demo.startswith('sponsor-') else 'p16'}_"
        f"{secrets.token_hex(12)}"
        if registry_demo == "synthetic-seed" or sandbox_demo in {"database-alpha", "database-partnership", "database-government"}
        or (sandbox_demo is not None and sandbox_demo.startswith("sponsor-"))
        else None
    )
    backend_environment = {
        **common,
        "CLM_E2E_PASSWORD": ephemeral_credential,
        "CLM_E2E_BACKEND_PORT": str(backend_port),
        "CLM_E2E_SYNTHETIC_MONGO_PORT": str(synthetic_seed_port),
        "CLM_E2E_FRONTEND_ORIGIN": frontend_origin,
        **({"CLM_E2E_DIAGNOSTICS": "1"} if diagnostics else {}),
        **({"CLM_E2E_GARDEN_PROTOCOL": "1"} if garden_protocol else {}),
        **({"CLM_E2E_REGISTRY_DEMO": registry_demo} if registry_demo else {}),
        **({"CLM_E2E_RECOVERY_DEMO": recovery_demo} if recovery_demo else {}),
        **({"CLM_E2E_SANDBOX_DEMO": sandbox_demo} if sandbox_demo else {}),
        **({"CLM_E2E_CLASSIFICATION_DATABASE": classification_database}
           if classification_database else {}),
    }
    frontend_environment = {
        **common,
        "VITE_BACKEND_PROXY_TARGET": backend_origin,
        "CLM_E2E_FRONTEND_PORT": str(frontend_port),
        **({"CLM_E2E_DIAGNOSTICS": "1", "VITE_E2E_DIAGNOSTICS": "1"} if diagnostics else {}),
        **({"VITE_E2E_RECOVERY_DEMO": recovery_demo} if recovery_demo else {}),
    }
    test_environment = {
        **common,
        "CLM_E2E_PASSWORD": ephemeral_credential,
        "CLM_E2E_BACKEND_ORIGIN": backend_origin,
        # Playwright 1.56 otherwise writes an AI-oriented DOM snapshot named
        # error-context.md after failures; authenticated pages may contain KYC data.
        "PLAYWRIGHT_NO_COPY_PROMPT": "1",
        "PLAYWRIGHT_BASE_URL": frontend_origin,
        **({"CLM_E2E_DIAGNOSTICS": "1"} if diagnostics else {}),
    }

    processes: list[OwnedProcess] = []
    cleanup_failures: list[str] = []
    result = 1
    phase_started = time.monotonic()
    deadline = phase_started + timeout_seconds
    failure_kind = "READINESS_FAILURE"

    def finish_phase(name: str) -> None:
        nonlocal phase_started
        now = time.monotonic()
        phases[name] = round(now - phase_started, 3)
        phase_started = now

    try:
        backend = OwnedProcess(
            "backend",
            [sys.executable, str(BACKEND_SERVER)],
            cwd=ROOT,
            env=backend_environment,
        )
        processes.append(backend)
        record["phase"] = "backend_ready"
        _wait_for_http(f"{backend_origin}/health", backend, deadline, expected_text='"status":"ok"')
        finish_phase("backend_ready_seconds")

        frontend = OwnedProcess(
            "frontend",
            [
                node,
                str(vite_cli),
                "--host",
                "127.0.0.1",
                "--port",
                str(frontend_port),
                "--strictPort",
            ],
            cwd=FRONTEND_ROOT,
            env=frontend_environment,
        )
        processes.append(frontend)
        record["phase"] = "frontend_ready"
        _wait_for_http(frontend_origin, frontend, deadline, expected_text="Zero-Touch CLM")
        finish_phase("frontend_ready_seconds")

        playwright_command = [
            node,
            str(playwright_cli),
            "test",
            "--config",
            "playwright.config.ts",
        ]
        if headed:
            playwright_command.append("--headed")
        if grep:
            playwright_command.extend(("--grep", grep))
        if selection:
            playwright_command.append(selection)
        record["phase"] = "playwright"
        tests = OwnedProcess(
            "playwright",
            playwright_command,
            cwd=FRONTEND_ROOT,
            env=test_environment,
        )
        processes.append(tests)
        failure_kind = "ASSERTION_FAILURE"
        return_code = _wait_for_test(tests, deadline)
        finish_phase("playwright_seconds")
        sanitized = _sanitize(tests.capture.text(), (ephemeral_credential,))
        if sanitized:
            print(sanitized)
        if diagnostics:
            for process in (backend, frontend):
                milestones = _sanitize(
                    "\n".join(
                        line for line in process.capture.text().splitlines()
                        if line.startswith("E2E_DIAG ")
                    ),
                    (ephemeral_credential,),
                )
                if milestones:
                    print(milestones)
        if return_code != 0:
            print("E2E FAILED [ASSERTION_FAILURE]: Playwright returned a non-zero status.", file=sys.stderr)
            record["result"] = "ASSERTION_FAILURE"
            result = return_code
        else:
            record["result"] = "PASS"
            result = 0
    except KeyboardInterrupt:
        print("E2E INTERRUPTED: stopping task-owned process groups.", file=sys.stderr)
        record["result"] = "INTERRUPTED"
        result = 130
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        if failure_kind == "ASSERTION_FAILURE" and isinstance(exc, TimeoutError):
            failure_kind = "INDIVIDUAL_SELECTION_TIMEOUT"
        if isinstance(exc, TimeoutError):
            # The runner's lifecycle deadline fired (not Playwright's own per-test timeout).
            record["timeout_owner"] = f"runner_lifecycle_{timeout_seconds:g}s"
        active = f"{record.get('phase')}_seconds"
        if active in phases and phases[active] is None:
            phases[active] = round(time.monotonic() - phase_started, 3)
        record["result"] = failure_kind
        print(
            f"E2E FAILED [{failure_kind}]: {_sanitize(str(exc), (ephemeral_credential,))}",
            file=sys.stderr,
        )
        for process in processes:
            output = _sanitize(process.capture.text(), (ephemeral_credential,))
            if output:
                print(f"[{process.name} sanitized output]\n{output}", file=sys.stderr)
        result = 1
    finally:
        phase_started = time.monotonic()
        for process in reversed(processes):
            try:
                process.stop()
            except (OSError, RuntimeError, subprocess.SubprocessError, TimeoutError) as exc:
                cleanup_failures.append(_sanitize(str(exc)))

        if classification_database is not None:
            try:
                _cleanup_classification_database(classification_database, synthetic_seed_port)
            except Exception:  # noqa: BLE001 - driver errors are deliberately sanitized
                cleanup_failures.append("Classification disposable database cleanup failed")
        finish_phase("cleanup_seconds")

    if cleanup_failures:
        print(
            f"E2E FAILED [CLEANUP_FAILURE]: task-owned process cleanup failed: {cleanup_failures[0]}",
            file=sys.stderr,
        )
        record["result"] = "CLEANUP_FAILURE"
        return 1
    if result == 0:
        print("E2E PASS: guarded authenticated local Mock browser suite completed.")
    return result


def _parse_shard(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9]\d*)/([1-9]\d*)", value)
    if match is None or int(match[1]) > int(match[2]):
        raise argparse.ArgumentTypeError("Shard must be INDEX/TOTAL with 1 <= INDEX <= TOTAL")
    return int(match[1]), int(match[2])


def _shard_selectors(
    selectors: list[str], shard: tuple[int, int] | None,
) -> list[str]:
    if shard is None:
        return selectors
    index, total = shard
    if not 1 <= index <= total <= len(selectors):
        raise ValueError("Shard must select at least one discovered lifecycle")
    return selectors[index - 1 :: total]


def _read_selector_file(path: Path, discovered: Sequence[str]) -> list[str]:
    """Return the requested selectors in discovery order; unknown entries fail closed."""

    requested: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            requested.append(entry)
    if not requested:
        raise ValueError("Selector file names no selectors")
    if len(set(requested)) != len(requested):
        raise ValueError("Selector file repeats a selector")
    unknown = [entry for entry in requested if entry not in discovered]
    if unknown:
        raise ValueError(
            f"Selector file names {len(unknown)} selector(s) absent from current discovery; "
            f"first: {unknown[0]}"
        )
    wanted = set(requested)
    return [selector for selector in discovered if selector in wanted]


def _git_identity() -> dict[str, object]:
    environment = {**_base_environment(), "GIT_OPTIONAL_LOCKS": "0"}

    def value(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *args], cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                check=False, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None

    status = value("status", "--porcelain")
    return {
        "head": value("rev-parse", "HEAD"),
        "tree": value("rev-parse", "HEAD^{tree}"),
        "dirty": None if status is None else bool(status),
        "origin_main": value("rev-parse", "--verify", "origin/main^{commit}"),
    }


def _environment_summary() -> dict[str, object]:
    node_version: str | None = None
    try:
        completed = subprocess.run(
            [_find_node(), "--version"], env=_base_environment(), stdin=subprocess.DEVNULL,
            capture_output=True, text=True, check=False, timeout=10,
        )
        if completed.returncode == 0:
            node_version = completed.stdout.strip()
    except (OSError, RuntimeError, subprocess.SubprocessError):
        pass
    playwright_version: str | None = None
    manifest = FRONTEND_ROOT / "node_modules" / "@playwright" / "test" / "package.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        playwright_version = version if isinstance(version, str) else None
    except (OSError, ValueError, AttributeError):
        pass
    return {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "node": node_version,
        "playwright": playwright_version,
    }


def _write_results(path: Path, document: Mapping[str, object]) -> None:
    # Exclusive creation: a results file is evidence and is never overwritten.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
        handle.write("\n")
    print(f"E2E RESULTS: {path}")


def run_isolated_suite(
    *,
    backend_port: int,
    frontend_port: int,
    timeout_seconds: float,
    headed: bool,
    diagnostics: bool = False,
    shard: tuple[int, int] | None = None,
    keep_going: bool = False,
    selectors_file: Path | None = None,
    results_path: Path | None = None,
) -> int:
    started = time.monotonic()
    if shard is not None and selectors_file is not None:
        raise ValueError("A selector file and a shard are mutually exclusive")
    if results_path is not None and (results_path.exists() or not results_path.parent.is_dir()):
        print(
            "E2E FAILED: results file must be a new path in an existing directory.",
            file=sys.stderr,
        )
        return 1
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mode = "shard" if shard else "selectors-file" if selectors_file else "full"
    document: dict[str, object] = {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "runner": "scripts/run_e2e.py",
        "status": "FAIL",
        "complete": False,
        "mode": mode,
        "shard": f"{shard[0]}/{shard[1]}" if shard else None,
        "keep_going": keep_going,
        "timeout_seconds": timeout_seconds,
        "discovered_count": None,
        "selected_count": None,
        "started_at_utc": started_at,
        "elapsed_seconds": None,
        "counts": {},
        "lifecycles": [],
    }
    lifecycles: list[dict[str, object]] = []

    def finish(code: int, *, complete: bool) -> int:
        if results_path is None:
            return code
        counts: dict[str, int] = {}
        for item in lifecycles:
            counts[str(item["result"])] = counts.get(str(item["result"]), 0) + 1
        document.update(
            status="PASS" if code == 0 else "FAIL",
            complete=complete,
            elapsed_seconds=round(time.monotonic() - started, 3),
            counts=counts,
            lifecycles=lifecycles,
            identity=_git_identity(),
            environment=_environment_summary(),
        )
        try:
            _write_results(results_path, document)
        except OSError as exc:
            print(f"E2E FAILED: results file could not be written: {_sanitize(str(exc))}",
                  file=sys.stderr)
            return code or 1
        return code

    setup_stage = "DISCOVERY"
    try:
        garden_selectors: set[str] = set()
        registry_selectors: dict[str, str] = {}
        recovery_selectors: dict[str, str] = {}
        sandbox_selectors: dict[str, str] = {}
        selectors = _list_test_selectors(frontend_port, garden_selectors=garden_selectors,
                                         registry_selectors=registry_selectors,
                                         recovery_selectors=recovery_selectors,
                                         sandbox_selectors=sandbox_selectors)
        document["discovered_count"] = len(selectors)
        setup_stage = "SELECTION"
        if shard is not None:
            discovered_count = len(selectors)
            selectors = _shard_selectors(selectors, shard)
            print(
                f"E2E SHARD: {shard[0]}/{shard[1]}; "
                f"discovered={discovered_count}; selected={len(selectors)}"
            )
        if selectors_file is not None:
            discovered_count = len(selectors)
            selectors = _read_selector_file(selectors_file, selectors)
            print(
                f"E2E SELECTOR FILE: discovered={discovered_count}; selected={len(selectors)}"
            )
        document["selected_count"] = len(selectors)
        setup_stage = "PORT_ALLOCATION"
        lifecycle_ports = _allocate_lifecycle_ports(
            backend_port,
            frontend_port,
            len(selectors),
        )
        setup_stage = "PORT_PREFLIGHT"
        _preflight_lifecycle_ports(lifecycle_ports)
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        print(f"E2E FAILED: {_sanitize(str(exc))}", file=sys.stderr)
        # Only the fixed stage is evidence; process output stays on stderr.
        document["setup_failure"] = setup_stage
        return finish(1, complete=False)

    def fixture(selection: str) -> dict[str, object]:
        return {
            "garden_protocol": (selection in garden_selectors
                or selection.startswith("e2e/garden-happy-path.e2e.ts:")),
            "registry_demo": registry_selectors.get(selection),
            "recovery_demo": recovery_selectors.get(selection),
            "sandbox_demo": sandbox_selectors.get(selection),
        }

    def not_run_from(first_index: int) -> None:
        for later, (selection, ports) in enumerate(
            zip(selectors[first_index - 1 :], lifecycle_ports[first_index - 1 :], strict=True),
            start=first_index,
        ):
            lifecycles.append({
                "index": later, "selector": selection, "fixture": fixture(selection),
                "ports": {"backend": ports[0], "frontend": ports[1]},
                "result": "NOT_RUN", "exit_code": None, "elapsed_seconds": None,
                "phases": None,
            })

    suite_timeout = DISCOVERY_TIMEOUT_SECONDS + len(selectors) * (
        timeout_seconds + LIFECYCLE_OVERHEAD_SECONDS
    )
    suite_deadline = started + suite_timeout
    print(
        f"E2E TIMEOUT CONTRACT: selectors={len(selectors)}; "
        f"lifecycle_seconds={timeout_seconds:g}; suite_seconds={suite_timeout:g}; "
        f"overhead_per_lifecycle_seconds={LIFECYCLE_OVERHEAD_SECONDS:g}"
    )
    slowest_seconds = 0.0
    slowest_selection = ""
    first_failure = 0
    failed: list[tuple[int, str, str]] = []
    for index, (selection, ports) in enumerate(
        zip(selectors, lifecycle_ports, strict=True),
        start=1,
    ):
        if time.monotonic() + timeout_seconds + LIFECYCLE_OVERHEAD_SECONDS > suite_deadline:
            print(
                f"E2E FAILED [SUITE_JOB_TIMEOUT]: suite safety budget exhausted; "
                f"selection {index}/{len(selectors)} was not dispatched.", file=sys.stderr,
            )
            not_run_from(index)
            return finish(1, complete=False)
        print(f"E2E isolated lifecycle {index}/{len(selectors)}: {selection}")
        selection_started = time.monotonic()
        outcome: dict[str, object] = {}
        selected_fixture = fixture(selection)
        result = run(
            backend_port=ports[0],
            frontend_port=ports[1],
            timeout_seconds=timeout_seconds,
            headed=headed,
            grep=None,
            selection=selection,
            diagnostics=diagnostics,
            garden_protocol=bool(selected_fixture["garden_protocol"]),
            registry_demo=registry_selectors.get(selection),
            recovery_demo=recovery_selectors.get(selection),
            sandbox_demo=sandbox_selectors.get(selection),
            outcome=outcome,
        )
        elapsed = time.monotonic() - selection_started
        print(f"E2E LIFECYCLE TIMING: selection={index}/{len(selectors)}; elapsed_seconds={elapsed:.3f}")
        kind = str(outcome.get("result", "PASS" if result == 0 else "ASSERTION_FAILURE"))
        if result != 0 and kind == "PASS":
            kind = "ASSERTION_FAILURE"
        lifecycles.append({
            "index": index, "selector": selection, "fixture": selected_fixture,
            "ports": {"backend": ports[0], "frontend": ports[1]},
            "result": kind, "exit_code": result, "elapsed_seconds": round(elapsed, 3),
            "phases": outcome.get("phases"),
        })
        if elapsed > slowest_seconds:
            slowest_seconds, slowest_selection = elapsed, selection
        if result != 0:
            # Codes and durations only: which phase was running, how long each took, and
            # which deadline ended it.
            timings = "; ".join(
                f"{name}={value:.3f}" if isinstance(value, float) else f"{name}=none"
                for name, value in (outcome.get("phases") or {}).items()
            )
            print(
                f"E2E SELECTION DIAGNOSTIC: selection={index}/{len(selectors)}; result={kind}; "
                f"phase={outcome.get('phase', 'none')}; "
                f"timeout_owner={outcome.get('timeout_owner', 'none')}; {timings}"
            )
            print(
                f"E2E SUITE FAILED: isolated selection {index}/{len(selectors)} failed.",
                file=sys.stderr,
            )
            # Interruption and unproved cleanup stay fatal even for diagnostics.
            if not keep_going or result == 130 or kind == "CLEANUP_FAILURE":
                not_run_from(index + 1)
                return finish(result, complete=False)
            first_failure = first_failure or result
            failed.append((index, selection, kind))

    if failed:
        print(
            f"E2E SUITE FAILED: {len(failed)}/{len(selectors)} isolated selections failed "
            "(keep-going diagnostics; not an acceptance pass).",
            file=sys.stderr,
        )
        for index, selection, kind in failed:
            print(f"E2E FAILED SELECTION: {index}/{len(selectors)} {selection} [{kind}]",
                  file=sys.stderr)
        return finish(first_failure, complete=True)
    if time.monotonic() > suite_deadline:
        print("E2E FAILED [SUITE_JOB_TIMEOUT]: suite safety budget exceeded.", file=sys.stderr)
        return finish(1, complete=True)
    print(
        f"E2E SUITE TIMING: elapsed_seconds={time.monotonic() - started:.3f}; "
        f"slowest_seconds={slowest_seconds:.3f}; slowest_selection={slowest_selection}"
    )
    print(f"E2E SUITE PASS: {len(selectors)} configured selectors passed in isolated lifecycles.")
    return finish(0, complete=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend-port",
        default=os.environ.get("CLM_E2E_BACKEND_PORT", str(DEFAULT_BACKEND_PORT)),
        type=lambda value: _parse_port(value, "backend port"),
    )
    parser.add_argument(
        "--frontend-port",
        default=os.environ.get("CLM_E2E_FRONTEND_PORT", str(DEFAULT_FRONTEND_PORT)),
        type=lambda value: _parse_port(value, "frontend port"),
    )
    parser.add_argument("--headed", action="store_true")
    parser.add_argument(
        "--garden-protocol", action="store_true",
        help="Use strict offline synthetic ACRA protocol evidence for focused Garden tests.",
    )
    parser.add_argument(
        "--registry-demo", choices=("garden-partnership", "garden-declaration", "five-layer-hybrid", "synthetic-cache", "synthetic-seed", "synthetic-target-ambiguity", "synthetic-target-reuse"),
        help="Isolated Slice-B fixture; requires focused --grep, never normal configuration.",
    )
    parser.add_argument(
        "--recovery-demo", choices=RECOVERY_DEMO_MODES,
        help="Isolated synthetic offline Slice-C fixture; requires focused --grep.",
    )
    parser.add_argument(
        "--sandbox-demo", choices=SANDBOX_DEMO_MODES,
        help="Isolated offline XPI Sandbox protocol; requires focused --grep.",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Emit payload-free E2E upload boundary milestones.",
    )
    parser.add_argument(
        "--grep",
        help="Run only Playwright tests whose title matches this regular expression.",
    )
    parser.add_argument(
        "--timeout-seconds", type=float, default=240.0,
        help="Per-lifecycle readiness and Playwright deadline (30-900 seconds); "
        "unfiltered suite safety budget scales with discovered selectors.",
    )
    parser.add_argument(
        "--shard", type=_parse_shard,
        help=("Run INDEX/TOTAL of the discovered isolated lifecycles; "
              "CI shards cover all selectors."),
    )
    parser.add_argument(
        "--keep-going", action="store_true",
        help=("Diagnostics only: run every selected isolated lifecycle after a failure, "
              "then exit non-zero listing each failure."),
    )
    parser.add_argument(
        "--selectors-file", type=Path,
        help=("Run only the listed discovered selectors (one per line, '#' comments) "
              "in isolated lifecycles."),
    )
    parser.add_argument(
        "--results-json", type=Path,
        help="Write per-lifecycle structured results to this new file.",
    )
    args = parser.parse_args(argv)
    if args.shard is not None and args.grep:
        parser.error("--shard applies only to the unfiltered isolated suite")
    if args.grep and (args.keep_going or args.selectors_file or args.results_json):
        parser.error(
            "--keep-going, --selectors-file and --results-json apply only to isolated lifecycles"
        )
    if args.selectors_file is not None and args.shard is not None:
        parser.error("--selectors-file and --shard are mutually exclusive")
    if args.sandbox_demo and (
        not args.grep or args.garden_protocol or args.registry_demo or args.recovery_demo
    ):
        parser.error("--sandbox-demo requires --grep and a separate fixture composition")
    if args.registry_demo and (not args.grep or args.garden_protocol):
        parser.error("--registry-demo requires --grep and cannot combine with --garden-protocol")
    if args.recovery_demo and (not args.grep or args.garden_protocol or args.registry_demo):
        parser.error("--recovery-demo requires --grep and a separate fixture composition")
    if args.garden_protocol and not args.grep:
        parser.error("--garden-protocol requires a focused --grep selection")
    if not 30 <= args.timeout_seconds <= 900:
        parser.error("--timeout-seconds must be between 30 and 900")
    if args.grep:
        return run(
            backend_port=args.backend_port,
            frontend_port=args.frontend_port,
            timeout_seconds=args.timeout_seconds,
            headed=args.headed,
            grep=args.grep,
            diagnostics=args.diagnostics,
            garden_protocol=args.garden_protocol,
            registry_demo=args.registry_demo,
            recovery_demo=args.recovery_demo,
            sandbox_demo=args.sandbox_demo,
        )
    return run_isolated_suite(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        timeout_seconds=args.timeout_seconds,
        headed=args.headed,
        diagnostics=args.diagnostics,
        shard=args.shard,
        keep_going=args.keep_going,
        selectors_file=args.selectors_file,
        results_path=args.results_json,
    )


if __name__ == "__main__":
    raise SystemExit(main())
