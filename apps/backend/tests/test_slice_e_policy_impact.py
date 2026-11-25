"""Slice E failing-first contracts over the existing read-only policy owner."""

from copy import deepcopy
from decimal import Decimal

import pytest
from test_phase24c_policy import DIRECTOR, HR, draft, service, submit

from app.domain.policy import (
    IDP_POLICY_ID,
    UBO_POLICY_ID,
    BooleanPolicyValue,
    DecimalPolicyValue,
    IntegerPolicyValue,
)
from app.services.admin_repository import AdministrationConflictError
from app.services.policy_management import PolicyValidationError


def impact(changes):
    owner = service()
    catalogue = owner.create_proposal(
        HR,
        expected_catalogue_version=owner.catalogue().version,
        changes=changes,
        reason="Synthetic explainable policy impact proposal",
    )
    return owner, catalogue, owner.proposal_impact(catalogue.proposals[-1].proposal_id)


def scenario(result, fixture_id):
    return next(row for row in result["advisor"]["scenarios"] if row["fixture_id"] == fixture_id)


def test_document_change_has_named_semantic_transition_and_synthetic_delta():
    owner, catalogue, result = impact(
        {
            "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": DecimalPolicyValue(value="0.92"),
        }
    )
    row = scenario(result, "DOCUMENT_CONFIDENCE_0.90")
    assert (row["before"]["label"], row["after"]["label"]) == ("AUTO_CONFIRMED", "REVIEW_REQUIRED")
    change = result["changes"][0]
    assert change["name"] and change["direction"] == "INCREASE"
    assert change["materiality"] == "HIGH"
    assert "DOCUMENT_FIXTURE_CROSSES_AUTO_CONFIRM_THRESHOLD" in change["reason_codes"]
    assert result["advisor"]["automation_delta"]["automatic_document_confirmations"]["delta"] < 0
    assert owner.catalogue() == catalogue
    assert result == owner.proposal_impact(catalogue.proposals[-1].proposal_id)


def test_registry_age_and_negative_ttl_expire_at_equality():
    _, _, result = impact(
        {
            "REGISTRY_FRESHNESS_DAYS": IntegerPolicyValue(value=30),
            "REGISTRY_NOT_FOUND_TTL_SECONDS": IntegerPolicyValue(value=60),
        }
    )
    stale = scenario(result, "REGISTRY_AGE_45_DAYS")
    assert (stale["before"]["label"], stale["after"]["label"]) == (
        "REUSE_FRESH",
        "REFRESH_REQUIRED",
    )
    assert scenario(result, "REGISTRY_PROPOSED_EXPIRY")["after"]["label"] == "REFRESH_REQUIRED"
    assert (
        scenario(result, "NEGATIVE_PROPOSED_EXPIRY")["after"]["label"] == "NEGATIVE_CACHE_EXPIRED"
    )
    assert result["advisor"]["registry_reuse_direction"] == "MORE_RESTRICTIVE_REUSE"


def test_ownership_consumes_decimal_aggregation_and_retains_review():
    _, _, result = impact({"OWNERSHIP_UBO_THRESHOLD_PERCENT": DecimalPolicyValue(value="30")})
    row = scenario(result, "OWNERSHIP_DIRECT_27")
    assert row["before"]["label"] == "PROVISIONAL_UBO_CANDIDATE"
    assert row["after"]["label"] == "BELOW_PROVISIONAL_THRESHOLD"
    assert scenario(result, "OWNERSHIP_MULTIPATH")["before"]["value"] == "27.00"
    incomplete = scenario(result, "OWNERSHIP_INCOMPLETE")
    assert incomplete["before"]["label"] == incomplete["after"]["label"] == "REVIEW_REQUIRED"
    assert "INCOMPLETE_LEGAL_ENTITY" in incomplete["before"]["reason_codes"]


def test_classifier_exposes_authoritative_scores_reasons_and_metric_delta():
    _, _, result = impact({"EVIDENCE_CLASSIFICATION_THRESHOLD": DecimalPolicyValue(value="0.95")})
    rows = [r for r in result["advisor"]["scenarios"] if r["stage"] == "CLASSIFIER"]
    assert len(rows) == 14
    assert all(r["before"]["score"] is not None and r["after"]["threshold"] == "0.95" for r in rows)
    assert any(r["before"]["label"] != r["after"]["label"] for r in rows)
    assert result["advisor"]["classifier_metric_delta"]["micro_f1"] < 0
    assert (
        result["before"]["classifier"]["benchmark_hash"]
        == result["after"]["classifier"]["benchmark_hash"]
    )


