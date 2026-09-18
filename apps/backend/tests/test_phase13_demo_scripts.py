from __future__ import annotations

import secrets
import socket
import sys
import time
from pathlib import Path
from threading import Thread
from typing import Any

import pytest
import uvicorn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from phase13_test_clients import RawTestClient  # noqa: E402
from phase13_test_credentials import build_test_authentication_service  # noqa: E402
from phase13_test_settings import ordinary_test_settings  # noqa: E402
from scripts.generate_admin_bootstrap_password_hashes import (  # noqa: E402
    main as generate_hashes,
)
from scripts.seed_phase13_demo import (  # noqa: E402
    DIRECTOR_USER_ID,
    SEED_PRIORITIES,
    SEED_UENS,
    TEAMS,
    HttpSeedApi,
    _synthetic_pdf,
    seed_demo,
)
from scripts.seed_phase13_demo import (  # noqa: E402
    main as seed_main,
)

from app.domain.access import SYNTHETIC_USER_PROFILES  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.authentication import (  # noqa: E402
    generate_scrypt_password_hash,
    parse_scrypt_password_hash,
)


class FakeSeedApi:
    def __init__(self, existing: list[dict[str, Any]] | None = None) -> None:
        self.existing = existing or []
        self.captured_credential: str | None = None
        self.created: list[tuple[str, str, int | None, str]] = []
        self.completed: list[str] = []
        self.priorities: list[tuple[str, int | None]] = []
        self.logged_out = False

    def login(self, credential: str) -> None:
        self.captured_credential = credential

    def list_cases(self) -> list[dict[str, Any]]:
        return list(self.existing)

    def create_case(self, team_id: str, uen: str, priority: int | None) -> str:
        case_id = f"synthetic-{team_id}-{uen}"
        self.created.append((team_id, uen, priority, case_id))
        self.existing.append(
            {
                "team_id": team_id,
                "requested_uen": uen,
                "case_id": case_id,
                "priority": priority,
                "status": "PENDING_INPUTS",
                "final_outcome": None,
            }
        )
        return case_id

    def complete_case(self, case_id: str) -> None:
        self.completed.append(case_id)
        for item in self.existing:
            if item["case_id"] == case_id:
                item["status"] = "COMPLETED"
                item["final_outcome"] = "MOCK_GOLDTIER_SUBMITTED"

    def set_priority(self, case_id: str, priority: int | None) -> None:
        self.priorities.append((case_id, priority))
        for item in self.existing:
            if item["case_id"] == case_id:
                item["priority"] = priority

    def logout(self) -> None:
        self.logged_out = True


def test_generator_emits_only_new_profile_hash_assignments(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    credentials = [secrets.token_urlsafe(24) for _ in range(6)]
    entries = iter(value for credential in credentials for value in (credential, credential))
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(entries))

    assert generate_hashes() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    lines = captured.out.splitlines()
    assert [line.split("=", 1)[0] for line in lines] == [
        "PHASE13_MAYA_LIM_PASSWORD_HASH",
        "PHASE13_ETHAN_TAN_PASSWORD_HASH",
        "PHASE13_SOPHIA_NG_PASSWORD_HASH",
        "PHASE13_RYAN_LEE_PASSWORD_HASH",
        "PHASE13_OLIVIA_KOH_PASSWORD_HASH",
        "PHASE14_5_HR_ADMIN_PASSWORD_HASH",
    ]
    for line in lines:
        parse_scrypt_password_hash(line.split("=", 1)[1])
    assert all(credential not in captured.out for credential in credentials)


def test_seeder_authenticates_as_the_new_synthetic_director() -> None:
    assert DIRECTOR_USER_ID == "olivia-koh"


def test_seed_uses_authenticated_api_for_ten_team_cases_and_priority_distribution() -> None:
    credential = secrets.token_urlsafe(24)
    api = FakeSeedApi()

    result = seed_demo(api, credential)

    assert api.captured_credential == credential
    assert api.logged_out
    assert result.created == 10
    assert result.reused == 0
    assert result.prioritised == 10
    assert [(team, uen, priority) for team, uen, priority, _ in api.created] == [
        (team, uen, priority)
        for team in TEAMS
        for uen, priority in zip(SEED_UENS, SEED_PRIORITIES, strict=True)
    ]
    assert [(team, uen) for team, uen, _, _ in api.created] == [
        (team, uen) for team in TEAMS for uen in SEED_UENS
    ]
    assert len(api.completed) == 10
    assert api.priorities == []
    assert all(item["status"] == "COMPLETED" for item in api.existing)


