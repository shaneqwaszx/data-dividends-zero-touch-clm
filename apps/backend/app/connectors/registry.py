"""Provider-neutral registry acquisition boundary and Singapore ACRA adapter."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.connectors.acra import (
    AcraCompanyPayload,
    AcraConnector,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
from app.connectors.errors import (
    AcraMalformedResponseError,
    AcraMappingError,
    AcraOperationUnsupportedError,
    AcraResponseIdentityMismatchError,
    AcraResponseInvalidError,
    AcraTimeoutError,
    AcraUnexpectedMappingError,
    ConnectorError,
)
from app.domain.jurisdiction import (
    JurisdictionCode,
    RegistryProviderCode,
    RegistryRoutingDecision,
    RegistryRoutingStatus,
    is_eligible_singapore_uen,
)
from app.domain.models import (
    CanonicalLegalEntity,
    RegistryAcquisitionBundle,
    RegistryAcquisitionIssue,
    RegistryAcquisitionStatus,
    RegistryEvidenceProvenance,
    RegistryOfficer,
    RegistryOperation,
    RegistryOperationResult,
    RegistryOperationStatus,
    RegistryOwnershipParty,
    RegistryPartyType,
    RegistryProviderIdentity,
    RegistryRelationship,
    RegistryRelationshipType,
    SourceEnvironment,
    SourceSystem,
)
from app.mappers.acra import map_acra_company
from app.mappers.errors import MappingError

CollectionPayload = TypeVar(
    "CollectionPayload",
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
NormalizedRecord = TypeVar(
    "NormalizedRecord", RegistryOfficer, RegistryOwnershipParty, RegistryRelationship
)


class RegistryProvider(Protocol):
    """Return normalized registry evidence without leaking provider DTOs."""

    provider_code: RegistryProviderCode
    cache_identity: RegistryProviderIdentity | None

    def retrieve_acquisition(self, identifier: str) -> RegistryAcquisitionBundle | None:
        """Run the bounded acquisition sequence for one registration identifier."""


class AcraIdentifierNotEligibleError(ValueError):
    """A fixed, safe domain error raised before an ineligible ACRA request."""

    def __init__(self) -> None:
        super().__init__("The identifier is not eligible for Singapore ACRA retrieval.")


class AcraRegistryProviderAdapter:
    """Strictly normalize project-owned ACRA Mock operations into one bundle."""

    provider_code = RegistryProviderCode.ACRA
    ACQUISITION_CONTRACT_VERSION = "PHASE10_ACQUISITION_V1"

    def __init__(
        self,
        connector: AcraConnector,
        *,
        clock: Callable[[], datetime] | None = None,
        cache_identity: RegistryProviderIdentity | None = None,
    ) -> None:
        self._connector = connector
        self._clock = clock or (lambda: datetime.now(UTC))
        self.cache_identity = cache_identity

    def retrieve_company(self, identifier: str) -> CanonicalLegalEntity | None:
        """Compatibility seam retaining Phase 09 entity-profile behavior."""

        normalized_identifier = self._require_eligible_identifier(identifier)
        source_payload = self._connector.fetch_company(normalized_identifier)
        if source_payload is None:
            return None
        try:
            validated_payload = AcraCompanyPayload.model_validate(
                _untrusted_to_primitives(source_payload)
            )
        except Exception as exc:
            raise AcraResponseInvalidError(exc) from None
        if validated_payload.uen.strip().upper() != normalized_identifier:
            raise AcraResponseIdentityMismatchError from None
        try:
            return map_acra_company(validated_payload)
        except MappingError as exc:
            raise AcraMappingError(exc) from None
        except Exception as exc:
            raise AcraUnexpectedMappingError(exc) from None

    def retrieve_acquisition(self, identifier: str) -> RegistryAcquisitionBundle | None:
        normalized_identifier = self._require_eligible_identifier(identifier)
        entity = self.retrieve_company(normalized_identifier)
        if entity is None:
            return None

        entity_provenance = RegistryEvidenceProvenance(
            provider=SourceSystem.ACRA,
            environment=entity.source.environment,
            operation=RegistryOperation.ENTITY_PROFILE,
            retrieved_at=entity.source.retrieved_at,
            evidence_reference=_evidence_reference(
                RegistryOperation.ENTITY_PROFILE, normalized_identifier
            ),
        )
        results: list[RegistryOperationResult] = [
            RegistryOperationResult(
                operation=RegistryOperation.ENTITY_PROFILE,
                status=RegistryOperationStatus.COMPLETE,
                record_count=1,
                provenance=entity_provenance,
            )
        ]

        officers, officer_result = self._retrieve_collection(
            identifier=normalized_identifier,
            operation=RegistryOperation.OFFICERS,
            fetch=self._connector.fetch_officers,
            payload_type=AcraOfficersPayload,
            collection_name="officers",
            normalize=lambda item, provenance: RegistryOfficer(
                officer_id=item.officer_id,
                name=item.name,
                role=item.role,
                appointment_date=item.appointment_date,
                cessation_date=item.cessation_date,
                country=item.country.upper() if item.country is not None else None,
                provenance=provenance,
            ),
            environment=entity.source.environment,
        )
        results.append(officer_result)
        if officer_result.status == RegistryOperationStatus.FAILED:
            return self._failed_bundle(
                normalized_identifier, entity, officers=(), results=results
            )

        ownership_parties, ownership_result = self._retrieve_collection(
            identifier=normalized_identifier,
            operation=RegistryOperation.OWNERSHIP_PARTIES,
            fetch=self._connector.fetch_ownership_parties,
            payload_type=AcraOwnershipPartiesPayload,
            collection_name="ownership_parties",
            normalize=lambda item, provenance: RegistryOwnershipParty(
                party_id=item.party_id,
                party_type=RegistryPartyType(item.party_type),
                name=item.name,
                registration_identifier=item.registration_identifier,
                country=item.country.upper() if item.country is not None else None,
                ownership_percentage=item.ownership_percentage,
                provenance=provenance,
            ),
            environment=entity.source.environment,
        )
        results.append(ownership_result)
        if ownership_result.status == RegistryOperationStatus.FAILED:
            return self._failed_bundle(
                normalized_identifier,
                entity,
                officers=officers,
                results=results,
            )

        relationships, relationship_result = self._retrieve_collection(
            identifier=normalized_identifier,
            operation=RegistryOperation.RELATIONSHIPS,
            fetch=self._connector.fetch_relationships,
            payload_type=AcraRelationshipsPayload,
            collection_name="relationships",
            normalize=lambda item, provenance: RegistryRelationship(
                relationship_id=item.relationship_id,
                owned_entity_id=item.owned_entity_id,
                owner_party_id=item.owner_party_id,
                relationship_type=RegistryRelationshipType(item.relationship_type),
                ownership_percentage=item.ownership_percentage,
                provenance=provenance,
            ),
            environment=entity.source.environment,
        )
        results.append(relationship_result)
        if relationship_result.status == RegistryOperationStatus.FAILED:
            return self._failed_bundle(
                normalized_identifier,
                entity,
                officers=officers,
                ownership_parties=ownership_parties,
                results=results,
            )

        issues: tuple[RegistryAcquisitionIssue, ...] = ()
        status = RegistryAcquisitionStatus.COMPLETE
        if not ownership_parties or not relationships:
            status = RegistryAcquisitionStatus.PARTIAL
            issues = (
                RegistryAcquisitionIssue(
                    code="REGISTRY_EXPECTED_DATA_MISSING",
                    message="Expected registry ownership evidence was not returned.",
                ),
            )
        try:
            return RegistryAcquisitionBundle(
                requested_identifier=normalized_identifier,
                root_party_id=f"ENTITY_{normalized_identifier}",
                entity_profile=entity,
                officers=officers,
                ownership_parties=ownership_parties,
                relationships=relationships,
                operation_results=tuple(results),
                status=status,
                issues=issues,
                retrieved_at=max(
                    result.provenance.retrieved_at
                    for result in results
                    if result.provenance is not None
                ),
            )
        except ValidationError:
            results[-1] = self._failed_result(
                RegistryOperation.RELATIONSHIPS,
                entity.source.environment,
                normalized_identifier,
                code="REGISTRY_OPERATION_MALFORMED_RESPONSE",
                message="Registry relationship data could not be validated safely.",
            )
            return self._failed_bundle(
                normalized_identifier,
                entity,
                officers=officers,
                ownership_parties=ownership_parties,
                results=results,
            )

    def _retrieve_collection(
        self,
        *,
        identifier: str,
        operation: RegistryOperation,
        fetch: Callable[[str], object],
        payload_type: type[CollectionPayload],
        collection_name: str,
        normalize: Callable[[Any, RegistryEvidenceProvenance], NormalizedRecord],
        environment: SourceEnvironment,
    ) -> tuple[tuple[NormalizedRecord, ...], RegistryOperationResult]:
        try:
            payload = payload_type.model_validate(
                _untrusted_to_primitives(fetch(identifier))
            )
            if payload.uen.strip().upper() != identifier:
                raise ValueError("registry operation identity mismatch")
            source_environment = SourceEnvironment(payload.source_environment)
            if source_environment != environment:
                raise ValueError("registry operation environment mismatch")
            provenance = RegistryEvidenceProvenance(
                provider=SourceSystem.ACRA,
                environment=source_environment,
                operation=operation,
                retrieved_at=payload.retrieved_at,
                evidence_reference=_evidence_reference(operation, identifier),
            )
            records = tuple(
                normalize(item, provenance)
                for item in getattr(payload, collection_name)
            )
            return records, RegistryOperationResult(
                operation=operation,
                status=(
                    RegistryOperationStatus.COMPLETE
                    if records
                    else RegistryOperationStatus.EMPTY
                ),
                record_count=len(records),
                provenance=provenance,
            )
        except AcraOperationUnsupportedError:
            return (), RegistryOperationResult(
                operation=operation,
                status=RegistryOperationStatus.UNSUPPORTED,
                record_count=0,
            )
        except ConnectorError as exc:
            code, message = _operation_error(exc)
        except Exception:
            code = "REGISTRY_OPERATION_MALFORMED_RESPONSE"
            message = "Registry operation data could not be validated safely."
        return (), self._failed_result(
            operation,
            environment,
            identifier,
            code=code,
            message=message,
        )

    def _failed_result(
        self,
        operation: RegistryOperation,
        environment: SourceEnvironment,
        identifier: str,
        *,
        code: str,
        message: str,
    ) -> RegistryOperationResult:
        return RegistryOperationResult(
            operation=operation,
            status=RegistryOperationStatus.FAILED,
            record_count=0,
            provenance=RegistryEvidenceProvenance(
                provider=SourceSystem.ACRA,
                environment=environment,
                operation=operation,
                retrieved_at=self._clock(),
                evidence_reference=_evidence_reference(operation, identifier),
            ),
            error=RegistryAcquisitionIssue(code=code, message=message),
        )

    def _failed_bundle(
        self,
        identifier: str,
        entity: CanonicalLegalEntity,
        *,
        officers: tuple[RegistryOfficer, ...],
        results: list[RegistryOperationResult],
        ownership_parties: tuple[RegistryOwnershipParty, ...] = (),
    ) -> RegistryAcquisitionBundle:
        while len(results) < len(RegistryOperation):
            results.append(
                RegistryOperationResult(
                    operation=tuple(RegistryOperation)[len(results)],
                    status=RegistryOperationStatus.NOT_ATTEMPTED,
                    record_count=0,
                )
            )
        failed = next(
            item.error
            for item in results
            if item.status == RegistryOperationStatus.FAILED and item.error is not None
        )
        return RegistryAcquisitionBundle(
            requested_identifier=identifier,
            root_party_id=f"ENTITY_{identifier}",
            entity_profile=entity,
            officers=officers,
            ownership_parties=ownership_parties,
            relationships=(),
            operation_results=tuple(results),
            status=RegistryAcquisitionStatus.FAILED,
            issues=(failed,),
            retrieved_at=max(
                item.provenance.retrieved_at
                for item in results
                if item.provenance is not None
            ),
        )

    @staticmethod
    def _require_eligible_identifier(identifier: str) -> str:
        normalized_identifier = identifier.strip().upper()
        if not is_eligible_singapore_uen(normalized_identifier):
            raise AcraIdentifierNotEligibleError
        return normalized_identifier


class RegistryProviderRouter:
    """Closed routing table: Singapore selects ACRA; all other providers stop."""

    def __init__(self, acra: RegistryProvider) -> None:
        if acra.provider_code != RegistryProviderCode.ACRA:
            raise ValueError("Singapore registry provider must identify as ACRA")
        self._acra = acra

    def route(
        self, jurisdiction: JurisdictionCode, *, decided_at: datetime
    ) -> tuple[RegistryRoutingDecision, RegistryProvider | None]:
        if jurisdiction == JurisdictionCode.SINGAPORE:
            return (
                RegistryRoutingDecision(
                    status=RegistryRoutingStatus.SELECTED,
                    jurisdiction=jurisdiction,
                    provider=RegistryProviderCode.ACRA,
                    decided_at=decided_at,
                ),
                self._acra,
            )
        return (
            RegistryRoutingDecision(
                status=RegistryRoutingStatus.PROVIDER_NOT_IMPLEMENTED,
                jurisdiction=jurisdiction,
                decided_at=decided_at,
            ),
            None,
        )


def _operation_error(error: ConnectorError) -> tuple[str, str]:
    if isinstance(error, AcraTimeoutError):
        return "REGISTRY_OPERATION_TIMEOUT", "Registry operation timed out."
    if isinstance(error, (AcraMalformedResponseError, AcraResponseInvalidError)):
        return (
            "REGISTRY_OPERATION_MALFORMED_RESPONSE",
            "Registry operation data could not be validated safely.",
        )
    return "REGISTRY_OPERATION_UNAVAILABLE", "Registry operation could not be completed."


def _evidence_reference(operation: RegistryOperation, identifier: str) -> str:
    return f"acra:{operation.value.lower()}:{identifier}"


def _untrusted_to_primitives(value: object) -> object:
    if isinstance(value, BaseModel):
        return _untrusted_to_primitives(value.model_dump(mode="python", round_trip=True))
    if isinstance(value, dict):
        return {key: _untrusted_to_primitives(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_untrusted_to_primitives(item) for item in value]
    return value
