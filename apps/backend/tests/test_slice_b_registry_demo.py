"""Three truthful normal journeys, exact connector counts, no external network."""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from scripts.slice_b_registry_fixture import (
    GARDEN_FIELDS,
    SECOND_FIELDS,
    CountingSyntheticRegistry,
    GardenPartnershipProtocolTransport,
)
from test_garden_protocol_fixture import fixture_settings
from test_zero_touch_exception_remediation import (
    current_document,
    ownership_request,
    successful,
)

from app.composition import build_acra_connector
from app.config import Settings
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures/uat"
OPERATIONS = ["ENTITY_PROFILE", "OFFICERS", "OWNERSHIP_PARTIES", "RELATIONSHIPS"]


def system(garden=False):
    if garden:
        settings = fixture_settings().model_copy(
            update={
                "idp_connector_mode": "local_pdf_text",
                "demo_controls_enabled": False,
                "registry_cache_mode": "mock",
                "registry_cache_freshness_seconds": 7776000,
            }
        )
        counter = GardenPartnershipProtocolTransport()
        connector = build_acra_connector(
            settings,
            transport=counter,
            marketplace_token_transport=counter,
        )
    else:
        settings = Settings(
            _env_file=None,
            app_env="test",
            clm_persistence_mode="memory",
            acra_connector_mode="mock",
            goldtier_connector_mode="mock",
            idp_connector_mode="local_pdf_text",
            demo_controls_enabled=False,
            registry_cache_mode="mock",
            registry_cache_freshness_seconds=7776000,
        )
        counter = connector = CountingSyntheticRegistry()
    return TestClient(
        create_app(
            settings,
            acra_connector=connector,
            e2e_acra_protocol_fixture=garden,
        )
    ), counter


def start(client, fields, filename):
    created = successful(
        client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": fields["UEN"],
                "legal_name": fields["Legal Name"],
                "country_of_incorporation": "SG",
            },
        ),
        201,
    )
    case_id = created["case"]["case_id"]
    successful(
        client.put(
            f"/api/clm/zero-touch/cases/{case_id}/target-classification",
            json={
                "kyc_customer_type": "Company - Private",
                "client_segment": "Corporate",
                "expected_automation_version": created["version"],
                "expected_case_event_count": len(created["case"]["events"]),
            },
        )
    )
    successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            content=(FIXTURES / filename).read_bytes(),
            headers={"Content-Type": "application/pdf", "X-Document-Name": filename},
        ),
        201,
    )
    return successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
    )


def confirm(client, current):
    case_id = current["case"]["case_id"]
    return successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/target-confirmation",
            json={
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
            },
        )
    )


