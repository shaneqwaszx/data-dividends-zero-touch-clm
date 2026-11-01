"""D-112 (O7) shared fixture: an ordinary official Mock company, with no scenario.

A fictional private company with an official entity profile, four official officer
Owner roles (one ceased) and a complete single-class Marketplace Mock register of
600/300/100 active units plus one withdrawn row. It belongs to no overlay scenario and
appears in no allowlist outside this test transport, so it reaches POC acceptance only
through the generic evidence rule. Synthetic test evidence only.
"""

from __future__ import annotations

from typing import Any

from scripts.generate_phase08_synthetic_pdfs import text_pdf

GENERIC_UEN = "209900123K"
GENERIC_NAME = "GENERIC POC DEMO PTE. LTD."
GENERIC_FIELDS = {
    "Legal Name": GENERIC_NAME,
    "UEN": GENERIC_UEN,
    "Country": "SG",
}
GENERIC_PDF = "generic-poc-demo-client.pdf"
GENERIC_HOLDERS = (("SYN-G-1", 600), ("SYN-G-2", 300), ("SYN-G-3", 100))


def _holder(identifier: str, units: int, status: str = "Active") -> dict[str, object]:
    return {
        "shareholderCategory": "Individual",
        "shareholderId": identifier,
        "shareholderName": f"SYNTHETIC HOLDER {identifier}",
        "shareAllotted": units,
        "shareType": "Ordinary",
        "currency": "SINGAPORE DOLLAR",
        "appointmentDate": "2020-01-01",
        "status": status,
    }


def generic_profile(ceased: tuple[int, ...] = (4,)) -> dict[str, object]:
    return {
        "entities": [
            {
                "uen": GENERIC_UEN,
                "name": GENERIC_NAME,
                "entityRegistrationKeyDates": {"registrationDate": "2020-01-01"},
                # The canonical minimum requires an address; visibly synthetic.
                "entityRegisteredAddressDetails": {
                    "registeredAddress": {
                        "blkhseNo": "2",
                        "streetName": "SYNTHETIC GENERIC PROTOCOL ROAD",
                        "postalCode": "000002",
                    }
                },
                "entityConstnDetailsAndType": {
                    "constitution": "PRIVATE COMPANY LIMITED BY SHARES"
                },
                "entityOfficersRecord": {
                    "officerAppointmentDetails": [
                        {
                            "officerId": f"SYNTHETIC-ROLE-{index}",
                            "officerName": f"Synthetic Generic Role {index}",
                            "position": "OWNER",
                            "appointedDate": "2020-01-01",
                            **({"withdrawalDate": "2023-06-30"} if index in ceased else {}),
                        }
                        for index in range(1, 5)
                    ]
                },
            }
        ]
    }


def add_generic_company(transport: Any, *, ceased: tuple[int, ...] = (4,)) -> Any:
    """Register the generic company on an offline Marketplace protocol transport."""

    transport.allowlist = frozenset(transport.allowlist) | {GENERIC_UEN}
    transport.profiles[GENERIC_UEN] = generic_profile(ceased)
    transport.shareholders[GENERIC_UEN] = {
        "entities": [
            {
                "uen": GENERIC_UEN,
                "name": GENERIC_NAME,
                "shareholders": {
                    "individual": [
                        *(_holder(identifier, units) for identifier, units in GENERIC_HOLDERS),
                        _holder("SYN-G-OLD", 900, "Withdrawn"),
                    ],
                    "grouping": [],
                },
            }
        ]
    }
    return transport


def generic_pdf() -> bytes:
    """Deterministic client PDF declaring identity only, never ownership values."""

    return text_pdf(
        GENERIC_FIELDS,
        extra_lines=(
            "SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE - generic D-112 company",
            "Fictional onboarding document; not an ACRA extract and declares no ownership.",
        ),
    )


def start_generic(client: Any) -> dict:
    """The ordinary zero-touch intake for the generic company (no scenario involved)."""

    from test_zero_touch_exception_remediation import successful

    created = successful(
        client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": GENERIC_UEN,
                "legal_name": GENERIC_NAME,
                "country_of_incorporation": "SG",
            },
        ),
        201,
    )
    case_id = created["case"]["case_id"]
    successful(
        client.put(
            f"/api/clm/zero-touch/cases/{case_id}/target-classification",
            json={
                "kyc_customer_type": "Company - Private",
                "client_segment": "Corporate",
                "expected_automation_version": created["version"],
                "expected_case_event_count": len(created["case"]["events"]),
            },
        )
    )
    successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            content=generic_pdf(),
            headers={"Content-Type": "application/pdf", "X-Document-Name": GENERIC_PDF},
        ),
        201,
    )
    return successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
    )
