from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.composition as composition
from app.composition import build_zero_touch_demo_control
from app.config import Settings
from app.connectors.goldtier_models import GoldTierOperationResult, GoldTierOutcome
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.demo.zero_touch_control import ZeroTouchDemoScenario
from app.domain.access import TeamId
from app.domain.documents import DocumentFieldKey, DocumentProfile, ReviewDecision
from app.domain.onboarding_intelligence import (
    MockRiskAssessment,
    MockRiskBand,
    OnboardingIntelligenceRecord,
)
from app.domain.reconciliation import ReconciliationOutcome
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    ExceptionResolutionAction,
    ZeroTouchAutomationRecord,
)
from app.main import create_app
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.document_errors import DocumentProcessingInfrastructureError
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.reconciliation_errors import (
    ReconciliationInfrastructureError,
    ReconciliationRequestError,
)
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.zero_touch_errors import (
    ZeroTouchInfrastructureError,
    ZeroTouchRequestError,
)
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import (
    InMemoryZeroTouchAutomationRepository,
    ZeroTouchRepositoryConflictError,
)

PDF = (Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf").read_bytes()


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


class RecordingMockAcra(MockAcraConnector):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def fetch_company(self, uen: str) -> Any:
        self.calls.append("entity")
        return super().fetch_company(uen)

    def fetch_officers(self, uen: str) -> Any:
        self.calls.append("officers")
        return super().fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> Any:
        self.calls.append("ownership")
        return super().fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> Any:
        self.calls.append("relationships")
        return super().fetch_relationships(uen)


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


class AddressMismatchIdp(MockIdpProvider):
    def __init__(self) -> None:
        super().__init__(MockIdpScenario.ALL_FIELDS_MATCH)

    def process(self, document: Any) -> Any:
        result = super().process(document)
        return result.model_copy(
            update={
                "fields": [
                    field.model_copy(update={"value": "99 OTHER ROAD, 999999, SG"})
                    if field.field_key == DocumentFieldKey.REGISTERED_ADDRESS
                    else field
                    for field in result.fields
                ]
            }
        )


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
        "GOLDTIER_SEARCH",
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


def test_coi_missing_address_remains_registry_only_and_completes() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)

    completed = zero.attach_document(
        case_id=created.case_id,
        display_name="coi-without-address.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.MISSING_FIELD),
    )

    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert completed.status == "COMPLETED"
    assert not any(
        item.blocker_code == "DOCUMENT_REQUIRED_FIELD_MISSING"
        for item in completed.active_exceptions
    )
    assert reconciliation is not None and reconciliation.status == "MATCHED"
    address = next(
        item for item in reconciliation.fields if item.field_name == "registered_address"
    )
    assert address.outcome == ReconciliationOutcome.REGISTRY_ONLY
    assert address.document_required is False
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_coi_supplied_mismatching_address_remains_reviewable() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)

    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="coi-with-mismatching-address.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=AddressMismatchIdp(),
    )

    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert paused.status == "WAITING_FOR_REVIEW"
    assert any(item.blocker_code == "DOCUMENT_SOURCE_CONFLICT" for item in paused.active_exceptions)
    assert reconciliation is not None
    address = next(
        item for item in reconciliation.fields if item.field_name == "registered_address"
    )
    assert address.outcome == ReconciliationOutcome.CONFLICT
    assert address.document_required is False
    assert target.calls == ["search"]


def test_legacy_document_profile_still_requires_registered_address() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="legacy-corporate-profile.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=MockIdpProvider(MockIdpScenario.MISSING_FIELD),
    )
    documents._repository.save(  # noqa: SLF001 - persisted legacy compatibility fixture
        document.model_copy(update={"profile": DocumentProfile.PROVISIONAL_CORPORATE})
    )

    paused = zero.start(case_id=created.case_id)

    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert paused.status == "WAITING_FOR_REVIEW"
    assert any(
        item.blocker_code == "DOCUMENT_REQUIRED_FIELD_MISSING"
        for item in paused.active_exceptions
    )
    assert reconciliation is not None
    address = next(
        item for item in reconciliation.fields if item.field_name == "registered_address"
    )
    assert address.outcome == ReconciliationOutcome.MISSING_IN_SOURCE
    assert address.document_required is True
    assert target.calls == ["search"]


