"""Bounded media validation and local text extraction for supported POC documents."""

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from unicodedata import category
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from app.connectors.idp import LocalDocumentProcessingError
from app.connectors.local_document_runtime import validate_local_media
from app.services.document_errors import (
    DOCUMENT_REJECTION_MESSAGES,
    DOCUMENT_UNREADABLE_MESSAGE,
    DocumentRequestError,
)

PDF_MEDIA_TYPE = "application/pdf"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TXT_MEDIA_TYPE = "text/plain"
IMAGE_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/tiff"})
SUPPORTED_MEDIA_TYPES = (
    frozenset({PDF_MEDIA_TYPE, DOCX_MEDIA_TYPE, TXT_MEDIA_TYPE}) | IMAGE_MEDIA_TYPES
)
SUPPORTED_EXTENSIONS = {
    ".pdf": PDF_MEDIA_TYPE,
    ".docx": DOCX_MEDIA_TYPE,
    ".txt": TXT_MEDIA_TYPE,
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}
SAFE_DOCUMENT_NAME = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,94}\.(?:pdf|docx|txt|png|jpe?g|tiff?)$", re.IGNORECASE
)
_MAX_DOCX_ENTRIES = 128
_MAX_DOCX_UNCOMPRESSED_BYTES = 10 * 1024 * 1024
_MAX_EXTRACTED_TEXT_CHARACTERS = 64_000
_PROHIBITED_DOCX_PARTS = (
    "vbaproject.bin",
    "word/embeddings/",
    "word/activex/",
)
_WINDOWS_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class ExtractedDocumentContent:
    """Validated transient provider input; source bytes/text are never retained."""

    media_type: str
    content: bytes
    extracted_text: str | None = None


