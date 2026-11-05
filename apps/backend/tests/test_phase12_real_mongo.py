"""Genuine Mongo composition-A to composition-B restart proof for Phase 12."""

import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from io import BytesIO
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from s2_legacy_schema_fixtures import assert_retained_legacy_content, omit_session2_fields
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_slice_a_legacy_compatibility import rich_v7_snapshot

import app.composition as composition
from app.composition import (
    build_document_processing_service,
    build_onboarding_service,
    build_reconciliation_service,
)
from app.config import Settings
from app.connectors.errors import AcraOperationUnsupportedError
from app.connectors.idp import IdpDocumentInput, IdpProcessingError
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MISSING_OWNERSHIP_UEN, MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.documents import (
    DocumentFieldKey,
    DocumentProcessingRecord,
    DocumentProcessingState,
    DocumentProfile,
    FieldReviewStatus,
    ReviewDecision,
)
from app.domain.models import SafeError
from app.domain.onboarding_intelligence import (
    MockRiskAssessment,
    MockRiskBand,
    OnboardingIntelligenceRecord,
)
from app.domain.policy import CasePolicySnapshot, legacy_intelligence_policy_snapshot
from app.domain.reconciliation import ReconciliationDecisionAction
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    GoldTierRecoveryOrigin,
    GoldTierSearchResolution,
    ProviderVerifiedRecovery,
)
from app.domain.zero_touch import AutomationStage, AutomationStatus
from app.main import create_app
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
)
from app.persistence.models import DurableCaseSnapshot, DurableCaseSnapshotV7
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
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in TEXT_PROFILE.splitlines()
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
    database = generate_ephemeral_mongo_database("p12")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        # This suite composes case stores directly; registry storage is separate.
        registry_cache_mode="disabled",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
    )
    cleanup_client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        yield settings
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup_client, database)
        finally:
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


