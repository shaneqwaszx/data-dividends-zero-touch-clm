"""Synthetic Policy recovery: truthful prefixes, authorization and zero replay."""

from copy import deepcopy
from hashlib import sha256
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from phase13_test_credentials import TEST_PASSWORD
from test_clm_orchestration import make_ready_case
from test_goldtier_xpi_sandbox import (
    FakeXpiTransport,
    _confirm_service_submission,
    _uncertain_policy_fixture,
    _xpi_onboarding_service,
)
from test_target_classification_continuation import (
    COMPANIES,
    RecordingTarget,
    confirm,
    prepare,
    runtime,
)
from test_zero_touch_database_happy_path import sandbox_settings

from app.connectors.errors import MutationOutcomeUncertainError, MutationUncertaintyReason
from app.connectors.goldtier_xpi import (
    GoldTierXpiHttpResponse,
    GoldTierXpiResponseDecodeError,
    GoldTierXpiResponseTooLargeError,
)
from app.domain.models import SafeError, WorkflowState
from app.domain.target_submission import (
    GoldTierExecutionClassification,
    GoldTierExecutionLedgerState,
    GoldTierRecoveryOrigin,
    GoldTierSearchResolution,
    GoldTierTargetOutcome,
)
from app.domain.target_submission import (
    GoldTierOperationMarker as Op,
)
from app.main import create_app
from app.services.clm_errors import ClmRequestError
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator
from app.services.zero_touch_repository import (
    InMemoryZeroTouchAutomationRepository,
    ZeroTouchRepositoryConflictError,
)


def normal_policy_fixture(*, amend=False, failure=None):
    transport = FakeXpiTransport(
        [
            GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
            failure or httpx.ReadTimeout("PRIVATE_POLICY_ERROR"),
        ]
    )
    service = _xpi_onboarding_service(transport, reviewed_test_enrichment=amend)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    service.advance_incremental_submission_input(
        submission,
        search_resolution=GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )
    with pytest.raises(MutationOutcomeUncertainError):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    return service, case, submission, transport


def evidence(case, submission):
    return dict(
        submission_input=submission,
        recovered_party_id="12345",
        legal_name=case.entity.legal_name,
        registration_number=case.requested_uen,
        country_of_incorporation=case.entity.country_of_incorporation,
        provider_policy=submission.target_policy.policy.value,
        provider_policy_status="Requested",
        actor_id="director-test",
        origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
    )


@pytest.mark.parametrize("historical", [False, True])
@pytest.mark.parametrize("amend", [False, True])
def test_both_shell_predecessors_recover_once_and_continue_exact_prefix(historical, amend):
    service, case, submission, transport = (
        _uncertain_policy_fixture() if historical else normal_policy_fixture(amend=amend)
    )
    before = service.get_target_execution_entry(submission.submission_id)
    calls = deepcopy(transport.calls)
    recovered = service.recover_uncertain_policy_from_provider(**evidence(case, submission))
    assert recovered.attempted_operations == (Op.SEARCH, Op.SHELL, Op.POLICY)
    assert recovered.lifecycle_resolved_operations == recovered.attempted_operations
    assert recovered.definitively_completed_operations == (
        (Op.SEARCH,) if historical else (Op.SEARCH, Op.SHELL)
    )
    assert recovered.shell_status == before.shell_status
    assert recovered.provider_verified_recovery == before.provider_verified_recovery
    assert recovered.policy_id is None
    assert recovered.provider_verified_policy_recovery.operation == Op.POLICY
    assert recovered.provider_verified_policy_recovery.replayed is False
    assert recovered.provider_verified_policy_recovery.original_outcome_uncertain is True
    assert recovered.policy_status == "PROVIDER_VERIFIED_REQUESTED"
    updated = service.get_case(case.case_id)
    assert updated.state == "GT_POLICY_CREATED"
    assert updated.goldtier_result.shell_status == before.shell_status
    assert updated.goldtier_result.policy_id is None
    assert service.recover_uncertain_policy_from_provider(**evidence(case, submission)) == recovered
    assert transport.calls == calls
    requires_amend = historical or amend
    transport.responses.extend(
        ([GoldTierXpiHttpResponse(status_code=200, body={})] if requires_amend else [])
        + [GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}])]
    )
    receipt = None
    for _ in range(2):
        receipt = service.advance_incremental_submission_input(
            submission,
            search_resolution=GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
        if receipt is not None:
            break
    assert receipt is not None and receipt.classification == "SUCCESS"
    assert len([c for c in transport.calls if str(c["url"]).endswith("/createPolicy")]) == 1
    assert len([c for c in transport.calls if str(c["url"]).endswith("/amendCustomer")]) == (
        1 if requires_amend else 0
    )
    final = service.get_target_execution_entry(submission.submission_id)
    assert final.submission_input == before.submission_input
    assert Op.POLICY not in final.definitively_completed_operations


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("recovered_party_id", "OTHER-ID"),
        ("legal_name", "OTHER NAME"),
        ("registration_number", "202499999Z"),
        ("country_of_incorporation", "AU"),
        ("provider_policy", "Australia"),
        ("provider_policy_status", "Active"),
        ("provider_policy_status", "PRIVATE_UNSUPPORTED_STATUS"),
    ],
)
def test_conflicting_provider_evidence_is_rejected_without_calls_or_writes(field, value):
    service, case, submission, transport = normal_policy_fixture()
    before = service.get_target_execution_entry(submission.submission_id)
    case_before = service.get_case(case.case_id)
    calls = deepcopy(transport.calls)
    supplied = {**evidence(case, submission), field: value}
    with pytest.raises(ValueError):
        service.recover_uncertain_policy_from_provider(**supplied)
    assert service.get_target_execution_entry(submission.submission_id) == before
    assert service.get_case(case.case_id) == case_before and transport.calls == calls


