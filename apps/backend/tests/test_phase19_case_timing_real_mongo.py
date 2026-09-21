"""Physical Mongo proof for the bounded Phase 19 timing projection."""

from __future__ import annotations

import os
from datetime import UTC, datetime
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
    project_case_timing,
)
from app.persistence.errors import PersistenceDataInvalidError
from app.persistence.mongo_case_store import MongoCaseStore

MONGO_URI = os.environ.get("PHASE12_MONGO_URI")
pytestmark = pytest.mark.skipif(not MONGO_URI, reason="PHASE12_MONGO_URI is not configured")
OBSERVED_AT = datetime(2026, 9, 21, 12, 0, 0, tzinfo=UTC)
ACTIVE_ID = UUID("00000000-0000-4000-8000-000000000191")
COMPLETED_ID = UUID("00000000-0000-4000-8000-000000000192")
OUT_OF_SCOPE_ID = UUID("00000000-0000-4000-8000-000000000193")


def _document(
    case_id: UUID,
    *,
    team_id: str,
    status: str,
    stage: str,
    created_at: str,
    updated_at: str,
    started_at: str | None,
    completed_at: str | None,
    total_duration_ms: int | None,
) -> dict[str, object]:
    return {
        "_id": str(case_id),
        "schema_version": 4,
        "case_id": str(case_id),
        "revision": 0,
        "onboarding": {
            "case_id": str(case_id),
            "team_id": team_id,
            "priority": 8,
            "requested_uen": f"{case_id.int % 10_000_000:07d}A",
            "entity": {"legal_name": "PHASE 19 TIMING PTE. LTD."},
            "jurisdiction_resolution": {"resolved_jurisdiction": "SG"},
        },
        "automation": {
            "case_id": str(case_id),
            "status": status,
            "current_stage": stage,
            "created_at": created_at,
            "updated_at": updated_at,
            "started_at": started_at,
            "completed_at": completed_at,
            "exceptions": [],
            "metrics": {
                "human_interventions": 0,
                "final_outcome": (
                    "MOCK_GOLDTIER_SUBMITTED" if status == "COMPLETED" else None
                ),
                "total_duration_ms": total_duration_ms,
            },
        },
    }


def test_physical_timing_projection_is_bounded_scoped_and_fail_closed() -> None:
    assert MONGO_URI is not None
    database = generate_ephemeral_mongo_database("p19")
    client: MongoClient[dict[str, Any]] = MongoClient(MONGO_URI)
    collection_name = "clm_case_snapshots"
    collection = client[database][collection_name]
    store = MongoCaseStore(client, database=database, collection=collection_name)
    scope = CasePortfolioScope(
        kind=PortfolioScopeKind.TEAM,
        team_id=TeamId.TEAM_A,
    )
    try:
        collection.insert_many(
            [
                _document(
                    ACTIVE_ID,
                    team_id="TEAM_A",
                    status="RUNNING",
                    stage="DOCUMENT",
                    created_at="2026-09-21T09:00:00Z",
                    updated_at="2026-09-21T10:00:00Z",
                    started_at="2026-09-21T09:30:00Z",
                    completed_at=None,
                    total_duration_ms=None,
                ),
                _document(
                    COMPLETED_ID,
                    team_id="TEAM_A",
                    status="COMPLETED",
                    stage="COMPLETE",
                    created_at="2026-09-21T08:00:00Z",
                    updated_at="2026-09-21T10:00:00Z",
                    started_at="2026-09-21T08:15:00Z",
                    completed_at="2026-09-21T09:00:00Z",
                    total_duration_ms=2_700_000,
                ),
                _document(
                    OUT_OF_SCOPE_ID,
                    team_id="TEAM_B",
                    status="RUNNING",
                    stage="DOCUMENT",
                    created_at="2026-09-21T09:00:00Z",
                    updated_at="2026-09-21T10:00:00Z",
                    started_at="2026-09-21T09:30:00Z",
                    completed_at=None,
                    total_duration_ms=-1,
                ),
            ]
        )

        page = store.list_portfolio_page(CasePortfolioQuery(scope=scope))
        assert {item.case_id for item in page.items} == {ACTIVE_ID, COMPLETED_ID}
        timing = {
            item.case_id: project_case_timing(
                created_at=item.created_at,
                updated_at=item.updated_at,
                started_at=item.started_at,
                completed_at=item.completed_at,
                recorded_total_duration_ms=item.recorded_total_duration_ms,
                observed_at=OBSERVED_AT,
            )
            for item in page.items
        }
        assert timing[ACTIVE_ID].model_dump() == {
            "case_elapsed_ms": 10_800_000,
            "time_since_last_update_ms": 7_200_000,
            "automation_elapsed_ms": 9_000_000,
            "recorded_total_duration_ms": None,
        }
        assert timing[COMPLETED_ID].model_dump() == {
            "case_elapsed_ms": 3_600_000,
            "time_since_last_update_ms": 7_200_000,
            "automation_elapsed_ms": 2_700_000,
            "recorded_total_duration_ms": 2_700_000,
        }

        collection.update_one(
            {"_id": str(ACTIVE_ID)},
            {"$set": {"automation.metrics.total_duration_ms": -1}},
        )
        with pytest.raises(PersistenceDataInvalidError):
            store.list_portfolio_page(CasePortfolioQuery(scope=scope))
    finally:
        try:
            cleanup_ephemeral_mongo_database(client, database)
        finally:
            client.close()
