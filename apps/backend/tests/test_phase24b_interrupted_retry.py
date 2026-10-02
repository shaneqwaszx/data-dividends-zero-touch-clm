"""Bounded interrupted registry-generation recovery; local synthetic evidence."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from test_phase24_identity import correction
from test_phase24b_p2_regressions import RecoveringRegistry
from test_zero_touch_orchestration import PDF, build_system

from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.documents import DocumentAutoClearBlocker
from app.domain.zero_touch import AutomationStage, BusinessExceptionType
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import _persistence_value
from app.services.clm_errors import ClmRequestError
from app.services.ownership_repository import OwnershipRepositoryConflictError
from app.services.reconciliation_errors import ReconciliationInfrastructureError
from app.services.zero_touch_errors import ZeroTouchRequestError
from app.services.zero_touch_provider_bindings import DurableOwnershipProviderBindingResolver


def blocked_registry_case(*, durable=False):
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    registry = RecoveringRegistry()
    zero._cases._registry_router = RegistryProviderRouter(AcraRegistryProviderAdapter(registry))
    zero._ownership._provider = RegistryAcquisitionOwnershipProvider(zero._cases)
    if durable:
        zero._ownership_provider_bindings = DurableOwnershipProviderBindingResolver(
            lambda: zero._ownership.configured_provider,
        )
    assert client.get("/api/auth/me").status_code == 200
    response = client.post("/api/clm/zero-touch/cases", json={
        "uen": "202400001A", "legal_name": "Synthetic", "country_of_incorporation": "SG",
    })
    assert response.status_code == 201
    case_id = UUID(response.json()["case"]["case_id"])
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/documents", content=PDF,
                       headers={"Content-Type": "application/pdf",
                                "X-Document-Name": "synthetic.pdf"}).status_code == 200
    blocked = zero.get(case_id=case_id)
    blocker = next(item for item in blocked.active_exceptions
                   if item.blocker_code == "OWNERSHIP_REQUIRED")
    assert blocker.registry_evidence_generation == 0
    return client, zero, documents, target, registry, blocker, case_id


def interrupt_refresh(
    client, zero, registry, blocker, monkeypatch, *, case_id, boundary, legacy,
    uen="202400001A", choice="ENTERED", generation=1,
):
    blocked = zero.get(case_id=case_id)
    if legacy:
        candidate = blocked.model_copy(deep=True)
        next(item for item in candidate.active_exceptions
             if item.exception_id == blocker.exception_id).registry_evidence_generation = None
        blocked = zero._save(blocked, candidate)
    registry.available = True
    with monkeypatch.context() as patch:
        if boundary == "reconciliation":
            def fail(**kwargs):
                raise ReconciliationInfrastructureError(
                    code="RECONCILIATION_UNAVAILABLE", message="Synthetic interruption.",
                )
            patch.setattr(zero._reconciliation, "reconcile_current", fail)
            response = correction(client, zero, blocked, choice=choice, uen=uen)
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "RECONCILIATION_UNAVAILABLE"
        else:
            def fail(**kwargs):
                raise ClmRequestError(code="CLM_IDENTITY_RECHECK_STALE",
                                      message="Synthetic checkpoint interruption.")
            patch.setattr(zero._clm, "refresh_initial_search_after_recheck", fail)
            response = correction(client, zero, blocked, choice=choice, uen=uen)
            assert response.status_code == 409
    assert len(zero._cases.get_case(case_id).identity_corrections) == generation
    assert zero._ownership.get(case_id=case_id) is None
    assert next(item for item in zero.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "OPEN"
    return case_id


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("boundary", ["reconciliation", "clm"])
@pytest.mark.parametrize("retry", ["resume", "correction"])
def test_interrupted_same_uen_recovers_exact_obsolete_blocker(monkeypatch, legacy, boundary, retry):
    client, zero, _, target, registry, blocker, case_id = blocked_registry_case()
    old = zero._ownership.get(case_id=case_id)
    case_id = interrupt_refresh(client, zero, registry, blocker, monkeypatch,
                                case_id=case_id, boundary=boundary, legacy=legacy)
    if retry == "resume":
        response = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    else:
        response = correction(client, zero, zero.get(case_id=case_id),
                              choice="ENTERED", uen="202400001A")
    assert response.status_code == 200
    current = zero.get(case_id=case_id)
    retained = next(item for item in current.exceptions
                    if item.exception_id == blocker.exception_id)
    assert retained.status == "CANCELLED"
    ownership = zero._ownership.get(case_id=case_id)
    assert ownership is not None and ownership.state == "ANALYZED"
    assert ownership.analysis_id != old.analysis_id
    assert ownership.identity_correction_version == (1 if retry == "resume" else 2)
    assert ownership.prior_analyses[-1].analysis_id == old.analysis_id
    assert {item.blocker_code for item in current.active_exceptions} == {
        "TARGET_CONFIRMATION_REQUIRED",
    }
    assert target.calls == ["search"] * (2 if retry == "resume" else 3)
    checkpoint = zero._clm.get(case_id=case_id).target_search_checkpoint
    assert checkpoint.request_id == zero._cases.get_case(case_id).initial_target_search.request_id
    version = current.version
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero.get(case_id=case_id).version == version
    assert target.calls == ["search"] * (2 if retry == "resume" else 3)


def snapshot_of(zero, case_id):
    now = datetime.now(UTC)
    return DurableCaseSnapshot(
        case_id=case_id, revision=0, onboarding=zero._cases.get_case(case_id),
        documents=tuple(zero._documents.list_documents(case_id=case_id)),
        ownership=zero._ownership._repository.get_for_case(case_id),
        reconciliation=zero._reconciliation._repository.get_for_case(case_id),
        clm=zero._clm._repository.get_for_case(case_id), automation=zero.get(case_id=case_id),
        created_at=now, updated_at=now,
    )


def restore_memory_snapshot(snapshot):
    client, zero, _, target, _ = build_system(require_confirmation=True)
    case_id = snapshot.case_id
    zero._cases._repository.create(snapshot.onboarding)
    for document in snapshot.documents:
        zero._documents._repository.save(document)
    zero._ownership._repository._records[case_id] = snapshot.ownership
    zero._clm._repository._records[case_id] = snapshot.clm
    zero._repository._records[case_id] = snapshot.automation
    zero._reconciliation._repository._records[case_id] = snapshot.reconciliation
    zero._ownership._provider = RegistryAcquisitionOwnershipProvider(zero._cases)
    zero._ownership_provider_bindings = DurableOwnershipProviderBindingResolver(
        lambda: zero._ownership.configured_provider,
    )
    return client, zero, target


@pytest.mark.parametrize("legacy_analysis", [False, True])
def test_serialized_reload_uses_retained_generation_and_legacy_history(
    monkeypatch, legacy_analysis,
):
    client, zero, _, _, registry, blocker, case_id = blocked_registry_case(durable=True)
    old = zero._ownership.get(case_id=case_id)
    if legacy_analysis:
        zero._ownership._repository._records[case_id] = old.model_copy(
            update={"identity_correction_version": None}, deep=True,
        )
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=True)
    raw = _persistence_value(snapshot_of(zero, case_id))
    for item in raw["automation"]["exceptions"]:
        item.pop("registry_evidence_generation", None)
    restored = DurableCaseSnapshot.model_validate(raw)
    restarted_client, restarted, target = restore_memory_snapshot(restored)
    assert restarted._ownership.get(case_id=case_id) is None
    assert restarted_client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    ownership = restarted._ownership.get(case_id=case_id)
    assert ownership.state == "ANALYZED" and ownership.identity_correction_version == 1
    assert next(item for item in restarted.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert target.calls == []


def test_interrupted_a_to_b_to_a_never_resurrects_first_a(monkeypatch):
    client, zero, _, target, registry, blocker, case_id = blocked_registry_case()
    old = zero._ownership.get(case_id=case_id)
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=True, uen="202400009I", choice="OTHER")
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=True, uen="202400001A", choice="OTHER", generation=2)
    assert zero._cases.get_case(case_id).requested_uen == old.identity_registration_number
    assert zero._ownership.get(case_id=case_id) is None
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    current = zero._ownership.get(case_id=case_id)
    assert current.analysis_id != old.analysis_id
    assert current.identity_correction_version == 2 and current.state == "ANALYZED"
    assert target.calls == ["search"] * 3
    assert next(item for item in zero.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    # Neither an old automation candidate nor an old ownership completion owns CAS.
    with pytest.raises(ZeroTouchRequestError) as conflict:
        zero._save(snapshot_of(zero, case_id).automation.model_copy(update={"version": 1}),
                   snapshot_of(zero, case_id).automation)
    assert conflict.value.code == "ZERO_TOUCH_AUTOMATION_CONFLICT"
    with pytest.raises(OwnershipRepositoryConflictError):
        zero._ownership._repository.save(old.model_copy(update={"version": old.version + 1}),
                                         expected_version=old.version)
    assert zero._ownership.get(case_id=case_id) == current


def test_retained_history_matches_legacy_blocker_after_current_analysis_rebuild(monkeypatch):
    client, zero, _, target, registry, blocker, case_id = blocked_registry_case()
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="reconciliation", legacy=True)
    zero._ownership.load(case_id=case_id)
    current = zero._ownership.analyze(case_id=case_id)
    assert current.state == "ANALYZED"
    assert zero._ownership.registry_dependency_is_obsolete(
        case_id=case_id, evidence_version=blocker.evidence_version,
    )
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero._ownership.get(case_id=case_id).analysis_id == current.analysis_id
    assert next(item for item in zero.get(case_id=case_id).exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert target.calls == ["search", "search"]


def test_current_registry_blocker_and_unknown_binding_remain_open():
    client, zero, _, target, _, blocker, case_id = blocked_registry_case()
    before = zero.get(case_id=case_id)
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero.get(case_id=case_id) == before
    assert not zero._ownership.registry_dependency_is_obsolete(
        case_id=case_id, evidence_version=f"ownership:{uuid4()}:1",
    )
    assert not zero._ownership.registry_dependency_is_obsolete(
        case_id=case_id, evidence_version=blocker.evidence_version,
    )
    assert target.calls == ["search"]


@pytest.mark.parametrize("kind", ["document", "classification", "target", "independent"])
def test_recovery_preserves_unrelated_blocker_identity_and_decision(monkeypatch, kind):
    client, zero, _, target, registry, blocker, case_id = blocked_registry_case()
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=True)
    record = zero.get(case_id=case_id)
    types = {
        "document": (BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE, AutomationStage.DOCUMENT),
        "classification": (BusinessExceptionType.TARGET_CLASSIFICATION_REQUIRED,
                           AutomationStage.READINESS),
        "target": (BusinessExceptionType.TARGET_CONFIRMATION_REQUIRED, AutomationStage.READINESS),
        "independent": (BusinessExceptionType.OWNERSHIP_REVIEW_REQUIRED, AutomationStage.OWNERSHIP),
    }
    if kind == "document":
        document = zero._documents.list_documents(case_id=case_id)[0]
        altered = document.model_copy(deep=True)
        altered.fields[0].confidence = 0.1
        zero._documents._repository.save(altered)
        candidate = zero._raise_document_exception(record, altered,
                                                   (DocumentAutoClearBlocker.LOW_CONFIDENCE,))
    else:
        exception_type, stage = types[kind]
        candidate = zero._add_exception(
            record, exception_type=exception_type, stage=stage,
            blocker_code={"classification": "TARGET_CLASSIFICATION_REQUIRED",
                          "target": "TARGET_CONFIRMATION_REQUIRED",
                          "independent": "OWNERSHIP_REQUIRED"}[kind],
            explanation="Synthetic current independent decision.",
            evidence_version=f"independent:{uuid4()}:1", evidence=(), actions=(),
        )
    record = candidate
    unrelated = next(item for item in record.active_exceptions
                     if item.exception_id != blocker.exception_id)
    # Normal owning service retry retains independent human decisions verbatim.
    zero.start(case_id=case_id)
    after = zero.get(case_id=case_id)
    assert next(item for item in after.exceptions
                if item.exception_id == blocker.exception_id).status == "CANCELLED"
    assert next(item for item in after.active_exceptions
                if item.exception_id == unrelated.exception_id) == unrelated
    assert target.calls == ["search", "search"]


def test_recovery_reauthorizes_inside_lock_before_writes(monkeypatch):
    client, zero, _, target, registry, blocker, case_id = blocked_registry_case()
    interrupt_refresh(client, zero, registry, blocker, monkeypatch, case_id=case_id,
                      boundary="clm", legacy=True)
    before = snapshot_of(zero, case_id)
    def deny():
        assert zero._cases.case_lock(case_id)._is_owned()
        raise ZeroTouchRequestError(code="SYNTHETIC_FORBIDDEN", message="Synthetic denial.")
    with pytest.raises(ZeroTouchRequestError) as denied:
        zero.start(case_id=case_id, reauthorize=deny)
    assert denied.value.code == "SYNTHETIC_FORBIDDEN"
    after = snapshot_of(zero, case_id)
    assert after.model_copy(update={"created_at": before.created_at,
                                    "updated_at": before.updated_at}) == before
    assert target.calls == ["search", "search"]


def test_new_insufficient_generation_remains_genuine_and_stale_request_has_no_effect():
    client, zero, _, target, _, blocker, case_id = blocked_registry_case()
    old = zero.get(case_id=case_id)
    parent = zero._cases.get_case(case_id)
    clm = zero._clm.get(case_id=case_id)
    assert correction(client, zero, old, choice="ENTERED", uen="202400001A").status_code == 200
    current = zero.get(case_id=case_id)
    new_blocker = next(item for item in current.active_exceptions
                       if item.blocker_code == "OWNERSHIP_REQUIRED")
    assert new_blocker.exception_id != blocker.exception_id
    assert new_blocker.registry_evidence_generation == 1
    assert zero._ownership.get(case_id=case_id).state == "REVIEW_REQUIRED"
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").status_code == 200
    assert zero.get(case_id=case_id) == current
    response = correction(client, zero, old, choice="ENTERED", uen="202400001A",
                          expected_clm_version=clm.version,
                          expected_case_event_count=len(parent.events))
    assert response.status_code == 409
    assert zero.get(case_id=case_id) == current
    assert target.calls == ["search", "search"]
