from datetime import UTC, datetime, timedelta, timezone
from typing import Literal

import httpx
import pytest

from app.config import Settings
from app.connectors.acra import AcraCompanyPayload
from app.connectors.errors import AcraTimeoutError
from app.connectors.goldtier_models import (
    AmendPartyRequest,
    CreatePolicyRequest,
    CreateShellCustomerRequest,
    GoldTierOperationResult,
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
    SearchPartyRequest,
)
from app.connectors.mock_acra import MockAcraConnector
from app.demo.scenarios import (
    GOLDTIER_FAILURE_UEN,
    GOLDTIER_PARTIAL_UEN,
    INCOMPLETE_ENTITY_UEN,
    VALID_SME_UEN,
)
from app.domain.models import WorkflowState
from app.main import create_app
from app.mappers.errors import MappingError
from app.mappers.goldtier import build_amend_request, build_shell_request
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository

FIXED_TIME = datetime(2026, 8, 10, 3, 0, tzinfo=UTC)
INTERNAL_SENTINEL = "private stack detail must never escape"
GoldTierStage = Literal["search", "shell", "policy", "amend"]


class RaisingAcraConnector:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        del uen
        self.calls.append("acra")
        raise RuntimeError(INTERNAL_SENTINEL)


class TimeoutAcraConnector:
    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        del uen
        raise AcraTimeoutError


class NonUtcAcraConnector:
    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        payload = MockAcraConnector(clock=lambda: FIXED_TIME).fetch_company(uen)
        assert payload is not None
        return payload.model_copy(
            update={
                "retrieved_at": datetime(
                    2026, 8, 10, 12, 0, tzinfo=timezone(timedelta(hours=8))
                )
            }
        )


class RecordingGoldTierConnector:
    def __init__(
        self,
        *,
        raise_at: GoldTierStage | None = None,
        search_outcome: GoldTierSearchOutcome = GoldTierSearchOutcome.NO_MATCH,
    ) -> None:
        self.raise_at = raise_at
        self.search_outcome = search_outcome
        self.calls: list[str] = []

    def _record(self, stage: GoldTierStage) -> None:
        self.calls.append(stage)
        if self.raise_at == stage:
            raise RuntimeError(INTERNAL_SENTINEL)

    def search_party(
        self, request: SearchPartyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierSearchResult:
        del request, metadata
        self._record("search")
        if self.search_outcome == GoldTierSearchOutcome.MATCH_FOUND:
            return GoldTierSearchResult(
                outcome=self.search_outcome,
                status_code=200,
                matched_party_id="GT-EXISTING-SYNTHETIC",
                message="Synthetic existing candidate.",
            )
        if self.search_outcome == GoldTierSearchOutcome.FAILURE:
            return GoldTierSearchResult(
                outcome=self.search_outcome,
                status_code=503,
                error_code="SYNTHETIC_SEARCH_FAILURE",
                message="Synthetic modeled search failure.",
            )
        return GoldTierSearchResult(
            outcome=GoldTierSearchOutcome.NO_MATCH,
            status_code=200,
            message="No synthetic match.",
        )

    def create_shell_customer(
        self, request: CreateShellCustomerRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        del request, metadata
        self._record("shell")
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id="GT-SYNTHETIC-NEW",
            status="SHELL_CREATED",
            message="Synthetic shell created.",
        )

    def create_policy(
        self, request: CreatePolicyRequest, metadata: GoldTierRequestMetadata
    ) -> GoldTierOperationResult:
        del request, metadata
        self._record("policy")
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=201,
            party_id="GT-SYNTHETIC-NEW",
            policy_id="POL-SYNTHETIC-NEW",
            status="POLICY_CREATED",
            message="Synthetic policy created.",
        )

    def amend_party(
        self,
        party_id: str,
        request: AmendPartyRequest,
        metadata: GoldTierRequestMetadata,
    ) -> GoldTierOperationResult:
        del party_id, request, metadata
        self._record("amend")
        return GoldTierOperationResult(
            outcome=GoldTierOutcome.SUCCESS,
            status_code=200,
            party_id="GT-SYNTHETIC-NEW",
            status="ENRICHED",
            message="Synthetic amend completed.",
        )


def build_recording_service(
    goldtier: RecordingGoldTierConnector,
    *,
    acra: (
        MockAcraConnector
        | RaisingAcraConnector
        | TimeoutAcraConnector
        | NonUtcAcraConnector
        | None
    ) = None,
) -> OnboardingService:
    return OnboardingService(
        acra=acra or MockAcraConnector(clock=lambda: FIXED_TIME),
        goldtier=goldtier,
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: FIXED_TIME,
    )


