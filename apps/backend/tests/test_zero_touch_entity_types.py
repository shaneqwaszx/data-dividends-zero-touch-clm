"""D-101 Partnership and Government demo entity types through the database lane."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.zero_touch_happy_path_fixtures import COMPANIES, GOVERNMENT
from test_slice_b_registry_demo import confirm
from test_zero_touch_database_happy_path import NoAcra, RecordingTarget, sandbox_settings

from app.domain.models import RegistryFreshnessPolicy
from app.domain.registry_dataset import local_synthetic_registry_identity
from app.domain.registry_legal_form import RegistryLegalForm, classify_registry_legal_form
from app.domain.target_classification import bounded_classification_compatible
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.registry_acquisition import RegistryAcquisitionCoordinator
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

GAMMA = COMPANIES[2]
GAMMA_ROOT = f"ENTITY_{GAMMA.uen}"
# D-125: the RM keys in the founding statute and type of body with every confirmation.
STATUTE = {
    "founding_statute": "Demo Parks FYP Test Authority Act",
    "government_body_type": "STATUTORY_BOARD",
}


# D-121: these tests pin the blocking review, the rollback mode.
pytestmark = pytest.mark.usefixtures("blocking_ubo_review")


@contextmanager
def lane(company) -> Iterator[tuple[TestClient, NoAcra, RecordingTarget, object]]:
    settings = sandbox_settings()
    bundle = build_persistence_bundle(settings)
    manage_fixtures(bundle.registry_snapshots, now=datetime.now(UTC), seed=True)
    acra = NoAcra()
    target = RecordingTarget(company.name, company.uen)
    with (
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(settings, acra_connector=acra, goldtier_transport=target)) as client,
    ):
        yield client, acra, target, bundle


def create(client, company) -> dict:
    response = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": company.uen, "legal_name": company.name, "country_of_incorporation": "SG"},
    )
    assert response.status_code == 201, response.json()
    return response.json()


def upload(client, current, lines, name="fictional.txt") -> None:
    response = client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/intake/documents",
        content="\n".join(lines).encode(),
        headers={"Content-Type": "text/plain", "X-Document-Name": name},
    )
    assert response.status_code == 201, response.json()


def complete(client, current, count) -> dict:
    response = client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/intake/complete",
        json={"expected_document_count": count},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def identity_lines(company) -> tuple[str, ...]:
    return tuple(
        f"{key}: {value}" for key, value in {**company.fields, **company.target_profile}.items()
    )


def documents(client, current) -> list[dict]:
    payload = client.get(
        f"/api/onboarding/cases/{current['case']['case_id']}/documents"
    ).json()
    return payload["documents"] if isinstance(payload, dict) else payload


def agreement_document(client, current) -> dict:
    return next(
        item for item in documents(client, current)
        if any("_PARTNER_SHARE_ROW_" in row["source_reference"]
               for row in item.get("ownership_observations") or ())
    )


def blockers(current) -> list[str]:
    return [item["blocker_code"] for item in current["active_exceptions"]]


def gamma_at_ownership(client, agreement=GAMMA.partnership_agreement_lines) -> dict:
    current = create(client, GAMMA)
    upload(client, current, identity_lines(GAMMA), "identity.txt")
    upload(client, current, agreement, "agreement.txt")
    return complete(client, current, 2)


def partner_declaration(current, document, shares=None, *, bindings) -> dict:
    """The RM's confirmation of the extracted agreement rows (the form's payload)."""
    rows = [
        item for item in document["ownership_observations"]
        if "_PARTNER_SHARE_ROW_" in item["source_reference"]
    ]
    shares = shares or [(item["owner_name"], item["explicit_percentage"]) for item in rows]
    parties = [{
        "party_id": GAMMA_ROOT, "display_name": GAMMA.name, "party_type": "LEGAL_ENTITY",
        "registration_number": GAMMA.uen, "country": "SG",
    }]
    relationships = []
    for index, (name, percent) in enumerate(shares, 1):
        parties.append({"party_id": f"PARTNER_{index}", "display_name": name,
                        "party_type": "NATURAL_PERSON", "country": "SG"})
        relationships.append({"relationship_id": f"SHARE_{index}",
                              "parent_party_id": GAMMA_ROOT,
                              "child_party_id": f"PARTNER_{index}",
                              "ownership_percent": str(percent)})
    return {
        "root_registration_number": GAMMA.uen,
        "evidence_document_id": document["document_id"],
        "evidence_document_version": len(document["events"]),
        "as_of_date": "2026-01-05",
        "rationale": "Reviewed synthetic partnership agreement shares.",
        "source_selection": "DOCUMENT_OBSERVATIONS",
        "observed_document_versions": bindings,
        "selected_observation_ids": [item["observation_id"] for item in rows],
        "root_party_id": GAMMA_ROOT,
        "parties": parties,
        "relationships": relationships,
        "expected_automation_version": current["version"],
        "expected_ownership_version": current["ownership_recovery"]["version"],
        "expected_case_event_count": len(current["case"]["events"]),
    }


def observed_bindings(client, current) -> list[dict]:
    """The form's binding of every current document carrying ownership rows."""
    return [
        {"document_id": item["document_id"], "event_count": len(item["events"])}
        for item in sorted(documents(client, current), key=lambda item: item["document_id"])
        if item.get("ownership_observations") and item.get("superseded_by_document_id") is None
    ]


