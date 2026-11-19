"""The hosted service's own request boundary (a plain ASGI wrapper, so streams pass through).

Caddy is the first check and this is the second: the service stays safe if an ingress rule is
wrong. The CLM backend remains the only authority on who a user is and what they may read.
This layer only refuses earlier, and it never grants anything.

    /internal/*        loopback peers only (the container's own health check)
    anything else      404 unless it is under /assistant (no API docs, no schema)
    no session cookie  401
    unsafe methods     need a single allowed Origin; ai_assistant accepts a missing one
    AI Models changes  only the listed model-free controls. A provider key never reaches
                       the process, because the request body is not read. R2.2: in the
                       Claude mode (provider.py) also the listed Claude setup, key, spending
                       and qualification routes; the HR key is then held in memory for that
                       HR session only (D-106). OpenRouter's stay refused, except in the
                       OpenRouter mode (D-134, proposed, off by default): then the listed
                       GPT-OSS key, spending, session and qualification routes pass too
    control characters 404 for any path holding one (an encoded newline, NUL, ...), before
                       anything else: the router's `$` would otherwise match a path the exact
                       checks below do not see (QG F-1, F-4)
    dashboard insights 503 DASHBOARD_INSIGHTS_UNAVAILABLE for any method, before the session,
                       origin and route checks (PR #178 / D-128 I7). The hosted deployment
                       approves no model for them (D-129/D-130 cover the four chat paths only),
                       so the route, and with it every local, remote or paid model, is never
                       reached here; the browser hides the panel (D-128 I5). Fifth hosted
                       path (D-130 amendment draft): only while HOSTED_INSIGHTS_DECISION is
                       set in the code, exactly GET .../insights/mode and POST
                       .../insights/generate pass on to the normal checks; nothing else
    external AI data   D-138 A1 (proposed): GET /assistant/health and a successful GET
                       .../cases/<id>/brief also carry ``external_ai``: which hosted
                       providers this deployment registered, which one the active model uses,
                       and the surfaces each may serve (from the reviewed code constants). The
                       browser's external-data notice names the provider from it. It is
                       display data only: it grants nothing, and every other reply (a refusal,
                       the safe 404, any error) passes through unchanged
"""

import json
import re
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from starlette.requests import cookie_parser

from ai_assistant import config as assistant_config
from ai_assistant import data_access
from ai_assistant.clm_client import SESSION_COOKIE_NAME

from .profile import NO_MODEL_NAME

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
App = Callable[[Scope, Receive, Send], Awaitable[None]]

ADMIN_PREFIX = "/assistant/admin/models"
# PR #178: the dashboard insights route, refused whole on the hosted deployment.
DASHBOARD_INSIGHTS = "/assistant/dashboard/insights"
# The fifth hosted path's two routes, the only insights routes that may pass, and only while the
# owner's decision is in the code (config.HOSTED_INSIGHTS_DECISION; None by default).
HOSTED_INSIGHTS_ROUTES = frozenset(
    {
        ("GET", DASHBOARD_INSIGHTS + "/mode"),
        ("POST", DASHBOARD_INSIGHTS + "/generate"),
    }
)


def _dashboard_insights(path: str) -> bool:
    # Any spelling the router or a proxy could treat as the route: case, trailing slashes,
    # sub-paths. (The ASGI path is already percent-decoded.)
    folded = path.lower().rstrip("/")
    return folded == DASHBOARD_INSIGHTS or folded.startswith(DASHBOARD_INSIGHTS + "/")


# D-138 A1: the case brief, whose successful reply also carries the external AI data.
BRIEF_PATH = re.compile(r"/assistant/cases/[^/]+/brief")
# The browser's notice surfaces each hosted chat path is shown on (config.HOSTED_CHAT_PATHS).
CHAT_PATH_SURFACES = {"general": "general", "support": "support", "try_change": "try"}

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
LOOPBACK_PEERS = frozenset({"127.0.0.1", "::1"})
# Allowlisted, so a route added later is refused here until it is reviewed for hosting. Every
# one of these keeps its own capability check, compare-and-set and audit row in ai_assistant.
ADMIN_CHANGES = (
    ("PUT", re.compile(r"/data-access")),
    ("POST", re.compile(r"/recovery/requests")),
    ("POST", re.compile(r"/recovery/requests/[^/]+/close")),
    ("POST", re.compile(r"/rollback")),
    ("POST", re.compile(r"/[^/]+/activate")),
    ("POST", re.compile(r"/[^/]+/connection-test")),
)


