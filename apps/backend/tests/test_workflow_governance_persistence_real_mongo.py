"""ADR-017 P2-1 governance persistence on a physical MongoDB (opt-in; integrator-run).

Owner decision D-11: every test runs as an authenticated **readWrite-only** user created
on a newly generated, allowlisted disposable database (never ``clm_poc``), with the same
server and transport options as ``PHASE12_MONGO_URI``; the user is dropped and the
database removed afterwards. Runs only when ``PHASE12_MONGO_URI`` is set. The URI and
the generated credentials are never printed.
"""

from __future__ import annotations

import contextlib
import os
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from pymongo.uri_parser import parse_uri
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from test_p2_1_migration import Seeder, p2_0_raw
from test_workflow_governance_repository import (
    WID,
    approve,
    born,
    payload,
    pending_proposal,
)

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
from app.persistence.workflow_governance_store import (
    ColdDuplicateKeyError,
    ColdHistoryIntegrityError,
    GovernanceHistoryRewriteError,
    GovernedDefinition,
    archive_record,
    dict_hash,
)

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)
_CREDENTIAL_OPTIONS = {"authsource", "authmechanism", "authmechanismproperties"}


def _client_as(user: str, password: str, database: str) -> MongoClient[dict[str, Any]]:
    """The same server and transport options as ``PHASE12_MONGO_URI``, authenticated as
    ``user`` (credentials replaced)."""

    assert MONGO_URI is not None
    parsed = parse_uri(MONGO_URI)
    options = {
        key: value
        for key, value in parsed["options"].items()
        if key.lower() not in _CREDENTIAL_OPTIONS
    }
    return MongoClient(
        [f"{host}:{port}" for host, port in parsed["nodelist"]],
        username=user,
        password=password,
        authSource=database,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
        **options,
    )


@pytest.fixture
def store() -> Iterator[MongoWorkflowStore]:
    name = require_ephemeral_mongo_database(generate_ephemeral_mongo_database("p12"))
    admin: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    user, password = f"wfg_{secrets.token_hex(6)}", secrets.token_urlsafe(24)
    client = None
    try:
        admin[name].command(
            "createUser", user, pwd=password, roles=[{"role": "readWrite", "db": name}]
        )
        client = _client_as(user, password, name)
        instance = MongoWorkflowStore(
            client,
            database=name,
            definitions_collection="clm_workflow_definitions",
            runs_collection="clm_workflow_runs",
        )
        instance.initialize()  # as readWrite: includes the cold indexes
        yield instance
    finally:
        if client is not None:
            client.close()
        with contextlib.suppress(OperationFailure):
            admin[name].command("dropUser", user)
        cleanup_ephemeral_mongo_database(admin, name)
        assert name not in admin.list_database_names()
        admin.close()


def _submit(repository: MongoWorkflowDefinitionRepository, current: Any, number: int) -> Any:
    """Store a PENDING_APPROVAL open proposal; a decision may only end that proposal."""

    return repository.write_governance(
        current.definition.model_copy(update={"revision": current.definition.revision + 1}),
        current.governance.model_copy(update={"open_proposal": pending_proposal(current, number)}),
        expected_revision=current.definition.revision,
    )


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
        current = _submit(repository, current, number)
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
    (first,) = [item for item in store.cold.find(OutboxCollection.EVENTS, f"{WID}:1")][:1]
    with pytest.raises(ColdDuplicateKeyError):  # insert-only: an existing _id never changes
        store.cold.insert(OutboxCollection.EVENTS, first)
    with pytest.raises(ColdHistoryIntegrityError):  # same logical id, different content
        archive_record(
            store.cold,
            **{
                **kwargs,
                "record": {"synthetic": 2},  # type: ignore[arg-type]
                "content_hash": dict_hash({"synthetic": 2}),
            },
        )
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
    assert apply_p2_1_migration(again, store.definitions, store.cold, now=NOW) == 0
    assert store.definitions.find_one({"_id": "refresh"}) == stored


