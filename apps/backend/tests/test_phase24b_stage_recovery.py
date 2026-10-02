"""Semantic dependency recovery over canonical owned states; offline only."""

from datetime import UTC, datetime, timedelta
from itertools import combinations_with_replacement, permutations

import pytest
from test_phase24_identity import correction
from test_phase24b_generation_currentness import rebuilt_registry_generations
from test_phase24b_interrupted_retry import restore_memory_snapshot, snapshot_of

from app.domain.zero_touch import AutomationStage, BusinessExceptionType, validate_automation_record
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import _persistence_value
from app.services.clm_errors import ClmRequestError


def mixed_case(monkeypatch, *, raise_current=True):
    client, zero, target, registry, stale, case_id = rebuilt_registry_generations(monkeypatch)
    with zero._cases.case_lock(case_id):
        zero._add_exception(
            zero.get(case_id=case_id),
            exception_type=BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED,
            stage=AutomationStage.READINESS, blocker_code="TARGET_CONFIRMATION_REQUIRED",
            explanation="Independent synthetic confirmation safety.",
            evidence_version="target-confirmation:independent:1", evidence=(), actions=(),
        )
    registry.available = False
    with monkeypatch.context() as patch:
        def fail(**kwargs):
            raise ClmRequestError(
                code="CLM_IDENTITY_RECHECK_STALE", message="Synthetic interruption.",
            )
        patch.setattr(zero._clm, "refresh_initial_search_after_recheck", fail)
        assert correction(client, zero, zero.get(case_id=case_id),
                          choice="ENTERED", uen="202400001A").status_code == 409
    assert client.post(f"/api/onboarding/cases/{case_id}/ownership/load").status_code == 201
    assert client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze").status_code == 200
    current = zero._ownership.get(case_id=case_id)
    assert current.state == "REVIEW_REQUIRED" and current.identity_correction_version == 6
    if raise_current:
        with zero._cases.case_lock(case_id):
            zero._raise_ownership_exception(zero.get(case_id=case_id), current)
    validate_automation_record(zero.get(case_id=case_id))
    return client, zero, target, stale, case_id


@pytest.mark.parametrize("reload", [False, True])
def test_canonical_pruned_mixed_chronology_recovers_ownership(monkeypatch, reload):
    client, zero, target, stale, case_id = mixed_case(monkeypatch)
    before = zero.get(case_id=case_id)
    assert [item.stage for item in before.active_exceptions] == [
        AutomationStage.OWNERSHIP, AutomationStage.READINESS, AutomationStage.OWNERSHIP,
    ]
    retained = {item.exception_id: item for item in before.active_exceptions
                if item.exception_id != stale.exception_id}
    if reload:
        snapshot = DurableCaseSnapshot.model_validate(
            _persistence_value(snapshot_of(zero, case_id)),
        )
        client, zero, target = restore_memory_snapshot(snapshot)
    calls = list(target.calls)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    recovered = zero.get(case_id=case_id)
    assert recovered.current_stage == AutomationStage.OWNERSHIP
    assert recovered.status == "WAITING_FOR_REVIEW"
    assert next(item for item in recovered.exceptions
                if item.exception_id == stale.exception_id).status == "CANCELLED"
    assert {item.exception_id: item for item in recovered.active_exceptions} == retained
    validate_automation_record(recovered)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero.get(case_id=case_id) == recovered
    assert target.calls == calls


def test_current_review_state_restores_missing_ownership_dependency(monkeypatch):
    client, zero, target, stale, case_id = mixed_case(monkeypatch, raise_current=False)
    calls = list(target.calls)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    recovered = zero.get(case_id=case_id)
    assert recovered.current_stage == AutomationStage.OWNERSHIP
    assert next(item for item in recovered.exceptions
                if item.exception_id == stale.exception_id).status == "CANCELLED"
    assert any(item.stage == AutomationStage.OWNERSHIP and item.registry_evidence_generation == 6
               for item in recovered.active_exceptions)
    assert any(item.stage == AutomationStage.READINESS for item in recovered.active_exceptions)
    assert target.calls == calls


