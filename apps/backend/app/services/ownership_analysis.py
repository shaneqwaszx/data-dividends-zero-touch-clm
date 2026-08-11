"""Bounded ownership loading, graph traversal, aggregation, and classification."""

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Never, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.connectors.ownership import (
    OwnershipProvider,
    OwnershipProviderError,
    OwnershipProviderMetadata,
    OwnershipProviderRequest,
    OwnershipSourceResult,
)
from app.domain.models import EventOutcome, OnboardingCase, SafeError
from app.domain.ownership import (
    OwnershipAnalysisIssue,
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipCandidate,
    OwnershipCandidateClassification,
    OwnershipEventType,
    OwnershipIssueCode,
    OwnershipPathEdge,
    OwnershipPathEvidence,
    OwnershipPercent,
    OwnershipRelationship,
    OwnershipThresholdResult,
    OwnershipWorkflowEvent,
    Party,
    PartyType,
)
from app.services.ownership_errors import (
    OwnershipInfrastructureError,
    OwnershipRequestError,
)
from app.services.ownership_repository import (
    OwnershipAnalysisRepository,
    OwnershipRepositoryConflictError,
)

_OWNERSHIP_PERCENT_ADAPTER = TypeAdapter(OwnershipPercent)


class OnboardingCaseReader(Protocol):
    def get_case(self, case_id: UUID) -> OnboardingCase | None: ...


class OwnershipGraphError(Exception):
    """Known unsafe provider graph that must terminalize without raw detail."""


@dataclass(frozen=True)
class OwnershipGraph:
    root_party_id: str
    parties: dict[str, Party]
    adjacency: dict[str, tuple[OwnershipRelationship, ...]]


@dataclass(frozen=True)
class PathCalculation:
    paths_by_party: dict[str, tuple[OwnershipPathEvidence, ...]]
    issues: tuple[OwnershipAnalysisIssue, ...]


def build_ownership_graph(source: OwnershipSourceResult) -> OwnershipGraph:
    """Build a deterministic adjacency list without mutating provider models."""

    parties = {party.party_id: party.model_copy(deep=True) for party in source.parties}
    adjacency_lists: dict[str, list[OwnershipRelationship]] = defaultdict(list)
    for relationship in source.relationships:
        if (
            relationship.parent_party_id not in parties
            or relationship.child_party_id not in parties
        ):
            raise OwnershipGraphError
        if relationship.parent_party_id == relationship.child_party_id:
            raise OwnershipGraphError
        adjacency_lists[relationship.parent_party_id].append(relationship.model_copy(deep=True))
    adjacency = {
        party_id: tuple(sorted(items, key=lambda item: item.relationship_id))
        for party_id, items in adjacency_lists.items()
    }
    return OwnershipGraph(
        root_party_id=source.root_party_id,
        parties=parties,
        adjacency=adjacency,
    )


def validate_ownership_graph(graph: OwnershipGraph) -> None:
    """Reject disconnected or semantically invalid owned-party-to-owner graphs."""

    for relationships in graph.adjacency.values():
        for relationship in relationships:
            parent = graph.parties[relationship.parent_party_id]
            if parent.party_type != PartyType.LEGAL_ENTITY:
                raise OwnershipGraphError

    reachable = {graph.root_party_id}
    queue = deque([graph.root_party_id])
    while queue:
        current = queue.popleft()
        for relationship in graph.adjacency.get(current, ()):
            if relationship.child_party_id not in reachable:
                reachable.add(relationship.child_party_id)
                queue.append(relationship.child_party_id)
    if reachable != set(graph.parties):
        raise OwnershipGraphError


