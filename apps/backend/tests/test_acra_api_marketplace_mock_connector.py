from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.errors import (
    AcraAuthenticationError,
    AcraMalformedResponseError,
    AcraOperationUnsupportedError,
    AcraServiceUnavailableError,
    AcraTimeoutError,
)
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.domain.models import RegistryAcquisitionStatus, WorkflowState
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository

FIXED_TIME = datetime(2026, 9, 26, 3, 0, tzinfo=UTC)
UEN = "202400001A"
TOKEN = "opaque-test-token"
COMPANY_ENDPOINT = (
    f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}"
    "/entityQuery/entityBasicInformation?uen=202400001A"
)
SHAREHOLDER_ENDPOINT = (
    f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}"
    "/entityQuery/coShareholdersDetails?uen=202400001A"
)

COMPANY_BODY: object = {
    "entities": [
        {
            "uen": UEN,
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
            "unknownProviderField": "ignored-at-source-boundary",
        }
    ]
}
SHAREHOLDERS_BODY: object = {
    "entities": [
        {
            "uen": UEN,
            "name": "MERLION CIRCULAR LABS PTE. LTD.",
            "shareholders": {
                "individual": [
                    {
                        "shareholderCategory": "Corporate",
                        "shareholderId": "OWNER-1",
                        "shareholderName": "SYNTHETIC HOLDINGS PTE. LTD.",
                        "status": "Active",
                        "shareAllotted": 5000,
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "OWNER-2",
                        "shareholderName": "WITHDRAWN PERSON",
                        "status": "Withdrawn",
                        "shareAllotted": 1000,
                    },
                ],
                "grouping": [],
            },
        }
    ]
}


class FixedAuthorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        return {"token": TOKEN}


class RecordingTransport:
    def __init__(
        self,
        responses: list[AcraHttpResponse],
        *,
        error: Exception | None = None,
    ) -> None:
        self.responses = responses
        self.error = error
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        self.calls.append((url, dict(headers), timeout_seconds))
        if self.error is not None:
            raise self.error
        return self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]


def connector(transport: RecordingTransport) -> AcraApiMarketplaceMockConnector:
    return AcraApiMarketplaceMockConnector(
        connection=AcraApiMarketplaceMockConnection(timeout_seconds=10),
        transport=transport,
        authorizer=FixedAuthorizer(),
        clock=lambda: FIXED_TIME,
    )


def test_entity_request_uses_exact_path_query_token_header_and_safe_provenance() -> None:
    transport = RecordingTransport([AcraHttpResponse(200, COMPANY_BODY)])

    company = connector(transport).fetch_company(" 202400001a ")

    assert company is not None
    assert company.uen == UEN
    assert company.entity_name == "MERLION CIRCULAR LABS PTE. LTD."
    assert company.source_environment == "MOCK"
    assert company.source_endpoint == COMPANY_ENDPOINT.split("?", 1)[0]
    assert transport.calls == [
        (
            COMPANY_ENDPOINT,
            {"token": TOKEN, "Accept": "application/json"},
            10,
        )
    ]
    assert "Authorization" not in transport.calls[0][1]
    assert "Bearer" not in str(transport.calls[0][1])


def test_embedded_officers_map_only_from_valid_entity_response() -> None:
    transport = RecordingTransport([AcraHttpResponse(200, COMPANY_BODY)])

    officers = connector(transport).fetch_officers(UEN)

    assert len(officers.officers) == 1
    assert officers.officers[0].officer_id == "OFFICER-1"
    assert officers.officers[0].role == "DIRECTOR"
    assert transport.calls[0][0] == COMPANY_ENDPOINT


def test_shareholder_request_maps_identity_category_status_and_exact_share_count() -> None:
    transport = RecordingTransport([AcraHttpResponse(200, SHAREHOLDERS_BODY)])

    ownership = connector(transport).fetch_ownership_parties(UEN)

    assert len(ownership.ownership_parties) == 2
    holder = ownership.ownership_parties[0]
    assert holder.party_id == "OWNER-1"
    assert holder.party_type == "LEGAL_ENTITY"
    assert holder.source_category == "Corporate"
    assert holder.source_status == "Active"
    assert holder.share_allotted == Decimal("5000")
    assert holder.ownership_percentage is None
    withdrawn = ownership.ownership_parties[1]
    assert withdrawn.party_id == "OWNER-2"
    assert withdrawn.party_type == "NATURAL_PERSON"
    assert withdrawn.source_status == "Withdrawn"
    assert withdrawn.share_allotted == Decimal("1000")
    assert withdrawn.ownership_percentage is None
    assert transport.calls == [
        (
            SHAREHOLDER_ENDPOINT,
            {"token": TOKEN, "Accept": "application/json"},
            10,
        )
    ]


