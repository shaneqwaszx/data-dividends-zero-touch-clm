"""Bounded confirmation input; document and source decisions remain distinct."""

import hashlib
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.documents import (
    DocumentFieldKey,
    DocumentProcessingRecord,
    FieldReviewStatus,
    ReviewDecision,
)
from app.domain.reconciliation import ReconciliationDecisionAction


class DocumentFieldDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_key: DocumentFieldKey
    decision: ReviewDecision
    corrected_value: str | None = Field(default=None, max_length=512)
    note: str | None = Field(default=None, max_length=240)


class DocumentDecisionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: UUID
    expected_event_count: int = Field(strict=True, ge=1)
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    decisions: tuple[DocumentFieldDecision, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def unique_fields(self) -> "DocumentDecisionGroup":
        if len({item.field_key for item in self.decisions}) != len(self.decisions):
            raise ValueError("Duplicate document decisions")
        return self


class ReconciliationChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    discrepancy_id: UUID
    action: ReconciliationDecisionAction
    evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ReviewDecisionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    expected_automation_version: int = Field(strict=True, ge=1)
    expected_case_event_count: int = Field(strict=True, ge=1)
    documents: tuple[DocumentDecisionGroup, ...] = Field(default=(), max_length=20)
    reconciliation: tuple[ReconciliationChoice, ...] = Field(default=(), max_length=80)
    expected_reconciliation_version: int | None = Field(default=None, strict=True, ge=1)

    @model_validator(mode="after")
    def one_decision_family(self) -> "ReviewDecisionBatch":
        if bool(self.documents) == bool(self.reconciliation):
            raise ValueError("Confirm exactly one decision family per current checkpoint")
        if len({item.document_id for item in self.documents}) != len(self.documents):
            raise ValueError("Duplicate document groups")
        if len({item.discrepancy_id for item in self.reconciliation}) != len(self.reconciliation):
            raise ValueError("Duplicate source decisions")
        if bool(self.reconciliation) != (self.expected_reconciliation_version is not None):
            raise ValueError("Source decisions require their current reconciliation version")
        return self


def document_review_source_fingerprint(record: DocumentProcessingRecord) -> str:
    """Bind immutable observations/comparisons independently of new review receipts."""
    source = record.model_copy(deep=True)
    for item in source.fields:
        item.review_status = FieldReviewStatus.PENDING
        item.reviewed_value = None
        item.reviewed_at = None
        item.review_note = None
    return hashlib.sha256(
        source.model_dump_json(
            exclude={
                "events",
                "state",
                "updated_at",
                "reviewed_at",
                "completion_method",
            }
        ).encode("utf-8")
    ).hexdigest()
