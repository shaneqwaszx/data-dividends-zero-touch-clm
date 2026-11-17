"""ADR-017 P2-0 reader release: schema 21 round-trip, nonce guards and the reverse migration.

Memory and codec level only (no Mongo server). The physical counterpart is
``test_adr017_reader_release_real_mongo.py``.
"""

from __future__ import annotations

import ast
import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from test_phase12_persistence import _provider_bound_snapshot

from app.domain.target_submission import (
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    GoldTierProviderMode,
    WorkflowDispatch,
    WorkflowDispatchFirstWrite,
    WorkflowDispatchState,
)
from app.domain.workflows import WorkflowDefinition
from app.persistence.adr017_migrations import (
    ReverseMigrationRefusedError,
    apply_reverse_migration,
    plan_reverse_migration,
)
from app.persistence.errors import PersistenceConflictError, PersistenceDataInvalidError
from app.persistence.models import CASE_SNAPSHOT_SCHEMA_VERSION, DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore, write_nonce_filter
from app.persistence.mongo_workflow_store import MongoWorkflowDefinitionRepository
from app.services.target_execution_repository import (
    InMemoryTargetExecutionRepository,
    TargetExecutionRepositoryConflictError,
)
from app.services.workflow_repository import InMemoryWorkflowDefinitionRepository

BACKEND = Path(__file__).resolve().parents[1]
CODEC = object.__new__(MongoCaseStore)
# BSON dates carry milliseconds, so fixtures use whole milliseconds to compare exactly.
LEASE = datetime(2031, 1, 1, 12, 0, 0, 123000, tzinfo=UTC)
TOKEN = "a" * 32
RECEIPT = "b" * 32


def _snapshot() -> DurableCaseSnapshot:
    return _provider_bound_snapshot(
        plan_mode=GoldTierProviderMode.MOCK, execution_mode=GoldTierProviderMode.MOCK
    )


def _authorised_with_first_write() -> WorkflowDispatch:
    return WorkflowDispatch(
        state=WorkflowDispatchState.AUTHORISED,
        token=TOKEN,
        version=3,
        lease_until=LEASE,
        d3_at=LEASE - timedelta(seconds=30),
        receipt=RECEIPT,
        first_write=WorkflowDispatchFirstWrite(
            operation=GoldTierOperationMarker.SHELL, version=3, token=TOKEN, receipt=RECEIPT
        ),
    )


def _writer_release_snapshot() -> DurableCaseSnapshot:
    """A schema-21 document as the writer release leaves it after D5."""

    snapshot = _snapshot()
    entry = snapshot.target_executions[0].model_copy(
        update={
            "attempted_operations": (GoldTierOperationMarker.SEARCH, GoldTierOperationMarker.SHELL),
            "completed_operations": (GoldTierOperationMarker.SEARCH,),
            "resolved_operations": (GoldTierOperationMarker.SEARCH,),
            "workflow_dispatch": _authorised_with_first_write(),
        }
    )
    return snapshot.model_copy(
        update={"target_executions": (entry,), "write_nonce": "c" * 32}, deep=True
    )


# --- domain shape -----------------------------------------------------------------------


def test_schema_is_21_and_dispatch_claim_is_backend_only() -> None:
    assert CASE_SNAPSHOT_SCHEMA_VERSION == 21
    entry = _writer_release_snapshot().target_executions[0]
    assert "workflow_dispatch" not in entry.model_dump()
    assert "write_nonce" not in _snapshot().model_dump()


def test_claim_shape_rules() -> None:
    with pytest.raises(ValueError):
        WorkflowDispatch(
            state=WorkflowDispatchState.TENTATIVE, token=TOKEN, version=1, lease_until=LEASE,
            d3_at=LEASE,
        )
    with pytest.raises(ValueError):
        WorkflowDispatch(
            state=WorkflowDispatchState.AUTHORISED, token=TOKEN, version=1, lease_until=LEASE
        )
    with pytest.raises(ValueError):
        WorkflowDispatchFirstWrite(
            operation=GoldTierOperationMarker.SEARCH, version=1, token=TOKEN, receipt=RECEIPT
        )
    naive = WorkflowDispatch.model_validate(
        {"state": "TENTATIVE", "token": TOKEN, "version": 1,
         "lease_until": LEASE.replace(tzinfo=None)}
    )
    assert naive.lease_until == LEASE


