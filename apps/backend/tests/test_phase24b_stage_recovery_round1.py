"""Stage-recovery F1/F2 failing-first coverage using owned synthetic seams."""

import pytest
from test_phase24_identity import correction
from test_phase24b_generation_currentness import rebuilt_registry_generations
from test_phase24b_interrupted_retry import restore_memory_snapshot, snapshot_of
from test_zero_touch_orchestration import build_system

from app.domain.access import TeamId
from app.domain.zero_touch import AutomationStage, BusinessExceptionType
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import _persistence_value
from app.services.clm_errors import ClmRequestError


def unfinished_mixed_case(monkeypatch, *, loaded, available=False):
    client, zero, target, registry, stale, case_id = rebuilt_registry_generations(monkeypatch)
    with zero._cases.case_lock(case_id):
        zero._add_exception(
            zero.get(case_id=case_id),
            exception_type=BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
            stage=AutomationStage.READINESS, blocker_code="TARGET_CONFIRMATION_REQUIRED",
            explanation="Independent synthetic confirmation safety.",
            evidence_version="target-confirmation:independent:1", evidence=(), actions=(),
        )
    registry.available = available
    with monkeypatch.context() as patch:
        def fail(**kwargs):
            raise ClmRequestError(
                code="CLM_IDENTITY_RECHECK_STALE", message="Synthetic interruption.",
            )
        patch.setattr(zero._clm, "refresh_initial_search_after_recheck", fail)
        assert correction(client, zero, zero.get(case_id=case_id),
                          choice="ENTERED", uen="202400001A").status_code == 409
    if loaded:
        assert client.post(f"/api/onboarding/cases/{case_id}/ownership/load").status_code == 201
        assert zero._ownership.get(case_id=case_id).state == "LOADED"
    else:
        assert zero._ownership.get(case_id=case_id) is None
    snapshot = DurableCaseSnapshot.model_validate(_persistence_value(snapshot_of(zero, case_id)))
    return client, zero, target, stale, case_id, snapshot


@pytest.mark.parametrize("loaded", [False, True])
@pytest.mark.parametrize("reload", [False, True])
@pytest.mark.parametrize("available", [False, True])
def test_unfinished_current_ownership_precedes_independent_readiness(
    monkeypatch, loaded, reload, available,
):
    client, zero, target, stale, case_id, snapshot = unfinished_mixed_case(
        monkeypatch, loaded=loaded, available=available,
    )
    retained = next(item for item in snapshot.automation.active_exceptions
                    if item.blocker_code == "TARGET_CONFIRMATION_REQUIRED")
    if reload:
        client, zero, target = restore_memory_snapshot(snapshot)
    calls = list(target.calls)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    ownership = zero._ownership.get(case_id=case_id)
    assert ownership.state == ("ANALYZED" if available else "REVIEW_REQUIRED")
    assert ownership.identity_correction_version == 6
    assert current.current_stage == (AutomationStage.READINESS if available
                                     else AutomationStage.OWNERSHIP)
    assert AutomationStage.DOCUMENT in current.completed_stages
    assert next(item for item in current.exceptions
                if item.exception_id == stale.exception_id).status == "CANCELLED"
    assert next(item for item in current.active_exceptions
                if item.exception_id == retained.exception_id) == retained
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero.get(case_id=case_id) == current
    assert zero._ownership.get(case_id=case_id) == ownership
    assert target.calls == calls


def correction_blockers(*, reverse=False):
    client, zero, _, target, _ = build_system(require_confirmation=True)
    record = zero.create_case(
        "202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A,
        created_by_actor_id="maya-lim",
    )
    stages = [AutomationStage.READINESS, AutomationStage.OWNERSHIP]
    if reverse:
        stages.reverse()
    with zero._cases.case_lock(record.case_id):
        for stage in stages:
            kind = (BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED
                    if stage == AutomationStage.READINESS
                    else BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED)
            zero._add_exception(
                zero.get(case_id=record.case_id), exception_type=kind, stage=stage,
                blocker_code=kind.value, explanation="Independent synthetic safety input.",
                evidence_version=f"independent:{stage}:1", evidence=(), actions=(),
            )
    snapshot = DurableCaseSnapshot.model_validate(
        _persistence_value(snapshot_of(zero, record.case_id)),
    )
    return client, zero, target, record.case_id, snapshot


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("reload", [False, True])
def test_identity_correction_uses_semantic_blocker_stage(reverse, reload):
    client, zero, target, case_id, snapshot = correction_blockers(reverse=reverse)
    if reload:
        client, zero, target = restore_memory_snapshot(snapshot)
    original = list(zero.get(case_id=case_id).active_exceptions)
    calls = list(target.calls)
    response = correction(
        client, zero, zero.get(case_id=case_id), choice="ENTERED", uen="202400001A",
    )
    assert response.status_code == 200
    current = zero.get(case_id=case_id)
    assert current.current_stage == AutomationStage.OWNERSHIP
    assert list(current.active_exceptions) == original
    assert len(zero._cases.get_case(case_id).identity_corrections) == 1
    assert target.calls == calls + ["search"]


