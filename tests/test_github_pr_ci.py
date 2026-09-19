from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "github_pr_ci.py"
SPEC = importlib.util.spec_from_file_location("github_pr_ci_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load github_pr_ci")
GITHUB_PR_CI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GITHUB_PR_CI
SPEC.loader.exec_module(GITHUB_PR_CI)

SHA_A = "a" * 40
SHA_B = "b" * 40


def view(
    sha: str = SHA_A,
    *,
    number: int = 17,
    repository: str = "example/repo",
    branch: str = "feature/tooling",
    url_suffix: str = "",
    **overrides: object,
) -> dict[str, object]:
    result: dict[str, object] = {
        "number": number,
        "url": f"https://github.com/{repository}/pull/{number}{url_suffix}",
        "state": "OPEN",
        "isDraft": False,
        "headRefName": branch,
        "headRefOid": sha,
        "baseRefName": "main",
        "reviewDecision": "REVIEW_REQUIRED",
        "mergeStateStatus": "BLOCKED",
    }
    result.update(overrides)
    return result


def check(name: str, bucket: str, *, workflow: str = "CI") -> dict[str, str]:
    return {
        "bucket": bucket,
        "event": "pull_request",
        "link": f"https://github.com/example/repo/actions/runs/1?check={name}",
        "name": name,
        "state": bucket.upper(),
        "workflow": workflow,
    }


