"""CT-9 (pure): the required-obligation ratchet, baseline, structure, budget, diff, safe target.

Synthetic data only. No I/O, no store, no provider.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.api_workflow_governance_models import ValidationIssue
from app.domain.workflow_governance import (
    MAX_ENCODED_VERSION_BYTES,
    GovernanceErrorCode,
    ObligationKey,
    PermanentObligationChange,
    ProposalKind,
    RatchetRule,
    RequiredBaseline,
    proposal_content_hash,
)
from app.domain.workflows import (
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
)
from app.services import workflow_ratchet as ratchet
from app.services.workflow_ratchet import (
    advance_baseline,
    applicability_issues,
    change_counts,
    encoded_version_bytes,
    field_signature,
    permanent_obligations,
    ratchet_issues,
    safe_target,
    seed_baseline,
    stage_diff,
    structure_issues,
    validate_candidate,
)

T0 = datetime(2026, 11, 17, tzinfo=UTC)
ANCHOR = "OWNERSHIP_UBO"
EMPTY = RequiredBaseline()


def text(field_id: str, label: str, *, required: bool = True, **extra: object) -> WorkflowField:
    return WorkflowField(
        field_id=field_id, label=label, kind=WorkflowFieldKind.TEXT, required=required, **extra
    )


def choice(field_id: str, label: str, *options: str, required: bool = True) -> WorkflowField:
    return WorkflowField(
        field_id=field_id,
        label=label,
        kind=WorkflowFieldKind.CHOICE,
        required=required,
        options=options,
    )


def stage(
    stage_id: str, name: str, *fields: WorkflowField, after: str | None = ANCHOR
) -> WorkflowStage:
    return WorkflowStage(stage_id=stage_id, name=name, fields=fields, after_node_id=after)


def version(number: int, *stages: WorkflowStage) -> WorkflowVersion:
    return WorkflowVersion(version=number, stages=stages, activated_at=T0, activated_by="dir-1")


SCREENED = text("screened-by", "Screened by")
OUTCOME = choice("outcome", "Screening outcome", "Clear", "Match", "Escalated")
NOTE = text("note", "Reviewer note", required=False)
SANCTIONS = stage("sanctions", "Sanctions attestation", SCREENED, OUTCOME, NOTE)
OPTIONAL = stage("extra", "Extra checks", text("info", "Info", required=False))
V1 = version(1, SANCTIONS, OPTIONAL)
BASE1 = seed_baseline(V1)


def with_fields(item: WorkflowStage, *fields: WorkflowField) -> WorkflowStage:
    return item.model_copy(update={"fields": fields})


def rules(issues: tuple[ValidationIssue, ...]) -> set[RatchetRule]:
    return {issue.rule for issue in issues if issue.rule is not None}


def check(
    *candidate: WorkflowStage,
    active: WorkflowVersion | None = V1,
    baseline: RequiredBaseline = BASE1,
) -> tuple[ValidationIssue, ...]:
    return ratchet_issues(candidate, active=active, baseline=baseline, is_onboarding=True)


# --- signatures and baseline ---


def test_field_signature_normalises_label_and_sorts_choice_options() -> None:
    signature = field_signature(choice("f", "  Screening,  OUTCOME! ", "Match", "clear", "Clear."))
    assert signature.normalised_label == "screening outcome"
    assert signature.choice_options == ("clear", "match")
    assert signature.has_case_data_key is False
    assert signature.applicability is None
    assert field_signature(text("t", "Text", case_data_key="LEGAL_NAME")).choice_options is None
    assert field_signature(text("t", "Text", case_data_key="LEGAL_NAME")).has_case_data_key


def test_seed_baseline_holds_only_required_obligations_of_the_active_version() -> None:
    assert BASE1.seeded_from_version == 1
    assert BASE1.updated_at_version == 1
    assert [s.stage_id for s in BASE1.stages] == ["sanctions"]
    entry = BASE1.stages[0]
    assert entry.normalised_name == "sanctions attestation"
    assert entry.representative_after_node_id == ANCHOR
    assert entry.first_published_version == entry.last_published_version == 1
    assert [f.field_id for f in entry.fields] == ["screened-by", "outcome"]
    assert entry.fields[1].signature.choice_options == ("clear", "escalated", "match")


def test_advance_baseline_intersects_choice_options_and_a_removed_option_never_returns() -> None:
    narrowed = with_fields(SANCTIONS, SCREENED, choice("outcome", "Screening outcome", "Clear"))
    base2 = advance_baseline(BASE1, version(2, narrowed))
    field = base2.stages[0].fields[1]
    assert field.signature.choice_options == ("clear",)
    assert field.representative.options == ("Clear",)
    assert base2.updated_at_version == 2 and base2.seeded_from_version == 1
    # Re-offering "Match" later is refused against the baseline (RR-6) even though the
    # active version would be fine if it had kept "Match".
    readded = with_fields(SANCTIONS, SCREENED, OUTCOME)
    assert RatchetRule.RR_6 in rules(check(readded, active=V1, baseline=base2))
    # A version that somehow re-published it still cannot widen the baseline.
    base3 = advance_baseline(base2, version(3, readded))
    assert base3.stages[0].fields[1].signature.choice_options == ("clear",)
    assert base3.stages[0].fields[1].representative.options == ("Clear",)


def test_advance_baseline_adds_obligations_keeps_kind_label_and_drops_case_data_key() -> None:
    keyed = text("name", "Legal name", case_data_key="LEGAL_NAME")
    v1 = version(1, stage("a", "Alpha", keyed))
    base = seed_baseline(v1)
    assert base.stages[0].fields[0].signature.has_case_data_key
    v2 = version(2, stage("a", "ALPHA!", text("name", "Legal Name")), stage("b", "Beta", SCREENED))
    base2 = advance_baseline(base, v2)
    alpha = base2.stages[0]
    assert alpha.normalised_name == "alpha"
    assert alpha.representative_name == "ALPHA!"  # latest version's representative
    assert alpha.first_published_version == 1 and alpha.last_published_version == 2
    assert alpha.fields[0].signature.has_case_data_key is False
    assert alpha.fields[0].representative.case_data_key is None
    assert [s.stage_id for s in base2.stages] == ["a", "b"]
    # Once absent, a re-published key is not taken back into the signature or representative.
    base3 = advance_baseline(base2, version(3, stage("a", "Alpha", keyed), v2.stages[1]))
    assert base3.stages[0].fields[0].signature.has_case_data_key is False
    assert base3.stages[0].fields[0].representative.case_data_key is None


def test_advance_baseline_never_loses_an_obligation_and_refuses_going_backwards() -> None:
    base2 = advance_baseline(BASE1, version(2, OPTIONAL))  # sanctions missing (never allowed)
    assert base2.stages == BASE1.stages
    with pytest.raises(ValueError):
        advance_baseline(base2, version(2, SANCTIONS))


# --- structure ---


def test_structure_issues_ports_existing_rules_as_issues() -> None:
    dup_stage = (SANCTIONS, SANCTIONS)
    assert [i.code for i in structure_issues(dup_stage, is_onboarding=True)] == [
        "WORKFLOW_DUPLICATE_ID"
    ]
    dup_field = (with_fields(SANCTIONS, SCREENED, SCREENED),)
    issue = structure_issues(dup_field, is_onboarding=True)[0]
    assert (issue.code, issue.field_id) == ("WORKFLOW_DUPLICATE_ID", "screened-by")
    codes = {
        i.code
        for i in structure_issues(
            (
                stage("a", "A", after=None),
                stage("b", "B", choice("c", "C"), after="FINAL_REVIEW_SEND"),
                stage("d", "D", text("e", "E", autofill=True)),
            ),
            is_onboarding=True,
        )
    }
    assert codes == {
        "WORKFLOW_STAGE_POSITION_INVALID",
        "WORKFLOW_FIELD_REQUIRED",
        "WORKFLOW_OPTIONS_REQUIRED",
        "WORKFLOW_AUTOFILL_INVALID",
    }
    anchored = structure_issues((stage("a", "A", SCREENED),), is_onboarding=False)
    assert [i.code for i in anchored] == ["WORKFLOW_STAGE_POSITION_INVALID"]
    assert structure_issues((SANCTIONS,), is_onboarding=True) == ()


def test_empty_non_onboarding_candidate_is_proposal_empty_but_empty_onboarding_is_not() -> None:
    issues = structure_issues((), is_onboarding=False)
    assert [i.code for i in issues] == [GovernanceErrorCode.PROPOSAL_EMPTY.value]
    assert structure_issues((), is_onboarding=True) == ()
    report = validate_candidate(
        (), active=None, baseline=EMPTY, is_onboarding=False, base_version=0, active_version=0
    )
    assert not report.valid


def test_labels_that_normalise_to_nothing_are_invalid() -> None:
    issues = structure_issues((stage("a", "!!!", text("b", "?")),), is_onboarding=True)
    assert [(i.code, i.field_id) for i in issues] == [
        ("WORKFLOW_PROPOSAL_INVALID", None),
        ("WORKFLOW_PROPOSAL_INVALID", "b"),
    ]


# --- RR-1 to RR-10 refused ---


def test_rr1_required_stage_missing() -> None:
    issues = check(OPTIONAL)
    assert rules(issues) == {RatchetRule.RR_1}
    assert issues[0].code == GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED.value
    assert issues[0].stage_id == "sanctions"


def test_rr2_required_stage_no_longer_blocks_the_send() -> None:
    weakened = with_fields(
        SANCTIONS,
        SCREENED.model_copy(update={"required": False}),
        OUTCOME.model_copy(update={"required": False}),
    )
    found = check(weakened)
    assert {RatchetRule.RR_2, RatchetRule.RR_3} == rules(found)
    rr2 = next(i for i in found if i.rule == RatchetRule.RR_2)
    assert rr2.code == GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED.value


def test_rr3_required_field_missing_or_optional() -> None:
    missing = check(with_fields(SANCTIONS, OUTCOME))
    optional = check(
        with_fields(SANCTIONS, SCREENED.model_copy(update={"required": False}), OUTCOME)
    )
    for found in (missing, optional):
        assert rules(found) == {RatchetRule.RR_3}
        assert found[0].field_id == "screened-by"
        assert found[0].code == GovernanceErrorCode.REQUIRED_OBLIGATION_REMOVED.value


def test_rr4_kind_changed() -> None:
    changed = SCREENED.model_copy(update={"kind": WorkflowFieldKind.DATE})
    assert rules(check(with_fields(SANCTIONS, changed, OUTCOME))) == {RatchetRule.RR_4}


def test_rr5_normalised_label_changed_but_cosmetic_change_allowed() -> None:
    renamed = SCREENED.model_copy(update={"label": "Checked by"})
    assert rules(check(with_fields(SANCTIONS, renamed, OUTCOME))) == {RatchetRule.RR_5}
    cosmetic = SCREENED.model_copy(update={"label": "SCREENED   by."})
    assert check(with_fields(SANCTIONS, cosmetic, OUTCOME)) == ()


def test_rr6_choice_option_outside_the_intersection() -> None:
    widened = choice("outcome", "Screening outcome", "Clear", "Match", "Escalated", "Waived")
    found = check(with_fields(SANCTIONS, SCREENED, widened))
    assert rules(found) == {RatchetRule.RR_6}
    assert found[0].code == GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED.value


def test_rr7_required_field_gaining_a_case_data_key() -> None:
    keyed = SCREENED.model_copy(update={"case_data_key": "LEGAL_NAME"})
    assert rules(check(with_fields(SANCTIONS, keyed, OUTCOME))) == {RatchetRule.RR_7}


def test_rr8_is_an_inert_hook_until_adr_018() -> None:
    assert applicability_issues((SANCTIONS,), BASE1) == ()
    assert all(f.signature.applicability is None for s in BASE1.stages for f in s.fields)


@pytest.mark.parametrize(
    ("candidate", "is_onboarding"),
    [
        (stage("case-start", "Sanctions review", SCREENED), True),  # id of a locked node
        (stage("my-step", "Final review & send", SCREENED), True),  # locked label
        (stage("my-step", "ownership ubo", SCREENED), True),  # locked node id as words
        (stage("my-step", "Late step", SCREENED, after="FINAL_REVIEW_SEND"), True),
        (stage("my-step", "Unplaced", SCREENED, after=None), True),
        (stage("my-step", "Unknown anchor", SCREENED, after="NOT_A_NODE"), True),
        (stage("my-step", "Anchored", SCREENED), False),
    ],
)
def test_rr9_code_owned_stages_and_engine_order(
    candidate: WorkflowStage, is_onboarding: bool
) -> None:
    found = ratchet_issues((candidate,), active=None, baseline=EMPTY, is_onboarding=is_onboarding)
    assert rules(found) == {RatchetRule.RR_9}
    assert found[0].code == GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED.value


def test_rr10_required_stage_renamed() -> None:
    renamed = SANCTIONS.model_copy(update={"name": "Sanctions check"})
    assert rules(check(renamed)) == {RatchetRule.RR_10}


def test_every_violation_is_reported_once_with_message_and_ids() -> None:
    bad = SANCTIONS.model_copy(
        update={
            "name": "Renamed",
            "fields": (
                SCREENED.model_copy(update={"kind": WorkflowFieldKind.NUMBER, "label": "Other"}),
                choice("outcome", "Screening outcome", "Clear", "Waived"),
            ),
        }
    )
    found = check(bad)
    assert rules(found) == {
        RatchetRule.RR_4,
        RatchetRule.RR_5,
        RatchetRule.RR_6,
        RatchetRule.RR_10,
    }
    keys = [(i.rule, i.stage_id, i.field_id) for i in found]
    assert len(keys) == len(set(keys))  # active and baseline violations deduplicated
    assert all(0 < len(i.message) <= 240 for i in found)


# --- checks against both the active version and the baseline ---


def test_candidate_fine_against_active_but_weaker_than_baseline_is_refused() -> None:
    # The baseline remembers an obligation the active version no longer shows (e.g. after
    # deactivation and reactivation, or an emergency fallback).
    weaker_active = version(2, OPTIONAL)
    assert check(OPTIONAL, active=weaker_active, baseline=EMPTY) == ()
    found = check(OPTIONAL, active=weaker_active, baseline=BASE1)
    assert rules(found) == {RatchetRule.RR_1}


def test_candidate_fine_against_baseline_but_weaker_than_active_is_refused() -> None:
    found = check(OPTIONAL, active=V1, baseline=EMPTY)
    assert rules(found) == {RatchetRule.RR_1}


def test_interleaved_stricter_publication_refuses_a_candidate_prepared_earlier() -> None:
    # Prepared against v1: keeps "Match" and adds nothing.
    prepared = (with_fields(SANCTIONS, SCREENED, OUTCOME, NOTE), OPTIONAL)
    assert check(*prepared) == ()
    # Meanwhile v2 narrows the options and makes the note required.
    stricter = with_fields(
        SANCTIONS,
        SCREENED,
        choice("outcome", "Screening outcome", "Clear", "Escalated"),
        NOTE.model_copy(update={"required": True}),
    )
    v2 = version(2, stricter, OPTIONAL)
    base2 = advance_baseline(BASE1, v2)
    found = check(*prepared, active=v2, baseline=base2)
    assert rules(found) == {RatchetRule.RR_3, RatchetRule.RR_6}


# --- allowed changes ---


@pytest.mark.parametrize(
    "candidate",
    [
        (SANCTIONS, OPTIONAL, stage("new", "New step", text("n", "New field"))),  # new stage
        (with_fields(SANCTIONS, SCREENED, OUTCOME, NOTE, text("n2", "Extra")), OPTIONAL),
        (with_fields(SANCTIONS, SCREENED, OUTCOME, NOTE.model_copy(update={"required": True})),),
        (with_fields(SANCTIONS, SCREENED, choice("outcome", "Screening outcome", "Clear")),),
        (SANCTIONS.model_copy(update={"after_node_id": "ADVISORY"}),),  # moved to legal anchor
        (with_fields(SANCTIONS, SCREENED, OUTCOME, NOTE.model_copy(update={"label": "X"})),),
        (SANCTIONS,),  # optional stage deleted
        (with_fields(SANCTIONS, SCREENED, OUTCOME), OPTIONAL),  # optional field deleted
    ],
)
def test_allowed_changes_pass(candidate: tuple[WorkflowStage, ...]) -> None:
    report = validate_candidate(
        candidate, active=V1, baseline=BASE1, is_onboarding=True, base_version=1, active_version=1
    )
    assert report.valid, report.issues
    assert report.issues == ()


def test_existing_case_data_key_may_be_kept() -> None:
    keyed = text("name", "Legal name", case_data_key="LEGAL_NAME")
    v1 = version(1, stage("a", "Alpha", keyed, after=None))
    base = seed_baseline(v1)
    found = ratchet_issues(v1.stages, active=v1, baseline=base, is_onboarding=False)
    assert found == ()


def test_non_onboarding_with_nothing_active_checks_the_baseline_only() -> None:
    plain = stage("a", "Alpha", SCREENED, after=None)
    base = seed_baseline(version(1, plain))
    assert ratchet_issues((plain,), active=None, baseline=base, is_onboarding=False) == ()
    found = ratchet_issues(
        (stage("b", "Beta", SCREENED, after=None),),
        active=None,
        baseline=base,
        is_onboarding=False,
    )
    assert rules(found) == {RatchetRule.RR_1}


# --- permanent obligations ---


def test_permanent_obligations_new_and_tightened_in_candidate_order() -> None:
    candidate = (
        with_fields(
            SANCTIONS,
            SCREENED,
            choice("outcome", "Screening outcome", "Clear", "Match"),  # narrowed
            NOTE.model_copy(update={"required": True}),  # optional -> required
            text("added", "Added field"),  # new required field in known stage
        ),
        with_fields(OPTIONAL, text("info", "Info")),  # optional stage becomes required
        stage("fresh", "Fresh step", text("f1", "One"), text("f2", "Two", required=False)),
    )
    found = permanent_obligations(candidate, active=V1, baseline=BASE1)
    assert [(o.key.stage_id, o.key.field_id, o.change) for o in found] == [
        ("sanctions", "outcome", PermanentObligationChange.TIGHTENED),
        ("sanctions", "note", PermanentObligationChange.TIGHTENED),
        ("sanctions", "added", PermanentObligationChange.NEW_REQUIRED_FIELD),
        ("extra", None, PermanentObligationChange.TIGHTENED),
        ("extra", "info", PermanentObligationChange.TIGHTENED),
        ("fresh", None, PermanentObligationChange.NEW_REQUIRED_STAGE),
        ("fresh", "f1", PermanentObligationChange.NEW_REQUIRED_FIELD),
    ]
    assert found[0].stage_name == "Sanctions attestation"
    assert found[0].field_label == "Screening outcome"
    assert found[3].field_label is None
    assert all(len(o.detail) <= 240 for o in found)
    assert permanent_obligations(candidate, active=V1, baseline=BASE1) == found


def test_unchanged_candidate_has_no_permanent_obligations() -> None:
    assert permanent_obligations(V1.stages, active=V1, baseline=BASE1) == ()


def test_validate_candidate_report_combines_everything() -> None:
    candidate = (OPTIONAL, stage("fresh", "Fresh", text("f", "F")))
    report = validate_candidate(
        candidate,
        active=V1,
        baseline=BASE1,
        is_onboarding=True,
        base_version=1,
        active_version=1,
    )
    assert not report.valid
    assert report.content_hash == proposal_content_hash(ProposalKind.CHANGE, candidate)
    assert report.encoded_bytes == encoded_version_bytes(candidate)
    assert report.max_encoded_bytes == MAX_ENCODED_VERSION_BYTES
    assert (report.base_version, report.active_version) == (1, 1)
    assert rules(report.issues) == {RatchetRule.RR_1}
    assert [o.key for o in report.permanent_obligations] == [
        ObligationKey(stage_id="fresh"),
        ObligationKey(stage_id="fresh", field_id="f"),
    ]


# --- byte budget ---


def test_encoded_version_bytes_is_bson_size_and_grows_with_content() -> None:
    small = encoded_version_bytes(())
    assert small > 0
    assert encoded_version_bytes((SANCTIONS,)) > small


def test_too_large_candidate_is_refused() -> None:
    long = "L" * 80
    fields = tuple(
        WorkflowField(
            field_id=f"f{i}",
            label=f"{long[:76]}{i:04d}",
            kind=WorkflowFieldKind.CHOICE,
            options=tuple(f"{long[:76]}{j:04d}" for j in range(32)),
            document_label=long,
        )
        for i in range(32)
    )
    stages = tuple(stage(f"s{i}", f"{long[:76]}{i:04d}", *fields) for i in range(32))
    report = validate_candidate(
        stages, active=None, baseline=EMPTY, is_onboarding=True, base_version=0, active_version=0
    )
    assert report.encoded_bytes > MAX_ENCODED_VERSION_BYTES
    assert [i.code for i in report.issues] == [GovernanceErrorCode.PROPOSAL_TOO_LARGE.value]
    assert not report.valid


def test_budget_boundary() -> None:
    assert ratchet.budget_issues(MAX_ENCODED_VERSION_BYTES) == ()
    issue = ratchet.budget_issues(MAX_ENCODED_VERSION_BYTES + 1)[0]
    assert issue.code == GovernanceErrorCode.PROPOSAL_TOO_LARGE.value
    assert len(issue.message) <= 240


# --- diff and counts ---


def test_stage_diff_and_change_counts() -> None:
    changed = with_fields(
        SANCTIONS,
        SCREENED,
        choice("outcome", "Screening outcome", "Clear"),
        text("added", "Added"),
    )
    fresh = stage("fresh", "Fresh", text("f", "F"))
    diffs = stage_diff(V1.stages, (changed, fresh))
    assert [(d.stage_id, d.change) for d in diffs] == [
        ("sanctions", "CHANGED"),
        ("fresh", "ADDED"),
        ("extra", "REMOVED"),
    ]
    sanctions = diffs[0]
    assert [(f.field_id, f.change) for f in sanctions.fields] == [
        ("screened-by", "UNCHANGED"),
        ("outcome", "CHANGED"),
        ("added", "ADDED"),
        ("note", "REMOVED"),
    ]
    assert sanctions.blocks_send_before and sanctions.blocks_send_after
    assert diffs[1].name_before is None and not diffs[1].blocks_send_before
    assert diffs[2].name_after is None and not diffs[2].blocks_send_after
    counts = change_counts(diffs)
    assert counts.model_dump() == {
        "stages_added": 1,
        "stages_removed": 1,
        "stages_changed": 1,
        "fields_added": 2,
        "fields_removed": 2,
        "fields_changed": 1,
    }
    unchanged = stage_diff(V1.stages, V1.stages)
    assert {d.change for d in unchanged} == {"UNCHANGED"}
    assert change_counts(unchanged).model_dump() == dict.fromkeys(counts.model_dump(), 0)


# --- safe target ---


def test_safe_target_is_base_union_baseline_with_baseline_signatures() -> None:
    narrowed = with_fields(SANCTIONS, SCREENED, choice("outcome", "Screening outcome", "Clear"))
    later = stage("later", "Later step", text("l", "Later field"), after="ADVISORY")
    base2 = advance_baseline(BASE1, version(2, narrowed, later))
    # Restore an earlier base that offered "Match", lacked "later" and had an optional stage.
    target = safe_target(V1.stages, base2)
    assert [s.stage_id for s in target] == ["sanctions", "extra", "later"]
    restored = target[0]
    outcome = next(f for f in restored.fields if f.field_id == "outcome")
    assert outcome.options == ("Clear",)
    assert [f.field_id for f in restored.fields] == ["screened-by", "outcome", "note"]
    assert target[2].after_node_id == "ADVISORY"
    v3 = version(3, *target)
    assert ratchet_issues(target, active=v3, baseline=base2, is_onboarding=True) == ()
    assert structure_issues(target, is_onboarding=True) == ()


def test_safe_target_restores_a_dropped_required_field() -> None:
    base_without = (with_fields(SANCTIONS, OUTCOME),)
    target = safe_target(base_without, BASE1)
    assert [f.field_id for f in target[0].fields] == ["outcome", "screened-by"]
    assert ratchet_issues(target, active=None, baseline=BASE1, is_onboarding=True) == ()
    assert safe_target((), EMPTY) == ()
