import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Phase04OwnershipContractTests(unittest.TestCase):
    def test_phase04_planner_architecture_and_profile_are_truthful(self) -> None:
        planner = (
            ROOT / ".ai-pipeline/001_planner/PHASE_04_RELATED_PARTIES_UBO.md"
        ).read_text(encoding="utf-8")
        architecture = (
            ROOT / "docs/architecture/PHASE_04_RELATED_PARTIES_UBO.md"
        ).read_text(encoding="utf-8")
        profile = (ROOT / "docs/contracts/OWNERSHIP_UBO_PROFILE.md").read_text(
            encoding="utf-8"
        )
        remediation = (
            ROOT / ".ai-pipeline/001_planner/PHASE_04_REMEDIATION.md"
        ).read_text(encoding="utf-8")
        for text in (planner, architecture, profile):
            self.assertIn("ownership", text.lower())
            self.assertIn("provisional", text.lower())
            self.assertIn("Q-004", text)
            self.assertNotIn("LEGALLY CONFIRMED UBO", text)
        self.assertIn("Decimal", profile)
        self.assertIn("aggregated ownership >= configured threshold", profile)
        self.assertIn("Q-002", architecture)
        self.assertIn("no live hierarchy", architecture.lower())
        for finding in range(1, 7):
            self.assertIn(f"P04-QG-00{finding}", remediation)

    def test_generic_ownership_api_has_no_mock_selector(self) -> None:
        main = (ROOT / "apps/backend/app/main.py").read_text(encoding="utf-8")
        generic_route = '"/api/onboarding/cases/{case_id}/ownership/load"'
        demo_route = '"/api/demo/onboarding/cases/{case_id}/ownership/load"'
        generic_block = main.split(generic_route, maxsplit=1)[1].split(
            demo_route, maxsplit=1
        )[0]
        demo_block = main.split(demo_route, maxsplit=1)[1]
        self.assertNotIn("X-Mock-Ownership-Scenario", generic_block)
        self.assertIn("X-Mock-Ownership-Scenario", demo_block)
        self.assertIn('"/api/onboarding/cases/{case_id}/ownership/analyze"', main)
        self.assertIn('"/api/onboarding/cases/{case_id}/ubo-candidates"', main)

    def test_decimal_api_contract_and_typed_classifications(self) -> None:
        domain = (ROOT / "apps/backend/app/domain/ownership.py").read_text(
            encoding="utf-8"
        )
        api_models = (ROOT / "apps/backend/app/api_models.py").read_text(
            encoding="utf-8"
        )
        frontend = (ROOT / "apps/frontend/src/types.ts").read_text(encoding="utf-8")
        self.assertIn("OwnershipPercent = Annotated[", domain)
        self.assertIn("Decimal", domain)
        self.assertIn("PROVISIONAL_UBO_CANDIDATE", domain)
        self.assertIn("threshold_percent: Decimal", api_models)
        self.assertIn("aggregated_ownership_percent: string", frontend)
        self.assertNotIn("Number(value)", (ROOT / "apps/frontend/src/App.tsx").read_text())
        browser_ownership = api_models.split("class BrowserOwnershipProvenance", maxsplit=1)[1]
        self.assertNotIn("source_reference", browser_ownership)

    def test_configuration_defaults_are_bounded_and_provisional(self) -> None:
        config = (ROOT / "apps/backend/app/config.py").read_text(encoding="utf-8")
        self.assertIn('ubo_ownership_threshold_percent: OwnershipPercent = Decimal("25")', config)
        self.assertIn("ownership_max_parties: int = Field(default=100", config)
        self.assertIn("ownership_max_relationships: int = Field(default=200", config)
        self.assertIn("ownership_max_depth: int = Field(default=8", config)
        self.assertIn("ownership_max_total_paths: int = Field(default=256", config)

    def test_generic_ownership_runtime_has_no_goldtier_or_mock_scenario_dependency(
        self,
    ) -> None:
        ownership_service = (
            ROOT / "apps/backend/app/services/ownership_analysis.py"
        ).read_text(encoding="utf-8")
        provider_contract = (
            ROOT / "apps/backend/app/connectors/ownership.py"
        ).read_text(encoding="utf-8")
        domain = (ROOT / "apps/backend/app/domain/ownership.py").read_text(
            encoding="utf-8"
        )
        for text in (ownership_service, provider_contract, domain):
            self.assertNotIn("MockOwnershipScenario", text)
            self.assertNotIn("create_related_party", text.lower())
            self.assertNotIn("pingfed", text.lower())

    def test_remediated_graph_trust_concurrency_and_path_contracts_are_explicit(self) -> None:
        service = (ROOT / "apps/backend/app/services/ownership_analysis.py").read_text(
            encoding="utf-8"
        )
        repository = (ROOT / "apps/backend/app/services/ownership_repository.py").read_text(
            encoding="utf-8"
        )
        domain = (ROOT / "apps/backend/app/domain/ownership.py").read_text(encoding="utf-8")
        self.assertIn("parent.party_type != PartyType.LEGAL_ENTITY", service)
        self.assertIn("_untrusted_to_primitives", service)
        self.assertIn("expected_version", repository)
        self.assertIn("OwnershipRepositoryConflictError", repository)
        self.assertIn('return f"path-v1-{digest.hexdigest()}"', service)
        self.assertIn('pattern=r"^path-v1-[a-f0-9]{64}$"', domain)
        self.assertIn('pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"', domain)


if __name__ == "__main__":
    unittest.main()
