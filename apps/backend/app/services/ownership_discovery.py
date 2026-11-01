"""Bounded registry-driven corporate-owner discovery for the ownership boundary.

The coordinator schedules separate issuer acquisitions through the existing registry
owner and attaches each issuer's own normalized direct-ownership record to one shared
graph. It never classifies candidates: every path product comes from the authoritative
ownership engine, and threshold classification stays in OwnershipAnalysisService.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from re import compile as compile_pattern
from time import monotonic
from typing import Literal, Protocol

from pydantic import ValidationError

from app.connectors.errors import ConnectorError
from app.connectors.hybrid_ownership_overlay import (
    OFFICIAL_MARKETPLACE_PROFILE_REFERENCE,
    OVERLAY_RELATIONSHIP_PROVIDER,
    POC_EQUAL_UNITS_PROVIDER,
    POC_ISSUED_CAPITAL_PROVIDER,
    HybridOverlayScenario,
    OverlayIssuer,
    issued_capital_matches,
    official_equal_unit_component,
    official_issued_capital_component,
    overlay_component,
)
from app.connectors.ownership import OwnershipSourceResult
from app.connectors.registry_ownership import acquisition_ownership_source
from app.domain.jurisdiction import is_eligible_singapore_uen
from app.domain.models import (
    OnboardingCase,
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryOperation,
    RegistryOperationStatus,
    SourceEnvironment,
)
from app.domain.ownership import (
    OFFICIAL_BUSINESS_PROFILE_EMPTY,
    OFFICIAL_BUSINESS_PROFILE_ISSUED_CAPITAL,
    OFFICIAL_BUSINESS_PROFILE_RETAINED,
    OFFICIAL_SHAREHOLDERS_EMPTY,
    OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS,
    OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
    RESOLVED_DISCOVERY_OUTCOMES,
    OfficialBusinessProfileObservation,
    OfficialBusinessProfileShareholder,
    OfficialEntityLookup,
    OfficialOfficerRoleObservation,
    OfficialShareCapitalObservation,
    OfficialShareholderLookup,
    OfficialShareholderObservation,
    OwnershipDiscoveryAudit,
    OwnershipDiscoveryOutcome,
    OwnershipDiscoveryRecord,
    OwnershipIssueCode,
    OwnershipProvenance,
    OwnershipRelationship,
    Party,
    PartyType,
    discovery_topology_resolved,
)
from app.domain.ownership_evidence import OwnershipEvidence
from app.domain.policy import OwnershipDiscoveryPolicySnapshot, RegistryPolicySnapshot
from app.domain.registry_legal_form import RegistryLegalForm, classify_registry_legal_form
from app.services.ownership_analysis import (
    DiscoveryLimits,
    OwnershipGraph,
    OwnershipGraphError,
    PathCalculation,
    aggregate_ownership_paths,
    build_ownership_graph,
    calculate_ownership_paths,
    ownership_collection_complete,
    poc_mixed_share_classes,
    quantify_poc_equal_units,
    validate_ownership_graph,
)
from app.services.registry_acquisition import (
    RegistryAcquisitionBusyError,
    RegistryCacheError,
    SubsidiaryBusinessProfileEvidence,
    SubsidiaryRegistryEvidence,
    SubsidiaryShareholderEvidence,
)

# Non-editable technical safeguards; they remain effective when the business budget
# is disabled. Acquisition is sequential, so concurrency per discovery run is one.
TECHNICAL_MAX_ISSUER_LOOKUPS = 32
TECHNICAL_DEADLINE_SECONDS = 60.0
TECHNICAL_MAX_EVIDENCE = 256
_SAFE_SCOPED_ID = compile_pattern(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_BOUND_INVALIDATING_ISSUES = frozenset(
    {
        OwnershipIssueCode.CYCLE_DETECTED,
        OwnershipIssueCode.MAXIMUM_DEPTH_EXCEEDED,
        OwnershipIssueCode.PATH_LIMIT_EXCEEDED,
    }
)


class SubsidiaryRegistryReader(Protocol):
    def acquire_subsidiary_registry_evidence(
        self,
        identifier: str,
        *,
        case_policy: RegistryPolicySnapshot | None,
        policy_version: int,
        cancelled: Callable[[], bool] | None = None,
    ) -> SubsidiaryRegistryEvidence: ...


@dataclass(frozen=True)
class VerifiedPersonBinding:
    """Explicit accepted person identity binding across issuer records.

    No current provider or reviewer flow supplies these bindings; without one, equal
    source identifiers in different issuer records stay distinct and require review.
    """

    issuer_registration_number: str
    source_party_id: str
    person_key: str


@dataclass(frozen=True)
class _OverlayIdentity:
    identity_basis: Literal["OFFICIAL_MOCK_ENTITY_PROFILE", "LOCAL_SYNTHETIC_IDENTITY"]
    official_entity_lookup: OfficialEntityLookup
    official_legal_form: RegistryLegalForm | None
    officer_roles: tuple[OfficialOfficerRoleObservation, ...] = ()


class OwnershipDiscoveryCoordinator:
    """Schedule bounded issuer retrieval; never a second ownership calculator."""

    def __init__(
        self,
        reader: SubsidiaryRegistryReader,
        *,
        max_issuer_lookups: int = TECHNICAL_MAX_ISSUER_LOOKUPS,
        deadline_seconds: float = TECHNICAL_DEADLINE_SECONDS,
        clock: Callable[[], float] = monotonic,
        utc_clock: Callable[[], datetime] | None = None,
        verified_person_bindings: Iterable[VerifiedPersonBinding] = (),
    ) -> None:
        if not 1 <= max_issuer_lookups <= TECHNICAL_MAX_ISSUER_LOOKUPS or not (
            0 < deadline_seconds <= TECHNICAL_DEADLINE_SECONDS
        ):
            raise ValueError("ownership discovery technical bounds are invalid")
        bindings: dict[tuple[str, str], str] = {}
        for item in verified_person_bindings:
            key = (item.issuer_registration_number.strip().upper(), item.source_party_id)
            if key in bindings or not item.person_key.strip():
                raise ValueError("verified person bindings must be unique and non-blank")
            bindings[key] = item.person_key.strip()
        self._reader = reader
        self._max_issuer_lookups = max_issuer_lookups
        self._deadline_seconds = deadline_seconds
        self._clock = clock
        self._utc_clock = utc_clock or (lambda: datetime.now(UTC))
        self._bindings = bindings

    def expand(
        self,
        source: OwnershipSourceResult,
        *,
        parent: OnboardingCase,
        policy: OwnershipDiscoveryPolicySnapshot,
        ubo_threshold_percent: Decimal,
        limits: DiscoveryLimits,
        overlay: HybridOverlayScenario | None = None,
    ) -> tuple[OwnershipSourceResult, OwnershipDiscoveryAudit]:
        return _DiscoveryRun(
            coordinator=self,
            source=source,
            parent=parent,
            policy=policy,
            ubo_threshold=ubo_threshold_percent,
            limits=limits,
            overlay=overlay,
        ).run()


class _DiscoveryRun:
    def __init__(
        self,
        *,
        coordinator: OwnershipDiscoveryCoordinator,
        source: OwnershipSourceResult,
        parent: OnboardingCase,
        policy: OwnershipDiscoveryPolicySnapshot,
        ubo_threshold: Decimal,
        limits: DiscoveryLimits,
        overlay: HybridOverlayScenario | None = None,
    ) -> None:
        if parent.entity is None:
            raise OwnershipGraphError
        # A whitelisted scenario may supply declared direct holders only for its own
        # issuers, and only after a definitive official lookup for that issuer.
        self._overlay = overlay
        self._reader = coordinator._reader
        self._bindings = coordinator._bindings
        self._max_lookups = coordinator._max_issuer_lookups
        self._clock = coordinator._clock
        self._utc_clock = coordinator._utc_clock
        self._deadline = coordinator._clock() + coordinator._deadline_seconds
        self._parent = parent
        self._policy = policy
        self._ubo = ubo_threshold
        self._limits = limits
        self._source = source
        self._root = source.root_party_id
        self._root_uen = parent.entity.registration_number.strip().upper()
        self._parties: dict[str, Party] = {
            item.party_id: item.model_copy(deep=True) for item in source.parties
        }
        self._relationships = [item.model_copy(deep=True) for item in source.relationships]
        self._evidence = list(source.evidence)
        self._issuer_nodes: dict[str, str] = {self._root_uen: self._root}
        self._duplicate_issuer_nodes: set[str] = set()
        for party in source.parties:
            uen = _verified_uen(party)
            if uen is None or party.party_id == self._root:
                continue
            if uen in self._issuer_nodes:
                self._duplicate_issuer_nodes.add(party.party_id)
            else:
                self._issuer_nodes[uen] = party.party_id
        self._person_sources: dict[str, tuple[str, str]] = {}
        self._person_nodes: dict[str, str] = {}
        for party in source.parties:
            if party.party_type == PartyType.NATURAL_PERSON:
                self._register_person(party.party_id, self._root_uen, party.party_id)
        self._records: dict[str, OwnershipDiscoveryRecord] = {}
        self._looked_up: set[str] = set()
        self._lookups = 0
        self._provider_backed = 0
        self._cache_hits = 0

    def run(self) -> tuple[OwnershipSourceResult, OwnershipDiscoveryAudit]:
        # Each round finalizes or attaches at least one frontier issuer, so the round
        # count is bounded by lookups plus unresolved leaves; this cap is a backstop.
        for _ in range(2 * self._max_lookups + self._limits.max_parties):
            graph, calculation = self._calculate()
            frontier = self._frontier(graph)
            if not frontier:
                break
            depths = _depths(graph)
            shares = calculation.unresolved_entity_shares
            candidates: list[str] = []
            for node in frontier:
                reason = self._ineligible(node, depths[node])
                if reason is None:
                    candidates.append(node)
                else:
                    self._finalize(node, reason[0], depths[node], shares, reason[1])
            if not candidates:
                continue
            valid, could_change, _ = self._bound(graph, calculation)
            trace = self._policy.trace_threshold_percent
            selected = [node for node in candidates if shares.get(node, Decimal("0")) >= trace]
            if not selected and (not valid or could_change):
                # A deferral cannot be proved safe, so prefer bounded extra expansion.
                selected = list(candidates)
            if not selected:
                for node in candidates:
                    self._finalize(
                        node,
                        OwnershipDiscoveryOutcome.DEFERRED_BELOW_TRACE_THRESHOLD,
                        depths[node],
                        shares,
                    )
                continue
            selected.sort(key=lambda node: (-shares.get(node, Decimal("0")), self._uen(node)))
            for node in selected:
                self._acquire(node, depths[node], shares)
        graph, calculation = self._calculate()
        depths = _depths(graph)
        for node in self._frontier(graph):
            self._finalize(
                node,
                OwnershipDiscoveryOutcome.HARD_LIMIT,
                depths[node],
                calculation.unresolved_entity_shares,
                "DISCOVERY_ROUND_LIMIT",
            )
        valid, could_change, upper_bound = self._bound(graph, calculation)
        records = tuple(
            sorted(
                self._records.values(),
                key=lambda item: (item.depth, item.registration_number or "", item.party_id),
            )
        )
        complete = all(item.outcome in RESOLVED_DISCOVERY_OUTCOMES for item in records)
        ambiguous = self._ambiguous_persons()
        # D-112: equal-unit issuers outside a scenario need the same evidence separation.
        hybrid = self._overlay is not None or any(
            item.reason_code == OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS for item in records
        )
        certainty = (
            # Declared synthetic links can never certify a classification outcome.
            "UNCERTAIN"
            if hybrid
            else "COMPLETE"
            if complete and valid
            else "BOUNDED_NO_THRESHOLD_CHANGE"
            if not complete and valid and not could_change
            else "UNCERTAIN"
        )
        audit = OwnershipDiscoveryAudit(
            trace_threshold_percent=self._policy.trace_threshold_percent,
            ubo_threshold_percent=self._ubo,
            max_corporate_depth=self._policy.max_corporate_depth,
            call_budget_enabled=self._policy.call_budget_enabled,
            call_budget_max=self._policy.call_budget_max,
            graph_complete=complete,
            classification_certainty=certainty,
            unresolved_upper_bound_percent=upper_bound if valid else None,
            registry_lookups=self._lookups,
            provider_backed_lookups=self._provider_backed,
            cache_hits=self._cache_hits,
            records=records,
            unresolved_person_party_ids=ambiguous[:32],
            overlay_scenario_id=self._overlay.scenario_id if self._overlay is not None else None,
            topology_complete=(
                all(discovery_topology_resolved(item) for item in records) if hybrid else None
            ),
            official_identity_complete=(
                all(
                    item.outcome in RESOLVED_DISCOVERY_OUTCOMES
                    or item.identity_basis == "OFFICIAL_MOCK_ENTITY_PROFILE"
                    for item in records
                )
                if hybrid
                else None
            ),
            quantitative_evidence_complete=False if hybrid else None,
        )
        expanded = OwnershipSourceResult(
            root_party_id=self._root,
            parties=list(self._parties.values()),
            relationships=self._relationships,
            evidence=tuple(self._evidence),
            legal_form=self._source.legal_form,
        )
        return expanded, audit

    def _calculate(self) -> tuple[OwnershipGraph, PathCalculation]:
        graph = build_ownership_graph(
            OwnershipSourceResult(
                root_party_id=self._root,
                parties=list(self._parties.values()),
                relationships=self._relationships,
            )
        )
        return graph, calculate_ownership_paths(
            graph,
            max_depth=self._limits.max_depth,
            max_paths_per_candidate=self._limits.max_paths_per_candidate,
            max_total_paths=self._limits.max_total_paths,
        )

    def _frontier(self, graph: OwnershipGraph) -> list[str]:
        reachable = _depths(graph)
        return sorted(
            (
                party_id
                for party_id, party in self._parties.items()
                if party_id != self._root
                and party_id in reachable
                and party.party_type == PartyType.LEGAL_ENTITY
                and not graph.adjacency.get(party_id)
                and party_id not in self._records
            ),
            key=lambda node: (self._uen(node), node),
        )

    def _ineligible(
        self, node: str, depth: int
    ) -> tuple[OwnershipDiscoveryOutcome, str | None] | None:
        party = self._parties[node]
        uen = _verified_uen(party)
        if party.country not in {None, "SG"}:
            return OwnershipDiscoveryOutcome.FOREIGN_UNSUPPORTED, None
        if uen is None:
            return OwnershipDiscoveryOutcome.UNVERIFIED_UEN, None
        if node in self._duplicate_issuer_nodes or self._issuer_nodes.get(uen) != node:
            return OwnershipDiscoveryOutcome.UNVERIFIED_UEN, "DUPLICATE_ISSUER_IDENTITY"
        if uen in self._looked_up:
            return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_ALREADY_ACQUIRED"
        if depth > self._policy.max_corporate_depth:
            return OwnershipDiscoveryOutcome.DEPTH_LIMIT, None
        return None

    def _acquire(self, node: str, depth: int, shares: dict[str, Decimal]) -> None:
        if self._clock() >= self._deadline:
            self._finalize(
                node, OwnershipDiscoveryOutcome.HARD_LIMIT, depth, shares, "DISCOVERY_DEADLINE"
            )
            return
        if self._lookups >= self._max_lookups:
            self._finalize(
                node, OwnershipDiscoveryOutcome.HARD_LIMIT, depth, shares, "ISSUER_LOOKUP_LIMIT"
            )
            return
        if (
            self._policy.call_budget_enabled
            and self._provider_backed >= self._policy.call_budget_max
        ):
            self._finalize(node, OwnershipDiscoveryOutcome.BUSINESS_BUDGET, depth, shares)
            return
        uen = self._uen(node)
        self._looked_up.add(uen)
        self._lookups += 1
        provider_backed = True
        outcome: OwnershipDiscoveryOutcome
        reason: str | None
        identity: _OverlayIdentity | None = None
        shareholders: tuple[OfficialShareholderObservation, ...] = ()
        shareholder_lookup: OfficialShareholderLookup | None = None
        business_profile: OfficialBusinessProfileObservation | None = None
        try:
            evidence = self._reader.acquire_subsidiary_registry_evidence(
                uen,
                case_policy=self._parent.policy_snapshot.registry,
                policy_version=self._parent.policy_snapshot.catalogue_version,
                cancelled=lambda: self._clock() >= self._deadline,
            )
            provider_backed = evidence.provider_backed
        except RegistryAcquisitionBusyError:
            # Uncertain provider activity counts against the budget conservatively.
            outcome, reason = OwnershipDiscoveryOutcome.HARD_LIMIT, "REGISTRY_ACQUISITION_BUSY"
        except RegistryCacheError as error:
            outcome, reason = OwnershipDiscoveryOutcome.CACHE_FAILURE, error.code
        except (ConnectorError, ValueError):
            outcome, reason = OwnershipDiscoveryOutcome.PROVIDER_FAILED, "REGISTRY_PROVIDER_FAILED"
        except Exception:
            outcome = OwnershipDiscoveryOutcome.PROVIDER_FAILED
            reason = "REGISTRY_UNEXPECTED_FAILURE"
        else:
            issuer_overlay = self._overlay.issuer(uen) if self._overlay is not None else None
            if issuer_overlay is not None:
                outcome, reason, identity = self._attach_overlay(
                    node, uen, evidence, issuer_overlay
                )
            else:
                rejected, reason = self._classify(uen, evidence.acquisition)
                if rejected is None:
                    outcome, reason = self._attach(node, uen, evidence, provider_backed)
                elif rejected == OwnershipDiscoveryOutcome.NOT_FOUND:
                    (
                        outcome,
                        reason,
                        shareholders,
                        shareholder_lookup,
                        shareholder_backed,
                    ) = self._official_shareholders(uen)
                    provider_backed = provider_backed or shareholder_backed
                    if (
                        shareholders
                        # D-112: outside a scenario the same Mock equal-unit rule applies,
                        # but only to one reported class and currency (owner O2).
                        and (self._overlay is not None or _single_current_class(shareholders))
                        and self._attach_poc_distribution(node, uen, shareholders)
                    ):
                        reason = OFFICIAL_SHAREHOLDERS_POC_EQUAL_UNITS
                    elif (
                        reason == OFFICIAL_SHAREHOLDERS_EMPTY
                        and self._overlay is not None
                        and uen in self._overlay.business_profile_issuers
                    ):
                        (
                            outcome,
                            reason,
                            business_profile,
                            profile_backed,
                        ) = self._official_business_profile(node, uen)
                        provider_backed = provider_backed or profile_backed
                else:
                    outcome = rejected
        if provider_backed:
            self._provider_backed += 1
        else:
            self._cache_hits += 1
        self._finalize(
            node,
            outcome,
            depth,
            shares,
            reason,
            identity,
            shareholders,
            shareholder_lookup,
            business_profile,
        )

    def _official_business_profile(self, node: str, uen: str) -> tuple[
        OwnershipDiscoveryOutcome, str | None, OfficialBusinessProfileObservation | None, bool
    ]:
        """D-088: a scenario-named issuer's official businessProfile, in the hybrid lane only.

        Read once, after the same issuer's entity profile and shareholder operation were
        both definitively empty. Status-free rows are assumed current only when they
        exactly equal the issuer's single compatible issued class; then they attach as
        labelled issued-capital links. Otherwise the profile is retained unattached, and
        any failure stops safely with nothing retained.
        """
        empty = (OwnershipDiscoveryOutcome.NOT_FOUND, OFFICIAL_SHAREHOLDERS_EMPTY, None, False)
        reader = getattr(self._reader, "acquire_subsidiary_business_profile_evidence", None)
        if reader is None:
            return empty
        try:
            result: SubsidiaryBusinessProfileEvidence | None = reader(
                uen,
                case_policy=self._parent.policy_snapshot.registry,
                policy_version=self._parent.policy_snapshot.catalogue_version,
                cancelled=lambda: self._clock() >= self._deadline,
            )
        except RegistryAcquisitionBusyError:
            return OwnershipDiscoveryOutcome.HARD_LIMIT, "REGISTRY_ACQUISITION_BUSY", None, True
        except RegistryCacheError as error:
            return OwnershipDiscoveryOutcome.CACHE_FAILURE, error.code, None, True
        except (ConnectorError, ValueError):
            return (
                OwnershipDiscoveryOutcome.PROVIDER_FAILED,
                "BUSINESS_PROFILE_PROVIDER_FAILED",
                None,
                True,
            )
        except Exception:
            return (
                OwnershipDiscoveryOutcome.PROVIDER_FAILED,
                "BUSINESS_PROFILE_UNEXPECTED_FAILURE",
                None,
                True,
            )
        if result is None:
            return empty
        backed = result.provider_backed
        evidence = result.evidence
        if evidence.requested_identifier != uen or evidence.environment.value != "MOCK":
            return (
                OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_IDENTITY_MISMATCH", None, backed
            )
        if evidence.status == "FAILED":
            return (
                OwnershipDiscoveryOutcome.PROVIDER_FAILED,
                evidence.error_code or "BUSINESS_PROFILE_PROVIDER_FAILED",
                None,
                backed,
            )
        if evidence.status == "EMPTY":
            return (
                OwnershipDiscoveryOutcome.NOT_FOUND, OFFICIAL_BUSINESS_PROFILE_EMPTY, None, backed
            )
        try:
            capital = {
                name: tuple(
                    OfficialShareCapitalObservation(
                        share_type=line.share_type,
                        currency=line.currency,
                        number_of_shares=line.number_of_shares,
                        amount=line.amount,
                    )
                    for line in lines
                )
                for name, lines in (
                    ("issued", evidence.issued_share_capital),
                    ("paid_up", evidence.paid_up_capital),
                )
            }

            def rows(assumed: bool) -> tuple[OfficialBusinessProfileShareholder, ...]:
                return tuple(
                    OfficialBusinessProfileShareholder(
                        source_party_id=item.party_id,
                        display_name=item.name,
                        party_type=PartyType(item.party_type.value),
                        source_category=item.source_category,
                        provider_status=item.source_status,
                        number_of_shares=item.number_of_shares,
                        share_type=item.share_type,
                        currency=item.currency,
                        assumed_current=assumed,
                    )
                    for item in evidence.shareholders
                )

            def observation(assumed: bool) -> OfficialBusinessProfileObservation:
                return OfficialBusinessProfileObservation(
                    entity_name=evidence.entity_name or "",
                    company_type=evidence.company_type,
                    status_of_company=evidence.status_of_company,
                    shareholders=rows(assumed),
                    issued_share_capital=capital["issued"],
                    paid_up_capital=capital["paid_up"],
                    lookup=(
                        "BUSINESS_PROFILE_FETCHED" if backed else "BUSINESS_PROFILE_CACHE_REUSED"
                    ),
                    retrieved_at=evidence.retrieved_at,
                    evidence_reference=evidence.evidence_reference,
                )

            retained = observation(False)
        except ValidationError:
            return (
                OwnershipDiscoveryOutcome.PROVIDER_INVALID,
                "BUSINESS_PROFILE_RECORD_INVALID",
                None,
                backed,
            )
        partial = OwnershipDiscoveryOutcome.PROVIDER_PARTIAL
        if not issued_capital_matches(
            retained.shareholders, retained.issued_share_capital, retained.paid_up_capital
        ):
            return partial, OFFICIAL_BUSINESS_PROFILE_RETAINED, retained, backed
        assumed = observation(True)
        try:
            component = official_issued_capital_component(
                uen,
                assumed,
                issuer_party=Party(
                    party_id=f"ENTITY_{uen}",
                    display_name=assumed.entity_name,
                    party_type=PartyType.LEGAL_ENTITY,
                    registration_number=uen,
                    country="SG",
                ),
                sourced_at=self._utc_clock(),
            )
            source = OwnershipSourceResult(
                root_party_id=component.root_party_id,
                parties=list(component.parties),
                relationships=list(component.relationships),
            )
            validate_ownership_graph(build_ownership_graph(source))
        except (ValidationError, OwnershipGraphError, ValueError, KeyError):
            return partial, OFFICIAL_BUSINESS_PROFILE_RETAINED, retained, backed
        if self._merge(node, uen, source) is not None:
            return partial, OFFICIAL_BUSINESS_PROFILE_RETAINED, retained, backed
        # The node's identity label follows its official profile; the links stay POC.
        self._parties[node] = Party.model_validate(
            {**self._parties[node].model_dump(), "display_name": assumed.entity_name}
        )
        return partial, OFFICIAL_BUSINESS_PROFILE_ISSUED_CAPITAL, assumed, backed

    def _official_shareholders(self, uen: str) -> tuple[
        OwnershipDiscoveryOutcome,
        str | None,
        tuple[OfficialShareholderObservation, ...],
        OfficialShareholderLookup | None,
        bool,
    ]:
        """D-079: keep a NOT_FOUND issuer's official shareholder rows beside the graph.

        Only the official Marketplace lane answers. Rows never become identity or
        official percentages; only the hybrid lane may derive labelled POC links from
        them (D-081, `_attach_poc_distribution`). Any failure stops safely with nothing
        retained. The read belongs to the same issuer lookup.
        """
        not_found = (OwnershipDiscoveryOutcome.NOT_FOUND, None, (), None, False)
        reader = getattr(self._reader, "acquire_subsidiary_shareholder_evidence", None)
        if reader is None:
            return not_found
        try:
            result: SubsidiaryShareholderEvidence | None = reader(
                uen,
                case_policy=self._parent.policy_snapshot.registry,
                policy_version=self._parent.policy_snapshot.catalogue_version,
                cancelled=lambda: self._clock() >= self._deadline,
            )
        except RegistryAcquisitionBusyError:
            return (
                OwnershipDiscoveryOutcome.HARD_LIMIT, "REGISTRY_ACQUISITION_BUSY", (), None, True
            )
        except RegistryCacheError as error:
            return OwnershipDiscoveryOutcome.CACHE_FAILURE, error.code, (), None, True
        except (ConnectorError, ValueError):
            return (
                OwnershipDiscoveryOutcome.PROVIDER_FAILED, "SHAREHOLDER_PROVIDER_FAILED", (), None,
                True,
            )
        except Exception:
            return (
                OwnershipDiscoveryOutcome.PROVIDER_FAILED, "SHAREHOLDER_UNEXPECTED_FAILURE", (),
                None, True,
            )
        if result is None:
            return not_found
        backed = result.provider_backed
        evidence = result.evidence
        operation = evidence.operation_result
        if evidence.requested_identifier != uen:
            return (
                OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_IDENTITY_MISMATCH", (), None,
                backed,
            )
        if operation.status == RegistryOperationStatus.FAILED:
            code = operation.error.code if operation.error is not None else None
            return (
                OwnershipDiscoveryOutcome.PROVIDER_FAILED,
                code or "SHAREHOLDER_PROVIDER_FAILED",
                (),
                None,
                backed,
            )
        if operation.status == RegistryOperationStatus.EMPTY:
            return (
                OwnershipDiscoveryOutcome.NOT_FOUND, OFFICIAL_SHAREHOLDERS_EMPTY, (), None, backed
            )
        try:
            rows = tuple(
                OfficialShareholderObservation(
                    source_party_id=item.party_id,
                    display_name=item.name,
                    party_type=PartyType(item.party_type.value),
                    source_category=item.source_category,
                    source_status=item.source_status,
                    share_allotted=item.share_allotted,
                    share_type=item.share_type,
                    currency=item.currency,
                    current_interest=(
                        item.source_status is not None
                        and item.source_status.strip().casefold() == "active"
                    ),
                    registration_identifier=item.registration_identifier,
                    retrieved_at=item.provenance.retrieved_at,
                    evidence_reference=item.provenance.evidence_reference,
                )
                for item in evidence.ownership_parties
            )
        except ValidationError:
            return (
                OwnershipDiscoveryOutcome.PROVIDER_INVALID, "SHAREHOLDER_RECORD_INVALID", (), None,
                backed,
            )
        return (
            OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
            OFFICIAL_SHAREHOLDERS_WITHOUT_ENTITY_PROFILE,
            rows,
            "SHAREHOLDERS_FETCHED" if backed else "SHAREHOLDERS_CACHE_REUSED",
            backed,
        )

    def _attach_poc_distribution(
        self, node: str, uen: str, rows: tuple[OfficialShareholderObservation, ...]
    ) -> bool:
        """D-081: attach the retained rows as POC equal-unit links in the hybrid lane.

        Only this issuer's own current rows form its denominator. Any row set that cannot
        support the convention, or a graph merge refusal, attaches nothing and leaves the
        D-079 retained-evidence outcome in place.
        """
        try:
            component = official_equal_unit_component(
                uen,
                rows,
                issuer_party=Party(
                    party_id=f"ENTITY_{uen}",
                    display_name=self._parties[node].display_name,
                    party_type=PartyType.LEGAL_ENTITY,
                    registration_number=uen,
                    country="SG",
                ),
                sourced_at=self._utc_clock(),
            )
            source = OwnershipSourceResult(
                root_party_id=component.root_party_id,
                parties=list(component.parties),
                relationships=list(component.relationships),
            )
            validate_ownership_graph(build_ownership_graph(source))
        except (ValidationError, OwnershipGraphError, ValueError, KeyError):
            return False
        return self._merge(node, uen, source) is None

    def _classify(
        self, uen: str, bundle: RegistryAcquisitionBundle | None
    ) -> tuple[OwnershipDiscoveryOutcome | None, str | None]:
        if bundle is None:
            return OwnershipDiscoveryOutcome.NOT_FOUND, None
        if (
            bundle.requested_identifier.strip().upper() != uen
            or bundle.entity_profile.registration_number.strip().upper() != uen
        ):
            return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_IDENTITY_MISMATCH"
        if bundle.entity_profile.source.environment != SourceEnvironment.MOCK:
            return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "PROVIDER_ENVIRONMENT_MISMATCH"
        if bundle.status == RegistryAcquisitionStatus.FAILED:
            return OwnershipDiscoveryOutcome.PROVIDER_FAILED, (
                bundle.issues[0].code if bundle.issues else None
            )
        # D-112: EMPTY operations are definitive provider answers, not failures. A
        # PARTIAL bundle whose shareholder collection is complete and that has no failed,
        # skipped or unsupported operation is judged on its evidence like any issuer.
        definitive = self._overlay is None and ownership_collection_complete(bundle) and all(
            item.status in {RegistryOperationStatus.COMPLETE, RegistryOperationStatus.EMPTY}
            for item in bundle.operation_results
        )
        if bundle.status != RegistryAcquisitionStatus.COMPLETE and not definitive:
            unsupported = any(
                item.operation
                in {RegistryOperation.OWNERSHIP_PARTIES, RegistryOperation.RELATIONSHIPS}
                and item.status == RegistryOperationStatus.UNSUPPORTED
                for item in bundle.operation_results
            )
            return (
                OwnershipDiscoveryOutcome.PROVIDER_UNSUPPORTED
                if unsupported
                else OwnershipDiscoveryOutcome.PROVIDER_PARTIAL
            ), None
        if classify_registry_legal_form(bundle.entity_profile.party_type) != (
            RegistryLegalForm.COMPANY
        ):
            return OwnershipDiscoveryOutcome.UNSUPPORTED_LEGAL_FORM, None
        return None, None

    def _attach(
        self,
        node: str,
        uen: str,
        evidence: SubsidiaryRegistryEvidence,
        provider_backed: bool,
    ) -> tuple[OwnershipDiscoveryOutcome, str | None]:
        bundle = evidence.acquisition
        if bundle is None:
            return OwnershipDiscoveryOutcome.NOT_FOUND, None
        try:
            issuer = acquisition_ownership_source(
                bundle,
                root_display_name=self._parties[node].display_name,
                root_registration_number=uen,
                evidence_version=max(1, len(self._parent.events)),
            )
            if self._overlay is None:
                # D-112: the same official Mock equal-unit rule as the root, per issuer;
                # no other provider or environment ever qualifies (O1, O6).
                issuer = quantify_poc_equal_units(
                    issuer, collection_complete=ownership_collection_complete(bundle)
                )
                if not issuer.relationships and any(
                    item.kind == "SHARE_UNITS" for item in issuer.evidence
                ):
                    # Precise evidence outcomes, never an invalid-record label (O2, 7).
                    return OwnershipDiscoveryOutcome.PROVIDER_PARTIAL, (
                        "ISSUER_SHARE_CLASSES_MIXED"
                        if poc_mixed_share_classes(issuer.evidence)
                        else "ISSUER_UNITS_NOT_QUANTIFIED"
                    )
            validate_ownership_graph(build_ownership_graph(issuer))
        except (ValidationError, OwnershipGraphError, ValueError, KeyError):
            return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_RECORD_INVALID"
        # Officer roles are descriptive issuer evidence, not quantitative ownership.
        # Ownership-like roles would need review, so that issuer is not attached.
        if any(
            item.kind == "ROLE"
            and item.raw_value.strip().upper() in {"OWNER", "PARTNER", "MEMBER", "SHAREHOLDER"}
            for item in issuer.evidence
        ):
            return OwnershipDiscoveryOutcome.PROVIDER_PARTIAL, "UNRESOLVED_ROLE_EVIDENCE"
        failure = self._merge(node, uen, issuer)
        if failure is not None:
            return failure
        return (
            OwnershipDiscoveryOutcome.FETCHED
            if provider_backed
            else OwnershipDiscoveryOutcome.CACHE_HIT
        ), None

    def _attach_overlay(
        self,
        node: str,
        uen: str,
        evidence: SubsidiaryRegistryEvidence,
        issuer: OverlayIssuer,
    ) -> tuple[OwnershipDiscoveryOutcome, str | None, _OverlayIdentity | None]:
        """Attach declared direct holders after a definitive official entity lookup.

        Provider failure, identity/lane mismatch or official quantitative evidence never
        selects the overlay: the branch stays unresolved rather than locally overridden.
        """
        assert self._overlay is not None
        bundle = evidence.acquisition
        if bundle is None:
            identity = _OverlayIdentity(
                "LOCAL_SYNTHETIC_IDENTITY",
                "NOT_FOUND_CACHE_REUSED" if evidence.negative_cache_hit else "NOT_FOUND",
                None,
            )
            name = issuer.local_display_name
        else:
            if (
                bundle.requested_identifier.strip().upper() != uen
                or bundle.entity_profile.registration_number.strip().upper() != uen
            ):
                return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_IDENTITY_MISMATCH", None
            if (
                bundle.entity_profile.source.environment != SourceEnvironment.MOCK
                or bundle.entity_profile.source.registry_source_link
                != OFFICIAL_MARKETPLACE_PROFILE_REFERENCE
            ):
                return (
                    OwnershipDiscoveryOutcome.PROVIDER_INVALID,
                    "OVERLAY_REQUIRES_OFFICIAL_LOOKUP",
                    None,
                )
            if (
                bundle.status == RegistryAcquisitionStatus.FAILED
                or bundle.operation_results[0].status != RegistryOperationStatus.COMPLETE
                or any(
                    item.status == RegistryOperationStatus.FAILED
                    for item in bundle.operation_results
                )
            ):
                return (
                    OwnershipDiscoveryOutcome.PROVIDER_FAILED,
                    bundle.issues[0].code if bundle.issues else None,
                    None,
                )
            if bundle.ownership_parties or bundle.relationships:
                # Official quantity is retained in its own snapshot, never overridden.
                return (
                    OwnershipDiscoveryOutcome.PROVIDER_PARTIAL,
                    "OFFICIAL_QUANTITY_PRECLUDES_OVERLAY",
                    None,
                )
            # D-086 fail closed (owner decision): the issuer's official OFFICERS roles are
            # kept beside the graph (role and status only, never identities or holdings)
            # so POC eligibility evaluates them instead of silently dropping them.
            try:
                roles = tuple(
                    OfficialOfficerRoleObservation(
                        role=officer.role,
                        status="CEASED" if officer.cessation_date is not None else "CURRENT",
                        source_operation=officer.provenance.operation.value,
                        retrieved_at=officer.provenance.retrieved_at,
                    )
                    for officer in bundle.officers
                )
            except ValidationError:
                return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_RECORD_INVALID", None
            identity = _OverlayIdentity(
                "OFFICIAL_MOCK_ENTITY_PROFILE",
                "ENTITY_PROFILE_CACHE_REUSED"
                if evidence.entity_profile_reused
                else "ENTITY_PROFILE_FETCHED",
                classify_registry_legal_form(bundle.entity_profile.party_type),
                roles,
            )
            name = bundle.entity_profile.legal_name or self._parties[node].display_name
        # The node's identity name follows its identity source; links stay local.
        renamed = Party.model_validate({**self._parties[node].model_dump(), "display_name": name})
        component = overlay_component(
            self._overlay,
            issuer,
            issuer_party=Party(
                party_id=f"ENTITY_{uen}",
                display_name=name,
                party_type=PartyType.LEGAL_ENTITY,
                registration_number=uen,
                country="SG",
            ),
            sourced_at=self._utc_clock(),
        )
        try:
            source = OwnershipSourceResult(
                root_party_id=component.root_party_id,
                parties=list(component.parties),
                relationships=list(component.relationships),
            )
            validate_ownership_graph(build_ownership_graph(source))
        except (ValidationError, OwnershipGraphError, ValueError, KeyError):
            return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "OVERLAY_RECORD_INVALID", None
        failure = self._merge(node, uen, source)
        if failure is not None:
            return (*failure, None)
        self._parties[node] = renamed
        return OwnershipDiscoveryOutcome.LOCAL_SYNTHETIC_OVERLAY, None, identity

    def _merge(
        self, node: str, uen: str, issuer: OwnershipSourceResult
    ) -> tuple[OwnershipDiscoveryOutcome, str] | None:
        """Attach one issuer record's direct holders under issuer-scoped identifiers."""
        mapping = {issuer.root_party_id: node}
        new_parties: list[Party] = []
        new_issuers: dict[str, str] = {}
        new_people: dict[str, str] = {}
        new_sources: dict[str, tuple[str, str]] = {}
        for party in issuer.parties:
            if party.party_id == issuer.root_party_id:
                continue
            owner_uen = _verified_uen(party)
            known = None if owner_uen is None else self._issuer_nodes.get(owner_uen)
            if known is None and owner_uen is not None:
                known = new_issuers.get(owner_uen)
            if known is not None:
                mapping[party.party_id] = known
                continue
            person_key = (
                self._bindings.get((uen, party.party_id))
                if party.party_type == PartyType.NATURAL_PERSON
                else None
            )
            bound = None if person_key is None else (
                self._person_nodes.get(person_key) or new_people.get(person_key)
            )
            if bound is not None:
                mapping[party.party_id] = bound
                continue
            scoped = _scoped_id(uen, party.party_id)
            if scoped in self._parties or scoped in mapping.values():
                return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "SCOPED_IDENTITY_COLLISION"
            mapping[party.party_id] = scoped
            new_parties.append(Party.model_validate({**party.model_dump(), "party_id": scoped}))
            if owner_uen is not None:
                new_issuers[owner_uen] = scoped
            if person_key is not None:
                new_people[person_key] = scoped
            if party.party_type == PartyType.NATURAL_PERSON:
                new_sources[scoped] = (uen, party.party_id)
        known_relationships = {item.relationship_id for item in self._relationships}
        new_relationships: list[OwnershipRelationship] = []
        for edge in issuer.relationships:
            scoped = _scoped_id(uen, edge.relationship_id)
            parent_id, child_id = mapping[edge.parent_party_id], mapping[edge.child_party_id]
            if scoped in known_relationships or parent_id == child_id:
                return OwnershipDiscoveryOutcome.PROVIDER_INVALID, "ISSUER_RECORD_INVALID"
            new_relationships.append(
                OwnershipRelationship(
                    relationship_id=scoped,
                    parent_party_id=parent_id,
                    child_party_id=child_id,
                    ownership_percent=edge.ownership_percent,
                    relationship_type=edge.relationship_type,
                    basis=edge.basis,
                    provenance=OwnershipProvenance(
                        provider=edge.provenance.provider,
                        environment=edge.provenance.environment,
                        source_reference=(
                            f"HYBRID_OVERLAY_{scoped}"
                            if edge.provenance.provider == OVERLAY_RELATIONSHIP_PROVIDER
                            else f"POC_EQUAL_UNITS_{scoped}"
                            if edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
                            else f"POC_ISSUED_CAPITAL_{scoped}"
                            if edge.provenance.provider == POC_ISSUED_CAPITAL_PROVIDER
                            else f"ACRA_REGISTRY_{scoped}"
                        ),
                        sourced_at=edge.provenance.sourced_at,
                    ),
                )
            )
        new_evidence = [
            OwnershipEvidence.model_validate(
                {
                    **item.model_dump(),
                    "evidence_id": "e-"
                    + sha256(f"{uen}:{item.evidence_id}".encode()).hexdigest()[:48],
                    "party_id": mapping.get(item.party_id, _scoped_id(uen, item.party_id)),
                }
            )
            for item in issuer.evidence
            if item.kind != "ROLE"
        ]
        if (
            len(self._parties) + len(new_parties) > self._limits.max_parties
            or len(self._relationships) + len(new_relationships)
            > self._limits.max_relationships
            or len(self._evidence) + len(new_evidence) > TECHNICAL_MAX_EVIDENCE
        ):
            return OwnershipDiscoveryOutcome.HARD_LIMIT, "GRAPH_SIZE_LIMIT"
        for party in new_parties:
            self._parties[party.party_id] = party
        self._relationships.extend(new_relationships)
        self._evidence.extend(new_evidence)
        self._issuer_nodes.update(new_issuers)
        self._person_nodes.update(new_people)
        for scoped, (issuer_uen, source_id) in new_sources.items():
            self._register_person(scoped, issuer_uen, source_id)
        return None

    def _register_person(self, node: str, issuer_uen: str, source_id: str) -> None:
        self._person_sources[node] = (issuer_uen, source_id)
        key = self._bindings.get((issuer_uen, source_id))
        if key is not None:
            self._person_nodes.setdefault(key, node)

    def _ambiguous_persons(self) -> tuple[str, ...]:
        """Distinct person nodes sharing a source identifier across issuer records."""
        groups: dict[str, set[str]] = {}
        for node, (_, source_id) in self._person_sources.items():
            if node in self._parties:
                groups.setdefault(source_id.strip().upper(), set()).add(node)
        return tuple(
            sorted(node for nodes in groups.values() if len(nodes) > 1 for node in nodes)
        )

    def _bound(
        self, graph: OwnershipGraph, calculation: PathCalculation
    ) -> tuple[bool, bool, Decimal]:
        """Sound global bound over every unresolved corporate branch, or invalid.

        Assumes each unresolved issuer's own holders total at most 100%. Cycles,
        traversal limits, over-allocated resolved issuers or unresolved person identity
        invalidate the bound instead of permitting a deferral.
        """
        valid = not any(item.code in _BOUND_INVALIDATING_ISSUES for item in calculation.issues)
        for edges in graph.adjacency.values():
            if sum((edge.ownership_percent for edge in edges), Decimal("0")) > Decimal("100"):
                valid = False
        if self._ambiguous_persons():
            valid = False
        upper = sum(
            (
                share
                for party_id, share in calculation.unresolved_entity_shares.items()
                if party_id != self._root
            ),
            Decimal("0"),
        )
        try:
            totals = aggregate_ownership_paths(calculation)
        except OwnershipGraphError:
            return False, True, upper
        if upper > Decimal("100"):
            return False, True, upper
        could_change = upper >= self._ubo or any(
            total < self._ubo <= total + upper for _, _, total in totals.values()
        )
        return valid, could_change, upper

    def _finalize(
        self,
        node: str,
        outcome: OwnershipDiscoveryOutcome,
        depth: int,
        shares: dict[str, Decimal],
        reason: str | None = None,
        identity: _OverlayIdentity | None = None,
        shareholders: tuple[OfficialShareholderObservation, ...] = (),
        shareholder_lookup: OfficialShareholderLookup | None = None,
        business_profile: OfficialBusinessProfileObservation | None = None,
    ) -> None:
        party = self._parties[node]
        share = shares.get(node)
        self._records[node] = OwnershipDiscoveryRecord(
            party_id=node,
            display_name=party.display_name,
            registration_number=party.registration_number,
            depth=min(depth, 64),
            outcome=outcome,
            max_effective_percent=share if share is not None and share <= 100 else None,
            reason_code=reason,
            identity_basis=identity.identity_basis if identity is not None else None,
            official_entity_lookup=(
                identity.official_entity_lookup if identity is not None else None
            ),
            official_legal_form=identity.official_legal_form if identity is not None else None,
            official_officer_roles=identity.officer_roles if identity is not None else (),
            official_shareholders=shareholders,
            official_shareholder_lookup=shareholder_lookup,
            official_business_profile=business_profile,
        )

    def _uen(self, node: str) -> str:
        return _verified_uen(self._parties[node]) or ""


