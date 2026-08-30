"""Bounded local PDF-text extraction for the input-driven synthetic POC."""

import re
from io import BytesIO

from pypdf import PdfReader

from app.connectors.idp import (
    IdpDocumentInput,
    IdpProcessingError,
    IdpProviderMetadata,
    IdpSourceField,
    IdpSourceResult,
)
from app.domain.documents import DocumentFieldKey, IdpEnvironment

_FIELD_LABELS: dict[DocumentFieldKey, tuple[str, ...]] = {
    DocumentFieldKey.LEGAL_NAME: ("Legal Name", "Company", "Company / Legal Name"),
    DocumentFieldKey.REGISTRATION_NUMBER: ("UEN", "Registration Number"),
    DocumentFieldKey.REGISTERED_ADDRESS: ("Registered Address",),
    DocumentFieldKey.COUNTRY_OF_INCORPORATION: ("Country", "Country of Incorporation"),
}
_MAX_PAGES = 10
_MAX_EXTRACTED_TEXT_CHARACTERS = 64_000


class LocalPdfTextIdpProvider:
    """Extract labelled synthetic-PDF fields without OCR, inference, or network I/O.

    Confidence is project-defined parser evidence: 0.97 for one exact labelled value,
    0.90 for one accepted alternate label, 0.40 for duplicate/ambiguous candidates,
    and 0.00 for a missing value. It is not a calibrated model probability.
    """

    @property
    def metadata(self) -> object:
        return IdpProviderMetadata(provider_name="LOCAL_PDF_TEXT", environment=IdpEnvironment.LOCAL)

    def process(self, document: IdpDocumentInput) -> object:
        text = (
            document.extracted_text
            if document.extracted_text is not None
            else self._extract_text(document.content)
        )
        if not text.strip():
            return self._unavailable_result(document)
        return IdpSourceResult(
            profile=document.profile,
            fields=[self._field_from_text(text, key) for key in DocumentFieldKey],
        )

    def _extract_text(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted or len(reader.pages) > _MAX_PAGES:
                raise IdpProcessingError
            extracted_pages: list[str] = []
            extracted_length = 0
            for page in reader.pages:
                page_text = page.extract_text() or ""
                extracted_length += len(page_text)
                if extracted_length > _MAX_EXTRACTED_TEXT_CHARACTERS:
                    raise IdpProcessingError
                extracted_pages.append(page_text)
            return "\n".join(extracted_pages)
        except IdpProcessingError:
            raise
        except Exception as exc:
            raise IdpProcessingError from exc

    def _unavailable_result(self, document: IdpDocumentInput) -> IdpSourceResult:
        return IdpSourceResult(
            profile=document.profile,
            fields=[
                IdpSourceField(
                    field_key=key,
                    value=None,
                    confidence=0.0,
                    source_reference="DOCUMENT_TEXT_UNAVAILABLE",
                )
                for key in DocumentFieldKey
            ],
        )

    def _field_from_text(self, text: str, key: DocumentFieldKey) -> IdpSourceField:
        candidates: list[tuple[str, bool]] = []
        for index, label in enumerate(_FIELD_LABELS[key]):
            pattern = re.compile(rf"(?im)^\s*{re.escape(label)}\s*:\s*([^\r\n]+)\s*$")
            candidates.extend(
                (match.group(1).strip(), index == 0)
                for match in pattern.finditer(text)
            )
        distinct = list(dict.fromkeys(value for value, _ in candidates if value))
        if not distinct:
            return IdpSourceField(
                field_key=key,
                value=None,
                confidence=0.0,
                source_reference="LABEL_MISSING",
            )
        if len(distinct) > 1:
            return IdpSourceField(
                field_key=key,
                value=distinct[0],
                confidence=0.40,
                page_number=1,
                source_reference="AMBIGUOUS_LABELLED_VALUES",
            )
        exact_label = any(value == distinct[0] and exact for value, exact in candidates)
        return IdpSourceField(
            field_key=key,
            value=distinct[0],
            confidence=0.97 if exact_label else 0.90,
            page_number=1,
            source_reference="UNIQUE_LABELLED_TEXT",
        )
