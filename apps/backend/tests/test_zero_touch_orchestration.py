from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.composition import build_zero_touch_demo_control
from app.config import Settings
from app.connectors.goldtier_models import GoldTierOperationResult, GoldTierOutcome
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.demo.zero_touch_control import ZeroTouchDemoScenario
from app.domain.documents import ReviewDecision
from app.domain.zero_touch import ExceptionResolutionAction
from app.main import create_app
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.zero_touch_errors import ZeroTouchInfrastructureError
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository

PDF = b"%PDF-1.4\nSYNTHETIC TEST ONLY - NO CUSTOMER DATA\n%%EOF"


class RecordingMockGoldTier(MockGoldTierConnector):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.calls: list[str] = []

    def search_party(self, request: Any, metadata: Any) -> Any:
        self.calls.append("search")
        return super().search_party(request, metadata)

    def create_shell_customer(self, request: Any, metadata: Any) -> Any:
        self.calls.append("shell")
        return super().create_shell_customer(request, metadata)

    def create_policy(self, request: Any, metadata: Any) -> Any:
        self.calls.append("policy")
        return super().create_policy(request, metadata)

    def amend_party(self, party_id: str, request: Any, metadata: Any) -> Any:
        self.calls.append("amend")
        return super().amend_party(party_id, request, metadata)


class MalformedShellGoldTier(RecordingMockGoldTier):
    def create_shell_customer(self, request: Any, metadata: Any) -> Any:
        self.calls.append("shell")
        return GoldTierOperationResult.model_construct(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id="X" * 97,
            status="SHELL_CREATED",
            message="synthetic malformed response",
        )


class MultipleBlockerIdp(MockIdpProvider):
    def __init__(self) -> None:
        super().__init__(MockIdpScenario.FIELD_MISMATCH)

    def process(self, document: Any) -> Any:
        result = super().process(document)
        fields = [
            field.model_copy(update={"confidence": 0.42})
            if field.field_key.value == "legal_name"
            else field
            for field in result.fields
        ]
        return result.model_copy(update={"fields": fields})


def build_system(
    *, max_transitions: int = 12, connector: RecordingMockGoldTier | None = None
) -> tuple[
    TestClient,
    ZeroTouchOrchestrator,
    DocumentProcessingService,
    RecordingMockGoldTier,
    Any,
]:
    target = connector or RecordingMockGoldTier(
        policy_validation_failure_keys=frozenset({"202400003C"}),
        partial_amend_external_keys=frozenset({"202400004D"}),
        match_found_external_keys=frozenset({"202400005E"}),
    )
    cases = OnboardingService(
        acra=MockAcraConnector(),
        goldtier=target,
        repository=InMemoryOnboardingCaseRepository(),
    )
    documents = DocumentProcessingService(
        cases=cases,
        idp=MockIdpProvider(),
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=1024 * 1024,
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
        repository=InMemoryClmOrchestrationRepository(),
    )
    zero = ZeroTouchOrchestrator(
        cases=cases,
        documents=documents,
        ownership=ownership,
        clm=clm,
        repository=InMemoryZeroTouchAutomationRepository(),
        max_transitions_per_run=max_transitions,
    )
    demo = build_zero_touch_demo_control()
    app = create_app(
        Settings(app_env="test", demo_controls_enabled=True),
        onboarding_service=cases,
        document_processing_service=documents,
        ownership_analysis_service=ownership,
        clm_orchestration_service=clm,
        zero_touch_orchestrator=zero,
        zero_touch_demo_control=demo,
    )
    return TestClient(app), zero, documents, target, demo


def start_demo(client: TestClient, scenario: str) -> dict[str, Any]:
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": scenario},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    response = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "synthetic.pdf"},
        content=PDF,
    )
    if scenario == "TECHNICAL_FAILURE":
        assert response.status_code == 503
        return client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
    assert response.status_code == 200
    return response.json()


