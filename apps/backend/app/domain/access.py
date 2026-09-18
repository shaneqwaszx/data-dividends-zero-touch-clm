"""Backend-owned identity, dynamic team ID, role, and capability contracts."""

import re
from enum import StrEnum
from typing import Annotated, Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import core_schema

TEAM_ID_PATTERN = re.compile(r"^(?:TEAM_A|TEAM_B|TEAM_[A-F0-9]{24})$")


class TeamId(str):
    """Canonical persisted team identifier with legacy seed constants."""

    TEAM_A: ClassVar["TeamId"]
    TEAM_B: ClassVar["TeamId"]

    def __new__(cls, value: str) -> "TeamId":
        if not isinstance(value, str) or not TEAM_ID_PATTERN.fullmatch(value):
            raise ValueError("invalid team ID")
        return str.__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        del source_type, handler
        return core_schema.no_info_after_validator_function(
            cls, core_schema.str_schema(strict=True)
        )


TeamId.TEAM_A = TeamId("TEAM_A")
TeamId.TEAM_B = TeamId("TEAM_B")


class Role(StrEnum):
    CLIENT_ONBOARDER = "CLIENT_ONBOARDER"
    RELATIONSHIP_MANAGER = "RELATIONSHIP_MANAGER"
    DIRECTOR = "DIRECTOR"
    HR = "HR"


class Capability(StrEnum):
    POLICY_VIEW = "POLICY_VIEW"
    POLICY_MUTATE = "POLICY_MUTATE"
    CASE_ACCESS = "CASE_ACCESS"
    CASE_GLOBAL = "CASE_GLOBAL"
    IDENTITY_ADMIN = "IDENTITY_ADMIN"
    TEAM_ADMIN = "TEAM_ADMIN"


ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.CLIENT_ONBOARDER: frozenset({Capability.POLICY_VIEW, Capability.CASE_ACCESS}),
    Role.RELATIONSHIP_MANAGER: frozenset(
        {Capability.POLICY_VIEW, Capability.POLICY_MUTATE, Capability.CASE_ACCESS}
    ),
    Role.DIRECTOR: frozenset(
        {
            Capability.POLICY_VIEW,
            Capability.POLICY_MUTATE,
            Capability.CASE_ACCESS,
            Capability.CASE_GLOBAL,
        }
    ),
    Role.HR: frozenset({Capability.POLICY_VIEW, Capability.IDENTITY_ADMIN, Capability.TEAM_ADMIN}),
}


def has_capability(role: Role, capability: Capability) -> bool:
    return capability in ROLE_CAPABILITIES[role]


CasePriority = Annotated[int, Field(strict=True, ge=1, le=10)]


class Team(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    display_name: str
    team_type: str
    client_scope_label: str

    @property
    def description(self) -> str:
        return f"Type: {self.team_type} | Client coverage: {self.client_scope_label}"


TEAMS: tuple[Team, ...] = (
    Team(
        team_id=TeamId.TEAM_A,
        display_name="Alpha",
        team_type="Corporate Client Onboarding",
        client_scope_label="Alpha",
    ),
    Team(
        team_id=TeamId.TEAM_B,
        display_name="Beta",
        team_type="Corporate Client Onboarding",
        client_scope_label="Beta",
    ),
)
TEAM_BY_ID = {team.team_id: team for team in TEAMS}


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    display_name: str
    role: Role
    team_id: TeamId | None

    @model_validator(mode="after")
    def validate_role_team(self) -> "UserProfile":
        if self.role in {Role.DIRECTOR, Role.HR} and self.team_id is not None:
            raise ValueError("global profile must not have a team")
        if self.role in {Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER} and self.team_id is None:
            raise ValueError("case profile requires a team")
        return self

    @property
    def team_display_name(self) -> str | None:
        return TEAM_BY_ID[self.team_id].display_name if self.team_id is not None else None

    @property
    def client_scope_label(self) -> str:
        return (
            TEAM_BY_ID[self.team_id].client_scope_label
            if self.team_id is not None
            else ("Administration only" if self.role == Role.HR else "Global / cross-team")
        )

    @property
    def team_type(self) -> str | None:
        return TEAM_BY_ID[self.team_id].team_type if self.team_id is not None else None

    @property
    def team_description(self) -> str:
        return (
            TEAM_BY_ID[self.team_id].description
            if self.team_id is not None
            else (
                "Administration only; no client-case access"
                if self.role == Role.HR
                else "Global / cross-team access"
            )
        )


class AuthenticatedActor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: UserProfile


SYNTHETIC_USER_PROFILES: tuple[UserProfile, ...] = (
    UserProfile(
        user_id="maya-lim",
        display_name="Maya Lim",
        role=Role.CLIENT_ONBOARDER,
        team_id=TeamId.TEAM_A,
    ),
    UserProfile(
        user_id="ethan-tan",
        display_name="Ethan Tan",
        role=Role.RELATIONSHIP_MANAGER,
        team_id=TeamId.TEAM_A,
    ),
    UserProfile(
        user_id="sophia-ng",
        display_name="Sophia Ng",
        role=Role.CLIENT_ONBOARDER,
        team_id=TeamId.TEAM_B,
    ),
    UserProfile(
        user_id="ryan-lee",
        display_name="Ryan Lee",
        role=Role.RELATIONSHIP_MANAGER,
        team_id=TeamId.TEAM_B,
    ),
    UserProfile(
        user_id="olivia-koh",
        display_name="Olivia Koh",
        role=Role.DIRECTOR,
        team_id=None,
    ),
)
SYNTHETIC_PROFILE_BY_ID = {profile.user_id: profile for profile in SYNTHETIC_USER_PROFILES}
