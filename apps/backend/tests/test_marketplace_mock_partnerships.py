"""D-112: Marketplace Mock partnerships take their registry partners from current partner officers.

The fixture follows the ACRA API Marketplace Mock sample record for T19PF1111A (fictional
XYZ ACCOUNTING); officer ids are replaced with synthetic ones.
"""

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from test_zero_touch_database_happy_path import RecordingTarget, sandbox_settings
from test_zero_touch_entity_types import (
    agreement_document,
    blockers,
    complete,
    create,
    observed_bindings,
    submit_partners,
    upload,
)

from app.connectors.acra_api_marketplace_mock import (
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.errors import AcraMalformedResponseError
from app.connectors.registry import AcraRegistryProviderAdapter
from app.domain.models import RegistryAcquisitionStatus, RegistryOperationStatus
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.partnership_agreement import (
    partnership_agreement_issues,
    registry_partner_names,
)

FIXED_TIME = datetime(2026, 11, 2, 3, 0, tzinfo=UTC)
XYZ = SimpleNamespace(uen="T19PF1111A", name="XYZ ACCOUNTING")
XYZ_ROOT = f"ENTITY_{XYZ.uen}"
ADDRESS = "114 JURONG STREET 1, #09-19, ROBINSONS, 879909, SG"

OFFICERS = [
    {"officerId": "XYZ-OFFICER-1", "officerName": "TAN WEI LING", "position": "Partner",
     "appointedDate": "2019-11-29", "status": "Active"},
    {"officerId": "XYZ-OFFICER-2", "officerName": "LILY",
     "position": "PARTNER UNDER SECTION 18(3)(C) OF THE ACCOUNTANTS ACT",
     "appointedDate": "2019-11-29", "status": "Active"},
    {"officerId": "XYZ-OFFICER-3", "officerName": "RAIN JORDON",
     "position": "PUBLIC ACCOUNTANT EMPLOYEE", "appointedDate": "2019-11-29", "status": "Active"},
    {"officerId": "XYZ-OFFICER-4", "officerName": "ALLIE", "position": "Partner",
     "appointedDate": "2019-11-29", "status": "Withdrawn", "withdrawalDate": "2019-12-31",
     "withdrawalReason": "Others"},
]


def entity_body(officers=OFFICERS, constitution="PARTNERSHIP") -> dict:
    return {"entities": [{
        "uen": XYZ.uen,
        "name": XYZ.name,
        "entityRegistrationKeyDates": {"registrationDate": "2019-11-29"},
        "entityRegisteredAddressDetails": {"registeredAddress": {
            "blkhseNo": "114", "streetName": "JURONG STREET 1", "levelNo": "9",
            "unitNo": "19", "buildingName": "ROBINSONS", "postalCode": "879909",
        }},
        "entityConstnDetailsAndType": {"constitution": constitution},
        "entityOfficersRecord": {"officerAppointmentDetails": deepcopy(officers)},
    }]}


class RoutedTransport:
    """The official Mock by operation path; the shareholder lookup is never expected."""

    def __init__(self, body: object) -> None:
        self.body = body
        self.paths: list[str] = []

    def get(self, url: str, *, headers: Mapping[str, str], timeout_seconds: float):
        path = urlsplit(url).path
        self.paths.append(path.rsplit("/", 1)[-1])
        if path.endswith("/entityBasicInformation"):
            return AcraHttpResponse(200, self.body)
        if path.endswith("/coShareholdersDetails"):
            return AcraHttpResponse(200, {"entities": []})
        return AcraHttpResponse(500)


class FixedAuthorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        return {"token": "opaque-test-token"}


def connector(transport: RoutedTransport, clock=lambda: FIXED_TIME):
    return AcraApiMarketplaceMockConnector(
        connection=AcraApiMarketplaceMockConnection(timeout_seconds=10),
        transport=transport,
        authorizer=FixedAuthorizer(),
        clock=clock,
    )


def acquire(body: object, *, company_shareholders_only: bool = True):
    return AcraRegistryProviderAdapter(
        connector(RoutedTransport(body)), company_shareholders_only=company_shareholders_only,
    ).retrieve_acquisition(XYZ.uen)


# --- M1 / M2: the Mock connector ---------------------------------------------------------------


def test_listed_partner_positions_become_partner_and_other_positions_are_unchanged():
    officers = connector(RoutedTransport(entity_body())).fetch_officers(XYZ.uen).officers

    assert [(item.name, item.role, item.cessation_date) for item in officers] == [
        ("TAN WEI LING", "PARTNER", None),
        ("LILY", "PARTNER", None),
        ("RAIN JORDON", "PUBLIC ACCOUNTANT EMPLOYEE", None),
        ("ALLIE", "PARTNER", datetime(2019, 12, 31).date()),
    ]


@pytest.mark.parametrize(
    "position",
    ["SECRETARY (ACTING)", "PARTNER UNDER SECTION 18(3)(D) OF THE ACCOUNTANTS ACT",
     "PARTNER (MANAGING)"],
)
def test_an_unlisted_position_with_brackets_still_fails_the_officers_operation(position):
    officers = [*OFFICERS[:2], {**OFFICERS[2], "position": position}]

    with pytest.raises(AcraMalformedResponseError):
        connector(RoutedTransport(entity_body(officers))).fetch_officers(XYZ.uen)
    bundle = acquire(entity_body(officers))
    assert bundle is not None
    assert bundle.status == RegistryAcquisitionStatus.FAILED
    assert [item.code for item in bundle.issues] == ["REGISTRY_OPERATION_MALFORMED_RESPONSE"]
    assert registry_partner_names(bundle) == ()


@pytest.mark.parametrize("status", ["Withdrawn", "Ceased", "", 3])
def test_a_partner_not_active_without_a_withdrawal_date_fails_closed(status):
    officers = [*OFFICERS[:3], {**OFFICERS[3], "status": status}]
    del officers[3]["withdrawalDate"]

    with pytest.raises(AcraMalformedResponseError):
        connector(RoutedTransport(entity_body(officers))).fetch_officers(XYZ.uen)


def test_a_non_partner_row_keeps_todays_status_handling():
    officers = [*OFFICERS[:2], {**OFFICERS[2], "status": "Withdrawn"}]

    roles = [item.role for item in
             connector(RoutedTransport(entity_body(officers))).fetch_officers(XYZ.uen).officers]
    assert roles == ["PARTNER", "PARTNER", "PUBLIC ACCOUNTANT EMPLOYEE"]


# --- M3: registry partners ---------------------------------------------------------------------


def test_registry_partners_are_the_current_partner_officers_only():
    bundle = acquire(entity_body())

    assert bundle is not None
    assert bundle.status == RegistryAcquisitionStatus.PARTIAL
    assert [item.status for item in bundle.operation_results[2:]] == [
        RegistryOperationStatus.UNSUPPORTED, RegistryOperationStatus.UNSUPPORTED,
    ]
    assert registry_partner_names(bundle) == ("TAN WEI LING", "LILY")


def test_garden_style_owner_officers_give_no_registry_partners():
    officers = [{**item, "position": "Owner"} for item in OFFICERS]

    bundle = acquire(entity_body(officers))
    assert bundle is not None
    assert [item.role for item in bundle.officers] == ["Owner"] * 4
    assert registry_partner_names(bundle) == ()


def test_officer_partners_are_used_only_when_the_shareholder_lookup_was_skipped():
    # Without the Marketplace company-only dispatch the shareholder lookup runs (here EMPTY),
    # so officers never stand in for registry partners.
    bundle = acquire(entity_body(), company_shareholders_only=False)
    assert bundle is not None
    assert bundle.operation_results[2].status == RegistryOperationStatus.EMPTY
    assert registry_partner_names(bundle) == ()


def test_officer_partners_are_not_used_for_a_company():
    bundle = acquire(entity_body(constitution="PRIVATE COMPANY LIMITED BY SHARES"),
                     company_shareholders_only=True)
    assert bundle is not None
    assert registry_partner_names(bundle) == ()


def agreement_issues(shares) -> tuple[str, ...]:
    rows = [SimpleNamespace(
        owner_name=name, explicit_percentage=Decimal(share), extraction_quality="HIGH",
        evidence_score=0.99, owned_entity_registration_identifier=XYZ.uen,
    ) for name, share in shares]
    return partnership_agreement_issues(
        registry_partners=registry_partner_names(acquire(entity_body())), rows=rows,
        root_uen=XYZ.uen, confidence_threshold=0.8,
    )


@pytest.mark.parametrize("extra", ["ALLIE", "RAIN JORDON"])
def test_an_agreement_naming_a_non_partner_fails_the_d101_checks(extra):
    assert agreement_issues((("TAN WEI LING", "60"), ("LILY", "40"))) == ()
    assert agreement_issues((("TAN WEI LING", "50"), ("LILY", "30"), (extra, "20"))) == (
        "PARTNERSHIP_EXTRA_PARTNER_IN_AGREEMENT",
    )


# --- End to end on the Mock lane (API) ---------------------------------------------------------

IDENTITY_LINES = (
    "FICTIONAL FYP TEST DATA - SYNTHETIC ONBOARDING FORM",
    f"Legal Name: {XYZ.name}",
    f"UEN: {XYZ.uen}",
    f"Registered Address: {ADDRESS}",
    "Country: SG",
    "KYC Customer Type: Partnership - Unregulated",
    "Client Segment: Corporate",
    "Registration Type: ACRA",
    "Customer External System: DSD",
    "Policy: Singapore",
    "Booking Entity: ANZBGL (Singapore Branch)",
)


def agreement_lines(shares) -> tuple[str, ...]:
    return (
        "FICTIONAL FYP TEST DATA - SYNTHETIC PARTNERSHIP AGREEMENT",
        f"Legal Name: {XYZ.name}",
        f"UEN: {XYZ.uen}",
        f"Registered Address: {ADDRESS}",
        "Country: SG",
        "Agreement Date: 2020-01-02",
        *(f"Partner Share: {name}: {value} percent: NATURAL_PERSON" for name, value in shares),
        *(f"Signing Partner: {name}" for name, _ in shares),
    )


XYZ_SHARES = [("TAN WEI LING", "60"), ("LILY", "40")]


@contextmanager
def mock_lane() -> Iterator[tuple[TestClient, RoutedTransport]]:
    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    transport = RoutedTransport(entity_body())
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(
            # The registry cache refuses evidence from the future, so the API lane uses now.
            settings, acra_connector=connector(transport, clock=lambda: datetime.now(UTC)),
            goldtier_transport=RecordingTarget(XYZ.name, XYZ.uen),
        )) as client,
    ):
        yield client, transport


