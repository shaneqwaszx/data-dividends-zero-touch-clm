"""Required-obligation ratchet, structure checks, byte budget and diff (ADR-017 §2, §5).

Pure, deterministic functions over the frozen governance contract. Nothing here performs
I/O, reads a case, calls a provider or touches a store. The service owns locking, CAS and
persistence; this module only answers "is this candidate allowed, and what would it add".

Obligations (ADR-017 §2):
- a required stage is an added stage that blocks the send (``stage_blocks_send``);
- a required field is ``(stage_id, field_id)`` with ``field.required``.

Every candidate is checked against **both** the active version **and** the required
baseline. An identical violation found against both is reported once.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import bson

from app.api_workflow_governance_models import (
    ChangeCounts,
    FieldDiff,
    StageDiff,
    ValidationIssue,
    ValidationReport,
)
from app.domain.workflow_governance import (
    MAX_ENCODED_VERSION_BYTES,
    BaselineField,
    BaselineStage,
    FieldSignature,
    GovernanceErrorCode,
    ObligationKey,
    PermanentObligation,
    PermanentObligationChange,
    ProposalKind,
    RatchetRule,
    RequiredBaseline,
    normalise_label,
    proposal_content_hash,
    ratchet_error_code,
)
from app.domain.workflows import (
    ONBOARDING_ANCHOR_STAGES,
    ONBOARDING_LOCKED_STAGES,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
)
from app.services.workflow_management import stage_blocks_send

MAX_MESSAGE = 240
MAX_NORMALISED = 80  # FieldSignature.normalised_label / BaselineStage.normalised_name

# Existing structure codes (``WorkflowManagementService._validate_structure`` /
# ``_validate_activation``), reported as issues instead of raised.
CODE_DUPLICATE_ID = "WORKFLOW_DUPLICATE_ID"
CODE_STAGE_POSITION_INVALID = "WORKFLOW_STAGE_POSITION_INVALID"
CODE_FIELD_REQUIRED = "WORKFLOW_FIELD_REQUIRED"
CODE_OPTIONS_REQUIRED = "WORKFLOW_OPTIONS_REQUIRED"
CODE_AUTOFILL_INVALID = "WORKFLOW_AUTOFILL_INVALID"

_ANCHOR_IDS = frozenset(node_id for node_id, _ in ONBOARDING_ANCHOR_STAGES)
_FINAL_NODE_ID = ONBOARDING_LOCKED_STAGES[-1][0]
_FINAL_LABEL = ONBOARDING_LOCKED_STAGES[-1][1]
_LOCKED_IDS = frozenset(node_id for node_id, _ in ONBOARDING_LOCKED_STAGES)
# A locked stage is impersonated by its label or its node id read as words.
_LOCKED_NAMES = frozenset(
    name
    for node_id, label in ONBOARDING_LOCKED_STAGES
    for name in (normalise_label(label), normalise_label(node_id.replace("_", " ")))
)

# Placeholders for the parts of a would-be version the service fills at publication.
# Worst case: an int64 version number and a maximum-length actor id.
_BUDGET_VERSION = 2**62
_BUDGET_ACTIVATED_AT = datetime(2000, 1, 1, tzinfo=UTC)
_BUDGET_ACTIVATED_BY = "x" * 64


def _message(text: str) -> str:
    return text if len(text) <= MAX_MESSAGE else text[: MAX_MESSAGE - 1] + "…"


def _options(field: WorkflowField) -> frozenset[str]:
    return frozenset(normalise_label(option) for option in field.options)


# --- Signatures and the baseline ---


def field_signature(field: WorkflowField) -> FieldSignature:
    """The semantic signature of one field (ADR-017 §2). Applicability is None until M3."""

    return FieldSignature(
        kind=field.kind,
        normalised_label=normalise_label(field.label),
        choice_options=(
            tuple(sorted(_options(field))) if field.kind == WorkflowFieldKind.CHOICE else None
        ),
        has_case_data_key=field.case_data_key is not None,
    )


def _representative(field: WorkflowField, signature: FieldSignature) -> WorkflowField:
    """R1-12: the latest published definition, restricted to the baseline signature."""

    options = field.options
    if signature.choice_options is not None:
        allowed = frozenset(signature.choice_options)
        options = tuple(option for option in field.options if normalise_label(option) in allowed)
    return field.model_copy(
        update={
            "required": True,
            "options": options,
            "case_data_key": field.case_data_key if signature.has_case_data_key else None,
        }
    )


def _stricter_signature(old: FieldSignature, field: WorkflowField) -> FieldSignature:
    """Kind and label fixed; CHOICE options intersected; ``case_data_key`` absent once absent."""

    options = old.choice_options
    if options is not None and field.kind == WorkflowFieldKind.CHOICE:
        options = tuple(sorted(frozenset(options) & _options(field)))
    return old.model_copy(
        update={
            "choice_options": options,
            "has_case_data_key": old.has_case_data_key and field.case_data_key is not None,
        }
    )


def _new_baseline_field(field: WorkflowField) -> BaselineField:
    signature = field_signature(field)
    return BaselineField(
        field_id=field.field_id,
        signature=signature,
        representative=_representative(field, signature),
    )


def _advanced_stage(existing: BaselineStage, stage: WorkflowStage, version: int) -> BaselineStage:
    by_id = {field.field_id: field for field in stage.fields if field.required}
    fields: list[BaselineField] = []
    for item in existing.fields:
        published = by_id.get(item.field_id)
        if published is None:
            fields.append(item)  # not published as required here: unchanged (never weaker)
            continue
        signature = _stricter_signature(item.signature, published)
        fields.append(
            BaselineField(
                field_id=item.field_id,
                signature=signature,
                representative=_representative(published, signature),
            )
        )
    known = {item.field_id for item in existing.fields}
    fields.extend(
        _new_baseline_field(field)
        for field in stage.fields
        if field.required and field.field_id not in known
    )
    return existing.model_copy(
        update={
            "representative_name": stage.name,
            "representative_after_node_id": stage.after_node_id,
            "fields": tuple(fields),
            "last_published_version": version,
        }
    )


def advance_baseline(baseline: RequiredBaseline, version: WorkflowVersion) -> RequiredBaseline:
    """Fold one published version into the baseline. The result is never weaker."""

    if baseline.updated_at_version is not None and version.version <= baseline.updated_at_version:
        raise ValueError("a baseline only advances to a later published version")
    published = {stage.stage_id: stage for stage in version.stages if stage_blocks_send(stage)}
    stages: list[BaselineStage] = []
    for existing in baseline.stages:
        stage = published.get(existing.stage_id)
        stages.append(
            existing if stage is None else _advanced_stage(existing, stage, version.version)
        )
    known = {item.stage_id for item in baseline.stages}
    for stage in version.stages:
        if stage.stage_id in known or not stage_blocks_send(stage):
            continue
        stages.append(
            BaselineStage(
                stage_id=stage.stage_id,
                normalised_name=normalise_label(stage.name),
                representative_name=stage.name,
                representative_after_node_id=stage.after_node_id,
                fields=tuple(_new_baseline_field(f) for f in stage.fields if f.required),
                first_published_version=version.version,
                last_published_version=version.version,
            )
        )
    return baseline.model_copy(
        update={"updated_at_version": version.version, "stages": tuple(stages)}
    )


def seed_baseline(version: WorkflowVersion) -> RequiredBaseline:
    """Seed from the currently active version only (ADR-017 §1.4, §2)."""

    seeded = advance_baseline(RequiredBaseline(), version)
    return seeded.model_copy(update={"seeded_from_version": version.version})


# --- Structure (ports _validate_structure and _validate_activation as issues) ---


def structure_issues(
    stages: tuple[WorkflowStage, ...], *, is_onboarding: bool
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    def add(
        code: str, message: str, stage_id: str | None = None, field_id: str | None = None
    ) -> None:
        issues.append(
            ValidationIssue(
                code=code, stage_id=stage_id, field_id=field_id, message=_message(message)
            )
        )

    if not stages and not is_onboarding:
        add(
            GovernanceErrorCode.PROPOSAL_EMPTY.value,
            "Add at least one stage. An empty workflow stays unpublished and inactive.",
        )
    seen_stages: set[str] = set()
    for stage in stages:
        if stage.stage_id in seen_stages:
            add(
                CODE_DUPLICATE_ID,
                "Stage and field identifiers must be unique.",
                stage_id=stage.stage_id,
            )
        seen_stages.add(stage.stage_id)
        if is_onboarding and stage.after_node_id not in _ANCHOR_IDS:
            add(
                CODE_STAGE_POSITION_INVALID,
                "Choose which onboarding stage this stage follows.",
                stage_id=stage.stage_id,
            )
        if not is_onboarding and stage.after_node_id is not None:
            add(
                CODE_STAGE_POSITION_INVALID,
                "Only onboarding stages follow an existing stage.",
                stage_id=stage.stage_id,
            )
        if not 1 <= len(normalise_label(stage.name)) <= MAX_NORMALISED:
            add(
                GovernanceErrorCode.PROPOSAL_INVALID.value,
                "A stage name needs letters or digits, within 80 characters.",
                stage_id=stage.stage_id,
            )
        if not stage.fields:
            add(
                CODE_FIELD_REQUIRED,
                "Add at least one field to every stage.",
                stage_id=stage.stage_id,
            )
        seen_fields: set[str] = set()
        for field in stage.fields:
            if field.field_id in seen_fields:
                add(
                    CODE_DUPLICATE_ID,
                    "Stage and field identifiers must be unique.",
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
            seen_fields.add(field.field_id)
            if field.kind == WorkflowFieldKind.CHOICE and not field.options:
                add(
                    CODE_OPTIONS_REQUIRED,
                    "Add options to every dropdown field.",
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
            if field.autofill and not field.document_label:
                add(
                    CODE_AUTOFILL_INVALID,
                    "Autofill needs a document label.",
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
            labels = (field.label, *field.options)
            if any(not 1 <= len(normalise_label(text)) <= MAX_NORMALISED for text in labels):
                add(
                    GovernanceErrorCode.PROPOSAL_INVALID.value,
                    "Field labels and options need letters or digits, within 80 characters.",
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
    return tuple(issues)


# --- Byte budget (ADR-017 §5) ---


def encoded_version_bytes(stages: tuple[WorkflowStage, ...]) -> int:
    """BSON size of the would-be version document, with worst-case publication metadata."""

    document = {
        "version": _BUDGET_VERSION,
        "stages": [stage.model_dump(mode="json") for stage in stages],
        "activated_at": _BUDGET_ACTIVATED_AT.isoformat(),
        "activated_by": _BUDGET_ACTIVATED_BY,
    }
    return len(bson.encode(document))


def budget_issues(encoded_bytes: int) -> tuple[ValidationIssue, ...]:
    if encoded_bytes <= MAX_ENCODED_VERSION_BYTES:
        return ()
    return (
        ValidationIssue(
            code=GovernanceErrorCode.PROPOSAL_TOO_LARGE.value,
            message=_message(
                f"This version would be {encoded_bytes} bytes; the limit is "
                f"{MAX_ENCODED_VERSION_BYTES} bytes."
            ),
        ),
    )


# --- The ratchet (RR-1 to RR-10) ---


@dataclass(frozen=True)
class _FieldObligation:
    field_id: str
    label: str
    kind: WorkflowFieldKind
    normalised_label: str
    options: frozenset[str] | None
    has_case_data_key: bool


@dataclass(frozen=True)
class _StageObligation:
    stage_id: str
    name: str
    normalised_name: str
    fields: tuple[_FieldObligation, ...]


def _active_obligations(active: WorkflowVersion | None) -> tuple[_StageObligation, ...]:
    if active is None:
        return ()
    return tuple(
        _StageObligation(
            stage_id=stage.stage_id,
            name=stage.name,
            normalised_name=normalise_label(stage.name),
            fields=tuple(
                _FieldObligation(
                    field_id=field.field_id,
                    label=field.label,
                    kind=field.kind,
                    normalised_label=normalise_label(field.label),
                    options=(_options(field) if field.kind == WorkflowFieldKind.CHOICE else None),
                    has_case_data_key=field.case_data_key is not None,
                )
                for field in stage.fields
                if field.required
            ),
        )
        for stage in active.stages
        if stage_blocks_send(stage)
    )


def _baseline_obligations(baseline: RequiredBaseline) -> tuple[_StageObligation, ...]:
    return tuple(
        _StageObligation(
            stage_id=stage.stage_id,
            name=stage.representative_name,
            normalised_name=stage.normalised_name,
            fields=tuple(
                _FieldObligation(
                    field_id=item.field_id,
                    label=item.representative.label,
                    kind=item.signature.kind,
                    normalised_label=item.signature.normalised_label,
                    options=(
                        None
                        if item.signature.choice_options is None
                        else frozenset(item.signature.choice_options)
                    ),
                    has_case_data_key=item.signature.has_case_data_key,
                )
                for item in stage.fields
            ),
        )
        for stage in baseline.stages
    )


def _issue(
    rule: RatchetRule, message: str, stage_id: str | None, field_id: str | None = None
) -> ValidationIssue:
    return ValidationIssue(
        code=ratchet_error_code(rule).value,
        rule=rule,
        stage_id=stage_id,
        field_id=field_id,
        message=_message(message),
    )


def _field_issues(
    obligation: _FieldObligation, stage: WorkflowStage, stage_name: str
) -> list[ValidationIssue]:
    found = next((f for f in stage.fields if f.field_id == obligation.field_id), None)
    where = f"'{obligation.label}' in '{stage_name}'"
    sid, fid = stage.stage_id, obligation.field_id
    if found is None or not found.required:
        return [
            _issue(
                RatchetRule.RR_3,
                f"The required field {where} cannot be removed or made optional.",
                sid,
                fid,
            )
        ]
    issues: list[ValidationIssue] = []
    if found.kind != obligation.kind:
        issues.append(
            _issue(
                RatchetRule.RR_4,
                f"The required field {where} must stay a {obligation.kind.value} field.",
                sid,
                fid,
            )
        )
    if normalise_label(found.label) != obligation.normalised_label:
        issues.append(
            _issue(
                RatchetRule.RR_5,
                f"The required field {where} cannot be renamed.",
                sid,
                fid,
            )
        )
    if (
        obligation.options is not None
        and found.kind == WorkflowFieldKind.CHOICE
        and not _options(found) <= obligation.options
    ):
        issues.append(
            _issue(
                RatchetRule.RR_6,
                f"The required field {where} cannot offer an option that was removed or never "
                "approved.",
                sid,
                fid,
            )
        )
    if not obligation.has_case_data_key and found.case_data_key is not None:
        issues.append(
            _issue(
                RatchetRule.RR_7,
                f"The required field {where} cannot start taking its value from the case.",
                sid,
                fid,
            )
        )
    return issues


def _obligation_issues(
    obligations: Iterable[_StageObligation], candidate: dict[str, WorkflowStage]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for obligation in obligations:
        stage = candidate.get(obligation.stage_id)
        if stage is None:
            issues.append(
                _issue(
                    RatchetRule.RR_1,
                    f"The required stage '{obligation.name}' cannot be removed.",
                    obligation.stage_id,
                )
            )
            continue
        if not stage_blocks_send(stage):
            issues.append(
                _issue(
                    RatchetRule.RR_2,
                    f"The required stage '{obligation.name}' must keep at least one required "
                    "field.",
                    obligation.stage_id,
                )
            )
        if normalise_label(stage.name) != obligation.normalised_name:
            issues.append(
                _issue(
                    RatchetRule.RR_10,
                    f"The required stage '{obligation.name}' cannot be renamed.",
                    obligation.stage_id,
                )
            )
        for field in obligation.fields:
            issues.extend(_field_issues(field, stage, obligation.name))
    return issues


def applicability_issues(
    candidate: tuple[WorkflowStage, ...], baseline: RequiredBaseline
) -> tuple[ValidationIssue, ...]:
    """RR-8 HOOK (inert until ADR-018 / M3).

    Conditional steps do not exist yet: every obligation is unconditional and every
    ``FieldSignature.applicability`` is None, so nothing can be narrowed. When ADR-018 adds
    applicability, this hook must refuse a narrowed applicability or an unconditional
    obligation made conditional, against both the active version and the baseline.
    """

    del candidate, baseline
    return ()


def _engine_order_issues(
    candidate: tuple[WorkflowStage, ...], *, is_onboarding: bool
) -> list[ValidationIssue]:
    """RR-9: added stages never impersonate or reorder the code-owned stages."""

    issues: list[ValidationIssue] = []
    for stage in candidate:
        sid = stage.stage_id
        if not is_onboarding:
            if stage.after_node_id is not None:
                issues.append(
                    _issue(
                        RatchetRule.RR_9,
                        f"The stage '{stage.name}' cannot be placed among the onboarding stages.",
                        sid,
                    )
                )
            continue
        impersonates = (
            sid.upper().replace("-", "_") in _LOCKED_IDS
            or normalise_label(stage.name) in _LOCKED_NAMES
        )
        if impersonates:
            issues.append(
                _issue(
                    RatchetRule.RR_9,
                    f"The stage '{stage.name}' cannot take the identity of a built-in "
                    "onboarding stage.",
                    sid,
                )
            )
        if stage.after_node_id == _FINAL_NODE_ID:
            issues.append(
                _issue(
                    RatchetRule.RR_9,
                    f"The stage '{stage.name}' must come before '{_FINAL_LABEL}'.",
                    sid,
                )
            )
        elif stage.after_node_id not in _ANCHOR_IDS:
            issues.append(
                _issue(
                    RatchetRule.RR_9,
                    f"The stage '{stage.name}' must follow a built-in onboarding stage.",
                    sid,
                )
            )
    return issues


def ratchet_issues(
    candidate: tuple[WorkflowStage, ...],
    *,
    active: WorkflowVersion | None,
    baseline: RequiredBaseline,
    is_onboarding: bool,
) -> tuple[ValidationIssue, ...]:
    """RR-1 to RR-10 against both the active version and the baseline; every violation."""

    by_id: dict[str, WorkflowStage] = {}
    for stage in candidate:
        by_id.setdefault(stage.stage_id, stage)
    found = [
        *_obligation_issues(_active_obligations(active), by_id),
        *_obligation_issues(_baseline_obligations(baseline), by_id),
        *applicability_issues(candidate, baseline),
        *_engine_order_issues(candidate, is_onboarding=is_onboarding),
    ]
    unique: dict[tuple[str | None, str | None, str | None], ValidationIssue] = {}
    for issue in found:
        key = (issue.rule.value if issue.rule else None, issue.stage_id, issue.field_id)
        unique.setdefault(key, issue)
    return tuple(unique.values())


# --- Permanent obligations (ADR-017 §1.3) ---


def permanent_obligations(
    candidate: tuple[WorkflowStage, ...],
    *,
    active: WorkflowVersion | None,
    baseline: RequiredBaseline,
) -> tuple[PermanentObligation, ...]:
    """New required obligations and tightenings, in candidate order (stage, then fields)."""

    active_stages = {stage.stage_id: stage for stage in active.stages} if active else {}
    baseline_stages = {stage.stage_id: stage for stage in baseline.stages}
    result: list[PermanentObligation] = []
    seen: set[ObligationKey] = set()

    def add(
        key: ObligationKey,
        change: PermanentObligationChange,
        stage: WorkflowStage,
        detail: str,
        field: WorkflowField | None = None,
    ) -> None:
        if key in seen:
            return
        seen.add(key)
        result.append(
            PermanentObligation(
                key=key,
                change=change,
                stage_name=stage.name,
                field_label=field.label if field else None,
                detail=_message(detail),
            )
        )

    for stage in candidate:
        if not stage_blocks_send(stage):
            continue
        before = active_stages.get(stage.stage_id)
        recorded = baseline_stages.get(stage.stage_id)
        if recorded is None:
            if before is not None and not stage_blocks_send(before):
                add(
                    ObligationKey(stage_id=stage.stage_id),
                    PermanentObligationChange.TIGHTENED,
                    stage,
                    f"The stage '{stage.name}' becomes required.",
                )
            else:
                add(
                    ObligationKey(stage_id=stage.stage_id),
                    PermanentObligationChange.NEW_REQUIRED_STAGE,
                    stage,
                    f"New required stage '{stage.name}'.",
                )
        recorded_fields = {item.field_id: item for item in recorded.fields} if recorded else {}
        before_fields = {f.field_id: f for f in before.fields} if before else {}
        for field in stage.fields:
            if not field.required:
                continue
            key = ObligationKey(stage_id=stage.stage_id, field_id=field.field_id)
            item = recorded_fields.get(field.field_id)
            if item is None:
                earlier = before_fields.get(field.field_id)
                if earlier is not None and not earlier.required:
                    add(
                        key,
                        PermanentObligationChange.TIGHTENED,
                        stage,
                        f"The field '{field.label}' becomes required.",
                        field,
                    )
                else:
                    add(
                        key,
                        PermanentObligationChange.NEW_REQUIRED_FIELD,
                        stage,
                        f"New required field '{field.label}'.",
                        field,
                    )
                continue
            allowed = item.signature.choice_options
            if (
                allowed is not None
                and field.kind == WorkflowFieldKind.CHOICE
                and not frozenset(allowed) <= _options(field)
            ):
                add(
                    key,
                    PermanentObligationChange.TIGHTENED,
                    stage,
                    f"The field '{field.label}' offers fewer options; removed options can "
                    "never return.",
                    field,
                )
    return tuple(result)


# --- The combined report ---


def validate_candidate(
    candidate: tuple[WorkflowStage, ...],
    *,
    active: WorkflowVersion | None,
    baseline: RequiredBaseline,
    is_onboarding: bool,
    base_version: int,
    active_version: int,
    kind: ProposalKind = ProposalKind.CHANGE,
) -> ValidationReport:
    encoded = encoded_version_bytes(candidate)
    issues = (
        *structure_issues(candidate, is_onboarding=is_onboarding),
        *budget_issues(encoded),
        *ratchet_issues(candidate, active=active, baseline=baseline, is_onboarding=is_onboarding),
    )
    return ValidationReport(
        valid=not issues,
        content_hash=proposal_content_hash(kind, candidate),
        encoded_bytes=encoded,
        max_encoded_bytes=MAX_ENCODED_VERSION_BYTES,
        base_version=base_version,
        active_version=active_version,
        issues=issues,
        permanent_obligations=permanent_obligations(candidate, active=active, baseline=baseline),
    )


# --- Comparison diff ---


def _field_diffs(
    before: tuple[WorkflowField, ...], after: tuple[WorkflowField, ...]
) -> tuple[FieldDiff, ...]:
    old = {field.field_id: field for field in before}
    new_ids = {field.field_id for field in after}
    diffs = [
        FieldDiff(
            field_id=field.field_id,
            change=(
                "ADDED"
                if field.field_id not in old
                else "UNCHANGED"
                if old[field.field_id] == field
                else "CHANGED"
            ),
            before=old.get(field.field_id),
            after=field,
        )
        for field in after
    ]
    diffs.extend(
        FieldDiff(field_id=field.field_id, change="REMOVED", before=field, after=None)
        for field in before
        if field.field_id not in new_ids
    )
    return tuple(diffs)


def stage_diff(
    active: tuple[WorkflowStage, ...], candidate: tuple[WorkflowStage, ...]
) -> tuple[StageDiff, ...]:
    """Candidate order first (ADDED / CHANGED / UNCHANGED), then REMOVED in active order."""

    old = {stage.stage_id: stage for stage in active}
    new_ids = {stage.stage_id for stage in candidate}
    diffs: list[StageDiff] = []
    for stage in candidate:
        before = old.get(stage.stage_id)
        diffs.append(
            StageDiff(
                stage_id=stage.stage_id,
                change=(
                    "ADDED" if before is None else "UNCHANGED" if before == stage else "CHANGED"
                ),
                name_before=before.name if before else None,
                name_after=stage.name,
                after_node_id_before=before.after_node_id if before else None,
                after_node_id_after=stage.after_node_id,
                blocks_send_before=stage_blocks_send(before) if before else False,
                blocks_send_after=stage_blocks_send(stage),
                fields=_field_diffs(before.fields if before else (), stage.fields),
            )
        )
    for stage in active:
        if stage.stage_id in new_ids:
            continue
        diffs.append(
            StageDiff(
                stage_id=stage.stage_id,
                change="REMOVED",
                name_before=stage.name,
                name_after=None,
                after_node_id_before=stage.after_node_id,
                after_node_id_after=None,
                blocks_send_before=stage_blocks_send(stage),
                blocks_send_after=False,
                fields=_field_diffs(stage.fields, ()),
            )
        )
    return tuple(diffs)


def change_counts(diffs: tuple[StageDiff, ...]) -> ChangeCounts:
    fields = [item for diff in diffs for item in diff.fields]
    return ChangeCounts(
        stages_added=sum(diff.change == "ADDED" for diff in diffs),
        stages_removed=sum(diff.change == "REMOVED" for diff in diffs),
        stages_changed=sum(diff.change == "CHANGED" for diff in diffs),
        fields_added=sum(item.change == "ADDED" for item in fields),
        fields_removed=sum(item.change == "REMOVED" for item in fields),
        fields_changed=sum(item.change == "CHANGED" for item in fields),
    )


# --- Safe target (ADR-017 §2, §4; used by M2 recovery publications) ---


def safe_target(
    base_stages: tuple[WorkflowStage, ...], baseline: RequiredBaseline
) -> tuple[WorkflowStage, ...]:
    """``base ∪ required_baseline``: baseline obligations use their representative content."""

    recorded = {stage.stage_id: stage for stage in baseline.stages}
    result: list[WorkflowStage] = []
    for stage in base_stages:
        item = recorded.get(stage.stage_id)
        if item is None:
            result.append(stage)
            continue
        representatives = {field.field_id: field.representative for field in item.fields}
        present = {field.field_id for field in stage.fields}
        fields = [representatives.get(field.field_id, field) for field in stage.fields]
        fields.extend(
            field.representative for field in item.fields if field.field_id not in present
        )
        result.append(
            stage.model_copy(update={"name": item.representative_name, "fields": tuple(fields)})
        )
    present_stages = {stage.stage_id for stage in base_stages}
    result.extend(
        WorkflowStage(
            stage_id=item.stage_id,
            name=item.representative_name,
            after_node_id=item.representative_after_node_id,
            fields=tuple(field.representative for field in item.fields),
        )
        for item in baseline.stages
        if item.stage_id not in present_stages
    )
    return tuple(result)
