"""Process-local defensive repository for case-linked ownership records."""

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.models import OnboardingCase
from app.domain.ownership import (
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    PriorOwnershipAnalysisSnapshot,
)


class OwnershipRepositoryConflictError(Exception):
    """An expected version/state no longer owns the repository transition."""


class OwnershipAnalysisRepository(Protocol):
    def replace_document_bound(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int,
    ) -> OwnershipAnalysisRecord: ...
    def replace_identity_bound(
        self, record: OwnershipAnalysisRecord, *, expected_version: int,
    ) -> OwnershipAnalysisRecord: ...
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
                } or not poc_ledger_preserved(current, record):
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

    def replace_document_bound(
        self,
        record: OwnershipAnalysisRecord,
        *,
        expected_version: int,
    ) -> OwnershipAnalysisRecord:
        with self._lock:
            current = self._records.get(record.case_id)
            if not _is_valid_document_replacement(current, record, expected_version):
                raise OwnershipRepositoryConflictError
            persisted = record.model_copy(update={"version": expected_version + 1}, deep=True)
            self._records[record.case_id] = persisted
            return persisted.model_copy(deep=True)

    def get_for_case(self, case_id: UUID) -> OwnershipAnalysisRecord | None:
        with self._lock:
            record = self._records.get(case_id)
            return record.model_copy(deep=True) if record is not None else None

    def replace_identity_bound(
        self, record: OwnershipAnalysisRecord, *, expected_version: int,
    ) -> OwnershipAnalysisRecord:
        with self._lock:
            current = self._records.get(record.case_id)
            if not _is_valid_identity_replacement(current, record, expected_version):
                raise OwnershipRepositoryConflictError
            persisted = record.model_copy(update={"version": expected_version + 1}, deep=True)
            self._records[record.case_id] = persisted
            return persisted.model_copy(deep=True)

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            self._records.pop(case_id, None)


def poc_ledger_preserved(
    current: OwnershipAnalysisRecord, replacement: OwnershipAnalysisRecord
) -> bool:
    """D-120: an established POC ledger only ever grows; nothing may shrink or rewrite it."""

    kept = current.poc_interest_ledger
    new = replacement.poc_interest_ledger
    return kept is None or (new is not None and new[: len(kept)] == kept)


def _is_valid_review_replacement(
    current: OwnershipAnalysisRecord | None,
    replacement: OwnershipAnalysisRecord,
    expected_version: int,
) -> bool:
    if (
        current is None
        or current.version != expected_version
        or current.state
        not in {OwnershipAnalysisState.REVIEW_REQUIRED, OwnershipAnalysisState.ANALYZED}
        or replacement.version != expected_version
        or replacement.analysis_id == current.analysis_id
        or replacement.state != OwnershipAnalysisState.LOADING
        or replacement.manual_review_receipt is None
        or not replacement.prior_analyses
        or not poc_ledger_preserved(current, replacement)
    ):
        return False
    retained = replacement.prior_analyses[-1]
    return retained.analysis_id == current.analysis_id and retained.version == current.version


def _is_valid_document_replacement(
    current: OwnershipAnalysisRecord | None,
    replacement: OwnershipAnalysisRecord,
    expected_version: int,
) -> bool:
    if (
        current is None
        or current.version != expected_version
        or current.case_id != replacement.case_id
        or replacement.version != expected_version
        or current.state
        not in {OwnershipAnalysisState.REVIEW_REQUIRED, OwnershipAnalysisState.ANALYZED}
        or replacement.state != OwnershipAnalysisState.LOADING
        or replacement.analysis_id == current.analysis_id
        or replacement.identity_registration_number != ownership_identity(current)
        or replacement.identity_correction_version != current.identity_correction_version
        or replacement.document_bindings == current.document_bindings
        or not replacement.prior_analyses
        or not poc_ledger_preserved(current, replacement)
    ):
        return False
    prior = replacement.prior_analyses[-1]
    return prior.analysis_id == current.analysis_id and prior.version == current.version


def ownership_identity(
    record: OwnershipAnalysisRecord | PriorOwnershipAnalysisSnapshot,
) -> str | None:
    return record.identity_registration_number or next(
        (party.registration_number for party in record.parties
         if party.party_id == record.root_party_id), None,
    )


def ownership_is_current(
    record: OwnershipAnalysisRecord | PriorOwnershipAnalysisSnapshot, parent: OnboardingCase,
) -> bool:
    """Shared service/persistence eligibility; caller retains the owning lock/CAS."""
    if ownership_identity(record) != parent.requested_uen:
        return False
    if record.provider_name not in {None, "ACRA_REGISTRY_ACQUISITION"}:
        later = (parent.identity_corrections[record.identity_correction_version:]
                 if record.identity_correction_version is not None else
                 tuple(item for item in parent.identity_corrections
                       if item.corrected_at > record.created_at))
        return not any(item.previous_identity is None or
                       item.previous_identity.registration_number !=
                       item.corrected_identity.registration_number for item in later)
    if record.identity_correction_version is None:
        return not any(item.corrected_at > record.created_at
                       for item in parent.identity_corrections)
    return record.identity_correction_version == len(parent.identity_corrections)


def _is_valid_identity_replacement(
    current: OwnershipAnalysisRecord | None, replacement: OwnershipAnalysisRecord,
    expected_version: int,
) -> bool:
    if (current is None or current.version != expected_version
        or replacement.case_id != current.case_id or replacement.version != expected_version
        or replacement.state != OwnershipAnalysisState.LOADING
        or replacement.analysis_id == current.analysis_id
        or not replacement.identity_registration_number
        or (ownership_identity(current) == replacement.identity_registration_number
            and not (replacement.identity_correction_version is not None
                     and (current.identity_correction_version is None
                          or current.identity_correction_version
                          < replacement.identity_correction_version)))
        or not replacement.prior_analyses
        or not poc_ledger_preserved(current, replacement)):
        return False
    prior = replacement.prior_analyses[-1]
    return prior.analysis_id == current.analysis_id and prior.version == current.version
