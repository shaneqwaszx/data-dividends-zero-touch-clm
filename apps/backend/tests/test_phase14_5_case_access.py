"""Focused dynamic-team, Director-filter, and HR zero-case-access proofs."""

from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings

from app.main import create_app


def _login(client: RawTestClient, user_id: str) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_dynamic_gamma_filter_is_empty_and_authority_is_server_owned() -> None:
    app = create_app(ordinary_test_settings())
    hr = RawTestClient(app)
    hr_csrf = _login(hr, "biz-ops")
    created = hr.post(
        "/api/admin/teams",
        headers={"X-CSRF-Token": hr_csrf},
        json={"display_name": "Gamma", "client_scope_label": "Gamma"},
    )
    assert created.status_code == 201
    gamma_id = created.json()["team_id"]

    director = RawTestClient(app)
    _login(director, "olivia-koh")
    assert gamma_id in {item["team_id"] for item in director.get("/api/teams/options").json()}
    assert director.get(f"/api/clm/zero-touch/cases?team_filter={gamma_id}").json() == []
    assert (
        director.get(f"/api/clm/zero-touch/dashboard?team_filter={gamma_id}").json()["totals"][
            "total_cases"
        ]
        == 0
    )

    team_actor = RawTestClient(app)
    _login(team_actor, "maya-lim")
    denied = team_actor.get("/api/clm/zero-touch/cases?team_filter=TEAM_A")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "TEAM_FILTER_FORBIDDEN"
    assert hr.get("/api/clm/zero-touch/cases").status_code == 403
