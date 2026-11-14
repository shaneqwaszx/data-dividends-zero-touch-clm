"""PR #178 dashboard insights on the model-free hosted service (R2.1): refused at the server
boundary.

The public route is ``POST /api/assistant/dashboard/insights``; Caddy forwards ``/api/assistant/*``
to the assistant, whose app route is ``/assistant/dashboard/insights``. The hosting layer
(``assistant_hosting.guard``) answers it with ``503 DASHBOARD_INSIGHTS_UNAVAILABLE`` before the
session, origin or route checks, so neither the route nor any model is ever reached. Outside
the hosted service the dashboard is unchanged (tests/test_dashboard_insights.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ai_assistant.dashboard_insights import DashboardInsights
from assistant_hosting.guard import DASHBOARD_INSIGHTS, _dashboard_insights
from tests import test_hosting
from tests.test_dashboard_insights import FINDINGS

UNAVAILABLE = {"code": "DASHBOARD_INSIGHTS_UNAVAILABLE", "message": "AI insights are unavailable."}


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    seen = {"write": 0}
    real = DashboardInsights.write

    def write(self: DashboardInsights, *args: Any, **kwargs: Any) -> Any:
        seen["write"] += 1
        return real(self, *args, **kwargs)

    monkeypatch.setattr(DashboardInsights, "write", write)
    return seen


def test_the_public_and_internal_routes_are_the_ones_refused() -> None:
    from ai_assistant.main import create_app

    caddy = Path(test_hosting.CADDYFILE).read_text(encoding="utf-8")
    assert "@assistant path /api/assistant /api/assistant/*" in caddy
    routes = {getattr(route, "path", "") for route in create_app().routes}  # type: ignore[call-arg]
    assert DASHBOARD_INSIGHTS in routes


@pytest.mark.parametrize(
    ("method", "path", "token"),
    [
        ("POST", "/assistant/dashboard/insights", "rm-a"),
        ("POST", "/assistant/dashboard/insights/", "rm-a"),
        ("POST", "/assistant/Dashboard/Insights", "rm-a"),
        ("POST", "/assistant/dashboard/insights/extra", "rm-a"),
        ("POST", "/assistant/dashboard%2Finsights", "rm-a"),
        ("GET", "/assistant/dashboard/insights", "rm-a"),
        ("POST", "/assistant/dashboard/insights", None),
        ("POST", "/assistant/dashboard/insights", "hr"),
    ],
)
def test_direct_requests_never_reach_the_route_or_any_model(
    tmp_path: Path, calls: dict[str, int], method: str, path: str, token: str | None
) -> None:
    clm = test_hosting.Clm()
    with test_hosting.service(tmp_path, clm) as client:
        headers = test_hosting.post_headers(token) if token else {}
        reply = client.request(method, path, headers=headers, json=FINDINGS)
        assert reply.status_code == 503, (path, reply.text)
        assert reply.json() == {"detail": UNAVAILABLE}
    assert calls == {"write": 0}
    assert clm.requests == []  # not even the backend's who-is-this call


def test_other_routes_are_not_caught_and_the_service_still_answers(tmp_path: Path) -> None:
    for path in (
        "/assistant/dashboard",
        "/assistant/dashboard/insight",
        "/assistant/dashboard/insightsx",
        "/assistant/health",
    ):
        assert _dashboard_insights(path) is False, path
    with test_hosting.service(tmp_path, test_hosting.Clm()) as client:
        health = client.get("/assistant/health", headers=test_hosting.session("rm-a"))
        assert health.status_code == 200


# --- QG F-1, F-3, F-4: the router's own path semantics, and the route's own refusal -------------

BYPASS_FORMS = [
    ("POST", "/assistant/dashboard/insights%0A"),
    ("POST", "/assistant/dashboard/insights%0a"),
    ("POST", "/assistant/dashboard/insights%0D"),
    ("POST", "/assistant/dashboard/insights%00"),
    ("POST", "/assistant/dashboard/insights%09"),
    ("POST", "/assistant/dashboard/insights%7F"),
    ("POST", "/assistant/dashboard/insights/%0A"),
    ("HEAD", "/assistant/dashboard/insights"),
    ("OPTIONS", "/assistant/dashboard/insights"),
    ("HEAD", "/assistant/dashboard/insights%0A"),
    ("POST", "/assistant/dashboard/./insights"),
    ("POST", "/assistant/x/../dashboard/insights"),
    ("POST", "/assistant/dashboard/%2e/insights"),
    ("POST", "/assistant/dashboard/insights?x=1"),
    ("POST", "/assistant/dashboard/insights;x"),
    ("POST", "/assistant//dashboard/insights"),
]


@pytest.fixture
def route_runs(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    seen = {"write": 0, "candidates": 0, "fallback": 0}
    real_write, real_candidates = DashboardInsights.write, DashboardInsights.candidates

    def write(self: DashboardInsights, *args: Any, **kwargs: Any) -> Any:
        seen["write"] += 1
        return real_write(self, *args, **kwargs)

    def candidates(cls: Any, *args: Any, **kwargs: Any) -> Any:
        seen["candidates"] += 1
        return real_candidates(*args, **kwargs)

    monkeypatch.setattr(DashboardInsights, "write", write)
    monkeypatch.setattr(DashboardInsights, "candidates", classmethod(candidates))
    return seen


@pytest.mark.parametrize(("method", "path"), BYPASS_FORMS)
def test_no_path_form_reaches_the_route_on_the_model_free_hosted_service(
    tmp_path: Path, route_runs: dict[str, int], method: str, path: str
) -> None:
    clm = test_hosting.Clm()
    with test_hosting.service(tmp_path, clm) as client:
        reply = client.request(
            method, path, headers=test_hosting.post_headers("rm-a"), json=FINDINGS
        )
    # Refused by the guard (503), or no such route (404/405); never answered by the route.
    assert reply.status_code in (404, 405, 503), (path, reply.status_code, reply.text)
    assert route_runs == {"write": 0, "candidates": 0, "fallback": 0}, path


@pytest.mark.parametrize("path", ["/assistant/dashboard/insights%0A", "/assistant/health%0A"])
def test_a_control_character_in_any_path_is_refused_before_anything_else(
    tmp_path: Path, path: str
) -> None:
    clm = test_hosting.Clm()
    with test_hosting.service(tmp_path, clm) as client:
        reply = client.request("GET", path, headers=test_hosting.session("rm-a"))
    assert reply.status_code == 404
    assert reply.json() == {"detail": {"code": "NOT_FOUND", "message": "Not found."}}
    assert clm.requests == []  # not even the backend was asked


def test_the_route_refuses_itself_on_the_hosted_service_even_without_the_guard(
    tmp_path: Path, route_runs: dict[str, int]
) -> None:
    import httpx
    from fastapi.testclient import TestClient

    from ai_assistant.main import create_app
    from assistant_hosting.harden import harden

    settings = test_hosting.hosted_settings(tmp_path)
    clm = test_hosting.Clm()
    transport = httpx.MockTransport(clm.handler)
    hardened = create_app(settings, clm_transport=transport)
    harden(hardened, settings, environ=test_hosting.ELIGIBLE, transport=transport)
    assert hardened.state.dashboard_insights_disabled is True
    # The same app without the hosting layer's middleware, but with the hosted flag: what a
    # request that somehow got past the guard would meet.
    bare = create_app(settings, clm_transport=transport)
    bare.state.dashboard_insights_disabled = True
    with TestClient(bare, base_url="http://clm-assistant-proxy:8100") as client:
        reply = client.post(
            DASHBOARD_INSIGHTS, headers=test_hosting.post_headers("rm-a"), json=FINDINGS
        )
    assert reply.status_code == 503
    assert reply.json() == {"detail": UNAVAILABLE}
    assert route_runs == {"write": 0, "candidates": 0, "fallback": 0}
    assert clm.requests == []  # refused before the session was even read
