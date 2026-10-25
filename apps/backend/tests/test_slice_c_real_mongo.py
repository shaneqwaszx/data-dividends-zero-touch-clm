"""Physical strict-codec restart of supported partial reconciliation, synthetic only."""

import os

import pytest
from fastapi.testclient import TestClient
from test_phase11_reconciliation import FieldOverrideIdp, attach, current_discrepancy
from test_phase12_real_mongo import (
    TEXT_PROFILE,
    _complete_intake,
    _create_case,
    _install_counting_connectors,
    _open_store,
    _upload_text,
    isolated_mongo_settings,  # noqa: F401
)
from test_phase24b_interrupted_retry import restore_memory_snapshot, snapshot_of
from test_slice_c_blocker_recovery import system

import app.composition as composition
from app.domain.documents import DocumentFieldKey
from app.domain.reconciliation import ReconciliationDecisionAction, ReconciliationField
from app.main import create_app

pytestmark = pytest.mark.skipif(
    not os.environ.get("PHASE12_MONGO_URI"), reason="Disposable physical Mongo is not configured"
)


def test_existing_customer_confirmation_and_document_review_survive_mongo_restart(
    isolated_mongo_settings,  # noqa: F811
):
    from pydantic import SecretStr
    from test_goldtier_xpi_sandbox import FakeXpiTransport

    from app.config import Settings
    from app.connectors.goldtier_xpi import GoldTierXpiHttpResponse

    settings = Settings(_env_file=None, **{
        **isolated_mongo_settings.model_dump(),
        "goldtier_connector_mode": "sandbox",
        "goldtier_sandbox_base_url": "https://sandbox.goldtier.invalid",
        "goldtier_sandbox_environment": "synthetic",
        "goldtier_sandbox_user_id": SecretStr("synthetic-offline-user"),
        "goldtier_sandbox_allow_writes": True,
    })
    transport = FakeXpiTransport([GoldTierXpiHttpResponse(200, [{
        "goldTierId": 143878, "legalName": "MERLION CIRCULAR LABS PTE. LTD.",
    }])])
    with TestClient(create_app(settings, goldtier_transport=transport)) as first:
        created = first.post("/api/clm/zero-touch/cases", json={
            "uen": "202400001A", "legal_name": "MERLION CIRCULAR LABS PTE. LTD.",
            "country_of_incorporation": "SG",
        })
        assert created.status_code == 201
        case_id = created.json()["case"]["case_id"]
        uploaded = _upload_text(
            first, case_id, TEXT_PROFILE.replace("MERLION CIRCULAR LABS PTE. LTD.",
                                                "DIFFERENT SYNTHETIC NAME"),
            name="synthetic-existing-review.txt",
        )
        _complete_intake(first, case_id, expected_count=1)
        review = first.post(
            f"/api/onboarding/cases/{case_id}/documents/{uploaded['document_id']}/reviews",
            json={"field_key": "legal_name", "decision": "CORRECTED",
                  "corrected_value": "MERLION CIRCULAR LABS PTE. LTD."},
        )
        assert review.status_code == 200
        current = first.get(f"/api/clm/zero-touch/cases/{case_id}").json()
        assert current["current_stage"] == "GOLDTIER_SEARCH"
        confirmed = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/confirm-existing-customer",
            json={
                "search_request_id": current["clm"]["target_search_checkpoint"]["request_id"],
                "expected_automation_version": current["version"],
                "expected_clm_version": current["clm"]["version"],
                "expected_case_event_count": len(current["case"]["events"]),
                "rationale": "Synthetic creator compared registry and document evidence.",
            },
        )
        assert confirmed.status_code == 200
        checkpoint = confirmed.json()["clm"]["target_search_checkpoint"]
        assert checkpoint["disposition"] == "CONFIRMED_EXISTING"
        assert checkpoint["selected_party_id"] == "143878"
        assert checkpoint["confirmation"]["actor_id"] == "maya-lim"
        assert len(transport.calls) == 1
    after_restart = FakeXpiTransport()
    with TestClient(create_app(settings, goldtier_transport=after_restart)) as second:
        reopened = second.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert reopened.status_code == 200
        assert reopened.json()["clm"]["target_search_checkpoint"] == checkpoint
        assert reopened.json()["case"]["goldtier_result"] is None
        documents = second.get(f"/api/onboarding/cases/{case_id}/documents").json()
        field = next(item for item in documents[0]["fields"] if item["field_key"] == "legal_name")
        assert field["review_status"] == "CORRECTED"
        assert after_restart.calls == []


