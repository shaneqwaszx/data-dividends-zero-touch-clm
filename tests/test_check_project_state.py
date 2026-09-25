from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check_project_state.py"
SPEC = importlib.util.spec_from_file_location(
    "check_project_state_under_test", MODULE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load check_project_state")
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


class ProjectStateCheckerTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        fixture_root = ROOT / "tmp"
        fixture_root.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=fixture_root)
        root = Path(temporary.name)
        self._git(root, "init", "-b", "main")
        self._git(root, "config", "user.email", "state@example.invalid")
        self._git(root, "config", "user.name", "State Test")
        (root / "docs").mkdir()
        app = root / "apps" / "backend" / "app"
        app.mkdir(parents=True)
        (app / "config.py").write_text(
            'from typing import Literal\nclass Settings:\n    acra_connector_mode: Literal["mock", "sandbox"] = "mock"\n    goldtier_connector_mode: Literal["mock", "sandbox"] = "mock"\n    idp_connector_mode: Literal["mock", "local_pdf_text"] = "local_pdf_text"\n',
            encoding="utf-8",
        )
        (app / "composition.py").write_text(
            "MockGoldTierConnector\nGoldTierXpiSandboxConnector\n",
            encoding="utf-8",
        )
        persistence = app / "persistence"
        persistence.mkdir()
        (persistence / "models.py").write_text(
            "CASE_SNAPSHOT_SCHEMA_VERSION = 3\n", encoding="utf-8"
        )
        (persistence / "composition.py").write_text(
            "bootstrap_administration(teams, profiles, hashes)\n", encoding="utf-8"
        )
        services = app / "services"
        services.mkdir()
        (services / "authentication.py").write_text(
            "class AuthenticationService:\n"
            "    def __init__(self):\n"
            "        self._sessions = {}\n",
            encoding="utf-8",
        )
        config = app / "config.py"
        config.write_text(
            config.read_text(encoding="utf-8")
            + '    clm_persistence_mode: Literal["memory", "mongo"] = "memory"\n',
            encoding="utf-8",
        )
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "source")
        sha = self._git(root, "rev-parse", "HEAD").stdout.strip()
        baseline_date = self._git(
            root, "show", "-s", "--format=%cs", sha
        ).stdout.strip()
        self._git(root, "update-ref", "refs/remotes/origin/main", sha)
        metadata = {
            "schema_version": 1,
            "case_envelope_schema_version": 3,
            "verified_date": baseline_date,
            "verified_main_sha": sha,
            "verification_status": "verified-against-main",
            "providers": {
                "registry": {"name": "ACRA", "mode": "mock", "classification": "MOCK"},
                "registry_api_marketplace_mock": {
                    "name": "ACRA_API_MARKETPLACE_MOCK",
                    "mode": "api_marketplace_mock",
                    "classification": "MOCK",
                },
                "registry_sandbox": {
                    "name": "ACRA_GENERIC_SANDBOX",
                    "mode": "sandbox",
                    "classification": "PARTIAL",
                },
                "registry_bizfile": {
                    "name": "ACRA_BIZFILE",
                    "mode": "dormant",
                    "classification": "DORMANT",
                },
                "idp": {
                    "name": "LOCAL_PDF_TEXT",
                    "mode": "local_pdf_text",
                    "classification": "LOCAL",
                },
                "idp_fault": {
                    "name": "MOCK_IDP",
                    "mode": "mock",
                    "classification": "MOCK",
                },
                "ownership": {
                    "name": "DECIMAL_GRAPH_ENGINE",
                    "mode": "local",
                    "classification": "LOCAL",
                },
                "target": {
                    "name": "GOLDTIER",
                    "mode": "mock",
                    "classification": "MOCK",
                },
                "target_sandbox": {
                    "name": "GOLDTIER_XPI",
                    "mode": "sandbox",
                    "classification": "PARTIAL",
                },
            },
            "persistence": {"default": "memory", "supported": ["memory", "mongo"]},
            "identity": {
                "account_source": "bootstrap_repositories",
                "session_store": "process_local",
                "production_sso": "not_implemented",
            },
            "workflow_engine": {"camunda": "not_implemented"},
        }
        sections = "\n".join(sorted(CHECK.REQUIRED_SECTIONS))
        (root / "docs" / "PROJECT_STATE.md").write_text(
            sections + "\n```json project-state\n" + json.dumps(metadata) + "\n```\n",
            encoding="utf-8",
        )
        self._git(root, "add", "docs/PROJECT_STATE.md")
        self._git(root, "commit", "-m", "state")
        return temporary, root

    def _mutate_metadata(self, root: Path, mutation: object) -> list[str]:
        path = root / "docs" / "PROJECT_STATE.md"
        text = path.read_text(encoding="utf-8")
        match = CHECK.STATE_BLOCK.search(text)
        self.assertIsNotNone(match)
        assert match is not None
        metadata = json.loads(match.group("body"))
        assert callable(mutation)
        mutation(metadata)
        start, end = match.span("body")
        path.write_text(
            text[:start] + json.dumps(metadata) + text[end:], encoding="utf-8"
        )
        return CHECK.validate(root)

    def _add_to_fixture_index(self, root: Path, relative_path: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
        self._git(root, "add", relative_path)

    def test_accepts_current_repository_baseline(self) -> None:
        self.assertEqual(CHECK.validate(ROOT), [])

    def test_accepts_synthetic_baseline_and_does_not_require_head_equality(
        self,
    ) -> None:
        temporary, root = self._fixture()
        try:
            self._git(root, "commit", "--allow-empty", "-m", "feature head")
            self.assertEqual(CHECK.validate(root), [])
        finally:
            temporary.cleanup()

    def test_accepts_detached_feature_head_ahead_of_baseline(self) -> None:
        temporary, root = self._fixture()
        try:
            self._git(root, "commit", "--allow-empty", "-m", "feature head")
            self._git(root, "switch", "--detach")
            self.assertEqual(CHECK.validate(root), [])
        finally:
            temporary.cleanup()

    def test_allows_origin_main_descendant_of_verified_baseline(self) -> None:
        temporary, root = self._fixture()
        try:
            self._git(root, "commit", "--allow-empty", "-m", "main advances")
            self._git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
            self.assertEqual(CHECK.validate(root), [])
        finally:
            temporary.cleanup()

    def test_catches_verified_baseline_not_ancestor_of_origin_main(self) -> None:
        temporary, root = self._fixture()
        try:
            tree = self._git(root, "write-tree").stdout.strip()
            unrelated = self._git(
                root, "commit-tree", tree, "-m", "unrelated main"
            ).stdout.strip()
            self._git(root, "update-ref", "refs/remotes/origin/main", unrelated)
            failures = CHECK.validate(root)
            self.assertTrue(
                any("reachable from origin/main" in item for item in failures), failures
            )
        finally:
            temporary.cleanup()

    def test_ordinary_prose_edits_do_not_change_validation(self) -> None:
        temporary, root = self._fixture()
        try:
            path = root / "docs" / "PROJECT_STATE.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\nOrdinary prose changed.\n",
                encoding="utf-8",
            )
            self.assertEqual(CHECK.validate(root), [])
        finally:
            temporary.cleanup()

    def test_catches_wrong_metadata_schema_version(self) -> None:
        temporary, root = self._fixture()
        try:
            failures = self._mutate_metadata(
                root, lambda value: value.__setitem__("schema_version", 999)
            )
            self.assertTrue(
                any("schema_version" in item for item in failures), failures
            )
        finally:
            temporary.cleanup()

    def test_catches_wrong_case_envelope_schema_version(self) -> None:
        temporary, root = self._fixture()
        try:
            failures = self._mutate_metadata(
                root,
                lambda value: value.__setitem__("case_envelope_schema_version", 999),
            )
            self.assertTrue(any("case envelope" in item for item in failures), failures)
        finally:
            temporary.cleanup()

    def test_catches_malformed_and_nonexistent_baseline_sha(self) -> None:
        temporary, root = self._fixture()
        try:
            malformed = self._mutate_metadata(
                root, lambda value: value.__setitem__("verified_main_sha", "not-a-sha")
            )
            self.assertTrue(any("40-hex" in item for item in malformed), malformed)
            nonexistent = self._mutate_metadata(
                root, lambda value: value.__setitem__("verified_main_sha", "0" * 40)
            )
            self.assertTrue(any("exist" in item for item in nonexistent), nonexistent)
        finally:
            temporary.cleanup()

    def test_catches_invalid_verification_date(self) -> None:
        temporary, root = self._fixture()
        try:
            failures = self._mutate_metadata(
                root, lambda value: value.__setitem__("verified_date", "15/09/2026")
            )
            self.assertTrue(any("verified_date" in item for item in failures), failures)
        finally:
            temporary.cleanup()

    def test_catches_verification_date_before_baseline_commit(self) -> None:
        temporary, root = self._fixture()
        try:
            failures = self._mutate_metadata(
                root, lambda value: value.__setitem__("verified_date", "2000-01-01")
            )
            self.assertTrue(any("predates" in item for item in failures), failures)
        finally:
            temporary.cleanup()

    def test_allows_one_day_date_tolerance_for_commit_timezone(self) -> None:
        temporary, root = self._fixture()
        try:
            commit_date = date.fromisoformat(
                self._git(
                    root, "show", "-s", "--format=%cs", "origin/main"
                ).stdout.strip()
            )
            tolerated_date = (commit_date - timedelta(days=1)).isoformat()
            failures = self._mutate_metadata(
                root,
                lambda value: value.__setitem__("verified_date", tolerated_date),
            )
            self.assertEqual(failures, [])
        finally:
            temporary.cleanup()

    def test_catches_wrong_persistence_default_and_supported_modes(self) -> None:
        temporary, root = self._fixture()
        try:
            wrong_default = self._mutate_metadata(
                root,
                lambda value: value["persistence"].__setitem__("default", "mongo"),
            )
            self.assertTrue(
                any("persistence default" in item for item in wrong_default)
            )
            wrong_supported = self._mutate_metadata(
                root,
                lambda value: value["persistence"].__setitem__("supported", ["memory"]),
            )
            self.assertTrue(
                any("persistence modes" in item for item in wrong_supported)
            )
        finally:
            temporary.cleanup()

    def test_catches_wrong_identity_classification(self) -> None:
        temporary, root = self._fixture()
        try:
            failures = self._mutate_metadata(
                root,
                lambda value: value["identity"].__setitem__("production_sso", "active"),
            )
            self.assertTrue(any("identity" in item for item in failures), failures)
        finally:
            temporary.cleanup()

    def test_catches_deliberate_live_goldtier_mismatch(self) -> None:
        temporary, root = self._fixture()
        try:
            failures = self._mutate_metadata(
                root,
                lambda value: value["providers"]["target"].__setitem__(
                    "classification", "LIVE"
                ),
            )
            self.assertTrue(
                any("goldtier" in failure.lower() for failure in failures), failures
            )
        finally:
            temporary.cleanup()

    def test_allows_camunda_named_files_in_exact_backend_test_tree(self) -> None:
        temporary, root = self._fixture()
        try:
            self._add_to_fixture_index(
                root, "apps/backend/tests/test_camunda_observer_contract.py"
            )
            self._add_to_fixture_index(
                root, "apps/backend/tests/camunda_observer_contract_support.py"
            )
            self.assertEqual(CHECK.validate(root), [])
        finally:
            temporary.cleanup()

    def test_rejects_camunda_named_files_outside_exact_backend_test_tree(self) -> None:
        runtime_paths = (
            "apps/backend/app/camunda_worker.py",
            "apps/frontend/src/camundaRuntime.ts",
            "apps/backend/app/tests_camunda_runtime.py",
        )
        for runtime_path in runtime_paths:
            with self.subTest(runtime_path=runtime_path):
                temporary, root = self._fixture()
                try:
                    self._add_to_fixture_index(root, runtime_path)
                    self.assertIn(
                        "Camunda runtime files exist but PROJECT_STATE says "
                        "not_implemented",
                        CHECK.validate(root),
                    )
                finally:
                    temporary.cleanup()

    def test_checker_does_not_read_env_untracked_or_mutate_repository(self) -> None:
        temporary, root = self._fixture()
        try:
            env_file = root / ".env"
            untracked = root / "untracked-private.txt"
            env_file.write_text("SECRET=DO_NOT_PRINT_ME\n", encoding="utf-8")
            untracked.write_text("UNTRACKED_SENTINEL\n", encoding="utf-8")
            before = (
                self._git(root, "rev-parse", "HEAD").stdout,
                self._git(root, "status", "--porcelain").stdout,
                env_file.read_bytes(),
                untracked.read_bytes(),
            )
            real_read = CHECK._read_text

            def guarded_read(path: Path) -> str:
                if path.name in {".env", "untracked-private.txt"}:
                    raise AssertionError("untracked secret access")
                return real_read(path)

            output = io.StringIO()
            with (
                patch.object(CHECK, "_read_text", side_effect=guarded_read),
                patch.dict(os.environ, {"STATE_SECRET_SENTINEL": "DO_NOT_PRINT_ME"}),
                redirect_stdout(output),
            ):
                result = CHECK.main(["--root", str(root)])
            after = (
                self._git(root, "rev-parse", "HEAD").stdout,
                self._git(root, "status", "--porcelain").stdout,
                env_file.read_bytes(),
                untracked.read_bytes(),
            )
            self.assertEqual(result, 0)
            self.assertEqual(before, after)
            self.assertNotIn("DO_NOT_PRINT_ME", output.getvalue())
            self.assertNotIn("UNTRACKED_SENTINEL", output.getvalue())
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