def test_registry_complete_restart_runs_search_before_document() -> None:
    _, zero, documents, target, _ = build_system()
    case = zero._cases.create_staged_case("202400001A")  # noqa: SLF001 - restart fixture
    zero._clm._create_record(case)  # noqa: SLF001 - pre-Search durable fixture
    documents.create_document(
        case_id=case.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    now = datetime.now(UTC)
    zero.automation_repository.save(
        ZeroTouchAutomationRecord(
            case_id=case.case_id,
            automation_id=uuid4(),
            ownership_provider_binding_id=(
                zero._ownership_provider_bindings.default_binding_id  # noqa: SLF001
            ),
            status=AutomationStatus.RUNNING,
            current_stage=AutomationStage.GOLDTIER_SEARCH,
            completed_stages=(AutomationStage.REGISTRY,),
            started_at=now,
            created_at=now,
            updated_at=now,
        ),
        expected_version=None,
    )

    resumed = zero.start(case_id=case.case_id)

    assert resumed.completed_stages[:3] == (
        AutomationStage.REGISTRY,
        AutomationStage.GOLDTIER_SEARCH,
        AutomationStage.DOCUMENT,
    )
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_case_bound_high_mock_risk_can_pause_readiness_without_compliance_decision() -> None:
    client, zero, _, target, _ = build_system()

    def high_risk(case_id: UUID) -> OnboardingIntelligenceRecord:
        return OnboardingIntelligenceRecord(
            case_id=case_id,
            version=1,
            input_fingerprint="sha256:" + "b" * 64,
            policy_catalogue_version=1,
            mock_risk=MockRiskAssessment(
                score=80,
                band=MockRiskBand.HIGH,
                signal_assessments={
                    "entity_resolution": "40",
                    "document": "20",
                    "ownership": "20",
                },
                reason_codes=("SYNTHETIC_ADVERSE_EVIDENCE",),
                not_assessed_signals=frozenset({"pep", "sanctions", "adverse_media"}),
                blocks_readiness=True,
            ),
            evaluated_at=datetime(2026, 9, 23, tzinfo=UTC),
        )

    zero._intelligence_evaluator = high_risk  # noqa: SLF001 - bounded injected seam
    result = start_demo(client, "STRAIGHT_THROUGH")

    assert result["status"] == "WAITING_FOR_REVIEW"
    assert result["current_stage"] == "READINESS"
    assert result["active_exceptions"][0]["exception_type"] == ("MOCK_RISK_REVIEW_REQUIRED")
    assert result["active_exceptions"][0]["available_actions"] == []
    assert target.calls == ["search"]


def test_cache_hit_journey_preserves_target_order_and_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = RecordingMockAcra()
    target = RecordingMockGoldTier()
    monkeypatch.setattr(composition, "MockAcraConnector", lambda: registry)
    monkeypatch.setattr(composition, "MockGoldTierConnector", lambda **_: target)
    client = TestClient(
        create_app(
            Settings(
                _env_file=None,
                app_env="test",
                demo_controls_enabled=True,
                registry_cache_mode="mock",
                registry_cache_freshness_seconds=7_776_000,
            )
        )
    )

    first = start_demo(client, "STRAIGHT_THROUGH")
    second = start_demo(client, "STRAIGHT_THROUGH")

    assert first["status"] == second["status"] == "COMPLETED"
    assert registry.calls == ["entity", "officers", "ownership", "relationships"]
    assert target.calls == [
        "search",
        "shell",
        "policy",
        "amend",
        "search",
        "shell",
        "policy",
        "amend",
    ]


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
    expected_code = (
        "DEMO_CONTROLS_DISABLED"
        if path
        in {
            "/api/onboarding/mock-scenarios",
            "/api/demo/clm/zero-touch/cases",
        }
        else "CASE_NOT_FOUND"
    )
    assert response.json()["detail"]["code"] == expected_code


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
    assert target.calls == ["search"]


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
    assert target.calls == ["search"]


def test_existing_party_skips_shell_and_continues_to_completion() -> None:
    client, _, _, target, _ = build_system()
    result = start_demo(client, "EXISTING_PARTY")
    assert result["status"] == "COMPLETED"
    assert result["active_exceptions"] == []
    assert target.calls == ["search", "amend"]


def test_provider_and_target_failures_are_technical_not_business_review() -> None:
    client, _, _, target, _ = build_system()
    provider_failure = start_demo(client, "TECHNICAL_FAILURE")
    assert provider_failure["status"] == "TECHNICAL_FAILURE"
    assert provider_failure["active_exceptions"] == []
    assert provider_failure["technical_failure"]["code"] == "IDP_PROCESSING_FAILED"
    assert target.calls == ["search"]

    client, _, _, target, _ = build_system()
    target_failure = start_demo(client, "TARGET_FAILURE")
    assert target_failure["status"] == "TECHNICAL_FAILURE"
    assert target_failure["active_exceptions"] == []
    assert target_failure["technical_failure"]["code"] == "GT_POLICY_VALIDATION_FAILED"
    assert target.calls == ["search", "shell", "policy"]


def test_duplicate_and_concurrent_start_do_not_repeat_completed_work() -> None:
    client, zero, documents, target, demo = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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


def test_low_confidence_conflict_is_one_unverifiable_review_checkpoint() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    result = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MultipleBlockerIdp(),
        ownership_provider=MockOwnershipProvider(),
    )
    assert result.status == "WAITING_FOR_REVIEW"
    assert result.active_exceptions[0].blocker_codes == ("DOCUMENT_LOW_CONFIDENCE",)
    assert result.active_exceptions[0].available_actions == ()
    assert target.calls == ["search"]


