"""Atomic process-local repository for Phase 05 orchestration records."""

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.clm import ClmOrchestrationRecord


class ClmRepositoryConflictError(Exception):
    """The requested orchestration version no longer owns the transition."""


class ClmOrchestrationRepository(Protocol):
    def save(
        self,
        record: ClmOrchestrationRecord,
        *,
        expected_version: int | None,
    ) -> ClmOrchestrationRecord: ...

    def get_for_case(self, case_id: UUID) -> ClmOrchestrationRecord | None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryClmOrchestrationRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, ClmOrchestrationRecord] = {}
        self._lock = RLock()

    def save(
        self,
        record: ClmOrchestrationRecord,
        *,
        expected_version: int | None,
    ) -> ClmOrchestrationRecord:
        with self._lock:
            current = self._records.get(record.case_id)
            if expected_version is None:
                if current is not None or record.version != 0:
                    raise ClmRepositoryConflictError
                next_version = 1
            else:
                if current is None or current.version != expected_version:
                    raise ClmRepositoryConflictError
                next_version = expected_version + 1
            persisted = record.model_copy(update={"version": next_version}, deep=True)
            self._records[record.case_id] = persisted
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> ClmOrchestrationRecord | None:
        with self._lock:
            record = self._records.get(case_id)
            return record.model_copy(deep=True) if record is not None else None

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._records.pop(case_id, None)
