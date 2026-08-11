"""Dedicated Mock-only control for synthetic ownership scenario selection."""

from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import OwnershipProvider


class MockOwnershipDemoControl:
    def provider_for(self, raw_scenario: str | None) -> OwnershipProvider:
        return MockOwnershipProvider(MockOwnershipScenario(raw_scenario or ""))
