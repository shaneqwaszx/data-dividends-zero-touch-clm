"""Focused Phase 12 configuration, schema, and fail-closed tests."""

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

import pytest
from bson import BSON
from fastapi.testclient import TestClient
from s2_legacy_schema_fixtures import omit_session2_fields

import app.composition as composition
from app.composition import (
    build_clm_orchestration_service,
    build_document_processing_service,
    build_onboarding_service,
    build_ownership_analysis_service,
    build_reconciliation_service,
    build_zero_touch_demo_control,
    build_zero_touch_orchestrator,
)
from app.config import Settings
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.domain.clm import (
    ClmSubmissionSnapshot,
    EvidenceReference,
    GoldTierSubmissionPlan,
    ProvisionalUboSummary,
)
from app.domain.documents import (
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
)
from app.domain.onboarding_intelligence import (
    EntityIdentity,
    MockRiskAssessment,
    MockRiskBand,
    OnboardingIntelligenceRecord,
)
from app.domain.policy import (
    CasePolicySnapshot,
    EntityResolutionWeights,
    IntelligencePolicySnapshot,
    legacy_intelligence_policy_snapshot,
)
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    GoldTierProviderFailureStatus,
    GoldTierProviderMode,
    GoldTierRecoveryOrigin,
    GoldTierSearchResolution,
    ProviderVerifiedFailure,
    ProviderVerifiedRecovery,
)
from app.domain.zero_touch import (
    AUTOMATION_STAGE_ORDER_VERSION,
    LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
    ZeroTouchAutomationRecord,
    validate_automation_record,
)
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import (
    PersistenceConfigurationError,
    PersistenceDataInvalidError,
    PersistenceSchemaUnsupportedError,
)
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoClmOrchestrationRepository,
    MongoDemoScenarioRepository,
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOnboardingIntelligenceRepository,
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)
from app.services.onboarding import OnboardingService
from app.services.onboarding_intelligence import OnboardingIntelligenceService
from app.services.onboarding_intelligence_repository import (
    InMemoryOnboardingIntelligenceRepository,
    OnboardingIntelligenceRepositoryConflictError,
)
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository

TEXT_PROFILE = """Legal Name: MERLION CIRCULAR LABS PTE. LTD.
UEN: 202400001A
Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG
Country: SG
"""


def intelligence_record(case_id: UUID, *, version: int = 1) -> OnboardingIntelligenceRecord:
    return OnboardingIntelligenceRecord(
        case_id=case_id,
        version=version,
        input_fingerprint="sha256:" + "a" * 64,
        policy_catalogue_version=1,
        mock_risk=MockRiskAssessment(
            score=15,
            band=MockRiskBand.LOW,
            signal_assessments={
                "entity_resolution": "0",
                "document": "15",
                "ownership": "NOT_ASSESSED",
            },
            reason_codes=("DOCUMENT_EXCEPTION_COUNT_AVAILABLE",),
            not_assessed_signals=frozenset({"ownership"}),
        ),
        evaluated_at=datetime(2026, 9, 23, tzinfo=UTC),
    )


def intelligence_case_policy() -> CasePolicySnapshot:
    return CasePolicySnapshot(
        snapshot_label="TEST_INTELLIGENCE_POLICY_V1",
        catalogue_version=1,
        idp_review_confidence_threshold="0.85",
        ubo_threshold_percent="25.000000",
        intelligence=legacy_intelligence_policy_snapshot(),
        bound_at=datetime(2026, 9, 23, tzinfo=UTC),
    )


def intelligence_onboarding() -> OnboardingService:
    return build_onboarding_service(
        settings=Settings(_env_file=None),
        policy_snapshot_provider=intelligence_case_policy,
    )


def test_intelligence_repositories_enforce_create_update_delete_and_no_resurrection() -> None:
    case_id = uuid4()
    memory = InMemoryOnboardingIntelligenceRepository()
    created = memory.save(intelligence_record(case_id), expected_version=None)
    assert created.version == 1
    with pytest.raises(OnboardingIntelligenceRepositoryConflictError):
        memory.save(intelligence_record(case_id), expected_version=None)
    updated = memory.save(intelligence_record(case_id, version=2), expected_version=1)
    assert updated.version == 2
    memory.delete_for_case(case_id)
    assert memory.get_for_case(case_id) is None

    store = MemoryEnvelopeStore()
    onboarding = intelligence_onboarding()
    case = onboarding.create_staged_case("202400001A")
    MongoOnboardingCaseRepository(store).create(case)  # type: ignore[arg-type]
    repository = MongoOnboardingIntelligenceRepository(store)  # type: ignore[arg-type]
    assert repository.save(intelligence_record(case.case_id), expected_version=None).version == 1
    store.records.pop(case.case_id)
    with pytest.raises(OnboardingIntelligenceRepositoryConflictError):
        repository.save(intelligence_record(case.case_id, version=2), expected_version=1)


class MemoryEnvelopeStore:
    """Exercise Mongo adapters without pretending to be the genuine-Mongo gate."""

    def __init__(self) -> None:
        self.records: dict[object, DurableCaseSnapshot] = {}
        self.transaction_lock = RLock()

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self.transaction_lock:
            yield

    def create(self, snapshot: DurableCaseSnapshot) -> DurableCaseSnapshot:
        if snapshot.case_id in self.records:
            raise AssertionError("duplicate case")
        self.records[snapshot.case_id] = snapshot.model_copy(deep=True)
        return snapshot.model_copy(deep=True)

    def get(self, case_id: object) -> DurableCaseSnapshot | None:
        snapshot = self.records.get(case_id)
        return snapshot.model_copy(deep=True) if snapshot is not None else None

    def list(self) -> list[DurableCaseSnapshot]:
        return sorted(
            (item.model_copy(deep=True) for item in self.records.values()),
            key=lambda item: (item.updated_at, str(item.case_id)),
            reverse=True,
        )

    def replace(
        self, snapshot: DurableCaseSnapshot, *, expected_revision: int
    ) -> DurableCaseSnapshot:
        current = self.records.get(snapshot.case_id)
        if current is None or current.revision != expected_revision:
            raise AssertionError("stale envelope")
        persisted = snapshot.model_copy(update={"revision": expected_revision + 1}, deep=True)
        self.records[snapshot.case_id] = persisted
        return persisted.model_copy(deep=True)

    def find_by_submission(self, submission_id: object) -> DurableCaseSnapshot | None:
        for snapshot in self.records.values():
            if any(
                item.submission_input.submission_id == submission_id
                for item in snapshot.target_executions
            ):
                return snapshot.model_copy(deep=True)
        return None

    def find_by_document(self, document_id: object) -> DurableCaseSnapshot | None:
        for snapshot in self.records.values():
            if any(item.document_id == document_id for item in snapshot.documents):
                return snapshot.model_copy(deep=True)
        return None


