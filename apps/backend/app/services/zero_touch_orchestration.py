"""Monotonic Phase 06 zero-touch coordinator over the accepted bounded services."""

import hmac
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.connectors.idp import IdpProvider
from app.connectors.ownership import OwnershipProvider
from app.domain.access import CasePriority, TeamId
from app.domain.clm import (
    ClmBlockerCode,
    ClmOrchestrationRecord,
    ClmStatus,
    ClmWarningCode,
    GoldTierSearchCheckpointStatus,
    GoldTierSearchDisposition,
    can_confirm_existing_customer,
)
from app.domain.documents import (
    DocumentAutoClearBlocker,
    DocumentFieldKey,
    DocumentProcessingRecord,
    DocumentProcessingState,
    FieldReviewStatus,
    ReviewDecision,
)
from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import (
    EventOutcome,
    GovernmentBodyType,
    OnboardingCase,
    SafeError,
    WorkflowState,
)
from app.domain.onboarding_intelligence import (
    EntityResolutionOutcome,
    MockRiskBand,
    OnboardingIntelligenceRecord,
)
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState
from app.domain.reconciliation import (
    CANONICAL_BASELINE_SOURCE_KINDS,
    ReconciliationCaseRecord,
    ReconciliationDecisionAction,
    ReconciliationDiscrepancy,
    ReconciliationField,
    ReconciliationOutcome,
    ReconciliationSourceKind,
    ReconciliationStatus,
)
from app.domain.review_decisions import ReviewDecisionBatch
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierRecoveryOrigin,
)
from app.domain.zero_touch import (
    AUTOMATION_STAGE_ORDER,
    AUTOMATION_STAGE_ORDER_VERSION,
    LEGACY_AUTOMATION_STAGE_ORDER,
    LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
    AutomationEvent,
    AutomationEventType,
    AutomationMetrics,
    AutomationStage,
    AutomationStatus,
    BlockerDecisionAction,
    BlockerDecisionRecord,
    BlockerMinimumInput,
    BusinessException,
    BusinessExceptionStatus,
    BusinessExceptionType,
    ExceptionResolutionAction,
    SafeExceptionEvidence,
    ZeroTouchAutomationRecord,
)
from app.services.blocker_decision_policy import (
    AutoResolvedDecisionInput,
    AutoResolvedRule,
    BlockerDecisionPolicy,
    ContinueWithWarningDecisionInput,
    ContinueWithWarningRule,
    OpenBlockerDecisionInput,
)
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.document_errors import (
    DocumentProcessingInfrastructureError,
    DocumentRequestError,
)
from app.services.document_processing import DocumentProcessingService
from app.services.errors import OnboardingInfrastructureError
from app.services.government_status import (
    government_profile_applies,
    government_status_confirmed,
    government_status_evidence,
    statute_matches,
)
from app.services.manual_ownership_evidence import (
    ManualOwnershipDeclaration,
    ManualOwnershipEvidenceError,
    ManualOwnershipEvidenceProvider,
)
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import OwnershipInfrastructureError, OwnershipRequestError
from app.services.partnership_agreement import (
    agreement_rows,
    partnership_agreement_issues,
    registry_partner_names,
)
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

ADVISORY_CONTINUATION_REQUESTED = "ADVISORY_CONTINUATION_REQUESTED"
DOCUMENT_INTAKE_REOPENED = "DOCUMENT_INTAKE_REOPENED"
_LOGGER = logging.getLogger(__name__)
_OWNERSHIP_DEPENDENCY_EXCEPTION_TYPES = frozenset({
    BusinessExceptionType.OWNERSHIP_CYCLE,
    BusinessExceptionType.OWNERSHIP_INCOMPLETE,
    BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED,
    BusinessExceptionType.GOVERNMENT_STATUS_REQUIRED,
})