def test_low_confidence_conflict_rejects_value_selection() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MultipleBlockerIdp(),
        ownership_provider=MockOwnershipProvider(),
    )
    first = paused.active_exceptions[0]
    with pytest.raises(ZeroTouchRequestError) as caught:
        zero.resolve_exception(
            case_id=created.case_id,
            exception_id=first.exception_id,
            action=ExceptionResolutionAction.KEEP_REGISTRY_VALUE,
            expected_automation_version=paused.version,
            evidence_version=first.evidence_version,
        )
    assert caught.value.code == "ZERO_TOUCH_RESOLUTION_NOT_ALLOWED"
    current = zero.get(case_id=created.case_id)
    assert current is not None and current.status == "WAITING_FOR_REVIEW"
    assert current.metrics.human_interventions == 0
    assert target.calls == ["search"]


def test_partial_review_stays_waiting_then_safe_correction_resumes_once() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ownership_provider=MockOwnershipProvider(),
    )
    document = documents.list_documents(case_id=created.case_id)[0]
    original_name = next(
        item.original_extracted_value
        for item in document.fields
        if item.field_key == DocumentFieldKey.LEGAL_NAME
    )

    zero.review_document_field(
        case_id=created.case_id,
        document_id=document.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.CORRECTED,
        corrected_value="MERLION CIRCULAR LABS PTE. LTD.",
    )
    partial = zero.get(case_id=created.case_id)
    assert partial is not None
    assert partial.status == "WAITING_FOR_REVIEW"
    assert {item.blocker_code for item in partial.active_exceptions} == {"DOCUMENT_REVIEW_REQUIRED"}
    assert partial.version > paused.version
    assert target.calls == ["search"]

    for key in (
        DocumentFieldKey.REGISTRATION_NUMBER,
        DocumentFieldKey.REGISTERED_ADDRESS,
        DocumentFieldKey.COUNTRY_OF_INCORPORATION,
    ):
        zero.review_document_field(
            case_id=created.case_id,
            document_id=document.document_id,
            field_key=key,
            decision=ReviewDecision.ACCEPTED,
        )

    completed = zero.get(case_id=created.case_id)
    reviewed = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert completed is not None and completed.status == "COMPLETED"
    assert reviewed is not None
    legal_name = next(
        item for item in reviewed.fields if item.field_key == DocumentFieldKey.LEGAL_NAME
    )
    assert legal_name.original_extracted_value == original_name
    assert legal_name.reviewed_value == "MERLION CIRCULAR LABS PTE. LTD."
    assert target.calls == ["search", "shell", "policy", "amend"]

    zero.review_document_field(
        case_id=created.case_id,
        document_id=document.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.CORRECTED,
        corrected_value="MERLION CIRCULAR LABS PTE. LTD.",
    )
    assert zero.get(case_id=created.case_id).version == completed.version  # type: ignore[union-attr]
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_failed_replacement_returns_to_targeted_intake_and_resumes_once() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    zero.attach_document(
        case_id=created.case_id,
        display_name="review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ownership_provider=MockOwnershipProvider(),
    )
    current = documents.list_documents(case_id=created.case_id)[0]

    with pytest.raises(ZeroTouchInfrastructureError) as exc_info:
        zero.replace_document(
            case_id=created.case_id,
            document_id=current.document_id,
            expected_document_event_count=len(current.events),
            display_name="failed-replacement.pdf",
            content_type="application/pdf",
            content=PDF,
            idp_provider=MockIdpProvider(MockIdpScenario.PROCESSOR_FAILURE),
        )

    assert exc_info.value.code == "IDP_PROCESSING_FAILED"
    recovered = zero.get(case_id=created.case_id)
    current_documents = [
        item
        for item in documents.list_documents(case_id=created.case_id)
        if item.is_current_evidence
    ]
    assert recovered is not None
    assert recovered.status == "PENDING_INPUTS"
    assert recovered.current_stage == "DOCUMENT"
    assert recovered.active_exceptions == []
    assert recovered.events[-1].event_type == "DOCUMENT_REUPLOAD_REQUIRED"
    assert len(current_documents) == 1 and current_documents[0].state == "FAILED"
    assert target.calls == ["search"]

    retried = zero.retry_intake_document(
        case_id=created.case_id,
        failed_document_id=current_documents[0].document_id,
        display_name="retry.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert retried.is_current_evidence
    completed = zero.start(case_id=created.case_id)
    assert completed.status == "COMPLETED"
    assert target.calls == ["search", "shell", "policy", "amend"]
    assert zero.start(case_id=created.case_id).version == completed.version
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_replacement_repository_failure_does_not_enter_reupload_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ownership_provider=MockOwnershipProvider(),
    )
    current = documents.list_documents(case_id=created.case_id)[0]

    def reject_save(**_: object) -> object:
        raise DocumentProcessingInfrastructureError(
            case_id=created.case_id,
            document_id=current.document_id,
            correlation_id=current.correlation_id,
            code="DOCUMENT_PERSISTENCE_FAILED",
            message="Document evidence could not be saved.",
        )

    monkeypatch.setattr(zero._documents, "replace_document", reject_save)  # noqa: SLF001
    with pytest.raises(ZeroTouchInfrastructureError) as caught:
        zero.replace_document(
            case_id=created.case_id,
            document_id=current.document_id,
            expected_document_event_count=len(current.events),
            display_name="replacement.pdf",
            content_type="application/pdf",
            content=PDF,
        )

    assert caught.value.code == "DOCUMENT_PERSISTENCE_FAILED"
    unchanged = zero.get(case_id=created.case_id)
    assert unchanged is not None
    assert unchanged.version == paused.version
    assert unchanged.status == "WAITING_FOR_REVIEW"
    assert unchanged.current_stage == "DOCUMENT"
    assert unchanged.active_exceptions == paused.active_exceptions
    assert target.calls == ["search"]
    assert zero.start(case_id=created.case_id).version == paused.version
    assert target.calls == ["search"]


