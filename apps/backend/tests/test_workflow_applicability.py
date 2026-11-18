"""ADR-018 (M3-C) conditional applicability evaluation: CT-23, CT-24, CT-25, CT-32..CT-34,
CT-36..CT-38 and CT-40, memory mode only (no Mongo, no provider beyond the in-process Mock
ACRA). The legal form only ever comes from the case record through the single classifier.
"""

from __future__ import annotations

import threading
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from test_phase16_registry_cache import (
    VALID_UEN,
    CountingAcraConnector,
    MutableClock,
    build_cached_service,
)

from app.connectors.acra import AcraCompanyPayload
from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.domain.models import SourceEnvironment
from app.domain.registry_legal_form import ConditionalLegalForm
from app.domain.uen_route import route_uen
from app.domain.workflow_governance import (
    CASE_EVENT_APPLICABILITY_BASIS_CONFLICT,
    CASE_EVENT_APPLICABILITY_ESCALATED,
    HOLD_APPLICABILITY_BASIS_CONFLICT,
)
from app.domain.workflows import (
    ONBOARDING_USE_CASE,
    ONBOARDING_WORKFLOW_ID,
    ApplicabilityBasisReason,
    ApplicabilityBasisStatus,
    RunItemKey,
    WorkflowCaseSource,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStage,
    WorkflowVersion,
)
from app.mappers.acra import map_acra_company
from app.services import workflow_applicability as applicability
from app.services.dispatch_fence import HOLD_INCOMPLETE
from app.services.workflow_applicability import (
    BasisCheckStatus,
    basis_conflict_of,
    creation_basis,
    excluded_items,
    freeze_decision,
    observe_case_basis,
    resolve_stages,
    safe_observe,
)
from app.services.workflow_management import (
    BASIS_HOOK_CONFLICT_RECORDED,
    BASIS_HOOK_FROZEN,
    BASIS_HOOK_NONE,
    HOLD_UNAVAILABLE,
    WorkflowConflictError,
    WorkflowManagementService,
    WorkflowValidationError,
)
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
)

BACKEND = Path(__file__).resolve().parents[1]
LLP_TEXT = "LIMITED LIABILITY PARTNERSHIP"
COMPANY_TEXT = "PRIVATE_COMPANY_LIMITED_BY_SHARES"
OPQ_SHAPED = "Limited Liability Partnership - LLP"  # decodes to OTHER (A4: UNVERIFIED)
REASON = "Registry identity changed after the basis froze."


def stage(
    stage_id: str, after: str | None, fields: list[dict[str, Any]], **extra: Any
) -> WorkflowStage:
    return WorkflowStage.model_validate(
        {
            "stage_id": stage_id,
            "name": stage_id.title(),
            "after_node_id": after,
            "fields": fields,
            **extra,
        }
    )


def field(field_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "label": field_id.replace("-", " ").title(),
        "kind": "TEXT",
        **extra,
    }


REGISTRY_NOTES = stage("registry-notes", "ACRA_REGISTRY", [field("reference")])
LLP_ONLY = stage("llp-partners", "ACRA_REGISTRY", [field("partner-count")], applies_to=("LLP",))
SIGNATORY = stage(
    "signatory",
    "DOCUMENT_IDP",
    [
        field("full-name"),
        field(
            "company-secretary",
            applies_to=("COMPANY",),
            autofill=True,
            document_label="Company secretary",
        ),
    ],
)
LP_NOTICE = stage("lp-notice", "ADVISORY", [], applies_to=("LP",))  # authored with no fields
STAGES = (REGISTRY_NOTES, LLP_ONLY, SIGNATORY, LP_NOTICE)


def actor(user_id: str, role: Role, team: str | None = None) -> AuthenticatedActor:
    profile = UserProfile(user_id=user_id, display_name=user_id, role=role, team_id=team)
    return AuthenticatedActor.model_construct(profile=profile)


RM = actor("ethan-tan", Role.RELATIONSHIP_MANAGER, "TEAM_A")


class TypedConnector(CountingAcraConnector):
    """The in-process Mock ACRA with a chosen source entity type (synthetic)."""

    def __init__(self, clock: MutableClock, entity_type: str) -> None:
        super().__init__(clock)
        self.entity_type = entity_type

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        payload = super().fetch_company(uen)
        if payload is None:
            return None
        return payload.model_copy(update={"entity_type": self.entity_type})


