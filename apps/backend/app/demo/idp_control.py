"""Dedicated demo control for deterministic Mock IDP scenario selection."""

from app.connectors.idp import IdpProvider
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario


class MockIdpDemoControl:
    """Translate a UI demo selector into a configured provider instance."""

    def provider_for(self, raw_scenario: str | None) -> IdpProvider:
        scenario = MockIdpScenario(raw_scenario or "")
        return MockIdpProvider(scenario=scenario)
