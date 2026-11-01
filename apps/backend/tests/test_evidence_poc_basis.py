"""Owner O1-O8 (2026-11-01): the code-level evidence POC basis for any company.

Synthetic, source-neutral evidence only; never captured provider data.
"""

from datetime import UTC, datetime
from decimal import Decimal

from test_zero_touch_orchestration import build_system

from app.connectors.hybrid_ownership_overlay import POC_EQUAL_UNITS_PROVIDER
from app.connectors.ownership import OwnershipProviderMetadata, OwnershipSourceResult
from app.domain.access import TeamId
from app.domain.ownership import OwnershipEnvironment, Party
from app.domain.ownership_evidence import OwnershipEvidence
from app.domain.registry_legal_form import RegistryLegalForm
from app.services.ownership_analysis import (
    EVIDENCE_POC_BASIS_ID,
    eligible_poc_acceptance,
    poc_unit_basis,
)

AT = datetime(2026, 10, 1, tzinfo=UTC)


def units(party: str, value: str, uen: str, **changes: object) -> OwnershipEvidence:
    data: dict[str, object] = dict(
        evidence_id=f"units-{party}",
        entity_identifier=uen,
        party_id=party,
        kind="SHARE_UNITS",
        raw_value=value,
        numeric_value=value,
        source_operation="OWNERSHIP_PARTIES",
        provider="ACRA_REGISTRY_ACQUISITION",
        environment="MOCK",
        retrieved_at=AT,
        evidence_version=1,
        share_class="ORDINARY SGD",
        source_status="Active",
        determination_basis="SOURCE_SCALAR",
    )
    data.update(changes)
    return OwnershipEvidence.model_validate(data)


class Provider:
    def __init__(
        self,
        uen: str,
        items: tuple[OwnershipEvidence, ...],
        *,
        environment: str = "MOCK",
        legal_form: RegistryLegalForm = RegistryLegalForm.COMPANY,
        corporate: frozenset[str] = frozenset(),
    ) -> None:
        self.uen, self.items, self.environment = uen, items, environment
        self.legal_form, self.corporate = legal_form, corporate

    @property
    def metadata(self) -> OwnershipProviderMetadata:
        return OwnershipProviderMetadata(
            provider_name="ACRA_REGISTRY_ACQUISITION", environment=self.environment
        )

    def load(self, request: object) -> OwnershipSourceResult:
        holders = sorted({item.party_id for item in self.items})
        return OwnershipSourceResult(
            root_party_id="ROOT",
            parties=[
                Party(
                    party_id="ROOT",
                    display_name="Synthetic root",
                    party_type="LEGAL_ENTITY",
                    registration_number=self.uen,
                ),
                *(
                    Party(
                        party_id=party,
                        display_name=f"Synthetic {party}",
                        party_type="LEGAL_ENTITY" if party in self.corporate else "NATURAL_PERSON",
                    )
                    for party in holders
                ),
            ],
            evidence=list(self.items),
            legal_form=self.legal_form,
        )


