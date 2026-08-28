from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.config import Settings
from app.connectors.acra import AcraCompanyPayload
from app.connectors.acra_sandbox import (
    AcraHttpResponse,
    AcraSandboxConnection,
    AcraSandboxConnector,
    ProjectAcraResponseDecoder,
)
from app.connectors.errors import (
    AcraAuthenticationError,
    AcraMalformedResponseError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
    ConnectorError,
)
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.demo.scenarios import VALID_SME_UEN
from app.domain.models import CanonicalLegalEntity
from app.main import create_app
from app.mappers.acra import map_acra_company
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository

FIXED_TIME = datetime(2026, 8, 10, 6, 0, tzinfo=UTC)
PRIVATE_SENTINEL = "PRIVATE-CONNECTOR-DETAIL-9f3a"


def project_body() -> dict[str, Any]:
    return {
        "company": {
            "uen": VALID_SME_UEN,
            "entityName": "MERLION CIRCULAR LABS PTE. LTD.",
            "countryCode": "SG",
            "entityType": "PRIVATE_COMPANY_LIMITED_BY_SHARES",
            "registrationDate": "2024-01-02",
            "entityStatus": "LIVE",
            "registeredAddress": {
                "block": "18",
                "streetName": "INNOVATION WAY",
                "unit": "#04-01",
                "buildingName": "SYNTHETIC CENTRE",
                "postalCode": "018956",
                "countryCode": "SG",
            },
        }
    }


def set_nested(document: dict[str, Any], path: tuple[str, ...], value: str) -> None:
    target: dict[str, Any] = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


class BodyTransport:
    def __init__(self, body: object) -> None:
        self.body = body

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        del url, headers, timeout_seconds
        return AcraHttpResponse(status_code=200, body=self.body)


class SafeAuthorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        return {"X-Synthetic-Authorization": "fixture-only-value"}


class RaisingAuthenticationAuthorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        raise AcraAuthenticationError(RuntimeError(PRIVATE_SENTINEL))


