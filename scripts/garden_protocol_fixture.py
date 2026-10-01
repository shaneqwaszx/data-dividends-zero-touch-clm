"""Offline synthetic protocol input; never an observed ACRA response or fallback."""

from __future__ import annotations

import json
import secrets
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


@dataclass
class OfflineGardenProtocolTransport:
    """Allowlist one synthetic identity and fixed paths; no HTTP client exists here."""

    _token: str = field(default_factory=lambda: secrets.token_urlsafe(32), repr=False)
    calls: list[str] = field(default_factory=list)

    def post(
        self, url: str, *, auth: httpx.BasicAuth, headers: Mapping[str, str],
        body: bytes, timeout_seconds: float,
    ) -> AcraMarketplaceTokenHttpResponse:
        if url != ACRA_API_MARKETPLACE_MOCK_TOKEN_ENDPOINT or body != b"":
            raise ValueError("Offline protocol token request is outside the allowlist")
        self.calls.append("TOKEN")
        payload = json.dumps({
            "access_token": self._token, "expires_in": 3600,
            "scope": "read", "token_type": "Bearer",
        }).encode()
        return AcraMarketplaceTokenHttpResponse(200, "application/json", payload, len(payload))

    def get(
        self, url: str, *, headers: Mapping[str, str], timeout_seconds: float,
    ) -> AcraHttpResponse:
        parsed = urlsplit(url)
        base = urlsplit(ACRA_API_MARKETPLACE_MOCK_BASE_URL)
        if (
            parsed.scheme != base.scheme or parsed.netloc != base.netloc
            or parse_qs(parsed.query) != {"uen": ["11111999A"]}
            or parsed.fragment or headers.get("token") != self._token
        ):
            raise ValueError("Offline protocol lookup is outside the allowlist")
        if parsed.path == f"{base.path}/entityQuery/entityBasicInformation":
            self.calls.append("ENTITY_PROFILE")
            payload: object = {"entities": [{
                "uen": "11111999A", "name": "GARDEN BUSINESS",
                "entityRegistrationKeyDates": {"registrationDate": "2024-01-02"},
                "entityRegisteredAddressDetails": {"registeredAddress": {
                    "blkhseNo": "18", "streetName": "GARDEN WALK",
                    "levelNo": "01", "unitNo": "01", "postalCode": "018919",
                }},
                "entityConstnDetailsAndType": {
                    "constitution": "PRIVATE COMPANY LIMITED BY SHARES",
                },
                "entityOfficersRecord": {"officerAppointmentDetails": [{
                    "officerId": "DEMO-OFFICER", "officerName": "DEMO OFFICER",
                    "position": "DIRECTOR", "appointedDate": "2024-01-02",
                }]},
            }]}
        elif parsed.path == f"{base.path}/entityQuery/coShareholdersDetails":
            self.calls.append("SHAREHOLDERS")
            payload = {"entities": []}
        else:
            raise ValueError("Offline protocol operation is outside the allowlist")
        return AcraHttpResponse(200, payload, "application/json", len(json.dumps(payload)))