class _CaseDocumentReader:
    """Bind the document service's case-aware lookup to the manual provider protocol."""

    def __init__(
        self, documents: DocumentProcessingService, case_id: UUID
    ) -> None:
        self._documents = documents
        self._case_id = case_id

    def get(self, document_id: UUID) -> DocumentProcessingRecord | None:
        return self._documents.get_document(case_id=self._case_id, document_id=document_id)


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
        establishment_discard: Callable[[UUID], str | None] | None = None,
        max_transitions_per_run: int = 12,
        clock: Callable[[], datetime] | None = None,
        intelligence_evaluator: Callable[[UUID], OnboardingIntelligenceRecord | None] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
        workflow_send_hold: Callable[[UUID], str | None] | None = None,
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
        self._establishment_discard = establishment_discard
        self._max_transitions = max_transitions_per_run
        self._clock = clock or (lambda: datetime.now(UTC))
        self._intelligence_evaluator = intelligence_evaluator
        self._uuid_factory = uuid_factory or uuid4
        self._workflow_send_hold = workflow_send_hold
        self._blocker_decision_policy = BlockerDecisionPolicy()

    def release_provider_binding(self, binding_id: str) -> None:
        """Release process-local provider state only after physical deletion succeeds."""

        self._ownership_provider_bindings.release(binding_id)

    def create_case(
        self,
        uen: str,
        country_of_incorporation: str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
        created_by_actor_id: str | None = None,
        establishment_action: Callable[[UUID], None] | None = None,
        establishment_rollback: Callable[[UUID], None] | None = None,
        establishment_projection: Callable[[ZeroTouchAutomationRecord], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Atomically establish every initial case-owned record under one case lock."""

        case_id, correlation_id = self._cases.reserve_case_identity()
        with self._cases.case_lock(case_id):
            try:
                record = self._create_case_locked(
                    case_id,
                    correlation_id,
                    uen,
                    country_of_incorporation,
                    legal_name=legal_name,
                    team_id=team_id,
                    priority=priority,
                    created_by_actor_id=created_by_actor_id,
                )
                if establishment_action is not None:
                    establishment_action(record.case_id)
                if establishment_projection is not None:
                    establishment_projection(record)
                return record
            except Exception as primary_error:
                try:
                    self._discard_failed_establishment(case_id, establishment_rollback)
                except Exception as rollback_error:
                    raise primary_error from rollback_error
                raise

    def _create_case_locked(
        self,
        case_id: UUID,
        correlation_id: UUID,
        uen: str,
        country_of_incorporation: str | None,
        *,
        legal_name: str | None,
        team_id: TeamId | None,
        priority: CasePriority | None,
        created_by_actor_id: str | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Create registry, CLM, and automation state while the RLock is owned."""

        try:
            clm_record = self._clm.create_case_with_identity(
                case_id,
                correlation_id,
                uen,
                country_of_incorporation,
                legal_name=legal_name,
                team_id=team_id,
                priority=priority,
                created_by_actor_id=created_by_actor_id,
            )
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
        search = clm_record.target_search_checkpoint
        search_ready = bool(
            search is not None
            and search.status == GoldTierSearchCheckpointStatus.COMPLETED
            and search.disposition
            in {
                GoldTierSearchDisposition.NO_MATCH,
                GoldTierSearchDisposition.EXACT_MATCH,
                GoldTierSearchDisposition.CONFIRMED_EXISTING,
            }
        )
        search_review = bool(
            search is not None and search.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
        )
        search_failed = bool(
            search is not None and search.status == GoldTierSearchCheckpointStatus.FAILED
        )
        record = ZeroTouchAutomationRecord(
            case_id=case.case_id,
            automation_id=self._uuid_factory(),
            ownership_provider_binding_id=(self._ownership_provider_bindings.default_binding_id),
            status=(
                AutomationStatus.PENDING_INPUTS
                if registry_ready and (search_ready or search_failed)
                else (
                    AutomationStatus.TECHNICAL_FAILURE
                    if registry_failed
                    else AutomationStatus.WAITING_FOR_REVIEW
                )
            ),
            current_stage=(
                AutomationStage.DOCUMENT
                if registry_ready and (search_ready or search_failed)
                else AutomationStage.GOLDTIER_SEARCH
                if search_review or search_failed or registry_ready
                else AutomationStage.REGISTRY
            ),
            completed_stages=(
                (AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH)
                if registry_ready and (search_ready or search_failed)
                else (AutomationStage.REGISTRY,)
                if registry_ready
                else ()
            ),
            technical_failure=(
                case.error
                if registry_failed
                else None
            ),
            metrics=AutomationMetrics(
                automated_stages_completed=2 if search_ready else 1 if registry_ready else 0,
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
        if registry_ready and case.registry_acquisition is not None:
            record = self._append_event(
                record,
                event_type=AutomationEventType.REGISTRY_AUTOMATED,
                outcome=EventOutcome.SUCCEEDED,
                code="REGISTRY_AUTOMATED",
                message="Registry evidence was validated automatically.",
            )
        if search_ready and search is not None:
            target_stage = record.current_stage
            record.current_stage = AutomationStage.GOLDTIER_SEARCH
            record = self._append_event(
                record,
                event_type=AutomationEventType.GOLDTIER_SEARCH_COMPLETED,
                outcome=EventOutcome.SUCCEEDED,
                code=search.code,
                message=search.message,
            )
            record.current_stage = target_stage
        elif search_review and search is not None:
            record = self._append_event(
                record,
                event_type=AutomationEventType.GOLDTIER_SEARCH_REVIEW_REQUIRED,
                outcome=EventOutcome.REVIEW_REQUIRED,
                code=search.code,
                message=search.message,
            )
            record = self._add_exception(
                record,
                exception_type=BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED,
                stage=AutomationStage.GOLDTIER_SEARCH,
                blocker_code=search.code or "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
                explanation=(
                    "GoldTier candidates require identity review. This onboarding case "
                    "remains valid and may retain case evidence, while Shell, target binding, "
                    "and Amend remain blocked."
                ),
                evidence_version=f"goldtier-search:{search.request_id}",
                evidence=(),
                actions=(),
            )
        elif search_failed and search is not None:
            record = self._append_event(
                record,
                event_type=AutomationEventType.GOLDTIER_SEARCH_FAILED,
                outcome=EventOutcome.FAILED,
                code=search.code,
                message=search.message,
            )
        if registry_failed:
            record.status = AutomationStatus.TECHNICAL_FAILURE
            record.current_stage = AutomationStage.REGISTRY
            for item in record.active_exceptions:
                item.status = BusinessExceptionStatus.CANCELLED
            record = self._append_event(
                record,
                event_type=AutomationEventType.AUTOMATION_TECHNICAL_FAILURE,
                outcome=EventOutcome.FAILED,
                code=(case.error.code if case.error is not None else "REGISTRY_FAILED"),
                message="Registry automation stopped after a technical failure.",
            )
        elif not registry_ready:
            blocker_code = case.error.code if case.error is not None else "REGISTRY_REVIEW_REQUIRED"
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

    @property
    def automation_repository(self) -> ZeroTouchAutomationRepository:
        return self._repository

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
                and not _allows_retained_evidence_intake(record)
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
                for document in self._current_documents(case_id):
                    if document.state == DocumentProcessingState.REVIEW_REQUIRED:
                        self._documents.auto_confirm_document(
                            case_id=case_id, document_id=document.document_id, allow_partial=True
                        )
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
        reauthorize: Callable[[], None] | None = None,
    ) -> DocumentProcessingRecord:
        """Process one intake document without starting reconciliation or later stages."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            retained_evidence_intake = _allows_retained_evidence_intake(record)
            case = self._cases.get_case(case_id)
            clm = self._clm.get(case_id=case_id)
            ownership = self._ownership.get(case_id=case_id)
            ownership_intake = (
                record.status == AutomationStatus.WAITING_FOR_REVIEW
                and record.current_stage == AutomationStage.OWNERSHIP
                and case is not None
                and case.target_dispatch_confirmation is None
                and case.goldtier_result is None
                and clm is not None
                and clm.submission_snapshot is None
                and clm.status != ClmStatus.SUBMITTING
                and ownership is not None
                and ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
            )
            classification_intake = (
                record.status == AutomationStatus.WAITING_FOR_REVIEW
                and record.current_stage == AutomationStage.READINESS
                and case is not None
                and case.target_dispatch_confirmation is None
                and case.goldtier_result is None
                and clm is not None
                and clm.submission_snapshot is None
                and clm.status != ClmStatus.SUBMITTING
                and not self._cases.has_retained_target_execution(case_id)
            )
            if (
                record.status != AutomationStatus.PENDING_INPUTS
                and not retained_evidence_intake
                and not ownership_intake
                and not classification_intake
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_NOT_OPEN",
                    message="Document intake is not open for this case.",
                )
            if self._has_required_document_reuploads(case_id):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_DOCUMENT_REUPLOAD_REQUIRED",
                    message=(
                        "Interrupted documents must be retried before unrelated "
                        "evidence can be added."
                    ),
                )
            document = self._documents.create_document(
                case_id=case_id,
                display_name=display_name,
                content_type=content_type,
                content=content,
                provider=idp_provider,
            )
            if ownership_intake:
                self._refresh_document_checkpoint_locked(record, human_intervention=True)
                return (
                    self._documents.get_document(case_id=case_id, document_id=document.document_id)
                    or document
                )
            for current in self._current_documents(case_id):
                if current.state == DocumentProcessingState.REVIEW_REQUIRED:
                    self._documents.auto_confirm_document(
                        case_id=case_id, document_id=current.document_id, allow_partial=True
                    )
            if classification_intake:
                self._sync_document_target_classification(case_id)
                self._clm.refresh_target_classification(case_id=case_id)
            return (
                self._documents.get_document(case_id=case_id, document_id=document.document_id)
                or document
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
        reauthorize: Callable[[], None] | None = None,
    ) -> DocumentProcessingRecord:
        """Explicitly supersede one failed intake record without creating a new case."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            automation = self._require_record(case_id)
            if automation.status != AutomationStatus.PENDING_INPUTS:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_NOT_OPEN",
                    message="Document intake is not open for this case.",
                )
            failed = self._documents.get_document(case_id=case_id, document_id=failed_document_id)
            if (
                failed is None
                or failed.state != DocumentProcessingState.FAILED
                or not failed.is_current_evidence
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_RETRY_INVALID",
                    message="The failed intake document is no longer retryable.",
                )
            replacement = self._documents.replace_document(
                case_id=case_id,
                document_id=failed.document_id,
                expected_event_count=len(failed.events),
                display_name=display_name,
                content_type=content_type,
                content=content,
                provider=idp_provider,
            )
            if self._initial_intake_pending(automation):
                self._documents.auto_confirm_document(
                    case_id=case_id, document_id=replacement.document_id, allow_partial=True,
                )
            elif not self._has_required_document_reuploads(case_id):
                self.start(case_id=case_id)
            return (
                self._documents.get_document(case_id=case_id, document_id=replacement.document_id)
                or replacement
            )

    @staticmethod
    def _initial_intake_pending(record: ZeroTouchAutomationRecord) -> bool:
        """Unstarted intake is distinct from a retained started-workflow recovery."""
        return record.status == AutomationStatus.PENDING_INPUTS and record.started_at is None

    def _has_required_document_reuploads(self, case_id: UUID) -> bool:
        documents = self._current_documents(case_id)
        return any(item.state == DocumentProcessingState.FAILED for item in documents)

    def _current_documents(self, case_id: UUID) -> list[DocumentProcessingRecord]:
        return [
            item
            for item in self._documents.list_documents(case_id=case_id)
            if item.is_current_evidence
        ]

    @staticmethod
    def target_recovery_context_is_supported(record: ZeroTouchAutomationRecord | None) -> bool:
        """Share the existing matching-failure predicate with browser eligibility."""
        return bool(
            record is None or record.status != AutomationStatus.TECHNICAL_FAILURE or (
                record.current_stage == AutomationStage.MOCK_GOLDTIER
                and record.technical_failure is not None
                and record.technical_failure.code == "CLM_TARGET_OUTCOME_UNCERTAIN"
            )
        )

    def record_provider_policy_recovery(
        self,
        *,
        case_id: UUID,
        recovered_party_id: str,
        legal_name: str,
        registration_number: str,
        country_of_incorporation: str,
        provider_policy: str,
        provider_policy_status: str,
        actor_id: str,
        origin: GoldTierRecoveryOrigin,
        reauthorize: Callable[[], None],
    ) -> GoldTierExecutionLedgerEntry:
        """Record provider proof and reconcile only the matching target failure; no dispatch."""

        with self._cases.case_lock(case_id):
            reauthorize()
            # The existing recovery API also serves manually orchestrated CLM
            # submissions. Reconcile automation only when that owner has a record.
            record = self._repository.get_for_case(case_id)
            clm = self._clm.get(case_id=case_id)
            if clm is None or clm.submission_snapshot is None:
                raise ValueError("Policy recovery requires the frozen target submission")
            if not self.target_recovery_context_is_supported(record):
                raise ValueError("Policy recovery cannot clear an unrelated technical failure")
            entry = self._cases.recover_uncertain_policy_from_provider(
                submission_input=clm.submission_snapshot.target_input,
                recovered_party_id=recovered_party_id,
                legal_name=legal_name,
                registration_number=registration_number,
                country_of_incorporation=country_of_incorporation,
                provider_policy=provider_policy,
                provider_policy_status=provider_policy_status,
                actor_id=actor_id,
                origin=origin,
                reauthorize=reauthorize,
            )
            self._retain_target_recovery_pending(record, operation="POLICY")
            return entry

    def record_provider_shell_recovery(
        self, *, case_id: UUID, recovered_party_id: str, legal_name: str,
        registration_number: str, country_of_incorporation: str, actor_id: str,
        origin: GoldTierRecoveryOrigin, reauthorize: Callable[[], None],
    ) -> GoldTierExecutionLedgerEntry:
        """Reuse Shell evidence validation and the same explicit continuation checkpoint."""
        with self._cases.case_lock(case_id):
            reauthorize()
            record = self._repository.get_for_case(case_id)
            clm = self._clm.get(case_id=case_id)
            if clm is None or clm.submission_snapshot is None:
                raise ValueError("Shell recovery requires the frozen target submission")
            if not self.target_recovery_context_is_supported(record):
                raise ValueError("Shell recovery cannot clear an unrelated technical failure")
            entry = self._cases.recover_uncertain_shell_from_provider(
                submission_input=clm.submission_snapshot.target_input,
                recovered_party_id=recovered_party_id, legal_name=legal_name,
                registration_number=registration_number,
                country_of_incorporation=country_of_incorporation,
                actor_id=actor_id, origin=origin, reauthorize=reauthorize,
            )
            self._retain_target_recovery_pending(record, operation="SHELL")
            return entry

    def _retain_target_recovery_pending(
        self, record: ZeroTouchAutomationRecord | None, *, operation: Literal["SHELL", "POLICY"],
    ) -> None:
        if record is None:
            return
        recovery_code = f"GT_{operation}_PROVIDER_VERIFIED_RECOVERY"
        if record.status == AutomationStatus.TECHNICAL_FAILURE:
            candidate = record.model_copy(deep=True)
            candidate.status = AutomationStatus.RESUMING
            candidate.technical_failure = None
            candidate.metrics.final_outcome = None
            candidate = self._append_event(
                candidate, event_type=AutomationEventType.AUTOMATION_RESUMING,
                outcome=EventOutcome.SUCCEEDED, code=recovery_code,
                message=(
                    f"Provider-verified {operation.title()} recovery retained without replay; "
                    "explicit resume can continue the frozen target submission."
                ),
            )
            record = self._save(record, candidate)
        if record.status == AutomationStatus.RESUMING and record.events[-1].code == recovery_code:
            candidate = record.model_copy(deep=True)
            candidate.status = AutomationStatus.RECOVERY_PENDING
            candidate = self._append_event(
                candidate, event_type=AutomationEventType.TARGET_OPERATION_RECOVERY_PENDING,
                outcome=EventOutcome.SUCCEEDED, code=f"GT_{operation}_RECOVERY_PENDING",
                message="Recovered target prefix is ready for explicit resume without replay.",
            )
            self._save(record, candidate)

    def start(
        self,
        *,
        case_id: UUID,
        ownership_provider: OwnershipProvider | None = None,
        expected_document_count: int | None = None,
        reauthorize: Callable[[], None] | None = None,
        refresh_document_checkpoint: bool = False,
        expected_automation_id: UUID | None = None,
        expected_automation_version: int | None = None,
        expected_clm_version: int | None = None,
        expected_case_event_count: int | None = None,
        reauthorize_document_recovery: Callable[[], None] | None = None,
        automatic_release: bool = False,
    ) -> ZeroTouchAutomationRecord:
        """Idempotently start or continue; normal upload already invokes this."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if self._intake_reopen_interrupted(record):
                if reauthorize_document_recovery is not None:
                    reauthorize_document_recovery()
                return self._return_to_document_intake(record)
            pending_refresh = self.document_refresh_pending(record)
            # D-124: only /resume or the startup release continues past an advisory hold or
            # applies a retained identity decision, with version context, in this lock.
            advisory_continuation = (
                refresh_document_checkpoint and self.advisory_continuation_pending(record)
            )
            recovery_context = (
                expected_automation_id, expected_automation_version,
                expected_clm_version, expected_case_event_count,
            )
            if (
                pending_refresh or advisory_continuation
                or any(value is not None for value in recovery_context)
            ):
                if reauthorize_document_recovery is not None:
                    reauthorize_document_recovery()
                case = self._cases.get_case(case_id)
                clm = self._clm.get(case_id=case_id)
                assert case is not None and clm is not None
                current_context = (
                    record.automation_id, record.version, clm.version, len(case.events),
                )
                if recovery_context != current_context:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_DOCUMENT_REFRESH_STALE",
                        message="The case changed; reload current evidence before recovery.",
                    )
                if self.evidence_edit_is_frozen(case_id=case_id):
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_DOCUMENT_REFRESH_FROZEN",
                        message="Document evidence is frozen for target submission.",
                    )
            if pending_refresh:
                return self._continue_replacement_locked(record)
            if advisory_continuation:
                if self._existing_confirmation_projection_due(record):
                    return self._project_existing_confirmation_locked(record)
                # Before the hold is retired: a failed document can be replaced only at intake.
                if self._has_required_document_reuploads(case_id):
                    return self._reopen_document_intake_locked(record)
                if not self._current_documents(case_id):
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_DOCUMENTS_REQUIRED",
                        message="At least one valid supporting document is required.",
                    )
                record = self._begin_advisory_continuation_locked(
                    record, automatic=automatic_release,
                )
            record = self._recover_obsolete_registry_ownership_locked(
                record, release_advisory=advisory_continuation,
            )
            if (
                refresh_document_checkpoint
                and record.status == AutomationStatus.WAITING_FOR_REVIEW
                and record.current_stage == AutomationStage.DOCUMENT
            ):
                return self._refresh_document_checkpoint_locked(record)
            retained_evidence_intake = _allows_retained_evidence_intake(record)
            if record.status in {
                AutomationStatus.COMPLETED,
                AutomationStatus.TECHNICAL_FAILURE,
            } or (
                record.status == AutomationStatus.WAITING_FOR_REVIEW
                and not retained_evidence_intake
                and not _has_unproved_prerequisite(record)
            ):
                return record
            current_documents = self._current_documents(case_id)
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
            if self._initial_intake_pending(record) and expected_document_count is None:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_INTAKE_INCOMPLETE",
                    message="Complete the intended document intake before starting onboarding.",
                )
            if retained_evidence_intake:
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

    @staticmethod
    def document_refresh_pending(record: ZeroTouchAutomationRecord) -> bool:
        """The durable accepted replacement still awaits dependent continuation."""
        return (
            record.status == AutomationStatus.RESUMING
            and record.current_stage == AutomationStage.DOCUMENT
            and bool(record.events)
            and record.events[-1].code == "DOCUMENT_REPLACEMENT_ACCEPTED"
        )

    def _refresh_replacement_evidence_locked(self, record: ZeroTouchAutomationRecord) -> None:
        try:
            self._clm.refresh_pre_submission_evidence(
                case_id=record.case_id, document_revision=True,
            )
        except ClmRequestError as exc:
            raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
        except ClmInfrastructureError as exc:
            raise ZeroTouchInfrastructureError(
                case_id=record.case_id, automation_id=record.automation_id,
                code=exc.code, message=exc.public_message,
            ) from None

    def _continue_replacement_locked(
        self, record: ZeroTouchAutomationRecord,
    ) -> ZeroTouchAutomationRecord:
        self._refresh_replacement_evidence_locked(record)
        if self._has_required_document_reuploads(record.case_id):
            return self._return_to_document_intake(record)
        return self._advance_locked(case_id=record.case_id)

    def evidence_edit_is_frozen(self, *, case_id: UUID) -> bool:
        """Current owning projection; a retained target intent/attempt also freezes edits."""
        case = self._cases.get_case(case_id)
        clm = self._clm.get(case_id=case_id)
        return (
            case is None or clm is None
            or case.target_dispatch_confirmation is not None
            or case.goldtier_result is not None
            or clm.submission_snapshot is not None
            or clm.execution_receipt is not None
            or clm.status == ClmStatus.SUBMITTING
            or self._cases.has_retained_target_execution(case_id)
        )

    def government_reconfirmation_needs_resume(self, *, case_id: UUID) -> bool:
        """D-125 (gate M1): a revoked Government checkpoint with no open hold to confirm.

        True only where `_recover_obsolete_registry_ownership_locked` would restore the
        Government hold on resume: OWNERSHIP was completed, the stored confirmation no
        longer counts (for example a pre-D-125 one without a statute), no
        GOVERNMENT_STATUS_REQUIRED hold is open and nothing was frozen for or sent to the
        target. Read-only; the browser only offers the existing resume.
        """
        record = self._repository.get_for_case(case_id)
        case = self._cases.get_case(case_id)
        clm = self._clm.get(case_id=case_id)
        if (
            record is None or case is None or clm is None
            or record.status in {AutomationStatus.COMPLETED, AutomationStatus.TECHNICAL_FAILURE}
            or AutomationStage.OWNERSHIP not in record.completed_stages
            or clm.submission_snapshot is not None
            or case.goldtier_result is not None
            or self._cases.has_retained_target_execution(case_id)
        ):
            return False
        if any(
            item.exception_type == BusinessExceptionType.GOVERNMENT_STATUS_REQUIRED
            for item in record.active_exceptions
        ):
            return False
        return self._government_gate(case_id) is False

    def document_replacement_allowed(self, *, case_id: UUID) -> bool:
        record = self._require_record(case_id)
        return (
            record.status in {AutomationStatus.PENDING_INPUTS, AutomationStatus.WAITING_FOR_REVIEW}
            and record.current_stage in {AutomationStage.DOCUMENT, AutomationStage.READINESS}
            and not self.evidence_edit_is_frozen(case_id=case_id)
        )

    def replace_document(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        expected_document_event_count: int,
        display_name: str,
        content_type: str,
        content: bytes,
        expected_automation_version: int | None = None,
        expected_clm_version: int | None = None,
        expected_case_event_count: int | None = None,
        idp_provider: IdpProvider | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Supersede current pre-submission evidence and re-evaluate its dependencies."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if self.evidence_edit_is_frozen(case_id=case_id):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_NOT_ALLOWED",
                    message="Document evidence is frozen for target submission.",
                )
            if record.status in {AutomationStatus.COMPLETED, AutomationStatus.TECHNICAL_FAILURE}:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_NOT_ALLOWED",
                    message="Replacement evidence is not accepted after a terminal outcome.",
                )
            if not self.document_replacement_allowed(case_id=case_id):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_NOT_ALLOWED",
                    message=("Replacement evidence is only accepted during current "
                             "pre-submission review."),
                )
            case = self._cases.get_case(case_id)
            clm = self._clm.get(case_id=case_id)
            assert case is not None and clm is not None
            final_review = record.current_stage == AutomationStage.READINESS
            versions = (
                (expected_automation_version, record.version),
                (expected_clm_version, clm.version),
                (expected_case_event_count, len(case.events)),
            )
            if any((final_review and expected is None) or
                   (expected is not None and expected != actual)
                   for expected, actual in versions):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REPLACEMENT_STALE",
                    message=("The case changed before document replacement; "
                             "reload current evidence."),
                )
            try:
                replacement = self._documents.replace_document(
                    case_id=case_id,
                    document_id=document_id,
                    expected_event_count=expected_document_event_count,
                    display_name=display_name,
                    content_type=content_type,
                    content=content,
                    provider=idp_provider,
                )
            except DocumentProcessingInfrastructureError as exc:
                recovered = record
                if exc.code == "IDP_PROCESSING_FAILED":
                    recovered = self._return_to_document_intake(record)
                raise ZeroTouchInfrastructureError(
                    case_id=recovered.case_id,
                    automation_id=recovered.automation_id,
                    code=exc.code,
                    message=exc.public_message,
                ) from None
            if self._initial_intake_pending(record):
                self._documents.auto_confirm_document(
                    case_id=case_id, document_id=replacement.document_id, allow_partial=True,
                )
                return record
            candidate = record.model_copy(deep=True)
            for exception in candidate.active_exceptions:
                if (
                    exception.stage == AutomationStage.DOCUMENT
                    or exception.exception_type
                    == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
                ):
                    exception.status = BusinessExceptionStatus.CANCELLED
                    exception.resolved_at = self._clock()
            candidate.completed_stages = tuple(
                stage for stage in candidate.completed_stages
                if stage in {AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH}
            )
            candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
            candidate.metrics.final_outcome = None
            candidate.status = AutomationStatus.RESUMING
            candidate.current_stage = AutomationStage.DOCUMENT
            candidate.started_at = candidate.started_at or self._clock()
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += 1
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.AUTOMATION_RESUMING,
                outcome=EventOutcome.SUCCEEDED,
                code="DOCUMENT_REPLACEMENT_ACCEPTED",
                message="Replacement document evidence was accepted; onboarding is re-evaluating.",
            )
            record = self._save(record, candidate)
            return self._continue_replacement_locked(record)

    def apply_review_decisions(
        self,
        *,
        case_id: UUID,
        batch: ReviewDecisionBatch,
        actor_id: str | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """One explicit group confirmation; section checkpoints precede continuation."""
        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            case = self._cases.get_case(case_id)
            clm = self._clm.get(case_id=case_id)
            if (
                case is None
                or record.version != batch.expected_automation_version
                or len(case.events) != batch.expected_case_event_count
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXCEPTION_STALE",
                    message="The case changed before review confirmation.",
                )
            if (
                case.target_dispatch_confirmation is not None
                or case.goldtier_result is not None
                or self._cases.has_retained_target_execution(case_id)
                or (
                    clm is not None
                    and (clm.submission_snapshot is not None or clm.status == ClmStatus.SUBMITTING)
                )
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REVIEW_NOT_ALLOWED",
                    message="Evidence review is frozen for target submission.",
                )
            if batch.documents:
                ownership = self._ownership.get(case_id=case_id)
                allowed = record.status == AutomationStatus.PENDING_INPUTS or (
                    record.status == AutomationStatus.WAITING_FOR_REVIEW
                    and (
                        record.current_stage
                        in {AutomationStage.DOCUMENT, AutomationStage.GOLDTIER_SEARCH}
                        or (
                            record.current_stage == AutomationStage.OWNERSHIP
                            and ownership is not None
                            and ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
                        )
                    )
                )
                if not allowed:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_REVIEW_NOT_ALLOWED",
                        message="Document review is not accepted at the current onboarding stage.",
                    )
                supplied = {
                    (group.document_id, decision.field_key)
                    for group in batch.documents for decision in group.decisions
                }
                required = {
                    (document.document_id, field.field_key)
                    for document in self._current_documents(case_id)
                    if document.state == DocumentProcessingState.REVIEW_REQUIRED
                    and self._reconciliation.resolved_document_checkpoint(
                        case_id=case_id, document_id=document.document_id,
                        event_count=len(document.events),
                    ) is None
                    for field in document.fields if field.review_status == FieldReviewStatus.PENDING
                }
                if not required.issubset(supplied):
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_REVIEW_INCOMPLETE",
                        message=("Select a decision for every required document field "
                                 "before continuing."),
                    )
                try:
                    # Prepare every document before the first section write.
                    prepared = [
                        self._documents.prepare_review_group(case_id=case_id, group=group)
                        for group in batch.documents
                    ]
                    for candidate in prepared:
                        self._documents.retain_review_group(candidate=candidate)
                except DocumentProcessingInfrastructureError as exc:
                    raise ZeroTouchInfrastructureError(
                        case_id=case_id,
                        automation_id=record.automation_id,
                        code=exc.code,
                        message=exc.public_message,
                    ) from None
                if record.status == AutomationStatus.PENDING_INPUTS:
                    if (
                        self._initial_intake_pending(record)
                        or self._has_required_document_reuploads(case_id)
                    ):
                        return record
                    return self.start(case_id=case_id)
                return self._refresh_document_checkpoint_locked(
                    record,
                    human_intervention=True,
                    actor_id=actor_id,
                    reviewed_field_keys=frozenset(
                        decision.field_key
                        for group in batch.documents for decision in group.decisions
                    ),
                )
            active = {item.exception_id: item for item in record.active_exceptions}
            for choice in batch.reconciliation:
                item = active.get(choice.discrepancy_id)
                if (
                    item is None
                    or item.stage != AutomationStage.DOCUMENT
                    or ExceptionResolutionAction(choice.action.value) not in item.available_actions
                ):
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_RESOLUTION_NOT_ALLOWED",
                        message="A source decision is not authorized for the current blocker.",
                    )
            assert batch.expected_reconciliation_version is not None
            try:
                reconciliation = self._reconciliation.resolve_discrepancies(
                    case_id=case_id,
                    choices=batch.reconciliation,
                    expected_version=batch.expected_reconciliation_version,
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
                raise ZeroTouchInfrastructureError(
                    case_id=case_id,
                    automation_id=record.automation_id,
                    code=exc.code,
                    message=exc.public_message,
                ) from None
            candidate_record = record.model_copy(deep=True)
            choices = {choice.discrepancy_id: choice for choice in batch.reconciliation}
            pending = {item.discrepancy_id: item for item in reconciliation.open_discrepancies}
            for item in candidate_record.active_exceptions:
                selected_choice = choices.get(item.exception_id)
                if selected_choice is not None:
                    item.status = BusinessExceptionStatus.RESOLVED
                    item.resolved_at = self._clock()
                    item.resolution = ExceptionResolutionAction(selected_choice.action.value)
                    self._retain_resolution_actor(item, actor_id)
                    candidate_record.metrics.exceptions_resolved += 1
                elif item.exception_id in pending:
                    item.evidence_version = self._reconciliation_evidence_version(
                        reconciliation, pending[item.exception_id]
                    )
                    item.decisions = tuple(
                        d.model_copy(update={"evidence_version": item.evidence_version})
                        for d in item.decisions
                    )
                    item.authoritative_evidence_digest = self._authoritative_evidence_digest(
                        case_id=case_id,
                        exception_type=item.exception_type,
                        evidence_version=item.evidence_version,
                        blocker_codes=item.blocker_codes,
                    )
            candidate_record.metrics.human_interventions += 1
            candidate_record.status = (
                AutomationStatus.WAITING_FOR_REVIEW
                if candidate_record.active_exceptions
                else AutomationStatus.RESUMING
            )
            candidate_record.current_stage = (
                _earliest_open_stage(candidate_record)
                if candidate_record.active_exceptions
                else AutomationStage.DOCUMENT
            )
            candidate_record = self._append_event(
                candidate_record,
                event_type=AutomationEventType.RECONCILIATION_DECISION_RECORDED,
                outcome=EventOutcome.SUCCEEDED,
                code="RECONCILIATION_GROUP_CONFIRMED",
                message="A bounded group of source decisions was confirmed by the reviewer.",
            )
            saved = self._save(record, candidate_record)
            return saved if saved.active_exceptions else self._advance_locked(case_id=case_id)

    def review_document_field(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        field_key: DocumentFieldKey,
        decision: ReviewDecision,
        corrected_value: str | None = None,
        note: str | None = None,
        actor_id: str | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> DocumentProcessingRecord:
        """Apply a current-evidence review and refresh its document checkpoint."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            automation = self._repository.get_for_case(case_id)
            document = self._documents.get_document(case_id=case_id, document_id=document_id)
            reviewed_field = (
                next((item for item in document.fields if item.field_key == field_key), None)
                if document is not None
                else None
            )
            is_final_repeat = (
                reviewed_field is not None
                and reviewed_field.review_status != FieldReviewStatus.PENDING
            )
            independent_review = False
            if (
                automation is not None
                and automation.status == AutomationStatus.WAITING_FOR_REVIEW
                and automation.current_stage in {
                    AutomationStage.OWNERSHIP, AutomationStage.GOLDTIER_SEARCH,
                }
            ):
                case = self._cases.get_case(case_id)
                clm = self._clm.get(case_id=case_id)
                ownership = self._ownership.get(case_id=case_id)
                independent_review = (
                    case is not None
                    and clm is not None
                    and (
                        automation.current_stage == AutomationStage.GOLDTIER_SEARCH
                        or (
                            ownership is not None
                            and ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
                        )
                    )
                    and case.target_dispatch_confirmation is None
                    and case.goldtier_result is None
                    and clm.submission_snapshot is None
                    and clm.status != ClmStatus.SUBMITTING
                    and not self._cases.has_retained_target_execution(case_id)
                )
            if (
                automation is not None
                and not is_final_repeat
                and not (
                    automation.status == AutomationStatus.PENDING_INPUTS
                    or (
                        automation.status == AutomationStatus.WAITING_FOR_REVIEW
                        and automation.current_stage == AutomationStage.DOCUMENT
                    )
                    or independent_review
                )
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_REVIEW_NOT_ALLOWED",
                    message="Document review is not accepted at the current onboarding stage.",
                )
            previous_event_count = len(document.events) if document is not None else 0
            reviewed = self._documents.review_field(
                case_id=case_id,
                document_id=document_id,
                field_key=field_key,
                decision=decision,
                corrected_value=corrected_value,
                note=note,
            )
            if (
                automation is None
                or automation.status == AutomationStatus.PENDING_INPUTS
                or (
                    len(reviewed.events) == previous_event_count
                    and automation.status != AutomationStatus.WAITING_FOR_REVIEW
                )
            ):
                return reviewed
            self._refresh_document_checkpoint_locked(
                automation,
                human_intervention=len(reviewed.events) > previous_event_count,
                actor_id=actor_id,
                reviewed_field_key=field_key,
            )
            return (
                self._documents.get_document(case_id=case_id, document_id=document_id) or reviewed
            )

    def _held_by_advisory_review(self, record: ZeroTouchAutomationRecord) -> bool:
        """D-121: an ownership hold raised before this review became advisory."""

        holds = [
            item for item in record.active_exceptions
            if item.stage == AutomationStage.OWNERSHIP
            and item.exception_type in _OWNERSHIP_DEPENDENCY_EXCEPTION_TYPES
        ]
        if record.status != AutomationStatus.WAITING_FOR_REVIEW or not holds:
            return False
        ownership = self._ownership.get(case_id=record.case_id)
        return (
            ownership is not None
            and self._government_gate(record.case_id) is None
            and self._ownership.review_is_advisory(ownership)
            and not self.evidence_edit_is_frozen(case_id=record.case_id)
            and any(
                item.evidence_version == f"ownership:{ownership.analysis_id}:{ownership.version}"
                for item in holds
            )
        )

    def _advisory_continuation_failed(self, record: ZeroTouchAutomationRecord) -> bool:
        """D-124: a requested continuation failed before anything could reach the target."""

        if (
            record.status != AutomationStatus.TECHNICAL_FAILURE
            or record.technical_failure is None
            or record.current_stage == AutomationStage.MOCK_GOLDTIER
        ):
            return False
        requested = [
            place for place, event in enumerate(record.events)
            if event.code == ADVISORY_CONTINUATION_REQUESTED
        ]
        attempt = record.events[requested[-1] + 1:] if requested else []
        kinds = {event.event_type for event in attempt}
        return (
            AutomationEventType.AUTOMATION_TECHNICAL_FAILURE in kinds
            # A raised exception means the attempt got further, and a retry would lose it.
            and AutomationEventType.BUSINESS_EXCEPTION_RAISED not in kinds
            and not self.evidence_edit_is_frozen(case_id=record.case_id)
        )

    def advisory_continuation_pending(self, record: ZeroTouchAutomationRecord) -> bool:
        """D-124: a resume can continue this case. Reads only, never changes it."""

        return (
            self._held_by_advisory_review(record)
            or self._advisory_continuation_failed(record)
            or self._existing_confirmation_projection_due(record)
        )

    def release_advisory_holds(self) -> None:
        """D-124 S9: at startup, advisory holds continue towards target confirmation by themselves.

        Nothing is written to the target. A case already in technical failure is not retried,
        and one case that fails neither stops the others nor stops the backend from starting.
        """

        try:
            case_ids = [record.case_id for record in self._repository.list_records()]
        except Exception as exc:  # noqa: BLE001 - startup must survive a failed sweep.
            _LOGGER.warning("Advisory hold release skipped: %s", type(exc).__name__)
            return
        for case_id in case_ids:
            try:
                self._release_advisory_hold(case_id)
            except Exception as exc:  # noqa: BLE001 - /resume or the next startup can continue.
                _LOGGER.warning(
                    "Advisory hold release failed for case %s: %s", case_id, type(exc).__name__,
                )

    def _release_advisory_hold(self, case_id: UUID) -> None:
        with self._cases.case_lock(case_id):
            record = self._repository.get_for_case(case_id)
            if record is None:
                return
            if self._intake_reopen_interrupted(record):
                self._return_to_document_intake(record)
                return
            if self._advisory_continuation_interrupted(record):
                # Ownership saves its completion before it raises these two reviews, and that
                # stage never runs again, so a stop in between must not lose them.
                restored = (
                    self._raise_intelligence_blocker(record, self._intelligence_evaluator(case_id))
                    if self._intelligence_evaluator is not None
                    and record.status == AutomationStatus.RUNNING
                    and record.events[-1].event_type == AutomationEventType.OWNERSHIP_AUTOMATED
                    else None
                )
                self._warn_if_failed(restored or self.start(case_id=case_id))
                return
            if not self._held_by_advisory_review(record):
                return
            case = self._cases.get_case(case_id)
            clm = self._clm.get(case_id=case_id)
            assert case is not None and clm is not None
            self._warn_if_failed(self.start(
                case_id=case_id,
                refresh_document_checkpoint=True,
                expected_automation_id=record.automation_id,
                expected_automation_version=record.version,
                expected_clm_version=clm.version,
                expected_case_event_count=len(case.events),
                automatic_release=True,
            ))

    @staticmethod
    def _warn_if_failed(record: ZeroTouchAutomationRecord) -> None:
        if record.status == AutomationStatus.TECHNICAL_FAILURE:
            _LOGGER.warning("Advisory hold release ended in failure for case %s", record.case_id)

    @staticmethod
    def _intake_reopen_interrupted(record: ZeroTouchAutomationRecord) -> bool:
        """D-124 S9: the process stopped between the two saves of an intake reopen."""

        return (
            record.status == AutomationStatus.RESUMING
            and record.events[-1].code == DOCUMENT_INTAKE_REOPENED
        )

    def _advisory_continuation_interrupted(self, record: ZeroTouchAutomationRecord) -> bool:
        """D-124 S9: a case that has had a continuation stopped mid-pipeline.

        That may be the continuation or a later pipeline on the same case. Only evidence stages
        remain: a target write needs a confirmation, which freezes the case.
        """

        requested = [
            place for place, event in enumerate(record.events)
            if event.code == ADVISORY_CONTINUATION_REQUESTED
        ]
        return (
            bool(requested)
            and record.status in {AutomationStatus.RUNNING, AutomationStatus.RESUMING}
            and record.current_stage != AutomationStage.MOCK_GOLDTIER
            and not self.document_refresh_pending(record)
            and not self.evidence_edit_is_frozen(case_id=record.case_id)
            and not any(
                event.code == "DOCUMENT_REPLACEMENT_ACCEPTED"
                for event in record.events[requested[-1] + 1:]
            )
        )

    def _reopen_document_intake_locked(
        self, record: ZeroTouchAutomationRecord,
    ) -> ZeroTouchAutomationRecord:
        """D-124 S9: a failed document found past Document goes back through the legal route.

        The state table returns to intake only from Document, so the case first resumes there,
        as a document replacement does. Onboarding re-evaluates every blocker after the upload.
        """

        candidate = record.model_copy(deep=True)
        for item in candidate.active_exceptions:
            item.status = BusinessExceptionStatus.CANCELLED
            item.resolved_at = self._clock()
        candidate.completed_stages = tuple(
            stage for stage in candidate.completed_stages
            if stage in {AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH}
        )
        candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
        candidate.technical_failure = None
        candidate.status = AutomationStatus.RESUMING
        candidate.current_stage = AutomationStage.DOCUMENT
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code=DOCUMENT_INTAKE_REOPENED,
            message="A failed document must be uploaded again before onboarding continues.",
        )
        return self._return_to_document_intake(self._save(record, candidate))

    def _begin_advisory_continuation_locked(
        self, record: ZeroTouchAutomationRecord, *, automatic: bool = False,
    ) -> ZeroTouchAutomationRecord:
        """Record the request; a failed attempt reopens for one more try.

        Only an attempt that reached no target state reopens. Search is read-only, and every
        target write still needs its own confirmation.
        """

        candidate = record.model_copy(deep=True)
        if record.status == AutomationStatus.TECHNICAL_FAILURE:
            self._clm.retry_failed_search(case_id=record.case_id)
            candidate.status = AutomationStatus.RESUMING
            candidate.technical_failure = None
            candidate.metrics.final_outcome = None
            candidate.current_stage = _next_stage(
                candidate.completed_stages, order=_stage_order(candidate),
            )
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code=ADVISORY_CONTINUATION_REQUESTED,
            message=(
                ("The backend continued automatically" if automatic
                 else "An authorized user continued")
                + " with the ownership review open; nothing is "
                "sent to the target before its confirmation."
            ),
        )
        return self._save(record, candidate)

    def get(self, *, case_id: UUID) -> ZeroTouchAutomationRecord | None:
        """D-124: a read changes nothing, whoever reads."""

        return self._repository.get_for_case(case_id)

    def _require_partnership_agreement_match(
        self, case: OnboardingCase, declaration: ManualOwnershipDeclaration
    ) -> None:
        """D-101: a partnership's confirmed shares must equal its reviewed agreement."""
        partners = registry_partner_names(case.registry_acquisition)
        if not partners:
            return
        document = self._documents.get_document(
            case_id=case.case_id, document_id=declaration.evidence_document_id
        )
        names = {party.party_id: party.display_name for party in declaration.parties}
        issues = partnership_agreement_issues(
            registry_partners=partners,
            rows=agreement_rows(document) if document is not None else (),
            root_uen=case.entity.registration_number if case.entity is not None else "",
            confidence_threshold=float(case.policy_snapshot.idp_review_confidence_threshold),
            declared=tuple(
                (names[edge.child_party_id], edge.ownership_percent)
                for edge in declaration.relationships
            ),
        )
        if issues:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_PARTNERSHIP_AGREEMENT_MISMATCH",
                message=(
                    "The partnership agreement does not match the registry partners or the "
                    "confirmed shares; the case stays in review."
                ),
            )

    def submit_manual_ownership_evidence(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        declaration: ManualOwnershipDeclaration,
        expected_automation_version: int,
        expected_ownership_version: int,
        expected_case_event_count: int,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Revise pre-submission ownership through creator-reviewed, case-bound evidence."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            case = self._cases.get_case(case_id)
            clm_record = self._clm.get(case_id=case_id)
            current_ownership = self._ownership.get(case_id=case_id)
            if record.version != expected_automation_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_MANUAL_OWNERSHIP_STALE",
                    message="The onboarding case changed before manual evidence was accepted.",
                )
            if case is None or clm_record is None or current_ownership is None:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_MANUAL_OWNERSHIP_NOT_AVAILABLE",
                    message="The current ownership review is unavailable.",
                )
            if case.created_by_actor_id is None or case.created_by_actor_id != actor_id:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_OWNERSHIP_CREATOR_REQUIRED",
                    message="Only the current case creator may decide ownership evidence.",
                )
            if len(case.events) != expected_case_event_count:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_MANUAL_OWNERSHIP_STALE",
                    message="The onboarding case changed before manual evidence was accepted.",
                )
            if current_ownership.version != expected_ownership_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_MANUAL_OWNERSHIP_STALE",
                    message="The ownership analysis changed before manual evidence was accepted.",
                )
            ownership_blockers = [
                item for item in record.active_exceptions if item.stage == AutomationStage.OWNERSHIP
            ]
            if (
                declaration.case_id != case_id
                or record.status != AutomationStatus.WAITING_FOR_REVIEW
                or current_ownership.state
                not in {OwnershipAnalysisState.REVIEW_REQUIRED, OwnershipAnalysisState.ANALYZED}
                or case.goldtier_result is not None
                or clm_record.submission_snapshot is not None
                or clm_record.status == ClmStatus.SUBMITTING
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_MANUAL_OWNERSHIP_NOT_ALLOWED",
                    message=(
                        "Manual ownership evidence is accepted only for current "
                        "pre-submission ownership evidence."
                    ),
                )

            try:
                provider = ManualOwnershipEvidenceProvider(
                    declaration=declaration,
                    reviewed_by_actor_id=actor_id,
                    cases=self._cases,
                    documents=_CaseDocumentReader(self._documents, case_id),
                    reconciliation=self._reconciliation,
                    clock=self._clock,
                )
                if declaration.observed_document_versions != current_ownership.document_bindings:
                    raise ZeroTouchRequestError(
                        code="ZERO_TOUCH_MANUAL_OWNERSHIP_STALE",
                        message="Current document ownership evidence changed before the decision.",
                    )
                self._require_partnership_agreement_match(case, declaration)
                replacement = self._ownership.replace_review_required_source(
                    case_id=case_id,
                    provider=provider,
                    review_receipt=provider.review_receipt,
                    expected_version=expected_ownership_version,
                    before_replace=lambda: self._cases.invalidate_target_dispatch_confirmation(
                        case_id=case_id, expected_case_event_count=expected_case_event_count,
                    ),
                )
            except ManualOwnershipEvidenceError as exc:
                raise ZeroTouchRequestError(code=exc.code, message=exc.message) from None
            except OwnershipRequestError as exc:
                code = (
                    "ZERO_TOUCH_MANUAL_OWNERSHIP_STALE"
                    if exc.code == "OWNERSHIP_MANUAL_REPLACEMENT_STALE"
                    else exc.code
                )
                raise ZeroTouchRequestError(code=code, message=exc.public_message) from None
            except OwnershipInfrastructureError as exc:
                raise ZeroTouchInfrastructureError(
                    case_id=case_id,
                    automation_id=record.automation_id,
                    code=exc.code,
                    message=exc.public_message,
                ) from None
            try:
                self._clm.refresh_pre_submission_evidence(case_id=case_id)
            except ClmRequestError as exc:
                raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
            except ClmInfrastructureError as exc:
                raise ZeroTouchInfrastructureError(
                    case_id=case_id, automation_id=record.automation_id,
                    code=exc.code, message=exc.public_message,
                ) from None
            # D-121: an advisory review does not hold the case, so it continues as analysed.
            held = (
                replacement.state != OwnershipAnalysisState.ANALYZED
                and not self._ownership.clears_review(replacement)
            )
            candidate = record.model_copy(deep=True)
            resolved_at = self._clock()
            for item in candidate.active_exceptions:
                if (
                    item.stage == AutomationStage.OWNERSHIP
                    or (
                        item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
                        # A retained creator-owned graph replacement invalidates
                        # every earlier local review, including one bound before a
                        # subsequent classification revision. Recompute before send.
                        and item.evidence_version.startswith("target-confirmation:")
                    )
                ):
                    item.status = (
                        BusinessExceptionStatus.CANCELLED
                        if held
                        and item.exception_type
                        == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
                        else BusinessExceptionStatus.RESOLVED
                    )
                    item.resolved_at = resolved_at
            candidate.completed_stages = tuple(
                stage
                for stage in candidate.completed_stages
                if stage
                in {
                    AutomationStage.REGISTRY,
                    AutomationStage.GOLDTIER_SEARCH,
                    AutomationStage.DOCUMENT,
                }
            )
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += len(ownership_blockers)
            if held:
                # The graph and receipt are retained even for a safe 409. Bind the
                # current ownership hold before returning that failed-closed result.
                candidate = self._raise_ownership_exception(candidate, replacement, persist=False)
                candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
                self._save(record, candidate)
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_MANUAL_OWNERSHIP_REVIEW_REQUIRED",
                    message="The replacement ownership evidence still requires review.",
                )
            remaining_blockers = candidate.active_exceptions
            if remaining_blockers:
                candidate.status = AutomationStatus.WAITING_FOR_REVIEW
                candidate.current_stage = _earliest_open_stage(candidate)
            else:
                candidate.status = AutomationStatus.RESUMING
                candidate.current_stage = AutomationStage.OWNERSHIP
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.BUSINESS_EXCEPTION_RESOLVED,
                outcome=EventOutcome.SUCCEEDED,
                code="MANUAL_OWNERSHIP_EVIDENCE_ACCEPTED",
                message="Creator-reviewed ownership evidence revised the retained source.",
            )
            saved = self._save(record, candidate)
            if saved.active_exceptions:
                return saved
            return self._advance_locked(case_id=case_id)

    def confirm_government_status(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        document_id: UUID,
        document_event_count: int,
        expected_automation_version: int,
        expected_case_event_count: int,
        founding_statute: str,
        government_body_type: GovernmentBodyType,
        statute_section: str | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """D-101: the RM confirms Government status from one exact reviewed document.

        D-125: the RM-entered founding statute must equal the document's Founding
        Instrument after normalisation; otherwise nothing is saved.
        """

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            case = self._cases.get_case(case_id)
            clm_record = self._clm.get(case_id=case_id)
            if (
                record.version != expected_automation_version
                or case is None
                or len(case.events) != expected_case_event_count
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_GOVERNMENT_STATUS_STALE",
                    message="The onboarding case changed before Government status was confirmed.",
                )
            if case.created_by_actor_id is None or case.created_by_actor_id != actor_id:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_GOVERNMENT_STATUS_CREATOR_REQUIRED",
                    message="Only the current case creator may confirm Government status.",
                )
            open_hold = any(
                item.exception_type == BusinessExceptionType.GOVERNMENT_STATUS_REQUIRED
                for item in record.active_exceptions
            )
            if (
                not government_profile_applies(case)
                or not open_hold
                or record.status != AutomationStatus.WAITING_FOR_REVIEW
                or clm_record is None
                or case.goldtier_result is not None
                or clm_record.submission_snapshot is not None
                or clm_record.status == ClmStatus.SUBMITTING
                or self._cases.has_retained_target_execution(case_id)
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_GOVERNMENT_STATUS_NOT_ALLOWED",
                    message=(
                        "Government status is confirmed only for a current pre-submission "
                        "Government case."
                    ),
                )
            documents = [
                item
                for item in self._documents.list_documents(case_id=case_id)
                if item.is_current_evidence
            ]
            evidence = government_status_evidence(
                case,
                documents,
                confidence_threshold=float(case.policy_snapshot.idp_review_confidence_threshold),
            )
            if (
                evidence is None
                or evidence.document_id != document_id
                or evidence.document_event_count != document_event_count
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_GOVERNMENT_STATUS_EVIDENCE_REQUIRED",
                    message=(
                        "A current reviewed document with every Government status label "
                        "is required."
                    ),
                )
            if not statute_matches(founding_statute, evidence.founding_instrument):
                raise ZeroTouchRequestError(
                    code="GOVERNMENT_STATUTE_MISMATCH",
                    message=(
                        "The statute entered does not match the Founding Instrument on the "
                        "reviewed document."
                    ),
                )
            try:
                self._cases.confirm_government_status(
                    case_id=case_id,
                    actor_id=actor_id,
                    expected_case_event_count=expected_case_event_count,
                    document_id=evidence.document_id,
                    document_event_count=evidence.document_event_count,
                    evidence_fingerprint=evidence.evidence_fingerprint,
                    founding_statute=founding_statute,
                    statute_section=statute_section,
                    government_body_type=government_body_type,
                )
                self._clm.refresh_pre_submission_evidence(case_id=case_id)
            except ValueError:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_GOVERNMENT_STATUS_STALE",
                    message="The onboarding case changed before Government status was confirmed.",
                ) from None
            except ClmRequestError as exc:
                raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
            except ClmInfrastructureError as exc:
                raise ZeroTouchInfrastructureError(
                    case_id=case_id, automation_id=record.automation_id,
                    code=exc.code, message=exc.public_message,
                ) from None
            candidate = record.model_copy(deep=True)
            resolved_at = self._clock()
            for item in candidate.active_exceptions:
                if item.exception_type == BusinessExceptionType.GOVERNMENT_STATUS_REQUIRED or (
                    item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
                    and item.evidence_version.startswith("target-confirmation:")
                ):
                    item.status = BusinessExceptionStatus.RESOLVED
                    item.resolved_at = resolved_at
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += 1
            if candidate.active_exceptions:
                candidate.status = AutomationStatus.WAITING_FOR_REVIEW
                candidate.current_stage = _earliest_open_stage(candidate)
            else:
                candidate.status = AutomationStatus.RESUMING
                candidate.current_stage = AutomationStage.OWNERSHIP
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.BUSINESS_EXCEPTION_RESOLVED,
                outcome=EventOutcome.SUCCEEDED,
                code="GOVERNMENT_STATUS_CONFIRMED",
                message="The RM confirmed Government status from a reviewed document.",
            )
            saved = self._save(record, candidate)
            if saved.active_exceptions:
                return saved
            return self._advance_locked(case_id=case_id)

    def _raise_target_confirmation_exception(
        self, record: ZeroTouchAutomationRecord, clm: ClmOrchestrationRecord
    ) -> ZeroTouchAutomationRecord:
        case = self._cases.get_case(record.case_id)
        assert case is not None
        return self._add_exception(
            record,
            exception_type=BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
            stage=AutomationStage.READINESS,
            blocker_code="TARGET_CONFIRMATION_REQUIRED",
            explanation=(
                "Review the prepared submission and confirm Send before any "
                "target mutation."
            ),
            evidence_version=f"target-confirmation:{clm.version}:{len(case.events)}",
            evidence=(),
            actions=(),
        )

    def _sync_document_target_classification(self, case_id: UUID) -> None:
        clm = self._clm.get(case_id=case_id)
        if (
            clm is None
            or clm.submission_snapshot is not None
            or self._cases.has_retained_target_execution(case_id)
        ):
            return
        before = self._cases.get_case(case_id)
        assert before is not None
        if (before.policy_snapshot.goldtier_target is None
            or before.target_dispatch_confirmation is not None):
            return
        after = self._cases.bind_goldtier_case_classification(
            case_id=case_id,
            document_selections=self._documents.assess_target_classification(
                case_id=case_id
            ).candidates,
        )
        if len(after.events) != len(before.events):
            self._clm.refresh_target_classification(case_id=case_id)

    def bind_target_classification(
        self,
        *,
        case_id: UUID,
        kyc_customer_type: str,
        client_segment: str,
        expected_classification_evidence_fingerprint: str | None = None,
        expected_automation_version: int | None = None,
        expected_case_event_count: int | None = None,
        actor_id: str | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Bind a case-only target decision and resume only its waiting checkpoint."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if (
                expected_automation_version is not None
                and record.version != expected_automation_version
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_TARGET_CLASSIFICATION_STALE",
                    message="The onboarding case changed before target classification.",
                )
            clm_record = self._clm.get(case_id=case_id)
            if clm_record is None or self.evidence_edit_is_frozen(case_id=case_id):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_TARGET_CLASSIFICATION_FROZEN",
                    message="Target classification is already frozen for submission.",
                )
            assessment = self._documents.assess_target_classification(case_id=case_id)
            if (
                assessment.trusted_evidence_present
                and expected_classification_evidence_fingerprint is None
            ) or (
                expected_classification_evidence_fingerprint is not None
                and expected_classification_evidence_fingerprint != assessment.evidence_fingerprint
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_TARGET_CLASSIFICATION_STALE",
                    message=(
                        "Classification evidence changed; review the current evidence "
                        "before saving."
                    ),
                )
            try:
                self._cases.bind_goldtier_case_classification(
                    case_id=case_id,
                    kyc_customer_type=kyc_customer_type,
                    client_segment=client_segment,
                    expected_case_event_count=expected_case_event_count,
                    classification_assessment=assessment,
                    actor_id=actor_id,
                )
                self._clm.refresh_target_classification(case_id=case_id)
            except (ValueError, ClmRequestError) as exc:
                code = (
                    exc.code
                    if isinstance(exc, ClmRequestError)
                    else "ZERO_TOUCH_TARGET_CLASSIFICATION_INVALID"
                )
                message = exc.public_message if isinstance(exc, ClmRequestError) else str(exc)
                raise ZeroTouchRequestError(code=code, message=message) from None

            refreshed_classification = self._clm.get(case_id=case_id)
            if (
                refreshed_classification is not None
                and ClmBlockerCode.GOLDTIER_CLASSIFICATION_REQUIRED
                in refreshed_classification.readiness.blockers
            ):
                return record
            classification_exceptions = [
                item
                for item in record.active_exceptions
                if item.exception_type == BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED
            ]
            confirmation_exceptions = [
                item for item in record.active_exceptions
                if item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
            ]
            if not classification_exceptions and not confirmation_exceptions:
                return record
            candidate = record.model_copy(deep=True)
            resolved_at = self._clock()
            for item in candidate.active_exceptions:
                if item.exception_type == BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED:
                    item.status = BusinessExceptionStatus.RESOLVED
                    item.resolved_at = resolved_at
                    self._retain_resolution_actor(item, actor_id)
                elif item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED:
                    item.status = BusinessExceptionStatus.CANCELLED
                    item.resolved_at = resolved_at
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += len(classification_exceptions)
            if not candidate.active_exceptions:
                candidate.status = AutomationStatus.RESUMING
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.TARGET_CLASSIFICATION_RECORDED,
                outcome=EventOutcome.SUCCEEDED,
                code="TARGET_CLASSIFICATION_RECORDED",
                message="Case-specific target classifications were retained with POC authority.",
            )
            saved = self._save(record, candidate)
            if saved.active_exceptions or saved.current_stage != AutomationStage.READINESS:
                return saved
            refreshed = self._clm.get(case_id=case_id)
            if refreshed is not None and not refreshed.readiness.blockers:
                return self._raise_target_confirmation_exception(saved, refreshed)
            return self._advance_locked(case_id=case_id)

    def rebind_case_policy_snapshot(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        rationale: str,
        expected_automation_version: int,
        expected_clm_version: int,
        expected_case_event_count: int,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Rebind accepted SG POC constants and resume only the readiness dependency."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            case = self._cases.get_case(case_id)
            clm_record = self._clm.get(case_id=case_id)
            if (
                record.version != expected_automation_version
                or case is None
                or len(case.events) != expected_case_event_count
                or clm_record is None
                or clm_record.version != expected_clm_version
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_POLICY_REBIND_STALE",
                    message="The onboarding case changed before policy rebind.",
                )
            if (
                record.status != AutomationStatus.WAITING_FOR_REVIEW
                or record.current_stage != AutomationStage.READINESS
                or clm_record.submission_snapshot is not None
                or clm_record.execution_receipt is not None
                or case.target_dispatch_confirmation is not None
                or case.goldtier_result is not None
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_POLICY_REBIND_NOT_ALLOWED",
                    message="Policy rebind is accepted only for a pre-submission readiness case.",
                )
            previous_revision = case.policy_snapshot_revision
            try:
                rebound_case = self._cases.rebind_case_policy_snapshot(
                    case_id=case_id,
                    actor_id=actor_id,
                    rationale=rationale,
                    expected_case_event_count=expected_case_event_count,
                )
            except ValueError as exc:
                message = str(exc)
                code = (
                    "ZERO_TOUCH_POLICY_REBIND_STALE"
                    if "changed before" in message
                    else "ZERO_TOUCH_POLICY_REBIND_NOT_ALLOWED"
                )
                raise ZeroTouchRequestError(code=code, message=message) from None
            if rebound_case.policy_snapshot_revision == previous_revision:
                return record
            try:
                self._clm.refresh_target_classification(case_id=case_id)
            except ClmRequestError as exc:
                raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None

            candidate = record.model_copy(deep=True)
            affected_types = {
                BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED,
                BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
            }
            resolved_at = self._clock()
            affected_count = 0
            for item in candidate.active_exceptions:
                if item.exception_type in affected_types:
                    item.status = BusinessExceptionStatus.RESOLVED
                    item.resolved_at = resolved_at
                    affected_count += 1
            remaining = candidate.active_exceptions
            candidate.metrics.human_interventions += 1
            candidate.metrics.exceptions_resolved += affected_count
            if remaining:
                candidate.status = AutomationStatus.WAITING_FOR_REVIEW
                candidate.current_stage = _earliest_open_stage(candidate)
            else:
                candidate.status = AutomationStatus.RESUMING
                candidate.current_stage = AutomationStage.READINESS
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.POLICY_SNAPSHOT_REBOUND,
                outcome=EventOutcome.SUCCEEDED,
                code="SG_POC_POLICY_SNAPSHOT_REBOUND",
                message="Accepted SG POC target constants were rebound to the case.",
            )
            saved = self._save(record, candidate)
            if saved.active_exceptions:
                return saved
            return self._advance_locked(case_id=case_id)

    def confirm_existing_customer(
        self, *, case_id: UUID, actor_id: str, search_request_id: UUID,
        expected_automation_version: int, expected_clm_version: int,
        expected_case_event_count: int, rationale: str,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Record a case-bound identity decision without advancing or dispatching."""
        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if record.version != expected_automation_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXISTING_CUSTOMER_STALE",
                    message="The onboarding evidence changed before confirmation.",
                )
            if (
                record.status != AutomationStatus.WAITING_FOR_REVIEW
                or record.current_stage != AutomationStage.GOLDTIER_SEARCH
                or not any(item.stage == AutomationStage.GOLDTIER_SEARCH
                           for item in record.active_exceptions)
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_EXISTING_CUSTOMER_NOT_ALLOWED",
                    message="Existing-customer confirmation is not accepted at this stage.",
                )
            try:
                self._clm.confirm_existing_customer(
                    case_id=case_id, actor_id=actor_id, search_request_id=search_request_id,
                    expected_clm_version=expected_clm_version,
                    expected_case_event_count=expected_case_event_count, rationale=rationale,
                )
            except ClmRequestError as exc:
                raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
            return self._project_existing_confirmation_locked(record)

    def _existing_confirmation_projection_due(self, record: ZeroTouchAutomationRecord) -> bool:
        """A retained identity decision whose stage projection was interrupted. Reads only."""
        if (
            record.status != AutomationStatus.WAITING_FOR_REVIEW
            or record.current_stage != AutomationStage.GOLDTIER_SEARCH
        ):
            return False
        clm = self._clm.get(case_id=record.case_id)
        checkpoint = clm.target_search_checkpoint if clm is not None else None
        return (
            checkpoint is not None
            and checkpoint.confirmation is not None
            and self._clm.existing_confirmation_is_current(case_id=record.case_id)
            and checkpoint.status == GoldTierSearchCheckpointStatus.COMPLETED
            and any(
                item.stage == AutomationStage.GOLDTIER_SEARCH
                and item.evidence_version == f"goldtier-search:{checkpoint.request_id}"
                for item in record.active_exceptions
            )
        )

    def _project_existing_confirmation_locked(
        self, record: ZeroTouchAutomationRecord,
    ) -> ZeroTouchAutomationRecord:
        """Recover only the local stage projection after a retained identity decision."""
        if not self._existing_confirmation_projection_due(record):
            return record
        clm = self._clm.get(case_id=record.case_id)
        assert clm is not None and clm.target_search_checkpoint is not None
        receipt = clm.target_search_checkpoint.confirmation
        assert receipt is not None
        candidate = record.model_copy(deep=True)
        if candidate.started_at is None:
            candidate.started_at = receipt.confirmed_at
        for item in candidate.active_exceptions:
            if item.stage == AutomationStage.GOLDTIER_SEARCH:
                item.status = BusinessExceptionStatus.RESOLVED
                item.resolved_at = receipt.confirmed_at
                self._retain_resolution_actor(item, receipt.actor_id)
                candidate.metrics.exceptions_resolved += 1
        if AutomationStage.GOLDTIER_SEARCH not in candidate.completed_stages:
            candidate.completed_stages += (AutomationStage.GOLDTIER_SEARCH,)
            candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
        candidate.metrics.human_interventions += 1
        candidate.status = (
            AutomationStatus.WAITING_FOR_REVIEW if candidate.active_exceptions
            else AutomationStatus.PENDING_INPUTS
        )
        candidate.current_stage = (
            _earliest_open_stage(candidate) if candidate.active_exceptions
            else _next_stage(candidate.completed_stages, order=_stage_order(candidate))
        )
        candidate = self._append_event(
            candidate, event_type=AutomationEventType.GOLDTIER_SEARCH_COMPLETED,
            outcome=EventOutcome.SUCCEEDED, code="EXISTING_GOLDTIER_CUSTOMER_CONFIRMED",
            message="The creator confirmed retained customer identity; no target call ran.",
        )
        return self._save(record, candidate)

    def confirm_target_dispatch(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        expected_automation_version: int,
        expected_clm_version: int,
        expected_case_event_count: int,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Confirm the frozen review and resume the same case from readiness."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if record.version != expected_automation_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_TARGET_CONFIRMATION_STALE",
                    message="The onboarding case changed before target confirmation.",
                )
            confirmation_exceptions = [
                item
                for item in record.active_exceptions
                if item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
            ]
            if not confirmation_exceptions or record.current_stage != AutomationStage.READINESS:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_TARGET_CONFIRMATION_NOT_ALLOWED",
                    message="Target confirmation is not accepted at the current stage.",
                )
            if self._workflow_send_hold is not None:  # D-123: absent unless switched on.
                hold_code = self._workflow_send_hold(case_id)
                if hold_code is not None:
                    raise ZeroTouchRequestError(
                        code=hold_code,
                        message="Complete and confirm the added workflow stages before sending.",
                    )
            try:
                rechecked_clm = self._clm.confirm_target_dispatch(
                    case_id=case_id,
                    actor_id=actor_id,
                    expected_clm_version=expected_clm_version,
                    expected_case_event_count=expected_case_event_count,
                    reauthorize=reauthorize,
                )
            except ClmRequestError as exc:
                raise ZeroTouchRequestError(
                    code=exc.code,
                    message=exc.public_message,
                ) from None
            confirmed_case = self._cases.get_case(case_id)
            if (
                confirmed_case is None
                or confirmed_case.target_dispatch_confirmation is None
            ):
                return self._retain_revised_confirmation_review(record, rechecked_clm)

            candidate = record.model_copy(deep=True)
            resolved_at = self._clock()
            for item in candidate.active_exceptions:
                if item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED:
                    item.status = BusinessExceptionStatus.RESOLVED
                    item.resolved_at = resolved_at
                    candidate.metrics.exceptions_resolved += 1
            candidate.status = AutomationStatus.RESUMING
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.TARGET_DISPATCH_CONFIRMED,
                outcome=EventOutcome.SUCCEEDED,
                code="TARGET_DISPATCH_CONFIRMED",
                message="A local-POC operator confirmed the frozen target review.",
            )
            saved = self._save(record, candidate)
            completed = self._complete_stage(
                saved,
                stage=AutomationStage.READINESS,
                event_type=AutomationEventType.READINESS_AUTOMATED,
                code="READINESS_CONFIRMED",
                message="Authoritative readiness was confirmed for target dispatch.",
                started_at=resolved_at,
            )
            if reauthorize is not None:
                reauthorize()
            return self._advance_locked(case_id=completed.case_id)

    def _retain_revised_confirmation_review(
        self,
        record: ZeroTouchAutomationRecord,
        clm_record: ClmOrchestrationRecord,
    ) -> ZeroTouchAutomationRecord:
        """Replace a superseded confirmation action with the fresh Search truth."""

        candidate = record.model_copy(deep=True)
        now = self._clock()
        for item in candidate.active_exceptions:
            if item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED:
                item.status = BusinessExceptionStatus.CANCELLED
                item.resolved_at = now
        checkpoint = clm_record.target_search_checkpoint
        candidate.status = AutomationStatus.WAITING_FOR_REVIEW
        candidate.current_stage = AutomationStage.GOLDTIER_SEARCH
        candidate = self._append_event(
            candidate,
            event_type=(
                AutomationEventType.GOLDTIER_SEARCH_REVIEW_REQUIRED
                if checkpoint is not None
                and checkpoint.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                else AutomationEventType.GOLDTIER_SEARCH_FAILED
                if checkpoint is not None
                and checkpoint.status == GoldTierSearchCheckpointStatus.FAILED
                else AutomationEventType.GOLDTIER_SEARCH_COMPLETED
            ),
            outcome=(
                EventOutcome.REVIEW_REQUIRED
                if checkpoint is not None
                and checkpoint.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                else EventOutcome.FAILED
                if checkpoint is not None
                and checkpoint.status == GoldTierSearchCheckpointStatus.FAILED
                else EventOutcome.SUCCEEDED
            ),
            code=(checkpoint.code if checkpoint is not None else "GOLDTIER_SEARCH_REVISED"),
            message="Confirmation-time Search changed the proposed target path.",
        )
        if checkpoint is None:
            return self._technical_failure(
                candidate,
                stage=AutomationStage.GOLDTIER_SEARCH,
                code="GOLDTIER_SEARCH_FAILED",
                message="Confirmation-time Search produced no retained checkpoint.",
            )
        if checkpoint.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED:
            return self._add_exception(
                candidate,
                exception_type=BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED,
                stage=AutomationStage.GOLDTIER_SEARCH,
                blocker_code=checkpoint.code or "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
                explanation=(
                    "Confirmation-time Search changed the proposed target identity; "
                    "all target mutations remain blocked."
                ),
                evidence_version=f"goldtier-search:{checkpoint.request_id}",
                evidence=(),
                actions=(),
            )
        if checkpoint.status == GoldTierSearchCheckpointStatus.FAILED:
            return self._technical_failure(
                candidate,
                stage=AutomationStage.GOLDTIER_SEARCH,
                code=checkpoint.code or "GOLDTIER_SEARCH_FAILED",
                message="Confirmation-time Search failed; target mutations remain blocked.",
            )
        return self._add_exception(
            candidate,
            exception_type=BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
            stage=AutomationStage.READINESS,
            blocker_code="TARGET_CONFIRMATION_REQUIRED",
            explanation=(
                "Confirmation-time Search changed the frozen target review; the revised "
                "operation plan requires confirmation."
            ),
            evidence_version=f"target-confirmation:{clm_record.version}",
            evidence=(),
            actions=(),
        )

    def repair_initial_identity_and_recheck(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        legal_name: str,
        registration_number: str,
        country_of_incorporation: str,
        expected_automation_version: int,
        expected_clm_version: int,
        expected_case_event_count: int,
        verify_registry: bool = False,
        identity_choice: Literal["ENTERED", "DOCUMENT", "OTHER"] = "OTHER",
        document_id: UUID | None = None,
        expected_document_event_count: int | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Repair/recheck the same pre-submission case without target mutation."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if record.version != expected_automation_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_IDENTITY_RECHECK_STALE",
                    message="The onboarding case changed before identity recheck.",
                )
            clm_record = self._clm.get(case_id=case_id)
            if clm_record is None or clm_record.version != expected_clm_version:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_IDENTITY_RECHECK_STALE",
                    message="The CLM case changed before identity recheck.",
                )
            if clm_record.submission_snapshot is not None:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_IDENTITY_RECHECK_FROZEN",
                    message="Identity Search is already frozen for submission.",
                )
            checkpoint = clm_record.target_search_checkpoint
            current_case = self._cases.get_case(case_id)
            missing_identity_repair = bool(
                checkpoint is None
                and current_case is not None
                and current_case.initial_identity is None
                and current_case.error is not None
                and current_case.error.code == "INITIAL_IDENTITY_INCOMPLETE"
            )
            if not missing_identity_repair and not verify_registry and (
                checkpoint is None
                or checkpoint.status
                not in {
                    GoldTierSearchCheckpointStatus.COMPLETED,
                    GoldTierSearchCheckpointStatus.FAILED,
                    GoldTierSearchCheckpointStatus.REVIEW_REQUIRED,
                }
            ):
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_IDENTITY_RECHECK_NOT_ALLOWED",
                    message="Identity editing is not accepted at the current stage.",
                )
            if record.status == AutomationStatus.COMPLETED:
                raise ZeroTouchRequestError(
                    code="ZERO_TOUCH_IDENTITY_RECHECK_FROZEN",
                    message="Completed case identity is frozen.",
                )
            if verify_registry:
                if current_case is None:
                    raise ZeroTouchRequestError(
                        code="ONBOARDING_CASE_NOT_FOUND",
                        message="The onboarding case was not found."
                    )
                if identity_choice == "ENTERED" and (
                    registration_number.strip().upper() != current_case.requested_uen
                ):
                    raise ZeroTouchRequestError(
                        code="IDENTITY_CHOICE_INVALID", message="The entered UEN choice changed."
                    )
                if identity_choice == "DOCUMENT":
                    document = next((item for item in self._current_documents(case_id)
                                     if item.document_id == document_id), None)
                    field = next((item for item in document.fields
                                  if item.field_key == DocumentFieldKey.REGISTRATION_NUMBER), None
                                 ) if document is not None else None
                    value = (field.reviewed_value or field.normalized_value) if field else None
                    if (document is None or len(document.events) != expected_document_event_count
                        or field is None or value is None
                        or not is_eligible_singapore_uen(value.strip().upper())
                        or value.strip().upper() != registration_number.strip().upper()
                        or field.review_status == FieldReviewStatus.REJECTED
                        or (field.review_status == FieldReviewStatus.PENDING
                            and field.confidence
                            < current_case.policy_snapshot.idp_review_confidence_threshold)
                    ):
                        raise ZeroTouchRequestError(
                            code="IDENTITY_DOCUMENT_CHOICE_STALE",
                            message=(
                                "The document UEN is unavailable or changed; refresh the evidence."
                            ),
                        )
            changed_uen = bool(current_case and
                               current_case.requested_uen != registration_number.strip().upper())
            failure_base = record.model_copy(deep=True)
            failure_base.status = AutomationStatus.RESUMING
            failure_base.completed_stages = ()
            failure_base.metrics.automated_stages_completed = 0
            failure_base.technical_failure = None
            try:
                self._cases.repair_initial_identity_and_recheck(
                    case_id=case_id,
                    actor_id=actor_id,
                    legal_name=legal_name,
                    registration_number=registration_number,
                    country_of_incorporation=country_of_incorporation,
                    expected_case_event_count=expected_case_event_count,
                    verify_registry=verify_registry,
                    identity_choice=identity_choice,
                    source_document_id=document_id if identity_choice == "DOCUMENT" else None,
                    source_document_event_count=(
                        expected_document_event_count if identity_choice == "DOCUMENT" else None
                    ),
                )
                refreshed = self._clm.refresh_initial_search_after_recheck(
                    case_id=case_id,
                    expected_clm_version=expected_clm_version,
                )
            except OnboardingInfrastructureError as exc:
                self._clm.refresh_initial_search_after_recheck(
                    case_id=case_id, expected_clm_version=expected_clm_version
                )
                failed = self._technical_failure(
                    failure_base, stage=AutomationStage.REGISTRY,
                    code=exc.code, message=exc.public_message,
                )
                raise ZeroTouchInfrastructureError(
                    case_id=failed.case_id, automation_id=failed.automation_id,
                    code=exc.code, message=exc.public_message,
                ) from None
            except (ValueError, ClmRequestError) as exc:
                raise ZeroTouchRequestError(
                    code=(
                        exc.code
                        if isinstance(exc, ClmRequestError)
                        else "ZERO_TOUCH_IDENTITY_RECHECK_INVALID"
                    ),
                    message=(exc.public_message if isinstance(exc, ClmRequestError) else str(exc)),
                ) from None

            acquired_case = self._cases.get_case(case_id)
            if (
                acquired_case is not None
                and acquired_case.state == WorkflowState.FAILED
                and acquired_case.error is not None
            ):
                return self._technical_failure(
                    failure_base, stage=AutomationStage.REGISTRY,
                    code=acquired_case.error.code, message=acquired_case.error.message,
                )

            candidate = record.model_copy(deep=True)
            documents_available = bool(self._current_documents(case_id))
            for item in candidate.active_exceptions:
                obsolete_registry_dependency = (
                    verify_registry
                    and self._is_obsolete_registry_ownership_exception(case_id, item)
                )
                if (
                    obsolete_registry_dependency
                    or item.stage == AutomationStage.GOLDTIER_SEARCH
                    or (verify_registry and documents_available
                        and item.stage == AutomationStage.DOCUMENT)
                    or (changed_uen and item.stage in {
                        AutomationStage.DOCUMENT, AutomationStage.OWNERSHIP,
                        AutomationStage.READINESS
                    })
                    or (
                        item.stage == AutomationStage.REGISTRY
                        and acquired_case is not None
                        and acquired_case.state == WorkflowState.VALIDATED
                        and acquired_case.registry_acquisition is not None
                    )
                    or item.blocker_code == "INITIAL_IDENTITY_INCOMPLETE"
                    or item.exception_type
                    == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
                ):
                    item.status = BusinessExceptionStatus.CANCELLED
                    item.resolved_at = self._clock()
            if (
                acquired_case is not None
                and acquired_case.registry_acquisition is None
                and acquired_case.error is not None
                and acquired_case.error.code in {
                    "ACRA_ENTITY_NOT_FOUND",
                    "GOVERNMENT_IDENTITY_NOT_FOUND",
                    "ENTITY_CATEGORY_MISMATCH",
                    "UEN_ENTITY_TYPE_UNSUPPORTED",
                }
            ):
                for item in candidate.active_exceptions:
                    if item.stage == AutomationStage.REGISTRY:
                        item.status = BusinessExceptionStatus.CANCELLED
                        item.resolved_at = self._clock()
                candidate.completed_stages = ()
                candidate.metrics.automated_stages_completed = 0
                candidate.technical_failure = None
                candidate.metrics.final_outcome = None
                candidate = self._add_exception(
                    candidate, exception_type=BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
                    stage=AutomationStage.REGISTRY, blocker_code=acquired_case.error.code,
                    explanation="Required registry evidence is unavailable.",
                    evidence_version=f"case:{case_id}:{len(acquired_case.events)}",
                    evidence=(), actions=(), persist=False,
                )
                return self._save(record, candidate)
            if verify_registry and documents_available:
                try:
                    self._documents.refresh_current_comparisons(case_id=case_id)
                    reconciliation = self._reconciliation.reconcile_current(case_id=case_id)
                    if identity_choice == "ENTERED":
                        for discrepancy in reconciliation.open_discrepancies:
                            if (discrepancy.field_name
                                == ReconciliationField.REGISTRATION_IDENTIFIER
                                and ReconciliationDecisionAction.KEEP_REGISTRY_VALUE
                                in discrepancy.allowed_actions):
                                reconciliation = self._reconciliation.resolve_discrepancy(
                                    case_id=case_id, discrepancy_id=discrepancy.discrepancy_id,
                                    action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
                                    expected_version=reconciliation.version,
                                    evidence_fingerprint=discrepancy.evidence_fingerprint,
                                )
                except (DocumentRequestError, ReconciliationRequestError) as exc:
                    raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
                except (
                    DocumentProcessingInfrastructureError, ReconciliationInfrastructureError,
                ) as exc:
                    raise ZeroTouchInfrastructureError(
                        case_id=case_id, automation_id=record.automation_id,
                        code=exc.code, message=exc.public_message,
                    ) from None
            repaired_case = self._cases.get_case(case_id)
            search_completed = bool(
                refreshed.target_search_checkpoint is not None
                and refreshed.target_search_checkpoint.status
                == GoldTierSearchCheckpointStatus.COMPLETED
                and repaired_case is not None
                and repaired_case.state == WorkflowState.VALIDATED
                and repaired_case.entity is not None
            )
            registry_completed = bool(
                repaired_case is not None
                and repaired_case.state == WorkflowState.VALIDATED
                and repaired_case.entity is not None
            )
            candidate.completed_stages = (
                (AutomationStage.REGISTRY,) if registry_completed else ()
            )
            remaining_exceptions = candidate.active_exceptions
            if remaining_exceptions and search_completed:
                candidate.completed_stages = (
                    AutomationStage.REGISTRY,
                    AutomationStage.GOLDTIER_SEARCH,
                )
                candidate.metrics.automated_stages_completed = len(
                    candidate.completed_stages
                )
            candidate.status = (
                AutomationStatus.WAITING_FOR_REVIEW
                if remaining_exceptions
                else AutomationStatus.RESUMING
            )
            candidate.current_stage = (
                _earliest_open_stage(candidate)
                if remaining_exceptions
                else AutomationStage.GOLDTIER_SEARCH
            )
            candidate.started_at = candidate.started_at or self._clock()
            candidate.technical_failure = None
            candidate.metrics.final_outcome = None
            candidate = self._append_event(
                candidate,
                event_type=AutomationEventType.AUTOMATION_RESUMING,
                outcome=EventOutcome.SUCCEEDED,
                code="IDENTITY_RECHECK_RETAINED",
                message="Authorized identity repair and read-only Search recheck were retained.",
            )
            saved = self._save(record, candidate)
            if verify_registry and documents_available:
                return self._advance_locked(case_id=case_id)
            if remaining_exceptions:
                return saved
            if search_completed:
                completed = self._complete_stage(
                    saved,
                    stage=AutomationStage.GOLDTIER_SEARCH,
                    event_type=AutomationEventType.GOLDTIER_SEARCH_COMPLETED,
                    code="GOLDTIER_SEARCH_RECHECK_COMPLETED",
                    message="Authorized read-only GoldTier Search recheck completed.",
                    started_at=self._clock(),
                )
                return self._advance_locked(case_id=completed.case_id)
            if refreshed.target_search_checkpoint is None:
                return saved
            return self._advance_locked(case_id=case_id)

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
        actor_id: str | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Resolve current evidence once and automatically resume from the checkpoint."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
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
                reconciliation_version, fingerprint = _parse_reconciliation_evidence_version(
                    item.evidence_version
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
                    actor_id=actor_id,
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
            self._retain_resolution_actor(resolved, actor_id)
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
        actor_id: str | None = None,
        reauthorize: Callable[[], None] | None = None,
    ) -> ZeroTouchAutomationRecord:
        """Resolve one case-bound discrepancy through the typed backend authority."""

        with self._cases.case_lock(case_id):
            if reauthorize is not None:
                reauthorize()
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
                actor_id=actor_id,
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
        actor_id: str | None = None,
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
                if exc.code
                in {
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
        self._retain_resolution_actor(resolved, actor_id)
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
                entry.discrepancy_id: entry for entry in reconciliation.open_discrepancies
            }
            for active in candidate.active_exceptions:
                remaining_discrepancy = discrepancies_by_id.get(active.exception_id)
                if remaining_discrepancy is None:
                    continue
                active.evidence_version = self._reconciliation_evidence_version(
                    reconciliation, remaining_discrepancy
                )
                active.blocker_codes = (active.blocker_code,)
                active.decisions = tuple(
                    decision.model_copy(update={"evidence_version": active.evidence_version})
                    for decision in active.decisions
                    if decision.metadata.blocker_code == active.blocker_code
                )
                active.authoritative_evidence_digest = self._authoritative_evidence_digest(
                    case_id=candidate.case_id,
                    exception_type=active.exception_type,
                    evidence_version=active.evidence_version,
                    blocker_codes=active.blocker_codes,
                )
            candidate.status = AutomationStatus.WAITING_FOR_REVIEW
            candidate.current_stage = _earliest_open_stage(candidate)
            return self._save(record, candidate)
        remaining = candidate.active_exceptions
        candidate.status = (
            AutomationStatus.WAITING_FOR_REVIEW if remaining else AutomationStatus.RESUMING
        )
        candidate.current_stage = (
            _earliest_open_stage(candidate) if remaining else AutomationStage.DOCUMENT
        )
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code="AUTOMATION_RESUMING",
            message="All reconciliation blockers are resolved; onboarding is resuming.",
        )
        saved = self._save(record, candidate)
        if saved.active_exceptions:
            return saved
        return self._advance_locked(case_id=record.case_id)

    def _retain_resolution_actor(self, exception: BusinessException, actor_id: str | None) -> None:
        if actor_id is None or not exception.decisions or len(exception.decisions) >= 8:
            return
        previous = exception.decisions[-1]
        exception.decisions += (
            previous.model_copy(
                update={
                    "decision_id": self._uuid_factory(),
                    "recorded_at": self._clock(),
                    "actor_id": actor_id,
                    "reviewer_id": actor_id,
                    "evidence_version": exception.evidence_version,
                    "automation_version": exception.automation_version,
                }
            ),
        )

    def _refresh_document_checkpoint_locked(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        human_intervention: bool = False,
        actor_id: str | None = None,
        reviewed_field_key: DocumentFieldKey | None = None,
        reviewed_field_keys: frozenset[DocumentFieldKey] = frozenset(),
    ) -> ZeroTouchAutomationRecord:
        current_documents = self._current_documents(record.case_id)
        if any(item.state == DocumentProcessingState.FAILED for item in current_documents):
            return self._return_to_document_intake(record)
        for document in current_documents:
            if document.state == DocumentProcessingState.REVIEW_REQUIRED:
                self._documents.auto_confirm_document(
                    case_id=record.case_id,
                    document_id=document.document_id,
                    allow_partial=True,
                )
        try:
            reconciliation = self._reconciliation.reconcile_current(case_id=record.case_id)
            expected_versions = {
                self._reconciliation_evidence_version(reconciliation, item)
                for item in reconciliation.open_discrepancies
            }
        except ReconciliationRequestError as exc:
            raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
        except ReconciliationInfrastructureError as exc:
            raise ZeroTouchInfrastructureError(
                case_id=record.case_id,
                automation_id=record.automation_id,
                code=exc.code,
                message=exc.public_message,
            ) from None
        record = self._recover_obsolete_registry_ownership_locked(record)
        actual_versions = {
            item.evidence_version
            for item in record.active_exceptions
            if item.stage == AutomationStage.DOCUMENT
        }
        if (
            not human_intervention
            and record.status == AutomationStatus.WAITING_FOR_REVIEW
            and (actual_versions == expected_versions)
        ):
            return record
        candidate = record.model_copy(deep=True)
        if human_intervention:
            candidate.metrics.human_interventions += 1
        for item in candidate.active_exceptions:
            if item.stage == AutomationStage.DOCUMENT:
                unresolved_fields = {
                    discrepancy.field_name.value
                    for discrepancy in reconciliation.open_discrepancies
                }
                field_key = item.evidence[0].field_key if item.evidence else None
                item.status = (
                    BusinessExceptionStatus.CANCELLED
                    if field_key in unresolved_fields
                    else BusinessExceptionStatus.RESOLVED
                )
                item.resolved_at = self._clock()
                if field_key in {
                    (
                        "registration_identifier"
                        if key == DocumentFieldKey.REGISTRATION_NUMBER else key
                    )
                    for key in reviewed_field_keys
                } or field_key == (
                    "registration_identifier"
                    if reviewed_field_key == DocumentFieldKey.REGISTRATION_NUMBER
                    else reviewed_field_key
                ):
                    self._retain_resolution_actor(item, actor_id)
                if item.status == BusinessExceptionStatus.RESOLVED:
                    candidate.metrics.exceptions_resolved += 1
        candidate.status = (
            AutomationStatus.RUNNING if record.status == AutomationStatus.RESUMING
            else AutomationStatus.RESUMING
        )
        candidate.current_stage = _next_stage(
            candidate.completed_stages, order=_stage_order(candidate)
        )
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code="DOCUMENT_REVIEW_UPDATED",
            message="Current document review evidence is being re-evaluated.",
        )
        if reconciliation.status == ReconciliationStatus.REVIEW_REQUIRED:
            return self._raise_reconciliation_exceptions(candidate, reconciliation)
        if candidate.active_exceptions:
            candidate.status = AutomationStatus.WAITING_FOR_REVIEW
            candidate.current_stage = _earliest_open_stage(candidate)
            return self._save(record, candidate)
        self._save(record, candidate)
        return self._advance_locked(case_id=record.case_id)

    def _return_to_document_intake(
        self, record: ZeroTouchAutomationRecord
    ) -> ZeroTouchAutomationRecord:
        candidate = record.model_copy(deep=True)
        candidate.status = AutomationStatus.PENDING_INPUTS
        candidate.current_stage = AutomationStage.DOCUMENT
        candidate.completed_stages = (
            (AutomationStage.REGISTRY,)
            if candidate.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
            else (
                AutomationStage.REGISTRY,
                AutomationStage.GOLDTIER_SEARCH,
            )
        )
        candidate.technical_failure = None
        candidate.completed_at = None
        candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
        candidate.metrics.final_outcome = None
        for item in candidate.active_exceptions:
            item.status = BusinessExceptionStatus.CANCELLED
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.DOCUMENT_REUPLOAD_REQUIRED,
            outcome=EventOutcome.PARTIAL,
            code="DOCUMENT_REUPLOAD_REQUIRED",
            message="Failed replacement evidence requires targeted re-upload.",
        )
        return self._save(record, candidate)

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

    def _is_obsolete_registry_ownership_exception(
        self, case_id: UUID, item: BusinessException, *, release_advisory: bool = False,
    ) -> bool:
        return (
            item.stage in {AutomationStage.OWNERSHIP, AutomationStage.READINESS}
            and item.exception_type in _OWNERSHIP_DEPENDENCY_EXCEPTION_TYPES
            and item.evidence_version.startswith("ownership:")
            and (
                self._ownership.registry_dependency_is_obsolete(
                    case_id=case_id, evidence_version=item.evidence_version,
                    registry_evidence_generation=item.registry_evidence_generation,
                )
                or self._ownership.document_dependency_is_obsolete(
                    case_id=case_id, evidence_version=item.evidence_version,
                )
                or self._ownership_hold_now_cleared(case_id, item, release_advisory)
            )
        )

    def _ownership_hold_now_cleared(
        self, case_id: UUID, item: BusinessException, release_advisory: bool,
    ) -> bool:
        """D-082 F2: a hold on an analysis now accepted. D-124: an advisory hold is retired
        only by a continuation, from /resume or the startup release."""
        ownership = self._ownership.get(case_id=case_id)
        return (
            ownership is not None
            and item.evidence_version == f"ownership:{ownership.analysis_id}:{ownership.version}"
            and (
                self._ownership.poc_basis_accepted(ownership)
                or (release_advisory and self._ownership.review_is_advisory(ownership))
            )
        )

    def _recover_obsolete_registry_ownership_locked(
        self, record: ZeroTouchAutomationRecord, *, release_advisory: bool = False,
    ) -> ZeroTouchAutomationRecord:
        """Repair an interrupted pre-submission rebind under the owning case lock.

        Only proven obsolete registry/document ownership dependencies are retired. No new
        registry/Search call, human decision or target dispatch is performed here.
        """
        if record.status in {AutomationStatus.COMPLETED, AutomationStatus.TECHNICAL_FAILURE}:
            return record
        obsolete = {
            item.exception_id for item in record.active_exceptions
            if self._is_obsolete_registry_ownership_exception(
                record.case_id, item, release_advisory=release_advisory,
            )
        }
        case = self._cases.get_case(record.case_id)
        clm = self._clm.get(case_id=record.case_id)
        if (
            case is None or clm is None or clm.submission_snapshot is not None
            or case.goldtier_result is not None
            or self._cases.has_retained_target_execution(record.case_id)
        ):
            return record
        ownership = self._ownership.get(case_id=record.case_id)
        government = self._government_gate(record.case_id)
        current_review = (
            ownership is not None
            and ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
            and not self._ownership.clears_review(ownership)
            and not government
        ) or (government is False and ownership is not None)
        # D-101: a Government checkpoint is proved only by a confirmation that is current.
        government_revoked = (
            AutomationStage.OWNERSHIP in record.completed_stages and government is False
        )
        # D-082 F2: only an analysis carrying a POC acceptance can complete OWNERSHIP while
        # REVIEW_REQUIRED; once that acceptance is not current, its checkpoint is unproved.
        # Every other review analysis keeps the existing restoration below.
        poc_revoked = (
            AutomationStage.OWNERSHIP in record.completed_stages
            and current_review
            and ownership is not None
            and ownership.poc_acceptance is not None
        )
        unproved_ownership_checkpoint = (
            AutomationStage.OWNERSHIP in record.completed_stages
            and (ownership is None or ownership.state in {
                OwnershipAnalysisState.LOADED, OwnershipAnalysisState.FAILED,
            })
        ) or poc_revoked or government_revoked
        if not obsolete and not unproved_ownership_checkpoint:
            # A durable ownership result can precede its automation checkpoint.
            # Restore that owned dependency even beside an independent later blocker.
            if current_review and ownership is not None:
                return self._raise_ownership_exception(record, ownership)
            return record
        stale_confirmation_versions = {
            f"target-confirmation:{clm.version}",
            f"target-confirmation:{clm.version}:{len(case.events)}",
        }
        if case.target_dispatch_confirmation is not None:
            self._cases.invalidate_target_dispatch_confirmation(
                case_id=record.case_id, expected_case_event_count=len(case.events),
            )
            case = self._cases.get_case(record.case_id)
            assert case is not None
        try:
            clm = self._clm.refresh_pre_submission_evidence(case_id=record.case_id)
        except ClmRequestError as exc:
            raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
        # The parent write may have succeeded before its CLM projection. Rebind
        # retained Search evidence using its existing request ID and CLM CAS.
        search = case.initial_target_search
        if search is not None and (
            clm.target_search_checkpoint is None
            or clm.target_search_checkpoint.request_id != search.request_id
        ):
            try:
                clm = self._clm.refresh_initial_search_after_recheck(
                    case_id=record.case_id, expected_clm_version=clm.version,
                )
            except ClmRequestError as exc:
                raise ZeroTouchRequestError(code=exc.code, message=exc.public_message) from None
        candidate = record.model_copy(deep=True)
        for item in candidate.active_exceptions:
            if (
                item.exception_id in obsolete
                or (
                    item.exception_type == BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED
                    and (
                        item.evidence_version in stale_confirmation_versions
                        # A revoked POC acceptance withdraws any earlier confirmation hold.
                        or (
                            poc_revoked
                            and item.evidence_version.startswith("target-confirmation:")
                        )
                    )
                )
            ):
                item.status = BusinessExceptionStatus.CANCELLED
                item.resolved_at = self._clock()
        # Rebuild document reconciliation, ownership and readiness from current
        # evidence; retain every unrelated blocker and its original decision.
        candidate.completed_stages = (
            (AutomationStage.REGISTRY,)
            if case.state == WorkflowState.VALIDATED and case.entity is not None else ()
        )
        if (candidate.stage_order_version != LEGACY_AUTOMATION_STAGE_ORDER_VERSION
            and candidate.completed_stages and search is not None
            and clm.target_search_checkpoint is not None
            and clm.target_search_checkpoint.request_id == search.request_id
            and clm.target_search_checkpoint.status == GoldTierSearchCheckpointStatus.COMPLETED):
            candidate.completed_stages += (AutomationStage.GOLDTIER_SEARCH,)
        if current_review and ownership is not None:
            candidate = self._raise_ownership_exception(candidate, ownership, persist=False)
        remaining = candidate.active_exceptions
        candidate.status = (
            AutomationStatus.WAITING_FOR_REVIEW if remaining else AutomationStatus.RESUMING
        )
        candidate.current_stage = _earliest_open_stage(candidate) if remaining else _next_stage(
            candidate.completed_stages, order=_stage_order(candidate),
        )
        candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
        candidate.metrics.final_outcome = None
        candidate = self._append_event(
            candidate, event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code=("OBSOLETE_OWNERSHIP_EVIDENCE_RETIRED" if obsolete
                  else "CURRENT_OWNERSHIP_PREREQUISITE_RESTORED"),
            message=(
                "Superseded ownership evidence blockers were retained as cancelled history."
                if obsolete else "Current ownership prerequisites require re-evaluation."
            ),
        )
        return self._save(record, candidate)

    def _advance_locked_impl(self, *, case_id: UUID) -> ZeroTouchAutomationRecord:
        record = self._recover_obsolete_registry_ownership_locked(self._require_record(case_id))
        if record.active_exceptions and not _has_unproved_prerequisite(record):
            return record
        if record.status in {
            AutomationStatus.COMPLETED,
            AutomationStatus.TECHNICAL_FAILURE,
        }:
            return record
        if (
            record.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
            and record.status == AutomationStatus.RECOVERY_PENDING
        ):
            return record
        record = self._upgrade_legacy_stage_order(record)

        finalization_recovery_attempts = 0
        for _ in range(self._max_transitions):
            record = self._require_record(case_id)
            if record.active_exceptions and not _has_unproved_prerequisite(record):
                return record
            next_stage = _next_stage(record.completed_stages)
            if next_stage == AutomationStage.GOLDTIER_SEARCH:
                started_at = self._clock()
                clm_record = self._clm.evaluate(case_id=case_id)
                search = clm_record.target_search_checkpoint
                if (
                    search is not None
                    and search.status == GoldTierSearchCheckpointStatus.COMPLETED
                    and search.disposition
                    in {
                        GoldTierSearchDisposition.NO_MATCH,
                        GoldTierSearchDisposition.EXACT_MATCH,
                        GoldTierSearchDisposition.CONFIRMED_EXISTING,
                    }
                ):
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.GOLDTIER_SEARCH,
                        event_type=AutomationEventType.GOLDTIER_SEARCH_COMPLETED,
                        code=search.code or "GOLDTIER_SEARCH_COMPLETED",
                        message=search.message,
                        started_at=started_at,
                    )
                    continue
                if (
                    search is not None
                    and search.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                ):
                    record = self._add_exception(
                        record,
                        exception_type=BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED,
                        stage=AutomationStage.GOLDTIER_SEARCH,
                        blocker_code=search.code or "GT_SEARCH_IDENTITY_REVIEW_REQUIRED",
                        explanation=(
                            "GoldTier candidates require identity review; all target "
                            "mutations remain blocked."
                        ),
                        evidence_version=f"goldtier-search:{search.request_id}",
                        evidence=(),
                        actions=(),
                    )
                    return self._save(self._require_record(case_id), record)
                return self._technical_failure(
                    record,
                    stage=AutomationStage.GOLDTIER_SEARCH,
                    code=(
                        search.code
                        if search is not None and search.code
                        else "GOLDTIER_SEARCH_FAILED"
                    ),
                    message=(
                        search.message
                        if search is not None
                        else "GoldTier customer Search could not be completed safely."
                    ),
                )
            if next_stage == AutomationStage.DOCUMENT:
                documents = self._documents.list_documents(case_id=case_id)
                if not documents:
                    candidate = record.model_copy(deep=True)
                    candidate.status = AutomationStatus.PENDING_INPUTS
                    candidate.current_stage = AutomationStage.DOCUMENT
                    return self._save(record, candidate)
                current_documents = self._current_documents(case_id)
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
                for document in current_documents:
                    if document.state != DocumentProcessingState.REVIEW_REQUIRED:
                        continue
                    self._documents.auto_confirm_document(
                        case_id=case_id, document_id=document.document_id, allow_partial=True
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
                    self._sync_document_target_classification(case_id)
                    record = self._record_equivalent_normalization_decisions(
                        record,
                        reconciliation=reconciliation,
                    )
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.DOCUMENT,
                        event_type=(AutomationEventType.RECONCILIATION_EVALUATED),
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
                # D-082: a current opt-in POC acceptance completes the stage below with
                # its own audit code; every other review outcome raises the exception.
                poc_accepted = self._ownership.poc_basis_accepted(ownership)
                advisory = self._ownership.review_is_advisory(ownership)  # D-121
                # D-101: for a Government entity only a current RM confirmation completes
                # this stage, whatever the (unsupported) ownership analysis says.
                government = self._government_gate(case_id)
                if government is False or (
                    government is None
                    and ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED
                    and not poc_accepted
                    and not advisory
                ):
                    if self._intelligence_evaluator is not None:
                        intelligence = self._intelligence_evaluator(case_id)
                        if intelligence is not None:
                            record = self._append_intelligence_event(record, intelligence)
                    return self._raise_ownership_exception(record, ownership)
                if ownership.state == OwnershipAnalysisState.FAILED:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.OWNERSHIP,
                        code=(ownership.error.code if ownership.error else "OWNERSHIP_FAILED"),
                        message="Ownership processing stopped after a technical failure.",
                    )
                if government or (
                    government is None
                    and (
                        ownership.state == OwnershipAnalysisState.ANALYZED
                        or poc_accepted
                        or advisory
                    )
                ):
                    intelligence = (
                        self._intelligence_evaluator(case_id)
                        if self._intelligence_evaluator is not None
                        else None
                    )
                    if intelligence is not None:
                        record = self._append_intelligence_event(record, intelligence)
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.OWNERSHIP,
                        event_type=AutomationEventType.OWNERSHIP_AUTOMATED,
                        code=(
                            "GOVERNMENT_STATUS_CONFIRMED"
                            if government
                            else "OWNERSHIP_POC_BASIS_ACCEPTED"
                            if poc_accepted
                            else "OWNERSHIP_REVIEW_ADVISORY"
                            if advisory
                            else "OWNERSHIP_AUTOMATED"
                        ),
                        message=(
                            "Government status was confirmed by the RM from a reviewed "
                            "document; no ownership or UBO analysis applies (D-101)."
                            if government
                            else "Ownership calculated; the scenario's declared POC basis was "
                            "accepted by D-085. Classification review is retained."
                            if poc_accepted
                            else "Ownership review is advisory on this lane (D-121): it does "
                            "not block readiness, and nothing was accepted or verified."
                            if advisory
                            else "Deterministic ownership analysis completed automatically."
                        ),
                        started_at=started_at,
                    )
                    blocked = self._raise_intelligence_blocker(record, intelligence)
                    if blocked is not None:
                        return blocked
                    continue
                return self._technical_failure(
                    record,
                    stage=AutomationStage.OWNERSHIP,
                    code="AUTOMATION_NO_PROGRESS",
                    message="Ownership automation made no safe progress.",
                )

            if next_stage == AutomationStage.READINESS:
                self._sync_document_target_classification(case_id)
                started_at = self._clock()
                try:
                    clm_record = self._clm.evaluate(case_id=case_id)
                except ClmRequestError as exc:
                    if (
                        exc.code == "CLM_TARGET_OUTCOME_UNCERTAIN"
                        and record.status == AutomationStatus.RECOVERY_PENDING
                    ):
                        return record
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.READINESS,
                        code=exc.code,
                        message="Readiness evaluation could not progress safely.",
                    )
                if ClmBlockerCode.GOLDTIER_CLASSIFICATION_REQUIRED in clm_record.readiness.blockers:
                    classification_case = self._cases.get_case(case_id)
                    if classification_case is None:
                        return self._technical_failure(
                            record,
                            stage=AutomationStage.READINESS,
                            code="ZERO_TOUCH_CASE_NOT_FOUND",
                            message="The onboarding case is unavailable.",
                        )
                    assessment = self._documents.assess_target_classification(case_id=case_id)
                    return self._add_exception(
                        record,
                        exception_type=BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED,
                        stage=AutomationStage.READINESS,
                        blocker_code=ClmBlockerCode.GOLDTIER_CLASSIFICATION_REQUIRED.value,
                        explanation=(
                            "Current trusted documents contain different target-classification "
                            "values. Review the evidence and select the value to use for this case."
                            if assessment.state == "CONFLICT" else
                            "Current classification evidence requires review. Select the values "
                            "to use from the current GoldTier vocabulary."
                        ),
                        evidence_version=f"target-classification:{case_id}:{assessment.evidence_fingerprint}",
                        evidence=(),
                        actions=(),
                    )
                if ClmBlockerCode.GOLDTIER_SEARCH_FAILED in clm_record.readiness.blockers:
                    search = clm_record.target_search_checkpoint
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.GOLDTIER_SEARCH,
                        code=(
                            search.code
                            if search is not None and search.code
                            else "SEARCH_SERVICE_UNAVAILABLE"
                        ),
                        message=(
                            "GoldTier Search failed after independent case evidence was retained. "
                            "Customer existence remains unresolved and all target mutations are "
                            "blocked."
                        ),
                    )
                if clm_record.status != ClmStatus.READY_FOR_MOCK_SUBMISSION:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.READINESS,
                        code="AUTOMATION_READINESS_INCONSISTENT",
                        message="Authoritative readiness changed before automatic submission.",
                    )
                record = self._record_readiness_warning_decisions(
                    record,
                    warnings=tuple(clm_record.readiness.warnings),
                    clm_version=clm_record.version,
                )
                confirmation_case = self._cases.get_case(case_id)
                if confirmation_case is None:
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.READINESS,
                        code="ZERO_TOUCH_CASE_NOT_FOUND",
                        message="The onboarding case is unavailable.",
                    )
                return self._add_exception(
                    record,
                    exception_type=BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
                    stage=AutomationStage.READINESS,
                    blocker_code="TARGET_CONFIRMATION_REQUIRED",
                    explanation=(
                        "A local-POC operator must confirm the frozen destination, warnings, "
                        "and review digest before any target mutation."
                    ),
                    evidence_version=(
                        f"target-confirmation:{clm_record.version}:"
                        f"{len(confirmation_case.events)}"
                    ),
                    evidence=(),
                    actions=(),
                )

            if next_stage == AutomationStage.MOCK_GOLDTIER:
                started_at = self._clock()
                if (
                    not any(
                        event.event_type == AutomationEventType.MOCK_SUBMISSION_STARTED
                        for event in record.events
                    )
                    and record.status != AutomationStatus.RECOVERY_PENDING
                ):
                    candidate = record.model_copy(deep=True)
                    candidate.status = AutomationStatus.RUNNING
                    candidate.current_stage = AutomationStage.MOCK_GOLDTIER
                    candidate = self._append_event(
                        candidate,
                        event_type=AutomationEventType.MOCK_SUBMISSION_STARTED,
                        outcome=EventOutcome.SUCCEEDED,
                        code="MOCK_SUBMISSION_STARTED",
                        message="Automatic GoldTier target submission started.",
                    )
                    record = self._save(record, candidate)
                try:
                    clm_record = self._clm.submit(case_id=case_id, single_checkpoint=True)
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
                                "Target submission outcome is retained; finalization recovery "
                                "will resume without replaying target operations."
                            ),
                        )
                        return self._save(record, candidate)
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.MOCK_GOLDTIER,
                        code=exc.code,
                        message="GoldTier target processing stopped after a technical failure.",
                    )
                except ClmRequestError as exc:
                    if (
                        exc.code == "CLM_TARGET_OUTCOME_UNCERTAIN"
                        and record.status == AutomationStatus.RECOVERY_PENDING
                    ):
                        return record
                    return self._technical_failure(
                        record,
                        stage=AutomationStage.MOCK_GOLDTIER,
                        code=exc.code,
                        message="GoldTier target processing could not progress safely.",
                    )
                if clm_record.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED:
                    record = self._complete_stage(
                        record,
                        stage=AutomationStage.MOCK_GOLDTIER,
                        event_type=AutomationEventType.MOCK_SUBMISSION_COMPLETED,
                        code="MOCK_GOLDTIER_SUBMITTED",
                        message="GoldTier target submission completed automatically.",
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
                if clm_record.status == ClmStatus.SUBMITTING:
                    operations = self._clm.attempted_target_operations(case_id=case_id)
                    operation = operations[-1] if operations else "SEARCH"
                    candidate = record.model_copy(deep=True)
                    candidate = self._append_event(
                        candidate,
                        event_type=AutomationEventType.TARGET_OPERATION_CHECKPOINTED,
                        outcome=EventOutcome.SUCCEEDED,
                        code=f"GOLDTIER_{operation}_CHECKPOINTED",
                        message=(
                            f"GoldTier {operation} reached a durable checkpoint; "
                            "the next target operation will use the retained ledger."
                        ),
                    )
                    record = self._save(record, candidate)
                    continue
                if clm_record.status == ClmStatus.REVIEW_REQUIRED:
                    return self._raise_target_exception(record, clm_record.error)
                return self._technical_failure(
                    record,
                    stage=AutomationStage.MOCK_GOLDTIER,
                    code=(clm_record.error.code if clm_record.error else "CLM_SUBMISSION_FAILED"),
                    message="GoldTier target processing stopped after a technical failure.",
                )

            if next_stage == AutomationStage.COMPLETE:
                return record

        return self._technical_failure(
            self._require_record(case_id),
            stage=self._require_record(case_id).current_stage,
            code="AUTOMATION_LOOP_GUARD",
            message="Automation stopped at the configured progression bound.",
        )

    def _upgrade_legacy_stage_order(
        self, record: ZeroTouchAutomationRecord
    ) -> ZeroTouchAutomationRecord:
        """Rebase non-terminal pre-Search progress without claiming Search evidence."""

        if record.stage_order_version != LEGACY_AUTOMATION_STAGE_ORDER_VERSION:
            return record
        candidate = record.model_copy(deep=True)
        candidate.stage_order_version = AUTOMATION_STAGE_ORDER_VERSION
        registry_completed = AutomationStage.REGISTRY in record.completed_stages
        candidate.completed_stages = (
            (AutomationStage.REGISTRY,) if registry_completed else ()
        )
        candidate.current_stage = (
            AutomationStage.GOLDTIER_SEARCH if registry_completed else AutomationStage.REGISTRY
        )
        candidate.status = (
            AutomationStatus.WAITING_FOR_REVIEW
            if candidate.active_exceptions else AutomationStatus.RUNNING
        )
        if candidate.active_exceptions:
            candidate.current_stage = _earliest_open_stage(candidate)
        candidate.started_at = candidate.started_at or self._clock()
        candidate.completed_at = None
        candidate.metrics.automated_stages_completed = len(candidate.completed_stages)
        candidate.metrics.final_outcome = None
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.AUTOMATION_RESUMING,
            outcome=EventOutcome.SUCCEEDED,
            code="AUTOMATION_STAGE_ORDER_UPGRADED",
            message=(
                "Historical onboarding progress is resuming at the earliest unproved "
                "stage in the current workflow."
            ),
        )
        return self._save(record, candidate)

    def _raise_document_exception(
        self,
        record: ZeroTouchAutomationRecord,
        document: DocumentProcessingRecord,
        blockers: tuple[DocumentAutoClearBlocker, ...],
    ) -> ZeroTouchAutomationRecord:
        if DocumentAutoClearBlocker.TEXT_UNAVAILABLE in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING
            code = "DOCUMENT_TEXT_UNAVAILABLE"
            explanation = "No usable text was found within the bounded local extraction path."
        elif DocumentAutoClearBlocker.SOURCE_CONFLICT in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT
            code = "DOCUMENT_SOURCE_CONFLICT"
            explanation = "Document evidence conflicts with current registry evidence."
        elif DocumentAutoClearBlocker.AMBIGUOUS_EXTRACTION in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_REVIEW_REQUIRED
            code = "DOCUMENT_AMBIGUOUS_EXTRACTION"
            explanation = "Multiple labelled values were extracted; no value was selected."
        elif DocumentAutoClearBlocker.REQUIRED_FIELD_MISSING in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING
            code = "DOCUMENT_REQUIRED_FIELD_MISSING"
            explanation = "A required document field is missing and requires human review."
        elif DocumentAutoClearBlocker.LOW_CONFIDENCE in blockers:
            exception_type = BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE
            code = "DOCUMENT_LOW_CONFIDENCE"
            explanation = "Extraction evidence score is below the case-bound threshold."
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
                or field.confidence
                < self._documents.review_confidence_threshold_for_case(record.case_id)
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
                and observation.evidence_reference == "DOCUMENT_AMBIGUOUS_EXTRACTION"
                for observation in item.observations
            ):
                return "DOCUMENT_AMBIGUOUS_EXTRACTION"
            if any(
                observation.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
                and observation.evidence_reference == "DOCUMENT_TEXT_UNAVAILABLE"
                for observation in item.observations
            ):
                return "DOCUMENT_TEXT_UNAVAILABLE"
            if any(
                observation.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
                and observation.evidence_reference == "DOCUMENT_REVIEW_PENDING"
                for observation in item.observations
            ):
                return "DOCUMENT_REVIEW_REQUIRED"
            return outcome_codes[item.outcome]

        for discrepancy in reconciliation.open_discrepancies:
            if any(
                item.exception_id == discrepancy.discrepancy_id for item in record.active_exceptions
            ):
                continue
            code = code_for(discrepancy)
            exception_type = (
                BusinessExceptionType.DOCUMENT_REVIEW_REQUIRED
                if code in {"DOCUMENT_REVIEW_REQUIRED", "DOCUMENT_AMBIGUOUS_EXTRACTION"}
                else {
                    ReconciliationOutcome.CONFLICT: (
                        BusinessExceptionType.DOCUMENT_SOURCE_CONFLICT
                    ),
                    ReconciliationOutcome.MISSING_IN_SOURCE: (
                        BusinessExceptionType.DOCUMENT_REQUIRED_FIELD_MISSING
                    ),
                    ReconciliationOutcome.UNVERIFIABLE: (
                        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE
                    ),
                    ReconciliationOutcome.INVALID: (BusinessExceptionType.RECONCILIATION_INVALID),
                }[discrepancy.outcome]
            )
            baseline = next(
                (
                    item
                    for item in discrepancy.observations
                    if item.source_kind in CANONICAL_BASELINE_SOURCE_KINDS
                ),
                None,
            )
            registry = (
                baseline
                if baseline is not None
                and baseline.source_kind == ReconciliationSourceKind.REGISTRY
                else None
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
                    if baseline is None
                    or item.normalized_value != baseline.normalized_value
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
                    (
                        "Retained existing-customer baseline and document observations "
                        "disagree and require an explicit bounded decision."
                        if baseline is not None
                        and baseline.source_kind == ReconciliationSourceKind.EXISTING_CASE
                        else "Registry and document observations disagree and require an "
                        "explicit bounded decision."
                    )
                    if discrepancy.outcome == ReconciliationOutcome.CONFLICT
                    else (
                        "Document evidence is not currently usable for deterministic "
                        "reconciliation."
                    )
                ),
                evidence_version=self._reconciliation_evidence_version(reconciliation, discrepancy),
                evidence=evidence,
                actions=tuple(
                    ExceptionResolutionAction(action.value)
                    for action in discrepancy.allowed_actions
                ),
                blocker_codes=(code,),
                exception_id=discrepancy.discrepancy_id,
            )
        return record

    @staticmethod
    def _reconciliation_evidence_version(
        reconciliation: ReconciliationCaseRecord,
        discrepancy: ReconciliationDiscrepancy,
    ) -> str:
        baseline = next(
            (
                item
                for item in discrepancy.observations
                if item.source_kind in CANONICAL_BASELINE_SOURCE_KINDS
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
                if baseline is None
                or item.normalized_value != baseline.normalized_value
                or item.validity.value != "VALID"
            ),
            0,
        )
        affected_document_id = (
            document_observations[affected_document_index].source_record_id
            or reconciliation.source_document_ids[0]
        )
        affected_source_index = reconciliation.source_document_ids.index(affected_document_id)
        return (
            f"reconciliation:{reconciliation.version}:"
            f"{reconciliation.source_document_event_counts[affected_source_index]}:"
            f"{discrepancy.evidence_fingerprint}"
        )

    def _government_gate(self, case_id: UUID) -> bool | None:
        """D-101: None when the Government profile does not apply, else whether the RM
        confirmation is bound to the current evidence."""
        case = self._cases.get_case(case_id)
        if case is None or not government_profile_applies(case):
            return None
        documents = [
            item
            for item in self._documents.list_documents(case_id=case_id)
            if item.is_current_evidence
        ]
        return government_status_confirmed(
            case,
            documents,
            confidence_threshold=float(case.policy_snapshot.idp_review_confidence_threshold),
        )

    def _raise_ownership_exception(
        self, record: ZeroTouchAutomationRecord, ownership: OwnershipAnalysisRecord,
        *, persist: bool = True,
    ) -> ZeroTouchAutomationRecord:
        case = self._cases.get_case(record.case_id)
        if case is not None and government_profile_applies(case):
            # D-101: the Government status step replaces every ownership exception.
            return self._add_exception(
                record,
                exception_type=BusinessExceptionType.GOVERNMENT_STATUS_REQUIRED,
                stage=AutomationStage.OWNERSHIP,
                blocker_code="GOVERNMENT_STATUS_REQUIRED",
                explanation=(
                    "Confirm Singapore Government status from a reviewed document. "
                    "No ownership or UBO analysis applies; not ACRA-registered."
                ),
                evidence_version=(
                    f"government-status:{ownership.analysis_id}:{ownership.version}:"
                    f"{len(case.events)}"
                ),
                persist=persist,
                evidence=(),
                actions=(),
            )
        issue_codes = {item.code.value for item in ownership.issues}
        evidence_specific = next((item for item in ownership.issues if item.code.value in {
            "OWNERSHIP_DENOMINATOR_REQUIRED", "OWNERSHIP_REQUIRED",
            "UBO_REVIEW_REQUIRED", "OWNERSHIP_METHOD_UNSUPPORTED",
            "CONTRADICTORY_OWNERSHIP_EVIDENCE",
        }), None)
        if evidence_specific is not None:
            exception_type = BusinessExceptionType.OWNERSHIP_INCOMPLETE
            code = evidence_specific.code.value
            explanation = evidence_specific.message
        elif "CYCLE_DETECTED" in issue_codes:
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
            persist=persist,
            registry_evidence_generation=(ownership.identity_correction_version
                if ownership.provider_name == "ACRA_REGISTRY_ACQUISITION" else None),
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
                "An existing GoldTier target party was found; duplicate creation was stopped."
            )
        else:
            exception_type = BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED
            explanation = "GoldTier target processing returned a partial or review outcome."
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

    def _raise_intelligence_blocker(
        self,
        record: ZeroTouchAutomationRecord,
        intelligence: OnboardingIntelligenceRecord | None,
    ) -> ZeroTouchAutomationRecord | None:
        if (
            intelligence is not None
            and intelligence.entity_resolution is not None
            and intelligence.entity_resolution.outcome
            in {
                EntityResolutionOutcome.REVIEW_REQUIRED,
                EntityResolutionOutcome.CONFLICT,
            }
        ):
            return self._raise_entity_resolution_exception(record, intelligence)
        if (
            intelligence is not None
            and intelligence.mock_risk is not None
            and intelligence.mock_risk.blocks_readiness
            and intelligence.mock_risk.band == MockRiskBand.HIGH
        ):
            return self._raise_mock_risk_exception(record, intelligence)
        return None

    def _raise_mock_risk_exception(
        self,
        record: ZeroTouchAutomationRecord,
        intelligence: OnboardingIntelligenceRecord,
    ) -> ZeroTouchAutomationRecord:
        return self._add_exception(
            record,
            exception_type=BusinessExceptionType.MOCK_RISK_REVIEW_REQUIRED,
            stage=AutomationStage.READINESS,
            blocker_code="MOCK_RISK_REVIEW_REQUIRED",
            explanation=(
                "Project-configured mock advisory risk requires human review; "
                "this is not a compliance decision."
            ),
            evidence_version=(
                f"intelligence:{intelligence.version}:{intelligence.input_fingerprint}"
            ),
            evidence=(),
            actions=(),
        )

    def _raise_entity_resolution_exception(
        self,
        record: ZeroTouchAutomationRecord,
        intelligence: OnboardingIntelligenceRecord,
    ) -> ZeroTouchAutomationRecord:
        return self._add_exception(
            record,
            exception_type=BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED,
            stage=AutomationStage.READINESS,
            blocker_code="ENTITY_RESOLUTION_REVIEW_REQUIRED",
            explanation=(
                "Synthetic entity candidate evidence is ambiguous and requires human review."
            ),
            evidence_version=(
                f"intelligence:{intelligence.version}:{intelligence.input_fingerprint}"
            ),
            evidence=(),
            actions=(),
        )

    def _record_readiness_warning_decisions(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        warnings: tuple[ClmWarningCode, ...],
        clm_version: int,
    ) -> ZeroTouchAutomationRecord:
        """Retain warnings the readiness owner already allowed; never authorize progress."""

        if not warnings:
            return record
        candidate = record.model_copy(deep=True)
        changed = False
        for warning in warnings:
            evidence_version = f"readiness:{clm_version}:{warning.value}"
            if any(
                item.evidence_version == evidence_version
                and item.metadata.blocker_code == warning.value
                for item in candidate.non_blocking_decisions
            ):
                continue
            if len(candidate.non_blocking_decisions) >= 64:
                break
            metadata = self._blocker_decision_policy.continue_with_warning(
                ContinueWithWarningDecisionInput(
                    rule=ContinueWithWarningRule(warning.value),
                    available_inputs=frozenset(
                        {BlockerMinimumInput.CURRENT_READINESS_WARNING}
                    ),
                )
            )
            candidate.non_blocking_decisions.append(
                BlockerDecisionRecord(
                    decision_id=uuid5(
                        NAMESPACE_URL,
                        f"blocker-decision:{record.case_id}:{evidence_version}",
                    ),
                    case_id=record.case_id,
                    evidence_version=evidence_version,
                    automation_version=record.version + 1,
                    recorded_at=self._clock(),
                    metadata=metadata,
                )
            )
            changed = True
        # The caller folds these metadata-only records into the next existing
        # authoritative transition; metadata never creates its own transition.
        return candidate if changed else record

    def _record_equivalent_normalization_decisions(
        self,
        record: ZeroTouchAutomationRecord,
        *,
        reconciliation: ReconciliationCaseRecord,
    ) -> ZeroTouchAutomationRecord:
        """Retain notes only where current source values normalize equivalently."""

        candidate = record.model_copy(deep=True)
        changed = False
        for field in reconciliation.fields:
            valid = tuple(
                item
                for item in field.observations
                if item.validity.value == "VALID" and item.normalized_value is not None
            )
            if (
                field.outcome != ReconciliationOutcome.MATCH
                or not any(
                    item.source_kind == ReconciliationSourceKind.DOCUMENT_IDP
                    for item in valid
                )
                or len({item.normalized_value for item in valid}) != 1
                or len({item.raw_value for item in valid}) < 2
            ):
                continue
            evidence_version = (
                f"reconciliation:{reconciliation.version}:"
                f"{field.field_name.value}:normalized-equivalent"
            )
            if any(
                item.evidence_version == evidence_version
                for item in candidate.non_blocking_decisions
            ):
                continue
            if len(candidate.non_blocking_decisions) >= 64:
                break
            metadata = self._blocker_decision_policy.auto_resolved_note(
                AutoResolvedDecisionInput(
                    rule=AutoResolvedRule.EQUIVALENT_DOCUMENT_VALUES_AUTO_CONFIRMED,
                    available_inputs=frozenset(
                        {
                            BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE,
                            BlockerMinimumInput.EQUIVALENT_NORMALIZED_VALUES,
                        }
                    ),
                )
            )
            candidate.non_blocking_decisions.append(
                BlockerDecisionRecord(
                    decision_id=uuid5(
                        NAMESPACE_URL,
                        f"blocker-decision:{record.case_id}:{evidence_version}",
                    ),
                    case_id=record.case_id,
                    evidence_version=evidence_version,
                    automation_version=record.version + 1,
                    recorded_at=self._clock(),
                    metadata=metadata,
                )
            )
            changed = True
        return candidate if changed else record

    @staticmethod
    def _decision_inputs_for_exception(
        *,
        stage: AutomationStage,
        blocker_codes: tuple[str, ...],
        actions: tuple[ExceptionResolutionAction, ...],
    ) -> frozenset[BlockerMinimumInput]:
        inputs = {
            BlockerMinimumInput.CURRENT_CASE_VERSION,
            BlockerMinimumInput.CURRENT_EXCEPTION_VERSION,
        }
        if stage == AutomationStage.GOLDTIER_SEARCH:
            inputs.add(BlockerMinimumInput.CURRENT_SEARCH_CHECKPOINT)
        elif stage == AutomationStage.DOCUMENT:
            inputs.add(BlockerMinimumInput.CURRENT_DOCUMENT_EVIDENCE)
        elif stage == AutomationStage.OWNERSHIP:
            inputs.add(BlockerMinimumInput.CURRENT_OWNERSHIP_EVIDENCE)
        elif stage == AutomationStage.MOCK_GOLDTIER:
            inputs.add(BlockerMinimumInput.CURRENT_TARGET_LEDGER)
        if any("RECONCILIATION" in code or "SOURCE_CONFLICT" in code for code in blocker_codes):
            inputs.add(BlockerMinimumInput.CURRENT_RECONCILIATION_EVIDENCE)
            if actions:
                inputs.add(BlockerMinimumInput.AUTHORIZED_RECONCILIATION_ACTION)
        if "TARGET_CONFIRMATION_REQUIRED" in blocker_codes:
            inputs.add(BlockerMinimumInput.CURRENT_FROZEN_TARGET_REVIEW)
        if "MOCK_RISK_REVIEW_REQUIRED" in blocker_codes:
            inputs.add(BlockerMinimumInput.CURRENT_MOCK_RISK_EVIDENCE)
        if "ENTITY_RESOLUTION_REVIEW_REQUIRED" in blocker_codes:
            inputs.add(BlockerMinimumInput.CURRENT_ENTITY_RESOLUTION_EVIDENCE)
        return frozenset(inputs)

    @staticmethod
    def _decision_actions_for_code(blocker_code: str) -> frozenset[BlockerDecisionAction]:
        supported = {
            "INITIAL_IDENTITY_INCOMPLETE": BlockerDecisionAction.CORRECT_INITIAL_IDENTITY,
            "GT_SEARCH_IDENTITY_REVIEW_REQUIRED": (
                BlockerDecisionAction.RUN_READ_ONLY_SEARCH_RECHECK
            ),
            "DOCUMENT_TEXT_UNAVAILABLE": BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT,
            "DOCUMENT_AMBIGUOUS_EXTRACTION": BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT,
            "DOCUMENT_REQUIRED_FIELD_MISSING": (
                BlockerDecisionAction.UPLOAD_REPLACEMENT_DOCUMENT
            ),
            "DOCUMENT_LOW_CONFIDENCE": BlockerDecisionAction.COMPLETE_DOCUMENT_REVIEW,
            "DOCUMENT_REVIEW_REQUIRED": BlockerDecisionAction.COMPLETE_DOCUMENT_REVIEW,
            "OWNERSHIP_CYCLE": BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE,
            "OWNERSHIP_INCOMPLETE": (
                BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE
            ),
            "OWNERSHIP_REVIEW_REQUIRED": (
                BlockerDecisionAction.PROVIDE_CORRECTED_OWNERSHIP_EVIDENCE
            ),
            "GOVERNMENT_STATUS_REQUIRED": BlockerDecisionAction.CONFIRM_GOVERNMENT_STATUS,
            "GOLDTIER_CLASSIFICATION_REQUIRED": (
                BlockerDecisionAction.SELECT_TARGET_CLASSIFICATION
            ),
            "TARGET_CONFIRMATION_REQUIRED": (
                BlockerDecisionAction.CONFIRM_FROZEN_TARGET_SUBMISSION
            ),
        }
        action = supported.get(blocker_code)
        return frozenset() if action is None else frozenset({action})

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
        registry_evidence_generation: int | None = None,
        persist: bool = True,
    ) -> ZeroTouchAutomationRecord:
        for existing in record.active_exceptions:
            if (
                existing.exception_type == exception_type
                and existing.evidence_version == evidence_version
            ):
                return record
        if (registry_evidence_generation is None
            and stage in {AutomationStage.OWNERSHIP, AutomationStage.READINESS}
            and exception_type in _OWNERSHIP_DEPENDENCY_EXCEPTION_TYPES):
            registry_evidence_generation = self._ownership.current_registry_dependency_generation(
                case_id=record.case_id, evidence_version=evidence_version,
            )
        candidate = record.model_copy(deep=True)
        candidate.status = AutomationStatus.WAITING_FOR_REVIEW
        candidate.current_stage = stage
        bound_codes = blocker_codes or (blocker_code,)
        bound_exception_id = exception_id or self._uuid_factory()
        created_at = self._clock()
        current_actions = frozenset(
            action for code in bound_codes for action in self._decision_actions_for_code(code)
        )
        case = self._cases.get_case(record.case_id)
        clm = self._clm.get(case_id=record.case_id)
        if (
            blocker_code == "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
            and case is not None and clm is not None
            and can_confirm_existing_customer(case, clm.target_search_checkpoint)
        ):
            current_actions |= frozenset({BlockerDecisionAction.CONFIRM_EXISTING_GOLDTIER_CUSTOMER})
        decision_metadata = self._blocker_decision_policy.evaluate_open_exception(
            OpenBlockerDecisionInput(
                exception_type=exception_type,
                blocker_codes=bound_codes,
                available_inputs=self._decision_inputs_for_exception(
                    stage=stage,
                    blocker_codes=bound_codes,
                    actions=actions,
                ),
                available_actions=current_actions,
                available_resolution_actions=frozenset(actions),
            )
        )
        decisions = tuple(
            BlockerDecisionRecord(
                decision_id=uuid5(
                    NAMESPACE_URL,
                    f"blocker-decision:{bound_exception_id}:{metadata.blocker_code}",
                ),
                case_id=record.case_id,
                exception_id=bound_exception_id,
                evidence_version=evidence_version,
                automation_version=record.version + 1,
                recorded_at=created_at,
                metadata=metadata,
            )
            for metadata in decision_metadata
        )
        candidate.exceptions.append(
            BusinessException(
                exception_id=bound_exception_id,
                case_id=record.case_id,
                exception_type=exception_type,
                stage=stage,
                blocker_code=blocker_code,
                blocker_codes=bound_codes,
                explanation=explanation,
                evidence_version=evidence_version,
                authoritative_evidence_digest=self._authoritative_evidence_digest(
                    case_id=record.case_id,
                    exception_type=exception_type,
                    evidence_version=evidence_version,
                    blocker_codes=bound_codes,
                ),
                automation_version=record.version + 1,
                registry_evidence_generation=registry_evidence_generation,
                evidence=evidence,
                available_actions=actions,
                decisions=decisions,
                created_at=created_at,
            )
        )
        candidate.current_stage = _earliest_open_stage(candidate)
        candidate.metrics.exceptions_raised += 1
        candidate = self._append_event(
            candidate,
            event_type=AutomationEventType.BUSINESS_EXCEPTION_RAISED,
            outcome=EventOutcome.REVIEW_REQUIRED,
            code=blocker_code,
            message="Automation paused at a typed human-review exception.",
        )
        return self._save(record, candidate) if record.version and persist else candidate

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
        candidate.status = (
            AutomationStatus.WAITING_FOR_REVIEW
            if candidate.active_exceptions else AutomationStatus.RUNNING
        )
        candidate.current_stage = (
            _earliest_open_stage(candidate) if candidate.active_exceptions else _stage_after(stage)
        )
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

    def _append_intelligence_event(
        self,
        record: ZeroTouchAutomationRecord,
        intelligence: OnboardingIntelligenceRecord,
    ) -> ZeroTouchAutomationRecord:
        code = "ONBOARDING_INTELLIGENCE_V1"
        if any(
            event.event_type == AutomationEventType.INTELLIGENCE_EVALUATED and event.code == code
            for event in record.events
        ):
            return record
        return self._append_event(
            record,
            event_type=AutomationEventType.INTELLIGENCE_EVALUATED,
            outcome=EventOutcome.SUCCEEDED,
            code=code,
            message=(
                "Advisory onboarding intelligence was evaluated under "
                f"policy catalogue v{intelligence.policy_catalogue_version}."
            ),
        )

    def _create(self, record: ZeroTouchAutomationRecord) -> ZeroTouchAutomationRecord:
        try:
            return self._repository.save(record, expected_version=None)
        except ZeroTouchRepositoryConflictError:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_CASE_ALREADY_EXISTS",
                message="A zero-touch automation record already exists for this case.",
            ) from None

    def _discard_failed_establishment(
        self,
        case_id: UUID,
        establishment_rollback: Callable[[UUID], None] | None,
    ) -> None:
        """Bound rollback to the case aggregate created by this failed attempt."""

        binding_id: str | None = None
        try:
            if self._establishment_discard is not None:
                binding_id = self._establishment_discard(case_id)
            else:
                automation = self._repository.get_for_case(case_id)
                if automation is not None:
                    binding_id = automation.ownership_provider_binding_id
                self._repository.delete_for_case(case_id)
                self._clm.discard_case_establishment(case_id)
                self._cases.case_repository.delete_for_case(case_id)
        finally:
            if binding_id is not None:
                self._ownership_provider_bindings.release(binding_id)
            if establishment_rollback is not None:
                establishment_rollback(case_id)

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
        except ValueError:
            # A rejected domain transition never becomes an accepted checkpoint or
            # a raw API exception. Keep the last durable state; do not dispatch.
            raise ZeroTouchInfrastructureError(
                case_id=previous.case_id, automation_id=previous.automation_id,
                code="ZERO_TOUCH_TRANSITION_REJECTED",
                message="Onboarding could not accept the workflow transition safely.",
            ) from None

    def _require_record(self, case_id: UUID) -> ZeroTouchAutomationRecord:
        record = self._repository.get_for_case(case_id)
        if record is None:
            raise ZeroTouchRequestError(
                code="ZERO_TOUCH_CASE_NOT_FOUND",
                message="The zero-touch onboarding case was not found.",
            )
        return record


def _allows_retained_evidence_intake(record: ZeroTouchAutomationRecord) -> bool:
    if record.status != AutomationStatus.WAITING_FOR_REVIEW:
        return False
    if record.current_stage == AutomationStage.GOLDTIER_SEARCH:
        return True
    return any(
        item.stage == AutomationStage.REGISTRY
        and item.blocker_code
        in {
            "REGISTRY_EXPECTED_DATA_MISSING",
            "INITIAL_IDENTITY_INCOMPLETE",
            "ACRA_ENTITY_NOT_FOUND",
            "GOVERNMENT_IDENTITY_NOT_FOUND",
            "ENTITY_CATEGORY_MISMATCH",
            "UEN_ENTITY_TYPE_UNSUPPORTED",
        }
        for item in record.active_exceptions
    )


def _earliest_open_stage(record: ZeroTouchAutomationRecord) -> AutomationStage:
    """Project dependencies using the same versioned order as domain validation.

    Exception order and timestamps remain audit facts. Currentness is normalized
    by the owning services before this projection; it does not infer currentness.
    """
    return min((item.stage for item in record.active_exceptions),
               key=_stage_order(record).index)


def _stage_order(record: ZeroTouchAutomationRecord) -> tuple[AutomationStage, ...]:
    return tuple(AutomationStage(value) for value in (
        LEGACY_AUTOMATION_STAGE_ORDER
        if record.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
        else AUTOMATION_STAGE_ORDER
    ))


def _has_unproved_prerequisite(record: ZeroTouchAutomationRecord) -> bool:
    """Existing progression may prove only dependencies strictly before a blocker.

    Human decisions remain OPEN. The normal document/ownership/readiness owners
    evaluate evidence; completing a prerequisite does not authorize crossing the
    earliest current blocker, and target mutations remain behind that boundary.
    """
    if not record.active_exceptions:
        return False
    order = _stage_order(record)
    return len(record.completed_stages) < order.index(_earliest_open_stage(record))


def _next_stage(
    completed: tuple[AutomationStage, ...], *, order: tuple[AutomationStage, ...] | None = None,
) -> AutomationStage:
    for stage in order if order is not None else tuple(
        AutomationStage(value) for value in AUTOMATION_STAGE_ORDER
    ):
        if stage not in completed:
            return stage
    return AutomationStage.COMPLETE


def _stage_after(stage: AutomationStage) -> AutomationStage:
    stages = {
        AutomationStage.REGISTRY: AutomationStage.GOLDTIER_SEARCH,
        AutomationStage.GOLDTIER_SEARCH: AutomationStage.DOCUMENT,
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
        prefix, raw_version, raw_document_version, fingerprint = value.split(":", maxsplit=3)
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
