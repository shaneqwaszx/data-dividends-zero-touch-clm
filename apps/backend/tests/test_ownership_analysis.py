from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier, Event
from typing import Any, Never
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import OwnershipProviderMetadata, OwnershipSourceResult
from app.domain.models import (
    CanonicalLegalEntity,
    OnboardingCase,
    SourceEnvironment,
    SourceMetadata,
    SourceSystem,
    WorkflowState,
)
from app.domain.ownership import (
    OwnershipAnalysisState,
    OwnershipCandidateClassification,
    OwnershipEnvironment,
    OwnershipIssueCode,
    OwnershipProvenance,
    OwnershipRelationship,
    OwnershipThresholdResult,
)
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import OwnershipInfrastructureError, OwnershipRequestError
from app.services.ownership_repository import (
    InMemoryOwnershipAnalysisRepository,
    OwnershipRepositoryConflictError,
)

CASE_ID = UUID("00000000-0000-4000-8000-000000000401")
OTHER_CASE_ID = UUID("00000000-0000-4000-8000-000000000402")
FIXED_TIME = datetime(2026, 8, 11, tzinfo=UTC)


class Cases:
    def get_case(self, case_id: UUID) -> OnboardingCase | None:
        if case_id not in {CASE_ID, OTHER_CASE_ID}:
            return None
        entity = CanonicalLegalEntity(
            registration_number="202400001A",
            legal_name="MERLION CIRCULAR LABS PTE. LTD.",
            country_of_incorporation="SG",
            party_type="PRIVATE_COMPANY_LIMITED_BY_SHARES",
            source=SourceMetadata(
                source_system=SourceSystem.ACRA,
                environment=SourceEnvironment.MOCK,
                registry_source_link="https://mock.acra.gov.sg/entities/202400001A",
                retrieved_at=FIXED_TIME,
            ),
        )
        return OnboardingCase(
            case_id=case_id,
            source_case_id="CASE-SYNTHETIC",
            correlation_id=UUID("00000000-0000-4000-8000-000000000403"),
            requested_uen="202400001A",
            state=WorkflowState.COMPLETED,
            entity=entity,
            created_at=FIXED_TIME,
            updated_at=FIXED_TIME,
        )


class IncrementingClock:
    def __init__(self) -> None:
        self.current = FIXED_TIME

    def __call__(self) -> datetime:
        result = self.current
        self.current += timedelta(microseconds=1)
        return result


class FailOnceClock(IncrementingClock):
    def __init__(self, fail_at: int) -> None:
        super().__init__()
        self.calls = 0
        self.fail_at = fail_at

    def __call__(self) -> datetime:
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("PRIVATE_CLOCK_SENTINEL")
        return super().__call__()


class FailOnceRepository(InMemoryOwnershipAnalysisRepository):
    def __init__(self, fail_at: int) -> None:
        super().__init__()
        self.calls = 0
        self.fail_at = fail_at

    def save(self, record, *, expected_version):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError("PRIVATE_REPOSITORY_SENTINEL")
        return super().save(record, expected_version=expected_version)


class BarrierRepository(InMemoryOwnershipAnalysisRepository):
    def __init__(
        self,
        *,
        state: OwnershipAnalysisState,
        participants: int = 2,
        create_only: bool = False,
    ) -> None:
        super().__init__()
        self.state = state
        self.barrier = Barrier(participants)
        self.create_only = create_only

    def save(self, record, *, expected_version):  # type: ignore[no-untyped-def]
        if record.state == self.state and (not self.create_only or expected_version is None):
            self.barrier.wait(timeout=5)
        return super().save(record, expected_version=expected_version)


class StubProvider:
    def __init__(self, result: object, metadata: object | None = None) -> None:
        self.result = result
        self._metadata = metadata or {
            "provider_name": "LOCAL_GRAPH",
            "environment": "LOCAL",
        }
        self.calls = 0

    @property
    def metadata(self) -> object:
        return self._metadata

    def load(self, request: object) -> object:
        self.calls += 1
        return self.result


def provenance(reference: str = "LOCAL_REL") -> dict[str, object]:
    return {
        "provider": "LOCAL_GRAPH",
        "environment": "LOCAL",
        "source_reference": reference,
        "sourced_at": FIXED_TIME,
    }


def source_result(
    parties: list[dict[str, object]], relationships: list[dict[str, object]]
) -> dict[str, object]:
    return {
        "root_party_id": "ROOT",
        "parties": [
            {
                "party_id": "ROOT",
                "display_name": "MERLION CIRCULAR LABS PTE. LTD.",
                "party_type": "LEGAL_ENTITY",
                "registration_number": "202400001A",
                "country": "SG",
            },
            *parties,
        ],
        "relationships": relationships,
    }