async def post_case(
    service: OnboardingService, uen: str = VALID_SME_UEN
) -> tuple[httpx.Response, httpx.AsyncClient]:
    application = create_app(Settings(app_env="test"), onboarding_service=service)
    transport = httpx.ASGITransport(app=application)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    response = await client.post("/api/onboarding/cases", json={"uen": uen})
    return response, client


def assert_safe_terminal_failure(response: httpx.Response) -> str:
    assert response.status_code == 503
    response_text = response.text.lower()
    assert INTERNAL_SENTINEL not in response.text
    assert "traceback" not in response_text
    assert "runtimeerror" not in response_text
    detail = response.json()["detail"]
    assert set(detail) == {"code", "message", "case_id", "correlation_id"}
    return detail["case_id"]


@pytest.mark.anyio
async def test_acra_exception_persists_retrievable_failed_case_and_stops() -> None:
    acra = RaisingAcraConnector()
    goldtier = RecordingGoldTierConnector()
    service = build_recording_service(goldtier, acra=acra)

    response, client = await post_case(service)
    case_id = assert_safe_terminal_failure(response)
    retrieved = await client.get(f"/api/onboarding/cases/{case_id}")
    await client.aclose()

    assert acra.calls == ["acra"]
    assert goldtier.calls == []
    assert retrieved.status_code == 200
    assert retrieved.json()["state"] == "FAILED"
    assert retrieved.json()["events"][-1]["code"] == "ACRA_RETRIEVAL_UNEXPECTED_FAILURE"


@pytest.mark.anyio
async def test_typed_acra_failure_persists_safe_code_and_stops_goldtier() -> None:
    goldtier = RecordingGoldTierConnector()
    service = build_recording_service(goldtier, acra=TimeoutAcraConnector())

    response, client = await post_case(service)
    case_id = assert_safe_terminal_failure(response)
    retrieved = await client.get(f"/api/onboarding/cases/{case_id}")
    await client.aclose()

    assert response.json()["detail"]["code"] == "ACRA_TIMEOUT"
    assert retrieved.json()["state"] == "FAILED"
    assert retrieved.json()["events"][-1]["code"] == "ACRA_TIMEOUT"
    assert goldtier.calls == []


@pytest.mark.anyio
async def test_acra_source_mapping_failure_terminalizes_and_stops_goldtier() -> None:
    goldtier = RecordingGoldTierConnector()
    service = build_recording_service(goldtier, acra=NonUtcAcraConnector())

    response, client = await post_case(service)
    case_id = assert_safe_terminal_failure(response)
    retrieved = await client.get(f"/api/onboarding/cases/{case_id}")
    await client.aclose()

    assert response.json()["detail"]["code"] == "ACRA_SOURCE_MAPPING_FAILED"
    assert retrieved.json()["state"] == "FAILED"
    assert retrieved.json()["events"][-1]["code"] == "ACRA_SOURCE_MAPPING_FAILED"
    assert goldtier.calls == []


@pytest.mark.anyio
async def test_acra_mapping_exception_persists_failed_case_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_mapping_error(payload: AcraCompanyPayload) -> None:
        del payload
        raise RuntimeError(INTERNAL_SENTINEL)

    monkeypatch.setattr("app.services.onboarding.map_acra_company", raise_mapping_error)
    goldtier = RecordingGoldTierConnector()
    service = build_recording_service(goldtier)

    response, client = await post_case(service)
    case_id = assert_safe_terminal_failure(response)
    retrieved = await client.get(f"/api/onboarding/cases/{case_id}")
    await client.aclose()

    assert goldtier.calls == []
    assert response.json()["detail"]["code"] == "ACRA_MAPPING_UNEXPECTED_FAILURE"
    assert retrieved.json()["state"] == "FAILED"
    assert retrieved.json()["events"][-1]["code"] == "ACRA_MAPPING_UNEXPECTED_FAILURE"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("raise_at", "expected_calls", "expected_code"),
    [
        ("search", ["search"], "GT_SEARCH_UNEXPECTED_FAILURE"),
        ("shell", ["search", "shell"], "GT_SHELL_UNEXPECTED_FAILURE"),
        ("policy", ["search", "shell", "policy"], "GT_POLICY_UNEXPECTED_FAILURE"),
        ("amend", ["search", "shell", "policy", "amend"], "GT_AMEND_UNEXPECTED_FAILURE"),
    ],
)
async def test_goldtier_exception_terminalizes_and_prevents_later_calls(
    raise_at: GoldTierStage,
    expected_calls: list[str],
    expected_code: str,
) -> None:
    goldtier = RecordingGoldTierConnector(raise_at=raise_at)
    service = build_recording_service(goldtier)

    response, client = await post_case(service)
    case_id = assert_safe_terminal_failure(response)
    retrieved = await client.get(f"/api/onboarding/cases/{case_id}")
    await client.aclose()

    body = retrieved.json()
    assert goldtier.calls == expected_calls
    assert response.json()["detail"]["code"] == expected_code
    assert body["state"] == "FAILED"
    assert body["error"]["code"] == expected_code
    assert body["events"][-1]["stage"] == "FAILED"
    assert body["events"][-1]["outcome"] == "FAILED"
    assert body["events"][-1]["code"] == expected_code
    assert "COMPLETED" not in [event["stage"] for event in body["events"]]