SEMANTIC_STAGES = (
    AutomationStage.REGISTRY, AutomationStage.DOCUMENT, AutomationStage.OWNERSHIP,
    AutomationStage.READINESS, AutomationStage.MOCK_GOLDTIER,
)
BLOCKER_TYPES = {
    AutomationStage.REGISTRY: BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
    AutomationStage.DOCUMENT: BusinessExceptionType.DOCUMENT_REVIEW_REQUIRED,
    AutomationStage.OWNERSHIP: BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED,
    AutomationStage.READINESS: BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED,
    AutomationStage.MOCK_GOLDTIER: BusinessExceptionType.TARGET_PARTIAL_REVIEW_REQUIRED,
}
SEMANTIC_SETS = tuple(stages for size in (1, 2, 3)
                      for stages in combinations_with_replacement(SEMANTIC_STAGES, size))


@pytest.mark.parametrize("stages", SEMANTIC_SETS)
def test_all_one_two_three_and_duplicate_stage_permutations(monkeypatch, stages):
    # Canonical pre-submission state with pruned stale dependency. Ownership
    # permutations use a genuinely current insufficient analysis, not an arbitrary
    # incompatible automation/state swap.
    if AutomationStage.OWNERSHIP in stages:
        _, base, _, stale, case_id = mixed_case(monkeypatch)
    else:
        _, base, _, _, stale, case_id = rebuilt_registry_generations(monkeypatch)
    with base._cases.case_lock(case_id):
        previous = base.get(case_id=case_id)
        candidate = previous.model_copy(deep=True)
        for item in candidate.active_exceptions:
            if item.exception_id != stale.exception_id and item.stage != AutomationStage.OWNERSHIP:
                item.status = "CANCELLED"
        base._save(previous, candidate)
        added_ownership = False
        for index, stage in enumerate(stages):
            if stage == AutomationStage.OWNERSHIP and not added_ownership:
                added_ownership = True
                continue  # already raised by the real ownership owner
            base._add_exception(
                base.get(case_id=case_id), exception_type=BLOCKER_TYPES[stage], stage=stage,
                blocker_code=BLOCKER_TYPES[stage].value,
                explanation="Independent synthetic stage safety input.",
                evidence_version=f"independent:{stage}:{index}", evidence=(), actions=(),
            )
    frozen = DurableCaseSnapshot.model_validate(_persistence_value(snapshot_of(base, case_id)))
    live = [item for item in frozen.automation.active_exceptions
            if item.exception_id != stale.exception_id]
    assert len(live) == len(stages)
    expected = min(stages, key=SEMANTIC_STAGES.index)
    if expected == AutomationStage.MOCK_GOLDTIER:
        # The authoritative final-confirmation prerequisite must be raised by the
        # existing readiness owner before this independent later safety blocker.
        expected = AutomationStage.READINESS
    for order in permutations(range(len(live))):
        snapshot = frozen.model_copy(deep=True)
        automation = snapshot.automation
        historical = [item for item in automation.exceptions
                      if item.exception_id not in {entry.exception_id for entry in live}]
        reordered = [live[index].model_copy(deep=True) for index in order]
        for index, item in enumerate(reordered):
            item.created_at = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=len(live) - index)
        automation.exceptions = historical + reordered
        validate_automation_record(automation)
        client, zero, target = restore_memory_snapshot(snapshot)
        # /start and /resume share the owner. Avoid asking the document refresh
        # owner to reinterpret the deliberately independent safety input here.
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/start").status_code == 200
        current = zero.get(case_id=case_id)
        assert current.current_stage == expected
        original_ids = {item.exception_id for item in reordered}
        assert [item for item in current.active_exceptions
                if item.exception_id in original_ids] == reordered
        added = [item for item in current.active_exceptions
                 if item.exception_id not in original_ids]
        if min(stages, key=SEMANTIC_STAGES.index) == AutomationStage.MOCK_GOLDTIER:
            assert len(added) == 1
            assert added[0].stage == AutomationStage.READINESS
            assert added[0].blocker_code == "TARGET_CONFIRMATION_REQUIRED"
        else:
            assert added == []
        assert next(item for item in current.exceptions
                    if item.exception_id == stale.exception_id).status == "CANCELLED"
        assert client.post(f"/api/clm/zero-touch/cases/{case_id}/start").status_code == 200
        assert zero.get(case_id=case_id) == current
        assert target.calls == []


