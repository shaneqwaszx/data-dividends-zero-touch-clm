"""Write the frozen workflow-governance contract fixtures (C0) from the contract models.

The fixtures are synthetic. Both the backend contract test and the frontend type tests read
them, so a fixture can never drift from the models. Run with ``--check`` to verify that the
committed fixtures equal a fresh render (used by the contract test).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.api_workflow_governance_models import (
    AffectedCases,
    ApprovalInboxItem,
    ApprovalInboxResponse,
    BaselineSummary,
    ChangeCounts,
    ComparisonResponse,
    DecisionRequest,
    DecisionResponse,
    FieldDiff,
    GovernanceErrorBody,
    ProposalResponse,
    PublicationReport,
    SimulatedStep,
    SimulationOutcome,
    SimulationResult,
    SimulationScenario,
    StageDiff,
    ValidationIssue,
    ValidationReport,
    WorkflowGovernanceView,
)
from app.domain.workflow_governance import (
    LEGACY_VERSION_NOTE,
    MAX_ENCODED_VERSION_BYTES,
    PERMANENT_OBLIGATION_WARNING,
    DecisionOutcome,
    GovernanceErrorCode,
    GovernanceEvent,
    GovernanceEventKind,
    ObligationKey,
    PermanentObligation,
    PermanentObligationChange,
    ProposalKind,
    ProposalState,
    RatchetRule,
    VersionOrigin,
    VersionProvenance,
    WorkflowProposal,
    proposal_content_hash,
)
from app.domain.workflows import (
    ONBOARDING_LOCKED_STAGES,
    ONBOARDING_WORKFLOW_ID,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "contracts" / "fixtures" / "workflow-governance"
T0 = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
T1 = datetime(2026, 11, 17, 9, 30, tzinfo=UTC)
T2 = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
HR = "hr-synthetic-1"
DIRECTOR = "director-synthetic-1"
PID = "0b6f7c2e-1d3a-4c5b-9e8f-7a6b5c4d3e2f"

SANCTIONS = WorkflowStage(
    stage_id="sanctions-attestation",
    name="Sanctions attestation",
    after_node_id="OWNERSHIP_UBO",
    fields=(
        WorkflowField(field_id="screened-by", label="Screened by", kind=WorkflowFieldKind.TEXT),
        WorkflowField(
            field_id="outcome",
            label="Screening outcome",
            kind=WorkflowFieldKind.CHOICE,
            options=("Clear", "Escalated"),
        ),
        WorkflowField(
            field_id="comment",
            label="Comment",
            kind=WorkflowFieldKind.TEXT,
            required=False,
        ),
    ),
)
ACTIVE = WorkflowVersion(version=1, stages=(), activated_at=T0, activated_by="director-legacy-1")
HASH = proposal_content_hash(ProposalKind.CHANGE, (SANCTIONS,))


def _proposal(state: ProposalState, **extra: object) -> WorkflowProposal:
    fields: dict[str, object] = {
        "proposal_id": PID,
        "workflow_id": ONBOARDING_WORKFLOW_ID,
        "state": state,
        "revision": 3,
        "base_version": 1,
        "stages": (SANCTIONS,),
        "note": "Add a sanctions attestation after ownership review.",
        "author_id": HR,
        "created_at": T0,
        "updated_at": T1,
        "last_activity_at": T1,
    }
    return WorkflowProposal.model_validate({**fields, **extra})


def _response(item: WorkflowProposal, **flags: bool) -> ProposalResponse:
    base = {"can_edit": False, "can_submit": False, "can_withdraw": False, "can_decide": False}
    return ProposalResponse.from_domain(item, **{**base, **flags})


OBLIGATIONS = (
    PermanentObligation(
        key=ObligationKey(stage_id="sanctions-attestation"),
        change=PermanentObligationChange.NEW_REQUIRED_STAGE,
        stage_name="Sanctions attestation",
        detail="New required stage; it will hold the send until confirmed.",
    ),
    PermanentObligation(
        key=ObligationKey(stage_id="sanctions-attestation", field_id="screened-by"),
        change=PermanentObligationChange.NEW_REQUIRED_FIELD,
        stage_name="Sanctions attestation",
        field_label="Screened by",
        detail="New required text field.",
    ),
    PermanentObligation(
        key=ObligationKey(stage_id="sanctions-attestation", field_id="outcome"),
        change=PermanentObligationChange.NEW_REQUIRED_FIELD,
        stage_name="Sanctions attestation",
        field_label="Screening outcome",
        detail="New required choice: Clear, Escalated.",
    ),
)
LEGACY = VersionProvenance(
    version=1,
    origin=VersionOrigin.PRE_GOVERNANCE_DIRECTOR_ACTIVATION,
    author_id=None,
    approved_by=None,
    proposal_id=None,
    activated_by="director-legacy-1",
    published_at=T0,
    note=LEGACY_VERSION_NOTE,
)
GOVERNED = VersionProvenance(
    version=2,
    origin=VersionOrigin.GOVERNED_APPROVAL,
    author_id=HR,
    approved_by=DIRECTOR,
    proposal_id=PID,
    published_at=T2,
)
VALID = ValidationReport(
    valid=True,
    content_hash=HASH,
    encoded_bytes=612,
    max_encoded_bytes=MAX_ENCODED_VERSION_BYTES,
    base_version=1,
    active_version=1,
    permanent_obligations=OBLIGATIONS,
)


def fixtures() -> dict[str, object]:
    draft = _proposal(ProposalState.DRAFT)
    pending = _proposal(ProposalState.PENDING_APPROVAL, submitted_at=T1, content_hash=HASH)
    approved = _proposal(
        ProposalState.APPROVED,
        revision=4,
        submitted_at=T1,
        content_hash=HASH,
        decided_at=T2,
        decided_by=DIRECTOR,
        decision_reason="Required by the sanctions screening procedure.",
        acknowledged_permanent_obligations=tuple(item.key for item in OBLIGATIONS),
        published_version=2,
    )
    scenario = SimulationScenario(
        scenario_id="private-limited-clear",
        label="Private limited company, clear screening",
        description="A synthetic Singapore private company limited by shares.",
        legal_form="PRIVATE_COMPANY_LIMITED_BY_SHARES",
    )
    refused = ValidationReport(
        valid=False,
        content_hash=proposal_content_hash(ProposalKind.CHANGE, ()),
        encoded_bytes=2,
        max_encoded_bytes=MAX_ENCODED_VERSION_BYTES,
        base_version=2,
        active_version=2,
        issues=(
            ValidationIssue(
                code=GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED.value,
                rule=RatchetRule.RR_1,
                stage_id="sanctions-attestation",
                message="The required stage 'Sanctions attestation' cannot be removed.",
            ),
        ),
    )
    return {
        "proposal_draft.json": _response(draft, can_edit=True, can_submit=True, can_withdraw=True),
        "proposal_pending_director_view.json": _response(pending, can_decide=True),
        "validation_report_valid.json": VALID,
        "validation_report_refused.json": refused,
        "simulation_scenarios.json": (scenario,),
        "simulation_result.json": SimulationResult(
            content_hash=HASH,
            outcomes=(
                SimulationOutcome(
                    scenario=scenario,
                    steps=(
                        *(
                            SimulatedStep(
                                node_id=node_id, name=label, added=False, blocks_send=False
                            )
                            for node_id, label in ONBOARDING_LOCKED_STAGES[:8]
                        ),
                        SimulatedStep(
                            node_id="sanctions-attestation",
                            name="Sanctions attestation",
                            added=True,
                            blocks_send=True,
                            required_field_labels=("Screened by", "Screening outcome"),
                        ),
                    ),
                    held_before_send=True,
                    summary="The send is held until 'Sanctions attestation' is confirmed.",
                ),
            ),
        ),
        "approvals_inbox.json": ApprovalInboxResponse(
            items=(
                ApprovalInboxItem(
                    workflow_id=ONBOARDING_WORKFLOW_ID,
                    workflow_name="Corporate onboarding",
                    use_case="Onboarding",
                    is_onboarding=True,
                    workflow_revision=7,
                    proposal=_response(pending, can_decide=True),
                    active_version=1,
                    changes=ChangeCounts(
                        stages_added=1,
                        stages_removed=0,
                        stages_changed=0,
                        fields_added=3,
                        fields_removed=0,
                        fields_changed=0,
                    ),
                    permanent_obligation_count=len(OBLIGATIONS),
                ),
            )
        ),
        "comparison.json": ComparisonResponse(
            workflow_id=ONBOARDING_WORKFLOW_ID,
            workflow_name="Corporate onboarding",
            is_onboarding=True,
            workflow_revision=7,
            proposal=_response(pending, can_decide=True),
            active_version=ACTIVE,
            active_provenance=LEGACY,
            stages=(
                StageDiff(
                    stage_id="sanctions-attestation",
                    change="ADDED",
                    name_before=None,
                    name_after="Sanctions attestation",
                    after_node_id_before=None,
                    after_node_id_after="OWNERSHIP_UBO",
                    blocks_send_before=False,
                    blocks_send_after=True,
                    fields=tuple(
                        FieldDiff(field_id=f.field_id, change="ADDED", before=None, after=f)
                        for f in SANCTIONS.fields
                    ),
                ),
            ),
            locked_stages=ONBOARDING_LOCKED_STAGES,
            validation=VALID,
            permanent_obligations=OBLIGATIONS,
            permanent_obligation_warning=PERMANENT_OBLIGATION_WARNING,
            affected_cases=AffectedCases(open_runs_on_active_version=4, counted_at=T1),
        ),
        "decision_request_approve.json": DecisionRequest(
            outcome=DecisionOutcome.APPROVE,
            reason="Required by the sanctions screening procedure.",
            expected_workflow_revision=7,
            expected_proposal_revision=3,
            content_hash=HASH,
            acknowledged_permanent_obligations=tuple(item.key for item in OBLIGATIONS),
        ),
        "decision_response_approved.json": DecisionResponse(
            proposal=_response(approved),
            workflow_revision=8,
            active_version=2,
            published_version=2,
            provenance=GOVERNED,
            publication_report=PublicationReport(
                published_version=2,
                cases_past_first_write_under_earlier_version=3,
                cases_authorised_under_earlier_version=1,
                cases_possibly_authorised=0,
                counted_at=T2,
            ),
        ),
        "workflow_governance_view.json": WorkflowGovernanceView(
            migrated=True,
            latest_version=2,
            open_proposal=None,
            decided_proposals=(),
            version_provenance=(LEGACY, GOVERNED),
            baseline=BaselineSummary(
                seeded_from_version=1,
                updated_at_version=2,
                required_stages=1,
                required_fields=2,
            ),
            recent_events=(
                GovernanceEvent(
                    sequence=5,
                    occurred_at=T2,
                    actor_id=DIRECTOR,
                    kind=GovernanceEventKind.VERSION_PUBLISHED,
                    proposal_id=PID,
                    version=2,
                    summary="Published version 2",
                ),
            ),
            unacknowledged_notices=(),
            can_create_proposal=True,
        ),
        "error_ratchet_removed.json": GovernanceErrorBody(
            code=GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED.value,
            message="A required step or field cannot be removed or made optional.",
            rule=RatchetRule.RR_1,
            issues=refused.issues,
        ),
        "error_acknowledgement_required.json": GovernanceErrorBody(
            code=GovernanceErrorCode.PERMANENT_OBLIGATION_ACK_REQUIRED.value,
            message="Confirm every permanent obligation before approving.",
        ),
        "error_self_decision.json": GovernanceErrorBody(
            code=GovernanceErrorCode.SELF_DECISION_REFUSED.value,
            message="You cannot decide a proposal you authored.",
        ),
        "error_history_unavailable.json": GovernanceErrorBody(
            code=GovernanceErrorCode.HISTORY_UNAVAILABLE.value,
            message="Workflow history is unavailable right now. Nothing was changed.",
        ),
    }


def render() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for name, value in fixtures().items():
        if isinstance(value, tuple):
            data: object = [item.model_dump(mode="json") for item in value]
        else:
            data = value.model_dump(mode="json")  # type: ignore[attr-defined]
        rendered[name] = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return rendered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    rendered = render()
    if args.check:
        stale = [
            name
            for name, text in rendered.items()
            if not (OUT / name).is_file() or (OUT / name).read_bytes().decode("utf-8") != text
        ]
        for name in stale:
            print(f"STALE {name}")
        return 1 if stale else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        (OUT / name).write_bytes(text.encode("utf-8"))
    print(f"wrote {len(rendered)} fixtures to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
