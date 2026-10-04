"""Phase24C physical proofs use only fresh existing-allowlisted disposable databases."""

import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from threading import Barrier

import pytest
from phase24c_policy_workflow import approve_business_change
from pymongo import MongoClient
from s2_legacy_schema_fixtures import omit_session2_fields
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_phase24c_policy import DIRECTOR, draft, submit
from test_phase24c_registry import setup

from app.composition import build_onboarding_service
from app.config import Settings
from app.domain.models import RegistryCacheKey, RegistryFreshnessPolicy, WorkflowState
from app.domain.policy import DecimalPolicyValue
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_registry_cache_store import MongoRegistryCacheStore
from app.services.admin_repository import AdministrationConflictError
from app.services.policy_management import PolicyManagementService
from app.services.registry_acquisition import RegistryAcquisitionCoordinator

URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not URI, reason="PHASE12_MONGO_URI is not configured")
NOW = datetime(2026, 10, 2, tzinfo=UTC)


@pytest.fixture
def physical_settings(monkeypatch):
    assert URI is not None
    database = generate_ephemeral_mongo_database("p145")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=URI,
        mongo_database=database,
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7776000,
    )
    client = MongoClient(URI)
    import sys

    bundles = []
    original = build_persistence_bundle

    def tracked(settings):
        result = original(settings)
        bundles.append(result)
        return result

    monkeypatch.setattr(sys.modules[__name__], "build_persistence_bundle", tracked)
    try:
        client.admin.command("ping")
        yield settings, client
    finally:
        for bundle in bundles:
            bundle.close()
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def test_policy_activation_restart_preserves_inflight_and_completed_case_freeze(physical_settings):
    settings, client = physical_settings
    first = build_persistence_bundle(settings)
    policy = PolicyManagementService(first.policies)
    cases = build_onboarding_service(
        settings=settings,
        repository=first.onboarding,
        target_execution_repository=first.target_executions,
        registry_snapshot_repository=first.registry_snapshots,
        policy_snapshot_provider=policy.case_snapshot,
    )
    inflight = cases.create_staged_case("202400001A")
    completed = cases.create_staged_case("202400007G")
    cases.confirm_target_dispatch(
        case_id=completed.case_id,
        actor_id="synthetic-operator",
        expected_case_event_count=len(completed.events),
        clm_version=None,
        destination="GOLDTIER_MOCK",
    )
    completed = cases.submit_staged_case(completed.case_id, complete_legacy_flow=True)
    assert completed.state == WorkflowState.COMPLETED
    old_inflight = inflight.policy_snapshot
    old_completed = completed.policy_snapshot
    approved = approve_business_change(
        policy, "DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD", DecimalPolicyValue(value="0.90")
    )
    identity = approved.active_identity
    new = cases.create_staged_case("202400001A")
    assert new.policy_snapshot.idp_review_confidence_threshold == Decimal("0.90")
    first.close()
    second = build_persistence_bundle(settings)
    try:
        restarted = PolicyManagementService(second.policies)
        assert restarted.catalogue().active_identity == identity
        assert restarted.catalogue().proposals[-1].decided_by == "director-decider"
        assert len(restarted.catalogue().superseded_versions) == 1
        assert second.onboarding.get(inflight.case_id).policy_snapshot == old_inflight
        assert second.onboarding.get(completed.case_id).policy_snapshot == old_completed
        assert second.onboarding.get(new.case_id).policy_snapshot.policy_identity == identity
        raw = client[settings.mongo_database][settings.mongo_case_collection].find_one(
            {"_id": str(new.case_id)}
        )
        assert raw["schema_version"] == 9
    finally:
        second.close()


def test_independent_policy_service_decisions_cas_activate_once(physical_settings):
    settings, _ = physical_settings
    bundle = build_persistence_bundle(settings)
    one = PolicyManagementService(bundle.policies, clock=lambda: NOW)
    two = PolicyManagementService(bundle.policies, clock=lambda: NOW)
    c = submit(one, draft(one))
    p = c.proposals[-1]
    barrier = Barrier(2)
    for service in (one, two):
        original = service._expected

        def read(version, original=original):
            result = original(version)
            barrier.wait(timeout=3)
            return result

        service._expected = read

    def decide(service):
        try:
            service.decide_proposal(
                DIRECTOR,
                p.proposal_id,
                approve=True,
                expected_catalogue_version=c.version,
                expected_proposal_version=p.version,
                reason="Independent physical concurrent approval",
            )
            return "APPROVED"
        except AdministrationConflictError:
            return "CONFLICT"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(decide, (one, two))) == ["APPROVED", "CONFLICT"]
        assert len(one.catalogue().superseded_versions) == 1
    finally:
        bundle.close()


