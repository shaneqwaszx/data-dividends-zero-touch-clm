"""Registry correction adverse paths using entirely synthetic providers."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from scripts.generate_phase08_synthetic_pdfs import text_pdf
from test_zero_touch_orchestration import PDF, build_system, start_demo

from app.config import Settings
from app.connectors.idp import IdpDocumentInput, IdpSourceResult
from app.connectors.mock_idp import MockIdpProvider, MockIdpScenario
from app.connectors.mock_ownership import MockOwnershipProvider
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.access import TeamId
from app.domain.documents import DocumentFieldKey
from app.main import create_app


def correction(client, zero, record, *, uen="202400009I", choice="OTHER", **extra):
    case = zero._cases.get_case(record.case_id)
    clm = zero._clm.get(case_id=record.case_id)
    return client.post(
        f"/api/clm/zero-touch/cases/{record.case_id}/registry-identity",
        json={
            "legal_name": "Synthetic corrected company",
            "registration_number": uen,
            "country_of_incorporation": "SG",
            "choice": choice,
            "expected_automation_version": record.version,
            "expected_clm_version": clm.version,
            "expected_case_event_count": len(case.events),
            **extra,
        },
    )


def test_not_found_correction_preserves_authoritative_identity_and_makes_no_search():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    before = zero._cases.get_case(record.case_id)
    calls = list(target.calls)
    response = correction(client, zero, record, uen="99999999Z")
    assert response.status_code == 409
    assert (
        response.json()["detail"]["message"] == "Registry verification could not verify this UEN."
    )
    assert zero._cases.get_case(record.case_id) == before
    assert target.calls == calls


def test_verified_correction_reuses_case_and_preserves_old_registry_history():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    before = zero._cases.get_case(record.case_id)
    response = correction(client, zero, record)
    assert response.status_code == 200
    body = response.json()
    assert body["case"]["case_id"] == str(record.case_id)
    assert body["case"]["entity"]["registration_number"] == "202400009I"
    current = zero._cases.get_case(record.case_id)
    assert (
        current.identity_corrections[-1].previous_registry_acquisition
        == before.registry_acquisition
    )
    assert current.registry_acquisition.requested_identifier == "202400009I"
    assert target.calls == ["search", "search"]


def test_identity_rebind_never_reuses_old_ownership_and_retains_analysis_history():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    old = zero._ownership.load(case_id=record.case_id)
    old = zero._ownership.analyze(case_id=record.case_id)
    assert old.candidates[0].aggregated_ownership_percent > Decimal("0")
    response = correction(client, zero, record)
    assert response.status_code == 200
    assert zero._ownership.get(case_id=record.case_id) is None
    replacement = zero._ownership.load(case_id=record.case_id)
    assert replacement.analysis_id != old.analysis_id
    assert replacement.identity_registration_number == "202400009I"
    assert replacement.prior_analyses[-1].analysis_id == old.analysis_id
    assert replacement.version > old.version


def test_document_choice_requires_current_evidence():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    response = correction(client, zero, record, choice="DOCUMENT")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "IDENTITY_DOCUMENT_CHOICE_STALE"


def test_entered_choice_cannot_substitute_another_uen():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    response = correction(client, zero, record, choice="ENTERED")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "IDENTITY_CHOICE_INVALID"


class ConflictingIdentityDocument(MockIdpProvider):
    def process(self, document: IdpDocumentInput) -> object:
        result = IdpSourceResult.model_validate(super().process(document))
        return result.model_copy(
            update={
                "fields": [
                    field.model_copy(update={"value": "202400009I"})
                    if field.field_key == DocumentFieldKey.REGISTRATION_NUMBER
                    else field
                    for field in result.fields
                ]
            }
        )


def attach_conflict(zero, record, *, low_confidence=False):
    provider = ConflictingIdentityDocument(
        MockIdpScenario.LOW_CONFIDENCE if low_confidence else MockIdpScenario.ALL_FIELDS_MATCH
    )
    return zero.attach_document(
        case_id=record.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
        idp_provider=provider,
        ownership_provider=MockOwnershipProvider(),
    )


def test_entered_choice_without_documents_is_safe_same_case_recovery():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    response = correction(client, zero, record, choice="ENTERED", uen="202400001A")
    assert response.status_code == 200
    assert response.json()["case"]["requested_uen"] == "202400001A"
    assert target.calls == ["search", "search"]


def test_entered_choice_resolves_only_identity_and_preserves_unrelated_document_blocker():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    record = attach_conflict(zero, record, low_confidence=True)
    response = correction(client, zero, record, choice="ENTERED", uen="202400001A")
    assert response.status_code == 200
    current = zero._reconciliation.get(case_id=record.case_id)
    identity = [
        item
        for item in current.discrepancies
        if item.field_name == "registration_identifier" and item.status == "RESOLVED"
    ]
    assert identity[-1].decision.action == "KEEP_REGISTRY_VALUE"
    assert any(item["stage"] == "DOCUMENT" for item in response.json()["active_exceptions"])
    assert all(item.field_name != "registration_identifier" for item in current.open_discrepancies)
    assert target.calls == ["search", "search"]


def test_document_choice_reverifies_and_retains_selected_document_version():
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    record = attach_conflict(zero, record)
    document = documents.list_documents(case_id=record.case_id)[0]
    response = correction(
        client,
        zero,
        record,
        choice="DOCUMENT",
        document_id=str(document.document_id),
        expected_document_event_count=len(document.events),
    )
    assert response.status_code == 200
    current = zero._cases.get_case(record.case_id)
    assert current.requested_uen == "202400009I"
    assert current.identity_corrections[-1].source_document_id == document.document_id
    assert current.identity_corrections[-1].source_document_event_count == len(document.events)
    reconciliation = zero._reconciliation.get(case_id=record.case_id)
    assert not any(
        item.field_name == "registration_identifier" for item in reconciliation.open_discrepancies
    )
    assert target.calls == ["search", "search"]


def test_stale_document_choice_has_no_canonical_or_search_effect():
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    record = attach_conflict(zero, record)
    document = documents.list_documents(case_id=record.case_id)[0]
    before = zero._cases.get_case(record.case_id)
    response = correction(
        client,
        zero,
        record,
        choice="DOCUMENT",
        document_id=str(document.document_id),
        expected_document_event_count=len(document.events) - 1,
    )
    assert response.status_code == 409
    assert zero._cases.get_case(record.case_id) == before
    assert target.calls == ["search"]


def test_initial_registry_failure_can_correct_without_a_new_case():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("99999999Z", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    response = correction(client, zero, record, uen="202400001A")
    assert response.status_code == 200
    assert response.json()["case"]["case_id"] == str(record.case_id)
    assert response.json()["case"]["entity"]["registration_number"] == "202400001A"
    assert target.calls == ["search", "search"]


def test_completed_identity_is_frozen_and_no_provider_call_occurs():
    client, zero, _, target, _ = build_system()
    completed = start_demo(client, "STRAIGHT_THROUGH")
    from uuid import UUID

    record = zero.get(case_id=UUID(completed["case"]["case_id"]))
    before = zero._cases.get_case(record.case_id)
    calls = list(target.calls)
    response = correction(client, zero, record)
    assert response.status_code == 409
    assert zero._cases.get_case(record.case_id) == before
    assert target.calls == calls


def test_composed_registry_ownership_rebind_resumes_with_retained_history():
    client = TestClient(
        create_app(
            Settings(
                _env_file=None,
                app_env="test",
                idp_connector_mode="local_pdf_text",
            )
        )
    )
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": "202400001A",
            "legal_name": "Synthetic",
            "country_of_incorporation": "SG",
        },
    ).json()
    case_id = created["case"]["case_id"]
    assert client.post(f"/api/onboarding/cases/{case_id}/ownership/load").status_code == 201
    assert client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze").status_code == 200
    old = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    content = text_pdf(
        {
            "UEN": "202400009I",
            "Legal Name": "MULTI LEVEL OWNERSHIP DEMO PTE. LTD.",
            "Registered Address": "18 HIERARCHY WALK, #04-01, 049004, SG",
            "Country": "SG",
        }
    )
    paused = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        content=content,
        headers={"Content-Type": "application/pdf", "X-Document-Name": "synthetic-phase24.pdf"},
    ).json()
    document = client.get(f"/api/onboarding/cases/{case_id}/documents").json()[0]
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/registry-identity",
        json={
            "legal_name": "Synthetic",
            "registration_number": "202400009I",
            "country_of_incorporation": "SG",
            "choice": "DOCUMENT",
            "document_id": document["document_id"],
            "expected_document_event_count": len(document["events"]),
            "expected_automation_version": paused["version"],
            "expected_clm_version": paused["clm"]["version"],
            "expected_case_event_count": len(paused["case"]["events"]),
        },
    )
    assert response.status_code == 200
    current = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
    assert current["analysis_id"] != old["analysis_id"]
    assert (
        response.json()["case"]["identity_corrections"][-1]["previous_identity"][
            "registration_number"
        ]
        == "202400001A"
    )
    assert (
        next(item for item in current["parties"] if item["party_id"] == current["root_party_id"])[
            "registration_number"
        ]
        == "202400009I"
    )


def test_same_uen_verification_invalidates_registry_derived_analysis_and_retains_history():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    provider = RegistryAcquisitionOwnershipProvider(zero._cases)
    zero._ownership.load(case_id=record.case_id, provider=provider)
    old = zero._ownership.analyze(case_id=record.case_id)
    assert correction(client, zero, record, choice="ENTERED", uen="202400001A").status_code == 200
    assert zero._ownership.get(case_id=record.case_id) is None
    current = zero._ownership.load(case_id=record.case_id, provider=provider)
    assert current.identity_correction_version == 1
    assert current.prior_analyses[-1].analysis_id == old.analysis_id
    assert current.prior_analyses[-1].identity_correction_version == 0


def test_same_uen_verification_retains_independent_non_registry_evidence():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    zero._ownership.load(case_id=record.case_id)
    old = zero._ownership.analyze(case_id=record.case_id)
    assert correction(client, zero, record, choice="ENTERED", uen="202400001A").status_code == 200
    assert zero._ownership.get(case_id=record.case_id) == old


def test_same_uen_verification_allows_independent_loaded_analysis_to_continue():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    loaded = zero._ownership.load(case_id=record.case_id)
    assert loaded.state == "LOADED" and loaded.identity_correction_version == 0
    assert correction(client, zero, record, choice="ENTERED", uen="202400001A").status_code == 200
    analyzed = zero._ownership.analyze(case_id=record.case_id)
    assert analyzed.state == "ANALYZED"
    assert analyzed.analysis_id == loaded.analysis_id
    assert analyzed.identity_correction_version == 0


def test_identity_roundtrip_keeps_superseded_independent_analysis_historical():
    client, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    zero._ownership.load(case_id=record.case_id)
    old = zero._ownership.analyze(case_id=record.case_id)
    assert correction(client, zero, record, uen="202400009I").status_code == 200
    assert zero._ownership.get(case_id=record.case_id) is None
    current = zero.get(case_id=record.case_id)
    assert correction(client, zero, current, uen="202400001A").status_code == 200
    assert zero._ownership.get(case_id=record.case_id) is None
    replacement = zero._ownership.load(case_id=record.case_id)
    assert replacement.analysis_id != old.analysis_id
    assert replacement.identity_correction_version == 2
    assert replacement.prior_analyses[-1].analysis_id == old.analysis_id
    assert replacement.prior_analyses[-1].candidates == tuple(old.candidates)


def test_identity_history_limit_rejects_before_registry_search_or_mutation(monkeypatch):
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    for _ in range(16):
        response = correction(client, zero, record, choice="ENTERED", uen="202400001A")
        assert response.status_code == 200
        record = zero.get(case_id=record.case_id)
    before = zero._cases.get_case(record.case_id)
    calls = list(target.calls)

    def forbidden_registry(*args, **kwargs):
        pytest.fail("history exhaustion must precede registry dispatch")

    monkeypatch.setattr(zero._cases, "_verify_registry_correction", forbidden_registry)
    response = correction(client, zero, record, choice="ENTERED", uen="202400001A")
    assert response.status_code == 409
    assert "history is full" in response.json()["detail"]["message"]
    assert zero._cases.get_case(record.case_id) == before
    assert zero.get(case_id=record.case_id) == record
    assert target.calls == calls
    from app.domain.models import OnboardingCase

    assert OnboardingCase.model_validate(before.model_dump()) == before
