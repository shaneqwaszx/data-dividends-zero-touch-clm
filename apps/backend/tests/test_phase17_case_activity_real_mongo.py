"""Physical Mongo proof for the Phase 17 bounded activity aggregation."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
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
    CaseActivityAction,
    CaseActivityQuery,
    CasePortfolioScope,
    PortfolioScopeKind,
)
from app.domain.models import EventOutcome
from app.domain.zero_touch import AutomationStage
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
NOW = datetime(2026, 9, 21, 12, 0, 0, 123456, tzinfo=UTC)


def _event(
    case_id: UUID,
    sequence: int,
    timestamp: str,
    *,
    event_type: str = "ONBOARDING_CREATED",
    stage: str = "REGISTRY",
    outcome: str = "SUCCEEDED",
    message: str = "Retained physical event.",
) -> dict[str, object]:
    return {
        "sequence": sequence,
        "event_type": event_type,
        "status": "RUNNING",
        "stage": stage,
        "outcome": outcome,
        "timestamp": timestamp,
        "case_id": str(case_id),
        "code": None,
        "message": message,
    }


def _document(
    case_id: UUID,
    schema_version: int,
    events: list[dict[str, object]],
    *,
    team_id: str | None = "TEAM_A",
    priority: int | None = 7,
) -> dict[str, object]:
    onboarding: dict[str, object] = {"case_id": str(case_id)}
    if schema_version >= 2:
        onboarding.update({"team_id": team_id, "priority": priority})
    return {
        "_id": str(case_id),
        "schema_version": schema_version,
        "case_id": str(case_id),
        "revision": 0,
        "onboarding": onboarding,
        "automation": {"case_id": str(case_id), "events": events},
    }


def test_physical_activity_query_preserves_precision_scope_legacy_and_corruption() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p17")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    ids = [UUID(f"00000000-0000-4000-8000-00000000017{value}") for value in range(1, 7)]
    try:
        collection.insert_many(
            [
                _document(ids[0], 1, [_event(ids[0], 1, "2026-09-21T12:00:00Z")]),
                _document(
                    ids[1],
                    2,
                    [
                        _event(ids[1], 1, "2026-09-21T12:00:00.123455Z"),
                        _event(
                            ids[1],
                            2,
                            "2026-09-21T12:00:00.123456Z",
                            event_type="DOCUMENT_REVIEW_REQUIRED",
                            stage="DOCUMENT",
                            outcome="REVIEW_REQUIRED",
                        ),
                    ],
                ),
                _document(ids[2], 3, [_event(ids[2], 1, "2026-09-21T12:00:00.123456Z")]),
                _document(ids[3], 4, [_event(ids[3], 1, "2026-09-21T12:00:00.123457Z")]),
                _document(
                    ids[4],
                    4,
                    [_event(ids[4], 1, "not-a-timestamp")],
                    team_id="TEAM_B",
                ),
            ]
        )

        team_page = store.list_activity(
            CaseActivityQuery(
                scope=CasePortfolioScope(
                    kind=PortfolioScopeKind.TEAM,
                    team_id=TeamId.TEAM_A,
                ),
                limit=2,
            )
        )
        assert [(item.case_id, item.sequence) for item in team_page.items] == [
            (ids[3], 1),
            (ids[1], 2),
        ]
        assert team_page.items[0].timestamp.microsecond == 123457
        assert team_page.has_more

        second_page = store.list_activity(
            CaseActivityQuery(
                scope=CasePortfolioScope(
                    kind=PortfolioScopeKind.TEAM,
                    team_id=TeamId.TEAM_A,
                ),
                limit=2,
                offset=2,
            )
        )
        assert [(item.case_id, item.sequence) for item in second_page.items] == [
            (ids[2], 1),
            (ids[1], 1),
        ]
        assert not second_page.has_more

        filtered = store.list_activity(
            CaseActivityQuery(
                scope=CasePortfolioScope(
                    kind=PortfolioScopeKind.TEAM,
                    team_id=TeamId.TEAM_A,
                ),
                action=CaseActivityAction.DOCUMENT,
                stage=AutomationStage.DOCUMENT,
                outcome=EventOutcome.REVIEW_REQUIRED,
                from_at=NOW,
                to_at=NOW + timedelta(microseconds=1),
            )
        )
        assert [(item.case_id, item.sequence) for item in filtered.items] == [(ids[1], 2)]

        legacy = store.list_activity(
            CaseActivityQuery(
                scope=CasePortfolioScope(kind=PortfolioScopeKind.UNASSIGNED),
            )
        )
        assert [item.case_id for item in legacy.items] == [ids[0]]

        with pytest.raises(PersistenceDataInvalidError):
            store.list_activity(
                CaseActivityQuery(scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))
            )

        collection.delete_one({"_id": str(ids[4])})
        global_page = store.list_activity(
            CaseActivityQuery(scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL))
        )
        assert {item.case_id for item in global_page.items} == set(ids[:4])

        collection.delete_one({"_id": str(ids[1])})
        deleted_page = store.list_activity(
            CaseActivityQuery(
                scope=CasePortfolioScope(kind=PortfolioScopeKind.GLOBAL),
                case_id=ids[1],
            )
        )
        assert deleted_page.items == ()
        assert not deleted_page.has_more
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
