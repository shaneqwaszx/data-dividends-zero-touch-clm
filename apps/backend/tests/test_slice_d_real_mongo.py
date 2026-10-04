"""D2 physical evidence: durable ledger survives loss of process-local Mock facts."""

import os
from uuid import uuid4

import pytest
from test_phase12_real_mongo import _open_store, isolated_mongo_settings
from test_slice_d_mock_goldtier import NAME, UEN, advance, prepared

from app.config import Settings
from app.connectors.errors import MutationOutcomeUncertainError
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.domain.target_submission import GoldTierOperationMarker
from app.persistence.repositories import (
    MongoOnboardingCaseRepository,
    MongoTargetExecutionRepository,
)
from app.services.onboarding import OnboardingService

pytestmark = pytest.mark.skipif(
    not os.environ.get("PHASE12_MONGO_URI"),
    reason="D2 isolated physical Mongo is not configured",
)
__all__ = ["isolated_mongo_settings"]


def owner(store, connector):
    return OnboardingService(
        acra=MockAcraConnector(),
        goldtier=connector,
        repository=MongoOnboardingCaseRepository(store),
        target_execution_repository=MongoTargetExecutionRepository(store),
    )


class RecordingMock(MockGoldTierConnector):
    def __init__(self):
        super().__init__()
        self.calls = []

    def create_shell_customer(self, request, metadata):
        self.calls.append("SHELL")
        return super().create_shell_customer(request, metadata)

    def create_policy(self, request, metadata):
        self.calls.append("POLICY")
        return super().create_policy(request, metadata)

    def amend_party(self, party_id, request, metadata):
        self.calls.append("AMEND")
        return super().amend_party(party_id, request, metadata)

    def search_party(self, request, metadata):
        self.calls.append("SEARCH")
        return super().search_party(request, metadata)


def test_physical_retained_success_and_read_only_ledger_lookup_after_restart(
    isolated_mongo_settings: Settings,
):
    first_store = _open_store(isolated_mongo_settings)
    try:
        first_owner = owner(first_store, RecordingMock())
        submission = prepared(first_owner)
        receipt = first_owner.execute_submission_input(submission)
        assert receipt.classification.value == "SUCCESS"
    finally:
        first_store.close()
    second_store = _open_store(isolated_mongo_settings)
    try:
        connector = RecordingMock()
        restarted = owner(second_store, connector)
        before = second_store.get(submission.case_id)
        entries = MongoTargetExecutionRepository(second_store).list_for_case(submission.case_id)
        assert len(entries) == 1
        assert entries[0].target_outcome.readback_status == "VERIFIED"
        assert MongoTargetExecutionRepository(second_store).list_for_case(uuid4()) == ()
        assert second_store.get(submission.case_id) == before
        assert restarted.execute_submission_input(submission) == receipt
        assert connector.calls == [] and connector._customers == {}
        new_case = restarted.create_staged_case_with_identity(
            uuid4(), uuid4(), UEN, "SG", legal_name=NAME
        )
        assert new_case.initial_target_search.disposition == "NO_MATCH"
        assert new_case.existing_target_state is None
    finally:
        second_store.close()


@pytest.mark.parametrize("definitive_mutations", [1, 2, 3])
def test_physical_loss_of_mock_state_cannot_complete_missing_customer(
    isolated_mongo_settings: Settings, definitive_mutations
):
    first_store = _open_store(isolated_mongo_settings)
    try:
        first_owner = owner(first_store, RecordingMock())
        submission = prepared(first_owner)
        for _ in range(definitive_mutations):
            assert advance(first_owner, submission) is None
    finally:
        first_store.close()
    second_store = _open_store(isolated_mongo_settings)
    try:
        connector = RecordingMock()
        restarted = owner(second_store, connector)
        result = advance(restarted, submission)
        assert result is not None and result.classification.value in {"FAILED", "REVIEW_REQUIRED"}
        assert connector.calls == [{1: "POLICY", 2: "AMEND", 3: "SEARCH"}[definitive_mutations]]
        assert restarted.get_target_outcome(submission.submission_id).readback_status is None
        assert (
            restarted.get_attempted_target_operations(submission.submission_id).count(
                GoldTierOperationMarker.SHELL
            )
            == 1
        )
    finally:
        second_store.close()


def test_physical_uncertain_policy_after_state_loss_never_replays(
    isolated_mongo_settings: Settings,
):
    class LostResponse(RecordingMock):
        def create_policy(self, request, metadata):
            super().create_policy(request, metadata)
            raise MutationOutcomeUncertainError("GT_POLICY_OUTCOME_UNCERTAIN")

    first_store = _open_store(isolated_mongo_settings)
    try:
        first_owner = owner(first_store, LostResponse())
        submission = prepared(first_owner)
        assert advance(first_owner, submission) is None
        with pytest.raises(MutationOutcomeUncertainError):
            advance(first_owner, submission)
        before = first_owner.get_target_execution_entry(submission.submission_id)
    finally:
        first_store.close()
    second_store = _open_store(isolated_mongo_settings)
    try:
        connector = RecordingMock()
        restarted = owner(second_store, connector)
        for _ in range(2):
            with pytest.raises(MutationOutcomeUncertainError):
                advance(restarted, submission)
        assert connector.calls == []
        assert restarted.get_target_execution_entry(submission.submission_id) == before
    finally:
        second_store.close()


@pytest.mark.parametrize(
    "contradiction",
    (
        "receipt.case_id",
        "target_outcome.submission_id",
        "target_outcome.input_fingerprint",
        "ledger.resolved_party_id",
    ),
)
def test_physical_inconsistent_retained_proof_after_restart_cannot_reuse(
    isolated_mongo_settings: Settings, contradiction
):
    from test_slice_d_mock_goldtier import inconsistent_prior_entry

    first_store = _open_store(isolated_mongo_settings)
    connector = RecordingMock()
    try:
        first_owner = owner(first_store, connector)
        submission = prepared(first_owner)
        first_owner.execute_submission_input(submission)
        entry = first_owner.get_target_execution_entry(submission.submission_id)
        MongoTargetExecutionRepository(first_store).replace(
            inconsistent_prior_entry(entry, contradiction),
            expected_state="FINALIZED",
        )
    finally:
        first_store.close()

    second_store = _open_store(isolated_mongo_settings)
    try:
        restarted = owner(second_store, connector)
        before = MongoTargetExecutionRepository(second_store).get(submission.submission_id)
        new_case = restarted.create_staged_case_with_identity(
            uuid4(), uuid4(), UEN, "SG", legal_name=NAME
        )
        assert new_case.initial_target_search.disposition == "REVIEW_REQUIRED"
        assert new_case.existing_target_state is None
        assert MongoTargetExecutionRepository(second_store).get(submission.submission_id) == before
    finally:
        second_store.close()
