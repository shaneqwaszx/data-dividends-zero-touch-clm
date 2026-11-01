"""Canonical onboarding and normalized registry-acquisition models."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.access import CasePriority, TeamId
from app.domain.jurisdiction import JurisdictionResolution, RegistryRoutingDecision
from app.domain.policy import (
    CasePolicyRebindAudit,
    CasePolicySnapshot,
    PolicyAuthority,
    legacy_phase13_policy_snapshot,
)
from app.domain.target_classification import TargetClassificationSelection

IDENTITY_RECHECK_HISTORY_LIMIT = 16


class WorkflowState(StrEnum):
    """Application workflow states exposed to the user."""

    REQUESTED = "REQUESTED"
    REGISTRY_FETCHED = "REGISTRY_FETCHED"
    VALIDATED = "VALIDATED"
    GT_SEARCHED = "GT_SEARCHED"
    GT_SHELL_CREATED = "GT_SHELL_CREATED"
    GT_POLICY_CREATED = "GT_POLICY_CREATED"
    GT_ENRICHED = "GT_ENRICHED"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class EventOutcome(StrEnum):
    """Safe outcome values for case history."""

    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class SourceSystem(StrEnum):
    """Business source independent of connector implementation mode."""

    ACRA = "ACRA"


class SourceEnvironment(StrEnum):
    """Environment in which source evidence was obtained."""

    MOCK = "MOCK"
    SANDBOX = "SANDBOX"


class RegisteredAddress(BaseModel):
    """Small canonical address needed by the Phase 01 UI and target mapper."""

    address_line_1: str
    address_line_2: str | None = None
    postal_code: str
    country_code: str = "SG"


class SourceMetadata(BaseModel):
    """Provenance for the canonical entity without retaining a raw payload."""

    source_system: SourceSystem
    environment: SourceEnvironment
    registry_source_link: str
    retrieved_at: datetime


class CanonicalLegalEntity(BaseModel):
    """Minimum source-neutral representation of a Singapore legal entity."""

    registration_number: str
    legal_name: str | None = None
    country_of_incorporation: str | None = None
    party_type: str | None = None
    registration_date: date | None = None
    entity_status: str | None = None
    registered_address: RegisteredAddress | None = None
    source: SourceMetadata


class RegistryOperation(StrEnum):
    """Project-owned acquisition operations pending authoritative ACRA details."""

    ENTITY_PROFILE = "ENTITY_PROFILE"
    OFFICERS = "OFFICERS"
    OWNERSHIP_PARTIES = "OWNERSHIP_PARTIES"
    RELATIONSHIPS = "RELATIONSHIPS"


class RegistryOperationStatus(StrEnum):
    COMPLETE = "COMPLETE"
    EMPTY = "EMPTY"
    FAILED = "FAILED"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    UNSUPPORTED = "UNSUPPORTED"


class RegistryAcquisitionStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RegistryPartyType(StrEnum):
    NATURAL_PERSON = "NATURAL_PERSON"
    LEGAL_ENTITY = "LEGAL_ENTITY"


class RegistryRelationshipType(StrEnum):
    SHARE_OWNERSHIP = "SHARE_OWNERSHIP"


RegistryOwnershipPercent = Annotated[
    Decimal,
    Field(gt=Decimal("0"), le=Decimal("100"), max_digits=12, decimal_places=6),
]


class RegistryAcquisitionIssue(BaseModel):
    """Stable provider-neutral issue safe for persistence and browser projection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    message: str = Field(min_length=1, max_length=200)


class RegistryEvidenceProvenance(BaseModel):
    """Opaque normalized provenance; raw connector URLs remain connector-internal."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    provider: SourceSystem
    environment: SourceEnvironment
    operation: RegistryOperation
    retrieved_at: datetime
    evidence_reference: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    )

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("registry evidence timestamp must be timezone-aware UTC")
        return value.astimezone(UTC)


class RegistryOfficer(BaseModel):
    """Project-owned normalized officer evidence with deliberately narrow fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    officer_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
    name: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=64)
    appointment_date: date | None = None
    cessation_date: date | None = None
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2,3}$")
    provenance: RegistryEvidenceProvenance


class RegistryOwnershipParty(BaseModel):
    """Registry ownership evidence; percentage is evidence, never a UBO result."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
    party_type: RegistryPartyType
    name: str = Field(min_length=1, max_length=160)
    registration_identifier: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2,3}$")
    ownership_percentage: RegistryOwnershipPercent | None = None
    source_category: str | None = Field(default=None, min_length=1, max_length=64)
    source_status: str | None = Field(default=None, min_length=1, max_length=64)
    share_allotted: Decimal | None = Field(
        default=None, ge=0, allow_inf_nan=False, max_digits=18, decimal_places=6
    )
    # D-080: source share class and currency, kept only on entity-less shareholder
    # evidence. Untrusted labels; units of different classes are never combined.
    share_type: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=1, max_length=64)
    provenance: RegistryEvidenceProvenance

    @field_validator("share_allotted", mode="before")
    @classmethod
    def exact_share_units(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("share units must be exact")
        return value


class RegistryRelationship(BaseModel):
    """Bounded normalized edge aligned with the existing ownership vocabulary."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    relationship_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
    owned_entity_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
    owner_party_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
    relationship_type: RegistryRelationshipType = RegistryRelationshipType.SHARE_OWNERSHIP
    ownership_percentage: RegistryOwnershipPercent
    provenance: RegistryEvidenceProvenance


