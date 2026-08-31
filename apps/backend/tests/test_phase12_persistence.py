"""Focused Phase 12 configuration, schema, and fail-closed tests."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

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
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
)
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    ZeroTouchAutomationRecord,
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
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)

TEXT_PROFILE = """Legal Name: MERLION CIRCULAR LABS PTE. LTD.
UEN: 202400001A
Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG
Country: SG
"""


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
        persisted = snapshot.model_copy(
            update={"revision": expected_revision + 1}, deep=True
        )
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


def _durable_adapter_app(store: MemoryEnvelopeStore) -> object:
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


def test_memory_mode_never_requires_mongo() -> None:
    bundle = build_persistence_bundle(
        Settings(_env_file=None, clm_persistence_mode="memory", mongo_uri=None)
    )
    assert bundle.mode == "memory"
    assert bundle.public_label == "Process-local"


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
    assert snapshot.schema_version == 1

    store = object.__new__(MongoCaseStore)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(uuid4())
    raw["schema_version"] = 2
    with pytest.raises(PersistenceSchemaUnsupportedError):
        store._decode(raw)  # noqa: SLF001 - direct corruption boundary test


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
        review = second.get(
            "/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW"
        )
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