class World:
    def __init__(
        self,
        entity_type: str = LLP_TEXT,
        *,
        stages: tuple[WorkflowStage, ...] = STAGES,
        hook: bool = True,
        dispatch_claim: bool = False,
    ) -> None:
        self.clock = MutableClock()
        self.service, _, _ = build_cached_service(
            self.clock, TypedConnector(self.clock, entity_type)
        )
        self.definitions = InMemoryWorkflowDefinitionRepository()
        moment = self.clock.value - timedelta(days=1)
        self.definitions.create(
            WorkflowDefinition(
                workflow_id=ONBOARDING_WORKFLOW_ID,
                name="Corporate onboarding",
                use_case=ONBOARDING_USE_CASE,
                country="Singapore",
                versions=(self.version(1, stages, moment),),
                created_at=moment,
                updated_at=moment,
            )
        )
        self.runs = InMemoryWorkflowRunRepository()
        self.sent: set[Any] = set()
        self.workflows = WorkflowManagementService(
            definitions=self.definitions,
            runs=self.runs,
            cases=self.service,
            case_is_sent=lambda case_id: case_id in self.sent,
            case_has_dispatch_claim=lambda _case_id: dispatch_claim,
            clock=self.clock,
        )
        if hook:
            self.service.bind_registry_binding_hook(self.workflows.freeze_onboarding_basis)

    @staticmethod
    def version(number: int, stages: tuple[WorkflowStage, ...], moment: Any) -> WorkflowVersion:
        return WorkflowVersion(
            version=number, stages=stages, activated_at=moment, activated_by="olivia-koh"
        )

    def publish(self, stages: tuple[WorkflowStage, ...]) -> None:
        """Test double for a governed publication (the governance service is M3-D's)."""

        current = self.definitions._items[ONBOARDING_WORKFLOW_ID]  # noqa: SLF001
        number = current.versions[-1].version + 1
        self.definitions._items[ONBOARDING_WORKFLOW_ID] = current.model_copy(  # noqa: SLF001
            update={
                "versions": (*current.versions, self.version(number, stages, self.clock.value)),
                "stored_active_version": number,
                "latest_version": number,
            }
        )

    def new_case(self) -> Any:
        return self.service.create_staged_case(VALID_UEN)

    def run(self, case_id: Any) -> WorkflowRun:
        case = self.service.get_case(case_id)
        view = self.workflows.case_view(case)
        assert view.onboarding is not None
        return view.onboarding

    def stored(self, case_id: Any) -> WorkflowRun | None:
        return next((r for r in self.runs.list_for_case(case_id) if r.is_onboarding), None)

    def answer(self, case_id: Any, stage_id: str, values: dict[str, str]) -> WorkflowRun:
        run = self.run(case_id)
        return self.workflows.save_answers(
            lambda: RM,
            case_id=case_id,
            run_id=run.run_id,
            stage_id=stage_id,
            expected_revision=run.revision,
            values=values,
        )

    def confirm(self, case_id: Any, stage_id: str) -> WorkflowRun:
        run = self.run(case_id)
        return self.workflows.confirm_stage(
            lambda: RM,
            case_id=case_id,
            run_id=run.run_id,
            stage_id=stage_id,
            expected_revision=run.revision,
        )

    def complete(self, case_id: Any, values: dict[str, dict[str, str]]) -> None:
        for stage_id, answers in values.items():
            if answers:
                self.answer(case_id, stage_id, answers)
            self.confirm(case_id, stage_id)

    def replace_case(self, case_id: Any, **changes: Any) -> Any:
        case = self.service.get_case(case_id)
        changed = case.model_copy(update=changes)
        self.service.case_repository.save(changed)
        return self.service.get_case(case_id)

    def escalate(self, case_id: Any) -> WorkflowRun:
        run = self.run(case_id)
        return self.workflows.escalate_applicability(
            lambda: RM,
            case_id=case_id,
            run_id=run.run_id,
            expected_revision=run.revision,
            reason=REASON,
        )


def ids(run: WorkflowRun) -> dict[str, tuple[str, ...]]:
    return {item.stage_id: tuple(f.field_id for f in item.fields) for item in run.stages}


