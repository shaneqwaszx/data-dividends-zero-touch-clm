"""R3a: DOCX XML parts refuse any DTD, entity or non-OOXML encoding (CVE-2026-115506)."""

import time
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from app.services.document_errors import DocumentRequestError
from app.services.document_media import DOCX_MEDIA_TYPE, DocumentMediaRouter

XML_INVALID = "The DOCX document XML could not be validated safely."
CONTAINER_INVALID = "The DOCX container could not be validated safely."
CONTAINER_MALFORMED = "The DOCX container is malformed or exceeds POC limits."
MACRO = "Macro-enabled documents are not supported."
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
)
PARAGRAPH = "<w:p><w:r><w:t>Synthetic text</w:t></w:r></w:p>"
BODY = f'<w:document xmlns:w="{W_NS}"><w:body>{PARAGRAPH}</w:body></w:document>'
DOCUMENT = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + BODY
LAUGHS = (
    "<!DOCTYPE w:document ["
    '<!ENTITY a "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa">'
    + "".join(f'<!ENTITY {chr(98 + i)} "{("&" + chr(97 + i) + ";") * 10}">' for i in range(8))
    + "]>"
)
LAUGHS_DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8"?>\n' + LAUGHS + BODY.replace("Synthetic text", "&i;")
)


def _docx(
    members: dict[str, bytes | str] | None = None,
    *,
    extra: tuple[tuple[str, bytes | str], ...] = (),
    compression: int = ZIP_DEFLATED,
) -> bytes:
    parts: dict[str, bytes | str] = {
        "[Content_Types].xml": CONTENT_TYPES,
        "word/document.xml": DOCUMENT,
    }
    parts.update(members or {})
    output = BytesIO()
    with ZipFile(output, "w", compression) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
        for name, data in extra:
            archive.writestr(name, data)
    return output.getvalue()


def _extract(content: bytes) -> str:
    result = DocumentMediaRouter().extract(
        display_name="synthetic.docx", content_type=DOCX_MEDIA_TYPE, content=content
    )
    assert result.extracted_text is not None
    return result.extracted_text


def _rejected(content: bytes) -> DocumentRequestError:
    with pytest.raises(DocumentRequestError) as raised:
        _extract(content)
    assert raised.value.code == "DOCUMENT_STRUCTURE_INVALID"
    return raised.value


def _utf16(text: str, codec: str = "utf-16", declared: str = "UTF-16") -> bytes:
    return text.replace('encoding="UTF-8"', f'encoding="{declared}"').encode(codec)


def test_valid_utf8_docx_text_is_unchanged() -> None:
    assert _extract(_docx()) == "Synthetic text"


@pytest.mark.parametrize(
    ("codec", "declared", "bom"),
    [
        ("utf-16", "UTF-16", b""),
        ("utf-16-le", "UTF-16", b"\xff\xfe"),
        ("utf-16-be", "UTF-16", b"\xfe\xff"),
    ],
)
def test_valid_utf16_parts_are_still_accepted(codec: str, declared: str, bom: bytes) -> None:
    document = bom + _utf16(DOCUMENT, codec, declared)
    types = bom + _utf16(CONTENT_TYPES, codec, declared)
    content = _docx({"word/document.xml": document, "[Content_Types].xml": types})
    assert _extract(content) == "Synthetic text"


def test_document_without_xml_declaration_is_accepted() -> None:
    assert _extract(_docx({"word/document.xml": BODY})) == "Synthetic text"


def test_entity_amplification_is_refused_before_expansion() -> None:
    started = time.perf_counter()
    error = _rejected(_docx({"word/document.xml": LAUGHS_DOCUMENT}))
    assert error.public_message == XML_INVALID
    assert time.perf_counter() - started < 1.0


@pytest.mark.parametrize(
    ("codec", "bom"),
    [("utf-16", b""), ("utf-16-le", b"\xff\xfe"), ("utf-16-be", b"\xfe\xff")],
)
def test_doctype_cannot_hide_behind_utf16(codec: str, bom: bytes) -> None:
    payload = bom + _utf16(LAUGHS_DOCUMENT, codec)
    assert _rejected(_docx({"word/document.xml": payload})).public_message == XML_INVALID


