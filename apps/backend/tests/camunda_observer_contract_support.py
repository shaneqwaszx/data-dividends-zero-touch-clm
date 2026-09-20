"""Test-only reference model for the offline Camunda observation contract.

This module deliberately lives under ``tests``.  It models one handler invocation
against fake ports; it is not a worker, transport, authentication client, or runtime
composition component.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, cast
from uuid import UUID

from app.domain.zero_touch import AutomationStage, AutomationStatus

JOB_TYPE = "clm.observe-case.v1"
OBSERVATION_SCHEMA_VERSION = 1


class ObservationFailureCode(StrEnum):
    INVALID_JOB = "INVALID_JOB"
    INVALID_INPUT = "INVALID_INPUT"
    AUTHENTICATION_CONFIGURATION_FAILURE = "AUTHENTICATION_CONFIGURATION_FAILURE"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    RESPONSE_MALFORMED = "RESPONSE_MALFORMED"
    RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"
    CASE_ID_MISMATCH = "CASE_ID_MISMATCH"
    CASE_CHANGED_DURING_OBSERVATION = "CASE_CHANGED_DURING_OBSERVATION"
    UNEXPECTED_HTTP_STATUS = "UNEXPECTED_HTTP_STATUS"


class HandlerState(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPLETION_REJECTED = "COMPLETION_REJECTED"
    COMPLETION_ACKNOWLEDGEMENT_AMBIGUOUS = "COMPLETION_ACKNOWLEDGEMENT_AMBIGUOUS"


class CompletionMode(StrEnum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REJECTED = "REJECTED"
    ACKNOWLEDGEMENT_LOST = "ACKNOWLEDGEMENT_LOST"


class ObserverReadTimeout(Exception):
    """Synthetic, sanitized fake-port timeout."""


class ObserverTransportFailure(Exception):
    """Synthetic, sanitized fake-port transport failure."""


class CompletionRejected(Exception):
    """The fake engine rejected a completion command."""


class CompletionAcknowledgementLost(Exception):
    """The fake engine outcome is intentionally ambiguous to the handler."""


@dataclass(frozen=True)
class FakeHttpResponse:
    status_code: int
    body: bytes = b""


@dataclass(frozen=True)
class ObservationJob:
    job_key: int
    job_type: str
    variables: Mapping[str, object]


@dataclass(frozen=True)
class FailurePolicy:
    retries: int
    backoff_ms: int

    def __post_init__(self) -> None:
        if self.retries < 0 or self.retries > 100:
            raise ValueError("retries must be finite and between 0 and 100")
        if self.backoff_ms < 0 or self.backoff_ms > 86_400_000:
            raise ValueError("backoff_ms must be finite and at most one day")


@dataclass(frozen=True)
class FailureCommand:
    job_key: int
    code: ObservationFailureCode
    retries: int
    backoff_ms: int


@dataclass(frozen=True)
class CompletionCommand:
    job_key: int
    variables: Mapping[str, object]


@dataclass(frozen=True)
class HandlerResult:
    state: HandlerState
    failure_code: ObservationFailureCode | None = None
    observation: Mapping[str, object] | None = None


@dataclass(frozen=True)
class _SelectedProjection:
    case_ref: str
    automation_status: str
    current_stage: str
    automation_version: int
    clm_version: int


class _NotAvailable:
    pass


NOT_AVAILABLE = _NotAvailable()


class CaseReadPort(Protocol):
    """The only application-facing capability exposed to the handler."""

    def read_case(self, case_ref: UUID) -> FakeHttpResponse: ...


class EnginePort(Protocol):
    """Minimal fake engine command boundary used by one handler invocation."""

    def complete(self, job_key: int, variables: Mapping[str, object]) -> None: ...

    def fail(
        self,
        job_key: int,
        code: ObservationFailureCode,
        *,
        retries: int,
        backoff_ms: int,
    ) -> None: ...


@dataclass
class FakeCaseReadClient:
    scripted: list[FakeHttpResponse | BaseException]
    read_case_refs: list[UUID] = field(default_factory=list)
    forbidden_spy: ForbiddenCallSpy | None = None

    def read_case(self, case_ref: UUID) -> FakeHttpResponse:
        self.read_case_refs.append(case_ref)
        if not self.scripted:
            raise AssertionError("unexpected extra backend read")
        item = self.scripted.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@dataclass
class ForbiddenCallSpy:
    """Fail-fast stand-in for capabilities intentionally absent from the read port."""

    calls: list[str] = field(default_factory=list)

    def invoke(self, operation: str) -> None:
        self.calls.append(operation)
        raise AssertionError(f"forbidden observer operation: {operation}")


@dataclass
class FakeEngineClient:
    completion_modes: dict[int, CompletionMode] = field(default_factory=dict)
    completions: list[CompletionCommand] = field(default_factory=list)
    failures: list[FailureCommand] = field(default_factory=list)
    completed_job_keys: set[int] = field(default_factory=set)

    def complete(self, job_key: int, variables: Mapping[str, object]) -> None:
        self.completions.append(
            CompletionCommand(job_key=job_key, variables=deepcopy(dict(variables)))
        )
        if job_key in self.completed_job_keys:
            raise CompletionRejected
        mode = self.completion_modes.get(job_key, CompletionMode.ACKNOWLEDGED)
        if mode == CompletionMode.REJECTED:
            raise CompletionRejected
        self.completed_job_keys.add(job_key)
        if mode == CompletionMode.ACKNOWLEDGEMENT_LOST:
            raise CompletionAcknowledgementLost

    def fail(
        self,
        job_key: int,
        code: ObservationFailureCode,
        *,
        retries: int,
        backoff_ms: int,
    ) -> None:
        self.failures.append(
            FailureCommand(
                job_key=job_key,
                code=code,
                retries=retries,
                backoff_ms=backoff_ms,
            )
        )


class ObservationContractHandler:
    """One bounded, synchronous, offline reference invocation."""

    def __init__(
        self,
        reader: CaseReadPort,
        engine: EnginePort,
        *,
        max_body_bytes: int,
        failure_policy: FailurePolicy,
    ) -> None:
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        self._reader = reader
        self._engine = engine
        self._max_body_bytes = max_body_bytes
        self._failure_policy = failure_policy

    def handle(self, job: ObservationJob) -> HandlerResult:
        if job.job_type != JOB_TYPE:
            return self._fail(job.job_key, ObservationFailureCode.INVALID_JOB)
        case_ref = _validated_case_ref(job.variables)
        if case_ref is None:
            return self._fail(job.job_key, ObservationFailureCode.INVALID_INPUT)

        try:
            first = self._read_selected(case_ref)
            if isinstance(first, _NotAvailable):
                return self._complete(job.job_key, _unavailable_observation(str(case_ref)))

            second = self._read_selected(case_ref)
            if isinstance(second, _NotAvailable):
                return self._complete(job.job_key, _unavailable_observation(str(case_ref)))
        except _ReadFailure as exc:
            return self._fail(job.job_key, exc.code)

        if first != second:
            return self._fail(
                job.job_key,
                ObservationFailureCode.CASE_CHANGED_DURING_OBSERVATION,
            )
        return self._complete(job.job_key, _observed_result(first))

    def _read_selected(self, case_ref: UUID) -> _SelectedProjection | _NotAvailable:
        try:
            response = self._reader.read_case(case_ref)
        except (ObserverReadTimeout, ObserverTransportFailure):
            raise _ReadFailure(ObservationFailureCode.BACKEND_UNAVAILABLE) from None

        if response.status_code == 404:
            return NOT_AVAILABLE
        if response.status_code in {401, 403}:
            raise _ReadFailure(ObservationFailureCode.AUTHENTICATION_CONFIGURATION_FAILURE)
        if 500 <= response.status_code <= 599:
            raise _ReadFailure(ObservationFailureCode.BACKEND_UNAVAILABLE)
        if response.status_code != 200:
            raise _ReadFailure(ObservationFailureCode.UNEXPECTED_HTTP_STATUS)
        if len(response.body) > self._max_body_bytes:
            raise _ReadFailure(ObservationFailureCode.RESPONSE_TOO_LARGE)

        try:
            decoded = cast(object, json.loads(response.body))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED) from None
        return _parse_projection(decoded, case_ref)

    def _complete(self, job_key: int, observation: Mapping[str, object]) -> HandlerResult:
        variables: dict[str, object] = {"clmObservation": dict(observation)}
        try:
            self._engine.complete(job_key, variables)
        except CompletionAcknowledgementLost:
            return HandlerResult(
                state=HandlerState.COMPLETION_ACKNOWLEDGEMENT_AMBIGUOUS,
                observation=observation,
            )
        except CompletionRejected:
            return HandlerResult(
                state=HandlerState.COMPLETION_REJECTED,
                observation=observation,
            )
        return HandlerResult(state=HandlerState.COMPLETED, observation=observation)

    def _fail(self, job_key: int, code: ObservationFailureCode) -> HandlerResult:
        self._engine.fail(
            job_key,
            code,
            retries=self._failure_policy.retries,
            backoff_ms=self._failure_policy.backoff_ms,
        )
        return HandlerResult(state=HandlerState.FAILED, failure_code=code)


@dataclass(frozen=True)
class _ReadFailure(Exception):
    code: ObservationFailureCode


def _validated_case_ref(variables: Mapping[str, object]) -> UUID | None:
    if set(variables) != {"caseRef"}:
        return None
    raw = variables.get("caseRef")
    if not isinstance(raw, str):
        return None
    try:
        parsed = UUID(raw)
    except ValueError:
        return None
    if raw.lower() != str(parsed):
        return None
    return parsed


def _parse_projection(decoded: object, expected_case_ref: UUID) -> _SelectedProjection:
    root = _required_mapping(decoded)
    case = _required_mapping(root.get("case"))
    clm = _required_mapping(root.get("clm"))

    returned_case_ref = _required_string(case.get("case_id"))
    try:
        parsed_returned_case_ref = UUID(returned_case_ref)
    except ValueError:
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED) from None
    if returned_case_ref.lower() != str(parsed_returned_case_ref):
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED)
    if parsed_returned_case_ref != expected_case_ref:
        raise _ReadFailure(ObservationFailureCode.CASE_ID_MISMATCH)

    automation_status = _required_string(root.get("status"))
    current_stage = _required_string(root.get("current_stage"))
    if automation_status not in {item.value for item in AutomationStatus}:
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED)
    if current_stage not in {item.value for item in AutomationStage}:
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED)

    return _SelectedProjection(
        case_ref=str(expected_case_ref),
        automation_status=automation_status,
        current_stage=current_stage,
        automation_version=_required_version(root.get("version")),
        clm_version=_required_version(clm.get("version")),
    )


def _required_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED)
    return cast(Mapping[str, object], value)


def _required_string(value: object) -> str:
    if not isinstance(value, str):
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED)
    return value


def _required_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _ReadFailure(ObservationFailureCode.RESPONSE_MALFORMED)
    return value


def _observed_result(projection: _SelectedProjection) -> dict[str, object]:
    return {
        "schemaVersion": OBSERVATION_SCHEMA_VERSION,
        "caseRef": projection.case_ref,
        "availability": "OBSERVED",
        "automationStatus": projection.automation_status,
        "currentStage": projection.current_stage,
        "automationVersion": projection.automation_version,
        "clmVersion": projection.clm_version,
    }


def _unavailable_observation(case_ref: str) -> dict[str, object]:
    return {
        "schemaVersion": OBSERVATION_SCHEMA_VERSION,
        "caseRef": case_ref,
        "availability": "NOT_AVAILABLE",
    }


def scripted_responses(
    items: Sequence[FakeHttpResponse | BaseException],
) -> list[FakeHttpResponse | BaseException]:
    """Copy an immutable-looking test script into the fake client's mutable queue."""

    return list(items)