def test_in_lock_reauthorization_failure_prevents_review_mutation() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    zero.attach_document(
        case_id=created.case_id,
        display_name="review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ownership_provider=MockOwnershipProvider(),
    )
    document = documents.list_documents(case_id=created.case_id)[0]
    automation = zero.get(case_id=created.case_id)
    assert automation is not None

    def deny() -> None:
        raise PermissionError("revoked")

    with pytest.raises(PermissionError):
        zero.review_document_field(
            case_id=created.case_id,
            document_id=document.document_id,
            field_key=DocumentFieldKey.LEGAL_NAME,
            decision=ReviewDecision.ACCEPTED,
            reauthorize=deny,
        )

    unchanged_document = documents.get_document(
        case_id=created.case_id, document_id=document.document_id
    )
    unchanged_automation = zero.get(case_id=created.case_id)
    assert unchanged_document is not None and unchanged_automation is not None
    assert len(unchanged_document.events) == len(document.events)
    assert unchanged_automation.version == automation.version
    assert target.calls == ["search"]


def test_explicit_resume_repairs_interrupted_review_checkpoint_without_replay() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
        ownership_provider=MockOwnershipProvider(),
    )
    document = documents.list_documents(case_id=created.case_id)[0]
    for field in document.fields:
        documents.review_field(
            case_id=created.case_id,
            document_id=document.document_id,
            field_key=field.field_key,
            decision=(
                ReviewDecision.CORRECTED
                if field.field_key == DocumentFieldKey.LEGAL_NAME
                else ReviewDecision.ACCEPTED
            ),
            corrected_value=(
                "MERLION CIRCULAR LABS PTE. LTD."
                if field.field_key == DocumentFieldKey.LEGAL_NAME
                else None
            ),
        )

    unchanged = zero.start(case_id=created.case_id)
    assert unchanged.version == paused.version
    assert unchanged.status == "WAITING_FOR_REVIEW"
    repaired = zero.start(
        case_id=created.case_id,
        refresh_document_checkpoint=True,
    )
    assert repaired.status == "COMPLETED"
    assert target.calls == ["search", "shell", "policy", "amend"]
    repeated = zero.start(
        case_id=created.case_id,
        refresh_document_checkpoint=True,
    )
    assert repeated.version == repaired.version
    assert target.calls == ["search", "shell", "policy", "amend"]


