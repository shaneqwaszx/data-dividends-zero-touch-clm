"""Required-obligation ratchet, structure checks, byte budget and diff (ADR-017 §2, §5).

Pure, deterministic functions over the frozen governance contract. Nothing here performs
I/O, reads a case, calls a provider or touches a store. The service owns locking, CAS and
persistence; this module only answers "is this candidate allowed, and what would it add".

Obligations (ADR-017 §2):
- a required stage is an added stage that blocks the send (``stage_blocks_send``);
- a required field is ``(stage_id, field_id)`` with ``field.required``.

Every candidate is checked against **both** the active version **and** the required
baseline. An identical violation found against both is reported once.

ADR-018 (M3, CC-8): an obligation's applicability ``A`` is its stage's ``applies_to`` (a
stage) or its effective ``applies_to`` (a field: stage ∩ field). ``None`` is ALL, the top
element. RR-8 refuses narrowing, the baseline keeps the broadest ``A`` ever published, and a
safe target renders exactly the baseline ``A``. Unconditional content (every ``A`` is ALL)
behaves exactly as in M1/M2.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import bson
from pydantic import ValidationError

from app.api_workflow_governance_models import (
    ChangeCounts,
    FieldDiff,
    StageDiff,
    ValidationIssue,
    ValidationReport,
)
from app.domain.registry_legal_form import ConditionalLegalForm
from app.domain.workflow_governance import (
    CONDITIONAL_BEFORE_REGISTRY_ISSUE,
    CONDITIONAL_FIELD_OUTSIDE_STAGE_ISSUE,
    CONDITIONAL_FULL_SET_ISSUE,
    CONDITIONAL_NON_ONBOARDING_MINIMUM_ISSUE,
    CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE,
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
    CONDITIONAL_ONBOARDING_ANCHORS,
    ONBOARDING_ANCHOR_STAGES,
    ONBOARDING_LOCKED_STAGES,
    AppliesTo,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowStage,
    WorkflowVersion,
    applies_to_includes,
    effective_applies_to,
    field_within_stage,
)
from app.services.workflow_management import stage_blocks_send

MAX_MESSAGE = 240
MAX_NORMALISED = 80  # FieldSignature.normalised_label / BaselineStage.normalised_name
# Count limits of the stage models (``WorkflowVersion.stages``, ``WorkflowStage.fields``,
# ``WorkflowField.options``). ``model_copy`` skips them, so they are checked explicitly.
MAX_STAGES = 32
MAX_FIELDS_PER_STAGE = 32
MAX_OPTIONS_PER_FIELD = 32

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
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


def _identity_key(value: str) -> str:
    """RR-9 only: punctuation read as spaces, and "&" read explicitly as "and"."""

    text = unicodedata.normalize("NFKC", value).casefold().replace("&", " and ")
    return _NON_WORD.sub(" ", text).strip()


# A locked stage is impersonated by its label or its node id read as words, compared both
# with the ratchet normalisation (punctuation removed) and with ``_identity_key``
# (punctuation as spaces, "&" equivalent to "and").
_LOCKED_NAMES = frozenset(
    name
    for node_id, label in ONBOARDING_LOCKED_STAGES
    for name in (normalise_label(label), normalise_label(node_id.replace("_", " ")))
)
_LOCKED_IDENTITY_KEYS = frozenset(
    key
    for node_id, label in ONBOARDING_LOCKED_STAGES
    for key in (_identity_key(label), _identity_key(node_id))
)


class BaselineIntegrityError(ValueError):
    """A version that did not pass the ratchet was offered to ``advance_baseline``."""


class SafeTargetError(ValueError):
    """``base ∪ baseline`` cannot be built within the model limits; fail closed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = GovernanceErrorCode.PROPOSAL_INVALID.value
        self.public_message = message


