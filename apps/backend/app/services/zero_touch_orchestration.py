"""Monotonic Phase 06 zero-touch coordinator over the accepted bounded services."""

import hmac
import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from app.connectors.idp import IdpProvider
from app.connectors.ownership import OwnershipProvider
from app.domain.clm import ClmStatus
from app.domain.documents import (
    DocumentAutoClearBlocker,
    DocumentProcessingRecord,
    DocumentProcessingState,
)
from app.domain.models import EventOutcome, SafeError, WorkflowState
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState
from app.domain.zero_touch import (
    AutomationEvent,
    AutomationEventType,
    AutomationMetrics,
    AutomationStage,
    AutomationStatus,
    BusinessException,
    BusinessExceptionStatus,
    BusinessExceptionType,
    ExceptionResolutionAction,
    SafeExceptionEvidence,
    ZeroTouchAutomationRecord,
)
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.document_errors import (
    DocumentProcessingInfrastructureError,
    DocumentRequestError,
)
from app.services.document_processing import DocumentProcessingService
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import OwnershipInfrastructureError, OwnershipRequestError
from app.services.zero_touch_errors import (
    ZeroTouchInfrastructureError,
    ZeroTouchRequestError,
)
from app.services.zero_touch_provider_bindings import (
    InMemoryOwnershipProviderBindingResolver,
    OwnershipProviderBindingResolver,
)
from app.services.zero_touch_repository import (
    ZeroTouchAutomationRepository,
    ZeroTouchRepositoryConflictError,
)


