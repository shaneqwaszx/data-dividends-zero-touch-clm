from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dev_context.py"
SPEC = importlib.util.spec_from_file_location("dev_context_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load dev_context")
DEV_CONTEXT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DEV_CONTEXT
SPEC.loader.exec_module(DEV_CONTEXT)


class DevContextTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_root = ROOT / "tmp"
        fixture_root.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=fixture_root)
        self.repo = Path(self.temporary.name)
        self._git("init", "-b", "main")
        self._git("config", "user.email", "governance@example.invalid")
        self._git("config", "user.name", "Governance Test")
        (self.repo / "docs").mkdir()
        (self.repo / ".agents" / "skills").mkdir(parents=True)
        (self.repo / "docs" / "PROJECT_STATE.md").write_text(
            """# Current Project State
```json project-state
{"verified_date":"2026-09-15","verified_main_sha":"BASE","providers":{"target":{"name":"GOLDTIER","mode":"mock","classification":"MOCK"}},"open_sponsor_questions":["Q-012"]}
```
""",
            encoding="utf-8",
        )
        (self.repo / ".agents" / "skills" / "README.md").write_text(
            "| `sample-skill` | use | not use | relation |\n", encoding="utf-8"
        )
        (self.repo / ".env").write_text(
            "DO_NOT_READ=fixture-secret\n", encoding="utf-8"
        )
        self._git("add", "docs/PROJECT_STATE.md", ".agents/skills/README.md")
        self._git("commit", "-m", "fixture")
        sha = self._git("rev-parse", "HEAD").stdout.strip()
        state = (self.repo / "docs" / "PROJECT_STATE.md").read_text(encoding="utf-8")
        (self.repo / "docs" / "PROJECT_STATE.md").write_text(
            state.replace("BASE", sha), encoding="utf-8"
        )
        self._git("add", "docs/PROJECT_STATE.md")
        self._git("commit", "-m", "metadata")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self._git("switch", "-c", "feature/context")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_context_is_read_only_ignores_untracked_and_never_reads_env(self) -> None:
        untracked = self.repo / "untracked-secret.txt"
        untracked.write_text("UNTRACKED_SENTINEL\n", encoding="utf-8")
        before = (
            self._git("rev-parse", "HEAD").stdout,
            self._git("status", "--porcelain").stdout,
            untracked.read_bytes(),
        )
        opened: list[Path] = []
        real_read = DEV_CONTEXT._read_text

        def guarded_read(path: Path) -> str:
            opened.append(path)
            if path.name == ".env":
                raise AssertionError(".env access is forbidden")
            return real_read(path)

        with (
            patch.object(DEV_CONTEXT, "_read_text", side_effect=guarded_read),
            patch.dict(os.environ, {"GOVERNANCE_SECRET_SENTINEL": "DO_NOT_PRINT_ME"}),
        ):
            output = DEV_CONTEXT.render_context(self.repo)
        after = (
            self._git("rev-parse", "HEAD").stdout,
            self._git("status", "--porcelain").stdout,
            untracked.read_bytes(),
        )
        self.assertEqual(before, after)
        self.assertNotIn("DO_NOT_PRINT_ME", output)
        self.assertNotIn("UNTRACKED_SENTINEL", output)
        self.assertNotIn(self.repo / ".env", opened)
        self.assertIn("Tracked working tree: clean", output)

    def test_main_prints_git_metadata_and_returns_zero(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = DEV_CONTEXT.main(["--root", str(self.repo)])
        self.assertEqual(result, 0)
        self.assertIn("Branch: feature/context", output.getvalue())
        self.assertIn("Repository skills: sample-skill", output.getvalue())

    def test_resolves_repository_when_invoked_from_subdirectory(self) -> None:
        output = DEV_CONTEXT.render_context(self.repo / "docs")
        self.assertIn(f"Repository root: {self.repo.resolve()}", output)
        self.assertIn("Branch: feature/context", output)

    def test_detached_head_is_explicit(self) -> None:
        self._git("switch", "--detach")
        output = DEV_CONTEXT.render_context(self.repo)
        self.assertIn("Branch: DETACHED", output)

    def test_missing_origin_main_is_reported_as_unavailable(self) -> None:
        self._git("update-ref", "-d", "refs/remotes/origin/main")
        output = DEV_CONTEXT.render_context(self.repo)
        self.assertIn("origin/main: UNAVAILABLE", output)
        self.assertIn("Merge base: UNAVAILABLE", output)

    def test_missing_project_state_returns_sanitized_error(self) -> None:
        (self.repo / "docs" / "PROJECT_STATE.md").unlink()
        output = io.StringIO()
        with redirect_stdout(output):
            result = DEV_CONTEXT.main(["--root", str(self.repo)])
        self.assertEqual(result, 1)
        self.assertEqual(
            output.getvalue().strip(),
            "DEVELOPMENT CONTEXT ERROR: FileNotFoundError",
        )

    def test_malformed_project_state_returns_sanitized_error(self) -> None:
        (self.repo / "docs" / "PROJECT_STATE.md").write_text(
            "```json project-state\n{not-json}\n```\n", encoding="utf-8"
        )
        output = io.StringIO()
        with redirect_stdout(output):
            result = DEV_CONTEXT.main(["--root", str(self.repo)])
        self.assertEqual(result, 1)
        self.assertEqual(
            output.getvalue().strip(), "DEVELOPMENT CONTEXT ERROR: JSONDecodeError"
        )

    def test_tracked_dirty_worktree_is_reported(self) -> None:
        path = self.repo / "docs" / "PROJECT_STATE.md"
        path.write_text(path.read_text(encoding="utf-8") + "dirty\n", encoding="utf-8")
        output = DEV_CONTEXT.render_context(self.repo)
        self.assertIn("Tracked working tree: M docs/PROJECT_STATE.md", output)

    def test_git_lookup_failure_returns_sanitized_error(self) -> None:
        failure = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="sensitive path omitted"
        )
        output = io.StringIO()
        with (
            patch.object(DEV_CONTEXT, "_git", return_value=failure),
            redirect_stdout(output),
        ):
            result = DEV_CONTEXT.main(["--root", str(self.repo)])
        self.assertEqual(result, 1)
        self.assertEqual(
            output.getvalue().strip(), "DEVELOPMENT CONTEXT ERROR: ValueError"
        )


