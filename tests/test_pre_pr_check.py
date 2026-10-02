from __future__ import annotations

import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import ANY, patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "pre_pr_check.py"
SPEC = importlib.util.spec_from_file_location("pre_pr_check_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load the pre-PR checker")
PRE_PR_CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PRE_PR_CHECK
SPEC.loader.exec_module(PRE_PR_CHECK)


class PrePrCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary_directory.name)
        self._git("init", "-b", "main")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Pre-PR Test")
        self._write("README.md", "baseline\n")
        self._git("add", "README.md")
        self._git("commit", "-m", "baseline")
        self._set_origin_main()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def _readonly_git(
        self, *args: str, binary: bool = False
    ) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=not binary,
            encoding=None if binary else "utf-8",
            env=environment,
        )

    def _set_origin_main(self) -> None:
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")

    def _write(self, relative: str, contents: str = "baseline\n") -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def _add_baseline_files(self, *paths: str) -> None:
        for path in paths:
            self._write(path)
        self._git("add", "--", *paths)
        self._git("commit", "-m", "add baseline fixtures")
        self._set_origin_main()

    def _switch_to_feature(self, name: str = "feature/checker") -> None:
        self._git("switch", "-c", name)

    def _commit_feature_files(self, *paths: str) -> None:
        self._git("add", "--", *paths)
        self._git("commit", "-m", "feature change")

    def _run_checker(self) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            result = PRE_PR_CHECK.main([], root=self.repo)
        return result, output.getvalue()

    def _copy_historical_patch(self, name: str, suffix: bytes = b"") -> str:
        relative = ".ai-pipeline/reports/" + name
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes() + suffix)
        self._git("config", "core.autocrlf", "false")
        (self.repo / "README.md").write_bytes(b"baseline\n")
        return relative

    def test_exact_three_historical_patches_pass_committed_checker(self) -> None:
        self._switch_to_feature()
        paths = [self._copy_historical_patch(name) for name in (
            "PHASE_24B_REMEDIATION_ROUND_1_DELTA.patch",
            "PHASE_24B_REMEDIATION_ROUND_2_DELTA.patch",
            "PHASE_24B_STAGE_RECOVERY_ROUND_1_ORCHESTRATION_DELTA.patch",
        )]
        self._commit_feature_files(*paths)
        result, output = self._run_checker()
        self.assertEqual(result, 0, output)
        self.assertIn("SUMMARY: PASS", output)
        for relative in paths:
            self.assertIn("Exact historical patch whitespace identity: " + relative, output)

    def test_normal_source_and_markdown_whitespace_still_fail(self) -> None:
        self._switch_to_feature()
        self._write("ordinary.py", "value = 1 \n")
        self._write("ordinary.md", "ordinary text \n")
        self._commit_feature_files("ordinary.py", "ordinary.md")
        result, output = self._run_checker()
        self.assertEqual(result, 1)
        for relative in ("ordinary.py", "ordinary.md"):
            self.assertIn(relative + ":1: trailing whitespace", output)

    def test_arbitrary_patch_context_whitespace_is_not_exempt(self) -> None:
        self._switch_to_feature()
        self._write("new.patch", "--- a/file\n+++ b/file\n@@ -1 +1 @@\n \n")
        self._commit_feature_files("new.patch")
        result, output = self._run_checker()
        self.assertEqual(result, 1)
        self.assertIn("new.patch:4: trailing whitespace", output)

    def test_approved_patch_changed_byte_fails_identity(self) -> None:
        self._switch_to_feature()
        relative = self._copy_historical_patch("PHASE_24B_REMEDIATION_ROUND_1_DELTA.patch")
        target = self.repo / relative
        raw = target.read_bytes()
        changed = b"?" + raw[1:]
        self.assertNotEqual(raw, changed)
        target.write_bytes(changed)
        self._commit_feature_files(relative)
        result, output = self._run_checker()
        self.assertEqual(result, 1)
        self.assertIn("Historical patch identity mismatch: " + relative, output)

    def test_approved_patch_additional_whitespace_fails_identity(self) -> None:
        self._switch_to_feature()
        relative = self._copy_historical_patch(
            "PHASE_24B_REMEDIATION_ROUND_2_DELTA.patch", b"unexpected whitespace \n"
        )
        self._commit_feature_files(relative)
        result, output = self._run_checker()
        self.assertEqual(result, 1)
        self.assertIn("Historical patch identity mismatch: " + relative, output)
        self.assertIn("trailing whitespace", output)

    def test_approved_patch_changed_hash_without_whitespace_still_fails(self) -> None:
        self._switch_to_feature()
        relative = self._copy_historical_patch("PHASE_24B_REMEDIATION_ROUND_1_DELTA.patch")
        target = self.repo / relative
        target.write_bytes(b"ordinary text without whitespace\n")
        self._commit_feature_files(relative)
        result, output = self._run_checker()
        self.assertEqual(result, 1)
        self.assertIn("Historical patch identity mismatch: " + relative, output)

    def test_historical_patch_unrecognized_diagnostic_still_fails(self) -> None:
        relative = ".ai-pipeline/reports/PHASE_24B_REMEDIATION_ROUND_1_DELTA.patch"
        report = PRE_PR_CHECK.Report()
        completed = subprocess.CompletedProcess(
            [], 2, relative + ":1: trailing whitespace.\n+unexpected \n", ""
        )
        PRE_PR_CHECK._check_diff_whitespace(
            report, completed, "staged changes", {relative: (ROOT / relative).read_text(encoding="utf-8")}
        )
        self.assertTrue(report.failures)

    def test_clean_feature_branch_containing_origin_main_passes(self) -> None:
        self._switch_to_feature()

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertIn("Branch relationship: ahead 0, behind 0", output)
        self.assertIn("Working-tree inventory: clean", output)
        self.assertIn("SUMMARY: PASS", output)
        self.assertIn("PASS does not prove semantic merge safety", output)

    def test_main_branch_fails(self) -> None:
        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Current branch is main", output)
        self.assertIn("SUMMARY: FAIL", output)

    def test_branch_behind_origin_main_fails(self) -> None:
        self._switch_to_feature("feature/stale")
        self._git("switch", "main")
        self._write("README.md", "new main\n")
        self._git("add", "README.md")
        self._git("commit", "-m", "advance main")
        self._set_origin_main()
        self._git("switch", "feature/stale")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("does not contain the latest origin/main", output)
        self.assertIn("ahead 0, behind 1", output)

    def test_missing_origin_main_fails(self) -> None:
        self._switch_to_feature("feature/no-origin-main")
        self._git("update-ref", "-d", "refs/remotes/origin/main")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("origin/main does not exist", output)

    def test_unstaged_tracked_modification_fails(self) -> None:
        self._switch_to_feature("feature/unstaged")
        self._write("README.md", "unstaged\n")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Unstaged tracked changes must be committed", output)
        self.assertIn(" M README.md", output)

    def test_staged_tracked_modification_fails(self) -> None:
        self._switch_to_feature("feature/staged")
        self._write("README.md", "staged\n")
        self._git("add", "README.md")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Staged changes must be committed", output)
        self.assertIn("M  README.md", output)

    def test_untracked_file_fails(self) -> None:
        self._switch_to_feature("feature/untracked")
        self._write("new-file.txt", "untracked\n")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Untracked files must be committed, ignored, or removed", output)
        self.assertIn("?? new-file.txt", output)

    def test_staged_and_unstaged_mixed_state_fails(self) -> None:
        self._switch_to_feature("feature/mixed-index")
        self._write("README.md", "staged\n")
        self._git("add", "README.md")
        self._write("README.md", "staged plus unstaged\n")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Staged changes must be committed", output)
        self.assertIn("Unstaged tracked changes must be committed", output)
        self.assertIn("MM README.md", output)

    def test_tracked_and_untracked_mixed_state_fails(self) -> None:
        self._switch_to_feature("feature/mixed-untracked")
        self._write("README.md", "unstaged\n")
        self._write("new-file.txt", "untracked\n")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Unstaged tracked changes must be committed", output)
        self.assertIn("Untracked files must be committed, ignored, or removed", output)

    def test_unresolved_git_conflict_fails(self) -> None:
        self._switch_to_feature("feature/conflict")
        self._write("README.md", "feature\n")
        self._commit_feature_files("README.md")
        self._git("switch", "main")
        self._write("README.md", "main\n")
        self._git("add", "README.md")
        self._git("commit", "-m", "main change")
        self._set_origin_main()
        self._git("switch", "feature/conflict")
        merge = subprocess.run(
            ["git", "merge", "origin/main"],
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(merge.returncode, 0)

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Unresolved Git conflicts: README.md", output)

    def test_committed_coherent_conflict_markers_fail(self) -> None:
        self._switch_to_feature("feature/markers")
        self._write(
            "module.py",
            "<<<<<<< branch\ncurrent\n=======\nincoming\n>>>>>>> origin/main\n",
        )
        self._commit_feature_files("module.py")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Conflict marker structure in changed file module.py", output)

    def test_standalone_equals_separators_do_not_trigger_marker_failure(self) -> None:
        self._switch_to_feature("feature/benign-separators")
        self._write("notes.md", "heading\n=======\nbody\n==========\n")
        self._commit_feature_files("notes.md")

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertNotIn("Conflict marker", output)
        self.assertIn("SUMMARY: PASS", output)

    def test_partial_start_and_end_markers_are_intentionally_unsafe(self) -> None:
        self._switch_to_feature("feature/partial-marker")
        self._write("start.txt", "<<<<<<< branch\ncontent without end\n")
        self._write("end.txt", "content without start\n>>>>>>> branch\n")
        self._commit_feature_files("start.txt", "end.txt")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Conflict marker structure in changed file start.txt", output)
        self.assertIn("Conflict marker structure in changed file end.txt", output)

    def test_marker_logic_detects_coherent_matching_non_default_widths(self) -> None:
        for width in (1, 8, 32, 128):
            with self.subTest(width=width):
                text = (
                    f"{'<' * width} branch\n"
                    "current\n"
                    f"{'=' * width}\n"
                    "incoming\n"
                    f"{'>' * width} origin/main\n"
                )

                self.assertEqual(PRE_PR_CHECK._marker_lines(text), [1, 3, 5])

    def _configure_non_default_marker_fixture(self, width: int = 32) -> None:
        self._write(".gitattributes", f"*.txt conflict-marker-size={width}\n")
        self._write("notes.txt", "baseline\n")
        self._git("add", ".gitattributes", "notes.txt")
        self._git("commit", "-m", "configure conflict marker size")
        self._set_origin_main()
        self._switch_to_feature(f"feature/marker-size-{width}")
        attribute = self._git(
            "check-attr", "conflict-marker-size", "--", "notes.txt"
        ).stdout
        self.assertIn(f"conflict-marker-size: {width}", attribute)

    @staticmethod
    def _coherent_marker_text(width: int = 32) -> str:
        return (
            f"{'<' * width} branch\n"
            "current\n"
            f"{'=' * width}\n"
            "incoming\n"
            f"{'>' * width} origin/main\n"
        )

    def test_committed_git_supported_non_default_markers_fail(self) -> None:
        self._configure_non_default_marker_fixture()
        self._write("notes.txt", self._coherent_marker_text())
        self._commit_feature_files("notes.txt")
        raw_diff_check = subprocess.run(
            ["git", "diff", "--check", "origin/main...HEAD"],
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(raw_diff_check.returncode, 0)
        self.assertIn("leftover conflict marker", raw_diff_check.stdout)

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Conflict marker structure in changed file notes.txt", output)

    def test_staged_git_supported_non_default_markers_fail(self) -> None:
        self._configure_non_default_marker_fixture()
        self._write("notes.txt", self._coherent_marker_text())
        self._git("add", "notes.txt")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Conflict marker structure in staged file notes.txt", output)

    def test_unstaged_git_supported_non_default_markers_fail(self) -> None:
        self._configure_non_default_marker_fixture()
        self._write("notes.txt", self._coherent_marker_text())

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Conflict marker structure in unstaged file notes.txt", output)

    def test_committed_trailing_whitespace_still_fails_diff_check(self) -> None:
        self._switch_to_feature("feature/whitespace")
        self._write("module.py", "value = 1  \n")
        self._commit_feature_files("module.py")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("git diff --check failed for the branch delta", output)

    def test_committed_ordinary_deletion_is_visible(self) -> None:
        self._add_baseline_files("notes.txt")
        self._switch_to_feature("feature/committed-deletion")
        self._git("rm", "notes.txt")
        self._git("commit", "-m", "delete notes")

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertIn("D\tnotes.txt", output)
        self.assertNotIn("Committed branch delta: none", output)

    def test_staged_ordinary_deletion_is_visible_and_fails_dirty_check(self) -> None:
        self._add_baseline_files("notes.txt")
        self._switch_to_feature("feature/staged-deletion")
        self._git("rm", "notes.txt")

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Staged changes must be committed", output)
        self.assertIn("D  notes.txt", output)

    def test_unstaged_ordinary_deletion_is_visible_and_fails_dirty_check(self) -> None:
        self._add_baseline_files("notes.txt")
        self._switch_to_feature("feature/unstaged-deletion")
        (self.repo / "notes.txt").unlink()

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Unstaged tracked changes must be committed", output)
        self.assertIn(" D notes.txt", output)

    def test_committed_hotspot_deletion_is_visible_and_warned(self) -> None:
        path = "apps/frontend/src/App.tsx"
        self._add_baseline_files(path)
        self._switch_to_feature("feature/hotspot-deletion")
        self._git("rm", path)
        self._git("commit", "-m", "delete hotspot")

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertIn(f"D\t{path}", output)
        self.assertIn(f"Integration hotspot files changed: {path}", output)

    def test_staged_hotspot_deletion_is_visible_and_warned(self) -> None:
        path = "apps/backend/app/composition.py"
        self._add_baseline_files(path)
        self._switch_to_feature("feature/staged-hotspot-deletion")
        self._git("rm", path)

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Staged changes must be committed", output)
        self.assertIn(f"Integration hotspot files changed: {path}", output)

    def test_unstaged_ci_deletion_is_visible_and_warned(self) -> None:
        path = ".github/workflows/ci.yml"
        self._add_baseline_files(path)
        self._switch_to_feature("feature/ci-deletion")
        (self.repo / path).unlink()

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Unstaged tracked changes must be committed", output)
        self.assertIn(f"CI workflow changed: {path}", output)

    def test_staged_ci_deletion_is_visible_and_warned(self) -> None:
        path = ".github/workflows/ci.yml"
        self._add_baseline_files(path)
        self._switch_to_feature("feature/staged-ci-deletion")
        self._git("rm", path)

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Staged changes must be committed", output)
        self.assertIn(f"CI workflow changed: {path}", output)

    def test_unstaged_dependency_deletion_is_visible_and_warned(self) -> None:
        path = "apps/frontend/package-lock.json"
        self._add_baseline_files(path)
        self._switch_to_feature("feature/dependency-deletion")
        (self.repo / path).unlink()

        result, output = self._run_checker()

        self.assertEqual(result, 1)
        self.assertIn("Unstaged tracked changes must be committed", output)
        self.assertIn(f"Dependency manifests/lockfiles changed: {path}", output)

    def test_committed_api_owner_deletion_is_visible_and_warned(self) -> None:
        path = "apps/backend/app/api_models.py"
        self._add_baseline_files(path)
        self._switch_to_feature("feature/api-deletion")
        self._git("rm", path)
        self._git("commit", "-m", "delete api owner")

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertIn(f"D\t{path}", output)
        self.assertIn(f"API/config/shared type files changed: {path}", output)

    def test_committed_rename_is_visible_and_classifies_old_hotspot(self) -> None:
        old_path = "apps/frontend/src/App.tsx"
        new_path = "apps/frontend/src/Application.tsx"
        self._add_baseline_files(old_path)
        self._switch_to_feature("feature/rename")
        self._git("mv", old_path, new_path)
        self._git("commit", "-m", "rename application")

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        pattern = rf"R\d+\t{re.escape(old_path)} -> {re.escape(new_path)}"
        self.assertRegex(output, pattern)
        self.assertIn(f"Integration hotspot files changed: {old_path}", output)

    def test_type_and_copy_change_status_records_are_parsed(self) -> None:
        result = subprocess.CompletedProcess(
            args=["git", "diff", "--name-status", "-z"],
            returncode=0,
            stdout=(
                b"T\0typed.txt\0"
                b"C100\0old path with spaces.txt\0new path with spaces.txt\0"
            ),
            stderr=b"",
        )

        changes = PRE_PR_CHECK._changes_from_name_status(result)

        self.assertEqual(
            changes,
            [
                PRE_PR_CHECK.Change(status="T", path="typed.txt"),
                PRE_PR_CHECK.Change(
                    status="C100",
                    path="new path with spaces.txt",
                    previous_path="old path with spaces.txt",
                ),
            ],
        )

    def test_common_sensitive_filenames_fail_without_printing_contents(self) -> None:
        for filename in (
            "credentials.json",
            "service-account-key.json",
            ".env",
            "private.pem",
        ):
            with (
                self.subTest(filename=filename),
                tempfile.TemporaryDirectory() as directory,
            ):
                repo = Path(directory)
                self._initialize_standalone_repo(repo, filename)
                output = io.StringIO()
                with redirect_stdout(output):
                    result = PRE_PR_CHECK.main([], root=repo)
                rendered = output.getvalue()
                self.assertEqual(result, 1)
                self.assertIn(filename, rendered)
                self.assertNotIn("fixture-private-value", rendered)

    def _initialize_standalone_repo(self, repo: Path, tracked_filename: str) -> None:
        def run(*args: str) -> None:
            subprocess.run(
                ["git", *args],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        run("init", "-b", "main")
        run("config", "user.email", "test@example.invalid")
        run("config", "user.name", "Pre-PR Test")
        path = repo / tracked_filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture-private-value\n", encoding="utf-8")
        run("add", "--", tracked_filename)
        run("commit", "-m", "baseline")
        run("update-ref", "refs/remotes/origin/main", "HEAD")
        run("switch", "-c", "feature/sensitive-name")

    def test_safe_environment_example_and_ordinary_config_are_allowed(self) -> None:
        self._switch_to_feature("feature/safe-names")
        paths = (".env.example", "ordinary-config.json")
        for path in paths:
            self._write(path, "placeholder=true\n")
        self._commit_feature_files(*paths)

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertNotIn("Tracked obvious secret/environment files", output)

    def test_required_api_config_and_shared_type_owners_are_warned(self) -> None:
        paths = (
            "apps/backend/app/api_models.py",
            "apps/backend/app/config.py",
            "apps/backend/app/main.py",
            "apps/frontend/src/api.ts",
            "apps/frontend/src/types.ts",
            "apps/frontend/src/shared.ts",
        )
        self._add_baseline_files(*paths)
        self._switch_to_feature("feature/shared-contracts")
        for path in paths:
            self._write(path, "changed\n")
        self._commit_feature_files(*paths)

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        warning = next(
            line
            for line in output.splitlines()
            if "API/config/shared type files changed" in line
        )
        for path in paths:
            self.assertIn(path, warning)

    def test_ordinary_source_file_has_no_api_shared_contract_warning(self) -> None:
        path = "apps/backend/app/services/onboarding.py"
        self._switch_to_feature("feature/ordinary-source")
        self._write(path, "ordinary\n")
        self._commit_feature_files(path)

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertNotIn("API/config/shared type files changed", output)

    def test_committed_warning_categories_remain_advisory(self) -> None:
        paths = (
            ".github/workflows/extra.yml",
            "apps/frontend/package-lock.json",
            "apps/frontend/src/api.ts",
        )
        self._switch_to_feature("feature/warnings")
        for path in paths:
            self._write(path, "safe\n")
        self._commit_feature_files(*paths)

        result, output = self._run_checker()

        self.assertEqual(result, 0)
        self.assertIn("CI workflow changed", output)
        self.assertIn("Dependency manifests/lockfiles changed", output)
        self.assertIn("API/config/shared type files changed", output)
        self.assertIn("SUMMARY: PASS", output)

    def test_checker_does_not_change_head_refs_index_or_worktree(self) -> None:
        self._switch_to_feature("feature/read-only")
        self._write("README.md", "staged\n")
        self._git("add", "README.md")
        self._write("README.md", "staged plus unstaged\n")
        self._write("notes.txt", "keep me\n")
        before = (
            self._git("rev-parse", "HEAD").stdout,
            self._git("show-ref").stdout,
            self._git("write-tree").stdout,
            self._git("status", "--porcelain=v1").stdout,
            (self.repo / "README.md").read_bytes(),
            (self.repo / "notes.txt").read_bytes(),
        )

        result, _ = self._run_checker()

        after = (
            self._git("rev-parse", "HEAD").stdout,
            self._git("show-ref").stdout,
            self._git("write-tree").stdout,
            self._git("status", "--porcelain=v1").stdout,
            (self.repo / "README.md").read_bytes(),
            (self.repo / "notes.txt").read_bytes(),
        )
        self.assertEqual(result, 1)
        self.assertEqual(after, before)

    def test_git_runner_preserves_environment_and_disables_optional_locks(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["git", "status", "--short"],
            returncode=0,
            stdout="",
            stderr="",
        )
        with (
            patch.dict(
                os.environ,
                {"PRE_PR_CHECK_SENTINEL": "preserved", "GIT_OPTIONAL_LOCKS": "1"},
            ),
            patch.object(PRE_PR_CHECK.subprocess, "run", return_value=completed) as run,
        ):
            PRE_PR_CHECK._git(self.repo, "status", "--short")

        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["PRE_PR_CHECK_SENTINEL"], "preserved")
        self.assertEqual(environment["GIT_OPTIONAL_LOCKS"], "0")
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_clean_mtime_only_check_preserves_raw_index_bytes(self) -> None:
        self._switch_to_feature("feature/mtime-read-only")
        ignored_path = self._write("ignored-local.txt", "ignored but preserved\n")
        exclude_path = self.repo / ".git" / "info" / "exclude"
        exclude_path.write_text("ignored-local.txt\n", encoding="utf-8")
        tracked_path = self.repo / "README.md"

        def repository_state() -> tuple[object, ...]:
            tracked_paths = self._readonly_git("ls-files", "-z", binary=True).stdout
            return (
                self._readonly_git("rev-parse", "HEAD").stdout,
                self._readonly_git("show-ref").stdout,
                (self.repo / ".git" / "index").read_bytes(),
                self._readonly_git("ls-files", "--stage", "-z", binary=True).stdout,
                tracked_paths,
                tracked_path.read_bytes(),
                ignored_path.read_bytes(),
                self._readonly_git("status", "--porcelain=v1").stdout,
            )

        before = repository_state()
        original_stat = tracked_path.stat()
        os.utime(
            tracked_path,
            ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 2_000_000_000),
        )
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), before[2])

        with patch.dict(os.environ, {"GIT_OPTIONAL_LOCKS": "1"}):
            result, output = self._run_checker()

        after = repository_state()
        self.assertEqual(result, 0)
        self.assertIn("Working-tree inventory: clean", output)
        self.assertIn("SUMMARY: PASS", output)
        self.assertEqual(after, before)

    def test_governance_check_runs_read_only_script_and_reports_result(self) -> None:
        script = self.repo / "scripts" / "check_project_state.py"
        script.parent.mkdir()
        script.write_text("raise SystemExit(0)\n", encoding="utf-8")
        report = PRE_PR_CHECK.Report()
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="PROJECT STATE CHECK: PASS\n", stderr=""
        )

        with patch.object(
            PRE_PR_CHECK.subprocess, "run", return_value=completed
        ) as run:
            PRE_PR_CHECK._run_governance_check(
                self.repo, report, "check_project_state.py"
            )

        self.assertEqual(report.failures, [])
        self.assertIn("check_project_state.py: PASS", report.details)
        self.assertEqual(
            run.call_args.args[0],
            [
                PRE_PR_CHECK.sys.executable,
                str(script),
                "--root",
                str(self.repo),
            ],
        )
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_governance_check_failure_surfaces_stderr_only(self) -> None:
        script = self.repo / "scripts" / "check_project_state.py"
        script.parent.mkdir()
        script.write_text("raise SystemExit(1)\n", encoding="utf-8")
        report = PRE_PR_CHECK.Report()
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="structured drift\n"
        )
        with patch.object(PRE_PR_CHECK.subprocess, "run", return_value=completed):
            PRE_PR_CHECK._run_governance_check(
                self.repo, report, "check_project_state.py"
            )
        self.assertEqual(len(report.failures), 1)
        self.assertIn("stderr:\nstructured drift", report.failures[0])

    def test_governance_check_failure_surfaces_stdout_only(self) -> None:
        script = self.repo / "scripts" / "check_architecture.py"
        script.parent.mkdir()
        script.write_text("raise SystemExit(1)\n", encoding="utf-8")
        report = PRE_PR_CHECK.Report()
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="boundary violation\n", stderr=""
        )
        with patch.object(PRE_PR_CHECK.subprocess, "run", return_value=completed):
            PRE_PR_CHECK._run_governance_check(
                self.repo, report, "check_architecture.py"
            )
        self.assertEqual(len(report.failures), 1)
        self.assertIn("stdout:\nboundary violation", report.failures[0])

    def test_governance_check_failure_surfaces_stdout_and_stderr(self) -> None:
        script = self.repo / "scripts" / "check_architecture.py"
        script.parent.mkdir()
        script.write_text("raise SystemExit(2)\n", encoding="utf-8")
        report = PRE_PR_CHECK.Report()
        completed = subprocess.CompletedProcess(
            args=[], returncode=2, stdout="checker summary\n", stderr="parse detail\n"
        )
        with patch.object(PRE_PR_CHECK.subprocess, "run", return_value=completed):
            PRE_PR_CHECK._run_governance_check(
                self.repo, report, "check_architecture.py"
            )
        self.assertEqual(len(report.failures), 1)
        self.assertIn("exit 2", report.failures[0])
        self.assertIn("stdout:\nchecker summary", report.failures[0])
        self.assertIn("stderr:\nparse detail", report.failures[0])

    def test_audit_routes_tooling_config_through_governance_owner(self) -> None:
        with patch.object(PRE_PR_CHECK, "_run_governance_check") as governance:
            PRE_PR_CHECK.audit_repository(self.repo)
        self.assertIn(
            (self.repo, ANY, "check_tooling_config.py"),
            [call.args for call in governance.call_args_list],
        )

    def test_audit_routes_policy_authority_through_governance_owner(self) -> None:
        with patch.object(PRE_PR_CHECK, "_run_governance_check") as governance:
            PRE_PR_CHECK.audit_repository(self.repo)
        self.assertIn(
            (self.repo, ANY, "check_policy_authority.py"),
            [call.args for call in governance.call_args_list],
        )


if __name__ == "__main__":
    unittest.main()
