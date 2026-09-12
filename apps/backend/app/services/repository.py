"""Temporary process-local repository used by the Phase 01 mock slice."""

from __future__ import annotations

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.models import OnboardingCase


class OnboardingCaseRepository(Protocol):
    def create(self, case: OnboardingCase) -> None: ...

    def save(self, case: OnboardingCase) -> None: ...

    def get(self, case_id: UUID) -> OnboardingCase | None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...

    @property
    def transaction_lock(self) -> RLock: ...

    def transaction_snapshot(self, case_id: UUID) -> OnboardingCase | None: ...

    def transaction_replace(self, case: OnboardingCase) -> None: ...

    def transaction_restore(
        self, case_id: UUID, snapshot: OnboardingCase | None
    ) -> None: ...


class CaseTeamImmutableError(Exception):
    pass


class OnboardingCaseRepositoryConflictError(Exception):
    """A create/update no longer owns the expected persistence state."""


class InMemoryOnboardingCaseRepository:
    """Store defensive model copies for the lifetime of one application process."""

    def __init__(self, *, transaction_lock: RLock | None = None) -> None:
        self._cases: dict[UUID, OnboardingCase] = {}
        self._lock = transaction_lock or RLock()

    @property
    def transaction_lock(self) -> RLock:
        return self._lock

    def save(self, case: OnboardingCase) -> None:
        with self._lock:
            validated = OnboardingCase.model_validate(case)
            current = self._cases.get(validated.case_id)
            if current is None:
                raise OnboardingCaseRepositoryConflictError
            if current.team_id != validated.team_id:
                raise CaseTeamImmutableError
            self._cases[validated.case_id] = validated.model_copy(deep=True)

    def create(self, case: OnboardingCase) -> None:
        with self._lock:
            validated = OnboardingCase.model_validate(case)
            if validated.case_id in self._cases:
                raise OnboardingCaseRepositoryConflictError
            self._cases[validated.case_id] = validated.model_copy(deep=True)

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._cases.pop(case_id, None)

    def get(self, case_id: UUID) -> OnboardingCase | None:
        with self._lock:
            case = self._cases.get(case_id)
            return case.model_copy(deep=True) if case is not None else None

    def transaction_snapshot(self, case_id: UUID) -> OnboardingCase | None:
        case = self._cases.get(case_id)
        return case.model_copy(deep=True) if case is not None else None

    def transaction_replace(self, case: OnboardingCase) -> None:
        current = self._cases.get(case.case_id)
        if current is None:
            raise OnboardingCaseRepositoryConflictError
        if current.team_id != case.team_id:
            raise CaseTeamImmutableError
        self._cases[case.case_id] = case.model_copy(deep=True)

    def transaction_restore(
        self, case_id: UUID, snapshot: OnboardingCase | None
    ) -> None:
        if snapshot is None:
            self._cases.pop(case_id, None)
        else:
            self._cases[case_id] = snapshot.model_copy(deep=True)