def test_partial_reconciliation_survives_physical_store_restart(
    isolated_mongo_settings,  # noqa: F811 - reuse the guarded generated-DB fixture
    monkeypatch,
):
    _, zero, _, target, _ = system(monkeypatch)
    case_id = zero.create_case("202400001A").case_id
    paused = attach(
        zero,
        case_id,
        FieldOverrideIdp(
            {
                DocumentFieldKey.LEGAL_NAME: "DIFFERENT PTE. LTD.",
                DocumentFieldKey.REGISTERED_ADDRESS: "99 OTHER ROAD, 999999, SG",
            }
        ),
    )
    reconciliation = zero._reconciliation.get(case_id=case_id)
    first = current_discrepancy(reconciliation, ReconciliationField.LEGAL_NAME)
    pending = zero.resolve_reconciliation_discrepancy(
        case_id=case_id,
        discrepancy_id=first.discrepancy_id,
        action=ReconciliationDecisionAction.USE_DOCUMENT_VALUE,
        expected_automation_version=paused.version,
        expected_reconciliation_version=reconciliation.version,
        evidence_fingerprint=first.evidence_fingerprint,
    )
    assert len(pending.active_exceptions) == 1
    assert target.calls == ["search"]
    snapshot = snapshot_of(zero, case_id)
    store = _open_store(isolated_mongo_settings)
    try:
        assert store.create(snapshot) == snapshot
    finally:
        store.close()
    restarted = _open_store(isolated_mongo_settings)
    try:
        restored = restarted.get(case_id)
        assert restored == snapshot
        _, recovered, recovery_target = restore_memory_snapshot(restored)
        current = recovered._reconciliation.get(case_id=case_id)
        last = current.open_discrepancies[0]
        resumed = recovered.resolve_reconciliation_discrepancy(
            case_id=case_id,
            discrepancy_id=last.discrepancy_id,
            action=ReconciliationDecisionAction.KEEP_REGISTRY_VALUE,
            expected_automation_version=pending.version,
            expected_reconciliation_version=current.version,
            evidence_fingerprint=last.evidence_fingerprint,
        )
        assert not any(item.stage == "DOCUMENT" for item in resumed.active_exceptions)
        assert (
            sum(
                item.status == "RESOLVED" for item in resumed.exceptions if item.stage == "DOCUMENT"
            )
            == 2
        )
        assert recovered.start(case_id=case_id).version == resumed.version
        assert recovery_target.calls == []
        # Physical bytes retained both the resolved decision and remaining current binding.
        assert restarted.get(case_id) == snapshot
    finally:
        restarted.close()