def _pending_automation_record(
    case_id: UUID, *, updated_at: datetime, version: int = 0
) -> ZeroTouchAutomationRecord:
    return ZeroTouchAutomationRecord(
        case_id=case_id,
        automation_id=uuid4(),
        version=version,
        ownership_provider_binding_id="a" * 32,
        status=AutomationStatus.PENDING_INPUTS,
        current_stage=AutomationStage.DOCUMENT,
        completed_stages=(AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH),
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_automation_repository_order_is_independent_of_envelope_order() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    envelope_newer_case = onboarding.create_staged_case("202400001A")
    automation_newer_case = onboarding.create_staged_case("202400002B")
    automation_older_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    automation_newer_at = datetime(2026, 1, 2, 3, 4, 6, tzinfo=UTC)
    envelope_older_at = datetime(2026, 1, 2, 4, 0, 0, tzinfo=UTC)
    envelope_newer_at = datetime(2026, 1, 2, 5, 0, 0, tzinfo=UTC)

    memory_repository = InMemoryZeroTouchAutomationRepository()
    memory_repository.save(
        _pending_automation_record(envelope_newer_case.case_id, updated_at=automation_older_at),
        expected_version=None,
    )
    memory_repository.save(
        _pending_automation_record(automation_newer_case.case_id, updated_at=automation_newer_at),
        expected_version=None,
    )

    store = MemoryEnvelopeStore()
    store.create(
        DurableCaseSnapshot(
            case_id=envelope_newer_case.case_id,
            revision=0,
            onboarding=envelope_newer_case,
            automation=_pending_automation_record(
                envelope_newer_case.case_id,
                updated_at=automation_older_at,
                version=1,
            ),
            created_at=envelope_newer_at,
            updated_at=envelope_newer_at,
        )
    )
    store.create(
        DurableCaseSnapshot(
            case_id=automation_newer_case.case_id,
            revision=0,
            onboarding=automation_newer_case,
            automation=_pending_automation_record(
                automation_newer_case.case_id,
                updated_at=automation_newer_at,
                version=1,
            ),
            created_at=envelope_older_at,
            updated_at=envelope_older_at,
        )
    )

    expected = [automation_newer_case.case_id, envelope_newer_case.case_id]
    assert [item.case_id for item in store.list()] == list(reversed(expected))
    assert [item.case_id for item in memory_repository.list_records()] == expected
    mongo_repository = MongoZeroTouchAutomationRepository(store)  # type: ignore[arg-type]
    assert [item.case_id for item in mongo_repository.list_records()] == expected

    automation_latest_at = datetime(2026, 1, 2, 6, 0, 0, tzinfo=UTC)
    memory_older = memory_repository.get_for_case(envelope_newer_case.case_id)
    assert memory_older is not None
    memory_repository.save(
        memory_older.model_copy(update={"updated_at": automation_latest_at}, deep=True),
        expected_version=memory_older.version,
    )
    mongo_older = mongo_repository.get_for_case(envelope_newer_case.case_id)
    assert mongo_older is not None
    mongo_repository.save(
        mongo_older.model_copy(update={"updated_at": automation_latest_at}, deep=True),
        expected_version=mongo_older.version,
    )

    updated_expected = [envelope_newer_case.case_id, automation_newer_case.case_id]
    assert [item.case_id for item in store.list()] == updated_expected
    assert [item.case_id for item in memory_repository.list_records()] == updated_expected
    assert [item.case_id for item in mongo_repository.list_records()] == updated_expected

    memory_result = memory_repository.list_records()
    mongo_result = mongo_repository.list_records()
    memory_result[0].metrics.human_interventions = 99
    mongo_result[0].metrics.human_interventions = 99
    memory_result.clear()
    mongo_result.clear()
    assert memory_repository.list_records()[0].metrics.human_interventions == 0
    assert mongo_repository.list_records()[0].metrics.human_interventions == 0


def test_automation_repository_equal_timestamp_order_matches_across_modes() -> None:
    lower_id = UUID("00000000-0000-0000-0000-000000000001")
    higher_id = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    tied_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    higher_case = onboarding.create_staged_case("202400001A").model_copy(
        update={"case_id": higher_id}, deep=True
    )
    lower_case = onboarding.create_staged_case("202400002B").model_copy(
        update={"case_id": lower_id}, deep=True
    )

    memory_repository = InMemoryZeroTouchAutomationRepository()
    store = MemoryEnvelopeStore()
    # Save the higher ID first: stable identity ordering, not save chronology, wins the tie.
    for case in (higher_case, lower_case):
        memory_repository.save(
            _pending_automation_record(case.case_id, updated_at=tied_at),
            expected_version=None,
        )
        store.create(
            DurableCaseSnapshot(
                case_id=case.case_id,
                revision=0,
                onboarding=case,
                automation=_pending_automation_record(case.case_id, updated_at=tied_at, version=1),
                created_at=tied_at,
                updated_at=tied_at,
            )
        )

    mongo_repository = MongoZeroTouchAutomationRepository(store)  # type: ignore[arg-type]
    expected = [higher_id, lower_id]
    for _ in range(2):
        assert [item.case_id for item in memory_repository.list_records()] == expected
        assert [item.case_id for item in mongo_repository.list_records()] == expected


class ConfirmingPersistenceTestOrchestrator(ZeroTouchOrchestrator):
    """Run the explicit confirmation step in legacy persistence journeys."""

    def _advance_locked(self, *, case_id: UUID) -> ZeroTouchAutomationRecord:
        record = super()._advance_locked(case_id=case_id)
        if not any(
            item.exception_type.value == "TARGET_CONFIRMATION_REQUIRED"
            for item in record.active_exceptions
        ):
            return record
        case = self._cases.get_case(case_id)  # noqa: SLF001
        clm_record = self._clm.get(case_id=case_id)  # noqa: SLF001
        assert case is not None and clm_record is not None
        return self.confirm_target_dispatch(
            case_id=case_id,
            actor_id="test-operator",
            expected_automation_version=record.version,
            expected_clm_version=clm_record.version,
            expected_case_event_count=len(case.events),
        )


def _durable_adapter_app(
    store: MemoryEnvelopeStore, *, require_confirmation: bool = False
) -> object:
    settings = Settings(_env_file=None, app_env="test")
    onboarding = build_onboarding_service(
        settings=settings,
        repository=MongoOnboardingCaseRepository(store),  # type: ignore[arg-type]
        target_execution_repository=MongoTargetExecutionRepository(store),  # type: ignore[arg-type]
    )
    documents = build_document_processing_service(
        onboarding,
        settings,
        repository=MongoDocumentProcessingRepository(store),  # type: ignore[arg-type]
    )
    ownership = build_ownership_analysis_service(
        onboarding,
        settings,
        repository=MongoOwnershipAnalysisRepository(store),  # type: ignore[arg-type]
    )
    reconciliation_repository = MongoReconciliationRepository(store)  # type: ignore[arg-type]
    reconciliation = build_reconciliation_service(
        onboarding,
        documents,
        repository=reconciliation_repository,
        unit_of_work=MongoReconciliationUnitOfWork(store),  # type: ignore[arg-type]
    )
    clm = build_clm_orchestration_service(
        onboarding,
        documents,
        ownership,
        reconciliation,
        repository=MongoClmOrchestrationRepository(store),  # type: ignore[arg-type]
    )
    zero_touch = build_zero_touch_orchestrator(
        onboarding,
        documents,
        ownership,
        clm,
        reconciliation,
        settings,
        repository=MongoZeroTouchAutomationRepository(store),  # type: ignore[arg-type]
        durable_provider_bindings=True,
    )
    if not require_confirmation:
        zero_touch.__class__ = ConfirmingPersistenceTestOrchestrator
    demo = build_zero_touch_demo_control(
        MongoDemoScenarioRepository(store)  # type: ignore[arg-type]
    )
    return create_app(
        settings,
        onboarding_service=onboarding,
        document_processing_service=documents,
        ownership_analysis_service=ownership,
        reconciliation_service=reconciliation,
        clm_orchestration_service=clm,
        zero_touch_orchestrator=zero_touch,
        zero_touch_demo_control=demo,
    )


def _install_counting_goldtier(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, int]:
    calls = {name: 0 for name in ("search", "shell", "policy", "amend")}

    class CountingGoldTier(MockGoldTierConnector):
        def search_party(self, request: object, metadata: object) -> object:
            calls["search"] += 1
            return super().search_party(request, metadata)  # type: ignore[arg-type]

        def create_shell_customer(self, request: object, metadata: object) -> object:
            calls["shell"] += 1
            return super().create_shell_customer(request, metadata)  # type: ignore[arg-type]

        def create_policy(self, request: object, metadata: object) -> object:
            calls["policy"] += 1
            return super().create_policy(request, metadata)  # type: ignore[arg-type]

        def amend_party(self, party_id: str, request: object, metadata: object) -> object:
            calls["amend"] += 1
            return super().amend_party(  # type: ignore[arg-type]
                party_id, request, metadata
            )

    monkeypatch.setattr(composition, "MockGoldTierConnector", CountingGoldTier)
    return calls


def _base_schema_v5_raw_without_early_search(
    codec: MongoCaseStore,
    snapshot: DurableCaseSnapshot,
) -> dict[str, object]:
    """Build the exact pre-Search stage shape while retaining strict storage fields."""

    raw = codec._encode(snapshot)  # noqa: SLF001 - compatibility fixture boundary
    raw_automation = raw["automation"]
    assert isinstance(raw_automation, dict)
    raw_automation.pop("stage_order_version")
    raw_automation["completed_stages"] = [
        stage
        for stage in raw_automation["completed_stages"]
        if stage != AutomationStage.GOLDTIER_SEARCH.value
    ]
    raw_automation["events"] = [
        event
        for event in raw_automation["events"]
        if not str(event["event_type"]).startswith("GOLDTIER_SEARCH_")
    ]
    raw_metrics = raw_automation["metrics"]
    assert isinstance(raw_metrics, dict)
    raw_metrics["automated_stages_completed"] = len(raw_automation["completed_stages"])
    raw_metrics["stage_durations_ms"].pop(AutomationStage.GOLDTIER_SEARCH.value, None)
    raw_clm = raw["clm"]
    assert isinstance(raw_clm, dict)
    raw_clm.pop("target_search_checkpoint")
    raw_clm["events"] = [
        event
        for event in raw_clm["events"]
        if not str(event["event_type"]).startswith("GOLDTIER_SEARCH_")
    ]
    return raw


def test_memory_mode_never_requires_mongo() -> None:
    bundle = build_persistence_bundle(
        Settings(_env_file=None, clm_persistence_mode="memory", mongo_uri=None)
    )
    assert bundle.mode == "memory"
    assert bundle.public_label == "Process-local"
    assert isinstance(bundle.intelligence, InMemoryOnboardingIntelligenceRepository)


def test_mongo_mode_without_uri_fails_closed() -> None:
    with pytest.raises(PersistenceConfigurationError):
        build_persistence_bundle(
            Settings(_env_file=None, clm_persistence_mode="mongo", mongo_uri=None)
        )


def test_schema_version_is_explicit_and_unknown_version_is_rejected() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    assert snapshot.schema_version == 10

    store = object.__new__(MongoCaseStore)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["schema_version"] = 11
    with pytest.raises(PersistenceSchemaUnsupportedError):
        store._decode(raw)  # noqa: SLF001 - direct corruption boundary test


def test_schema_v6_decodes_to_current_with_recovery_fields_absent() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=4,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    raw = snapshot.model_dump(mode="json")
    raw["schema_version"] = 6
    omit_session2_fields(raw)
    raw["onboarding"].pop("identity_corrections")
    raw["onboarding"].pop("initial_target_search_attempts")
    raw["onboarding"].pop("target_dispatch_confirmation")
    raw["onboarding"].pop("policy_snapshot_revision")
    raw["onboarding"].pop("policy_rebind_history")
    raw["_id"] = str(case.case_id)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.schema_version == 10
    assert decoded.revision == 4
    assert decoded.onboarding.identity_corrections == ()
    assert decoded.onboarding.initial_target_search_attempts == ()
    assert decoded.onboarding.target_dispatch_confirmation is None
    assert decoded.onboarding.policy_snapshot_revision == 1
    assert decoded.onboarding.policy_rebind_history == ()


def test_schema_v5_round_trip_preserves_registry_only_search_restart_checkpoint() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    automation = ZeroTouchAutomationRecord(
        case_id=case.case_id,
        automation_id=uuid4(),
        ownership_provider_binding_id="a" * 32,
        status=AutomationStatus.RUNNING,
        current_stage=AutomationStage.GOLDTIER_SEARCH,
        completed_stages=(AutomationStage.REGISTRY,),
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        automation=automation,
        created_at=now,
        updated_at=now,
    )
    codec = object.__new__(MongoCaseStore)

    decoded = codec._decode(codec._encode(snapshot))  # noqa: SLF001

    assert decoded.automation is not None
    assert decoded.automation.current_stage == AutomationStage.GOLDTIER_SEARCH
    assert decoded.automation.completed_stages == (AutomationStage.REGISTRY,)


@pytest.mark.parametrize(
    ("stage_order_version", "status", "current_stage", "completed_stages"),
    [
        (
            AUTOMATION_STAGE_ORDER_VERSION,
            AutomationStatus.PENDING_INPUTS,
            AutomationStage.DOCUMENT,
            [AutomationStage.REGISTRY.value],
        ),
        (
            LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
            AutomationStatus.PENDING_INPUTS,
            AutomationStage.DOCUMENT,
            [
                AutomationStage.REGISTRY.value,
                AutomationStage.GOLDTIER_SEARCH.value,
            ],
        ),
        (
            AUTOMATION_STAGE_ORDER_VERSION,
            AutomationStatus.COMPLETED,
            AutomationStage.COMPLETE,
            [
                AutomationStage.REGISTRY.value,
                AutomationStage.GOLDTIER_SEARCH.value,
            ],
        ),
    ],
)
def test_schema_v5_decode_rejects_explicit_automation_stage_order_tampering(
    stage_order_version: int,
    status: AutomationStatus,
    current_stage: AutomationStage,
    completed_stages: list[str],
) -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=7,
        onboarding=case,
        automation=_pending_automation_record(case.case_id, updated_at=now, version=3),
        created_at=now,
        updated_at=now,
    )
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(snapshot)  # noqa: SLF001 - exact persistence representation
    raw_automation = raw["automation"]
    assert isinstance(raw_automation, dict)
    raw_automation["stage_order_version"] = stage_order_version
    raw_automation["status"] = status.value
    raw_automation["current_stage"] = current_stage.value
    raw_automation["completed_stages"] = completed_stages

    with pytest.raises(PersistenceDataInvalidError):
        codec._decode(raw)  # noqa: SLF001 - direct corruption boundary test