def gamma_declaration(client, current, shares=None) -> dict:
    return partner_declaration(
        current, agreement_document(client, current), shares,
        bindings=observed_bindings(client, current),
    )


def submit_partners(client, current, payload):
    return client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/manual-ownership-evidence",
        json=payload,
    )


def government_at_status(client, lines=GOVERNMENT.government_status_lines) -> dict:
    current = create(client, GOVERNMENT)
    upload(client, current, lines, "status.txt")
    return complete(client, current, 1)


def confirm_government(client, current, **statute):
    status = current["entity_type_basis"]["government_status"]
    return client.post(
        f"/api/clm/zero-touch/cases/{current['case']['case_id']}/government-status-confirmation",
        json={
            "document_id": status["document_id"],
            "document_event_count": status["document_event_count"],
            "expected_automation_version": current["version"],
            "expected_case_event_count": len(current["case"]["events"]),
            **STATUTE,
            **statute,
        },
    )


def test_partnership_happy_path_reaches_ready_for_approval_with_rm_confirmed_shares():
    with lane(GAMMA) as (client, acra, target, _):
        current = gamma_at_ownership(client)
        assert current["current_stage"] == "OWNERSHIP"
        assert current["entity_type_basis"] == {
            "entity_type": "PARTNERSHIP",
            "label": "Partner shares from partnership agreement, awaiting RM confirmation",
            "partnership_state": "AWAITING_RM_CONFIRMATION",
            "government_status": None,
        }
        assert current["case"]["registry_evidence_binding"] is None
        response = submit_partners(client, current, gamma_declaration(client, current))
        assert response.status_code == 200, response.json()
        current = response.json()
        assert blockers(current) == ["TARGET_CONFIRMATION_REQUIRED"]
        assert current["clm"]["readiness"]["blockers"] == []
        assert current["entity_type_basis"]["label"] == (
            "Partner shares from partnership agreement, RM-confirmed"
        )
        ownership = client.get(
            f"/api/onboarding/cases/{current['case']['case_id']}/ownership"
        ).json()
        assert ownership["state"] == "ANALYZED"
        provisional = {
            item["party"]["display_name"]: Decimal(item["aggregated_ownership_percent"])
            for item in ownership["candidates"]
            if item["classification"] == "PROVISIONAL_UBO_CANDIDATE"
        }
        assert provisional == {"DEMO GAMMA PERSON P1": Decimal("30"),
                               "DEMO GAMMA PERSON P2": Decimal("25")}
        final = confirm(client, current)
        assert final["status"] == "COMPLETED"
        assert acra.calls == []


def test_government_happy_path_reaches_ready_for_approval_without_ownership_step():
    with lane(GOVERNMENT) as (client, acra, target, bundle):
        current = government_at_status(client)
        assert current["current_stage"] == "OWNERSHIP"
        assert blockers(current) == ["GOVERNMENT_STATUS_REQUIRED"]
        assert "GOVERNMENT_STATUS_REQUIRED" in current["clm"]["readiness"]["blockers"]
        basis = current["entity_type_basis"]
        assert basis["label"] == (
            "Local synthetic identity: not ACRA-registered; government status from "
            "reviewed document"
        )
        assert basis["government_status"]["state"] == "CONFIRMATION_REQUIRED"
        response = confirm_government(client, current)
        assert response.status_code == 200, response.json()
        current = response.json()
        assert blockers(current) == ["TARGET_CONFIRMATION_REQUIRED"]
        assert current["clm"]["readiness"]["blockers"] == []
        assert current["entity_type_basis"]["government_status"]["state"] == "CONFIRMED"
        final = confirm(client, current)
        assert final["status"] == "COMPLETED"
        # The browser projection omits UBO detail, so read the frozen domain snapshot.
        snapshot = bundle.clm.get_for_case(UUID(final["case"]["case_id"])).submission_snapshot
        assert snapshot is not None
        assert snapshot.ownership_reference.status == "GOVERNMENT_STATUS_CONFIRMED"
        assert snapshot.provisional_ubo.candidate_count == 0
        assert snapshot.provisional_ubo.internal_party_ids == ()
        assert acra.calls == []


@pytest.mark.parametrize("company", [GAMMA, GOVERNMENT], ids=["GAMMA", "GOVERNMENT"])
def test_partial_local_seed_serves_identity_without_any_provider_call(company):
    with lane(company) as (client, acra, _, _):
        current = create(client, company)
        assert current["case"]["registry_evidence_binding"] is None
        assert current["case"]["registry_acquisition"]["status"] == "PARTIAL"
        assert acra.calls == []


