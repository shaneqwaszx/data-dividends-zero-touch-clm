"""Transient multi-format processing, deterministic comparison, and field review."""

import hashlib
import json
import re
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from typing import Never, Protocol
from unicodedata import category
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.connectors.idp import (
    IdpDocumentInput,
    IdpProcessingError,
    IdpProvider,
    IdpProviderMetadata,
    IdpSourceResult,
    LocalDocumentProcessingError,
)
from app.domain.documents import (
    ComparisonStatus,
    DocumentAutoClearAssessment,
    DocumentAutoClearBlocker,
    DocumentClassificationObservation,
    DocumentCompletionMethod,
    DocumentEventType,
    DocumentFieldKey,
    DocumentGovernmentStatusObservation,
    DocumentOwnershipObservation,
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
    DocumentSourceConflictResolution,
    DocumentWorkflowEvent,
    ExtractedField,
    ExtractionQuality,
    FieldProvenance,
    FieldReviewStatus,
    ReviewDecision,
)
from app.domain.models import CanonicalLegalEntity, EventOutcome, OnboardingCase, SafeError
from app.domain.policy import GOLDTIER_CLIENT_SEGMENT_VALUES, GOLDTIER_KYC_CUSTOMER_TYPE_VALUES
from app.domain.review_decisions import (
    DocumentDecisionGroup,
    document_review_source_fingerprint,
)
from app.domain.target_classification import (
    AUTO_KYC_TYPES,
    VOCABULARY_VERSION,
    ClassificationAssessmentState,
    ClassificationDocumentEvidence,
    ClassificationFieldAssessment,
    TargetClassificationAssessment,
    TargetClassificationKey,
    TargetClassificationSelection,
    bounded_classification_compatible,
)
from app.services.document_errors import (
    DocumentProcessingInfrastructureError,
    DocumentRequestError,
)
from app.services.document_media import DocumentMediaRouter, ExtractedDocumentContent
from app.services.document_repository import DocumentProcessingRepository

WHITESPACE = re.compile(r"\s+")
MAX_RETAINED_FIELD_VALUE = 512


class DocumentComparisonInputError(Exception):
    """Known invalid canonical input that cannot enter the bounded review model."""


class OnboardingCaseReader(Protocol):
    def get_case(self, case_id: UUID) -> OnboardingCase | None: ...


