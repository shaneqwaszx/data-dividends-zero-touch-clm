"""Each local-check rejection reaches the RM as a fixed, specific code and message.

The worker reports only a fixed exit code; no document content, file names, object ids or
library text may cross into the API response.
"""

import sys
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    StreamObject,
    TextStringObject,
)

from app.config import Settings
from app.connectors import local_document_worker
from app.connectors.idp import LocalDocumentProcessingError
from app.connectors.local_document_runtime import (
    DOCUMENT_REJECTION_CODES,
    isolated_document_pages,
    validate_local_media,
)
from app.connectors.local_process import run_bounded_process
from app.main import create_app
from app.services import document_media
from app.services.document_errors import (
    DOCUMENT_REJECTION_MESSAGES,
    DOCUMENT_UNREADABLE_MESSAGE,
)

SECRET_TEXT = "SYNTHETIC-SECRET-MARKER-7f3a"
LIBRARY_WORDS = (
    "pypdf",
    "pdfium",
    "PdfReadError",
    "Traceback",
    "PIL",
    "Pillow",
    "DecompressionBomb",
    "ValueError",
    "unsafe pdf object",
    "pdf bounds",
    "image bounds",
    "/URI",
    "example.invalid",
)


def _pdf(writer: PdfWriter) -> bytes:
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _blank_pdf(pages: int = 1, *, width: float = 612, height: float = 792) -> PdfWriter:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    return writer


def eleven_page_pdf() -> bytes:
    return _pdf(_blank_pdf(11))


def encrypted_pdf() -> bytes:
    writer = _blank_pdf()
    writer.encrypt(SECRET_TEXT)
    return _pdf(writer)


def link_annotation_pdf() -> bytes:
    # The shape a "Save as PDF" from a dashboard tool produces for a hyperlink.
    writer = _blank_pdf()
    link = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (10, 10, 100, 30)]),
            NameObject("/A"): DictionaryObject(
                {
                    NameObject("/S"): NameObject("/URI"),
                    NameObject("/URI"): TextStringObject(
                        f"https://example.invalid/{SECRET_TEXT}"
                    ),
                }
            ),
        }
    )
    writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(link)])  # noqa: SLF001
    return _pdf(writer)


def oversized_page_pdf() -> bytes:
    # 4000pt at the 150 DPI render is 8334px, over the 8000px dimension limit.
    return _pdf(_blank_pdf(width=4000, height=800))


