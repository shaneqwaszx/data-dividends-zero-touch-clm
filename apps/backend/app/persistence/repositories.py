"""Mongo infrastructure adapters for existing service repository boundaries."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from threading import RLock
from uuid import UUID

from app.domain.clm import ClmOrchestrationRecord
from app.domain.documents import DocumentProcessingRecord
from app.domain.models import OnboardingCase
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState
from app.domain.reconciliation import ReconciliationCaseRecord
from app.domain.target_submission import GoldTierExecutionLedgerEntry
from app.domain.zero_touch import (
    ZeroTouchAutomationRecord,
    validate_automation_record,
    validate_automation_transition,
)
from app.persistence.errors import PersistenceConflictError
from app.persistence.models import DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.clm_repository import ClmRepositoryConflictError
from app.services.ownership_repository import OwnershipRepositoryConflictError
from app.services.reconciliation_repository import (
    ReconciliationRepositoryConflictError,
    ReconciliationUnitOfWorkError,
)
from app.services.target_execution_repository import (
    TargetExecutionRepositoryConflictError,
)
from app.services.zero_touch_repository import (
    ZeroTouchRepositoryConflictError,
    order_zero_touch_automation_records,
)


class MongoOnboardingCaseRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    @property
    def transaction_lock(self) -> RLock:
        return self._store.transaction_lock

    def save(self, case: OnboardingCase) -> None:
        validated = OnboardingCase.model_validate(case)
        with self._store.locked():
            current = self._store.get(validated.case_id)
            if current is None:
                now = datetime.now(UTC)
                self._store.create(
                    DurableCaseSnapshot(
                        case_id=validated.case_id,
                        revision=0,
                        onboarding=validated,
                        created_at=now,
                        updated_at=now,
                    )
                )
                return
            candidate = current.model_copy(update={"onboarding": validated}, deep=True)
            self._store.replace(candidate, expected_revision=current.revision)

    def get(self, case_id: UUID) -> OnboardingCase | None:
        snapshot = self._store.get(case_id)
        return snapshot.onboarding.model_copy(deep=True) if snapshot is not None else None

    def transaction_snapshot(self, case_id: UUID) -> OnboardingCase | None:
        return self.get(case_id)

    def transaction_replace(self, case: OnboardingCase) -> None:
        self.save(case)

    def transaction_restore(
        self, case_id: UUID, snapshot: OnboardingCase | None
    ) -> None:
        if snapshot is None:
            raise PersistenceConflictError
        self.save(snapshot)


class MongoDocumentProcessingRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def save(self, record: DocumentProcessingRecord) -> None:
        validated = DocumentProcessingRecord.model_validate(record)
        with self._store.locked():
            current = self._require_snapshot(validated.case_id)
            documents = list(current.documents)
            for index, item in enumerate(documents):
                if item.document_id == validated.document_id:
                    documents[index] = validated
                    break
            else:
                documents.append(validated)
            candidate = current.model_copy(update={"documents": tuple(documents)}, deep=True)
            self._store.replace(candidate, expected_revision=current.revision)

    def get(self, document_id: UUID) -> DocumentProcessingRecord | None:
        snapshot = self._store.find_by_document(document_id)
        if snapshot is not None:
            for record in snapshot.documents:
                if record.document_id == document_id:
                    return record.model_copy(deep=True)
        return None

    def list_for_case(self, case_id: UUID) -> list[DocumentProcessingRecord]:
        snapshot = self._store.get(case_id)
        if snapshot is None:
            return []
        return [item.model_copy(deep=True) for item in snapshot.documents]

    def _require_snapshot(self, case_id: UUID) -> DurableCaseSnapshot:
        snapshot = self._store.get(case_id)
        if snapshot is None:
            raise PersistenceConflictError
        return snapshot


class MongoOwnershipAnalysisRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def save(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int | None,
    ) -> OwnershipAnalysisRecord:
        validated = OwnershipAnalysisRecord.model_validate(record)
        with self._store.locked():
            snapshot = self._store.get(validated.case_id)
            if snapshot is None:
                raise OwnershipRepositoryConflictError
            current = snapshot.ownership
            if expected_version is None:
                if current is not None or validated.version != 0:
                    raise OwnershipRepositoryConflictError
                next_version = 1
            else:
                if current is None or current.version != expected_version:
                    raise OwnershipRepositoryConflictError
                if current.state in {
                    OwnershipAnalysisState.FAILED,
                    OwnershipAnalysisState.ANALYZED,
                    OwnershipAnalysisState.REVIEW_REQUIRED,
                }:
                    raise OwnershipRepositoryConflictError
                next_version = expected_version + 1
            persisted = validated.model_copy(update={"version": next_version}, deep=True)
            candidate = snapshot.model_copy(update={"ownership": persisted}, deep=True)
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise OwnershipRepositoryConflictError from None
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> OwnershipAnalysisRecord | None:
        snapshot = self._store.get(case_id)
        if snapshot is None or snapshot.ownership is None:
            return None
        return snapshot.ownership.model_copy(deep=True)


class MongoClmOrchestrationRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def save(
        self,
        record: ClmOrchestrationRecord,
        *,
        expected_version: int | None,
    ) -> ClmOrchestrationRecord:
        validated = ClmOrchestrationRecord.model_validate(record)
        with self._store.locked():
            snapshot = self._store.get(validated.case_id)
            if snapshot is None:
                raise ClmRepositoryConflictError
            current = snapshot.clm
            if expected_version is None:
                if current is not None or validated.version != 0:
                    raise ClmRepositoryConflictError
                next_version = 1
            else:
                if current is None or current.version != expected_version:
                    raise ClmRepositoryConflictError
                next_version = expected_version + 1
            persisted = validated.model_copy(update={"version": next_version}, deep=True)
            candidate = snapshot.model_copy(update={"clm": persisted}, deep=True)
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise ClmRepositoryConflictError from None
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> ClmOrchestrationRecord | None:
        snapshot = self._store.get(case_id)
        if snapshot is None or snapshot.clm is None:
            return None
        return snapshot.clm.model_copy(deep=True)


class MongoZeroTouchAutomationRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def save(
        self, record: ZeroTouchAutomationRecord, *, expected_version: int | None
    ) -> ZeroTouchAutomationRecord:
        validated = ZeroTouchAutomationRecord.model_validate(record)
        with self._store.locked():
            snapshot = self._store.get(validated.case_id)
            if snapshot is None:
                raise ZeroTouchRepositoryConflictError
            current = snapshot.automation
            if expected_version is None:
                if current is not None or validated.version != 0:
                    raise ZeroTouchRepositoryConflictError
                next_version = 1
                validate_automation_record(validated)
            else:
                if current is None or current.version != expected_version:
                    raise ZeroTouchRepositoryConflictError
                next_version = expected_version + 1
                validate_automation_transition(current, validated)
            persisted = validated.model_copy(update={"version": next_version}, deep=True)
            candidate = snapshot.model_copy(update={"automation": persisted}, deep=True)
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise ZeroTouchRepositoryConflictError from None
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> ZeroTouchAutomationRecord | None:
        snapshot = self._store.get(case_id)
        if snapshot is None or snapshot.automation is None:
            return None
        return snapshot.automation.model_copy(deep=True)

    def list_records(self) -> list[ZeroTouchAutomationRecord]:
        records = (
            snapshot.automation.model_copy(deep=True)
            for snapshot in self._store.list()
            if snapshot.automation is not None
        )
        return order_zero_touch_automation_records(records)


class MongoReconciliationRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def bind_transaction_lock(self, lock: RLock) -> None:
        del lock

    def save(
        self, record: ReconciliationCaseRecord, *, expected_version: int | None
    ) -> ReconciliationCaseRecord:
        validated = ReconciliationCaseRecord.model_validate(record)
        with self._store.locked():
            snapshot = self._store.get(validated.case_id)
            if snapshot is None:
                raise ReconciliationRepositoryConflictError
            current = snapshot.reconciliation
            if expected_version is None:
                if current is not None or validated.version != 0:
                    raise ReconciliationRepositoryConflictError
                next_version = 1
            else:
                if current is None or current.version != expected_version:
                    raise ReconciliationRepositoryConflictError
                next_version = expected_version + 1
            persisted = validated.model_copy(update={"version": next_version}, deep=True)
            candidate = snapshot.model_copy(update={"reconciliation": persisted}, deep=True)
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise ReconciliationRepositoryConflictError from None
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> ReconciliationCaseRecord | None:
        snapshot = self._store.get(case_id)
        if snapshot is None or snapshot.reconciliation is None:
            return None
        return snapshot.reconciliation.model_copy(deep=True)

    def transaction_snapshot(self, case_id: UUID) -> ReconciliationCaseRecord | None:
        return self.get_for_case(case_id)

    def transaction_prepare(
        self, record: ReconciliationCaseRecord, *, expected_version: int
    ) -> ReconciliationCaseRecord:
        current = self.get_for_case(record.case_id)
        if current is None or current.version != expected_version:
            raise ReconciliationRepositoryConflictError
        return ReconciliationCaseRecord.model_validate(record).model_copy(
            update={"version": expected_version + 1}, deep=True
        )

    def transaction_replace(self, record: ReconciliationCaseRecord) -> None:
        self.save(record, expected_version=record.version - 1)

    def transaction_restore(
        self, case_id: UUID, snapshot: ReconciliationCaseRecord | None
    ) -> None:
        del case_id, snapshot
        raise ReconciliationUnitOfWorkError


class MongoReconciliationUnitOfWork:
    """Commit canonical and decision state in one envelope CAS."""

    def __init__(
        self,
        store: MongoCaseStore,
        *,
        fault: Callable[[str], None] | None = None,
    ) -> None:
        self._store = store
        self._fault = fault

    def commit_resolution(
        self,
        *,
        onboarding_candidate: OnboardingCase | None,
        reconciliation_candidate: ReconciliationCaseRecord,
        expected_reconciliation_version: int,
        expected_onboarding_fingerprint: str,
        expected_entity_fingerprint: str,
    ) -> ReconciliationCaseRecord:
        validated_reconciliation = ReconciliationCaseRecord.model_validate(
            reconciliation_candidate
        )
        with self._store.locked():
            snapshot = self._store.get(validated_reconciliation.case_id)
            if (
                snapshot is None
                or snapshot.onboarding.entity is None
                or snapshot.reconciliation is None
                or snapshot.reconciliation.version != expected_reconciliation_version
            ):
                raise ReconciliationRepositoryConflictError
            onboarding_json = snapshot.onboarding.model_dump_json().encode("utf-8")
            entity_json = snapshot.onboarding.entity.model_dump_json().encode("utf-8")
            if not hmac.compare_digest(
                sha256(onboarding_json).hexdigest(), expected_onboarding_fingerprint
            ) or not hmac.compare_digest(
                sha256(entity_json).hexdigest(), expected_entity_fingerprint
            ):
                raise ReconciliationRepositoryConflictError
            onboarding = (
                OnboardingCase.model_validate(onboarding_candidate)
                if onboarding_candidate is not None
                else snapshot.onboarding
            )
            if onboarding.case_id != snapshot.case_id:
                raise ValueError("coordinated reconciliation case IDs must agree")
            persisted_reconciliation = validated_reconciliation.model_copy(
                update={"version": expected_reconciliation_version + 1}, deep=True
            )
            candidate = snapshot.model_copy(
                update={
                    "onboarding": onboarding,
                    "reconciliation": persisted_reconciliation,
                },
                deep=True,
            )
            try:
                if self._fault is not None:
                    self._fault("before_atomic_commit")
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise ReconciliationRepositoryConflictError from None
            except Exception:
                raise ReconciliationUnitOfWorkError from None
            return persisted_reconciliation.model_copy(deep=True)


class MongoTargetExecutionRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def get(self, submission_id: UUID) -> GoldTierExecutionLedgerEntry | None:
        snapshot = self._store.find_by_submission(submission_id)
        if snapshot is None:
            return None
        for entry in snapshot.target_executions:
            if entry.submission_input.submission_id == submission_id:
                return entry.model_copy(deep=True)
        return None

    def create(self, entry: GoldTierExecutionLedgerEntry) -> None:
        case_id = entry.submission_input.case_id
        with self._store.locked():
            snapshot = self._store.get(case_id)
            if snapshot is None or any(
                item.submission_input.submission_id
                == entry.submission_input.submission_id
                for item in snapshot.target_executions
            ):
                raise TargetExecutionRepositoryConflictError
            candidate = snapshot.model_copy(
                update={"target_executions": (*snapshot.target_executions, entry)},
                deep=True,
            )
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise TargetExecutionRepositoryConflictError from None

    def replace(
        self,
        entry: GoldTierExecutionLedgerEntry,
        *,
        expected_state: str,
    ) -> None:
        submission_id = entry.submission_input.submission_id
        with self._store.locked():
            snapshot = self._store.get(entry.submission_input.case_id)
            if snapshot is None:
                raise TargetExecutionRepositoryConflictError
            entries = list(snapshot.target_executions)
            for index, current in enumerate(entries):
                if current.submission_input.submission_id == submission_id:
                    if current.state.value != expected_state:
                        raise TargetExecutionRepositoryConflictError
                    entries[index] = entry
                    break
            else:
                raise TargetExecutionRepositoryConflictError
            candidate = snapshot.model_copy(
                update={"target_executions": tuple(entries)}, deep=True
            )
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise TargetExecutionRepositoryConflictError from None

    def delete_if_unattempted(self, submission_id: UUID) -> None:
        with self._store.locked():
            snapshot = self._store.find_by_submission(submission_id)
            if snapshot is None:
                return
            entries = []
            for current in snapshot.target_executions:
                if current.submission_input.submission_id == submission_id:
                    if current.attempted_operations:
                        raise TargetExecutionRepositoryConflictError
                    continue
                entries.append(current)
            candidate = snapshot.model_copy(
                update={"target_executions": tuple(entries)}, deep=True
            )
            try:
                self._store.replace(candidate, expected_revision=snapshot.revision)
            except PersistenceConflictError:
                raise TargetExecutionRepositoryConflictError from None


class MongoDemoScenarioRepository:
    def __init__(self, store: MongoCaseStore) -> None:
        self._store = store

    def set(self, case_id: UUID, scenario: str) -> None:
        with self._store.locked():
            snapshot = self._store.get(case_id)
            if snapshot is None:
                raise PersistenceConflictError
            candidate = snapshot.model_copy(update={"demo_scenario": scenario}, deep=True)
            self._store.replace(candidate, expected_revision=snapshot.revision)

    def get(self, case_id: UUID) -> str | None:
        snapshot = self._store.get(case_id)
        return snapshot.demo_scenario if snapshot is not None else None
