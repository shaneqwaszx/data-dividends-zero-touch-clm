"""Phase 05 integrated readiness, submission, and finality scenarios."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier, Lock
from typing import Literal
from uuid import UUID

import httpx
import pytest
from pydantic import ValidationError

import app.services.clm_orchestration as clm_orchestration_module
import app.services.onboarding as onboarding_module
from app.config import Settings
from app.connectors.goldtier_models import (
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_idp import MockIdpProvider
from app.connectors.mock_ownership import MockOwnershipProvider
from app.domain.clm import ClmEventType, ClmOrchestrationRecord, ClmStatus
from app.domain.documents import DocumentFieldKey, ReviewDecision
from app.domain.models import OnboardingCase
from app.domain.target_submission import (
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
)
from app.main import create_app
from app.services.clm_errors import ClmInfrastructureError, ClmRequestError
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import (
    ClmOrchestrationRepository,
    ClmRepositoryConflictError,
    InMemoryClmOrchestrationRepository,
)
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository

PDF = b"%PDF-1.4\nSYNTHETIC PHASE 05 EVIDENCE\n%%EOF\n"


class RecordingGoldTier:
    def __init__(
        self,
        *,
        policy_failure_keys: frozenset[str] = frozenset(),
        partial_amend_keys: frozenset[str] = frozenset(),
        match_found: bool = False,
        controlled_failure_stage: str | None = None,
        unexpected_stage: str | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.requests: dict[str, object] = {}
        self.metadata: dict[str, GoldTierRequestMetadata] = {}
        self._lock = Lock()
        self._match_found = match_found
        self._controlled_failure_stage = controlled_failure_stage
        self._unexpected_stage = unexpected_stage
        self._delegate = MockGoldTierConnector(
            policy_validation_failure_keys=policy_failure_keys,
            partial_amend_external_keys=partial_amend_keys,
        )

    def _record(
        self,
        call: str,
        request: object,
        metadata: GoldTierRequestMetadata,
    ) -> None:
        with self._lock:
            self.calls.append(call)
            self.requests[call] = request
            self.metadata[call] = metadata

    def _raise_if_unexpected(self, stage: str) -> None:
        if self._unexpected_stage == stage:
            raise RuntimeError("PRIVATE_GOLDTIER_FAILURE_SENTINEL")

    def search_party(
        self, request: SearchPartyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult:
        self._record("search", request, metadata)
        self._raise_if_unexpected("search")
        if self._controlled_failure_stage == "search":
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.FAILURE,
                status_code=503,
                error_code="GT_SEARCH_FAILED",
                message="Synthetic controlled search failure.",
            )
        if self._match_found:
            return GoldTierSearchResult(
                outcome=GoldTierSearchOutcome.MATCH_FOUND,
                status_code=200,
                matched_party_id="GT-EXISTING-SYNTHETIC",
                message="Synthetic existing party candidate.",
            )
        return self._delegate.search_party(request, metadata)

    def create_shell_customer(
        self, request: CreateShellCustomerRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        self._record("shell", request, metadata)
        self._raise_if_unexpected("shell")
        if self._controlled_failure_stage == "shell":
            return GoldTierOperationResult(
                outcome="VALIDATION_FAILED",
                status_code=422,
                status="SHELL_FAILED",
                error_code="GT_SHELL_FAILED",
                message="Synthetic controlled shell failure.",
            )
        return self._delegate.create_shell_customer(request, metadata)

    def create_policy(
        self, request: CreatePolicyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        self._record("policy", request, metadata)
        self._raise_if_unexpected("policy")
        return self._delegate.create_policy(request, metadata)

    def amend_party(
        self,
        party_id: str,
        request: AmendPartyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        self._record("amend", request, metadata)
        self._raise_if_unexpected("amend")
        return self._delegate.amend_party(party_id, request, metadata)


class UntrustedResponseGoldTier(RecordingGoldTier):
    """Return one deliberately bypass-constructed connector response."""

    def __init__(
        self,
        *,
        stage: Literal["search", "shell", "policy", "amend"],
        response: GoldTierSearchResult | GoldTierOperationResult,
    ) -> None:
        super().__init__()
        self._untrusted_stage = stage
        self._untrusted_response = response

    def search_party(
        self, request: SearchPartyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult:
        if self._untrusted_stage == "search":
            self._record("search", request, metadata)
            assert isinstance(self._untrusted_response, GoldTierSearchResult)
            return self._untrusted_response
        return super().search_party(request, metadata)

    def create_shell_customer(
        self, request: CreateShellCustomerRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        if self._untrusted_stage == "shell":
            self._record("shell", request, metadata)
            assert isinstance(self._untrusted_response, GoldTierOperationResult)
            return self._untrusted_response
        return super().create_shell_customer(request, metadata)

    def create_policy(
        self, request: CreatePolicyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        if self._untrusted_stage == "policy":
            self._record("policy", request, metadata)
            assert isinstance(self._untrusted_response, GoldTierOperationResult)
            return self._untrusted_response
        return super().create_policy(request, metadata)

    def amend_party(
        self,
        party_id: str,
        request: AmendPartyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        if self._untrusted_stage == "amend":
            self._record("amend", request, metadata)
            assert isinstance(self._untrusted_response, GoldTierOperationResult)
            return self._untrusted_response
        return super().amend_party(party_id, request, metadata)


class FailOnceClmRepository:
    def __init__(
        self,
        *,
        fail_point: Literal["receipt", "terminal"],
        conflict: bool = False,
    ) -> None:
        self._delegate = InMemoryClmOrchestrationRepository()
        self._fail_point = fail_point
        self._conflict = conflict
        self.failed = False

    def save(
        self,
        record: ClmOrchestrationRecord,
        *,
        expected_version: int | None,
    ) -> ClmOrchestrationRecord:
        is_receipt = (
            record.status == ClmStatus.SUBMITTING
            and record.execution_receipt is not None
        )
        is_terminal = (
            record.submission_snapshot is not None
            and record.status
            in {
                ClmStatus.MOCK_GOLDTIER_SUBMITTED,
                ClmStatus.REVIEW_REQUIRED,
                ClmStatus.FAILED,
            }
        )
        should_fail = (
            self._fail_point == "receipt" and is_receipt
        ) or (
            self._fail_point == "terminal" and is_terminal
        )
        if should_fail and not self.failed:
            self.failed = True
            if self._conflict:
                raise ClmRepositoryConflictError
            raise RuntimeError("PRIVATE_TERMINAL_REPOSITORY_SENTINEL")
        return self._delegate.save(record, expected_version=expected_version)

    def get_for_case(self, case_id: UUID) -> ClmOrchestrationRecord | None:
        return self._delegate.get_for_case(case_id)


class FailOnceCompletionClock:
    def __init__(self, repository: ClmOrchestrationRepository) -> None:
        self._repository = repository
        self.case_id: UUID | None = None
        self.failed = False

    def __call__(self) -> datetime:
        record = (
            self._repository.get_for_case(self.case_id)
            if self.case_id is not None
            else None
        )
        if (
            record is not None
            and record.execution_receipt is not None
            and record.status == ClmStatus.SUBMITTING
            and not self.failed
        ):
            self.failed = True
            raise RuntimeError("PRIVATE_COMPLETION_CLOCK_SENTINEL")
        return datetime.now(UTC)


def mutate_current_case(
    cases: OnboardingService,
    case_id: UUID,
    mutation: Callable[[OnboardingCase], None],
) -> None:
    repository = cases._repository  # type: ignore[attr-defined]
    case = repository.get(case_id)
    assert case is not None
    mutation(case)
    repository.save(case)


def invalidate_canonical_field(case: OnboardingCase, field: str) -> None:
    assert case.entity is not None
    entity = case.entity
    if field == "registration_number":
        entity.registration_number = "INVALID"
    elif field == "legal_name":
        entity.legal_name = " "
    elif field == "country_of_incorporation":
        entity.country_of_incorporation = " "
    elif field == "party_type":
        entity.party_type = " "
    elif field == "registered_address":
        entity.registered_address = None
    else:
        assert entity.registered_address is not None
        setattr(entity.registered_address, field, " ")


def build_services(
    goldtier: RecordingGoldTier | None = None,
    *,
    clm_repository: ClmOrchestrationRepository | None = None,
    clm_clock: Callable[[], datetime] | None = None,
) -> tuple[
    OnboardingService,
    DocumentProcessingService,
    OwnershipAnalysisService,
    ClmOrchestrationService,
    RecordingGoldTier,
]:
    target = goldtier or RecordingGoldTier()
    cases = OnboardingService(
        acra=MockAcraConnector(),
        goldtier=target,
        repository=InMemoryOnboardingCaseRepository(),
    )
    documents = DocumentProcessingService(
        cases=cases,
        idp=MockIdpProvider(),
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=5 * 1024 * 1024,
        review_confidence_threshold=0.85,
    )
    ownership = OwnershipAnalysisService(
        cases=cases,
        provider=MockOwnershipProvider(),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
    )
    clm = ClmOrchestrationService(
        cases=cases,
        documents=documents,
        ownership=ownership,
        repository=clm_repository or InMemoryClmOrchestrationRepository(),
        clock=clm_clock,
    )
    return cases, documents, ownership, clm, target


def make_ready_case(
    *,
    uen: str = "202400001A",
    goldtier: RecordingGoldTier | None = None,
    clm_repository: ClmOrchestrationRepository | None = None,
    clm_clock: Callable[[], datetime] | None = None,
) -> tuple[
    OnboardingService,
    DocumentProcessingService,
    OwnershipAnalysisService,
    ClmOrchestrationService,
    RecordingGoldTier,
    object,
]:
    cases, documents, ownership, clm, target = build_services(
        goldtier,
        clm_repository=clm_repository,
        clm_clock=clm_clock,
    )
    record = clm.create_case(uen)
    document = documents.create_document(
        case_id=record.case_id,
        display_name="synthetic-phase-05.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    for field_key in DocumentFieldKey:
        field = next(item for item in document.fields if item.field_key == field_key)
        decision = (
            ReviewDecision.ACCEPTED
            if field.comparison_status == "MATCH"
            else ReviewDecision.CORRECTED
        )
        document = documents.review_field(
            case_id=record.case_id,
            document_id=document.document_id,
            field_key=field_key,
            decision=decision,
            corrected_value=(
                field.canonical_value if decision == ReviewDecision.CORRECTED else None
            ),
        )
    ownership.load(case_id=record.case_id)
    ownership.analyze(case_id=record.case_id)
    evaluated = clm.evaluate(case_id=record.case_id)
    assert evaluated.status == ClmStatus.READY_FOR_MOCK_SUBMISSION
    return cases, documents, ownership, clm, target, record.case_id


def recovery_case_configuration(
    outcome: Literal["success", "match", "policy", "partial"],
) -> tuple[str, RecordingGoldTier, ClmStatus, list[str], str | None]:
    if outcome == "match":
        return (
            "202400001A",
            RecordingGoldTier(match_found=True),
            ClmStatus.REVIEW_REQUIRED,
            ["search"],
            "GT_EXISTING_PARTY_REVIEW_REQUIRED",
        )
    if outcome == "policy":
        return (
            "202400003C",
            RecordingGoldTier(
                policy_failure_keys=frozenset({"202400003C"})
            ),
            ClmStatus.FAILED,
            ["search", "shell", "policy"],
            "GT_POLICY_VALIDATION_FAILED",
        )
    if outcome == "partial":
        return (
            "202400004D",
            RecordingGoldTier(
                partial_amend_keys=frozenset({"202400004D"})
            ),
            ClmStatus.REVIEW_REQUIRED,
            ["search", "shell", "policy", "amend"],
            "GT_OPTIONAL_SECTION_REVIEW",
        )
    return (
        "202400001A",
        RecordingGoldTier(),
        ClmStatus.MOCK_GOLDTIER_SUBMITTED,
        ["search", "shell", "policy", "amend"],
        None,
    )


def test_staged_intake_stops_before_goldtier_and_preserves_legacy_composition() -> None:
    cases, _, _, clm, target = build_services()
    staged = clm.create_case("202400001A")
    assert staged.status == ClmStatus.COLLECTING_EVIDENCE
    assert staged.readiness.registry.status == "READY"
    assert target.calls == []
    assert cases.get_case(staged.case_id).state == "VALIDATED"  # type: ignore[union-attr]

    legacy = cases.create_case("202400001A")
    assert legacy.state == "COMPLETED"
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_happy_end_to_end_snapshot_plan_and_mock_submission() -> None:
    cases, _, _, clm, target, case_id = make_ready_case()
    submitted = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert submitted.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED
    assert submitted.readiness.goldtier.status == "SUBMITTED"
    assert submitted.submission_snapshot is not None
    assert len(submitted.submission_snapshot.document_references) == 1
    assert submitted.submission_snapshot.canonical_entity.registration_number == "202400001A"
    with pytest.raises(TypeError):
        submitted.submission_snapshot.document_references[0] = (  # type: ignore[index]
            submitted.submission_snapshot.document_references[0]
        )
    with pytest.raises(ValidationError):
        submitted.submission_snapshot.canonical_entity.registered_address.postal_code = (  # type: ignore[misc]
            "000000"
        )
    assert submitted.related_party_preparation is not None
    assert submitted.related_party_preparation.mapping_status == "PENDING_SPONSOR_CONFIRMATION"
    assert submitted.related_party_preparation.write_status == "RELATED_PARTY_WRITE_NOT_EXECUTED"
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert cases.get_case(case_id).state == "GT_ENRICHED"  # type: ignore[arg-type,union-attr]


def test_document_and_multiple_blockers_prevent_all_goldtier_calls() -> None:
    _, documents, ownership, clm, target = build_services()
    record = clm.create_case("202400001A")
    documents.create_document(
        case_id=record.case_id,
        display_name="pending-review.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    ownership.load(case_id=record.case_id)
    evaluated = clm.evaluate(case_id=record.case_id)
    assert set(evaluated.readiness.blockers) == {
        "DOCUMENT_REVIEW_INCOMPLETE",
        "OWNERSHIP_ANALYSIS_INCOMPLETE",
    }
    with pytest.raises(ClmRequestError, match="CLM_NOT_READY"):
        clm.submit(case_id=record.case_id)
    assert target.calls == []


def test_reviewed_mismatch_is_source_conflict_and_never_overwrites_registry() -> None:
    _, documents, ownership, clm, target = build_services()
    record = clm.create_case("202400001A")
    mismatch_provider = MockIdpProvider(scenario="FIELD_MISMATCH")
    document = documents.create_document(
        case_id=record.case_id,
        display_name="source-conflict.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=mismatch_provider,
    )
    for field_key in DocumentFieldKey:
        document = documents.review_field(
            case_id=record.case_id,
            document_id=document.document_id,
            field_key=field_key,
            decision=ReviewDecision.ACCEPTED,
        )
    ownership.load(case_id=record.case_id)
    ownership.analyze(case_id=record.case_id)
    evaluated = clm.evaluate(case_id=record.case_id)
    assert "SOURCE_CONFLICT_REQUIRES_POLICY" in evaluated.readiness.blockers
    assert target.calls == []


def test_stale_ready_result_is_revalidated_before_submission() -> None:
    _, documents, _, clm, target, case_id = make_ready_case()
    documents.create_document(
        case_id=case_id,  # type: ignore[arg-type]
        display_name="new-unresolved-evidence.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    with pytest.raises(ClmRequestError, match="CLM_NOT_READY"):
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    current = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert current is not None
    assert "DOCUMENT_REVIEW_INCOMPLETE" in current.readiness.blockers
    assert target.calls == []


@pytest.mark.parametrize(
    "field",
    [
        "registration_number",
        "legal_name",
        "country_of_incorporation",
        "party_type",
        "registered_address",
        "address_line_1",
        "postal_code",
        "country_code",
    ],
)
def test_current_canonical_invalid_blocks_readiness_and_submission(field: str) -> None:
    cases, _, _, clm, target, case_id = make_ready_case()
    mutate_current_case(
        cases,
        case_id,  # type: ignore[arg-type]
        lambda case: invalidate_canonical_field(case, field),
    )

    evaluated = clm.evaluate(case_id=case_id)  # type: ignore[arg-type]
    assert evaluated.readiness.registry.status == "BLOCKED"
    assert "CANONICAL_DATA_INVALID" in evaluated.readiness.blockers
    assert evaluated.status != ClmStatus.READY_FOR_MOCK_SUBMISSION
    with pytest.raises(ClmRequestError, match="CLM_NOT_READY"):
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert target.calls == []


def test_reviewed_document_is_compared_with_current_canonical_entity() -> None:
    cases, _, _, clm, target, case_id = make_ready_case()

    def change_current_name(case: OnboardingCase) -> None:
        assert case.entity is not None
        case.entity.legal_name = "CURRENT CANONICAL NAME PTE. LTD."

    mutate_current_case(cases, case_id, change_current_name)  # type: ignore[arg-type]
    evaluated = clm.evaluate(case_id=case_id)  # type: ignore[arg-type]

    assert evaluated.readiness.registry.status == "READY"
    assert "SOURCE_CONFLICT_REQUIRES_POLICY" in evaluated.readiness.blockers
    with pytest.raises(ClmRequestError, match="CLM_NOT_READY"):
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert target.calls == []


def test_final_submit_revalidates_current_canonical_without_new_evaluation() -> None:
    cases, _, _, clm, target, case_id = make_ready_case()
    mutate_current_case(
        cases,
        case_id,  # type: ignore[arg-type]
        lambda case: invalidate_canonical_field(case, "legal_name"),
    )

    with pytest.raises(ClmRequestError, match="CLM_NOT_READY"):
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    current = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert current is not None
    assert current.readiness.registry.status == "BLOCKED"
    assert "CANONICAL_DATA_INVALID" in current.readiness.blockers
    assert target.calls == []


def test_snapshot_is_exact_target_mapper_source_after_live_entity_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, _, _, clm, target, case_id = make_ready_case()
    execute = cases.execute_submission_input

    def mutate_then_execute(*args: object, **kwargs: object):
        submission_input = args[0]

        def mutate(case: OnboardingCase) -> None:
            assert case.entity is not None
            assert case.entity.registered_address is not None
            case.entity.registration_number = "202499999Z"
            case.entity.legal_name = "MUTATED AFTER SNAPSHOT PTE. LTD."
            case.entity.country_of_incorporation = "MY"
            case.entity.registered_address.address_line_1 = "99 MUTATED ROAD"
            case.entity.registered_address.postal_code = "999999"
            case.entity.registered_address.country_code = "MY"

        mutate_current_case(cases, case_id, mutate)  # type: ignore[arg-type]
        return execute(submission_input, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cases, "execute_submission_input", mutate_then_execute)
    submitted = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    snapshot = submitted.submission_snapshot
    assert snapshot is not None
    assert snapshot.canonical_entity.registration_number == "202400001A"
    assert snapshot.canonical_entity.legal_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert snapshot.canonical_entity.country_of_incorporation == "SG"
    assert snapshot.canonical_entity.registered_address.address_line_1 == "18 INNOVATION WAY"

    search = target.requests["search"]
    shell = target.requests["shell"]
    policy = target.requests["policy"]
    amend = target.requests["amend"]
    assert isinstance(search, SearchPartyRequest)
    assert isinstance(shell, CreateShellCustomerRequest)
    assert isinstance(policy, CreatePolicyRequest)
    assert isinstance(amend, AmendPartyRequest)
    assert search.registration_number == snapshot.canonical_entity.registration_number
    assert shell.party.names.legal_name == snapshot.canonical_entity.legal_name
    assert (
        shell.party.non_individual_profile.country_of_incorporation
        == snapshot.canonical_entity.country_of_incorporation
    )
    assert (
        policy.customer_external_system_key
        == snapshot.canonical_entity.registration_number
    )
    assert amend.party.names.legal_name == snapshot.canonical_entity.legal_name
    assert (
        amend.party.addresses[0].address_line_1
        == snapshot.canonical_entity.registered_address.address_line_1
    )
    assert (
        amend.party.addresses[0].postal_code
        == snapshot.canonical_entity.registered_address.postal_code
    )
    assert (
        amend.party.addresses[0].country
        == snapshot.canonical_entity.registered_address.country_code
    )
    assert target.metadata["shell"].correlation_id == snapshot.correlation_id
    assert (
        target.metadata["shell"].idempotency_key
        == snapshot.target_input.idempotency.shell
    )


@pytest.mark.parametrize(
    ("uen", "expected_status", "expected_calls", "expected_code"),
    [
        (
            "202400003C",
            "FAILED",
            ["search", "shell", "policy"],
            "GT_POLICY_VALIDATION_FAILED",
        ),
        (
            "202400004D",
            "REVIEW_REQUIRED",
            ["search", "shell", "policy", "amend"],
            "GT_OPTIONAL_SECTION_REVIEW",
        ),
    ],
)
def test_goldtier_failure_and_partial_amend_terminalize_truthfully(
    uen: str, expected_status: str, expected_calls: list[str], expected_code: str
) -> None:
    target = RecordingGoldTier(
        policy_failure_keys=frozenset({"202400003C"}),
        partial_amend_keys=frozenset({"202400004D"}),
    )
    _, _, _, clm, _, case_id = make_ready_case(uen=uen, goldtier=target)
    submitted = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert submitted.status == expected_status
    assert submitted.error is not None and submitted.error.code == expected_code
    assert target.calls == expected_calls


def test_match_found_routes_to_review_and_executes_search_only() -> None:
    target = RecordingGoldTier(match_found=True)
    _, _, _, clm, _, case_id = make_ready_case(goldtier=target)
    submitted = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert submitted.status == ClmStatus.REVIEW_REQUIRED
    assert submitted.error is not None
    assert submitted.error.code == "GT_EXISTING_PARTY_REVIEW_REQUIRED"
    assert target.calls == ["search"]


@pytest.mark.parametrize(
    ("stage", "calls", "code"),
    [
        ("search", ["search"], "GT_SEARCH_FAILED"),
        ("shell", ["search", "shell"], "GT_SHELL_FAILED"),
    ],
)
def test_controlled_required_stage_failures_stop_later_operations(
    stage: str, calls: list[str], code: str
) -> None:
    target = RecordingGoldTier(controlled_failure_stage=stage)
    _, _, _, clm, _, case_id = make_ready_case(goldtier=target)
    submitted = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert submitted.status == ClmStatus.FAILED
    assert submitted.error is not None and submitted.error.code == code
    assert target.calls == calls


def test_unexpected_submission_failure_is_safe_terminal_and_retrievable() -> None:
    target = RecordingGoldTier(unexpected_stage="policy")
    cases, _, _, clm, _, case_id = make_ready_case(goldtier=target)
    with pytest.raises(ClmInfrastructureError) as failure:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    current = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert failure.value.code == "GT_POLICY_UNEXPECTED_FAILURE"
    assert "PRIVATE_GOLDTIER_FAILURE_SENTINEL" not in failure.value.public_message
    assert current is not None and current.status == ClmStatus.FAILED
    assert current.error is not None and current.error.code == "GT_POLICY_UNEXPECTED_FAILURE"
    assert target.calls == ["search", "shell", "policy"]
    assert current.submission_snapshot is not None
    outcome = cases.get_target_outcome(current.submission_snapshot.submission_id)
    assert outcome is not None and outcome.infrastructure_failure
    assert outcome.error_code == "GT_POLICY_UNEXPECTED_FAILURE"
    assert "PRIVATE_GOLDTIER_FAILURE_SENTINEL" not in outcome.model_dump_json()


@pytest.mark.parametrize(
    ("stage", "response", "expected_calls", "expected_operations", "sentinel"),
    [
        pytest.param(
            "shell",
            GoldTierOperationResult.model_construct(
                outcome=GoldTierOutcome.SUCCESS,
                status_code=201,
                party_id="PRIVATE_SHELL_PARTY_ID_SENTINEL" + "X" * 70,
                status="SHELL_CREATED",
                message="Synthetic shell result.",
            ),
            ["search", "shell"],
            (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL),
            "PRIVATE_SHELL_PARTY_ID_SENTINEL",
            id="SHELL_OVERSIZED_PARTY_ID",
        ),
        pytest.param(
            "shell",
            GoldTierOperationResult.model_construct(
                outcome=GoldTierOutcome.SUCCESS,
                status_code=201,
                party_id="GT-PRIVATE_SHELL_CONTROL_SENTINEL\r\n",
                status="SHELL_CREATED",
                message="Synthetic shell result.",
            ),
            ["search", "shell"],
            (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL),
            "PRIVATE_SHELL_CONTROL_SENTINEL",
            id="SHELL_CONTROL_PARTY_ID",
        ),
        pytest.param(
            "policy",
            GoldTierOperationResult.model_construct(
                outcome=GoldTierOutcome.SUCCESS,
                status_code=201,
                policy_id="PRIVATE_POLICY_ID_SENTINEL" + "X" * 80,
                status="POLICY_CREATED",
                message="Synthetic policy result.",
            ),
            ["search", "shell", "policy"],
            (
                GoldTierOperationMarker.SEARCH,
                GoldTierOperationMarker.SHELL,
                GoldTierOperationMarker.POLICY,
            ),
            "PRIVATE_POLICY_ID_SENTINEL",
            id="POLICY_OVERSIZED_POLICY_ID",
        ),
        pytest.param(
            "search",
            GoldTierSearchResult.model_construct(
                outcome=GoldTierSearchOutcome.NO_MATCH,
                status_code=199,
                message="PRIVATE_SEARCH_STATUS_SENTINEL",
            ),
            ["search"],
            (GoldTierOperationMarker.SEARCH,),
            "PRIVATE_SEARCH_STATUS_SENTINEL",
            id="SEARCH_INVALID_STATUS",
        ),
        pytest.param(
            "amend",
            GoldTierOperationResult.model_construct(
                outcome=GoldTierOutcome.SUCCESS,
                status_code=200,
                status="PRIVATE_AMEND_STATUS_SENTINEL",
                message="Synthetic amend result.",
            ),
            ["search", "shell", "policy", "amend"],
            (
                GoldTierOperationMarker.SEARCH,
                GoldTierOperationMarker.SHELL,
                GoldTierOperationMarker.POLICY,
                GoldTierOperationMarker.AMEND,
            ),
            "PRIVATE_AMEND_STATUS_SENTINEL",
            id="AMEND_INVALID_STATUS_OR_RESULT",
        ),
        pytest.param(
            "shell",
            GoldTierOperationResult.model_construct(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=422,
                status="SHELL_FAILED",
                error_code="PRIVATE_ERROR_CODE_SENTINEL\r\n",
                message="Synthetic shell failure.",
            ),
            ["search", "shell"],
            (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL),
            "PRIVATE_ERROR_CODE_SENTINEL",
            id="MALFORMED_TARGET_ERROR_CODE",
        ),
        pytest.param(
            "shell",
            GoldTierOperationResult.model_construct(
                outcome=GoldTierOutcome.VALIDATION_FAILED,
                status_code=422,
                status="SHELL_FAILED",
                error_code="GT_SHELL_FAILED",
                message="PRIVATE_ERROR_MESSAGE_SENTINEL\r\n",
            ),
            ["search", "shell"],
            (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL),
            "PRIVATE_ERROR_MESSAGE_SENTINEL",
            id="MALFORMED_TARGET_ERROR_MESSAGE",
        ),
    ],
)
def test_malformed_target_response_records_safe_outcome_and_never_replays(
    stage: Literal["search", "shell", "policy", "amend"],
    response: GoldTierSearchResult | GoldTierOperationResult,
    expected_calls: list[str],
    expected_operations: tuple[GoldTierOperationMarker, ...],
    sentinel: str,
) -> None:
    target = UntrustedResponseGoldTier(stage=stage, response=response)
    cases, _, _, clm, _, case_id = make_ready_case(goldtier=target)

    with pytest.raises(ClmInfrastructureError) as failure:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    current = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert failure.value.code == "GT_MALFORMED_TARGET_RESPONSE"
    assert current is not None and current.status == ClmStatus.FAILED
    assert current.error is not None
    assert current.error.code == "GT_MALFORMED_TARGET_RESPONSE"
    assert current.submission_snapshot is not None
    submission_id = current.submission_snapshot.submission_id
    outcome = cases.get_target_outcome(submission_id)
    receipt = cases.get_execution_receipt(submission_id)
    onboarding_case = cases.get_case(case_id)  # type: ignore[arg-type]
    assert outcome is not None and outcome.completed_operations == expected_operations
    assert outcome.error_code == "GT_MALFORMED_TARGET_RESPONSE"
    assert outcome.infrastructure_failure
    assert receipt is not None and receipt.submission_id == submission_id
    assert cases.get_execution_state(submission_id) == GoldTierExecutionLedgerState.FINALIZED
    assert target.calls == expected_calls

    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == ClmStatus.FAILED
    assert recovered.submission_snapshot is not None
    assert recovered.submission_snapshot.submission_id == submission_id
    assert target.calls == expected_calls
    combined = " ".join(
        (
            failure.value.public_message,
            current.model_dump_json(),
            outcome.model_dump_json(),
            receipt.model_dump_json(),
            onboarding_case.model_dump_json() if onboarding_case is not None else "",
            recovered.model_dump_json(),
        )
    )
    assert sentinel not in combined
    event_types = [event.event_type for event in recovered.events]
    assert event_types.count("MOCK_SUBMISSION_STARTED") == 1
    assert event_types.count("CLM_SUBMISSION_FAILED") == 1


@pytest.mark.parametrize(
    ("party_id", "accepted"),
    [
        pytest.param("A" * 96, True, id="party-id-length-96"),
        pytest.param("A" * 97, False, id="party-id-length-97"),
        pytest.param("", False, id="party-id-blank"),
        pytest.param("   ", False, id="party-id-whitespace"),
        pytest.param("GT-PARTY\nPRIVATE_CONTROL", False, id="party-id-control"),
        pytest.param("https://private.example/party", False, id="party-id-url"),
        pytest.param("GT PARTY", False, id="party-id-invalid-grammar"),
    ],
)
def test_shell_party_identifier_boundary_stops_before_policy(
    party_id: str, accepted: bool
) -> None:
    response = GoldTierOperationResult.model_construct(
        outcome=GoldTierOutcome.SUCCESS,
        status_code=201,
        party_id=party_id,
        status="SHELL_CREATED",
        message="Synthetic shell result.",
    )
    target = UntrustedResponseGoldTier(stage="shell", response=response)
    cases, _, _, clm, _, case_id = make_ready_case(goldtier=target)

    if accepted:
        submitted = clm.submit(case_id=case_id)  # type: ignore[arg-type]
        assert submitted.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED
        assert target.calls == ["search", "shell", "policy", "amend"]
    else:
        with pytest.raises(ClmInfrastructureError) as failure:
            clm.submit(case_id=case_id)  # type: ignore[arg-type]
        assert failure.value.code == "GT_MALFORMED_TARGET_RESPONSE"
        assert target.calls == ["search", "shell"]
        current = clm.get(case_id=case_id)  # type: ignore[arg-type]
        assert current is not None and current.submission_snapshot is not None
        outcome = cases.get_target_outcome(current.submission_snapshot.submission_id)
        assert outcome is not None and outcome.party_id is None


def test_normal_outcome_construction_failure_uses_constant_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, _, _, clm, target, case_id = make_ready_case()

    def fail_outcome_construction(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("PRIVATE_NORMAL_OUTCOME_CONSTRUCTION_SENTINEL")

    monkeypatch.setattr(cases, "_build_target_outcome", fail_outcome_construction)
    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    current = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert current is not None and current.submission_snapshot is not None
    submission_id = current.submission_snapshot.submission_id
    outcome = cases.get_target_outcome(submission_id)
    assert outcome is not None
    assert outcome.error_code == "GT_TARGET_OUTCOME_RECORDING_FAILED"
    assert cases.get_execution_state(submission_id) == (
        GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED
    )
    assert target.calls == ["search", "shell", "policy", "amend"]

    with pytest.raises(ClmInfrastructureError) as recovery_signal:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovery_signal.value.code == "GT_TARGET_OUTCOME_RECORDING_FAILED"
    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == ClmStatus.FAILED
    assert recovered.error is not None
    assert recovered.error.code == "GT_TARGET_OUTCOME_RECORDING_FAILED"
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert cases.get_execution_state(submission_id) == GoldTierExecutionLedgerState.FINALIZED
    combined = first.value.public_message + outcome.model_dump_json() + recovered.model_dump_json()
    assert "PRIVATE_NORMAL_OUTCOME_CONSTRUCTION_SENTINEL" not in combined


def test_unexpected_response_validator_failure_cannot_leave_in_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, _, _, clm, target, case_id = make_ready_case()

    def fail_validation(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("PRIVATE_RESPONSE_VALIDATOR_SENTINEL")

    monkeypatch.setattr(onboarding_module, "validate_shell_response", fail_validation)
    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    current = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert current is not None and current.submission_snapshot is not None
    submission_id = current.submission_snapshot.submission_id
    outcome = cases.get_target_outcome(submission_id)
    assert outcome is not None
    assert outcome.error_code == "GT_TARGET_OUTCOME_RECORDING_FAILED"
    assert outcome.completed_operations == (
        GoldTierOperationMarker.SEARCH,
        GoldTierOperationMarker.SHELL,
    )
    assert cases.get_execution_state(submission_id) == (
        GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED
    )
    assert target.calls == ["search", "shell"]

    with pytest.raises(ClmInfrastructureError) as recovery_signal:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovery_signal.value.code == "GT_TARGET_OUTCOME_RECORDING_FAILED"
    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == ClmStatus.FAILED
    assert target.calls == ["search", "shell"]
    combined = first.value.public_message + outcome.model_dump_json() + recovered.model_dump_json()
    assert "PRIVATE_RESPONSE_VALIDATOR_SENTINEL" not in combined


def test_duplicate_and_concurrent_submissions_execute_business_operations_once() -> None:
    _, _, _, clm, target, case_id = make_ready_case()
    start = Barrier(3)

    def submit() -> ClmStatus:
        start.wait()
        return clm.submit(case_id=case_id).status  # type: ignore[arg-type]

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(submit)
        second = executor.submit(submit)
        start.wait()
        results = {first.result(timeout=5), second.result(timeout=5)}

    duplicate = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert results == {ClmStatus.MOCK_GOLDTIER_SUBMITTED}
    assert duplicate.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert [event.event_type for event in duplicate.events].count("MOCK_SUBMISSION_STARTED") == 1


@pytest.mark.parametrize("outcome", ["success", "match", "policy", "partial"])
def test_receipt_construction_failure_recovers_from_pre_receipt_target_outcome(
    monkeypatch: pytest.MonkeyPatch,
    outcome: Literal["success", "match", "policy", "partial"],
) -> None:
    uen, target, expected_status, expected_calls, expected_code = (
        recovery_case_configuration(outcome)
    )
    cases, _, _, clm, _, case_id = make_ready_case(uen=uen, goldtier=target)
    build_receipt = cases._build_execution_receipt  # type: ignore[attr-defined]
    failures_remaining = 2 if outcome == "success" else 1

    def fail_once(*args: object, **kwargs: object):
        nonlocal failures_remaining
        if failures_remaining:
            failures_remaining -= 1
            raise RuntimeError("PRIVATE_RECEIPT_CONSTRUCTION_SENTINEL")
        return build_receipt(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cases, "_build_execution_receipt", fail_once)
    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]

    retained = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert "PRIVATE_RECEIPT_CONSTRUCTION_SENTINEL" not in first.value.public_message
    assert retained is not None and retained.status == ClmStatus.SUBMITTING
    assert retained.execution_receipt is None
    assert retained.submission_snapshot is not None
    submission_id = retained.submission_snapshot.submission_id
    target_outcome = cases.get_target_outcome(submission_id)
    assert target_outcome is not None
    assert cases.get_execution_state(submission_id) == (
        GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED
    )
    assert "PRIVATE_RECEIPT_CONSTRUCTION_SENTINEL" not in target_outcome.model_dump_json()
    assert "PRIVATE_RECEIPT_CONSTRUCTION_SENTINEL" not in retained.model_dump_json()
    assert target.calls == expected_calls

    if outcome == "success":
        with pytest.raises(ClmInfrastructureError) as repeated:
            clm.submit(case_id=case_id)  # type: ignore[arg-type]
        assert repeated.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
        assert target.calls == expected_calls

    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    duplicate = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == expected_status
    assert duplicate.status == expected_status
    assert (recovered.error.code if recovered.error else None) == expected_code
    assert target.calls == expected_calls
    assert cases.get_execution_state(submission_id) == (
        GoldTierExecutionLedgerState.FINALIZED
    )
    receipt = cases.get_execution_receipt(submission_id)
    assert receipt is not None
    assert "PRIVATE_RECEIPT_CONSTRUCTION_SENTINEL" not in receipt.model_dump_json()
    event_types = [event.event_type for event in recovered.events]
    assert event_types.count("MOCK_SUBMISSION_STARTED") == 1
    assert event_types.count("MOCK_TARGET_EXECUTION_RECORDED") == 1
    assert sum(
        event_types.count(event_type)
        for event_type in (
            "MOCK_SUBMISSION_COMPLETED",
            "CLM_REVIEW_REQUIRED",
            "CLM_SUBMISSION_FAILED",
        )
    ) == 1


@pytest.mark.parametrize(
    ("outcome", "mapping_helper", "sentinel"),
    [
        ("success", "_map_execution_result", "PRIVATE_SUCCESS_RESULT_SENTINEL"),
        ("match", "_map_execution_result", "PRIVATE_MATCH_RESULT_SENTINEL"),
        ("policy", "_map_execution_error", "PRIVATE_FAILURE_ERROR_SENTINEL"),
        ("partial", "_map_execution_result", "PRIVATE_PARTIAL_RESULT_SENTINEL"),
    ],
)
def test_rich_result_or_error_mapping_failure_recovers_without_target_reexecution(
    monkeypatch: pytest.MonkeyPatch,
    outcome: Literal["success", "match", "policy", "partial"],
    mapping_helper: str,
    sentinel: str,
) -> None:
    uen, target, expected_status, expected_calls, expected_code = (
        recovery_case_configuration(outcome)
    )
    cases, _, _, clm, _, case_id = make_ready_case(uen=uen, goldtier=target)
    mapping = getattr(onboarding_module, mapping_helper)
    failed = False

    def fail_once(*args: object, **kwargs: object):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError(sentinel)
        return mapping(*args, **kwargs)

    monkeypatch.setattr(onboarding_module, mapping_helper, fail_once)
    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]

    retained = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert sentinel not in first.value.public_message
    assert retained is not None and retained.submission_snapshot is not None
    submission_id = retained.submission_snapshot.submission_id
    target_outcome = cases.get_target_outcome(submission_id)
    assert target_outcome is not None
    assert sentinel not in target_outcome.model_dump_json()
    assert retained.execution_receipt is None
    assert target.calls == expected_calls

    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == expected_status
    assert (recovered.error.code if recovered.error else None) == expected_code
    assert target.calls == expected_calls
    assert sentinel not in recovered.model_dump_json()
    assert cases.get_execution_state(submission_id) == (
        GoldTierExecutionLedgerState.FINALIZED
    )


def test_two_concurrent_retries_after_pre_receipt_failure_finalize_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, _, _, clm, target, case_id = make_ready_case()
    build_receipt = cases._build_execution_receipt  # type: ignore[attr-defined]
    failed = False

    def fail_once(*args: object, **kwargs: object):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("PRIVATE_CONCURRENT_RECOVERY_SENTINEL")
        return build_receipt(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cases, "_build_execution_receipt", fail_once)
    with pytest.raises(ClmInfrastructureError) as initial:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert initial.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"

    start = Barrier(3)

    def recover() -> ClmStatus:
        start.wait()
        return clm.submit(case_id=case_id).status  # type: ignore[arg-type]

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(recover)
        second = executor.submit(recover)
        start.wait()
        results = [first.result(timeout=5), second.result(timeout=5)]

    recovered = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert results == [
        ClmStatus.MOCK_GOLDTIER_SUBMITTED,
        ClmStatus.MOCK_GOLDTIER_SUBMITTED,
    ]
    assert recovered is not None
    assert target.calls == ["search", "shell", "policy", "amend"]
    event_types = [event.event_type for event in recovered.events]
    assert event_types.count("MOCK_SUBMISSION_STARTED") == 1
    assert event_types.count("MOCK_TARGET_EXECUTION_RECORDED") == 1
    assert event_types.count("MOCK_SUBMISSION_COMPLETED") == 1
    assert "PRIVATE_CONCURRENT_RECOVERY_SENTINEL" not in recovered.model_dump_json()


@pytest.mark.parametrize(
    ("outcome", "uen", "expected_status", "expected_calls", "expected_code"),
    [
        (
            "success",
            "202400001A",
            ClmStatus.MOCK_GOLDTIER_SUBMITTED,
            ["search", "shell", "policy", "amend"],
            None,
        ),
        (
            "match",
            "202400001A",
            ClmStatus.REVIEW_REQUIRED,
            ["search"],
            "GT_EXISTING_PARTY_REVIEW_REQUIRED",
        ),
        (
            "policy",
            "202400003C",
            ClmStatus.FAILED,
            ["search", "shell", "policy"],
            "GT_POLICY_VALIDATION_FAILED",
        ),
        (
            "partial",
            "202400004D",
            ClmStatus.REVIEW_REQUIRED,
            ["search", "shell", "policy", "amend"],
            "GT_OPTIONAL_SECTION_REVIEW",
        ),
    ],
)
def test_result_mapping_failure_recovers_actual_target_outcome_without_reexecution(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    uen: str,
    expected_status: ClmStatus,
    expected_calls: list[str],
    expected_code: str | None,
) -> None:
    target = RecordingGoldTier(
        match_found=outcome == "match",
        policy_failure_keys=(
            frozenset({"202400003C"}) if outcome == "policy" else frozenset()
        ),
        partial_amend_keys=(
            frozenset({"202400004D"}) if outcome == "partial" else frozenset()
        ),
    )
    _, _, _, clm, _, case_id = make_ready_case(uen=uen, goldtier=target)
    translate = clm_orchestration_module._terminal_from_receipt
    failed = False

    def fail_once(*args: object, **kwargs: object):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("PRIVATE_RESULT_TRANSLATION_SENTINEL")
        return translate(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        clm_orchestration_module,
        "_terminal_from_receipt",
        fail_once,
    )
    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    retained = clm.get(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert "PRIVATE_RESULT_TRANSLATION_SENTINEL" not in first.value.public_message
    assert retained is not None and retained.status == ClmStatus.SUBMITTING
    assert retained.execution_receipt is not None
    assert "PRIVATE_RESULT_TRANSLATION_SENTINEL" not in retained.model_dump_json()
    assert target.calls == expected_calls

    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == expected_status
    assert (recovered.error.code if recovered.error else None) == expected_code
    assert target.calls == expected_calls
    assert [event.event_type for event in recovered.events].count(
        "MOCK_TARGET_EXECUTION_RECORDED"
    ) == 1


def test_post_target_completion_clock_failure_is_retryable_without_duplicate_calls() -> None:
    repository = InMemoryClmOrchestrationRepository()
    clock = FailOnceCompletionClock(repository)
    _, _, _, clm, target, case_id = make_ready_case(
        clm_repository=repository,
        clm_clock=clock,
    )
    clock.case_id = case_id  # type: ignore[assignment]

    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert "PRIVATE_COMPLETION_CLOCK_SENTINEL" not in first.value.public_message
    assert target.calls == ["search", "shell", "policy", "amend"]

    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert clock.failed
    assert recovered.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_post_target_terminal_event_construction_failure_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, _, clm, target, case_id = make_ready_case()
    build_event = clm_orchestration_module._build_clm_event
    failed = False

    def fail_once(*args: object, **kwargs: object):
        nonlocal failed
        event_type = kwargs.get("event_type")
        if (
            event_type
            in {
                ClmEventType.MOCK_SUBMISSION_COMPLETED,
                ClmEventType.CLM_REVIEW_REQUIRED,
                ClmEventType.CLM_SUBMISSION_FAILED,
            }
            and not failed
        ):
            failed = True
            raise RuntimeError("PRIVATE_TERMINAL_EVENT_SENTINEL")
        return build_event(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(clm_orchestration_module, "_build_clm_event", fail_once)
    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert "PRIVATE_TERMINAL_EVENT_SENTINEL" not in first.value.public_message
    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert recovered.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED
    assert target.calls == ["search", "shell", "policy", "amend"]


@pytest.mark.parametrize(
    ("fail_point", "conflict"),
    [("terminal", False), ("receipt", True)],
)
def test_post_target_repository_failures_recover_without_reexecution(
    fail_point: Literal["receipt", "terminal"],
    conflict: bool,
) -> None:
    repository = FailOnceClmRepository(
        fail_point=fail_point,
        conflict=conflict,
    )
    _, _, _, clm, target, case_id = make_ready_case(clm_repository=repository)

    with pytest.raises(ClmInfrastructureError) as first:
        clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert first.value.code == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert "PRIVATE_TERMINAL_REPOSITORY_SENTINEL" not in first.value.public_message
    assert target.calls == ["search", "shell", "policy", "amend"]

    recovered = clm.submit(case_id=case_id)  # type: ignore[arg-type]
    assert repository.failed
    assert recovered.status == ClmStatus.MOCK_GOLDTIER_SUBMITTED
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert [event.event_type for event in recovered.events].count(
        "MOCK_SUBMISSION_COMPLETED"
    ) == 1


def test_case_evidence_and_submission_are_isolated() -> None:
    _, documents, ownership, clm, target = build_services()
    ready = clm.create_case("202400001A")
    other = clm.create_case("202400001A")
    document = documents.create_document(
        case_id=ready.case_id,
        display_name="case-a.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    for field_key in DocumentFieldKey:
        documents.review_field(
            case_id=ready.case_id,
            document_id=document.document_id,
            field_key=field_key,
            decision=ReviewDecision.ACCEPTED,
        )
    ownership.load(case_id=ready.case_id)
    ownership.analyze(case_id=ready.case_id)

    first = clm.evaluate(case_id=ready.case_id)
    second = clm.evaluate(case_id=other.case_id)
    assert first.status == ClmStatus.READY_FOR_MOCK_SUBMISSION
    assert set(second.readiness.blockers) == {"DOCUMENT_REQUIRED", "OWNERSHIP_REQUIRED"}
    clm.submit(case_id=ready.case_id)
    unchanged = clm.get(case_id=other.case_id)
    assert unchanged is not None and unchanged.submission_snapshot is None
    assert target.calls == ["search", "shell", "policy", "amend"]


@pytest.mark.anyio
async def test_phase05_api_happy_path_and_safe_unified_summary() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/clm/cases", json={"uen": "202400001A"})
        case_id = created.json()["case"]["case_id"]
        uploaded = await client.post(
            f"/api/demo/onboarding/cases/{case_id}/documents",
            content=PDF,
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "integrated.pdf",
                "X-Mock-IDP-Scenario": "ALL_FIELDS_MATCH",
            },
        )
        for field in uploaded.json()["fields"]:
            await client.post(
                f"/api/onboarding/cases/{case_id}/documents/"
                f"{uploaded.json()['document_id']}/reviews",
                json={"field_key": field["field_key"], "decision": "ACCEPTED"},
            )
        await client.post(
            f"/api/demo/onboarding/cases/{case_id}/ownership/load",
            headers={"X-Mock-Ownership-Scenario": "DIRECT_OWNER"},
        )
        await client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze")
        evaluated = await client.post(f"/api/clm/cases/{case_id}/readiness/evaluate")
        plan = await client.get(f"/api/clm/cases/{case_id}/submission-plan")
        submitted = await client.post(f"/api/clm/cases/{case_id}/submit")
        fetched = await client.get(f"/api/clm/cases/{case_id}")

    assert created.status_code == 201
    assert created.json()["case"]["state"] == "VALIDATED"
    assert created.json()["status"] == "COLLECTING_EVIDENCE"
    assert evaluated.json()["status"] == "READY_FOR_MOCK_SUBMISSION"
    assert plan.json()["environment"] == "MOCK"
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "MOCK_GOLDTIER_SUBMITTED"
    assert submitted.json()["submission"]["document_reference_count"] == 1
    assert fetched.json() == submitted.json()
    assert "registry_source_link" not in submitted.text
    assert "source_reference" not in submitted.text
    assert "execution_receipt" not in submitted.text
    assert "input_fingerprint" not in submitted.text
    assert "Ready-for-Approval" not in submitted.text


@pytest.mark.anyio
async def test_pre_receipt_failure_api_and_recovery_projection_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, documents, ownership, clm, target, case_id = make_ready_case()
    build_receipt = cases._build_execution_receipt  # type: ignore[attr-defined]
    failed = False

    def fail_once(*args: object, **kwargs: object):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("PRIVATE_API_RECEIPT_SENTINEL")
        return build_receipt(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(cases, "_build_execution_receipt", fail_once)
    application = create_app(
        Settings(app_env="test", demo_controls_enabled=True),
        onboarding_service=cases,
        document_processing_service=documents,
        ownership_analysis_service=ownership,
        clm_orchestration_service=clm,
    )
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(f"/api/clm/cases/{case_id}/submit")
        recovered = await client.post(f"/api/clm/cases/{case_id}/submit")
        current = await client.get(f"/api/clm/cases/{case_id}")

    assert first.status_code == 503
    assert first.json()["detail"]["code"] == "CLM_FINALIZATION_RETRY_REQUIRED"
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "MOCK_GOLDTIER_SUBMITTED"
    assert current.json() == recovered.json()
    assert target.calls == ["search", "shell", "policy", "amend"]
    combined = first.text + recovered.text + current.text
    assert "PRIVATE_API_RECEIPT_SENTINEL" not in combined
    assert "target_outcome" not in combined
    assert "execution_receipt" not in combined
    assert "idempotency_fingerprint" not in combined


@pytest.mark.anyio
async def test_malformed_target_response_api_projection_is_sanitized() -> None:
    target = UntrustedResponseGoldTier(
        stage="shell",
        response=GoldTierOperationResult.model_construct(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id="GT-PRIVATE_API_TARGET_SENTINEL\r\n",
            status="SHELL_CREATED",
            message="PRIVATE_API_MESSAGE_SENTINEL\r\n",
        ),
    )
    cases, documents, ownership, clm, _, case_id = make_ready_case(goldtier=target)
    application = create_app(
        Settings(app_env="test", demo_controls_enabled=True),
        onboarding_service=cases,
        document_processing_service=documents,
        ownership_analysis_service=ownership,
        clm_orchestration_service=clm,
    )
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        failed = await client.post(f"/api/clm/cases/{case_id}/submit")
        current = await client.get(f"/api/clm/cases/{case_id}")
        duplicate = await client.post(f"/api/clm/cases/{case_id}/submit")

    assert failed.status_code == 503
    assert failed.json()["detail"]["code"] == "GT_MALFORMED_TARGET_RESPONSE"
    assert current.status_code == 200 and current.json()["status"] == "FAILED"
    assert duplicate.status_code == 200 and duplicate.json() == current.json()
    assert target.calls == ["search", "shell"]
    combined = failed.text + current.text + duplicate.text
    assert "PRIVATE_API_TARGET_SENTINEL" not in combined
    assert "PRIVATE_API_MESSAGE_SENTINEL" not in combined
    assert "target_outcome" not in combined
    assert "execution_receipt" not in combined


@pytest.mark.anyio
async def test_blocked_api_submit_returns_typed_conflict_and_zero_result() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/clm/cases", json={"uen": "202400001A"})
        case_id = created.json()["case"]["case_id"]
        blocked = await client.post(f"/api/clm/cases/{case_id}/submit")
        current = await client.get(f"/api/clm/cases/{case_id}")
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == {
        "code": "CLM_NOT_READY",
        "message": "The case is not ready for Mock GoldTier submission.",
    }
    assert current.json()["goldtier_result"] is None
