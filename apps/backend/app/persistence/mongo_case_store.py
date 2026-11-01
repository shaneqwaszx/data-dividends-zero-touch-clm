"""Single-document Mongo store for bounded durable CLM case snapshots."""

from __future__ import annotations

import builtins
from collections.abc import Callable, Iterator
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
from app.domain.case_management import (
    CaseActivityAction,
    CaseActivityQuery,
    CaseActivityRepositoryPage,
    CaseActivityRepositoryRecord,
    CasePortfolioPage,
    CasePortfolioQuery,
    CasePortfolioRecord,
    CasePortfolioScope,
    PortfolioScopeKind,
    PriorityFilter,
    PrioritySort,
    case_portfolio_search_pattern,
    ordered_active_exception_types,
)
from app.domain.documents import (
    DocumentEventType,
    DocumentProcessingState,
    DocumentWorkflowEvent,
)
from app.domain.jurisdiction import JurisdictionCode
from app.domain.models import EventOutcome, SafeError
from app.domain.target_submission import GoldTierExecutionLedgerState
from app.domain.zero_touch import (
    LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
    AutomationEvent,
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
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
    DurableCaseSnapshotV4,
    DurableCaseSnapshotV5,
    DurableCaseSnapshotV6,
    DurableCaseSnapshotV7,
    DurableCaseSnapshotV8,
    DurableCaseSnapshotV9,
    DurableCaseSnapshotV10,
    DurableCaseSnapshotV11,
    DurableCaseSnapshotV12,
    DurableCaseSnapshotV13,
    DurableCaseSnapshotV14,
    DurableCaseSnapshotV15,
    DurableCaseSnapshotV16,
    DurableCaseSnapshotV17,
    _validate_case_bindings,
    reject_classification_legacy_fields,
    reject_document_digest_legacy_fields,
    reject_entity_category_legacy_fields,
    reject_entity_type_legacy_fields,
    reject_hybrid_overlay_legacy_fields,
    reject_official_shareholder_legacy_fields,
    reject_ownership_discovery_legacy_fields,
    reject_scenario_poc_legacy_fields,
    reject_session2_legacy_fields,
    reject_share_class_legacy_fields,
)

_SUPPORTED_SCHEMA_VERSIONS = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, CASE_SNAPSHOT_SCHEMA_VERSION
]


