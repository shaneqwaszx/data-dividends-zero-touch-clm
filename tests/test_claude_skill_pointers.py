"""Claude Code pointers must mirror canonical skills.

Shared settings must not exclude instruction files and must ask before the listed branch
and worktree mutations in both the Bash and PowerShell tools.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POINTER_ROOT = ROOT / ".claude" / "skills"
CANONICAL_ROOT = ROOT / ".agents" / "skills"
SETTINGS_PATH = ROOT / ".claude" / "settings.json"

POINTERS = {
    "fyp-phase-execution": False,
    "worktree-task": False,
    "fyp-quality-gate": True,
    "integration-safe-development": True,
}
MANUAL_ONLY_LINE = "disable-model-invocation: true"
BRANCH_AND_WORKTREE_ASK = (
    "git branch *",
    "git checkout*",
    "git switch*",
    "git merge*",
    "git rebase*",
    "git reset*",
    "git pull*",
    "git cherry-pick*",
    "git revert*",
    "git am*",
    "git update-ref*",
    "git symbolic-ref*",
    "git filter-branch*",
    "git worktree add*",
    "git worktree move*",
    "git worktree remove*",
    "git worktree prune*",
    "git worktree lock*",
    "git worktree unlock*",
    "git worktree repair*",
)
MAX_POINTER_LINES = 30


def _frontmatter_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise AssertionError("missing YAML frontmatter")
    return lines[1 : lines.index("---", 1)]


def _field_line(lines: list[str], key: str) -> str:
    matches = [line for line in lines if line.startswith(f"{key}: ")]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {key} line")
    return matches[0]


class ClaudeSkillPointerTests(unittest.TestCase):
    def test_pointer_set_is_exactly_the_canonical_workflows(self) -> None:
        names = {path.name for path in POINTER_ROOT.iterdir()}
        self.assertEqual(names, set(POINTERS))
        for name in POINTERS:
            with self.subTest(skill=name):
                self.assertTrue((CANONICAL_ROOT / name / "SKILL.md").is_file())
                contents = sorted(path.name for path in (POINTER_ROOT / name).iterdir())
                self.assertEqual(contents, ["SKILL.md"])

    def test_metadata_matches_canonical_skill(self) -> None:
        for name, manual_only in POINTERS.items():
            with self.subTest(skill=name):
                pointer = _frontmatter_lines(self._pointer_text(name))
                canonical = _frontmatter_lines(
                    (CANONICAL_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
                )
                self.assertEqual(_field_line(pointer, "name"), f"name: {name}")
                self.assertEqual(_field_line(canonical, "name"), f"name: {name}")
                self.assertEqual(
                    _field_line(pointer, "description"),
                    _field_line(canonical, "description"),
                )
                expected = [f"name: {name}", _field_line(canonical, "description")]
                if manual_only:
                    expected.append(MANUAL_ONLY_LINE)
                self.assertEqual(pointer, expected)

    def test_only_review_and_integration_are_manual_only(self) -> None:
        for name, manual_only in POINTERS.items():
            with self.subTest(skill=name):
                frontmatter = _frontmatter_lines(self._pointer_text(name))
                self.assertEqual(MANUAL_ONLY_LINE in frontmatter, manual_only)

    def test_body_defers_to_canonical_skill_in_current_checkout(self) -> None:
        for name in POINTERS:
            with self.subTest(skill=name):
                text = self._pointer_text(name)
                self.assertIn(f"`.agents/skills/{name}/SKILL.md`", text)
                self.assertIn("`git rev-parse --show-toplevel`", text)
                self.assertIn("never the primary checkout", text)
                self.assertIn("adds no instructions, scope or authority", text)
                self.assertLessEqual(len(text.splitlines()), MAX_POINTER_LINES)

    @staticmethod
    def _pointer_text(name: str) -> str:
        return (POINTER_ROOT / name / "SKILL.md").read_text(encoding="utf-8")


class SharedClaudeSettingsTests(unittest.TestCase):
    def test_shared_settings_do_not_exclude_instruction_files(self) -> None:
        # claudeMdExcludes globs match absolute paths, so a snapshot pattern such as
        # **/tmp/**/AGENTS.md would also drop the live AGENTS.md of a checkout under tmp/.
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("claudeMdExcludes", settings)

    def test_branch_and_worktree_mutations_ask_in_both_shells(self) -> None:
        ask = _permissions()["ask"]
        for tool in ("Bash", "PowerShell"):
            with self.subTest(tool=tool):
                missing = set(BRANCH_AND_WORKTREE_ASK) - _shell_patterns(ask, tool)
                self.assertEqual(missing, set())

    def test_deny_and_ask_rules_have_shell_parity(self) -> None:
        permissions = _permissions()
        for kind in ("deny", "ask"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    _shell_patterns(permissions[kind], "Bash"),
                    _shell_patterns(permissions[kind], "PowerShell"),
                )


def _permissions() -> dict[str, list[str]]:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    permissions: dict[str, list[str]] = settings["permissions"]
    return permissions


def _shell_patterns(rules: list[str], tool: str) -> set[str]:
    prefix = f"{tool}("
    return {rule[len(prefix) : -1] for rule in rules if rule.startswith(prefix)}


if __name__ == "__main__":
    unittest.main()
