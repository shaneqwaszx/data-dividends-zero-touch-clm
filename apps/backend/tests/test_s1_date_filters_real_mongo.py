"""Physical memory/Mongo parity for filtering before pagination on creation dates."""

import os
from typing import Any

import pytest
from pymongo import MongoClient
from s1_date_filter_fixtures import (
    END,
    START,
    date_filter_documents,
    memory_date_filter_repository,
)
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
)

from app.domain.access import TeamId
from app.domain.case_management import CasePortfolioQuery, CasePortfolioScope, PortfolioScopeKind
from app.domain.zero_touch import AutomationStatus
from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


def test_physical_creation_filter_matches_memory_scope_precision_and_page_window() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p18")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    documents = date_filter_documents()
    memory = memory_date_filter_repository(documents)
    try:
        collection.insert_many(documents)
        for scope in (
            CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL),
            CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A),
            CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_B),
        ):
            for status in (None, AutomationStatus.COMPLETED):
                for from_at, to_at in ((START, END), (START, None), (None, END)):
                    for offset in range(4):
                        query = CasePortfolioQuery(
                            scope=scope, status=status, created_from_at=from_at,
                            created_to_at=to_at, limit=1, offset=offset,
                        )
                        assert store.list_portfolio_page(query) == memory.list_page(query)
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
