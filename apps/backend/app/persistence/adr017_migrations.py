"""ADR-017 P2-0 schema migrations: the reviewed, dry-run-first reverse migration.

The reverse migration returns documents written by a P2-0 release to the shape the
pre-P2-0 code can decode (ADR-017 section 3.2, "Schema and safe rollback"):

* **Case documents** (schema 21 -> 20): a ledger ``workflow_dispatch`` claim is cleared
  only where the entry has no write attempt marker, or where the entry is finalised. An
  unfinalised entry with a Shell, Policy or Amend attempt keeps its recovery data and the
  migration **refuses**. The write nonce is dropped.
* **Workflow definition documents**: the P2-0 top-level fields (``write_nonce``,
  ``active_version``, ``latest_version``, ``dispatch_authorisation_seq``) are removed. A
  deactivated workflow (``active_version: 0`` after a publication) and any P2-1 governance
  content (outbox, notices, proposals, baseline) make the migration **refuse**; cold
  history is never touched. ``revision`` is unchanged, because legacy code requires the
  top-level revision to equal the payload revision.

Planning reads only. Applying is all-or-nothing: it refuses while the plan has any
refusal, and each document write is a compare-and-set on the revision and nonce that were
planned, under ``w: "majority", j: true``. Re-running after success finds nothing to do.

**Operational precondition (QG R0 P3-2):** run it only with every backend process stopped.
A write between planning and applying makes the apply stop at that document (a partial
revert); re-running with the backend stopped converges.

**Decode gate (QG R0 P3-4):** the legacy check is this release's ``DurableCaseSnapshotV20``
decoder, which must stay field-for-field identical to the pre-P2-0 schema-20 model.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pymongo.collection import Collection
from pymongo.write_concern import WriteConcern

from app.domain.target_submission import (
    WORKFLOW_DISPATCH_WRITE_OPERATIONS,
    GoldTierExecutionLedgerState,
)
from app.domain.workflows import WorkflowDefinition

DURABLE_WRITE_CONCERN = WriteConcern(w="majority", j=True, wtimeout=5_000)
P2_0_DEFINITION_FIELDS = (
    "write_nonce",
    "active_version",
    "latest_version",
    "dispatch_authorisation_seq",
)
# Present only from P2-1. This P2-0 tool never strips governance history it cannot archive.
P2_1_DEFINITION_FIELDS = (
    "required_baseline",
    "outbox",
    "notices",
    "proposals",
    "open_proposal",
    "decided_proposals",
    "governance_events",
    "p2_1_migration_marker",
)


@dataclass(frozen=True)
class MigrationRefusal:
    collection: str
    document_id: str
    reason: str


@dataclass(frozen=True)
class PlannedChange:
    document_id: str
    revision: int
    write_nonce: str | None
    replacement: Mapping[str, Any]


@dataclass
class ReverseMigrationPlan:
    cases: list[PlannedChange] = field(default_factory=list)
    definitions: list[PlannedChange] = field(default_factory=list)
    refusals: list[MigrationRefusal] = field(default_factory=list)
    already_reverted_cases: int = 0
    already_reverted_definitions: int = 0

    @property
    def refused(self) -> bool:
        return bool(self.refusals)

    def summary(self) -> dict[str, object]:
        """Safe identifiers and counts only; never document content."""

        return {
            "cases_to_revert": len(self.cases),
            "definitions_to_revert": len(self.definitions),
            "already_reverted_cases": self.already_reverted_cases,
            "already_reverted_definitions": self.already_reverted_definitions,
            "refusals": [
                {"collection": item.collection, "id": item.document_id, "reason": item.reason}
                for item in self.refusals
            ],
        }


class ReverseMigrationRefusedError(RuntimeError):
    """The plan contains refusals, or a document changed after it was planned."""


def _nonce_filter(nonce: str | None) -> dict[str, Any]:
    return {"write_nonce": {"$exists": False}} if nonce is None else {"write_nonce": nonce}


def _entry_has_write_marker(entry: Mapping[str, Any]) -> bool:
    attempted = entry.get("attempted_operations") or ()
    return any(item in WORKFLOW_DISPATCH_WRITE_OPERATIONS for item in attempted)


def _plan_case(
    raw: Mapping[str, Any], decode_legacy: Any
) -> tuple[PlannedChange | None, MigrationRefusal | None, bool]:
    document_id = str(raw.get("_id"))
    version = raw.get("schema_version")
    if type(version) is not int or version > 21 or version < 1:
        # P3-3: an unknown (future or corrupt) version is never counted as reverted.
        return None, MigrationRefusal("cases", document_id, "SCHEMA_VERSION_UNKNOWN"), False
    if version != 21:
        if "write_nonce" in raw:
            return None, MigrationRefusal("cases", document_id, "NONCE_ON_LEGACY_SCHEMA"), False
        return None, None, True
    revision = raw.get("revision")
    if type(revision) is not int:
        return None, MigrationRefusal("cases", document_id, "REVISION_INVALID"), False
    replacement = {key: copy.deepcopy(value) for key, value in raw.items() if key != "_id"}
    replacement.pop("write_nonce", None)
    replacement["schema_version"] = 20
    replacement["revision"] = revision + 1
    for entry in replacement.get("target_executions") or ():
        if not isinstance(entry, dict) or "workflow_dispatch" not in entry:
            continue
        finalised = entry.get("state") == GoldTierExecutionLedgerState.FINALIZED.value
        if _entry_has_write_marker(entry) and not finalised:
            return (
                None,
                MigrationRefusal("cases", document_id, "DISPATCH_WRITE_MARKER_NOT_FINALISED"),
                False,
            )
        entry.pop("workflow_dispatch")
    try:
        decode_legacy({**replacement, "_id": raw["_id"]})
    except Exception:  # noqa: BLE001 - any decode failure is a refusal, never a write
        return None, MigrationRefusal("cases", document_id, "LEGACY_DECODE_FAILED"), False
    nonce = raw.get("write_nonce")
    return (
        PlannedChange(
            document_id, revision, nonce if isinstance(nonce, str) else None, replacement
        ),
        None,
        False,
    )


def _plan_definition(
    raw: Mapping[str, Any],
) -> tuple[PlannedChange | None, MigrationRefusal | None, bool]:
    document_id = str(raw.get("_id"))
    if any(name in raw for name in P2_1_DEFINITION_FIELDS):
        return None, MigrationRefusal("definitions", document_id, "P2_1_CONTENT_PRESENT"), False
    if not any(name in raw for name in P2_0_DEFINITION_FIELDS):
        return None, None, True
    latest = raw.get("latest_version")
    if raw.get("active_version") == 0 and isinstance(latest, int) and latest > 0:
        return None, MigrationRefusal("definitions", document_id, "DEACTIVATED_WORKFLOW"), False
    try:
        WorkflowDefinition.model_validate(raw["payload"])
    except Exception:  # noqa: BLE001
        return None, MigrationRefusal("definitions", document_id, "LEGACY_DECODE_FAILED"), False
    revision = raw.get("revision")
    if type(revision) is not int:
        return None, MigrationRefusal("definitions", document_id, "REVISION_INVALID"), False
    nonce = raw.get("write_nonce")
    replacement = {
        key: copy.deepcopy(value)
        for key, value in raw.items()
        if key != "_id" and key not in P2_0_DEFINITION_FIELDS
    }
    return (
        PlannedChange(
            document_id, revision, nonce if isinstance(nonce, str) else None, replacement
        ),
        None,
        False,
    )


def plan_reverse_migration(
    cases: Collection[dict[str, Any]],
    definitions: Collection[dict[str, Any]],
    *,
    decode_legacy_case: Any,
) -> ReverseMigrationPlan:
    """Read-only. ``decode_legacy_case`` must be the pre-P2-0-compatible schema-20 decoder."""

    plan = ReverseMigrationPlan()
    for raw in cases.find({}):
        change, refusal, reverted = _plan_case(raw, decode_legacy_case)
        if refusal is not None:
            plan.refusals.append(refusal)
        elif change is not None:
            plan.cases.append(change)
        elif reverted:
            plan.already_reverted_cases += 1
    for raw in definitions.find({}):
        change, refusal, reverted = _plan_definition(raw)
        if refusal is not None:
            plan.refusals.append(refusal)
        elif change is not None:
            plan.definitions.append(change)
        elif reverted:
            plan.already_reverted_definitions += 1
    return plan


def apply_reverse_migration(
    plan: ReverseMigrationPlan,
    cases: Collection[dict[str, Any]],
    definitions: Collection[dict[str, Any]],
) -> dict[str, int]:
    """All-or-nothing gate, then one durable compare-and-set per planned document."""

    if plan.refused:
        raise ReverseMigrationRefusedError("the reverse migration plan has refusals")
    durable_cases = cases.with_options(write_concern=DURABLE_WRITE_CONCERN)
    durable_definitions = definitions.with_options(write_concern=DURABLE_WRITE_CONCERN)
    reverted = {"cases": 0, "definitions": 0}
    for change in plan.cases:
        result = durable_cases.replace_one(
            {
                "_id": change.document_id,
                "revision": change.revision,
                **_nonce_filter(change.write_nonce),
            },
            dict(change.replacement),
        )
        if result.modified_count != 1:
            raise ReverseMigrationRefusedError("a case changed after it was planned")
        reverted["cases"] += 1
    for change in plan.definitions:
        result = durable_definitions.replace_one(
            {
                "_id": change.document_id,
                "revision": change.revision,
                **_nonce_filter(change.write_nonce),
            },
            dict(change.replacement),
        )
        if result.modified_count != 1:
            raise ReverseMigrationRefusedError("a definition changed after it was planned")
        reverted["definitions"] += 1
    return reverted
