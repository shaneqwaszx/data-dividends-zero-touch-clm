"""Offline browser recovery contract: current identity, authorization and no replay."""

from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pydantic import SecretStr
from scripts.run_s3_sandbox_acceptance import (
    BoundedAcceptanceTransport,
    SyntheticAcceptanceAcra,
    prepare_case,
)
from test_clm_orchestration import make_ready_case
from test_policy_provider_recovery import (
    UncertainPolicyTransport,
    login_as,
    recovery_payload,
)
from test_s3_submission_status import NAME, UEN, ScenarioTransport, confirm
from test_target_classification_continuation import (
    COMPANIES,
    prepare,
    runtime,
)
from test_target_classification_continuation import (
    confirm as confirm_classification,
)

from app.config import Settings
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
from app.domain.target_submission import GoldTierSearchResolution
from app.main import create_app
from app.services.clm_errors import ClmRequestError


@pytest.fixture
def sandbox_runtime(request):
    # The real-acceptance guard has a one-readback budget. Recovery explicitly
    # requires additional reads, so use an offline-only mutation-counting wrapper.
    guard = BoundedAcceptanceTransport(
        ScenarioTransport(getattr(request, "param", "success")),
        origin="https://sandbox.goldtier.invalid", environment="synthetic", name=NAME, uen=UEN,
    )

    class OfflineRecoveryTransport:
        def request(self, method, url, **kwargs):
            assert url.startswith("https://sandbox.goldtier.invalid/")
            operation = (
                "READBACK" if guard.delegate.created else "SEARCH"
            ) if method == "GET" else "SHELL" if url.endswith("/create") else "POLICY"
            guard.counts[operation] += 1
            if method == "POST":
                assert guard.counts[operation] == 1
            return guard.delegate.request(method, url, **kwargs)

    settings = Settings(
        _env_file=None, app_env="test", goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic", goldtier_sandbox_allow_writes=True,
        goldtier_sandbox_user_id=SecretStr("synthetic-api-user"),
    )
    with RawTestClient(create_app(
        settings, acra_connector=SyntheticAcceptanceAcra(NAME, UEN),
        goldtier_transport=OfflineRecoveryTransport(),
    )) as client:
        yield client, guard


def login(client, user):
    session = client.post("/api/auth/login", json={
        "user_id": user, "password": TEST_PASSWORD,
    })
    assert session.status_code == 200
    client.headers["X-CSRF-Token"] = session.json()["csrf_token"]


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("drift", ["document", "ownership", "policy", "confirmation"])
def test_every_recovery_contract_rejects_drift_without_calls_or_resolution(legacy, drift):
    target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
    with runtime(target=target) as (client, bundle, _, _):
        unresolved = confirm_classification(client, prepare(client, COMPANIES[0]))
        case_id = UUID(unresolved["case"]["case_id"])
        path = f"/api/clm/zero-touch/cases/{case_id}"
        if drift == "document":
            document = bundle.documents.list_for_case(case_id)[0]
            document.updated_at += timedelta(seconds=1)
            bundle.documents.save(document)
        elif drift == "ownership":
            analysis = bundle.ownership.get_for_case(case_id)
            analysis.updated_at += timedelta(seconds=1)
            # Simulate independently retained evidence drift in this memory-only fixture.
            bundle.ownership._records[case_id] = analysis  # noqa: SLF001
        else:
            case = bundle.onboarding.get(case_id)
            if drift == "policy":
                policy = case.policy_snapshot.goldtier_target
                case.policy_snapshot = case.policy_snapshot.model_copy(update={
                    "goldtier_target": policy.model_copy(update={
                        "customer_external_system": policy.customer_external_system.model_copy(
                            update={"value": "STALE"},
                        ),
                    }),
                })
            else:
                case.target_dispatch_confirmation = None
            bundle.onboarding.save(case)
        before = bundle.target_executions.list_for_case(case_id)
        automation = bundle.automation.get_for_case(case_id)
        calls = list(target.calls)
        login_as(client, "olivia-koh")
        body = recovery_payload(unresolved)
        if not legacy:
            for field in ("legal_name", "registration_number", "country_of_incorporation"):
                body.pop(field)
            body["expected_submission_id"] = unresolved["target_submission"]["submission_id"]
        assert client.get(path).json()["target_submission"]["recovery_available"] is False
        rejected = client.post(path + "/target-recovery", json=body)
        assert rejected.status_code == 422
        assert rejected.json()["detail"]["code"] == "TARGET_RECOVERY_REJECTED"
        assert bundle.target_executions.list_for_case(case_id) == before
        assert bundle.automation.get_for_case(case_id) == automation
        assert target.calls == calls