def test_first_write_must_be_the_first_attempted_write() -> None:
    snapshot = _snapshot()
    with pytest.raises(ValueError):
        snapshot.target_executions[0].model_validate(
            {
                **snapshot.target_executions[0].model_dump(),
                "attempted_operations": ("SEARCH",),
                "workflow_dispatch": _authorised_with_first_write(),
            }
        )


# --- codec round trip (R3-4) --------------------------------------------------------------


def test_schema_21_round_trips_nonce_and_claim_with_bson_dates() -> None:
    snapshot = _writer_release_snapshot()
    raw = CODEC._encode(snapshot)  # noqa: SLF001
    assert raw["schema_version"] == 21
    assert raw["write_nonce"] == "c" * 32
    claim = raw["target_executions"][0]["workflow_dispatch"]
    assert isinstance(claim["lease_until"], datetime)
    assert isinstance(claim["d3_at"], datetime)
    # Driver round trip: BSON dates come back naive UTC.
    driver_raw = copy.deepcopy(raw)
    driver_claim = driver_raw["target_executions"][0]["workflow_dispatch"]
    driver_claim["lease_until"] = driver_claim["lease_until"].replace(tzinfo=None)
    driver_claim["d3_at"] = driver_claim["d3_at"].replace(tzinfo=None)
    decoded = CODEC._decode(driver_raw)  # noqa: SLF001
    assert decoded.write_nonce == "c" * 32
    assert decoded.target_executions[0].workflow_dispatch == _authorised_with_first_write()
    assert CODEC._encode(decoded) == raw  # noqa: SLF001


def test_absent_fields_are_omitted_not_null() -> None:
    raw = CODEC._encode(_snapshot())  # noqa: SLF001
    assert "write_nonce" not in raw
    assert all("workflow_dispatch" not in entry for entry in raw["target_executions"])


def test_schema_20_reads_into_21_without_nonce() -> None:
    raw = CODEC._encode(_snapshot())  # noqa: SLF001
    raw["schema_version"] = 20
    decoded = CODEC._decode(raw)  # noqa: SLF001
    assert decoded.schema_version == 21
    assert decoded.write_nonce is None


@pytest.mark.parametrize("version", [19, 20])
def test_historical_schema_cannot_carry_adr017_fields(version: int) -> None:
    raw = CODEC._encode(_writer_release_snapshot())  # noqa: SLF001
    raw["schema_version"] = version
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001
    raw.pop("write_nonce")
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001


def test_unknown_claim_field_is_rejected() -> None:
    raw = CODEC._encode(_writer_release_snapshot())  # noqa: SLF001
    raw["target_executions"][0]["workflow_dispatch"]["unexpected"] = 1
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001


# --- case store compare-and-set (R4-4) ---------------------------------------------------


class _RecordingCollection:
    """Applies the store's filter to one stored document; records every write filter."""

    def __init__(self, stored: dict[str, Any]) -> None:
        self.stored = stored
        self.filters: list[dict[str, Any]] = []

    def _matches(self, query: dict[str, Any]) -> bool:
        for key, expected in query.items():
            actual: Any = self.stored
            for part in key.split("."):
                actual = actual.get(part) if isinstance(actual, dict) else None
            present = _path_present(self.stored, key)
            if isinstance(expected, dict) and "$exists" in expected:
                if present != expected["$exists"]:
                    return False
            elif actual != expected:
                return False
        return True

    def replace_one(self, query: dict[str, Any], document: dict[str, Any]) -> Any:
        self.filters.append(query)
        if not self._matches(query):
            return SimpleNamespace(modified_count=0, matched_count=0)
        self.stored = document
        return SimpleNamespace(modified_count=1, matched_count=1)

    def delete_one(self, query: dict[str, Any]) -> Any:
        self.filters.append(query)
        return SimpleNamespace(deleted_count=1 if self._matches(query) else 0)


