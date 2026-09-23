from __future__ import annotations

from datetime import UTC, datetime

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError

from app.domain.access import AuthenticatedActor, Role, TeamId, UserProfile
from app.domain.policy import (
    DecimalPolicyValue,
    StringListPolicyValue,
    StringPolicyValue,
    validate_showcase_plain_text_value,
)
from app.main import create_app
from app.services.admin_repository import AdministrationConflictError, InMemoryPolicyRepository
from app.services.policy_management import PolicyManagementService


def _actor(role: Role) -> AuthenticatedActor:
    return AuthenticatedActor(
        profile=UserProfile(
            user_id="actor-user",
            display_name="Actor User",
            role=role,
            team_id=(
                TeamId.TEAM_A
                if role in {Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER}
                else None
            ),
        )
    )


def test_default_catalogue_is_exact_and_snapshot_is_typed() -> None:
    service = PolicyManagementService(
        InMemoryPolicyRepository(), clock=lambda: datetime(2026, 9, 9, tzinfo=UTC)
    )
    catalogue = service.catalogue()

    assert [rule.policy_id for rule in catalogue.rules] == [
        "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD",
        "OWNERSHIP_UBO_THRESHOLD_PERCENT",
        "OWNERSHIP_UBO_COMPARATOR",
        "REGISTRY_SUPPORTED_JURISDICTIONS",
        "REGISTRY_PROVIDER",
        "DOCUMENT_SUPPORTED_MEDIA_TYPES",
        "WORKFLOW_SUPPORTED_STAGES",
        "RECONCILIATION_SOURCE_PRECEDENCE",
    ]
    snapshot = service.case_snapshot()
    assert str(snapshot.idp_review_confidence_threshold) == "0.85"
    assert str(snapshot.ubo_threshold_percent) == "25.000000"


def test_showcase_policy_is_forced_non_runtime_and_cas_is_strict() -> None:
    repository = InMemoryPolicyRepository()
    service = PolicyManagementService(repository)
    director = _actor(Role.DIRECTOR)
    initial = service.catalogue()
    created = service.create_showcase(
        director,
        expected_catalogue_version=initial.version,
        policy_id="SHOWCASE_NOTE",
        category="Demonstration",
        name="Showcase note",
        description="Visible demonstration value only.",
        value=StringPolicyValue(value="Visible only"),
    )
    assert created.rule("SHOWCASE_NOTE").enforcement == "DISPLAY_SHOWCASE_ONLY"  # type: ignore[union-attr]
    with pytest.raises(AdministrationConflictError):
        service.create_showcase(
            director,
            expected_catalogue_version=initial.version,
            policy_id="ANOTHER_SHOWCASE",
            category="Demonstration",
            name="Another showcase",
            description="Must lose the stale catalogue race.",
            value=StringPolicyValue(value="No effect"),
        )


def test_policy_decimal_rejects_nan_infinity_and_excess_precision() -> None:
    for value in ("NaN", "Infinity", "0.1234567"):
        with pytest.raises(ValidationError):
            DecimalPolicyValue(value=value)


@pytest.mark.parametrize(
    "value",
    [
        "__import__('os')",
        "eval(x)",
        "exec(x)",
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "a == b",
        "${value}",
        "{{value}}",
        "lambda x: x",
        "`command`",
        "a | b",
        "a && b",
        "a; b",
    ],
)
def test_showcase_plain_text_validator_rejects_expression_syntax(value: str) -> None:
    with pytest.raises(ValueError):
        validate_showcase_plain_text_value(StringPolicyValue(value=value))
    with pytest.raises(ValueError):
        validate_showcase_plain_text_value(StringListPolicyValue(value=("Safe", value)))


@pytest.mark.parametrize(
    "value",
    [
        "Enhanced Review",
        "MANUAL_REVIEW",
        "Level-2",
        "SG",
        "ACRA",
        "25%",
        "Risk: Medium",
        "application/pdf",
    ],
)
def test_showcase_plain_text_validator_accepts_normal_display_values(value: str) -> None:
    validate_showcase_plain_text_value(StringPolicyValue(value=value))
    validate_showcase_plain_text_value(StringListPolicyValue(value=(value,)))