@pytest.mark.parametrize(
    "shape",
    ["not_attempted", "resolved", "amend", "readback", "outcome", "receipt", "wrong_shell_status"],
)
def test_invalid_recovery_prefix_or_terminal_ledger_is_rejected(shape):
    service, case, submission, transport = normal_policy_fixture()
    before = service.get_target_execution_entry(submission.submission_id)
    changes = {}
    if shape == "not_attempted":
        changes["attempted_operations"] = (Op.SEARCH, Op.SHELL)
    elif shape == "resolved":
        changes.update(
            completed_operations=before.attempted_operations,
            resolved_operations=before.attempted_operations,
            policy_status="POLICY_CREATED",
        )
    elif shape in {"amend", "readback"}:
        changes["attempted_operations"] = (
            *before.attempted_operations,
            Op.AMEND if shape == "amend" else Op.READBACK,
        )
    elif shape == "wrong_shell_status":
        changes["shell_status"] = "SHELL_FAILED"
    else:
        outcome = GoldTierTargetOutcome(
            submission_id=submission.submission_id,
            case_id=case.case_id,
            correlation_id=submission.correlation_id,
            input_fingerprint=sha256(submission.model_dump_json().encode()).hexdigest(),
            idempotency_fingerprint=sha256(
                submission.idempotency.model_dump_json().encode()
            ).hexdigest(),
            classification=GoldTierExecutionClassification.FAILED,
            onboarding_state=WorkflowState.FAILED,
            completed_operations=before.attempted_operations,
            error_code="GT_OPERATION_FAILED",
            error_message="Controlled synthetic failure.",
        )
        changes.update(
            target_outcome=outcome,
            completed_operations=before.attempted_operations,
            resolved_operations=before.attempted_operations,
            state=GoldTierExecutionLedgerState.TARGET_OUTCOME_RECORDED,
        )
        if shape == "receipt":
            changes.update(
                receipt=service._build_execution_receipt(submission, outcome),
                state=GoldTierExecutionLedgerState.FINALIZED,
            )
    candidate = before.model_copy(update=changes)
    service._target_executions.replace(
        candidate, expected_state="IN_PROGRESS", expected_attempted=before.attempted_operations
    )
    calls = deepcopy(transport.calls)
    with pytest.raises(ValueError):
        service.recover_uncertain_policy_from_provider(**evidence(case, submission))
    assert service.get_target_execution_entry(submission.submission_id) == candidate
    assert transport.calls == calls


def test_current_canonical_identity_and_locked_reauthorization_are_required():
    service, case, submission, transport = normal_policy_fixture()
    before = service.get_target_execution_entry(submission.submission_id)
    calls = deepcopy(transport.calls)

    def deny():
        raise PermissionError("controlled authorization denial")

    with pytest.raises(PermissionError):
        service.recover_uncertain_policy_from_provider(
            **evidence(case, submission), reauthorize=deny
        )
    changed = service.get_case(case.case_id)
    changed.entity.legal_name = "OTHER CURRENT NAME"
    service.repository.save(changed)
    with pytest.raises(ValueError):
        service.recover_uncertain_policy_from_provider(**evidence(case, submission))
    assert service.get_target_execution_entry(submission.submission_id) == before
    assert transport.calls == calls


