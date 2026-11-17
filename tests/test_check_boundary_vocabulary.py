from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_boundary_vocabulary.py"
SPEC = importlib.util.spec_from_file_location("check_boundary_vocabulary_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load the vocabulary check")
VOCAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VOCAB
SPEC.loader.exec_module(VOCAB)

# A stand-in generator with the real generator's interface (``build() -> str``). It derives the
# vocabulary from one backend source file, so tests can add drift by editing that file.
FAKE_GENERATOR = '''
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
WORDS = HERE.parent / "backend" / "app" / "words.txt"


def build():
    words = sorted({line.strip() for line in WORDS.read_text("utf-8").splitlines() if line.strip()})
    # Like the real generators: non-ASCII words are written as-is, not escaped.
    return json.dumps({"code_vocabulary": words, "version": 1}, indent=1, ensure_ascii=False) + "\\n"
'''


PRIVACY_FILE = "apps/assistant/ai_assistant/privacy_vocabulary.json"
# A stand-in for the D-142 privacy generator: it derives its words from the stored D-094 file.
FAKE_PRIVACY_GENERATOR = '''
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BOUNDARY = HERE / "ai_assistant" / "synthetic_boundary.json"


def build():
    stored = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    return json.dumps({"words": sorted(stored["code_vocabulary"])}, indent=1) + "\\n"
'''


