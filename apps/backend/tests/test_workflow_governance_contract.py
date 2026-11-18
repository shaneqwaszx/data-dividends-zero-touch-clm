"""C0 contract freeze: fixtures, error codes and model invariants (ADR-017, D-135)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from scripts.generate_workflow_governance_fixtures import OUT, render, stored_text

from app.api_workflow_governance_models import (
    ApprovalInboxResponse,
    ComparisonResponse,
    DecisionRequest,
    DecisionResponse,
    GovernanceErrorBody,
    ProposalResponse,
    SimulationResult,
    SimulationScenario,
    ValidationReport,
    WorkflowGovernanceView,
)
from app.domain.workflow_governance import (
    GOVERNANCE_ERROR_STATUS,
    GOVERNANCE_TOP_LEVEL_FIELDS,
    DecidedProposalEntry,
    GovernanceErrorCode,
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
from app.domain.workflows import WorkflowField, WorkflowFieldKind, WorkflowStage
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
