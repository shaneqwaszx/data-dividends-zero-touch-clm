"""Bounded Garden Business Mock fixture and ordinary-pipeline regressions."""

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api_models import BrowserTargetOperationEvidence, project_processing_pipeline
from app.config import Settings
from app.connectors.garden_business import (
    GARDEN_BUSINESS_UEN,
    GARDEN_DIRECT_SHAREHOLDERS,
    SIM_LIM_DIRECT_SHAREHOLDERS,
    SIM_LIM_UEN,
    derive_garden_ownership,
)
from app.connectors.idp import IdpDocumentInput
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.clm import GoldTierSearchDisposition
from app.domain.documents import DocumentFieldKey, DocumentProfile
from app.domain.models import RegistryAcquisitionStatus
from app.domain.ownership import OwnershipAnalysisState, OwnershipCandidateClassification
from app.domain.policy import (
    CasePolicySnapshot,
    EvidenceClassifierPolicy,
    OwnershipDiscoveryPolicySnapshot,
    RegistryPolicySnapshot,
)
from app.domain.zero_touch import AutomationStage, AutomationStatus
from app.main import create_app
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_discovery import OwnershipDiscoveryCoordinator
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 9, 22, 4, 0, tzinfo=UTC)


def test_garden_synthetic_profile_uses_real_local_pdf_parser_and_binds_identity() -> None:
    parsed = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=_synthetic_pdf(
                {
                    "Legal Name": "GARDEN BUSINESS",
                    "UEN": GARDEN_BUSINESS_UEN,
                    "Registered Address": "18 GARDEN WALK, #01-01, 018919, SG",
                    "Country": "SG",
                }
            ),
        )
    )
    values = {field.field_key: field.value for field in parsed.fields}  # type: ignore[attr-defined]

    assert values == {
        DocumentFieldKey.LEGAL_NAME: "GARDEN BUSINESS",
        DocumentFieldKey.REGISTRATION_NUMBER: GARDEN_BUSINESS_UEN,
        DocumentFieldKey.REGISTERED_ADDRESS: "18 GARDEN WALK, #01-01, 018919, SG",
        DocumentFieldKey.COUNTRY_OF_INCORPORATION: "SG",
    }
    assert values[DocumentFieldKey.LEGAL_NAME] == "GARDEN BUSINESS"
    assert values[DocumentFieldKey.REGISTRATION_NUMBER] == GARDEN_BUSINESS_UEN


