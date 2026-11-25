"""Truthful GoldTier Sandbox Search diagnostics with injected transports only.

No test in this module reaches a real GoldTier endpoint: connector tests use a local
fake transport, and transport tests replace the httpx client with ``MockTransport``.
"""

from __future__ import annotations

import ssl
from collections.abc import Callable, Mapping
from decimal import Decimal
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request
from phase13_test_clients import RawAsyncClient
from pydantic import SecretStr
from test_goldtier_xpi_sandbox import _sandbox_submission, _xpi_onboarding_service

from app.api_provider_sandbox import build_provider_sandbox_router
from app.config import Settings
from app.connectors import goldtier_xpi
from app.connectors.errors import ConnectorError, MutationUncertaintyReason
from app.connectors.goldtier_models import GoldTierRequestMetadata
from app.connectors.goldtier_xpi import (
    GoldTierMutationOutcomeUncertainError,
    GoldTierXpiHttpResponse,
    GoldTierXpiMalformedResponseError,
    GoldTierXpiResponseDecodeError,
    GoldTierXpiResponseTooLargeError,
    GoldTierXpiSandboxConnection,
    GoldTierXpiSandboxConnector,
    GoldTierXpiServiceUnavailableError,
    GoldTierXpiTimeoutError,
    HttpxGoldTierXpiTransport,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_idp import MockIdpProvider
from app.connectors.mock_ownership import MockOwnershipProvider
from app.domain.access import AuthenticatedActor, Role, TeamId, UserProfile
from app.domain.clm import ClmBlockerCode
from app.domain.models import EventOutcome
from app.domain.onboarding_intelligence import EntityResolutionOutcome
from app.domain.target_submission import GoldTierProviderMode
from app.mappers.goldtier_xpi import GoldTierXpiRequestMapper
from app.services.clm_orchestration import ClmOrchestrationService
from app.services.clm_repository import InMemoryClmOrchestrationRepository
from app.services.document_processing import DocumentProcessingService
from app.services.document_repository import InMemoryDocumentProcessingRepository
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository

BACKEND_USER = "backend-only-diagnostic-user"
PRIVATE_MARKER = "private-provider-detail-7f3a"
SYNTHETIC_ID = "900001"
SYNTHETIC_NAME = "SYNTHETIC DIAGNOSTIC PTE LTD"
SEARCH_PATH = "/api/admin/goldtier-sandbox/search"
STATUS_PATH = "/api/admin/goldtier-sandbox/status"
_REAL_HTTPX_CLIENT = httpx.Client


class ScriptedTransport:
    """Local fake XPI transport returning scripted responses or raising scripted errors."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json_body: object | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> object:
        self.calls.append({"method": method, "url": url, "headers": dict(headers)})
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _connection(*, max_response_bytes: int = 4096) -> GoldTierXpiSandboxConnection:
    return GoldTierXpiSandboxConnection(
        base_url="https://sandbox.goldtier.invalid",
        environment="synthetic",
        user_id=SecretStr(BACKEND_USER),
        timeout_seconds=5.0,
        max_response_bytes=max_response_bytes,
        allow_writes=True,
    )


def _connector(
    transport: object | None = None, *, max_response_bytes: int = 4096
) -> GoldTierXpiSandboxConnector:
    return GoldTierXpiSandboxConnector(
        connection=_connection(max_response_bytes=max_response_bytes),
        transport=transport,  # type: ignore[arg-type]
    )


def _metadata() -> GoldTierRequestMetadata:
    return GoldTierRequestMetadata(
        correlation_id=UUID("00000000-0000-4000-8000-00000000d1a6"),
        source_case_id="SANDBOX-CONSOLE",
        idempotency_key=UUID("00000000-0000-4000-8000-00000000d1a7"),
    )


def _candidate(party_id: str = SYNTHETIC_ID, **extra: object) -> dict[str, object]:
    return {"goldTierID": party_id, **extra}


def _patch_httpx(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[dict[str, object]]:
    """Route the production transport through ``MockTransport`` and record its options."""

    created: list[dict[str, object]] = []

    def client_factory(**kwargs: object) -> httpx.Client:
        created.append(kwargs)
        return _REAL_HTTPX_CLIENT(
            transport=httpx.MockTransport(handler),
            follow_redirects=bool(kwargs.get("follow_redirects", True)),
        )

    monkeypatch.setattr(goldtier_xpi.httpx, "Client", client_factory)
    return created


def _service(transport: object) -> OnboardingService:
    return OnboardingService(
        acra=MockAcraConnector(),
        goldtier=_connector(transport),
        goldtier_mapper=GoldTierXpiRequestMapper(),
        repository=InMemoryOnboardingCaseRepository(),
    )


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr(BACKEND_USER),
        goldtier_sandbox_allow_writes=False,
    )


def _app(service: OnboardingService, role: Role = Role.HR) -> FastAPI:
    application = FastAPI()

    @application.middleware("http")
    async def actor_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.actor = AuthenticatedActor(
            profile=UserProfile(
                user_id="biz-ops" if role == Role.HR else "maya-lim",
                display_name="Synthetic actor",
                role=role,
                team_id=None if role in {Role.HR, Role.DIRECTOR} else TeamId.TEAM_A,
            )
        )
        return await call_next(request)

    application.include_router(build_provider_sandbox_router(service, _settings()))
    return application


async def _search(
    service: OnboardingService,
    body: dict[str, str],
    *,
    role: Role = Role.HR,
) -> tuple[httpx.Response, httpx.Response]:
    transport = httpx.ASGITransport(app=_app(service, role))
    async with RawAsyncClient(transport=transport, base_url="http://test") as client:
        search = await client.post(SEARCH_PATH, json=body)
        status_response = await client.get(STATUS_PATH)
    return search, status_response


def _assert_no_private_values(*responses: httpx.Response) -> None:
    for response in responses:
        assert BACKEND_USER not in response.text
        assert PRIVATE_MARKER not in response.text
        assert "gt-xpi" not in response.text
        assert "user_id" not in response.text


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# Connector and transport classification -------------------------------------------


@pytest.mark.parametrize(
    ("criteria", "expected_query"),
    [
        ({"goldtier_id": SYNTHETIC_ID}, [("goldTierID", SYNTHETIC_ID)]),
        ({"legal_name": SYNTHETIC_NAME}, [("legalName", SYNTHETIC_NAME)]),
        ({"group_company_name": "SYNTHETIC GROUP"}, [("groupCompanyName", "SYNTHETIC GROUP")]),
        ({"country_of_incorporation": "SG"}, [("countryOfIncorporation", "SG")]),
    ],
)
def test_search_sends_only_the_supplied_xpi_query_aliases(
    criteria: dict[str, str], expected_query: list[tuple[str, str]]
) -> None:
    transport = ScriptedTransport(GoldTierXpiHttpResponse(status_code=200, body=[]))

    _connector(transport).search_party(XpiCustomerSearchRequest(**criteria), _metadata())

    query = parse_qsl(urlsplit(str(transport.calls[0]["url"])).query)
    assert query == expected_query
    assert all(name != "registrationNumber" for name, _ in query)


def test_http_200_outcomes_distinguish_no_match_exact_id_and_multiple() -> None:
    transport = ScriptedTransport(
        GoldTierXpiHttpResponse(status_code=200, body=[]),
        GoldTierXpiHttpResponse(status_code=200, body=[_candidate(legalName=SYNTHETIC_NAME)]),
        GoldTierXpiHttpResponse(
            status_code=200, body=[_candidate(), _candidate("900002")]
        ),
    )
    connector = _connector(transport)
    request = XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID)

    empty = connector.search_party(request, _metadata())
    exact = connector.search_party(request, _metadata())
    multiple = connector.search_party(request, _metadata())

    assert (empty.outcome, empty.status_code, empty.candidates) == ("NO_MATCH", 200, ())
    assert (exact.outcome, exact.matched_party_id) == ("MATCH_FOUND", SYNTHETIC_ID)
    assert multiple.outcome == "MULTIPLE_MATCHES"
    assert [item.party_id for item in multiple.candidates] == [SYNTHETIC_ID, "900002"]


def test_http_400_is_a_controlled_rejection_not_absence() -> None:
    transport = ScriptedTransport(
        GoldTierXpiHttpResponse(status_code=400, body={"detail": PRIVATE_MARKER})
    )

    result = _connector(transport).search_party(
        XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
    )

    assert (result.outcome, result.status_code, result.error_code) == (
        "FAILURE",
        400,
        "GT_XPI_SEARCH_INVALID",
    )
    assert PRIVATE_MARKER not in result.model_dump_json()


@pytest.mark.parametrize("status_code", [401, 403])
def test_http_401_and_403_are_trusted_authorization_failures(status_code: int) -> None:
    transport = ScriptedTransport(
        GoldTierXpiHttpResponse(status_code=status_code, body={"detail": PRIVATE_MARKER})
    )

    with pytest.raises(goldtier_xpi.GoldTierXpiAuthorizationError) as caught:
        _connector(transport).search_party(
            XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
        )

    assert caught.value.code == "GT_XPI_AUTHORIZATION_FAILED"
    assert caught.value.upstream_status == status_code
    assert PRIVATE_MARKER not in str(caught.value)


def test_http_404_is_an_unexpected_response_that_retains_only_its_status() -> None:
    transport = ScriptedTransport(GoldTierXpiHttpResponse(status_code=404, body=None))

    with pytest.raises(GoldTierXpiMalformedResponseError) as caught:
        _connector(transport).search_party(
            XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
        )

    assert caught.value.code == "GT_XPI_MALFORMED_RESPONSE"
    assert caught.value.upstream_status == 404


def test_http_429_is_a_trusted_rate_limit_failure() -> None:
    transport = ScriptedTransport(GoldTierXpiHttpResponse(status_code=429, body=None))

    with pytest.raises(goldtier_xpi.GoldTierXpiRateLimitedError) as caught:
        _connector(transport).search_party(
            XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
        )

    assert caught.value.code == "GT_XPI_RATE_LIMITED"
    assert caught.value.upstream_status == 429


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b'{"error":"' + PRIVATE_MARKER.encode() + b'"}', "application/json"),
        (b"", "text/plain"),
    ],
    ids=["json", "empty"],
)
def test_http_500_with_a_decodable_body_is_a_controlled_failure(
    monkeypatch: pytest.MonkeyPatch, content: bytes, content_type: str
) -> None:
    _patch_httpx(
        monkeypatch,
        lambda _request: httpx.Response(
            500, content=content, headers={"content-type": content_type}
        ),
    )

    result = _connector(HttpxGoldTierXpiTransport()).search_party(
        XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
    )

    assert (result.outcome, result.status_code, result.error_code) == (
        "FAILURE",
        500,
        "GT_XPI_SERVICE_UNAVAILABLE",
    )
    assert result.candidates == ()
    assert PRIVATE_MARKER not in result.model_dump_json()


@pytest.mark.parametrize(
    ("status_code", "content", "error_type"),
    [
        (500, b"<html>" + PRIVATE_MARKER.encode() + b"</html>", "ServiceUnavailable"),
        (503, b"{not-json " + PRIVATE_MARKER.encode(), "ServiceUnavailable"),
        (400, b"<html>" + PRIVATE_MARKER.encode(), "ResponseDecode"),
        (401, b"<html>" + PRIVATE_MARKER.encode(), "Authorization"),
        (403, b"<html>" + PRIVATE_MARKER.encode(), "Authorization"),
        (404, b"<html>" + PRIVATE_MARKER.encode(), "ResponseDecode"),
        (429, b"{not-json", "RateLimited"),
    ],
    ids=["500-html", "503-invalid-json", "400-html", "401", "403", "404", "429"],
)
def test_non_json_error_bodies_keep_their_status_category_as_trusted_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    content: bytes,
    error_type: str,
) -> None:
    _patch_httpx(
        monkeypatch,
        lambda _request: httpx.Response(
            status_code, content=content, headers={"content-type": "text/html"}
        ),
    )
    expected = {
        "ServiceUnavailable": GoldTierXpiServiceUnavailableError,
        "ResponseDecode": GoldTierXpiResponseDecodeError,
        "Authorization": goldtier_xpi.GoldTierXpiAuthorizationError,
        "RateLimited": goldtier_xpi.GoldTierXpiRateLimitedError,
    }[error_type]

    with pytest.raises(expected) as caught:
        _connector(HttpxGoldTierXpiTransport()).search_party(
            XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
        )

    assert type(caught.value) is expected
    assert caught.value.upstream_status == status_code
    assert PRIVATE_MARKER not in str(caught.value)


def test_http_200_success_body_keeps_strict_json_array_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        (
            httpx.Response(200, content=b"<html>" + PRIVATE_MARKER.encode()),
            httpx.Response(200, json={"unexpected": PRIVATE_MARKER}),
            httpx.Response(200, json=[{"legalName": SYNTHETIC_NAME}]),
        )
    )
    _patch_httpx(monkeypatch, lambda _request: next(responses))
    connector = _connector(HttpxGoldTierXpiTransport())
    request = XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID)

    with pytest.raises(GoldTierXpiResponseDecodeError) as undecodable:
        connector.search_party(request, _metadata())
    with pytest.raises(GoldTierXpiMalformedResponseError) as wrong_shape:
        connector.search_party(request, _metadata())
    with pytest.raises(GoldTierXpiMalformedResponseError) as missing_id:
        connector.search_party(request, _metadata())

    for caught in (undecodable, wrong_shape, missing_id):
        assert caught.value.code == "GT_XPI_MALFORMED_RESPONSE"
        assert caught.value.upstream_status == 200
        assert PRIVATE_MARKER not in str(caught.value)


def test_timeout_and_transport_failure_are_distinct_trusted_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(PRIVATE_MARKER, request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(PRIVATE_MARKER, request=request)

    request = XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID)
    _patch_httpx(monkeypatch, timeout)
    with pytest.raises(GoldTierXpiTimeoutError) as timed_out:
        _connector(HttpxGoldTierXpiTransport()).search_party(request, _metadata())
    _patch_httpx(monkeypatch, refused)
    with pytest.raises(GoldTierXpiServiceUnavailableError) as unavailable:
        _connector(HttpxGoldTierXpiTransport()).search_party(request, _metadata())

    assert timed_out.value.code == "GT_XPI_TIMEOUT"
    assert unavailable.value.code == "GT_XPI_SERVICE_UNAVAILABLE"
    assert PRIVATE_MARKER not in str(timed_out.value) + str(unavailable.value)


def test_real_transport_keeps_tls13_verification_no_redirects_and_size_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _patch_httpx(
        monkeypatch,
        lambda _request: httpx.Response(500, content=b"x" * 2048),
    )

    with pytest.raises(GoldTierXpiResponseTooLargeError):
        _connector(HttpxGoldTierXpiTransport(), max_response_bytes=1024).search_party(
            XpiCustomerSearchRequest(goldtier_id=SYNTHETIC_ID), _metadata()
        )

    options = created[0]
    context = options["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version == ssl.TLSVersion.TLSv1_3
    assert context.maximum_version == ssl.TLSVersion.TLSv1_3
    assert options["follow_redirects"] is False


@pytest.mark.parametrize("operation", ["SHELL", "POLICY", "AMEND"])
@pytest.mark.parametrize(
    ("status_code", "content"),
    [(500, b"<html>gateway</html>"), (400, b"{not-json"), (200, b"<html>ok</html>")],
)
def test_mutation_bodies_that_are_not_json_remain_uncertain_and_unreplayed(
    monkeypatch: pytest.MonkeyPatch, operation: str, status_code: int, content: bytes
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(status_code, content=content)

    _patch_httpx(monkeypatch, handler)
    mapper = GoldTierXpiRequestMapper()
    submission = _sandbox_submission()
    connector = _connector(HttpxGoldTierXpiTransport())
    mutations: dict[str, Callable[[], object]] = {
        "SHELL": lambda: connector.create_shell_customer(
            mapper.build_shell_request(submission), _metadata()
        ),
        "POLICY": lambda: connector.create_policy(
            mapper.build_policy_request(submission, SYNTHETIC_ID), _metadata()
        ),
        "AMEND": lambda: connector.amend_party(
            SYNTHETIC_ID, mapper.build_amend_request(submission, SYNTHETIC_ID), _metadata()
        ),
    }

    with pytest.raises(GoldTierMutationOutcomeUncertainError) as caught:
        mutations[operation]()

    assert caught.value.reason == MutationUncertaintyReason.RESPONSE_DECODE
    assert calls == ["POST"]


# Standalone Sandbox service resolution --------------------------------------------


def _sandbox_search(service: OnboardingService, **criteria: str):  # type: ignore[no-untyped-def]
    return service.search_sandbox_target(
        XpiCustomerSearchRequest(**criteria),
        correlation_id=UUID("00000000-0000-4000-8000-00000000d1a8"),
    )


@pytest.mark.parametrize("status_code", [400, 500])
def test_failed_provider_search_is_never_resolved_into_no_match(status_code: int) -> None:
    service = _service(ScriptedTransport(GoldTierXpiHttpResponse(status_code=status_code)))

    evidence = _sandbox_search(service, legal_name=SYNTHETIC_NAME, country_of_incorporation="SG")

    assert evidence.result.outcome == "FAILURE"
    assert evidence.resolution is None


def test_id_only_candidate_is_retrieved_but_not_identity_assessed() -> None:
    service = _service(
        ScriptedTransport(
            GoldTierXpiHttpResponse(
                status_code=200, body=[_candidate(legalName=SYNTHETIC_NAME)]
            )
        )
    )

    evidence = _sandbox_search(service, goldtier_id=SYNTHETIC_ID)

    assert evidence.result.outcome == "MATCH_FOUND"
    assert evidence.result.matched_party_id == SYNTHETIC_ID
    assert evidence.resolution is None


def test_legal_name_and_singapore_country_use_the_existing_resolver() -> None:
    service = _service(
        ScriptedTransport(
            GoldTierXpiHttpResponse(
                status_code=200,
                body=[_candidate(legalName=SYNTHETIC_NAME, countryOfIncorporation="SG")],
            )
        )
    )

    evidence = _sandbox_search(
        service, legal_name=SYNTHETIC_NAME, country_of_incorporation="SG"
    )

    assert evidence.resolution is not None
    assert evidence.resolution.outcome == EntityResolutionOutcome.REVIEW_REQUIRED
    assert evidence.resolution.selected_candidate_id is None


@pytest.mark.parametrize(
    ("criteria", "candidate"),
    [
        ({"goldtier_id": SYNTHETIC_ID, "country_of_incorporation": "SG"},
         _candidate(legalName=SYNTHETIC_NAME)),
        ({"legal_name": SYNTHETIC_NAME}, _candidate()),
        ({"country_of_incorporation": "SG"}, _candidate(legalName=SYNTHETIC_NAME)),
    ],
    ids=["id-and-country-without-candidate-country", "name-without-candidate-name", "country"],
)
def test_retrieval_without_any_comparable_feature_is_not_assessed(
    criteria: dict[str, str], candidate: dict[str, object]
) -> None:
    service = _service(
        ScriptedTransport(GoldTierXpiHttpResponse(status_code=200, body=[candidate]))
    )

    evidence = _sandbox_search(service, **criteria)

    assert evidence.result.outcome == "MATCH_FOUND"
    assert evidence.resolution is None


def test_id_and_country_conflict_is_retained_from_the_existing_resolver() -> None:
    service = _service(
        ScriptedTransport(
            GoldTierXpiHttpResponse(
                status_code=200,
                body=[_candidate(legalName=SYNTHETIC_NAME, countryOfIncorporation="MY")],
            )
        )
    )

    evidence = _sandbox_search(service, goldtier_id=SYNTHETIC_ID, country_of_incorporation="SG")

    assert evidence.resolution is not None
    assert evidence.resolution.outcome == EntityResolutionOutcome.CONFLICT


def test_successful_zero_candidate_search_remains_a_genuine_no_match() -> None:
    service = _service(ScriptedTransport(GoldTierXpiHttpResponse(status_code=200, body=[])))

    evidence = _sandbox_search(service, goldtier_id=SYNTHETIC_ID)

    assert evidence.result.outcome == "NO_MATCH"
    assert evidence.resolution is not None
    assert evidence.resolution.outcome == EntityResolutionOutcome.NO_MATCH


# Administrative API projection and timeline ----------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [(400, "GT_XPI_SEARCH_INVALID"), (500, "GT_XPI_SERVICE_UNAVAILABLE")],
)
async def test_api_controlled_failure_is_recorded_failed_and_not_assessed(
    status_code: int, error_code: str
) -> None:
    transport = ScriptedTransport(
        GoldTierXpiHttpResponse(status_code=status_code, body={"detail": PRIVATE_MARKER})
    )

    search, status_response = await _search(_service(transport), {"goldtier_id": SYNTHETIC_ID})

    assert search.status_code == 200
    body = search.json()
    assert body["status"] == "FAILURE"
    assert body["entity_resolution"] == "NOT_ASSESSED"
    assert body["error_code"] == error_code
    assert body["upstream_status"] == status_code
    assert body["count"] == 0
    assert body["correlation_id"] == transport.calls[0]["headers"]["X-Correlation-Id"]
    timeline = status_response.json()["timeline"]
    assert [(item["action"], item["outcome"], item["code"]) for item in timeline] == [
        ("SEARCH", "FAILED", error_code)
    ]
    _assert_no_private_values(search, status_response)


@pytest.mark.anyio
async def test_api_html_500_from_the_real_transport_is_unavailable_not_no_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_httpx(
        monkeypatch,
        lambda _request: httpx.Response(
            500,
            content=b"<html>" + PRIVATE_MARKER.encode() + b"</html>",
            headers={"content-type": "text/html"},
        ),
    )

    search, status_response = await _search(
        _service(HttpxGoldTierXpiTransport()), {"goldtier_id": SYNTHETIC_ID}
    )

    assert search.status_code == 503
    detail = search.json()["detail"]
    assert (detail["code"], detail["upstream_status"]) == ("GT_XPI_SERVICE_UNAVAILABLE", 500)
    assert "NO_MATCH" not in search.text
    timeline = status_response.json()["timeline"]
    assert [(item["outcome"], item["code"]) for item in timeline] == [
        ("FAILED", "GT_XPI_SERVICE_UNAVAILABLE")
    ]
    _assert_no_private_values(search, status_response)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("scripted", "code", "upstream_status"),
    [
        (httpx.ReadTimeout(PRIVATE_MARKER), "GT_XPI_TIMEOUT", None),
        (httpx.ConnectError(PRIVATE_MARKER), "GT_XPI_SERVICE_UNAVAILABLE", None),
        (
            GoldTierXpiHttpResponse(status_code=200, body={"detail": PRIVATE_MARKER}),
            "GT_XPI_MALFORMED_RESPONSE",
            200,
        ),
        (GoldTierXpiHttpResponse(status_code=401), "GT_XPI_AUTHORIZATION_FAILED", 401),
        (GoldTierXpiHttpResponse(status_code=403), "GT_XPI_AUTHORIZATION_FAILED", 403),
        (GoldTierXpiHttpResponse(status_code=404), "GT_XPI_MALFORMED_RESPONSE", 404),
        (GoldTierXpiHttpResponse(status_code=429), "GT_XPI_RATE_LIMITED", 429),
    ],
    ids=["timeout", "transport", "malformed-200", "401", "403", "404", "429"],
)
async def test_api_connector_failures_project_trusted_codes_and_failed_timeline(
    scripted: object, code: str, upstream_status: int | None
) -> None:
    transport = ScriptedTransport(scripted)

    search, status_response = await _search(_service(transport), {"goldtier_id": SYNTHETIC_ID})

    assert search.status_code == 503
    detail = search.json()["detail"]
    assert detail["code"] == code
    assert detail["message"] == {
        "GT_XPI_TIMEOUT": "The GoldTier sandbox request timed out.",
        "GT_XPI_SERVICE_UNAVAILABLE": "The GoldTier sandbox service is unavailable.",
        "GT_XPI_MALFORMED_RESPONSE": "The GoldTier sandbox returned an unexpected response.",
        "GT_XPI_AUTHORIZATION_FAILED": "The GoldTier sandbox did not authorize the request.",
        "GT_XPI_RATE_LIMITED": "The GoldTier sandbox rate-limited the request.",
    }[code]
    assert detail["correlation_id"] == transport.calls[0]["headers"]["X-Correlation-Id"]
    assert detail.get("upstream_status") == upstream_status
    assert isinstance(detail["elapsed_ms"], int)
    expected_keys = {"code", "message", "correlation_id", "elapsed_ms"}
    if upstream_status is not None:
        expected_keys.add("upstream_status")
    assert set(detail) == expected_keys
    assert "retry-after" not in search.headers
    assert "www-authenticate" not in search.headers
    assert len(transport.calls) == 1
    timeline = status_response.json()["timeline"]
    assert [(item["action"], item["outcome"], item["code"]) for item in timeline] == [
        ("SEARCH", "FAILED", code)
    ]
    _assert_no_private_values(search, status_response)


class StubSearchConnector:
    """Local connector double for service-boundary failures the XPI adapter cannot emit."""

    environment = GoldTierProviderMode.SANDBOX

    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls = 0

    def search_party(self, request: object, metadata: object) -> object:
        del request, metadata
        self.calls += 1
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("outcome", "code", "message"),
    [
        (
            {"outcome": "NO_MATCH", "detail": PRIVATE_MARKER},
            "GT_XPI_MALFORMED_RESPONSE",
            "The GoldTier sandbox returned an unexpected response.",
        ),
        (
            RuntimeError(PRIVATE_MARKER),
            "GOLDTIER_SANDBOX_SEARCH_FAILED",
            "GoldTier sandbox Search could not be completed.",
        ),
    ],
    ids=["invalid-target-response", "unexpected-exception"],
)
async def test_api_service_boundary_failures_stay_sanitized(
    outcome: object, code: str, message: str
) -> None:
    connector = StubSearchConnector(outcome)
    service = OnboardingService(
        acra=MockAcraConnector(),
        goldtier=connector,  # type: ignore[arg-type]
        goldtier_mapper=GoldTierXpiRequestMapper(),
        repository=InMemoryOnboardingCaseRepository(),
    )

    search, status_response = await _search(service, {"goldtier_id": SYNTHETIC_ID})

    assert search.status_code == 503
    detail = search.json()["detail"]
    assert (detail["code"], detail["message"]) == (code, message)
    assert set(detail) == {"code", "message", "correlation_id", "elapsed_ms"}
    assert connector.calls == 1
    assert status_response.json()["timeline"][-1]["code"] == code
    _assert_no_private_values(search, status_response)


@pytest.mark.anyio
async def test_api_rejects_an_unsupported_registration_number_criterion_before_dispatch() -> None:
    transport = ScriptedTransport()

    search, _ = await _search(
        _service(transport),
        {"goldtier_id": SYNTHETIC_ID, "registration_number": "202400001A"},
    )

    assert search.status_code == 422
    assert transport.calls == []


@pytest.mark.anyio
async def test_api_projects_a_resolver_conflict_for_id_and_country_search() -> None:
    transport = ScriptedTransport(
        GoldTierXpiHttpResponse(
            status_code=200,
            body=[_candidate(legalName=SYNTHETIC_NAME, countryOfIncorporation="MY")],
        )
    )

    search, _ = await _search(
        _service(transport), {"goldtier_id": SYNTHETIC_ID, "country_of_incorporation": "SG"}
    )

    assert (search.json()["status"], search.json()["entity_resolution"]) == (
        "MATCH_FOUND",
        "CONFLICT",
    )


@pytest.mark.anyio
async def test_api_id_only_candidate_is_retrieved_with_identity_not_assessed() -> None:
    transport = ScriptedTransport(
        GoldTierXpiHttpResponse(status_code=200, body=[_candidate(legalName=SYNTHETIC_NAME)])
    )

    search, status_response = await _search(_service(transport), {"goldtier_id": SYNTHETIC_ID})

    body = search.json()
    assert search.status_code == 200
    assert (body["status"], body["count"]) == ("MATCH_FOUND", 1)
    assert body["candidates"][0]["party_id"] == SYNTHETIC_ID
    assert body["entity_resolution"] == "NOT_ASSESSED"
    assert body["error_code"] is None
    assert body["upstream_status"] == 200
    assert status_response.json()["timeline"][-1]["outcome"] == "SUCCEEDED"
    assert status_response.json()["timeline"][-1]["code"] == "GOLDTIER_SANDBOX_SEARCH_MATCH_FOUND"


@pytest.mark.anyio
async def test_api_genuine_no_match_and_assessed_identity_remain_succeeded() -> None:
    empty = ScriptedTransport(GoldTierXpiHttpResponse(status_code=200, body=[]))
    named = ScriptedTransport(
        GoldTierXpiHttpResponse(
            status_code=200,
            body=[_candidate(legalName=SYNTHETIC_NAME, countryOfIncorporation="SG")],
        )
    )

    no_match, no_match_status = await _search(_service(empty), {"goldtier_id": SYNTHETIC_ID})
    assessed, _ = await _search(
        _service(named),
        {"legal_name": SYNTHETIC_NAME, "country_of_incorporation": "SG"},
    )

    assert (no_match.json()["status"], no_match.json()["entity_resolution"]) == (
        "NO_MATCH",
        "NO_MATCH",
    )
    assert no_match_status.json()["timeline"][-1]["outcome"] == "SUCCEEDED"
    assert assessed.json()["entity_resolution"] == "REVIEW_REQUIRED"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "role", [Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER, Role.DIRECTOR]
)
async def test_api_search_is_hr_only_and_forbidden_roles_reach_no_provider(role: Role) -> None:
    transport = ScriptedTransport()
    app = _app(_service(transport), role)

    async with RawAsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(SEARCH_PATH, json={"goldtier_id": SYNTHETIC_ID})

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PROVIDER_SANDBOX_TEST_FORBIDDEN"
    assert transport.calls == []


# Case-level Search callers keep their failure path ---------------------------------


@pytest.mark.parametrize(
    ("scripted", "observed_status"),
    [
        (GoldTierXpiHttpResponse(status_code=401), 401),
        (GoldTierXpiHttpResponse(status_code=403), 403),
        (GoldTierXpiHttpResponse(status_code=429), 429),
        (GoldTierXpiResponseDecodeError(upstream_status=502), 502),
    ],
    ids=["401", "403", "429", "non-json-502"],
)
def test_case_level_initial_search_failure_stays_failed_without_mutation(
    scripted: object, observed_status: int
) -> None:
    transport = ScriptedTransport(scripted)

    case = _service(transport).create_staged_case(
        "202400001A", "SG", legal_name=SYNTHETIC_NAME
    )

    failed = [event.code for event in case.events if event.outcome == EventOutcome.FAILED]
    assert failed == ["SEARCH_SERVICE_UNAVAILABLE"]
    retained = case.initial_target_search
    assert retained is not None
    assert (retained.disposition, retained.provider_outcome, retained.candidate_count) == (
        "FAILED",
        "SEARCH_SERVICE_UNAVAILABLE",
        0,
    )
    # The observed provider status is retained, as for a JSON-bodied failure; the safe
    # code and message stay the existing initial-Search vocabulary.
    assert retained.status_code == observed_status
    assert [call["method"] for call in transport.calls] == ["GET"]


class RepeatingTransport(ScriptedTransport):
    """Return or raise the same scripted outcome for every Search call."""

    def request(self, method: str, url: str, **kwargs: object) -> object:  # type: ignore[override]
        self.responses.append(self.responses[0])
        return super().request(method, url, **kwargs)  # type: ignore[arg-type]


def _sandbox_clm(transport: object) -> ClmOrchestrationService:
    cases = _xpi_onboarding_service(transport)
    documents = DocumentProcessingService(
        cases=cases,
        idp=MockIdpProvider(),
        repository=InMemoryDocumentProcessingRepository(),
        max_upload_bytes=5 * 1024 * 1024,
        review_confidence_threshold=0.85,
    )
    ownership = OwnershipAnalysisService(
        cases=cases,
        provider=MockOwnershipProvider(),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
    )
    return ClmOrchestrationService(
        cases=cases,
        documents=documents,
        ownership=ownership,
        repository=InMemoryClmOrchestrationRepository(),
    )


@pytest.mark.parametrize(
    ("scripted", "code", "message", "status_code"),
    [
        (
            GoldTierXpiTimeoutError(),
            "GT_XPI_TIMEOUT",
            "The GoldTier sandbox request timed out.",
            503,
        ),
        (
            GoldTierXpiResponseDecodeError(upstream_status=500),
            "GT_XPI_SERVICE_UNAVAILABLE",
            "The GoldTier sandbox service is unavailable.",
            500,
        ),
        (
            GoldTierXpiHttpResponse(status_code=401),
            "GT_XPI_AUTHORIZATION_FAILED",
            "The GoldTier sandbox did not authorize the request.",
            401,
        ),
        (
            GoldTierXpiHttpResponse(status_code=429),
            "GT_XPI_RATE_LIMITED",
            "The GoldTier sandbox rate-limited the request.",
            429,
        ),
        (
            GoldTierXpiHttpResponse(status_code=404),
            "GT_XPI_MALFORMED_RESPONSE",
            "The GoldTier sandbox returned an unexpected response.",
            404,
        ),
        (
            GoldTierXpiHttpResponse(status_code=200, body={"detail": PRIVATE_MARKER}),
            "GT_XPI_MALFORMED_RESPONSE",
            "The GoldTier sandbox returned an unexpected response.",
            200,
        ),
        (
            GoldTierXpiHttpResponse(status_code=500, body={"detail": PRIVATE_MARKER}),
            "GT_SEARCH_FAILED",
            "GoldTier party search returned a controlled failure.",
            500,
        ),
        (
            ConnectorError(PRIVATE_MARKER),
            "CONNECTOR_FAILURE",
            "An external service request could not be completed.",
            503,
        ),
    ],
    ids=[
        "timeout",
        "non-json-500",
        "401",
        "429",
        "404",
        "malformed-200",
        "json-500-controlled",
        "untrusted-connector-error",
    ],
)
def test_case_level_early_search_failure_keeps_trusted_category_and_observed_status(
    scripted: object, code: str, message: str, status_code: int
) -> None:
    transport = RepeatingTransport(scripted)

    record = _sandbox_clm(transport).create_case("202400001A")

    checkpoint = record.target_search_checkpoint
    assert checkpoint is not None
    assert (checkpoint.status, checkpoint.disposition) == ("FAILED", "FAILED")
    assert (checkpoint.code, checkpoint.message) == (code, message)
    assert checkpoint.status_code == status_code
    assert (checkpoint.candidate_count, checkpoint.selected_party_id) == (0, None)
    assert ClmBlockerCode.GOLDTIER_SEARCH_FAILED in record.readiness.blockers
    assert record.submission_snapshot is None
    assert transport.calls and {call["method"] for call in transport.calls} == {"GET"}
    assert PRIVATE_MARKER not in record.model_dump_json()
    assert BACKEND_USER not in record.model_dump_json()


def test_observed_search_status_is_retained_only_for_trusted_retainable_statuses() -> None:
    observed = goldtier_xpi.observed_goldtier_xpi_search_status

    assert observed(GoldTierXpiServiceUnavailableError(upstream_status=503)) == 503
    assert observed(GoldTierXpiMalformedResponseError(upstream_status=200)) == 200
    assert observed(GoldTierXpiResponseDecodeError(upstream_status=101)) is None
    assert observed(GoldTierXpiServiceUnavailableError()) is None
    assert observed(GoldTierXpiTimeoutError()) is None
    assert observed(ConnectorError()) is None
