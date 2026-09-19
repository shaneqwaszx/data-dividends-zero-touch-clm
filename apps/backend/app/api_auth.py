"""Bounded HTTP models and route helpers for Phase 13 POC authentication."""

import re
from collections.abc import Awaitable, Callable, Collection
from dataclasses import dataclass
from ipaddress import IPv6Address
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import ROLE_CAPABILITIES, Capability, Role, TeamId, UserProfile
from app.domain.administration import TeamRecord
from app.services.administration import TeamDirectoryService
from app.services.authentication import (
    AuthenticatedSession,
    AuthenticationError,
    AuthenticationService,
    SessionCapacityError,
)
from app.services.authorization import (
    CaseAccessPolicy,
    CaseNotAvailableError,
    RouteAccess,
    classify_route,
)
from app.services.onboarding import OnboardingService

SESSION_COOKIE_NAME = "clm_session"
DNS_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]+$")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Annotated[str, Field(min_length=1, max_length=64)]
    credential: Annotated[str, Field(alias="password", min_length=1, max_length=256)]


class TeamResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    display_name: str
    team_type: str
    client_scope_label: str
    description: str

    @classmethod
    def from_domain(cls, team: TeamRecord) -> "TeamResponse":
        return cls(
            team_id=team.team_id,
            display_name=team.display_name,
            team_type=team.team_type,
            client_scope_label=team.client_scope_label,
            description=team.presentation_description,
        )


class AuthenticatedProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    display_name: str
    role: Role
    team_id: TeamId | None
    team_display_name: str | None
    team_type: str | None
    team_description: str
    client_scope_label: str
    capabilities: tuple[Capability, ...]

    @classmethod
    def from_domain(
        cls, profile: UserProfile, teams: TeamDirectoryService
    ) -> "AuthenticatedProfileResponse":
        team = teams.get(profile.team_id)
        is_hr = profile.role == Role.HR
        return cls(
            user_id=profile.user_id,
            display_name=profile.display_name,
            role=profile.role,
            team_id=profile.team_id,
            team_display_name=team.display_name if team is not None else None,
            team_type=team.team_type if team is not None else None,
            team_description=(
                team.presentation_description
                if team is not None
                else (
                    "Administration only; no client-case access"
                    if is_hr
                    else "Global / cross-team access"
                )
            ),
            client_scope_label=(
                team.client_scope_label
                if team is not None
                else ("Administration" if is_hr else "Global / cross-team")
            ),
            capabilities=tuple(sorted(ROLE_CAPABILITIES[profile.role], key=str)),
        )


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: AuthenticatedProfileResponse
    csrf_token: str


@dataclass(frozen=True)
class BrowserOriginPolicy:
    """Own the exact browser origins accepted by the Phase 13 CSRF boundary."""

    trusted_origins: frozenset[str]

    @classmethod
    def from_origins(
        cls,
        origins: Collection[str],
        *,
        require_https: bool = False,
    ) -> "BrowserOriginPolicy":
        normalized = frozenset(
            _normalize_configured_origin(origin, require_https=require_https) for origin in origins
        )
        if not normalized:
            raise ValueError("at least one trusted browser origin is required")
        return cls(trusted_origins=normalized)

    def request_is_trusted(self, request: Request) -> bool:
        origin_is_unambiguous, origin = _single_header_value(request, "origin")
        if not origin_is_unambiguous:
            return False
        if origin is not None and _normalize_header_origin(origin) not in self.trusted_origins:
            return False
        referer_is_unambiguous, referer = _single_header_value(request, "referer")
        if not referer_is_unambiguous:
            return False
        return referer is None or _referer_origin(referer) in self.trusted_origins


def build_auth_router(
    auth: AuthenticationService,
    teams: TeamDirectoryService,
    *,
    cookie_secure: bool,
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["authentication"])

    @router.post("/login", response_model=AuthSessionResponse)
    def login(body: LoginRequest, response: Response) -> AuthSessionResponse:
        try:
            issued = auth.login(body.user_id, body.credential)
        except AuthenticationError:
            raise _unauthorized() from None
        except SessionCapacityError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "AUTHENTICATION_UNAVAILABLE",
                    "message": "Authentication is temporarily unavailable.",
                },
            ) from None
        response.set_cookie(
            SESSION_COOKIE_NAME,
            issued.token,
            httponly=True,
            secure=cookie_secure,
            samesite="strict",
            path="/api",
            max_age=8 * 60 * 60,
        )
        return _session_response(issued.record, teams)

    @router.get("/me", response_model=AuthSessionResponse)
    def me(request: Request) -> AuthSessionResponse:
        record = _request_session(request)
        return _session_response(record, teams)

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request, response: Response) -> Response:
        try:
            auth.logout(request.cookies.get(SESSION_COOKIE_NAME))
        except AuthenticationError:
            raise _unauthorized() from None
        response.delete_cookie(
            SESSION_COOKIE_NAME,
            path="/api",
            secure=cookie_secure,
            httponly=True,
            samesite="strict",
        )
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    return router