def bound_case(entity_type: str = LLP_TEXT) -> Any:
    world = World(entity_type, hook=False)
    return world.new_case()


def with_party_type(case: Any, party_type: str | None) -> Any:
    return case.model_copy(
        update={"entity": case.entity.model_copy(update={"party_type": party_type})}
    )


# --- CT-23: evaluation --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("party_type", "expected"),
    [
        ("PRIVATE LIMITED COMPANY", ConditionalLegalForm.COMPANY),
        ("SOLE PROPRIETORSHIP", ConditionalLegalForm.BUSINESS_PARTNERSHIP),
        (LLP_TEXT, ConditionalLegalForm.LLP),
        ("LIMITED PARTNERSHIP", ConditionalLegalForm.LP),
    ],
)
def test_every_bound_legal_form_is_registry_bound(party_type, expected):
    observed = observe_case_basis(with_party_type(bound_case(), party_type))
    assert observed.status == ApplicabilityBasisStatus.REGISTRY_BOUND
    assert observed.legal_form == expected
    assert observed.reason == ApplicabilityBasisReason.REGISTRY_BINDING
    assert observed.source_environment == SourceEnvironment.MOCK  # B4: Mock counts, labelled
    assert observed.binding_ref is not None


def test_government_only_binds_under_the_government_route():
    case = bound_case()
    assert observe_case_basis(with_party_type(case, "GOVERNMENT")).reason == (
        ApplicabilityBasisReason.CONFLICTING_CLASSIFICATION
    )
    government = with_party_type(case, "GOVERNMENT").model_copy(
        update={"uen_route": route_uen("T08GB0001A")}
    )
    assert observe_case_basis(government).legal_form == ConditionalLegalForm.GOVERNMENT
    company = case.model_copy(update={"uen_route": route_uen("T08GB0001A")})
    assert observe_case_basis(with_party_type(company, COMPANY_TEXT)).reason == (
        ApplicabilityBasisReason.CONFLICTING_CLASSIFICATION
    )


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda c: with_party_type(c, "SOMETHING ELSE"), ApplicabilityBasisReason.OTHER_FORM),
        (lambda c: with_party_type(c, None), ApplicabilityBasisReason.OTHER_FORM),
        (lambda c: with_party_type(c, OPQ_SHAPED), ApplicabilityBasisReason.OTHER_FORM),
        (lambda c: c.model_copy(update={"entity": None}), ApplicabilityBasisReason.NO_ENTITY),
        (
            lambda c: c.model_copy(update={"registry_evidence_binding": None}),
            ApplicabilityBasisReason.NO_BINDING,
        ),
        (lambda _c: None, ApplicabilityBasisReason.NO_CASE_RECORD),
    ],
)
def test_anything_unverified_applies_everything(change, reason):
    observed = observe_case_basis(change(bound_case()))
    assert observed.status == ApplicabilityBasisStatus.UNVERIFIED
    assert observed.legal_form is None and observed.reason == reason


def test_a_read_failure_and_a_new_case_run_are_unverified():
    class Broken:
        @property
        def entity(self) -> Any:
            raise RuntimeError("decode failure")

    assert safe_observe(Broken()).reason == ApplicabilityBasisReason.READ_FAILED  # type: ignore[arg-type]
    version = World.version(1, STAGES, bound_case().created_at)
    basis = creation_basis(None, version, now=version.activated_at)  # NEW_CASE: no record
    assert basis.status == ApplicabilityBasisStatus.UNVERIFIED and basis.frozen
    assert basis.reason == ApplicabilityBasisReason.NO_CASE_RECORD


@pytest.mark.parametrize(
    ("entity_type", "environment", "expected"),
    [
        # Sandbox ``entityType`` (synthetic), normalised by the ACRA mapper.
        ("LLP", "SANDBOX", ConditionalLegalForm.LLP),
        # Marketplace Mock ``companyType`` shapes (synthetic); the OPQ shape is OTHER.
        ("Private Company Limited by Shares", "MOCK", ConditionalLegalForm.COMPANY),
        (OPQ_SHAPED, "MOCK", None),
    ],
)
def test_both_adapter_paths_reach_the_single_classifier(entity_type, environment, expected):
    case = bound_case()
    payload = AcraCompanyPayload(
        uen=VALID_UEN,
        entity_name="SYNTHETIC ENTITY PTE. LTD.",
        country_code="SG",
        entity_type=entity_type,
        registered_address=None,
        source_environment=environment,
        source_endpoint=f"https://example.invalid/{VALID_UEN}",
        retrieved_at=case.created_at,
    )
    observed = observe_case_basis(case.model_copy(update={"entity": map_acra_company(payload)}))
    assert observed.legal_form == expected
    assert observed.source_environment == SourceEnvironment(environment)


