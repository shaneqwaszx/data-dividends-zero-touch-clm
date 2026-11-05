"""D-123 physical MongoDB proof for workflow definitions and runs.

Opt-in like every ``*_real_mongo`` suite: it runs only when ``PHASE12_MONGO_URI`` is set.
Each test uses a newly generated allowlisted database that is dropped afterwards.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)

from app.domain.workflows import WorkflowDefinition, WorkflowRun
from app.persistence.errors import PersistenceConflictError
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowRunRepository,
    MongoWorkflowStore,
)

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
NOW = datetime(2030, 1, 1, tzinfo=UTC)


@pytest.fixture
def store() -> Iterator[MongoWorkflowStore]:
    database = generate_ephemeral_mongo_database("p12")
    client: MongoClient = MongoClient(MONGO_URI)
    instance = MongoWorkflowStore(
        client,
        database=database,
        definitions_collection="clm_workflow_definitions",
        runs_collection="clm_workflow_runs",
    )
    instance.initialize()
    try:
        yield instance
    finally:
        cleanup_ephemeral_mongo_database(client, database)
        client.close()


def definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="refresh",
        name="Refresh",
        use_case="Case refresh",
        country="Singapore",
        created_at=NOW,
        updated_at=NOW,
    )


def run(case_id, revision: int = 1) -> WorkflowRun:
    return WorkflowRun(
        run_id=uuid4(),
        case_id=case_id,
        workflow_id="refresh",
        workflow_name="Refresh",
        use_case="Case refresh",
        workflow_version=1,
        stages=(),
        revision=revision,
        created_at=NOW,
        updated_at=NOW,
    )


def test_definition_create_is_insert_only_and_update_is_revision_guarded(store) -> None:
    repository = MongoWorkflowDefinitionRepository(store)
    created = repository.create(definition())
    with pytest.raises(PersistenceConflictError):
        repository.create(definition())
    updated = created.model_copy(update={"revision": 2, "name": "Renamed"})
    repository.update(updated, expected_revision=1)
    assert repository.get("refresh") == updated
    with pytest.raises(PersistenceConflictError):
        repository.update(updated, expected_revision=1)


def test_a_deleted_run_is_not_resurrected_by_a_stale_writer(store) -> None:
    repository = MongoWorkflowRunRepository(store)
    case_id = uuid4()
    created = repository.create(run(case_id))
    assert repository.list_for_case(case_id) == [created]
    assert repository.list_for_workflow("refresh") == [created]
    repository.delete_for_case(case_id)
    with pytest.raises(PersistenceConflictError):
        repository.update(created.model_copy(update={"revision": 2}), expected_revision=1)
    assert repository.list_for_case(case_id) == []
