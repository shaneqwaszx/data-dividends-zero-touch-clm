from __future__ import annotations

import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "backend"
FRONTEND_ROOT = REPOSITORY_ROOT / "apps" / "frontend" / "src"
FIXTURE = BACKEND_ROOT / "tests" / "fixtures" / "acra" / "synthetic_company_success.json"
sys.path.insert(0, str(BACKEND_ROOT))

from app.api_models import BrowserSourceMetadata
from app.connectors.acra import AcraCompanyPayload
from app.connectors.acra_sandbox import ProjectAcraResponseDecoder
from app.connectors.errors import AcraMalformedResponseError
from app.domain.models import SourceEnvironment, SourceMetadata, SourceSystem
from app.mappers.acra import map_acra_company


class Phase02AcraContractTests(unittest.TestCase):
    def test_tracked_fixture_is_marked_synthetic_and_decodes_through_source_model(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertIn("SYNTHETIC SANITIZED", document["fixture_notice"])
        self.assertIn("NOT AN ACRA RESPONSE", document["fixture_notice"])

        payload = ProjectAcraResponseDecoder().decode(
            document["response"],
            requested_uen="202400001A",
            source_endpoint="https://sandbox.synthetic-acra.example/business-profile/202400001A",
            retrieved_at=datetime(2026, 8, 10, tzinfo=UTC),
        )
        canonical = map_acra_company(payload)

        self.assertIsInstance(payload, AcraCompanyPayload)
        self.assertEqual(canonical.source.source_system, SourceSystem.ACRA)
        self.assertEqual(canonical.source.environment, SourceEnvironment.SANDBOX)
        self.assertEqual(canonical.registration_number, "202400001A")

    def test_source_dto_rejects_unmodeled_external_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AcraCompanyPayload.model_validate(
                {
                    "uen": "202400001A",
                    "entity_name": "SYNTHETIC COMPANY",
                    "country_code": "SG",
                    "entity_type": "SYNTHETIC_TYPE",
                    "registered_address": None,
                    "source_environment": "SANDBOX",
                    "source_endpoint": "https://sandbox.synthetic-acra.example/entity",
                    "retrieved_at": "2026-08-10T00:00:00Z",
                    "raw_response": {"must": "not be retained"},
                }
            )

    def test_source_dto_rejects_semantically_blank_required_fields(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document["response"]["company"]["entityType"] = "   "

        with self.assertRaisesRegex(AcraMalformedResponseError, "unexpected response"):
            ProjectAcraResponseDecoder().decode(
                document["response"],
                requested_uen="202400001A",
                source_endpoint=(
                    "https://sandbox.synthetic-acra.example/business-profile/202400001A"
                ),
                retrieved_at=datetime(2026, 8, 10, tzinfo=UTC),
            )

    def test_internal_provenance_retains_link_but_browser_contract_omits_it(self) -> None:
        self.assertIn("registry_source_link", SourceMetadata.model_fields)
        self.assertNotIn("registry_source_link", BrowserSourceMetadata.model_fields)

        frontend_types = (FRONTEND_ROOT / "types.ts").read_text(encoding="utf-8")
        self.assertNotIn("registry_source_link", frontend_types)

    def test_application_source_does_not_disable_tls_verification(self) -> None:
        connector_source = (
            BACKEND_ROOT / "app" / "connectors" / "acra_sandbox.py"
        ).read_text(encoding="utf-8")
        compact = connector_source.replace(" ", "").lower()

        self.assertNotIn("verify=false", compact)
        self.assertIn("verify=true", compact)
        self.assertIn("follow_redirects=false", compact)

    def test_frontend_has_no_acra_transport_or_private_configuration(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in FRONTEND_ROOT.rglob("*") if path.is_file()
        )
        forbidden = (
            "ACRA_BASE_URL",
            "ACRA_AUTH_HEADER",
            "ACRA_COMPANY_PATH_TEMPLATE",
            "X-Synthetic-Authorization",
            "httpx",
        )
        for value in forbidden:
            self.assertNotIn(value, combined)

    def test_ci_does_not_execute_optional_live_smoke(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("acra_sandbox_smoke.py", workflow)


if __name__ == "__main__":
    unittest.main()
