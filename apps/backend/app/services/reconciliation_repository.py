"""Atomic process-local reconciliation repository."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from hashlib import sha256
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.models import OnboardingCase
from app.domain.reconciliation import ReconciliationCaseRecord
from app.services.repository import OnboardingCaseRepository


class ReconciliationRepositoryConflictError(Exception):
    pass


class ReconciliationUnitOfWorkError(Exception):
    pass


class ReconciliationRepository(Protocol):
    def save(
        self, record: ReconciliationCaseRecord, *, expected_version: int | None
    ) -> ReconciliationCaseRecord: ...

    def get_for_case(self, case_id: UUID) -> ReconciliationCaseRecord | None: ...

    def bind_transaction_lock(self, lock: RLock) -> None: ...

    def transaction_snapshot(self, case_id: UUID) -> ReconciliationCaseRecord | None: ...

    def transaction_prepare(
        self, record: ReconciliationCaseRecord, *, expected_version: int
    ) -> ReconciliationCaseRecord: ...

    def transaction_replace(self, record: ReconciliationCaseRecord) -> None: ...

    def transaction_restore(
        self, case_id: UUID, snapshot: ReconciliationCaseRecord | None
    ) -> None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class ReconciliationUnitOfWork(Protocol):
    def commit_resolution(
        self,
        *,
        onboarding_candidate: OnboardingCase | None,
        reconciliation_candidate: ReconciliationCaseRecord,
        expected_reconciliation_version: int,
        expected_onboarding_fingerprint: str,
        expected_entity_fingerprint: str,
    ) -> ReconciliationCaseRecord: ...


class InMemoryReconciliationRepository:
    def __init__(self, *, transaction_lock: RLock | None = None) -> None:
        self._records: dict[UUID, ReconciliationCaseRecord] = {}
        self._lock = transaction_lock or RLock()

    def bind_transaction_lock(self, lock: RLock) -> None:
        with self._lock:
            if self._records:
                raise ValueError("cannot rebind a populated reconciliation repository")
            self._lock = lock

    def save(
        self, record: ReconciliationCaseRecord, *, expected_version: int | None
    ) -> ReconciliationCaseRecord:
        with self._lock:
            validated = ReconciliationCaseRecord.model_validate(record)
            current = self._records.get(validated.case_id)
            if expected_version is None:
                if current is not None or validated.version != 0:
                    raise ReconciliationRepositoryConflictError
                next_version = 1
            else:
                if current is None or current.version != expected_version:
                    raise ReconciliationRepositoryConflictError
                next_version = expected_version + 1
            candidate = validated.model_copy(update={"version": next_version}, deep=True)
            self.transaction_replace(candidate)
            return candidate.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> ReconciliationCaseRecord | None:
        with self._lock:
            record = self._records.get(case_id)
            return (
                ReconciliationCaseRecord.model_validate(record).model_copy(deep=True)
                if record is not None
                else None
            )

    def transaction_snapshot(self, case_id: UUID) -> ReconciliationCaseRecord | None:
        record = self._records.get(case_id)
        return record.model_copy(deep=True) if record is not None else None

    def transaction_prepare(
        self, record: ReconciliationCaseRecord, *, expected_version: int
    ) -> ReconciliationCaseRecord:
        validated = ReconciliationCaseRecord.model_validate(record)
        current = self._records.get(validated.case_id)
        if current is None or current.version != expected_version:
            raise ReconciliationRepositoryConflictError
        return validated.model_copy(update={"version": expected_version + 1}, deep=True)

    def transaction_replace(self, record: ReconciliationCaseRecord) -> None:
        self._records[record.case_id] = record.model_copy(deep=True)

    def transaction_restore(
        self, case_id: UUID, snapshot: ReconciliationCaseRecord | None
    ) -> None:
        if snapshot is None:
            self._records.pop(case_id, None)
        else:
            self._records[case_id] = snapshot.model_copy(deep=True)

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._records.pop(case_id, None)


class ProcessLocalReconciliationUnitOfWork:
    """Commit one canonical candidate and its decision without observable half-state."""

    def __init__(
        self,
        *,
        onboarding_repository: OnboardingCaseRepository,
        reconciliation_repository: ReconciliationRepository,
        fault: Callable[[str], None] | None = None,
    ) -> None:
        self._onboarding = onboarding_repository
        self._reconciliation = reconciliation_repository
        self._lock = onboarding_repository.transaction_lock
        self._reconciliation.bind_transaction_lock(self._lock)
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
        """Validate first, then commit or restore both process-local aggregates."""

        validated_onboarding = (
            OnboardingCase.model_validate(onboarding_candidate)
            if onboarding_candidate is not None
            else None
        )
        validated_reconciliation = ReconciliationCaseRecord.model_validate(
            reconciliation_candidate
        )
        with self._lock:
            current_onboarding = self._onboarding.transaction_snapshot(
                validated_reconciliation.case_id
            )
            if current_onboarding is None or current_onboarding.entity is None:
                raise ReconciliationRepositoryConflictError
            current_onboarding_fingerprint = sha256(
                current_onboarding.model_dump_json().encode("utf-8")
            ).hexdigest()
            if not hmac.compare_digest(
                current_onboarding_fingerprint, expected_onboarding_fingerprint
            ):
                raise ReconciliationRepositoryConflictError
            current_entity_fingerprint = sha256(
                current_onboarding.entity.model_dump_json().encode("utf-8")
            ).hexdigest()
            if not hmac.compare_digest(
                current_entity_fingerprint, expected_entity_fingerprint
            ):
                raise ReconciliationRepositoryConflictError
            if (
                validated_onboarding is not None
                and validated_onboarding.case_id != validated_reconciliation.case_id
            ):
                raise ValueError("coordinated reconciliation case IDs must agree")
            prepared_reconciliation = self._reconciliation.transaction_prepare(
                validated_reconciliation,
                expected_version=expected_reconciliation_version,
            )
            onboarding_snapshot = current_onboarding.model_copy(deep=True)
            reconciliation_snapshot = self._reconciliation.transaction_snapshot(
                validated_reconciliation.case_id
            )
            try:
                self._inject("before_onboarding_commit")
                if validated_onboarding is not None:
                    self._onboarding.transaction_replace(validated_onboarding)
                self._inject("before_reconciliation_commit")
                self._reconciliation.transaction_replace(prepared_reconciliation)
                self._inject("after_reconciliation_commit")
            except Exception:
                self._onboarding.transaction_restore(
                    validated_reconciliation.case_id, onboarding_snapshot
                )
                self._reconciliation.transaction_restore(
                    validated_reconciliation.case_id, reconciliation_snapshot
                )
                raise ReconciliationUnitOfWorkError from None
            return prepared_reconciliation.model_copy(deep=True)

    def _inject(self, stage: str) -> None:
        if self._fault is not None:
            self._fault(stage)
