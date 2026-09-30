"""Bounded read-only diagnostics over the application's composed ACRA connector.

This service owns no connector construction, case state, target ledger, or authorization.
The API boundary must inject the exact configured connector and enforce the existing
``PROVIDER_SANDBOX_TEST`` capability before calling it.
"""

from __future__ import annotations

import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from hashlib import sha256
from threading import BoundedSemaphore, Event, Lock
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.connectors.acra import (
    AcraAddressPayload,
    AcraCompanyPayload,
    AcraConnector,
    AcraOfficerPayload,
    AcraOwnershipPartyPayload,
)
from app.connectors.errors import (
    AcraResponseIdentityMismatchError,
    ConnectorError,
    public_connector_error,
)
from app.domain.jurisdiction import is_eligible_singapore_uen

_SAFE_HOST = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
AcraProviderId = Literal[
    "ACRA_MOCK",
    "ACRA_API_MARKETPLACE_MOCK",
    "ACRA_GENERIC_SANDBOX",
]


class AcraDiagnosticOperation(StrEnum):
    ENTITY_PROFILE = "ENTITY_PROFILE"
    OFFICERS = "OFFICERS"
    SHAREHOLDERS = "SHAREHOLDERS"
    LLP_HIGHLIGHTS = "LLP_HIGHLIGHTS"
    CAPITAL_DETAILS = "CAPITAL_DETAILS"
    RELATIONSHIPS = "RELATIONSHIPS"


class AcraDiagnosticOutcome(StrEnum):
    COMPLETE = "COMPLETE"
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    FAILED = "FAILED"
    UNSUPPORTED = "UNSUPPORTED"
    INVALID_REQUEST = "INVALID_REQUEST"
    CANCELLED = "CANCELLED"
    RATE_LIMITED = "RATE_LIMITED"