# --- Partnership adverse paths (fail closed, never auto-corrected) ---------------------------


def agreement_with(shares) -> tuple[str, ...]:
    head = [line for line in GAMMA.partnership_agreement_lines
            if not line.startswith(("Partner Share:", "Signing Partner:"))]
    return (*head, *(f"Partner Share: {name}: {value} percent: NATURAL_PERSON"
                     for name, value in shares))


GAMMA_SHARES = [(f"DEMO GAMMA PERSON {key}", value) for key, value in GAMMA.expected]


@pytest.mark.parametrize(
    "shares",
    [
        [("DEMO GAMMA PERSON P1", "29"), *GAMMA_SHARES[1:]],  # totals 99
        [("DEMO GAMMA PERSON P1", "31"), *GAMMA_SHARES[1:]],  # totals 101
        [("DEMO GAMMA PERSON P1", "35"), *GAMMA_SHARES[1:5]],  # registry P6 missing
        [("DEMO GAMMA PERSON P1", "25"), *GAMMA_SHARES[1:],
         ("DEMO GAMMA PERSON P7", "5")],  # extra partner
        [("DEMO GAMMA PERSON P1", "25"), *GAMMA_SHARES[1:],
         ("DEMO GAMMA PERSON P1", "5")],  # duplicate partner
        [("DEMO GAMMA PERSON P1", "30"), *GAMMA_SHARES[1:5],
         ("DEMO GAMMA PERSON P6", "5"), ("DEMO GAMMA PERSON P6", "0")],  # zero share
    ],
    ids=["total-99", "total-101", "missing-partner", "extra-partner", "duplicate", "zero"],
)
def test_partnership_agreement_mismatch_keeps_the_case_blocked(shares):
    with lane(GAMMA) as (client, acra, target, _):
        current = gamma_at_ownership(client, agreement_with(shares))
        before = (current["version"], blockers(current), current["current_stage"])
        # Whatever the RM submits (the agreement as read, or a "corrected" 100% split),
        # the case never leaves Ownership review.
        for declared in (None, GAMMA_SHARES):
            payload = gamma_declaration(client, current, declared)
            response = submit_partners(client, current, payload)
            assert response.status_code in {409, 422}, response.json()
        after = client.get(f"/api/clm/zero-touch/cases/{current['case']['case_id']}").json()
        assert (after["version"], blockers(after), after["current_stage"]) == before
        assert "OWNERSHIP_REVIEW_REQUIRED" in after["clm"]["readiness"]["blockers"]
        assert [call[0] for call in target.calls] == ["GET"]
        assert acra.calls == []


def test_partnership_corrected_split_against_a_matching_agreement_is_refused():
    with lane(GAMMA) as (client, _, _, _):
        current = gamma_at_ownership(client)
        changed = [("DEMO GAMMA PERSON P1", "25"), ("DEMO GAMMA PERSON P2", "30"),
                   *GAMMA_SHARES[2:]]
        response = submit_partners(client, current, {
            **gamma_declaration(client, current, changed),
            "source_selection": "USER_SUPPLIED_DECLARATION",
            "selected_observation_ids": [],
        })
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "ZERO_TOUCH_PARTNERSHIP_AGREEMENT_MISMATCH"


def test_partnership_shares_extracted_but_not_confirmed_stay_blocked():
    with lane(GAMMA) as (client, _, target, _):
        current = gamma_at_ownership(client)
        assert current["status"] == "WAITING_FOR_REVIEW"
        assert current["current_stage"] == "OWNERSHIP"
        assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
        assert len(agreement_document(client, current)["ownership_observations"]) == 6
        ownership = client.get(
            f"/api/onboarding/cases/{current['case']['case_id']}/ownership"
        ).json()
        assert ownership["state"] == "REVIEW_REQUIRED"
        assert ownership["relationships"] == []
        send = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/target-confirmation",
            json={"expected_automation_version": current["version"],
                  "expected_clm_version": current["clm"]["version"],
                  "expected_case_event_count": len(current["case"]["events"])},
        )
        assert send.status_code == 409
        assert [call[0] for call in target.calls] == ["GET"]


# --- Government adverse paths ------------------------------------------------------------------


def test_government_without_a_status_document_stays_blocked():
    with lane(GOVERNMENT) as (client, _, target, _):
        lines = tuple(line for line in GOVERNMENT.government_status_lines
                      if not line.startswith("Founding Instrument:"))
        current = government_at_status(client, lines)
        assert blockers(current) == ["GOVERNMENT_STATUS_REQUIRED"]
        status = current["entity_type_basis"]["government_status"]
        assert status["state"] == "EVIDENCE_REQUIRED" and status["document_id"] is None
        document = documents(client, current)[0]
        response = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/government-status-confirmation",
            json={"document_id": document["document_id"],
                  "document_event_count": len(document["events"]),
                  "expected_automation_version": current["version"],
                  "expected_case_event_count": len(current["case"]["events"]), **STATUTE},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "ZERO_TOUCH_GOVERNMENT_STATUS_EVIDENCE_REQUIRED"
        assert [call[0] for call in target.calls] == ["GET"]