class ContextSelectionTests(unittest.TestCase):
    def test_known_change_classes_have_valid_deterministic_sections(self) -> None:
        self.assertEqual(DEV_CONTEXT.validate_context_manifest(ROOT), [])
        first = DEV_CONTEXT.select_context(ROOT, ["CI_TOOLING"])
        second = DEV_CONTEXT.select_context(ROOT, ["CI_TOOLING"])
        self.assertEqual(first, second)
        self.assertEqual(
            [reference.path for reference in first],
            sorted(reference.path for reference in first),
        )

    def test_unknown_change_class_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown change class; use --full"):
            DEV_CONTEXT.select_context(ROOT, ["NOT_A_CHANGE_CLASS"])

        output = io.StringIO()
        with redirect_stdout(output):
            result = DEV_CONTEXT.main(
                ["--root", str(ROOT), "--change-class", "NOT_A_CHANGE_CLASS"]
            )
        self.assertEqual(result, 1)
        self.assertEqual(
            output.getvalue().strip(),
            "DEVELOPMENT CONTEXT ERROR: unknown change class; use --full",
        )

    def test_empty_change_class_fails_closed_for_api_and_cli(self) -> None:
        for value in ("", "   "):
            with (
                self.subTest(value=repr(value), surface="api"),
                self.assertRaisesRegex(ValueError, "empty change class; use --full"),
            ):
                DEV_CONTEXT.select_context(ROOT, [value])

            with self.subTest(value=repr(value), surface="cli"):
                output = io.StringIO()
                with redirect_stdout(output):
                    result = DEV_CONTEXT.main(
                        ["--root", str(ROOT), "--change-class", value]
                    )
                self.assertEqual(result, 1)
                self.assertEqual(
                    output.getvalue().strip(),
                    "DEVELOPMENT CONTEXT ERROR: empty change class; use --full",
                )
                self.assertNotIn("Change classes: FULL", output.getvalue())

    def test_missing_declared_heading_fails_closed(self) -> None:
        errors = DEV_CONTEXT.validate_context_references(
            ROOT,
            [
                DEV_CONTEXT.ContextReference(
                    path="docs/ARCHITECTURE.md",
                    sections=("missing heading",),
                    tier=1,
                    reason="negative fixture",
                )
            ],
        )
        self.assertEqual(
            errors, ["missing section: docs/ARCHITECTURE.md#missing heading"]
        )

    def test_high_risk_classes_expand_to_full_canonical_context(self) -> None:
        for change_class in (
            "AUTH_RBAC_SECURITY",
            "PERSISTENCE",
            "EXTERNAL_PROVIDER",
        ):
            with self.subTest(change_class=change_class):
                references = DEV_CONTEXT.select_context(ROOT, [change_class])
                by_path = {reference.path: reference for reference in references}
                for path in DEV_CONTEXT.CANONICAL_CONTEXT_PATHS:
                    self.assertIn(path, by_path)
                    self.assertIsNone(by_path[path].sections)
                self.assertIn("docs/sponsor-questions/OPEN_QUESTIONS.md", by_path)
                self.assertIsNone(
                    by_path["docs/sponsor-questions/OPEN_QUESTIONS.md"].sections
                )

    def test_routine_benchmark_reduces_mean_utf8_footprint_by_thirty_percent(
        self,
    ) -> None:
        benchmark = DEV_CONTEXT.build_context_benchmark(ROOT)
        routine = [
            benchmark[change_class]
            for change_class in ("DOCS_ONLY", "FRONTEND_UI", "CI_TOOLING")
        ]
        mean_reduction = sum(row.reduction_percent for row in routine) / len(routine)
        self.assertGreaterEqual(mean_reduction, 30.0)
        for row in routine:
            self.assertLess(row.selected.bytes, row.baseline.bytes)
        for change_class in (
            "AUTH_RBAC_SECURITY",
            "PERSISTENCE",
            "EXTERNAL_PROVIDER",
        ):
            self.assertGreaterEqual(
                benchmark[change_class].selected.bytes,
                benchmark[change_class].baseline.bytes,
            )

    def test_context_selector_output_is_bounded_ordered_and_summary_first(self) -> None:
        output = DEV_CONTEXT.render_context(ROOT, change_classes=["CI_TOOLING"])
        self.assertIn("CONTEXT SELECTION", output)
        self.assertIn("Tier 0", output)
        self.assertIn("Tier 1", output)
        self.assertIn("Tier 2: on demand", output)
        self.assertNotIn("# Current Project State", output)
        self.assertLessEqual(len(output.splitlines()), 60)
        paths = [
            line.split(": ", maxsplit=1)[1].split(" # ", maxsplit=1)[0]
            for line in output.splitlines()
            if line.startswith("Reference: ")
        ]
        self.assertEqual(paths, sorted(paths))

    def test_main_supports_change_class_full_and_benchmark_modes(self) -> None:
        selected = io.StringIO()
        with redirect_stdout(selected):
            result = DEV_CONTEXT.main(
                ["--root", str(ROOT), "--change-class", "DOCS_ONLY"]
            )
        self.assertEqual(result, 0)
        self.assertIn("Change classes: DOCS_ONLY", selected.getvalue())

        full = io.StringIO()
        with redirect_stdout(full):
            result = DEV_CONTEXT.main(["--root", str(ROOT), "--full"])
        self.assertEqual(result, 0)
        self.assertIn("Selection mode: full diagnostic", full.getvalue())

        benchmark = io.StringIO()
        with redirect_stdout(benchmark):
            result = DEV_CONTEXT.main(["--root", str(ROOT), "--benchmark"])
        self.assertEqual(result, 0)
        self.assertIn("CONTEXT FOOTPRINT BENCHMARK", benchmark.getvalue())
        self.assertIn("Routine mean reduction:", benchmark.getvalue())

    def test_governance_surfaces_reference_the_canonical_context_policy(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        workflow = (ROOT / "docs" / "DEVELOPMENT_WORKFLOW.md").read_text(
            encoding="utf-8"
        )
        codex = (ROOT / "docs" / "CODEX_WORKFLOW.md").read_text(encoding="utf-8")
        pipeline = (ROOT / ".ai-pipeline" / "README.md").read_text(encoding="utf-8")
        phase_skill = (
            ROOT / ".agents" / "skills" / "fyp-phase-execution" / "SKILL.md"
        ).read_text(encoding="utf-8")
        reviewer = (ROOT / ".ai-pipeline" / "005_reviewer" / "ROLE.md").read_text(
            encoding="utf-8"
        )

        for text in (agents, workflow, pipeline, phase_skill):
            self.assertIn("--change-class", text)
            self.assertIn("--full", text)
        self.assertIn("## Context tiers and deterministic retrieval", workflow)
        self.assertIn("Passing-command evidence is summary-first", workflow)
        self.assertIn(
            "docs/DEVELOPMENT_WORKFLOW.md#coordination-and-model-routing", codex
        )
        self.assertIn("inspect the actual\nchanged content", reviewer)


if __name__ == "__main__":
    unittest.main()