def test_the_evaluator_has_no_classifier_of_its_own():
    for name in ("workflow_applicability.py", "workflow_management.py"):
        source = (BACKEND / "app" / "services" / name).read_text(encoding="utf-8")
        assert "LIMITED LIABILITY" not in source.upper().replace("_", " ")
        assert "party_type ==" not in source and "party_type in" not in source
    source = (BACKEND / "app" / "services" / "workflow_applicability.py").read_text("utf-8")
    assert "classify_registry_legal_form(entity.party_type)" in source


def test_resolution_drops_only_what_does_not_apply_and_is_deterministic():
    company = resolve_stages(STAGES, ConditionalLegalForm.COMPANY)
    # ADR-018 3.3: a zero-field LP-only stage follows its own condition, so COMPANY drops it.
    assert [s.stage_id for s in company] == ["registry-notes", "signatory"]
    llp = resolve_stages(STAGES, ConditionalLegalForm.LLP)
    assert {s.stage_id: len(s.fields) for s in llp} == {
        "registry-notes": 1,
        "llp-partners": 1,
        "signatory": 1,
    }
    # The zero-field LP-only stage follows its own condition; anchors and order never change.
    assert [s.after_node_id for s in llp] == [
        s.after_node_id for s in STAGES if s.stage_id != "lp-notice"
    ]
    lp = resolve_stages(STAGES, ConditionalLegalForm.LP)
    assert "lp-notice" in [s.stage_id for s in lp]
    assert resolve_stages(STAGES, None) == STAGES  # UNVERIFIED: everything applies
    assert resolve_stages(STAGES, ConditionalLegalForm.LLP) == llp  # deterministic
    plain = (REGISTRY_NOTES,)
    assert resolve_stages(plain, ConditionalLegalForm.LP)[0] is REGISTRY_NOTES
    assert excluded_items(STAGES, ConditionalLegalForm.LLP) == {
        ("signatory", "company-secretary"),
        ("lp-notice", None),
    }


# --- CT-32 / CT-36: freeze at the first binding (end to end, Mock) ------------------------


def test_an_llp_binding_freezes_and_its_llp_stage_holds_the_send():
    world = World(LLP_TEXT)
    case = world.new_case()
    stored = world.stored(case.case_id)
    assert stored is not None  # the freeze wrote the run (insert-only)
    basis = stored.applicability_basis
    assert basis is not None and basis.frozen
    assert (basis.status, basis.legal_form) == (
        ApplicabilityBasisStatus.REGISTRY_BOUND,
        ConditionalLegalForm.LLP,
    )
    assert basis.source_environment == SourceEnvironment.MOCK
    assert ids(stored) == {
        "registry-notes": ("reference",),
        "llp-partners": ("partner-count",),
        "signatory": ("full-name",),
    }
    world.complete(
        case.case_id,
        {"registry-notes": {"reference": "R-1"}, "signatory": {"full-name": "Jane Tan"}},
    )
    assert world.workflows.send_hold_code(case.case_id) == HOLD_INCOMPLETE
    world.complete(case.case_id, {"llp-partners": {"partner-count": "2"}})
    assert world.workflows.send_hold_code(case.case_id) is None


def test_a_company_gets_no_llp_stage_and_is_not_held():
    world = World(COMPANY_TEXT)
    case = world.new_case()
    run = world.run(case.case_id)
    assert "llp-partners" not in ids(run)
    assert ids(run)["signatory"] == ("full-name", "company-secretary")
    world.complete(
        case.case_id,
        {
            "registry-notes": {"reference": "R-1"},
            "signatory": {"full-name": "Jane Tan", "company-secretary": "Ali Bin"},
        },
    )
    assert world.workflows.send_hold_code(case.case_id) is None


