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
MODULE_PATH = ROOT / "scripts" / "check_architecture.py"
SPEC = importlib.util.spec_from_file_location(
    "check_architecture_under_test", MODULE_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load check_architecture")
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)


class ArchitectureCheckerTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(
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
        self._git(root, "config", "user.email", "architecture@example.invalid")
        self._git(root, "config", "user.name", "Architecture Test")
        app = root / "apps" / "backend" / "app"
        (app / "domain").mkdir(parents=True)
        (app / "domain" / "ownership.py").write_text("OWNER = True\n", encoding="utf-8")
        (app / "composition.py").write_text(
            "from app.connectors.mock_goldtier import MockGoldTierConnector\n"
            "TARGET = MockGoldTierConnector()\n",
            encoding="utf-8",
        )
        (app / "config.py").write_text(
            "from typing import Literal\n"
            "class Settings:\n"
            '    goldtier_connector_mode: Literal["mock"] = "mock"\n',
            encoding="utf-8",
        )
        (app / "main.py").write_text(
            "from app.persistence.composition import build_persistence_bundle\n",
            encoding="utf-8",
        )
        (app / "api_cases.py").write_text(
            "from app.services.onboarding import OnboardingService\n", encoding="utf-8"
        )
        frontend = root / "apps" / "frontend" / "src"
        frontend.mkdir(parents=True)
        (frontend / "main.tsx").write_text(
            "export const ok = true;\n", encoding="utf-8"
        )
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "fixture")
        return temporary, root

    def _rules_after(self, relative: str, content: str) -> set[str]:
        temporary, root = self._fixture()
        try:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self._git(root, "add", relative)
            return {finding.rule for finding in CHECK.check(root)}
        finally:
            temporary.cleanup()

    def test_accepts_current_repository_baseline(self) -> None:
        self.assertEqual(CHECK.check(ROOT), [])

    def test_catches_direct_api_mongo_import_form(self) -> None:
        self.assertIn(
            "API_PERSISTENCE_BOUNDARY",
            self._rules_after(
                "apps/backend/app/api_cases.py",
                "from app.persistence.mongo_case_store import MongoCaseStore\n",
            ),
        )

    def test_catches_from_package_import_of_concrete_persistence_module(self) -> None:
        self.assertIn(
            "API_PERSISTENCE_BOUNDARY",
            self._rules_after(
                "apps/backend/app/api_cases.py",
                "from app.persistence import mongo_case_store as store\n",
            ),
        )

    def test_allows_composition_root_persistence_wiring(self) -> None:
        self.assertNotIn(
            "API_PERSISTENCE_BOUNDARY",
            self._rules_after(
                "apps/backend/app/main.py",
                "from app.persistence.mongo_case_store import MongoCaseStore\n",
            ),
        )

    def test_catches_frontend_persistence_import(self) -> None:
        self.assertIn(
            "FRONTEND_BACKEND_BOUNDARY",
            self._rules_after(
                "apps/frontend/src/main.tsx",
                'import { MongoCaseStore } from "app.persistence";\n',
            ),
        )

    def test_allows_harmless_frontend_text_comments_and_similar_names(self) -> None:
        rules = self._rules_after(
            "apps/frontend/src/main.tsx",
            "// app.persistence must remain backend-only\n"
            '/* import { Store } from "app.persistence"; */\n'
            'const displayCopy = "app.persistence";\n'
            "const mongo_case_store_status = 'unavailable';\n"
            'import { persistenceStatus } from "./persistenceStatus";\n',
        )
        self.assertNotIn("FRONTEND_BACKEND_BOUNDARY", rules)

    def test_catches_second_domain_ownership_owner(self) -> None:
        self.assertIn(
            "OWNERSHIP_CANONICAL_OWNER",
            self._rules_after(
                "apps/backend/app/domain/ownership_v2.py", "SECOND = True\n"
            ),
        )

    def test_catches_dormant_bizfile_composition(self) -> None:
        self.assertIn(
            "DORMANT_BIZFILE",
            self._rules_after(
                "apps/backend/app/composition.py",
                "from app.connectors.acra_bizfile_sandbox import AcraBizfileConnector\n"
                "from app.connectors.mock_goldtier import MockGoldTierConnector\n"
                "TARGET = MockGoldTierConnector()\n",
            ),
        )

    def test_allows_goldtier_formatting_only_change(self) -> None:
        rules = self._rules_after(
            "apps/backend/app/config.py",
            "from typing import Literal\n"
            "class Settings:\n"
            "    goldtier_connector_mode: (\n"
            "        Literal['mock']\n"
            "    ) = 'mock'\n",
        )
        self.assertNotIn("MOCK_GOLDTIER_ONLY", rules)

    def test_allows_mock_goldtier_import_alias_in_composition(self) -> None:
        rules = self._rules_after(
            "apps/backend/app/composition.py",
            "from app.connectors.mock_goldtier import MockGoldTierConnector as Target\n"
            "CONNECTOR = Target()\n",
        )
        self.assertNotIn("MOCK_GOLDTIER_ONLY", rules)

    def test_catches_semantic_live_goldtier_configuration(self) -> None:
        self.assertIn(
            "MOCK_GOLDTIER_ONLY",
            self._rules_after(
                "apps/backend/app/config.py",
                "from typing import Literal\n"
                "class Settings:\n"
                '    goldtier_connector_mode: Literal["mock", "live"] = "mock"\n',
            ),
        )

    def test_checker_does_not_read_env_untracked_or_mutate_repository(self) -> None:
        temporary, root = self._fixture()
        try:
            env_file = root / ".env"
            untracked = root / "untracked-provider.py"
            env_file.write_text("SECRET=DO_NOT_PRINT_ME\n", encoding="utf-8")
            untracked.write_text("app.persistence\n", encoding="utf-8")
            head_before = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            status_before = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            real_read = CHECK._read_text

            def guarded_read(path: Path) -> str:
                if path.name in {".env", "untracked-provider.py"}:
                    raise AssertionError("untracked secret access")
                return real_read(path)

            output = io.StringIO()
            with (
                patch.object(CHECK, "_read_text", side_effect=guarded_read),
                patch.dict(os.environ, {"ARCH_SECRET_SENTINEL": "DO_NOT_PRINT_ME"}),
                redirect_stdout(output),
            ):
                result = CHECK.main(["--root", str(root)])
            head_after = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            status_after = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(result, 0)
            self.assertEqual((head_before, status_before), (head_after, status_after))
            self.assertEqual(
                env_file.read_text(encoding="utf-8"), "SECRET=DO_NOT_PRINT_ME\n"
            )
            self.assertNotIn("DO_NOT_PRINT_ME", output.getvalue())
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
