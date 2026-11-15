"""Strict global administration records with bounded audit metadata."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.domain.access import Role, TeamId

TEAM_TYPE = "Corporate Client Onboarding"
USER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,31}$")
MAX_AUDIT_EVENTS = 256

SafeAuditScalar = str | int | bool | None


class AdministrationAuditEvent(BaseModel):
    """Append-only evidence whose metadata is deliberately secret-incapable."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: Annotated[str, Field(pattern=r"^[A-F0-9]{24}$")]
    action: Literal[
        "TEAM_CREATED",
        "TEAM_UPDATED",
        "PROFILE_CREATED",
        "PROFILE_UPDATED",
        "PROFILE_AUTHORITY_UPDATED",
    ]
    actor_user_id: Annotated[str, Field(min_length=3, max_length=32)]
    target_id: Annotated[str, Field(min_length=3, max_length=64)]
    timestamp: datetime
    resulting_version: Annotated[int, Field(ge=1)]
    metadata: Annotated[dict[str, SafeAuditScalar], Field(max_length=16)] = Field(
        default_factory=dict
    )

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, SafeAuditScalar]) -> dict[str, SafeAuditScalar]:
        forbidden = {"password", "credential", "hash", "session", "csrf", "secret", "uri"}
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 48:
                raise ValueError("audit metadata key is invalid")
            lowered = key.casefold()
            if any(marker in lowered for marker in forbidden):
                raise ValueError("audit metadata key is not permitted")
            if isinstance(item, str) and len(item) > 160:
                raise ValueError("audit metadata value is too long")
        return value


class TeamRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    display_name: Annotated[str, Field(min_length=2, max_length=80)]
    normalized_display_name: Annotated[str, Field(min_length=2, max_length=160)]
    team_type: Literal["Corporate Client Onboarding"] = "Corporate Client Onboarding"
    client_scope_label: Annotated[str, Field(min_length=2, max_length=80)]
    normalized_client_scope_label: Annotated[str, Field(min_length=2, max_length=160)]
    description: Annotated[str | None, Field(default=None, max_length=240)]
    active: Literal[True] = True
    version: Annotated[int, Field(ge=1)]
    created_at: datetime
    updated_at: datetime
    created_by: Annotated[str, Field(min_length=3, max_length=32)]
    updated_by: Annotated[str, Field(min_length=3, max_length=32)]
    audit_events: Annotated[tuple[AdministrationAuditEvent, ...], Field(max_length=256)] = ()

    @model_validator(mode="after")
    def validate_derived_name(self) -> TeamRecord:
        if normalize_display_name(self.display_name) != self.normalized_display_name:
            raise ValueError("normalized team name does not match display name")
        if normalize_display_name(self.client_scope_label) != self.normalized_client_scope_label:
            raise ValueError("normalized client scope label does not match client scope label")
        if self.updated_at < self.created_at:
            raise ValueError("team update time precedes creation time")
        validate_audit_chain(self.audit_events, self.team_id, self.version)
        return self

    @property
    def presentation_description(self) -> str:
        return self.description or (
            f"Type: {self.team_type} | Client coverage: {self.client_scope_label}"
        )


class UserAccountRecord(BaseModel):
    """Internal account owner. The credential field is never an API response field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{2,31}$")]
    display_name: Annotated[str, Field(min_length=2, max_length=80)]
    role: Role
    team_id: TeamId | None
    credential_hash: SecretStr = Field(repr=False)
    security_version: Annotated[int, Field(ge=1)]
    version: Annotated[int, Field(ge=1)]
    created_at: datetime
    updated_at: datetime
    created_by: Annotated[str, Field(min_length=3, max_length=32)]
    updated_by: Annotated[str, Field(min_length=3, max_length=32)]
    audit_events: Annotated[tuple[AdministrationAuditEvent, ...], Field(max_length=256)] = ()

    @model_validator(mode="after")
    def validate_account(self) -> UserAccountRecord:
        if self.role in {Role.DIRECTOR, Role.HR, Role.SUPPORT} and self.team_id is not None:
            raise ValueError("global administration roles must not have a team")
        if self.role in {Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER} and self.team_id is None:
            raise ValueError("case roles require a team")
        if self.updated_at < self.created_at:
            raise ValueError("account update time precedes creation time")
        validate_audit_chain(self.audit_events, self.user_id, self.version)
        return self


def normalize_display_name(value: str) -> str:
    """Return the uniqueness key used identically by memory and Mongo owners."""

    normalized = " ".join(unicodedata.normalize("NFKC", value).strip().split()).casefold()
    if len(normalized) < 2 or len(normalized) > 160:
        raise ValueError("normalized display name is invalid")
    return normalized


def normalize_user_id(value: str) -> str:
    normalized = value.strip().casefold()
    if not USER_ID_PATTERN.fullmatch(normalized) or normalized != value:
        raise ValueError("user ID is invalid")
    return normalized


def validate_audit_chain(
    events: tuple[AdministrationAuditEvent, ...], target_id: str, version: int
) -> None:
    if len(events) > MAX_AUDIT_EVENTS:
        raise ValueError("audit capacity exceeded")
    previous_version = 0
    seen: set[str] = set()
    for event in events:
        if event.target_id != str(target_id) or event.event_id in seen:
            raise ValueError("audit event identity is invalid")
        if event.resulting_version <= previous_version or event.resulting_version > version:
            raise ValueError("audit event version order is invalid")
        seen.add(event.event_id)
        previous_version = event.resulting_version
    if events and events[-1].resulting_version != version:
        raise ValueError("audit does not describe the current version")


def audit_is_prefix(
    previous: tuple[AdministrationAuditEvent, ...],
    candidate: tuple[AdministrationAuditEvent, ...],
) -> bool:
    return len(candidate) == len(previous) + 1 and candidate[: len(previous)] == previous


# D-140: credential operations are recorded as PROFILE_UPDATED events tagged by
# ``metadata["operation"]``. No new audit action or persisted field is introduced, so a
# rollback to an image without D-140 still decodes every profile.
CREDENTIAL_OPERATION_KEY = "operation"
PASSWORD_RESET_OPERATION: Final = "PASSWORD_RESET"
SIGN_IN_DISABLED_OPERATION: Final = "SIGN_IN_DISABLED"
CredentialOperation = Literal["PASSWORD_RESET", "SIGN_IN_DISABLED"]


def sign_in_disabled(record: UserAccountRecord) -> bool:
    """True when the latest credential operation discarded the credential (SF-006)."""

    for event in reversed(record.audit_events):
        operation = event.metadata.get(CREDENTIAL_OPERATION_KEY)
        if event.action == "PROFILE_UPDATED" and operation in {
            PASSWORD_RESET_OPERATION,
            SIGN_IN_DISABLED_OPERATION,
        }:
            return operation == SIGN_IN_DISABLED_OPERATION
    return False