# Placeholders for the parts of a would-be version the service fills at publication.
# Worst case: an int64 version number and a maximum-length actor id.
_BUDGET_VERSION = 2**62
_BUDGET_ACTIVATED_AT = datetime(2000, 1, 1, tzinfo=UTC)
_BUDGET_ACTIVATED_BY = "x" * 64


def _message(text: str) -> str:
    return text if len(text) <= MAX_MESSAGE else text[: MAX_MESSAGE - 1] + "…"


def _options(field: WorkflowField) -> frozenset[str]:
    return frozenset(normalise_label(option) for option in field.options)


# --- Applicability (ADR-018 §2.1, §4.1; None = ALL, the top element) ---


def _union(left: AppliesTo | None, right: AppliesTo | None) -> AppliesTo | None:
    """The broader of two applicabilities. ALL absorbs every set; the full set is ALL."""

    if left is None or right is None:
        return None
    forms = set(left) | set(right)
    if len(forms) >= len(ConditionalLegalForm):
        return None
    return tuple(sorted(forms, key=lambda item: item.value))


def _broader(candidate: AppliesTo | None, recorded: AppliesTo | None) -> bool:
    """``candidate`` covers ``recorded`` and more."""

    return applies_to_includes(candidate, recorded) and candidate != recorded


def _field_applicability(stage: WorkflowStage, field: WorkflowField) -> AppliesTo | None:
    return effective_applies_to(stage.applies_to, field.applies_to)


def _applies_text(value: AppliesTo | None) -> str:
    if value is None:
        return "Applies to all entities."
    forms = ", ".join(item.value for item in value)
    return f"Applies to: {forms}, and any entity whose legal form is not verified."


def _field_applies_to(effective: AppliesTo | None, stage: AppliesTo | None) -> AppliesTo | None:
    """The field-level ``applies_to`` that renders ``effective`` inside a stage of ``stage``."""

    return None if effective == stage else effective


# --- Signatures and the baseline ---


def field_signature(
    field: WorkflowField, *, stage_applies_to: AppliesTo | None = None
) -> FieldSignature:
    """The semantic signature of one field (ADR-017 §2, ADR-018 §2.3).

    ``applicability`` is the field's effective applicability within a stage whose
    ``applies_to`` is ``stage_applies_to`` (ALL when omitted).
    """

    return FieldSignature(
        kind=field.kind,
        normalised_label=normalise_label(field.label),
        choice_options=(
            tuple(sorted(_options(field))) if field.kind == WorkflowFieldKind.CHOICE else None
        ),
        has_case_data_key=field.case_data_key is not None,
        applicability=effective_applies_to(stage_applies_to, field.applies_to),
    )


def _representative(
    field: WorkflowField, signature: FieldSignature, stage_applicability: AppliesTo | None
) -> WorkflowField:
    """R1-12: the latest published definition, restricted to the baseline signature.

    It carries the baseline (broadest) applicability, relative to the baseline stage.
    """

    options = field.options
    if signature.choice_options is not None:
        allowed = frozenset(signature.choice_options)
        options = tuple(option for option in field.options if normalise_label(option) in allowed)
    data = {
        **field.model_dump(),
        "required": True,
        "options": options,
        "case_data_key": field.case_data_key if signature.has_case_data_key else None,
    }
    data.pop("applies_to", None)
    applies_to = _field_applies_to(signature.applicability, stage_applicability)
    if applies_to is not None:
        data["applies_to"] = applies_to
    return WorkflowField.model_validate(data)


def _stricter_signature(
    old: FieldSignature, field: WorkflowField, applicability: AppliesTo | None
) -> FieldSignature:
    """Kind and label fixed; CHOICE options intersected; ``case_data_key`` absent once absent;
    applicability the broadest ever published (ADR-018 §4.2)."""

    options = old.choice_options
    if options is not None and field.kind == WorkflowFieldKind.CHOICE:
        options = tuple(sorted(frozenset(options) & _options(field)))
    return FieldSignature(
        kind=old.kind,
        normalised_label=old.normalised_label,
        choice_options=options,
        has_case_data_key=old.has_case_data_key and field.case_data_key is not None,
        applicability=_union(old.applicability, applicability),
    )


