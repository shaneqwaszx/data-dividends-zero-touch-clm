"""Typed bounded global policy catalogue and immutable per-case policy snapshots."""

from __future__ import annotations

import re
import unicodedata
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
ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD_ID = "ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD"
ENTITY_RESOLUTION_REVIEW_THRESHOLD_ID = "ENTITY_RESOLUTION_REVIEW_THRESHOLD"
ENTITY_RESOLUTION_AMBIGUITY_MARGIN_ID = "ENTITY_RESOLUTION_AMBIGUITY_MARGIN"
ENTITY_RESOLUTION_IDENTIFIER_WEIGHT_ID = "ENTITY_RESOLUTION_IDENTIFIER_WEIGHT"
ENTITY_RESOLUTION_NAME_WEIGHT_ID = "ENTITY_RESOLUTION_NAME_WEIGHT"
ENTITY_RESOLUTION_ADDRESS_WEIGHT_ID = "ENTITY_RESOLUTION_ADDRESS_WEIGHT"
ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT_ID = "ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT"
ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT_ID = "ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT"
UBO_ADVISORY_LIKELY_THRESHOLD_ID = "UBO_ADVISORY_LIKELY_THRESHOLD"
UBO_ADVISORY_UNLIKELY_THRESHOLD_ID = "UBO_ADVISORY_UNLIKELY_THRESHOLD"
MOCK_RISK_MEDIUM_THRESHOLD_ID = "MOCK_RISK_MEDIUM_THRESHOLD"
MOCK_RISK_HIGH_THRESHOLD_ID = "MOCK_RISK_HIGH_THRESHOLD"
MOCK_RISK_BLOCKS_READINESS_ID = "MOCK_RISK_BLOCKS_READINESS"
GOLDTIER_KYC_CUSTOMER_TYPE_ID = "GOLDTIER_KYC_CUSTOMER_TYPE"
GOLDTIER_CLIENT_SEGMENT_ID = "GOLDTIER_CLIENT_SEGMENT"
GOLDTIER_VOCABULARY_VERSION = "GOLDTIER_OPENAPI_V1_0_0"
GOLDTIER_CLIENT_SEGMENT_VALUES = (
    "Corporate",
    "DI - Diversified Industrials",
    "DI - Education and Defence",
    "DI - Food, Beverage, and Agribusiness",
    "DI - Government",
    "DI - Telecom, Media, Entertainment, and Technology",
    "DI - Transport and Logistics",
    "FIG - Banks",
    "FIG - Diversified Financials",
    "FIG - Funds",
    "FIG - Insurance",
    "FIG - OSU",
    "Global Subsidiary Group",
    "Private Wealth",
    "Property and Health",
    "Resource, Energy, and Infrastructure",
    "Retail",
    "Commercial BB (Business Banking)",
    "Commercial RBB (Regional Business Banking)",
    "Commercial SBB (Small Business Banking)",
    "Corporate Finance",
    "Diversified & Specialist Industries",
    "Personal",
)
GOLDTIER_KYC_CUSTOMER_TYPE_VALUES = (
    "Association - Incorporated",
    "Association - Unincorporated",
    "Co-Operative",
    "Company - Private",
    "Company - Public",
    "Government",
    "Individual",
    "Managed Fund",
    "Partnership - Regulated",
    "Partnership - Unregulated",
    "Regulated Financial Institution",
    "Regulated Fund Manager - ANZ Approved",
    "Regulated Fund Manager - Non-ANZ Approved",
    "Sole Trader",
    "Trust - Regulated",
    "Trust - Unregulated",
    "Unregulated Fund Manager",
)
GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID = "GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM"
GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_POC_VALUE = "DSD"
GOLDTIER_REGISTRATION_TYPE_ID = "GOLDTIER_REGISTRATION_TYPE"
GOLDTIER_REGISTRATION_TYPE_POC_VALUE = "ACRA"
GOLDTIER_POLICY_POC_VALUE = "Singapore"
GOLDTIER_BOOKING_ENTITY_POC_VALUE = "ANZBGL (Singapore Branch)"
GOLDTIER_POLICY_ID = "GOLDTIER_POLICY"
GOLDTIER_BOOKING_ENTITY_ID = "GOLDTIER_BOOKING_ENTITY"
GOLDTIER_ACCOUNT_ENTITY_TYPE_ID = "GOLDTIER_ACCOUNT_ENTITY_TYPE"
GOLDTIER_ACCOUNT_ENTITY_TYPE_POC_VALUE = "PROJECT_DEFINED_PROVISIONAL"
GOLDTIER_PRODUCT_TYPE_ID = "GOLDTIER_PRODUCT_TYPE"
GOLDTIER_TARGET_POLICY_IDS = (
    GOLDTIER_KYC_CUSTOMER_TYPE_ID,
    GOLDTIER_CLIENT_SEGMENT_ID,
    GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM_ID,
    GOLDTIER_REGISTRATION_TYPE_ID,
    GOLDTIER_POLICY_ID,
    GOLDTIER_BOOKING_ENTITY_ID,
    GOLDTIER_ACCOUNT_ENTITY_TYPE_ID,
    GOLDTIER_PRODUCT_TYPE_ID,
)
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