def _service() -> OnboardingService:
    return OnboardingService(
        acra=MockAcraConnector(clock=lambda: NOW),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: NOW,
        policy_snapshot_provider=lambda: CasePolicySnapshot(
            snapshot_label="SYNTHETIC_GARDEN_DISCOVERY",
            catalogue_version=1,
            idp_review_confidence_threshold=Decimal("0.85"),
            ubo_threshold_percent=Decimal("25.000000"),
            registry=RegistryPolicySnapshot(),
            evidence_classifier=EvidenceClassifierPolicy(),
            ownership_discovery=OwnershipDiscoveryPolicySnapshot(
                trace_threshold_percent=Decimal("10"),
                max_corporate_depth=5,
                call_budget_enabled=False,
                call_budget_max=10,
            ),
            policy_identity="b" * 64,
            bound_at=NOW,
        ),
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
    # Garden's own record holds only its direct owners; SIM LIM is a separate issuer.
    assert [party.party_id for party in acquisition.ownership_parties] == [
        SIM_LIM_UEN,
        "S9988776F",
    ]

    ownership = OwnershipAnalysisService(
        cases=service,
        provider=RegistryAcquisitionOwnershipProvider(service),
        discovery=OwnershipDiscoveryCoordinator(service),
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
    # SIM LIM's holders come from SIM LIM's own record, namespaced by that issuer.
    by_party = {key.removeprefix(f"{SIM_LIM_UEN}."): value for key, value in by_party.items()}
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
        create_app(
            Settings(
                app_env="test",
                acra_connector_mode="mock",
                goldtier_connector_mode="mock",
                idp_connector_mode="local_pdf_text",
            )
        )
    )
    created = client.post("/api/clm/zero-touch/cases", json={"uen": GARDEN_BUSINESS_UEN})
    assert created.status_code == 201
    created_payload = created.json()
    case_id = created_payload["case"]["case_id"]
    assert created_payload["status"] == "PENDING_INPUTS"
    assert [item["status"] for item in created_payload["target_operations"]] == [
        "NO_MATCH",
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
    ]
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
    review = completed.json()
    assert review["status"] == "WAITING_FOR_REVIEW"
    assert review["active_exceptions"][0]["exception_type"] == ("TARGET_CONFIRMATION_REQUIRED")
    assert [item["status"] for item in review["target_operations"]] == [
        "NO_MATCH",
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
    ]
    preview = review["clm"]["submission_plan"]["request_preview"]
    assert [item["operation"] for item in preview["operations"]] == [
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
    ]
    by_operation = {item["operation"]: item for item in preview["operations"]}
    assert {field["target_field"] for field in by_operation["SHELL"]["fields"]} >= {
        "party.names.legalName",
        "party.nonIndividualProfile.countryOfIncorporation",
        "sourceContext.sourceCaseId",
    }
    assert {field["target_field"] for field in by_operation["POLICY"]["fields"]} >= {
        "goldTierId",
        "customerExternalSystem",
        "customerExternalSystemKey",
        "policyDetails.policy",
    }
    assert {field["target_field"] for field in by_operation["AMEND"]["fields"]} >= {
        "party.names.legalName",
        "party.addresses[0].addressLine1",
        "party.addresses[0].postalCode",
        "party.addresses[0].country",
    }
    confirmed = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": review["version"],
            "expected_clm_version": review["clm"]["version"],
            "expected_case_event_count": len(review["case"]["events"]),
        },
    )
    assert confirmed.status_code == 200
    payload = confirmed.json()
    assert payload["status"] == "COMPLETED"
    assert payload["clm"]["status"] == "MOCK_GOLDTIER_SUBMITTED"
    assert [item["operation"] for item in payload["target_operations"]] == [
        "SEARCH",
        "SHELL",
        "POLICY",
        "AMEND",
        "READBACK",
    ]
    assert [item["status"] for item in payload["target_operations"]] == [
        "NO_MATCH",
        "CREATED",
        "CREATED",
        "SUCCESS",
        "SUCCESS",
    ]
    assert payload["case"]["goldtier_result"]["readback_status"] == "VERIFIED"
    assert (
        payload["case"]["goldtier_result"]["readback_party_id"]
        == payload["case"]["goldtier_result"]["party_id"]
    )
    assert (
        next(item for item in payload["target_operations"] if item["operation"] == "READBACK")[
            "status"
        ]
        == "SUCCESS"
    )
    assert payload["stage_order_version"] == 2
    pipeline = payload["processing_pipeline"]
    assert [item["node_id"] for item in pipeline] == [
        "CASE_START",
        "INITIAL_IDENTITY",
        "JURISDICTION",
        "GOLDTIER_SEARCH",
        "ACRA_REGISTRY",
        "DOCUMENT_IDP",
        "RECONCILIATION",
        "OWNERSHIP_UBO",
        "ADVISORY",
        "READINESS",
        "GOLDTIER_TARGET",
        "FINAL_REVIEW_SEND",
    ]
    assert [item["node_id"] for item in pipeline[4]["children"]] == [
        "ACRA_ENTITY_PROFILE",
        "ACRA_OFFICERS",
        "ACRA_OWNERSHIP_PARTIES",
        "ACRA_RELATIONSHIPS",
    ]
    assert [item["status"] for item in pipeline[3]["children"]] == [
        "SKIPPED",
        "COMPLETE",
        "SKIPPED",
    ]
    assert pipeline[3]["retained_goldtier_id"] is None
    assert [item["status"] for item in pipeline[-1]["children"]] == [
        "COMPLETE",
        "COMPLETE",
        "COMPLETE",
        "COMPLETE",
        "COMPLETE",
    ]
    assert pipeline[-1]["children"][-1]["node_id"] == "GOLDTIER_COMPLETED"
    assert pipeline[-1]["retained_goldtier_id"]
    assert pipeline[-1]["node_id"] == "FINAL_REVIEW_SEND"
    assert pipeline[-1]["status"] == "COMPLETE"
    assert pipeline[-1]["blocker_code"] is None
    assert pipeline[-1]["label"] == "Final review & send"


