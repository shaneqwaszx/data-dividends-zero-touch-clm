"""Every approved document uses current intake and LOCAL extraction boundaries."""

import shutil
from pathlib import Path

import pytest

from app.connectors.idp import IdpDocumentInput, IdpSourceResult, LocalDocumentProcessingError
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.domain.documents import DocumentProfile
from app.services.document_errors import DocumentRequestError
from app.services.document_media import DocumentMediaRouter

ROOT = Path(__file__).parent / "fixtures/uat"
NAMES = (
    "clean-company-profile.pdf",
    "address-mismatch.pdf",
    "legal-name-mismatch.pdf",
    "missing-field.pdf",
    "low-confidence.pdf",
    "no-text.pdf",
    "cycle-uen-clean.pdf",
    "second-case-isolation.pdf",
    "invalid-document.pdf",
    "garden-business-clean-onboarding-profile.pdf",
    "garden-business-conflicting-onboarding-profile.pdf",
    "garden-partnership-reviewed-client.pdf",
    "multiple-owner-demo-client.pdf",
)


@pytest.mark.parametrize("name", NAMES)
def test_pack_uses_current_intake_and_extraction(name):
    content = (ROOT / name).read_bytes()
    router = DocumentMediaRouter()
    if name == "invalid-document.pdf":
        with pytest.raises(DocumentRequestError) as error:
            router.extract(display_name=name, content_type="application/pdf", content=content)
        assert error.value.code == "DOCUMENT_STRUCTURE_INVALID"
        return
    routed = router.extract(display_name=name, content_type="application/pdf", content=content)
    if name == "no-text.pdf" and shutil.which("tesseract") is None:
        with pytest.raises(LocalDocumentProcessingError, match="OCR_RUNTIME_UNAVAILABLE"):
            LocalPdfTextIdpProvider().process(
                IdpDocumentInput(
                    profile=DocumentProfile.PROVISIONAL_CORPORATE, content=routed.content,
                )
            )
        return
    extracted = IdpSourceResult.model_validate(
        LocalPdfTextIdpProvider().process(
            IdpDocumentInput(profile=DocumentProfile.PROVISIONAL_CORPORATE, content=routed.content)
        )
    )
    assert len(extracted.fields) == 4
    fields = {field.field_key.value: field for field in extracted.fields}
    if name == "no-text.pdf":
        assert all(field.value is None and field.confidence == 0 for field in extracted.fields)
    elif name == "missing-field.pdf":
        assert fields["country_of_incorporation"].value is None
    elif name == "low-confidence.pdf":
        assert fields["legal_name"].confidence == 0.40
    else:
        assert all(
            field.value is not None and field.confidence == 0.97 for field in extracted.fields
        )