def analyze(uen: str, items: tuple[OwnershipEvidence, ...], **options: object) -> object:
    _, zero, _, _, _ = build_system(require_confirmation=True)
    case = zero.create_case(uen, "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    zero._ownership.load(case_id=case.case_id, provider=Provider(uen, items, **options))
    return zero._ownership.analyze(case_id=case.case_id)


def accept(record: object) -> object:
    return eligible_poc_acceptance(
        record,  # type: ignore[arg-type]
        scenario=None,
        accepted_at=AT,
        ownership_version=record.version,  # type: ignore[attr-defined]
    )


def register(uen: str) -> tuple[OwnershipEvidence, ...]:
    return (
        units("A", "600", uen),
        units("B", "300", uen),
        units("C", "100", uen),
        # Withdrawn rows stay history and never enter the denominator.
        units("D", "5000", uen, source_status="Withdrawn"),
    )


def test_two_unlisted_companies_with_equivalent_evidence_have_equivalent_results() -> None:
    first, second = analyze("202400001A", register("202400001A")), analyze(
        "202400002B", register("202400002B")
    )
    for record in (first, second):
        assert record.state == "REVIEW_REQUIRED"
        assert {issue.code for issue in record.issues} == {"OWNERSHIP_DENOMINATOR_REQUIRED"}
        assert all(
            edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER
            and edge.provenance.environment == OwnershipEnvironment.LOCAL
            for edge in record.relationships
        )
        # Calculated POC percentages stay separate from legally verified ownership.
        assert {item.classification for item in record.candidates} <= {
            "REVIEW_REQUIRED", "INDETERMINATE"
        }
        acceptance = accept(record)
        assert acceptance is not None
        assert acceptance.overlay_scenario_id == EVIDENCE_POC_BASIS_ID
        assert acceptance.accepted_assumptions == ("EQUAL_UNIT_DENOMINATOR",)
    shares = [
        sorted((edge.child_party_id, edge.ownership_percent) for edge in item.relationships)
        for item in (first, second)
    ]
    assert shares[0] == shares[1] == [
        ("A", Decimal("60.000000")), ("B", Decimal("30.000000")), ("C", Decimal("10.000000"))
    ]
    assert sum(edge.ownership_percent for edge in first.relationships) == Decimal("100")
    # The inclusive 25% threshold is the existing engine's, on the labelled POC basis.
    basis = {
        item.party.party_id: item.synthetic_basis_threshold_result for item in first.candidates
    }
    assert basis == {"A": "MET", "B": "MET", "C": "NOT_MET"}
    # Original evidence, including the withdrawn row, is retained unchanged.
    assert first.evidence == register("202400001A")


def test_mixed_or_unreported_classes_are_never_pooled_and_require_review() -> None:
    uen = "202400003C"
    for items in (
        (units("A", "500", uen), units("B", "500", uen, share_class="PREFERENCE SGD")),
        (units("A", "500", uen), units("B", "500", uen, share_class=None)),
    ):
        record = analyze(uen, items)
        assert record.state == "REVIEW_REQUIRED"
        assert record.relationships == []
        assert any("mix share classes" in issue.message for issue in record.issues)
        assert accept(record) is None


def test_incomplete_conflicting_and_unsupported_evidence_requires_review() -> None:
    uen = "202400008H"
    cases = (
        # Incomplete: a current row without positive units.
        (units("A", "500", uen), units("B", "0", uen)),
        # Unsupported status.
        (units("A", "500", uen), units("B", "500", uen, source_status="Suspended")),
        # Conflicting duplicate rows for one holder.
        (units("A", "500", uen), units("A", "400", uen, evidence_id="units-A2")),
    )
    for items in cases:
        record = analyze(uen, items)
        assert record.state == "REVIEW_REQUIRED"
        assert not any(
            edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER for edge in record.relationships
        )
        assert accept(record) is None


def test_unsupported_legal_form_and_corporate_holders_stay_blocked() -> None:
    uen = "202400009I"
    other = analyze(uen, register(uen), legal_form=RegistryLegalForm.OTHER)
    assert "OWNERSHIP_METHOD_UNSUPPORTED" in {issue.code for issue in other.issues}
    assert accept(other) is None
    # A corporate holder needs its own resolved register; it is never accepted directly.
    corporate = analyze(uen, register(uen), corporate=frozenset({"A"}))
    assert corporate.state == "REVIEW_REQUIRED"
    assert accept(corporate) is None


def test_sandbox_and_live_never_receive_an_assumption_based_quantity() -> None:
    uen = "202400002B"
    items = tuple(
        OwnershipEvidence.model_validate({**item.model_dump(), "environment": "SANDBOX"})
        for item in register(uen)
    )
    record = analyze(uen, items, environment="SANDBOX")
    assert not any(
        edge.provenance.provider == POC_EQUAL_UNITS_PROVIDER for edge in record.relationships
    )
    assert accept(record) is None
    assert poc_unit_basis(items, uen) is None
