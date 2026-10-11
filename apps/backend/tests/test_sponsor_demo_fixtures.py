"""Additive native annexes through actual configured owners and offline Sandbox XPI."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from scripts.s3_sandbox_fixture import OfflineS3SandboxTransport
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.synthetic_company_pack_test_transport import NoMarketplaceRequests
from scripts.zero_touch_happy_path_fixtures import ALL_COMPANIES, SPONSOR_DEMO_COMPANIES
from test_slice_b_registry_demo import confirm
from test_synthetic_company_pack import marketplace_seams, settings

from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.services.registry_cache_repository import InMemoryRegistrySnapshotRepository

DOCUMENTS = Path(__file__).parent / "fixtures/uat/zero-touch-database"


def test_explicit_demo_seed_preserves_legacy_and_unknown_neighbor():
    store = InMemoryRegistrySnapshotRepository()
    now = datetime.now(UTC)
    assert manage_fixtures(store, now=now, seed=True)["created"] == len(ALL_COMPANIES)
    originals = {c.uen: store.get(c.snapshot(now).key) for c in ALL_COMPANIES}
    assert (
        manage_fixtures(store, now=now, seed=True, companies=SPONSOR_DEMO_COMPANIES)["created"] == 1
    )
    assert (
        manage_fixtures(store, now=now, seed=False, companies=SPONSOR_DEMO_COMPANIES)["fresh"] == 4
    )
    assert all(store.get(c.snapshot(now).key) == originals[c.uen] for c in ALL_COMPANIES)
    assert SPONSOR_DEMO_COMPANIES[0].uen == "202400019S"
    assert "202400018R" not in {c.uen for c in (*ALL_COMPANIES, *SPONSOR_DEMO_COMPANIES)}


def exercise_native_registry_annex(company, *, configured=None):
    configured = configured or settings(
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url="https://sandbox.goldtier.invalid",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id="synthetic-offline-user",
        goldtier_sandbox_allow_writes=True,
    )
    bundle = build_persistence_bundle(configured)
    manage_fixtures(
        bundle.registry_snapshots,
        now=datetime.now(UTC),
        seed=True,
        companies=SPONSOR_DEMO_COMPANIES,
    )
    marketplace = NoMarketplaceRequests()
    target = OfflineS3SandboxTransport("success")
    target.name, target.uen = company.name, company.uen
    with (
        marketplace_seams(marketplace),
        patch("app.main.build_persistence_bundle", return_value=bundle),
        TestClient(create_app(configured, goldtier_transport=target)) as client,
    ):
        created = client.post(
            "/api/clm/zero-touch/cases",
            json={
                "uen": company.uen,
                "legal_name": company.name,
                "country_of_incorporation": "SG",
            },
        )
        assert created.status_code == 201, created.text
        current = created.json()
        case_id = current["case"]["case_id"]
        assert current["case"]["registry_evidence_binding"]["disposition"] == "CACHE_HIT"
        assert (
            current["case"]["registry_evidence_binding"]["synthetic_seed_namespace"]
            == "LOCAL_SYNTHETIC_UAT_V1"
        )
        assert current["clm"]["target_search_checkpoint"]["disposition"] == "NO_MATCH"
        uploaded = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            content=(DOCUMENTS / company.document_name).read_bytes(),
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": company.document_name,
            },
        )
        assert uploaded.status_code == 201, uploaded.text
        started = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/complete",
            json={"expected_document_count": 1},
        )
        assert started.status_code == 200, started.text
        current = started.json()
        assert [e["blocker_code"] for e in current["active_exceptions"]] == [
            "TARGET_CONFIRMATION_REQUIRED"
        ]
        assert current["metrics"]["human_interventions"] == 0
        document = client.get(f"/api/onboarding/cases/{case_id}/documents").json()[0]
        assert document["completion_method"] == "AUTO_CONFIRMED"
        assert len(document["fields"]) == 4
        assert all(
            f["comparison_status"] == "MATCH"
            and f["review_status"] == "ACCEPTED"
            and f["extraction_method"] == "NATIVE_PDF_TEXT"
            and f["extraction_quality"] == "HIGH"
            and Decimal(str(f["confidence"])) == Decimal("0.97")
            and f["provenance"]["page_number"] == 1
            and f["provenance"]["source_reference"] == "UNIQUE_LABELLED_TEXT"
            and len(f["candidates"]) == 1
            and f["candidates"][0]["page_number"] == 1
            and f["candidates"][0]["source_reference"].startswith("PAGE_1_LINE_")
            for f in document["fields"]
        ), [
            {
                key: f[key]
                for key in (
                    "field_key",
                    "provenance",
                    "extraction_method",
                    "extraction_quality",
                    "candidates",
                )
            }
            for f in document["fields"]
        ]
        assert document["ownership_observations"] == []
        retained = bundle.documents.get(UUID(document["document_id"]))
        assert retained is not None and len(retained.classification_observations) == 2
        assert all(
            o.extraction_method == "NATIVE_PDF_TEXT"
            and o.extraction_quality == "HIGH"
            and o.page_number == 1
            and o.source_reference.startswith("PAGE_1_LINE_")
            for o in retained.classification_observations
        )
        assert all(
            current["target_classification"][key]["selection"]["source"] == "DOCUMENT"
            for key in ("kyc_customer_type", "client_segment")
        )
        ownership = client.get(f"/api/onboarding/cases/{case_id}/ownership").json()
        assert ownership["state"] == "ANALYZED"
        assert ownership["manual_review_receipt"] is None
        assert {
            c["party"]["party_id"]: Decimal(c["aggregated_ownership_percent"])
            for c in ownership["candidates"]
        } == {key: Decimal(value) for key, value in company.expected}
        assert current["clm"]["readiness"]["blockers"] == []
        assert target.counts == {"SEARCH": 1, "SHELL": 0, "POLICY": 0, "AMEND": 0, "READBACK": 0}
        final = confirm(client, current)
        assert final["status"] == "COMPLETED"
        assert final["target_submission"]["state"] == "SUBMISSION_CONFIRMED"
        assert target.counts == {"SEARCH": 2, "SHELL": 1, "POLICY": 1, "AMEND": 0, "READBACK": 1}
        client.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert target.counts == {"SEARCH": 2, "SHELL": 1, "POLICY": 1, "AMEND": 0, "READBACK": 1}
        assert marketplace.calls == []
        return case_id


@pytest.mark.parametrize("company", SPONSOR_DEMO_COMPANIES, ids=lambda c: c.code)
def test_native_registry_annex_has_automatic_evidence_exact_engine_result_and_guarded_sandbox(
    company,
):
    exercise_native_registry_annex(company)
