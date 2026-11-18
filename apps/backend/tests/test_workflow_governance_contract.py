"""C0 contract freeze: fixtures, error codes and model invariants (ADR-017, D-135).

M3 (ADR-018, CC-8): conditional applicability models and CT-21 golden hashes.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.generate_workflow_governance_fixtures import OUT, render, stored_text

from app.api_workflow_governance_models import (
    ApplicabilityEscalationRequest,
    ApprovalInboxResponse,
    ComparisonResponse,
    DecisionRequest,
    DecisionResponse,
    GovernanceErrorBody,
    ProposalResponse,
    RunApplicabilityView,
    SimulationResult,
    SimulationScenario,
    ValidationReport,
    WorkflowGovernanceView,
)
from app.domain.models import EventOutcome, SourceEnvironment, WorkflowState
from app.domain.registry_legal_form import ConditionalLegalForm, RegistryLegalForm
from app.domain.workflow_governance import (
    CASE_EVENT_APPLICABILITY_BASIS_CONFLICT,
    CASE_EVENT_APPLICABILITY_ESCALATED,
    CONDITIONAL_APPLICABILITY_ENABLED_DEFAULT,
    CONDITIONAL_APPLICABILITY_ENABLED_ENV,
    GOVERNANCE_ERROR_STATUS,
    GOVERNANCE_TOP_LEVEL_FIELDS,
    HOLD_APPLICABILITY_BASIS_CONFLICT,
    BaselineField,
    BaselineStage,
    DecidedProposalEntry,
    FieldSignature,
    GovernanceErrorCode,
    PermanentObligationChange,
    ProposalKind,
    ProposalOrigin,
    ProposalState,
    RatchetRule,
    VersionOrigin,
    VersionProvenance,
    WorkflowGovernanceState,
    WorkflowProposal,
    normalise_label,
    proposal_content_hash,
    ratchet_error_code,
)
from app.domain.workflows import (
    CONDITIONAL_ONBOARDING_ANCHORS,
    MAX_RUN_TOUCHED_KEYS,
    ApplicabilityBasis,
    ApplicabilityBasisReason,
    ApplicabilityBasisStatus,
    BasisConflict,
    BindingRef,
    RunItemKey,
    WorkflowCompany,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowRun,
    WorkflowStage,
    effective_applies_to,
)
from app.persistence.adr017_migrations import P2_1_DEFINITION_FIELDS

MODELS = {
    "proposal_draft.json": ProposalResponse,
    "proposal_pending_director_view.json": ProposalResponse,
    "validation_report_valid.json": ValidationReport,
    "validation_report_refused.json": ValidationReport,
    "simulation_result.json": SimulationResult,
    "approvals_inbox.json": ApprovalInboxResponse,
    "comparison.json": ComparisonResponse,
    "decision_request_approve.json": DecisionRequest,
    "decision_response_approved.json": DecisionResponse,
    "workflow_governance_view.json": WorkflowGovernanceView,
    "proposal_conditional_draft.json": ProposalResponse,
    "run_applicability_view.json": RunApplicabilityView,
    "error_ratchet_removed.json": GovernanceErrorBody,
    "error_acknowledgement_required.json": GovernanceErrorBody,
    "error_self_decision.json": GovernanceErrorBody,
    "error_history_unavailable.json": GovernanceErrorBody,
}
T = datetime(2026, 11, 17, tzinfo=UTC)
FROZEN_CODES = {
    "WORKFLOW_PROPOSAL_OPEN",
    "WORKFLOW_PROPOSAL_STALE",
    "WORKFLOW_PROPOSAL_NOT_FOUND",
    "WORKFLOW_PROPOSAL_STATE_INVALID",
    "WORKFLOW_PROPOSAL_CONTENT_CHANGED",
    "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE",
    "WORKFLOW_PROPOSAL_INVALID",
    "WORKFLOW_PROPOSAL_EMPTY",
    "WORKFLOW_REQUIRED_OBLIGATION_REMOVED",
    "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED",
    "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED",
    "WORKFLOW_SELF_DECISION_REFUSED",
    "WORKFLOW_PROPOSAL_TOO_LARGE",
    "WORKFLOW_HISTORY_UNAVAILABLE",
    "WORKFLOW_GOVERNANCE_NOT_MIGRATED",
    "WORKFLOW_DRAFT_NOT_RELEASABLE",
    "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS",
    "WORKFLOW_NOTICES_UNACKNOWLEDGED",
    "WORKFLOW_ROUTE_RETIRED",
}


def test_committed_fixtures_equal_a_fresh_render() -> None:
    rendered = render()
    assert set(rendered) == {path.name for path in Path(OUT).glob("*.json")}
    for name, text in rendered.items():
        assert stored_text(Path(OUT) / name) == text, name


@pytest.mark.parametrize("name", sorted(MODELS))
def test_every_fixture_validates_against_its_model(name: str) -> None:
    MODELS[name].model_validate(json.loads((Path(OUT) / name).read_text(encoding="utf-8")))


def test_scenario_catalogue_fixture_is_synthetic() -> None:
    items = json.loads((Path(OUT) / "simulation_scenarios.json").read_text(encoding="utf-8"))
    assert items and all(SimulationScenario.model_validate(item).synthetic for item in items)


def test_error_codes_are_frozen_and_mapped() -> None:
    assert {code.value for code in GovernanceErrorCode} == FROZEN_CODES
    assert set(GOVERNANCE_ERROR_STATUS) == set(GovernanceErrorCode)
    assert GOVERNANCE_ERROR_STATUS[GovernanceErrorCode.HISTORY_UNAVAILABLE] == 503
    assert ratchet_error_code(RatchetRule.RR_1) == GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED
    assert ratchet_error_code(RatchetRule.RR_3) == GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED
    for rule in set(RatchetRule) - {RatchetRule.RR_1, RatchetRule.RR_3}:
        assert ratchet_error_code(rule) == GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED


def test_p2_0_tools_already_refuse_every_stored_governance_field() -> None:
    # B-0 probe 6a: the P2-0 reverse migration refuses any document carrying these names.
    stored = set(GOVERNANCE_TOP_LEVEL_FIELDS) - {"version_provenance", "governance_sequence"}
    assert stored <= set(P2_1_DEFINITION_FIELDS)


def test_normalised_label_and_content_hash_are_deterministic() -> None:
    assert normalise_label("  Screening   Outcome! ") == normalise_label("screening outcome")
    assert normalise_label("Screened-by") == "screenedby"
    stage = WorkflowStage(
        stage_id="s",
        name="S",
        fields=(WorkflowField(field_id="f", label="F", kind=WorkflowFieldKind.TEXT),),
    )
    first = proposal_content_hash(ProposalKind.CHANGE, (stage,))
    assert first == proposal_content_hash(ProposalKind.CHANGE, (stage,))
    assert first != proposal_content_hash(ProposalKind.CHANGE, ())
    assert first != proposal_content_hash(ProposalKind.RESET_TO_DEFAULT, (stage,))


def _proposal(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "proposal_id": "0b6f7c2e-1d3a-4c5b-9e8f-7a6b5c4d3e2f",
        "workflow_id": "w",
        "base_version": 0,
        "author_id": "hr-1",
        "created_at": T,
        "updated_at": T,
        "last_activity_at": T,
    }
    return {**base, **changes}


def test_model_refuses_self_decision() -> None:
    with pytest.raises(ValidationError, match="SELF_DECISION"):
        WorkflowProposal.model_validate(
            _proposal(
                state=ProposalState.APPROVED,
                content_hash="0" * 64,
                submitted_at=T,
                decided_at=T,
                decided_by="hr-1",
                decision_reason="A sufficient reason.",
                published_version=1,
            )
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"state": ProposalState.PENDING_APPROVAL},  # no content hash
        {"state": ProposalState.APPROVED, "content_hash": "0" * 64, "submitted_at": T},
        {"state": ProposalState.STALE},
        {"author_id": None},
        {"origin": ProposalOrigin.PRE_GOVERNANCE_DRAFT, "author_id": None},  # not WITHDRAWN
        {"restore_target_version": 1},
    ],
)
def test_model_refuses_inconsistent_proposals(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        WorkflowProposal.model_validate(_proposal(**changes))


def test_legacy_version_is_never_approved() -> None:
    with pytest.raises(ValidationError):
        VersionProvenance(
            version=1,
            origin=VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION,
            author_id=None,
            approved_by="director-1",
            proposal_id=None,
            published_at=T,
        )
    with pytest.raises(ValidationError):
        VersionProvenance(
            version=2,
            origin=VersionOrigin.GOVERNED_APPROVAL,
            author_id="hr-1",
            approved_by=None,
            proposal_id="0b6f7c2e-1d3a-4c5b-9e8f-7a6b5c4d3e2f",
            published_at=T,
        )


def test_decided_entry_keeps_the_full_record_until_archived() -> None:
    record = WorkflowProposal.model_validate(_proposal(state=ProposalState.WITHDRAWN))
    summary = {
        "proposal_id": record.proposal_id,
        "kind": record.kind,
        "state": record.state,
        "origin": record.origin,
        "author_id": record.author_id,
        "decided_by": None,
        "decided_at": None,
        "ended_at": T,
        "published_version": None,
        "content_hash": None,
        "record_hash": "0" * 64,
    }
    with pytest.raises(ValidationError, match="cold copy"):
        DecidedProposalEntry.model_validate({**summary, "archived": False, "record": None})
    DecidedProposalEntry.model_validate({**summary, "archived": False, "record": record})
    DecidedProposalEntry.model_validate({**summary, "archived": True, "record": None})


def test_open_proposal_slot_holds_only_open_states() -> None:
    withdrawn = WorkflowProposal.model_validate(_proposal(state=ProposalState.WITHDRAWN))
    with pytest.raises(ValidationError):
        WorkflowGovernanceState(open_proposal=withdrawn)
    assert not WorkflowGovernanceState().migrated


# --- M3 (ADR-018, CC-8) ---

# CT-21 golden values, recorded before CC-8 on the M1/M2 final candidate (703a0057).
GOLDEN_SANCTIONS_HASH = "306a1db210e1ad991884effd8f68275018c8e1530cb5248a72eefc2aac72dc9f"
GOLDEN_EMPTY_HASH = "70d7ec24109a07b17e126b6ba418f94a3b59eb2e7ebb741a92f5923c9e76170d"
GOLDEN_FIXTURES = {
    "approvals_inbox.json": "e94154a3f9a3e4191402a28c886013bd0a7d1052f7d807af5b6eba9467da90a7",
    "comparison.json": "fea8846a1c970d6a953b302acb30b56c2fe1d16bb31fdbf1c77fcba0e46dec08",
    "decision_request_approve.json": (
        "172286905aabe28d337ace3b39c14a42cb1ce265422bb1cef2569c54678266f7"
    ),
    "decision_response_approved.json": (
        "daf4f4b0d788125cb64482974685c509912dc36c47b08143c425d1515689061c"
    ),
    "error_acknowledgement_required.json": (
        "1458f8be976c6a12c56c9f7242c1ed8dec35038ca31f8f5fb6811488b228c60f"
    ),
    "error_history_unavailable.json": (
        "009839bce9a9e013917eab8ff5cf61187eb00196ea1fbe7153f2d65a59ab6e52"
    ),
    "error_ratchet_removed.json": (
        "b6d7a7e177f88c19435dda0f459ca9ad2d006c3caba5acf6907acc36b403e51b"
    ),
    "error_self_decision.json": "95a09f9cf443a5ab9fa71e847676d7340f52fc70fa0cb449e67974bdff0a16e4",
    "proposal_draft.json": "c34c33ea4fb658a9553f606fb0cb6ea23af0a6d00259fb7dbbb0491d58665f7c",
    "proposal_pending_director_view.json": (
        "603ed35ce9ce5fdd86082fd44439a95f2213351b51c2ed23ca14aabbfe5c2c0a"
    ),
    "simulation_result.json": "b0d0fcf0fb8374cfa7d409e5206189176b1a313bd5e64ac5840681bfdcc5e725",
    "simulation_scenarios.json": (
        "c7269148c328f04f9ee14fddedd691a72b0813d08792d694d7e79d6c7f83f662"
    ),
    "validation_report_refused.json": (
        "28b825f27ba94fad9666c6afe67d63f89ec487f38025e79e55be721d3bcf107e"
    ),
    "validation_report_valid.json": (
        "e8afc8b87653c7c81fea5d32a499232e0380b3bd352b2f7e8d91bd63cb7f918e"
    ),
    "workflow_governance_view.json": (
        "0abe21593ae7a969718a53712369a7a6826819c2cd73ed29cdb18028cc1d407a"
    ),
}
FORMS = ConditionalLegalForm


def _field(field_id: str = "f", applies_to: object = None) -> WorkflowField:
    return WorkflowField.model_validate(
        {"field_id": field_id, "label": "F", "kind": "TEXT", "applies_to": applies_to}
    )


def _stage(applies_to: object = None, *fields: WorkflowField) -> WorkflowStage:
    return WorkflowStage.model_validate(
        {
            "stage_id": "s",
            "name": "S",
            "applies_to": applies_to,
            "fields": fields or (_field(),),
        }
    )


def test_ct21_existing_hashes_and_fixtures_are_unchanged() -> None:
    from scripts.generate_workflow_governance_fixtures import HASH

    assert HASH == GOLDEN_SANCTIONS_HASH
    assert proposal_content_hash(ProposalKind.CHANGE, ()) == GOLDEN_EMPTY_HASH
    rendered = render()
    for name, digest in GOLDEN_FIXTURES.items():
        assert hashlib.sha256(rendered[name].encode("utf-8")).hexdigest() == digest, name


def test_ct21_unconditional_content_serialises_without_applies_to() -> None:
    stage = _stage()
    dumped = stage.model_dump(mode="json")
    assert "applies_to" not in dumped
    assert "applies_to" not in dumped["fields"][0]
    assert WorkflowStage.model_validate(dumped) == stage


def test_ct21_applies_to_is_canonical_and_hashes_order_independently() -> None:
    forward = _stage(["LP", "LLP"])
    backward = _stage(["LLP", "LP"])
    assert forward.applies_to == (FORMS.LLP, FORMS.LP)
    assert forward.model_dump(mode="json")["applies_to"] == ["LLP", "LP"]
    assert proposal_content_hash(ProposalKind.CHANGE, (forward,)) == proposal_content_hash(
        ProposalKind.CHANGE, (backward,)
    )
    assert proposal_content_hash(ProposalKind.CHANGE, (forward,)) != proposal_content_hash(
        ProposalKind.CHANGE, (_stage(),)
    )


@pytest.mark.parametrize(
    "applies_to",
    [
        [],
        ["LLP", "LLP"],
        ["OTHER"],
        ["UNVERIFIED"],
        [form.value for form in ConditionalLegalForm],  # the full set must be ALL (None)
    ],
)
def test_ct21_invalid_applies_to_is_refused(applies_to: list[str]) -> None:
    with pytest.raises(ValidationError):
        _field(applies_to=applies_to)
    with pytest.raises(ValidationError):
        _stage(applies_to)


def test_ct21_field_applies_within_its_stage() -> None:
    inherited = _stage(["LLP", "LP"], _field("a"), _field("b", ["LP"]))
    assert inherited.is_conditional
    assert effective_applies_to(inherited.applies_to, inherited.fields[0].applies_to) == (
        FORMS.LLP,
        FORMS.LP,
    )
    assert effective_applies_to(inherited.applies_to, inherited.fields[1].applies_to) == (
        FORMS.LP,
    )
    assert effective_applies_to(None, None) is None
    assert not _stage().is_conditional
    with pytest.raises(ValidationError, match="within its stage"):
        _stage(["LP"], _field("a", ["LLP"]))


def test_conditional_legal_forms_are_registry_forms_without_other() -> None:
    assert {form.value for form in ConditionalLegalForm} == {
        form.value for form in RegistryLegalForm
    } - {"OTHER"}


def test_onboarding_conditional_anchors_start_at_the_registry_stage() -> None:
    assert {
        "ACRA_REGISTRY",
        "DOCUMENT_IDP",
        "RECONCILIATION",
        "OWNERSHIP_UBO",
        "ADVISORY",
        "GOLDTIER_DETAILS",
    } == CONDITIONAL_ONBOARDING_ANCHORS


def test_baseline_applicability_keeps_m1_bytes() -> None:
    signature = FieldSignature(
        kind=WorkflowFieldKind.TEXT, normalised_label="f", has_case_data_key=False
    )
    assert signature.model_dump(mode="json")["applicability"] is None  # stored as null, as before
    stage = BaselineStage(
        stage_id="s",
        normalised_name="s",
        representative_name="S",
        fields=(BaselineField(field_id="f", signature=signature, representative=_field()),),
        first_published_version=1,
        last_published_version=1,
    )
    assert "applicability" not in stage.model_dump(mode="json")
    conditional = FieldSignature.model_validate(
        {**signature.model_dump(mode="json"), "applicability": ["LP", "LLP"]}
    )
    assert conditional.applicability == (FORMS.LLP, FORMS.LP)


def test_cc8_codes_and_gate() -> None:
    assert PermanentObligationChange.APPLICABILITY_BROADENED.value == "APPLICABILITY_BROADENED"
    assert RatchetRule.RR_8.value == "RR-8"
    assert HOLD_APPLICABILITY_BASIS_CONFLICT == "WORKFLOW_APPLICABILITY_BASIS_CONFLICT"
    # A send hold, not a governance error code; the frozen error-code set is unchanged.
    assert HOLD_APPLICABILITY_BASIS_CONFLICT not in {code.value for code in GovernanceErrorCode}
    assert CONDITIONAL_APPLICABILITY_ENABLED_DEFAULT is False
    assert CONDITIONAL_APPLICABILITY_ENABLED_ENV == "CLM_WORKFLOW_CONDITIONAL_APPLICABILITY_ENABLED"


def test_case_event_codes_add_no_workflow_state_or_outcome() -> None:
    # ADR-018 §8: new case events are ``code`` strings only. These enums are frozen here.
    assert {item.value for item in WorkflowState} == {
        "COMPLETED", "FAILED", "GT_ENRICHED", "GT_POLICY_CREATED", "GT_SEARCHED",
        "GT_SHELL_CREATED", "REGISTRY_FETCHED", "REQUESTED", "REVIEW_REQUIRED", "VALIDATED",
    }
    assert {item.value for item in EventOutcome} == {
        "FAILED", "PARTIAL", "REVIEW_REQUIRED", "SUCCEEDED",
    }
    for code in (CASE_EVENT_APPLICABILITY_BASIS_CONFLICT, CASE_EVENT_APPLICABILITY_ESCALATED):
        assert code not in {item.value for item in WorkflowState}
        assert code not in {item.value for item in EventOutcome}


def _basis(**changes: object) -> ApplicabilityBasis:
    base: dict[str, object] = {
        "legal_form": "LLP",
        "status": "REGISTRY_BOUND",
        "reason": "REGISTRY_BINDING",
        "source_environment": SourceEnvironment.MOCK,
        "evaluated_at": T,
        "evaluated_from_version": 1,
        "frozen": True,
        "binding_ref": BindingRef(cache_id="a" * 64, cache_revision=0, bound_to_case_at=T),
    }
    return ApplicabilityBasis.model_validate({**base, **changes})


def _run(**changes: object) -> WorkflowRun:
    base: dict[str, object] = {
        "run_id": "5d1c2b3a-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
        "company": WorkflowCompany(legal_name="L", registration_id="R", team_id="t"),
        "workflow_id": "w",
        "workflow_name": "W",
        "use_case": "U",
        "workflow_version": 1,
        "stages": (),
        "created_at": T,
        "updated_at": T,
    }
    return WorkflowRun.model_validate({**base, **changes})


def test_m1_runs_serialise_unchanged() -> None:
    dumped = _run().model_dump(mode="json")
    assert not {"applicability_basis", "basis_conflict", "ever_touched"} & set(dumped)
    assert _run().effective_legal_form is None  # no basis: UNVERIFIED


@pytest.mark.parametrize(
    "changes",
    [
        {"legal_form": None},
        {"status": "UNVERIFIED"},
        {"reason": "NO_BINDING"},
        {"binding_ref": None},
    ],
)
def test_basis_is_consistent(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _basis(**changes)
    ApplicabilityBasis.model_validate(
        {
            "legal_form": None,
            "status": ApplicabilityBasisStatus.UNVERIFIED,
            "reason": ApplicabilityBasisReason.TOO_LATE_TO_NARROW,
            "evaluated_at": T,
            "evaluated_from_version": 1,
            "frozen": True,
        }
    )


def test_effective_basis() -> None:
    assert _run(applicability_basis=_basis(frozen=False)).effective_legal_form is None
    assert _run(applicability_basis=_basis()).effective_legal_form == FORMS.LLP
    conflict = BasisConflict(detected_at=T, observed_status=ApplicabilityBasisStatus.UNVERIFIED)
    held = _run(applicability_basis=_basis(), basis_conflict=conflict)
    assert held.effective_legal_form == FORMS.LLP  # held by the send check, not narrowed
    escalated = conflict.model_copy(
        update={
            "escalated_by": "rm-1",
            "escalated_at": T,
            "escalation_reason": "Registry re-check differs.",
        }
    )
    assert _run(applicability_basis=_basis(), basis_conflict=escalated).effective_legal_form is None


def test_conflict_and_touched_rules() -> None:
    conflict = BasisConflict(detected_at=T, observed_status=ApplicabilityBasisStatus.UNVERIFIED)
    with pytest.raises(ValidationError, match="REGISTRY_BOUND"):
        _run(basis_conflict=conflict)
    with pytest.raises(ValidationError, match="REGISTRY_BOUND"):
        _run(applicability_basis=_basis(frozen=False), basis_conflict=conflict)
    with pytest.raises(ValidationError, match="who, when and why"):
        BasisConflict(
            detected_at=T, observed_status=ApplicabilityBasisStatus.UNVERIFIED, escalated_at=T
        )
    with pytest.raises(ValidationError):
        BasisConflict(
            detected_at=T,
            observed_status=ApplicabilityBasisStatus.UNVERIFIED,
            escalated_by="rm-1",
            escalated_at=T,
            escalation_reason="short",
        )
    key = RunItemKey(stage_id="s", field_id="f")
    with pytest.raises(ValidationError, match="once"):
        _run(ever_touched=(key, key))
    assert MAX_RUN_TOUCHED_KEYS == 32 * 33


def test_typed_simulation_scenario_and_escalation_request() -> None:
    with pytest.raises(ValidationError):
        SimulationScenario(scenario_id="x", label="X", description="X", legal_form="LISTED")
    for value in ("UNVERIFIED", "OTHER", "LLP"):
        SimulationScenario(scenario_id="x", label="X", description="X", legal_form=value)
    with pytest.raises(ValidationError):
        ApplicabilityEscalationRequest(
            run_id="5d1c2b3a-4e5f-4a6b-8c7d-9e0f1a2b3c4d", expected_revision=1, reason="short"
        )
    view = RunApplicabilityView.from_run(_run(applicability_basis=_basis()))
    assert view is not None and view.source_environment == SourceEnvironment.MOCK
    assert RunApplicabilityView.from_run(_run()) is None
