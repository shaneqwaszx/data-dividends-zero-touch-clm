"""PR #178 dashboard insights on the hosted deployment: refused at the server boundary.

The public route is ``POST /api/assistant/dashboard/insights``; Caddy forwards ``/api/assistant/*``
to the assistant, whose app route is ``/assistant/dashboard/insights``. On the hosted deployment
the hosting layer (``assistant_hosting.guard``) answers it with ``503
DASHBOARD_INSIGHTS_UNAVAILABLE`` before the session, origin or route checks, so neither the
route nor any model (local fallback, OpenRouter, Anthropic) is ever reached. The route's own
model selection (``main.py``) is a second, independent check. Outside the hosted service the
dashboard is unchanged (tests/test_dashboard_insights.py).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from ai_assistant.dashboard_insights import DashboardInsights
from assistant_hosting.guard import DASHBOARD_INSIGHTS
from tests import test_hosting
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_dashboard_insights import FINDINGS
from tests.test_hosted_claude import (
    Hosted,
    HostedClm,
    hosted_replies,  # noqa: F401 (fixture)
    post_headers,
)

UNAVAILABLE = {"code": "DASHBOARD_INSIGHTS_UNAVAILABLE", "message": "AI insights are unavailable."}


class NeverCalled:
    """Any model the route could reach. Every use is recorded."""

    name = "never"

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.calls = 0

    def complete(self, messages: Any) -> Any:
        self.calls += 1
        raise AssertionError(f"{self.kind} model called")

    async def stream(self, messages: Any) -> Any:  # pragma: no cover - never reached
        self.calls += 1
        raise AssertionError(f"{self.kind} model called")
        yield


@pytest.fixture
def live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hosted_replies: Any) -> Hosted:  # noqa: F811
    hosted = Hosted(tmp_path, monkeypatch, HostedClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    return hosted


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    seen = {"write": 0, "candidates": 0}
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


def test_the_public_and_internal_routes_are_the_ones_refused() -> None:
    from ai_assistant.main import create_app

    caddy = (Path(test_hosting.CADDYFILE)).read_text(encoding="utf-8")
    assert "@assistant path /api/assistant /api/assistant/*" in caddy
    routes = {getattr(route, "path", "") for route in create_app().routes}  # type: ignore[call-arg]
    assert DASHBOARD_INSIGHTS in routes


@pytest.mark.parametrize(
    ("method", "path", "headers"),
    [
        ("POST", "/assistant/dashboard/insights", "rm"),
        ("POST", "/assistant/dashboard/insights/", "rm"),
        ("POST", "/assistant/Dashboard/Insights", "rm"),
        ("POST", "/assistant/dashboard/insights/extra", "rm"),
        ("POST", "/assistant/dashboard%2Finsights", "rm"),
        ("GET", "/assistant/dashboard/insights", "rm"),
        ("PUT", "/assistant/dashboard/insights", "rm"),
        ("POST", "/assistant/dashboard/insights", "none"),  # refused before the session check
        ("POST", "/assistant/dashboard/insights", "hr"),
    ],
)
def test_direct_requests_never_reach_the_route_or_any_model_with_claude_active(
    live: Hosted, spies: dict[str, int], method: str, path: str, headers: str
) -> None:
    hosted = live
    before = len(hosted.claude.requests)
    sent = {"rm": post_headers("rm-a"), "hr": post_headers("hr"), "none": {}}[headers]
    reply = hosted.client.request(method, path, headers=sent, json=FINDINGS)
    assert reply.status_code == 503, (path, reply.text)
    assert reply.json() == {"detail": UNAVAILABLE}
    assert spies == {"write": 0, "candidates": 0}  # the route never ran
    assert len(hosted.claude.requests) == before  # no Anthropic request, not even a preflight


def test_no_fallback_or_provider_is_reached_even_if_the_routes_own_check_is_bypassed(
    live: Hosted, monkeypatch: pytest.MonkeyPatch, spies: dict[str, int]
) -> None:
    hosted = live
    # Every model the route could pick: the active one, the local fallback, an OpenRouter one.
    local, openrouter = NeverCalled("local"), NeverCalled("openrouter")
    active = hosted.selector.current()
    monkeypatch.setattr(hosted.selector, "local_fallback", lambda: replace(active, model=local))
    monkeypatch.setattr("ai_assistant.main.hosted_deployment", lambda: None)  # route check off
    before = len(hosted.claude.requests)
    for model in (openrouter, active.model):
        monkeypatch.setattr(hosted.selector, "current", lambda m=model: replace(active, model=m))
        reply = hosted.client.post(DASHBOARD_INSIGHTS, headers=post_headers("rm-a"), json=FINDINGS)
        assert reply.status_code == 503 and reply.json() == {"detail": UNAVAILABLE}
    assert (local.calls, openrouter.calls) == (0, 0)
    assert spies == {"write": 0, "candidates": 0}
    assert len(hosted.claude.requests) == before


def test_the_guard_refuses_on_the_model_free_hosted_service_too(tmp_path: Path) -> None:
    # Stage A / R2.1: the hosted service with no model at all.
    with test_hosting.service(tmp_path, test_hosting.Clm()) as client:
        reply = client.post(
            DASHBOARD_INSIGHTS, headers=test_hosting.post_headers("rm-a"), json=FINDINGS
        )
        assert reply.status_code == 503 and reply.json() == {"detail": UNAVAILABLE}
        # The rest of the service is unchanged: health still answers.
        assert (
            client.get("/assistant/health", headers=test_hosting.session("rm-a")).status_code == 200
        )


def test_the_chat_paths_and_other_routes_are_not_caught_by_the_insights_refusal(
    live: Hosted,
) -> None:
    from assistant_hosting.guard import _dashboard_insights

    for path in (
        "/assistant/dashboard",
        "/assistant/dashboard/insight",
        "/assistant/dashboard/insightsx",
        "/assistant/general/chat/stream",
        "/assistant/support/chat",
        "/assistant/health",
    ):
        assert _dashboard_insights(path) is False, path
    status, _ = live.ask()
    assert status == 200  # case chat still answered (by Claude, in this harness)


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