def _new_baseline_field(
    field: WorkflowField, stage: WorkflowStage, stage_applicability: AppliesTo | None
) -> BaselineField:
    signature = field_signature(field, stage_applies_to=stage.applies_to)
    return BaselineField(
        field_id=field.field_id,
        signature=signature,
        representative=_representative(field, signature, stage_applicability),
    )


def _rerendered(item: BaselineField, stage_applicability: AppliesTo | None) -> BaselineField:
    """Keep a field's broadest applicability exact after its baseline stage broadened."""

    applies_to = _field_applies_to(item.signature.applicability, stage_applicability)
    if item.representative.applies_to == applies_to:
        return item
    data = item.representative.model_dump()
    data.pop("applies_to", None)
    if applies_to is not None:
        data["applies_to"] = applies_to
    return BaselineField(
        field_id=item.field_id,
        signature=item.signature,
        representative=WorkflowField.model_validate(data),
    )


def _advanced_stage(existing: BaselineStage, stage: WorkflowStage, version: int) -> BaselineStage:
    if normalise_label(stage.name) != existing.normalised_name:
        raise BaselineIntegrityError("a published version cannot rename a required stage")
    stage_applicability = _union(existing.applicability, stage.applies_to)
    by_id = {field.field_id: field for field in stage.fields if field.required}
    fields: list[BaselineField] = []
    for item in existing.fields:
        published = by_id.get(item.field_id)
        if published is None:
            # Not published as required here: unchanged (never weaker), rendered exactly.
            fields.append(_rerendered(item, stage_applicability))
            continue
        if (
            published.kind != item.signature.kind
            or normalise_label(published.label) != item.signature.normalised_label
        ):
            raise BaselineIntegrityError(
                "a published version cannot change a required field's kind or label"
            )
        signature = _stricter_signature(
            item.signature, published, _field_applicability(stage, published)
        )
        fields.append(
            BaselineField(
                field_id=item.field_id,
                signature=signature,
                representative=_representative(published, signature, stage_applicability),
            )
        )
    known = {item.field_id for item in existing.fields}
    fields.extend(
        _new_baseline_field(field, stage, stage_applicability)
        for field in stage.fields
        if field.required and field.field_id not in known
    )
    return BaselineStage(
        stage_id=existing.stage_id,
        normalised_name=existing.normalised_name,
        representative_name=stage.name,
        representative_after_node_id=stage.after_node_id,
        fields=tuple(fields),
        first_published_version=existing.first_published_version,
        last_published_version=version,
        applicability=stage_applicability,
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
                fields=tuple(
                    _new_baseline_field(f, stage, stage.applies_to)
                    for f in stage.fields
                    if f.required
                ),
                first_published_version=version.version,
                last_published_version=version.version,
                applicability=stage.applies_to,
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


def _applies_to_issue(value: AppliesTo | None) -> str | None:
    """A canonical-form check for content built without validation (``model_copy``)."""

    if value is None:
        return None
    if len(set(value)) >= len(ConditionalLegalForm):
        return CONDITIONAL_FULL_SET_ISSUE
    if not value or len(set(value)) != len(value):
        return "A condition names one or more different legal forms."
    return None


def _has_minimum_for_all(stages: tuple[WorkflowStage, ...]) -> bool:
    return any(
        stage.applies_to is None and any(field.applies_to is None for field in stage.fields)
        for stage in stages
    )


def structure_issues(
    stages: tuple[WorkflowStage, ...],
    *,
    is_onboarding: bool,
    active: WorkflowVersion | None = None,
) -> tuple[ValidationIssue, ...]:
    """Structure rules as issues. ``active`` enables the B9 check (ADR-018 §2.1)."""

    issues: list[ValidationIssue] = []
    invalid = GovernanceErrorCode.PROPOSAL_INVALID.value

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
    conditional = any(stage.is_conditional for stage in stages)
    if stages and not is_onboarding and conditional and not _has_minimum_for_all(stages):
        # ADR-018 §2.1, B6: an extension of WORKFLOW_PROPOSAL_EMPTY.
        add(GovernanceErrorCode.PROPOSAL_EMPTY.value, CONDITIONAL_NON_ONBOARDING_MINIMUM_ISSUE)
    if len(stages) > MAX_STAGES:
        add(
            GovernanceErrorCode.PROPOSAL_INVALID.value,
            f"A workflow can have at most {MAX_STAGES} stages; this one has {len(stages)}.",
        )
    active_stages = {stage.stage_id: stage for stage in active.stages} if active else {}
    seen_stages: set[str] = set()
    for stage in stages:
        if len(stage.fields) > MAX_FIELDS_PER_STAGE:
            add(
                GovernanceErrorCode.PROPOSAL_INVALID.value,
                f"A stage can have at most {MAX_FIELDS_PER_STAGE} fields; this one has "
                f"{len(stage.fields)}.",
                stage_id=stage.stage_id,
            )
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
        stage_problem = _applies_to_issue(stage.applies_to)
        if stage_problem:
            add(invalid, stage_problem, stage_id=stage.stage_id)
        if (
            is_onboarding
            and stage.is_conditional
            and stage.after_node_id not in CONDITIONAL_ONBOARDING_ANCHORS
        ):
            add(invalid, CONDITIONAL_BEFORE_REGISTRY_ISSUE, stage_id=stage.stage_id)
        before = active_stages.get(stage.stage_id)
        earlier_fields = {f.field_id: f for f in before.fields} if before else {}
        seen_fields: set[str] = set()
        for field in stage.fields:
            field_problem = _applies_to_issue(field.applies_to)
            if field_problem:
                add(invalid, field_problem, stage_id=stage.stage_id, field_id=field.field_id)
            elif not field_within_stage(stage.applies_to, field.applies_to):
                add(
                    invalid,
                    CONDITIONAL_FIELD_OUTSIDE_STAGE_ISSUE,
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
            earlier = earlier_fields.get(field.field_id)
            if (
                before is not None
                and earlier is not None
                and not earlier.required
                and _field_applicability(before, earlier) is None
                and field.required
                and not field_problem
                and _field_applicability(stage, field) is not None
            ):
                # ADR-018 §2.1, B9: optional ALL -> conditional required is refused.
                add(
                    invalid,
                    CONDITIONAL_OPTIONAL_TO_REQUIRED_ISSUE,
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
            if field.field_id in seen_fields:
                add(
                    CODE_DUPLICATE_ID,
                    "Stage and field identifiers must be unique.",
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
            seen_fields.add(field.field_id)
            if len(field.options) > MAX_OPTIONS_PER_FIELD:
                add(
                    GovernanceErrorCode.PROPOSAL_INVALID.value,
                    f"A dropdown field can have at most {MAX_OPTIONS_PER_FIELD} options; this "
                    f"one has {len(field.options)}.",
                    stage_id=stage.stage_id,
                    field_id=field.field_id,
                )
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
    applicability: AppliesTo | None = None  # effective (stage ∩ field); None = ALL


@dataclass(frozen=True)
class _StageObligation:
    stage_id: str
    name: str
    normalised_name: str
    fields: tuple[_FieldObligation, ...]
    applicability: AppliesTo | None = None  # the stage's applies_to; None = ALL


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
                    applicability=_field_applicability(stage, field),
                )
                for field in stage.fields
                if field.required
            ),
            applicability=stage.applies_to,
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
                    applicability=item.signature.applicability,
                )
                for item in stage.fields
            ),
            applicability=stage.applicability,
        )
        for stage in baseline.stages
    )


