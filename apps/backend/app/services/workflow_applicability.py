"""Conditional workflow applicability: the pure evaluator (ADR-018 §3, §6; contract CC-8).

Everything here is a pure function of its inputs: no clock (times come from the caller), no
I/O and no randomness. The legal form comes only from the backend case record, through the
single classifier ``classify_registry_legal_form`` (§3.1, OPQ rule A4). Anything unknown,
missing, ``OTHER``, conflicting or ambiguous is ``UNVERIFIED``, which applies every
conditional obligation (CA-4). Resolution only ever drops conditional content that does not
apply; it never touches unconditional content, the code-owned onboarding stages
(``ONBOARDING_LOCKED_STAGES`` are not ``WorkflowStage`` records) or the engine order.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.models import (
    EventOutcome,
    OnboardingCase,
    SourceEnvironment,
    SourceSystem,
    WorkflowState,
)
from app.domain.registry_legal_form import (
    ConditionalLegalForm,
    RegistryLegalForm,
    classify_registry_legal_form,
)
from app.domain.uen_route import UenRoute
from app.domain.workflows import (
    ApplicabilityBasis,
    ApplicabilityBasisReason,
    ApplicabilityBasisStatus,
    AppliesTo,
    BasisConflict,
    BindingRef,
    RunItemKey,
    WorkflowRun,
    WorkflowStage,
    WorkflowVersion,
)

LOGGER = logging.getLogger(__name__)

ItemKey = tuple[str, str | None]  # (stage_id, field_id or None for the stage itself)


@dataclass(frozen=True)
class ObservedBasis:
    """The basis a case record supports right now (never stored by itself)."""

    status: ApplicabilityBasisStatus
    legal_form: ConditionalLegalForm | None
    reason: ApplicabilityBasisReason
    source_environment: SourceEnvironment | None
    binding_ref: BindingRef | None


def _unverified(
    reason: ApplicabilityBasisReason,
    *,
    environment: SourceEnvironment | None = None,
    binding_ref: BindingRef | None = None,
) -> ObservedBasis:
    return ObservedBasis(
        status=ApplicabilityBasisStatus.UNVERIFIED,
        legal_form=None,
        reason=reason,
        source_environment=environment,
        binding_ref=binding_ref,
    )


def observe_case_basis(case: OnboardingCase | None) -> ObservedBasis:
    """§3.2: REGISTRY_BOUND only for a bound, classified, non-conflicting legal form.

    Raises nothing for a decodable case; callers map any exception to ``READ_FAILED`` or to
    ``WORKFLOW_STAGE_CHECK_UNAVAILABLE``.
    """

    if case is None:
        return _unverified(ApplicabilityBasisReason.NO_CASE_RECORD)
    entity = case.entity
    if entity is None:
        return _unverified(ApplicabilityBasisReason.NO_ENTITY)
    binding = case.registry_evidence_binding
    environment = entity.source.environment
    if binding is None:
        return _unverified(ApplicabilityBasisReason.NO_BINDING, environment=environment)
    reference = BindingRef(
        cache_id=binding.cache_id,
        cache_revision=binding.cache_revision,
        bound_to_case_at=binding.bound_to_case_at,
    )
    if entity.source.source_system != SourceSystem.ACRA:
        # Defensive: a future non-ACRA source is not an eligible binding (§3.2).
        return _unverified(
            ApplicabilityBasisReason.NO_BINDING, environment=environment, binding_ref=reference
        )
    form = classify_registry_legal_form(entity.party_type)  # the single classifier (A4)
    if form == RegistryLegalForm.OTHER:
        return _unverified(
            ApplicabilityBasisReason.OTHER_FORM, environment=environment, binding_ref=reference
        )
    route = case.uen_route
    if route is not None and (
        (route.route == UenRoute.GOVERNMENT_REGISTER) != (form == RegistryLegalForm.GOVERNMENT)
    ):
        return _unverified(
            ApplicabilityBasisReason.CONFLICTING_CLASSIFICATION,
            environment=environment,
            binding_ref=reference,
        )
    return ObservedBasis(
        status=ApplicabilityBasisStatus.REGISTRY_BOUND,
        legal_form=ConditionalLegalForm(form.value),
        reason=ApplicabilityBasisReason.REGISTRY_BINDING,
        source_environment=environment,
        binding_ref=reference,
    )


def safe_observe(case: OnboardingCase | None) -> ObservedBasis:
    """``observe_case_basis`` that fails closed to ``UNVERIFIED (READ_FAILED)``."""

    try:
        return observe_case_basis(case)
    except Exception:  # noqa: BLE001 - any read or decode failure is UNVERIFIED
        return _unverified(ApplicabilityBasisReason.READ_FAILED)


# --- Resolution (§3.3) --------------------------------------------------------------------


def applies(applies_to: AppliesTo | None, legal_form: ConditionalLegalForm | None) -> bool:
    """ALL applies to everyone; UNVERIFIED (None) receives every condition (CA-4)."""

    return applies_to is None or legal_form is None or legal_form in applies_to


def has_conditional(stages: Iterable[WorkflowStage]) -> bool:
    return any(stage.is_conditional for stage in stages)


def resolve_stages(
    stages: tuple[WorkflowStage, ...],
    legal_form: ConditionalLegalForm | None,
    *,
    keep: frozenset[ItemKey] = frozenset(),
) -> tuple[WorkflowStage, ...]:
    """The run's stage copy for ``legal_form`` (None = UNVERIFIED: everything applies).

    A field is kept when its effective applicability (stage ∩ field) applies. A stage that
    resolution emptied (it had fields and none applies) is dropped; a stage authored with no
    fields is copied unchanged (§3.3). Items in ``keep`` (already touched by the run) are never
    dropped (owner constraint: no retroactive removal); a stage touched only at stage level
    (a confirmation) is kept whole. Unconditional content is returned as is. ``after_node_id``
    and the order are never changed.
    """

    result: list[WorkflowStage] = []
    for stage in stages:
        if not stage.is_conditional:
            result.append(stage)
            continue
        if not stage.fields:
            # A stage authored with no fields follows its own condition (ADR-018 3.3).
            if applies(stage.applies_to, legal_form) or (stage.stage_id, None) in keep:
                result.append(stage)
            continue
        stage_applies = applies(stage.applies_to, legal_form)
        fields = tuple(
            field
            for field in stage.fields
            if (stage_applies and applies(field.applies_to, legal_form))
            or (stage.stage_id, field.field_id) in keep
        )
        if not fields:
            if (stage.stage_id, None) not in keep:
                continue
            fields = stage.fields
        result.append(
            stage
            if len(fields) == len(stage.fields)
            else stage.model_copy(update={"fields": fields})
        )
    return tuple(result)


def excluded_items(
    stages: tuple[WorkflowStage, ...], legal_form: ConditionalLegalForm | None
) -> frozenset[ItemKey]:
    """F3's ``X``: what the UNVERIFIED copy holds that ``legal_form`` would exclude."""

    full = resolve_stages(stages, None)
    narrowed = {stage.stage_id: stage for stage in resolve_stages(stages, legal_form)}
    items: set[ItemKey] = set()
    for stage in full:
        kept = narrowed.get(stage.stage_id)
        if kept is None:
            items.add((stage.stage_id, None))
            items.update((stage.stage_id, field.field_id) for field in stage.fields)
            continue
        kept_fields = {field.field_id for field in kept.fields}
        items.update(
            (stage.stage_id, field.field_id)
            for field in stage.fields
            if field.field_id not in kept_fields
        )
    return frozenset(items)