class PolicyAuthority(StrEnum):
    SPONSOR_SUPPLIED = "SPONSOR_SUPPLIED"
    SPONSOR_DOCUMENTED = "SPONSOR_DOCUMENTED"
    SPONSOR_EXAMPLE = "SPONSOR_EXAMPLE"
    SANDBOX_OBSERVED = "SANDBOX_OBSERVED"
    USER_AUTHORIZED_POC = "USER_AUTHORIZED_POC"
    PROJECT_DERIVED_POC = "PROJECT_DERIVED_POC"
    PROJECT_DEFINED_PROVISIONAL = "PROJECT_DEFINED_PROVISIONAL"
    INDUSTRY_PRACTICE = "INDUSTRY_PRACTICE"
    TBD_SPONSOR = "TBD_SPONSOR"
    SANDBOX_TEST_ONLY = "SANDBOX_TEST_ONLY"


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


def normalize_safe_policy_text(value: str) -> str:
    """Normalize bounded policy text and reject characters unsafe for target dispatch."""

    normalized = value.strip()
    if not normalized or any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in normalized
    ):
        raise ValueError("policy text must be non-blank control-free text")
    return normalized


def is_usable_policy_text(value: str) -> bool:
    try:
        return normalize_safe_policy_text(value) == value
    except ValueError:
        return False


class StringPolicyValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal[PolicyValueType.STRING] = PolicyValueType.STRING
    value: Annotated[str, Field(min_length=1, max_length=160)]

    @field_validator("value")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return normalize_safe_policy_text(value)


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
        "POLICY_CATALOGUE_MIGRATED",
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
    authority: PolicyAuthority | None = None
    default_authority: PolicyAuthority | None = None
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
        if (self.authority is None) != (self.default_authority is None):
            raise ValueError("policy authority and default authority must be paired")
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