class CapturedCaseBatch:
    """Opaque one-shot store read; raw envelopes never leave this boundary."""

    def __init__(
        self, authorized: frozenset[UUID], raw_records: list[dict[str, Any]],
        decode: Callable[[dict[str, Any]], DurableCaseSnapshot],
    ) -> None:
        self._authorized = authorized
        self._raw_records = raw_records
        self._decode: Callable[[dict[str, Any]], DurableCaseSnapshot] | None = decode

    def close(self) -> None:
        self._authorized = frozenset()
        self._raw_records.clear()
        self._decode = None

    def read_selected(self, case_ids: frozenset[UUID]) -> list[DurableCaseSnapshot]:
        decode = self._decode
        if decode is None:
            raise ValueError("case batch is closed")
        try:
            if (type(case_ids) is not frozenset
                    or any(type(value) is not UUID for value in case_ids)
                    or not case_ids <= self._authorized):
                raise ValueError("invalid case batch selection")
            selected = {str(value): value for value in case_ids}
            authorized = {str(value) for value in self._authorized}
            seen: set[UUID] = set()
            snapshots = []
            for raw in self._raw_records:
                # Mongo's canonical _id alone routes the captured raw batch. Never
                # inspect excluded nested/schema data before final cohort selection.
                key = raw.get("_id")
                if type(key) is not str or key not in authorized:
                    raise PersistenceDataInvalidError
                if key not in selected:
                    continue
                case_id = selected[key]
                if case_id in seen:
                    raise PersistenceDataInvalidError
                snapshot = decode(raw)
                if snapshot.case_id != case_id:
                    raise PersistenceDataInvalidError
                seen.add(case_id)
                snapshots.append(snapshot)
            return snapshots
        finally:
            self.close()


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
        """Decode a fresh caller-owned envelope on every read; retain no model cache."""
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

    @contextmanager
    def capture_for_cases(self, case_ids: frozenset[UUID]) -> Iterator[CapturedCaseBatch]:
        """Materialize one authorized-ID raw read before yielding, without decoding."""
        if type(case_ids) is not frozenset or any(type(value) is not UUID for value in case_ids):
            raise ValueError("invalid case batch selection")
        raw_records: builtins.list[dict[str, Any]] = []
        cursor = None
        try:
            try:
                if case_ids:
                    cursor = self._collection.find({"_id": {"$in": sorted(map(str, case_ids))}})
                    raw_records = builtins.list(cursor)
            finally:
                if cursor is not None:
                    cursor.close()
        except PyMongoError:
            raw_records.clear()
            raise PersistenceUnavailableError from None
        batch = CapturedCaseBatch(case_ids, raw_records, self._decode)
        try:
            yield batch
        finally:
            batch.close()

    def list_portfolio(
        self,
        scope: CasePortfolioScope,
        *,
        status: AutomationStatus | None = None,
    ) -> builtins.list[CasePortfolioRecord]:
        """Read one bounded projection without decoding complete case envelopes."""

        query: dict[str, Any] = {"automation": {"$ne": None}}
        if scope.kind == PortfolioScopeKind.TEAM:
            query["onboarding.team_id"] = str(scope.team_id)
        elif scope.kind == PortfolioScopeKind.UNASSIGNED:
            query["onboarding.team_id"] = None
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
        "onboarding.created_by_actor_id": 1,
            "onboarding.requested_uen": 1,
            "onboarding.entity.legal_name": 1,
            "onboarding.jurisdiction_resolution.resolved_jurisdiction": 1,
            "onboarding.goldtier_result.party_id": 1,
            "automation.case_id": 1,
            "automation.status": 1,
            "automation.current_stage": 1,
            "automation.created_at": 1,
            "automation.updated_at": 1,
            "automation.started_at": 1,
            "automation.completed_at": 1,
            "automation.exceptions.status": 1,
            "automation.exceptions.exception_type": 1,
            "automation.metrics.human_interventions": 1,
            "automation.metrics.final_outcome": 1,
            "automation.metrics.total_duration_ms": 1,
        }
        try:
            raw_records = list(self._collection.find(query, projection))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [self._decode_portfolio(item) for item in raw_records]

    def list_portfolio_page(self, query: CasePortfolioQuery) -> CasePortfolioPage:
        """Read one strict filtered portfolio page with one bounded aggregation."""

        candidate_match: dict[str, Any] = {"automation": {"$ne": None}}
        if query.scope.kind == PortfolioScopeKind.TEAM:
            candidate_match["onboarding.team_id"] = str(query.scope.team_id)
        elif query.scope.kind == PortfolioScopeKind.UNASSIGNED:
            candidate_match["onboarding.team_id"] = None
        projection = _portfolio_projection()
        valid_candidate = _portfolio_candidate_valid_expression()
        source_valid = _portfolio_source_container_valid_expression()
        pipeline: list[dict[str, Any]] = [
            {"$match": candidate_match},
            {"$set": {"_portfolio_source_valid": source_valid}},
            {"$project": {**projection, "_portfolio_source_valid": 1}},
            {
                "$facet": {
                    "invalid": [
                        {
                            "$match": {
                                "$expr": {
                                    "$not": [
                                        {
                                            "$and": [
                                                "$_portfolio_source_valid",
                                                valid_candidate,
                                            ]
                                        }
                                    ]
                                }
                            }
                        },
                        {"$limit": 1},
                        {"$project": {"_id": 0, "invalid": {"$literal": True}}},
                    ],
                    "rows": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        "$_portfolio_source_valid",
                                        valid_candidate,
                                    ]
                                }
                            }
                        },
                        {"$match": _portfolio_row_match(query)},
                        {
                            "$set": {
                                "_priority_unset": {
                                    "$cond": [
                                        {
                                            "$in": [
                                                {"$type": "$onboarding.priority"},
                                                ["missing", "null"],
                                            ]
                                        },
                                        1,
                                        0,
                                    ]
                                },
                                "_priority_value": {"$ifNull": ["$onboarding.priority", 0]},
                                "_sort_updated_at": (
                                    _normalized_activity_timestamp_expression(
                                        "$automation.updated_at"
                                    )
                                ),
                            }
                        },
                        {
                            "$sort": {
                                "_priority_unset": ASCENDING,
                                "_priority_value": (
                                    DESCENDING
                                    if query.priority_sort == PrioritySort.HIGHEST_FIRST
                                    else ASCENDING
                                ),
                                "_sort_updated_at": DESCENDING,
                                "case_id": DESCENDING,
                            }
                        },
                        {"$skip": query.offset},
                        {"$limit": query.limit + 1},
                        {"$project": projection},
                    ],
                }
            },
        ]
        try:
            result = list(
                self._collection.aggregate(
                    pipeline,
                    allowDiskUse=False,
                    maxTimeMS=5_000,
                )
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if len(result) != 1 or set(result[0]) != {"invalid", "rows"}:
            raise PersistenceDataInvalidError
        invalid = result[0]["invalid"]
        rows = result[0]["rows"]
        if not isinstance(invalid, list) or not isinstance(rows, list) or invalid:
            raise PersistenceDataInvalidError
        if len(rows) > query.limit + 1:
            raise PersistenceDataInvalidError
        decoded = [self._decode_portfolio(row) for row in rows]
        return CasePortfolioPage(
            items=tuple(decoded[: query.limit]),
            offset=query.offset,
            limit=query.limit,
            has_more=len(decoded) > query.limit,
        )

    def list_activity(self, query: CaseActivityQuery) -> CaseActivityRepositoryPage:
        """Read one strict retained-event page with one bounded aggregation."""

        candidate_match: dict[str, Any] = {"automation": {"$ne": None}}
        if query.scope.kind == PortfolioScopeKind.TEAM:
            candidate_match["onboarding.team_id"] = str(query.scope.team_id)
        elif query.scope.kind == PortfolioScopeKind.UNASSIGNED:
            candidate_match["onboarding.team_id"] = None
        if query.case_id is not None:
            candidate_match["_id"] = str(query.case_id)

        valid_candidate = _activity_candidate_valid_expression()
        row_match = _activity_row_match(query)
        pipeline: list[dict[str, Any]] = [
            {"$match": candidate_match},
            {
                "$project": {
                    "_id": 1,
                    "schema_version": 1,
                    "case_id": 1,
                    "revision": 1,
                    "onboarding.case_id": 1,
                    "onboarding.team_id": 1,
                    "onboarding.priority": 1,
                    "onboarding.created_by_actor_id": 1,
                    "automation.case_id": 1,
                    "automation.events": 1,
                }
            },
            {
                "$facet": {
                    "invalid": [
                        {"$match": {"$expr": {"$not": [valid_candidate]}}},
                        {"$limit": 1},
                        {"$project": {"_id": 0, "invalid": {"$literal": True}}},
                    ],
                    "rows": [
                        {"$match": {"$expr": valid_candidate}},
                        # Validate the authorized envelope before creator filtering.
                        *(
                            [{"$match": {"onboarding.created_by_actor_id": query.created_by}}]
                            if query.created_by is not None else []
                        ),
                        {"$unwind": "$automation.events"},
                        {"$match": row_match},
                        {
                            "$set": {
                                "_sort_timestamp": _normalized_activity_timestamp_expression(
                                    "$automation.events.timestamp"
                                )
                            }
                        },
                        {
                            "$sort": {
                                "_sort_timestamp": DESCENDING,
                                "case_id": ASCENDING,
                                "automation.events.sequence": DESCENDING,
                            }
                        },
                        {"$skip": query.offset},
                        {"$limit": query.limit + 1},
                        {
                            "$project": {
                                "_id": 0,
                                "case_id": 1,
                                "sequence": "$automation.events.sequence",
                                "timestamp": "$automation.events.timestamp",
                                "event_type": "$automation.events.event_type",
                                "status": "$automation.events.status",
                                "stage": "$automation.events.stage",
                                "outcome": "$automation.events.outcome",
                                "code": "$automation.events.code",
                                "message": "$automation.events.message",
                                "team_id": "$onboarding.team_id",
                                "current_priority": "$onboarding.priority",
                            }
                        },
                    ],
                }
            },
        ]
        try:
            result = list(
                self._collection.aggregate(
                    pipeline,
                    allowDiskUse=False,
                    maxTimeMS=5_000,
                )
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if len(result) != 1 or set(result[0]) != {"invalid", "rows"}:
            raise PersistenceDataInvalidError
        invalid = result[0]["invalid"]
        rows = result[0]["rows"]
        if not isinstance(invalid, list) or not isinstance(rows, list) or invalid:
            raise PersistenceDataInvalidError
        if len(rows) > query.limit + 1:
            raise PersistenceDataInvalidError
        decoded = [self._decode_activity_record(row) for row in rows]
        return CaseActivityRepositoryPage(
            items=tuple(decoded[: query.limit]),
            offset=query.offset,
            limit=query.limit,
            has_more=len(decoded) > query.limit,
        )

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
                {
                    "_id": str(candidate.case_id),
                    "revision": expected_revision,
                    "onboarding.created_by_actor_id": candidate.onboarding.created_by_actor_id,
                },
                self._encode(candidate),
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.modified_count != 1:
            raise PersistenceConflictError
        return candidate.model_copy(deep=True)

    def _encode(self, snapshot: DurableCaseSnapshot) -> dict[str, Any]:
        try:
            # Reuse the durable serializer: model_dump omits backend-only bindings.
            validated = DurableCaseSnapshot.model_validate(_persistence_value(snapshot))
        except (ValidationError, ValueError, TypeError):
            raise PersistenceDataInvalidError from None
        _validate_case_bindings(validated)
        raw_value = _persistence_value(validated)
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
        automation_value = value.get("automation")
        if (
            schema_version
            in {
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
                CASE_SNAPSHOT_SCHEMA_VERSION,
            }
            and isinstance(automation_value, dict)
            and "stage_order_version" not in automation_value
        ):
            value["automation"] = {
                **automation_value,
                "stage_order_version": LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
            }
        try:
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}:
                reject_entity_category_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}:
                reject_entity_type_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15}:
                reject_document_digest_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14}:
                reject_scenario_poc_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}:
                reject_share_class_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}:
                reject_official_shareholder_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}:
                reject_hybrid_overlay_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}:
                reject_ownership_discovery_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8, 9}:
                reject_classification_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7, 8}:
                reject_session2_legacy_fields(value)
            if schema_version in {1, 2, 3, 4, 5, 6, 7}:
                _reject_phase24c_legacy_values(value)
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
            elif schema_version == 4:
                legacy_v4 = DurableCaseSnapshotV4.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v4)
                snapshot = legacy_v4.to_current()
            elif schema_version == 5:
                legacy_v5 = DurableCaseSnapshotV5.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v5)
                snapshot = legacy_v5.to_current()
            elif schema_version == 6:
                legacy_v6 = DurableCaseSnapshotV6.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v6)
                snapshot = legacy_v6.to_current()
            elif schema_version == 7:
                legacy_v7 = DurableCaseSnapshotV7.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v7)
                snapshot = legacy_v7.to_current()
            elif schema_version == 8:
                legacy_v8 = DurableCaseSnapshotV8.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v8)
                snapshot = legacy_v8.to_current()
            elif schema_version == 9:
                legacy_v9 = DurableCaseSnapshotV9.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v9)
                snapshot = legacy_v9.to_current()
            elif schema_version == 10:
                legacy_v10 = DurableCaseSnapshotV10.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v10)
                snapshot = legacy_v10.to_current()
            elif schema_version == 11:
                legacy_v11 = DurableCaseSnapshotV11.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v11)
                snapshot = legacy_v11.to_current()
            elif schema_version == 12:
                legacy_v12 = DurableCaseSnapshotV12.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v12)
                snapshot = legacy_v12.to_current()
            elif schema_version == 13:
                legacy_v13 = DurableCaseSnapshotV13.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v13)
                snapshot = legacy_v13.to_current()
            elif schema_version == 14:
                legacy_v14 = DurableCaseSnapshotV14.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v14)
                snapshot = legacy_v14.to_current()
            elif schema_version == 15:
                legacy_v15 = DurableCaseSnapshotV15.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v15)
                snapshot = legacy_v15.to_current()
            elif schema_version == 16:
                legacy_v16 = DurableCaseSnapshotV16.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v16)
                snapshot = legacy_v16.to_current()
            elif schema_version == 17:
                legacy_v17 = DurableCaseSnapshotV17.model_validate(value)
                _reject_unknown_model_fields(value, legacy_v17)
                snapshot = legacy_v17.to_current()
            elif schema_version == CASE_SNAPSHOT_SCHEMA_VERSION:
                snapshot = DurableCaseSnapshot.model_validate(value)
                _reject_unknown_model_fields(value, snapshot)
            else:
                raise PersistenceSchemaUnsupportedError
            if mongo_id != str(snapshot.case_id):
                raise PersistenceDataInvalidError
            if snapshot.automation is not None:
                validate_automation_record(snapshot.automation)
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
            if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
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
            if schema_version >= 9:
                optional_onboarding.add("created_by_actor_id")
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
                "started_at",
                "completed_at",
                "exceptions",
                "metrics",
            }
            optional_timing = {"started_at"}
            if (
                not expected_automation - optional_timing <= set(automation)
                or set(automation) - expected_automation
            ):
                raise PersistenceDataInvalidError
            exceptions = automation["exceptions"]
            if not isinstance(exceptions, list):
                raise PersistenceDataInvalidError
            active_count = 0
            exception_pairs: list[tuple[BusinessExceptionStatus, BusinessExceptionType]] = []
            for item in exceptions:
                value = _strict_dict(item)
                if set(value) != {"status", "exception_type"}:
                    raise PersistenceDataInvalidError
                status_value = BusinessExceptionStatus(value["status"])
                exception_type = BusinessExceptionType(value["exception_type"])
                exception_pairs.append((status_value, exception_type))
                active_count += status_value == BusinessExceptionStatus.OPEN
            metrics = _strict_dict(automation["metrics"])
            required_metrics = {"human_interventions", "final_outcome"}
            optional_timing_metrics = {"total_duration_ms"}
            if not required_metrics <= set(metrics) or set(metrics) - (
                required_metrics | optional_timing_metrics
            ):
                raise PersistenceDataInvalidError
            interventions = metrics["human_interventions"]
            if type(interventions) is not int or interventions < 0:
                raise PersistenceDataInvalidError
            total_duration_ms = metrics.get("total_duration_ms")
            if total_duration_ms is not None and (
                type(total_duration_ms) is not int or total_duration_ms < 0
            ):
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
                created_by_actor_id=onboarding.get("created_by_actor_id"),
                status=AutomationStatus(automation["status"]),
                current_stage=AutomationStage(automation["current_stage"]),
                created_at=_utc_datetime(automation["created_at"]),
                updated_at=_utc_datetime(automation["updated_at"]),
                started_at=(
                    _utc_datetime(automation["started_at"])
                    if automation.get("started_at") is not None
                    else None
                ),
                completed_at=(
                    _utc_datetime(automation["completed_at"])
                    if automation["completed_at"] is not None
                    else None
                ),
                active_exception_count=active_count,
                active_exception_types=ordered_active_exception_types(exception_pairs),
                human_interventions=interventions,
                final_outcome=_optional_bounded_string(metrics["final_outcome"], 64),
                recorded_total_duration_ms=total_duration_ms,
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

    def _decode_activity_record(self, raw: dict[str, Any]) -> CaseActivityRepositoryRecord:
        expected = {
            "case_id",
            "sequence",
            "timestamp",
            "event_type",
            "status",
            "stage",
            "outcome",
            "code",
            "message",
        }
        optional = {"team_id", "current_priority"}
        try:
            if (
                not isinstance(raw, dict)
                or set(raw) - (expected | optional)
                or not expected <= set(raw)
            ):
                raise PersistenceDataInvalidError
            return CaseActivityRepositoryRecord(
                case_id=_canonical_uuid(raw["case_id"]),
                sequence=raw["sequence"],
                timestamp=_utc_datetime(raw["timestamp"]),
                event_type=AutomationEventType(raw["event_type"]),
                status=AutomationStatus(raw["status"]),
                stage=AutomationStage(raw["stage"]),
                outcome=EventOutcome(raw["outcome"]),
                code=raw["code"],
                message=raw["message"],
                team_id=TeamId(raw["team_id"]) if raw.get("team_id") is not None else None,
                current_priority=raw.get("current_priority"),
            )
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
            and entry.attempted_operations != entry.definitively_completed_operations
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
            recovered_automation.completed_stages = (
                (AutomationStage.REGISTRY,)
                if recovered_automation.stage_order_version == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
                else (
                    AutomationStage.REGISTRY,
                    AutomationStage.GOLDTIER_SEARCH,
                )
            )
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
    if isinstance(value, (set, frozenset)):
        return sorted(
            (_persistence_value(item) for item in value),
            key=repr,
        )
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
        fields = type(parsed).model_fields
        if raw.keys() - fields.keys():
            raise PersistenceDataInvalidError
        for name, raw_item in raw.items():
            parsed_item = getattr(parsed, name)
            if isinstance(parsed_item, (BaseModel, list, tuple, dict)):
                _reject_unknown_model_fields(raw_item, parsed_item)
        return
    if isinstance(parsed, (list, tuple)):
        if not isinstance(raw, list) or len(raw) != len(parsed):
            raise PersistenceDataInvalidError
        for raw_item, parsed_item in zip(raw, parsed, strict=True):
            if isinstance(parsed_item, (BaseModel, list, tuple, dict)):
                _reject_unknown_model_fields(raw_item, parsed_item)
        return
    if isinstance(parsed, dict):
        if not isinstance(raw, dict) or set(raw) != {
            str(key.value if isinstance(key, Enum) else key) for key in parsed
        }:
            raise PersistenceDataInvalidError
        for key, parsed_item in parsed.items():
            raw_key = str(key.value if isinstance(key, Enum) else key)
            if isinstance(parsed_item, (BaseModel, list, tuple, dict)):
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