class ZeroTouchOrchestrator:
    """Advance deterministic stages and stop only at a safe explicit boundary."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        documents: DocumentProcessingService,
        ownership: OwnershipAnalysisService,
        clm: ClmOrchestrationService,
        repository: ZeroTouchAutomationRepository,
        ownership_provider_bindings: OwnershipProviderBindingResolver | None = None,
        max_transitions_per_run: int = 12,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        if not 1 <= max_transitions_per_run <= 32:
            raise ValueError("zero-touch transition bound must be between 1 and 32")
        self._cases = cases
        self._documents = documents
        self._ownership = ownership
        self._clm = clm
        self._repository = repository
        self._ownership_provider_bindings = ownership_provider_bindings or (
            InMemoryOwnershipProviderBindingResolver(lambda: ownership.configured_provider)
        )
        self._max_transitions = max_transitions_per_run
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    def create_case(self, uen: str) -> ZeroTouchAutomationRecord:
        """Create registry evidence and wait only for the required PDF input."""

        try:
            clm_record = self._clm.create_case(uen)
        except ClmInfrastructureError as exc:
            recovered_clm_record = self._clm.get(case_id=exc.case_id)
            if recovered_clm_record is None:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_CASE_CREATION_FAILED",
                    message="Onboarding could not be started safely.",
                ) from None
            clm_record = recovered_clm_record
            now = self._clock()
            record = ZeroTouchAutomationRecord(
                case_id=exc.case_id,
                automation_id=self._uuid_factory(),
                ownership_provider_binding_id=(
                    self._ownership_provider_bindings.default_binding_id
                ),
                status=AutomationStatus.TECHNICAL_FAILURE,
                current_stage=AutomationStage.REGISTRY,
                technical_failure=SafeError(code=exc.code, message=exc.public_message),
                metrics=AutomationMetrics(final_outcome=AutomationStatus.TECHNICAL_FAILURE.value),
                created_at=now,
                updated_at=now,
            )
            record = self._append_event(
                record,
                event_type=AutomationEventType.AUTOMATION_TECHNICAL_FAILURE,
                outcome=EventOutcome.FAILED,
                code=exc.code,
                message="Registry automation stopped after a technical failure.",
            )
            return self._create(record)

        case = self._cases.get_case(clm_record.case_id)
        if case is None:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_CASE_CREATION_FAILED",
                message="Onboarding could not be started safely.",
            )
        now = self._clock()
        registry_ready = case.state == WorkflowState.VALIDATED and case.entity is not None
        record = ZeroTouchAutomationRecord(
            case_id=case.case_id,
            automation_id=self._uuid_factory(),
            ownership_provider_binding_id=(self._ownership_provider_bindings.default_binding_id),
            status=(
                AutomationStatus.PENDING_INPUTS
                if registry_ready
                else AutomationStatus.WAITING_FOR_REVIEW
            ),
            current_stage=(
                AutomationStage.DOCUMENT if registry_ready else AutomationStage.REGISTRY
            ),
            completed_stages=(AutomationStage.REGISTRY,) if registry_ready else (),
            metrics=AutomationMetrics(automated_stages_completed=1 if registry_ready else 0),
            created_at=now,
            updated_at=now,
        )
        record = self._append_event(
            record,
            event_type=AutomationEventType.ONBOARDING_CREATED,
            outcome=EventOutcome.SUCCEEDED,
            code="ZERO_TOUCH_CASE_CREATED",
            message="Corporate onboarding case created.",
        )
        if registry_ready:
            record = self._append_event(
                record,
                event_type=AutomationEventType.REGISTRY_AUTOMATED,
                outcome=EventOutcome.SUCCEEDED,
                code="REGISTRY_AUTOMATED",
                message="Registry evidence was validated automatically.",
            )
        else:
            record = self._add_exception(
                record,
                exception_type=BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
                stage=AutomationStage.REGISTRY,
                blocker_code="REGISTRY_REVIEW_REQUIRED",
                explanation=(
                    "Registry evidence requires human review before automation can continue."
                ),
                evidence_version=f"case:{case.case_id}:{len(case.events)}",
                evidence=(),
                actions=(),
            )
        return self._create(record)

    def attach_document(
        self,
        *,
        case_id: UUID,
        display_name: str,
        content_type: str,
        content: bytes,
        idp_provider: IdpProvider | None = None,
        ownership_provider: OwnershipProvider | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Attach one PDF and automatically start every deterministic later stage."""

        with self._cases.case_lock(case_id):
            record = self._require_record(case_id)
            if record.status == AutomationStatus.TECHNICAL_FAILURE:
                return record
            if self._documents.list_documents(case_id=case_id):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_DOCUMENT_ALREADY_SUPPLIED",
                    message="The zero-touch case already has its initial document.",
                )
            try:
                self._documents.create_document(
                    case_id=case_id,
                    display_name=display_name,
                    content_type=content_type,
                    content=content,
                    provider=idp_provider,
                )
            except DocumentProcessingInfrastructureError as exc:
                failed = self._technical_failure(
                    record,
                    stage=AutomationStage.DOCUMENT,
                    code=exc.code,
                    message="Document processing stopped after a technical failure.",
                )
                raise ZeroTouchInfrastructureError(
                    case_id=failed.case_id,
                    automation_id=failed.automation_id,
                    code=exc.code,
                    message=exc.public_message,
                ) from None
            if ownership_provider is not None:
                binding_id = self._ownership_provider_bindings.register(
                    _constant_provider_factory(ownership_provider)
                )
                bound = record.model_copy(deep=True)
                bound.ownership_provider_binding_id = binding_id
                record = self._save(record, bound)
            if record.status == AutomationStatus.WAITING_FOR_REVIEW:
                return record
            started = record.model_copy(deep=True)
            started.status = AutomationStatus.RUNNING
            started.current_stage = AutomationStage.DOCUMENT
            started.started_at = started.started_at or self._clock()
            started = self._append_event(
                started,
                event_type=AutomationEventType.ONBOARDING_STARTED,
                outcome=EventOutcome.SUCCEEDED,
                code="ONBOARDING_STARTED",
                message="Required onboarding inputs were supplied; automation started.",
            )
            self._save(record, started)
            return self._advance_locked(case_id=case_id)

    def start(
        self, *, case_id: UUID, ownership_provider: OwnershipProvider | None = None
    ) -> ZeroTouchAutomationRecord:
        """Idempotently start or continue; normal upload already invokes this."""

        with self._cases.case_lock(case_id):
            record = self._require_record(case_id)
            if record.status in {
                AutomationStatus.COMPLETED,
                AutomationStatus.TECHNICAL_FAILURE,
                AutomationStatus.WAITING_FOR_REVIEW,
            }:
                return record
            if not self._documents.list_documents(case_id=case_id):
                return record
            if ownership_provider is not None:
                binding_id = self._ownership_provider_bindings.register(
                    _constant_provider_factory(ownership_provider)
                )
                candidate = record.model_copy(deep=True)
                candidate.ownership_provider_binding_id = binding_id
                record = self._save(record, candidate)
            if record.status == AutomationStatus.PENDING_INPUTS:
                candidate = record.model_copy(deep=True)
                candidate.status = AutomationStatus.RUNNING
                candidate.current_stage = AutomationStage.DOCUMENT
                candidate.started_at = candidate.started_at or self._clock()
                candidate = self._append_event(
                    candidate,
                    event_type=AutomationEventType.ONBOARDING_STARTED,
                    outcome=EventOutcome.SUCCEEDED,
                    code="ONBOARDING_STARTED",
                    message="Required onboarding inputs were supplied; automation started.",
                )
                self._save(record, candidate)
            return self._advance_locked(case_id=case_id)

    def get(self, *, case_id: UUID) -> ZeroTouchAutomationRecord | None:
        return self._repository.get_for_case(case_id)

    def resolve_exception(
        self,
        *,
        case_id: UUID,
        exception_id: UUID,
        action: ExceptionResolutionAction,
        expected_automation_version: int,
        evidence_version: str,
    ) -> ZeroTouchAutomationRecord:
        """Resolve current evidence once and automatically resume from the checkpoint."""

        with self._cases.case_lock(case_id):
            record = self._require_record(case_id)
            if record.version != expected_automation_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXCEPTION_STALE",
                    message="The onboarding case changed before this resolution.",
                )
            item = next(
                (
                    candidate
                    for candidate in record.exceptions
                    if candidate.exception_id == exception_id
                    and candidate.status == BusinessExceptionStatus.OPEN
                ),
                None,
            )
            if item is None or item.case_id != case_id:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXCEPTION_NOT_FOUND",
                    message="The active onboarding exception was not found.",
                )
            if item.evidence_version != evidence_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXCEPTION_STALE",
                    message="The onboarding evidence changed before this resolution.",
                )
            current_digest = self._authoritative_evidence_digest(
                case_id=case_id,
                exception_type=item.exception_type,
                evidence_version=item.evidence_version,
                blocker_codes=item.blocker_codes,
            )
            if not hmac.compare_digest(item.authoritative_evidence_digest, current_digest):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXCEPTION_STALE",
                    message="Authoritative onboarding evidence changed before this resolution.",
                )
            if action not in item.available_actions:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_RESOLUTION_NOT_ALLOWED",
                    message="This resolution is not allowed for the active exception.",
                )
            if item.stage != AutomationStage.DOCUMENT:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_EVIDENCE_REQUIRED",
                    message="Corrected replacement evidence is required for this exception.",
                )
            if item.exception_type != BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_RESOLUTION_NOT_ALLOWED",
                    message="This exception requires a distinct sponsor-confirmed review policy.",
                )
            document_id, event_count = _parse_document_evidence_version(evidence_version)
            try:
                self._documents.resolve_with_registry_values(
                    case_id=case_id,
                    document_id=document_id,
                    expected_event_count=event_count,
                )
            except DocumentRequestError as exc:
                code = (
                    "ZERO_TOUCH_EXCEPTION_STALE"
                    if exc.code == "DOCUMENT_REVIEW_STALE"
                    else exc.code
                )
                raise ZeroTouchRequestError(code=code, message=exc.public_message) from None

            candidate = record.model_copy(deep=True)
            resolved = next(
                entry for entry in candidate.exceptions if entry.exception_id == exception_id
            )
            resolved.status = BusinessExceptionStatus.RESOLVED
            resolved.resolved_at = self._clock()
            resolved.resolution = action
            for other in candidate.active_exceptions:
                if other.exception_id != exception_id:
                    other.status = BusinessExceptionStatus.CANCELLED
            candidate.status = AutomationStatus.RESUMING
            candidate.current_stage = AutomationStage.DOCUMENT
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += 1
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.BUSINESS_EXCEPTION_RESOLVED,
                outcome=EventOutcome.SUCCEEDED,
                code=action.value,
                message="Human review exception was resolved; onboarding will resume.",
            )
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.AUTOMATION_RESUMING,
                outcome=EventOutcome.SUCCEEDED,
                code="AUTOMATION_RESUMING",
                message="Deterministic onboarding stages are resuming automatically.",
            )
            self._save(record, candidate)
            return self._advance_locked(case_id=case_id)

    def _advance_locked(self, *, case_id: UUID) -> ZeroTouchAutomationRecord:
        try:
            return self._advance_locked_impl(case_id=case_id)
        except (ZeroTouchRequestError, ZeroTouchInfrastructureError):
            raise
        except Exception:
            latest = self._require_record(case_id)
            failed = self._persist_unexpected_failure(latest)
            raise ZeroTouchInfrastructureError(
                case_id=failed.case_id,
                automation_id=failed.automation_id,
                code="ZERO_TOUCH_UNEXPECTED_FAILURE",
                message="Onboarding automation stopped after an unexpected technical failure.",
            ) from None

    def _advance_locked_impl(self, *, case_id: UUID) -> ZeroTouchAutomationRecord:
        record = self._require_record(case_id)
        if record.active_exceptions:
            return record
        if record.status in {
            AutomationStatus.COMPLETED,
            AutomationStatus.TECHNICAL_FAILURE,
        }:
            return record

        finalization_recovery_attempts = 0
        for _ in range(self._max_transitions):
            record = self._require_record(case_id)
            if record.active_exceptions:
                return record
            next_stage = _next_stage(record.completed_stages)
            if next_stage == AutomationStage.DOCUMENT:
                documents = self._documents.list_documents(case_id=case_id)
                if not documents:
                    candidate = record.model_copy(deep=True)
                    candidate.status = AutomationStatus.PENDING_INPUTS
                    candidate.current_stage = AutomationStage.DOCUMENT
                    return self._save(record, candidate)
                failed_document = next(
                    (
                        document
                        for document in documents
                        if document.state == DocumentProcessingState.FAILED
                    ),
                    None,
                )
                if failed_document is not None:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.DOCUMENT,
                        code=(
                            failed_document.error.code
                            if failed_document.error
                            else "DOCUMENT_PROCESSING_FAILED"
                        ),
                        message="Document processing stopped after a technical failure.",
                    )
                for document in documents:
                    if document.state != DocumentProcessingState.REVIEW_REQUIRED:
                        continue
                    assessment = self._documents.assess_auto_clear(
                        case_id=case_id, document_id=document.document_id
                    )
                    if assessment.eligible:
                        self._documents.auto_confirm_document(
                            case_id=case_id, document_id=document.document_id
                        )
                documents = self._documents.list_documents(case_id=case_id)
                blocked_documents: list[
                    tuple[DocumentProcessingRecord, tuple[DocumentAutoClearBlocker, ...]]
                ] = []
                for document in documents:
                    if document.state not in {
                        DocumentProcessingState.REVIEW_REQUIRED,
                        DocumentProcessingState.REVIEWED,
                    }:
                        continue
                    assessment = self._documents.assess_auto_clear(
                        case_id=case_id, document_id=document.document_id
                    )
                    if not assessment.eligible:
                        blocked_documents.append((document, assessment.blockers))
                if blocked_documents:
                    for document, blockers in blocked_documents:
                        record = self._raise_document_exception(record, document, blockers)
                    return record
                if all(
                    document.state == DocumentProcessingState.REVIEWED for document in documents
                ):
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.DOCUMENT,
                        event_type=(
                            AutomationEventType.DOCUMENT_EXCEPTION_RESOLVED
                            if record.status == AutomationStatus.RESUMING
                            else AutomationEventType.DOCUMENT_AUTO_CONFIRMED
                        ),
                        code="DOCUMENT_CHECKPOINT_COMPLETE",
                        message="All document evidence checkpoints are complete.",
                        started_at=self._clock(),
                    )
                    continue
                return self._technical_failure(
                    record,
                    stage=AutomationStage.DOCUMENT,
                    code="AUTOMATION_NO_PROGRESS",
                    message="Document automation made no safe progress.",
                )

            if next_stage == AutomationStage.OWNERSHIP:
                started_at = self._clock()
                try:
                    ownership = self._ownership.get(case_id=case_id)
                    if ownership is None:
                        provider = self._ownership_provider_bindings.resolve(
                            record.ownership_provider_binding_id
                        )
                        if provider is None:
                            return self._technical_failure(
                                record,
                                stage=AutomationStage.OWNERSHIP,
                                code="OWNERSHIP_PROVIDER_BINDING_UNAVAILABLE",
                                message="The configured ownership provider is unavailable.",
                            )
                        ownership = self._ownership.load(case_id=case_id, provider=provider)
                    if ownership.state == OwnershipAnalysisState.LOADED:
                        ownership = self._ownership.analyze(case_id=case_id)
                except OwnershipInfrastructureError as exc:
                    failed = self._technical_failure(
                        record,
                        stage=AutomationStage.OWNERSHIP,
                        code=exc.code,
                        message="Ownership processing stopped after a technical failure.",
                    )
                    raise ZeroTouchInfrastructureError(
                        case_id=failed.case_id,
                        automation_id=failed.automation_id,
                        code=exc.code,
                        message=exc.public_message,
                    ) from None
                except OwnershipRequestError as exc:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.OWNERSHIP,
                        code=exc.code,
                        message="Ownership processing could not progress safely.",
                    )
                if ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED:
                    return self._raise_ownership_exception(record, ownership)
                if ownership.state == OwnershipAnalysisState.FAILED:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.OWNERSHIP,
                        code=(ownership.error.code if ownership.error else "OWNERSHIP_FAILED"),
                        message="Ownership processing stopped after a technical failure.",
                    )
                if ownership.state == OwnershipAnalysisState.ANALYZED:
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.OWNERSHIP,
                        event_type=AutomationEventType.OWNERSHIP_AUTOMATED,
                        code="OWNERSHIP_AUTOMATED",
                        message="Deterministic ownership analysis completed automatically.",
                        started_at=started_at,
                    )
                    continue
                return self._technical_failure(
                    record,
                    stage=AutomationStage.OWNERSHIP,
                    code="AUTOMATION_NO_PROGRESS",
                    message="Ownership automation made no safe progress.",
                )

            if next_stage == AutomationStage.READINESS:
                started_at = self._clock()
                try:
                    clm_record = self._clm.evaluate(case_id=case_id)
                except ClmRequestError as exc:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.READINESS,
                        code=exc.code,
                        message="Readiness evaluation could not progress safely.",
                    )
                if clm_record.status != ClmStatus.READY_FOR_MOCK_SUBMISSION:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.READINESS,
                        code="AUTOMATION_READINESS_INCONSISTENT",
                        message="Authoritative readiness changed before automatic submission.",
                    )
                record = self._complete_stage(
                    record,
                    stage=AutomationStage.READINESS,
                    event_type=AutomationEventType.READINESS_AUTOMATED,
                    code="READINESS_AUTOMATED",
                    message="Authoritative Mock submission readiness was evaluated automatically.",
                    started_at=started_at,
                )
                continue

            if next_stage == AutomationStage.MOCK_GOLDTIER:
                started_at = self._clock()
                if not any(
                    event.event_type == AutomationEventType.MOCK_SUBMISSION_STARTED
                    for event in record.events
                ):
                    candidate = record.model_copy(deep=True)
                    candidate.status = AutomationStatus.RUNNING
                    candidate.current_stage = AutomationStage.MOCK_GOLDTIER
                    candidate = self._append_event(
                        candidate,
                        event_type=AutomationEventType.MOCK_SUBMISSION_STARTED,
                        outcome=EventOutcome.SUCCEEDED,
                        code="MOCK_SUBMISSION_STARTED",
                        message="Automatic Mock GoldTier submission started.",
                    )
                    record = self._save(record, candidate)
                try:
                    clm_record = self._clm.submit(case_id=case_id)
                except ClmInfrastructureError as exc:
                    if exc.code == "CLM_FINALIZATION_RETRY_REQUIRED":
                        finalization_recovery_attempts += 1
                        if finalization_recovery_attempts < 2:
                            continue
                        if record.status == AutomationStatus.RECOVERY_PENDING:
                            return record
                        candidate = record.model_copy(deep=True)
                        candidate.status = AutomationStatus.RECOVERY_PENDING
                        candidate.current_stage = AutomationStage.MOCK_GOLDTIER
                        candidate = self._append_event(
                            candidate,
                            event_type=(
                                AutomationEventType.MOCK_FINALIZATION_RECOVERY_PENDING
                            ),
                            outcome=EventOutcome.PARTIAL,
                            code="CLM_FINALIZATION_RETRY_REQUIRED",
                            message=(
                                "Mock submission outcome is retained; finalization recovery "
                                "will resume without replaying target operations."
                            ),
                        )
                        return self._save(record, candidate)
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.MOCK_GOLDTIER,
                        code=exc.code,
                        message="Mock GoldTier processing stopped after a technical failure.",
                    )
                except ClmRequestError as exc:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.MOCK_GOLDTIER,
                        code=exc.code,
                        message="Mock GoldTier processing could not progress safely.",
                    )
                if clm_record.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED:
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.MOCK_GOLDTIER,
                        event_type=AutomationEventType.MOCK_SUBMISSION_COMPLETED,
                        code="MOCK_GOLDTIER_SUBMITTED",
                        message="Mock GoldTier submission completed automatically.",
                        started_at=started_at,
                    )
                    candidate = record.model_copy(deep=True)
                    candidate.status = AutomationStatus.COMPLETED
                    candidate.current_stage = AutomationStage.COMPLETE
                    candidate.completed_at = self._clock()
                    candidate.metrics.final_outcome = "MOCK_GOLDTIER_SUBMITTED"
                    if candidate.started_at is not None:
                        candidate.metrics.total_duration_ms = _duration_ms(
                            candidate.started_at, candidate.completed_at
                        )
                    return self._save(record, candidate)
                if clm_record.status == ClmStatus.REVIEW_REQUIRED:
                    return self._raise_target_exception(record, clm_record.error)
                return self._technical_failure(
                    record,
                    stage=AutomationStage.MOCK_GOLDTIER,
                    code=(clm_record.error.code if clm_record.error else "CLM_SUBMISSION_FAILED"),
                    message="Mock GoldTier processing stopped after a technical failure.",
                )

            if next_stage == AutomationStage.COMPLETE:
                return record

        return self._technical_failure(
            self._require_record(case_id),
            stage=self._require_record(case_id).current_stage,
            code="AUTOMATION_LOOP_GUARD",
            message="Automation stopped at the configured progression bound.",
        )

    def _raise_document_exception(
        self,
        record: ZeroTouchAutomationRecord,
        document: DocumentProcessingRecord,
        blockers: tuple[DocumentAutoClearBlocker, ...],
    ) -> ZeroTouchAutomationRecord:
        if DocumentAutoClearBlocker.SOURCE_CONFLICT in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT
            code = "DOCUMENT_SOURCE_CONFLICT"
            explanation = "Document evidence conflicts with current registry evidence."
        elif DocumentAutoClearBlocker.REQUIRED_FIELD_MISSING in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING
            code = "DOCUMENT_REQUIRED_FIELD_MISSING"
            explanation = "A required document field is missing and requires human review."
        elif DocumentAutoClearBlocker.LOW_CONFIDENCE in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE
            code = "DOCUMENT_LOW_CONFIDENCE"
            explanation = "Document confidence is below the provisional automated threshold."
        else:
            exception_type = BusinessExceptionType.DOCUMENT_REVIEW_REQUIRED
            code = "DOCUMENT_REVIEW_REQUIRED"
            explanation = "Document evidence requires human review."
        evidence = tuple(
            SafeExceptionEvidence(
                reference_id=document.document_id,
                field_key=field.field_key.value,
                registry_value=field.canonical_value,
                document_value=field.original_extracted_value,
                confidence=field.confidence,
                comparison=field.comparison_status.value,
            )
            for field in document.fields
            if (
                field.original_extracted_value is None
                or field.confidence < self._documents.review_confidence_threshold
                or field.comparison_status.value != "MATCH"
            )
        )[:4]
        return self._add_exception(
            record,
            exception_type=exception_type,
            stage=AutomationStage.DOCUMENT,
            blocker_code=code,
            explanation=explanation,
            evidence_version=_document_evidence_version(document),
            evidence=evidence,
            actions=(
                (ExceptionResolutionAction.KEEP_REGISTRY_VALUE,)
                if DocumentAutoClearBlocker.SOURCE_CONFLICT in blockers
                else ()
            ),
            blocker_codes=tuple(blocker.value for blocker in blockers),
        )

    def _raise_ownership_exception(
        self, record: ZeroTouchAutomationRecord, ownership: OwnershipAnalysisRecord
    ) -> ZeroTouchAutomationRecord:
        issue_codes = {item.code.value for item in ownership.issues}
        if "CYCLE_DETECTED" in issue_codes:
            exception_type = BusinessExceptionType.OWNERSHIP_CYCLE
            code = "OWNERSHIP_CYCLE"
            explanation = (
                "A cycle makes the ownership result indeterminate. Corrected evidence is required."
            )
        elif "INCOMPLETE_LEGAL_ENTITY" in issue_codes:
            exception_type = BusinessExceptionType.OWNERSHIP_INCOMPLETE
            code = "OWNERSHIP_INCOMPLETE"
            explanation = (
                "The legal-entity ownership chain is incomplete. Corrected evidence is required."
            )
        else:
            exception_type = BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED
            code = "OWNERSHIP_REVIEW_REQUIRED"
            explanation = "Ownership evidence is not definitive and requires replacement or review."
        return self._add_exception(
            record,
            exception_type=exception_type,
            stage=AutomationStage.OWNERSHIP,
            blocker_code=code,
            explanation=explanation,
            evidence_version=f"ownership:{ownership.analysis_id}:{ownership.version}",
            evidence=(),
            actions=(),
        )

    def _raise_target_exception(
        self, record: ZeroTouchAutomationRecord, error: SafeError | None
    ) -> ZeroTouchAutomationRecord:
        code = error.code if error is not None else "TARGET_REVIEW_REQUIRED"
        if code == "GT_EXISTING_PARTY_REVIEW_REQUIRED":
            exception_type = BusinessExceptionType.EXISTING_PARTY_REVIEW_REQUIRED
            explanation = (
                "An existing Mock GoldTier party was found; duplicate creation was stopped."
            )
        else:
            exception_type = BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED
            explanation = "Mock target processing returned a partial or review outcome."
        clm_record = self._clm.get(case_id=record.case_id)
        version = clm_record.version if clm_record is not None else 0
        return self._add_exception(
            record,
            exception_type=exception_type,
            stage=AutomationStage.MOCK_GOLDTIER,
            blocker_code=code,
            explanation=explanation,
            evidence_version=f"target:{record.case_id}:{version}",
            evidence=(),
            actions=(),
        )

    def _add_exception(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        exception_type: BusinessExceptionType,
        stage: AutomationStage,
        blocker_code: str,
        explanation: str,
        evidence_version: str,
        evidence: tuple[SafeExceptionEvidence, ...],
        actions: tuple[ExceptionResolutionAction, ...],
        blocker_codes: tuple[str, ...] | None = None,
    ) -> ZeroTouchAutomationRecord:
        for existing in record.active_exceptions:
            if (
                existing.exception_type == exception_type
                and existing.evidence_version == evidence_version
            ):
                return record
        candidate = record.model_copy(deep=True)
        candidate.status = AutomationStatus.WAITING_FOR_REVIEW
        candidate.current_stage = stage
        candidate.exceptions.append(
            BusinessException(
                exception_id=self._uuid_factory(),
                case_id=record.case_id,
                exception_type=exception_type,
                stage=stage,
                blocker_code=blocker_code,
                blocker_codes=blocker_codes or (blocker_code,),
                explanation=explanation,
                evidence_version=evidence_version,
                authoritative_evidence_digest=self._authoritative_evidence_digest(
                    case_id=record.case_id,
                    exception_type=exception_type,
                    evidence_version=evidence_version,
                    blocker_codes=blocker_codes or (blocker_code,),
                ),
                automation_version=record.version + 1,
                evidence=evidence,
                available_actions=actions,
                created_at=self._clock(),
            )
        )
        candidate.metrics.exceptions_raised += 1
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.BUSINESS_EXCEPTION_RAISED,
            outcome=EventOutcome.REVIEW_REQUIRED,
            code=blocker_code,
            message="Automation paused at a typed human-review exception.",
        )
        return self._save(record, candidate) if record.version else candidate

    def _complete_stage(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        stage: AutomationStage,
        event_type: AutomationEventType,
        code: str,
        message: str,
        started_at: datetime,
    ) -> ZeroTouchAutomationRecord:
        if stage in record.completed_stages:
            return record
        candidate = record.model_copy(deep=True)
        candidate.status = AutomationStatus.RUNNING
        candidate.current_stage = _stage_after(stage)
        candidate.completed_stages = (*candidate.completed_stages, stage)
        candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
        candidate.metrics.stage_durations_ms[stage] = _duration_ms(started_at, self._clock())
        candidate = self._append_event(
            candidate,
            event_type=event_type,
            outcome=EventOutcome.SUCCEEDED,
            code=code,
            message=message,
        )
        return self._save(record, candidate)

    def _technical_failure(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        stage: AutomationStage,
        code: str,
        message: str,
    ) -> ZeroTouchAutomationRecord:
        if record.status == AutomationStatus.TECHNICAL_FAILURE:
            return record
        candidate = record.model_copy(deep=True)
        candidate.status = AutomationStatus.TECHNICAL_FAILURE
        candidate.current_stage = stage
        for item in candidate.active_exceptions:
            item.status = BusinessExceptionStatus.CANCELLED
        candidate.technical_failure = SafeError(code=code, message=message)
        candidate.metrics.final_outcome = AutomationStatus.TECHNICAL_FAILURE.value
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_TECHNICAL_FAILURE,
            outcome=EventOutcome.FAILED,
            code=code,
            message=message,
        )
        return self._save(record, candidate)

    def _persist_unexpected_failure(
        self, record: ZeroTouchAutomationRecord
    ) -> ZeroTouchAutomationRecord:
        """Terminalize an untyped fault without retaining exception detail."""

        if record.status == AutomationStatus.TECHNICAL_FAILURE:
            return record
        now = datetime.now(UTC)
        candidate = record.model_copy(deep=True)
        candidate.status = AutomationStatus.TECHNICAL_FAILURE
        for item in candidate.active_exceptions:
            item.status = BusinessExceptionStatus.CANCELLED
        candidate.technical_failure = SafeError(
            code="ZERO_TOUCH_UNEXPECTED_FAILURE",
            message="Onboarding automation stopped after an unexpected technical failure.",
        )
        candidate.metrics.final_outcome = AutomationStatus.TECHNICAL_FAILURE.value
        candidate.updated_at = now
        candidate.events.append(
            AutomationEvent(
                sequence=len(candidate.events) + 1,
                event_type=AutomationEventType.AUTOMATION_TECHNICAL_FAILURE,
                status=AutomationStatus.TECHNICAL_FAILURE,
                stage=candidate.current_stage,
                outcome=EventOutcome.FAILED,
                timestamp=now,
                case_id=candidate.case_id,
                code="ZERO_TOUCH_UNEXPECTED_FAILURE",
                message="Onboarding automation stopped after an unexpected technical failure.",
            )
        )
        return self._save(record, candidate)

    def _authoritative_evidence_digest(
        self,
        *,
        case_id: UUID,
        exception_type: BusinessExceptionType,
        evidence_version: str,
        blocker_codes: tuple[str, ...],
    ) -> str:
        """Fingerprint every server-owned input that can authorize progression."""

        case = self._cases.get_case(case_id)
        documents = sorted(
            self._documents.list_documents(case_id=case_id),
            key=lambda item: str(item.document_id),
        )
        payload = {
            "domain": "zero-touch-authoritative-evidence-v1",
            "case": case.model_dump(mode="json") if case is not None else None,
            "documents": [item.model_dump(mode="json") for item in documents],
            "exception_type": exception_type.value,
            "evidence_version": evidence_version,
            "blocker_codes": blocker_codes,
        }
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return sha256(canonical).hexdigest()

    def _append_event(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        event_type: AutomationEventType,
        outcome: EventOutcome,
        code: str | None,
        message: str,
    ) -> ZeroTouchAutomationRecord:
        candidate = record.model_copy(deep=True)
        now = self._clock()
        candidate.updated_at = now
        candidate.events.append(
            AutomationEvent(
                sequence=len(candidate.events) + 1,
                event_type=event_type,
                status=candidate.status,
                stage=candidate.current_stage,
                outcome=outcome,
                timestamp=now,
                case_id=candidate.case_id,
                code=code,
                message=message,
            )
        )
        return candidate

    def _create(self, record: ZeroTouchAutomationRecord) -> ZeroTouchAutomationRecord:
        try:
            return self._repository.save(record, expected_version=None)
        except ZeroTouchRepositoryConflictError:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_CASE_ALREADY_EXISTS",
                message="A zero-touch automation record already exists for this case.",
            ) from None

    def _save(
        self, previous: ZeroTouchAutomationRecord, candidate: ZeroTouchAutomationRecord
    ) -> ZeroTouchAutomationRecord:
        try:
            return self._repository.save(candidate, expected_version=previous.version)
        except ZeroTouchRepositoryConflictError:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_AUTOMATION_CONFLICT",
                message="The onboarding automation changed during this operation.",
            ) from None

    def _require_record(self, case_id: UUID) -> ZeroTouchAutomationRecord:
        record = self._repository.get_for_case(case_id)
        if record is None:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_CASE_NOT_FOUND",
                message="The zero-touch onboarding case was not found.",
            )
        return record