@pytest.mark.parametrize("sandbox_runtime", ["uncertain"], indirect=True)
def test_director_minimal_frozen_policy_recovery_and_same_intent_continuation(sandbox_runtime):
    client, guard = sandbox_runtime
    prepared, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    unresolved = confirm(client, prepared).json()
    target = unresolved["target_submission"]
    assert target["recovery_operation"] == "POLICY"
    assert target["attempted_operations"] == ["SEARCH", "SHELL", "POLICY"]
    assert target["definitively_completed_operations"] == ["SEARCH", "SHELL"]
    assert target["lifecycle_resolved_operations"] == ["SEARCH", "SHELL"]
    assert target["uncertainty_reason"] == "TIMEOUT"
    path = f"/api/clm/zero-touch/cases/{prepared['case']['case_id']}"
    body = {
        "expected_submission_id": target["submission_id"], "operation": "POLICY",
        "recovered_party_id": target["goldtier_id"], "provider_policy": "Singapore",
        "provider_policy_status": "Requested", "origin": "UNCERTAIN_DURABLE_LEDGER",
    }
    counts = dict(guard.counts)
    assert client.post(path + "/target-recovery", json=body).status_code == 403
    assert guard.counts == counts
    login(client, "olivia-koh")
    assert client.get(path).json()["target_submission"]["recovery_available"] is True
    stale = client.post(path + "/target-recovery", json={
        **body, "expected_submission_id": str(uuid4()),
    })
    assert stale.status_code == 409 and guard.counts == counts
    overridden = client.post(path + "/target-recovery", json={**body, "legal_name": "OTHER"})
    assert overridden.status_code == 422 and guard.counts == counts
    recovered = client.post(path + "/target-recovery", json=body)
    assert recovered.status_code == 200
    assert recovered.json()["replayed"] is False
    assert client.post(path + "/target-recovery", json=body).json() == recovered.json()
    assert guard.counts == counts
    pending = client.get(path).json()
    assert pending["status"] == "RECOVERY_PENDING"
    assert pending["target_submission"]["state"] == "FINALIZATION_PENDING"
    assert pending["case"]["target_dispatch_confirmation"] == unresolved["case"][
        "target_dispatch_confirmation"
    ]
    final = client.post(path + "/resume").json()
    assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
    assert final["target_submission"]["submission_id"] == target["submission_id"]
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 1
    assert guard.counts["AMEND"] == 0 and guard.counts["READBACK"] == 1


def test_search_only_retained_intent_rechecks_snapshot_before_first_write():
    cases, documents, _, clm, target, case_id = make_ready_case()
    frozen = clm.get(case_id=case_id)
    submission = frozen.submission_snapshot.target_input
    cases._start_incremental_execution(  # noqa: SLF001
        submission, search_resolution=GoldTierSearchResolution.NO_MATCH, selected_party_id=None,
    )
    document = documents.list_documents(case_id=case_id)[0]
    document.updated_at += timedelta(seconds=1)
    documents._repository.save(document)  # noqa: SLF001
    before = cases.get_target_execution_entry(submission.submission_id)
    with pytest.raises(ClmRequestError, match="CLM_TARGET_CONFIRMATION_REQUIRED"):
        clm.submit(case_id=case_id)
    assert cases.get_target_execution_entry(submission.submission_id) == before
    assert target.calls == ["search", "search"]
    assert not cases.is_execution_outcome_uncertain(submission.submission_id)


def test_confirmation_read_only_preflight_failure_has_no_attempt_and_can_be_rechecked(
    sandbox_runtime, monkeypatch,
):
    client, guard = sandbox_runtime
    prepared, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    original = guard.delegate.request

    def unavailable(method, url, **kwargs):
        assert method == "GET"
        raise httpx.ReadTimeout("PRIVATE_PREFLIGHT_SENTINEL")

    monkeypatch.setattr(guard.delegate, "request", unavailable)
    failed = confirm(client, prepared).json()
    target = failed["target_submission"]
    assert target["state"] == "NOT_SUBMITTED" and target["submission_id"] is None
    assert target["attempted_operations"] == []
    assert failed["case"]["target_dispatch_confirmation"] is None
    assert failed["clm"]["submission"] is None
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 0
    assert "SENTINEL" not in str(failed)
    monkeypatch.setattr(guard.delegate, "request", original)
    path = f"/api/clm/zero-touch/cases/{prepared['case']['case_id']}"
    rechecked = client.post(path + "/identity-search-recheck", json={
        "legal_name": failed["case"]["entity"]["legal_name"],
        "registration_number": failed["case"]["requested_uen"],
        "country_of_incorporation": "SG", "expected_automation_version": failed["version"],
        "expected_clm_version": failed["clm"]["version"],
        "expected_case_event_count": len(failed["case"]["events"]),
    })
    assert rechecked.status_code == 200
    assert rechecked.json()["target_submission"]["state"] == "NOT_SUBMITTED"
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 0