class RegistryOperationResult(BaseModel):
    """One safe, provider-neutral acquisition operation summary."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    operation: RegistryOperation
    status: RegistryOperationStatus
    record_count: int = Field(ge=0, le=128)
    provenance: RegistryEvidenceProvenance | None = None
    error: RegistryAcquisitionIssue | None = None

    @model_validator(mode="after")
    def validate_status_shape(self) -> "RegistryOperationResult":
        if self.status == RegistryOperationStatus.COMPLETE:
            if self.record_count < 1 or self.provenance is None or self.error is not None:
                raise ValueError("complete registry operations require records and provenance")
        elif self.status == RegistryOperationStatus.EMPTY:
            if self.record_count != 0 or self.provenance is None or self.error is not None:
                raise ValueError("empty registry operations require provenance only")
        elif self.status == RegistryOperationStatus.FAILED:
            if self.record_count != 0 or self.provenance is None or self.error is None:
                raise ValueError("failed registry operations require provenance and a safe error")
        elif self.record_count != 0 or self.provenance is not None or self.error is not None:
            raise ValueError("unattempted or unsupported registry operations carry no result data")
        if self.provenance is not None and self.provenance.operation != self.operation:
            raise ValueError("operation provenance must identify the summarized operation")
        return self


class RegistryAcquisitionBundle(BaseModel):
    """Normalized multi-step registry evidence without any UBO conclusion."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    requested_identifier: str = Field(min_length=1, max_length=32)
    root_party_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
    entity_profile: CanonicalLegalEntity
    officers: tuple[RegistryOfficer, ...] = Field(default=(), max_length=32)
    ownership_parties: tuple[RegistryOwnershipParty, ...] = Field(default=(), max_length=64)
    relationships: tuple[RegistryRelationship, ...] = Field(default=(), max_length=128)
    operation_results: tuple[RegistryOperationResult, ...] = Field(min_length=4, max_length=4)
    status: RegistryAcquisitionStatus
    issues: tuple[RegistryAcquisitionIssue, ...] = Field(default=(), max_length=4)
    retrieved_at: datetime

    @field_validator("retrieved_at")
    @classmethod
    def bundle_time_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("registry acquisition timestamp must be timezone-aware UTC")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_bundle_consistency(self) -> "RegistryAcquisitionBundle":
        expected_operations = tuple(RegistryOperation)
        if tuple(item.operation for item in self.operation_results) != expected_operations:
            raise ValueError("registry operation results must be complete and ordered")

        results_by_operation = {item.operation: item for item in self.operation_results}
        expected_counts = {
            RegistryOperation.ENTITY_PROFILE: 1,
            RegistryOperation.OFFICERS: len(self.officers),
            RegistryOperation.OWNERSHIP_PARTIES: len(self.ownership_parties),
            RegistryOperation.RELATIONSHIPS: len(self.relationships),
        }
        for result in self.operation_results:
            evidence_count = expected_counts[result.operation]
            if result.record_count != evidence_count:
                raise ValueError("registry operation count does not match normalized evidence")
            if result.status == RegistryOperationStatus.COMPLETE and evidence_count == 0:
                raise ValueError("complete registry operations require normalized evidence")
            if (
                result.status
                in {
                    RegistryOperationStatus.EMPTY,
                    RegistryOperationStatus.FAILED,
                    RegistryOperationStatus.NOT_ATTEMPTED,
                    RegistryOperationStatus.UNSUPPORTED,
                }
                and evidence_count != 0
            ):
                raise ValueError("non-complete registry operations cannot retain evidence")
        # D-112 (owner O2, 2026-11-01): ownership parties keep the untrusted source class
        # and currency so mixed classes are detected; units of different classes are
        # never combined. (D-080 had kept them only on entity-less shareholder evidence.)

        entity_result = results_by_operation[RegistryOperation.ENTITY_PROFILE]
        if entity_result.status != RegistryOperationStatus.COMPLETE:
            raise ValueError("registry acquisition requires a complete entity profile")
        canonical_identifier = self.entity_profile.registration_number.strip()
        if canonical_identifier and canonical_identifier != self.requested_identifier:
            raise ValueError("registry entity profile must match the requested identifier")
        if self.root_party_id != f"ENTITY_{self.requested_identifier}":
            raise ValueError("registry root party must match the requested identifier")

        entity_provenance = entity_result.provenance
        if entity_provenance is None:
            raise ValueError("complete entity profile requires operation provenance")
        entity_source = self.entity_profile.source
        if (
            entity_provenance.provider != entity_source.source_system
            or entity_provenance.environment != entity_source.environment
            or entity_provenance.retrieved_at != entity_source.retrieved_at
        ):
            raise ValueError("entity operation provenance must match canonical source metadata")

        attempted_provenance = tuple(
            item.provenance for item in self.operation_results if item.provenance is not None
        )
        if any(
            provenance.provider != entity_source.source_system
            or provenance.environment != entity_source.environment
            for provenance in attempted_provenance
        ):
            raise ValueError("registry operation provenance must use one source and environment")
        if self.retrieved_at != max(provenance.retrieved_at for provenance in attempted_provenance):
            raise ValueError("registry acquisition timestamp must match its latest operation")

        collection_evidence = (
            (
                RegistryOperation.OFFICERS,
                tuple(item.provenance for item in self.officers),
            ),
            (
                RegistryOperation.OWNERSHIP_PARTIES,
                tuple(item.provenance for item in self.ownership_parties),
            ),
            (
                RegistryOperation.RELATIONSHIPS,
                tuple(item.provenance for item in self.relationships),
            ),
        )
        for operation, record_provenance in collection_evidence:
            result_provenance = results_by_operation[operation].provenance
            if any(provenance != result_provenance for provenance in record_provenance):
                raise ValueError("registry record provenance must match its operation result")

        officer_ids = [officer.officer_id for officer in self.officers]
        if len(officer_ids) != len(set(officer_ids)):
            raise ValueError("registry officer IDs must be unique")
        party_ids = [party.party_id for party in self.ownership_parties]
        if len(party_ids) != len(set(party_ids)):
            raise ValueError("registry ownership party IDs must be unique")
        relationship_ids = [item.relationship_id for item in self.relationships]
        if len(relationship_ids) != len(set(relationship_ids)):
            raise ValueError("registry relationship IDs must be unique")
        parties_by_id = {party.party_id: party for party in self.ownership_parties}
        valid_owned_entities = {self.root_party_id}.union(
            party.party_id
            for party in self.ownership_parties
            if party.party_type == RegistryPartyType.LEGAL_ENTITY
        )
        for relationship in self.relationships:
            if (
                relationship.owned_entity_id not in valid_owned_entities
                or relationship.owner_party_id not in parties_by_id
                or relationship.owned_entity_id == relationship.owner_party_id
            ):
                raise ValueError("registry relationship endpoints are inconsistent")

        statuses = tuple(item.status for item in self.operation_results)
        expected_missing_code = "REGISTRY_EXPECTED_DATA_MISSING"
        if self.status == RegistryAcquisitionStatus.COMPLETE:
            if statuses[1] not in {
                RegistryOperationStatus.COMPLETE,
                RegistryOperationStatus.EMPTY,
            }:
                raise ValueError("complete acquisition requires attempted officer evidence")
            if statuses[2:] != (
                RegistryOperationStatus.COMPLETE,
                RegistryOperationStatus.COMPLETE,
            ):
                raise ValueError("complete acquisition requires usable ownership evidence")
            if self.issues:
                raise ValueError("complete registry acquisition cannot retain issues")
        elif self.status == RegistryAcquisitionStatus.PARTIAL:
            if any(
                status
                in {
                    RegistryOperationStatus.FAILED,
                    RegistryOperationStatus.NOT_ATTEMPTED,
                }
                for status in statuses
            ):
                raise ValueError("partial acquisition cannot contain technical failure states")
            if statuses[1] not in {
                RegistryOperationStatus.COMPLETE,
                RegistryOperationStatus.EMPTY,
            } or any(
                status
                not in {
                    RegistryOperationStatus.COMPLETE,
                    RegistryOperationStatus.EMPTY,
                    RegistryOperationStatus.UNSUPPORTED,
                }
                for status in statuses[2:]
            ):
                raise ValueError("partial acquisition has inconsistent operation states")
            if not any(
                status in {RegistryOperationStatus.EMPTY, RegistryOperationStatus.UNSUPPORTED}
                for status in statuses[2:]
            ):
                raise ValueError("partial acquisition requires missing ownership evidence")
            if len(self.issues) != 1 or self.issues[0].code != expected_missing_code:
                raise ValueError("partial acquisition requires its expected-data issue")
        else:
            failed_indices = tuple(
                index
                for index, status in enumerate(statuses)
                if status == RegistryOperationStatus.FAILED
            )
            if len(failed_indices) != 1:
                raise ValueError("failed acquisition requires exactly one failed operation")
            failed_index = failed_indices[0]
            if any(
                status
                not in {
                    RegistryOperationStatus.COMPLETE,
                    RegistryOperationStatus.EMPTY,
                }
                for status in statuses[:failed_index]
            ) or any(
                status != RegistryOperationStatus.NOT_ATTEMPTED
                for status in statuses[failed_index + 1 :]
            ):
                raise ValueError("failed acquisition must follow the operation prefix rule")
            failed_error = self.operation_results[failed_index].error
            if failed_error is None or failed_error.code == expected_missing_code:
                raise ValueError("failed acquisition requires a technical operation error")
            if len(self.issues) != 1 or self.issues[0] != failed_error:
                raise ValueError("failed acquisition issue must match the failed operation")
        return self


