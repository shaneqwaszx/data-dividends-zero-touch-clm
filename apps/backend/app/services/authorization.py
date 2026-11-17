"""Single server-side Phase 13 case access and route-classification policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability, Role, TeamId
from app.domain.case_management import (
    CasePortfolioScope,
    PortfolioScopeKind,
)
from app.domain.models import OnboardingCase
from app.services.onboarding import OnboardingService


class RouteAccess(StrEnum):
    PUBLIC = "PUBLIC"
    ACTOR_ONLY = "ACTOR_ONLY"
    CASE_SCOPED = "CASE_SCOPED"
    # Read-only case GET that a KNOWLEDGE_CASE_READ actor may also load (D-103).
    CASE_READ = "CASE_READ"
    CASE_CREATION = "CASE_CREATION"
    CASE_PORTFOLIO = "CASE_PORTFOLIO"


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
    RoutePolicy("POST", "/api/admin/me/password", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/teams/options", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/admin/teams", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/teams", RouteAccess.ACTOR_ONLY),
    RoutePolicy("PATCH", "/api/admin/teams/{team_id}", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/admin/profiles", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/profiles", RouteAccess.ACTOR_ONLY),
    RoutePolicy("PATCH", "/api/admin/profiles/{user_id}", RouteAccess.ACTOR_ONLY),
    # D-140: HR password reset and SF-006 disable; IDENTITY_ADMIN is rechecked in the store lock.
    RoutePolicy("POST", "/api/admin/profiles/{user_id}/password", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/profiles/{user_id}/disable", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/policies", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/policies/classifier-benchmark", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/policies/proposals/{proposal_id}/impact", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/policies/proposals", RouteAccess.ACTOR_ONLY),
    RoutePolicy("PATCH", "/api/policies/proposals/{proposal_id}", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/policies/proposals/{proposal_id}/submit", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/policies/proposals/{proposal_id}/decision", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/policies/{policy_id}", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/policies", RouteAccess.ACTOR_ONLY),
    RoutePolicy("PATCH", "/api/policies/{policy_id}", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/policies/{policy_id}/reset", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/policies/reset", RouteAccess.ACTOR_ONLY),
    # D-123: the owning service applies the Director or RM/onboarder rule on these.
    RoutePolicy("GET", "/api/workflows", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/workflows/startable", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/workflows", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/workflows/{workflow_id}", RouteAccess.ACTOR_ONLY),
    # P1: read-only execution plan; HR or Director capability is checked in the handler.
    RoutePolicy("GET", "/api/workflows/onboarding/execution-plan", RouteAccess.ACTOR_ONLY),
    RoutePolicy("PUT", "/api/workflows/{workflow_id}/draft", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/workflows/{workflow_id}/activate", RouteAccess.ACTOR_ONLY),
    # P2-1 (ADR-017 section 6): the governance service checks HR or Director inside the lock.
    RoutePolicy("GET", "/api/workflows/simulation-scenarios", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/workflow-approvals", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/workflows/{workflow_id}/proposals", RouteAccess.ACTOR_ONLY),
    RoutePolicy(
        "PUT", "/api/workflows/{workflow_id}/proposals/{proposal_id}", RouteAccess.ACTOR_ONLY
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/validate",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/simulate",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/submit",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/withdraw",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/decision",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "GET",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/comparison",
        RouteAccess.ACTOR_ONLY,
    ),
    # M2 (contract CC-4): recovery and administration; checked inside the lock.
    RoutePolicy(
        "POST", "/api/workflows/{workflow_id}/emergency-fallback", RouteAccess.ACTOR_ONLY
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/release",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/proposals/{proposal_id}/copy",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "GET", "/api/workflows/{workflow_id}/versions/{version}", RouteAccess.ACTOR_ONLY
    ),
    RoutePolicy("GET", "/api/workflows/notices", RouteAccess.ACTOR_ONLY),
    RoutePolicy(
        "POST", "/api/workflows/notices/{notice_id}/acknowledge", RouteAccess.ACTOR_ONLY
    ),
    RoutePolicy("POST", "/api/workflows/{workflow_id}/runs", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/workflows/{workflow_id}/runs", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/workflows/{workflow_id}/new-cases", RouteAccess.ACTOR_ONLY),
    RoutePolicy(
        "PUT",
        "/api/workflows/{workflow_id}/runs/{run_id}/stages/{stage_id}/answers",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST",
        "/api/workflows/{workflow_id}/runs/{run_id}/stages/{stage_id}/confirm",
        RouteAccess.ACTOR_ONLY,
    ),
    RoutePolicy(
        "POST", "/api/workflows/{workflow_id}/runs/{run_id}/documents", RouteAccess.ACTOR_ONLY
    ),
    RoutePolicy("DELETE", "/api/workflows/{workflow_id}/runs/{run_id}", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/clm/zero-touch/cases/{case_id}/workflows", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "PUT",
        "/api/clm/zero-touch/cases/{case_id}/workflows/runs/{run_id}/stages/{stage_id}/answers",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/workflows/runs/{run_id}/stages/{stage_id}/confirm",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("GET", "/api/admin/goldtier-sandbox/status", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/goldtier-sandbox/search", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/goldtier-sandbox/dry-run", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/goldtier-sandbox/write", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/admin/acra/status", RouteAccess.ACTOR_ONLY),
    RoutePolicy("POST", "/api/admin/acra/lookup", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/system/execution-profile", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/onboarding/mock-scenarios", RouteAccess.ACTOR_ONLY),
    RoutePolicy("GET", "/api/clm/zero-touch/cases", RouteAccess.CASE_PORTFOLIO),
    RoutePolicy("GET", "/api/clm/zero-touch/case-portfolio", RouteAccess.CASE_PORTFOLIO),
    RoutePolicy("GET", "/api/clm/zero-touch/activity", RouteAccess.CASE_PORTFOLIO),
    RoutePolicy("GET", "/api/clm/zero-touch/activity.csv", RouteAccess.CASE_PORTFOLIO),
    RoutePolicy("GET", "/api/clm/zero-touch/dashboard", RouteAccess.CASE_PORTFOLIO),
    RoutePolicy("POST", "/api/onboarding/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("POST", "/api/clm/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("POST", "/api/clm/zero-touch/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("POST", "/api/demo/clm/zero-touch/cases", RouteAccess.CASE_CREATION),
    RoutePolicy("GET", "/api/onboarding/cases/{case_id}", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "POST", "/api/clm/zero-touch/cases/{case_id}/review-decisions", RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("GET", "/api/clm/cases/{case_id}", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "POST",
        "/api/clm/cases/{case_id}/readiness/evaluate",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("GET", "/api/clm/cases/{case_id}/submission-plan", RouteAccess.CASE_SCOPED),
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
        "/api/demo/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry",
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
    RoutePolicy("GET", "/api/clm/zero-touch/cases/{case_id}", RouteAccess.CASE_READ),
    RoutePolicy(
        "GET",
        "/api/clm/zero-touch/cases/{case_id}/intelligence",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("DELETE", "/api/clm/zero-touch/cases/{case_id}", RouteAccess.CASE_SCOPED),
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
    RoutePolicy("POST", "/api/clm/zero-touch/cases/{case_id}/start", RouteAccess.CASE_SCOPED),
    RoutePolicy("POST", "/api/clm/zero-touch/cases/{case_id}/resume", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/reconciliation/discrepancies/{discrepancy_id}/resolve",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "PATCH",
        "/api/clm/zero-touch/cases/{case_id}/priority",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "PUT",
        "/api/clm/zero-touch/cases/{case_id}/target-classification",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/verify-goldtier",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/target-status-check",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/target-recovery",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/confirm-existing-customer",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/identity-search-recheck",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/registry-identity",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/government-status-confirmation",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy(
        "POST",
        "/api/clm/zero-touch/cases/{case_id}/policy-rebind",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("POST", "/api/onboarding/cases/{case_id}/ownership/load", RouteAccess.CASE_SCOPED),
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
    RoutePolicy("GET", "/api/onboarding/cases/{case_id}/ownership", RouteAccess.CASE_SCOPED),
    RoutePolicy("GET", "/api/onboarding/cases/{case_id}/ubo-candidates", RouteAccess.CASE_SCOPED),
    RoutePolicy("POST", "/api/onboarding/cases/{case_id}/documents", RouteAccess.CASE_SCOPED),
    RoutePolicy(
        "POST",
        "/api/demo/onboarding/cases/{case_id}/documents",
        RouteAccess.CASE_SCOPED,
    ),
    RoutePolicy("GET", "/api/onboarding/cases/{case_id}/documents", RouteAccess.CASE_READ),
    # D-095: content digests of the same documents, under the same case scope.
    RoutePolicy(
        "GET", "/api/onboarding/cases/{case_id}/document-digests", RouteAccess.CASE_SCOPED
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

    def can_use_case_routes(self, actor: AuthenticatedActor) -> bool:
        return Capability.CASE_ACCESS in ROLE_CAPABILITIES[actor.profile.role]

    def can_access(self, actor: AuthenticatedActor, case: OnboardingCase) -> bool:
        profile = actor.profile
        if not self.can_use_case_routes(actor):
            return False
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

    def can_read(self, actor: AuthenticatedActor, case: OnboardingCase) -> bool:
        """Case access, or the team-less knowledge redaction read (D-103)."""

        if self.can_access(actor, case):
            return True
        return (
            Capability.KNOWLEDGE_CASE_READ in ROLE_CAPABILITIES[actor.profile.role]
            and actor.profile.team_id is None
        )

    def require_case_read(
        self,
        actor: AuthenticatedActor,
        case_id: UUID,
        cases: OnboardingService,
    ) -> OnboardingCase:
        case = cases.get_case(case_id)
        if case is None or not self.can_read(actor, case):
            raise CaseNotAvailableError
        return case

    def can_decide_evidence(self, actor: AuthenticatedActor, case: OnboardingCase) -> bool:
        """The creating onboarding user owns bounded case evidence decisions.

        An unknown legacy creator grants no decision authority. Team/global access
        remains a prerequisite and does not substitute for this actor binding.
        """
        return bool(
            self.can_access(actor, case)
            and case.created_by_actor_id is not None
            and case.created_by_actor_id == actor.profile.user_id
        )

    def portfolio_scope(self, actor: AuthenticatedActor) -> CasePortfolioScope:
        """Translate only the authenticated server profile into a repository scope."""

        if actor.profile.role == Role.DIRECTOR:
            return CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)
        if actor.profile.team_id is None:
            raise ValueError("team actor requires a canonical team")
        return CasePortfolioScope(
            kind=PortfolioScopeKind.TEAM,
            team_id=actor.profile.team_id,
        )

    def resolve_creation_team(
        self,
        actor: AuthenticatedActor,
        requested_team: TeamId | None,
        *,
        field_was_supplied: bool,
    ) -> TeamId:
        profile = actor.profile
        if not self.can_use_case_routes(actor):
            raise CreationTeamSelectionError
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
        pieces.append(rf"(?P<{match.group(1)}>[^/]+)")
        position = match.end()
    pieces.append(re.escape(path[position:]))
    return re.compile("".join(pieces))
