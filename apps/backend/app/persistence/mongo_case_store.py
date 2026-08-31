"""Single-document Mongo store for bounded durable CLM case snapshots."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.domain.documents import (
    DocumentEventType,
    DocumentProcessingState,
    DocumentWorkflowEvent,
)
from app.domain.models import EventOutcome, SafeError
from app.domain.target_submission import GoldTierExecutionLedgerState
from app.domain.zero_touch import (
    AutomationEvent,
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
)
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceSchemaUnsupportedError,
    PersistenceUnavailableError,
)
from app.persistence.models import CASE_SNAPSHOT_SCHEMA_VERSION, DurableCaseSnapshot


class MongoCaseStore:
    """Validate and compare-and-set one complete structured case envelope."""

    def __init__(
        self,
        client: MongoClient[dict[str, Any]],
        *,
        database: str,
        collection: str,
    ) -> None:
        self._client = client
        self._collection: Collection[dict[str, Any]] = client[database][collection]
        self._lock = RLock()

    @property
    def transaction_lock(self) -> RLock:
        return self._lock

    def initialize(self) -> None:
        try:
            self._client.admin.command("ping")
            self._collection.create_index(
                [("case_id", ASCENDING)], unique=True, name="case_id_unique"
            )
            self._collection.create_index(
                [("automation.status", ASCENDING), ("updated_at", DESCENDING)],
                name="automation_status_updated_at",
            )
            self._collection.create_index(
                [("target_executions.submission_input.submission_id", ASCENDING)],
                name="target_submission_lookup",
            )
            self._collection.create_index(
                [("documents.document_id", ASCENDING)], name="document_id_lookup"
            )
            for raw in self._collection.find({}):
                snapshot = self._decode(raw)
                recovered = self._recover_interrupted(snapshot)
                if recovered != snapshot:
                    self.replace(recovered, expected_revision=snapshot.revision)
        except (PersistenceDataInvalidError, PersistenceSchemaUnsupportedError):
            raise
        except PyMongoError:
            raise PersistenceUnavailableError from None

    def close(self) -> None:
        self._client.close()

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self._lock:
            yield

    def create(self, snapshot: DurableCaseSnapshot) -> DurableCaseSnapshot:
        candidate = DurableCaseSnapshot.model_validate(snapshot)
        raw = self._encode(candidate)
        try:
            self._collection.insert_one(raw)
        except DuplicateKeyError:
            raise PersistenceConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return candidate.model_copy(deep=True)

    def get(self, case_id: UUID) -> DurableCaseSnapshot | None:
        try:
            raw = self._collection.find_one({"_id": str(case_id)})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return self._decode(raw) if raw is not None else None

    def list(self) -> list[DurableCaseSnapshot]:
        try:
            raw_records = list(
                self._collection.find({}).sort(
                    [("updated_at", DESCENDING), ("case_id", DESCENDING)]
                )
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [self._decode(item) for item in raw_records]

    def find_by_submission(self, submission_id: UUID) -> DurableCaseSnapshot | None:
        try:
            raw = self._collection.find_one(
                {"target_executions.submission_input.submission_id": str(submission_id)}
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return self._decode(raw) if raw is not None else None

    def find_by_document(self, document_id: UUID) -> DurableCaseSnapshot | None:
        try:
            raw = self._collection.find_one({"documents.document_id": str(document_id)})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return self._decode(raw) if raw is not None else None

    def replace(
        self,
        snapshot: DurableCaseSnapshot,
        *,
        expected_revision: int,
    ) -> DurableCaseSnapshot:
        candidate = DurableCaseSnapshot.model_validate(snapshot).model_copy(
            update={"revision": expected_revision + 1, "updated_at": datetime.now(UTC)},
            deep=True,
        )
        try:
            result = self._collection.replace_one(
                {"_id": str(candidate.case_id), "revision": expected_revision},
                self._encode(candidate),
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.modified_count != 1:
            raise PersistenceConflictError
        return candidate.model_copy(deep=True)

    def _encode(self, snapshot: DurableCaseSnapshot) -> dict[str, Any]:
        raw_value = _persistence_value(snapshot)
        if not isinstance(raw_value, dict):
            raise PersistenceDataInvalidError
        raw = raw_value
        raw["_id"] = str(snapshot.case_id)
        return raw

    def _decode(self, raw: dict[str, Any]) -> DurableCaseSnapshot:
        value = dict(raw)
        value.pop("_id", None)
        schema_version = value.get("schema_version")
        if schema_version != CASE_SNAPSHOT_SCHEMA_VERSION:
            raise PersistenceSchemaUnsupportedError
        try:
            snapshot = DurableCaseSnapshot.model_validate(value)
            _reject_unknown_model_fields(value, snapshot)
            return snapshot
        except (ValidationError, ValueError, TypeError):
            raise PersistenceDataInvalidError from None

    def _recover_interrupted(
        self, snapshot: DurableCaseSnapshot
    ) -> DurableCaseSnapshot:
        """Conservatively classify state whose transient inputs/outcome were lost."""

        now = datetime.now(UTC)
        documents = []
        changed = False
        for record in snapshot.documents:
            if record.state not in {
                DocumentProcessingState.UPLOADED,
                DocumentProcessingState.PROCESSING,
            }:
                documents.append(record)
                continue
            recovered = record.model_copy(deep=True)
            recovered.state = DocumentProcessingState.FAILED
            recovered.fields = []
            recovered.processed_at = None
            recovered.reviewed_at = None
            recovered.error = SafeError(
                code="DOCUMENT_REUPLOAD_REQUIRED",
                message=(
                    "Document processing was interrupted before structured evidence "
                    "was retained; re-upload is required."
                ),
            )
            recovered.updated_at = now
            recovered.events.append(
                DocumentWorkflowEvent(
                    sequence=len(recovered.events) + 1,
                    event_type=DocumentEventType.DOCUMENT_PROCESSING_FAILED,
                    state=DocumentProcessingState.FAILED,
                    outcome=EventOutcome.FAILED,
                    timestamp=now,
                    case_id=recovered.case_id,
                    document_id=recovered.document_id,
                    correlation_id=recovered.correlation_id,
                    code="DOCUMENT_REUPLOAD_REQUIRED",
                    message=(
                        "Interrupted processing requires explicit document re-upload."
                    ),
                )
            )
            documents.append(recovered)
            changed = True

        target_executions = tuple(
            entry
            for entry in snapshot.target_executions
            if not (
                entry.state == GoldTierExecutionLedgerState.IN_PROGRESS
                and not entry.attempted_operations
            )
        )
        if target_executions != snapshot.target_executions:
            changed = True
        uncertain_target = any(
            entry.state == GoldTierExecutionLedgerState.IN_PROGRESS
            and bool(entry.attempted_operations)
            for entry in target_executions
        )
        automation = snapshot.automation
        if (
            uncertain_target
            and automation is not None
            and automation.status in {AutomationStatus.RUNNING, AutomationStatus.RESUMING}
            and automation.current_stage == AutomationStage.MOCK_GOLDTIER
        ):
            recovered_automation = automation.model_copy(deep=True)
            recovered_automation.version += 1
            recovered_automation.status = AutomationStatus.RECOVERY_PENDING
            recovered_automation.updated_at = now
            recovered_automation.events.append(
                AutomationEvent(
                    sequence=len(recovered_automation.events) + 1,
                    event_type=AutomationEventType.TARGET_OPERATION_RECOVERY_PENDING,
                    status=AutomationStatus.RECOVERY_PENDING,
                    stage=AutomationStage.MOCK_GOLDTIER,
                    outcome=EventOutcome.PARTIAL,
                    timestamp=now,
                    case_id=recovered_automation.case_id,
                    code="RECOVERY_STATE_UNCERTAIN",
                    message=(
                        "A target operation outcome is uncertain after restart; "
                        "automatic replay is blocked."
                    ),
                )
            )
            automation = recovered_automation
            changed = True
        if not changed:
            return snapshot
        return snapshot.model_copy(
            update={
                "documents": tuple(documents),
                "target_executions": target_executions,
                "automation": automation,
            },
            deep=True,
        )


def _persistence_value(value: object) -> Any:
    """Serialize every declared model field, including backend-only excluded fields."""

    if isinstance(value, BaseModel):
        return {
            name: _persistence_value(getattr(value, name))
            for name in type(value).model_fields
        }
    if isinstance(value, dict):
        return {
            str(key.value if isinstance(key, Enum) else key): _persistence_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_persistence_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _reject_unknown_model_fields(raw: object, parsed: object) -> None:
    """Apply extra-forbid semantics recursively even to historical domain models."""

    if isinstance(parsed, BaseModel):
        if not isinstance(raw, dict):
            raise PersistenceDataInvalidError
        allowed = set(type(parsed).model_fields)
        if set(raw) - allowed:
            raise PersistenceDataInvalidError
        for name in allowed.intersection(raw):
            _reject_unknown_model_fields(raw[name], getattr(parsed, name))
        return
    if isinstance(parsed, (list, tuple)):
        if not isinstance(raw, list) or len(raw) != len(parsed):
            raise PersistenceDataInvalidError
        for raw_item, parsed_item in zip(raw, parsed, strict=True):
            _reject_unknown_model_fields(raw_item, parsed_item)
        return
    if isinstance(parsed, dict):
        if not isinstance(raw, dict) or set(raw) != {
            str(key.value if isinstance(key, Enum) else key) for key in parsed
        }:
            raise PersistenceDataInvalidError
        for key, parsed_item in parsed.items():
            raw_key = str(key.value if isinstance(key, Enum) else key)
            _reject_unknown_model_fields(raw[raw_key], parsed_item)
