from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

import app.connectors.acra_bizfile_sandbox as bizfile_module
from app.connectors.acra_bizfile_sandbox import (
    AcraBizfileConnection,
    BizfileMockAcraConnector,
    BizfileMockCompanyDecoder,
    BizfileMockOfficersDecoder,
    BizfileMockOwnershipPartiesDecoder,
    NoAuthAcraAuthorizer,
)
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.errors import AcraConfigurationError, AcraMalformedResponseError

FIXED_TIME = datetime(2026, 9, 1, 4, 0, tzinfo=UTC)
SAFE_COMPANY_ENDPOINT = (
    "https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation"
)
SAFE_SHAREHOLDERS_ENDPOINT = (
    "https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/coShareholdersDetails"
)

COMPANY_RESPONSE: object = {
    "entities": [
        {
            "uen": "202400001A",
            "name": "MERLION CIRCULAR LABS PTE. LTD.",
            "entityRegistrationKeyDates": {"registrationDate": "2024-01-02"},
            "entityRegisteredAddressDetails": {
                "registeredAddress": {
                    "blkhseNo": "10",
                    "streetName": "ANSON ROAD",
                    "levelNo": "4",
                    "unitNo": "1",
                    "buildingName": "INTERNATIONAL PLAZA",
                    "postalCode": "079903",
                }
            },
            "entityConstnDetailsAndType": {
                "constitution": "PRIVATE COMPANY LIMITED BY SHARES"
            },
            "entityOfficersRecord": {
                "officerAppointmentDetails": [
                    {
                        "officerId": "OFFICER-1",
                        "officerName": "JANE TAN",
                        "position": "DIRECTOR",
                        "appointedDate": "2024-01-02",
                    }
                ]
            },
        }
    ]
}

SHAREHOLDERS_RESPONSE: object = {
    "entities": [
        {
            "uen": "202400001A",
            "name": "MERLION CIRCULAR LABS PTE. LTD.",
            "shareholders": {
                "individual": [
                    {
                        "shareholderCategory": "Corporate",
                        "shareholderId": "OWNER-1",
                        "shareholderName": "SYNTHETIC HOLDINGS PTE. LTD.",
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "OWNER-2",
                        "shareholderName": "WITHDRAWN PERSON",
                        "status": "Withdrawn",
                    },
                ],
                "grouping": [],
            },
        }
    ]
}