class UncertainPolicyTransport(RecordingTarget):
    def request(self, method, url, **kwargs):
        if method == "POST" and url.endswith("/createPolicy"):
            self.calls.append((method, "/createPolicy", {}))
            raise httpx.ReadTimeout("PRIVATE_POLICY_ERROR")
        return super().request(method, url, **kwargs)


@pytest.mark.parametrize("historical", [False, True])
def test_manual_clm_api_recovers_both_predecessors_without_creating_automation(historical):
    transport = FakeXpiTransport(
        [
            GoldTierXpiHttpResponse(status_code=200, body=[]),
            GoldTierXpiHttpResponse(status_code=200, body=[]),
            httpx.ReadTimeout("PRIVATE_SHELL_ERROR")
            if historical
            else GoldTierXpiHttpResponse(status_code=200, body={"goldTierId": 12345}),
        ]
        + ([] if historical else [httpx.ReadTimeout("PRIVATE_POLICY_ERROR")])
    )
    seed = _xpi_onboarding_service(transport)
    snapshot = seed.create_staged_case("202400001A").policy_snapshot
    # The existing manual readiness helper accepts a RecordingGoldTier flag.
    # The actual connector and all operation results remain the fake XPI boundary.
    seed._goldtier._match_found = False
    cases, documents, ownership, clm, _, cid = make_ready_case(
        goldtier=seed._goldtier,
        goldtier_mapper=seed._goldtier_mapper,
        policy_snapshot_provider=lambda: snapshot,
    )
    with pytest.raises(ClmRequestError, match="CLM_TARGET_OUTCOME_UNCERTAIN"):
        clm.submit(case_id=cid)
    frozen = clm.get(case_id=cid).submission_snapshot.target_input
    current = cases.get_case(cid)
    if historical:
        transport.responses.extend(
            [
                GoldTierXpiHttpResponse(
                    status_code=200,
                    body=[
                        {
                            "goldTierId": 12345,
                            "legalName": current.entity.legal_name,
                        }
                    ],
                ),
                httpx.ReadTimeout("PRIVATE_POLICY_ERROR"),
            ]
        )
        cases.recover_uncertain_shell_from_provider(
            submission_input=frozen,
            recovered_party_id="12345",
            legal_name=current.entity.legal_name,
            registration_number=current.requested_uen,
            country_of_incorporation=current.entity.country_of_incorporation,
            actor_id="director-test",
            origin=GoldTierRecoveryOrigin.UNCERTAIN_DURABLE_LEDGER,
        )
        with pytest.raises(ClmRequestError, match="CLM_TARGET_OUTCOME_UNCERTAIN"):
            clm.submit(case_id=cid)
        current = cases.get_case(cid)
    automation = InMemoryZeroTouchAutomationRepository()
    zero = ZeroTouchOrchestrator(
        cases=cases,
        documents=documents,
        ownership=ownership,
        clm=clm,
        repository=automation,
    )
    original = cases.get_target_execution_entry(frozen.submission_id)
    confirmation = current.target_dispatch_confirmation
    calls = deepcopy(transport.calls)
    proof = evidence(current, frozen)
    proof.pop("submission_input")
    proof.pop("actor_id")
    proof["operation"] = "POLICY"
    with TestClient(
        create_app(
            sandbox_settings(),
            onboarding_service=cases,
            document_processing_service=documents,
            ownership_analysis_service=ownership,
            clm_orchestration_service=clm,
            zero_touch_orchestrator=zero,
        )
    ) as client:
        login_as(client, "olivia-koh")
        path = f"/api/clm/zero-touch/cases/{cid}/target-recovery"
        recovered = client.post(path, json=proof)
        assert recovered.status_code == 200, recovered.text
        retained = cases.get_target_execution_entry(frozen.submission_id)
        assert (
            retained.definitively_completed_operations == original.definitively_completed_operations
        )
        assert retained.provider_verified_recovery == original.provider_verified_recovery
        assert retained.shell_status == original.shell_status
        assert retained.lifecycle_resolved_operations == (Op.SEARCH, Op.SHELL, Op.POLICY)
        assert retained.submission_input == frozen and retained.policy_id is None
        assert client.post(path, json=proof).status_code == 200
        assert cases.get_target_execution_entry(frozen.submission_id) == retained
        assert automation.get_for_case(cid) is None
        assert cases.get_case(cid).target_dispatch_confirmation == confirmation
        assert transport.calls == calls
        transport.responses.extend(
            [
                GoldTierXpiHttpResponse(status_code=200, body={}),
                GoldTierXpiHttpResponse(status_code=200, body=[{"goldTierId": 12345}]),
            ]
        )
        completed = client.post(f"/api/clm/cases/{cid}/submit")
        assert completed.status_code == 200, completed.text
        assert completed.json()["status"] == "MOCK_GOLDTIER_SUBMITTED"
        final = cases.get_target_execution_entry(frozen.submission_id)
        assert final.submission_input == frozen
        assert cases.get_case(cid).target_dispatch_confirmation == confirmation
        assert automation.get_for_case(cid) is None
        assert [c["method"] for c in transport.calls[len(calls) :]] == ["POST", "GET"]
        assert len([c for c in transport.calls if str(c["url"]).endswith("/createPolicy")]) == 1
        assert len([c for c in transport.calls if str(c["url"]).endswith("/customers/create")]) == 1