def test_straight_through_reaches_mock_target_with_zero_human_interventions() -> None:
    client, _, documents, target, _ = build_system()
    result = start_demo(client, "STRAIGHT_THROUGH")
    assert result["status"] == "COMPLETED"
    assert result["clm"]["status"] == "MOCK_GOLDTIER_SUBMITTED"
    assert result["completed_stages"] == [
        "REGISTRY",
        "DOCUMENT",
        "OWNERSHIP",
        "READINESS",
        "MOCK_GOLDTIER",
    ]
    assert result["metrics"]["human_interventions"] == 0
    assert target.calls == ["search", "shell", "policy", "amend"]
    case_id = UUID(result["case"]["case_id"])
    document = documents.list_documents(case_id=case_id)[0]
    assert document.completion_method == "AUTO_CONFIRMED"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", "/api/onboarding/mock-scenarios", {}),
        (
            "POST",
            "/api/demo/clm/zero-touch/cases",
            {"json": {"uen": "202400001A", "scenario": "STRAIGHT_THROUGH"}},
        ),
        (
            "POST",
            "/api/demo/clm/zero-touch/cases/00000000-0000-4000-8000-000000000001/documents",
            {"content": PDF},
        ),
        (
            "POST",
            "/api/demo/onboarding/cases/00000000-0000-4000-8000-000000000001/ownership/load",
            {},
        ),
        (
            "POST",
            "/api/demo/onboarding/cases/00000000-0000-4000-8000-000000000001/documents",
            {"content": PDF},
        ),
    ],
)
def test_demo_routes_are_disabled_by_default(
    method: str, path: str, kwargs: dict[str, object]
) -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    response = client.request(method, path, **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DEMO_CONTROLS_DISABLED"


@pytest.mark.parametrize(
    ("scenario", "exception_type", "stage"),
    [
        ("DOCUMENT_DISCREPANCY", "DOCUMENT_SOURCE_CONFLICT", "DOCUMENT"),
        ("LOW_CONFIDENCE_DOCUMENT", "DOCUMENT_LOW_CONFIDENCE", "DOCUMENT"),
        ("OWNERSHIP_EXCEPTION", "OWNERSHIP_CYCLE", "OWNERSHIP"),
        ("OWNERSHIP_INCOMPLETE", "OWNERSHIP_INCOMPLETE", "OWNERSHIP"),
    ],
)
def test_business_exceptions_pause_before_target(
    scenario: str, exception_type: str, stage: str
) -> None:
    client, _, _, target, _ = build_system()
    result = start_demo(client, scenario)
    assert result["status"] == "WAITING_FOR_REVIEW"
    assert result["current_stage"] == stage
    assert result["active_exceptions"][0]["exception_type"] == exception_type
    assert target.calls == []


def test_document_source_conflict_resolution_is_one_intervention_and_auto_resumes() -> None:
    client, _, _, target, _ = build_system()
    paused = start_demo(client, "DOCUMENT_DISCREPANCY")
    exception = paused["active_exceptions"][0]
    resolved = client.post(
        (
            f"/api/clm/zero-touch/cases/{paused['case']['case_id']}/exceptions/"
            f"{exception['exception_id']}/resolve"
        ),
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": paused["version"],
            "evidence_version": exception["evidence_version"],
        },
    )
    assert resolved.status_code == 200
    result = resolved.json()
    assert result["status"] == "COMPLETED"
    assert result["metrics"]["human_interventions"] == 1
    assert result["metrics"]["exceptions_resolved"] == 1
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_low_confidence_has_no_unconfirmed_resolution_action() -> None:
    client, _, _, target, _ = build_system()
    paused = start_demo(client, "LOW_CONFIDENCE_DOCUMENT")
    exception = paused["active_exceptions"][0]
    assert exception["available_actions"] == []
    resolved = client.post(
        (
            f"/api/clm/zero-touch/cases/{paused['case']['case_id']}/exceptions/"
            f"{exception['exception_id']}/resolve"
        ),
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": paused["version"],
            "evidence_version": exception["evidence_version"],
        },
    )
    assert resolved.status_code == 422
    assert resolved.json()["detail"]["code"] == "ZERO_TOUCH_RESOLUTION_NOT_ALLOWED"
    assert target.calls == []


