"""ADR-017 section 5: cold store, archiver (fallback mode) and compaction.

Memory-backed and dict-backed fakes only (no Mongo server, no mongomock). The fake
collection below is shared by the other P2-1 persistence tests.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from pymongo.errors import DuplicateKeyError, WTimeoutError

from app.domain.workflow_governance import (
    MAX_HOT_EVENTS,
    ColdRecord,
    GovernanceEvent,
    GovernanceEventKind,
    MigrationMarker,
    OutboxCollection,
    WorkflowGovernanceState,
    event_logical_id,
    record_content_hash,
)
from app.domain.workflows import WorkflowDefinition, WorkflowVersion
from app.persistence.errors import PersistenceOutcomeAmbiguousError
from app.persistence.workflow_governance_store import (
    ColdDuplicateKeyError,
    ColdHistoryIntegrityError,
    InMemoryColdHistoryStore,
    MongoColdHistoryStore,
    archive_record,
    compact_history,
    dict_hash,
    drain_outbox_entries,
    encode_governance_fields,
    event_record,
    outbox_for_event,
    outbox_for_version,
    version_record,
)

NOW = datetime(2031, 3, 1, 9, 0, tzinfo=UTC)


# --- dict-backed pymongo doubles ------------------------------------------------------


def _get(document: Any, path: str) -> tuple[bool, Any]:
    current = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(document, item) for item in expected):
                return False
            continue
        present, actual = _get(document, key)
        if isinstance(expected, dict) and any(op.startswith("$") for op in expected):
            for op, value in expected.items():
                if op == "$exists" and present != value:
                    return False
                if op == "$gte" and not (present and actual >= value):
                    return False
                if op == "$ne" and present and actual == value:
                    return False
        elif not present or actual != expected:
            return False
    return True


class FakeCollection:
    """Applies filters, ``$set`` and ``$inc``; records every write and its durability."""

    def __init__(
        self,
        documents: dict[str, dict[str, Any]] | None = None,
        log: list[tuple[str, bool, Any]] | None = None,
        durable: bool = False,
        faults: dict[str, list[BaseException]] | None = None,
    ) -> None:
        self.documents = {} if documents is None else documents
        self.log = [] if log is None else log
        self.durable = durable
        self.faults = {} if faults is None else faults
        self.indexes: list[str] = []

    def with_options(self, **kwargs: Any) -> FakeCollection:
        concern = kwargs.get("write_concern")
        durable = bool(concern and concern.document.get("j") and concern.document["w"])
        view = FakeCollection(self.documents, self.log, durable, self.faults)
        view.indexes = self.indexes
        return view

    def _fault(self, operation: str) -> None:
        queue = self.faults.get(operation)
        if queue:
            raise queue.pop(0)

    @property
    def writes(self) -> list[tuple[str, bool, Any]]:
        return self.log

    def create_index(self, keys: Any, name: str) -> str:
        if name not in self.indexes:
            self.indexes.append(name)
        return name

    def find(self, query: dict[str, Any] | None = None, *_: Any) -> list[dict[str, Any]]:
        self._fault("find")
        return [
            copy.deepcopy(item) for item in self.documents.values() if _matches(item, query or {})
        ]

    def find_one(self, query: dict[str, Any], *_: Any) -> dict[str, Any] | None:
        found = self.find(query)
        return found[0] if found else None

    def insert_one(self, document: dict[str, Any]) -> Any:
        self.log.append(("insert_one", self.durable, copy.deepcopy(document)))
        self._fault("insert_one")
        if document["_id"] in self.documents:
            raise DuplicateKeyError("duplicate", 11000)
        self.documents[document["_id"]] = copy.deepcopy(document)
        self._fault("insert_one_after")
        return SimpleNamespace(acknowledged=True, inserted_id=document["_id"])

    def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> Any:
        self.log.append(("update_one", self.durable, copy.deepcopy((query, update))))
        self._fault("update_one")
        for key, document in self.documents.items():
            if _matches(document, query):
                changed = copy.deepcopy(document)
                for field, value in update.get("$set", {}).items():
                    changed[field] = copy.deepcopy(value)
                for field, value in update.get("$inc", {}).items():
                    changed[field] = changed.get(field, 0) + value
                self.documents[key] = changed
                return SimpleNamespace(acknowledged=True, matched_count=1, modified_count=1)
        return SimpleNamespace(acknowledged=True, matched_count=0, modified_count=0)


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


class FakeClient:
    def __init__(self) -> None:
        self.databases: dict[str, FakeDatabase] = {}
        self.admin = SimpleNamespace(command=lambda _name: {"ok": 1})
        self.closed = False

    def __getitem__(self, name: str) -> FakeDatabase:
        return self.databases.setdefault(name, FakeDatabase())

    def close(self) -> None:
        self.closed = True


# --- fixtures -------------------------------------------------------------------------


def version(number: int, label: str = "Stage") -> WorkflowVersion:
    return WorkflowVersion(
        version=number,
        stages=(),
        activated_at=NOW + timedelta(minutes=number),
        activated_by=f"director-{label.lower()}",
    )


def event(sequence: int, *, archived: bool = False) -> GovernanceEvent:
    return GovernanceEvent(
        sequence=sequence,
        occurred_at=NOW + timedelta(seconds=sequence),
        actor_id="hr-author",
        kind=GovernanceEventKind.PROPOSAL_EDITED,
        summary=f"Edited {sequence}",
        archived=archived,
    )


def definition(*versions: WorkflowVersion) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="refresh",
        name="Refresh",
        use_case="Case refresh",
        country="Singapore",
        versions=versions,
        created_at=NOW,
        updated_at=NOW,
    )


MARKER = MigrationMarker(
    migrated_at=NOW, tool_version="test", legacy_versions=0, legacy_draft_converted=False
)


def cold_record(logical_id: str, record: dict[str, Any], attempt: int = 0) -> ColdRecord:
    return ColdRecord(
        logical_id=logical_id,
        attempt=attempt,
        content_hash=dict_hash(record),
        workflow_id="refresh",
        archived_at=NOW,
        record=record,
    )


def mongo_cold() -> tuple[MongoColdHistoryStore, FakeDatabase]:
    database = FakeDatabase()
    return MongoColdHistoryStore(database), database  # type: ignore[arg-type]


@pytest.fixture(params=["memory", "mongo"])
def cold(request: pytest.FixtureRequest) -> Any:
    if request.param == "memory":
        return InMemoryColdHistoryStore()
    return mongo_cold()[0]


# --- cold store -----------------------------------------------------------------------


def test_cold_store_is_insert_only_and_reads_by_logical_id(cold: Any) -> None:
    record = version_record(version(1))
    first = cold_record("refresh:1", record)
    cold.insert(OutboxCollection.VERSIONS, first)
    with pytest.raises(ColdDuplicateKeyError):
        cold.insert(OutboxCollection.VERSIONS, first)
    cold.insert(OutboxCollection.VERSIONS, cold_record("refresh:1", record, attempt=1))
    found = cold.find(OutboxCollection.VERSIONS, "refresh:1")
    assert [item.document_id for item in found] == ["refresh:1#0", "refresh:1#1"]
    assert cold.find(OutboxCollection.PROPOSALS, "refresh:1") == []
    assert [item.attempt for item in cold.list_for_workflow(OutboxCollection.VERSIONS, "refresh")]
    assert cold.confirm(OutboxCollection.VERSIONS, "refresh:1#0", first.content_hash)
    assert not cold.confirm(OutboxCollection.VERSIONS, "refresh:1#0", "0" * 64)


def test_mongo_cold_store_uses_the_durable_rule_and_idempotent_indexes() -> None:
    store, database = mongo_cold()
    store.initialize()
    store.initialize()
    for name in ("workflow_versions", "workflow_proposals", "workflow_governance_events"):
        assert database[name].indexes == ["cold_logical_id", "cold_workflow_id"]
    store.insert(OutboxCollection.EVENTS, cold_record("refresh:1", {"a": 1}))
    assert database["workflow_governance_events"].log[-1][:2] == ("insert_one", True)
    store.confirm(OutboxCollection.EVENTS, "refresh:1#0", dict_hash({"a": 1}))
    operation, durable, (query, update) = database["workflow_governance_events"].log[-1]
    assert (operation, durable) == ("update_one", True)
    assert set(query) == {"_id", "content_hash"}
    assert update == {"$inc": {"archive_confirmations": 1}}


def test_mongo_cold_insert_timeout_is_ambiguous_never_done() -> None:
    store, database = mongo_cold()
    database["workflow_versions"].faults["insert_one_after"] = [WTimeoutError("timeout")]
    with pytest.raises(PersistenceOutcomeAmbiguousError):
        store.insert(OutboxCollection.VERSIONS, cold_record("refresh:1", {"a": 1}))


def test_tampered_cold_record_is_an_integrity_failure() -> None:
    store, database = mongo_cold()
    store.insert(OutboxCollection.VERSIONS, cold_record("refresh:1", {"a": 1}))
    database["workflow_versions"].documents["refresh:1#0"]["record"] = {"a": 2}
    with pytest.raises(ColdHistoryIntegrityError):
        store.find(OutboxCollection.VERSIONS, "refresh:1")


# --- archiver -------------------------------------------------------------------------


def _archive(cold: Any, record: dict[str, Any], **kwargs: Any) -> int:
    return archive_record(
        cold,
        collection=OutboxCollection.VERSIONS,
        logical_id="refresh:1",
        content_hash=dict_hash(record),
        workflow_id="refresh",
        record=record,
        now=NOW,
        **kwargs,
    )


def test_fallback_mode_inserts_a_fresh_suffix_on_an_identical_duplicate(cold: Any) -> None:
    record = {"a": 1}
    assert _archive(cold, record) == 0
    # The first insert's acknowledgement is unknown to a later drain: never a confirmation.
    assert _archive(cold, record) == 1
    assert [item.attempt for item in cold.find(OutboxCollection.VERSIONS, "refresh:1")] == [0, 1]


def test_duplicate_with_a_different_hash_fails_closed(cold: Any) -> None:
    _archive(cold, {"a": 1})
    with pytest.raises(ColdHistoryIntegrityError):
        _archive(cold, {"a": 2})


def test_hot_record_must_match_its_outbox_hash(cold: Any) -> None:
    with pytest.raises(ColdHistoryIntegrityError):
        archive_record(
            cold,
            collection=OutboxCollection.VERSIONS,
            logical_id="refresh:1",
            content_hash="0" * 64,
            workflow_id="refresh",
            record={"a": 1},
            now=NOW,
        )


def test_confirming_mode_is_explicit_and_confirms_with_inc(cold: Any) -> None:
    record = {"a": 1}
    _archive(cold, record)
    assert _archive(cold, record, confirming_writes=True) == 0
    (stored,) = cold.find(OutboxCollection.VERSIONS, "refresh:1")
    assert stored.archive_confirmations == 1


def _state_with_outbox(definition_: WorkflowDefinition, *events: GovernanceEvent) -> Any:
    outbox = tuple(outbox_for_event("refresh", item) for item in events)
    outbox += tuple(outbox_for_version("refresh", item) for item in definition_.versions)
    return WorkflowGovernanceState(
        migration_marker=MARKER,
        governance_events=events,
        outbox=outbox,
        governance_sequence=len(events),
    )


def test_drain_removes_only_durably_acknowledged_entries() -> None:
    store, database = mongo_cold()
    current = definition(version(1))
    state = _state_with_outbox(current, event(1), event(2))
    # The second event's insert is applied but its acknowledgement times out.
    database["workflow_governance_events"].faults["insert_one_after"] = [
        PersistenceOutcomeAmbiguousError()
    ]
    first = drain_outbox_entries(current, state, store, now=NOW)
    assert isinstance(first.error, PersistenceOutcomeAmbiguousError)
    assert first.archived == ()
    assert first.governance.outbox == state.outbox
    # A read-back would show the record; it never counts. The next drain inserts #1.
    assert [item.attempt for item in store.find(OutboxCollection.EVENTS, "refresh:1")] == [0]
    second = drain_outbox_entries(current, state, store, now=NOW)
    assert second.error is None and second.governance.outbox == ()
    assert [item.attempt for item in store.find(OutboxCollection.EVENTS, "refresh:1")] == [0, 1]
    assert all(item.archived for item in second.governance.governance_events)


def test_drain_commits_the_acknowledged_prefix_and_keeps_the_rest() -> None:
    store = InMemoryColdHistoryStore()
    current = definition()
    events = (event(1), event(2), event(3))
    state = _state_with_outbox(current, *events)
    # Plant a conflicting cold copy for event 2: integrity failure, governance fails closed.
    other = event_record(event(2).model_copy(update={"summary": "Different"}))
    store.insert(OutboxCollection.EVENTS, cold_record(event_logical_id("refresh", 2), other))
    result = drain_outbox_entries(current, state, store, now=NOW)
    assert isinstance(result.error, ColdHistoryIntegrityError)
    assert [item.logical_id for item in result.archived] == ["refresh:1"]
    assert [item.logical_id for item in result.governance.outbox] == ["refresh:2", "refresh:3"]
    assert [item.archived for item in result.governance.governance_events] == [True, False, False]


def test_outbox_reference_to_a_missing_hot_record_fails_closed() -> None:
    current = definition()
    state = _state_with_outbox(current, event(1)).model_copy(update={"governance_events": ()})
    result = drain_outbox_entries(current, state, InMemoryColdHistoryStore(), now=NOW)
    assert isinstance(result.error, ColdHistoryIntegrityError)
    assert result.governance.outbox == state.outbox


# --- compaction -----------------------------------------------------------------------


def test_compaction_moves_only_acknowledged_items_and_never_truncates() -> None:
    store = InMemoryColdHistoryStore()
    current = definition()
    total = 300  # past the old silent 256-event truncation
    events = [event(number) for number in range(1, total + 1)]
    archived = []
    for item in events[:250]:
        archive_record(
            store,
            collection=OutboxCollection.EVENTS,
            logical_id=event_logical_id("refresh", item.sequence),
            content_hash=dict_hash(event_record(item)),
            workflow_id="refresh",
            record=event_record(item),
            now=NOW,
        )
        archived.append(item.model_copy(update={"archived": True}))
    pending = events[250:]
    state = WorkflowGovernanceState(
        migration_marker=MARKER,
        governance_events=(*archived, *pending),
        outbox=tuple(outbox_for_event("refresh", item) for item in pending[:32]),
        governance_sequence=total,
    )
    _, compacted = compact_history(current, state, store, active_version=0, latest_version=0)
    kept = compacted.governance_events
    # Every unarchived event stays hot, whatever the count; archived ones move out.
    assert {item.sequence for item in pending} <= {item.sequence for item in kept}
    assert len(kept) == max(MAX_HOT_EVENTS, len(pending))
    assert all(item.archived for item in kept if item.sequence <= 250)
    # Nothing is lost: every event is hot or cold.
    cold_ids = {item.logical_id for item in store.all_records(OutboxCollection.EVENTS)}
    hot_ids = {event_logical_id("refresh", item.sequence) for item in kept}
    assert cold_ids | hot_ids == {event_logical_id("refresh", n) for n in range(1, total + 1)}


def test_compaction_never_moves_pinned_or_unarchived_versions() -> None:
    store = InMemoryColdHistoryStore()
    versions = tuple(version(number) for number in range(1, 21))
    current = definition(*versions)
    for item in versions[:-2]:  # 1..18 archived; 19 has no cold copy; 20 is active
        archive_record(
            store,
            collection=OutboxCollection.VERSIONS,
            logical_id=f"refresh:{item.version}",
            content_hash=record_content_hash(item),
            workflow_id="refresh",
            record=version_record(item),
            now=NOW,
        )
    referenced = outbox_for_version("refresh", versions[0])
    state = WorkflowGovernanceState(migration_marker=MARKER, outbox=(referenced,))
    compacted, _ = compact_history(current, state, store, active_version=20, latest_version=20)
    numbers = [item.version for item in compacted.versions]
    assert len(numbers) == 16
    assert 20 in numbers and 19 in numbers  # active, and not provably archived
    assert 1 in numbers  # outbox-referenced
    assert numbers == sorted(numbers)


def test_compaction_is_a_no_op_below_the_thresholds() -> None:
    current = definition(version(1))
    state = WorkflowGovernanceState(migration_marker=MARKER)
    assert compact_history(
        current, state, InMemoryColdHistoryStore(), active_version=1, latest_version=1
    ) == (current, state)


def test_unmigrated_default_state_stores_no_fields_and_marker_is_last() -> None:
    assert encode_governance_fields(WorkflowGovernanceState()) == {}
    fields = encode_governance_fields(WorkflowGovernanceState(migration_marker=MARKER))
    assert list(fields)[-1] == "p2_1_migration_marker"
