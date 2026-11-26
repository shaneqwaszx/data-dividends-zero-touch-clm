"""Repository protocols, memory implementations, and idempotent administration seeds."""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol

from pydantic import SecretStr

from app.domain.access import (
    ROLE_CAPABILITIES,
    SYNTHETIC_USER_PROFILES,
    Capability,
    Role,
    TeamId,
)
from app.domain.administration import (
    CREDENTIAL_OPERATION_KEY,
    MAX_AUDIT_EVENTS,
    PASSWORD_CHANGED_SELF_OPERATION,
    AdministrationAuditEvent,
    CredentialOperation,
    TeamRecord,
    UserAccountRecord,
    audit_is_prefix,
    normalize_display_name,
    sign_in_disabled,
)
from app.domain.policy import PolicyCatalogue


class AdministrationConflictError(Exception):
    """A uniqueness or optimistic-version boundary rejected a mutation."""


class AdministrationUnavailableError(Exception):
    """Administration persistence is unavailable or invalid."""


class AdministrationAuditCapacityError(AdministrationConflictError):
    """Append-only audit capacity has been exhausted."""


class AdministrationAuthorityInvariantError(Exception):
    """A profile authority mutation would violate a global safety invariant."""


class AdministrationActorNotAuthorizedError(Exception):
    """The acting account no longer holds identity-administration authority (D-140)."""


class AdministrationCredentialTargetRefusedError(Exception):
    """The credential target is outside the HR password-reset scope (D-140)."""


class TeamRepository(Protocol):
    def list(self) -> list[TeamRecord]: ...
    def get(self, team_id: TeamId) -> TeamRecord | None: ...
    def create(self, record: TeamRecord) -> TeamRecord: ...
    def update(self, record: TeamRecord, *, expected_version: int) -> TeamRecord: ...


class ProfileRepository(Protocol):
    def list(self) -> list[UserAccountRecord]: ...
    def get(self, user_id: str) -> UserAccountRecord | None: ...
    def create(self, record: UserAccountRecord) -> UserAccountRecord: ...
    def update(self, record: UserAccountRecord, *, expected_version: int) -> UserAccountRecord: ...
    def mutate_authority(
        self,
        *,
        actor_user_id: str,
        user_id: str,
        expected_version: int,
        display_name: str,
        role: Role,
        team_id: TeamId | None,
        updated_at: datetime,
    ) -> UserAccountRecord: ...
    def replace_credential(
        self,
        *,
        actor_user_id: str,
        user_id: str,
        expected_version: int,
        credential_hash: SecretStr,
        operation: CredentialOperation,
        updated_at: datetime,
        expected_actor_security_version: int | None = None,
    ) -> UserAccountRecord: ...


class PolicyRepository(Protocol):
    def get(self) -> PolicyCatalogue | None: ...
    def create(self, catalogue: PolicyCatalogue) -> PolicyCatalogue: ...
    def update(self, catalogue: PolicyCatalogue, *, expected_version: int) -> PolicyCatalogue: ...


