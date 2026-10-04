"""Disposable physical restart proof for all three retained Sandbox outcomes."""

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pydantic import SecretStr
from scripts.run_s3_sandbox_acceptance import (
    BoundedAcceptanceTransport,
    SyntheticAcceptanceAcra,
    prepare_case,
)
from test_s2_intelligence_real_mongo import MONGO_URI, open_store, physical_database  # noqa: F401
from test_s3_retained_recovery import Store, assert_interrupted_shell_recovery
from test_s3_submission_status import NAME, UEN, ScenarioTransport, confirm

from app.main import create_app

pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


@pytest.mark.parametrize(("scenario", "expected"), [
    ("success", "SUBMISSION_CONFIRMED"),
    ("uncertain", "SUBMISSION_OUTCOME_UNCERTAIN"),
    ("failed", "SUBMISSION_FAILED"),
])
def test_physical_restart_preserves_documents_ownership_target_and_no_replay(
    physical_database, scenario, expected,  # noqa: F811
):
    settings = physical_database.model_copy(update={
        "goldtier_connector_mode": "sandbox",
        "goldtier_sandbox_base_url": "https://sandbox.goldtier.invalid",
        "goldtier_sandbox_environment": "synthetic",
        "goldtier_sandbox_user_id": SecretStr("synthetic-api-user"),
        "goldtier_sandbox_allow_writes": True,
    })
    guard = BoundedAcceptanceTransport(
        ScenarioTransport(scenario), origin="https://sandbox.goldtier.invalid",
        environment="synthetic", name=NAME, uen=UEN,
    )
    def application():
        return create_app(settings, acra_connector=SyntheticAcceptanceAcra(NAME, UEN),
                          goldtier_transport=guard)
    with RawTestClient(application()) as client:
        summary, prepared = prepare_case(client, guard, TEST_PASSWORD)
        case_id = summary["case"]["case_id"]
        guard.writes_approved = True
        final = confirm(client, summary).json()
        assert final["target_submission"]["state"] == expected
        document_path = f"/api/onboarding/cases/{case_id}/documents/{prepared['document_id']}"
        document = client.get(document_path).json()
        ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    counts = dict(guard.counts)
    with RawTestClient(application()) as restored:
        login = restored.post("/api/auth/login", json={
            "user_id": "maya-lim", "password": TEST_PASSWORD,
        })
        assert login.status_code == 200
        restored.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        current = restored.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert current["target_submission"] == final["target_submission"]
        assert current["target_operations"] == final["target_operations"]
        assert restored.get(document_path).json() == document
        assert restored.get(f"/api/onboarding/cases/{case_id}/ownership").json() == ownership
        assert len(document["ownership_observations"]) == 2
        assert ownership["manual_review_receipt"] is not None
        assert confirm(restored, current).status_code == 409
        assert guard.counts == counts


def test_physical_interrupted_shell_recovery_resumes_only_unattempted_policy_and_readback(
    physical_database,  # noqa: F811
):
    settings = physical_database.model_copy(update={
        "goldtier_connector_mode": "sandbox",
        "goldtier_sandbox_base_url": "https://sandbox.goldtier.invalid",
        "goldtier_sandbox_environment": "synthetic",
        "goldtier_sandbox_user_id": SecretStr("synthetic-api-user"),
        "goldtier_sandbox_allow_writes": True,
    })
    stores = [open_store(settings)]

    def restart(current: Store) -> Store:
        assert current is stores[-1]
        current.close()
        # Fresh connection and initialize invoke the normal strict restart owner.
        restored = open_store(settings)
        stores.append(restored)
        return restored

    try:
        assert_interrupted_shell_recovery(stores[0], settings, restart)
    finally:
        for store in stores:
            store.close()