def _mongo_bounded_string(value: str, minimum: int, maximum: int) -> dict[str, Any]:
    value_type = {"$type": value}
    safe_value = {"$cond": [{"$eq": [value_type, "string"]}, value, ""]}
    return {
        "$and": [
            {"$eq": [value_type, "string"]},
            {"$gte": [{"$strLenCP": safe_value}, minimum]},
            {"$lte": [{"$strLenCP": safe_value}, maximum]},
        ]
    }


def _mongo_canonical_uuid(value: str) -> dict[str, Any]:
    value_type = {"$type": value}
    safe_value = {"$cond": [{"$eq": [value_type, "string"]}, value, ""]}
    return {
        "$and": [
            {"$eq": [value_type, "string"]},
            {
                "$regexMatch": {
                    "input": safe_value,
                    "regex": ("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"),
                }
            },
        ]
    }


def _mongo_activity_timestamp(value: str) -> dict[str, Any]:
    value_type = {"$type": value}
    safe_value = {"$cond": [{"$eq": [value_type, "string"]}, value, ""]}
    return {
        "$and": [
            {"$eq": [value_type, "string"]},
            {
                "$regexMatch": {
                    "input": safe_value,
                    "regex": (
                        "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]{6})?Z$"
                    ),
                }
            },
            {
                "$ne": [
                    {
                        "$dateFromString": {
                            "dateString": safe_value,
                            "onError": None,
                            "onNull": None,
                        }
                    },
                    None,
                ]
            },
        ]
    }


