"""Mongo persistence for workflow definitions and runs (D-123).

Writes are insert-only on create and revision-guarded on update, so a deleted record
cannot be recreated by a stale writer.
"""

from __future__ import annotations

import builtins
import re
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.write_concern import WriteConcern

from app.domain.workflow_governance import FIELD_MIGRATION_MARKER, WorkflowGovernanceState
from app.domain.workflows import WorkflowDefinition, WorkflowRun, WorkflowVersion
from app.persistence.adr017_backfill import (
    verify_definition_document,
    verify_p2_1_definition_document,
)
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceOutcomeAmbiguousError,
    PersistenceUnavailableError,
)
from app.persistence.workflow_governance_store import (
    ColdHistoryStore,
    GovernedDefinition,
    MongoColdHistoryStore,
    WorkflowGovernanceNotMigratedError,
    check_document_size,
    cold_version,
    compact_history,
    decode_governance_fields,
    drain_outbox_entries,
    encode_governance_fields,
    governed_document,
    prepare_governance_write,
)

# ADR-017 section 3.1: creation/provisioning and D3 use the durable write rule.
DURABLE_WRITE_CONCERN = WriteConcern(w="majority", j=True, wtimeout=5_000)


class MongoWorkflowStore:
    def __init__(
        self,
        client: MongoClient[dict[str, Any]],
        *,
        database: str,
        definitions_collection: str,
        runs_collection: str,
    ) -> None:
        db = client[database]
        self._client = client
        self.definitions: Collection[dict[str, Any]] = db[definitions_collection]
        self.runs: Collection[dict[str, Any]] = db[runs_collection]
        # ADR-017 section 5: the insert-only cold history collections of the same database.
        self.cold = MongoColdHistoryStore(db)

    def initialize(self) -> None:
        try:
            self._client.admin.command("ping")
            self.runs.create_index([("case_id", ASCENDING)], name="workflow_run_case_id")
        except PyMongoError:
            raise PersistenceUnavailableError from None
        self.cold.initialize()

    def close(self) -> None:
        self._client.close()


_NONCE = re.compile(r"[0-9a-f]{32}")


def _decode_definition(raw: dict[str, Any]) -> WorkflowDefinition:
    """Decode the payload; top-level ADR-017 fields stay in the stored document.

    Only ``payload``, ``revision`` and ``write_nonce`` are ever ``$set`` by this
    release, so ``active_version``, ``latest_version``, ``dispatch_authorisation_seq``
    and any later top-level field are preserved unchanged on every write.
    """
    nonce = raw.get("write_nonce")
    if "write_nonce" in raw and (not isinstance(nonce, str) or not _NONCE.fullmatch(nonce)):
        # A stored null nonce (P3-5) is invalid, like any other malformed nonce.
        raise PersistenceDataInvalidError
    try:
        definition = WorkflowDefinition.model_validate(raw["payload"])
    except (KeyError, ValidationError):
        raise PersistenceDataInvalidError from None
    stored: dict[str, Any] = {"write_nonce": nonce}
    for field, name in (("active_version", "stored_active_version"),
                        ("latest_version", "latest_version")):
        value = raw.get(field)
        if value is not None and (type(value) is not int or value < 0):
            raise PersistenceDataInvalidError
        stored[name] = value
    return definition.model_copy(update=stored)


def _nonce_filter(expected_nonce: str | None) -> dict[str, Any]:
    if expected_nonce is None:
        return {"write_nonce": {"$exists": False}}
    return {"write_nonce": expected_nonce}


def _highest_version(definition: WorkflowDefinition) -> int:
    return max((item.version for item in definition.versions), default=0)


def _decode_run(raw: dict[str, Any]) -> WorkflowRun:
    try:
        return WorkflowRun.model_validate(raw["payload"])
    except (KeyError, ValidationError):
        raise PersistenceDataInvalidError from None


def _decode_governed(raw: dict[str, Any]) -> GovernedDefinition:
    return GovernedDefinition(_decode_definition(raw), decode_governance_fields(raw))


def _stored_revision(raw: dict[str, Any]) -> int:
    revision = raw.get("revision")
    if type(revision) is not int:
        raise PersistenceDataInvalidError
    return revision


