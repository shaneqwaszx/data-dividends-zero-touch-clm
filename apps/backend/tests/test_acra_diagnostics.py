"""Read-only ACRA diagnostic service contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from threading import Event, Lock
from uuid import UUID

import pytest

from app.connectors.acra import (
    AcraAddressPayload,
    AcraCompanyPayload,
    AcraOfficerPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraOwnershipPartyPayload,
    AcraRelationshipsPayload,
)
from app.connectors.errors import (
    AcraAuthenticationError,
    AcraMalformedResponseError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
    ConnectorError,
)
from app.services.acra_diagnostics import (
    AcraDiagnosticConfiguration,
    AcraDiagnosticOperation,
    AcraDiagnosticOutcome,
    AcraDiagnosticService,
    AcraDiagnosticStatus,
)

NOW = datetime(2026, 9, 29, 4, 0, tzinfo=UTC)
GARDEN_UEN = "11111999A"
OPQ_UEN = "201511222D"
RRR_UEN = "T15LL1111W"


class MutableMonotonic:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


class RecordingConnector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.company: AcraCompanyPayload | None = _company()
        self.officers = _officers()
        self.shareholders = _shareholders()
        self.errors: dict[str, Exception] = {}
        self.started = Event()
        self.release = Event()
        self.block_operation: str | None = None
        self._guard = Lock()

    def _record(self, operation: str, uen: str) -> None:
        with self._guard:
            self.calls.append((operation, uen))
        if operation == self.block_operation:
            self.started.set()
            if not self.release.wait(timeout=5):
                raise AssertionError("test connector was not released")
        error = self.errors.get(operation)
        if error is not None:
            raise error

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self._record("company", uen)
        return self.company

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self._record("officers", uen)
        return self.officers.model_copy(update={"uen": uen})

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self._record("shareholders", uen)
        return self.shareholders.model_copy(update={"uen": uen})

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self._record("relationships", uen)
        raise AssertionError("diagnostics must not call unsupported relationships")


def _company(*, address: bool = True, entity_type: str = "BUSINESS") -> AcraCompanyPayload:
    return AcraCompanyPayload(
        uen=GARDEN_UEN,
        entity_name="GARDEN BUSINESS",
        country_code="SG",
        entity_type=entity_type,
        registration_date=date(2018, 3, 10),
        entity_status=None,
        registered_address=(
            AcraAddressPayload(
                block="18",
                street="GARDEN WALK",
                unit="#01-01",
                postal_code="018919",
                country_code="SG",
            )
            if address
            else None
        ),
        source_environment="MOCK",
        source_endpoint="https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation",
        retrieved_at=NOW,
    )


def _officers(*, empty: bool = False) -> AcraOfficersPayload:
    return AcraOfficersPayload(
        uen=GARDEN_UEN,
        officers=(
            ()
            if empty
            else (
                AcraOfficerPayload(
                    officer_id="OFFICER-1",
                    name="SYNTHETIC OFFICER",
                    role="OWNER",
                ),
            )
        ),
        source_environment="MOCK",
        source_endpoint="https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation",
        retrieved_at=NOW,
    )


def _shareholders(*, missing_count: bool = False) -> AcraOwnershipPartiesPayload:
    return AcraOwnershipPartiesPayload(
        uen=GARDEN_UEN,
        ownership_parties=(
            AcraOwnershipPartyPayload(
                party_id="SHAREHOLDER-1",
                party_type="LEGAL_ENTITY",
                name="SYNTHETIC SHAREHOLDER",
                source_category="Corporate",
                source_status="Active",
                share_allotted=None if missing_count else Decimal("100"),
            ),
        ),
        source_environment="MOCK",
        source_endpoint="https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/coShareholdersDetails",
        retrieved_at=NOW,
    )


def _configuration() -> AcraDiagnosticConfiguration:
    return AcraDiagnosticConfiguration(
        provider="ACRA_API_MARKETPLACE_MOCK",
        mode="api_marketplace_mock",
        classification="MOCK",
        configured=True,
        safe_host="api-sandbox.bizfile.gov.sg",
        client_id_present=True,
        secret_key_present=True,
        generic_auth_present=False,
        timeout_seconds=10,
        max_response_bytes=256 * 1024,
    )


def _service(
    connector: RecordingConnector,
    *,
    monotonic_clock: MutableMonotonic | None = None,
    cooldown_seconds: float = 0,
    max_dispatches_per_window: int = 12,
    rate_window_seconds: float = 60,
    max_concurrent_requests: int = 2,
    timeline_limit: int = 25,
) -> AcraDiagnosticService:
    next_uuid = iter(UUID(int=index) for index in range(1, 100))
    return AcraDiagnosticService(
        connector=connector,
        configuration=_configuration(),
        clock=lambda: NOW,
        monotonic_clock=monotonic_clock or MutableMonotonic(),
        uuid_factory=lambda: next(next_uuid),
        cooldown_seconds=cooldown_seconds,
        max_dispatches_per_window=max_dispatches_per_window,
        rate_window_seconds=rate_window_seconds,
        max_concurrent_requests=max_concurrent_requests,
        timeline_limit=timeline_limit,
    )


def test_status_is_sanitized_and_catalogue_keeps_sample_evidence_separate() -> None:
    service = _service(RecordingConnector())

    status = service.status()

    assert isinstance(status, AcraDiagnosticStatus)
    assert status.configuration.safe_host == "api-sandbox.bizfile.gov.sg"
    assert status.configuration.client_id_present is True
    assert status.configuration.secret_key_present is True
    assert status.connectivity == "NOT_CHECKED"
    assert status.last_actual_check_at is None
    assert status.cancellation_semantics == "PRE_DISPATCH_ONLY_IN_FLIGHT_USES_TIMEOUT"
    assert [(item.uen, item.legal_name, item.classification) for item in status.samples] == [
        (GARDEN_UEN, "GARDEN BUSINESS", "DOCUMENTED_SAMPLE_CANDIDATE"),
        (OPQ_UEN, "OPQ PTE. LTD.", "DOCUMENTED_SAMPLE_CANDIDATE"),
        (RRR_UEN, "RRR LLP", "DOCUMENTED_SAMPLE_CANDIDATE"),
    ]
    assert status.samples[0].operations == (AcraDiagnosticOperation.ENTITY_PROFILE,)
    assert status.samples[1].operations == (AcraDiagnosticOperation.ENTITY_PROFILE,)
    assert status.samples[2].operations == (
        AcraDiagnosticOperation.ENTITY_PROFILE,
        AcraDiagnosticOperation.LLP_HIGHLIGHTS,
    )
    dumped = status.model_dump_json()
    assert "access_token" not in dumped
    assert "secret-value" not in dumped
    assert "111111111M" not in dumped
    assert "111111111K" not in dumped


def test_configuration_rejects_host_override_shapes_that_can_carry_secrets() -> None:
    with pytest.raises(ValueError):
        AcraDiagnosticConfiguration.model_validate(
            {
                **_configuration().model_dump(),
                "safe_host": "https://user:secret@example.test/path",
            }
        )


def test_configuration_rejects_contradictory_provider_mode_classification() -> None:
    with pytest.raises(ValueError):
        AcraDiagnosticConfiguration.model_validate(
            {
                **_configuration().model_dump(),
                "provider": "ACRA_GENERIC_SANDBOX",
                "mode": "api_marketplace_mock",
                "classification": "MOCK",
            }
        )


def test_entity_profile_success_returns_only_canonical_safe_summary_and_receipt() -> None:
    connector = RecordingConnector()
    service = _service(connector)

    result = service.run(GARDEN_UEN.lower(), AcraDiagnosticOperation.ENTITY_PROFILE)

    assert result.outcome == AcraDiagnosticOutcome.COMPLETE
    assert result.code == "ACRA_DIAGNOSTIC_ENTITY_PROFILE_COMPLETE"
    assert result.company is not None
    assert result.company.uen == GARDEN_UEN
    assert result.company.registered_address is not None
    assert result.company.registered_address.address_line_1 == "18 GARDEN WALK"
    assert result.company.source_environment == "MOCK"
    assert result.officers == ()
    assert result.shareholders == ()
    assert connector.calls == [("company", GARDEN_UEN)]
    assert result.receipt.provider_called is True
    assert result.receipt.request_reference != GARDEN_UEN
    serialized = result.model_dump_json()
    assert "source_endpoint" not in serialized
    assert "token" not in serialized.lower()


def test_entity_profile_not_found_and_partial_are_distinct() -> None:
    missing = RecordingConnector()
    missing.company = None
    missing_result = _service(missing).run(GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE)
    assert missing_result.outcome == AcraDiagnosticOutcome.NOT_FOUND
    assert missing_result.company is None

    partial = RecordingConnector()
    partial.company = _company(address=False, entity_type="UNKNOWN")
    partial_result = _service(partial).run(
        GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE
    )
    assert partial_result.outcome == AcraDiagnosticOutcome.PARTIAL
    assert partial_result.missing_fields == ("entity_type", "registered_address")


def test_officer_empty_and_shareholder_partial_preserve_operation_meaning() -> None:
    connector = RecordingConnector()
    connector.officers = _officers(empty=True)
    connector.shareholders = _shareholders(missing_count=True)
    service = _service(connector)

    officers = service.run(GARDEN_UEN, AcraDiagnosticOperation.OFFICERS)
    shareholders = service.run(GARDEN_UEN, AcraDiagnosticOperation.SHAREHOLDERS)

    assert officers.outcome == AcraDiagnosticOutcome.EMPTY
    assert officers.code == "ACRA_DIAGNOSTIC_OFFICERS_EMPTY"
    assert shareholders.outcome == AcraDiagnosticOutcome.PARTIAL
    assert shareholders.missing_fields == ("shareholders[].share_allotted",)
    assert len(shareholders.shareholders) == 1
    assert connector.calls == [
        ("officers", GARDEN_UEN),
        ("shareholders", GARDEN_UEN),
    ]


@pytest.mark.parametrize(
    "operation",
    [
        AcraDiagnosticOperation.LLP_HIGHLIGHTS,
        AcraDiagnosticOperation.CAPITAL_DETAILS,
        AcraDiagnosticOperation.RELATIONSHIPS,
    ],
)
def test_unsupported_coverage_is_explicit_and_makes_no_provider_call(
    operation: AcraDiagnosticOperation,
) -> None:
    connector = RecordingConnector()

    result = _service(connector).run(RRR_UEN, operation)

    assert result.outcome == AcraDiagnosticOutcome.UNSUPPORTED
    assert result.code == f"ACRA_DIAGNOSTIC_{operation.value}_UNSUPPORTED"
    assert result.receipt.provider_called is False
    assert connector.calls == []


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (AcraAuthenticationError("private token value"), "ACRA_AUTHENTICATION_ERROR"),
        (AcraTimeoutError("private endpoint"), "ACRA_TIMEOUT"),
        (AcraServiceUnavailableError("provider 429 body"), "ACRA_SERVICE_UNAVAILABLE"),
        (AcraMalformedResponseError("oversized raw body"), "ACRA_MALFORMED_RESPONSE"),
    ],
)
def test_connector_failures_map_to_fixed_safe_results(
    error: ConnectorError,
    expected_code: str,
) -> None:
    connector = RecordingConnector()
    connector.errors["company"] = error

    result = _service(connector).run(GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE)

    assert result.outcome == AcraDiagnosticOutcome.FAILED
    assert result.code == expected_code
    assert result.message == error.public_message
    serialized = result.model_dump_json()
    assert "private" not in serialized
    assert "provider 429 body" not in serialized
    assert "oversized raw body" not in serialized


def test_invalid_identifier_and_pre_dispatch_cancellation_make_zero_calls() -> None:
    connector = RecordingConnector()
    service = _service(connector)

    invalid = service.run(
        "https://unsafe.test/?token=secret",
        AcraDiagnosticOperation.ENTITY_PROFILE,
    )
    cancelled = service.run(
        GARDEN_UEN,
        AcraDiagnosticOperation.ENTITY_PROFILE,
        cancellation_requested=lambda: True,
    )

    assert invalid.outcome == AcraDiagnosticOutcome.INVALID_REQUEST
    assert invalid.requested_uen is None
    assert "unsafe" not in invalid.model_dump_json()
    assert cancelled.outcome == AcraDiagnosticOutcome.CANCELLED
    assert cancelled.receipt.provider_called is False
    assert connector.calls == []


def test_single_flight_reuses_one_in_flight_result_for_the_same_operation() -> None:
    connector = RecordingConnector()
    connector.block_operation = "company"
    service = _service(connector, max_concurrent_requests=1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            service.run, GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE
        )
        assert connector.started.wait(timeout=2)
        second = executor.submit(
            service.run, GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE
        )
        connector.release.set()
        first_result = first.result(timeout=2)
        second_result = second.result(timeout=2)

    assert connector.calls == [("company", GARDEN_UEN)]
    assert first_result == second_result


def test_cooldown_and_sliding_window_rate_bounds_stop_before_connector() -> None:
    clock = MutableMonotonic()
    connector = RecordingConnector()
    service = _service(
        connector,
        monotonic_clock=clock,
        cooldown_seconds=2,
        max_dispatches_per_window=2,
        rate_window_seconds=10,
    )

    assert service.run(GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE).outcome == (
        AcraDiagnosticOutcome.COMPLETE
    )
    cooldown = service.run(GARDEN_UEN, AcraDiagnosticOperation.OFFICERS)
    clock.value += 2
    assert service.run(GARDEN_UEN, AcraDiagnosticOperation.OFFICERS).outcome == (
        AcraDiagnosticOutcome.COMPLETE
    )
    clock.value += 2
    window = service.run(GARDEN_UEN, AcraDiagnosticOperation.SHAREHOLDERS)

    assert cooldown.outcome == AcraDiagnosticOutcome.RATE_LIMITED
    assert cooldown.code == "ACRA_DIAGNOSTIC_LOCAL_COOLDOWN"
    assert window.outcome == AcraDiagnosticOutcome.RATE_LIMITED
    assert window.code == "ACRA_DIAGNOSTIC_LOCAL_RATE_LIMIT"
    assert connector.calls == [("company", GARDEN_UEN), ("officers", GARDEN_UEN)]


def test_distinct_request_is_rejected_while_concurrency_capacity_is_occupied() -> None:
    connector = RecordingConnector()
    connector.block_operation = "company"
    service = _service(connector, max_concurrent_requests=1)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            service.run, GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE
        )
        assert connector.started.wait(timeout=2)
        limited = service.run(OPQ_UEN, AcraDiagnosticOperation.OFFICERS)
        connector.release.set()
        assert first.result(timeout=2).outcome == AcraDiagnosticOutcome.COMPLETE

    assert limited.outcome == AcraDiagnosticOutcome.RATE_LIMITED
    assert limited.code == "ACRA_DIAGNOSTIC_LOCAL_CONCURRENCY_LIMIT"
    assert connector.calls == [("company", GARDEN_UEN)]


def test_timeline_is_bounded_and_last_actual_check_excludes_local_blocks() -> None:
    connector = RecordingConnector()
    monotonic_clock = MutableMonotonic()
    service = _service(
        connector,
        monotonic_clock=monotonic_clock,
        max_dispatches_per_window=10,
        timeline_limit=2,
    )

    service.run(GARDEN_UEN, AcraDiagnosticOperation.ENTITY_PROFILE)
    monotonic_clock.value += 1
    service.run(GARDEN_UEN, AcraDiagnosticOperation.OFFICERS)
    monotonic_clock.value += 1
    service.run(RRR_UEN, AcraDiagnosticOperation.LLP_HIGHLIGHTS)
    status = service.status()

    assert len(status.timeline) == 2
    assert status.timeline[-1].provider_called is False
    assert status.last_actual_check_at == NOW
    assert status.connectivity == "LAST_CHECK_SUCCEEDED"
