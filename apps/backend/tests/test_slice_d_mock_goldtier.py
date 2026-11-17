"""Slice D2: local Mock facts cannot replace case/ledger authority."""

from dataclasses import fields
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from workflow_publication_seed import bind_test_fence

from app.connectors.errors import ConnectorError, MutationOutcomeUncertainError
from app.connectors.goldtier_models import (
    GoldTierOutcome,
    GoldTierRequestMetadata,
    GoldTierSearchOutcome,
    SearchPartyRequest,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.domain.target_submission import (
    GoldTierOperationMarker,
    GoldTierProviderMode,
    GoldTierSearchResolution,
)
from app.mappers.goldtier import MockGoldTierRequestMapper
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.target_execution_repository import InMemoryTargetExecutionRepository

UEN = "202400001A"
NAME = "MERLION CIRCULAR LABS PTE. LTD."
MAPPER = MockGoldTierRequestMapper()


def service(connector=None, repository=None, ledger=None):
    service = OnboardingService(
        acra=MockAcraConnector(),
        goldtier=connector or MockGoldTierConnector(),
        repository=repository or InMemoryOnboardingCaseRepository(),
        target_execution_repository=ledger or InMemoryTargetExecutionRepository(),
    )
    return bind_test_fence(service)


def prepared(owner):
    case = owner.create_case(UEN)
    owner.confirm_target_dispatch(
        case_id=case.case_id,
        actor_id="d2-local-test",
        expected_case_event_count=len(case.events),
        clm_version=None,
        destination="GOLDTIER_MOCK",
    )
    return owner.build_submission_input(case, provider_mode=GoldTierProviderMode.MOCK)


def metadata(submission, *, correlation_id=None):
    return GoldTierRequestMetadata(
        correlation_id=correlation_id or submission.correlation_id,
        source_case_id=submission.source_case_id,
        idempotency_key=uuid4(),
    )


def shell(connector, submission):
    result = connector.create_shell_customer(
        MAPPER.build_shell_request(submission), metadata(submission)
    )
    assert result.outcome == GoldTierOutcome.SUCCESS and result.party_id is not None
    return result.party_id


def policy(connector, submission, party_id):
    return connector.create_policy(
        MAPPER.build_policy_request(submission, party_id), metadata(submission)
    )


def search(connector, submission, registration=UEN):
    return connector.search_party(
        SearchPartyRequest(registration_number=registration), metadata(submission)
    )


def advance(owner, submission):
    return owner.advance_incremental_submission_input(
        submission,
        search_resolution=GoldTierSearchResolution.NO_MATCH,
        selected_party_id=None,
    )


def test_default_no_match_is_unchanged_and_exact_only():
    connector = MockGoldTierConnector()
    submission = prepared(service(connector))
    for value in (UEN, UEN.lower(), "202400001", "UNRELATED"):
        assert search(connector, submission, value).outcome == GoldTierSearchOutcome.NO_MATCH


def test_configured_match_does_not_invent_policy_or_legal_name():
    connector = MockGoldTierConnector(match_found_external_keys=frozenset({UEN}))
    submission = prepared(service())
    found = search(connector, submission)
    assert found.matched_party_id == f"GT-MOCK-EXISTING-{UEN}"
    assert found.candidates[0].legal_name is None
    assert found.candidates[0].registration_number == UEN


def test_shell_never_parses_source_case_id_for_registration():
    connector = MockGoldTierConnector()
    submission = prepared(service()).model_copy(
        update={"source_case_id": "CASE-FAKE-UEN-SECRETLESS"}
    )
    party_id = shell(connector, submission)
    assert search(connector, submission).outcome == GoldTierSearchOutcome.NO_MATCH
    customer = connector._customers[party_id]
    assert customer.identity.legal_name == NAME
    assert customer.identity.country == "SG"
    assert customer.identity.registration_number is None
    assert customer.party_role == "Customer"
    assert customer.party_type == "Organisation"


def test_policy_success_establishes_registration_binding_not_approval():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    party_id = shell(connector, submission)
    result = policy(connector, submission, party_id)
    assert result.status == "POLICY_CREATED"
    found = search(connector, submission)
    assert found.matched_party_id == party_id
    assert found.candidates[0].registration_number == UEN
    assert search(connector, submission, UEN.lower()).outcome == GoldTierSearchOutcome.NO_MATCH


def test_policy_validation_failure_retains_shell_without_registration():
    connector = MockGoldTierConnector(policy_validation_failure_keys=frozenset({UEN}))
    submission = prepared(service())
    party_id = shell(connector, submission)
    assert policy(connector, submission, party_id).outcome == GoldTierOutcome.VALIDATION_FAILED
    assert search(connector, submission).outcome == GoldTierSearchOutcome.NO_MATCH


def test_required_amend_then_truthful_readback_in_same_process():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    party_id = shell(connector, submission)
    assert policy(connector, submission, party_id).outcome == GoldTierOutcome.SUCCESS
    assert MAPPER.requires_amend(submission)
    result = connector.amend_party(
        party_id, MAPPER.build_amend_request(submission, party_id), metadata(submission)
    )
    assert result.status == "ENRICHED"
    found = connector.search_party(
        MAPPER.build_readback_request(submission, party_id), metadata(submission)
    )
    assert found.matched_party_id == party_id
    assert found.candidates[0].legal_name == NAME
    assert found.candidates[0].registered_address == "18 INNOVATION WAY, #04-01, 018956, SG"


@pytest.mark.parametrize(
    "fixture,outcome,status",
    [
        ("partial_amend_external_keys", GoldTierOutcome.PARTIAL_SUCCESS, "PARTIALLY_ENRICHED"),
        ("amend_validation_failure_keys", GoldTierOutcome.VALIDATION_FAILED, "VALIDATION_FAILED"),
    ],
)
def test_amend_failure_fixtures_have_truthful_technical_state(fixture, outcome, status):
    connector = MockGoldTierConnector(**{fixture: frozenset({UEN})})
    submission = prepared(service())
    party_id = shell(connector, submission)
    policy(connector, submission, party_id)
    result = connector.amend_party(
        party_id, MAPPER.build_amend_request(submission, party_id), metadata(submission)
    )
    assert result.outcome == outcome and result.status == status
    assert connector._customers[party_id].identity.registered_address is None


def test_new_connector_loses_state_and_unknown_mutations_cannot_succeed():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    party_id = shell(connector, submission)
    policy(connector, submission, party_id)
    fresh = MockGoldTierConnector()
    assert search(fresh, submission).outcome == GoldTierSearchOutcome.NO_MATCH
    assert policy(fresh, submission, party_id).outcome == GoldTierOutcome.VALIDATION_FAILED
    assert (
        fresh.amend_party(
            party_id, MAPPER.build_amend_request(submission, party_id), metadata(submission)
        ).outcome
        == GoldTierOutcome.VALIDATION_FAILED
    )
    assert not fresh._customers


def test_snapshot_is_defensive_and_fixture_reset_is_connector_local():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    party_id = shell(connector, submission)
    request = MAPPER.build_policy_request(submission, party_id)
    connector.create_policy(request, metadata(submission))
    request.customer_external_system_key = "UNRELATED"
    assert search(connector, submission).matched_party_id == party_id
    assert MockGoldTierConnector()._customers == {}
    assert not hasattr(connector, "seed") and not hasattr(connector, "reset")


def test_bounded_state_full_correlation_id_and_collision_fail_closed():
    connector = MockGoldTierConnector(max_customers=2)
    submission = prepared(service())
    first = shell(connector, submission)
    other_metadata = metadata(
        submission, correlation_id=UUID("12345678-0000-4000-8000-000000000001")
    )
    third_metadata = metadata(
        submission, correlation_id=UUID("12345678-0000-4000-8000-000000000002")
    )
    second = connector.create_shell_customer(MAPPER.build_shell_request(submission), other_metadata)
    assert second.party_id != first
    assert (
        connector.create_shell_customer(
            MAPPER.build_shell_request(submission), third_metadata
        ).outcome
        != GoldTierOutcome.SUCCESS
    )
    assert (
        connector.create_shell_customer(
            MAPPER.build_shell_request(submission), metadata(submission)
        ).outcome
        != GoldTierOutcome.SUCCESS
    )
    assert len(connector._customers) == 2


def test_duplicate_registration_never_selects_an_arbitrary_customer():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    for correlation in (uuid4(), uuid4()):
        result = connector.create_shell_customer(
            MAPPER.build_shell_request(submission), metadata(submission, correlation_id=correlation)
        )
        assert result.party_id is not None
        policy(connector, submission, result.party_id)
    found = search(connector, submission)
    assert found.outcome == GoldTierSearchOutcome.MULTIPLE_MATCHES
    assert found.matched_party_id is None


def test_unsupported_query_dialects_fail_closed():
    with pytest.raises(ValidationError):
        XpiCustomerSearchRequest.model_validate({"registrationNumber": UEN})
    submission = prepared(service())
    with pytest.raises(ConnectorError):
        MockGoldTierConnector().search_party(
            XpiCustomerSearchRequest(legal_name=NAME), metadata(submission)
        )


def test_mock_internal_state_has_no_workflow_audit_http_or_persistence_owner():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    party_id = shell(connector, submission)
    assert {field.name for field in fields(connector._customers[party_id])} == {
        "identity",
        "party_role",
        "party_type",
        "external_system",
        "policy_id",
        "policy_status",
        "amend_status",
    }
    assert connector.environment == GoldTierProviderMode.MOCK
    assert not any(
        name in vars(connector)
        for name in ("transport", "session", "token", "database", "ledger", "repository")
    )


def test_direct_success_is_verified_by_existing_ledger():
    owner = service()
    submission = prepared(owner)
    receipt = owner.execute_submission_input(submission)
    assert receipt.classification.value == "SUCCESS"
    entry = owner.get_target_execution_entry(submission.submission_id)
    assert entry is not None and entry.target_outcome is not None
    assert entry.completed_operations == (
        GoldTierOperationMarker.SEARCH,
        GoldTierOperationMarker.SHELL,
        GoldTierOperationMarker.POLICY,
        GoldTierOperationMarker.AMEND,
        GoldTierOperationMarker.READBACK,
    )
    assert entry.target_outcome.readback_party_id == entry.target_outcome.party_id
    assert entry.target_outcome.readback_status == "VERIFIED"


def test_incremental_requires_amend_and_ledger_readback_before_finalization():
    owner = service()
    submission = prepared(owner)
    for expected in (
        GoldTierOperationMarker.SHELL,
        GoldTierOperationMarker.POLICY,
        GoldTierOperationMarker.AMEND,
    ):
        assert advance(owner, submission) is None
        entry = owner.get_target_execution_entry(submission.submission_id)
        assert entry is not None and entry.attempted_operations[-1] == expected
        assert entry.target_outcome is None
    receipt = advance(owner, submission)
    assert receipt is not None and receipt.classification.value == "SUCCESS"
    assert owner.get_execution_receipt(submission.submission_id) == receipt


def test_provider_state_loss_after_definitive_shell_never_fabricates_policy_success():
    repository, ledger = InMemoryOnboardingCaseRepository(), InMemoryTargetExecutionRepository()
    owner = service(repository=repository, ledger=ledger)
    submission = prepared(owner)
    assert advance(owner, submission) is None
    restarted = service(repository=repository, ledger=ledger)
    receipt = advance(restarted, submission)
    assert receipt is not None and receipt.classification.value == "FAILED"
    assert restarted.get_attempted_target_operations(submission.submission_id) == (
        GoldTierOperationMarker.SEARCH,
        GoldTierOperationMarker.SHELL,
        GoldTierOperationMarker.POLICY,
    )


def test_uncertain_operation_blocks_replay_after_provider_state_loss():
    class LoseResponse(MockGoldTierConnector):
        def create_policy(self, request, metadata):
            super().create_policy(request, metadata)
            raise MutationOutcomeUncertainError("GT_POLICY_OUTCOME_UNCERTAIN")

    repository, ledger = InMemoryOnboardingCaseRepository(), InMemoryTargetExecutionRepository()
    owner = service(LoseResponse(), repository, ledger)
    submission = prepared(owner)
    advance(owner, submission)
    with pytest.raises(MutationOutcomeUncertainError):
        advance(owner, submission)
    restarted = service(repository=repository, ledger=ledger)
    with pytest.raises(MutationOutcomeUncertainError):
        advance(restarted, submission)
    assert restarted.get_target_outcome(submission.submission_id) is None
    assert (
        restarted.get_attempted_target_operations(submission.submission_id)[-1]
        == GoldTierOperationMarker.POLICY
    )


def test_seeded_provider_cannot_establish_prior_verified_case_or_reuse():
    owner = service(MockGoldTierConnector(match_found_external_keys=frozenset({UEN})))
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert case.initial_target_search is not None
    assert case.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert case.existing_target_state is None
    legacy = owner.create_case(UEN)
    submission = owner.build_submission_input(legacy, provider_mode=GoldTierProviderMode.MOCK)
    evidence = owner.search_target_identity(
        case_id=legacy.case_id,
        request_id=uuid4(),
        provider_mode=GoldTierProviderMode.MOCK,
        searched_at=legacy.created_at,
    )
    assert evidence.resolution is None
    assert owner.get_target_execution_entry(submission.submission_id) is None


def test_same_identity_reuse_requires_case_and_real_ledger_proof():
    owner = service()
    submission = prepared(owner)
    receipt = owner.execute_submission_input(submission)
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert (
        case.initial_target_search is not None
        and case.initial_target_search.disposition == "EXACT_MATCH"
    )
    assert (
        case.existing_target_state is not None
        and case.existing_target_state.target_party_id == receipt.result.party_id
    )
    different = owner.create_staged_case_with_identity(
        uuid4(), uuid4(), UEN, "SG", legal_name="DIFFERENT SYNTHETIC PTE. LTD."
    )
    assert (
        different.initial_target_search is not None
        and different.initial_target_search.disposition == "REVIEW_REQUIRED"
    )


def test_case_projection_without_ledger_cannot_verify_provider_seed():
    from app.domain.models import GoldTierResult, WorkflowState

    repository = InMemoryOnboardingCaseRepository()
    connector = MockGoldTierConnector(match_found_external_keys=frozenset({UEN}))
    owner = service(connector, repository)
    prior = owner.create_case(UEN)
    prior.goldtier_result = GoldTierResult(
        party_id=f"GT-MOCK-EXISTING-{UEN}",
        shell_status="SHELL_CREATED",
        readback_party_id=f"GT-MOCK-EXISTING-{UEN}",
        readback_status="VERIFIED",
    )
    prior.state = WorkflowState.GT_ENRICHED
    repository.save(prior)
    assert (
        repository.find_verified_target_case(
            registration_number=UEN,
            legal_name=NAME,
            country_of_incorporation="SG",
            party_id=f"GT-MOCK-EXISTING-{UEN}",
        )
        is not None
    )
    case = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert (
        case.initial_target_search is not None
        and case.initial_target_search.disposition == "REVIEW_REQUIRED"
    )


@pytest.mark.parametrize("completed_mutations", [2, 3])
def test_state_loss_after_policy_or_amend_blocks_false_finalization(completed_mutations):
    repository, ledger = InMemoryOnboardingCaseRepository(), InMemoryTargetExecutionRepository()
    owner = service(repository=repository, ledger=ledger)
    submission = prepared(owner)
    for _ in range(completed_mutations):
        assert advance(owner, submission) is None
    restarted = service(repository=repository, ledger=ledger)
    receipt = advance(restarted, submission)
    assert receipt is not None
    assert receipt.classification.value in {"FAILED", "REVIEW_REQUIRED"}
    assert receipt.classification.value != "SUCCESS"
    assert (
        restarted.get_target_execution_entry(
            submission.submission_id
        ).target_outcome.readback_status
        is None
    )


def test_retained_success_receipt_needs_no_provider_reconstruction():
    repository, ledger = InMemoryOnboardingCaseRepository(), InMemoryTargetExecutionRepository()
    owner = service(repository=repository, ledger=ledger)
    submission = prepared(owner)
    receipt = owner.execute_submission_input(submission)
    fresh = MockGoldTierConnector()
    restarted = service(fresh, repository, ledger)
    assert restarted.execute_submission_input(submission) == receipt
    assert fresh._customers == {}
    assert search(fresh, submission).outcome == GoldTierSearchOutcome.NO_MATCH


def test_actual_same_identity_reuse_skips_shell_policy_and_verifies_again():
    owner = service()
    first = prepared(owner)
    original = owner.execute_submission_input(first)
    second = prepared(owner)
    reused = owner.execute_submission_input(second)
    assert reused.classification.value == "SUCCESS"
    assert reused.result.party_id == original.result.party_id
    assert owner.get_attempted_target_operations(second.submission_id) == (
        GoldTierOperationMarker.SEARCH,
        GoldTierOperationMarker.AMEND,
        GoldTierOperationMarker.READBACK,
    )


def test_current_provider_identity_conflict_cannot_reuse_prior_verified_case():
    connector = MockGoldTierConnector()
    owner = service(connector)
    first = prepared(owner)
    result = owner.execute_submission_input(first)
    amend = MAPPER.build_amend_request(first, result.result.party_id)
    amend.party.names.legal_name = "OTHER SYNTHETIC CUSTOMER"
    connector.amend_party(result.result.party_id, amend, metadata(first))
    created = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert created.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert created.existing_target_state is None


def test_local_provider_operations_never_use_http_or_auth(monkeypatch):
    import socket

    import httpx

    def forbidden(*args, **kwargs):
        raise AssertionError("External activity is forbidden in this local Mock test")

    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    owner = service()
    submission = prepared(owner)
    assert owner.execute_submission_input(submission).classification.value == "SUCCESS"


def test_incremental_cannot_bypass_prior_proof_with_seeded_selected_id():
    owner = service(MockGoldTierConnector(match_found_external_keys=frozenset({UEN})))
    submission = prepared(owner)
    with pytest.raises(ValueError, match="prior finalized readback"):
        owner.advance_incremental_submission_input(
            submission,
            search_resolution=GoldTierSearchResolution.EXACT_MATCH,
            selected_party_id=f"GT-MOCK-EXISTING-{UEN}",
        )
    assert owner.get_target_execution_entry(submission.submission_id) is None


def test_concurrent_shell_ids_with_shared_prefix_are_distinct_and_bounded():
    from concurrent.futures import ThreadPoolExecutor

    connector = MockGoldTierConnector(max_customers=2)
    submission = prepared(service())
    correlations = (
        UUID("12345678-0000-4000-8000-000000000001"),
        UUID("12345678-0000-4000-8000-000000000002"),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda correlation: connector.create_shell_customer(
                    MAPPER.build_shell_request(submission),
                    metadata(submission, correlation_id=correlation),
                ),
                correlations,
            )
        )
    assert all(result.outcome == GoldTierOutcome.SUCCESS for result in results)
    assert len({result.party_id for result in results}) == 2


