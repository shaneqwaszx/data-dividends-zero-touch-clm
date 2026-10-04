"""Synthetic Session 2 ownership evidence, creator decision and composite boundaries."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from test_manual_ownership_evidence import (
    CASE_ID,
    FIXED_TIME,
    Cases,
    make_case,
    make_declaration,
    make_document,
    make_provider,
)

from app.connectors.mock_acra import MockAcraConnector
from app.connectors.mock_goldtier import MockGoldTierConnector
from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import OwnershipProviderRequest
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.documents import DocumentOwnershipObservation
from app.domain.models import RegistryAcquisitionStatus, RegistryOperationStatus
from app.domain.ownership import OwnershipAnalysisState
from app.domain.policy import RegistryPolicySnapshot
from app.services.document_ownership import compare_document_ownership
from app.services.manual_ownership_evidence import ManualOwnershipEvidenceProvider
from app.services.onboarding import OnboardingService
from app.services.ownership_analysis import OwnershipAnalysisService
from app.services.ownership_errors import OwnershipInfrastructureError
from app.services.ownership_repository import InMemoryOwnershipAnalysisRepository
from app.services.repository import InMemoryOnboardingCaseRepository


class DocumentReader:
    def __init__(self, document):
        self.document = document

    def list_documents(self, *, case_id):
        return [self.document] if self.document.case_id == case_id else []

    def get(self, document_id):
        return self.document if self.document.document_id == document_id else None


def proposal(document, **changes):
    values = dict(
        observation_id=uuid4(),
        document_id=document.document_id,
        document_version=1,
        page_number=1,
        source_reference="PAGE_1_ROW_1",
        extraction_method="NATIVE_PDF_TEXT",
        extraction_quality="HIGH",
        evidence_score=0.97,
        owner_name="Avery Tan",
        owner_type="NATURAL_PERSON",
        owned_entity_registration_identifier=make_case().requested_uen,
        explicit_percentage="60",
    )
    values.update(changes)
    return DocumentOwnershipObservation.model_validate(values)


def service_for(cases, provider=None, documents=None, *, supplement=False):
    return OwnershipAnalysisService(
        cases=cases,
        provider=provider or MockOwnershipProvider(MockOwnershipScenario.DIRECT_OWNER),
        documents=documents,
        garden_supplement_enabled=supplement,
        repository=InMemoryOwnershipAnalysisRepository(),
        threshold_percent=Decimal("25"),
        max_parties=100,
        max_relationships=200,
        max_depth=8,
        max_paths_per_candidate=64,
        max_total_paths=256,
        clock=lambda: FIXED_TIME,
    )


@pytest.mark.parametrize(("percentage", "agreement"), [("60", "MATCH"), ("70", "MISMATCH")])
def test_high_quality_source_agreement_is_separate_and_all_proposals_require_creator(
    percentage, agreement
):
    case = make_case()
    document = make_document()
    observation = proposal(document, explicit_percentage=percentage)
    reader = DocumentReader(
        document.model_copy(
            update={"ownership_observations": (observation,), "document_version": 1}
        )
    )
    service = service_for(Cases(case), documents=reader)
    loaded = service.load(case_id=CASE_ID)
    analyzed = service.analyze(case_id=CASE_ID)
    assert loaded.document_observations == (observation,)
    assert analyzed.document_discrepancies[0].agreement == agreement
    assert analyzed.document_discrepancies[0].verification_state == "REVIEW_REQUIRED"
    assert analyzed.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert observation.decision_state == "PROPOSED"
    assert observation.extraction_quality == "HIGH"
    assert analyzed.relationships[0].ownership_percent == Decimal("60")


@pytest.mark.parametrize(
    "changes,agreement",
    [
        ({"owner_type": None}, "NOT_COMPARABLE"),
        ({"extraction_quality": "AMBIGUOUS"}, "AMBIGUOUS"),
        ({"owned_entity_registration_identifier": None}, "NOT_COMPARABLE"),
        (
            {"explicit_percentage": None, "share_count": "6000", "explicit_total_shares": "10000"},
            "NOT_COMPARABLE",
        ),
    ],
)
def test_ambiguous_or_unit_evidence_never_supplies_a_canonical_edge(changes, agreement):
    case = make_case()
    document = make_document()
    observation = proposal(document, **changes)
    source = MockOwnershipProvider(MockOwnershipScenario.DIRECT_OWNER).load(
        OwnershipProviderRequest(
            CASE_ID,
            case.requested_uen,
            case.entity.legal_name,
        )
    )
    compared = compare_document_ownership((observation,), source.parties, source.relationships, ())
    assert compared[0].agreement == agreement
    assert compared[0].verification_state == "REVIEW_REQUIRED"


def test_calculable_manual_edit_retains_old_receipt_and_graph():
    case = make_case()
    cases = Cases(case)
    service = service_for(cases)
    service.load(case_id=CASE_ID)
    original = service.analyze(case_id=CASE_ID)
    assert original.state == OwnershipAnalysisState.ANALYZED
    manual, _, _ = make_provider(case=case)
    revised = service.replace_review_required_source(
        case_id=CASE_ID,
        provider=manual,
        review_receipt=manual.review_receipt,
        expected_version=original.version,
    )
    again = service.replace_review_required_source(
        case_id=CASE_ID,
        provider=manual,
        review_receipt=manual.review_receipt,
        expected_version=revised.version,
    )
    prior = again.prior_analyses[-1]
    assert prior.manual_review_receipt == revised.manual_review_receipt
    assert prior.relationships == tuple(revised.relationships)
    assert again.prior_analyses[-2].relationships == tuple(original.relationships)
    assert again.manual_review_receipt.replaced_ownership_version == revised.version


def test_creator_document_decision_retains_original_and_current_bindings():
    case = make_case()
    document = make_document()
    observation = proposal(document, explicit_percentage="70")
    reader = DocumentReader(
        document.model_copy(
            update={"ownership_observations": (observation,), "document_version": 1}
        )
    )
    cases = Cases(case)
    service = service_for(cases, documents=reader)
    service.load(case_id=CASE_ID)
    original = service.analyze(case_id=CASE_ID)
    declaration = make_declaration().model_copy(
        update={
            "observed_document_versions": original.document_bindings,
            "selected_observation_ids": (observation.observation_id,),
        }
    )
    provider = ManualOwnershipEvidenceProvider(
        declaration=declaration,
        reviewed_by_actor_id="rm-a",
        cases=cases,
        documents=reader,
        clock=lambda: FIXED_TIME,
    )
    revised = service.replace_review_required_source(
        case_id=CASE_ID,
        provider=provider,
        review_receipt=provider.review_receipt,
        expected_version=original.version,
    )
    assert revised.state == OwnershipAnalysisState.ANALYZED
    assert revised.document_observations == original.document_observations
    assert revised.document_discrepancies[0].agreement == "MISMATCH"
    assert revised.document_discrepancies[0].verification_state == "REVIEWED"
    assert (
        revised.prior_analyses[-1].document_discrepancies[0].verification_state == "REVIEW_REQUIRED"
    )
    assert revised.manual_review_receipt.observed_document_versions == original.document_bindings


def test_document_version_change_retires_the_old_analysis_without_erasing_it():
    case = make_case()
    document = make_document()
    observation = proposal(document)
    reader = DocumentReader(
        document.model_copy(
            update={"ownership_observations": (observation,), "document_version": 1}
        )
    )
    service = service_for(Cases(case), documents=reader)
    service.load(case_id=CASE_ID)
    original = service.analyze(case_id=CASE_ID)
    reader.document = reader.document.model_copy(
        update={"events": [*reader.document.events, reader.document.events[0]]}
    )
    assert service.get(case_id=CASE_ID) is None
    refreshed = service.load(case_id=CASE_ID)
    assert refreshed.document_bindings[0].event_count == 2
    assert refreshed.prior_analyses[-1].analysis_id == original.analysis_id
    assert refreshed.prior_analyses[-1].document_observations == (observation,)


def official_garden_case():
    cases = OnboardingService(
        acra=MockAcraConnector(clock=lambda: FIXED_TIME),
        goldtier=MockGoldTierConnector(),
        repository=InMemoryOnboardingCaseRepository(),
        clock=lambda: FIXED_TIME,
    )
    case = cases.create_staged_case("11111999A")
    acquisition = case.registry_acquisition
    entity = acquisition.entity_profile.model_copy(
        update={
            "source": acquisition.entity_profile.source.model_copy(
                update={
                    "registry_source_link": "https://api-sandbox.bizfile.gov.sg/api/acra/entityQuery/entityBasicInformation",
                }
            )
        }
    )
    operations = (
        *acquisition.operation_results[:2],
        acquisition.operation_results[2].model_copy(
            update={
                "status": RegistryOperationStatus.EMPTY,
                "record_count": 0,
            }
        ),
        acquisition.operation_results[3].model_copy(
            update={
                "status": RegistryOperationStatus.UNSUPPORTED,
                "record_count": 0,
                "provenance": None,
            }
        ),
    )
    # A normalized successful official profile with truthful empty/unsupported quantities.
    acquisition = acquisition.model_copy(
        update={
            "entity_profile": entity,
            "ownership_parties": (),
            "relationships": (),
            "operation_results": operations,
            "status": RegistryAcquisitionStatus.PARTIAL,
        }
    )
    policy = case.policy_snapshot.model_copy(update={"registry": RegistryPolicySnapshot()})
    return case.model_copy(
        update={
            "entity": entity,
            "registry_acquisition": acquisition,
            "registry_evidence_binding": None,
            "policy_snapshot": policy,
        }
    )


def test_enabled_garden_component_preserves_official_facts_and_uses_single_engine():
    case = official_garden_case()
    cases = Cases(case)
    provider = RegistryAcquisitionOwnershipProvider(
        cases, garden_supplement_enabled=True, clock=lambda: FIXED_TIME
    )
    service = service_for(cases, provider, supplement=True)
    service.load(case_id=case.case_id)
    analyzed = service.analyze(case_id=case.case_id)
    assert analyzed.state == OwnershipAnalysisState.ANALYZED
    assert analyzed.source_classification == "OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT"
    assert {edge.provenance.provider for edge in analyzed.relationships} == {
        "LOCAL_SYNTHETIC_SUPPLEMENT"
    }
    percentages = {
        item.party.party_id: item.aggregated_ownership_percent for item in analyzed.candidates
    }
    assert percentages["S123AC1234E"] == Decimal("51.13636375")
    assert percentages["S9988776F"] == Decimal("37.500000")
    assert cases.case.registry_acquisition == case.registry_acquisition
    assert not cases.case.registry_acquisition.relationships
    assert cases.case.registry_acquisition.officers == case.registry_acquisition.officers


@pytest.mark.parametrize("mode", ["disabled", "nonofficial", "expired", "failed"])
def test_garden_never_acts_as_a_provider_failure_fallback(mode):
    case = official_garden_case()
    if mode == "nonofficial":
        source = case.entity.source.model_copy(
            update={"registry_source_link": "https://mock.acra.invalid/garden"}
        )
        entity = case.entity.model_copy(update={"source": source})
        case = case.model_copy(
            update={
                "entity": entity,
                "registry_acquisition": case.registry_acquisition.model_copy(
                    update={"entity_profile": entity}
                ),
            }
        )
    if mode == "failed":
        case = case.model_copy(
            update={
                "registry_acquisition": case.registry_acquisition.model_copy(
                    update={"status": RegistryAcquisitionStatus.FAILED}
                )
            }
        )
    now = FIXED_TIME + timedelta(days=91) if mode == "expired" else FIXED_TIME
    provider = RegistryAcquisitionOwnershipProvider(
        Cases(case), garden_supplement_enabled=mode != "disabled", clock=lambda: now
    )
    request = OwnershipProviderRequest(case.case_id, case.requested_uen, case.entity.legal_name)
    if mode == "failed":
        from app.connectors.ownership import OwnershipProviderError

        with pytest.raises(OwnershipProviderError):
            provider.load(request)
    else:
        assert provider.load(request).garden_supplement is None


def test_service_rejects_unconfigured_or_tampered_local_component():
    case = official_garden_case()
    cases = Cases(case)
    provider = RegistryAcquisitionOwnershipProvider(
        cases, garden_supplement_enabled=True, clock=lambda: FIXED_TIME
    )
    service = service_for(cases, provider, supplement=False)
    with pytest.raises(OwnershipInfrastructureError) as error:
        service.load(case_id=case.case_id)
    assert error.value.code == "OWNERSHIP_MALFORMED_SOURCE"
    source = provider.load(
        OwnershipProviderRequest(case.case_id, case.requested_uen, case.entity.legal_name)
    )
    first = source.garden_supplement.relationships[0].model_copy(
        update={"ownership_percent": Decimal("99")}
    )
    changed = source.model_copy(
        update={
            "garden_supplement": source.garden_supplement.model_copy(
                update={
                    "relationships": [first, *source.garden_supplement.relationships[1:]],
                }
            )
        }
    )

    class Tampered:
        metadata = provider.metadata

        def load(self, request):
            return changed

    service = service_for(cases, Tampered(), supplement=True)
    with pytest.raises(OwnershipInfrastructureError) as error:
        service.load(case_id=case.case_id)
    assert error.value.code == "OWNERSHIP_MALFORMED_SOURCE"


def _declaration_for_current(zero, document, ownership, *, percent="55"):
    from app.services.manual_ownership_evidence import (
        ManualEconomicInterest,
        ManualOwnershipDeclaration,
    )

    case = zero._cases.get_case(ownership.case_id)
    return ManualOwnershipDeclaration(
        case_id=ownership.case_id,
        root_registration_number=case.requested_uen,
        evidence_document_id=document.document_id,
        evidence_document_version=len(document.events),
        as_of_date=zero._clock().date(),
        rationale="Creator reviewed the current ownership evidence and revised it.",
        root_party_id=ownership.root_party_id,
        parties=tuple(ownership.parties),
        relationships=tuple(
            ManualEconomicInterest(
                relationship_id=edge.relationship_id,
                parent_party_id=edge.parent_party_id,
                child_party_id=edge.child_party_id,
                ownership_percent=Decimal(percent)
                if index == 0
                else Decimal("100") - Decimal(percent),
            )
            for index, edge in enumerate(ownership.relationships)
        ),
    )


def test_creator_edits_calculable_case_at_final_review_and_resumes_without_target_write():
    from test_zero_touch_orchestration import PDF, build_system

    from app.domain.access import TeamId
    from app.domain.zero_touch import AutomationStage

    _, zero, documents, target, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A, created_by_actor_id="maya-lim")
    waiting = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    assert waiting.current_stage == AutomationStage.READINESS
    original = zero._ownership.get(case_id=created.case_id)
    document = documents.list_documents(case_id=created.case_id)[0]
    case = zero._cases.get_case(created.case_id)
    clm = zero._clm.get(case_id=created.case_id)
    revised = zero.submit_manual_ownership_evidence(
        case_id=created.case_id,
        actor_id="maya-lim",
        declaration=_declaration_for_current(zero, document, original),
        expected_automation_version=waiting.version,
        expected_ownership_version=original.version,
        expected_case_event_count=len(case.events),
    )
    ownership = zero._ownership.get(case_id=created.case_id)
    assert ownership.state == OwnershipAnalysisState.ANALYZED
    assert ownership.relationships[0].ownership_percent == Decimal("55")
    assert ownership.prior_analyses[-1].relationships[0].ownership_percent == Decimal("60")
    assert ownership.manual_review_receipt.actor_id == "maya-lim"
    assert revised.current_stage == AutomationStage.READINESS
    assert any(
        item.exception_type.value == "TARGET_CONFIRMATION_REQUIRED"
        for item in revised.active_exceptions
    )
    assert zero._cases.get_case(created.case_id).target_dispatch_confirmation is None
    assert zero._clm.get(case_id=created.case_id).version > clm.version
    assert target.calls == ["search"]


@pytest.mark.parametrize("creator,actor", [(None, "maya-lim"), ("maya-lim", "other-rm")])
def test_legacy_unknown_or_other_creator_cannot_decide_ownership(creator, actor):
    from test_zero_touch_orchestration import PDF, build_system

    from app.domain.access import TeamId
    from app.services.zero_touch_errors import ZeroTouchRequestError

    _, zero, documents, target, _ = build_system(require_confirmation=True)
    created = zero.create_case("202400001A", team_id=TeamId.TEAM_A, created_by_actor_id=creator)
    waiting = zero.attach_document(
        case_id=created.case_id,
        display_name="synthetic.pdf",
        content_type="application/pdf",
        content=PDF,
    )
    ownership = zero._ownership.get(case_id=created.case_id)
    case = zero._cases.get_case(created.case_id)
    document = documents.list_documents(case_id=created.case_id)[0]
    with pytest.raises(ZeroTouchRequestError) as error:
        zero.submit_manual_ownership_evidence(
            case_id=created.case_id,
            actor_id=actor,
            declaration=_declaration_for_current(zero, document, ownership),
            expected_automation_version=waiting.version,
            expected_ownership_version=ownership.version,
            expected_case_event_count=len(case.events),
        )
    assert error.value.code == "ZERO_TOUCH_OWNERSHIP_CREATOR_REQUIRED"
    assert zero._ownership.get(case_id=created.case_id) == ownership
    assert zero._cases.get_case(created.case_id) == case
    assert target.calls == ["search"]


def test_nonempty_official_garden_quantity_is_not_added_to_local_graph():
    case = official_garden_case()
    from app.domain.models import RegistryOwnershipParty, RegistryPartyType, RegistryRelationship

    acquisition = case.registry_acquisition
    provenance = acquisition.operation_results[0].provenance
    from app.domain.models import RegistryOperation

    ownership_provenance = provenance.model_copy(
        update={"operation": RegistryOperation.OWNERSHIP_PARTIES}
    )
    relationship_provenance = provenance.model_copy(
        update={"operation": RegistryOperation.RELATIONSHIPS}
    )
    party = RegistryOwnershipParty(
        party_id="S9988776F",
        name="LIM CHOON HUAT",
        party_type=RegistryPartyType.NATURAL_PERSON,
        country="SG",
        ownership_percentage=Decimal("70"),
        provenance=ownership_provenance,
    )
    edge = RegistryRelationship(
        relationship_id="OFFICIAL_DIRECT",
        owned_entity_id=acquisition.root_party_id,
        owner_party_id=party.party_id,
        ownership_percentage=Decimal("70"),
        provenance=relationship_provenance,
    )
    acquisition = acquisition.model_copy(
        update={"ownership_parties": (party,), "relationships": (edge,)}
    )
    case = case.model_copy(update={"registry_acquisition": acquisition})
    cases = Cases(case)
    provider = RegistryAcquisitionOwnershipProvider(
        cases, garden_supplement_enabled=True, clock=lambda: FIXED_TIME
    )
    service = service_for(cases, provider, supplement=True)
    service.load(case_id=case.case_id)
    record = service.analyze(case_id=case.case_id)
    assert record.state == OwnershipAnalysisState.REVIEW_REQUIRED
    assert len(record.relationships) == 1
    assert record.relationships[0].ownership_percent == Decimal("70")
    assert len(record.supplemental_relationships) == 5
    assert len(record.supplemental_evidence) == 10
    assert record.supplemental_relationships[0].provenance.provider == "LOCAL_SYNTHETIC_SUPPLEMENT"
    assert any(issue.code.value == "CONTRADICTORY_OWNERSHIP_EVIDENCE" for issue in record.issues)