def _path_present(document: dict[str, Any], key: str) -> bool:
    current: Any = document
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _store_over(raw: dict[str, Any]) -> tuple[MongoCaseStore, _RecordingCollection]:
    store = object.__new__(MongoCaseStore)
    collection = _RecordingCollection(raw)
    store._collection = collection  # noqa: SLF001
    return store, collection


def test_replace_filters_revision_and_nonce_and_sets_a_new_nonce() -> None:
    snapshot = _writer_release_snapshot()
    store, collection = _store_over(CODEC._encode(snapshot))  # noqa: SLF001
    written = store.replace(snapshot, expected_revision=1, expected_nonce="c" * 32)
    query = collection.filters[-1]
    assert query["revision"] == 1 and query["write_nonce"] == "c" * 32
    assert written.write_nonce not in {None, "c" * 32}
    assert written.revision == 2
    # The reader release round-trips the claim it cannot interpret.
    assert written.target_executions[0].workflow_dispatch == _authorised_with_first_write()
    assert collection.stored["target_executions"][0]["workflow_dispatch"]["token"] == TOKEN


def test_first_writer_of_a_legacy_document_matches_an_absent_nonce() -> None:
    snapshot = _snapshot()
    store, collection = _store_over(CODEC._encode(snapshot))  # noqa: SLF001
    written = store.replace(snapshot, expected_revision=1, expected_nonce=None)
    assert collection.filters[-1]["write_nonce"] == {"$exists": False}
    assert written.write_nonce is not None and collection.stored["write_nonce"]


def test_revision_collision_with_a_different_nonce_never_overwrites() -> None:
    """CT-17 / R4-4: a revision reused in another history fails on the nonce."""

    snapshot = _writer_release_snapshot()
    other_history = CODEC._encode(  # noqa: SLF001
        snapshot.model_copy(update={"write_nonce": "d" * 32}, deep=True)
    )
    store, collection = _store_over(other_history)
    with pytest.raises(PersistenceConflictError):
        store.replace(snapshot, expected_revision=1, expected_nonce="c" * 32)
    assert collection.stored == other_history
    with pytest.raises(PersistenceConflictError):
        store.delete(snapshot.case_id, expected_revision=1, expected_nonce="c" * 32)


def test_create_writes_a_fresh_nonce() -> None:
    inserted: list[dict[str, Any]] = []
    store = object.__new__(MongoCaseStore)
    store._collection = SimpleNamespace(insert_one=inserted.append)  # noqa: SLF001
    created = store.create(_snapshot())
    assert created.write_nonce is not None and inserted[0]["write_nonce"] == created.write_nonce


def test_write_nonce_filter_shapes() -> None:
    assert write_nonce_filter(None) == {"write_nonce": {"$exists": False}}
    assert write_nonce_filter("e" * 32) == {"write_nonce": "e" * 32}


# --- repository-wide writer guard (ADR-017 3.2; CT-20 writer guards) ----------------------

_GUARDED_MODULES = (
    BACKEND / "app/persistence/mongo_case_store.py",
    BACKEND / "app/persistence/mongo_workflow_store.py",
)
_COLLECTION_WRITES = {"replace_one", "update_one", "delete_one", "find_one_and_update",
                      "find_one_and_replace", "find_one_and_delete", "update_many",
                      "delete_many", "replace_many"}
# Writers of documents ADR-017 does not guard: workflow runs (their own revision CAS).
_UNGUARDED_CLASSES = {"MongoWorkflowRunRepository"}


def _filter_keys(node: ast.AST) -> tuple[set[str], set[str]]:
    keys: set[str] = set()
    unpacked: set[str] = set()
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=True):
            if key is None and isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                unpacked.add(value.func.id)
            elif isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
    return keys, unpacked


