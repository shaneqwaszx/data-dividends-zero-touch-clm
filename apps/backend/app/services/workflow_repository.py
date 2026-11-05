"""Workflow definition and run ports with process-local implementations (D-123)."""

from __future__ import annotations

from threading import RLock
from typing import Protocol
from uuid import UUID

from app.domain.workflows import WorkflowDefinition, WorkflowRun
from app.persistence.errors import PersistenceConflictError


class WorkflowDefinitionRepository(Protocol):
    def list(self) -> list[WorkflowDefinition]: ...

    def get(self, workflow_id: str) -> WorkflowDefinition | None: ...

    def create(self, definition: WorkflowDefinition) -> WorkflowDefinition: ...

    def update(
        self, definition: WorkflowDefinition, *, expected_revision: int
    ) -> WorkflowDefinition: ...


class WorkflowRunRepository(Protocol):
    def list_for_case(self, case_id: UUID) -> list[WorkflowRun]: ...

    def list_for_workflow(self, workflow_id: str) -> list[WorkflowRun]: ...

    def get(self, run_id: UUID) -> WorkflowRun | None: ...

    def create(self, run: WorkflowRun) -> WorkflowRun: ...

    def update(self, run: WorkflowRun, *, expected_revision: int) -> WorkflowRun: ...

    def delete_for_case(self, case_id: UUID) -> None: ...

    def delete(self, run_id: UUID) -> None: ...


class InMemoryWorkflowDefinitionRepository:
    def __init__(self) -> None:
        self._items: dict[str, WorkflowDefinition] = {}
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
            self._items[definition.workflow_id] = definition
            return definition

    def update(
        self, definition: WorkflowDefinition, *, expected_revision: int
    ) -> WorkflowDefinition:
        with self._lock:
            current = self._items.get(definition.workflow_id)
            if current is None or current.revision != expected_revision:
                raise PersistenceConflictError
            self._items[definition.workflow_id] = definition
            return definition


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