def _prepare_final_document_review(
    zero: ZeroTouchOrchestrator,
    documents: DocumentProcessingService,
    *,
    uen: str = "202400001A",
    demo: Any | None = None,
) -> tuple[UUID, UUID, int]:
    created = zero.create_case(uen, team_id=TeamId.TEAM_A)
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    assert case is not None and case.entity is not None
    idp_provider = MockIdpProvider(MockIdpScenario.FIELD_MISMATCH)
    if demo is not None:
        demo.register(created.case_id, ZeroTouchDemoScenario.DOCUMENT_DISCREPANCY)
        idp_provider = demo.idp_provider_for(created.case_id, case.entity)
    zero.attach_document(
        case_id=created.case_id,
        display_name="review.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=idp_provider,
        ownership_provider=MockOwnershipProvider(),
    )
    document = documents.list_documents(case_id=created.case_id)[0]
    for key in (
        DocumentFieldKey.LEGAL_NAME,
        DocumentFieldKey.REGISTRATION_NUMBER,
        DocumentFieldKey.REGISTERED_ADDRESS,
    ):
        zero.review_document_field(
            case_id=created.case_id,
            document_id=document.document_id,
            field_key=key,
            decision=(
                ReviewDecision.CORRECTED
                if key == DocumentFieldKey.LEGAL_NAME
                else ReviewDecision.ACCEPTED
            ),
            corrected_value=(
                case.entity.legal_name if key == DocumentFieldKey.LEGAL_NAME else None
            ),
        )
    current = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert current is not None
    return created.case_id, document.document_id, len(current.events)


def _install_ownership_counter(
    monkeypatch: pytest.MonkeyPatch, zero: ZeroTouchOrchestrator
) -> dict[str, int]:
    calls = {"count": 0}
    original = zero._ownership.analyze  # noqa: SLF001

    def counted(**kwargs: object) -> object:
        calls["count"] += 1
        return original(**kwargs)

    monkeypatch.setattr(zero._ownership, "analyze", counted)  # noqa: SLF001
    return calls


