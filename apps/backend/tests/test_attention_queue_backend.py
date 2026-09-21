from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import ValidationError

from app.domain.access import SYNTHETIC_PROFILE_BY_ID, AuthenticatedActor, TeamId
from app.domain.case_management import (
    CasePortfolioRecord,
    CasePortfolioScope,
    PortfolioScopeKind,
)
from app.domain.jurisdiction import JurisdictionCode
from app.domain.zero_touch import (
    AutomationStage,
    AutomationStatus,
    BusinessExceptionStatus,
    BusinessExceptionType,
)
from app.main import create_app
from app.services.authorization import CaseAccessPolicy
from app.services.case_portfolio_repository import InMemoryCasePortfolioRepository
from app.services.case_query import CaseQueryService, PriorityFilter, PrioritySort

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def _portfolio_record(
    case_id: str,
    *,
    team_id: TeamId | None,
    priority: int | None,
    exception_types: tuple[BusinessExceptionType, ...],
) -> CasePortfolioRecord:
    return CasePortfolioRecord(
        case_id=UUID(case_id),
        requested_uen="202400001A",
        legal_name="MERLION PTE. LTD.",
        resolved_jurisdiction=JurisdictionCode.SINGAPORE,
        team_id=team_id,
        priority=priority,
        status=AutomationStatus.WAITING_FOR_REVIEW,
        current_stage=AutomationStage.DOCUMENT,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
        active_exception_count=len(exception_types),
        active_exception_types=exception_types,
        human_interventions=0,
        final_outcome=None,
        mock_goldtier_party_id=None,
    )


class _PortfolioProbe:
    def __init__(self, records: list[CasePortfolioRecord]) -> None:
        self.records = records
        self.scopes: list[CasePortfolioScope] = []
        self.statuses: list[AutomationStatus | None] = []

    def list_authorized(
        self,
        scope: CasePortfolioScope,
        *,
        status: AutomationStatus | None = None,
    ) -> list[CasePortfolioRecord]:
        self.scopes.append(scope)
        self.statuses.append(status)
        return [
            record
            for record in self.records
            if (
                scope.kind == PortfolioScopeKind.GLOBAL
                or scope.kind == PortfolioScopeKind.UNASSIGNED
                and record.team_id is None
                or scope.kind == PortfolioScopeKind.TEAM
                and record.team_id == scope.team_id
            )
        ]


def _query_service(probe: _PortfolioProbe) -> CaseQueryService:
    return CaseQueryService(
        cases=object(),  # type: ignore[arg-type]
        case_repository=object(),  # type: ignore[arg-type]
        automation_repository=object(),  # type: ignore[arg-type]
        access_policy=CaseAccessPolicy(),
        teams=object(),  # type: ignore[arg-type]
        portfolio_repository=probe,
    )


def test_memory_projection_deduplicates_open_types_in_enum_order_and_keeps_count() -> None:
    case_id = UUID("00000000-0000-4000-8000-000000000101")
    case = SimpleNamespace(
        case_id=case_id,
        requested_uen="202400001A",
        entity=None,
        jurisdiction_resolution=None,
        team_id=TeamId.TEAM_A,
        priority=8,
        goldtier_result=None,
    )
    exceptions = [
        SimpleNamespace(
            status=BusinessExceptionStatus.OPEN,
            exception_type=BusinessExceptionType.OWNERSHIP_CYCLE,
        ),
        SimpleNamespace(
            status=BusinessExceptionStatus.OPEN,
            exception_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        ),
        SimpleNamespace(
            status=BusinessExceptionStatus.OPEN,
            exception_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        ),
        SimpleNamespace(
            status=BusinessExceptionStatus.RESOLVED,
            exception_type=BusinessExceptionType.JURISDICTION_CONFLICT,
        ),
        SimpleNamespace(
            status=BusinessExceptionStatus.CANCELLED,
            exception_type=BusinessExceptionType.REGISTRY_REVIEW_REQUIRED,
        ),
    ]
    automation = SimpleNamespace(
        case_id=case_id,
        status=AutomationStatus.WAITING_FOR_REVIEW,
        current_stage=AutomationStage.DOCUMENT,
        created_at=NOW,
        updated_at=NOW,
        completed_at=None,
        exceptions=exceptions,
        active_exceptions=[
            item for item in exceptions if item.status == BusinessExceptionStatus.OPEN
        ],
        metrics=SimpleNamespace(human_interventions=0, final_outcome=None),
    )
    repository = InMemoryCasePortfolioRepository(
        SimpleNamespace(get=lambda _: case),  # type: ignore[arg-type]
        SimpleNamespace(list_records=lambda: [automation]),  # type: ignore[arg-type]
    )

    record = repository.list_authorized(
        CasePortfolioScope(kind=PortfolioScopeKind.TEAM, team_id=TeamId.TEAM_A)
    )[0]

    assert record.active_exception_count == 3
    assert record.active_exception_types == (
        BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        BusinessExceptionType.OWNERSHIP_CYCLE,
    )


