"""In-flight attempts stay distinct from abandoned intent; checks never mutate it."""

from uuid import uuid4

import httpx
import pytest
from test_goldtier_xpi_sandbox import (
    FakeXpiTransport,
    _confirm_service_submission,
    _xpi_onboarding_service,
)

from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse


def uncertain_service():
    transport = FakeXpiTransport([
        GoldTierXpiHttpResponse(200, []),
        httpx.ReadTimeout("synthetic timeout"),
    ])
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    with pytest.raises(Exception, match="uncertain"):
        service.execute_submission_input(submission)
    return service, case, submission, transport


def test_activity_is_published_before_intent_and_cleared_after_uncertain_exit():
    class HeldTransport(FakeXpiTransport):
        def request(self, method, url, **kwargs):
            if method == "POST":
                entry, active = service.get_target_execution_activity_snapshot(
                    submission.submission_id
                )
                assert entry is not None and entry.attempted_operations[-1] == "SHELL"
                assert active is True
                assert service.is_execution_outcome_uncertain(submission.submission_id) is False
            return super().request(method, url, **kwargs)

    transport = HeldTransport([
        GoldTierXpiHttpResponse(200, []), httpx.ReadTimeout("synthetic timeout"),
    ])
    service = _xpi_onboarding_service(transport)
    case = service.create_staged_case("202400001A")
    submission = service.build_submission_input(case, provider_mode="SANDBOX")
    _confirm_service_submission(service, submission)
    with pytest.raises(Exception, match="uncertain"):
        service.execute_submission_input(submission)
    assert service.is_target_submission_active(submission.submission_id) is False
    assert service.is_execution_outcome_uncertain(submission.submission_id) is True


@pytest.mark.parametrize(("body", "expected"), [
    ([], "NO_MATCH"),
    ([{"goldTierId": "SYNTHETIC-FOUND", "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
       "countryOfIncorporation": "SG"}], "IDENTITY_UNVERIFIED"),
    ([{"goldTierId": "SYNTHETIC-FOUND", "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
       "countryOfIncorporation": "SG", "registrationNumber": "202400001A"}],
     "CUSTOMER_IDENTITY_VERIFIED"),
    ([{"goldTierId": "SYNTHETIC-FOUND", "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
       "countryOfIncorporation": "SG", "registrationNumber": "202400002B"}],
     "IDENTITY_UNVERIFIED"),
    ([{"goldTierId": "SYNTHETIC-A"}, {"goldTierId": "SYNTHETIC-B"}], "AMBIGUOUS"),
])
def test_one_read_only_check_retains_exact_uncertain_ledger(body, expected):
    service, case, submission, transport = uncertain_service()
    original = service.get_target_execution_entry(submission.submission_id)
    transport.responses.append(GoldTierXpiHttpResponse(200, body))
    checks = []
    result = service.check_uncertain_target_status(
        case_id=case.case_id, submission_id=submission.submission_id,
        reauthorize=lambda: checks.append("fresh"),
    )
    assert checks == ["fresh"] and result.result == expected
    assert len(transport.calls) == 3 and transport.calls[-1]["method"] == "GET"
    assert service.get_target_execution_entry(submission.submission_id) == original
    assert service.is_execution_outcome_uncertain(submission.submission_id)
    assert service.get_case(case.case_id).goldtier_result is None


def test_read_only_check_timeout_is_safe_and_does_not_resolve_or_replay():
    service, case, submission, transport = uncertain_service()
    original = service.get_target_execution_entry(submission.submission_id)
    transport.responses.append(httpx.ReadTimeout("synthetic confidential-like diagnostic"))
    result = service.check_uncertain_target_status(
        case_id=case.case_id, submission_id=submission.submission_id, reauthorize=lambda: None,
    )
    assert result.result == "CHECK_FAILED"
    assert service.get_target_execution_entry(submission.submission_id) == original
    assert len(transport.calls) == 3


def test_failed_fresh_reauthorization_and_wrong_case_make_zero_new_calls():
    service, case, submission, transport = uncertain_service()
    def denied():
        raise PermissionError("synthetic revoked session")
    with pytest.raises(PermissionError):
        service.check_uncertain_target_status(
            case_id=case.case_id, submission_id=submission.submission_id, reauthorize=denied,
        )
    with pytest.raises(ValueError):
        service.check_uncertain_target_status(
            case_id=uuid4(), submission_id=submission.submission_id, reauthorize=lambda: None,
        )
    assert len(transport.calls) == 2


def test_status_check_rejects_provider_composition_drift_without_calls(monkeypatch):
    service, case, submission, transport = uncertain_service()
    monkeypatch.setattr(service._goldtier, "environment", "MOCK")
    with pytest.raises(ValueError, match="retained uncertain"):
        service.check_uncertain_target_status(
            case_id=case.case_id, submission_id=submission.submission_id, reauthorize=lambda: None,
        )
    assert len(transport.calls) == 2


def test_status_check_rejects_current_name_drift_without_calls():
    service, case, submission, transport = uncertain_service()
    current = service.get_case(case.case_id)
    current.entity = current.entity.model_copy(update={"legal_name": "SYNTHETIC CHANGED NAME"})
    service._repository.save(current)
    with pytest.raises(ValueError, match="frozen current identity"):
        service.check_uncertain_target_status(
            case_id=case.case_id, submission_id=submission.submission_id, reauthorize=lambda: None,
        )
    assert len(transport.calls) == 2