def _two_published(repository: MongoWorkflowDefinitionRepository) -> Any:
    current = repository.create_governed(payload(), born())
    for number in (1, 2):
        current = _submit(repository, current, number)
        definition, governance = approve(current, number)
        current = repository.write_governance(
            definition,
            governance,
            expected_revision=current.definition.revision,
            active_version=number,
            latest_version=number,
        )
    return current


@pytest.mark.parametrize("latest", [1, 2, 4])  # QG P1-1: decreasing, equal, skipping
def test_physical_latest_version_only_rises_by_one(store: MongoWorkflowStore, latest: int) -> None:
    repository = MongoWorkflowDefinitionRepository(store)
    current = _two_published(repository)
    forged = current.definition.model_copy(update={"stored_active_version": 0, "latest_version": 0})
    definition, governance = approve(GovernedDefinition(forged, current.governance), 3)
    extra = definition.versions[-1].model_copy(update={"version": latest})
    definition = definition.model_copy(update={"versions": (*current.definition.versions, extra)})
    with pytest.raises(ValueError):
        repository.write_governance(
            definition,
            governance,
            expected_revision=current.definition.revision,
            active_version=latest,
            latest_version=latest,
        )
    stored = store.definitions.find_one({"_id": WID})
    assert stored is not None and stored["latest_version"] == 2


def test_physical_write_never_drops_unarchived_history(store: MongoWorkflowStore) -> None:
    """QG P1-2: dropping the outbox, unarchived events or the pinned latest version is
    refused before any write; the latest version stays hot and dispatchable."""

    repository = MongoWorkflowDefinitionRepository(store)
    current = _two_published(repository)
    bumped = current.definition.model_copy(update={"revision": current.definition.revision + 1})
    attempts = [
        (bumped, current.governance.model_copy(update={"outbox": ()})),
        (bumped, current.governance.model_copy(update={"governance_events": ()})),
        (bumped.model_copy(update={"versions": bumped.versions[:1]}), current.governance),
    ]
    for definition, governance in attempts:
        with pytest.raises(GovernanceHistoryRewriteError):
            repository.write_governance(
                definition, governance, expected_revision=current.definition.revision
            )
    assert repository.get_governed(WID) == current
    assert repository.get_version(WID, 2) is not None


def test_physical_deactivation_then_reactivation(store: MongoWorkflowStore) -> None:
    """M2 (ADR-017 4, CC-5): deactivation sets active 0 and keeps latest, versions and
    baseline; dispatch is refused; reactivation publishes latest + 1; verification stays
    clean throughout."""

    from types import SimpleNamespace

    from test_workflow_governance_repository import _deactivation, _submit_deactivation

    repository = MongoWorkflowDefinitionRepository(store)
    holder: Any = SimpleNamespace(repository=repository)
    current = _two_published(repository)
    current = _submit_deactivation(holder, current)
    definition, governance = _deactivation(current)
    deactivated = repository.write_governance(
        definition,
        governance,
        expected_revision=current.definition.revision,
        active_version=0,
        deactivate=True,
    )
    stored = store.definitions.find_one({"_id": WID})
    assert stored is not None
    assert (stored["active_version"], stored["latest_version"]) == (0, 2)
    assert deactivated.governance.required_baseline == current.governance.required_baseline
    assert not repository.authorise_dispatch(WID, 2)
    repository.drain_outbox(WID, now=NOW)
    assert repository.verify_dispatch_state() == []
    assert repository.verify_governance_state() == []
    current = _submit(repository, repository.get_governed(WID), 3)
    definition, governance = approve(current, 3)
    repository.write_governance(
        definition,
        governance,
        expected_revision=current.definition.revision,
        active_version=3,
        latest_version=3,
    )
    assert repository.authorise_dispatch(WID, 3)
    repository.drain_outbox(WID, now=NOW)
    assert repository.verify_governance_state() == []