def _client_for(user_id: str) -> tuple[RawTestClient, str]:
    client = RawTestClient(create_app(ordinary_test_settings()))
    login = client.post("/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD})
    assert login.status_code == 200
    return client, login.json()["csrf_token"]


@pytest.mark.parametrize(
    "value",
    [
        "__import__('os')",
        "eval(x)",
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "${value}",
        "a && b",
    ],
)
def test_showcase_create_api_rejects_hostile_strings_without_echo(value: str) -> None:
    client, csrf = _client_for("ethan-tan")
    catalogue = client.get("/api/policies").json()

    response = client.post(
        "/api/policies",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": catalogue["version"],
            "policy_id": "SHOWCASE_RULE",
            "category": "Demo",
            "name": "Showcase rule",
            "description": "Display-only demonstration rule.",
            "value": {"type": "STRING", "value": value},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "POLICY_REQUEST_INVALID"
    assert value not in response.text


@pytest.mark.parametrize("user_id", ["maya-lim", "ethan-tan", "olivia-koh", "hr-admin"])
def test_all_authenticated_roles_can_read_policy_catalogue(user_id: str) -> None:
    client, _ = _client_for(user_id)
    response = client.get("/api/policies")
    assert response.status_code == 200
    assert len(response.json()["rules"]) == 8


@pytest.mark.parametrize("user_id", ["ethan-tan", "olivia-koh"])
def test_policy_mutators_can_create_update_and_reset_allowed_rules(user_id: str) -> None:
    client, csrf = _client_for(user_id)
    catalogue = client.get("/api/policies").json()
    created = client.post(
        "/api/policies",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": catalogue["version"],
            "policy_id": "SHOWCASE_RULE",
            "category": "Demo",
            "name": "Showcase rule",
            "description": "Display-only demonstration rule.",
            "value": {"type": "STRING", "value": "visible"},
        },
    )
    assert created.status_code == 201
    showcase = next(
        item for item in created.json()["rules"] if item["policy_id"] == "SHOWCASE_RULE"
    )
    assert showcase["enforcement"] == "DISPLAY_SHOWCASE_ONLY"

    catalogue = created.json()
    rule = next(
        item
        for item in catalogue["rules"]
        if item["policy_id"] == "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD"
    )
    updated = client.patch(
        f"/api/policies/{rule['policy_id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": catalogue["version"],
            "expected_rule_version": rule["version"],
            "value": {"type": "DECIMAL", "value": "0.90"},
        },
    )
    assert updated.status_code == 200
    changed = next(
        item for item in updated.json()["rules"] if item["policy_id"] == rule["policy_id"]
    )
    assert changed["value"]["value"] == "0.90"

    stale = client.patch(
        f"/api/policies/{rule['policy_id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": catalogue["version"],
            "expected_rule_version": rule["version"],
            "value": {"type": "DECIMAL", "value": "0.80"},
        },
    )
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "POLICY_VERSION_CONFLICT"

    reset = client.post(
        f"/api/policies/{rule['policy_id']}/reset",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": updated.json()["version"],
            "expected_rule_version": changed["version"],
            "confirmation": "RESET_POLICY_DEFAULT",
        },
    )
    assert reset.status_code == 200
    reset_rule = next(
        item for item in reset.json()["rules"] if item["policy_id"] == rule["policy_id"]
    )
    assert reset_rule["value"] == reset_rule["default_value"]

    reset_all = client.post(
        "/api/policies/reset",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": reset.json()["version"],
            "confirmation": "RESET_ALL_POLICY_DEFAULTS",
        },
    )
    assert reset_all.status_code == 200
    assert next(
        item for item in reset_all.json()["rules"] if item["policy_id"] == rule["policy_id"]
    )["value"] == rule["default_value"]


def test_policy_edit_binds_only_to_cases_created_after_successful_cas() -> None:
    client, csrf = _client_for("ethan-tan")
    before = client.post(
        "/api/onboarding/cases",
        headers={"X-CSRF-Token": csrf},
        json={"uen": "202400001A"},
    )
    assert before.status_code == 201
    before_case = before.json()
    assert before_case["policy_snapshot"]["idp_review_confidence_threshold"] == "0.85"

    catalogue = client.get("/api/policies").json()
    rule = next(
        item
        for item in catalogue["rules"]
        if item["policy_id"] == "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD"
    )
    updated = client.patch(
        f"/api/policies/{rule['policy_id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": catalogue["version"],
            "expected_rule_version": rule["version"],
            "value": {"type": "DECIMAL", "value": "0.90"},
        },
    )
    assert updated.status_code == 200

    after = client.post(
        "/api/onboarding/cases",
        headers={"X-CSRF-Token": csrf},
        json={"uen": "202400002B"},
    )
    assert after.status_code == 201
    assert after.json()["policy_snapshot"]["idp_review_confidence_threshold"] == "0.90"
    retained = client.get(f"/api/onboarding/cases/{before_case['case_id']}")
    assert retained.status_code == 200
    assert retained.json()["policy_snapshot"] == before_case["policy_snapshot"]


@pytest.mark.parametrize("user_id", ["maya-lim", "hr-admin"])
def test_read_only_roles_cannot_use_any_policy_mutation(user_id: str) -> None:
    client, csrf = _client_for(user_id)
    catalogue = client.get("/api/policies").json()
    rule = next(
        item
        for item in catalogue["rules"]
        if item["policy_id"] == "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD"
    )
    attempts = [
        ("post", "/api/policies", {
            "expected_catalogue_version": catalogue["version"],
            "policy_id": "SHOWCASE_RULE",
            "category": "Demo",
            "name": "Showcase rule",
            "description": "Display-only demonstration rule.",
            "value": {"type": "STRING", "value": "visible"},
        }),
        ("patch", f"/api/policies/{rule['policy_id']}", {
            "expected_catalogue_version": catalogue["version"],
            "expected_rule_version": rule["version"],
            "value": {"type": "DECIMAL", "value": "0.90"},
        }),
        ("post", f"/api/policies/{rule['policy_id']}/reset", {
            "expected_catalogue_version": catalogue["version"],
            "expected_rule_version": rule["version"],
            "confirmation": "RESET_POLICY_DEFAULT",
        }),
        ("post", "/api/policies/reset", {
            "expected_catalogue_version": catalogue["version"],
            "confirmation": "RESET_ALL_POLICY_DEFAULTS",
        }),
    ]
    for method, path, body in attempts:
        response = getattr(client, method)(
            path,
            headers={"X-CSRF-Token": csrf},
            json=body,
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "POLICY_MUTATION_FORBIDDEN"
