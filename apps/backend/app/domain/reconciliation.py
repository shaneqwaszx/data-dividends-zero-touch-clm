"""Source-neutral field reconciliation, discrepancy, and decision models."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.models import SafeError

FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"


class ReconciliationField(StrEnum):
    LEGAL_NAME = "legal_name"
    REGISTRATION_IDENTIFIER = "registration_identifier"
    REGISTERED_ADDRESS = "registered_address"
    COUNTRY_OF_INCORPORATION = "country_of_incorporation"


class ReconciliationSourceKind(StrEnum):
    USER_INPUT = "USER_INPUT"
    REGISTRY = "REGISTRY"
    DOCUMENT_IDP = "DOCUMENT_IDP"
    EXISTING_CASE = "EXISTING_CASE"


class ObservationValidity(StrEnum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    UNVERIFIABLE = "UNVERIFIABLE"


class ReconciliationOutcome(StrEnum):
    MATCH = "MATCH"
    REGISTRY_ONLY = "REGISTRY_ONLY"
    MISSING_IN_SOURCE = "MISSING_IN_SOURCE"
    CONFLICT = "CONFLICT"
    UNVERIFIABLE = "UNVERIFIABLE"
    INVALID = "INVALID"


NON_BLOCKING_RECONCILIATION_OUTCOMES = frozenset(
    {ReconciliationOutcome.MATCH, ReconciliationOutcome.REGISTRY_ONLY}
)

CANONICAL_BASELINE_SOURCE_KINDS = frozenset(
    {ReconciliationSourceKind.REGISTRY, ReconciliationSourceKind.EXISTING_CASE}
)


class DiscrepancyStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class ReconciliationDecisionAction(StrEnum):
    KEEP_REGISTRY_VALUE = "KEEP_REGISTRY_VALUE"
    USE_DOCUMENT_VALUE = "USE_DOCUMENT_VALUE"


class ReconciliationStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    MATCHED = "MATCHED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


def derive_reconciliation_outcome(
    field_name: ReconciliationField,
    observations: tuple["ReconciliationObservation", ...],
    *,
    document_required: bool = True,
) -> ReconciliationOutcome:
    """Derive one truthful current outcome from normalized source observations."""

    if not document_required and field_name != ReconciliationField.REGISTERED_ADDRESS:
        raise ValueError("only registered address may be optional document evidence")
    if any(item.field_name != field_name for item in observations):
        raise ValueError("reconciliation observations must identify one field")
    sources = {item.source_kind for item in observations}
    if (
        not sources.intersection(CANONICAL_BASELINE_SOURCE_KINDS)
        or ReconciliationSourceKind.DOCUMENT_IDP not in sources
    ):
        raise ValueError(
            "reconciliation requires canonical baseline and Document observations"
        )
    if any(item.validity == ObservationValidity.INVALID for item in observations):
        return ReconciliationOutcome.INVALID
    if any(item.validity == ObservationValidity.UNVERIFIABLE for item in observations):
        return ReconciliationOutcome.UNVERIFIABLE
    baseline_observations = tuple(
        item
        for item in observations
        if item.source_kind in CANONICAL_BASELINE_SOURCE_KINDS
    )
    document_observations = tuple(
        item
        for item in observations
        if item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
    )
    if any(item.validity == ObservationValidity.MISSING for item in baseline_observations):
        return ReconciliationOutcome.MISSING_IN_SOURCE
    if not any(item.validity == ObservationValidity.VALID for item in document_observations):
        if not document_required and all(
            item.validity == ObservationValidity.MISSING for item in document_observations
        ):
            return ReconciliationOutcome.REGISTRY_ONLY
        return ReconciliationOutcome.MISSING_IN_SOURCE
    values = {
        item.normalized_value
        for item in observations
        if item.validity == ObservationValidity.VALID
    }
    if not values:
        raise ValueError("reconciliation requires at least one usable normalized value")
    return (
        ReconciliationOutcome.MATCH
        if len(values) == 1
        else ReconciliationOutcome.CONFLICT
    )


def derive_allowed_actions(
    field_name: ReconciliationField,
    outcome: ReconciliationOutcome,
    observations: tuple["ReconciliationObservation", ...],
) -> tuple[ReconciliationDecisionAction, ...]:
    """Advertise value selection only for a genuine usable source conflict."""

    if outcome != ReconciliationOutcome.CONFLICT:
        return ()
    if derive_reconciliation_outcome(field_name, observations) != outcome:
        raise ValueError("allowed actions require the observations' derived outcome")
    registry_values = {
        item.normalized_value
        for item in observations
        if item.source_kind == ReconciliationSourceKind.REGISTRY
        and item.validity == ObservationValidity.VALID
    }
    if len(registry_values) != 1:
        return ()
    registry_value = next(iter(registry_values))
    competing = {
        item.normalized_value
        for item in observations
        if item.source_kind != ReconciliationSourceKind.REGISTRY
        and item.validity == ObservationValidity.VALID
        and item.normalized_value != registry_value
    }
    if not competing:
        return ()
    actions = [ReconciliationDecisionAction.KEEP_REGISTRY_VALUE]
    document_values = {
        item.normalized_value
        for item in observations
        if item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
        and item.validity == ObservationValidity.VALID
        and item.normalized_value != registry_value
    }
    if field_name == ReconciliationField.LEGAL_NAME and len(document_values) == 1:
        actions.append(ReconciliationDecisionAction.USE_DOCUMENT_VALUE)
    return tuple(actions)


class ReconciliationObservation(BaseModel):
    """One immutable source fact; it is never replaced by a selected value."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    observation_id: UUID
    field_name: ReconciliationField
    raw_value: str | None = Field(default=None, max_length=512, exclude=True, repr=False)
    normalized_value: str | None = Field(default=None, max_length=512)
    source_kind: ReconciliationSourceKind
    source_system: str | None = Field(default=None, min_length=1, max_length=64)
    environment: str | None = Field(default=None, min_length=1, max_length=32)
    observed_at: datetime
    evidence_reference: str | None = Field(default=None, min_length=1, max_length=128)
    source_record_id: UUID | None = Field(default=None, exclude=True, repr=False)
    source_display_name: str | None = Field(default=None, min_length=5, max_length=99)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    validity: ObservationValidity

    @field_validator(
        "raw_value", "normalized_value", "source_system", "environment", "source_display_name"
    )
    @classmethod
    def optional_text_is_safe(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or any(ord(character) < 32 for character in normalized):
            raise ValueError("reconciliation text must be nonblank and control-free")
        return normalized

    @field_validator("evidence_reference")
    @classmethod
    def reference_is_opaque(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if (
            not normalized
            or any(ord(character) < 32 for character in normalized)
            or "://" in normalized
            or "?" in normalized
        ):
            raise ValueError("reconciliation references must be opaque and safe")
        return normalized

    @field_validator("observed_at")
    @classmethod
    def observed_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("reconciliation timestamps must be timezone-aware UTC")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_value_shape(self) -> "ReconciliationObservation":
        if self.validity == ObservationValidity.MISSING:
            if self.raw_value is not None or self.normalized_value is not None:
                raise ValueError("missing observations cannot retain a value")
        elif self.validity == ObservationValidity.VALID:
            if self.raw_value is None or self.normalized_value is None:
                raise ValueError("valid observations require raw and normalized values")
        elif self.raw_value is None:
            raise ValueError("invalid or unverifiable observations require supplied evidence")
        if (
            self.source_kind != ReconciliationSourceKind.DOCUMENT_IDP
            and self.confidence is not None
        ):
            raise ValueError("confidence is retained only when a document provider supplied it")
        if self.source_kind != ReconciliationSourceKind.DOCUMENT_IDP and self.source_record_id:
            raise ValueError("source record IDs are retained only for document observations")
        if self.source_kind != ReconciliationSourceKind.DOCUMENT_IDP and self.source_display_name:
            raise ValueError("source display names are retained only for document observations")
        return self


class ReconciliationDecision(BaseModel):
    """Explicit current-POC operator action without an invented reviewer identity."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    action: ReconciliationDecisionAction
    selected_observation_id: UUID
    selected_value: str = Field(min_length=1, max_length=512)
    decided_at: datetime
    reconciliation_version: int = Field(ge=1)
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=FINGERPRINT_PATTERN,
        exclude=True,
        repr=False,
    )

    @field_validator("decided_at")
    @classmethod
    def decided_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("decision timestamps must be timezone-aware UTC")
        return value.astimezone(UTC)


class ReconciliationDiscrepancy(BaseModel):
    """First-class discrepancy retaining every competing source observation."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    discrepancy_id: UUID
    field_name: ReconciliationField
    outcome: ReconciliationOutcome
    observations: tuple[ReconciliationObservation, ...] = Field(min_length=2, max_length=24)
    created_at: datetime
    status: DiscrepancyStatus = DiscrepancyStatus.OPEN
    allowed_actions: tuple[ReconciliationDecisionAction, ...] = Field(
        default_factory=tuple, max_length=2
    )
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=FINGERPRINT_PATTERN,
        exclude=True,
        repr=False,
    )
    decision: ReconciliationDecision | None = None

    @model_validator(mode="after")
    def validate_discrepancy(self) -> "ReconciliationDiscrepancy":
        derived_outcome = derive_reconciliation_outcome(
            self.field_name, self.observations
        )
        if self.outcome in NON_BLOCKING_RECONCILIATION_OUTCOMES:
            raise ValueError("non-blocking fields cannot create discrepancies")
        if self.outcome != derived_outcome:
            raise ValueError("discrepancy outcome must agree with its observations")
        if any(item.field_name != self.field_name for item in self.observations):
            raise ValueError("discrepancy observations must identify one field")
        observation_ids = [item.observation_id for item in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("discrepancy observation IDs must be unique")
        if len(self.allowed_actions) != len(set(self.allowed_actions)):
            raise ValueError("discrepancy actions must be unique")
        if self.allowed_actions != derive_allowed_actions(
            self.field_name, self.outcome, self.observations
        ):
            raise ValueError("discrepancy actions must match usable current evidence")
        if self.status == DiscrepancyStatus.RESOLVED:
            if self.decision is None:
                raise ValueError("resolved discrepancies require a decision")
            selected = next(
                (
                    item
                    for item in self.observations
                    if item.observation_id == self.decision.selected_observation_id
                ),
                None,
            )
            if selected is None or selected.normalized_value != self.decision.selected_value:
                raise ValueError("decision must select a retained discrepancy observation")
            expected_source = (
                ReconciliationSourceKind.REGISTRY
                if self.decision.action
                == ReconciliationDecisionAction.KEEP_REGISTRY_VALUE
                else ReconciliationSourceKind.DOCUMENT_IDP
            )
            if selected.source_kind != expected_source:
                raise ValueError("decision action and selected source must agree")
            if self.decision.action not in self.allowed_actions:
                raise ValueError("decision action must have been backend-authorized")
            if self.decision.evidence_fingerprint != self.evidence_fingerprint:
                raise ValueError("decision must be bound to discrepancy evidence")
        elif self.decision is not None:
            raise ValueError("only resolved discrepancies may retain decisions")
        return self


class FieldReconciliationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    field_name: ReconciliationField
    observations: tuple[ReconciliationObservation, ...] = Field(min_length=2, max_length=24)
    outcome: ReconciliationOutcome
    document_required: bool = True
    discrepancy_id: UUID | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "FieldReconciliationResult":
        if any(item.field_name != self.field_name for item in self.observations):
            raise ValueError("field observations must identify the result field")
        observation_ids = [item.observation_id for item in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("field observation IDs must be unique")
        if not self.document_required and self.field_name != ReconciliationField.REGISTERED_ADDRESS:
            raise ValueError("only registered address may be optional document evidence")
        if self.outcome != derive_reconciliation_outcome(
            self.field_name,
            self.observations,
            document_required=self.document_required,
        ):
            raise ValueError("field outcome must agree with its observations")
        if (self.outcome in NON_BLOCKING_RECONCILIATION_OUTCOMES) != (
            self.discrepancy_id is None
        ):
            raise ValueError("only blocking field results require a discrepancy")
        return self


class ReconciliationCaseRecord(BaseModel):
    """Process-local current reconciliation plus retained superseded discrepancies."""

    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    case_id: UUID
    reconciliation_id: UUID
    version: int = Field(default=0, ge=0)
    status: ReconciliationStatus
    source_document_ids: tuple[UUID, ...] = Field(default_factory=tuple, max_length=20)
    source_document_event_counts: tuple[int, ...] = Field(
        default_factory=tuple, max_length=20
    )
    evidence_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=FINGERPRINT_PATTERN,
        exclude=True,
        repr=False,
    )
    fields: tuple[FieldReconciliationResult, ...] = Field(default_factory=tuple, max_length=4)
    discrepancies: list[ReconciliationDiscrepancy] = Field(default_factory=list, max_length=64)
    error: SafeError | None = None
    created_at: datetime
    updated_at: datetime

    @property
    def open_discrepancies(self) -> list[ReconciliationDiscrepancy]:
        return [item for item in self.discrepancies if item.status == DiscrepancyStatus.OPEN]

    @property
    def semantically_cleared(self) -> bool:
        if self.status == ReconciliationStatus.MATCHED:
            return all(
                item.outcome in NON_BLOCKING_RECONCILIATION_OUTCOMES for item in self.fields
            )
        if self.status != ReconciliationStatus.RESOLVED:
            return False
        by_id = {item.discrepancy_id: item for item in self.discrepancies}
        current = [
            by_id[item.discrepancy_id]
            for item in self.fields
            if item.discrepancy_id is not None
        ]
        return bool(current) and all(
            item.status == DiscrepancyStatus.RESOLVED and item.decision is not None
            for item in current
        )

    @model_validator(mode="after")
    def validate_record(self) -> "ReconciliationCaseRecord":
        if self.status == ReconciliationStatus.NOT_STARTED:
            if (
                self.version != 0
                or self.source_document_ids
                or self.source_document_event_counts
                or self.fields
                or self.discrepancies
                or self.error is not None
            ):
                raise ValueError("not-started reconciliation cannot retain evidence")
            return self
        if self.status == ReconciliationStatus.FAILED and not self.fields:
            if (
                self.error is None
                or self.discrepancies
                or self.source_document_ids
                or self.source_document_event_counts
            ):
                raise ValueError("failed reconciliation requires one safe technical error")
            return self
        if (
            not self.source_document_ids
            or len(self.source_document_ids) != len(self.source_document_event_counts)
            or len(self.source_document_ids) != len(set(self.source_document_ids))
            or any(count < 1 for count in self.source_document_event_counts)
        ):
            raise ValueError("reconciliation document evidence versions are inconsistent")
        field_names = tuple(item.field_name for item in self.fields)
        if field_names != tuple(ReconciliationField):
            raise ValueError("reconciliation fields must be complete, unique, and ordered")
        discrepancy_ids = [item.discrepancy_id for item in self.discrepancies]
        if len(discrepancy_ids) != len(set(discrepancy_ids)):
            raise ValueError("reconciliation discrepancy IDs must be unique")
        by_id = {item.discrepancy_id: item for item in self.discrepancies}
        current_discrepancies: list[ReconciliationDiscrepancy] = []
        for field in self.fields:
            if field.discrepancy_id is None:
                continue
            discrepancy = by_id.get(field.discrepancy_id)
            if discrepancy is None or discrepancy.field_name != field.field_name:
                raise ValueError("field results must reference their retained discrepancy")
            if discrepancy.outcome != field.outcome:
                raise ValueError("field and discrepancy outcomes must agree")
            if discrepancy.observations != field.observations:
                raise ValueError("field and discrepancy observations must agree")
            if discrepancy.status == DiscrepancyStatus.CANCELLED:
                raise ValueError("current field cannot reference a cancelled discrepancy")
            current_discrepancies.append(discrepancy)
        open_current = [
            item for item in current_discrepancies if item.status == DiscrepancyStatus.OPEN
        ]
        open_all = self.open_discrepancies
        current_ids = {item.discrepancy_id for item in current_discrepancies}
        if any(item.discrepancy_id not in current_ids for item in open_all):
            raise ValueError("open discrepancies must be referenced by current fields")
        derived_status = (
            ReconciliationStatus.MATCHED
            if all(
                item.outcome in NON_BLOCKING_RECONCILIATION_OUTCOMES for item in self.fields
            )
            else (
                ReconciliationStatus.REVIEW_REQUIRED
                if open_current
                else ReconciliationStatus.RESOLVED
            )
        )
        if self.status == ReconciliationStatus.MATCHED:
            if (
                derived_status != ReconciliationStatus.MATCHED
                or current_discrepancies
                or open_all
                or self.error is not None
            ):
                raise ValueError("matched reconciliation cannot retain current discrepancies")
        elif self.status == ReconciliationStatus.REVIEW_REQUIRED:
            if (
                derived_status != ReconciliationStatus.REVIEW_REQUIRED
                or not open_current
                or self.error is not None
            ):
                raise ValueError("review-required reconciliation needs an open discrepancy")
        elif self.status == ReconciliationStatus.RESOLVED:
            if (
                derived_status != ReconciliationStatus.RESOLVED
                or not current_discrepancies
                or open_current
                or any(item.status != DiscrepancyStatus.RESOLVED for item in current_discrepancies)
                or self.error is not None
            ):
                raise ValueError("resolved reconciliation requires every current blocker resolved")
        elif self.status == ReconciliationStatus.FAILED:
            if self.error is None or open_current:
                raise ValueError("failed reconciliation requires one safe technical error")
        else:
            raise ValueError("unsupported reconciliation status semantics")
        return self
