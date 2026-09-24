"""Typed Phase 01 subset of the provisional GoldTier development contract."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from app.domain.target_safety import (
    SafeTargetErrorCode,
    SafeTargetIdentifier,
    SafeTargetMessage,
    SafeTargetStatus,
)


class ContractModel(BaseModel):
    """Base model that serialises Python names to canonical contract properties."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SourceContext(ContractModel):
    source_system: str = Field(validation_alias="sourceSystem", serialization_alias="sourceSystem")
    source_case_id: str = Field(
        validation_alias="sourceCaseId", serialization_alias="sourceCaseId"
    )
    accepted_by: str = Field(validation_alias="acceptedBy", serialization_alias="acceptedBy")
    accepted_at: datetime = Field(validation_alias="acceptedAt", serialization_alias="acceptedAt")
    source_channel: Literal["EDS_API", "API", "PORTAL", "BATCH", "EVENT", "MANUAL"] = Field(
        default="EDS_API",
        validation_alias="sourceChannel",
        serialization_alias="sourceChannel",
    )


class GoldTierRequestMetadata(BaseModel):
    """Mandatory safe headers kept separate from request bodies."""

    correlation_id: UUID
    source_case_id: str
    idempotency_key: UUID4

    def as_headers(self) -> dict[str, str]:
        return {
            "X-Correlation-Id": str(self.correlation_id),
            "X-Source-Case-Id": self.source_case_id,
            "Idempotency-Key": str(self.idempotency_key),
            "Content-Type": "application/json",
        }


class SearchPartyRequest(ContractModel):
    registration_number: str = Field(
        validation_alias="registrationNumber", serialization_alias="registrationNumber"
    )


class PartyNames(ContractModel):
    legal_name: str = Field(validation_alias="legalName", serialization_alias="legalName")


class NonIndividualProfile(ContractModel):
    country_of_incorporation: str = Field(
        validation_alias="countryOfIncorporation",
        serialization_alias="countryOfIncorporation",
    )


class ShellParty(ContractModel):
    party_role: str = Field(validation_alias="partyRole", serialization_alias="partyRole")
    party_type: str = Field(validation_alias="partyType", serialization_alias="partyType")
    names: PartyNames
    non_individual_profile: NonIndividualProfile = Field(
        validation_alias="nonIndividualProfile", serialization_alias="nonIndividualProfile"
    )


class CreateShellCustomerRequest(ContractModel):
    party: ShellParty
    source_context: SourceContext = Field(
        validation_alias="sourceContext", serialization_alias="sourceContext"
    )


class PolicyDetails(ContractModel):
    policy: str


class CreatePolicyRequest(ContractModel):
    goldtier_id: str = Field(validation_alias="goldTierId", serialization_alias="goldTierId")
    customer_external_system: str = Field(
        validation_alias="customerExternalSystem", serialization_alias="customerExternalSystem"
    )
    customer_external_system_key: str = Field(
        validation_alias="customerExternalSystemKey",
        serialization_alias="customerExternalSystemKey",
    )
    policy_details: PolicyDetails = Field(
        validation_alias="policyDetails", serialization_alias="policyDetails"
    )
    source_context: SourceContext = Field(
        validation_alias="sourceContext", serialization_alias="sourceContext"
    )


class AmendAddress(ContractModel):
    address_line_1: str = Field(
        validation_alias="addressLine1", serialization_alias="addressLine1"
    )
    address_line_2: str | None = Field(
        default=None, validation_alias="addressLine2", serialization_alias="addressLine2"
    )
    postal_code: str = Field(validation_alias="postalCode", serialization_alias="postalCode")
    country: str


class AmendPartyData(ContractModel):
    names: PartyNames
    addresses: list[AmendAddress]


class AmendPartyRequest(ContractModel):
    party_type: str = Field(validation_alias="partyType", serialization_alias="partyType")
    policy: str
    party: AmendPartyData
    source_context: SourceContext = Field(
        validation_alias="sourceContext", serialization_alias="sourceContext"
    )


class GoldTierOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


class GoldTierSearchOutcome(StrEnum):
    """Search-specific semantics preventing ambiguous shell creation."""

    NO_MATCH = "NO_MATCH"
    MATCH_FOUND = "MATCH_FOUND"
    MULTIPLE_MATCHES = "MULTIPLE_MATCHES"
    FAILURE = "FAILURE"


class GoldTierSearchCandidate(BaseModel):
    """Bounded safe identity projection; raw provider fields stop at the connector."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    party_id: SafeTargetIdentifier
    registration_number: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    country: Annotated[str, Field(pattern=r"^[A-Za-z]{2,3}$")] | None = None
    legal_name: Annotated[str, Field(min_length=1, max_length=160)] | None = None
    legal_form: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    registered_address: Annotated[str, Field(min_length=1, max_length=240)] | None = None


class GoldTierSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    outcome: GoldTierSearchOutcome
    status_code: Annotated[int, Field(ge=200, le=599)]
    matched_party_id: SafeTargetIdentifier | None = None
    candidates: tuple[GoldTierSearchCandidate, ...] = Field(default=(), max_length=25)
    error_code: SafeTargetErrorCode | None = None
    message: SafeTargetMessage

    @model_validator(mode="after")
    def candidate_shape_matches_outcome(self) -> GoldTierSearchResult:
        ids = tuple(item.party_id for item in self.candidates)
        if len(ids) != len(set(ids)):
            raise ValueError("GoldTier search candidates must be unique")
        if self.outcome == GoldTierSearchOutcome.NO_MATCH and (
            self.matched_party_id is not None or self.candidates
        ):
            raise ValueError("no-match result cannot contain candidates")
        if self.outcome == GoldTierSearchOutcome.MULTIPLE_MATCHES and len(self.candidates) < 2:
            raise ValueError("multiple-match result requires multiple candidates")
        if (
            self.outcome == GoldTierSearchOutcome.MATCH_FOUND
            and self.candidates
            and (
                len(self.candidates) != 1
                or self.matched_party_id != self.candidates[0].party_id
            )
        ):
            raise ValueError("unique match must bind its candidate identity")
        return self


class GoldTierOperationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    outcome: GoldTierOutcome
    status_code: Annotated[int, Field(ge=200, le=599)]
    party_id: SafeTargetIdentifier | None = None
    policy_id: SafeTargetIdentifier | None = None
    status: SafeTargetStatus
    error_code: SafeTargetErrorCode | None = None
    message: SafeTargetMessage