def _portfolio_projection() -> dict[str, int]:
    return {
        "_id": 1,
        "schema_version": 1,
        "case_id": 1,
        "revision": 1,
        "onboarding.case_id": 1,
        "onboarding.team_id": 1,
        "onboarding.priority": 1,
        "onboarding.created_by_actor_id": 1,
        "onboarding.requested_uen": 1,
        "onboarding.entity.legal_name": 1,
        "onboarding.jurisdiction_resolution.resolved_jurisdiction": 1,
        "onboarding.goldtier_result.party_id": 1,
        "automation.case_id": 1,
        "automation.status": 1,
        "automation.current_stage": 1,
        "automation.created_at": 1,
        "automation.updated_at": 1,
        "automation.started_at": 1,
        "automation.completed_at": 1,
        "automation.exceptions.status": 1,
        "automation.exceptions.exception_type": 1,
        "automation.metrics.human_interventions": 1,
        "automation.metrics.final_outcome": 1,
        "automation.metrics.total_duration_ms": 1,
    }


def _mongo_exact_object_keys(value: str, expected: list[str]) -> dict[str, Any]:
    value_type = {"$type": value}
    safe_value = {"$cond": [{"$eq": [value_type, "object"]}, value, {}]}
    keys = {
        "$map": {
            "input": {"$objectToArray": safe_value},
            "as": "pair",
            "in": "$$pair.k",
        }
    }
    return {
        "$and": [
            {"$eq": [value_type, "object"]},
            {"$setEquals": [keys, expected]},
        ]
    }


