"""D-095 physical MongoDB proof for backend-computed document digests (case snapshot schema 16).

Opt-in, like every ``*_real_mongo`` suite: it runs only when ``PHASE12_MONGO_URI`` is set (see
``scripts/run_physical_mongo_tests.py``, which owns this suite). Each test uses a newly generated,
allowlisted database (``scripts/mongo_test_safety.py``: ``clm_p12_<24 hex>``) that is dropped
and verified absent afterwards; ``clm_poc`` and every other database are never touched. Only
synthetic fixtures are uploaded. A "restart" is a new application process composition with new
Mongo clients over the same database, as in the other physical suites.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from pymongo import MongoClient
from s2_legacy_schema_fixtures import drop_uen_route
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_phase12_real_mongo import TEXT_PROFILE, _complete_intake, _create_case, _open_store

from app.config import Settings
from app.main import create_app

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")

REPOSITORY = Path(__file__).resolve().parents[3]
UAT = Path(__file__).parent / "fixtures" / "uat"
FIXTURE = UAT / "clean-company-profile.pdf"
MANIFEST = REPOSITORY / "apps" / "assistant" / "ai_assistant" / "synthetic_eligibility.json"
COLLECTION = "clm_case_snapshots"


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _tampered(content: bytes) -> bytes:
    """The same file name and size, one byte changed in a text line that carries no field."""

    edited = content.replace(b"(SYNTHETIC TEST DATA)", b"(SYNTHETIC TEST DATB)", 1)
    assert edited != content and len(edited) == len(content)
    return edited


@pytest.fixture
def physical() -> Iterator[tuple[Settings, Any]]:
    """Settings for a generated allowlisted database, and that database's raw collection."""

    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p12")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        registry_cache_mode="disabled",
        acra_connector_mode="mock",
        goldtier_connector_mode="mock",
        mongo_uri=MONGO_URI,
        mongo_database=database,
        mongo_case_collection=COLLECTION,
    )
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    try:
        yield settings, client[database][COLLECTION]
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def _upload(
    client: TestClient, case_id: UUID | str, content: bytes, *, name: str, media: str
) -> dict[str, Any]:
    response = client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
        headers={"Content-Type": media, "X-Document-Name": name},
        content=content,
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _digests(client: TestClient, case_id: UUID | str) -> list[dict[str, Any]]:
    response = client.get(f"/api/onboarding/cases/{case_id}/document-digests")
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


def _documents(client: TestClient, case_id: UUID | str) -> list[dict[str, Any]]:
    response = client.get(f"/api/onboarding/cases/{case_id}/documents")
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


def _as_schema_15(collection: Any, case_id: UUID | str) -> dict[str, Any]:
    """Store the case exactly as a schema-15 writer did (the same envelope without the digest
    field, which schema 15 never had) and return a deep copy of the stored envelope."""

    raw = collection.find_one({"_id": str(case_id)})
    assert raw is not None and raw["schema_version"] == 19
    raw["schema_version"] = 15
    raw["onboarding"].pop("government_status_confirmation")  # D-101 (schema 17)
    raw["onboarding"] = drop_uen_route(raw["onboarding"])  # D-114 (schema 18)
    for document in raw["documents"]:
        document.pop("content_sha256")
        document.pop("government_status_observations")  # D-101 (schema 17)
    result = collection.replace_one({"_id": str(case_id)}, raw)
    assert result.matched_count == 1
    stored = collection.find_one({"_id": str(case_id)})
    assert stored is not None and stored["schema_version"] == 15
    return deepcopy(stored)


# --- 1. upload, storage, digest, retrieval after a restart ----------------------------------------


def test_the_uploaded_documents_digest_is_stored_and_served_after_a_restart(
    physical: tuple[Settings, Any],
) -> None:
    settings, collection = physical
    content = FIXTURE.read_bytes()
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        uploaded = _upload(first, case_id, content, name=FIXTURE.name, media="application/pdf")
        served = _digests(first, case_id)
        listed = _documents(first, case_id)
    expected = [
        {
            "document_id": uploaded["document_id"],
            "document_version": uploaded["document_version"],
            "content_sha256": _sha(content),
        }
    ]
    assert served == expected
    # The browser document list names the same record and never carries the digest.
    assert [(item["document_id"], item["document_version"]) for item in listed] == [
        (item["document_id"], item["document_version"]) for item in served
    ]
    assert "content_sha256" not in json.dumps(listed) and _sha(content) not in json.dumps(listed)
    # Physically stored at schema 16 on the document record.
    raw = collection.find_one({"_id": str(case_id)})
    assert raw is not None and raw["schema_version"] == 19
    assert [item["content_sha256"] for item in raw["documents"]] == [_sha(content)]
    store = _open_store(settings, initialize=False)
    try:
        snapshot = store.get(case_id)
        assert snapshot is not None
        assert [item.content_sha256 for item in snapshot.documents] == [_sha(content)]
    finally:
        store.close()

    with TestClient(create_app(settings)) as restarted:
        assert _digests(restarted, case_id) == expected
        assert [item["document_id"] for item in _documents(restarted, case_id)] == [
            uploaded["document_id"]
        ]
    after = collection.find_one({"_id": str(case_id)})
    assert after is not None and after["documents"][0]["content_sha256"] == _sha(content)


