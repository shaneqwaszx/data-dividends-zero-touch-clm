"""Typed Phase 13 POC identity, team, and role contracts."""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeamId(StrEnum):
    TEAM_A = "TEAM_A"
    TEAM_B = "TEAM_B"


class Role(StrEnum):
    CLIENT_ONBOARDER = "CLIENT_ONBOARDER"
    RELATIONSHIP_MANAGER = "RELATIONSHIP_MANAGER"
    DIRECTOR = "DIRECTOR"


CasePriority = Annotated[int, Field(strict=True, ge=1, le=10)]


class Team(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    team_id: TeamId
    display_name: str
    client_scope_label: str


TEAMS: tuple[Team, ...] = (
    Team(team_id=TeamId.TEAM_A, display_name="Team A", client_scope_label="DBS"),
    Team(team_id=TeamId.TEAM_B, display_name="Team B", client_scope_label="OCBC"),
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
        if self.role == Role.DIRECTOR and self.team_id is not None:
            raise ValueError("director profile must not have a team")
        if self.role != Role.DIRECTOR and self.team_id is None:
            raise ValueError("team-scoped profile requires a team")
        return self

    @property
    def team_display_name(self) -> str | None:
        return TEAM_BY_ID[self.team_id].display_name if self.team_id is not None else None

    @property
    def client_scope_label(self) -> str:
        return (
            TEAM_BY_ID[self.team_id].client_scope_label
            if self.team_id is not None
            else "All demo scopes"
        )


class AuthenticatedActor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: UserProfile


SYNTHETIC_USER_PROFILES: tuple[UserProfile, ...] = (
    UserProfile(
        user_id="team-a-onboarder",
        display_name="Team A Client Onboarder",
        role=Role.CLIENT_ONBOARDER,
        team_id=TeamId.TEAM_A,
    ),
    UserProfile(
        user_id="team-a-rm",
        display_name="Team A Relationship Manager",
        role=Role.RELATIONSHIP_MANAGER,
        team_id=TeamId.TEAM_A,
    ),
    UserProfile(
        user_id="team-b-onboarder",
        display_name="Team B Client Onboarder",
        role=Role.CLIENT_ONBOARDER,
        team_id=TeamId.TEAM_B,
    ),
    UserProfile(
        user_id="team-b-rm",
        display_name="Team B Relationship Manager",
        role=Role.RELATIONSHIP_MANAGER,
        team_id=TeamId.TEAM_B,
    ),
    UserProfile(
        user_id="director",
        display_name="POC Director",
        role=Role.DIRECTOR,
        team_id=None,
    ),
)
SYNTHETIC_PROFILE_BY_ID = {
    profile.user_id: profile for profile in SYNTHETIC_USER_PROFILES
}