class MongoWorkflowDefinitionRepository:
    def __init__(
        self,
        store: MongoWorkflowStore,
        *,
        cold_store: ColdHistoryStore | None = None,
        archive_confirming_writes: bool = False,
    ) -> None:
        self._collection = store.definitions
        self._durable = store.definitions.with_options(write_concern=DURABLE_WRITE_CONCERN)
        self._cold: ColdHistoryStore = store.cold if cold_store is None else cold_store
        # ADR-017 section 5: fallback mode (fresh-suffix inserts) unless CT-16 allows the
        # confirming write. Default off.
        self._confirming = archive_confirming_writes

    def list(self) -> list[WorkflowDefinition]:
        try:
            items = [_decode_definition(raw) for raw in self._collection.find({})]
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return sorted(items, key=lambda item: item.created_at)

    def get(self, workflow_id: str) -> WorkflowDefinition | None:
        try:
            raw = self._collection.find_one({"_id": workflow_id})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return None if raw is None else _decode_definition(raw)

    def create(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        """Insert-only, durable, and always with the authoritative version fields."""

        nonce = secrets.token_hex(16)
        highest = _highest_version(definition)
        try:
            self._durable.insert_one(
                {
                    "_id": definition.workflow_id,
                    "revision": definition.revision,
                    "write_nonce": nonce,
                    "active_version": highest,
                    "latest_version": highest,
                    "dispatch_authorisation_seq": 0,
                    "payload": definition.model_dump(mode="json"),
                }
            )
        except DuplicateKeyError:
            raise PersistenceConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return definition.model_copy(
            update={
                "write_nonce": nonce,
                "stored_active_version": highest,
                "latest_version": highest,
            }
        )

    def update(
        self, definition: WorkflowDefinition, *, expected_revision: int
    ) -> WorkflowDefinition:
        """Compare-and-set on the revision and nonce read; set a new nonce.

        Once ``latest_version`` exists (written by the P2-0 backfill or writer release),
        this release refuses any payload whose versions exceed it: an ungoverned append
        could not keep ``active_version`` and ``latest_version`` true (ADR-017 3.2, 3.5).
        From P2-1 it also refuses a migrated document (marker present): after migration
        every definition write goes through ``write_governance``.
        """
        nonce = secrets.token_hex(16)
        try:
            result = self._collection.update_one(
                {
                    "_id": definition.workflow_id,
                    "revision": expected_revision,
                    **_nonce_filter(definition.write_nonce),
                    FIELD_MIGRATION_MARKER: {"$exists": False},
                    "$or": [
                        {"latest_version": {"$exists": False}},
                        {"latest_version": {"$gte": _highest_version(definition)}},
                    ],
                },
                {
                    "$set": {
                        "revision": definition.revision,
                        "write_nonce": nonce,
                        "payload": definition.model_dump(mode="json"),
                    }
                },
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.matched_count != 1:
            raise PersistenceConflictError
        return definition.model_copy(update={"write_nonce": nonce})

    def dispatch_active_version(self, workflow_id: str) -> int | None:
        """D1 (advisory): a stale read only causes a D3 retry."""

        try:
            raw = self._collection.find_one({"_id": workflow_id}, {"active_version": 1})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        value = None if raw is None else raw.get("active_version")
        return value if type(value) is int and value >= 0 else None

    def authorise_dispatch(self, workflow_id: str, version: int) -> bool:
        """D3, the linearisation point. Modifies only ``dispatch_authorisation_seq``."""

        try:
            result = self._durable.update_one(
                {
                    "_id": workflow_id,
                    "active_version": version,
                    "latest_version": version,
                    "payload.versions.version": {"$ne": version + 1},
                },
                {"$inc": {"dispatch_authorisation_seq": 1}},
            )
        except PyMongoError:
            raise PersistenceOutcomeAmbiguousError from None
        return result.acknowledged and result.modified_count == 1

    def verify_dispatch_state(self) -> builtins.list[tuple[str, str]]:
        """P2-0 checks on unmigrated documents; the P2-1 checks on migrated ones."""

        try:
            raws = list(self._collection.find({}))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [
            (str(raw.get("_id")), reason)
            for raw in raws
            if (
                reason := verify_p2_1_definition_document(raw, cold=self._cold)
                if FIELD_MIGRATION_MARKER in raw
                else verify_definition_document(raw)
            )
            is not None
        ]

    # --- P2-1 governance (ADR-017 1.1, 3.1, 3.2, 3.5, 5) ---------------------------------

    def get_governed(self, workflow_id: str) -> GovernedDefinition | None:
        try:
            raw = self._collection.find_one({"_id": workflow_id})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return None if raw is None else _decode_governed(raw)

    def list_governed(self) -> builtins.list[GovernedDefinition]:
        try:
            items = [_decode_governed(raw) for raw in self._collection.find({})]
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return sorted(items, key=lambda item: item.definition.created_at)

    def create_governed(
        self, definition: WorkflowDefinition, governance: WorkflowGovernanceState
    ) -> GovernedDefinition:
        """Insert-only, durable, born with its migration marker (D-7 empty workflows)."""

        if not governance.migrated:
            raise WorkflowGovernanceNotMigratedError
        nonce = secrets.token_hex(16)
        highest = _highest_version(definition)
        document = governed_document(
            definition,
            governance,
            write_nonce=nonce,
            active_version=highest,
            latest_version=highest,
        )
        check_document_size(document)
        try:
            self._durable.insert_one(document)
        except DuplicateKeyError:
            raise PersistenceConflictError from None
        except PyMongoError:
            raise PersistenceOutcomeAmbiguousError from None
        stored = definition.model_copy(
            update={
                "write_nonce": nonce,
                "stored_active_version": highest,
                "latest_version": highest,
            }
        )
        return GovernedDefinition(stored, governance)

    def write_governance(
        self,
        definition: WorkflowDefinition,
        governance: WorkflowGovernanceState,
        *,
        expected_revision: int,
        active_version: int | None = None,
        latest_version: int | None = None,
        deactivate: bool = False,
    ) -> GovernedDefinition:
        """The one governance compare-and-set (durable; revision and nonce as read).

        ``definition`` is the payload to store, carrying the ``write_nonce`` it was read
        with. Its ``stored_active_version``/``latest_version`` are never trusted: the
        stored document is read, validated and history-guarded, and the CAS filter asserts
        revision, nonce, ``active_version`` and ``latest_version`` as read. A publication
        passes both ``active_version`` and ``latest_version``. Compaction runs last; the
        encoded document is then checked against the hard ceiling (never truncated).
        """

        if not governance.migrated:
            raise WorkflowGovernanceNotMigratedError
        try:
            raw = self._collection.find_one({"_id": definition.workflow_id})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if (
            raw is None
            or _stored_revision(raw) != expected_revision
            or raw.get("write_nonce") != definition.write_nonce
        ):
            raise PersistenceConflictError
        stored = _decode_governed(raw)
        read_active = stored.definition.stored_active_version
        read_latest = stored.definition.latest_version
        compacted, state, active, latest = prepare_governance_write(
            stored,
            definition,
            governance,
            self._cold,
            active_version=active_version,
            latest_version=latest_version,
            deactivate=deactivate,
        )
        nonce = secrets.token_hex(16)
        check_document_size(
            governed_document(
                compacted, state, write_nonce=nonce, active_version=active, latest_version=latest
            )
        )
        updates: dict[str, Any] = {
            "revision": compacted.revision,
            "write_nonce": nonce,
            "payload": compacted.model_dump(mode="json"),
        }
        if latest_version is not None or deactivate:
            updates["active_version"] = active
            updates["latest_version"] = latest
        updates.update(encode_governance_fields(state))
        try:
            result = self._durable.update_one(
                {
                    "_id": compacted.workflow_id,
                    "revision": expected_revision,
                    **_nonce_filter(definition.write_nonce),
                    "active_version": read_active,
                    "latest_version": read_latest,
                    FIELD_MIGRATION_MARKER: {"$exists": True},
                },
                {"$set": updates},
            )
        except PyMongoError:
            raise PersistenceOutcomeAmbiguousError from None
        if not result.acknowledged or result.matched_count != 1:
            raise PersistenceConflictError
        written = compacted.model_copy(
            update={
                "write_nonce": nonce,
                "stored_active_version": active,
                "latest_version": latest,
            }
        )
        return GovernedDefinition(written, state)

    def drain_outbox(self, workflow_id: str, *, now: datetime | None = None) -> int:
        """Archive the outbox (startup, before every governance mutation, after each
        commit). Returns how many entries left the outbox after durable acknowledgement.

        The acknowledged prefix is committed in one durable CAS that rotates the nonce but
        keeps the revision (housekeeping does not stale a client's expected revision);
        then a failed entry's error is raised and the entry stays in the outbox.
        """

        try:
            raw = self._collection.find_one({"_id": workflow_id})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if raw is None or FIELD_MIGRATION_MARKER not in raw:
            return 0
        current = _decode_governed(raw)
        if not current.governance.outbox:
            return 0
        result = drain_outbox_entries(
            current.definition,
            current.governance,
            self._cold,
            now=now or datetime.now(UTC),
            confirming_writes=self._confirming,
        )
        if result.archived:
            self._commit_housekeeping(
                _stored_revision(raw), current, result.definition, result.governance
            )
        if result.error is not None:
            raise result.error
        return len(result.archived)

    def drain_all(self, *, now: datetime | None = None) -> int:
        """Startup drain over every migrated definition."""

        return sum(
            self.drain_outbox(item.definition.workflow_id, now=now)
            for item in self.list_governed()
            if item.governance.migrated and item.governance.outbox
        )

    def _commit_housekeeping(
        self,
        expected_revision: int,
        current: GovernedDefinition,
        definition: WorkflowDefinition,
        governance: WorkflowGovernanceState,
    ) -> None:
        """Drain/compaction commit: rotates the nonce, keeps the revision.

        Safe because the two tokens guard different things. The revision is the client's
        optimistic token (``expected_workflow_revision``); housekeeping changes no
        governance meaning (only archived flags, outbox removal and acknowledged items
        leaving the hot document), so it must not stale a client's request. The nonce is
        the same-snapshot CAS token (ADR-017 3.2): rotating it makes every writer still
        holding the pre-housekeeping snapshot fail its filter, re-read and re-evaluate.
        """
        active = current.definition.stored_active_version
        latest = current.definition.latest_version
        if active is None or latest is None:
            raise PersistenceDataInvalidError
        compacted, state = compact_history(
            definition, governance, self._cold, active_version=active, latest_version=latest
        )
        nonce = secrets.token_hex(16)
        check_document_size(
            governed_document(
                compacted, state, write_nonce=nonce, active_version=active, latest_version=latest
            )
        )
        try:
            result = self._durable.update_one(
                {
                    "_id": compacted.workflow_id,
                    "revision": expected_revision,
                    **_nonce_filter(current.definition.write_nonce),
                    "active_version": active,
                    "latest_version": latest,
                    FIELD_MIGRATION_MARKER: {"$exists": True},
                },
                {
                    "$set": {
                        "write_nonce": nonce,
                        "payload": compacted.model_dump(mode="json"),
                        **encode_governance_fields(state),
                    }
                },
            )
        except PyMongoError:
            raise PersistenceOutcomeAmbiguousError from None
        if not result.acknowledged or result.matched_count != 1:
            raise PersistenceConflictError

    def get_version(self, workflow_id: str, version: int) -> WorkflowVersion | None:
        """Hot ``payload.versions`` first, then cold by ``logical_id`` (ADR-017 5)."""

        current = self.get_governed(workflow_id)
        if current is None:
            return None
        for item in current.definition.versions:
            if item.version == version:
                return item
        latest = current.definition.latest_version
        if latest is None or version > latest or version < 1:
            return None
        return cold_version(self._cold, workflow_id, version)

    def verify_governance_state(self) -> builtins.list[tuple[str, str]]:
        """P2-1 governance enablement: every definition must be migrated and sound."""

        try:
            raws = list(self._collection.find({}))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [
            (str(raw.get("_id")), reason)
            for raw in raws
            if (reason := verify_p2_1_definition_document(raw, cold=self._cold)) is not None
        ]


class MongoWorkflowRunRepository:
    def __init__(self, store: MongoWorkflowStore) -> None:
        self._collection = store.runs

    def list_for_case(self, case_id: UUID) -> list[WorkflowRun]:
        try:
            items = [
                _decode_run(raw) for raw in self._collection.find({"case_id": str(case_id)})
            ]
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return sorted(items, key=lambda item: item.created_at)

    def list_for_workflow(self, workflow_id: str) -> list[WorkflowRun]:
        try:
            items = [
                _decode_run(raw)
                for raw in self._collection.find({"payload.workflow_id": workflow_id})
            ]
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return sorted(items, key=lambda item: item.created_at)

    def get(self, run_id: UUID) -> WorkflowRun | None:
        try:
            raw = self._collection.find_one({"_id": str(run_id)})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return None if raw is None else _decode_run(raw)

    def create(self, run: WorkflowRun) -> WorkflowRun:
        try:
            self._collection.insert_one(
                {
                    "_id": str(run.run_id),
                    "case_id": None if run.case_id is None else str(run.case_id),
                    "revision": run.revision,
                    "payload": run.model_dump(mode="json"),
                }
            )
        except DuplicateKeyError:
            raise PersistenceConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return run

    def update(self, run: WorkflowRun, *, expected_revision: int) -> WorkflowRun:
        try:
            payload = run.model_dump(mode="json")
            # ADR-018 3.5: a frozen applicability basis is write-once. The update matches
            # only when the stored basis is not frozen, or is carried over unchanged.
            keep_basis: list[dict[str, Any]] = [
                {"payload.applicability_basis.frozen": {"$ne": True}}
            ]
            if "applicability_basis" in payload:
                keep_basis.append({"payload.applicability_basis": payload["applicability_basis"]})
            result = self._collection.update_one(
                {"_id": str(run.run_id), "revision": expected_revision, "$or": keep_basis},
                {"$set": {"revision": run.revision, "payload": payload}},
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.matched_count != 1:
            raise PersistenceConflictError
        return run

    def delete(self, run_id: UUID) -> None:
        try:
            self._collection.delete_one({"_id": str(run_id)})
        except PyMongoError:
            raise PersistenceUnavailableError from None

    def delete_for_case(self, case_id: UUID) -> None:
        try:
            self._collection.delete_many({"case_id": str(case_id)})
        except PyMongoError:
            raise PersistenceUnavailableError from None
