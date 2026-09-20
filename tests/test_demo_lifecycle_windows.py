"""Executed Windows lifecycle safety checks for the sponsor demo launcher."""

from __future__ import annotations

import io
import json
import os
import re
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
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Self
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

_CREATION_TIME_PATTERN = re.compile(
    r"\A(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T"
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,7}))?"
    r"(?P<zone>[zZ]|[+-]\d{2}:\d{2})\Z"
)
_TICKS_PER_SECOND = 10_000_000
_CREATION_TIME_TOLERANCE_TICKS = 10_000


def _utc_creation_ticks(value: object) -> int | None:
    """Parse an offset-bearing ISO creation time into 100 ns UTC ticks."""

    if not isinstance(value, str):
        return None
    match = _CREATION_TIME_PATTERN.fullmatch(value)
    if match is None:
        return None
    try:
        local_time = datetime(
            int(match["year"]),
            int(match["month"]),
            int(match["day"]),
            int(match["hour"]),
            int(match["minute"]),
            int(match["second"]),
            tzinfo=timezone.utc,
        )
        zone = match["zone"]
        offset_minutes = 0
        if zone.lower() != "z":
            offset_hours = int(zone[1:3])
            offset_remainder = int(zone[4:6])
            if offset_hours > 14 or offset_remainder > 59:
                return None
            if offset_hours == 14 and offset_remainder != 0:
                return None
            offset_minutes = offset_hours * 60 + offset_remainder
            if zone[0] == "-":
                offset_minutes = -offset_minutes
        utc_time = local_time - timedelta(minutes=offset_minutes)
        fraction = match["fraction"] or ""
        fraction_ticks = int(fraction.ljust(7, "0")) if fraction else 0
        seconds = (
            utc_time.toordinal() * 86_400
            + utc_time.hour * 3_600
            + utc_time.minute * 60
            + utc_time.second
        )
        return seconds * _TICKS_PER_SECOND + fraction_ticks
    except (OverflowError, TypeError, ValueError):
        return None


def _same_process_identity(
    expected: dict[str, str | int],
    observed: dict[str, str | int] | None,
) -> bool:
    """Apply the production PID, executable, and <=1 ms creation-time contract."""

    if observed is None:
        return False
    try:
        expected_ticks = _utc_creation_ticks(expected["creation_time_utc"])
        observed_ticks = _utc_creation_ticks(observed["creation_time_utc"])
        return (
            int(observed["pid"]) == int(expected["pid"])
            and expected_ticks is not None
            and observed_ticks is not None
            and abs(observed_ticks - expected_ticks) <= _CREATION_TIME_TOLERANCE_TICKS
            and os.path.normcase(str(observed["executable_path"]))
            == os.path.normcase(str(expected["executable_path"]))
        )
    except (KeyError, TypeError, ValueError):
        return False


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

        expected_identity = {
            "pid": 201,
            "creation_time_utc": "2026-09-20T00:00:00.1230000Z",
            "executable_path": "node.exe",
        }
        equivalent_creation_times = (
            "2026-09-20T00:00:00.123000Z",
            "2026-09-20T08:00:00.1230000+08:00",
            "2026-09-20T00:00:00.1239999Z",
            "2026-09-20T00:00:00.1240000Z",
        )
        for creation_time in equivalent_creation_times:
            with self.subTest(creation_time=creation_time):
                self.assertTrue(
                    _same_process_identity(
                        expected_identity,
                        {
                            **expected_identity,
                            "creation_time_utc": creation_time,
                        },
                    )
                )

        same_pid_expected = (
            expected_identity,
            {
                **expected_identity,
                "creation_time_utc": "2026-09-20T00:00:00.123000Z",
            },
        )
        same_pid_observed = {
            **expected_identity,
            "creation_time_utc": "2026-09-20T08:00:00.1230000+08:00",
        }
        self.assertEqual(
            [
                _same_process_identity(expected, same_pid_observed)
                for expected in same_pid_expected
            ],
            [True, True],
        )

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

        expected_identity = {
            "pid": 201,
            "creation_time_utc": "2026-09-20T00:00:00.1230000Z",
            "executable_path": "node.exe",
        }
        for observed_identity in (
            {
                **expected_identity,
                "creation_time_utc": "2026-09-20T00:00:00.1240001Z",
            },
            {**expected_identity, "pid": 202},
            {**expected_identity, "executable_path": "other-node.exe"},
            None,
        ):
            with self.subTest(observed_identity=observed_identity):
                self.assertFalse(
                    _same_process_identity(expected_identity, observed_identity)
                )

        same_pid_expected = (
            expected_identity,
            {
                **expected_identity,
                "creation_time_utc": "2026-09-20T00:00:00.123000Z",
            },
        )
        for observed_identity in (
            {
                **expected_identity,
                "creation_time_utc": "2026-09-20T00:00:00.1240001Z",
            },
            {**expected_identity, "executable_path": "other-node.exe"},
            {**expected_identity, "pid": 202},
            None,
        ):
            with self.subTest(same_pid_observed_identity=observed_identity):
                self.assertEqual(
                    [
                        _same_process_identity(expected, observed_identity)
                        for expected in same_pid_expected
                    ],
                    [False, False],
                )

    def test_invalid_and_zone_less_creation_times_fail_closed(self) -> None:
        observed = (
            "[DateTimeOffset]::Parse('2026-09-02T17:37:01.1234567+08:00', "
            "[Globalization.CultureInfo]::InvariantCulture)"
        )
        for recorded in ("'not-a-timestamp'", "'2026-09-02T09:37:01.1234567'"):
            with self.subTest(recorded=recorded):
                self.assertFalse(self.run_creation_time_comparison(observed, recorded))

        expected_identity = {
            "pid": 201,
            "creation_time_utc": "2026-09-20T00:00:00.1230000Z",
            "executable_path": "node.exe",
        }
        for creation_time in (
            "2026-09-20T00:00:00.1230000",
            "not-a-timestamp",
        ):
            with self.subTest(creation_time=creation_time):
                self.assertFalse(
                    _same_process_identity(
                        expected_identity,
                        {
                            **expected_identity,
                            "creation_time_utc": creation_time,
                        },
                    )
                )


