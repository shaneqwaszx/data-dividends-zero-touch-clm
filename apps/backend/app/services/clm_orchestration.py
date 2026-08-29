"""Deterministic Phase 05 readiness and serialized Mock GoldTier orchestration."""

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from threading import RLock
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.clm import (
    ClmBlockerCode,
    ClmEventType,
    ClmOrchestrationRecord,
    ClmReadinessAssessment,
    ClmStatus,
    ClmSubmissionSnapshot,
    ClmWarningCode,
    ClmWorkflowEvent,
    EvidenceReference,
    GoldTierSubmissionPlan,
    ProvisionalUboSummary,
    ReadinessStageStatus,
    RelatedPartySubmissionPreparation,
    StageReadiness,
)
from app.domain.documents import (
    DocumentAutoClearBlocker,
    DocumentProcessingRecord,
    DocumentProcessingState,
)
from app.domain.models import (
    EventOutcome,
    GoldTierResult,
    OnboardingCase,
    SafeError,
    WorkflowState,
)
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipCandidateClassification,
)
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierExecutionLedgerState,
    GoldTierExecutionReceipt,
)
from app.services.canonical_validation import validate_entity
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.clm_repository import (
    ClmOrchestrationRepository,
    ClmRepositoryConflictError,
)
from app.services.document_processing import (
    DocumentProcessingService,
    document_semantic_assessment,
)
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService

REAL_INTEGRATION_WARNINGS = [
    ClmWarningCode.IDP_PROFILE_PROVISIONAL,
    ClmWarningCode.UBO_POLICY_NOT_SPONSOR_CONFIRMED,
    ClmWarningCode.LIVE_HIERARCHY_UNAVAILABLE,
    ClmWarningCode.RELATED_PARTY_MAPPING_PENDING,
    ClmWarningCode.REAL_GOLDTIER_NOT_CONFIGURED,
    ClmWarningCode.READY_FOR_APPROVAL_UNAVAILABLE,
]


class ReconciliationReadiness(Protocol):
    def is_currently_cleared(self, *, case_id: UUID) -> bool: ...


