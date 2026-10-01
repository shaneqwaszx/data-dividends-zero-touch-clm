"""Normalize registry acquisition evidence into the existing ownership boundary."""

from typing import Protocol
from uuid import UUID

from app.connectors.ownership import (
    OwnershipProviderError,
    OwnershipProviderMetadata,
    OwnershipProviderRequest,
    OwnershipSourceResult,
)
from app.domain.models import OnboardingCase, RegistryAcquisitionStatus, SourceEnvironment
from app.domain.ownership import (
    OwnershipEnvironment,
    OwnershipProvenance,
    OwnershipRelationship,
    Party,
    PartyType,
)


class RegistryCaseReader(Protocol):
    def get_case(self, case_id: UUID) -> OnboardingCase | None: ...


class RegistryAcquisitionOwnershipProvider:
    """Feed Mock ACRA ownership evidence to the authoritative Decimal graph engine."""

    def __init__(self, cases: RegistryCaseReader) -> None:
        self._cases = cases

    @property
    def metadata(self) -> object:
        return OwnershipProviderMetadata(
            provider_name="ACRA_REGISTRY_ACQUISITION",
            environment=OwnershipEnvironment.MOCK,
        )

    def load(self, request: OwnershipProviderRequest) -> object:
        case = self._cases.get_case(request.case_id)
        acquisition = case.registry_acquisition if case is not None else None
        if (
            case is None
            or acquisition is None
            or acquisition.status
            not in {RegistryAcquisitionStatus.COMPLETE, RegistryAcquisitionStatus.PARTIAL}
            or acquisition.entity_profile.source.environment != SourceEnvironment.MOCK
            or acquisition.requested_identifier != request.registration_number
        ):
            raise OwnershipProviderError

        parties = [
            Party(
                party_id=acquisition.root_party_id,
                display_name=request.display_name,
                party_type=PartyType.LEGAL_ENTITY,
                registration_number=request.registration_number,
                country=acquisition.entity_profile.country_of_incorporation,
            )
        ]
        parties.extend(
            Party(
                party_id=item.party_id,
                display_name=item.name,
                party_type=PartyType(item.party_type.value),
                registration_number=item.registration_identifier,
                country=item.country,
            )
            for item in acquisition.ownership_parties
        )
        relationships = [
            OwnershipRelationship(
                relationship_id=item.relationship_id,
                parent_party_id=item.owned_entity_id,
                child_party_id=item.owner_party_id,
                ownership_percent=item.ownership_percentage,
                provenance=OwnershipProvenance(
                    provider="ACRA_REGISTRY_ACQUISITION",
                    environment=OwnershipEnvironment.MOCK,
                    source_reference=f"ACRA_REGISTRY_{item.relationship_id}",
                    sourced_at=item.provenance.retrieved_at,
                ),
            )
            for item in acquisition.relationships
        ]
        return OwnershipSourceResult(
            root_party_id=acquisition.root_party_id,
            parties=parties,
            relationships=relationships,
        )
