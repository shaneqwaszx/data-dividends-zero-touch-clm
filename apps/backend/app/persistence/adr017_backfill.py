"""ADR-017 section 3.5 one-time P2-0 backfill and the startup re-verification.

Backfill (P2-0 only; never after P2-1): for every workflow definition document without
``latest_version``, set ``latest_version`` to the highest version number present and
``active_version`` to that same number (0 if none), ``dispatch_authorisation_seq`` to 0,
under the durable write rule, compare-and-set on the revision and nonce read. Apply
refuses while the plan has any refusal, then writes per document: a document that
changed after planning stops it, and a re-run resumes (QG R0 P3-6). Its rule is
valid only while every version is hot, nothing is archived or deactivated and every version
is a migrated pre-governance activation. Dry-run by default; idempotent.

Startup re-verification (every start): each definition document must have strictly
increasing hot version numbers whose last equals ``latest_version``; ``active_version`` is 0
or ``latest_version`` (onboarding: equal once anything is published); no version number
exceeds ``latest_version``. Any failure makes the fence refuse every dispatch. The P2-1
provenance rule applies only after the P2-1 migration marker, which P2-0 never writes.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pymongo.collection import Collection
from pymongo.write_concern import WriteConcern

from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowDefinition

DURABLE = WriteConcern(w="majority", j=True, wtimeout=5_000)
P2_1_MIGRATION_MARKER = "p2_1_migration_marker"


@dataclass(frozen=True)
class DefinitionFinding:
    workflow_id: str
    reason: str


@dataclass
class BackfillPlan:
    changes: list[tuple[str, int, str | None, int]] = field(default_factory=list)
    already_backfilled: int = 0
    refusals: list[DefinitionFinding] = field(default_factory=list)

    def summary(self) -> dict[str, object]:
        return {
            "to_backfill": [
                {"id": wid, "latest_version": version} for wid, _, _, version in self.changes
            ],
            "already_backfilled": self.already_backfilled,
            "refusals": [{"id": item.workflow_id, "reason": item.reason} for item in self.refusals],
        }


class BackfillRefusedError(RuntimeError):
    pass


def _versions(raw: Mapping[str, Any]) -> list[int]:
    definition = WorkflowDefinition.model_validate(raw["payload"])
    return [item.version for item in definition.versions]


def verify_definition_document(raw: Mapping[str, Any]) -> str | None:
    """The startup checks; return a refusal reason, or None when the document is sound."""

    workflow_id = str(raw.get("_id"))
    if P2_1_MIGRATION_MARKER in raw:
        return "P2_1_CONTENT_NOT_SUPPORTED_BY_P2_0"
    latest, active = raw.get("latest_version"), raw.get("active_version")
    if type(latest) is not int or type(active) is not int:
        return "NOT_BACKFILLED"
    try:
        versions = _versions(raw)
    except Exception:  # noqa: BLE001
        return "DEFINITION_INVALID"
    if any(later <= earlier for earlier, later in zip(versions, versions[1:], strict=False)):
        return "VERSIONS_NOT_STRICTLY_INCREASING"
    if (versions[-1] if versions else 0) != latest:
        return "LAST_VERSION_NOT_LATEST"
    if any(version > latest for version in versions):
        return "VERSION_ABOVE_LATEST"
    if active not in {0, latest}:
        return "ACTIVE_NOT_ZERO_OR_LATEST"
    if workflow_id == ONBOARDING_WORKFLOW_ID and latest > 0 and active != latest:
        return "ONBOARDING_NOT_ACTIVE"
    return None


def verify_definitions(raws: Iterable[Mapping[str, Any]]) -> list[DefinitionFinding]:
    findings = []
    for raw in raws:
        reason = verify_definition_document(raw)
        if reason is not None:
            findings.append(DefinitionFinding(str(raw.get("_id")), reason))
    return findings


def plan_backfill(definitions: Collection[dict[str, Any]]) -> BackfillPlan:
    plan = BackfillPlan()
    for raw in definitions.find({}):
        workflow_id = str(raw.get("_id"))
        if P2_1_MIGRATION_MARKER in raw:
            plan.refusals.append(DefinitionFinding(workflow_id, "P2_1_MIGRATED"))
            continue
        if "latest_version" in raw or "active_version" in raw:
            reason = verify_definition_document(raw)
            if reason is None:
                plan.already_backfilled += 1
            else:
                plan.refusals.append(DefinitionFinding(workflow_id, reason))
            continue
        try:
            versions = _versions(raw)
        except Exception:  # noqa: BLE001
            plan.refusals.append(DefinitionFinding(workflow_id, "DEFINITION_INVALID"))
            continue
        if any(later <= earlier for earlier, later in zip(versions, versions[1:], strict=False)):
            plan.refusals.append(DefinitionFinding(workflow_id, "VERSIONS_NOT_STRICTLY_INCREASING"))
            continue
        revision = raw.get("revision")
        if type(revision) is not int:
            plan.refusals.append(DefinitionFinding(workflow_id, "REVISION_INVALID"))
            continue
        nonce = raw.get("write_nonce")
        known_nonce = nonce if isinstance(nonce, str) else None
        plan.changes.append((workflow_id, revision, known_nonce, max(versions, default=0)))
    return plan


def apply_backfill(plan: BackfillPlan, definitions: Collection[dict[str, Any]]) -> int:
    if plan.refusals:
        raise BackfillRefusedError("the backfill plan has refusals")
    durable = definitions.with_options(write_concern=DURABLE)
    applied = 0
    for workflow_id, revision, nonce, latest in plan.changes:
        result = durable.update_one(
            {
                "_id": workflow_id,
                "revision": revision,
                "write_nonce": nonce if nonce is not None else {"$exists": False},
                "latest_version": {"$exists": False},
                "active_version": {"$exists": False},
            },
            {
                "$set": {
                    "latest_version": latest,
                    "active_version": latest,
                    "dispatch_authorisation_seq": 0,
                    # The backfill is a definition writer: it rotates the nonce. ``revision``
                    # stays equal to the payload revision that legacy code compares.
                    "write_nonce": secrets.token_hex(16),
                }
            },
        )
        if result.modified_count != 1:
            raise BackfillRefusedError("a definition changed after it was planned")
        applied += 1
    return applied
