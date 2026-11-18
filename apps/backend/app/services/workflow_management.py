"""Single owner of Director workflows and RM/onboarder field collection (D-123)."""

from __future__ import annotations

import logging
import weakref
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from threading import Lock, RLock
from typing import Literal, Protocol, cast
from uuid import NAMESPACE_OID, UUID, uuid4, uuid5

from app.connectors.idp import LocalDocumentProcessingError
from app.connectors.local_document_runtime import isolated_document_pages
from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability, Role
from app.domain.models import OnboardingCase
from app.domain.workflow_governance import (
    GovernanceErrorCode,
    GovernanceEvent,
    GovernanceEventKind,
    MigrationMarker,
    WorkflowGovernanceState,
)
from app.domain.workflows import (
    MAX_ANSWER_LENGTH,
    ONBOARDING_USE_CASE,
    ONBOARDING_WORKFLOW_ID,
    WorkflowAnswer,
    WorkflowAnswerSource,
    WorkflowAuditEvent,
    WorkflowCaseSource,
    WorkflowCompany,
    WorkflowDefinition,
    WorkflowField,
    WorkflowFieldKind,
    WorkflowRun,
    WorkflowStage,
    WorkflowStageConfirmation,
    WorkflowVersion,
)
from app.persistence.errors import PersistenceConflictError, PersistenceError
from app.persistence.workflow_governance_store import outbox_for_event
from app.services.workflow_autofill import (
    find_labelled_value,
    match_option,
    normalize_date,
    normalize_number,
)
from app.services.workflow_repository import (
    WorkflowDefinitionRepository,
    WorkflowGovernanceNotMigratedError,
    WorkflowGovernanceRepository,
    WorkflowRunRepository,
)

LOGGER = logging.getLogger(__name__)
HOLD_INCOMPLETE = "WORKFLOW_STAGE_INCOMPLETE"
HOLD_UNAVAILABLE = "WORKFLOW_STAGE_CHECK_UNAVAILABLE"
_FIELD_FILLER_ROLES = frozenset({Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER})

_NEVER_SAVED = 0
# The marker of a definition created already governed (no legacy data to migrate, D-7).
BORN_GOVERNED_TOOL_VERSION = "p2-1-born-governed"
_GOVERNANCE_METHODS = (
    "get_governed",
    "list_governed",
    "create_governed",
    "write_governance",
    "drain_outbox",
    "drain_all",
    "get_version",
    "verify_governance_state",
)

Reauthorize = Callable[[], AuthenticatedActor]


class WorkflowForbiddenError(Exception):
    pass


class WorkflowRouteRetiredError(Exception):
    """ADR-017 section 6: a retired legacy route (410 ``WORKFLOW_ROUTE_RETIRED``)."""

    code = GovernanceErrorCode.ROUTE_RETIRED.value


class WorkflowNotFoundError(Exception):
    pass


class WorkflowConflictError(Exception):
    pass


class WorkflowValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = message


class ConfirmationGate:
    """ADR-017 section 4 (R1-9, R2-5): the per-workflow confirmation gate.

    A stage confirmation takes the workflow's gate lock briefly to increment its in-progress
    counter before it enters the run's lock, and again to decrement it afterwards. The
    deactivation decision holds the same lock from checking the counter until its own
    compare-and-set completes, so no confirmation can begin between the check and the
    decision. Valid under the single-backend-process deployment (ADR-017 3.4).
    """

    def __init__(self) -> None:
        self._registry = Lock()
        # workflow id -> its gate entry; pruned once no caller uses it (QG P3-1).
        self._entries: dict[str, _GateEntry] = {}

    def _enter(self, workflow_id: str) -> _GateEntry:
        with self._registry:
            entry = self._entries.get(workflow_id)
            if entry is None:
                entry = self._entries[workflow_id] = _GateEntry()
            entry.users += 1
            return entry

    def _leave(self, workflow_id: str, entry: _GateEntry) -> None:
        with self._registry:
            entry.users -= 1
            if entry.users == 0 and entry.confirming == 0:
                self._entries.pop(workflow_id, None)

    @contextmanager
    def confirming(self, workflow_id: str) -> Iterator[None]:
        entry = self._enter(workflow_id)
        try:
            with entry.lock:
                entry.confirming += 1
            try:
                yield
            finally:
                with entry.lock:
                    entry.confirming -= 1
        finally:
            self._leave(workflow_id, entry)

    @contextmanager
    def holding(self, workflow_id: str) -> Iterator[None]:
        """Hold the workflow's gate (the deactivation decision, until its CAS completes)."""

        entry = self._enter(workflow_id)
        try:
            with entry.lock:
                yield
        finally:
            self._leave(workflow_id, entry)

    def in_progress(self, workflow_id: str) -> int:
        """The current count; meaningful to a caller inside ``holding(workflow_id)``."""

        with self._registry:
            entry = self._entries.get(workflow_id)
            return 0 if entry is None else entry.confirming

    def tracked(self) -> int:
        """How many workflows have a live gate entry (bounded by callers in flight)."""

        with self._registry:
            return len(self._entries)


