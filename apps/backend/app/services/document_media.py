"""Bounded media validation and local text extraction for supported POC documents."""

import re
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from typing import NoReturn
from unicodedata import category
from xml.etree import ElementTree
from xml.parsers import expat
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
# R3a (CVE-2026-115506, CPython-bundled expat 2.9.0): OOXML parts are UTF-8 or UTF-16 and never
# carry a DTD, so every XML part is pre-parsed by expat itself and any DOCTYPE, entity or notation
# declaration, external entity, or other declared encoding is refused before expansion can start.
_DOCX_XML_MEMBER_SUFFIXES = (".xml", ".rels")
_DOCX_XML_ENCODINGS = frozenset({"utf-8", "utf-16", "utf-16le", "utf-16be"})
_DOCX_XML_INVALID_MESSAGE = "The DOCX document XML could not be validated safely."
_DOCX_MACRO_MARKERS = ("macroenabled", "vbaproject")


class _UnsafeDocxXml(Exception):
    """Internal: a DOCX XML part declared a DTD, an entity or an unsupported encoding."""


def _refuse_declaration(*_arguments: object) -> NoReturn:
    raise _UnsafeDocxXml


def _check_xml_declaration(_version: str, encoding: str | None, _standalone: int) -> None:
    if encoding is not None and encoding.lower() not in _DOCX_XML_ENCODINGS:
        raise _UnsafeDocxXml


def _require_declaration_free_xml(data: bytes) -> None:
    """Fail closed unless expat accepts ``data`` as well-formed XML with no DTD at all.

    Expat decodes the bytes itself (BOM, XML declaration, UTF-16), so the refusal cannot be
    bypassed by re-encoding; bytes it cannot decode or parse are refused as malformed.
    """

    parser = expat.ParserCreate()
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.XmlDeclHandler = _check_xml_declaration
    parser.StartDoctypeDeclHandler = _refuse_declaration
    parser.EntityDeclHandler = _refuse_declaration
    parser.UnparsedEntityDeclHandler = _refuse_declaration
    parser.NotationDeclHandler = _refuse_declaration
    parser.ExternalEntityRefHandler = _refuse_declaration
    try:
        parser.Parse(data, True)
    except (_UnsafeDocxXml, expat.ExpatError):
        raise DocumentRequestError(
            code="DOCUMENT_STRUCTURE_INVALID", message=_DOCX_XML_INVALID_MESSAGE
        ) from None


def _parse_docx_xml(data: bytes) -> ElementTree.Element:
    _require_declaration_free_xml(data)
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError:
        raise DocumentRequestError(
            code="DOCUMENT_STRUCTURE_INVALID", message=_DOCX_XML_INVALID_MESSAGE
        ) from None


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
                    if name in normalized_names:
                        # A repeated name would let the checked part differ from the read one.
                        raise DocumentRequestError(
                            code="DOCUMENT_STRUCTURE_INVALID",
                            message="The DOCX container is malformed or exceeds POC limits.",
                        )
                    normalized_names.add(name)
                required = {"[Content_Types].xml", "word/document.xml"}
                if not required.issubset(normalized_names):
                    raise DocumentRequestError(
                        code="DOCUMENT_STRUCTURE_INVALID",
                        message="The DOCX container is missing required OOXML parts.",
                    )
                # Every XML part, not only the two this service reads, must be DTD-free.
                for info in infos:
                    if info.filename.lower().endswith(_DOCX_XML_MEMBER_SUFFIXES):
                        _require_declaration_free_xml(archive.read(info))
                content_types = archive.read("[Content_Types].xml")
                document_xml = archive.read("word/document.xml")
        except DocumentRequestError:
            raise
        except (BadZipFile, KeyError, OSError, RuntimeError, EOFError, zlib.error):
            raise DocumentRequestError(
                code="DOCUMENT_STRUCTURE_INVALID",
                message="The DOCX container could not be validated safely.",
            ) from None
        types_root = _parse_docx_xml(content_types)
        declared_types = [
            value.lower() for node in types_root.iter() for value in node.attrib.values()
        ]
        raw_types = content_types.lower()
        if any(
            marker.encode("ascii") in raw_types or any(marker in value for value in declared_types)
            for marker in _DOCX_MACRO_MARKERS
        ):
            # The decoded attribute check also holds for a UTF-16 [Content_Types].xml.
            raise DocumentRequestError(
                code="DOCUMENT_STRUCTURE_INVALID",
                message="Macro-enabled documents are not supported.",
            )
        root = _parse_docx_xml(document_xml)
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
