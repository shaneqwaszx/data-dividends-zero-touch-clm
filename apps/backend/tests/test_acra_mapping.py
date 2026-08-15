from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.connectors.acra import AcraAddressPayload, AcraCompanyPayload
from app.domain.models import SourceEnvironment, SourceSystem
from app.mappers.acra import map_acra_company

FIXED_TIME = datetime(2026, 8, 10, 5, 0, tzinfo=UTC)


def source_payload(retrieved_at: datetime = FIXED_TIME) -> AcraCompanyPayload:
    return AcraCompanyPayload(
        uen="202400001A",
        entity_name="MERLION CIRCULAR LABS PTE. LTD.",
        country_code="SG",
        entity_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
        registration_date=date(2024, 1, 2),
        entity_status="LIVE",
        registered_address=AcraAddressPayload(
            block="18",
            street="INNOVATION WAY",
            unit="#04-01",
            building_name="SYNTHETIC CENTRE",
            postal_code="018956",
            country_code="SG",
        ),
        source_environment="SANDBOX",
        source_endpoint="https://sandbox.synthetic-acra.example/business-profile/202400001A",
        retrieved_at=retrieved_at,
    )


def test_acra_source_dto_maps_to_source_neutral_canonical_entity() -> None:
    entity = map_acra_company(source_payload())

    assert entity.registration_number == "202400001A"
    assert entity.legal_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert entity.country_of_incorporation == "SG"
    assert entity.party_type == "PRIVATE_COMPANY_LIMITED_BY_SHARES"
    assert entity.registration_date == date(2024, 1, 2)
    assert entity.entity_status == "LIVE"
    assert entity.registered_address is not None
    assert entity.registered_address.model_dump() == {
        "address_line_1": "18 INNOVATION WAY",
        "address_line_2": "#04-01, SYNTHETIC CENTRE",
        "postal_code": "018956",
        "country_code": "SG",
    }
    assert entity.source.source_system == SourceSystem.ACRA
    assert entity.source.environment == SourceEnvironment.SANDBOX
    assert entity.source.registry_source_link.endswith("/business-profile/202400001A")
    assert entity.source.retrieved_at == FIXED_TIME
    assert entity.source.retrieved_at.isoformat().endswith("+00:00")


@pytest.mark.parametrize(
    "retrieved_at",
    [
        datetime(2026, 8, 10, 5, 0),
        datetime(2026, 8, 10, 13, 0, tzinfo=timezone(timedelta(hours=8))),
    ],
)
def test_non_utc_source_timestamp_is_rejected(retrieved_at: datetime) -> None:
    with pytest.raises(ValidationError, match="UTC|timezone-aware"):
        source_payload(retrieved_at)