def test_unsimulated_intelligence_is_unknown_not_zero_materiality():
    _, _, result = impact({"MOCK_RISK_BLOCKS_READINESS": BooleanPolicyValue(value=True)})
    row = result["changes"][0]
    assert row["assessment"] == "NOT_ASSESSED"
    assert row["materiality"] == "NOT_ASSESSED"
    assert row["scenario_ids"] == []
    assert "IMPACT_NOT_ASSESSED" in row["reason_codes"]
    assert any(
        u["concept"] == "GoldTier approval" and u["status"] == "NOT_ASSESSED"
        for u in result["advisor"]["unknown_impacts"]
    )


def test_stale_impact_uses_retained_base_and_never_makes_proposal_current():
    owner = service()
    first = submit(owner, draft(owner))
    pending = first.proposals[-1]
    second = owner.create_proposal(
        HR,
        expected_catalogue_version=first.version,
        changes={"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": DecimalPolicyValue(value="0.92")},
        reason="Second synthetic proposal on the original active base",
    )
    old = second.proposals[-1]
    latest = owner.decide_proposal(
        DIRECTOR,
        pending.proposal_id,
        approve=True,
        expected_catalogue_version=second.version,
        expected_proposal_version=pending.version,
        reason="Independent activation changes current active version",
    )
    result = owner.proposal_impact(old.proposal_id)
    assert result["stale"] is True
    assert result["comparison_basis"] == "RETAINED_PROPOSAL_BASE"
    assert result["before"]["runtime"]["document_auto_confirm"] == [False, True, True]
    assert result["changes"][0]["current"]["value"] == "0.90"
    assert result["changes"][0]["base"]["value"] == "0.85"
    assert "STALE_PROPOSAL_BASE" in result["advisor"]["reason_codes"]
    with pytest.raises(AdministrationConflictError):
        owner.submit_proposal(
            HR,
            old.proposal_id,
            expected_catalogue_version=latest.version,
            expected_proposal_version=old.version,
        )
    assert owner.catalogue() == latest


def test_fixture_bounds_and_same_payload_are_deterministic():
    owner, catalogue, result = impact(
        {"OWNERSHIP_UBO_THRESHOLD_PERCENT": DecimalPolicyValue(value="100")}
    )
    assert result["advisor"]["fixture_set_id"] == "SYNTHETIC_POLICY_IMPACT_V1"
    assert len(result["advisor"]["scenarios"]) <= 64
    assert len(result["advisor"]["fixture_set_hash"]) == 64
    assert len(result["comparison_identity"]) == 64
    assert result["proposal_version"] == catalogue.proposals[-1].version
    assert result["catalogue_version"] == catalogue.version
    assert result == deepcopy(owner.proposal_impact(catalogue.proposals[-1].proposal_id))


@pytest.mark.parametrize("threshold", ["0", "1"])
def test_document_boundary_and_semantic_blockers_remain_authoritative(threshold):
    _, _, result = impact({IDP_POLICY_ID: DecimalPolicyValue(value=threshold)})
    assert scenario(result, "DOCUMENT_PROPOSED_AT")["after"]["label"] == "AUTO_CONFIRMED"
    for identity, code in (
        ("DOCUMENT_MISSING", "DOCUMENT_REQUIRED_FIELD_MISSING"),
        ("DOCUMENT_CONFLICT", "DOCUMENT_SOURCE_CONFLICT"),
        ("DOCUMENT_TEXT_UNAVAILABLE", "DOCUMENT_TEXT_UNAVAILABLE"),
        ("DOCUMENT_SUPERSEDED", "DOCUMENT_REVIEW_STATE_INVALID"),
    ):
        outcome = scenario(result, identity)["after"]
        assert outcome["label"] == "REVIEW_REQUIRED" and code in outcome["reason_codes"]


def test_zero_ownership_is_unknown_not_false_or_zero():
    _, _, result = impact({UBO_POLICY_ID: DecimalPolicyValue(value="0")})
    assert result["changes"][0]["assessment"] == "NOT_ASSESSED"
    assert result["after"]["runtime"]["ownership_numeric_candidates"] == [None, None, None]
    count = result["advisor"]["automation_delta"]["provisional_ubo_candidates"]
    assert count["before"] is not None and count["after"] is None and count["delta"] is None
    assert all(
        r["after"]["provisional_candidate"] is None
        for r in result["advisor"]["scenarios"]
        if r["stage"] == "OWNERSHIP"
    )