# R2.2: what HR needs to set up, fund, qualify and run Claude Sonnet 5.5 (Claude mode only).
# Each keeps its own capability check, compare-and-set, rate limit and audit row.
CLAUDE_CHANGES = (
    ("PUT", re.compile(r"/credential/anthropic")),
    ("DELETE", re.compile(r"/credential/anthropic")),
    ("POST", re.compile(r"/provider/anthropic/workspace-read")),
    ("PUT", re.compile(r"/provider/anthropic")),
    ("PUT", re.compile(r"/budget/claude/controls")),
    ("PUT", re.compile(r"/budget/claude/lifetime-cap")),
    ("POST", re.compile(r"/session/start")),
    ("PUT", re.compile(r"/session/allowance")),
    ("POST", re.compile(r"/budget/resume")),
    ("POST", re.compile(r"/anthropic_claude_sonnet_5_5_(?:medium|low)/qualifications")),
    ("POST", re.compile(r"/qualifications/[^/]+/cancel")),
)


# D-134 (proposed): what HR needs to set up, fund, qualify and run GPT-OSS 120B (OpenRouter
# mode only). Each keeps its own capability check, compare-and-set, rate limit and audit row.
OPENROUTER_CHANGES = (
    ("PUT", re.compile(r"/credential")),
    ("DELETE", re.compile(r"/credential")),
    ("PUT", re.compile(r"/budget/controls")),
    ("PUT", re.compile(r"/budget/lifetime-cap")),
    ("POST", re.compile(r"/budget/provider-refresh")),
    ("POST", re.compile(r"/session/start")),
    ("PUT", re.compile(r"/session/allowance")),
    ("POST", re.compile(r"/budget/resume")),
    ("POST", re.compile(r"/openrouter_gpt_oss_120b/qualifications")),
    ("POST", re.compile(r"/qualifications/[^/]+/cancel")),
)


def _admin_change_allowed(
    method: str, path: str, *, claude: bool = False, openrouter: bool = False
) -> bool:
    tail = path[len(ADMIN_PREFIX) :]
    changes: tuple[tuple[str, re.Pattern[str]], ...] = ADMIN_CHANGES
    if claude:
        changes += CLAUDE_CHANGES
    if openrouter:
        changes += OPENROUTER_CHANGES
    return any(method == verb and shape.fullmatch(tail) for verb, shape in changes)


async def _json(send: Send, status: int, body: dict[str, Any]) -> None:
    payload = json.dumps(body, separators=(",", ":")).encode("ascii")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


async def _refuse(send: Send, status: int, code: str, message: str) -> None:
    await _json(send, status, {"detail": {"code": code, "message": message}})


def _headers(scope: Scope, name: bytes) -> list[str]:
    return [
        value.decode("latin-1") for key, value in scope.get("headers", ()) if key.lower() == name
    ]


def _has_session(scope: Scope) -> bool:
    # The same parser the service uses, so both layers read one header the same way.
    return any(cookie_parser(raw).get(SESSION_COOKIE_NAME) for raw in _headers(scope, b"cookie"))