def test_deleted_policy_is_not_resurrected_by_stale_proposal(physical_settings):
    settings, client = physical_settings
    bundle = build_persistence_bundle(settings)
    service = PolicyManagementService(bundle.policies, clock=lambda: NOW)
    original = bundle.policies.update

    def delete_before_write(candidate, *, expected_version):
        client[settings.mongo_database][settings.mongo_admin_policies_collection].delete_one(
            {"_id": "GLOBAL_POLICY_CATALOGUE"}
        )
        return original(candidate, expected_version=expected_version)

    bundle.policies.update = delete_before_write
    try:
        with pytest.raises(AdministrationConflictError):
            draft(service)
        assert (
            client[settings.mongo_database][
                settings.mongo_admin_policies_collection
            ].count_documents({})
            == 0
        )
    finally:
        bundle.close()


@pytest.mark.parametrize(
    "corruption", ["self", "decision", "version", "effective", "unknown", "schema_bool"]
)
def test_corrupt_policy_history_fails_closed(physical_settings, corruption):
    settings, client = physical_settings
    bundle = build_persistence_bundle(settings)
    service = PolicyManagementService(bundle.policies, clock=lambda: NOW)
    c = submit(service, draft(service))
    p = c.proposals[-1]
    service.decide_proposal(
        DIRECTOR,
        p.proposal_id,
        approve=True,
        expected_catalogue_version=c.version,
        expected_proposal_version=p.version,
        reason="Independent physical history approval",
    )
    collection = client[settings.mongo_database][settings.mongo_admin_policies_collection]
    raw = collection.find_one({"_id": "GLOBAL_POLICY_CATALOGUE"})
    if corruption == "self":
        raw["proposals"][-1]["decided_by"] = raw["proposals"][-1]["proposer_id"]
    elif corruption == "decision":
        raw["proposals"][-1]["decided_at"] = None
    elif corruption == "version":
        raw["active_version"] += 1
    elif corruption == "effective":
        raw["active_effective_at"] = "2026-10-03T00:00:00+00:00"
    elif corruption == "unknown":
        raw["proposals"][-1]["unknown"] = "unsupported"
    else:
        raw["catalogue_schema_version"] = True
    collection.replace_one({"_id": raw["_id"]}, raw)
    try:
        with pytest.raises(PersistenceDataInvalidError):
            bundle.policies.get()
    finally:
        bundle.close()


def test_registry_prefix_and_definitive_negative_restart_are_lossless(physical_settings):
    settings, client = physical_settings
    clock, connector, _, provider, _ = setup()
    store = MongoRegistryCacheStore(
        client,
        database=settings.mongo_database,
        collection=settings.mongo_registry_cache_collection,
    )
    store.initialize()
    first = RegistryAcquisitionCoordinator(store, RegistryFreshnessPolicy(), clock=clock)
    connector.fail_operation = "RELATIONSHIPS"
    partial = first.acquire(provider, "202400001A")
    assert partial.binding is None
    first.acquire(provider, "209999999Z")
    connector.fail_operation = None
    before = dict(connector.calls)
    restarted_store = MongoRegistryCacheStore(
        client,
        database=settings.mongo_database,
        collection=settings.mongo_registry_cache_collection,
    )
    restarted_store.initialize()
    restarted = RegistryAcquisitionCoordinator(
        restarted_store, RegistryFreshnessPolicy(), clock=clock
    )
    assert restarted.acquire(provider, "209999999Z").acquisition is None
    assert connector.calls == before
    complete = restarted.acquire(provider, "202400001A")
    assert complete.binding is not None
    for operation in ("ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES"):
        assert connector.calls[operation] == before[operation]
    assert connector.calls["RELATIONSHIPS"] == before["RELATIONSHIPS"] + 1
    key = RegistryCacheKey(
        provider_identity=provider.cache_identity, normalized_identifier="202400001A"
    )
    assert restarted_store.get(key).cache_schema_version == 2


def test_schema7_case_read_is_legacy_without_rewrite_or_new_parameter_smuggling(physical_settings):
    settings, client = physical_settings
    bundle = build_persistence_bundle(settings)
    policy = PolicyManagementService(bundle.policies)
    cases = build_onboarding_service(
        settings=settings,
        repository=bundle.onboarding,
        registry_snapshot_repository=bundle.registry_snapshots,
        policy_snapshot_provider=policy.case_snapshot,
    )
    case = cases.create_staged_case("202400001A")
    collection = client[settings.mongo_database][settings.mongo_case_collection]
    raw = collection.find_one({"_id": str(case.case_id)})
    raw["schema_version"] = 7
    omit_session2_fields(raw)
    parameters = deepcopy(raw["onboarding"]["policy_snapshot"])
    for key in ("registry", "evidence_classifier", "policy_identity"):
        raw["onboarding"]["policy_snapshot"].pop(key)
    collection.replace_one({"_id": raw["_id"]}, raw)
    try:
        loaded = bundle.onboarding.get(case.case_id)
        assert (
            loaded.policy_snapshot.registry is None
            and loaded.policy_snapshot.evidence_classifier is None
        )
        assert collection.find_one({"_id": raw["_id"]}) == raw
        raw["onboarding"]["policy_snapshot"] = parameters
        collection.replace_one({"_id": raw["_id"]}, raw)
        with pytest.raises(PersistenceDataInvalidError):
            bundle.onboarding.get(case.case_id)
    finally:
        bundle.close()
