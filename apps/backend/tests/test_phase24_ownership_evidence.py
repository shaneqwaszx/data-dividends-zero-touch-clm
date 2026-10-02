"""Synthetic source-neutral evidence; never captured provider data."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_zero_touch_orchestration import build_system

from app.connectors.ownership import OwnershipProviderMetadata, OwnershipSourceResult
from app.domain.access import TeamId
from app.domain.ownership import OwnershipProvenance, OwnershipRelationship, Party
from app.domain.ownership_evidence import OwnershipEvidence, OwnershipEvidenceKind
from app.domain.registry_legal_form import classify_registry_legal_form
from app.services.ownership_analysis import percentage_from_units, quantify_ownership_evidence
from app.services.ownership_evidence_tagger import OwnershipEvidenceTagger


def evidence(**changes: object) -> OwnershipEvidence:
    data = dict(
        evidence_id="units-a",
        entity_identifier="202400001A",
        party_id="PERSON_A",
        kind="SHARE_UNITS",
        raw_value="6000",
        numeric_value="6000",
        source_operation="SYNTHETIC_UNITS",
        provider="SYNTHETIC",
        environment="MOCK",
        retrieved_at=datetime(2026, 10, 1, tzinfo=UTC),
        evidence_version=1,
        as_of=datetime(2026, 10, 1, tzinfo=UTC),
        share_class="ORDINARY",
        unit_type="SHARES",
        authoritative=False,
    )
    data.update(changes)
    return OwnershipEvidence.model_validate(data)


def denominator(**changes: object) -> OwnershipEvidence:
    data = dict(
        evidence_id="total-a",
        kind="CAPITAL_DENOMINATOR",
        raw_value="10000",
        numeric_value="10000",
        authoritative=True,
    )
    data.update(changes)
    return evidence(**data)


def test_decimal_units_and_threshold_equality() -> None:
    assert percentage_from_units(evidence(), denominator()) == Decimal("60")
    assert percentage_from_units(
        evidence(numeric_value="2500", raw_value="2500"), denominator()
    ) == Decimal("25")


@pytest.mark.parametrize(
    "changes",
    [
        {"entity_identifier": "202400002B"},
        {"share_class": "PREFERENCE"},
        {"unit_type": "CURRENCY"},
        {"authoritative": False},
        {"share_class": None},
        {"numeric_value": "0", "raw_value": "0"},
    ],
)
def test_incompatible_denominator_never_produces_percentage(changes: dict[str, object]) -> None:
    assert percentage_from_units(evidence(), denominator(**changes)) is None


def test_no_row_sum_or_missing_denominator_inference() -> None:
    assert percentage_from_units(evidence(), None) is None
    assert percentage_from_units(evidence(share_class=None), denominator()) is None


@pytest.mark.parametrize("value", [True, 0.1, "NaN", "Infinity", "-1"])
def test_malformed_numeric_evidence_is_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        evidence(numeric_value=value)


@pytest.mark.parametrize(
    "role,tag",
    [
        ("OWNER", "OWNER_ROLE"),
        ("PARTNER", "PARTNER_ROLE"),
        ("MEMBER", "MEMBER_ROLE"),
        ("SHAREHOLDER", "DIRECT_ECONOMIC_INTEREST"),
        ("DIRECTOR", "UNKNOWN"),
        ("OFFICER", "UNKNOWN"),
        ("UNKNOWN", "UNKNOWN"),
    ],
)
def test_semantic_rules_do_not_turn_officers_into_owners(role: str, tag: str) -> None:
    item = evidence(kind=OwnershipEvidenceKind.ROLE, raw_value=role, numeric_value=None)
    result = OwnershipEvidenceTagger().tag((item,), case_version=3)
    assert result.runtime_status == "ML_RUNTIME_NOT_AVAILABLE"
    assert result.method == "DETERMINISTIC_RULES"
    assert result.tags[0].tag == tag
    assert result.tags[0].evidence_ids == (item.evidence_id,)
    assert result.tags[0].case_version == 3
    assert result.tags[0].evidence_version == 1
    assert result.tags[0].rule_version
    assert result.tags[0].reason_code
    assert Decimal("0") <= result.tags[0].confidence <= Decimal("1")


def test_share_and_capital_tags_preserve_source_references() -> None:
    result = OwnershipEvidenceTagger().tag((evidence(), denominator()), case_version=2)
    assert [item.tag for item in result.tags] == [
        "SHARE_UNIT_EVIDENCE",
        "CAPITAL_DENOMINATOR_EVIDENCE",
    ]


def source(items: tuple[OwnershipEvidence, ...]) -> OwnershipSourceResult:
    return OwnershipSourceResult(
        root_party_id="ROOT",
        parties=[
            Party(
                party_id="ROOT",
                display_name="Synthetic root",
                party_type="LEGAL_ENTITY",
                registration_number="202400001A",
            ),
            Party(party_id="PERSON_A", display_name="Synthetic A", party_type="NATURAL_PERSON"),
            Party(party_id="PERSON_B", display_name="Synthetic B", party_type="NATURAL_PERSON"),
        ],
        evidence=items,
    )


def test_units_create_exact_edges_only_with_authoritative_compatible_denominator() -> None:
    result = quantify_ownership_evidence(
        source(
            (
                evidence(),
                evidence(
                    evidence_id="units-b",
                    party_id="PERSON_B",
                    raw_value="4000",
                    numeric_value="4000",
                ),
                denominator(),
            )
        )
    )
    assert [item.ownership_percent for item in result.relationships] == [
        Decimal("60"),
        Decimal("40"),
    ]
    assert result.evidence[0].raw_value == "6000"
    assert result.evidence[1].raw_value == "4000"
    assert sum(item.ownership_percent for item in result.relationships) == Decimal("100")


@pytest.mark.parametrize(
    "items",
    [
        (evidence(),),
        (evidence(), denominator(authoritative=False)),
        (evidence(), denominator(as_of=None)),
        (evidence(), denominator(source_status="WITHDRAWN")),
        (evidence(), denominator(evidence_id="total-b"), denominator()),
        (evidence(), evidence(evidence_id="duplicate-units"), denominator()),
        (
            evidence(),
            evidence(evidence_id="other-class", party_id="PERSON_B", share_class="PREFERENCE"),
            denominator(),
        ),
        (
            evidence(),
            evidence(
                evidence_id="conflict", kind="CONFLICT", raw_value="CONFLICT", numeric_value=None
            ),
            denominator(),
        ),
    ],
)
def test_missing_conflicting_or_multiclass_evidence_never_becomes_edges(
    items: tuple[OwnershipEvidence, ...],
) -> None:
    assert quantify_ownership_evidence(source(items)).relationships == []


def test_provider_percentage_requires_explicit_basis_and_no_status_assumption() -> None:
    item = evidence(kind="DIRECT_PERCENTAGE", raw_value="25", numeric_value="25")
    assert not quantify_ownership_evidence(source((item,))).relationships
    supplied = item.model_copy(update={"determination_basis": "PROVIDER_PERCENTAGE"})
    assert quantify_ownership_evidence(source((supplied,))).relationships[0].ownership_percent == 25
    assert not quantify_ownership_evidence(
        source((supplied.model_copy(update={"source_status": "WITHDRAWN"}),))
    ).relationships


def test_no_precision_rounding_or_cross_provider_synthesis() -> None:
    assert (
        percentage_from_units(
            evidence(raw_value="1", numeric_value="1"),
            denominator(raw_value="3", numeric_value="3"),
        )
        is None
    )
    assert percentage_from_units(evidence(), denominator(provider="OTHER_PROVIDER")) is None
    with pytest.raises(ValidationError):
        evidence(raw_value="500", numeric_value="6000")


@pytest.mark.parametrize(
    "kind,tag",
    [
        ("DIRECT_PERCENTAGE", "DIRECT_ECONOMIC_INTEREST"),
        ("ECONOMIC_INTEREST", "DIRECT_ECONOMIC_INTEREST"),
        ("MEMBERSHIP_INTEREST", "DIRECT_ECONOMIC_INTEREST"),
        ("CONTROL", "CONTROL_EVIDENCE"),
        ("CONFLICT", "CONFLICTING_EVIDENCE"),
        ("GROUP_SHAREHOLDER", "UNKNOWN"),
        ("UNKNOWN", "UNKNOWN"),
    ],
)
def test_remaining_semantic_fixture_rules_are_exact(kind: str, tag: str) -> None:
    result = OwnershipEvidenceTagger().tag((evidence(kind=kind),), case_version=5)
    assert result.tags[0].tag == tag
    assert result.tags[0].provider == "SYNTHETIC"
    assert result.tags[0].environment == "MOCK"
    assert result.tags[0].reason_code


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("PRIVATE_COMPANY_LIMITED_BY_SHARES", "COMPANY"),
        ("PARTNERSHIP", "BUSINESS_PARTNERSHIP"),
        ("BUSINESS", "BUSINESS_PARTNERSHIP"),
        ("LLP", "LLP"),
        ("LP", "LP"),
        ("unrecognized form", "OTHER"),
    ],
)
def test_legal_form_is_bounded_and_unknown_forms_fail_closed(raw: str, expected: str) -> None:
    assert classify_registry_legal_form(raw) == expected


class EvidenceOnlyProvider:
    def __init__(self, items: tuple[OwnershipEvidence, ...]) -> None:
        self.items = items

    @property
    def metadata(self) -> object:
        return OwnershipProviderMetadata(provider_name="SYNTHETIC", environment="MOCK")

    def load(self, request: object) -> object:
        return source(self.items)


def test_existing_engine_calculates_candidates_and_keeps_original_scalar_evidence() -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    items = (
        evidence(),
        evidence(
            evidence_id="units-b", party_id="PERSON_B", raw_value="4000", numeric_value="4000"
        ),
        denominator(),
    )
    zero._ownership.load(case_id=record.case_id, provider=EvidenceOnlyProvider(items))
    analyzed = zero._ownership.analyze(case_id=record.case_id)
    assert analyzed.state == "ANALYZED"
    assert analyzed.threshold_percent == Decimal("25")
    assert sorted(candidate.aggregated_ownership_percent for candidate in analyzed.candidates) == [
        Decimal("40"),
        Decimal("60"),
    ]
    assert all(
        candidate.classification == "PROVISIONAL_UBO_CANDIDATE" for candidate in analyzed.candidates
    )
    assert analyzed.evidence == items
    assert analyzed.tagging.runtime_status == "ML_RUNTIME_NOT_AVAILABLE"
    assert all(tag.evidence_version == 1 for tag in analyzed.tagging.tags)


def test_unquantified_units_have_a_specific_review_outcome_in_the_same_engine() -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    zero._ownership.load(case_id=record.case_id, provider=EvidenceOnlyProvider((evidence(),)))
    analyzed = zero._ownership.analyze(case_id=record.case_id)
    assert analyzed.state == "REVIEW_REQUIRED"
    assert analyzed.candidates == []
    assert {issue.code.value for issue in analyzed.issues} == {
        "INCOMPLETE_LEGAL_ENTITY", "OWNERSHIP_DENOMINATOR_REQUIRED"
    }
    assert analyzed.evidence[0].raw_value == "6000"


@pytest.mark.parametrize("conflict", [False, True])
def test_scalar_review_issues_make_retained_candidates_indeterminate(conflict: bool) -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    direct = evidence(kind="DIRECT_PERCENTAGE", raw_value="60", numeric_value="60",
                      determination_basis="PROVIDER_PERCENTAGE")
    unresolved = evidence(evidence_id="unresolved", party_id="PERSON_B",
                          kind="CONFLICT" if conflict else "SHARE_UNITS",
                          raw_value="CONFLICT" if conflict else "4000",
                          numeric_value=None if conflict else "4000")
    if conflict:
        class MixedProvider(EvidenceOnlyProvider):
            def load(self, request: object) -> object:
                return quantify_ownership_evidence(source((direct,))).model_copy(
                    update={"evidence": (direct, unresolved)}, deep=True
                )
        provider = MixedProvider((direct, unresolved))
    else:
        provider = EvidenceOnlyProvider((direct, unresolved))
    zero._ownership.load(case_id=record.case_id, provider=provider)
    analyzed = zero._ownership.analyze(case_id=record.case_id)
    assert analyzed.state == "REVIEW_REQUIRED"
    assert analyzed.candidates
    assert all(candidate.classification == "REVIEW_REQUIRED" and
               candidate.threshold_result == "INDETERMINATE" for candidate in analyzed.candidates)
    assert analyzed.candidates[0].aggregated_ownership_percent == Decimal("60")


def test_graph_and_scalar_diagnostics_are_both_retained() -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    record = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    provenance = OwnershipProvenance(provider="SYNTHETIC", environment="MOCK",
                                    source_reference="SYNTHETIC", sourced_at=datetime.now(UTC))
    raw = source((evidence(kind="CONFLICT", raw_value="CONFLICT", numeric_value=None),))
    holding = Party(party_id="HOLDING", display_name="Synthetic holding", party_type="LEGAL_ENTITY",
                    registration_number="202400009I")
    raw = raw.model_copy(update={"parties": [*raw.parties, holding], "relationships": [
        OwnershipRelationship(relationship_id="root-a", parent_party_id="ROOT",
                              child_party_id="PERSON_A", ownership_percent="60",
                              provenance=provenance),
        OwnershipRelationship(relationship_id="root-holding", parent_party_id="ROOT",
                              child_party_id="HOLDING", ownership_percent="40",
                              provenance=provenance),
        OwnershipRelationship(relationship_id="holding-b", parent_party_id="HOLDING",
                              child_party_id="PERSON_B", ownership_percent="100",
                              provenance=provenance),
    ]}, deep=True)

    class GraphProvider(EvidenceOnlyProvider):
        def load(self, request: object) -> object:
            return raw

    zero._ownership.max_depth = 1
    zero._ownership.load(case_id=record.case_id, provider=GraphProvider(raw.evidence))
    analyzed = zero._ownership.analyze(case_id=record.case_id)
    assert {issue.code.value for issue in analyzed.issues} == {
        "MAXIMUM_DEPTH_EXCEEDED", "UBO_REVIEW_REQUIRED"
    }
    assert all(candidate.threshold_result == "INDETERMINATE" for candidate in analyzed.candidates)


@pytest.mark.parametrize(("kind", "raw"), [
    ("GROUP_SHAREHOLDER", "UNKNOWN"), ("UNKNOWN", "UNKNOWN"),
    ("CONTROL", "UNCONFIRMED"), ("MEMBERSHIP_INTEREST", "UNQUANTIFIED"),
    ("ECONOMIC_INTEREST", "UNQUANTIFIED"), ("ROLE", "OWNER"),
    ("ROLE", "PARTNER"), ("ROLE", "MEMBER"), ("ROLE", "SHAREHOLDER"),
])
def test_valid_graph_cannot_hide_unresolved_semantic_interest(kind: str, raw: str) -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    case = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    direct = evidence(kind="DIRECT_PERCENTAGE", raw_value="60", numeric_value="60",
                      determination_basis="PROVIDER_PERCENTAGE")
    unresolved = evidence(evidence_id="unresolved", party_id="PERSON_B",
                          kind=kind, raw_value=raw, numeric_value=None)

    class MixedProvider(EvidenceOnlyProvider):
        def load(self, request: object) -> object:
            return quantify_ownership_evidence(source((direct,))).model_copy(
                update={"evidence": (direct, unresolved)}, deep=True
            )

    zero._ownership.load(case_id=case.case_id, provider=MixedProvider((direct, unresolved)))
    result = zero._ownership.analyze(case_id=case.case_id)
    assert result.state == "REVIEW_REQUIRED"
    assert "UBO_REVIEW_REQUIRED" in {issue.code.value for issue in result.issues}
    assert result.evidence == (direct, unresolved)
    assert result.candidates[0].aggregated_ownership_percent == Decimal("60")
    assert all(item.threshold_result == "INDETERMINATE"
               and item.classification == "REVIEW_REQUIRED" for item in result.candidates)


@pytest.mark.parametrize(("kind", "status"), [
    ("DIRECT_PERCENTAGE", "UNKNOWN"), ("DIRECT_PERCENTAGE", "WITHDRAWN"),
    ("DIRECT_PERCENTAGE", "ACTIVE"), ("SHARE_UNITS", "UNKNOWN"),
    ("SHARE_UNITS", "WITHDRAWN"),
])
def test_existing_percentage_does_not_resolve_unsupported_scalar_activity(kind, status) -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    case = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    direct = evidence(kind="DIRECT_PERCENTAGE", raw_value="60", numeric_value="60",
                      determination_basis="PROVIDER_PERCENTAGE")
    uncertain = (direct.model_copy(update={"source_status": status})
                 if kind == "DIRECT_PERCENTAGE" else evidence(kind=kind, source_status=status))

    class ActivityProvider(EvidenceOnlyProvider):
        def load(self, request: object) -> object:
            return quantify_ownership_evidence(source((direct,))).model_copy(
                update={"evidence": (uncertain,)}, deep=True
            )

    zero._ownership.load(case_id=case.case_id, provider=ActivityProvider((uncertain,)))
    result = zero._ownership.analyze(case_id=case.case_id)
    assert result.state == "REVIEW_REQUIRED"
    assert result.evidence[0].source_status == status
    assert result.candidates[0].aggregated_ownership_percent == Decimal("60")
    assert all(item.threshold_result == "INDETERMINATE" for item in result.candidates)


def test_officer_only_labels_do_not_invalidate_an_independently_valid_graph() -> None:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    case = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    direct = evidence(kind="DIRECT_PERCENTAGE", raw_value="60", numeric_value="60",
                      determination_basis="PROVIDER_PERCENTAGE")
    officer = evidence(evidence_id="officer", party_id="PERSON_B",
                       kind="ROLE", raw_value="DIRECTOR", numeric_value=None)

    class OfficerProvider(EvidenceOnlyProvider):
        def load(self, request: object) -> object:
            return quantify_ownership_evidence(source((direct,))).model_copy(
                update={"evidence": (direct, officer)}, deep=True
            )

    zero._ownership.load(case_id=case.case_id, provider=OfficerProvider((direct, officer)))
    result = zero._ownership.analyze(case_id=case.case_id)
    assert result.state == "ANALYZED"
    assert len(result.candidates) == 1
    assert result.candidates[0].party.party_id == "PERSON_A"
    assert result.tagging.tags[-1].tag == "UNKNOWN"


def test_nested_registry_percentages_keep_actual_owned_entity_bindings() -> None:
    from app.composition import build_onboarding_service
    from app.config import Settings
    from app.connectors.ownership import OwnershipProviderRequest
    from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider

    cases = build_onboarding_service(settings=Settings(_env_file=None))
    case = cases.create_case("11111999A")
    result = RegistryAcquisitionOwnershipProvider(cases).load(OwnershipProviderRequest(
        case_id=case.case_id, registration_number="11111999A", display_name="Synthetic"
    ))
    parties = {party.party_id: party for party in result.parties}
    nested = [edge for edge in result.relationships if edge.parent_party_id != result.root_party_id]
    assert len(nested) == 3
    for edge in result.relationships:
        assert any(item.party_id == edge.child_party_id and
                   item.numeric_value == edge.ownership_percent and
                   item.entity_identifier == parties[edge.parent_party_id].registration_number
                   for item in result.evidence if item.kind == "DIRECT_PERCENTAGE")


def test_same_numerator_and_denominator_for_another_entity_cannot_become_root_edges() -> None:
    result = quantify_ownership_evidence(source((
        evidence(entity_identifier="202400009I"), denominator(entity_identifier="202400009I")
    )))
    assert result.relationships == []


def repeated_party_registry_source(*, unknown_binding: bool = False) -> OwnershipSourceResult:
    from types import SimpleNamespace
    from uuid import uuid4

    from app.connectors.mock_acra import MockAcraConnector
    from app.connectors.ownership import OwnershipProviderRequest
    from app.connectors.registry import AcraRegistryProviderAdapter
    from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
    from app.domain.models import RegistryAcquisitionBundle, RegistryPartyType

    bundle = AcraRegistryProviderAdapter(MockAcraConnector()).retrieve_acquisition("202400001A")
    person = bundle.ownership_parties[0].model_copy(update={
        "party_id": "PERSON_A", "ownership_percentage": Decimal("60")
    })
    holding = bundle.ownership_parties[1].model_copy(update={
        "party_id": "HOLDING", "party_type": RegistryPartyType.LEGAL_ENTITY,
        "registration_identifier": None if unknown_binding else "202400009I",
        "ownership_percentage": Decimal("40"),
    })
    edge = bundle.relationships[0]
    edges = tuple(edge.model_copy(update={
        "relationship_id": key, "owned_entity_id": parent,
        "owner_party_id": child, "ownership_percentage": Decimal(percent),
    }) for key, parent, child, percent in (
        ("root-a", bundle.root_party_id, "PERSON_A", "60"),
        ("root-holding", bundle.root_party_id, "HOLDING", "40"),
        ("holding-a", "HOLDING", "PERSON_A", "100"),
    ))
    bundle = bundle.model_copy(update={
        "ownership_parties": (person, holding), "relationships": edges,
        "operation_results": tuple(result.model_copy(update={"record_count": 3})
                                   if result.operation == "RELATIONSHIPS" else result
                                   for result in bundle.operation_results),
    })
    bundle = RegistryAcquisitionBundle.model_validate(bundle.model_dump())

    class Cases:
        def get_case(self, case_id: object) -> object:
            return SimpleNamespace(registry_acquisition=bundle, events=[None])

    return RegistryAcquisitionOwnershipProvider(Cases()).load(OwnershipProviderRequest(
        case_id=uuid4(), registration_number="202400001A", display_name="Synthetic"
    ))


def test_repeated_party_percentages_remain_bound_to_each_owned_entity() -> None:
    result = repeated_party_registry_source()
    percentages = [item for item in result.evidence if item.party_id == "PERSON_A"]
    assert {(item.entity_identifier, item.numeric_value) for item in percentages} == {
        ("202400001A", Decimal("60")), ("202400009I", Decimal("100"))
    }
    assert len({item.evidence_id for item in percentages}) == 2
    _, zero, _, _, _ = build_system(require_confirmation=True)
    case = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)

    class RegistrySourceProvider:
        metadata = OwnershipProviderMetadata(provider_name="ACRA_REGISTRY_ACQUISITION",
                                             environment="MOCK")
        def load(self, request: object) -> object:
            return result

    zero._ownership.load(case_id=case.case_id, provider=RegistrySourceProvider())
    analyzed = zero._ownership.analyze(case_id=case.case_id)
    assert analyzed.state == "ANALYZED"
    assert analyzed.candidates[0].direct_ownership_percent == Decimal("60")
    assert analyzed.candidates[0].indirect_ownership_percent == Decimal("40")


def test_unknown_parent_binding_is_retained_without_calculation_or_tag_confidence() -> None:
    result = repeated_party_registry_source(unknown_binding=True)
    unbound = next(item for item in result.evidence if item.entity_identifier is None)
    assert unbound.raw_value == "100"
    assert unbound.numeric_value == Decimal("100")
    tag = OwnershipEvidenceTagger().tag((unbound,), case_version=1).tags[0]
    assert tag.tag == "UNKNOWN" and tag.confidence == 0
    assert tag.reason_code == "EVIDENCE_ENTITY_BINDING_UNKNOWN"
    assert percentage_from_units(evidence(entity_identifier=None),
                                 denominator(entity_identifier=None)) is None


def test_inapplicable_company_ownership_stops_dependent_relationship_acquisition() -> None:
    from app.connectors.mock_acra import MockAcraConnector
    from app.connectors.registry import AcraRegistryProviderAdapter

    class RoleOnlyConnector(MockAcraConnector):
        def fetch_ownership_parties(self, identifier: str) -> object:
            pytest.fail("company ownership must not dispatch for a partnership")
        def fetch_relationships(self, identifier: str) -> object:
            pytest.fail("relationships depend on applicable ownership evidence")

    bundle = AcraRegistryProviderAdapter(
        RoleOnlyConnector(), company_shareholders_only=True
    ).retrieve_acquisition("11111999A")
    assert bundle is not None
    assert bundle.status == "PARTIAL"
    assert [item.status.value for item in bundle.operation_results] == [
        "COMPLETE", "EMPTY", "UNSUPPORTED", "UNSUPPORTED"
    ]
    assert bundle.relationships == ()
