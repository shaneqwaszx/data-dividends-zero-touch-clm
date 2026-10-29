"""Physical Mongo proof for the Cases page "Show" view (progress) filter."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

import pytest
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)
from test_phase18_case_portfolio_real_mongo import _document

from app.domain.case_management import (
    CasePortfolioQuery,
    CasePortfolioScope,
    PortfolioScopeKind,
)
from app.domain.zero_touch import AutomationStatus
from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


def test_physical_progress_splits_completed_cases_from_every_other_status() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p18")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    statuses = list(AutomationStatus)
    ids = {
        status: UUID(f"00000000-0000-4000-8000-{index + 1:012d}")
        for index, status in enumerate(statuses)
    }
    try:
        documents = []
        for status, case_id in ids.items():
            document = _document(case_id, uen=f"2099{len(documents):05d}A")
            document["automation"]["status"] = status.value  # type: ignore[index]
            documents.append(document)
        collection.insert_many(documents)
        scope = CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL)

        def listed(**filters: Any) -> set[UUID]:
            page = store.list_portfolio_page(CasePortfolioQuery(scope=scope, **filters))
            return {item.case_id for item in page.items}

        completed = ids[AutomationStatus.COMPLETED]
        assert listed() == set(ids.values())
        assert listed(progress="onboarded") == {completed}
        assert listed(progress="in_progress") == set(ids.values()) - {completed}
        assert listed(progress="onboarded", status=AutomationStatus.WAITING_FOR_REVIEW) == set()
        assert listed(
            progress="in_progress", status=AutomationStatus.WAITING_FOR_REVIEW,
        ) == {ids[AutomationStatus.WAITING_FOR_REVIEW]}
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
