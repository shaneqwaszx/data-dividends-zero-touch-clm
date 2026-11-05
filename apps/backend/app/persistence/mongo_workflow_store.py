"""Mongo persistence for workflow definitions and runs (D-121).

Writes are insert-only on create and revision-guarded on update, so a deleted record
cannot be recreated by a stale writer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import ValidationError
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.domain.workflows import WorkflowDefinition, WorkflowRun
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceUnavailableError,
)


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


def _decode_definition(raw: dict[str, Any]) -> WorkflowDefinition:
    try:
        return WorkflowDefinition.model_validate(raw["payload"])
    except (KeyError, ValidationError):
        raise PersistenceDataInvalidError from None


def _decode_run(raw: dict[str, Any]) -> WorkflowRun:
    try:
        return WorkflowRun.model_validate(raw["payload"])
    except (KeyError, ValidationError):
        raise PersistenceDataInvalidError from None


class MongoWorkflowDefinitionRepository:
    def __init__(self, store: MongoWorkflowStore) -> None:
        self._collection = store.definitions

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
        try:
            self._collection.insert_one(
                {
                    "_id": definition.workflow_id,
                    "revision": definition.revision,
                    "payload": definition.model_dump(mode="json"),
                }
            )
        except DuplicateKeyError:
            raise PersistenceConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return definition

    def update(
        self, definition: WorkflowDefinition, *, expected_revision: int
    ) -> WorkflowDefinition:
        try:
            result = self._collection.update_one(
                {"_id": definition.workflow_id, "revision": expected_revision},
                {
                    "$set": {
                        "revision": definition.revision,
                        "payload": definition.model_dump(mode="json"),
                    }
                },
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.matched_count != 1:
            raise PersistenceConflictError
        return definition


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
