"""Phase 24B failing-first counterexamples; synthetic providers only."""

from decimal import Decimal
from uuid import UUID

import pytest
from test_phase24_identity import correction
from test_phase24_ownership_evidence import (
    EvidenceOnlyProvider,
    denominator,
    evidence,
    source,
)
from test_zero_touch_orchestration import PDF, build_system

from app.connectors.mock_acra import MockAcraConnector
from app.connectors.registry import AcraRegistryProviderAdapter, RegistryProviderRouter
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider
from app.domain.access import TeamId
from app.services.ownership_analysis import quantify_ownership_evidence


@pytest.mark.parametrize("units, expected_state", [("1", "REVIEW_REQUIRED"), ("60", "ANALYZED")])
def test_graph_and_compatible_units_are_compared_before_classification(units, expected_state):
    _, zero, _, target, _ = build_system(require_confirmation=True)
    case = zero.create_case("202400001A", "SG", legal_name="Synthetic", team_id=TeamId.TEAM_A)
    direct = evidence(kind="DIRECT_PERCENTAGE", numeric_value="60", raw_value="60",
                      determination_basis="PROVIDER_PERCENTAGE")
    retained = (direct, evidence(evidence_id="unit-interest", numeric_value=units,
                                raw_value=units, authoritative=True),
                denominator(numeric_value="100", raw_value="100"))

    class MixedProvider(EvidenceOnlyProvider):
        def load(self, request):
            return quantify_ownership_evidence(source((direct,))).model_copy(
                update={"evidence": retained}, deep=True,
            )

    zero._ownership.load(case_id=case.case_id, provider=MixedProvider(retained))
    analyzed = zero._ownership.analyze(case_id=case.case_id)
    assert analyzed.state == expected_state
    assert analyzed.evidence == retained
    assert analyzed.relationships[0].ownership_percent == Decimal("60")
    assert target.calls == ["search"]
    if expected_state == "REVIEW_REQUIRED":
        assert "CONTRADICTORY_OWNERSHIP_EVIDENCE" in {item.code.value for item in analyzed.issues}
        assert all(item.threshold_result == "INDETERMINATE" for item in analyzed.candidates)
        assert all(item.classification == "REVIEW_REQUIRED" for item in analyzed.candidates)
    else:
        assert analyzed.candidates[0].classification == "PROVISIONAL_UBO_CANDIDATE"


class RecoveringRegistry(MockAcraConnector):
    available = False

    def fetch_ownership_parties(self, uen):
        result = super().fetch_ownership_parties(uen)
        return result if self.available else result.model_copy(update={"ownership_parties": ()})

    def fetch_relationships(self, uen):
        result = super().fetch_relationships(uen)
        return result if self.available else result.model_copy(update={"relationships": ()})


@pytest.mark.parametrize("legacy_binding", [False, True])
def test_authenticated_same_uen_refresh_retires_only_obsolete_registry_ownership_blocker(
    legacy_binding,
):
    client, zero, _, target, _ = build_system(require_confirmation=True)
    registry = RecoveringRegistry()
    zero._cases._registry_router = RegistryProviderRouter(AcraRegistryProviderAdapter(registry))
    zero._ownership._provider = RegistryAcquisitionOwnershipProvider(zero._cases)
    assert client.get("/api/auth/me").status_code == 200
    created = client.post("/api/clm/zero-touch/cases", json={
        "uen": "202400001A", "legal_name": "Synthetic", "country_of_incorporation": "SG",
    })
    assert created.status_code == 201
    case_id = UUID(created.json()["case"]["case_id"])
    uploaded = client.post(f"/api/clm/zero-touch/cases/{case_id}/documents", content=PDF,
                           headers={"Content-Type": "application/pdf",
                                    "X-Document-Name": "synthetic.pdf"})
    assert uploaded.status_code == 200
    blocked = zero.get(case_id=case_id)
    old = zero._ownership.get(case_id=case_id)
    obsolete = next(item for item in blocked.active_exceptions
                    if item.blocker_code == "OWNERSHIP_REQUIRED")
    assert obsolete.registry_evidence_generation == 0
    if legacy_binding:
        legacy = blocked.model_copy(deep=True)
        next(item for item in legacy.active_exceptions
             if item.exception_id == obsolete.exception_id).registry_evidence_generation = None
        blocked = zero._save(blocked, legacy)
    registry.available = True
    response = correction(client, zero, blocked, choice="ENTERED", uen="202400001A")
    assert response.status_code == 200
    current = zero.get(case_id=case_id)
    retained = next(item for item in current.exceptions
                    if item.exception_id == obsolete.exception_id)
    assert retained.status == "CANCELLED"
    ownership = zero._ownership.get(case_id=case_id)
    assert ownership is not None and ownership.analysis_id != old.analysis_id
    assert ownership.identity_correction_version == 1
    assert ownership.prior_analyses[-1].analysis_id == old.analysis_id
    assert ownership.state == "ANALYZED"
    assert ownership.candidates
    assert {item.blocker_code for item in current.active_exceptions} == {
        "TARGET_CONFIRMATION_REQUIRED",
    }
    assert target.calls == ["search", "search"]


def test_same_uen_refresh_preserves_current_independent_ownership_blocker():
    client, zero, _, target, _ = build_system(require_confirmation=True)
    zero._ownership._provider = EvidenceOnlyProvider((evidence(),))
    created = client.post("/api/clm/zero-touch/cases", json={
        "uen": "202400001A", "legal_name": "Synthetic", "country_of_incorporation": "SG",
    }).json()
    case_id = UUID(created["case"]["case_id"])
    assert client.post(f"/api/clm/zero-touch/cases/{case_id}/documents", content=PDF,
                       headers={"Content-Type": "application/pdf",
                                "X-Document-Name": "synthetic.pdf"}).status_code == 200
    blocked = zero.get(case_id=case_id)
    independent = blocked.active_exceptions[0]
    assert independent.stage == "OWNERSHIP"
    assert independent.registry_evidence_generation is None
    assert correction(client, zero, blocked, choice="ENTERED", uen="202400001A").status_code == 200
    current = zero.get(case_id=case_id)
    assert independent.exception_id in {item.exception_id for item in current.active_exceptions}
    assert zero._ownership.get(case_id=case_id).state == "REVIEW_REQUIRED"
    assert target.calls == ["search", "search"]
