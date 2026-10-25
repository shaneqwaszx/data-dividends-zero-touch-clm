"""Bounded ownership loading, graph traversal, aggregation, and classification."""

import json
from collections import Counter, defaultdict, deque
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Final, Never, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.connectors.garden_business import quantized_unit_share
from app.connectors.hybrid_ownership_overlay import (
    OVERLAY_RELATIONSHIP_PROVIDER,
    POC_EQUAL_UNITS_PROVIDER,
    POC_ISSUED_CAPITAL_PROVIDER,
    HybridOverlayScenario,
    HybridOwnershipOverlayCatalogue,
    PocAcceptanceDeclaration,
    issued_capital_matches,
    overlay_component,
)
from app.connectors.ownership import (
    OwnershipProvider,
    OwnershipProviderError,
    OwnershipProviderMetadata,
    OwnershipProviderRequest,
    OwnershipSourceResult,
)
from app.domain.documents import DocumentOwnershipObservation, DocumentProcessingRecord
from app.domain.models import EventOutcome, OnboardingCase, SafeError
from app.domain.ownership import (
    OFFICIAL_BUSINESS_PROFILE_ISSUED_CAPITAL,
    OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
    OWNERSHIP_POC_ACCEPTANCE_POLICY,
    ManualOwnershipReviewReceipt,
    OwnershipAnalysisIssue,
    OwnershipAnalysisRecord,
    OwnershipAnalysisState,
    OwnershipCandidate,
    OwnershipCandidateClassification,
    OwnershipDiscoveryAudit,
    OwnershipDiscoveryOutcome,
    OwnershipDiscoveryRecord,
    OwnershipDocumentBinding,
    OwnershipEnvironment,
    OwnershipEventType,
    OwnershipIssueCode,
    OwnershipPathEdge,
    OwnershipPathEvidence,
    OwnershipPercent,
    OwnershipPocAcceptance,
    OwnershipProvenance,
    OwnershipRelationship,
    OwnershipThresholdResult,
    OwnershipWorkflowEvent,
    Party,
    PartyType,
    PocAssumption,
    PriorOwnershipAnalysisSnapshot,
    discovery_topology_resolved,
)
from app.domain.ownership_evidence import OwnershipEvidence
from app.domain.policy import OwnershipDiscoveryPolicySnapshot
from app.domain.registry_legal_form import RegistryLegalForm
from app.services.document_ownership import compare_document_ownership, current_document_inputs
from app.services.ownership_errors import (
    OwnershipInfrastructureError,
    OwnershipRequestError,
)
from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger
from app.services.ownership_repository import (
    OwnershipAnalysisRepository,
    OwnershipRepositoryConflictError,
    ownership_is_current,
)

_OWNERSHIP_PERCENT_ADAPTER = TypeAdapter(OwnershipPercent)


def percentage_from_units(
    numerator: OwnershipEvidence,
    denominator: OwnershipEvidence | None,
) -> Decimal | None:
    """Calculate only explicitly compatible, same-entity, authoritative unit evidence.

    Never sum source rows, infer activity, equate capital currency with shares or
    round a value into the six-place source-edge contract.
    """
    if denominator is None:
        return None
    numerator = OwnershipEvidence.model_validate(numerator.model_dump())
    denominator = OwnershipEvidence.model_validate(denominator.model_dump())
    if (
        numerator.kind != "SHARE_UNITS"
        or denominator.kind != "CAPITAL_DENOMINATOR"
        or not denominator.authoritative
        or not numerator.entity_identifier
        or numerator.entity_identifier != denominator.entity_identifier
        or not numerator.share_class
        or numerator.share_class != denominator.share_class
        or not numerator.unit_type
        or numerator.unit_type != denominator.unit_type
        or numerator.numeric_value is None
        or denominator.numeric_value is None
        or numerator.numeric_value <= 0
        or denominator.numeric_value <= 0
        or numerator.numeric_value > denominator.numeric_value
        or numerator.provider != denominator.provider
        or numerator.environment != denominator.environment
        or numerator.source_status is not None
        or denominator.source_status is not None
        or numerator.as_of is None
        or numerator.as_of != denominator.as_of
    ):
        return None
    value = numerator.numeric_value / denominator.numeric_value * Decimal("100")
    if value != value.quantize(Decimal("0.000001")):
        return None
    return value


def _scalar_percentage(
    item: OwnershipEvidence,
    evidence: tuple[OwnershipEvidence, ...],
) -> Decimal | None:
    """Use the existing Decimal rules to assess a retained scalar beside a graph.

    A matching party/entity edge alone cannot resolve missing, ambiguous or
    incompatible unit evidence. No source wins over another source.
    """
    same_interest = [
        other
        for other in evidence
        if other.kind == item.kind
        and other.party_id == item.party_id
        and other.entity_identifier == item.entity_identifier
    ]
    if len(same_interest) != 1:
        return None
    if item.kind == "DIRECT_PERCENTAGE":
        return (
            item.numeric_value
            if item.source_status is None
            and item.determination_basis in {"PROVIDER_PERCENTAGE", "REVIEWED_DECLARATION"}
            else None
        )
    denominators = [
        other
        for other in evidence
        if other.kind == "CAPITAL_DENOMINATOR" and other.entity_identifier == item.entity_identifier
    ]
    classes = {
        other.share_class
        for other in evidence
        if other.kind == "SHARE_UNITS" and other.entity_identifier == item.entity_identifier
    }
    return (
        percentage_from_units(item, denominators[0])
        if len(denominators) == 1 and len(classes) == 1
        else None
    )


def quantify_ownership_evidence(source: OwnershipSourceResult) -> OwnershipSourceResult:
    """Extend an evidence-only source inside the existing arithmetic owner.

    Existing graph evidence is never replaced or combined with a second numerator.
    Multiple classes, denominators or conflicting interests remain unquantified.
    """
    if (
        source.relationships
        or not source.evidence
        or any(item.kind == "CONFLICT" for item in source.evidence)
    ):
        return source
    denominators = [item for item in source.evidence if item.kind == "CAPITAL_DENOMINATOR"]
    class_set = {item.share_class for item in source.evidence if item.kind == "SHARE_UNITS"}
    interests: dict[str, list[OwnershipEvidence]] = defaultdict(list)
    root_identifier = next(
        item.registration_number for item in source.parties if item.party_id == source.root_party_id
    )
    for item in source.evidence:
        if item.kind in {"DIRECT_PERCENTAGE", "SHARE_UNITS"}:
            interests[item.party_id].append(item)
    relationships: list[OwnershipRelationship] = []
    for party_id, items in interests.items():
        if len(items) != 1:
            continue
        item = items[0]
        if not item.entity_identifier or item.entity_identifier != root_identifier:
            continue
        percentage = (
            item.numeric_value
            if item.kind == "DIRECT_PERCENTAGE"
            and not item.source_status
            and item.determination_basis in {"PROVIDER_PERCENTAGE", "REVIEWED_DECLARATION"}
            else percentage_from_units(item, denominators[0])
            if len(denominators) == 1 and len(class_set) == 1
            else None
        )
        if percentage is None or percentage <= 0 or percentage > 100:
            continue
        relationships.append(
            OwnershipRelationship(
                relationship_id="derived-" + sha256(item.evidence_id.encode()).hexdigest()[:32],
                parent_party_id=source.root_party_id,
                child_party_id=party_id,
                ownership_percent=percentage,
                provenance=OwnershipProvenance(
                    provider=item.provider,
                    environment=OwnershipEnvironment(item.environment),
                    source_reference="EVIDENCE_" + sha256(item.evidence_id.encode()).hexdigest(),
                    sourced_at=item.retrieved_at,
                ),
            )
        )
    if not relationships:
        return source
    # Unquantified parties are retained in source evidence rather than invented graph edges.
    connected = {source.root_party_id, *(item.child_party_id for item in relationships)}
    return OwnershipSourceResult(
        root_party_id=source.root_party_id,
        parties=[item for item in source.parties if item.party_id in connected],
        relationships=relationships,
        evidence=source.evidence,
        legal_form=source.legal_form,
    )


class OnboardingCaseReader(Protocol):
    def get_case(self, case_id: UUID) -> OnboardingCase | None: ...


@dataclass(frozen=True)
class DiscoveryLimits:
    """Existing service graph/path limits applied while scheduling retrieval."""

    max_parties: int
    max_relationships: int
    max_depth: int
    max_paths_per_candidate: int
    max_total_paths: int


class OwnershipDiscoveryExpander(Protocol):
    """Schedules separate issuer acquisition; never calculates or classifies owners."""

    def expand(
        self,
        source: OwnershipSourceResult,
        *,
        parent: OnboardingCase,
        policy: OwnershipDiscoveryPolicySnapshot,
        ubo_threshold_percent: Decimal,
        limits: DiscoveryLimits,
        overlay: HybridOverlayScenario | None = None,
    ) -> tuple[OwnershipSourceResult, OwnershipDiscoveryAudit]: ...


HYBRID_SOURCE_CLASSIFICATION: Final = "OFFICIAL_MOCK_PLUS_LOCAL_DIRECT_OVERLAY"
# The flattened legacy Garden supplement is never a lookup source; a hybrid direct
# overlay is, because each corporate holder remains a verified-format issuer UEN.
_DISCOVERY_SOURCE_CLASSIFICATIONS = frozenset({"SINGLE_SOURCE", HYBRID_SOURCE_CLASSIFICATION})
_SYNTHETIC_BASIS_BLOCKING_ISSUES = frozenset(
    {
        OwnershipIssueCode.CYCLE_DETECTED,
        OwnershipIssueCode.MAXIMUM_DEPTH_EXCEEDED,
        OwnershipIssueCode.PATH_LIMIT_EXCEEDED,
        OwnershipIssueCode.PERSON_IDENTITY_UNRESOLVED,
        OwnershipIssueCode.CONTRADICTORY_OWNERSHIP_EVIDENCE,
    }
)


