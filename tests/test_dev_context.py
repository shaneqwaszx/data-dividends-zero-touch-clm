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


if __name__ == "__main__":
    unittest.main()