def test_base_schema_v5_pending_record_decodes_with_explicit_legacy_stage_order() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=7,
        onboarding=case,
        automation=_pending_automation_record(case.case_id, updated_at=now, version=3),
        created_at=now,
        updated_at=now,
    )
    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(snapshot)  # noqa: SLF001 - exact persistence representation
    raw_automation = raw["automation"]
    assert isinstance(raw_automation, dict)
    raw_automation.pop("stage_order_version", None)
    raw_automation["completed_stages"] = [AutomationStage.REGISTRY.value]
    original = deepcopy(raw)

    decoded = codec._decode(raw)  # noqa: SLF001 - compatibility boundary

    assert decoded.automation is not None
    assert decoded.automation.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
    assert decoded.automation.status == AutomationStatus.PENDING_INPUTS
    assert decoded.automation.current_stage == AutomationStage.DOCUMENT
    assert decoded.automation.completed_stages == (AutomationStage.REGISTRY,)
    assert codec._encode(decoded)["automation"]["stage_order_version"] == (  # noqa: SLF001
        LEGACY_AUTOMATION_STAGE_ORDER_VERSION
    )
    assert raw == original
    assert AUTOMATION_STAGE_ORDER_VERSION > LEGACY_AUTOMATION_STAGE_ORDER_VERSION


def test_base_schema_v5_pending_restart_runs_search_before_later_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goldtier_calls = _install_counting_goldtier(monkeypatch)
    store = MemoryEnvelopeStore()
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        assert created.status_code == 201
        case_id = UUID(created.json()["case"]["case_id"])

    codec = object.__new__(MongoCaseStore)
    raw = codec._encode(store.records[case_id])  # noqa: SLF001
    raw_automation = raw["automation"]
    assert isinstance(raw_automation, dict)
    raw_automation.pop("stage_order_version")
    raw_automation["status"] = AutomationStatus.PENDING_INPUTS.value
    raw_automation["current_stage"] = AutomationStage.DOCUMENT.value
    raw_automation["completed_stages"] = [AutomationStage.REGISTRY.value]
    raw_automation["events"] = [
        event
        for event in raw_automation["events"]
        if not str(event["event_type"]).startswith("GOLDTIER_SEARCH_")
    ]
    raw_metrics = raw_automation["metrics"]
    assert isinstance(raw_metrics, dict)
    raw_metrics["automated_stages_completed"] = 1
    raw_metrics["stage_durations_ms"].pop(AutomationStage.GOLDTIER_SEARCH.value, None)
    raw_clm = raw["clm"]
    assert isinstance(raw_clm, dict)
    raw_clm.pop("target_search_checkpoint")
    raw_clm["events"] = [
        event
        for event in raw_clm["events"]
        if not str(event["event_type"]).startswith("GOLDTIER_SEARCH_")
    ]
    store.records[case_id] = codec._decode(raw)  # noqa: SLF001
    calls_before_restart = goldtier_calls.copy()

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        uploaded = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
            content=TEXT_PROFILE.encode(),
        )
        completed = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )

    assert uploaded.status_code == 201
    assert completed.status_code == 200
    assert completed.json()["status"] == AutomationStatus.COMPLETED.value
    assert goldtier_calls == {
        "search": calls_before_restart["search"] + 3,
        "shell": calls_before_restart["shell"] + 1,
        "policy": calls_before_restart["policy"] + 1,
        "amend": calls_before_restart["amend"] + 1,
    }
    persisted = store.records[case_id]
    assert persisted.automation is not None
    assert persisted.automation.stage_order_version == AUTOMATION_STAGE_ORDER_VERSION
    event_codes = [event.code for event in persisted.automation.events]
    event_types = [event.event_type for event in persisted.automation.events]
    assert event_codes.index("AUTOMATION_STAGE_ORDER_UPGRADED") < event_types.index(
        AutomationEventType.GOLDTIER_SEARCH_COMPLETED
    )


