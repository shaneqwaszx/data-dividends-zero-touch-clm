"""Phase 08 input-driven PDF evidence and supersession regressions."""

from collections.abc import Mapping
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.connectors.idp import IdpDocumentInput
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.domain.documents import DocumentFieldKey, DocumentProfile
from app.main import create_app

TESTS_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = TESTS_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent.parent


def synthetic_pdf(
    fields: Mapping[str, str], *, include_text: bool = True, extra_lines: tuple[str, ...] = ()
) -> bytes:
    """Build one small valid, text-based fictional PDF without a test dependency."""

    lines = ["SYNTHETIC TEST DATA", "CORPORATE PROFILE"] if include_text else []
    lines.extend(f"{label}: {value}" for label, value in fields.items())
    lines.extend(extra_lines)
    escaped = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    operations = "BT /F1 12 Tf 72 720 Td "
    operations += " Tj 0 -16 Td ".join(f"({line})" for line in escaped)
    operations += " Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(operations.encode('latin-1'))} >>\nstream\n{operations}\nendstream",
    ]
    output = "%PDF-1.4\n"
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output.encode("latin-1")))
        output += f"{index} 0 obj\n{item}\nendobj\n"
    xref = len(output.encode("latin-1"))
    output += "xref\n0 6\n0000000000 65535 f \n"
    output += "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    output += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return output.encode("latin-1")


def matching_fields(uen: str = "202400001A") -> dict[str, str]:
    fields = {
        "Legal Name": "MERLION CIRCULAR LABS PTE. LTD.",
        "UEN": "202400001A",
        "Registered Address": "18 INNOVATION WAY, #04-01, 018956, SG",
        "Country": "SG",
    }
    if uen == "202400006F":
        fields.update(
            {
                "Legal Name": "CYCLIC HARBOUR HOLDINGS PTE. LTD.",
                "UEN": uen,
                "Registered Address": "18 CYCLE STREET, #01-01, 049001, SG",
            }
        )
    if uen == "202400005E":
        fields.update(
            {
                "Legal Name": "LION CITY EXISTING CUSTOMER PTE. LTD.",
                "UEN": uen,
                "Registered Address": "18 CUSTOMER ROAD, #05-02, 068914, SG",
            }
        )
    return fields


def provider_result(fields: Mapping[str, str], *, include_text: bool = True) -> object:
    return LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=synthetic_pdf(fields, include_text=include_text),
        )
    )


def test_local_pdf_provider_reads_actual_labelled_pdf_text_deterministically() -> None:
    first = provider_result(matching_fields())
    second = provider_result(matching_fields())
    assert first == second
    values = {field.field_key: field for field in first.fields}  # type: ignore[attr-defined]
    assert values[DocumentFieldKey.LEGAL_NAME].value == "MERLION CIRCULAR LABS PTE. LTD."
    assert values[DocumentFieldKey.REGISTRATION_NUMBER].value == "202400001A"
    assert values[DocumentFieldKey.REGISTERED_ADDRESS].confidence == 0.97


def test_local_pdf_provider_derives_missing_and_ambiguous_evidence_from_content() -> None:
    missing = provider_result(
        {key: value for key, value in matching_fields().items() if key != "Country"}
    )
    missing_country = next(
        field
        for field in missing.fields
        if field.field_key == DocumentFieldKey.COUNTRY_OF_INCORPORATION
    )  # type: ignore[attr-defined]
    assert missing_country.value is None and missing_country.confidence == 0.0

    ambiguous = LocalPdfTextIdpProvider().process(
        IdpDocumentInput(
            profile=DocumentProfile.PROVISIONAL_CORPORATE,
            content=synthetic_pdf(
                matching_fields(),
                extra_lines=("Legal Name: SECOND SYNTHETIC NAME PTE. LTD.",),
            ),
        )
    )
    ambiguous_name = next(
        field for field in ambiguous.fields if field.field_key == DocumentFieldKey.LEGAL_NAME
    )
    assert ambiguous_name.confidence == 0.40


def test_local_pdf_provider_reports_no_text_without_claiming_ocr() -> None:
    result = provider_result({}, include_text=False)
    assert all(field.value is None for field in result.fields)  # type: ignore[attr-defined]
    assert {field.source_reference for field in result.fields} == {"DOCUMENT_TEXT_UNAVAILABLE"}  # type: ignore[attr-defined]


def start(
    client: TestClient,
    uen: str,
    fields: Mapping[str, str],
    *,
    display_name: str = "synthetic-profile.pdf",
) -> dict[str, object]:
    created = client.post("/api/clm/zero-touch/cases", json={"uen": uen})
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": display_name},
        content=synthetic_pdf(fields),
    )
    assert response.status_code == 200
    return response.json()