class PureRuleTests(unittest.TestCase):
    def test_drift_reports_added_and_removed_words_and_other_changes(self) -> None:
        stored = {"code_vocabulary": ["a", "b"], "version": 1, "same": ["x"]}
        generated = {"code_vocabulary": ["b", "c"], "version": 2, "same": ["x"]}
        result = VOCAB.drift(stored, generated)
        self.assertEqual(result["code_vocabulary"], {"added": ["c"], "removed": ["a"]})
        self.assertEqual(set(result), {"code_vocabulary", "version"})
        # A non-list key is fingerprinted, so a further change to it is a different drift.
        self.assertNotEqual(
            result["version"], VOCAB.drift(stored, {**generated, "version": 3})["version"]
        )
        self.assertEqual(VOCAB._summary(result)["version"], {"added": 0, "removed": 0, "other": 1})

    def test_a_word_list_on_one_side_only_counts_against_empty(self) -> None:
        self.assertEqual(
            VOCAB.drift({}, {"words": ["a"]}), {"words": {"added": ["a"], "removed": []}}
        )
        self.assertEqual(
            VOCAB.drift({"words": ["a"]}, {}), {"words": {"added": [], "removed": ["a"]}}
        )

    def test_classify_covers_every_outcome(self) -> None:
        stale = {"code_vocabulary": {"added": ["c"], "removed": []}}
        other = {"code_vocabulary": {"added": ["d"], "removed": []}}
        cases = [
            ({"head_drift": {}, "base_drift": None, "boundary_changed": False}, "CURRENT"),
            ({"head_drift": {}, "base_drift": None, "boundary_changed": True}, "REVIEW_REQUIRED"),
            ({"head_drift": stale, "base_drift": stale, "boundary_changed": False},
             "PRE_EXISTING_DRIFT"),
            ({"head_drift": stale, "base_drift": other, "boundary_changed": False},
             "FAIL_NEW_DRIFT"),
            ({"head_drift": stale, "base_drift": {}, "boundary_changed": False}, "FAIL_NEW_DRIFT"),
            ({"head_drift": stale, "base_drift": stale, "boundary_changed": True},
             "FAIL_CHANGED_NOT_CURRENT"),
            ({"head_drift": None, "base_drift": None, "boundary_changed": False},
             "FAIL_UNVERIFIABLE"),
            ({"head_drift": stale, "base_drift": None, "boundary_changed": False},
             "FAIL_UNVERIFIABLE"),
        ]
        for kwargs, expected in cases:
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                self.assertEqual(VOCAB.classify(**kwargs), expected)


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.repo = Path(self._dir.name)
        self._git("init", "-b", "main")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "Vocabulary Test")
        self._git("config", "core.autocrlf", "false")
        self._write("apps/assistant/scripts/build_synthetic_boundary.py", FAKE_GENERATOR)
        self._write("apps/backend/app/words.txt", "alpha\nbeta\n")
        self._regenerate()
        self._commit("baseline")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self._git("checkout", "-b", "feature")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout

    def _write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def _regenerate(self) -> None:
        words = sorted(
            {w for w in (self.repo / "apps/backend/app/words.txt").read_text("utf-8").split() if w}
        )
        self._write(
            VOCAB.BOUNDARY_FILE,
            json.dumps({"code_vocabulary": words, "version": 1}, indent=1) + "\n",
        )

    def _commit(self, message: str) -> None:
        self._git("add", "-A")
        self._git("commit", "-m", message)

    def _status(self) -> dict[str, object]:
        return VOCAB.evaluate(self.repo, "origin/main")

    def test_current_file_passes(self) -> None:
        self.assertEqual(self._status()["status"], "CURRENT")

    def test_new_source_words_without_regeneration_fail(self) -> None:
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\n")
        self._commit("add a backend word")
        report = self._status()
        self.assertEqual(report["status"], "FAIL_NEW_DRIFT")
        self.assertEqual(report["head_drift"], {"code_vocabulary": {"added": 1, "removed": 0}})
        self.assertEqual(report["base_drift"], {})

    def test_uncommitted_source_change_is_seen(self) -> None:
        self._write("apps/backend/app/words.txt", "alpha\n")
        self.assertEqual(self._status()["status"], "FAIL_NEW_DRIFT")

    def test_regenerated_file_requires_review_and_reports_the_word_delta(self) -> None:
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\ndelta\n")
        self._regenerate()
        self._commit("add words and regenerate")
        report = self._status()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            report["file_word_delta"], {"code_vocabulary": {"added": 2, "removed": 0}}
        )

    def test_edited_but_stale_file_fails(self) -> None:
        self._write(
            VOCAB.BOUNDARY_FILE,
            json.dumps({"code_vocabulary": ["alpha"], "version": 1}, indent=1) + "\n",
        )
        self._commit("hand edit")
        self.assertEqual(self._status()["status"], "FAIL_CHANGED_NOT_CURRENT")

    def test_drift_already_on_the_base_only_warns(self) -> None:
        self._git("checkout", "main")
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\n")
        self._commit("stale main")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self._git("checkout", "-b", "unrelated")
        self._write("README.md", "docs only\n")
        self._commit("unrelated change")
        self.assertEqual(self._status()["status"], "PRE_EXISTING_DRIFT")

    def test_more_drift_on_top_of_a_stale_base_fails(self) -> None:
        self._git("checkout", "main")
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\n")
        self._commit("stale main")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self._git("checkout", "-b", "more")
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\nepsilon\n")
        self._commit("more words")
        self.assertEqual(self._status()["status"], "FAIL_NEW_DRIFT")

    def test_non_ascii_vocabulary_builds_on_any_console_code_page(self) -> None:
        # "Ω" and "→" are outside Windows cp1252; the child must still write UTF-8.
        self._write("apps/backend/app/words.txt", "alpha\nbeta\nΩmega\n→\n")
        self._regenerate()
        self._commit("non-ascii words")
        report = self._status()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            report["file_word_delta"], {"code_vocabulary": {"added": 2, "removed": 0}}
        )

    def test_broken_generator_fails_closed(self) -> None:
        self._write("apps/assistant/scripts/build_synthetic_boundary.py", "raise SystemExit(3)\n")
        self.assertEqual(self._status()["status"], "FAIL_UNVERIFIABLE")

    def test_renamed_or_deleted_generator_fails(self) -> None:
        self._git("mv", "apps/assistant/scripts/build_synthetic_boundary.py",
                  "apps/assistant/scripts/build_boundary_renamed.py")
        self._write(VOCAB.BOUNDARY_FILE, json.dumps({"code_vocabulary": ["unreviewed"]}) + "\n")
        self._commit("rename generator and edit the vocabulary")
        report = self._status()
        self.assertEqual(report["status"], "FAIL_GENERATOR_REMOVED")
        self.assertEqual(VOCAB.main(["--root", str(self.repo)]), 1)

    def test_removed_privacy_generator_fails(self) -> None:
        self._add_privacy_artifact()
        self._commit("add privacy vocabulary")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self._git("rm", "-q", "apps/assistant/scripts/build_privacy_vocabulary.py")
        self._commit("drop the privacy generator")
        report = self._status()
        self.assertEqual(report["status"], "FAIL_GENERATOR_REMOVED")
        self.assertEqual(report["artifacts"][PRIVACY_FILE]["status"], "FAIL_GENERATOR_REMOVED")

    def test_vocabulary_without_any_generator_is_unverifiable(self) -> None:
        self._write(PRIVACY_FILE, json.dumps({"words": ["orphan"]}) + "\n")
        self._commit("a vocabulary with no generator anywhere")
        report = self._status()
        self.assertEqual(report["status"], "FAIL_UNVERIFIABLE")
        self.assertEqual(report["artifacts"][PRIVACY_FILE]["status"], "FAIL_UNVERIFIABLE")

    def test_history_without_any_generator_is_out_of_scope(self) -> None:
        self._git("rm", "-q", "apps/assistant/scripts/build_synthetic_boundary.py", VOCAB.BOUNDARY_FILE)
        self._commit("before the boundary existed")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.assertEqual(self._status()["status"], "CURRENT")

    def test_check_never_writes_the_boundary_file(self) -> None:
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\n")
        before = (self.repo / VOCAB.BOUNDARY_FILE).read_bytes()
        self._status()
        self.assertEqual((self.repo / VOCAB.BOUNDARY_FILE).read_bytes(), before)

    def _add_privacy_artifact(self) -> None:
        self._write("apps/assistant/scripts/build_privacy_vocabulary.py", FAKE_PRIVACY_GENERATOR)
        self._regenerate_privacy()

    def _regenerate_privacy(self) -> None:
        stored = json.loads((self.repo / VOCAB.BOUNDARY_FILE).read_text(encoding="utf-8"))
        self._write(
            PRIVACY_FILE,
            json.dumps({"words": sorted(stored["code_vocabulary"])}, indent=1) + "\n",
        )

    def test_privacy_artifact_is_checked_after_the_boundary(self) -> None:
        self._add_privacy_artifact()
        self._commit("add privacy vocabulary")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.assertEqual(self._status()["status"], "CURRENT")
        self.assertEqual(set(self._status()["artifacts"]), {VOCAB.BOUNDARY_FILE, PRIVACY_FILE})

        # Regenerating the boundary alone leaves the derived privacy vocabulary stale.
        self._write("apps/backend/app/words.txt", "alpha\nbeta\ngamma\n")
        self._regenerate()
        self._commit("boundary only")
        report = self._status()
        self.assertEqual(report["status"], "FAIL_NEW_DRIFT")
        self.assertEqual(report["artifacts"][VOCAB.BOUNDARY_FILE]["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["artifacts"][PRIVACY_FILE]["status"], "FAIL_NEW_DRIFT")

        # Regenerating both, in order, needs one review covering both word deltas.
        self._regenerate_privacy()
        self._commit("privacy too")
        report = self._status()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            report["artifacts"][PRIVACY_FILE]["file_word_delta"],
            {"words": {"added": 1, "removed": 0}},
        )

    def test_main_exit_code_follows_the_outcome(self) -> None:
        self.assertEqual(VOCAB.main(["--root", str(self.repo)]), 0)
        self._write("apps/backend/app/words.txt", "alpha\nbeta\nzeta\n")
        self.assertEqual(VOCAB.main(["--root", str(self.repo)]), 1)


if __name__ == "__main__":
    unittest.main()
