"""Repository boundary for durable Mock target execution checkpoints."""

import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.target_submission import (
    WORKFLOW_DISPATCH_WRITE_OPERATIONS,
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    WorkflowDispatch,
    WorkflowDispatchFirstWrite,
    WorkflowDispatchState,
)

FENCE_LEASE = timedelta(seconds=60)


def has_write_marker(entry: GoldTierExecutionLedgerEntry) -> bool:
    return any(
        item.value in WORKFLOW_DISPATCH_WRITE_OPERATIONS for item in entry.attempted_operations
    )


def claim_selectable(entry: GoldTierExecutionLedgerEntry, token: str, now: datetime) -> bool:
    """D2 predicate: no claim, an expired claim, or own claim; never after a write marker."""

    claim = entry.workflow_dispatch
    return (
        entry.state == GoldTierExecutionLedgerState.IN_PROGRESS
        and not has_write_marker(entry)
        and (claim is None or claim.lease_until <= now or claim.token == token)
    )


def authorise_selectable(
    entry: GoldTierExecutionLedgerEntry, token: str, version: int, now: datetime
) -> bool:
    """D4 predicate: own TENTATIVE claim for the version, lease unexpired."""

    claim = entry.workflow_dispatch
    return (
        entry.state == GoldTierExecutionLedgerState.IN_PROGRESS
        and not has_write_marker(entry)
        and claim is not None
        and claim.state == WorkflowDispatchState.TENTATIVE
        and claim.token == token
        and claim.version == version
        and claim.lease_until > now
    )


def first_write_selectable(
    entry: GoldTierExecutionLedgerEntry, token: str, now: datetime
) -> bool:
    """D5 predicate: own AUTHORISED claim, lease unexpired, no write attempt yet."""

    claim = entry.workflow_dispatch
    return (
        entry.state == GoldTierExecutionLedgerState.IN_PROGRESS
        and not has_write_marker(entry)
        and claim is not None
        and claim.state == WorkflowDispatchState.AUTHORISED
        and claim.token == token
        and claim.lease_until > now
    )


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
        expected_attempted: tuple[GoldTierOperationMarker, ...],
    ) -> None:
        """Compare-and-set asserting, on the same snapshot as the write, the state and the
        attempted operations the caller read (ADR-017 3.2). A conflict means re-read."""
        ...

    def fence_claim(
        self, submission_id: UUID, *, token: str, version: int
    ) -> GoldTierExecutionLedgerEntry | None: ...

    def fence_authorise(
        self, submission_id: UUID, *, token: str, version: int
    ) -> GoldTierExecutionLedgerEntry | None: ...

    def fence_first_write(
        self, submission_id: UUID, *, token: str, operation: GoldTierOperationMarker
    ) -> GoldTierExecutionLedgerEntry | None: ...

    def delete_if_unattempted(self, submission_id: UUID) -> None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryTargetExecutionRepository:
    """Memory mode: this lock orders D2, D4 and D5 (ADR-017 3.8); the clock is the server."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._entries: dict[UUID, GoldTierExecutionLedgerEntry] = {}
        self._lock = RLock()
        self._clock = clock or (lambda: datetime.now(UTC))

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
        expected_attempted: tuple[GoldTierOperationMarker, ...],
    ) -> None:
        submission_id = entry.submission_input.submission_id
        with self._lock:
            current = self._entries.get(submission_id)
            if (
                current is None
                or current.state.value != expected_state
                or current.attempted_operations != tuple(expected_attempted)
            ):
                raise TargetExecutionRepositoryConflictError
            if current.workflow_dispatch != entry.workflow_dispatch:
                # A dispatch claim changes only through the fence steps, never a replace.
                raise TargetExecutionRepositoryConflictError
            if has_write_marker(entry) and not has_write_marker(current):
                # The first write attempt marker is recorded only by the fence (D5).
                raise TargetExecutionRepositoryConflictError
            self._entries[submission_id] = entry.model_copy(deep=True)

    def probe_durability(self) -> tuple[bool, str | None]:
        """Memory mode: one process, one lock (ADR-017 3.8)."""

        return True, None

    def fence_claim(
        self, submission_id: UUID, *, token: str, version: int
    ) -> GoldTierExecutionLedgerEntry | None:
        with self._lock:
            entry, now = self._entries.get(submission_id), self._clock()
            if entry is None or not claim_selectable(entry, token, now):
                return None
            claim = WorkflowDispatch(
                state=WorkflowDispatchState.TENTATIVE, token=token, version=version,
                lease_until=now + FENCE_LEASE, receipt=secrets.token_hex(16),
            )
            updated = entry.model_copy(update={"workflow_dispatch": claim})
            self._entries[submission_id] = updated
            return updated.model_copy(deep=True)

    def fence_authorise(
        self, submission_id: UUID, *, token: str, version: int
    ) -> GoldTierExecutionLedgerEntry | None:
        with self._lock:
            entry, now = self._entries.get(submission_id), self._clock()
            if entry is None or not authorise_selectable(entry, token, version, now):
                return None
            claim = WorkflowDispatch(
                state=WorkflowDispatchState.AUTHORISED, token=token, version=version,
                d3_at=now, lease_until=now + FENCE_LEASE, receipt=secrets.token_hex(16),
            )
            updated = entry.model_copy(update={"workflow_dispatch": claim})
            self._entries[submission_id] = updated
            return updated.model_copy(deep=True)

    def fence_first_write(
        self, submission_id: UUID, *, token: str, operation: GoldTierOperationMarker
    ) -> GoldTierExecutionLedgerEntry | None:
        with self._lock:
            entry, now = self._entries.get(submission_id), self._clock()
            if entry is None or not first_write_selectable(entry, token, now):
                return None
            current = entry.workflow_dispatch
            if current is None:  # pragma: no cover - excluded by the predicate
                return None
            receipt = secrets.token_hex(16)
            claim = current.model_copy(
                update={
                    "receipt": receipt,
                    "first_write": WorkflowDispatchFirstWrite(
                        operation=operation, version=current.version, token=token,
                        receipt=receipt,
                    ),
                }
            )
            updated = GoldTierExecutionLedgerEntry.model_validate(
                {
                    **entry.model_dump(),
                    "attempted_operations": (*entry.attempted_operations, operation),
                    "workflow_dispatch": claim,
                }
            )
            self._entries[submission_id] = updated
            return updated.model_copy(deep=True)

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