def test_government_document_without_rm_confirmation_stays_blocked():
    with lane(GOVERNMENT) as (client, _, target, bundle):
        current = government_at_status(client)
        assert current["entity_type_basis"]["government_status"]["state"] == (
            "CONFIRMATION_REQUIRED"
        )
        assert "GOVERNMENT_STATUS_REQUIRED" in current["clm"]["readiness"]["blockers"]
        send = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/target-confirmation",
            json={"expected_automation_version": current["version"],
                  "expected_clm_version": current["clm"]["version"],
                  "expected_case_event_count": len(current["case"]["events"])},
        )
        assert send.status_code == 409
        case = bundle.onboarding.get(UUID(current["case"]["case_id"]))
        assert case.government_status_confirmation is None
        assert [call[0] for call in target.calls] == ["GET"]


def test_government_confirmation_must_bind_the_exact_document_version():
    with lane(GOVERNMENT) as (client, _, _, _):
        current = government_at_status(client)
        status = current["entity_type_basis"]["government_status"]
        response = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/government-status-confirmation",
            json={"document_id": status["document_id"],
                  "document_event_count": status["document_event_count"] + 1,
                  "expected_automation_version": current["version"],
                  "expected_case_event_count": len(current["case"]["events"]), **STATUTE},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "ZERO_TOUCH_GOVERNMENT_STATUS_EVIDENCE_REQUIRED"
        stale = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/government-status-confirmation",
            json={"document_id": status["document_id"],
                  "document_event_count": status["document_event_count"],
                  "expected_automation_version": current["version"] + 1,
                  "expected_case_event_count": len(current["case"]["events"]), **STATUTE},
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "ZERO_TOUCH_GOVERNMENT_STATUS_STALE"


def test_government_case_never_claims_acra_verification():
    with lane(GOVERNMENT) as (client, _, _, _):
        current = government_at_status(client)
        current = confirm_government(client, current).json()
        assert current["case"]["registry_evidence_binding"] is None
        assert current["case"]["entity"]["party_type"] == "GOVERNMENT"
        assert "not ACRA-registered" in current["entity_type_basis"]["label"]
        issues = current["case"]["registry_acquisition"]["issues"]
        assert [item["code"] for item in issues] == ["REGISTRY_EXPECTED_DATA_MISSING"]
        assert "Not ACRA-registered" in issues[0]["message"]


@pytest.mark.parametrize("company", [COMPANIES[0], GAMMA], ids=["company", "partnership"])
def test_government_label_on_a_non_government_entity_is_unsafe(company):
    with lane(company) as (client, _, _, _):
        current = create(client, company)
        upload(client, current, (
            *(f"{key}: {value}" for key, value in company.fields.items()),
            "KYC Customer Type: Government",
            "Client Segment: DI - Government",
        ))
        current = complete(client, current, 1)
        kyc = current["target_classification"]["kyc_customer_type"]
        assert kyc["selected_value"] != "Government"
        assert kyc["selection"] is None or kyc["selection"]["source"] != "DOCUMENT"
        manual = client.put(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/target-classification",
            json={"kyc_customer_type": "Government", "client_segment": "DI - Government",
                  "expected_classification_evidence_fingerprint": current[
                      "target_classification"].get("evidence_fingerprint"),
                  "expected_automation_version": current["version"],
                  "expected_case_event_count": len(current["case"]["events"])},
        )
        assert manual.status_code == 422, manual.json()
        assert current["entity_type_basis"] is None or (
            current["entity_type_basis"]["entity_type"] != "GOVERNMENT"
        )


# --- Legal-form compatibility table (every cell) -----------------------------------------------

FORM_SOURCE = {
    RegistryLegalForm.COMPANY: "PRIVATE COMPANY LIMITED BY SHARES",
    RegistryLegalForm.BUSINESS_PARTNERSHIP: "PARTNERSHIP",
    RegistryLegalForm.LLP: "LIMITED LIABILITY PARTNERSHIP",
    RegistryLegalForm.LP: "LIMITED PARTNERSHIP",
    RegistryLegalForm.GOVERNMENT: "GOVERNMENT",
    RegistryLegalForm.OTHER: "STATUTORY BOARD OF SOMEWHERE",
}
KNOWN = {
    "Company - Private": {RegistryLegalForm.COMPANY},
    "Company - Public": {RegistryLegalForm.COMPANY},
    "Partnership - Unregulated": {
        RegistryLegalForm.BUSINESS_PARTNERSHIP, RegistryLegalForm.LLP, RegistryLegalForm.LP,
    },
    "Partnership - Regulated": {
        RegistryLegalForm.BUSINESS_PARTNERSHIP, RegistryLegalForm.LLP, RegistryLegalForm.LP,
    },
    "Sole Trader": {RegistryLegalForm.BUSINESS_PARTNERSHIP},
    "Government": {RegistryLegalForm.GOVERNMENT},
}


