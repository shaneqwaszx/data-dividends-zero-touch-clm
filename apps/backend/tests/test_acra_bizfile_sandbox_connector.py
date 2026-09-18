from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal

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
from app.connectors.errors import AcraConfigurationError, AcraServiceUnavailableError
from app.connectors.garden_business_shareholders import GARDEN_BUSINESS_UEN, SIM_LIM_UEN

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

SIM_LIM_SHAREHOLDERS_RESPONSE: object = {
    "entities": [
        {
            "uen": SIM_LIM_UEN,
            "name": "SIM LIM PTE. LTD.",
            "shareholders": {
                "individual": [
                    {
                        "shareholderCategory": "Corporate",
                        "shareholderId": "T16UF3333A",
                        "shareholderName": "FORMER OWNER",
                        "shareAllotted": 10000,
                        "status": "Withdrawn",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S123AC1234E",
                        "shareholderName": "ABCD123",
                        "shareAllotted": 900,
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S2222222E",
                        "shareholderName": "TAN WEI LING",
                        "shareAllotted": 100,
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S23BT2997U",
                        "shareholderName": "EFGH2345",
                        "shareAllotted": 100,
                        "status": "Active",
                    },
                ]
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


class GardenBusinessTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        del headers, timeout_seconds
        self.calls.append(url)
        if f"uen={GARDEN_BUSINESS_UEN}" in url:
            return AcraHttpResponse(status_code=200, body={"entities": []})
        if f"uen={SIM_LIM_UEN}" in url:
            return AcraHttpResponse(status_code=200, body=SIM_LIM_SHAREHOLDERS_RESPONSE)
        raise AssertionError(f"unexpected endpoint: {url}")


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


def test_existing_ownership_decoding_and_relationship_fail_closed_behavior_are_preserved() -> None:
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
    with pytest.raises(AcraServiceUnavailableError):
        connector.fetch_relationships("202400001A")


def test_garden_business_synthetic_root_and_recursive_sim_lim_chain_are_bounded() -> None:
    transport = GardenBusinessTransport()
    connector = BizfileMockAcraConnector(
        connection=AcraBizfileConnection(),
        transport=transport,
        clock=lambda: FIXED_TIME,
    )

    ownership = connector.fetch_ownership_parties(GARDEN_BUSINESS_UEN)
    relationships = connector.fetch_relationships(GARDEN_BUSINESS_UEN)

    assert [party.party_id for party in ownership.ownership_parties] == [
        SIM_LIM_UEN,
        "S9988776F",
        "S123AC1234E",
        "S2222222E",
        "S23BT2997U",
    ]
    assert [
        (relationship.owned_entity_id, relationship.owner_party_id, relationship.ownership_percentage)
        for relationship in relationships.relationships
    ] == [
        (f"ENTITY_{GARDEN_BUSINESS_UEN}", SIM_LIM_UEN, Decimal("62.500000")),
        (f"ENTITY_{GARDEN_BUSINESS_UEN}", "S9988776F", Decimal("37.500000")),
        (SIM_LIM_UEN, "S123AC1234E", Decimal("81.818182")),
        (SIM_LIM_UEN, "S2222222E", Decimal("9.090909")),
        (SIM_LIM_UEN, "S23BT2997U", Decimal("9.090909")),
    ]
    assert len(transport.calls) == 4