# --- 2. schema 15 to 16: no evidence loss, no silent rewrite, no stale fingerprints ---------------


def test_a_populated_schema_15_case_reads_as_16_without_loss_rewrite_or_stale_evidence(
    physical: tuple[Settings, Any],
) -> None:
    settings, collection = physical
    conflict = TEXT_PROFILE.replace("MERLION CIRCULAR LABS PTE. LTD.", "DIFFERENT PTE. LTD.")
    with TestClient(create_app(settings)) as first:
        case_id = _create_case(first)
        _upload(
            first, case_id, conflict.encode(), name="Synthetic-conflict.txt", media="text/plain"
        )
        paused = _complete_intake(first, case_id, expected_count=1)
    opened = [
        item for item in paused["reconciliation"]["discrepancies"] if item["status"] == "OPEN"
    ]
    discrepancy = next(item for item in opened if item["field_name"] == "legal_name")
    legacy = _as_schema_15(collection, case_id)
    # The stored case carries backend-only evidence that a lossy upgrade would drop.
    observations = [
        observation
        for item in legacy["reconciliation"]["discrepancies"]
        for observation in item["observations"]
    ]
    assert any(observation.get("raw_value") for observation in observations)
    assert any(observation.get("source_record_id") for observation in observations)

    # The physical read path upgrades to 16 and keeps every field of the stored envelope.
    store = _open_store(settings, initialize=False)
    try:
        upgraded = store.get(case_id)
        assert upgraded is not None and upgraded.schema_version == 19
        reencoded = store._encode(upgraded)  # noqa: SLF001 - the store's own serializer
    finally:
        store.close()
    expected = deepcopy(legacy)
    expected["schema_version"] = 19
    expected["onboarding"]["government_status_confirmation"] = None  # D-101 default
    expected["onboarding"]["uen_route"] = None  # D-114 default
    for document in expected["documents"]:
        document["content_sha256"] = None
        document["government_status_observations"] = []  # D-101 default
    assert reencoded == expected
    assert collection.find_one({"_id": str(case_id)}) == legacy  # reading never rewrites

    with TestClient(create_app(settings)) as restarted:
        current = restarted.get(f"/api/clm/zero-touch/cases/{case_id}")
        assert current.status_code == 200, current.text
        assert current.json()["version"] == paused["version"]
        assert current.json()["reconciliation"] == paused["reconciliation"]
        assert [item["content_sha256"] for item in _digests(restarted, case_id)] == [None]
        assert collection.find_one({"_id": str(case_id)}) == legacy  # still no silent rewrite
        # The fingerprint recorded before the upgrade is still the current one: a drifted
        # fingerprint would refuse this decision as stale.
        resolved = restarted.post(
            f"/api/clm/zero-touch/cases/{case_id}/reconciliation/"
            f"discrepancies/{discrepancy['discrepancy_id']}/resolve",
            json={
                "action": "KEEP_REGISTRY_VALUE",
                "expected_automation_version": paused["version"],
                "expected_reconciliation_version": paused["reconciliation"]["version"],
                "evidence_fingerprint": discrepancy["evidence_fingerprint"],
            },
        )
        assert resolved.status_code == 200, resolved.text
    # The first write stores schema 16; the legacy document stays digest-less, its evidence kept.
    written = collection.find_one({"_id": str(case_id)})
    assert written is not None and written["schema_version"] == 19
    assert written["documents"] == [
        {**document, "content_sha256": None, "government_status_observations": []}
        for document in legacy["documents"]
    ]


# --- 3. the document-digests route: team scope and safe 404s on Mongo ---------------------------


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text
    csrf: str = response.json()["csrf_token"]
    return csrf


