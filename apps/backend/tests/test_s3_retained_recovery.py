"""A real interrupted Shell preserves its prefix and permits only verified continuation."""

from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import pytest
from fastapi import FastAPI
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pydantic import SecretStr
from scripts.run_s3_sandbox_acceptance import (
    BoundedAcceptanceTransport,
    OfflineAcceptanceTransport,
    SyntheticAcceptanceAcra,
    prepare_case,
)
from test_phase12_persistence import MemoryEnvelopeStore
from test_s3_submission_status import NAME, UEN, confirm

from app.composition import (
    build_clm_orchestration_service,
    build_document_processing_service,
    build_onboarding_service,
    build_ownership_analysis_service,
    build_reconciliation_service,
    build_zero_touch_orchestrator,
)
from app.config import Settings
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.domain.target_submission import GoldTierOperationMarker
from app.domain.zero_touch import AutomationStatus
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoClmOrchestrationRepository,
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoReconciliationUnitOfWork,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)
from app.services.policy_management import PolicyManagementService

Store = MemoryEnvelopeStore | MongoCaseStore


class InterruptedShellTransport(OfflineAcceptanceTransport):
    """The provider creates once; the process exits before retaining the response."""

    def __init__(self) -> None:
        super().__init__(NAME, UEN)
        self.interrupted = False
        self.counts = {operation: 0 for operation in (
            "SEARCH", "SHELL", "POLICY", "AMEND", "READBACK",
        )}
        self.calls: list[str] = []

    def request(self, method: str, url: str, **kwargs: Any) -> GoldTierXpiHttpResponse:
        response = super().request(method, url, **kwargs)
        path = urlsplit(url).path
        if method == "GET":
            operation = "READBACK" if self.created else "SEARCH"
        elif path.endswith("/customers/create"):
            operation = "SHELL"
        elif path.endswith("/customers/createPolicy"):
            operation = "POLICY"
        else:
            raise AssertionError("Unexpected synthetic protocol operation")
        self.counts[operation] += 1
        self.calls.append(operation)
        if operation == "SHELL" and not self.interrupted:
            self.interrupted = True
            raise KeyboardInterrupt
        return response


def retained_recovery_application(
    store: Store, settings: Settings, transport: InterruptedShellTransport,
) -> FastAPI:
    """Use normal services with one shared durable envelope and provider binding."""
    policy_bundle = build_persistence_bundle(settings)
    onboarding = build_onboarding_service(
        settings=settings,
        acra_connector=SyntheticAcceptanceAcra(NAME, UEN),
        goldtier_transport=transport,
        repository=MongoOnboardingCaseRepository(store),  # type: ignore[arg-type]
        target_execution_repository=MongoTargetExecutionRepository(store),  # type: ignore[arg-type]
        policy_snapshot_provider=PolicyManagementService(policy_bundle.policies).case_snapshot,
    )
    documents = build_document_processing_service(
        onboarding, settings,
        repository=MongoDocumentProcessingRepository(store),  # type: ignore[arg-type]
    )
    ownership = build_ownership_analysis_service(
        onboarding, settings, documents=documents,
        repository=MongoOwnershipAnalysisRepository(store),  # type: ignore[arg-type]
    )
    reconciliation = build_reconciliation_service(
        onboarding, documents,
        repository=MongoReconciliationRepository(store),  # type: ignore[arg-type]
        unit_of_work=MongoReconciliationUnitOfWork(store),  # type: ignore[arg-type]
    )
    clm = build_clm_orchestration_service(
        onboarding, documents, ownership, reconciliation,
        repository=MongoClmOrchestrationRepository(store),  # type: ignore[arg-type]
    )
    zero_touch = build_zero_touch_orchestrator(
        onboarding, documents, ownership, clm, reconciliation, settings,
        repository=MongoZeroTouchAutomationRepository(store),  # type: ignore[arg-type]
        durable_provider_bindings=True,
    )
    application = create_app(
        settings, onboarding_service=onboarding, document_processing_service=documents,
        ownership_analysis_service=ownership, reconciliation_service=reconciliation,
        clm_orchestration_service=clm, zero_touch_orchestrator=zero_touch,
    )
    application.router.add_event_handler("shutdown", policy_bundle.close)
    return application


