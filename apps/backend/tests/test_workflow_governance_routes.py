"""P2-1 governance routes (contract C0 section 3, 4): RBAC, error bodies, 410s, startup."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest
from phase13_test_settings import ordinary_test_settings
from test_workflow_manager import STAGE, enabled_app, governed_publish, login, new_case
from workflow_publication_seed import capturing_workflow_store, store_for

from app.domain.workflows import ONBOARDING_USE_CASE, ONBOARDING_WORKFLOW_ID, WorkflowDefinition
from app.main import create_app
from app.services.workflow_governance import GovernanceStartup

URL = f"/api/workflows/{ONBOARDING_WORKFLOW_ID}"
MISSING = "00000000-0000-4000-8000-000000000000"


def propose(hr: Any, stages: list[dict[str, Any]]) -> dict[str, Any]:
    created = hr.post(
        f"{URL}/proposals",
        json={"expected_workflow_revision": hr.get(URL).json()["revision"], "stages": stages},
    )
    assert created.status_code == 201, created.json()
    return created.json()


def submit(hr: Any, proposal: dict[str, Any]) -> Any:
    purl = f"{URL}/proposals/{proposal['proposal_id']}"
    report = hr.post(f"{purl}/validate", json={}).json()
    return hr.post(
        f"{purl}/submit",
        json={
            "expected_workflow_revision": hr.get(URL).json()["revision"],
            "expected_proposal_revision": proposal["revision"],
            "content_hash": report["content_hash"],
        },
    )


def decision_body(client: Any, proposal: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "outcome": "APPROVE",
        "reason": "Approved through the route test.",
        "expected_workflow_revision": client.get(URL).json()["revision"],
        "expected_proposal_revision": proposal["revision"],
        "content_hash": proposal["content_hash"],
        "acknowledged_permanent_obligations": [],
        **extra,
    }


def test_the_governed_lifecycle_over_http_publishes_and_holds_a_new_case():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    published = governed_publish(director, ONBOARDING_WORKFLOW_ID, [STAGE])
    assert published["active_version"] == 1 and published["status"] == "ACTIVE"
    governance = published["governance"]
    assert governance["migrated"] and governance["latest_version"] == 1
    (provenance,) = governance["version_provenance"]
    assert provenance["origin"] == "GOVERNED_APPROVAL"
    assert (provenance["author_id"], provenance["approved_by"]) == ("hr-admin", "olivia-koh")
    assert governance["baseline"]["required_stages"] == 1
    case_id = new_case(maya)
    run = maya.get(f"/api/clm/zero-touch/cases/{case_id}/workflows").json()["onboarding"]
    assert run["workflow_version"] == 1 and run["stages"][0]["blocks_send"]


def test_hr_cannot_decide_and_the_director_cannot_author():
    app = enabled_app()
    hr, director = login(app, "hr-admin"), login(app, "olivia-koh")
    assert (
        director.post(
            f"{URL}/proposals", json={"expected_workflow_revision": 1, "stages": []}
        ).status_code
        == 403
    )
    proposal = propose(hr, [STAGE])
    pending = submit(hr, proposal).json()
    purl = f"{URL}/proposals/{proposal['proposal_id']}"
    refused = hr.post(f"{purl}/decision", json=decision_body(hr, pending))
    assert refused.status_code == 403 and refused.json()["detail"]["code"] == "WORKFLOW_FORBIDDEN"
    assert hr.get("/api/workflow-approvals").status_code == 403
    assert hr.get(f"{purl}/comparison").status_code == 403
    assert director.get("/api/workflows/simulation-scenarios").status_code == 403
    inbox = director.get("/api/workflow-approvals")
    assert inbox.status_code == 200 and inbox.json()["items"][0]["proposal"]["can_decide"]


def test_the_acknowledgement_and_a_second_decision_are_refused_with_the_contract_body():
    app = enabled_app()
    hr, director = login(app, "hr-admin"), login(app, "olivia-koh")
    proposal = propose(hr, [STAGE])
    pending = submit(hr, proposal).json()
    purl = f"{URL}/proposals/{proposal['proposal_id']}"
    missing_ack = director.post(f"{purl}/decision", json=decision_body(director, pending))
    assert missing_ack.status_code == 409
    detail = missing_ack.json()["detail"]
    assert detail["code"] == "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED"
    assert set(detail) == {"code", "message", "rule", "issues"}
    keys = [
        item["key"] for item in director.get(f"{purl}/comparison").json()["permanent_obligations"]
    ]
    body = decision_body(director, pending, acknowledged_permanent_obligations=keys)
    approved = director.post(f"{purl}/decision", json=body)
    assert approved.status_code == 200, approved.json()
    assert approved.json()["publication_report"]["published_version"] == 1
    again = director.post(f"{purl}/decision", json=body)
    assert again.status_code == 409 and again.json()["detail"]["code"] == "WORKFLOW_CONFLICT"
    fresh = director.post(
        f"{purl}/decision",
        json=decision_body(director, pending, acknowledged_permanent_obligations=keys),
    )
    assert fresh.json()["detail"]["code"] == "WORKFLOW_PROPOSAL_STATE_INVALID"


def test_a_ratchet_refusal_carries_its_rule_and_every_issue():
    app = enabled_app()
    governed_publish(login(app, "olivia-koh"), ONBOARDING_WORKFLOW_ID, [STAGE])
    hr = login(app, "hr-admin")  # after publication: a second HR login ends earlier sessions
    removing = propose(hr, [])
    refused = submit(hr, removing)
    assert refused.status_code == 422
    detail = refused.json()["detail"]
    assert detail["code"] == "WORKFLOW_REQUIRED_OBLIGATION_REMOVED"
    assert detail["rule"] == "RR-1" and detail["issues"]


@pytest.mark.parametrize("user_id", ["maya-lim", "ethan-tan", "support-user"])
def test_onboarders_rms_and_support_reach_no_governance_route(user_id):
    app = enabled_app()
    client = login(app, user_id)
    purl = f"{URL}/proposals/{MISSING}"
    requests = [
        ("GET", "/api/workflows/simulation-scenarios", None),
        ("GET", "/api/workflow-approvals", None),
        ("POST", f"{URL}/proposals", {"expected_workflow_revision": 1}),
        (
            "PUT",
            purl,
            {"expected_workflow_revision": 1, "expected_proposal_revision": 1, "stages": []},
        ),
        ("POST", f"{purl}/validate", {}),
        ("POST", f"{purl}/simulate", {}),
        (
            "POST",
            f"{purl}/submit",
            {
                "expected_workflow_revision": 1,
                "expected_proposal_revision": 1,
                "content_hash": "0" * 64,
            },
        ),
        (
            "POST",
            f"{purl}/withdraw",
            {"expected_workflow_revision": 1, "expected_proposal_revision": 1},
        ),
        ("GET", f"{purl}/comparison", None),
        (
            "POST",
            f"{purl}/decision",
            {
                "outcome": "REJECT",
                "reason": "Not for this role.",
                "expected_workflow_revision": 1,
                "expected_proposal_revision": 1,
                "content_hash": "0" * 64,
            },
        ),
    ]
    for method, path, body in requests:
        response = client.request(method, path, json=body)
        assert response.status_code == 403, (method, path, response.json())


def test_inaccessible_items_are_a_safe_404_and_fixed_routes_are_not_shadowed():
    app = enabled_app()
    hr, director = login(app, "hr-admin"), login(app, "olivia-koh")
    scenarios = hr.get("/api/workflows/simulation-scenarios")
    assert scenarios.status_code == 200 and all(item["synthetic"] for item in scenarios.json())
    assert director.get("/api/workflow-approvals").json() == {"items": []}
    unknown = hr.get("/api/workflows/not-a-workflow")
    assert unknown.status_code == 404 and unknown.json()["detail"]["code"] == "WORKFLOW_NOT_FOUND"
    assert (
        hr.post(
            "/api/workflows/not-a-workflow/proposals", json={"expected_workflow_revision": 1}
        ).status_code
        == 404
    )
    missing = hr.post(f"{URL}/proposals/{MISSING}/validate", json={})
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "WORKFLOW_PROPOSAL_NOT_FOUND"


def test_activate_and_put_draft_are_retired():
    app = enabled_app()
    for user_id in ("hr-admin", "olivia-koh"):
        client = login(app, user_id)
        assert client.post(f"{URL}/activate", json={}).status_code == 410
        response = client.put(f"{URL}/draft", json={"expected_revision": 1, "stages": []})
        assert response.status_code == 410
        assert response.json()["detail"]["code"] == "WORKFLOW_ROUTE_RETIRED"
    assert store_for(app).definitions.get(ONBOARDING_WORKFLOW_ID).versions == ()


def test_startup_migrates_memory_mode_and_verifies():
    app = enabled_app()
    store = store_for(app)
    governed = store.definitions.get_governed(ONBOARDING_WORKFLOW_ID)
    assert governed.governance.migrated
    assert store.definitions.verify_governance_state() == []


def _legacy_store() -> Any:
    from workflow_publication_seed import memory_workflow_store

    from app.domain.workflows import WorkflowStage, WorkflowVersion

    store = memory_workflow_store()
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    store.definitions.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            versions=(
                WorkflowVersion(
                    version=1,
                    stages=(WorkflowStage.model_validate(STAGE),),
                    activated_at=moment,
                    activated_by="olivia-koh",
                ),
            ),
            created_at=moment,
            updated_at=moment,
        )
    )
    return store


def test_a_legacy_memory_store_is_migrated_with_honest_provenance():
    with capturing_workflow_store(_legacy_store()) as store:
        app = create_app(ordinary_test_settings(workflow_manager_enabled=True))
    hr = login(app, "hr-admin")
    governance = hr.get(URL).json()["governance"]
    (provenance,) = governance["version_provenance"]
    assert provenance["origin"] == "PRE_GOVERNANCE_DIRECTOR_ACTIVATION"
    assert provenance["approved_by"] is None and provenance["author_id"] is None
    assert store.definitions.verify_governance_state() == []


def test_an_unmigrated_store_answers_503_for_mutations_and_null_governance_for_reads():
    unmigrated = GovernanceStartup(available=True, blocked={})
    with (
        patch("app.main.start_governance", return_value=unmigrated),
        capturing_workflow_store(_legacy_store()),
    ):
        app = create_app(ordinary_test_settings(workflow_manager_enabled=True))
    hr = login(app, "hr-admin")
    read = hr.get(URL)
    assert read.status_code == 200 and read.json()["governance"] is None
    refused = hr.post(f"{URL}/proposals", json={"expected_workflow_revision": 1})
    assert refused.status_code == 503
    assert refused.json()["detail"]["code"] == "WORKFLOW_GOVERNANCE_NOT_MIGRATED"
    created = hr.post("/api/workflows", json={"name": "R", "use_case": "R", "country": "SG"})
    assert created.status_code == 503
    assert created.json()["detail"]["code"] == "WORKFLOW_GOVERNANCE_NOT_MIGRATED"


def test_a_failed_startup_verification_blocks_mutations_but_not_reads():
    with patch(
        "app.services.workflow_repository.InMemoryWorkflowDefinitionRepository"
        ".verify_governance_state",
        side_effect=RuntimeError("verification failed"),
    ):
        app = enabled_app()
    hr = login(app, "hr-admin")
    read = hr.get(URL)
    assert read.status_code == 200
    assert read.json()["governance"]["can_create_proposal"] is False
    refused = hr.post(
        f"{URL}/proposals", json={"expected_workflow_revision": read.json()["revision"]}
    )
    assert refused.status_code == 503
    assert refused.json()["detail"]["code"] == "WORKFLOW_HISTORY_UNAVAILABLE"