def test_existing_party_stops_after_search_and_creates_unresolvable_review() -> None:
    client, _, _, target, _ = build_system()
    result = start_demo(client, "EXISTING_PARTY")
    assert result["status"] == "WAITING_FOR_REVIEW"
    assert result["active_exceptions"][0]["exception_type"] == (
        "EXISTING_PARTY_REVIEW_REQUIRED"
    )
    assert result["active_exceptions"][0]["available_actions"] == []
    assert target.calls == ["search"]


def test_provider_and_target_failures_are_technical_not_business_review() -> None:
    client, _, _, target, _ = build_system()
    provider_failure = start_demo(client, "TECHNICAL_FAILURE")
    assert provider_failure["status"] == "TECHNICAL_FAILURE"
    assert provider_failure["active_exceptions"] == []
    assert provider_failure["technical_failure"]["code"] == "IDP_PROCESSING_FAILED"
    assert target.calls == []

    client, _, _, target, _ = build_system()
    target_failure = start_demo(client, "TARGET_FAILURE")
    assert target_failure["status"] == "TECHNICAL_FAILURE"
    assert target_failure["active_exceptions"] == []
    assert target_failure["technical_failure"]["code"] == "GT_POLICY_VALIDATION_FAILED"
    assert target.calls == ["search", "shell", "policy"]


def test_duplicate_and_concurrent_start_do_not_repeat_completed_work() -> None:
    client, zero, documents, target, demo = build_system()
    created = zero.create_case("202400001A")
    demo.register(created.case_id, ZeroTouchDemoScenario.STRAIGHT_THROUGH)
    case = created
    entity = client.get(f"/api/clm/zero-touch/cases/{created.case_id}").json()["case"]
    assert entity["entity"] is not None
    domain_case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    assert domain_case is not None and domain_case.entity is not None
    documents.create_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=demo.idp_provider_for(created.case_id, domain_case.entity),
    )
    barrier = Barrier(2)

    def run() -> str:
        barrier.wait()
        return zero.start(
            case_id=case.case_id,
            ownership_provider=demo.ownership_provider_for(case.case_id),
        ).status.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run) for _ in range(2)]
        statuses = sorted(future.result() for future in futures)
    assert statuses == ["COMPLETED", "COMPLETED"]
    version = zero.get(case_id=case.case_id).version  # type: ignore[union-attr]
    assert zero.start(case_id=case.case_id).version == version
    resumed = client.post(f"/api/clm/zero-touch/cases/{case.case_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["version"] == version
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_multiple_document_blockers_are_preserved_in_one_review_checkpoint() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    result = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MultipleBlockerIdp(),
        ownership_provider=MockOwnershipProvider(),
    )
    assert result.status == "WAITING_FOR_REVIEW"
    assert set(result.active_exceptions[0].blocker_codes) == {
        "DOCUMENT_LOW_CONFIDENCE",
        "DOCUMENT_SOURCE_CONFLICT",
    }
    assert target.calls == []


def test_source_resolution_preserves_low_confidence_as_a_new_blocker() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MultipleBlockerIdp(),
        ownership_provider=MockOwnershipProvider(),
    )
    first = paused.active_exceptions[0]
    resumed = zero.resolve_exception(
        case_id=created.case_id,
        exception_id=first.exception_id,
        action=ExceptionResolutionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=paused.version,
        evidence_version=first.evidence_version,
    )
    assert resumed.status == "WAITING_FOR_REVIEW"
    assert resumed.active_exceptions[0].exception_type == "DOCUMENT_LOW_CONFIDENCE"
    assert resumed.active_exceptions[0].available_actions == ()
    assert resumed.metrics.human_interventions == 1
    assert target.calls == []