def test_policy_cannot_rebind_an_established_customer_identity():
    connector = MockGoldTierConnector()
    submission = prepared(service())
    party_id = shell(connector, submission)
    assert policy(connector, submission, party_id).outcome == GoldTierOutcome.SUCCESS
    request = MAPPER.build_policy_request(submission, party_id)
    request.customer_external_system_key = "OTHER-REGISTRATION"
    assert (
        connector.create_policy(request, metadata(submission)).outcome
        == GoldTierOutcome.VALIDATION_FAILED
    )
    assert search(connector, submission).matched_party_id == party_id


PROOF_CONTRADICTIONS = (
    "receipt.case_id",
    "receipt.submission_id",
    "receipt.correlation_id",
    "receipt.input_fingerprint",
    "target_outcome.case_id",
    "target_outcome.submission_id",
    "target_outcome.correlation_id",
    "target_outcome.input_fingerprint",
    "target_outcome.idempotency_fingerprint",
    "ledger.resolved_party_id",
    "ledger.readback_status",
    "ledger.policy_status",
    "receipt.onboarding_state",
    "receipt.result.policy_status",
    "receipt.error",
    "receipt.infrastructure_failure",
)


def inconsistent_prior_entry(entry, contradiction):
    """Strict-model-valid contradictions, never a runtime seeding facility."""
    from app.domain.target_submission import GoldTierExecutionLedgerEntry

    data = entry.model_dump(mode="python")
    data["workflow_dispatch"] = entry.workflow_dispatch  # excluded from dumps (ADR-017)
    if contradiction == "ledger.resolved_party_id":
        data["resolved_party_id"] = "GT-MOCK-CONTRADICTORY"
        data["readback_party_id"] = "GT-MOCK-CONTRADICTORY"
    else:
        segments = contradiction.split(".")
        if segments[0] == "ledger":
            segments = segments[1:]
        current = data
        for segment in segments[:-1]:
            current = current[segment]
        field = segments[-1]
        if field in {"case_id", "submission_id", "correlation_id"}:
            current[field] = uuid4()
        elif field.endswith("fingerprint"):
            current[field] = "0" * 64
        elif field == "onboarding_state":
            current[field] = "REVIEW_REQUIRED"
        elif field == "error":
            current[field] = {
                "code": "GT_LOCAL_CONTRADICTION",
                "message": "Local contradictory proof.",
            }
        elif field == "infrastructure_failure":
            current[field] = True
        else:
            current[field] = "INCONSISTENT"
    return GoldTierExecutionLedgerEntry.model_validate(data)


