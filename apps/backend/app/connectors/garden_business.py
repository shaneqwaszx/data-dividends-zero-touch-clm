"""Bounded synthetic Garden Business ownership fixture for the Mock ACRA provider."""

from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.connectors.acra import AcraOwnershipPartyPayload, AcraRelationshipPayload

GARDEN_BUSINESS_UEN = "11111999A"
SIM_LIM_UEN = "111111111M"
GARDEN_BUSINESS_NAME = "GARDEN BUSINESS"
GARDEN_BUSINESS_ADDRESS = ("GARDEN WALK", "018919", "#01-01")

_SIX_DECIMAL_PLACES = Decimal("0.000001")


class GardenShareholderFixture(BaseModel):
    """Strict local share-count evidence used only by the Garden synthetic chain."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )

    party_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    name: str = Field(min_length=1, max_length=160)
    category: Literal["Corporate", "Individual"]
    share_allotted: Decimal = Field(
        alias="shareAllotted",
        gt=Decimal("0"),
        max_digits=18,
        decimal_places=6,
    )
    status: Literal["Active", "Withdrawn"]

    @field_validator("share_allotted", mode="before")
    @classmethod
    def reject_binary_float_share_counts(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("shareAllotted must use exact Decimal-compatible input")
        return value


GARDEN_DIRECT_SHAREHOLDERS: tuple[dict[str, object], ...] = (
    {
        "party_id": SIM_LIM_UEN,
        "name": "SIM LIM PTE. LTD.",
        "category": "Corporate",
        "shareAllotted": 5000,
        "status": "Active",
    },
    {
        "party_id": "S9988776F",
        "name": "LIM CHOON HUAT",
        "category": "Individual",
        "shareAllotted": 3000,
        "status": "Active",
    },
)

SIM_LIM_DIRECT_SHAREHOLDERS: tuple[dict[str, object], ...] = (
    {
        "party_id": "T16UF3333A",
        "name": "FORMER OWNER",
        "category": "Corporate",
        "shareAllotted": 10000,
        "status": "Withdrawn",
    },
    {
        "party_id": "S123AC1234E",
        "name": "ABCD123",
        "category": "Individual",
        "shareAllotted": 900,
        "status": "Active",
    },
    {
        "party_id": "S2222222E",
        "name": "TAN WEI LING",
        "category": "Individual",
        "shareAllotted": 100,
        "status": "Active",
    },
    {
        "party_id": "S23BT2997U",
        "name": "EFGH2345",
        "category": "Individual",
        "shareAllotted": 100,
        "status": "Active",
    },
)


def derive_garden_ownership(
    *,
    garden_shareholders: Sequence[Mapping[str, object] | GardenShareholderFixture] = (
        GARDEN_DIRECT_SHAREHOLDERS
    ),
    sim_lim_shareholders: Sequence[Mapping[str, object] | GardenShareholderFixture] = (
        SIM_LIM_DIRECT_SHAREHOLDERS
    ),
) -> tuple[tuple[AcraOwnershipPartyPayload, ...], tuple[AcraRelationshipPayload, ...]]:
    """Derive the exact bounded Garden graph without creating a generic ACRA rule."""

    garden = _active_shareholders(garden_shareholders)
    sim_lim = _active_shareholders(sim_lim_shareholders)
    sim_lim_owner = tuple(holder for holder in garden if holder.party_id == SIM_LIM_UEN)
    if len(sim_lim_owner) != 1 or sim_lim_owner[0].category != "Corporate":
        raise ValueError("Garden fixture must contain the expected SIM LIM corporate owner")

    all_party_ids = [holder.party_id for holder in (*garden, *sim_lim)]
    if len(set(all_party_ids)) != len(all_party_ids):
        raise ValueError("Garden fixture party identifiers must be unique")

    garden_percentages = _percentages(garden)
    sim_lim_percentages = _percentages(sim_lim)
    parties = tuple(
        _party(holder, percentage)
        for holder, percentage in (
            *zip(garden, garden_percentages, strict=True),
            *zip(sim_lim, sim_lim_percentages, strict=True),
        )
    )
    relationships = tuple(
        _relationship(
            relationship_id=f"REL_GARDEN_DIRECT_{index}",
            parent_party_id=f"ENTITY_{GARDEN_BUSINESS_UEN}",
            holder=holder,
            percentage=percentage,
        )
        for index, (holder, percentage) in enumerate(
            zip(garden, garden_percentages, strict=True), start=1
        )
    ) + tuple(
        _relationship(
            relationship_id=f"REL_SIM_LIM_DIRECT_{index}",
            parent_party_id=SIM_LIM_UEN,
            holder=holder,
            percentage=percentage,
        )
        for index, (holder, percentage) in enumerate(
            zip(sim_lim, sim_lim_percentages, strict=True), start=1
        )
    )
    return parties, relationships


def _active_shareholders(
    values: Sequence[Mapping[str, object] | GardenShareholderFixture],
) -> tuple[GardenShareholderFixture, ...]:
    validated = tuple(
        item
        if isinstance(item, GardenShareholderFixture)
        else GardenShareholderFixture.model_validate(item)
        for item in values
    )
    active = tuple(item for item in validated if item.status == "Active")
    if not active:
        raise ValueError("Garden fixture requires at least one active shareholder")
    return active


def _percentages(
    shareholders: tuple[GardenShareholderFixture, ...],
) -> tuple[Decimal, ...]:
    total = sum((holder.share_allotted for holder in shareholders), Decimal("0"))
    if total <= 0:
        raise ValueError("Garden fixture active share total must be positive")
    return tuple(
        (holder.share_allotted * Decimal("100") / total).quantize(
            _SIX_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )
        for holder in shareholders
    )


def _party(
    holder: GardenShareholderFixture,
    percentage: Decimal,
) -> AcraOwnershipPartyPayload:
    is_corporate = holder.category == "Corporate"
    return AcraOwnershipPartyPayload(
        party_id=holder.party_id,
        party_type="LEGAL_ENTITY" if is_corporate else "NATURAL_PERSON",
        name=holder.name,
        registration_identifier=holder.party_id if is_corporate else None,
        country="SG",
        ownership_percentage=percentage,
    )


def _relationship(
    *,
    relationship_id: str,
    parent_party_id: str,
    holder: GardenShareholderFixture,
    percentage: Decimal,
) -> AcraRelationshipPayload:
    return AcraRelationshipPayload(
        relationship_id=relationship_id,
        owned_entity_id=parent_party_id,
        owner_party_id=holder.party_id,
        ownership_percentage=percentage,
    )
