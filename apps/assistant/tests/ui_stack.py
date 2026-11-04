"""A disposable local stack for the AI Models "Set up AI" journey in a real browser.

The real assistant service (create_app: model admin, setup view, session ledgers, the
qualification job) runs on loopback with:

- mock Anthropic and OpenRouter APIs (no network, nothing spent; keys are test sentinels);
- the fake CLM backend of the assistant tests (synthetic users; every browser request is
  signed in as the synthetic HR administrator);
- new stores in a disposable data folder (never apps/assistant/data, never a live store);
- the AI Models page bundle (built by apps/frontend/e2e/support/ai-models-page.mjs) at "/".

It never reads apps/assistant/.env and refuses any non-loopback connection. Test-only.

    python -m tests.ui_stack --data-dir DIR --port 8765 --static DIR [--scenario NAME] [--set k=v]

A restart is the same command with the same --data-dir: stores persist, HR keys do not.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _guard_network() -> None:
    """Refuse every non-loopback connection or name lookup (mirrors the suite guard)."""

    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo
    real_create_connection = asyncio.base_events.BaseEventLoop.create_connection

    def host_of(address: Any) -> str:
        return str(address[0] if isinstance(address, tuple) else address)

    def connect(self: socket.socket, address: Any) -> Any:
        if self.family in (socket.AF_INET, socket.AF_INET6) and host_of(address) not in LOOPBACK:
            raise OSError("ui_stack: non-loopback connection refused")
        return real_connect(self, address)

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        if host not in LOOPBACK and host is not None:
            raise OSError("ui_stack: non-loopback name lookup refused")
        return real_getaddrinfo(host, *args, **kwargs)

    async def create_connection(
        self: Any, protocol_factory: Any, host: Any = None, *a: Any, **k: Any
    ) -> Any:
        if host is not None and host not in LOOPBACK:
            raise OSError("ui_stack: non-loopback connection refused")
        return await real_create_connection(self, protocol_factory, host, *a, **k)

    socket.socket.connect = connect  # type: ignore[method-assign, assignment]
    socket.getaddrinfo = getaddrinfo
    asyncio.base_events.BaseEventLoop.create_connection = create_connection  # type: ignore[method-assign]


SCENARIOS = ("fresh", "claude-existing-record", "gptoss-existing-history")


def _value(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def build(data_dir: Path, port: int, scenario: str, overrides: dict[str, Any]) -> Any:
    from ai_assistant import (
        anthropic_runtime,
        key_sources,
        model_admin,
        remote_test,
        synthetic_eligibility,
    )
    from ai_assistant.main import create_app
    from ai_assistant.model_admin import ModelSelector
    from assistant_eval.qualification import run_job
    from tests.test_claude_hr_enablement import NO_DECISIONS
    from tests.test_claude_runtime import Claude
    from tests.test_model_management import Backend, Baseline, ThreadRun, profile, write_profiles
    from tests.test_remote_test import D094, OpenRouter, config, listing

    monkeypatch = pytest.MonkeyPatch()
    # No .env, empty HR key stores (keys are entered in the page and kept in memory only).
    monkeypatch.setattr(key_sources, "ENV_FILE", data_dir / "no-such.env")
    monkeypatch.setattr(key_sources, "HR_STORE", key_sources.HrCredential())
    monkeypatch.setattr(key_sources, "ANTHROPIC_STORE", key_sources.HrCredential())
    monkeypatch.setattr(key_sources, "_SESSION_CHECK", None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv(anthropic_runtime.CREDENTIAL_VARIABLE, raising=False)
    synthetic_eligibility._tickets.clear()

    origin = f"http://127.0.0.1:{port}"
    data_dir.mkdir(parents=True, exist_ok=True)
    profiles = data_dir / "profiles.json"
    if not profiles.exists():
        write_profiles(profiles, profile())
    values: dict[str, Any] = {
        # Claude by HR enablement (no decision settings), GPT-OSS by its launcher settings.
        **NO_DECISIONS,
        **{k: v for k, v in D094.items() if not k.startswith("local_api_test_qualification")},
        "allowed_origins": [origin],
        "model_admin_db_path": str(data_dir / "state" / "admin.sqlite3"),
        # The D-118 session stores: created from the page, never by this harness.
        "anthropic_ledger_path": str(data_dir / "budget" / "sessions" / "anthropic.sqlite3"),
        "budget_ledger_path": str(data_dir / "budget" / "sessions" / "openrouter.sqlite3"),
        "budget_daily_cap_micro_usd": 5_000_000,
        "anthropic_daily_cap_micro_usd": 5_000_000,
    }
    values.update(overrides)
    settings = config(data_dir, profiles, **values)
    # config() supplies the D-094 question list unless the scenario overrides it; drop it so
    # the application's own default applies (what a teammate's launcher gets).
    for name in ("local_api_test_qualification_questions", "local_api_test_qualification_count"):
        if name not in overrides:
            settings = settings.model_copy(update={name: type(settings).model_fields[name].default})

    if scenario == "gptoss-existing-history":
        # An earlier-design GPT-OSS ledger kept at its old path (never used or changed).
        from ai_assistant.budget import BudgetLedger

        legacy = data_dir / "budget" / "ledger.sqlite3"
        if not legacy.exists():
            legacy.parent.mkdir(parents=True, exist_ok=True)
            BudgetLedger.initialise(
                legacy, cap_micro_usd=1_000_000, opening_usage_micro_usd=0, key_alias="key-01"
            )

    claude, openrouter, backend, baseline = Claude(), OpenRouter(), Backend(), Baseline()
    monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *a, **k: baseline)
    monkeypatch.setattr(model_admin, "SUPERVISE_SECONDS", 0.05)
    monkeypatch.setattr(remote_test, "fetch_public", listing)
    app = create_app(
        settings, clm_transport=httpx.MockTransport(lambda request: backend.handler(request))
    )
    selector: ModelSelector = app.state.model_selector

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.anthropic.com":
            return claude.handler(request)
        return openrouter.handler(request)

    # The service's own key lookup (HR session key, then process environment, then .env); no
    # server key exists here, so HR enters one in the page.
    selector.environ = None
    selector.transport = httpx.MockTransport(provider)
    selector.fetch = listing

    def launch(qualification_id: str) -> ThreadRun:
        return ThreadRun(
            lambda: run_job(
                qualification_id,
                selector.settings,
                environ=selector.environ,
                transport=selector.transport,
                fetch=listing,
            )
        )

    selector.launch = launch

    if scenario == "claude-existing-record":
        _existing_claude_record(app, claude, origin)
    return app, origin


def _existing_claude_record(app: Any, claude: Any, origin: str) -> None:
    """A Claude enablement record from before D-118 with no session store yet."""

    from fastapi.testclient import TestClient

    from ai_assistant import anthropic_runtime, key_sources
    from tests.test_claude_hr_enablement import CONFIRMATIONS, READ, SETUP
    from tests.test_claude_runtime import KEY, WORKSPACE

    settings = app.state.model_selector.settings
    marker = Path(settings.model_admin_db_path).parent / "ui_stack_existing_record"
    if marker.exists():
        return  # a restart: the record is already there
    client = TestClient(app, headers={"Origin": origin})
    client.cookies.set("clm_session", "hr-session")
    assert (
        client.put(
            "/assistant/admin/models/credential/anthropic", json={"api_key": KEY}
        ).status_code
        == 200
    )
    assert client.post(READ).json()["workspace_id"] == WORKSPACE
    enabled = client.put(
        SETUP,
        json={
            "expected_revision": 0,
            "enabled": True,
            "workspace_id": WORKSPACE,
            "workspace_limit_micro_usd": 5_000_000,
            "confirmations": CONFIRMATIONS,
        },
    )
    assert enabled.status_code == 200, enabled.text
    # Before D-118 there was no session store: remove the one enabling just created, and the
    # HR key (a restart since then).
    Path(anthropic_runtime.ledger_file(settings)).unlink()
    key_sources.ANTHROPIC_STORE.clear()
    anthropic_runtime._last.clear()
    marker.write_text("created", encoding="utf-8")


class Front:
    """ASGI front door: the page at "/", /api/assistant/* to the service as /assistant/*,
    signed in as the synthetic HR administrator (the fake backend's session)."""

    def __init__(self, app: Any, static: Path, session: str = "hr-session") -> None:
        self.app = app
        self.static = static
        self.session = session.encode()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]
        if path.startswith("/api/assistant"):
            inner = dict(scope)
            inner["path"] = path[len("/api") :]
            inner["raw_path"] = inner["path"].encode()
            headers = [(k, v) for k, v in scope["headers"] if k != b"cookie"]
            headers.append((b"cookie", b"clm_session=" + self.session))
            inner["headers"] = headers
            await self.app(inner, receive, send)
            return
        name = {"/": "index.html"}.get(path, path.lstrip("/"))
        file = (self.static / name).resolve()
        if self.static.resolve() not in file.parents or not file.is_file():
            await _respond(send, 404, b"not found", b"text/plain")
            return
        kind = {".html": b"text/html", ".js": b"text/javascript", ".css": b"text/css"}.get(
            file.suffix, b"application/octet-stream"
        )
        await _respond(send, 200, file.read_bytes(), kind)


async def _respond(send: Any, status: int, body: bytes, kind: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", kind), (b"cache-control", b"no-store")],
        }
    )
    await send({"type": "http.response.body", "body": body})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--static", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--scenario", choices=SCENARIOS, default="fresh")
    parser.add_argument("--set", action="append", default=[], metavar="SETTING=VALUE")
    args = parser.parse_args(argv)
    data_dir = args.data_dir.resolve()
    live = [(Path(__file__).resolve().parents[1] / "data").resolve()]
    if os.environ.get("LOCALAPPDATA"):
        live.append((Path(os.environ["LOCALAPPDATA"]) / "DataDividendsCLM").resolve())
    if any(data_dir == root or root in data_dir.parents for root in live):
        parser.error("--data-dir must be a disposable folder, never a runtime data root")
    overrides = dict(item.split("=", 1) for item in args.set)
    _guard_network()
    app, _ = build(data_dir, args.port, args.scenario, {k: _value(v) for k, v in overrides.items()})
    import uvicorn

    print(f"ui_stack ready on http://127.0.0.1:{args.port}", flush=True)
    uvicorn.run(Front(app, args.static), host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