def test_freeze_once_and_unconditional_content_is_never_frozen():
    world = World(LLP_TEXT)
    case = world.new_case()
    frozen = world.stored(case.case_id)
    assert world.workflows.freeze_onboarding_basis(case.case_id) == BASIS_HOOK_NONE
    assert world.stored(case.case_id) == frozen
    plain = World(LLP_TEXT, stages=(REGISTRY_NOTES,))
    plain_case = plain.new_case()
    assert plain.stored(plain_case.case_id) is None  # byte-identical: no run written
    assert plain.run(plain_case.case_id).applicability_basis is None


def test_a_lost_freeze_leaves_unverified_and_the_next_run_write_retries():
    world = World(LLP_TEXT, hook=False)
    case = world.new_case()
    assert world.run(case.case_id).applicability_basis is None  # UNVERIFIED: all apply
    assert "company-secretary" in ids(world.run(case.case_id))["signatory"]
    with pytest.raises(WorkflowConflictError):  # the retried freeze moved the revision
        world.answer(case.case_id, "registry-notes", {"reference": "R-1"})
    stored = world.stored(case.case_id)
    assert stored is not None and stored.applicability_basis.legal_form == ConditionalLegalForm.LLP
    world.answer(case.case_id, "registry-notes", {"reference": "R-1"})


# --- CT-33 / CT-40: too late to narrow -------------------------------------------------------


def test_a_document_suggestion_before_the_freeze_makes_it_too_late():
    world = World(LLP_TEXT, hook=False)
    case = world.new_case()
    world.workflows.suggest_from_document(
        case_id=case.case_id,
        document_id=uuid4(),
        content=b"",
        media_type="text/plain",
        extracted_text="Company secretary: Ali Bin",
    )
    touched = world.stored(case.case_id)
    assert RunItemKey(stage_id="signatory", field_id="company-secretary") in touched.ever_touched
    assert world.workflows.freeze_onboarding_basis(case.case_id) == BASIS_HOOK_FROZEN
    run = world.stored(case.case_id)
    assert run.applicability_basis.reason == ApplicabilityBasisReason.TOO_LATE_TO_NARROW
    assert run.applicability_basis.frozen and run.effective_legal_form is None
    assert ids(run)["signatory"] == ("full-name", "company-secretary")  # nothing removed


def _pure_run(case: Any, **changes: Any) -> WorkflowRun:
    return WorkflowRun(
        run_id=uuid4(),
        case_id=case.case_id,
        workflow_id=ONBOARDING_WORKFLOW_ID,
        workflow_name="Corporate onboarding",
        use_case=ONBOARDING_USE_CASE,
        workflow_version=1,
        stages=STAGES,
        created_at=case.created_at,
        updated_at=case.created_at,
        **changes,
    )


@pytest.mark.parametrize(
    ("changes", "closed"),
    [
        # History, not current answers: an answer recorded then cleared (CT-40).
        (
            {"ever_touched": (RunItemKey(stage_id="signatory", field_id="company-secretary"),)},
            False,
        ),
        (
            {
                "answers": (
                    {
                        "stage_id": "signatory",
                        "field_id": "company-secretary",
                        "value": "Ali Bin",
                        "source": "CASE",
                    },
                )
            },
            False,
        ),
        (
            {
                "confirmations": (
                    {
                        # A confirmation of a stage a COMPANY basis would exclude.
                        "stage_id": "llp-partners",
                        "confirmed_by": "ethan-tan",
                        "confirmed_at": "2026-01-02T03:04:05Z",
                    },
                )
            },
            False,
        ),
        ({}, True),  # sent, dispatch confirmed or a dispatch claim
    ],
)
def test_each_touched_kind_is_too_late_to_narrow(changes, closed):
    case = bound_case()
    if "confirmations" in changes:
        case = with_party_type(case, COMPANY_TEXT)
    run = WorkflowRun.model_validate({**_pure_run(case).model_dump(), **changes})
    decision = freeze_decision(
        case,
        run,
        World.version(1, STAGES, case.created_at),
        now=case.created_at,
        case_closed=closed,
    )
    assert decision.basis.reason == ApplicabilityBasisReason.TOO_LATE_TO_NARROW
    assert decision.stages == STAGES


