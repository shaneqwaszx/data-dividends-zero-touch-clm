"""D-112 through the real registry acquisition and discovery path, for any company.

Fictional issuers whose Mock registers report share units (no ACRA percentage or
denominator). The same evidence must give the same decision whatever the UEN.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from test_recursive_ownership_discovery import (
    ROOT,
    Clock,
    Issuer,
    SyntheticRegistry,
    VerifiedPersonBinding,
    codes,
    company,
    harness,
    person,
)

from app.connectors.acra import (
    AcraOwnershipPartiesPayload,
    AcraOwnershipPartyPayload,
    AcraRelationshipsPayload,
)
from app.connectors.hybrid_ownership_overlay import POC_EQUAL_UNITS_PROVIDER
from app.domain.models import RegistryOperation
from app.domain.ownership import OwnershipAnalysisRecord, OwnershipThresholdResult
from app.services.ownership_analysis import (
    EVIDENCE_POC_BASIS_ID,
    eligible_poc_acceptance,
    ownership_collection_complete,
)


class UnitsRegistry(SyntheticRegistry):
    """The holder tuple's third field is a unit count, reported with a class label."""

    def __init__(
        self,
        issuers: dict[str, Issuer],
        clock: Any,
        *,
        classes: dict[tuple[str, str], str] | None = None,
        withdrawn: frozenset[tuple[str, str]] = frozenset(),
    ) -> None:
        super().__init__(issuers, clock)
        self.classes = classes or {}
        self.withdrawn = withdrawn

    def fetch_ownership_parties(self, uen: str) -> AcraOwnershipPartiesPayload:
        self.calls[(uen, "parties")] += 1
        return AcraOwnershipPartiesPayload(
            uen=uen,
            ownership_parties=tuple(
                AcraOwnershipPartyPayload(
                    party_id=party_id,
                    party_type="LEGAL_ENTITY" if kind == "C" else "NATURAL_PERSON",
                    name=f"SYNTHETIC {party_id}",
                    registration_identifier=registration,
                    country=country,
                    share_allotted=Decimal(units),
                    share_type=self.classes.get((uen, party_id), "ORDINARY"),
                    currency="SGD",
                    source_status="Withdrawn" if (uen, party_id) in self.withdrawn else "Active",
                )
                for party_id, kind, units, registration, country in self.issuers[uen].holders
            ),
            source_environment="MOCK",
            source_endpoint=self._endpoint(uen, "/ownership-parties"),
            retrieved_at=self.clock(),
        )

    def fetch_relationships(self, uen: str) -> AcraRelationshipsPayload:
        self.calls[(uen, "relationships")] += 1
        return AcraRelationshipsPayload(
            uen=uen,
            relationships=(),
            source_environment="MOCK",
            source_endpoint=self._endpoint(uen, "/relationships"),
            retrieved_at=self.clock(),
        )


def run(issuers: dict[str, Issuer], root: str = ROOT, **options: Any) -> OwnershipAnalysisRecord:
    clock = Clock()
    bindings = options.pop("bindings", ())
    registry = UnitsRegistry(issuers, clock, **options)
    return harness(registry, clock=clock, bindings=bindings).analyze(root)


def accepted(record: OwnershipAnalysisRecord) -> Any:
    return eligible_poc_acceptance(
        record,
        scenario=None,
        accepted_at=datetime(2026, 11, 1, tzinfo=UTC),
        ownership_version=record.version,
    )


def candidate(record: OwnershipAnalysisRecord, suffix: str) -> Any:
    return next(item for item in record.candidates if item.party.party_id.endswith(suffix))


def test_600_300_100_gives_60_30_10_and_equivalent_evidence_gives_equal_results() -> None:
    results = []
    # A new UEN and the Garden and OPQ identifiers follow exactly the same generic rule.
    for uen in (ROOT, "209900077Z", "11111999A", "201511222D"):
        record = run(
            {uen: Issuer("SOME CO", (person("A", "600"), person("B", "300"), person("C", "100")))},
            root=uen,
        )
        assert sorted(
            (edge.child_party_id, edge.ownership_percent) for edge in record.relationships
        ) == [("A", Decimal("60.000000")), ("B", Decimal("30.000000")), ("C", Decimal("10.000000"))]
        assert all(e.provenance.provider == POC_EQUAL_UNITS_PROVIDER for e in record.relationships)
        assert codes(record) == {"OWNERSHIP_DENOMINATOR_REQUIRED"}
        acceptance = accepted(record)
        assert acceptance is not None and acceptance.overlay_scenario_id == EVIDENCE_POC_BASIS_ID
        results.append(
            (
                {(c.party.party_id, c.aggregated_ownership_percent) for c in record.candidates},
                {(c.party.party_id, c.synthetic_basis_threshold_result) for c in record.candidates},
                record.state,
                acceptance.accepted_assumptions,
            )
        )
    assert all(item == results[0] for item in results)


