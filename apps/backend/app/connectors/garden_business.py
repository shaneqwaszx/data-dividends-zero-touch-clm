"""Bounded synthetic Garden Business and SIM LIM per-issuer Mock ownership fixtures.

Each issuer has its own synthetic `coShareholdersDetails`-shaped direct shareholder
record. Garden's record names SIM LIM only as a direct corporate owner; SIM LIM's own
holders exist only in SIM LIM's record. The D-046 equal-unit derivation applies only to
these two exact fixtures and never defines a generic ACRA share-count rule.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.connectors.acra import AcraOwnershipPartyPayload, AcraRelationshipPayload
from app.connectors.acra_bizfile_sandbox import BizfileMockOwnershipPartiesDecoder
from app.domain.jurisdiction import is_eligible_singapore_uen

GARDEN_BUSINESS_UEN = "11111999A"
SIM_LIM_UEN = "111111111M"
GARDEN_BUSINESS_NAME = "GARDEN BUSINESS"
GARDEN_BUSINESS_ADDRESS = ("GARDEN WALK", "018919", "#01-01")
SIM_LIM_NAME = "SIM LIM PTE. LTD."
SIM_LIM_ADDRESS = ("SYNTHETIC HOLDINGS ROAD", "049010", "#03-01")

_SIX_DECIMAL_PLACES = Decimal("0.000001")
_SYNTHETIC_ENDPOINT = "https://mock.acra.gov.sg/api/entities/{uen}/shareholders"
# The strict decoder requires an aware time; this value is never retained as evidence.
_FIXTURE_DECODE_TIME = datetime(2018, 3, 10, tzinfo=UTC)

# Owner-supplied synthetic Mock body (Master Assignment v4, section 1A). The corporate
# SIM LIM row is nested under `individual`; classification uses `shareholderCategory`.
GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY: dict[str, Any] = {
    "entities": [
        {
            "uen": GARDEN_BUSINESS_UEN,
            "name": "GARDEN BUSINESS",
            "shareholders": {
                "individual": [
                    {
                        "shareholderCategory": "Corporate",
                        "shareholderId": SIM_LIM_UEN,
                        "shareholderName": "SIM LIM PTE. LTD.",
                        "shareAllotted": 5000,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2018-03-10",
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S9988776F",
                        "shareholderName": "LIM CHOON HUAT",
                        "shareAllotted": 3000,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2018-03-10",
                        "status": "Active",
                    },
                ],
                "grouping": [],
            },
        }
    ]
}

# SIM LIM's own independent synthetic record, retaining the approved D-046 counts.
SIM_LIM_MOCK_SHAREHOLDERS_BODY: dict[str, Any] = {
    "entities": [
        {
            "uen": SIM_LIM_UEN,
            "name": SIM_LIM_NAME,
            "shareholders": {
                "individual": [
                    {
                        "shareholderCategory": "Corporate",
                        "shareholderId": "T16UF3333A",
                        "shareholderName": "FORMER OWNER",
                        "shareAllotted": 10000,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2016-05-20",
                        "status": "Withdrawn",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S123AC1234E",
                        "shareholderName": "ABCD123",
                        "shareAllotted": 900,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2016-05-20",
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S2222222E",
                        "shareholderName": "TAN WEI LING",
                        "shareAllotted": 100,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2016-05-20",
                        "status": "Active",
                    },
                    {
                        "shareholderCategory": "Individual",
                        "shareholderId": "S23BT2997U",
                        "shareholderName": "EFGH2345",
                        "shareAllotted": 100,
                        "shareType": "Ordinary",
                        "currency": "SINGAPORE DOLLAR",
                        "appointmentDate": "2016-05-20",
                        "status": "Active",
                    },
                ],
                "grouping": [],
            },
        }
    ]
}

_ISSUER_BODIES: Mapping[str, Mapping[str, Any]] = {
    GARDEN_BUSINESS_UEN: GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY,
    SIM_LIM_UEN: SIM_LIM_MOCK_SHAREHOLDERS_BODY,
}
_ISSUER_RELATIONSHIP_PREFIX: Mapping[str, str] = {
    GARDEN_BUSINESS_UEN: "REL_GARDEN_DIRECT",
    SIM_LIM_UEN: "REL_SIM_LIM_DIRECT",
}

_FixtureId = Annotated[
    str, StringConstraints(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
]
_FixtureName = Annotated[str, StringConstraints(min_length=1, max_length=160)]


class SyntheticShareholderRow(BaseModel):
    """One strict synthetic direct-holder row; never an official ACRA schema claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    shareholder_category: Literal["Corporate", "Individual"] = Field(alias="shareholderCategory")
    shareholder_id: _FixtureId = Field(alias="shareholderId")
    shareholder_name: _FixtureName = Field(alias="shareholderName")
    share_allotted: Decimal = Field(
        alias="shareAllotted", gt=Decimal("0"), max_digits=18, decimal_places=6
    )
    # One explicit share class keeps every active unit economically comparable.
    share_type: Literal["Ordinary"] = Field(alias="shareType")
    currency: Literal["SINGAPORE DOLLAR"]
    appointment_date: date = Field(alias="appointmentDate")
    status: Literal["Active", "Withdrawn"]

    @field_validator("share_allotted", mode="before")
    @classmethod
    def reject_binary_float_share_counts(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("shareAllotted must use exact Decimal-compatible input")
        return value


class _SyntheticShareholders(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    individual: tuple[SyntheticShareholderRow, ...] = Field(min_length=1, max_length=64)
    # Grouping semantics are unconfirmed; the fixture never flattens a group.
    grouping: tuple[()] = ()


class _SyntheticIssuer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    uen: _FixtureId
    name: _FixtureName
    shareholders: _SyntheticShareholders


class _SyntheticEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entities: tuple[_SyntheticIssuer]


def synthetic_issuer_shareholders(
    body: Mapping[str, Any], *, requested_uen: str
) -> tuple[SyntheticShareholderRow, ...]:
    """Validate one issuer body through the existing strict decoder plus fixture rules.

    The existing official-Mock-compatible decoder classifies each row by its validated
    `shareholderCategory`, not by the `individual` container name, and binds the echoed
    issuer UEN. The stricter fixture model then requires one share class and an explicit
    Active/Withdrawn status before any D-046 derivation.
    """

    normalized = requested_uen.strip().upper()
    decoded = BizfileMockOwnershipPartiesDecoder(include_withdrawn=True).decode(
        body,
        requested_uen=normalized,
        source_endpoint=_SYNTHETIC_ENDPOINT.format(uen=normalized),
        retrieved_at=_FIXTURE_DECODE_TIME,
    )
    issuer = _SyntheticEnvelope.model_validate(body).entities[0]
    if issuer.uen.strip().upper() != normalized:
        raise ValueError("synthetic issuer record does not match the requested UEN")
    rows = issuer.shareholders.individual
    expected = tuple(
        (row.shareholder_id, "LEGAL_ENTITY" if row.shareholder_category == "Corporate"
         else "NATURAL_PERSON")
        for row in rows
    )
    if tuple((item.party_id, item.party_type) for item in decoded.ownership_parties) != expected:
        raise ValueError("synthetic issuer rows disagree with the strict Mock decoder")
    return rows


def derive_issuer_direct_ownership(
    uen: str,
) -> tuple[tuple[AcraOwnershipPartyPayload, ...], tuple[AcraRelationshipPayload, ...]] | None:
    """Return one known synthetic issuer's own direct holders, or None when unknown."""

    normalized = uen.strip().upper()
    body = _ISSUER_BODIES.get(normalized)
    if body is None:
        return None
    rows = synthetic_issuer_shareholders(body, requested_uen=normalized)
    active = tuple(row for row in rows if row.status == "Active")
    if not active:
        raise ValueError("synthetic issuer requires at least one active shareholder")
    identifiers = [row.shareholder_id.strip().upper() for row in rows]
    if len(set(identifiers)) != len(identifiers) or normalized in identifiers:
        raise ValueError("synthetic issuer holder identifiers must be unique and external")
    total = sum((row.share_allotted for row in active), Decimal("0"))
    parties: list[AcraOwnershipPartyPayload] = []
    relationships: list[AcraRelationshipPayload] = []
    for index, row in enumerate(active, start=1):
        percentage = _quantized_share(row.share_allotted, total)
        corporate = row.shareholder_category == "Corporate"
        registration = row.shareholder_id.strip().upper() if corporate else None
        if registration is not None and not is_eligible_singapore_uen(registration):
            raise ValueError("synthetic corporate holder requires a verified Singapore UEN")
        parties.append(
            AcraOwnershipPartyPayload(
                party_id=row.shareholder_id,
                party_type="LEGAL_ENTITY" if corporate else "NATURAL_PERSON",
                name=row.shareholder_name,
                registration_identifier=registration,
                country="SG",
                ownership_percentage=percentage,
            )
        )
        relationships.append(
            AcraRelationshipPayload(
                relationship_id=f"{_ISSUER_RELATIONSHIP_PREFIX[normalized]}_{index}",
                owned_entity_id=f"ENTITY_{normalized}",
                owner_party_id=row.shareholder_id,
                ownership_percentage=percentage,
            )
        )
    return tuple(parties), tuple(relationships)


class GardenShareholderFixture(BaseModel):
    """Strict local share-count evidence used only by the official-Mock supplement."""

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


def _supplement_rows(body: Mapping[str, Any], uen: str) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "party_id": row.shareholder_id,
            "name": row.shareholder_name,
            "category": row.shareholder_category,
            "shareAllotted": row.share_allotted,
            "status": row.status,
        }
        for row in synthetic_issuer_shareholders(body, requested_uen=uen)
    )


# Flattened views of the same per-issuer bodies, retained only for the official
# Marketplace Mock lane's separately labelled LOCAL_SYNTHETIC_SUPPLEMENT.
GARDEN_DIRECT_SHAREHOLDERS: tuple[dict[str, object], ...] = _supplement_rows(
    GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY, GARDEN_BUSINESS_UEN
)
SIM_LIM_DIRECT_SHAREHOLDERS: tuple[dict[str, object], ...] = _supplement_rows(
    SIM_LIM_MOCK_SHAREHOLDERS_BODY, SIM_LIM_UEN
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
    """Derive the flattened supplement graph; never served by the local Mock registry."""

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


def _quantized_share(units: Decimal, total: Decimal) -> Decimal:
    if total <= 0:
        raise ValueError("synthetic issuer active share total must be positive")
    return (units * Decimal("100") / total).quantize(_SIX_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def quantized_unit_share(units: Decimal, total: Decimal) -> Decimal:
    """The same six-decimal equal-unit rule, for explicitly whitelisted fixtures only."""
    return _quantized_share(units, total)


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
    return tuple(_quantized_share(holder.share_allotted, total) for holder in shareholders)


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
