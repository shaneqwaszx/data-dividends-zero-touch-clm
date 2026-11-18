"""Synthetic local OCR, proposed evidence, page provenance and file/process safeguards."""

import os
import shutil
import sys
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject
from test_document_processing import CASE_ID, make_service
from test_phase_08_input_driven import matching_fields, synthetic_pdf

from app.connectors.idp import IdpDocumentInput, IdpSourceResult, LocalDocumentProcessingError
from app.connectors.local_ocr import LocalOcrResult, decode_tesseract_tsv
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.local_process import run_bounded_process
from app.domain.documents import (
    DocumentAutoClearBlocker,
    DocumentFieldKey,
    DocumentProfile,
    ExtractionMethod,
    ExtractionQuality,
    ExtractionScoreKind,
)
from app.services.document_errors import DocumentProcessingInfrastructureError, DocumentRequestError
from app.services.document_media import DocumentMediaRouter


class StubOcr:
    def __init__(self, text: str = "", mean: float | None = None) -> None:
        self.text, self.mean = text, mean
        self.paths: list[Path] = []

    def recognize(self, image_path: Path, *, timeout_seconds: float) -> LocalOcrResult:
        assert image_path.is_file() and image_path.name.startswith("page-")
        assert 0 < timeout_seconds <= 60
        self.paths.append(image_path)
        return LocalOcrResult(self.text, self.mean, len(self.text.split()))


def process(
    content: bytes, media_type: str = "application/pdf", *, ocr: StubOcr | None = None
) -> IdpSourceResult:
    return LocalPdfTextIdpProvider(ocr=ocr).process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=content,
            media_type=media_type,
        )
    )


def image_bytes(
    format_name: str = "PNG", *, size: tuple[int, int] = (100, 80), frames: int = 1
) -> bytes:
    output = BytesIO()
    with Image.new("RGB", size, "white") as image:
        if format_name == "TIFF" and frames > 1:
            image.save(
                output, format=format_name, save_all=True, append_images=[image] * (frames - 1)
            )
        else:
            image.save(output, format=format_name)
    return output.getvalue()


def combine_pdf(*documents: bytes) -> bytes:
    writer = PdfWriter()
    for content in documents:
        writer.append(PdfReader(BytesIO(content)))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_native_pages_and_multiple_candidates_are_real_and_never_select_ambiguity() -> None:
    content = combine_pdf(
        synthetic_pdf(matching_fields()),
        synthetic_pdf(
            {"Legal Name": "SECOND SYNTHETIC NAME PTE. LTD.", "UEN": "202400001A"},
        ),
    )
    ocr = StubOcr()
    result = process(content, ocr=ocr)
    legal_name = next(
        item for item in result.fields if item.field_key == DocumentFieldKey.LEGAL_NAME
    )
    assert legal_name.value is None and legal_name.extraction_quality == ExtractionQuality.AMBIGUOUS
    assert len(legal_name.candidates) == 2
    assert [item.page_number for item in legal_name.candidates] == [1, 2]
    assert all(
        item.extraction_method == ExtractionMethod.NATIVE_PDF_TEXT for item in legal_name.candidates
    )
    assert ocr.paths == []


def test_native_field_page_number_is_not_hardcoded_to_one() -> None:
    result = process(
        combine_pdf(
            synthetic_pdf({"Legal Name": "SYNTHETIC LONG LEGAL NAME"}),
            synthetic_pdf({"UEN": "202400001A", "Country": "SG"}),
        )
    )
    assert (
        next(
            item for item in result.fields if item.field_key == DocumentFieldKey.REGISTRATION_NUMBER
        ).page_number
        == 2
    )


def test_low_ocr_quality_uses_documented_score_and_temporary_images_are_removed() -> None:
    ocr = StubOcr("Legal Name: LOW QUALITY SYNTHETIC COMPANY\nUEN: 202400001A", 35.0)
    result = process(image_bytes(), "image/png", ocr=ocr)
    name = next(item for item in result.fields if item.field_key == DocumentFieldKey.LEGAL_NAME)
    assert name.confidence == pytest.approx(0.97 * 0.35)
    assert name.extraction_quality == ExtractionQuality.LOW
    assert name.raw_ocr_mean_confidence == 35.0
    assert name.score_formula == "LABEL_SCORE_TIMES_OCR_MEAN_OVER_100"
    assert result.pages[0].raw_ocr_word_count == len(ocr.text.split())
    assert all(not path.exists() for path in ocr.paths)


