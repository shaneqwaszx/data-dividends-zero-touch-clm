import json

import httpx
import pytest

from app.config import Settings
from app.demo.scenarios import VALID_SME_UEN
from app.main import create_app


async def create_case(client: httpx.AsyncClient) -> dict[str, object]:
    response = await client.post("/api/onboarding/cases", json={"uen": VALID_SME_UEN})
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_demo_load_analyze_get_and_candidate_contract() -> None:
    application = create_app(Settings(app_env="test"))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        case_id = case["case_id"]
        loaded = await client.post(
            f"/api/demo/onboarding/cases/{case_id}/ownership/load",
            headers={"X-Mock-Ownership-Scenario": "INDIRECT_OWNER"},
        )
        analyzed = await client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze")
        retrieved = await client.get(f"/api/onboarding/cases/{case_id}/ownership")
        candidates = await client.get(f"/api/onboarding/cases/{case_id}/ubo-candidates")

    assert loaded.status_code == 201 and loaded.json()["state"] == "LOADED"
    assert analyzed.status_code == 200 and analyzed.json()["state"] == "ANALYZED"
    assert retrieved.json() == analyzed.json()
    assert [item["aggregated_ownership_percent"] for item in candidates.json()] == [
        "30.000",
        "10.000",
    ]
    assert analyzed.json()["threshold_percent"] == "25"
    assert analyzed.json()["threshold_comparator"] == "GREATER_THAN_OR_EQUAL_TO"
    assert analyzed.json()["provider_environment"] == "MOCK"
    assert "source_reference" not in json.dumps(analyzed.json())
    assert set(analyzed.json()["relationships"][0]["provenance"]) == {
        "provider",
        "environment",
        "sourced_at",
    }


@pytest.mark.anyio
async def test_generic_load_has_no_mock_scenario_request_contract() -> None:
    application = create_app(Settings(app_env="test"))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        response = await client.post(f"/api/onboarding/cases/{case['case_id']}/ownership/load")
        openapi = (await client.get("/openapi.json")).json()
    assert response.status_code == 201
    operation = openapi["paths"]["/api/onboarding/cases/{case_id}/ownership/load"]["post"]
    assert "X-Mock-Ownership-Scenario" not in str(operation)


@pytest.mark.anyio
async def test_unknown_case_not_loaded_invalid_scenario_and_case_isolation() -> None:
    application = create_app(Settings(app_env="test"))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unknown = await client.post(
            "/api/onboarding/cases/00000000-0000-4000-8000-000000000999/ownership/load"
        )
        first = await create_case(client)
        second = await create_case(client)
        not_loaded = await client.post(
            f"/api/onboarding/cases/{first['case_id']}/ownership/analyze"
        )
        invalid = await client.post(
            f"/api/demo/onboarding/cases/{first['case_id']}/ownership/load",
            headers={"X-Mock-Ownership-Scenario": "NOT_A_SCENARIO"},
        )
        loaded = await client.post(
            f"/api/demo/onboarding/cases/{first['case_id']}/ownership/load",
            headers={"X-Mock-Ownership-Scenario": "DIRECT_OWNER"},
        )
        other = await client.get(f"/api/onboarding/cases/{second['case_id']}/ownership")
    assert unknown.status_code == 404
    assert not_loaded.status_code == 404
    assert not_loaded.json()["detail"]["code"] == "OWNERSHIP_NOT_LOADED"
    assert invalid.status_code == 422
    assert loaded.status_code == 201
    assert other.status_code == 404


@pytest.mark.anyio
async def test_provider_failure_is_retrievable_and_sanitized_through_api() -> None:
    application = create_app(Settings(app_env="test"))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        case_id = case["case_id"]
        failed = await client.post(
            f"/api/demo/onboarding/cases/{case_id}/ownership/load",
            headers={"X-Mock-Ownership-Scenario": "PROVIDER_FAILURE"},
        )
        retrieved = await client.get(f"/api/onboarding/cases/{case_id}/ownership")
        parent = await client.get(f"/api/onboarding/cases/{case_id}")
    assert failed.status_code == 503
    assert set(failed.json()["detail"]) == {
        "code",
        "message",
        "case_id",
        "analysis_id",
        "correlation_id",
    }
    assert "ProviderError" not in failed.text
    assert retrieved.status_code == 200
    assert retrieved.json()["state"] == "FAILED"
    assert retrieved.json()["error"]["code"] == "OWNERSHIP_PROVIDER_FAILED"
    assert parent.json() == case


@pytest.mark.anyio
async def test_ownership_failure_does_not_corrupt_document_review_state() -> None:
    application = create_app(Settings(app_env="test"))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        case = await create_case(client)
        case_id = case["case_id"]
        document = await client.post(
            f"/api/demo/onboarding/cases/{case_id}/documents",
            content=b"%PDF-1.4\nSYNTHETIC PHASE 04 ISOLATION\n%%EOF",
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "synthetic-isolation.pdf",
                "X-Mock-IDP-Scenario": "ALL_FIELDS_MATCH",
            },
        )
        failed = await client.post(
            f"/api/demo/onboarding/cases/{case_id}/ownership/load",
            headers={"X-Mock-Ownership-Scenario": "PROVIDER_FAILURE"},
        )
        unchanged = await client.get(
            f"/api/onboarding/cases/{case_id}/documents/{document.json()['document_id']}"
        )
    assert document.status_code == 201
    assert failed.status_code == 503
    assert unchanged.status_code == 200
    assert unchanged.json() == document.json()


@pytest.mark.anyio
async def test_cycle_and_incomplete_are_truthful_review_states() -> None:
    for scenario, issue in (
        ("CYCLE", "CYCLE_DETECTED"),
        ("INCOMPLETE_CHAIN", "INCOMPLETE_LEGAL_ENTITY"),
    ):
        application = create_app(Settings(app_env="test"))
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            case = await create_case(client)
            case_id = case["case_id"]
            await client.post(
                f"/api/demo/onboarding/cases/{case_id}/ownership/load",
                headers={"X-Mock-Ownership-Scenario": scenario},
            )
            response = await client.post(f"/api/onboarding/cases/{case_id}/ownership/analyze")
        body = response.json()
        assert body["state"] == "REVIEW_REQUIRED"
        assert body["candidates"] == []
        assert issue in {item["code"] for item in body["issues"]}