def relationship(relationship_id: str, parent: str, child: str, percent: str) -> dict[str, object]:
    return {
        "relationship_id": relationship_id,
        "parent_party_id": parent,
        "child_party_id": child,
        "ownership_percent": percent,
        "relationship_type": "OWNERSHIP",
        "basis": "SHARE_OWNERSHIP",
        "provenance": provenance(relationship_id),
    }


def make_service(
    *,
    provider: Any | None = None,
    threshold: Decimal = Decimal("25"),
    repository: InMemoryOwnershipAnalysisRepository | None = None,
    clock: Any | None = None,
    max_parties: int = 100,
    max_relationships: int = 200,
    max_depth: int = 8,
    max_paths_per_candidate: int = 64,
    max_total_paths: int = 256,
) -> tuple[OwnershipAnalysisService, InMemoryOwnershipAnalysisRepository]:
    active_repository = repository or InMemoryOwnershipAnalysisRepository()
    service = OwnershipAnalysisService(
        cases=Cases(),
        provider=provider or MockOwnershipProvider(),
        repository=active_repository,
        threshold_percent=threshold,
        max_parties=max_parties,
        max_relationships=max_relationships,
        max_depth=max_depth,
        max_paths_per_candidate=max_paths_per_candidate,
        max_total_paths=max_total_paths,
        clock=clock or IncrementingClock(),
        uuid_factory=uuid4,
    )
    return service, active_repository


def run_scenario(
    scenario: MockOwnershipScenario,
    *,
    threshold: Decimal = Decimal("25"),
) -> object:
    service, _ = make_service(threshold=threshold)
    service.load(case_id=CASE_ID, provider=MockOwnershipProvider(scenario))
    return service.analyze(case_id=CASE_ID)


@pytest.mark.parametrize("value", ["0", "-1", "100.000001", "NaN", "Infinity", "-Infinity"])
def test_percentage_validation_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(ValidationError):
        OwnershipRelationship(
            relationship_id="REL",
            parent_party_id="ROOT",
            child_party_id="PERSON",
            ownership_percent=Decimal(value),
            provenance=OwnershipProvenance(
                provider="LOCAL_GRAPH",
                environment=OwnershipEnvironment.LOCAL,
                source_reference="LOCAL_REL",
                sourced_at=FIXED_TIME,
            ),
        )