def _mongo_optional_projected_string(
    container: str,
    field: str,
    *,
    maximum: int,
) -> dict[str, Any]:
    container_type = {"$type": container}
    value = f"{container}.{field}"
    value_type = {"$type": value}
    return {
        "$or": [
            {"$in": [container_type, ["missing", "null"]]},
            {
                "$and": [
                    _mongo_exact_object_keys(container, [field]),
                    {
                        "$or": [
                            {"$eq": [value_type, "null"]},
                            _mongo_bounded_string(value, 1, maximum),
                        ]
                    },
                ]
            },
        ]
    }


def _portfolio_exception_valid_expression() -> dict[str, Any]:
    item_type = {"$type": "$$exception"}
    safe_item = {"$cond": [{"$eq": [item_type, "object"]}, "$$exception", {}]}
    keys = {
        "$map": {
            "input": {"$objectToArray": safe_item},
            "as": "pair",
            "in": "$$pair.k",
        }
    }
    return {
        "$and": [
            {"$eq": [item_type, "object"]},
            {"$setEquals": [keys, ["status", "exception_type"]]},
            {
                "$in": [
                    "$$exception.status",
                    [item.value for item in BusinessExceptionStatus],
                ]
            },
            {
                "$in": [
                    "$$exception.exception_type",
                    [item.value for item in BusinessExceptionType],
                ]
            },
        ]
    }


