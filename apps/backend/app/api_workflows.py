"""Authenticated workflow HTTP contract (D-123). Disabled unless explicitly enabled."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.api_auth import SESSION_COOKIE_NAME
from app.api_workflow_governance_models import (
    AcknowledgeNoticeRequest,
    ApprovalInboxResponse,
    ComparisonResponse,
    CopyProposalRequest,
    CreateProposalRequest,
    DecisionRequest,
    DecisionResponse,
    EmergencyFallbackRequest,
    EmergencyFallbackResponse,
    NoticeItem,
    NoticeListResponse,
    ProposalResponse,
    ReleaseDraftRequest,
    SimulateProposalRequest,
    SimulationResult,
    SimulationScenario,
    SubmitProposalRequest,
    UpdateProposalRequest,
    ValidateProposalRequest,
    ValidationReport,
    WithdrawProposalRequest,
    WorkflowGovernanceView,
    WorkflowVersionResponse,
)
from app.domain.access import AuthenticatedActor
from app.domain.models import OnboardingCase
from app.domain.workflow_governance import GovernanceErrorCode
from app.domain.workflows import (
    ONBOARDING_LOCKED_STAGES,
    WorkflowAnswerSource,
    WorkflowAuditEvent,
    WorkflowCaseSource,
    WorkflowDefinition,
    WorkflowFieldKind,
    WorkflowLabel,
    WorkflowRun,
    WorkflowStage,
    WorkflowTag,
    WorkflowVersion,
)
from app.persistence.errors import (
    PersistenceDataInvalidError,
    PersistenceOutcomeAmbiguousError,
    PersistenceUnavailableError,
)
from app.persistence.workflow_governance_store import (
    WorkflowGovernanceNotMigratedError,
    WorkflowHistoryUnavailableError,
)
from app.services.authentication import AuthenticationError, AuthenticationService
from app.services.authorization import CaseAccessPolicy, CaseNotAvailableError
from app.services.document_errors import DocumentRequestError
from app.services.document_media import DocumentMediaRouter
from app.services.onboarding import OnboardingService
from app.services.workflow_governance import WorkflowGovernanceError, WorkflowGovernanceService
from app.services.workflow_management import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowManagementService,
    WorkflowNotFoundError,
    WorkflowRouteRetiredError,
    WorkflowValidationError,
    stage_blocks_send,
    stored_active_version,
)


class LockedStageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    label: str


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: str
    name: str
    use_case: str
    country: str
    case_source: WorkflowCaseSource
    revision: int
    is_onboarding: bool
    status: Literal["ACTIVE", "DRAFT"]
    active_version: int | None
    draft_stages: tuple[WorkflowStage, ...]
    versions: tuple[WorkflowVersion, ...]
    audit: tuple[WorkflowAuditEvent, ...]
    locked_stages: tuple[LockedStageResponse, ...]
    updated_at: datetime
    # P2-1: null until the definition carries its migration marker (contract section 3.1).
    governance: WorkflowGovernanceView | None = None

    @classmethod
    def from_domain(
        cls, item: WorkflowDefinition, governance: WorkflowGovernanceView | None = None
    ) -> WorkflowResponse:
        # The stored active version: a deactivated workflow (0) shows as a draft.
        active = stored_active_version(item)
        return cls(
            workflow_id=item.workflow_id,
            name=item.name,
            use_case=item.use_case,
            country=item.country,
            case_source=item.case_source,
            revision=item.revision,
            is_onboarding=item.is_onboarding,
            status="ACTIVE" if active is not None or item.is_onboarding else "DRAFT",
            active_version=active.version if active is not None else None,
            draft_stages=item.draft_stages,
            versions=item.versions,
            audit=item.audit,
            locked_stages=tuple(
                LockedStageResponse(node_id=node_id, label=label)
                for node_id, label in (ONBOARDING_LOCKED_STAGES if item.is_onboarding else ())
            ),
            updated_at=item.updated_at,
            governance=governance,
        )


class RunFieldResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: str
    label: str
    kind: WorkflowFieldKind
    required: bool
    options: tuple[str, ...]
    value: str | None
    source: WorkflowAnswerSource | None
    page_number: int | None


class RunStageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_id: str
    name: str
    after_node_id: str | None
    status: Literal["COMPLETE", "OPEN", "LOCKED"]
    blocks_send: bool
    confirmed_by: str | None
    confirmed_at: datetime | None
    fields: tuple[RunFieldResponse, ...]


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    case_id: UUID | None
    workflow_id: str
    workflow_name: str
    use_case: str
    workflow_version: int
    revision: int
    is_onboarding: bool
    is_complete: bool
    started_by: str | None
    stages: tuple[RunStageResponse, ...]

    @classmethod
    def from_domain(cls, run: WorkflowRun) -> RunResponse:
        answers = {(item.stage_id, item.field_id): item for item in run.answers}
        confirmations = {item.stage_id: item for item in run.confirmations}
        stages: list[RunStageResponse] = []
        reachable = True
        for stage in run.stages:
            confirmation = confirmations.get(stage.stage_id)
            stage_status: Literal["COMPLETE", "OPEN", "LOCKED"] = (
                "COMPLETE" if confirmation else "OPEN" if reachable else "LOCKED"
            )
            if confirmation is None and not run.is_onboarding:
                reachable = False
            fields: list[RunFieldResponse] = []
            for field in stage.fields:
                answer = answers.get((stage.stage_id, field.field_id))
                fields.append(
                    RunFieldResponse(
                        field_id=field.field_id,
                        label=field.label,
                        kind=field.kind,
                        required=field.required,
                        options=field.options,
                        value=answer.value if answer else None,
                        source=answer.source if answer else None,
                        page_number=answer.page_number if answer else None,
                    )
                )
            stages.append(
                RunStageResponse(
                    stage_id=stage.stage_id,
                    name=stage.name,
                    after_node_id=stage.after_node_id,
                    status=stage_status,
                    blocks_send=stage_blocks_send(stage),
                    confirmed_by=confirmation.confirmed_by if confirmation else None,
                    confirmed_at=confirmation.confirmed_at if confirmation else None,
                    fields=tuple(fields),
                )
            )
        return cls(
            run_id=run.run_id,
            case_id=run.case_id,
            workflow_id=run.workflow_id,
            workflow_name=run.workflow_name,
            use_case=run.use_case,
            workflow_version=run.workflow_version,
            revision=run.revision,
            is_onboarding=run.is_onboarding,
            is_complete=run.is_complete,
            started_by=run.started_by,
            stages=tuple(stages),
        )


class StartableWorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: str
    name: str
    case_source: WorkflowCaseSource


class WorkflowRunListItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: UUID | None
    company: str
    registration_id: str
    run: RunResponse


class CaseWorkflowsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    onboarding: RunResponse | None
    runs: tuple[RunResponse, ...]


class CreateWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: WorkflowLabel
    use_case: WorkflowTag
    country: WorkflowTag
    case_source: WorkflowCaseSource = WorkflowCaseSource.EXISTING_CASE


class CreateWorkflowCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: str = Field(min_length=1, max_length=160)
    registration_id: str = Field(min_length=1, max_length=32)
    jurisdiction: str | None = Field(default=None, min_length=2, max_length=3)
    priority: int | None = Field(default=None, ge=1, le=10)


class StartRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: UUID


class SaveAnswersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    values: dict[str, str] = Field(max_length=32)


class ConfirmStageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)


def build_workflow_router(
    service: WorkflowManagementService | None,
    authentication: AuthenticationService,
    access_policy: CaseAccessPolicy,
    cases: OnboardingService,
    max_upload_bytes: int,
    read_bounded_body: Callable[[Request, int], Awaitable[bytes]],
    governance: WorkflowGovernanceService | None = None,
) -> APIRouter:
    def require_enabled() -> None:
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "WORKFLOW_MANAGER_DISABLED",
                    "message": "Workflow management is switched off on this server.",
                },
            )

    router = APIRouter(tags=["workflows"], dependencies=[Depends(require_enabled)])

    def active() -> WorkflowManagementService:
        assert service is not None  # require_enabled runs first.
        return service

    def fresh_actor(request: Request) -> Callable[[], AuthenticatedActor]:
        token = request.cookies.get(SESSION_COOKIE_NAME)

        def reauthorize() -> AuthenticatedActor:
            try:
                return authentication.authenticate_session(token).actor
            except AuthenticationError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "A valid authenticated session is required.",
                    },
                ) from None

        return reauthorize

    def governed() -> WorkflowGovernanceService:
        if governance is None:
            raise WorkflowGovernanceError(GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED)
        return governance

    def fresh_case_actor(request: Request, case_id: UUID) -> Callable[[], AuthenticatedActor]:
        session_actor = fresh_actor(request)

        def reauthorize() -> AuthenticatedActor:
            actor = session_actor()
            access_policy.require_case_access(actor, case_id, cases)
            return actor

        return reauthorize

    @router.get("/api/workflows", response_model=tuple[WorkflowResponse, ...])
    def list_workflows(request: Request) -> tuple[WorkflowResponse, ...]:
        def build() -> tuple[WorkflowResponse, ...]:
            actor = _actor(request)
            if governance is None:
                return tuple(
                    WorkflowResponse.from_domain(item) for item in active().list_workflows(actor)
                )
            return tuple(
                WorkflowResponse.from_domain(item, view)
                for item, view in governance.list_workflows(actor)
            )

        return _call(build)

    @router.get("/api/workflows/startable", response_model=tuple[StartableWorkflowResponse, ...])
    def startable_workflows(request: Request) -> tuple[StartableWorkflowResponse, ...]:
        return _call(
            lambda: tuple(
                StartableWorkflowResponse(
                    workflow_id=item.workflow_id, name=item.name, case_source=item.case_source
                )
                for item in active().startable_workflows(_actor(request))
            )
        )

    @router.post(
        "/api/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED
    )
    def create_workflow(body: CreateWorkflowRequest, request: Request) -> WorkflowResponse:
        return _call(
            lambda: WorkflowResponse.from_domain(
                active().create_workflow(
                    fresh_actor(request),
                    name=body.name,
                    use_case=body.use_case,
                    country=body.country,
                    case_source=body.case_source,
                )
            )
        )

    # Registered before ``/api/workflows/{workflow_id}`` so it is never shadowed.
    @router.get(
        "/api/workflows/simulation-scenarios", response_model=tuple[SimulationScenario, ...]
    )
    def simulation_scenarios(request: Request) -> tuple[SimulationScenario, ...]:
        return _call(lambda: governed().simulation_scenarios(_actor(request)))

    @router.get("/api/workflow-approvals", response_model=ApprovalInboxResponse)
    def approvals_inbox(request: Request) -> ApprovalInboxResponse:
        return _call(lambda: governed().approvals_inbox(_actor(request)))

    # M2 (CC-4) notices: static paths, registered before ``/api/workflows/{workflow_id}``.
    @router.get("/api/workflows/notices", response_model=NoticeListResponse)
    def governance_notices(request: Request) -> NoticeListResponse:
        return _call(lambda: governed().notices(_actor(request)))

    @router.post(
        "/api/workflows/notices/{notice_id}/acknowledge", response_model=NoticeItem
    )
    def acknowledge_notice(
        notice_id: str, body: AcknowledgeNoticeRequest, request: Request
    ) -> NoticeItem:
        return _call(
            lambda: governed().acknowledge_notice(fresh_actor(request), notice_id, body)
        )

    @router.get("/api/workflows/{workflow_id}", response_model=WorkflowResponse)
    def get_workflow(workflow_id: str, request: Request) -> WorkflowResponse:
        def build() -> WorkflowResponse:
            actor = _actor(request)
            if governance is None:
                return WorkflowResponse.from_domain(active().get_workflow(actor, workflow_id))
            return WorkflowResponse.from_domain(*governance.get_workflow(actor, workflow_id))

        return _call(build)

    # Retired legacy routes (contract section 3): still mounted, only to answer 410.
    @router.put("/api/workflows/{workflow_id}/draft", response_model=WorkflowResponse)
    def save_draft(workflow_id: str, request: Request) -> WorkflowResponse:
        return _call(
            lambda: WorkflowResponse.from_domain(
                active().save_draft(
                    fresh_actor(request), workflow_id, expected_revision=1, stages=()
                )
            )
        )

    @router.post("/api/workflows/{workflow_id}/activate", response_model=WorkflowResponse)
    def activate(workflow_id: str, request: Request) -> WorkflowResponse:
        return _call(
            lambda: WorkflowResponse.from_domain(
                active().activate(fresh_actor(request), workflow_id, expected_revision=1)
            )
        )

    # Governance (ADR-017 section 6, contract section 3): HR authors, a Director decides.
    @router.post(
        "/api/workflows/{workflow_id}/proposals",
        response_model=ProposalResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_proposal(
        workflow_id: str, body: CreateProposalRequest, request: Request
    ) -> ProposalResponse:
        return _call(lambda: governed().create_proposal(fresh_actor(request), workflow_id, body))

    @router.put(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}", response_model=ProposalResponse
    )
    def update_proposal(
        workflow_id: str, proposal_id: str, body: UpdateProposalRequest, request: Request
    ) -> ProposalResponse:
        return _call(
            lambda: governed().update_proposal(fresh_actor(request), workflow_id, proposal_id, body)
        )

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/validate",
        response_model=ValidationReport,
    )
    def validate_proposal(
        workflow_id: str, proposal_id: str, body: ValidateProposalRequest, request: Request
    ) -> ValidationReport:
        return _call(lambda: governed().validate(_actor(request), workflow_id, proposal_id, body))

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/simulate",
        response_model=SimulationResult,
    )
    def simulate_proposal(
        workflow_id: str, proposal_id: str, body: SimulateProposalRequest, request: Request
    ) -> SimulationResult:
        return _call(lambda: governed().simulate(_actor(request), workflow_id, proposal_id, body))

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/submit",
        response_model=ProposalResponse,
    )
    def submit_proposal(
        workflow_id: str, proposal_id: str, body: SubmitProposalRequest, request: Request
    ) -> ProposalResponse:
        return _call(
            lambda: governed().submit_proposal(fresh_actor(request), workflow_id, proposal_id, body)
        )

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/withdraw",
        response_model=ProposalResponse,
    )
    def withdraw_proposal(
        workflow_id: str, proposal_id: str, body: WithdrawProposalRequest, request: Request
    ) -> ProposalResponse:
        return _call(
            lambda: governed().withdraw_proposal(
                fresh_actor(request), workflow_id, proposal_id, body
            )
        )

    @router.get(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/comparison",
        response_model=ComparisonResponse,
    )
    def proposal_comparison(
        workflow_id: str, proposal_id: str, request: Request
    ) -> ComparisonResponse:
        return _call(lambda: governed().comparison(_actor(request), workflow_id, proposal_id))

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/decision",
        response_model=DecisionResponse,
    )
    def decide_proposal(
        workflow_id: str, proposal_id: str, body: DecisionRequest, request: Request
    ) -> DecisionResponse:
        return _call(
            lambda: governed().decide(fresh_actor(request), workflow_id, proposal_id, body)
        )

    # M2 (CC-4): recovery and administration.
    @router.post(
        "/api/workflows/{workflow_id}/emergency-fallback",
        response_model=EmergencyFallbackResponse,
    )
    def emergency_fallback(
        workflow_id: str, body: EmergencyFallbackRequest, request: Request
    ) -> EmergencyFallbackResponse:
        return _call(
            lambda: governed().emergency_fallback(fresh_actor(request), workflow_id, body)
        )

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/release",
        response_model=ProposalResponse,
    )
    def release_proposal(
        workflow_id: str, proposal_id: str, body: ReleaseDraftRequest, request: Request
    ) -> ProposalResponse:
        return _call(
            lambda: governed().release_proposal(
                fresh_actor(request), workflow_id, proposal_id, body
            )
        )

    @router.post(
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/copy",
        response_model=ProposalResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def copy_proposal(
        workflow_id: str, proposal_id: str, body: CopyProposalRequest, request: Request
    ) -> ProposalResponse:
        return _call(
            lambda: governed().copy_proposal(fresh_actor(request), workflow_id, proposal_id, body)
        )

    @router.get(
        "/api/workflows/{workflow_id}/versions/{version}",
        response_model=WorkflowVersionResponse,
    )
    def workflow_version(
        workflow_id: str, version: int, request: Request
    ) -> WorkflowVersionResponse:
        return _call(lambda: governed().get_version(_actor(request), workflow_id, version))

    @router.post(
        "/api/workflows/{workflow_id}/runs",
        response_model=RunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def start_run(workflow_id: str, body: StartRunRequest, request: Request) -> RunResponse:
        return _call(
            lambda: RunResponse.from_domain(
                active().start_run(
                    fresh_case_actor(request, body.case_id), workflow_id, case_id=body.case_id
                )
            )
        )

    @router.get(
        "/api/workflows/{workflow_id}/runs", response_model=tuple[WorkflowRunListItem, ...]
    )
    def workflow_runs(workflow_id: str, request: Request) -> tuple[WorkflowRunListItem, ...]:
        def build() -> tuple[WorkflowRunListItem, ...]:
            actor = _actor(request)
            return tuple(
                _run_item(run, case)
                for run, case in active().runs_for_workflow(actor, workflow_id)
                if case is None or access_policy.can_access(actor, case)
            )

        return _call(build)

    @router.post(
        "/api/workflows/{workflow_id}/new-cases",
        response_model=WorkflowRunListItem,
        status_code=status.HTTP_201_CREATED,
    )
    def create_workflow_case(
        workflow_id: str, body: CreateWorkflowCaseRequest, request: Request
    ) -> WorkflowRunListItem:
        return _call(
            lambda: _run_item(
                active().create_workflow_case(
                    fresh_actor(request),
                    workflow_id,
                    legal_name=body.legal_name,
                    registration_id=body.registration_id,
                    jurisdiction=body.jurisdiction,
                    priority=body.priority,
                ),
                None,
            )
        )

    @router.put(
        "/api/workflows/{workflow_id}/runs/{run_id}/stages/{stage_id}/answers",
        response_model=RunResponse,
    )
    def save_workflow_case_answers(
        workflow_id: str, run_id: UUID, stage_id: str, body: SaveAnswersRequest, request: Request
    ) -> RunResponse:
        return _call(
            lambda: RunResponse.from_domain(
                active().save_workflow_case_answers(
                    fresh_actor(request),
                    workflow_id=workflow_id,
                    run_id=run_id,
                    stage_id=stage_id,
                    expected_revision=body.expected_revision,
                    values=body.values,
                )
            )
        )

    @router.post(
        "/api/workflows/{workflow_id}/runs/{run_id}/stages/{stage_id}/confirm",
        response_model=RunResponse,
    )
    def confirm_workflow_case_stage(
        workflow_id: str, run_id: UUID, stage_id: str, body: ConfirmStageRequest, request: Request
    ) -> RunResponse:
        return _call(
            lambda: RunResponse.from_domain(
                active().confirm_workflow_case_stage(
                    fresh_actor(request),
                    workflow_id=workflow_id,
                    run_id=run_id,
                    stage_id=stage_id,
                    expected_revision=body.expected_revision,
                )
            )
        )

    @router.post("/api/workflows/{workflow_id}/runs/{run_id}/documents", response_model=RunResponse)
    async def suggest_from_upload(
        workflow_id: str, run_id: UUID, request: Request
    ) -> RunResponse:
        # Who may upload is settled before any of the body is read.
        _call(lambda: active().require_workflow_case(fresh_actor(request)(), workflow_id, run_id))
        content = await read_bounded_body(request, max_upload_bytes)
        try:
            extracted = DocumentMediaRouter().extract(
                display_name=request.headers.get("X-Document-Name", ""),
                content_type=request.headers.get("Content-Type", ""),
                content=content,
            )
        except DocumentRequestError as error:
            raise _error(422, error.code, "The document could not be read.") from None
        return _call(
            lambda: RunResponse.from_domain(
                active().suggest_for_workflow_case(
                    fresh_actor(request),
                    workflow_id=workflow_id,
                    run_id=run_id,
                    content=extracted.content,
                    media_type=extracted.media_type,
                    extracted_text=extracted.extracted_text,
                )
            )
        )

    @router.delete(
        "/api/workflows/{workflow_id}/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT
    )
    def delete_workflow_case(workflow_id: str, run_id: UUID, request: Request) -> None:
        _call(
            lambda: active().delete_workflow_case(
                fresh_actor(request), workflow_id=workflow_id, run_id=run_id
            )
        )

    @router.get(
        "/api/clm/zero-touch/cases/{case_id}/workflows", response_model=CaseWorkflowsResponse
    )
    def case_workflows(case_id: UUID, request: Request) -> CaseWorkflowsResponse:
        def build() -> CaseWorkflowsResponse:
            case = access_policy.require_case_access(_actor(request), case_id, cases)
            view = active().case_view(case)
            return CaseWorkflowsResponse(
                onboarding=(
                    RunResponse.from_domain(view.onboarding) if view.onboarding else None
                ),
                runs=tuple(RunResponse.from_domain(run) for run in view.runs),
            )

        return _call(build)

    @router.put(
        "/api/clm/zero-touch/cases/{case_id}/workflows/runs/{run_id}/stages/{stage_id}/answers",
        response_model=RunResponse,
    )
    def save_answers(
        case_id: UUID, run_id: UUID, stage_id: str, body: SaveAnswersRequest, request: Request
    ) -> RunResponse:
        return _call(
            lambda: RunResponse.from_domain(
                active().save_answers(
                    fresh_case_actor(request, case_id),
                    case_id=case_id,
                    run_id=run_id,
                    stage_id=stage_id,
                    expected_revision=body.expected_revision,
                    values=body.values,
                )
            )
        )

    @router.post(
        "/api/clm/zero-touch/cases/{case_id}/workflows/runs/{run_id}/stages/{stage_id}/confirm",
        response_model=RunResponse,
    )
    def confirm_stage(
        case_id: UUID, run_id: UUID, stage_id: str, body: ConfirmStageRequest, request: Request
    ) -> RunResponse:
        return _call(
            lambda: RunResponse.from_domain(
                active().confirm_stage(
                    fresh_case_actor(request, case_id),
                    case_id=case_id,
                    run_id=run_id,
                    stage_id=stage_id,
                    expected_revision=body.expected_revision,
                )
            )
        )

    return router


def _run_item(run: WorkflowRun, case: OnboardingCase | None) -> WorkflowRunListItem:
    company = run.company
    if company is not None:
        name, registration_id = company.legal_name, company.registration_id
    else:
        assert case is not None  # Every run has a company or a case.
        name, registration_id = _company_name(case), case.requested_uen
    return WorkflowRunListItem(
        case_id=run.case_id,
        company=name,
        registration_id=registration_id,
        run=RunResponse.from_domain(run),
    )


def _company_name(case: OnboardingCase) -> str:
    """Registry name when known, else the name entered at intake, else the identifier."""

    registry_name = case.entity.legal_name if case.entity else None
    entered_name = case.initial_identity.legal_name if case.initial_identity else None
    return registry_name or entered_name or case.requested_uen


def _actor(request: Request) -> AuthenticatedActor:
    actor = getattr(request.state, "actor", None)
    if not isinstance(actor, AuthenticatedActor):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return actor


def _call[ResponseT](call: Callable[[], ResponseT]) -> ResponseT:
    try:
        return call()
    except WorkflowForbiddenError:
        raise _error(
            status.HTTP_403_FORBIDDEN, "WORKFLOW_FORBIDDEN", "This action is not permitted."
        ) from None
    except (WorkflowNotFoundError, CaseNotAvailableError):
        raise _error(
            status.HTTP_404_NOT_FOUND, "WORKFLOW_NOT_FOUND", "The item was not found."
        ) from None
    except WorkflowConflictError:
        raise _error(
            status.HTTP_409_CONFLICT,
            "WORKFLOW_CONFLICT",
            "This changed elsewhere. Reload and try again.",
        ) from None
    except WorkflowGovernanceError as error:
        raise HTTPException(
            status_code=error.status, detail=error.body().model_dump(mode="json")
        ) from None
    except WorkflowRouteRetiredError:
        raise _governance_error(GovernanceErrorCode.ROUTE_RETIRED) from None
    except WorkflowGovernanceNotMigratedError:
        raise _governance_error(GovernanceErrorCode.GOVERNANCE_NOT_MIGRATED) from None
    except WorkflowHistoryUnavailableError:
        raise _governance_error(GovernanceErrorCode.HISTORY_UNAVAILABLE) from None
    except WorkflowValidationError as error:
        raise _error(422, error.code, error.public_message) from None
    except (
        PersistenceUnavailableError,
        PersistenceOutcomeAmbiguousError,
        PersistenceDataInvalidError,
    ):
        # An ambiguous outcome is never retried automatically: reload, then decide.
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "WORKFLOW_UNAVAILABLE",
            "Workflows are unavailable right now.",
        ) from None


def _error(code: int, error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"code": error_code, "message": message})


def _governance_error(code: GovernanceErrorCode) -> HTTPException:
    error = WorkflowGovernanceError(code)
    return HTTPException(status_code=error.status, detail=error.body().model_dump(mode="json"))
