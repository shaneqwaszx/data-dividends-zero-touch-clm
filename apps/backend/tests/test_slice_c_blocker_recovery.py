"""Owner regressions for Slice C; synthetic evidence, no external provider calls."""

import pytest
import test_zero_touch_orchestration as orchestration_tests
from test_phase11_reconciliation import FieldOverrideIdp, attach, current_discrepancy
from test_phase24b_interrupted_retry import snapshot_of

from app.config import Settings
from app.domain.documents import DocumentFieldKey
from app.domain.reconciliation import ReconciliationDecisionAction, ReconciliationField
from app.domain.zero_touch import BusinessException
from app.persistence.mongo_case_store import MongoCaseStore, _persistence_value


def system(monkeypatch, **kwargs):
    monkeypatch.setattr(
        orchestration_tests, "Settings", lambda **values: Settings(_env_file=None, **values)
    )
    return orchestration_tests.build_system(require_confirmation=True, **kwargs)


def test_partial_reconciliation_retains_valid_current_decision_bindings(monkeypatch):
    _, zero, _, target, _ = system(monkeypatch)
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp(
            {
                DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD.",
                DocumentFieldKey.REGISTERED_ADDRESS: "99 OTHER ROAD, 999999, SG",
            }
        ),
    )
    assert len(paused.active_exceptions) == 2
    for exception in paused.active_exceptions:
        BusinessException.model_validate(_persistence_value(exception))
    before = zero._reconciliation.get(case_id=created.case_id)
    first = current_discrepancy(before, ReconciliationField.LEGAL_NAME)
    remaining_before = next(
        item for item in paused.active_exceptions if item.exception_id != first.discrepancy_id
    )
    pending = zero.resolve_reconciliation_discrepancy(
        case_id=created.case_id,
        discrepancy_id=first.discrepancy_id,
        action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
        expected_automation_version=paused.version,
        expected_reconciliation_version=before.version,
        evidence_fingerprint=first.evidence_fingerprint,
    )
    assert pending.status == "WAITING_FOR_REVIEW"
    assert target.calls == ["search"]
    remaining = pending.active_exceptions[0]
    BusinessException.model_validate(_persistence_value(remaining))
    assert remaining.evidence_version != remaining_before.evidence_version
    assert [item.decision_id for item in remaining.decisions] == [
        item.decision_id for item in remaining_before.decisions
    ]
    assert all(item.evidence_version == remaining.evidence_version for item in remaining.decisions)
    assert [item.metadata for item in remaining.decisions] == [
        item.metadata for item in remaining_before.decisions
    ]
    assert [item.recorded_at for item in remaining.decisions] == [
        item.recorded_at for item in remaining_before.decisions
    ]
    resolved = next(
        item for item in pending.exceptions if item.exception_id == first.discrepancy_id
    )
    assert resolved.status == "RESOLVED"
    assert resolved.resolution == "USE_DOCUMENT_VALUE"
    codec = object.__new__(MongoCaseStore)
    snapshot = snapshot_of(zero, created.case_id)
    assert codec._decode(codec._encode(snapshot)) == snapshot
    record = zero._reconciliation.get(case_id=created.case_id)
    last = record.open_discrepancies[0]
    resumed = zero.resolve_reconciliation_discrepancy(
        case_id=created.case_id,
        discrepancy_id=last.discrepancy_id,
        action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=pending.version,
        expected_reconciliation_version=record.version,
        evidence_fingerprint=last.evidence_fingerprint,
    )
    assert not any(item.stage == "DOCUMENT" for item in resumed.active_exceptions)
    assert (
        next(item for item in resumed.exceptions if item.exception_id == first.discrepancy_id)
        == resolved
    )
    calls = list(target.calls)
    assert zero.start(case_id=created.case_id).version == resumed.version
    assert target.calls == calls


def test_definitive_missing_registry_entity_is_business_identity_review(monkeypatch):
    _, zero, _, target, _ = system(monkeypatch)
    record = zero.create_case(
        "99999999Z", legal_name="SYNTHETIC UNKNOWN", country_of_incorporation="SG"
    )
    assert record.status == "WAITING_FOR_REVIEW"
    assert record.technical_failure is None
    assert [item.blocker_code for item in record.active_exceptions] == ["ACRA_ENTITY_NOT_FOUND"]
    assert target.calls == ["search"]


def test_missing_registry_identity_has_current_correction_navigation(monkeypatch):
    from app.api_models import project_human_interventions

    _, zero, _, _, _ = system(monkeypatch)
    record = zero.create_case(
        "99999999Z", legal_name="SYNTHETIC UNKNOWN", country_of_incorporation="SG"
    )
    interventions = project_human_interventions(
        automation=record,
        clm=zero._clm.get(case_id=record.case_id),
        case=zero._cases.get_case(record.case_id),
    )
    current = next(item for item in interventions if item.blocker_code == "ACRA_ENTITY_NOT_FOUND")
    assert current.identity_correction_action == "IDENTITY_SEARCH_RECHECK"
    assert [item.target for item in current.evidence_actions] == ["IDENTITY"]
    assert current.no_action_reason is None