class DocumentMediaRouter:
    """Route one supported media type through its bounded validation/extraction path."""

    def validate_metadata(self, *, display_name: str, content_type: str) -> str:
        name = display_name.strip()
        if len(name) > 99 or not SAFE_DOCUMENT_NAME.fullmatch(name):
            raise DocumentRequestError(
                code="DOCUMENT_NAME_INVALID",
                message="The upload must use a safe supported-document display name.",
            )
        extension = PurePosixPath(name.lower()).suffix
        declared = content_type.split(";", 1)[0].lower().strip()
        expected = SUPPORTED_EXTENSIONS.get(extension)
        if expected is None or declared not in SUPPORTED_MEDIA_TYPES or declared != expected:
            raise DocumentRequestError(
                code="DOCUMENT_MEDIA_TYPE_UNSUPPORTED",
                message=("Only matching PDF, DOCX, UTF-8 TXT, PNG, JPEG, "
                         "and TIFF uploads are accepted."),
            )
        return expected

    def extract(
        self, *, display_name: str, content_type: str, content: bytes
    ) -> ExtractedDocumentContent:
        media_type = self.validate_metadata(display_name=display_name, content_type=content_type)
        if not content:
            raise DocumentRequestError(
                code="DOCUMENT_EMPTY",
                message="The uploaded document is empty.",
            )
        if media_type == PDF_MEDIA_TYPE:
            self._validate_pdf_structure(content)
            return ExtractedDocumentContent(media_type=media_type, content=content)
        if media_type in IMAGE_MEDIA_TYPES:
            self._validate_isolated_media(content, media_type)
            return ExtractedDocumentContent(media_type=media_type, content=content)
        if media_type == DOCX_MEDIA_TYPE:
            return ExtractedDocumentContent(
                media_type=media_type,
                content=content,
                extracted_text=self._extract_docx_text(content),
            )
        return ExtractedDocumentContent(
            media_type=media_type,
            content=content,
            extracted_text=self._extract_txt_text(content),
        )

    def _validate_pdf_structure(self, content: bytes) -> None:
        self._validate_isolated_media(content, PDF_MEDIA_TYPE)

    @staticmethod
    def _validate_isolated_media(content: bytes, media_type: str) -> None:
        try:
            validate_local_media(content, media_type)
        except LocalDocumentProcessingError as error:
            raise DocumentRequestError(
                code=error.code,
                message=(
                    DOCUMENT_REJECTION_MESSAGES.get(error.code)
                    or (
                        DOCUMENT_UNREADABLE_MESSAGE
                        if error.code == "DOCUMENT_STRUCTURE_INVALID"
                        else "The uploaded document could not pass the bounded local "
                        "structure checks."
                    )
                ),
            ) from None

    def _extract_docx_text(self, content: bytes) -> str:
        try:
            with ZipFile(BytesIO(content)) as archive:
                infos = archive.infolist()
                if not infos or len(infos) > _MAX_DOCX_ENTRIES:
                    raise DocumentRequestError(
                        code="DOCUMENT_STRUCTURE_INVALID",
                        message="The DOCX container is malformed or exceeds POC limits.",
                    )
                total_size = 0
                normalized_names: set[str] = set()
                for info in infos:
                    name = info.filename
                    lowered = name.lower()
                    validation_name = name.replace("\\", "/")
                    parts = PurePosixPath(validation_name).parts
                    if (
                        not name
                        or "\x00" in name
                        or "\\" in name
                        or validation_name.startswith("/")
                        or "//" in validation_name
                        or _WINDOWS_DRIVE_PREFIX.match(validation_name)
                        or ".." in parts
                        or info.flag_bits & 0x1
                        or any(part in lowered for part in _PROHIBITED_DOCX_PARTS)
                    ):
                        raise DocumentRequestError(
                            code="DOCUMENT_STRUCTURE_INVALID",
                            message="The DOCX container contains an unsafe part.",
                        )
                    total_size += info.file_size
                    if total_size > _MAX_DOCX_UNCOMPRESSED_BYTES:
                        raise DocumentRequestError(
                            code="DOCUMENT_STRUCTURE_INVALID",
                            message="The DOCX container exceeds the extraction limit.",
                        )
                    normalized_names.add(name)
                required = {"[Content_Types].xml", "word/document.xml"}
                if not required.issubset(normalized_names):
                    raise DocumentRequestError(
                        code="DOCUMENT_STRUCTURE_INVALID",
                        message="The DOCX container is missing required OOXML parts.",
                    )
                content_types = archive.read("[Content_Types].xml").lower()
                if b"macroenabled" in content_types or b"vbaproject" in content_types:
                    raise DocumentRequestError(
                        code="DOCUMENT_STRUCTURE_INVALID",
                        message="Macro-enabled documents are not supported.",
                    )
                document_xml = archive.read("word/document.xml")
        except DocumentRequestError:
            raise
        except (BadZipFile, KeyError, OSError, RuntimeError):
            raise DocumentRequestError(
                code="DOCUMENT_STRUCTURE_INVALID",
                message="The DOCX container could not be validated safely.",
            ) from None
        try:
            root = ElementTree.fromstring(document_xml)
        except ElementTree.ParseError:
            raise DocumentRequestError(
                code="DOCUMENT_STRUCTURE_INVALID",
                message="The DOCX document XML could not be validated safely.",
            ) from None
        values = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
        text = "\n".join(values)
        if len(text) > _MAX_EXTRACTED_TEXT_CHARACTERS:
            raise DocumentRequestError(
                code="DOCUMENT_STRUCTURE_INVALID",
                message="The extracted DOCX text exceeds the POC limit.",
            )
        return text

    def _extract_txt_text(self, content: bytes) -> str:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise DocumentRequestError(
                code="DOCUMENT_TEXT_INVALID",
                message="TXT uploads must contain valid UTF-8 text.",
            ) from None
        if any(
            category(character).startswith("C") and character not in "\t\r\n" for character in text
        ):
            raise DocumentRequestError(
                code="DOCUMENT_TEXT_INVALID",
                message="The TXT upload contains unsupported binary or control content.",
            )
        if len(text) > _MAX_EXTRACTED_TEXT_CHARACTERS:
            raise DocumentRequestError(
                code="DOCUMENT_TEXT_INVALID",
                message="The extracted TXT text exceeds the POC limit.",
            )
        return text