def test_untouched_items_are_dropped_and_a_late_ambiguous_binding_never_narrows():
    case = bound_case()
    version = World.version(1, STAGES, case.created_at)
    clean = freeze_decision(case, _pure_run(case), version, now=case.created_at, case_closed=False)
    assert clean.basis.legal_form == ConditionalLegalForm.LLP
    assert "company-secretary" not in [f.field_id for s in clean.stages for f in s.fields]
    corrected = case.model_copy(update={"identity_corrections": (object(),)})
    ambiguous = freeze_decision(
        corrected, _pure_run(case), version, now=case.created_at, case_closed=False
    )
    assert ambiguous.basis.reason == ApplicabilityBasisReason.AMBIGUOUS_BINDING
    assert ambiguous.stages == STAGES
    twice = case.model_copy(
        update={
            "events": [
                *case.events,
                case.events[
                    next(i for i, e in enumerate(case.events) if e.stage == "REGISTRY_FETCHED")
                ],
            ]
        }
    )
    assert freeze_decision(
        twice, _pure_run(case), version, now=case.created_at, case_closed=False
    ).basis.reason == (ApplicabilityBasisReason.AMBIGUOUS_BINDING)


def test_a_sent_case_and_a_dispatch_claim_are_too_late():
    claimed = World(LLP_TEXT, dispatch_claim=True)
    case = claimed.new_case()
    assert claimed.stored(case.case_id).applicability_basis.reason == (
        ApplicabilityBasisReason.TOO_LATE_TO_NARROW
    )


# --- CT-34: conflicts, hook loss and escalation ----------------------------------------------


def test_a_later_binding_change_holds_the_send_even_when_the_hook_is_lost():
    world = World(LLP_TEXT)
    case = world.new_case()
    frozen = world.stored(case.case_id)
    world.replace_case(case.case_id, registry_evidence_binding=None)  # no hook call
    assert world.stored(case.case_id) == frozen  # the frozen copy is never changed
    assert world.workflows.send_hold_code(case.case_id) == HOLD_APPLICABILITY_BASIS_CONFLICT
    check = basis_conflict_of(world.service.get_case(case.case_id), frozen)
    assert check.status == BasisCheckStatus.CONFLICT and not check.persisted
    assert basis_conflict_of(None, frozen).status == BasisCheckStatus.UNAVAILABLE


def test_the_hook_persists_a_conflict_with_a_code_only_case_event():
    world = World(LLP_TEXT)
    case = world.new_case()
    changed = world.replace_case(case.case_id, registry_evidence_binding=None)
    events = len(changed.events)
    world.service._after_registry_binding(changed)  # noqa: SLF001 - the later binding write
    run = world.stored(case.case_id)
    assert run.basis_conflict is not None and not run.basis_conflict.escalated
    assert run.basis_conflict.observed_status == ApplicabilityBasisStatus.UNVERIFIED
    current = world.service.get_case(case.case_id)
    assert len(current.events) == events + 1
    event = current.events[-1]
    assert event.code == CASE_EVENT_APPLICABILITY_BASIS_CONFLICT
    assert event.stage == current.state and event.outcome == "REVIEW_REQUIRED"
    assert world.workflows.freeze_onboarding_basis(case.case_id) == BASIS_HOOK_NONE  # once
    assert world.workflows.send_hold_code(case.case_id) == HOLD_APPLICABILITY_BASIS_CONFLICT


def test_an_unverified_frozen_run_never_conflicts():
    world = World(OPQ_SHAPED)
    case = world.new_case()
    basis = world.stored(case.case_id).applicability_basis
    assert basis.status == ApplicabilityBasisStatus.UNVERIFIED and basis.frozen
    assert basis.reason == ApplicabilityBasisReason.OTHER_FORM
    world.replace_case(case.case_id, registry_evidence_binding=None)
    assert world.workflows.freeze_onboarding_basis(case.case_id) == BASIS_HOOK_NONE
    assert world.workflows.send_hold_code(case.case_id) == HOLD_INCOMPLETE