def calculate_ownership_paths(
    graph: OwnershipGraph,
    *,
    max_depth: int,
    max_paths_per_candidate: int,
    max_total_paths: int,
) -> PathCalculation:
    """Iteratively enumerate unique bounded root-to-natural-person paths."""

    paths: dict[str, list[OwnershipPathEvidence]] = defaultdict(list)
    path_keys: set[tuple[str, ...]] = set()
    issues: dict[tuple[OwnershipIssueCode, tuple[str, ...]], OwnershipAnalysisIssue] = {}
    stack: list[tuple[str, tuple[OwnershipRelationship, ...], frozenset[str], Decimal]] = [
        (graph.root_party_id, (), frozenset({graph.root_party_id}), Decimal("1"))
    ]
    total_paths = 0
    explored_path_states = 0
    traversal_limit_reached = False

    def add_issue(code: OwnershipIssueCode, message: str, party_ids: tuple[str, ...]) -> None:
        key = (code, party_ids)
        issues.setdefault(
            key,
            OwnershipAnalysisIssue(
                code=code,
                message=message,
                affected_party_ids=list(party_ids),
            ),
        )

    while stack:
        current_id, current_edges, visited, current_fraction = stack.pop()
        outgoing = graph.adjacency.get(current_id, ())
        current_party = graph.parties[current_id]
        if not outgoing and current_party.party_type == PartyType.LEGAL_ENTITY:
            add_issue(
                OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY,
                "A reachable legal-entity ownership chain has no disclosed owners.",
                (current_id,),
            )
            continue

        for relationship in reversed(outgoing):
            explored_path_states += 1
            if explored_path_states > max_total_paths:
                add_issue(
                    OwnershipIssueCode.PATH_LIMIT_EXCEEDED,
                    "A project-defined ownership path limit was exceeded.",
                    (current_id,),
                )
                traversal_limit_reached = True
                break
            child_id = relationship.child_party_id
            if child_id in visited:
                add_issue(
                    OwnershipIssueCode.CYCLE_DETECTED,
                    "A circular ownership path was detected and excluded from calculation.",
                    (current_id, child_id),
                )
                continue
            next_edges = current_edges + (relationship,)
            if len(next_edges) > max_depth:
                add_issue(
                    OwnershipIssueCode.MAXIMUM_DEPTH_EXCEEDED,
                    "The project-defined maximum ownership traversal depth was exceeded.",
                    (child_id,),
                )
                continue

            child = graph.parties[child_id]
            next_fraction = current_fraction * (relationship.ownership_percent / Decimal("100"))
            if child.party_type == PartyType.NATURAL_PERSON:
                path_key = tuple(item.relationship_id for item in next_edges)
                if path_key in path_keys:
                    continue
                if (
                    total_paths >= max_total_paths
                    or len(paths[child_id]) >= max_paths_per_candidate
                ):
                    add_issue(
                        OwnershipIssueCode.PATH_LIMIT_EXCEEDED,
                        "A project-defined ownership path limit was exceeded.",
                        (child_id,),
                    )
                    continue
                path_keys.add(path_key)
                total_paths += 1
                effective_percent = next_fraction * Decimal("100")
                evidence_edges = [
                    OwnershipPathEdge(
                        relationship_id=item.relationship_id,
                        parent_party_id=item.parent_party_id,
                        parent_display_name=graph.parties[item.parent_party_id].display_name,
                        child_party_id=item.child_party_id,
                        child_display_name=graph.parties[item.child_party_id].display_name,
                        ownership_percent=item.ownership_percent,
                    )
                    for item in next_edges
                ]
                paths[child_id].append(
                    OwnershipPathEvidence(
                        path_id=_path_id(path_key),
                        edges=evidence_edges,
                        effective_ownership_percent=effective_percent,
                        is_direct=len(next_edges) == 1,
                        calculation=_calculation_text(next_edges, effective_percent),
                    )
                )
                continue

            stack.append((child_id, next_edges, visited | {child_id}, next_fraction))

        if traversal_limit_reached:
            break

    return PathCalculation(
        paths_by_party={
            party_id: tuple(sorted(items, key=lambda item: item.path_id))
            for party_id, items in sorted(paths.items())
        },
        issues=tuple(
            sorted(
                issues.values(),
                key=lambda issue: (issue.code.value, tuple(issue.affected_party_ids)),
            )
        ),
    )