@pytest.mark.parametrize("form", list(FORM_SOURCE), ids=lambda form: form.value)
@pytest.mark.parametrize("kyc", [*KNOWN, "Trust - Regulated", "Individual"])
@pytest.mark.parametrize("automatic", [True, False], ids=["automatic", "manual"])
def test_compatibility_table_every_cell(form, kyc, automatic):
    party_type = FORM_SOURCE[form]
    assert classify_registry_legal_form(party_type) == form
    if kyc not in KNOWN:
        expected = True  # outside the three families: earlier behaviour
    elif form == RegistryLegalForm.OTHER:
        expected = not automatic  # unknown form: automatic fails closed, manual allowed
    else:
        expected = form in KNOWN[kyc]
    assert bounded_classification_compatible(party_type, kyc, automatic=automatic) is expected


@pytest.mark.parametrize("missing", [None, ""])
def test_missing_legal_form_fails_closed_only_for_automatic_candidates(missing):
    assert not bounded_classification_compatible(missing, "Government", automatic=True)
    assert bounded_classification_compatible(missing, "Government", automatic=False)


def test_government_legal_form_is_the_exact_source_value_only():
    assert classify_registry_legal_form("GOVERNMENT") == RegistryLegalForm.GOVERNMENT
    for other in ("GOVERNMENT AGENCY", "STATUTORY BOARD", "MINISTRY", "GOVT"):
        assert classify_registry_legal_form(other) == RegistryLegalForm.OTHER


# --- Narrowed PARTIAL local seed (D-101 change to the registry cache owner) --------------------

NOW = datetime(2026, 10, 29, tzinfo=UTC)


class CountingProvider:
    cache_identity = local_synthetic_registry_identity().model_copy(
        update={"dataset_namespace": "ACRA_API_MARKETPLACE_MOCK_V1"}
    )

    def __init__(self):
        self.calls = []

    def retrieve_acquisition(self, identifier, **kwargs):
        self.calls.append(identifier)
        return None


def acquire(entry, *, now=NOW):
    repository = InMemoryRegistrySnapshotRepository()
    repository.create(entry)
    provider = CountingProvider()
    result = RegistryAcquisitionCoordinator(
        repository, RegistryFreshnessPolicy(), clock=lambda: now,
        local_seed_identity=local_synthetic_registry_identity(),
    ).acquire(provider, entry.key.normalized_identifier)
    return result, provider.calls


@pytest.mark.parametrize("company", [GAMMA, GOVERNMENT], ids=["GAMMA", "GOVERNMENT"])
def test_partial_partnership_or_government_seed_is_used_unbound(company):
    result, calls = acquire(company.snapshot(NOW))
    assert calls == []
    assert result.binding is None
    assert result.acquisition.status == "PARTIAL"
    assert result.acquisition.entity_profile.legal_name == company.name


def test_partial_seed_for_a_company_legal_form_is_still_skipped():
    company_shaped = replace(GAMMA, party_type="PRIVATE COMPANY LIMITED BY SHARES")
    result, calls = acquire(company_shaped.snapshot(NOW))
    assert calls == [GAMMA.uen] and result.acquisition is None


@pytest.mark.parametrize("gap", ["legal_name", "registered_address"])
def test_partial_seed_with_an_incomplete_entity_profile_is_still_skipped(gap):
    entry = GAMMA.snapshot(NOW)
    profile = entry.acquisition.entity_profile.model_copy(update={gap: None})
    entry = entry.model_copy(
        update={"acquisition": entry.acquisition.model_copy(update={"entity_profile": profile})}
    )
    result, calls = acquire(entry)
    assert calls == [GAMMA.uen] and result.acquisition is None


def test_stale_partial_seed_is_still_skipped():
    result, calls = acquire(GOVERNMENT.snapshot(NOW), now=NOW + timedelta(days=90))
    assert calls == [GOVERNMENT.uen] and result.acquisition is None


def test_complete_seed_is_unchanged_cache_hit():
    result, calls = acquire(COMPANIES[0].snapshot(NOW))
    assert calls == []
    assert result.binding is not None and result.binding.disposition == "CACHE_HIT"


def test_government_hold_never_offers_ownership_inputs():
    with lane(GOVERNMENT) as (client, _, _, _):
        current = government_at_status(client)
        cards = [item for item in current["interventions"] if item["owning_stage"] == "OWNERSHIP"]
        assert [item["title"] for item in cards] == ["Government status — needs confirmation"]
        assert cards[0]["evidence_actions"] == []


# --- Manual-test follow-ups: partnership agreement shares are not registry conflicts ---------