def test_indirect_80_times_50_is_40_and_a_complete_corporate_graph_proceeds() -> None:
    record = run(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "800"), person("X", "200"))),
            "300000001B": Issuer("B CO", (person("P", "500"), person("Q", "500"))),
        }
    )
    p = candidate(record, ".P")
    assert p.indirect_ownership_percent == Decimal("40")
    assert p.aggregated_ownership_percent == Decimal("40")
    assert p.synthetic_basis_threshold_result == OwnershipThresholdResult.MET
    x = candidate(record, "X")
    assert x.synthetic_basis_threshold_result == OwnershipThresholdResult.NOT_MET
    # A corporate holder is not blocked for being corporate; no demo scenario is involved.
    assert record.discovery is not None and record.discovery.graph_complete is True
    assert accepted(record) is not None


def test_direct_and_indirect_interests_of_one_bound_person_aggregate_to_threshold() -> None:
    record = run(
        {
            ROOT: Issuer(
                "ROOT CO", (person("P", "200"), company("300000001B", "500"), person("Z", "300"))
            ),
            "300000001B": Issuer("B CO", (person("P", "200"), person("W", "800"))),
        },
        bindings=(
            VerifiedPersonBinding(ROOT, "P", "VERIFIED-PERSON-9"),
            VerifiedPersonBinding("300000001B", "P", "VERIFIED-PERSON-9"),
        ),
    )
    p = next(item for item in record.candidates if item.party.party_id == "P")
    assert p.direct_ownership_percent == Decimal("20")
    assert p.indirect_ownership_percent == Decimal("10")
    assert p.aggregated_ownership_percent == Decimal("30")
    assert p.synthetic_basis_threshold_result == OwnershipThresholdResult.MET
    assert accepted(record) is not None


def test_missing_corporate_ownership_requires_review_not_acceptance() -> None:
    record = run({ROOT: Issuer("ROOT CO", (company("300000009Z", "800"), person("X", "200")))})
    assert record.state == "REVIEW_REQUIRED"
    assert record.discovery is not None and record.discovery.graph_complete is False
    assert accepted(record) is None


def test_mixed_classes_at_a_corporate_holder_keep_an_accurate_warning() -> None:
    record = run(
        {
            ROOT: Issuer("ROOT CO", (company("300000001B", "800"), person("X", "200"))),
            "300000001B": Issuer("B CO", (person("P", "500"), person("Q", "500"))),
        },
        classes={("300000001B", "Q"): "PREFERENCE"},
    )
    assert record.state == "REVIEW_REQUIRED"
    assert record.discovery is not None
    assert [(item.registration_number, item.reason_code) for item in record.discovery.records] == [
        ("300000001B", "ISSUER_SHARE_CLASSES_MIXED")
    ]
    assert "CORPORATE_OWNERSHIP_UNRESOLVED" in codes(record)
    assert accepted(record) is None
    # The root's own single-class register is still illustrated on the POC basis.
    assert any(
        edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
        and edge.parent_party_id == record.root_party_id
        for edge in record.relationships
    )


def test_withdrawn_holders_do_not_contribute_to_current_ownership() -> None:
    record = run(
        {ROOT: Issuer("ROOT CO", (person("A", "300"), person("B", "100"), person("C", "9000")))},
        withdrawn=frozenset({(ROOT, "C")}),
    )
    assert sorted((e.child_party_id, e.ownership_percent) for e in record.relationships) == [
        ("A", Decimal("75.000000")),
        ("B", Decimal("25.000000")),
    ]
    assert accepted(record) is not None


def test_an_incomplete_collection_never_qualifies_even_when_totals_reach_100() -> None:
    clock = Clock()
    registry = UnitsRegistry(
        {ROOT: Issuer("ROOT CO", (person("A", "600"), person("B", "400")))}, clock
    )
    system = harness(registry, clock=clock)
    case = system.onboarding.create_staged_case(ROOT)
    acquisition = system.onboarding.get_case(case.case_id).registry_acquisition
    assert ownership_collection_complete(acquisition)
    truncated = acquisition.model_copy(
        update={
            "operation_results": tuple(
                item.model_copy(update={"record_count": item.record_count + 1})
                if item.operation == RegistryOperation.OWNERSHIP_PARTIES
                else item
                for item in acquisition.operation_results
            )
        }
    )
    # The returned rows alone would total 100%, but the provider reported more rows.
    assert not ownership_collection_complete(truncated)
    assert not ownership_collection_complete(None)