def test_high_quality_mismatch_does_not_lower_extraction_score() -> None:
    service, _ = make_service(provider=LocalPdfTextIdpProvider(), max_bytes=5 * 1024 * 1024)
    fields = matching_fields()
    fields["Legal Name"] = "DIFFERENT SYNTHETIC LEGAL NAME"
    record = service.create_document(
        case_id=CASE_ID,
        display_name="mismatch.pdf",
        content_type="application/pdf",
        content=synthetic_pdf(fields),
    )
    name = next(item for item in record.fields if item.field_key == DocumentFieldKey.LEGAL_NAME)
    assert name.comparison_status.value == "MISMATCH"
    assert name.extraction_quality == ExtractionQuality.HIGH
    assert name.confidence == 0.97
    assert name.score_kind == ExtractionScoreKind.DETERMINISTIC_EVIDENCE_SCORE
    assert name.review_status.value == "PENDING"


def test_missing_and_ambiguous_identity_never_auto_clear() -> None:
    service, _ = make_service(provider=LocalPdfTextIdpProvider(), max_bytes=5 * 1024 * 1024)
    record = service.create_document(
        case_id=CASE_ID,
        display_name="ambiguous.pdf",
        content_type="application/pdf",
        content=synthetic_pdf(
            matching_fields(),
            extra_lines=("Legal Name: SECOND SYNTHETIC NAME",),
        ),
    )
    assessment = service.assess_auto_clear(case_id=CASE_ID, document_id=record.document_id)
    assert not assessment.eligible
    assert DocumentAutoClearBlocker.AMBIGUOUS_EXTRACTION in assessment.blockers
    assert DocumentAutoClearBlocker.REQUIRED_FIELD_MISSING in assessment.blockers


def ownership_text(*, total: bool = True) -> str:
    return "\n".join(
        [
            "Shareholder: SYNTHETIC OWNER ONE",
            "Type: NATURAL_PERSON",
            "Shares: 250",
            "Percentage: 25%",
            "Share Class: ORDINARY",
            "Owned Entity: SYNTHETIC HOLDINGS",
            "Owned Entity Registration Number: 202400001A",
            "As Of: 2026-10-04",
            *(["Total Shares: 1000"] if total else []),
        ]
    )


def test_source_ownership_is_explicit_proposed_and_server_bound_without_arithmetic() -> None:
    text = ownership_text()
    provider = LocalPdfTextIdpProvider()
    source = provider.process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=text.encode(),
            media_type="text/plain",
            extracted_text=text,
        )
    )
    proposal = source.ownership_observations[0]
    assert proposal.share_count == Decimal("250")
    assert proposal.explicit_percentage == Decimal("25")
    assert proposal.explicit_total_shares == Decimal("1000")
    assert proposal.as_of_date == date(2026, 10, 4)
    assert proposal.owner_registration_identifier is None
    assert proposal.decision_state == "PROPOSED"
    assert "document_id" not in proposal.model_dump()
    service, _ = make_service(provider=provider, max_bytes=5 * 1024 * 1024)
    record = service.create_document(
        case_id=CASE_ID,
        display_name="declaration.txt",
        content_type="text/plain",
        content=text.encode(),
    )
    retained = record.ownership_observations[0]
    assert record.document_version == retained.document_version == 1
    assert (
        retained.document_id == record.document_id and retained.observation_id != record.document_id
    )
    assert retained.decision_state == "PROPOSED"
    assert "text" not in record.model_dump()
    with pytest.raises(ValidationError):
        retained.owner_name = "CHANGED"  # type: ignore[misc]


def test_missing_denominator_stays_missing_and_no_type_is_inferred_from_name() -> None:
    text = ownership_text(total=False).replace("Type: NATURAL_PERSON\n", "")
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=text.encode(),
            media_type="text/plain",
            extracted_text=text,
        )
    )
    assert result.ownership_observations[0].explicit_total_shares is None
    assert result.ownership_observations[0].owner_type is None
    assert result.ownership_observations[0].share_count == Decimal("250")


