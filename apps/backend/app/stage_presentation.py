"""OPQ S1: backend-authored, computed (never stored) presentation verdict per pipeline stage.

The node ``status`` keeps its existing meaning (execution or readiness). This module adds a
separate verdict that keeps four facts apart: execution completion, evidence validity, an
unresolved blocker, and an open operator review. It is derived only from facts the pipeline
projection already receives. It never feeds readiness, a gate, a send, an audit code or any
persisted record, and it introduces no rule of its own.

``blocks_send`` (per stage) is true whenever the stage is not done and something holds it:
RUNNING, ACTION_REQUIRED, BLOCKED or FAILED, or NOT_STARTED with a retained readiness blocker
mapped to it, or any open exception it owns or links. The only not-done stage that reports
false is FINAL_REVIEW_SEND waiting solely for the human confirmation (that confirmation is the
send action), and a NOT_STARTED stage with nothing retained against it.

No case-level "send available" flag is provided: the zero-touch confirmation gate also
re-evaluates readiness from live evidence, re-checks classification, registry provenance and
target-write permission, may run a fresh read-only Search, and checks the D-123 workflow send
hold, none of which this read-only projection can reproduce. The UI must never derive send
availability from these stage flags; it must use the existing confirmation exception and the
gate's own response.

Mapping to the report's section 7 matrix: COMPLETE_INFO is COMPLETE with an informational
``reason_code`` (NO_QUALIFYING_UBO, POC_BASIS_ACCEPTED, OWNERSHIP_SOURCE_PARTIAL, NO_RECORDS);
COMPLETE_REVIEW_ADVISED is REVIEW_ADVISED; SKIPPED (verified GoldTier match) is kept distinct.
COMPLETE always means nothing open: a retained blocker or open exception owned by the stage
turns it into ACTION_REQUIRED.

Owner decisions (2026-11-18): A1 an advised review does not count as done; A2 D-121/D-124
advisory behaviour is unchanged; A3 the UEN conflict stays owned by the Document stage and is
linked from Registry verification while unresolved; A6 additive, non-persisted field.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.zero_touch import (
    AUTOMATION_STAGE_ORDER,
    LEGACY_AUTOMATION_STAGE_ORDER,
    LEGACY_AUTOMATION_STAGE_ORDER_VERSION,
)

StagePresentationState = Literal[
    "NOT_STARTED",
    "RUNNING",
    "COMPLETE",
    "REVIEW_ADVISED",
    "ACTION_REQUIRED",
    "BLOCKED",
    "FAILED",
    "SKIPPED",
]

_CODE = re.compile(r"^[A-Z0-9_]{1,64}$")
_TARGET_CONFIRMATION = "TARGET_CONFIRMATION_REQUIRED"
_JURISDICTION_EXCEPTIONS = frozenset({"JURISDICTION_UNRESOLVED", "JURISDICTION_CONFLICT"})
# Exactly one owning node per automation stage, so each open exception is counted once.
_EXCEPTION_OWNER = {
    "REGISTRY": "ACRA_REGISTRY",
    "GOLDTIER_SEARCH": "GOLDTIER_SEARCH",
    "DOCUMENT": "DOCUMENT_IDP",
    "OWNERSHIP": "OWNERSHIP_UBO",
    "READINESS": "READINESS",
    "MOCK_GOLDTIER": "FINAL_REVIEW_SEND",
    "COMPLETE": "FINAL_REVIEW_SEND",
}
_BLOCKER_OWNER = {
    "REGISTRY_NOT_READY": "ACRA_REGISTRY",
    "REGISTRY_FAILED": "ACRA_REGISTRY",
    "CANONICAL_DATA_INVALID": "ACRA_REGISTRY",
    "DOCUMENT_REQUIRED": "DOCUMENT_IDP",
    "DOCUMENT_PROCESSING": "DOCUMENT_IDP",
    "DOCUMENT_REVIEW_INCOMPLETE": "DOCUMENT_IDP",
    "DOCUMENT_PROCESSING_FAILED": "DOCUMENT_IDP",
    "SOURCE_CONFLICT_REQUIRES_POLICY": "DOCUMENT_IDP",
    "OWNERSHIP_REQUIRED": "OWNERSHIP_UBO",
    "OWNERSHIP_ANALYSIS_INCOMPLETE": "OWNERSHIP_UBO",
    "OWNERSHIP_REVIEW_REQUIRED": "OWNERSHIP_UBO",
    "OWNERSHIP_ANALYSIS_FAILED": "OWNERSHIP_UBO",
    "GOVERNMENT_STATUS_REQUIRED": "OWNERSHIP_UBO",
    "GOLDTIER_SEARCH_REQUIRED": "GOLDTIER_SEARCH",
    "GOLDTIER_SEARCH_REVIEW_REQUIRED": "GOLDTIER_SEARCH",
    "GOLDTIER_SEARCH_FAILED": "GOLDTIER_SEARCH",
    "GOLDTIER_SEARCH_STALE": "GOLDTIER_SEARCH",
    "GOLDTIER_CLASSIFICATION_REQUIRED": "READINESS",
}
# Readiness-derived nodes whose BLOCKED status may only mean "not reached yet".
_READINESS_NODES = {
    "DOCUMENT_IDP": "DOCUMENT",
    "OWNERSHIP_UBO": "OWNERSHIP",
    "READINESS": "READINESS",
    "GOLDTIER_TARGET": "READINESS",
}
# F-1: OWNERSHIP_METHOD_UNSUPPORTED alone no longer means "no evidence". When relationships were
# calculated (e.g. a synthetic overlay on a legal form ``OTHER`` root) the stage reports
# REVIEW_ISSUES; with zero relationships it is still EVIDENCE_ABSENT via the relationship check.
_NO_EVIDENCE_ISSUES = frozenset({"OWNERSHIP_REQUIRED"})
_BASE_STATE: dict[str, StagePresentationState] = {
    "COMPLETE": "COMPLETE",
    "EMPTY": "COMPLETE",
    "SKIPPED": "SKIPPED",
    "NOT_REACHED": "NOT_STARTED",
    "IN_PROGRESS": "RUNNING",
    "REVIEW_REQUIRED": "ACTION_REQUIRED",
    "BLOCKED": "BLOCKED",
    "FAILED": "FAILED",
    "UNSUPPORTED": "BLOCKED",
}


class BrowserStagePresentation(BaseModel):
    """Display verdict for one pipeline stage; computed per response, never persisted.

    ``owned_exception_ids`` are counted by this stage; ``linked_exception_ids`` are owned and
    counted by another stage and are only shown here, so an issue counter that sums
    ``owned_exception_ids`` counts every open exception exactly once.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    state: StagePresentationState
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z0-9_]+$", max_length=64)
    # Bounded by the automation record's own exceptions; no cap that could fail a read.
    owned_exception_ids: tuple[str, ...] = Field(default_factory=tuple)
    linked_exception_ids: tuple[str, ...] = Field(default_factory=tuple)
    counts_as_done: bool
    blocks_send: bool