def test_positive_ownership_equality_and_safe_declaration():
    _, _, result = impact({UBO_POLICY_ID: DecimalPolicyValue(value="30")})
    assert (
        scenario(result, "OWNERSHIP_PROPOSED_BELOW")["after"]["label"]
        == "BELOW_PROVISIONAL_THRESHOLD"
    )
    assert (
        scenario(result, "OWNERSHIP_PROPOSED_AT")["after"]["label"] == "PROVISIONAL_UBO_CANDIDATE"
    )
    assert (
        scenario(result, "OWNERSHIP_PROPOSED_ABOVE")["after"]["label"]
        == "PROVISIONAL_UBO_CANDIDATE"
    )
    assert scenario(result, "OWNERSHIP_DECLARATION_60")["after"]["value"] == "60.0"
    assert scenario(result, "OWNERSHIP_DECLARATION_40")["after"]["value"] == "40.0"


def test_registry_both_sides_of_expiry_and_minimum_negative_ttl():
    _, _, result = impact({"REGISTRY_NOT_FOUND_TTL_SECONDS": IntegerPolicyValue(value=1)})
    assert (
        scenario(result, "NEGATIVE_PROPOSED_EXPIRY_BELOW")["after"]["label"] == "NEGATIVE_CACHE_HIT"
    )
    for suffix in ("", "_ABOVE"):
        assert (
            scenario(result, "NEGATIVE_PROPOSED_EXPIRY" + suffix)["after"]["label"]
            == "NEGATIVE_CACHE_EXPIRED"
        )
    assert scenario(result, "REGISTRY_BASE_EXPIRY_BELOW")["before"]["cache_reuse"] is True
    assert scenario(result, "REGISTRY_BASE_EXPIRY")["before"]["cache_reuse"] is False


def test_unbound_classifier_never_becomes_ownership_or_automation():
    _, _, result = impact({"EVIDENCE_CLASSIFICATION_THRESHOLD": DecimalPolicyValue(value="0")})
    unbound = scenario(result, "CLASSIFIER_BENCHMARK_11")
    assert unbound["after"]["label"] == "UNKNOWN"
    assert unbound["after"]["automatic"] is None and unbound["after"]["review_required"] is None
    assert "EVIDENCE_ENTITY_BINDING_UNKNOWN" in unbound["after"]["reason_codes"]
    assert len(result["changes"][0]["coupled_policy_ids"]) == 3


def test_only_score_change_is_low_and_identical_forecasts_have_explicit_zero():
    _, _, result = impact(
        {
            "EVIDENCE_KIND_WEIGHT": DecimalPolicyValue(value="0.40"),
            "EVIDENCE_CONFIDENCE_WEIGHT": DecimalPolicyValue(value="0.35"),
        }
    )
    assert all(c["materiality"] == "LOW" for c in result["changes"])
    assert all(v["delta"] == 0 for v in result["advisor"]["automation_delta"].values())
    assert all(c["scenario_ids"] for c in result["changes"])


def test_advisor_reuses_engines_and_never_writes_repository(monkeypatch):
    import app.services.policy_impact_advisor as advisor

    owner, catalogue, _ = impact({UBO_POLICY_ID: DecimalPolicyValue(value="30")})
    called = []
    original = advisor.build_ownership_candidates

    def observed(*args, **kwargs):
        called.append(kwargs["threshold_percent"])
        return original(*args, **kwargs)

    monkeypatch.setattr(advisor, "build_ownership_candidates", observed)

    def forbidden(*args, **kwargs):
        raise AssertionError("Read-only impact attempted a repository mutation")

    monkeypatch.setattr(owner._repository, "update", forbidden)
    monkeypatch.setattr(owner._repository, "create", forbidden)
    owner.proposal_impact(catalogue.proposals[-1].proposal_id)
    assert Decimal("25.000000") in called and Decimal("30") in called


@pytest.mark.parametrize("limit", ["fixtures", "output"])
def test_projection_bounds_fail_closed_with_safe_owner_error(monkeypatch, limit):
    import app.services.policy_impact_advisor as advisor

    owner, catalogue, _ = impact({IDP_POLICY_ID: DecimalPolicyValue(value="0.92")})
    monkeypatch.setattr(advisor, "MAX_SCENARIOS" if limit == "fixtures" else "MAX_OUTPUT_BYTES", 1)
    with pytest.raises(PolicyValidationError):
        owner.proposal_impact(catalogue.proposals[-1].proposal_id)


