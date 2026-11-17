"""Mongo persistence for workflow definitions and runs (D-123).

Writes are insert-only on create and revision-guarded on update, so a deleted record
cannot be recreated by a stale writer.
"""

from __future__ import annotations

import builtins
import re
import secrets
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.write_concern import WriteConcern

from app.domain.workflows import WorkflowDefinition, WorkflowRun
from app.persistence.adr017_backfill import verify_definition_document
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceOutcomeAmbiguousError,
    PersistenceUnavailableError,
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

    def initialize(self) -> None:
        try:
            self._client.admin.command("ping")
            self.runs.create_index([("case_id", ASCENDING)], name="workflow_run_case_id")
        except PyMongoError:
            raise PersistenceUnavailableError from None

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


class MongoWorkflowDefinitionRepository:
    def __init__(self, store: MongoWorkflowStore) -> None:
        self._collection = store.definitions
        self._durable = store.definitions.with_options(write_concern=DURABLE_WRITE_CONCERN)

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
        """
        nonce = secrets.token_hex(16)
        try:
            result = self._collection.update_one(
                {
                    "_id": definition.workflow_id,
                    "revision": expected_revision,
                    **_nonce_filter(definition.write_nonce),
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
        try:
            raws = list(self._collection.find({}))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [
            (str(raw.get("_id")), reason)
            for raw in raws
            if (reason := verify_definition_document(raw)) is not None
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
            result = self._collection.update_one(
                {"_id": str(run.run_id), "revision": expected_revision},
                {"$set": {"revision": run.revision, "payload": run.model_dump(mode="json")}},
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
