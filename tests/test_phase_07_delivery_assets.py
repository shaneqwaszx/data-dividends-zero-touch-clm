"""Repository-level Phase 07 handoff and synthetic-fixture checks."""

import hashlib
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase07DeliveryAssetsTests(unittest.TestCase):
    def test_required_handoff_documents_exist(self) -> None:
        required = (
            "docs/uat/PHASE_07_UAT_CATALOGUE.md",
            "docs/demo/SPONSOR_DEMO_SCRIPT.md",
            "docs/demo/DEMO_RUNBOOK.md",
            "docs/integration/INTEGRATION_HANDOFF.md",
            "docs/integration/PROVIDER_REPLACEMENT_GUIDE.md",
            "docs/integration/ADAPTER_CONFORMANCE_CHECKLIST.md",
            "docs/integration/API_HANDOFF.md",
            "docs/integration/CONFIGURATION_REFERENCE.md",
            "docs/integration/FAILURE_RECOVERY_GUIDE.md",
            "docs/architecture/FINAL_POC_ARCHITECTURE.md",
            "docs/security/POC_SECURITY_BOUNDARIES.md",
            "docs/sponsor-questions/PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md",
            "docs/FINAL_DELIVERABLE_INDEX.md",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_synthetic_document_pack_is_explicit_and_bounded(self) -> None:
        fixture_root = ROOT / "apps/backend/tests/fixtures/uat"
        expected = {
            "clean-company-profile.pdf",
            "address-mismatch.pdf",
            "legal-name-mismatch.pdf",
            "missing-field.pdf",
            "low-confidence.pdf",
            "no-text.pdf",
            "cycle-uen-clean.pdf",
            "second-case-isolation.pdf",
            "invalid-document.pdf",
            "garden-business-clean-onboarding-profile.pdf",
            "garden-business-conflicting-onboarding-profile.pdf",
            "garden-partnership-reviewed-client.pdf",
            "multiple-owner-demo-client.pdf",
            "five-layer-marketplace-hybrid-client.pdf",
            "garden-d076-ownership-declaration-client.pdf",
            "zero-touch-database/orion-synthetic-technologies-client.pdf",
            "zero-touch-database/pacific-synthetic-ledger-client.pdf",
            "zero-touch-database/straits-synthetic-holdings-client.pdf",
            "zero-touch-database/meridian-synthetic-infrastructure-client.pdf",
            "zero-touch-database/aurora-sponsor-demo-registry-annex.pdf",
            "zero-touch-database/pacific-sponsor-demo-registry-annex.pdf",
            "zero-touch-database/straits-sponsor-demo-registry-annex.pdf",
            "zero-touch-database/meridian-sponsor-demo-registry-annex.pdf",
        }
        self.assertEqual({path.relative_to(fixture_root).as_posix() for path in fixture_root.rglob("*.pdf") if path.name not in {"demo-alpha-scanned.pdf", "demo-beta-scanned.pdf", "demo-gamma-scanned.pdf", "demo-delta-scanned.pdf", "demo-government-scanned.pdf", "demo-gamma-partnership-agreement.pdf", "demo-parks-government-status.pdf"}}, expected)
        index = (fixture_root / "README.md").read_text(encoding="utf-8")
        indexed = dict(
            re.findall(
                r"^\| \x60([^\x60]+\.pdf)\x60 \|.*?\| \x60([a-f0-9]{64})\x60 \|",
                index,
                re.MULTILINE,
            )
        )
        self.assertEqual(set(indexed), expected)
        for name in expected:
            self.assertEqual(
                indexed[name],
                hashlib.sha256((fixture_root / name).read_bytes()).hexdigest(),
            )

        for path in fixture_root.glob("*.pdf"):
            with self.subTest(path=path.name):
                content = path.read_bytes()
                self.assertLess(len(content), 4096)
                if path.name == "invalid-document.pdf":
                    self.assertFalse(content.startswith(b"%PDF-"))
                elif path.name == "no-text.pdf":
                    self.assertTrue(content.startswith(b"%PDF-"))
                    self.assertTrue(content.rstrip().endswith(b"%%EOF"))
                    self.assertNotIn(b"SYNTHETIC TEST DATA", content)
                else:
                    self.assertTrue(content.startswith(b"%PDF-"))
                    self.assertTrue(content.rstrip().endswith(b"%%EOF"))
                    self.assertIn(b"SYNTHETIC TEST DATA", content)

    def test_windows_demo_scripts_use_known_processes_and_supported_poc_defaults(
        self,
    ) -> None:
        start = (ROOT / "scripts/start_demo_windows.bat").read_text(encoding="utf-8")
        stop = (ROOT / "scripts/stop_demo_windows.bat").read_text(encoding="utf-8")
        reset = (ROOT / "scripts/reset_demo_windows.bat").read_text(encoding="utf-8")
        lifecycle = (ROOT / "scripts/demo_lifecycle.ps1").read_text(encoding="utf-8")

        for mode in (
            '$env:ACRA_CONNECTOR_MODE = "mock"',
            '$env:GOLDTIER_CONNECTOR_MODE = "mock"',
            '$env:IDP_CONNECTOR_MODE = "local_pdf_text"',
            '$env:OWNERSHIP_CONNECTOR_MODE = "mock"',
        ):
            self.assertIn(mode, lifecycle)
        self.assertNotIn("pip install", start.lower())
        self.assertNotIn("npm install", start.lower())
        for wrapper, action in ((start, "Start"), (stop, "Stop"), (reset, "Reset")):
            self.assertIn("demo_lifecycle.ps1", wrapper)
            self.assertIn(f"-Action {action}", wrapper)
            self.assertIn("exit /b %DEMO_EXIT_CODE%", wrapper)
        self.assertIn("Start-Process", lifecycle)
        self.assertIn("-PassThru", lifecycle)
        self.assertIn("taskkill.exe /PID", lifecycle)
        self.assertIn("/T /F", lifecycle)
        self.assertIn("demo-processes.json", lifecycle)
        self.assertIn("creation_time_utc", lifecycle)
        self.assertIn("function Assert-RunningState", lifecycle)
        self.assertIn("DEMO_RUNTIME_STATE_INCOMPLETE", lifecycle)
        self.assertIn("Wait-DemoHealthy", lifecycle)
        self.assertIn("Wait-ForOwnedShutdown", lifecycle)
        self.assertIn("Normalize-ChildProcessEnvironment", lifecycle)
        self.assertIn(
            '[Environment]::SetEnvironmentVariable("PATH", $effectivePath, "Process")',
            lifecycle,
        )
        self.assertIn("Demo started and verified healthy", lifecycle)
        self.assertIn("Demo stopped: the launcher-owned", lifecycle)
        self.assertIn("Demo reset verified", lifecycle)
        self.assertIn("Reset aborted because verified stop failed", lifecycle)
        self.assertIn("Startup was aborted; the occupant was not terminated", lifecycle)
        self.assertNotIn("WINDOWTITLE", lifecycle)
        self.assertNotIn("/IM python.exe", lifecycle)
        self.assertNotIn("/IM node.exe", lifecycle)

    def test_runtime_metadata_is_ignored_and_app_name_is_documented(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        configuration = (
            ROOT / "docs/integration/CONFIGURATION_REFERENCE.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".runtime/", gitignore)
        self.assertIn("APP_NAME=Zero-Touch CLM API", env_example)
        self.assertIn("`APP_NAME`", configuration)


if __name__ == "__main__":
    unittest.main()
