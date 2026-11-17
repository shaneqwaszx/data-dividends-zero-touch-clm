"""Workflow definition and run ports with process-local implementations (D-123)."""

from __future__ import annotations

import builtins
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Protocol
from uuid import UUID

from app.domain.workflow_governance import RequiredBaseline, WorkflowGovernanceState
from app.domain.workflows import (
    ONBOARDING_WORKFLOW_ID,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowVersion,
)
from app.persistence.adr017_backfill import DefinitionFinding, verify_p2_1_definition_document
from app.persistence.errors import PersistenceConflictError, PersistenceDataInvalidError
from app.persistence.p2_1_migration import (
    MigrationRefusedError,
    PlannedMigration,
    plan_definition_migration,
    store_cold_inserts,
)
from app.persistence.workflow_governance_store import (
    ColdHistoryIntegrityError,
    ColdHistoryStore,
    GovernedDefinition,
    InMemoryColdHistoryStore,
    WorkflowGovernanceNotMigratedError,
    WorkflowHistoryUnavailableError,
    check_document_size,
    cold_version,
    compact_history,
    drain_outbox_entries,
    governed_document,
    prepare_governance_write,
)

__all__ = [
    "ColdHistoryIntegrityError",
    "GovernedDefinition",
    "WorkflowGovernanceNotMigratedError",
    "WorkflowHistoryUnavailableError",
]


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