class HostedGuard:
    def __init__(
        self,
        app: App,
        *,
        allowed_origins: frozenset[str],
        selector: Any,
        claude: bool = False,
        openrouter: bool = False,
    ) -> None:
        self._app = app
        self._origins = allowed_origins
        self._selector = selector
        self._claude = claude
        self._openrouter = openrouter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        path: str = scope["path"]
        method: str = scope["method"]
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in path):
            await _refuse(send, 404, "NOT_FOUND", "Not found.")
            return
        if path.startswith("/internal/"):
            peer = scope.get("client")
            if peer is None or peer[0] not in LOOPBACK_PEERS:
                await _refuse(send, 404, "NOT_FOUND", "Not found.")
                return
            await self._app(scope, receive, send)
            return
        if not path.startswith("/assistant/"):
            await _refuse(send, 404, "NOT_FOUND", "Not found.")
            return
        if _dashboard_insights(path) and (
            assistant_config.HOSTED_INSIGHTS_DECISION is None
            or not assistant_config.HOSTED_INSIGHTS_PROVIDERS
            or (method, path) not in HOSTED_INSIGHTS_ROUTES
        ):
            await _refuse(
                send, 503, "DASHBOARD_INSIGHTS_UNAVAILABLE", "AI insights are unavailable."
            )
            return
        if not _has_session(scope):
            await _refuse(send, 401, "AUTHENTICATION_REQUIRED", "Please sign in again.")
            return
        if method not in SAFE_METHODS and not await self._origin_allowed(scope, send):
            return
        if (
            method not in SAFE_METHODS
            and path.startswith(ADMIN_PREFIX + "/")
            and not _admin_change_allowed(
                method, path, claude=self._claude, openrouter=self._openrouter
            )
        ):
            self._audit_refusal()
            await _refuse(send, 403, "HOSTED_REMOTE_DISABLED", "This action is not available here.")
            return
        if method == "GET" and path == "/assistant/health":
            await self._health(scope, receive, send)
            return
        if method == "GET" and BRIEF_PATH.fullmatch(path):
            await self._brief(scope, receive, send)
            return
        await self._app(scope, receive, send)

    async def _origin_allowed(self, scope: Scope, send: Send) -> bool:
        origins = _headers(scope, b"origin")
        if len(origins) != 1:
            await _refuse(send, 403, "ORIGIN_REQUIRED", "Request origin not allowed.")
            return False
        if origins[0].rstrip("/") not in self._origins:
            await _refuse(send, 403, "ORIGIN_NOT_ALLOWED", "Request origin not allowed.")
            return False
        return True

    def _audit_refusal(self) -> None:
        # The caller is not known here (the backend has not been asked, and this layer never
        # reads the body), so the row records the refusal and not a person.
        store = getattr(self._selector, "store", None)
        if store is None:
            return
        try:
            store.record(
                actor="hosted-guard",
                role=None,
                action="HOSTED_ACTION_REFUSED",
                outcome="refused",
                code="HOSTED_REMOTE_DISABLED",
            )
        except Exception:  # noqa: BLE001 - the refusal stands even if its audit row fails
            return

    async def _health(self, scope: Scope, receive: Receive, send: Send) -> None:
        # ai_assistant reports the baseline as a configured model. In this deployment that
        # baseline is the no-model marker, so the reply must not say a model is on.
        status: dict[str, int] = {}
        chunks: list[bytes] = []

        async def capture(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await self._app(scope, receive, capture)
        body = json.loads(b"".join(chunks))
        if body.get("model") == NO_MODEL_NAME:
            body.update(llm_enabled=False, model=None)
        body["external_ai"] = self._external_ai()
        await _json(send, status.get("code", 200), body)

    def _external_ai(self) -> dict[str, Any]:
        # D-138 A1: what the notice needs to name the provider: the registered hosted modes,
        # the active model's provider class (only if it is one of them) and each mode's
        # surfaces, all from code constants and the selector, never from the request.
        surfaces: dict[str, list[str]] = {}
        if self._claude:
            paths = (
                assistant_config.HOSTED_CHAT_PATHS
                if assistant_config.HOSTED_CHAT_DECISION is not None
                else frozenset()
            )
            names = ["case"] + [
                CHAT_PATH_SURFACES[p] for p in sorted(paths) if p in CHAT_PATH_SURFACES
            ]
            if (
                assistant_config.HOSTED_INSIGHTS_DECISION is not None
                and "anthropic" in assistant_config.HOSTED_INSIGHTS_PROVIDERS
            ):
                names.append("insights")
            surfaces["anthropic"] = names
        if self._openrouter:
            surfaces["openrouter"] = ["case"]  # D-134 M4: the case chat only
        try:
            active = data_access.model_class(self._selector.current().model, None)
        except Exception:  # noqa: BLE001 - unknown is reported as no active provider
            active = None
        return {
            "providers": list(surfaces),
            "active": active if active in surfaces else None,
            "surfaces": surfaces,
        }

    async def _brief(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only a 200 JSON object gains the field; anything else is replayed byte for byte.
        messages: list[Message] = []

        async def capture(message: Message) -> None:
            messages.append(message)

        await self._app(scope, receive, capture)
        start = next((m for m in messages if m["type"] == "http.response.start"), None)
        body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
        parsed: Any = None
        if start is not None and start["status"] == 200:
            try:
                parsed = json.loads(body)
            except ValueError:
                parsed = None
        if not isinstance(parsed, dict) or start is None:
            for message in messages:
                await send(message)
            return
        parsed["external_ai"] = self._external_ai()
        payload = json.dumps(parsed, separators=(",", ":")).encode("ascii")
        headers = [(k, v) for k, v in start.get("headers", []) if k.lower() != b"content-length"]
        headers.append((b"content-length", str(len(payload)).encode("ascii")))
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": payload})
