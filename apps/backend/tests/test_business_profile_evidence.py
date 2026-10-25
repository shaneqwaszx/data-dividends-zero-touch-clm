"""D-088 official Marketplace Mock businessProfile: connector, adapter, cache and codec.

The single owner-authorized read (2026-10-25) returned one Individual holding 1000
ORDINARY (SGD), with no row status, and issued and paid-up capital of 1000 ORDINARY. All
bodies below are synthetic stand-ins in that shape; counts arrive as JSON numbers.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic import ValidationError
from scripts.five_layer_hybrid_fixture import (
    ABC_SYNTHETIC_HOLDER_ID,
    ABC_SYNTHETIC_HOLDER_NAME,
    abc_business_profile,
)

from app.connectors.acra_api_marketplace_mock import (
    ACRA_API_MARKETPLACE_MOCK_BASE_URL,
    AcraApiMarketplaceMockConnection,
    AcraApiMarketplaceMockConnector,
)
from app.connectors.acra_sandbox import AcraHttpResponse
from app.connectors.errors import AcraAuthenticationError, AcraMalformedResponseError
from app.connectors.hybrid_ownership_overlay import ABC_COMPANY_UEN
from app.connectors.registry import AcraRegistryProviderAdapter, business_profile_holder_id
from app.domain.models import (
    BUSINESS_PROFILE_EVIDENCE_CONTRACT_VERSION,
    RegistryBusinessProfileEvidence,
    RegistryCacheKey,
    RegistryFreshnessPolicy,
    RegistryProviderIdentity,
    RegistrySnapshotEntry,
    SourceEnvironment,
    SourceSystem,
)
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

AT = datetime(2026, 10, 25, 3, 0, tzinfo=UTC)
ENDPOINT = f"{ACRA_API_MARKETPLACE_MOCK_BASE_URL}/entityQuery/businessProfile?uen={ABC_COMPANY_UEN}"
MARKETPLACE = RegistryProviderIdentity(
    provider=SourceSystem.ACRA,
    environment=SourceEnvironment.MOCK,
    acquisition_contract_version="PHASE10_ACQUISITION_V1",
    dataset_namespace="ACRA_API_MARKETPLACE_MOCK_V1",
)
PROFILE_KEY = RegistryCacheKey(
    provider_identity=MARKETPLACE.model_copy(
        update={"acquisition_contract_version": BUSINESS_PROFILE_EVIDENCE_CONTRACT_VERSION}
    ),
    normalized_identifier=ABC_COMPANY_UEN,
)


class Authorizer:
    def authorization_headers(self) -> Mapping[str, str]:
        return {"token": "opaque-test-token"}


class Transport:
    def __init__(self, response: AcraHttpResponse) -> None:
        self.response, self.urls = response, []

    def get(self, url: str, *, headers: Mapping[str, str], timeout_seconds: float) -> Any:
        self.urls.append(url)
        return self.response


def connector(body: object = None, status: int = 200, **response: Any) -> tuple[Any, Transport]:
    transport = Transport(
        AcraHttpResponse(
            status,
            abc_business_profile() if body is None else body,
            response.pop("content_type", "application/json"),
            response.pop("response_bytes", 1404),
            **response,
        )
    )
    return (
        AcraApiMarketplaceMockConnector(
            connection=AcraApiMarketplaceMockConnection(),
            transport=transport,
            authorizer=Authorizer(),
            clock=lambda: AT,
        ),
        transport,
    )


def body_with(**changes: Any) -> dict[str, Any]:
    body: Any = deepcopy(abc_business_profile())
    entity = body["entities"][0]
    for key, value in changes.items():
        if key.startswith("holder_"):
            entity["shareholder"][0][key.removeprefix("holder_")] = value
        else:
            entity[key] = value
    return body


# --- Connector and decoder --------------------------------------------------------------


def test_the_observed_shape_decodes_exactly_and_drops_identity_fields() -> None:
    source, transport = connector(
        body_with(officer=[{"id": "S0000000Z", "principalName": "X"}], registeredOfficeAddress={})
    )
    payload = source.fetch_business_profile(ABC_COMPANY_UEN)
    assert transport.urls == [ENDPOINT]
    assert (payload.entity_present, payload.entity_name, payload.status_of_company) == (
        True,
        "ABC COMPANY PTE. LTD.",
        "LIVE COMPANY",
    )
    [row] = payload.shareholders
    # JSON 1000.0 becomes the exact count 1000; no status was returned.
    assert (row.party_type, row.number_of_shares, row.share_type, row.source_status) == (
        "NATURAL_PERSON",
        Decimal("1000"),
        "ORDINARY",
        None,
    )
    [issued] = payload.issued_share_capital
    assert (issued.number_of_shares, issued.amount, issued.currency) == (
        Decimal("1000"),
        Decimal("1000.0"),
        "SINGAPORE DOLLAR",
    )
    dumped = payload.model_dump_json()
    assert "S0000000Z" not in dumped and "officer" not in dumped and "Address" not in dumped
    assert payload.source_endpoint == ENDPOINT.split("?")[0]


@pytest.mark.parametrize(
    "body",
    [
        body_with(holder_numberOfShares=1000.5),
        body_with(holder_numberOfShares=float("nan")),
        body_with(holder_numberOfShares=True),
        body_with(holder_numberOfShares=-1),
        # JSON strings are never counts, whole or fractional (D-088 QG P2-1).
        body_with(holder_numberOfShares="1000"),
        body_with(holder_numberOfShares="1000.5"),
        body_with(holder_numberOfShares="1e3"),
        body_with(issuedShareCapital=[{"numberOfShares": "12.5", "shareType": "ORDINARY"}]),
        body_with(issuedShareCapital=[{"numberOfShares": 1000.0, "amount": "1000"}]),
        body_with(holder_category="Trust"),
        body_with(uen="999999999Z"),
        {"entities": [abc_business_profile()["entities"][0]] * 2},  # type: ignore[index]
        {"items": []},
    ],
)
def test_malformed_profiles_are_refused(body: object) -> None:
    source, _ = connector(body)
    with pytest.raises(AcraMalformedResponseError):
        source.fetch_business_profile(ABC_COMPANY_UEN)


def test_empty_profiles_and_transport_failures_are_distinct() -> None:
    source, _ = connector({"entities": []})
    assert source.fetch_business_profile(ABC_COMPANY_UEN).entity_present is False
    for status, error in ((401, AcraAuthenticationError), (200, AcraMalformedResponseError)):
        extra = {"content_type": "text/html"} if status == 200 else {}
        source, _ = connector(status=status, **extra)
        with pytest.raises(error):
            source.fetch_business_profile(ABC_COMPANY_UEN)


# --- Registry adapter -----------------------------------------------------------------


def test_the_adapter_replaces_the_holder_identifier_with_an_opaque_digest() -> None:
    source, _ = connector()
    adapter = AcraRegistryProviderAdapter(source, company_shareholders_only=True, clock=lambda: AT)
    assert adapter.supports_business_profile_evidence
    evidence = adapter.retrieve_business_profile_evidence(ABC_COMPANY_UEN)
    assert evidence.status == "COMPLETE"
    [row] = evidence.shareholders
    assert row.party_id == business_profile_holder_id(ABC_COMPANY_UEN, ABC_SYNTHETIC_HOLDER_ID)
    assert row.name == ABC_SYNTHETIC_HOLDER_NAME
    assert ABC_SYNTHETIC_HOLDER_ID not in evidence.model_dump_json()
    assert evidence.evidence_reference == f"acra:business_profile:{ABC_COMPANY_UEN}"
    # Only the official Marketplace composition reads business profiles.
    assert not AcraRegistryProviderAdapter(source).supports_business_profile_evidence


def test_adapter_failures_are_safe_failed_results() -> None:
    source, _ = connector(body_with(holder_numberOfShares=1.5))
    adapter = AcraRegistryProviderAdapter(source, company_shareholders_only=True, clock=lambda: AT)
    failed = adapter.retrieve_business_profile_evidence(ABC_COMPANY_UEN)
    assert (failed.status, failed.error_code, failed.shareholders) == (
        "FAILED",
        "REGISTRY_OPERATION_MALFORMED_RESPONSE",
        (),
    )

    class Raising(Transport):
        def get(self, url: str, **_: Any) -> Any:
            raise httpx.ConnectError("offline")

    raising = AcraApiMarketplaceMockConnector(
        connection=AcraApiMarketplaceMockConnection(),
        transport=Raising(AcraHttpResponse(200, {}, "application/json", 2)),
        authorizer=Authorizer(),
        clock=lambda: AT,
    )
    failed = AcraRegistryProviderAdapter(
        raising, company_shareholders_only=True, clock=lambda: AT
    ).retrieve_business_profile_evidence(ABC_COMPANY_UEN)
    assert (failed.status, failed.error_code) == ("FAILED", "REGISTRY_OPERATION_UNAVAILABLE")


# --- Cache coordinator and codec ------------------------------------------------------


def profile_evidence(status: str, at: datetime) -> RegistryBusinessProfileEvidence:
    source, _ = connector({"entities": []} if status == "EMPTY" else None)
    if status == "FAILED":
        source, _ = connector(status=401)
    adapter = AcraRegistryProviderAdapter(source, company_shareholders_only=True, clock=lambda: at)
    evidence = adapter.retrieve_business_profile_evidence(ABC_COMPANY_UEN)
    return evidence.model_copy(update={"retrieved_at": at})


class FakeProfileProvider:
    cache_identity = MARKETPLACE
    supports_business_profile_evidence = True

    def __init__(self, status: str, clock: Any) -> None:
        self.status, self.clock, self.calls = status, clock, 0

    def retrieve_business_profile_evidence(self, identifier: str) -> Any:
        assert identifier == ABC_COMPANY_UEN
        self.calls += 1
        return profile_evidence(self.status, self.clock())


@pytest.mark.parametrize(
    ("status", "fresh_for", "cached"),
    [
        ("COMPLETE", timedelta(days=90), True),
        ("EMPTY", timedelta(seconds=600), True),
        ("FAILED", timedelta(0), False),
    ],
)
def test_coordinator_caches_profiles_under_their_own_key(
    status: str, fresh_for: timedelta, cached: bool
) -> None:
    now = [AT]
    repository = InMemoryRegistrySnapshotRepository()
    coordinator = RegistryAcquisitionCoordinator(
        repository, RegistryFreshnessPolicy(), clock=lambda: now[0]
    )
    provider = FakeProfileProvider(status, lambda: now[0])
    first = coordinator.acquire_business_profile_evidence(provider, ABC_COMPANY_UEN)
    assert (first.cache_hit, provider.calls) == (False, 1)
    entry = repository.get(PROFILE_KEY)
    if not cached:
        assert entry is None
        assert (
            coordinator.acquire_business_profile_evidence(provider, ABC_COMPANY_UEN).cache_hit
            is False
        )
        assert provider.calls == 2
        return
    assert entry is not None and entry.cache_schema_version == 5
    assert entry.business_profile_evidence == first.evidence
    assert (
        repository.get(
            RegistryCacheKey(provider_identity=MARKETPLACE, normalized_identifier=ABC_COMPANY_UEN)
        )
        is None
    )
    now[0] += fresh_for - timedelta(seconds=1)
    hit = coordinator.acquire_business_profile_evidence(provider, ABC_COMPANY_UEN)
    assert (hit.cache_hit, hit.evidence, provider.calls) == (True, first.evidence, 1)
    now[0] += timedelta(seconds=1)
    assert (
        coordinator.acquire_business_profile_evidence(provider, ABC_COMPANY_UEN).cache_hit is False
    )
    assert provider.calls == 2


def test_profile_cache_entries_are_exclusive_and_round_trip() -> None:
    good = profile_evidence("COMPLETE", AT)
    entry = RegistrySnapshotEntry(
        cache_schema_version=5,
        cache_id=PROFILE_KEY.digest,
        key=PROFILE_KEY,
        revision=0,
        acquisition=None,
        business_profile_evidence=good,
        freshness_anchor=AT,
        written_at=AT,
    )
    codec = MongoRegistryCacheStore
    assert codec._decode(codec._encode(entry)) == entry  # noqa: SLF001
    ordinary = RegistryCacheKey(
        provider_identity=MARKETPLACE, normalized_identifier=ABC_COMPANY_UEN
    )
    for invalid in (
        {"cache_schema_version": 4},
        {"key": ordinary, "cache_id": ordinary.digest},
        {"business_profile_evidence": profile_evidence("FAILED", AT)},
        {"business_profile_evidence": None},
        {"freshness_anchor": AT + timedelta(seconds=1)},
        {"negative_result": "NOT_FOUND"},
    ):
        with pytest.raises(ValidationError):
            RegistrySnapshotEntry.model_validate({**entry.model_dump(), **invalid})


def test_evidence_validators_fail_closed() -> None:
    good = profile_evidence("COMPLETE", AT)
    data = good.model_dump()
    for invalid in (
        {"status": "EMPTY"},
        {"status": "FAILED"},
        {"evidence_reference": "acra:business_profile:OTHER"},
        {"retrieved_at": datetime(2026, 10, 25)},
        {"shareholders": [*data["shareholders"], *data["shareholders"]]},
        {"error_code": "X"},
    ):
        with pytest.raises(ValidationError):
            RegistryBusinessProfileEvidence.model_validate({**data, **invalid})


@pytest.mark.skipif(
    not __import__("os").environ.get("PHASE12_MONGO_URI"),
    reason="PHASE12_MONGO_URI is not configured",
)
def test_profile_cache_entries_survive_a_physical_mongo_store_and_coordinator_restart() -> None:
    import os

    from pymongo import MongoClient
    from scripts.mongo_test_safety import (
        cleanup_ephemeral_mongo_database,
        generate_ephemeral_mongo_database,
    )

    uri = os.environ["PHASE12_MONGO_URI"]
    database = generate_ephemeral_mongo_database("p16")
    client: MongoClient[dict[str, Any]] = MongoClient(uri)
    try:
        store = MongoRegistryCacheStore(client, database=database, collection="registry_cache")
        store.initialize()
        now = [AT]
        provider = FakeProfileProvider("COMPLETE", lambda: now[0])
        first = RegistryAcquisitionCoordinator(
            store, RegistryFreshnessPolicy(), clock=lambda: now[0]
        ).acquire_business_profile_evidence(provider, ABC_COMPANY_UEN)
        stored = store.get(PROFILE_KEY)
        assert stored is not None and stored.cache_schema_version == 5
        assert stored.business_profile_evidence == first.evidence
        # A fresh coordinator (process restart) reuses the durable entry with no call.
        now[0] += timedelta(days=1)
        again = RegistryAcquisitionCoordinator(
            MongoRegistryCacheStore(client, database=database, collection="registry_cache"),
            RegistryFreshnessPolicy(),
            clock=lambda: now[0],
        ).acquire_business_profile_evidence(provider, ABC_COMPANY_UEN)
        assert (again.cache_hit, again.evidence, provider.calls) == (True, first.evidence, 1)
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
