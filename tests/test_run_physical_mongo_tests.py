from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "run_physical_mongo_tests.py"
SPEC = importlib.util.spec_from_file_location("physical_mongo_runner_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load run_physical_mongo_tests")
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

SECRET_URI = "mongo" + "db://user:private@127.0.0.1:27017"


def completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def collection_output() -> str:
    return "\n".join(str(path).replace("\\", "/") for path in RUNNER.PHYSICAL_SUITES)


def expected_counts(
    *,
    passed: int = 0,
    failed: int = 0,
    errors: int = 0,
    skipped: int = 0,
) -> dict[str, int]:
    return {
        "total": passed + failed + errors + skipped,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
    }


def run_actual_pytest(source: str) -> tuple[subprocess.CompletedProcess[str], dict[str, int] | None]:
    with tempfile.TemporaryDirectory(prefix="physical-runner-unit-") as directory:
        test_path = Path(directory) / "test_sample.py"
        test_path.write_text(source, encoding="utf-8")
        result = RUNNER._run_pytest(
            [
                str(test_path),
                "-o",
                "addopts=",
                "-p",
                "no:cacheprovider",
                "--tb=no",
                "-q",
            ],
            uri="",
            deadline=time.monotonic() + 30,
        )
        return result, RUNNER._summary(RUNNER._combined_output(result))