def test_current_ownership_and_stale_readiness_dependency(monkeypatch):
    client, zero, target, stale, case_id = mixed_case(monkeypatch)
    with zero._cases.case_lock(case_id):
        zero._add_exception(
            zero.get(case_id=case_id),
            exception_type=BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED,
            stage=AutomationStage.READINESS, blocker_code="OWNERSHIP_REVIEW_REQUIRED",
            explanation="Superseded registry readiness dependency.",
            evidence_version=stale.evidence_version, registry_evidence_generation=0,
            evidence=(), actions=(),
        )
    calls = list(target.calls)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero.get(case_id=case_id)
    assert current.current_stage == AutomationStage.OWNERSHIP
    assert all(item.registry_evidence_generation != 0 for item in current.active_exceptions)
    assert any(item.blocker_code == "TARGET_CONFIRMATION_REQUIRED"
               for item in current.active_exceptions)
    assert target.calls == calls


def test_rejected_transition_is_sanitized_and_preserves_durable_state(monkeypatch):
    client, zero, target, _, case_id = mixed_case(monkeypatch)
    before = snapshot_of(zero, case_id)
    calls = list(target.calls)
    def reject(*args, **kwargs):
        raise ValueError("private synthetic validation diagnostic")
    with monkeypatch.context() as patch:
        patch.setattr(zero._repository, "save", reject)
        response = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    assert response.status_code == 503
    assert "ZERO_TOUCH_TRANSITION_REJECTED" in response.text
    assert "private synthetic" not in response.text
    assert zero.get(case_id=case_id) == before.automation
    assert zero._ownership.get(case_id=case_id) == before.ownership
    assert target.calls == calls



def test_impossible_internal_stage_transition_is_rejected_without_mutation(monkeypatch):
    client, zero, target, _, case_id = mixed_case(monkeypatch)
    before = zero.get(case_id=case_id)
    calls = list(target.calls)
    save = zero._repository.save
    def impossible(record, *, expected_version):
        candidate = record.model_copy(deep=True)
        candidate.current_stage = AutomationStage.READINESS
        return save(candidate, expected_version=expected_version)
    with monkeypatch.context() as patch:
        patch.setattr(zero._repository, "save", impossible)
        response = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    assert response.status_code == 503
    assert "ZERO_TOUCH_TRANSITION_REJECTED" in response.text
    assert "earliest open blocker" not in response.text
    assert zero.get(case_id=case_id) == before
    assert target.calls == calls



def test_historical_v1_stage_order_recovery_uses_its_existing_prefix(monkeypatch):
    _, zero, _, stale, case_id = mixed_case(monkeypatch)
    raw = _persistence_value(snapshot_of(zero, case_id))
    # Simulate an accepted historical v1 serialized automation record. Decode
    # never fabricates a Search stage or downgrades an existing repository row.
    raw["automation"]["stage_order_version"] = 1
    raw["automation"]["completed_stages"] = [
        stage for stage in raw["automation"]["completed_stages"] if stage != "GOLDTIER_SEARCH"
    ]
    snapshot = DurableCaseSnapshot.model_validate(raw)
    client, restarted, target = restore_memory_snapshot(snapshot)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    recovered = restarted.get(case_id=case_id)
    assert recovered.current_stage == AutomationStage.OWNERSHIP
    assert recovered.stage_order_version == 2
    assert recovered.completed_stages == (
        AutomationStage.REGISTRY, AutomationStage.GOLDTIER_SEARCH, AutomationStage.DOCUMENT,
    )
    search = restarted._clm.get(case_id=case_id).target_search_checkpoint
    assert search.status == "COMPLETED"
    assert search.request_id == restarted._cases.get_case(case_id).initial_target_search.request_id
    assert any(event.code == "AUTOMATION_STAGE_ORDER_UPGRADED" for event in recovered.events)
    assert next(item for item in recovered.exceptions
                if item.exception_id == stale.exception_id).status == "CANCELLED"
    validate_automation_record(recovered)
    assert target.calls == []