@pytest.mark.parametrize("observation", ["verified", "no-match", "ambiguous", "conflicting"])
def test_uncertain_shell_read_only_observation_then_director_recovery_without_replay(
    sandbox_runtime, monkeypatch, observation,
):
    client, guard = sandbox_runtime
    prepared, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    original = guard.delegate.request

    def lost_shell_response(method, url, **kwargs):
        response = original(method, url, **kwargs)
        if method == "POST" and url.endswith("/customers/create"):
            raise httpx.ReadTimeout("PRIVATE_SHELL_SENTINEL")
        return response

    monkeypatch.setattr(guard.delegate, "request", lost_shell_response)
    unresolved = confirm(client, prepared).json()
    target = unresolved["target_submission"]
    path = f"/api/clm/zero-touch/cases/{prepared['case']['case_id']}"
    assert target["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
    assert target["recovery_operation"] == "SHELL" and target["recovery_available"] is False
    assert target["attempted_operations"] == ["SEARCH", "SHELL"]
    assert target["definitively_completed_operations"] == ["SEARCH"]
    candidate = {
        "goldTierId": "SYNTHETIC-GT-S3", "legalName": prepared["case"]["entity"]["legal_name"],
        "registrationNumber": prepared["case"]["requested_uen"], "countryOfIncorporation": "SG",
    }

    def read_only(method, url, **kwargs):
        assert method == "GET"
        if observation == "no-match":
            return GoldTierXpiHttpResponse(200, [])
        if observation == "ambiguous":
            return GoldTierXpiHttpResponse(200, [candidate, {**candidate, "goldTierId": "OTHER"}])
        if observation == "conflicting":
            return GoldTierXpiHttpResponse(200, [{**candidate, "registrationNumber": "202499999Z"}])
        return GoldTierXpiHttpResponse(200, [candidate])

    monkeypatch.setattr(guard.delegate, "request", read_only)
    checked = client.post(path + "/target-status-check", json={
        "expected_submission_id": target["submission_id"],
    }).json()
    assert checked["result"] == {
        "verified": "CUSTOMER_IDENTITY_VERIFIED", "no-match": "NO_MATCH",
        "ambiguous": "AMBIGUOUS", "conflicting": "IDENTITY_UNVERIFIED",
    }[observation]
    assert checked["verified_party_id"] == (
        "SYNTHETIC-GT-S3" if observation == "verified" else None
    )
    assert client.get(path).json()["target_submission"]["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
    login(client, "olivia-koh")
    body = {
        "expected_submission_id": target["submission_id"], "operation": "SHELL",
        "recovered_party_id": "SYNTHETIC-GT-S3", "origin": "UNCERTAIN_DURABLE_LEDGER",
    }
    recovery = client.post(path + "/target-recovery", json=body)
    assert recovery.status_code == (200 if observation == "verified" else 422)
    assert guard.counts["SHELL"] == 1 and guard.counts["POLICY"] == 0
    if observation != "verified":
        still_uncertain = client.get(path).json()["target_submission"]
        assert still_uncertain["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
        return
    before_repeat = dict(guard.counts)
    assert client.post(path + "/target-recovery", json=body).status_code == 200
    assert guard.counts == before_repeat
    pending = client.get(path).json()
    assert pending["status"] == "RECOVERY_PENDING"
    assert pending["target_submission"]["state"] == "FINALIZATION_PENDING"
    monkeypatch.setattr(guard.delegate, "request", original)
    final = client.post(path + "/resume").json()
    assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
    assert final["target_submission"]["submission_id"] == target["submission_id"]
    assert final["case"]["target_dispatch_confirmation"] == unresolved["case"][
        "target_dispatch_confirmation"
    ]
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 1