def test_duplicate_scalar_labels_retain_both_proposed_values() -> None:
    text = "Shareholder: SYNTHETIC OWNER | Shares: 250 | Shares: 300 | Total Shares: 1000"
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=text.encode(),
            media_type="text/plain",
            extracted_text=text,
        )
    )
    assert {item.share_count for item in result.ownership_observations} == {
        Decimal(250),
        Decimal(300),
    }
    assert all(
        item.explicit_total_shares == Decimal(1000)
        and item.extraction_quality == ExtractionQuality.AMBIGUOUS
        for item in result.ownership_observations
    )


@pytest.mark.parametrize("duplicate_label", ["Shares", "Share count"])
def test_duplicate_table_columns_retain_all_explicit_values(duplicate_label: str) -> None:
    text = (
        f"Shareholder | Shares | {duplicate_label} | Type | Total Shares | As Of\n"
        "SYNTHETIC OWNER | 250 | 300 | NATURAL_PERSON | 1000 | 2026-10-04"
    )
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=text.encode(),
            media_type="text/plain",
            extracted_text=text,
        )
    )
    assert len(result.ownership_observations) == 2
    assert {item.share_count for item in result.ownership_observations} == {
        Decimal(250), Decimal(300),
    }
    assert all(
        item.owner_name == "SYNTHETIC OWNER"
        and item.owner_type == "NATURAL_PERSON"
        and item.explicit_total_shares == Decimal(1000)
        and item.as_of_date == date(2026, 10, 4)
        and item.explicit_percentage is None
        and item.extraction_quality == ExtractionQuality.AMBIGUOUS
        and item.evidence_score <= 0.4
        and item.decision_state == "PROPOSED"
        and item.page_number == 1
        and item.source_reference == "PAGE_1_OWNERSHIP_ROW_2"
        for item in result.ownership_observations
    )


def test_duplicate_table_proposals_retain_distinct_server_bindings() -> None:
    text = (
        "Shareholder | Type | Shares | Shares\n"
        "SYNTHETIC OWNER | NATURAL_PERSON | 250 | 300"
    )
    service, _ = make_service(provider=LocalPdfTextIdpProvider(), max_bytes=5 * 1024 * 1024)
    record = service.create_document(
        case_id=CASE_ID,
        display_name="duplicate-table.txt",
        content_type="text/plain",
        content=text.encode(),
    )
    assert len(record.ownership_observations) == 2
    assert {item.share_count for item in record.ownership_observations} == {
        Decimal(250), Decimal(300),
    }
    assert len({item.observation_id for item in record.ownership_observations}) == 2
    assert all(
        item.document_id == record.document_id
        and item.document_version == record.document_version == 1
        and item.observation_id != record.document_id
        and item.page_number == 1
        and item.source_reference == "PAGE_1_OWNERSHIP_ROW_2"
        and item.extraction_quality == ExtractionQuality.AMBIGUOUS
        and item.decision_state == "PROPOSED"
        for item in record.ownership_observations
    )


@pytest.mark.parametrize("count", [128, 129])
def test_duplicate_table_proposals_obey_existing_output_limit(count: int) -> None:
    text = "\n".join([
        "Shareholder | Type | " + " | ".join("Shares" for _ in range(count)),
        "SYNTHETIC OWNER | NATURAL_PERSON | " + " | ".join(str(i) for i in range(1, count + 1)),
    ])
    request = IdpDocumentInput(
        profile=DocumentProfile.PROVISIONAL_CORPORATE,
        content=text.encode(),
        media_type="text/plain",
        extracted_text=text,
    )
    if count > 128:
        with pytest.raises(LocalDocumentProcessingError, match="DOCUMENT_OUTPUT_LIMIT_EXCEEDED"):
            LocalPdfTextIdpProvider().process(request)
    else:
        result = LocalPdfTextIdpProvider().process(request)
        assert len(result.ownership_observations) == count
        assert {item.share_count for item in result.ownership_observations} == {
            Decimal(i) for i in range(1, count + 1)
        }
        assert all(
            item.explicit_total_shares is None
            and item.explicit_percentage is None
            and item.extraction_quality == ExtractionQuality.AMBIGUOUS
            and item.decision_state == "PROPOSED"
            for item in result.ownership_observations
        )


