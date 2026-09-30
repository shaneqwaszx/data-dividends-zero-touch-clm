"""Process-local defensive repository for case-linked ownership records."""

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.ownership import OwnershipAnalysisRecord, OwnershipAnalysisState


class OwnershipRepositoryConflictError(Exception):
    """An expected version/state no longer owns the repository transition."""


class OwnershipAnalysisRepository(Protocol):
    def save(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int | None,
    ) -> OwnershipAnalysisRecord: ...

    def replace_review_required(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int,
    ) -> OwnershipAnalysisRecord: ...

    def get_for_case(self, case_id: UUID) -> OwnershipAnalysisRecord | None: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryOwnershipAnalysisRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, OwnershipAnalysisRecord] = {}
        self._lock = RLock()

    def save(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int | None,
    ) -> OwnershipAnalysisRecord:
        """Atomically create or compare-and-set a nonterminal record."""

        with self._lock:
            current = self._records.get(record.case_id)
            if expected_version is None:
                if current is not None or record.version != 0:
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

            persisted = record.model_copy(update={"version": next_version}, deep=True)
            self._records[record.case_id] = persisted
            return persisted.model_copy(deep=True)

    def replace_review_required(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int,
    ) -> OwnershipAnalysisRecord:
        """Atomically replace only a current review-required source, retaining its snapshot."""

        with self._lock:
            current = self._records.get(record.case_id)
            if not _is_valid_review_replacement(current, record, expected_version):
                raise OwnershipRepositoryConflictError
            persisted = record.model_copy(update={"version": expected_version + 1}, deep=True)
            self._records[record.case_id] = persisted
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> OwnershipAnalysisRecord | None:
        with self._lock:
            record = self._records.get(case_id)
            return record.model_copy(deep=True) if record is not None else None

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._records.pop(case_id, None)


def _is_valid_review_replacement(
    current: OwnershipAnalysisRecord | None,
    replacement: OwnershipAnalysisRecord,
    expected_version: int,
) -> bool:
    if (
        current is None
        or current.version != expected_version
        or current.state != OwnershipAnalysisState.REVIEW_REQUIRED
        or replacement.version != expected_version
        or replacement.analysis_id == current.analysis_id
        or replacement.state != OwnershipAnalysisState.LOADING
        or replacement.manual_review_receipt is None
        or not replacement.prior_analyses
    ):
        return False
    retained = replacement.prior_analyses[-1]
    return retained.analysis_id == current.analysis_id and retained.version == current.version
