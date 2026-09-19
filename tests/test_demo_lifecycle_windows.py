"""Executed Windows lifecycle safety checks for the sponsor demo launcher."""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from collections.abc import Callable
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUNTIME = ROOT / ".runtime"
STATE = RUNTIME / "demo-processes.json"
CREATE_NO_WINDOW = 0x08000000

BACKEND_ROOT = ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.access import SYNTHETIC_USER_PROFILES
from app.services.authentication import (
    credential_setting_key,
    generate_scrypt_password_hash,
)

_LIFECYCLE_CREDENTIAL = secrets.token_urlsafe(24)
_LIFECYCLE_HASH = generate_scrypt_password_hash(_LIFECYCLE_CREDENTIAL)
_LIFECYCLE_AUTH_ENV = {
    credential_setting_key(profile.user_id): _LIFECYCLE_HASH
    for profile in SYNTHETIC_USER_PROFILES
}
_LIFECYCLE_AUTH_ENV[credential_setting_key("hr-admin")] = _LIFECYCLE_HASH


@unittest.skipUnless(os.name == "nt", "Windows-only process lifecycle verification")
class DemoLifecycleCreationTimeTests(unittest.TestCase):
    """Exercise the script's creation-time comparison without starting the demo."""

    def run_creation_time_comparison(
        self, observed_expression: str, recorded_expression: str
    ) -> bool:
        script_path = str(SCRIPTS / "demo_lifecycle.ps1").replace("'", "''")
        command = (
            "$tokens = $null; $errors = $null;"
            f"$ast = [Management.Automation.Language.Parser]::ParseFile('{script_path}', [ref]$tokens, [ref]$errors);"
            "$definitions = $ast.FindAll({"
            "param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and "
            "$node.Name -in @('ConvertTo-UtcCreationInstant', 'Test-SameCreationTime')"
            "}, $true);"
            "if ($definitions.Count -lt 1 -or $errors.Count -ne 0) { exit 2 };"
            "$definitions | ForEach-Object { Invoke-Expression $_.Extent.Text };"
            f"$observed = {observed_expression};"
            f"$recorded = {recorded_expression};"
            "if (Test-SameCreationTime -Left $observed -Right $recorded) { exit 0 } else { exit 1 }"
        )
        result = subprocess.run(
            ["pwsh.exe", "-NoProfile", "-Command", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertNotEqual(result.returncode, 2, result.stdout + result.stderr)
        return result.returncode == 0

    def test_stored_utc_and_observed_utc_plus_eight_are_the_same_instant(self) -> None:
        observed = (
            "[DateTimeOffset]::Parse('2026-09-02T17:37:01.1234567+08:00', "
            "[Globalization.CultureInfo]::InvariantCulture)"
        )
        recorded = (
            '(\'{"creation_time_utc":"2026-09-02T09:37:01.1234567Z"}\' | '
            "ConvertFrom-Json).creation_time_utc"
        )
        self.assertTrue(self.run_creation_time_comparison(observed, recorded))

    def test_genuinely_different_instants_do_not_match(self) -> None:
        observed = (
            "[DateTimeOffset]::Parse('2026-09-02T17:37:03.1234567+08:00', "
            "[Globalization.CultureInfo]::InvariantCulture)"
        )
        recorded = (
            '(\'{"creation_time_utc":"2026-09-02T09:37:01.1234567Z"}\' | '
            "ConvertFrom-Json).creation_time_utc"
        )
        self.assertFalse(self.run_creation_time_comparison(observed, recorded))

    def test_invalid_and_zone_less_creation_times_fail_closed(self) -> None:
        observed = (
            "[DateTimeOffset]::Parse('2026-09-02T17:37:01.1234567+08:00', "
            "[Globalization.CultureInfo]::InvariantCulture)"
        )
        for recorded in ("'not-a-timestamp'", "'2026-09-02T09:37:01.1234567'"):
            with self.subTest(recorded=recorded):
                self.assertFalse(self.run_creation_time_comparison(observed, recorded))


@unittest.skipUnless(os.name == "nt", "Windows-only process lifecycle verification")
class DemoLifecycleWindowsTests(unittest.TestCase):
    """Use harmless exact test processes; never select processes by executable name."""

    def setUp(self) -> None:
        self.test_processes: list[subprocess.Popen[str]] = []
        self.fake_state_written = False
        self.demo_cleanup_state: dict[str, Any] | None = None
        if STATE.exists():
            result = self.run_lifecycle("stop_demo_windows.bat")
            self.assertEqual(
                result.returncode, 0, (result.stdout or "") + (result.stderr or "")
            )
        self.assert_port_free(8000)
        self.assert_port_free(5173)

    def tearDown(self) -> None:
        if self.demo_cleanup_state is not None:
            self.write_state(self.demo_cleanup_state)
            stopped = self.run_lifecycle("stop_demo_windows.bat")
            self.assertEqual(stopped.returncode, 0)
            self.demo_cleanup_state = None
        elif STATE.exists():
            stopped = self.run_lifecycle("stop_demo_windows.bat")
            if stopped.returncode != 0 and self.fake_state_written and STATE.exists():
                STATE.unlink()
        for process in reversed(self.test_processes):
            self.terminate_exact(process)

    def run_lifecycle(
        self, script: str, timeout: int = 90
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["cmd.exe", "/d", "/c", str(SCRIPTS / script)],
            cwd=ROOT,
            env=self.lifecycle_environment(),
            text=True,
            timeout=timeout,
            check=False,
        )

    def lifecycle_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        path_values = [
            value for key, value in environment.items() if key.casefold() == "path"
        ]
        for key in [key for key in environment if key.casefold() == "path"]:
            del environment[key]
        if path_values:
            environment["Path"] = max(path_values, key=len)
        environment.update(_LIFECYCLE_AUTH_ENV)
        environment.update(
            {
                "CLM_PERSISTENCE_MODE": "memory",
                "MONGO_URI": "mongodb://127.0.0.1:1",
                "MONGO_DATABASE": "clm_ordinary_tests",
            }
        )
        return environment

    def test_lifecycle_environment_overrides_ambient_durable_persistence(self) -> None:
        ambient = {
            "CLM_PERSISTENCE_MODE": "mongo",
            "MONGO_URI": "ambient-configured-value",
            "MONGO_DATABASE": "clm_poc",
        }
        with patch.dict(os.environ, ambient):
            environment = self.lifecycle_environment()

        self.assertEqual(environment["CLM_PERSISTENCE_MODE"], "memory")
        self.assertEqual(environment["MONGO_DATABASE"], "clm_ordinary_tests")
        self.assertNotEqual(environment["MONGO_URI"], ambient["MONGO_URI"])

    def run_lifecycle_captured(self, script: str, timeout: int = 90) -> tuple[int, str]:
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", str(SCRIPTS / script)],
                cwd=ROOT,
                env=self.lifecycle_environment(),
                text=True,
                timeout=timeout,
                check=False,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            output.seek(0)
            return result.returncode, output.read()

    def run_pwsh_lifecycle(
        self, action: str, timeout: int = 90
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "pwsh.exe",
                "-NoProfile",
                "-File",
                str(SCRIPTS / "demo_lifecycle.ps1"),
                "-Action",
                action,
            ],
            cwd=ROOT,
            env=self.lifecycle_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def collect_ownership_diagnostics(self) -> dict[str, Any]:
        """Return sanitized ownership predicates without exposing process command lines."""
        environment = self.lifecycle_environment()
        environment["RQG03_SCRIPT_PATH"] = str(SCRIPTS / "demo_lifecycle.ps1")
        environment["RQG03_STATE_PATH"] = str(STATE)
        environment["RQG03_ROOT"] = str(ROOT)
        command = r"""
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile(
    $env:RQG03_SCRIPT_PATH,
    [ref]$tokens,
    [ref]$errors
)
$definitions = $ast.FindAll({
    param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst]
}, $true)
if ($errors.Count -ne 0 -or $definitions.Count -lt 1) {
    throw "Lifecycle diagnostic function extraction failed."
}
$definitions | ForEach-Object { Invoke-Expression $_.Extent.Text }

$script:RepositoryRoot = [IO.Path]::GetFullPath($env:RQG03_ROOT)
$script:BackendDirectory = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot "apps\backend"))
$script:FrontendDirectory = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot "apps\frontend"))
$script:PythonPath = [IO.Path]::GetFullPath((Join-Path $script:RepositoryRoot ".venv\Scripts\python.exe"))
$script:VitePath = [IO.Path]::GetFullPath((Join-Path $script:FrontendDirectory "node_modules\vite\bin\vite.js"))
$script:BackendPort = 8000
$script:FrontendPort = 5173

function Get-DiagnosticInstant {
    param([object]$Value)
    try {
        return ConvertTo-UtcCreationInstant -Value $Value
    }
    catch {
        return $null
    }
}

$state = Get-Content -LiteralPath $env:RQG03_STATE_PATH -Raw -Encoding UTF8 | ConvertFrom-Json
$roles = @(
    foreach ($record in @($state.processes)) {
        $expected = Get-RoleExpectation -Role ([string]$record.role)
        $observed = Get-ProcessIdentity -ProcessId ([int]$record.launcher_pid)
        $listenerObserved = if ($null -ne $record.listener_pid) {
            Get-ProcessIdentity -ProcessId ([int]$record.listener_pid)
        }
        else {
            $null
        }
        $launcherCheck = Confirm-OwnedProcess -Record $record
        $listenerCheck = Confirm-OwnedListener -Record $record

        $recordedInstant = Get-DiagnosticInstant -Value $record.creation_time_utc
        $observedInstant = if ($null -ne $observed) {
            Get-DiagnosticInstant -Value $observed.creation_time_utc
        }
        else {
            $null
        }
        $listenerRecordedInstant = Get-DiagnosticInstant -Value $record.listener_creation_time_utc
        $listenerObservedInstant = if ($null -ne $listenerObserved) {
            Get-DiagnosticInstant -Value $listenerObserved.creation_time_utc
        }
        else {
            $null
        }

        $creationDelta = if ($null -ne $recordedInstant -and $null -ne $observedInstant) {
            [Math]::Abs(($observedInstant - $recordedInstant).TotalMilliseconds)
        }
        else {
            $null
        }
        $listenerCreationDelta = if (
            $null -ne $listenerRecordedInstant -and $null -ne $listenerObservedInstant
        ) {
            [Math]::Abs(($listenerObservedInstant - $listenerRecordedInstant).TotalMilliseconds)
        }
        else {
            $null
        }
        $ancestryMatch = (
            $null -ne $observed -and
            $null -ne $listenerObserved -and
            (Test-IsDescendantProcess `
                -CandidateProcessId ([int]$listenerObserved.pid) `
                -AncestorProcessId ([int]$observed.pid))
        )

        [ordered]@{
            role = [string]$record.role
            launcher_status = [string]$launcherCheck.status
            launcher_reason = [string]$launcherCheck.reason
            recorded_creation_utc = if ($null -ne $recordedInstant) { $recordedInstant.ToString("O") } else { $null }
            observed_creation_utc = if ($null -ne $observedInstant) { $observedInstant.ToString("O") } else { $null }
            creation_delta_ms = $creationDelta
            creation_time_match = (
                $null -ne $observed -and
                (Test-SameCreationTime -Left $observed.creation_time_utc -Right $record.creation_time_utc)
            )
            executable_path_match = (
                $null -ne $observed -and
                (Test-SamePath -Left $observed.executable_path -Right ([string]$record.executable_path))
            )
            command_role_markers_match = (
                $null -ne $observed -and
                (Test-IdentityRoleMarkers -Identity $observed -Expected $expected)
            )
            listener_status = [string]$listenerCheck.status
            listener_reason = [string]$listenerCheck.reason
            listener_recorded_creation_utc = if ($null -ne $listenerRecordedInstant) { $listenerRecordedInstant.ToString("O") } else { $null }
            listener_observed_creation_utc = if ($null -ne $listenerObservedInstant) { $listenerObservedInstant.ToString("O") } else { $null }
            listener_creation_delta_ms = $listenerCreationDelta
            listener_creation_time_match = (
                $null -ne $listenerObserved -and
                (Test-SameCreationTime `
                    -Left $listenerObserved.creation_time_utc `
                    -Right $record.listener_creation_time_utc)
            )
            listener_executable_path_match = (
                $null -ne $listenerObserved -and
                (Test-SamePath `
                    -Left $listenerObserved.executable_path `
                    -Right ([string]$record.listener_executable_path))
            )
            listener_role_markers_match = (
                $null -ne $listenerObserved -and
                (Test-IdentityRoleMarkers -Identity $listenerObserved -Expected $expected)
            )
            listener_ownership_match = $listenerCheck.status -eq "OWNED"
            launcher_ancestry_corroboration_match = [bool]$ancestryMatch
        }
    }
)
[ordered]@{
    powershell_version = $PSVersionTable.PSVersion.ToString()
    windows_timezone_id = [TimeZoneInfo]::Local.Id
    roles = $roles
} | ConvertTo-Json -Depth 5 -Compress
"""
        result = subprocess.run(
            ["pwsh.exe", "-NoProfile", "-Command", command],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def request(
        self, url: str, *, data: bytes | None = None, timeout: float = 3
    ) -> tuple[int, bytes]:
        opener: urllib.request.OpenerDirector | None = None
        csrf_token: str | None = None
        if "/api/" in url:
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(CookieJar())
            )
            login_request = urllib.request.Request(
                "http://127.0.0.1:8000/api/auth/login",
                data=json.dumps(
                    {"user_id": "olivia-koh", "password": _LIFECYCLE_CREDENTIAL}
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            with opener.open(login_request, timeout=timeout) as response:
                csrf_token = json.loads(response.read())["csrf_token"]

        request = urllib.request.Request(url, data=data)
        if data is not None:
            request.add_header("Content-Type", "application/json")
            request.add_header("X-CSRF-Token", csrf_token or "")
            request.add_header("Origin", "http://127.0.0.1:8000")
        try:
            open_request = opener.open if opener is not None else urllib.request.urlopen
            with open_request(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def login_through_frontend_proxy(self) -> tuple[int, dict[str, Any]]:
        request = urllib.request.Request(
            "http://127.0.0.1:5173/api/auth/login",
            data=json.dumps(
                {"user_id": "maya-lim", "password": _LIFECYCLE_CREDENTIAL}
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:5173",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def endpoint_available(self, url: str, *, timeout: float = 3) -> bool:
        try:
            return self.request(url, timeout=timeout)[0] == 200
        except (OSError, urllib.error.URLError):
            return False

    def assert_owned_endpoints_healthy_within(
        self,
        expected_state: dict[str, Any],
        *,
        timeout: float = 5.0,
        poll_interval: float = 0.1,
        endpoint_probe: Callable[[str, str], bool] | None = None,
        identity_probe: Callable[[int], dict[str, str | int] | None] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        wait: Callable[[float], None] = time.sleep,
    ) -> None:
        """Require the original owned trees while allowing bounded HTTP recovery."""

        endpoints = {
            "backend": "http://127.0.0.1:8000/health",
            "frontend": "http://127.0.0.1:5173/",
        }
        if endpoint_probe is None:
            endpoint_probe = lambda _name, url: self.endpoint_available(
                url, timeout=min(timeout, 0.5)
            )
        expected_identities: list[dict[str, str | int]] = []
        for record in expected_state["processes"]:
            expected_identities.append(
                {
                    "role": str(record["role"]),
                    "kind": "launcher",
                    "pid": int(record["launcher_pid"]),
                    "creation_time_utc": str(record["creation_time_utc"]),
                    "executable_path": str(record["executable_path"]),
                }
            )
            if record.get("listener_pid") is not None:
                expected_identities.append(
                    {
                        "role": str(record["role"]),
                        "kind": "listener",
                        "pid": int(record["listener_pid"]),
                        "creation_time_utc": str(
                            record["listener_creation_time_utc"]
                        ),
                        "executable_path": str(record["listener_executable_path"]),
                    }
                )

        attempts = 0
        last_endpoint_status = {name: False for name in endpoints}

        def observe_owned_identities() -> list[dict[str, str | int | bool | None]]:
            identity_diagnostics: list[dict[str, str | int | bool | None]] = []
            identity_changed = False
            if identity_probe is None:
                observed_by_pid = self.probe_process_identities(
                    sorted({int(item["pid"]) for item in expected_identities})
                )
            else:
                observed_by_pid = {
                    int(item["pid"]): identity_probe(int(item["pid"]))
                    for item in expected_identities
                }
            for expected in expected_identities:
                observed = observed_by_pid.get(int(expected["pid"]))
                same_identity = (
                    observed is not None
                    and int(observed["pid"]) == int(expected["pid"])
                    and str(observed["creation_time_utc"])
                    == str(expected["creation_time_utc"])
                    and os.path.normcase(str(observed["executable_path"]))
                    == os.path.normcase(str(expected["executable_path"]))
                )
                identity_changed = identity_changed or not same_identity
                identity_diagnostics.append(
                    {
                        "role": expected["role"],
                        "kind": expected["kind"],
                        "pid": expected["pid"],
                        "present": observed is not None,
                        "same_identity": same_identity,
                    }
                )
            if identity_changed:
                self.fail(
                    "Post-rejection owned process identity changed before endpoint "
                    f"recovery: {json.dumps(identity_diagnostics, sort_keys=True)}"
                )
            return identity_diagnostics

        identity_diagnostics = observe_owned_identities()
        deadline = monotonic() + timeout
        while True:
            if monotonic() > deadline:
                self.fail(
                    "Post-rejection endpoints did not recover before the monotonic "
                    f"deadline: attempts={attempts}, endpoints={last_endpoint_status}, "
                    f"identities={json.dumps(identity_diagnostics, sort_keys=True)}"
                )
            attempts += 1
            for name, url in endpoints.items():
                last_endpoint_status[name] = endpoint_probe(name, url)
                probe_completed_at = monotonic()
                identity_diagnostics = observe_owned_identities()
                if probe_completed_at > deadline:
                    self.fail(
                        "Post-rejection endpoints did not recover before the "
                        f"monotonic deadline: attempts={attempts}, "
                        f"endpoints={last_endpoint_status}, identities="
                        f"{json.dumps(identity_diagnostics, sort_keys=True)}"
                    )
            if all(last_endpoint_status.values()):
                return

            remaining = deadline - monotonic()
            if remaining <= 0:
                self.fail(
                    "Post-rejection endpoints did not recover while the original "
                    "owned process identities remained alive: "
                    f"attempts={attempts}, endpoints={last_endpoint_status}, "
                    f"identities={json.dumps(identity_diagnostics, sort_keys=True)}"
                )
            wait(min(poll_interval, remaining))

    def assert_endpoints_stopped(self) -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not self.endpoint_available(
                "http://127.0.0.1:8000/health"
            ) and not self.endpoint_available("http://127.0.0.1:5173/"):
                return
            time.sleep(0.2)
        self.fail("Backend or frontend endpoint remained available after stop")

    def assert_port_free(self, port: int) -> None:
        with socket.socket() as probe:
            probe.settimeout(0.5)
            self.assertNotEqual(
                probe.connect_ex(("127.0.0.1", port)), 0, f"port {port} occupied"
            )

    def process_alive(self, process_id: int) -> bool:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"if (Get-Process -Id {process_id} -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0

    def terminate_exact(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            check=False,
        )
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    def spawn_unrelated(self, command: list[str]) -> subprocess.Popen[str]:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.test_processes.append(process)
        time.sleep(0.2)
        self.assertIsNone(process.poll())
        return process

    def spawn_port_holder(self, port: int) -> subprocess.Popen[str]:
        base_python = str(getattr(sys, "_base_executable", sys.executable))
        code = (
            "import socket,time;"
            "s=socket.socket();"
            "s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);"
            f"s.bind(('127.0.0.1',{port}));"
            "s.listen();"
            "time.sleep(120)"
        )
        process = self.spawn_unrelated([base_python, "-c", code])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    return process
            time.sleep(0.1)
        self.fail(f"test port holder did not bind {port}")

    def read_state(self) -> dict[str, Any]:
        return json.loads(STATE.read_text(encoding="utf-8"))

    def write_state(self, state: dict[str, Any]) -> None:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state), encoding="utf-8")

    def probe_process_identity(
        self, process_id: int
    ) -> dict[str, str | int] | None:
        return self.probe_process_identities([process_id]).get(process_id)

    def probe_process_identities(
        self, process_ids: list[int]
    ) -> dict[int, dict[str, str | int]]:
        if not process_ids:
            return {}
        process_filter = " OR ".join(
            f"ProcessId = {process_id}" for process_id in process_ids
        )
        command = (
            "$items=@(Get-CimInstance Win32_Process "
            f'-Filter "{process_filter}" -ErrorAction SilentlyContinue | '
            "ForEach-Object {[ordered]@{pid=[int]$_.ProcessId;"
            "creation_time_utc=$_.CreationDate.ToUniversalTime().ToString('O');"
            "executable_path=[string]$_.ExecutablePath}});"
            "ConvertTo-Json -InputObject @($items) -Compress"
        )
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {}
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        try:
            decoded = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}
        items = decoded if isinstance(decoded, list) else [decoded]
        return {
            int(item["pid"]): item
            for item in items
            if isinstance(item, dict) and "pid" in item
        }

    def process_identity(self, process_id: int) -> dict[str, str | int]:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            identity = self.probe_process_identity(process_id)
            if identity is not None:
                return identity
            time.sleep(0.1)
        self.fail(f"could not read identity for test-owned PID {process_id}")

    def write_fake_state(
        self, records: list[dict[str, Any]], *, status: str = "RUNNING"
    ) -> None:
        self.fake_state_written = True
        self.write_state(
            {
                "schema_version": 1,
                "session_id": "00000000-0000-4000-8000-000000000099",
                "status": status,
                "created_at_utc": "2026-08-15T00:00:00Z",
                "repository_root": str(ROOT),
                "processes": records,
            }
        )

    def fake_record(
        self,
        role: str,
        process_id: int,
        creation_time: str,
        executable_path: str,
    ) -> dict[str, Any]:
        backend = role == "backend"
        directory = ROOT / "apps" / ("backend" if backend else "frontend")
        return {
            "role": role,
            "launcher_pid": process_id,
            "creation_time_utc": creation_time,
            "executable_path": executable_path,
            "expected_port": 8000 if backend else 5173,
            "working_directory_marker": str(directory),
            "command_markers": [],
            "listener_pid": None,
            "listener_creation_time_utc": None,
            "listener_executable_path": None,
        }

    def test_start_stop_health_pids_and_unrelated_processes(self) -> None:
        base_python = str(getattr(sys, "_base_executable", sys.executable))
        python_process = self.spawn_unrelated(
            [base_python, "-c", "import time;time.sleep(120)"]
        )
        node_process = self.spawn_unrelated(
            ["node.exe", "-e", "setTimeout(()=>{},120000)"]
        )
        titled_process = self.spawn_unrelated(
            [
                "cmd.exe",
                "/d",
                "/c",
                "title Unrelated Lifecycle Safety & ping -n 120 127.0.0.1 > nul",
            ]
        )

        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        state = self.read_state()
        self.assert_owned_endpoints_healthy_within(state)
        proxy_login_status, proxy_login = self.login_through_frontend_proxy()
        self.assertEqual(proxy_login_status, 200)
        self.assertEqual(proxy_login["profile"]["user_id"], "maya-lim")
        self.assertEqual(proxy_login["profile"]["display_name"], "Maya Lim")
        self.assertEqual(state["status"], "RUNNING")
        self.assertEqual(
            [record["role"] for record in state["processes"]], ["backend", "frontend"]
        )
        owned_ids = {
            int(process_id)
            for record in state["processes"]
            for process_id in (record["launcher_pid"], record["listener_pid"])
            if process_id is not None
        }

        status = self.run_pwsh_lifecycle("Status")
        diagnostic_message = ""
        if status.returncode != 0:
            diagnostics = self.collect_ownership_diagnostics()
            diagnostic_message = "\nOWNERSHIP_DIAGNOSTICS=" + json.dumps(
                diagnostics, sort_keys=True, separators=(",", ":")
            )
        self.assertEqual(
            status.returncode,
            0,
            status.stdout + status.stderr + diagnostic_message,
        )
        self.assertIn("backend:", status.stdout)
        self.assertIn("frontend:", status.stdout)
        self.assertEqual(status.stdout.count("OWNED"), 2)

        stopped = self.run_pwsh_lifecycle("Stop")
        self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
        self.assert_endpoints_stopped()
        self.assertFalse(STATE.exists())
        for process_id in owned_ids:
            self.assertFalse(
                self.process_alive(process_id), f"owned PID {process_id} survived"
            )
        for process in (python_process, node_process, titled_process):
            self.assertIsNone(
                process.poll(), f"unrelated PID {process.pid} was terminated"
            )

    def test_wrong_or_unparseable_creation_time_fails_closed_for_status_and_stop(
        self,
    ) -> None:
        expected_state = {
            "processes": [
                {
                    "role": "backend",
                    "launcher_pid": 101,
                    "creation_time_utc": "2026-09-19T00:00:00.0000000Z",
                    "executable_path": "backend-python.exe",
                    "listener_pid": 102,
                    "listener_creation_time_utc": "2026-09-19T00:00:01.0000000Z",
                    "listener_executable_path": "backend-python.exe",
                },
                {
                    "role": "frontend",
                    "launcher_pid": 201,
                    "creation_time_utc": "2026-09-19T00:00:02.0000000Z",
                    "executable_path": "node.exe",
                    "listener_pid": 201,
                    "listener_creation_time_utc": "2026-09-19T00:00:02.0000000Z",
                    "listener_executable_path": "node.exe",
                },
            ]
        }
        stable_identities = {
            101: {
                "pid": 101,
                "creation_time_utc": "2026-09-19T00:00:00.0000000Z",
                "executable_path": "backend-python.exe",
            },
            102: {
                "pid": 102,
                "creation_time_utc": "2026-09-19T00:00:01.0000000Z",
                "executable_path": "backend-python.exe",
            },
            201: {
                "pid": 201,
                "creation_time_utc": "2026-09-19T00:00:02.0000000Z",
                "executable_path": "node.exe",
            },
        }

        def exercise_probe_sequence(
            responses: dict[str, list[bool]],
            *,
            identities: dict[int, dict[str, str | int] | None] | None = None,
            probe_effect: Callable[
                [str, list[float], dict[int, dict[str, str | int] | None]], None
            ]
            | None = None,
            expect_failure: str | None = None,
        ) -> dict[str, int]:
            now = [0.0]
            calls = {name: 0 for name in responses}
            active_identities = (
                identities if identities is not None else dict(stable_identities)
            )

            def endpoint_probe(name: str, _url: str) -> bool:
                index = calls[name]
                calls[name] += 1
                if probe_effect is not None:
                    probe_effect(name, now, active_identities)
                values = responses[name]
                return values[min(index, len(values) - 1)]

            def identity_probe(process_id: int) -> dict[str, str | int] | None:
                return active_identities.get(process_id)

            def wait(seconds: float) -> None:
                now[0] += seconds

            arguments = {
                "expected_state": expected_state,
                "timeout": 0.2,
                "poll_interval": 0.1,
                "endpoint_probe": endpoint_probe,
                "identity_probe": identity_probe,
                "monotonic": lambda: now[0],
                "wait": wait,
            }
            if expect_failure is None:
                self.assert_owned_endpoints_healthy_within(**arguments)
            else:
                with self.assertRaisesRegex(AssertionError, expect_failure):
                    self.assert_owned_endpoints_healthy_within(**arguments)
            return calls

        with self.subTest(post_rejection_probe="transient_frontend"):
            calls = exercise_probe_sequence(
                {"backend": [True, True], "frontend": [False, True]}
            )
            self.assertEqual(calls, {"backend": 2, "frontend": 2})

        with self.subTest(post_rejection_probe="permanent_frontend"):
            exercise_probe_sequence(
                {"backend": [True], "frontend": [False]},
                expect_failure="endpoints did not recover",
            )

        with self.subTest(post_rejection_probe="dead_frontend"):
            dead_frontend = dict(stable_identities)
            dead_frontend[201] = None
            exercise_probe_sequence(
                {"backend": [True], "frontend": [True]},
                identities=dead_frontend,
                expect_failure="owned process identity changed",
            )

        with self.subTest(post_rejection_probe="replaced_frontend"):
            replaced_frontend = {
                **stable_identities,
                201: {
                    **stable_identities[201],
                    "creation_time_utc": "2026-09-19T00:01:02.0000000Z",
                },
            }
            exercise_probe_sequence(
                {"backend": [True], "frontend": [True]},
                identities=replaced_frontend,
                expect_failure="owned process identity changed",
            )

        with self.subTest(post_rejection_probe="frontend_replaced_during_probe"):
            def replace_frontend_during_backend_probe(
                name: str,
                _now: list[float],
                identities: dict[int, dict[str, str | int] | None],
            ) -> None:
                if name == "backend":
                    identities[201] = {
                        **stable_identities[201],
                        "creation_time_utc": "2026-09-19T00:01:02.0000000Z",
                    }

            exercise_probe_sequence(
                {"backend": [True], "frontend": [True]},
                probe_effect=replace_frontend_during_backend_probe,
                expect_failure="owned process identity changed",
            )

        with self.subTest(post_rejection_probe="health_after_deadline"):
            def advance_past_deadline(
                name: str,
                now: list[float],
                _identities: dict[int, dict[str, str | int] | None],
            ) -> None:
                if name == "frontend":
                    now[0] = 1.0

            exercise_probe_sequence(
                {"backend": [True], "frontend": [True]},
                probe_effect=advance_past_deadline,
                expect_failure="monotonic deadline",
            )

        with self.subTest(post_rejection_probe="backend_remains_checked"):
            calls = exercise_probe_sequence(
                {"backend": [False, True], "frontend": [True, True]}
            )
            self.assertEqual(calls, {"backend": 2, "frontend": 2})

        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        original_state = self.read_state()
        self.assert_owned_endpoints_healthy_within(original_state)
        self.demo_cleanup_state = original_state

        for bad_creation_time in ("1970-01-01T00:00:00.0000000Z", "not-a-timestamp"):
            with self.subTest(creation_time=bad_creation_time):
                corrupt_state = json.loads(json.dumps(original_state))
                for record in corrupt_state["processes"]:
                    record["creation_time_utc"] = bad_creation_time
                    record["listener_creation_time_utc"] = bad_creation_time
                self.write_state(corrupt_state)

                status = self.run_pwsh_lifecycle("Status")
                self.assertNotEqual(status.returncode, 0)
                self.assertEqual(status.stdout.count("MISMATCH"), 2)

                diagnostics = self.collect_ownership_diagnostics()
                serialized_diagnostics = json.dumps(diagnostics, sort_keys=True)
                self.assertNotIn("command_line", serialized_diagnostics)
                self.assertEqual(
                    {item["role"] for item in diagnostics["roles"]},
                    {"backend", "frontend"},
                )
                for item in diagnostics["roles"]:
                    self.assertFalse(item["creation_time_match"])
                    self.assertFalse(item["listener_creation_time_match"])
                    self.assertTrue(item["executable_path_match"])
                    self.assertTrue(item["command_role_markers_match"])

                stopped = self.run_pwsh_lifecycle("Stop")
                self.assertNotEqual(stopped.returncode, 0)
                self.assertIn(
                    "Launcher ownership could not be established", stopped.stdout
                )
                self.assertEqual(self.read_state(), corrupt_state)
                self.assert_owned_endpoints_healthy_within(original_state)

        self.write_state(original_state)
        stopped = self.run_lifecycle("stop_demo_windows.bat")
        self.assertEqual(stopped.returncode, 0)
        self.demo_cleanup_state = None
        self.assert_endpoints_stopped()

    def test_reset_restarts_and_clears_process_local_case(self) -> None:
        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        before_state = self.read_state()
        payload = json.dumps(
            {
                "uen": "202400001A",
                "scenario": "STRAIGHT_THROUGH",
                "team_id": "TEAM_A",
            }
        ).encode()
        status, body = self.request(
            "http://127.0.0.1:8000/api/demo/clm/zero-touch/cases", data=payload
        )
        self.assertEqual(status, 201)
        case_id = json.loads(body)["case"]["case_id"]
        self.assertEqual(
            self.request(f"http://127.0.0.1:8000/api/clm/zero-touch/cases/{case_id}")[
                0
            ],
            200,
        )

        reset = self.run_lifecycle("reset_demo_windows.bat", timeout=120)
        self.assertEqual(reset.returncode, 0)
        after_state = self.read_state()
        self.assertNotEqual(before_state["session_id"], after_state["session_id"])
        self.assert_owned_endpoints_healthy_within(after_state)
        self.assertEqual(
            self.request(f"http://127.0.0.1:8000/api/clm/zero-touch/cases/{case_id}")[
                0
            ],
            404,
        )

    def test_occupied_ports_fail_without_terminating_occupants(self) -> None:
        for port in (8000, 5173):
            with self.subTest(port=port):
                holder = self.spawn_port_holder(port)
                started = self.run_lifecycle("start_demo_windows.bat")
                self.assertNotEqual(started.returncode, 0)
                self.assertIsNone(holder.poll())
                self.assertFalse(STATE.exists())
                self.terminate_exact(holder)

    def test_reset_stops_on_ownership_mismatch_and_does_not_start(self) -> None:
        base_python = str(getattr(sys, "_base_executable", sys.executable))
        unrelated = self.spawn_unrelated(
            [base_python, "-c", "import time;time.sleep(120)"]
        )
        identity = self.process_identity(unrelated.pid)
        self.write_fake_state(
            [
                self.fake_record(
                    "backend",
                    unrelated.pid,
                    str(identity["creation_time_utc"]),
                    str(identity["executable_path"]),
                ),
                self.fake_record(
                    "frontend",
                    2_147_000_001,
                    "2026-08-15T00:00:00Z",
                    "C:/Program Files/nodejs/node.exe",
                ),
            ]
        )
        returncode, output = self.run_lifecycle_captured("reset_demo_windows.bat")
        self.assertNotEqual(returncode, 0)
        self.assertIn(
            "backend executable is outside the project virtual environment", output
        )
        self.assertIsNone(unrelated.poll())
        self.assertFalse(self.endpoint_available("http://127.0.0.1:8000/health"))
        self.assertTrue(STATE.exists())
        STATE.unlink()
        self.fake_state_written = False

    def test_reset_returns_nonzero_when_fresh_start_is_blocked(self) -> None:
        holder = self.spawn_port_holder(8000)
        reset = self.run_lifecycle("reset_demo_windows.bat")
        self.assertNotEqual(reset.returncode, 0)
        self.assertIsNone(holder.poll())
        self.assertFalse(STATE.exists())

    def exercise_missing_role_stop(self, missing_role: str) -> None:
        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        original_state = self.read_state()
        self.assert_owned_endpoints_healthy_within(original_state)
        self.demo_cleanup_state = original_state
        corrupt_state = dict(original_state)
        corrupt_state["processes"] = [
            record
            for record in original_state["processes"]
            if record["role"] != missing_role
        ]
        self.write_state(corrupt_state)

        returncode, output = self.run_lifecycle_captured("stop_demo_windows.bat")
        self.assertNotEqual(returncode, 0)
        self.assertIn("DEMO_RUNTIME_STATE_INCOMPLETE", output)
        self.assertIn("Runtime metadata was retained", output)
        self.assertNotIn("backend and frontend process trees are gone", output)
        self.assertEqual(self.read_state(), corrupt_state)
        self.assert_owned_endpoints_healthy_within(original_state)

        self.write_state(original_state)
        stopped = self.run_lifecycle("stop_demo_windows.bat")
        self.assertEqual(stopped.returncode, 0)
        self.demo_cleanup_state = None
        self.assert_endpoints_stopped()
        self.assertFalse(STATE.exists())

    def test_missing_frontend_running_record_fails_closed_before_stop(self) -> None:
        self.exercise_missing_role_stop("frontend")

    def test_missing_backend_running_record_fails_closed_before_stop(self) -> None:
        self.exercise_missing_role_stop("backend")

    def exercise_missing_role_reset(self, missing_role: str) -> None:
        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        original_state = self.read_state()
        self.demo_cleanup_state = original_state
        corrupt_state = dict(original_state)
        corrupt_state["processes"] = [
            record
            for record in original_state["processes"]
            if record["role"] != missing_role
        ]
        self.write_state(corrupt_state)

        returncode, output = self.run_lifecycle_captured(
            "reset_demo_windows.bat", timeout=120
        )
        self.assertNotEqual(returncode, 0)
        self.assertIn("DEMO_RUNTIME_STATE_INCOMPLETE", output)
        self.assertIn(
            "Reset aborted because verified stop failed. No start was attempted.",
            output,
        )
        self.assertEqual(self.read_state(), corrupt_state)
        self.assertEqual(self.read_state()["session_id"], original_state["session_id"])
        self.assert_owned_endpoints_healthy_within(original_state)

        self.write_state(original_state)
        stopped = self.run_lifecycle("stop_demo_windows.bat")
        self.assertEqual(stopped.returncode, 0)
        self.demo_cleanup_state = None

    def test_reset_with_missing_frontend_record_does_not_start(self) -> None:
        self.exercise_missing_role_reset("frontend")

    def test_reset_with_missing_backend_record_does_not_start(self) -> None:
        self.exercise_missing_role_reset("backend")

    def test_running_rejects_duplicate_and_unknown_roles_before_process_selection(
        self,
    ) -> None:
        missing_pid = 2_147_000_100
        backend = self.fake_record(
            "backend",
            missing_pid,
            "2026-08-15T00:00:00Z",
            str(ROOT / ".venv/Scripts/python.exe"),
        )
        frontend = self.fake_record(
            "frontend",
            missing_pid - 1,
            "2026-08-15T00:00:00Z",
            "C:/Program Files/nodejs/node.exe",
        )
        unknown = self.fake_record(
            "unknown",
            missing_pid - 2,
            "2026-08-15T00:00:00Z",
            "C:/Program Files/nodejs/node.exe",
        )
        invalid_sets = (
            [backend, dict(backend)],
            [frontend, dict(frontend)],
            [backend, frontend, unknown],
            [unknown],
        )
        for records in invalid_sets:
            with self.subTest(roles=[record["role"] for record in records]):
                self.write_fake_state(records)
                retained = self.read_state()
                returncode, output = self.run_lifecycle_captured(
                    "stop_demo_windows.bat"
                )
                self.assertNotEqual(returncode, 0)
                self.assertIn("DEMO_RUNTIME_STATE_INCOMPLETE", output)
                self.assertNotIn("backend and frontend process trees are gone", output)
                self.assertEqual(self.read_state(), retained)
                STATE.unlink()
                self.fake_state_written = False

    def test_starting_backend_only_is_distinct_from_running_completeness(self) -> None:
        self.write_fake_state(
            [
                self.fake_record(
                    "backend",
                    2_147_000_200,
                    "2026-08-15T00:00:00Z",
                    str(ROOT / ".venv/Scripts/python.exe"),
                )
            ],
            status="STARTING",
        )
        returncode, output = self.run_lifecycle_captured("stop_demo_windows.bat")
        self.assertEqual(returncode, 0)
        self.assertIn("Stale launcher metadata was cleared", output)
        self.assertNotIn("backend and frontend process trees are gone", output)
        self.assertFalse(STATE.exists())
        self.fake_state_written = False

    def test_stale_nonexistent_metadata_is_cleared_without_process_selection(
        self,
    ) -> None:
        missing_pid = 2_147_000_000
        self.write_fake_state(
            [
                self.fake_record(
                    "backend",
                    missing_pid,
                    "2026-08-15T00:00:00Z",
                    str(ROOT / ".venv/Scripts/python.exe"),
                ),
                self.fake_record(
                    "frontend",
                    missing_pid - 1,
                    "2026-08-15T00:00:00Z",
                    "C:/Program Files/nodejs/node.exe",
                ),
            ]
        )
        stopped = self.run_lifecycle("stop_demo_windows.bat")
        self.assertEqual(stopped.returncode, 0)
        self.assertFalse(STATE.exists())

    def test_repeated_start_stop_start_reset_stop_sequence(self) -> None:
        sequence = (
            ("start_demo_windows.bat", True),
            ("stop_demo_windows.bat", False),
            ("start_demo_windows.bat", True),
            ("reset_demo_windows.bat", True),
            ("stop_demo_windows.bat", False),
        )
        for script, expected_healthy in sequence:
            result = self.run_lifecycle(script, timeout=120)
            self.assertEqual(result.returncode, 0, script)
            if expected_healthy:
                self.assert_owned_endpoints_healthy_within(self.read_state())
            else:
                self.assert_endpoints_stopped()
        self.assertFalse(STATE.exists())


if __name__ == "__main__":
    unittest.main()