def test_the_digests_route_keeps_team_scope_and_safe_404s_across_a_restart(
    physical: tuple[Settings, Any],
) -> None:
    settings, _ = physical
    content = FIXTURE.read_bytes()
    with RawTestClient(create_app(settings)) as team_a:
        csrf = _login(team_a, "maya-lim")
        created = team_a.post(
            "/api/clm/zero-touch/cases", json={"uen": "202400001A"}, headers={"X-CSRF-Token": csrf}
        )
        assert created.status_code == 201, created.text
        case_id = created.json()["case"]["case_id"]
        uploaded = team_a.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": FIXTURE.name,
                "X-CSRF-Token": csrf,
            },
            content=content,
        )
        assert uploaded.status_code == 201, uploaded.text

    for _ in ("first process", "restarted process"):
        with RawTestClient(create_app(settings)) as owner:
            # Extra sessions on the same process; only the first client runs the lifespan.
            teammate = RawTestClient(owner.app)
            other_team = RawTestClient(owner.app)
            director = RawTestClient(owner.app)
            _login(owner, "maya-lim")
            _login(teammate, "ethan-tan")  # TEAM_A, not the case creator
            _login(other_team, "sophia-ng")
            _login(director, "olivia-koh")
            route = f"/api/onboarding/cases/{case_id}/document-digests"
            for same_team in (owner, teammate):
                own = same_team.get(route)
                assert own.status_code == 200, own.text
                assert [item["content_sha256"] for item in own.json()] == [_sha(content)]
            assert director.get(route).status_code == 200  # global case access
            foreign = other_team.get(route)
            absent = other_team.get(f"/api/onboarding/cases/{uuid4()}/document-digests")
            unknown_own = owner.get(f"/api/onboarding/cases/{uuid4()}/document-digests")
            assert foreign.status_code == absent.status_code == unknown_own.status_code == 404
            assert foreign.json() == absent.json() == unknown_own.json()
            assert _sha(content) not in foreign.text
        anonymous = RawTestClient(create_app(settings))
        with anonymous:
            assert anonymous.get(route).status_code == 401


# --- 4. unverified and digest-less documents never qualify for D-095 ----------------------------


def _three_cases(settings: Settings, collection: Any) -> dict[str, tuple[Any, Any]]:
    """An approved fixture upload, the same fixture with one altered byte (same name, type and
    size), and an approved upload stored before schema 16 (no digest). Each maps to (served
    documents, served digests) after a restart."""

    content = FIXTURE.read_bytes()
    with TestClient(create_app(settings)) as first:
        cases = {name: _create_case(first) for name in ("approved", "tampered", "legacy")}
        _upload(first, cases["approved"], content, name=FIXTURE.name, media="application/pdf")
        _upload(
            first, cases["tampered"], _tampered(content), name=FIXTURE.name, media="application/pdf"
        )
        _upload(first, cases["legacy"], content, name=FIXTURE.name, media="application/pdf")
    _as_schema_15(collection, cases["legacy"])
    with TestClient(create_app(settings)) as restarted:
        return {
            name: (_documents(restarted, case_id), _digests(restarted, case_id))
            for name, case_id in cases.items()
        }


def test_only_the_approved_fixture_bytes_match_the_d095_manifest(
    physical: tuple[Settings, Any],
) -> None:
    settings, collection = physical
    approved = {
        item["sha256"]: (item["media_type"], item["size_bytes"])
        for item in json.loads(MANIFEST.read_text(encoding="utf-8"))["documents"]
    }
    served = _three_cases(settings, collection)
    (approved_document,), (approved_digest,) = served["approved"]
    (tampered_document,), (tampered_digest,) = served["tampered"]
    (_,), (legacy_digest,) = served["legacy"]
    assert approved_digest["content_sha256"] == _sha(FIXTURE.read_bytes())
    assert approved[approved_digest["content_sha256"]] == (
        approved_document["media_type"],
        approved_document["size_bytes"],
    )
    # Same file name, media type and size as the fixture, but not its bytes.
    assert (tampered_document["display_name"], tampered_document["media_type"]) == (
        approved_document["display_name"],
        approved_document["media_type"],
    )
    assert tampered_document["size_bytes"] == approved_document["size_bytes"]
    assert tampered_digest["content_sha256"] not in approved
    assert legacy_digest["content_sha256"] is None


def test_the_assistant_eligibility_check_refuses_them_on_the_served_digests(
    physical: tuple[Settings, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The AI assistant's own document check (D-095 V2) is run on exactly what this backend
    serves from MongoDB. The module needs only the standard library and httpx, so it is loaded
    from this checkout when the assistant package is not installed (never skipped)."""

    if importlib.util.find_spec("ai_assistant") is None:
        monkeypatch.syspath_prepend(str(REPOSITORY / "apps" / "assistant"))
    from ai_assistant.synthetic_eligibility import _verify_documents, manifest

    settings, collection = physical
    served = _three_cases(settings, collection)
    outcomes = {
        name: _verify_documents(documents, digests, manifest())[0]
        for name, (documents, digests) in served.items()
    }
    assert outcomes == {
        "approved": None,
        "tampered": "SYNTHETIC_DOCUMENT_NOT_VERIFIED",
        "legacy": "SYNTHETIC_DOCUMENT_DIGEST_UNAVAILABLE",
    }