def _value(item: object) -> str:
    return str(getattr(item, "value", item))


def _code(value: object) -> str | None:
    text = None if value is None else _value(value)
    return text if text is not None and _CODE.match(text) else None


def _open(items: Iterable[Any]) -> list[Any]:
    return [item for item in items if _value(getattr(item, "status", "OPEN")) == "OPEN"]


def _exception_owner(item: Any) -> str | None:
    if _value(item.exception_type) == _TARGET_CONFIRMATION:
        return None  # The final human confirmation is the send step itself, not an issue.
    if _value(item.exception_type) in _JURISDICTION_EXCEPTIONS:
        return "JURISDICTION"
    return _EXCEPTION_OWNER.get(_value(item.stage), "READINESS")


def _not_reached(automation: Any, stage: str) -> bool:
    order = (
        LEGACY_AUTOMATION_STAGE_ORDER
        if getattr(automation, "stage_order_version", None)
        == LEGACY_AUTOMATION_STAGE_ORDER_VERSION
        else AUTOMATION_STAGE_ORDER
    )
    completed = {_value(item) for item in automation.completed_stages}
    current = _value(automation.current_stage) if automation.current_stage is not None else None
    if stage in completed or current is None or stage not in order or current not in order:
        return False
    return order.index(stage) > order.index(current)


def _ownership_reason(ownership: Any, *, advisory: bool, poc_accepted: bool) -> tuple[
    StagePresentationState, str | None
]:
    if advisory:
        issues = {_value(getattr(item, "code", "")) for item in getattr(ownership, "issues", ())}
        absent = not getattr(ownership, "relationships", ()) or bool(issues & _NO_EVIDENCE_ISSUES)
        return "REVIEW_ADVISED", "EVIDENCE_ABSENT" if absent else "REVIEW_ISSUES"
    if poc_accepted:
        return "COMPLETE", "POC_BASIS_ACCEPTED"
    if _value(getattr(ownership, "state", "")) == "ANALYZED" and not any(
        _value(item.threshold_result) == "MET"
        and _value(item.classification) == "PROVISIONAL_UBO_CANDIDATE"
        for item in getattr(ownership, "candidates", ())
    ):
        return "COMPLETE", "NO_QUALIFYING_UBO"
    return "COMPLETE", None


