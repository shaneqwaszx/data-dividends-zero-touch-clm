"""Normal Sandbox composition, truthful uncertainty and strictly read-only checks."""

from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pydantic import SecretStr
from scripts.run_s3_sandbox_acceptance import (
    BoundedAcceptanceTransport,
    OfflineAcceptanceTransport,
    SyntheticAcceptanceAcra,
    prepare_case,
)

from app.config import Settings
from app.main import create_app

NAME = "ZERO TOUCH POC ACCEPTANCE TESTS3"
UEN = "202698765Z"


class ScenarioTransport(OfflineAcceptanceTransport):
    def __init__(self, scenario: str) -> None:
        super().__init__(NAME, UEN)
        self.scenario = scenario
        self.policy_attempted = False

    def request(self, method, url, **kwargs):
        if method == "POST" and url.endswith("/createPolicy"):
            self.policy_attempted = True
            if self.scenario == "uncertain":
                raise httpx.ReadTimeout("synthetic test timeout")
            if self.scenario == "failed":
                from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse
                return GoldTierXpiHttpResponse(400, {})
        return super().request(method, url, **kwargs)


@pytest.fixture
def sandbox_runtime(request) -> Iterator[tuple[RawTestClient, BoundedAcceptanceTransport]]:
    scenario = getattr(request, "param", "success")
    guard = BoundedAcceptanceTransport(
        ScenarioTransport(scenario), origin="https://sandbox.goldtier.invalid",
        environment="synthetic", name=NAME, uen=UEN,
    )
    settings = Settings(
        _env_file=None, app_env="test", goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-api-user"),
        goldtier_sandbox_allow_writes=True,
    )
    with RawTestClient(create_app(
        settings, acra_connector=SyntheticAcceptanceAcra(NAME, UEN), goldtier_transport=guard
    )) as client:
        yield client, guard


def confirm(client, summary):
    return client.post(
        f"/api/clm/zero-touch/cases/{summary['case']['case_id']}/target-confirmation",
        json={
            "expected_automation_version": summary["version"],
            "expected_clm_version": summary["clm"]["version"],
            "expected_case_event_count": len(summary["case"]["events"]),
        },
    )


