"""Mongo-free structural guards for the opt-in Phase 14 physical verifier."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from test_phase14_real_mongo import (
    DOCUMENT,
    DOCUMENT_CONTENT_TYPE,
    DOCUMENT_NAME,
    _assert_unrelated_envelope_preserved,
    _post_document_upload,
    _prove_stale_delete_conflict,
)

from app.persistence.errors import PersistenceConflictError


class _RecordingClient:
    def __init__(self) -> None:
        self.request: dict[str, Any] | None = None

    def post(self, url: str, **kwargs: Any) -> object:
        self.request = {"url": url, **kwargs}
        return object()


class _RecordingStore:
    def __init__(self) -> None:
        self.call: tuple[object, int] | None = None

    def delete(
        self, case_id: object, *, expected_revision: int, expected_nonce: str | None
    ) -> None:
        del expected_nonce
        self.call = (case_id, expected_revision)
        raise PersistenceConflictError


class _EnvelopeCollection:
    def __init__(self, records: dict[str, dict[str, Any]]) -> None:
        self.records = records
        self.query: dict[str, str] | None = None

    def find_one(self, query: dict[str, str]) -> dict[str, Any] | None:
        self.query = query
        return self.records.get(query["_id"])


def test_physical_verifier_upload_uses_raw_body_filename_header_and_csrf() -> None:
    client = _RecordingClient()
    case_id = str(uuid4())

    _post_document_upload(client, case_id=case_id, csrf_token="csrf")

    assert client.request == {
        "url": f"/api/demo/clm/zero-touch/cases/{case_id}/intake/documents",
        "content": DOCUMENT,
        "headers": {
            "Content-Type": DOCUMENT_CONTENT_TYPE,
            "X-Document-Name": DOCUMENT_NAME,
            "X-CSRF-Token": "csrf",
        },
    }


def test_physical_verifier_compares_the_unrelated_envelope() -> None:
    unrelated_case_id = str(uuid4())
    target_case_id = str(uuid4())
    expected = {
        "_id": unrelated_case_id,
        "revision": 7,
        "onboarding": {"case_id": unrelated_case_id},
    }

    collection = _EnvelopeCollection(
        {unrelated_case_id: expected, target_case_id: {"_id": target_case_id}}
    )
    _assert_unrelated_envelope_preserved(
        collection,
        unrelated_case_id=unrelated_case_id,
        expected_envelope=expected,
    )
    assert collection.query == {"_id": unrelated_case_id}


def test_physical_verifier_uses_stale_revision_for_cas_conflict() -> None:
    store = _RecordingStore()
    target_case_id = uuid4()

    _prove_stale_delete_conflict(store, case_id=target_case_id, stale_revision=3)

    assert store.call == (target_case_id, 3)


@pytest.mark.parametrize(
    "database", ["clm_poc", "clm_p14_short", "clm_p14_0123456789ABCDEF01234567"]
)
def test_phase14_database_allowlist_rejects_unsafe_names(database: str) -> None:
    from scripts.mongo_test_safety import require_ephemeral_mongo_database

    with pytest.raises(ValueError):
        require_ephemeral_mongo_database(database)
