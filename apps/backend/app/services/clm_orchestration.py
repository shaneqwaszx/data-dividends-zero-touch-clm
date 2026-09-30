"""Deterministic Phase 05 readiness and serialized Mock GoldTier orchestration."""

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from threading import RLock
from typing import Literal, Protocol
from uuid import UUID, uuid4

from app.connectors.errors import ConnectorError, public_connector_error
from app.connectors.goldtier_models import GoldTierSearchOutcome
from app.domain.access import CasePriority, TeamId
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
    GoldTierSearchCheckpoint,
    GoldTierSearchCheckpointStatus,
    GoldTierSearchDisposition,
    GoldTierSubmissionPlan,
    ProvisionalUboSummary,
    ReadinessStageStatus,
    RelatedPartySubmissionPreparation,
    RetainedGoldTierCandidate,
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
from app.domain.onboarding_intelligence import EntityResolutionOutcome
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipCandidateClassification,
)
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierExecutionLedgerState,
    GoldTierExecutionReceipt,
    GoldTierProviderClassification,
    GoldTierProviderMode,
    GoldTierSearchResolution,
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
from app.services.errors import (
    OnboardingInfrastructureError,
    TargetProviderContextMismatchError,
)
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.target_response_validation import InvalidTargetResponseError

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
        self,
        uen: str,
        country_of_incorporation: str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> ClmOrchestrationRecord:
        """Create a registry-validated staged case and stop before GoldTier."""

        case_id, correlation_id = self._cases.reserve_case_identity()
        return self.create_case_with_identity(
            case_id,
            correlation_id,
            uen,
            country_of_incorporation,
            legal_name=legal_name,
            team_id=team_id,
            priority=priority,
        )

    def create_case_with_identity(
        self,
        case_id: UUID,
        correlation_id: UUID,
        uen: str,
        country_of_incorporation: str | None = None,
        *,
        legal_name: str | None = None,
        team_id: TeamId | None = None,
        priority: CasePriority | None = None,
    ) -> ClmOrchestrationRecord:
        """Create CLM state for an identity already inside its lifecycle boundary."""

        try:
            case = self._cases.create_staged_case_with_identity(
                case_id,
                correlation_id,
                uen,
                country_of_incorporation,
                legal_name=legal_name,
                team_id=team_id,
                priority=priority,
            )
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

    def discard_case_establishment(self, case_id: UUID) -> None:
        """Remove CLM state created by an establishment attempt."""

        self._repository.delete_for_case(case_id)

    def get(self, *, case_id: UUID) -> ClmOrchestrationRecord | None:
        record = self._repository.get_for_case(case_id)
        if record is None:
            return None
        if record.submission_snapshot is not None or record.status == ClmStatus.SUBMITTING:
            return record
        case = self._cases.get_case(case_id)
        if case is None:
            return record
        readiness = self._evaluate_current(case, search_checkpoint=record.target_search_checkpoint)
        return record.model_copy(
            update={
                "status": _status_for_readiness(case, readiness),
                "readiness": readiness,
                "updated_at": max(record.updated_at, readiness.evaluated_at),
            },
            deep=True,
        )

    def refresh_target_classification(self, *, case_id: UUID) -> ClmOrchestrationRecord:
        """Refresh the case-bound target preview before any submission is frozen."""

        with self._lock_for(case_id):
            record = self._require_record(case_id)
            if record.submission_snapshot is not None:
                raise ClmRequestError(
                    code="CLM_TARGET_CLASSIFICATION_FROZEN",
                    message="Target classification is already frozen for submission.",
                )
            case = self._require_case(case_id)
            readiness = self._evaluate_current(
                case, search_checkpoint=record.target_search_checkpoint
            )
            candidate = record.model_copy(deep=True)
            candidate.submission_plan = self._build_submission_plan(case)
            candidate.readiness = readiness
            candidate.status = _status_for_readiness(case, readiness)
            candidate.error = None
            return self._record_event(
                record,
                candidate,
                event_type=ClmEventType.TARGET_CLASSIFICATION_BOUND,
                outcome=EventOutcome.SUCCEEDED,
                code="TARGET_CLASSIFICATION_BOUND",
                message="Case-specific GoldTier target classifications were retained.",
            )

    def refresh_initial_search_after_recheck(
        self, *, case_id: UUID, expected_clm_version: int
    ) -> ClmOrchestrationRecord:
        """Rebind one authorized initial Search result before submission is frozen."""

        with self._lock_for(case_id):
            record = self._require_record(case_id)
            if record.version != expected_clm_version:
                raise ClmRequestError(
                    code="CLM_IDENTITY_RECHECK_STALE",
                    message="The CLM case changed before identity recheck.",
                )
            if record.submission_snapshot is not None:
                raise ClmRequestError(
                    code="CLM_IDENTITY_RECHECK_FROZEN",
                    message="Identity Search is already frozen for submission.",
                )
            case = self._require_case(case_id)
            search = case.initial_target_search
            if search is None:
                raise ClmRequestError(
                    code="CLM_TARGET_SEARCH_NOT_AVAILABLE",
                    message="Initial target Search evidence is unavailable.",
                )
            disposition = GoldTierSearchDisposition(search.disposition)
            status = (
                GoldTierSearchCheckpointStatus.COMPLETED
                if disposition
                in {GoldTierSearchDisposition.NO_MATCH, GoldTierSearchDisposition.EXACT_MATCH}
                else GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                if disposition == GoldTierSearchDisposition.REVIEW_REQUIRED
                else GoldTierSearchCheckpointStatus.FAILED
            )
            checkpoint = GoldTierSearchCheckpoint(
                request_id=search.request_id,
                identity_fingerprint=_initial_or_canonical_identity_fingerprint(case),
                provider_mode=record.submission_plan.environment,
                provider_classification=record.submission_plan.provider_classification,
                status=status,
                disposition=disposition,
                provider_outcome=search.provider_outcome,
                status_code=search.status_code,
                candidate_count=search.candidate_count,
                candidates=tuple(
                    RetainedGoldTierCandidate(party_id=party_id, legal_name=legal_name)
                    for party_id, legal_name in zip(
                        search.candidate_party_ids,
                        search.candidate_legal_names,
                        strict=True,
                    )
                ),
                selected_party_id=search.selected_party_id,
                resolution_outcome=(
                    "EXACT_MATCH"
                    if disposition == GoldTierSearchDisposition.EXACT_MATCH
                    else None
                ),
                code=(
                    "GOLDTIER_SEARCH_RECHECK_COMPLETED"
                    if status == GoldTierSearchCheckpointStatus.COMPLETED
                    else search.provider_outcome
                ),
                message="Authorized read-only GoldTier Search recheck was retained.",
                searched_at=search.searched_at,
            )
            readiness = self._evaluate_current(case, search_checkpoint=checkpoint)
            candidate = record.model_copy(deep=True)
            candidate.target_search_checkpoint = checkpoint
            candidate.submission_plan = self._build_submission_plan(case)
            candidate.readiness = readiness
            candidate.status = _status_for_readiness(case, readiness)
            candidate.error = None
            return self._record_event(
                record,
                candidate,
                event_type=(
                    ClmEventType.GOLDTIER_SEARCH_COMPLETED
                    if status == GoldTierSearchCheckpointStatus.COMPLETED
                    else ClmEventType.GOLDTIER_SEARCH_REVIEW_REQUIRED
                    if status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                    else ClmEventType.GOLDTIER_SEARCH_FAILED
                ),
                outcome=(
                    EventOutcome.SUCCEEDED
                    if status == GoldTierSearchCheckpointStatus.COMPLETED
                    else EventOutcome.REVIEW_REQUIRED
                    if status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                    else EventOutcome.FAILED
                ),
                code=checkpoint.code,
                message=checkpoint.message,
            )

    def attempted_target_operations(self, *, case_id: UUID) -> tuple[str, ...]:
        """Expose safe operation names for sponsor UAT evidence, never payloads."""

        record = self._repository.get_for_case(case_id)
        if record is None:
            return ()
        if record.submission_snapshot is None:
            return ("SEARCH",) if record.target_search_checkpoint is not None else ()
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
            if (
                record.target_search_checkpoint is None
                or record.target_search_checkpoint.identity_fingerprint
                != _target_identity_fingerprint(case)
            ):
                record = self._perform_early_search(record, case)
            readiness = self._evaluate_current(
                case, search_checkpoint=record.target_search_checkpoint
            )
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
                    "Current authoritative evidence is ready for GoldTier target submission."
                    if candidate.status == ClmStatus.READY_FOR_MOCK_SUBMISSION
                    else "Current authoritative evidence does not yet permit target submission."
                ),
            )

    def submission_plan(self, *, case_id: UUID) -> GoldTierSubmissionPlan:
        return self._require_record(case_id).submission_plan.model_copy(deep=True)

    def confirm_target_dispatch(
        self,
        *,
        case_id: UUID,
        actor_id: str,
        expected_clm_version: int,
        expected_case_event_count: int,
        reauthorize: Callable[[], None] | None = None,
    ) -> ClmOrchestrationRecord:
        """Freeze the current submission review and retain local-POC confirmation."""

        with self._lock_for(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            if record.version != expected_clm_version:
                raise ClmRequestError(
                    code="CLM_TARGET_CONFIRMATION_STALE",
                    message="The CLM case changed before target confirmation.",
                )
            case = self._require_case(case_id)
            existing_confirmation = case.target_dispatch_confirmation
            if existing_confirmation is None and record.submission_snapshot is None:
                previous_search = record.target_search_checkpoint
                record = self._perform_early_search(record, case, force=True)
                current_search = record.target_search_checkpoint
                if not _materially_equivalent_search(previous_search, current_search):
                    # A fresh read changed the proposed target path.  Retain the new
                    # evidence and return it for review; no confirmation or target
                    # mutation is allowed from the superseded summary.
                    return record.model_copy(deep=True)
            if record.submission_snapshot is None:
                record = self._start_submission(record)
            snapshot = record.submission_snapshot
            if snapshot is None:
                raise ClmRequestError(
                    code="CLM_SNAPSHOT_NOT_AVAILABLE",
                    message="Submission evidence is incomplete.",
                )
            destination: Literal["GOLDTIER_MOCK", "GOLDTIER_XPI_SANDBOX"] = (
                "GOLDTIER_XPI_SANDBOX"
                if record.submission_plan.environment == GoldTierProviderMode.SANDBOX
                else "GOLDTIER_MOCK"
            )
            try:
                self._cases.confirm_target_dispatch(
                    case_id=case_id,
                    actor_id=actor_id,
                    expected_case_event_count=expected_case_event_count,
                    clm_version=record.version,
                    destination=destination,
                    warnings=tuple(item.value for item in record.readiness.warnings),
                )
            except ValueError as exc:
                raise ClmRequestError(
                    code="CLM_TARGET_CONFIRMATION_INVALID",
                    message=str(exc),
                ) from None
            return record.model_copy(deep=True)

    def submit(
        self,
        *,
        case_id: UUID,
        single_checkpoint: bool = False,
        reauthorize: Callable[[], None] | None = None,
    ) -> ClmOrchestrationRecord:
        """Advance durable target checkpoints; callers may stop after one mutation."""

        with self._lock_for(case_id):
            if reauthorize is not None:
                reauthorize()
            record = self._require_record(case_id)
            snapshot = record.submission_snapshot
            if snapshot is not None and self._cases.is_execution_outcome_uncertain(
                snapshot.submission_id
            ):
                raise ClmRequestError(
                    code="CLM_TARGET_OUTCOME_UNCERTAIN",
                    message=(
                        "A prior GoldTier target operation has no definitive retained "
                        "outcome and cannot be replayed automatically."
                    ),
                ) from None
            if record.submission_snapshot is not None and record.status in {
                ClmStatus.MOCK_GOLDTIER_SUBMITTED,
                ClmStatus.REVIEW_REQUIRED,
                ClmStatus.FAILED,
            }:
                return record

            if record.submission_snapshot is None:
                record = self.evaluate(case_id=case_id)
                if record.readiness.blockers:
                    raise ClmRequestError(
                        code="CLM_NOT_READY",
                        message="The case is not ready for GoldTier target submission.",
                    )
                raise ClmRequestError(
                    code="CLM_TARGET_CONFIRMATION_REQUIRED",
                    message="A current frozen-review confirmation is required.",
                )
            snapshot = record.submission_snapshot
            if snapshot is None:
                raise ClmRequestError(
                    code="CLM_SNAPSHOT_NOT_AVAILABLE",
                    message="Submission evidence is incomplete.",
                )

            if snapshot.target_input.provider_mode != self._cases.target_provider_mode:
                raise ClmRequestError(
                    code="CLM_TARGET_PROVIDER_CONTEXT_MISMATCH",
                    message="Target provider context changed; submission cannot continue safely.",
                )

            if (
                self._cases.get_execution_state(snapshot.submission_id)
                == GoldTierExecutionLedgerState.NOT_STARTED
            ) and (
                not self._submission_snapshot_is_current(record)
                or not self._cases.has_valid_target_dispatch_confirmation(
                    self._require_case(case_id), clm_version=record.version
                )
            ):
                raise ClmRequestError(
                    code="CLM_TARGET_CONFIRMATION_REQUIRED",
                    message="A current frozen-review confirmation is required.",
                )

            receipt = record.execution_receipt
            if receipt is None:
                receipt = self._cases.get_execution_receipt(snapshot.submission_id)
            if receipt is None:
                execution_state = self._cases.get_execution_state(snapshot.submission_id)
                if execution_state == GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED:
                    try:
                        receipt = self._cases.finalize_recorded_execution(snapshot.submission_id)
                    except Exception:
                        raise ClmInfrastructureError(
                            case_id=record.case_id,
                            orchestration_id=record.orchestration_id,
                            correlation_id=record.correlation_id,
                            code="CLM_FINALIZATION_RETRY_REQUIRED",
                            message=(
                                "GoldTier target execution was retained but "
                                "finalization must be retried."
                            ),
                        ) from None
                if (
                    receipt is None
                    and execution_state == GoldTierExecutionLedgerState.IN_PROGRESS
                    and self._cases.is_execution_outcome_uncertain(snapshot.submission_id)
                ):
                    raise ClmRequestError(
                        code="CLM_TARGET_OUTCOME_UNCERTAIN",
                        message=(
                            "A prior GoldTier target operation has no definitive retained "
                            "outcome and cannot be replayed automatically."
                        ),
                    ) from None
                if receipt is None:
                    checkpoint = record.target_search_checkpoint
                    if (
                        checkpoint is None
                        or checkpoint.status != GoldTierSearchCheckpointStatus.COMPLETED
                        or checkpoint.disposition
                        not in {
                            GoldTierSearchDisposition.NO_MATCH,
                            GoldTierSearchDisposition.EXACT_MATCH,
                        }
                    ):
                        raise ClmRequestError(
                            code="CLM_TARGET_SEARCH_NOT_RESOLVED",
                            message=(
                                "GoldTier customer identity is not resolved for target mutation."
                            ),
                        )
                    search_resolution = (
                        GoldTierSearchResolution.EXACT_MATCH
                        if checkpoint.disposition == GoldTierSearchDisposition.EXACT_MATCH
                        else GoldTierSearchResolution.NO_MATCH
                    )
                    try:
                        receipt = self._cases.advance_incremental_submission_input(
                            snapshot.target_input,
                            search_resolution=search_resolution,
                            selected_party_id=checkpoint.selected_party_id,
                        )
                    except TargetProviderContextMismatchError as exc:
                        raise ClmRequestError(
                            code="CLM_TARGET_PROVIDER_CONTEXT_MISMATCH",
                            message=exc.public_message,
                        ) from None
                    except Exception:
                        receipt = self._cases.get_execution_receipt(snapshot.submission_id)
                        if receipt is None:
                            execution_state = self._cases.get_execution_state(
                                snapshot.submission_id
                            )
                            if (
                                execution_state
                                == GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED
                            ):
                                raise ClmInfrastructureError(
                                    case_id=record.case_id,
                                    orchestration_id=record.orchestration_id,
                                    correlation_id=record.correlation_id,
                                    code="CLM_FINALIZATION_RETRY_REQUIRED",
                                    message=(
                                        "GoldTier target execution was retained but "
                                        "finalization must be retried."
                                    ),
                                ) from None
                            if execution_state == GoldTierExecutionLedgerState.IN_PROGRESS:
                                if self._cases.is_execution_outcome_uncertain(
                                    snapshot.submission_id
                                ):
                                    raise ClmRequestError(
                                        code="CLM_TARGET_OUTCOME_UNCERTAIN",
                                        message=(
                                            "A GoldTier target operation has no definitive "
                                            "retained outcome and cannot be replayed "
                                            "automatically."
                                        ),
                                    ) from None
                                raise
                            raise ClmInfrastructureError(
                                case_id=record.case_id,
                                orchestration_id=record.orchestration_id,
                                correlation_id=record.correlation_id,
                                code="CLM_SUBMISSION_UNEXPECTED_FAILURE",
                                message="GoldTier target submission could not be completed.",
                            ) from None

            if receipt is None:
                candidate = record.model_copy(deep=True)
                candidate.status = ClmStatus.SUBMITTING
                operation_names = self.attempted_target_operations(case_id=case_id)
                operation = operation_names[-1] if operation_names else "SEARCH"
                checkpointed = self._record_event(
                    record,
                    candidate,
                    event_type=ClmEventType.GOLDTIER_OPERATION_CHECKPOINTED,
                    outcome=EventOutcome.SUCCEEDED,
                    code=f"GOLDTIER_{operation}_CHECKPOINTED",
                    message=f"GoldTier {operation} reached a durable operation checkpoint.",
                )
                if single_checkpoint:
                    return checkpointed
                return self.submit(case_id=case_id, single_checkpoint=False)

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
                        "GoldTier target execution was retained but finalization must be retried."
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
                        else "GoldTier target submission could not be completed."
                    ),
                ) from None
            return completed

    def _submission_snapshot_is_current(self, record: ClmOrchestrationRecord) -> bool:
        snapshot = record.submission_snapshot
        if snapshot is None:
            return False
        case = self._require_case(record.case_id)
        try:
            current_input = self._cases.build_submission_input(
                case,
                provider_mode=snapshot.target_input.provider_mode,
            )
        except ValueError:
            return False
        if (
            current_input.canonical_entity != snapshot.target_input.canonical_entity
            or current_input.policy_catalogue_version
            != snapshot.target_input.policy_catalogue_version
            or current_input.target_policy != snapshot.target_input.target_policy
        ):
            return False
        reconciliation_cleared = (
            self._reconciliation.is_currently_cleared(case_id=record.case_id)
            if self._reconciliation is not None
            else False
        )
        documents = tuple(
            EvidenceReference(
                reference_id=item.document_id,
                version=len(item.events),
                status=(
                    item.state.value
                    if item.state == DocumentProcessingState.REVIEWED
                    else "RECONCILIATION_RESOLVED"
                ),
                updated_at=item.updated_at,
            )
            for item in self._documents.list_documents(case_id=record.case_id)
            if item.is_current_evidence
            and (item.state == DocumentProcessingState.REVIEWED or reconciliation_cleared)
        )
        ownership = self._ownership.get(case_id=record.case_id)
        return bool(
            documents == snapshot.document_references
            and ownership is not None
            and EvidenceReference(
                reference_id=ownership.analysis_id,
                version=ownership.version,
                status=ownership.state.value,
                updated_at=ownership.updated_at,
            )
            == snapshot.ownership_reference
        )

    def _start_submission(self, record: ClmOrchestrationRecord) -> ClmOrchestrationRecord:
        case = self._require_case(record.case_id)
        documents = [
            item
            for item in self._documents.list_documents(case_id=record.case_id)
            if item.is_current_evidence
        ]
        ownership = self._ownership.get(case_id=record.case_id)
        if (
            record.target_search_checkpoint is None
            or record.target_search_checkpoint.identity_fingerprint
            != _target_identity_fingerprint(case)
        ):
            record = self._perform_early_search(record, case)
        readiness = _readiness_with_search(
            _evaluate_readiness(
                case=case,
                documents=documents,
                ownership=ownership,
                document_confidence_threshold=float(
                    case.policy_snapshot.idp_review_confidence_threshold
                ),
                reconciliation_cleared=(
                    self._reconciliation.is_currently_cleared(case_id=record.case_id)
                    if self._reconciliation is not None
                    else False
                ),
                require_target_classification=(
                    record.submission_plan.environment == GoldTierProviderMode.SANDBOX
                ),
                now=self._clock(),
            ),
            record.target_search_checkpoint,
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
                message="Target submission was blocked by current authoritative evidence.",
            )
            raise ClmRequestError(
                code="CLM_NOT_READY",
                message="The case is not ready for GoldTier target submission.",
            ) from None

        snapshot, preparation = self._build_snapshot(
            case=case,
            documents=documents,
            ownership=ownership,
            submission_plan=record.submission_plan,
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
            message="Serialized GoldTier target base submission started.",
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
                message="The retained target execution does not match this submission.",
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
                message="Safe target execution receipt retained for finalization.",
            )
        except Exception:
            raise ClmInfrastructureError(
                case_id=record.case_id,
                orchestration_id=record.orchestration_id,
                correlation_id=record.correlation_id,
                code="CLM_FINALIZATION_RETRY_REQUIRED",
                message="GoldTier target execution was retained but finalization must be retried.",
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

    def _build_submission_plan(self, case: OnboardingCase) -> GoldTierSubmissionPlan:
        mode = self._cases.target_provider_mode
        preview = (
            self._cases.build_request_preview(case, provider_mode=mode)
            if case.entity is not None and not validate_entity(case.entity)
            else None
        )
        if mode == GoldTierProviderMode.SANDBOX:
            return GoldTierSubmissionPlan(
                environment=GoldTierProviderMode.SANDBOX,
                provider_classification=GoldTierProviderClassification.SANDBOX_PARTIAL,
                base_operations=(
                    "customers/search",
                    "customers/create if NO_MATCH",
                    "customers/createPolicy",
                    "customers/amendCustomer",
                    "customers/search by retained GoldTier ID",
                ),
                match_found_behavior="EXACT_MATCH_REUSE_ELSE_REVIEW_NO_WRITES",
                related_party_integration="BLOCKED_CHILD_ID_LIFECYCLE",
                real_ready_for_approval="NOT_AVAILABLE",
                request_preview=preview,
            )
        return GoldTierSubmissionPlan(request_preview=preview)

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
            submission_plan=self._build_submission_plan(case),
            error=case.error if status == ClmStatus.FAILED else None,
            created_at=now,
            updated_at=now,
        )
        initial_search = case.initial_target_search
        if initial_search is not None:
            disposition = GoldTierSearchDisposition(initial_search.disposition)
            checkpoint_status = (
                GoldTierSearchCheckpointStatus.COMPLETED
                if disposition
                in {
                    GoldTierSearchDisposition.NO_MATCH,
                    GoldTierSearchDisposition.EXACT_MATCH,
                }
                else GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
                if disposition == GoldTierSearchDisposition.REVIEW_REQUIRED
                else GoldTierSearchCheckpointStatus.FAILED
            )
            checkpoint = GoldTierSearchCheckpoint(
                request_id=initial_search.request_id,
                identity_fingerprint=_initial_or_canonical_identity_fingerprint(case),
                provider_mode=record.submission_plan.environment,
                provider_classification=record.submission_plan.provider_classification,
                status=checkpoint_status,
                disposition=disposition,
                provider_outcome=initial_search.provider_outcome,
                status_code=initial_search.status_code,
                candidate_count=initial_search.candidate_count,
                candidates=tuple(
                    RetainedGoldTierCandidate(party_id=party_id, legal_name=legal_name)
                    for party_id, legal_name in zip(
                        initial_search.candidate_party_ids,
                        initial_search.candidate_legal_names,
                        strict=True,
                    )
                ),
                selected_party_id=initial_search.selected_party_id,
                resolution_outcome=(
                    "EXACT_MATCH"
                    if disposition == GoldTierSearchDisposition.EXACT_MATCH
                    else None
                ),
                code={
                    GoldTierSearchDisposition.EXACT_MATCH: "GOLDTIER_FIRST_EXACT_MATCH",
                    GoldTierSearchDisposition.NO_MATCH: "GOLDTIER_FIRST_NO_MATCH",
                    GoldTierSearchDisposition.REVIEW_REQUIRED: (
                        "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
                    ),
                    GoldTierSearchDisposition.FAILED: initial_search.provider_outcome,
                }[disposition],
                message={
                    GoldTierSearchDisposition.EXACT_MATCH: (
                        "Initial GoldTier Search found one exact verified customer."
                    ),
                    GoldTierSearchDisposition.NO_MATCH: (
                        "Initial GoldTier Search found no customer."
                    ),
                    GoldTierSearchDisposition.REVIEW_REQUIRED: (
                        "Initial GoldTier candidates require exact identity review."
                    ),
                    GoldTierSearchDisposition.FAILED: (
                        "Initial GoldTier Search failed; customer existence remains unresolved."
                    ),
                }[disposition],
                searched_at=initial_search.searched_at,
            )
            record.target_search_checkpoint = checkpoint
            record.readiness = _readiness_with_search(record.readiness, checkpoint)
            record.status = _status_for_readiness(case, record.readiness)
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
            saved = self._repository.save(record, expected_version=None)
        except ClmRepositoryConflictError:
            raise ClmRequestError(
                code="CLM_CASE_ALREADY_EXISTS",
                message="A CLM orchestration record already exists for this case.",
            ) from None
        if (
            readiness.registry.status == ReadinessStageStatus.READY
            and saved.target_search_checkpoint is None
        ):
            return self._perform_early_search(saved, case)
        return saved

    def _perform_early_search(
        self,
        record: ClmOrchestrationRecord,
        case: OnboardingCase,
        *,
        force: bool = False,
    ) -> ClmOrchestrationRecord:
        """Persist intent, call read-only Search once, and retain only safe evidence."""

        identity_fingerprint = _target_identity_fingerprint(case)
        current = record.target_search_checkpoint
        if (
            not force
            and current is not None
            and current.identity_fingerprint == identity_fingerprint
            and current.status != GoldTierSearchCheckpointStatus.STALE
        ):
            return record
        request_id = self._uuid_factory()
        started = record.model_copy(deep=True)
        started = self._record_event(
            record,
            started,
            event_type=ClmEventType.GOLDTIER_SEARCH_STARTED,
            outcome=EventOutcome.SUCCEEDED,
            code="GOLDTIER_SEARCH_STARTED",
            message="Early read-only GoldTier customer Search started.",
        )
        searched_at = self._clock()
        try:
            evidence = self._cases.search_target_identity(
                case_id=case.case_id,
                request_id=request_id,
                provider_mode=record.submission_plan.environment,
                searched_at=searched_at,
            )
        except TargetProviderContextMismatchError:
            return self._record_search_failure(
                started,
                request_id=request_id,
                identity_fingerprint=identity_fingerprint,
                searched_at=searched_at,
                code="CLM_TARGET_PROVIDER_CONTEXT_MISMATCH",
                message="Configured GoldTier provider identity does not match this case.",
            )
        except InvalidTargetResponseError:
            return self._record_search_failure(
                started,
                request_id=request_id,
                identity_fingerprint=identity_fingerprint,
                searched_at=searched_at,
                code="GT_MALFORMED_TARGET_RESPONSE",
                message="GoldTier target returned an invalid response.",
            )
        except ConnectorError as exc:
            public = public_connector_error(exc)
            return self._record_search_failure(
                started,
                request_id=request_id,
                identity_fingerprint=identity_fingerprint,
                searched_at=searched_at,
                code=public.code,
                message=public.message,
            )
        except Exception:
            return self._record_search_failure(
                started,
                request_id=request_id,
                identity_fingerprint=identity_fingerprint,
                searched_at=searched_at,
                code="GT_SEARCH_UNEXPECTED_FAILURE",
                message="GoldTier party search could not be completed.",
            )

        result = evidence.result
        resolution = evidence.resolution
        selected_party_id = None
        if result.outcome == GoldTierSearchOutcome.NO_MATCH:
            status = GoldTierSearchCheckpointStatus.COMPLETED
            disposition = GoldTierSearchDisposition.NO_MATCH
            event_type = ClmEventType.GOLDTIER_SEARCH_COMPLETED
            event_outcome = EventOutcome.SUCCEEDED
            code = "GOLDTIER_SEARCH_NO_MATCH"
            message = "No GoldTier customer was found; new-customer onboarding may continue."
        elif (
            resolution is not None
            and resolution.outcome == EntityResolutionOutcome.EXACT_MATCH
            and resolution.selected_candidate_id is not None
        ):
            status = GoldTierSearchCheckpointStatus.COMPLETED
            disposition = GoldTierSearchDisposition.EXACT_MATCH
            selected_party_id = resolution.selected_candidate_id
            event_type = ClmEventType.GOLDTIER_SEARCH_COMPLETED
            event_outcome = EventOutcome.SUCCEEDED
            code = "GOLDTIER_SEARCH_EXACT_MATCH"
            message = "An exact GoldTier customer was retained; Shell creation will be skipped."
        elif result.outcome == GoldTierSearchOutcome.FAILURE:
            status = GoldTierSearchCheckpointStatus.FAILED
            disposition = GoldTierSearchDisposition.FAILED
            event_type = ClmEventType.GOLDTIER_SEARCH_FAILED
            event_outcome = EventOutcome.FAILED
            code = "GT_SEARCH_FAILED"
            message = "GoldTier party search returned a controlled failure."
        else:
            status = GoldTierSearchCheckpointStatus.REVIEW_REQUIRED
            disposition = GoldTierSearchDisposition.REVIEW_REQUIRED
            event_type = ClmEventType.GOLDTIER_SEARCH_REVIEW_REQUIRED
            event_outcome = EventOutcome.REVIEW_REQUIRED
            code = "GT_SEARCH_IDENTITY_REVIEW_REQUIRED"
            message = (
                "GoldTier candidates require human identity review; target writes are blocked."
            )

        checkpoint = GoldTierSearchCheckpoint(
            request_id=request_id,
            identity_fingerprint=identity_fingerprint,
            provider_mode=record.submission_plan.environment,
            provider_classification=record.submission_plan.provider_classification,
            status=status,
            disposition=disposition,
            provider_outcome=result.outcome.value,
            status_code=result.status_code,
            candidate_count=len(result.candidates),
            candidates=tuple(
                RetainedGoldTierCandidate(
                    party_id=item.party_id,
                    registration_number=item.registration_number,
                    country=item.country,
                    legal_name=item.legal_name,
                    legal_form=item.legal_form,
                    registered_address=item.registered_address,
                )
                for item in result.candidates
            ),
            selected_party_id=selected_party_id,
            resolution_outcome=(resolution.outcome.value if resolution is not None else None),
            code=code,
            message=message,
            searched_at=searched_at,
        )
        candidate = started.model_copy(deep=True)
        candidate.target_search_checkpoint = checkpoint
        candidate.readiness = _readiness_with_search(candidate.readiness, checkpoint)
        candidate.status = _status_for_readiness(case, candidate.readiness)
        if status == GoldTierSearchCheckpointStatus.FAILED:
            candidate.error = None
        return self._record_event(
            started,
            candidate,
            event_type=event_type,
            outcome=event_outcome,
            code=code,
            message=message,
        )

    def _record_search_failure(
        self,
        record: ClmOrchestrationRecord,
        *,
        request_id: UUID,
        identity_fingerprint: str,
        searched_at: datetime,
        code: str,
        message: str,
    ) -> ClmOrchestrationRecord:
        checkpoint = GoldTierSearchCheckpoint(
            request_id=request_id,
            identity_fingerprint=identity_fingerprint,
            provider_mode=record.submission_plan.environment,
            provider_classification=record.submission_plan.provider_classification,
            status=GoldTierSearchCheckpointStatus.FAILED,
            disposition=GoldTierSearchDisposition.FAILED,
            provider_outcome="FAILURE",
            status_code=503,
            candidate_count=0,
            code=code,
            message=message,
            searched_at=searched_at,
        )
        candidate = record.model_copy(deep=True)
        candidate.target_search_checkpoint = checkpoint
        candidate.readiness = _readiness_with_search(candidate.readiness, checkpoint)
        candidate.status = _status_for_readiness(
            self._require_case(record.case_id), candidate.readiness
        )
        candidate.error = None
        return self._record_event(
            record,
            candidate,
            event_type=ClmEventType.GOLDTIER_SEARCH_FAILED,
            outcome=EventOutcome.FAILED,
            code=code,
            message=message,
        )

    def _evaluate_current(
        self,
        case: OnboardingCase,
        *,
        search_checkpoint: GoldTierSearchCheckpoint | None = None,
        now: datetime | None = None,
    ) -> ClmReadinessAssessment:
        documents = [
            item
            for item in self._documents.list_documents(case_id=case.case_id)
            if item.is_current_evidence
        ]
        ownership = self._ownership.get(case_id=case.case_id)
        return _readiness_with_search(
            _evaluate_readiness(
                case=case,
                documents=documents,
                ownership=ownership,
                document_confidence_threshold=float(
                    case.policy_snapshot.idp_review_confidence_threshold
                ),
                reconciliation_cleared=(
                    self._reconciliation.is_currently_cleared(case_id=case.case_id)
                    if self._reconciliation is not None
                    else False
                ),
                require_target_classification=(
                    self._cases.target_provider_mode == GoldTierProviderMode.SANDBOX
                ),
                now=now or self._clock(),
            ),
            search_checkpoint,
        )

    def _build_snapshot(
        self,
        *,
        case: OnboardingCase,
        documents: list[DocumentProcessingRecord],
        ownership: OwnershipAnalysisRecord | None,
        submission_plan: GoldTierSubmissionPlan,
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
            accepted_at=case.created_at,
            provider_mode=submission_plan.environment,
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
    require_target_classification: bool = False,
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

    target_policy = case.policy_snapshot.goldtier_target
    if require_target_classification and (
        target_policy is None or not target_policy.dispatch_ready
    ):
        block(ClmBlockerCode.GOLDTIER_CLASSIFICATION_REQUIRED)
    goldtier = StageReadiness(
        status=(
            ReadinessStageStatus.READY
            if not blockers
            else ReadinessStageStatus.REVIEW_REQUIRED
            if ClmBlockerCode.GOLDTIER_CLASSIFICATION_REQUIRED in blockers
            else ReadinessStageStatus.BLOCKED
        )
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


def _readiness_with_search(
    readiness: ClmReadinessAssessment,
    checkpoint: GoldTierSearchCheckpoint | None,
) -> ClmReadinessAssessment:
    """Overlay target-identity readiness without changing document/ownership owners."""

    blockers = list(readiness.blockers)
    if checkpoint is None:
        blocker = ClmBlockerCode.GOLDTIER_SEARCH_REQUIRED
        status = ReadinessStageStatus.BLOCKED
    elif checkpoint.status == GoldTierSearchCheckpointStatus.REVIEW_REQUIRED:
        blocker = ClmBlockerCode.GOLDTIER_SEARCH_REVIEW_REQUIRED
        status = ReadinessStageStatus.REVIEW_REQUIRED
    elif checkpoint.status == GoldTierSearchCheckpointStatus.FAILED:
        blocker = ClmBlockerCode.GOLDTIER_SEARCH_FAILED
        status = ReadinessStageStatus.FAILED
    elif checkpoint.status == GoldTierSearchCheckpointStatus.STALE:
        blocker = ClmBlockerCode.GOLDTIER_SEARCH_STALE
        status = ReadinessStageStatus.BLOCKED
    else:
        blocker = None
        status = ReadinessStageStatus.READY if not blockers else ReadinessStageStatus.BLOCKED
    if blocker is not None and blocker not in blockers:
        blockers.append(blocker)
    return readiness.model_copy(
        update={
            "goldtier": StageReadiness(
                status=status,
                reference_id=(str(checkpoint.request_id) if checkpoint is not None else None),
            ),
            "blockers": blockers,
        },
        deep=True,
    )


def _target_identity_fingerprint(case: OnboardingCase) -> str:
    entity = case.entity
    if (
        entity is None
        or entity.registration_number is None
        or entity.legal_name is None
        or entity.country_of_incorporation is None
    ):
        raise ValueError("Canonical identity is unavailable")
    value = "|".join(
        (
            entity.registration_number.strip().upper(),
            " ".join(entity.legal_name.split()).casefold(),
            entity.country_of_incorporation.strip().upper(),
        )
    )
    return sha256(value.encode("utf-8")).hexdigest()


def _materially_equivalent_search(
    previous: GoldTierSearchCheckpoint | None,
    current: GoldTierSearchCheckpoint | None,
) -> bool:
    """Compare only evidence that can change the proposed target dispatch path."""

    if previous is None or current is None:
        return False
    common = (
        previous.identity_fingerprint == current.identity_fingerprint
        and previous.provider_mode == current.provider_mode
        and previous.provider_classification == current.provider_classification
        and previous.status == current.status
        and previous.disposition == current.disposition
        and previous.provider_outcome == current.provider_outcome
        and previous.status_code == current.status_code
        and previous.selected_party_id == current.selected_party_id
        and previous.resolution_outcome == current.resolution_outcome
    )
    if not common:
        return False
    if current.disposition == GoldTierSearchDisposition.REVIEW_REQUIRED:
        return previous.candidates == current.candidates
    return True


def _initial_or_canonical_identity_fingerprint(case: OnboardingCase) -> str:
    if case.entity is not None:
        return _target_identity_fingerprint(case)
    identity = case.initial_identity
    if identity is None:
        raise ValueError("Initial identity is unavailable")
    value = "|".join(
        (
            identity.registration_number.strip().upper(),
            " ".join(identity.legal_name.split()).casefold(),
            identity.country_of_incorporation.strip().upper(),
        )
    )
    return sha256(value.encode("utf-8")).hexdigest()


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
        ClmBlockerCode.GOLDTIER_SEARCH_REVIEW_REQUIRED,
        ClmBlockerCode.GOLDTIER_CLASSIFICATION_REQUIRED,
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
            "Accepted GoldTier target base operations completed.",
        )

    error = (
        SafeError(code=receipt.error.code, message=receipt.error.message)
        if receipt.error is not None
        else SafeError(
            code="CLM_SUBMISSION_FAILED",
            message="GoldTier target submission failed.",
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
            "GoldTier target returned an outcome requiring human review.",
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