class _GateEntry:
    __slots__ = ("confirming", "lock", "users")

    def __init__(self) -> None:
        self.lock = Lock()
        self.users = 0
        self.confirming = 0


_GATES: weakref.WeakKeyDictionary[object, ConfirmationGate] = weakref.WeakKeyDictionary()
_GATES_LOCK = Lock()


def confirmation_gate_for(definition_lock: object) -> ConfirmationGate:
    """The one gate shared by every service built on the same definition lock."""

    with _GATES_LOCK:
        gate = _GATES.get(definition_lock)
        if gate is None:
            gate = _GATES[definition_lock] = ConfirmationGate()
        return gate


def stored_active_version(definition: WorkflowDefinition) -> WorkflowVersion | None:
    """The version new runs use: the stored top-level ``active_version`` (ADR-017 3.5).

    0 means none (an empty or deactivated workflow). A definition that was never
    backfilled keeps the P2-0 rule (the newest version).
    """

    number = definition.stored_active_version
    if number is None:
        return definition.active_version
    if number == 0:
        return None
    return next((item for item in definition.versions if item.version == number), None)


class WorkflowCaseReader(Protocol):
    def get_case(self, case_id: UUID) -> OnboardingCase | None: ...

    def case_lock(self, case_id: UUID) -> RLock: ...


@dataclass(frozen=True)
class CaseWorkflowView:
    onboarding: WorkflowRun | None
    runs: tuple[WorkflowRun, ...]


def stage_blocks_send(stage: WorkflowStage) -> bool:
    return any(field.required for field in stage.fields)


def governance_store(
    definitions: WorkflowDefinitionRepository,
) -> WorkflowGovernanceRepository | None:
    """The P2-1 governance port of a definition store, or None when it has none."""

    if all(callable(getattr(definitions, name, None)) for name in _GOVERNANCE_METHODS):
        return cast(WorkflowGovernanceRepository, definitions)
    return None


def born_governed_state(
    workflow_id: str, *, now: datetime, actor_id: str | None
) -> WorkflowGovernanceState:
    """The governance fields of a definition created governed: no versions, an empty
    baseline, and its creation event awaiting archival (ADR-017 section 5, D-7)."""

    event = GovernanceEvent(
        sequence=1,
        occurred_at=now,
        actor_id=actor_id,
        kind=GovernanceEventKind.WORKFLOW_CREATED,
        summary="Created workflow; unpublished until a proposal is approved",
    )
    return WorkflowGovernanceState(
        migration_marker=MigrationMarker(
            migrated_at=now,
            tool_version=BORN_GOVERNED_TOOL_VERSION,
            legacy_versions=0,
            legacy_draft_converted=False,
        ),
        governance_events=(event,),
        outbox=(outbox_for_event(workflow_id, event),),
        governance_sequence=1,
    )


@dataclass(frozen=True)
class ActiveOnboardingStages:
    """What the send check would enforce on a new open onboarding case, read-only."""

    state: Literal["ACTIVE", "NO_ACTIVE_WORKFLOW", "UNAVAILABLE"]
    version: int | None
    stages: tuple[WorkflowStage, ...]