def _single_current_class(rows: tuple[OfficialShareholderObservation, ...]) -> bool:
    """D-112 (O2): every current row reports the same, non-empty class and currency."""

    labels = {
        (
            (row.share_type or "").strip().upper(),
            (row.currency or "").strip().upper(),
        )
        for row in rows
        if row.current_interest
    }
    return len(labels) == 1 and all(part for part in next(iter(labels)))


def _verified_uen(party: Party) -> str | None:
    if party.party_type != PartyType.LEGAL_ENTITY or party.registration_number is None:
        return None
    candidate = party.registration_number.strip().upper()
    return candidate if is_eligible_singapore_uen(candidate) else None


def _depths(graph: OwnershipGraph) -> dict[str, int]:
    """Minimum edge count from the root; unreachable parties are omitted."""
    depths = {graph.root_party_id: 0}
    queue = deque([graph.root_party_id])
    while queue:
        current = queue.popleft()
        for edge in graph.adjacency.get(current, ()):
            if edge.child_party_id not in depths:
                depths[edge.child_party_id] = depths[current] + 1
                queue.append(edge.child_party_id)
    return depths


def _scoped_id(issuer_uen: str, source_id: str) -> str:
    """Deterministic issuer-namespaced identifier; hashed when too long or unsafe."""
    candidate = f"{issuer_uen}.{source_id}"
    if _SAFE_SCOPED_ID.fullmatch(candidate):
        return candidate
    digest = sha256(f"{issuer_uen}\x00{source_id}".encode()).hexdigest()[:40]
    return f"{issuer_uen}.h{digest}"
