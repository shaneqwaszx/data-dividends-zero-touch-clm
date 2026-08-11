"""Deterministic fictional ownership provider for the Phase 04 POC."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from app.connectors.ownership import (
    OwnershipProviderError,
    OwnershipProviderMetadata,
    OwnershipProviderRequest,
    OwnershipSourceResult,
)
from app.domain.ownership import (
    OwnershipEnvironment,
    OwnershipProvenance,
    OwnershipRelationship,
    Party,
    PartyType,
)


class MockOwnershipScenario(StrEnum):
    DIRECT_OWNER = "DIRECT_OWNER"
    INDIRECT_OWNER = "INDIRECT_OWNER"
    MULTIPLE_PATHS = "MULTIPLE_PATHS"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    INCOMPLETE_CHAIN = "INCOMPLETE_CHAIN"
    CYCLE = "CYCLE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"


class MockOwnershipProvider:
    """Return only explicit synthetic scenarios with no network or credentials."""

    def __init__(
        self, scenario: MockOwnershipScenario = MockOwnershipScenario.DIRECT_OWNER
    ) -> None:
        self._scenario = scenario

    @property
    def metadata(self) -> object:
        return OwnershipProviderMetadata(
            provider_name="MOCK_OWNERSHIP",
            environment=OwnershipEnvironment.MOCK,
        )

    def load(self, request: OwnershipProviderRequest) -> object:
        if self._scenario == MockOwnershipScenario.PROVIDER_FAILURE:
            raise OwnershipProviderError

        root = Party(
            party_id="ROOT_ENTITY",
            display_name=request.display_name,
            party_type=PartyType.LEGAL_ENTITY,
            registration_number=request.registration_number,
            country="SG",
        )
        parties = [root]
        edges: list[OwnershipRelationship] = []

        def person(party_id: str, name: str) -> Party:
            item = Party(party_id=party_id, display_name=name, party_type=PartyType.NATURAL_PERSON)
            parties.append(item)
            return item

        def company(party_id: str, name: str) -> Party:
            item = Party(
                party_id=party_id,
                display_name=name,
                party_type=PartyType.LEGAL_ENTITY,
                registration_number=f"SYN-{party_id}",
                country="SG",
            )
            parties.append(item)
            return item

        def edge(relationship_id: str, parent: Party, child: Party, percent: str) -> None:
            edges.append(
                OwnershipRelationship(
                    relationship_id=relationship_id,
                    parent_party_id=parent.party_id,
                    child_party_id=child.party_id,
                    ownership_percent=Decimal(percent),
                    provenance=OwnershipProvenance(
                        provider="MOCK_OWNERSHIP",
                        environment=OwnershipEnvironment.MOCK,
                        source_reference=f"SYNTHETIC_{relationship_id}",
                        sourced_at=datetime(2026, 8, 11, tzinfo=UTC),
                    ),
                )
            )

        if self._scenario == MockOwnershipScenario.DIRECT_OWNER:
            first = person("PERSON_A", "Avery Tan")
            second = person("PERSON_B", "Blair Lim")
            edge("REL_DIRECT_A", root, first, "60")
            edge("REL_DIRECT_B", root, second, "40")
        elif self._scenario == MockOwnershipScenario.INDIRECT_OWNER:
            holding = company("HOLDING_B", "Harbour Holdings Pte. Ltd.")
            first = person("PERSON_C", "Casey Ong")
            second = person("PERSON_D", "Devon Goh")
            edge("REL_ROOT_HOLDING", root, holding, "40")
            edge("REL_HOLDING_C", holding, first, "75")
            edge("REL_HOLDING_D", holding, second, "25")
        elif self._scenario == MockOwnershipScenario.MULTIPLE_PATHS:
            first = person("PERSON_A", "Avery Tan")
            second = person("PERSON_B", "Blair Lim")
            holding = company("HOLDING_B", "Harbour Holdings Pte. Ltd.")
            edge("REL_ROOT_A", root, first, "20")
            edge("REL_ROOT_HOLDING", root, holding, "40")
            edge("REL_HOLDING_A", holding, first, "50")
            edge("REL_HOLDING_B", holding, second, "50")
        elif self._scenario == MockOwnershipScenario.BELOW_THRESHOLD:
            first = person("PERSON_A", "Avery Tan")
            second = person("PERSON_B", "Blair Lim")
            edge("REL_BELOW_A", root, first, "20")
            edge("REL_BELOW_B", root, second, "15")
        elif self._scenario == MockOwnershipScenario.INCOMPLETE_CHAIN:
            unresolved = company("UNRESOLVED_HOLDING", "Unresolved Synthetic Holding")
            edge("REL_INCOMPLETE", root, unresolved, "80")
        else:
            first = company("CYCLE_B", "Cycle Holdings B")
            second = company("CYCLE_C", "Cycle Holdings C")
            edge("REL_CYCLE_ROOT_B", root, first, "60")
            edge("REL_CYCLE_B_C", first, second, "100")
            edge("REL_CYCLE_C_B", second, first, "100")

        return OwnershipSourceResult(
            root_party_id=root.party_id,
            parties=parties,
            relationships=edges,
        )