class NoGoldTierCalls:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def search_party(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        self.calls.append("search")
        raise AssertionError("GoldTier must not be called")


class RaisingAcraConnector:
    def __init__(self, error: ConnectorError) -> None:
        self.error = error

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        del uen
        raise self.error


def sandbox_connector(
    body: object,
    *,
    authorizer: SafeAuthorizer | RaisingAuthenticationAuthorizer | None = None,
) -> AcraSandboxConnector:
    return AcraSandboxConnector(
        connection=AcraSandboxConnection(
            base_url="https://sandbox.synthetic-acra.example",
            company_path_template="/business-profile/{uen}",
            timeout_seconds=5,
        ),
        transport=BodyTransport(body),
        authorizer=authorizer or SafeAuthorizer(),
        decoder=ProjectAcraResponseDecoder(),
        clock=lambda: FIXED_TIME,
    )


def service_with(acra: object, goldtier: NoGoldTierCalls) -> OnboardingService:
    return OnboardingService(
        acra=acra,  # type: ignore[arg-type]
        goldtier=goldtier,  # type: ignore[arg-type]
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: FIXED_TIME,
    )


async def post_case(service: OnboardingService) -> tuple[httpx.Response, httpx.Response]:
    application = create_app(Settings(app_env="test"), onboarding_service=service)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/onboarding/cases", json={"uen": VALID_SME_UEN})
        detail = response.json()["detail"]
        retrieved = await client.get(f"/api/onboarding/cases/{detail['case_id']}")
    return response, retrieved


REQUIRED_SOURCE_PATHS = [
    ("company", "uen"),
    ("company", "entityName"),
    ("company", "countryCode"),
    ("company", "entityType"),
    ("company", "registeredAddress", "block"),
    ("company", "registeredAddress", "streetName"),
    ("company", "registeredAddress", "postalCode"),
    ("company", "registeredAddress", "countryCode"),
]
REQUIRED_SOURCE_PATH_IDS = [
    "uen",
    "entity-name",
    "company-country",
    "entity-type",
    "address-block",
    "address-street",
    "address-postal",
    "address-country",
]


@pytest.mark.parametrize("path", REQUIRED_SOURCE_PATHS, ids=REQUIRED_SOURCE_PATH_IDS)
@pytest.mark.parametrize("bad_value", ["", "   "], ids=["empty", "whitespace"])
def test_decoder_rejects_semantically_blank_required_source_fields(
    path: tuple[str, ...], bad_value: str
) -> None:
    body = project_body()
    set_nested(body, path, bad_value)

    with pytest.raises(AcraMalformedResponseError):
        sandbox_connector(body).fetch_company(VALID_SME_UEN)


def test_decoder_trims_valid_required_source_fields() -> None:
    body = project_body()
    for path in REQUIRED_SOURCE_PATHS:
        value_target: dict[str, Any] = body
        for part in path[:-1]:
            value_target = value_target[part]
        value_target[path[-1]] = f"  {value_target[path[-1]]}  "

    payload = sandbox_connector(body).fetch_company(VALID_SME_UEN)

    assert payload is not None
    assert payload.uen == VALID_SME_UEN
    assert payload.entity_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert payload.country_code == "SG"
    assert payload.entity_type == "PRIVATE_COMPANY_LIMITED_BY_SHARES"
    assert payload.registered_address is not None
    assert payload.registered_address.model_dump() == {
        "block": "18",
        "street": "INNOVATION WAY",
        "unit": "#04-01",
        "building_name": "SYNTHETIC CENTRE",
        "postal_code": "018956",
        "country_code": "SG",
    }


@pytest.mark.anyio
@pytest.mark.parametrize("path", REQUIRED_SOURCE_PATHS, ids=REQUIRED_SOURCE_PATH_IDS)
@pytest.mark.parametrize("bad_value", ["", "   "], ids=["empty", "whitespace"])
async def test_malformed_required_source_terminalizes_and_stops_goldtier(
    path: tuple[str, ...], bad_value: str
) -> None:
    body = project_body()
    set_nested(body, path, bad_value)
    goldtier = NoGoldTierCalls()
    service = service_with(sandbox_connector(body), goldtier)

    response, retrieved = await post_case(service)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ACRA_MALFORMED_RESPONSE"
    assert retrieved.status_code == 200
    assert retrieved.json()["state"] == "FAILED"
    assert retrieved.json()["events"][-1]["code"] == "ACRA_MALFORMED_RESPONSE"
    assert goldtier.calls == []
    combined = response.text + retrieved.text
    assert "traceback" not in combined.lower()


def malformed_canonical(field: str) -> CanonicalLegalEntity:
    payload = MockAcraConnector(clock=lambda: FIXED_TIME).fetch_company(VALID_SME_UEN)
    assert payload is not None
    canonical = map_acra_company(payload)
    if field.startswith("address."):
        assert canonical.registered_address is not None
        address_field = field.removeprefix("address.")
        address = canonical.registered_address.model_copy(update={address_field: "   "})
        return canonical.model_copy(update={"registered_address": address})
    return canonical.model_copy(update={field: "   "})


@pytest.mark.anyio
@pytest.mark.parametrize(
    "field",
    [
        "registration_number",
        "legal_name",
        "country_of_incorporation",
        "party_type",
        "address.address_line_1",
        "address.postal_code",
        "address.country_code",
    ],
)
async def test_canonical_defense_stops_future_mapper_bypass(
    field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    entity = malformed_canonical(field)
    monkeypatch.setattr("app.connectors.registry.map_acra_company", lambda payload: entity)
    goldtier = NoGoldTierCalls()
    service = service_with(MockAcraConnector(clock=lambda: FIXED_TIME), goldtier)
    application = create_app(Settings(app_env="test"), onboarding_service=service)
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/onboarding/cases", json={"uen": VALID_SME_UEN})

    assert response.status_code == 201
    assert response.json()["state"] == "REVIEW_REQUIRED"
    assert response.json()["error"]["code"] == "CANONICAL_DATA_INCOMPLETE"
    assert goldtier.calls == []


@pytest.mark.anyio
async def test_private_authentication_context_never_reaches_public_or_persisted_errors() -> None:
    goldtier = NoGoldTierCalls()
    service = service_with(
        sandbox_connector(project_body(), authorizer=RaisingAuthenticationAuthorizer()),
        goldtier,
    )

    response, retrieved = await post_case(service)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ACRA_AUTHENTICATION_ERROR"
    assert response.json()["detail"]["message"] == (
        "The ACRA registry request could not be authorized."
    )
    assert retrieved.json()["state"] == "FAILED"
    assert PRIVATE_SENTINEL not in response.text
    assert PRIVATE_SENTINEL not in retrieved.text
    assert goldtier.calls == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected_code", "expected_message"),
    [
        (
            AcraTimeoutError(RuntimeError(PRIVATE_SENTINEL)),
            "ACRA_TIMEOUT",
            "The ACRA registry request timed out.",
        ),
        (
            AcraServiceUnavailableError(RuntimeError(PRIVATE_SENTINEL)),
            "ACRA_SERVICE_UNAVAILABLE",
            "The ACRA registry service is unavailable.",
        ),
    ],
)
async def test_other_typed_connector_context_is_sanitized(
    error: ConnectorError, expected_code: str, expected_message: str
) -> None:
    goldtier = NoGoldTierCalls()
    service = service_with(RaisingAcraConnector(error), goldtier)

    response, retrieved = await post_case(service)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == expected_code
    assert response.json()["detail"]["message"] == expected_message
    assert retrieved.json()["state"] == "FAILED"
    assert PRIVATE_SENTINEL not in response.text
    assert PRIVATE_SENTINEL not in retrieved.text
    assert goldtier.calls == []


@pytest.mark.anyio
async def test_browser_case_omits_internal_registry_source_link() -> None:
    service = OnboardingService(
        acra=MockAcraConnector(clock=lambda: FIXED_TIME),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: FIXED_TIME,
    )
    internal_case = service.create_case(VALID_SME_UEN)
    assert internal_case.entity is not None
    assert internal_case.entity.source.registry_source_link.endswith(VALID_SME_UEN)
    application = create_app(Settings(app_env="test"), onboarding_service=service)
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/onboarding/cases/{internal_case.case_id}")

    assert response.status_code == 200
    source = response.json()["entity"]["source"]
    assert source == {
        "source_system": "ACRA",
        "environment": "MOCK",
        "retrieved_at": FIXED_TIME.isoformat().replace("+00:00", "Z"),
    }
    assert "registry_source_link" not in response.text
    assert "mock.acra.gov.sg" not in response.text
