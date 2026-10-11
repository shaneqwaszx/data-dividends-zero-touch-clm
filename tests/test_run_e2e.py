from __future__ import annotations

import importlib.util
import io
import json
import socket
import subprocess
import sys
import unittest
from collections.abc import Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, ClassVar, cast
from unittest.mock import MagicMock, call, patch

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

    def __init__(self, name: str, command: Sequence[str], *, cwd: Path, env: Mapping[str, str]) -> None:
        del cwd
        self.name = name
        self.command = list(command)
        self.env = dict(env)
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

    def _browser_policy_probe(self) -> dict[str, Any]:
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
        return cast(dict[str, Any], json.loads(completed.stdout))

    def test_browser_policy_allows_only_owned_loopback_surfaces(self) -> None:
        result = self._browser_policy_probe()
        self.assertEqual(result["frontend"]["action"], "continue")
        self.assertEqual(result["frontend"].get("classification"), "OWNED_LOOPBACK")
        self.assertEqual(result["localhostEquivalent"]["action"], "continue")
        self.assertEqual(result["backendWhenProxied"]["action"], "abort")
        self.assertEqual(result["backendWhenDirect"]["action"], "continue")

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
                self.assertEqual(result[name]["action"], "abort")

    def test_exact_baseline_font_stylesheet_is_fulfilled_locally_once(self) -> None:
        result = self._browser_policy_probe()
        self.assertEqual(result["fontExact"].get("classification"), "KNOWN_NEUTRALIZED_FONT_STYLESHEET")
        self.assertEqual(result["fontExact"]["action"], "fulfill")
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

    def test_lifecycle_port_allocation_starts_with_configured_pair(self) -> None:
        self.assertEqual(
            RUN_E2E._allocate_lifecycle_ports(8765, 4173, 3)[0],
            (8765, 4173),
        )

    def test_lifecycle_port_allocation_is_unique_and_deterministic(self) -> None:
        expected = [(8765, 4173), (8766, 4174), (8767, 4175), (8768, 4176)]
        first = RUN_E2E._allocate_lifecycle_ports(8765, 4173, 4)
        second = RUN_E2E._allocate_lifecycle_ports(8765, 4173, 4)

        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        backend_ports = [pair[0] for pair in first]
        frontend_ports = [pair[1] for pair in first]
        self.assertEqual(len(backend_ports), len(set(backend_ports)))
        self.assertEqual(len(frontend_ports), len(set(frontend_ports)))
        self.assertTrue(set(backend_ports).isdisjoint(frontend_ports))

    def test_lifecycle_port_allocation_rejects_cross_pair_collision(self) -> None:
        with self.assertRaisesRegex(ValueError, "collision"):
            RUN_E2E._allocate_lifecycle_ports(5000, 5001, 2)

    def test_lifecycle_port_allocation_rejects_bounds_and_overflow(self) -> None:
        for backend_port, frontend_port, count in (
            (1023, 4173, 1),
            (8765, 65536, 1),
            (65535, 4173, 2),
            (8765, 65535, 2),
        ):
            with self.subTest(
                backend_port=backend_port,
                frontend_port=frontend_port,
                count=count,
            ), self.assertRaisesRegex(ValueError, "1024.*65535"):
                RUN_E2E._allocate_lifecycle_ports(
                    backend_port,
                    frontend_port,
                    count,
                )

    def test_lifecycle_port_allocation_rejects_malformed_base_values(self) -> None:
        for backend_port, frontend_port in (
            ("8765", 4173),
            (8765, "4173"),
            (8765.0, 4173),
            (8765, True),
        ):
            with self.subTest(
                backend_port=backend_port,
                frontend_port=frontend_port,
            ), self.assertRaisesRegex(ValueError, "1024.*65535"):
                RUN_E2E._allocate_lifecycle_ports(
                    backend_port,
                    frontend_port,
                    1,
                )

    def test_lifecycle_port_allocation_rejects_invalid_selection_count(self) -> None:
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaisesRegex(
                ValueError, "selection count"
            ):
                RUN_E2E._allocate_lifecycle_ports(8765, 4173, count)

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
        for value in ("-1", "0", "1023", "65536", "1e3", " 8000", "port"):
            with self.subTest(value=value), self.assertRaises(
                RUN_E2E.argparse.ArgumentTypeError
            ):
                RUN_E2E._parse_port(value, "test port")

    def test_classification_database_cleanup_survives_startup_and_assertion_failures(self) -> None:
        for startup_failure in (True, False):
            with self.subTest(startup_failure=startup_failure):
                _FakeOwnedProcess.instances.clear()
                def cleanup(database, port):
                    self.assertEqual(database, "clm_p16_" + "a" * 24)
                    self.assertEqual(port, 27149)
                    self.assertTrue(all(p.stopped for p in _FakeOwnedProcess.instances))
                with (
                    patch.dict(RUN_E2E.os.environ, {"CLM_E2E_SYNTHETIC_MONGO_PORT": "27149"}),
                    patch.object(RUN_E2E.Path, "is_file", return_value=True),
                    patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
                    patch.object(RUN_E2E, "_find_node", return_value="node"),
                    patch.object(RUN_E2E, "_assert_ports_available"),
                    patch.object(RUN_E2E, "_wait_for_http", side_effect=TimeoutError("timeout") if startup_failure else None),
                    patch.object(RUN_E2E, "_wait_for_test", return_value=1),
                    patch.object(RUN_E2E.secrets, "token_hex", return_value="a" * 24),
                    patch.object(RUN_E2E, "_cleanup_classification_database", side_effect=cleanup) as cleaned,
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
                ):
                    result = RUN_E2E.run(backend_port=8765, frontend_port=4173,
                        timeout_seconds=60, sandbox_demo="database-alpha", grep="Alpha")
                self.assertEqual(result, 1)
                cleaned.assert_called_once_with("clm_p16_" + "a" * 24, 27149)
                self.assertEqual(_FakeOwnedProcess.instances[0].env["CLM_E2E_CLASSIFICATION_DATABASE"], "clm_p16_" + "a" * 24)

    def test_every_physical_fixture_cleanup_uses_its_configured_port(self) -> None:
        modes = [(None, mode) for mode in RUN_E2E.SANDBOX_DEMO_MODES
                 if mode.startswith("sponsor-")]
        modes += [(None, mode) for mode in (
            "database-alpha", "database-partnership", "database-government",
        )]
        modes.append(("synthetic-seed", None))
        for registry, sandbox in modes:
            for outcome in ("startup_failure", "assertion_failure", "success"):
                with self.subTest(registry=registry, sandbox=sandbox, outcome=outcome):
                    _FakeOwnedProcess.instances.clear()
                    with (
                        patch.dict(RUN_E2E.os.environ, {"CLM_E2E_SYNTHETIC_MONGO_PORT": "27419"}),
                        patch.object(RUN_E2E.Path, "is_file", return_value=True),
                        patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
                        patch.object(RUN_E2E, "_find_node", return_value="node"),
                        patch.object(RUN_E2E, "_assert_ports_available"),
                        patch.object(RUN_E2E, "_wait_for_http",
                                     side_effect=TimeoutError("timeout")
                                     if outcome == "startup_failure" else None),
                        patch.object(RUN_E2E, "_wait_for_test",
                                     return_value=int(outcome == "assertion_failure")),
                        patch.object(RUN_E2E.secrets, "token_hex", return_value="a" * 24),
                        patch.object(RUN_E2E, "_cleanup_classification_database") as cleaned,
                        redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
                    ):
                        result = RUN_E2E.run(
                            backend_port=8765, frontend_port=4173, timeout_seconds=60,
                            registry_demo=registry, sandbox_demo=sandbox, grep="focused",
                        )
                    prefix = "uat" if sandbox and sandbox.startswith("sponsor-") else "p16"
                    cleaned.assert_called_once_with(f"clm_{prefix}_" + "a" * 24, 27419)
                    self.assertEqual(result, int(outcome != "success"))
                    self.assertTrue(all(p.stopped for p in _FakeOwnedProcess.instances))

    def test_synthetic_seed_cleanup_uses_reserved_port_after_startup_failure(self) -> None:
        _FakeOwnedProcess.instances.clear()
        with (
            patch.dict(RUN_E2E.os.environ, {"CLM_E2E_SYNTHETIC_MONGO_PORT": "27149"}),
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http", side_effect=TimeoutError("timeout")),
            patch.object(RUN_E2E.secrets, "token_hex", return_value="a" * 24),
            patch.object(RUN_E2E, "_cleanup_classification_database") as cleaned,
            redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run(backend_port=8765, frontend_port=4173,
                                timeout_seconds=60, registry_demo="synthetic-seed", grep="Synthetic company pack")
        self.assertEqual(result, 1)
        cleaned.assert_called_once_with("clm_p16_" + "a" * 24, 27149)
        self.assertTrue(all(p.stopped for p in _FakeOwnedProcess.instances))
        self.assertEqual(_FakeOwnedProcess.instances[0].env["CLM_E2E_SYNTHETIC_MONGO_PORT"], "27149")

    def test_classification_database_cleanup_failure_is_safe_and_fails_the_run(self) -> None:
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            patch.object(RUN_E2E, "_cleanup_classification_database", side_effect=RuntimeError("private-driver-sentinel")),
            redirect_stdout(output), redirect_stderr(output),
        ):
            result = RUN_E2E.run(backend_port=8765, frontend_port=4173,
                timeout_seconds=60, sandbox_demo="database-alpha", grep="Alpha")
        self.assertEqual(result, 1)
        self.assertIn("CLEANUP_FAILURE", output.getvalue())
        self.assertNotIn("private-driver-sentinel", output.getvalue())
        self.assertNotIn("E2E PASS", output.getvalue())

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
        self.assertIn("ASSERTION_FAILURE", rendered)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("user:pass", rendered)
        self.assertEqual(len(_FakeOwnedProcess.instances), 3)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))

    def test_readiness_failure_stops_only_started_processes(self) -> None:
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http", side_effect=TimeoutError("timeout")),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        self.assertEqual(result, 1)
        self.assertEqual(len(_FakeOwnedProcess.instances), 1)
        self.assertTrue(_FakeOwnedProcess.instances[0].stopped)
        self.assertIn("READINESS_FAILURE", output.getvalue())

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
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
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
        backend, frontend, playwright = _FakeOwnedProcess.instances
        self.assertEqual(backend.env["CLM_E2E_BACKEND_PORT"], "8765")
        self.assertEqual(
            backend.env["CLM_E2E_FRONTEND_ORIGIN"],
            "http://127.0.0.1:4173",
        )
        self.assertEqual(
            frontend.env["VITE_BACKEND_PROXY_TARGET"],
            "http://127.0.0.1:8765",
        )
        self.assertEqual(
            playwright.env["CLM_E2E_BACKEND_ORIGIN"],
            "http://127.0.0.1:8765",
        )
        self.assertEqual(
            playwright.env["PLAYWRIGHT_BASE_URL"],
            "http://127.0.0.1:4173",
        )
        self.assertNotIn("CLM_E2E_DIAGNOSTICS", backend.env)
        self.assertNotIn("CLM_E2E_DIAGNOSTICS", frontend.env)
        self.assertNotIn("VITE_E2E_DIAGNOSTICS", frontend.env)
        self.assertNotIn("CLM_E2E_DIAGNOSTICS", playwright.env)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))
        self.assertEqual(
            _FakeOwnedProcess.events,
            ["stop:playwright", "stop:frontend", "stop:backend"],
        )

    def test_diagnostics_are_explicit_and_emit_only_safe_milestone_lines(self) -> None:
        _FakeOwnedProcess.output = (
            'E2E_DIAG {"milestone":"SAFE","case_id":"opaque"}\n'
        )
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            redirect_stdout(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
                diagnostics=True,
            )

        self.assertEqual(result, 0)
        backend, frontend, playwright = _FakeOwnedProcess.instances
        self.assertEqual(backend.env["CLM_E2E_DIAGNOSTICS"], "1")
        self.assertEqual(frontend.env["CLM_E2E_DIAGNOSTICS"], "1")
        self.assertEqual(frontend.env["VITE_E2E_DIAGNOSTICS"], "1")
        self.assertEqual(playwright.env["CLM_E2E_DIAGNOSTICS"], "1")
        rendered = output.getvalue()
        self.assertIn('E2E_DIAG {"milestone":"SAFE","case_id":"opaque"}', rendered)

    def test_old_port_non_bindability_after_cleanup_does_not_fail_lifecycle(self) -> None:
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(
                RUN_E2E,
                "_assert_ports_available",
                side_effect=[None, RuntimeError("old tuple remains non-bindable")],
            ) as port_probe,
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )

        self.assertEqual(result, 0)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))
        self.assertEqual(port_probe.call_count, 1)

    def test_process_stop_failure_is_reported_and_fails_closed(self) -> None:
        class StopFailingProcess(_FakeOwnedProcess):
            def stop(self) -> None:
                super().stop()
                if self.name == "frontend":
                    raise RuntimeError("task-owned frontend process still running")

        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", StopFailingProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )

        self.assertEqual(result, 1)
        self.assertEqual(
            StopFailingProcess.events,
            ["stop:playwright", "stop:frontend", "stop:backend"],
        )
        self.assertIn("CLEANUP_FAILURE", output.getvalue())
        self.assertIn("task-owned frontend process still running", output.getvalue())

    def test_occupied_later_lifecycle_port_fails_before_startup(self) -> None:
        output = io.StringIO()
        with (
            patch.object(
                RUN_E2E,
                "_assert_ports_available",
                side_effect=RuntimeError("occupied"),
            ),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8766,
                frontend_port=4174,
                timeout_seconds=60,
            )

        self.assertEqual(result, 1)
        self.assertEqual(_FakeOwnedProcess.instances, [])
        self.assertIn("occupied", output.getvalue())

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
        self.assertEqual(
            [
                (call.kwargs["backend_port"], call.kwargs["frontend_port"])
                for call in run.call_args_list
            ],
            [(8765, 4173), (8766, 4174)],
        )
        self.assertTrue(all(call.kwargs["grep"] is None for call in run.call_args_list))

    def test_posix_stop_signals_only_owned_group_and_proves_exit(self) -> None:
        owned = RUN_E2E.OwnedProcess.__new__(RUN_E2E.OwnedProcess)
        owned.name = "backend"
        owned.process_group_id = 54321
        owned.process = MagicMock()
        owned.process.poll.return_value = 0
        owned.process.wait.return_value = 0

        with (
            patch.object(RUN_E2E.os, "name", "posix"),
            patch.object(RUN_E2E.os, "killpg", create=True) as kill_group,
            patch.object(RUN_E2E.signal, "SIGKILL", 9, create=True),
            patch.object(
                RUN_E2E,
                "_wait_for_posix_process_group_exit",
                return_value=None,
            ) as wait_group,
        ):
            owned.stop()

        kill_group.assert_called_once_with(54321, RUN_E2E.signal.SIGTERM)
        wait_group.assert_called_once()
        self.assertEqual(wait_group.call_args.args[0], 54321)
        self.assertNotIn(call(54321, 9), kill_group.call_args_list)

    def test_posix_surviving_owned_group_fails_cleanup_after_term_and_kill(self) -> None:
        owned = RUN_E2E.OwnedProcess.__new__(RUN_E2E.OwnedProcess)
        owned.name = "backend"
        owned.process_group_id = 54321
        owned.process = MagicMock()
        owned.process.poll.return_value = None
        owned.process.wait.side_effect = subprocess.TimeoutExpired("backend", 5)

        with (
            patch.object(RUN_E2E.os, "name", "posix"),
            patch.object(RUN_E2E.os, "killpg", create=True) as kill_group,
            patch.object(RUN_E2E.signal, "SIGKILL", 9, create=True),
            patch.object(
                RUN_E2E,
                "_wait_for_posix_process_group_exit",
                side_effect=[TimeoutError("still alive"), TimeoutError("still alive")],
            ),
            self.assertRaisesRegex(RuntimeError, "process group did not terminate"),
        ):
            owned.stop()

        self.assertEqual(
            kill_group.call_args_list,
            [
                call(54321, RUN_E2E.signal.SIGTERM),
                call(54321, 9),
            ],
        )

    def test_windows_stop_targets_only_owned_process_tree(self) -> None:
        owned = RUN_E2E.OwnedProcess.__new__(RUN_E2E.OwnedProcess)
        owned.name = "frontend"
        owned.process_group_id = None
        owned.process = MagicMock()
        owned.process.pid = 54321
        owned.process.poll.side_effect = [None, None, 0]
        owned.process.wait.side_effect = [subprocess.TimeoutExpired("frontend", 5), 0]

        with (
            patch.object(RUN_E2E.os, "name", "nt"),
            patch.object(RUN_E2E.subprocess, "run") as run_command,
        ):
            owned.stop()

        run_command.assert_called_once()
        self.assertEqual(
            run_command.call_args.args[0],
            ["taskkill", "/PID", "54321", "/T", "/F"],
        )

    def test_successful_selectors_keep_their_lifecycle_budget_past_240_seconds(self) -> None:
        selectors = [f"e2e/valid.e2e.ts:{index}" for index in range(1, 27)]
        clock = [0.0]

        def complete_selector(**kwargs: object) -> int:
            clock[0] += 10.0
            return 0

        with (
            patch.object(RUN_E2E, "_list_test_selectors", return_value=selectors),
            patch.object(RUN_E2E, "_allocate_lifecycle_ports", return_value=[(8765, 4173)] * 26),
            patch.object(RUN_E2E.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(RUN_E2E, "run", side_effect=complete_selector) as run,
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=8765, frontend_port=4173,
                timeout_seconds=240, headed=False,
            )

        self.assertEqual(result, 0)
        self.assertEqual([c.kwargs["selection"] for c in run.call_args_list], selectors)
        self.assertEqual([c.kwargs["timeout_seconds"] for c in run.call_args_list], [240] * 26)
        self.assertEqual(clock[0], 260)

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
        output = io.StringIO()
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", side_effect=TimeoutError("timeout")),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run(
                backend_port=8765,
                frontend_port=4173,
                timeout_seconds=60,
            )
        self.assertEqual(result, 1)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))
        self.assertIn("INDIVIDUAL_SELECTION_TIMEOUT", output.getvalue())

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

    def test_discovery_routes_tagged_garden_without_changing_golden_composition(self) -> None:
        payload = {"suites": [{"specs": [
            {"ok": True, "file": "zero-touch-exception.e2e.ts", "line": 122, "tags": []},
            {"ok": True, "file": "zero-touch-exception.e2e.ts", "line": 145, "tags": ["garden-protocol"]},
            {"ok": True, "file": "zero-touch-exception.e2e.ts", "line": 145, "tags": ["garden-protocol"]},
        ]}]}
        def discovery(port: int, *, garden_selectors: set[str], registry_selectors: dict[str, str] | None = None, recovery_selectors: dict[str, str] | None = None, sandbox_selectors: dict[str, str] | None = None) -> list[str]:
            return cast(list[str], RUN_E2E._selectors_from_listing(payload, garden_selectors=garden_selectors))
        with (
            patch.object(RUN_E2E, "_list_test_selectors", side_effect=discovery),
            patch.object(RUN_E2E, "run", return_value=0) as run,
            redirect_stdout(io.StringIO()),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=8765, frontend_port=4173, timeout_seconds=240, headed=False,
            )
        self.assertEqual(result, 0)
        self.assertEqual([item.kwargs["garden_protocol"] for item in run.call_args_list], [False, True])
        self.assertEqual([item.kwargs["selection"] for item in run.call_args_list], [
            "e2e/zero-touch-exception.e2e.ts:122", "e2e/zero-touch-exception.e2e.ts:145",
        ])

    def test_discovery_rejects_mixed_fixture_composition_at_same_selector(self) -> None:
        payload = {"suites": [{"specs": [
            {"ok": True, "file": "zero-touch-exception.e2e.ts", "line": 145, "tags": []},
            {"ok": True, "file": "zero-touch-exception.e2e.ts", "line": 145, "tags": ["garden-protocol"]},
        ]}]}
        with self.assertRaisesRegex(RuntimeError, "conflicting fixture"):
            RUN_E2E._selectors_from_listing(payload, garden_selectors=set())

    def test_recovery_mode_is_explicit_and_only_exposes_offline_frontend_label(self) -> None:
        with (
            patch.object(RUN_E2E.Path, "is_file", return_value=True),
            patch.object(RUN_E2E, "OwnedProcess", _FakeOwnedProcess),
            patch.object(RUN_E2E, "_find_node", return_value="node"),
            patch.object(RUN_E2E, "_assert_ports_available"),
            patch.object(RUN_E2E, "_wait_for_http"),
            patch.object(RUN_E2E, "_wait_for_test", return_value=0),
            redirect_stdout(io.StringIO()),
        ):
            result = RUN_E2E.run(backend_port=8765, frontend_port=4173,
                                timeout_seconds=60, grep="Slice C optional Amend",
                                recovery_demo="optional-amend")
        self.assertEqual(result, 0)
        backend, frontend, playwright = _FakeOwnedProcess.instances
        self.assertEqual(backend.env["CLM_E2E_RECOVERY_DEMO"], "optional-amend")
        self.assertEqual(frontend.env["VITE_E2E_RECOVERY_DEMO"], "optional-amend")
        self.assertNotIn("CLM_E2E_RECOVERY_DEMO", playwright.env)
        self.assertNotIn("CLM_E2E_REGISTRY_DEMO", backend.env)
        self.assertNotIn("GOLDTIER_SANDBOX_USER_ID", frontend.env)
        self.assertTrue(all(process.stopped for process in _FakeOwnedProcess.instances))


    def test_derived_suite_safety_overrun_fails_without_claiming_omitted_tests_pass(self) -> None:
        clock = [0.0]
        output = io.StringIO()

        def exceed_safety_budget(**kwargs: object) -> int:
            clock[0] = 5000.0
            return 0

        with (
            patch.object(RUN_E2E, "_list_test_selectors", return_value=["e2e/a.e2e.ts:1", "e2e/b.e2e.ts:2"]),
            patch.object(RUN_E2E, "_allocate_lifecycle_ports", return_value=[(8765, 4173)] * 2),
            patch.object(RUN_E2E.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(RUN_E2E, "run", side_effect=exceed_safety_budget) as run,
            redirect_stdout(output), redirect_stderr(output),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=8765, frontend_port=4173, timeout_seconds=60, headed=False,
            )
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)
        self.assertIn("SUITE_JOB_TIMEOUT", output.getvalue())
        self.assertIn("2/2 was not dispatched", output.getvalue())
        self.assertNotIn("E2E SUITE PASS", output.getvalue())

    def test_hung_browser_reaches_its_individual_deadline(self) -> None:
        process = MagicMock()
        process.process.poll.return_value = None
        with (
            patch.object(RUN_E2E.time, "monotonic", side_effect=[0.0, 61.0]),
            patch.object(RUN_E2E.time, "sleep"),
            self.assertRaisesRegex(TimeoutError, "Playwright test execution timed out"),
        ):
            RUN_E2E._wait_for_test(process, deadline=60.0)

    def test_shard_arguments_and_empty_assignments_fail_closed(self) -> None:
        self.assertEqual(RUN_E2E._parse_shard("2/3"), (2, 3))
        for value in ("0/2", "3/2", "1/0", "1", "-1/2", "1/2/3"):
            with self.subTest(value=value), self.assertRaises(RUN_E2E.argparse.ArgumentTypeError):
                RUN_E2E._parse_shard(value)
        for shard in ((0, 2), (3, 2), (1, 4)):
            with self.subTest(shard=shard), self.assertRaises(ValueError):
                RUN_E2E._shard_selectors(["a:1", "b:2", "c:3"], shard)
        selectors = ["a:1", "b:2", "c:3"]
        self.assertIs(RUN_E2E._shard_selectors(selectors, None), selectors)

    def test_shard_preserves_fixture_dispatch_and_failure_stops_selected_calls(self) -> None:
        def discover(*args: object, **kwargs: object) -> list[str]:
            kwargs["garden_selectors"].add("garden:2")
            return ["default:1", "garden:2", "default:3", "default:4"]
        with (
            patch.object(RUN_E2E, "_list_test_selectors", side_effect=discover),
            patch.object(RUN_E2E, "run", return_value=1) as run,
            redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=RUN_E2E.DEFAULT_BACKEND_PORT,
                frontend_port=RUN_E2E.DEFAULT_FRONTEND_PORT,
                timeout_seconds=60, headed=False, shard=(2, 2),
            )
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs["selection"], "garden:2")
        self.assertTrue(run.call_args.kwargs["garden_protocol"])
        self.assertEqual(run.call_args.kwargs["timeout_seconds"], 60)

    def test_focused_grep_cannot_silently_bypass_a_shard(self) -> None:
        with (
            self.assertRaises(SystemExit) as raised,
            patch.object(RUN_E2E, "run") as run,
            redirect_stderr(io.StringIO()),
        ):
            RUN_E2E.main(["--shard", "1/2", "--grep", "case"])
        self.assertEqual(raised.exception.code, 2)
        run.assert_not_called()

    def test_ci_outer_bound_covers_current_discovery_and_bounded_cleanup(self) -> None:
        lifecycle_seconds = 60
        installation_minutes = 14
        job_minutes = 234
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        e2e = workflow.split("  e2e-shards:\n", 1)[1].split("  e2e:\n", 1)[0]
        self.assertIn(f"timeout-minutes: {job_minutes}", e2e)
        self.assertIn(f"python scripts/run_e2e.py --timeout-seconds {lifecycle_seconds}", e2e)
        selectors = RUN_E2E._list_test_selectors(RUN_E2E.DEFAULT_FRONTEND_PORT)
        self.assertEqual(len(selectors), 91)
        self.assertIn("shard: [1, 2]", e2e)
        self.assertIn("fail-fast: false", e2e)
        self.assertIn("--shard ${{ matrix.shard }}/2", e2e)
        shards = [RUN_E2E._shard_selectors(selectors, (index, 2)) for index in (1, 2)]
        self.assertEqual(sorted(shards[0] + shards[1]), sorted(selectors))
        self.assertFalse(set(shards[0]) & set(shards[1]))
        self.assertEqual(RUN_E2E.DISCOVERY_TIMEOUT_SECONDS, 60)
        self.assertEqual(RUN_E2E.LIFECYCLE_OVERHEAD_SECONDS, 120)
        launcher_seconds = RUN_E2E.DISCOVERY_TIMEOUT_SECONDS + max(map(len, shards)) * (
            lifecycle_seconds + RUN_E2E.LIFECYCLE_OVERHEAD_SECONDS
        )
        self.assertEqual(launcher_seconds, 8340)
        self.assertLessEqual(
            launcher_seconds + installation_minutes * 60,
            job_minutes * 60,
        )
        aggregate = workflow.split("  e2e:\n", 1)[1].split("  demo-lifecycle-windows:", 1)[0]
        self.assertIn("needs: e2e-shards", aggregate)
        self.assertIn("if: ${{ always() }}", aggregate)
        self.assertIn('test "${{ needs[\'e2e-shards\'].result }}" = "success"', aggregate)

        clock = [0.0]
        output = io.StringIO()

        def discover(*args: object, **kwargs: object) -> list[str]:
            clock[0] += RUN_E2E.DISCOVERY_TIMEOUT_SECONDS
            return selectors

        def complete_selector(**kwargs: object) -> int:
            clock[0] += lifecycle_seconds + RUN_E2E.LIFECYCLE_OVERHEAD_SECONDS
            return 0

        with (
            patch.object(RUN_E2E, "_list_test_selectors", side_effect=discover),
            patch.object(RUN_E2E.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(RUN_E2E, "run", side_effect=complete_selector) as run,
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            result = RUN_E2E.run_isolated_suite(
                backend_port=RUN_E2E.DEFAULT_BACKEND_PORT,
                frontend_port=RUN_E2E.DEFAULT_FRONTEND_PORT,
                timeout_seconds=lifecycle_seconds,
                headed=False,
                shard=(1, 2),
            )

        self.assertEqual(result, 0)
        self.assertEqual([item.kwargs["selection"] for item in run.call_args_list], shards[0])
        self.assertEqual(
            [item.kwargs["timeout_seconds"] for item in run.call_args_list],
            [lifecycle_seconds] * len(shards[0]),
        )
        self.assertEqual(clock[0], launcher_seconds)
        self.assertIn("E2E SUITE PASS: 46 configured selectors", output.getvalue())

    def test_sandbox_discovery_routes_each_mode_and_preserves_default(self) -> None:
        payload = {"suites": [{"specs": [
            {"ok": True, "file": "default.e2e.ts", "line": 1, "tags": []},
            *[{"ok": True, "file": "sandbox.e2e.ts", "line": index + 2,
               "tags": ["s3-sandbox-" + mode]}
              for index, mode in enumerate(RUN_E2E.SANDBOX_DEMO_MODES)],
        ]}]}
        modes: dict[str, str] = {}
        selectors = RUN_E2E._selectors_from_listing(payload, sandbox_selectors=modes)
        self.assertEqual(len(selectors), 1 + len(RUN_E2E.SANDBOX_DEMO_MODES))
        self.assertNotIn("e2e/default.e2e.ts:1", modes)
        self.assertEqual(set(modes.values()), set(RUN_E2E.SANDBOX_DEMO_MODES))
        for tags in (["s3-sandbox-unknown"], ["s3-sandbox-success", "garden-protocol"],
                     ["s3-sandbox-success", "s3-sandbox-failed-policy"]):
            payload["suites"][0]["specs"][0]["tags"] = tags
            with self.subTest(tags=tags), self.assertRaises(RuntimeError):
                RUN_E2E._selectors_from_listing(payload, sandbox_selectors={})

    def test_sandbox_mode_requires_focused_separate_composition(self) -> None:
        for arguments in ({}, {"grep": "S3", "garden_protocol": True},
                          {"grep": "S3", "registry_demo": "incomplete"}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                RUN_E2E.run(backend_port=8765, frontend_port=4173,
                            timeout_seconds=60, sandbox_demo="success", **arguments)


if __name__ == "__main__":
    unittest.main()
