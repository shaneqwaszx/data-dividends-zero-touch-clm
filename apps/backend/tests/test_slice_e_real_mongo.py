"""Slice E physical policy persistence; only freshly allowlisted disposable databases."""

import os
from copy import deepcopy
from decimal import Decimal

import pytest
from test_phase24c_policy import DIRECTOR, HR
from test_phase24c_real_mongo import physical_settings  # noqa: F401

from app.composition import build_onboarding_service
from app.domain.policy import DecimalPolicyValue
from app.persistence.composition import build_persistence_bundle
from app.services.policy_management import PolicyManagementService

pytestmark = pytest.mark.skipif(
    not os.environ.get("PHASE12_MONGO_URI"), reason="Disposable physical Mongo is not configured"
)


def test_impact_restart_is_read_only_and_retained_base_and_case_freeze_survive(
    physical_settings,  # noqa: F811
):
    settings, client = physical_settings
    first = build_persistence_bundle(settings)
    second = None
    try:
        owner = PolicyManagementService(first.policies)
        cases = build_onboarding_service(
            settings=settings,
            repository=first.onboarding,
            target_execution_repository=first.target_executions,
            registry_snapshot_repository=first.registry_snapshots,
            policy_snapshot_provider=owner.case_snapshot,
        )
        old = cases.create_staged_case("202400001A")
        frozen = old.policy_snapshot.model_copy(deep=True)
        initial = owner.catalogue()
        draft = owner.create_proposal(
            HR,
            expected_catalogue_version=initial.version,
            changes={"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": DecimalPolicyValue(value="0.92")},
            reason="Synthetic physical prospective impact proposal",
        )
        pending = draft.proposals[-1]
        submitted = owner.submit_proposal(
            HR,
            pending.proposal_id,
            expected_catalogue_version=draft.version,
            expected_proposal_version=pending.version,
        )
        pending = submitted.proposals[-1]
        other = owner.create_proposal(
            HR,
            expected_catalogue_version=submitted.version,
            changes={"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD": DecimalPolicyValue(value="0.90")},
            reason="Synthetic retained historical comparison proposal",
        )
        stale_id = other.proposals[-1].proposal_id
        collections = (settings.mongo_admin_policies_collection, settings.mongo_case_collection)

        def contents():
            return [
                deepcopy(list(client[settings.mongo_database][name].find({})))
                for name in collections
            ]

        before = contents()
        evidence = owner.proposal_impact(pending.proposal_id)
        assert evidence == owner.proposal_impact(pending.proposal_id)
        assert before == contents()
        active = owner.decide_proposal(
            DIRECTOR,
            pending.proposal_id,
            approve=True,
            expected_catalogue_version=other.version,
            expected_proposal_version=pending.version,
            reason="Independent physical synthetic impact approval",
        )
        new = cases.create_staged_case("202400001A")
        assert first.onboarding.get(old.case_id).policy_snapshot == frozen
        assert new.policy_snapshot.idp_review_confidence_threshold == Decimal("0.92")
        historical = owner.proposal_impact(stale_id)
        assert historical["stale"] and historical["comparison_basis"] == "RETAINED_PROPOSAL_BASE"
        first.close()
        second = build_persistence_bundle(settings)
        restarted = PolicyManagementService(second.policies)
        snapshot = contents()
        assert restarted.catalogue().active_identity == active.active_identity
        assert restarted.proposal_impact(stale_id) == historical
        assert second.onboarding.get(old.case_id).policy_snapshot == frozen
        assert second.onboarding.get(new.case_id).policy_snapshot == new.policy_snapshot
        assert snapshot == contents()
    finally:
        first.close()
        if second is not None:
            second.close()