def test_normal_composition_review_send_uses_xpi_ledger_and_exact_preview(sandbox_runtime):
    client, guard = sandbox_runtime
    summary, prepared = prepare_case(client, guard, TEST_PASSWORD)
    assert summary["target_submission"]["state"] == "NOT_SUBMITTED"
    assert prepared["document_state"] == "REVIEWED"
    assert len(prepared["ownership"]["document_observations"]) == 2
    assert {Decimal(item["aggregated_ownership_percent"])
            for item in prepared["ownership"]["candidates"]} == {
        Decimal("70"), Decimal("30"),
    }
    guard.writes_approved = True
    response = confirm(client, summary)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "COMPLETED"
    assert result["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
    assert result["target_submission"]["goldtier_id"] == "SYNTHETIC-GT-S3"
    assert guard.counts == {"SEARCH": 2, "SHELL": 1, "POLICY": 1, "AMEND": 0, "READBACK": 1}
    assert {item["operation"]: item["status"] for item in result["target_operations"]} == {
        "SEARCH": "NO_MATCH", "SHELL": "CREATED", "POLICY": "CREATED",
        "AMEND": "SKIPPED", "READBACK": "SUCCESS",
    }
    repeated = confirm(client, result)
    assert repeated.status_code == 409
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 1


@pytest.mark.parametrize("sandbox_runtime", ["uncertain"], indirect=True)
def test_customer_search_does_not_resolve_uncertain_policy_or_replay(sandbox_runtime):
    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    response = confirm(client, summary)
    assert response.status_code == 200
    result = response.json()
    target = result["target_submission"]
    assert target["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
    assert target["status_check_available"] is True
    assert target["goldtier_id"] == "SYNTHETIC-GT-S3"
    path = f"/api/clm/zero-touch/cases/{summary['case']['case_id']}"
    checked = client.post(path + "/target-status-check", json={
        "expected_submission_id": target["submission_id"],
    })
    assert checked.status_code == 200
    assert checked.json()["result"] == "CUSTOMER_IDENTITY_VERIFIED"
    assert "cannot prove Policy" in checked.json()["message"]
    current = client.get(path).json()
    assert current["target_submission"]["state"] == "SUBMISSION_OUTCOME_UNCERTAIN"
    assert current["target_operations"] == result["target_operations"]
    assert confirm(client, current).status_code == 409
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 1
    assert guard.counts["READBACK"] == 1


@pytest.mark.parametrize("sandbox_runtime", ["uncertain"], indirect=True)
def test_status_check_rejects_stale_submission_and_inaccessible_actor_before_search(
    sandbox_runtime,
):
    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    current = confirm(client, summary).json()
    path = f"/api/clm/zero-touch/cases/{summary['case']['case_id']}/target-status-check"
    assert client.post(path, json={"expected_submission_id": str(uuid4())}).status_code == 409
    assert guard.counts["READBACK"] == 0
    session = client.post("/api/auth/login", json={
        "user_id": "sophia-ng", "password": TEST_PASSWORD,
    }).json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    assert client.post(path, json={
        "expected_submission_id": current["target_submission"]["submission_id"],
    }).status_code == 404
    assert guard.counts["READBACK"] == 0


@pytest.mark.parametrize("sandbox_runtime", ["failed"], indirect=True)
def test_definitive_policy_rejection_retains_failure_and_customer_without_success(sandbox_runtime):
    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    result = confirm(client, summary).json()
    assert result["target_submission"]["state"] == "SUBMISSION_FAILED"
    assert result["target_submission"]["goldtier_id"] == "SYNTHETIC-GT-S3"
    assert result["target_submission"]["status_check_available"] is False
    assert result["status"] != "COMPLETED"
    assert guard.counts["SHELL"] == guard.counts["POLICY"] == 1
    assert guard.counts["READBACK"] == 0


@pytest.mark.parametrize("observation", [
    "verified", "no-match", "different-id", "multiple", "malformed", "failed",
])
def test_completed_verification_searches_retained_id_once_without_rewriting(
    sandbox_runtime, observation, monkeypatch,
):
    from urllib.parse import parse_qs, urlsplit

    from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse

    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    retained = confirm(client, summary).json()
    target = retained["target_submission"]
    assert target["verification_available"] is True
    assert target["customer_handling"] == "NEW_CREATED"
    path = f"/api/clm/zero-touch/cases/{summary['case']['case_id']}"
    before = client.get(path).json()
    calls = []
    candidate = {"goldTierId": target["goldtier_id"], "legalName": NAME,
                 "registrationNumber": UEN, "countryOfIncorporation": "SG"}

    def response(method, url, **kwargs):
        assert method == "GET"
        assert parse_qs(urlsplit(url).query) == {"goldTierID": [target["goldtier_id"]]}
        calls.append(method)
        if observation == "failed":
            raise httpx.ReadTimeout("private provider failure sentinel")
        body = [candidate]
        if observation == "no-match":
            body = []
        elif observation == "different-id":
            body = [{**candidate, "goldTierId": "OTHER-GT-ID"}]
        elif observation == "multiple":
            body = [candidate, {**candidate, "goldTierId": "OTHER-GT-ID"}]
        elif observation == "malformed":
            body = {"private": "malformed provider sentinel"}
        return GoldTierXpiHttpResponse(200, body)

    monkeypatch.setattr(guard.delegate, "request", response)
    checked = client.post(path + "/verify-goldtier", json={
        "expected_submission_id": target["submission_id"],
    })
    assert checked.status_code == 200
    result = checked.json()
    assert result["goldtier_id"] == target["goldtier_id"]
    assert result["result"] == (
        "VERIFIED" if observation == "verified"
        else "UNAVAILABLE" if observation in {"malformed", "failed"} else "REQUIRES_REVIEW"
    )
    assert result["legal_name"] == (NAME if observation == "verified" else None)
    assert "sentinel" not in checked.text
    assert calls == ["GET"]
    after = client.get(path).json()
    for key in ("case", "clm", "timeline", "version", "target_submission", "target_operations"):
        assert after[key] == before[key]
    assert guard.counts == {"SEARCH": 2, "SHELL": 1, "POLICY": 1, "AMEND": 0, "READBACK": 2}


@pytest.mark.parametrize("invalid", [
    {"expected_submission_id": "private-invalid-id-sentinel"},
    {"goldTierID": "arbitrary-private-id-sentinel"},
])
def test_completed_verification_rejects_invalid_input_without_echo(sandbox_runtime, invalid):
    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    retained = confirm(client, summary).json()
    response = client.post(
        f"/api/clm/zero-touch/cases/{summary['case']['case_id']}/verify-goldtier", json=invalid
    )
    assert response.status_code == 422
    assert response.json() == {"detail": {
        "code": "GOLDTIER_VERIFICATION_INVALID",
        "message": "The GoldTier verification request is invalid.",
    }}
    assert guard.counts["READBACK"] == 1
    assert retained["target_submission"]["state"] == "SUBMISSION_CONFIRMED"


@pytest.mark.parametrize("user,status", [("sophia-ng", 404), ("hr-admin", 404)])
def test_completed_verification_requires_current_case_access(sandbox_runtime, user, status):
    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    guard.writes_approved = True
    retained = confirm(client, summary).json()
    session = client.post("/api/auth/login", json={"user_id": user, "password": TEST_PASSWORD})
    assert session.status_code == 200
    client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
    response = client.post(
        f"/api/clm/zero-touch/cases/{summary['case']['case_id']}/verify-goldtier",
        json={"expected_submission_id": retained["target_submission"]["submission_id"]},
    )
    assert response.status_code == status
    assert guard.counts["READBACK"] == 1


def test_completed_verification_rejects_stale_submission_and_client_target_id(sandbox_runtime):
    client, guard = sandbox_runtime
    summary, _ = prepare_case(client, guard, TEST_PASSWORD)
    path = f"/api/clm/zero-touch/cases/{summary['case']['case_id']}/verify-goldtier"
    assert client.post(path, json={"expected_submission_id": str(uuid4())}).status_code == 409
    assert guard.counts["READBACK"] == 0
    guard.writes_approved = True
    retained = confirm(client, summary).json()
    assert client.post(path, json={"expected_submission_id": str(uuid4())}).status_code == 409
    response = client.post(path, json={
        "expected_submission_id": retained["target_submission"]["submission_id"],
        "goldTierID": "private-arbitrary-target-sentinel",
    })
    assert response.status_code == 422
    assert "sentinel" not in response.text
    assert guard.counts["READBACK"] == 1