def test_processing_pipeline_retains_historical_v1_search_without_inventing_confirmation() -> None:
    automation = SimpleNamespace(
        active_exceptions=(),
        completed_at=NOW,
        completed_stages=(
            AutomationStage.REGISTRY,
            AutomationStage.DOCUMENT,
            AutomationStage.OWNERSHIP,
            AutomationStage.READINESS,
            AutomationStage.MOCK_GOLDTIER,
        ),
        created_at=NOW,
        current_stage=AutomationStage.COMPLETE,
        events=(),
        stage_order_version=1,
        status=AutomationStatus.COMPLETED,
    )
    readiness_item = SimpleNamespace(status=SimpleNamespace(value="READY"))
    clm = SimpleNamespace(
        events=(),
        readiness=SimpleNamespace(
            blockers=(),
            document=readiness_item,
            evaluated_at=NOW,
            ownership=readiness_item,
        ),
        submission_plan=SimpleNamespace(environment=SimpleNamespace(value="MOCK")),
        target_search_checkpoint=None,
    )
    pipeline = project_processing_pipeline(
        automation=automation,
        clm=clm,
        case=SimpleNamespace(jurisdiction_resolution=None, registry_acquisition=None),
        reconciliation=None,
        target_operations=(
            BrowserTargetOperationEvidence(operation="SEARCH", status="NO_MATCH"),
            BrowserTargetOperationEvidence(operation="SHELL", status="CREATED"),
            BrowserTargetOperationEvidence(operation="POLICY", status="CREATED"),
            BrowserTargetOperationEvidence(operation="AMEND", status="SUCCESS"),
        ),
        retained_goldtier_id="synthetic-test-id",
    )

    assert [item.node_id for item in pipeline] == [
        "CASE_START",
        "INITIAL_IDENTITY",
        "JURISDICTION",
        "GOLDTIER_SEARCH",
        "ACRA_REGISTRY",
        "DOCUMENT_IDP",
        "RECONCILIATION",
        "OWNERSHIP_UBO",
        "ADVISORY",
        "READINESS",
        "GOLDTIER_TARGET",
        "FINAL_REVIEW_SEND",
    ]
    assert [item.node_id for item in pipeline[-1].children] == [
        "GOLDTIER_SEARCH",
        "GOLDTIER_SHELL",
        "GOLDTIER_POLICY",
        "GOLDTIER_AMEND",
        "GOLDTIER_COMPLETED",
    ]
    assert pipeline[-1].status == "NOT_REACHED"
    assert pipeline[1].status == "NOT_REACHED"


@pytest.mark.parametrize(
    ("automation_status", "expected_status", "expected_result"),
    [
        (AutomationStatus.RUNNING, "IN_PROGRESS", "Search in progress"),
        (
            AutomationStatus.WAITING_FOR_REVIEW,
            "REVIEW_REQUIRED",
            "Search requires review",
        ),
        (AutomationStatus.RECOVERY_PENDING, "BLOCKED", "Search blocked"),
        (AutomationStatus.TECHNICAL_FAILURE, "FAILED", "Search failed"),
    ],
)
def test_processing_pipeline_uses_active_stage_status_before_search_checkpoint(
    automation_status: AutomationStatus,
    expected_status: str,
    expected_result: str,
) -> None:
    automation = SimpleNamespace(
        active_exceptions=(),
        completed_at=None,
        completed_stages=(AutomationStage.REGISTRY,),
        created_at=NOW,
        current_stage=AutomationStage.GOLDTIER_SEARCH,
        events=(),
        stage_order_version=2,
        status=automation_status,
    )
    pending_item = SimpleNamespace(status=SimpleNamespace(value="NOT_SUBMITTED"))
    clm = SimpleNamespace(
        events=(
            SimpleNamespace(
                event_type=SimpleNamespace(value="GOLDTIER_SEARCH_STARTED"),
                timestamp=NOW,
            ),
        ),
        readiness=SimpleNamespace(
            blockers=(),
            document=pending_item,
            evaluated_at=NOW,
            ownership=pending_item,
        ),
        submission_plan=SimpleNamespace(environment=SimpleNamespace(value="SANDBOX")),
        target_search_checkpoint=None,
    )
    pipeline = project_processing_pipeline(
        automation=automation,
        clm=clm,
        case=SimpleNamespace(jurisdiction_resolution=None, registry_acquisition=None),
        reconciliation=None,
        target_operations=(
            BrowserTargetOperationEvidence(operation="SEARCH", status="NOT_ATTEMPTED"),
        ),
        retained_goldtier_id=None,
    )

    search = next(item for item in pipeline if item.node_id == "GOLDTIER_SEARCH")
    assert search.status == expected_status
    assert search.safe_result == expected_result
    assert search.timestamp == NOW
    assert all(item.status == "NOT_REACHED" for item in search.children)


