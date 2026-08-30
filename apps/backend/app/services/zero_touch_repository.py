"""Atomic process-local zero-touch automation repository."""

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.zero_touch import (
    ZeroTouchAutomationRecord,
    validate_automation_record,
    validate_automation_transition,
)


class ZeroTouchRepositoryConflictError(Exception):
    pass


class ZeroTouchAutomationRepository(Protocol):
    def save(
        self, record: ZeroTouchAutomationRecord, *, expected_version: int | None
    ) -> ZeroTouchAutomationRecord: ...

    def get_for_case(self, case_id: UUID) -> ZeroTouchAutomationRecord | None: ...

    def list_records(self) -> list[ZeroTouchAutomationRecord]: ...


class InMemoryZeroTouchAutomationRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, ZeroTouchAutomationRecord] = {}
        self._lock = RLock()

    def save(
        self, record: ZeroTouchAutomationRecord, *, expected_version: int | None
    ) -> ZeroTouchAutomationRecord:
        with self._lock:
            current = self._records.get(record.case_id)
            if expected_version is None:
                if current is not None or record.version != 0:
                    raise ZeroTouchRepositoryConflictError
                next_version = 1
                validate_automation_record(record)
            else:
                if current is None or current.version != expected_version:
                    raise ZeroTouchRepositoryConflictError
                next_version = expected_version + 1
                validate_automation_transition(current, record)
            persisted = record.model_copy(update={"version": next_version}, deep=True)
            self._records[record.case_id] = persisted
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> ZeroTouchAutomationRecord | None:
        with self._lock:
            record = self._records.get(case_id)
            return record.model_copy(deep=True) if record is not None else None

    def list_records(self) -> list[ZeroTouchAutomationRecord]:
        """Return defensive copies, newest update first with a stable case-ID tie-break."""

        with self._lock:
            records = [record.model_copy(deep=True) for record in self._records.values()]
        return sorted(records, key=lambda item: (item.updated_at, str(item.case_id)), reverse=True)