def xyz_at_ownership(client, shares=XYZ_SHARES) -> dict:
    current = create(client, XYZ)
    upload(client, current, IDENTITY_LINES, "identity.txt")
    upload(client, current, agreement_lines(shares), "agreement.txt")
    return complete(client, current, 2)


def xyz_declaration(client, current) -> dict:
    document = agreement_document(client, current)
    rows = [item for item in document["ownership_observations"]
            if "_PARTNER_SHARE_ROW_" in item["source_reference"]]
    parties = [{"party_id": XYZ_ROOT, "display_name": XYZ.name, "party_type": "LEGAL_ENTITY",
                "registration_number": XYZ.uen, "country": "SG"}]
    relationships = []
    for index, item in enumerate(rows, 1):
        parties.append({"party_id": f"PARTNER_{index}", "display_name": item["owner_name"],
                        "party_type": "NATURAL_PERSON", "country": "SG"})
        relationships.append({"relationship_id": f"SHARE_{index}", "parent_party_id": XYZ_ROOT,
                              "child_party_id": f"PARTNER_{index}",
                              "ownership_percent": str(item["explicit_percentage"])})
    return {
        "root_registration_number": XYZ.uen,
        "evidence_document_id": document["document_id"],
        "evidence_document_version": len(document["events"]),
        "as_of_date": "2020-01-02",
        "rationale": "Reviewed synthetic partnership agreement shares.",
        "source_selection": "DOCUMENT_OBSERVATIONS",
        "observed_document_versions": observed_bindings(client, current),
        "selected_observation_ids": [item["observation_id"] for item in rows],
        "root_party_id": XYZ_ROOT,
        "parties": parties,
        "relationships": relationships,
        "expected_automation_version": current["version"],
        "expected_ownership_version": current["ownership_recovery"]["version"],
        "expected_case_event_count": len(current["case"]["events"]),
    }