def test_optional_amend_projects_retained_not_required_as_skipped():
    from pathlib import Path

    from fastapi.testclient import TestClient
    from scripts.slice_c_recovery_fixture import build_offline_recovery_fixture

    from app.main import create_app

    fixture = build_offline_recovery_fixture(
        Settings(_env_file=None, app_env="test", idp_connector_mode="local_pdf_text"),
        "optional-amend",
    )
    client = TestClient(
        create_app(
            settings=fixture.settings,
            onboarding_service=fixture.onboarding,
        )
    )
    response = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": "202400001A",
            "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
            "country_of_incorporation": "SG",
        },
    )
    assert response.status_code == 201
    record = response.json()
    case_id = record["case"]["case_id"]
    assert (
        client.put(
            f"/api/clm/zero-touch/cases/{case_id}/target-classification",
            json={
                "kyc_customer_type": "Company - Private",
                "client_segment": "Corporate",
                "expected_automation_version": record["version"],
                "expected_case_event_count": len(record["case"]["events"]),
            },
        ).status_code
        == 200
    )
    ready = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        content=(Path(__file__).parent / "fixtures/uat/clean-company-profile.pdf").read_bytes(),
        headers={"Content-Type": "application/pdf", "X-Document-Name": "synthetic.pdf"},
    )
    assert ready.status_code == 200
    record = ready.json()
    done = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_automation_version": record["version"],
            "expected_clm_version": record["clm"]["version"],
            "expected_case_event_count": len(record["case"]["events"]),
        },
    )
    assert done.status_code == 200
    summary = done.json()
    assert summary["status"] == "COMPLETED"
    assert summary["case"]["goldtier_result"]["amend_status"] == "AMEND_NOT_REQUIRED"
    amend = next(item for item in summary["target_operations"] if item["operation"] == "AMEND")
    assert amend["status"] == "SKIPPED"
    target = next(
        item for item in summary["processing_pipeline"] if item["node_id"] == "GOLDTIER_TARGET"
    )
    assert (
        next(item for item in target["children"] if item["node_id"] == "GOLDTIER_AMEND")["status"]
        == "SKIPPED"
    )
    assert "AMEND" not in fixture.metadata()["operations"]
    assert fixture.metadata()["external_calls"] == 0


def test_intervention_uses_metadata_for_its_own_blocker_not_aggregated_sibling(monkeypatch):
    from app.api_models import project_human_interventions

    _, zero, _, _, _ = system(monkeypatch)
    created = zero.create_case("202400001A")
    paused = attach(
        zero,
        created.case_id,
        FieldOverrideIdp(
            {
                DocumentFieldKey.LEGAL_NAME: "OTHER NAME",
                DocumentFieldKey.COUNTRY_OF_INCORPORATION: None,
            }
        ),
    )
    exception = next(
        item
        for item in paused.active_exceptions
        if item.blocker_code == "DOCUMENT_REQUIRED_FIELD_MISSING"
    )
    metadata = next(
        item.metadata
        for item in exception.decisions
        if item.metadata.blocker_code == exception.blocker_code
    )
    current = next(
        item
        for item in project_human_interventions(
            automation=paused,
            clm=zero._clm.get(case_id=created.case_id),
            case=zero._cases.get_case(created.case_id),
        )
        if item.blocker_code == exception.blocker_code
    )
    assert current.blocker_class == "RECOVERABLE_INPUT"
    assert current.backend_mutation_owner == metadata.owner.value
    assert current.resume_target == metadata.resume_stage
    assert current.dependent_stages == tuple(
        item.value for item in metadata.invalidated_dependencies
    )


