import httpx
import pytest

from app.config import Settings
from app.demo.scenarios import INCOMPLETE_ENTITY_UEN, VALID_SME_UEN
from app.main import create_app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_create_and_retrieve_happy_path_case() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/api/onboarding/cases", json={"uen": VALID_SME_UEN.lower()}
        )
        case_id = create_response.json()["case_id"]
        get_response = await client.get(f"/api/onboarding/cases/{case_id}")

    assert create_response.status_code == 201
    assert create_response.json()["state"] == "COMPLETED"
    assert create_response.json()["requested_uen"] == VALID_SME_UEN
    assert get_response.status_code == 200
    assert get_response.json() == create_response.json()
    assert "registry_source_link" not in create_response.text
    assert "mock.acra.gov.sg" not in create_response.text
    assert "registry_source_link" not in get_response.text


@pytest.mark.anyio
async def test_mock_scenario_discovery_and_review_response() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        scenarios = await client.get("/api/onboarding/mock-scenarios")
        review = await client.post(
            "/api/onboarding/cases", json={"uen": INCOMPLETE_ENTITY_UEN}
        )

    assert scenarios.status_code == 200
    discovery = scenarios.json()
    assert discovery["simulation"] == {
        "is_simulated": True,
        "registry_system": "ACRA",
        "registry_environment": "MOCK",
        "target_system": "GOLDTIER",
        "target_environment": "MOCK",
        "idp_system": "IDP",
        "idp_environment": "LOCAL",
        "idp_provider": "LOCAL_PDF_TEXT",
        "idp_review_confidence_threshold": 0.85,
        "ownership_system": "OWNERSHIP_PROVIDER",
        "ownership_environment": "MOCK",
            "ubo_ownership_threshold_percent": "25",
            "persistence": "Process-local",
        }
    assert {scenario["expected_outcome"] for scenario in discovery["scenarios"]} == {
        "COMPLETED",
        "REVIEW_REQUIRED",
        "FAILED",
    }
    assert review.status_code == 201
    assert review.json()["state"] == "REVIEW_REQUIRED"


@pytest.mark.anyio
async def test_unknown_case_returns_application_404() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/onboarding/cases/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Onboarding case not found"}


@pytest.mark.anyio
async def test_whitespace_only_uen_is_rejected_before_case_creation() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/onboarding/cases", json={"uen": "   "})

    assert response.status_code == 422
    assert "UEN must not be blank" in response.text


@pytest.mark.anyio
async def test_padded_lowercase_uen_is_normalized_before_case_creation() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/onboarding/cases", json={"uen": f"  {VALID_SME_UEN.lower()}  "}
        )

    assert response.status_code == 201
    assert response.json()["requested_uen"] == VALID_SME_UEN
    assert response.json()["state"] == "COMPLETED"


@pytest.mark.anyio
async def test_well_formed_unknown_uen_is_a_registry_outcome_not_input_error() -> None:
    application = create_app(Settings(app_env="test", demo_controls_enabled=True))
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/onboarding/cases", json={"uen": "999999999Z"})

    assert response.status_code == 201
    assert response.json()["state"] == "FAILED"
    assert response.json()["error"]["code"] == "ACRA_ENTITY_NOT_FOUND"
