"""Caller-owned Mongo read models must stay detached from stored and later reads."""

from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import BaseModel
from scripts.performance_optimization import application
from test_phase12_persistence import MemoryEnvelopeStore
from test_slice_b_registry_demo import confirm
from test_zero_touch_exception_remediation import normal_started_case

from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.repositories import (
    MongoClmOrchestrationRepository,
    MongoDocumentProcessingRepository,
    MongoOnboardingCaseRepository,
    MongoOnboardingIntelligenceRepository,
    MongoOwnershipAnalysisRepository,
    MongoReconciliationRepository,
    MongoTargetExecutionRepository,
    MongoZeroTouchAutomationRepository,
)

READ_NAMES = (
    "case", "document", "documents", "ownership", "intelligence", "clm",
    "automation", "automation_list", "reconciliation", "ledger", "ledger_list",
)


def populated_snapshot() -> DurableCaseSnapshot:
    from uuid import UUID

    with application("memory", None) as (client, bundle, _target, _registry):
        completed = confirm(client, normal_started_case(client, garden=False))
        case_id = UUID(completed["case"]["case_id"])
        case = bundle.onboarding.get(case_id)
        assert case is not None
        snapshot = DurableCaseSnapshot(
            case_id=case_id,
            revision=0,
            onboarding=case,
            documents=tuple(bundle.documents.list_for_case(case_id)),
            ownership=bundle.ownership.get_for_case(case_id),
            intelligence=bundle.intelligence.get_for_case(case_id),
            clm=bundle.clm.get_for_case(case_id),
            reconciliation=bundle.reconciliation.get_for_case(case_id),
            automation=bundle.automation.get_for_case(case_id),
            target_executions=bundle.target_executions.list_for_case(case_id),
            created_at=case.created_at,
            updated_at=case.updated_at,
        )
    codec = object.__new__(MongoCaseStore)
    return codec._decode(codec._encode(snapshot))  # noqa: SLF001

def read(store: Any, snapshot: DurableCaseSnapshot, name: str) -> object:
    case_id = snapshot.case_id
    readers = {
        "case": lambda: MongoOnboardingCaseRepository(store).get(case_id),
        "document": lambda: MongoDocumentProcessingRepository(store).get(
            snapshot.documents[0].document_id
        ),
        "documents": lambda: MongoDocumentProcessingRepository(store).list_for_case(case_id),
        "ownership": lambda: MongoOwnershipAnalysisRepository(store).get_for_case(case_id),
        "intelligence": lambda: MongoOnboardingIntelligenceRepository(store).get_for_case(case_id),
        "clm": lambda: MongoClmOrchestrationRepository(store).get_for_case(case_id),
        "automation": lambda: MongoZeroTouchAutomationRepository(store).get_for_case(case_id),
        "automation_list": lambda: MongoZeroTouchAutomationRepository(store).list_records(),
        "reconciliation": lambda: MongoReconciliationRepository(store).get_for_case(case_id),
        "ledger": lambda: MongoTargetExecutionRepository(store).get(
            snapshot.target_executions[0].submission_input.submission_id
        ),
        "ledger_list": lambda: MongoTargetExecutionRepository(store).list_for_case(case_id),
    }
    return readers[name]()


def mutable_objects(value: object) -> Iterator[object]:
    if isinstance(value, BaseModel):
        yield value
        for name in type(value).model_fields:
            yield from mutable_objects(getattr(value, name))
    elif isinstance(value, (list, dict, set)):
        yield value
        children = value.values() if isinstance(value, dict) else value
        for item in children:
            yield from mutable_objects(item)
    elif isinstance(value, (tuple, frozenset)):
        for item in value:
            yield from mutable_objects(item)


def mutable_ids(value: object) -> set[int]:
    return {id(item) for item in mutable_objects(value)}


@pytest.mark.parametrize("name", READ_NAMES)
def test_adapter_reads_have_no_shared_model_or_mutable_container(name: str) -> None:
    snapshot = populated_snapshot()
    store = MemoryEnvelopeStore()
    store.create(snapshot)
    first, second = read(store, snapshot, name), read(store, snapshot, name)
    assert first is not None and first == second
    assert mutable_ids(first) and mutable_ids(first).isdisjoint(mutable_ids(second))
    assert store.get(snapshot.case_id) == snapshot


@pytest.mark.parametrize("kind", ["case", "document"])
def test_nested_caller_mutation_does_not_alter_stored_evidence(kind: str) -> None:
    snapshot = populated_snapshot()
    store = MemoryEnvelopeStore()
    store.create(snapshot)
    caller = read(store, snapshot, kind)
    assert caller is not None
    if kind == "case":
        caller.events.clear()
    else:
        caller.fields.clear()
    assert store.get(snapshot.case_id) == snapshot
    assert read(store, snapshot, kind) != caller


def test_missing_case_read_contract_is_unchanged() -> None:
    snapshot = populated_snapshot()
    store = MemoryEnvelopeStore()
    for name in READ_NAMES:
        assert read(store, snapshot, name) in (None, [], ())