def test_reconciliation_conflict_after_review_fails_closed_then_repeat_repairs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zero, documents, target, demo = build_system()
    case_id, document_id, event_count = _prepare_final_document_review(
        zero, documents, uen="202400005E", demo=demo
    )
    before = zero.get(case_id=case_id)
    assert before is not None
    blocker_ids = {item.exception_id for item in before.active_exceptions}
    reconciliation_calls = {"count": 0}
    original = zero._reconciliation.reconcile_current  # noqa: SLF001

    def reject_once(*, case_id: UUID) -> object:
        reconciliation_calls["count"] += 1
        raise ReconciliationRequestError(
            code="RECONCILIATION_CONFLICT",
            message="Reconciliation changed during this operation.",
        )

    monkeypatch.setattr(zero._reconciliation, "reconcile_current", reject_once)  # noqa: SLF001
    ownership_calls = _install_ownership_counter(monkeypatch, zero)

    with pytest.raises(ZeroTouchRequestError) as caught:
        zero.review_document_field(
            case_id=case_id,
            document_id=document_id,
            field_key=DocumentFieldKey.COUNTRY_OF_INCORPORATION,
            decision=ReviewDecision.ACCEPTED,
        )

    assert caught.value.code == "RECONCILIATION_CONFLICT"
    failed = zero.get(case_id=case_id)
    assert failed is not None
    assert failed.version == before.version
    assert {item.exception_id for item in failed.active_exceptions} == blocker_ids
    assert reconciliation_calls["count"] == 1
    assert ownership_calls["count"] == 0
    assert target.calls == ["search"]
    reviewed = documents.get_document(case_id=case_id, document_id=document_id)
    assert reviewed is not None and len(reviewed.events) > event_count
    durable_event_count = len(reviewed.events)

    monkeypatch.setattr(zero._reconciliation, "reconcile_current", original)  # noqa: SLF001
    zero.review_document_field(
        case_id=case_id,
        document_id=document_id,
        field_key=DocumentFieldKey.COUNTRY_OF_INCORPORATION,
        decision=ReviewDecision.ACCEPTED,
    )

    completed = zero.get(case_id=case_id)
    repeated = documents.get_document(case_id=case_id, document_id=document_id)
    assert completed is not None
    assert completed.status == "COMPLETED"
    assert completed.current_stage == "COMPLETE"
    assert repeated is not None and len(repeated.events) == durable_event_count
    assert ownership_calls["count"] == 1
    assert target.calls == ["search", "amend"]


def test_reconciliation_infrastructure_failure_after_review_resume_repairs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zero, documents, target, _ = build_system()
    case_id, document_id, _ = _prepare_final_document_review(zero, documents)
    before = zero.get(case_id=case_id)
    assert before is not None
    blocker_ids = {item.exception_id for item in before.active_exceptions}
    reconciliation_calls = {"count": 0}
    original = zero._reconciliation.reconcile_current  # noqa: SLF001

    def fail_once(*, case_id: UUID) -> object:
        reconciliation_calls["count"] += 1
        raise ReconciliationInfrastructureError(
            code="RECONCILIATION_PERSISTENCE_FAILED",
            message="Reconciliation could not be saved.",
        )

    monkeypatch.setattr(zero._reconciliation, "reconcile_current", fail_once)  # noqa: SLF001
    ownership_calls = _install_ownership_counter(monkeypatch, zero)

    with pytest.raises(ZeroTouchInfrastructureError) as caught:
        zero.review_document_field(
            case_id=case_id,
            document_id=document_id,
            field_key=DocumentFieldKey.COUNTRY_OF_INCORPORATION,
            decision=ReviewDecision.ACCEPTED,
        )

    assert caught.value.code == "RECONCILIATION_PERSISTENCE_FAILED"
    failed = zero.get(case_id=case_id)
    assert failed is not None and failed.version == before.version
    assert {item.exception_id for item in failed.active_exceptions} == blocker_ids
    assert reconciliation_calls["count"] == 1
    assert ownership_calls["count"] == 0
    assert target.calls == ["search"]

    monkeypatch.setattr(zero._reconciliation, "reconcile_current", original)  # noqa: SLF001
    completed = zero.start(case_id=case_id, refresh_document_checkpoint=True)
    assert completed.status == "COMPLETED"
    assert ownership_calls["count"] == 1
    assert target.calls == ["search", "shell", "policy", "amend"]


