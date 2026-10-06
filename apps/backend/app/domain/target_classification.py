"""Bounded case selection evidence, separate from policy authority and identity fields."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AUTO_KYC_TYPES = ("Company - Private", "Partnership - Unregulated", "Government")
VOCABULARY_VERSION: Literal["GOLDTIER_OPENAPI_V1_0_0"] = "GOLDTIER_OPENAPI_V1_0_0"


class TargetClassificationKey(StrEnum):
    KYC_CUSTOMER_TYPE = "kyc_customer_type"
    CLIENT_SEGMENT = "client_segment"


class ClassificationDocumentEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: UUID
    document_version: Literal[1]
    document_event_count: int = Field(strict=True, ge=1)
    page_number: int = Field(strict=True, ge=1, le=10)
    source_reference: str = Field(min_length=1, max_length=128, pattern=r"^[A-Z0-9_]+$")
    extraction_method: Literal[
        "NATIVE_PDF_TEXT", "NATIVE_DOCX_TEXT", "NATIVE_TXT_TEXT", "LOCAL_TESSERACT_OCR"
    ]
    extraction_quality: Literal["HIGH"]
    evidence_score: float = Field(ge=0, le=1)
    extracted_exact_value: str = Field(min_length=1, max_length=160)


class TargetClassificationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_key: TargetClassificationKey
    value: str = Field(min_length=1, max_length=160)
    source: Literal["DOCUMENT", "USER"]
    document_evidence: ClassificationDocumentEvidence | None = None
    evidence_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    actor_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9-]{2,31}$")
    classified_at: datetime
    policy_version: int = Field(strict=True, ge=0)
    vocabulary_version: Literal["GOLDTIER_OPENAPI_V1_0_0"] = VOCABULARY_VERSION

    @model_validator(mode="after")
    def evidence_agrees(self) -> "TargetClassificationSelection":
        if (self.source == "DOCUMENT") != (self.document_evidence is not None):
            raise ValueError("Document selection requires original document evidence")
        if self.document_evidence is not None:
            if " ".join(self.value.casefold().split()) != " ".join(
                self.document_evidence.extracted_exact_value.casefold().split()
            ):
                raise ValueError("Automatic selection must match its exact labelled evidence")
            if (
                self.field_key == TargetClassificationKey.KYC_CUSTOMER_TYPE
                and self.value not in AUTO_KYC_TYPES
            ):
                raise ValueError("Automatic KYC selection is outside the bounded POC types")
        if self.source == "DOCUMENT" and self.actor_id is not None:
            raise ValueError("Automatic evidence cannot claim a user actor")
        if (
            self.source == "USER"
            and self.evidence_fingerprint is not None
            and self.actor_id is None
        ):
            raise ValueError("Current user review requires its authenticated actor")
        return self


class ClassificationAssessmentState(StrEnum):
    NO_EVIDENCE = "NO_EVIDENCE"
    PARTIAL = "PARTIAL"
    SAFE_CANDIDATE = "SAFE_CANDIDATE"
    CONFLICT = "CONFLICT"
    UNSAFE = "UNSAFE"


class ClassificationFieldAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_key: TargetClassificationKey
    state: ClassificationAssessmentState
    candidate: TargetClassificationSelection | None = None
    trusted_values: tuple[str, ...] = Field(default=(), max_length=64)


class TargetClassificationAssessment(BaseModel):
    """Current evidence, including the reason an automatic candidate is unavailable."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    state: ClassificationAssessmentState
    evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    trusted_evidence_present: bool
    fields: tuple[ClassificationFieldAssessment, ...] = Field(min_length=2, max_length=2)

    @property
    def candidates(self) -> tuple[TargetClassificationSelection, ...]:
        return tuple(field.candidate for field in self.fields if field.candidate is not None)

    def selections_are_current(self, selections: tuple[TargetClassificationSelection, ...]) -> bool:
        by_key = {item.field_key: item for item in selections}
        for field in self.fields:
            selection = by_key.get(field.field_key)
            if field.state == ClassificationAssessmentState.CONFLICT and (
                selection is None or selection.source != "USER"
            ):
                return False
            if selection is None:
                continue
            if selection.evidence_fingerprint != self.evidence_fingerprint:
                return False
            if selection.source == "DOCUMENT":
                if field.candidate is None or field.candidate.model_dump(
                    exclude={"classified_at"}
                ) != selection.model_dump(exclude={"classified_at"}):
                    return False
            elif field.candidate is not None and field.candidate.value != selection.value:
                return False
        return True


def bounded_classification_compatible(party_type: str | None, kyc_customer_type: str) -> bool:
    """The existing sole bounded private-company/Government incompatibility rule."""
    return not (
        (party_type or "").upper().replace("_", " ") == "PRIVATE COMPANY LIMITED BY SHARES"
        and kyc_customer_type == "Government"
    )