def synthetic_basis_threshold_results(
    aggregated: dict[str, tuple[Decimal, Decimal, Decimal]],
    issues: list[OwnershipAnalysisIssue],
    *,
    threshold_percent: Decimal,
    unresolved_upper_bound_percent: Decimal | None,
) -> dict[str, OwnershipThresholdResult]:
    """The existing inclusive comparator over a declared synthetic basis, labelled apart.

    Known paths are a lower bound, so MET survives unresolved branches; NOT_MET needs a
    topologically complete graph or a sound bound. Never a candidate classification.
    """

    codes = {issue.code for issue in issues}
    unresolved = OwnershipIssueCode.INCOMPLETE_LEGAL_ENTITY in codes
    results: dict[str, OwnershipThresholdResult] = {}
    for party_id, (_, _, total) in aggregated.items():
        if codes & _SYNTHETIC_BASIS_BLOCKING_ISSUES:
            results[party_id] = OwnershipThresholdResult.INDETERMINATE
        elif total >= threshold_percent:
            results[party_id] = OwnershipThresholdResult.MET
        elif not unresolved or (
            unresolved_upper_bound_percent is not None
            and total + unresolved_upper_bound_percent < threshold_percent
        ):
            results[party_id] = OwnershipThresholdResult.NOT_MET
        else:
            results[party_id] = OwnershipThresholdResult.INDETERMINATE
    return results


# D-085: which declared assumption each link provenance exercises. Any other link kind
# (an official ACRA edge, a manual declaration) is outside every POC acceptance.
_POC_ACCEPTANCE_EDGE_ASSUMPTIONS: Final = {
    OVERLAY_RELATIONSHIP_PROVIDER: PocAssumption.SIMULATED_RELATIONSHIPS,
    POC_EQUAL_UNITS_PROVIDER: PocAssumption.EQUAL_UNIT_DENOMINATOR,
    POC_ISSUED_CAPITAL_PROVIDER: PocAssumption.ISSUED_CAPITAL_DENOMINATOR,
}
_OWNERSHIP_LIKE_ROLES: Final = frozenset({"OWNER", "PARTNER", "MEMBER", "SHAREHOLDER"})
_UNRESOLVED_EVIDENCE_KINDS: Final = frozenset(
    {"GROUP_SHAREHOLDER", "UNKNOWN", "CONTROL", "MEMBERSHIP_INTEREST", "ECONOMIC_INTEREST"}
)
_POC_BASIS_FIELDS: Final = frozenset(
    {
        "case_id", "analysis_id", "identity_registration_number",
        "identity_correction_version", "source_classification", "legal_form",
        "provider_name", "provider_environment", "root_party_id", "parties",
        "relationships", "candidates", "issues", "evidence", "supplemental_parties",
        "supplemental_relationships", "supplemental_evidence", "discovery",
        "document_observations", "document_bindings", "document_discrepancies",
        "manual_review_receipt", "threshold_percent", "threshold_comparator", "error",
    }
)


@dataclass(frozen=True)
class _ReviewCauses:
    """Every evidence cause behind the single registry review issue, kept separate.

    The analysis records one issue code chosen by priority (a legal form of OTHER masks
    every other cause), so POC acceptance evaluates these causes, never the code alone.
    """

    unquantified: tuple[OwnershipEvidence, ...]
    contradictory: tuple[OwnershipEvidence, ...]
    has_conflict: bool
    has_unbound: bool
    has_unsupported_activity: bool
    unresolved_kinds: bool
    unresolved_roles: tuple[OwnershipEvidence, ...]


def _review_causes(record: OwnershipAnalysisRecord) -> _ReviewCauses:
    entities = {party.party_id: party.registration_number for party in record.parties}
    unquantified: list[OwnershipEvidence] = []
    contradictory: list[OwnershipEvidence] = []
    for item in record.evidence:
        if item.kind not in {"SHARE_UNITS", "DIRECT_PERCENTAGE"}:
            continue
        scalar = _scalar_percentage(item, record.evidence)
        edges = [
            edge
            for edge in record.relationships
            if item.entity_identifier is not None
            and edge.child_party_id == item.party_id
            and entities[edge.parent_party_id] == item.entity_identifier
        ]
        if scalar is None or len(edges) != 1:
            unquantified.append(item)
        elif edges[0].ownership_percent != scalar:
            contradictory.append(item)
    garden_fixture_graph = (
        record.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
        and record.identity_registration_number == "11111999A"
        and bool(record.supplemental_relationships)
        and tuple(record.relationships) == record.supplemental_relationships
    )
    unresolved_roles = tuple(
        item
        for item in record.evidence
        if item.kind == "ROLE"
        # Official officer roles are retained descriptive context, not quantitative
        # ownership authority for the validated Garden fixture.
        and not (
            garden_fixture_graph
            and item.provider == "ACRA_REGISTRY_ACQUISITION"
            and item.source_operation == "OFFICERS"
        )
        and item.raw_value.strip().upper() in _OWNERSHIP_LIKE_ROLES
        and not any(
            item.entity_identifier is not None
            and edge.child_party_id == item.party_id
            and entities[edge.parent_party_id] == item.entity_identifier
            for edge in record.relationships
        )
    )
    return _ReviewCauses(
        unquantified=tuple(unquantified),
        contradictory=tuple(contradictory),
        has_conflict=any(item.kind == "CONFLICT" for item in record.evidence),
        has_unbound=any(item.entity_identifier is None for item in record.evidence),
        has_unsupported_activity=any(
            (item.kind == "DIRECT_PERCENTAGE" and item.source_status is not None)
            or (item.kind == "SHARE_UNITS" and item.source_status not in {None, "ACTIVE"})
            for item in record.evidence
        ),
        unresolved_kinds=any(item.kind in _UNRESOLVED_EVIDENCE_KINDS for item in record.evidence),
        unresolved_roles=unresolved_roles,
    )


def _intermediate_ownership_like_roles(discovery: OwnershipDiscoveryAudit) -> bool:
    """D-086: any ownership-like official officer role retained on an overlay issuer."""

    return bool(_intermediate_role_records(discovery))


def _intermediate_role_records(
    discovery: OwnershipDiscoveryAudit,
) -> tuple[OwnershipDiscoveryRecord, ...]:
    """Discovery records holding at least one ownership-like official officer role."""

    return tuple(
        item
        for item in discovery.records
        if any(
            role.role.strip().upper() in _OWNERSHIP_LIKE_ROLES
            for role in item.official_officer_roles
        )
    )


def _undeclared_intermediate_roles(
    discovery: OwnershipDiscoveryAudit,
    scenario: HybridOverlayScenario,
    declaration: PocAcceptanceDeclaration,
) -> bool:
    """D-087 fail closed: an ownership-like intermediate role outside the declaration.

    Accepted only for the role kinds the trusted declaration names for that issuer, on a
    non-root issuer of this scenario recorded once with its official entity profile, and
    only for role records that keep the official OFFICERS evidence contract.
    """

    if not (records := _intermediate_role_records(discovery)):
        return False
    counts = Counter(item.registration_number for item in discovery.records)
    return (
        PocAssumption.DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES not in declaration.accepted_assumptions
        # The acceptance keeps at most 32 descriptive intermediate role records.
        or sum(len(item.official_officer_roles) for item in records) > 32
        or any(
            item.registration_number is None
            or item.registration_number == scenario.root_uen
            or scenario.issuer(item.registration_number) is None
            or counts[item.registration_number] != 1
            or item.identity_basis != "OFFICIAL_MOCK_ENTITY_PROFILE"
            or item.outcome != OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
            or any(
                role.source_operation != "OFFICERS"
                or role.provider != "ACRA_REGISTRY_ACQUISITION"
                or role.environment != "MOCK"
                or role.status not in {"CURRENT", "CEASED"}
                or (
                    role.role.strip().upper() in _OWNERSHIP_LIKE_ROLES
                    and role.role.strip().upper()
                    not in declaration.descriptive_roles_of(item.registration_number)
                )
                for role in item.official_officer_roles
            )
            for item in records
        )
    )


def _issued_capital_links_disagree(
    record: OwnershipAnalysisRecord,
    discovery: OwnershipDiscoveryAudit,
    scenario: HybridOverlayScenario,
) -> bool:
    """D-088 fail closed: issued-capital links not reproduced by their retained profile.

    Every such link must come from a scenario-named issuer whose retained businessProfile
    still satisfies the exact capital match, and the links from that issuer must be
    exactly its rows' holder names and quantized issued-capital shares.
    """

    links = [
        edge
        for edge in record.relationships
        if edge.provenance.provider == POC_ISSUED_CAPITAL_PROVIDER
    ]
    profiles = [
        item
        for item in discovery.records
        if item.reason_code == OFFICIAL_BUSINESS_PROFILE_ISSUED_CAPITAL
    ]
    if {edge.parent_party_id for edge in links} != {item.party_id for item in profiles}:
        return True
    names = {party.party_id: party.display_name for party in record.parties}
    for item in profiles:
        profile = item.official_business_profile
        if (
            profile is None
            or item.registration_number is None
            or item.registration_number not in scenario.business_profile_issuers
            or len(profile.issued_share_capital) != 1
            or not all(row.assumed_current for row in profile.shareholders)
            or not issued_capital_matches(
                profile.shareholders, profile.issued_share_capital, profile.paid_up_capital
            )
        ):
            return True
        denominator = profile.issued_share_capital[0].number_of_shares or Decimal("0")
        expected = sorted(
            (row.display_name, quantized_unit_share(row.number_of_shares, denominator))
            for row in profile.shareholders
        )
        actual = sorted(
            (names.get(edge.child_party_id, ""), edge.ownership_percent)
            for edge in links
            if edge.parent_party_id == item.party_id
        )
        if actual != expected:
            return True
    return False