def test_escalation_is_add_only_and_survives_later_publications():
    world = World(LLP_TEXT)
    case = world.new_case()
    world.complete(
        case.case_id,
        {"registry-notes": {"reference": "R-1"}, "llp-partners": {"partner-count": "2"}},
    )
    with pytest.raises(WorkflowValidationError) as none:
        world.escalate(case.case_id)
    assert none.value.code == "WORKFLOW_APPLICABILITY_NOT_IN_CONFLICT"
    world.replace_case(case.case_id, registry_evidence_binding=None)
    before = world.run(case.case_id)
    escalated = world.escalate(case.case_id)
    conflict = escalated.basis_conflict
    assert conflict.escalated and conflict.escalated_by == "ethan-tan"
    assert conflict.escalation_reason == REASON
    assert escalated.effective_legal_form is None
    assert ids(escalated)["signatory"] == ("full-name", "company-secretary")  # added
    assert {a.field_id for a in escalated.answers} == {a.field_id for a in before.answers}
    assert {c.stage_id for c in escalated.confirmations} == {"registry-notes", "llp-partners"}
    # The conflict hold is released; the added obligation now holds as incomplete.
    assert world.workflows.send_hold_code(case.case_id) == HOLD_INCOMPLETE
    # A later publication with a COMPANY-only stage applies too (permanently UNVERIFIED).
    world.publish(
        (*STAGES, stage("company-extra", "OWNERSHIP_UBO", [field("x")], applies_to=("COMPANY",)))
    )
    assert "company-extra" in ids(world.run(case.case_id))
    world.service.record_applicability_event(case.case_id, CASE_EVENT_APPLICABILITY_ESCALATED)
    assert world.service.get_case(case.case_id).events[-1].code == (
        CASE_EVENT_APPLICABILITY_ESCALATED
    )


# --- CT-24: rebase reapplies the effective basis ---------------------------------------------


def test_a_rebase_reapplies_the_frozen_basis_and_keeps_touched_items():
    world = World(LLP_TEXT)
    case = world.new_case()
    world.answer(case.case_id, "registry-notes", {"reference": "R-1"})
    world.confirm(case.case_id, "registry-notes")
    new_llp = stage("llp-extra", "OWNERSHIP_UBO", [field("y")], applies_to=("LLP",))
    company = stage("company-extra", "OWNERSHIP_UBO", [field("x")], applies_to=("COMPANY",))
    # The ALL stage the run already confirmed becomes conditional optional content.
    narrowed_notes = stage(
        "registry-notes",
        "ACRA_REGISTRY",
        [field("reference", applies_to=("COMPANY",))],
    )
    world.publish((narrowed_notes, LLP_ONLY, SIGNATORY, LP_NOTICE, new_llp, company))
    run = world.run(case.case_id)
    assert run.workflow_version == 2
    assert "llp-extra" in ids(run) and "company-extra" not in ids(run)
    assert ids(run)["registry-notes"] == ("reference",)  # touched: never dropped
    assert run.applicability_basis == world.stored(case.case_id).applicability_basis


def test_a_rebase_after_too_late_drops_nothing():
    world = World(LLP_TEXT, dispatch_claim=True)
    case = world.new_case()
    world.publish(
        (*STAGES, stage("company-extra", "OWNERSHIP_UBO", [field("x")], applies_to=("COMPANY",)))
    )
    run = world.run(case.case_id)
    assert {"llp-partners", "company-extra"} <= set(ids(run))
    assert ids(run)["signatory"] == ("full-name", "company-secretary")


def test_start_run_prefills_only_the_resolved_copy():
    world = World(LLP_TEXT)
    case = world.new_case()
    refresh = WorkflowDefinition(
        workflow_id="refresh",
        name="Refresh",
        use_case="Refresh",
        country="SG",
        case_source=WorkflowCaseSource.EXISTING_CASE,
        versions=(
            World.version(
                1,
                (
                    stage("common", None, [field("name", case_data_key="LEGAL_NAME")]),
                    stage(
                        "company-only",
                        None,
                        [field("ssic", case_data_key="SSIC")],
                        applies_to=("COMPANY",),
                    ),
                ),
                world.clock.value,
            ),
        ),
        created_at=world.clock.value,
        updated_at=world.clock.value,
    )
    world.definitions.create(refresh)
    workflows = WorkflowManagementService(
        definitions=world.definitions,
        runs=world.runs,
        cases=world.service,
        case_is_onboarded=lambda _case_id: True,
        case_data=lambda _case_id: {"LEGAL_NAME": "Synthetic LLP", "SSIC": "62011"},
        clock=world.clock,
    )
    run = workflows.start_run(lambda: RM, "refresh", case_id=case.case_id)
    assert [s.stage_id for s in run.stages] == ["common"]
    assert [a.field_id for a in run.answers] == ["name"]
    assert run.applicability_basis.legal_form == ConditionalLegalForm.LLP