class WorkflowManagementService:
    def __init__(
        self,
        *,
        definitions: WorkflowDefinitionRepository,
        runs: WorkflowRunRepository,
        cases: WorkflowCaseReader,
        case_is_sent: Callable[[UUID], bool] | None = None,
        case_is_onboarded: Callable[[UUID], bool] | None = None,
        case_data: Callable[[UUID], Mapping[str, str]] | None = None,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self._definitions = definitions
        self._runs = runs
        self._cases = cases
        self._case_is_sent = case_is_sent or (lambda _case_id: False)
        self._case_is_onboarded = case_is_onboarded or (lambda _case_id: False)
        self._case_data = case_data or (lambda _case_id: {})
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._lock = RLock()
        self._gate = confirmation_gate_for(self._lock)

    @property
    def definition_lock(self) -> RLock:
        """The one lock that orders every definition write (governance shares it)."""

        return self._lock

    @property
    def confirmation_gate(self) -> ConfirmationGate:
        """The confirmation gate shared with the deactivation decision (ADR-017 4)."""

        return self._gate

    # HR and Director: definitions (HR authors, a Director decides; both read).

    def list_workflows(self, actor: AuthenticatedActor) -> list[WorkflowDefinition]:
        self._require_reader(actor)
        with self._lock:
            # A read never creates a definition (ADR-017 R1-2); provisioning is at startup.
            return self._definitions.list()

    def startable_workflows(self, actor: AuthenticatedActor) -> list[WorkflowDefinition]:
        """The active workflows an RM or onboarder can start; none for any other role."""

        if actor.profile.role not in _FIELD_FILLER_ROLES:
            return []
        return [
            item
            for item in self._definitions.list()
            if not item.is_onboarding and stored_active_version(item) is not None
        ]

    def runs_for_workflow(
        self, actor: AuthenticatedActor, workflow_id: str
    ) -> list[tuple[WorkflowRun, OnboardingCase | None]]:
        """Runs this actor's team owns, and case runs for the caller to check by case."""

        self._require_filler(actor)
        pairs: list[tuple[WorkflowRun, OnboardingCase | None]] = []
        for run in self._runs.list_for_workflow(workflow_id):
            if run.case_id is None:
                if _owns(actor, run):
                    pairs.append((run, None))
                continue
            case = self._cases.get_case(run.case_id)
            if case is not None:
                pairs.append((run, case))
        return pairs

    def create_workflow_case(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        *,
        legal_name: str,
        registration_id: str,
        jurisdiction: str | None,
        priority: int | None,
    ) -> WorkflowRun:
        with self._lock:
            actor = reauthorize()
            self._require_filler(actor)
            definition = self._require_definition(workflow_id)
            version = stored_active_version(definition)
            team_id = actor.profile.team_id
            if (
                version is None
                or definition.case_source != WorkflowCaseSource.NEW_CASE
                or team_id is None
            ):
                raise WorkflowValidationError(
                    "WORKFLOW_NOT_STARTABLE", "This workflow does not open new cases."
                )
            now = self._clock()
            return self._runs.create(
                WorkflowRun(
                    run_id=self._uuid_factory(),
                    company=WorkflowCompany(
                        legal_name=legal_name,
                        registration_id=registration_id,
                        jurisdiction=jurisdiction,
                        priority=priority,
                        team_id=str(team_id),
                    ),
                    workflow_id=definition.workflow_id,
                    workflow_name=definition.name,
                    use_case=definition.use_case,
                    workflow_version=version.version,
                    stages=version.stages,
                    revision=1,
                    started_by=actor.profile.user_id,
                    created_at=now,
                    updated_at=now,
                )
            )

    def save_workflow_case_answers(
        self,
        reauthorize: Reauthorize,
        *,
        workflow_id: str,
        run_id: UUID,
        stage_id: str,
        expected_revision: int,
        values: Mapping[str, str],
    ) -> WorkflowRun:
        with self._cases.case_lock(run_id):
            run = self._owned_run(reauthorize(), workflow_id, run_id, expected_revision)
            return self._with_answers(run, stage_id, values)

    def confirm_workflow_case_stage(
        self,
        reauthorize: Reauthorize,
        *,
        workflow_id: str,
        run_id: UUID,
        stage_id: str,
        expected_revision: int,
    ) -> WorkflowRun:
        # Authorize and resolve the run first, so only a real, owned run's workflow id
        # ever reaches the gate (QG P3-1); then re-check inside the run's lock.
        self._owned_run(reauthorize(), workflow_id, run_id, None)
        with self._gate.confirming(workflow_id), self._cases.case_lock(run_id):
            actor = reauthorize()
            run = self._owned_run(actor, workflow_id, run_id, expected_revision)
            return self._with_confirmation(run, stage_id, actor)

    def suggest_for_workflow_case(
        self,
        reauthorize: Reauthorize,
        *,
        workflow_id: str,
        run_id: UUID,
        content: bytes,
        media_type: str,
        extracted_text: str | None,
    ) -> WorkflowRun:
        """Read one upload for suggestions; the document itself is never kept."""

        with self._cases.case_lock(run_id):
            run = self._owned_run(reauthorize(), workflow_id, run_id, None)
            if _autofill_fields(run):
                pages = _document_pages(content, media_type, extracted_text)
                self._apply_suggestions(run, self._uuid_factory(), pages)
            return self._owned_run(reauthorize(), workflow_id, run_id, None)

    def require_workflow_case(
        self, actor: AuthenticatedActor, workflow_id: str, run_id: UUID
    ) -> None:
        self._owned_run(actor, workflow_id, run_id, None)

    def delete_workflow_case(
        self, reauthorize: Reauthorize, *, workflow_id: str, run_id: UUID
    ) -> None:
        with self._cases.case_lock(run_id):
            actor = reauthorize()
            self._owned_run(actor, workflow_id, run_id, None)
            if actor.profile.role != Role.RELATIONSHIP_MANAGER:
                raise WorkflowForbiddenError
            self._runs.delete(run_id)

    def get_workflow(self, actor: AuthenticatedActor, workflow_id: str) -> WorkflowDefinition:
        self._require_reader(actor)
        with self._lock:
            return self._require_definition(workflow_id)

    def create_workflow(
        self,
        reauthorize: Reauthorize,
        *,
        name: str,
        use_case: str,
        country: str,
        case_source: WorkflowCaseSource = WorkflowCaseSource.EXISTING_CASE,
    ) -> WorkflowDefinition:
        """HR creates an empty non-onboarding workflow, born governed (D-7).

        It has no version (``active_version: 0``), starts no run and stays a draft until an
        approved proposal publishes its first version. A store that is not migrated refuses
        (503 ``WORKFLOW_GOVERNANCE_NOT_MIGRATED``) instead of creating an ungoverned document.
        """

        with self._lock:
            actor = reauthorize()
            self._require_author(actor)
            if use_case.strip().casefold() == ONBOARDING_USE_CASE.casefold():
                raise WorkflowValidationError(
                    "WORKFLOW_USE_CASE_RESERVED",
                    "Onboarding has one workflow. Add stages to it instead.",
                )
            store = self._governed_store()
            if store is None:
                raise WorkflowGovernanceNotMigratedError
            now = self._clock()
            workflow_id = str(self._uuid_factory())
            try:
                created = store.create_governed(
                    WorkflowDefinition(
                        workflow_id=workflow_id,
                        name=name,
                        use_case=use_case,
                        country=country,
                        case_source=case_source,
                        audit=(self._audit(actor, now, "CREATED", "Created workflow"),),
                        created_at=now,
                        updated_at=now,
                    ),
                    born_governed_state(workflow_id, now=now, actor_id=actor.profile.user_id),
                )
            except PersistenceConflictError:
                raise WorkflowConflictError from None
            _drain_after_commit(store, workflow_id, now)
            return created.definition

    def save_draft(
        self,
        reauthorize: Reauthorize,
        workflow_id: str,
        *,
        expected_revision: int,
        stages: tuple[WorkflowStage, ...],
    ) -> WorkflowDefinition:
        """Retired (ADR-017 section 6, PR-5): HR edits a proposal instead. Writes nothing."""

        del workflow_id, expected_revision, stages
        with self._lock:
            reauthorize()
            raise WorkflowRouteRetiredError

    def activate(
        self, reauthorize: Reauthorize, workflow_id: str, *, expected_revision: int
    ) -> WorkflowDefinition:
        """Retired (ADR-017 section 6, PR-4): a Director's approval publishes a version.

        The caller is still reauthorized. Nothing is read for writing and nothing is written.
        """

        del workflow_id, expected_revision
        with self._lock:
            reauthorize()
            raise WorkflowRouteRetiredError

    def start_run(
        self, reauthorize: Reauthorize, workflow_id: str, *, case_id: UUID
    ) -> WorkflowRun:
        with self._cases.case_lock(case_id), self._lock:
            actor = reauthorize()
            self._require_filler(actor)
            definition = self._require_definition(workflow_id)
            # The stored active version: a deactivated workflow (0) starts no run.
            version = stored_active_version(definition)
            if definition.is_onboarding or version is None:
                raise WorkflowValidationError(
                    "WORKFLOW_NOT_STARTABLE", "Only an active non-onboarding workflow can start."
                )
            if definition.case_source != WorkflowCaseSource.EXISTING_CASE:
                raise WorkflowValidationError(
                    "WORKFLOW_NOT_STARTABLE", "This workflow opens its own new cases."
                )
            if not self._case_is_onboarded(case_id):
                raise WorkflowValidationError(
                    "WORKFLOW_CASE_NOT_ONBOARDED", "Choose a case that has finished onboarding."
                )
            if any(run.workflow_id == workflow_id for run in self._runs.list_for_case(case_id)):
                raise WorkflowConflictError
            now = self._clock()
            return self._runs.create(
                WorkflowRun(
                    run_id=self._uuid_factory(),
                    case_id=case_id,
                    answers=self._loaded_answers(case_id, version.stages),
                    workflow_id=definition.workflow_id,
                    workflow_name=definition.name,
                    use_case=definition.use_case,
                    workflow_version=version.version,
                    stages=version.stages,
                    revision=1,
                    started_by=actor.profile.user_id,
                    created_at=now,
                    updated_at=now,
                )
            )

    # Case: RM/onboarder field collection.

    def case_view(self, case: OnboardingCase) -> CaseWorkflowView:
        stored = self._runs.list_for_case(case.case_id)
        return CaseWorkflowView(
            onboarding=self._onboarding_run(case, stored),
            runs=tuple(run for run in stored if not run.is_onboarding),
        )

    def save_answers(
        self,
        reauthorize: Reauthorize,
        *,
        case_id: UUID,
        run_id: UUID,
        stage_id: str,
        expected_revision: int,
        values: Mapping[str, str],
    ) -> WorkflowRun:
        with self._cases.case_lock(case_id):
            self._require_filler(reauthorize())
            run = self._open_run(case_id, run_id, expected_revision)
            self._require_not_sent(run, case_id)
            return self._with_answers(run, stage_id, values)

    def confirm_stage(
        self,
        reauthorize: Reauthorize,
        *,
        case_id: UUID,
        run_id: UUID,
        stage_id: str,
        expected_revision: int,
    ) -> WorkflowRun:
        stored = self._runs.get(run_id)
        # An unsaved onboarding run has no stored record; onboarding is never deactivated.
        gated = stored.workflow_id if stored is not None else ONBOARDING_WORKFLOW_ID
        with self._gate.confirming(gated), self._cases.case_lock(case_id):
            actor = reauthorize()
            self._require_filler(actor)
            run = self._open_run(case_id, run_id, expected_revision)
            self._require_not_sent(run, case_id)
            return self._with_confirmation(run, stage_id, actor)

    # Integration hooks. Neither may change a case's outcome when nothing is configured.

    def send_hold_code(self, case_id: UUID) -> str | None:
        """Return why a case may not be sent; any failure refuses the send (fail closed)."""

        try:
            case = self._cases.get_case(case_id)
            if case is None:
                return None
            run = self._onboarding_run(case, self._runs.list_for_case(case_id))
            if run is None:
                return None
            confirmed = run.confirmed_stage_ids
            incomplete = any(
                stage_blocks_send(stage) and stage.stage_id not in confirmed
                for stage in run.stages
            )
            return HOLD_INCOMPLETE if incomplete else None
        except Exception:
            LOGGER.warning("workflow send check unavailable", extra={"case_id": str(case_id)})
            return HOLD_UNAVAILABLE

    def active_onboarding_stages(self) -> ActiveOnboardingStages:
        """Read the active onboarding version for display, never creating anything.

        It reads the stored definition and never creates one (ADR-017 R1-2; provisioning is
        at startup). A definition with no active version is "no active workflow". A missing
        onboarding definition document is "unavailable" (ADR-017 3.6, the D-136 E2
        amendment), as is any read or decode failure; the send check refuses on both.
        """

        try:
            definition = self._definitions.get(ONBOARDING_WORKFLOW_ID)
        except Exception:
            LOGGER.warning("workflow store unavailable for the execution plan")
            return ActiveOnboardingStages(state="UNAVAILABLE", version=None, stages=())
        if definition is None:
            return ActiveOnboardingStages(state="UNAVAILABLE", version=None, stages=())
        version = definition.active_version
        if version is None:
            return ActiveOnboardingStages(state="NO_ACTIVE_WORKFLOW", version=None, stages=())
        return ActiveOnboardingStages(
            state="ACTIVE", version=version.version, stages=version.stages
        )

    def suggest_from_document(
        self, *, case_id: UUID, document_id: UUID, content: bytes, media_type: str,
        extracted_text: str | None,
    ) -> None:
        """Keep matched values as unconfirmed suggestions; never fail the upload."""

        try:
            case = self._cases.get_case(case_id)
            if case is None:
                return
            view = self.case_view(case)
            # A sent case keeps its onboarding stages exactly as they were sent.
            onboarding = None if self._case_is_sent(case_id) else view.onboarding
            runs = [run for run in (onboarding, *view.runs) if run is not None]
            if not any(_autofill_fields(run) for run in runs):
                return
            pages = _document_pages(content, media_type, extracted_text)
            for run in runs:
                self._apply_suggestions(run, document_id, pages)
        except Exception:
            LOGGER.warning("workflow autofill skipped", extra={"case_id": str(case_id)})

    def delete_case_data(self, case_id: UUID) -> Callable[[], None]:
        """Delete a case's answers and return how to put them back if the case survives."""

        removed = self._runs.list_for_case(case_id)
        self._runs.delete_for_case(case_id)

        def restore() -> None:
            for run in removed:
                self._runs.create(run)

        return restore

    # Internals.

    def _loaded_answers(
        self, case_id: UUID, stages: tuple[WorkflowStage, ...]
    ) -> tuple[WorkflowAnswer, ...]:
        """Start each field from the onboarded case, leaving unknown values empty."""

        values = self._case_data(case_id)
        collected = self._onboarding_answers(case_id)
        answers: list[WorkflowAnswer] = []
        for stage in stages:
            for field in stage.fields:
                raw = (
                    values.get(field.case_data_key)
                    if field.case_data_key is not None
                    else collected.get((stage.name.casefold(), field.label.casefold()))
                )
                try:
                    value = None if raw is None else _validated_answer(field, raw)
                except WorkflowValidationError:
                    value = None
                if value is not None:
                    answers.append(
                        WorkflowAnswer(
                            stage_id=stage.stage_id,
                            field_id=field.field_id,
                            value=value,
                            source=WorkflowAnswerSource.CASE,
                        )
                    )
        return tuple(answers)

    def _onboarding_answers(self, case_id: UUID) -> dict[tuple[str, str], str]:
        """Answers given to added onboarding stages, by stage and field name."""

        result: dict[tuple[str, str], str] = {}
        for run in self._runs.list_for_case(case_id):
            if not run.is_onboarding:
                continue
            for stage in run.stages:
                for field in stage.fields:
                    for answer in run.answers:
                        if (answer.stage_id, answer.field_id) == (stage.stage_id, field.field_id):
                            result[(stage.name.casefold(), field.label.casefold())] = answer.value
        return result

    def _require_not_sent(self, run: WorkflowRun, case_id: UUID) -> None:
        if run.is_onboarding and self._case_is_sent(case_id):
            raise WorkflowValidationError(
                "WORKFLOW_CASE_SENT", "This case has been sent, so its stages are closed."
            )

    def _with_answers(
        self, run: WorkflowRun, stage_id: str, values: Mapping[str, str]
    ) -> WorkflowRun:
        stage = self._open_stage(run, stage_id)
        fields = {field.field_id: field for field in stage.fields}
        if set(values) - set(fields):
            raise WorkflowValidationError(
                "WORKFLOW_FIELD_UNKNOWN", "A submitted field is not part of this stage."
            )
        existing = {item.field_id: item for item in run.answers if item.stage_id == stage_id}
        for field_id, raw in values.items():
            value = _validated_answer(fields[field_id], raw)
            previous = existing.get(field_id)
            if value is None:
                existing.pop(field_id, None)
            elif (
                previous is None
                or previous.value != value
                or previous.source == WorkflowAnswerSource.DOCUMENT
            ):
                # Saving a suggestion makes it the person's answer, so later uploads leave it.
                existing[field_id] = WorkflowAnswer(
                    stage_id=stage_id, field_id=field_id, value=value
                )
        return self._persist(
            run,
            answers=(
                *(item for item in run.answers if item.stage_id != stage_id),
                *existing.values(),
            ),
            confirmations=tuple(
                item for item in run.confirmations if item.stage_id != stage_id
            ),
        )

    def _with_confirmation(
        self, run: WorkflowRun, stage_id: str, actor: AuthenticatedActor
    ) -> WorkflowRun:
        stage = self._open_stage(run, stage_id)
        answered = {item.field_id for item in run.answers if item.stage_id == stage_id}
        if any(field.required and field.field_id not in answered for field in stage.fields):
            raise WorkflowValidationError(
                "WORKFLOW_REQUIRED_FIELD_MISSING", "Fill in every required field first."
            )
        confirmation = WorkflowStageConfirmation(
            stage_id=stage_id,
            confirmed_by=actor.profile.user_id,
            confirmed_at=self._clock(),
        )
        return self._persist(
            run,
            confirmations=(
                *(item for item in run.confirmations if item.stage_id != stage_id),
                confirmation,
            ),
        )

    def _owned_run(
        self,
        actor: AuthenticatedActor,
        workflow_id: str,
        run_id: UUID,
        expected_revision: int | None,
    ) -> WorkflowRun:
        self._require_filler(actor)
        run = self._runs.get(run_id)
        if (
            run is None
            or run.workflow_id != workflow_id
            or run.case_id is not None
            or not _owns(actor, run)
        ):
            raise WorkflowNotFoundError
        if expected_revision is not None and run.revision != expected_revision:
            raise WorkflowConflictError
        return run

    def _apply_suggestions(
        self, run: WorkflowRun, document_id: UUID, pages: tuple[str, ...]
    ) -> None:
        answers = {(item.stage_id, item.field_id): item for item in run.answers}
        changed = False
        for stage, field in _autofill_fields(run):
            key = (stage.stage_id, field.field_id)
            existing = answers.get(key)
            if stage.stage_id in run.confirmed_stage_ids or (
                existing is not None and existing.source != WorkflowAnswerSource.DOCUMENT
            ):
                continue
            match = find_labelled_value(pages, field.document_label or field.label)
            if match is None:
                continue
            value = _suggested_value(field, match.value)
            if value is None or (existing is not None and existing.value == value):
                continue
            answers[key] = WorkflowAnswer(
                stage_id=stage.stage_id,
                field_id=field.field_id,
                value=value,
                source=WorkflowAnswerSource.DOCUMENT,
                document_id=document_id,
                page_number=match.page_number,
            )
            changed = True
        if changed:
            self._persist(run, answers=tuple(answers.values()))

    def _persist(self, run: WorkflowRun, **changes: object) -> WorkflowRun:
        candidate = run.model_copy(
            update={
                **changes,
                "revision": run.revision + 1,
                "stored_revision": None,
                "updated_at": self._clock(),
            }
        )
        try:
            # Only a never-saved run is inserted. Every other write is guarded by the
            # revision the run was read at, which refuses a stale writer.
            if run.stored_revision == _NEVER_SAVED:
                return self._runs.create(candidate)
            expected = run.revision if run.stored_revision is None else run.stored_revision
            return self._runs.update(candidate, expected_revision=expected)
        except PersistenceConflictError:
            raise WorkflowConflictError from None

    def _open_run(self, case_id: UUID, run_id: UUID, expected_revision: int) -> WorkflowRun:
        case = self._cases.get_case(case_id)
        if case is None:
            raise WorkflowNotFoundError
        stored = self._runs.list_for_case(case_id)
        candidates = [
            self._onboarding_run(case, stored),
            *(item for item in stored if not item.is_onboarding),
        ]
        run = next(
            (item for item in candidates if item is not None and item.run_id == run_id), None
        )
        if run is None:
            raise WorkflowNotFoundError
        if run.revision != expected_revision:
            raise WorkflowConflictError
        return run

    @staticmethod
    def _open_stage(run: WorkflowRun, stage_id: str) -> WorkflowStage:
        for index, stage in enumerate(run.stages):
            if stage.stage_id != stage_id:
                continue
            earlier = {item.stage_id for item in run.stages[:index]}
            if not run.is_onboarding and not earlier <= run.confirmed_stage_ids:
                raise WorkflowValidationError(
                    "WORKFLOW_STAGE_LOCKED", "Confirm the earlier stages first."
                )
            return stage
        raise WorkflowNotFoundError

    def _onboarding_run(
        self, case: OnboardingCase, stored: list[WorkflowRun]
    ) -> WorkflowRun | None:
        existing = next((run for run in stored if run.is_onboarding), None)
        definition = self._definitions.get(ONBOARDING_WORKFLOW_ID)
        sent = self._case_is_sent(case.case_id)
        if sent and existing is not None:
            return existing
        if definition is None:
            return existing
        # An open case follows the latest active version. A sent case stays as it was
        # sent: the version active when it was created.
        versions = (
            [item for item in definition.versions if item.activated_at <= case.created_at]
            if sent
            else list(definition.versions)
        )
        if not versions:
            return existing
        version = versions[-1]
        if not version.stages:
            return None
        if existing is not None:
            return _rebased(existing, version)
        return WorkflowRun(
            run_id=uuid5(NAMESPACE_OID, f"workflow-onboarding:{case.case_id}"),
            case_id=case.case_id,
            workflow_id=definition.workflow_id,
            workflow_name=definition.name,
            use_case=definition.use_case,
            workflow_version=version.version,
            stages=version.stages,
            # Unsaved too, each version shows its own revision, so a screen still showing
            # an older version must reload before it can answer or confirm.
            revision=version.version - 1,
            stored_revision=_NEVER_SAVED,
            created_at=case.created_at,
            updated_at=case.created_at,
        )

    def provision_onboarding(self) -> WorkflowDefinition:
        """Startup provisioning (ADR-017 3.5): idempotent, insert-only, never on a read.

        A new document carries ``active_version: 0`` (no active version) under the
        durable write rule; an existing document is returned unchanged.
        """

        with self._lock:
            current = self._definitions.get(ONBOARDING_WORKFLOW_ID)
            if current is not None:
                return current
            now = self._clock()
            definition = WorkflowDefinition(
                workflow_id=ONBOARDING_WORKFLOW_ID,
                name="Corporate onboarding",
                use_case=ONBOARDING_USE_CASE,
                country="Singapore",
                created_at=now,
                updated_at=now,
            )
            try:
                # Born governed in a fresh or migrated store; otherwise the P2-0 shape, which
                # the reviewed migration tool later migrates (Mongo never auto-migrates).
                store = self._governed_store()
                if store is None:
                    return self._definitions.create(definition)
                created = store.create_governed(
                    definition,
                    born_governed_state(ONBOARDING_WORKFLOW_ID, now=now, actor_id=None),
                )
                _drain_after_commit(store, ONBOARDING_WORKFLOW_ID, now)
                return created.definition
            except PersistenceConflictError:
                current = self._definitions.get(ONBOARDING_WORKFLOW_ID)
                if current is None:
                    raise WorkflowConflictError from None
                return current

    def _governed_store(self) -> WorkflowGovernanceRepository | None:
        """The governance port when every stored definition is migrated (or none exists)."""

        store = governance_store(self._definitions)
        if store is None:
            return None
        if all(item.governance.migrated for item in store.list_governed()):
            return store
        return None

    def _require_definition(self, workflow_id: str) -> WorkflowDefinition:
        definition = self._definitions.get(workflow_id)
        if definition is None:
            raise WorkflowNotFoundError
        return definition

    @staticmethod
    def _audit(
        actor: AuthenticatedActor, now: datetime, action: str, summary: str
    ) -> WorkflowAuditEvent:
        return WorkflowAuditEvent(
            occurred_at=now, actor_id=actor.profile.user_id, action=action, summary=summary
        )

    @staticmethod
    def _require_reader(actor: AuthenticatedActor) -> None:
        capabilities = ROLE_CAPABILITIES[actor.profile.role]
        if not capabilities & {Capability.POLICY_MUTATE, Capability.POLICY_APPROVE}:
            raise WorkflowForbiddenError

    @staticmethod
    def _require_author(actor: AuthenticatedActor) -> None:
        if Capability.POLICY_MUTATE not in ROLE_CAPABILITIES[actor.profile.role]:
            raise WorkflowForbiddenError

    @staticmethod
    def _require_filler(actor: AuthenticatedActor) -> None:
        if actor.profile.role not in _FIELD_FILLER_ROLES:
            raise WorkflowForbiddenError


def _drain_after_commit(
    store: WorkflowGovernanceRepository, workflow_id: str, now: datetime
) -> None:
    """Archive after a committed write. A failure leaves the outbox for the next drain."""

    try:
        store.drain_outbox(workflow_id, now=now)
    except PersistenceError:
        LOGGER.warning("workflow history archival deferred", extra={"workflow_id": workflow_id})


def _owns(actor: AuthenticatedActor, run: WorkflowRun) -> bool:
    return run.company is not None and run.company.team_id == str(actor.profile.team_id)


def _rebased(run: WorkflowRun, version: WorkflowVersion) -> WorkflowRun:
    """Move an open case to a new version, keeping answers to anything unchanged."""

    if run.workflow_version == version.version:
        return run
    previous = {stage.stage_id: stage for stage in run.stages}
    current = {stage.stage_id: stage for stage in version.stages}
    fields = {
        (stage.stage_id, field.field_id): field
        for stage in version.stages
        for field in stage.fields
    }
    return run.model_copy(
        update={
            "workflow_version": version.version,
            "stages": version.stages,
            # Each version shown gets its own revision, so any screen still showing an
            # older version must reload first, however many versions it has missed.
            "revision": run.revision + version.version - run.workflow_version,
            "stored_revision": run.revision,
            "answers": tuple(
                item
                for item in run.answers
                if (item.stage_id, item.field_id) in fields
                and _answer_still_valid(fields[(item.stage_id, item.field_id)], item.value)
            ),
            # A stage that changed needs checking again.
            "confirmations": tuple(
                item
                for item in run.confirmations
                if item.stage_id in current
                and previous.get(item.stage_id) == current[item.stage_id]
            ),
        }
    )


def _suggested_value(field: WorkflowField, value: str) -> str | None:
    """Fit a document value to its field, or leave the field for a person."""

    if field.kind == WorkflowFieldKind.DATE:
        return normalize_date(value)
    if field.kind == WorkflowFieldKind.NUMBER:
        return normalize_number(value)
    if field.kind == WorkflowFieldKind.YES_NO:
        return match_option(value, ("Yes", "No"))
    if field.kind == WorkflowFieldKind.CHOICE:
        return match_option(value, field.options)
    return value


def _answer_still_valid(field: WorkflowField, value: str) -> bool:
    try:
        return _validated_answer(field, value) is not None
    except WorkflowValidationError:
        return False


def _autofill_fields(run: WorkflowRun) -> list[tuple[WorkflowStage, WorkflowField]]:
    return [
        (stage, field) for stage in run.stages for field in stage.fields if field.autofill
    ]


def _document_pages(
    content: bytes, media_type: str, extracted_text: str | None
) -> tuple[str, ...]:
    if extracted_text is not None:
        return (extracted_text,)
    try:
        with isolated_document_pages(content, media_type) as pages:
            return tuple(page.text for page in pages)
    except LocalDocumentProcessingError:
        return ()


def _validated_answer(field: WorkflowField, raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    valid = len(value) <= MAX_ANSWER_LENGTH and value.isprintable()
    if valid and field.kind == WorkflowFieldKind.DATE:
        try:
            date.fromisoformat(value)
        except ValueError:
            valid = False
    elif valid and field.kind == WorkflowFieldKind.NUMBER:
        try:
            valid = Decimal(value).is_finite()
        except InvalidOperation:
            valid = False
    elif valid and field.kind == WorkflowFieldKind.YES_NO:
        valid = value in {"Yes", "No"}
    elif valid and field.kind == WorkflowFieldKind.CHOICE:
        valid = value in field.options
    if not valid:
        raise WorkflowValidationError(
            "WORKFLOW_ANSWER_INVALID", f"The value for {field.label} is not valid."
        )
    return value