def test_garden_partnership_keeps_official_boundary_and_completes_local_remediation():
    client, transport = system(garden=True)
    current = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
    case_id = current["case"]["case_id"]
    acquisition = current["case"]["registry_acquisition"]
    assert current["case"]["entity"]["party_type"] == "PARTNERSHIP"
    assert current["case"]["entity"]["registration_date"] == "1974-09-28"
    assert current["case"]["entity"]["entity_status"] is None
    assert acquisition["status"] == "PARTIAL"
    assert [item["status"] for item in acquisition["operation_results"]] == [
        "COMPLETE",
        "COMPLETE",
        "UNSUPPORTED",
        "UNSUPPORTED",
    ]
    assert len(acquisition["officers"]) == 4
    assert acquisition["ownership_parties"] == acquisition["relationships"] == []
    assert current["case"]["registry_evidence_binding"] is None
    assert transport.calls == ["TOKEN", "ENTITY_PROFILE", "ENTITY_PROFILE"]
    document = current_document(client, case_id)
    assert document["completion_method"] == "AUTO_CONFIRMED"
    assert all(item["review_status"] == "ACCEPTED" for item in document["fields"])
    before = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert before["legal_form"] == "BUSINESS_PARTNERSHIP"
    assert before["candidates"] == [] and before["relationships"] == []
    assert {item["kind"] for item in before["evidence"]} == {"ROLE"}
    assert any(item["stage"] == "OWNERSHIP" for item in current["active_exceptions"])
    payload = ownership_request(current, document)
    payload["parties"][1]["display_name"] = "Synthetic Garden Partner A"
    payload["parties"][2]["display_name"] = "Synthetic Garden Partner B"
    current = successful(
        client.post(
            f"/api/clm/zero-touch/cases/{case_id}/manual-ownership-evidence",
            json=payload,
        )
    )
    receipt = current["ownership_recovery"]["review_receipt"]
    assert (receipt["source_type"], receipt["provider_environment"], receipt["provider_name"]) == (
        "USER_SUPPLIED_DECLARATION",
        "LOCAL",
        "MANUAL_DECLARATION_POC",
    )
    assert receipt["evidence_document_id"] == document["document_id"]
    assert receipt["evidence_document_version"] == len(document["events"])
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert ownership["state"] == "ANALYZED"
    assert {Decimal(item["aggregated_ownership_percent"]) for item in ownership["candidates"]} == {
        Decimal("60"),
        Decimal("40"),
    }
    assert all(
        item["classification"] == "PROVISIONAL_UBO_CANDIDATE" for item in ownership["candidates"]
    )
    assert [item["blocker_code"] for item in current["active_exceptions"]] == [
        "TARGET_CONFIRMATION_REQUIRED",
    ]
    assert any(
        item["stage"] == "OWNERSHIP" and item["status"] == "RESOLVED"
        for item in current["historical_exceptions"]
    )
    completed = confirm(client, current)
    assert completed["status"] == "COMPLETED" and completed["active_exceptions"] == []
    assert completed["clm"]["status"] == "MOCK_GOLDTIER_SUBMITTED"
    for _ in range(2):
        retained = successful(client.get(f"/api/clm/zero-touch/cases/{case_id}"))
        assert retained["status"] == "COMPLETED" and retained["active_exceptions"] == []
        assert retained["case"]["registry_acquisition"] == acquisition
        assert retained["case"]["registry_evidence_binding"] is None
    assert transport.calls == ["TOKEN", "ENTITY_PROFILE", "ENTITY_PROFILE"]


def test_second_existing_synthetic_company_completes_with_exact_four_operation_sequence():
    client, connector = system()
    current = start(client, SECOND_FIELDS, "multiple-owner-demo-client.pdf")
    case_id = current["case"]["case_id"]
    assert connector.calls == [(op, "202400008H") for op in OPERATIONS]
    assert current["case"]["registry_acquisition"]["status"] == "COMPLETE"
    assert current["case"]["registry_evidence_binding"]["disposition"] == "PROVIDER_FETCH"
    assert current_document(client, case_id)["completion_method"] == "AUTO_CONFIRMED"
    ownership = successful(client.get(f"/api/onboarding/cases/{case_id}/ownership"))
    assert ownership["provider_environment"] == "MOCK"
    assert ownership["state"] == "ANALYZED"
    assert {Decimal(item["ownership_percent"]) for item in ownership["relationships"]} == {
        Decimal("50"),
        Decimal("30"),
        Decimal("20"),
    }
    assert confirm(client, current)["status"] == "COMPLETED"
    assert connector.calls == [(op, "202400008H") for op in OPERATIONS]


def test_third_merlion_owner_warmed_cache_uses_zero_new_acra_calls():
    client, connector = system()
    fields = {"Legal Name": "MERLION CIRCULAR LABS PTE. LTD.", "UEN": "202400001A"}
    warm = start(client, fields, "clean-company-profile.pdf")  # deliberately unsubmitted target
    before = list(connector.calls)
    assert before == [(op, "202400001A") for op in OPERATIONS]
    hit = start(client, fields, "clean-company-profile.pdf")
    assert connector.calls == before
    assert hit["case"]["case_id"] != warm["case"]["case_id"]
    binding = hit["case"]["registry_evidence_binding"]
    assert binding["disposition"] == "CACHE_HIT"
    assert set(binding) == {
        "disposition",
        "bound_to_case_at",
        "expires_at",
        "freshness_policy_id",
        "freshness_policy_version",
        "freshness_duration_seconds",
        "freshness_comparator",
    }
    assert binding["freshness_duration_seconds"] == 7776000
    assert binding["freshness_comparator"] == "EVALUATION_NOW_LT_EXPIRES_AT"
    assert hit["case"]["registry_acquisition"] == warm["case"]["registry_acquisition"]
    assert hit["case"]["registry_acquisition"]["status"] == "COMPLETE"
    assert all(
        item["provenance"]["environment"] == "MOCK"
        for item in hit["case"]["registry_acquisition"]["operation_results"]
    )
    assert confirm(client, hit)["status"] == "COMPLETED"
    assert connector.calls == before