def _officer_role_evidence_id(party_id: str) -> str:
    """The registry ownership adapter's stable id for an officer's role evidence."""

    return "e-" + sha256(f"{party_id}:ROLE".encode()).hexdigest()[:48]


def _poc_basis_fingerprint(record: OwnershipAnalysisRecord) -> str:
    """Digest of every input the POC acceptance depends on; any change revokes it."""

    content = record.model_dump(mode="json", include=set(_POC_BASIS_FIELDS))
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def eligible_poc_acceptance(
    record: OwnershipAnalysisRecord,
    *,
    scenario: HybridOverlayScenario | None,
    accepted_at: datetime,
    ownership_version: int,
) -> OwnershipPocAcceptance | None:
    """D-085 fail-closed eligibility: only the scenario's declared assumptions remain open.

    The trusted catalogue declaration (project code, never a case field) lists the
    accepted assumptions, and each accepts exactly one review cause. The analysis must
    belong to that scenario's official Mock root, have a complete topology built only
    from declared link kinds over issuers that are not locally named, calculated
    assumed-basis results, and no other cause, issue or defect. Nothing is changed:
    state, issues, evidence and classifications stay.
    """

    discovery = record.discovery
    declaration = scenario.poc_acceptance if scenario is not None else None
    if (
        scenario is None
        or declaration is None
        or discovery is None
        or discovery.overlay_scenario_id != scenario.scenario_id
    ):
        return None
    declared = declaration.accepted_assumptions
    root_uen = scenario.root_uen
    root = next((item for item in record.parties if item.party_id == record.root_party_id), None)
    retained = [item for item in discovery.records if item.official_shareholders]
    poc_edges = [
        edge
        for edge in record.relationships
        if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
    ]
    link_assumptions = {
        _POC_ACCEPTANCE_EDGE_ASSUMPTIONS.get(edge.provenance.provider)
        for edge in record.relationships
    }
    codes = {issue.code for issue in record.issues}
    causes = _review_causes(record)
    legal_form_other = record.legal_form == RegistryLegalForm.OTHER
    if (
        record.source_classification != HYBRID_SOURCE_CLASSIFICATION
        or record.provider_name != "ACRA_REGISTRY_ACQUISITION"
        or record.provider_environment != OwnershipEnvironment.MOCK
        or record.identity_registration_number != root_uen
        or record.identity_correction_version is None
        or root is None
        or root.registration_number != root_uen
        or record.legal_form is None
        or (legal_form_other and PocAssumption.UNCLASSIFIED_LEGAL_FORM not in declared)
        or record.error is not None
        or record.manual_review_receipt is not None
        or record.supplemental_relationships
        or discovery.topology_complete is not True
        or discovery.unresolved_person_party_ids
        or any(
            item.verification_state == "REVIEW_REQUIRED" for item in record.document_discrepancies
        )
        # A locally named issuer is a fabricated identity, never a declared assumption.
        or any(item.identity_basis == "LOCAL_SYNTHETIC_IDENTITY" for item in discovery.records)
        # D-086/D-087 fail closed: an intermediate issuer's ownership-like official officer
        # roles block unless the trusted declaration names that issuer.
        or _undeclared_intermediate_roles(discovery, scenario, declaration)
        or _issued_capital_links_disagree(record, discovery, scenario)
        or not link_assumptions
        or not link_assumptions <= declared
        or any(
            item.reason_code != OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS
            or item.official_shareholder_lookup is None
            for item in retained
        )
        or {edge.parent_party_id for edge in poc_edges} != {item.party_id for item in retained}
        or any(
            item.provider != OVERLAY_RELATIONSHIP_PROVIDER or item.environment != "LOCAL"
            for item in record.supplemental_evidence
        )
        # Genuine evidence defects stay blocking whatever the recorded issue code says.
        or causes.unquantified
        or causes.contradictory
        or causes.has_conflict
        or causes.has_unbound
        or causes.has_unsupported_activity
        or causes.unresolved_kinds
        or (causes.unresolved_roles and PocAssumption.DESCRIPTIVE_OFFICER_ROLES not in declared)
        or len(causes.unresolved_roles) > 16
        # Retained root evidence is only official Mock officer roles, kept as context;
        # none is a shareholding, a percentage or a classification input.
        or any(
            item.kind != "ROLE"
            or item.source_operation != "OFFICERS"
            or item.provider != "ACRA_REGISTRY_ACQUISITION"
            or item.environment != "MOCK"
            or item.entity_identifier != root_uen
            or item.source_status not in {None, "CEASED"}
            or item.evidence_id != _officer_role_evidence_id(item.party_id)
            for item in record.evidence
        )
        or len({item.party_id for item in record.evidence}) != len(record.evidence)
        or len({item.evidence_id for item in record.evidence}) != len(record.evidence)
        or len(codes) != len(record.issues)
        or not record.candidates
        or any(
            item.classification
            not in {
                OwnershipCandidateClassification.REVIEW_REQUIRED,
                OwnershipCandidateClassification.INDETERMINATE,
            }
            or item.synthetic_basis_threshold_result
            not in {OwnershipThresholdResult.MET, OwnershipThresholdResult.NOT_MET}
            for item in record.candidates
        )
    ):
        return None
    exercised = {item for item in link_assumptions if item is not None}
    if causes.unresolved_roles:
        exercised.add(PocAssumption.DESCRIPTIVE_OFFICER_ROLES)
    intermediate_statuses = [
        role.status
        for item in _intermediate_role_records(discovery)
        for role in item.official_officer_roles
        if role.role.strip().upper() in _OWNERSHIP_LIKE_ROLES
    ]
    if intermediate_statuses:
        exercised.add(PocAssumption.DESCRIPTIVE_INTERMEDIATE_OFFICER_ROLES)
    if legal_form_other:
        exercised.add(PocAssumption.UNCLASSIFIED_LEGAL_FORM)
    # One registry review issue is recorded by priority: legal form OTHER masks roles.
    expected = {OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE}
    if poc_edges:
        expected.add(OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED)
    if legal_form_other:
        expected.add(OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED)
    elif causes.unresolved_roles:
        expected.add(OwnershipIssueCode.UBO_REVIEW_REQUIRED)
    if codes != expected:
        return None
    statuses = [
        "CEASED" if item.source_status == "CEASED" else "CURRENT"
        for item in causes.unresolved_roles
    ]
    return OwnershipPocAcceptance(
        policy=OWNERSHIP_POC_ACCEPTANCE_POLICY,
        accepted_at=accepted_at,
        case_id=record.case_id,
        analysis_id=record.analysis_id,
        ownership_version=ownership_version,
        identity_registration_number=root_uen,
        identity_correction_version=record.identity_correction_version,
        overlay_scenario_id=scenario.scenario_id,
        accepted_issue_codes=tuple(sorted(codes)),
        poc_relationship_ids=tuple(sorted({edge.relationship_id for edge in poc_edges})),
        descriptive_current_role_count=statuses.count("CURRENT"),
        descriptive_ceased_role_count=statuses.count("CEASED"),
        descriptive_intermediate_current_role_count=intermediate_statuses.count("CURRENT"),
        descriptive_intermediate_ceased_role_count=intermediate_statuses.count("CEASED"),
        issued_capital_relationship_ids=tuple(
            sorted(
                {
                    edge.relationship_id
                    for edge in record.relationships
                    if edge.provenance.provider == POC_ISSUED_CAPITAL_PROVIDER
                }
            )
        ),
        accepted_assumptions=tuple(sorted(exercised)),
        basis_fingerprint=_poc_basis_fingerprint(record),
    )


def poc_acceptance_current(
    record: OwnershipAnalysisRecord, scenario: HybridOverlayScenario | None
) -> bool:
    """The recorded acceptance still matches this exact analysis version and policy.

    A D-082 record never matches: eligibility is recomputed under D-085 only.
    """

    acceptance = record.poc_acceptance
    return (
        acceptance is not None
        and record.state == OwnershipAnalysisState.REVIEW_REQUIRED
        and acceptance.ownership_version == record.version
        and eligible_poc_acceptance(
            record,
            scenario=scenario,
            accepted_at=acceptance.accepted_at,
            ownership_version=acceptance.ownership_version,
        )
        == acceptance
    )


# Issues a completed declared-overlay simulation may carry: its synthetic-evidence marker,
# the root legal form's unsupported formal method, and the root's descriptive role review.
_SIMULATION_ISSUES: Final = frozenset(
    {
        OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
        OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED,
        OwnershipIssueCode.UBO_REVIEW_REQUIRED,
    }
)