class RecordingTransport:
    def __init__(self, response: AcraHttpResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        self.calls.append((url, headers, timeout_seconds))
        return self.response


def test_module_imports_without_exposing_speculative_oauth_authorizer() -> None:
    assert bizfile_module.NoAuthAcraAuthorizer is NoAuthAcraAuthorizer
    assert not any(name.startswith("OAuth") for name in vars(bizfile_module))


def test_default_authorizer_preserves_current_no_auth_request_behavior() -> None:
    transport = RecordingTransport(AcraHttpResponse(status_code=404))
    connector = BizfileMockAcraConnector(
        connection=AcraBizfileConnection(timeout_seconds=7.5),
        transport=transport,
        clock=lambda: FIXED_TIME,
    )

    assert NoAuthAcraAuthorizer().authorization_headers() == {}
    assert connector.fetch_company(" 202400001a ") is None
    assert transport.calls == [
        (
            f"{SAFE_COMPANY_ENDPOINT}?uen=202400001A",
            {"Accept": "application/json"},
            7.5,
        )
    ]


def test_connection_remains_https_only() -> None:
    with pytest.raises(AcraConfigurationError):
        AcraBizfileConnection(base_url="http://api-sandbox.bizfile.gov.sg/api/acra")


def test_business_profile_helper_is_bounded_and_does_not_make_a_request() -> None:
    transport = RecordingTransport(AcraHttpResponse(status_code=500))
    connection = AcraBizfileConnection()

    endpoint = connection.business_profile_endpoint("11111999A")

    assert endpoint.endswith("/entityQuery/businessProfile?uen=11111999A")
    assert transport.calls == []


def test_existing_company_and_officer_decoding_is_preserved() -> None:
    company = BizfileMockCompanyDecoder().decode(
        COMPANY_RESPONSE,
        requested_uen="202400001A",
        source_endpoint=SAFE_COMPANY_ENDPOINT,
        retrieved_at=FIXED_TIME,
    )
    officers = BizfileMockOfficersDecoder().decode(
        COMPANY_RESPONSE,
        requested_uen="202400001A",
        source_endpoint=SAFE_COMPANY_ENDPOINT,
        retrieved_at=FIXED_TIME,
    )

    assert company.uen == "202400001A"
    assert company.entity_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert company.registration_date is not None
    assert company.registration_date.isoformat() == "2024-01-02"
    assert company.entity_status is None
    assert company.entity_type == "PRIVATE COMPANY LIMITED BY SHARES"
    assert company.registered_address is not None
    assert company.registered_address.unit == "#04-01"
    assert company.registered_address.country_code == "SG"
    assert officers.uen == "202400001A"
    assert len(officers.officers) == 1
    assert officers.officers[0].officer_id == "OFFICER-1"
    assert officers.officers[0].role == "DIRECTOR"


def test_existing_ownership_decoding_and_empty_relationship_behavior_are_preserved() -> None:
    ownership = BizfileMockOwnershipPartiesDecoder().decode(
        SHAREHOLDERS_RESPONSE,
        requested_uen="202400001A",
        source_endpoint=SAFE_SHAREHOLDERS_ENDPOINT,
        retrieved_at=FIXED_TIME,
    )
    connector = BizfileMockAcraConnector(
        connection=AcraBizfileConnection(),
        transport=RecordingTransport(AcraHttpResponse(status_code=200, body={})),
        clock=lambda: FIXED_TIME,
    )

    assert len(ownership.ownership_parties) == 1
    assert ownership.ownership_parties[0].party_id == "OWNER-1"
    assert ownership.ownership_parties[0].party_type == "LEGAL_ENTITY"
    assert ownership.ownership_parties[0].ownership_percentage is None
    relationships = connector.fetch_relationships("202400001A")
    assert relationships.relationships == ()
    assert relationships.source_endpoint == SAFE_SHAREHOLDERS_ENDPOINT


def test_connector_uses_query_free_provenance_and_strict_requested_identity() -> None:
    connector = BizfileMockAcraConnector(
        connection=AcraBizfileConnection(),
        transport=RecordingTransport(AcraHttpResponse(status_code=200, body=COMPANY_RESPONSE)),
        clock=lambda: FIXED_TIME,
    )

    company = connector.fetch_company("202400001A")

    assert company is not None
    assert company.source_endpoint == SAFE_COMPANY_ENDPOINT
    wrong_identity = {"entities": [{**COMPANY_RESPONSE["entities"][0], "uen": "202400002B"}]}  # type: ignore[index]
    wrong_connector = BizfileMockAcraConnector(
        connection=AcraBizfileConnection(),
        transport=RecordingTransport(AcraHttpResponse(status_code=200, body=wrong_identity)),
        clock=lambda: FIXED_TIME,
    )
    with pytest.raises(AcraMalformedResponseError):
        wrong_connector.fetch_company("202400001A")


def test_explicit_empty_entities_have_operation_specific_semantics() -> None:
    connector = BizfileMockAcraConnector(
        connection=AcraBizfileConnection(),
        transport=RecordingTransport(AcraHttpResponse(status_code=200, body={"entities": []})),
        clock=lambda: FIXED_TIME,
    )

    assert connector.fetch_company("11111999A") is None
    assert connector.fetch_officers("11111999A").officers == ()
    assert connector.fetch_ownership_parties("11111999A").ownership_parties == ()


def test_missing_or_multiple_entity_envelopes_remain_malformed() -> None:
    for body in ({}, {"entities": [COMPANY_RESPONSE["entities"][0]] * 2}):  # type: ignore[index]
        connector = BizfileMockAcraConnector(
            connection=AcraBizfileConnection(),
            transport=RecordingTransport(AcraHttpResponse(status_code=200, body=body)),
            clock=lambda: FIXED_TIME,
        )
        with pytest.raises(AcraMalformedResponseError):
            connector.fetch_company("202400001A")
