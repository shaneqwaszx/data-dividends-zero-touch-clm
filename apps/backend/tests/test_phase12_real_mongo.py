"""Genuine Mongo composition-A to composition-B restart proof for Phase 12."""

import os
from io import BytesIO
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

import app.composition as composition
from app.config import Settings
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.main import create_app

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")

TEXT_PROFILE = """Legal Name: MERLION CIRCULAR LABS PTE. LTD.
UEN: 202400001A
Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG
Country: SG
"""
DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx_bytes() -> bytes:
    output = BytesIO()
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
        for line in TEXT_PROFILE.splitlines()
    )
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        archive.writestr(
            "word/document.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paragraphs}</w:body></w:document>""",
        )
    return output.getvalue()


def test_real_mongo_restart_preserves_three_cases_and_replays_no_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MONGO_URI is not None
    database = f"clm_phase12_test_{uuid4().hex}"
    counters = {name: 0 for name in ("registry", "idp", "ownership", "goldtier")}

    class CountingAcra(MockAcraConnector):
        def fetch_company(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_company(uen)

        def fetch_officers(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_officers(uen)

        def fetch_ownership_parties(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_ownership_parties(uen)

        def fetch_relationships(self, uen: str) -> object:
            counters["registry"] += 1
            return super().fetch_relationships(uen)

    class CountingIdp(LocalPdfTextIdpProvider):
        def process(self, document: object) -> object:
            counters["idp"] += 1
            return super().process(document)  # type: ignore[arg-type]

    class CountingOwnership(RegistryAcquisitionOwnershipProvider):
        def load(self, request: object) -> object:
            counters["ownership"] += 1
            return super().load(request)  # type: ignore[arg-type]

    class CountingGoldTier(MockGoldTierConnector):
        def search_party(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().search_party(request, metadata)  # type: ignore[arg-type]

        def create_shell_customer(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_shell_customer(request, metadata)  # type: ignore[arg-type]

        def create_policy(self, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().create_policy(request, metadata)  # type: ignore[arg-type]

        def amend_party(self, party_id: str, request: object, metadata: object) -> object:
            counters["goldtier"] += 1
            return super().amend_party(party_id, request, metadata)  # type: ignore[arg-type]

    monkeypatch.setattr(composition, "MockAcraConnector", CountingAcra)
    monkeypatch.setattr(composition, "LocalPdfTextIdpProvider", CountingIdp)
    monkeypatch.setattr(composition, "RegistryAcquisitionOwnershipProvider", CountingOwnership)
    monkeypatch.setattr(composition, "MockGoldTierConnector", CountingGoldTier)

    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
    )
    cleanup_client: MongoClient[dict[str, object]] = MongoClient(MONGO_URI)
    try:
        with TestClient(create_app(settings)) as first:
            completed = first.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
            assert completed.status_code == 201
            completed_id = completed.json()["case"]["case_id"]
            pdf = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
                headers={"Content-Type": "text/plain", "X-Document-Name": "Profile.txt"},
                content=TEXT_PROFILE.encode(),
            )
            docx = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
                headers={"Content-Type": DOCX_MEDIA, "X-Document-Name": "Constitution.docx"},
                content=_docx_bytes(),
            )
            txt = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/documents",
                headers={"Content-Type": "text/plain", "X-Document-Name": "Details.txt"},
                content=TEXT_PROFILE.encode(),
            )
            assert [pdf.status_code, docx.status_code, txt.status_code] == [201, 201, 201]
            done = first.post(
                f"/api/clm/zero-touch/cases/{completed_id}/intake/complete",
                json={"expected_document_count": 3},
            )
            assert done.status_code == 200, done.text
            assert done.json()["status"] == "COMPLETED"

            pending = first.post(
                "/api/clm/zero-touch/cases", json={"uen": "202400001A"}
            )
            waiting = first.post(
                "/api/clm/zero-touch/cases",
                json={"uen": "UNKNOWN", "country_of_incorporation": "AU"},
            )
            assert pending.json()["status"] == "PENDING_INPUTS"
            assert waiting.json()["status"] == "WAITING_FOR_REVIEW"

        before_restart = counters.copy()
        assert before_restart == {
            "registry": 8,
            "idp": 3,
            "ownership": 1,
            "goldtier": 4,
        }

        with TestClient(create_app(settings)) as second:
            listed = second.get("/api/clm/zero-touch/cases")
            detail = second.get(f"/api/clm/zero-touch/cases/{completed_id}")
            documents = second.get(
                f"/api/onboarding/cases/{completed_id}/documents"
            )
            review = second.get(
                "/api/clm/zero-touch/cases?status=WAITING_FOR_REVIEW"
            )
            profile = second.get("/api/system/execution-profile")
            assert (
                listed.status_code
                == detail.status_code
                == documents.status_code
                == review.status_code
                == 200
            )
            assert {item["status"] for item in listed.json()} == {
                "PENDING_INPUTS",
                "WAITING_FOR_REVIEW",
                "COMPLETED",
            }
            assert detail.json()["status"] == "COMPLETED"
            assert len(documents.json()) == 3
            assert len(review.json()) == 1
            assert profile.json()["persistence"] == "Mongo-backed durable POC"
            assert counters == before_restart
    finally:
        assert database.startswith("clm_phase12_test_")
        cleanup_client.drop_database(database)
        cleanup_client.close()