def touched_keys(run: WorkflowRun) -> frozenset[ItemKey]:
    """Run history (§3.5 F3): ``ever_touched`` plus the current answers and confirmations."""

    keys: set[ItemKey] = {(item.stage_id, item.field_id) for item in run.ever_touched}
    for answer in run.answers:
        keys.add((answer.stage_id, answer.field_id))
        keys.add((answer.stage_id, None))
    keys.update((item.stage_id, None) for item in run.confirmations)
    return frozenset(keys)


def with_touched(run: WorkflowRun, candidate: WorkflowRun) -> tuple[RunItemKey, ...]:
    """``candidate.ever_touched`` extended (monotonic, each key once) by its answers and
    confirmations; the order of earlier keys is kept."""

    present = list(run.ever_touched)
    seen = set(present)
    for stage_id, field_id in sorted(
        {(a.stage_id, a.field_id) for a in candidate.answers}
        | {(a.stage_id, None) for a in candidate.answers}
        | {(c.stage_id, None) for c in candidate.confirmations},
        key=lambda item: (item[0], item[1] or ""),
    ):
        key = RunItemKey(stage_id=stage_id, field_id=field_id)
        if key not in seen:
            seen.add(key)
            present.append(key)
    return tuple(present)


def is_touched(touched: frozenset[ItemKey], excluded: frozenset[ItemKey]) -> bool:
    excluded_stages = {stage_id for stage_id, field_id in excluded if field_id is None}
    for stage_id, field_id in touched:
        if stage_id in excluded_stages or (stage_id, field_id) in excluded:
            return True
    return False


# --- Freeze (§3.5 F1, F3, F4) -------------------------------------------------------------


def eligible_first_binding(case: OnboardingCase) -> bool:
    """F4: the binding is still the case's first, with no identity correction."""

    fetched = sum(
        1
        for event in case.events
        if event.stage == WorkflowState.REGISTRY_FETCHED
        and event.outcome == EventOutcome.SUCCEEDED
        and event.code is None
    )
    return (
        case.registry_evidence_binding is not None
        and not case.identity_corrections
        and fetched == 1
    )


