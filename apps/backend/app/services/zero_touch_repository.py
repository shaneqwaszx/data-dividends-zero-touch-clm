"""Atomic process-local zero-touch automation repository."""

from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager, contextmanager
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


def order_zero_touch_automation_records(
    records: Iterable[ZeroTouchAutomationRecord],
) -> list[ZeroTouchAutomationRecord]:
    """Order by automation update time, using case ID only as a stable tie-break."""

    return sorted(
        records,
        key=lambda item: (item.updated_at, str(item.case_id)),
        reverse=True,
    )


class ZeroTouchRepositoryReadError(ValueError):
    """Invalid selected evidence or misuse of a request-local read batch."""


class AutomationReadBatch(Protocol):
    def read_selected(
        self, case_ids: frozenset[UUID],
    ) -> list[ZeroTouchAutomationRecord]: ...


def validate_automation_batch_ids(case_ids: frozenset[UUID]) -> None:
    if type(case_ids) is not frozenset or any(type(value) is not UUID for value in case_ids):
        raise ZeroTouchRepositoryReadError("invalid automation batch selection")


class _MemoryAutomationReadBatch:
    def __init__(
        self, authorized: frozenset[UUID], records: dict[UUID, ZeroTouchAutomationRecord],
    ) -> None:
        self._authorized = authorized
        self._records = records
        self._closed = False

    def close(self) -> None:
        self._closed = True
        self._authorized = frozenset()
        self._records.clear()

    def read_selected(self, case_ids: frozenset[UUID]) -> list[ZeroTouchAutomationRecord]:
        if self._closed:
            raise ZeroTouchRepositoryReadError("automation batch is closed")
        try:
            validate_automation_batch_ids(case_ids)
            if not case_ids <= self._authorized:
                raise ZeroTouchRepositoryReadError("invalid automation batch selection")
            result = []
            for case_id in case_ids:
                record = self._records.get(case_id)
                if record is None:
                    continue
                if record.case_id != case_id:
                    raise ZeroTouchRepositoryReadError("invalid selected automation")
                decoded = record.model_copy(deep=True)
                validate_automation_record(decoded)
                result.append(decoded)
            return order_zero_touch_automation_records(result)
        except ValueError:
            raise ZeroTouchRepositoryReadError("invalid selected automation") from None
        finally:
            self.close()


class ZeroTouchAutomationRepository(Protocol):
    def save(
        self, record: ZeroTouchAutomationRecord, *, expected_version: int | None
    ) -> ZeroTouchAutomationRecord: ...

    def get_for_case(self, case_id: UUID) -> ZeroTouchAutomationRecord | None: ...

    def list_records(self) -> list[ZeroTouchAutomationRecord]: ...

    def capture_for_cases(
        self, case_ids: frozenset[UUID],
    ) -> AbstractContextManager[AutomationReadBatch]: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


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
        return order_zero_touch_automation_records(records)

    @contextmanager
    def capture_for_cases(self, case_ids: frozenset[UUID]) -> Iterator[AutomationReadBatch]:
        """Capture owned copies before observation; decode only one selected subset."""
        validate_automation_batch_ids(case_ids)
        with self._lock:
            records = {key: self._records[key].model_copy(deep=True)
                       for key in case_ids if key in self._records}
        batch = _MemoryAutomationReadBatch(case_ids, records)
        try:
            yield batch
        finally:
            batch.close()

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._records.pop(case_id, None)