def test_real_mongo_concurrent_field_review_has_one_durable_winner(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    with TestClient(create_app(settings)) as client:
        case_id = _create_case(client)
        uploaded = _upload_text(client, case_id, CONFLICT_PROFILE, name="Review.txt")
    document_id = UUID(uploaded["document_id"])
    stores = (_open_store(settings), _open_store(settings))
    services = []
    barrier = Barrier(2)
    try:
        initial_snapshot = stores[0].get(case_id)
        assert initial_snapshot is not None
        race_revision = initial_snapshot.revision
        for store in stores:
            snapshot = store.get(case_id)
            assert snapshot is not None
            assert snapshot.revision == race_revision
            onboarding = build_onboarding_service(
                settings=settings,
                repository=MongoOnboardingCaseRepository(store),
                target_execution_repository=MongoTargetExecutionRepository(store),
            )
            services.append(
                build_document_processing_service(
                    onboarding,
                    settings,
                    repository=MongoDocumentProcessingRepository(store),
                )
            )
            original_replace = store.replace

            def synchronized_replace(
                snapshot: object,
                *,
                expected_revision: int,
                replace: Callable[..., object] = original_replace,
            ) -> object:
                # Race the initial decisions only. The CAS winner subsequently
                # persists review completion after automatic sibling confirmation.
                if expected_revision == race_revision:
                    barrier.wait(timeout=10)
                return replace(snapshot, expected_revision=expected_revision)

            monkeypatch.setattr(store, "replace", synchronized_replace)

        def decide(index: int, decision: ReviewDecision) -> object:
            try:
                return services[index].review_field(
                    case_id=case_id,
                    document_id=document_id,
                    field_key=DocumentFieldKey.LEGAL_NAME,
                    decision=decision,
                )
            except Exception as exc:  # inspected below as the durable CAS loser
                return exc

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = [
                executor.submit(decide, 0, ReviewDecision.ACCEPTED),
                executor.submit(decide, 1, ReviewDecision.REJECTED),
            ]
            results = [future.result() for future in outcomes]

        assert sum(isinstance(item, DocumentProcessingRecord) for item in results) == 1
        assert sum(isinstance(item, PersistenceConflictError) for item in results) == 1
        winner = next(item for item in results if isinstance(item, DocumentProcessingRecord))
        fresh_store = _open_store(settings, initialize=False)
        try:
            persisted = MongoDocumentProcessingRepository(fresh_store).get(document_id)
            assert persisted is not None
            assert winner.state == persisted.state == DocumentProcessingState.REVIEWED
            completed_snapshot = fresh_store.get(case_id)
            assert completed_snapshot is not None
            assert completed_snapshot.revision == race_revision + 2
            legal_name = next(
                item
                for item in persisted.fields
                if item.field_key == DocumentFieldKey.LEGAL_NAME
            )
            winning_legal_name = next(
                item
                for item in winner.fields
                if item.field_key == DocumentFieldKey.LEGAL_NAME
            )
            assert legal_name.review_status == winning_legal_name.review_status
            assert legal_name.review_status in {
                FieldReviewStatus.ACCEPTED,
                FieldReviewStatus.REJECTED,
            }
        finally:
            fresh_store.close()
    finally:
        for store in stores:
            store.close()


def test_real_mongo_restart_rejects_policy_unbound_intelligence(
    isolated_mongo_settings: Settings,
) -> None:
    settings = isolated_mongo_settings
    store = _open_store(settings)
    onboarding = build_onboarding_service(
        settings=settings,
        policy_snapshot_provider=lambda: CasePolicySnapshot(
            snapshot_label="TEST_INTELLIGENCE_POLICY_V1",
            catalogue_version=1,
            idp_review_confidence_threshold="0.85",
            ubo_threshold_percent="25.000000",
            intelligence=legacy_intelligence_policy_snapshot(),
            bound_at=datetime(2026, 9, 23, tzinfo=UTC),
        ),
    )
    case = onboarding.create_staged_case("202400001A")
    now = datetime.now(UTC)
    record = OnboardingIntelligenceRecord(
        case_id=case.case_id,
        version=1,
        input_fingerprint="sha256:" + "a" * 64,
        policy_catalogue_version=case.policy_snapshot.catalogue_version,
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
        evaluated_at=now,
    )
    store.create(
        DurableCaseSnapshot(
            case_id=case.case_id,
            revision=0,
            onboarding=case,
            intelligence=record,
            created_at=now,
            updated_at=now,
        )
    )
    store._collection.update_one(  # noqa: SLF001 - deliberate physical corruption
        {"_id": str(case.case_id)},
        {"$set": {"intelligence.policy_catalogue_version": 999}},
    )
    store.close()

    restarted = _open_store(settings, initialize=False)
    try:
        with pytest.raises(PersistenceDataInvalidError):
            restarted.get(case.case_id)
        with pytest.raises(PersistenceDataInvalidError):
            restarted.initialize()
    finally:
        restarted.close()


def test_real_mongo_restart_preserves_review_refresh_and_stops_target(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        uploaded = _upload_text(first, case_id, CONFLICT_PROFILE, name="Partial.txt")
        paused = _complete_intake(first, case_id, expected_count=1)
        initial_exception_ids = {
            item["exception_id"] for item in paused["active_exceptions"]
        }
        reviewed = first.post(
            (
                f"/api/onboarding/cases/{case_id}/documents/"
                f"{uploaded['document_id']}/reviews"
            ),
            json={
                "field_key": "legal_name",
                "decision": "CORRECTED",
                "corrected_value": "MERLION CIRCULAR LABS PTE. LTD.",
            },
        )
        assert reviewed.status_code == 200, reviewed.text
        refreshed = first.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert refreshed["status"] == "WAITING_FOR_REVIEW"
        assert initial_exception_ids.isdisjoint(
            item["exception_id"] for item in refreshed["active_exceptions"]
        )
        assert counters == {"registry": 4, "idp": 1, "ownership": 1, "goldtier": 1}

    before_restart = counters.copy()
    with TestClient(create_app(settings)) as second:
        restored = second.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        repeated = second.post(f"/api/clm/zero-touch/cases/{case_id}/resume").json()
        restored_document = second.get(
            f"/api/onboarding/cases/{case_id}/documents/{uploaded['document_id']}"
        ).json()

    assert restored["status"] == repeated["status"] == "WAITING_FOR_REVIEW"
    assert restored["version"] == repeated["version"]
    legal_name = next(
        item
        for item in restored_document["fields"]
        if item["field_key"] == "legal_name"
    )
    pending = [
        item for item in restored_document["fields"]
        if item["review_status"] == "PENDING"
    ]
    assert legal_name["review_status"] == "CORRECTED"
    assert legal_name["reviewed_value"] == "MERLION CIRCULAR LABS PTE. LTD."
    assert pending == []
    assert all(
        item["review_status"] == "ACCEPTED"
        for item in restored_document["fields"]
        if item["field_key"] != "legal_name"
    )
    assert counters == before_restart
    snapshot = _open_store(settings, initialize=False)
    try:
        durable = snapshot.get(case_id)
        assert durable is not None
        assert durable.target_executions == ()
    finally:
        snapshot.close()


def test_real_mongo_failed_replacement_restart_requires_retry_without_replay(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    failure_marker = b"FAIL_REPLACEMENT_IDP"

    class FailingReplacementIdp(LocalPdfTextIdpProvider):
        def process(self, document: IdpDocumentInput) -> object:
            counters["idp"] += 1
            if document.content == failure_marker:
                raise IdpProcessingError
            return LocalPdfTextIdpProvider.process(self, document)

    monkeypatch.setattr(composition, "LocalPdfTextIdpProvider", FailingReplacementIdp)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        original = _upload_text(first, case_id, CONFLICT_PROFILE, name="Original.txt")
        paused = _complete_intake(first, case_id, expected_count=1)
        assert paused["status"] == "WAITING_FOR_REVIEW"
        started_store = _open_store(settings, initialize=False)
        try:
            started_snapshot = started_store.get(case_id)
            assert started_snapshot is not None and started_snapshot.automation is not None
            started_at = started_snapshot.automation.started_at
            assert started_at is not None
            assert started_snapshot.target_executions == ()
        finally:
            started_store.close()
        stale_exception = paused["active_exceptions"][0]
        current_document = first.get(
            f"/api/onboarding/cases/{case_id}/documents/{original['document_id']}"
        )
        assert current_document.status_code == 200
        current_event_count = len(current_document.json()["events"])
        assert current_document.json()["events"] == original["events"]
        assert any(
            event["event_type"] == "DOCUMENT_AUTO_CONFIRMED" for event in original["events"]
        )
        assert [
            field["field_key"] for field in current_document.json()["fields"]
            if field["review_status"] == "PENDING"
        ] == ["legal_name"]
        failed = first.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/documents/"
                f"{original['document_id']}/replacement"
            ),
            headers={
                "Content-Type": "text/plain",
                "X-Document-Name": "Failed.txt",
                "X-Document-Event-Count": str(current_event_count),
            },
            content=failure_marker,
        )
        assert failed.status_code == 503
        assert failed.json()["detail"]["code"] == "IDP_PROCESSING_FAILED"
        pending = first.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        documents = first.get(f"/api/onboarding/cases/{case_id}/documents").json()
        by_id = {item["document_id"]: item for item in documents}
        current_documents = [
            item for item in documents if item["superseded_by_document_id"] is None
        ]
        assert len(current_documents) == 1
        current = current_documents[0]
        assert pending["status"] == "PENDING_INPUTS"
        assert pending["current_stage"] == "DOCUMENT"
        assert pending["active_exceptions"] == []
        assert pending["timeline"][-1]["event_type"] == "DOCUMENT_REUPLOAD_REQUIRED"
        assert current["state"] == "FAILED"
        failed_document_id = current["document_id"]
        assert current["supersedes_document_id"] == original["document_id"]
        assert by_id[original["document_id"]]["superseded_by_document_id"] == (
            failed_document_id
        )
        assert by_id[original["document_id"]]["superseded_at"] is not None
        assert counters == {"registry": 4, "idp": 2, "ownership": 0, "goldtier": 1}

    before_restart = counters.copy()
    with TestClient(create_app(settings)) as second:
        restored = second.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        restored_documents = second.get(
            f"/api/onboarding/cases/{case_id}/documents"
        ).json()
        assert restored["status"] == "PENDING_INPUTS"
        assert restored["current_stage"] == "DOCUMENT"
        restored_by_id = {item["document_id"]: item for item in restored_documents}
        assert restored_by_id[failed_document_id]["state"] == "FAILED"
        assert restored_by_id[failed_document_id]["supersedes_document_id"] == (
            original["document_id"]
        )
        assert restored_by_id[failed_document_id]["superseded_by_document_id"] is None
        assert restored_by_id[original["document_id"]]["superseded_by_document_id"] == (
            failed_document_id
        )
        assert counters == before_restart

        stale = second.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/exceptions/"
                f"{stale_exception['exception_id']}/resolve"
            ),
            json={
                "action": "KEEP_REGISTRY_VALUE",
                "expected_automation_version": paused["version"],
                "evidence_version": stale_exception["evidence_version"],
            },
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "ZERO_TOUCH_EXCEPTION_STALE"
        assert counters == before_restart

        retried = second.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/intake/documents/"
                f"{failed_document_id}/retry"
            ),
            headers={"Content-Type": "text/plain", "X-Document-Name": "Retry.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert retried.status_code == 201, retried.text
        retried_document = retried.json()
        retried_document_id = retried_document["document_id"]
        assert retried_document["supersedes_document_id"] == failed_document_id
        assert retried_document["superseded_by_document_id"] is None
        after_retry = second.get(
            f"/api/onboarding/cases/{case_id}/documents"
        ).json()
        after_retry_by_id = {item["document_id"]: item for item in after_retry}
        assert after_retry_by_id[failed_document_id]["superseded_by_document_id"] == (
            retried_document_id
        )
        assert after_retry_by_id[retried_document_id]["supersedes_document_id"] == (
            failed_document_id
        )
        assert after_retry_by_id[retried_document_id]["superseded_by_document_id"] is None
        assert retried_document["case_id"] == str(case_id)
        assert retried_document["state"] == "REVIEWED"
        assert len(after_retry_by_id) == 3
        assert after_retry_by_id[original["document_id"]]["superseded_by_document_id"] == (
            failed_document_id
        )
        assert after_retry_by_id[failed_document_id]["state"] == "FAILED"
        assert all(item["case_id"] == str(case_id) for item in after_retry)
        # PR83 continues a started recovery once; this is not initial intake completion.
        assert counters == {"registry": 4, "idp": 3, "ownership": 1, "goldtier": 1}
        pending = second.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert pending["status"] == "WAITING_FOR_REVIEW"
        assert pending["current_stage"] == "READINESS"
        assert [item["exception_type"] for item in pending["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        resumed = second.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert resumed.status_code == 200
        assert resumed.json()["version"] == pending["version"]
        assert counters == {"registry": 4, "idp": 3, "ownership": 1, "goldtier": 1}
        recovered_store = _open_store(settings, initialize=False)
        try:
            recovered_snapshot = recovered_store.get(case_id)
            assert recovered_snapshot is not None and recovered_snapshot.automation is not None
            assert recovered_snapshot.automation.started_at == started_at
            assert recovered_snapshot.target_executions == ()
            assert recovered_snapshot.onboarding.target_dispatch_confirmation is None
        finally:
            recovered_store.close()
        completed = _confirm_target_dispatch(second, case_id, pending)
        assert completed["status"] == "COMPLETED"
        assert completed["case"]["case_id"] == str(case_id)
        assert counters == {"registry": 4, "idp": 3, "ownership": 1, "goldtier": 6}
        repeated_retry = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Repeat.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert repeated_retry.status_code == 409
        assert repeated_retry.json()["detail"]["code"] == "ZERO_TOUCH_INTAKE_NOT_OPEN"
        assert second.get(f"/api/onboarding/cases/{case_id}/documents").json() == after_retry

    with TestClient(create_app(settings)) as third:
        restored = third.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        resumed = third.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert resumed.status_code == 200
        assert restored["status"] == resumed.json()["status"] == "COMPLETED"
        assert restored["version"] == resumed.json()["version"] == completed["version"]
        assert restored["case"]["target_dispatch_confirmation"] == (
            completed["case"]["target_dispatch_confirmation"]
        )
        assert third.get(f"/api/onboarding/cases/{case_id}/documents").json() == after_retry
    assert counters == {"registry": 4, "idp": 3, "ownership": 1, "goldtier": 6}


def _install_counting_connectors(
    monkeypatch: pytest.MonkeyPatch,
    *, unsupported_relationships: bool = False,
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
            if unsupported_relationships:
                raise AcraOperationUnsupportedError
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


def _complete_intake(client: TestClient, case_id: UUID, *, expected_count: int) -> dict[str, Any]:
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": expected_count},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _confirm_target_dispatch(
    client: Any,
    case_id: UUID | str,
    pending: dict[str, Any],
    *,
    csrf_token: str | None = None,
) -> dict[str, Any]:
    """Complete a happy-path fixture through the real guarded confirmation API."""

    assert pending["status"] == "WAITING_FOR_REVIEW"
    assert any(
        item["exception_type"] == "TARGET_CONFIRMATION_REQUIRED"
        for item in pending["active_exceptions"]
    )
    assert pending["case"]["target_dispatch_confirmation"] is None
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": pending["version"],
            "expected_clm_version": pending["clm"]["version"],
            "expected_case_event_count": len(pending["case"]["events"]),
        },
        headers={"X-CSRF-Token": csrf_token} if csrf_token else {},
    )
    assert response.status_code == 200, response.text
    confirmed: dict[str, Any] = response.json()
    assert confirmed["case"]["target_dispatch_confirmation"] is not None
    return confirmed


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
    database = generate_ephemeral_mongo_database("p12")
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
            confirmed = _confirm_target_dispatch(first, completed_id, done.json())
            assert confirmed["status"] == "COMPLETED"
            first_intelligence = first.get(
                f"/api/clm/zero-touch/cases/{completed_id}/intelligence"
            )
            assert first_intelligence.status_code == 200
            assert first_intelligence.json()["model_bundle_version"] == (
                "onboarding-intelligence-v1"
            )

            pending = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
            waiting = first.post(
                "/api/clm/zero-touch/cases",
                json={"uen": "UNKNOWN", "country_of_incorporation": "AU"},
            )
            assert pending.json()["status"] == "PENDING_INPUTS"
            assert waiting.json()["status"] == "WAITING_FOR_REVIEW"

        before_restart = counters.copy()
        assert before_restart == {
            "registry": 4,  # The second exact-UEN case reuses the ordinary cache.
            "idp": 3,
            "ownership": 1,
            "goldtier": 7,
        }

        with TestClient(create_app(settings)) as second:
            listed = second.get("/api/clm/zero-touch/cases")
            detail = second.get(f"/api/clm/zero-touch/cases/{completed_id}")
            resumed_completed = second.post(f"/api/clm/zero-touch/cases/{completed_id}/resume")
            documents = second.get(f"/api/onboarding/cases/{completed_id}/documents")
            review = second.get("/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW")
            profile = second.get("/api/system/execution-profile")
            restored_intelligence = second.get(
                f"/api/clm/zero-touch/cases/{completed_id}/intelligence"
            )
            assert (
                listed.status_code
                == detail.status_code
                == resumed_completed.status_code
                == documents.status_code
                == review.status_code
                == restored_intelligence.status_code
                == 200
            )
            assert {item["status"] for item in listed.json()} == {
                "PENDING_INPUTS",
                "WAITING_FOR_REVIEW",
                "COMPLETED",
            }
            assert detail.json()["status"] == "COMPLETED"
            assert resumed_completed.json()["status"] == "COMPLETED"
            assert len(documents.json()) == 3
            assert len(review.json()) == 1
            assert profile.json()["persistence"] == "Mongo-backed durable POC"
            assert restored_intelligence.json() == first_intelligence.json()
            assert counters == before_restart
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup_client, database)
        finally:
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
        assert unrelated.json()["detail"]["code"] == ("ZERO_TOUCH_DOCUMENT_REUPLOAD_REQUIRED")

        retried = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents/{interrupted_id}/retry",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Retry.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert retried.status_code == 201, retried.text
        assert retried.json()["case_id"] == str(case_id)
        after_retry = second.get(f"/api/onboarding/cases/{case_id}/documents")
        assert after_retry.status_code == 200
        records = after_retry.json()
        assert len(records) == 3
        assert all(item["case_id"] == str(case_id) for item in records)
        old_interrupted = next(
            item for item in records if item["document_id"] == str(interrupted_id)
        )
        assert old_interrupted["state"] == "FAILED"
        assert old_interrupted["superseded_by_document_id"] == retried.json()["document_id"]
        assert old_interrupted["superseded_at"] is not None
        current = next(
            item for item in records if item["document_id"] == retried.json()["document_id"]
        )
        assert current["state"] == "REVIEWED"
        assert current["supersedes_document_id"] == str(interrupted_id)
        assert current["superseded_by_document_id"] is None
        sibling = next(item for item in records if item["document_id"] == str(completed_id))
        assert sibling["superseded_by_document_id"] is None
        assert len(sibling["events"]) == completed_event_count
        assert sibling["events"] == preserved["events"]
        continued_counts = {
            "registry": before_restart["registry"],
            "idp": before_restart["idp"] + 1,
            "ownership": before_restart["ownership"] + 1,
            "goldtier": before_restart["goldtier"],
        }
        assert counters == continued_counts
        pending = second.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert pending["status"] == "WAITING_FOR_REVIEW"
        assert pending["current_stage"] == "READINESS"
        assert [item["exception_type"] for item in pending["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        recovered_store = _open_store(settings, initialize=False)
        try:
            recovered_snapshot = recovered_store.get(case_id)
            assert recovered_snapshot is not None and recovered_snapshot.automation is not None
            assert recovered_snapshot.automation.started_at == now
            assert recovered_snapshot.target_executions == ()
            assert recovered_snapshot.onboarding.target_dispatch_confirmation is None
        finally:
            recovered_store.close()
        for _ in range(2):
            observed = second.get(f"/api/clm/zero-touch/cases/{case_id}").json()
            assert observed["version"] == pending["version"]
            assert observed["status"] == "WAITING_FOR_REVIEW"
            assert observed["current_stage"] == "READINESS"
        resumed = second.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert resumed.status_code == 200
        assert resumed.json()["version"] == pending["version"]
        invalid_retry = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents/{interrupted_id}/retry",
            headers={"Content-Type": "text/plain", "X-Document-Name": "Repeat.txt"},
            content=TEXT_PROFILE.encode(),
        )
        assert invalid_retry.status_code == 409
        assert invalid_retry.json()["detail"]["code"] == "ZERO_TOUCH_INTAKE_NOT_OPEN"
        assert counters == continued_counts
        sent = _confirm_target_dispatch(second, case_id, pending)
        assert sent["status"] == "COMPLETED"
        assert sent["case"]["case_id"] == str(case_id)
        assert counters == {**continued_counts, "goldtier": before_restart["goldtier"] + 5}
    with TestClient(create_app(settings)) as third:
        restored = third.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        resumed = third.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
        assert resumed.status_code == 200
        assert restored["status"] == resumed.json()["status"] == "COMPLETED"
        assert restored["version"] == resumed.json()["version"] == sent["version"]
        assert restored["case"]["target_dispatch_confirmation"] == (
            sent["case"]["target_dispatch_confirmation"]
        )
        assert third.get(f"/api/onboarding/cases/{case_id}/documents").json() == records
    assert counters == {**continued_counts, "goldtier": before_restart["goldtier"] + 5}


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
        pending = _complete_intake(first, case_id, expected_count=1)
        completed = _confirm_target_dispatch(first, case_id, pending)
        assert completed["status"] == "COMPLETED"

    store = _open_store(settings)
    snapshot = store.get(case_id)
    assert snapshot is not None and snapshot.automation is not None and snapshot.target_executions
    running = snapshot.automation.model_copy(
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
        resumed = [second.post(f"/api/clm/zero-touch/cases/{case_id}/resume") for _ in range(3)]
        assert detail.status_code == 200
        assert all(item.status_code == 200 for item in resumed)
        assert detail.json()["status"] == "RECOVERY_PENDING"
        assert all(item.json()["status"] == "RECOVERY_PENDING" for item in resumed)
    assert counters == before_restart


def test_real_mongo_shell_and_policy_recovery_facts_survive_restart_with_amend_next(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        _upload_text(first, case_id, TEXT_PROFILE, name="Profile.txt")
        pending = _complete_intake(first, case_id, expected_count=1)
        completed = _confirm_target_dispatch(first, case_id, pending)
        assert completed["status"] == "COMPLETED"

    store = _open_store(settings)
    snapshot = store.get(case_id)
    assert snapshot is not None and snapshot.target_executions
    original = snapshot.target_executions[0]
    entity = original.submission_input.canonical_entity
    assert original.submission_input.target_policy is not None
    policy = original.submission_input.target_policy.policy.value
    verified_at = datetime.now(UTC)
    recovered = GoldTierExecutionLedgerEntry(
        submission_input=original.submission_input,
        state=GoldTierExecutionLedgerState.IN_PROGRESS,
        attempted_operations=(
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
        ),
        completed_operations=(GoldTierOperationMarker.SEARCH,),
        resolved_operations=(
            GoldTierOperationMarker.SEARCH,
            GoldTierOperationMarker.SHELL,
            GoldTierOperationMarker.POLICY,
        ),
        provider_verified_recovery=ProviderVerifiedRecovery(
            origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
            recovered_party_id="RECOVERED-123",
            legal_name=entity.legal_name,
            registration_number=entity.registration_number,
            country_of_incorporation=entity.country_of_incorporation,
            actor_id="mongo-restart-test",
            verified_at=verified_at,
            candidate_count=1,
        ),
        provider_verified_policy_recovery=ProviderVerifiedRecovery(
            origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
            operation=GoldTierOperationMarker.POLICY,
            recovered_party_id="RECOVERED-123",
            legal_name=entity.legal_name,
            registration_number=entity.registration_number,
            country_of_incorporation=entity.country_of_incorporation,
            actor_id="mongo-restart-test",
            verified_at=verified_at,
            candidate_count=1,
            provider_policy=policy,
            provider_policy_status="Requested",
        ),
        search_resolution=GoldTierSearchResolution.NO_MATCH,
        resolved_party_id="RECOVERED-123",
        shell_status="PROVIDER_VERIFIED_RECOVERY",
        policy_status="PROVIDER_VERIFIED_REQUESTED",
    )
    store.replace(
        snapshot.model_copy(update={"target_executions": (recovered,)}, deep=True),
        expected_revision=snapshot.revision,
    )
    store.close()

    restarted = _open_store(settings)
    try:
        after = restarted.get(case_id)
        assert after is not None
        assert after.target_executions == (recovered,)
        assert after.target_executions[0].resolved_party_id == "RECOVERED-123"
        assert after.target_executions[0].provider_verified_recovery is not None
        assert after.target_executions[0].provider_verified_recovery.replayed is False
        policy_recovery = after.target_executions[0].provider_verified_policy_recovery
        assert policy_recovery is not None
        assert policy_recovery.provider_policy == policy
        assert policy_recovery.provider_policy_status == "Requested"
        assert policy_recovery.replayed is False
        assert GoldTierOperationMarker.AMEND not in after.target_executions[0].attempted_operations
    finally:
        restarted.close()


def test_real_mongo_replacement_restart_preserves_history_and_stales_old_decision(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        document_a = _upload_text(first, case_id, TEXT_PROFILE, name="Document-A.txt")
        document_b = _upload_text(first, case_id, CONFLICT_PROFILE, name="Document-B.txt")
        paused = _complete_intake(first, case_id, expected_count=2)
        assert paused["status"] == "WAITING_FOR_REVIEW"
        old_discrepancy = next(
            item for item in paused["reconciliation"]["discrepancies"] if item["status"] == "OPEN"
        )
        current_document = first.get(
            f"/api/onboarding/cases/{case_id}/documents/{document_b['document_id']}"
        )
        assert current_document.status_code == 200
        current_event_count = len(current_document.json()["events"])
        assert current_document.json()["events"] == document_b["events"]
        assert any(
            event["event_type"] == "DOCUMENT_AUTO_CONFIRMED" for event in document_b["events"]
        )
        assert [
            field["field_key"] for field in current_document.json()["fields"]
            if field["review_status"] == "PENDING"
        ] == ["legal_name"]
        replacement = first.post(
            (
                f"/api/clm/zero-touch/cases/{case_id}/documents/"
                f"{document_b['document_id']}/replacement"
            ),
            headers={
                "Content-Type": "text/plain",
                "X-Document-Name": "Document-B2.txt",
                "X-Document-Event-Count": str(current_event_count),
            },
            content=TEXT_PROFILE.encode(),
        )
        assert replacement.status_code == 200, replacement.text
        confirmed = _confirm_target_dispatch(first, case_id, replacement.json())
        assert confirmed["status"] == "COMPLETED"

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
            item for item in stale.documents if item.document_id == UUID(uploaded["document_id"])
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
        assert (
            next(
                item
                for item in durable.documents
                if item.document_id == UUID(uploaded["document_id"])
            ).display_name
            == "Writer-A.txt"
        )
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
        service = _build_mongo_reconciliation_service(settings, store, fault=create_stale_revision)
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
        service = _build_mongo_reconciliation_service(settings, store, fault=fail_before_commit)
        with pytest.raises(ReconciliationInfrastructureError) as caught:
            _resolve_document_legal_name(service, store, case_id)
        assert caught.value.code == "RECONCILIATION_COMMIT_FAILED"

        durable = store.get(case_id)
        assert durable is not None
        assert durable.onboarding == before.onboarding
        assert durable.reconciliation == before.reconciliation
    finally:
        store.close()


def test_real_mongo_schema_v7_restart_preserves_identity_repair_and_pending_confirmation_guard(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact v7 bytes retain recovery/audit facts and cannot bypass confirmation."""

    target_calls: list[str] = []

    class CountingGoldTier(MockGoldTierConnector):
        def search_party(self, request: object, metadata: object) -> object:
            target_calls.append("search")
            return super().search_party(request, metadata)  # type: ignore[arg-type]

        def create_shell_customer(self, request: object, metadata: object) -> object:
            target_calls.append("shell")
            return super().create_shell_customer(request, metadata)  # type: ignore[arg-type]

        def create_policy(self, request: object, metadata: object) -> object:
            target_calls.append("policy")
            return super().create_policy(request, metadata)  # type: ignore[arg-type]

        def amend_party(self, party_id: str, request: object, metadata: object) -> object:
            target_calls.append("amend")
            return super().amend_party(party_id, request, metadata)  # type: ignore[arg-type]

    monkeypatch.setattr(composition, "MockGoldTierConnector", CountingGoldTier)
    settings = isolated_mongo_settings
    with TestClient(create_app(settings)) as first:
        created = first.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": "202400001A",
                "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
            },
        )
        assert created.status_code == 201
        before = created.json()
        case_id = UUID(before["case"]["case_id"])
        assert before["case"]["initial_identity"] is None

        repaired = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/identity-search-recheck",
            json={
                "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
                "registration_number": "202400001A",
                "country_of_incorporation": "SG",
                "expected_automation_version": before["version"],
                "expected_clm_version": before["clm"]["version"],
                "expected_case_event_count": len(before["case"]["events"]),
            },
        )
        assert repaired.status_code == 200, repaired.text
        _upload_text(first, case_id, TEXT_PROFILE, name="Recovered-identity.txt")
        pending = _complete_intake(first, case_id, expected_count=1)
        assert pending["status"] == "WAITING_FOR_REVIEW"
        assert pending["case"]["target_dispatch_confirmation"] is None
        confirmation = next(
            item
            for item in pending["active_exceptions"]
            if item["blocker_code"] == "TARGET_CONFIRMATION_REQUIRED"
        )
        assert confirmation["decisions"][0]["metadata"]["classification"] == (
            "USER_ACTION_REQUIRED"
        )

    store = _open_store(settings, initialize=False)
    try:
        retained = store.get(case_id)
        assert retained is not None and retained.automation is not None
        assert retained.onboarding.identity_corrections
        assert retained.onboarding.initial_target_search_attempts
        assert retained.onboarding.initial_target_search_attempts[-1].status == "COMPLETED"
        assert retained.onboarding.target_dispatch_confirmation is None
        assert retained.automation.active_exceptions[0].decisions
        raw = store._collection.find_one({"_id": str(case_id)})  # noqa: SLF001
        assert raw is not None and raw["schema_version"] == 19
    finally:
        store.close()

    calls_before_restart_guard = target_calls.copy()
    with TestClient(create_app(settings)) as restarted:
        detail = restarted.get(f"/api/clm/zero-touch/cases/{case_id}")
        blocked = restarted.post(f"/api/clm/cases/{case_id}/submit")

    assert detail.status_code == 200
    assert detail.json()["case"]["identity_corrections"]
    assert detail.json()["case"]["target_dispatch_confirmation"] is None
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "CLM_TARGET_CONFIRMATION_REQUIRED"
    assert target_calls == calls_before_restart_guard == ["search"]


def test_real_mongo_partial_registry_manual_ownership_restart_preserves_confirmation_guard(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counters = _install_counting_connectors(monkeypatch, unsupported_relationships=True)
    settings = isolated_mongo_settings
    profile = """SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE
Legal Name: MISSING OWNERSHIP EVIDENCE DEMO PTE. LTD.
UEN: 202400011K
Registered Address: 18 PARTIAL STREET, #06-01, 049006, SG
Country: SG
"""
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first, uen=MISSING_OWNERSHIP_UEN)
        uploaded = _upload_text(first, case_id, profile, name="Synthetic-ownership-profile.txt")
        pending = _complete_intake(first, case_id, expected_count=1)
        assert pending["current_stage"] == "OWNERSHIP"
        assert pending["case"]["state"] == "VALIDATED"
        assert pending["case"]["registry_acquisition"]["status"] == "PARTIAL"
        relationship = pending["case"]["registry_acquisition"]["operation_results"][3]
        assert relationship["status"] == "UNSUPPORTED"
        assert relationship["provenance"] is None
        assert counters["registry"] == 3
        assert pending["ownership_recovery"]["manual_evidence_action"] == (
            "MANUAL_OWNERSHIP_EVIDENCE"
        )

    before_restart = counters.copy()
    with TestClient(create_app(settings)) as second:
        retained = second.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert retained["case"]["registry_acquisition"]["operation_results"][3] == relationship
        documents = second.get(f"/api/onboarding/cases/{case_id}/documents").json()
        document = next(
            item for item in documents if item["document_id"] == uploaded["document_id"]
        )
        assert document["state"] == "REVIEWED"
        response = second.post(
            f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
            json={
                "root_registration_number": MISSING_OWNERSHIP_UEN,
                "evidence_document_id": document["document_id"],
                "evidence_document_version": len(document["events"]),
                "as_of_date": datetime.now(UTC).date().isoformat(),
                "rationale": "Operator reviewed synthetic client-supplied ownership evidence.",
                "root_party_id": "SYNTHETIC_ROOT",
                "parties": [
                    {
                        "party_id": "SYNTHETIC_ROOT",
                        "display_name": "Synthetic client company",
                        "party_type": "LEGAL_ENTITY",
                        "registration_number": MISSING_OWNERSHIP_UEN,
                        "country": "SG",
                    },
                    {
                        "party_id": "SYNTHETIC_OWNER",
                        "display_name": "Synthetic client owner",
                        "party_type": "NATURAL_PERSON",
                        "country": "SG",
                    },
                ],
                "relationships": [
                    {
                        "relationship_id": "SYNTHETIC_INTEREST",
                        "parent_party_id": "SYNTHETIC_ROOT",
                        "child_party_id": "SYNTHETIC_OWNER",
                        "ownership_percent": "100",
                    }
                ],
                "expected_automation_version": retained["version"],
                "expected_ownership_version": retained["ownership_recovery"]["version"],
                "expected_case_event_count": len(retained["case"]["events"]),
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["current_stage"] == "READINESS"
        assert response.json()["ownership_recovery"]["review_receipt"]["source_type"] == (
            "USER_SUPPLIED_DECLARATION"
        )
    assert counters == before_restart

    with TestClient(create_app(settings)) as third:
        detail = third.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert detail["case"]["registry_acquisition"]["status"] == "PARTIAL"
        assert detail["case"]["registry_acquisition"]["operation_results"][3] == relationship
        assert detail["ownership_recovery"]["state"] == "ANALYZED"
        assert detail["case"]["target_dispatch_confirmation"] is None
        blocked = third.post(f"/api/clm/cases/{case_id}/submit")
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "CLM_TARGET_CONFIRMATION_REQUIRED"
    assert counters == before_restart


@pytest.mark.parametrize("scenario", ["RECONCILIATION", "PENDING", "CONFIRMED", "IDENTITY"])
def test_real_mongo_populated_actual_v7_restart_has_no_rewrite_or_provider_replay(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
) -> None:
    """Historical bytes survive fresh store and application composition unchanged."""
    snapshot = rich_v7_snapshot(scenario)
    settings = isolated_mongo_settings
    counters = _install_counting_connectors(monkeypatch)
    store = _open_store(settings)
    try:
        raw = store._encode(snapshot)  # noqa: SLF001
        raw["schema_version"] = 7
        omit_session2_fields(raw)
        DurableCaseSnapshotV7.model_validate(
            {key: value for key, value in raw.items() if key != "_id"}
        )
        before = deepcopy(raw)
        store._collection.insert_one(raw)  # noqa: SLF001 - historical synthetic write
    finally:
        store.close()

    restarted_store = _open_store(settings)
    try:
        current = restarted_store.get(snapshot.case_id)
        assert_retained_legacy_content(current, snapshot)
        assert restarted_store._collection.find_one(  # noqa: SLF001
            {"_id": str(snapshot.case_id)}
        ) == before
    finally:
        restarted_store.close()

    with TestClient(create_app(settings)) as restarted_app:
        response = restarted_app.get(f"/api/clm/zero-touch/cases/{snapshot.case_id}")
        assert response.status_code == 200
        public = response.json()
        assert "ownership_provider_binding_id" not in str(public)
        assert "authoritative_evidence_digest" not in str(public)
        if scenario in {"PENDING", "IDENTITY"}:
            assert public["case"]["target_dispatch_confirmation"] is None
        if scenario == "IDENTITY":
            assert public["case"]["identity_corrections"]
        if scenario == "CONFIRMED":
            assert public["case"]["target_dispatch_confirmation"] is not None
    assert counters == {"registry": 0, "idp": 0, "ownership": 0, "goldtier": 0}
    final_store = _open_store(settings, initialize=False)
    try:
        restored = final_store.get(snapshot.case_id)
        assert restored is not None
        assert_retained_legacy_content(restored, snapshot)
        assert final_store._collection.find_one(  # noqa: SLF001
            {"_id": str(snapshot.case_id)}
        ) == before
    finally:
        final_store.close()


def test_real_mongo_actual_v7_uncertain_target_recovery_never_replays(
    isolated_mongo_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup recovery may write its checkpoint; ordinary conversion cannot replay."""
    snapshot = rich_v7_snapshot("CONFIRMED")
    assert snapshot.automation is not None and snapshot.target_executions
    running = snapshot.automation.model_copy(
        update={
            "status": AutomationStatus.RUNNING,
            "current_stage": AutomationStage.MOCK_GOLDTIER,
            "completed_stages": (
                AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH,
                AutomationStage.DOCUMENT, AutomationStage.OWNERSHIP, AutomationStage.READINESS,
            ),
            "completed_at": None,
        },
        deep=True,
    )
    running.metrics.final_outcome = None
    uncertain = GoldTierExecutionLedgerEntry(
        submission_input=snapshot.target_executions[0].submission_input,
        state=GoldTierExecutionLedgerState.IN_PROGRESS,
        attempted_operations=(GoldTierOperationMarker.SEARCH,),
    )
    interrupted = snapshot.model_copy(
        update={"automation": running, "target_executions": (uncertain,)}, deep=True
    )
    counters = _install_counting_connectors(monkeypatch)
    settings = isolated_mongo_settings
    store = _open_store(settings)
    try:
        raw = store._encode(interrupted)  # noqa: SLF001
        raw["schema_version"] = 7
        omit_session2_fields(raw)
        DurableCaseSnapshotV7.model_validate(
            {key: value for key, value in raw.items() if key != "_id"}
        )
        store._collection.insert_one(raw)  # noqa: SLF001
    finally:
        store.close()
    with TestClient(create_app(settings)) as restarted:
        detail = restarted.get(f"/api/clm/zero-touch/cases/{snapshot.case_id}")
        resumed = [
            restarted.post(f"/api/clm/zero-touch/cases/{snapshot.case_id}/resume")
            for _ in range(3)
        ]
        assert detail.status_code == 200
        assert detail.json()["status"] == "RECOVERY_PENDING"
        assert all(item.status_code == 200 for item in resumed)
        assert all(item.json()["status"] == "RECOVERY_PENDING" for item in resumed)
    assert counters == {"registry": 0, "idp": 0, "ownership": 0, "goldtier": 0}
    final_store = _open_store(settings)
    try:
        retained = final_store.get(snapshot.case_id)
        assert retained is not None
        assert retained.target_executions == (uncertain,)
        assert retained.onboarding.target_dispatch_confirmation == (
            snapshot.onboarding.target_dispatch_confirmation
        )
    finally:
        final_store.close()
