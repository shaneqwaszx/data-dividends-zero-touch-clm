"""Deterministic evidence for the test-only Camunda observation contract."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import cast
from uuid import UUID, uuid4

import pytest
from camunda_observer_contract_support import (
    JOB_TYPE,
    CompletionMode,
    FailurePolicy,
    FakeCaseReadClient,
    FakeEngineClient,
    FakeHttpResponse,
    ForbiddenCallSpy,
    HandlerState,
    ObservationContractHandler,
    ObservationFailureCode,
    ObservationJob,
    ObserverReadTimeout,
    ObserverTransportFailure,
)

CASE_REF = UUID("00000000-0000-4000-8000-000000000123")
FAILURE_POLICY = FailurePolicy(retries=2, backoff_ms=250)
MAX_BODY_BYTES = 4_096
PROHIBITED_MARKERS = {
    "Synthetic Secret Name",
    "202400001A",
    "TEAM_A",
    "Bearer fake-token",
    "raw-document-body",
    "private-exception-detail",
    "GOLDTIER-PARTY-123",
}


def _broad_response(
    *,
    case_ref: UUID = CASE_REF,
    automation_status: object = "RUNNING",
    current_stage: object = "DOCUMENT",
    automation_version: object = 7,
    clm_status: object = "COLLECTING_EVIDENCE",
    clm_version: object = 3,
    unobserved_marker: str = "first-unobserved-state",
) -> dict[str, object]:
    return {
        "case": {
            "case_id": str(case_ref),
            "requested_uen": "202400001A",
            "entity": {"legal_name": "Synthetic Secret Name"},
            "team": {"team_id": "TEAM_A"},
        },
        "status": automation_status,
        "current_stage": current_stage,
        "version": automation_version,
        "clm": {
            "status": clm_status,
            "version": clm_version,
            "documents": ["raw-document-body"],
            "target_id": "GOLDTIER-PARTY-123",
        },
        "reconciliation": {"detail": "private-exception-detail"},
        "debug": {"authorization": "Bearer fake-token", "marker": unobserved_marker},
    }


def _response(body: Mapping[str, object], *, status_code: int = 200) -> FakeHttpResponse:
    return FakeHttpResponse(status_code=status_code, body=json.dumps(body).encode())


def _handler(
    scripted: Sequence[FakeHttpResponse | BaseException],
    *,
    engine: FakeEngineClient | None = None,
    max_body_bytes: int = MAX_BODY_BYTES,
) -> tuple[ObservationContractHandler, FakeCaseReadClient, FakeEngineClient]:
    reader = FakeCaseReadClient(scripted=list(scripted))
    active_engine = engine or FakeEngineClient()
    return (
        ObservationContractHandler(
            reader,
            active_engine,
            max_body_bytes=max_body_bytes,
            failure_policy=FAILURE_POLICY,
        ),
        reader,
        active_engine,
    )


def _job(
    *,
    key: int = 1,
    job_type: str = JOB_TYPE,
    variables: Mapping[str, object] | None = None,
) -> ObservationJob:
    return ObservationJob(
        job_key=key,
        job_type=job_type,
        variables=variables if variables is not None else {"caseRef": str(CASE_REF)},
    )


def _assert_sanitized(value: object) -> None:
    serialized = repr(value)
    assert all(marker not in serialized for marker in PROHIBITED_MARKERS)


def test_matching_reads_complete_with_only_allowlisted_projection() -> None:
    broad = _broad_response()
    handler, reader, engine = _handler([_response(broad), _response(broad)])

    result = handler.handle(_job())

    assert result.state == HandlerState.COMPLETED
    assert reader.read_case_refs == [CASE_REF, CASE_REF]
    assert engine.failures == []
    assert len(engine.completions) == 1
    assert engine.completions[0].variables == {
        "clmObservation": {
            "schemaVersion": 1,
            "caseRef": str(CASE_REF),
            "availability": "OBSERVED",
            "automationStatus": "RUNNING",
            "currentStage": "DOCUMENT",
            "automationVersion": 7,
            "clmVersion": 3,
        }
    }
    _assert_sanitized(engine.completions)


def test_matching_selected_fields_are_not_claimed_as_atomic_snapshot() -> None:
    first = _broad_response(unobserved_marker="first-unobserved-state")
    second = _broad_response(
        clm_status="READY_FOR_MOCK_SUBMISSION",
        unobserved_marker="second-unobserved-state",
    )
    handler, _, engine = _handler([_response(first), _response(second)])

    result = handler.handle(_job())

    assert result.state == HandlerState.COMPLETED
    assert first != second
    assert engine.completions[0].variables["clmObservation"] == result.observation
    # Completion means only that the selected fields matched in two observations.  The
    # unobserved aggregate demonstrably changed and no atomic snapshot is asserted.


@pytest.mark.parametrize(
    ("field_path", "changed_value"),
    [
        (("status",), "WAITING_FOR_REVIEW"),
        (("current_stage",), "OWNERSHIP"),
        (("version",), 8),
        (("clm", "version"), 4),
    ],
)
def test_each_selected_projection_mismatch_fails_without_completion(
    field_path: tuple[str, ...], changed_value: object
) -> None:
    first = _broad_response()
    second = deepcopy(first)
    target = second
    for part in field_path[:-1]:
        target = cast(dict[str, object], target[part])
    target[field_path[-1]] = changed_value
    handler, reader, engine = _handler([_response(first), _response(second)])

    result = handler.handle(_job())

    assert result.failure_code == ObservationFailureCode.CASE_CHANGED_DURING_OBSERVATION
    assert reader.read_case_refs == [CASE_REF, CASE_REF]
    assert engine.completions == []
    assert len(engine.failures) == 1


@pytest.mark.parametrize(
    ("job_type", "variables"),
    [
        ("clm.observe-case.v2", {"caseRef": str(CASE_REF)}),
        (JOB_TYPE, {}),
        (JOB_TYPE, {"caseRef": str(CASE_REF), "clmObservation": {"stale": True}}),
        (JOB_TYPE, {"caseRef": str(CASE_REF), "endpoint": "https://example.invalid"}),
        (JOB_TYPE, {"caseRef": f"https://example.invalid/{CASE_REF}"}),
        (JOB_TYPE, {"caseRef": f"../{CASE_REF}"}),
        (JOB_TYPE, {"caseRef": 123}),
    ],
)
def test_invalid_job_or_input_has_zero_reads_and_no_success_variables(
    job_type: str, variables: Mapping[str, object]
) -> None:
    handler, reader, engine = _handler([])

    result = handler.handle(_job(job_type=job_type, variables=variables))

    assert result.state == HandlerState.FAILED
    assert reader.read_case_refs == []
    assert engine.completions == []
    assert len(engine.failures) == 1
    assert engine.failures[0].retries == FAILURE_POLICY.retries
    assert engine.failures[0].backoff_ms == FAILURE_POLICY.backoff_ms


@pytest.mark.parametrize("description", ["missing", "inaccessible", "deleted"])
def test_safe_first_404_is_one_read_and_non_enumerating(description: str) -> None:
    handler, reader, engine = _handler([FakeHttpResponse(status_code=404)])

    result = handler.handle(_job(key=len(description)))

    assert result.state == HandlerState.COMPLETED
    assert len(reader.read_case_refs) == 1
    assert engine.completions[0].variables == {
        "clmObservation": {
            "schemaVersion": 1,
            "caseRef": str(CASE_REF),
            "availability": "NOT_AVAILABLE",
        }
    }


def test_second_read_404_discards_the_first_observation() -> None:
    handler, reader, engine = _handler(
        [_response(_broad_response()), FakeHttpResponse(status_code=404)]
    )

    result = handler.handle(_job())

    assert result.state == HandlerState.COMPLETED
    assert len(reader.read_case_refs) == 2
    observation = cast(dict[str, object], engine.completions[0].variables["clmObservation"])
    assert observation == {
        "schemaVersion": 1,
        "caseRef": str(CASE_REF),
        "availability": "NOT_AVAILABLE",
    }
    assert "automationStatus" not in observation
    assert "currentStage" not in observation
    assert "automationVersion" not in observation
    assert "clmVersion" not in observation


@pytest.mark.parametrize("status_code", [401, 403])
@pytest.mark.parametrize("read_index", [0, 1])
def test_authentication_failures_are_never_case_absence(status_code: int, read_index: int) -> None:
    scripted = [FakeHttpResponse(status_code=status_code)]
    if read_index == 1:
        scripted.insert(0, _response(_broad_response()))
    handler, reader, engine = _handler(scripted)

    result = handler.handle(_job())

    assert result.failure_code == ObservationFailureCode.AUTHENTICATION_CONFIGURATION_FAILURE
    assert len(reader.read_case_refs) == read_index + 1
    assert engine.completions == []


@pytest.mark.parametrize(
    "failure",
    [
        ObserverReadTimeout("private-exception-detail"),
        ObserverTransportFailure("Bearer fake-token"),
        FakeHttpResponse(status_code=500, body=b"Synthetic Secret Name"),
        FakeHttpResponse(status_code=503, body=b"202400001A"),
    ],
)
@pytest.mark.parametrize("read_index", [0, 1])
def test_backend_failures_on_either_read_are_sanitized_and_not_retried_internally(
    failure: FakeHttpResponse | BaseException, read_index: int
) -> None:
    scripted: list[FakeHttpResponse | BaseException] = [failure]
    if read_index == 1:
        scripted.insert(0, _response(_broad_response()))
    handler, reader, engine = _handler(scripted)

    result = handler.handle(_job())

    assert result.failure_code == ObservationFailureCode.BACKEND_UNAVAILABLE
    assert len(reader.read_case_refs) == read_index + 1
    assert engine.completions == []
    assert len(engine.failures) == 1
    _assert_sanitized(result)
    _assert_sanitized(engine.failures)


@pytest.mark.parametrize(
    ("field_path", "changed_value", "remove", "expected_code"),
    [
        (("case", "case_id"), str(uuid4()), False, "CASE_ID_MISMATCH"),
        (("status",), "UNKNOWN", False, "RESPONSE_MALFORMED"),
        (("current_stage",), "UNKNOWN", False, "RESPONSE_MALFORMED"),
        (("version",), True, False, "RESPONSE_MALFORMED"),
        (("clm", "version"), "3", False, "RESPONSE_MALFORMED"),
        (("current_stage",), None, True, "RESPONSE_MALFORMED"),
        (("clm", "version"), None, True, "RESPONSE_MALFORMED"),
    ],
)
def test_wrong_identity_enum_type_or_missing_field_fails_closed(
    field_path: tuple[str, ...],
    changed_value: object,
    remove: bool,
    expected_code: str,
) -> None:
    body = _broad_response()
    target = body
    for part in field_path[:-1]:
        target = cast(dict[str, object], target[part])
    if remove:
        target.pop(field_path[-1])
    else:
        target[field_path[-1]] = changed_value
    handler, reader, engine = _handler([_response(body)])

    result = handler.handle(_job())

    assert result.failure_code == ObservationFailureCode(expected_code)
    assert len(reader.read_case_refs) == 1
    assert engine.completions == []
    _assert_sanitized(result)


@pytest.mark.parametrize(
    "body",
    [b"not-json private-exception-detail", b"[]", b'{"case": null}'],
)
def test_malformed_response_fails_closed_without_body_diagnostics(body: bytes) -> None:
    handler, reader, engine = _handler([FakeHttpResponse(status_code=200, body=body)])

    result = handler.handle(_job())

    assert result.failure_code == ObservationFailureCode.RESPONSE_MALFORMED
    assert len(reader.read_case_refs) == 1
    assert engine.completions == []
    _assert_sanitized(result)


def test_oversized_response_is_rejected_before_parsing() -> None:
    invalid_large_body = b"{" + b"Bearer fake-token" * 16 + b"}"
    handler, reader, engine = _handler(
        [FakeHttpResponse(status_code=200, body=invalid_large_body)], max_body_bytes=32
    )

    result = handler.handle(_job())

    assert result.failure_code == ObservationFailureCode.RESPONSE_TOO_LARGE
    assert len(reader.read_case_refs) == 1
    assert engine.completions == []
    _assert_sanitized(result)


def test_redelivery_performs_a_fresh_observation_without_stale_output() -> None:
    reader = FakeCaseReadClient(
        scripted=[
            _response(_broad_response(automation_version=7)),
            _response(_broad_response(automation_version=7)),
            _response(_broad_response(automation_version=8, current_stage="OWNERSHIP")),
            _response(_broad_response(automation_version=8, current_stage="OWNERSHIP")),
        ]
    )
    engine = FakeEngineClient()
    handler = ObservationContractHandler(
        reader,
        engine,
        max_body_bytes=MAX_BODY_BYTES,
        failure_policy=FAILURE_POLICY,
    )

    first = handler.handle(_job(key=1))
    second = handler.handle(_job(key=2))

    assert first.state == second.state == HandlerState.COMPLETED
    assert len(reader.read_case_refs) == 4
    first_observation = cast(dict[str, object], engine.completions[0].variables["clmObservation"])
    second_observation = cast(dict[str, object], engine.completions[1].variables["clmObservation"])
    assert first_observation["automationVersion"] == 7
    assert second_observation["automationVersion"] == 8
    assert second_observation["currentStage"] == "OWNERSHIP"


def test_overlapping_fake_workers_have_one_completion_winner() -> None:
    engine = FakeEngineClient()
    first_handler, first_reader, _ = _handler(
        [_response(_broad_response()), _response(_broad_response())], engine=engine
    )
    second_handler, second_reader, _ = _handler(
        [_response(_broad_response()), _response(_broad_response())], engine=engine
    )

    winner = first_handler.handle(_job(key=77))
    loser = second_handler.handle(_job(key=77))

    assert winner.state == HandlerState.COMPLETED
    assert loser.state == HandlerState.COMPLETION_REJECTED
    assert len(first_reader.read_case_refs) == len(second_reader.read_case_refs) == 2
    assert len(engine.completions) == 2
    assert engine.failures == []


def test_lost_completion_acknowledgement_is_ambiguous_and_not_repeated_or_failed() -> None:
    engine = FakeEngineClient(completion_modes={88: CompletionMode.ACKNOWLEDGEMENT_LOST})
    handler, reader, _ = _handler(
        [_response(_broad_response()), _response(_broad_response())], engine=engine
    )

    result = handler.handle(_job(key=88))

    assert result.state == HandlerState.COMPLETION_ACKNOWLEDGEMENT_AMBIGUOUS
    assert len(reader.read_case_refs) == 2
    assert len(engine.completions) == 1
    assert engine.failures == []


def test_rejected_completion_does_not_trigger_contradictory_fail_command() -> None:
    engine = FakeEngineClient(completion_modes={99: CompletionMode.REJECTED})
    handler, _, _ = _handler(
        [_response(_broad_response()), _response(_broad_response())], engine=engine
    )

    result = handler.handle(_job(key=99))

    assert result.state == HandlerState.COMPLETION_REJECTED
    assert len(engine.completions) == 1
    assert engine.failures == []


def test_reference_handler_has_zero_forbidden_mutation_provider_or_repository_calls() -> None:
    forbidden = ForbiddenCallSpy()
    reader = FakeCaseReadClient(
        scripted=[_response(_broad_response()), _response(_broad_response())],
        forbidden_spy=forbidden,
    )
    engine = FakeEngineClient()
    handler = ObservationContractHandler(
        reader,
        engine,
        max_body_bytes=MAX_BODY_BYTES,
        failure_policy=FAILURE_POLICY,
    )

    result = handler.handle(_job())

    assert result.state == HandlerState.COMPLETED
    assert forbidden.calls == []
    assert len(reader.read_case_refs) == 2
    assert len(engine.completions) == 1
    assert all(
        not hasattr(reader, operation)
        for operation in (
            "create",
            "start",
            "resume",
            "review",
            "replace",
            "resolve",
            "refresh",
            "evaluate",
            "submit",
            "delete",
            "provider_call",
            "repository_mutation",
        )
    )


@pytest.mark.parametrize(
    "operation",
    [
        "create",
        "start",
        "resume",
        "review",
        "replace",
        "resolve",
        "refresh",
        "evaluate",
        "submit",
        "delete",
        "provider_call",
        "repository_mutation",
    ],
)
def test_forbidden_call_spy_fails_if_invoked(operation: str) -> None:
    forbidden = ForbiddenCallSpy()

    with pytest.raises(AssertionError, match="forbidden observer operation"):
        forbidden.invoke(operation)

    assert forbidden.calls == [operation]


def test_failure_policy_is_finite_and_does_not_sleep_or_poll() -> None:
    handler, reader, engine = _handler([ObserverReadTimeout()])

    result = handler.handle(_job())

    assert result.state == HandlerState.FAILED
    assert len(reader.read_case_refs) == 1
    assert len(engine.failures) == 1
    assert engine.failures[0].retries == 2
    assert engine.failures[0].backoff_ms == 250
