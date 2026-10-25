"""Provider-neutral registry acquisition boundary and Singapore ACRA adapter."""

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.connectors.acra import (
    AcraCompanyPayload,
    AcraConnector,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraOwnershipPartyPayload,
    AcraRelationshipsPayload,
)
from app.connectors.acra_api_marketplace_mock import (
    AcraApiMarketplaceMockConnector,
    AcraBusinessProfilePayload,
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
    RegistryBusinessProfileEvidence,
    RegistryBusinessProfileShareholder,
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
    RegistryShareCapital,
    RegistryShareholderEvidence,
    SourceEnvironment,
    SourceSystem,
)
from app.domain.registry_legal_form import RegistryLegalForm, classify_registry_legal_form
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


def _normalize_ownership_party(
    item: AcraOwnershipPartyPayload,
    provenance: RegistryEvidenceProvenance,
    *,
    share_class: bool = False,
) -> RegistryOwnershipParty:
    return RegistryOwnershipParty(
        party_id=item.party_id,
        party_type=RegistryPartyType(item.party_type),
        name=item.name,
        registration_identifier=item.registration_identifier,
        country=item.country.upper() if item.country is not None else None,
        ownership_percentage=item.ownership_percentage,
        source_category=item.source_category,
        source_status=item.source_status,
        share_allotted=item.share_allotted,
        share_type=item.share_type if share_class else None,
        currency=item.currency if share_class else None,
        provenance=provenance,
    )


def _normalize_shareholder_evidence_party(
    item: AcraOwnershipPartyPayload, provenance: RegistryEvidenceProvenance
) -> RegistryOwnershipParty:
    """D-080: entity-less shareholder evidence also keeps the source share class."""
    return _normalize_ownership_party(item, provenance, share_class=True)


class RegistryProvider(Protocol):
    """Return normalized registry evidence without leaking provider DTOs."""

    provider_code: RegistryProviderCode
    cache_identity: RegistryProviderIdentity | None

    def retrieve_acquisition(
        self,
        identifier: str,
        *,
        reuse: RegistryAcquisitionBundle | None = None,
        reuse_operations: frozenset[RegistryOperation] = frozenset(),
    ) -> RegistryAcquisitionBundle | None:
        """Run the bounded acquisition sequence for one registration identifier."""


class ShareholderEvidenceProvider(Protocol):
    """D-079 capability: one issuer's shareholder operation without an entity profile."""

    cache_identity: RegistryProviderIdentity | None

    @property
    def supports_shareholder_evidence(self) -> bool: ...

    def retrieve_shareholder_evidence(self, identifier: str) -> RegistryShareholderEvidence:
        """Read only the shareholder operation for one registration identifier."""


class BusinessProfileEvidenceProvider(Protocol):
    """D-088 capability: one issuer's businessProfile operation without an entity profile."""

    cache_identity: RegistryProviderIdentity | None

    @property
    def supports_business_profile_evidence(self) -> bool: ...

    def retrieve_business_profile_evidence(
        self, identifier: str
    ) -> RegistryBusinessProfileEvidence:
        """Read only the businessProfile operation for one registration identifier."""