def test_seed_reuses_matching_team_and_uen_but_still_applies_priority() -> None:
    credential = secrets.token_urlsafe(24)
    api = FakeSeedApi(
        [
            {
                "team_id": "TEAM_A",
                "requested_uen": SEED_UENS[0],
                "case_id": "existing",
                "priority": None,
                "status": "COMPLETED",
                "final_outcome": "MOCK_GOLDTIER_SUBMITTED",
            }
        ]
    )

    result = seed_demo(api, credential)

    assert result.created == 9
    assert result.reused == 1
    assert result.prioritised == 10
    assert api.priorities[0] == ("existing", 10)


def test_second_seed_reuses_all_successful_cases_without_duplicates() -> None:
    credential = secrets.token_urlsafe(24)
    api = FakeSeedApi()

    first = seed_demo(api, credential)
    second = seed_demo(api, credential)

    assert first.created == 10
    assert second.created == 0
    assert second.reused == 10
    assert len(api.existing) == 10
    assert len({(item["team_id"], item["requested_uen"]) for item in api.existing}) == 10
    assert all(item["status"] == "COMPLETED" for item in api.existing)


def test_seed_ignores_unrelated_shared_cases_but_validates_seed_identities() -> None:
    unrelated = {
        "team_id": None,
        "requested_uen": "LEGACY",
        "case_id": "unrelated-legacy-case",
        "priority": None,
        "status": "WAITING_FOR_REVIEW",
        "final_outcome": None,
    }
    api = FakeSeedApi([unrelated])

    result = seed_demo(api, secrets.token_urlsafe(24))

    assert result.created == 10
    assert unrelated in api.existing
    assert len(api.existing) == 11


def test_seed_prefers_exact_showcase_case_when_unrelated_history_collides() -> None:
    collision = {
        "team_id": "TEAM_A",
        "requested_uen": SEED_UENS[0],
        "case_id": "unrelated-pending-case",
        "priority": None,
        "status": "PENDING_INPUTS",
        "final_outcome": None,
    }
    showcase = {
        "team_id": "TEAM_A",
        "requested_uen": SEED_UENS[0],
        "case_id": "showcase-case",
        "priority": 10,
        "status": "COMPLETED",
        "final_outcome": "MOCK_GOLDTIER_SUBMITTED",
    }
    api = FakeSeedApi([collision, showcase])

    result = seed_demo(api, secrets.token_urlsafe(24))

    assert result.reused == 1
    assert "unrelated-pending-case" not in api.completed
    assert ("unrelated-pending-case", 10) not in api.priorities


def test_seed_fails_when_final_portfolio_verification_is_not_successful() -> None:
    class BrokenVerificationApi(FakeSeedApi):
        def complete_case(self, case_id: str) -> None:
            self.completed.append(case_id)

    with pytest.raises(RuntimeError, match="verification"):
        seed_demo(BrokenVerificationApi(), secrets.token_urlsafe(24))


def test_seeder_main_exits_nonzero_without_printing_credential_on_verification_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    credential = secrets.token_urlsafe(24)

    class BrokenVerificationApi(FakeSeedApi):
        def complete_case(self, case_id: str) -> None:
            self.completed.append(case_id)

    monkeypatch.setattr("getpass.getpass", lambda _prompt: credential)
    monkeypatch.setattr(
        "scripts.seed_phase13_demo.HttpSeedApi",
        lambda _base_url: BrokenVerificationApi(),
    )

    assert seed_main(["--base-url", "http://127.0.0.1:8000"]) == 1
    output = capsys.readouterr()
    assert "verification" in output.err
    assert credential not in output.out + output.err