@pytest.mark.parametrize("recovery", ["repeat", "resume"])
def test_automation_checkpoint_rejection_stops_progress_and_is_recoverable(
    monkeypatch: pytest.MonkeyPatch,
    recovery: str,
) -> None:
    _, zero, documents, target, _ = build_system()
    case_id, document_id, event_count = _prepare_final_document_review(zero, documents)
    before = zero.get(case_id=case_id)
    assert before is not None
    original_save = zero._repository.save  # noqa: SLF001
    rejected = {"count": 0}

    def reject_checkpoint(
        record: ZeroTouchAutomationRecord, *, expected_version: int | None
    ) -> ZeroTouchAutomationRecord:
        if record.events[-1].code == "DOCUMENT_REVIEW_UPDATED" and rejected["count"] == 0:
            rejected["count"] += 1
            raise ZeroTouchRepositoryConflictError
        return original_save(record, expected_version=expected_version)

    monkeypatch.setattr(zero._repository, "save", reject_checkpoint)  # noqa: SLF001
    ownership_calls = _install_ownership_counter(monkeypatch, zero)

    with pytest.raises(ZeroTouchRequestError) as caught:
        zero.review_document_field(
            case_id=case_id,
            document_id=document_id,
            field_key=DocumentFieldKey.COUNTRY_OF_INCORPORATION,
            decision=ReviewDecision.ACCEPTED,
        )

    assert caught.value.code == "ZERO_TOUCH_AUTOMATION_CONFLICT"
    failed = zero.get(case_id=case_id)
    assert failed is not None and failed.version == before.version
    assert failed.active_exceptions
    assert rejected["count"] == 1
    assert ownership_calls["count"] == 0
    assert target.calls == ["search"]
    durable = documents.get_document(case_id=case_id, document_id=document_id)
    assert durable is not None
    durable_event_count = len(durable.events)
    assert durable_event_count > event_count

    if recovery == "repeat":
        zero.review_document_field(
            case_id=case_id,
            document_id=document_id,
            field_key=DocumentFieldKey.COUNTRY_OF_INCORPORATION,
            decision=ReviewDecision.ACCEPTED,
        )
    else:
        zero.start(case_id=case_id, refresh_document_checkpoint=True)

    completed = zero.get(case_id=case_id)
    reviewed = documents.get_document(case_id=case_id, document_id=document_id)
    assert completed is not None and completed.status == "COMPLETED"
    assert reviewed is not None and len(reviewed.events) == durable_event_count
    assert ownership_calls["count"] == 1
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_reconciliation_failure_preserves_an_independent_document_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    conflict = zero.intake_document(
        case_id=created.case_id,
        display_name="conflict.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
    )
    zero.intake_document(
        case_id=created.case_id,
        display_name="low-confidence.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.LOW_CONFIDENCE),
    )
    paused = zero.start(
        case_id=created.case_id,
        ownership_provider=MockOwnershipProvider(),
        expected_document_count=2,
    )
    before_codes = {item.blocker_code for item in paused.active_exceptions}
    calls = {"count": 0}

    def reject(*, case_id: UUID) -> object:
        calls["count"] += 1
        raise ReconciliationRequestError(
            code="RECONCILIATION_CONFLICT",
            message="Reconciliation changed during this operation.",
        )

    monkeypatch.setattr(zero._reconciliation, "reconcile_current", reject)  # noqa: SLF001
    with pytest.raises(ZeroTouchRequestError):
        zero.review_document_field(
            case_id=created.case_id,
            document_id=conflict.document_id,
            field_key=DocumentFieldKey.LEGAL_NAME,
            decision=ReviewDecision.CORRECTED,
            corrected_value="MERLION CIRCULAR LABS PTE. LTD.",
        )

    failed = zero.get(case_id=created.case_id)
    assert failed is not None
    assert {item.blocker_code for item in failed.active_exceptions} == before_codes
    assert calls["count"] == 1
    assert target.calls == ["search"]


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
    assert target.calls == ["search"]


