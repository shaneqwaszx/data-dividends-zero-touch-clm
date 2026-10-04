"""Explicit synthetic, process-local ambiguity through accepted public Mock operations."""

from dataclasses import dataclass
from uuid import uuid4

from app.config import Settings
from app.connectors.goldtier_models import GoldTierOutcome, GoldTierRequestMetadata
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.domain.target_submission import GoldTierProviderMode
from app.mappers.goldtier import MockGoldTierRequestMapper
from app.services.onboarding import OnboardingService
from app.services.repository import InMemoryOnboardingCaseRepository
from app.services.target_execution_repository import InMemoryTargetExecutionRepository

from scripts.slice_b_registry_fixture import CountingSyntheticRegistry


@dataclass(frozen=True)
class LocalAmbiguityFixture:
    onboarding: OnboardingService
    registry: CountingSyntheticRegistry

    def metadata(self) -> dict[str, object]:
        return {
            "fixture": "synthetic-target-ambiguity",
            "classification": "SYNTHETIC_MOCK",
            "setup_target_mutations": 4,
            "external_calls": 0,
        }


def build_local_ambiguity_fixture(settings: Settings) -> LocalAmbiguityFixture:
    if (
        settings.app_env != "test"
        or settings.clm_persistence_mode != "memory"
        or settings.acra_connector_mode != "mock"
        or settings.goldtier_connector_mode != "mock"
        or settings.idp_connector_mode != "local_pdf_text"
    ):
        raise ValueError(
            "Ambiguity fixture requires isolated test/memory/Mock/LOCAL composition"
        )
    connector = MockGoldTierConnector()
    registry = CountingSyntheticRegistry()

    def owner(acra):
        return OnboardingService(
            acra=acra,
            goldtier=connector,
            repository=InMemoryOnboardingCaseRepository(),
            target_execution_repository=InMemoryTargetExecutionRepository(),
        )

    # Seed only process-local provider facts. No finalized case/ledger reuse proof is forged.
    seed = owner(CountingSyntheticRegistry())
    case = seed.create_case("202400001A")
    seed.confirm_target_dispatch(
        case_id=case.case_id,
        actor_id="slice-f-local-fixture",
        expected_case_event_count=len(case.events),
        clm_version=None,
        destination="GOLDTIER_MOCK",
    )
    submission = seed.build_submission_input(
        case, provider_mode=GoldTierProviderMode.MOCK
    )
    mapper = MockGoldTierRequestMapper()
    for _ in range(2):
        metadata = GoldTierRequestMetadata(
            correlation_id=uuid4(),
            source_case_id=submission.source_case_id,
            idempotency_key=uuid4(),
        )
        shell = connector.create_shell_customer(
            mapper.build_shell_request(submission), metadata
        )
        assert shell.outcome == GoldTierOutcome.SUCCESS and shell.party_id is not None
        policy = connector.create_policy(
            mapper.build_policy_request(submission, shell.party_id), metadata
        )
        assert policy.outcome == GoldTierOutcome.SUCCESS
    return LocalAmbiguityFixture(owner(registry), registry)


@dataclass(frozen=True)
class LocalReuseFixture:
    onboarding: OnboardingService
    ownership: object
    registry: CountingSyntheticRegistry


def build_local_reuse_fixture(settings: Settings) -> LocalReuseFixture:
    # Use the same guard as ambiguity; all providers and persistence are explicit local fixtures.
    if (
        settings.app_env != "test"
        or settings.clm_persistence_mode != "memory"
        or settings.acra_connector_mode != "mock"
        or settings.goldtier_connector_mode != "mock"
        or settings.idp_connector_mode != "local_pdf_text"
    ):
        raise ValueError(
            "Reuse fixture requires isolated test/memory/Mock/LOCAL composition"
        )
    from app.composition import (
        build_onboarding_service,
        build_ownership_analysis_service,
    )

    from scripts.slice_c_recovery_fixture import CreationPolicyFixture

    registry = CountingSyntheticRegistry()
    onboarding = build_onboarding_service(
        settings=settings,
        acra_connector=registry,
        policy_snapshot_provider=CreationPolicyFixture(legacy_creation=False),
    )
    ownership = build_ownership_analysis_service(onboarding, settings)
    return LocalReuseFixture(onboarding, ownership, registry)