class ApplicationSeedApi:
    def __init__(self, client: RawTestClient) -> None:
        self.client = client
        self.csrf = ""

    def login(self, credential: str) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"user_id": DIRECTOR_USER_ID, "password": credential},
        )
        assert response.status_code == 200
        self.csrf = response.json()["csrf_token"]

    def list_cases(self) -> list[dict[str, Any]]:
        response = self.client.get("/api/clm/zero-touch/cases")
        assert response.status_code == 200
        return response.json()

    def create_case(self, team_id: str, uen: str, priority: int | None) -> str:
        response = self.client.post(
            "/api/demo/clm/zero-touch/cases",
            json={
                "uen": uen,
                "team_id": team_id,
                "priority": priority,
                "scenario": "STRAIGHT_THROUGH",
            },
            headers={"X-CSRF-Token": self.csrf},
        )
        assert response.status_code == 201
        assert response.json()["case"]["priority"] == priority
        return response.json()["case"]["case_id"]

    def complete_case(self, case_id: str) -> None:
        response = self.client.post(
            f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
            content=_synthetic_pdf(),
            headers={
                "Content-Type": "application/pdf",
                "X-Document-Name": "phase13-synthetic-profile.pdf",
                "X-CSRF-Token": self.csrf,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED", (
            response.json()["case"]["requested_uen"],
            response.json()["active_exceptions"],
        )
        assert response.json()["clm"]["status"] == "MOCK_GOLDTIER_SUBMITTED"

    def set_priority(self, case_id: str, priority: int | None) -> None:
        response = self.client.patch(
            f"/api/clm/zero-touch/cases/{case_id}/priority",
            json={"priority": priority},
            headers={"X-CSRF-Token": self.csrf},
        )
        assert response.status_code == 200

    def logout(self) -> None:
        response = self.client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": self.csrf},
        )
        assert response.status_code == 204


def test_memory_mode_seed_twice_produces_genuine_shared_team_portfolios() -> None:
    credential = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(credential)
    authentication = build_test_authentication_service(
        {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}
    )
    application = create_app(
        ordinary_test_settings(demo_controls_enabled=True),
        authentication_service=authentication,
    )
    director_api = ApplicationSeedApi(RawTestClient(application))

    first = seed_demo(director_api, credential)
    second = seed_demo(director_api, credential)

    assert first == type(first)(created=10, reused=0, prioritised=10)
    assert second == type(second)(created=0, reused=10, prioritised=10)
    expected_by_team = {
        "TEAM_A": list(SEED_PRIORITIES),
        "TEAM_B": list(SEED_PRIORITIES),
    }
    for user_id, expected_team in (
        ("maya-lim", "TEAM_A"),
        ("ethan-tan", "TEAM_A"),
        ("sophia-ng", "TEAM_B"),
        ("ryan-lee", "TEAM_B"),
    ):
        client = RawTestClient(application)
        assert (
            client.post(
                "/api/auth/login",
                json={"user_id": user_id, "password": credential},
            ).status_code
            == 200
        )
        cases = client.get("/api/clm/zero-touch/cases").json()
        assert [item["team_id"] for item in cases] == [expected_team] * 5
        assert [item["priority"] for item in cases] == expected_by_team[expected_team]
        assert [item["status"] for item in cases] == ["COMPLETED"] * 5

    director = RawTestClient(application)
    assert (
        director.post(
            "/api/auth/login",
            json={"user_id": DIRECTOR_USER_ID, "password": credential},
        ).status_code
        == 200
    )
    global_cases = director.get("/api/clm/zero-touch/cases").json()
    assert len(global_cases) == 10
    assert {item["team_id"] for item in global_cases} == set(TEAMS)


def test_http_seeder_runs_twice_against_one_live_memory_backend() -> None:
    credential = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(credential)
    authentication = build_test_authentication_service(
        {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}
    )
    application = create_app(
        ordinary_test_settings(demo_controls_enabled=True),
        authentication_service=authentication,
    )
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="error")
    )
    worker = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    worker.start()
    deadline = time.monotonic() + 10
    while not server.started and worker.is_alive() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started
    try:
        api = HttpSeedApi(f"http://127.0.0.1:{port}")
        first = seed_demo(api, credential)
        second = seed_demo(api, credential)
        assert first == type(first)(created=10, reused=0, prioritised=10)
        assert second == type(second)(created=0, reused=10, prioritised=10)
    finally:
        server.should_exit = True
        worker.join(timeout=10)
        listener.close()
    assert not worker.is_alive()
