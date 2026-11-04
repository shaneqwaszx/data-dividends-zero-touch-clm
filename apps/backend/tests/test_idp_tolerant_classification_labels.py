"""Layout-tolerant classification labels in the local document reader (synthetic text only).

A label may carry a short qualifier ("KYC Customer Type (suggested):") and its value may sit on
the very next line. A blank next line or another "Label:" line is never taken as a value, and
nothing is read without its label. Provenance names the line the value came from.
"""

import pytest
from scripts.generate_phase08_synthetic_pdfs import text_pdf

from app.connectors.idp import IdpDocumentInput
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.domain.documents import DocumentProfile


def _read(text: str):
    return LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=b"transient",
            media_type="text/plain",
            extracted_text=text,
        )
    )


def _classified(result) -> list[tuple[str, str, str]]:
    return [
        (str(item.field_key), item.value, item.source_reference)
        for item in result.classification_observations
    ]


# The layout of the owner's synthetic Garden and OPQ onboarding PDFs (values on the next line).
GARDEN = "\n".join(
    [
        "1. Entity identity supplied for onboarding",
        "Legal Name:",
        "GARDEN BUSINESS",
        "UEN:",
        "11111999A",
        "3. Target-classification examples (RM selection only)",
        "KYC Customer Type (suggested):",
        "Partnership - Unregulated",
        "Client Segment (suggested):",
        "Corporate",
        "4. Fields intentionally not supplied",
    ]
)


def test_qualified_labels_with_the_value_on_the_next_line_are_read():
    assert _classified(_read(GARDEN)) == [
        ("kyc_customer_type", "Partnership - Unregulated", "PAGE_1_LINE_8"),
        ("client_segment", "Corporate", "PAGE_1_LINE_10"),
    ]


def test_a_qualifier_on_the_same_line_is_read():
    text = "KYC Customer Type (suggested): Company - Private\nClient Segment (RM review): Corporate"
    assert _classified(_read(text)) == [
        ("kyc_customer_type", "Company - Private", "PAGE_1_LINE_1"),
        ("client_segment", "Corporate", "PAGE_1_LINE_2"),
    ]


def test_the_single_line_form_is_unchanged():
    text = "KYC Customer Type: Company - Private\nClient Segment: Corporate"
    assert _classified(_read(text)) == [
        ("kyc_customer_type", "Company - Private", "PAGE_1_LINE_1"),
        ("client_segment", "Corporate", "PAGE_1_LINE_2"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        # A blank next line: nothing is taken.
        "KYC Customer Type:\n\nCompany - Private",
        # The label at the end of the text.
        "KYC Customer Type:",
        # The next line is another label: it is never a value.
        "KYC Customer Type:\nClient Segment:",
        "KYC Customer Type (suggested):\nRegistered Address: 1 EXAMPLE ROAD",
    ],
)
def test_no_value_is_invented_for_an_empty_label(text):
    kyc = [
        item
        for item in _read(text).classification_observations
        if str(item.field_key) == "kyc_customer_type"
    ]
    assert kyc == []


def test_two_empty_labels_on_consecutive_lines_do_not_capture_each_other():
    text = "KYC Customer Type:\nClient Segment:\nCorporate"
    assert _classified(_read(text)) == [("client_segment", "Corporate", "PAGE_1_LINE_3")]


@pytest.mark.parametrize(
    "text",
    [
        "The KYC Customer Type: is chosen by the RM",  # not at the start of a line
        "Customer Type: Company - Private",  # another label
        "KYC Customer Type (suggested and reviewed by the relationship manager team):\nCorporate",
        "Partnership - Unregulated",  # a value with no label
    ],
)
def test_unlabelled_or_unrelated_lines_are_not_read(text):
    assert _classified(_read(text)) == []


def test_a_real_pdf_in_the_next_line_layout_is_read():
    content = text_pdf(
        {"Legal Name": "OPQ PTE. LTD.", "UEN": "201511222D", "Country": "SG"},
        extra_lines=(
            "KYC Customer Type (suggested):",
            "Company - Private",
            "Client Segment (suggested):",
            "Corporate",
        ),
    )
    result = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=content,
            media_type="application/pdf",
        )
    )
    assert [(str(item.field_key), item.value) for item in result.classification_observations] == [
        ("kyc_customer_type", "Company - Private"),
        ("client_segment", "Corporate"),
    ]
    assert all(
        item.extraction_method == "NATIVE_PDF_TEXT" and item.evidence_score == 0.97
        for item in result.classification_observations
    )


@pytest.mark.parametrize(
    "next_line",
    [
        "4. Fields intentionally not supplied",  # a numbered heading
        "2) Notes",
        "- Partnership - Unregulated",  # a bullet
        "• Corporate",
    ],
)
def test_a_heading_or_bullet_is_never_a_next_line_value(next_line):
    assert _classified(_read(f"Client Segment:\n{next_line}")) == []


def test_a_long_next_line_is_skipped_and_the_rest_of_the_document_still_reads():
    # QG: a blank form field followed by a paragraph must not fail the whole document.
    text = "\n".join(
        [
            "Legal Name: GARDEN BUSINESS",
            "UEN: 11111999A",
            "Client Segment:",
            "x" * 200,
            "KYC Customer Type: Company - Private",
        ]
    )
    result = _read(text)
    assert _classified(result) == [("kyc_customer_type", "Company - Private", "PAGE_1_LINE_5")]
    fields = {str(item.field_key): item.value for item in result.fields}
    assert fields["legal_name"] == "GARDEN BUSINESS"
    assert fields["registration_number"] == "11111999A"
