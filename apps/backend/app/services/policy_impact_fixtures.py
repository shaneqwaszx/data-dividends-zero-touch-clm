"""Versioned synthetic inputs only; no policy decisions, case reads or provider calls."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.connectors.ownership import OwnershipSourceResult
from app.domain.documents import (
    ComparisonStatus,
    DocumentFieldKey,
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
    ExtractedField,
    FieldProvenance,
    IdpEnvironment,
)
from app.domain.models import CanonicalLegalEntity, SourceMetadata
from app.domain.ownership import OwnershipProvenance, OwnershipRelationship, Party, PartyType

FIXTURE_NOW = datetime(2026, 1, 1, tzinfo=UTC)
FIXTURE_EPSILON = Decimal("0.000001")
DOCUMENT_CONFIDENCES = ("0.84", "0.85", "0.90", "0.97")
REGISTRY_AGES_DAYS = (1, 29, 31, 45, 89, 91)
NEGATIVE_AGES_SECONDS = (60, 300, 660)
OWNERSHIP_PERCENTAGES = ("24.999999", "25", "27", "30")


def synthetic_entity() -> CanonicalLegalEntity:
    return CanonicalLegalEntity(
        registration_number="202400001A",
        legal_name="Synthetic Impact Company",
        country_of_incorporation="SG",
        source=SourceMetadata(
            source_system="ACRA",
            environment="MOCK",
            registry_source_link="https://example.invalid/synthetic-policy-impact",
            retrieved_at=FIXTURE_NOW,
        ),
    )


def document_fixture(confidence: Decimal, variant: str = "MATCH") -> DocumentProcessingRecord:
    entity = synthetic_entity()
    values = {
        DocumentFieldKey.REGISTRATION_NUMBER: entity.registration_number,
        DocumentFieldKey.LEGAL_NAME: entity.legal_name,
        DocumentFieldKey.COUNTRY_OF_INCORPORATION: entity.country_of_incorporation,
    }
    fields = [
        ExtractedField(
            field_key=key,
            original_extracted_value=value,
            normalized_value=value,
            canonical_value=value,
            confidence=float(confidence) if key == DocumentFieldKey.LEGAL_NAME else 1.0,
            comparison_status=ComparisonStatus.MATCH,
            provenance=FieldProvenance(
                provider="SYNTHETIC_IMPACT",
                environment=IdpEnvironment.LOCAL,
                source_reference="SYNTHETIC_FIXTURE",
            ),
        )
        for key, value in values.items()
    ]
    if variant == "MISSING":
        fields = [f for f in fields if f.field_key != DocumentFieldKey.LEGAL_NAME]
    elif variant == "CONFLICT":
        fields[1].original_extracted_value = "Conflicting Synthetic Company"
        fields[1].normalized_value = fields[1].original_extracted_value
        fields[1].comparison_status = ComparisonStatus.MISMATCH
    elif variant == "TEXT_UNAVAILABLE":
        for f in fields:
            f.provenance.source_reference = "DOCUMENT_TEXT_UNAVAILABLE"
    record = DocumentProcessingRecord(
        case_id=UUID(int=1),
        document_id=UUID(int=2),
        correlation_id=UUID(int=3),
        display_name="synthetic-impact.txt",
        media_type="text/plain",
        size_bytes=1,
        profile=DocumentProfile.CERTIFICATE_OF_INCORPORATION_POC,
        provider_environment=IdpEnvironment.LOCAL,
        state=DocumentProcessingState.REVIEW_REQUIRED,
        fields=fields,
        created_at=FIXTURE_NOW,
        updated_at=FIXTURE_NOW,
    )
    if variant == "SUPERSEDED":
        record.superseded_by_document_id = UUID(int=4)
    return record


def ownership_fixture(kind: str, percent: Decimal = Decimal("27")) -> OwnershipSourceResult:
    root = Party(
        party_id="root", display_name="Synthetic Impact Root", party_type=PartyType.LEGAL_ENTITY
    )
    person = Party(
        party_id="person", display_name="Synthetic Owner A", party_type=PartyType.NATURAL_PERSON
    )
    parties = [root, person]
    edges: list[tuple[str, str, str]] = []
    if kind == "MULTIPATH":
        parties.append(
            Party(
                party_id="holding",
                display_name="Synthetic Holding",
                party_type=PartyType.LEGAL_ENTITY,
            )
        )
        edges = [("root", "person", "7"), ("root", "holding", "40"), ("holding", "person", "50")]
    elif kind == "INCOMPLETE":
        parties.append(
            Party(
                party_id="undisclosed",
                display_name="Synthetic Undisclosed Entity",
                party_type=PartyType.LEGAL_ENTITY,
            )
        )
        edges = [("root", "person", "27"), ("root", "undisclosed", "73")]
    elif kind == "DECLARATION_60_40":
        parties.append(
            Party(
                party_id="person-b",
                display_name="Synthetic Owner B",
                party_type=PartyType.NATURAL_PERSON,
            )
        )
        edges = [("root", "person", "60"), ("root", "person-b", "40")]
    else:
        edges = [("root", "person", str(percent))]
    provenance = OwnershipProvenance(
        provider="SYNTHETIC_IMPACT",
        environment="LOCAL",
        source_reference="SYNTHETIC_POLICY_IMPACT_V1",
        sourced_at=FIXTURE_NOW,
    )
    return OwnershipSourceResult(
        root_party_id="root",
        parties=parties,
        relationships=[
            OwnershipRelationship(
                relationship_id=f"fixture-edge-{i}",
                parent_party_id=parent,
                child_party_id=child,
                ownership_percent=Decimal(value),
                basis="ECONOMIC_INTEREST" if kind == "DECLARATION_60_40" else "SHARE_OWNERSHIP",
                provenance=provenance,
            )
            for i, (parent, child, value) in enumerate(edges)
        ],
    )
