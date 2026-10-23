"""Explicit Phase 24 read-only Mock acceptance; emits minimized evidence only."""

from __future__ import annotations

import argparse
import json
import os
import ssl
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
from app.config import Settings
from app.connectors.acra_api_marketplace_auth import (
    AcraApiMarketplaceMockRequestAuthorizer,
    AcraApiMarketplaceMockTokenClient,
    AcraMarketplaceTokenHttpResponse,
    HttpxAcraMarketplaceTokenTransport,
)
from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import AcraHttpResponse, HttpxAcraTransport
from app.connectors.errors import ConnectorError
from app.connectors.registry import AcraRegistryProviderAdapter
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.models import EventOutcome, OnboardingCase, WorkflowEvent, WorkflowState
from app.domain.registry_legal_form import (
    RegistryLegalForm,
    classify_registry_legal_form,
)
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import (
    OwnershipInfrastructureError,
    OwnershipRequestError,
)
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from dotenv import dotenv_values
from pydantic import SecretStr, ValidationError

SAFE_FIELDS = frozenset(
    {
        "uen",
        "entityName",
        "entityConstnDetailsAndType",
        "constitution",
        "position",
        "shareAllotted",
        "shareholders",
        "individualShareholders",
        "corporateShareholders",
        "groupShareholders",
        "member",
        "status",
        "ownershipPercentage",
    }
)


def field_names(value: object) -> list[str]:
    found: set[str] = set()
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            found.update(key for key in item if key in SAFE_FIELDS)
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return sorted(found)


class RecordedReads(HttpxAcraTransport):
    def __init__(self, receipts: list[dict[str, object]], *, limit: int = 10) -> None:
        super().__init__(ssl_context=ssl.create_default_context(), trust_env=False)
        self.receipts = receipts
        self.limit = limit

    def get(
        self, url: str, *, headers: Mapping[str, str], timeout_seconds: float
    ) -> AcraHttpResponse:
        # Fixed connector URLs only; no production or arbitrary URL input.
        if (
            not url.startswith(ACRA_API_MARKETPLACE_MOCK_BASE_URL)
            or len(self.receipts) >= self.limit
        ):
            raise ValueError("Mock acceptance bound rejected")
        parsed = urlsplit(url)
        receipt: dict[str, object] = {
            "classification": "OFFICIAL_ACRA_MARKETPLACE_MOCK_READ",
            "operation": parsed.path.rsplit("/", 1)[-1],
            "uen": parse_qs(parsed.query).get("uen", [""])[0],
        }
        self.receipts.append(receipt)
        try:
            response = super().get(url, headers=headers, timeout_seconds=timeout_seconds)
        except Exception as exc:
            receipt["transport"] = "UNAVAILABLE"
            receipt["failure_kind"] = type(exc).__name__
            raise
        receipt["http_status"] = response.status_code
        receipt["relevant_fields"] = field_names(response.body)
        entities = response.body.get("entities") if isinstance(response.body, dict) else None
        receipt["returned_entity_count"] = len(entities) if isinstance(entities, list) else None
        return response