# Cache identity for issuer shareholder evidence read without an entity profile. D-080
# rows also keep their source share class (cache schema 4); D-079 V1 entries (schema 3)
# never carry it, stay readable and are never reused or rewritten under the new key.
SHAREHOLDER_EVIDENCE_CONTRACT_VERSION: Literal["MARKETPLACE_SHAREHOLDERS_V2"] = (
    "MARKETPLACE_SHAREHOLDERS_V2"
)
LEGACY_SHAREHOLDER_EVIDENCE_CONTRACT_VERSION: Literal["MARKETPLACE_SHAREHOLDERS_V1"] = (
    "MARKETPLACE_SHAREHOLDERS_V1"
)


class RegistryShareholderEvidence(BaseModel):
    """One issuer's own official shareholder operation, read without an entity profile.

    D-079 partial evidence for an identified corporate holder whose entity-basic profile
    is a definitive NOT_FOUND. It carries no canonical identity, legal form, percentage
    or relationship; withdrawn rows are retained with their source status.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    requested_identifier: str = Field(min_length=1, max_length=32)
    operation_result: RegistryOperationResult
    ownership_parties: tuple[RegistryOwnershipParty, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def validate_shareholder_evidence(self) -> "RegistryShareholderEvidence":
        result = self.operation_result
        if result.operation != RegistryOperation.OWNERSHIP_PARTIES or result.status not in {
            RegistryOperationStatus.COMPLETE,
            RegistryOperationStatus.EMPTY,
            RegistryOperationStatus.FAILED,
        }:
            raise ValueError("shareholder evidence requires one attempted shareholder operation")
        if result.record_count != len(self.ownership_parties):
            raise ValueError("shareholder evidence count disagrees with its rows")
        if len({item.party_id for item in self.ownership_parties}) != len(
            self.ownership_parties
        ):
            raise ValueError("shareholder evidence rows must be unique")
        if any(
            item.provenance != result.provenance or item.ownership_percentage is not None
            for item in self.ownership_parties
        ):
            raise ValueError("shareholder rows require operation provenance and no percentage")
        return self


# D-088: cache identity for one issuer's official Marketplace Mock `businessProfile`
# read (cache schema 5), separate from every entity and shareholder contract.
BUSINESS_PROFILE_EVIDENCE_CONTRACT_VERSION: Literal["MARKETPLACE_BUSINESS_PROFILE_V1"] = (
    "MARKETPLACE_BUSINESS_PROFILE_V1"
)
_BUSINESS_PROFILE_TEXT = Field(min_length=1, max_length=160)
_SHARE_COUNT = Field(ge=0, allow_inf_nan=False, max_digits=18, decimal_places=6)


class RegistryBusinessProfileShareholder(BaseModel):
    """One official `businessProfile` shareholder row; never an identity or percentage.

    `party_id` is an opaque issuer-scoped digest: the source holder identifier is not
    kept. `source_status` is the provider-returned status, which this operation omits.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party_id: str = Field(pattern=r"^BP-[0-9a-f]{24}$")
    party_type: RegistryPartyType
    name: str = _BUSINESS_PROFILE_TEXT
    source_category: str = Field(min_length=1, max_length=64)
    source_status: str | None = Field(default=None, min_length=1, max_length=64)
    number_of_shares: Decimal = _SHARE_COUNT
    share_type: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("number_of_shares", mode="before")
    @classmethod
    def exact_share_count(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("share counts must be exact")
        return value


class RegistryShareCapital(BaseModel):
    """One official `businessProfile` issued or paid-up capital line, as returned."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    share_type: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = Field(default=None, min_length=1, max_length=64)
    number_of_shares: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False,
                                             max_digits=18, decimal_places=6)
    amount: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False,
                                   max_digits=24, decimal_places=6)

    @field_validator("number_of_shares", "amount", mode="before")
    @classmethod
    def exact_capital(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("capital values must be exact")
        return value


class RegistryBusinessProfileEvidence(BaseModel):
    """One issuer's own official Marketplace Mock `businessProfile` read (D-088).

    Read only for a scenario-named corporate holder whose entity-basic profile and
    shareholder operation are both empty. It keeps the company identity labels, the
    shareholder rows and the issued/paid-up capital exactly as returned; it derives no
    canonical identity, legal form, percentage or relationship.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    requested_identifier: str = Field(min_length=1, max_length=32)
    status: Literal["COMPLETE", "EMPTY", "FAILED"]
    provider: SourceSystem = SourceSystem.ACRA
    environment: SourceEnvironment
    retrieved_at: datetime
    evidence_reference: str = Field(pattern=r"^acra:business_profile:[A-Z0-9]{1,32}$")
    error_code: str | None = Field(default=None, min_length=1, max_length=64)
    entity_name: str | None = Field(default=None, min_length=1, max_length=160)
    company_type: str | None = Field(default=None, min_length=1, max_length=160)
    status_of_company: str | None = Field(default=None, min_length=1, max_length=80)
    shareholders: tuple[RegistryBusinessProfileShareholder, ...] = Field(
        default=(), max_length=64
    )
    issued_share_capital: tuple[RegistryShareCapital, ...] = Field(default=(), max_length=16)
    paid_up_capital: tuple[RegistryShareCapital, ...] = Field(default=(), max_length=16)

    @field_validator("retrieved_at")
    @classmethod
    def retrieved_at_is_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def validate_business_profile(self) -> "RegistryBusinessProfileEvidence":
        if self.evidence_reference != f"acra:business_profile:{self.requested_identifier}":
            raise ValueError("business profile evidence reference disagrees with its issuer")
        content = (
            self.entity_name is not None
            or self.company_type is not None
            or self.status_of_company is not None
            or self.shareholders
            or self.issued_share_capital
            or self.paid_up_capital
        )
        if self.status == "COMPLETE" and (self.entity_name is None or self.error_code):
            raise ValueError("complete business profile evidence requires its entity name")
        if self.status == "EMPTY" and (content or self.error_code):
            raise ValueError("empty business profile evidence carries no content")
        if self.status == "FAILED" and (content or self.error_code is None):
            raise ValueError("failed business profile evidence carries only its error")
        if len({item.party_id for item in self.shareholders}) != len(self.shareholders):
            raise ValueError("business profile shareholder rows must be unique")
        return self


class RegistryEvidenceDisposition(StrEnum):
    """Truthful reason a complete shared snapshot was bound to one case."""

    PROVIDER_FETCH = "PROVIDER_FETCH"
    CACHE_HIT = "CACHE_HIT"


class RegistryProviderIdentity(BaseModel):
    """Exact internal identity required before a provider may use the cache."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: SourceSystem
    environment: SourceEnvironment
    acquisition_contract_version: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z0-9][A-Z0-9_.-]{0,63}$",
    )
    dataset_namespace: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z0-9][A-Z0-9_.-]{0,63}$",
    )


class RegistryCacheKey(BaseModel):
    """Immutable cache identity isolated by provider, contract, and data set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_identity: RegistryProviderIdentity
    normalized_identifier: str = Field(min_length=1, max_length=32)

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(encoded).hexdigest()


class RegistryFreshnessPolicy(BaseModel):
    """Fixed owner-approved Mock freshness rule; never provider policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: Literal["MOCK_ACRA_FIXED_90D", "MOCK_ACRA_APPROVED_POLICY"] = "MOCK_ACRA_FIXED_90D"
    version: int = Field(default=1, strict=True, ge=1)
    duration_seconds: int = Field(default=7_776_000, strict=True, ge=60, le=31_536_000)
    comparator: Literal["EVALUATION_NOW_LT_EXPIRES_AT"] = "EVALUATION_NOW_LT_EXPIRES_AT"

    @model_validator(mode="after")
    def fixed_policy_is_exact(self) -> "RegistryFreshnessPolicy":
        if self.policy_id == "MOCK_ACRA_FIXED_90D" and (
            self.version != 1 or self.duration_seconds != 7_776_000
        ):
            raise ValueError("fixed historical registry policy cannot be reinterpreted")
        return self

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def expires_at(self, freshness_anchor: datetime) -> datetime:
        return _require_utc(freshness_anchor) + timedelta(seconds=self.duration_seconds)


class RegistrySnapshotEntry(BaseModel):
    """One complete normalized shared registry snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    cache_schema_version: Literal[1, 2, 3, 4, 5] = 1
    cache_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    key: RegistryCacheKey
    revision: int = Field(ge=0)
    acquisition: RegistryAcquisitionBundle | None
    negative_result: Literal["NOT_FOUND"] | None = None
    # Schemas 3 (D-079, V1 key) and 4 (D-080, V2 key, share class retained) only:
    # shareholder evidence under its own contract key.
    shareholder_evidence: RegistryShareholderEvidence | None = None
    # Schema 5 (D-088) only: business profile evidence under its own contract key.
    business_profile_evidence: RegistryBusinessProfileEvidence | None = None
    freshness_anchor: datetime
    provider_effective_at: datetime | None = None
    written_at: datetime

    @field_validator("freshness_anchor", "provider_effective_at", "written_at")
    @classmethod
    def timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return _require_utc(value) if value is not None else None

    @field_validator("cache_schema_version", mode="before")
    @classmethod
    def strict_cache_schema(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("cache schema must be an integer")
        return value

    @model_validator(mode="after")
    def validate_entry(self) -> "RegistrySnapshotEntry":
        if self.cache_id != self.key.digest:
            raise ValueError("registry cache identity does not match its key")
        if (
            self.key.provider_identity.environment != SourceEnvironment.MOCK
            and self.cache_schema_version == 2
        ):
            raise ValueError("operation and negative cache require explicit Mock identity")
        identity = self.key.provider_identity
        business_profile_key = (
            identity.acquisition_contract_version == BUSINESS_PROFILE_EVIDENCE_CONTRACT_VERSION
        )
        if (
            business_profile_key
            or self.business_profile_evidence is not None
            or self.cache_schema_version == 5
        ):
            profile = self.business_profile_evidence
            if (
                not business_profile_key
                or profile is None
                or self.cache_schema_version != 5
                or profile.status == "FAILED"
                or self.acquisition is not None
                or self.negative_result is not None
                or self.shareholder_evidence is not None
                or self.provider_effective_at is not None
                or identity.environment != SourceEnvironment.MOCK
                or profile.requested_identifier != self.key.normalized_identifier
                or profile.provider != identity.provider
                or profile.environment != identity.environment
                or self.freshness_anchor != profile.retrieved_at
                or self.written_at < profile.retrieved_at
            ):
                raise ValueError("business profile cache entries hold only Mock profile evidence")
            return self
        shareholder_schema = {
            LEGACY_SHAREHOLDER_EVIDENCE_CONTRACT_VERSION: 3,
            SHAREHOLDER_EVIDENCE_CONTRACT_VERSION: 4,
        }.get(identity.acquisition_contract_version)
        if (
            shareholder_schema is not None
            or self.shareholder_evidence is not None
            or self.cache_schema_version in {3, 4}
        ):
            evidence = self.shareholder_evidence
            if (
                shareholder_schema is None
                or evidence is None
                or self.cache_schema_version != shareholder_schema
                or (
                    shareholder_schema == 3
                    and any(
                        item.share_type is not None or item.currency is not None
                        for item in evidence.ownership_parties
                    )
                )
                or self.acquisition is not None
                or self.negative_result is not None
                or self.provider_effective_at is not None
                or identity.environment != SourceEnvironment.MOCK
            ):
                raise ValueError("shareholder cache entries hold only Mock shareholder evidence")
            provenance = evidence.operation_result.provenance
            if (
                evidence.operation_result.status == RegistryOperationStatus.FAILED
                or provenance is None
                or evidence.requested_identifier != self.key.normalized_identifier
                or provenance.provider != identity.provider
                or provenance.environment != identity.environment
                or self.freshness_anchor != provenance.retrieved_at
                or self.written_at < provenance.retrieved_at
            ):
                raise ValueError("shareholder cache evidence disagrees with its key")
            return self
        if self.negative_result is not None:
            if (
                self.cache_schema_version != 2
                or self.acquisition is not None
                or self.freshness_anchor != self.written_at
                or self.provider_effective_at is not None
            ):
                raise ValueError("negative cache contains inconsistent evidence")
            return self
        if self.acquisition is None:
            raise ValueError("registry cache requires acquisition or definitive absence")
        if (
            self.cache_schema_version == 1
            and self.acquisition.status != RegistryAcquisitionStatus.COMPLETE
        ):
            raise ValueError("registry cache entries require complete acquisition evidence")
        if self.acquisition.requested_identifier != self.key.normalized_identifier:
            raise ValueError("registry cache key does not match the acquisition identifier")
        provenances = tuple(result.provenance for result in self.acquisition.operation_results)
        if self.cache_schema_version == 1 and any(provenance is None for provenance in provenances):
            raise ValueError("complete registry cache evidence requires all provenances")
        complete_provenances = tuple(
            result.provenance
            for result in self.acquisition.operation_results
            if result.provenance is not None
            and result.status in {RegistryOperationStatus.COMPLETE, RegistryOperationStatus.EMPTY}
        )
        identity = self.key.provider_identity
        if any(
            provenance.provider != identity.provider
            or provenance.environment != identity.environment
            for provenance in provenances
            if provenance is not None
        ):
            raise ValueError("registry cache identity does not match acquisition provenance")
        if self.freshness_anchor != min(
            provenance.retrieved_at for provenance in complete_provenances
        ):
            raise ValueError("registry freshness anchor must be the earliest operation time")
        if self.written_at < self.acquisition.retrieved_at:
            raise ValueError("registry cache write cannot precede provider retrieval")
        if (
            identity.environment == SourceEnvironment.MOCK
            and self.provider_effective_at is not None
        ):
            raise ValueError("Mock registry evidence has no provider-effective time")
        return self


class RegistryEvidenceBinding(BaseModel):
    """Immutable record of one successfully committed complete cache use."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    disposition: RegistryEvidenceDisposition
    cache_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    cache_key: RegistryCacheKey
    cache_revision: int = Field(ge=0)
    freshness_anchor: datetime
    bundle_retrieved_at: datetime
    cache_written_at: datetime
    bound_to_case_at: datetime
    expires_at: datetime
    freshness_policy: RegistryFreshnessPolicy
    freshness_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "freshness_anchor",
        "bundle_retrieved_at",
        "cache_written_at",
        "bound_to_case_at",
        "expires_at",
    )
    @classmethod
    def binding_timestamps_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @model_validator(mode="after")
    def validate_binding(self) -> "RegistryEvidenceBinding":
        if self.cache_id != self.cache_key.digest:
            raise ValueError("registry binding identity does not match its key")
        if self.freshness_policy_fingerprint != self.freshness_policy.fingerprint:
            raise ValueError("registry binding policy fingerprint is inconsistent")
        if self.expires_at != self.freshness_policy.expires_at(self.freshness_anchor):
            raise ValueError("registry binding expiry is inconsistent")
        if self.bundle_retrieved_at < self.freshness_anchor:
            raise ValueError("registry bundle time cannot precede its freshness anchor")
        if self.cache_written_at < self.bundle_retrieved_at:
            raise ValueError("registry cache write cannot precede provider retrieval")
        if self.bound_to_case_at < self.cache_written_at:
            raise ValueError("registry case binding cannot precede the cache write")
        if self.bound_to_case_at >= self.expires_at:
            raise ValueError("registry evidence cannot be bound at or after expiry")
        return self


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("registry cache timestamp must be timezone-aware UTC")
    return value.astimezone(UTC)


class WorkflowEvent(BaseModel):
    """Audit-safe workflow event; raw corporate payloads are deliberately excluded."""

    sequence: int = Field(ge=1)
    stage: WorkflowState
    outcome: EventOutcome
    timestamp: datetime
    case_id: UUID
    correlation_id: UUID
    code: str | None = None
    message: str


class GoldTierResult(BaseModel):
    """User-facing summary of the mock target result."""

    party_id: str
    shell_status: str
    policy_id: str | None = None
    policy_status: str | None = None
    amend_status: str | None = None
    readback_party_id: str | None = None
    readback_status: str | None = None


class InitialCustomerIdentity(BaseModel):
    """User-supplied identity retained before any registry or target lookup."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    legal_name: str = Field(min_length=1, max_length=160)
    registration_number: str = Field(min_length=1, max_length=32)
    country_of_incorporation: str = Field(min_length=2, max_length=3)


class ExistingTargetStateProvenance(BaseModel):
    """Safe provenance for canonical state reused from a prior verified target case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = "EXISTING_TARGET_STATE"
    source_case_id: UUID
    target_party_id: str = Field(min_length=1, max_length=96)
    verified_at: datetime


class InitialGoldTierSearchEvidence(BaseModel):
    """Bounded Search-first evidence retained before optional ACRA acquisition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: UUID
    disposition: Literal["NO_MATCH", "EXACT_MATCH", "REVIEW_REQUIRED", "FAILED"]
    provider_outcome: str = Field(min_length=1, max_length=32)
    status_code: int = Field(ge=200, le=599)
    candidate_count: int = Field(ge=0, le=25)
    candidate_party_ids: tuple[str, ...] = Field(default=(), max_length=25)
    candidate_legal_names: tuple[str | None, ...] = Field(default=(), max_length=25)
    # Absent tuples in historical envelopes mean unknown provider evidence.
    candidate_registration_numbers: tuple[str | None, ...] = Field(default=(), max_length=25)
    candidate_countries: tuple[str | None, ...] = Field(default=(), max_length=25)
    selected_party_id: str | None = Field(default=None, min_length=1, max_length=96)
    searched_at: datetime

    @model_validator(mode="after")
    def validate_initial_search(self) -> "InitialGoldTierSearchEvidence":
        if self.candidate_count != len(self.candidate_party_ids) or self.candidate_count != len(
            self.candidate_legal_names
        ):
            raise ValueError("Initial Search candidate evidence must remain aligned")
        if (self.disposition == "EXACT_MATCH") != (self.selected_party_id is not None):
            raise ValueError("Only an exact initial Search may retain a target identity")
        for evidence in (self.candidate_registration_numbers, self.candidate_countries):
            if evidence and len(evidence) != self.candidate_count:
                raise ValueError("Initial Search identity fields must remain aligned")
        if (
            self.selected_party_id is not None
            and self.selected_party_id not in self.candidate_party_ids
        ):
            raise ValueError("Initial Search must select a retained provider identity")
        return self


class IdentityCorrectionEvidence(BaseModel):
    """Audit-safe local-POC evidence for one same-case identity repair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    correction_id: UUID
    actor_id: str = Field(min_length=3, max_length=32, pattern=r"^[a-z][a-z0-9-]{2,31}$")
    evidence_type: Literal["OPERATOR_VERIFIED_SOURCE", "USER_SUPPLIED_CORRECTION_POC"] = (
        "USER_SUPPLIED_CORRECTION_POC"
    )
    previous_identity: InitialCustomerIdentity | None = None
    previous_entity: CanonicalLegalEntity | None = None
    previous_registry_acquisition: RegistryAcquisitionBundle | None = None
    choice: Literal["ENTERED", "DOCUMENT", "OTHER"] = "OTHER"
    source_document_id: UUID | None = None
    source_document_event_count: int | None = Field(default=None, ge=0)
    corrected_identity: InitialCustomerIdentity
    previous_search_request_id: UUID | None = None
    corrected_at: datetime


class InitialGoldTierSearchAttempt(BaseModel):
    """Durable intent/result for one authorized read-only Search recheck."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: UUID
    actor_id: str = Field(min_length=3, max_length=32, pattern=r"^[a-z][a-z0-9-]{2,31}$")
    identity: InitialCustomerIdentity
    status: Literal["REQUESTED", "COMPLETED"]
    requested_at: datetime
    completed_at: datetime | None = None
    result: InitialGoldTierSearchEvidence | None = None

    @model_validator(mode="after")
    def validate_completion(self) -> "InitialGoldTierSearchAttempt":
        completed = self.status == "COMPLETED"
        if completed != (self.completed_at is not None and self.result is not None):
            raise ValueError("Completed Search recheck requires retained result and time")
        return self


class TargetDispatchConfirmation(BaseModel):
    """Local-POC confirmation of one frozen target review, never approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    confirmation_id: UUID
    actor_id: str = Field(min_length=3, max_length=32, pattern=r"^[a-z][a-z0-9-]{2,31}$")
    confirmed_at: datetime
    case_event_count: int = Field(ge=1)
    clm_version: int | None = Field(default=None, ge=1)
    destination: Literal["GOLDTIER_MOCK", "GOLDTIER_XPI_SANDBOX"]
    warnings: tuple[str, ...] = Field(default=(), max_length=16)
    review_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: Literal["USER_AUTHORIZED_POC"] = "USER_AUTHORIZED_POC"


class GovernmentStatusConfirmation(BaseModel):
    """D-101 RM confirmation of Government status from one reviewed document version.

    It replaces the ownership/UBO step only while it stays bound to that exact current
    evidence; it is never set automatically and is not approval.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    confirmation_id: UUID
    actor_id: str = Field(min_length=3, max_length=32, pattern=r"^[a-z][a-z0-9-]{2,31}$")
    confirmed_at: datetime
    case_event_count: int = Field(ge=1)
    document_id: UUID
    document_event_count: int = Field(ge=1)
    evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: Literal["USER_AUTHORIZED_POC"] = "USER_AUTHORIZED_POC"


class SafeError(BaseModel):
    """Sanitised application error safe for API and history responses."""

    code: str
    message: str


class OnboardingCase(BaseModel):
    """Canonical aggregate returned by the application-facing API."""

    case_id: UUID
    source_case_id: str
    correlation_id: UUID
    requested_uen: str
    initial_identity: InitialCustomerIdentity | None = None
    initial_target_search: InitialGoldTierSearchEvidence | None = None
    identity_corrections: tuple[IdentityCorrectionEvidence, ...] = Field(
        default=(), max_length=IDENTITY_RECHECK_HISTORY_LIMIT
    )
    initial_target_search_attempts: tuple[InitialGoldTierSearchAttempt, ...] = Field(
        default=(), max_length=IDENTITY_RECHECK_HISTORY_LIMIT
    )
    existing_target_state: ExistingTargetStateProvenance | None = None
    target_classification_selections: tuple[TargetClassificationSelection, ...] = Field(
        default=(), max_length=2
    )
    target_dispatch_confirmation: TargetDispatchConfirmation | None = None
    # D-101 (schema 17). Left out of dumps while unset, so fingerprints and review digests
    # of cases without it (every case before schema 17) do not change.
    government_status_confirmation: GovernmentStatusConfirmation | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    policy_snapshot: CasePolicySnapshot = Field(default_factory=legacy_phase13_policy_snapshot)
    policy_snapshot_revision: int = Field(default=1, ge=1)
    policy_rebind_history: tuple[CasePolicyRebindAudit, ...] = Field(default=(), max_length=8)
    team_id: TeamId | None = None
    created_by_actor_id: Annotated[
        str, Field(pattern=r"^[a-z][a-z0-9-]{2,31}$")
    ] | None = None
    priority: CasePriority | None = None
    jurisdiction_resolution: JurisdictionResolution | None = None
    registry_route: RegistryRoutingDecision | None = None
    state: WorkflowState
    entity: CanonicalLegalEntity | None = None
    registry_acquisition: RegistryAcquisitionBundle | None = None
    registry_evidence_binding: RegistryEvidenceBinding | None = None
    goldtier_result: GoldTierResult | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_registry_binding(self) -> "OnboardingCase":
        selections = self.target_classification_selections
        if len({item.field_key for item in selections}) != len(selections):
            raise ValueError("Target classification selection keys must be unique")
        for selection in selections:
            target = self.policy_snapshot.goldtier_target
            if target is None or getattr(target, selection.field_key).value != selection.value:
                raise ValueError("Target classification selection must match case policy")
            authority = (
                PolicyAuthority.PROJECT_DERIVED_POC if selection.source == "DOCUMENT"
                else PolicyAuthority.USER_AUTHORIZED_POC
            )
            if getattr(target, selection.field_key).authority != authority:
                raise ValueError("Target selection source must agree with policy authority")
            if selection.policy_version != self.policy_snapshot.catalogue_version:
                raise ValueError("Target selection requires the frozen case policy version")
            evidence = selection.document_evidence
            if evidence is not None and evidence.evidence_score < float(
                self.policy_snapshot.idp_review_confidence_threshold
            ):
                raise ValueError("Automatic selection requires the frozen confidence threshold")
        if self.initial_identity is not None and (
            self.initial_identity.registration_number != self.requested_uen
        ):
            raise ValueError("Initial identity must match the requested identifier")
        if self.existing_target_state is not None:
            if self.entity is None or self.initial_target_search is None:
                raise ValueError(
                    "Existing target state requires hydrated entity and Search evidence"
                )
            if (
                self.initial_target_search.disposition != "EXACT_MATCH"
                or self.initial_target_search.selected_party_id
                != self.existing_target_state.target_party_id
            ):
                raise ValueError("Existing target state must match the exact Search identity")
        binding = self.registry_evidence_binding
        acquisition = self.registry_acquisition
        if binding is None:
            return self
        if acquisition is None or acquisition.status != RegistryAcquisitionStatus.COMPLETE:
            raise ValueError("registry evidence binding requires a complete acquisition")
        if self.entity != acquisition.entity_profile:
            raise ValueError("registry evidence binding requires the acquired entity")
        if binding.cache_key.normalized_identifier != self.requested_uen:
            raise ValueError("registry evidence binding does not match the case identifier")
        if binding.bundle_retrieved_at != acquisition.retrieved_at:
            raise ValueError("registry evidence binding does not match the bundle timestamp")
        provenances = tuple(result.provenance for result in acquisition.operation_results)
        if any(provenance is None for provenance in provenances):
            raise ValueError("bound registry evidence requires every operation provenance")
        complete_provenances = tuple(
            provenance for provenance in provenances if provenance is not None
        )
        identity = binding.cache_key.provider_identity
        if any(
            provenance.provider != identity.provider
            or provenance.environment != identity.environment
            for provenance in complete_provenances
        ):
            raise ValueError("registry evidence binding has inconsistent provider identity")
        if binding.freshness_anchor != min(
            provenance.retrieved_at for provenance in complete_provenances
        ):
            raise ValueError("registry evidence binding has an inconsistent freshness anchor")
        return self