def _creator_valid_expression() -> dict[str, Any]:
    value = "$onboarding.created_by_actor_id"
    value_type = {"$type": value}
    return {
        "$cond": [
            {"$lt": ["$schema_version", 9]},
            {"$eq": [value_type, "missing"]},
            {"$or": [
                {"$in": [value_type, ["missing", "null"]]},
                {"$and": [
                    {"$eq": [value_type, "string"]},
                    {"$regexMatch": {
                        "input": {"$cond": [{"$eq": [value_type, "string"]}, value, ""]},
                        "regex": "^[a-z][a-z0-9-]{2,31}$",
                    }},
                ]},
            ]},
        ]
    }


def _portfolio_candidate_valid_expression() -> dict[str, Any]:
    schema_type = {"$type": "$schema_version"}
    revision_type = {"$type": "$revision"}
    team_type = {"$type": "$onboarding.team_id"}
    priority_type = {"$type": "$onboarding.priority"}
    exceptions_type = {"$type": "$automation.exceptions"}
    safe_exceptions = {
        "$cond": [
            {"$eq": [exceptions_type, "array"]},
            "$automation.exceptions",
            [],
        ]
    }
    completed_type = {"$type": "$automation.completed_at"}
    started_type = {"$type": "$automation.started_at"}
    final_outcome_type = {"$type": "$automation.metrics.final_outcome"}
    total_duration_type = {"$type": "$automation.metrics.total_duration_ms"}
    jurisdiction_type = {"$type": "$onboarding.jurisdiction_resolution.resolved_jurisdiction"}
    return {
        "$and": [
            _creator_valid_expression(),
            {"$in": [schema_type, ["int", "long"]]},
            {"$in": ["$schema_version", _SUPPORTED_SCHEMA_VERSIONS]},
            {"$in": [revision_type, ["int", "long"]]},
            {"$gte": ["$revision", 0]},
            _mongo_canonical_uuid("$_id"),
            _mongo_canonical_uuid("$case_id"),
            {"$eq": ["$_id", "$case_id"]},
            _mongo_canonical_uuid("$onboarding.case_id"),
            {"$eq": ["$onboarding.case_id", "$case_id"]},
            _mongo_canonical_uuid("$automation.case_id"),
            {"$eq": ["$automation.case_id", "$case_id"]},
            _mongo_bounded_string("$onboarding.requested_uen", 1, 32),
            {
                "$cond": [
                    {"$eq": ["$schema_version", 1]},
                    {"$eq": [team_type, "missing"]},
                    {
                        "$or": [
                            {"$eq": [team_type, "null"]},
                            {
                                "$and": [
                                    {"$eq": [team_type, "string"]},
                                    {
                                        "$regexMatch": {
                                            "input": {
                                                "$cond": [
                                                    {"$eq": [team_type, "string"]},
                                                    "$onboarding.team_id",
                                                    "",
                                                ]
                                            },
                                            "regex": "^(TEAM_A|TEAM_B|TEAM_[0-9A-F]{24})$",
                                        }
                                    },
                                ]
                            },
                        ]
                    },
                ]
            },
            {
                "$cond": [
                    {"$eq": ["$schema_version", 1]},
                    {"$eq": [priority_type, "missing"]},
                    {
                        "$or": [
                            {"$eq": [priority_type, "null"]},
                            {
                                "$and": [
                                    {"$in": [priority_type, ["int", "long"]]},
                                    {"$gte": ["$onboarding.priority", 1]},
                                    {"$lte": ["$onboarding.priority", 10]},
                                ]
                            },
                        ]
                    },
                ]
            },
            _mongo_optional_projected_string("$onboarding.entity", "legal_name", maximum=512),
            {
                "$or": [
                    {
                        "$in": [
                            {"$type": "$onboarding.jurisdiction_resolution"},
                            ["missing", "null"],
                        ]
                    },
                    {
                        "$and": [
                            _mongo_exact_object_keys(
                                "$onboarding.jurisdiction_resolution",
                                ["resolved_jurisdiction"],
                            ),
                            {
                                "$or": [
                                    {"$eq": [jurisdiction_type, "null"]},
                                    {
                                        "$in": [
                                            (
                                                "$onboarding.jurisdiction_resolution."
                                                "resolved_jurisdiction"
                                            ),
                                            [item.value for item in JurisdictionCode],
                                        ]
                                    },
                                ]
                            },
                        ]
                    },
                ]
            },
            _mongo_optional_projected_string("$onboarding.goldtier_result", "party_id", maximum=96),
            {"$in": ["$automation.status", [item.value for item in AutomationStatus]]},
            {
                "$in": [
                    "$automation.current_stage",
                    [item.value for item in AutomationStage],
                ]
            },
            _mongo_activity_timestamp("$automation.created_at"),
            _mongo_activity_timestamp("$automation.updated_at"),
            {
                "$or": [
                    {"$eq": [started_type, "missing"]},
                    {"$eq": [started_type, "null"]},
                    _mongo_activity_timestamp("$automation.started_at"),
                ]
            },
            {
                "$or": [
                    {"$eq": [completed_type, "null"]},
                    _mongo_activity_timestamp("$automation.completed_at"),
                ]
            },
            {"$eq": [exceptions_type, "array"]},
            {
                "$allElementsTrue": {
                    "$map": {
                        "input": safe_exceptions,
                        "as": "exception",
                        "in": _portfolio_exception_valid_expression(),
                    }
                }
            },
            {
                "$or": [
                    _mongo_exact_object_keys(
                        "$automation.metrics",
                        ["human_interventions", "final_outcome"],
                    ),
                    _mongo_exact_object_keys(
                        "$automation.metrics",
                        ["human_interventions", "final_outcome", "total_duration_ms"],
                    ),
                ]
            },
            {
                "$in": [
                    {"$type": "$automation.metrics.human_interventions"},
                    ["int", "long"],
                ]
            },
            {"$gte": ["$automation.metrics.human_interventions", 0]},
            {
                "$or": [
                    {"$eq": [final_outcome_type, "null"]},
                    _mongo_bounded_string("$automation.metrics.final_outcome", 1, 64),
                ]
            },
            {
                "$or": [
                    {"$eq": [total_duration_type, "missing"]},
                    {"$eq": [total_duration_type, "null"]},
                    {
                        "$and": [
                            {"$in": [total_duration_type, ["int", "long"]]},
                            {"$gte": ["$automation.metrics.total_duration_ms", 0]},
                        ]
                    },
                ]
            },
        ]
    }