def present_stages(
    nodes: tuple[Any, ...],
    *,
    automation: Any,
    clm: Any,
    case: Any,
    reconciliation: Any | None,
    ownership: Any | None,
    ownership_poc_basis_accepted: bool = False,
) -> dict[str, BrowserStagePresentation]:
    """Return the presentation for every top-level node, keyed by ``node_id``."""

    exceptions = _open(automation.active_exceptions)
    owned: dict[str, list[str]] = {}
    for item in exceptions:
        owner = _exception_owner(item)
        if owner is not None:
            owned.setdefault(owner, []).append(str(item.exception_id))
    blockers: dict[str, list[str]] = {}
    for blocker in clm.readiness.blockers:
        blockers.setdefault(_BLOCKER_OWNER.get(_value(blocker), "READINESS"), []).append(
            _value(blocker)
        )
    open_discrepancies = (
        [item for item in reconciliation.discrepancies if _value(item.status) == "OPEN"]
        if reconciliation is not None
        else []
    )
    discrepancy_ids = {str(item.discrepancy_id) for item in open_discrepancies}
    identity_ids = {
        str(item.discrepancy_id)
        for item in open_discrepancies
        if _value(item.field_name) == "registration_identifier"
    }
    document_exception_ids = [
        str(item.exception_id) for item in exceptions if _value(item.stage) == "DOCUMENT"
    ]
    final_review_required = any(
        _value(item.exception_type) == _TARGET_CONFIRMATION for item in exceptions
    )
    ownership_current = (
        ownership is not None
        and clm.readiness.ownership.reference_id == str(ownership.analysis_id)
    )

    result: dict[str, BrowserStagePresentation] = {}
    for node in nodes:
        node_id = node.node_id
        state = _BASE_STATE.get(node.status, "BLOCKED")
        reason = _code(node.blocker_code) if state in {
            "ACTION_REQUIRED", "BLOCKED", "FAILED"
        } else None
        own = tuple(owned.get(node_id, ()))
        linked: tuple[str, ...] = ()
        stage_blockers = blockers.get(node_id, [])

        if node_id == "RECONCILIATION":
            linked = tuple(item for item in document_exception_ids if item in discrepancy_ids)
        if node_id == "ACRA_REGISTRY" and state == "COMPLETE":
            acquisition = getattr(case, "registry_acquisition", None)
            if identity_ids:
                # A3: owned by the Document stage, linked here until either path resolves it.
                state, reason = "ACTION_REQUIRED", "IDENTITY_CONFIRMATION_REQUIRED"
                linked = tuple(item for item in document_exception_ids if item in identity_ids)
            elif acquisition is not None and _value(acquisition.status) == "PARTIAL":
                reason = "OWNERSHIP_SOURCE_PARTIAL"
        elif node_id == "ACRA_REGISTRY" and state == "SKIPPED":
            reason = "VERIFIED_GOLDTIER_MATCH"
        if node.status == "EMPTY":
            reason = "NO_RECORDS"
        if node_id == "OWNERSHIP_UBO" and state == "COMPLETE" and ownership_current:
            state, reason = _ownership_reason(
                ownership,
                advisory=node.advisory_review is True,
                poc_accepted=ownership_poc_basis_accepted,
            )
        if node_id == "READINESS" and state in {"ACTION_REQUIRED", "BLOCKED"}:
            if stage_blockers:
                state, reason = "ACTION_REQUIRED", stage_blockers[0]
            elif not own:
                state, reason = "BLOCKED", "EARLIER_STAGE_BLOCKERS"
        if node_id == "GOLDTIER_TARGET" and state in {"ACTION_REQUIRED", "BLOCKED"}:
            # The package owns no blocker; it references readiness without recounting.
            state, reason = "BLOCKED", "EARLIER_STAGE_BLOCKERS"
        if (
            node_id == "FINAL_REVIEW_SEND"
            and state == "ACTION_REQUIRED"
            and final_review_required
            and not own
        ):
            # Never masks another open exception owned by this stage (counted below).
            reason = "FINAL_CONFIRMATION_REQUIRED"
        if stage_blockers and state in {"COMPLETE", "SKIPPED", "REVIEW_ADVISED"}:
            # COMPLETE means nothing open: a retained blocker mapped here keeps it open.
            state, reason = "ACTION_REQUIRED", stage_blockers[0]
        if (
            node_id in _READINESS_NODES
            and state == "BLOCKED"
            and not own
            and _not_reached(automation, _READINESS_NODES[node_id])
        ):
            state, reason = "NOT_STARTED", "WAITING_FOR_EARLIER_STEPS"
        if own and state not in {"BLOCKED", "FAILED"}:
            state = "ACTION_REQUIRED"
            reason = reason if reason not in {None, "NO_QUALIFYING_UBO", "POC_BASIS_ACCEPTED",
                                              "EVIDENCE_ABSENT", "REVIEW_ISSUES",
                                              "OWNERSHIP_SOURCE_PARTIAL"} else None
            reason = reason or _code(node.blocker_code) or "OPEN_EXCEPTION"

        held = bool(own or linked or stage_blockers)
        if (
            node_id == "FINAL_REVIEW_SEND"
            and reason == "FINAL_CONFIRMATION_REQUIRED"
            and not held
        ):
            blocks_send = False  # The confirmation is the send action, not a blocker of it.
        else:
            blocks_send = held or state in {"RUNNING", "ACTION_REQUIRED", "BLOCKED", "FAILED"}
        result[node_id] = BrowserStagePresentation(
            state=state,
            reason_code=reason,
            owned_exception_ids=own,
            linked_exception_ids=linked,
            counts_as_done=state in {"COMPLETE", "SKIPPED"},
            blocks_send=blocks_send,
        )
    return result
