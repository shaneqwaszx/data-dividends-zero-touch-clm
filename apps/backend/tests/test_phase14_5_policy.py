from __future__ import annotations

from datetime import UTC, datetime

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError

from app.domain.access import AuthenticatedActor, Role, TeamId, UserProfile
from app.domain.policy import (
    BooleanPolicyValue,
    DecimalPolicyValue,
    IntegerPolicyValue,
    StringListPolicyValue,
    StringPolicyValue,
    legacy_phase13_policy_snapshot,
    validate_showcase_plain_text_value,
)
from app.main import create_app
from app.services.admin_repository import AdministrationConflictError, InMemoryPolicyRepository
from app.services.policy_management import (
    PolicyManagementService,
    PolicyValidationError,
    default_policy_catalogue,
)


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
        "ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD",
        "ENTITY_RESOLUTION_REVIEW_THRESHOLD",
        "ENTITY_RESOLUTION_AMBIGUITY_MARGIN",
        "ENTITY_RESOLUTION_IDENTIFIER_WEIGHT",
        "ENTITY_RESOLUTION_NAME_WEIGHT",
        "ENTITY_RESOLUTION_ADDRESS_WEIGHT",
        "ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT",
        "ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT",
        "UBO_ADVISORY_LIKELY_THRESHOLD",
        "UBO_ADVISORY_UNLIKELY_THRESHOLD",
        "MOCK_RISK_MEDIUM_THRESHOLD",
        "MOCK_RISK_HIGH_THRESHOLD",
        "MOCK_RISK_BLOCKS_READINESS",
        "GOLDTIER_KYC_CUSTOMER_TYPE",
        "GOLDTIER_CLIENT_SEGMENT",
        "GOLDTIER_CUSTOMER_EXTERNAL_SYSTEM",
        "GOLDTIER_REGISTRATION_TYPE",
        "GOLDTIER_POLICY",
        "GOLDTIER_BOOKING_ENTITY",
        "GOLDTIER_ACCOUNT_ENTITY_TYPE",
        "GOLDTIER_PRODUCT_TYPE",
    ]
    snapshot = service.case_snapshot()
    assert str(snapshot.idp_review_confidence_threshold) == "0.85"
    assert str(snapshot.ubo_threshold_percent) == "25.000000"
    assert snapshot.intelligence is not None
    assert str(snapshot.intelligence.entity_resolution_auto_match_threshold) == "0.85"
    assert str(snapshot.intelligence.entity_resolution_review_threshold) == "0.60"
    assert str(snapshot.intelligence.entity_resolution_weights.identifier) == "0.55"
    assert snapshot.intelligence.mock_risk_medium_threshold == 30
    assert snapshot.intelligence.mock_risk_high_threshold == 60
    assert snapshot.intelligence.mock_risk_blocks_readiness is False
    assert legacy_phase13_policy_snapshot().intelligence is None


def test_intelligence_policy_snapshot_is_case_bound_and_validated_as_one_policy() -> None:
    repository = InMemoryPolicyRepository()
    service = PolicyManagementService(repository, clock=lambda: datetime(2026, 9, 9, tzinfo=UTC))
    actor = _actor(Role.DIRECTOR)
    before = service.case_snapshot()
    catalogue = service.catalogue()
    probable = catalogue.rule("ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD")
    assert probable is not None

    service.update(
        actor,
        probable.policy_id,
        expected_catalogue_version=catalogue.version,
        expected_rule_version=probable.version,
        value=DecimalPolicyValue(value="0.90"),
    )
    after = service.case_snapshot()

    assert before.intelligence is not None and after.intelligence is not None
    assert str(before.intelligence.entity_resolution_auto_match_threshold) == "0.85"
    assert str(after.intelligence.entity_resolution_auto_match_threshold) == "0.90"
    assert before.catalogue_version != after.catalogue_version


def test_mock_risk_blocks_readiness_defaults_false_and_is_case_bound() -> None:
    service = PolicyManagementService(InMemoryPolicyRepository())
    rule = service.get("MOCK_RISK_BLOCKS_READINESS")

    assert rule.value == BooleanPolicyValue(value=False)
    assert rule.enforcement == "RUNTIME_ENFORCED"
    before = service.case_snapshot()
    service.update(
        _actor(Role.DIRECTOR),
        rule.policy_id,
        expected_catalogue_version=service.catalogue().version,
        expected_rule_version=rule.version,
        value=BooleanPolicyValue(value=True),
    )
    after = service.case_snapshot()

    assert before.intelligence is not None and after.intelligence is not None
    assert before.intelligence.mock_risk_blocks_readiness is False
    assert after.intelligence.mock_risk_blocks_readiness is True