@dataclass(frozen=True)
class FreezeDecision:
    basis: ApplicabilityBasis
    stages: tuple[WorkflowStage, ...]


def freeze_decision(
    case: OnboardingCase,
    run: WorkflowRun,
    version: WorkflowVersion,
    *,
    now: datetime,
    case_closed: bool,
) -> FreezeDecision:
    """The one freeze of an onboarding run (pure). ``case_closed``: already sent, dispatch
    confirmed or claimed (F3)."""

    observed = safe_observe(case)

    def unverified(reason: ApplicabilityBasisReason) -> ApplicabilityBasis:
        return ApplicabilityBasis(
            legal_form=None,
            status=ApplicabilityBasisStatus.UNVERIFIED,
            reason=reason,
            source_environment=observed.source_environment,
            evaluated_at=now,
            evaluated_from_version=version.version,
            frozen=True,
            binding_ref=observed.binding_ref,
        )

    if not eligible_first_binding(case):
        basis = unverified(ApplicabilityBasisReason.AMBIGUOUS_BINDING)
    elif observed.status != ApplicabilityBasisStatus.REGISTRY_BOUND:
        basis = unverified(observed.reason)
    else:
        excluded = excluded_items(version.stages, observed.legal_form)
        if case_closed or (excluded and is_touched(touched_keys(run), excluded)):
            basis = unverified(ApplicabilityBasisReason.TOO_LATE_TO_NARROW)
        else:
            basis = ApplicabilityBasis(
                legal_form=observed.legal_form,
                status=ApplicabilityBasisStatus.REGISTRY_BOUND,
                reason=ApplicabilityBasisReason.REGISTRY_BINDING,
                source_environment=observed.source_environment,
                evaluated_at=now,
                evaluated_from_version=version.version,
                frozen=True,
                binding_ref=observed.binding_ref,
            )
    return FreezeDecision(
        basis=basis,
        stages=resolve_stages(version.stages, basis.legal_form, keep=touched_keys(run)),
    )


def creation_basis(
    case: OnboardingCase | None,
    version: WorkflowVersion,
    *,
    now: datetime,
    read_failed: bool = False,
) -> ApplicabilityBasis:
    """A non-onboarding run's basis at creation (always frozen, §3.4). A ``NEW_CASE`` run has
    no case record; a failed case read is ``READ_FAILED``. Both are UNVERIFIED."""

    observed = (
        _unverified(ApplicabilityBasisReason.READ_FAILED) if read_failed else safe_observe(case)
    )
    return ApplicabilityBasis(
        legal_form=observed.legal_form,
        status=observed.status,
        reason=observed.reason,
        source_environment=observed.source_environment,
        evaluated_at=now,
        evaluated_from_version=version.version,
        frozen=True,
        binding_ref=observed.binding_ref,
    )


# --- Conflicts (§3.5 F5) ------------------------------------------------------------------


class BasisCheckStatus(StrEnum):
    NONE = "NONE"
    CONFLICT = "CONFLICT"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class BasisConflictCheck:
    status: BasisCheckStatus
    observed: ObservedBasis | None = None
    persisted: bool = False


def basis_conflict_of(case: OnboardingCase | None, run: WorkflowRun | None) -> BasisConflictCheck:
    """F5: the one shared, deterministic recompute. Only a frozen, unescalated
    ``REGISTRY_BOUND`` basis can conflict; any read failure is ``UNAVAILABLE``."""

    try:
        if run is None:
            return BasisConflictCheck(BasisCheckStatus.NONE)
        basis = run.applicability_basis
        if (
            basis is None
            or not basis.frozen
            or basis.status != ApplicabilityBasisStatus.REGISTRY_BOUND
        ):
            return BasisConflictCheck(BasisCheckStatus.NONE)
        conflict = run.basis_conflict
        if conflict is not None and conflict.escalated:
            return BasisConflictCheck(BasisCheckStatus.NONE)
        if conflict is not None:
            return BasisConflictCheck(BasisCheckStatus.CONFLICT, persisted=True)
        if case is None:
            return BasisConflictCheck(BasisCheckStatus.UNAVAILABLE)
        observed = observe_case_basis(case)
        if (
            observed.status != basis.status
            or observed.legal_form != basis.legal_form
            or observed.binding_ref != basis.binding_ref
        ):
            return BasisConflictCheck(BasisCheckStatus.CONFLICT, observed=observed)
        return BasisConflictCheck(BasisCheckStatus.NONE)
    except Exception:  # noqa: BLE001 - an unreadable case or run fails closed
        return BasisConflictCheck(BasisCheckStatus.UNAVAILABLE)


def conflict_record(observed: ObservedBasis, *, now: datetime) -> BasisConflict:
    return BasisConflict(
        detected_at=now,
        observed_status=observed.status,
        observed_legal_form=observed.legal_form,
        binding_ref=observed.binding_ref,
    )
