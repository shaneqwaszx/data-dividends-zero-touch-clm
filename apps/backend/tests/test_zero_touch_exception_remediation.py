"""Zero-touch rules exercised through existing owners, without provider transport."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from scripts.garden_protocol_fixture import OfflineGardenProtocolTransport
from test_garden_protocol_fixture import fixture_settings
from test_zero_touch_orchestration import PDF, build_system

from app.composition import build_acra_connector
from app.config import Settings
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.domain.access import TeamId
from app.domain.documents import DocumentCompletionMethod, DocumentFieldKey, ReviewDecision
from app.domain.zero_touch import ExceptionResolutionAction
from app.main import create_app
from app.services.document_errors import DocumentRequestError
from app.services.document_processing import document_semantic_assessment


def test_matching_document_auto_confirms_even_after_readiness_created_reconciliation() -> None:
    _, zero, documents, target, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = zero.intake_document(
        case_id=created.case_id,
        display_name="clean.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    zero._reconciliation.reconcile_current(case_id=created.case_id)  # noqa: SLF001
    result = zero.start(case_id=created.case_id)
    retained = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert retained is not None
    assert retained.completion_method == DocumentCompletionMethod.AUTO_CONFIRMED
    assert all(field.review_status != "PENDING" for field in retained.fields)
    assert result.metrics.human_interventions == 0
    assert all("DOCUMENT" not in item.blocker_code for item in result.active_exceptions)
    assert target.calls == ["search"]


def test_auto_confirmation_does_not_relabel_operator_acceptance() -> None:
    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="clean.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    reviewed = documents.review_field(
        case_id=created.case_id,
        document_id=document.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.ACCEPTED,
        corrected_value=None,
        note="Operator checked the supplied name.",
    )
    confirmed = documents.auto_confirm_document(
        case_id=created.case_id, document_id=document.document_id
    )
    accepted = next(
        field for field in confirmed.fields if field.field_key == DocumentFieldKey.LEGAL_NAME
    )
    original = next(
        field for field in reviewed.fields if field.field_key == DocumentFieldKey.LEGAL_NAME
    )
    assert accepted == original
    assert confirmed.completion_method == DocumentCompletionMethod.HUMAN_REVIEWED


def test_superseded_document_cannot_be_auto_confirmed() -> None:
    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = zero.intake_document(
        case_id=created.case_id,
        display_name="clean.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    documents.replace_document(
        case_id=created.case_id,
        document_id=document.document_id,
        expected_event_count=len(document.events),
        display_name="replacement.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    with pytest.raises(DocumentRequestError):
        documents.auto_confirm_document(case_id=created.case_id, document_id=document.document_id)


def test_contradictory_current_document_prevents_automatic_confirmation() -> None:
    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = zero.intake_document(
        case_id=created.case_id,
        display_name="clean.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    documents.create_document(
        case_id=created.case_id,
        display_name="conflicting.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
    )
    assert not documents.assess_auto_clear(
        case_id=created.case_id, document_id=document.document_id
    ).eligible


@pytest.mark.parametrize("confidence,automatic", [(0.85, True), (0.849999, False)])
def test_frozen_threshold_is_inclusive(confidence: float, automatic: bool) -> None:
    class ExactConfidenceProvider(MockIdpProvider):
        def process(self, document):
            result = super().process(document)
            return result.model_copy(
                update={
                    "fields": [
                        field.model_copy(update={"confidence": confidence})
                        for field in result.fields
                    ]
                }
            )

    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="threshold.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=ExactConfidenceProvider(),
    )
    result = zero.start(case_id=created.case_id)
    retained = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert (retained.completion_method == DocumentCompletionMethod.AUTO_CONFIRMED) == automatic
    assert result.metrics.human_interventions == 0
    assert all(
        field.review_status == ("ACCEPTED" if automatic else "PENDING") for field in retained.fields
    )


@pytest.mark.parametrize(
    "scenario", [MockIdpScenario.LOW_CONFIDENCE, MockIdpScenario.MISSING_FIELD]
)
def test_partial_machine_confirmation_does_not_clear_missing_or_low_confidence(scenario) -> None:
    class RequiredMissingProvider(MockIdpProvider):
        def process(self, document):
            result = MockIdpProvider().process(document)
            return result.model_copy(
                update={
                    "fields": [
                        field.model_copy(update={"value": None, "confidence": 0.0})
                        if field.field_key == DocumentFieldKey.LEGAL_NAME
                        else field
                        for field in result.fields
                    ]
                }
            )

    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="exception.pdf",
        content_type="application/pdf",
        content=PDF,
        provider=(
            RequiredMissingProvider()
            if scenario == MockIdpScenario.MISSING_FIELD
            else MockIdpProvider(scenario)
        ),
    )
    result = zero.start(case_id=created.case_id)
    retained = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert retained.state == "REVIEW_REQUIRED"
    assert sum(field.review_status == "PENDING" for field in retained.fields) == 1
    assert result.current_stage == "DOCUMENT"
    assert result.active_exceptions
    assert result.metrics.human_interventions == 0


def test_changed_canonical_value_and_operator_rejection_do_not_auto_clear() -> None:
    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    document = documents.create_document(
        case_id=created.case_id,
        display_name="current.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    case = zero._cases.get_case(created.case_id)  # noqa: SLF001
    assert not document_semantic_assessment(
        record=document,
        current_entity=case.entity.model_copy(update={"legal_name": "Changed"}),
        confidence_threshold=0.85,
    ).eligible
    documents.review_field(
        case_id=created.case_id,
        document_id=document.document_id,
        field_key=DocumentFieldKey.LEGAL_NAME,
        decision=ReviewDecision.REJECTED,
        corrected_value=None,
        note="Current operator rejection retained.",
    )
    zero.start(case_id=created.case_id)
    retained = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert retained.fields[1].review_status == "REJECTED"
    assert retained.state == "REVIEW_REQUIRED"


def normal_client(garden: bool) -> TestClient:
    if not garden:
        return TestClient(
            create_app(
                Settings(
                    _env_file=None,
                    app_env="test",
                    clm_persistence_mode="memory",
                    acra_connector_mode="mock",
                    goldtier_connector_mode="mock",
                    idp_connector_mode="local_pdf_text",
                    demo_controls_enabled=False,
                )
            )
        )
    settings = fixture_settings().model_copy(
        update={
            "idp_connector_mode": "local_pdf_text",
            "demo_controls_enabled": False,
        }
    )
    transport = OfflineGardenProtocolTransport()
    connector = build_acra_connector(
        settings,
        transport=transport,
        marketplace_token_transport=transport,
    )
    return TestClient(
        create_app(
            settings,
            acra_connector=connector,
            e2e_acra_protocol_fixture=True,
        )
    )


def successful(response, expected=200):
    assert response.status_code == expected, response.json().get("detail", "Unexpected status")
    return response.json()


def normal_started_case(client, *, garden: bool, conflict: bool = False):
    case = successful(
        client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": "11111999A" if garden else "202400001A",
                "country_of_incorporation": "SG",
                "legal_name": "GARDEN BUSINESS" if garden else "MERLION CIRCULAR LABS PTE. LTD.",
            },
        ),
        201,
    )
    case_id = case["case"]["case_id"]
    if not garden:
        successful(
            client.put(
                f"/api/clm/zero-touch/cases/{case_id}/target-classification",
                json={
                    "kyc_customer_type": "Company - Private",
                    "client_segment": "Corporate",
                    "expected_automation_version": case["version"],
                    "expected_case_event_count": len(case["case"]["events"]),
                },
            )
        )
    name = (
        f"garden-business-{'conflicting' if conflict else 'clean'}-onboarding-profile.pdf"
        if garden
        else "clean-company-profile.pdf"
    )
    successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            content=(Path(__file__).parent / "fixtures/uat" / name).read_bytes(),
            headers={"Content-Type": "application/pdf", "X-Document-Name": name},
        ),
        201,
    )
    return successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
    )


def current_document(client, case_id):
    return successful(client.get(f"/api/onboarding/cases/{case_id}/documents"))[0]


def test_normal_golden_api_has_zero_exception_interventions_and_one_confirmation() -> None:
    client = normal_client(False)
    current = normal_started_case(client, garden=False)
    case_id = current["case"]["case_id"]
    assert current["interventions"] == []
    assert current["metrics"]["human_interventions"] == 0
    assert current_document(client, case_id)["completion_method"] == "AUTO_CONFIRMED"
    source = current["case"]["registry_acquisition"]
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert ownership["state"] == "ANALYZED"
    assert ownership["provider_environment"] == "MOCK"
    assert sorted(
        Decimal(item["ownership_percentage"]) for item in source["relationships"]
    ) == sorted(Decimal(item["ownership_percent"]) for item in ownership["relationships"])
    assert "OWNERSHIP_REQUIRED" not in current["clm"]["readiness"]["blockers"]
    assert not any(item["owning_stage"] == "OWNERSHIP" for item in current["interventions"])
    completed = successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json={
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
            },
        )
    )
    assert completed["status"] == "COMPLETED"
    assert completed["metrics"]["human_interventions"] == 0
    assert (
        completed["metrics"]["exceptions_raised"]
        == completed["metrics"]["exceptions_resolved"]
        == 1
    )
    assert (
        sum(event["event_type"] == "TARGET_DISPATCH_CONFIRMED" for event in completed["timeline"])
        == 1
    )


def ownership_request(current, document):
    return {
        "root_registration_number": "11111999A",
        "evidence_document_id": document["document_id"],
        "evidence_document_version": len(document["events"]),
        "as_of_date": datetime.now(UTC).date().isoformat(),
        "rationale": "Reviewed synthetic client economic interest declaration.",
        "root_party_id": "ROOT",
        "parties": [
            {
                "party_id": "ROOT",
                "display_name": "GARDEN BUSINESS",
                "party_type": "LEGAL_ENTITY",
                "registration_number": "11111999A",
                "country": "SG",
            },
            {
                "party_id": "A",
                "display_name": "Demo Partner A",
                "party_type": "NATURAL_PERSON",
                "country": "SG",
            },
            {
                "party_id": "B",
                "display_name": "Demo Partner B",
                "party_type": "NATURAL_PERSON",
                "country": "SG",
            },
        ],
        "relationships": [
            {
                "relationship_id": "RA",
                "parent_party_id": "ROOT",
                "child_party_id": "A",
                "ownership_percent": "60",
            },
            {
                "relationship_id": "RB",
                "parent_party_id": "ROOT",
                "child_party_id": "B",
                "ownership_percent": "40",
            },
        ],
        "expected_automation_version": current["version"],
        "expected_ownership_version": current["ownership_recovery"]["version"],
        "expected_case_event_count": len(current["case"]["events"]),
    }


@pytest.mark.parametrize("conflict", [False, True])
def test_normal_garden_actions_clear_exact_issues_and_resume_ubo(conflict: bool) -> None:
    client = normal_client(True)
    current = normal_started_case(client, garden=True, conflict=conflict)
    case_id = current["case"]["case_id"]
    if conflict:
        # Resolve exact backend-authorized discrepancies. No generic continue or document accepts.
        while current["current_stage"] == "DOCUMENT":
            blocker = current["active_exceptions"][0]
            before = len(current["active_exceptions"])
            current = successful(
                client.post(
                    f"/api/clm/zero-touch/cases/{case_id}/exceptions/{blocker['exception_id']}/resolve",
                    json={
                        "action": "KEEP_REGISTRY_VALUE",
                        "expected_automation_version": current["version"],
                        "evidence_version": blocker["evidence_version"],
                    },
                )
            )
            assert all(
                item["exception_id"] != blocker["exception_id"]
                for item in current["active_exceptions"]
            )
            assert any(
                item["exception_id"] == blocker["exception_id"] and item["status"] == "RESOLVED"
                for item in current["historical_exceptions"]
            )
            assert len(current["active_exceptions"]) <= before
            history = next(
                item
                for item in current["historical_exceptions"]
                if item["exception_id"] == blocker["exception_id"]
            )
            assert history["decisions"][-1]["actor_id"] == "maya-lim"
    else:
        assert current_document(client, case_id)["completion_method"] == "AUTO_CONFIRMED"
        assert current["metrics"]["human_interventions"] == 0
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert ownership["state"] == "ANALYZED"
    assert ownership["manual_review_receipt"] is None
    assert ownership["source_classification"] == "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
    assert {edge["provenance"]["provider"] for edge in ownership["relationships"]} == {
        "LOCAL_SYNTHETIC_SUPPLEMENT"
    }
    percentages = {item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
                   for item in ownership["candidates"]}
    assert percentages["ABCD123"] == Decimal("51.13636375")
    assert percentages["LIM CHOON HUAT"] == Decimal("37.500000")
    assert all(item["owning_stage"] != "OWNERSHIP" for item in current["interventions"])
    assert current["case"]["registry_acquisition"]["ownership_parties"] == []


def test_automatic_garden_does_not_require_unrelated_supplementary_upload() -> None:
    client = normal_client(True)
    current = normal_started_case(client, garden=True)
    case_id = current["case"]["case_id"]
    document_path = f"/api/onboarding/cases/{case_id}/documents"
    before = successful(client.get(document_path))
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        content=b"not a PDF",
        headers={"Content-Type": "application/pdf", "X-Document-Name": "invalid.pdf"},
    )
    assert response.status_code in {409, 422}
    assert successful(client.get(document_path)) == before
    assert current["case"]["registry_acquisition"]["ownership_parties"] == []
    assert current["metrics"]["human_interventions"] == 0


@pytest.mark.parametrize(
    "stale", ["wrong_document", "wrong_case", "event_version", "canonical", "replacement"]
)
def test_resolved_document_checkpoint_requires_exact_current_binding(stale, monkeypatch) -> None:
    from uuid import uuid4

    _, zero, documents, _, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A)
    paused = zero.attach_document(
        case_id=created.case_id,
        display_name="binding.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=MockIdpProvider(MockIdpScenario.FIELD_MISMATCH),
    )
    document = documents.list_documents(case_id=created.case_id)[0]
    owner = zero._reconciliation  # noqa: SLF001
    assert (
        owner.resolved_document_checkpoint(
            case_id=created.case_id,
            document_id=document.document_id,
            event_count=len(document.events),
        )
        is None
    )
    blocker = paused.active_exceptions[0]
    zero.resolve_exception(
        case_id=created.case_id,
        exception_id=blocker.exception_id,
        action=ExceptionResolutionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=paused.version,
        evidence_version=blocker.evidence_version,
    )
    retained = documents.get_document(case_id=created.case_id, document_id=document.document_id)
    assert (
        retained == document
    )  # Semantic completion never rewrites source review or its fingerprint.
    assert (
        owner.resolved_document_checkpoint(
            case_id=created.case_id,
            document_id=document.document_id,
            event_count=len(document.events),
        )
        is not None
    )
    case_id, document_id, count = created.case_id, document.document_id, len(document.events)
    if stale == "wrong_document":
        document_id = uuid4()
    elif stale == "wrong_case":
        case_id = uuid4()
    elif stale == "event_version":
        count += 1
    elif stale == "replacement":
        documents.replace_document(
            case_id=case_id,
            document_id=document_id,
            expected_event_count=count,
            display_name="new-binding.pdf",
            content_type="application/pdf",
            content=PDF,
        )
    else:
        cases = zero._cases  # noqa: SLF001
        case = cases.get_case(case_id)
        altered = case.model_copy(
            update={"entity": case.entity.model_copy(update={"legal_name": "CHANGED"})}
        )
        monkeypatch.setattr(
            cases, "get_case", lambda requested: altered if requested == case_id else None
        )
    assert (
        owner.resolved_document_checkpoint(
            case_id=case_id, document_id=document_id, event_count=count
        )
        is None
    )