def recovery_payload(current):
    entity = current["case"]["entity"]
    return dict(
        operation="POLICY",
        recovered_party_id=current["target_submission"]["goldtier_id"],
        legal_name=entity["legal_name"],
        registration_number=entity["registration_number"],
        country_of_incorporation=entity["country_of_incorporation"],
        provider_policy="Singapore",
        provider_policy_status="Requested",
        origin="UNCERTAIN_DURABLE_LEDGER",
    )


def login_as(client, user):
    response = client.post("/api/auth/login", json={"user_id": user, "password": TEST_PASSWORD})
    assert response.status_code == 200
    client._phase13_csrf = response.json()["csrf_token"]
    client._phase13_authenticated = True


def test_api_recovery_reconciles_failure_without_calls_then_explicit_resume_completes():
    target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
    with runtime(target=target) as (client, bundle, _, acra):
        current = confirm(client, prepare(client, COMPANIES[0]))
        cid = UUID(current["case"]["case_id"])
        path = f"/api/clm/zero-touch/cases/{cid}"
        original = bundle.target_executions.list_for_case(cid)[0]
        original_confirmation = bundle.onboarding.get(cid).target_dispatch_confirmation
        failure = bundle.automation.get_for_case(cid).events[-1]
        calls = deepcopy(target.calls)
        login_as(client, "olivia-koh")
        result = client.post(path + "/target-recovery", json=recovery_payload(current))
        assert result.status_code == 200, result.text
        assert result.json()["definitively_completed_operations"] == ["SEARCH", "SHELL"]
        assert result.json()["lifecycle_resolved_operations"] == ["SEARCH", "SHELL", "POLICY"]
        assert target.calls == calls
        after = bundle.automation.get_for_case(cid)
        assert after.status == "RECOVERY_PENDING" and after.technical_failure is None
        assert failure in after.events
        assert (
            client.post(path + "/target-recovery", json=recovery_payload(current)).status_code
            == 200
        )
        assert bundle.automation.get_for_case(cid) == after
        assert target.calls == calls
        resumed = client.post(path + "/resume")
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["status"] == "COMPLETED"
        final = bundle.target_executions.list_for_case(cid)
        assert len(final) == 1 and final[0].submission_input == original.submission_input
        assert final[0].shell_status == "SHELL_CREATED"
        assert bundle.onboarding.get(cid).target_dispatch_confirmation == original_confirmation
        assert [c[1] for c in target.calls[len(calls) :]] == [
            "/synthetic/gt-xpi/v1/customers/search"
        ]
        assert len([c for c in target.calls if c[1].endswith("/createPolicy")]) == 1
        assert len([c for c in target.calls if c[1].endswith("/customers/create")]) == 1
        assert all(not c[1].endswith("/amendCustomer") for c in target.calls)
        assert acra.calls == []


@pytest.mark.parametrize(("user", "expected"), [("maya-lim", 403), ("hr-admin", 404)])
def test_recovery_api_preserves_capability_and_hr_case_access(user, expected):
    target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
    with runtime(target=target) as (client, bundle, _, _):
        current = confirm(client, prepare(client, COMPANIES[0]))
        cid = UUID(current["case"]["case_id"])
        original = bundle.target_executions.list_for_case(cid)
        calls = deepcopy(target.calls)
        login_as(client, user)
        result = client.post(
            f"/api/clm/zero-touch/cases/{cid}/target-recovery", json=recovery_payload(current)
        )
        assert result.status_code == expected
        assert bundle.target_executions.list_for_case(cid) == original and target.calls == calls


