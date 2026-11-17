"""Workflow definition and run ports with process-local implementations (D-123)."""

from __future__ import annotations

import builtins
import secrets
from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.workflows import ONBOARDING_WORKFLOW_ID, WorkflowDefinition, WorkflowRun
from app.persistence.errors import PersistenceConflictError


class WorkflowDefinitionRepository(Protocol):
    def list(self) -> list[WorkflowDefinition]: ...

    def get(self, workflow_id: str) -> WorkflowDefinition | None: ...

    def create(self, definition: WorkflowDefinition) -> WorkflowDefinition: ...

    def update(
        self, definition: WorkflowDefinition, *, expected_revision: int
    ) -> WorkflowDefinition: ...

    def dispatch_active_version(self, workflow_id: str) -> int | None:
        """D1: the stored ``active_version``; None when missing or not backfilled."""
        ...

    def authorise_dispatch(self, workflow_id: str, version: int) -> bool:
        """D3: True only when this durable conditional increment applied."""
        ...

    def verify_dispatch_state(self) -> builtins.list[tuple[str, str]]:
        """Startup re-verification (ADR-017 3.5): (workflow_id, reason) per refusal."""
        ...


def _highest(definition: WorkflowDefinition) -> int:
    return max((item.version for item in definition.versions), default=0)


def verify_definition_state(definition: WorkflowDefinition) -> str | None:
    """The startup checks on one decoded definition (memory mode and shared rules)."""

    latest, active = definition.latest_version, definition.stored_active_version
    if latest is None or active is None:
        return "NOT_BACKFILLED"
    numbers = [item.version for item in definition.versions]
    if any(later <= earlier for earlier, later in zip(numbers, numbers[1:], strict=False)):
        return "VERSIONS_NOT_STRICTLY_INCREASING"
    if (numbers[-1] if numbers else 0) != latest:
        return "LAST_VERSION_NOT_LATEST"
    if active not in {0, latest}:
        return "ACTIVE_NOT_ZERO_OR_LATEST"
    if definition.workflow_id == ONBOARDING_WORKFLOW_ID and latest > 0 and active != latest:
        return "ONBOARDING_NOT_ACTIVE"
    return None


class WorkflowRunRepository(Protocol):
    def list_for_case(self, case_id: UUID) -> list[WorkflowRun]: ...

    def list_for_workflow(self, workflow_id: str) -> list[WorkflowRun]: ...

    def get(self, run_id: UUID) -> WorkflowRun | None: ...

    def create(self, run: WorkflowRun) -> WorkflowRun: ...

    def update(self, run: WorkflowRun, *, expected_revision: int) -> WorkflowRun: ...

    def delete_for_case(self, case_id: UUID) -> None: ...

    def delete(self, run_id: UUID) -> None: ...


class InMemoryWorkflowDefinitionRepository:
    """Memory mode: this lock orders D3 against every definition write (ADR-017 3.8)."""

    def __init__(self) -> None:
        self._items: dict[str, WorkflowDefinition] = {}
        self._dispatch_authorisations: dict[str, int] = {}
        self._lock = RLock()

    def list(self) -> list[WorkflowDefinition]:
        with self._lock:
            return sorted(self._items.values(), key=lambda item: item.created_at)

    def get(self, workflow_id: str) -> WorkflowDefinition | None:
        with self._lock:
            return self._items.get(workflow_id)

    def create(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        with self._lock:
            if definition.workflow_id in self._items:
                raise PersistenceConflictError
            highest = _highest(definition)
            # Every create writes the authoritative fields (ADR-017 3.5).
            stored = definition.model_copy(
                update={
                    "write_nonce": secrets.token_hex(16),
                    "stored_active_version": highest,
                    "latest_version": highest,
                }
            )
            self._items[definition.workflow_id] = stored
            return stored

    def update(
        self, definition: WorkflowDefinition, *, expected_revision: int
    ) -> WorkflowDefinition:
        with self._lock:
            current = self._items.get(definition.workflow_id)
            if (
                current is None
                or current.revision != expected_revision
                or current.write_nonce != definition.write_nonce
            ):
                raise PersistenceConflictError
            latest = current.latest_version
            if latest is not None and _highest(definition) > latest:
                # No ungoverned append may pass the high-water mark (activation is frozen).
                raise PersistenceConflictError
            stored = definition.model_copy(
                update={
                    "write_nonce": secrets.token_hex(16),
                    "stored_active_version": current.stored_active_version,
                    "latest_version": current.latest_version,
                }
            )
            self._items[definition.workflow_id] = stored
            return stored

    def dispatch_active_version(self, workflow_id: str) -> int | None:
        with self._lock:
            current = self._items.get(workflow_id)
            return None if current is None else current.stored_active_version

    def authorise_dispatch(self, workflow_id: str, version: int) -> bool:
        with self._lock:
            current = self._items.get(workflow_id)
            if (
                current is None
                or current.stored_active_version != version
                or current.latest_version != version
                or any(item.version == version + 1 for item in current.versions)
            ):
                return False
            self._dispatch_authorisations[workflow_id] = (
                self._dispatch_authorisations.get(workflow_id, 0) + 1
            )
            return True

    def verify_dispatch_state(self) -> builtins.list[tuple[str, str]]:
        with self._lock:
            return [
                (item.workflow_id, reason)
                for item in self._items.values()
                if (reason := verify_definition_state(item)) is not None
            ]


class InMemoryWorkflowRunRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, WorkflowRun] = {}
        self._lock = RLock()

    def list_for_case(self, case_id: UUID) -> list[WorkflowRun]:
        with self._lock:
            return sorted(
                (item for item in self._items.values() if item.case_id == case_id),
                key=lambda item: item.created_at,
            )

    def list_for_workflow(self, workflow_id: str) -> list[WorkflowRun]:
        with self._lock:
            return sorted(
                (item for item in self._items.values() if item.workflow_id == workflow_id),
                key=lambda item: item.created_at,
            )

    def get(self, run_id: UUID) -> WorkflowRun | None:
        with self._lock:
            return self._items.get(run_id)

    def create(self, run: WorkflowRun) -> WorkflowRun:
        with self._lock:
            if run.run_id in self._items:
                raise PersistenceConflictError
            self._items[run.run_id] = run
            return run

    def update(self, run: WorkflowRun, *, expected_revision: int) -> WorkflowRun:
        with self._lock:
            current = self._items.get(run.run_id)
            if current is None or current.revision != expected_revision:
                raise PersistenceConflictError
            self._items[run.run_id] = run
            return run

    def delete(self, run_id: UUID) -> None:
        with self._lock:
            self._items.pop(run_id, None)

    def delete_for_case(self, case_id: UUID) -> None:
        with self._lock:
            for run_id in [
                key for key, item in self._items.items() if item.case_id == case_id
            ]:
                del self._items[run_id]
