"""Bounded source-neutral scalar evidence, separate from authoritative graph edges."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

EvidenceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")]
EvidenceText = Annotated[str, StringConstraints(min_length=1, max_length=128)]


class OwnershipEvidenceKind(StrEnum):
    DIRECT_PERCENTAGE = "DIRECT_PERCENTAGE"
    SHARE_UNITS = "SHARE_UNITS"
    CAPITAL_DENOMINATOR = "CAPITAL_DENOMINATOR"
    MEMBERSHIP_INTEREST = "MEMBERSHIP_INTEREST"
    ROLE = "ROLE"
    GROUP_SHAREHOLDER = "GROUP_SHAREHOLDER"
    ECONOMIC_INTEREST = "ECONOMIC_INTEREST"
    CONTROL = "CONTROL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class OwnershipEvidence(BaseModel):
    """One minimized original scalar and its identity/unit/provenance binding.

    authoritative refers only to denominator completeness/meaning. Neither this
    record nor a role tag determines legal ownership, activity or control.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    evidence_id: EvidenceId
    entity_identifier: (
        Annotated[str, StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9._:-]{0,63}$")] | None
    )
    party_id: EvidenceId
    kind: OwnershipEvidenceKind
    raw_value: EvidenceText
    numeric_value: Decimal | None = Field(
        default=None, ge=0, allow_inf_nan=False, max_digits=24, decimal_places=6
    )
    source_operation: EvidenceId
    provider: EvidenceId
    environment: Literal["MOCK", "LOCAL", "SANDBOX", "LIVE"]
    retrieved_at: datetime
    as_of: datetime | None = None
    share_class: EvidenceText | None = None
    unit_type: EvidenceText | None = None
    source_status: EvidenceText | None = None
    authoritative: bool = False
    confidence: Decimal = Field(default=Decimal("1"), ge=0, le=1, allow_inf_nan=False)
    determination_basis: Literal["SOURCE_SCALAR", "PROVIDER_PERCENTAGE", "REVIEWED_DECLARATION"] = (
        "SOURCE_SCALAR"
    )
    evidence_version: int = Field(ge=1)

    @model_validator(mode="after")
    def original_numeric_value_agrees(self) -> "OwnershipEvidence":
        if self.numeric_value is not None:
            try:
                original = Decimal(self.raw_value)
            except ArithmeticError:
                raise ValueError("original numeric evidence is invalid") from None
            if not original.is_finite() or original != self.numeric_value:
                raise ValueError("original numeric evidence disagrees")
        return self

    @field_validator("numeric_value", "confidence", mode="before")
    @classmethod
    def exact_decimal(cls, value: object) -> object:
        if isinstance(value, (bool, float)):
            raise ValueError("numeric evidence must be exact")
        return value

    @field_validator("raw_value", "share_class", "unit_type", "source_status")
    @classmethod
    def bounded_scalar(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or any(ord(c) < 32 for c in value)):
            raise ValueError("evidence must be a safe scalar")
        return value

    @field_validator("retrieved_at", "as_of")
    @classmethod
    def utc_only(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
        ):
            raise ValueError("evidence time must be UTC")
        return value


class OwnershipEvidenceTag(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")
    tag: Literal[
        "DIRECT_ECONOMIC_INTEREST",
        "INDIRECT_ECONOMIC_INTEREST",
        "SHARE_UNIT_EVIDENCE",
        "CAPITAL_DENOMINATOR_EVIDENCE",
        "OWNER_ROLE",
        "PARTNER_ROLE",
        "MEMBER_ROLE",
        "POSSIBLE_CONTROLLER",
        "CONTROL_EVIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "CONFLICTING_EVIDENCE",
        "UNKNOWN",
    ]
    evidence_ids: tuple[EvidenceId, ...] = Field(min_length=1, max_length=16)
    reason_code: EvidenceId
    rule_version: Literal["ownership-semantic-rules-v1", "ownership-semantic-rules-v2"] = (
        "ownership-semantic-rules-v1"
    )
    score: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    threshold: Decimal | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    policy_version: int | None = Field(default=None, ge=1)
    reason_codes: tuple[EvidenceId, ...] = Field(default=(), max_length=4)
    confidence: Decimal = Field(ge=0, le=1, allow_inf_nan=False)
    provider: EvidenceId
    environment: Literal["MOCK", "LOCAL", "SANDBOX", "LIVE"]
    case_version: int = Field(ge=0)
    evidence_version: int = Field(ge=1)

    @model_validator(mode="after")
    def rule_metadata_agrees(self) -> "OwnershipEvidenceTag":
        fields = (self.score, self.threshold, self.policy_version)
        if self.rule_version == "ownership-semantic-rules-v2":
            if any(value is None for value in fields) or not self.reason_codes:
                raise ValueError("parameterized classifier requires score and policy evidence")
        elif any(value is not None for value in fields) or self.reason_codes:
            raise ValueError("legacy classifier cannot claim parameterized evidence")
        return self


class OwnershipTaggingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    method: Literal["DETERMINISTIC_RULES"] = "DETERMINISTIC_RULES"
    runtime_status: Literal["ML_RUNTIME_NOT_AVAILABLE"] = "ML_RUNTIME_NOT_AVAILABLE"
    tags: tuple[OwnershipEvidenceTag, ...] = Field(default=(), max_length=256)