class InMemoryTeamRepository:
    def __init__(self) -> None:
        self._records: dict[TeamId, TeamRecord] = {}
        self._lock = RLock()

    def list(self) -> list[TeamRecord]:
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in sorted(
                    self._records.values(),
                    key=lambda item: (not item.active, item.display_name.casefold()),
                )
            ]

    def get(self, team_id: TeamId) -> TeamRecord | None:
        with self._lock:
            record = self._records.get(TeamId(team_id))
            return record.model_copy(deep=True) if record is not None else None

    def create(self, record: TeamRecord) -> TeamRecord:
        candidate = TeamRecord.model_validate(record)
        with self._lock:
            if candidate.team_id in self._records or self._name_conflicts(candidate, None):
                raise AdministrationConflictError
            self._records[candidate.team_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def update(self, record: TeamRecord, *, expected_version: int) -> TeamRecord:
        candidate = TeamRecord.model_validate(record)
        with self._lock:
            current = self._records.get(candidate.team_id)
            if (
                current is None
                or current.version != expected_version
                or candidate.version != expected_version + 1
                or candidate.created_at != current.created_at
                or candidate.created_by != current.created_by
                or candidate.team_type != current.team_type
                or candidate.active != current.active
                or not audit_is_prefix(current.audit_events, candidate.audit_events)
                or self._name_conflicts(candidate, candidate.team_id)
            ):
                raise AdministrationConflictError
            self._records[candidate.team_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def _name_conflicts(self, candidate: TeamRecord, excluded: TeamId | None) -> bool:
        return any(
            item.team_id != excluded
            and (
                item.normalized_display_name == candidate.normalized_display_name
                or item.normalized_client_scope_label == candidate.normalized_client_scope_label
            )
            for item in self._records.values()
        )


class InMemoryProfileRepository:
    def __init__(self) -> None:
        self._records: dict[str, UserAccountRecord] = {}
        self._lock = RLock()

    def list(self) -> list[UserAccountRecord]:
        with self._lock:
            return [
                item.model_copy(deep=True)
                for item in sorted(self._records.values(), key=lambda item: item.user_id)
            ]

    def get(self, user_id: str) -> UserAccountRecord | None:
        with self._lock:
            record = self._records.get(user_id.casefold()) if isinstance(user_id, str) else None
            return record.model_copy(deep=True) if record is not None else None

    def create(self, record: UserAccountRecord) -> UserAccountRecord:
        candidate = UserAccountRecord.model_validate(record)
        with self._lock:
            if candidate.user_id.casefold() in self._records:
                raise AdministrationConflictError
            self._records[candidate.user_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def update(self, record: UserAccountRecord, *, expected_version: int) -> UserAccountRecord:
        candidate = UserAccountRecord.model_validate(record)
        with self._lock:
            current = self._records.get(candidate.user_id)
            if (
                current is None
                or current.version != expected_version
                or candidate.version != expected_version + 1
                or candidate.created_at != current.created_at
                or candidate.created_by != current.created_by
                or candidate.credential_hash.get_secret_value()
                != current.credential_hash.get_secret_value()
                or not audit_is_prefix(current.audit_events, candidate.audit_events)
            ):
                raise AdministrationConflictError
            self._records[candidate.user_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def mutate_authority(
        self,
        *,
        actor_user_id: str,
        user_id: str,
        expected_version: int,
        display_name: str,
        role: Role,
        team_id: TeamId | None,
        updated_at: datetime,
    ) -> UserAccountRecord:
        """Serialize the cross-record last-HR check with the target authority write."""

        with self._lock:
            current = self._records.get(user_id)
            if current is None or current.version != expected_version:
                raise AdministrationConflictError
            if actor_user_id == user_id and current.role == Role.HR and role != Role.HR:
                raise AdministrationAuthorityInvariantError
            if current.role == Role.HR and role != Role.HR:
                hr_count = sum(item.role == Role.HR for item in self._records.values())
                if hr_count <= 1:
                    raise AdministrationAuthorityInvariantError
            candidate = build_profile_authority_candidate(
                current,
                actor_user_id=actor_user_id,
                display_name=display_name,
                role=role,
                team_id=team_id,
                updated_at=updated_at,
            )
            self._records[user_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def replace_credential(
        self,
        *,
        actor_user_id: str,
        user_id: str,
        expected_version: int,
        credential_hash: SecretStr,
        operation: CredentialOperation,
        updated_at: datetime,
        expected_actor_security_version: int | None = None,
    ) -> UserAccountRecord:
        """D-140: reauthorize the actor and CAS-replace one credential under the owning lock."""

        with self._lock:
            check_credential_replacement_actor(
                self._records.get(actor_user_id), operation, expected_actor_security_version
            )
            current = self._records.get(user_id)
            if current is None or current.version != expected_version:
                raise AdministrationConflictError
            candidate = build_credential_reset_candidate(
                current,
                actor_user_id=actor_user_id,
                credential_hash=credential_hash,
                operation=operation,
                updated_at=updated_at,
            )
            self._records[user_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)


class InMemoryPolicyRepository:
    def __init__(self) -> None:
        self._catalogue: PolicyCatalogue | None = None
        self._lock = RLock()

    def get(self) -> PolicyCatalogue | None:
        with self._lock:
            return self._catalogue.model_copy(deep=True) if self._catalogue else None

    def create(self, catalogue: PolicyCatalogue) -> PolicyCatalogue:
        candidate = PolicyCatalogue.model_validate(catalogue)
        with self._lock:
            if self._catalogue is not None:
                raise AdministrationConflictError
            self._catalogue = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def update(self, catalogue: PolicyCatalogue, *, expected_version: int) -> PolicyCatalogue:
        candidate = PolicyCatalogue.model_validate(catalogue)
        with self._lock:
            current = self._catalogue
            if (
                current is None
                or current.version != expected_version
                or candidate.version != expected_version + 1
                or candidate.created_at != current.created_at
                or len(candidate.audit_events) != len(current.audit_events) + 1
                or candidate.audit_events[: len(current.audit_events)] != current.audit_events
            ):
                raise AdministrationConflictError
            self._catalogue = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)


def bootstrap_administration(
    teams: TeamRepository,
    profiles: ProfileRepository,
    credential_hashes: Mapping[str, SecretStr | str | None],
    *,
    now: datetime | None = None,
) -> None:
    """Insert missing exact seeds and never overwrite persisted administration state."""

    timestamp = now or datetime.now(UTC)
    for team_id, display_name in (
        (TeamId.TEAM_A, "Alpha"),
        (TeamId.TEAM_B, "Beta"),
    ):
        if teams.get(team_id) is None:
            event = _admin_event(
                action="TEAM_CREATED",
                actor="system-bootstrap",
                target=str(team_id),
                timestamp=timestamp,
                version=1,
                metadata={"display_name": display_name},
            )
            teams.create(
                TeamRecord(
                    team_id=team_id,
                    display_name=display_name,
                    normalized_display_name=normalize_display_name(display_name),
                    client_scope_label=display_name,
                    normalized_client_scope_label=normalize_display_name(display_name),
                    description=None,
                    version=1,
                    created_at=timestamp,
                    updated_at=timestamp,
                    created_by="system-bootstrap",
                    updated_by="system-bootstrap",
                    audit_events=(event,),
                )
            )

    seeds = (*SYNTHETIC_USER_PROFILES,)
    for profile in seeds:
        _insert_seed_profile(profiles, credential_hashes, profile, timestamp)
    from app.domain.access import UserProfile

    _insert_seed_profile(
        profiles,
        credential_hashes,
        UserProfile(
            user_id="biz-ops",
            display_name="POC Biz Ops Administrator",
            role=Role.HR,
            team_id=None,
        ),
        timestamp,
    )
    _insert_seed_profile(
        profiles,
        credential_hashes,
        UserProfile(
            user_id="support-user",
            display_name="Support User",
            role=Role.SUPPORT,
            team_id=None,
        ),
        timestamp,
    )


def _insert_seed_profile(
    profiles: ProfileRepository,
    credential_hashes: Mapping[str, SecretStr | str | None],
    profile: object,
    timestamp: datetime,
) -> None:
    from app.domain.access import UserProfile
    from app.services.authentication import (
        AuthenticationConfigurationError,
        credential_setting_key,
        parse_scrypt_password_hash,
    )

    safe_profile = UserProfile.model_validate(profile)
    current = profiles.get(safe_profile.user_id)
    if current is not None:
        try:
            parse_scrypt_password_hash(current.credential_hash.get_secret_value())
        except ValueError:
            raise AdministrationUnavailableError from None
        return
    secret = credential_hashes.get(safe_profile.user_id)
    if secret is None:
        raise AuthenticationConfigurationError(credential_setting_key(safe_profile.user_id))
    encoded = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
    try:
        parse_scrypt_password_hash(encoded)
    except ValueError:
        raise AuthenticationConfigurationError(
            credential_setting_key(safe_profile.user_id)
        ) from None
    event = _admin_event(
        action="PROFILE_CREATED",
        actor="system-bootstrap",
        target=safe_profile.user_id,
        timestamp=timestamp,
        version=1,
        metadata={"role": safe_profile.role.value, "team_id": safe_profile.team_id},
    )
    profiles.create(
        UserAccountRecord(
            user_id=safe_profile.user_id,
            display_name=safe_profile.display_name,
            role=safe_profile.role,
            team_id=safe_profile.team_id,
            credential_hash=SecretStr(encoded),
            security_version=1,
            version=1,
            created_at=timestamp,
            updated_at=timestamp,
            created_by="system-bootstrap",
            updated_by="system-bootstrap",
            audit_events=(event,),
        )
    )


def generate_team_id() -> TeamId:
    return TeamId(f"TEAM_{secrets.token_hex(12).upper()}")


def new_event_id() -> str:
    return secrets.token_hex(12).upper()


def build_profile_authority_candidate(
    current: UserAccountRecord,
    *,
    actor_user_id: str,
    display_name: str,
    role: Role,
    team_id: TeamId | None,
    updated_at: datetime,
) -> UserAccountRecord:
    if role == Role.HR and sign_in_disabled(current):
        raise AdministrationAuthorityInvariantError
    if len(current.audit_events) >= MAX_AUDIT_EVENTS:
        raise AdministrationAuditCapacityError
    authority_changed = role != current.role or team_id != current.team_id
    next_version = current.version + 1
    event = _admin_event(
        action="PROFILE_AUTHORITY_UPDATED",
        actor=actor_user_id,
        target=current.user_id,
        timestamp=updated_at,
        version=next_version,
        metadata={"display_name": display_name, "role": role.value, "team_id": team_id},
    )
    return UserAccountRecord.model_validate(
        current.model_copy(
            update={
                "display_name": display_name,
                "role": role,
                "team_id": team_id,
                "security_version": current.security_version + (1 if authority_changed else 0),
                "version": next_version,
                "updated_at": updated_at,
                "updated_by": actor_user_id,
                "audit_events": (*current.audit_events, event),
            },
            deep=True,
        )
    )


def check_credential_replacement_actor(
    actor: UserAccountRecord | None,
    operation: CredentialOperation,
    expected_actor_security_version: int | None,
) -> None:
    """Require current HR authority and bind a self-change to the admitted session epoch."""
    if actor is None or Capability.IDENTITY_ADMIN not in ROLE_CAPABILITIES[actor.role]:
        raise AdministrationActorNotAuthorizedError
    if (
        operation == PASSWORD_CHANGED_SELF_OPERATION
        and actor.security_version != expected_actor_security_version
    ):
        raise AdministrationActorNotAuthorizedError


def build_credential_reset_candidate(
    current: UserAccountRecord,
    *,
    actor_user_id: str,
    credential_hash: SecretStr,
    operation: CredentialOperation,
    updated_at: datetime,
) -> UserAccountRecord:
    """Replace only the credential, bump both versions, and append a secret-free audit event.

    HR can only change its own credential through the self-change operation.
    The security epoch revokes every existing session. The existing audit action and
    metadata shape remain decodable by older images.
    """

    if operation == PASSWORD_CHANGED_SELF_OPERATION:
        if current.role != Role.HR or current.user_id != actor_user_id:
            raise AdministrationCredentialTargetRefusedError
    elif current.role == Role.HR:
        raise AdministrationCredentialTargetRefusedError
    if len(current.audit_events) >= MAX_AUDIT_EVENTS:
        raise AdministrationAuditCapacityError
    next_version = current.version + 1
    next_security_version = current.security_version + 1
    event = _admin_event(
        action="PROFILE_UPDATED",
        actor=actor_user_id,
        target=current.user_id,
        timestamp=updated_at,
        version=next_version,
        metadata={
            CREDENTIAL_OPERATION_KEY: operation,
            "previous_version": current.version,
            # security_version as an epoch: metadata keys may not contain "uri".
            "resulting_access_epoch": next_security_version,
        },
    )
    return UserAccountRecord.model_validate(
        current.model_copy(
            update={
                "credential_hash": credential_hash,
                "security_version": next_security_version,
                "version": next_version,
                "updated_at": updated_at,
                "updated_by": actor_user_id,
                "audit_events": (*current.audit_events, event),
            },
            deep=True,
        )
    )


def _admin_event(
    *,
    action: str,
    actor: str,
    target: str,
    timestamp: datetime,
    version: int,
    metadata: dict[str, object],
) -> AdministrationAuditEvent:
    if version > MAX_AUDIT_EVENTS:
        raise AdministrationAuditCapacityError
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
