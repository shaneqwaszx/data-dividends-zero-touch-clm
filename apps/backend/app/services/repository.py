"""Temporary process-local repository used by the Phase 01 mock slice."""

from typing import Protocol
from uuid import UUID

from app.domain.models import OnboardingCase


class OnboardingCaseRepository(Protocol):
    def save(self, case: OnboardingCase) -> None: ...

    def get(self, case_id: UUID) -> OnboardingCase | None: ...


class InMemoryOnboardingCaseRepository:
    """Store defensive model copies for the lifetime of one application process."""

    def __init__(self) -> None:
        self._cases: dict[UUID, OnboardingCase] = {}

    def save(self, case: OnboardingCase) -> None:
        self._cases[case.case_id] = case.model_copy(deep=True)

    def get(self, case_id: UUID) -> OnboardingCase | None:
        case = self._cases.get(case_id)
        return case.model_copy(deep=True) if case is not None else None
