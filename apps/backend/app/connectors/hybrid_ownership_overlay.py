"""Explicitly whitelisted local direct-holder overlays for hybrid demonstration cases.

The official ACRA API Marketplace Mock supplies entity identity. It has no relationship
operation and no authorized share denominator, so a named non-production scenario may
declare each issuer's *direct* holders here as LOCAL_SYNTHETIC_RELATIONSHIP evidence.
This is never an ACRA response, never a provider fallback and never applied to an
issuer outside its own scenario catalogue (D-077). Percentages use the existing D-046
six-decimal equal-unit rule over a locally declared complete same-class denominator;
paths and classification stay in the single ownership engine.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    ACRA_API_MARKETPLACE_MOCK_ENTITY_PATH,
)
from app.connectors.garden_business import (
    GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY,
    GARDEN_BUSINESS_NAME,
    GARDEN_BUSINESS_UEN,
    quantized_unit_share,
    synthetic_issuer_shareholders,
)
from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import (
    OnboardingCase,
    RegistryAcquisitionStatus,
    RegistryOperationStatus,
    SourceEnvironment,
)
from app.domain.ownership import (
    OwnershipEnvironment,
    OwnershipProvenance,
    OwnershipRelationship,
    Party,
    PartyType,
)
from app.domain.ownership_evidence import OwnershipEvidence, OwnershipEvidenceKind

OVERLAY_RELATIONSHIP_PROVIDER = "LOCAL_SYNTHETIC_RELATIONSHIP"
OVERLAY_SOURCE_OPERATION = "LOCAL_HYBRID_OVERLAY"
OFFICIAL_MARKETPLACE_PROFILE_REFERENCE = (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL + ACRA_API_MARKETPLACE_MOCK_ENTITY_PATH
)
GARDEN_DIRECT_OVERLAY_SCENARIO_ID = "GARDEN_DIRECT_OVERLAY_V1"
FIVE_LAYER_SCENARIO_ID = "FIVE_LAYER_MARKETPLACE_HYBRID_V1"
FIVE_LAYER_ROOT_UEN = "201511222D"

_ScenarioId = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9_]{0,47}$")]
_HolderId = Annotated[
    str, StringConstraints(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
]
_Name = Annotated[str, StringConstraints(min_length=1, max_length=160)]


class OverlayHolder(BaseModel):
    """One declared direct holder row; never an official ACRA schema claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    holder_id: _HolderId
    holder_name: _Name
    category: Literal["Corporate", "Individual"]
    registration_number: str | None = None
    share_units: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    share_class: Literal["ORDINARY"] = "ORDINARY"
    status: Literal["Active", "Withdrawn"] = "Active"

    @field_validator("share_units", mode="before")
    @classmethod
    def exact_units(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("overlay share units must use exact Decimal-compatible input")
        return value

    @model_validator(mode="after")
    def corporate_identity(self) -> OverlayHolder:
        corporate = self.category == "Corporate"
        if corporate != (self.registration_number is not None):
            raise ValueError("only corporate overlay holders carry a registration number")
        if self.registration_number is not None and (
            self.registration_number != self.holder_id
            or not is_eligible_singapore_uen(self.registration_number)
        ):
            raise ValueError("corporate overlay holders require their verified-format UEN")
        return self


class OverlayIssuer(BaseModel):
    """One issuer's complete declared same-class register for the scenario."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer_uen: _HolderId
    local_display_name: _Name
    declared_active_units: Decimal = Field(gt=Decimal("0"), max_digits=18, decimal_places=6)
    denominator_basis: Literal["LOCAL_DECLARED_COMPLETE_SAME_CLASS"] = (
        "LOCAL_DECLARED_COMPLETE_SAME_CLASS"
    )
    holders: tuple[OverlayHolder, ...] = Field(min_length=1, max_length=32)

    @field_validator("declared_active_units", mode="before")
    @classmethod
    def exact_denominator(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("overlay denominators must use exact Decimal-compatible input")
        return value

    @model_validator(mode="after")
    def complete_register(self) -> OverlayIssuer:
        if not is_eligible_singapore_uen(self.issuer_uen):
            raise ValueError("overlay issuers require a verified-format Singapore UEN")
        identifiers = [item.holder_id.upper() for item in self.holders]
        if len(set(identifiers)) != len(identifiers) or self.issuer_uen in identifiers:
            raise ValueError("overlay holder identifiers must be unique and external")
        active = [item for item in self.holders if item.status == "Active"]
        if not active:
            raise ValueError("an overlay issuer requires at least one active holder")
        # The declared denominator must be exactly the complete active same-class total;
        # an arbitrary numerator set never becomes a denominator.
        if sum((item.share_units for item in active), Decimal("0")) != self.declared_active_units:
            raise ValueError("declared overlay denominator disagrees with active holdings")
        return self


class HybridOverlayScenario(BaseModel):
    """A named, whitelisted non-production scenario rooted at one official issuer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_id: _ScenarioId
    root_uen: _HolderId
    issuers: tuple[OverlayIssuer, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def bounded_catalogue(self) -> HybridOverlayScenario:
        uens = [item.issuer_uen for item in self.issuers]
        if len(set(uens)) != len(uens) or self.root_uen not in uens:
            raise ValueError("overlay scenarios require unique issuers including the root")
        return self

    def issuer(self, uen: str) -> OverlayIssuer | None:
        normalized = uen.strip().upper()
        return next((item for item in self.issuers if item.issuer_uen == normalized), None)


@dataclass(frozen=True)
class OverlayComponent:
    """One issuer's declared direct holders, normalized to the ownership vocabulary."""

    root_party_id: str
    parties: tuple[Party, ...]
    relationships: tuple[OwnershipRelationship, ...]
    share_evidence: tuple[OwnershipEvidence, ...]


def overlay_component(
    scenario: HybridOverlayScenario,
    issuer: OverlayIssuer,
    *,
    issuer_party: Party,
    sourced_at: datetime,
) -> OverlayComponent:
    """Normalize active declared holders; withdrawn rows never become edges."""

    parties = [issuer_party]
    relationships: list[OwnershipRelationship] = []
    shares: list[OwnershipEvidence] = []
    active = [item for item in issuer.holders if item.status == "Active"]
    for index, holder in enumerate(active, start=1):
        corporate = holder.category == "Corporate"
        percentage = quantized_unit_share(holder.share_units, issuer.declared_active_units)
        parties.append(
            Party(
                party_id=holder.holder_id,
                display_name=holder.holder_name,
                party_type=PartyType.LEGAL_ENTITY if corporate else PartyType.NATURAL_PERSON,
                registration_number=holder.registration_number,
                country="SG" if corporate else None,
            )
        )
        relationship_id = f"OVL_{issuer.issuer_uen}_{index}"
        relationships.append(
            OwnershipRelationship(
                relationship_id=relationship_id,
                parent_party_id=issuer_party.party_id,
                child_party_id=holder.holder_id,
                ownership_percent=percentage,
                provenance=OwnershipProvenance(
                    provider=OVERLAY_RELATIONSHIP_PROVIDER,
                    environment=OwnershipEnvironment.LOCAL,
                    source_reference=f"HYBRID_OVERLAY_{scenario.scenario_id}_{relationship_id}",
                    sourced_at=sourced_at,
                ),
            )
        )
        shares.append(
            OwnershipEvidence(
                evidence_id="e-"
                + sha256(f"{scenario.scenario_id}:{relationship_id}:UNITS".encode()).hexdigest()[
                    :48
                ],
                entity_identifier=issuer.issuer_uen,
                party_id=holder.holder_id,
                kind=OwnershipEvidenceKind.SHARE_UNITS,
                raw_value=format(holder.share_units, "f"),
                numeric_value=holder.share_units,
                source_operation=OVERLAY_SOURCE_OPERATION,
                provider=OVERLAY_RELATIONSHIP_PROVIDER,
                environment="LOCAL",
                retrieved_at=sourced_at,
                share_class="SYNTHETIC_" + holder.share_class,
                unit_type="SHARES",
                source_status="ACTIVE",
                evidence_version=1,
            )
        )
    return OverlayComponent(
        root_party_id=issuer_party.party_id,
        parties=tuple(parties),
        relationships=tuple(relationships),
        share_evidence=tuple(shares),
    )


def official_marketplace_root_is_eligible(case: OnboardingCase, uen: str, now: datetime) -> bool:
    """Exact UEN plus successful, fresh official Marketplace Mock entity evidence.

    Never a fallback: a missing, stale, failed, local-Mock or mismatched acquisition
    keeps the case on its ordinary single-source path.
    """

    acquisition = case.registry_acquisition
    if (
        acquisition is None
        or case.requested_uen != uen
        or acquisition.requested_identifier != uen
        or acquisition.entity_profile.registration_number.strip().upper() != uen
        or acquisition.status
        not in {RegistryAcquisitionStatus.COMPLETE, RegistryAcquisitionStatus.PARTIAL}
        or acquisition.entity_profile.source.environment != SourceEnvironment.MOCK
        or acquisition.entity_profile.source.registry_source_link
        != OFFICIAL_MARKETPLACE_PROFILE_REFERENCE
        or case.policy_snapshot.registry is None
        or acquisition.operation_results[0].status != RegistryOperationStatus.COMPLETE
        or any(
            item.status == RegistryOperationStatus.FAILED for item in acquisition.operation_results
        )
    ):
        return False
    provenance = acquisition.operation_results[0].provenance
    return provenance is not None and provenance.retrieved_at <= now < (
        provenance.retrieved_at + timedelta(seconds=case.policy_snapshot.registry.freshness_seconds)
    )


class HybridOwnershipOverlayCatalogue:
    """Resolve the whitelisted scenario for one eligible official root, or nothing."""

    def __init__(self, scenarios: Iterable[HybridOverlayScenario] | None = None) -> None:
        catalogue: dict[str, HybridOverlayScenario] = {}
        for scenario in HYBRID_OVERLAY_SCENARIOS if scenarios is None else scenarios:
            if scenario.root_uen in catalogue:
                raise ValueError("hybrid overlay roots must be unique")
            catalogue[scenario.root_uen] = scenario
        self._by_root: Mapping[str, HybridOverlayScenario] = catalogue

    @property
    def scenarios(self) -> tuple[HybridOverlayScenario, ...]:
        return tuple(self._by_root.values())

    def root_scenario(self, case: OnboardingCase, now: datetime) -> HybridOverlayScenario | None:
        scenario = self._by_root.get(case.requested_uen.strip().upper())
        if scenario is None or not official_marketplace_root_is_eligible(
            case, scenario.root_uen, now
        ):
            return None
        return scenario


def _garden_direct_issuer() -> OverlayIssuer:
    # Owner-supplied Garden body, direct rows only; SIM LIM's own holders are never
    # attached here and are left to the official cache-first lookup.
    rows = synthetic_issuer_shareholders(
        GARDEN_BUSINESS_MOCK_SHAREHOLDERS_BODY, requested_uen=GARDEN_BUSINESS_UEN
    )
    holders = tuple(
        OverlayHolder(
            holder_id=row.shareholder_id,
            holder_name=row.shareholder_name,
            category=row.shareholder_category,
            registration_number=(
                row.shareholder_id if row.shareholder_category == "Corporate" else None
            ),
            share_units=row.share_allotted,
            status=row.status,
        )
        for row in rows
    )
    return OverlayIssuer(
        issuer_uen=GARDEN_BUSINESS_UEN,
        local_display_name=GARDEN_BUSINESS_NAME,
        declared_active_units=sum(
            (item.share_units for item in holders if item.status == "Active"), Decimal("0")
        ),
        holders=holders,
    )


def _corporate(uen: str, name: str, units: str) -> OverlayHolder:
    return OverlayHolder(
        holder_id=uen,
        holder_name=name,
        category="Corporate",
        registration_number=uen,
        share_units=Decimal(units),
    )


def _person(identifier: str, name: str, units: str) -> OverlayHolder:
    return OverlayHolder(
        holder_id=identifier, holder_name=name, category="Individual", share_units=Decimal(units)
    )


# Five distinct corporate levels L1 -> L2 -> L3 -> L4 -> L5 plus an equal-length diamond
# (L4A and L4B both hold L5). UENs come from the operation-specific sample catalogue;
# the links, names below the root and unit counts are fictional demonstration input.
L2_UEN, L3_UEN, L4A_UEN, L4B_UEN, L5_UEN = (
    "200811111M",
    "201688888A",
    "200811111K",
    "199801111H",
    "111111111K",
)
FIVE_LAYER_ISSUERS: tuple[OverlayIssuer, ...] = (
    OverlayIssuer(
        issuer_uen=FIVE_LAYER_ROOT_UEN,
        local_display_name="OPQ PTE. LTD.",
        declared_active_units=Decimal("10000"),
        holders=(
            _corporate(L2_UEN, "FIVE LAYER L2 HOLDINGS (SYNTHETIC)", "8000"),
            _person("SYN-5L-P1", "ALEX TAN (SYNTHETIC PERSON)", "2000"),
        ),
    ),
    OverlayIssuer(
        issuer_uen=L2_UEN,
        local_display_name="FIVE LAYER L2 HOLDINGS (SYNTHETIC)",
        declared_active_units=Decimal("1000"),
        holders=(
            _corporate(L3_UEN, "FIVE LAYER L3 INVESTMENTS (SYNTHETIC)", "625"),
            _person("SYN-5L-P2", "BEATRICE LIM (SYNTHETIC PERSON)", "375"),
        ),
    ),
    OverlayIssuer(
        issuer_uen=L3_UEN,
        local_display_name="FIVE LAYER L3 INVESTMENTS (SYNTHETIC)",
        declared_active_units=Decimal("1000"),
        holders=(
            _corporate(L4A_UEN, "FIVE LAYER L4A CAPITAL (SYNTHETIC)", "600"),
            _corporate(L4B_UEN, "FIVE LAYER L4B VENTURES (SYNTHETIC)", "400"),
        ),
    ),
    OverlayIssuer(
        issuer_uen=L4A_UEN,
        local_display_name="FIVE LAYER L4A CAPITAL (SYNTHETIC)",
        declared_active_units=Decimal("100"),
        holders=(_corporate(L5_UEN, "FIVE LAYER L5 HOLDCO (SYNTHETIC)", "100"),),
    ),
    OverlayIssuer(
        issuer_uen=L4B_UEN,
        local_display_name="FIVE LAYER L4B VENTURES (SYNTHETIC)",
        declared_active_units=Decimal("100"),
        holders=(
            _corporate(L5_UEN, "FIVE LAYER L5 HOLDCO (SYNTHETIC)", "50"),
            _person("SYN-5L-P3", "CHARLES ONG (SYNTHETIC PERSON)", "50"),
        ),
    ),
    OverlayIssuer(
        issuer_uen=L5_UEN,
        local_display_name="FIVE LAYER L5 HOLDCO (SYNTHETIC)",
        declared_active_units=Decimal("1000"),
        holders=(
            _person("SYN-5L-P4", "DIANA KOH (SYNTHETIC PERSON)", "625"),
            _person("SYN-5L-P5", "EDWARD NG (SYNTHETIC PERSON)", "375"),
        ),
    ),
)

HYBRID_OVERLAY_SCENARIOS: tuple[HybridOverlayScenario, ...] = (
    HybridOverlayScenario(
        scenario_id=GARDEN_DIRECT_OVERLAY_SCENARIO_ID,
        root_uen=GARDEN_BUSINESS_UEN,
        issuers=(_garden_direct_issuer(),),
    ),
    HybridOverlayScenario(
        scenario_id=FIVE_LAYER_SCENARIO_ID,
        root_uen=FIVE_LAYER_ROOT_UEN,
        issuers=FIVE_LAYER_ISSUERS,
    ),
)