def test_party_validation_rejects_invalid_type_duplicate_ids_and_unknown_endpoints() -> None:
    invalid_type = source_result(
        [{"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "HUMAN"}],
        [],
    )
    duplicate = source_result(
        [{"party_id": "ROOT", "display_name": "Duplicate", "party_type": "LEGAL_ENTITY"}],
        [],
    )
    unknown = source_result([], [relationship("REL", "ROOT", "UNKNOWN", "25")])
    for value in (invalid_type, duplicate, unknown):
        service, repository = make_service(provider=StubProvider(value))
        with pytest.raises(OwnershipInfrastructureError):
            service.load(case_id=CASE_ID)
        stored = repository.get_for_case(CASE_ID)
        assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
        assert stored.error is not None and stored.error.code == "OWNERSHIP_MALFORMED_SOURCE"


@pytest.mark.parametrize(
    "relationships",
    [
        [relationship("REL", "ROOT", "ROOT", "25")],
        [relationship("REL", "ROOT", "PERSON", "25"), relationship("REL", "ROOT", "PERSON", "25")],
    ],
)
def test_self_edge_and_duplicate_relationship_id_terminalize(
    relationships: list[dict[str, object]],
) -> None:
    people = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"}
    ]
    service, repository = make_service(provider=StubProvider(source_result(people, relationships)))
    with pytest.raises(OwnershipInfrastructureError):
        service.load(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED


def test_direct_ownership_uses_exact_decimal_and_inclusive_threshold() -> None:
    record = run_scenario(MockOwnershipScenario.DIRECT_OWNER)
    assert record.state == OwnershipAnalysisState.ANALYZED
    assert [item.aggregated_ownership_percent for item in record.candidates] == [
        Decimal("60"),
        Decimal("40"),
    ]
    assert all(
        item.classification == OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
        for item in record.candidates
    )
    assert all(
        item.direct_ownership_percent == item.aggregated_ownership_percent
        for item in record.candidates
    )
    assert record.events[-1].candidate_count == 2


def test_indirect_two_level_calculation_retains_path_evidence() -> None:
    record = run_scenario(MockOwnershipScenario.INDIRECT_OWNER)
    results = {item.party.party_id: item for item in record.candidates}
    assert results["PERSON_C"].aggregated_ownership_percent == Decimal("30.00")
    assert results["PERSON_D"].aggregated_ownership_percent == Decimal("10.00")
    assert results["PERSON_C"].direct_ownership_percent == Decimal("0")
    assert results["PERSON_C"].paths[0].calculation == "40% x 75% = 30%"
    assert [edge.ownership_percent for edge in results["PERSON_C"].paths[0].edges] == [
        Decimal("40"),
        Decimal("75"),
    ]


def test_three_level_decimal_precision_is_exact() -> None:
    parties = [
        {"party_id": "HOLDING_1", "display_name": "Holding One", "party_type": "LEGAL_ENTITY"},
        {"party_id": "HOLDING_2", "display_name": "Holding Two", "party_type": "LEGAL_ENTITY"},
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"},
    ]
    relationships = [
        relationship("REL_1", "ROOT", "HOLDING_1", "33.333333"),
        relationship("REL_2", "HOLDING_1", "HOLDING_2", "30"),
        relationship("REL_3", "HOLDING_2", "PERSON", "50"),
    ]
    service, _ = make_service(provider=StubProvider(source_result(parties, relationships)))
    service.load(case_id=CASE_ID)
    candidate = service.analyze(case_id=CASE_ID).candidates[0]
    assert candidate.aggregated_ownership_percent == Decimal("4.9999999500")
    assert candidate.paths[0].calculation == "33.333333% x 30% x 50% = 4.99999995%"


def test_multiple_independent_paths_aggregate_once() -> None:
    record = run_scenario(MockOwnershipScenario.MULTIPLE_PATHS)
    result = next(item for item in record.candidates if item.party.party_id == "PERSON_A")
    assert result.direct_ownership_percent == Decimal("20")
    assert result.indirect_ownership_percent == Decimal("20.00")
    assert result.aggregated_ownership_percent == Decimal("40.00")
    assert len(result.paths) == 2
    assert len({path.path_id for path in result.paths}) == 2


@pytest.mark.parametrize(
    ("threshold", "percent", "classification", "result"),
    [
        (
            Decimal("25"),
            Decimal("20"),
            OwnershipCandidateClassification.BELOW_PROVISIONAL_THRESHOLD,
            OwnershipThresholdResult.NOT_MET,
        ),
        (
            Decimal("40"),
            Decimal("40"),
            OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
            OwnershipThresholdResult.MET,
        ),
        (
            Decimal("39.999999"),
            Decimal("40"),
            OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE,
            OwnershipThresholdResult.MET,
        ),
    ],
)
def test_configurable_threshold_below_exact_and_above(
    threshold: Decimal,
    percent: Decimal,
    classification: OwnershipCandidateClassification,
    result: OwnershipThresholdResult,
) -> None:
    scenario = (
        MockOwnershipScenario.BELOW_THRESHOLD
        if percent == Decimal("20")
        else MockOwnershipScenario.MULTIPLE_PATHS
    )
    record = run_scenario(scenario, threshold=threshold)
    candidate = next(item for item in record.candidates if item.party.party_id == "PERSON_A")
    assert candidate.aggregated_ownership_percent == percent
    assert candidate.classification == classification
    assert candidate.threshold_result == result
    assert candidate.threshold_comparator == "GREATER_THAN_OR_EQUAL_TO"


@pytest.mark.parametrize(
    ("scenario", "issue"),
    [
        (MockOwnershipScenario.INCOMPLETE_CHAIN, OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY),
        (MockOwnershipScenario.CYCLE, OwnershipIssueCode.CYCLE_DETECTED),
    ],
)
def test_incomplete_and_cycle_route_to_review_without_false_candidate(
    scenario: MockOwnershipScenario, issue: OwnershipIssueCode
) -> None:
    record = run_scenario(scenario)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.candidates == []
    assert issue in {item.code for item in record.issues}
    assert record.events[-1].event_type.value == "OWNERSHIP_REVIEW_REQUIRED"


def test_depth_limit_routes_to_review_without_truncated_definitive_result() -> None:
    parties = [
        {"party_id": "HOLDING", "display_name": "Holding", "party_type": "LEGAL_ENTITY"},
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"},
    ]
    relationships = [
        relationship("REL_1", "ROOT", "HOLDING", "50"),
        relationship("REL_2", "HOLDING", "PERSON", "50"),
    ]
    service, _ = make_service(
        provider=StubProvider(source_result(parties, relationships)), max_depth=1
    )
    service.load(case_id=CASE_ID)
    record = service.analyze(case_id=CASE_ID)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert record.candidates == []
    assert {item.code for item in record.issues} == {OwnershipIssueCode.MAXIMUM_DEPTH_EXCEEDED}


def test_path_limit_marks_all_retained_results_non_definitive() -> None:
    record = run_scenario(MockOwnershipScenario.MULTIPLE_PATHS)
    assert record.state == OwnershipAnalysisState.ANALYZED
    service, _ = make_service(max_paths_per_candidate=1)
    service.load(
        case_id=CASE_ID, provider=MockOwnershipProvider(MockOwnershipScenario.MULTIPLE_PATHS)
    )
    limited = service.analyze(case_id=CASE_ID)
    assert limited.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert OwnershipIssueCode.PATH_LIMIT_EXCEEDED in {item.code for item in limited.issues}
    assert all(
        item.classification == OwnershipCandidateClassification.REVIEW_REQUIRED
        for item in limited.candidates
    )

    total_limited_service, _ = make_service(max_total_paths=2)
    total_limited_service.load(
        case_id=CASE_ID,
        provider=MockOwnershipProvider(MockOwnershipScenario.INDIRECT_OWNER),
    )
    total_limited = total_limited_service.analyze(case_id=CASE_ID)
    assert total_limited.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert OwnershipIssueCode.PATH_LIMIT_EXCEEDED in {item.code for item in total_limited.issues}
    assert all(
        item.classification == OwnershipCandidateClassification.REVIEW_REQUIRED
        for item in total_limited.candidates
    )


def test_graph_size_limits_fail_closed_during_source_loading() -> None:
    service, repository = make_service(max_parties=2)
    with pytest.raises(OwnershipInfrastructureError) as exc_info:
        service.load(
            case_id=CASE_ID,
            provider=MockOwnershipProvider(MockOwnershipScenario.DIRECT_OWNER),
        )
    assert exc_info.value.code == "OWNERSHIP_MALFORMED_SOURCE"
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED


def test_disconnected_graph_is_rejected_during_analysis() -> None:
    parties = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"},
        {"party_id": "ORPHAN", "display_name": "Orphan Entity", "party_type": "LEGAL_ENTITY"},
    ]
    relationships = [relationship("REL", "ROOT", "PERSON", "25")]
    service, repository = make_service(provider=StubProvider(source_result(parties, relationships)))
    service.load(case_id=CASE_ID)
    with pytest.raises(OwnershipInfrastructureError) as exc_info:
        service.analyze(case_id=CASE_ID)
    assert exc_info.value.code == "OWNERSHIP_GRAPH_INVALID"
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.candidates == []


def test_non_mock_provider_works_without_scenario_in_generic_contract() -> None:
    people = [
        {
            "party_id": "PERSON",
            "display_name": "Local Synthetic Person",
            "party_type": "NATURAL_PERSON",
        }
    ]
    provider = StubProvider(source_result(people, [relationship("REL", "ROOT", "PERSON", "25")]))
    service, _ = make_service(provider=provider)
    loaded = service.load(case_id=CASE_ID)
    analyzed = service.analyze(case_id=CASE_ID)
    assert provider.calls == 1
    assert loaded.provider_environment == OwnershipEnvironment.LOCAL
    assert (
        analyzed.candidates[0].classification
        == OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
    )
    assert "scenario" not in analyzed.model_dump_json().lower()


@pytest.mark.parametrize(
    ("metadata", "source_reference"),
    [
        ({"provider_name": " ", "environment": "LOCAL"}, "LOCAL_REL"),
        ({"provider_name": "LOCAL\nGRAPH", "environment": "LOCAL"}, "LOCAL_REL"),
        ({"provider_name": "LOCAL_GRAPH", "environment": "LOCAL"}, "PRIVATE\nREFERENCE"),
        ({"provider_name": "LOCAL_GRAPH", "environment": "LOCAL"}, "X" * 129),
    ],
)
def test_unsafe_provider_provenance_terminalizes_without_retention(
    metadata: object, source_reference: str
) -> None:
    people = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"}
    ]
    value = source_result(people, [relationship("REL", "ROOT", "PERSON", "25")])
    value["relationships"][0]["provenance"]["source_reference"] = source_reference  # type: ignore[index]
    service, repository = make_service(provider=StubProvider(value, metadata))
    with pytest.raises(OwnershipInfrastructureError):
        service.load(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert source_reference not in stored.model_dump_json()


def test_provider_failure_is_retrievable_sanitized_and_parent_is_unchanged() -> None:
    cases = Cases()
    before = cases.get_case(CASE_ID)
    service, repository = make_service()
    with pytest.raises(OwnershipInfrastructureError) as exc_info:
        service.load(
            case_id=CASE_ID,
            provider=MockOwnershipProvider(MockOwnershipScenario.PROVIDER_FAILURE),
        )
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.error is not None and stored.error.code == "OWNERSHIP_PROVIDER_FAILED"
    assert stored.events[-1].event_type.value == "OWNERSHIP_ANALYSIS_FAILED"
    assert cases.get_case(CASE_ID) == before
    assert "OwnershipProviderError" not in stored.model_dump_json()
    assert exc_info.value.analysis_id == stored.analysis_id


@pytest.mark.parametrize(
    "target",
    [
        "build_ownership_graph",
        "validate_ownership_graph",
        "calculate_ownership_paths",
        "aggregate_ownership_paths",
        "build_ownership_candidates",
    ],
)
def test_post_acceptance_stage_failures_terminalize(
    monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    service, repository = make_service()
    service.load(case_id=CASE_ID)

    def fail(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise RuntimeError("PRIVATE_STAGE_SENTINEL")

    monkeypatch.setattr(f"app.services.ownership_analysis.{target}", fail)
    with pytest.raises(OwnershipInfrastructureError):
        service.analyze(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.candidates == []
    assert stored.events[-1].state == OwnershipAnalysisState.FAILED
    assert "PRIVATE_STAGE_SENTINEL" not in stored.model_dump_json()


def test_clock_and_recoverable_repository_failure_do_not_strand_analyzing() -> None:
    clock = FailOnceClock(fail_at=6)
    service, repository = make_service(clock=clock)
    service.load(case_id=CASE_ID)
    with pytest.raises(OwnershipInfrastructureError):
        service.analyze(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED

    fail_repository = FailOnceRepository(fail_at=4)
    second, _ = make_service(repository=fail_repository)
    second.load(case_id=CASE_ID)
    with pytest.raises(OwnershipInfrastructureError):
        second.analyze(case_id=CASE_ID)
    recovered = fail_repository.get_for_case(CASE_ID)
    assert recovered is not None and recovered.state == OwnershipAnalysisState.FAILED
    assert all(event.state != OwnershipAnalysisState.ANALYZING for event in recovered.events)


def test_case_isolation_keeps_separate_records() -> None:
    service, _ = make_service()
    first = service.load(case_id=CASE_ID)
    second = service.load(
        case_id=OTHER_CASE_ID,
        provider=MockOwnershipProvider(MockOwnershipScenario.BELOW_THRESHOLD),
    )
    assert first.analysis_id != second.analysis_id
    assert service.get(case_id=CASE_ID) == first
    assert service.get(case_id=OTHER_CASE_ID) == second


@pytest.mark.parametrize(
    ("parties", "relationships"),
    [
        (
            [
                {
                    "party_id": "PERSON_A",
                    "display_name": "Person A",
                    "party_type": "NATURAL_PERSON",
                },
                {
                    "party_id": "PERSON_B",
                    "display_name": "Person B",
                    "party_type": "NATURAL_PERSON",
                },
            ],
            [
                relationship("REL_1", "ROOT", "PERSON_A", "25"),
                relationship("REL_2", "PERSON_A", "PERSON_B", "100"),
            ],
        ),
        (
            [
                {"party_id": "LEGAL_A", "display_name": "Legal A", "party_type": "LEGAL_ENTITY"},
                {
                    "party_id": "PERSON_A",
                    "display_name": "Person A",
                    "party_type": "NATURAL_PERSON",
                },
                {
                    "party_id": "PERSON_B",
                    "display_name": "Person B",
                    "party_type": "NATURAL_PERSON",
                },
            ],
            [
                relationship("REL_1", "ROOT", "LEGAL_A", "50"),
                relationship("REL_2", "LEGAL_A", "PERSON_A", "50"),
                relationship("REL_3", "PERSON_A", "PERSON_B", "100"),
            ],
        ),
        (
            [
                {
                    "party_id": "VALID",
                    "display_name": "Valid Person",
                    "party_type": "NATURAL_PERSON",
                },
                {"party_id": "LEGAL_A", "display_name": "Legal A", "party_type": "LEGAL_ENTITY"},
                {
                    "party_id": "PERSON_A",
                    "display_name": "Person A",
                    "party_type": "NATURAL_PERSON",
                },
                {
                    "party_id": "PERSON_B",
                    "display_name": "Person B",
                    "party_type": "NATURAL_PERSON",
                },
            ],
            [
                relationship("REL_VALID", "ROOT", "VALID", "60"),
                relationship("REL_1", "ROOT", "LEGAL_A", "40"),
                relationship("REL_2", "LEGAL_A", "PERSON_A", "50"),
                relationship("REL_3", "PERSON_A", "PERSON_B", "100"),
            ],
        ),
        (
            [
                {"party_id": "LEGAL_A", "display_name": "Legal A", "party_type": "LEGAL_ENTITY"},
                {"party_id": "LEGAL_B", "display_name": "Legal B", "party_type": "LEGAL_ENTITY"},
                {
                    "party_id": "PERSON_A",
                    "display_name": "Person A",
                    "party_type": "NATURAL_PERSON",
                },
                {
                    "party_id": "PERSON_B",
                    "display_name": "Person B",
                    "party_type": "NATURAL_PERSON",
                },
            ],
            [
                relationship("REL_1", "ROOT", "LEGAL_A", "80"),
                relationship("REL_2", "LEGAL_A", "LEGAL_B", "75"),
                relationship("REL_3", "LEGAL_B", "PERSON_A", "50"),
                relationship("REL_4", "PERSON_A", "PERSON_B", "100"),
            ],
        ),
    ],
)
def test_natural_person_parent_edges_fail_graph_semantics_without_candidates(
    parties: list[dict[str, object]], relationships: list[dict[str, object]]
) -> None:
    service, repository = make_service(provider=StubProvider(source_result(parties, relationships)))
    loaded = service.load(case_id=CASE_ID)
    assert loaded.state == OwnershipAnalysisState.LOADED
    with pytest.raises(OwnershipInfrastructureError) as exc_info:
        service.analyze(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert exc_info.value.code == "OWNERSHIP_GRAPH_INVALID"
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.candidates == []


@pytest.mark.parametrize(
    "unsafe_reference",
    [
        "https://private.example/hierarchy",
        "user@example",
        "hierarchy?access=value",
        "hierarchy#fragment",
        "bearer-value",
        "token-value",
        "accessTokenValue",
        "case-api_key-value",
        '{"raw":"body"}',
        " ",
        "X" * 129,
    ],
)
def test_source_reference_is_a_safe_opaque_identifier(unsafe_reference: str) -> None:
    people = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"}
    ]
    value = source_result(people, [relationship("REL", "ROOT", "PERSON", "25")])
    value["relationships"][0]["provenance"]["source_reference"] = unsafe_reference  # type: ignore[index]
    service, repository = make_service(provider=StubProvider(value))
    with pytest.raises(OwnershipInfrastructureError):
        service.load(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.relationships == []
    assert stored.provider_name is None


def test_mutated_existing_provider_metadata_is_freshly_revalidated() -> None:
    metadata = OwnershipProviderMetadata(provider_name="LOCAL_GRAPH", environment="LOCAL")
    object.__setattr__(metadata, "provider_name", "LOCAL\nGRAPH")
    people = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"}
    ]
    value = source_result(people, [relationship("REL", "ROOT", "PERSON", "25")])
    service, repository = make_service(provider=StubProvider(value, metadata))
    with pytest.raises(OwnershipInfrastructureError):
        service.load(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and "LOCAL\\nGRAPH" not in stored.model_dump_json()


@pytest.mark.parametrize(
    ("target", "field", "mutated_value"),
    [
        ("provenance", "source_reference", "https://private.example/hierarchy?token=value"),
        ("party", "display_name", "Unsafe\nPerson"),
        ("relationship", "relationship_id", "REL?query=value"),
        ("relationship", "ownership_percent", Decimal("0")),
    ],
)
def test_mutated_existing_source_models_cannot_bypass_fresh_nested_validation(
    target: str, field: str, mutated_value: object
) -> None:
    people = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"}
    ]
    model = OwnershipSourceResult.model_validate(
        source_result(people, [relationship("REL", "ROOT", "PERSON", "25")])
    )
    selected = {
        "provenance": model.relationships[0].provenance,
        "party": model.parties[1],
        "relationship": model.relationships[0],
    }[target]
    object.__setattr__(selected, field, mutated_value)
    service, repository = make_service(provider=StubProvider(model))
    with pytest.raises(OwnershipInfrastructureError):
        service.load(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.parties == []
    assert stored.relationships == []


def test_mutated_provider_subclass_is_also_detached_and_revalidated() -> None:
    class ProviderSourceSubclass(OwnershipSourceResult):
        pass

    people = [
        {
            "party_id": "PERSON",
            "display_name": "Synthetic Person",
            "party_type": "NATURAL_PERSON",
        }
    ]
    model = ProviderSourceSubclass.model_validate(
        source_result(people, [relationship("REL", "ROOT", "PERSON", "25")])
    )
    object.__setattr__(model.parties[1], "display_name", "Unsafe\nSubclass")
    service, repository = make_service(provider=StubProvider(model))
    with pytest.raises(OwnershipInfrastructureError):
        service.load(case_id=CASE_ID)
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.parties == []


@pytest.mark.parametrize("depth", [8, 64])
def test_digest_path_id_accepts_maximum_source_ids_at_configured_depth(depth: int) -> None:
    parties: list[dict[str, object]] = []
    relationships: list[dict[str, object]] = []
    parent = "ROOT"
    for index in range(depth):
        child = "PERSON" if index == depth - 1 else f"LEGAL_{index:02d}"
        party_type = "NATURAL_PERSON" if index == depth - 1 else "LEGAL_ENTITY"
        parties.append({"party_id": child, "display_name": child, "party_type": party_type})
        prefix = f"R{index:02d}"
        relationship_id = prefix + ("X" * (64 - len(prefix)))
        relationships.append(relationship(relationship_id, parent, child, "100"))
        parent = child

    service, _ = make_service(
        provider=StubProvider(source_result(parties, relationships)),
        max_depth=depth,
        max_parties=depth + 1,
        max_relationships=depth,
        max_paths_per_candidate=1,
        max_total_paths=depth,
    )
    service.load(case_id=CASE_ID)
    record = service.analyze(case_id=CASE_ID)
    path = record.candidates[0].paths[0]
    assert record.state == OwnershipAnalysisState.ANALYZED
    assert len(path.path_id) == 72
    assert path.path_id.startswith("path-v1-")
    assert len(path.edges) == depth


def test_similar_ordered_paths_have_distinct_digest_ids_and_aggregate_once() -> None:
    people = [
        {"party_id": "PERSON", "display_name": "Synthetic Person", "party_type": "NATURAL_PERSON"}
    ]
    relationships = [
        relationship("REL_PATH_0001", "ROOT", "PERSON", "20"),
        relationship("REL_PATH_0002", "ROOT", "PERSON", "20"),
    ]
    service, _ = make_service(provider=StubProvider(source_result(people, relationships)))
    service.load(case_id=CASE_ID)
    candidate = service.analyze(case_id=CASE_ID).candidates[0]
    assert candidate.aggregated_ownership_percent == Decimal("40")
    assert len(candidate.paths) == 2
    assert len({path.path_id for path in candidate.paths}) == 2


def test_same_ordered_path_has_the_same_digest_id_across_analyses() -> None:
    people = [
        {
            "party_id": "PERSON",
            "display_name": "Synthetic Person",
            "party_type": "NATURAL_PERSON",
        }
    ]
    result = source_result(people, [relationship("REL_STABLE", "ROOT", "PERSON", "25")])
    first, _ = make_service(provider=StubProvider(result))
    second, _ = make_service(provider=StubProvider(result))
    first.load(case_id=CASE_ID)
    second.load(case_id=OTHER_CASE_ID)
    assert (
        first.analyze(case_id=CASE_ID).candidates[0].paths[0].path_id
        == second.analyze(case_id=OTHER_CASE_ID).candidates[0].paths[0].path_id
    )


@pytest.mark.parametrize("threshold", ["0.000001", "25.000001", "100.000000"])
def test_settings_accept_ownership_threshold_precision_contract(threshold: str) -> None:
    settings = Settings(app_env="test", ubo_ownership_threshold_percent=threshold)
    assert settings.ubo_ownership_threshold_percent == Decimal(threshold)


@pytest.mark.parametrize("threshold", ["0", "25.0000001", "100.000001"])
def test_settings_reject_invalid_or_excess_threshold_precision(threshold: str) -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="test", ubo_ownership_threshold_percent=threshold)
    with pytest.raises(ValueError):
        make_service(threshold=Decimal(threshold))


def test_failed_terminal_rejects_synchronized_stale_success_and_preserves_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, repository = make_service()
    stale = service.load(case_id=CASE_ID)
    terminal_saved = Event()

    def fail(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise RuntimeError("PRIVATE_FAILURE_SENTINEL")

    monkeypatch.setattr("app.services.ownership_analysis.build_ownership_graph", fail)

    def persist_failure() -> str:
        try:
            service.analyze(case_id=CASE_ID)
        except OwnershipInfrastructureError:
            terminal_saved.set()
            return "FAILED"
        raise AssertionError("failure invocation unexpectedly succeeded")

    def attempt_stale_success() -> str:
        assert terminal_saved.wait(timeout=5)
        candidate = stale.model_copy(update={"state": OwnershipAnalysisState.ANALYZED}, deep=True)
        with pytest.raises(OwnershipRepositoryConflictError):
            repository.save(candidate, expected_version=stale.version)
        return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        failure = executor.submit(persist_failure)
        stale_success = executor.submit(attempt_stale_success)
        results = {failure.result(), stale_success.result()}
    stored = repository.get_for_case(CASE_ID)
    assert results == {"FAILED", "REJECTED"}
    assert stored is not None and stored.state == OwnershipAnalysisState.FAILED
    assert stored.events[-1].event_type.value == "OWNERSHIP_ANALYSIS_FAILED"


def test_analyzed_terminal_rejects_synchronized_stale_failure_and_preserves_event() -> None:
    service, repository = make_service()
    stale = service.load(case_id=CASE_ID)
    terminal_saved = Event()

    def persist_success() -> str:
        assert service.analyze(case_id=CASE_ID).state == OwnershipAnalysisState.ANALYZED
        terminal_saved.set()
        return "ANALYZED"

    def attempt_stale_failure() -> str:
        assert terminal_saved.wait(timeout=5)
        candidate = stale.model_copy(update={"state": OwnershipAnalysisState.FAILED}, deep=True)
        with pytest.raises(OwnershipRepositoryConflictError):
            repository.save(candidate, expected_version=stale.version)
        return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        success = executor.submit(persist_success)
        stale_failure = executor.submit(attempt_stale_failure)
        assert {success.result(), stale_failure.result()} == {"ANALYZED", "REJECTED"}
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.state == OwnershipAnalysisState.ANALYZED
    assert stored.events[-1].event_type.value == "OWNERSHIP_ANALYSIS_COMPLETED"


def test_two_simultaneous_analyze_calls_accept_exactly_one_transition() -> None:
    repository = BarrierRepository(state=OwnershipAnalysisState.ANALYZING)
    service, _ = make_service(repository=repository)
    service.load(case_id=CASE_ID)

    def analyze() -> str:
        try:
            return service.analyze(case_id=CASE_ID).state.value
        except OwnershipRequestError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(analyze) for _ in range(2)]
        results = {future.result() for future in futures}
    stored = repository.get_for_case(CASE_ID)
    assert results == {"ANALYZED", "OWNERSHIP_ANALYSIS_CONFLICT"}
    assert stored is not None and stored.state == OwnershipAnalysisState.ANALYZED
    assert [event.event_type.value for event in stored.events].count(
        "OWNERSHIP_ANALYSIS_STARTED"
    ) == 1


def test_duplicate_simultaneous_load_accepts_exactly_one_create() -> None:
    repository = BarrierRepository(state=OwnershipAnalysisState.LOADING, create_only=True)
    service, _ = make_service(repository=repository)

    def load() -> str:
        try:
            return service.load(case_id=CASE_ID).state.value
        except OwnershipRequestError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(load) for _ in range(2)]
        results = {future.result() for future in futures}
    stored = repository.get_for_case(CASE_ID)
    assert results == {"LOADED", "OWNERSHIP_ALREADY_LOADED"}
    assert stored is not None and stored.state == OwnershipAnalysisState.LOADED
    assert [event.event_type.value for event in stored.events].count("OWNERSHIP_LOAD_STARTED") == 1


def test_terminal_record_cannot_reenter_analyzing_or_lose_history() -> None:
    service, repository = make_service()
    service.load(case_id=CASE_ID)
    terminal = service.analyze(case_id=CASE_ID)
    history = terminal.events
    stale = terminal.model_copy(
        update={"state": OwnershipAnalysisState.ANALYZING, "version": terminal.version - 1},
        deep=True,
    )
    with pytest.raises(OwnershipRepositoryConflictError):
        repository.save(stale, expected_version=stale.version)
    assert service.analyze(case_id=CASE_ID) == terminal
    stored = repository.get_for_case(CASE_ID)
    assert stored is not None and stored.events == history
