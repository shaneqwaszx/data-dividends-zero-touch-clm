"""What the hosted service adds to the existing one, without changing any route, gate or answer."""

import os
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from ai_assistant.config import AiAssistantSettings

from .eligibility import CaseGate
from .guard import HostedGuard
from .profile import limits
from .readiness import Readiness


def harden(
    app: FastAPI,
    settings: AiAssistantSettings,
    *,
    environ: Mapping[str, str] | None = None,
    **readiness: Any,
) -> FastAPI:
    # RD-1: every case the assistant loads must be an approved one (load_case in
    # ai_assistant.main). Malformed settings raise here; refusals() stops them before this.
    app.state.case_gate = CaseGate.from_env(os.environ if environ is None else environ)
    # PR #178 dashboard insights: the route refuses itself on the hosted service, whatever
    # reaches it (the guard refuses it first; QG F-1). No model is selected or called.
    app.state.dashboard_insights_disabled = True
    selector = app.state.model_selector
    checks = Readiness(
        settings,
        limits(),
        # ai_assistant carries on without knowledge when its store cannot be opened, and then
        # has no knowledge routes. The schema lists them however the routers were included.
        knowledge_open=lambda: any(
            path.startswith("/assistant/knowledge/") for path in app.openapi()["paths"]
        ),
        model_state=lambda: selector.store.revision(),
        **readiness,
    )

    # Async on purpose: this answers only while the event loop is running, which is what the
    # hang recovery in probe.py needs to know.
    async def live() -> dict[str, str]:
        return {"status": "live"}

    def ready() -> JSONResponse:
        report = checks.report()
        return JSONResponse(report, status_code=200 if report["status"] == "ready" else 503)

    app.add_api_route("/internal/live", live, methods=["GET"], include_in_schema=False)
    app.add_api_route("/internal/ready", ready, methods=["GET"], include_in_schema=False)
    app.add_middleware(
        HostedGuard,
        allowed_origins=frozenset(origin.rstrip("/") for origin in settings.allowed_origins),
        selector=selector,
    )
    return app
