"""Phase 07 sponsor UAT, evidence, and handoff contract checks."""

import unittest
from pathlib import Path

from phase13_contract_credentials import provision_contract_hash_environment

provision_contract_hash_environment()

from app.config import Settings
from app.demo.uat_evidence import UatEvidenceExport
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]


class Phase07UatContractTests(unittest.TestCase):
    def test_openapi_exposes_safe_profile_and_demo_gated_evidence_routes(self) -> None:
        paths = create_app(Settings(app_env="test")).openapi()["paths"]
        self.assertIn("/api/system/execution-profile", paths)
        self.assertIn(
            "/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence",
            paths,
        )
        self.assertEqual(
            paths["/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence"]["get"][
                "tags"
            ],
            ["demo"],
        )

    def test_uat_export_schema_is_a_strict_safe_whitelist(self) -> None:
        schema = UatEvidenceExport.model_json_schema()
        properties = set(schema["properties"])
        self.assertTrue(
            {
                "case_id",
                "scenario",
                "final_state",
                "active_blockers",
                "human_interventions",
                "target_calls",
                "warnings",
                "timeline",
            }.issubset(properties)
        )
        self.assertTrue(
            properties.isdisjoint(
                {
                    "pdf",
                    "raw_payload",
                    "source_reference",
                    "endpoint",
                    "authorization",
                    "authority_digest",
                    "input_fingerprint",
                }
            )
        )

    def test_final_handoff_keeps_live_and_policy_boundaries_explicit(self) -> None:
        handoff = (ROOT / "docs/integration/INTEGRATION_HANDOFF.md").read_text(
            encoding="utf-8"
        )
        dependencies = (
            ROOT / "docs/sponsor-questions/PHASE_07_SPONSOR_DEPENDENCY_MATRIX.md"
        ).read_text(encoding="utf-8")
        self.assertIn("ACRA live-ready — `BLOCKED`", handoff)
        self.assertIn("GoldTier real-ready — `NOT READY`", handoff)
        self.assertIn("Ready-for-Approval — `NOT CONFIRMED`", handoff)
        for question in (
            "Q-001",
            "Q-002",
            "Q-003",
            "Q-004",
            "Q-005",
            "Q-006",
            "Q-007",
            "Q-008",
            "Q-012",
            "Q-013",
            "Q-014",
        ):
            self.assertIn(question, dependencies)


if __name__ == "__main__":
    unittest.main()
