"""Repository boundary for durable Mock target execution checkpoints."""

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.target_submission import GoldTierExecutionLedgerEntry


class TargetExecutionRepositoryConflictError(Exception):
    """A target execution checkpoint no longer owns its transition."""


class TargetExecutionRepository(Protocol):
    def get(self, submission_id: UUID) -> GoldTierExecutionLedgerEntry | None: ...

    def list_for_case(self, case_id: UUID) -> tuple[GoldTierExecutionLedgerEntry, ...]: ...

    def create(self, entry: GoldTierExecutionLedgerEntry) -> None: ...

    def replace(
        self,
        entry: GoldTierExecutionLedgerEntry,
        *,
        expected_state: str,
    ) -> None: ...

    def delete_if_unattempted(self, submission_id: UUID) -> None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryTargetExecutionRepository:
    def __init__(self) -> None:
        self._entries: dict[UUID, GoldTierExecutionLedgerEntry] = {}
        self._lock = RLock()

    def get(self, submission_id: UUID) -> GoldTierExecutionLedgerEntry | None:
        with self._lock:
            entry = self._entries.get(submission_id)
            return entry.model_copy(deep=True) if entry is not None else None

    def list_for_case(self, case_id: UUID) -> tuple[GoldTierExecutionLedgerEntry, ...]:
        with self._lock:
            return tuple(
                entry.model_copy(deep=True) for entry in self._entries.values()
                if entry.submission_input.case_id == case_id
            )

    def create(self, entry: GoldTierExecutionLedgerEntry) -> None:
        submission_id = entry.submission_input.submission_id
        with self._lock:
            if submission_id in self._entries:
                raise TargetExecutionRepositoryConflictError
            self._entries[submission_id] = entry.model_copy(deep=True)

    def replace(
        self,
        entry: GoldTierExecutionLedgerEntry,
        *,
        expected_state: str,
    ) -> None:
        submission_id = entry.submission_input.submission_id
        with self._lock:
            current = self._entries.get(submission_id)
            if current is None or current.state.value != expected_state:
                raise TargetExecutionRepositoryConflictError
            if current.workflow_dispatch != entry.workflow_dispatch:
                # Reader release: a dispatch claim is preserved, never rewritten.
                raise TargetExecutionRepositoryConflictError
            self._entries[submission_id] = entry.model_copy(deep=True)

    def delete_if_unattempted(self, submission_id: UUID) -> None:
        with self._lock:
            current = self._entries.get(submission_id)
            if current is None:
                return
            if current.attempted_operations:
                raise TargetExecutionRepositoryConflictError
            del self._entries[submission_id]

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            submission_ids = [
                submission_id
                for submission_id, entry in self._entries.items()
                if entry.submission_input.case_id == case_id
            ]
            for submission_id in submission_ids:
                self._entries.pop(submission_id, None)