@pytest.mark.parametrize("contradiction", PROOF_CONTRADICTIONS)
def test_inconsistent_finalized_ledger_never_proves_customer_reuse(contradiction):
    ledger = InMemoryTargetExecutionRepository()
    owner = service(ledger=ledger)
    first = prepared(owner)
    owner.execute_submission_input(first)
    entry = owner.get_target_execution_entry(first.submission_id)
    contradictory = inconsistent_prior_entry(entry, contradiction)
    ledger.replace(
        contradictory,
        expected_state="FINALIZED",
        expected_attempted=entry.attempted_operations,
    )

    created = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert created.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert created.existing_target_state is None
    second = prepared(owner)
    evidence = owner.search_target_identity(
        case_id=second.case_id,
        request_id=uuid4(),
        provider_mode=GoldTierProviderMode.MOCK,
        searched_at=owner.get_case(second.case_id).created_at,
    )
    assert evidence.resolution is None
    with pytest.raises(ValueError, match="prior finalized readback"):
        owner.advance_incremental_submission_input(
            second,
            search_resolution=GoldTierSearchResolution.EXACT_MATCH,
            selected_party_id=entry.target_outcome.party_id,
        )
    assert owner.get_target_execution_entry(second.submission_id) is None


def test_conflicting_case_projection_cannot_replace_retained_result():
    repository = InMemoryOnboardingCaseRepository()
    owner = service(repository=repository)
    first = prepared(owner)
    owner.execute_submission_input(first)
    prior = repository.get(first.case_id)
    prior.goldtier_result.policy_status = "INCONSISTENT"
    repository.save(prior)
    created = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert created.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert created.existing_target_state is None


