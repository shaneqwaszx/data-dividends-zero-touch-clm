"""Explicit schema-versioned representation for one durable CLM case."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.clm import ClmOrchestrationRecord
from app.domain.documents import DocumentProcessingRecord
from app.domain.models import OnboardingCase
from app.domain.ownership import OwnershipAnalysisRecord
from app.domain.reconciliation import ReconciliationCaseRecord
from app.domain.target_submission import GoldTierExecutionLedgerEntry
from app.domain.zero_touch import ZeroTouchAutomationRecord

CASE_SNAPSHOT_SCHEMA_VERSION: Literal[1] = 1


class DurableCaseSnapshot(BaseModel):
    """Bounded authoritative structured state; never raw source/upload payloads."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    case_id: UUID
    revision: int = Field(ge=0)
    onboarding: OnboardingCase
    documents: tuple[DocumentProcessingRecord, ...] = Field(default=(), max_length=40)
    ownership: OwnershipAnalysisRecord | None = None
    reconciliation: ReconciliationCaseRecord | None = None
    clm: ClmOrchestrationRecord | None = None
    automation: ZeroTouchAutomationRecord | None = None
    target_executions: tuple[GoldTierExecutionLedgerEntry, ...] = Field(
        default=(), max_length=4
    )
    demo_scenario: str | None = Field(default=None, min_length=1, max_length=64)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_case_bindings(self) -> "DurableCaseSnapshot":
        if self.onboarding.case_id != self.case_id:
            raise ValueError("onboarding case does not match envelope")
        records: tuple[Any, ...] = (
            *self.documents,
            *(
                item
                for item in (
                    self.ownership,
                    self.reconciliation,
                    self.clm,
                    self.automation,
                )
                if item is not None
            ),
        )
        if any(item.case_id != self.case_id for item in records):
            raise ValueError("nested record does not match envelope")
        if any(
            item.submission_input.case_id != self.case_id
            for item in self.target_executions
        ):
            raise ValueError("target execution does not match envelope")
        submission_ids = [
            item.submission_input.submission_id for item in self.target_executions
        ]
        if len(set(submission_ids)) != len(submission_ids):
            raise ValueError("duplicate target execution identity")
        return self