def test_http_same_evidence_roles_typed_schema_and_no_raw_fixtures():
    from phase13_test_clients import RawTestClient
    from phase13_test_credentials import TEST_PASSWORD
    from phase13_test_settings import ordinary_test_settings

    from app.main import create_app

    app = create_app(settings=ordinary_test_settings())

    def client(user):
        c = RawTestClient(app)
        login = c.post("/api/auth/login", json={"user_id": user, "password": TEST_PASSWORD})
        assert login.status_code == 200
        c.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        return c

    hr, director = client("biz-ops"), client("olivia-koh")
    base = hr.get("/api/policies").json()
    draft = hr.post(
        "/api/policies/proposals",
        json=dict(
            expected_catalogue_version=base["version"],
            changes={IDP_POLICY_ID: {"type": "DECIMAL", "value": "0.92"}},
            reason="Synthetic read-only impact HTTP comparison",
        ),
    )
    assert draft.status_code == 201
    proposal = draft.json()["proposals"][-1]
    url = f"/api/policies/proposals/{proposal['proposal_id']}/impact"
    left, right = hr.get(url), director.get(url)
    assert left.status_code == right.status_code == 200 and left.json() == right.json()
    from app.domain.policy_impact import PolicyImpactResponse

    PolicyImpactResponse.model_validate(left.json())
    assert len(left.content) < 262144
    for forbidden in (
        "display_name",
        "original_extracted_value",
        "raw_value",
        "relationships",
        "authorization",
        "password",
        "csrf_token",
    ):
        assert forbidden not in left.text
    assert RawTestClient(app).get(url).status_code == 401
    schema = app.openapi()
    response = schema["paths"]["/api/policies/proposals/{proposal_id}/impact"]["get"]["responses"][
        "200"
    ]
    assert response["content"]["application/json"]["schema"]["$ref"].endswith(
        "/PolicyImpactResponse"
    )


def test_all_active_intelligence_parameters_have_values_and_explicit_unknowns():
    values = {
        "ENTITY_RESOLUTION_AUTO_MATCH_THRESHOLD": DecimalPolicyValue(value="0.90"),
        "ENTITY_RESOLUTION_REVIEW_THRESHOLD": DecimalPolicyValue(value="0.65"),
        "ENTITY_RESOLUTION_AMBIGUITY_MARGIN": DecimalPolicyValue(value="0.04"),
        "ENTITY_RESOLUTION_IDENTIFIER_WEIGHT": DecimalPolicyValue(value="0.50"),
        "ENTITY_RESOLUTION_NAME_WEIGHT": DecimalPolicyValue(value="0.26"),
        "ENTITY_RESOLUTION_ADDRESS_WEIGHT": DecimalPolicyValue(value="0.12"),
        "ENTITY_RESOLUTION_LEGAL_FORM_WEIGHT": DecimalPolicyValue(value="0.06"),
        "ENTITY_RESOLUTION_INCORPORATION_DATE_WEIGHT": DecimalPolicyValue(value="0.06"),
        "UBO_ADVISORY_LIKELY_THRESHOLD": DecimalPolicyValue(value="0.70"),
        "UBO_ADVISORY_UNLIKELY_THRESHOLD": DecimalPolicyValue(value="0.30"),
        "MOCK_RISK_MEDIUM_THRESHOLD": IntegerPolicyValue(value=35),
        "MOCK_RISK_HIGH_THRESHOLD": IntegerPolicyValue(value=65),
        "MOCK_RISK_BLOCKS_READINESS": BooleanPolicyValue(value=True),
    }
    _, _, result = impact(values)
    assert len(result["changes"]) == 13
    for change in result["changes"]:
        assert change["materiality"] == change["assessment"] == "NOT_ASSESSED"
        assert change["effect"] == "NOT_ASSESSED"
        assert change["scenario_ids"] == []
        assert change["current"] and change["default"] and change["proposed"]
        assert change["coupled_policy_ids"]


def test_decimal_representation_change_is_not_a_numeric_decrease():
    _, _, result = impact({IDP_POLICY_ID: DecimalPolicyValue(value="0.850000")})
    assert result["changes"][0]["direction"] == "VALUE_CHANGE"
    assert result["changes"][0]["materiality"] == "NO_OBSERVED_CHANGE"


def test_classifier_policy_version_distinguishes_prospective_and_actual_activation():
    owner = service()
    pending = submit(owner, draft(owner))
    proposal = pending.proposals[-1]
    forecast = owner.proposal_impact(proposal.proposal_id)
    assert forecast["after"]["classifier"]["policy_version"] == pending.version + 1
    assert forecast["after"]["policy_version_context"] == "PROSPECTIVE_UNRESERVED"
    active = owner.decide_proposal(
        DIRECTOR,
        proposal.proposal_id,
        approve=True,
        expected_catalogue_version=pending.version,
        expected_proposal_version=proposal.version,
        reason="Independent activation preserves actual policy identity",
    )
    result = owner.proposal_impact(proposal.proposal_id)
    assert result["after"]["classifier"]["policy_version"] == active.proposals[-1].activated_version
    assert result["after"]["policy_version_context"] == "ACTIVATED_PROPOSAL"