def aggregate_ownership_paths(
    calculation: PathCalculation,
) -> dict[str, tuple[Decimal, Decimal, Decimal]]:
    """Return exact direct, indirect, and aggregated percentages per person."""

    aggregated: dict[str, tuple[Decimal, Decimal, Decimal]] = {}
    for party_id, paths in calculation.paths_by_party.items():
        direct = sum(
            (path.effective_ownership_percent for path in paths if path.is_direct),
            start=Decimal("0"),
        )
        indirect = sum(
            (path.effective_ownership_percent for path in paths if not path.is_direct),
            start=Decimal("0"),
        )
        total = direct + indirect
        if total > Decimal("100"):
            raise OwnershipGraphError
        aggregated[party_id] = (direct, indirect, total)
    return aggregated


def build_ownership_candidates(
    graph: OwnershipGraph,
    calculation: PathCalculation,
    aggregated: dict[str, tuple[Decimal, Decimal, Decimal]],
    *,
    threshold_percent: Decimal,
) -> list[OwnershipCandidate]:
    """Apply the provisional inclusive threshold, or review classification on issues."""

    candidates: list[OwnershipCandidate] = []
    requires_review = bool(calculation.issues)
    for party_id, (direct, indirect, total) in sorted(aggregated.items()):
        party = graph.parties[party_id]
        if party.party_type != PartyType.NATURAL_PERSON:
            raise OwnershipGraphError
        if requires_review:
            threshold_result = OwnershipThresholdResult.INDETERMINATE
            classification = OwnershipCandidateClassification.REVIEW_REQUIRED
        elif total >= threshold_percent:
            threshold_result = OwnershipThresholdResult.MET
            classification = OwnershipCandidateClassification.PROVISIONAL_UBO_CANDIDATE
        else:
            threshold_result = OwnershipThresholdResult.NOT_MET
            classification = OwnershipCandidateClassification.BELOW_PROVISIONAL_THRESHOLD
        candidates.append(
            OwnershipCandidate(
                party=party.model_copy(deep=True),
                direct_ownership_percent=direct,
                indirect_ownership_percent=indirect,
                aggregated_ownership_percent=total,
                threshold_percent=threshold_percent,
                threshold_comparator="GREATER_THAN_OR_EQUAL_TO",
                threshold_result=threshold_result,
                classification=classification,
                paths=list(calculation.paths_by_party[party_id]),
            )
        )
    return candidates


