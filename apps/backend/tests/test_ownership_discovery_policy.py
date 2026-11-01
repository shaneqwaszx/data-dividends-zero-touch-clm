"""Editable discovery policy, catalogue migration and case-frozen persistence."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from phase24c_policy_workflow import approve_business_change
from pydantic import ValidationError
from s2_legacy_schema_fixtures import without_d101_fields

from app.connectors.garden_business import GARDEN_BUSINESS_UEN
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.domain.policy import (
    OWNERSHIP_CALL_BUDGET_ENABLED_ID,
    OWNERSHIP_CALL_BUDGET_MAX_ID,
    OWNERSHIP_DISCOVERY_MAX_DEPTH_ID,
    OWNERSHIP_DISCOVERY_POLICY_IDS,
    OWNERSHIP_TRACE_THRESHOLD_ID,
    UBO_POLICY_ID,
    BooleanPolicyValue,
    CasePolicySnapshot,
    DecimalPolicyValue,
    EvidenceClassifierPolicy,
    IntegerPolicyValue,
    OwnershipDiscoveryPolicySnapshot,
    PolicyCatalogue,
    RegistryPolicySnapshot,
    legacy_phase13_policy_snapshot,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.models import CASE_SNAPSHOT_SCHEMA_VERSION, DurableCaseSnapshot
from app.persistence.mongo_case_store import MongoCaseStore
from app.services.admin_repository import InMemoryPolicyRepository
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_discovery import OwnershipDiscoveryCoordinator
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.policy_management import (
    PolicyManagementService,
    PolicyValidationError,
    default_policy_catalogue,
)
from app.services.repository import InMemoryOnboardingCaseRepository

NOW = datetime(2026, 10, 23, 1, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)
HR = AuthenticatedActor(
    profile=UserProfile(user_id="hr-proposer", display_name="HR", role=Role.HR, team_id=None)
)
DIRECTOR = AuthenticatedActor(
    profile=UserProfile(
        user_id="director-decider", display_name="Director", role=Role.DIRECTOR, team_id=None
    )
)


def service(clock: datetime = NOW) -> PolicyManagementService:
    return PolicyManagementService(InMemoryPolicyRepository(), clock=lambda: clock)


def test_default_catalogue_appends_four_editable_discovery_rules() -> None:
    catalogue = service().catalogue()
    assert len(catalogue.rules) == 39
    assert tuple(rule.policy_id for rule in catalogue.rules[-4:]) == (
        OWNERSHIP_DISCOVERY_POLICY_IDS
    )
    by_id = {rule.policy_id: rule for rule in catalogue.rules}
    assert by_id[OWNERSHIP_TRACE_THRESHOLD_ID].value == DecimalPolicyValue(value="10.000000")
    assert by_id[OWNERSHIP_DISCOVERY_MAX_DEPTH_ID].value == IntegerPolicyValue(value=5)
    assert by_id[OWNERSHIP_DISCOVERY_MAX_DEPTH_ID].maximum == 7
    assert by_id[OWNERSHIP_CALL_BUDGET_ENABLED_ID].value == BooleanPolicyValue(value=False)
    assert by_id[OWNERSHIP_CALL_BUDGET_MAX_ID].value == IntegerPolicyValue(value=10)
    assert all(by_id[i].enforcement == "RUNTIME_ENFORCED" for i in OWNERSHIP_DISCOVERY_POLICY_IDS)
    assert by_id[UBO_POLICY_ID].value == DecimalPolicyValue(value="25.000000")


def test_new_case_snapshot_freezes_discovery_and_later_approval_affects_only_new_cases() -> None:
    s = service()
    first = s.case_snapshot()
    assert first.ownership_discovery == OwnershipDiscoveryPolicySnapshot(
        trace_threshold_percent=Decimal("10.000000"),
        max_corporate_depth=5,
        call_budget_enabled=False,
        call_budget_max=10,
    )
    approve_business_change(s, OWNERSHIP_TRACE_THRESHOLD_ID, DecimalPolicyValue(value="15"))
    approve_business_change(s, OWNERSHIP_CALL_BUDGET_ENABLED_ID, BooleanPolicyValue(value=True))
    second = s.case_snapshot()
    assert second.ownership_discovery is not None
    assert second.ownership_discovery.trace_threshold_percent == Decimal("15")
    assert second.ownership_discovery.call_budget_enabled is True
    assert first.ownership_discovery is not None
    assert first.ownership_discovery.trace_threshold_percent == Decimal("10.000000")
    assert second.policy_identity != first.policy_identity


@pytest.mark.parametrize(
    ("policy_id", "value"),
    (
        (OWNERSHIP_TRACE_THRESHOLD_ID, DecimalPolicyValue(value="30")),
        (UBO_POLICY_ID, DecimalPolicyValue(value="5")),
        (UBO_POLICY_ID, DecimalPolicyValue(value="0")),
        (OWNERSHIP_DISCOVERY_MAX_DEPTH_ID, IntegerPolicyValue(value=8)),
        (OWNERSHIP_DISCOVERY_MAX_DEPTH_ID, IntegerPolicyValue(value=0)),
        (OWNERSHIP_CALL_BUDGET_MAX_ID, IntegerPolicyValue(value=33)),
        (OWNERSHIP_CALL_BUDGET_MAX_ID, IntegerPolicyValue(value=0)),
        (OWNERSHIP_TRACE_THRESHOLD_ID, DecimalPolicyValue(value="0")),
    ),
)
def test_backend_rejects_inconsistent_or_out_of_range_discovery_policy(
    policy_id: str, value: DecimalPolicyValue | IntegerPolicyValue
) -> None:
    s = service()
    before = s.catalogue().rules
    with pytest.raises(PolicyValidationError):
        approve_business_change(s, policy_id, value)
    assert s.catalogue().rules == before


def test_lowering_ubo_threshold_together_with_trace_threshold_is_accepted() -> None:
    s = service()
    catalogue = s.create_proposal(
        HR,
        expected_catalogue_version=s.catalogue().version,
        changes={
            UBO_POLICY_ID: DecimalPolicyValue(value="20"),
            OWNERSHIP_TRACE_THRESHOLD_ID: DecimalPolicyValue(value="5"),
        },
        reason="Synthetic combined threshold proposal",
    )
    proposal = catalogue.proposals[-1]
    catalogue = s.submit_proposal(
        HR,
        proposal.proposal_id,
        expected_catalogue_version=catalogue.version,
        expected_proposal_version=proposal.version,
    )
    proposal = catalogue.proposals[-1]
    impact = s.proposal_impact(proposal.proposal_id)
    trace_change = next(
        item for item in impact["changes"] if item["policy_id"] == OWNERSHIP_TRACE_THRESHOLD_ID
    )
    assert trace_change["assessment"] == "NOT_ASSESSED"
    assert trace_change["stages"] == ["OWNERSHIP"]
    s.decide_proposal(
        DIRECTOR,
        proposal.proposal_id,
        approve=True,
        expected_catalogue_version=catalogue.version,
        expected_proposal_version=proposal.version,
        reason="Independent synthetic threshold approval",
    )
    snapshot = s.case_snapshot()
    assert snapshot.ubo_threshold_percent == Decimal("20")
    assert snapshot.ownership_discovery is not None
    assert snapshot.ownership_discovery.trace_threshold_percent == Decimal("5")


def _strip(rules: tuple) -> tuple:  # type: ignore[type-arg]
    return tuple(rule for rule in rules if rule.policy_id not in OWNERSHIP_DISCOVERY_POLICY_IDS)


def _legacy_catalogue_with_history() -> PolicyCatalogue:
    """A 35-rule schema-2 catalogue with approval, draft, pending and rejected history."""
    s = service()
    approve_business_change(
        s, "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD", DecimalPolicyValue(value="0.90")
    )
    for policy_id, value, submit in (
        (UBO_POLICY_ID, DecimalPolicyValue(value="30"), False),
        ("ENTITY_RESOLUTION_REVIEW_THRESHOLD", DecimalPolicyValue(value="0.65"), True),
        ("MOCK_RISK_HIGH_THRESHOLD", IntegerPolicyValue(value=70), True),
    ):
        catalogue = s.create_proposal(
            HR,
            expected_catalogue_version=s.catalogue().version,
            changes={policy_id: value},
            reason="Synthetic historical proposal",
        )
        if submit:
            proposal = catalogue.proposals[-1]
            s.submit_proposal(
                HR,
                proposal.proposal_id,
                expected_catalogue_version=catalogue.version,
                expected_proposal_version=proposal.version,
            )
    catalogue = s.catalogue()
    rejected = catalogue.proposals[-1]
    s.decide_proposal(
        DIRECTOR,
        rejected.proposal_id,
        approve=False,
        expected_catalogue_version=catalogue.version,
        expected_proposal_version=rejected.version,
        reason="Independent synthetic rejection",
    )
    legacy = _as_legacy_35(s.catalogue())
    assert legacy.active_origin == "APPROVED"
    return legacy


def _as_legacy_35(current: PolicyCatalogue) -> PolicyCatalogue:
    """Remove the discovery rules everywhere, as a pre-D-076 catalogue stored them."""
    legacy = PolicyCatalogue.model_validate(
        current.model_copy(
            update={
                "rules": _strip(current.rules),
                "superseded_versions": tuple(
                    item.model_copy(update={"rules": _strip(item.rules)})
                    for item in current.superseded_versions
                ),
                "proposals": tuple(
                    item.model_copy(update={"rules": _strip(item.rules)})
                    for item in current.proposals
                ),
            }
        ).model_dump()
    )
    assert len(legacy.rules) == 35
    return legacy


def _with_ubo(rules: tuple, value: str) -> tuple:  # type: ignore[type-arg]
    return tuple(
        rule.model_copy(update={"value": DecimalPolicyValue(value=value)})
        if rule.policy_id == UBO_POLICY_ID
        else rule
        for rule in rules
    )


@pytest.mark.parametrize("count", (35, 29))
def test_migration_seeds_trace_at_a_positive_ubo_below_ten_percent(count: int) -> None:
    repository = InMemoryPolicyRepository()
    current = default_policy_catalogue(NOW)
    repository.create(
        current.model_copy(update={"rules": _with_ubo(current.rules[:count], "8.000000")})
    )

    service = PolicyManagementService(repository, clock=lambda: LATER)
    migrated = service.catalogue()

    assert migrated.rule(UBO_POLICY_ID).value == DecimalPolicyValue(value="8.000000")  # type: ignore[union-attr]
    assert migrated.rule(OWNERSHIP_TRACE_THRESHOLD_ID).value == (  # type: ignore[union-attr]
        DecimalPolicyValue(value="8.000000")
    )
    assert migrated.audit_events[-1].metadata["trace_threshold_seeded_from_ubo"] is True
    snapshot = service.case_snapshot().ownership_discovery
    assert snapshot is not None and snapshot.trace_threshold_percent == Decimal("8")


@pytest.mark.parametrize("count", (35, 29))
def test_migration_fails_closed_for_a_zero_ubo_threshold(count: int) -> None:
    repository = InMemoryPolicyRepository()
    current = default_policy_catalogue(NOW)
    stored = repository.create(
        current.model_copy(update={"rules": _with_ubo(current.rules[:count], "0")})
    )

    with pytest.raises(PolicyValidationError):
        PolicyManagementService(repository, clock=lambda: LATER)

    assert repository.get() == stored


def test_history_bearing_migration_seeds_trace_at_an_approved_five_percent_ubo() -> None:
    s = service()
    approve_business_change(s, OWNERSHIP_TRACE_THRESHOLD_ID, DecimalPolicyValue(value="5"))
    approve_business_change(s, UBO_POLICY_ID, DecimalPolicyValue(value="5"))
    legacy = _as_legacy_35(s.catalogue())
    repository = InMemoryPolicyRepository()
    repository.create(legacy)

    migrated_service = PolicyManagementService(repository, clock=lambda: LATER)
    migrated = migrated_service.catalogue()

    assert migrated.active_origin == "MIGRATED"
    assert migrated.rules[:35] == legacy.rules
    assert migrated.rule(OWNERSHIP_TRACE_THRESHOLD_ID).value == DecimalPolicyValue(value="5")  # type: ignore[union-attr]
    assert migrated.audit_events[-1].metadata["trace_threshold_seeded_from_ubo"] is True
    snapshot = migrated_service.case_snapshot()
    assert snapshot.ubo_threshold_percent == Decimal("5")
    assert snapshot.ownership_discovery is not None
    assert snapshot.ownership_discovery.trace_threshold_percent == Decimal("5")


def test_history_bearing_35_rule_catalogue_migrates_additively_without_loss() -> None:
    legacy = _legacy_catalogue_with_history()
    repository = InMemoryPolicyRepository()
    repository.create(legacy)

    migrated = PolicyManagementService(repository, clock=lambda: LATER).catalogue()

    assert len(migrated.rules) == 39
    assert migrated.catalogue_schema_version == 3
    assert migrated.active_origin == "MIGRATED"
    assert migrated.active_version == legacy.version + 1
    assert migrated.rules[:35] == legacy.rules
    assert migrated.rule("DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD").value == (  # type: ignore[union-attr]
        DecimalPolicyValue(value="0.90")
    )
    assert migrated.superseded_versions[:-1] == legacy.superseded_versions
    assert migrated.superseded_versions[-1].version == legacy.active_version
    assert migrated.superseded_versions[-1].rules == legacy.rules
    assert migrated.audit_events[:-1] == legacy.audit_events
    event = migrated.audit_events[-1]
    assert event.action == "POLICY_CATALOGUE_MIGRATED"
    assert event.metadata == {
        "added_rule_count": 4,
        "rebased_proposal_count": 2,
        "superseded_active_version": legacy.active_version,
    }
    by_id = {item.proposal_id: item for item in migrated.proposals}
    for original in legacy.proposals:
        current = by_id[original.proposal_id]
        if original.status in {"APPROVED", "REJECTED"}:
            assert current == original
        else:
            assert current.base_active_version == migrated.active_version
            assert current.version == original.version + 1
            assert current.rules[:35] == original.rules
            assert current.rules[35:] == migrated.rules[35:]
    # Restart is idempotent and the rebased draft remains actionable.
    again = PolicyManagementService(repository, clock=lambda: LATER)
    assert again.catalogue() == migrated
    draft = next(item for item in migrated.proposals if item.status == "DRAFT")
    submitted = again.submit_proposal(
        HR,
        draft.proposal_id,
        expected_catalogue_version=migrated.version,
        expected_proposal_version=draft.version,
    )
    pending = next(item for item in submitted.proposals if item.proposal_id == draft.proposal_id)
    approved = again.decide_proposal(
        DIRECTOR,
        pending.proposal_id,
        approve=True,
        expected_catalogue_version=submitted.version,
        expected_proposal_version=pending.version,
        reason="Independent synthetic post-migration approval",
    )
    assert approved.active_origin == "APPROVED"
    assert approved.catalogue_schema_version == 3
    assert approved.rule(UBO_POLICY_ID).value == DecimalPolicyValue(value="30")  # type: ignore[union-attr]
    assert again.case_snapshot().ownership_discovery is not None


def test_history_free_35_rule_catalogue_keeps_existing_rebuild() -> None:
    repository = InMemoryPolicyRepository()
    current = default_policy_catalogue(NOW)
    edited = _strip(current.rules)
    edited = tuple(
        rule.model_copy(update={"value": DecimalPolicyValue(value="30.000000")})
        if rule.policy_id == UBO_POLICY_ID
        else rule
        for rule in edited
    )
    repository.create(current.model_copy(update={"rules": edited}))

    migrated = PolicyManagementService(repository, clock=lambda: LATER).catalogue()

    assert len(migrated.rules) == 39
    assert migrated.active_origin == "DEFAULT"
    assert migrated.rule(UBO_POLICY_ID).value == DecimalPolicyValue(value="30.000000")  # type: ignore[union-attr]
    assert migrated.audit_events[-1].metadata == {"added_rule_count": 4}


@pytest.mark.parametrize("count", (29, 21, 8))
def test_earlier_legacy_prefixes_gain_all_current_rules(count: int) -> None:
    repository = InMemoryPolicyRepository()
    current = default_policy_catalogue(NOW)
    repository.create(current.model_copy(update={"rules": current.rules[:count]}))
    migrated = PolicyManagementService(repository, clock=lambda: LATER).catalogue()
    assert [rule.policy_id for rule in migrated.rules] == [
        rule.policy_id for rule in current.rules
    ]


def test_partial_discovery_rule_set_fails_closed() -> None:
    repository = InMemoryPolicyRepository()
    current = default_policy_catalogue(NOW)
    repository.create(
        current.model_copy(
            update={
                "rules": tuple(
                    rule
                    for rule in current.rules
                    if rule.policy_id != OWNERSHIP_DISCOVERY_MAX_DEPTH_ID
                )
            }
        )
    )
    with pytest.raises(PolicyValidationError):
        PolicyManagementService(repository, clock=lambda: LATER)


def test_migrated_activation_cannot_change_predecessor_values() -> None:
    repository = InMemoryPolicyRepository()
    repository.create(_legacy_catalogue_with_history())
    migrated = PolicyManagementService(repository, clock=lambda: LATER).catalogue()
    tampered = tuple(
        rule.model_copy(update={"value": DecimalPolicyValue(value="0.99")})
        if rule.policy_id == "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD"
        else rule
        for rule in migrated.rules
    )
    with pytest.raises(ValidationError):
        PolicyCatalogue.model_validate({**migrated.model_dump(), "rules": tampered})
    with pytest.raises(ValidationError):
        PolicyCatalogue.model_validate({**migrated.model_dump(), "catalogue_schema_version": 2})


def test_case_snapshot_discovery_requires_consistent_approved_parameters() -> None:
    discovery = OwnershipDiscoveryPolicySnapshot(
        trace_threshold_percent=Decimal("30"),
        max_corporate_depth=5,
        call_budget_enabled=False,
        call_budget_max=10,
    )
    base = {
        "snapshot_label": "SYNTHETIC",
        "catalogue_version": 1,
        "idp_review_confidence_threshold": Decimal("0.85"),
        "ubo_threshold_percent": Decimal("25"),
        "registry": RegistryPolicySnapshot(),
        "evidence_classifier": EvidenceClassifierPolicy(),
        "policy_identity": "c" * 64,
        "bound_at": NOW,
    }
    with pytest.raises(ValidationError):
        CasePolicySnapshot(**base, ownership_discovery=discovery)
    # A legacy unapproved snapshot cannot claim discovery parameters.
    with pytest.raises(ValidationError):
        CasePolicySnapshot.model_validate(
            {
                **legacy_phase13_policy_snapshot().model_dump(),
                "ownership_discovery": {
                    **discovery.model_dump(),
                    "trace_threshold_percent": Decimal("10"),
                },
            }
        )
    assert legacy_phase13_policy_snapshot().ownership_discovery is None
    with pytest.raises(ValidationError):
        OwnershipDiscoveryPolicySnapshot.model_validate(
            {**discovery.model_dump(), "max_corporate_depth": "5"}
        )


def _garden_envelope() -> DurableCaseSnapshot:
    policies = service()
    onboarding = OnboardingService(
        acra=MockAcraConnector(clock=lambda: NOW),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: NOW,
        policy_snapshot_provider=policies.case_snapshot,
    )
    ownership = OwnershipAnalysisService(
        cases=onboarding,
        provider=RegistryAcquisitionOwnershipProvider(onboarding),
        discovery=OwnershipDiscoveryCoordinator(onboarding),
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=lambda: NOW,
    )
    case = onboarding.create_staged_case(GARDEN_BUSINESS_UEN)
    ownership.load(case_id=case.case_id)
    record = ownership.analyze(case_id=case.case_id)
    current = onboarding.get_case(case.case_id)
    assert current is not None and record.discovery is not None
    return DurableCaseSnapshot(
        case_id=case.case_id,
        revision=1,
        onboarding=current,
        ownership=record,
        created_at=NOW,
        updated_at=NOW,
    )


def test_current_envelope_round_trips_frozen_policy_and_discovery_audit() -> None:
    snapshot = _garden_envelope()
    codec = object.__new__(MongoCaseStore)
    decoded = codec._decode(codec._encode(snapshot))  # noqa: SLF001
    assert CASE_SNAPSHOT_SCHEMA_VERSION == 18
    assert decoded.schema_version == 18
    assert decoded.ownership == snapshot.ownership
    assert decoded.onboarding.policy_snapshot == snapshot.onboarding.policy_snapshot


def test_schema_ten_envelope_cannot_carry_discovery_fields_but_reads_without_them() -> None:
    snapshot = _garden_envelope()
    codec = object.__new__(MongoCaseStore)
    encoded = codec._encode(snapshot)  # noqa: SLF001
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode({**encoded, "schema_version": 10})  # noqa: SLF001

    legacy = {**without_d101_fields(encoded), "schema_version": 10}
    legacy["onboarding"] = dict(legacy["onboarding"])
    legacy["onboarding"]["policy_snapshot"] = {
        key: value
        for key, value in encoded["onboarding"]["policy_snapshot"].items()
        if key != "ownership_discovery"
    }
    with pytest.raises(PersistenceDataInvalidError):
        codec._decode(legacy)  # noqa: SLF001 - ownership audit is still later evidence
    legacy["ownership"] = {
        key: value for key, value in encoded["ownership"].items() if key != "discovery"
    }
    decoded = codec._decode(legacy)  # noqa: SLF001
    assert decoded.schema_version == 18
    assert decoded.onboarding.policy_snapshot.ownership_discovery is None
    assert decoded.ownership is not None and decoded.ownership.discovery is None
