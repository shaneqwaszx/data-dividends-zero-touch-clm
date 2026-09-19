"""Run the authenticated Playwright smoke with owned local processes."""

from __future__ import annotations

import argparse
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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "apps" / "frontend"
BACKEND_SERVER = ROOT / "scripts" / "e2e_backend_server.py"
DEFAULT_BACKEND_PORT = 8765
DEFAULT_FRONTEND_PORT = 4173
MAX_CAPTURE_CHARS = 64_000
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
    "TMP",
    "USERPROFILE",
    "WINDIR",
)


class OutputCapture:
    """Drain a child pipe while retaining only a bounded tail."""

    def __init__(self, stream: object) -> None:
        self._stream = stream
        self._chunks: deque[str] = deque()
        self._length = 0
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self) -> None:
        for line in self._stream:  # type: ignore[union-attr]
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
        kwargs: dict[str, object] = {}
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
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

    def stop(self) -> None:
        if self.process.poll() is not None:
            return
        if os.name == "nt":
            try:
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
                self.process.wait(timeout=5)
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
        else:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                if self.process.poll() is None:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)


def _parse_port(value: str, name: str) -> int:
    if not value.isascii() or not value.isdecimal():
        raise argparse.ArgumentTypeError(f"{name} must be a decimal integer")
    port = int(value)
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"{name} must be between 1024 and 65535")
    return port


def _assert_ports_available(backend_port: int, frontend_port: int) -> None:
    if backend_port == frontend_port:
        raise ValueError("Backend and frontend ports must be distinct")
    sockets: list[socket.socket] = []
    try:
        for port in (backend_port, frontend_port):
            candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets.append(candidate)
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                candidate.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            candidate.bind(("127.0.0.1", port))
    except OSError as exc:
        raise RuntimeError("An assigned E2E loopback port is already occupied") from exc
    finally:
        for candidate in sockets:
            candidate.close()


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


def run(
    *,
    backend_port: int,
    frontend_port: int,
    timeout_seconds: float,
    headed: bool = False,
) -> int:
    _assert_ports_available(backend_port, frontend_port)
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
    backend_environment = {
        **common,
        "CLM_E2E_PASSWORD": ephemeral_credential,
        "CLM_E2E_BACKEND_PORT": str(backend_port),
        "CLM_E2E_FRONTEND_ORIGIN": frontend_origin,
    }
    frontend_environment = {
        **common,
        "VITE_BACKEND_PROXY_TARGET": backend_origin,
    }
    test_environment = {
        **common,
        "CLM_E2E_PASSWORD": ephemeral_credential,
        "CLM_E2E_BACKEND_ORIGIN": backend_origin,
        # Playwright 1.56 otherwise writes an AI-oriented DOM snapshot named
        # error-context.md after failures; authenticated pages may contain KYC data.
        "PLAYWRIGHT_NO_COPY_PROMPT": "1",
        "PLAYWRIGHT_BASE_URL": frontend_origin,
    }

    processes: list[OwnedProcess] = []
    deadline = time.monotonic() + timeout_seconds
    try:
        backend = OwnedProcess(
            "backend",
            [sys.executable, str(BACKEND_SERVER)],
            cwd=ROOT,
            env=backend_environment,
        )
        processes.append(backend)
        _wait_for_http(f"{backend_origin}/health", backend, deadline, expected_text='"status":"ok"')

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
        _wait_for_http(frontend_origin, frontend, deadline, expected_text="Zero-Touch CLM")

        playwright_command = [
            node,
            str(playwright_cli),
            "test",
            "--config",
            "playwright.config.ts",
        ]
        if headed:
            playwright_command.append("--headed")
        tests = OwnedProcess(
            "playwright",
            playwright_command,
            cwd=FRONTEND_ROOT,
            env=test_environment,
        )
        processes.append(tests)
        return_code = _wait_for_test(tests, deadline)
        sanitized = _sanitize(tests.capture.text(), (ephemeral_credential,))
        if sanitized:
            print(sanitized)
        if return_code != 0:
            print("E2E FAILED: Playwright returned a non-zero status.", file=sys.stderr)
            return return_code
        print("E2E PASS: 2 authenticated local Mock smoke tests completed.")
        return 0
    except KeyboardInterrupt:
        print("E2E INTERRUPTED: stopping task-owned process groups.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, TimeoutError, ValueError) as exc:
        print(
            f"E2E FAILED: {_sanitize(str(exc), (ephemeral_credential,))}",
            file=sys.stderr,
        )
        for process in processes:
            output = _sanitize(process.capture.text(), (ephemeral_credential,))
            if output:
                print(f"[{process.name} sanitized output]\n{output}", file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            process.stop()


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
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    args = parser.parse_args(argv)
    if not 30 <= args.timeout_seconds <= 900:
        parser.error("--timeout-seconds must be between 30 and 900")
    return run(
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
        timeout_seconds=args.timeout_seconds,
        headed=args.headed,
    )


if __name__ == "__main__":
    raise SystemExit(main())