def test_nonempty_grouping_fails_closed_pending_provider_semantics() -> None:
    body = {
        "entities": [
            {
                **SHAREHOLDERS_BODY["entities"][0],  # type: ignore[index]
                "shareholders": {
                    "individual": [],
                    "grouping": [
                        {
                            "shareholderCategory": "Corporate",
                            "shareholderId": "GROUP-1",
                            "shareholderName": "GROUP HOLDER",
                            "status": "Active",
                            "shareAllotted": 1,
                        }
                    ],
                },
            }
        ]
    }

    with pytest.raises(AcraMalformedResponseError):
        connector(RecordingTransport([AcraHttpResponse(200, body)])).fetch_ownership_parties(
            UEN
        )


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"entities": "not-an-array"},
        {"entities": [COMPANY_BODY["entities"][0]] * 2},  # type: ignore[index]
        {
            "entities": [
                {
                    **COMPANY_BODY["entities"][0],  # type: ignore[index]
                    "uen": "202400002B",
                }
            ]
        },
    ],
)
def test_malformed_ambiguous_or_mismatched_entity_fails_closed(body: object) -> None:
    with pytest.raises(AcraMalformedResponseError):
        connector(RecordingTransport([AcraHttpResponse(200, body)])).fetch_company(UEN)


def test_explicit_empty_entities_has_operation_specific_semantics() -> None:
    empty = AcraHttpResponse(200, {"entities": []})

    assert connector(RecordingTransport([empty])).fetch_company(UEN) is None
    ownership = connector(RecordingTransport([empty])).fetch_ownership_parties(UEN)
    assert ownership.ownership_parties == ()
    with pytest.raises(AcraMalformedResponseError):
        connector(RecordingTransport([empty])).fetch_officers(UEN)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, AcraAuthenticationError),
        (403, AcraAuthenticationError),
        (408, AcraTimeoutError),
        (504, AcraTimeoutError),
        (429, AcraServiceUnavailableError),
        (500, AcraServiceUnavailableError),
        (404, AcraMalformedResponseError),
    ],
)
def test_provider_statuses_map_to_safe_errors(
    status: int,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type) as caught:
        connector(RecordingTransport([AcraHttpResponse(status)])).fetch_company(UEN)

    assert TOKEN not in f"{caught.value!s} {caught.value!r}"


@pytest.mark.parametrize(
    ("error", "error_type"),
    [
        (httpx.ReadTimeout("safe"), AcraTimeoutError),
        (httpx.ConnectError("safe"), AcraServiceUnavailableError),
    ],
)
def test_provider_transport_failures_are_sanitized(
    error: Exception,
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type) as caught:
        connector(RecordingTransport([], error=error)).fetch_company(UEN)

    assert TOKEN not in f"{caught.value!s} {caught.value!r}"


def test_missing_body_represents_content_type_or_size_rejection() -> None:
    invalid = (
        AcraHttpResponse(200, None),
        AcraHttpResponse(200, COMPANY_BODY, content_type="text/html", response_bytes=100),
        AcraHttpResponse(
            200,
            COMPANY_BODY,
            content_type="application/json",
            response_bytes=262_145,
            size_limit_exceeded=True,
        ),
    )
    for response in invalid:
        with pytest.raises(AcraMalformedResponseError):
            connector(RecordingTransport([response])).fetch_company(UEN)


def test_authentication_status_cannot_be_hidden_by_an_empty_envelope() -> None:
    with pytest.raises(AcraAuthenticationError):
        connector(
            RecordingTransport([AcraHttpResponse(401, {"entities": []})])
        ).fetch_company(UEN)


def test_relationships_are_unsupported_without_a_provider_call() -> None:
    transport = RecordingTransport([AcraHttpResponse(500)])

    with pytest.raises(AcraOperationUnsupportedError):
        connector(transport).fetch_relationships(UEN)
    assert transport.calls == []