class AcraDiagnosticConfiguration(BaseModel):
    """Sanitized configuration supplied by the backend composition boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: AcraProviderId
    mode: Literal["mock", "api_marketplace_mock", "sandbox"]
    classification: Literal["MOCK", "PARTIAL"]
    configured: bool
    safe_host: str | None
    client_id_present: bool
    secret_key_present: bool
    generic_auth_present: bool
    timeout_seconds: Annotated[float, Field(gt=0, le=30)]
    max_response_bytes: Annotated[int, Field(ge=1024, le=1024 * 1024)]

    @field_validator("safe_host")
    @classmethod
    def safe_host_is_hostname_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _SAFE_HOST.fullmatch(value) or ".." in value:
            raise ValueError("safe_host must contain a hostname only")
        return value.lower()

    @model_validator(mode="after")
    def provider_identity_is_consistent(self) -> AcraDiagnosticConfiguration:
        expected = {
            "ACRA_MOCK": ("mock", "MOCK"),
            "ACRA_API_MARKETPLACE_MOCK": ("api_marketplace_mock", "MOCK"),
            "ACRA_GENERIC_SANDBOX": ("sandbox", "PARTIAL"),
        }[self.provider]
        if (self.mode, self.classification) != expected:
            raise ValueError("ACRA diagnostic provider identity is contradictory")
        return self


class AcraDiagnosticCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: AcraDiagnosticOperation
    availability: Literal["SUPPORTED", "UNSUPPORTED"]
    reason_code: str


class AcraDiagnosticSample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uen: str
    legal_name: str
    classification: Literal["PROFILE_VERIFIED", "DOCUMENTED_SAMPLE_CANDIDATE"]
    operations: tuple[AcraDiagnosticOperation, ...]
    limitation_codes: tuple[str, ...] = ()


class AcraDiagnosticAddressSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    address_line_1: str
    address_line_2: str | None
    postal_code: str
    country_code: str


class AcraDiagnosticCompanySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uen: str
    legal_name: str
    country_code: str
    entity_type: str
    registration_date: date | None
    entity_status: str | None
    registered_address: AcraDiagnosticAddressSummary | None
    source_environment: Literal["MOCK", "SANDBOX"]
    retrieved_at: datetime


class AcraDiagnosticOfficerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    officer_id: str
    name: str
    role: str
    appointment_date: date | None
    cessation_date: date | None
    country: str | None


class AcraDiagnosticShareholderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    party_id: str
    party_type: Literal["NATURAL_PERSON", "LEGAL_ENTITY"]
    name: str
    registration_identifier: str | None
    country: str | None
    source_category: str | None
    source_status: str | None
    share_allotted: str | None
    ownership_percentage: str | None


class AcraDiagnosticReceipt(BaseModel):
    """Copyable safe receipt that deliberately excludes the requested UEN and data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    diagnostic_id: UUID
    provider: AcraProviderId
    classification: Literal["MOCK", "PARTIAL"]
    operation: AcraDiagnosticOperation
    request_reference: Annotated[str, Field(pattern=r"^acra-diagnostic:[0-9a-f]{16}$")]
    started_at: datetime
    completed_at: datetime
    outcome: AcraDiagnosticOutcome
    code: Annotated[str, Field(pattern=r"^[A-Z0-9_]{3,96}$")]
    provider_called: bool
    record_count: Annotated[int, Field(ge=0, le=64)]

    @field_validator("started_at", "completed_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("diagnostic timestamps must be UTC")
        return value.astimezone(UTC)


class AcraDiagnosticResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_uen: str | None
    operation: AcraDiagnosticOperation
    outcome: AcraDiagnosticOutcome
    code: Annotated[str, Field(pattern=r"^[A-Z0-9_]{3,96}$")]
    message: Annotated[str, Field(min_length=1, max_length=240)]
    missing_fields: tuple[str, ...] = ()
    company: AcraDiagnosticCompanySummary | None = None
    officers: tuple[AcraDiagnosticOfficerSummary, ...] = Field(default=(), max_length=32)
    shareholders: tuple[AcraDiagnosticShareholderSummary, ...] = Field(
        default=(), max_length=64
    )
    receipt: AcraDiagnosticReceipt


class AcraDiagnosticStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    configuration: AcraDiagnosticConfiguration
    connectivity: Literal["NOT_CHECKED", "LAST_CHECK_SUCCEEDED", "LAST_CHECK_FAILED"]
    last_actual_check_at: datetime | None
    cancellation_semantics: Literal["PRE_DISPATCH_ONLY_IN_FLIGHT_USES_TIMEOUT"] = (
        "PRE_DISPATCH_ONLY_IN_FLIGHT_USES_TIMEOUT"
    )
    coverage: tuple[AcraDiagnosticCoverage, ...]
    samples: tuple[AcraDiagnosticSample, ...]
    timeline: tuple[AcraDiagnosticReceipt, ...]


@dataclass
class _Flight:
    event: Event = field(default_factory=Event)
    result: AcraDiagnosticResult | None = None


_SUPPORTED_OPERATIONS = frozenset(
    {
        AcraDiagnosticOperation.ENTITY_PROFILE,
        AcraDiagnosticOperation.OFFICERS,
        AcraDiagnosticOperation.SHAREHOLDERS,
    }
)

_COVERAGE = tuple(
    AcraDiagnosticCoverage(
        operation=operation,
        availability="SUPPORTED" if operation in _SUPPORTED_OPERATIONS else "UNSUPPORTED",
        reason_code=(
            "IMPLEMENTED_STRICT_CONNECTOR_OPERATION"
            if operation in _SUPPORTED_OPERATIONS
            else "PROVIDER_CONTRACT_NOT_IMPLEMENTED"
        ),
    )
    for operation in AcraDiagnosticOperation
)

_SAMPLES = (
    AcraDiagnosticSample(
        uen="11111999A",
        legal_name="GARDEN BUSINESS",
        classification="DOCUMENTED_SAMPLE_CANDIDATE",
        operations=(AcraDiagnosticOperation.ENTITY_PROFILE,),
        limitation_codes=("OFFICIAL_SHAREHOLDERS_EMPTY", "REQUIRES_CURRENT_DIAGNOSTIC_RUN"),
    ),
    AcraDiagnosticSample(
        uen="201511222D",
        legal_name="OPQ PTE. LTD.",
        classification="DOCUMENTED_SAMPLE_CANDIDATE",
        operations=(AcraDiagnosticOperation.ENTITY_PROFILE,),
        limitation_codes=("NO_SAVED_SUCCESS_RESPONSE",),
    ),
    AcraDiagnosticSample(
        uen="T15LL1111W",
        legal_name="RRR LLP",
        classification="DOCUMENTED_SAMPLE_CANDIDATE",
        operations=(
            AcraDiagnosticOperation.ENTITY_PROFILE,
            AcraDiagnosticOperation.LLP_HIGHLIGHTS,
        ),
        limitation_codes=("LLP_HIGHLIGHTS_UNSUPPORTED", "NO_SAVED_SUCCESS_RESPONSE"),
    ),
)


class AcraDiagnosticService:
    """Execute bounded read-only diagnostics without case or ledger side effects."""

    def __init__(
        self,
        *,
        connector: AcraConnector,
        configuration: AcraDiagnosticConfiguration,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] = monotonic,
        uuid_factory: Callable[[], UUID] = uuid4,
        cooldown_seconds: float = 0.5,
        max_dispatches_per_window: int = 12,
        rate_window_seconds: float = 60,
        max_concurrent_requests: int = 2,
        timeline_limit: int = 25,
    ) -> None:
        if not 0 <= cooldown_seconds <= 60:
            raise ValueError("diagnostic cooldown must be between zero and 60 seconds")
        if not 1 <= max_dispatches_per_window <= 100:
            raise ValueError("diagnostic request-window bound is invalid")
        if not 1 <= rate_window_seconds <= 3600:
            raise ValueError("diagnostic rate window is invalid")
        if not 1 <= max_concurrent_requests <= 8:
            raise ValueError("diagnostic concurrency bound is invalid")
        if not 1 <= timeline_limit <= 100:
            raise ValueError("diagnostic timeline bound is invalid")
        self._connector = connector
        self._configuration = configuration
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic_clock
        self._uuid_factory = uuid_factory
        self._cooldown_seconds = cooldown_seconds
        self._max_dispatches_per_window = max_dispatches_per_window
        self._rate_window_seconds = rate_window_seconds
        self._capacity = BoundedSemaphore(max_concurrent_requests)
        self._state_guard = Lock()
        self._inflight: dict[tuple[str, AcraDiagnosticOperation], _Flight] = {}
        self._dispatch_times: deque[float] = deque()
        self._last_dispatch_at: float | None = None
        self._timeline: deque[AcraDiagnosticReceipt] = deque(maxlen=timeline_limit)
        self._last_actual_receipt: AcraDiagnosticReceipt | None = None

    def status(self) -> AcraDiagnosticStatus:
        with self._state_guard:
            timeline = tuple(item.model_copy(deep=True) for item in self._timeline)
            last = (
                self._last_actual_receipt.model_copy(deep=True)
                if self._last_actual_receipt is not None
                else None
            )
        connectivity: Literal[
            "NOT_CHECKED", "LAST_CHECK_SUCCEEDED", "LAST_CHECK_FAILED"
        ]
        if last is None:
            connectivity = "NOT_CHECKED"
        elif last.outcome == AcraDiagnosticOutcome.FAILED:
            connectivity = "LAST_CHECK_FAILED"
        else:
            connectivity = "LAST_CHECK_SUCCEEDED"
        return AcraDiagnosticStatus(
            configuration=self._configuration.model_copy(deep=True),
            connectivity=connectivity,
            last_actual_check_at=last.completed_at if last is not None else None,
            coverage=_COVERAGE,
            samples=_SAMPLES,
            timeline=timeline,
        )

    def run(
        self,
        uen: str,
        operation: AcraDiagnosticOperation,
        *,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> AcraDiagnosticResult:
        normalized = self._normalize_uen(uen)
        if normalized is None:
            return self._local_result(
                requested_uen=None,
                operation=operation,
                outcome=AcraDiagnosticOutcome.INVALID_REQUEST,
                code="ACRA_DIAGNOSTIC_INVALID_UEN",
                message="A valid bounded Singapore UEN is required.",
            )
        if operation not in _SUPPORTED_OPERATIONS:
            return self._local_result(
                requested_uen=normalized,
                operation=operation,
                outcome=AcraDiagnosticOutcome.UNSUPPORTED,
                code=f"ACRA_DIAGNOSTIC_{operation.value}_UNSUPPORTED",
                message="This ACRA operation is not available through the current connector.",
            )
        if cancellation_requested is not None and cancellation_requested():
            return self._local_result(
                requested_uen=normalized,
                operation=operation,
                outcome=AcraDiagnosticOutcome.CANCELLED,
                code="ACRA_DIAGNOSTIC_CANCELLED_BEFORE_DISPATCH",
                message="The diagnostic was cancelled before provider dispatch.",
            )

        key = (normalized, operation)
        flight: _Flight
        gate: tuple[str, str] | None = None
        leader = False
        with self._state_guard:
            existing = self._inflight.get(key)
            if existing is not None:
                flight = existing
            else:
                now = self._monotonic()
                self._retire_rate_window(now)
                if (
                    self._last_dispatch_at is not None
                    and now - self._last_dispatch_at < self._cooldown_seconds
                ):
                    gate = (
                        "ACRA_DIAGNOSTIC_LOCAL_COOLDOWN",
                        "The local ACRA diagnostic cooldown is active.",
                    )
                elif len(self._dispatch_times) >= self._max_dispatches_per_window:
                    gate = (
                        "ACRA_DIAGNOSTIC_LOCAL_RATE_LIMIT",
                        "The local ACRA diagnostic request budget is exhausted.",
                    )
                elif not self._capacity.acquire(blocking=False):
                    gate = (
                        "ACRA_DIAGNOSTIC_LOCAL_CONCURRENCY_LIMIT",
                        "The local ACRA diagnostic concurrency bound is active.",
                    )
                else:
                    flight = _Flight()
                    self._inflight[key] = flight
                    self._dispatch_times.append(now)
                    self._last_dispatch_at = now
                    leader = True

        if gate is not None:
            return self._local_result(
                requested_uen=normalized,
                operation=operation,
                outcome=AcraDiagnosticOutcome.RATE_LIMITED,
                code=gate[0],
                message=gate[1],
            )
        if not leader:
            if not flight.event.wait(timeout=self._configuration.timeout_seconds + 1):
                return self._local_result(
                    requested_uen=normalized,
                    operation=operation,
                    outcome=AcraDiagnosticOutcome.FAILED,
                    code="ACRA_DIAGNOSTIC_SINGLE_FLIGHT_TIMEOUT",
                    message="The shared ACRA diagnostic did not complete in time.",
                )
            if flight.result is None:
                return self._local_result(
                    requested_uen=normalized,
                    operation=operation,
                    outcome=AcraDiagnosticOutcome.FAILED,
                    code="ACRA_DIAGNOSTIC_UNEXPECTED_FAILURE",
                    message="The ACRA diagnostic could not be completed.",
                )
            return flight.result.model_copy(deep=True)

        try:
            result = self._execute(normalized, operation)
        finally:
            self._capacity.release()
        with self._state_guard:
            self._record_receipt(result.receipt)
            flight.result = result
            flight.event.set()
            self._inflight.pop(key, None)
        return result

    def _execute(
        self,
        uen: str,
        operation: AcraDiagnosticOperation,
    ) -> AcraDiagnosticResult:
        started_at = self._clock()
        try:
            if operation == AcraDiagnosticOperation.ENTITY_PROFILE:
                company = self._connector.fetch_company(uen)
                if company is None:
                    return self._result(
                        uen=uen,
                        operation=operation,
                        outcome=AcraDiagnosticOutcome.NOT_FOUND,
                        code="ACRA_DIAGNOSTIC_ENTITY_PROFILE_NOT_FOUND",
                        message="No entity profile was returned for the requested UEN.",
                        started_at=started_at,
                        provider_called=True,
                    )
                self._require_identity(company.uen, uen)
                missing = tuple(
                    field_name
                    for field_name, missing_value in (
                        ("entity_type", company.entity_type == "UNKNOWN"),
                        ("registered_address", company.registered_address is None),
                    )
                    if missing_value
                )
                return self._result(
                    uen=uen,
                    operation=operation,
                    outcome=(
                        AcraDiagnosticOutcome.PARTIAL
                        if missing
                        else AcraDiagnosticOutcome.COMPLETE
                    ),
                    code=(
                        "ACRA_DIAGNOSTIC_ENTITY_PROFILE_PARTIAL"
                        if missing
                        else "ACRA_DIAGNOSTIC_ENTITY_PROFILE_COMPLETE"
                    ),
                    message=(
                        "The entity profile is missing supported profile fields."
                        if missing
                        else "The entity profile was retrieved and validated."
                    ),
                    started_at=started_at,
                    provider_called=True,
                    missing_fields=missing,
                    company=self._company_summary(company),
                    record_count=1,
                )
            if operation == AcraDiagnosticOperation.OFFICERS:
                officers_payload = self._connector.fetch_officers(uen)
                self._require_identity(officers_payload.uen, uen)
                officers = tuple(
                    self._officer_summary(item) for item in officers_payload.officers
                )
                empty = not officers
                return self._result(
                    uen=uen,
                    operation=operation,
                    outcome=(
                        AcraDiagnosticOutcome.EMPTY
                        if empty
                        else AcraDiagnosticOutcome.COMPLETE
                    ),
                    code=(
                        "ACRA_DIAGNOSTIC_OFFICERS_EMPTY"
                        if empty
                        else "ACRA_DIAGNOSTIC_OFFICERS_COMPLETE"
                    ),
                    message=(
                        "The officer operation returned an explicit empty collection."
                        if empty
                        else "The officer collection was retrieved and validated."
                    ),
                    started_at=started_at,
                    provider_called=True,
                    officers=officers,
                    record_count=len(officers),
                )

            shareholders_payload = self._connector.fetch_ownership_parties(uen)
            self._require_identity(shareholders_payload.uen, uen)
            shareholders = tuple(
                self._shareholder_summary(item)
                for item in shareholders_payload.ownership_parties
            )
            missing = (
                ("shareholders[].share_allotted",)
                if shareholders and any(item.share_allotted is None for item in shareholders)
                else ()
            )
            empty = not shareholders
            outcome = (
                AcraDiagnosticOutcome.EMPTY
                if empty
                else AcraDiagnosticOutcome.PARTIAL
                if missing
                else AcraDiagnosticOutcome.COMPLETE
            )
            code = {
                AcraDiagnosticOutcome.EMPTY: "ACRA_DIAGNOSTIC_SHAREHOLDERS_EMPTY",
                AcraDiagnosticOutcome.PARTIAL: "ACRA_DIAGNOSTIC_SHAREHOLDERS_PARTIAL",
                AcraDiagnosticOutcome.COMPLETE: "ACRA_DIAGNOSTIC_SHAREHOLDERS_COMPLETE",
            }[outcome]
            return self._result(
                uen=uen,
                operation=operation,
                outcome=outcome,
                code=code,
                message=(
                    "The shareholder operation returned an explicit empty collection."
                    if empty
                    else "The shareholder collection has missing supported fields."
                    if missing
                    else "The shareholder collection was retrieved and validated."
                ),
                started_at=started_at,
                provider_called=True,
                missing_fields=missing,
                shareholders=shareholders,
                record_count=len(shareholders),
            )
        except ConnectorError as error:
            public = public_connector_error(error)
            return self._result(
                uen=uen,
                operation=operation,
                outcome=AcraDiagnosticOutcome.FAILED,
                code=public.code,
                message=public.message,
                started_at=started_at,
                provider_called=True,
            )
        except Exception:
            return self._result(
                uen=uen,
                operation=operation,
                outcome=AcraDiagnosticOutcome.FAILED,
                code="ACRA_DIAGNOSTIC_UNEXPECTED_FAILURE",
                message="The ACRA diagnostic could not be completed.",
                started_at=started_at,
                provider_called=True,
            )

    @staticmethod
    def _normalize_uen(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().upper()
        return normalized if is_eligible_singapore_uen(normalized) else None

    @staticmethod
    def _require_identity(returned_uen: str, requested_uen: str) -> None:
        if returned_uen.strip().upper() != requested_uen:
            raise AcraResponseIdentityMismatchError

    def _local_result(
        self,
        *,
        requested_uen: str | None,
        operation: AcraDiagnosticOperation,
        outcome: AcraDiagnosticOutcome,
        code: str,
        message: str,
    ) -> AcraDiagnosticResult:
        now = self._clock()
        result = self._result(
            uen=requested_uen,
            operation=operation,
            outcome=outcome,
            code=code,
            message=message,
            started_at=now,
            provider_called=False,
        )
        with self._state_guard:
            self._record_receipt(result.receipt)
        return result

    def _result(
        self,
        *,
        uen: str | None,
        operation: AcraDiagnosticOperation,
        outcome: AcraDiagnosticOutcome,
        code: str,
        message: str,
        started_at: datetime,
        provider_called: bool,
        missing_fields: tuple[str, ...] = (),
        company: AcraDiagnosticCompanySummary | None = None,
        officers: tuple[AcraDiagnosticOfficerSummary, ...] = (),
        shareholders: tuple[AcraDiagnosticShareholderSummary, ...] = (),
        record_count: int = 0,
    ) -> AcraDiagnosticResult:
        request_reference = self._request_reference(uen)
        receipt = AcraDiagnosticReceipt(
            diagnostic_id=self._uuid_factory(),
            provider=self._configuration.provider,
            classification=self._configuration.classification,
            operation=operation,
            request_reference=request_reference,
            started_at=started_at,
            completed_at=self._clock(),
            outcome=outcome,
            code=code,
            provider_called=provider_called,
            record_count=record_count,
        )
        return AcraDiagnosticResult(
            requested_uen=uen,
            operation=operation,
            outcome=outcome,
            code=code,
            message=message,
            missing_fields=missing_fields,
            company=company,
            officers=officers,
            shareholders=shareholders,
            receipt=receipt,
        )

    def _record_receipt(self, receipt: AcraDiagnosticReceipt) -> None:
        self._timeline.append(receipt)
        if receipt.provider_called:
            self._last_actual_receipt = receipt

    def _retire_rate_window(self, now: float) -> None:
        while self._dispatch_times and now - self._dispatch_times[0] >= self._rate_window_seconds:
            self._dispatch_times.popleft()

    @staticmethod
    def _request_reference(uen: str | None) -> str:
        value = uen if uen is not None else "INVALID"
        return f"acra-diagnostic:{sha256(value.encode('ascii')).hexdigest()[:16]}"

    @staticmethod
    def _company_summary(company: AcraCompanyPayload) -> AcraDiagnosticCompanySummary:
        return AcraDiagnosticCompanySummary(
            uen=company.uen,
            legal_name=company.entity_name,
            country_code=company.country_code,
            entity_type=company.entity_type,
            registration_date=company.registration_date,
            entity_status=company.entity_status,
            registered_address=(
                AcraDiagnosticService._address_summary(company.registered_address)
                if company.registered_address is not None
                else None
            ),
            source_environment=company.source_environment,
            retrieved_at=company.retrieved_at,
        )

    @staticmethod
    def _address_summary(address: AcraAddressPayload) -> AcraDiagnosticAddressSummary:
        line_two_parts = tuple(
            value for value in (address.unit, address.building_name) if value is not None
        )
        return AcraDiagnosticAddressSummary(
            address_line_1=f"{address.block} {address.street}",
            address_line_2=", ".join(line_two_parts) or None,
            postal_code=address.postal_code,
            country_code=address.country_code,
        )

    @staticmethod
    def _officer_summary(officer: AcraOfficerPayload) -> AcraDiagnosticOfficerSummary:
        return AcraDiagnosticOfficerSummary(
            officer_id=officer.officer_id,
            name=officer.name,
            role=officer.role,
            appointment_date=officer.appointment_date,
            cessation_date=officer.cessation_date,
            country=officer.country,
        )

    @staticmethod
    def _shareholder_summary(
        shareholder: AcraOwnershipPartyPayload,
    ) -> AcraDiagnosticShareholderSummary:
        return AcraDiagnosticShareholderSummary(
            party_id=shareholder.party_id,
            party_type=shareholder.party_type,
            name=shareholder.name,
            registration_identifier=shareholder.registration_identifier,
            country=shareholder.country,
            source_category=shareholder.source_category,
            source_status=shareholder.source_status,
            share_allotted=(
                format(shareholder.share_allotted, "f")
                if shareholder.share_allotted is not None
                else None
            ),
            ownership_percentage=(
                format(shareholder.ownership_percentage, "f")
                if shareholder.ownership_percentage is not None
                else None
            ),
        )
