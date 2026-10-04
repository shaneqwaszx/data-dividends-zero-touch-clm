"""Full owner-path observation for the final target reuse demo."""

from fastapi.testclient import TestClient
from scripts.slice_f_target_fixture import build_local_reuse_fixture
from test_slice_b_registry_demo import confirm, start, system

from app.config import Settings
from app.main import create_app

FIELDS = {"UEN": "202400001A", "Legal Name": "MERLION CIRCULAR LABS PTE. LTD."}


def test_verified_reuse_owner_path():
    client, counter = system()
    first = confirm(client, start(client, FIELDS, "clean-company-profile.pdf"))
    assert first["status"] == "COMPLETED"
    # G closes the observed F limitation through the existing registry/cache owner.
    second = start(client, FIELDS, "clean-company-profile.pdf")
    assert second["clm"]["target_search_checkpoint"]["disposition"] == "EXACT_MATCH"
    done = confirm(client, second)
    assert done["status"] == "COMPLETED"
    assert (
        done["case"]["goldtier_result"]["party_id"] == first["case"]["goldtier_result"]["party_id"]
    )
    assert done["case"]["goldtier_result"]["readback_status"] == "VERIFIED"
    assert len(counter.calls) == 4
    assert done["case"]["registry_evidence_binding"]["disposition"] == "CACHE_HIT"
    registry_node = next(
        node for node in done["processing_pipeline"] if node["node_id"] == "ACRA_REGISTRY"
    )
    assert registry_node["status"] == "COMPLETE"
    assert registry_node["safe_result"] == "Registry acquisition retained"
    target = {row["operation"]: row["status"] for row in done["target_operations"]}
    assert target["SHELL"] == target["POLICY"] == "SKIPPED"
    assert target["AMEND"] == target["READBACK"] == "SUCCESS"


def test_local_reuse_fixture_uses_normal_registry_ownership_and_actual_prior_proof():
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="memory",
        acra_connector_mode="mock",
        goldtier_connector_mode="mock",
        idp_connector_mode="local_pdf_text",
        registry_cache_mode="mock",
        registry_cache_freshness_seconds=7776000,
    )
    fixture = build_local_reuse_fixture(settings)
    client = TestClient(
        create_app(
            settings,
            onboarding_service=fixture.onboarding,
            ownership_analysis_service=fixture.ownership,
            acra_connector=fixture.registry,
        )
    )
    first = confirm(client, start(client, FIELDS, "clean-company-profile.pdf"))
    second = start(client, FIELDS, "clean-company-profile.pdf")
    assert second["clm"]["target_search_checkpoint"]["disposition"] == "EXACT_MATCH"
    done = confirm(client, second)
    assert done["status"] == "COMPLETED"
    assert (
        done["case"]["goldtier_result"]["party_id"] == first["case"]["goldtier_result"]["party_id"]
    )
    assert done["case"]["goldtier_result"]["readback_status"] == "VERIFIED"
    assert len(fixture.registry.calls) == 4