def test_base_schema_v5_review_resolution_rebases_before_target_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goldtier_calls = _install_counting_goldtier(monkeypatch)
    store = MemoryEnvelopeStore()
    mismatched_profile = TEXT_PROFILE.replace(
        "MERLION CIRCULAR LABS PTE. LTD.", "MERLION CIRCULAR LABS PTE. LIMITED"
    )
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        case_id = UUID(created.json()["case"]["case_id"])
        uploaded = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Mismatch.txt"},
            content=mismatched_profile.encode(),
        )
        paused = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
    assert uploaded.status_code == 201
    assert paused.status_code == 200
    assert paused.json()["status"] == AutomationStatus.WAITING_FOR_REVIEW.value

    codec = object.__new__(MongoCaseStore)
    raw = _base_schema_v5_raw_without_early_search(codec, store.records[case_id])
    decoded = codec._decode(raw)  # noqa: SLF001
    assert decoded.automation is not None
    assert decoded.automation.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
    validate_automation_record(decoded.automation)
    store.records[case_id] = decoded
    paused_body = paused.json()
    exception = paused_body["active_exceptions"][0]
    calls_before_restart = goldtier_calls.copy()

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        resumed = second.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/exceptions/"
                f"{exception['exception_id']}/resolve"
            ),
            json={
                "action": "KEEP_REGISTRY_VALUE",
                "expected_automation_version": paused_body["version"],
                "evidence_version": exception["evidence_version"],
            },
        )

    assert resumed.status_code == 200
    assert resumed.json()["status"] == AutomationStatus.COMPLETED.value
    assert goldtier_calls == {
        "search": calls_before_restart["search"] + 3,
        "shell": calls_before_restart["shell"] + 1,
        "policy": calls_before_restart["policy"] + 1,
        "amend": calls_before_restart["amend"] + 1,
    }
    persisted = store.records[case_id]
    assert persisted.automation is not None
    assert persisted.automation.stage_order_version == AUTOMATION_STAGE_ORDER_VERSION


def test_base_schema_v5_completed_record_remains_terminal_without_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goldtier_calls = _install_counting_goldtier(monkeypatch)
    store = MemoryEnvelopeStore()
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        case_id = UUID(created.json()["case"]["case_id"])
        first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
            content=TEXT_PROFILE.encode(),
        )
        completed = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
    assert completed.status_code == 200
    assert completed.json()["status"] == AutomationStatus.COMPLETED.value

    codec = object.__new__(MongoCaseStore)
    raw = _base_schema_v5_raw_without_early_search(codec, store.records[case_id])
    decoded = codec._decode(raw)  # noqa: SLF001
    assert decoded.automation is not None
    assert decoded.automation.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
    validate_automation_record(decoded.automation)
    expected_version = decoded.automation.version
    store.records[case_id] = decoded
    calls_before_restart = goldtier_calls.copy()

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        for _ in range(3):
            resumed = second.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
            assert resumed.status_code == 200
            assert resumed.json()["status"] == AutomationStatus.COMPLETED.value
            assert resumed.json()["version"] == expected_version

    assert goldtier_calls == calls_before_restart
    persisted = store.records[case_id]
    assert persisted.automation is not None
    assert persisted.automation.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
    assert all(
        event.event_type != AutomationEventType.GOLDTIER_SEARCH_COMPLETED
        for event in persisted.automation.events
    )


def _provider_bound_snapshot(
    *,
    plan_mode: GoldTierProviderMode,
    execution_mode: GoldTierProviderMode,
) -> DurableCaseSnapshot:
    settings = Settings(_env_file=None)
    onboarding = build_onboarding_service(settings=settings)
    documents = build_document_processing_service(onboarding, settings)
    ownership = build_ownership_analysis_service(onboarding, settings)
    clm = build_clm_orchestration_service(onboarding, documents, ownership)
    record = clm.create_case("202400001A")
    case = onboarding.get_case(record.case_id)
    assert case is not None
    target_input = onboarding.build_submission_input(
        case,
        provider_mode=execution_mode,
    )
    now = datetime.now(UTC)
    submission_snapshot = ClmSubmissionSnapshot(
        snapshot_id=uuid4(),
        target_input=target_input,
        document_references=(),
        ownership_reference=EvidenceReference(
            reference_id=uuid4(),
            version=1,
            status="ANALYZED",
            updated_at=now,
        ),
        provisional_ubo=ProvisionalUboSummary(candidate_count=0),
        created_at=now,
    )
    classification = "MOCK" if plan_mode == GoldTierProviderMode.MOCK else "SANDBOX_PARTIAL"
    bound_record = record.model_copy(
        update={
            "submission_plan": GoldTierSubmissionPlan(
                environment=plan_mode,
                provider_classification=classification,
            ),
            "submission_snapshot": submission_snapshot,
        },
        deep=True,
    )
    return DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=case,
        clm=bound_record,
        target_executions=(
            GoldTierExecutionLedgerEntry(
                submission_input=target_input,
                state=GoldTierExecutionLedgerState.IN_PROGRESS,
            ),
        ),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    "mode",
    [GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX],
)
def test_schema_v5_accepts_matching_plan_and_execution_provider(mode: GoldTierProviderMode) -> None:
    snapshot = _provider_bound_snapshot(plan_mode=mode, execution_mode=mode)

    decoded = object.__new__(MongoCaseStore)._decode(  # noqa: SLF001
        {**snapshot.model_dump(mode="json"), "_id": str(snapshot.case_id)}
    )

    assert decoded.clm is not None and decoded.clm.submission_snapshot is not None
    assert decoded.clm.submission_plan.environment == mode
    assert decoded.clm.submission_snapshot.target_input.provider_mode == mode


@pytest.mark.parametrize("version", [6, 7, 8])
def test_schema_v6_round_trips_provider_verified_amend_failure_without_completion(
    version: int,
) -> None:
    snapshot = _provider_bound_snapshot(
        plan_mode=GoldTierProviderMode.SANDBOX,
        execution_mode=GoldTierProviderMode.SANDBOX,
    )
    original = snapshot.target_executions[0]
    entity = original.submission_input.canonical_entity
    now = datetime.now(UTC)
    party_id = "RECOVERED-123"
    shell = ProviderVerifiedRecovery(
        origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        recovered_party_id=party_id,
        legal_name=entity.legal_name,
        registration_number=entity.registration_number,
        country_of_incorporation=entity.country_of_incorporation,
        actor_id="persistence-test",
        verified_at=now,
        candidate_count=1,
    )
    policy = ProviderVerifiedRecovery(
        origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        operation=GoldTierOperationMarker.POLICY,
        recovered_party_id=party_id,
        legal_name=entity.legal_name,
        registration_number=entity.registration_number,
        country_of_incorporation=entity.country_of_incorporation,
        actor_id="persistence-test",
        verified_at=now,
        candidate_count=1,
        provider_policy="Singapore",
        provider_policy_status="Requested",
    )
    failure = ProviderVerifiedFailure(
        provider_status=GoldTierProviderFailureStatus.PROVIDER_VALIDATION_FAILED,
        provider_status_evidence="Valdiation Failed",
        recovered_party_id=party_id,
        actor_id="persistence-test",
        verified_at=now,
    )
    retained = GoldTierExecutionLedgerEntry(
        submission_input=original.submission_input,
        state=GoldTierExecutionLedgerState.IN_PROGRESS,
        attempted_operations=(
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
            GoldTierOperationMarker.AMEND,
        ),
        completed_operations=(GoldTierOperationMarker.SEARCH,),
        resolved_operations=(
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
        ),
        provider_verified_recovery=shell,
        provider_verified_policy_recovery=policy,
        provider_verified_amend_failure=failure,
        search_resolution=GoldTierSearchResolution.NO_MATCH,
        resolved_party_id=party_id,
        shell_status="PROVIDER_VERIFIED_RECOVERY",
        policy_status="PROVIDER_VERIFIED_REQUESTED",
    )
    raw = snapshot.model_copy(
        update={"target_executions": (retained,)}, deep=True
    ).model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["schema_version"] = version
    omit_session2_fields(raw)
    if version == 6:
        for field in (
            "identity_corrections", "initial_target_search_attempts",
            "target_dispatch_confirmation", "policy_snapshot_revision", "policy_rebind_history",
        ):
            raw["onboarding"].pop(field)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    reloaded = decoded.target_executions[0]
    assert reloaded.provider_verified_amend_failure == failure
    assert GoldTierOperationMarker.AMEND not in reloaded.lifecycle_resolved_operations
    assert GoldTierOperationMarker.AMEND not in reloaded.definitively_completed_operations


