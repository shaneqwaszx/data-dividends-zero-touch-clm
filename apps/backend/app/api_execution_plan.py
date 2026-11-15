"""Read-only onboarding execution plan for the HR Admin workflow designer (P1).

GET only. It is mounted outside the workflow-manager router, so it still describes
stored, enforced stages when ``WORKFLOW_MANAGER_ENABLED`` is false. It returns no case
data. HR (``POLICY_MUTATE``) and Directors (``POLICY_APPROVE``) may read it; the
session is reauthorized on every request.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.api_auth import SESSION_COOKIE_NAME
from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.services.authentication import AuthenticationError, AuthenticationService
from app.services.onboarding_execution_plan import ExecutionPlan, ExecutionPlanService

_READERS = frozenset({Capability.POLICY_MUTATE, Capability.POLICY_APPROVE})


def build_execution_plan_router(
    service: ExecutionPlanService, authentication: AuthenticationService
) -> APIRouter:
    router = APIRouter(tags=["workflows"])

    @router.get("/api/workflows/onboarding/execution-plan", response_model=ExecutionPlan)
    def get_execution_plan(request: Request) -> ExecutionPlan:
        actor = _reauthorized(request, authentication)
        if not _READERS & ROLE_CAPABILITIES[actor.profile.role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "EXECUTION_PLAN_FORBIDDEN",
                    "message": "Only HR administrators and Directors can view the execution plan.",
                },
            )
        return service.plan()

    return router


def _reauthorized(request: Request, authentication: AuthenticationService) -> AuthenticatedActor:
    try:
        return authentication.authenticate_session(request.cookies.get(SESSION_COOKIE_NAME)).actor
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "A valid authenticated session is required.",
            },
        ) from None