class EntityResolutionWeights(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identifier: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    name: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    address: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    legal_form: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    incorporation_date: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> EntityResolutionWeights:
        if (
            self.identifier + self.name + self.address + self.legal_form + self.incorporation_date
            != Decimal("1")
        ):
            raise ValueError("entity-resolution weights must sum to one")
        return self


class IntelligencePolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_resolution_auto_match_threshold: Annotated[
        Decimal, Field(ge=Decimal("0"), le=Decimal("1"))
    ]
    entity_resolution_review_threshold: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    entity_resolution_ambiguity_margin: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    entity_resolution_weights: EntityResolutionWeights
    ubo_advisory_likely_threshold: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    ubo_advisory_unlikely_threshold: Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
    mock_risk_medium_threshold: Annotated[int, Field(ge=0, le=100)]
    mock_risk_high_threshold: Annotated[int, Field(ge=0, le=100)]
    mock_risk_blocks_readiness: bool = False
    entity_resolution_model_version: Literal["entity-resolution-linear-v1"] = (
        "entity-resolution-linear-v1"
    )
    ubo_advisory_model_version: Literal["ubo-advisory-linear-v1"] = "ubo-advisory-linear-v1"
    mock_risk_model_version: Literal["mock-advisory-risk-rules-v1"] = "mock-advisory-risk-rules-v1"

    @model_validator(mode="after")
    def validate_threshold_order(self) -> IntelligencePolicySnapshot:
        if self.entity_resolution_review_threshold > self.entity_resolution_auto_match_threshold:
            raise ValueError("entity-resolution review threshold exceeds probable threshold")
        if self.ubo_advisory_unlikely_threshold >= self.ubo_advisory_likely_threshold:
            raise ValueError("UBO advisory thresholds overlap")
        if self.mock_risk_medium_threshold >= self.mock_risk_high_threshold:
            raise ValueError("mock risk thresholds overlap")
        return self


def legacy_intelligence_policy_snapshot() -> IntelligencePolicySnapshot:
    return IntelligencePolicySnapshot(
        entity_resolution_auto_match_threshold=Decimal("0.85"),
        entity_resolution_review_threshold=Decimal("0.60"),
        entity_resolution_ambiguity_margin=Decimal("0.03"),
        entity_resolution_weights=EntityResolutionWeights(
            identifier=Decimal("0.55"),
            name=Decimal("0.25"),
            address=Decimal("0.10"),
            legal_form=Decimal("0.05"),
            incorporation_date=Decimal("0.05"),
        ),
        ubo_advisory_likely_threshold=Decimal("0.65"),
        ubo_advisory_unlikely_threshold=Decimal("0.35"),
        mock_risk_medium_threshold=30,
        mock_risk_high_threshold=60,
    )


class AuthorityLabelledTargetValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: Annotated[str, Field(min_length=1, max_length=160)]
    authority: PolicyAuthority

    @field_validator("value")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return normalize_safe_policy_text(value)


class GoldTierTargetPolicySnapshot(BaseModel):
    """Case-bound institution-specific values; never canonical entity fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kyc_customer_type: AuthorityLabelledTargetValue
    client_segment: AuthorityLabelledTargetValue
    customer_external_system: AuthorityLabelledTargetValue
    registration_type: AuthorityLabelledTargetValue
    policy: AuthorityLabelledTargetValue
    booking_entity: AuthorityLabelledTargetValue
    account_entity_type: AuthorityLabelledTargetValue
    product_type: AuthorityLabelledTargetValue

    _OPTIONAL_SANDBOX_FIELDS = frozenset({"accountEntityType", "productType"})

    @property
    def dispatch_ready(self) -> bool:
        return not self.missing_fields and not self.invalid_fields

    @property
    def values(self) -> dict[str, AuthorityLabelledTargetValue]:
        return {
            "kycCustomerType": self.kyc_customer_type,
            "clientSegment": self.client_segment,
            "customerExternalSystem": self.customer_external_system,
            "registrationType": self.registration_type,
            "policy": self.policy,
            "bookingEntity": self.booking_entity,
            "accountEntityType": self.account_entity_type,
            "productType": self.product_type,
        }

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, item in self.values.items()
            if name not in self._OPTIONAL_SANDBOX_FIELDS
            and (item.authority == PolicyAuthority.TBD_SPONSOR or item.value == "TBD_SPONSOR")
        )

    @property
    def invalid_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, item in self.values.items()
            if name not in self.missing_fields
            and name not in self._OPTIONAL_SANDBOX_FIELDS
            and not is_usable_policy_text(item.value)
        )


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
    intelligence: IntelligencePolicySnapshot | None = None
    goldtier_target: GoldTierTargetPolicySnapshot | None = None
    bound_at: datetime


class CasePolicyRebindAudit(BaseModel):
    """Immutable bounded audit entry retaining the complete replaced snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    previous_revision: Annotated[int, Field(ge=1)]
    resulting_revision: Annotated[int, Field(ge=2)]
    previous_snapshot: CasePolicySnapshot
    actor_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{2,31}$")]
    rebound_at: datetime
    rationale: Annotated[str, Field(min_length=10, max_length=240)]
    changed_fields: Annotated[
        tuple[
            Literal[
                "customerExternalSystem",
                "registrationType",
                "policy",
                "bookingEntity",
            ],
            ...,
        ],
        Field(min_length=1, max_length=4),
    ]
    source_catalogue_version: Annotated[int, Field(ge=1)]

    @field_validator("rebound_at")
    @classmethod
    def rebound_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("policy rebind timestamp must be UTC")
        return value

    @field_validator("rationale")
    @classmethod
    def rationale_must_be_safe(cls, value: str) -> str:
        normalized = normalize_safe_policy_text(value)
        prohibited = (
            "ignore previous",
            "ignore prior",
            "system prompt",
            "developer message",
            "<script",
            "javascript:",
        )
        if any(marker in normalized.casefold() for marker in prohibited):
            raise ValueError("policy rebind rationale contains a prohibited marker")
        return normalized

    @model_validator(mode="after")
    def validate_revision(self) -> CasePolicyRebindAudit:
        if self.resulting_revision != self.previous_revision + 1:
            raise ValueError("policy rebind revision must increment exactly once")
        if len(set(self.changed_fields)) != len(self.changed_fields):
            raise ValueError("policy rebind changed fields must be unique")
        return self


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
