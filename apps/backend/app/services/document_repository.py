"""Process-local repository for minimum document review records only."""

from threading import Lock
from typing import Protocol
from uuid import UUID

from app.domain.documents import DocumentProcessingRecord


class DocumentProcessingRepository(Protocol):
    def save(self, record: DocumentProcessingRecord) -> None: ...

    def get(self, document_id: UUID) -> DocumentProcessingRecord | None: ...

    def list_for_case(self, case_id: UUID) -> list[DocumentProcessingRecord]: ...

    def delete_for_case(self, case_id: UUID) -> None: ...


class InMemoryDocumentProcessingRepository:
    """Store copies only; uploaded bytes and raw provider payloads never enter storage."""

    def __init__(self) -> None:
        self._records: dict[UUID, DocumentProcessingRecord] = {}
        self._insertion_sequence: dict[UUID, int] = {}
        self._next_sequence = 1
        self._lock = Lock()

    def save(self, record: DocumentProcessingRecord) -> None:
        candidate = record.model_copy(deep=True)
        with self._lock:
            if record.document_id not in self._insertion_sequence:
                self._insertion_sequence[record.document_id] = self._next_sequence
                self._next_sequence += 1
            self._records[record.document_id] = candidate

    def get(self, document_id: UUID) -> DocumentProcessingRecord | None:
        with self._lock:
            record = self._records.get(document_id)
            return record.model_copy(deep=True) if record is not None else None

    def list_for_case(self, case_id: UUID) -> list[DocumentProcessingRecord]:
        with self._lock:
            records = [
                (self._insertion_sequence[document_id], record.model_copy(deep=True))
                for document_id, record in self._records.items()
                if record.case_id == case_id
            ]
        return [record for _, record in sorted(records, key=lambda item: item[0])]

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            document_ids = [
                document_id
                for document_id, record in self._records.items()
                if record.case_id == case_id
            ]
            for document_id in document_ids:
                self._records.pop(document_id, None)
                self._insertion_sequence.pop(document_id, None)
