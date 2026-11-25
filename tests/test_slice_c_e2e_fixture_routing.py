"""Fail-closed routing for explicit offline Slice C browser compositions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import run_e2e

ROOT = Path(__file__).resolve().parents[1]


def test_discovery_preserves_slice_b_and_routes_slice_c_separately():
    registry, recovery, garden = {}, {}, set()
    payload = {
        "suites": [
            {
                "specs": [
                    {
                        "ok": True,
                        "file": "slice-b-registry-demo.e2e.ts",
                        "line": 1,
                        "tags": ["@slice-b-synthetic-cache"],
                    },
                    {
                        "ok": True,
                        "file": "slice-c-recovery.e2e.ts",
                        "line": 2,
                        "tags": ["@slice-c-optional-amend"],
                    },
                    {
                        "ok": True,
                        "file": "slice-c-recovery.e2e.ts",
                        "line": 3,
                        "tags": ["@slice-c-stale-policy"],
                    },
                    {
                        "ok": True,
                        "file": "slice-c-recovery.e2e.ts",
                        "line": 4,
                        "tags": ["@slice-c-retained-recovery"],
                    },
                    {
                        "ok": True,
                        "file": "slice-c-recovery.e2e.ts",
                        "line": 5,
                        "tags": ["@slice-c-search-recheck"],
                    },
                    {
                        "ok": True,
                        "file": "blocker-simulation.e2e.ts",
                        "line": 6,
                        "tags": ["@slice-c-document-refresh"],
                    },
                ]
            }
        ]
    }
    selectors = run_e2e._selectors_from_listing(
        payload,
        registry_selectors=registry,
        garden_selectors=garden,
        recovery_selectors=recovery,
    )
    assert registry == {selectors[0]: "synthetic-cache"}
    assert recovery == dict(
        zip(selectors[1:], run_e2e.RECOVERY_DEMO_MODES, strict=True)
    )
    assert garden == set()


@pytest.mark.parametrize(
    "tags",
    [
        ["@slice-c-optional-amend", "@slice-b-synthetic-cache"],
        ["@slice-c-optional-amend", "@garden-protocol"],
        ["@slice-c-optional-amend", "@slice-c-stale-policy"],
        ["@slice-c-unknown"],
    ],
)
def test_discovery_rejects_mixed_or_unknown_recovery_tags(tags):
    payload = {
        "suites": [
            {
                "specs": [
                    {
                        "ok": True,
                        "file": "slice-c-recovery.e2e.ts",
                        "line": 1,
                        "tags": tags,
                    },
                ]
            }
        ]
    }
    with pytest.raises(RuntimeError, match="fixture"):
        run_e2e._selectors_from_listing(payload)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--recovery-demo", "optional-amend"],
        ["--recovery-demo", "optional-amend", "--garden-protocol", "--grep", "Slice C"],
        [
            "--recovery-demo",
            "optional-amend",
            "--registry-demo",
            "synthetic-cache",
            "--grep",
            "Slice C",
        ],
    ],
)
def test_cli_rejects_broad_or_combined_recovery_before_startup(arguments):
    with patch.object(run_e2e, "OwnedProcess") as process:
        with pytest.raises(SystemExit):
            run_e2e.main(arguments)
        process.assert_not_called()


def test_runtime_rejects_unknown_recovery_before_startup():
    with patch.object(run_e2e, "OwnedProcess") as process:
        with pytest.raises(ValueError, match="Unknown"):
            run_e2e.run(
                backend_port=8037,
                frontend_port=5207,
                timeout_seconds=60,
                recovery_demo="unapproved",
                grep="Slice C",
            )
        process.assert_not_called()


def test_isolated_suite_dispatches_slice_c_mode_without_changing_normal_or_slice_b():
    selectors = [
        "e2e/normal.e2e.ts:1",
        "e2e/slice-b-registry-demo.e2e.ts:2",
        "e2e/slice-c-recovery.e2e.ts:3",
    ]

    def discovery(
        port, *, garden_selectors, registry_selectors, recovery_selectors, sandbox_selectors,
    ):
        assert sandbox_selectors == {}
        registry_selectors[selectors[1]] = "synthetic-cache"
        recovery_selectors[selectors[2]] = "optional-amend"
        return selectors

    with (
        patch.object(run_e2e, "_list_test_selectors", side_effect=discovery),
        patch.object(
            run_e2e, "_allocate_lifecycle_ports", return_value=[(8037, 5207)] * 3
        ),
        patch.object(run_e2e, "run", return_value=0) as dispatch,
    ):
        assert (
            run_e2e.run_isolated_suite(
                backend_port=8037, frontend_port=5207, timeout_seconds=60, headed=False
            )
            == 0
        )
    assert [item.kwargs["recovery_demo"] for item in dispatch.call_args_list] == [
        None,
        None,
        "optional-amend",
    ]
    assert [item.kwargs["registry_demo"] for item in dispatch.call_args_list] == [
        None,
        "synthetic-cache",
        None,
    ]
    assert [item.kwargs["sandbox_demo"] for item in dispatch.call_args_list] == [
        None,
        None,
        None,
    ]


def _system(monkeypatch, mode):
    monkeypatch.syspath_prepend(str(ROOT / "apps" / "backend"))
    monkeypatch.syspath_prepend(str(ROOT / "apps" / "backend" / "tests"))
    from app.config import Settings
    from app.domain.access import SYNTHETIC_USER_PROFILES
    from app.services.authentication import (
        credential_setting_key,
        generate_scrypt_password_hash,
    )
    from phase13_test_credentials import TEST_PASSWORD

    monkeypatch.setattr(
        Settings, "model_config", {**Settings.model_config, "env_file": None}
    )
    # app.main's conventional module application also stays in credential-free memory mode.
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ACRA_CONNECTOR_MODE", "mock")
    monkeypatch.setenv("GOLDTIER_CONNECTOR_MODE", "mock")
    monkeypatch.setenv("IDP_CONNECTOR_MODE", "local_pdf_text")
    monkeypatch.setenv("CLM_PERSISTENCE_MODE", "memory")
    password = TEST_PASSWORD
    encoded = generate_scrypt_password_hash(password)
    values = {}
    for user_id in [profile.user_id for profile in SYNTHETIC_USER_PROFILES] + [
        "biz-ops",
        "support-user",
    ]:
        key = credential_setting_key(user_id)
        monkeypatch.setenv(key, encoded)
        values[key.lower()] = encoded
    from app.main import create_app
    from starlette.testclient import TestClient

    from scripts.slice_c_recovery_fixture import build_offline_recovery_fixture

    settings = Settings(
        _env_file=None,
        app_env="test",
        idp_connector_mode="local_pdf_text",
        phase13_cookie_secure=False,
        **values,
    )
    fixture = build_offline_recovery_fixture(settings, mode)
    client = TestClient(
        create_app(settings=fixture.settings, onboarding_service=fixture.onboarding)
    )
    login = client.post(
        "/api/auth/login", json={"user_id": "maya-lim", "password": password}
    )
    assert login.status_code == 200
    client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    return client, fixture


def _ready_case(client):
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={
            "uen": "202400001A",
            "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
            "country_of_incorporation": "SG",
        },
    )
    assert created.status_code == 201
    record = created.json()
    case_id = record["case"]["case_id"]
    bound = client.put(
        f"/api/clm/zero-touch/cases/{case_id}/target-classification",
        json={
            "kyc_customer_type": "Company - Private",
            "client_segment": "Corporate",
            "expected_automation_version": record["version"],
            "expected_case_event_count": len(record["case"]["events"]),
        },
    )
    assert bound.status_code == 200
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/documents",
        content=(
            ROOT / "apps/backend/tests/fixtures/uat/clean-company-profile.pdf"
        ).read_bytes(),
        headers={"Content-Type": "application/pdf", "X-Document-Name": "synthetic.pdf"},
    )
    assert response.status_code == 200
    return case_id, response.json()


def _confirm(client, case_id, record):
    return client.post(
        f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
        json={
            "expected_clm_version": record["clm"]["version"],
            "expected_case_event_count": len(record["case"]["events"]),
            "expected_automation_version": record["version"],
        },
    )


def test_offline_optional_amend_uses_real_mapper_connector_and_retained_owner(
    monkeypatch,
):
    client, fixture = _system(monkeypatch, "optional-amend")
    case_id, ready = _ready_case(client)
    assert fixture.metadata()["operations"] == ["SEARCH"]
    assert ready["status"] == "WAITING_FOR_REVIEW"
    assert [item["blocker_code"] for item in ready["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED"
    ]
    response = _confirm(client, case_id, ready)
    assert response.status_code == 200
    done = response.json()
    assert done["status"] == "COMPLETED"
    assert done["case"]["goldtier_result"]["amend_status"] == "AMEND_NOT_REQUIRED"
    assert (
        next(
            item for item in done["target_operations"] if item["operation"] == "AMEND"
        )["status"]
        == "SKIPPED"
    )
    assert fixture.metadata()["operations"] == [
        "SEARCH",
        "SEARCH",
        "SHELL",
        "POLICY",
        "READBACK",
    ]
    assert fixture.metadata()["external_calls"] == 0
    assert (
        client.post(f"/api/clm/zero-touch/cases/{case_id}/resume").json()["version"]
        == done["version"]
    )
    assert fixture.metadata()["operations"] == [
        "SEARCH",
        "SEARCH",
        "SHELL",
        "POLICY",
        "READBACK",
    ]
    # Counters contain no URL, request metadata, credentials, customer or provider body.
    assert set(fixture.metadata()) == {
        "fixture",
        "classification",
        "external_calls",
        "operations",
        "registry_operations",
        "finalization_attempts",
    }
    assert type(fixture.onboarding._goldtier).__name__ == "GoldTierXpiSandboxConnector"
    assert (
        type(fixture.onboarding._goldtier_mapper).__name__ == "GoldTierXpiRequestMapper"
    )


def test_offline_retained_recovery_resumes_without_target_replay(monkeypatch):
    client, fixture = _system(monkeypatch, "retained-recovery")
    case_id, ready = _ready_case(client)
    pending = _confirm(client, case_id, ready)
    assert pending.status_code == 200
    assert pending.json()["status"] == "RECOVERY_PENDING"
    operations = fixture.metadata()["operations"]
    assert operations == ["SEARCH", "SEARCH", "SHELL", "POLICY", "READBACK"]
    completed = client.post(f"/api/clm/zero-touch/cases/{case_id}/resume")
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert fixture.metadata()["operations"] == operations


def test_offline_stale_policy_is_bound_at_creation_and_rebound_by_owner(monkeypatch):
    client, fixture = _system(monkeypatch, "stale-policy")
    case_id, ready = _ready_case(client)
    assert ready["case"]["policy_rebind"]["configuration_status"] == "REQUIRES_REBIND"
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/policy-rebind",
        json={
            "rationale": "Replace retained synthetic legacy target configuration.",
            "expected_automation_version": ready["version"],
            "expected_clm_version": ready["clm"]["version"],
            "expected_case_event_count": len(ready["case"]["events"]),
        },
    )
    assert response.status_code == 200
    rebound = response.json()
    assert rebound["case"]["policy_snapshot_revision"] == 2
    assert (
        rebound["case"]["policy_rebind"]["configuration_status"]
        == "CURRENT_ACCEPTED_POC"
    )
    assert fixture.metadata()["operations"] == ["SEARCH"]
    assert _confirm(client, case_id, rebound).json()["status"] == "COMPLETED"


def test_offline_transport_forbids_amend_and_real_destinations(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "apps" / "backend"))
    from scripts.slice_c_recovery_fixture import OfflineXpiRecoveryTransport

    transport = OfflineXpiRecoveryTransport()
    for url in [
        "https://slice-c-offline.invalid/synthetic-offline/gt-xpi/v1/customers/amendCustomer",
        "https://outside.invalid/synthetic-offline/gt-xpi/v1/customers/create",
    ]:
        with pytest.raises(ValueError, match="fixture"):
            transport.request(
                "POST",
                url,
                headers={},
                json_body={},
                timeout_seconds=1,
                max_response_bytes=4096,
            )
    assert transport.operations == []


def test_offline_search_failure_recheck_uses_existing_identity_owner(monkeypatch):
    client, fixture = _system(monkeypatch, "search-recheck")
    case_id, failed = _ready_case(client)
    assert failed["status"] == "TECHNICAL_FAILURE"
    assert failed["clm"]["target_search_checkpoint"]["disposition"] == "FAILED"
    assert failed["active_exceptions"] == []
    assert fixture.metadata()["operations"] == ["SEARCH"]
    corrected = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/registry-identity",
        json={
            "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
            "registration_number": "202400001A",
            "country_of_incorporation": "SG",
            "choice": "OTHER",
            "expected_automation_version": failed["version"],
            "expected_clm_version": failed["clm"]["version"],
            "expected_case_event_count": len(failed["case"]["events"]),
        },
    )
    assert corrected.status_code == 200
    current = corrected.json()
    assert current["case"]["case_id"] == case_id
    assert current["clm"]["target_search_checkpoint"]["disposition"] == "NO_MATCH"
    assert current["technical_failure"] is None
    assert fixture.metadata()["operations"] == ["SEARCH", "SEARCH"]


def test_offline_fixture_never_constructs_http_transport_and_rejects_normal_composition(
    monkeypatch,
):
    monkeypatch.syspath_prepend(str(ROOT / "apps" / "backend"))
    from app import composition
    from app.config import Settings

    from scripts.slice_c_recovery_fixture import build_offline_recovery_fixture

    def forbidden_transport():
        pytest.fail(
            "An offline fixture must never construct an external HTTP transport"
        )

    monkeypatch.setattr(composition, "HttpxGoldTierXpiTransport", forbidden_transport)
    fixture = build_offline_recovery_fixture(
        Settings(_env_file=None, app_env="test", idp_connector_mode="local_pdf_text"),
        "optional-amend",
    )
    assert fixture.metadata()["external_calls"] == 0
    with pytest.raises(ValueError, match="isolated"):
        build_offline_recovery_fixture(
            Settings(_env_file=None, app_env="development"), "optional-amend"
        )
    with pytest.raises(ValueError, match="Unknown"):
        build_offline_recovery_fixture(
            Settings(_env_file=None, app_env="test", idp_connector_mode="local_pdf_text"),
            "document-refresh",
        )
