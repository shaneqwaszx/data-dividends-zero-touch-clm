"""Physical Mongo evidence for immutable GoldTier provider identity."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)

from app.composition import (
    build_clm_orchestration_service,
    build_document_processing_service,
    build_onboarding_service,
    build_ownership_analysis_service,
)
from app.config import Settings
from app.domain.clm import (
    ClmSubmissionSnapshot,
    EvidenceReference,
    GoldTierSubmissionPlan,
    ProvisionalUboSummary,
)
from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierProviderMode,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
COLLECTION_NAME = "clm_case_snapshots"


@pytest.fixture
def isolated_provider_database() -> Iterator[str]:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p12")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    assert database not in client.list_database_names()
    try:
        yield database
    finally:
        unexpected_collections = set(client[database].list_collection_names()) - {
            COLLECTION_NAME
        }
        cleanup_ephemeral_mongo_database(client, database)
        cleanup_succeeded = database not in client.list_database_names()
        client.close()
        assert not unexpected_collections
        assert cleanup_succeeded


def _open_store(database: str, *, initialize: bool = True) -> MongoCaseStore:
    assert MONGO_URI is not None
    store = MongoCaseStore(
        MongoClient(MONGO_URI),
        database=database,
        collection=COLLECTION_NAME,
    )
    if initialize:
        store.initialize()
    return store


def _provider_bound_snapshot(mode: GoldTierProviderMode) -> DurableCaseSnapshot:
    settings = Settings(_env_file=None)
    onboarding = build_onboarding_service(settings=settings)
    documents = build_document_processing_service(onboarding, settings)
    ownership = build_ownership_analysis_service(onboarding, settings)
    clm = build_clm_orchestration_service(onboarding, documents, ownership)
    record = clm.create_case("202400001A")
    case = onboarding.get_case(record.case_id)
    assert case is not None
    target_input = onboarding.build_submission_input(case, provider_mode=mode)
    now = datetime.now(UTC)
    submission_snapshot = ClmSubmissionSnapshot(
        snapshot_id=uuid4(),
        target_input=target_input,
        document_references=(),
        ownership_reference=EvidenceReference(
            reference_id=uuid4(),
            version=1,
            status="ANALYZED",
            updated_at=now,
        ),
        provisional_ubo=ProvisionalUboSummary(candidate_count=0),
        created_at=now,
    )
    provider_classification = "MOCK" if mode == GoldTierProviderMode.MOCK else "SANDBOX_PARTIAL"
    bound_record = record.model_copy(
        update={
            "submission_plan": GoldTierSubmissionPlan(
                environment=mode,
                provider_classification=provider_classification,
            ),
            "submission_snapshot": submission_snapshot,
        },
        deep=True,
    )
    return DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=case,
        clm=bound_record,
        target_executions=(
            GoldTierExecutionLedgerEntry(
                submission_input=target_input,
                state=GoldTierExecutionLedgerState.NOT_STARTED,
            ),
        ),
        created_at=now,
        updated_at=now,
    )


def _insert_raw(database: str, raw: dict[str, Any]) -> None:
    assert MONGO_URI is not None
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        client[database][COLLECTION_NAME].insert_one(raw)
    finally:
        client.close()


@pytest.mark.parametrize(
    "mode",
    [GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX],
)
def test_physical_restart_preserves_stable_provider_identity(
    isolated_provider_database: str,
    mode: GoldTierProviderMode,
) -> None:
    database = isolated_provider_database
    original = _provider_bound_snapshot(mode)
    store = _open_store(database)
    store.create(original)
    store.close()

    restarted = _open_store(database)
    try:
        restored = restarted.get(original.case_id)
        assert restored is not None and restored.clm is not None
        assert restored.clm.submission_snapshot is not None
        assert restored.clm.submission_plan.environment == mode
        assert restored.clm.submission_snapshot.target_input.provider_mode == mode
        assert restored.target_executions[0].submission_input.provider_mode == mode
    finally:
        restarted.close()


@pytest.mark.parametrize(
    ("plan_mode", "contradictory_mode"),
    [
        (GoldTierProviderMode.MOCK, GoldTierProviderMode.SANDBOX),
        (GoldTierProviderMode.SANDBOX, GoldTierProviderMode.MOCK),
    ],
)
def test_physical_restart_rejects_plan_input_contradiction(
    isolated_provider_database: str,
    plan_mode: GoldTierProviderMode,
    contradictory_mode: GoldTierProviderMode,
) -> None:
    snapshot = _provider_bound_snapshot(plan_mode)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["clm"]["submission_snapshot"]["target_input"]["provider_mode"] = (
        contradictory_mode.value
    )
    raw["target_executions"] = []
    _insert_raw(isolated_provider_database, raw)

    restarted = _open_store(isolated_provider_database, initialize=False)
    try:
        with pytest.raises(PersistenceDataInvalidError):
            restarted.get(snapshot.case_id)
        with pytest.raises(PersistenceDataInvalidError):
            restarted.initialize()
    finally:
        restarted.close()


def test_physical_restart_rejects_matching_ledger_provider_contradiction(
    isolated_provider_database: str,
) -> None:
    snapshot = _provider_bound_snapshot(GoldTierProviderMode.MOCK)
    raw = snapshot.model_dump(mode="json")
    raw["_id"] = str(snapshot.case_id)
    raw["target_executions"][0]["submission_input"]["provider_mode"] = "SANDBOX"
    _insert_raw(isolated_provider_database, raw)

    restarted = _open_store(isolated_provider_database, initialize=False)
    try:
        with pytest.raises(PersistenceDataInvalidError):
            restarted.get(snapshot.case_id)
        with pytest.raises(PersistenceDataInvalidError):
            restarted.initialize()
    finally:
        restarted.close()


def test_physical_restart_accepts_plan_without_submission(
    isolated_provider_database: str,
) -> None:
    snapshot = _provider_bound_snapshot(GoldTierProviderMode.SANDBOX)
    assert snapshot.clm is not None
    plan_only = snapshot.model_copy(
        update={
            "clm": snapshot.clm.model_copy(
                update={"submission_snapshot": None},
                deep=True,
            ),
            "target_executions": (),
        },
        deep=True,
    )
    store = _open_store(isolated_provider_database)
    store.create(plan_only)
    store.close()

    restarted = _open_store(isolated_provider_database)
    try:
        restored = restarted.get(plan_only.case_id)
        assert restored is not None and restored.clm is not None
        assert restored.clm.submission_plan.environment == GoldTierProviderMode.SANDBOX
        assert restored.clm.submission_snapshot is None
        assert restored.target_executions == ()
    finally:
        restarted.close()