def business_profile_holder_id(issuer_uen: str, source_id: str) -> str:
    """Issuer-scoped pseudonymous holder identifier; the source identifier is never kept.

    An unkeyed digest: it is not irreversible for small identifier spaces (an NRIC/FIN
    format can be enumerated), so it is Mock-only pseudonymisation. Any non-Mock use
    needs a keyed digest under a server-held secret first.
    """
    digest = sha256(f"{issuer_uen}\x00{source_id.strip().upper()}".encode()).hexdigest()
    return f"BP-{digest[:24]}"


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
        company_shareholders_only: bool = False,
    ) -> None:
        self._connector = connector
        self._clock = clock or (lambda: datetime.now(UTC))
        self.cache_identity = cache_identity
        self._company_shareholders_only = company_shareholders_only

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

    @property
    def supports_shareholder_evidence(self) -> bool:
        """Only the official Marketplace Mock composition reads shareholders alone."""
        return self._company_shareholders_only and isinstance(
            self._connector, AcraApiMarketplaceMockConnector
        )

    def retrieve_shareholder_evidence(self, identifier: str) -> RegistryShareholderEvidence:
        """Read only an issuer's own shareholder operation, never its entity profile.

        D-079: used after a definitive entity-basic NOT_FOUND for an identified corporate
        holder. The shared collection path binds the returned UEN, records operation
        provenance and maps failures safely; no identity, legal form or percentage is
        derived, and no other operation is dispatched.
        """
        normalized_identifier = self._require_eligible_identifier(identifier)
        if not self.supports_shareholder_evidence:
            raise AcraOperationUnsupportedError
        parties, result = self._retrieve_collection(
            identifier=normalized_identifier,
            operation=RegistryOperation.OWNERSHIP_PARTIES,
            fetch=self._connector.fetch_ownership_parties,
            payload_type=AcraOwnershipPartiesPayload,
            collection_name="ownership_parties",
            normalize=_normalize_shareholder_evidence_party,
            environment=SourceEnvironment.MOCK,
        )
        return RegistryShareholderEvidence(
            requested_identifier=normalized_identifier,
            operation_result=result,
            ownership_parties=parties,
        )

    @property
    def supports_business_profile_evidence(self) -> bool:
        """Only the official Marketplace Mock composition reads business profiles."""
        return self.supports_shareholder_evidence

    def retrieve_business_profile_evidence(
        self, identifier: str
    ) -> RegistryBusinessProfileEvidence:
        """D-088: read only an issuer's own businessProfile operation.

        Used only for a scenario-named corporate holder whose entity profile and
        shareholder operation are both empty. The returned UEN is bound, every failure is
        a safe FAILED result, and no identity, legal form or percentage is derived.
        """
        normalized_identifier = self._require_eligible_identifier(identifier)
        if not self.supports_business_profile_evidence:
            raise AcraOperationUnsupportedError
        connector = self._connector
        assert isinstance(connector, AcraApiMarketplaceMockConnector)
        reference = f"acra:business_profile:{normalized_identifier}"
        try:
            payload = AcraBusinessProfilePayload.model_validate(
                _untrusted_to_primitives(connector.fetch_business_profile(normalized_identifier))
            )
            if payload.uen.strip().upper() != normalized_identifier:
                raise ValueError("business profile identity mismatch")
            if not payload.entity_present:
                return RegistryBusinessProfileEvidence(
                    requested_identifier=normalized_identifier,
                    status="EMPTY",
                    environment=SourceEnvironment.MOCK,
                    retrieved_at=payload.retrieved_at,
                    evidence_reference=reference,
                )
            return RegistryBusinessProfileEvidence(
                requested_identifier=normalized_identifier,
                status="COMPLETE",
                environment=SourceEnvironment.MOCK,
                retrieved_at=payload.retrieved_at,
                evidence_reference=reference,
                entity_name=payload.entity_name,
                company_type=payload.company_type,
                status_of_company=payload.status_of_company,
                shareholders=tuple(
                    RegistryBusinessProfileShareholder(
                        party_id=business_profile_holder_id(normalized_identifier, row.source_id),
                        party_type=RegistryPartyType(row.party_type),
                        name=row.name,
                        source_category=row.source_category,
                        source_status=row.source_status,
                        number_of_shares=row.number_of_shares,
                        share_type=row.share_type,
                        currency=row.currency,
                    )
                    for row in payload.shareholders
                ),
                issued_share_capital=tuple(
                    RegistryShareCapital.model_validate(line.model_dump())
                    for line in payload.issued_share_capital
                ),
                paid_up_capital=tuple(
                    RegistryShareCapital.model_validate(line.model_dump())
                    for line in payload.paid_up_capital
                ),
            )
        except ConnectorError as exc:
            code, _ = _operation_error(exc)
        except Exception:
            code = "REGISTRY_OPERATION_MALFORMED_RESPONSE"
        return RegistryBusinessProfileEvidence(
            requested_identifier=normalized_identifier,
            status="FAILED",
            environment=SourceEnvironment.MOCK,
            retrieved_at=self._clock(),
            evidence_reference=reference,
            error_code=code,
        )

    @staticmethod
    def _unsupported_ownership(identifier: str) -> AcraOwnershipPartiesPayload:
        del identifier
        raise AcraOperationUnsupportedError

    @staticmethod
    def _unsupported_relationships(identifier: str) -> AcraRelationshipsPayload:
        del identifier
        raise AcraOperationUnsupportedError

    def retrieve_acquisition(
        self,
        identifier: str,
        *,
        reuse: RegistryAcquisitionBundle | None = None,
        reuse_operations: frozenset[RegistryOperation] = frozenset(),
    ) -> RegistryAcquisitionBundle | None:
        normalized_identifier = self._require_eligible_identifier(identifier)
        if reuse is not None:
            reuse = RegistryAcquisitionBundle.model_validate(reuse.model_dump())
            if reuse.requested_identifier != normalized_identifier:
                raise AcraResponseIdentityMismatchError
        entity = (
            reuse.entity_profile.model_copy(deep=True)
            if reuse is not None and RegistryOperation.ENTITY_PROFILE in reuse_operations
            else self.retrieve_company(normalized_identifier)
        )
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

        def retrieve_collection(**kwargs: Any) -> tuple[tuple[Any, ...], RegistryOperationResult]:
            operation = kwargs["operation"]
            if reuse is not None and operation in reuse_operations:
                result = next(
                    item for item in reuse.operation_results if item.operation == operation
                )
                if result.status not in {
                    RegistryOperationStatus.COMPLETE,
                    RegistryOperationStatus.EMPTY,
                }:
                    raise AcraResponseInvalidError
                return getattr(reuse, kwargs["collection_name"]), result
            return self._retrieve_collection(**kwargs)

        officers, officer_result = retrieve_collection(
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
            return self._failed_bundle(normalized_identifier, entity, officers=(), results=results)

        company_method_inapplicable = (
            self._company_shareholders_only
            and classify_registry_legal_form(entity.party_type) != RegistryLegalForm.COMPANY
        )
        ownership_parties, ownership_result = retrieve_collection(
            identifier=normalized_identifier,
            operation=RegistryOperation.OWNERSHIP_PARTIES,
            fetch=(
                self._unsupported_ownership
                if company_method_inapplicable
                else self._connector.fetch_ownership_parties
            ),
            payload_type=AcraOwnershipPartiesPayload,
            collection_name="ownership_parties",
            normalize=_normalize_ownership_party,
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

        relationships, relationship_result = retrieve_collection(
            identifier=normalized_identifier,
            operation=RegistryOperation.RELATIONSHIPS,
            fetch=(
                self._unsupported_relationships
                if company_method_inapplicable
                else self._connector.fetch_relationships
            ),
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
            payload = payload_type.model_validate(_untrusted_to_primitives(fetch(identifier)))
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
                normalize(item, provenance) for item in getattr(payload, collection_name)
            )
            return records, RegistryOperationResult(
                operation=operation,
                status=(
                    RegistryOperationStatus.COMPLETE if records else RegistryOperationStatus.EMPTY
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
                item.provenance.retrieved_at for item in results if item.provenance is not None
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
