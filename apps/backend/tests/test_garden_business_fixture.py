"""Bounded Garden Business Mock fixture and ordinary-pipeline regressions."""

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.connectors.garden_business import (
    GARDEN_BUSINESS_UEN,
    GARDEN_DIRECT_SHAREHOLDERS,
    SIM_LIM_DIRECT_SHAREHOLDERS,
    SIM_LIM_UEN,
    derive_garden_ownership,
)
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.models import RegistryAcquisitionStatus
from app.domain.ownership import OwnershipAnalysisState, OwnershipCandidateClassification
from app.main import create_app
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 9, 22, 4, 0, tzinfo=UTC)


def _service() -> OnboardingService:
    return OnboardingService(
        acra=MockAcraConnector(clock=lambda: NOW),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: NOW,
    )


def _synthetic_pdf(fields: Mapping[str, str]) -> bytes:
    lines = ["SYNTHETIC TEST DATA", "CORPORATE PROFILE"]
    lines.extend(f"{label}: {value}" for label, value in fields.items())
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    operations = "BT /F1 12 Tf 72 720 Td "
    operations += " Tj 0 -16 Td ".join(f"({line})" for line in escaped)
    operations += " Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(operations.encode('latin-1'))} >>\nstream\n{operations}\nendstream",
    ]
    output = "%PDF-1.4\n"
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output.encode("latin-1")))
        output += f"{index} 0 obj\n{item}\nendobj\n"
    xref = len(output.encode("latin-1"))
    output += "xref\n0 6\n0000000000 65535 f \n"
    output += "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    output += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return output.encode("latin-1")


def test_garden_fixture_shape_order_percentages_and_withdrawn_exclusion() -> None:
    parties, relationships = derive_garden_ownership()

    assert [party.party_id for party in parties] == [
        SIM_LIM_UEN,
        "S9988776F",
        "S123AC1234E",
        "S2222222E",
        "S23BT2997U",
    ]
    assert "T16UF3333A" not in {party.party_id for party in parties}
    assert [relationship.ownership_percentage for relationship in relationships] == [
        Decimal("62.500000"),
        Decimal("37.500000"),
        Decimal("81.818182"),
        Decimal("9.090909"),
        Decimal("9.090909"),
    ]
    assert len({item.relationship_id for item in relationships}) == len(relationships)


@pytest.mark.parametrize("bad_share", (None, 0, -1, 1.5))
def test_garden_fixture_rejects_missing_nonpositive_or_binary_float_shares(
    bad_share: object,
) -> None:
    malformed = [dict(item) for item in GARDEN_DIRECT_SHAREHOLDERS]
    if bad_share is None:
        malformed[0].pop("shareAllotted")
    else:
        malformed[0]["shareAllotted"] = bad_share

    with pytest.raises((ValidationError, ValueError)):
        derive_garden_ownership(
            garden_shareholders=malformed,
            sim_lim_shareholders=SIM_LIM_DIRECT_SHAREHOLDERS,
        )


def test_garden_fixture_rejects_malformed_or_duplicate_owner_identity() -> None:
    malformed = [dict(item) for item in GARDEN_DIRECT_SHAREHOLDERS]
    malformed[0]["party_id"] = "unsafe owner"
    with pytest.raises(ValidationError):
        derive_garden_ownership(
            garden_shareholders=malformed,
            sim_lim_shareholders=SIM_LIM_DIRECT_SHAREHOLDERS,
        )

    duplicated = [dict(item) for item in SIM_LIM_DIRECT_SHAREHOLDERS]
    duplicated[1]["party_id"] = "S9988776F"
    with pytest.raises(ValueError, match="unique"):
        derive_garden_ownership(
            garden_shareholders=GARDEN_DIRECT_SHAREHOLDERS,
            sim_lim_shareholders=duplicated,
        )


def test_garden_mock_acquisition_feeds_the_existing_decimal_engine() -> None:
    service = _service()
    case = service.create_staged_case(GARDEN_BUSINESS_UEN)
    acquisition = case.registry_acquisition
    assert acquisition is not None
    assert acquisition.status == RegistryAcquisitionStatus.COMPLETE
    assert acquisition.officers == ()
    assert [party.party_id for party in acquisition.ownership_parties] == [
        SIM_LIM_UEN,
        "S9988776F",
        "S123AC1234E",
        "S2222222E",
        "S23BT2997U",
    ]

    ownership = OwnershipAnalysisService(
        cases=service,
        provider=RegistryAcquisitionOwnershipProvider(service),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=lambda: NOW,
    )
    ownership.load(case_id=case.case_id)
    analyzed = ownership.analyze(case_id=case.case_id)
    by_party = {candidate.party.party_id: candidate for candidate in analyzed.candidates}

    assert analyzed.state == OwnershipAnalysisState.ANALYZED
    assert by_party["S9988776F"].direct_ownership_percent == Decimal("37.500000")
    assert by_party["S123AC1234E"].aggregated_ownership_percent == Decimal("51.13636375")
    assert by_party["S2222222E"].aggregated_ownership_percent == Decimal("5.681818125")
    assert by_party["S23BT2997U"].aggregated_ownership_percent == Decimal("5.681818125")
    assert by_party["S123AC1234E"].classification == (
        OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
    )
    assert by_party["S9988776F"].classification == (
        OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
    )


def test_garden_reaches_normal_mock_completion_without_external_network() -> None:
    client = TestClient(
        create_app(Settings(app_env="test", idp_connector_mode="local_pdf_text"))
    )
    created = client.post("/api/clm/zero-touch/cases", json={"uen": GARDEN_BUSINESS_UEN})
    assert created.status_code == 201
    created_payload = created.json()
    case_id = created_payload["case"]["case_id"]
    assert created_payload["status"] == "PENDING_INPUTS"
    assert {item["status"] for item in created_payload["target_operations"]} == {
        "NOT_ATTEMPTED"
    }
    completed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "garden-profile.pdf"},
        content=_synthetic_pdf(
            {
                "Legal Name": "GARDEN BUSINESS",
                "UEN": GARDEN_BUSINESS_UEN,
                "Registered Address": "18 GARDEN WALK, #01-01, 018919, SG",
                "Country": "SG",
            }
        ),
    )

    assert completed.status_code == 200
    payload = completed.json()
    assert payload["status"] == "COMPLETED"
    assert payload["clm"]["status"] == "MOCK_GOLDTIER_SUBMITTED"
    assert [item["operation"] for item in payload["target_operations"]] == [
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
    ]
    assert [item["status"] for item in payload["target_operations"]] == [
        "NO_MATCH",
        "CREATED",
        "CREATED",
        "SUCCESS",
    ]


def test_unknown_uens_and_standard_mock_scenario_remain_unchanged() -> None:
    connector = MockAcraConnector(clock=lambda: NOW)

    assert connector.fetch_company("999999999Z") is None
    standard = connector.fetch_company("202400001A")
    assert standard is not None
    assert standard.entity_name == "MERLION CIRCULAR LABS PTE. LTD."
    standard_percentages = [
        item.ownership_percentage
        for item in connector.fetch_relationships("202400001A").relationships
    ]
    assert standard_percentages == [
        Decimal("60"),
        Decimal("40"),
    ]
