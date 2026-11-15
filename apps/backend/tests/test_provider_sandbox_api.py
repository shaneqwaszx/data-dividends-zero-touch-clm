from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request
from phase13_test_clients import RawAsyncClient
from pydantic import SecretStr

from app.api_provider_sandbox import build_provider_sandbox_router
from app.config import Settings
from app.connectors.goldtier_models import (
    GoldTierSearchCandidate,
    GoldTierSearchOutcome,
    GoldTierSearchResult,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.domain.access import AuthenticatedActor, Role, TeamId, UserProfile
from app.domain.onboarding_intelligence import EntityIdentity
from app.domain.target_submission import GoldTierProviderMode
from app.services.onboarding import TargetIdentitySearchEvidence
from app.services.onboarding_intelligence import OnboardingIntelligenceService


class RecordingSandboxSearch:
    def __init__(self) -> None:
        self.calls: list[XpiCustomerSearchRequest] = []

    @property
    def target_provider_mode(self) -> GoldTierProviderMode:
        return GoldTierProviderMode.SANDBOX

    def target_read_budget_usage(self, now: datetime) -> tuple[int, int]:
        assert now.tzinfo is UTC
        return 8, 3

    def search_sandbox_target(
        self,
        request: XpiCustomerSearchRequest,
        *,
        correlation_id: UUID,
    ) -> TargetIdentitySearchEvidence:
        del correlation_id
        self.calls.append(request)
        candidate = GoldTierSearchCandidate(
            party_id="GT-SANDBOX-1",
            legal_name="SYNTHETIC PTE LTD",
            country="SG",
        )
        result = GoldTierSearchResult(
            outcome=GoldTierSearchOutcome.MATCH_FOUND,
            status_code=200,
            matched_party_id=candidate.party_id,
            candidates=(candidate,),
            message="GoldTier sandbox Search returned one bounded candidate.",
        )
        resolution = OnboardingIntelligenceService().resolve_entity(
            source=EntityIdentity(
                candidate_id="SANDBOX-CONSOLE",
                legal_name=request.legal_name,
                country=request.country_of_incorporation,
                source_reference="GOLDTIER_SANDBOX_CONSOLE",
            ),
            candidates=(
                EntityIdentity(
                    candidate_id=candidate.party_id,
                    legal_name=candidate.legal_name,
                    country=candidate.country,
                    source_reference=f"goldtier:{candidate.party_id}",
                ),
            ),
        )
        return TargetIdentitySearchEvidence(result=result, resolution=resolution)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-user"),
        goldtier_sandbox_allow_writes=True,
    )


def _actor(role: Role) -> AuthenticatedActor:
    return AuthenticatedActor(
        profile=UserProfile(
            user_id="hr-admin" if role == Role.HR else "maya-lim",
            display_name="Test actor",
            role=role,
            team_id=None if role in {Role.HR, Role.DIRECTOR} else TeamId.TEAM_A,
        )
    )


def _app(
    service: RecordingSandboxSearch,
    role: Role,
    settings: Settings | None = None,
) -> FastAPI:
    application = FastAPI()

    @application.middleware("http")
    async def actor_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.actor = _actor(role)
        return await call_next(request)

    application.include_router(
        build_provider_sandbox_router(service, settings or _settings())  # type: ignore[arg-type]
    )
    return application


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_hr_status_search_and_dry_run_are_safe_and_bounded() -> None:
    service = RecordingSandboxSearch()
    transport = httpx.ASGITransport(app=_app(service, Role.HR))
    test_values = {
        "kyc_customer_type": "Company - Private",
        "client_segment": "Corporate",
        "customer_external_system": "DSD",
        "registration_type": "ACRA",
        "policy": "Singapore",
        "booking_entity": "ANZBGL (Singapore Branch)",
        "account_entity_type": "",
        "product_type": "",
    }
    async with RawAsyncClient(transport=transport, base_url="http://test") as client:
        status_response = await client.get("/api/admin/goldtier-sandbox/status")
        search_response = await client.post(
            "/api/admin/goldtier-sandbox/search",
            json={"legal_name": "SYNTHETIC PTE LTD", "country_of_incorporation": "SG"},
        )
        dry_run_response = await client.post(
            "/api/admin/goldtier-sandbox/dry-run",
            json={
                "search": {
                    "legal_name": "SYNTHETIC PTE LTD",
                    "country_of_incorporation": "SG",
                },
                "test_values": test_values,
            },
        )

    assert status_response.status_code == 200
    status_projection = status_response.json()
    assert status_projection["classification"] == "SANDBOX_PARTIAL"
    assert status_projection["daily_read_limit"] == 8
    assert status_projection["reads_used_today"] == 3
    assert status_projection["safe_host"] == "sandbox.goldtier.invalid"
    assert status_projection["customer_operations"] == "PARTIAL"
    assert status_projection["related_party_operations"] == "BLOCKED_CONTRACT"
    assert status_projection["blocker_code"] == "BLOCKED_CHILD_ID_LIFECYCLE"
    assert status_projection["required_authority"] == "SPONSOR_CONFIRMATION"
    assert "synthetic-user" not in status_response.text
    assert search_response.status_code == 200
    assert search_response.json()["entity_resolution"] == "REVIEW_REQUIRED"
    assert search_response.json()["count"] == 1
    assert dry_run_response.status_code == 200
    assert dry_run_response.json()["dispatch_ready"] is True
    assert all(
        field["authority"] == "SANDBOX_TEST_ONLY"
        for operation in dry_run_response.json()["operations"]
        for field in operation["fields"]
        if field["provenance"] == "POLICY"
    )
    assert len(service.calls) == 1


@pytest.mark.anyio
async def test_mock_status_uses_mock_classification_and_disables_writes() -> None:
    service = RecordingSandboxSearch()
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="mock",
        goldtier_sandbox_allow_writes=True,
    )
    transport = httpx.ASGITransport(app=_app(service, Role.HR, settings))

    async with RawAsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/goldtier-sandbox/status")

    assert response.status_code == 200
    assert response.json()["mode"] == "MOCK"
    assert response.json()["classification"] == "MOCK"
    assert response.json()["writes_enabled"] is False
    assert response.json()["safe_host"] is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    "role",
    [Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER, Role.DIRECTOR],
)
async def test_non_hr_is_forbidden_and_guarded_write_makes_zero_provider_calls(
    role: Role,
) -> None:
    forbidden_service = RecordingSandboxSearch()
    forbidden_transport = httpx.ASGITransport(app=_app(forbidden_service, role))
    async with RawAsyncClient(transport=forbidden_transport, base_url="http://test") as client:
        forbidden = await client.get("/api/admin/goldtier-sandbox/status")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "PROVIDER_SANDBOX_TEST_FORBIDDEN"

    hr_service = RecordingSandboxSearch()
    hr_transport = httpx.ASGITransport(app=_app(hr_service, Role.HR))
    async with RawAsyncClient(transport=hr_transport, base_url="http://test") as client:
        blocked = await client.post(
            "/api/admin/goldtier-sandbox/write",
            json={"confirmation": "SANDBOX_TEST_ONLY"},
        )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == ("GOLDTIER_SANDBOX_WRITE_REQUIRES_CASE_LEDGER")
    assert hr_service.calls == []


@pytest.mark.anyio
async def test_blank_search_is_rejected_before_provider_access() -> None:
    service = RecordingSandboxSearch()
    transport = httpx.ASGITransport(app=_app(service, Role.HR))

    async with RawAsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/admin/goldtier-sandbox/search", json={})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "GOLDTIER_SANDBOX_SEARCH_INVALID"
    assert service.calls == []