def test_observation_and_transient_text_overflow_fail_without_truncation() -> None:
    text = "\n".join(f"Shareholder: SYNTHETIC OWNER {index} | Shares: 25" for index in range(129))
    with pytest.raises(LocalDocumentProcessingError, match="DOCUMENT_OUTPUT_LIMIT_EXCEEDED"):
        LocalPdfTextIdpProvider().process(
            IdpDocumentInput(
                profile=DocumentProfile.PROVISIONAL_CORPORATE,
                content=text.encode(),
                media_type="text/plain",
                extracted_text=text,
            )
        )
    with pytest.raises(LocalDocumentProcessingError, match="DOCUMENT_OUTPUT_LIMIT_EXCEEDED"):
        process(image_bytes(), "image/png", ocr=StubOcr("x" * 64001, 90.0))


def test_failed_ocr_cleans_temporary_files_and_unknown_error_codes_are_sanitized() -> None:
    paths: list[Path] = []

    class FailingOcr:
        def recognize(self, image_path: Path, *, timeout_seconds: float) -> LocalOcrResult:
            paths.append(image_path)
            raise LocalDocumentProcessingError("PRIVATE_ENGINE_SENTINEL")

    with pytest.raises(LocalDocumentProcessingError, match="IDP_PROCESSING_FAILED"):
        LocalPdfTextIdpProvider(ocr=FailingOcr()).process(
            IdpDocumentInput(
                profile=DocumentProfile.PROVISIONAL_CORPORATE,
                content=image_bytes(),
                media_type="image/png",
            )
        )
    assert paths and all(not path.exists() for path in paths)


def test_ownership_table_and_conflicting_rows_are_preserved_as_proposals() -> None:
    text = (
        "Shareholder | Type | Shares | Percentage | Owned Entity | "
        "Owned Entity Registration Number\n"
        "SYNTHETIC OWNER | NATURAL_PERSON | 25 | 25% | HOLDINGS | 202400001A\n"
        "SYNTHETIC OWNER | NATURAL_PERSON | 35 | 35% | HOLDINGS | 202400001A"
    )
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=text.encode(),
            media_type="text/plain",
            extracted_text=text,
        )
    )
    assert len(result.ownership_observations) == 2
    assert {item.share_count for item in result.ownership_observations} == {
        Decimal(25),
        Decimal(35),
    }
    assert all(
        item.extraction_quality == ExtractionQuality.AMBIGUOUS and item.decision_state == "PROPOSED"
        for item in result.ownership_observations
    )


def test_source_dto_rejects_provider_authored_binding_and_selected_ambiguous_values() -> None:
    source = process(synthetic_pdf(matching_fields())).model_dump()
    source["document_id"] = "00000000-0000-4000-8000-000000000101"
    with pytest.raises(ValidationError):
        IdpSourceResult.model_validate(source)
    source.pop("document_id")
    proposal = {
        "owner_name": "SYNTHETIC OWNER",
        "evidence_score": 0.9,
        "page_number": 1,
        "source_reference": "PAGE_1",
        "document_id": source.get("document_id"),
    }
    source["ownership_observations"] = [proposal]
    with pytest.raises(ValidationError):
        IdpSourceResult.model_validate(source)


def test_absent_runtime_is_explicit_and_native_text_remains_usable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert process(synthetic_pdf(matching_fields())).fields[0].value is not None
    with pytest.raises(LocalDocumentProcessingError, match="OCR_RUNTIME_UNAVAILABLE"):
        process(image_bytes(), "image/png")
    service, repository = make_service(
        provider=LocalPdfTextIdpProvider(), max_bytes=5 * 1024 * 1024
    )
    with pytest.raises(DocumentProcessingInfrastructureError) as error:
        service.create_document(
            case_id=CASE_ID,
            display_name="scan.png",
            content_type="image/png",
            content=image_bytes(),
        )
    failed = repository.get(error.value.document_id)
    assert failed is not None and failed.state.value == "FAILED"
    assert failed.error is not None and failed.error.code == "OCR_RUNTIME_UNAVAILABLE"


@pytest.mark.parametrize(
    ("name", "media", "content"),
    [
        ("spoof.png", "image/png", b"\xff\xd8\xffnot png"),
        ("spoof.jpg", "image/jpeg", b"\x89PNG\r\n\x1a\nnot jpeg"),
        ("invalid.tiff", "image/tiff", b"II*\x00truncated"),
    ],
)
def test_signature_and_decoded_format_rejections(name: str, media: str, content: bytes) -> None:
    with pytest.raises(DocumentRequestError) as error:
        DocumentMediaRouter().extract(display_name=name, content_type=media, content=content)
    assert error.value.code == "DOCUMENT_STRUCTURE_INVALID"


