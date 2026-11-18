"""Trusted public errors for the Phase 03 document boundary."""

from uuid import UUID

# Fixed RM-facing wording for each reason a file fails the local document checks.
# Codes are application-owned; no document content or library text is ever included.
DOCUMENT_REJECTION_MESSAGES = {
    "DOCUMENT_TOO_MANY_PAGES": (
        "This file has more than 10 pages. Upload only the pages needed (up to 10)."
    ),
    "DOCUMENT_ENCRYPTED": (
        "This PDF is password-protected. Remove the password and upload it again."
    ),
    "DOCUMENT_ACTIVE_CONTENT": (
        "This PDF contains links or interactive content, which isn't allowed. "
        "Print it to PDF ('Save as PDF') and upload that copy."
    ),
    "DOCUMENT_PAGE_TOO_LARGE": (
        "A page in this file is too large. Export it at a standard page size "
        "(A4 or Letter) and upload it again."
    ),
    "DOCUMENT_CONTENT_TOO_LARGE": (
        "This file is too large to process. Upload fewer or smaller pages."
    ),
    # Not about the file's content: the RM keeps "Try upload again" for these two.
    "DOCUMENT_PROCESSING_TIMEOUT": (
        "Processing this file took too long. Try uploading it again; if it keeps "
        "happening, upload a smaller or simpler copy."
    ),
    "DOCUMENT_RUNTIME_UNAVAILABLE": (
        "Document processing isn't available right now. Try again in a moment."
    ),
}
# Upload-time wording for a file that fails the checks for any other (malformed) reason.
DOCUMENT_UNREADABLE_MESSAGE = (
    "This file isn't a readable PDF or image. Re-export it and upload it again."
)


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