def _portfolio_source_container_valid_expression() -> dict[str, Any]:
    """Validate optional source container types before projection can erase them."""

    return {
        "$and": [
            {
                "$in": [
                    {"$type": path},
                    ["missing", "null", "object"],
                ]
            }
            for path in (
                "$onboarding.entity",
                "$onboarding.jurisdiction_resolution",
                "$onboarding.goldtier_result",
            )
        ]
    }


def _portfolio_row_match(query: CasePortfolioQuery) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = []
    if query.status is not None:
        conditions.append({"automation.status": query.status.value})
    if query.progress == "onboarded":
        conditions.append({"automation.status": AutomationStatus.COMPLETED.value})
    elif query.progress == "in_progress":
        conditions.append({"automation.status": {"$ne": AutomationStatus.COMPLETED.value}})
    created_timestamp = _normalized_activity_timestamp_expression("$automation.created_at")
    if query.created_from_at is not None:
        conditions.append(
            {"$expr": {"$gte": [
                created_timestamp, _activity_timestamp_string(query.created_from_at),
            ]}}
        )
    if query.created_to_at is not None:
        conditions.append(
            {"$expr": {"$lt": [created_timestamp, _activity_timestamp_string(query.created_to_at)]}}
        )
    if query.priority_filter == PriorityFilter.PRIORITISED:
        conditions.append({"onboarding.priority": {"$ne": None}})
    elif query.priority_filter == PriorityFilter.UNSET:
        conditions.append({"onboarding.priority": None})
    elif query.priority_filter != PriorityFilter.ALL:
        conditions.append({"onboarding.priority": int(query.priority_filter)})
    if query.attention_type is not None:
        conditions.append(
            {
                "automation.exceptions": {
                    "$elemMatch": {
                        "status": BusinessExceptionStatus.OPEN.value,
                        "exception_type": query.attention_type.value,
                    }
                }
            }
        )
    if query.jurisdiction is not None:
        conditions.append(
            {"onboarding.jurisdiction_resolution.resolved_jurisdiction": (query.jurisdiction.value)}
        )
    if query.search is not None:
        literal = case_portfolio_search_pattern(query.search)
        conditions.append(
            {
                "$or": [
                    {"onboarding.requested_uen": {"$regex": literal}},
                    {"onboarding.entity.legal_name": {"$regex": literal}},
                    {"case_id": {"$regex": literal}},
                ]
            }
        )
    return {"$and": conditions} if conditions else {}


def _activity_event_valid_expression() -> dict[str, Any]:
    event_type = {"$type": "$$event"}
    safe_event = {"$cond": [{"$eq": [event_type, "object"]}, "$$event", {}]}
    keys = {
        "$map": {
            "input": {"$objectToArray": safe_event},
            "as": "pair",
            "in": "$$pair.k",
        }
    }
    code_type = {"$type": "$$event.code"}
    return {
        "$and": [
            {"$eq": [event_type, "object"]},
            {
                "$setEquals": [
                    keys,
                    [
                        "sequence",
                        "event_type",
                        "status",
                        "stage",
                        "outcome",
                        "timestamp",
                        "case_id",
                        "code",
                        "message",
                    ],
                ]
            },
            {"$in": [{"$type": "$$event.sequence"}, ["int", "long"]]},
            {"$gte": ["$$event.sequence", 1]},
            {"$in": ["$$event.event_type", [item.value for item in AutomationEventType]]},
            {"$in": ["$$event.status", [item.value for item in AutomationStatus]]},
            {"$in": ["$$event.stage", [item.value for item in AutomationStage]]},
            {"$in": ["$$event.outcome", [item.value for item in EventOutcome]]},
            _mongo_activity_timestamp("$$event.timestamp"),
            _mongo_canonical_uuid("$$event.case_id"),
            {"$eq": ["$$event.case_id", "$case_id"]},
            {
                "$or": [
                    {"$eq": [code_type, "null"]},
                    _mongo_bounded_string("$$event.code", 0, 64),
                ]
            },
            _mongo_bounded_string("$$event.message", 1, 200),
        ]
    }