def test_processing_pipeline_projects_exact_existing_customer_branch() -> None:
    automation = SimpleNamespace(
        active_exceptions=(),
        completed_at=NOW,
        completed_stages=(
            AutomationStage.GOLDTIER_SEARCH,
            AutomationStage.DOCUMENT,
            AutomationStage.OWNERSHIP,
            AutomationStage.READINESS,
            AutomationStage.MOCK_GOLDTIER,
        ),
        created_at=NOW,
        current_stage=AutomationStage.COMPLETE,
        events=(),
        stage_order_version=2,
        status=AutomationStatus.COMPLETED,
    )
    ready_item = SimpleNamespace(status=SimpleNamespace(value="READY"))
    checkpoint = SimpleNamespace(
        candidate_count=1,
        code=None,
        disposition=GoldTierSearchDisposition.EXACT_MATCH,
        searched_at=NOW,
    )
    clm = SimpleNamespace(
        events=(),
        readiness=SimpleNamespace(
            blockers=(),
            document=ready_item,
            evaluated_at=NOW,
            ownership=ready_item,
        ),
        submission_plan=SimpleNamespace(environment=SimpleNamespace(value="SANDBOX")),
        target_search_checkpoint=checkpoint,
    )
    case = SimpleNamespace(
        created_at=NOW,
        events=(),
        existing_target_state=SimpleNamespace(target_party_id="143878"),
        initial_identity=SimpleNamespace(),
        initial_target_search=SimpleNamespace(),
        jurisdiction_resolution=None,
        policy_snapshot=None,
        registry_acquisition=None,
    )

    pipeline = project_processing_pipeline(
        automation=automation,
        clm=clm,
        case=case,
        reconciliation=None,
        target_operations=(
            BrowserTargetOperationEvidence(operation="SEARCH", status="MATCH_FOUND"),
            BrowserTargetOperationEvidence(operation="SHELL", status="SKIPPED"),
            BrowserTargetOperationEvidence(operation="POLICY", status="SKIPPED"),
            BrowserTargetOperationEvidence(operation="AMEND", status="SUCCESS"),
            BrowserTargetOperationEvidence(operation="READBACK", status="SUCCESS"),
        ),
        retained_goldtier_id="143878",
    )

    assert [item.node_id for item in pipeline[:5]] == [
        "CASE_START",
        "INITIAL_IDENTITY",
        "JURISDICTION",
        "GOLDTIER_SEARCH",
        "ACRA_REGISTRY",
    ]
    assert pipeline[3].children[-1].node_id == "EXISTING_TARGET_STATE"
    assert pipeline[3].retained_goldtier_id == "143878"
    assert pipeline[4].status == "SKIPPED"
    assert pipeline[3].children[-1].retained_goldtier_id == "143878"
    target = next(item for item in pipeline if item.node_id == "FINAL_REVIEW_SEND")
    assert [(item.node_id, item.status) for item in target.children[:-1]] == [
        ("GOLDTIER_SHELL", "SKIPPED"),
        ("GOLDTIER_POLICY", "SKIPPED"),
        ("GOLDTIER_AMEND", "COMPLETE"),
        ("GOLDTIER_READBACK", "COMPLETE"),
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
