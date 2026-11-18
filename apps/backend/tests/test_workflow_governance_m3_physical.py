"""ADR-018 M3 owner scenarios on a physical MongoDB (opt-in; integrator-run).

The memory twins are ``test_workflow_governance_m3``, ``test_workflow_applicability``,
``test_workflow_applicability_routes`` and ``test_workflow_run_basis_write_once``. Here the
same owner scenarios run against Mongo persistence:

1. an LLP case receives its approved conditional stage;
2. a Company case does not receive an LLP-only stage;
3. unknown or conflicting legal forms keep every obligation (UNVERIFIED applies all);
4. recovery cannot weaken obligations (fallback refusals, broadest restore/reset, RR-8,
   write-once frozen basis);
5. conditional rules cannot modify the mandatory stages (registry anchor, RR-8, the
   UBO/compliance nodes stay in every case's processing plan).

Runs only when ``PHASE12_MONGO_URI`` is set. Every test uses a newly generated, allowlisted
disposable database (``scripts.mongo_test_safety``), never ``clm_poc``; the governance-store
tests run as an authenticated readWrite-only user (owner decision D-11). Mock ACRA only (an
in-process connector with a chosen synthetic entity type), Mock GoldTier, no network. The URI
is never printed.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pymongo import MongoClient
from test_phase16_registry_cache import CountingAcraConnector
from test_synthetic_company_pack import settings
from test_synthetic_company_pack_real_mongo import MONGO_URI, pytestmark  # noqa: F401
from test_synthetic_company_pack_real_mongo import database as disposable_database
from test_workflow_applicability import LLP_TEXT, OPQ_SHAPED
from test_workflow_applicability_routes import STAGES
from test_workflow_governance_m3 import (
    ALL_STAGE,
    LLP_STAGE,
    WIDER_LLP_STAGE,
    World,
    field,
    messages,
    stage,
)
from test_workflow_governance_persistence_real_mongo import store as governed_store
from test_workflow_governance_recovery import HR, snapshot
from test_workflow_manager import governed_publish, login
from test_workflow_run_basis_write_once import _basis, _next, _run

from app.api_workflow_governance_models import SubmitProposalRequest, WithdrawProposalRequest
from app.connectors.acra import AcraCompanyPayload
from app.domain.workflow_governance import (
    CONDITIONAL_APPLICABILITY_ENABLED_ENV,
    CONDITIONAL_BEFORE_REGISTRY_ISSUE,
    ProposalKind,
    RatchetRule,
)
from app.domain.workflows import (
    ONBOARDING_USE_CASE,
    ONBOARDING_WORKFLOW_ID,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowVersion,
)
from app.main import create_app
from app.persistence.errors import PersistenceConflictError
from app.persistence.mongo_workflow_store import (
    MongoWorkflowDefinitionRepository,
    MongoWorkflowRunRepository,
    MongoWorkflowStore,
)
from app.persistence.p2_1_migration import apply_p2_1_migration, plan_p2_1_migration
from app.services.workflow_governance import WorkflowGovernanceError
from app.services.workflow_ratchet import seed_baseline

database = disposable_database
store = governed_store

COMPANY_UEN = "202400001A"  # Mock ACRA sample: PRIVATE_COMPANY_LIMITED_BY_SHARES
UNKNOWN_UEN = "209900001Z"  # not in the Mock ACRA dataset: no entity, no binding
ALL_IDS = ["registry-notes", "llp-partners", "company-secretary"]
# Mandatory product nodes that no workflow condition can remove (ADR-018 §2.1).
MANDATORY_NODES = {"ACRA_REGISTRY", "DOCUMENT_IDP", "OWNERSHIP_UBO", "ADVISORY"}


def _now() -> datetime:
    return datetime.now(UTC)


class SyntheticFormAcra(CountingAcraConnector):
    """The in-process Mock ACRA with a chosen synthetic source entity type (real clock)."""

    def __init__(self, entity_type: str) -> None:
        super().__init__(_now)
        self.entity_type = entity_type

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        payload = super().fetch_company(uen)
        if payload is None:
            return None
        return payload.model_copy(update={"entity_type": self.entity_type})


def physical(name: str) -> Any:
    return settings(
        acra_connector_mode="mock",
        clm_persistence_mode="mongo",
        mongo_uri=SecretStr(MONGO_URI),
        mongo_database=name,
        workflow_manager_enabled=True,
    )


@contextmanager
def application(name: str, connector: Any = None) -> Iterator[TestClient]:
    with TestClient(create_app(physical(name), acra_connector=connector)) as client:
        yield client


def new_case(client: TestClient, uen: str) -> str:
    created = login(client.app, "maya-lim").post("/api/clm/zero-touch/cases", json={"uen": uen})
    assert created.status_code == 201, created.text
    return created.json()["case"]["case_id"]


def onboarding_run(client: TestClient, case_id: str) -> dict[str, Any]:
    response = login(client.app, "maya-lim").get(f"/api/clm/zero-touch/cases/{case_id}/workflows")
    assert response.status_code == 200, response.text
    return response.json()["onboarding"]


def stage_ids(run: dict[str, Any]) -> list[str]:
    return [item["stage_id"] for item in run["stages"]]


def plan_nodes(client: TestClient, case_id: str) -> set[str]:
    summary = login(client.app, "maya-lim").get(f"/api/clm/zero-touch/cases/{case_id}")
    assert summary.status_code == 200, summary.text
    return {node["node_id"] for node in summary.json()["processing_pipeline"]}


def stored_runs(name: str, case_id: str) -> list[dict[str, Any]]:
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        collection = client[name][physical(name).mongo_workflow_runs_collection]
        return list(collection.find({"case_id": case_id}))
    finally:
        client.close()


def publish_conditional_onboarding(client: TestClient) -> None:
    active = governed_publish(login(client.app, "olivia-koh"), ONBOARDING_WORKFLOW_ID, STAGES)
    assert active["active_version"] == 1, active
    assert active["governance"]["version_provenance"][-1]["origin"] == "GOVERNED_APPROVAL"


@pytest.fixture
def enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CONDITIONAL_APPLICABILITY_ENABLED_ENV, "true")


# --- Scenarios 1, 2 and 5: each case receives exactly its applicable stages --------------------


def test_physical_m3_llp_case_receives_its_approved_conditional_stage(database, enabled):
    with application(database, SyntheticFormAcra(LLP_TEXT)) as client:
        publish_conditional_onboarding(client)
        case_id = new_case(client, COMPANY_UEN)
        run = onboarding_run(client, case_id)
        assert stage_ids(run) == ["registry-notes", "llp-partners"]
        applicability = run["applicability"]
        assert applicability["status"] == "REGISTRY_BOUND" and applicability["frozen"]
        assert applicability["legal_form"] == "LLP"
        assert applicability["source_environment"] == "MOCK"  # never presented as Live
        assert plan_nodes(client, case_id) >= MANDATORY_NODES
    stored = stored_runs(database, case_id)
    assert len(stored) == 1
    assert stored[0]["payload"]["applicability_basis"]["frozen"] is True
    assert stored[0]["payload"]["applicability_basis"]["legal_form"] == "LLP"
    # A restart reads the frozen basis and the resolved copy back from Mongo unchanged.
    with application(database, SyntheticFormAcra(LLP_TEXT)) as client:
        again = onboarding_run(client, case_id)
        assert stage_ids(again) == ["registry-notes", "llp-partners"]
        assert again["applicability"] == applicability


def test_physical_m3_company_case_does_not_receive_the_llp_only_stage(database, enabled):
    # The unmodified Mock ACRA sample: 202400001A is a private company limited by shares.
    with application(database) as client:
        publish_conditional_onboarding(client)
        case_id = new_case(client, COMPANY_UEN)
        run = onboarding_run(client, case_id)
        assert stage_ids(run) == ["registry-notes", "company-secretary"]
        assert "llp-partners" not in stage_ids(run)
        assert run["applicability"]["legal_form"] == "COMPANY"
        assert run["applicability"]["status"] == "REGISTRY_BOUND"
        assert plan_nodes(client, case_id) >= MANDATORY_NODES
    with application(database) as client:
        assert stage_ids(onboarding_run(client, case_id)) == ["registry-notes", "company-secretary"]


# --- Scenario 3: unknown or conflicting legal forms keep every obligation ----------------------


def test_physical_m3_a_conflicting_decoder_result_applies_every_condition(database, enabled):
    # An OPQ-shaped source value ("Limited Liability Partnership - LLP") decodes to OTHER.
    with application(database, SyntheticFormAcra(OPQ_SHAPED)) as client:
        publish_conditional_onboarding(client)
        case_id = new_case(client, COMPANY_UEN)
        run = onboarding_run(client, case_id)
        assert stage_ids(run) == ALL_IDS
        applicability = run["applicability"]
        assert applicability["status"] == "UNVERIFIED" and applicability["frozen"]
        assert applicability["reason"] == "OTHER_FORM"
        assert applicability["legal_form"] is None
        assert applicability["effective_legal_form"] is None
        assert plan_nodes(client, case_id) >= MANDATORY_NODES
    with application(database, SyntheticFormAcra(OPQ_SHAPED)) as client:
        assert stage_ids(onboarding_run(client, case_id)) == ALL_IDS


def test_physical_m3_an_unknown_entity_and_an_unbound_case_apply_every_condition(database, enabled):
    with application(database) as client:
        # A case bound before any conditional content exists is never frozen: UNVERIFIED.
        before = new_case(client, COMPANY_UEN)
        publish_conditional_onboarding(client)
        unknown = new_case(client, UNKNOWN_UEN)  # no registry entity, so no binding
        for case_id in (before, unknown):
            run = onboarding_run(client, case_id)
            assert stage_ids(run) == ALL_IDS
            assert run.get("applicability") is None  # never frozen: every condition applies
            assert plan_nodes(client, case_id) >= MANDATORY_NODES


# --- Scenario 4: recovery cannot weaken existing obligations -----------------------------------


def legacy_on_mongo(store: MongoWorkflowStore, *versions: tuple[WorkflowStage, ...]) -> World:
    """A pre-governance onboarding history migrated by the P2-1 tool on Mongo."""

    repository = MongoWorkflowDefinitionRepository(store)
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    repository.create(
        WorkflowDefinition(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            name="Corporate onboarding",
            use_case=ONBOARDING_USE_CASE,
            country="Singapore",
            versions=tuple(
                WorkflowVersion(version=n, stages=s, activated_at=moment, activated_by="olivia-koh")
                for n, s in enumerate(versions, start=1)
            ),
            created_at=moment,
            updated_at=moment,
        )
    )
    plan = plan_p2_1_migration(
        store.definitions.find({}), seed_baseline=seed_baseline, now=moment, cold=store.cold
    )
    assert apply_p2_1_migration(plan, store.definitions, store.cold, now=moment) == 1
    return World(repository)


def governed_on_mongo(store: MongoWorkflowStore) -> World:
    return World(MongoWorkflowDefinitionRepository(store))


def test_physical_m3_fallback_refuses_broadening_applicability(store):
    world = legacy_on_mongo(
        store, (ALL_STAGE, stage("partners", [field("partner-count")])), (ALL_STAGE, LLP_STAGE)
    )
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback(target="VERSION", target_version=1)
    assert refused.value.code == "WORKFLOW_PROPOSAL_INVALID"
    assert snapshot(world) == before  # nothing written


def test_physical_m3_fallback_refuses_adding_a_conditional_obligation(store):
    world = legacy_on_mongo(store, (ALL_STAGE, LLP_STAGE), (ALL_STAGE,))
    before = snapshot(world)
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.fallback(target="VERSION", target_version=1)
    assert {item.stage_id for item in refused.value.issues} == {"partners"}
    assert snapshot(world) == before


def test_physical_m3_restore_reset_and_fallback_keep_the_broadest_applicability(store):
    world = governed_on_mongo(store)
    world.publish((ALL_STAGE, LLP_STAGE))
    world.publish((ALL_STAGE, WIDER_LLP_STAGE))  # a governed broadening publishes
    restore = world.create(kind=ProposalKind.RESTORE_VERSION, restore_target_version=1)
    partners = next(item for item in restore.stages if item.stage_id == "partners")
    assert partners.applies_to == ("COMPANY", "LLP")  # never the narrower v1 set
    world.governance.withdraw_proposal(
        lambda: HR,
        ONBOARDING_WORKFLOW_ID,
        restore.proposal_id,
        WithdrawProposalRequest(
            expected_workflow_revision=world.revision(),
            expected_proposal_revision=restore.revision,
        ),
    )
    reset = world.create(kind=ProposalKind.RESET_TO_DEFAULT)
    assert next(s for s in reset.stages if s.stage_id == "partners").applies_to == (
        "COMPANY",
        "LLP",
    )
    world.governance.withdraw_proposal(
        lambda: HR,
        ONBOARDING_WORKFLOW_ID,
        reset.proposal_id,
        WithdrawProposalRequest(
            expected_workflow_revision=world.revision(),
            expected_proposal_revision=reset.revision,
        ),
    )
    baseline = world.state().governance.required_baseline.model_dump_json()
    # A Director fallback to the narrower v1 publishes the safe target: still the broadest.
    assert world.fallback(target="VERSION", target_version=1).published_version == 3
    published = world.state().definition.versions[-1]
    assert next(s for s in published.stages if s.stage_id == "partners").applies_to == (
        "COMPANY",
        "LLP",
    )
    assert world.state().governance.required_baseline.model_dump_json() == baseline


def test_physical_m3_rr8_narrowing_is_refused_at_submit(store):
    world = governed_on_mongo(store)
    world.publish((ALL_STAGE,))
    narrowed = stage("signatory", [field("full-name")], applies_to=("LLP",))
    draft = world.create(stages=(narrowed,))
    report = world.report(draft, draft.stages)
    assert RatchetRule.RR_8 in {item.rule for item in report.issues}
    before = world.state().definition.versions
    with pytest.raises(WorkflowGovernanceError) as refused:
        world.governance.submit_proposal(
            lambda: HR,
            ONBOARDING_WORKFLOW_ID,
            draft.proposal_id,
            SubmitProposalRequest(
                expected_workflow_revision=world.revision(),
                expected_proposal_revision=draft.revision,
                content_hash=report.content_hash,
            ),
        )
    assert refused.value.code == "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED"
    assert refused.value.rule == RatchetRule.RR_8
    assert world.state().definition.versions == before


def test_physical_m3_a_frozen_basis_is_write_once_on_mongo(store):
    runs = MongoWorkflowRunRepository(store)
    run = runs.create(_run())
    frozen = runs.update(
        _next(run, applicability_basis=_basis(frozen=True)), expected_revision=run.revision
    )
    for rewrite in (None, _basis(frozen=False)):
        with pytest.raises(PersistenceConflictError):
            runs.update(
                _next(frozen, applicability_basis=rewrite), expected_revision=frozen.revision
            )
    stored = runs.get(run.run_id)
    assert stored is not None and stored.applicability_basis == _basis(frozen=True)


# --- Scenario 5: conditional rules cannot modify mandatory stages ------------------------------


def test_physical_m3_conditions_cannot_precede_the_registry_or_narrow_a_required_stage(store):
    world = governed_on_mongo(store)
    world.publish((ALL_STAGE,))  # an unconditional required stage after DOCUMENT_IDP
    early = stage("early", [field("x")], after="GOLDTIER_SEARCH", applies_to=("LLP",))
    unanchored = stage("loose", [field("y")], after=None, applies_to=("LLP",))
    draft = world.create(stages=(ALL_STAGE,))
    for content in ((ALL_STAGE, early), (ALL_STAGE, unanchored)):
        report = world.report(draft, content)
        assert not report.valid
        assert CONDITIONAL_BEFORE_REGISTRY_ISSUE in messages(report)
    conditional = stage("signatory", [field("full-name")], applies_to=("COMPANY", "LLP"))
    report = world.report(draft, (conditional,))
    assert not report.valid and RatchetRule.RR_8 in {item.rule for item in report.issues}
    at_registry = stage("registry", [field("z")], after="ACRA_REGISTRY", applies_to=("LLP",))
    assert world.report(draft, (ALL_STAGE, at_registry)).valid  # adding is still allowed
