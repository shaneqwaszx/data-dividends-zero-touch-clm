"""Genuine Mongo composition-A to composition-B restart proof for Phase 12."""

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

import app.composition as composition
from app.composition import (
    build_document_processing_service,
    build_onboarding_service,
    build_reconciliation_service,
)
from app.config import Settings
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.documents import (
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
)
from app.domain.models import SafeError
from app.domain.reconciliation import ReconciliationDecisionAction
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
)
from app.domain.zero_touch import AutomationStage, AutomationStatus
from app.main import create_app
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
)
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)
from app.services.reconciliation import (
    ReconciliationInfrastructureError,
    ReconciliationRequestError,
    ReconciliationService,
)
from app.services.zero_touch_repository import ZeroTouchRepositoryConflictError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")

TEXT_PROFILE = """Legal Name: MERLION CIRCULAR LABS PTE. LTD.
UEN: 202400001A
Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG
Country: SG
"""
DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
CONFLICT_PROFILE = TEXT_PROFILE.replace(
    "MERLION CIRCULAR LABS PTE. LTD.", "DOCUMENT SELECTED PTE. LTD."
)


def _docx_bytes() -> bytes:
    output = BytesIO()
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
        for line in TEXT_PROFILE.splitlines()
    )
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paragraphs}</w:body></w:document>""",
        )
    return output.getvalue()


@pytest.fixture
def isolated_mongo_settings() -> Iterator[Settings]:
    assert MONGO_URI is not None
    database = f"clm_phase12_test_{uuid4().hex}"
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
    )
    cleanup_client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        yield settings
    finally:
        assert database.startswith("clm_phase12_test_")
        cleanup_client.drop_database(database)
        cleanup_client.close()


def _open_store(settings: Settings, *, initialize: bool = True) -> MongoCaseStore:
    assert MONGO_URI is not None
    store = MongoCaseStore(
        MongoClient(MONGO_URI),
        database=settings.mongo_database,
        collection=settings.mongo_case_collection,
    )
    if initialize:
        store.initialize()
    return store


def _install_counting_connectors(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, int]:
    counters = {name: 0 for name in ("registry", "idp", "ownership", "goldtier")}

    class CountingAcra(MockAcraConnector):
        def fetch_company(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_company(uen)

        def fetch_officers(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_officers(uen)

        def fetch_ownership_parties(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_ownership_parties(uen)

        def fetch_relationships(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_relationships(uen)

    class CountingIdp(LocalPdfTextIdpProvider):
        def process(self, document: object) -> object:
            counters["idp"] += 1
            return super().process(document)  # type: ignore[arg-type]

    class CountingOwnership(RegistryAcquisitionOwnershipProvider):
        def load(self, request: object) -> object:
            counters["ownership"] += 1
            return super().load(request)  # type: ignore[arg-type]

    class CountingGoldTier(MockGoldTierConnector):
        def search_party(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().search_party(request, metadata)  # type: ignore[arg-type]

        def create_shell_customer(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_shell_customer(request, metadata)  # type: ignore[arg-type]

        def create_policy(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_policy(request, metadata)  # type: ignore[arg-type]

        def amend_party(self, party_id: str, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().amend_party(party_id, request, metadata)  # type: ignore[arg-type]

    monkeypatch.setattr(composition, "MockAcraConnector", CountingAcra)
    monkeypatch.setattr(composition, "LocalPdfTextIdpProvider", CountingIdp)
    monkeypatch.setattr(
        composition, "RegistryAcquisitionOwnershipProvider", CountingOwnership
    )
    monkeypatch.setattr(composition, "MockGoldTierConnector", CountingGoldTier)
    return counters


def _create_case(client: TestClient, *, uen: str = "202400001A") -> UUID:
    response = client.post("/api/clm/zero-touch/cases", json={"uen": uen})
    assert response.status_code == 201, response.text
    return UUID(response.json()["case"]["case_id"])


def _upload_text(
    client: TestClient,
    case_id: UUID,
    content: str,
    *,
    name: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": "text/plain", "X-Document-Name": name},
        content=content.encode(),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _complete_intake(
    client: TestClient, case_id: UUID, *, expected_count: int
) -> dict[str, Any]:
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": expected_count},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _build_mongo_reconciliation_service(
    settings: Settings,
    store: MongoCaseStore,
    *,
    fault: Callable[[str], None] | None = None,
) -> ReconciliationService:
    onboarding = build_onboarding_service(
        settings=settings,
        repository=MongoOnboardingCaseRepository(store),
        target_execution_repository=MongoTargetExecutionRepository(store),
    )
    documents = build_document_processing_service(
        onboarding,
        settings,
        repository=MongoDocumentProcessingRepository(store),
    )
    return build_reconciliation_service(
        onboarding,
        documents,
        repository=MongoReconciliationRepository(store),
        unit_of_work=MongoReconciliationUnitOfWork(store, fault=fault),
    )


def test_real_mongo_restart_preserves_three_cases_and_replays_no_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MONGO_URI is not None
    database = f"clm_phase12_test_{uuid4().hex}"
    counters = {name: 0 for name in ("registry", "idp", "ownership", "goldtier")}

    class CountingAcra(MockAcraConnector):
        def fetch_company(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_company(uen)

        def fetch_officers(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_officers(uen)

        def fetch_ownership_parties(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_ownership_parties(uen)

        def fetch_relationships(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_relationships(uen)

    class CountingIdp(LocalPdfTextIdpProvider):
        def process(self, document: object) -> object:
            counters["idp"] += 1
            return super().process(document)  # type: ignore[arg-type]

    class CountingOwnership(RegistryAcquisitionOwnershipProvider):
        def load(self, request: object) -> object:
            counters["ownership"] += 1
            return super().load(request)  # type: ignore[arg-type]

    class CountingGoldTier(MockGoldTierConnector):
        def search_party(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().search_party(request, metadata)  # type: ignore[arg-type]

        def create_shell_customer(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_shell_customer(request, metadata)  # type: ignore[arg-type]

        def create_policy(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_policy(request, metadata)  # type: ignore[arg-type]

        def amend_party(self, party_id: str, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().amend_party(party_id, request, metadata)  # type: ignore[arg-type]

    monkeypatch.setattr(composition, "MockAcraConnector", CountingAcra)
    monkeypatch.setattr(composition, "LocalPdfTextIdpProvider", CountingIdp)
    monkeypatch.setattr(composition, "RegistryAcquisitionOwnershipProvider", CountingOwnership)
    monkeypatch.setattr(composition, "MockGoldTierConnector", CountingGoldTier)

    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
    )
    cleanup_client: MongoClient[dict[str, object]] = MongoClient(MONGO_URI)
    try:
        with TestClient(create_app(settings)) as first:
            completed = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
            assert completed.status_code == 201
            completed_id = completed.json()["case"]["case_id"]
            pdf = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
                headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
                content=TEXT_PROFILE.encode(),
            )
            docx = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
                headers={"Content-Type": DOCX_MEDIA, "X-Document-Name": "Constitution.docx"},
                content=_docx_bytes(),
            )
            txt = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
                headers={"Content-Type": "text/plain", "X-Document-Name": "Details.txt"},
                content=TEXT_PROFILE.encode(),
            )
            assert [pdf.status_code, docx.status_code, txt.status_code] == [201, 201, 201]
            done = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/complete",
                json={"expected_document_count": 3},
            )
            assert done.status_code == 200, done.text
            assert done.json()["status"] == "COMPLETED"

            pending = first.post(
                "/api/clm/zero-touch/cases", json={"uen": "202400001A"}
            )
            waiting = first.post(
                "/api/clm/zero-touch/cases",
                json={"uen": "UNKNOWN", "country_of_incorporation": "AU"},
            )
            assert pending.json()["status"] == "PENDING_INPUTS"
            assert waiting.json()["status"] == "WAITING_FOR_REVIEW"

        before_restart = counters.copy()
        assert before_restart == {
            "registry": 8,
            "idp": 3,
            "ownership": 1,
            "goldtier": 4,
        }

        with TestClient(create_app(settings)) as second:
            listed = second.get("/api/clm/zero-touch/cases")
            detail = second.get(f"/api/clm/zero-touch/cases/{completed_id}")
            documents = second.get(
                f"/api/onboarding/cases/{completed_id}/documents"
            )
            review = second.get(
                "/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW"
            )
            profile = second.get("/api/system/execution-profile")
            assert (
                listed.status_code
                == detail.status_code
                == documents.status_code
                == review.status_code
                == 200
            )
            assert {item["status"] for item in listed.json()} == {
                "PENDING_INPUTS",
                "WAITING_FOR_REVIEW",
                "COMPLETED",
            }
            assert detail.json()["status"] == "COMPLETED"
            assert len(documents.json()) == 3
            assert len(review.json()) == 1
            assert profile.json()["persistence"] == "Mongo-backed durable POC"
            assert counters == before_restart
    finally:
        assert database.startswith("clm_phase12_test_")
        cleanup_client.drop_database(database)
        cleanup_client.close()


def test_real_mongo_rejects_cross_case_storage_identity_on_every_read_path(
    isolated_mongo_settings: Settings,
) -> None:
    settings = isolated_mongo_settings
    with TestClient(create_app(settings)) as first:
        case_b = _create_case(first)
        document = _upload_text(first, case_b, TEXT_PROFILE, name="Identity.txt")
    document_id = UUID(document["document_id"])

    assert MONGO_URI is not None
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection = client[settings.mongo_database][settings.mongo_case_collection]
    raw = collection.find_one({"_id": str(case_b)})
    assert raw is not None
    case_a = uuid4()
    assert collection.delete_one({"_id": str(case_b)}).deleted_count == 1
    raw["_id"] = str(case_a)
    collection.insert_one(raw)

    store = _open_store(settings, initialize=False)
    try:
        assert store.get(case_b) is None
        with pytest.raises(PersistenceDataInvalidError):
            store.get(case_a)
        with pytest.raises(PersistenceDataInvalidError):
            store.list()
        with pytest.raises(PersistenceDataInvalidError):
            store.find_by_document(document_id)
    finally:
        store.close()
        client.close()

    with pytest.raises(PersistenceDataInvalidError):
        create_app(settings)


def test_real_mongo_interrupted_document_recovers_to_bounded_same_case_retry(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        completed = _upload_text(first, case_id, TEXT_PROFILE, name="Completed.txt")
    completed_id = UUID(completed["document_id"])

    store = _open_store(settings)
    snapshot = store.get(case_id)
    assert snapshot is not None and snapshot.automation is not None
    now = datetime.now(UTC)
    interrupted_id = uuid4()
    interrupted = DocumentProcessingRecord(
        case_id=case_id,
        document_id=interrupted_id,
        correlation_id=uuid4(),
        display_name="Interrupted.txt",
        media_type="text/plain",
        size_bytes=16,
        profile=DocumentProfile.PROVISIONAL_CORPORATE,
        state=DocumentProcessingState.PROCESSING,
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
    interrupted_snapshot = snapshot.model_copy(
        update={
            "documents": (*snapshot.documents, interrupted),
            "automation": running,
        },
        deep=True,
    )
    store.replace(interrupted_snapshot, expected_revision=snapshot.revision)
    store.close()

    before_restart = counters.copy()
    completed_event_count = len(
        next(item for item in snapshot.documents if item.document_id == completed_id).events
    )
    with TestClient(create_app(settings)) as second:
        detail = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        documents = second.get(f"/api/onboarding/cases/{case_id}/documents")
        assert detail.status_code == documents.status_code == 200
        assert detail.json()["status"] == "PENDING_INPUTS"
        assert detail.json()["current_stage"] == "DOCUMENT"
        recovered = next(
            item for item in documents.json() if item["document_id"] == str(interrupted_id)
        )
        preserved = next(
            item for item in documents.json() if item["document_id"] == str(completed_id)
        )
        assert recovered["state"] == "FAILED"
        assert recovered["error"]["code"] == "DOCUMENT_REUPLOAD_REQUIRED"
        assert len(preserved["events"]) == completed_event_count
        assert counters == before_restart

        unrelated = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Unrelated.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert unrelated.status_code == 409
        assert unrelated.json()["detail"]["code"] == (
            "ZERO_TOUCH_DOCUMENT_REUPLOAD_REQUIRED"
        )

        retried = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents/{interrupted_id}/retry",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Retry.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert retried.status_code == 201, retried.text
        assert retried.json()["case_id"] == str(case_id)
        after_retry = second.get(f"/api/onboarding/cases/{case_id}/documents")

    assert counters == {
        "registry": before_restart["registry"],
        "idp": before_restart["idp"] + 1,
        "ownership": before_restart["ownership"],
        "goldtier": before_restart["goldtier"],
    }
    records = after_retry.json()
    old_interrupted = next(
        item for item in records if item["document_id"] == str(interrupted_id)
    )
    assert old_interrupted["superseded_by_document_id"] == retried.json()["document_id"]
    assert next(
        item for item in records if item["document_id"] == str(completed_id)
    )["superseded_by_document_id"] is None


def test_real_mongo_technical_failure_restart_preserves_safe_terminal_state(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)

    store = _open_store(settings)
    snapshot = store.get(case_id)
    assert snapshot is not None and snapshot.automation is not None
    failed = snapshot.automation.model_copy(
        update={
            "status": AutomationStatus.TECHNICAL_FAILURE,
            "technical_failure": SafeError(
                code="TEST_SAFE_FAILURE",
                message="Onboarding stopped after a safe test failure.",
            ),
            "updated_at": datetime.now(UTC),
        },
        deep=True,
    )
    store.replace(
        snapshot.model_copy(update={"automation": failed}, deep=True),
        expected_revision=snapshot.revision,
    )
    store.close()

    before_restart = counters.copy()
    with TestClient(create_app(settings)) as second:
        detail = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "TECHNICAL_FAILURE"
        assert detail.json()["technical_failure"] == {
            "code": "TEST_SAFE_FAILURE",
            "message": "Onboarding stopped after a safe test failure.",
        }
    assert counters == before_restart


def test_real_mongo_uncertain_target_restart_and_resume_never_replay(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        _upload_text(first, case_id, TEXT_PROFILE, name="Profile.txt")
        completed = _complete_intake(first, case_id, expected_count=1)
        assert completed["status"] == "COMPLETED"

    store = _open_store(settings)
    snapshot = store.get(case_id)
    assert (
        snapshot is not None
        and snapshot.automation is not None
        and snapshot.target_executions
    )
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
    store.replace(
        snapshot.model_copy(
            update={"automation": running, "target_executions": (uncertain,)},
            deep=True,
        ),
        expected_revision=snapshot.revision,
    )
    store.close()

    before_restart = counters.copy()
    with TestClient(create_app(settings)) as second:
        detail = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        resumed = second.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert detail.status_code == resumed.status_code == 200
        assert detail.json()["status"] == "RECOVERY_PENDING"
        assert resumed.json()["status"] == "RECOVERY_PENDING"
    assert counters == before_restart


def test_real_mongo_replacement_restart_preserves_history_and_stales_old_decision(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        document_a = _upload_text(first, case_id, TEXT_PROFILE, name="Document-A.txt")
        document_b = _upload_text(
            first, case_id, CONFLICT_PROFILE, name="Document-B.txt"
        )
        paused = _complete_intake(first, case_id, expected_count=2)
        assert paused["status"] == "WAITING_FOR_REVIEW"
        old_discrepancy = next(
            item
            for item in paused["reconciliation"]["discrepancies"]
            if item["status"] == "OPEN"
        )
        replacement = first.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/documents/"
                f"{document_b['document_id']}/replacement"
            ),
            headers={
                "Content-Type": "text/plain",
                "X-Document-Name": "Document-B2.txt",
                "X-Document-Event-Count": str(len(document_b["events"])),
            },
            content=TEXT_PROFILE.encode(),
        )
        assert replacement.status_code == 200, replacement.text
        assert replacement.json()["status"] == "COMPLETED"

    before_restart = counters.copy()
    with TestClient(create_app(settings)) as second:
        documents = second.get(f"/api/onboarding/cases/{case_id}/documents")
        detail = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert documents.status_code == detail.status_code == 200
        by_id = {item["document_id"]: item for item in documents.json()}
        assert by_id[document_a["document_id"]]["superseded_by_document_id"] is None
        assert by_id[document_b["document_id"]]["superseded_by_document_id"] is not None
        replacement_id = by_id[document_b["document_id"]]["superseded_by_document_id"]
        assert by_id[replacement_id]["supersedes_document_id"] == document_b["document_id"]
        current_source_ids = set(detail.json()["reconciliation"]["source_document_ids"])
        assert current_source_ids == {document_a["document_id"], replacement_id}
        assert document_b["document_id"] not in current_source_ids

        stale = second.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/reconciliation/"
                f"discrepancies/{old_discrepancy['discrepancy_id']}/resolve"
            ),
            json={
                "action": "KEEP_REGISTRY_VALUE",
                "expected_automation_version": paused["version"],
                "expected_reconciliation_version": paused["reconciliation"]["version"],
                "evidence_fingerprint": old_discrepancy["evidence_fingerprint"],
            },
        )
        assert stale.status_code == 409
    assert counters == before_restart
    assert counters["registry"] == 4
    assert counters["idp"] == 3


def test_real_mongo_stale_envelope_cas_rejects_second_writer(
    isolated_mongo_settings: Settings,
) -> None:
    settings = isolated_mongo_settings
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)

    writer_a = _open_store(settings)
    writer_b = _open_store(settings)
    try:
        snapshot_a = writer_a.get(case_id)
        snapshot_b = writer_b.get(case_id)
        assert snapshot_a is not None and snapshot_b is not None
        assert snapshot_a.revision == snapshot_b.revision

        persisted_a = writer_a.replace(
            snapshot_a.model_copy(update={"demo_scenario": "STRAIGHT_THROUGH"}),
            expected_revision=snapshot_a.revision,
        )
        with pytest.raises(PersistenceConflictError):
            writer_b.replace(
                snapshot_b.model_copy(update={"demo_scenario": "DOCUMENT_DISCREPANCY"}),
                expected_revision=snapshot_b.revision,
            )

        durable = writer_a.get(case_id)
        assert durable is not None
        assert durable.revision == persisted_a.revision
        assert durable.demo_scenario == "STRAIGHT_THROUGH"
    finally:
        writer_a.close()
        writer_b.close()


def test_real_mongo_cross_repository_stale_write_preserves_successful_section(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        uploaded = _upload_text(first, case_id, TEXT_PROFILE, name="Original.txt")

    document_writer = _open_store(settings)
    automation_writer = _open_store(settings)
    try:
        stale = automation_writer.get(case_id)
        assert stale is not None and stale.automation is not None
        document = next(
            item
            for item in stale.documents
            if item.document_id == UUID(uploaded["document_id"])
        )
        MongoDocumentProcessingRepository(document_writer).save(
            document.model_copy(update={"display_name": "Writer-A.txt"}, deep=True)
        )

        monkeypatch.setattr(
            automation_writer,
            "get",
            lambda requested_case_id: (
                stale.model_copy(deep=True) if requested_case_id == case_id else None
            ),
        )
        automation_candidate = stale.automation.model_copy(
            update={"updated_at": datetime.now(UTC)}, deep=True
        )
        with pytest.raises(ZeroTouchRepositoryConflictError):
            MongoZeroTouchAutomationRepository(automation_writer).save(
                automation_candidate,
                expected_version=stale.automation.version,
            )

        durable = document_writer.get(case_id)
        assert durable is not None
        assert next(
            item
            for item in durable.documents
            if item.document_id == UUID(uploaded["document_id"])
        ).display_name == "Writer-A.txt"
        assert durable.automation == stale.automation
    finally:
        document_writer.close()
        automation_writer.close()


def _create_real_mongo_conflict_case(settings: Settings) -> UUID:
    with TestClient(create_app(settings)) as client:
        case_id = _create_case(client)
        _upload_text(client, case_id, CONFLICT_PROFILE, name="Conflict.txt")
        paused = _complete_intake(client, case_id, expected_count=1)
        assert paused["status"] == "WAITING_FOR_REVIEW"
        return case_id


def _resolve_document_legal_name(
    service: ReconciliationService,
    store: MongoCaseStore,
    case_id: UUID,
) -> None:
    snapshot = store.get(case_id)
    assert snapshot is not None and snapshot.reconciliation is not None
    discrepancy = snapshot.reconciliation.open_discrepancies[0]
    service.resolve_discrepancy(
        case_id=case_id,
        discrepancy_id=discrepancy.discrepancy_id,
        action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
        expected_version=snapshot.reconciliation.version,
        evidence_fingerprint=discrepancy.evidence_fingerprint,
    )


def test_real_mongo_phase11_resolution_commits_canonical_and_decision_together(
    isolated_mongo_settings: Settings,
) -> None:
    settings = isolated_mongo_settings
    case_id = _create_real_mongo_conflict_case(settings)
    store = _open_store(settings)
    try:
        service = _build_mongo_reconciliation_service(settings, store)
        _resolve_document_legal_name(service, store, case_id)

        durable = store.get(case_id)
        assert durable is not None
        assert durable.onboarding.entity is not None
        assert durable.onboarding.entity.legal_name == "DOCUMENT SELECTED PTE. LTD."
        assert durable.reconciliation is not None
        decision = durable.reconciliation.discrepancies[0].decision
        assert decision is not None
        assert decision.action == ReconciliationDecisionAction.USE_DOCUMENT_VALUE
    finally:
        store.close()


def test_real_mongo_phase11_stale_cas_changes_neither_atomic_half(
    isolated_mongo_settings: Settings,
) -> None:
    settings = isolated_mongo_settings
    case_id = _create_real_mongo_conflict_case(settings)
    store = _open_store(settings)
    concurrent = _open_store(settings)
    before = store.get(case_id)
    assert before is not None

    def create_stale_revision(stage: str) -> None:
        assert stage == "before_atomic_commit"
        current = concurrent.get(case_id)
        assert current is not None
        concurrent.replace(
            current.model_copy(update={"demo_scenario": "STRAIGHT_THROUGH"}),
            expected_revision=current.revision,
        )

    try:
        service = _build_mongo_reconciliation_service(
            settings, store, fault=create_stale_revision
        )
        with pytest.raises(ReconciliationRequestError) as caught:
            _resolve_document_legal_name(service, store, case_id)
        assert caught.value.code == "RECONCILIATION_CONFLICT"

        durable = concurrent.get(case_id)
        assert durable is not None
        assert durable.demo_scenario == "STRAIGHT_THROUGH"
        assert durable.onboarding == before.onboarding
        assert durable.reconciliation == before.reconciliation
    finally:
        store.close()
        concurrent.close()


def test_real_mongo_phase11_precommit_failure_changes_neither_atomic_half(
    isolated_mongo_settings: Settings,
) -> None:
    settings = isolated_mongo_settings
    case_id = _create_real_mongo_conflict_case(settings)
    store = _open_store(settings)
    before = store.get(case_id)
    assert before is not None

    def fail_before_commit(stage: str) -> None:
        assert stage == "before_atomic_commit"
        raise RuntimeError("bounded test fault")

    try:
        service = _build_mongo_reconciliation_service(
            settings, store, fault=fail_before_commit
        )
        with pytest.raises(ReconciliationInfrastructureError) as caught:
            _resolve_document_legal_name(service, store, case_id)
        assert caught.value.code == "RECONCILIATION_COMMIT_FAILED"

        durable = store.get(case_id)
        assert durable is not None
        assert durable.onboarding == before.onboarding
        assert durable.reconciliation == before.reconciliation
    finally:
        store.close()