class GitHubPrCiTests(unittest.TestCase):
    def _observe(
        self,
        target: str | None,
        sequence: list[tuple[int, object]],
        *,
        git_outputs: list[str] | None = None,
    ) -> tuple[int, dict[str, object]]:
        parsed_target = GITHUB_PR_CI._target(target, {})
        outputs = git_outputs or ["https://github.com/example/repo.git"]
        with (
            patch.object(GITHUB_PR_CI, "_run_json", side_effect=sequence),
            patch.object(
                GITHUB_PR_CI,
                "_run_text",
                side_effect=outputs,
                create=True,
            ),
        ):
            return GITHUB_PR_CI.observe(
                parsed_target,
                wait=False,
                timeout_seconds=60,
                poll_seconds=1,
            )

    def test_target_rejects_option_injection_and_malformed_urls(self) -> None:
        for value in (
            "--repo=attacker/repo",
            "feature..branch",
            "https://evil.example/owner/repo/pull/1",
            "https://user:secret@github.com/owner/repo/pull/1",
            "https://github.com/owner/repo/pull/1/",
        ):
            with self.subTest(value=value), self.assertRaises(
                GITHUB_PR_CI.argparse.ArgumentTypeError
            ):
                GITHUB_PR_CI._target(value, {})

    def test_target_accepts_number_url_and_safe_branch(self) -> None:
        self.assertEqual(GITHUB_PR_CI._target("17", {}).kind, "number")
        self.assertEqual(
            GITHUB_PR_CI._target("https://github.com/example/repo/pull/17", {}).kind,
            "url",
        )
        self.assertEqual(GITHUB_PR_CI._target("feature/tooling", {}).kind, "branch")

    def test_pr_url_query_and_fragment_are_accepted_but_canonicalized(self) -> None:
        try:
            target = GITHUB_PR_CI._target(
                "https://github.com/example/repo/pull/17?token=sentinel#fragment", {}
            )
        except GITHUB_PR_CI.argparse.ArgumentTypeError as exc:
            self.fail(f"safe identity URL was rejected instead of canonicalized: {exc}")
        self.assertEqual(target.argument, "https://github.com/example/repo/pull/17")

    def test_runner_uses_argument_list_shell_false_and_bounded_timeout(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"number": 1}', stderr="raw secret"
        )
        with patch.object(GITHUB_PR_CI.subprocess, "run", return_value=completed) as runner:
            code, payload = GITHUB_PR_CI._run_json(
                ["gh", "pr", "view", "17", "--json", "number"],
                GITHUB_PR_CI.time.monotonic() + 60,
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload, {"number": 1})
        args, kwargs = runner.call_args
        self.assertEqual(args[0][0:3], ["gh", "pr", "view"])
        self.assertFalse(kwargs["shell"])
        self.assertLessEqual(kwargs["timeout"], 30)
        self.assertTrue(kwargs["capture_output"])

    def test_subprocess_environment_cannot_redirect_observation_to_enterprise_host(self) -> None:
        source = {
            "PATH": "safe-path",
            "GH_TOKEN": "github-token",
            "GH_HOST": "enterprise.invalid",
            "GH_ENTERPRISE_TOKEN": "enterprise-token",
            "GITHUB_ENTERPRISE_TOKEN": "enterprise-token-2",
        }
        with patch.dict(os.environ, source, clear=True):
            result = GITHUB_PR_CI._subprocess_environment()
        self.assertEqual(result["PATH"], "safe-path")
        self.assertEqual(result["GH_TOKEN"], "github-token")
        self.assertNotIn("GH_HOST", result)
        self.assertNotIn("GH_ENTERPRISE_TOKEN", result)
        self.assertNotIn("GITHUB_ENTERPRISE_TOKEN", result)

    def test_local_git_identity_commands_are_fixed_read_only_and_bounded(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="https://github.com/example/repo.git\n",
            stderr="secret-marker",
        )
        with patch.object(GITHUB_PR_CI.subprocess, "run", return_value=completed) as runner:
            value = GITHUB_PR_CI._run_text(
                ["git", "remote", "get-url", "origin"],
                GITHUB_PR_CI.time.monotonic() + 60,
            )
        self.assertEqual(value, "https://github.com/example/repo.git")
        args, kwargs = runner.call_args
        self.assertEqual(args[0], ["git", "remote", "get-url", "origin"])
        self.assertFalse(kwargs["shell"])
        self.assertLessEqual(kwargs["timeout"], 10)
        self.assertTrue(kwargs["capture_output"])
        with self.assertRaises(GITHUB_PR_CI.ObservationError):
            GITHUB_PR_CI._run_text(
                ["git", "status"], GITHUB_PR_CI.time.monotonic() + 60
            )

    def test_repository_identity_accepts_only_supported_github_origin_forms(self) -> None:
        self.assertEqual(
            GITHUB_PR_CI._repository_from_remote(
                "https://github.com/example/repo.git"
            ),
            "example/repo",
        )
        self.assertEqual(
            GITHUB_PR_CI._repository_from_remote("git@github.com:example/repo.git"),
            "example/repo",
        )
        for value in (
            "https://user:secret@github.com/example/repo.git",
            "https://gitlab.com/example/repo.git",
            "https://github.com/example/repo.git?token=secret",
            "https://github.com/example/repo.git/",
            "ssh://git@github.com/example/repo.git",
            "git@github.com:example/too/many.git",
        ):
            with self.subTest(value=value), self.assertRaises(
                GITHUB_PR_CI.ObservationError
            ):
                GITHUB_PR_CI._repository_from_remote(value)

    def test_empty_required_checks_are_not_green(self) -> None:
        sequence = [(0, view()), (0, []), (0, []), (0, view())]
        code, report = self._observe("17", sequence)
        self.assertEqual(code, 2)
        self.assertEqual(report["outcome"], "NO_REQUIRED_CHECKS")

    def test_check_links_are_https_and_drop_query_data(self) -> None:
        payload = [check("backend", "pass")]
        with patch.object(GITHUB_PR_CI, "_run_json", return_value=(0, payload)):
            checks = GITHUB_PR_CI._checks(
                17,
                "example/repo",
                GITHUB_PR_CI.time.monotonic() + 60,
                required=True,
            )
        self.assertEqual(
            checks[0]["link"], "https://github.com/example/repo/actions/runs/1"
        )

        payload[0]["link"] = "http://github.com/example/repo/actions/runs/1"
        with (
            patch.object(GITHUB_PR_CI, "_run_json", return_value=(0, payload)),
            self.assertRaises(GITHUB_PR_CI.ObservationError),
        ):
            GITHUB_PR_CI._checks(
                17,
                "example/repo",
                GITHUB_PR_CI.time.monotonic() + 60,
                required=True,
            )

    def test_all_skipped_required_checks_are_not_green(self) -> None:
        required = [check("backend", "skipping")]
        sequence = [(0, view()), (0, required), (0, required), (0, view())]
        code, report = self._observe("17", sequence)
        self.assertEqual(code, 2)
        self.assertEqual(report["outcome"], "REQUIRED_CHECKS_NOT_EXECUTED")

    def test_required_pass_and_optional_failure_are_reported_separately(self) -> None:
        required = [check("backend", "pass")]
        all_checks = [*required, check("lint-advisory", "fail", workflow="Optional")]
        sequence = [(0, view()), (0, required), (0, all_checks), (0, view())]
        code, report = self._observe("17", sequence)
        self.assertEqual(code, 0)
        self.assertEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")
        self.assertEqual(report["observed_head_sha"], SHA_A)
        self.assertEqual([item["name"] for item in report["optional_failures"]], ["lint-advisory"])
        self.assertIn("not merge approval", report["advisory"])

    def test_pending_exit_eight_is_parsed_but_not_green(self) -> None:
        pending = [check("backend", "pending")]
        sequence = [(0, view()), (8, pending), (8, pending), (0, view())]
        code, report = self._observe("17", sequence)
        self.assertEqual(code, 8)
        self.assertEqual(report["outcome"], "PENDING")

    def test_head_change_invalidates_the_observation(self) -> None:
        required = [check("backend", "pass")]
        sequence = [(0, view(SHA_A)), (0, required), (0, required), (0, view(SHA_B))]
        code, report = self._observe("17", sequence)
        self.assertEqual(code, 2)
        self.assertEqual(report["outcome"], "HEAD_CHANGED")
        self.assertEqual(report["observed_head_sha"], SHA_A)
        self.assertEqual(report["pr"]["head_sha"], SHA_B)

    def test_raw_cli_error_text_is_not_rendered(self) -> None:
        output = io.StringIO()
        with (
            patch.object(
                GITHUB_PR_CI,
                "observe",
                side_effect=GITHUB_PR_CI.ObservationError("PR_VIEW_UNAVAILABLE"),
            ),
            redirect_stdout(output),
        ):
            result = GITHUB_PR_CI.main(["17"])
        report = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(report["outcome"], "PR_VIEW_UNAVAILABLE")
        self.assertNotIn("stderr", report)

    def test_requested_pr_number_mismatch_cannot_be_green(self) -> None:
        required = [check("backend", "pass")]
        code, report = self._observe(
            "17",
            [(0, view(number=18)), (0, required), (0, required), (0, view(number=18))],
        )
        self.assertNotEqual(code, 0)
        self.assertNotEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")

    def test_repository_or_branch_mismatch_cannot_be_green(self) -> None:
        required = [check("backend", "pass")]
        cases = (
            ("17", view(repository="other/repo"), ["https://github.com/example/repo.git"]),
            ("feature/tooling", view(branch="other/branch"), ["https://github.com/example/repo.git"]),
            (None, view(branch="other/branch"), ["https://github.com/example/repo.git", "feature/tooling"]),
        )
        for target, observed, git_outputs in cases:
            with self.subTest(target=target, observed=observed):
                code, report = self._observe(
                    target,
                    [(0, observed), (0, required), (0, required), (0, observed)],
                    git_outputs=git_outputs,
                )
                self.assertNotEqual(code, 0)
                self.assertNotEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")

    def test_explicit_url_repository_mismatch_cannot_be_green(self) -> None:
        required = [check("backend", "pass")]
        observed = view(repository="other/repo")
        code, report = self._observe(
            "https://github.com/example/repo/pull/17",
            [(0, observed), (0, required), (0, required), (0, observed)],
        )
        self.assertNotEqual(code, 0)
        self.assertNotEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")

    def test_pr_url_output_is_validated_and_canonicalized(self) -> None:
        required = [check("backend", "pass")]
        observed = view(url_suffix="?token=sentinel#fragment")
        code, report = self._observe(
            "17", [(0, observed), (0, required), (0, required), (0, observed)]
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["pr"]["url"], "https://github.com/example/repo/pull/17")  # type: ignore[index]
        self.assertNotIn("sentinel", json.dumps(report))

    def test_invalid_pr_view_fields_cannot_be_green(self) -> None:
        required = [check("backend", "pass")]
        invalid_views = (
            view(url_suffix="", url="http://github.com/example/repo/pull/17"),
            view(url_suffix="", url="https://gitlab.com/example/repo/pull/17"),
            view(url_suffix="", url="https://user:pass@github.com/example/repo/pull/17"),
            view(url_suffix="", url="https://github.com/example/repo/pull/17/"),
            view(state="UNTRUSTED"),
            view(reviewDecision="UNTRUSTED"),
            view(isDraft="false"),
            view(headRefOid="short"),
            view(number="17"),
        )
        for observed in invalid_views:
            with self.subTest(observed=observed):
                try:
                    code, report = self._observe(
                        "17", [(0, observed), (0, required), (0, required), (0, observed)]
                    )
                except GITHUB_PR_CI.ObservationError:
                    continue
                self.assertNotEqual(code, 0)
                self.assertNotEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")

    def test_untrusted_container_types_return_deterministic_non_success(self) -> None:
        required = [check("backend", "pass")]
        for field in ("state", "reviewDecision", "mergeStateStatus"):
            with self.subTest(field=field):
                observed = view(**{field: []})
                try:
                    code, report = self._observe(
                        "17", [(0, observed), (0, required), (0, required), (0, observed)]
                    )
                except (TypeError, ValueError) as exc:
                    self.fail(f"untrusted {field} escaped validation: {exc}")
                self.assertNotEqual(code, 0)
                self.assertNotEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")

    def test_second_view_identity_change_cannot_be_green(self) -> None:
        required = [check("backend", "pass")]
        code, report = self._observe(
            "17",
            [(0, view()), (0, required), (0, required), (0, view(number=18))],
        )
        self.assertNotEqual(code, 0)
        self.assertNotEqual(report["outcome"], "REQUIRED_CHECKS_PASSED")

    def test_every_gh_command_is_bound_to_expected_repository(self) -> None:
        required = [check("backend", "pass")]
        commands: list[list[str]] = []
        sequence = iter([(0, view()), (0, required), (0, required), (0, view())])

        def record(command: list[str], deadline: float) -> tuple[int, object]:
            del deadline
            commands.append(command)
            return next(sequence)

        with (
            patch.object(GITHUB_PR_CI, "_run_json", side_effect=record),
            patch.object(
                GITHUB_PR_CI,
                "_run_text",
                return_value="https://github.com/example/repo.git",
                create=True,
            ),
        ):
            code, _ = GITHUB_PR_CI.observe(
                GITHUB_PR_CI._target("17", {}),
                wait=False,
                timeout_seconds=60,
                poll_seconds=1,
            )
        self.assertEqual(code, 0)
        self.assertTrue(commands)
        for command in commands:
            self.assertIn("--repo", command)
            index = command.index("--repo")
            self.assertEqual(command[index + 1], "example/repo")

    def test_local_git_failure_is_sanitized_unavailable_evidence(self) -> None:
        required = [check("backend", "pass")]
        with (
            patch.object(
                GITHUB_PR_CI,
                "_run_json",
                side_effect=[(0, view()), (0, required), (0, required), (0, view())],
            ),
            patch.object(
                GITHUB_PR_CI,
                "_run_text",
                side_effect=GITHUB_PR_CI.ObservationError("LOCAL_GIT_UNAVAILABLE"),
                create=True,
            ),
        ):
            try:
                code, report = GITHUB_PR_CI.observe(
                    GITHUB_PR_CI._target("17", {}),
                    wait=False,
                    timeout_seconds=60,
                    poll_seconds=1,
                )
            except GITHUB_PR_CI.ObservationError as exc:
                self.assertEqual(exc.code, "LOCAL_GIT_UNAVAILABLE")
                return
        self.assertNotEqual(code, 0)
        self.assertEqual(report["outcome"], "LOCAL_GIT_UNAVAILABLE")

    def test_local_git_stderr_is_never_rendered(self) -> None:
        output = io.StringIO()
        with (
            patch.object(
                GITHUB_PR_CI,
                "_run_text",
                side_effect=GITHUB_PR_CI.ObservationError("LOCAL_GIT_UNAVAILABLE"),
            ),
            redirect_stdout(output),
        ):
            result = GITHUB_PR_CI.main(["17"])
        rendered = output.getvalue()
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(rendered)["outcome"], "LOCAL_GIT_UNAVAILABLE")
        self.assertNotIn("secret-marker", rendered)


if __name__ == "__main__":
    unittest.main()
