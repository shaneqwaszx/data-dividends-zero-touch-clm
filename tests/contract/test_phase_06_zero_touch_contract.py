import unittest
from pathlib import Path

from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


class Phase06ZeroTouchContractTests(unittest.TestCase):
    def test_openapi_exposes_zero_touch_lifecycle_and_typed_resolution(self) -> None:
        schema = TestClient(create_app(Settings(app_env="test"))).get("/openapi.json").json()
        paths = schema["paths"]
        self.assertIn("/api/clm/zero-touch/cases", paths)
        self.assertIn("/api/clm/zero-touch/cases/{case_id}/documents", paths)
        self.assertIn("/api/clm/zero-touch/cases/{case_id}/start", paths)
        self.assertIn("/api/clm/zero-touch/cases/{case_id}/resume", paths)
        self.assertIn(
            "/api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve",
            paths,
        )
        components = schema["components"]["schemas"]
        self.assertIn("ZeroTouchCaseSummaryResponse", components)
        self.assertIn("ExceptionResolutionAction", components)

    def test_generic_orchestrator_contains_no_mock_scenario_branching(self) -> None:
        source = (ROOT / "apps/backend/app/services/zero_touch_orchestration.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ZeroTouchDemoScenario", source)
        self.assertNotIn("MockIdpScenario", source)
        self.assertNotIn("MockOwnershipScenario", source)
        self.assertNotIn("if scenario", source)

    def test_phase06_documents_and_provider_contract_exist(self) -> None:
        required = (
            ".ai-pipeline/001_planner/PHASE_06_ZERO_TOUCH_ORCHESTRATION.md",
            "docs/architecture/PHASE_06_ZERO_TOUCH_ORCHESTRATION.md",
            "docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md",
            "docs/contracts/INTEGRATION_ADAPTER_CONTRACTS.md",
        )
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
