"""D-123 Director workflows, RM/onboarder field collection, autofill and the send check."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import SHARE_COMPANIES
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import (
    NoAcra,
    RecordingTarget,
    prepare,
    sandbox_settings,
)
from workflow_publication_seed import (
    capturing_workflow_store,
    publish_draft,
    register_app_store,
    store_for,
)

from app.domain.access import SYNTHETIC_USER_PROFILES, AuthenticatedActor
from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowAnswer, WorkflowStage
from app.main import create_app
from app.persistence.composition import WorkflowPersistence, build_persistence_bundle
from app.persistence.errors import PersistenceUnavailableError
from app.services.case_deletion import _restore
from app.services.workflow_autofill import (
    find_labelled_value,
    match_option,
    normalize_date,
    normalize_number,
)
from app.services.workflow_management import (
    HOLD_INCOMPLETE,
    HOLD_UNAVAILABLE,
    WorkflowConflictError,
    WorkflowManagementService,
    WorkflowValidationError,
    _suggested_value,
)
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
)

STAGE = {
    "stage_id": "signatory",
    "name": "Authorised signatory details",
    "after_node_id": "DOCUMENT_IDP",
    "fields": [
        {"field_id": "full-name", "label": "Full name", "kind": "TEXT", "required": True,
         "autofill": True, "document_label": "Full name"},
        {"field_id": "birth-date", "label": "Date of birth", "kind": "DATE", "required": True},
        {"field_id": "notes", "label": "Notes", "kind": "TEXT", "required": False},
    ],
}
REFRESH_STAGES = [
    {"stage_id": "first", "name": "Refresh details", "fields": [
        {"field_id": "reason", "label": "Reason", "kind": "CHOICE", "options": ["Scheduled"]},
    ]},
    {"stage_id": "second", "name": "Company changes", "fields": [
        {"field_id": "changed", "label": "Any change?", "kind": "YES_NO"},
    ]},
]


def login(app, user_id):
    client = RawTestClient(app)
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


def enabled_app(workflow_store=None):
    with capturing_workflow_store(workflow_store) as store:
        app = create_app(ordinary_test_settings(workflow_manager_enabled=True))
    register_app_store(app, store)
    return app


def activate_onboarding(director, stages=(STAGE,)):
    baseline = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}").json()
    saved = director.put(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/draft",
        json={"expected_revision": baseline["revision"], "stages": list(stages)},
    )
    assert saved.status_code == 200, saved.json()
    # Activation is frozen (ADR-017); publish the draft as governed publication will.
    publish_draft(store_for(director).definitions, ONBOARDING_WORKFLOW_ID, actor_id="olivia-koh")
    active = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}")
    assert active.status_code == 200, active.json()
    return active.json()


def new_case(client, uen="202400001A"):
    response = client.post("/api/clm/zero-touch/cases", json={"uen": uen})
    assert response.status_code == 201, response.json()
    return response.json()["case"]["case_id"]


def case_url(case_id, run, stage_id, action):
    return (
        f"/api/clm/zero-touch/cases/{case_id}/workflows/runs/{run['run_id']}"
        f"/stages/{stage_id}/{action}"
    )


def onboarding_run(client, case_id):
    return client.get(f"/api/clm/zero-touch/cases/{case_id}/workflows").json()["onboarding"]


def test_it_is_on_by_default_and_changes_nothing_until_a_stage_is_activated():
    app = create_app(ordinary_test_settings())
    case_id = new_case(login(app, "maya-lim"))
    view = login(app, "maya-lim").get(f"/api/clm/zero-touch/cases/{case_id}/workflows").json()
    assert view == {"onboarding": None, "runs": []}


def test_it_can_still_be_switched_off():
    app = create_app(ordinary_test_settings(workflow_manager_enabled=False))
    director = login(app, "olivia-koh")
    response = director.get("/api/workflows")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "WORKFLOW_MANAGER_DISABLED"
    case_id = new_case(login(app, "maya-lim"))
    assert login(app, "maya-lim").get(
        f"/api/clm/zero-touch/cases/{case_id}/workflows"
    ).status_code == 404


@pytest.mark.parametrize("user_id", ["maya-lim", "ethan-tan", "hr-admin", "support-user"])
def test_only_the_director_reaches_workflow_definitions(user_id):
    client = login(enabled_app(), user_id)
    assert client.get("/api/workflows").status_code == 403
    assert client.post(
        "/api/workflows", json={"name": "X", "use_case": "Case refresh", "country": "Singapore"}
    ).status_code == 403
    assert client.put(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/draft",
        json={"expected_revision": 1, "stages": []},
    ).status_code == 403


def test_onboarding_workflow_lists_the_locked_stages_and_its_use_case_tag():
    director = login(enabled_app(), "olivia-koh")
    (onboarding,) = director.get("/api/workflows").json()
    assert onboarding["use_case"] == "Onboarding"
    assert onboarding["status"] == "ACTIVE"
    assert onboarding["active_version"] is None
    assert [item["label"] for item in onboarding["locked_stages"]] == [
        "Case created", "Initial identity", "Jurisdiction", "Existing-customer search",
        "Registry verification", "Document verification", "Data reconciliation",
        "Ownership & UBO", "Risk assessment", "GoldTier Details & Status",
        "Final review & send",
    ]


def test_a_second_onboarding_workflow_cannot_be_created():
    director = login(enabled_app(), "olivia-koh")
    response = director.post(
        "/api/workflows", json={"name": "X", "use_case": "onboarding", "country": "Singapore"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "WORKFLOW_USE_CASE_RESERVED"


@pytest.mark.parametrize(
    ("stage", "code"),
    [
        ({**STAGE, "fields": []}, "WORKFLOW_FIELD_REQUIRED"),
        (
            {**STAGE, "fields": [{"field_id": "c", "label": "C", "kind": "CHOICE"}]},
            "WORKFLOW_OPTIONS_REQUIRED",
        ),
        (
            {**STAGE, "fields": [
                {"field_id": "n", "label": "N", "kind": "NUMBER", "autofill": True},
            ]},
            "WORKFLOW_AUTOFILL_INVALID",
        ),
    ],
)
def test_incomplete_stages_save_as_a_draft_but_cannot_activate(stage, code):
    """ADR-017 P2-0: activation is frozen for every draft; nothing is published."""
    del code
    director = login(enabled_app(), "olivia-koh")
    baseline = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}").json()
    saved = director.put(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/draft",
        json={"expected_revision": baseline["revision"], "stages": [stage]},
    ).json()
    response = director.post(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/activate",
        json={"expected_revision": saved["revision"]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "WORKFLOW_PUBLICATION_FROZEN"
    after = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}").json()
    assert after["revision"] == saved["revision"] and after["versions"] == []


@pytest.mark.parametrize("anchor", [None, "FINAL_REVIEW_SEND", "NOT_A_STAGE"])
def test_an_onboarding_stage_must_follow_a_stage_before_final_review(anchor):
    director = login(enabled_app(), "olivia-koh")
    baseline = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}").json()
    response = director.put(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/draft",
        json={
            "expected_revision": baseline["revision"],
            "stages": [{**STAGE, "after_node_id": anchor}],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "WORKFLOW_STAGE_POSITION_INVALID"


def test_a_stale_director_edit_is_refused():
    director = login(enabled_app(), "olivia-koh")
    baseline = director.get(f"/api/workflows/{ONBOARDING_WORKFLOW_ID}").json()
    body = {"expected_revision": baseline["revision"], "stages": [STAGE]}
    url = f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/draft"
    assert director.put(url, json=body).status_code == 200
    stale = director.put(url, json=body)
    assert stale.status_code == 409


def test_a_stage_reaches_open_cases_and_keeps_unchanged_answers():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    older = new_case(maya)
    activated = activate_onboarding(director)
    newer = new_case(maya, "202400002A")

    assert activated["active_version"] == 1
    assert onboarding_run(maya, older)["workflow_version"] == 1
    run = onboarding_run(maya, newer)
    assert run["workflow_version"] == 1
    assert run["stages"][0]["after_node_id"] == "DOCUMENT_IDP"
    assert run["stages"][0]["status"] == "OPEN"

    second = {**STAGE, "stage_id": "other", "name": "Another stage"}
    saved = maya.put(
        case_url(newer, run, "signatory", "answers"),
        json={
            "expected_revision": 0,
            "values": {"full-name": "Sample", "birth-date": "1980-01-15"},
        },
    ).json()
    assert maya.post(
        case_url(newer, run, "signatory", "confirm"), json={"expected_revision": saved["revision"]}
    ).status_code == 200

    activate_onboarding(director, (STAGE, second))
    moved = onboarding_run(maya, newer)
    assert moved["workflow_version"] == 2
    assert [item["status"] for item in moved["stages"]] == ["COMPLETE", "OPEN"]
    assert moved["stages"][0]["fields"][0]["value"] == "Sample"

    changed = {**STAGE, "name": "Renamed stage"}
    activate_onboarding(director, (changed,))
    again = onboarding_run(maya, newer)
    assert [item["status"] for item in again["stages"]] == ["OPEN"]
    assert again["stages"][0]["fields"][0]["value"] == "Sample"
    refilled = maya.post(
        case_url(newer, again, "signatory", "confirm"),
        json={"expected_revision": again["revision"]},
    )
    assert refilled.status_code == 200, refilled.json()
    assert onboarding_run(maya, newer)["workflow_version"] == 3


def test_rm_or_onboarder_fills_and_confirms_while_the_director_cannot():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    activate_onboarding(director)
    case_id = new_case(maya)
    run = onboarding_run(maya, case_id)
    values = {"full-name": "Sample Person", "birth-date": "1980-01-15"}

    assert director.put(
        case_url(case_id, run, "signatory", "answers"),
        json={"expected_revision": 0, "values": values},
    ).status_code == 403
    assert maya.post(
        case_url(case_id, run, "signatory", "confirm"), json={"expected_revision": 0}
    ).json()["detail"]["code"] == "WORKFLOW_REQUIRED_FIELD_MISSING"

    saved = maya.put(
        case_url(case_id, run, "signatory", "answers"),
        json={"expected_revision": 0, "values": values},
    )
    assert saved.status_code == 200, saved.json()
    assert saved.json()["stages"][0]["status"] == "OPEN"
    confirmed = maya.post(
        case_url(case_id, run, "signatory", "confirm"),
        json={"expected_revision": saved.json()["revision"]},
    ).json()
    assert confirmed["stages"][0]["status"] == "COMPLETE"
    assert confirmed["stages"][0]["confirmed_by"] == "maya-lim"

    changed = maya.put(
        case_url(case_id, run, "signatory", "answers"),
        json={"expected_revision": confirmed["revision"], "values": {"full-name": "Other"}},
    ).json()
    assert changed["stages"][0]["status"] == "OPEN"


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"birth-date": "15 Jan 1980"}, "WORKFLOW_ANSWER_INVALID"),
        ({"unknown": "x"}, "WORKFLOW_FIELD_UNKNOWN"),
    ],
)
def test_answers_are_validated_by_the_backend(values, code):
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    activate_onboarding(director)
    case_id = new_case(maya)
    run = onboarding_run(maya, case_id)
    response = maya.put(
        case_url(case_id, run, "signatory", "answers"),
        json={"expected_revision": 0, "values": values},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code


def test_another_team_gets_the_safe_404():
    app = enabled_app()
    director, maya, sophia = (login(app, item) for item in ("olivia-koh", "maya-lim", "sophia-ng"))
    activate_onboarding(director)
    case_id = new_case(maya)
    run = onboarding_run(maya, case_id)
    assert sophia.get(f"/api/clm/zero-touch/cases/{case_id}/workflows").status_code == 404
    assert sophia.put(
        case_url(case_id, run, "signatory", "answers"),
        json={"expected_revision": 0, "values": {}},
    ).status_code == 404


@patch("app.main._automation_is_complete", return_value=True)
def test_an_active_workflow_is_startable_by_rm_or_onboarder_and_stages_open_in_order(_sent):
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    case_id = new_case(maya)
    created = director.post(
        "/api/workflows",
        json={
            "name": "Corporate refresh",
            "use_case": "Case refresh",
            "country": "Singapore",
        },
    ).json()
    url = f"/api/workflows/{created['workflow_id']}"
    assert maya.post(f"{url}/runs", json={"case_id": case_id}).status_code == 422
    assert maya.get("/api/workflows/startable").json() == []

    director.put(
        f"{url}/draft", json={"expected_revision": created["revision"], "stages": REFRESH_STAGES}
    ).json()
    publish_draft(store_for(director).definitions, url.rsplit("/", 1)[1])

    assert maya.get("/api/workflows/startable").json() == [
        {
            "workflow_id": created["workflow_id"],
            "name": "Corporate refresh",
            "case_source": "EXISTING_CASE",
        }
    ]
    assert director.get("/api/workflows/startable").json() == []
    assert director.post(f"{url}/runs", json={"case_id": case_id}).status_code == 403
    started = maya.post(f"{url}/runs", json={"case_id": case_id})
    assert started.status_code == 201, started.json()
    run = started.json()
    assert run["use_case"] == "Case refresh"
    assert [item["status"] for item in run["stages"]] == ["OPEN", "LOCKED"]
    assert maya.post(f"{url}/runs", json={"case_id": case_id}).status_code == 409

    listed = maya.get(f"{url}/runs").json()
    assert [item["run"]["run_id"] for item in listed] == [run["run_id"]]
    assert listed[0]["registration_id"] == "202400001A"
    assert login(app, "sophia-ng").get(f"{url}/runs").json() == []
    assert director.get(f"{url}/runs").status_code == 403
    view = maya.get(f"/api/clm/zero-touch/cases/{case_id}/workflows").json()
    assert view["onboarding"] is None
    assert [item["run_id"] for item in view["runs"]] == [run["run_id"]]
    locked = maya.put(
        case_url(case_id, run, "second", "answers"),
        json={"expected_revision": run["revision"], "values": {"changed": "No"}},
    )
    assert locked.json()["detail"]["code"] == "WORKFLOW_STAGE_LOCKED"

    filled = maya.put(
        case_url(case_id, run, "first", "answers"),
        json={"expected_revision": run["revision"], "values": {"reason": "Scheduled"}},
    ).json()
    done = maya.post(
        case_url(case_id, run, "first", "confirm"), json={"expected_revision": filled["revision"]}
    ).json()
    assert [item["status"] for item in done["stages"]] == ["COMPLETE", "OPEN"]


def test_an_existing_case_workflow_needs_a_case_that_finished_onboarding():
    case = FakeCase()
    service = service_with_stage(case)
    actor = director_actor()
    created = service.create_workflow(
        lambda: actor, name="Refresh", use_case="Refresh", country="Singapore"
    )
    service.save_draft(
        lambda: actor,
        created.workflow_id,
        expected_revision=created.revision,
        stages=(WorkflowStage.model_validate(REFRESH_STAGES[0]),),
    )
    publish_draft(service._definitions, created.workflow_id, now=service._clock())  # noqa: SLF001
    filler = filler_actor()
    with pytest.raises(WorkflowValidationError) as refused:
        service.start_run(lambda: filler, created.workflow_id, case_id=case.case_id)
    assert refused.value.code == "WORKFLOW_CASE_NOT_ONBOARDED"
    service._case_is_onboarded = lambda _case_id: True
    assert service.start_run(lambda: filler, created.workflow_id, case_id=case.case_id)
    with pytest.raises(WorkflowConflictError):
        service.start_run(lambda: filler, created.workflow_id, case_id=case.case_id)


def new_case_workflow(director):
    created = director.post(
        "/api/workflows",
        json={"name": "R", "use_case": "R", "country": "SG", "case_source": "NEW_CASE"},
    ).json()
    url = f"/api/workflows/{created['workflow_id']}"
    stage = {"stage_id": "first", "name": "Details", "fields": [
        {"field_id": "reference", "label": "Reference", "kind": "TEXT", "autofill": True,
         "document_label": "Reference"},
    ]}
    director.put(
        f"{url}/draft", json={"expected_revision": created["revision"], "stages": [stage]}
    ).json()
    publish_draft(store_for(director).definitions, url.rsplit("/", 1)[1])
    return url


COMPANY = {"legal_name": "Typed Name Pte Ltd", "registration_id": "202400002A",
           "jurisdiction": "HK", "priority": 5}


def test_a_workflow_only_case_creates_no_onboarding_case():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    url = new_case_workflow(director)
    created = maya.post(f"{url}/new-cases", json=COMPANY)
    assert created.status_code == 201, created.json()
    item = created.json()
    assert item["company"] == "Typed Name Pte Ltd"
    assert item["case_id"] is None
    assert maya.get("/api/clm/zero-touch/cases").json() == []
    assert [row["company"] for row in maya.get(f"{url}/runs").json()] == ["Typed Name Pte Ltd"]


def test_workflow_only_case_is_filled_confirmed_and_autofilled_by_its_team():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    url = new_case_workflow(director)
    run = maya.post(f"{url}/new-cases", json=COMPANY).json()["run"]
    base = f"{url}/runs/{run['run_id']}"

    uploaded = maya.post(
        f"{base}/documents",
        content=b"Reference: ABC123\n",
        headers={"Content-Type": "text/plain", "X-Document-Name": "profile.txt"},
    )
    assert uploaded.status_code == 200, uploaded.json()
    field = uploaded.json()["stages"][0]["fields"][0]
    assert (field["value"], field["source"]) == ("ABC123", "DOCUMENT")
    assert uploaded.json()["stages"][0]["status"] == "OPEN"

    edited = maya.put(
        f"{base}/stages/first/answers",
        json={"expected_revision": uploaded.json()["revision"], "values": {"reference": "XYZ"}},
    ).json()
    assert maya.put(
        f"{base}/stages/first/answers",
        json={"expected_revision": uploaded.json()["revision"], "values": {}},
    ).status_code == 409
    done = maya.post(
        f"{base}/stages/first/confirm", json={"expected_revision": edited["revision"]}
    ).json()
    assert done["stages"][0]["status"] == "COMPLETE"


def test_workflow_only_case_is_hidden_from_other_teams_and_roles():
    app = enabled_app()
    director, maya, sophia = (login(app, item) for item in ("olivia-koh", "maya-lim", "sophia-ng"))
    url = new_case_workflow(director)
    run = maya.post(f"{url}/new-cases", json=COMPANY).json()["run"]
    base = f"{url}/runs/{run['run_id']}"
    assert sophia.get(f"{url}/runs").json() == []
    body = {"expected_revision": run["revision"], "values": {"reference": "X"}}
    assert sophia.put(f"{base}/stages/first/answers", json=body).status_code == 404
    assert sophia.post(
        f"{base}/stages/first/confirm", json={"expected_revision": run["revision"]}
    ).status_code == 404
    assert sophia.delete(base).status_code == 404
    assert director.put(f"{base}/stages/first/answers", json=body).status_code == 403
    assert director.post(f"{url}/new-cases", json=COMPANY).status_code == 403


def test_only_a_relationship_manager_deletes_a_workflow_only_case():
    app = enabled_app()
    director, maya, ethan = (login(app, item) for item in ("olivia-koh", "maya-lim", "ethan-tan"))
    url = new_case_workflow(director)
    run = maya.post(f"{url}/new-cases", json=COMPANY).json()["run"]
    base = f"{url}/runs/{run['run_id']}"
    assert maya.delete(base).status_code == 403
    assert ethan.delete(base).status_code == 204
    assert maya.get(f"{url}/runs").json() == []
    assert ethan.delete(base).status_code == 404


def test_each_workflow_type_only_starts_its_own_way():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    url = new_case_workflow(director)
    refused = maya.post(f"{url}/runs", json={"case_id": new_case(maya)})
    assert refused.json()["detail"]["code"] == "WORKFLOW_NOT_STARTABLE"
    created = director.post(
        "/api/workflows", json={"name": "E", "use_case": "E", "country": "SG"}
    ).json()
    response = maya.post(f"/api/workflows/{created['workflow_id']}/new-cases", json=COMPANY)
    assert response.json()["detail"]["code"] == "WORKFLOW_NOT_STARTABLE"


def existing_workflow_service(case, values, runs=None):
    service = service_with_stage(case, runs)
    service._case_data = lambda _case_id: values
    service._case_is_onboarded = lambda _case_id: True
    return service


def start_with(service, case, stage):
    actor = director_actor()
    created = service.create_workflow(
        lambda: actor, name="Refresh", use_case="Refresh", country="Singapore"
    )
    service.save_draft(
        lambda: actor,
        created.workflow_id,
        expected_revision=created.revision,
        stages=(WorkflowStage.model_validate(stage),),
    )
    publish_draft(service._definitions, created.workflow_id, now=service._clock())  # noqa: SLF001
    return service.start_run(
        lambda: filler_actor(), created.workflow_id, case_id=case.case_id
    )


def test_an_existing_case_run_starts_with_the_data_the_case_holds():
    case = FakeCase()
    service = existing_workflow_service(
        case, {"LEGAL_NAME": "Real Co", "RISK_LEVEL": "Low", "OWNERSHIP_PERCENT": "not a number"}
    )
    stage = {"stage_id": "s", "name": "Mixed", "fields": [
        {"field_id": "name", "label": "Legal name", "kind": "TEXT", "case_data_key": "LEGAL_NAME"},
        {"field_id": "risk", "label": "Risk", "kind": "CHOICE", "options": ["Low", "High"],
         "case_data_key": "RISK_LEVEL"},
        {"field_id": "pct", "label": "Percent", "kind": "NUMBER",
         "case_data_key": "OWNERSHIP_PERCENT"},
        {"field_id": "missing", "label": "Missing", "kind": "TEXT", "case_data_key": "GOLDTIER_ID"},
        {"field_id": "plain", "label": "Plain", "kind": "TEXT"},
    ]}
    run = start_with(service, case, stage)
    assert {item.field_id: (item.value, item.source) for item in run.answers} == {
        "name": ("Real Co", "CASE"),
        "risk": ("Low", "CASE"),
    }
    assert run.confirmations == ()


def test_answers_to_added_onboarding_stages_carry_into_the_workflow():
    case = FakeCase()
    runs = InMemoryWorkflowRunRepository()
    service = existing_workflow_service(case, {}, runs)
    onboarding = service.case_view(case).onboarding
    service._persist(onboarding, answers=(
        WorkflowAnswer(stage_id="signatory", field_id="full-name", value="Sample Person"),
    ))
    copied = {"stage_id": "copy", "name": STAGE["name"], "fields": [
        {"field_id": "new-id", "label": "Full name", "kind": "TEXT"},
    ]}
    run = start_with(service, case, copied)
    assert [(item.field_id, item.value) for item in run.answers] == [("new-id", "Sample Person")]


def test_a_sent_case_cannot_be_edited_or_confirmed():
    case = FakeCase()
    service = service_with_stage(case)
    run = service.case_view(case).onboarding
    actor = filler_actor()
    service.save_answers(
        lambda: actor, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
        expected_revision=0, values={"full-name": "Sample", "birth-date": "1980-01-15"},
    )
    service._case_is_sent = lambda _case_id: True
    for call in (
        lambda: service.save_answers(
            lambda: actor, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
            expected_revision=1, values={"full-name": "Changed"},
        ),
        lambda: service.confirm_stage(
            lambda: actor, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
            expected_revision=1,
        ),
    ):
        with pytest.raises(WorkflowValidationError) as refused:
            call()
        assert refused.value.code == "WORKFLOW_CASE_SENT"


def test_a_failed_send_is_not_finished_onboarding():
    """ADR-017 3.7: MOCK_GOLDTIER alone is never "sent"; a write attempt marker is."""
    from types import SimpleNamespace

    from app.domain.zero_touch import AutomationStage, AutomationStatus
    from app.main import _automation_is_complete, _case_is_sent

    failed = SimpleNamespace(
        status=AutomationStatus.TECHNICAL_FAILURE, current_stage=AutomationStage.MOCK_GOLDTIER
    )
    no_marker = SimpleNamespace(case_is_sent=lambda _case_id: False)
    marker = SimpleNamespace(case_is_sent=lambda _case_id: True)
    complete = SimpleNamespace(current_stage=AutomationStage.COMPLETE)
    assert not _case_is_sent(no_marker, failed, uuid4())
    assert _case_is_sent(marker, failed, uuid4())
    assert _case_is_sent(no_marker, complete, uuid4())
    assert not _automation_is_complete(failed)
    assert _automation_is_complete(SimpleNamespace(status=AutomationStatus.COMPLETED))


def test_a_changed_stage_refuses_a_stale_screen_and_drops_a_now_invalid_answer():
    case = FakeCase()
    service = service_with_stage(case)
    filler, director = filler_actor(), director_actor()
    run = service.case_view(case).onboarding
    saved = service.save_answers(
        lambda: filler, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
        expected_revision=0, values={"full-name": "Sample", "birth-date": "1980-01-15"},
    )
    changed = dict(STAGE)
    changed["fields"] = [
        {"field_id": "full-name", "label": "Full name", "kind": "NUMBER", "required": True},
    ]
    baseline = service.get_workflow(director, ONBOARDING_WORKFLOW_ID)
    service.save_draft(
        lambda: director, ONBOARDING_WORKFLOW_ID, expected_revision=baseline.revision,
        stages=(WorkflowStage.model_validate(changed),),
    )
    publish_draft(service._definitions, ONBOARDING_WORKFLOW_ID, now=service._clock())  # noqa: SLF001
    case.created_at = datetime(2031, 1, 1, tzinfo=UTC)

    with pytest.raises(WorkflowConflictError):
        service.confirm_stage(
            lambda: filler, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
            expected_revision=saved.revision,
        )
    current = service.case_view(case).onboarding
    assert current.workflow_version == 2
    assert current.answers == ()
    with pytest.raises(WorkflowValidationError):
        service.confirm_stage(
            lambda: filler, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
            expected_revision=current.revision,
        )
    assert service.send_hold_code(case.case_id) == HOLD_INCOMPLETE


def test_a_failed_case_deletion_keeps_the_workflow_answers():
    runs = InMemoryWorkflowRunRepository()
    case = FakeCase()
    service = service_with_stage(case, runs)
    run = service.case_view(case).onboarding
    service.save_answers(
        lambda: filler_actor(), case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
        expected_revision=0, values={"full-name": "Sample"},
    )
    restore = service.delete_case_data(case.case_id)
    assert runs.list_for_case(case.case_id) == []
    restore()
    assert runs.list_for_case(case.case_id)[0].answers[0].value == "Sample"


def test_a_saved_suggestion_is_not_replaced_by_a_later_document():
    case = FakeCase()
    runs = InMemoryWorkflowRunRepository()
    service = service_with_stage(case, runs)

    def suggest(text):
        service.suggest_from_document(
            case_id=case.case_id, document_id=case.case_id, content=b"x",
            media_type="text/plain", extracted_text=text,
        )

    suggest("Full name: One")
    run = runs.list_for_case(case.case_id)[0]
    service.save_answers(
        lambda: filler_actor(), case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
        expected_revision=run.revision, values={"full-name": "One"},
    )
    suggest("Full name: Two")
    assert runs.list_for_case(case.case_id)[0].answers[0].value == "One"


def test_a_workflow_upload_is_authorized_before_the_body_is_read():
    reader = AsyncMock(return_value=b"Reference: ABC123\n")
    with patch("app.main._read_bounded_body", reader):
        app = enabled_app()
    director, maya, sophia = (login(app, item) for item in ("olivia-koh", "maya-lim", "sophia-ng"))
    url = new_case_workflow(director)
    run = maya.post(f"{url}/new-cases", json=COMPANY).json()["run"]
    upload = f"{url}/runs/{run['run_id']}/documents"
    headers = {"Content-Type": "text/plain", "X-Document-Name": "profile.txt"}
    body = b"Reference: ABC123\n"
    assert login(app, "hr-admin").post(upload, content=body, headers=headers).status_code == 403
    assert sophia.post(upload, content=body, headers=headers).status_code == 404
    assert director.post(upload, content=body, headers=headers).status_code == 403
    reader.assert_not_awaited()
    assert maya.post(upload, content=body, headers=headers).status_code == 200
    reader.assert_awaited_once()


def test_a_document_after_sending_leaves_the_onboarding_stage_alone():
    case = FakeCase()
    runs = InMemoryWorkflowRunRepository()
    service = service_with_stage(case, runs)
    service._case_is_sent = lambda _case_id: True
    service.suggest_from_document(
        case_id=case.case_id, document_id=case.case_id, content=b"x",
        media_type="text/plain", extracted_text="Full name: After Send",
    )
    assert runs.list_for_case(case.case_id) == []


def activate_stage(service, stage):
    director = director_actor()
    baseline = service.get_workflow(director, ONBOARDING_WORKFLOW_ID)
    service.save_draft(
        lambda: director, ONBOARDING_WORKFLOW_ID, expected_revision=baseline.revision,
        stages=(WorkflowStage.model_validate(stage),),
    )
    publish_draft(service._definitions, ONBOARDING_WORKFLOW_ID, now=service._clock())  # noqa: SLF001


def test_a_screen_two_versions_behind_is_still_refused():
    case = FakeCase()
    service = service_with_stage(case)
    filler = filler_actor()
    run = service.case_view(case).onboarding
    service.save_answers(
        lambda: filler, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
        expected_revision=0, values={"full-name": "Sample", "birth-date": "1980-01-15"},
    )
    activate_stage(service, {**STAGE, "name": "Second version"})
    second = service.case_view(case).onboarding
    activate_stage(service, {**STAGE, "name": "Third version"})
    third = service.case_view(case).onboarding
    assert third.revision != second.revision
    with pytest.raises(WorkflowConflictError):
        service.confirm_stage(
            lambda: filler, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
            expected_revision=second.revision,
        )
    confirmed = service.confirm_stage(
        lambda: filler, case_id=case.case_id, run_id=run.run_id, stage_id="signatory",
        expected_revision=third.revision,
    )
    assert confirmed.workflow_version == 3
    assert service.send_hold_code(case.case_id) is None


def test_a_screen_on_an_old_version_of_an_unsaved_stage_is_refused():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    activate_onboarding(director)
    case_id = new_case(maya)
    stale = onboarding_run(maya, case_id)
    assert stale["revision"] == 0

    relabelled = {**STAGE, "fields": [{**STAGE["fields"][0], "label": "Sanctions declaration"}]}
    activate_onboarding(director, (relabelled,))
    refused = maya.put(
        case_url(case_id, stale, "signatory", "answers"),
        json={"expected_revision": stale["revision"], "values": {"full-name": "Old answer"}},
    )
    assert refused.status_code == 409

    current = onboarding_run(maya, case_id)
    assert current["stages"][0]["fields"][0]["label"] == "Sanctions declaration"
    saved = maya.put(
        case_url(case_id, current, "signatory", "answers"),
        json={"expected_revision": current["revision"], "values": {"full-name": "New answer"}},
    )
    assert saved.status_code == 200, saved.json()
    assert saved.json()["workflow_version"] == 2


def test_a_stale_writer_cannot_overwrite_or_resurrect_a_run():
    case = FakeCase()
    runs = InMemoryWorkflowRunRepository()
    service = service_with_stage(case, runs)
    run = service.case_view(case).onboarding
    saved = service._persist(run, confirmations=())
    service._persist(saved, confirmations=())
    with pytest.raises(WorkflowConflictError):
        service._persist(saved, confirmations=())
    latest = runs.list_for_case(case.case_id)[0]
    runs.delete_for_case(case.case_id)
    with pytest.raises(WorkflowConflictError):
        service._persist(latest, confirmations=())
    assert runs.list_for_case(case.case_id) == []


def test_a_failed_restore_does_not_hide_why_deletion_failed():
    def failing_restore():
        raise PersistenceUnavailableError

    _restore(failing_restore, FakeCase().case_id)


def test_labels_with_special_characters_and_control_breaks():
    assert find_labelled_value(["Straße: Main"], "Straße").value == "Main"
    assert find_labelled_value(["Name: a\x0bb"], "Name") is None


def test_a_long_hostile_line_is_read_quickly():
    from time import perf_counter

    started = perf_counter()
    find_labelled_value([" " * 60_000 + "\n" + "Full name" * 6_000], "Full name")
    assert perf_counter() - started < 0.5


def test_onboarding_cannot_be_started_as_a_run():
    app = enabled_app()
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    activate_onboarding(director)
    response = maya.post(
        f"/api/workflows/{ONBOARDING_WORKFLOW_ID}/runs", json={"case_id": new_case(maya)}
    )
    assert response.json()["detail"]["code"] == "WORKFLOW_NOT_STARTABLE"


def test_a_run_cannot_start_on_an_absent_or_other_team_case():
    app = enabled_app()
    director, maya, sophia = (login(app, item) for item in ("olivia-koh", "maya-lim", "sophia-ng"))
    created = director.post(
        "/api/workflows", json={"name": "R", "use_case": "Case refresh", "country": "Singapore"}
    ).json()
    assert sophia.post(
        f"/api/workflows/{created['workflow_id']}/runs", json={"case_id": new_case(maya)}
    ).status_code == 404
    response = maya.post(
        f"/api/workflows/{created['workflow_id']}/runs",
        json={"case_id": "00000000-0000-4000-8000-000000000000"},
    )
    assert response.status_code == 404


def test_labelled_values_need_one_unambiguous_match():
    assert find_labelled_value(["Full name: Sample"], "full name").value == "Sample"
    second_page = find_labelled_value(["nothing", "Full name - Sample"], "Full name")
    assert second_page.page_number == 2
    assert find_labelled_value(["Full name: A\nFull name: B"], "Full name") is None
    assert find_labelled_value(["Unrelated text"], "Full name") is None
    assert find_labelled_value(["A.B: x"], "A?B") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("15 Jan 1980", "1980-01-15"), ("15/01/1980", "1980-01-15"), ("1980-01-15", "1980-01-15"),
     ("sometime", None)],
)
def test_dates_normalize_or_are_left_for_a_person(raw, expected):
    assert normalize_date(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1,000,000", "1000000"), ("1000.50", "1000.50"), ("-25", "-25"), ("1.000", None),
     ("S$ 1,000", None), ("25%", None), ("1,00", None), ("about 5", None)],
)
def test_only_plain_numbers_are_suggested(raw, expected):
    assert normalize_number(raw) == expected


def test_options_must_match_exactly_apart_from_case():
    assert match_option(" yes ", ("Yes", "No")) == "Yes"
    assert match_option("Director", ("Director", "Other")) == "Director"
    assert match_option("Directors", ("Director", "Other")) is None


def test_each_field_type_is_suggested_or_left_empty():
    from app.domain.workflows import WorkflowField

    def field(kind, options=()):
        return WorkflowField(field_id="f", label="F", kind=kind, options=options, autofill=True)

    assert _suggested_value(field("NUMBER"), "1,000") == "1000"
    assert _suggested_value(field("NUMBER"), "S$ 1,000") is None
    assert _suggested_value(field("YES_NO"), "no") == "No"
    assert _suggested_value(field("YES_NO"), "maybe") is None
    assert _suggested_value(field("CHOICE", ("A", "B")), "b") == "B"
    assert _suggested_value(field("CHOICE", ("A", "B")), "C") is None


class Cases:
    def __init__(self, case):
        self.case = case

    def get_case(self, case_id):
        return self.case

    def case_lock(self, case_id):
        from threading import RLock

        return RLock()


class FakeCase:
    def __init__(self):
        from uuid import uuid4

        self.case_id = uuid4()
        self.created_at = datetime(2030, 1, 1, tzinfo=UTC)


class FailingRuns(InMemoryWorkflowRunRepository):
    def list_for_case(self, case_id):
        raise PersistenceUnavailableError


def actor_for(user_id):
    profile = next(item for item in SYNTHETIC_USER_PROFILES if item.user_id == user_id)
    return AuthenticatedActor.model_construct(profile=profile)


def director_actor():
    return actor_for("olivia-koh")


def filler_actor():
    return actor_for("maya-lim")


def service_with_stage(case, runs=None):
    actor = director_actor()
    service = WorkflowManagementService(
        definitions=InMemoryWorkflowDefinitionRepository(),
        runs=runs or InMemoryWorkflowRunRepository(),
        cases=Cases(case),
        clock=lambda: datetime(2029, 1, 1, tzinfo=UTC),
    )
    service.provision_onboarding()
    baseline = service.get_workflow(actor, ONBOARDING_WORKFLOW_ID)
    service.save_draft(
        lambda: actor,
        ONBOARDING_WORKFLOW_ID,
        expected_revision=baseline.revision,
        stages=(WorkflowStage.model_validate(STAGE),),
    )
    publish_draft(service._definitions, ONBOARDING_WORKFLOW_ID, now=service._clock())  # noqa: SLF001
    return service


def test_the_send_check_refuses_incomplete_stages_and_fails_closed():
    case = FakeCase()
    assert service_with_stage(case).send_hold_code(case.case_id) == HOLD_INCOMPLETE
    assert (
        service_with_stage(case, FailingRuns()).send_hold_code(case.case_id) == HOLD_UNAVAILABLE
    )


def test_a_new_stage_holds_an_open_case_older_than_the_stage():
    case = FakeCase()
    case.created_at = datetime(2028, 1, 1, tzinfo=UTC)
    assert service_with_stage(case).send_hold_code(case.case_id) == HOLD_INCOMPLETE


def test_a_sent_case_never_gains_a_stage():
    case = FakeCase()
    case.created_at = datetime(2028, 1, 1, tzinfo=UTC)
    service = service_with_stage(case)
    service._case_is_sent = lambda _case_id: True
    assert service.case_view(case).onboarding is None
    assert service.send_hold_code(case.case_id) is None


def test_suggestions_never_overwrite_a_person_and_an_upload_never_fails():
    case = FakeCase()
    runs = InMemoryWorkflowRunRepository()
    service = service_with_stage(case, runs)
    document_id = case.case_id

    def suggest(text):
        service.suggest_from_document(
            case_id=case.case_id, document_id=document_id, content=b"x",
            media_type="text/plain", extracted_text=text,
        )

    suggest("Full name: From Document")
    (run,) = runs.list_for_case(case.case_id)
    assert run.answers[0].value == "From Document"
    assert run.answers[0].source == "DOCUMENT"
    assert run.confirmations == ()
    assert service.send_hold_code(case.case_id) == HOLD_INCOMPLETE

    manual = run.answers[0].model_copy(update={"source": "MANUAL", "value": "Typed"})
    runs.update(
        run.model_copy(update={"answers": (manual,), "revision": run.revision + 1}),
        expected_revision=run.revision,
    )
    suggest("Full name: Second Document")
    assert runs.list_for_case(case.case_id)[0].answers[0].value == "Typed"

    failing = service_with_stage(case, FailingRuns())
    failing.suggest_from_document(
        case_id=case.case_id, document_id=document_id, content=b"x",
        media_type="text/plain", extracted_text="Full name: X",
    )


def test_deleting_a_case_deletes_its_collected_answers():
    storage = WorkflowPersistence(
        definitions=InMemoryWorkflowDefinitionRepository(),
        runs=InMemoryWorkflowRunRepository(),
        close=lambda: None,
    )
    app = enabled_app(storage)
    director, maya = login(app, "olivia-koh"), login(app, "maya-lim")
    activate_onboarding(director)
    case_id = new_case(maya)
    run = onboarding_run(maya, case_id)
    assert maya.put(
        case_url(case_id, run, "signatory", "answers"),
        json={"expected_revision": 0, "values": {"full-name": "Sample"}},
    ).status_code == 200
    assert len(storage.runs.list_for_case(UUID(case_id))) == 1
    assert director.delete(f"/api/clm/zero-touch/cases/{case_id}").status_code in {200, 204}
    assert storage.runs.list_for_case(UUID(case_id)) == []


def test_a_really_onboarded_company_loads_its_case_data_into_a_workflow():
    company = SHARE_COMPANIES[0]
    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    target = RecordingTarget(company.name, company.uen)
    keys = {
        "LEGAL_NAME": "TEXT", "REGISTRATION_ID": "TEXT", "REGISTERED_ADDRESS": "TEXT",
        "COUNTRY": "TEXT", "DOCUMENT_NAME": "TEXT", "DOCUMENT_REVIEWED": "YES_NO",
        "DISCREPANCIES_FOUND": "YES_NO", "OWNER_NAME": "TEXT", "EXISTING_CUSTOMER": "YES_NO",
        "GOLDTIER_ID": "TEXT", "KYC_CUSTOMER_TYPE": "TEXT", "CLIENT_SEGMENT": "TEXT",
        "BOOKING_ENTITY": "TEXT", "REVIEWED_BY": "TEXT", "REVIEW_DATE": "DATE",
        "READY_TO_SEND": "YES_NO",
    }
    stage = {"stage_id": "all", "name": "Everything", "fields": [
        {"field_id": key.lower().replace("_", "-"), "label": key, "kind": kind,
         "required": False, "case_data_key": key}
        for key, kind in keys.items()
    ]}
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        capturing_workflow_store() as workflow_store,
        TestClient(
            create_app(settings, acra_connector=NoAcra(), goldtier_transport=target)
        ) as client,
    ):
        register_app_store(client.app, workflow_store)
        director = login(client.app, "olivia-koh")
        current = prepare(client, company)
        assert confirm(client, current)["status"] == "COMPLETED"
        created = director.post(
            "/api/workflows", json={"name": "Refresh", "use_case": "R", "country": "SG"}
        ).json()
        url = f"/api/workflows/{created['workflow_id']}"
        director.put(
            f"{url}/draft", json={"expected_revision": created["revision"], "stages": [stage]}
        ).json()
        publish_draft(store_for(director).definitions, url.rsplit("/", 1)[1])
        started = client.post(f"{url}/runs", json={"case_id": current["case"]["case_id"]})
        assert started.status_code == 201, started.json()
        fields = {item["label"]: item for item in started.json()["stages"][0]["fields"]}

    assert fields["LEGAL_NAME"]["value"] == company.name
    assert fields["REGISTRATION_ID"]["value"] == company.uen
    assert fields["LEGAL_NAME"]["source"] == "CASE"
    assert fields["READY_TO_SEND"]["value"] == "Yes"
    assert fields["DOCUMENT_REVIEWED"]["value"] == "Yes"
    assert fields["GOLDTIER_ID"]["value"]
    assert fields["KYC_CUSTOMER_TYPE"]["value"]
    assert fields["CLIENT_SEGMENT"]["value"]
    assert fields["OWNER_NAME"]["value"]
    empty = [label for label, item in fields.items() if item["value"] is None]
    assert empty == []


def test_the_send_is_held_until_the_stage_is_confirmed_through_the_real_flow():
    company = SHARE_COMPANIES[0]
    settings = sandbox_settings(workflow_manager_enabled=True)
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    target = RecordingTarget(company.name, company.uen)
    label = next(iter(company.fields))
    stage = {
        **STAGE,
        "fields": [
            {"field_id": "from-doc", "label": "From document", "kind": "TEXT", "required": True,
             "autofill": True, "document_label": label},
        ],
    }
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        capturing_workflow_store() as workflow_store,
        TestClient(
            create_app(settings, acra_connector=NoAcra(), goldtier_transport=target)
        ) as client,
    ):
        register_app_store(client.app, workflow_store)
        director = login(client.app, "olivia-koh")
        activate_onboarding(director, (stage,))
        current = prepare(client, company)
        case_id = current["case"]["case_id"]

        run = onboarding_run(client, case_id)
        field = run["stages"][0]["fields"][0]
        assert field["value"] == company.fields[label]
        assert field["source"] == "DOCUMENT"

        before = list(target.calls)
        held = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json={
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
            },
        )
        assert held.status_code >= 400
        assert held.json()["detail"]["code"] == HOLD_INCOMPLETE
        assert target.calls == before

        confirmed = client.post(
            case_url(case_id, run, "signatory", "confirm"),
            json={"expected_revision": run["revision"]},
        )
        assert confirmed.status_code == 200, confirmed.json()
        final = confirm(client, current)
        assert final["status"] == "COMPLETED"