def truncated_pdf() -> bytes:
    content = eleven_page_pdf()
    return content[: len(content) // 2]


def oversized_png() -> bytes:
    output = BytesIO()
    with Image.new("RGB", (8001, 1), "white") as image:
        image.save(output, format="PNG")
    return output.getvalue()


def text_heavy_pdf(pages: int = 10, characters_per_page: int = 7000) -> bytes:
    writer = PdfWriter()
    font = writer._add_object(  # noqa: SLF001
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    for _ in range(pages):
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = StreamObject()
        stream.set_data(b"BT /F1 2 Tf 5 780 Td (" + b"A" * characters_per_page + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001
    return _pdf(writer)


def hand_built_pdf(objects: list[str]) -> bytes:
    """The same minimal writer as apps/frontend/e2e/upload-rejection.e2e.ts buildPdf."""
    body = "%PDF-1.7\n"
    offsets: list[int] = []
    for index, value in enumerate(objects, 1):
        offsets.append(len(body.encode("latin-1")))
        body += f"{index} 0 obj\n{value}\nendobj\n"
    xref = len(body.encode("latin-1"))
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    body += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    body += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return body.encode("latin-1")


def e2e_link_pdf() -> bytes:
    return hand_built_pdf(
        [
            "<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Annots [4 0 R] >>",
            "<< /Type /Annot /Subtype /Link /Rect [10 10 100 30] "
            "/A << /S /URI /URI (https://example.invalid/) >> >>",
        ]
    )


REJECTIONS = [
    ("e2e-link.pdf", "application/pdf", e2e_link_pdf, "DOCUMENT_ACTIVE_CONTENT"),
    ("eleven-pages.pdf", "application/pdf", eleven_page_pdf, "DOCUMENT_TOO_MANY_PAGES"),
    ("protected.pdf", "application/pdf", encrypted_pdf, "DOCUMENT_ENCRYPTED"),
    ("Forecast in Tableau.pdf", "application/pdf", link_annotation_pdf, "DOCUMENT_ACTIVE_CONTENT"),
    ("wide-page.pdf", "application/pdf", oversized_page_pdf, "DOCUMENT_PAGE_TOO_LARGE"),
    ("truncated.pdf", "application/pdf", truncated_pdf, "DOCUMENT_STRUCTURE_INVALID"),
    ("wide-image.png", "image/png", oversized_png, "DOCUMENT_PAGE_TOO_LARGE"),
]


@pytest.mark.parametrize(("name", "media_type", "build", "code"), REJECTIONS)
def test_upload_rejection_has_specific_code_and_fixed_message_only(
    name: str, media_type: str, build: object, code: str
) -> None:
    assert callable(build)
    content = build()
    client = TestClient(create_app(Settings(app_env="test")))
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]

    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": media_type, "X-Document-Name": name},
        content=content,
    )

    assert response.status_code == 422
    expected_message = DOCUMENT_REJECTION_MESSAGES.get(code, DOCUMENT_UNREADABLE_MESSAGE)
    assert response.json()["detail"] == {"code": code, "message": expected_message}
    body = response.text
    assert name not in body
    assert SECRET_TEXT not in body
    for word in LIBRARY_WORDS:
        assert word not in body


def test_every_specific_code_has_plain_wording_with_a_next_step() -> None:
    assert set(DOCUMENT_REJECTION_MESSAGES) == set(DOCUMENT_REJECTION_CODES.values()) | {
        "DOCUMENT_PROCESSING_TIMEOUT",
        "DOCUMENT_RUNTIME_UNAVAILABLE",
    }
    for message in (*DOCUMENT_REJECTION_MESSAGES.values(), DOCUMENT_UNREADABLE_MESSAGE):
        assert message.endswith(".") and "bounded" not in message


def test_worker_and_runtime_exit_code_maps_agree_and_avoid_reserved_codes() -> None:
    worker = local_document_worker.REJECTION_EXIT_CODES
    assert {
        exit_code: f"DOCUMENT_{reason}" for reason, exit_code in worker.items()
    } == DOCUMENT_REJECTION_CODES
    # 0 success, 1 interpreter crash/uncaught error, 2 the worker's malformed exit,
    # negative values are signals (shell=False, so never 128+n).
    assert local_document_worker.EXIT_MALFORMED == 2
    assert not set(worker.values()) & {0, 1, 2}
    assert all(0 < exit_code < 126 for exit_code in worker.values())


@pytest.mark.parametrize("code", sorted(DOCUMENT_REJECTION_CODES.values()))
def test_specific_codes_survive_the_processing_error_allowlist(code: str) -> None:
    assert LocalDocumentProcessingError(code).code == code


@pytest.mark.parametrize(
    ("program", "expected"),
    [
        ("raise SystemExit(12)", "DOCUMENT_ACTIVE_CONTENT"),
        ("raise SystemExit(2)", "DOCUMENT_STRUCTURE_INVALID"),
        ("raise SystemExit(7)", "DOCUMENT_STRUCTURE_INVALID"),
        ("raise SystemExit(1)", "DOCUMENT_STRUCTURE_INVALID"),
        ("import os, signal; os.kill(os.getpid(), signal.SIGTERM)", "DOCUMENT_STRUCTURE_INVALID"),
    ],
)
def test_unmapped_exit_codes_fall_back_to_structure_invalid(program: str, expected: str) -> None:
    if "signal" in program and sys.platform == "win32":
        pytest.skip("POSIX signal exit")
    with pytest.raises(LocalDocumentProcessingError) as error:
        run_bounded_process(
            [sys.executable, "-B", "-c", program],
            timeout_seconds=10,
            output_limit=1024,
            unavailable_code="DOCUMENT_RUNTIME_UNAVAILABLE",
            timeout_code="DOCUMENT_PROCESSING_TIMEOUT",
            failed_code="DOCUMENT_STRUCTURE_INVALID",
            failed_codes=DOCUMENT_REJECTION_CODES,
        )
    assert error.value.code == expected


@pytest.mark.parametrize(
    ("code", "message"),
    [
        (
            "DOCUMENT_PROCESSING_TIMEOUT",
            "Processing this file took too long. Try uploading it again; if it keeps "
            "happening, upload a smaller or simpler copy.",
        ),
        (
            "DOCUMENT_RUNTIME_UNAVAILABLE",
            "Document processing isn't available right now. Try again in a moment.",
        ),
    ],
)
def test_timeout_and_unavailable_keep_their_codes_with_friendly_messages(
    monkeypatch: pytest.MonkeyPatch, code: str, message: str
) -> None:
    # The worker itself is not slowed down or removed; the runtime's own error is raised.
    def refuse(content: bytes, media_type: str) -> None:
        raise LocalDocumentProcessingError(code)

    monkeypatch.setattr(document_media, "validate_local_media", refuse)
    client = TestClient(create_app(Settings(app_env="test")))
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
    case_id = created.json()["case"]["case_id"]
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": "application/pdf", "X-Document-Name": "profile.pdf"},
        content=_pdf(_blank_pdf()),
    )
    assert response.status_code == 422
    assert response.json()["detail"] == {"code": code, "message": message}


def test_text_limit_is_checked_at_extraction_with_its_own_code() -> None:
    content = text_heavy_pdf()
    validate_local_media(content, "application/pdf")  # Validation does not read text.
    with (
        pytest.raises(LocalDocumentProcessingError) as error,
        isolated_document_pages(content, "application/pdf"),
    ):
        pass
    assert error.value.code == "DOCUMENT_CONTENT_TOO_LARGE"