@pytest.mark.parametrize(
    "proof_defect",
    ("marker", "status", "both", "AMEND_NOT_REQUIRED", "PARTIALLY_ENRICHED", "VALIDATION_FAILED"),
)
def test_mock_reuse_rejects_coherently_invalid_required_amend_proof(proof_defect):
    from app.domain.target_submission import GoldTierExecutionLedgerEntry

    repository = InMemoryOnboardingCaseRepository()
    ledger = InMemoryTargetExecutionRepository()
    owner = service(repository=repository, ledger=ledger)
    first = prepared(owner)
    owner.execute_submission_input(first)
    entry = owner.get_target_execution_entry(first.submission_id)
    assert GoldTierOperationMarker.AMEND in entry.definitively_completed_operations
    assert entry.amend_status == "ENRICHED"
    data = entry.model_dump()
    data["workflow_dispatch"] = entry.workflow_dispatch  # excluded from dumps (ADR-017)

    if proof_defect in {"marker", "both"}:
        for key in ("attempted_operations", "completed_operations", "resolved_operations"):
            if data[key] is not None:
                data[key] = tuple(
                    operation
                    for operation in data[key]
                    if operation != GoldTierOperationMarker.AMEND
                )
        data["target_outcome"]["completed_operations"] = tuple(
            operation
            for operation in data["target_outcome"]["completed_operations"]
            if operation != GoldTierOperationMarker.AMEND
        )
    if proof_defect != "marker":
        retained_status = None if proof_defect in {"status", "both"} else proof_defect
        data["amend_status"] = retained_status
        data["target_outcome"]["amend_status"] = retained_status
        data["receipt"]["result"]["amend_status"] = retained_status
        prior = repository.get(first.case_id)
        prior.goldtier_result.amend_status = retained_status
        repository.save(prior)

    # Shared historical/XPI schemas remain valid; the Mock proof consumer must reject.
    incomplete = GoldTierExecutionLedgerEntry.model_validate(data)
    ledger.replace(
        incomplete,
        expected_state="FINALIZED",
        expected_attempted=entry.attempted_operations,
    )
    created = owner.create_staged_case_with_identity(uuid4(), uuid4(), UEN, "SG", legal_name=NAME)
    assert created.initial_target_search.disposition == "REVIEW_REQUIRED"
    assert created.existing_target_state is None

    second = prepared(owner)
    evidence = owner.search_target_identity(
        case_id=second.case_id,
        request_id=uuid4(),
        provider_mode=GoldTierProviderMode.MOCK,
        searched_at=owner.get_case(second.case_id).created_at,
    )
    assert evidence.resolution is None
    with pytest.raises(ValueError, match="prior finalized readback"):
        owner.advance_incremental_submission_input(
            second,
            search_resolution=GoldTierSearchResolution.EXACT_MATCH,
            selected_party_id=entry.target_outcome.party_id,
        )
    assert owner.get_target_execution_entry(second.submission_id) is None