class WorkflowGovernanceRepository(Protocol):
    """P2-1 governance persistence (ADR-017 1.1, 3.1, 3.2, 3.5, 5). Memory and Mongo
    implementations keep strict parity. Errors: ``PersistenceConflictError`` (409
    ``WORKFLOW_CONFLICT``), ``WorkflowGovernanceNotMigratedError`` (503
    ``WORKFLOW_GOVERNANCE_NOT_MIGRATED``), ``WorkflowHistoryUnavailableError`` and its
    ``ColdHistoryIntegrityError`` (503 ``WORKFLOW_HISTORY_UNAVAILABLE``),
    ``PersistenceOutcomeAmbiguousError`` / ``PersistenceUnavailableError`` (503)."""

    def get_governed(self, workflow_id: str) -> GovernedDefinition | None: ...

    def list_governed(self) -> builtins.list[GovernedDefinition]: ...

    def create_governed(
        self, definition: WorkflowDefinition, governance: WorkflowGovernanceState
    ) -> GovernedDefinition: ...

    def write_governance(
        self,
        definition: WorkflowDefinition,
        governance: WorkflowGovernanceState,
        *,
        expected_revision: int,
        active_version: int | None = None,
        latest_version: int | None = None,
    ) -> GovernedDefinition: ...

    def drain_outbox(self, workflow_id: str, *, now: datetime | None = None) -> int: ...

    def drain_all(self, *, now: datetime | None = None) -> int: ...

    def get_version(self, workflow_id: str, version: int) -> WorkflowVersion | None: ...

    def verify_governance_state(self) -> builtins.list[tuple[str, str]]: ...


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

    def __init__(
        self,
        cold_store: ColdHistoryStore | None = None,
        *,
        archive_confirming_writes: bool = False,
    ) -> None:
        self._items: dict[str, WorkflowDefinition] = {}
        self._dispatch_authorisations: dict[str, int] = {}
        # P2-1: the reserved top-level governance fields; absent = not migrated. P2-0
        # writes (``update``) never touch them, like the Mongo ``$set`` of payload only.
        self._governance: dict[str, WorkflowGovernanceState] = {}
        self._cold: ColdHistoryStore = (
            InMemoryColdHistoryStore() if cold_store is None else cold_store
        )
        self._confirming = archive_confirming_writes
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
        """P2-0 checks on unmigrated definitions; the P2-1 checks on migrated ones."""

        with self._lock:
            return [
                (item.workflow_id, reason)
                for item in self._items.values()
                if (
                    reason := self._verify_governed(item)
                    if self._state(item.workflow_id).migrated
                    else verify_definition_state(item)
                )
                is not None
            ]

    # --- P2-1 governance (memory mode; parity with ``MongoWorkflowDefinitionRepository``) --

    def _state(self, workflow_id: str) -> WorkflowGovernanceState:
        return self._governance.get(workflow_id, WorkflowGovernanceState())

    def _raw(self, definition: WorkflowDefinition) -> dict[str, Any]:
        return governed_document(
            definition,
            self._state(definition.workflow_id),
            write_nonce=definition.write_nonce,
            active_version=definition.stored_active_version,
            latest_version=definition.latest_version,
            dispatch_authorisation_seq=self._dispatch_authorisations.get(
                definition.workflow_id, 0
            ),
        )

    def _verify_governed(self, definition: WorkflowDefinition) -> str | None:
        return verify_p2_1_definition_document(self._raw(definition), cold=self._cold)

    def get_governed(self, workflow_id: str) -> GovernedDefinition | None:
        with self._lock:
            current = self._items.get(workflow_id)
            return None if current is None else GovernedDefinition(
                current, self._state(workflow_id)
            )

    def list_governed(self) -> builtins.list[GovernedDefinition]:
        with self._lock:
            return [
                GovernedDefinition(item, self._state(item.workflow_id)) for item in self.list()
            ]

    def create_governed(
        self, definition: WorkflowDefinition, governance: WorkflowGovernanceState
    ) -> GovernedDefinition:
        if not governance.migrated:
            raise WorkflowGovernanceNotMigratedError
        with self._lock:
            if definition.workflow_id in self._items:
                raise PersistenceConflictError
            highest = _highest(definition)
            stored = definition.model_copy(
                update={
                    "write_nonce": secrets.token_hex(16),
                    "stored_active_version": highest,
                    "latest_version": highest,
                }
            )
            check_document_size(
                governed_document(
                    stored,
                    governance,
                    write_nonce=stored.write_nonce,
                    active_version=highest,
                    latest_version=highest,
                )
            )
            self._items[definition.workflow_id] = stored
            self._governance[definition.workflow_id] = governance
            return GovernedDefinition(stored, governance)

    def write_governance(
        self,
        definition: WorkflowDefinition,
        governance: WorkflowGovernanceState,
        *,
        expected_revision: int,
        active_version: int | None = None,
        latest_version: int | None = None,
    ) -> GovernedDefinition:
        if not governance.migrated:
            raise WorkflowGovernanceNotMigratedError
        with self._lock:
            current = self._items.get(definition.workflow_id)
            if (
                current is None
                or current.revision != expected_revision
                or current.write_nonce != definition.write_nonce
            ):
                raise PersistenceConflictError
            if not self._state(definition.workflow_id).migrated:
                # Parity with the Mongo filter on the marker.
                raise PersistenceConflictError
            compacted, state, active, latest = prepare_governance_write(
                definition,
                governance,
                self._cold,
                current_active=current.stored_active_version,
                current_latest=current.latest_version,
                active_version=active_version,
                latest_version=latest_version,
            )
            stored = compacted.model_copy(
                update={
                    "write_nonce": secrets.token_hex(16),
                    "stored_active_version": active,
                    "latest_version": latest,
                }
            )
            check_document_size(
                governed_document(
                    stored,
                    state,
                    write_nonce=stored.write_nonce,
                    active_version=active,
                    latest_version=latest,
                )
            )
            self._items[definition.workflow_id] = stored
            self._governance[definition.workflow_id] = state
            return GovernedDefinition(stored, state)

    def drain_outbox(self, workflow_id: str, *, now: datetime | None = None) -> int:
        with self._lock:
            current = self._items.get(workflow_id)
            state = self._state(workflow_id)
            if current is None or not state.migrated or not state.outbox:
                return 0
            result = drain_outbox_entries(
                current,
                state,
                self._cold,
                now=now or datetime.now(UTC),
                confirming_writes=self._confirming,
            )
            if result.archived:
                active, latest = current.stored_active_version, current.latest_version
                if active is None or latest is None:
                    raise PersistenceDataInvalidError
                compacted, compacted_state = compact_history(
                    result.definition,
                    result.governance,
                    self._cold,
                    active_version=active,
                    latest_version=latest,
                )
                # Housekeeping rotates the nonce and keeps the revision (Mongo parity).
                stored = compacted.model_copy(update={"write_nonce": secrets.token_hex(16)})
                check_document_size(
                    governed_document(
                        stored,
                        compacted_state,
                        write_nonce=stored.write_nonce,
                        active_version=active,
                        latest_version=latest,
                    )
                )
                self._items[workflow_id] = stored
                self._governance[workflow_id] = compacted_state
            if result.error is not None:
                raise result.error
            return len(result.archived)

    def drain_all(self, *, now: datetime | None = None) -> int:
        with self._lock:
            identifiers = [item.workflow_id for item in self.list()]
            return sum(self.drain_outbox(workflow_id, now=now) for workflow_id in identifiers)

    def get_version(self, workflow_id: str, version: int) -> WorkflowVersion | None:
        with self._lock:
            current = self._items.get(workflow_id)
        if current is None:
            return None
        for item in current.versions:
            if item.version == version:
                return item
        latest = current.latest_version
        if latest is None or version > latest or version < 1:
            return None
        return cold_version(self._cold, workflow_id, version)

    def verify_governance_state(self) -> builtins.list[tuple[str, str]]:
        with self._lock:
            return [
                (item.workflow_id, reason)
                for item in self._items.values()
                if (reason := self._verify_governed(item)) is not None
            ]

    def migrate_to_governance(
        self,
        seed_baseline: Callable[[WorkflowVersion], RequiredBaseline],
        *,
        now: datetime | None = None,
    ) -> builtins.list[DefinitionFinding]:
        """Memory mode only: the P2-1 migration (ADR-017 1.4) of every unmigrated
        definition, with the same planner as the Mongo tool. Cold copies first, then the
        governance fields with the marker; payload unchanged. Returns the refusals;
        refused definitions stay unmigrated (governance stays 503 for them)."""

        moment = now or datetime.now(UTC)
        refusals: builtins.list[DefinitionFinding] = []
        with self._lock:
            for workflow_id, current in list(self._items.items()):
                if self._state(workflow_id).migrated:
                    continue
                outcome = plan_definition_migration(
                    self._raw(current), seed_baseline=seed_baseline, now=moment, cold=self._cold
                )
                if isinstance(outcome, DefinitionFinding):
                    refusals.append(outcome)
                    continue
                if not isinstance(outcome, PlannedMigration):
                    continue
                try:
                    store_cold_inserts(outcome, self._cold, now=moment)
                except (WorkflowHistoryUnavailableError, MigrationRefusedError) as exc:
                    refusals.append(DefinitionFinding(workflow_id, type(exc).__name__))
                    continue
                self._items[workflow_id] = current.model_copy(
                    update={"write_nonce": secrets.token_hex(16)}
                )
                self._governance[workflow_id] = outcome.governance
        return refusals


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