@pytest.mark.parametrize(
    ("plan_mode", "execution_mode"),
    [
        (GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX),
        (GoldTierProviderMode.SANDBOX, GoldTierProviderMode.MOCK),
    ],
)
def test_schema_v5_rejects_contradictory_plan_and_execution_provider(
    plan_mode: GoldTierProviderMode,
    execution_mode: GoldTierProviderMode,
) -> None:
    with pytest.raises(ValueError, match="provider identity"):
        _provider_bound_snapshot(plan_mode=plan_mode, execution_mode=execution_mode)


@pytest.mark.parametrize(
    ("plan_mode", "contradictory_mode"),
    [
        (GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX),
        (GoldTierProviderMode.SANDBOX, GoldTierProviderMode.MOCK),
    ],
)
def test_schema_v5_decode_rejects_persisted_provider_contradiction(
    plan_mode: GoldTierProviderMode,
    contradictory_mode: GoldTierProviderMode,
) -> None:
    snapshot = _provider_bound_snapshot(plan_mode=plan_mode, execution_mode=plan_mode)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["clm"]["submission_snapshot"]["target_input"]["provider_mode"] = contradictory_mode.value
    raw["target_executions"][0]["submission_input"]["provider_mode"] = contradictory_mode.value

    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


def test_schema_v5_accepts_plan_without_submission_snapshot() -> None:
    snapshot = _provider_bound_snapshot(
        plan_mode=GoldTierProviderMode.SANDBOX,
        execution_mode=GoldTierProviderMode.SANDBOX,
    )
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["clm"]["submission_snapshot"] = None
    raw["target_executions"] = []

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.clm is not None
    assert decoded.clm.submission_plan.environment == GoldTierProviderMode.SANDBOX
    assert decoded.clm.submission_snapshot is None


def test_schema_v5_rejects_matching_input_with_contradictory_execution_provider() -> None:
    snapshot = _provider_bound_snapshot(
        plan_mode=GoldTierProviderMode.MOCK,
        execution_mode=GoldTierProviderMode.MOCK,
    )
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["target_executions"][0]["submission_input"]["provider_mode"] = "SANDBOX"

    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


def test_schema_v5_rejects_internally_contradictory_provider_plan() -> None:
    snapshot = _provider_bound_snapshot(
        plan_mode=GoldTierProviderMode.MOCK,
        execution_mode=GoldTierProviderMode.MOCK,
    )
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["clm"]["submission_plan"]["provider_classification"] = "SANDBOX_PARTIAL"

    with pytest.raises(PersistenceDataInvalidError):
        object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001


def test_schema_v2_read_receives_legacy_policy_snapshot_without_rewrite() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    current = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=4,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    raw = current.model_dump(mode="json")
    raw["schema_version"] = 2
    omit_session2_fields(raw)
    raw.pop("intelligence")
    raw["onboarding"].pop("policy_snapshot")
    raw["onboarding"].pop("registry_evidence_binding")
    raw["onboarding"].pop("initial_identity")
    raw["onboarding"].pop("initial_target_search")
    raw["onboarding"].pop("existing_target_state")
    raw["onboarding"].pop("identity_corrections")
    raw["onboarding"].pop("initial_target_search_attempts")
    raw["onboarding"].pop("target_dispatch_confirmation")
    raw["onboarding"].pop("policy_snapshot_revision")
    raw["onboarding"].pop("policy_rebind_history")
    raw["_id"] = str(case.case_id)
    original = deepcopy(raw)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.schema_version == 10
    assert decoded.onboarding.policy_snapshot.snapshot_label == "LEGACY_PHASE13_DEFAULTS_V1"
    assert decoded.onboarding.registry_evidence_binding is None
    assert str(decoded.onboarding.policy_snapshot.idp_review_confidence_threshold) == "0.85"
    assert raw == original


def test_schema_v3_read_has_absent_binding_without_rewrite() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    current = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=7,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    raw = current.model_dump(mode="json")
    raw["schema_version"] = 3
    omit_session2_fields(raw)
    raw.pop("intelligence")
    raw["onboarding"].pop("registry_evidence_binding")
    raw["onboarding"].pop("initial_identity")
    raw["onboarding"].pop("initial_target_search")
    raw["onboarding"].pop("existing_target_state")
    raw["onboarding"].pop("identity_corrections")
    raw["onboarding"].pop("initial_target_search_attempts")
    raw["onboarding"].pop("target_dispatch_confirmation")
    raw["onboarding"].pop("policy_snapshot_revision")
    raw["onboarding"].pop("policy_rebind_history")
    raw["_id"] = str(case.case_id)
    original = deepcopy(raw)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.schema_version == 10
    assert decoded.onboarding.registry_evidence_binding is None
    assert raw == original


def test_schema_v4_read_has_no_intelligence_record_and_is_not_rewritten() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    current = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=9,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    raw = current.model_dump(mode="json")
    raw["schema_version"] = 4
    omit_session2_fields(raw)
    raw.pop("intelligence")
    raw["onboarding"]["policy_snapshot"].pop("intelligence")
    raw["onboarding"].pop("initial_identity")
    raw["onboarding"].pop("initial_target_search")
    raw["onboarding"].pop("existing_target_state")
    raw["onboarding"].pop("identity_corrections")
    raw["onboarding"].pop("initial_target_search_attempts")
    raw["onboarding"].pop("target_dispatch_confirmation")
    raw["onboarding"].pop("policy_snapshot_revision")
    raw["onboarding"].pop("policy_rebind_history")
    raw["_id"] = str(case.case_id)
    original = deepcopy(raw)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.schema_version == 10
    assert decoded.intelligence is None
    assert decoded.onboarding.policy_snapshot.intelligence is None
    assert raw == original


def test_existing_schema_v5_reads_without_new_goldtier_preparation_fields() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    submission = onboarding.build_submission_input(
        case,
        provider_mode=GoldTierProviderMode.MOCK,
    )
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=10,
        onboarding=case,
        target_executions=(
            GoldTierExecutionLedgerEntry(
                submission_input=submission,
                state=GoldTierExecutionLedgerState.IN_PROGRESS,
            ),
        ),
        created_at=now,
        updated_at=now,
    )
    raw = snapshot.model_dump(mode="json")
    raw["onboarding"]["policy_snapshot"].pop("goldtier_target")
    target_input = raw["target_executions"][0]["submission_input"]
    for field in (
        "provider_mode",
        "policy_catalogue_version",
        "target_external_key",
        "target_policy",
    ):
        target_input.pop(field)
    raw["_id"] = str(case.case_id)
    original = deepcopy(raw)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.onboarding.policy_snapshot.goldtier_target is None
    assert decoded.target_executions[0].submission_input.provider_mode == "MOCK"
    assert decoded.target_executions[0].submission_input.target_policy is None
    assert raw == original


