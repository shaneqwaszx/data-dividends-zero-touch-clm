"""Generation-first currentness survives bounded history; authenticated local routes."""

import pytest
from test_phase24_identity import correction
from test_phase24b_interrupted_retry import (
    blocked_registry_case,
    interrupt_refresh,
    restore_memory_snapshot,
    snapshot_of,
)
from test_zero_touch_orchestration import PDF, AddressMismatchIdp

from app.domain.zero_touch import AutomationStage, BusinessExceptionType
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import _persistence_value
from app.services.zero_touch_errors import ZeroTouchRequestError


def rebuilt_registry_generations(monkeypatch, *, replacements=5, legacy=False):
    client, zero, _, target, registry, blocker, case_id = blocked_registry_case(durable=True)
    original = zero._ownership.get(case_id=case_id)
    for generation in range(1, replacements + 1):
        interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                          boundary="clm", legacy=legacy, generation=generation)
        assert client.post(f"/api/onboarding/cases/{case_id}/ownership/load").status_code == 201
        assert client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze").status_code == 200
        current = zero._ownership.get(case_id=case_id)
        assert current.state == "ANALYZED"
        assert current.identity_correction_version == generation
        assert len(current.prior_analyses) == min(generation, 4)
    assert len(zero._cases.get_case(case_id).identity_corrections) == replacements
    current = zero._ownership.get(case_id=case_id)
    assert (original.analysis_id in {item.analysis_id for item in current.prior_analyses}) == (
        replacements <= 4
    )
    assert next(item for item in zero.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "OPEN"
    return client, zero, target, registry, blocker, case_id


@pytest.mark.parametrize("replacements", [4, 5, 10, 12])
def test_numeric_registry_generation_retires_after_legitimate_history_pruning(
    monkeypatch, replacements,
):
    client, zero, target, _, blocker, case_id = rebuilt_registry_generations(
        monkeypatch, replacements=replacements,
    )
    current_analysis = zero._ownership.get(case_id=case_id)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    recovered = zero.get(case_id=case_id)
    assert next(item for item in recovered.exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert zero._ownership.get(case_id=case_id).analysis_id == current_analysis.analysis_id
    assert {item.blocker_code for item in recovered.active_exceptions} == {
        "TARGET_CONFIRMATION_REQUIRED",
    }
    assert target.calls == ["search"] * (replacements + 1)


@pytest.mark.parametrize("replacements", [4, 5, 10])
def test_numeric_pruning_serialized_restart_and_further_correction(monkeypatch, replacements):
    _, zero, _, _, blocker, case_id = rebuilt_registry_generations(
        monkeypatch, replacements=replacements,
    )
    restored = DurableCaseSnapshot.model_validate(_persistence_value(snapshot_of(zero, case_id)))
    client, restarted, target = restore_memory_snapshot(restored)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert next(item for item in restarted.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert restarted._ownership.get(case_id=case_id).state == "ANALYZED"
    assert target.calls == []
    assert correction(client, restarted, restarted.get(case_id=case_id),
                      choice="ENTERED", uen="202400001A").status_code == 200
    assert restarted._ownership.get(case_id=case_id).identity_correction_version == replacements + 1
    assert next(item for item in restarted.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert {item.blocker_code for item in restarted.get(case_id=case_id).active_exceptions} == {
        "TARGET_CONFIRMATION_REQUIRED",
    }
    assert target.calls == ["search"]


@pytest.mark.parametrize("replacements, expected", [(4, "CANCELLED"), (5, "OPEN"), (10, "OPEN")])
def test_legacy_null_uses_only_retained_proof_without_guessing(monkeypatch, replacements, expected):
    client, zero, target, _, blocker, case_id = rebuilt_registry_generations(
        monkeypatch, replacements=replacements, legacy=True,
    )
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert next(item for item in zero.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == expected
    assert target.calls == ["search"] * (replacements + 1)


@pytest.mark.parametrize("binding, expected", [(0, "CANCELLED"), (5, "OPEN"), (6, "OPEN")])
def test_pruned_less_equal_future_generation_remains_safe(monkeypatch, binding, expected):
    client, zero, _, _, blocker, case_id = rebuilt_registry_generations(monkeypatch)
    old = zero.get(case_id=case_id)
    changed = old.model_copy(deep=True)
    next(item for item in changed.exceptions
         if item.exception_id == blocker.exception_id).registry_evidence_generation = binding
    zero._save(old, changed)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    assert next(item for item in current.exceptions
                if item.exception_id == blocker.exception_id).status == expected
    if expected == "OPEN":
        assert current.status == "WAITING_FOR_REVIEW"
        assert zero._ownership.get(case_id=case_id).state == "ANALYZED"


@pytest.mark.parametrize("stage", [AutomationStage.OWNERSHIP, AutomationStage.READINESS])
def test_new_registry_ownership_dependencies_bind_even_on_current_legacy_analysis(stage):
    _, zero, _, _, _, _, case_id = blocked_registry_case()
    retained = zero._ownership.get(case_id=case_id)
    zero._ownership._repository._records[case_id] = retained.model_copy(
        update={"identity_correction_version": None}, deep=True,
    )
    candidate = zero._add_exception(
        zero.get(case_id=case_id), exception_type=BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED,
        stage=stage, blocker_code="OWNERSHIP_REVIEW_REQUIRED",
        explanation="Synthetic current registry dependency.",
        evidence_version=f"ownership:{retained.analysis_id}:{retained.version}",
        evidence=(), actions=(),
    )
    new = next(item for item in candidate.active_exceptions
               if item.exception_type == BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED)
    assert new.registry_evidence_generation == 0
    restored = DurableCaseSnapshot.model_validate(_persistence_value(snapshot_of(zero, case_id)))
    assert next(item for item in restored.automation.active_exceptions
                if item.exception_id == new.exception_id).registry_evidence_generation == 0


def test_generation_metadata_cannot_retire_target_safety(monkeypatch):
    client, zero, _, _, blocker, case_id = rebuilt_registry_generations(monkeypatch)
    target = zero._add_exception(
        zero.get(case_id=case_id),
        exception_type=BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
        stage=AutomationStage.READINESS, blocker_code="TARGET_CONFIRMATION_REQUIRED",
        explanation="Synthetic target safety decision.",
        evidence_version="target-confirmation:1:1", evidence=(), actions=(),
        registry_evidence_generation=0,
    ).active_exceptions[-1]
    assert not zero._is_obsolete_registry_ownership_exception(case_id, target)
    zero.start(case_id=case_id)
    current = zero.get(case_id=case_id)
    assert next(item for item in current.exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert next(item for item in current.active_exceptions
                if item.exception_id == target.exception_id) == target


def test_current_insufficient_registry_blocker_survives_beside_pruned_stale_one(monkeypatch):
    client, zero, target, registry, blocker, case_id = rebuilt_registry_generations(monkeypatch)
    obsolete_candidate = zero.get(case_id=case_id)
    registry.available = False
    with monkeypatch.context() as patch:
        def fail(**kwargs):
            from app.services.clm_errors import ClmRequestError
            raise ClmRequestError(
                code="CLM_IDENTITY_RECHECK_STALE", message="Synthetic interruption.",
            )
        patch.setattr(zero._clm, "refresh_initial_search_after_recheck", fail)
        assert correction(client, zero, obsolete_candidate,
                          choice="ENTERED", uen="202400001A").status_code == 409
    assert client.post(f"/api/onboarding/cases/{case_id}/ownership/load").status_code == 201
    assert client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze").status_code == 200
    ownership = zero._ownership.get(case_id=case_id)
    assert ownership.state == "REVIEW_REQUIRED" and ownership.identity_correction_version == 6
    with zero._cases.case_lock(case_id):
        raised = zero._raise_ownership_exception(zero.get(case_id=case_id), ownership)
    genuine = next(item for item in raised.active_exceptions
                   if item.exception_id != blocker.exception_id)
    assert genuine.registry_evidence_generation == 6
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    assert next(item for item in current.exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert next(item for item in current.active_exceptions
                if item.exception_id == genuine.exception_id) == genuine
    assert target.calls == ["search"] * 7
    with pytest.raises(ZeroTouchRequestError) as stale:
        zero._save(obsolete_candidate, obsolete_candidate.model_copy(deep=True))
    assert stale.value.code == "ZERO_TOUCH_AUTOMATION_CONFLICT"
    assert zero.get(case_id=case_id) == current


def test_a_to_b_to_a_after_pruning_uses_current_generation(monkeypatch):
    client, zero, target, registry, blocker, case_id = rebuilt_registry_generations(monkeypatch)
    old_a = zero._ownership.get(case_id=case_id)
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=False, generation=6,
                      uen="202400009I", choice="OTHER")
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=False, generation=7,
                      uen="202400001A", choice="OTHER")
    assert zero._ownership.get(case_id=case_id) is None
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero._ownership.get(case_id=case_id)
    assert current.analysis_id != old_a.analysis_id
    assert current.identity_registration_number == old_a.identity_registration_number
    assert current.identity_correction_version == 7 and current.state == "ANALYZED"
    assert next(item for item in zero.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert target.calls == ["search"] * 8


def test_actual_document_mismatch_remains_actionable_after_stale_retirement(monkeypatch):
    client, zero, target, _, blocker, case_id = rebuilt_registry_generations(monkeypatch)
    zero._documents._idp = AddressMismatchIdp()
    response = client.post(f"/api/onboarding/cases/{case_id}/documents", content=PDF,
                           headers={"Content-Type": "application/pdf",
                                    "X-Document-Name": "synthetic-mismatch.pdf"})
    assert response.status_code == 201
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    blocked = zero.get(case_id=case_id)
    assert next(item for item in blocked.exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert blocked.active_exceptions
    assert all(item.stage == AutomationStage.DOCUMENT for item in blocked.active_exceptions)
    mismatches = {item.exception_id for item in blocked.active_exceptions}
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    assert mismatches <= {item.exception_id for item in current.active_exceptions}
    assert current.status == "WAITING_FOR_REVIEW"
    assert target.calls == ["search"] * 6
