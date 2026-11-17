"""Test-only stand-in for governed publication while legacy activation is frozen (ADR-017).

P2-0 freezes ``POST /api/workflows/{id}/activate`` (409 WORKFLOW_PUBLICATION_FROZEN) and
governed publication arrives only in P2-1. Tests that need an active version publish it
the way governed publication will: one write that appends version ``latest_version + 1``
and sets ``active_version`` and ``latest_version`` to it. This helper writes only
process-local (memory) repositories and has no production caller.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

from app.domain.workflows import WorkflowStage, WorkflowVersion
from app.persistence.composition import WorkflowPersistence
from app.services.workflow_repository import (
    InMemoryWorkflowDefinitionRepository,
    InMemoryWorkflowRunRepository,
)

_STORES: dict[int, WorkflowPersistence] = {}


def memory_workflow_store() -> WorkflowPersistence:
    return WorkflowPersistence(
        definitions=InMemoryWorkflowDefinitionRepository(),
        runs=InMemoryWorkflowRunRepository(),
        close=lambda: None,
    )


@contextmanager
def capturing_workflow_store(store: WorkflowPersistence | None = None) -> Iterator[
    WorkflowPersistence
]:
    """Make ``create_app`` use (and expose to the test) a known memory workflow store."""

    active = store or memory_workflow_store()
    with patch("app.main.build_workflow_persistence", return_value=active):
        yield active


def register_app_store(app: Any, store: WorkflowPersistence) -> None:
    _STORES[id(app)] = store


def store_for(client_or_app: Any) -> WorkflowPersistence:
    app = getattr(client_or_app, "app", client_or_app)
    return _STORES[id(app)]


def publish_draft(
    definitions: Any,
    workflow_id: str,
    *,
    actor_id: str = "d-director",
    stages: tuple[WorkflowStage, ...] | None = None,
    now: datetime | None = None,
) -> Any:
    """Publish the stored draft (or ``stages``) as the next governed version."""

    if not isinstance(definitions, InMemoryWorkflowDefinitionRepository):
        raise TypeError("test publication writes memory repositories only")
    with definitions._lock:  # noqa: SLF001
        current = definitions._items[workflow_id]  # noqa: SLF001
        number = (current.latest_version or 0) + 1
        moment = now or datetime.now(UTC)
        version = WorkflowVersion(
            version=number,
            stages=current.draft_stages if stages is None else stages,
            activated_at=moment,
            activated_by=actor_id,
        )
        published = current.model_copy(
            update={
                "versions": (*current.versions, version),
                "revision": current.revision + 1,
                "updated_at": moment,
                "write_nonce": secrets.token_hex(16),
                "stored_active_version": number,
                "latest_version": number,
            }
        )
        definitions._items[workflow_id] = published  # noqa: SLF001
        return published


def bind_test_fence(service: Any) -> Any:
    """Bind a fence for a service built without ``create_app`` (tests only).

    Production binds the application's fence over its workflow store; a service with a
    durable ledger and no fence refuses every first write (fail closed). Tests that drive
    such a service directly bind this one: the service's own (possibly Mongo) ledger, with a
    process-local provisioned onboarding definition (``active_version: 0``, holds nothing).
    """

    from app.services.dispatch_fence import default_memory_fence

    service.bind_dispatch_fence(
        default_memory_fence(service.target_execution_repository, lambda: datetime.now(UTC))
    )
    return service