def test_partnership_agreement_shares_are_pending_not_conflicts_until_confirmed():
    with lane(GAMMA) as (client, _, _, _):
        current = gamma_at_ownership(client)
        assert current["entity_type_basis"]["partnership_state"] == "AWAITING_RM_CONFIRMATION"
        ownership = client.get(
            f"/api/onboarding/cases/{current['case']['case_id']}/ownership"
        ).json()
        rows = ownership["document_discrepancies"]
        assert len(rows) == 6
        assert {(item["agreement"], item["reason_code"], item["verification_state"])
                for item in rows} == {
            ("NOT_COMPARABLE", "PARTNERSHIP_AGREEMENT_SHARE", "REVIEW_REQUIRED")
        }
        codes = {item["code"] for item in ownership["issues"]}
        assert "CONTRADICTORY_OWNERSHIP_EVIDENCE" not in codes
        assert "OWNERSHIP_REVIEW_REQUIRED" in current["clm"]["readiness"]["blockers"]
        confirmed = submit_partners(client, current, gamma_declaration(client, current)).json()
        assert confirmed["entity_type_basis"]["partnership_state"] == "RM_CONFIRMED"
        after = client.get(f"/api/onboarding/cases/{current['case']['case_id']}/ownership").json()
        assert {item["verification_state"] for item in after["document_discrepancies"]} == {
            "REVIEWED"
        }


def test_a_real_registry_share_still_conflicts_with_a_different_agreement_share():
    from app.domain.ownership import (
        OwnershipEnvironment,
        OwnershipProvenance,
        OwnershipRelationship,
        OwnershipRelationshipType,
        Party,
        PartyType,
    )
    from app.services.document_ownership import compare_document_ownership

    with lane(GAMMA) as (client, _, _, _):
        current = gamma_at_ownership(client)
        document = agreement_document(client, current)
    from app.domain.documents import DocumentOwnershipObservation

    row = DocumentOwnershipObservation.model_validate(document["ownership_observations"][0])
    root = Party(party_id="ROOT", display_name=GAMMA.name, party_type=PartyType.LEGAL_ENTITY,
                 registration_number=GAMMA.uen, country="SG")
    owner = Party(party_id="P1", display_name=row.owner_name,
                  party_type=PartyType.NATURAL_PERSON, country="SG")
    provenance = OwnershipProvenance.model_validate({
        "provider": "TEST", "environment": OwnershipEnvironment.MOCK,
        "source_reference": "TEST_EDGE", "sourced_at": datetime.now(UTC),
    })
    edge = OwnershipRelationship(
        relationship_id="E1", parent_party_id="ROOT", child_party_id="P1",
        ownership_percent=Decimal("40"),
        relationship_type=OwnershipRelationshipType.OWNERSHIP,
        provenance=provenance,
    )
    (result,) = compare_document_ownership((row,), [root, owner], [edge], ())
    assert (result.agreement, result.reason_code) == ("MISMATCH", "OWNERSHIP_DOCUMENT_CONFLICT")


# --- D-125 founding statute --------------------------------------------------------------------


def government_confirmed(bundle, case_id: UUID) -> bool:
    from app.services.government_status import government_status_confirmed

    case = bundle.onboarding.get(case_id)
    return government_status_confirmed(
        case,
        [item for item in bundle.documents.list_for_case(case_id) if item.is_current_evidence],
        confidence_threshold=float(case.policy_snapshot.idp_review_confidence_threshold),
    )


@pytest.mark.parametrize(
    "statute",
    [
        "Demo Parks FYP Test Authority Act",
        "demo parks fyp test authority act",
        "  DEMO  PARKS FYP Test Authority Act 2099 ",
        "Demo Parks FYP Test Authority Act (fictional FYP test instrument)",
    ],
    ids=["exact", "case", "whitespace-and-year", "bracketed"],
)
def test_government_statute_equal_after_normalisation_is_confirmed(statute):
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = government_at_status(client)
        response = confirm_government(client, current, founding_statute=statute)
        assert response.status_code == 200, response.json()
        status = response.json()["entity_type_basis"]["government_status"]
        assert status["state"] == "CONFIRMED"
        assert status["founding_statute"] == statute.strip()
        assert status["statute_section"] is None
        assert status["government_body_type"] == "STATUTORY_BOARD"
        assert status["statute_match"] == "MATCHED_AFTER_NORMALISATION"
        confirmation = bundle.onboarding.get(
            UUID(current["case"]["case_id"])
        ).government_status_confirmation
        assert confirmation.founding_statute == statute.strip()
        assert confirmation.statute_section is None


def test_government_statute_section_is_optional_and_stored_when_given():
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = government_at_status(client)
        response = confirm_government(
            client, current, founding_statute="demo parks fyp test authority act",
            statute_section=" s 3 ", government_body_type="MINISTRY_OR_ORGAN_OF_STATE",
        )
        assert response.status_code == 200, response.json()
        status = response.json()["entity_type_basis"]["government_status"]
        assert status["statute_section"] == "s 3"
        assert status["government_body_type"] == "MINISTRY_OR_ORGAN_OF_STATE"
        case = bundle.onboarding.get(UUID(current["case"]["case_id"]))
        assert case.government_status_confirmation.statute_section == "s 3"
        [event] = [item for item in case.events if item.code == "GOVERNMENT_STATUS_CONFIRMED"]
        assert event.message == (
            "The RM confirmed Government status from a reviewed document, founded under "
            "demo parks fyp test authority act, s 3; this is not approval."
        )