def _activity_candidate_valid_expression() -> dict[str, Any]:
    events_type = {"$type": "$automation.events"}
    safe_events = {"$cond": [{"$eq": [events_type, "array"]}, "$automation.events", []]}
    schema_type = {"$type": "$schema_version"}
    revision_type = {"$type": "$revision"}
    team_type = {"$type": "$onboarding.team_id"}
    priority_type = {"$type": "$onboarding.priority"}
    return {
        "$and": [
            _creator_valid_expression(),
            {"$in": [schema_type, ["int", "long"]]},
            {"$in": ["$schema_version", _SUPPORTED_SCHEMA_VERSIONS]},
            {"$in": [revision_type, ["int", "long"]]},
            {"$gte": ["$revision", 0]},
            _mongo_canonical_uuid("$_id"),
            _mongo_canonical_uuid("$case_id"),
            {"$eq": ["$_id", "$case_id"]},
            _mongo_canonical_uuid("$onboarding.case_id"),
            {"$eq": ["$onboarding.case_id", "$case_id"]},
            _mongo_canonical_uuid("$automation.case_id"),
            {"$eq": ["$automation.case_id", "$case_id"]},
            {
                "$cond": [
                    {"$eq": ["$schema_version", 1]},
                    {"$eq": [team_type, "missing"]},
                    {
                        "$or": [
                            {"$eq": [team_type, "null"]},
                            {
                                "$and": [
                                    {"$eq": [team_type, "string"]},
                                    {
                                        "$regexMatch": {
                                            "input": {
                                                "$cond": [
                                                    {"$eq": [team_type, "string"]},
                                                    "$onboarding.team_id",
                                                    "",
                                                ]
                                            },
                                            "regex": "^(TEAM_A|TEAM_B|TEAM_[0-9A-F]{24})$",
                                        }
                                    },
                                ]
                            },
                        ]
                    },
                ]
            },
            {
                "$cond": [
                    {"$eq": ["$schema_version", 1]},
                    {"$eq": [priority_type, "missing"]},
                    {
                        "$or": [
                            {"$eq": [priority_type, "null"]},
                            {
                                "$and": [
                                    {"$in": [priority_type, ["int", "long"]]},
                                    {"$gte": ["$onboarding.priority", 1]},
                                    {"$lte": ["$onboarding.priority", 10]},
                                ]
                            },
                        ]
                    },
                ]
            },
            {"$eq": [events_type, "array"]},
            {
                "$allElementsTrue": {
                    "$map": {
                        "input": safe_events,
                        "as": "event",
                        "in": _activity_event_valid_expression(),
                    }
                }
            },
            {
                "$eq": [
                    {
                        "$map": {
                            "input": safe_events,
                            "as": "event",
                            "in": "$$event.sequence",
                        }
                    },
                    {"$range": [1, {"$add": [{"$size": safe_events}, 1]}]},
                ]
            },
        ]
    }


def _normalized_activity_timestamp_expression(value: str) -> dict[str, Any]:
    return {
        "$cond": [
            {"$eq": [{"$strLenCP": value}, 20]},
            {"$concat": [{"$substrCP": [value, 0, 19]}, ".000000Z"]},
            value,
        ]
    }


def _activity_timestamp_string(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _activity_row_match(query: CaseActivityQuery) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = []
    if query.action == CaseActivityAction.CREATED:
        conditions.append({"automation.events.event_type": {"$regex": "CREATED"}})
    elif query.action == CaseActivityAction.DOCUMENT:
        conditions.append({"automation.events.stage": AutomationStage.DOCUMENT.value})
    elif query.action == CaseActivityAction.RECONCILIATION:
        conditions.append({"automation.events.event_type": {"$regex": "RECONCILIATION"}})
    elif query.action == CaseActivityAction.OWNERSHIP:
        conditions.append({"automation.events.stage": AutomationStage.OWNERSHIP.value})
    elif query.action == CaseActivityAction.INTELLIGENCE:
        conditions.append(
            {"automation.events.event_type": (AutomationEventType.INTELLIGENCE_EVALUATED.value)}
        )
    elif query.action == CaseActivityAction.TARGET:
        conditions.append(
            {
                "$or": [
                    {"automation.events.stage": AutomationStage.MOCK_GOLDTIER.value},
                    {"automation.events.event_type": {"$regex": "MOCK_SUBMISSION"}},
                ]
            }
        )
    elif query.action == CaseActivityAction.COMPLETED:
        conditions.append(
            {
                "$or": [
                    {"automation.events.event_type": {"$regex": "COMPLETED"}},
                    {"automation.events.stage": AutomationStage.COMPLETE.value},
                ]
            }
        )
    if query.stage is not None:
        conditions.append({"automation.events.stage": query.stage.value})
    if query.outcome is not None:
        conditions.append({"automation.events.outcome": query.outcome.value})
    normalized_timestamp = _normalized_activity_timestamp_expression("$automation.events.timestamp")
    if query.from_at is not None:
        conditions.append(
            {"$expr": {"$gte": [normalized_timestamp, _activity_timestamp_string(query.from_at)]}}
        )
    if query.to_at is not None:
        conditions.append(
            {"$expr": {"$lt": [normalized_timestamp, _activity_timestamp_string(query.to_at)]}}
        )
    return {"$and": conditions} if conditions else {}


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


def _reject_phase24c_legacy_values(value: Any) -> None:
    """Old envelopes cannot masquerade as approved Phase24C policy/classification."""
    if isinstance(value, dict):
        if {"catalogue_version", "idp_review_confidence_threshold"} <= value.keys() and any(
            value.get(key) is not None
            for key in ("registry", "evidence_classifier", "policy_identity")
        ):
            raise PersistenceDataInvalidError
        if value.get("rule_version") == "ownership-semantic-rules-v2":
            raise PersistenceDataInvalidError
        for child in value.values():
            _reject_phase24c_legacy_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_phase24c_legacy_values(child)
