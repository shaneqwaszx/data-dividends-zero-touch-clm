"""D-114: the UEN's own entity type picks the identity register; never a user choice.

Source for the PQ codes (provisional, not sponsor-confirmed): "Annex 1 - Information on
Singapore's Unique Entity Number (UEN) system". ACRA issues LL, LP, FC and PF; the Smart Nation
and Digital Government Office issues GA and GB. Every code list lives here so it is easy to change.
"""

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UEN_ROUTE_RULE_VERSION = "UEN-ROUTE-1"

_FORMAT_A = re.compile(r"^[0-9]{8}[A-Z]$")
_FORMAT_B = re.compile(r"^[0-9]{9}[A-Z]$")
_FORMAT_C = re.compile(r"^[TSR][0-9]{2}(?P<pq>[A-Z0-9]{2})[0-9]{4}[A-Z]$")

# Format C entity types ACRA registers; they keep the existing ACRA lookup.
ACRA_PQ_CODES: dict[str, str] = {
    "LL": "limited liability partnership",
    "LP": "limited partnership",
    "FC": "foreign company",
    "PF": "public accounting firm",
}
# Singapore government bodies; read only from the government register, never ACRA.
GOVERNMENT_PQ_CODES: dict[str, str] = {
    "GA": "organ of state, ministry or department",
    "GB": "statutory board",
}
# Known Format C types this POC does not onboard (named in the RM guidance). Any other code
# is unsupported as well and is named by its code only.
UNSUPPORTED_PQ_CODES: dict[str, str] = {
    "GS": "school",
    "DP": "foreign diplomatic mission",
    "CP": "foreign consular post",
    "NR": "international organisation",
    "RF": "foreign representative office",
    "SS": "society",
    "CC": "charity",
    "TU": "trade union",
    "MC": "management corporation",
}


class UenRoute(StrEnum):
    ACRA = "ACRA"
    GOVERNMENT_REGISTER = "GOVERNMENT_REGISTER"
    UNSUPPORTED = "UNSUPPORTED"


class UenRouteDecision(BaseModel):
    """How the system routed a UEN, retained on the case as its audit record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    uen: str = Field(min_length=1, max_length=32)
    route: UenRoute
    uen_format: Literal["A", "B", "C"]
    pq_code: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2}$")
    entity_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    rule_version: Literal["UEN-ROUTE-1"] = "UEN-ROUTE-1"


def route_uen(uen: str) -> UenRouteDecision | None:
    """Route a normalized UEN by its format; None when it is not a Singapore UEN shape."""

    normalized = uen.strip().upper()
    if _FORMAT_A.fullmatch(normalized):
        return _decision(normalized, UenRoute.ACRA, "A", None, "business")
    if _FORMAT_B.fullmatch(normalized):
        return _decision(normalized, UenRoute.ACRA, "B", None, "local company")
    match = _FORMAT_C.fullmatch(normalized)
    if match is None:
        return None
    code = match.group("pq")
    if code in ACRA_PQ_CODES:
        return _decision(normalized, UenRoute.ACRA, "C", code, ACRA_PQ_CODES[code])
    if code in GOVERNMENT_PQ_CODES:
        return _decision(
            normalized, UenRoute.GOVERNMENT_REGISTER, "C", code, GOVERNMENT_PQ_CODES[code]
        )
    return _decision(
        normalized, UenRoute.UNSUPPORTED, "C", code,
        UNSUPPORTED_PQ_CODES.get(code, f"unlisted entity type, code {code}"),
    )


def route_change_message(previous: UenRouteDecision, current: UenRouteDecision) -> str:
    """The audit line for a UEN correction that changes the route."""

    names = {
        UenRoute.ACRA: "ACRA",
        UenRoute.GOVERNMENT_REGISTER: "government register",
        UenRoute.UNSUPPORTED: "unsupported entity type",
    }
    kind = f"UEN type {current.pq_code}" if current.pq_code else f"UEN format {current.uen_format}"
    return f"Route changed from {names[previous.route]} to {names[current.route]} ({kind})."


def _decision(
    uen: str, route: UenRoute, uen_format: Literal["A", "B", "C"], code: str | None,
    entity_type: str,
) -> UenRouteDecision:
    coded = f"{entity_type}, code {code}" if code else entity_type
    if route == UenRoute.GOVERNMENT_REGISTER:
        description = (
            f"Government body ({coded}) · checked against the government register, not ACRA"
        )
    elif route == UenRoute.UNSUPPORTED:
        description = f"Not onboarded in this POC ({coded}) · no registry lookup"
    else:
        description = f"Format {uen_format} UEN ({coded}) · checked against ACRA"
    return UenRouteDecision(
        uen=uen, route=route, uen_format=uen_format, pq_code=code,
        entity_type=entity_type, description=description,
    )
