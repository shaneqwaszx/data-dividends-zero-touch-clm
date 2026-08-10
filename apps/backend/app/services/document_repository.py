"""Process-local repository for minimum document review records only."""

from typing import Protocol
from uuid import UUID

from app.domain.documents import DocumentProcessingRecord


class DocumentProcessingRepository(Protocol):
    def save(self, record: DocumentProcessingRecord) -> None: ...

    def get(self, document_id: UUID) -> DocumentProcessingRecord | None: ...

    def list_for_case(self, case_id: UUID) -> list[DocumentProcessingRecord]: ...


class InMemoryDocumentProcessingRepository:
    """Store copies only; uploaded bytes and raw provider payloads never enter storage."""

    def __init__(self) -> None:
        self._records: dict[UUID, DocumentProcessingRecord] = {}

    def save(self, record: DocumentProcessingRecord) -> None:
        self._records[record.document_id] = record.model_copy(deep=True)

    def get(self, document_id: UUID) -> DocumentProcessingRecord | None:
        record = self._records.get(document_id)
        return record.model_copy(deep=True) if record is not None else None

    def list_for_case(self, case_id: UUID) -> list[DocumentProcessingRecord]:
        records = [
            record.model_copy(deep=True)
            for record in self._records.values()
            if record.case_id == case_id
        ]
        return sorted(records, key=lambda item: (item.created_at, str(item.document_id)))
