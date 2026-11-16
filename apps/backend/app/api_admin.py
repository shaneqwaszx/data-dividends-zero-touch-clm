"""Strict team options and HR-only administration HTTP contract."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.api_auth import TeamResponse
from app.domain.access import AuthenticatedActor, Role, TeamId
from app.domain.administration import TeamRecord, UserAccountRecord, sign_in_disabled
from app.persistence.errors import PersistenceUnavailableError
from app.services.admin_repository import (
    AdministrationAuditCapacityError,
    AdministrationConflictError,
    AdministrationUnavailableError,
)
from app.services.administration import (
    AdministrationCredentialVerificationError,
    AdministrationForbiddenError,
    AdministrationNotFoundError,
    AdministrationService,
    AdministrationValidationError,
)
from app.services.authentication import AuthenticatedSession
from app.services.login_admission import LoginAdmission, LoginAdmissionDenied


class AdminTeamResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    display_name: str
    team_type: str
    client_scope_label: str
    description: str | None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    @classmethod
    def from_domain(cls, team: TeamRecord) -> AdminTeamResponse:
        return cls.model_validate(
            team.model_dump(
                exclude={
                    "normalized_display_name",
                    "normalized_client_scope_label",
                    "audit_events",
                }
            )
        )


class AdminProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    display_name: str
    role: Role
    team_id: TeamId | None
    team_display_name: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    # D-140 / SF-006: derived from the audit trail; not a persisted field.
    sign_in_disabled: bool = False


class CreateTeamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: Annotated[str, Field(min_length=2, max_length=80)]
    client_scope_label: Annotated[str, Field(min_length=2, max_length=80)]
    description: Annotated[str | None, Field(default=None, max_length=240)]


class UpdateTeamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(strict=True, ge=1)]
    display_name: Annotated[str | None, Field(default=None, min_length=2, max_length=80)]
    client_scope_label: Annotated[str | None, Field(default=None, min_length=2, max_length=80)]
    description: Annotated[str | None, Field(default=None, max_length=240)]


class CreateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{2,31}$")]
    display_name: Annotated[str, Field(min_length=2, max_length=80)]
    role: Role
    team_id: TeamId | None = None
    password: Annotated[str, Field(min_length=12, max_length=128, repr=False)]


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(strict=True, ge=1)]
    display_name: Annotated[str | None, Field(default=None, min_length=2, max_length=80)]
    role: Role | None = None
    team_id: TeamId | None = None


class ChangeOwnPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[SecretStr, Field(min_length=12, max_length=128, repr=False)]
    new_password: Annotated[SecretStr, Field(min_length=12, max_length=128, repr=False)]


class ResetPasswordRequest(BaseModel):
    """D-140 body. The new password is a SecretStr: never echoed, logged or returned."""

    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(strict=True, ge=1)]
    new_password: Annotated[SecretStr, Field(min_length=12, max_length=128, repr=False)]


class DisableSignInRequest(BaseModel):
    """D-140 / SF-006 body: only the expected version; the server discards the credential."""

    model_config = ConfigDict(extra="forbid")

    expected_version: Annotated[int, Field(strict=True, ge=1)]


def build_admin_router(
    service: AdministrationService, *, login_admission: LoginAdmission | None = None
) -> APIRouter:
    router = APIRouter(tags=["administration"])
    credential_admission = login_admission or LoginAdmission()

    @router.get("/api/teams/options", response_model=list[TeamResponse])
    def team_options(request: Request) -> list[TeamResponse]:
        actor = _actor(request)
        return [TeamResponse.from_domain(team) for team in service.directory.options_for(actor)]

    @router.get("/api/admin/teams", response_model=list[AdminTeamResponse])
    def list_teams(request: Request) -> list[AdminTeamResponse]:
        return _admin_call(
            lambda: [
                AdminTeamResponse.from_domain(item) for item in service.list_teams(_actor(request))
            ]
        )

    @router.post(
        "/api/admin/teams",
        response_model=AdminTeamResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_team(body: CreateTeamRequest, request: Request) -> AdminTeamResponse:
        return _admin_call(
            lambda: AdminTeamResponse.from_domain(
                service.create_team(
                    _actor(request),
                    display_name=body.display_name,
                    client_scope_label=body.client_scope_label,
                    description=body.description,
                )
            )
        )

    @router.patch("/api/admin/teams/{team_id}", response_model=AdminTeamResponse)
    def update_team(
        team_id: TeamId, body: UpdateTeamRequest, request: Request
    ) -> AdminTeamResponse:
        return _admin_call(
            lambda: AdminTeamResponse.from_domain(
                service.update_team(
                    _actor(request),
                    team_id,
                    expected_version=body.expected_version,
                    display_name=body.display_name,
                    client_scope_label=body.client_scope_label,
                    description=body.description,
                    description_supplied="description" in body.model_fields_set,
                )
            )
        )

    @router.get("/api/admin/profiles", response_model=list[AdminProfileResponse])
    def list_profiles(request: Request) -> list[AdminProfileResponse]:
        actor = _actor(request)
        return _admin_call(
            lambda: [_profile_response(item, service) for item in service.list_profiles(actor)]
        )

    @router.post(
        "/api/admin/profiles",
        response_model=AdminProfileResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_profile(body: CreateProfileRequest, request: Request) -> AdminProfileResponse:
        actor = _actor(request)
        return _admin_call(
            lambda: _profile_response(
                service.create_profile(
                    actor,
                    user_id=body.user_id,
                    display_name=body.display_name,
                    role=body.role,
                    team_id=body.team_id,
                    password=body.password,
                ),
                service,
            )
        )

    @router.patch("/api/admin/profiles/{user_id}", response_model=AdminProfileResponse)
    def update_profile(
        user_id: str, body: UpdateProfileRequest, request: Request
    ) -> AdminProfileResponse:
        actor = _actor(request)
        return _admin_call(
            lambda: _profile_response(
                service.update_profile(
                    actor,
                    user_id,
                    expected_version=body.expected_version,
                    display_name=body.display_name,
                    role=body.role,
                    role_supplied="role" in body.model_fields_set,
                    team_id=body.team_id,
                    team_supplied="team_id" in body.model_fields_set,
                ),
                service,
            )
        )

    @router.post("/api/admin/me/password", status_code=status.HTTP_204_NO_CONTENT)
    def change_own_password(body: ChangeOwnPasswordRequest, request: Request) -> Response:
        actor = _actor(request)
        _admin_call(lambda: service.require_hr(actor))
        session = getattr(request.state, "auth_session", None)
        if not isinstance(session, AuthenticatedSession):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            with credential_admission.admit(request.client.host if request.client else None):
                _admin_call(
                    lambda: service.change_own_password(
                        actor,
                        session_security_version=session.security_version,
                        current_password=body.current_password,
                        new_password=body.new_password,
                    )
                )
        except LoginAdmissionDenied as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "LOGIN_RATE_LIMITED",
                    "message": "Too many credential attempts. Try again later.",
                },
                headers={"Retry-After": str(exc.retry_after), "Cache-Control": "no-store"},
            ) from None
        except AdministrationCredentialVerificationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CREDENTIAL_VERIFICATION_FAILED",
                    "message": "The password change could not be verified.",
                },
                headers={"Cache-Control": "no-store"},
            ) from None
        return Response(
            status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"}
        )

    @router.post("/api/admin/profiles/{user_id}/password", response_model=AdminProfileResponse)
    def reset_profile_password(
        user_id: str, body: ResetPasswordRequest, request: Request
    ) -> AdminProfileResponse:
        actor = _actor(request)
        return _admin_call(
            lambda: _profile_response(
                service.reset_password(
                    actor,
                    user_id,
                    expected_version=body.expected_version,
                    new_password=body.new_password,
                ),
                service,
            )
        )

    @router.post("/api/admin/profiles/{user_id}/disable", response_model=AdminProfileResponse)
    def disable_profile_sign_in(
        user_id: str, body: DisableSignInRequest, request: Request
    ) -> AdminProfileResponse:
        actor = _actor(request)
        return _admin_call(
            lambda: _profile_response(
                service.disable_sign_in(actor, user_id, expected_version=body.expected_version),
                service,
            )
        )

    return router


def _profile_response(
    account: UserAccountRecord, service: AdministrationService
) -> AdminProfileResponse:
    team = service.directory.get(account.team_id)
    return AdminProfileResponse(
        user_id=account.user_id,
        display_name=account.display_name,
        role=account.role,
        team_id=account.team_id,
        team_display_name=team.display_name if team is not None else None,
        version=account.version,
        created_at=account.created_at,
        updated_at=account.updated_at,
        created_by=account.created_by,
        updated_by=account.updated_by,
        sign_in_disabled=sign_in_disabled(account),
    )


def _actor(request: Request) -> AuthenticatedActor:
    actor = getattr(request.state, "actor", None)
    if not isinstance(actor, AuthenticatedActor):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "A valid authenticated session is required.",
            },
        )
    return actor


def _admin_call[ResponseT](call: Callable[[], ResponseT]) -> ResponseT:
    try:
        return call()
    except AdministrationForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADMINISTRATION_FORBIDDEN",
                "message": "Administration access is not permitted.",
            },
        ) from None
    except AdministrationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ADMINISTRATION_RECORD_NOT_FOUND",
                "message": "The administration record was not found.",
            },
        ) from None
    except (AdministrationConflictError, AdministrationAuditCapacityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ADMINISTRATION_CONFLICT",
                "message": (
                    "The administration record changed or conflicts with an existing record."
                ),
            },
        ) from None
    except AdministrationValidationError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "ADMINISTRATION_REQUEST_INVALID",
                "message": "The administration request is invalid.",
            },
        ) from None
    except (AdministrationUnavailableError, PersistenceUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ADMINISTRATION_UNAVAILABLE",
                "message": "Administration is temporarily unavailable.",
            },
        ) from None
