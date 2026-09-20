"""Single-document Mongo store for bounded durable CLM case snapshots."""

from __future__ import annotations

import builtins
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.domain.access import TeamId
from app.domain.case_management import CasePortfolioRecord, CasePortfolioScope
from app.domain.documents import (
    DocumentEventType,
    DocumentProcessingState,
    DocumentWorkflowEvent,
)
from app.domain.jurisdiction import JurisdictionCode
from app.domain.models import EventOutcome, SafeError
from app.domain.target_submission import GoldTierExecutionLedgerState
from app.domain.zero_touch import (
    AutomationEvent,
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    validate_automation_record,
)
from app.persistence.errors import (
    PersistenceConflictError,
    PersistenceDataInvalidError,
    PersistenceSchemaUnsupportedError,
    PersistenceUnavailableError,
)
from app.persistence.models import (
    CASE_SNAPSHOT_SCHEMA_VERSION,
    DurableCaseSnapshot,
    DurableCaseSnapshotV1,
    DurableCaseSnapshotV2,
    DurableCaseSnapshotV3,
)


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
            self._collection.create_index(
                [("onboarding.team_id", ASCENDING)], name="onboarding_team_lookup"
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

    def list_portfolio(
        self,
        scope: CasePortfolioScope,
        *,
        status: AutomationStatus | None = None,
    ) -> builtins.list[CasePortfolioRecord]:
        """Read one bounded projection without decoding complete case envelopes."""

        query: dict[str, Any] = {"automation": {"$ne": None}}
        if scope.team_id is not None:
            query["onboarding.team_id"] = str(scope.team_id)
        if status is not None:
            query["automation.status"] = status.value
        projection = {
            "_id": 1,
            "schema_version": 1,
            "case_id": 1,
            "revision": 1,
            "onboarding.case_id": 1,
            "onboarding.team_id": 1,
            "onboarding.priority": 1,
            "onboarding.requested_uen": 1,
            "onboarding.entity.legal_name": 1,
            "onboarding.jurisdiction_resolution.resolved_jurisdiction": 1,
            "onboarding.goldtier_result.party_id": 1,
            "automation.case_id": 1,
            "automation.status": 1,
            "automation.current_stage": 1,
            "automation.created_at": 1,
            "automation.updated_at": 1,
            "automation.completed_at": 1,
            "automation.exceptions.status": 1,
            "automation.metrics.human_interventions": 1,
            "automation.metrics.final_outcome": 1,
        }
        try:
            raw_records = list(self._collection.find(query, projection))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [self._decode_portfolio(item) for item in raw_records]

    def delete(self, case_id: UUID, *, expected_revision: int) -> None:
        try:
            result = self._collection.delete_one(
                {"_id": str(case_id), "revision": expected_revision}
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.deleted_count != 1:
            raise PersistenceConflictError

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
        mongo_id = raw.get("_id")
        if not isinstance(mongo_id, str):
            raise PersistenceDataInvalidError
        try:
            parsed_mongo_id = UUID(mongo_id)
        except (ValueError, TypeError, AttributeError):
            raise PersistenceDataInvalidError from None
        if str(parsed_mongo_id) != mongo_id:
            raise PersistenceDataInvalidError

        value = dict(raw)
        value.pop("_id")
        schema_version = value.get("schema_version")
        if type(schema_version) is not int:
            raise PersistenceDataInvalidError
        try:
            if schema_version == 1:
                legacy_v1 = DurableCaseSnapshotV1.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v1)
                snapshot = legacy_v1.to_current()
            elif schema_version == 2:
                legacy_v2 = DurableCaseSnapshotV2.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v2)
                snapshot = legacy_v2.to_current()
            elif schema_version == 3:
                legacy_v3 = DurableCaseSnapshotV3.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v3)
                snapshot = legacy_v3.to_current()
            elif schema_version == CASE_SNAPSHOT_SCHEMA_VERSION:
                snapshot = DurableCaseSnapshot.model_validate(value)
                _reject_unknown_model_fields(value, snapshot)
            else:
                raise PersistenceSchemaUnsupportedError
            if mongo_id != str(snapshot.case_id):
                raise PersistenceDataInvalidError
            return snapshot
        except PersistenceSchemaUnsupportedError:
            raise
        except PersistenceDataInvalidError:
            raise
        except (ValidationError, ValueError, TypeError):
            raise PersistenceDataInvalidError from None

    def _decode_portfolio(self, raw: dict[str, Any]) -> CasePortfolioRecord:
        """Strictly validate only the bounded fields returned by the projection."""

        try:
            if set(raw) != {
                "_id",
                "schema_version",
                "case_id",
                "revision",
                "onboarding",
                "automation",
            }:
                raise PersistenceDataInvalidError
            schema_version = raw["schema_version"]
            revision = raw["revision"]
            if type(schema_version) is not int or type(revision) is not int or revision < 0:
                raise PersistenceDataInvalidError
            if schema_version not in {1, 2, 3, CASE_SNAPSHOT_SCHEMA_VERSION}:
                raise PersistenceSchemaUnsupportedError
            envelope_id = _canonical_uuid(raw["_id"])
            if _canonical_uuid(raw["case_id"]) != envelope_id:
                raise PersistenceDataInvalidError
            onboarding = _strict_dict(raw["onboarding"])
            automation = _strict_dict(raw["automation"])
            if _canonical_uuid(onboarding.get("case_id")) != envelope_id:
                raise PersistenceDataInvalidError
            if _canonical_uuid(automation.get("case_id")) != envelope_id:
                raise PersistenceDataInvalidError

            required_onboarding = {"case_id", "requested_uen"}
            v2_fields = {"team_id", "priority"}
            optional_onboarding = {"entity", "jurisdiction_resolution", "goldtier_result"}
            keys = set(onboarding)
            if not required_onboarding <= keys or keys - (
                required_onboarding | v2_fields | optional_onboarding
            ):
                raise PersistenceDataInvalidError
            if schema_version == 1:
                if keys & v2_fields:
                    raise PersistenceDataInvalidError
                team_id = None
                priority = None
            else:
                if not v2_fields <= keys:
                    raise PersistenceDataInvalidError
                team_id = (
                    TeamId(onboarding["team_id"]) if onboarding["team_id"] is not None else None
                )
                priority = onboarding["priority"]
                if priority is not None and (
                    type(priority) is not int or priority < 1 or priority > 10
                ):
                    raise PersistenceDataInvalidError

            expected_automation = {
                "case_id",
                "status",
                "current_stage",
                "created_at",
                "updated_at",
                "completed_at",
                "exceptions",
                "metrics",
            }
            if set(automation) != expected_automation:
                raise PersistenceDataInvalidError
            exceptions = automation["exceptions"]
            if not isinstance(exceptions, list):
                raise PersistenceDataInvalidError
            active_count = 0
            for item in exceptions:
                value = _strict_dict(item)
                if set(value) != {"status"}:
                    raise PersistenceDataInvalidError
                status_value = BusinessExceptionStatus(value["status"])
                active_count += status_value == BusinessExceptionStatus.OPEN
            metrics = _strict_dict(automation["metrics"])
            if set(metrics) != {"human_interventions", "final_outcome"}:
                raise PersistenceDataInvalidError
            interventions = metrics["human_interventions"]
            if type(interventions) is not int or interventions < 0:
                raise PersistenceDataInvalidError

            return CasePortfolioRecord(
                case_id=envelope_id,
                requested_uen=_bounded_string(onboarding["requested_uen"], 32),
                legal_name=_nested_optional_string(onboarding.get("entity"), "legal_name", 512),
                resolved_jurisdiction=_nested_optional_enum(
                    onboarding.get("jurisdiction_resolution"),
                    "resolved_jurisdiction",
                    JurisdictionCode,
                ),
                team_id=team_id,
                priority=priority,
                status=AutomationStatus(automation["status"]),
                current_stage=AutomationStage(automation["current_stage"]),
                created_at=_utc_datetime(automation["created_at"]),
                updated_at=_utc_datetime(automation["updated_at"]),
                completed_at=(
                    _utc_datetime(automation["completed_at"])
                    if automation["completed_at"] is not None
                    else None
                ),
                active_exception_count=active_count,
                human_interventions=interventions,
                final_outcome=_optional_bounded_string(metrics["final_outcome"], 64),
                mock_goldtier_party_id=_nested_optional_string(
                    onboarding.get("goldtier_result"), "party_id", 96
                ),
            )
        except PersistenceSchemaUnsupportedError:
            raise
        except PersistenceDataInvalidError:
            raise
        except (KeyError, TypeError, ValueError, ValidationError):
            raise PersistenceDataInvalidError from None

    def _recover_interrupted(self, snapshot: DurableCaseSnapshot) -> DurableCaseSnapshot:
        """Conservatively classify state whose transient inputs/outcome were lost."""

        now = datetime.now(UTC)
        documents = []
        changed = False
        current_document_reupload_required = False
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
                    message=("Interrupted processing requires explicit document re-upload."),
                )
            )
            documents.append(recovered)
            if recovered.is_current_evidence:
                current_document_reupload_required = True
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
        elif (
            current_document_reupload_required
            and automation is not None
            and automation.status
            not in {
                AutomationStatus.COMPLETED,
                AutomationStatus.TECHNICAL_FAILURE,
                AutomationStatus.RECOVERY_PENDING,
            }
            and automation.current_stage == AutomationStage.DOCUMENT
        ):
            recovered_automation = automation.model_copy(deep=True)
            recovered_automation.version += 1
            recovered_automation.status = AutomationStatus.PENDING_INPUTS
            recovered_automation.current_stage = AutomationStage.DOCUMENT
            recovered_automation.completed_stages = (AutomationStage.REGISTRY,)
            recovered_automation.technical_failure = None
            recovered_automation.completed_at = None
            for exception in recovered_automation.active_exceptions:
                exception.status = BusinessExceptionStatus.CANCELLED
            recovered_automation.updated_at = now
            recovered_automation.events.append(
                AutomationEvent(
                    sequence=len(recovered_automation.events) + 1,
                    event_type=AutomationEventType.DOCUMENT_REUPLOAD_REQUIRED,
                    status=AutomationStatus.PENDING_INPUTS,
                    stage=AutomationStage.DOCUMENT,
                    outcome=EventOutcome.PARTIAL,
                    timestamp=now,
                    case_id=recovered_automation.case_id,
                    code="DOCUMENT_REUPLOAD_REQUIRED",
                    message=(
                        "Interrupted document processing requires targeted re-upload "
                        "before onboarding can continue."
                    ),
                )
            )
            validate_automation_record(recovered_automation)
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
        return {name: _persistence_value(getattr(value, name)) for name in type(value).model_fields}
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


def _strict_dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PersistenceDataInvalidError
    return value


def _canonical_uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise PersistenceDataInvalidError
    parsed = UUID(value)
    if str(parsed) != value:
        raise PersistenceDataInvalidError
    return parsed


def _bounded_string(value: object, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise PersistenceDataInvalidError
    return value


def _optional_bounded_string(value: object, maximum: int) -> str | None:
    if value is None:
        return None
    return _bounded_string(value, maximum)


def _nested_optional_string(
    container: object,
    field: str,
    maximum: int,
) -> str | None:
    if container is None:
        return None
    value = _strict_dict(container)
    if set(value) != {field}:
        raise PersistenceDataInvalidError
    return _optional_bounded_string(value[field], maximum)


def _nested_optional_enum(
    container: object,
    field: str,
    enum_type: type[Enum],
) -> Any:
    if container is None:
        return None
    value = _strict_dict(container)
    if set(value) != {field}:
        raise PersistenceDataInvalidError
    return enum_type(value[field]) if value[field] is not None else None


def _utc_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise PersistenceDataInvalidError
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    if parsed.utcoffset() != timedelta(0):
        raise PersistenceDataInvalidError
    return parsed.astimezone(UTC)
