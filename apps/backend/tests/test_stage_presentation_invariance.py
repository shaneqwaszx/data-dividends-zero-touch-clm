"""OPQ S1: the stage presentation is additive; gate, readiness and send outcomes are unchanged.

``capture_all()`` drives a fixed set of synthetic in-memory cases (no network, no MongoDB)
through the real API and records every send/readiness/gate outcome that existed before the
presentation field. The baseline JSON was captured with the same function on the unmodified
base source (origin/main b667402e); the test asserts the current source reproduces it exactly.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from test_marketplace_mock_partnerships import (
    RoutedTransport,
    connector,
    mock_lane,
    xyz_at_ownership,
)
from test_phase24_identity import attach_conflict, correction
from test_zero_touch_database_happy_path import RecordingTarget, sandbox_settings
from test_zero_touch_entity_types import complete, create, upload
from test_zero_touch_orchestration import build_system, start_demo

from app.domain.access import TeamId
from app.main import create_app
from app.persistence.composition import build_persistence_bundle

BASELINE = Path(__file__).parent / "fixtures" / "stage_presentation_gate_baseline.json"
DEMO_SCENARIOS = (
    "STRAIGHT_THROUGH",
    "DOCUMENT_DISCREPANCY",
    "LOW_CONFIDENCE_DOCUMENT",
    "OWNERSHIP_INCOMPLETE",
    "EXISTING_PARTY",
    "TARGET_FAILURE",
    "TECHNICAL_FAILURE",
)
OPQ = type("Co", (), {"uen": "201511222D", "name": "OPQ PTE. LTD."})
OPQ_LINES = (
    "FICTIONAL FYP TEST DATA - SYNTHETIC ONBOARDING FORM",
    f"Legal Name: {OPQ.name}",
    f"UEN: {OPQ.uen}",
    "Registered Address: 1 SYNTHETIC STREET, #01-01, 000001, SG",
    "Country: SG",
    "KYC Customer Type: Company - Private",
    "Client Segment: Corporate",
    "Registration Type: ACRA",
    "Customer External System: DSD",
    "Policy: Singapore",
    "Booking Entity: ANZBGL (Singapore Branch)",
)
_NODE_KEYS = ("node_id", "status", "safe_result", "blocker_code", "record_count",
              "advisory_review", "backend_stage", "operation")


def opq_body(*, constitution: str | None, company_type: str | None) -> dict:
    entity: dict[str, Any] = {
        "uen": OPQ.uen,
        "name": OPQ.name,
        "entityRegistrationKeyDates": {"registrationDate": "2015-01-02"},
        "entityRegisteredAddressDetails": {"registeredAddress": {
            "blkhseNo": "1", "streetName": "SYNTHETIC STREET", "levelNo": "1",
            "unitNo": "1", "postalCode": "000001",
        }},
        "entityOfficersRecord": {"officerAppointmentDetails": deepcopy([
            {"officerId": "OPQ-OFFICER-1", "officerName": "SYNTHETIC DIRECTOR ONE",
             "position": "Director", "appointedDate": "2015-01-02", "status": "Active"},
        ])},
    }
    if constitution is not None:
        entity["entityConstnDetailsAndType"] = {"constitution": constitution}
    if company_type is not None:
        entity["companyType"] = company_type
    return {"entities": [entity]}


@contextmanager
def opq_lane(entity_body: dict):
    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    target = RecordingTarget(OPQ.name, OPQ.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(
            settings,
            acra_connector=connector(RoutedTransport(entity_body), clock=lambda: datetime.now(UTC)),
            goldtier_transport=target,
        )) as client,
    ):
        yield client, target


def opq_at_review(client) -> dict:
    current = create(client, OPQ)
    upload(client, current, OPQ_LINES, "identity.txt")
    return complete(client, current, 1)


def node_view(node: dict) -> dict:
    """Every pre-existing node fact except volatile timestamps and identifiers."""

    view = {key: node.get(key) for key in _NODE_KEYS}
    view["children"] = [node_view(item) for item in node.get("children") or ()]
    return view


def gate_view(summary: dict) -> dict:
    readiness = summary["clm"]["readiness"]
    return {
        "status": summary["status"],
        "current_stage": summary["current_stage"],
        "completed_stages": summary["completed_stages"],
        "active_exceptions": sorted(
            [item["stage"], item["exception_type"], item["blocker_code"]]
            for item in summary["active_exceptions"]
        ),
        "readiness": {
            key: readiness[key]["status"]
            for key in ("registry", "document", "ownership", "goldtier")
        },
        "blockers": readiness["blockers"],
        "warnings": readiness["warnings"],
        "pipeline": [node_view(item) for item in summary["processing_pipeline"]],
    }


def http_view(response) -> list:
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = None
    return [response.status_code, detail.get("code") if isinstance(detail, dict) else None]


def summary_of(client, case_id: str) -> dict:
    response = client.get(f"/api/clm/zero-touch/cases/{case_id}")
    assert response.status_code == 200, response.text
    return response.json()


def confirm(client, summary: dict):
    return client.post(
        f"/api/clm/zero-touch/cases/{summary['case']['case_id']}/target-confirmation",
        json={
            "expected_automation_version": summary["version"],
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )


def send_attempts(client, summary: dict) -> dict:
    case_id = summary["case"]["case_id"]
    return {
        "zero_touch_confirmation": http_view(confirm(client, summary)),
        "legacy_submit": http_view(client.post(f"/api/clm/cases/{case_id}/submit")),
    }


def sandbox_writes(target) -> list[str]:
    return [f"{method} {path}" for method, path, _ in target.calls if method != "GET"]


def capture_demo(scenario: str) -> dict:
    client, _, _, target, _ = build_system(require_confirmation=True)
    summary = start_demo(client, scenario, confirm_if_required=False)
    before = gate_view(summary_of(client, summary["case"]["case_id"]))
    attempts = send_attempts(client, summary)
    after = gate_view(summary_of(client, summary["case"]["case_id"]))
    return {"before": before, "send": attempts, "after": after, "target_calls": target.calls}


def capture_uen_conflict(choice: str | None) -> dict:
    client, zero, documents, target, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic",
                              team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim")
    record = attach_conflict(zero, record)
    case_id = str(record.case_id)
    result: dict[str, Any] = {"open": gate_view(summary_of(client, case_id))}
    if choice is None:
        result["send"] = send_attempts(client, summary_of(client, case_id))
    else:
        extra = {}
        if choice == "DOCUMENT":
            document = documents.list_documents(case_id=record.case_id)[0]
            extra = {"document_id": str(document.document_id),
                     "expected_document_event_count": len(document.events)}
        current = zero._repository.get_for_case(record.case_id)
        response = correction(client, zero, current, choice=choice,
                              uen="202400001A" if choice == "ENTERED" else "202400009I", **extra)
        result["correction"] = http_view(response)
        resolved = summary_of(client, case_id)
        result["resolved"] = gate_view(resolved)
        result["send"] = http_view(confirm(client, resolved))
        result["after_send"] = gate_view(summary_of(client, case_id))
    result["target_calls"] = target.calls
    return result


def capture_opq(constitution: str | None, company_type: str | None) -> dict:
    with opq_lane(opq_body(constitution=constitution, company_type=company_type)) as (
        client, target,
    ):
        summary = summary_of(client, opq_at_review(client)["case"]["case_id"])
        result = {"review": gate_view(summary), "send": http_view(confirm(client, summary))}
        result["after_send"] = gate_view(summary_of(client, summary["case"]["case_id"]))
        result["writes"] = sandbox_writes(target)
        return result


def capture_xyz() -> dict:
    with mock_lane() as (client, _):
        summary = summary_of(client, xyz_at_ownership(client)["case"]["case_id"])
        return {"review": gate_view(summary), "send": http_view(confirm(client, summary)),
                "after_send": gate_view(summary_of(client, summary["case"]["case_id"]))}


def capture_all(monkeypatch: pytest.MonkeyPatch | None = None) -> dict:
    result: dict[str, Any] = {}
    for scenario in DEMO_SCENARIOS:
        result[f"demo:{scenario}"] = capture_demo(scenario)
    for choice in (None, "ENTERED", "DOCUMENT"):
        result[f"uen_conflict:{choice}"] = capture_uen_conflict(choice)
    result["opq:company_type_only"] = capture_opq(
        None, "EXEMPT PRIVATE COMPANY LIMITED BY SHARES"
    )
    result["opq:constitution_empty_register"] = capture_opq(
        "EXEMPT PRIVATE COMPANY LIMITED BY SHARES", None
    )
    result["xyz:advisory"] = capture_xyz()
    if monkeypatch is not None:
        with monkeypatch.context() as scoped:
            scoped.setenv("ACRA_MARKETPLACE_UBO_REVIEW_MODE", "blocking")
            result["xyz:blocking"] = capture_xyz()
    return json.loads(json.dumps(result, default=str))


def test_gate_readiness_and_send_outcomes_match_the_base_capture(monkeypatch) -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert capture_all(monkeypatch) == baseline
