"""Credential-free deterministic ACRA connector for Phase 01."""

from collections.abc import Callable
from datetime import UTC, date, datetime

from app.connectors.acra import AcraAddressPayload, AcraCompanyPayload
from app.demo.scenarios import (
    GOLDTIER_FAILURE_UEN,
    GOLDTIER_PARTIAL_UEN,
    INCOMPLETE_ENTITY_UEN,
    VALID_SME_UEN,
)


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