@pytest.mark.parametrize(
    "member",
    [
        "[Content_Types].xml",
        "_rels/.rels",
        "word/_rels/document.xml.rels",
        "word/styles.xml",
        "customXml/item1.xml",
        "docProps/core.xml",
        "WORD/SETTINGS.XML",
    ],
)
def test_doctype_is_refused_in_every_xml_member(member: str) -> None:
    payload = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE r [<!ENTITY x "y">]><r>&x;</r>'
    if member == "[Content_Types].xml":
        content = _docx({member: payload})
    else:
        content = _docx(extra=((member, payload),))
    assert _rejected(content).public_message == XML_INVALID


@pytest.mark.parametrize(
    "prolog",
    [
        '<!DOCTYPE w:document SYSTEM "file:///etc/passwd">',
        '<!DOCTYPE w:document PUBLIC "-//x//y" "http://127.0.0.1/x.dtd">',
        '<!DOCTYPE w:document [<!ENTITY % p "x">]>',
        '<!DOCTYPE w:document [<!NOTATION n SYSTEM "x">]>',
        "<!DOCTYPE w:document>",
    ],
)
def test_any_doctype_form_is_refused(prolog: str) -> None:
    payload = '<?xml version="1.0" encoding="UTF-8"?>\n' + prolog + BODY
    assert _rejected(_docx({"word/document.xml": payload})).public_message == XML_INVALID


def test_undeclared_entity_reference_is_refused() -> None:
    payload = DOCUMENT.replace("Synthetic text", "&xxe;")
    assert _rejected(_docx({"word/document.xml": payload})).public_message == XML_INVALID


@pytest.mark.parametrize("declared", ["ISO-8859-1", "US-ASCII", "windows-1252", "UTF-7", "UTF-32"])
def test_non_ooxml_declared_encodings_are_refused(declared: str) -> None:
    payload = DOCUMENT.replace('encoding="UTF-8"', f'encoding="{declared}"').encode("ascii")
    assert _rejected(_docx({"word/document.xml": payload})).public_message == XML_INVALID


def test_utf32_bytes_are_refused() -> None:
    payload = BODY.encode("utf-32")
    assert _rejected(_docx({"word/document.xml": payload})).public_message == XML_INVALID


def test_macro_marker_in_utf16_content_types_is_still_detected() -> None:
    types = CONTENT_TYPES.replace("document.main+xml", "document.macroEnabled.main+xml")
    content = _docx({"[Content_Types].xml": b"\xff\xfe" + _utf16(types, "utf-16-le")})
    assert _rejected(content).public_message == MACRO


def test_utf8_macro_marker_keeps_existing_message() -> None:
    types = CONTENT_TYPES.replace("document.main+xml", "document.macroEnabled.main+xml")
    assert _rejected(_docx({"[Content_Types].xml": types})).public_message == MACRO


def test_duplicate_member_names_are_refused() -> None:
    content = _docx(extra=(("word/document.xml", LAUGHS_DOCUMENT),))
    assert _rejected(content).public_message == CONTAINER_MALFORMED


def test_corrupt_deflate_stream_is_a_bounded_client_error() -> None:
    content = bytearray(_docx(extra=(("word/styles.xml", "<s>" + "x" * 4000 + "</s>"),)))
    marker = content.find(b"word/styles.xml") + len(b"word/styles.xml")
    for offset in range(marker + 8, marker + 40):
        content[offset] ^= 0x5A
    error = _rejected(bytes(content))
    assert error.public_message in {CONTAINER_INVALID, XML_INVALID, CONTAINER_MALFORMED}


def test_non_xml_binary_members_are_not_parsed() -> None:
    content = _docx(extra=(("word/media/image1.png", b"\x89PNG\r\n\x1a\n<!DOCTYPE"),))
    assert _extract(content) == "Synthetic text"


def test_existing_uncompressed_limit_still_applies() -> None:
    big = "<r>" + "a" * (10 * 1024 * 1024) + "</r>"
    error = _rejected(_docx(extra=(("word/big.xml", big),)))
    assert error.public_message == "The DOCX container exceeds the extraction limit."


def test_stored_members_are_checked_too() -> None:
    content = _docx({"word/document.xml": LAUGHS_DOCUMENT}, compression=ZIP_STORED)
    assert _rejected(content).public_message == XML_INVALID