def assert_interrupted_shell_recovery(
    store: Store, settings: Settings, restart: Callable[[Store], Store],
) -> None:
    """Shared memory-adapter/physical proof; never fabricate automation or ledger state."""
    transport = InterruptedShellTransport()
    # Preparation consumes only identity/review metadata from the bounded guard.
    # The application's actual execution transport stays the plain synthetic fake.
    metadata = BoundedAcceptanceTransport(
        transport, origin="https://sandbox.goldtier.invalid", environment="synthetic",
        name=NAME, uen=UEN,
    )
    interrupted = False
    application = retained_recovery_application(store, settings, transport)
    try:
        with RawTestClient(application) as client:
            summary, prepared = prepare_case(client, metadata, TEST_PASSWORD)
            case_id = UUID(summary["case"]["case_id"])
            path = f"/api/clm/zero-touch/cases/{case_id}"
            document_path = (
                f"/api/onboarding/cases/{case_id}/documents/{prepared['document_id']}"
            )
            document = client.get(document_path).json()
            ownership_path = f"/api/onboarding/cases/{case_id}/ownership"
            ownership = client.get(ownership_path).json()
            assert summary["case"]["created_by_actor_id"] == "maya-lim"
            assert ownership["manual_review_receipt"] is not None
            with pytest.raises(KeyboardInterrupt):
                confirm(client, summary)
            interrupted = True
    except RuntimeError as error:
        # KeyboardInterrupt stops Starlette's portal, including its context exit.
        assert interrupted and str(error) == "This portal is not running"
    finally:
        if transport.interrupted:
            # The stopped portal cannot run its normal synchronous store cleanup.
            for close in application.router.on_shutdown:
                close()
    assert interrupted and transport.created
    original = store.get(case_id)
    assert original is not None and original.automation is not None
    assert original.automation.status == AutomationStatus.RUNNING
    assert len(original.target_executions) == 1
    entry = original.target_executions[0]
    assert entry.attempted_operations == (
        GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL,
    )
    assert entry.lifecycle_resolved_operations == (GoldTierOperationMarker.SEARCH,)
    assert transport.counts == {
        "SEARCH": 2, "SHELL": 1, "POLICY": 0, "AMEND": 0, "READBACK": 0,
    }

    store = restart(store)
    recovered = store.get(case_id)
    assert recovered is not None and recovered.automation is not None
    assert recovered.automation.status == AutomationStatus.RECOVERY_PENDING
    assert recovered.target_executions == original.target_executions
    assert recovered.documents == original.documents and recovered.ownership == original.ownership
    assert recovered.onboarding.created_by_actor_id == original.onboarding.created_by_actor_id
    with RawTestClient(retained_recovery_application(store, settings, transport)) as client:
        login = client.post("/api/auth/login", json={
            "user_id": "olivia-koh", "password": TEST_PASSWORD,
        })
        assert login.status_code == 200
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        before = client.get(path).json()
        assert before["status"] == "RECOVERY_PENDING"
        assert before["target_submission"]["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
        assert before["target_submission"]["status_check_available"] is True
        counts = dict(transport.counts)
        unresolved = client.post(path + "/resume")
        assert unresolved.status_code == 200
        assert unresolved.json()["target_submission"]["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
        assert transport.counts == counts
        recovery = client.post(path + "/target-recovery", json={
            "operation": "SHELL", "recovered_party_id": "SYNTHETIC-GT-S3",
            "legal_name": NAME, "registration_number": UEN,
            "country_of_incorporation": "SG", "origin": "UNCERTAIN_DURABLE_LEDGER",
        })
        assert recovery.status_code == 200
        assert recovery.json()["replayed"] is False
        assert recovery.json()["authority"] == "PROVIDER_VERIFIED_RECOVERY"
        assert recovery.json()["attempted_operations"] == ["SEARCH", "SHELL"]
        assert recovery.json()["lifecycle_resolved_operations"] == ["SEARCH", "SHELL"]
        after = client.get(path).json()
        assert after["status"] == "RECOVERY_PENDING"
        assert after["target_submission"]["state"] == "FINALIZATION_PENDING"
        assert after["target_submission"]["status_check_available"] is False
        assert after["target_submission"]["goldtier_id"] == "SYNTHETIC-GT-S3"
        assert transport.counts["SHELL"] == 1 and transport.counts["POLICY"] == 0
        assert transport.calls[-1] == "READBACK"
        assert confirm(client, after).status_code == 409
        calls = list(transport.calls)
        resumed = client.post(path + "/resume")
        assert resumed.status_code == 200
        final = resumed.json()
        assert final["status"] == "COMPLETED"
        assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        assert final["target_submission"]["status_check_available"] is False
        assert transport.calls[len(calls):] == ["POLICY", "READBACK"]
        assert transport.counts == {
            "SEARCH": 2, "SHELL": 1, "POLICY": 1, "AMEND": 0, "READBACK": 2,
        }
        assert client.get(document_path).json() == document
        assert client.get(ownership_path).json() == ownership
        assert final["case"]["created_by_actor_id"] == "maya-lim"
        counts = dict(transport.counts)
        repeated = client.post(path + "/resume")
        assert repeated.status_code == 200 and repeated.json()["status"] == "COMPLETED"
        assert confirm(client, repeated.json()).status_code == 409
        assert transport.counts == counts


def test_verified_interrupted_shell_prefix_projects_finalization_and_resumes_only_next_operation():
    store = MemoryEnvelopeStore()
    settings = Settings(
        _env_file=None, app_env="test", clm_persistence_mode="memory",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-api-user"),
        goldtier_sandbox_allow_writes=True,
    )

    def restart(current: Store) -> Store:
        assert isinstance(current, MemoryEnvelopeStore)
        codec = object.__new__(MongoCaseStore)
        for case_id, snapshot in tuple(current.records.items()):
            current.records[case_id] = codec._recover_interrupted(snapshot)  # noqa: SLF001
        return current

    assert_interrupted_shell_recovery(store, settings, restart)