def test_xyz_partnership_reaches_rm_confirmed_shares_on_the_mock_lane():
    with mock_lane() as (client, transport):
        current = xyz_at_ownership(client)
        assert current["current_stage"] == "OWNERSHIP", blockers(current)
        assert current["entity_type_basis"]["partnership_state"] == "AWAITING_RM_CONFIRMATION"
        assert "coShareholdersDetails" not in transport.paths

        response = submit_partners(client, current, xyz_declaration(client, current))
        assert response.status_code == 200, response.json()
        current = response.json()
        assert "OWNERSHIP_REVIEW_REQUIRED" not in current["clm"]["readiness"]["blockers"]
        assert current["entity_type_basis"]["label"] == (
            "Partner shares from partnership agreement, RM-confirmed"
        )
        ownership = client.get(
            f"/api/onboarding/cases/{current['case']['case_id']}/ownership"
        ).json()
        assert ownership["state"] == "ANALYZED"
        assert {
            item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
            for item in ownership["candidates"]
            if item["classification"] == "PROVISIONAL_UBO_CANDIDATE"
        } == {"TAN WEI LING": Decimal("60"), "LILY": Decimal("40")}


@pytest.mark.parametrize(
    "shares",
    [
        [("TAN WEI LING", "50"), ("LILY", "30"), ("ALLIE", "20")],
        [("TAN WEI LING", "50"), ("LILY", "30"), ("RAIN JORDON", "20")],
        [("TAN WEI LING", "60"), ("ALLIE", "40")],
    ],
    ids=["withdrawn-partner-added", "employee-added", "withdrawn-partner-instead"],
)
def test_xyz_agreement_naming_allie_or_rain_jordon_keeps_the_case_blocked(shares):
    with mock_lane() as (client, _):
        current = xyz_at_ownership(client, shares)
        before = (current["version"], blockers(current), current["current_stage"])
        response = submit_partners(client, current, xyz_declaration(client, current))
        assert response.status_code in {409, 422}, response.json()
        after = client.get(f"/api/clm/zero-touch/cases/{current['case']['case_id']}").json()
        assert (after["version"], blockers(after), after["current_stage"]) == before
        assert "OWNERSHIP_REVIEW_REQUIRED" in after["clm"]["readiness"]["blockers"]
