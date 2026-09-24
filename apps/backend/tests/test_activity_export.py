from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from uuid import UUID

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings

from app.domain.case_management import CaseActivityItem, CaseActivityPage
from app.domain.models import EventOutcome
from app.domain.zero_touch import (
    AutomationEventType,
    AutomationStage,
    AutomationStatus,
)
from app.main import create_app
from app.services.activity_export import render_case_activity_csv

CASE_ID = UUID("00000000-0000-4000-8000-000000000221")


def test_activity_csv_is_fixed_bounded_utc_and_formula_hardened() -> None:
    page = CaseActivityPage(
        items=(
            CaseActivityItem(
                case_id=CASE_ID,
                sequence=1,
                timestamp=datetime(2026, 9, 23, 1, 2, 3, 456789, tzinfo=UTC),
                event_type=AutomationEventType.ONBOARDING_CREATED,
                status=AutomationStatus.RUNNING,
                stage=AutomationStage.REGISTRY,
                outcome=EventOutcome.SUCCEEDED,
                code="=CMD()",
                message="\t+formula, with comma",
                current_priority=9,
                current_client_scope_label="@client",
            ),
        ),
        offset=0,
        limit=100,
        has_more=True,
    )

    rendered = render_case_activity_csv(page)
    rows = list(csv.reader(io.StringIO(rendered)))

    assert rows[0] == [
        "case_id",
        "sequence",
        "timestamp_utc",
        "event_type",
        "status",
        "stage",
        "outcome",
        "code",
        "message",
        "current_priority",
        "current_client_scope_label",
    ]
    assert len(rows) == 2
    assert rows[1][2] == "2026-09-23T01:02:03.456789Z"
    assert rows[1][7] == "'=CMD()"
    assert rows[1][8] == "'\t+formula, with comma"
    assert rows[1][10] == "'@client"
    assert "has_more" not in rendered


@pytest.mark.parametrize(
    "prefix",
    ["\x00", "\x0b", "\x0c", "\u00a0", "\u2003"],
    ids=["nul", "vertical-tab", "form-feed", "no-break-space", "em-space"],
)
def test_activity_csv_neutralizes_formula_after_any_control_or_unicode_whitespace(
    prefix: str,
) -> None:
    page = CaseActivityPage(
        items=(
            CaseActivityItem(
                case_id=CASE_ID,
                sequence=1,
                timestamp=datetime(2026, 9, 23, tzinfo=UTC),
                event_type=AutomationEventType.ONBOARDING_CREATED,
                status=AutomationStatus.RUNNING,
                stage=AutomationStage.REGISTRY,
                outcome=EventOutcome.SUCCEEDED,
                code="SAFE",
                message=f"{prefix}=2+2",
                current_priority=1,
                current_client_scope_label="SYNTHETIC",
            ),
        ),
        offset=0,
        limit=100,
        has_more=False,
    )

    row = list(csv.reader(io.StringIO(render_case_activity_csv(page))))[1]

    assert row[8] == f"'{prefix}=2+2"


def test_activity_csv_endpoint_reuses_authorized_query_and_safe_headers() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    login = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200

    response = client.get("/api/clm/zero-touch/activity.csv?limit=100")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        'attachment; filename="case-activity.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.text.startswith("case_id,sequence,timestamp_utc,")


def test_activity_csv_endpoint_preserves_non_enumerating_case_boundary() -> None:
    application = create_app(ordinary_test_settings())
    team_a = RawTestClient(application)
    team_b = RawTestClient(application)
    for client, user_id in ((team_a, "maya-lim"), (team_b, "sophia-ng")):
        login = client.post(
            "/api/auth/login",
            json={"user_id": user_id, "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        if user_id == "sophia-ng":
            csrf = login.json()["csrf_token"]

    created = team_b.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    other_team_case = created.json()["case"]["case_id"]

    inaccessible = team_a.get(
        f"/api/clm/zero-touch/activity.csv?case_id={other_team_case}"
    )
    absent = team_a.get(f"/api/clm/zero-touch/activity.csv?case_id={CASE_ID}")

    assert inaccessible.status_code == absent.status_code == 404
    assert inaccessible.json() == absent.json()