def test_mock_risk_band_thresholds_are_editable_integer_rules() -> None:
    service = PolicyManagementService(InMemoryPolicyRepository())
    actor = _actor(Role.DIRECTOR)
    catalogue = service.catalogue()
    medium = service.get("MOCK_RISK_MEDIUM_THRESHOLD")
    updated = service.update(
        actor,
        medium.policy_id,
        expected_catalogue_version=catalogue.version,
        expected_rule_version=medium.version,
        value=IntegerPolicyValue(value=35),
    )

    assert service.case_snapshot().intelligence.mock_risk_medium_threshold == 35
    assert updated.rule(medium.policy_id).value == IntegerPolicyValue(value=35)  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("policy_id", "value"),
    [
        ("ENTITY_RESOLUTION_REVIEW_THRESHOLD", DecimalPolicyValue(value="0.90")),
        ("UBO_ADVISORY_UNLIKELY_THRESHOLD", DecimalPolicyValue(value="0.70")),
        ("MOCK_RISK_MEDIUM_THRESHOLD", IntegerPolicyValue(value=70)),
        ("ENTITY_RESOLUTION_NAME_WEIGHT", DecimalPolicyValue(value="0.30")),
    ],
)
def test_policy_update_rejects_cross_rule_invalid_intelligence_catalogue(
    policy_id: str,
    value: DecimalPolicyValue | IntegerPolicyValue,
) -> None:
    service = PolicyManagementService(InMemoryPolicyRepository())
    rule = service.get(policy_id)

    with pytest.raises(PolicyValidationError):
        service.update(
            _actor(Role.DIRECTOR),
            policy_id,
            expected_catalogue_version=service.catalogue().version,
            expected_rule_version=rule.version,
            value=value,
        )


def test_exact_legacy_policy_catalogue_is_upgraded_once_with_an_audit_event() -> None:
    repository = InMemoryPolicyRepository()
    now = datetime(2026, 9, 9, tzinfo=UTC)
    current = default_policy_catalogue(now)
    repository.create(current.model_copy(update={"rules": current.rules[:8]}))

    first = PolicyManagementService(repository, clock=lambda: now).catalogue()
    second = PolicyManagementService(repository, clock=lambda: now).catalogue()

    assert len(first.rules) == 29
    assert first.version == 2
    assert first.audit_events[-1].action == "POLICY_CATALOGUE_MIGRATED"
    assert second == first


def test_partial_intelligence_policy_catalogue_fails_closed() -> None:
    repository = InMemoryPolicyRepository()
    now = datetime(2026, 9, 9, tzinfo=UTC)
    current = default_policy_catalogue(now)
    repository.create(current.model_copy(update={"rules": current.rules[:-1]}))

    with pytest.raises(PolicyValidationError):
        PolicyManagementService(repository, clock=lambda: now)


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
    assert len(response.json()["rules"]) == 29


def test_target_policy_api_exposes_fixed_sponsor_documented_authority() -> None:
    client, csrf = _client_for("olivia-koh")
    catalogue = client.get("/api/policies").json()
    rule = next(
        item for item in catalogue["rules"] if item["policy_id"] == "GOLDTIER_POLICY"
    )

    assert rule["value"]["value"] == "Singapore"
    assert rule["authority"] == "SPONSOR_DOCUMENTED"
    assert rule["default_authority"] == "SPONSOR_DOCUMENTED"
    assert rule["allowed_values"] == ["Singapore"]

    updated = client.patch(
        "/api/policies/GOLDTIER_POLICY",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_catalogue_version": catalogue["version"],
            "expected_rule_version": rule["version"],
            "value": {"type": "STRING", "value": "SPONSOR VALUE"},
            "authority": "SPONSOR_SUPPLIED",
        },
    )

    assert updated.status_code == 422
    assert updated.json()["detail"]["code"] == "POLICY_REQUEST_INVALID"


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
    assert (
        next(item for item in reset_all.json()["rules"] if item["policy_id"] == rule["policy_id"])[
            "value"
        ]
        == rule["default_value"]
    )


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
        (
            "post",
            "/api/policies",
            {
                "expected_catalogue_version": catalogue["version"],
                "policy_id": "SHOWCASE_RULE",
                "category": "Demo",
                "name": "Showcase rule",
                "description": "Display-only demonstration rule.",
                "value": {"type": "STRING", "value": "visible"},
            },
        ),
        (
            "patch",
            f"/api/policies/{rule['policy_id']}",
            {
                "expected_catalogue_version": catalogue["version"],
                "expected_rule_version": rule["version"],
                "value": {"type": "DECIMAL", "value": "0.90"},
            },
        ),
        (
            "post",
            f"/api/policies/{rule['policy_id']}/reset",
            {
                "expected_catalogue_version": catalogue["version"],
                "expected_rule_version": rule["version"],
                "confirmation": "RESET_POLICY_DEFAULT",
            },
        ),
        (
            "post",
            "/api/policies/reset",
            {
                "expected_catalogue_version": catalogue["version"],
                "confirmation": "RESET_ALL_POLICY_DEFAULTS",
            },
        ),
    ]
    for method, path, body in attempts:
        response = getattr(client, method)(
            path,
            headers={"X-CSRF-Token": csrf},
            json=body,
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "POLICY_MUTATION_FORBIDDEN"