@pytest.mark.parametrize("mutation", ["legal_name", "registered_address"])
def test_canonical_mutation_without_new_events_makes_resolution_stale(
    mutation: str,
) -> None:
    client, zero, documents, target, _ = build_system()
    paused = start_demo(client, "DOCUMENT_DISCREPANCY")
    case_id = UUID(paused["case"]["case_id"])
    case = zero._cases.get_case(case_id)  # noqa: SLF001
    assert case is not None and case.entity is not None
    event_count = len(case.events)
    if mutation == "legal_name":
        case.entity.legal_name = "SYNTHETIC MUTATED CANONICAL NAME"
    else:
        assert case.entity.registered_address is not None
        case.entity.registered_address.postal_code = "999999"
    zero._cases._repository.save(case)  # type: ignore[attr-defined]  # noqa: SLF001
    exception = paused["active_exceptions"][0]
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/exceptions/{exception['exception_id']}/resolve",
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": paused["version"],
            "evidence_version": exception["evidence_version"],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ZERO_TOUCH_EXCEPTION_STALE"
    current = zero.get(case_id=case_id)
    assert current is not None and current.status == "WAITING_FOR_REVIEW"
    assert len(zero._cases.get_case(case_id).events) == event_count  # type: ignore[union-attr]  # noqa: SLF001
    assert documents.list_documents(case_id=case_id)[0].state == "REVIEW_REQUIRED"
    assert target.calls == []


def test_invalid_pdf_does_not_publish_started_state() -> None:
    client, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    response = client.post(
        f"/api/clm/zero-touch/cases/{created.case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "invalid.pdf"},
        content=b"not a pdf",
    )
    assert response.status_code == 422
    current = zero.get(case_id=created.case_id)
    assert current is not None
    assert current.status == "PENDING_INPUTS"
    assert current.version == created.version
    assert all(event.event_type != "ONBOARDING_STARTED" for event in current.events)
    assert target.calls == []


def test_registry_review_document_attach_does_not_publish_running_state() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400002B")
    assert created.status == "WAITING_FOR_REVIEW"
    current = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert current.status == "WAITING_FOR_REVIEW"
    assert current.current_stage == "REGISTRY"
    assert all(event.event_type != "ONBOARDING_STARTED" for event in current.events)
    assert target.calls == []


def test_unexpected_document_fault_terminalizes_with_sanitized_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")

    def fail_assessment(**_: object) -> object:
        raise RuntimeError("PRIVATE_ASSESSMENT_SENTINEL")

    monkeypatch.setattr(zero._documents, "assess_auto_clear", fail_assessment)  # noqa: SLF001
    with pytest.raises(ZeroTouchInfrastructureError) as failure:
        zero.attach_document(
            case_id=created.case_id,
            display_name="synthetic.pdf",
            content_type="application/pdf",
            content=PDF,
        )
    assert failure.value.code == "ZERO_TOUCH_UNEXPECTED_FAILURE"
    current = zero.get(case_id=created.case_id)
    assert current is not None and current.status == "TECHNICAL_FAILURE"
    assert current.current_stage == "DOCUMENT"
    assert len(
        [
            event
            for event in current.events
            if event.event_type == "AUTOMATION_TECHNICAL_FAILURE"
        ]
    ) == 1
    assert "PRIVATE_ASSESSMENT_SENTINEL" not in current.model_dump_json()
    assert zero.start(case_id=created.case_id).version == current.version
    assert target.calls == []


def test_ownership_provider_binding_survives_document_resolution() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A")
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ownership_provider=MockOwnershipProvider(MockOwnershipScenario.CYCLE),
    )
    exception = paused.active_exceptions[0]
    resumed = zero.resolve_exception(
        case_id=created.case_id,
        exception_id=exception.exception_id,
        action=ExceptionResolutionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=paused.version,
        evidence_version=exception.evidence_version,
    )
    assert resumed.status == "WAITING_FOR_REVIEW"
    assert resumed.current_stage == "OWNERSHIP"
    assert resumed.active_exceptions[0].exception_type == "OWNERSHIP_CYCLE"
    assert target.calls == []


def test_phase05_finalization_recovery_completes_without_target_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zero, _, target, _ = build_system()
    original = zero._cases._build_execution_receipt  # type: ignore[attr-defined]  # noqa: SLF001
    failed = False

    def fail_once(*args: object, **kwargs: object) -> object:
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("PRIVATE_FINALIZATION_SENTINEL")
        return original(*args, **kwargs)

    monkeypatch.setattr(zero._cases, "_build_execution_receipt", fail_once)  # noqa: SLF001
    created = zero.create_case("202400001A")
    completed = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert completed.status == "COMPLETED"
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert "PRIVATE_FINALIZATION_SENTINEL" not in completed.model_dump_json()


