"""ADR-017 section 3.2/3.3 fence writes on the case snapshot document (Mongo).

Every step is one ``find_one_and_update`` update pipeline under the durable write rule:
the filter asserts ``_id``, the revision and nonce read, and the identity-bearing predicate
of the targeted ledger element (state, own token, no write attempt marker, lease); the
pipeline rewrites only that element and sets a new nonce and revision. A step succeeds only
when that same write is durably acknowledged **and** its post-image shows the expected
element with own token and this step's fresh receipt. A modified count never authorises.
There are no confirming writes (CT-16 fallback mode): an ambiguous outcome stops.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from pymongo import ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from pymongo.write_concern import WriteConcern

from app.domain.target_submission import (
    WORKFLOW_DISPATCH_WRITE_OPERATIONS,
    GoldTierExecutionLedgerEntry,
    GoldTierExecutionLedgerState,
    GoldTierOperationMarker,
    WorkflowDispatchState,
)
from app.persistence.errors import PersistenceOutcomeAmbiguousError

FENCE_LEASE_MILLISECONDS = 60_000
DEFAULT_WTIMEOUT_MS = 5_000
MAX_WTIMEOUT_MS = 30_000
_WRITES = sorted(WORKFLOW_DISPATCH_WRITE_OPERATIONS)




def durable_write_concern(wtimeout_ms: int = DEFAULT_WTIMEOUT_MS) -> WriteConcern:
    if not 1 <= wtimeout_ms <= MAX_WTIMEOUT_MS:
        raise ValueError("wtimeout must be between 1 ms and 30 s")
    return WriteConcern(w="majority", j=True, wtimeout=wtimeout_ms)


def new_random() -> str:
    return secrets.token_hex(16)


def _element(submission_id: str) -> dict[str, Any]:
    return {
        "$first": {
            "$filter": {
                "input": "$target_executions",
                "cond": {"$eq": ["$$this.submission_input.submission_id", submission_id]},
            }
        }
    }


def _lease_live(submission_id: str) -> dict[str, Any]:
    return {
        "$let": {
            "vars": {"el": _element(submission_id)},
            "in": {"$gt": ["$$el.workflow_dispatch.lease_until", "$$NOW"]},
        }
    }


def _claim_free_or_expired_or_own(submission_id: str, token: str) -> dict[str, Any]:
    return {
        "$let": {
            "vars": {"el": _element(submission_id)},
            "in": {
                "$or": [
                    {"$eq": [{"$type": "$$el.workflow_dispatch"}, "missing"]},
                    {"$lte": ["$$el.workflow_dispatch.lease_until", "$$NOW"]},
                    {"$eq": ["$$el.workflow_dispatch.token", {"$literal": token}]},
                ]
            },
        }
    }


def _rewrite_element(submission_id: str, element: dict[str, Any]) -> dict[str, Any]:
    return {
        "$map": {
            "input": "$target_executions",
            "in": {
                "$cond": [
                    {"$eq": ["$$this.submission_input.submission_id", submission_id]},
                    {"$mergeObjects": ["$$this", element]},
                    "$$this",
                ]
            },
        }
    }


def _lease() -> dict[str, Any]:
    return {"$add": ["$$NOW", FENCE_LEASE_MILLISECONDS]}


def _base_filter(case_id: UUID, revision: int, nonce: str | None) -> dict[str, Any]:
    return {
        "_id": str(case_id),
        "revision": revision,
        "write_nonce": nonce if nonce is not None else {"$exists": False},
    }


def _no_write_marker() -> dict[str, Any]:
    return {"$nin": _WRITES}


class MongoFenceLedger:
    """D2, D4, D5 and claim clearing on one case snapshot collection."""

    def __init__(
        self, collection: Collection[dict[str, Any]], *, wtimeout_ms: int = DEFAULT_WTIMEOUT_MS
    ) -> None:
        self._collection = collection.with_options(
            write_concern=durable_write_concern(wtimeout_ms)
        )

    def _step(
        self, query: dict[str, Any], pipeline: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        try:
            return self._collection.find_one_and_update(
                query, pipeline, return_document=ReturnDocument.AFTER
            )
        except PyMongoError:
            # Timeout, wtimeout, writeConcernError, network error, unknown commit state:
            # never treated as done, and a post-image delivered with one never counts.
            raise PersistenceOutcomeAmbiguousError from None

    @staticmethod
    def _owned(
        post_image: dict[str, Any] | None, submission_id: str, token: str, receipt: str,
        state: WorkflowDispatchState,
    ) -> dict[str, Any] | None:
        if post_image is None:
            return None
        for element in post_image.get("target_executions") or ():
            if element.get("submission_input", {}).get("submission_id") != submission_id:
                continue
            claim = element.get("workflow_dispatch") or {}
            if (
                claim.get("token") == token
                and claim.get("receipt") == receipt
                and claim.get("state") == state.value
            ):
                return post_image
        return None

    def claim(
        self, *, case_id: UUID, revision: int, nonce: str | None, submission_id: UUID,
        token: str, version: int,
    ) -> dict[str, Any] | None:
        """D2: no claim, an expired claim, or own claim, with no write marker -> TENTATIVE."""

        sid, receipt = str(submission_id), new_random()
        query = {
            **_base_filter(case_id, revision, nonce),
            "target_executions": {
                "$elemMatch": {
                    "submission_input.submission_id": sid,
                    "state": GoldTierExecutionLedgerState.IN_PROGRESS.value,
                    "attempted_operations": _no_write_marker(),
                }
            },
            "$expr": _claim_free_or_expired_or_own(sid, token),
        }
        claim = {
            "workflow_dispatch": {
                "state": WorkflowDispatchState.TENTATIVE.value,
                "token": {"$literal": token},
                "version": {"$literal": version},
                "lease_until": _lease(),
                "receipt": {"$literal": receipt},
            }
        }
        pipeline = [
            {
                "$set": {
                    "target_executions": _rewrite_element(sid, claim),
                    "revision": {"$literal": revision + 1},
                    "write_nonce": {"$literal": new_random()},
                }
            }
        ]
        return self._owned(
            self._step(query, pipeline), sid, token, receipt, WorkflowDispatchState.TENTATIVE
        )

    def authorise(
        self, *, case_id: UUID, revision: int, nonce: str | None, submission_id: UUID,
        token: str, version: int,
    ) -> dict[str, Any] | None:
        """D4: own TENTATIVE claim for ``version``, lease live -> AUTHORISED (new lease)."""

        sid, receipt = str(submission_id), new_random()
        query = {
            **_base_filter(case_id, revision, nonce),
            "target_executions": {
                "$elemMatch": {
                    "submission_input.submission_id": sid,
                    "state": GoldTierExecutionLedgerState.IN_PROGRESS.value,
                    "attempted_operations": _no_write_marker(),
                    "workflow_dispatch.state": WorkflowDispatchState.TENTATIVE.value,
                    "workflow_dispatch.token": token,
                    "workflow_dispatch.version": version,
                }
            },
            "$expr": _lease_live(sid),
        }
        element = {
            "workflow_dispatch": {
                "state": WorkflowDispatchState.AUTHORISED.value,
                "token": {"$literal": token},
                "version": {"$literal": version},
                "d3_at": "$$NOW",
                "lease_until": _lease(),
                "receipt": {"$literal": receipt},
            }
        }
        pipeline = [
            {
                "$set": {
                    "target_executions": _rewrite_element(sid, element),
                    "revision": {"$literal": revision + 1},
                    "write_nonce": {"$literal": new_random()},
                }
            }
        ]
        return self._owned(
            self._step(query, pipeline), sid, token, receipt, WorkflowDispatchState.AUTHORISED
        )

    def first_write(
        self, *, case_id: UUID, revision: int, nonce: str | None, submission_id: UUID,
        token: str, operation: GoldTierOperationMarker,
    ) -> dict[str, Any] | None:
        """D5: own AUTHORISED claim, lease live, no write marker -> the attempt marker."""

        if operation.value not in WORKFLOW_DISPATCH_WRITE_OPERATIONS:
            raise ValueError("Only a Shell, Policy or Amend attempt is a dispatch")
        sid, receipt = str(submission_id), new_random()
        query = {
            **_base_filter(case_id, revision, nonce),
            "target_executions": {
                "$elemMatch": {
                    "submission_input.submission_id": sid,
                    "state": GoldTierExecutionLedgerState.IN_PROGRESS.value,
                    "attempted_operations": _no_write_marker(),
                    "workflow_dispatch.state": WorkflowDispatchState.AUTHORISED.value,
                    "workflow_dispatch.token": token,
                }
            },
            "$expr": _lease_live(sid),
        }
        element = {
            "attempted_operations": {
                "$concatArrays": ["$$this.attempted_operations", [operation.value]]
            },
            "workflow_dispatch": {
                "$mergeObjects": [
                    "$$this.workflow_dispatch",
                    {
                        "receipt": {"$literal": receipt},
                        "first_write": {
                            "operation": operation.value,
                            "version": "$$this.workflow_dispatch.version",
                            "token": {"$literal": token},
                            "receipt": {"$literal": receipt},
                        },
                    },
                ]
            },
        }
        pipeline = [
            {
                "$set": {
                    "target_executions": _rewrite_element(sid, element),
                    "revision": {"$literal": revision + 1},
                    "write_nonce": {"$literal": new_random()},
                }
            }
        ]
        post = self._owned(
            self._step(query, pipeline), sid, token, receipt, WorkflowDispatchState.AUTHORISED
        )
        if post is None:
            return None
        for element_raw in post.get("target_executions") or ():
            if element_raw.get("submission_input", {}).get("submission_id") == sid:
                first = (element_raw.get("workflow_dispatch") or {}).get("first_write") or {}
                if (
                    first.get("receipt") == receipt
                    and first.get("token") == token
                    and first.get("operation") == operation.value
                    and operation.value in (element_raw.get("attempted_operations") or ())
                ):
                    return post
        return None

    def clear_unattempted_claim(
        self, *, case_id: UUID, revision: int, nonce: str | None, submission_id: UUID
    ) -> bool:
        """Startup recovery (single process): remove a claim that has no write marker."""

        sid = str(submission_id)
        query = {
            **_base_filter(case_id, revision, nonce),
            "target_executions": {
                "$elemMatch": {
                    "submission_input.submission_id": sid,
                    "attempted_operations": _no_write_marker(),
                    "workflow_dispatch": {"$exists": True},
                }
            },
        }
        pipeline = [
            {
                "$set": {
                    "target_executions": {
                        "$map": {
                            "input": "$target_executions",
                            "in": {
                                "$cond": [
                                    {"$eq": ["$$this.submission_input.submission_id", sid]},
                                    {
                                        "$arrayToObject": {
                                            "$filter": {
                                                "input": {"$objectToArray": "$$this"},
                                                "as": "field",
                                                "cond": {
                                                    "$ne": ["$$field.k", "workflow_dispatch"]
                                                },
                                            }
                                        }
                                    },
                                    "$$this",
                                ]
                            },
                        }
                    },
                    "revision": {"$literal": revision + 1},
                    "write_nonce": {"$literal": new_random()},
                }
            }
        ]
        post = self._step(query, pipeline)
        if post is None:
            return False
        return all(
            "workflow_dispatch" not in item
            for item in post.get("target_executions") or ()
            if item.get("submission_input", {}).get("submission_id") == sid
        )


def entry_from(post_image: dict[str, Any], submission_id: UUID, decode: Any) -> tuple[
    GoldTierExecutionLedgerEntry, int, str | None, datetime
]:
    """Decode the post-image (full domain validation) and return the targeted entry."""

    snapshot = decode(post_image)
    for entry in snapshot.target_executions:
        if entry.submission_input.submission_id == submission_id:
            return entry, snapshot.revision, snapshot.write_nonce, snapshot.updated_at
    raise ValueError("fence post-image lost its ledger entry")
