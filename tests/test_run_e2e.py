from __future__ import annotations

import importlib.util
import io
import json
import socket
import subprocess
import sys
import threading
import unittest
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_e2e.py"
SPEC = importlib.util.spec_from_file_location("run_e2e_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load run_e2e")
RUN_E2E = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUN_E2E
SPEC.loader.exec_module(RUN_E2E)


class _FakePopen:
    pid = 54321

    def poll(self) -> int | None:
        return None


class _FakeCapture:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text


class _FakeOwnedProcess:
    instances: ClassVar[list[_FakeOwnedProcess]] = []
    events: ClassVar[list[str]] = []
    output = ""

    def __init__(self, name: str, command: Sequence[str], *, cwd: Path, env: object) -> None:
        del cwd
        self.name = name
        self.command = list(command)
        self.env = dict(env)  # type: ignore[arg-type]
        self.process = _FakePopen()
        self.capture = _FakeCapture(self.output)
        self.stopped = False
        self.instances.append(self)

    def stop(self) -> None:
        self.stopped = True
        self.events.append(f"stop:{self.name}")


class RunE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        _FakeOwnedProcess.instances = []
        _FakeOwnedProcess.events = []
        _FakeOwnedProcess.output = ""

    def test_base_environment_is_an_allowlist(self) -> None:
        result = RUN_E2E._base_environment(
            {
                "PATH": "safe-path",
                "TEMP": "safe-temp",
                "MONGO_URI": "mongodb://secret",
                "GITHUB_TOKEN": "secret",
                "PHASE13_MAYA_LIM_PASSWORD_HASH": "hash",
            }
        )
        self.assertEqual(result["PATH"], "safe-path")
        self.assertEqual(result["TEMP"], "safe-temp")
        self.assertNotIn("MONGO_URI", result)
        self.assertNotIn("GITHUB_TOKEN", result)
        self.assertNotIn("PHASE13_MAYA_LIM_PASSWORD_HASH", result)

    def test_sanitizer_removes_auth_material_and_connection_strings(self) -> None:
        secret = "generated-e2e-password"
        sanitized = RUN_E2E._sanitize(
            f"assert {secret}\npassword={secret}\nmongodb://user:pass@localhost/db\n",
            (secret,),
        )
        self.assertNotIn(secret, sanitized)
        self.assertNotIn("user:pass", sanitized)
        self.assertIn("[REDACTED]", sanitized)
        self.assertIn("[REDACTED_URI]", sanitized)
        self.assertIn("\\u279c", RUN_E2E._sanitize("\u279c"))

    def _browser_policy_probe(self) -> dict[str, object]:
        script = r"""
const policyModule = await import('./apps/frontend/playwright.config.ts');
const frontend = 'http://127.0.0.1:4273';
const backend = 'http://127.0.0.1:8865';
const proxiedPolicy = policyModule.createBrowserNetworkPolicy({
  frontendOrigin: frontend,
  backendOrigin: backend,
  allowDirectBackend: false,
});
const directPolicy = policyModule.createBrowserNetworkPolicy({
  frontendOrigin: frontend,
  backendOrigin: backend,
  allowDirectBackend: true,
});
const classify = (url, policy = proxiedPolicy) =>
  policyModule.classifyBrowserRequest(url, policy, 'document');
const fontUrl = 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Lora:wght@400;600&display=swap';
const classifyAs = (url, resourceType, policy = proxiedPolicy) =>
  policyModule.classifyBrowserRequest(url, policy, resourceType);
const blockedRouteCalls = [];
const violations = [];
const blockedRoute = {
  request: () => ({
    url: () => 'https://outside.invalid/private?token=sentinel',
    resourceType: () => 'stylesheet',
  }),
  abort: async () => blockedRouteCalls.push('abort'),
  continue: async () => blockedRouteCalls.push('continue'),
  fulfill: async () => blockedRouteCalls.push('fulfill'),
};
await policyModule.handleBrowserRoute(blockedRoute, proxiedPolicy, violations);
const fontRouteCalls = [];
const fontRoute = {
  request: () => ({ url: () => fontUrl, resourceType: () => 'stylesheet' }),
  abort: async () => fontRouteCalls.push({ action: 'abort' }),
  continue: async () => fontRouteCalls.push({ action: 'continue' }),
  fulfill: async (options) => fontRouteCalls.push({ action: 'fulfill', options }),
};
await policyModule.handleBrowserRoute(fontRoute, proxiedPolicy, violations);
const config = policyModule.default;
console.log(JSON.stringify({
  frontend: classify(frontend + '/'),
  localhostEquivalent: classify('http://localhost:4273/app'),
  backendWhenProxied: classify(backend + '/health'),
  backendWhenDirect: classify(backend + '/health', directPolicy),
  wrongPort: classify('http://127.0.0.1:4999/'),
  externalHttps: classify('https://outside.invalid/'),
  privateLan: classify('http://192.168.1.10:4273/'),
  nonHttp: classify('data:text/plain,hello'),
  malformed: classify('not a url'),
  fontExact: classifyAs(fontUrl, 'stylesheet'),
  fontWrongPath: classifyAs('https://fonts.googleapis.com/css', 'stylesheet'),
  fontWrongFamily: classifyAs('https://fonts.googleapis.com/css2?family=Other', 'stylesheet'),
  fontWrongResource: classifyAs(fontUrl, 'font'),
  fontBinary: classifyAs('https://fonts.gstatic.com/s/font.woff2', 'font'),
  blockedRouteCalls,
  fontRouteCalls,
  violations,
  artifactPolicy: {
    preserveOutput: config.preserveOutput,
    screenshot: config.use.screenshot,
    trace: config.use.trace,
    video: config.use.video,
    storageState: config.use.storageState ?? null,
    recordHar: config.use.recordHar ?? null,
  },
}));
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_browser_policy_allows_only_owned_loopback_surfaces(self) -> None:
        result = self._browser_policy_probe()
        self.assertEqual(result["frontend"]["action"], "continue")  # type: ignore[index]
        self.assertEqual(result["frontend"].get("classification"), "OWNED_LOOPBACK")  # type: ignore[union-attr]
        self.assertEqual(result["localhostEquivalent"]["action"], "continue")  # type: ignore[index]
        self.assertEqual(result["backendWhenProxied"]["action"], "abort")  # type: ignore[index]
        self.assertEqual(result["backendWhenDirect"]["action"], "continue")  # type: ignore[index]

    def test_browser_policy_fails_closed_for_unowned_requests(self) -> None:
        result = self._browser_policy_probe()
        for name in (
            "wrongPort",
            "externalHttps",
            "privateLan",
            "nonHttp",
            "malformed",
            "fontWrongPath",
            "fontWrongFamily",
            "fontWrongResource",
            "fontBinary",
        ):
            with self.subTest(name=name):
                self.assertEqual(result[name]["action"], "abort")  # type: ignore[index]

    def test_exact_baseline_font_stylesheet_is_fulfilled_locally_once(self) -> None:
        result = self._browser_policy_probe()
        self.assertEqual(result["fontExact"].get("classification"), "KNOWN_NEUTRALIZED_FONT_STYLESHEET")  # type: ignore[union-attr]
        self.assertEqual(result["fontExact"]["action"], "fulfill")  # type: ignore[index]
        self.assertEqual(
            result["fontRouteCalls"],
            [
                {
                    "action": "fulfill",
                    "options": {
                        "status": 200,
                        "contentType": "text/css; charset=utf-8",
                        "body": "",
                    },
                }
            ],
        )

    def test_browser_route_aborts_once_and_records_only_safe_structure(self) -> None:
        result = self._browser_policy_probe()
        self.assertEqual(result["blockedRouteCalls"], ["abort"])
        rendered = json.dumps(result["violations"])
        self.assertIn("scheme=https", rendered)
        self.assertIn("loopback=false", rendered)
        self.assertIn("port=other", rendered)
        self.assertNotIn("outside.invalid", rendered)
        self.assertNotIn("private", rendered)
        self.assertNotIn("sentinel", rendered)
        self.assertNotIn("fonts.googleapis.com", rendered)

    def test_browser_recording_and_session_artifacts_are_disabled(self) -> None:
        result = self._browser_policy_probe()
        self.assertEqual(
            result["artifactPolicy"],
            {
                "preserveOutput": "never",
                "screenshot": "off",
                "trace": "off",
                "video": "off",
                "storageState": None,
                "recordHar": None,
            },
        )

    def test_duplicate_ports_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "distinct"):
            RUN_E2E._assert_ports_available(8123, 8123)

    def test_occupied_port_is_rejected_without_reusing_it(self) -> None:
        occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupied.bind(("127.0.0.1", 0))
        port = occupied.getsockname()[1]
        try:
            with self.assertRaisesRegex(RuntimeError, "occupied"):
                RUN_E2E._assert_ports_available(port, port + 1)
        finally:
            occupied.close()

    def test_immediately_available_ports_pass_release_wait(self) -> None:
        backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        frontend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend.bind(("127.0.0.1", 0))
        frontend.bind(("127.0.0.1", 0))
        backend_port = backend.getsockname()[1]
        frontend_port = frontend.getsockname()[1]
        backend.close()
        frontend.close()

        RUN_E2E._wait_for_ports_available(
            backend_port,
            frontend_port,
            deadline=RUN_E2E.time.monotonic() + 1,
        )

    def test_delayed_port_release_eventually_passes(self) -> None:
        occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupied.bind(("127.0.0.1", 0))
        backend_port = occupied.getsockname()[1]
        frontend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        frontend.bind(("127.0.0.1", 0))
        frontend_port = frontend.getsockname()[1]
        frontend.close()
        observed_occupied = threading.Event()
        completed = threading.Event()
        errors: list[BaseException] = []
        original_assert = RUN_E2E._assert_ports_available

        def observed_assert(first_port: int, second_port: int) -> None:
            try:
                original_assert(first_port, second_port)
            except RuntimeError:
                observed_occupied.set()
                raise

        def wait_for_release() -> None:
            try:
                RUN_E2E._wait_for_ports_available(
                    backend_port,
                    frontend_port,
                    deadline=RUN_E2E.time.monotonic() + 2,
                )
            except (RuntimeError, TimeoutError, ValueError) as exc:
                errors.append(exc)
            finally:
                completed.set()

        with patch.object(RUN_E2E, "_assert_ports_available", observed_assert):
            waiter = threading.Thread(target=wait_for_release)
            waiter.start()
            self.assertTrue(observed_occupied.wait(timeout=1))
            occupied.close()
            self.assertTrue(completed.wait(timeout=1))
            waiter.join(timeout=1)

        self.assertFalse(waiter.is_alive())
        self.assertEqual(errors, [])

    def test_never_released_ports_fail_at_bounded_deadline(self) -> None:
        occupied_error = RuntimeError("occupied")
        with (
            patch.object(
                RUN_E2E,
                "_assert_ports_available",
                side_effect=occupied_error,
            ) as probe,
            patch.object(RUN_E2E.time, "monotonic", side_effect=[10.1, 11.0]),
            patch.object(RUN_E2E.time, "sleep") as sleep,
            self.assertRaisesRegex(TimeoutError, "backend=8765.*frontend=4173"),
        ):
            RUN_E2E._wait_for_ports_available(8765, 4173, deadline=11.0)

        self.assertEqual(probe.call_count, 2)
        sleep.assert_called_once()

    def test_port_probe_closes_every_temporary_socket(self) -> None:
        created = []

        class ProbeSocket:
            def setsockopt(self, *args: object) -> None:
                del args

            def bind(self, address: object) -> None:
                del address

            def close(self) -> None:
                self.closed = True

        def create_socket(*args: object) -> ProbeSocket:
            del args
            candidate = ProbeSocket()
            candidate.closed = False
            created.append(candidate)
            return candidate

        with patch.object(RUN_E2E.socket, "socket", side_effect=create_socket):
            RUN_E2E._assert_ports_available(8765, 4173)

        self.assertEqual(len(created), 2)
        self.assertTrue(all(candidate.closed for candidate in created))

    def test_invalid_ports_are_rejected(self) -> None:
        for value in ("-1", "0", "65536", "1e3", " 8000"):
            with self.subTest(value=value), self.assertRaises(
                RUN_E2E.argparse.ArgumentTypeError
            ):
                RUN_E2E._parse_port(value, "test port")

    def test_failed_test_output_is_sanitized_and_all_processes_stop(self) -> None:
        secret = "sentinel-generated-password"
        assignment = "pass" + "word=" + secret
        credential_uri = "mongo" + "db://user:pass@127.0.0.1/db"
        _FakeOwnedProcess.output = (
            f"failed login with {secret}; {assignment}; {credential_uri}"
        )
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=1),
            patch.object(RUN_E2E.secrets, "token_urlsafe", return_value=secret),
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        rendered = output.getvalue()
        self.assertEqual(result, 1)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("user:pass", rendered)
        self.assertEqual(len(_FakeOwnedProcess.instances), 3)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))

    def test_readiness_failure_stops_only_started_processes(self) -> None:
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http", side_effect=TimeoutError("timeout")),
            redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        self.assertEqual(result, 1)
        self.assertEqual(len(_FakeOwnedProcess.instances), 1)
        self.assertTrue(_FakeOwnedProcess.instances[0].stopped)

    def test_frontend_startup_failure_stops_backend_and_frontend(self) -> None:
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(
                RUN_E2E,
                "_wait_for_http",
                side_effect=[None, RuntimeError("frontend exited")],
            ),
            redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        self.assertEqual(result, 1)
        self.assertEqual(len(_FakeOwnedProcess.instances), 2)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))

    def test_success_stops_every_process_and_supports_headed_mode(self) -> None:
        cleanup_events: list[str] = []

        def record_release(*args: object, **kwargs: object) -> None:
            del args, kwargs
            cleanup_events.extend(_FakeOwnedProcess.events)
            cleanup_events.append("ports-released")

        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            patch.object(
                RUN_E2E,
                "_wait_for_ports_available",
                side_effect=record_release,
            ),
            redirect_stdout(io.StringIO()),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
                headed=True,
            )
        self.assertEqual(result, 0)
        self.assertIn("--headed", _FakeOwnedProcess.instances[-1].command)
        self.assertEqual(
            _FakeOwnedProcess.instances[-1].env["PLAYWRIGHT_NO_COPY_PROMPT"], "1"
        )
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))
        self.assertEqual(
            cleanup_events,
            ["stop:playwright", "stop:frontend", "stop:backend", "ports-released"],
        )

    def test_cleanup_release_timeout_fails_the_lifecycle(self) -> None:
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            patch.object(
                RUN_E2E,
                "_wait_for_ports_available",
                side_effect=TimeoutError(
                    "Task-owned E2E ports did not become bindable after shutdown "
                    "(backend=8765, frontend=4173)"
                ),
            ),
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )

        self.assertEqual(result, 1)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))
        self.assertIn("backend=8765, frontend=4173", output.getvalue())

    def test_unfiltered_suite_runs_each_discovered_test_in_a_fresh_lifecycle(self) -> None:
        selectors = [
            "e2e/authenticated-zero-touch.e2e.ts:87",
            "e2e/responsive-layout.e2e.ts:177",
        ]
        with (
            patch.object(RUN_E2E, "_list_test_selectors", return_value=selectors),
            patch.object(RUN_E2E, "run", return_value=0) as run,
            redirect_stdout(io.StringIO()),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=240,
                headed=False,
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            [call.kwargs["selection"] for call in run.call_args_list],
            selectors,
        )
        self.assertTrue(all(call.kwargs["grep"] is None for call in run.call_args_list))

    def test_unfiltered_suite_stops_after_the_first_failed_isolated_test(self) -> None:
        selectors = ["e2e/one.e2e.ts:10", "e2e/two.e2e.ts:20"]
        with (
            patch.object(RUN_E2E, "_list_test_selectors", return_value=selectors),
            patch.object(RUN_E2E, "run", side_effect=[1, 0]) as run,
            redirect_stdout(io.StringIO()),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=240,
                headed=False,
            )

        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)

    def test_test_timeout_stops_every_process(self) -> None:
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", side_effect=TimeoutError("timeout")),
            redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        self.assertEqual(result, 1)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))

    def test_interruption_stops_every_process(self) -> None:
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", side_effect=KeyboardInterrupt),
            redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        self.assertEqual(result, 130)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))


if __name__ == "__main__":
    unittest.main()