def _next_stage(completed: tuple[AutomationStage, ...]) -> AutomationStage:
    for stage in (
        AutomationStage.REGISTRY,
        AutomationStage.DOCUMENT,
        AutomationStage.OWNERSHIP,
        AutomationStage.READINESS,
        AutomationStage.MOCK_GOLDTIER,
    ):
        if stage not in completed:
            return stage
    return AutomationStage.COMPLETE


def _stage_after(stage: AutomationStage) -> AutomationStage:
    stages = {
        AutomationStage.REGISTRY: AutomationStage.DOCUMENT,
        AutomationStage.DOCUMENT: AutomationStage.OWNERSHIP,
        AutomationStage.OWNERSHIP: AutomationStage.READINESS,
        AutomationStage.READINESS: AutomationStage.MOCK_GOLDTIER,
        AutomationStage.MOCK_GOLDTIER: AutomationStage.COMPLETE,
        AutomationStage.COMPLETE: AutomationStage.COMPLETE,
    }
    return stages[stage]


def _document_evidence_version(document: DocumentProcessingRecord) -> str:
    return f"document:{document.document_id}:{len(document.events)}"


def _parse_document_evidence_version(value: str) -> tuple[UUID, int]:
    try:
        prefix, raw_id, raw_count = value.split(":", maxsplit=2)
        if prefix != "document":
            raise ValueError
        return UUID(raw_id), int(raw_count)
    except (ValueError, TypeError):
        raise ZeroTouchRequestError(
            code="ZERO_TOUCH_EXCEPTION_STALE",
            message="The onboarding evidence version is invalid.",
        ) from None


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _constant_provider_factory(
    provider: OwnershipProvider,
) -> Callable[[], OwnershipProvider]:
    def factory() -> OwnershipProvider:
        return provider

    return factory
