"""UEN-keyed synthetic ownership data for sponsor-mode input-driven journeys."""

from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import OwnershipProviderRequest


class InputDrivenOwnershipProvider:
    """Select only provider-local fictional data from a canonical registration number."""

    @property
    def metadata(self) -> object:
        return MockOwnershipProvider().metadata

    def load(self, request: OwnershipProviderRequest) -> object:
        scenario = {
            "202400006F": MockOwnershipScenario.CYCLE,
        }.get(request.registration_number, MockOwnershipScenario.DIRECT_OWNER)
        return MockOwnershipProvider(scenario).load(request)
