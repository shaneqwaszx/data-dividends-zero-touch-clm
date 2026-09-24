"""Authenticated case-scoped onboarding intelligence projection."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from app.domain.access import AuthenticatedActor
from app.domain.onboarding_intelligence import OnboardingIntelligenceRecord
from app.services.authorization import CaseAccessPolicy, CaseNotAvailableError
from app.services.onboarding import OnboardingService
from app.services.onboarding_intelligence import OnboardingIntelligenceProjectionService


def build_intelligence_router(
    projection: OnboardingIntelligenceProjectionService,
    *,
    cases: OnboardingService,
    access_policy: CaseAccessPolicy,
) -> APIRouter:
    router = APIRouter(prefix="/api/clm/zero-touch/cases", tags=["intelligence"])

    @router.get("/{case_id}/intelligence", response_model=OnboardingIntelligenceRecord)
    def get_intelligence(case_id: UUID, request: Request) -> OnboardingIntelligenceRecord:
        actor = getattr(request.state, "actor", None)
        if not isinstance(actor, AuthenticatedActor):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            access_policy.require_case_access(actor, case_id, cases)
        except CaseNotAvailableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CASE_NOT_FOUND", "message": "The case was not found."},
            ) from None
        record = projection.get(case_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "INTELLIGENCE_NOT_AVAILABLE",
                    "message": "No intelligence projection is available for this case.",
                },
            )
        return record

    return router