def test_policy_recovery_cannot_clear_an_unrelated_technical_failure():
    target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
    with runtime(target=target) as (client, bundle, _, _):
        current = confirm(client, prepare(client, COMPANIES[0]))
        cid = UUID(current["case"]["case_id"])
        record = bundle.automation.get_for_case(cid)
        record.technical_failure = SafeError(
            code="ZERO_TOUCH_UNEXPECTED_FAILURE",
            message="Controlled unrelated failure.",
        )
        bundle.automation.save(record, expected_version=record.version)
        original = bundle.target_executions.list_for_case(cid)
        calls = deepcopy(target.calls)
        login_as(client, "olivia-koh")
        projected = client.get(f"/api/clm/zero-touch/cases/{cid}").json()
        assert projected["target_submission"]["recovery_available"] is False
        assert projected["target_submission"]["recovery_operation"] is None
        result = client.post(
            f"/api/clm/zero-touch/cases/{cid}/target-recovery", json=recovery_payload(current)
        )
        assert result.status_code == 422
        assert bundle.target_executions.list_for_case(cid) == original and target.calls == calls


@pytest.mark.parametrize("failed_status", ["RESUMING", "RECOVERY_PENDING"])
def test_partial_automation_checkpoint_can_retry_locally_without_provider_calls(
    monkeypatch,
    failed_status,
):
    target = UncertainPolicyTransport(COMPANIES[0].name, COMPANIES[0].uen)
    with runtime(target=target) as (client, bundle, _, _):
        current = confirm(client, prepare(client, COMPANIES[0]))
        cid = UUID(current["case"]["case_id"])
        path = f"/api/clm/zero-touch/cases/{cid}/target-recovery"
        save = bundle.automation.save
        failed = False

        def fail_once(record, *, expected_version):
            nonlocal failed
            if not failed and record.status == failed_status:
                failed = True
                raise ZeroTouchRepositoryConflictError
            return save(record, expected_version=expected_version)

        monkeypatch.setattr(bundle.automation, "save", fail_once)
        calls = deepcopy(target.calls)
        login_as(client, "olivia-koh")
        first = client.post(path, json=recovery_payload(current))
        assert first.status_code == 409
        retained = bundle.target_executions.list_for_case(cid)[0]
        assert retained.provider_verified_policy_recovery is not None
        second = client.post(path, json=recovery_payload(current))
        assert second.status_code == 200
        assert bundle.automation.get_for_case(cid).status == "RECOVERY_PENDING"
        assert bundle.target_executions.list_for_case(cid) == (retained,)
        assert target.calls == calls


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (httpx.ReadTimeout("PRIVATE_POLICY_ERROR"), MutationUncertaintyReason.TIMEOUT),
        (httpx.ConnectError("PRIVATE_POLICY_ERROR"), MutationUncertaintyReason.TRANSPORT),
        (GoldTierXpiResponseDecodeError(), MutationUncertaintyReason.RESPONSE_DECODE),
        (GoldTierXpiResponseTooLargeError(), MutationUncertaintyReason.RESPONSE_TOO_LARGE),
        (
            GoldTierXpiHttpResponse(status_code=503, body={"private": "PRIVATE_POLICY_ERROR"}),
            MutationUncertaintyReason.UNEXPECTED_STATUS,
        ),
        (RuntimeError("PRIVATE_POLICY_ERROR"), MutationUncertaintyReason.UNKNOWN),
    ],
)
def test_safe_uncertainty_reason_is_retained_without_private_detail_or_replay(failure, reason):
    service, case, submission, transport = normal_policy_fixture(failure=failure)
    current = service.get_case(case.case_id)
    assert current.events[-1].code == f"GT_TARGET_OUTCOME_UNCERTAIN_{reason.value}"
    assert "PRIVATE_POLICY_ERROR" not in current.model_dump_json()
    before = service.get_target_execution_entry(submission.submission_id)
    calls = deepcopy(transport.calls)
    with pytest.raises(MutationOutcomeUncertainError):
        service.advance_incremental_submission_input(
            submission,
            search_resolution=GoldTierSearchResolution.NO_MATCH,
            selected_party_id=None,
        )
    assert service.get_target_execution_entry(submission.submission_id) == before
    assert transport.calls == calls
