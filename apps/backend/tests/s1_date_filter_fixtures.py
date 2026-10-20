"""Synthetic creation-date portfolio fixtures shared by memory and physical tests."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from app.domain.access import TeamId
from app.domain.zero_touch import AutomationStage, AutomationStatus
from app.services.case_portfolio_repository import InMemoryCasePortfolioRepository

START = datetime(2026, 10, 3, 16, tzinfo=UTC)
END = START + timedelta(days=1)
OBSERVED = END + timedelta(days=2)


def date_filter_documents() -> list[dict[str, Any]]:
    dates = [
        START - timedelta(microseconds=1),
        START,
        START + timedelta(microseconds=1),
        END - timedelta(microseconds=1),
        END,
        START + timedelta(hours=2),
    ]
    documents: list[dict[str, Any]] = []
    for index, created_at in enumerate(dates):
        case_id = str(UUID(f"00000000-0000-4000-8000-{index + 6100:012d}"))
        documents.append({
            "_id": case_id,
            "case_id": case_id,
            "schema_version": 4,
            "revision": 1,
            "onboarding": {
                "case_id": case_id,
                "team_id": "TEAM_B" if index == 5 else "TEAM_A",
                "priority": 10 - index,
                "requested_uen": f"20990000{index}A",
                "entity": None,
                "jurisdiction_resolution": None,
                "goldtier_result": None,
            },
            "automation": {
                "case_id": case_id,
                "status": "COMPLETED" if index in {2, 3} else "WAITING_FOR_REVIEW",
                "current_stage": "DOCUMENT",
                "created_at": created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": OBSERVED.isoformat().replace("+00:00", "Z"),
                "started_at": None,
                "completed_at": None,
                "exceptions": [],
                "metrics": {
                    "human_interventions": 0,
                    "final_outcome": None,
                    "total_duration_ms": None,
                },
            },
        })
    return documents


def memory_date_filter_repository(
    documents: list[dict[str, Any]],
) -> InMemoryCasePortfolioRepository:
    cases = {}
    automation_records = []
    for document in documents:
        onboarding = document["onboarding"]
        automation = document["automation"]
        case_id = UUID(document["case_id"])
        cases[case_id] = SimpleNamespace(
            case_id=case_id,
            team_id=TeamId(onboarding["team_id"]),
            priority=onboarding["priority"],
            requested_uen=onboarding["requested_uen"],
            entity=None,
            jurisdiction_resolution=None,
            goldtier_result=None,
            created_by_actor_id=None,
            # Different from automation creation: never use the wrong owner.
            created_at=OBSERVED,
        )
        automation_records.append(SimpleNamespace(
            case_id=case_id,
            status=AutomationStatus(automation["status"]),
            current_stage=AutomationStage(automation["current_stage"]),
            created_at=datetime.fromisoformat(automation["created_at"]),
            updated_at=OBSERVED,
            started_at=None,
            completed_at=None,
            active_exceptions=[],
            exceptions=[],
            metrics=SimpleNamespace(**automation["metrics"]),
        ))
    return InMemoryCasePortfolioRepository(
        SimpleNamespace(get=lambda case_id: cases.get(case_id)),  # type: ignore[arg-type]
        SimpleNamespace(list_records=lambda: automation_records),  # type: ignore[arg-type]
    )