def test_invalid_pdf_does_not_publish_started_state() -> None:
    client, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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
    assert target.calls == ["search"]


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
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)

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
    assert (
        len(
            [
                event
                for event in current.events
                if event.event_type == "AUTOMATION_TECHNICAL_FAILURE"
            ]
        )
        == 1
    )
    assert "PRIVATE_ASSESSMENT_SENTINEL" not in current.model_dump_json()
    assert zero.start(case_id=created.case_id).version == current.version
    assert target.calls == ["search"]


def test_ownership_provider_binding_survives_document_resolution() -> None:
    _, zero, _, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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
    assert target.calls == ["search"]


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
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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
    assert target.calls == ["search"]


def test_P06_QG_005_REVIEWED_CONFLICT_LATER_DOCUMENT() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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
    assert target.calls == ["search"]


def test_P11_ONE_CURRENT_FIELD_DISCREPANCY_RETAINS_BOTH_CONFLICT_DOCUMENTS() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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

    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert len(paused.active_exceptions) == 1
    assert reconciliation is not None
    legal = next(
        item for item in reconciliation.open_discrepancies if item.field_name == "legal_name"
    )
    document_ids = [
        item.source_record_id for item in legal.observations if item.source_kind == "DOCUMENT_IDP"
    ]
    assert document_ids == [first.document_id, second.document_id]
    assert target.calls == ["search"]


def test_P06_QG_013_EQUAL_TIMESTAMPS_PRESERVE_INSERTION_ORDER_100_RUNS() -> None:
    _, zero, documents, target, _ = build_system()
    fixed_document_time = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
    documents._clock = lambda: fixed_document_time  # noqa: SLF001

    for index in range(100):
        created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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

        reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
        assert len(paused.active_exceptions) == 1
        assert reconciliation is not None
        legal = next(
            item for item in reconciliation.open_discrepancies if item.field_name == "legal_name"
        )
        assert [
            item.source_record_id
            for item in legal.observations
            if item.source_kind == "DOCUMENT_IDP"
        ] == [first.document_id, second.document_id]
        assert paused.status == "WAITING_FOR_REVIEW"

    assert target.calls == ["search"] * 100


def test_P06_QG_013_FORMER_FLAKY_TEST_IS_STABLE_100_RUNS() -> None:
    for _ in range(100):
        test_P11_ONE_CURRENT_FIELD_DISCREPANCY_RETAINS_BOTH_CONFLICT_DOCUMENTS()


def test_P06_QG_005_REVIEWED_CONFLICT_RESOLVED_BY_KEEP_REGISTRY() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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

    current = documents.get_document(case_id=created.case_id, document_id=reviewed.document_id)
    assert completed.status == "COMPLETED"
    assert current is not None
    retained = next(field for field in current.fields if field.field_key == mismatch.field_key)
    assert retained.original_extracted_value == original
    assert retained.reviewed_value == reviewed_value
    assert current.source_conflict_resolutions == []
    reconciliation = zero._reconciliation.get(case_id=created.case_id)  # noqa: SLF001
    assert reconciliation is not None
    assert reconciliation.discrepancies[0].decision is not None
    assert reconciliation.discrepancies[0].decision.action == "KEEP_REGISTRY_VALUE"
    assert completed.metrics.human_interventions == 1
    assert target.calls == ["search", "shell", "policy", "amend"]


def test_P06_QG_005_REVIEWED_LOW_CONFIDENCE_REMAINS_BLOCKED() -> None:
    _, zero, documents, target, _ = build_system()
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
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
    assert target.calls == ["search"]


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
        expected_status="COMPLETED",
        expected_code=None,
        expected_calls=["search", "amend"],
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
    assert target.calls == ["search", "search"]


def test_loop_guard_stops_safely_without_downstream_calls() -> None:
    client, _, _, target, _ = build_system(max_transitions=1)
    result = start_demo(client, "STRAIGHT_THROUGH")
    assert result["status"] == "TECHNICAL_FAILURE"
    assert result["technical_failure"]["code"] == "AUTOMATION_LOOP_GUARD"
    assert result["completed_stages"] == ["REGISTRY", "GOLDTIER_SEARCH", "DOCUMENT"]
    assert target.calls == ["search"]


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
