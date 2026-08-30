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
from app.domain.reconciliation import (
    ReconciliationCaseRecord,
    ReconciliationDecisionAction,
    ReconciliationDiscrepancy,
    ReconciliationOutcome,
    ReconciliationSourceKind,
    ReconciliationStatus,
)
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
from app.services.reconciliation import ReconciliationService
from app.services.reconciliation_errors import (
    ReconciliationInfrastructureError,
    ReconciliationRequestError,
)
from app.services.reconciliation_repository import InMemoryReconciliationRepository
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
        reconciliation: ReconciliationService | None = None,
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
        self._reconciliation = reconciliation or ReconciliationService(
            cases=cases,
            documents=documents,
            repository=InMemoryReconciliationRepository(),
        )
        if getattr(clm, "_reconciliation", None) is None:
            clm._reconciliation = self._reconciliation  # noqa: SLF001
        self._repository = repository
        self._ownership_provider_bindings = ownership_provider_bindings or (
            InMemoryOwnershipProviderBindingResolver(lambda: ownership.configured_provider)
        )
        self._max_transitions = max_transitions_per_run
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    def create_case(
        self, uen: str, country_of_incorporation: str | None = None
    ) -> ZeroTouchAutomationRecord:
        """Create registry evidence and wait only for the required PDF input."""

        try:
            clm_record = self._clm.create_case(uen, country_of_incorporation)
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
        registry_failed = case.state == WorkflowState.FAILED
        record = ZeroTouchAutomationRecord(
            case_id=case.case_id,
            automation_id=self._uuid_factory(),
            ownership_provider_binding_id=(self._ownership_provider_bindings.default_binding_id),
            status=(
                AutomationStatus.PENDING_INPUTS
                if registry_ready
                else (
                    AutomationStatus.TECHNICAL_FAILURE
                    if registry_failed
                    else AutomationStatus.WAITING_FOR_REVIEW
                )
            ),
            current_stage=(
                AutomationStage.DOCUMENT if registry_ready else AutomationStage.REGISTRY
            ),
            completed_stages=(AutomationStage.REGISTRY,) if registry_ready else (),
            technical_failure=(case.error if registry_failed else None),
            metrics=AutomationMetrics(
                automated_stages_completed=1 if registry_ready else 0,
                final_outcome=(
                    AutomationStatus.TECHNICAL_FAILURE.value
                    if registry_failed
                    else None
                ),
            ),
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
        elif registry_failed:
            record = self._append_event(
                record,
                event_type=AutomationEventType.AUTOMATION_TECHNICAL_FAILURE,
                outcome=EventOutcome.FAILED,
                code=(case.error.code if case.error is not None else "REGISTRY_FAILED"),
                message="Registry automation stopped after a technical failure.",
            )
        else:
            blocker_code = (
                case.error.code if case.error is not None else "REGISTRY_REVIEW_REQUIRED"
            )
            exception_types = {
                "JURISDICTION_UNRESOLVED": BusinessExceptionType.JURISDICTION_UNRESOLVED,
                "JURISDICTION_CONFLICT": BusinessExceptionType.JURISDICTION_CONFLICT,
                "REGISTRY_PROVIDER_NOT_IMPLEMENTED": (
                    BusinessExceptionType.REGISTRY_PROVIDER_NOT_IMPLEMENTED
                ),
                "REGISTRY_IDENTIFIER_NOT_ELIGIBLE": (
                    BusinessExceptionType.REGISTRY_IDENTIFIER_NOT_ELIGIBLE
                ),
            }
            explanations = {
                "JURISDICTION_UNRESOLVED": (
                    "Jurisdiction must be resolved before a registry provider can be selected."
                ),
                "JURISDICTION_CONFLICT": (
                    "Conflicting jurisdiction evidence must be reviewed before registry retrieval."
                ),
                "REGISTRY_PROVIDER_NOT_IMPLEMENTED": (
                    "The resolved jurisdiction is recognised, but its registry provider "
                    "is not implemented."
                ),
                "REGISTRY_IDENTIFIER_NOT_ELIGIBLE": (
                    "The supplied identifier is not eligible for Singapore ACRA retrieval."
                ),
                "REGISTRY_EXPECTED_DATA_MISSING": (
                    "Expected registry ownership evidence was not returned, so "
                    "automation cannot continue without review."
                ),
            }
            evidence = tuple(
                SafeExceptionEvidence(
                    field_key="country_of_incorporation",
                    source=observation.source.value,
                    observed_value=observation.jurisdiction.value,
                    observed_at=observation.observed_at,
                    evidence_reference=observation.source_reference,
                )
                for observation in (
                    case.jurisdiction_resolution.observations
                    if case.jurisdiction_resolution is not None
                    else ()
                )[:4]
            )
            record = self._add_exception(
                record,
                exception_type=exception_types.get(
                    blocker_code, BusinessExceptionType.REGISTRY_REVIEW_REQUIRED
                ),
                stage=AutomationStage.REGISTRY,
                blocker_code=blocker_code,
                explanation=explanations.get(
                    blocker_code,
                    "Registry evidence requires human review before automation can continue.",
                ),
                evidence_version=f"case:{case.case_id}:{len(case.events)}",
                evidence=evidence,
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
            if (
                record.status == AutomationStatus.WAITING_FOR_REVIEW
                and record.current_stage == AutomationStage.REGISTRY
            ):
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

    def intake_document(
        self,
        *,
        case_id: UUID,
        display_name: str,
        content_type: str,
        content: bytes,
        idp_provider: IdpProvider | None = None,
    ) -> DocumentProcessingRecord:
        """Process one intake document without starting reconciliation or later stages."""

        with self._cases.case_lock(case_id):
            record = self._require_record(case_id)
            if record.status != AutomationStatus.PENDING_INPUTS:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_NOT_OPEN",
                    message="Document intake is not open for this case.",
                )
            return self._documents.create_document(
                case_id=case_id,
                display_name=display_name,
                content_type=content_type,
                content=content,
                provider=idp_provider,
            )

    def retry_intake_document(
        self,
        *,
        case_id: UUID,
        failed_document_id: UUID,
        display_name: str,
        content_type: str,
        content: bytes,
        idp_provider: IdpProvider | None = None,
    ) -> DocumentProcessingRecord:
        """Explicitly supersede one failed intake record without creating a new case."""

        with self._cases.case_lock(case_id):
            automation = self._require_record(case_id)
            if automation.status != AutomationStatus.PENDING_INPUTS:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_NOT_OPEN",
                    message="Document intake is not open for this case.",
                )
            failed = self._documents.get_document(
                case_id=case_id, document_id=failed_document_id
            )
            if (
                failed is None
                or failed.state != DocumentProcessingState.FAILED
                or not failed.is_current_evidence
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_RETRY_INVALID",
                    message="The failed intake document is no longer retryable.",
                )
            return self._documents.replace_document(
                case_id=case_id,
                document_id=failed.document_id,
                expected_event_count=len(failed.events),
                display_name=display_name,
                content_type=content_type,
                content=content,
                provider=idp_provider,
            )

    def start(
        self,
        *,
        case_id: UUID,
        ownership_provider: OwnershipProvider | None = None,
        expected_document_count: int | None = None,
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
            current_documents = [
                item
                for item in self._documents.list_documents(case_id=case_id)
                if item.is_current_evidence
            ]
            if not current_documents:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_DOCUMENTS_REQUIRED",
                    message="At least one valid supporting document is required.",
                )
            if (
                expected_document_count is not None
                and len(current_documents) != expected_document_count
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_INCOMPLETE",
                    message="The complete intended document set has not been received.",
                )
            if any(item.state == DocumentProcessingState.FAILED for item in current_documents):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_INCOMPLETE",
                    message="A failed document must be replaced before intake can complete.",
                )
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

    def replace_document(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        expected_document_event_count: int,
        display_name: str,
        content_type: str,
        content: bytes,
        idp_provider: IdpProvider | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Supersede blocked document evidence and automatically re-evaluate it."""

        with self._cases.case_lock(case_id):
            record = self._require_record(case_id)
            if record.status in {AutomationStatus.COMPLETED, AutomationStatus.TECHNICAL_FAILURE}:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_NOT_ALLOWED",
                    message="Replacement evidence is not accepted after a terminal outcome.",
                )
            if (
                record.status != AutomationStatus.WAITING_FOR_REVIEW
                or record.current_stage != AutomationStage.DOCUMENT
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_NOT_ALLOWED",
                    message="Replacement evidence is only accepted for the active document review.",
                )
            self._documents.replace_document(
                case_id=case_id,
                document_id=document_id,
                expected_event_count=expected_document_event_count,
                display_name=display_name,
                content_type=content_type,
                content=content,
                provider=idp_provider,
            )
            candidate = record.model_copy(deep=True)
            for exception in candidate.active_exceptions:
                if exception.stage == AutomationStage.DOCUMENT:
                    exception.status = BusinessExceptionStatus.CANCELLED
            candidate.status = AutomationStatus.RESUMING
            candidate.current_stage = AutomationStage.DOCUMENT
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += 1
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.AUTOMATION_RESUMING,
                outcome=EventOutcome.SUCCEEDED,
                code="DOCUMENT_REPLACEMENT_ACCEPTED",
                message="Replacement document evidence was accepted; onboarding is re-evaluating.",
            )
            self._save(record, candidate)
            return self._advance_locked(case_id=case_id)

    def get(self, *, case_id: UUID) -> ZeroTouchAutomationRecord | None:
        return self._repository.get_for_case(case_id)

    def list_cases(
        self, *, status: AutomationStatus | None = None
    ) -> list[ZeroTouchAutomationRecord]:
        """Read the process-local case index without invoking any provider or workflow."""

        records = self._repository.list_records()
        return [item for item in records if status is None or item.status == status]

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
            if item.evidence_version.startswith("reconciliation:"):
                reconciliation_version, fingerprint = (
                    _parse_reconciliation_evidence_version(item.evidence_version)
                )
                try:
                    reconciliation_action = ReconciliationDecisionAction(action.value)
                except ValueError:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_RESOLUTION_NOT_ALLOWED",
                        message="This resolution is not allowed for the active discrepancy.",
                    ) from None
                return self._resolve_reconciliation_locked(
                    record=record,
                    discrepancy_id=item.exception_id,
                    action=reconciliation_action,
                    expected_reconciliation_version=reconciliation_version,
                    evidence_fingerprint=fingerprint,
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

    def resolve_reconciliation_discrepancy(
        self,
        *,
        case_id: UUID,
        discrepancy_id: UUID,
        action: ReconciliationDecisionAction,
        expected_automation_version: int,
        expected_reconciliation_version: int,
        evidence_fingerprint: str,
    ) -> ZeroTouchAutomationRecord:
        """Resolve one case-bound discrepancy through the typed backend authority."""

        with self._cases.case_lock(case_id):
            record = self._require_record(case_id)
            if record.version != expected_automation_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXCEPTION_STALE",
                    message="The onboarding case changed before this resolution.",
                )
            return self._resolve_reconciliation_locked(
                record=record,
                discrepancy_id=discrepancy_id,
                action=action,
                expected_reconciliation_version=expected_reconciliation_version,
                evidence_fingerprint=evidence_fingerprint,
            )

    def _resolve_reconciliation_locked(
        self,
        *,
        record: ZeroTouchAutomationRecord,
        discrepancy_id: UUID,
        action: ReconciliationDecisionAction,
        expected_reconciliation_version: int,
        evidence_fingerprint: str,
    ) -> ZeroTouchAutomationRecord:
        item = next(
            (
                candidate
                for candidate in record.active_exceptions
                if candidate.exception_id == discrepancy_id
            ),
            None,
        )
        if item is None or item.case_id != record.case_id:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_EXCEPTION_NOT_FOUND",
                message="The active reconciliation discrepancy was not found.",
            )
        try:
            reconciliation = self._reconciliation.resolve_discrepancy(
                case_id=record.case_id,
                discrepancy_id=discrepancy_id,
                action=action,
                expected_version=expected_reconciliation_version,
                evidence_fingerprint=evidence_fingerprint,
            )
        except ReconciliationRequestError as exc:
            code = (
                "ZERO_TOUCH_EXCEPTION_STALE"
                if exc.code == "RECONCILIATION_STALE"
                else "ZERO_TOUCH_RESOLUTION_NOT_ALLOWED"
                if exc.code in {
                    "RECONCILIATION_ACTION_NOT_ALLOWED",
                    "RECONCILIATION_CANONICAL_UPDATE_REJECTED",
                }
                else exc.code
            )
            raise ZeroTouchRequestError(code=code, message=exc.public_message) from None
        except ReconciliationInfrastructureError as exc:
            failed = self._technical_failure(
                record,
                stage=AutomationStage.DOCUMENT,
                code=exc.code,
                message="Reconciliation stopped after a technical failure.",
            )
            raise ZeroTouchInfrastructureError(
                case_id=failed.case_id,
                automation_id=failed.automation_id,
                code=exc.code,
                message=exc.public_message,
            ) from None

        candidate = record.model_copy(deep=True)
        resolved = next(
            entry for entry in candidate.exceptions if entry.exception_id == discrepancy_id
        )
        resolved.status = BusinessExceptionStatus.RESOLVED
        resolved.resolved_at = self._clock()
        resolved.resolution = ExceptionResolutionAction(action.value)
        candidate.metrics.human_interventions += 1
        candidate.metrics.exceptions_resolved += 1
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.RECONCILIATION_DECISION_RECORDED,
            outcome=EventOutcome.SUCCEEDED,
            code=action.value,
            message="A bounded reconciliation decision was recorded by the backend.",
        )
        if reconciliation.status == ReconciliationStatus.REVIEW_REQUIRED:
            discrepancies_by_id = {
                entry.discrepancy_id: entry
                for entry in reconciliation.open_discrepancies
            }
            for active in candidate.active_exceptions:
                discrepancy = discrepancies_by_id.get(active.exception_id)
                if discrepancy is None:
                    continue
                active.evidence_version = self._reconciliation_evidence_version(
                    reconciliation, discrepancy
                )
                active.authoritative_evidence_digest = self._authoritative_evidence_digest(
                    case_id=candidate.case_id,
                    exception_type=active.exception_type,
                    evidence_version=active.evidence_version,
                    blocker_codes=active.blocker_codes,
                )
            candidate.status = AutomationStatus.WAITING_FOR_REVIEW
            candidate.current_stage = AutomationStage.DOCUMENT
            return self._save(record, candidate)
        candidate.status = AutomationStatus.RESUMING
        candidate.current_stage = AutomationStage.DOCUMENT
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code="AUTOMATION_RESUMING",
            message="All reconciliation blockers are resolved; onboarding is resuming.",
        )
        self._save(record, candidate)
        return self._advance_locked(case_id=record.case_id)

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
                current_documents = [
                    document for document in documents if document.is_current_evidence
                ]
                failed_document = next(
                    (
                        document
                        for document in current_documents
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
                if self._reconciliation.get(case_id=case_id) is None:
                    for document in current_documents:
                        if document.state != DocumentProcessingState.REVIEW_REQUIRED:
                            continue
                        assessment = self._documents.assess_auto_clear(
                            case_id=case_id, document_id=document.document_id
                        )
                        if assessment.eligible:
                            self._documents.auto_confirm_document(
                                case_id=case_id, document_id=document.document_id
                            )
                try:
                    reconciliation = self._reconciliation.reconcile_current(case_id=case_id)
                except ReconciliationRequestError as exc:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.DOCUMENT,
                        code=exc.code,
                        message="Current evidence could not enter reconciliation safely.",
                    )
                except ReconciliationInfrastructureError as exc:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.DOCUMENT,
                        code=exc.code,
                        message="Reconciliation stopped after a technical failure.",
                    )
                if reconciliation.status == ReconciliationStatus.REVIEW_REQUIRED:
                    return self._raise_reconciliation_exceptions(record, reconciliation)
                if reconciliation.status in {
                    ReconciliationStatus.MATCHED,
                    ReconciliationStatus.RESOLVED,
                }:
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.DOCUMENT,
                        event_type=(
                            AutomationEventType.RECONCILIATION_EVALUATED
                        ),
                        code=(
                            "RECONCILIATION_RESOLVED"
                            if reconciliation.status == ReconciliationStatus.RESOLVED
                            else "RECONCILIATION_MATCHED"
                        ),
                        message="Current registry and document observations were reconciled.",
                        started_at=self._clock(),
                    )
                    continue
                return self._technical_failure(
                    record,
                    stage=AutomationStage.DOCUMENT,
                    code="RECONCILIATION_STATE_INVALID",
                    message="Reconciliation made no safe progress.",
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
                            event_type=(AutomationEventType.MOCK_FINALIZATION_RECOVERY_PENDING),
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
        if DocumentAutoClearBlocker.TEXT_UNAVAILABLE in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING
            code = "DOCUMENT_TEXT_UNAVAILABLE"
            explanation = "No extractable text was found; this bounded POC does not perform OCR."
        elif DocumentAutoClearBlocker.SOURCE_CONFLICT in blockers:
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

    def _raise_reconciliation_exceptions(
        self,
        record: ZeroTouchAutomationRecord,
        reconciliation: ReconciliationCaseRecord,
    ) -> ZeroTouchAutomationRecord:
        """Project every open field discrepancy without making either source authoritative."""

        outcome_codes = {
            ReconciliationOutcome.CONFLICT: "DOCUMENT_SOURCE_CONFLICT",
            ReconciliationOutcome.MISSING_IN_SOURCE: "DOCUMENT_REQUIRED_FIELD_MISSING",
            ReconciliationOutcome.UNVERIFIABLE: "DOCUMENT_LOW_CONFIDENCE",
            ReconciliationOutcome.INVALID: "RECONCILIATION_INVALID",
        }
        def code_for(item: ReconciliationDiscrepancy) -> str:
            if any(
                observation.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
                and observation.evidence_reference == "DOCUMENT_TEXT_UNAVAILABLE"
                for observation in item.observations
            ):
                return "DOCUMENT_TEXT_UNAVAILABLE"
            return outcome_codes[item.outcome]

        aggregate_codes = tuple(
            dict.fromkeys(code_for(item) for item in reconciliation.open_discrepancies)
        )
        for discrepancy in reconciliation.open_discrepancies:
            if any(
                item.exception_id == discrepancy.discrepancy_id
                for item in record.active_exceptions
            ):
                continue
            code = code_for(discrepancy)
            exception_type = {
                ReconciliationOutcome.CONFLICT: (
                    BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT
                ),
                ReconciliationOutcome.MISSING_IN_SOURCE: (
                    BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING
                ),
                ReconciliationOutcome.UNVERIFIABLE: (
                    BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE
                ),
                ReconciliationOutcome.INVALID: (
                    BusinessExceptionType.RECONCILIATION_INVALID
                ),
            }[discrepancy.outcome]
            registry = next(
                (
                    item
                    for item in discrepancy.observations
                    if item.source_kind == ReconciliationSourceKind.REGISTRY
                ),
                None,
            )
            document = next(
                (
                    item
                    for item in discrepancy.observations
                    if item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
                ),
                None,
            )
            document_observations = [
                item
                for item in discrepancy.observations
                if item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
            ]
            affected_document_index = next(
                (
                    index
                    for index, item in enumerate(document_observations)
                    if registry is None
                    or item.normalized_value != registry.normalized_value
                    or item.validity.value != "VALID"
                ),
                0,
            )
            affected_document_id = (
                document_observations[affected_document_index].source_record_id
                or reconciliation.source_document_ids[0]
            )
            evidence = (
                SafeExceptionEvidence(
                    reference_id=affected_document_id,
                    field_key=discrepancy.field_name.value,
                    registry_value=(registry.normalized_value if registry else None),
                    document_value=(document.normalized_value if document else None),
                    confidence=(document.confidence if document else None),
                    comparison=discrepancy.outcome.value,
                ),
            )
            record = self._add_exception(
                record,
                exception_type=exception_type,
                stage=AutomationStage.DOCUMENT,
                blocker_code=code,
                explanation=(
                    "Registry and document observations disagree and require an explicit "
                    "bounded decision."
                    if discrepancy.outcome == ReconciliationOutcome.CONFLICT
                    else (
                        "Document evidence is not currently usable for deterministic "
                        "reconciliation."
                    )
                ),
                evidence_version=self._reconciliation_evidence_version(
                    reconciliation, discrepancy
                ),
                evidence=evidence,
                actions=tuple(
                    ExceptionResolutionAction(action.value)
                    for action in discrepancy.allowed_actions
                ),
                blocker_codes=aggregate_codes,
                exception_id=discrepancy.discrepancy_id,
            )
        return record

    @staticmethod
    def _reconciliation_evidence_version(
        reconciliation: ReconciliationCaseRecord,
        discrepancy: ReconciliationDiscrepancy,
    ) -> str:
        registry = next(
            (
                item
                for item in discrepancy.observations
                if item.source_kind == ReconciliationSourceKind.REGISTRY
            ),
            None,
        )
        document_observations = [
            item
            for item in discrepancy.observations
            if item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
        ]
        affected_document_index = next(
            (
                index
                for index, item in enumerate(document_observations)
                if registry is None
                or item.normalized_value != registry.normalized_value
                or item.validity.value != "VALID"
            ),
            0,
        )
        affected_document_id = (
            document_observations[affected_document_index].source_record_id
            or reconciliation.source_document_ids[0]
        )
        affected_source_index = reconciliation.source_document_ids.index(
            affected_document_id
        )
        return (
            f"reconciliation:{reconciliation.version}:"
            f"{reconciliation.source_document_event_counts[affected_source_index]}:"
            f"{discrepancy.evidence_fingerprint}"
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
        exception_id: UUID | None = None,
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
                exception_id=exception_id or self._uuid_factory(),
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


def _parse_reconciliation_evidence_version(value: str) -> tuple[int, str]:
    try:
        prefix, raw_version, raw_document_version, fingerprint = value.split(
            ":", maxsplit=3
        )
        version = int(raw_version)
        document_version = int(raw_document_version)
        if (
            prefix != "reconciliation"
            or version < 1
            or document_version < 1
            or len(fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in fingerprint)
        ):
            raise ValueError
        return version, fingerprint
    except (TypeError, ValueError):
        raise ZeroTouchRequestError(
            code="ZERO_TOUCH_EXCEPTION_STALE",
            message="The reconciliation evidence version is invalid.",
        ) from None


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _constant_provider_factory(
    provider: OwnershipProvider,
) -> Callable[[], OwnershipProvider]:
    def factory() -> OwnershipProvider:
        return provider

    return factory