class DocumentProcessingService:
    """Own document safety, provider output, comparison, and human decisions."""

    def __init__(
        self,
        *,
        cases: OnboardingCaseReader,
        idp: IdpProvider,
        repository: DocumentProcessingRepository,
        max_upload_bytes: int,
        max_files_per_case: int = 20,
        max_total_intake_bytes: int = 25 * 1024 * 1024,
        review_confidence_threshold: float,
        media_router: DocumentMediaRouter | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        upload_observer: Callable[[UUID, UUID, ExtractedDocumentContent], None] | None = None,
    ) -> None:
        if max_upload_bytes <= 0:
            raise ValueError("max_upload_bytes must be positive")
        if max_files_per_case <= 0:
            raise ValueError("max_files_per_case must be positive")
        if max_total_intake_bytes < max_upload_bytes:
            raise ValueError("max_total_intake_bytes must allow one maximum-size document")
        if not 0.0 <= review_confidence_threshold <= 1.0:
            raise ValueError("review confidence threshold must be between zero and one")
        self._cases = cases
        self._idp = idp
        self._repository = repository
        self.max_upload_bytes = max_upload_bytes
        self.max_files_per_case = max_files_per_case
        self.max_total_intake_bytes = max_total_intake_bytes
        self.review_confidence_threshold = review_confidence_threshold
        self._media_router = media_router or DocumentMediaRouter()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._upload_observer = upload_observer

    def refresh_current_comparisons(self, *, case_id: UUID) -> None:
        """Recompare retained observations after an accepted identity correction.

        Extraction/provenance and human decisions remain evidence. No provider is
        called, no document is replaced, and comparison alone grants no authority.
        The caller owns the case lock and identity/currentness acceptance.
        """
        parent = self._cases.get_case(case_id)
        if parent is None or parent.entity is None:
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="Current canonical comparison evidence is unavailable.",
            )
        for record in self.list_documents(case_id=case_id):
            if not record.is_current_evidence or record.state not in {
                DocumentProcessingState.REVIEW_REQUIRED, DocumentProcessingState.REVIEWED,
            }:
                continue
            candidate = record.model_copy(deep=True)
            changed = False
            for field in candidate.fields:
                canonical = validate_canonical_comparison_value(
                    canonical_value_for_field(parent.entity, field.field_key)
                )
                comparison = compare_values(
                    field.field_key, field.original_extracted_value, canonical,
                )
                changed |= (
                    field.canonical_value != canonical or field.comparison_status != comparison
                )
                field.canonical_value = canonical
                field.comparison_status = comparison
            if changed:
                self._record(
                    candidate, event_type=DocumentEventType.DOCUMENT_PROCESSED,
                    state=candidate.state, outcome=EventOutcome.SUCCEEDED,
                    code="DOCUMENT_COMPARISON_RECOMPUTED",
                    message=(
                        "Retained document observations were compared "
                        "with current registry evidence."
                    ),
                )

    def review_confidence_threshold_for_case(self, case_id: UUID) -> float:
        """Return the immutable IDP threshold captured when the case was created."""

        case = self._cases.get_case(case_id)
        if case is None:
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        return float(case.policy_snapshot.idp_review_confidence_threshold)

    def validate_upload_metadata(
        self, *, case_id: UUID, display_name: str, content_type: str
    ) -> None:
        """Reject missing ownership and unsafe headers before reading request bytes."""

        if self._cases.get_case(case_id) is None:
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        self._media_router.validate_metadata(display_name=display_name, content_type=content_type)

    def create_document(
        self,
        *,
        case_id: UUID,
        display_name: str,
        content_type: str,
        content: bytes,
        provider: IdpProvider | None = None,
    ) -> DocumentProcessingRecord:
        with self._case_lock(case_id):
            return self._create_document_locked(
                case_id=case_id,
                display_name=display_name,
                content_type=content_type,
                content=content,
                provider=provider,
                replacing_document_id=None,
            )

    def replace_document(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        expected_event_count: int,
        display_name: str,
        content_type: str,
        content: bytes,
        provider: IdpProvider | None = None,
    ) -> DocumentProcessingRecord:
        """Create fresh evidence then explicitly supersede one current case document."""

        with self._case_lock(case_id):
            prior = self.get_document(case_id=case_id, document_id=document_id)
            if prior is None:
                raise DocumentRequestError(
                    code="DOCUMENT_NOT_FOUND",
                    message="The document review record was not found.",
                )
            if prior.superseded_by_document_id is not None:
                raise DocumentRequestError(
                    code="DOCUMENT_ALREADY_SUPERSEDED",
                    message="This document has already been replaced.",
                )
            if len(prior.events) != expected_event_count:
                raise DocumentRequestError(
                    code="DOCUMENT_REVIEW_STALE",
                    message="The document evidence changed before replacement.",
                )
            if prior.state not in {
                DocumentProcessingState.FAILED,
                DocumentProcessingState.REVIEW_REQUIRED,
                DocumentProcessingState.REVIEWED,
            }:
                raise DocumentRequestError(
                    code="DOCUMENT_NOT_REPLACEABLE",
                    message="This document cannot be replaced at its current state.",
                )
            try:
                replacement = self._create_document_locked(
                    case_id=case_id,
                    display_name=display_name,
                    content_type=content_type,
                    content=content,
                    provider=provider,
                    replacing_document_id=prior.document_id,
                )
            except DocumentProcessingInfrastructureError as error:
                failed_replacement = self.get_document(
                    case_id=case_id,
                    document_id=error.document_id,
                )
                if failed_replacement is not None:
                    self._supersede_document(prior=prior, replacement=failed_replacement)
                raise
            self._supersede_document(prior=prior, replacement=replacement)
            return replacement.model_copy(deep=True)

    def _supersede_document(
        self,
        *,
        prior: DocumentProcessingRecord,
        replacement: DocumentProcessingRecord,
    ) -> None:
        """Keep exactly one current record even when a replacement fails safely."""

        now = self._clock()
        prior.superseded_by_document_id = replacement.document_id
        prior.superseded_at = now
        prior = self._record(
            prior,
            event_type=DocumentEventType.DOCUMENT_SUPERSEDED,
            state=prior.state,
            outcome=EventOutcome.SUCCEEDED,
            code="DOCUMENT_SUPERSEDED",
            message="This document was superseded by explicit replacement evidence.",
        )
        replacement.supersedes_document_id = prior.document_id
        replacement.updated_at = now
        self._repository.save(replacement)

    def _create_document_locked(
        self,
        *,
        case_id: UUID,
        display_name: str,
        content_type: str,
        content: bytes,
        provider: IdpProvider | None,
        replacing_document_id: UUID | None,
    ) -> DocumentProcessingRecord:
        self.validate_upload_metadata(
            case_id=case_id,
            display_name=display_name,
            content_type=content_type,
        )
        self._validate_intake_limits(
            case_id=case_id,
            content_size=len(content),
            replacing_document_id=replacing_document_id,
        )
        extracted_content = self._media_router.extract(
            display_name=display_name,
            content_type=content_type,
            content=content,
        )
        parent_case = self._cases.get_case(case_id)
        if parent_case is None:  # Defensive against an in-process deletion race.
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )

        now = self._clock()
        record = DocumentProcessingRecord(
            case_id=case_id,
            document_id=self._uuid_factory(),
            correlation_id=self._uuid_factory(),
            display_name=display_name.strip(),
            media_type=extracted_content.media_type,
            size_bytes=len(content),
            content_sha256=hashlib.sha256(content).hexdigest(),
            profile=DocumentProfile.CERTIFICATE_OF_INCORPORATION_POC,
            document_version=1,
            state=DocumentProcessingState.UPLOADED,
            created_at=now,
            updated_at=now,
        )
        record = self._record(
            record,
            event_type=DocumentEventType.DOCUMENT_UPLOADED,
            state=DocumentProcessingState.UPLOADED,
            outcome=EventOutcome.SUCCEEDED,
            message="Document accepted for transient processing.",
        )
        return self._process_accepted_document(
            record=record,
            parent_case=parent_case,
            extracted_content=extracted_content,
            provider=provider or self._idp,
        )

    def _process_accepted_document(
        self,
        *,
        record: DocumentProcessingRecord,
        parent_case: OnboardingCase,
        extracted_content: ExtractedDocumentContent,
        provider: IdpProvider,
    ) -> DocumentProcessingRecord:
        """Run every required post-acceptance step inside a safe terminal boundary."""

        try:
            record = self._record(
                record,
                event_type=DocumentEventType.DOCUMENT_PROCESSING_STARTED,
                state=DocumentProcessingState.PROCESSING,
                outcome=EventOutcome.SUCCEEDED,
                message="IDP processing started.",
            )
            try:
                metadata = IdpProviderMetadata.model_validate(provider.metadata)
            except ValidationError:
                self._raise_terminal_failure(
                    record,
                    code="IDP_MALFORMED_OUTPUT",
                    message="IDP output could not be validated safely.",
                )
            record.provider_environment = metadata.environment

            try:
                provider_output = provider.process(
                    IdpDocumentInput(
                        profile=DocumentProfile.CERTIFICATE_OF_INCORPORATION_POC,
                        content=extracted_content.content,
                        media_type=extracted_content.media_type,
                        extracted_text=extracted_content.extracted_text,
                    )
                )
            except LocalDocumentProcessingError as error:
                self._raise_terminal_failure(
                    record, code=error.code,
                    message="Bounded local document processing could not be completed.",
                )
            except IdpProcessingError:
                self._raise_terminal_failure(
                    record,
                    code="IDP_PROCESSING_FAILED",
                    message="IDP processing could not be completed.",
                )
            try:
                source_result = IdpSourceResult.model_validate(provider_output)
            except ValidationError:
                self._raise_terminal_failure(
                    record,
                    code="IDP_MALFORMED_OUTPUT",
                    message="IDP output could not be validated safely.",
                )

            record.fields = [
                self._build_field(item, parent_case.entity, metadata)
                for item in source_result.fields
            ]
            record.pages = source_result.pages
            record.ownership_observations = tuple(
                DocumentOwnershipObservation(
                    **item.model_dump(), observation_id=self._uuid_factory(),
                    document_id=record.document_id, document_version=1,
                )
                for item in source_result.ownership_observations
            )
            record.classification_observations = tuple(
                DocumentClassificationObservation(
                    **item.model_dump(), document_id=record.document_id, document_version=1
                )
                for item in source_result.classification_observations
            )
            record.government_status_observations = tuple(
                DocumentGovernmentStatusObservation(
                    **item.model_dump(), document_id=record.document_id, document_version=1
                )
                for item in source_result.government_status_observations
            )
            record.processed_at = self._clock()
            record = self._record(
                record,
                event_type=DocumentEventType.DOCUMENT_PROCESSED,
                state=DocumentProcessingState.PROCESSING,
                outcome=EventOutcome.SUCCEEDED,
                message="Provider output validated and compared with canonical data.",
            )
            record = self._record(
                record,
                event_type=DocumentEventType.DOCUMENT_REVIEW_REQUIRED,
                state=DocumentProcessingState.REVIEW_REQUIRED,
                outcome=EventOutcome.REVIEW_REQUIRED,
                message="Human field review is required for this provisional document profile.",
                code="DOCUMENT_REVIEW_REQUIRED",
            )
            if self._upload_observer is not None:  # D-123: absent unless switched on.
                self._upload_observer(record.case_id, record.document_id, extracted_content)
            return record.model_copy(deep=True)
        except DocumentProcessingInfrastructureError:
            raise
        except DocumentComparisonInputError:
            self._raise_terminal_failure(
                record,
                code="DOCUMENT_COMPARISON_INPUT_INVALID",
                message="Canonical comparison data could not be processed safely.",
            )
        except Exception:
            self._raise_terminal_failure(
                record,
                code="IDP_UNEXPECTED_FAILURE",
                message="IDP processing could not be completed.",
            )

    def list_documents(self, *, case_id: UUID) -> list[DocumentProcessingRecord]:
        if self._cases.get_case(case_id) is None:
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        return self._repository.list_for_case(case_id)

    def assess_target_classification(self, *, case_id: UUID) -> TargetClassificationAssessment:
        """Distinguish trusted conflict, unsafe labels and absence through the document owner."""
        case = self._cases.get_case(case_id)
        if case is None:
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND", message="The onboarding case was not found."
            )
        documents = [doc for doc in self.list_documents(case_id=case_id) if doc.is_current_evidence]
        threshold = float(case.policy_snapshot.idp_review_confidence_threshold)
        trusted = [
            (doc, obs)
            for doc in documents
            if doc.state == DocumentProcessingState.REVIEWED
            and doc.document_version == 1
            and case.entity is not None
            and document_semantic_assessment(
                record=doc, current_entity=case.entity, confidence_threshold=threshold
            ).eligible
            for obs in doc.classification_observations
            if obs.extraction_quality == ExtractionQuality.HIGH
            and obs.extraction_method.value != "UNKNOWN"
            and obs.evidence_score >= threshold
        ]
        identities = sorted(
            (
                (
                    str(doc.document_id),
                    doc.document_version,
                    len(doc.events),
                    obs.field_key.value,
                    " ".join(obs.value.casefold().split()),
                    obs.page_number,
                    obs.source_reference,
                    obs.extraction_method.value,
                    obs.extraction_quality.value,
                    obs.evidence_score,
                    doc.provider_environment.value if doc.provider_environment is not None else "",
                    obs.score_kind.value,
                    obs.score_formula,
                )
                for doc, obs in trusted
            ),
            key=lambda identity: json.dumps(identity, separators=(",", ":"), ensure_ascii=True),
        )
        fingerprint = hashlib.sha256(
            json.dumps(
                (
                    "TARGET_CLASSIFICATION_EVIDENCE_V1",
                    str(case.case_id),
                    case.requested_uen,
                    (case.entity.party_type or "").upper().replace("_", " ")
                    if case.entity is not None
                    else "",
                    case.policy_snapshot.catalogue_version,
                    VOCABULARY_VERSION,
                    str(case.policy_snapshot.idp_review_confidence_threshold),
                    identities,
                ),
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        fields = []
        for key in TargetClassificationKey:
            observations = [
                (doc, obs)
                for doc in documents
                for obs in doc.classification_observations
                if obs.field_key == key
            ]
            authoritative = [(doc, obs) for doc, obs in trusted if obs.field_key == key]
            values = {" ".join(obs.value.casefold().split()) for _, obs in observations}
            trusted_values = {" ".join(obs.value.casefold().split()) for _, obs in authoritative}
            vocabulary = (
                AUTO_KYC_TYPES
                if key == TargetClassificationKey.KYC_CUSTOMER_TYPE
                else GOLDTIER_CLIENT_SEGMENT_VALUES
            )
            normalized = {" ".join(value.casefold().split()): value for value in vocabulary}
            candidate = None
            if not observations:
                state = ClassificationAssessmentState.NO_EVIDENCE
            elif len(trusted_values) > 1:
                state = ClassificationAssessmentState.CONFLICT
            elif (
                not authoritative
                or len(values) != 1
                or next(iter(values)) not in normalized
                or (
                    key == TargetClassificationKey.KYC_CUSTOMER_TYPE
                    and case.entity is not None
                    and not bounded_classification_compatible(
                        case.entity.party_type,
                        normalized.get(next(iter(values)), ""),
                        automatic=True,
                    )
                )
            ):
                state = ClassificationAssessmentState.UNSAFE
            else:
                state = ClassificationAssessmentState.SAFE_CANDIDATE
                doc, obs = max(
                    authoritative,
                    key=lambda pair: (pair[1].evidence_score, str(pair[0].document_id)),
                )
                candidate = TargetClassificationSelection(
                    field_key=key,
                    value=normalized[next(iter(values))],
                    source="DOCUMENT",
                    evidence_fingerprint=fingerprint,
                    document_evidence=ClassificationDocumentEvidence(
                        document_id=doc.document_id,
                        document_version=1,
                        document_event_count=len(doc.events),
                        page_number=obs.page_number,
                        source_reference=obs.source_reference,
                        extraction_method=obs.extraction_method.value,
                        extraction_quality="HIGH",
                        evidence_score=obs.evidence_score,
                        extracted_exact_value=obs.value,
                    ),
                    classified_at=self._clock(),
                    policy_version=case.policy_snapshot.catalogue_version,
                )
            display_vocabulary = (
                GOLDTIER_KYC_CUSTOMER_TYPE_VALUES
                if key == TargetClassificationKey.KYC_CUSTOMER_TYPE
                else GOLDTIER_CLIENT_SEGMENT_VALUES
            )
            display_values = {
                " ".join(value.casefold().split()): value for value in display_vocabulary
            }
            fields.append(
                ClassificationFieldAssessment(
                    field_key=key,
                    state=state,
                    candidate=candidate,
                    trusted_values=tuple(
                        sorted(
                            {
                                display_values.get(value, "Unsupported labelled value")
                                for value in trusted_values
                            }
                        )
                    ),
                )
            )
        states = {field.state for field in fields}
        if ClassificationAssessmentState.CONFLICT in states:
            state = ClassificationAssessmentState.CONFLICT
        elif states == {ClassificationAssessmentState.SAFE_CANDIDATE}:
            state = ClassificationAssessmentState.SAFE_CANDIDATE
        elif ClassificationAssessmentState.SAFE_CANDIDATE in states:
            state = ClassificationAssessmentState.PARTIAL
        elif ClassificationAssessmentState.UNSAFE in states:
            state = ClassificationAssessmentState.UNSAFE
        else:
            state = ClassificationAssessmentState.NO_EVIDENCE
        return TargetClassificationAssessment(
            state=state,
            evidence_fingerprint=fingerprint,
            trusted_evidence_present=bool(trusted),
            fields=tuple(fields),
        )

    def get_document(self, *, case_id: UUID, document_id: UUID) -> DocumentProcessingRecord | None:
        record = self._repository.get(document_id)
        if record is None or record.case_id != case_id:
            return None
        return record

    def review_field(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        field_key: DocumentFieldKey,
        decision: ReviewDecision,
        corrected_value: str | None = None,
        note: str | None = None,
    ) -> DocumentProcessingRecord:
        with self._case_lock(case_id):
            return self._review_field_locked(
                case_id=case_id,
                document_id=document_id,
                field_key=field_key,
                decision=decision,
                corrected_value=corrected_value,
                note=note,
            )

    def _review_field_locked(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        field_key: DocumentFieldKey,
        decision: ReviewDecision,
        corrected_value: str | None,
        note: str | None,
        record: DocumentProcessingRecord | None = None,
        persist: bool = True,
    ) -> DocumentProcessingRecord:
        record = record or self.get_document(case_id=case_id, document_id=document_id)
        if record is None:
            raise DocumentRequestError(
                code="DOCUMENT_NOT_FOUND",
                message="The document review record was not found.",
            )
        if not record.is_current_evidence:
            raise DocumentRequestError(
                code="DOCUMENT_ALREADY_SUPERSEDED",
                message="This document has already been replaced.",
            )
        if record.state not in {
            DocumentProcessingState.REVIEW_REQUIRED,
            DocumentProcessingState.REVIEWED,
        }:
            raise DocumentRequestError(
                code="DOCUMENT_NOT_REVIEWABLE",
                message="This document is not awaiting field review.",
            )

        field = next((item for item in record.fields if item.field_key == field_key), None)
        if field is None:
            raise DocumentRequestError(
                code="DOCUMENT_FIELD_NOT_FOUND",
                message="The provisional document field was not found.",
            )

        reviewed_value = self._validate_review_input(
            field=field,
            decision=decision,
            corrected_value=corrected_value,
        )
        normalized_note = _safe_optional_review_text(note)
        target_status = FieldReviewStatus(decision.value)
        if field.review_status != FieldReviewStatus.PENDING:
            if (
                field.review_status == target_status
                and field.reviewed_value == reviewed_value
                and field.review_note == normalized_note
            ):
                return record
            raise DocumentRequestError(
                code="DOCUMENT_FIELD_REVIEW_CONFLICT",
                message="A different final review decision already exists for this field.",
            )

        field.review_status = target_status
        field.reviewed_value = reviewed_value
        field.reviewed_at = self._clock()
        field.review_note = normalized_note
        event_type = {
            ReviewDecision.ACCEPTED: DocumentEventType.DOCUMENT_FIELD_ACCEPTED,
            ReviewDecision.REJECTED: DocumentEventType.DOCUMENT_FIELD_REJECTED,
            ReviewDecision.CORRECTED: DocumentEventType.DOCUMENT_FIELD_CORRECTED,
        }[decision]
        record = self._record(
            record,
            event_type=event_type,
            state=DocumentProcessingState.REVIEW_REQUIRED,
            outcome=(
                EventOutcome.PARTIAL
                if decision == ReviewDecision.REJECTED
                else EventOutcome.SUCCEEDED
            ),
            message={
                ReviewDecision.ACCEPTED: "A document field suggestion was accepted.",
                ReviewDecision.REJECTED: "A document field suggestion was rejected.",
                ReviewDecision.CORRECTED: "A document field suggestion was corrected.",
            }[decision],
            code=event_type.value,
            field_key=field_key,
            persist=persist,
        )

        if all(item.review_status != FieldReviewStatus.PENDING for item in record.fields):
            record.reviewed_at = self._clock()
            record.completion_method = DocumentCompletionMethod.HUMAN_REVIEWED
            record = self._record(
                record,
                event_type=DocumentEventType.DOCUMENT_REVIEW_COMPLETED,
                state=DocumentProcessingState.REVIEWED,
                outcome=EventOutcome.SUCCEEDED,
                message="All provisional document fields received a human review decision.",
                code="DOCUMENT_REVIEW_COMPLETED",
                persist=persist,
            )
        return record.model_copy(deep=True)

    def prepare_review_group(
        self,
        *,
        case_id: UUID,
        group: DocumentDecisionGroup,
    ) -> DocumentProcessingRecord:
        """Validate all choices without writes; unchanged partial receipts can resume."""
        current = self.get_document(case_id=case_id, document_id=group.document_id)
        if (
            current is None
            or not current.is_current_evidence
            or document_review_source_fingerprint(current) != group.source_fingerprint
            or len(current.events) < group.expected_event_count
        ):
            raise DocumentRequestError(
                code="DOCUMENT_REVIEW_STALE",
                message="Document source evidence changed before review.",
            )
        by_key = {item.field_key: item for item in group.decisions}
        if len(current.events) != group.expected_event_count:
            # Only receipts from this exact group may appear after its base version.
            # Replacement, auto-confirm, comparison refresh and other decisions fail closed.
            allowed_events = {
                DocumentEventType.DOCUMENT_FIELD_ACCEPTED,
                DocumentEventType.DOCUMENT_FIELD_REJECTED,
                DocumentEventType.DOCUMENT_FIELD_CORRECTED,
                DocumentEventType.DOCUMENT_REVIEW_COMPLETED,
            }
            tail = current.events[group.expected_event_count :]
            if any(
                event.event_type not in allowed_events
                or (event.field_key is not None and event.field_key not in by_key)
                for event in tail
            ):
                raise DocumentRequestError(
                    code="DOCUMENT_REVIEW_STALE",
                    message="Document review changed before confirmation.",
                )
        candidate = current.model_copy(deep=True)
        for decision in group.decisions:
            candidate = self._review_field_locked(
                case_id=case_id,
                document_id=group.document_id,
                field_key=decision.field_key,
                decision=decision.decision,
                corrected_value=decision.corrected_value,
                note=decision.note,
                record=candidate,
                persist=False,
            )
        return DocumentProcessingRecord.model_validate(candidate)

    def retain_review_group(self, *, candidate: DocumentProcessingRecord) -> None:
        """One section checkpoint per document, called under the canonical case lock."""
        current = self.get_document(case_id=candidate.case_id, document_id=candidate.document_id)
        if (
            current is None
            or not current.is_current_evidence
            or document_review_source_fingerprint(current)
            != document_review_source_fingerprint(candidate)
            or len(current.events) > len(candidate.events)
            or current.events != candidate.events[: len(current.events)]
            or any(
                field.review_status != FieldReviewStatus.PENDING
                and field
                != next(item for item in candidate.fields if item.field_key == field.field_key)
                for field in current.fields
            )
        ):
            raise DocumentRequestError(
                code="DOCUMENT_REVIEW_STALE", message="Document evidence is no longer current."
            )
        if len(current.events) != len(candidate.events):
            try:
                self._repository.save(candidate)
            except Exception:
                raise DocumentProcessingInfrastructureError(
                    case_id=candidate.case_id,
                    document_id=candidate.document_id,
                    correlation_id=candidate.correlation_id,
                    code="DOCUMENT_REVIEW_COMMIT_FAILED",
                    message="Document decisions could not be retained safely.",
                ) from None

    def assess_auto_clear(self, *, case_id: UUID, document_id: UUID) -> DocumentAutoClearAssessment:
        """Evaluate the shared Phase 05/06 semantic document checkpoint."""

        record = self.get_document(case_id=case_id, document_id=document_id)
        if record is None:
            raise DocumentRequestError(
                code="DOCUMENT_NOT_FOUND",
                message="The document review record was not found.",
            )
        parent = self._cases.get_case(case_id)
        if parent is None:
            raise DocumentRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        assessment = document_semantic_assessment(
            record=record,
            current_entity=parent.entity,
            confidence_threshold=float(parent.policy_snapshot.idp_review_confidence_threshold),
        )
        blockers = list(assessment.blockers)
        for other in self.list_documents(case_id=case_id):
            if other.document_id == record.document_id or not other.is_current_evidence:
                continue
            other_assessment = document_semantic_assessment(
                record=other,
                current_entity=parent.entity,
                confidence_threshold=float(parent.policy_snapshot.idp_review_confidence_threshold),
            )
            if (
                DocumentAutoClearBlocker.SOURCE_CONFLICT in other_assessment.blockers
                and DocumentAutoClearBlocker.SOURCE_CONFLICT not in blockers
            ):
                blockers.append(DocumentAutoClearBlocker.SOURCE_CONFLICT)
        return DocumentAutoClearAssessment(eligible=not blockers, blockers=tuple(blockers))

    def auto_confirm_document(
        self, *, case_id: UUID, document_id: UUID, allow_partial: bool = False
    ) -> DocumentProcessingRecord:
        """Auto-confirm only complete, current, all-match, high-confidence evidence."""

        with self._case_lock(case_id):
            assessment = self.assess_auto_clear(case_id=case_id, document_id=document_id)
            if not assessment.eligible and not allow_partial:
                raise DocumentRequestError(
                    code="DOCUMENT_AUTO_CLEAR_BLOCKED",
                    message="The document does not satisfy the provisional auto-clear policy.",
                )
            record = self.get_document(case_id=case_id, document_id=document_id)
            if record is None:
                raise DocumentRequestError(
                    code="DOCUMENT_NOT_FOUND",
                    message="The document review record was not found.",
                )
            parent = self._cases.get_case(case_id)
            if (
                parent is None
                or not record.is_current_evidence
                or record.state != DocumentProcessingState.REVIEW_REQUIRED
            ):
                return record
            current_documents = self.list_documents(case_id=case_id)
            now = self._clock()
            pending = [
                field for field in record.fields if field.review_status == FieldReviewStatus.PENDING
            ]
            if not pending:
                return record
            had_operator_decision = any(
                event.event_type
                in {
                    DocumentEventType.DOCUMENT_FIELD_ACCEPTED,
                    DocumentEventType.DOCUMENT_FIELD_REJECTED,
                    DocumentEventType.DOCUMENT_FIELD_CORRECTED,
                }
                for event in record.events
            )
            confirmed_keys: list[DocumentFieldKey] = []
            for field in record.fields:
                if field.review_status != FieldReviewStatus.PENDING:
                    continue
                if field.original_extracted_value is None:
                    # An optional absent field has no value to confirm.
                    continue
                canonical = canonical_value_for_field(parent.entity, field.field_key)
                if (
                    field.extraction_quality == ExtractionQuality.AMBIGUOUS
                    or field.confidence < float(
                        parent.policy_snapshot.idp_review_confidence_threshold
                    )
                    or field.comparison_status != ComparisonStatus.MATCH
                    or compare_values(field.field_key, field.canonical_value, canonical)
                    != ComparisonStatus.MATCH
                    or compare_values(field.field_key, field.original_extracted_value, canonical)
                    != ComparisonStatus.MATCH
                ):
                    continue
                contradictory = False
                for other in current_documents:
                    if other.document_id == record.document_id or not other.is_current_evidence:
                        continue
                    other_field = next(
                        (item for item in other.fields if item.field_key == field.field_key), None
                    )
                    if other_field is None or other_field.original_extracted_value is None:
                        continue
                    effective = (
                        other_field.reviewed_value
                        if other_field.review_status
                        in {
                            FieldReviewStatus.ACCEPTED,
                            FieldReviewStatus.CORRECTED,
                        }
                        else other_field.original_extracted_value
                    )
                    resolved = any(
                        item.field_key == field.field_key
                        and compare_values(
                            field.field_key,
                            item.registry_value,
                            canonical,
                        )
                        == ComparisonStatus.MATCH
                        for item in other.source_conflict_resolutions
                    )
                    if not resolved and (
                        other_field.review_status == FieldReviewStatus.REJECTED
                        or compare_values(field.field_key, effective, canonical)
                        != ComparisonStatus.MATCH
                    ):
                        contradictory = True
                if contradictory:
                    continue
                field.review_status = FieldReviewStatus.ACCEPTED
                field.reviewed_value = field.original_extracted_value
                field.reviewed_at = now
                confirmed_keys.append(field.field_key)
            for field_key in confirmed_keys:
                record = self._record(
                    record,
                    event_type=DocumentEventType.DOCUMENT_AUTO_CONFIRMED,
                    state=DocumentProcessingState.REVIEW_REQUIRED,
                    outcome=EventOutcome.SUCCEEDED,
                    field_key=field_key,
                    code="DOCUMENT_FIELD_AUTO_CONFIRMED",
                    message="A matching current field met the automated confidence rule.",
                )
            if not confirmed_keys:
                return record
            if not self.assess_auto_clear(case_id=case_id, document_id=document_id).eligible:
                return record.model_copy(deep=True)
            record.reviewed_at = now
            record.completion_method = (
                DocumentCompletionMethod.HUMAN_REVIEWED
                if had_operator_decision
                else DocumentCompletionMethod.AUTO_CONFIRMED
            )
            return self._record(
                record,
                event_type=DocumentEventType.DOCUMENT_AUTO_CONFIRMED,
                state=DocumentProcessingState.REVIEWED,
                outcome=EventOutcome.SUCCEEDED,
                code="DOCUMENT_AUTO_CONFIRMED",
                message="Document evidence met the provisional automated confirmation rule.",
            ).model_copy(deep=True)

    def resolve_with_registry_values(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        expected_event_count: int,
    ) -> DocumentProcessingRecord:
        """Resolve source conflicts only, preserving every unrelated blocker."""

        with self._case_lock(case_id):
            record = self.get_document(case_id=case_id, document_id=document_id)
            parent = self._cases.get_case(case_id)
            if record is None or parent is None:
                raise DocumentRequestError(
                    code="DOCUMENT_NOT_FOUND",
                    message="The document review record was not found.",
                )
            if len(record.events) != expected_event_count:
                raise DocumentRequestError(
                    code="DOCUMENT_REVIEW_STALE",
                    message="The document evidence changed before this resolution.",
                )
            if record.state not in {
                DocumentProcessingState.REVIEW_REQUIRED,
                DocumentProcessingState.REVIEWED,
            }:
                raise DocumentRequestError(
                    code="DOCUMENT_NOT_REVIEWABLE",
                    message="This document is not awaiting field review.",
                )
            now = self._clock()
            resolved_any = False
            for field in record.fields:
                current_value = validate_canonical_comparison_value(
                    canonical_value_for_field(parent.entity, field.field_key)
                )
                if current_value is None:
                    raise DocumentRequestError(
                        code="DOCUMENT_REGISTRY_VALUE_UNAVAILABLE",
                        message="A required registry value is unavailable for this resolution.",
                    )
                effective_value = (
                    field.reviewed_value
                    if field.review_status
                    in {FieldReviewStatus.ACCEPTED, FieldReviewStatus.CORRECTED}
                    else field.original_extracted_value
                )
                matches = (
                    compare_values(
                        field.field_key,
                        effective_value,
                        current_value,
                    )
                    == ComparisonStatus.MATCH
                )
                resolution_exists = any(
                    resolution.field_key == field.field_key
                    and resolution.action == "KEEP_REGISTRY_VALUE"
                    and compare_values(field.field_key, resolution.registry_value, current_value)
                    == ComparisonStatus.MATCH
                    for resolution in record.source_conflict_resolutions
                )
                if matches or resolution_exists:
                    continue
                record.source_conflict_resolutions.append(
                    DocumentSourceConflictResolution(
                        field_key=field.field_key,
                        action="KEEP_REGISTRY_VALUE",
                        registry_value=current_value,
                        resolved_at=now,
                    )
                )
                resolved_any = True
            if not resolved_any:
                raise DocumentRequestError(
                    code="DOCUMENT_SOURCE_CONFLICT_NOT_FOUND",
                    message="The document no longer contains a resolvable source conflict.",
                )
            remaining = document_semantic_assessment(
                record=record,
                current_entity=parent.entity,
                confidence_threshold=float(parent.policy_snapshot.idp_review_confidence_threshold),
            )
            next_state = DocumentProcessingState.REVIEW_REQUIRED
            if not remaining.blockers:
                record.reviewed_at = now
                record.completion_method = DocumentCompletionMethod.EXCEPTION_RESOLVED
                next_state = DocumentProcessingState.REVIEWED
            return self._record(
                record,
                event_type=DocumentEventType.DOCUMENT_EXCEPTION_RESOLVED,
                state=next_state,
                outcome=EventOutcome.SUCCEEDED,
                code="KEEP_REGISTRY_VALUE",
                message=(
                    "Document source conflicts were resolved by retaining current registry "
                    "values; unrelated review blockers remain authoritative."
                ),
            ).model_copy(deep=True)

    def _case_lock(self, case_id: UUID) -> AbstractContextManager[object]:
        lock_factory = getattr(self._cases, "case_lock", None)
        return lock_factory(case_id) if callable(lock_factory) else nullcontext()

    def _build_field(
        self,
        source_field: object,
        entity: CanonicalLegalEntity | None,
        metadata: IdpProviderMetadata,
    ) -> ExtractedField:
        from app.connectors.idp import IdpSourceField

        item = IdpSourceField.model_validate(source_field)
        canonical_value = validate_canonical_comparison_value(
            canonical_value_for_field(entity, item.field_key)
        )
        normalized_value = normalize_document_value(item.field_key, item.value)
        comparison = compare_values(item.field_key, item.value, canonical_value)
        return ExtractedField(
            field_key=item.field_key,
            original_extracted_value=item.value,
            normalized_value=normalized_value,
            confidence=item.confidence,
            candidates=item.candidates,
            extraction_method=item.extraction_method,
            extraction_quality=item.extraction_quality,
            score_kind=item.score_kind,
            score_formula=item.score_formula,
            raw_ocr_mean_confidence=item.raw_ocr_mean_confidence,
            raw_ocr_word_count=item.raw_ocr_word_count,
            provenance=FieldProvenance(
                provider=metadata.provider_name,
                environment=metadata.environment,
                page_number=item.page_number,
                source_reference=item.source_reference,
            ),
            canonical_value=canonical_value,
            comparison_status=comparison,
        )

    def _validate_review_input(
        self,
        *,
        field: ExtractedField,
        decision: ReviewDecision,
        corrected_value: str | None,
    ) -> str | None:
        normalized_correction = _safe_optional_review_text(corrected_value, max_length=512)
        if decision == ReviewDecision.CORRECTED:
            if normalized_correction is None:
                raise DocumentRequestError(
                    code="DOCUMENT_CORRECTION_REQUIRED",
                    message="A corrected field decision requires a nonblank corrected value.",
                )
            return normalized_correction
        if normalized_correction is not None:
            raise DocumentRequestError(
                code="DOCUMENT_CORRECTION_NOT_ALLOWED",
                message="A corrected value is allowed only for a corrected field decision.",
            )
        if decision == ReviewDecision.ACCEPTED:
            if field.original_extracted_value is None:
                raise DocumentRequestError(
                    code="DOCUMENT_MISSING_VALUE_CANNOT_BE_ACCEPTED",
                    message="A missing document value must be rejected or corrected.",
                )
            return field.original_extracted_value
        return None

    def _validate_intake_limits(
        self,
        *,
        case_id: UUID,
        content_size: int,
        replacing_document_id: UUID | None,
    ) -> None:
        if content_size <= 0:
            raise DocumentRequestError(
                code="DOCUMENT_EMPTY",
                message="The uploaded document is empty.",
            )
        if content_size > self.max_upload_bytes:
            raise DocumentRequestError(
                code="DOCUMENT_TOO_LARGE",
                message="The uploaded document exceeds the configured per-file size limit.",
            )
        current = [
            item
            for item in self._repository.list_for_case(case_id)
            if item.is_current_evidence and item.document_id != replacing_document_id
        ]
        if len(current) >= self.max_files_per_case:
            raise DocumentRequestError(
                code="DOCUMENT_COUNT_LIMIT_EXCEEDED",
                message="The document intake exceeds the configured file-count limit.",
            )
        if sum(item.size_bytes for item in current) + content_size > self.max_total_intake_bytes:
            raise DocumentRequestError(
                code="DOCUMENT_TOTAL_SIZE_LIMIT_EXCEEDED",
                message="The document intake exceeds the configured total-size limit.",
            )

    def _record(
        self,
        record: DocumentProcessingRecord,
        *,
        event_type: DocumentEventType,
        state: DocumentProcessingState,
        outcome: EventOutcome,
        message: str,
        code: str | None = None,
        field_key: DocumentFieldKey | None = None,
        persist: bool = True,
    ) -> DocumentProcessingRecord:
        timestamp = self._clock()
        candidate = record.model_copy(deep=True)
        candidate.state = state
        candidate.updated_at = timestamp
        candidate.events.append(
            DocumentWorkflowEvent(
                sequence=len(candidate.events) + 1,
                event_type=event_type,
                state=state,
                outcome=outcome,
                timestamp=timestamp,
                case_id=candidate.case_id,
                document_id=candidate.document_id,
                correlation_id=candidate.correlation_id,
                field_key=field_key,
                code=code,
                message=message,
            )
        )
        if persist:
            self._repository.save(candidate)
        return candidate

    def _raise_terminal_failure(
        self,
        record: DocumentProcessingRecord,
        *,
        code: str,
        message: str,
    ) -> Never:
        failed_record = record.model_copy(deep=True)
        failed_record.fields = []
        failed_record.pages = ()
        failed_record.ownership_observations = ()
        failed_record.government_status_observations = ()
        failed_record.processed_at = None
        failed_record.classification_observations = ()
        failed_record.reviewed_at = None
        failed_record.error = SafeError(code=code, message=message)
        failed_record = self._record(
            failed_record,
            event_type=DocumentEventType.DOCUMENT_PROCESSING_FAILED,
            state=DocumentProcessingState.FAILED,
            outcome=EventOutcome.FAILED,
            message=message,
            code=code,
        )
        raise DocumentProcessingInfrastructureError(
            case_id=failed_record.case_id,
            document_id=failed_record.document_id,
            correlation_id=failed_record.correlation_id,
            code=code,
            message=message,
        ) from None


def document_semantic_assessment(
    *,
    record: DocumentProcessingRecord,
    current_entity: CanonicalLegalEntity | None,
    confidence_threshold: float,
) -> DocumentAutoClearAssessment:
    """Apply one conservative semantic rule to pending and reviewed documents."""

    blockers: list[DocumentAutoClearBlocker] = []

    def block(code: DocumentAutoClearBlocker) -> None:
        if code not in blockers:
            blockers.append(code)

    if record.state not in {
        DocumentProcessingState.REVIEW_REQUIRED,
        DocumentProcessingState.REVIEWED,
    }:
        block(DocumentAutoClearBlocker.REVIEW_STATE_INVALID)
    if not record.is_current_evidence:
        block(DocumentAutoClearBlocker.REVIEW_STATE_INVALID)
    fields_by_key = {field.field_key: field for field in record.fields}
    if fields_by_key and all(
        field.provenance.source_reference == "DOCUMENT_TEXT_UNAVAILABLE"
        for field in fields_by_key.values()
    ):
        block(DocumentAutoClearBlocker.TEXT_UNAVAILABLE)
    required_fields = required_document_fields(record.profile)
    for field_key in DocumentFieldKey:
        field = fields_by_key.get(field_key)
        if field is not None and field.extraction_quality == ExtractionQuality.AMBIGUOUS:
            block(DocumentAutoClearBlocker.AMBIGUOUS_EXTRACTION)
        if field is None or field.original_extracted_value is None:
            if field_key in required_fields:
                block(DocumentAutoClearBlocker.REQUIRED_FIELD_MISSING)
            continue
        if field.confidence < confidence_threshold:
            block(DocumentAutoClearBlocker.LOW_CONFIDENCE)
        current_canonical = canonical_value_for_field(current_entity, field_key)
        resolution_matches = any(
            resolution.field_key == field_key
            and resolution.action == "KEEP_REGISTRY_VALUE"
            and compare_values(field_key, resolution.registry_value, current_canonical)
            == ComparisonStatus.MATCH
            for resolution in record.source_conflict_resolutions
        )
        if resolution_matches:
            continue
        if field.review_status == FieldReviewStatus.PENDING and (
            field.comparison_status != ComparisonStatus.MATCH
            or compare_values(field_key, field.canonical_value, current_canonical)
            != ComparisonStatus.MATCH
        ):
            block(DocumentAutoClearBlocker.SOURCE_CONFLICT)
        if field.review_status in {
            FieldReviewStatus.ACCEPTED,
            FieldReviewStatus.CORRECTED,
        }:
            effective_value = field.reviewed_value
        elif field.review_status == FieldReviewStatus.REJECTED:
            effective_value = None
        else:
            effective_value = field.original_extracted_value
        if compare_values(field_key, effective_value, current_canonical) != ComparisonStatus.MATCH:
            block(DocumentAutoClearBlocker.SOURCE_CONFLICT)
    return DocumentAutoClearAssessment(eligible=not blockers, blockers=tuple(blockers))


def required_document_fields(profile: DocumentProfile) -> frozenset[DocumentFieldKey]:
    """Return semantic requiredness while retaining the legacy four-field profile."""

    if profile == DocumentProfile.CERTIFICATE_OF_INCORPORATION_POC:
        return frozenset(
            {
                DocumentFieldKey.LEGAL_NAME,
                DocumentFieldKey.REGISTRATION_NUMBER,
                DocumentFieldKey.COUNTRY_OF_INCORPORATION,
            }
        )
    return frozenset(DocumentFieldKey)


def canonical_value_for_field(
    entity: CanonicalLegalEntity | None, field_key: DocumentFieldKey
) -> str | None:
    if entity is None:
        return None
    if field_key == DocumentFieldKey.REGISTRATION_NUMBER:
        return entity.registration_number
    if field_key == DocumentFieldKey.LEGAL_NAME:
        return entity.legal_name
    if field_key == DocumentFieldKey.COUNTRY_OF_INCORPORATION:
        return entity.country_of_incorporation
    address = entity.registered_address
    if address is None:
        return None
    return ", ".join(
        part
        for part in (
            address.address_line_1,
            address.address_line_2,
            address.postal_code,
            address.country_code,
        )
        if part
    )


def validate_canonical_comparison_value(value: str | None) -> str | None:
    """Bound and sanitize canonical text before constructing retained review models."""

    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_RETAINED_FIELD_VALUE:
        raise DocumentComparisonInputError
    if any(category(character).startswith("C") for character in normalized):
        raise DocumentComparisonInputError
    return normalized


def normalize_document_value(field_key: DocumentFieldKey, value: str | None) -> str | None:
    if value is None:
        return None
    if field_key == DocumentFieldKey.REGISTRATION_NUMBER:
        normalized_uen = WHITESPACE.sub("", value.strip())
        return normalized_uen.upper() or None
    collapsed = WHITESPACE.sub(" ", value.strip())
    if not collapsed:
        return None
    if field_key in {
        DocumentFieldKey.LEGAL_NAME,
        DocumentFieldKey.REGISTERED_ADDRESS,
        DocumentFieldKey.COUNTRY_OF_INCORPORATION,
    }:
        return collapsed.upper()
    return collapsed


def compare_values(
    field_key: DocumentFieldKey,
    document_value: str | None,
    canonical_value: str | None,
) -> ComparisonStatus:
    normalized_document = normalize_document_value(field_key, document_value)
    normalized_canonical = normalize_document_value(field_key, canonical_value)
    if normalized_document is None and normalized_canonical is None:
        return ComparisonStatus.NOT_COMPARABLE
    if normalized_document is None:
        return ComparisonStatus.MISSING_FROM_DOCUMENT
    if normalized_canonical is None:
        return ComparisonStatus.MISSING_FROM_REGISTRY
    if normalized_document == normalized_canonical:
        return ComparisonStatus.MATCH
    return ComparisonStatus.MISMATCH


def _safe_optional_review_text(value: str | None, *, max_length: int = 240) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length or any(ord(character) < 32 for character in normalized):
        raise DocumentRequestError(
            code="DOCUMENT_REVIEW_TEXT_INVALID",
            message="Review text is invalid or exceeds the configured limit.",
        )
    return normalized