@pytest.mark.anyio
async def test_match_found_requires_review_without_duplicate_shell() -> None:
    goldtier = RecordingGoldTierConnector(search_outcome=GoldTierSearchOutcome.MATCH_FOUND)
    service = build_recording_service(goldtier)

    response, client = await post_case(service)
    await client.aclose()

    assert response.status_code == 201
    assert response.json()["state"] == "REVIEW_REQUIRED"
    assert response.json()["error"]["code"] == "GT_EXISTING_PARTY_REVIEW_REQUIRED"
    assert goldtier.calls == ["search"]


@pytest.mark.anyio
async def test_no_match_allows_shell_and_full_happy_path() -> None:
    goldtier = RecordingGoldTierConnector(search_outcome=GoldTierSearchOutcome.NO_MATCH)
    service = build_recording_service(goldtier)

    response, client = await post_case(service)
    await client.aclose()

    assert response.status_code == 201
    assert response.json()["state"] == "COMPLETED"
    assert goldtier.calls == ["search", "shell", "policy", "amend"]


@pytest.mark.anyio
async def test_modeled_search_failure_is_failed_without_shell_or_5xx() -> None:
    goldtier = RecordingGoldTierConnector(search_outcome=GoldTierSearchOutcome.FAILURE)
    service = build_recording_service(goldtier)

    response, client = await post_case(service)
    await client.aclose()

    assert response.status_code == 201
    assert response.json()["state"] == "FAILED"
    assert response.json()["error"]["code"] == "GT_SEARCH_FAILED"
    assert goldtier.calls == ["search"]


def test_multiple_cases_are_isolated_and_events_obey_terminal_invariants() -> None:
    from app.main import build_onboarding_service

    service = build_onboarding_service()
    cases = [
        service.create_case(VALID_SME_UEN),
        service.create_case(INCOMPLETE_ENTITY_UEN),
        service.create_case(GOLDTIER_FAILURE_UEN),
        service.create_case(GOLDTIER_PARTIAL_UEN),
        service.create_case("999999999Z"),
    ]

    assert [case.state for case in cases] == [
        WorkflowState.COMPLETED,
        WorkflowState.REVIEW_REQUIRED,
        WorkflowState.FAILED,
        WorkflowState.REVIEW_REQUIRED,
        WorkflowState.FAILED,
    ]
    assert len({case.case_id for case in cases}) == len(cases)
    for case in cases:
        assert service.get_case(case.case_id) == case
        assert [event.sequence for event in case.events] == list(range(1, len(case.events) + 1))
        assert [event.timestamp for event in case.events] == sorted(
            event.timestamp for event in case.events
        )
        assert all(event.case_id == case.case_id for event in case.events)
        assert all(event.correlation_id == case.correlation_id for event in case.events)
        assert case.events[-1].stage in {
            WorkflowState.COMPLETED,
            WorkflowState.REVIEW_REQUIRED,
            WorkflowState.FAILED,
        }
        assert all(
            event.stage
            not in {
                WorkflowState.COMPLETED,
                WorkflowState.REVIEW_REQUIRED,
                WorkflowState.FAILED,
            }
            for event in case.events[:-1]
        )


def test_mapper_preconditions_raise_explicit_errors_not_assertions() -> None:
    payload = MockAcraConnector(clock=lambda: FIXED_TIME).fetch_company(VALID_SME_UEN)
    assert payload is not None
    from app.mappers.acra import map_acra_company

    entity = map_acra_company(payload)

    with pytest.raises(MappingError):
        build_shell_request(
            entity.model_copy(update={"legal_name": None}), "CASE-SYNTHETIC", FIXED_TIME
        )
    with pytest.raises(MappingError):
        build_amend_request(
            entity.model_copy(update={"registered_address": None}),
            "CASE-SYNTHETIC",
            FIXED_TIME,
        )
