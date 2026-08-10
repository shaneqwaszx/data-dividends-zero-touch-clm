"""Trusted public errors for the Phase 03 document boundary."""

from uuid import UUID


class DocumentRequestError(Exception):
    """A safe, controlled request failure before or outside IDP processing."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.public_message = message


class DocumentProcessingInfrastructureError(Exception):
    """Safe metadata for a retrievable terminal document processing failure."""

    def __init__(
        self,
        *,
        case_id: UUID,
        document_id: UUID,
        correlation_id: UUID,
        code: str,
        message: str,
    ) -> None:
        super().__init__(code)
        self.case_id = case_id
        self.document_id = document_id
        self.correlation_id = correlation_id
        self.code = code
        self.public_message = message
