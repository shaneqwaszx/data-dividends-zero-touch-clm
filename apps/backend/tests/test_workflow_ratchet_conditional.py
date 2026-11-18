"""ADR-018 ratchet (M3): CT-22, CT-27, CT-30 (ratchet half), CT-35 (ratchet half), B6, B9.

Synthetic data only. No I/O, no store, no provider.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

import pytest

from app.api_workflow_governance_models import ValidationIssue
from app.domain.registry_legal_form import ConditionalLegalForm as F
from app.domain.workflow_governance import (
    CONDITIONAL_BEFORE_REGISTRY_ISSUE,
    CONDITIONAL_FIELD_OUTSIDE_STAGE_ISSUE,
    CONDITIONAL_FULL_SET_ISSUE,
    CONDITIONAL_NON_ONBOARDING_MINIMUM_ISSUE,
    CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE,
    GovernanceErrorCode,
    ObligationKey,
    PermanentObligationChange,
    RatchetRule,
    RequiredBaseline,
)
from app.domain.workflows import (
    AppliesTo,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
)
from app.services.workflow_ratchet import (
    SafeTargetError,
    advance_baseline,
    field_signature,
    permanent_obligations,
    ratchet_issues,
    safe_target,
    seed_baseline,
    structure_issues,
    validate_candidate,
)

T0 = datetime(2026, 11, 18, tzinfo=UTC)
EMPTY = RequiredBaseline()
LLP: AppliesTo = (F.LLP,)
LLP_LP: AppliesTo = (F.LLP, F.LP)
INVALID = GovernanceErrorCode.PROPOSAL_INVALID.value


def fld(
    field_id: str, *, required: bool = True, applies_to: AppliesTo | None = None
) -> WorkflowField:
    return WorkflowField(
        field_id=field_id,
        label=f"Field {field_id}",
        kind=WorkflowFieldKind.TEXT,
        required=required,
        applies_to=applies_to,
    )


def stg(
    stage_id: str,
    *fields: WorkflowField,
    applies_to: AppliesTo | None = None,
    after: str | None = "OWNERSHIP_UBO",
    name: str | None = None,
) -> WorkflowStage:
    return WorkflowStage(
        stage_id=stage_id,
        name=name or f"Stage {stage_id}",
        fields=fields,
        applies_to=applies_to,
        after_node_id=after,
    )


def ver(number: int, *stages: WorkflowStage) -> WorkflowVersion:
    return WorkflowVersion(version=number, stages=stages, activated_at=T0, activated_by="dir-1")


def rr8(issues: tuple[ValidationIssue, ...]) -> list[ValidationIssue]:
    return [issue for issue in issues if issue.rule == RatchetRule.RR_8]


def check(
    *candidate: WorkflowStage,
    active: WorkflowVersion | None,
    baseline: RequiredBaseline,
    onboarding: bool = True,
) -> tuple[ValidationIssue, ...]:
    return ratchet_issues(candidate, active=active, baseline=baseline, is_onboarding=onboarding)


# A conditional required stage (LLP, LP) whose field inherits it, and an ALL stage whose
# required field is LLP-only.
COND = stg("cond", fld("a"), applies_to=LLP_LP)
PLAIN = stg("plain", fld("x"), fld("y", applies_to=LLP))
V1 = ver(1, COND, PLAIN)
B1 = seed_baseline(V1)


# --- signatures and baseline (CT-22: baseline union) ---


def test_field_signature_holds_the_effective_applicability() -> None:
    assert field_signature(fld("a")).applicability is None
    assert field_signature(fld("a"), stage_applies_to=LLP_LP).applicability == LLP_LP
    assert field_signature(fld("a", applies_to=LLP), stage_applies_to=LLP_LP).applicability == LLP
    entry = B1.stages[0]
    assert entry.applicability == LLP_LP
    assert entry.fields[0].signature.applicability == LLP_LP
    assert entry.fields[0].representative.applies_to is None  # inherits the baseline stage
    assert B1.stages[1].applicability is None
    assert B1.stages[1].fields[1].signature.applicability == LLP


def test_unconditional_baseline_dumps_are_unchanged() -> None:
    base = seed_baseline(ver(1, stg("s", fld("a"))))
    dumped = base.model_dump(mode="json")
    assert "applicability" not in dumped["stages"][0]
    assert dumped["stages"][0]["fields"][0]["signature"]["applicability"] is None
    assert "applies_to" not in dumped["stages"][0]["fields"][0]["representative"]


def test_baseline_keeps_the_broadest_applicability_ever_published() -> None:
    narrow = ver(1, stg("s", fld("a"), applies_to=LLP))
    base = seed_baseline(narrow)
    broad = advance_baseline(base, ver(2, stg("s", fld("a"), applies_to=LLP_LP)))
    assert broad.stages[0].applicability == LLP_LP
    assert broad.stages[0].fields[0].signature.applicability == LLP_LP
    # A later narrower publication (one that bypassed the ratchet) cannot narrow it.
    again = advance_baseline(broad, ver(3, stg("s", fld("a"), applies_to=LLP)))
    assert again.stages[0].applicability == LLP_LP
    # ALL absorbs every set.
    everyone = advance_baseline(again, ver(4, stg("s", fld("a"))))
    assert everyone.stages[0].applicability is None
    assert everyone.stages[0].fields[0].signature.applicability is None
    later = advance_baseline(everyone, ver(5, stg("s", fld("a"), applies_to=LLP)))
    assert later.stages[0].applicability is None


def test_union_naming_every_form_becomes_all() -> None:
    base = seed_baseline(ver(1, stg("s", fld("a"), applies_to=(F.COMPANY, F.LLP))))
    rest = (F.BUSINESS_PARTNERSHIP, F.GOVERNMENT, F.LP)
    base = advance_baseline(base, ver(2, stg("s", fld("a"), applies_to=rest)))
    assert base.stages[0].applicability is None


def test_representative_stays_exact_when_its_stage_broadens() -> None:
    v1 = ver(1, stg("s", fld("a"), fld("b"), applies_to=LLP))
    base = seed_baseline(v1)
    # v2 broadens the stage; "b" keeps its own LLP-only applicability explicitly.
    v2 = ver(2, stg("s", fld("a"), fld("b", applies_to=LLP), applies_to=LLP_LP))
    base2 = advance_baseline(base, v2)
    a, b = base2.stages[0].fields
    assert a.signature.applicability == LLP_LP and a.representative.applies_to is None
    assert b.signature.applicability == LLP and b.representative.applies_to == LLP
    # A field not republished (input that bypassed RR-3) is re-rendered, never broadened.
    base3 = advance_baseline(base, ver(2, stg("s", fld("a"), applies_to=LLP_LP)))
    kept = base3.stages[0].fields[1]
    assert kept.signature.applicability == LLP and kept.representative.applies_to == LLP


# --- RR-8 matrix (CT-22) ---


def test_rr8a_stage_narrowed_against_baseline_and_active() -> None:
    narrowed = stg("cond", fld("a"), applies_to=LLP)
    for active, baseline in ((V1, EMPTY), (None, B1), (V1, B1)):
        found = rr8(check(narrowed, PLAIN, active=active, baseline=baseline))
        assert [(i.stage_id, i.field_id) for i in found] == [("cond", None), ("cond", "a")]
        assert found[0].code == GovernanceErrorCode.REQUIRED_OBLIGATION_WEAKENED.value
        assert "fewer legal forms" in found[0].message
        assert "step's legal forms narrowed" in found[1].message  # RR-8c


def test_rr8b_unconditional_stage_and_field_cannot_become_conditional() -> None:
    v1 = ver(1, stg("s", fld("a"), fld("b")))
    base = seed_baseline(v1)
    stage_made_conditional = stg("s", fld("a"), fld("b"), applies_to=LLP)
    found = rr8(check(stage_made_conditional, active=v1, baseline=base))
    assert [(i.stage_id, i.field_id) for i in found] == [("s", None), ("s", "a"), ("s", "b")]
    assert "cannot become conditional" in found[0].message
    field_made_conditional = stg("s", fld("a", applies_to=LLP), fld("b"))
    found = rr8(check(field_made_conditional, active=v1, baseline=base))
    assert [(i.field_id, "cannot become conditional" in i.message) for i in found] == [("a", True)]


def test_rr8a_field_narrowed() -> None:
    v1 = ver(1, stg("s", fld("a", applies_to=LLP_LP)))
    found = rr8(check(stg("s", fld("a", applies_to=LLP)), active=v1, baseline=seed_baseline(v1)))
    assert [(i.field_id, "fewer legal forms" in i.message) for i in found] == [("a", True)]


def test_rr8c_field_narrowed_through_its_stage_only() -> None:
    v1 = ver(1, stg("s", fld("a"), fld("b", applies_to=LLP), applies_to=LLP_LP))
    base = seed_baseline(v1)
    # The field's own applies_to is unchanged (inherits); its stage narrowed.
    candidate = stg("s", fld("a"), fld("b", applies_to=LLP), applies_to=LLP)
    found = rr8(check(candidate, active=v1, baseline=base))
    assert [(i.stage_id, i.field_id) for i in found] == [("s", None), ("s", "a")]
    assert "step's legal forms narrowed" in found[1].message


@pytest.mark.parametrize(
    "candidate",
    [
        (stg("cond", fld("a"), applies_to=(F.COMPANY, F.LLP, F.LP)), PLAIN),  # adds a form
        (stg("cond", fld("a")), PLAIN),  # set -> ALL
        (COND, stg("plain", fld("x"), fld("y"))),  # field set -> ALL
        (COND, PLAIN, stg("new", fld("n"), applies_to=LLP)),  # new conditional stage
        (stg("cond", fld("a"), fld("c", applies_to=(F.LP,)), applies_to=LLP_LP), PLAIN),
        (COND, PLAIN, stg("opt", fld("o", required=False), applies_to=LLP)),  # optional
    ],
)
def test_rr8_allowed_changes(candidate: tuple[WorkflowStage, ...]) -> None:
    report = validate_candidate(
        candidate, active=V1, baseline=B1, is_onboarding=True, base_version=1, active_version=1
    )
    assert report.valid, report.issues


def test_optional_conditional_becoming_required_is_allowed() -> None:
    v1 = ver(1, stg("s", fld("a"), fld("b", required=False, applies_to=LLP)))
    candidate = (stg("s", fld("a"), fld("b", applies_to=LLP)),)
    report = validate_candidate(
        candidate,
        active=v1,
        baseline=seed_baseline(v1),
        is_onboarding=True,
        base_version=1,
        active_version=1,
    )
    assert report.valid, report.issues
    assert [(o.key.field_id, o.change) for o in report.permanent_obligations] == [
        ("b", PermanentObligationChange.TIGHTENED)
    ]
    assert "Applies to: LLP" in report.permanent_obligations[0].detail


def test_interleaved_broader_publication_refuses_a_candidate_prepared_earlier() -> None:
    prepared = (COND, PLAIN)  # prepared against v1: LLP, LP
    assert rr8(check(*prepared, active=V1, baseline=B1)) == []
    broader = stg("cond", fld("a"), applies_to=(F.COMPANY, F.LLP, F.LP))
    v2 = ver(2, broader, PLAIN)
    b2 = advance_baseline(B1, v2)
    found = rr8(check(*prepared, active=v2, baseline=b2))
    assert [(i.stage_id, i.field_id) for i in found] == [("cond", None), ("cond", "a")]


def test_deactivate_then_reactivate_must_satisfy_the_baseline() -> None:
    # After deactivation nothing is active; the baseline alone still refuses narrowing.
    narrowed = (stg("cond", fld("a"), applies_to=LLP), PLAIN)
    assert rr8(check(*narrowed, active=None, baseline=B1, onboarding=True))
    assert check(COND, PLAIN, active=None, baseline=B1) == ()


def test_active_narrower_than_baseline_still_checks_the_baseline() -> None:
    # e.g. an earlier version re-activated without the later broadening.
    broader = stg("cond", fld("a"), applies_to=(F.COMPANY, F.LLP, F.LP))
    b2 = advance_baseline(B1, ver(2, broader, PLAIN))
    assert rr8(check(*V1.stages, active=V1, baseline=EMPTY)) == []
    assert rr8(check(*V1.stages, active=V1, baseline=b2))


def test_unconditional_content_has_no_rr8_issue() -> None:
    v1 = ver(1, stg("s", fld("a")))
    assert check(stg("s", fld("a")), active=v1, baseline=seed_baseline(v1)) == ()


# --- safe targets (CT-22, CT-30 ratchet half) ---


def test_safe_target_widens_a_narrower_base_to_the_baseline() -> None:
    broader = stg("cond", fld("a"), applies_to=(F.COMPANY, F.LLP, F.LP))
    plain2 = stg("plain", fld("x"), fld("y", applies_to=LLP_LP))
    v2 = ver(2, broader, plain2)
    b2 = advance_baseline(B1, v2)
    target = safe_target(V1.stages, b2)  # base v1 is narrower
    by_id = {s.stage_id: s for s in target}
    assert by_id["cond"].applies_to == (F.COMPANY, F.LLP, F.LP)
    assert by_id["cond"].fields[0].applies_to is None
    assert by_id["plain"].applies_to is None
    assert by_id["plain"].fields[1].applies_to == LLP_LP
    # Never broadens beyond the baseline: no permanent obligation, no ratchet issue.
    assert permanent_obligations(target, active=v2, baseline=b2) == ()
    assert ratchet_issues(target, active=v2, baseline=b2, is_onboarding=True) == ()


def test_safe_target_adds_missing_conditional_obligations_with_baseline_applicability() -> None:
    target = safe_target((), B1)
    assert [(s.stage_id, s.applies_to) for s in target] == [("cond", LLP_LP), ("plain", None)]
    assert target[1].fields[1].applies_to == LLP
    assert permanent_obligations(target, active=V1, baseline=B1) == ()


def test_safe_target_refuses_a_base_broader_than_the_baseline() -> None:
    # v1: an optional stage for all entities; v2: the stage narrows to LLP and gains a new
    # required field. Restoring v1 would either broaden the obligation or narrow v1.
    v1 = ver(1, stg("s", fld("o", required=False)))
    v2 = ver(2, stg("s", fld("o", required=False), fld("r"), applies_to=LLP))
    base = advance_baseline(seed_baseline(v1), v2)
    with pytest.raises(SafeTargetError) as caught:
        safe_target(v1.stages, base)
    assert caught.value.code == INVALID


def test_safe_target_refuses_an_optional_base_field_outside_the_baseline_stage() -> None:
    v1 = ver(
        1,
        stg(
            "s",
            fld("r"),
            fld("o", required=False, applies_to=(F.LP,)),
            applies_to=(
                F.LLP,
                F.LP,
            ),
        ),
    )
    base = seed_baseline(ver(1, stg("s", fld("r"), applies_to=LLP)))
    with pytest.raises(SafeTargetError):
        safe_target(v1.stages, base)


def test_safe_target_never_broadens_beyond_the_baseline_property() -> None:
    forms: list[AppliesTo | None] = [None, LLP, LLP_LP, (F.COMPANY,), (F.COMPANY, F.LLP)]
    for first, second in itertools.product(forms, repeat=2):
        v1 = ver(1, stg("s", fld("a"), applies_to=first))
        base = seed_baseline(v1)
        v2 = ver(2, stg("s", fld("a"), applies_to=second))
        if ratchet_issues(v2.stages, active=v1, baseline=base, is_onboarding=True):
            continue  # a narrowing publication is never approved
        base2 = advance_baseline(base, v2)
        for earlier in (v1, v2):
            target = safe_target(earlier.stages, base2)
            assert target[0].applies_to == base2.stages[0].applicability
            assert permanent_obligations(target, active=v2, baseline=base2) == ()
            # Publishing the safe target leaves every baseline signature unchanged.
            base3 = advance_baseline(base2, ver(3, *target))
            assert [(s.applicability, [f.signature for f in s.fields]) for s in base3.stages] == [
                (s.applicability, [f.signature for f in s.fields]) for s in base2.stages
            ]


# --- permanent obligations (CT-27) ---


def test_new_conditional_obligations_are_listed_with_their_applicability() -> None:
    candidate = (COND, PLAIN, stg("new", fld("n"), applies_to=LLP_LP))
    found = permanent_obligations(candidate, active=V1, baseline=B1)
    assert [(o.key, o.change) for o in found] == [
        (ObligationKey(stage_id="new"), PermanentObligationChange.NEW_REQUIRED_STAGE),
        (
            ObligationKey(stage_id="new", field_id="n"),
            PermanentObligationChange.NEW_REQUIRED_FIELD,
        ),
    ]
    expected = "Applies to: LLP, LP, and any entity whose legal form is not verified."
    assert all(expected in o.detail for o in found)
    plain_new = permanent_obligations((stg("p", fld("q")),), active=None, baseline=EMPTY)
    assert "Applies to" not in plain_new[0].detail


def test_broadening_is_an_applicability_broadened_obligation() -> None:
    candidate = (
        stg("cond", fld("a"), applies_to=(F.COMPANY, F.LLP, F.LP)),
        stg("plain", fld("x"), fld("y")),
    )
    found = permanent_obligations(candidate, active=V1, baseline=B1)
    assert [(o.key.stage_id, o.key.field_id, o.change) for o in found] == [
        ("cond", None, PermanentObligationChange.APPLICABILITY_BROADENED),
        ("cond", "a", PermanentObligationChange.APPLICABILITY_BROADENED),
        ("plain", "y", PermanentObligationChange.APPLICABILITY_BROADENED),
    ]
    assert "applies to more entities" in found[0].detail
    assert "Applies to all entities." in found[2].detail
    assert all(len(o.detail) <= 240 for o in found)


def test_broadened_and_tightened_field_is_one_tightened_obligation() -> None:
    choice = WorkflowField(
        field_id="c",
        label="Kind",
        kind=WorkflowFieldKind.CHOICE,
        options=("A", "B"),
        applies_to=LLP,
    )
    v1 = ver(1, stg("s", choice))
    narrowed = choice.model_copy(update={"options": ("A",), "applies_to": LLP_LP})
    found = permanent_obligations((stg("s", narrowed),), active=v1, baseline=seed_baseline(v1))
    assert len(found) == 1 and found[0].change == PermanentObligationChange.TIGHTENED
    assert "fewer options" in found[0].detail and "more entities" in found[0].detail


# --- structure: anchors (CT-35), B6, B9, canonical form ---


@pytest.mark.parametrize(
    "candidate",
    [
        stg("c", fld("a"), applies_to=LLP, after="CASE_START"),
        stg("c", fld("a"), applies_to=LLP, after="GOLDTIER_SEARCH"),
        stg("c", fld("a"), fld("b", required=False, applies_to=LLP), after="JURISDICTION"),
        stg("c", fld("a"), applies_to=LLP, after=None),
    ],
)
def test_conditional_content_before_registry_verification_is_refused(
    candidate: WorkflowStage,
) -> None:
    issues = structure_issues((candidate,), is_onboarding=True)
    assert (INVALID, CONDITIONAL_BEFORE_REGISTRY_ISSUE) in {(i.code, i.message) for i in issues}


@pytest.mark.parametrize(
    "anchor",
    [
        "ACRA_REGISTRY",
        "DOCUMENT_IDP",
        "RECONCILIATION",
        "OWNERSHIP_UBO",
        "ADVISORY",
        "GOLDTIER_DETAILS",
    ],
)
def test_conditional_content_at_registry_or_later_is_allowed(anchor: str) -> None:
    candidate = (stg("c", fld("a"), applies_to=LLP, after=anchor),)
    assert structure_issues(candidate, is_onboarding=True) == ()


def test_moving_a_conditional_stage_to_an_earlier_anchor_is_refused() -> None:
    active = ver(1, stg("c", fld("a"), applies_to=LLP, after="ADVISORY"))
    moved = (stg("c", fld("a"), applies_to=LLP, after="INITIAL_IDENTITY"),)
    report = validate_candidate(
        moved,
        active=active,
        baseline=seed_baseline(active),
        is_onboarding=True,
        base_version=1,
        active_version=1,
    )
    assert CONDITIONAL_BEFORE_REGISTRY_ISSUE in {i.message for i in report.issues}
    assert not report.valid


def test_unconditional_content_at_early_anchors_is_unchanged() -> None:
    assert structure_issues((stg("c", fld("a"), after="CASE_START"),), is_onboarding=True) == ()


def test_conditional_stage_cannot_impersonate_a_locked_stage() -> None:
    candidate = stg("c", fld("a"), applies_to=LLP, after="ADVISORY", name="Final review & send")
    found = ratchet_issues((candidate,), active=None, baseline=EMPTY, is_onboarding=True)
    assert {i.rule for i in found} == {RatchetRule.RR_9}


def test_non_onboarding_minimum_all_stage_with_all_field_b6() -> None:
    only_conditional = (stg("a", fld("x"), applies_to=LLP, after=None),)
    all_stage_conditional_fields = (stg("a", fld("x", applies_to=LLP), after=None),)
    for candidate in (only_conditional, all_stage_conditional_fields):
        issues = structure_issues(candidate, is_onboarding=False)
        assert [(i.code, i.message) for i in issues] == [
            (GovernanceErrorCode.PROPOSAL_EMPTY.value, CONDITIONAL_NON_ONBOARDING_MINIMUM_ISSUE)
        ]
    fine = (stg("a", fld("x"), after=None), stg("b", fld("y"), applies_to=LLP, after=None))
    assert structure_issues(fine, is_onboarding=False) == ()
    # Onboarding has no minimum (B6 is non-onboarding only).
    assert structure_issues((stg("a", fld("x"), applies_to=LLP),), is_onboarding=True) == ()


def test_optional_all_to_conditional_required_is_refused_b9() -> None:
    active = ver(1, stg("s", fld("a"), fld("o", required=False)))
    via_field = (stg("s", fld("a"), fld("o", applies_to=LLP)),)
    issues = structure_issues(via_field, is_onboarding=True, active=active)
    assert [(i.code, i.field_id, i.message) for i in issues] == [
        (INVALID, "o", CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE)
    ]
    via_stage = (stg("s", fld("a"), fld("o"), applies_to=LLP),)
    issues = structure_issues(via_stage, is_onboarding=True, active=active)
    assert [(i.field_id, i.message) for i in issues] == [
        ("o", CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE)
    ]
    # Allowed: optional ALL -> required ALL, and a new conditional field beside it.
    ok = (stg("s", fld("a"), fld("o"), fld("n", applies_to=LLP)),)
    assert structure_issues(ok, is_onboarding=True, active=active) == ()
    report = validate_candidate(
        via_field,
        active=active,
        baseline=seed_baseline(active),
        is_onboarding=True,
        base_version=1,
        active_version=1,
    )
    assert not report.valid


def test_canonical_form_is_checked_for_content_built_without_validation() -> None:
    outside = stg("s", fld("a"), applies_to=LLP).model_copy(
        update={"fields": (fld("a", applies_to=(F.LP,)),)}
    )
    issues = structure_issues((outside,), is_onboarding=True)
    assert [(i.field_id, i.message) for i in issues] == [
        ("a", CONDITIONAL_FIELD_OUTSIDE_STAGE_ISSUE)
    ]
    full = stg("s", fld("a")).model_copy(update={"applies_to": tuple(F)})
    issues = structure_issues((full,), is_onboarding=True)
    assert [(i.stage_id, i.message) for i in issues] == [("s", CONDITIONAL_FULL_SET_ISSUE)]
