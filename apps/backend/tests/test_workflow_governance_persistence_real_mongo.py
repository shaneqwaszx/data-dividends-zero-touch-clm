"""ADR-017 P2-1 governance persistence on a physical MongoDB (opt-in; integrator-run).

Runs only when ``PHASE12_MONGO_URI`` is set. Each test uses a newly generated allowlisted
disposable database (``generate_ephemeral_mongo_database``), asserted again with
``require_ephemeral_mongo_database`` before any write, and dropped afterwards. The URI is
never printed. Never point it at ``clm_poc`` or any deployed database.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from test_p2_1_migration import Seeder, p2_0_raw
from test_workflow_governance_repository import WID, approve, born, payload

from app.domain.workflow_governance import COLD_COLLECTIONS, OutboxCollection
from app.persistence.adr017_backfill import (
    verify_definition_document,
    verify_p2_1_definition_document,
)
from app.persistence.errors import PersistenceConflictError
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowStore,
)
from app.persistence.p2_1_migration import apply_p2_1_migration, plan_p2_1_migration
from app.persistence.workflow_governance_store import archive_record, dict_hash

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def store() -> Iterator[MongoWorkflowStore]:
    database = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    client: MongoClient = MongoClient(MONGO_URI, tz_aware=True)
    instance = MongoWorkflowStore(
        client,
        database=database,
        definitions_collection="clm_workflow_definitions",
        runs_collection="clm_workflow_runs",
    )
    try:
        instance.initialize()
        yield instance
    finally:
        cleanup_ephemeral_mongo_database(client, database)
        client.close()


def test_cold_indexes_are_created_idempotently(store: MongoWorkflowStore) -> None:
    store.initialize()
    database = store.definitions.database
    for name in COLD_COLLECTIONS:
        indexes = database[name].index_information()
        assert "cold_logical_id" in indexes and "cold_workflow_id" in indexes


def test_governed_publication_drain_compaction_and_cold_reads(
    store: MongoWorkflowStore,
) -> None:
    repository = MongoWorkflowDefinitionRepository(store)
    current = repository.create_governed(payload(), born())
    with pytest.raises(PersistenceConflictError):
        repository.create_governed(payload(), born())
    for number in range(1, 21):
        definition, governance = approve(current, number)
        repository.write_governance(
            definition,
            governance,
            expected_revision=current.definition.revision,
            active_version=number,
            latest_version=number,
        )
        repository.drain_outbox(WID, now=NOW)
        current = repository.get_governed(WID)
    assert len(current.definition.versions) == 16
    assert current.governance.outbox == ()
    old = repository.get_version(WID, 1)
    assert old is not None and old.version == 1
    assert repository.verify_governance_state() == []
    assert repository.verify_dispatch_state() == []
    # A stale snapshot never overwrites the durable state.
    stale, governance = approve(current, 21)
    stale = stale.model_copy(update={"write_nonce": "0" * 32})
    with pytest.raises(PersistenceConflictError):
        repository.write_governance(
            stale,
            governance,
            expected_revision=current.definition.revision,
            active_version=21,
            latest_version=21,
        )


def test_fallback_mode_fresh_suffix_on_a_physical_duplicate(store: MongoWorkflowStore) -> None:
    record = {"synthetic": 1}
    kwargs = dict(
        collection=OutboxCollection.EVENTS,
        logical_id=f"{WID}:1",
        content_hash=dict_hash(record),
        workflow_id=WID,
        record=record,
        now=NOW,
    )
    assert archive_record(store.cold, **kwargs) == 0  # type: ignore[arg-type]
    assert archive_record(store.cold, **kwargs) == 1  # type: ignore[arg-type]
    ids = sorted(
        raw["_id"] for raw in store.definitions.database["workflow_governance_events"].find({})
    )
    assert ids == [f"{WID}:1#0", f"{WID}:1#1"]


def test_migration_apply_then_mixed_version_checks(store: MongoWorkflowStore) -> None:
    raw = p2_0_raw()
    store.definitions.insert_one(raw)
    plan = plan_p2_1_migration(
        store.definitions.find({}), seed_baseline=Seeder(), now=NOW, cold=store.cold
    )
    assert apply_p2_1_migration(plan, store.definitions, store.cold, now=NOW) == 1
    stored = store.definitions.find_one({"_id": "refresh"})
    assert stored is not None and stored["payload"] == raw["payload"]
    assert verify_definition_document(stored) == "P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0"
    assert verify_p2_1_definition_document(stored, cold=store.cold) is None
    again = plan_p2_1_migration(
        store.definitions.find({}), seed_baseline=Seeder(), now=NOW, cold=store.cold
    )
    assert again.migrations == [] and again.already_migrated == ["refresh"]
