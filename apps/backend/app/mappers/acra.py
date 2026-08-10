"""Map ACRA connector payloads into source-neutral canonical entities."""

from app.connectors.acra import AcraCompanyPayload
from app.domain.models import (
    CanonicalLegalEntity,
    RegisteredAddress,
    SourceEnvironment,
    SourceMetadata,
    SourceSystem,
)


def map_acra_company(payload: AcraCompanyPayload) -> CanonicalLegalEntity:
    """Transform one source payload without leaking the source shape downstream."""

    address = payload.registered_address
    canonical_address = None
    if address is not None:
        canonical_address = RegisteredAddress(
            address_line_1=f"{address.block} {address.street}",
            address_line_2=address.unit,
            postal_code=address.postal_code,
            country_code=address.country_code,
        )

    return CanonicalLegalEntity(
        registration_number=payload.uen,
        legal_name=payload.entity_name,
        country_of_incorporation=payload.country_code,
        party_type=payload.entity_type,
        registered_address=canonical_address,
        source=SourceMetadata(
            source_system=SourceSystem.ACRA,
            environment=SourceEnvironment(payload.source_environment),
            registry_source_link=payload.source_endpoint,
            retrieved_at=payload.retrieved_at,
        ),
    )
