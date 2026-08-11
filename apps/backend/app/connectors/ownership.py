"""Replaceable ownership provider boundary and strict provider result contract."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.ownership import (
    OwnershipEnvironment,
    OwnershipRelationship,
    Party,
    SafePartyId,
    SafeProviderName,
)


@dataclass(frozen=True)
class OwnershipProviderRequest:
    """Provider-neutral case/root identity with no demo scenario or target DTO."""

    case_id: UUID
    registration_number: str
    display_name: str


class OwnershipProviderMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    provider_name: SafeProviderName
    environment: OwnershipEnvironment


class OwnershipSourceResult(BaseModel):
    """Validated provider graph; service-configured safety limits are applied later."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    root_party_id: SafePartyId
    parties: list[Party] = Field(min_length=1, max_length=1000)
    relationships: list[OwnershipRelationship] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def validate_graph_references(self) -> "OwnershipSourceResult":
        party_ids = [party.party_id for party in self.parties]
        if len(party_ids) != len(set(party_ids)):
            raise ValueError("party IDs must be unique")
        relationship_ids = [item.relationship_id for item in self.relationships]
        if len(relationship_ids) != len(set(relationship_ids)):
            raise ValueError("relationship IDs must be unique")
        known = set(party_ids)
        if self.root_party_id not in known:
            raise ValueError("root party must exist")
        root = next(party for party in self.parties if party.party_id == self.root_party_id)
        if root.party_type.value != "LEGAL_ENTITY":
            raise ValueError("root party must be a legal entity")
        for item in self.relationships:
            if item.parent_party_id not in known or item.child_party_id not in known:
                raise ValueError("relationship endpoints must exist")
            if item.parent_party_id == item.child_party_id:
                raise ValueError("self-ownership is invalid")
        return self


class OwnershipProvider(Protocol):
    @property
    def metadata(self) -> object: ...

    def load(self, request: OwnershipProviderRequest) -> object: ...


class OwnershipProviderError(Exception):
    """Controlled provider failure whose internal context is never projected."""