class ClmOrchestrationService:
    """Compose current case evidence without copying subsystem source records."""

    def __init__(
        self,
        *,
        cases: OnboardingService,
        documents: DocumentProcessingService,
        ownership: OwnershipAnalysisService,
        repository: ClmOrchestrationRepository,
        reconciliation: ReconciliationReadiness | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._cases = cases
        self._documents = documents
        self._ownership = ownership
        self._repository = repository
        self._reconciliation = reconciliation
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    def create_case(
        self, uen: str, country_of_incorporation: str | None = None
    ) -> ClmOrchestrationRecord:
        """Create a registry-validated staged case and stop before GoldTier."""

        try:
            case = self._cases.create_staged_case(uen, country_of_incorporation)
        except OnboardingInfrastructureError as exc:
            failed_case = self._cases.get_case(exc.case_id)
            if failed_case is None:
                raise
            record = self._create_record(failed_case)
            raise ClmInfrastructureError(
                case_id=record.case_id,
                orchestration_id=record.orchestration_id,
                correlation_id=record.correlation_id,
                code=exc.code,
                message=exc.public_message,
            ) from None
        return self._create_record(case)

    def get(self, *, case_id: UUID) -> ClmOrchestrationRecord | None:
        record = self._repository.get_for_case(case_id)
        if record is None:
            return None
        if record.submission_snapshot is not None or record.status == ClmStatus.SUBMITTING:
            return record
        case = self._cases.get_case(case_id)
        if case is None:
            return record
        readiness = self._evaluate_current(case)
        return record.model_copy(
            update={
                "status": _status_for_readiness(case, readiness),
                "readiness": readiness,
                "updated_at": max(record.updated_at, readiness.evaluated_at),
            },
            deep=True,
        )

    def attempted_target_operations(self, *, case_id: UUID) -> tuple[str, ...]:
        """Expose safe operation names for sponsor UAT evidence, never payloads."""

        record = self._repository.get_for_case(case_id)
        if record is None or record.submission_snapshot is None:
            return ()
        return tuple(
            marker.value
            for marker in self._cases.get_attempted_target_operations(
                record.submission_snapshot.submission_id
            )
        )

    def evaluate(self, *, case_id: UUID) -> ClmOrchestrationRecord:
        with self._lock_for(case_id):
            record = self._require_record(case_id)
            if record.submission_snapshot is not None:
                return record
            case = self._require_case(case_id)
            readiness = self._evaluate_current(case)
            candidate = record.model_copy(deep=True)
            candidate.readiness = readiness
            candidate.status = _status_for_readiness(case, readiness)
            candidate.error = None
            return self._record_event(
                record,
                candidate,
                event_type=ClmEventType.READINESS_EVALUATED,
                outcome=(
                    EventOutcome.SUCCEEDED
                    if candidate.status == ClmStatus.READY_FOR_MOCK_SUBMISSION
                    else EventOutcome.REVIEW_REQUIRED
                ),
                code=(
                    None
                    if candidate.status == ClmStatus.READY_FOR_MOCK_SUBMISSION
                    else candidate.status.value
                ),
                message=(
                    "Current authoritative evidence is ready for Mock GoldTier submission."
                    if candidate.status == ClmStatus.READY_FOR_MOCK_SUBMISSION
                    else "Current authoritative evidence does not yet permit Mock submission."
                ),
            )

    def submission_plan(self, *, case_id: UUID) -> GoldTierSubmissionPlan:
        return self._require_record(case_id).submission_plan.model_copy(deep=True)

    def submit(self, *, case_id: UUID) -> ClmOrchestrationRecord:
        """Revalidate evidence inside a per-case boundary, snapshot, and submit once."""

        with self._lock_for(case_id):
            record = self._require_record(case_id)
            if record.submission_snapshot is not None and record.status in {
                ClmStatus.MOCK_GOLDTIER_SUBMITTED,
                ClmStatus.REVIEW_REQUIRED,
                ClmStatus.FAILED,
            }:
                return record

            if record.submission_snapshot is None:
                record = self._start_submission(record)
            snapshot = record.submission_snapshot
            if snapshot is None:
                raise ClmRequestError(
                    code="CLM_SNAPSHOT_NOT_AVAILABLE",
                    message="Submission evidence is incomplete.",
                )

            receipt = record.execution_receipt
            if receipt is None:
                receipt = self._cases.get_execution_receipt(snapshot.submission_id)
            if receipt is None:
                execution_state = self._cases.get_execution_state(snapshot.submission_id)
                if execution_state == GoldTierExecutionLedgerState.IN_PROGRESS:
                    raise ClmRequestError(
                        code="CLM_SUBMISSION_IN_PROGRESS",
                        message="Mock GoldTier submission is already in progress.",
                    ) from None
                try:
                    receipt = self._cases.execute_submission_input(snapshot.target_input)
                except Exception:
                    receipt = self._cases.get_execution_receipt(snapshot.submission_id)
                    if receipt is None:
                        execution_state = self._cases.get_execution_state(snapshot.submission_id)
                        if execution_state == GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED:
                            raise ClmInfrastructureError(
                                case_id=record.case_id,
                                orchestration_id=record.orchestration_id,
                                correlation_id=record.correlation_id,
                                code="CLM_FINALIZATION_RETRY_REQUIRED",
                                message=(
                                    "Mock GoldTier execution was retained but "
                                    "finalization must be retried."
                                ),
                            ) from None
                        if execution_state == GoldTierExecutionLedgerState.IN_PROGRESS:
                            raise ClmRequestError(
                                code="CLM_SUBMISSION_IN_PROGRESS",
                                message="Mock GoldTier submission is already in progress.",
                            ) from None
                        raise ClmInfrastructureError(
                            case_id=record.case_id,
                            orchestration_id=record.orchestration_id,
                            correlation_id=record.correlation_id,
                            code="CLM_SUBMISSION_UNEXPECTED_FAILURE",
                            message="Mock GoldTier submission could not be completed.",
                        ) from None

            if record.execution_receipt is None:
                record = self._persist_execution_receipt(record, receipt)

            try:
                completed = self._finalize_execution(record, receipt)
            except Exception:
                raise ClmInfrastructureError(
                    case_id=record.case_id,
                    orchestration_id=record.orchestration_id,
                    correlation_id=record.correlation_id,
                    code="CLM_FINALIZATION_RETRY_REQUIRED",
                    message=(
                        "Mock GoldTier execution was retained but finalization must be retried."
                    ),
                ) from None

            if receipt.infrastructure_failure:
                error = receipt.error
                raise ClmInfrastructureError(
                    case_id=completed.case_id,
                    orchestration_id=completed.orchestration_id,
                    correlation_id=completed.correlation_id,
                    code=error.code if error is not None else "GT_OPERATION_FAILED",
                    message=(
                        error.message
                        if error is not None
                        else "Mock GoldTier submission could not be completed."
                    ),
                ) from None
            return completed

    def _start_submission(self, record: ClmOrchestrationRecord) -> ClmOrchestrationRecord:
        case = self._require_case(record.case_id)
        documents = [
            item
            for item in self._documents.list_documents(case_id=record.case_id)
            if item.is_current_evidence
        ]
        ownership = self._ownership.get(case_id=record.case_id)
        readiness = _evaluate_readiness(
            case=case,
            documents=documents,
            ownership=ownership,
            document_confidence_threshold=self._documents.review_confidence_threshold,
            reconciliation_cleared=(
                self._reconciliation.is_currently_cleared(case_id=record.case_id)
                if self._reconciliation is not None
                else False
            ),
            now=self._clock(),
        )
        if readiness.blockers:
            candidate = record.model_copy(deep=True)
            candidate.readiness = readiness
            candidate.status = _status_for_readiness(case, readiness)
            self._record_event(
                record,
                candidate,
                event_type=ClmEventType.READINESS_EVALUATED,
                outcome=EventOutcome.REVIEW_REQUIRED,
                code="CLM_NOT_READY",
                message="Mock submission was blocked by current authoritative evidence.",
            )
            raise ClmRequestError(
                code="CLM_NOT_READY",
                message="The case is not ready for Mock GoldTier submission.",
            ) from None

        snapshot, preparation = self._build_snapshot(
            case=case,
            documents=documents,
            ownership=ownership,
        )
        submitting = record.model_copy(deep=True)
        submitting.status = ClmStatus.SUBMITTING
        submitting.readiness = readiness
        submitting.submission_snapshot = snapshot
        submitting.related_party_preparation = preparation
        submitting.error = None
        return self._record_event(
            record,
            submitting,
            event_type=ClmEventType.MOCK_SUBMISSION_STARTED,
            outcome=EventOutcome.SUCCEEDED,
            code="MOCK_SUBMISSION_STARTED",
            message="Serialized Mock GoldTier base submission started.",
        )

    def _persist_execution_receipt(
        self,
        record: ClmOrchestrationRecord,
        receipt: GoldTierExecutionReceipt,
    ) -> ClmOrchestrationRecord:
        snapshot = record.submission_snapshot
        if (
            snapshot is None
            or receipt.submission_id != snapshot.submission_id
            or receipt.case_id != record.case_id
            or receipt.correlation_id != snapshot.correlation_id
            or receipt.input_fingerprint
            != sha256(snapshot.target_input.model_dump_json().encode("utf-8")).hexdigest()
        ):
            raise ClmRequestError(
                code="CLM_EXECUTION_BINDING_INVALID",
                message="The retained Mock execution does not match this submission.",
            )
        candidate = record.model_copy(deep=True)
        candidate.execution_receipt = receipt
        try:
            return self._record_event(
                record,
                candidate,
                event_type=ClmEventType.MOCK_TARGET_EXECUTION_RECORDED,
                outcome=EventOutcome.SUCCEEDED,
                code="MOCK_TARGET_EXECUTION_RECORDED",
                message="Safe Mock target execution receipt retained for finalization.",
            )
        except Exception:
            raise ClmInfrastructureError(
                case_id=record.case_id,
                orchestration_id=record.orchestration_id,
                correlation_id=record.correlation_id,
                code="CLM_FINALIZATION_RETRY_REQUIRED",
                message="Mock GoldTier execution was retained but finalization must be retried.",
            ) from None

    def _finalize_execution(
        self,
        record: ClmOrchestrationRecord,
        receipt: GoldTierExecutionReceipt,
    ) -> ClmOrchestrationRecord:
        candidate, event_type, outcome, code, message = _terminal_from_receipt(record, receipt)
        return self._record_event(
            record,
            candidate,
            event_type=event_type,
            outcome=outcome,
            code=code,
            message=message,
        )

    def _create_record(self, case: OnboardingCase) -> ClmOrchestrationRecord:
        now = self._clock()
        readiness = self._evaluate_current(case, now=now)
        status = _status_for_readiness(case, readiness)
        record = ClmOrchestrationRecord(
            case_id=case.case_id,
            orchestration_id=self._uuid_factory(),
            correlation_id=self._uuid_factory(),
            status=status,
            readiness=readiness,
            submission_plan=GoldTierSubmissionPlan(),
            error=case.error if status == ClmStatus.FAILED else None,
            created_at=now,
            updated_at=now,
        )
        record.events.append(
            ClmWorkflowEvent(
                sequence=1,
                event_type=ClmEventType.CLM_CASE_CREATED,
                status=status,
                outcome=EventOutcome.SUCCEEDED,
                timestamp=now,
                case_id=record.case_id,
                orchestration_id=record.orchestration_id,
                correlation_id=record.correlation_id,
                code="CLM_CASE_CREATED",
                message="Staged CLM orchestration record created.",
            )
        )
        if readiness.registry.status == ReadinessStageStatus.READY:
            event_type = ClmEventType.REGISTRY_READY
            outcome = EventOutcome.SUCCEEDED
            code = "REGISTRY_READY"
            message = "Canonical ACRA registry evidence is ready."
        elif readiness.registry.status == ReadinessStageStatus.FAILED:
            event_type = ClmEventType.CLM_CASE_FAILED
            outcome = EventOutcome.FAILED
            code = case.error.code if case.error else "REGISTRY_FAILED"
            message = "Registry intake failed before downstream evidence collection."
        else:
            event_type = ClmEventType.CLM_REVIEW_REQUIRED
            outcome = EventOutcome.REVIEW_REQUIRED
            code = "REGISTRY_NOT_READY"
            message = "Registry intake requires human review before submission."
        record.events.append(
            ClmWorkflowEvent(
                sequence=2,
                event_type=event_type,
                status=status,
                outcome=outcome,
                timestamp=now,
                case_id=record.case_id,
                orchestration_id=record.orchestration_id,
                correlation_id=record.correlation_id,
                code=code,
                message=message,
            )
        )
        try:
            return self._repository.save(record, expected_version=None)
        except ClmRepositoryConflictError:
            raise ClmRequestError(
                code="CLM_CASE_ALREADY_EXISTS",
                message="A CLM orchestration record already exists for this case.",
            ) from None

    def _evaluate_current(
        self, case: OnboardingCase, *, now: datetime | None = None
    ) -> ClmReadinessAssessment:
        documents = [
            item
            for item in self._documents.list_documents(case_id=case.case_id)
            if item.is_current_evidence
        ]
        ownership = self._ownership.get(case_id=case.case_id)
        return _evaluate_readiness(
            case=case,
            documents=documents,
            ownership=ownership,
            document_confidence_threshold=self._documents.review_confidence_threshold,
            reconciliation_cleared=(
                self._reconciliation.is_currently_cleared(case_id=case.case_id)
                if self._reconciliation is not None
                else False
            ),
            now=now or self._clock(),
        )

    def _build_snapshot(
        self,
        *,
        case: OnboardingCase,
        documents: list[DocumentProcessingRecord],
        ownership: OwnershipAnalysisRecord | None,
    ) -> tuple[ClmSubmissionSnapshot, RelatedPartySubmissionPreparation]:
        entity = case.entity
        if entity is None or ownership is None or validate_entity(entity):
            raise ClmRequestError(
                code="CLM_SNAPSHOT_NOT_AVAILABLE",
                message="Submission evidence is incomplete.",
            )
        candidate_ids = sorted(
            candidate.party.party_id
            for candidate in ownership.candidates
            if candidate.classification
            == OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
        )
        target_input = self._cases.build_submission_input(
            case,
            submission_id=self._uuid_factory(),
            correlation_id=self._uuid_factory(),
            accepted_at=self._clock(),
        )
        snapshot = ClmSubmissionSnapshot(
            snapshot_id=self._uuid_factory(),
            target_input=target_input,
            document_references=tuple(
                EvidenceReference(
                    reference_id=document.document_id,
                    version=len(document.events),
                    status=(
                        document.state.value
                        if document.state == DocumentProcessingState.REVIEWED
                        else "RECONCILIATION_RESOLVED"
                    ),
                    updated_at=document.updated_at,
                )
                for document in documents
                if document.state == DocumentProcessingState.REVIEWED
                or (
                    self._reconciliation is not None
                    and self._reconciliation.is_currently_cleared(case_id=case.case_id)
                )
            ),
            ownership_reference=EvidenceReference(
                reference_id=ownership.analysis_id,
                version=ownership.version,
                status=ownership.state.value,
                updated_at=ownership.updated_at,
            ),
            provisional_ubo=ProvisionalUboSummary(
                candidate_count=len(candidate_ids),
                internal_party_ids=tuple(candidate_ids),
            ),
            created_at=self._clock(),
        )
        preparation = RelatedPartySubmissionPreparation(
            provisional_candidate_count=len(candidate_ids),
            internal_party_ids=tuple(candidate_ids),
            analysis_reference=ownership.analysis_id,
        )
        return snapshot, preparation

    def _record_event(
        self,
        previous: ClmOrchestrationRecord,
        candidate: ClmOrchestrationRecord,
        *,
        event_type: ClmEventType,
        outcome: EventOutcome,
        code: str | None,
        message: str,
    ) -> ClmOrchestrationRecord:
        timestamp = self._clock()
        candidate.updated_at = timestamp
        candidate.events.append(
            _build_clm_event(
                sequence=len(candidate.events) + 1,
                event_type=event_type,
                status=candidate.status,
                outcome=outcome,
                timestamp=timestamp,
                case_id=candidate.case_id,
                orchestration_id=candidate.orchestration_id,
                correlation_id=candidate.correlation_id,
                code=code,
                message=message,
            )
        )
        try:
            return self._repository.save(candidate, expected_version=previous.version)
        except ClmRepositoryConflictError:
            raise ClmRequestError(
                code="CLM_ORCHESTRATION_CONFLICT",
                message="The CLM case changed during this operation.",
            ) from None

    def _require_record(self, case_id: UUID) -> ClmOrchestrationRecord:
        record = self._repository.get_for_case(case_id)
        if record is None:
            raise ClmRequestError(
                code="CLM_CASE_NOT_FOUND",
                message="The staged CLM case was not found.",
            )
        return record

    def _require_case(self, case_id: UUID) -> OnboardingCase:
        case = self._cases.get_case(case_id)
        if case is None:
            raise ClmRequestError(
                code="CLM_CASE_NOT_FOUND",
                message="The staged CLM case was not found.",
            )
        return case

    def _lock_for(self, case_id: UUID) -> RLock:
        return self._cases.case_lock(case_id)


def _evaluate_readiness(
    *,
    case: OnboardingCase,
    documents: list[DocumentProcessingRecord],
    ownership: OwnershipAnalysisRecord | None,
    document_confidence_threshold: float,
    now: datetime,
    reconciliation_cleared: bool = False,
) -> ClmReadinessAssessment:
    blockers: list[ClmBlockerCode] = []

    def block(code: ClmBlockerCode) -> None:
        if code not in blockers:
            blockers.append(code)

    if case.state == WorkflowState.FAILED:
        registry = StageReadiness(status=ReadinessStageStatus.FAILED)
        block(ClmBlockerCode.REGISTRY_FAILED)
    elif case.state != WorkflowState.VALIDATED:
        registry = StageReadiness(status=ReadinessStageStatus.REVIEW_REQUIRED)
        block(ClmBlockerCode.REGISTRY_NOT_READY)
    elif case.entity is None or validate_entity(case.entity):
        registry = StageReadiness(status=ReadinessStageStatus.BLOCKED)
        block(ClmBlockerCode.CANONICAL_DATA_INVALID)
    else:
        registry = StageReadiness(
            status=ReadinessStageStatus.READY,
            reference_id=str(case.case_id),
        )

    if not documents:
        document_stage = StageReadiness(status=ReadinessStageStatus.MISSING)
        block(ClmBlockerCode.DOCUMENT_REQUIRED)
    else:
        if any(item.state == DocumentProcessingState.PROCESSING for item in documents):
            block(ClmBlockerCode.DOCUMENT_PROCESSING)
        if any(item.state == DocumentProcessingState.FAILED for item in documents):
            block(ClmBlockerCode.DOCUMENT_PROCESSING_FAILED)
        reviewed = [item for item in documents if item.state == DocumentProcessingState.REVIEWED]
        if not reconciliation_cleared:
            if any(item.state == DocumentProcessingState.REVIEW_REQUIRED for item in documents):
                block(ClmBlockerCode.DOCUMENT_REVIEW_INCOMPLETE)
            if not reviewed:
                block(ClmBlockerCode.DOCUMENT_REVIEW_INCOMPLETE)
            for item in reviewed:
                assessment = document_semantic_assessment(
                    record=item,
                    current_entity=case.entity,
                    confidence_threshold=document_confidence_threshold,
                )
                if DocumentAutoClearBlocker.SOURCE_CONFLICT in assessment.blockers:
                    block(ClmBlockerCode.SOURCE_CONFLICT_REQUIRES_POLICY)
                if any(
                    blocker
                    in {
                        DocumentAutoClearBlocker.LOW_CONFIDENCE,
                        DocumentAutoClearBlocker.REQUIRED_FIELD_MISSING,
                        DocumentAutoClearBlocker.REVIEW_STATE_INVALID,
                    }
                    for blocker in assessment.blockers
                ):
                    block(ClmBlockerCode.DOCUMENT_REVIEW_INCOMPLETE)
        document_blockers = {
            ClmBlockerCode.DOCUMENT_PROCESSING,
            ClmBlockerCode.DOCUMENT_REVIEW_INCOMPLETE,
            ClmBlockerCode.DOCUMENT_PROCESSING_FAILED,
            ClmBlockerCode.SOURCE_CONFLICT_REQUIRES_POLICY,
        }.intersection(blockers)
        if not document_blockers:
            document_stage = StageReadiness(
                status=ReadinessStageStatus.READY,
                reference_id=str(documents[-1].document_id),
            )
        elif ClmBlockerCode.DOCUMENT_PROCESSING_FAILED in document_blockers:
            document_stage = StageReadiness(status=ReadinessStageStatus.FAILED)
        elif ClmBlockerCode.DOCUMENT_PROCESSING in document_blockers:
            document_stage = StageReadiness(status=ReadinessStageStatus.IN_PROGRESS)
        else:
            document_stage = StageReadiness(status=ReadinessStageStatus.REVIEW_REQUIRED)

    if ownership is None:
        ownership_stage = StageReadiness(status=ReadinessStageStatus.MISSING)
        block(ClmBlockerCode.OWNERSHIP_REQUIRED)
    elif ownership.state == OwnershipAnalysisState.ANALYZED:
        ownership_stage = StageReadiness(
            status=ReadinessStageStatus.READY,
            reference_id=str(ownership.analysis_id),
        )
    elif ownership.state == OwnershipAnalysisState.REVIEW_REQUIRED:
        ownership_stage = StageReadiness(status=ReadinessStageStatus.REVIEW_REQUIRED)
        block(ClmBlockerCode.OWNERSHIP_REVIEW_REQUIRED)
    elif ownership.state == OwnershipAnalysisState.FAILED:
        ownership_stage = StageReadiness(status=ReadinessStageStatus.FAILED)
        block(ClmBlockerCode.OWNERSHIP_ANALYSIS_FAILED)
    else:
        ownership_stage = StageReadiness(status=ReadinessStageStatus.IN_PROGRESS)
        block(ClmBlockerCode.OWNERSHIP_ANALYSIS_INCOMPLETE)

    goldtier = StageReadiness(
        status=(ReadinessStageStatus.READY if not blockers else ReadinessStageStatus.BLOCKED)
    )
    return ClmReadinessAssessment(
        registry=registry,
        document=document_stage,
        ownership=ownership_stage,
        goldtier=goldtier,
        blockers=blockers,
        warnings=REAL_INTEGRATION_WARNINGS,
        evaluated_at=now,
    )


def _status_for_readiness(case: OnboardingCase, readiness: ClmReadinessAssessment) -> ClmStatus:
    if case.state == WorkflowState.FAILED:
        return ClmStatus.FAILED
    if not readiness.blockers:
        return ClmStatus.READY_FOR_MOCK_SUBMISSION
    review_codes = {
        ClmBlockerCode.REGISTRY_NOT_READY,
        ClmBlockerCode.CANONICAL_DATA_INVALID,
        ClmBlockerCode.DOCUMENT_REVIEW_INCOMPLETE,
        ClmBlockerCode.DOCUMENT_PROCESSING_FAILED,
        ClmBlockerCode.SOURCE_CONFLICT_REQUIRES_POLICY,
        ClmBlockerCode.OWNERSHIP_REVIEW_REQUIRED,
        ClmBlockerCode.OWNERSHIP_ANALYSIS_FAILED,
    }
    if review_codes.intersection(readiness.blockers):
        return ClmStatus.REVIEW_REQUIRED
    return ClmStatus.COLLECTING_EVIDENCE


def _terminal_from_receipt(
    record: ClmOrchestrationRecord,
    receipt: GoldTierExecutionReceipt,
) -> tuple[
    ClmOrchestrationRecord,
    ClmEventType,
    EventOutcome,
    str | None,
    str,
]:
    candidate = record.model_copy(deep=True)
    candidate.goldtier_result = (
        GoldTierResult.model_validate(receipt.result.model_dump())
        if receipt.result is not None
        else None
    )
    submission_reference = str(receipt.submission_id)

    if receipt.classification == GoldTierExecutionClassification.SUCCESS:
        candidate.status = ClmStatus.MOCK_GOLDTIER_SUBMITTED
        candidate.error = None
        candidate.readiness = candidate.readiness.model_copy(
            update={
                "goldtier": StageReadiness(
                    status=ReadinessStageStatus.SUBMITTED,
                    reference_id=submission_reference,
                )
            }
        )
        return (
            candidate,
            ClmEventType.MOCK_SUBMISSION_COMPLETED,
            EventOutcome.SUCCEEDED,
            "MOCK_GOLDTIER_SUBMITTED",
            "Accepted Mock GoldTier base operations completed.",
        )

    error = (
        SafeError(code=receipt.error.code, message=receipt.error.message)
        if receipt.error is not None
        else SafeError(
            code="CLM_SUBMISSION_FAILED",
            message="Mock GoldTier submission failed.",
        )
    )
    candidate.error = error
    if receipt.classification == GoldTierExecutionClassification.REVIEW_REQUIRED:
        candidate.status = ClmStatus.REVIEW_REQUIRED
        candidate.readiness = candidate.readiness.model_copy(
            update={
                "goldtier": StageReadiness(
                    status=ReadinessStageStatus.REVIEW_REQUIRED,
                    reference_id=submission_reference,
                )
            }
        )
        return (
            candidate,
            ClmEventType.CLM_REVIEW_REQUIRED,
            EventOutcome.REVIEW_REQUIRED,
            error.code,
            "Mock GoldTier returned an outcome requiring human review.",
        )

    candidate.status = ClmStatus.FAILED
    candidate.readiness = candidate.readiness.model_copy(
        update={"goldtier": StageReadiness(status=ReadinessStageStatus.FAILED)}
    )
    return (
        candidate,
        ClmEventType.CLM_SUBMISSION_FAILED,
        EventOutcome.FAILED,
        error.code,
        error.message,
    )


def _build_clm_event(
    *,
    sequence: int,
    event_type: ClmEventType,
    status: ClmStatus,
    outcome: EventOutcome,
    timestamp: datetime,
    case_id: UUID,
    orchestration_id: UUID,
    correlation_id: UUID,
    code: str | None,
    message: str,
) -> ClmWorkflowEvent:
    """Construct one safe event through an injectable finalization seam."""

    return ClmWorkflowEvent(
        sequence=sequence,
        event_type=event_type,
        status=status,
        outcome=outcome,
        timestamp=timestamp,
        case_id=case_id,
        orchestration_id=orchestration_id,
        correlation_id=correlation_id,
        code=code,
        message=message,
    )
