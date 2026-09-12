"""Typed bounded global policy catalogue and immutable per-case policy snapshots."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.administration import SafeAuditScalar

MAX_POLICY_RULES = 64
MAX_POLICY_AUDIT_EVENTS = 256
IDP_POLICY_ID = "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD"
UBO_POLICY_ID = "OWNERSHIP_UBO_THRESHOLD_PERCENT"
SHOWCASE_PLAIN_TEXT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./:+%-]{0,127}$")
SHOWCASE_EXPRESSION_PREFIX_PATTERN = re.compile(
    r"^(?:__import__|eval|exec|lambda|javascript|script)\b", re.IGNORECASE
)


class PolicyValueType(StrEnum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    STRING = "STRING"
    STRING_LIST = "STRING_LIST"


class PolicyEnforcement(StrEnum):
    RUNTIME_ENFORCED = "RUNTIME_ENFORCED"
    DISPLAY_SHOWCASE_ONLY = "DISPLAY_SHOWCASE_ONLY"
    NOT_EDITABLE = "NOT_EDITABLE"


class PolicyClassification(StrEnum):
    PROJECT_DEFAULT = "PROJECT_DEFAULT"
    PENDING_SPONSOR_CONFIRMATION = "PENDING_SPONSOR_CONFIRMATION"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"
    DISPLAY_ONLY_NOT_RUNTIME_ENFORCED = "DISPLAY_ONLY_NOT_RUNTIME_ENFORCED"


class BooleanPolicyValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal[PolicyValueType.BOOLEAN] = PolicyValueType.BOOLEAN
    value: bool


class IntegerPolicyValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal[PolicyValueType.INTEGER] = PolicyValueType.INTEGER
    value: Annotated[int, Field(strict=True, ge=-1_000_000, le=1_000_000)]


class DecimalPolicyValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal[PolicyValueType.DECIMAL] = PolicyValueType.DECIMAL
    value: Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,6})?$")]

    @field_validator("value")
    @classmethod
    def finite_decimal(cls, value: str) -> str:
        parsed = Decimal(value)
        if not parsed.is_finite():
            raise ValueError("policy decimal must be finite")
        return value


class StringPolicyValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal[PolicyValueType.STRING] = PolicyValueType.STRING
    value: Annotated[str, Field(min_length=1, max_length=160)]


class StringListPolicyValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal[PolicyValueType.STRING_LIST] = PolicyValueType.STRING_LIST
    value: Annotated[
        tuple[Annotated[str, Field(min_length=1, max_length=80)], ...], Field(max_length=32)
    ]


PolicyValue = Annotated[
    BooleanPolicyValue
    | IntegerPolicyValue
    | DecimalPolicyValue
    | StringPolicyValue
    | StringListPolicyValue,
    Field(discriminator="type"),
]


class PolicyAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: Annotated[str, Field(pattern=r"^[A-F0-9]{24}$")]
    action: Literal[
        "POLICY_CREATED",
        "POLICY_UPDATED",
        "POLICY_RESET_DEFAULT",
        "POLICY_CATALOGUE_RESET",
    ]
    actor_user_id: Annotated[str, Field(min_length=3, max_length=32)]
    target_id: Annotated[str, Field(min_length=3, max_length=64)]
    timestamp: datetime
    resulting_version: Annotated[int, Field(ge=1)]
    metadata: Annotated[dict[str, SafeAuditScalar], Field(max_length=16)] = Field(
        default_factory=dict
    )

    @field_validator("metadata")
    @classmethod
    def safe_metadata(cls, value: dict[str, SafeAuditScalar]) -> dict[str, SafeAuditScalar]:
        forbidden = {"password", "credential", "hash", "session", "csrf", "secret", "uri"}
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 48:
                raise ValueError("policy audit key is invalid")
            if any(marker in key.casefold() for marker in forbidden):
                raise ValueError("policy audit key is not permitted")
            if isinstance(item, str) and len(item) > 160:
                raise ValueError("policy audit value is too long")
        return value


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
    category: Annotated[str, Field(min_length=2, max_length=48)]
    name: Annotated[str, Field(min_length=2, max_length=80)]
    description: Annotated[str, Field(min_length=2, max_length=240)]
    value: PolicyValue
    value_type: PolicyValueType
    default_value: PolicyValue
    minimum: str | int | None = None
    maximum: str | int | None = None
    allowed_values: Annotated[tuple[str, ...], Field(max_length=32)] = ()
    classifications: Annotated[tuple[PolicyClassification, ...], Field(min_length=1, max_length=4)]
    enforcement: PolicyEnforcement
    version: Annotated[int, Field(ge=1)]
    created_at: datetime
    updated_at: datetime
    updated_by: Annotated[str, Field(min_length=3, max_length=32)]

    @model_validator(mode="after")
    def validate_rule(self) -> PolicyRule:
        if self.value.type != self.value_type or self.default_value.type != self.value_type:
            raise ValueError("policy value type metadata does not match value")
        if self.updated_at < self.created_at:
            raise ValueError("policy update time precedes creation")
        validate_policy_value(self, self.value)
        validate_policy_value(self, self.default_value)
        return self


class PolicyCatalogue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    catalogue_id: Literal["GLOBAL_POLICY_CATALOGUE"] = "GLOBAL_POLICY_CATALOGUE"
    version: Annotated[int, Field(ge=1)]
    rules: Annotated[tuple[PolicyRule, ...], Field(min_length=8, max_length=64)]
    created_at: datetime
    updated_at: datetime
    updated_by: Annotated[str, Field(min_length=3, max_length=32)]
    audit_events: Annotated[tuple[PolicyAuditEvent, ...], Field(max_length=256)] = ()

    @model_validator(mode="after")
    def validate_catalogue(self) -> PolicyCatalogue:
        ids = [rule.policy_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate policy ID")
        if self.updated_at < self.created_at:
            raise ValueError("catalogue update time precedes creation")
        if len(self.audit_events) > MAX_POLICY_AUDIT_EVENTS:
            raise ValueError("policy audit capacity exceeded")
        previous = 0
        seen: set[str] = set()
        for event in self.audit_events:
            if event.event_id in seen or event.resulting_version <= previous:
                raise ValueError("policy audit order is invalid")
            if event.resulting_version > self.version:
                raise ValueError("policy audit version is invalid")
            seen.add(event.event_id)
            previous = event.resulting_version
        if self.audit_events and self.audit_events[-1].resulting_version != self.version:
            raise ValueError("policy audit does not describe current catalogue")
        return self

    def rule(self, policy_id: str) -> PolicyRule | None:
        return next((rule for rule in self.rules if rule.policy_id == policy_id), None)


class CasePolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_label: Annotated[str, Field(min_length=3, max_length=64)]
    catalogue_version: Annotated[int, Field(ge=0)]
    idp_review_confidence_threshold: Annotated[
        Decimal, Field(ge=Decimal("0"), le=Decimal("1"), decimal_places=6)
    ]
    ubo_threshold_percent: Annotated[
        Decimal, Field(ge=Decimal("0"), le=Decimal("100"), decimal_places=6)
    ]
    comparator: Literal["GREATER_THAN_OR_EQUAL_TO"] = "GREATER_THAN_OR_EQUAL_TO"
    bound_at: datetime


def legacy_phase13_policy_snapshot(bound_at: datetime | None = None) -> CasePolicySnapshot:
    return CasePolicySnapshot(
        snapshot_label="LEGACY_PHASE13_DEFAULTS_V1",
        catalogue_version=0,
        idp_review_confidence_threshold=Decimal("0.85"),
        ubo_threshold_percent=Decimal("25.000000"),
        bound_at=bound_at or datetime(1970, 1, 1, tzinfo=UTC),
    )


def validate_policy_value(rule: PolicyRule, value: PolicyValue) -> None:
    if isinstance(value, DecimalPolicyValue):
        parsed = Decimal(value.value)
        if rule.minimum is not None and parsed < Decimal(str(rule.minimum)):
            raise ValueError("policy value is below minimum")
        if rule.maximum is not None and parsed > Decimal(str(rule.maximum)):
            raise ValueError("policy value is above maximum")
    elif isinstance(value, IntegerPolicyValue):
        if rule.minimum is not None and value.value < int(rule.minimum):
            raise ValueError("policy value is below minimum")
        if rule.maximum is not None and value.value > int(rule.maximum):
            raise ValueError("policy value is above maximum")
    if rule.allowed_values:
        items = value.value if isinstance(value, StringListPolicyValue) else (str(value.value),)
        if any(str(item) not in rule.allowed_values for item in items):
            raise ValueError("policy value is not allowed")


def validate_showcase_plain_text_value(value: PolicyValue) -> None:
    """Fail closed for user-authored showcase strings without constraining system values."""

    items: tuple[str, ...]
    if isinstance(value, StringPolicyValue):
        items = (value.value,)
    elif isinstance(value, StringListPolicyValue):
        items = value.value
    else:
        return
    if any(
        SHOWCASE_PLAIN_TEXT_PATTERN.fullmatch(item) is None
        or SHOWCASE_EXPRESSION_PREFIX_PATTERN.match(item) is not None
        for item in items
    ):
        raise ValueError("showcase string is not safe plain text")