def test_schema_v5_intelligence_round_trip_is_strict_and_case_bound() -> None:
    onboarding = intelligence_onboarding()
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    record = OnboardingIntelligenceRecord(
        case_id=case.case_id,
        version=1,
        input_fingerprint="sha256:" + "a" * 64,
        policy_catalogue_version=case.policy_snapshot.catalogue_version,
        mock_risk=MockRiskAssessment(
            score=65,
            band=MockRiskBand.HIGH,
            signal_assessments={
                "entity_resolution": "35",
                "document": "30",
                "ownership": "NOT_ASSESSED",
            },
            reason_codes=("ENTITY_REVIEW_REQUIRED",),
            not_assessed_signals=frozenset({"ownership", "pep", "sanctions"}),
        ),
        evaluated_at=now,
    )
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=case,
        intelligence=record,
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)

    encoded = store._encode(snapshot)  # noqa: SLF001
    bson_round_trip = BSON(BSON.encode(encoded)).decode()
    decoded = store._decode(bson_round_trip)  # noqa: SLF001

    assert decoded == snapshot
    wrong_case = record.model_copy(update={"case_id": uuid4()})
    with pytest.raises(ValueError):
        DurableCaseSnapshot(
            case_id=case.case_id,
            revision=1,
            onboarding=case,
            intelligence=wrong_case,
            created_at=now,
            updated_at=now,
        )


@pytest.mark.parametrize("corruption", ["entity", "ubo", "risk"])
def test_schema_v5_rejects_semantically_contradictory_nested_intelligence(
    corruption: str,
) -> None:
    onboarding = intelligence_onboarding()
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=case,
        intelligence=intelligence_record(case.case_id),
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw = store._encode(snapshot)  # noqa: SLF001
    if corruption == "entity":
        raw["intelligence"]["entity_resolution"] = {
            "outcome": "NO_MATCH",
            "selected_candidate_id": "ghost",
            "source_reference": None,
            "candidates": [],
            "reason_codes": ["NO_CANDIDATES"],
            "model_version": "entity-resolution-linear-v1",
            "assistance_label": "ML_ASSISTED",
            "disclaimer": "NOT_IDENTITY_AUTHORITY",
        }
    elif corruption == "ubo":
        raw["intelligence"]["ubo_advice"] = [
            {
                "party_id": "",
                "probability": None,
                "label": "LIKELY_UBO",
                "authoritative_ownership_percent": "0",
                "reason_codes": ["CONSUMES_DETERMINISTIC_OWNERSHIP_RESULT"],
                "likely_threshold": "0.65",
                "unlikely_threshold": "0.35",
                "model_version": "ubo-advisory-linear-v1",
                "assistance_label": "ML_ASSISTED",
                "disclaimer": "NOT_LEGAL_UBO_DETERMINATION",
            }
        ]
    else:
        raw["intelligence"]["mock_risk"]["band"] = "HIGH"

    with pytest.raises(PersistenceDataInvalidError):
        store._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize(
    "corruption",
    [
        "catalogue_version",
        "missing_intelligence_policy",
        "entity_weights",
        "ubo_thresholds",
        "risk_thresholds",
        "risk_readiness_flag",
        "unknown_risk_limitation",
    ],
)
def test_schema_v5_rejects_intelligence_not_bound_to_immutable_case_policy(
    corruption: str,
) -> None:
    onboarding = intelligence_onboarding()
    case = onboarding.create_staged_case("202400001A")
    assert case.policy_snapshot.intelligence is not None
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=case,
        intelligence=intelligence_record(case.case_id),
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw = store._encode(snapshot)  # noqa: SLF001
    if corruption == "catalogue_version":
        raw["intelligence"]["policy_catalogue_version"] = 999
    elif corruption == "missing_intelligence_policy":
        raw["onboarding"]["policy_snapshot"]["intelligence"] = None
    elif corruption == "entity_weights":
        default = case.policy_snapshot.intelligence
        alternate = IntelligencePolicySnapshot(
            **default.model_dump(exclude={"entity_resolution_weights"}),
            entity_resolution_weights=EntityResolutionWeights(
                identifier="0.10",
                name="0.40",
                address="0.30",
                legal_form="0.10",
                incorporation_date="0.10",
            ),
        )
        raw["intelligence"]["entity_resolution"] = (
            OnboardingIntelligenceService()
            .resolve_entity(
                source=EntityIdentity(
                    candidate_id="source",
                    legal_name="Synthetic Entity",
                    registered_address="1 Synthetic Street",
                ),
                candidates=(
                    EntityIdentity(
                        candidate_id="candidate",
                        legal_name="Synthetic Entity",
                        registered_address="1 Synthetic Street",
                    ),
                ),
                policy=alternate,
            )
            .model_dump(mode="json")
        )
    elif corruption == "ubo_thresholds":
        raw["intelligence"]["ubo_advice"] = [
            {
                "party_id": "PERSON-1",
                "probability": "0.800000",
                "label": "LIKELY_UBO",
                "authoritative_ownership_percent": "40",
                "reason_codes": ["CONSUMES_DETERMINISTIC_OWNERSHIP_RESULT"],
                "likely_threshold": "0.70",
                "unlikely_threshold": "0.30",
                "model_version": "ubo-advisory-linear-v1",
                "assistance_label": "ML_ASSISTED",
                "disclaimer": "NOT_LEGAL_UBO_DETERMINATION",
            }
        ]
    elif corruption == "risk_thresholds":
        raw["intelligence"]["mock_risk"]["medium_threshold"] = 20
    elif corruption == "risk_readiness_flag":
        raw["intelligence"]["mock_risk"]["blocks_readiness"] = True
    else:
        raw["intelligence"]["mock_risk"]["not_assessed_signals"].append(
            "unexpected_external_signal"
        )

    with pytest.raises(PersistenceDataInvalidError):
        store._decode(raw)  # noqa: SLF001


@pytest.mark.parametrize(
    "mongo_id",
    [
        None,
        17,
        "not-a-uuid",
        "550E8400-E29B-41D4-A716-446655440000",
        str(uuid4()),
    ],
    ids=["missing", "non-string", "malformed", "non-canonical", "mismatch"],
)
def test_mongo_storage_identity_must_be_canonical_and_match_case_id(
    mongo_id: object,
) -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw = store._encode(snapshot)  # noqa: SLF001
    if mongo_id is None:
        raw.pop("_id")
    else:
        raw["_id"] = mongo_id

    with pytest.raises(PersistenceDataInvalidError):
        store._decode(raw)  # noqa: SLF001


def test_mongo_storage_identity_accepts_exact_canonical_match() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)

    assert store._decode(store._encode(snapshot)) == snapshot  # noqa: SLF001


@pytest.mark.parametrize(
    "interrupted_state",
    [DocumentProcessingState.UPLOADED, DocumentProcessingState.PROCESSING],
)
@pytest.mark.parametrize("legacy_stage_order", [False, True])
def test_interrupted_current_document_recovers_automation_to_targeted_retry(
    interrupted_state: DocumentProcessingState,
    legacy_stage_order: bool,
) -> None:
    store = MemoryEnvelopeStore()
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        assert created.status_code == 201
        case_id = UUID(created.json()["case"]["case_id"])

    snapshot = store.records[case_id]
    assert snapshot.automation is not None
    now = datetime.now(UTC)
    interrupted = DocumentProcessingRecord(
        case_id=case_id,
        document_id=uuid4(),
        correlation_id=uuid4(),
        display_name="Interrupted.txt",
        media_type="text/plain",
        size_bytes=16,
        profile=DocumentProfile.PROVISIONAL_CORPORATE,
        state=interrupted_state,
        created_at=now,
        updated_at=now,
    )
    running = snapshot.automation.model_copy(
        update={
            "stage_order_version": (
                LEGACY_AUTOMATION_STAGE_ORDER_VERSION
                if legacy_stage_order
                else AUTOMATION_STAGE_ORDER_VERSION
            ),
            "status": AutomationStatus.RUNNING,
            "current_stage": AutomationStage.DOCUMENT,
            "completed_stages": (
                (AutomationStage.REGISTRY,)
                if legacy_stage_order
                else (
                    AutomationStage.REGISTRY,
                    AutomationStage.GOLDTIER_SEARCH,
                )
            ),
            "started_at": now,
        },
        deep=True,
    )
    candidate = snapshot.model_copy(
        update={"documents": (interrupted,), "automation": running}, deep=True
    )

    codec = object.__new__(MongoCaseStore)
    recovered = codec._recover_interrupted(candidate)  # noqa: SLF001
    recovered_document = recovered.documents[0]
    assert recovered_document.state == DocumentProcessingState.FAILED
    assert recovered_document.error is not None
    assert recovered_document.error.code == "DOCUMENT_REUPLOAD_REQUIRED"
    assert recovered.automation is not None
    assert recovered.automation.status == AutomationStatus.PENDING_INPUTS
    assert recovered.automation.current_stage == AutomationStage.DOCUMENT
    assert recovered.automation.completed_stages == (
        (AutomationStage.REGISTRY,)
        if legacy_stage_order
        else (
            AutomationStage.REGISTRY,
            AutomationStage.GOLDTIER_SEARCH,
        )
    )
    assert recovered.automation.events[-1].event_type == (
        AutomationEventType.DOCUMENT_REUPLOAD_REQUIRED
    )
    assert recovered.automation.metrics.human_interventions == 0