def simulation_calculation_complete(record: OwnershipAnalysisRecord) -> bool:
    """Presentation only: a declared-overlay simulation whose arithmetic fully completed.

    True when every link is a declared LOCAL_SYNTHETIC_RELATIONSHIP, the topology is
    complete, every person has a calculated assumed-basis result, and no genuine evidence
    defect, contradiction or other issue remains (causes are recomputed, never inferred
    from the masked review code). It grants no readiness, verification or acceptance.
    """

    discovery = record.discovery
    if (
        record.state != OwnershipAnalysisState.REVIEW_REQUIRED
        or record.source_classification != HYBRID_SOURCE_CLASSIFICATION
        or discovery is None
        or discovery.overlay_scenario_id is None
        or discovery.topology_complete is not True
        or discovery.unresolved_person_party_ids
        or record.error is not None
        or record.manual_review_receipt is not None
        or record.supplemental_relationships
        or any(
            item.verification_state == "REVIEW_REQUIRED" for item in record.document_discrepancies
        )
        or not record.relationships
        or any(
            edge.provenance.provider != OVERLAY_RELATIONSHIP_PROVIDER
            for edge in record.relationships
        )
        or not record.candidates
        or any(
            item.synthetic_basis_threshold_result
            not in {OwnershipThresholdResult.MET, OwnershipThresholdResult.NOT_MET}
            for item in record.candidates
        )
    ):
        return False
    codes = [issue.code for issue in record.issues]
    causes = _review_causes(record)
    return (
        not _intermediate_ownership_like_roles(discovery)
        and OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE in codes
        and set(codes) <= _SIMULATION_ISSUES
        and len(set(codes)) == len(codes)
        and not (
            causes.unquantified
            or causes.contradictory
            or causes.has_conflict
            or causes.has_unbound
            or causes.has_unsupported_activity
            or causes.unresolved_kinds
        )
        # A role cause must be the visible role review, never one masked by legal form OTHER.
        and bool(causes.unresolved_roles)
        == (OwnershipIssueCode.UBO_REVIEW_REQUIRED in codes)
    )