def test_portfolio_record_rejects_duplicate_or_noncanonical_type_order() -> None:
    base = _portfolio_record(
        "00000000-0000-4000-8000-000000000102",
        team_id=TeamId.TEAM_A,
        priority=5,
        exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
    )
    for invalid_types in (
        (
            BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
            BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        ),
        (
            BusinessExceptionType.OWNERSHIP_CYCLE,
            BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
        ),
    ):
        with pytest.raises(ValidationError):
            CasePortfolioRecord.model_validate(
                {**base.model_dump(), "active_exception_types": invalid_types}
            )


def test_attention_filter_intersects_authorized_scope_priority_and_status() -> None:
    matching = _portfolio_record(
        "00000000-0000-4000-8000-000000000103",
        team_id=TeamId.TEAM_A,
        priority=10,
        exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
    )
    wrong_priority = _portfolio_record(
        "00000000-0000-4000-8000-000000000104",
        team_id=TeamId.TEAM_A,
        priority=2,
        exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
    )
    inaccessible = _portfolio_record(
        "00000000-0000-4000-8000-000000000105",
        team_id=TeamId.TEAM_B,
        priority=10,
        exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
    )
    probe = _PortfolioProbe([matching, wrong_priority, inaccessible])
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])

    records = _query_service(probe).list_cases(
        actor,
        status=AutomationStatus.WAITING_FOR_REVIEW,
        priority_filter=PriorityFilter.P10,
        priority_sort=PrioritySort.HIGHEST_FIRST,
        attention_type=BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,
    )

    assert records == [matching]
    assert probe.scopes[0].team_id == TeamId.TEAM_A
    assert probe.statuses == [AutomationStatus.WAITING_FOR_REVIEW]


def test_closed_type_history_cannot_match_attention_filter() -> None:
    record = _portfolio_record(
        "00000000-0000-4000-8000-000000000106",
        team_id=TeamId.TEAM_A,
        priority=None,
        exception_types=(BusinessExceptionType.DOCUMENT_LOW_CONFIDENCE,),
    )
    probe = _PortfolioProbe([record])
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["maya-lim"])

    assert _query_service(probe).list_cases(
        actor,
        attention_type=BusinessExceptionType.OWNERSHIP_CYCLE,
    ) == []


def test_attention_filter_composes_with_director_unassigned_scope() -> None:
    unassigned = _portfolio_record(
        "00000000-0000-4000-8000-000000000107",
        team_id=None,
        priority=4,
        exception_types=(BusinessExceptionType.OWNERSHIP_CYCLE,),
    )
    assigned = _portfolio_record(
        "00000000-0000-4000-8000-000000000108",
        team_id=TeamId.TEAM_A,
        priority=9,
        exception_types=(BusinessExceptionType.OWNERSHIP_CYCLE,),
    )
    probe = _PortfolioProbe([unassigned, assigned])
    actor = AuthenticatedActor(profile=SYNTHETIC_PROFILE_BY_ID["olivia-koh"])

    records = _query_service(probe).list_cases(
        actor,
        team_filter="unassigned",
        attention_type=BusinessExceptionType.OWNERSHIP_CYCLE,
    )

    assert records == [unassigned]
    assert probe.scopes[0].team_id is None


def test_list_api_adds_empty_types_and_rejects_unknown_attention_type() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200
    created = client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
    )
    assert created.status_code == 201

    listed = client.get("/api/clm/zero-touch/cases")
    invalid = client.get("/api/clm/zero-touch/cases?attention_type=UNKNOWN")

    assert listed.status_code == 200
    assert listed.json()[0]["active_exception_types"] == []
    assert invalid.status_code == 422


def test_list_api_filters_an_actual_open_exception_without_matching_other_types() -> None:
    client = RawTestClient(create_app(ordinary_test_settings(demo_controls_enabled=True)))
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    csrf = login.json()["csrf_token"]
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": "LOW_CONFIDENCE"},
        headers={"X-CSRF-Token": csrf},
    )
    case_id = created.json()["case"]["case_id"]
    uploaded = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/intake/documents",
        content=(
            b"Legal Name: MERLION CIRCULAR LABS PTE. LTD.\n"
            b"UEN: 202400001A\n"
            b"Registered Address: 18 INNOVATION WAY, #04-01, 018956, SG\n"
            b"Country: SG\n"
        ),
        headers={
            "Content-Type": "text/plain",
            "X-Document-Name": "evidence.txt",
            "X-CSRF-Token": csrf,
        },
    )
    paused = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/intake/complete",
        json={"expected_document_count": 1},
        headers={"X-CSRF-Token": csrf},
    )

    matching = client.get(
        "/api/clm/zero-touch/cases?attention_type=DOCUMENT_LOW_CONFIDENCE"
    )
    nonmatching = client.get(
        "/api/clm/zero-touch/cases?attention_type=OWNERSHIP_CYCLE"
    )

    assert created.status_code == 201
    assert uploaded.status_code == 201
    assert paused.status_code == 200
    assert paused.json()["status"] == "WAITING_FOR_REVIEW"
    assert [item["case_id"] for item in matching.json()] == [case_id]
    assert matching.json()[0]["active_exception_types"] == ["DOCUMENT_LOW_CONFIDENCE"]
    assert nonmatching.json() == []
