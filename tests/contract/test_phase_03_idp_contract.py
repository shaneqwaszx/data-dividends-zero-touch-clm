from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "backend"
FRONTEND_ROOT = REPOSITORY_ROOT / "apps" / "frontend" / "src"
sys.path.insert(0, str(BACKEND_ROOT))

from app.api_models import DocumentProcessingResponse
from app.connectors.idp import (
    IdpDocumentInput,
    IdpProviderMetadata,
    IdpSourceResult,
)
from app.domain.documents import (
    DocumentFieldKey,
    DocumentProcessingRecord,
    DocumentProfile,
    ExtractedField,
    IdpEnvironment,
)
from app.services.document_processing import DocumentProcessingService


class Phase03IdpContractTests(unittest.TestCase):
    def test_retained_and_browser_models_exclude_binary_paths_and_raw_output(self) -> None:
        forbidden = {
            "content",
            "bytes",
            "path",
            "storage_path",
            "raw_ocr_text",
            "raw_provider_output",
            "evidence_snippet",
            "credentials",
        }
        for model in (DocumentProcessingRecord, DocumentProcessingResponse, ExtractedField):
            self.assertTrue(forbidden.isdisjoint(model.model_fields))
        self.assertIn("display_name", DocumentProcessingRecord.model_fields)

    def test_transient_provider_input_repr_excludes_pdf_bytes(self) -> None:
        document = IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=b"PRIVATE_PDF_SENTINEL",
        )
        self.assertNotIn("PRIVATE_PDF_SENTINEL", repr(document))

    def test_source_contract_requires_exact_provisional_profile(self) -> None:
        fields = [
            {
                "field_key": key.value,
                "value": "SYNTHETIC",
                "confidence": 0.9,
                "page_number": 1,
                "source_reference": "SYNTHETIC_PAGE_1",
            }
            for key in DocumentFieldKey
        ]
        valid = {
            "profile": "PROVISIONAL_CORPORATE",
            "fields": fields,
        }
        self.assertEqual(len(IdpSourceResult.model_validate(valid).fields), 4)

        duplicate = {**valid, "fields": [fields[0], fields[0], fields[2], fields[3]]}
        with self.assertRaises(ValidationError):
            IdpSourceResult.model_validate(duplicate)

        missing = {**valid, "fields": fields[:-1]}
        with self.assertRaises(ValidationError):
            IdpSourceResult.model_validate(missing)

    def test_source_contract_rejects_unknown_output_and_bad_confidence(self) -> None:
        fields = [
            {
                "field_key": key.value,
                "value": "SYNTHETIC",
                "confidence": 0.9,
                "source_reference": "SYNTHETIC_PAGE_1",
            }
            for key in DocumentFieldKey
        ]
        fields[0]["raw_ocr_text"] = "PRIVATE_OUTPUT_SENTINEL"
        with self.assertRaises(ValidationError):
            IdpSourceResult.model_validate(
                {
                    "profile": "PROVISIONAL_CORPORATE",
                    "fields": fields,
                }
            )
        fields[0].pop("raw_ocr_text")
        fields[0]["confidence"] = 1.1
        with self.assertRaises(ValidationError):
            IdpSourceResult.model_validate(
                {
                    "profile": "PROVISIONAL_CORPORATE",
                    "fields": fields,
                }
            )

    def test_provider_metadata_is_generic_and_validated(self) -> None:
        metadata = IdpProviderMetadata.model_validate(
            {"provider_name": "LOCAL_STUB", "environment": "LOCAL"}
        )
        self.assertEqual(metadata.environment.value, "LOCAL")

    def test_generic_provider_and_service_contracts_have_no_mock_scenario(self) -> None:
        self.assertNotIn("scenario", IdpDocumentInput.__dataclass_fields__)
        self.assertNotIn(
            "scenario", inspect.signature(DocumentProcessingService.create_document).parameters
        )
        self.assertEqual(
            {environment.value for environment in IdpEnvironment},
            {"MOCK", "LOCAL", "SANDBOX", "LIVE"},
        )
        generic_sources = [
            BACKEND_ROOT / "app" / "connectors" / "idp.py",
            BACKEND_ROOT / "app" / "services" / "document_processing.py",
            BACKEND_ROOT / "app" / "domain" / "documents.py",
        ]
        for source in generic_sources:
            self.assertNotIn("MockIdpScenario", source.read_text(encoding="utf-8"))

    def test_frontend_labels_mock_provisional_and_excludes_private_configuration(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in FRONTEND_ROOT.rglob("*")
            if path.is_file()
        )
        self.assertIn("not OCR output from this file", combined)
        self.assertIn("not Delta Capita-approved fields", combined)
        self.assertIn("unauthenticated local POC operator", combined)
        self.assertIn("Human-confirmed value", combined)
        for forbidden in (
            "IDP_MAX_UPLOAD_BYTES",
            "IDP_API_KEY",
            "raw_ocr_text",
            "raw_provider_output",
        ):
            self.assertNotIn(forbidden, combined)

    def test_planner_and_field_profile_keep_q003_and_phase04_out_of_scope(self) -> None:
        planner = (
            REPOSITORY_ROOT / ".ai-pipeline" / "001_planner" / "PHASE_03_IDP_REVIEW.md"
        ).read_text(encoding="utf-8")
        profile = (
            REPOSITORY_ROOT / "docs" / "contracts" / "IDP_FIELD_PROFILE.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Q-003", planner)
        self.assertIn("Phase 04", planner)
        self.assertIn("PROJECT-DEFINED / PROVISIONAL", profile)
        for key in DocumentFieldKey:
            self.assertIn(f"`{key.value}`", profile)


if __name__ == "__main__":
    unittest.main()