def test_multiple_interrupted_documents_require_individual_targeted_retries() -> None:
    store = MemoryEnvelopeStore()
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        assert created.status_code == 201
        case_id = UUID(created.json()["case"]["case_id"])
        preserved_upload = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Preserved.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert preserved_upload.status_code == 201
        preserved_id = UUID(preserved_upload.json()["document_id"])

    snapshot = store.records[case_id]
    assert snapshot.automation is not None
    preserved_event_count = len(snapshot.documents[0].events)
    now = datetime.now(UTC)
    document_ids = (uuid4(), uuid4())
    interrupted_documents = tuple(
        DocumentProcessingRecord(
            case_id=case_id,
            document_id=document_id,
            correlation_id=uuid4(),
            display_name=f"Interrupted-{index}.txt",
            media_type="text/plain",
            size_bytes=16,
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            state=state,
            created_at=now,
            updated_at=now,
        )
        for index, (document_id, state) in enumerate(
            zip(
                document_ids,
                (
                    DocumentProcessingState.UPLOADED,
                    DocumentProcessingState.PROCESSING,
                ),
                strict=True,
            ),
            start=1,
        )
    )
    running = snapshot.automation.model_copy(
        update={
            "status": AutomationStatus.RUNNING,
            "current_stage": AutomationStage.DOCUMENT,
            "started_at": now,
        },
        deep=True,
    )
    candidate = snapshot.model_copy(
        update={
            "documents": (*snapshot.documents, *interrupted_documents),
            "automation": running,
        },
        deep=True,
    )
    codec = object.__new__(MongoCaseStore)
    store.records[case_id] = codec._recover_interrupted(candidate)  # noqa: SLF001

    headers = {"Content-Type": "text/plain", "X-Document-Name": "Retry.txt"}
    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        unrelated = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers=headers,
            content=TEXT_PROFILE.encode(),
        )
        assert unrelated.status_code == 409
        assert unrelated.json()["detail"]["code"] == ("ZERO_TOUCH_DOCUMENT_REUPLOAD_REQUIRED")

        first_retry = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents/{document_ids[0]}/retry",
            headers=headers,
            content=TEXT_PROFILE.encode(),
        )
        assert first_retry.status_code == 201
        still_blocked = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers=headers,
            content=TEXT_PROFILE.encode(),
        )
        assert still_blocked.status_code == 409

        second_retry = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents/{document_ids[1]}/retry",
            headers=headers,
            content=TEXT_PROFILE.encode(),
        )
        assert second_retry.status_code == 201
        documents = second.get(f"/api/onboarding/cases/{case_id}/documents")
        automation = second.get(f"/api/clm/zero-touch/cases/{case_id}")

    assert documents.status_code == automation.status_code == 200
    records = documents.json()
    assert len(records) == 5
    assert sum(item["superseded_by_document_id"] is not None for item in records) == 2
    assert sum(item["superseded_by_document_id"] is None for item in records) == 3
    preserved = next(item for item in records if item["document_id"] == str(preserved_id))
    assert preserved["superseded_by_document_id"] is None
    assert len(preserved["events"]) == preserved_event_count
    assert automation.json()["status"] == "PENDING_INPUTS"
    assert automation.json()["case"]["case_id"] == str(case_id)


def test_durable_dto_round_trip_preserves_controlled_identifiers_and_no_raw_bytes() -> None:
    onboarding = build_onboarding_service(settings=Settings(_env_file=None))
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    snapshot = DurableCaseSnapshot(
        case_id=case.case_id,
        revision=0,
        onboarding=case,
        created_at=now,
        updated_at=now,
    )
    store = object.__new__(MongoCaseStore)
    raw = store._encode(snapshot)  # noqa: SLF001 - persistence representation assertion
    decoded = store._decode(raw)  # noqa: SLF001

    assert decoded.case_id == case.case_id
    serialized = repr(raw).lower()
    assert "raw_bytes" not in serialized
    assert "full_text" not in serialized
    assert "mongo_uri" not in serialized

    tampered = store._encode(snapshot)  # noqa: SLF001
    onboarding_raw = tampered["onboarding"]
    assert isinstance(onboarding_raw, dict)
    onboarding_raw["unexpected"] = "not allowed"
    with pytest.raises(PersistenceDataInvalidError):
        store._decode(tampered)  # noqa: SLF001


def test_new_composition_reconstructs_pending_and_review_queue_from_adapters() -> None:
    store = MemoryEnvelopeStore()
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        completed = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        completed_id = completed.json()["case"]["case_id"]
        uploaded = first.post(
            f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
            content=TEXT_PROFILE.encode(),
        )
        done = first.post(
            f"/api/clm/zero-touch/cases/{completed_id}/intake/complete",
            json={"expected_document_count": 1},
        )
        assert uploaded.status_code == 201
        assert done.status_code == 200
        assert done.json()["status"] == "COMPLETED"

        pending = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        waiting = first.post(
            "/api/clm/zero-touch/cases",
            json={"uen": "UNKNOWN", "country_of_incorporation": "AU"},
        )
        assert pending.status_code == waiting.status_code == 201
        pending_id = pending.json()["case"]["case_id"]
        waiting_id = waiting.json()["case"]["case_id"]

    codec = object.__new__(MongoCaseStore)
    for snapshot in store.records.values():
        assert codec._decode(codec._encode(snapshot)) == snapshot  # noqa: SLF001

    completed_snapshot = store.records[UUID(completed_id)]
    assert completed_snapshot.automation is not None
    assert completed_snapshot.target_executions
    running = completed_snapshot.automation.model_copy(
        update={
            "status": AutomationStatus.RUNNING,
            "current_stage": AutomationStage.MOCK_GOLDTIER,
            "completed_stages": (
                AutomationStage.REGISTRY,
                AutomationStage.GOLDTIER_SEARCH,
                AutomationStage.DOCUMENT,
                AutomationStage.OWNERSHIP,
                AutomationStage.READINESS,
            ),
            "completed_at": None,
        },
        deep=True,
    )
    running.metrics.final_outcome = None
    running = ZeroTouchAutomationRecord.model_validate(running)
    original_entry = completed_snapshot.target_executions[0]
    uncertain = GoldTierExecutionLedgerEntry(
        submission_input=original_entry.submission_input,
        state=GoldTierExecutionLedgerState.IN_PROGRESS,
        attempted_operations=(GoldTierOperationMarker.SEARCH,),
    )
    interrupted = completed_snapshot.model_copy(
        update={"automation": running, "target_executions": (uncertain,)}, deep=True
    )
    recovered = codec._recover_interrupted(interrupted)  # noqa: SLF001
    assert recovered.automation is not None
    assert recovered.automation.status == AutomationStatus.RECOVERY_PENDING
    assert recovered.target_executions[0].state == GoldTierExecutionLedgerState.IN_PROGRESS

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        listed = second.get("/api/clm/zero-touch/cases")
        review = second.get("/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW")
        assert listed.status_code == review.status_code == 200
        assert {item["case_id"] for item in listed.json()} == {
            completed_id,
            pending_id,
            waiting_id,
        }
        assert [item["case_id"] for item in review.json()] == [waiting_id]
        reopened = second.get(f"/api/clm/zero-touch/cases/{completed_id}")
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "COMPLETED"