class PhysicalMongoRunnerTests(unittest.TestCase):
    def test_requires_only_explicit_phase12_environment(self) -> None:
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 2)
        self.assertIn("PHASE12_MONGO_URI_UNAVAILABLE", output.getvalue())

    def test_child_environment_is_narrow_and_never_maps_shared_settings(self) -> None:
        environment = RUNNER._child_environment(
            SECRET_URI,
            {
                "PATH": "safe",
                "MONGO_URI": "mongodb://shared",
                "MONGO_DATABASE": "clm_poc",
                "PYTEST_ADDOPTS": "--capture=no",
                "PYTHONPATH": "untrusted",
            },
        )
        self.assertEqual(environment["PHASE12_MONGO_URI"], SECRET_URI)
        self.assertEqual(environment["PYTEST_ADDOPTS"], "")
        self.assertEqual(environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"], "1")
        self.assertNotIn("MONGO_URI", environment)
        self.assertNotIn("MONGO_DATABASE", environment)
        self.assertNotIn("clm_poc", " ".join(environment.values()))

    def test_all_four_owned_suites_are_selected_and_success_requires_execution(self) -> None:
        execution = completed(0, "....")
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(
                RUNNER,
                "_run_pytest",
                side_effect=[completed(0, collection_output()), execution],
            ) as invoke,
            patch.object(
                RUNNER,
                "_summary",
                return_value=expected_counts(passed=4),
            ),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 0)
        first_arguments = invoke.call_args_list[0].args[0]
        for suite in RUNNER.PHYSICAL_SUITES:
            self.assertIn(str(suite.relative_to(ROOT)), first_arguments)
        execution_arguments = invoke.call_args_list[1].args[0]
        self.assertIn("-o", execution_arguments)
        self.assertIn("addopts=", execution_arguments)
        self.assertFalse(any(item.startswith("--junitxml=") for item in execution_arguments))
        self.assertIn("SUITES=4", output.getvalue())
        self.assertNotIn(SECRET_URI, output.getvalue())

    def test_all_skipped_is_blocked_not_verified(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(
                RUNNER,
                "_run_pytest",
                side_effect=[
                    completed(0, collection_output()),
                    completed(0, "ssss"),
                ],
            ),
            patch.object(
                RUNNER,
                "_summary",
                return_value=expected_counts(skipped=4),
            ),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 2)
        self.assertIn("ALL_SKIPPED", output.getvalue())

    def test_true_zero_collection_has_distinct_sanitized_result(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(RUNNER, "_run_pytest", return_value=completed(5, "")),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 2)
        self.assertIn("NO_TESTS_COLLECTED", output.getvalue())

    def test_collection_error_has_distinct_sanitized_result(self) -> None:
        output = io.StringIO()
        raw_failure = f"collection failed at {SECRET_URI}"
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(RUNNER, "_run_pytest", return_value=completed(2, stderr=raw_failure)),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        rendered = output.getvalue()
        self.assertEqual(result, 2)
        self.assertIn("COLLECTION_FAILED", rendered)
        self.assertNotIn(SECRET_URI, rendered)

    def test_execution_zero_collection_is_not_reported_as_test_failure(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(
                RUNNER,
                "_run_pytest",
                side_effect=[completed(0, collection_output()), completed(5, "")],
            ),
            patch.object(
                RUNNER,
                "_summary",
                return_value=expected_counts(),
            ),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 2)
        self.assertIn("NO_TESTS_COLLECTED", output.getvalue())

    def test_failure_output_is_contained_and_uri_is_never_rendered(self) -> None:
        output = io.StringIO()
        raw_failure = f"driver failed at {SECRET_URI}\nprivate document body"
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(
                RUNNER,
                "_run_pytest",
                side_effect=[
                    completed(0, collection_output()),
                    completed(1, ".F..", raw_failure),
                ],
            ),
            patch.object(
                RUNNER,
                "_summary",
                return_value=expected_counts(passed=3, failed=1),
            ),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        rendered = output.getvalue()
        self.assertEqual(result, 1)
        self.assertIn("EXECUTION_FAILED", rendered)
        self.assertNotIn(SECRET_URI, rendered)
        self.assertNotIn("private document body", rendered)

    def test_missing_summary_is_sanitized_non_success(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(
                RUNNER,
                "_run_pytest",
                side_effect=[completed(0, collection_output()), completed(0, "....")],
            ),
            patch.object(RUNNER, "_summary", return_value=None),
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 2)
        self.assertIn("SUMMARY_UNAVAILABLE", output.getvalue())

    def test_missing_or_unowned_suite_fails_before_execution(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(os.environ, {"PHASE12_MONGO_URI": SECRET_URI}, clear=True),
            patch.object(RUNNER.Path, "is_file", return_value=False),
            patch.object(RUNNER, "_run_pytest") as invoke,
            redirect_stdout(output),
        ):
            result = RUNNER.run(timeout_seconds=60)
        self.assertEqual(result, 2)
        invoke.assert_not_called()
        self.assertIn("MISSING_SUITES", output.getvalue())

    def test_runner_has_no_shared_database_or_cleanup_sweep_owner(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("clm_poc", source)
        self.assertNotIn("list_database_names", source)
        self.assertNotIn("drop_database", source)
        self.assertNotIn("Settings", source)

    def test_actual_pytest_all_pass_report_is_parsed(self) -> None:
        result, counts = run_actual_pytest(
            "def test_one():\n    assert True\n\ndef test_two():\n    assert 2 + 2 == 4\n"
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(counts, expected_counts(passed=2))

    def test_actual_pytest_mixed_pass_skip_report_is_parsed(self) -> None:
        result, counts = run_actual_pytest(
            "import pytest\n\ndef test_pass():\n    assert True\n\n"
            "@pytest.mark.skip(reason='bounded unit skip')\n"
            "def test_skip():\n    assert False\n"
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(counts, expected_counts(passed=1, skipped=1))

    def test_actual_pytest_failure_report_is_parsed(self) -> None:
        result, counts = run_actual_pytest("def test_failure():\n    assert False\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(counts, expected_counts(failed=1))

    def test_actual_pytest_collection_error_report_is_parsed(self) -> None:
        result, counts = run_actual_pytest("def test_invalid(:\n    pass\n")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(counts, expected_counts(errors=1))

    def test_actual_pytest_zero_collection_report_is_parsed(self) -> None:
        result, counts = run_actual_pytest("def helper():\n    return 1\n")
        self.assertEqual(result.returncode, 5)
        self.assertIsNone(counts)


if __name__ == "__main__":
    unittest.main()