def _with_display_names(
    obligations: tuple[_StageObligation, ...], preferred: tuple[_StageObligation, ...]
) -> tuple[_StageObligation, ...]:
    """Display only: show baseline obligations with the active version's names, so the same
    violation found against both sources produces the same message."""

    names = {item.stage_id: item for item in preferred}
    result: list[_StageObligation] = []
    for item in obligations:
        shown = names.get(item.stage_id)
        if shown is None:
            result.append(item)
            continue
        labels = {f.field_id: f.label for f in shown.fields}
        result.append(
            replace(
                item,
                name=shown.name,
                fields=tuple(
                    replace(f, label=labels.get(f.field_id, f.label)) for f in item.fields
                ),
            )
        )
    return tuple(result)


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


def _narrowed_issues(obligation: _StageObligation, stage: WorkflowStage) -> list[ValidationIssue]:
    """RR-8a/b/c for one required stage obligation present in the candidate."""

    sid = stage.stage_id
    issues: list[ValidationIssue] = []
    if not applies_to_includes(stage.applies_to, obligation.applicability):
        unconditional = obligation.applicability is None
        issues.append(
            _issue(
                RatchetRule.RR_8,
                f"The required stage '{obligation.name}' applies to all entities and cannot "
                "become conditional."
                if unconditional
                else f"The required stage '{obligation.name}' cannot apply to fewer legal forms.",
                sid,
            )
        )
    for item in obligation.fields:
        found = next((f for f in stage.fields if f.field_id == item.field_id), None)
        if found is None or not found.required:
            continue  # RR-3 reports it
        effective = _field_applicability(stage, found)
        if applies_to_includes(effective, item.applicability):
            continue
        where = f"'{item.label}' in '{obligation.name}'"
        if applies_to_includes(found.applies_to, item.applicability):
            message = f"The required field {where} would apply to fewer legal forms because its "
            message += "step's legal forms narrowed."  # RR-8c
        elif item.applicability is None:
            message = f"The required field {where} applies to all entities and cannot become "
            message += "conditional."  # RR-8b
        else:
            message = f"The required field {where} cannot apply to fewer legal forms."  # RR-8a
        issues.append(_issue(RatchetRule.RR_8, message, sid, item.field_id))
    return issues