@pytest.mark.parametrize("route", ["registry-identity", "identity-search-recheck"])
def test_identity_rejected_transition_has_fixed_safe_http_projection(monkeypatch, route):
    client, zero, target, case_id, _ = correction_blockers(reverse=True)
    before = zero.get(case_id=case_id)
    parent = zero._cases.get_case(case_id)
    clm = zero._clm.get(case_id=case_id)
    calls = list(target.calls)
    def reject(*args, **kwargs):
        raise ValueError("private synthetic rejected transition diagnostic")
    with monkeypatch.context() as patch:
        patch.setattr(zero._repository, "save", reject)
        body = {
            "legal_name": "Synthetic", "registration_number": "202400001A",
            "country_of_incorporation": "SG",
            "expected_automation_version": before.version, "expected_clm_version": clm.version,
            "expected_case_event_count": len(parent.events),
        }
        if route == "registry-identity":
            body["choice"] = "ENTERED"
        response = client.post(f"/api/clm/zero-touch/cases/{case_id}/{route}", json=body)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ZERO_TOUCH_TRANSITION_REJECTED"
    assert "private synthetic" not in response.text
    assert zero.get(case_id=case_id) == before
    # Monotonic parent/Search checkpoints already accepted are retained.
    assert len(zero._cases.get_case(case_id).identity_corrections) == (
        1 if route == "registry-identity" else 0
    )
    assert zero._cases.get_case(case_id).initial_target_search.request_id != (
        parent.initial_target_search.request_id
    )
    assert target.calls == calls + ["search"]


@pytest.mark.parametrize("loaded", [False, True])
def test_interrupted_ready_case_without_open_stale_ownership_still_rebuilds(monkeypatch, loaded):
    from test_phase24b_interrupted_retry import blocked_registry_case
    client, zero, _, target, registry, _, case_id = blocked_registry_case(durable=True)
    registry.available = True
    assert correction(client, zero, zero.get(case_id=case_id),
                      choice="ENTERED", uen="202400001A").status_code == 200
    assert zero._ownership.get(case_id=case_id).state == "ANALYZED"
    assert AutomationStage.OWNERSHIP in zero.get(case_id=case_id).completed_stages
    with monkeypatch.context() as patch:
        def fail(**kwargs):
            raise ClmRequestError(
                code="CLM_IDENTITY_RECHECK_STALE", message="Synthetic interruption.",
            )
        patch.setattr(zero._clm, "refresh_initial_search_after_recheck", fail)
        assert correction(client, zero, zero.get(case_id=case_id),
                          choice="ENTERED", uen="202400001A").status_code == 409
    assert zero._ownership.get(case_id=case_id) is None
    if loaded:
        zero._ownership.load(case_id=case_id)
    snapshot = DurableCaseSnapshot.model_validate(_persistence_value(snapshot_of(zero, case_id)))
    client, zero, target = restore_memory_snapshot(snapshot)
    retained = list(zero.get(case_id=case_id).active_exceptions)
    assert all(item.stage == AutomationStage.READINESS for item in retained)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    assert zero._ownership.get(case_id=case_id).state == "ANALYZED"
    assert zero._ownership.get(case_id=case_id).identity_correction_version == 2
    assert list(current.active_exceptions) == retained
    assert current.current_stage == AutomationStage.READINESS
    assert zero._clm.get(case_id=case_id).target_search_checkpoint.request_id == (
        zero._cases.get_case(case_id).initial_target_search.request_id
    )
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero.get(case_id=case_id) == current
    assert target.calls == []


def test_document_prerequisite_blocks_unfinished_ownership(monkeypatch):
    client, zero, target, _, case_id, _ = unfinished_mixed_case(monkeypatch, loaded=True)
    document = zero._documents.list_documents(case_id=case_id)[0]
    altered = document.model_copy(deep=True)
    altered.fields[0].confidence = 0.1
    zero._documents._repository.save(altered)
    ownership = zero._ownership.get(case_id=case_id)
    calls = list(target.calls)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    assert current.current_stage == AutomationStage.DOCUMENT
    assert any(item.stage == AutomationStage.DOCUMENT for item in current.active_exceptions)
    assert any(item.stage == AutomationStage.READINESS for item in current.active_exceptions)
    assert AutomationStage.DOCUMENT not in current.completed_stages
    assert zero._ownership.get(case_id=case_id) == ownership
    assert target.calls == calls


def test_ownership_failure_before_later_blocker_stops_safely(monkeypatch):
    from app.services.ownership_errors import OwnershipInfrastructureError
    client, zero, target, _, case_id, _ = unfinished_mixed_case(monkeypatch, loaded=True)
    calls = list(target.calls)
    ownership = zero._ownership.get(case_id=case_id)
    def fail(**kwargs):
        raise OwnershipInfrastructureError(
            case_id=case_id, analysis_id=ownership.analysis_id,
            correlation_id=ownership.correlation_id,
            code="OWNERSHIP_UNAVAILABLE", message="Safe failure.",
        )
    with monkeypatch.context() as patch:
        patch.setattr(zero._ownership, "analyze", fail)
        response = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "OWNERSHIP_UNAVAILABLE"
    current = zero.get(case_id=case_id)
    assert current.status == "TECHNICAL_FAILURE"
    assert current.current_stage == AutomationStage.OWNERSHIP
    assert target.calls == calls



def test_historical_v1_stale_only_recovery_does_not_project_unproved_search(monkeypatch):
    _, zero, _, _, stale, case_id = rebuilt_registry_generations(monkeypatch)
    raw = _persistence_value(snapshot_of(zero, case_id))
    raw["automation"]["stage_order_version"] = 1
    raw["automation"]["completed_stages"] = [
        stage for stage in raw["automation"]["completed_stages"] if stage != "GOLDTIER_SEARCH"
    ]
    snapshot = DurableCaseSnapshot.model_validate(raw)
    client, restarted, target = restore_memory_snapshot(snapshot)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = restarted.get(case_id=case_id)
    assert current.stage_order_version == 2
    assert current.current_stage == AutomationStage.READINESS
    assert next(item for item in current.exceptions
                if item.exception_id == stale.exception_id).status == "CANCELLED"
    assert current.completed_stages == (
        AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH,
        AutomationStage.DOCUMENT, AutomationStage.OWNERSHIP,
    )
    assert target.calls == []
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert restarted.get(case_id=case_id) == current
