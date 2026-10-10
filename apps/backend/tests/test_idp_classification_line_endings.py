"""Exercise the actual local provider, preserving original page/method/value evidence."""

import pytest
from scripts.generate_phase08_synthetic_pdfs import text_pdf

from app.connectors.idp import IdpDocumentInput
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.domain.documents import DocumentProfile

FIELDS = {
    "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.",
    "UEN": "202400001A",
    "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG",
    "Country": "SG",
    "KYC Customer Type": "Company - Private",
    "Client Segment": "Corporate",
}


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize(
    "media",
    ["text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
)
def test_local_text_classification_line_endings(ending, media):
    text = ending.join(f"{key}: {value}" for key, value in FIELDS.items())
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=b"transient",
            media_type=media,
            extracted_text=text,
        )
    )
    assert [item.value for item in result.classification_observations] == [
        "Company - Private",
        "Corporate",
    ]
    assert [item.source_reference for item in result.classification_observations] == [
        "PAGE_1_LINE_5",
        "PAGE_1_LINE_6",
    ]
    assert all(
        item.page_number == 1 and item.evidence_score == 0.97
        for item in result.classification_observations
    )
    assert all(item.value is not None for item in result.fields)


def test_real_pdf_worker_extracts_classification():
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=text_pdf(FIELDS),
            media_type="application/pdf",
        )
    )
    assert len(result.classification_observations) == 2
    assert all(
        item.extraction_method == "NATIVE_PDF_TEXT" for item in result.classification_observations
    )
    assert [item.source_reference for item in result.classification_observations] == [
        "PAGE_1_LINE_7",
        "PAGE_1_LINE_8",
    ]


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("kind", ["docx", "txt"])
def test_actual_media_router_retains_classification(kind, ending):
    from test_document_processing import CASE_ID, make_service
    from test_pre_phase12_workspace_multidoc import docx_bytes

    text = ending.join(f"{key}: {value}" for key, value in FIELDS.items())
    content = docx_bytes(text) if kind == "docx" else text.encode()
    service, _ = make_service(provider=LocalPdfTextIdpProvider(), max_bytes=5 * 1024 * 1024)
    record = service.create_document(
        case_id=CASE_ID, display_name=f"synthetic-classified.{kind}", content=content,
        content_type=("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                      if kind == "docx" else "text/plain"),
    )
    assert [item.value for item in record.classification_observations] == [
        "Company - Private", "Corporate",
    ]


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_supported_ocr_separators_preserve_scores_and_references(ending):
    from test_s2_local_ocr import StubOcr, image_bytes

    ocr = StubOcr(ending.join(f"{key}: {value}" for key, value in FIELDS.items()), 95.0)
    result = LocalPdfTextIdpProvider(ocr=ocr).process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=image_bytes(),
            media_type="image/png",
        )
    )
    assert [item.value for item in result.classification_observations] == [
        "Company - Private",
        "Corporate",
    ]
    assert all(
        item.extraction_method == "LOCAL_TESSERACT_OCR"
        and item.evidence_score == pytest.approx(0.97 * 0.95)
        for item in result.classification_observations
    )
    assert [item.source_reference for item in result.classification_observations] == [
        "PAGE_1_LINE_5",
        "PAGE_1_LINE_6",
    ]
    assert all(not path.exists() for path in ocr.paths)


@pytest.mark.parametrize(
    "text,values",
    [
        ("KYC Customer Type:\r\nClient Segment:\r\n", []),
        ("KYC Customer Type:\r\nCompany - Private", []),
        (
            "KYC Customer Type: Company - Private\rKYC Customer Type: Government",
            ["Company - Private", "Government"],
        ),
        ("Client Segment: Corporate\rClient Segment: Corporate", ["Corporate", "Corporate"]),
        ("Client Segment: UNKNOWN UNSUPPORTED", ["UNKNOWN UNSUPPORTED"]),
    ],
)
def test_absence_wrapping_repeated_and_unknown_remain_observations(text, values):
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=b"transient",
            media_type="text/plain",
            extracted_text=text,
        )
    )
    assert [item.value for item in result.classification_observations] == values
