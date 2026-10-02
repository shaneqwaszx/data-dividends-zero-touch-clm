"""Normalize registry acquisition evidence into the existing ownership boundary."""

from decimal import Decimal
from hashlib import sha256
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
from app.domain.ownership_evidence import OwnershipEvidence, OwnershipEvidenceKind
from app.domain.registry_legal_form import classify_registry_legal_form


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
        evidence: list[OwnershipEvidence] = []
        entity_identifiers = {party.party_id: party.registration_number for party in parties}
        # An edge identifies the immediately owned entity, even in a flattened tree.
        for edge in acquisition.relationships:
            evidence.append(
                OwnershipEvidence(
                    evidence_id=_evidence_id(edge.relationship_id, "DIRECT_PERCENTAGE"),
                    entity_identifier=entity_identifiers[edge.owned_entity_id],
                    party_id=edge.owner_party_id,
                    kind=OwnershipEvidenceKind.DIRECT_PERCENTAGE,
                    raw_value=format(edge.ownership_percentage, "f"),
                    numeric_value=edge.ownership_percentage,
                    source_operation=edge.provenance.operation.value,
                    provider="ACRA_REGISTRY_ACQUISITION",
                    environment="MOCK",
                    retrieved_at=edge.provenance.retrieved_at,
                    evidence_version=len(case.events),
                    determination_basis="PROVIDER_PERCENTAGE",
                )
            )
        for item in acquisition.ownership_parties:
            owned_entities = {
                edge.owned_entity_id
                for edge in acquisition.relationships
                if edge.owner_party_id == item.party_id
            }
            binding = (
                entity_identifiers[next(iter(owned_entities))]
                if len(owned_entities) == 1
                else acquisition.requested_identifier
                if not acquisition.relationships
                else None
            )
            scalars: list[tuple[OwnershipEvidenceKind, str, str | None]] = []
            if item.share_allotted is not None:
                scalars.append(
                    (
                        OwnershipEvidenceKind.SHARE_UNITS,
                        format(item.share_allotted, "f"),
                        format(item.share_allotted, "f"),
                    )
                )
            represented_percentage = any(
                edge.owner_party_id == item.party_id
                and edge.ownership_percentage == item.ownership_percentage
                for edge in acquisition.relationships
            )
            if item.ownership_percentage is not None and not represented_percentage:
                scalars.append(
                    (
                        OwnershipEvidenceKind.DIRECT_PERCENTAGE,
                        format(item.ownership_percentage, "f"),
                        format(item.ownership_percentage, "f"),
                    )
                )
            if (
                not scalars
                and not represented_percentage
                and (not owned_entities or item.source_category is not None)
            ):
                scalars.append(
                    (OwnershipEvidenceKind.UNKNOWN, item.source_category or "UNKNOWN", None)
                )
            for kind, raw, numeric in scalars:
                evidence.append(
                    OwnershipEvidence(
                        evidence_id=_evidence_id(item.party_id, kind.value),
                        entity_identifier=(
                            None
                            if kind == OwnershipEvidenceKind.DIRECT_PERCENTAGE
                            and acquisition.relationships
                            else binding
                        ),
                        party_id=item.party_id,
                        kind=kind,
                        raw_value=raw,
                        numeric_value=Decimal(numeric) if numeric is not None else None,
                        source_operation=item.provenance.operation.value,
                        provider="ACRA_REGISTRY_ACQUISITION",
                        environment="MOCK",
                        retrieved_at=item.provenance.retrieved_at,
                        source_status=item.source_status,
                        evidence_version=len(case.events),
                        determination_basis=(
                            "PROVIDER_PERCENTAGE"
                            if kind == OwnershipEvidenceKind.DIRECT_PERCENTAGE
                            else "SOURCE_SCALAR"
                        ),
                    )
                )
        for officer in acquisition.officers:
            evidence.append(
                OwnershipEvidence(
                    evidence_id=_evidence_id(officer.officer_id, "ROLE"),
                    entity_identifier=acquisition.requested_identifier,
                    party_id=officer.officer_id,
                    kind=OwnershipEvidenceKind.ROLE,
                    raw_value=officer.role,
                    source_operation=officer.provenance.operation.value,
                    provider="ACRA_REGISTRY_ACQUISITION",
                    environment="MOCK",
                    retrieved_at=officer.provenance.retrieved_at,
                    source_status="CEASED" if officer.cessation_date is not None else None,
                    evidence_version=len(case.events),
                )
            )
        return OwnershipSourceResult(
            root_party_id=acquisition.root_party_id,
            parties=parties,
            relationships=relationships,
            evidence=tuple(evidence),
            legal_form=classify_registry_legal_form(acquisition.entity_profile.party_type),
        )


def _evidence_id(party_id: str, kind: str) -> str:
    return "e-" + sha256(f"{party_id}:{kind}".encode()).hexdigest()[:48]
