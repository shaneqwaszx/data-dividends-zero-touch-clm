"""Executed Windows lifecycle safety checks for the sponsor demo launcher."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
RUNTIME = ROOT / ".runtime"
STATE = RUNTIME / "demo-processes.json"
CREATE_NO_WINDOW = 0x08000000


@unittest.skipUnless(os.name == "nt", "Windows-only process lifecycle verification")
class DemoLifecycleWindowsTests(unittest.TestCase):
    """Use harmless exact test processes; never select processes by executable name."""

    def setUp(self) -> None:
        self.test_processes: list[subprocess.Popen[str]] = []
        self.fake_state_written = False
        self.demo_cleanup_state: dict[str, Any] | None = None
        if STATE.exists():
            result = self.run_lifecycle("stop_demo_windows.bat")
            self.assertEqual(result.returncode, 0, (result.stdout or "") + (result.stderr or ""))
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

    def run_lifecycle(self, script: str, timeout: int = 90) -> subprocess.CompletedProcess[str]:
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
        path_values = [value for key, value in environment.items() if key.casefold() == "path"]
        for key in [key for key in environment if key.casefold() == "path"]:
            del environment[key]
        if path_values:
            environment["Path"] = max(path_values, key=len)
        return environment

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

    def request(self, url: str, *, data: bytes | None = None) -> tuple[int, bytes]:
        request = urllib.request.Request(url, data=data)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def endpoint_available(self, url: str) -> bool:
        try:
            return self.request(url)[0] == 200
        except (OSError, urllib.error.URLError):
            return False

    def assert_endpoints_healthy(self) -> None:
        self.assertTrue(self.endpoint_available("http://127.0.0.1:8000/health"))
        self.assertTrue(self.endpoint_available("http://127.0.0.1:5173/"))

    def assert_endpoints_stopped(self) -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not self.endpoint_available("http://127.0.0.1:8000/health") and not self.endpoint_available(
                "http://127.0.0.1:5173/"
            ):
                return
            time.sleep(0.2)
        self.fail("Backend or frontend endpoint remained available after stop")

    def assert_port_free(self, port: int) -> None:
        with socket.socket() as probe:
            probe.settimeout(0.5)
            self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0, f"port {port} occupied")

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

    def process_identity(self, process_id: int) -> dict[str, str | int]:
        command = (
            f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId = {process_id}\";"
            "[ordered]@{pid=[int]$p.ProcessId;"
            "creation_time_utc=$p.CreationDate.ToUniversalTime().ToString('O');"
            "executable_path=[string]$p.ExecutablePath}|ConvertTo-Json -Compress"
        )
        deadline = time.monotonic() + 5
        last_result: subprocess.CompletedProcess[str] | None = None
        while time.monotonic() < deadline:
            last_result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if last_result.returncode == 0:
                return json.loads(last_result.stdout)
            time.sleep(0.1)
        self.fail(
            f"could not read identity for test-owned PID {process_id}: "
            f"{'' if last_result is None else last_result.stderr}"
        )

    def write_fake_state(self, records: list[dict[str, Any]], *, status: str = "RUNNING") -> None:
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
        python_process = self.spawn_unrelated([base_python, "-c", "import time;time.sleep(120)"])
        node_process = self.spawn_unrelated(["node.exe", "-e", "setTimeout(()=>{},120000)"])
        titled_process = self.spawn_unrelated(
            ["cmd.exe", "/d", "/c", "title Unrelated Lifecycle Safety & ping -n 120 127.0.0.1 > nul"]
        )

        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        self.assert_endpoints_healthy()
        state = self.read_state()
        self.assertEqual(state["status"], "RUNNING")
        self.assertEqual([record["role"] for record in state["processes"]], ["backend", "frontend"])
        owned_ids = {
            int(process_id)
            for record in state["processes"]
            for process_id in (record["launcher_pid"], record["listener_pid"])
            if process_id is not None
        }

        stopped = self.run_lifecycle("stop_demo_windows.bat")
        self.assertEqual(stopped.returncode, 0)
        self.assert_endpoints_stopped()
        self.assertFalse(STATE.exists())
        for process_id in owned_ids:
            self.assertFalse(self.process_alive(process_id), f"owned PID {process_id} survived")
        for process in (python_process, node_process, titled_process):
            self.assertIsNone(process.poll(), f"unrelated PID {process.pid} was terminated")

    def test_reset_restarts_and_clears_process_local_case(self) -> None:
        started = self.run_lifecycle("start_demo_windows.bat")
        self.assertEqual(started.returncode, 0)
        before_state = self.read_state()
        payload = json.dumps({"uen": "202400001A", "scenario": "STRAIGHT_THROUGH"}).encode()
        status, body = self.request("http://127.0.0.1:8000/api/demo/clm/zero-touch/cases", data=payload)
        self.assertEqual(status, 201)
        case_id = json.loads(body)["case"]["case_id"]
        self.assertEqual(self.request(f"http://127.0.0.1:8000/api/clm/zero-touch/cases/{case_id}")[0], 200)

        reset = self.run_lifecycle("reset_demo_windows.bat", timeout=120)
        self.assertEqual(reset.returncode, 0)
        after_state = self.read_state()
        self.assertNotEqual(before_state["session_id"], after_state["session_id"])
        self.assert_endpoints_healthy()
        self.assertEqual(self.request(f"http://127.0.0.1:8000/api/clm/zero-touch/cases/{case_id}")[0], 404)

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
        unrelated = self.spawn_unrelated([base_python, "-c", "import time;time.sleep(120)"])
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
        reset = self.run_lifecycle("reset_demo_windows.bat")
        self.assertNotEqual(reset.returncode, 0)
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
        self.assert_endpoints_healthy()
        original_state = self.read_state()
        self.demo_cleanup_state = original_state
        corrupt_state = dict(original_state)
        corrupt_state["processes"] = [
            record for record in original_state["processes"] if record["role"] != missing_role
        ]
        self.write_state(corrupt_state)

        returncode, output = self.run_lifecycle_captured("stop_demo_windows.bat")
        self.assertNotEqual(returncode, 0)
        self.assertIn("DEMO_RUNTIME_STATE_INCOMPLETE", output)
        self.assertIn("Runtime metadata was retained", output)
        self.assertNotIn("backend and frontend process trees are gone", output)
        self.assertEqual(self.read_state(), corrupt_state)
        self.assert_endpoints_healthy()

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
            record for record in original_state["processes"] if record["role"] != missing_role
        ]
        self.write_state(corrupt_state)

        returncode, output = self.run_lifecycle_captured("reset_demo_windows.bat", timeout=120)
        self.assertNotEqual(returncode, 0)
        self.assertIn("DEMO_RUNTIME_STATE_INCOMPLETE", output)
        self.assertIn("Reset aborted because verified stop failed. No start was attempted.", output)
        self.assertEqual(self.read_state(), corrupt_state)
        self.assertEqual(self.read_state()["session_id"], original_state["session_id"])
        self.assert_endpoints_healthy()

        self.write_state(original_state)
        stopped = self.run_lifecycle("stop_demo_windows.bat")
        self.assertEqual(stopped.returncode, 0)
        self.demo_cleanup_state = None

    def test_reset_with_missing_frontend_record_does_not_start(self) -> None:
        self.exercise_missing_role_reset("frontend")

    def test_reset_with_missing_backend_record_does_not_start(self) -> None:
        self.exercise_missing_role_reset("backend")

    def test_running_rejects_duplicate_and_unknown_roles_before_process_selection(self) -> None:
        missing_pid = 2_147_000_100
        backend = self.fake_record(
            "backend", missing_pid, "2026-08-15T00:00:00Z", str(ROOT / ".venv/Scripts/python.exe")
        )
        frontend = self.fake_record(
            "frontend", missing_pid - 1, "2026-08-15T00:00:00Z", "C:/Program Files/nodejs/node.exe"
        )
        unknown = self.fake_record(
            "unknown", missing_pid - 2, "2026-08-15T00:00:00Z", "C:/Program Files/nodejs/node.exe"
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
                returncode, output = self.run_lifecycle_captured("stop_demo_windows.bat")
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

    def test_stale_nonexistent_metadata_is_cleared_without_process_selection(self) -> None:
        missing_pid = 2_147_000_000
        self.write_fake_state(
            [
                self.fake_record("backend", missing_pid, "2026-08-15T00:00:00Z", str(ROOT / ".venv/Scripts/python.exe")),
                self.fake_record("frontend", missing_pid - 1, "2026-08-15T00:00:00Z", "C:/Program Files/nodejs/node.exe"),
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
                self.assert_endpoints_healthy()
            else:
                self.assert_endpoints_stopped()
        self.assertFalse(STATE.exists())


if __name__ == "__main__":
    unittest.main()