def _d3_exemption(method: ast.FunctionDef, call: ast.Call) -> bool:
    """ADR-017 3.2: D3 is the one writer without revision/nonce. It may modify only
    ``dispatch_authorisation_seq`` (never the payload, revision or nonce)."""

    if method.name != "authorise_dispatch" or len(call.args) < 2:
        return False
    return ast.unparse(call.args[1]) == "{'$inc': {'dispatch_authorisation_seq': 1}}"


def test_every_case_and_definition_writer_filters_revision_and_nonce() -> None:
    offences: list[str] = []
    for module in _GUARDED_MODULES:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for cls in (item for item in tree.body if isinstance(item, ast.ClassDef)):
            if cls.name in _UNGUARDED_CLASSES:
                continue
            for method in (node for node in cls.body if isinstance(node, ast.FunctionDef)):
                for call in (node for node in ast.walk(method) if isinstance(node, ast.Call)):
                    func = call.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr in _COLLECTION_WRITES
                        and _d3_exemption(method, call)
                    ):
                        call.func = ast.Name(id="_exempt_d3")  # checked, then skipped
            for call in (node for node in ast.walk(cls) if isinstance(node, ast.Call)):
                func = call.func
                if not isinstance(func, ast.Attribute) or func.attr not in _COLLECTION_WRITES:
                    continue
                keys, unpacked = _filter_keys(call.args[0]) if call.args else (set(), set())
                if "revision" not in keys or not unpacked & {
                    "write_nonce_filter", "_nonce_filter"
                }:
                    offences.append(f"{module.name}:{call.lineno} {cls.name}.{func.attr}")
                if func.attr in {"update_many", "delete_many", "replace_many"}:
                    offences.append(f"{module.name}:{call.lineno} multi-document write")
    assert offences == []


def test_every_fence_write_filters_revision_and_nonce() -> None:
    """Writer release: every fence query starts from ``_base_filter`` (revision + nonce),
    and ``_step`` is the only collection write in the fence ledger."""

    from app.persistence.fence_store import _base_filter

    assert _base_filter(uuid4_value(), 4, None) == {
        "_id": str(uuid4_value()), "revision": 4, "write_nonce": {"$exists": False}
    }
    tree = ast.parse((BACKEND / "app/persistence/fence_store.py").read_text(encoding="utf-8"))
    ledger = next(
        item for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == "MongoFenceLedger"
    )
    writers = [
        method.name for method in ledger.body if isinstance(method, ast.FunctionDef)
        for call in ast.walk(method)
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
        and call.func.attr in _COLLECTION_WRITES
    ]
    assert writers == ["_step"]
    for method in (item for item in ledger.body if isinstance(item, ast.FunctionDef)):
        queries = [
            node.value for node in ast.walk(method)
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "query" for t in node.targets)
        ]
        for query in queries:
            _, unpacked = _filter_keys(query)
            assert "_base_filter" in unpacked, method.name
        if method.name in {"claim", "authorise", "first_write", "clear_unattempted_claim"}:
            assert queries, method.name


_FIXED_UUID = "00000000-0000-4000-8000-000000000001"


def uuid4_value() -> Any:
    from uuid import UUID

    return UUID(_FIXED_UUID)


def test_every_store_write_call_passes_the_nonce_it_read() -> None:
    offences: list[str] = []
    for module in (
        BACKEND / "app/persistence/repositories.py",
        BACKEND / "app/persistence/mongo_case_store.py",
    ):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            func = call.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr in {"replace", "delete"}
                and any(keyword.arg == "expected_revision" for keyword in call.keywords)
            ):
                continue
            nonce = next((k for k in call.keywords if k.arg == "expected_nonce"), None)
            revision = next(k for k in call.keywords if k.arg == "expected_revision")
            if nonce is None:
                offences.append(f"{module.name}:{call.lineno} no expected_nonce")
                continue
            # Same snapshot: both come from the same read object.
            if not (
                isinstance(nonce.value, ast.Attribute)
                and isinstance(revision.value, ast.Attribute)
                and ast.dump(nonce.value.value) == ast.dump(revision.value.value)
                and nonce.value.attr == "write_nonce"
            ):
                offences.append(f"{module.name}:{call.lineno} nonce not from the read snapshot")
    assert offences == []


