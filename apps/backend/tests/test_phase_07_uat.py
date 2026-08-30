"""Sponsor-observable Phase 07 UAT and evidence-export checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

PDF = (Path(__file__).parent / "fixtures" / "uat" / "clean-company-profile.pdf").read_bytes()


def _client(*, demo: bool = True) -> TestClient:
    return TestClient(create_app(Settings(app_env="test", demo_controls_enabled=demo)))


def _start(client: TestClient, scenario: str) -> dict[str, Any]:
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": scenario},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    attached = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
        headers={"content-type": "application/pdf", "X-Document-Name": "uat.pdf"},
        content=PDF,
    )
    assert attached.status_code == 200
    return attached.json()


def test_execution_profile_is_safe_and_available_without_demo_controls() -> None:
    response = _client(demo=False).get("/api/system/execution-profile")

    assert response.status_code == 200
    assert response.json() == {
        "is_simulated": True,
        "registry_system": "ACRA",
        "registry_environment": "MOCK",
        "target_system": "GOLDTIER",
        "target_environment": "MOCK",
        "idp_system": "IDP",
        "idp_environment": "LOCAL",
        "idp_provider": "LOCAL_PDF_TEXT",
        "idp_review_confidence_threshold": 0.85,
        "ownership_system": "OWNERSHIP_PROVIDER",
        "ownership_environment": "MOCK",
        "ubo_ownership_threshold_percent": "25",
    }


@pytest.mark.parametrize(
    ("scenario", "status", "stage", "blocker"),
    [
        ("LOW_CONFIDENCE", "WAITING_FOR_REVIEW", "DOCUMENT", "DOCUMENT_LOW_CONFIDENCE"),
        ("OWNERSHIP_CYCLE", "WAITING_FOR_REVIEW", "OWNERSHIP", "OWNERSHIP_CYCLE"),
        (
            "MULTIPLE_DOCUMENT_BLOCKERS",
            "WAITING_FOR_REVIEW",
            "DOCUMENT",
            "DOCUMENT_SOURCE_CONFLICT",
        ),
        (
            "PARTIAL_AMEND",
            "WAITING_FOR_REVIEW",
            "MOCK_GOLDTIER",
            "GT_OPTIONAL_SECTION_REVIEW",
        ),
    ],
)
def test_presenter_presets_reach_truthful_review_boundaries(
    scenario: str, status: str, stage: str, blocker: str
) -> None:
    result = _start(_client(), scenario)

    assert result["status"] == status
    assert result["current_stage"] == stage
    assert result["active_exceptions"][0]["blocker_code"] == blocker


def test_multiple_document_blockers_remain_visible_and_stop_target() -> None:
    client = _client()
    result = _start(client, "MULTIPLE_DOCUMENT_BLOCKERS")
    exception = result["active_exceptions"][0]

    assert set(exception["blocker_codes"]) == {
        "DOCUMENT_SOURCE_CONFLICT",
        "DOCUMENT_LOW_CONFIDENCE",
    }
    evidence = client.get(
        f"/api/demo/clm/zero-touch/cases/{result['case']['case_id']}/uat-evidence"
    ).json()
    assert evidence["target_calls"] == []
    assert set(evidence["active_blockers"]) == set(exception["blocker_codes"])


def test_multiple_ownership_paths_complete_with_server_authored_candidate_summary() -> None:
    client = _client()
    result = _start(client, "MULTIPLE_OWNERSHIP_PATHS")

    assert result["status"] == "COMPLETED"
    assert result["metrics"]["human_interventions"] == 0
    assert result["clm"]["related_party_preparation"]["provisional_candidate_count"] == 1
    evidence = client.get(
        f"/api/demo/clm/zero-touch/cases/{result['case']['case_id']}/uat-evidence"
    ).json()
    assert evidence["uat_case_id"] == "UAT-07"
    assert evidence["target_calls"] == ["SEARCH", "SHELL", "POLICY", "AMEND"]


def test_recovery_preset_is_pending_then_finalizes_without_target_replay() -> None:
    client = _client()
    pending = _start(client, "RECOVERY")
    case_id = pending["case"]["case_id"]

    assert pending["status"] == "RECOVERY_PENDING"
    first_evidence = client.get(f"/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence").json()
    assert first_evidence["uat_case_id"] == "UAT-11"
    assert first_evidence["target_calls"] == ["SEARCH", "SHELL", "POLICY", "AMEND"]

    recovered = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "COMPLETED"
    second_evidence = client.get(f"/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence").json()
    assert second_evidence["target_calls"] == first_evidence["target_calls"]
    assert second_evidence["target_outcome"] == "MOCK_GOLDTIER_SUBMITTED"


def test_uat_evidence_is_whitelisted_and_demo_gated() -> None:
    client = _client()
    result = _start(client, "STRAIGHT_THROUGH")
    case_id = result["case"]["case_id"]
    response = client.get(f"/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence")

    assert response.status_code == 200
    evidence = response.json()
    assert evidence["uat_case_id"] == "UAT-01"
    assert evidence["human_interventions"] == 0
    serialized = json.dumps(evidence).lower()
    for prohibited in (
        "pdf-1.4",
        "source_reference",
        "authoritative_evidence_digest",
        "input_fingerprint",
        "authorization",
        "client_secret",
        "private_",
    ):
        assert prohibited not in serialized

    disabled = _client(demo=False).get(
        "/api/demo/clm/zero-touch/cases/00000000-0000-4000-8000-000000000001/uat-evidence"
    )
    assert disabled.status_code == 404
    assert disabled.json()["detail"]["code"] == "DEMO_CONTROLS_DISABLED"