class OwnershipDocumentReader(Protocol):
    def list_documents(self, *, case_id: UUID) -> list[DocumentProcessingRecord]: ...


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
    # Exact unrounded sum of path products reaching each legal entity without owners.
    unresolved_entity_shares: dict[str, Decimal] = field(default_factory=dict)
    # D-086 presentation only: the same traversal's path products reaching each
    # intermediate legal entity. Never a candidate, classification or readiness input.
    entity_paths_by_party: dict[str, tuple[OwnershipPathEvidence, ...]] = field(
        default_factory=dict
    )


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
    include_entity_paths: bool = False,
) -> PathCalculation:
    """Iteratively enumerate unique bounded root-to-natural-person paths.

    `include_entity_paths` (D-086 presentation only, off for analysis, discovery and
    advice) also records the product already reaching each intermediate legal entity.
    """

    paths: dict[str, list[OwnershipPathEvidence]] = defaultdict(list)
    path_keys: set[tuple[str, ...]] = set()
    issues: dict[tuple[OwnershipIssueCode, tuple[str, ...]], OwnershipAnalysisIssue] = {}
    stack: list[tuple[str, tuple[OwnershipRelationship, ...], frozenset[str], Decimal]] = [
        (graph.root_party_id, (), frozenset({graph.root_party_id}), Decimal("1"))
    ]
    total_paths = 0
    explored_path_states = 0
    traversal_limit_reached = False
    entity_shares: dict[str, Decimal] = defaultdict(Decimal)
    entity_paths: dict[str, list[OwnershipPathEvidence]] = defaultdict(list)

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
            entity_shares[current_id] += current_fraction * Decimal("100")
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

            if include_entity_paths and child.party_type == PartyType.LEGAL_ENTITY:
                # D-086 presentation only: record the product already reaching this entity.
                entity_percent = next_fraction * Decimal("100")
                entity_paths[child_id].append(
                    OwnershipPathEvidence(
                        path_id=_path_id(tuple(item.relationship_id for item in next_edges)),
                        edges=[
                            OwnershipPathEdge(
                                relationship_id=item.relationship_id,
                                parent_party_id=item.parent_party_id,
                                parent_display_name=graph.parties[item.parent_party_id].display_name,
                                child_party_id=item.child_party_id,
                                child_display_name=graph.parties[item.child_party_id].display_name,
                                ownership_percent=item.ownership_percent,
                            )
                            for item in next_edges
                        ],
                        effective_ownership_percent=entity_percent,
                        is_direct=len(next_edges) == 1,
                        calculation=_calculation_text(next_edges, entity_percent),
                    )
                )
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
        unresolved_entity_shares=dict(sorted(entity_shares.items())),
        entity_paths_by_party={
            party_id: tuple(sorted(items, key=lambda item: item.path_id))
            for party_id, items in sorted(entity_paths.items())
        },
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
        documents: OwnershipDocumentReader | None = None,
        garden_supplement_enabled: bool = False,
        discovery: OwnershipDiscoveryExpander | None = None,
        hybrid_overlay: HybridOwnershipOverlayCatalogue | None = None,
        poc_acceptance_enabled: bool = False,
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
        self._documents = documents
        if garden_supplement_enabled and hybrid_overlay is not None:
            raise ValueError("the legacy Garden supplement and hybrid overlays are exclusive")
        if poc_acceptance_enabled and hybrid_overlay is None:
            raise ValueError("POC ownership acceptance requires the hybrid overlay lane")
        self._garden_supplement_enabled = garden_supplement_enabled
        self._discovery = discovery
        self._hybrid_overlay = hybrid_overlay
        self._poc_acceptance_enabled = poc_acceptance_enabled
        self.threshold_percent = validated_threshold
        self.max_parties = max_parties
        self.max_relationships = max_relationships
        self.max_depth = max_depth
        self.max_paths_per_candidate = max_paths_per_candidate
        self.max_total_paths = max_total_paths
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4

    @property
    def configured_provider(self) -> OwnershipProvider:
        """Expose the composition-owned default for an opaque provider binding."""

        return self._provider

    def poc_basis_accepted(self, record: OwnershipAnalysisRecord) -> bool:
        """POC readiness authority: a current acceptance, only while this runtime opts in.

        A persisted acceptance alone grants nothing: disabling the setting, leaving the
        Mock hybrid lane or removing the scenario's catalogue declaration revokes it, and
        so does any later identity or content change.
        """

        if not self._poc_acceptance_enabled or self._hybrid_overlay is None:
            return False
        parent = self._cases.get_case(record.case_id)
        return (
            parent is not None
            and ownership_is_current(record, parent)
            and record.document_bindings == self._document_inputs(record.case_id)[1]
            and poc_acceptance_current(record, self._poc_scenario(record))
        )

    def simulation_calculated(self, record: OwnershipAnalysisRecord) -> bool:
        """Presentation only (see `simulation_calculation_complete`); never readiness."""

        return simulation_calculation_complete(record)

    def entity_effective_interests(
        self, record: OwnershipAnalysisRecord
    ) -> dict[str, tuple[OwnershipPathEvidence, ...]]:
        """Presentation only: the engine's path products reaching each intermediate entity.

        Recomputed from the analysed record with the same traversal and safety limits; it
        is never stored, classified or used for readiness. Empty (fail closed) when the
        record is not analysed, the traversal was bounded (path or depth limit), a cycle
        was excluded, any entity total exceeds 100 (over-allocation), or the evidence
        cannot be built, so nothing partial or impossible is shown as an interest.
        """

        if (
            record.state
            not in {OwnershipAnalysisState.ANALYZED, OwnershipAnalysisState.REVIEW_REQUIRED}
            or record.root_party_id is None
            or not record.relationships
        ):
            return {}
        try:
            calculation = calculate_ownership_paths(
                build_ownership_graph(
                    OwnershipSourceResult(
                        root_party_id=record.root_party_id,
                        parties=list(record.parties),
                        relationships=list(record.relationships),
                    )
                ),
                max_depth=self.max_depth,
                max_paths_per_candidate=self.max_paths_per_candidate,
                max_total_paths=self.max_total_paths,
                include_entity_paths=True,
            )
        except (OwnershipGraphError, ValidationError, KeyError):
            return {}
        if any(
            issue.code
            in {
                OwnershipIssueCode.PATH_LIMIT_EXCEEDED,
                OwnershipIssueCode.MAXIMUM_DEPTH_EXCEEDED,
                OwnershipIssueCode.CYCLE_DETECTED,
            }
            for issue in calculation.issues
        ) or any(
            sum((path.effective_ownership_percent for path in paths), start=Decimal("0"))
            > Decimal("100")
            for paths in calculation.entity_paths_by_party.values()
        ):
            return {}
        return calculation.entity_paths_by_party

    def _poc_scenario(self, record: OwnershipAnalysisRecord) -> HybridOverlayScenario | None:
        """This composition's own trusted declaration for the analysis's scenario."""

        if self._hybrid_overlay is None or record.discovery is None:
            return None
        return self._hybrid_overlay.scenario(record.discovery.overlay_scenario_id)

    def load(
        self, *, case_id: UUID, provider: OwnershipProvider | None = None
    ) -> OwnershipAnalysisRecord:
        with self._case_lock(case_id):
            return self._load_locked(case_id=case_id, provider=provider)

    def replace_review_required_source(
        self,
        *,
        case_id: UUID,
        provider: OwnershipProvider,
        review_receipt: ManualOwnershipReviewReceipt,
        expected_version: int,
        before_replace: Callable[[], object] | None = None,
    ) -> OwnershipAnalysisRecord:
        """Revise terminal pre-submission evidence, retaining the source and decision."""

        with self._case_lock(case_id):
            current = self._repository.get_for_case(case_id)
            parent = self._cases.get_case(case_id)
            if parent is None:
                raise OwnershipRequestError(
                    code="ONBOARDING_CASE_NOT_FOUND",
                    message="The onboarding case was not found.",
                )
            if current is None or current.state not in {
                OwnershipAnalysisState.REVIEW_REQUIRED,
                OwnershipAnalysisState.ANALYZED,
            }:
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_NOT_ALLOWED",
                    message=("Manual evidence may replace only current "
                             "pre-submission terminal analysis."),
                )
            if parent.goldtier_result is not None or not ownership_is_current(current, parent):
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_NOT_ALLOWED",
                    message="Submitted or obsolete ownership evidence cannot be revised.",
                )
            if current.version != expected_version:
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_STALE",
                    message="The ownership analysis changed before manual evidence was accepted.",
                )
            if parent.entity is None or parent.entity.legal_name is None:
                raise OwnershipRequestError(
                    code="OWNERSHIP_ROOT_UNAVAILABLE",
                    message=(
                        "The onboarding case has no canonical legal entity for ownership analysis."
                    ),
                )
            if review_receipt.case_id != case_id:
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_CASE_MISMATCH",
                    message="The manual review receipt does not belong to this case.",
                )

            try:
                metadata = OwnershipProviderMetadata.model_validate(
                    _untrusted_to_primitives(provider.metadata)
                )
                source = OwnershipSourceResult.model_validate(
                    _untrusted_to_primitives(
                        provider.load(
                            OwnershipProviderRequest(
                                case_id=case_id,
                                registration_number=parent.entity.registration_number,
                                display_name=parent.entity.legal_name,
                            )
                        )
                    )
                )
                self._validate_source(source, metadata, parent.entity.registration_number)
            except OwnershipProviderError as exc:
                code = getattr(exc, "code", "OWNERSHIP_PROVIDER_FAILED")
                message = getattr(
                    exc,
                    "message",
                    "Ownership source loading could not be completed.",
                )
                raise OwnershipRequestError(code=code, message=message) from None
            except (OwnershipGraphError, ValidationError):
                raise OwnershipRequestError(
                    code="OWNERSHIP_MALFORMED_SOURCE",
                    message="Ownership source data could not be validated safely.",
                ) from None

            observations, bindings = self._document_inputs(case_id)
            if review_receipt.observed_document_versions != bindings:
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_STALE",
                    message="Current document ownership evidence changed before the decision.",
                )
            # D-081 owner decision (F1): POC-assumed equal-unit links are illustrative. They
            # can be neither kept as current evidence nor redeclared unchanged.
            poc_edges = _poc_assumed_edges(current)
            if poc_edges and (
                review_receipt.source_selection == "CURRENT_EVIDENCE"
                or (
                    review_receipt.source_selection == "USER_SUPPLIED_DECLARATION"
                    and any(
                        (edge.parent_party_id, edge.child_party_id, edge.ownership_percent)
                        in poc_edges
                        for edge in source.relationships
                    )
                )
            ):
                raise OwnershipRequestError(
                    code="OWNERSHIP_POC_EVIDENCE_REVIEW_REQUIRED",
                    message=(
                        "POC-assumed equal-unit percentages require independent ownership "
                        "evidence; they cannot be kept or redeclared unchanged."
                    ),
                )
            if review_receipt.source_selection == "CURRENT_EVIDENCE" and (
                source.root_party_id != current.root_party_id
                or source.parties != current.parties
                or sorted(
                    (edge.parent_party_id, edge.child_party_id, edge.ownership_percent)
                    for edge in source.relationships
                )
                != sorted(
                    (edge.parent_party_id, edge.child_party_id, edge.ownership_percent)
                    for edge in current.relationships
                )
            ):
                raise OwnershipRequestError(
                    code="OWNERSHIP_SELECTED_SOURCE_MISMATCH",
                    message="Keeping current evidence requires the exact current ownership graph.",
                )
            known_observations = {item.observation_id for item in observations}
            if not set(review_receipt.selected_observation_ids).issubset(known_observations):
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_STALE",
                    message="Selected document observations are no longer current.",
                )
            if (
                review_receipt.source_selection == "DOCUMENT_OBSERVATIONS"
                and not review_receipt.selected_observation_ids
            ):
                raise OwnershipRequestError(
                    code="OWNERSHIP_SELECTED_SOURCE_MISMATCH",
                    message="Choosing document evidence requires current observation references.",
                )
            if review_receipt.source_selection == "DOCUMENT_OBSERVATIONS":
                selected = tuple(
                    item
                    for item in observations
                    if item.observation_id in review_receipt.selected_observation_ids
                )
                compared = compare_document_ownership(
                    selected, source.parties, source.relationships, source.evidence
                )
                covered_edges = {
                    identifier for item in compared for identifier in item.compared_relationship_ids
                }
                if (
                    any(item.agreement != "MATCH" for item in compared)
                    or covered_edges != {edge.relationship_id for edge in source.relationships}
                ):
                    raise OwnershipRequestError(
                        code="OWNERSHIP_SELECTED_SOURCE_MISMATCH",
                        message=(
                            "Selected document values must match the declaration; "
                            "ambiguous or corrected evidence requires manual evidence."
                        ),
                    )
            review_receipt = review_receipt.model_copy(
                update={
                    "replaced_analysis_id": current.analysis_id,
                    "replaced_ownership_version": current.version,
                }
            )
            now = self._clock()
            snapshot = _snapshot_prior_analysis(current)
            replacement = OwnershipAnalysisRecord(
                identity_registration_number=parent.entity.registration_number,
                identity_correction_version=len(parent.identity_corrections),
                case_id=case_id,
                version=current.version,
                analysis_id=self._uuid_factory(),
                correlation_id=self._uuid_factory(),
                root_party_id=source.root_party_id,
                provider_name=metadata.provider_name,
                provider_environment=metadata.environment,
                state=OwnershipAnalysisState.LOADING,
                parties=[item.model_copy(deep=True) for item in source.parties],
                relationships=[item.model_copy(deep=True) for item in source.relationships],
                threshold_percent=parent.policy_snapshot.ubo_threshold_percent,
                events=[
                    OwnershipWorkflowEvent(
                        sequence=1,
                        event_type=OwnershipEventType.OWNERSHIP_SOURCE_REPLACED,
                        state=OwnershipAnalysisState.LOADING,
                        outcome=EventOutcome.SUCCEEDED,
                        timestamp=now,
                        case_id=case_id,
                        analysis_id=self._uuid_factory(),
                        correlation_id=self._uuid_factory(),
                        code="MANUAL_OWNERSHIP_EVIDENCE_ACCEPTED",
                        message="Reviewed manual ownership evidence replaced the prior source.",
                        party_count=len(source.parties),
                        relationship_count=len(source.relationships),
                    )
                ],
                prior_analyses=(*current.prior_analyses[-3:], snapshot),
                manual_review_receipt=review_receipt,
                document_observations=observations,
                document_bindings=bindings,
                document_discrepancies=tuple(
                    item.model_copy(update={"verification_state": "REVIEWED"})
                    for item in compare_document_ownership(
                        observations, current.parties, current.relationships, current.evidence
                    )
                ),
                created_at=now,
                loaded_at=now,
                updated_at=now,
            )
            # Keep event identifiers bound to the replacement aggregate.
            replacement.events[0] = replacement.events[0].model_copy(
                update={
                    "analysis_id": replacement.analysis_id,
                    "correlation_id": replacement.correlation_id,
                }
            )
            if before_replace is not None:
                before_replace()
            try:
                persisted = self._repository.replace_review_required(
                    replacement, expected_version=expected_version
                )
                loaded = self._record(
                    persisted,
                    event_type=OwnershipEventType.OWNERSHIP_LOADED,
                    state=OwnershipAnalysisState.LOADED,
                    outcome=EventOutcome.SUCCEEDED,
                    message="Manual ownership source data loaded and validated.",
                    party_count=len(persisted.parties),
                    relationship_count=len(persisted.relationships),
                )
                return self._analyze_locked(case_id=loaded.case_id)
            except OwnershipRepositoryConflictError:
                raise OwnershipRequestError(
                    code="OWNERSHIP_MANUAL_REPLACEMENT_STALE",
                    message="The ownership analysis changed before manual evidence was accepted.",
                ) from None

    def _load_locked(
        self, *, case_id: UUID, provider: OwnershipProvider | None
    ) -> OwnershipAnalysisRecord:
        parent = self._cases.get_case(case_id)
        if parent is None:
            raise OwnershipRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        previous = self._repository.get_for_case(case_id)
        observations, bindings = self._document_inputs(case_id)
        documents_changed = previous is not None and previous.document_bindings != bindings
        identity_changed = (
            previous is not None
            and parent.entity is not None
            and not ownership_is_current(previous, parent)
        )
        if previous is not None and not identity_changed and not documents_changed:
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
            document_observations=observations,
            document_bindings=bindings,
            identity_registration_number=parent.entity.registration_number,
            identity_correction_version=len(parent.identity_corrections),
            version=previous.version if previous is not None else 0,
            prior_analyses=(*previous.prior_analyses[-3:], _snapshot_prior_analysis(previous))
            if previous is not None
            else (),
            analysis_id=self._uuid_factory(),
            correlation_id=self._uuid_factory(),
            state=OwnershipAnalysisState.LOADING,
            threshold_percent=parent.policy_snapshot.ubo_threshold_percent,
            created_at=now,
            updated_at=now,
        )
        try:
            record = (
                self._repository.replace_identity_bound(record, expected_version=previous.version)
                if previous is not None and identity_changed
                else self._repository.replace_document_bound(
                    record, expected_version=previous.version
                )
                if previous is not None
                else self._repository.save(record, expected_version=None)
            )
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
            overlay: HybridOverlayScenario | None = None
            if source.garden_supplement is not None:
                record.supplemental_parties = tuple(source.garden_supplement.parties)
                record.supplemental_relationships = tuple(source.garden_supplement.relationships)
                record.supplemental_evidence = (
                    *source.garden_supplement.evidence,
                    *source.garden_supplement.original_share_evidence,
                )
                source = self._merge_garden_supplement(source, metadata, parent)
                record.source_classification = "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
            elif (
                self._hybrid_overlay is not None
                and metadata.provider_name == "ACRA_REGISTRY_ACQUISITION"
                and metadata.environment == OwnershipEnvironment.MOCK
            ):
                overlay = self._hybrid_overlay.root_scenario(parent, self._clock())
                if overlay is not None:
                    source = self._apply_hybrid_root_overlay(source, record, parent, overlay)
                    record.source_classification = HYBRID_SOURCE_CLASSIFICATION
            discovery_policy = parent.policy_snapshot.ownership_discovery
            if (
                self._discovery is not None
                and discovery_policy is not None
                and metadata.provider_name == "ACRA_REGISTRY_ACQUISITION"
                # The legacy flattened Garden supplement is never a lookup source.
                and record.source_classification in _DISCOVERY_SOURCE_CLASSIFICATIONS
                and source.relationships
            ):
                # Each corporate owner is acquired as its own issuer, outside the root
                # case acquisition; the case lock is held and currentness is rechecked.
                source, record.discovery = self._discovery.expand(
                    source,
                    parent=parent,
                    policy=discovery_policy,
                    ubo_threshold_percent=parent.policy_snapshot.ubo_threshold_percent,
                    limits=DiscoveryLimits(
                        max_parties=self.max_parties,
                        max_relationships=self.max_relationships,
                        max_depth=self.max_depth,
                        max_paths_per_candidate=self.max_paths_per_candidate,
                        max_total_paths=self.max_total_paths,
                    ),
                    overlay=overlay,
                )
                self._validate_source(
                    source,
                    metadata,
                    parent.entity.registration_number,
                    local_overlay=overlay is not None,
                )
                latest = self._cases.get_case(case_id)
                if (
                    latest is None
                    or latest.goldtier_result is not None
                    or not ownership_is_current(record, latest)
                ):
                    self._raise_terminal_failure(
                        record,
                        code="OWNERSHIP_SOURCE_STALE",
                        message="The case changed while corporate ownership was acquired.",
                    )
            source = quantify_ownership_evidence(source)
            record.provider_name = metadata.provider_name
            record.provider_environment = metadata.environment
            record.root_party_id = source.root_party_id
            record.evidence = source.evidence
            record.legal_form = source.legal_form
            record.tagging = OwnershipEvidenceTagger().tag(
                source.evidence,
                case_version=len(parent.events),
                policy=parent.policy_snapshot.evidence_classifier,
                policy_version=parent.policy_snapshot.catalogue_version,
            )
            record.parties = [party.model_copy(deep=True) for party in source.parties]
            record.relationships = [item.model_copy(deep=True) for item in source.relationships]
            record.document_discrepancies = compare_document_ownership(
                observations, record.parties, record.relationships,
                (*record.evidence, *record.supplemental_evidence)
            )
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
        with self._case_lock(case_id):
            return self._analyze_locked(case_id=case_id)

    def _analyze_locked(self, *, case_id: UUID) -> OwnershipAnalysisRecord:
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
        parent = self._cases.get_case(case_id)
        if parent is not None and not ownership_is_current(record, parent):
            raise OwnershipRequestError(
                code="OWNERSHIP_IDENTITY_STALE",
                message="Ownership evidence belongs to a previous case identity.",
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
                parties=(
                    record.parties
                    if record.relationships or not record.evidence
                    else [item for item in record.parties if item.party_id == record.root_party_id]
                ),
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
            record.issues = list(calculation.issues)
            discovery = record.discovery
            # Overlay- and POC-attached branches are topologically resolved; their
            # synthetic evidence basis is reported separately below.
            unresolved = [
                item
                for item in (discovery.records if discovery is not None else ())
                if not discovery_topology_resolved(item)
            ]
            if discovery is not None and unresolved:
                bound = discovery.unresolved_upper_bound_percent
                record.issues.append(
                    OwnershipAnalysisIssue(
                        code=OwnershipIssueCode.CORPORATE_OWNERSHIP_UNRESOLVED,
                        message=(
                            f"{len(unresolved)} corporate ownership branch(es) remain "
                            "unresolved; "
                            + (
                                f"up to {_format_decimal(bound)}% root-equivalent interest "
                                "is undisclosed."
                                if bound is not None
                                else "the undisclosed root-equivalent interest is not bounded."
                            )
                        ),
                        affected_party_ids=[item.party_id for item in unresolved][:16],
                    )
                )
            # D-079 rows sit beside the graph: units without a same-entity authoritative
            # denominator stay quantities, never percentages.
            retained = [
                item
                for item in (discovery.records if discovery is not None else ())
                if item.official_shareholders
            ]
            if retained:
                # D-080: units of different (or unreported) share classes are not comparable.
                current_classes = (
                    {row.share_type for row in item.official_shareholders if row.current_interest}
                    for item in retained
                )
                mixed = any(len(classes) > 1 for classes in current_classes)
                # D-081: hybrid-lane POC links are labelled, never an ACRA denominator. An
                # issuer whose rows could not be distributed shows no percentage.
                poc = sum(
                    item.reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS for item in retained
                )
                record.issues.append(
                    OwnershipAnalysisIssue(
                        code=OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED,
                        message=(
                            f"{sum(len(item.official_shareholders) for item in retained)} "
                            "official Marketplace Mock shareholder row(s) are retained without "
                            "an entity profile; "
                            + (
                                ("current rows mix share classes; " if mixed else "")
                                + "percentages shown assume equal POC units, not an ACRA "
                                "denominator."
                                if poc == len(retained)
                                else ("current rows mix share classes; " if mixed else "")
                                + f"{poc} of {len(retained)} issuers show POC-unit percentages; "
                                "no ACRA denominator exists."
                                if poc
                                else ("current rows mix share classes and " if mixed else "")
                                + "no authoritative denominator exists, so no percentage is "
                                "inferred."
                            )
                        ),
                        affected_party_ids=[item.party_id for item in retained][:16],
                    )
                )
            if discovery is not None and discovery.unresolved_person_party_ids:
                record.issues.append(
                    OwnershipAnalysisIssue(
                        code=OwnershipIssueCode.PERSON_IDENTITY_UNRESOLVED,
                        message=(
                            "A source person identifier repeats across separate issuer "
                            "records without a verified identity binding; no aggregation "
                            "is assumed."
                        ),
                        affected_party_ids=list(discovery.unresolved_person_party_ids[:16]),
                    )
                )
            if record.source_classification == HYBRID_SOURCE_CLASSIFICATION:
                overlay_nodes = [
                    item.party_id
                    for item in (discovery.records if discovery is not None else ())
                    if item.outcome == OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY
                    or item.reason_code
                    in {
                        OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
                        OFFICIAL_BUSINESS_PROFILE_ISSUED_CAPITAL,
                    }
                ]
                poc_links = any(
                    edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
                    for edge in record.relationships
                )
                issued_capital_links = any(
                    edge.provenance.provider == POC_ISSUED_CAPITAL_PROVIDER
                    for edge in record.relationships
                )
                record.issues.append(
                    OwnershipAnalysisIssue(
                        code=OwnershipIssueCode.SYNTHETIC_OWNERSHIP_EVIDENCE,
                        message=(
                            "Ownership links are LOCAL_SYNTHETIC_RELATIONSHIP declarations or "
                            "LOCAL_POC_ASSUMED_EQUAL_UNITS / LOCAL_POC_ISSUED_CAPITAL_BASIS "
                            "estimates, not ACRA-returned ownership."
                            if issued_capital_links and poc_links
                            else "Ownership links are LOCAL_SYNTHETIC_RELATIONSHIP declarations or "
                            "LOCAL_POC_ISSUED_CAPITAL_BASIS estimates, not ACRA-returned "
                            "ownership; unverified issuers keep LOCAL_SYNTHETIC_IDENTITY."
                            if issued_capital_links
                            else "Ownership links are LOCAL_SYNTHETIC_RELATIONSHIP declarations or "
                            "LOCAL_POC_ASSUMED_EQUAL_UNITS estimates, not ACRA-returned "
                            "ownership; unverified issuers keep LOCAL_SYNTHETIC_IDENTITY."
                            if poc_links
                            else "Ownership links are LOCAL_SYNTHETIC_RELATIONSHIP demonstration "
                            "declarations, not ACRA-returned ownership; unverified issuers keep "
                            "LOCAL_SYNTHETIC_IDENTITY."
                        ),
                        affected_party_ids=[
                            item
                            for item in (record.root_party_id, *overlay_nodes)
                            if item is not None
                        ][:16],
                    )
                )
            if any(
                item.verification_state == "REVIEW_REQUIRED"
                for item in record.document_discrepancies
            ):
                record.issues.append(
                    OwnershipAnalysisIssue(
                        code=OwnershipIssueCode.CONTRADICTORY_OWNERSHIP_EVIDENCE
                        if any(
                            item.agreement == "MISMATCH" for item in record.document_discrepancies
                        )
                        else OwnershipIssueCode.UBO_REVIEW_REQUIRED,
                        message=(
                            "Proposed document ownership needs a current creator decision; "
                            "source agreement is retained separately."
                        ),
                    )
                )
            if record.supplemental_relationships and any(
                edge.provenance.provider == "ACRA_REGISTRY_ACQUISITION"
                for edge in record.relationships
            ):

                def interest_key(
                    edge: OwnershipRelationship, parties: list[Party]
                ) -> tuple[str, str]:
                    by_id = {party.party_id: party for party in parties}

                    def identity(party: Party) -> str:
                        return party.registration_number or party.display_name.casefold().strip()

                    return identity(by_id[edge.parent_party_id]), identity(
                        by_id[edge.child_party_id]
                    )

                official = {
                    interest_key(edge, record.parties): edge.ownership_percent
                    for edge in record.relationships
                }
                local = {
                    interest_key(edge, list(record.supplemental_parties)): edge.ownership_percent
                    for edge in record.supplemental_relationships
                }
                if official != local:
                    record.issues.append(
                        OwnershipAnalysisIssue(
                            code=OwnershipIssueCode.CONTRADICTORY_OWNERSHIP_EVIDENCE,
                            message=("Official and local supplemental quantities/relationships "
                                     "disagree; originals are retained for creator review."),
                        )
                    )
            causes = _review_causes(record)
            unquantified = list(causes.unquantified)
            if causes.contradictory:
                record.issues.append(
                    OwnershipAnalysisIssue(
                        code=OwnershipIssueCode.CONTRADICTORY_OWNERSHIP_EVIDENCE,
                        message="Graph and compatible scalar ownership evidence disagree; "
                        "both are retained and require review.",
                    )
                )
            has_conflict = causes.has_conflict
            has_unbound = causes.has_unbound
            has_unsupported_activity = causes.has_unsupported_activity
            has_unresolved_semantics = causes.unresolved_kinds or bool(causes.unresolved_roles)
            if (
                not record.relationships
                or unquantified
                or has_conflict
                or has_unbound
                or has_unresolved_semantics
                or record.legal_form == RegistryLegalForm.OTHER
            ):
                # An unquantified source is a review outcome, not a broken engine.
                has_units = any(
                    item.kind == "SHARE_UNITS" for item in (unquantified or record.evidence)
                )
                has_semantic_interest = any(
                    item.kind in {"ROLE", "CONTROL", "MEMBERSHIP_INTEREST"}
                    and item.raw_value.upper() in {"OWNER", "PARTNER", "MEMBER", "SHAREHOLDER"}
                    for item in record.evidence
                ) or any(item.kind == "CONTROL" for item in record.evidence)
                code = (
                    OwnershipIssueCode.OWNERSHIP_METHOD_UNSUPPORTED
                    if record.legal_form == RegistryLegalForm.OTHER
                    else OwnershipIssueCode.UBO_REVIEW_REQUIRED
                    if has_conflict
                    else OwnershipIssueCode.UBO_REVIEW_REQUIRED
                    if has_unbound
                    else OwnershipIssueCode.UBO_REVIEW_REQUIRED
                    if has_unsupported_activity
                    else OwnershipIssueCode.OWNERSHIP_DENOMINATOR_REQUIRED
                    if has_units
                    else OwnershipIssueCode.UBO_REVIEW_REQUIRED
                    if has_semantic_interest or has_unresolved_semantics or unquantified
                    else OwnershipIssueCode.OWNERSHIP_REQUIRED
                )
                message = (
                    "No ownership method is supported for this registry legal form."
                    if record.legal_form == RegistryLegalForm.OTHER
                    else "Conflicting source ownership evidence requires review."
                    if has_conflict
                    else "Ownership scalar entity binding is unavailable; "
                    "no percentage is inferred."
                    if has_unbound
                    else "Ownership activity status is unsupported or unresolved; "
                    "no active interest "
                    "is inferred."
                    if has_unsupported_activity
                    else "Share units are present; a same-entity compatible "
                    "authoritative denominator "
                    "is required."
                    if has_units
                    else "Unquantified role/control evidence requires review; "
                    "no legal determination "
                    "or ownership percentage is inferred."
                    if has_semantic_interest or has_unresolved_semantics or unquantified
                    else "No quantified registry ownership evidence is available."
                )
                record.issues.append(OwnershipAnalysisIssue(code=code, message=message))
            record.candidates = build_ownership_candidates(
                graph,
                PathCalculation(
                    paths_by_party=calculation.paths_by_party, issues=tuple(record.issues)
                ),
                aggregated,
                threshold_percent=record.threshold_percent,
            )
            if record.source_classification == HYBRID_SOURCE_CLASSIFICATION:
                basis = synthetic_basis_threshold_results(
                    aggregated,
                    record.issues,
                    threshold_percent=record.threshold_percent,
                    unresolved_upper_bound_percent=(
                        discovery.unresolved_upper_bound_percent if discovery is not None else None
                    ),
                )
                record.candidates = [
                    OwnershipCandidate.model_validate(
                        {
                            **item.model_dump(),
                            "synthetic_basis_threshold_result": basis[item.party.party_id],
                        }
                    )
                    for item in record.candidates
                ]
            record.analyzed_at = self._clock()
            if record.issues:
                # D-085: opt-in acceptance of the scenario's declared POC basis, recorded
                # beside the unchanged review state, issues and classifications.
                record.poc_acceptance = (
                    eligible_poc_acceptance(
                        record,
                        scenario=self._poc_scenario(record),
                        accepted_at=record.analyzed_at,
                        ownership_version=record.version + 1,
                    )
                    if self._poc_acceptance_enabled
                    else None
                )
                record = self._record(
                    record,
                    event_type=OwnershipEventType.OWNERSHIP_REVIEW_REQUIRED,
                    state=OwnershipAnalysisState.REVIEW_REQUIRED,
                    outcome=EventOutcome.REVIEW_REQUIRED,
                    code=(
                        "OWNERSHIP_POC_BASIS_ACCEPTED"
                        if record.poc_acceptance is not None
                        else "OWNERSHIP_GRAPH_REVIEW_REQUIRED"
                    ),
                    message=(
                        "Ownership calculated on the scenario's declared POC basis and "
                        "accepted for readiness by D-085; classification review is retained."
                        if record.poc_acceptance is not None
                        else "Ownership analysis completed with issues requiring human review."
                    ),
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
            parent = self._cases.get_case(case_id)
            if parent is not None and not ownership_is_current(record, parent):
                return None
            if record.document_bindings != self._document_inputs(case_id)[1]:
                return None
            return record
        if self._cases.get_case(case_id) is None:
            raise OwnershipRequestError(
                code="ONBOARDING_CASE_NOT_FOUND",
                message="The onboarding case was not found.",
            )
        return None

    def registry_dependency_is_obsolete(
        self,
        *,
        case_id: UUID,
        evidence_version: str,
        registry_evidence_generation: int | None = None,
    ) -> bool:
        """Inspect retained provenance without making stale ownership current again.

        A known durable registry binding outlives bounded analysis history. Equal
        or future generations stay blocking. Legacy references require retained
        registry provenance and the existing currentness predicate, never a guess.
        """
        with self._case_lock(case_id):
            parent = self._cases.get_case(case_id)
            if parent is None:
                return False
            if registry_evidence_generation is not None:
                return 0 <= registry_evidence_generation < len(parent.identity_corrections)
            retained = self._repository.get_for_case(case_id)
            if retained is None:
                return False
            analyses: tuple[OwnershipAnalysisRecord | PriorOwnershipAnalysisSnapshot, ...] = (
                retained,
                *retained.prior_analyses,
            )
            for analysis in analyses:
                if evidence_version == f"ownership:{analysis.analysis_id}:{analysis.version}":
                    return (
                        analysis.provider_name == "ACRA_REGISTRY_ACQUISITION"
                        and not ownership_is_current(analysis, parent)
                    )
            return False

    def document_dependency_is_obsolete(
        self, *, case_id: UUID, evidence_version: str,
    ) -> bool:
        """Prove that a retained ownership checkpoint uses superseded document inputs."""
        with self._case_lock(case_id):
            retained = self._repository.get_for_case(case_id)
            if retained is None:
                return False
            current_bindings = self._document_inputs(case_id)[1]
            analyses: tuple[OwnershipAnalysisRecord | PriorOwnershipAnalysisSnapshot, ...] = (
                retained, *retained.prior_analyses
            )
            return any(
                evidence_version == f"ownership:{analysis.analysis_id}:{analysis.version}"
                and analysis.document_bindings != current_bindings
                for analysis in analyses
            )

    def current_registry_dependency_generation(
        self,
        *,
        case_id: UUID,
        evidence_version: str,
    ) -> int | None:
        """Bind a newly raised dependency only to proven current registry evidence."""
        with self._case_lock(case_id):
            parent = self._cases.get_case(case_id)
            retained = self._repository.get_for_case(case_id)
            if (
                parent is None
                or retained is None
                or retained.provider_name != "ACRA_REGISTRY_ACQUISITION"
                or evidence_version != f"ownership:{retained.analysis_id}:{retained.version}"
                or not ownership_is_current(retained, parent)
            ):
                return None
            return len(parent.identity_corrections)

    def _document_inputs(
        self, case_id: UUID
    ) -> tuple[tuple[DocumentOwnershipObservation, ...], tuple[OwnershipDocumentBinding, ...]]:
        return (
            current_document_inputs(self._documents.list_documents(case_id=case_id))
            if self._documents is not None
            else ((), ())
        )

    def _merge_garden_supplement(
        self,
        source: OwnershipSourceResult,
        metadata: OwnershipProviderMetadata,
        parent: OnboardingCase,
    ) -> OwnershipSourceResult:
        # Only this explicitly enabled, proof-bound component may carry different provenance.
        from app.connectors.registry_ownership import (
            build_garden_supplement,
            garden_official_evidence_is_eligible,
        )

        supplement = source.garden_supplement
        now = self._clock()
        if (
            not self._garden_supplement_enabled
            or supplement is None
            or metadata.provider_name != "ACRA_REGISTRY_ACQUISITION"
            or metadata.environment != OwnershipEnvironment.MOCK
            or not garden_official_evidence_is_eligible(parent, now)
            or parent.registry_acquisition is None
            or supplement.official_retrieved_at != parent.registry_acquisition.retrieved_at
            or supplement.identity_correction_version != len(parent.identity_corrections)
            or supplement.root_party_id != source.root_party_id
        ):
            raise OwnershipGraphError
        local = OwnershipSourceResult(
            root_party_id=supplement.root_party_id,
            parties=supplement.parties,
            relationships=supplement.relationships,
            evidence=supplement.evidence,
        )
        self._validate_source(
            local,
            OwnershipProviderMetadata(
                provider_name="LOCAL_SYNTHETIC_SUPPLEMENT", environment=OwnershipEnvironment.LOCAL
            ),
            parent.requested_uen,
        )
        expected = build_garden_supplement(parent, now)

        def edge_values(edges: list[OwnershipRelationship]) -> list[tuple[object, ...]]:
            return [
                (
                    item.relationship_id,
                    item.parent_party_id,
                    item.child_party_id,
                    item.ownership_percent,
                    item.provenance.source_reference,
                )
                for item in edges
            ]

        def scalar_values(items: tuple[OwnershipEvidence, ...]) -> list[tuple[object, ...]]:
            return [
                (
                    item.evidence_id,
                    item.entity_identifier,
                    item.party_id,
                    item.kind,
                    item.numeric_value,
                    item.determination_basis,
                )
                for item in items
            ]

        if (
            supplement.parties != expected.parties
            or edge_values(supplement.relationships) != edge_values(expected.relationships)
            or scalar_values(supplement.evidence) != scalar_values(expected.evidence)
            or scalar_values(supplement.original_share_evidence)
            != scalar_values(expected.original_share_evidence)
            or any(edge.provenance.sourced_at > now for edge in supplement.relationships)
            or any(item.retrieved_at > now for item in supplement.evidence)
            or any(
                item.provider != "LOCAL_SYNTHETIC_SUPPLEMENT"
                or item.environment != "LOCAL"
                or item.retrieved_at > now
                for item in supplement.original_share_evidence
            )
        ):
            raise OwnershipGraphError
        if source.relationships or any(
            item.kind in {"DIRECT_PERCENTAGE", "SHARE_UNITS"} for item in source.evidence
        ):
            # Retain independent components outside arithmetic until agreement or creator decision.
            return source.model_copy(update={"garden_supplement": None}, deep=True)
        by_id = {item.party_id: item for item in source.parties}
        for party in supplement.parties:
            if party.party_id in by_id and by_id[party.party_id] != party:
                raise OwnershipGraphError
            by_id[party.party_id] = party
        merged = OwnershipSourceResult(
            root_party_id=source.root_party_id,
            parties=list(by_id.values()),
            relationships=[*source.relationships, *supplement.relationships],
            evidence=(*source.evidence, *supplement.evidence),
            legal_form=source.legal_form,
        )
        if (
            len(merged.parties) > self.max_parties
            or len(merged.relationships) > self.max_relationships
        ):
            raise OwnershipGraphError
        return merged

    def _case_lock(self, case_id: UUID) -> AbstractContextManager[object]:
        lock_factory = getattr(self._cases, "case_lock", None)
        return lock_factory(case_id) if callable(lock_factory) else nullcontext()

    def _apply_hybrid_root_overlay(
        self,
        source: OwnershipSourceResult,
        record: OwnershipAnalysisRecord,
        parent: OnboardingCase,
        overlay: HybridOverlayScenario,
    ) -> OwnershipSourceResult:
        """Add the root's declared direct holders as separately labelled local links."""

        issuer = overlay.issuer(overlay.root_uen)
        if issuer is None or parent.entity is None:
            raise OwnershipGraphError
        root = next(party for party in source.parties if party.party_id == source.root_party_id)
        component = overlay_component(overlay, issuer, issuer_party=root, sourced_at=self._clock())
        record.supplemental_evidence = component.share_evidence
        if source.relationships or any(
            item.kind in {"DIRECT_PERCENTAGE", "SHARE_UNITS"} for item in source.evidence
        ):
            # Official quantity stays the graph; the declaration is retained beside it
            # outside arithmetic, and the existing comparison requires review.
            record.supplemental_parties = component.parties
            record.supplemental_relationships = component.relationships
            return source
        known = {party.party_id for party in source.parties}
        if any(party.party_id in known for party in component.parties[1:]):
            raise OwnershipGraphError
        merged = OwnershipSourceResult(
            root_party_id=source.root_party_id,
            parties=[*source.parties, *component.parties[1:]],
            relationships=list(component.relationships),
            evidence=source.evidence,
            legal_form=source.legal_form,
        )
        self._validate_source(
            merged,
            OwnershipProviderMetadata(
                provider_name="ACRA_REGISTRY_ACQUISITION", environment=OwnershipEnvironment.MOCK
            ),
            parent.entity.registration_number,
            local_overlay=True,
        )
        return merged

    def _validate_source(
        self,
        source: OwnershipSourceResult,
        metadata: OwnershipProviderMetadata,
        registration_number: str,
        *,
        local_overlay: bool = False,
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
            if local_overlay and (provenance.provider, provenance.environment) in {
                (OVERLAY_RELATIONSHIP_PROVIDER, OwnershipEnvironment.LOCAL),
                (POC_EQUAL_UNITS_PROVIDER, OwnershipEnvironment.LOCAL),
                (POC_ISSUED_CAPITAL_PROVIDER, OwnershipEnvironment.LOCAL),
            }:
                continue
            if (
                provenance.provider != metadata.provider_name
                or provenance.environment != metadata.environment
            ):
                raise OwnershipGraphError
        for item in source.evidence:
            if (
                item.provider != metadata.provider_name
                or item.environment != metadata.environment.value
            ):
                raise OwnershipGraphError
            if item.entity_identifier not in {None, registration_number}:
                # Nested percentages must match an existing edge's actual owned entity.
                entities = {party.party_id: party for party in source.parties}
                if item.kind not in {"DIRECT_PERCENTAGE", "SHARE_UNITS", "UNKNOWN"} or not any(
                    edge.child_party_id == item.party_id
                    and (
                        item.kind != "DIRECT_PERCENTAGE"
                        or edge.ownership_percent == item.numeric_value
                    )
                    and entities[edge.parent_party_id].party_type == PartyType.LEGAL_ENTITY
                    and entities[edge.parent_party_id].registration_number == item.entity_identifier
                    for edge in source.relationships
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


def _poc_assumed_edges(
    record: OwnershipAnalysisRecord,
) -> frozenset[tuple[str, str, Decimal]]:
    """D-081 POC-assumed links behind this analysis: its own, or those it kept.

    A `CURRENT_EVIDENCE` replacement copies the kept graph under the manual label, so its
    receipt is followed back through the retained prior analyses.
    """

    priors = {item.analysis_id: item for item in record.prior_analyses}
    analysis: OwnershipAnalysisRecord | PriorOwnershipAnalysisSnapshot | None = record
    seen: set[UUID] = set()
    while analysis is not None and analysis.analysis_id not in seen:
        seen.add(analysis.analysis_id)
        edges = frozenset(
            (edge.parent_party_id, edge.child_party_id, edge.ownership_percent)
            for edge in (*analysis.relationships, *analysis.supplemental_relationships)
            if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
        )
        if edges:
            return edges
        receipt = analysis.manual_review_receipt
        if receipt is None or receipt.source_selection != "CURRENT_EVIDENCE":
            break
        replaced = receipt.replaced_analysis_id
        analysis = priors.get(replaced) if replaced is not None else None
    return frozenset()


def _snapshot_prior_analysis(record: OwnershipAnalysisRecord) -> PriorOwnershipAnalysisSnapshot:
    """Retain bounded immutable source and decision evidence before replacement."""

    return PriorOwnershipAnalysisSnapshot(
        version=record.version,
        evidence=record.evidence,
        document_observations=record.document_observations,
        document_bindings=record.document_bindings,
        document_discrepancies=record.document_discrepancies,
        source_classification=record.source_classification,
        supplemental_parties=record.supplemental_parties,
        supplemental_relationships=record.supplemental_relationships,
        supplemental_evidence=record.supplemental_evidence,
        manual_review_receipt=record.manual_review_receipt,
        poc_acceptance=record.poc_acceptance,
        tagging=record.tagging,
        identity_registration_number=record.identity_registration_number,
        identity_correction_version=record.identity_correction_version,
        legal_form=record.legal_form,
        discovery=record.discovery,
        analysis_id=record.analysis_id,
        correlation_id=record.correlation_id,
        root_party_id=record.root_party_id,
        provider_name=record.provider_name,
        provider_environment=record.provider_environment,
        state=record.state,
        parties=tuple(record.parties[:100]),
        relationships=tuple(record.relationships[:200]),
        candidates=tuple(record.candidates[:100]),
        issues=tuple(record.issues[:100]),
        threshold_percent=record.threshold_percent,
        events=tuple(record.events[-128:]),
        error=record.error,
        created_at=record.created_at,
        loaded_at=record.loaded_at,
        analyzed_at=record.analyzed_at,
        updated_at=record.updated_at,
    )


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
