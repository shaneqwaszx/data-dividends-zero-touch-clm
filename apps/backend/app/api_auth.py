"""Bounded HTTP models and route helpers for Phase 13 POC authentication."""

from collections.abc import Awaitable, Callable
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.domain.access import Role, TeamId, UserProfile
from app.services.authentication import (
    AuthenticationError,
    AuthenticationService,
    SessionCapacityError,
    SessionRecord,
)
from app.services.authorization import (
    CaseAccessPolicy,
    CaseNotAvailableError,
    RouteAccess,
    classify_route,
)
from app.services.onboarding import OnboardingService

SESSION_COOKIE_NAME = "clm_session"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Annotated[str, Field(min_length=1, max_length=64)]
    credential: Annotated[str, Field(alias="password", min_length=1, max_length=256)]


class AuthenticatedProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    display_name: str
    role: Role
    team_id: TeamId | None
    team_display_name: str | None
    client_scope_label: str

    @classmethod
    def from_domain(cls, profile: UserProfile) -> "AuthenticatedProfileResponse":
        return cls(
            user_id=profile.user_id,
            display_name=profile.display_name,
            role=profile.role,
            team_id=profile.team_id,
            team_display_name=profile.team_display_name,
            client_scope_label=profile.client_scope_label,
        )


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: AuthenticatedProfileResponse
    csrf_token: str


def build_auth_router(
    auth: AuthenticationService,
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
        return _session_response(issued.record)

    @router.get("/me", response_model=AuthSessionResponse)
    def me(request: Request) -> AuthSessionResponse:
        record = _request_session(request)
        return _session_response(record)

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
            if not request.headers.get("content-type", "").lower().startswith(
                "application/json"
            ):
                return _fixed_error(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    "AUTHENTICATION_REQUEST_INVALID",
                    "The authentication request must use JSON.",
                )
            if not _request_is_same_origin(request):
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
            not _request_is_same_origin(request)
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
        return await call_next(request)


def _request_is_same_origin(request: Request) -> bool:
    expected_scheme = request.url.scheme.lower()
    expected_host = request.url.netloc.lower()
    for name in ("origin", "referer"):
        raw = request.headers.get(name)
        if raw is None:
            continue
        parsed = urlsplit(raw)
        if parsed.scheme.lower() != expected_scheme or parsed.netloc.lower() != expected_host:
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


def _request_session(request: Request) -> SessionRecord:
    record = getattr(request.state, "auth_session", None)
    if not isinstance(record, SessionRecord):
        raise _unauthorized()
    return record


def _session_response(record: SessionRecord) -> AuthSessionResponse:
    return AuthSessionResponse(
        profile=AuthenticatedProfileResponse.from_domain(record.actor.profile),
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
