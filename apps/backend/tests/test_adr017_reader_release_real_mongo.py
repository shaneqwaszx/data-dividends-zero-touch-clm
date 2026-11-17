"""ADR-017 P2-0 reader release against a physical, disposable MongoDB.

Opt-in like every ``*_real_mongo`` suite: it runs only when ``PHASE12_MONGO_URI`` is set.
Each test uses a newly generated allowlisted database that is dropped afterwards. It never
touches ``clm_poc``, ``clm_staging`` or a staging host.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_adr017_reader_release import (
    TOKEN,
    _authorised_with_first_write,
    _definition,
    _snapshot,
    _writer_release_snapshot,
)

from app.persistence.adr017_migrations import apply_reverse_migration, plan_reverse_migration
from app.persistence.errors import PersistenceConflictError
from app.persistence.mongo_case_store import MongoCaseStore
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowStore,
)
from app.persistence.repositories import MongoDemoScenarioRepository

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
CASES = "clm_case_snapshots"
DEFINITIONS = "clm_workflow_definitions"


@pytest.fixture
def mongo() -> Iterator[tuple[MongoClient[dict[str, Any]], str]]:
    database = generate_ephemeral_mongo_database("p12")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        yield client, database
    finally:
        cleanup_ephemeral_mongo_database(client, database)
        client.close()


def _case_store(client: MongoClient[dict[str, Any]], database: str) -> MongoCaseStore:
    store = MongoCaseStore(client, database=database, collection=CASES)
    store.initialize()
    return store


def test_reader_write_round_trips_a_writer_release_claim_byte_for_byte(mongo) -> None:
    client, database = mongo
    store = _case_store(client, database)
    snapshot = _writer_release_snapshot()
    raw = store._encode(snapshot)  # noqa: SLF001
    client[database][CASES].insert_one(raw)
    before = client[database][CASES].find_one({"_id": raw["_id"]})
    assert before is not None

    MongoDemoScenarioRepository(store).set(snapshot.case_id, "adr017-reader")

    after = client[database][CASES].find_one({"_id": raw["_id"]})
    assert after is not None
    assert after["target_executions"][0]["workflow_dispatch"] == (
        before["target_executions"][0]["workflow_dispatch"]
    )
    assert isinstance(after["target_executions"][0]["workflow_dispatch"]["lease_until"], datetime)
    assert after["revision"] == before["revision"] + 1
    assert after["write_nonce"] != before["write_nonce"]
    assert after["schema_version"] == 21
    decoded = store.get(snapshot.case_id)
    assert decoded is not None
    assert decoded.target_executions[0].workflow_dispatch == _authorised_with_first_write()


def test_revision_reused_in_another_history_fails_on_the_nonce(mongo) -> None:
    """CT-17 revision collision: a simulated rollback restores the same revision number."""

    client, database = mongo
    store = _case_store(client, database)
    created = store.create(_snapshot())
    read_a = store.get(created.case_id)
    assert read_a is not None
    # Another history at the same revision number (a rollback or crash loss).
    other = store._encode(  # noqa: SLF001
        read_a.model_copy(update={"write_nonce": "9" * 32, "demo_scenario": "other"})
    )
    client[database][CASES].replace_one({"_id": other["_id"]}, other)
    with pytest.raises(PersistenceConflictError):
        store.replace(
            read_a.model_copy(update={"demo_scenario": "stale"}),
            expected_revision=read_a.revision,
            expected_nonce=read_a.write_nonce,
        )
    stored = client[database][CASES].find_one({"_id": other["_id"]})
    assert stored is not None and stored["demo_scenario"] == "other"
    with pytest.raises(PersistenceConflictError):
        store.delete(
            read_a.case_id, expected_revision=read_a.revision, expected_nonce=read_a.write_nonce
        )


def test_legacy_schema_20_document_is_adopted_by_its_first_writer(mongo) -> None:
    client, database = mongo
    store = _case_store(client, database)
    snapshot = _snapshot()
    raw = store._encode(snapshot)  # noqa: SLF001
    raw["schema_version"] = 20
    client[database][CASES].insert_one(raw)
    MongoDemoScenarioRepository(store).set(snapshot.case_id, "adopted")
    stored = client[database][CASES].find_one({"_id": raw["_id"]})
    assert stored is not None
    assert stored["schema_version"] == 21 and len(stored["write_nonce"]) == 32


def test_definition_writer_preserves_top_level_fields_and_refuses_ungoverned_appends(
    mongo,
) -> None:
    client, database = mongo
    store = MongoWorkflowStore(
        client, database=database, definitions_collection=DEFINITIONS,
        runs_collection="clm_workflow_runs",
    )
    store.initialize()
    repository = MongoWorkflowDefinitionRepository(store)
    created = repository.create(_definition())
    collection = client[database][DEFINITIONS]
    collection.update_one(
        {"_id": created.workflow_id},
        {"$set": {"active_version": 0, "latest_version": 0, "dispatch_authorisation_seq": 7}},
    )
    current = repository.get(created.workflow_id)
    assert current is not None and current.write_nonce == created.write_nonce
    drafted = repository.update(
        current.model_copy(update={"revision": 2, "updated_at": datetime.now(UTC)}),
        expected_revision=1,
    )
    raw = collection.find_one({"_id": created.workflow_id})
    assert raw is not None
    assert (raw["active_version"], raw["latest_version"], raw["dispatch_authorisation_seq"]) == (
        0, 0, 7,
    )
    assert raw["write_nonce"] == drafted.write_nonce != created.write_nonce
    with pytest.raises(PersistenceConflictError):
        repository.update(
            current.model_copy(update={"revision": 3}), expected_revision=2
        )  # stale nonce from the first read


def test_reverse_migration_on_a_disposable_database(mongo) -> None:
    client, database = mongo
    store = _case_store(client, database)
    marked = store._encode(_writer_release_snapshot())  # noqa: SLF001
    client[database][CASES].insert_one(marked)
    codec = object.__new__(MongoCaseStore)
    cases, definitions = client[database][CASES], client[database][DEFINITIONS]
    plan = plan_reverse_migration(
        cases, definitions, decode_legacy_case=codec._decode  # noqa: SLF001
    )
    assert [item.reason for item in plan.refusals] == ["DISPATCH_WRITE_MARKER_NOT_FINALISED"]
    stored = cases.find_one({"_id": marked["_id"]})
    assert stored is not None and stored["target_executions"][0]["workflow_dispatch"]["token"] == (
        TOKEN
    )

    cases.delete_one({"_id": marked["_id"]})
    plain = store.create(_snapshot())
    plan = plan_reverse_migration(
        cases, definitions, decode_legacy_case=codec._decode  # noqa: SLF001
    )
    assert not plan.refused
    assert apply_reverse_migration(plan, cases, definitions) == {"cases": 1, "definitions": 0}
    reverted = cases.find_one({"_id": str(plain.case_id)})
    assert reverted is not None
    assert reverted["schema_version"] == 20 and "write_nonce" not in reverted
    again = plan_reverse_migration(
        cases, definitions, decode_legacy_case=codec._decode  # noqa: SLF001
    )
    assert again.cases == [] and again.already_reverted_cases == 1