@pytest.mark.parametrize(
    "filename,fields",
    [
        ("garden-partnership-reviewed-client.pdf", GARDEN_FIELDS),
        ("multiple-owner-demo-client.pdf", SECOND_FIELDS),
    ],
)
def test_slice_b_client_pdf_has_valid_structure_and_exact_intake_labels(filename, fields):
    reader = PdfReader(FIXTURES / filename, strict=True)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "SYNTHETIC TEST DATA" in text and "not an ACRA extract" in text
    for key, value in fields.items():
        assert f"{key}: {value}" in text


@pytest.mark.parametrize(
    "stale_operation,expected",
    [
        ("OFFICERS", ["OFFICERS"]),
        ("OWNERSHIP_PARTIES", ["OWNERSHIP_PARTIES", "RELATIONSHIPS"]),
        ("RELATIONSHIPS", ["RELATIONSHIPS"]),
        ("ENTITY_PROFILE", OPERATIONS),
    ],
)
def test_only_stale_operations_and_their_required_dependents_are_refetched(
    stale_operation, expected
):
    from datetime import timedelta

    from test_phase16_registry_cache import (
        CountingAcraConnector,
        CountingRepository,
        MutableClock,
        identity,
    )

    from app.connectors.registry import AcraRegistryProviderAdapter
    from app.domain.models import RegistryFreshnessPolicy
    from app.domain.policy import RegistryPolicySnapshot
    from app.services.registry_acquisition import RegistryAcquisitionCoordinator

    clock = MutableClock()
    connector = CountingAcraConnector(clock)
    method = {
        "ENTITY_PROFILE": "fetch_company",
        "OFFICERS": "fetch_officers",
        "OWNERSHIP_PARTIES": "fetch_ownership_parties",
        "RELATIONSHIPS": "fetch_relationships",
    }[stale_operation]
    original = getattr(connector, method)

    def older(identifier):
        return original(identifier).model_copy(
            update={"retrieved_at": clock.value - timedelta(seconds=20)}
        )

    setattr(connector, method, older)
    provider = AcraRegistryProviderAdapter(connector, clock=clock, cache_identity=identity())
    coordinator = RegistryAcquisitionCoordinator(
        CountingRepository(), RegistryFreshnessPolicy(), clock=clock
    )
    policy = RegistryPolicySnapshot(freshness_seconds=60)
    first = coordinator.acquire(provider, "202400001A", case_policy=policy, policy_version=1)
    assert first.binding is not None
    before = dict(connector.calls)
    setattr(connector, method, original)
    clock.value += timedelta(seconds=40)  # exact expiry of only the older operation
    refreshed = coordinator.acquire(provider, "202400001A", case_policy=policy, policy_version=1)
    assert refreshed.binding.disposition.value == "PROVIDER_FETCH"
    assert {
        operation: connector.calls[operation] - before[operation] for operation in OPERATIONS
    } == {operation: int(operation in expected) for operation in OPERATIONS}
    before = dict(connector.calls)
    repeat = coordinator.acquire(provider, "202400001A", case_policy=policy, policy_version=1)
    assert repeat.binding.disposition.value == "CACHE_HIT"
    assert connector.calls == before and coordinator.active_lock_count == 0


def test_garden_fresh_partial_prefix_reuse_never_claims_complete_case_cache_hit():
    client, transport = system(garden=True)
    first = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
    before = list(transport.calls)
    second = start(client, GARDEN_FIELDS, "garden-partnership-reviewed-client.pdf")
    assert before == ["TOKEN", "ENTITY_PROFILE", "ENTITY_PROFILE"]
    assert transport.calls == before
    assert first["case"]["case_id"] != second["case"]["case_id"]
    assert second["case"]["registry_acquisition"] == first["case"]["registry_acquisition"]
    assert second["case"]["registry_acquisition"]["status"] == "PARTIAL"
    assert second["case"]["registry_evidence_binding"] is None
    assert any(item["stage"] == "OWNERSHIP" for item in second["active_exceptions"])