def install_auth_boundary(
    application: FastAPI,
    auth: AuthenticationService,
    access: CaseAccessPolicy,
    cases: OnboardingService,
    *,
    browser_origin_policy: BrowserOriginPolicy,
) -> None:
    """Default-protect `/api` and centrally authorize every case-scoped route."""

    @application.middleware("http")
    async def authenticate_and_authorize(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        method = request.method.upper()
        policy, path_values = classify_route(method, path)
        if path == "/api/auth/login" and method == "POST":
            if not request.headers.get("content-type", "").lower().startswith("application/json"):
                return _fixed_error(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    "AUTHENTICATION_REQUEST_INVALID",
                    "The authentication request must use JSON.",
                )
            if not browser_origin_policy.request_is_trusted(request):
                return _csrf_error()
            return await call_next(request)
        if not path.startswith("/api"):
            return await call_next(request)

        try:
            session = auth.authenticate_session(request.cookies.get(SESSION_COOKIE_NAME))
        except AuthenticationError:
            return _fixed_error(
                status.HTTP_401_UNAUTHORIZED,
                "AUTHENTICATION_REQUIRED",
                "A valid authenticated session is required.",
            )
        request.state.auth_session = session
        request.state.actor = session.actor

        if method in {"POST", "PUT", "PATCH", "DELETE"} and (
            not browser_origin_policy.request_is_trusted(request)
            or not auth.verify_csrf(session, request.headers.get("X-CSRF-Token"))
        ):
            return _csrf_error()

        if policy is not None and policy.access == RouteAccess.CASE_SCOPED:
            try:
                case_id = UUID(path_values["case_id"])
                request.state.authorized_case = access.require_case_access(
                    session.actor, case_id, cases
                )
            except (CaseNotAvailableError, KeyError, TypeError, ValueError):
                return _fixed_error(
                    status.HTTP_404_NOT_FOUND,
                    "CASE_NOT_FOUND",
                    "The requested case was not found.",
                )
        elif (
            policy is not None
            and policy.access
            in {
                RouteAccess.CASE_CREATION,
                RouteAccess.CASE_PORTFOLIO,
            }
            and not access.can_use_case_routes(session.actor)
        ):
            return _fixed_error(
                status.HTTP_403_FORBIDDEN,
                "CASE_ACCESS_FORBIDDEN",
                "Client-case access is not permitted.",
            )
        return await call_next(request)


def build_case_reauthorizer(
    request: Request,
    auth: AuthenticationService,
    access: CaseAccessPolicy,
    cases: OnboardingService,
    case_id: UUID,
) -> Callable[[], None]:
    """Capture request credentials for a fresh check inside the case mutation lock."""

    token = request.cookies.get(SESSION_COOKIE_NAME)

    def reauthorize() -> None:
        try:
            session = auth.authenticate_session(token)
        except AuthenticationError:
            raise _unauthorized() from None
        try:
            access.require_case_access(session.actor, case_id, cases)
        except CaseNotAvailableError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "CASE_NOT_FOUND",
                    "message": "The requested case was not found.",
                },
            ) from None

    return reauthorize


def _normalize_configured_origin(raw: str, *, require_https: bool = False) -> str:
    normalized = _parse_http_url(raw, allow_resource=False)
    if not normalized or (require_https and not normalized.startswith("https://")):
        raise ValueError("trusted browser origins must be exact HTTP(S) origins")
    return normalized


def _normalize_header_origin(raw: str) -> str:
    return _parse_http_url(raw, allow_resource=False)


def _referer_origin(raw: str) -> str:
    return _parse_http_url(raw, allow_resource=True)


def _single_header_value(request: Request, name: str) -> tuple[bool, str | None]:
    values = request.headers.getlist(name)
    if len(values) > 1:
        return False, None
    return True, values[0] if values else None


def _parse_http_url(raw: str, *, allow_resource: bool) -> str:
    if not raw or raw != raw.strip() or any(character.isspace() for character in raw):
        return ""
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.netloc.endswith(":")
        or not _valid_hostname(parsed.hostname)
        or parsed.fragment
        or (not allow_resource and (parsed.path or parsed.query))
    ):
        return ""
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    host_literal = f"[{host}]" if ":" in host else host
    default_port = 80 if scheme == "http" else 443
    authority = host_literal if port in {None, default_port} else f"{host_literal}:{port}"
    return f"{scheme}://{authority}"


def _valid_hostname(host: str) -> bool:
    if ":" not in host:
        return bool(DNS_HOST_PATTERN.fullmatch(host))
    try:
        IPv6Address(host)
    except ValueError:
        return False
    return True


def _csrf_error() -> JSONResponse:
    return _fixed_error(
        status.HTTP_403_FORBIDDEN,
        "CSRF_VALIDATION_FAILED",
        "The request could not be validated.",
    )


def _fixed_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message}},
    )


def _request_session(request: Request) -> AuthenticatedSession:
    record = getattr(request.state, "auth_session", None)
    if not isinstance(record, AuthenticatedSession):
        raise _unauthorized()
    return record


def _session_response(
    record: AuthenticatedSession, teams: TeamDirectoryService
) -> AuthSessionResponse:
    return AuthSessionResponse(
        profile=AuthenticatedProfileResponse.from_domain(record.actor.profile, teams),
        csrf_token=record.csrf_token,
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "AUTHENTICATION_REQUIRED",
            "message": "A valid authenticated session is required.",
        },
    )
