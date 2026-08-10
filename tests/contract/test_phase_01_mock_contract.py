from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.connectors.acra import AcraConnector
from app.connectors.goldtier_models import (
    CreatePolicyRequest,
    GoldTierRequestMetadata,
)
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import CANONICAL_AMEND_ROUTE
from app.demo.scenarios import (
    VALID_SME_UEN,
    Phase01MockScenarioCatalogue,
)
from app.domain.models import SourceEnvironment, SourceSystem
from app.mappers.acra import map_acra_company
from app.mappers.goldtier import build_policy_request, build_shell_request


class Phase01MockContractTests(unittest.TestCase):
    def setUp(self) -> None:
        payload = MockAcraConnector().fetch_company(VALID_SME_UEN)
        assert payload is not None
        self.entity = map_acra_company(payload)
        self.source_case_id = "CASE-202400001A-12345678"
        self.accepted_at = datetime(2026, 8, 10, tzinfo=UTC)

    def test_synthetic_acra_fixtures_validate_through_source_and_canonical_models(self) -> None:
        connector = MockAcraConnector()
        scenarios = Phase01MockScenarioCatalogue().discovery().scenarios
        self.assertTrue(scenarios)
        for scenario in scenarios:
            payload = connector.fetch_company(scenario.uen)
            self.assertIsNotNone(payload)
            assert payload is not None
            canonical = map_acra_company(payload)
            self.assertEqual(canonical.registration_number, scenario.uen)
            self.assertEqual(canonical.source.source_system, SourceSystem.ACRA)
            self.assertEqual(canonical.source.environment, SourceEnvironment.MOCK)

    def test_mock_discovery_is_not_part_of_acra_connector_protocol(self) -> None:
        self.assertNotIn("available_scenarios", AcraConnector.__dict__)

    def test_shell_request_applies_country_mandatory_field_overlay(self) -> None:
        request = build_shell_request(self.entity, self.source_case_id, self.accepted_at)
        body = request.model_dump(mode="json", by_alias=True)

        self.assertEqual(
            body["party"]["nonIndividualProfile"]["countryOfIncorporation"], "SG"
        )

    def test_policy_request_requires_phase_01_external_reference_fields(self) -> None:
        request = build_policy_request(
            self.entity, "GT-MOCK-1", self.source_case_id, self.accepted_at
        )
        body = request.model_dump(mode="json", by_alias=True)

        self.assertEqual(body["customerExternalSystem"], "ACRA")
        self.assertEqual(body["customerExternalSystemKey"], VALID_SME_UEN)
        with self.assertRaises(ValidationError):
            CreatePolicyRequest.model_validate(
                {
                    "goldtier_id": "GT-MOCK-1",
                    "policy_details": {"policy": "SINGAPORE_NTB_MOCK"},
                    "source_context": request.source_context,
                }
            )

    def test_source_case_header_matches_canonical_body_property(self) -> None:
        request = build_policy_request(
            self.entity, "GT-MOCK-1", self.source_case_id, self.accepted_at
        )
        metadata = GoldTierRequestMetadata(
            correlation_id=uuid4(),
            source_case_id=self.source_case_id,
            idempotency_key=uuid4(),
        )
        body = request.model_dump(mode="json", by_alias=True)

        self.assertEqual(metadata.as_headers()["X-Source-Case-Id"], body["sourceContext"]["sourceCaseId"])
        self.assertEqual(metadata.idempotency_key.version, 4)

    def test_canonical_amend_route_and_phase_01_sources_exclude_stale_forms(self) -> None:
        self.assertEqual(CANONICAL_AMEND_ROUTE, "/v1/eds/parties/{partyId}/amend")
        forbidden = ("X-DSD-Case-Id", "dsdCaseId", "{goldTierId}:amend")
        roots = [BACKEND_ROOT / "app", REPOSITORY_ROOT / "apps" / "frontend" / "src"]
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
                    continue
                content = path.read_text(encoding="utf-8")
                for stale_form in forbidden:
                    self.assertNotIn(stale_form, content, f"{stale_form} found in {path}")

    def test_phase_01_code_does_not_import_private_or_sponsor_json(self) -> None:
        for path in (BACKEND_ROOT / "app").rglob("*.py"):
            content = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("private/sponsor-artifacts", content)
            self.assertNotIn("gt_eds_api_specs_json", content)

    def test_mock_goldtier_does_not_import_mock_acra_or_parse_source_case(self) -> None:
        source = (BACKEND_ROOT / "app" / "connectors" / "mock_goldtier.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("mock_acra", source)
        self.assertNotIn("source_case_id[-", source)


if __name__ == "__main__":
    unittest.main()
