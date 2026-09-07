from __future__ import annotations

import secrets
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.seed_phase13_demo import (  # noqa: E402
    SEED_PRIORITIES,
    SEED_UENS,
    TEAMS,
    seed_demo,
)


class FakeSeedApi:
    def __init__(self, existing: list[dict[str, Any]] | None = None) -> None:
        self.existing = existing or []
        self.captured_credential: str | None = None
        self.created: list[tuple[str, str, str]] = []
        self.priorities: list[tuple[str, int | None]] = []
        self.logged_out = False

    def login(self, credential: str) -> None:
        self.captured_credential = credential

    def list_cases(self) -> list[dict[str, Any]]:
        return list(self.existing)

    def create_case(self, team_id: str, uen: str) -> str:
        case_id = f"synthetic-{team_id}-{uen}"
        self.created.append((team_id, uen, case_id))
        return case_id

    def set_priority(self, case_id: str, priority: int | None) -> None:
        self.priorities.append((case_id, priority))

    def logout(self) -> None:
        self.logged_out = True


def test_seed_uses_authenticated_api_for_ten_team_cases_and_priority_distribution() -> None:
    credential = secrets.token_urlsafe(24)
    api = FakeSeedApi()

    result = seed_demo(api, credential)

    assert api.captured_credential == credential
    assert api.logged_out
    assert result.created == 10
    assert result.reused == 0
    assert result.prioritised == 10
    assert [(team, uen) for team, uen, _ in api.created] == [
        (team, uen) for team in TEAMS for uen in SEED_UENS
    ]
    assert [priority for _, priority in api.priorities] == list(SEED_PRIORITIES) * 2


def test_seed_reuses_matching_team_and_uen_but_still_applies_priority() -> None:
    credential = secrets.token_urlsafe(24)
    api = FakeSeedApi(
        [{"team_id": "TEAM_A", "requested_uen": SEED_UENS[0], "case_id": "existing"}]
    )

    result = seed_demo(api, credential)

    assert result.created == 9
    assert result.reused == 1
    assert result.prioritised == 10
    assert api.priorities[0] == ("existing", 10)
