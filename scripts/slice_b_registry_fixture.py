"""Offline Slice-B evidence; no observed payload, private bytes or HTTP dispatch."""

from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.parse import parse_qs, urlsplit

from app.connectors.acra import (
    AcraCompanyPayload,
    AcraOfficersPayload,
    AcraOwnershipPartiesPayload,
    AcraRelationshipsPayload,
)
from app.connectors.acra_api_marketplace_mock import ACRA_API_MARKETPLACE_MOCK_BASE_URL
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.mock_acra import MockAcraConnector

from scripts.garden_protocol_fixture import OfflineGardenProtocolTransport

# Entity-level normalized fields already recorded in the accepted verification report.
# Officers and economic interests below are fictional; personal provider records omitted.
GARDEN_FIELDS = {
    "Legal Name": "GARDEN BUSINESS",
    "UEN": "11111999A",
    "Registered Address": "306C XYZ LINK, #03-21, ABC GARDEN, 333333, SG",
    "Country": "SG",
}
SECOND_FIELDS = {
    "Legal Name": "MULTIPLE OWNER DEMO PTE. LTD.",
    "UEN": "202400008H",
    "Registered Address": "18 SHAREHOLDER ROAD, #03-01, 049003, SG",
    "Country": "SG",
}


class GardenPartnershipProtocolTransport(OfflineGardenProtocolTransport):
    """Real strict decoder, recorded identity, fictional roles, zero external HTTP."""

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> AcraHttpResponse:
        if not urlsplit(url).path.endswith("/entityBasicInformation"):
            raise ValueError("Partnership protocol operation is outside the allowlist")
        response = super().get(url, headers=headers, timeout_seconds=timeout_seconds)
        payload = {
            "entities": [
                {
                    "uen": "11111999A",
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
        return AcraHttpResponse(
            response.status_code, payload, "application/json", len(json.dumps(payload))
        )


class GardenCorrectionProtocolTransport(GardenPartnershipProtocolTransport):
    """One fictional wrong-UEN absence plus the existing truthful PARTIAL Garden input."""

    def get(
        self, url: str, *, headers: Mapping[str, str], timeout_seconds: float,
    ) -> AcraHttpResponse:
        parsed = urlsplit(url)
        base = urlsplit(ACRA_API_MARKETPLACE_MOCK_BASE_URL)
        if parse_qs(parsed.query) == {"uen": ["11111998B"]}:
            if (
                parsed.scheme != base.scheme or parsed.netloc != base.netloc
                or parsed.path != f"{base.path}/entityQuery/entityBasicInformation"
                or parsed.fragment or headers.get("token") != self._token
            ):
                raise ValueError("Wrong-UEN protocol lookup is outside the allowlist")
            self.calls.append("NOT_FOUND")
            return AcraHttpResponse(200, {"entities": []}, "application/json", 16)
        return super().get(url, headers=headers, timeout_seconds=timeout_seconds)


class CountingSyntheticRegistry:
    """Test-owned counter through the existing connector port; no production telemetry."""

    def __init__(self) -> None:
        self.delegate = MockAcraConnector()
        self.calls: list[tuple[str, str]] = []

    def _record(self, operation: str, uen: str) -> None:
        self.calls.append((operation, uen))

    def fetch_company(self, uen: str) -> AcraCompanyPayload | None:
        self._record("ENTITY_PROFILE", uen)
        return self.delegate.fetch_company(uen)

    def fetch_officers(self, uen: str) -> AcraOfficersPayload:
        self._record("OFFICERS", uen)
        return self.delegate.fetch_officers(uen)

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self._record("OWNERSHIP_PARTIES", uen)
        return self.delegate.fetch_ownership_parties(uen)

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self._record("RELATIONSHIPS", uen)
        return self.delegate.fetch_relationships(uen)