def test_government_confirmation_event_without_a_section():
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = government_at_status(client)
        assert confirm_government(client, current).status_code == 200
        case = bundle.onboarding.get(UUID(current["case"]["case_id"]))
        [event] = [item for item in case.events if item.code == "GOVERNMENT_STATUS_CONFIRMED"]
        assert event.message == (
            "The RM confirmed Government status from a reviewed document, founded under "
            "Demo Parks FYP Test Authority Act; this is not approval."
        )


@pytest.mark.parametrize(
    "statute",
    [
        "Some Other Act", "Demo Parks FYP Test Authority", "Demo Parks FYP Test Authority Bill",
        # Gate L1: bracketed text that is not on the document is a mismatch, not a note.
        "Demo Parks FYP Test Authority Act (any note)",
    ],
)
def test_government_statute_mismatch_saves_nothing(statute):
    with lane(GOVERNMENT) as (client, _, target, bundle):
        current = government_at_status(client)
        case_id = UUID(current["case"]["case_id"])
        case_before = bundle.onboarding.get(case_id)
        automation_before = bundle.automation.get_for_case(case_id)
        clm_before = bundle.clm.get_for_case(case_id)
        response = confirm_government(client, current, founding_statute=statute)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "GOVERNMENT_STATUTE_MISMATCH"
        assert bundle.onboarding.get(case_id) == case_before  # no confirmation, no event
        assert bundle.automation.get_for_case(case_id) == automation_before
        assert bundle.clm.get_for_case(case_id) == clm_before
        after = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert after["entity_type_basis"]["government_status"]["state"] == (
            "CONFIRMATION_REQUIRED"
        )
        assert blockers(after) == ["GOVERNMENT_STATUS_REQUIRED"]
        assert [call[0] for call in target.calls] == ["GET"]
        # The same case still confirms with the right statute afterwards.
        assert confirm_government(client, after).status_code == 200


@pytest.mark.parametrize(
    "change",
    [
        {"founding_statute": None},
        {"founding_statute": ""},
        {"founding_statute": "   "},
        {"founding_statute": "ab"},
        {"founding_statute": "A" * 201},
        {"founding_statute": "Demo Parks FYP\nTest Authority Act"},
        {"founding_statute": 42},
        {"government_body_type": None},
        {"government_body_type": "STATUTORY BOARD"},
        {"government_body_type": "GOVERNMENT_LINKED_COMPANY"},
        {"statute_section": "s" * 41},
        {"statute_section": "s\t3"},
        {"unexpected": "value"},
    ],
    ids=[
        "statute-missing", "statute-empty", "statute-blank", "statute-short", "statute-long",
        "statute-newline", "statute-not-text", "body-missing", "body-label", "body-unknown",
        "section-long", "section-control", "extra-field",
    ],
)
def test_government_statute_request_validation_gives_422(change):
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = government_at_status(client)
        status = current["entity_type_basis"]["government_status"]
        payload = {
            "document_id": status["document_id"],
            "document_event_count": status["document_event_count"],
            "expected_automation_version": current["version"],
            "expected_case_event_count": len(current["case"]["events"]),
            **STATUTE,
        }
        for key, value in change.items():
            if value is None:
                payload.pop(key, None)
            else:
                payload[key] = value
        response = client.post(
            f"/api/clm/zero-touch/cases/{current['case']['case_id']}/government-status-confirmation",
            json=payload,
        )
        assert response.status_code == 422, response.json()
        case = bundle.onboarding.get(UUID(current["case"]["case_id"]))
        assert case.government_status_confirmation is None
        assert len(case.events) == len(current["case"]["events"])


def test_government_blank_section_is_stored_as_none():
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = government_at_status(client)
        assert confirm_government(client, current, statute_section="   ").status_code == 200
        case = bundle.onboarding.get(UUID(current["case"]["case_id"]))
        assert case.government_status_confirmation.statute_section is None


def test_a_confirmation_without_a_statute_no_longer_counts():
    """A pre-D-125 (schema-19) confirmation loads but must be confirmed again."""
    from app.domain.models import GovernmentStatusConfirmation

    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = confirm_government(client, government_at_status(client)).json()
        case_id = UUID(current["case"]["case_id"])
        assert government_confirmed(bundle, case_id)
        case = bundle.onboarding.get(case_id)
        old_shape = GovernmentStatusConfirmation.model_validate(
            case.government_status_confirmation.model_dump(
                exclude={"founding_statute", "statute_section", "government_body_type",
                         "statute_match"}
            )
        )
        assert old_shape.founding_statute is None and old_shape.statute_match is None
        bundle.onboarding.save(
            case.model_copy(update={"government_status_confirmation": old_shape})
        )
        assert not government_confirmed(bundle, case_id)
        after = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        status = after["entity_type_basis"]["government_status"]
        assert status["state"] == "CONFIRMATION_REQUIRED"
        assert status["founding_statute"] is None and status["confirmed_by_actor_id"] is None