def test_sponsor_mode_is_pdf_and_uen_driven_with_replacement_auto_resume() -> None:
    client = TestClient(create_app(Settings(app_env="test", demo_controls_enabled=True)))
    mismatch = matching_fields()
    mismatch["Registered Address"] = "25 ROBINSON ROAD, SINGAPORE 048547"
    paused = start(client, "202400001A", mismatch)
    assert paused["status"] == "WAITING_FOR_REVIEW"
    assert paused["active_exceptions"][0]["blocker_code"] == "DOCUMENT_SOURCE_CONFLICT"
    exception = paused["active_exceptions"][0]
    document_id = exception["evidence"][0]["reference_id"]
    event_count = exception["evidence_version"].split(":")[2]
    resumed = client.post(
        f"/api/clm/zero-touch/cases/{paused['case']['case_id']}/documents/{document_id}/replacement",
        headers={
            "content-type": "application/pdf",
            "X-Document-Name": "corrected-profile.pdf",
            "X-Document-Event-Count": event_count,
        },
        content=synthetic_pdf(matching_fields()),
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "COMPLETED"
    documents = client.get(f"/api/onboarding/cases/{paused['case']['case_id']}/documents").json()
    assert documents[0]["superseded_by_document_id"] == documents[1]["document_id"]
    assert documents[1]["supersedes_document_id"] == documents[0]["document_id"]


def test_supported_launcher_composition_keeps_pdf_bytes_causal_and_filename_independent() -> None:
    """Mirror the Windows sponsor mode instead of constructing the provider directly."""

    launcher = (REPO_ROOT / "scripts" / "demo_lifecycle.ps1").read_text(encoding="utf-8")
    assert '$env:IDP_CONNECTOR_MODE = "local_pdf_text"' in launcher
    client = TestClient(
        create_app(
            Settings(app_env="test", idp_connector_mode="local_pdf_text"),
        )
    )
    profile = client.get("/api/system/execution-profile").json()
    assert profile["idp_provider"] == "LOCAL_PDF_TEXT"
    assert profile["idp_environment"] == "LOCAL"

    clean = start(client, "202400001A", matching_fields(), display_name="low_confidence.pdf")
    assert clean["status"] == "COMPLETED"

    mismatch_fields = matching_fields()
    mismatch_fields["Registered Address"] = "25 ROBINSON ROAD, SINGAPORE 048547"
    mismatch = start(client, "202400001A", mismatch_fields, display_name="clean.pdf")
    assert mismatch["active_exceptions"][0]["blocker_code"] == "DOCUMENT_SOURCE_CONFLICT"

    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    ambiguous_response = client.post(
        f"/api/clm/zero-touch/cases/{created['case']['case_id']}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "clean.pdf"},
        content=synthetic_pdf(
            matching_fields(),
            extra_lines=("Legal Name: SECOND SYNTHETIC NAME PTE. LTD.",),
        ),
    ).json()
    assert ambiguous_response["active_exceptions"][0]["blocker_code"] == "DOCUMENT_LOW_CONFIDENCE"


def test_uen_drives_independent_ownership_and_target_outcomes() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    ownership_cycle = start(client, "202400006F", matching_fields("202400006F"))
    assert ownership_cycle["status"] == "WAITING_FOR_REVIEW"
    assert ownership_cycle["current_stage"] == "OWNERSHIP"
    assert ownership_cycle["active_exceptions"][0]["blocker_code"] == "OWNERSHIP_CYCLE"

    existing_party = start(client, "202400005E", matching_fields("202400005E"))
    assert existing_party["status"] == "WAITING_FOR_REVIEW"
    assert existing_party["current_stage"] == "MOCK_GOLDTIER"
    assert (
        existing_party["active_exceptions"][0]["blocker_code"]
        == "GT_EXISTING_PARTY_REVIEW_REQUIRED"
    )
    assert existing_party["target_operations"] == [
        {"operation": "SEARCH", "status": "MATCH_FOUND"},
        {"operation": "SHELL", "status": "NOT_ATTEMPTED"},
        {"operation": "POLICY", "status": "NOT_ATTEMPTED"},
        {"operation": "AMEND", "status": "NOT_ATTEMPTED"},
    ]


def test_cycle_uen_fixture_passes_document_before_input_driven_cycle() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400006F"}).json()
    fixture = (TESTS_DIR / "fixtures" / "uat" / "cycle-uen-clean.pdf").read_bytes()
    response = client.post(
        f"/api/clm/zero-touch/cases/{created['case']['case_id']}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "cycle-uen-clean.pdf"},
        content=fixture,
    ).json()
    assert response["current_stage"] == "OWNERSHIP"
    assert response["active_exceptions"][0]["blocker_code"] == "OWNERSHIP_CYCLE"


def test_no_text_and_unsafe_replacement_requests_stop_safely() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    created = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"}).json()
    case_id = created["case"]["case_id"]
    no_text = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "no-text.pdf"},
        content=synthetic_pdf({}, include_text=False),
    ).json()
    assert no_text["status"] == "WAITING_FOR_REVIEW"
    assert no_text["active_exceptions"][0]["blocker_code"] == "DOCUMENT_TEXT_UNAVAILABLE"
    document_id = no_text["active_exceptions"][0]["evidence"][0]["reference_id"]

    stale = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents/{document_id}/replacement",
        headers={
            "content-type": "application/pdf",
            "X-Document-Name": "replacement.pdf",
            "X-Document-Event-Count": "1",
        },
        content=synthetic_pdf(matching_fields()),
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "DOCUMENT_REVIEW_STALE"

    completed = start(client, "202400001A", matching_fields())
    completed_documents = client.get(
        f"/api/onboarding/cases/{completed['case']['case_id']}/documents"
    ).json()
    terminal = client.post(
        (
            f"/api/clm/zero-touch/cases/{completed['case']['case_id']}/documents/"
            f"{completed_documents[0]['document_id']}/replacement"
        ),
        headers={
            "content-type": "application/pdf",
            "X-Document-Name": "replacement.pdf",
            "X-Document-Event-Count": str(len(completed_documents[0]["events"])),
        },
        content=synthetic_pdf(matching_fields()),
    )
    assert terminal.status_code == 409
    assert terminal.json()["detail"]["code"] == "ZERO_TOUCH_REPLACEMENT_NOT_ALLOWED"
