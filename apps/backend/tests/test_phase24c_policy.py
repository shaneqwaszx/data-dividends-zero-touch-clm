"""Phase24C proposal and immutable active-policy contracts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.access import AuthenticatedActor, Role, TeamId, UserProfile
from app.domain.policy import DecimalPolicyValue
from app.services.admin_repository import AdministrationConflictError, InMemoryPolicyRepository
from app.services.policy_management import PolicyForbiddenError, PolicyManagementService

NOW = datetime(2026, 10, 2, tzinfo=UTC)


def actor(role: Role, user: str) -> AuthenticatedActor:
    return AuthenticatedActor(
        profile=UserProfile(
            user_id=user,
            display_name="Synthetic actor",
            role=role,
            team_id=TeamId.TEAM_A
            if role in {Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER}
            else None,
        )
    )


HR = actor(Role.HR, "hr-proposer")
DIRECTOR = actor(Role.DIRECTOR, "director-decider")


def service() -> PolicyManagementService:
    return PolicyManagementService(InMemoryPolicyRepository(), clock=lambda: NOW)


def draft(s: PolicyManagementService, proposer: AuthenticatedActor = HR):
    c = s.catalogue()
    return s.create_proposal(
        proposer,
        expected_catalogue_version=c.version,
        changes={"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": DecimalPolicyValue(value="0.90")},
        reason="Synthetic confidence threshold proposal",
    )


def submit(s: PolicyManagementService, c):
    p = c.proposals[-1]
    return s.submit_proposal(
        HR, p.proposal_id, expected_catalogue_version=c.version, expected_proposal_version=p.version
    )


def test_proposal_and_reset_cannot_activate_until_director_decision():
    s = service()
    original = s.case_snapshot()
    c = draft(s)
    assert s.case_snapshot().catalogue_version == original.catalogue_version
    assert (
        s.case_snapshot().idp_review_confidence_threshold
        == original.idp_review_confidence_threshold
    )
    c = submit(s, c)
    p = c.proposals[-1]
    c = s.decide_proposal(
        DIRECTOR,
        p.proposal_id,
        approve=True,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        reason="Approved synthetic benchmark impact",
    )
    assert c.proposals[-1].status == "APPROVED"
    assert str(s.case_snapshot().idp_review_confidence_threshold) == "0.90"
    assert (
        original.idp_review_confidence_threshold
        != s.case_snapshot().idp_review_confidence_threshold
    )
    reset = s.create_proposal(
        HR,
        expected_catalogue_version=c.version,
        changes={},
        reset_ids=("DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD",),
        reason="Restore defined project default",
    )
    assert str(s.case_snapshot().idp_review_confidence_threshold) == "0.90"
    assert reset.proposals[-1].rules[0].value == reset.rules[0].default_value


@pytest.mark.parametrize("role", [Role.CLIENT_ONBOARDER, Role.RELATIONSHIP_MANAGER, Role.DIRECTOR])
def test_only_hr_can_create_proposal(role):
    with pytest.raises(PolicyForbiddenError):
        draft(service(), actor(role, "normal-actor"))


def test_self_approval_and_stale_base_rejected():
    s = service()
    c = submit(s, draft(s))
    p = c.proposals[-1]
    promoted = actor(Role.DIRECTOR, HR.profile.user_id)
    with pytest.raises(PolicyForbiddenError):
        s.decide_proposal(
            promoted,
            p.proposal_id,
            approve=True,
            expected_catalogue_version=c.version,
            expected_proposal_version=p.version,
            reason="Forbidden self approval attempt",
        )
    newer = draft(s)
    c = s.decide_proposal(
        DIRECTOR,
        p.proposal_id,
        approve=True,
        expected_catalogue_version=newer.version,
        expected_proposal_version=p.version,
        reason="Independent synthetic approval",
    )
    second = c.proposals[-1]
    with pytest.raises(AdministrationConflictError):
        s.submit_proposal(
            HR,
            second.proposal_id,
            expected_catalogue_version=c.version,
            expected_proposal_version=second.version,
        )


def test_concurrent_decisions_only_activate_once():
    s = service()
    c = submit(s, draft(s))
    p = c.proposals[-1]

    def decide():
        try:
            s.decide_proposal(
                DIRECTOR,
                p.proposal_id,
                approve=True,
                expected_catalogue_version=c.version,
                expected_proposal_version=p.version,
                reason="Independent concurrent approval",
            )
            return "APPROVED"
        except AdministrationConflictError:
            return "CONFLICT"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: decide(), range(2))) == ["APPROVED", "CONFLICT"]
    assert len(s.catalogue().superseded_versions) == 1


def test_http_proposal_approval_and_direct_mutation_retirement():
    from phase13_test_clients import RawTestClient
    from phase13_test_credentials import TEST_PASSWORD
    from phase13_test_settings import ordinary_test_settings

    from app.main import create_app

    app = create_app(settings=ordinary_test_settings())

    def client(user):
        c = RawTestClient(app)
        response = c.post("/api/auth/login", json={"user_id": user, "password": TEST_PASSWORD})
        assert response.status_code == 200
        c.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return c

    hr = client("hr-admin")
    rm = client("ethan-tan")
    director = client("olivia-koh")
    baseline = hr.get("/api/policies").json()
    body = {
        "expected_catalogue_version": baseline["version"],
        "changes": {
            "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": {"type": "DECIMAL", "value": "0.91"}
        },
        "reason": "Synthetic confidence change for approval",
    }
    assert rm.post("/api/policies/proposals", json=body).status_code == 403
    response = hr.post("/api/policies/proposals", json=body)
    assert response.status_code == 201, response.text
    c = response.json()
    p = c["proposals"][-1]
    assert c["active_identity"] == baseline["active_identity"]
    submitted = hr.post(
        f"/api/policies/proposals/{p['proposal_id']}/submit",
        json={
            "expected_catalogue_version": c["version"],
            "expected_proposal_version": p["version"],
        },
    )
    assert submitted.status_code == 200, submitted.text
    c = submitted.json()
    p = c["proposals"][-1]
    decision = {
        "expected_catalogue_version": c["version"],
        "expected_proposal_version": p["version"],
        "approve": True,
        "reason": "Independent synthetic policy approval",
    }
    assert (
        hr.post(f"/api/policies/proposals/{p['proposal_id']}/decision", json=decision).status_code
        == 403
    )
    approved = director.post(f"/api/policies/proposals/{p['proposal_id']}/decision", json=decision)
    assert approved.status_code == 200, approved.text
    assert approved.json()["active_identity"] != baseline["active_identity"]
    assert (
        director.post(
            f"/api/policies/proposals/{p['proposal_id']}/decision", json=decision
        ).status_code
        == 409
    )
    for c in (hr, rm, director):
        assert (
            c.patch(
                "/api/policies/DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD",
                json={
                    "expected_catalogue_version": 1,
                    "expected_rule_version": 1,
                    "value": {"type": "DECIMAL", "value": "0.95"},
                },
            ).status_code
            == 403
        )
        c.close()


def test_reauthorization_rejects_privilege_change_inside_lock():
    s = service()
    c = submit(s, draft(s))
    p = c.proposals[-1]
    downgraded = actor(Role.RELATIONSHIP_MANAGER, DIRECTOR.profile.user_id)
    calls = []

    def reauthorize():
        calls.append(True)
        return downgraded

    with pytest.raises(PolicyForbiddenError):
        s.decide_proposal(
            DIRECTOR,
            p.proposal_id,
            approve=True,
            expected_catalogue_version=c.version,
            expected_proposal_version=p.version,
            reason="Must reject stale Director authority",
            reauthorize=reauthorize,
        )
    assert calls == [True]
    assert s.catalogue() == c


def test_impact_is_read_only_and_metrics_are_deterministic():
    s = service()
    c = s.create_proposal(
        HR,
        expected_catalogue_version=s.catalogue().version,
        changes={"EVIDENCE_CLASSIFICATION_THRESHOLD": DecimalPolicyValue(value="0.95")},
        reason="Synthetic higher semantic threshold",
    )
    proposal = c.proposals[-1]
    first = s.proposal_impact(proposal.proposal_id)
    assert s.catalogue() == c
    assert first == s.proposal_impact(proposal.proposal_id)
    before = first["before"]["classifier"]
    after = first["after"]["classifier"]
    assert before["support"] == 14
    assert before["exact_accuracy"] == 1
    assert after["exact_accuracy"] < before["exact_accuracy"]
    assert sum(sum(row.values()) for row in before["confusion_matrix"].values()) == 14
    assert before["micro"]["f1"] == before["exact_accuracy"]
    assert before["benchmark_hash"] == after["benchmark_hash"]


def test_parameterized_classifier_and_legacy_metadata_remain_distinct():
    from app.domain.ownership_evidence import OwnershipEvidence
    from app.domain.policy import EvidenceClassifierPolicy
    from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger

    evidence = (
        OwnershipEvidence(
            evidence_id="safe-fixture",
            entity_identifier="202400001A",
            party_id="safe-party",
            kind="SHARE_UNITS",
            raw_value="10",
            numeric_value="10",
            provider="BENCHMARK",
            environment="LOCAL",
            source_operation="SYNTHETIC",
            retrieved_at=NOW,
            confidence="0.20",
            evidence_version=1,
        ),
    )
    tagger = OwnershipEvidenceTagger()
    legacy = tagger.tag(evidence, case_version=1).tags[0]
    normal = tagger.tag(
        evidence, case_version=1, policy=EvidenceClassifierPolicy(), policy_version=1
    ).tags[0]
    strict = tagger.tag(
        evidence,
        case_version=1,
        policy=EvidenceClassifierPolicy(threshold="0.95"),
        policy_version=2,
    ).tags[0]
    assert legacy.rule_version == "ownership-semantic-rules-v1" and legacy.score is None
    assert normal.tag == "SHARE_UNIT_EVIDENCE" and str(normal.score) == "0.8000"
    assert strict.tag == "INSUFFICIENT_EVIDENCE"
    assert strict.policy_version == 2 and "SEMANTIC_SCORE_BELOW_THRESHOLD" in strict.reason_codes


def test_invalid_coupled_weights_cannot_submit_and_security_rules_cannot_be_proposed():
    from app.domain.policy import StringPolicyValue
    from app.services.policy_management import PolicyValidationError

    s = service()
    c = s.create_proposal(
        HR,
        expected_catalogue_version=s.catalogue().version,
        changes={"EVIDENCE_KIND_WEIGHT": DecimalPolicyValue(value="0.60")},
        reason="Unbalanced weights must stay a draft",
    )
    with pytest.raises(PolicyValidationError):
        submit(s, c)
    assert s.catalogue() == c
    for policy_id in ("REGISTRY_PROVIDER", "OWNERSHIP_UBO_COMPARATOR", "GOLDTIER_POLICY"):
        with pytest.raises(PolicyValidationError):
            s.create_proposal(
                HR,
                expected_catalogue_version=c.version,
                changes={policy_id: StringPolicyValue(value="UNAUTHORIZED")},
                reason="Forbidden invariant change must fail",
            )
    assert s.catalogue() == c


def test_edit_reject_and_approved_reset_reconstruct_history_without_early_activation():
    from app.domain.policy import PolicyCatalogue

    s = service()
    baseline = s.case_snapshot()
    c = draft(s)
    p = c.proposals[-1]
    c = s.edit_proposal(
        HR,
        p.proposal_id,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        changes={"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": DecimalPolicyValue(value="0.92")},
        reason="Edited synthetic proposal must not activate",
    )
    assert s.case_snapshot().policy_identity == baseline.policy_identity
    c = submit(s, c)
    p = c.proposals[-1]
    c = s.decide_proposal(
        DIRECTOR,
        p.proposal_id,
        approve=False,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        reason="Independent rejection retains active baseline",
    )
    assert c.proposals[-1].status == "REJECTED"
    assert s.case_snapshot().policy_identity == baseline.policy_identity
    c = submit(s, draft(s))
    p = c.proposals[-1]
    c = s.decide_proposal(
        DIRECTOR,
        p.proposal_id,
        approve=True,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        reason="Independent approval of synthetic change",
    )
    c = s.create_proposal(
        HR,
        expected_catalogue_version=c.version,
        changes={},
        reset_ids=("DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD",),
        reason="Reset defined default through independent review",
    )
    assert s.case_snapshot().idp_review_confidence_threshold == Decimal("0.90")
    c = submit(s, c)
    p = c.proposals[-1]
    c = s.decide_proposal(
        DIRECTOR,
        p.proposal_id,
        approve=True,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        reason="Independent approval of defined default reset",
    )
    assert (
        s.case_snapshot().idp_review_confidence_threshold
        == baseline.idp_review_confidence_threshold
    )
    decoded = PolicyCatalogue.model_validate_json(c.model_dump_json())
    assert decoded == c and len(decoded.superseded_versions) == 2
    assert [p.status for p in decoded.proposals] == ["REJECTED", "APPROVED", "APPROVED"]
    assert [event.action for event in decoded.audit_events].count("POLICY_PROPOSAL_APPROVED") == 2


def test_approved_registry_and_classifier_values_reach_new_cases_and_frozen_runtime():
    from datetime import timedelta

    from phase24c_policy_workflow import approve_business_change
    from test_phase24c_registry import setup

    from app.connectors.mock_goldtier import MockGoldTierConnector
    from app.connectors.registry import RegistryProviderRouter
    from app.domain.ownership_evidence import OwnershipEvidence
    from app.domain.policy import IntegerPolicyValue
    from app.services.onboarding import OnboardingService
    from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger
    from app.services.repository import InMemoryOnboardingCaseRepository

    clock, connector, cache, provider, coordinator = setup()
    policies = PolicyManagementService(InMemoryPolicyRepository(), clock=clock)
    cases = OnboardingService(
        acra=None,
        registry_router=RegistryProviderRouter(provider),
        registry_acquisition_coordinator=coordinator,
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=clock,
        policy_snapshot_provider=policies.case_snapshot,
    )
    old = cases.create_staged_case("202400001A")
    approve_business_change(policies, "REGISTRY_FRESHNESS_DAYS", IntegerPolicyValue(value=1))
    approve_business_change(policies, "REGISTRY_NOT_FOUND_TTL_SECONDS", IntegerPolicyValue(value=1))
    approve_business_change(
        policies, "EVIDENCE_CLASSIFICATION_THRESHOLD", DecimalPolicyValue(value="0.95")
    )
    clock.value += timedelta(days=1)
    new = cases.create_staged_case("202400001A")
    assert connector.total_calls == 8
    assert new.registry_evidence_binding.freshness_policy.duration_seconds == 86400
    assert cases.get_case(old.case_id).policy_snapshot == old.policy_snapshot
    assert old.policy_snapshot.registry.freshness_seconds == 7776000
    assert new.policy_snapshot.registry.negative_seconds == 1
    assert old.policy_snapshot.registry.negative_seconds == 600
    evidence = (
        OwnershipEvidence(
            evidence_id="synthetic-score",
            entity_identifier="202400001A",
            party_id="synthetic-party",
            kind="SHARE_UNITS",
            numeric_value=Decimal("10"),
            raw_value="10",
            provider="BENCHMARK",
            environment="LOCAL",
            source_operation="SYNTHETIC",
            retrieved_at=clock.value,
            confidence=Decimal("0.20"),
            evidence_version=1,
        ),
    )
    tagger = OwnershipEvidenceTagger()
    before = tagger.tag(
        evidence,
        case_version=1,
        policy=old.policy_snapshot.evidence_classifier,
        policy_version=old.policy_snapshot.catalogue_version,
    )
    after = tagger.tag(
        evidence,
        case_version=1,
        policy=new.policy_snapshot.evidence_classifier,
        policy_version=new.policy_snapshot.catalogue_version,
    )
    assert before.tags[0].tag == "SHARE_UNIT_EVIDENCE"
    assert after.tags[0].tag == "INSUFFICIENT_EVIDENCE"