def applicability_issues(
    candidate: tuple[WorkflowStage, ...],
    baseline: RequiredBaseline,
    *,
    active: WorkflowVersion | None = None,
) -> tuple[ValidationIssue, ...]:
    """RR-8 (ADR-018 §4.1), against the active version and the baseline.

    - RR-8a: a required obligation's applicability narrowed;
    - RR-8b: an ALL obligation made conditional;
    - RR-8c: a required field narrowed through its stage's ``applies_to``.

    Missing or optional obligations are RR-1 / RR-3, not RR-8.
    """

    by_id: dict[str, WorkflowStage] = {}
    for stage in candidate:
        by_id.setdefault(stage.stage_id, stage)
    from_active = _active_obligations(active)
    from_baseline = _with_display_names(_baseline_obligations(baseline), from_active)
    issues: list[ValidationIssue] = []
    for obligation in (*from_active, *from_baseline):
        present = by_id.get(obligation.stage_id)
        if present is not None:
            issues.extend(_narrowed_issues(obligation, present))
    return tuple(issues)


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
            or _identity_key(stage.name) in _LOCKED_IDENTITY_KEYS
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
    """RR-1 to RR-10 against both the active version and the baseline; every violation.

    RR-9 is unchanged by ADR-018: code-owned stages are not ``WorkflowStage`` records, so they
    can never carry ``applies_to``, and an added stage still cannot impersonate one.
    """

    by_id: dict[str, WorkflowStage] = {}
    for stage in candidate:
        by_id.setdefault(stage.stage_id, stage)
    from_active = _active_obligations(active)
    from_baseline = _with_display_names(_baseline_obligations(baseline), from_active)
    found = [
        *_obligation_issues(from_active, by_id),
        *_obligation_issues(from_baseline, by_id),
        *applicability_issues(candidate, baseline, active=active),
        *_engine_order_issues(candidate, is_onboarding=is_onboarding),
    ]
    # The same violation found against both sources has the same text and is kept once;
    # distinct violations of one rule on one stage or field are all kept.
    unique: dict[tuple[str, str | None, str | None, str | None, str], ValidationIssue] = {}
    for issue in found:
        key = (
            issue.code,
            issue.rule.value if issue.rule else None,
            issue.stage_id,
            issue.field_id,
            issue.message,
        )
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

    def conditional(text: str, applicability: AppliesTo | None) -> str:
        # ADR-018 §4.4: a new conditional obligation is listed with its applicability.
        return text if applicability is None else f"{text} {_applies_text(applicability)}"

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
                    conditional(f"The stage '{stage.name}' becomes required.", stage.applies_to),
                )
            else:
                add(
                    ObligationKey(stage_id=stage.stage_id),
                    PermanentObligationChange.NEW_REQUIRED_STAGE,
                    stage,
                    conditional(f"New required stage '{stage.name}'.", stage.applies_to),
                )
        elif _broader(stage.applies_to, recorded.applicability):
            add(
                ObligationKey(stage_id=stage.stage_id),
                PermanentObligationChange.APPLICABILITY_BROADENED,
                stage,
                f"The required stage '{stage.name}' applies to more entities. "
                f"{_applies_text(stage.applies_to)}",
            )
        recorded_fields = {item.field_id: item for item in recorded.fields} if recorded else {}
        before_fields = {f.field_id: f for f in before.fields} if before else {}
        for field in stage.fields:
            if not field.required:
                continue
            key = ObligationKey(stage_id=stage.stage_id, field_id=field.field_id)
            item = recorded_fields.get(field.field_id)
            effective = _field_applicability(stage, field)
            if item is None:
                earlier = before_fields.get(field.field_id)
                if earlier is not None and not earlier.required:
                    add(
                        key,
                        PermanentObligationChange.TIGHTENED,
                        stage,
                        conditional(f"The field '{field.label}' becomes required.", effective),
                        field,
                    )
                else:
                    add(
                        key,
                        PermanentObligationChange.NEW_REQUIRED_FIELD,
                        stage,
                        conditional(f"New required field '{field.label}'.", effective),
                        field,
                    )
                continue
            broadened = _broader(effective, item.signature.applicability)
            reasons: list[str] = []
            allowed = item.signature.choice_options
            if (
                allowed is not None
                and field.kind == WorkflowFieldKind.CHOICE
                and not frozenset(allowed) <= _options(field)
            ):
                reasons.append("offers fewer options; removed options can never return")
            if item.signature.has_case_data_key and field.case_data_key is None:
                # ADR-017 §2: case_data_key is absent once absent (RR-7 refuses it later).
                reasons.append(
                    "no longer starts from case data; the case data key can never be added back"
                )
            if reasons:
                if broadened:
                    reasons.append(f"applies to more entities ({_applies_text(effective)[:-1]})")
                add(
                    key,
                    PermanentObligationChange.TIGHTENED,
                    stage,
                    f"The field '{field.label}' " + "; it ".join(reasons) + ".",
                    field,
                )
            elif broadened:
                add(
                    key,
                    PermanentObligationChange.APPLICABILITY_BROADENED,
                    stage,
                    f"The required field '{field.label}' applies to more entities. "
                    f"{_applies_text(effective)}",
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
        *structure_issues(candidate, is_onboarding=is_onboarding, active=active),
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


# --- Safe target (ADR-017 §2, §4; ADR-018 §4.3; used by M2 recovery publications) ---


def _target_mismatch(target: tuple[WorkflowStage, ...], baseline: RequiredBaseline) -> str | None:
    """Every baseline obligation must render with exactly its baseline applicability."""

    by_id = {stage.stage_id: stage for stage in target}
    for item in baseline.stages:
        stage = by_id.get(item.stage_id)
        if stage is None or stage.applies_to != item.applicability:
            return item.stage_id
        fields = {field.field_id: field for field in stage.fields}
        for entry in item.fields:
            field = fields.get(entry.field_id)
            if field is None or not field.required:
                return item.stage_id
            if _field_applicability(stage, field) != entry.signature.applicability:
                return item.stage_id
    return None


def safe_target(
    base_stages: tuple[WorkflowStage, ...], baseline: RequiredBaseline
) -> tuple[WorkflowStage, ...]:
    """``base ∪ required_baseline``: baseline obligations use their representative content.

    Every stage is built through the validated model constructor. Each baseline obligation
    renders with exactly its baseline (broadest) applicability (ADR-018 §4.3): a narrower
    ``base`` stage is widened to the baseline stage applicability. A safe target never
    broadens beyond the baseline and never silently narrows ``base`` content, so when ``base``
    is broader than the baseline (content that was only optional when ``base`` was published),
    or the union cannot satisfy field ⊆ stage, it raises ``SafeTargetError`` (fail closed).
    It also raises when the union would exceed a model limit, instead of returning it.
    """

    recorded = {stage.stage_id: stage for stage in baseline.stages}
    present_stages = {stage.stage_id for stage in base_stages}
    planned: list[tuple[str, str, str | None, AppliesTo | None, tuple[WorkflowField, ...]]] = []
    for stage in base_stages:
        item = recorded.get(stage.stage_id)
        if item is None:
            planned.append(
                (stage.stage_id, stage.name, stage.after_node_id, stage.applies_to, stage.fields)
            )
            continue
        if not applies_to_includes(item.applicability, stage.applies_to):
            raise SafeTargetError(
                f"The safe target stage '{stage.stage_id}' applies to more entities in the "
                "earlier version than its required baseline."
            )
        representatives = {field.field_id: field for field in item.fields}
        fields: list[WorkflowField] = []
        for field in stage.fields:
            entry = representatives.get(field.field_id)
            if entry is None:
                fields.append(field)
                continue
            if not applies_to_includes(
                entry.signature.applicability, _field_applicability(stage, field)
            ):
                raise SafeTargetError(
                    f"The safe target field '{field.field_id}' applies to more entities in the "
                    "earlier version than its required baseline."
                )
            fields.append(entry.representative)
        present = {field.field_id for field in stage.fields}
        fields.extend(
            field.representative for field in item.fields if field.field_id not in present
        )
        planned.append(
            (
                stage.stage_id,
                item.representative_name,
                stage.after_node_id,
                item.applicability,
                tuple(fields),
            )
        )
    planned.extend(
        (
            item.stage_id,
            item.representative_name,
            item.representative_after_node_id,
            item.applicability,
            tuple(field.representative for field in item.fields),
        )
        for item in baseline.stages
        if item.stage_id not in present_stages
    )
    if len(planned) > MAX_STAGES:
        raise SafeTargetError(
            f"The safe target would have {len(planned)} stages; the limit is {MAX_STAGES}."
        )
    result: list[WorkflowStage] = []
    for stage_id, name, after_node_id, applies_to, stage_fields in planned:
        if len(stage_fields) > MAX_FIELDS_PER_STAGE:
            raise SafeTargetError(
                f"The safe target stage '{stage_id}' would have {len(stage_fields)} fields; the "
                f"limit is {MAX_FIELDS_PER_STAGE}."
            )
        data: dict[str, object] = {
            "stage_id": stage_id,
            "name": name,
            "after_node_id": after_node_id,
            "fields": [field.model_dump() for field in stage_fields],
        }
        if applies_to is not None:
            data["applies_to"] = applies_to
        try:
            result.append(WorkflowStage.model_validate(data))
        except ValidationError as error:
            raise SafeTargetError(
                f"The safe target stage '{stage_id}' is not a valid stage."
            ) from error
    target = tuple(result)
    mismatch = _target_mismatch(target, baseline)
    if mismatch is not None:
        raise SafeTargetError(
            f"The safe target stage '{mismatch}' does not render its required baseline exactly."
        )
    return target