class RecordedToken(HttpxAcraMarketplaceTokenTransport):
    def __init__(self, receipts: list[dict[str, object]]) -> None:
        self.receipts = receipts

    def post(
        self,
        url: str,
        *,
        auth: httpx.BasicAuth,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> AcraMarketplaceTokenHttpResponse:
        receipt: dict[str, object] = {"classification": "OFFICIAL_ACRA_MARKETPLACE_MOCK_OAUTH"}
        self.receipts.append(receipt)
        try:
            response = super().post(
                url, auth=auth, headers=headers, body=body, timeout_seconds=timeout_seconds
            )
        except Exception:
            receipt["transport"] = "UNAVAILABLE"
            raise
        receipt["http_status"] = response.status_code
        return response


def normalized_sample(connector: AcraApiMarketplaceMockConnector, uen: str) -> dict[str, object]:
    """Exercise current canonical normalization/tagging/analysis in process memory only."""
    acquisition = AcraRegistryProviderAdapter(
        connector, company_shareholders_only=True
    ).retrieve_acquisition(uen)
    if acquisition is None:
        return {"identity": "EMPTY", "canonical_evidence_count": 0,
                "candidate_count": 0, "numerator": False, "denominator": False,
                "derived_percentage": False}
    now = datetime.now(UTC)
    case_id, correlation = uuid4(), uuid4()
    case = OnboardingCase(
        case_id=case_id, source_case_id="phase24-bounded-read", correlation_id=correlation,
        requested_uen=uen, entity=acquisition.entity_profile, registry_acquisition=acquisition,
        state=WorkflowState.REGISTRY_FETCHED, created_at=now, updated_at=now,
        events=[WorkflowEvent(sequence=1, stage=WorkflowState.REGISTRY_FETCHED,
                              outcome=EventOutcome.SUCCEEDED, timestamp=now,
                              case_id=case_id, correlation_id=correlation,
                              message="Bounded registry evidence received.")],
    )

    class Cases:
        def get_case(self, requested_id: UUID) -> OnboardingCase | None:
            return case if requested_id == case_id else None

    cases = Cases()
    settings = Settings(_env_file=None)
    ownership = OwnershipAnalysisService(
        cases=cases, provider=RegistryAcquisitionOwnershipProvider(cases),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=settings.ubo_ownership_threshold_percent,
        max_parties=settings.ownership_max_parties,
        max_relationships=settings.ownership_max_relationships,
        max_depth=settings.ownership_max_depth,
        max_paths_per_candidate=settings.ownership_max_paths_per_candidate,
        max_total_paths=settings.ownership_max_total_paths,
    )
    ownership.load(case_id=case_id)
    analyzed = ownership.analyze(case_id=case_id)
    return {
        "identity": "SAME_UEN_VERIFIED",
        "legal_form": analyzed.legal_form.value if analyzed.legal_form is not None else "UNKNOWN",
        "canonical_evidence_count": len(analyzed.evidence),
        "evidence_kinds": dict(Counter(item.kind.value for item in analyzed.evidence)),
        "tags": dict(Counter(item.tag for item in analyzed.tagging.tags))
                if analyzed.tagging is not None else {},
        "runtime_status": analyzed.tagging.runtime_status if analyzed.tagging is not None else None,
        "analysis_state": analyzed.state.value,
        "issue_codes": [issue.code.value for issue in analyzed.issues],
        "candidate_count": len(analyzed.candidates),
        "numerator": any(item.kind in {"SHARE_UNITS", "DIRECT_PERCENTAGE"}
                         for item in analyzed.evidence),
        "denominator": any(item.kind == "CAPITAL_DENOMINATOR" for item in analyzed.evidence),
        "derived_percentage": False,
    }


def evidence_class(receipts: list[dict[str, object]]) -> str:
    """Classify only what the recorded receipts prove; never assume success.

    MOCK_INTEROPERABILITY_OBSERVED requires at least one official data read answered
    with HTTP 200: live HTTPS access to the ACRA API Marketplace Mock environment, never
    ACRA production or Live-registry verification.
    """
    reads = [
        item for item in receipts
        if item.get("classification") == "OFFICIAL_ACRA_MARKETPLACE_MOCK_READ"
    ]
    if any(item.get("http_status") == 200 for item in reads):
        return "MOCK_INTEROPERABILITY_OBSERVED"
    if any(item.get("http_status") in {401, 403} for item in receipts):
        return "AUTHENTICATION_FAILED"
    if any("transport" in item for item in receipts):
        return "TRANSPORT_FAILURE"
    return "NO_SUCCESSFUL_READ"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-env-path", type=Path, required=True)
    parser.add_argument("--lane", choices=("discovery", "unbound-shareholders",
                                           "documented-basic", "garden-normalized",
                                           "five-layer-hybrid"),
                        default="discovery")
    arguments = parser.parse_args()
    names = ("ACRA_API_MARKETPLACE_MOCK_CLIENT_ID", "ACRA_API_MARKETPLACE_MOCK_SECRET_KEY")
    values = {
        key: value
        for key, value in dotenv_values(arguments.config_env_path).items()
        if key in names
    }
    credentials = [os.environ.get(name) or values.get(name) for name in names]
    receipts: list[dict[str, object]] = []
    samples: list[dict[str, object]] = []
    if not all(credentials):
        print(json.dumps({"status": "MOCK_CREDENTIALS_UNAVAILABLE", "actual_call_count": 0}))
        return 2
    token = AcraApiMarketplaceMockTokenClient(
        client_id=SecretStr(credentials[0] or ""),
        secret_key=SecretStr(credentials[1] or ""),
        timeout_seconds=10,
        transport=RecordedToken(receipts),
    )
    connector = AcraApiMarketplaceMockConnector(
        connection=AcraApiMarketplaceMockConnection(timeout_seconds=10),
        # One token receipt plus at most 16 reads for the D-077 lane; 10 otherwise.
        transport=RecordedReads(
            receipts, limit=17 if arguments.lane == "five-layer-hybrid" else 10
        ),
        authorizer=AcraApiMarketplaceMockRequestAuthorizer(token),
    )
    candidate_uens = {
        "unbound-shareholders": ("111111111M", "333333333C", "222222222C"),
        "discovery": ("11111999A", "111111111M", "333333333C", "222222222C"),
        "documented-basic": ("201511222D", "T13FC1122A", "T15LL1111W", "T17LP1111A",
                             "T19PF1111A", "111111111K"),
        "garden-normalized": ("11111999A",),
        # D-077 shortlist from the seven-page sample catalogue: 8 UENs, at most 16 GETs.
        "five-layer-hybrid": ("11111999A", "201511222D", "111111111M", "200811111M",
                              "201688888A", "200811111K", "199801111H", "111111111K"),
    }[arguments.lane]
    for uen in candidate_uens:
        sample: dict[str, object] = {
            "uen": uen,
            "numerator": False,
            "denominator": False,
            "derived_percentage": False,
        }
        samples.append(sample)
        try:
            if arguments.lane == "garden-normalized":
                sample.update(normalized_sample(connector, uen))
                continue
            if arguments.lane == "unbound-shareholders":
                # These operation-specific samples had EMPTY basic-entity receipts.
                # Inspect the supported source operation without attaching it to any
                # canonical case or calculating an ownership percentage.
                sample["identity"] = "UNBOUND_BASIC_ENTITY_EMPTY"
                ownership = connector.fetch_ownership_parties(uen)
                sample["ownership_party_count"] = len(ownership.ownership_parties)
                sample["numerator"] = any(
                    item.share_allotted is not None for item in ownership.ownership_parties
                )
                sample["percentage"] = "NOT_COMPUTED_UNBOUND"
                sample["denominator_operation"] = "CONTRACT_UNAVAILABLE"
                continue
            entity = connector.fetch_company(uen)
            if entity is None:
                sample["identity"] = "EMPTY"
                if arguments.lane == "five-layer-hybrid" and uen == "111111111M":
                    # Diagnostic only: never a canonical issuer or COMPLETE identity.
                    ownership = connector.fetch_ownership_parties(uen)
                    sample["diagnostic_shareholders"] = "UNBOUND_NOT_CANONICAL"
                    sample["ownership_party_count"] = len(ownership.ownership_parties)
                    sample["withdrawn_count"] = sum(
                        (item.source_status or "").upper() == "WITHDRAWN"
                        for item in ownership.ownership_parties
                    )
                continue
            sample["identity"] = "SAME_UEN_VERIFIED"
            legal_form = classify_registry_legal_form(entity.entity_type)
            sample["legal_form"] = legal_form.value
            if uen == "11111999A":
                people = connector.fetch_officers(uen)
                sample["people_count"] = len(people.officers)
                sample["owner_partner_member_roles"] = sum(
                    item.role.strip().upper() in {"OWNER", "PARTNER", "MEMBER"}
                    for item in people.officers
                )
            if legal_form != RegistryLegalForm.COMPANY:
                sample["ownership"] = "COMPANY_SHAREHOLDERS_NOT_APPLICABLE"
                sample["applicable_other_operation"] = "CONTRACT_UNAVAILABLE"
                continue
            ownership = connector.fetch_ownership_parties(uen)
            sample["ownership_party_count"] = len(ownership.ownership_parties)
            sample["numerator"] = any(
                item.share_allotted is not None for item in ownership.ownership_parties
            )
            sample["provider_percentage"] = any(
                item.ownership_percentage is not None for item in ownership.ownership_parties
            )
            sample["denominator_operation"] = "CONTRACT_UNAVAILABLE"
            if arguments.lane == "five-layer-hybrid":
                sample["withdrawn_count"] = sum(
                    (item.source_status or "").upper() == "WITHDRAWN"
                    for item in ownership.ownership_parties
                )
                continue
            if sample["provider_percentage"]:
                sample["quantitative_sample"] = "PROVIDER_PERCENTAGE"
                break
        except (ConnectorError, OwnershipInfrastructureError, OwnershipRequestError,
                ValidationError, ValueError, TypeError):
            # This explicit discovery tool must never print confidential validation inputs.
            sample["result"] = "UNAVAILABLE_OR_CONTRACT_REJECTED"
            # A failed OAuth/transport is not a reason to repeat the same unavailable lane.
            if receipts and (
                "transport" in receipts[-1] or receipts[-1].get("http_status") in {401, 403}
            ):
                break
    print(
        json.dumps(
            {
                "status": "BOUNDED_DISCOVERY_RECORDED",
                **(
                    {"evidence_class": evidence_class(receipts)}
                    if arguments.lane == "five-layer-hybrid"
                    else {}
                ),
                "actual_call_count": len(receipts),
                "receipts": receipts,
                "samples": samples,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