def test_registry_only_coi_address_round_trips_across_adapter_restart() -> None:
    store = MemoryEnvelopeStore()
    certificate_without_address = TEXT_PROFILE.replace(
        "Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG\n", ""
    )
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        case_id = created.json()["case"]["case_id"]
        uploaded = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Certificate.txt"},
            content=certificate_without_address.encode(),
        )
        completed = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )

        assert uploaded.status_code == 201
        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"
        address = next(
            item
            for item in completed.json()["reconciliation"]["fields"]
            if item["field_name"] == "registered_address"
        )
        assert address["outcome"] == "REGISTRY_ONLY"
        assert address["document_required"] is False

    case_uuid = UUID(case_id)
    snapshot = store.records[case_uuid]
    assert snapshot.reconciliation is not None
    persisted_address = next(
        item
        for item in snapshot.reconciliation.fields
        if item.field_name == "registered_address"
    )
    assert persisted_address.outcome == "REGISTRY_ONLY"
    assert persisted_address.document_required is False
    codec = object.__new__(MongoCaseStore)
    assert codec._decode(codec._encode(snapshot)) == snapshot  # noqa: SLF001

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        reopened = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "COMPLETED"
        reopened_address = next(
            item
            for item in reopened.json()["reconciliation"]["fields"]
            if item["field_name"] == "registered_address"
        )
        assert reopened_address["outcome"] == "REGISTRY_ONLY"
        assert reopened_address["document_required"] is False


def test_partial_document_review_round_trips_across_adapter_restart() -> None:
    store = MemoryEnvelopeStore()
    mismatched_profile = TEXT_PROFILE.replace(
        "MERLION CIRCULAR LABS PTE. LTD.", "MERLION CIRCULAR LABS PTE. LIMITED"
    ).replace("Country: SG", "Country: MY")
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        case_id = created.json()["case"]["case_id"]
        uploaded = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Mismatch.txt"},
            content=mismatched_profile.encode(),
        )
        paused = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
        reviewed = first.post(
            (f"/api/onboarding/cases/{case_id}/documents/{uploaded.json()['document_id']}/reviews"),
            json={
                "field_key": "legal_name",
                "decision": "CORRECTED",
                "corrected_value": "MERLION CIRCULAR LABS PTE. LTD.",
            },
        )
        after_review = first.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert paused.json()["status"] == "WAITING_FOR_REVIEW"
        assert reviewed.status_code == 200
        assert after_review.json()["status"] == "WAITING_FOR_REVIEW"
        expected_version = after_review.json()["version"]
        expected_events = reviewed.json()["events"]

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        restored = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        restored_document = second.get(
            f"/api/onboarding/cases/{case_id}/documents/{uploaded.json()['document_id']}"
        )

    assert restored.status_code == 200
    assert restored.json()["status"] == "WAITING_FOR_REVIEW"
    assert restored.json()["version"] == expected_version
    assert restored_document.json()["events"] == expected_events
    legal_name = next(
        item for item in restored_document.json()["fields"] if item["field_key"] == "legal_name"
    )
    assert legal_name["original_extracted_value"] == ("MERLION CIRCULAR LABS PTE. LIMITED")
    assert legal_name["reviewed_value"] == "MERLION CIRCULAR LABS PTE. LTD."


@pytest.mark.parametrize("legacy_stage_order", [False, True])
def test_uncertain_target_resume_stays_recovery_pending_without_replay(
    monkeypatch: pytest.MonkeyPatch,
    legacy_stage_order: bool,
) -> None:
    goldtier_calls = _install_counting_goldtier(monkeypatch)
    store = MemoryEnvelopeStore()
    with TestClient(_durable_adapter_app(store)) as first:  # type: ignore[arg-type]
        created = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        case_id = UUID(created.json()["case"]["case_id"])
        uploaded = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
            content=TEXT_PROFILE.encode(),
        )
        completed = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
        assert uploaded.status_code == 201
        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"

    snapshot = store.records[case_id]
    assert snapshot.automation is not None and snapshot.target_executions
    running = snapshot.automation.model_copy(
        update={
            "stage_order_version": (
                LEGACY_AUTOMATION_STAGE_ORDER_VERSION
                if legacy_stage_order
                else AUTOMATION_STAGE_ORDER_VERSION
            ),
            "status": AutomationStatus.RUNNING,
            "current_stage": AutomationStage.MOCK_GOLDTIER,
            "completed_stages": (
                AutomationStage.REGISTRY,
                *(
                    ()
                    if legacy_stage_order
                    else (AutomationStage.GOLDTIER_SEARCH,)
                ),
                AutomationStage.DOCUMENT,
                AutomationStage.OWNERSHIP,
                AutomationStage.READINESS,
            ),
            "completed_at": None,
        },
        deep=True,
    )
    running.metrics.final_outcome = None
    original_entry = snapshot.target_executions[0]
    uncertain = GoldTierExecutionLedgerEntry(
        submission_input=original_entry.submission_input,
        state=GoldTierExecutionLedgerState.IN_PROGRESS,
        attempted_operations=(GoldTierOperationMarker.SEARCH,),
    )
    interrupted = snapshot.model_copy(
        update={"automation": running, "target_executions": (uncertain,)}, deep=True
    )
    codec = object.__new__(MongoCaseStore)
    recovered = codec._recover_interrupted(interrupted)  # noqa: SLF001
    store.records[case_id] = recovered
    assert recovered.automation is not None
    expected_version = recovered.automation.version
    expected_event_count = len(recovered.automation.events)
    calls_before_resume = goldtier_calls.copy()

    with TestClient(_durable_adapter_app(store)) as second:  # type: ignore[arg-type]
        for _ in range(3):
            resumed = second.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
            assert resumed.status_code == 200
            assert resumed.json()["status"] == "RECOVERY_PENDING"
            assert resumed.json()["version"] == expected_version

    persisted = store.records[case_id]
    assert persisted.automation is not None
    assert len(persisted.automation.events) == expected_event_count
    assert persisted.target_executions == (uncertain,)
    assert goldtier_calls == calls_before_resume


def test_memory_mode_preserves_safe_pending_and_completed_resume_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goldtier_calls = _install_counting_goldtier(monkeypatch)
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="memory",
        mongo_uri=None,
    )
    with TestClient(create_app(settings)) as client:
        pending = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        pending_id = pending.json()["case"]["case_id"]
        calls_before_pending_resume = goldtier_calls.copy()

        pending_resume = client.post(f"/api/clm/zero-touch/cases/{pending_id}/resume")
        pending_detail = client.get(f"/api/clm/zero-touch/cases/{pending_id}")
        assert pending_resume.status_code == 409
        assert pending_resume.json()["detail"]["code"] == "ZERO_TOUCH_DOCUMENTS_REQUIRED"
        assert pending_detail.status_code == 200
        assert pending_detail.json()["status"] == "PENDING_INPUTS"
        assert goldtier_calls == calls_before_pending_resume

        completed = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
        completed_id = completed.json()["case"]["case_id"]
        uploaded = client.post(
            f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
            content=TEXT_PROFILE.encode(),
        )
        terminal = client.post(
            f"/api/clm/zero-touch/cases/{completed_id}/intake/complete",
            json={"expected_document_count": 1},
        )
        assert uploaded.status_code == 201
        assert terminal.status_code == 200
        paused = terminal.json()
        terminal = client.post(
            f"/api/clm/zero-touch/cases/{completed_id}/target-confirmation",
            json={
                "expected_automation_version": paused["version"],
                "expected_clm_version": paused["clm"]["version"],
                "expected_case_event_count": len(paused["case"]["events"]),
            },
        )
        assert terminal.status_code == 200
        assert terminal.json()["status"] == "COMPLETED"
        assert goldtier_calls == {'search': 4, 'shell': 1, 'policy': 1, 'amend': 1}
        calls_before_completed_resume = goldtier_calls.copy()

        completed_resume = client.post(f"/api/clm/zero-touch/cases/{completed_id}/resume")
        assert completed_resume.status_code == 200
        assert completed_resume.json()["status"] == "COMPLETED"
        assert goldtier_calls == calls_before_completed_resume
