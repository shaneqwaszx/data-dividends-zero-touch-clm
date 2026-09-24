"""Repository boundary for one case-owned onboarding intelligence projection."""

from __future__ import annotations

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.onboarding_intelligence import OnboardingIntelligenceRecord


class OnboardingIntelligenceRepositoryConflictError(Exception):
    """The intelligence record or owning case changed or no longer exists."""


class OnboardingIntelligenceRepository(Protocol):
    def save(
        self,
        record: OnboardingIntelligenceRecord,
        *,
        expected_version: int | None,
    ) -> OnboardingIntelligenceRecord: ...

    def get_for_case(self, case_id: UUID) -> OnboardingIntelligenceRecord | None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryOnboardingIntelligenceRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, OnboardingIntelligenceRecord] = {}
        self._lock = RLock()

    def save(
        self,
        record: OnboardingIntelligenceRecord,
        *,
        expected_version: int | None,
    ) -> OnboardingIntelligenceRecord:
        candidate = OnboardingIntelligenceRecord.model_validate(record)
        with self._lock:
            current = self._records.get(candidate.case_id)
            if expected_version is None:
                valid = current is None and candidate.version == 1
            else:
                valid = (
                    current is not None
                    and current.version == expected_version
                    and candidate.version == expected_version + 1
                )
            if not valid:
                raise OnboardingIntelligenceRepositoryConflictError
            self._records[candidate.case_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> OnboardingIntelligenceRecord | None:
        with self._lock:
            current = self._records.get(case_id)
            return current.model_copy(deep=True) if current is not None else None

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._records.pop(case_id, None)
