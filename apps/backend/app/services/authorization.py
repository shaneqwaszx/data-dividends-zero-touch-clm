"""Single server-side Phase 13 case access and route-classification policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.access import AuthenticatedActor, Role, TeamId
from app.domain.models import OnboardingCase
from app.services.onboarding import OnboardingService


class RouteAccess(StrEnum):
    PUBLIC = "PUBLIC"
    ACTOR_ONLY = "ACTOR_ONLY"
    CASE_SCOPED = "CASE_SCOPED"
    CASE_CREATION = "CASE_CREATION"


@dataclass(frozen=True)
class RoutePolicy:
    method: str
    path: str
    access: RouteAccess


ROUTE_POLICIES: tuple[RoutePolicy, ...] = (
    RoutePolicy("GET", "/health", RouteAccess.PUBLIC),
    RoutePolicy("POST", "/api/auth/login", RouteAccess.PUBLIC),
    RoutePolicy("GET", "/api/auth/me", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/auth/logout", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/system/execution-profile", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/onboarding/mock-scenarios", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/clm/zero-touch/cases", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/onboarding/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("POST", "/api/clm/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("POST", "/api/clm/zero-touch/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("POST", "/api/demo/clm/zero-touch/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("GET", "/api/onboarding/cases/{case_id}", RouteAccess.CASE_SCOPED),
    RoutePolicy("GET", "/api/clm/cases/{case_id}", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "POST",
        "/api/clm/cases/{case_id}/readiness/evaluate",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "GET", "/api/clm/cases/{case_id}/submission-plan", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy("POST", "/api/clm/cases/{case_id}/submit", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/intake/documents",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/documents",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/documents/"
        "{failed_document_id}/retry",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/intake/complete",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/complete",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("GET", "/api/clm/zero-touch/cases/{case_id}", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "GET",
        "/api/demo/clm/zero-touch/cases/{case_id}/uat-evidence",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/documents",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/documents/{document_id}/replacement",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/demo/clm/zero-touch/cases/{case_id}/documents",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST", "/api/clm/zero-touch/cases/{case_id}/start", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "POST", "/api/clm/zero-touch/cases/{case_id}/resume", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/reconciliation/discrepancies/"
        "{discrepancy_id}/resolve",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "PATCH",
        "/api/clm/zero-touch/cases/{case_id}/priority",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST", "/api/onboarding/cases/{case_id}/ownership/load", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "POST",
        "/api/demo/onboarding/cases/{case_id}/ownership/load",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/onboarding/cases/{case_id}/ownership/analyze",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "GET", "/api/onboarding/cases/{case_id}/ownership", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "GET", "/api/onboarding/cases/{case_id}/ubo-candidates", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "POST", "/api/onboarding/cases/{case_id}/documents", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "POST",
        "/api/demo/onboarding/cases/{case_id}/documents",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "GET", "/api/onboarding/cases/{case_id}/documents", RouteAccess.CASE_SCOPED
    ),
    RoutePolicy(
        "GET",
        "/api/onboarding/cases/{case_id}/documents/{document_id}",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/onboarding/cases/{case_id}/documents/{document_id}/reviews",
        RouteAccess.CASE_SCOPED,
    ),
)


class CaseNotAvailableError(Exception):
    pass


class CreationTeamSelectionError(Exception):
    pass


class CaseAccessPolicy:
    """Authorize only from typed canonical case ownership and server actor data."""

    def can_access(self, actor: AuthenticatedActor, case: OnboardingCase) -> bool:
        profile = actor.profile
        if profile.role == Role.DIRECTOR:
            return profile.team_id is None
        return profile.team_id is not None and profile.team_id == case.team_id

    def require_case_access(
        self,
        actor: AuthenticatedActor,
        case_id: UUID,
        cases: OnboardingService,
    ) -> OnboardingCase:
        case = cases.get_case(case_id)
        if case is None or not self.can_access(actor, case):
            raise CaseNotAvailableError
        return case

    def resolve_creation_team(
        self,
        actor: AuthenticatedActor,
        requested_team: TeamId | None,
        *,
        field_was_supplied: bool,
    ) -> TeamId:
        profile = actor.profile
        if profile.role == Role.DIRECTOR:
            if not field_was_supplied or requested_team is None:
                raise CreationTeamSelectionError
            return requested_team
        if field_was_supplied or profile.team_id is None:
            raise CreationTeamSelectionError
        return profile.team_id


def classify_route(method: str, path: str) -> tuple[RoutePolicy | None, dict[str, str]]:
    for policy in ROUTE_POLICIES:
        if policy.method != method.upper():
            continue
        match = _route_pattern(policy.path).fullmatch(path)
        if match is not None:
            return policy, match.groupdict()
    return None, {}


def route_inventory() -> set[tuple[str, str]]:
    return {(policy.method, policy.path) for policy in ROUTE_POLICIES}


def _route_pattern(path: str) -> re.Pattern[str]:
    pieces: list[str] = []
    position = 0
    for match in re.finditer(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", path):
        pieces.append(re.escape(path[position : match.start()]))
        pieces.append(fr"(?P<{match.group(1)}>[^/]+)")
        position = match.end()
    pieces.append(re.escape(path[position:]))
    return re.compile("".join(pieces))
