"""Focused Phase 12 configuration, schema, and fail-closed tests."""

from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

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
from app.domain.documents import (
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
)
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
)
from app.domain.zero_touch import (
    AutomationEventType,
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
from app.services.zero_touch_repository import InMemoryZeroTouchAutomationRepository

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
        completed_stages=(AutomationStage.REGISTRY,),
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
    assert snapshot.schema_version == 4

    store = object.__new__(MongoCaseStore)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["schema_version"] = 5
    with pytest.raises(PersistenceSchemaUnsupportedError):
        store._decode(raw)  # noqa: SLF001 - direct corruption boundary test


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
    raw["onboarding"].pop("policy_snapshot")
    raw["onboarding"].pop("registry_evidence_binding")
    raw["_id"] = str(case.case_id)
    original = deepcopy(raw)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.schema_version == 4
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
    raw["onboarding"].pop("registry_evidence_binding")
    raw["_id"] = str(case.case_id)
    original = deepcopy(raw)

    decoded = object.__new__(MongoCaseStore)._decode(raw)  # noqa: SLF001

    assert decoded.schema_version == 4
    assert decoded.onboarding.registry_evidence_binding is None
    assert raw == original


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
def test_interrupted_current_document_recovers_automation_to_targeted_retry(
    interrupted_state: DocumentProcessingState,
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
            "status": AutomationStatus.RUNNING,
            "current_stage": AutomationStage.DOCUMENT,
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
    assert recovered.automation.completed_stages == (AutomationStage.REGISTRY,)
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


def test_partial_document_review_round_trips_across_adapter_restart() -> None:
    store = MemoryEnvelopeStore()
    mismatched_profile = TEXT_PROFILE.replace(
        "MERLION CIRCULAR LABS PTE. LTD.", "MERLION CIRCULAR LABS PTE. LIMITED"
    )
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
            (
                f"/api/onboarding/cases/{case_id}/documents/"
                f"{uploaded.json()['document_id']}/reviews"
            ),
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
        item
        for item in restored_document.json()["fields"]
        if item["field_key"] == "legal_name"
    )
    assert legal_name["original_extracted_value"] == (
        "MERLION CIRCULAR LABS PTE. LIMITED"
    )
    assert legal_name["reviewed_value"] == "MERLION CIRCULAR LABS PTE. LTD."


def test_uncertain_target_resume_stays_recovery_pending_without_replay(
    monkeypatch: pytest.MonkeyPatch,
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
        assert terminal.json()["status"] == "COMPLETED"
        assert goldtier_calls == {"search": 1, "shell": 1, "policy": 1, "amend": 1}
        calls_before_completed_resume = goldtier_calls.copy()

        completed_resume = client.post(f"/api/clm/zero-touch/cases/{completed_id}/resume")
        assert completed_resume.status_code == 200
        assert completed_resume.json()["status"] == "COMPLETED"
        assert goldtier_calls == calls_before_completed_resume