class OwnershipAnalysisService:
    """Own the case-linked provider, validation, analysis, and terminal failure boundary."""

    def __init__(
        self,
        *,
        cases: OnboardingCaseReader,
        provider: OwnershipProvider,
        repository: OwnershipAnalysisRepository,
        threshold_percent: Decimal,
        max_parties: int,
        max_relationships: int,
        max_depth: int,
        max_paths_per_candidate: int,
        max_total_paths: int,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        try:
            validated_threshold = _OWNERSHIP_PERCENT_ADAPTER.validate_python(threshold_percent)
        except ValidationError as exc:
            raise ValueError(
                "ownership threshold must use the ownership percentage precision contract"
            ) from exc
        if (
            min(
                max_parties,
                max_relationships,
                max_depth,
                max_paths_per_candidate,
                max_total_paths,
            )
            <= 0
        ):
            raise ValueError("ownership safety limits must be positive")
        self._cases = cases
        self._provider = provider
        self._repository = repository
        self.threshold_percent = validated_threshold
        self.max_parties = max_parties
        self.max_relationships = max_relationships
        self.max_depth = max_depth
        self.max_paths_per_candidate = max_paths_per_candidate
        self.max_total_paths = max_total_paths
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    def load(
        self, *, case_id: UUID, provider: OwnershipProvider | None = None
    ) -> OwnershipAnalysisRecord:
        parent = self._cases.get_case(case_id)
        if parent is None:
            raise OwnershipRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        if self._repository.get_for_case(case_id) is not None:
            raise OwnershipRequestError(
                code="OWNERSHIP_ALREADY_LOADED",
                message="Ownership data has already been loaded for this case.",
            )
        if parent.entity is None or parent.entity.legal_name is None:
            raise OwnershipRequestError(
                code="OWNERSHIP_ROOT_UNAVAILABLE",
                message="The onboarding case has no canonical legal entity for ownership analysis.",
            )

        now = self._clock()
        record = OwnershipAnalysisRecord(
            case_id=case_id,
            analysis_id=self._uuid_factory(),
            correlation_id=self._uuid_factory(),
            state=OwnershipAnalysisState.LOADING,
            threshold_percent=self.threshold_percent,
            created_at=now,
            updated_at=now,
        )
        try:
            record = self._repository.save(record, expected_version=None)
        except OwnershipRepositoryConflictError:
            raise OwnershipRequestError(
                code="OWNERSHIP_ALREADY_LOADED",
                message="Ownership data has already been loaded for this case.",
            ) from None
        active_provider = provider or self._provider
        try:
            record = self._record(
                record,
                event_type=OwnershipEventType.OWNERSHIP_LOAD_STARTED,
                state=OwnershipAnalysisState.LOADING,
                outcome=EventOutcome.SUCCEEDED,
                message="Ownership source loading started.",
            )
            try:
                metadata = OwnershipProviderMetadata.model_validate(
                    _untrusted_to_primitives(active_provider.metadata)
                )
            except ValidationError:
                self._raise_terminal_failure(
                    record,
                    code="OWNERSHIP_MALFORMED_SOURCE",
                    message="Ownership source data could not be validated safely.",
                )
            try:
                provider_result = active_provider.load(
                    OwnershipProviderRequest(
                        case_id=case_id,
                        registration_number=parent.entity.registration_number,
                        display_name=parent.entity.legal_name,
                    )
                )
            except OwnershipProviderError:
                self._raise_terminal_failure(
                    record,
                    code="OWNERSHIP_PROVIDER_FAILED",
                    message="Ownership source loading could not be completed.",
                )
            try:
                source = OwnershipSourceResult.model_validate(
                    _untrusted_to_primitives(provider_result)
                )
            except ValidationError:
                self._raise_terminal_failure(
                    record,
                    code="OWNERSHIP_MALFORMED_SOURCE",
                    message="Ownership source data could not be validated safely.",
                )
            self._validate_source(source, metadata, parent.entity.registration_number)
            record.provider_name = metadata.provider_name
            record.provider_environment = metadata.environment
            record.root_party_id = source.root_party_id
            record.parties = [party.model_copy(deep=True) for party in source.parties]
            record.relationships = [item.model_copy(deep=True) for item in source.relationships]
            record.loaded_at = self._clock()
            record = self._record(
                record,
                event_type=OwnershipEventType.OWNERSHIP_LOADED,
                state=OwnershipAnalysisState.LOADED,
                outcome=EventOutcome.SUCCEEDED,
                message="Ownership source data loaded and validated.",
                party_count=len(record.parties),
                relationship_count=len(record.relationships),
            )
            return record.model_copy(deep=True)
        except OwnershipInfrastructureError:
            raise
        except OwnershipRepositoryConflictError:
            raise OwnershipRequestError(
                code="OWNERSHIP_LOAD_CONFLICT",
                message="Ownership loading was superseded by another request.",
            ) from None
        except OwnershipRequestError:
            raise
        except OwnershipGraphError:
            self._raise_terminal_failure(
                record,
                code="OWNERSHIP_MALFORMED_SOURCE",
                message="Ownership source data could not be validated safely.",
            )
        except Exception:
            self._raise_terminal_failure(
                record,
                code="OWNERSHIP_UNEXPECTED_FAILURE",
                message="Ownership source loading could not be completed.",
            )

    def analyze(self, *, case_id: UUID) -> OwnershipAnalysisRecord:
        record = self._repository.get_for_case(case_id)
        if record is None:
            if self._cases.get_case(case_id) is None:
                raise OwnershipRequestError(
                    code="ONBOARDING_CASE_NOT_FOUND",
                    message="The onboarding case was not found.",
                )
            raise OwnershipRequestError(
                code="OWNERSHIP_NOT_LOADED",
                message="Ownership data has not been loaded for this case.",
            )
        if record.state in {
            OwnershipAnalysisState.ANALYZED,
            OwnershipAnalysisState.REVIEW_REQUIRED,
        }:
            return record
        if record.state != OwnershipAnalysisState.LOADED:
            raise OwnershipRequestError(
                code="OWNERSHIP_NOT_ANALYZABLE",
                message="This ownership record cannot be analyzed in its current state.",
            )

        try:
            record = self._record(
                record,
                event_type=OwnershipEventType.OWNERSHIP_ANALYSIS_STARTED,
                state=OwnershipAnalysisState.ANALYZING,
                outcome=EventOutcome.SUCCEEDED,
                message="Deterministic ownership analysis started.",
            )
        except OwnershipRepositoryConflictError:
            raise OwnershipRequestError(
                code="OWNERSHIP_ANALYSIS_CONFLICT",
                message="Ownership analysis is already in progress or has completed.",
            ) from None
        except Exception:
            self._raise_terminal_failure(
                record,
                code="OWNERSHIP_UNEXPECTED_FAILURE",
                message="Ownership analysis could not be completed.",
            )

        try:
            if record.root_party_id is None:
                raise OwnershipGraphError
            source = OwnershipSourceResult(
                root_party_id=record.root_party_id,
                parties=record.parties,
                relationships=record.relationships,
            )
            graph = build_ownership_graph(source)
            validate_ownership_graph(graph)
            calculation = calculate_ownership_paths(
                graph,
                max_depth=self.max_depth,
                max_paths_per_candidate=self.max_paths_per_candidate,
                max_total_paths=self.max_total_paths,
            )
            aggregated = aggregate_ownership_paths(calculation)
            candidates = build_ownership_candidates(
                graph,
                calculation,
                aggregated,
                threshold_percent=self.threshold_percent,
            )
            record.candidates = candidates
            record.issues = list(calculation.issues)
            record.analyzed_at = self._clock()
            if record.issues:
                record = self._record(
                    record,
                    event_type=OwnershipEventType.OWNERSHIP_REVIEW_REQUIRED,
                    state=OwnershipAnalysisState.REVIEW_REQUIRED,
                    outcome=EventOutcome.REVIEW_REQUIRED,
                    code="OWNERSHIP_GRAPH_REVIEW_REQUIRED",
                    message="Ownership analysis completed with issues requiring human review.",
                    candidate_count=len(record.candidates),
                )
            else:
                record = self._record(
                    record,
                    event_type=OwnershipEventType.OWNERSHIP_ANALYSIS_COMPLETED,
                    state=OwnershipAnalysisState.ANALYZED,
                    outcome=EventOutcome.SUCCEEDED,
                    message="Deterministic ownership analysis completed.",
                    candidate_count=len(record.candidates),
                )
            return record.model_copy(deep=True)
        except OwnershipInfrastructureError:
            raise
        except OwnershipRepositoryConflictError:
            raise OwnershipRequestError(
                code="OWNERSHIP_ANALYSIS_CONFLICT",
                message="Ownership analysis was superseded by another terminal result.",
            ) from None
        except OwnershipRequestError:
            raise
        except (OwnershipGraphError, ValidationError):
            self._raise_terminal_failure(
                record,
                code="OWNERSHIP_GRAPH_INVALID",
                message="The ownership graph could not be analyzed safely.",
            )
        except Exception:
            self._raise_terminal_failure(
                record,
                code="OWNERSHIP_UNEXPECTED_FAILURE",
                message="Ownership analysis could not be completed.",
            )

    def get(self, *, case_id: UUID) -> OwnershipAnalysisRecord | None:
        record = self._repository.get_for_case(case_id)
        if record is not None:
            return record
        if self._cases.get_case(case_id) is None:
            raise OwnershipRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        return None

    def _validate_source(
        self,
        source: OwnershipSourceResult,
        metadata: OwnershipProviderMetadata,
        registration_number: str,
    ) -> None:
        if (
            len(source.parties) > self.max_parties
            or len(source.relationships) > self.max_relationships
        ):
            raise OwnershipGraphError
        root = next(party for party in source.parties if party.party_id == source.root_party_id)
        if root.registration_number != registration_number:
            raise OwnershipGraphError
        for relationship in source.relationships:
            provenance = relationship.provenance
            if (
                provenance.provider != metadata.provider_name
                or provenance.environment != metadata.environment
            ):
                raise OwnershipGraphError

    def _record(
        self,
        record: OwnershipAnalysisRecord,
        *,
        event_type: OwnershipEventType,
        state: OwnershipAnalysisState,
        outcome: EventOutcome,
        message: str,
        code: str | None = None,
        party_count: int | None = None,
        relationship_count: int | None = None,
        candidate_count: int | None = None,
    ) -> OwnershipAnalysisRecord:
        timestamp = self._clock()
        candidate = record.model_copy(deep=True)
        candidate.state = state
        candidate.updated_at = timestamp
        candidate.events.append(
            OwnershipWorkflowEvent(
                sequence=len(candidate.events) + 1,
                event_type=event_type,
                state=state,
                outcome=outcome,
                timestamp=timestamp,
                case_id=candidate.case_id,
                analysis_id=candidate.analysis_id,
                correlation_id=candidate.correlation_id,
                code=code,
                message=message,
                party_count=party_count,
                relationship_count=relationship_count,
                candidate_count=candidate_count,
            )
        )
        return self._repository.save(candidate, expected_version=record.version)

    def _raise_terminal_failure(
        self,
        record: OwnershipAnalysisRecord,
        *,
        code: str,
        message: str,
    ) -> Never:
        persisted = self._repository.get_for_case(record.case_id) or record
        if persisted.state in {
            OwnershipAnalysisState.FAILED,
            OwnershipAnalysisState.ANALYZED,
            OwnershipAnalysisState.REVIEW_REQUIRED,
        }:
            self._raise_existing_terminal_or_conflict(persisted)
        failed = persisted.model_copy(deep=True)
        failed.candidates = []
        failed.issues = []
        failed.analyzed_at = None
        failed.error = SafeError(code=code, message=message)
        try:
            failed = self._record(
                failed,
                event_type=OwnershipEventType.OWNERSHIP_ANALYSIS_FAILED,
                state=OwnershipAnalysisState.FAILED,
                outcome=EventOutcome.FAILED,
                code=code,
                message=message,
            )
        except OwnershipRepositoryConflictError:
            current = self._repository.get_for_case(record.case_id)
            if current is not None:
                self._raise_existing_terminal_or_conflict(current)
            raise OwnershipRequestError(
                code="OWNERSHIP_ANALYSIS_CONFLICT",
                message="Ownership analysis was superseded by another request.",
            ) from None
        raise OwnershipInfrastructureError(
            case_id=failed.case_id,
            analysis_id=failed.analysis_id,
            correlation_id=failed.correlation_id,
            code=code,
            message=message,
        ) from None

    def _raise_existing_terminal_or_conflict(self, record: OwnershipAnalysisRecord) -> Never:
        if record.state == OwnershipAnalysisState.FAILED and record.error is not None:
            raise OwnershipInfrastructureError(
                case_id=record.case_id,
                analysis_id=record.analysis_id,
                correlation_id=record.correlation_id,
                code=record.error.code,
                message=record.error.message,
            ) from None
        raise OwnershipRequestError(
            code="OWNERSHIP_ANALYSIS_CONFLICT",
            message="Ownership analysis has already reached a terminal state.",
        ) from None


def _calculation_text(edges: tuple[OwnershipRelationship, ...], effective_percent: Decimal) -> str:
    factors = " x ".join(f"{_format_decimal(item.ownership_percent)}%" for item in edges)
    return f"{factors} = {_format_decimal(effective_percent)}%"


def _format_decimal(value: Decimal) -> str:
    normalized = format(value.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _path_id(path_key: tuple[str, ...]) -> str:
    """Derive a bounded stable identifier while retaining ordered IDs in edge evidence."""

    digest = sha256()
    for relationship_id in path_key:
        encoded = relationship_id.encode("ascii")
        digest.update(len(encoded).to_bytes(2, byteorder="big"))
        digest.update(encoded)
    return f"path-v1-{digest.hexdigest()}"


def _untrusted_to_primitives(value: object) -> object:
    """Detach every provider-owned model/container before fresh nested validation."""

    if isinstance(value, BaseModel):
        return _untrusted_to_primitives(value.model_dump(mode="python", round_trip=True))
    if isinstance(value, dict):
        return {key: _untrusted_to_primitives(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_untrusted_to_primitives(item) for item in value]
    return value