@pytest.mark.parametrize(
    ("size", "frames", "code"),
    [((8001, 1), 1, "DOCUMENT_PAGE_TOO_LARGE"), ((100, 80), 11, "DOCUMENT_TOO_MANY_PAGES")],
)
def test_image_dimensions_and_tiff_frame_limits(
    size: tuple[int, int], frames: int, code: str
) -> None:
    with pytest.raises(DocumentRequestError, match=code):
        DocumentMediaRouter().extract(
            display_name="bounds.tiff",
            content_type="image/tiff",
            content=image_bytes("TIFF", size=size, frames=frames),
        )


def test_pdf_page_bounds_encryption_and_unsafe_actions_are_rejected() -> None:
    for kind, code in (
        ("pages", "DOCUMENT_TOO_MANY_PAGES"),
        ("encrypted", "DOCUMENT_ENCRYPTED"),
        ("script", "DOCUMENT_ACTIVE_CONTENT"),
        ("remote", "DOCUMENT_ACTIVE_CONTENT"),
    ):
        writer = PdfWriter()
        for _ in range(11 if kind == "pages" else 1):
            writer.add_blank_page(width=612, height=792)
        if kind == "encrypted":
            writer.encrypt(str(uuid4()))
        if kind == "script":
            writer.add_js("app.alert('synthetic');")
        if kind == "remote":
            writer._root_object[NameObject("/OpenAction")] = DictionaryObject(
                {
                    NameObject("/S"): NameObject("/URI"),
                    NameObject("/URI"): TextStringObject("https://example.invalid/"),
                }
            )
        output = BytesIO()
        writer.write(output)
        with pytest.raises(DocumentRequestError) as error:
            DocumentMediaRouter().extract(
                display_name="unsafe.pdf", content_type="application/pdf", content=output.getvalue()
            )
        assert error.value.code == code


def test_image_pixel_and_pdf_aggregate_pixel_limits_are_enforced_before_ocr() -> None:
    with pytest.raises(DocumentRequestError, match="DOCUMENT_PAGE_TOO_LARGE"):
        DocumentMediaRouter().extract(
            display_name="pixels.png",
            content_type="image/png",
            content=image_bytes(size=(4000, 4001)),
        )
    writer = PdfWriter()
    for _ in range(8):
        writer.add_blank_page(width=1500, height=1500)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(DocumentRequestError, match="DOCUMENT_CONTENT_TOO_LARGE"):
        DocumentMediaRouter().extract(
            display_name="total.pdf", content_type="application/pdf", content=output.getvalue()
        )


def test_animated_png_is_rejected() -> None:
    output = BytesIO()
    with (
        Image.new("RGB", (10, 10), "white") as first,
        Image.new("RGB", (10, 10), "black") as second,
    ):
        first.save(output, format="PNG", save_all=True, append_images=[second])
    with pytest.raises(DocumentRequestError):
        DocumentMediaRouter().extract(
            display_name="animated.png", content_type="image/png", content=output.getvalue()
        )


@pytest.mark.parametrize(
    ("code", "program", "timeout", "bound"),
    [
        ("OCR_PROCESSING_TIMEOUT", "import time; time.sleep(5)", 0.1, 100),
        ("DOCUMENT_OUTPUT_LIMIT_EXCEEDED", "import sys; sys.stdout.write('x'*100000)", 5, 100),
        (
            "OCR_PROCESSING_FAILED",
            "import sys; print('PRIVATE_ENGINE_SENTINEL'); sys.exit(2)",
            5,
            100,
        ),
    ],
)
def test_real_process_deadline_output_and_error_bounds(
    code: str, program: str, timeout: float, bound: int
) -> None:
    with pytest.raises(LocalDocumentProcessingError) as error:
        run_bounded_process(
            [sys.executable, "-B", "-c", program],
            timeout_seconds=timeout,
            output_limit=bound,
            unavailable_code="OCR_RUNTIME_UNAVAILABLE",
            timeout_code="OCR_PROCESSING_TIMEOUT",
            failed_code="OCR_PROCESSING_FAILED",
        )
    assert error.value.code == code
    assert "PRIVATE_ENGINE_SENTINEL" not in str(error.value)


