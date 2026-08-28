"""Credential-free deterministic ACRA connector for Phase 01."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from app.connectors.acra import (
    AcraAddressPayload,
    AcraCompanyPayload,
    AcraOfficerPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraOwnershipPartyPayload,
    AcraRelationshipPayload,
    AcraRelationshipsPayload,
)
from app.connectors.errors import AcraServiceUnavailableError
from app.demo.scenarios import (
    GOLDTIER_FAILURE_UEN,
    GOLDTIER_PARTIAL_UEN,
    INCOMPLETE_ENTITY_UEN,
    VALID_SME_UEN,
)

LEGAL_ENTITY_OWNER_UEN = "202400007G"
MULTIPLE_OWNERS_UEN = "202400008H"
MULTI_LEVEL_OWNER_UEN = "202400009I"
EMPTY_OFFICERS_UEN = "202400010J"
MISSING_OWNERSHIP_UEN = "202400011K"
MALFORMED_RELATIONSHIPS_UEN = "202400012L"
FAILED_RELATIONSHIPS_UEN = "202400013M"


def _address(street: str, postal_code: str, unit: str) -> AcraAddressPayload:
    return AcraAddressPayload(
        block="18",
        street=street,
        unit=unit,
        postal_code=postal_code,
        country_code="SG",
    )


class MockAcraConnector:
    """Return only synthetic fixtures and never access a network."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        normalised_uen = uen.strip().upper()
        fixtures: dict[str, tuple[str, AcraAddressPayload | None]] = {
            VALID_SME_UEN: (
                "MERLION CIRCULAR LABS PTE. LTD.",
                _address("INNOVATION WAY", "018956", "#04-01"),
            ),
            INCOMPLETE_ENTITY_UEN: ("STRAITS TEST TRADING PTE. LTD.", None),
            GOLDTIER_FAILURE_UEN: (
                "ORCHID VALIDATION DEMO PTE. LTD.",
                _address("SANDBOX AVENUE", "048583", "#08-03"),
            ),
            GOLDTIER_PARTIAL_UEN: (
                "HARBOUR PARTIAL DEMO PTE. LTD.",
                _address("MOCK QUAY", "049317", "#12-04"),
            ),
            "202400005E": (
                "LION CITY EXISTING CUSTOMER PTE. LTD.",
                _address("CUSTOMER ROAD", "068914", "#05-02"),
            ),
            "202400006F": (
                "CYCLIC HARBOUR HOLDINGS PTE. LTD.",
                _address("CYCLE STREET", "049001", "#01-01"),
            ),
            LEGAL_ENTITY_OWNER_UEN: (
                "LEGAL ENTITY SHAREHOLDER DEMO PTE. LTD.",
                _address("HOLDING AVENUE", "049002", "#02-01"),
            ),
            MULTIPLE_OWNERS_UEN: (
                "MULTIPLE OWNER DEMO PTE. LTD.",
                _address("SHAREHOLDER ROAD", "049003", "#03-01"),
            ),
            MULTI_LEVEL_OWNER_UEN: (
                "MULTI LEVEL OWNERSHIP DEMO PTE. LTD.",
                _address("HIERARCHY WALK", "049004", "#04-01"),
            ),
            EMPTY_OFFICERS_UEN: (
                "EMPTY OFFICER COLLECTION DEMO PTE. LTD.",
                _address("OPTIONAL LANE", "049005", "#05-01"),
            ),
            MISSING_OWNERSHIP_UEN: (
                "MISSING OWNERSHIP EVIDENCE DEMO PTE. LTD.",
                _address("PARTIAL STREET", "049006", "#06-01"),
            ),
            MALFORMED_RELATIONSHIPS_UEN: (
                "MALFORMED RELATIONSHIP DEMO PTE. LTD.",
                _address("VALIDATION DRIVE", "049007", "#07-01"),
            ),
            FAILED_RELATIONSHIPS_UEN: (
                "FAILED RELATIONSHIP STEP DEMO PTE. LTD.",
                _address("FAILURE CLOSE", "049008", "#08-01"),
            ),
        }
        fixture = fixtures.get(normalised_uen)
        if fixture is None:
            return None

        entity_name, registered_address = fixture
        return AcraCompanyPayload(
            uen=normalised_uen,
            entity_name=entity_name,
            country_code="SG",
            entity_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
            registration_date=date(2024, 1, 2),
            entity_status="LIVE",
            registered_address=registered_address,
            source_environment="MOCK",
            source_endpoint=f"https://mock.acra.gov.sg/api/entities/{normalised_uen}",
            retrieved_at=self._clock(),
        )

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        normalised_uen = uen.strip().upper()
        officers: tuple[AcraOfficerPayload, ...]
        if normalised_uen == EMPTY_OFFICERS_UEN:
            officers = ()
        else:
            officers = (
                AcraOfficerPayload(
                    officer_id="OFFICER_A",
                    name="Alex Synthetic",
                    role="DIRECTOR",
                    appointment_date=date(2024, 1, 2),
                    country="SG",
                ),
            )
        return AcraOfficersPayload(
            uen=normalised_uen,
            officers=officers,
            source_environment="MOCK",
            source_endpoint=f"https://mock.acra.gov.sg/api/entities/{normalised_uen}/officers",
            retrieved_at=self._clock(),
        )

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        normalised_uen = uen.strip().upper()
        parties: tuple[AcraOwnershipPartyPayload, ...]
        if normalised_uen == MISSING_OWNERSHIP_UEN:
            parties = ()
        elif normalised_uen == "202400006F":
            parties = (
                self._company_party("CYCLE_B", "Cycle Holdings B"),
                self._company_party("CYCLE_C", "Cycle Holdings C"),
            )
        elif normalised_uen in {LEGAL_ENTITY_OWNER_UEN, MULTI_LEVEL_OWNER_UEN}:
            parties = (
                self._company_party("HOLDING_B", "Harbour Holdings Pte. Ltd."),
                self._person_party("PERSON_A", "Avery Tan"),
                self._person_party("PERSON_B", "Blair Lim"),
            )
        elif normalised_uen == MULTIPLE_OWNERS_UEN:
            parties = (
                self._person_party("PERSON_A", "Avery Tan", "50"),
                self._person_party("PERSON_B", "Blair Lim", "30"),
                self._person_party("PERSON_C", "Casey Ong", "20"),
            )
        else:
            parties = (
                self._person_party("PERSON_A", "Avery Tan", "60"),
                self._person_party("PERSON_B", "Blair Lim", "40"),
            )
        return AcraOwnershipPartiesPayload(
            uen=normalised_uen,
            ownership_parties=parties,
            source_environment="MOCK",
            source_endpoint=(
                f"https://mock.acra.gov.sg/api/entities/{normalised_uen}/ownership-parties"
            ),
            retrieved_at=self._clock(),
        )

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        normalised_uen = uen.strip().upper()
        if normalised_uen == FAILED_RELATIONSHIPS_UEN:
            raise AcraServiceUnavailableError
        if normalised_uen == MALFORMED_RELATIONSHIPS_UEN:
            return cast(
                AcraRelationshipsPayload,
                {
                    "uen": normalised_uen,
                    "relationships": [{"unexpected": "unsafe-shape"}],
                },
            )
        root = f"ENTITY_{normalised_uen}"
        relationships: tuple[AcraRelationshipPayload, ...]
        if normalised_uen == MISSING_OWNERSHIP_UEN:
            relationships = ()
        elif normalised_uen == "202400006F":
            relationships = (
                self._relationship("REL_CYCLE_ROOT_B", root, "CYCLE_B", "60"),
                self._relationship("REL_CYCLE_B_C", "CYCLE_B", "CYCLE_C", "100"),
                self._relationship("REL_CYCLE_C_B", "CYCLE_C", "CYCLE_B", "100"),
            )
        elif normalised_uen in {LEGAL_ENTITY_OWNER_UEN, MULTI_LEVEL_OWNER_UEN}:
            relationships = (
                self._relationship("REL_ROOT_HOLDING", root, "HOLDING_B", "40"),
                self._relationship("REL_HOLDING_A", "HOLDING_B", "PERSON_A", "75"),
                self._relationship("REL_HOLDING_B", "HOLDING_B", "PERSON_B", "25"),
            )
        elif normalised_uen == MULTIPLE_OWNERS_UEN:
            relationships = (
                self._relationship("REL_ROOT_A", root, "PERSON_A", "50"),
                self._relationship("REL_ROOT_B", root, "PERSON_B", "30"),
                self._relationship("REL_ROOT_C", root, "PERSON_C", "20"),
            )
        else:
            relationships = (
                self._relationship("REL_DIRECT_A", root, "PERSON_A", "60"),
                self._relationship("REL_DIRECT_B", root, "PERSON_B", "40"),
            )
        return AcraRelationshipsPayload(
            uen=normalised_uen,
            relationships=relationships,
            source_environment="MOCK",
            source_endpoint=f"https://mock.acra.gov.sg/api/entities/{normalised_uen}/relationships",
            retrieved_at=self._clock(),
        )

    @staticmethod
    def _person_party(
        party_id: str, name: str, percentage: str | None = None
    ) -> AcraOwnershipPartyPayload:
        return AcraOwnershipPartyPayload(
            party_id=party_id,
            party_type="NATURAL_PERSON",
            name=name,
            country="SG",
            ownership_percentage=Decimal(percentage) if percentage is not None else None,
        )

    @staticmethod
    def _company_party(party_id: str, name: str) -> AcraOwnershipPartyPayload:
        return AcraOwnershipPartyPayload(
            party_id=party_id,
            party_type="LEGAL_ENTITY",
            name=name,
            registration_identifier=f"SYN-{party_id}",
            country="SG",
        )

    @staticmethod
    def _relationship(
        relationship_id: str,
        owned_entity_id: str,
        owner_party_id: str,
        percentage: str,
    ) -> AcraRelationshipPayload:
        return AcraRelationshipPayload(
            relationship_id=relationship_id,
            owned_entity_id=owned_entity_id,
            owner_party_id=owner_party_id,
            ownership_percentage=Decimal(percentage),
        )