def test_mongo_composed_partial_resolution_restarts_and_resumes_without_replay(
    isolated_mongo_settings,  # noqa: F811 - guarded generated-DB fixture
    monkeypatch,
):
    counters = _install_counting_connectors(monkeypatch)
    settings = isolated_mongo_settings.model_copy(update={"registry_cache_mode": "auto"})
    target_calls = []
    for name in ("search_party", "create_shell_customer", "create_policy", "amend_party"):
        original = getattr(composition.MockGoldTierConnector, name)

        def record(self, *args, _original=original, _name=name, **kwargs):
            target_calls.append(_name)
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(composition.MockGoldTierConnector, name, record)
    conflict = TEXT_PROFILE.replace(
        "MERLION CIRCULAR LABS PTE. LTD.", "DIFFERENT PTE. LTD."
    ).replace("18 INNOVATION WAY, #04-01, 018956, SG", "99 OTHER ROAD, 999999, SG")

    def resolve(client, case_id, current, discrepancy, action):
        response = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/reconciliation/"
            f"discrepancies/{discrepancy['discrepancy_id']}/resolve",
            json={
                "action": action,
                "expected_automation_version": current["version"],
                "expected_reconciliation_version": current["reconciliation"]["version"],
                "evidence_fingerprint": discrepancy["evidence_fingerprint"],
            },
        )
        assert response.status_code == 200
        return response.json()

    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        _upload_text(first, case_id, conflict, name="Synthetic-conflicts.txt")
        paused = _complete_intake(first, case_id, expected_count=1)
        discrepancies = paused["reconciliation"]["discrepancies"]
        opened = [item for item in discrepancies if item["status"] == "OPEN"]
        assert len(opened) == 2
        legal_name = next(item for item in opened if item["field_name"] == "legal_name")
        acquired = paused["case"]["registry_acquisition"]
        assert paused["case"]["registry_evidence_binding"] is not None
        pending = resolve(first, case_id, paused, legal_name, "USE_DOCUMENT_VALUE")
        assert pending["case"]["registry_evidence_binding"] is None
        assert pending["case"]["registry_acquisition"] == acquired
        assert (
            len([item for item in pending["active_exceptions"] if item["stage"] == "DOCUMENT"]) == 1
        )
        store = _open_store(settings)
        try:
            snapshot = store.get(case_id)
            assert snapshot is not None and snapshot.automation is not None
            active = snapshot.automation.active_exceptions[0]
            assert all(
                item.evidence_version == active.evidence_version for item in active.decisions
            )
        finally:
            store.close()
    calls_after_partial = dict(counters)
    assert calls_after_partial["goldtier"] == 1
    assert target_calls == ["search_party"]

    with TestClient(create_app(settings)) as restarted:
        restored = restarted.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert restored.status_code == 200
        current = restored.json()
        assert current["version"] == pending["version"]
        assert counters == calls_after_partial
        remaining = next(
            item for item in current["reconciliation"]["discrepancies"] if item["status"] == "OPEN"
        )
        resumed = resolve(restarted, case_id, current, remaining, "KEEP_REGISTRY_VALUE")
        assert not any(item["stage"] == "DOCUMENT" for item in resumed["active_exceptions"])
        history = [item for item in resumed["historical_exceptions"] if item["stage"] == "DOCUMENT"]
        assert len(history) == 2 and all(item["status"] == "RESOLVED" for item in history)
        before_resume = dict(counters)
        repeated = restarted.post(f"/api/clm/zero-touch/cases/{case_id}/resume", json={})
        assert repeated.status_code == 200
        assert repeated.json()["version"] == resumed["version"]
        assert counters == before_resume
        # Selecting a new legal name invalidates Search; normal readiness rechecks it.
        # Both calls are read-only. Restart and repeated resume add no target replay.
        assert counters["goldtier"] == 2
        assert target_calls == ["search_party", "search_party"]


