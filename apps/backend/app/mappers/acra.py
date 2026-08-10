"""Map ACRA connector payloads into source-neutral canonical entities."""

from app.connectors.acra import AcraCompanyPayload
from app.domain.models import (
    CanonicalLegalEntity,
    RegisteredAddress,
    SourceEnvironment,
    SourceMetadata,
    SourceSystem,
)
from app.mappers.errors import MappingError


def map_acra_company(payload: AcraCompanyPayload) -> CanonicalLegalEntity:
    """Transform one source payload without leaking the source shape downstream."""

    retrieved_at = payload.retrieved_at
    utc_offset = retrieved_at.utcoffset()
    if retrieved_at.tzinfo is None or utc_offset is None:
        raise MappingError("ACRA retrieval time must be timezone-aware")
    if utc_offset.total_seconds() != 0:
        raise MappingError("ACRA retrieval time must use UTC")

    address = payload.registered_address
    canonical_address = None
    if address is not None:
        optional_address_parts = [
            normalized
            for value in (address.unit, address.building_name)
            if value is not None and (normalized := value.strip())
        ]
        address_line_2 = ", ".join(optional_address_parts) or None
        canonical_address = RegisteredAddress(
            address_line_1=f"{address.block} {address.street}",
            address_line_2=address_line_2,
            postal_code=address.postal_code,
            country_code=address.country_code,
        )

    return CanonicalLegalEntity(
        registration_number=payload.uen,
        legal_name=payload.entity_name,
        country_of_incorporation=payload.country_code,
        party_type=payload.entity_type,
        registration_date=payload.registration_date,
        entity_status=payload.entity_status,
        registered_address=canonical_address,
        source=SourceMetadata(
            source_system=SourceSystem.ACRA,
            environment=SourceEnvironment(payload.source_environment),
            registry_source_link=payload.source_endpoint,
            retrieved_at=payload.retrieved_at,
        ),
    )