def test_every_ledger_entry_copy_carries_the_dispatch_claim() -> None:
    """A rebuilt entry must never drop a claim (reader release round-trip)."""

    tree = ast.parse((BACKEND / "app/services/onboarding.py").read_text(encoding="utf-8"))
    offences: list[int] = []
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        func = call.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        owner = func.value.id if isinstance(func, ast.Attribute) and isinstance(
            func.value, ast.Name
        ) else ""
        if name == "GoldTierExecutionLedgerEntry":
            source = next((k for k in call.keywords if k.arg == "submission_input"), None)
            copies_existing = source is not None and not (
                isinstance(source.value, ast.Name) and source.value.id == "submission_input"
            ) and "submission_input.model_copy" not in ast.unparse(source.value)
            has_claim = any(k.arg == "workflow_dispatch" for k in call.keywords)
            if copies_existing and not has_claim:
                offences.append(call.lineno)
        if (
            owner == "GoldTierExecutionLedgerEntry"
            and name == "model_validate"
            and "workflow_dispatch" not in ast.unparse(call)
        ):
            offences.append(call.lineno)
    assert offences == []


def test_memory_ledger_refuses_to_rewrite_a_claim() -> None:
    entry = _writer_release_snapshot().target_executions[0]
    repository = InMemoryTargetExecutionRepository()
    repository.create(entry)
    stripped = entry.model_copy(update={"workflow_dispatch": None})
    with pytest.raises(TargetExecutionRepositoryConflictError):
        repository.replace(
            stripped,
            expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
            expected_attempted=entry.attempted_operations,
        )
    kept = entry.model_copy(update={"shell_status": "REQUESTED"})
    repository.replace(
            kept,
            expected_state=GoldTierExecutionLedgerState.IN_PROGRESS.value,
            expected_attempted=entry.attempted_operations,
        )
    stored = repository.get(entry.submission_input.submission_id)
    assert stored is not None and stored.workflow_dispatch == entry.workflow_dispatch


def test_entry_copy_keeps_the_claim() -> None:
    entry = _writer_release_snapshot().target_executions[0]
    assert entry.model_copy(deep=True).workflow_dispatch == entry.workflow_dispatch
    assert GoldTierExecutionLedgerEntry.model_validate(entry).workflow_dispatch is not None


# --- workflow definition writers --------------------------------------------------------

NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="refresh", name="Refresh", use_case="Case refresh", country="Singapore",
        created_at=NOW, updated_at=NOW,
    )


def test_definition_nonce_is_backend_only() -> None:
    definition = _definition().model_copy(update={"write_nonce": "f" * 32})
    assert "write_nonce" not in definition.model_dump(mode="json")


def test_memory_definition_repository_guards_and_rotates_the_nonce() -> None:
    repository = InMemoryWorkflowDefinitionRepository()
    created = repository.create(_definition())
    assert created.write_nonce is not None
    stale = created.model_copy(update={"write_nonce": "0" * 32, "revision": 2})
    with pytest.raises(PersistenceConflictError):
        repository.update(stale, expected_revision=1)
    fresh = repository.update(created.model_copy(update={"revision": 2}), expected_revision=1)
    assert fresh.write_nonce not in {None, created.write_nonce}


class _DefinitionCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, Any], dict[str, Any]]] = []

    def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> Any:
        self.calls.append((query, update))
        return SimpleNamespace(matched_count=1, modified_count=1)