def _strip_statute(bundle, case_id: UUID) -> None:
    """Rewrite the stored confirmation into its pre-D-125 (schema-19) shape."""
    from app.domain.models import GovernmentStatusConfirmation

    case = bundle.onboarding.get(case_id)
    old_shape = GovernmentStatusConfirmation.model_validate(
        case.government_status_confirmation.model_dump(
            exclude={"founding_statute", "statute_section", "government_body_type",
                     "statute_match"}
        )
    )
    bundle.onboarding.save(case.model_copy(update={"government_status_confirmation": old_shape}))


def test_an_old_confirmation_past_the_hold_is_reconfirmed_after_continue():
    """Gate M1: a pre-D-125 confirmation on a case already at target confirmation."""
    with lane(GOVERNMENT) as (client, _, target, bundle):
        current = confirm_government(client, government_at_status(client)).json()
        case_id = UUID(current["case"]["case_id"])
        assert blockers(current) == ["TARGET_CONFIRMATION_REQUIRED"]
        assert current["entity_type_basis"]["government_status"]["resume_required"] is False
        _strip_statute(bundle, case_id)

        stale = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        status = stale["entity_type_basis"]["government_status"]
        assert status["state"] == "CONFIRMATION_REQUIRED"
        assert status["resume_required"] is True
        # The form alone is still refused: there is no open Government hold to resolve.
        refused = confirm_government(client, stale)
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "ZERO_TOUCH_GOVERNMENT_STATUS_NOT_ALLOWED"

        # The existing resume reopens the Government step without any target write.
        resumed = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/resume",
            headers={
                "X-Automation-Id": stale["automation_id"],
                "X-Automation-Version": str(stale["version"]),
                "X-Clm-Version": str(stale["clm"]["version"]),
                "X-Case-Event-Count": str(len(stale["case"]["events"])),
            },
        )
        assert resumed.status_code == 200, resumed.json()
        reopened = resumed.json()
        assert blockers(reopened) == ["GOVERNMENT_STATUS_REQUIRED"]
        assert reopened["entity_type_basis"]["government_status"]["state"] == (
            "CONFIRMATION_REQUIRED"
        )
        assert reopened["entity_type_basis"]["government_status"]["resume_required"] is False
        assert bundle.onboarding.get(case_id).target_dispatch_confirmation is None

        confirmed = confirm_government(client, reopened)
        assert confirmed.status_code == 200, confirmed.json()
        assert blockers(confirmed.json()) == ["TARGET_CONFIRMATION_REQUIRED"]
        assert confirmed.json()["entity_type_basis"]["government_status"]["state"] == "CONFIRMED"
        assert government_confirmed(bundle, case_id)
        assert [call[0] for call in target.calls] == ["GET"]


def test_resume_is_not_offered_while_the_government_hold_is_open():
    with lane(GOVERNMENT) as (client, _, _, _):
        current = government_at_status(client)
        status = current["entity_type_basis"]["government_status"]
        assert status["state"] == "CONFIRMATION_REQUIRED"
        assert status["resume_required"] is False


@pytest.mark.parametrize(
    "partial",
    [
        {"founding_statute": "Demo Parks FYP Test Authority Act"},
        {"government_body_type": "STATUTORY_BOARD"},
        {"statute_match": "MATCHED_AFTER_NORMALISATION"},
        {"founding_statute": "Demo Parks FYP Test Authority Act",
         "government_body_type": "STATUTORY_BOARD"},
        {"statute_section": "s 3"},
    ],
)
def test_a_half_recorded_statute_is_refused(partial):
    from pydantic import ValidationError

    from app.domain.models import GovernmentStatusConfirmation

    base = {
        "confirmation_id": "00000000-0000-4000-8000-000000000001",
        "actor_id": "ethan-tan",
        "confirmed_at": NOW,
        "case_event_count": 1,
        "document_id": "00000000-0000-4000-8000-000000000002",
        "document_event_count": 1,
        "evidence_fingerprint": "0" * 64,
    }
    with pytest.raises(ValidationError):
        GovernmentStatusConfirmation.model_validate({**base, **partial})


def test_a_changed_document_still_invalidates_a_statute_confirmation():
    with lane(GOVERNMENT) as (client, _, _, bundle):
        current = confirm_government(client, government_at_status(client)).json()
        case_id = UUID(current["case"]["case_id"])
        assert government_confirmed(bundle, case_id)
        case = bundle.onboarding.get(case_id)
        [document] = [
            item for item in bundle.documents.list_for_case(case_id) if item.is_current_evidence
        ]
        changed = document.model_copy(update={"events": (*document.events, document.events[-1])})
        from app.services.government_status import government_status_confirmed

        assert not government_status_confirmed(
            case, [changed],
            confidence_threshold=float(case.policy_snapshot.idp_review_confidence_threshold),
        )
        assert case.government_status_confirmation.founding_statute is not None
