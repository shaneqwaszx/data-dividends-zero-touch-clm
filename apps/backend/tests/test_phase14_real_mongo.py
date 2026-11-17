"""Opt-in physical Mongo proof for Phase 14 projection and hard deletion."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_phase12_real_mongo import (
    _confirm_target_dispatch,
    _install_counting_connectors,
)

from app.config import Settings
from app.main import create_app
from app.persistence.composition import build_persistence_bundle
from app.persistence.errors import PersistenceConflictError

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")

DOCUMENT = b"""Legal Name: MERLION CIRCULAR LABS PTE. LTD.
UEN: 202400001A
Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG
Country: SG
"""
DOCUMENT_NAME = "evidence.txt"
DOCUMENT_CONTENT_TYPE = "text/plain"


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"user_id": user_id, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _post_document_upload(
    client: Any,
    *,
    case_id: str,
    csrf_token: str,
) -> Any:
    """Use the production intake request shape: raw body plus explicit filename."""

    return client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/intake/documents",
        content=DOCUMENT,
        headers={
            "Content-Type": DOCUMENT_CONTENT_TYPE,
            "X-Document-Name": DOCUMENT_NAME,
            "X-CSRF-Token": csrf_token,
        },
    )


def _create_completed_case(client: RawTestClient, *, csrf_token: str) -> str:
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": "STRAIGHT_THROUGH"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    uploaded = _post_document_upload(client, case_id=case_id, csrf_token=csrf_token)
    assert uploaded.status_code == 201
    completed = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 1},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert completed.status_code == 200
    confirmed = _confirm_target_dispatch(
        client, case_id, completed.json(), csrf_token=csrf_token
    )
    assert confirmed["status"] == "COMPLETED"
    return case_id


def _create_attention_case(client: RawTestClient, *, csrf_token: str) -> str:
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": "LOW_CONFIDENCE"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201
    case_id = created.json()["case"]["case_id"]
    uploaded = _post_document_upload(client, case_id=case_id, csrf_token=csrf_token)
    assert uploaded.status_code == 201
    paused = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 1},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "WAITING_FOR_REVIEW"
    return case_id


def _read_raw_envelope(collection: Any, case_id: str) -> dict[str, Any] | None:
    raw = collection.find_one({"_id": case_id})
    return deepcopy(raw) if raw is not None else None


def _assert_unrelated_envelope_preserved(
    collection: Any,
    *,
    unrelated_case_id: str,
    expected_envelope: dict[str, Any],
) -> None:
    actual_envelope = _read_raw_envelope(collection, unrelated_case_id)
    assert actual_envelope is not None
    assert actual_envelope == expected_envelope


def _prove_stale_delete_conflict(
    store: Any,
    *,
    case_id: UUID,
    stale_revision: int,
) -> None:
    with pytest.raises(PersistenceConflictError):
        store.delete(case_id, expected_revision=stale_revision, expected_nonce=None)


def test_real_mongo_projected_reads_and_completed_case_deletion_survive_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p14")
    assert database.startswith("clm_p14_") and len(database) == len("clm_p14_") + 24
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
        demo_controls_enabled=True,
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    counters = _install_counting_connectors(monkeypatch)
    try:
        with RawTestClient(create_app(settings)) as creator:
            csrf = _login(creator, "maya-lim")
            case_id = _create_completed_case(creator, csrf_token=csrf)
            unrelated_case_id = _create_completed_case(creator, csrf_token=csrf)

        before_restart_reads = counters.copy()
        with RawTestClient(create_app(settings)) as rm:
            csrf = _login(rm, "ethan-tan")
            listed = rm.get("/api/clm/zero-touch/cases")
            dashboard = rm.get("/api/clm/zero-touch/dashboard")
            assert listed.status_code == dashboard.status_code == 200
            assert {item["case_id"] for item in listed.json()} == {case_id, unrelated_case_id}
            assert all(item["completed_at"] is not None for item in listed.json())
            assert dashboard.json()["totals"]["total_cases"] == 2
            assert counters == before_restart_reads

            durable = build_persistence_bundle(settings)
            try:
                stale = durable.onboarding.get(UUID(case_id))
                assert stale is not None
                assert durable.mongo_store is not None
                target_before_update = durable.mongo_store.get(UUID(case_id))
                assert target_before_update is not None
                revision_r1 = target_before_update.revision

                updated = rm.patch(
                    f"/api/clm/zero-touch/cases/{case_id}/priority",
                    json={"priority": 7},
                    headers={"X-CSRF-Token": csrf},
                )
                assert updated.status_code == 200
                target_after_update = durable.mongo_store.get(UUID(case_id))
                assert target_after_update is not None
                revision_r2 = target_after_update.revision
                assert revision_r2 > revision_r1

                _prove_stale_delete_conflict(
                    durable.mongo_store,
                    case_id=UUID(case_id),
                    stale_revision=revision_r1,
                )
                target_after_stale_delete = durable.mongo_store.get(UUID(case_id))
                assert target_after_stale_delete is not None
                assert target_after_stale_delete.revision == revision_r2

                collection = cleanup[database][settings.mongo_case_collection]
                unrelated_envelope = _read_raw_envelope(collection, unrelated_case_id)
                assert unrelated_envelope is not None

                deleted = rm.delete(
                    f"/api/clm/zero-touch/cases/{case_id}",
                    headers={"X-CSRF-Token": csrf},
                )
                assert deleted.status_code == 204
                assert counters == before_restart_reads
                assert rm.get(f"/api/clm/zero-touch/cases/{case_id}").status_code == 404
                assert rm.get(f"/api/clm/zero-touch/cases/{unrelated_case_id}").status_code == 200
                assert [item["case_id"] for item in rm.get("/api/clm/zero-touch/cases").json()] == [
                    unrelated_case_id
                ]
                assert rm.get("/api/clm/zero-touch/dashboard").json()["totals"]["total_cases"] == 1

                with pytest.raises(PersistenceConflictError):
                    durable.onboarding.save(stale)

                assert _read_raw_envelope(collection, case_id) is None
                _assert_unrelated_envelope_preserved(
                    collection,
                    unrelated_case_id=unrelated_case_id,
                    expected_envelope=unrelated_envelope,
                )
            finally:
                durable.close()

        with RawTestClient(create_app(settings)) as restarted:
            _login(restarted, "olivia-koh")
            assert [
                item["case_id"] for item in restarted.get("/api/clm/zero-touch/cases").json()
            ] == [unrelated_case_id]
            restarted_dashboard = restarted.get("/api/clm/zero-touch/dashboard").json()
            assert restarted_dashboard["totals"]["total_cases"] == 1
            assert counters == before_restart_reads
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()


def test_real_mongo_attention_projection_and_exact_filter_survive_restart() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p14")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection="clm_case_snapshots",
        demo_controls_enabled=True,
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        with RawTestClient(create_app(settings)) as creator:
            csrf = _login(creator, "maya-lim")
            attention_case_id = _create_attention_case(creator, csrf_token=csrf)
            completed_case_id = _create_completed_case(creator, csrf_token=csrf)

        with RawTestClient(create_app(settings)) as restarted:
            _login(restarted, "ethan-tan")
            listed = restarted.get("/api/clm/zero-touch/cases")
            filtered = restarted.get(
                "/api/clm/zero-touch/cases?attention_type=DOCUMENT_LOW_CONFIDENCE"
            )

            assert listed.status_code == filtered.status_code == 200
            by_id = {item["case_id"]: item for item in listed.json()}
            assert by_id[attention_case_id]["active_exception_count"] == 1
            assert by_id[attention_case_id]["active_exception_types"] == [
                "DOCUMENT_LOW_CONFIDENCE"
            ]
            assert by_id[completed_case_id]["active_exception_types"] == []
            assert [item["case_id"] for item in filtered.json()] == [attention_case_id]
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()