def test_mongo_definition_update_filters_nonce_and_never_exceeds_latest_version() -> None:
    repository = object.__new__(MongoWorkflowDefinitionRepository)
    collection = _DefinitionCollection()
    repository._collection = collection  # noqa: SLF001
    current = _definition().model_copy(update={"write_nonce": "1" * 32})
    written = repository.update(current.model_copy(update={"revision": 2}), expected_revision=1)
    query, update = collection.calls[-1]
    assert query["revision"] == 1 and query["write_nonce"] == "1" * 32
    assert {"latest_version": {"$exists": False}} in query["$or"]
    assert {"latest_version": {"$gte": 0}} in query["$or"]
    assert set(update["$set"]) == {"revision", "write_nonce", "payload"}
    assert written.write_nonce == update["$set"]["write_nonce"] != "1" * 32
    assert "write_nonce" not in update["$set"]["payload"]


# --- reverse migration (R3-4, R2-4) ------------------------------------------------------


class _MigrationCollection:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self.documents = {item["_id"]: copy.deepcopy(item) for item in documents}

    def find(self, _query: dict[str, Any]) -> list[dict[str, Any]]:
        return [copy.deepcopy(item) for item in self.documents.values()]

    def with_options(self, **_kwargs: Any) -> _MigrationCollection:
        return self

    def replace_one(self, query: dict[str, Any], document: dict[str, Any]) -> Any:
        current = self.documents.get(query["_id"])
        nonce = query["write_nonce"]
        nonce_ok = (
            "write_nonce" not in (current or {})
            if isinstance(nonce, dict)
            else (current or {}).get("write_nonce") == nonce
        )
        if current is None or current.get("revision") != query["revision"] or not nonce_ok:
            return SimpleNamespace(modified_count=0)
        self.documents[query["_id"]] = {"_id": query["_id"], **document}
        return SimpleNamespace(modified_count=1)


def _case_raw(snapshot: DurableCaseSnapshot) -> dict[str, Any]:
    return CODEC._encode(snapshot)  # noqa: SLF001


def _definition_raw(**top: Any) -> dict[str, Any]:
    definition = _definition()
    return {"_id": "refresh", "revision": 1, "payload": definition.model_dump(mode="json"), **top}


def _plan(cases: _MigrationCollection, definitions: _MigrationCollection) -> Any:
    return plan_reverse_migration(
        cases, definitions, decode_legacy_case=CODEC._decode  # noqa: SLF001
    )


def test_reverse_migration_refuses_an_unfinalised_write_marker() -> None:
    cases = _MigrationCollection([_case_raw(_writer_release_snapshot())])
    plan = _plan(cases, _MigrationCollection([]))
    assert [item.reason for item in plan.refusals] == ["DISPATCH_WRITE_MARKER_NOT_FINALISED"]
    with pytest.raises(ReverseMigrationRefusedError):
        apply_reverse_migration(plan, cases, _MigrationCollection([]))


def test_reverse_migration_clears_unattempted_claims_and_is_idempotent() -> None:
    snapshot = _snapshot()
    entry = snapshot.target_executions[0].model_copy(
        update={
            "workflow_dispatch": WorkflowDispatch(
                state=WorkflowDispatchState.TENTATIVE, token=TOKEN, version=2, lease_until=LEASE
            )
        }
    )
    raw = _case_raw(
        snapshot.model_copy(update={"target_executions": (entry,), "write_nonce": "2" * 32})
    )
    cases = _MigrationCollection([raw])
    definitions = _MigrationCollection(
        [_definition_raw(write_nonce="3" * 32, active_version=0, latest_version=0,
                         dispatch_authorisation_seq=4)]
    )
    plan = _plan(cases, definitions)
    assert not plan.refused
    assert apply_reverse_migration(plan, cases, definitions) == {"cases": 1, "definitions": 1}
    reverted = cases.documents[raw["_id"]]
    assert reverted["schema_version"] == 20 and "write_nonce" not in reverted
    assert "workflow_dispatch" not in reverted["target_executions"][0]
    assert reverted["revision"] == raw["revision"] + 1
    legacy = CODEC._decode(reverted)  # noqa: SLF001
    assert legacy.write_nonce is None
    definition = definitions.documents["refresh"]
    assert set(definition) == {"_id", "revision", "payload"} and definition["revision"] == 1
    again = _plan(cases, definitions)
    assert (again.cases, again.definitions, again.refusals) == ([], [], [])
    assert again.already_reverted_cases == 1 and again.already_reverted_definitions == 1


