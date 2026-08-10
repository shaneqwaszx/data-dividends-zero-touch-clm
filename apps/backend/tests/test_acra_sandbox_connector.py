import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

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
    AcraUnexpectedConnectorError,
)
from app.mappers.acra import map_acra_company

FIXED_TIME = datetime(2026, 8, 10, 4, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "acra" / "synthetic_company_success.json"


class FakeAuthorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        return {"X-Synthetic-Authorization": "fixture-only-value"}


class FakeTransport:
    def __init__(
        self,
        response: AcraHttpResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        self.calls.append((url, headers, timeout_seconds))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def fixture_body() -> object:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert document["fixture_notice"].startswith("SYNTHETIC SANITIZED")
    return document["response"]


def build_connector(transport: FakeTransport) -> AcraSandboxConnector:
    return AcraSandboxConnector(
        connection=AcraSandboxConnection(
            base_url="https://sandbox.synthetic-acra.example",
            company_path_template="/business-profile/{uen}",
            timeout_seconds=7.5,
        ),
        transport=transport,
        authorizer=FakeAuthorizer(),
        decoder=ProjectAcraResponseDecoder(),
        clock=lambda: FIXED_TIME,
    )


def test_successful_source_response_is_parsed_into_acra_dto() -> None:
    transport = FakeTransport(AcraHttpResponse(status_code=200, body=fixture_body()))

    payload = build_connector(transport).fetch_company(" 202400001a ")

    assert payload is not None
    assert payload.uen == "202400001A"
    assert payload.entity_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert payload.registration_date is not None
    assert payload.registration_date.isoformat() == "2024-01-02"
    assert payload.entity_status == "LIVE"
    assert payload.registered_address is not None
    assert payload.registered_address.building_name == "SYNTHETIC CENTRE"
    assert payload.source_environment == "SANDBOX"
    assert payload.retrieved_at == FIXED_TIME
    assert transport.calls == [
        (
            "https://sandbox.synthetic-acra.example/business-profile/202400001A",
            {
                "X-Synthetic-Authorization": "fixture-only-value",
                "Accept": "application/json",
            },
            7.5,
        )
    ]


@pytest.mark.parametrize(
    ("unit", "building_name", "expected_unit", "expected_building", "expected_line_2"),
    [
        ("", "", None, None, None),
        ("   ", " \t ", None, None, None),
        ("  #04-01  ", None, "#04-01", None, "#04-01"),
        (None, "  SYNTHETIC CENTRE  ", None, "SYNTHETIC CENTRE", "SYNTHETIC CENTRE"),
        (
            "  #04-01  ",
            "  SYNTHETIC CENTRE  ",
            "#04-01",
            "SYNTHETIC CENTRE",
            "#04-01, SYNTHETIC CENTRE",
        ),
    ],
    ids=["empty", "whitespace", "unit-only", "building-only", "both"],
)
def test_optional_address_parts_are_normalized_before_canonical_mapping(
    unit: str | None,
    building_name: str | None,
    expected_unit: str | None,
    expected_building: str | None,
    expected_line_2: str | None,
) -> None:
    body = fixture_body()
    assert isinstance(body, dict)
    company = body["company"]
    assert isinstance(company, dict)
    address = company["registeredAddress"]
    assert isinstance(address, dict)
    address["unit"] = unit
    address["buildingName"] = building_name

    payload = build_connector(
        FakeTransport(AcraHttpResponse(status_code=200, body=body))
    ).fetch_company("202400001A")

    assert payload is not None
    assert payload.registered_address is not None
    assert payload.registered_address.unit == expected_unit
    assert payload.registered_address.building_name == expected_building
    canonical = map_acra_company(payload)
    assert canonical.registered_address is not None
    assert canonical.registered_address.address_line_2 == expected_line_2


def test_entity_status_is_trimmed_without_status_enum_assumptions() -> None:
    body = fixture_body()
    assert isinstance(body, dict)
    company = body["company"]
    assert isinstance(company, dict)
    company["entityStatus"] = "  SOURCE STATUS TEXT  "

    payload = build_connector(
        FakeTransport(AcraHttpResponse(status_code=200, body=body))
    ).fetch_company("202400001A")

    assert payload is not None
    assert payload.entity_status == "SOURCE STATUS TEXT"
    assert map_acra_company(payload).entity_status == "SOURCE STATUS TEXT"


def test_company_not_found_returns_none() -> None:
    connector = build_connector(FakeTransport(AcraHttpResponse(status_code=404)))

    assert connector.fetch_company("999999999Z") is None


@pytest.mark.parametrize("status_code", [408, 504])
def test_timeout_status_is_mapped_safely(status_code: int) -> None:
    connector = build_connector(FakeTransport(AcraHttpResponse(status_code=status_code)))

    with pytest.raises(AcraTimeoutError, match="timed out"):
        connector.fetch_company("202400001A")


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_unavailable_status_is_mapped_safely(status_code: int) -> None:
    connector = build_connector(FakeTransport(AcraHttpResponse(status_code=status_code)))

    with pytest.raises(AcraServiceUnavailableError, match="unavailable"):
        connector.fetch_company("202400001A")


@pytest.mark.parametrize("status_code", [401, 403])
def test_authentication_failure_is_mapped_safely(status_code: int) -> None:
    connector = build_connector(FakeTransport(AcraHttpResponse(status_code=status_code)))

    with pytest.raises(AcraAuthenticationError, match="authorized"):
        connector.fetch_company("202400001A")


@pytest.mark.parametrize(
    "response",
    [
        AcraHttpResponse(status_code=200, body=None),
        AcraHttpResponse(status_code=200, body={"company": {"uen": "WRONG"}}),
        AcraHttpResponse(status_code=418),
    ],
)
def test_malformed_or_unexpected_response_is_rejected(response: AcraHttpResponse) -> None:
    connector = build_connector(FakeTransport(response))

    with pytest.raises(AcraMalformedResponseError, match="unexpected response"):
        connector.fetch_company("202400001A")


def test_http_timeout_exception_is_sanitized() -> None:
    request = httpx.Request("GET", "https://sandbox.synthetic-acra.example")
    connector = build_connector(
        FakeTransport(error=httpx.ReadTimeout("private timeout detail", request=request))
    )

    with pytest.raises(AcraTimeoutError) as caught:
        connector.fetch_company("202400001A")

    assert "private timeout detail" not in str(caught.value)


def test_transport_failure_is_sanitized() -> None:
    request = httpx.Request("GET", "https://sandbox.synthetic-acra.example")
    connector = build_connector(
        FakeTransport(error=httpx.ConnectError("private network detail", request=request))
    )

    with pytest.raises(AcraServiceUnavailableError) as caught:
        connector.fetch_company("202400001A")

    assert "private network detail" not in str(caught.value)


def test_unexpected_connector_failure_is_sanitized() -> None:
    connector = build_connector(FakeTransport(error=RuntimeError("secret fixture value")))

    with pytest.raises(AcraUnexpectedConnectorError) as caught:
        connector.fetch_company("202400001A")

    assert caught.value.code == "ACRA_CONNECTOR_UNEXPECTED_FAILURE"
    assert "secret fixture value" not in str(caught.value)