def _create_reviewed_document(
    documents: DocumentProcessingService,
    *,
    case_id: UUID,
    provider: MockIdpProvider,
    display_name: str,
) -> Any:
    document = documents.create_document(
        case_id=case_id,
        display_name=display_name,
        content_type="application/pdf",
        content=PDF,
        provider=provider,
    )
    for field in document.fields:
        document = documents.review_field(
            case_id=case_id,
            document_id=document.document_id,
            field_key=field.field_key,
            decision=ReviewDecision.ACCEPTED,
        )
    return document


def _create_pending_document(
    documents: DocumentProcessingService,
    *,
    case_id: UUID,
    provider: MockIdpProvider,
    display_name: str,
) -> Any:
    return documents.create_document(
        case_id=case_id,
        display_name=display_name,
        content_type="application/pdf",
        content=PDF,
        provider=provider,
    )


def test_P06_QG_005_REVIEWED_CONFLICT_EARLIER_DOCUMENT() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A")
    conflict = _create_reviewed_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        display_name="earlier-conflict.pdf",
    )
    _create_pending_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.ALL_FIELDS_MATCH),
        display_name="later-clean.pdf",
    )

    paused = zero.start(case_id=created.case_id)

    assert paused.status == "WAITING_FOR_REVIEW"
    assert paused.current_stage == "DOCUMENT"
    assert paused.active_exceptions[0].exception_type == "DOCUMENT_SOURCE_CONFLICT"
    assert paused.active_exceptions[0].evidence[0].reference_id == conflict.document_id
    assert target.calls == []


def test_P06_QG_005_REVIEWED_CONFLICT_LATER_DOCUMENT() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A")
    _create_pending_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.ALL_FIELDS_MATCH),
        display_name="earlier-clean.pdf",
    )
    conflict = _create_reviewed_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        display_name="later-conflict.pdf",
    )

    paused = zero.start(case_id=created.case_id)

    assert paused.status == "WAITING_FOR_REVIEW"
    assert paused.active_exceptions[0].evidence[0].reference_id == conflict.document_id
    assert target.calls == []


def test_P06_QG_005_MULTIPLE_REVIEWED_CONFLICTS_ARE_RETAINED() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A")
    first = _create_reviewed_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        display_name="first-conflict.pdf",
    )
    second = _create_reviewed_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        display_name="second-conflict.pdf",
    )

    paused = zero.start(case_id=created.case_id)

    assert [item.evidence[0].reference_id for item in paused.active_exceptions] == [
        first.document_id,
        second.document_id,
    ]
    assert target.calls == []


def test_P06_QG_013_EQUAL_TIMESTAMPS_PRESERVE_INSERTION_ORDER_100_RUNS() -> None:
    _, zero, documents, target, _ = build_system()
    fixed_document_time = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    documents._clock = lambda: fixed_document_time  # noqa: SLF001

    for index in range(100):
        created = zero.create_case("202400001A")
        first = _create_reviewed_document(
            documents,
            case_id=created.case_id,
            provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
            display_name=f"first-conflict-{index}.pdf",
        )
        second = _create_reviewed_document(
            documents,
            case_id=created.case_id,
            provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
            display_name=f"second-conflict-{index}.pdf",
        )
        assert first.created_at == second.created_at == fixed_document_time
        assert [item.document_id for item in documents.list_documents(case_id=created.case_id)] == [
            first.document_id,
            second.document_id,
        ]

        paused = zero.start(case_id=created.case_id)

        assert [item.evidence[0].reference_id for item in paused.active_exceptions] == [
            first.document_id,
            second.document_id,
        ]
        assert paused.status == "WAITING_FOR_REVIEW"

    assert target.calls == []


def test_P06_QG_013_FORMER_FLAKY_TEST_IS_STABLE_100_RUNS() -> None:
    for _ in range(100):
        test_P06_QG_005_MULTIPLE_REVIEWED_CONFLICTS_ARE_RETAINED()


