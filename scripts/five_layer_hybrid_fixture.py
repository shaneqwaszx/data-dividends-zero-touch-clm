"""Offline five-layer hybrid protocol input; never an observed ACRA response or fallback.

The real official Marketplace Mock connector, decoders, cache and ownership owners run
unchanged against this allowlisted in-process transport. It answers only the sample
catalogue UENs used by the D-077 demonstration. Entity answers are synthetic protocol
inputs shaped like the historical Phase 24 observations (root profile present with an
unclassified legal form; other issuers explicitly empty). Unprobed UENs are offline
assumptions, not observations: live outcomes are recorded only by an authorized probe.
"""

from __future__ import annotations

import json
import secrets
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

import httpx
from app.connectors.acra_api_marketplace_auth import (
    ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT,
    AcraMarketplaceTokenHttpResponse,
)
from app.connectors.acra_api_marketplace_mock import ACRA_API_MARKETPLACE_MOCK_BASE_URL
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.hybrid_ownership_overlay import (
    FIVE_LAYER_ROOT_UEN,
    L2_UEN,
    L3_UEN,
    L4A_UEN,
    L4B_UEN,
    L5_UEN,
)

FIVE_LAYER_ROOT_NAME = "OPQ PTE. LTD."
# Certificate-of-incorporation profile fields; the registered address is deliberately
# omitted (REGISTRY_ONLY) because no official address was confirmed in this session.
FIVE_LAYER_FIELDS = {
    "Legal Name": FIVE_LAYER_ROOT_NAME,
    "UEN": FIVE_LAYER_ROOT_UEN,
    "Country": "SG",
}
GARDEN_UEN = "11111999A"
SIM_LIM_UEN = "111111111M"
ALLOWLISTED_UENS = frozenset(
    {
        FIVE_LAYER_ROOT_UEN,
        L2_UEN,
        L3_UEN,
        L4A_UEN,
        L4B_UEN,
        L5_UEN,
        GARDEN_UEN,
        SIM_LIM_UEN,
    }
)
_ENTITY_PATH = "/entityQuery/entityBasicInformation"
_SHAREHOLDERS_PATH = "/entityQuery/coShareholdersDetails"


def five_layer_root_profile() -> dict[str, object]:
    """Synthetic root: same UEN, sample-catalogue name, no constitution value.

    The canonical minimum requires a registered address. This visibly synthetic
    address is an offline protocol input only; no official OPQ address was observed.
    """
    return {
        "entities": [
            {
                "uen": FIVE_LAYER_ROOT_UEN,
                "name": FIVE_LAYER_ROOT_NAME,
                "entityRegisteredAddressDetails": {
                    "registeredAddress": {
                        "blkhseNo": "1",
                        "streetName": "SYNTHETIC OFFLINE PROTOCOL ROAD",
                        "postalCode": "000001",
                    }
                },
            }
        ]
    }


def garden_partnership_profile() -> dict[str, object]:
    """Garden as the accepted PARTNERSHIP protocol shape (tracked normalized fields)."""
    return {
        "entities": [
            {
                "uen": GARDEN_UEN,
                "name": "GARDEN BUSINESS",
                "entityRegistrationKeyDates": {"registrationDate": "1974-09-28"},
                "entityRegisteredAddressDetails": {
                    "registeredAddress": {
                        "blkhseNo": "306C",
                        "streetName": "XYZ LINK",
                        "levelNo": "03",
                        "unitNo": "21",
                        "buildingName": "ABC GARDEN",
                        "postalCode": "333333",
                    }
                },
                "entityConstnDetailsAndType": {"constitution": "PARTNERSHIP"},
                "entityOfficersRecord": {
                    "officerAppointmentDetails": [
                        {
                            "officerId": f"SYNTHETIC-ROLE-{index}",
                            "officerName": f"Synthetic Garden Role {index}",
                            "position": "OWNER",
                            "appointedDate": "1974-09-28",
                        }
                        for index in range(1, 5)
                    ]
                },
            }
        ]
    }


def _default_profiles() -> dict[str, dict[str, object] | None]:
    profiles: dict[str, dict[str, object] | None] = {
        uen: None for uen in ALLOWLISTED_UENS
    }
    profiles[FIVE_LAYER_ROOT_UEN] = five_layer_root_profile()
    profiles[GARDEN_UEN] = garden_partnership_profile()
    return profiles


@dataclass
class OfflineFiveLayerProtocolTransport:
    """Counting allowlisted token/GET transport; no HTTP client exists here."""

    profiles: dict[str, dict[str, object] | None] = field(
        default_factory=_default_profiles
    )
    shareholders: dict[str, dict[str, object]] = field(default_factory=dict)
    failures: dict[str, int | Exception] = field(default_factory=dict)
    token_status: int = 200
    allowlist: frozenset[str] = ALLOWLISTED_UENS
    _token: str = field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)
    token_requests: int = 0
    calls: Counter[tuple[str, str]] = field(default_factory=Counter)

    def post(
        self,
        url: str,
        *,
        auth: httpx.BasicAuth,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> AcraMarketplaceTokenHttpResponse:
        if url != ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT or body != b"":
            raise ValueError("Offline protocol token request is outside the allowlist")
        self.token_requests += 1
        if self.token_status != 200:
            return AcraMarketplaceTokenHttpResponse(
                self.token_status, "application/json", b"{}", 2
            )
        payload = json.dumps(
            {
                "access_token": self._token,
                "expires_in": 3600,
                "scope": "read",
                "token_type": "Bearer",
            }
        ).encode()
        return AcraMarketplaceTokenHttpResponse(
            200, "application/json", payload, len(payload)
        )

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        parsed = urlsplit(url)
        base = urlsplit(ACRA_API_MARKETPLACE_MOCK_BASE_URL)
        query = parse_qs(parsed.query)
        uen = query.get("uen", [""])[0]
        operation = parsed.path.removeprefix(base.path)
        if (
            parsed.scheme != base.scheme
            or parsed.netloc != base.netloc
            or set(query) != {"uen"}
            or len(query["uen"]) != 1
            or uen not in self.allowlist
            or parsed.fragment
            or operation not in {_ENTITY_PATH, _SHAREHOLDERS_PATH}
            or headers.get("token") != self._token
        ):
            raise ValueError("Offline protocol lookup is outside the allowlist")
        label = "ENTITY_PROFILE" if operation == _ENTITY_PATH else "SHAREHOLDERS"
        self.calls[(label, uen)] += 1
        failure = self.failures.get(uen)
        if isinstance(failure, Exception):
            raise failure
        if isinstance(failure, int):
            return AcraHttpResponse(failure, {}, "application/json", 2)
        payload: object
        if operation == _ENTITY_PATH:
            payload = self.profiles.get(uen) or {"entities": []}
        else:
            payload = self.shareholders.get(uen, {"entities": []})
        return AcraHttpResponse(
            200, payload, "application/json", len(json.dumps(payload))
        )

    @property
    def get_count(self) -> int:
        return sum(self.calls.values())

    def metadata(self) -> dict[str, object]:
        """Safe counters only: operation, UEN and count; never tokens or bodies."""
        return {
            "classification": "AUTOMATED_OFFLINE_SIMULATION",
            "external_calls": 0,
            "token_requests": self.token_requests,
            "gets": [
                {"operation": operation, "uen": uen, "count": count}
                for (operation, uen), count in sorted(self.calls.items())
            ],
        }