def test_mixed_reconciliation_retires_resolved_sibling_across_mongo_restart(
    isolated_mongo_settings,  # noqa: F811 - guarded generated-DB fixture
    monkeypatch,
):
    counters = _install_counting_connectors(monkeypatch)
    settings = isolated_mongo_settings
    target_calls = []
    for name in ("search_party", "create_shell_customer", "create_policy", "amend_party"):
        original = getattr(composition.MockGoldTierConnector, name)

        def record(self, *args, _original=original, _name=name, **kwargs):
            target_calls.append(_name)
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(composition.MockGoldTierConnector, name, record)
    mixed = TEXT_PROFILE.replace("MERLION CIRCULAR LABS PTE. LTD.", "DIFFERENT PTE. LTD.").replace(
        "Country: SG\n", ""
    )

    def current_missing_field(summary):
        document = [item for item in summary["active_exceptions"] if item["stage"] == "DOCUMENT"]
        assert len(document) == 1
        active = document[0]
        assert active["blocker_code"] == "DOCUMENT_REQUIRED_FIELD_MISSING"
        assert active["blocker_codes"] == ["DOCUMENT_REQUIRED_FIELD_MISSING"]
        assert [item["metadata"]["blocker_code"] for item in active["decisions"]] == [
            "DOCUMENT_REQUIRED_FIELD_MISSING"
        ]
        assert all(
            item["evidence_version"] == active["evidence_version"] for item in active["decisions"]
        )
        intervention = next(
            item
            for item in summary["interventions"]
            if item["blocker_code"] == active["blocker_code"]
        )
        assert [item["metadata"]["blocker_code"] for item in intervention["decisions"]] == [
            "DOCUMENT_REQUIRED_FIELD_MISSING"
        ]
        return active

    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        _upload_text(first, case_id, mixed, name="Synthetic-mixed-fields.txt")
        paused = _complete_intake(first, case_id, expected_count=1)
        opened = [
            item for item in paused["reconciliation"]["discrepancies"] if item["status"] == "OPEN"
        ]
        assert {item["field_name"] for item in opened} == {"legal_name", "country_of_incorporation"}
        conflict = next(item for item in opened if item["field_name"] == "legal_name")
        response = first.post(
            f"/api/clm/zero-touch/cases/{case_id}/reconciliation/"
            f"discrepancies/{conflict['discrepancy_id']}/resolve",
            json={
                "action": "KEEP_REGISTRY_VALUE",
                "expected_automation_version": paused["version"],
                "expected_reconciliation_version": paused["reconciliation"]["version"],
                "evidence_fingerprint": conflict["evidence_fingerprint"],
            },
        )
        assert response.status_code == 200
        pending = response.json()
        remaining = current_missing_field(pending)
        resolved = next(
            item
            for item in pending["historical_exceptions"]
            if item["exception_id"] == conflict["discrepancy_id"]
        )
        assert resolved["status"] == "RESOLVED"
        assert resolved["resolution"] == "KEEP_REGISTRY_VALUE"
        assert resolved["blocker_code"] == "DOCUMENT_SOURCE_CONFLICT"
        assert "DOCUMENT_SOURCE_CONFLICT" in {
            item["metadata"]["blocker_code"] for item in resolved["decisions"]
        }
        decided = next(
            item
            for item in pending["reconciliation"]["discrepancies"]
            if item["discrepancy_id"] == conflict["discrepancy_id"]
        )
        assert decided["status"] == "RESOLVED"
        assert decided["decision"]["action"] == "KEEP_REGISTRY_VALUE"
        assert decided["decision"]["selected_value"] == "MERLION CIRCULAR LABS PTE. LTD."
        store = _open_store(settings)
        try:
            snapshot = store.get(case_id)
            assert snapshot is not None and snapshot.automation is not None
            assert snapshot.reconciliation is not None
            physical_remaining = snapshot.automation.active_exceptions[0]
            assert physical_remaining.blocker_codes == ("DOCUMENT_REQUIRED_FIELD_MISSING",)
            assert all(
                item.evidence_version == physical_remaining.evidence_version
                and item.exception_id == physical_remaining.exception_id
                and item.case_id == case_id
                for item in physical_remaining.decisions
            )
            physical_receipt = next(
                item.decision
                for item in snapshot.reconciliation.discrepancies
                if str(item.discrepancy_id) == conflict["discrepancy_id"]
            )
            assert physical_receipt is not None
            assert physical_receipt.evidence_fingerprint == conflict["evidence_fingerprint"]
            raw = store._collection.find_one({"_id": str(case_id)})  # noqa: SLF001
            assert raw is not None and raw["schema_version"] == 14
        finally:
            store.close()
    calls_after_resolution = dict(counters)
    assert calls_after_resolution["goldtier"] == 1
    assert target_calls == ["search_party"]

    # Each fresh application reconstructs strict persisted current and historical bindings.
    for _ in range(2):
        with TestClient(create_app(settings)) as restarted:
            retained = restarted.get(f"/api/clm/zero-touch/cases/{case_id}")
            assert retained.status_code == 200
            summary = retained.json()
            assert summary["version"] == pending["version"]
            assert current_missing_field(summary) == remaining
            assert summary["historical_exceptions"] == pending["historical_exceptions"]
            assert summary["reconciliation"] == pending["reconciliation"]
            for _ in range(2):
                repeated = restarted.post(f"/api/clm/zero-touch/cases/{case_id}/resume", json={})
                assert repeated.status_code == 200
                summary = repeated.json()
                assert summary["version"] == pending["version"]
                assert current_missing_field(summary) == remaining
                assert summary["historical_exceptions"] == pending["historical_exceptions"]
                assert summary["reconciliation"] == pending["reconciliation"]
            assert counters == calls_after_resolution
            assert target_calls == ["search_party"]
        store = _open_store(settings)
        try:
            assert store.get(case_id) == snapshot
            assert store._collection.find_one({"_id": str(case_id)}) == raw  # noqa: SLF001
        finally:
            store.close()