def test_P06_QG_005_REVIEWED_CONFLICT_RESOLVED_BY_KEEP_REGISTRY() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A")
    reviewed = _create_reviewed_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        display_name="reviewed-conflict.pdf",
    )
    mismatch = next(field for field in reviewed.fields if field.comparison_status == "MISMATCH")
    original = mismatch.original_extracted_value
    reviewed_value = mismatch.reviewed_value
    paused = zero.start(case_id=created.case_id)
    exception = paused.active_exceptions[0]

    completed = zero.resolve_exception(
        case_id=created.case_id,
        exception_id=exception.exception_id,
        action=ExceptionResolutionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=paused.version,
        evidence_version=exception.evidence_version,
    )

    current = documents.get_document(
        case_id=created.case_id, document_id=reviewed.document_id
    )
    assert completed.status == "COMPLETED"
    assert current is not None
    retained = next(field for field in current.fields if field.field_key == mismatch.field_key)
    assert retained.original_extracted_value == original
    assert retained.reviewed_value == reviewed_value
    assert current.source_conflict_resolutions[0].action == "KEEP_REGISTRY_VALUE"
    assert completed.metrics.human_interventions == 1
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_P06_QG_005_REVIEWED_LOW_CONFIDENCE_REMAINS_BLOCKED() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A")
    _create_reviewed_document(
        documents,
        case_id=created.case_id,
        provider=MockIdpProvider(MockIdpScenario.LOW_CONFIDENCE),
        display_name="reviewed-low-confidence.pdf",
    )

    paused = zero.start(case_id=created.case_id)

    assert paused.status == "WAITING_FOR_REVIEW"
    assert paused.active_exceptions[0].exception_type == "DOCUMENT_LOW_CONFIDENCE"
    assert paused.active_exceptions[0].available_actions == ()
    assert target.calls == []


def _exercise_repeated_finalization_recovery(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uen: str,
    expected_status: str,
    expected_code: str | None,
    expected_calls: list[str],
) -> None:
    _, zero, _, target, demo = build_system()
    original = zero._cases._build_execution_receipt  # type: ignore[attr-defined]  # noqa: SLF001
    fault_enabled = True

    def fail_while_enabled(*args: object, **kwargs: object) -> object:
        if fault_enabled:
            raise RuntimeError("PRIVATE_REPEATED_FINALIZATION_SENTINEL")
        return original(*args, **kwargs)

    monkeypatch.setattr(zero._cases, "_build_execution_receipt", fail_while_enabled)  # noqa: SLF001
    created = zero.create_case(uen)
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    assert case is not None and case.entity is not None
    pending = zero.attach_document(
        case_id=created.case_id,
        display_name="recovery.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=demo.idp_provider_for(created.case_id, case.entity),
    )
    before = zero._clm.get(case_id=created.case_id)  # noqa: SLF001

    assert pending.status == "RECOVERY_PENDING"
    assert pending.current_stage == "MOCK_GOLDTIER"
    assert pending.technical_failure is None
    assert all(event.code != "AUTOMATION_LOOP_GUARD" for event in pending.events)
    assert target.calls == expected_calls
    assert before is not None and before.submission_snapshot is not None
    stable_snapshot = before.submission_snapshot.model_dump_json()

    still_pending = zero.start(case_id=created.case_id)
    assert still_pending.status == "RECOVERY_PENDING"
    assert still_pending.version == pending.version
    assert target.calls == expected_calls

    fault_enabled = False
    terminal = zero.start(case_id=created.case_id)
    after = zero._clm.get(case_id=created.case_id)  # noqa: SLF001

    assert terminal.status == expected_status
    if expected_code is None:
        assert terminal.metrics.final_outcome == "MOCK_GOLDTIER_SUBMITTED"
    elif expected_status == "WAITING_FOR_REVIEW":
        assert terminal.active_exceptions[0].blocker_code == expected_code
    else:
        assert terminal.technical_failure is not None
        assert terminal.technical_failure.code == expected_code
    assert after is not None and after.submission_snapshot is not None
    assert after.submission_snapshot.model_dump_json() == stable_snapshot
    assert target.calls == expected_calls
    assert "PRIVATE_REPEATED_FINALIZATION_SENTINEL" not in terminal.model_dump_json()