@pytest.mark.parametrize("legacy_aggregate", [False, True])
def test_resolved_mixed_sibling_is_absent_from_current_decisions_with_history_retained(
    monkeypatch,
    legacy_aggregate,
):
    from app.api_models import project_human_interventions

    _, zero, _, target, _ = system(monkeypatch)
    case_id = zero.create_case("202400001A").case_id
    add_exception = zero._add_exception
    if legacy_aggregate:

        def add_legacy_exception(record, **kwargs):
            if kwargs["stage"] == "DOCUMENT":
                kwargs["blocker_codes"] = (
                    "DOCUMENT_SOURCE_CONFLICT",
                    "DOCUMENT_REQUIRED_FIELD_MISSING",
                )
            return add_exception(record, **kwargs)

        monkeypatch.setattr(zero, "_add_exception", add_legacy_exception)
    paused = attach(
        zero,
        case_id,
        FieldOverrideIdp(
            {
                DocumentFieldKey.LEGAL_NAME: "OTHER NAME",
                DocumentFieldKey.COUNTRY_OF_INCORPORATION: None,
            }
        ),
    )
    monkeypatch.setattr(zero, "_add_exception", add_exception)
    current = zero._reconciliation.get(case_id=case_id)
    conflict = current_discrepancy(current, ReconciliationField.LEGAL_NAME)
    pending = zero.resolve_reconciliation_discrepancy(
        case_id=case_id,
        discrepancy_id=conflict.discrepancy_id,
        action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
        expected_automation_version=paused.version,
        expected_reconciliation_version=current.version,
        evidence_fingerprint=conflict.evidence_fingerprint,
    )
    active = pending.active_exceptions[0]
    assert active.blocker_code == "DOCUMENT_REQUIRED_FIELD_MISSING"
    assert active.blocker_codes == ("DOCUMENT_REQUIRED_FIELD_MISSING",)
    assert [item.metadata.blocker_code for item in active.decisions] == [
        "DOCUMENT_REQUIRED_FIELD_MISSING"
    ]
    resolved = next(
        item for item in pending.exceptions if item.exception_id == conflict.discrepancy_id
    )
    assert resolved.status == "RESOLVED" and resolved.resolution == "KEEP_REGISTRY_VALUE"
    assert resolved.decisions
    current_intervention = next(
        item
        for item in project_human_interventions(
            automation=pending,
            clm=zero._clm.get(case_id=case_id),
            case=zero._cases.get_case(case_id),
        )
        if item.blocker_code == "DOCUMENT_REQUIRED_FIELD_MISSING"
    )
    assert [item.metadata.blocker_code for item in current_intervention.decisions] == [
        "DOCUMENT_REQUIRED_FIELD_MISSING"
    ]
    codec = object.__new__(MongoCaseStore)
    snapshot = snapshot_of(zero, case_id)
    assert codec._decode(codec._encode(snapshot)) == snapshot
    assert zero.start(case_id=case_id).version == pending.version
    assert (
        next(
            item
            for item in zero.get(case_id=case_id).exceptions
            if item.exception_id == conflict.discrepancy_id
        )
        == resolved
    )
    assert target.calls == ["search"]
    document = zero._documents.list_documents(case_id=case_id)[0]
    replaced = zero.replace_document(
        case_id=case_id,
        document_id=document.document_id,
        expected_document_event_count=len(document.events),
        display_name="Synthetic-clean.pdf",
        content_type="application/pdf",
        content=orchestration_tests.PDF,
    )
    assert not any(item.stage == "DOCUMENT" for item in replaced.active_exceptions)
    assert (
        next(item for item in replaced.exceptions if item.exception_id == conflict.discrepancy_id)
        == resolved
    )


@pytest.mark.parametrize("target_kind", ["ambiguous", "failed"])
def test_registry_timeout_and_search_outcome_retains_typed_api_technical_failure(
    monkeypatch,
    target_kind,
):
    from uuid import UUID

    from fastapi.testclient import TestClient

    from app.connectors.errors import AcraTimeoutError
    from app.connectors.mock_acra import MockAcraConnector

    class TimeoutOfficers(MockAcraConnector):
        def fetch_officers(self, uen):
            raise AcraTimeoutError("SYNTHETIC_PRIVATE_DIAGNOSTIC")

    monkeypatch.setattr(orchestration_tests, "MockAcraConnector", TimeoutOfficers)
    target = (
        orchestration_tests.AmbiguousRecordingMockGoldTier()
        if target_kind == "ambiguous"
        else orchestration_tests.FailedSearchRecordingMockGoldTier()
    )
    original, zero, _, _, _ = system(monkeypatch, connector=target)
    with TestClient(original.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": "202400001A",
                "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
                "country_of_incorporation": "SG",
            },
        )
        assert response.status_code == 201
        assert "application/json" in response.headers["content-type"]
        assert "SYNTHETIC_PRIVATE_DIAGNOSTIC" not in response.text
        record = response.json()
        assert record["status"] == "TECHNICAL_FAILURE"
        assert record["current_stage"] == "REGISTRY"
        assert record["technical_failure"]["code"] == "REGISTRY_OPERATION_TIMEOUT"
        assert record["active_exceptions"] == []
        assert record["timeline"][-1]["event_type"] == "AUTOMATION_TECHNICAL_FAILURE"
        assert record["timeline"][-1]["status"] == "TECHNICAL_FAILURE"
        if target_kind == "ambiguous":
            assert any(
                item["exception_type"] == "ENTITY_RESOLUTION_REVIEW_REQUIRED"
                and item["status"] == "CANCELLED"
                for item in record["historical_exceptions"]
            )
        case_id = record["case"]["case_id"]
        persisted = client.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert persisted.status_code == 200
        assert persisted.json()["status"] == "TECHNICAL_FAILURE"
        assert zero.get(case_id=UUID(case_id)) is not None
        assert target.calls == ["search"]