def test_acquisition_distinguishes_empty_shareholders_from_unsupported_relationships() -> None:
    from app.connectors.registry import AcraRegistryProviderAdapter
    from app.domain.models import RegistryOperationStatus

    transport = RecordingTransport([
        AcraHttpResponse(200, COMPANY_BODY),
        AcraHttpResponse(200, COMPANY_BODY),
        AcraHttpResponse(200, {"entities": []}),
    ])
    bundle = AcraRegistryProviderAdapter(connector(transport)).retrieve_acquisition(UEN)
    assert bundle is not None
    assert bundle.status == RegistryAcquisitionStatus.PARTIAL
    shareholder, relationship = bundle.operation_results[2:]
    assert shareholder.status == RegistryOperationStatus.EMPTY
    assert shareholder.provenance is not None
    assert relationship.status == RegistryOperationStatus.UNSUPPORTED
    assert relationship.provenance is None
    assert relationship.error is None
    assert relationship.record_count == 0
    assert len(transport.calls) == 3

    from pydantic import ValidationError

    from app.domain.models import RegistryAcquisitionBundle, RegistryOperationResult

    unsupported = relationship.model_dump(mode="python")
    with pytest.raises(ValidationError):
        RegistryOperationResult.model_validate({**unsupported, "record_count": 1})
    with pytest.raises(ValidationError):
        RegistryOperationResult.model_validate(
            {**unsupported, "provenance": shareholder.provenance}
        )
    # A serialized bundle accepts the new status without inventing observed evidence.
    assert RegistryAcquisitionBundle.model_validate_json(bundle.model_dump_json()) == bundle


def test_present_entity_without_confirmed_shareholder_collection_is_not_empty() -> None:
    transport = RecordingTransport([
        AcraHttpResponse(200, {"entities": [{"uen": UEN, "name": "Synthetic company"}]}),
    ])
    with pytest.raises(AcraMalformedResponseError):
        connector(transport).fetch_ownership_parties(UEN)


def test_official_company_shareholder_dispatch_is_not_used_for_partnerships() -> None:
    from app.connectors.registry import AcraRegistryProviderAdapter
    from app.domain.models import RegistryOperationStatus

    body = deepcopy(COMPANY_BODY)
    assert isinstance(body, dict)
    body["entities"][0]["entityConstnDetailsAndType"] = {"constitution": "PARTNERSHIP"}
    transport = RecordingTransport([AcraHttpResponse(200, body), AcraHttpResponse(200, body)])
    bundle = AcraRegistryProviderAdapter(
        connector(transport), company_shareholders_only=True,
    ).retrieve_acquisition(UEN)
    assert bundle is not None
    assert bundle.operation_results[2].status == RegistryOperationStatus.UNSUPPORTED
    assert len(transport.calls) == 2
    assert not any("coShareholdersDetails" in url for url, _, _ in transport.calls)


def test_official_mock_missing_identity_still_stops_application_without_fallback() -> None:
    company = {
        "entities": [
            {
                "uen": UEN,
                "name": "MERLION CIRCULAR LABS PTE. LTD.",
                "entityConstnDetailsAndType": {
                    "constitution": "PRIVATE COMPANY LIMITED BY SHARES"
                },
                "entityOfficersRecord": {"officerAppointmentDetails": []},
            }
        ]
    }
    transport = RecordingTransport(
        [
            AcraHttpResponse(200, company),
            AcraHttpResponse(200, company),
            AcraHttpResponse(200, {"entities": []}),
        ]
    )
    service = OnboardingService(
        acra=connector(transport),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: FIXED_TIME,
    )

    case = service.create_staged_case(UEN)

    assert case.state == WorkflowState.REVIEW_REQUIRED
    assert case.error is not None
    assert case.error.code == "CANONICAL_DATA_INCOMPLETE"
    assert case.registry_acquisition is not None
    assert case.registry_acquisition.status == RegistryAcquisitionStatus.PARTIAL
    assert case.registry_acquisition.entity_profile.source.environment.value == "MOCK"
    assert [call[0] for call in transport.calls] == [
        COMPANY_ENDPOINT,
        COMPANY_ENDPOINT,
        SHAREHOLDER_ENDPOINT,
    ]