# --- CT-25 / CT-37: send check and fence routing ---------------------------------------------


def test_a_resolution_failure_fails_closed(monkeypatch):
    world = World(LLP_TEXT)
    case = world.new_case()

    def broken(*_args: Any) -> Any:
        raise RuntimeError("unreadable")

    monkeypatch.setattr(applicability, "observe_case_basis", broken)
    assert world.workflows.send_hold_code(case.case_id) == HOLD_UNAVAILABLE


def test_the_conflict_hold_never_fires_on_hold():
    from test_adr017_dispatch_fence import Clock, _authorise, _definitions, _entry, _fence, _ledger

    from app.domain.target_submission import GoldTierOperationMarker
    from app.services.errors import DispatchFenceRefusedError

    clock, entry = Clock(), _entry(GoldTierOperationMarker.SEARCH)
    superseded: list[str] = []
    fence = _fence(
        _ledger(entry, clock),
        _definitions(),
        hold=lambda _case_id: HOLD_APPLICABILITY_BASIS_CONFLICT,
        on_hold=lambda _case_id, code: superseded.append(code),
    )
    with pytest.raises(DispatchFenceRefusedError) as refused:
        _authorise(fence, entry)
    assert refused.value.code == HOLD_APPLICABILITY_BASIS_CONFLICT and superseded == []


def test_a_conflict_hold_returns_zero_touch_to_confirmation_with_no_goldtier_call(monkeypatch):
    from test_adr017_dispatch_fence import _refuse_once, _zero_touch_case_at_confirmation
    from test_aws_goldtier_sandbox_readiness import confirmation, full_path_transport, methods, ok

    zero, transport, record = _zero_touch_case_at_confirmation()
    transport.responses.extend([ok([]), *full_path_transport().responses])
    _refuse_once(monkeypatch, HOLD_APPLICABILITY_BASIS_CONFLICT)
    held = zero.confirm_target_dispatch(**confirmation(zero, record))
    assert held.status == "WAITING_FOR_REVIEW" and held.technical_failure is None
    assert held.current_stage == "READINESS"
    assert methods(transport).count("POST") == 0


# --- CT-38 / CT-40: event-count token and lock order -----------------------------------------


def test_the_case_event_invalidates_a_stale_event_count():
    world = World(LLP_TEXT)
    case = world.new_case()
    count = len(world.service.get_case(case.case_id).events)
    world.service.record_applicability_event(case.case_id, CASE_EVENT_APPLICABILITY_BASIS_CONFLICT)
    assert len(world.service.get_case(case.case_id).events) == count + 1
    with pytest.raises(ValueError):
        world.service.invalidate_target_dispatch_confirmation(
            case_id=case.case_id, expected_case_event_count=count
        )
    with pytest.raises(ValueError):
        world.service.record_applicability_event(case.case_id, "WORKFLOW_SOMETHING_ELSE")


def test_the_hook_takes_neither_the_gate_nor_the_definition_lock():
    world = World(LLP_TEXT, hook=False)
    case = world.new_case()
    held, release = threading.Event(), threading.Event()

    def hold_both() -> None:
        with (
            world.workflows.definition_lock,
            world.workflows.confirmation_gate.holding(ONBOARDING_WORKFLOW_ID),
        ):
            held.set()
            release.wait(10)

    holder = threading.Thread(target=hold_both)
    holder.start()
    assert held.wait(5)
    outcome: list[str] = []
    worker = threading.Thread(
        target=lambda: outcome.append(world.workflows.freeze_onboarding_basis(case.case_id))
    )
    worker.start()
    worker.join(5)
    release.set()
    holder.join(5)
    assert outcome == [BASIS_HOOK_FROZEN]


def test_conflict_record_constant_matches_the_hook_outcome():
    assert BASIS_HOOK_CONFLICT_RECORDED == "CONFLICT_RECORDED"
