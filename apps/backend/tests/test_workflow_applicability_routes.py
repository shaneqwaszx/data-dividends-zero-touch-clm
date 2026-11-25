"""ADR-018 M3-D over HTTP and end to end (memory mode, Mock ACRA, recording GoldTier):
the applicability escalation route and its RBAC (CT-34), the run view, the code-only case
event and the event-count token (CT-38), and the conditional send (CT-36).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from phase13_test_settings import ordinary_test_settings
from test_phase16_registry_cache import VALID_UEN, MutableClock, build_cached_service, identity
from test_workflow_applicability import COMPANY_TEXT, LLP_TEXT, TypedConnector
from test_workflow_manager import governed_publish, login
from workflow_publication_seed import capturing_workflow_store, register_app_store

from app.domain.access import TeamId
from app.domain.workflow_governance import (
    CASE_EVENT_APPLICABILITY_ESCALATED,
    CONDITIONAL_APPLICABILITY_ENABLED_ENV,
)
from app.domain.workflows import ONBOARDING_WORKFLOW_ID
from app.main import create_app

REASON = "The registry binding changed; apply every condition."
STAGES = [
    {
        "stage_id": "registry-notes",
        "name": "Registry notes",
        "after_node_id": "ACRA_REGISTRY",
        "fields": [{"field_id": "reference", "label": "Reference", "kind": "TEXT"}],
    },
    {
        "stage_id": "llp-partners",
        "name": "LLP partners",
        "after_node_id": "ACRA_REGISTRY",
        "applies_to": ["LLP"],
        "fields": [{"field_id": "partner-count", "label": "Partner count", "kind": "TEXT"}],
    },
    {
        "stage_id": "company-secretary",
        "name": "Company secretary",
        "after_node_id": "DOCUMENT_IDP",
        "applies_to": ["COMPANY"],
        "fields": [{"field_id": "secretary", "label": "Secretary", "kind": "TEXT"}],
    },
]


def application(monkeypatch: pytest.MonkeyPatch, entity_type: str) -> tuple[Any, Any, Any]:
    monkeypatch.setenv(CONDITIONAL_APPLICABILITY_ENABLED_ENV, "true")
    clock = MutableClock(datetime.now(UTC))
    service, _, _ = build_cached_service(clock, TypedConnector(clock, entity_type))
    with capturing_workflow_store() as store:
        app = create_app(
            ordinary_test_settings(workflow_manager_enabled=True), onboarding_service=service
        )
    register_app_store(app, store)
    director = login(app, "olivia-koh")
    governed_publish(director, ONBOARDING_WORKFLOW_ID, STAGES)
    case = service.create_staged_case(
        VALID_UEN, team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim"
    )
    return app, service, case


def onboarding_view(client: Any, case_id: Any) -> dict[str, Any]:
    response = client.get(f"/api/clm/zero-touch/cases/{case_id}/workflows")
    assert response.status_code == 200, response.json()
    return response.json()["onboarding"]


def escalate(client: Any, case_id: Any, run: dict[str, Any]) -> Any:
    return client.post(
        f"/api/clm/cases/{case_id}/workflow/applicability-escalation",
        json={"run_id": run["run_id"], "expected_revision": run["revision"], "reason": REASON},
    )


def test_the_run_view_shows_the_frozen_basis_and_the_escalation_is_audited(monkeypatch):
    app, service, case = application(monkeypatch, COMPANY_TEXT)
    maya = login(app, "maya-lim")
    run = onboarding_view(maya, case.case_id)
    applicability = run["applicability"]
    assert applicability["status"] == "REGISTRY_BOUND" and applicability["frozen"]
    assert applicability["legal_form"] == "COMPANY"
    assert applicability["source_environment"] == "MOCK"
    assert [item["stage_id"] for item in run["stages"]] == ["registry-notes", "company-secretary"]
    refused = escalate(maya, case.case_id, run)
    assert refused.status_code == 409
    assert refused.json()["detail"]["code"] == "WORKFLOW_APPLICABILITY_NOT_IN_CONFLICT"
    # A later binding change: the frozen basis conflicts (the send would hold).
    stored = service.get_case(case.case_id)
    service.case_repository.save(stored.model_copy(update={"registry_evidence_binding": None}))
    count = len(service.get_case(case.case_id).events)
    escalated = escalate(maya, case.case_id, run)
    assert escalated.status_code == 200, escalated.json()
    body = escalated.json()
    assert body["applicability"]["conflict"]["escalated"] is True
    assert body["applicability"]["effective_legal_form"] is None
    assert {item["stage_id"] for item in body["stages"]} == {
        "registry-notes",
        "llp-partners",
        "company-secretary",
    }
    current = service.get_case(case.case_id)
    assert len(current.events) == count + 1  # CT-38: the token moves
    event = current.events[-1]
    assert event.code == CASE_EVENT_APPLICABILITY_ESCALATED and event.stage == current.state
    with pytest.raises(ValueError):
        service.invalidate_target_dispatch_confirmation(
            case_id=case.case_id, expected_case_event_count=count
        )
    again = escalate(maya, case.case_id, onboarding_view(maya, case.case_id))
    assert again.status_code == 409  # an escalated run has no open conflict


@pytest.mark.parametrize(
    ("user_id", "expected"),
    [
        ("sophia-ng", 404),  # another team: a safe 404
        ("biz-ops", 404),
        ("support-user", 404),
        ("olivia-koh", 403),  # case access, but not a filler role
        ("ethan-tan", 200),
        ("maya-lim", 200),
    ],
)
def test_the_escalation_route_is_case_scoped_and_filler_only(monkeypatch, user_id, expected):
    app, service, case = application(monkeypatch, COMPANY_TEXT)
    run = onboarding_view(login(app, "maya-lim"), case.case_id)
    stored = service.get_case(case.case_id)
    service.case_repository.save(stored.model_copy(update={"registry_evidence_binding": None}))
    client = login(app, user_id)
    response = escalate(client, case.case_id, run)
    assert response.status_code == expected, response.json()
    if expected == 404:
        absent = escalate(client, "00000000-0000-4000-8000-000000000000", run)
        assert absent.status_code == 404 and absent.json() == response.json()


def test_an_unconditional_run_has_no_applicability_view(monkeypatch):
    monkeypatch.delenv(CONDITIONAL_APPLICABILITY_ENABLED_ENV, raising=False)
    clock = MutableClock(datetime.now(UTC))
    service, _, _ = build_cached_service(clock, TypedConnector(clock, COMPANY_TEXT))
    with capturing_workflow_store() as store:
        app = create_app(
            ordinary_test_settings(workflow_manager_enabled=True), onboarding_service=service
        )
    register_app_store(app, store)
    governed_publish(login(app, "olivia-koh"), ONBOARDING_WORKFLOW_ID, STAGES[:1])
    case = service.create_staged_case(
        VALID_UEN, team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim"
    )
    run = onboarding_view(login(app, "maya-lim"), case.case_id)
    assert "applicability" not in run


def test_the_gate_is_off_by_default_over_http(monkeypatch):
    monkeypatch.delenv(CONDITIONAL_APPLICABILITY_ENABLED_ENV, raising=False)
    with capturing_workflow_store() as store:
        app = create_app(ordinary_test_settings(workflow_manager_enabled=True))
    register_app_store(app, store)
    hr = login(app, "biz-ops")
    url = f"/api/workflows/{ONBOARDING_WORKFLOW_ID}"
    refused = hr.post(
        f"{url}/proposals",
        json={"expected_workflow_revision": hr.get(url).json()["revision"], "stages": STAGES},
    )
    assert refused.status_code == 422
    assert refused.json()["detail"]["code"] == "WORKFLOW_PROPOSAL_INVALID"


# --- CT-36: the conditional send end to end with recording GoldTier counts ------------------


def _zero_touch(entity_type: str) -> tuple[Any, Any, Any, Any]:
    from test_aws_goldtier_sandbox_readiness import UEN, ok, set_writes
    from test_goldtier_xpi_sandbox import PDF, FakeXpiTransport, _sandbox_zero_touch_system

    from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
    from app.domain.models import RegistryFreshnessPolicy
    from app.domain.workflows import (
        ONBOARDING_USE_CASE,
        WorkflowDefinition,
        WorkflowStage,
        WorkflowVersion,
    )
    from app.services.dispatch_fence import DispatchFence, FenceHealth
    from app.services.registry_acquisition import RegistryAcquisitionCoordinator
    from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository
    from app.services.workflow_management import WorkflowManagementService
    from app.services.workflow_repository import (
        InMemoryWorkflowDefinitionRepository,
        InMemoryWorkflowRunRepository,
    )

    transport = FakeXpiTransport([ok([])])
    zero, _, _ = _sandbox_zero_touch_system(transport)
    cases = zero._cases  # noqa: SLF001
    set_writes(cases, transport, allowed=True)
    clock = MutableClock(datetime.now(UTC))
    # A complete Mock binding (the cache coordinator), so the basis freezes at REGISTRY_FETCHED.
    cases._registry_router = RegistryProviderRouter(  # noqa: SLF001
        AcraRegistryProviderAdapter(
            TypedConnector(clock, entity_type), clock=clock, cache_identity=identity()
        )
    )
    cases._registry_acquisition_coordinator = RegistryAcquisitionCoordinator(  # noqa: SLF001
        InMemoryRegistrySnapshotRepository(), RegistryFreshnessPolicy(), clock=clock
    )
    moment = clock.value
    definitions = InMemoryWorkflowDefinitionRepository()
    definitions.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            versions=(
                WorkflowVersion(
                    version=1,
                    stages=tuple(WorkflowStage.model_validate(s) for s in STAGES[:2]),
                    activated_at=moment,
                    activated_by="olivia-koh",
                ),
            ),
            created_at=moment,
            updated_at=moment,
        )
    )
    workflows = WorkflowManagementService(
        definitions=definitions, runs=InMemoryWorkflowRunRepository(), cases=cases, clock=clock
    )
    cases.bind_registry_binding_hook(workflows.freeze_onboarding_basis)
    cases.bind_dispatch_fence(
        DispatchFence(
            ledger=cases.target_execution_repository,
            definitions=definitions,
            workflow_id=ONBOARDING_WORKFLOW_ID,
            hold=workflows.send_hold_code,
            health=lambda: FenceHealth(available=True),
            on_hold=lambda case_id, _code: cases.supersede_dispatch_confirmation(case_id),
        )
    )
    created = zero.create_case(UEN)
    record = zero.attach_document(
        case_id=created.case_id,
        display_name="sandbox-profile.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    return zero, transport, record, workflows


def _confirm_all(zero: Any, workflows: Any, case_id: Any, answers: dict[str, dict[str, str]]):
    from app.domain.access import AuthenticatedActor, Role, UserProfile

    rm = AuthenticatedActor.model_construct(
        profile=UserProfile(
            user_id="ethan-tan",
            display_name="Ethan Tan",
            role=Role.RELATIONSHIP_MANAGER,
            team_id="TEAM_A",
        )
    )
    for stage_id, values in answers.items():
        case = zero._cases.get_case(case_id)  # noqa: SLF001
        run = workflows.case_view(case).onboarding
        run = workflows.save_answers(
            lambda: rm,
            case_id=case_id,
            run_id=run.run_id,
            stage_id=stage_id,
            expected_revision=run.revision,
            values=values,
        )
        workflows.confirm_stage(
            lambda: rm,
            case_id=case_id,
            run_id=run.run_id,
            stage_id=stage_id,
            expected_revision=run.revision,
        )


def test_an_llp_binding_holds_the_send_until_its_llp_stage_is_confirmed():
    from test_aws_goldtier_sandbox_readiness import confirmation, full_path_transport, methods, ok

    zero, transport, record, workflows = _zero_touch(LLP_TEXT)
    run = workflows.case_view(zero._cases.get_case(record.case_id)).onboarding  # noqa: SLF001
    assert run.applicability_basis.legal_form == "LLP"
    assert [s.stage_id for s in run.stages] == ["registry-notes", "llp-partners"]
    _confirm_all(zero, workflows, record.case_id, {"registry-notes": {"reference": "R-1"}})
    transport.responses.extend([ok([]), *full_path_transport().responses])
    held = zero.confirm_target_dispatch(**confirmation(zero, record))
    assert held.status == "WAITING_FOR_REVIEW" and held.technical_failure is None
    assert methods(transport).count("POST") == 0  # nothing was written to GoldTier
    _confirm_all(zero, workflows, record.case_id, {"llp-partners": {"partner-count": "2"}})
    finished = zero.confirm_target_dispatch(**confirmation(zero, held))
    assert finished.status == "COMPLETED", [e.code for e in finished.events[-4:]]
    assert methods(transport).count("POST") == 3


def test_a_company_gets_no_llp_stage_and_is_not_held():
    from test_aws_goldtier_sandbox_readiness import confirmation, full_path_transport, methods, ok

    zero, transport, record, workflows = _zero_touch(COMPANY_TEXT)
    run = workflows.case_view(zero._cases.get_case(record.case_id)).onboarding  # noqa: SLF001
    assert [s.stage_id for s in run.stages] == ["registry-notes"]
    _confirm_all(zero, workflows, record.case_id, {"registry-notes": {"reference": "R-1"}})
    transport.responses.extend([ok([]), *full_path_transport().responses])
    finished = zero.confirm_target_dispatch(**confirmation(zero, record))
    assert finished.status == "COMPLETED", [e.code for e in finished.events[-4:]]
    assert methods(transport).count("POST") == 3