def test_reverse_migration_allows_a_finalised_marked_entry() -> None:
    # Planning reads raw state; a finalised entry's claim is no longer recovery data.
    raw = _case_raw(_writer_release_snapshot())
    raw["target_executions"][0]["state"] = GoldTierExecutionLedgerState.FINALIZED.value
    plan = _plan(_MigrationCollection([raw]), _MigrationCollection([]))
    # This synthetic entry lacks a terminal record, so the schema-20 decode check refuses
    # it instead: the migration still never writes a document legacy code cannot read.
    assert [item.reason for item in plan.refusals] == ["LEGACY_DECODE_FAILED"]


@pytest.mark.parametrize(
    ("top", "reason"),
    [
        ({"write_nonce": "4" * 32, "active_version": 0, "latest_version": 2},
         "DEACTIVATED_WORKFLOW"),
        ({"write_nonce": "4" * 32, "outbox": []}, "P2_1_CONTENT_PRESENT"),
        ({"required_baseline": {}}, "P2_1_CONTENT_PRESENT"),
    ],
)
def test_reverse_migration_refuses_definitions_it_cannot_preserve(
    top: dict[str, Any], reason: str
) -> None:
    plan = _plan(_MigrationCollection([]), _MigrationCollection([_definition_raw(**top)]))
    assert [item.reason for item in plan.refusals] == [reason]


def test_reverse_migration_detects_a_document_changed_after_planning() -> None:
    raw = _case_raw(_snapshot().model_copy(update={"write_nonce": "5" * 32}))
    cases = _MigrationCollection([raw])
    plan = _plan(cases, _MigrationCollection([]))
    cases.documents[raw["_id"]]["write_nonce"] = "6" * 32
    with pytest.raises(ReverseMigrationRefusedError):
        apply_reverse_migration(plan, cases, _MigrationCollection([]))


def test_reverse_migration_summary_has_no_document_content() -> None:
    plan = _plan(
        _MigrationCollection([_case_raw(_writer_release_snapshot())]), _MigrationCollection([])
    )
    summary = plan.summary()
    assert set(summary) == {
        "cases_to_revert", "definitions_to_revert", "already_reverted_cases",
        "already_reverted_definitions", "refusals",
    }
    assert all(set(item) == {"collection", "id", "reason"} for item in summary["refusals"])



# --- reader R1 (QG R0 notes P3-3, P3-5; version 0 for "no active version") ---------------


def test_claim_for_no_active_version_round_trips() -> None:
    claim = WorkflowDispatch(
        state=WorkflowDispatchState.TENTATIVE, token=TOKEN, version=0, lease_until=LEASE
    )
    snapshot = _snapshot()
    entry = snapshot.target_executions[0].model_copy(update={"workflow_dispatch": claim})
    raw = CODEC._encode(snapshot.model_copy(update={"target_executions": (entry,)}))  # noqa: SLF001
    assert CODEC._decode(raw).target_executions[0].workflow_dispatch == claim  # noqa: SLF001


def test_a_stored_null_nonce_is_rejected() -> None:
    raw = CODEC._encode(_snapshot())  # noqa: SLF001
    raw["write_nonce"] = None
    with pytest.raises(PersistenceDataInvalidError):
        CODEC._decode(raw)  # noqa: SLF001


def test_reverse_migration_refuses_an_unknown_schema_version() -> None:
    raw = CODEC._encode(_snapshot())  # noqa: SLF001
    raw["schema_version"] = 22
    plan = _plan(_MigrationCollection([raw]), _MigrationCollection([]))
    assert [item.reason for item in plan.refusals] == ["SCHEMA_VERSION_UNKNOWN"]
