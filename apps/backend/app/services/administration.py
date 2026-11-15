"""Application service for dynamic team and HR-owned profile administration."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import SecretStr, ValidationError

from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability, Role, TeamId
from app.domain.administration import (
    MAX_AUDIT_EVENTS,
    PASSWORD_RESET_OPERATION,
    SIGN_IN_DISABLED_OPERATION,
    AdministrationAuditEvent,
    CredentialOperation,
    TeamRecord,
    UserAccountRecord,
    normalize_display_name,
    normalize_user_id,
)
from app.services.admin_repository import (
    AdministrationActorNotAuthorizedError,
    AdministrationAuditCapacityError,
    AdministrationAuthorityInvariantError,
    AdministrationConflictError,
    AdministrationCredentialTargetRefusedError,
    ProfileRepository,
    TeamRepository,
    generate_team_id,
    new_event_id,
)
from app.services.authentication import generate_scrypt_password_hash


class AdministrationForbiddenError(Exception):
    pass


class AdministrationValidationError(Exception):
    pass


class AdministrationNotFoundError(Exception):
    pass


class TeamDirectoryService:
    def __init__(self, teams: TeamRepository) -> None:
        self._teams = teams

    def get(self, team_id: TeamId | None) -> TeamRecord | None:
        return self._teams.get(team_id) if team_id is not None else None

    def require_active(self, team_id: TeamId) -> TeamRecord:
        team = self._teams.get(team_id)
        if team is None or not team.active:
            raise AdministrationValidationError
        return team

    def options_for(self, actor: AuthenticatedActor) -> list[TeamRecord]:
        if actor.profile.role in {Role.DIRECTOR, Role.HR}:
            return [team for team in self._teams.list() if team.active]
        if actor.profile.team_id is None:
            return []
        team = self._teams.get(actor.profile.team_id)
        return [team] if team is not None and team.active else []


class AdministrationService:
    def __init__(
        self,
        teams: TeamRepository,
        profiles: ProfileRepository,
        *,
        revoke_sessions: Callable[[str], None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.teams = teams
        self.profiles = profiles
        self.directory = TeamDirectoryService(teams)
        self._revoke_sessions = revoke_sessions or (lambda user_id: None)
        self._clock = clock or (lambda: datetime.now(UTC))

    def bind_session_revoker(self, revoker: Callable[[str], None]) -> None:
        self._revoke_sessions = revoker

    def require_hr(self, actor: AuthenticatedActor) -> None:
        if Capability.IDENTITY_ADMIN not in ROLE_CAPABILITIES[actor.profile.role]:
            raise AdministrationForbiddenError

    def list_teams(self, actor: AuthenticatedActor) -> list[TeamRecord]:
        self.require_hr(actor)
        return self.teams.list()

    def create_team(
        self,
        actor: AuthenticatedActor,
        *,
        display_name: str,
        client_scope_label: str,
        description: str | None,
    ) -> TeamRecord:
        self.require_hr(actor)
        now = self._clock()
        clean_name = _clean_required(display_name, 2, 80)
        clean_scope = _clean_required(client_scope_label, 2, 80)
        clean_description = _clean_optional(description, 240)
        for _ in range(8):
            team_id = generate_team_id()
            event = _event(
                "TEAM_CREATED",
                actor.profile.user_id,
                str(team_id),
                now,
                1,
                {"display_name": clean_name, "client_scope_label": clean_scope},
            )
            candidate = TeamRecord(
                team_id=team_id,
                display_name=clean_name,
                normalized_display_name=normalize_display_name(clean_name),
                client_scope_label=clean_scope,
                normalized_client_scope_label=normalize_display_name(clean_scope),
                description=clean_description,
                version=1,
                created_at=now,
                updated_at=now,
                created_by=actor.profile.user_id,
                updated_by=actor.profile.user_id,
                audit_events=(event,),
            )
            try:
                return self.teams.create(candidate)
            except AdministrationConflictError:
                if any(
                    item.normalized_display_name == candidate.normalized_display_name
                    or item.normalized_client_scope_label == candidate.normalized_client_scope_label
                    for item in self.teams.list()
                ):
                    raise
        raise AdministrationConflictError

    def update_team(
        self,
        actor: AuthenticatedActor,
        team_id: TeamId,
        *,
        expected_version: int,
        display_name: str | None = None,
        client_scope_label: str | None = None,
        description: str | None = None,
        description_supplied: bool = False,
    ) -> TeamRecord:
        self.require_hr(actor)
        current = self.teams.get(team_id)
        if current is None:
            raise AdministrationNotFoundError
        if len(current.audit_events) >= MAX_AUDIT_EVENTS:
            raise AdministrationAuditCapacityError
        now = self._clock()
        next_version = current.version + 1
        next_name = (
            _clean_required(display_name, 2, 80)
            if display_name is not None
            else current.display_name
        )
        next_scope = (
            _clean_required(client_scope_label, 2, 80)
            if client_scope_label is not None
            else current.client_scope_label
        )
        next_description = (
            _clean_optional(description, 240) if description_supplied else current.description
        )
        event = _event(
            "TEAM_UPDATED",
            actor.profile.user_id,
            str(team_id),
            now,
            next_version,
            {"display_name": next_name, "client_scope_label": next_scope},
        )
        candidate = current.model_copy(
            update={
                "display_name": next_name,
                "normalized_display_name": normalize_display_name(next_name),
                "client_scope_label": next_scope,
                "normalized_client_scope_label": normalize_display_name(next_scope),
                "description": next_description,
                "version": next_version,
                "updated_at": now,
                "updated_by": actor.profile.user_id,
                "audit_events": (*current.audit_events, event),
            },
            deep=True,
        )
        return self.teams.update(candidate, expected_version=expected_version)

    def list_profiles(self, actor: AuthenticatedActor) -> list[UserAccountRecord]:
        self.require_hr(actor)
        return self.profiles.list()

    def create_profile(
        self,
        actor: AuthenticatedActor,
        *,
        user_id: str,
        display_name: str,
        role: Role,
        team_id: TeamId | None,
        password: str,
    ) -> UserAccountRecord:
        self.require_hr(actor)
        try:
            normalized_user_id = normalize_user_id(user_id)
        except ValueError:
            raise AdministrationValidationError from None
        clean_name = _clean_required(display_name, 2, 80)
        self._validate_role_team(role, team_id)
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            raise AdministrationValidationError
        encoded = generate_scrypt_password_hash(password)
        now = self._clock()
        event = _event(
            "PROFILE_CREATED",
            actor.profile.user_id,
            normalized_user_id,
            now,
            1,
            {"display_name": clean_name, "role": role.value, "team_id": team_id},
        )
        try:
            candidate = UserAccountRecord(
                user_id=normalized_user_id,
                display_name=clean_name,
                role=role,
                team_id=team_id,
                credential_hash=SecretStr(encoded),
                security_version=1,
                version=1,
                created_at=now,
                updated_at=now,
                created_by=actor.profile.user_id,
                updated_by=actor.profile.user_id,
                audit_events=(event,),
            )
        except ValidationError:
            raise AdministrationValidationError from None
        return self.profiles.create(candidate)

    def update_profile(
        self,
        actor: AuthenticatedActor,
        user_id: str,
        *,
        expected_version: int,
        display_name: str | None,
        role: Role | None,
        role_supplied: bool,
        team_id: TeamId | None,
        team_supplied: bool,
    ) -> UserAccountRecord:
        self.require_hr(actor)
        current = self.profiles.get(user_id)
        if current is None:
            raise AdministrationNotFoundError
        next_role = role if role_supplied and role is not None else current.role
        next_team = team_id if team_supplied else current.team_id
        if role_supplied and role is None:
            raise AdministrationValidationError
        if (
            role_supplied
            and next_role in {Role.DIRECTOR, Role.HR, Role.SUPPORT}
            and not team_supplied
        ):
            next_team = None
        self._validate_role_team(next_role, next_team)
        if len(current.audit_events) >= MAX_AUDIT_EVENTS:
            raise AdministrationAuditCapacityError
        next_name = (
            _clean_required(display_name, 2, 80)
            if display_name is not None
            else current.display_name
        )
        authority_changed = next_role != current.role or next_team != current.team_id
        now = self._clock()
        if authority_changed:
            try:
                persisted = self.profiles.mutate_authority(
                    actor_user_id=actor.profile.user_id,
                    user_id=user_id,
                    expected_version=expected_version,
                    display_name=next_name,
                    role=next_role,
                    team_id=next_team,
                    updated_at=now,
                )
            except AdministrationAuthorityInvariantError:
                raise AdministrationValidationError from None
            self._revoke_sessions(user_id)
            return persisted
        next_version = current.version + 1
        event = _event(
            "PROFILE_AUTHORITY_UPDATED" if authority_changed else "PROFILE_UPDATED",
            actor.profile.user_id,
            user_id,
            now,
            next_version,
            {"display_name": next_name, "role": next_role.value, "team_id": next_team},
        )
        candidate = current.model_copy(
            update={
                "display_name": next_name,
                "role": next_role,
                "team_id": next_team,
                "security_version": current.security_version + (1 if authority_changed else 0),
                "version": next_version,
                "updated_at": now,
                "updated_by": actor.profile.user_id,
                "audit_events": (*current.audit_events, event),
            },
            deep=True,
        )
        try:
            persisted = self.profiles.update(candidate, expected_version=expected_version)
        except ValidationError:
            raise AdministrationValidationError from None
        return persisted

    def reset_password(
        self,
        actor: AuthenticatedActor,
        user_id: str,
        *,
        expected_version: int,
        new_password: SecretStr,
    ) -> UserAccountRecord:
        """D-140: HR replaces a non-HR account credential and revokes its sessions.

        The plaintext is hashed immediately and never logged, stored, audited or returned.
        """

        self.require_hr(actor)
        plaintext = (
            new_password.get_secret_value() if isinstance(new_password, SecretStr) else None
        )
        if not isinstance(plaintext, str) or not 12 <= len(plaintext) <= 128:
            raise AdministrationValidationError
        return self._replace_credential(
            actor, user_id, expected_version, plaintext, PASSWORD_RESET_OPERATION
        )

    def disable_sign_in(
        self, actor: AuthenticatedActor, user_id: str, *, expected_version: int
    ) -> UserAccountRecord:
        """SF-006 / D-140: lock a non-HR account by replacing its credential with the hash
        of a random value that is discarded at once. A later password reset re-enables it."""

        self.require_hr(actor)
        return self._replace_credential(
            actor,
            user_id,
            expected_version,
            secrets.token_urlsafe(48),
            SIGN_IN_DISABLED_OPERATION,
        )

    def _replace_credential(
        self,
        actor: AuthenticatedActor,
        user_id: str,
        expected_version: int,
        plaintext: str,
        operation: CredentialOperation,
    ) -> UserAccountRecord:
        current = self.profiles.get(user_id)
        if current is None:
            raise AdministrationNotFoundError
        if current.role == Role.HR:
            raise AdministrationForbiddenError
        encoded = SecretStr(generate_scrypt_password_hash(plaintext))
        try:
            persisted = self.profiles.replace_credential(
                actor_user_id=actor.profile.user_id,
                user_id=current.user_id,
                expected_version=expected_version,
                credential_hash=encoded,
                operation=operation,
                updated_at=self._clock(),
            )
        except (
            AdministrationActorNotAuthorizedError,
            AdministrationCredentialTargetRefusedError,
        ):
            raise AdministrationForbiddenError from None
        self._revoke_sessions(persisted.user_id)
        return persisted

    def _validate_role_team(self, role: Role, team_id: TeamId | None) -> None:
        if role in {Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER}:
            if team_id is None:
                raise AdministrationValidationError
            self.directory.require_active(team_id)
        elif team_id is not None:
            raise AdministrationValidationError


def _clean_required(value: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise AdministrationValidationError
    clean = " ".join(value.strip().split())
    if not minimum <= len(clean) <= maximum:
        raise AdministrationValidationError
    return clean


def _clean_optional(value: str | None, maximum: int) -> str | None:
    if value is None:
        return None
    clean = " ".join(value.strip().split())
    if not clean:
        return None
    if len(clean) > maximum:
        raise AdministrationValidationError
    return clean


def _event(
    action: str,
    actor: str,
    target: str,
    timestamp: datetime,
    version: int,
    metadata: dict[str, object],
) -> AdministrationAuditEvent:
    return AdministrationAuditEvent.model_validate(
        {
            "event_id": new_event_id(),
            "action": action,
            "actor_user_id": actor,
            "target_id": target,
            "timestamp": timestamp,
            "resulting_version": version,
            "metadata": metadata,
        }
    )