def test_tsv_raw_mean_ignores_structural_rows_and_invalid_output_is_safe() -> None:
    header = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
        "left\ttop\twidth\theight\tconf\ttext\n"
    )
    output = (
        header + "1\t1\t0\t0\t0\t0\t0\t0\t10\t10\t-1\t\n"
        "5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t80\tLegal\n"
        "5\t1\t1\t1\t1\t2\t0\t0\t10\t10\t90\tName:\n"
    ).encode()
    result = decode_tesseract_tsv(output)
    assert result.text == "Legal Name:" and result.word_count == 2
    assert result.raw_mean_confidence == 85
    with pytest.raises(LocalDocumentProcessingError, match="OCR_OUTPUT_INVALID"):
        decode_tesseract_tsv(b"PRIVATE_ENGINE_SENTINEL")


def _render_synthetic_scan(*, poor: bool = False) -> Image.Image:
    font_name = "DejaVuSans.ttf" if sys.platform != "win32" else "C:/Windows/Fonts/arial.ttf"
    font = ImageFont.truetype(font_name, 30)
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    lines = [
        "SYNTHETIC LOCAL OCR ACCEPTANCE",
        *[f"{key}: {value}" for key, value in matching_fields().items()],
        *ownership_text().splitlines(),
    ]
    for index, line in enumerate(lines):
        draw.text((50, 40 + index * 65), line, fill="black", font=font)
    if poor:
        degraded = image.resize((240, 160)).resize(image.size).filter(ImageFilter.GaussianBlur(5))
        image.close()
        return degraded
    return image


@pytest.mark.parametrize("kind", ["PNG", "JPEG", "TIFF", "SCAN_PDF", "MIXED_PDF", "POOR_PNG"])
def test_real_local_ocr_acceptance(kind: str) -> None:
    if shutil.which("tesseract") is None:
        if os.environ.get("CLM_REAL_OCR_REQUIRED") == "1":
            pytest.fail("Real OCR acceptance requires the provisioned local Tesseract runtime")
        pytest.skip("Local Tesseract unavailable; real OCR is not claimed")
    output = BytesIO()
    with _render_synthetic_scan(poor=kind == "POOR_PNG") as image:
        image.save(
            output,
            format="PDF" if "PDF" in kind else "PNG" if kind == "POOR_PNG" else kind,
            resolution=150,
            **({"compression": "tiff_deflate"} if kind == "TIFF" else {}),
        )
    content = output.getvalue()
    if kind == "MIXED_PDF":
        content = combine_pdf(
            synthetic_pdf({"Company": "MERLION CIRCULAR LABS PTE. LTD."}), content
        )
    media = (
        "application/pdf"
        if "PDF" in kind
        else {
            "PNG": "image/png",
            "POOR_PNG": "image/png",
            "JPEG": "image/jpeg",
            "TIFF": "image/tiff",
        }[kind]
    )
    name = "acceptance." + (
        "pdf" if "PDF" in kind else "png" if kind == "POOR_PNG" else kind.lower()
    )
    routed = DocumentMediaRouter().extract(display_name=name, content_type=media, content=content)
    result = process(routed.content, media)
    assert any(
        page.extraction_method == ExtractionMethod.LOCAL_TESSERACT_OCR for page in result.pages
    )
    if kind == "POOR_PNG":
        assert any(
            item.extraction_quality in {ExtractionQuality.LOW, ExtractionQuality.UNAVAILABLE}
            for item in result.fields
        )
        assert any(item.value is None or item.confidence < 0.85 for item in result.fields)
        return
    fields = {item.field_key: item for item in result.fields}
    assert fields[DocumentFieldKey.REGISTRATION_NUMBER].value == "202400001A"
    assert fields[DocumentFieldKey.LEGAL_NAME].value == matching_fields()["Legal Name"]
    assert len(result.ownership_observations) == 1
    assert result.ownership_observations[0].share_count == Decimal(250)
    assert result.ownership_observations[0].explicit_percentage == Decimal(25)
    assert result.ownership_observations[0].decision_state == "PROPOSED"
    if kind == "MIXED_PDF":
        assert result.pages[0].extraction_method == ExtractionMethod.NATIVE_PDF_TEXT
        assert fields[DocumentFieldKey.REGISTRATION_NUMBER].page_number == 2