def test_P06_QG_006_REPEATED_SUCCESS_FINALIZATION_RETRY(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _exercise_repeated_finalization_recovery(
        monkeypatch,
        uen="202400001A",
        expected_status="COMPLETED",
        expected_code=None,
        expected_calls=["search", "shell", "policy", "amend"],
    )


def test_P06_QG_006_REPEATED_MATCH_FOUND_FINALIZATION_RETRY(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _exercise_repeated_finalization_recovery(
        monkeypatch,
        uen="202400005E",
        expected_status="WAITING_FOR_REVIEW",
        expected_code="GT_EXISTING_PARTY_REVIEW_REQUIRED",
        expected_calls=["search"],
    )


def test_P06_QG_006_REPEATED_POLICY_FAILURE_FINALIZATION_RETRY(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _exercise_repeated_finalization_recovery(
        monkeypatch,
        uen="202400003C",
        expected_status="TECHNICAL_FAILURE",
        expected_code="GT_POLICY_VALIDATION_FAILED",
        expected_calls=["search", "shell", "policy"],
    )


def test_P06_QG_006_REPEATED_PARTIAL_AMEND_FINALIZATION_RETRY(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _exercise_repeated_finalization_recovery(
        monkeypatch,
        uen="202400004D",
        expected_status="WAITING_FOR_REVIEW",
        expected_code="GT_OPTIONAL_SECTION_REVIEW",
        expected_calls=["search", "shell", "policy", "amend"],
    )


def test_P06_QG_006_RECOVERY_PENDING_NOT_LOOP_GUARD(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _exercise_repeated_finalization_recovery(
        monkeypatch,
        uen="202400001A",
        expected_status="COMPLETED",
        expected_code=None,
        expected_calls=["search", "shell", "policy", "amend"],
    )


def test_stale_and_cross_case_exception_resolution_cannot_advance() -> None:
    client, _, documents, target, _ = build_system()
    first = start_demo(client, "DOCUMENT_DISCREPANCY")
    second = start_demo(client, "DOCUMENT_DISCREPANCY")
    first_exception = first["active_exceptions"][0]
    first_case_id = UUID(first["case"]["case_id"])
    document = documents.list_documents(case_id=first_case_id)[0]
    matching = next(field for field in document.fields if field.comparison_status == "MATCH")
    documents.review_field(
        case_id=first_case_id,
        document_id=document.document_id,
        field_key=matching.field_key,
        decision=ReviewDecision.ACCEPTED,
    )
    stale = client.post(
        (
            f"/api/clm/zero-touch/cases/{first_case_id}/exceptions/"
            f"{first_exception['exception_id']}/resolve"
        ),
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": first["version"],
            "evidence_version": first_exception["evidence_version"],
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "ZERO_TOUCH_EXCEPTION_STALE"
    second_case_id = second["case"]["case_id"]
    isolated = client.post(
        (
            f"/api/clm/zero-touch/cases/{second_case_id}/exceptions/"
            f"{first_exception['exception_id']}/resolve"
        ),
        json={
            "action": "KEEP_REGISTRY_VALUE",
            "expected_automation_version": second["version"],
            "evidence_version": first_exception["evidence_version"],
        },
    )
    assert isolated.status_code == 409
    assert target.calls == []


def test_loop_guard_stops_safely_without_downstream_calls() -> None:
    client, _, _, target, _ = build_system(max_transitions=1)
    result = start_demo(client, "STRAIGHT_THROUGH")
    assert result["status"] == "TECHNICAL_FAILURE"
    assert result["technical_failure"]["code"] == "AUTOMATION_LOOP_GUARD"
    assert result["completed_stages"] == ["REGISTRY", "DOCUMENT"]
    assert target.calls == []


def test_malformed_target_response_terminalizes_without_replay_or_review() -> None:
    connector = MalformedShellGoldTier()
    client, zero, _, target, _ = build_system(connector=connector)
    result = start_demo(client, "STRAIGHT_THROUGH")
    assert result["status"] == "TECHNICAL_FAILURE"
    assert result["active_exceptions"] == []
    assert result["technical_failure"]["code"] == "GT_MALFORMED_TARGET_RESPONSE"
    assert target.calls == ["search", "shell"]
    same = zero.start(case_id=UUID(result["case"]["case_id"]))
    assert same.status == "TECHNICAL_FAILURE"
    assert target.calls == ["search", "shell"]
