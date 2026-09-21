"""Physical Mongo proof for the Phase 18 bounded portfolio aggregation."""

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

from app.domain.access import TeamId
from app.domain.case_management import (
    CasePortfolioQuery,
    CasePortfolioScope,
    PortfolioScopeKind,
    PrioritySort,
    case_portfolio_matches,
)
from app.domain.zero_touch import BusinessExceptionType
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")


def _exception(status: str, exception_type: str) -> dict[str, str]:
    return {"status": status, "exception_type": exception_type}


def _document(
    case_id: UUID,
    *,
    schema_version: int = 4,
    team_id: str | None = "TEAM_A",
    priority: int | None = 9,
    uen: str = "202400001A",
    legal_name: str | None = "MERLION PTE. LTD.",
    jurisdiction: str | None = "SG",
    updated_at: str = "2026-09-21T12:00:00.123456Z",
    exceptions: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    onboarding: dict[str, object] = {
        "case_id": str(case_id),
        "requested_uen": uen,
        "entity": {"legal_name": legal_name} if legal_name is not None else None,
        "jurisdiction_resolution": (
            {"resolved_jurisdiction": jurisdiction} if jurisdiction is not None else None
        ),
    }
    if schema_version >= 2:
        onboarding.update({"team_id": team_id, "priority": priority})
    values = exceptions or []
    return {
        "_id": str(case_id),
        "schema_version": schema_version,
        "case_id": str(case_id),
        "revision": 0,
        "onboarding": onboarding,
        "automation": {
            "case_id": str(case_id),
            "status": "WAITING_FOR_REVIEW",
            "current_stage": "DOCUMENT",
            "created_at": "2026-09-21T11:00:00.123456Z",
            "updated_at": updated_at,
            "completed_at": None,
            "exceptions": values,
            "metrics": {
                "human_interventions": 0,
                "final_outcome": None,
            },
        },
    }


def test_physical_portfolio_query_preserves_filters_order_bounds_and_scope() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p18")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    ids = [UUID(f"00000000-0000-4000-8000-00000000018{value}") for value in range(1, 7)]
    try:
        collection.insert_many(
            [
                _document(
                    ids[0],
                    legal_name="MERLION .* LITERAL PTE. LTD.",
                    exceptions=[
                        _exception("OPEN", "DOCUMENT_LOW_CONFIDENCE"),
                        _exception("RESOLVED", "OWNERSHIP_CYCLE"),
                    ],
                ),
                _document(ids[1], uen="202400002B"),
                _document(
                    ids[2],
                    priority=3,
                    uen="202400003C",
                    exceptions=[_exception("OPEN", "OWNERSHIP_CYCLE")],
                ),
                _document(
                    ids[3],
                    priority=None,
                    uen="202400004D",
                    updated_at="2026-09-22T12:00:00.123456Z",
                ),
                _document(ids[4], schema_version=1, team_id=None, priority=None),
                _document(
                    ids[5],
                    team_id="TEAM_B",
                    updated_at="not-a-timestamp",
                ),
            ]
        )
        team_scope = CasePortfolioScope(
            kind=PortfolioScopeKind.TEAM,
            team_id=TeamId.TEAM_A,
        )
        first = store.list_portfolio_page(
            CasePortfolioQuery(scope=team_scope, limit=2)
        )
        assert [item.case_id for item in first.items] == [ids[1], ids[0]]
        assert first.has_more
        second = store.list_portfolio_page(
            CasePortfolioQuery(scope=team_scope, limit=2, offset=2)
        )
        assert [item.case_id for item in second.items] == [ids[2], ids[3]]
        assert not second.has_more

        low_first = store.list_portfolio_page(
            CasePortfolioQuery(scope=team_scope, priority_sort=PrioritySort.LOWEST_FIRST)
        )
        assert [item.priority for item in low_first.items] == [3, 9, 9, None]

        literal = store.list_portfolio_page(
            CasePortfolioQuery(scope=team_scope, search=".*")
        )
        assert [item.case_id for item in literal.items] == [ids[0]]
        uuid_search = store.list_portfolio_page(
            CasePortfolioQuery(scope=team_scope, search=str(ids[2]).upper())
        )
        assert [item.case_id for item in uuid_search.items] == [ids[2]]

        correlated = store.list_portfolio_page(
            CasePortfolioQuery(
                scope=team_scope,
                attention_type=BusinessExceptionType.OWNERSHIP_CYCLE,
            )
        )
        assert [item.case_id for item in correlated.items] == [ids[2]]

        legacy = store.list_portfolio_page(
            CasePortfolioQuery(
                scope=CasePortfolioScope(kind=PortfolioScopeKind.UNASSIGNED)
            )
        )
        assert [item.case_id for item in legacy.items] == [ids[4]]

        with pytest.raises(PersistenceDataInvalidError):
            store.list_portfolio_page(
                CasePortfolioQuery(scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))
            )
        collection.delete_one({"_id": str(ids[5])})
        global_page = store.list_portfolio_page(
            CasePortfolioQuery(scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))
        )
        assert {item.case_id for item in global_page.items} == set(ids[:5])
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def test_physical_portfolio_query_bounds_a_105_case_inventory() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p18")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    ids = [
        UUID(f"00000000-0000-4000-8000-{index:012d}")
        for index in range(1, 106)
    ]
    try:
        collection.insert_many(
            [
                _document(
                    case_id,
                    priority=10 - (index % 10),
                    uen=f"2099{index:05d}A",
                )
                for index, case_id in enumerate(ids)
            ]
        )
        scope = CasePortfolioScope(
            kind=PortfolioScopeKind.TEAM,
            team_id=TeamId.TEAM_A,
        )
        first = store.list_portfolio_page(
            CasePortfolioQuery(scope=scope, limit=100)
        )
        assert len(first.items) == 100
        assert first.has_more
        tail = store.list_portfolio_page(
            CasePortfolioQuery(scope=scope, limit=100, offset=100)
        )
        assert len(tail.items) == 5
        assert not tail.has_more
        assert {item.case_id for item in (*first.items, *tail.items)} == set(ids)
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()


def test_physical_portfolio_rejects_malformed_container_and_preserves_search_parity() -> (
    None
):
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p18")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    case_id = UUID("00000000-0000-4000-8000-000000000199")
    scope = CasePortfolioScope(
        kind=PortfolioScopeKind.TEAM,
        team_id=TeamId.TEAM_A,
    )
    try:
        document = _document(case_id, legal_name="\u0130")
        collection.insert_one(document)

        for legal_name, search in (
            ("\u0130", "i"),
            ("\u0131", "i"),
            ("STRA\u1e9eE PTE. LTD.", "strasse"),
        ):
            collection.update_one(
                {"_id": str(case_id)},
                {"$set": {"onboarding.entity.legal_name": legal_name}},
            )
            memory_record = store.list_portfolio_page(
                CasePortfolioQuery(scope=scope)
            ).items[0]
            query = CasePortfolioQuery(scope=scope, search=search)
            assert not case_portfolio_matches(memory_record, query)
            assert store.list_portfolio_page(query).items == ()

        collection.update_one(
            {"_id": str(case_id)},
            {"$set": {"onboarding.entity": "CORRUPT_SCALAR"}},
        )
        with pytest.raises(PersistenceDataInvalidError):
            store.list_portfolio_page(CasePortfolioQuery(scope=scope))
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
