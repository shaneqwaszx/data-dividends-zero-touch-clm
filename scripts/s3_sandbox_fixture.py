"""Explicit offline XPI responses for the isolated Session3 browser harness only."""

from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse

from scripts.run_s3_sandbox_acceptance import OfflineAcceptanceTransport

S3_SYNTHETIC_NAME = "ZERO TOUCH POC ACCEPTANCE TESTS3"
S3_SYNTHETIC_UEN = "202698765Z"


class OfflineS3SandboxTransport(OfflineAcceptanceTransport):
    def __init__(self, scenario: str) -> None:
        super().__init__(S3_SYNTHETIC_NAME, S3_SYNTHETIC_UEN)
        if scenario not in {"success", "uncertain-policy", "failed-policy"}:
            raise ValueError("Unknown offline Sandbox fixture")
        self.scenario = scenario
        self.counts = {"SEARCH": 0, "SHELL": 0, "POLICY": 0, "AMEND": 0, "READBACK": 0}

    def request(self, method: str, url: str, **kwargs: Any) -> GoldTierXpiHttpResponse:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "sandbox.goldtier.invalid":
            raise ValueError("Offline fixture refuses another destination")
        if method == "GET":
            operation = "READBACK" if self.created else "SEARCH"
            query = parse_qs(parsed.query)
            if query not in (
                {"legalName": [self.name], "countryOfIncorporation": ["SG"]},
                {"goldTierID": ["SYNTHETIC-GT-S3"]},
            ):
                raise ValueError("Offline fixture refuses another identity")
        elif parsed.path.endswith("/customers/create"):
            operation = "SHELL"
        elif parsed.path.endswith("/customers/createPolicy"):
            operation = "POLICY"
        else:
            raise ValueError("Offline fixture refuses another operation")
        self.counts[operation] += 1
        if operation in {"SHELL", "POLICY"} and self.counts[operation] > 1:
            raise ValueError("Offline fixture detected replay")
        if operation == "POLICY" and self.scenario == "uncertain-policy":
            raise httpx.ReadTimeout("Synthetic offline Policy timeout")
        if operation == "POLICY" and self.scenario == "failed-policy":
            return GoldTierXpiHttpResponse(400, {})
        return super().request(method, url, **kwargs)