@unittest.skipUnless(os.name == "nt", "Windows-only process lifecycle verification")
class DemoLifecycleWindowsTests(unittest.TestCase):
    """Use harmless exact test processes; never select processes by executable name."""

    def setUp(self) -> None:
        self.test_processes: list[subprocess.Popen[str]] = []
        self.fake_state_written = False
        self.demo_cleanup_state: dict[str, Any] | None = None
        self.request_diagnostics: list[dict[str, Any]] = []
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

    def test_authenticated_request_records_success_then_expected_404(self) -> None:
        class FakeResponse:
            def __init__(self, body: bytes, *, status: int = 200) -> None:
                self.status = status
                self.body = body

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.body

        target_error = urllib.error.HTTPError(
            "http://must-not-appear.invalid/case-id",
            404,
            "raw-message-must-not-appear",
            {},
            io.BytesIO(b"ignored-target-body"),
        )

        class FakeOpener:
            def __init__(self) -> None:
                self.calls = 0

            def open(
                self, _request: urllib.request.Request, *, timeout: float
            ) -> FakeResponse:
                self.calls += 1
                self.timeout = timeout
                if self.calls == 1:
                    return FakeResponse(b'{"csrf_token":"must-not-appear"}')
                raise target_error

        opener = FakeOpener()
        with patch("urllib.request.build_opener", return_value=opener):
            status, body = self.request(
                "http://127.0.0.1:8000/api/clm/zero-touch/cases/case-id",
                request_context="after_reset",
            )

        self.assertEqual((status, body), (404, b"ignored-target-body"))
        self.assertEqual(opener.calls, 2)
        self.assertEqual(
            [item["operation_role"] for item in self.request_diagnostics],
            ["login", "target_request"],
        )
        self.assertEqual(self.request_diagnostics[0]["stage"], "parse_complete")
        self.assertEqual(self.request_diagnostics[1]["stage"], "body_complete")
        self.assertTrue(self.request_diagnostics[1]["target_dispatched"])
        rendered = json.dumps(self.request_diagnostics)
        for prohibited in (
            "must-not-appear",
            "case-id",
            "csrf_token",
            "cookie",
            "http://",
        ):
            self.assertNotIn(prohibited, rendered.casefold())

    def test_authenticated_request_classifies_login_failures_without_target_dispatch(
        self,
    ) -> None:
        class FakeResponse:
            status = 200

            def __init__(
                self,
                body: bytes = b'{"csrf_token":"safe-placeholder"}',
                *,
                failure: BaseException | None = None,
            ) -> None:
                self.body = body
                self.failure = failure

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                if self.failure is not None:
                    raise self.failure
                return self.body

        denied = urllib.error.HTTPError(
            "http://must-not-appear.invalid/login",
            401,
            "raw-message-must-not-appear",
            {},
            io.BytesIO(b"ignored"),
        )
        cases: tuple[
            tuple[
                str,
                FakeResponse | BaseException,
                type[BaseException],
                str,
                str,
                bool,
                bool,
                int | None,
            ],
            ...,
        ] = (
            (
                "before_headers",
                TimeoutError("raw-message-must-not-appear"),
                TimeoutError,
                "response_acquisition",
                "timeout",
                False,
                False,
                None,
            ),
            (
                "body_read",
                FakeResponse(failure=TimeoutError("raw-message-must-not-appear")),
                TimeoutError,
                "body_read",
                "timeout",
                True,
                False,
                200,
            ),
            (
                "malformed",
                FakeResponse(b"not-json"),
                json.JSONDecodeError,
                "response_parsing",
                "malformed_response",
                True,
                True,
                200,
            ),
            (
                "denied",
                denied,
                urllib.error.HTTPError,
                "response_acquisition",
                "http_denied",
                True,
                False,
                401,
            ),
        )
        for (
            name,
            effect,
            exception_type,
            stage,
            category,
            headers_received,
            body_complete,
            status,
        ) in cases:
            with self.subTest(name=name):
                calls = 0

                class FakeOpener:
                    def __init__(
                        self, open_effect: FakeResponse | BaseException
                    ) -> None:
                        self.open_effect = open_effect

                    def open(
                        self, _request: urllib.request.Request, *, timeout: float
                    ) -> FakeResponse:
                        nonlocal calls
                        calls += 1
                        if isinstance(self.open_effect, BaseException):
                            raise self.open_effect
                        return self.open_effect

                with (
                    patch(
                        "urllib.request.build_opener", return_value=FakeOpener(effect)
                    ),
                    self.assertRaises(exception_type) as raised,
                ):
                    self.request(
                        "http://127.0.0.1:8000/api/clm/zero-touch/cases/case-id",
                        request_context="after_reset",
                    )

                self.assertEqual(calls, 1)
                self.assertEqual(len(self.request_diagnostics), 1)
                diagnostic = self.request_diagnostics[0]
                self.assertEqual(diagnostic["operation_role"], "login")
                self.assertEqual(diagnostic["stage"], stage)
                self.assertEqual(diagnostic["failure_category"], category)
                self.assertEqual(diagnostic["headers_received"], headers_received)
                self.assertEqual(diagnostic["body_complete"], body_complete)
                self.assertEqual(diagnostic["http_status"], status)
                self.assertFalse(diagnostic["parse_complete"])
                self.assertFalse(diagnostic["target_dispatched"])
                self.assertEqual(diagnostic["request_context"], "after_reset")
                rendered = json.dumps(diagnostic).casefold()
                for prohibited in (
                    "raw-message-must-not-appear",
                    "case-id",
                    "safe-placeholder",
                    "cookie",
                    "http://",
                ):
                    self.assertNotIn(prohibited, rendered)
                    self.assertNotIn(
                        prohibited,
                        json.dumps(
                            getattr(raised.exception, "__notes__", [])
                        ).casefold(),
                    )
                self.assertIn(
                    "authenticated_request_diagnostic=",
                    json.dumps(getattr(raised.exception, "__notes__", [])),
                )

    def test_authenticated_request_preserves_target_failure_without_retry(self) -> None:
        class LoginResponse:
            status = 200

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"csrf_token":"must-not-appear"}'

        calls = 0

        class FakeOpener:
            def open(
                self, _request: urllib.request.Request, *, timeout: float
            ) -> LoginResponse:
                nonlocal calls
                calls += 1
                if calls == 1:
                    return LoginResponse()
                raise TimeoutError("raw-message-must-not-appear")

        with (
            patch("urllib.request.build_opener", return_value=FakeOpener()),
            self.assertRaises(TimeoutError) as raised,
        ):
            self.request(
                "http://127.0.0.1:8000/api/clm/zero-touch/cases/case-id",
                request_context="before_reset",
            )

        self.assertEqual(calls, 2)
        self.assertEqual(len(self.request_diagnostics), 2)
        target = self.request_diagnostics[1]
        self.assertEqual(target["operation_role"], "target_request")
        self.assertEqual(target["stage"], "response_acquisition")
        self.assertEqual(target["failure_category"], "timeout")
        self.assertTrue(target["target_dispatched"])
        self.assertEqual(target["request_context"], "before_reset")
        note = json.dumps(getattr(raised.exception, "__notes__", [])).casefold()
        self.assertIn("authenticated_request_diagnostic=", note)
        self.assertNotIn("raw-message-must-not-appear", note)
        self.assertNotIn("case-id", note)

    def test_endpoint_probe_classifies_sanitized_failure_stages(self) -> None:
        class FakeResponse:
            def __init__(
                self,
                *,
                status: int = 200,
                body_failure: BaseException | None = None,
            ) -> None:
                self.status = status
                self.body_failure = body_failure
                self.closed = False

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                self.closed = True

            def read(self) -> bytes:
                if self.body_failure is not None:
                    raise self.body_failure
                return b"ignored"

        def classify(
            effect: FakeResponse | BaseException,
        ) -> tuple[dict[str, Any], FakeResponse | None]:
            response = effect if isinstance(effect, FakeResponse) else None
            patcher = (
                patch("urllib.request.urlopen", return_value=effect)
                if response is not None
                else patch("urllib.request.urlopen", side_effect=effect)
            )
            ticks = iter((10.0, 10.125))
            with patcher:
                observation = self.probe_endpoint_health(
                    "frontend",
                    "http://127.0.0.1:5173/",
                    timeout=0.5,
                    monotonic=lambda: next(ticks),
                )
            return observation, response

        cases: tuple[
            tuple[str, FakeResponse | BaseException, bool, bool, int | None], ...
        ] = (
            ("healthy", FakeResponse(), True, True, 200),
            ("http_non_200", FakeResponse(status=503), True, True, 503),
            ("connection_refused", ConnectionRefusedError(), False, False, None),
            ("connection_reset", ConnectionResetError(), False, False, None),
            ("timeout", TimeoutError(), False, False, None),
            (
                "response_body_failure",
                FakeResponse(body_failure=TimeoutError()),
                True,
                False,
                200,
            ),
            ("verifier_exception", RuntimeError("must-not-leak"), False, False, None),
        )
        for category, effect, headers_completed, body_completed, status in cases:
            with self.subTest(category=category):
                observation, response = classify(effect)
                self.assertEqual(observation["role"], "frontend")
                self.assertEqual(observation["failure_category"], category)
                self.assertEqual(observation["headers_completed"], headers_completed)
                self.assertEqual(observation["body_completed"], body_completed)
                self.assertEqual(observation["http_status"], status)
                self.assertEqual(observation["elapsed_ms"], 125)
                self.assertNotIn("url", observation)
                self.assertNotIn("must-not-leak", json.dumps(observation))
                if response is not None:
                    self.assertTrue(response.closed)

    def test_endpoint_recovery_reports_bounded_structural_diagnostics(self) -> None:
        expected_state = {
            "processes": [
                {
                    "role": "backend",
                    "launcher_pid": 101,
                    "creation_time_utc": "2026-09-19T00:00:00.0000000Z",
                    "executable_path": "backend-python.exe",
                },
                {
                    "role": "frontend",
                    "launcher_pid": 201,
                    "creation_time_utc": "2026-09-19T00:00:02.0000000Z",
                    "executable_path": "node.exe",
                },
            ]
        }
        identities = {
            101: {
                "pid": 101,
                "creation_time_utc": "2026-09-19T00:00:00.0000000Z",
                "executable_path": "backend-python.exe",
            },
            201: {
                "pid": 201,
                "creation_time_utc": "2026-09-19T00:00:02.0000000Z",
                "executable_path": "node.exe",
            },
        }
        now = [0.0]

        def endpoint_probe(name: str, _url: str) -> dict[str, Any]:
            if name == "backend":
                return {
                    "role": name,
                    "http_status": 503,
                    "failure_category": "http_non_200",
                    "headers_completed": True,
                    "body_completed": True,
                    "elapsed_ms": 12,
                }
            return {
                "role": name,
                "http_status": 200,
                "failure_category": "response_body_failure",
                "headers_completed": True,
                "body_completed": False,
                "elapsed_ms": 34,
            }

        with self.assertRaises(AssertionError) as raised:
            self.assert_owned_endpoints_healthy_within(
                expected_state,
                timeout=0.1,
                poll_interval=0.1,
                endpoint_probe=endpoint_probe,
                identity_probe=identities.get,
                monotonic=lambda: now[0],
                wait=lambda seconds: now.__setitem__(0, now[0] + seconds),
            )

        diagnostic = str(raised.exception)
        self.assertIn('"failure_category": "http_non_200"', diagnostic)
        self.assertIn('"failure_category": "response_body_failure"', diagnostic)
        self.assertIn('"remaining_budget_ms"', diagnostic)
        self.assertIn('"phase": "pre_deadline"', diagnostic)
        self.assertIn('"same_identity": true', diagnostic)
        self.assertNotIn("127.0.0.1", diagnostic)

        now[0] = 0.0

        def late_success(name: str, _url: str) -> bool:
            if name == "frontend":
                now[0] = 1.0
            return True

        with self.assertRaisesRegex(AssertionError, '"deadline_overrun"'):
            self.assert_owned_endpoints_healthy_within(
                expected_state,
                timeout=0.1,
                endpoint_probe=late_success,
                identity_probe=identities.get,
                monotonic=lambda: now[0],
                wait=lambda seconds: now.__setitem__(0, now[0] + seconds),
            )

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

    @staticmethod
    def _request_failure_category(exc: BaseException, *, operation_role: str) -> str:
        reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
        if isinstance(exc, urllib.error.HTTPError):
            if operation_role == "login" and exc.code in {401, 403}:
                return "http_denied"
            return "http_non_2xx"
        if (
            isinstance(reason, (TimeoutError, socket.timeout))
            or getattr(reason, "winerror", None) == 10060
        ):
            return "timeout"
        if (
            isinstance(reason, ConnectionRefusedError)
            or getattr(reason, "winerror", None) == 10061
        ):
            return "connection_refused"
        if isinstance(
            reason, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)
        ) or getattr(reason, "winerror", None) in {10053, 10054}:
            return "connection_reset"
        if isinstance(exc, (json.JSONDecodeError, KeyError, TypeError)):
            return "malformed_response"
        if isinstance(reason, (OSError, urllib.error.URLError)):
            return "transport_failure"
        return "request_failure"

    def _record_request_diagnostic(
        self,
        *,
        operation_role: str,
        stage: str,
        request_context: str,
        headers_received: bool,
        body_complete: bool,
        parse_complete: bool,
        http_status: int | None,
        failure_category: str | None,
        started_at: float,
        target_dispatched: bool,
    ) -> None:
        self.request_diagnostics.append(
            {
                "operation_role": operation_role,
                "stage": stage,
                "request_context": request_context,
                "headers_received": headers_received,
                "body_complete": body_complete,
                "parse_complete": parse_complete,
                "http_status": http_status,
                "failure_category": failure_category,
                "elapsed_ms": round(max(0.0, time.monotonic() - started_at) * 1000),
                "target_dispatched": target_dispatched,
            }
        )

    def _annotate_request_failure(self, exc: BaseException) -> None:
        exc.add_note(
            "authenticated_request_diagnostic="
            + json.dumps(self.request_diagnostics[-1], sort_keys=True)
        )

    def request(
        self,
        url: str,
        *,
        data: bytes | None = None,
        timeout: float = 3,
        request_context: str = "unspecified",
    ) -> tuple[int, bytes]:
        self.request_diagnostics = []
        safe_context = (
            request_context
            if request_context in {"before_reset", "after_reset", "unspecified"}
            else "unspecified"
        )
        opener: urllib.request.OpenerDirector | None = None
        csrf_token: str | None = None
        if "/api/" in url:
            login_started_at = time.monotonic()
            try:
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
            except Exception as exc:
                self._record_request_diagnostic(
                    operation_role="login",
                    stage="request_preparation",
                    request_context=safe_context,
                    headers_received=False,
                    body_complete=False,
                    parse_complete=False,
                    http_status=None,
                    failure_category=self._request_failure_category(
                        exc, operation_role="login"
                    ),
                    started_at=login_started_at,
                    target_dispatched=False,
                )
                self._annotate_request_failure(exc)
                raise
            try:
                response = opener.open(login_request, timeout=timeout)
            except Exception as exc:
                self._record_request_diagnostic(
                    operation_role="login",
                    stage="response_acquisition",
                    request_context=safe_context,
                    headers_received=isinstance(exc, urllib.error.HTTPError),
                    body_complete=False,
                    parse_complete=False,
                    http_status=(
                        int(exc.code)
                        if isinstance(exc, urllib.error.HTTPError)
                        else None
                    ),
                    failure_category=self._request_failure_category(
                        exc, operation_role="login"
                    ),
                    started_at=login_started_at,
                    target_dispatched=False,
                )
                self._annotate_request_failure(exc)
                raise
            login_status = int(response.status)
            try:
                with response:
                    login_body = response.read()
            except Exception as exc:
                self._record_request_diagnostic(
                    operation_role="login",
                    stage="body_read",
                    request_context=safe_context,
                    headers_received=True,
                    body_complete=False,
                    parse_complete=False,
                    http_status=login_status,
                    failure_category=self._request_failure_category(
                        exc, operation_role="login"
                    ),
                    started_at=login_started_at,
                    target_dispatched=False,
                )
                self._annotate_request_failure(exc)
                raise
            try:
                csrf_token = json.loads(login_body)["csrf_token"]
            except Exception as exc:
                self._record_request_diagnostic(
                    operation_role="login",
                    stage="response_parsing",
                    request_context=safe_context,
                    headers_received=True,
                    body_complete=True,
                    parse_complete=False,
                    http_status=login_status,
                    failure_category=self._request_failure_category(
                        exc, operation_role="login"
                    ),
                    started_at=login_started_at,
                    target_dispatched=False,
                )
                self._annotate_request_failure(exc)
                raise
            self._record_request_diagnostic(
                operation_role="login",
                stage="parse_complete",
                request_context=safe_context,
                headers_received=True,
                body_complete=True,
                parse_complete=True,
                http_status=login_status,
                failure_category=None,
                started_at=login_started_at,
                target_dispatched=False,
            )

        target_started_at = time.monotonic()
        try:
            request = urllib.request.Request(url, data=data)
            if data is not None:
                request.add_header("Content-Type", "application/json")
                request.add_header("X-CSRF-Token", csrf_token or "")
                request.add_header("Origin", "http://127.0.0.1:8000")
        except Exception as exc:
            self._record_request_diagnostic(
                operation_role="target_request",
                stage="request_preparation",
                request_context=safe_context,
                headers_received=False,
                body_complete=False,
                parse_complete=False,
                http_status=None,
                failure_category=self._request_failure_category(
                    exc, operation_role="target_request"
                ),
                started_at=target_started_at,
                target_dispatched=False,
            )
            self._annotate_request_failure(exc)
            raise
        try:
            open_request = opener.open if opener is not None else urllib.request.urlopen
            response = open_request(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            target_status = int(exc.code)
            try:
                target_body = exc.read()
            except Exception as body_exc:
                self._record_request_diagnostic(
                    operation_role="target_request",
                    stage="body_read",
                    request_context=safe_context,
                    headers_received=True,
                    body_complete=False,
                    parse_complete=False,
                    http_status=target_status,
                    failure_category=self._request_failure_category(
                        body_exc, operation_role="target_request"
                    ),
                    started_at=target_started_at,
                    target_dispatched=True,
                )
                self._annotate_request_failure(body_exc)
                raise
            self._record_request_diagnostic(
                operation_role="target_request",
                stage="body_complete",
                request_context=safe_context,
                headers_received=True,
                body_complete=True,
                parse_complete=False,
                http_status=target_status,
                failure_category="http_non_2xx",
                started_at=target_started_at,
                target_dispatched=True,
            )
            return target_status, target_body
        except Exception as exc:
            self._record_request_diagnostic(
                operation_role="target_request",
                stage="response_acquisition",
                request_context=safe_context,
                headers_received=False,
                body_complete=False,
                parse_complete=False,
                http_status=None,
                failure_category=self._request_failure_category(
                    exc, operation_role="target_request"
                ),
                started_at=target_started_at,
                target_dispatched=True,
            )
            self._annotate_request_failure(exc)
            raise
        target_status = int(response.status)
        try:
            with response:
                target_body = response.read()
        except Exception as exc:
            self._record_request_diagnostic(
                operation_role="target_request",
                stage="body_read",
                request_context=safe_context,
                headers_received=True,
                body_complete=False,
                parse_complete=False,
                http_status=target_status,
                failure_category=self._request_failure_category(
                    exc, operation_role="target_request"
                ),
                started_at=target_started_at,
                target_dispatched=True,
            )
            self._annotate_request_failure(exc)
            raise
        self._record_request_diagnostic(
            operation_role="target_request",
            stage="body_complete",
            request_context=safe_context,
            headers_received=True,
            body_complete=True,
            parse_complete=False,
            http_status=target_status,
            failure_category=None,
            started_at=target_started_at,
            target_dispatched=True,
        )
        return target_status, target_body

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

    def probe_endpoint_health(
        self,
        role: str,
        url: str,
        *,
        timeout: float,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> dict[str, Any]:
        """Probe one allowlisted endpoint without exposing response or error content."""

        started_at = monotonic()
        http_status: int | None = None
        headers_completed = False
        body_completed = False
        failure_category = "verifier_exception"
        try:
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                headers_completed = True
                http_status = int(response.status)
                try:
                    response.read()
                    body_completed = True
                except Exception:  # noqa: BLE001 - classify the response stage only
                    failure_category = "response_body_failure"
                else:
                    failure_category = (
                        "healthy" if http_status == 200 else "http_non_200"
                    )
        except urllib.error.HTTPError as exc:
            headers_completed = True
            http_status = int(exc.code)
            try:
                with exc:
                    exc.read()
                body_completed = True
            except Exception:  # noqa: BLE001 - non-200 remains the safe category
                body_completed = False
            failure_category = "http_non_200"
        except Exception as exc:  # noqa: BLE001 - sanitize the verifier boundary
            reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            if (
                isinstance(reason, ConnectionRefusedError)
                or getattr(reason, "winerror", None) == 10061
            ):
                failure_category = "connection_refused"
            elif isinstance(
                reason, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)
            ) or getattr(reason, "winerror", None) in {10053, 10054}:
                failure_category = "connection_reset"
            elif (
                isinstance(reason, (TimeoutError, socket.timeout))
                or getattr(reason, "winerror", None) == 10060
            ):
                failure_category = "timeout"
            elif isinstance(reason, (OSError, urllib.error.URLError)):
                failure_category = "transport_failure"
            else:
                failure_category = "verifier_exception"

        elapsed_ms = round(max(0.0, monotonic() - started_at) * 1000)
        return {
            "role": role,
            "http_status": http_status,
            "failure_category": failure_category,
            "headers_completed": headers_completed,
            "body_completed": body_completed,
            "elapsed_ms": elapsed_ms,
        }

    def assert_owned_endpoints_healthy_within(
        self,
        expected_state: dict[str, Any],
        *,
        timeout: float = 5.0,
        poll_interval: float = 0.1,
        endpoint_probe: Callable[[str, str], bool | dict[str, Any]] | None = None,
        identity_probe: Callable[[int], dict[str, str | int] | None] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        wait: Callable[[float], None] = time.sleep,
    ) -> None:
        """Require the original owned trees while allowing bounded HTTP recovery."""

        endpoints = {
            "backend": "http://127.0.0.1:8000/health",
            "frontend": "http://127.0.0.1:5173/",
        }
        use_structured_probe = endpoint_probe is None
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
                        "creation_time_utc": str(record["listener_creation_time_utc"]),
                        "executable_path": str(record["listener_executable_path"]),
                    }
                )

        attempts = 0
        last_endpoint_status = {name: False for name in endpoints}
        endpoint_observations: list[dict[str, Any]] = []
        identity_observations: list[dict[str, Any]] = []

        def observe_owned_identities(
            phase: str, deadline: float | None
        ) -> list[dict[str, str | int | bool | None]]:
            observation_started_at = monotonic()
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
                same_identity = _same_process_identity(expected, observed)
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
            observation_completed_at = monotonic()
            identity_observations.append(
                {
                    "phase": phase,
                    "elapsed_ms": round(
                        max(0.0, observation_completed_at - observation_started_at)
                        * 1000
                    ),
                    "remaining_budget_ms": (
                        None
                        if deadline is None
                        else round((deadline - observation_completed_at) * 1000)
                    ),
                    "identities": identity_diagnostics,
                }
            )
            if identity_changed:
                self.fail(
                    "Post-rejection owned process identity changed before endpoint "
                    "recovery: "
                    f"identities={json.dumps(identity_diagnostics, sort_keys=True)}, "
                    "identity_observations="
                    f"{json.dumps(identity_observations, sort_keys=True)}"
                )
            return identity_diagnostics

        observe_owned_identities("pre_deadline", None)
        deadline = monotonic() + timeout
        while True:
            if monotonic() > deadline:
                self.fail(
                    "Post-rejection endpoints did not recover before the monotonic "
                    f"deadline: attempts={attempts}, endpoints={last_endpoint_status}, "
                    f"probes={json.dumps(endpoint_observations, sort_keys=True)}, "
                    "identity_observations="
                    f"{json.dumps(identity_observations, sort_keys=True)}"
                )
            attempts += 1
            probe_completed_at: dict[str, float] = {}
            for name, url in endpoints.items():
                probe_started_at = monotonic()
                try:
                    if use_structured_probe:
                        observation = self.probe_endpoint_health(
                            name,
                            url,
                            timeout=min(timeout, 0.5),
                            monotonic=monotonic,
                        )
                    else:
                        assert endpoint_probe is not None
                        probe_result = endpoint_probe(name, url)
                        if isinstance(probe_result, dict):
                            observation = dict(probe_result)
                        else:
                            observation = {
                                "role": name,
                                "http_status": None,
                                "failure_category": (
                                    "healthy" if probe_result else "transport_failure"
                                ),
                                "headers_completed": None,
                                "body_completed": None,
                                "elapsed_ms": round(
                                    max(0.0, monotonic() - probe_started_at) * 1000
                                ),
                            }
                except Exception:  # noqa: BLE001 - sanitize injected verifier errors
                    observation = {
                        "role": name,
                        "http_status": None,
                        "failure_category": "verifier_exception",
                        "headers_completed": False,
                        "body_completed": False,
                        "elapsed_ms": round(
                            max(0.0, monotonic() - probe_started_at) * 1000
                        ),
                    }
                completed_at = monotonic()
                probe_completed_at[name] = completed_at
                observation["remaining_budget_ms"] = round(
                    (deadline - completed_at) * 1000
                )
                observation["attempt"] = attempts
                if completed_at > deadline:
                    observation["underlying_failure_category"] = observation[
                        "failure_category"
                    ]
                    observation["failure_category"] = "deadline_overrun"
                endpoint_observations.append(observation)
                last_endpoint_status[name] = (
                    observation["failure_category"] == "healthy"
                )
                if observation["failure_category"] == "verifier_exception":
                    self.fail(
                        "Endpoint verifier raised an unexpected exception: "
                        f"attempts={attempts}, "
                        f"probes={json.dumps(endpoint_observations, sort_keys=True)}"
                    )
            observe_owned_identities(f"attempt_{attempts}", deadline)
            if any(
                completed_at > deadline for completed_at in probe_completed_at.values()
            ):
                self.fail(
                    "Post-rejection endpoints did not recover before the "
                    f"monotonic deadline: attempts={attempts}, "
                    f"endpoints={last_endpoint_status}, "
                    f"probes={json.dumps(endpoint_observations, sort_keys=True)}, "
                    "identity_observations="
                    f"{json.dumps(identity_observations, sort_keys=True)}"
                )
            if all(last_endpoint_status.values()):
                return

            remaining = deadline - monotonic()
            if remaining <= 0:
                self.fail(
                    "Post-rejection endpoints did not recover while the original "
                    "owned process identities remained alive: "
                    f"attempts={attempts}, endpoints={last_endpoint_status}, "
                    f"probes={json.dumps(endpoint_observations, sort_keys=True)}, "
                    "identity_observations="
                    f"{json.dumps(identity_observations, sort_keys=True)}"
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

    def probe_process_identity(self, process_id: int) -> dict[str, str | int] | None:
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
                    "creation_time_utc": "2026-09-19T00:00:02.1230000Z",
                    "executable_path": "node.exe",
                    "listener_pid": 201,
                    "listener_creation_time_utc": "2026-09-19T00:00:02.123000Z",
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
                "creation_time_utc": "2026-09-19T08:00:02.1230000+08:00",
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
            expect_one_identity_batch_per_attempt: bool = False,
        ) -> dict[str, int]:
            now = [0.0]
            calls = {name: 0 for name in responses}
            identity_probe_calls = [0]
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
                identity_probe_calls[0] += 1
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
            if expect_one_identity_batch_per_attempt:
                expected_batches = 1 + max(calls.values())
                self.assertEqual(
                    identity_probe_calls[0],
                    len(expected_state["processes"]) * 2 * expected_batches,
                )
            return calls

        with self.subTest(post_rejection_probe="transient_frontend"):
            calls = exercise_probe_sequence(
                {"backend": [True, True], "frontend": [False, True]},
                expect_one_identity_batch_per_attempt=True,
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
            "http://127.0.0.1:8000/api/demo/clm/zero-touch/cases",
            data=payload,
            request_context="before_reset",
        )
        self.assertEqual(status, 201)
        case_id = json.loads(body)["case"]["case_id"]
        self.assertEqual(
            self.request(
                f"http://127.0.0.1:8000/api/clm/zero-touch/cases/{case_id}",
                request_context="before_reset",
            )[0],
            200,
        )

        reset = self.run_lifecycle("reset_demo_windows.bat", timeout=120)
        self.assertEqual(reset.returncode, 0)
        after_state = self.read_state()
        self.assertNotEqual(before_state["session_id"], after_state["session_id"])
        self.assert_owned_endpoints_healthy_within(after_state)
        self.assertEqual(
            self.request(
                f"http://127.0.0.1:8000/api/clm/zero-touch/cases/{case_id}",
                request_context="after_reset",
            )[0],
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
