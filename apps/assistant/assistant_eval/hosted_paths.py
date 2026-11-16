"""D-130: the hosted chat paths' paid qualification turns (H-G1, H-S1, H-T1; OD-G6).

Each turn is one call to the model under qualification, through the real route as the browser
sends it: the general chat (an RM's general context), Support's chat, and "Try with this
change" (Support, on an ended conversation of the synthetic Garden case). The CLM backend is a
fake serving the synthetic case, a synthetic RM, a synthetic Support user and a synthetic
policy catalogue (tests/fixtures/eval/hosted_paths.json). The ended conversation "Try" needs is
made first on a separate app whose stand-in model never answers, so it costs no call.

A turn passes when the route answered 200 with the model's own answer, not cut short. Only
content-free results are kept (no question or answer text).
"""

import hashlib
import json
import tempfile
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import ChatModel, LlmUnavailableError, ModelAnswer, Piece
from ai_assistant.main import CUT_SHORT_NOTICE, create_app
from ai_assistant.model_qualification import EVAL_FIXTURES
from ai_assistant.support_chat import CUT_SHORT as SUPPORT_CUT_SHORT

from .runner import EVAL_NOW, ORIGIN, SESSION, Workspace, _digests
from .variants import CaseInputs, case_inputs, verified_fixture_documents

FIXTURE = EVAL_FIXTURES / "hosted_paths.json"
SUPPORT_SESSION = "eval-support-session"
BASE = "garden_address_conflict"
KNOWLEDGE = "guidance+seed"


@dataclass(frozen=True)
class PathTurn:
    key: str
    path: str
    status: int
    answered_by: str
    cut_short: bool

    @property
    def passed(self) -> bool:
        return self.status == 200 and self.answered_by == "model" and not self.cut_short

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "path": self.path,
            "status": self.status,
            "answered_by": self.answered_by,
            "cut_short": self.cut_short,
            "passed": self.passed,
        }


def load_fixture() -> dict[str, Any]:
    return dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


class _NoModel:
    """A local stand-in that never answers: the setup chat gets the case-data answer."""

    name = "setup-no-model"

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        raise LlmUnavailableError("setup only")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        raise LlmUnavailableError("setup only")
        yield Piece()  # pragma: no cover - makes this an async generator

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


def _backend(case: CaseInputs, fixture: dict[str, Any]) -> httpx.MockTransport:
    actors = {SESSION: case.actor, SUPPORT_SESSION: fixture["support_actor"]}

    def handler(request: httpx.Request) -> httpx.Response:
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        if request.method != "GET" or token not in actors:
            return httpx.Response(401, json={"detail": "auth"})
        path = request.url.path
        if path == "/api/auth/me":
            return httpx.Response(200, json=actors[token])
        if path == "/api/policies":
            return httpx.Response(200, json=fixture["policies"])
        if path == f"/api/clm/zero-touch/cases/{case.case_id}":
            return httpx.Response(200, json=case.summary)
        if path == f"/api/onboarding/cases/{case.case_id}/documents":
            return httpx.Response(200, json=case.documents)
        if path == f"/api/onboarding/cases/{case.case_id}/document-digests":
            return httpx.Response(200, json=_digests(case.documents))
        if path == "/api/clm/zero-touch/cases":
            return httpx.Response(200, json=[_list_item(case)])
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


def _list_item(case: CaseInputs) -> dict[str, Any]:
    # The portfolio list item the backend would show for the fixture case (only the fields the
    # fifth path reads).
    summary = case.summary
    exceptions = [
        item.get("exception_type")
        for item in summary.get("active_exceptions") or []
        if isinstance(item, dict) and item.get("exception_type")
    ]
    return {
        "case_id": case.case_id,
        "status": summary.get("status"),
        "current_stage": summary.get("current_stage"),
        "created_at": summary.get("created_at"),
        "completed_at": None,
        "human_interventions": len(summary.get("interventions") or []),
        "active_exception_types": exceptions,
    }


class _FixtureGate:
    """The hosted service's case policy object (D-139), here for the one synthetic fixture case."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        self.refs = frozenset({hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:12]})

    def __call__(self, case_id: object, summary: object) -> str | None:
        return None if str(case_id) == self.case_id else "NOT_THE_FIXTURE_CASE"


def _events(reply: Any) -> dict[str, Any]:
    # The stream route's final event (the test client's own response type).
    events = [json.loads(line) for line in reply.text.splitlines() if line.strip()]
    return next(event for event in events if event.get("type") == "done")


def _cut(notice: Any) -> bool:
    text = str(notice or "")
    return CUT_SHORT_NOTICE in text or SUPPORT_CUT_SHORT in text


def run_paths(
    model: ChatModel,
    keys: tuple[str, ...],
    *,
    workspace: Workspace,
    harness_settings: AiAssistantSettings,
    verified_documents: bool,
    begin: Callable[[str], None],
) -> list[PathTurn]:
    """Ask each listed hosted-path turn once (``begin``: called before each, for the stop
    check and the turn count)."""

    fixture = load_fixture()
    unknown = set(keys) - set(fixture["turns"])
    if unknown:
        raise ValueError("unknown hosted turn keys: " + ", ".join(sorted(unknown)))
    case = case_inputs(BASE)
    if verified_documents:
        case = verified_fixture_documents(case)
    kb = workspace.knowledge(KNOWLEDGE)
    transport = _backend(case, fixture)
    # The fifth path's daily-limit store lives with this run, never in the service's own.
    stores = Path(tempfile.mkdtemp(prefix="hosted-paths-"))
    settings = harness_settings.model_copy(
        update={"model_admin_db_path": str(stores / "models" / "model_admin.sqlite3")}
    )

    def app_for(chat_model: object) -> TestClient:
        app = create_app(
            settings,
            clm_transport=transport,
            chat_model=chat_model,  # type: ignore[arg-type]
            knowledge=kb,
            retrieval_clock=lambda: EVAL_NOW,
        )
        app.state.case_gate = _FixtureGate(case.case_id)
        # As on the hosted service: PR #178's own insights route is refused there.
        app.state.dashboard_insights_disabled = True
        return TestClient(app, headers={"Origin": ORIGIN})

    results: list[PathTurn] = []
    with app_for(model) as client:
        for key in keys:
            turn = fixture["turns"][key]
            path = turn["path"]
            if path == "try_change":
                conversation = _ended_conversation(app_for(_NoModel()), case, turn)
            begin(key)
            if path == "general":
                client.cookies.set("clm_session", SESSION)
                opened = client.post("/assistant/contexts", json={})
                opened.raise_for_status()
                reply = client.post(
                    "/assistant/general/chat/stream",
                    json={"message": turn["question"], "context_id": opened.json()["context_id"]},
                )
                done = _events(reply) if reply.status_code == 200 else {}
            elif path == "support":
                client.cookies.set("clm_session", SUPPORT_SESSION)
                reply = client.post("/assistant/support/chat", json={"message": turn["question"]})
                done = reply.json() if reply.status_code == 200 else {}
            elif path == "dashboard_insights":
                client.cookies.set("clm_session", SESSION)
                reply = client.post("/assistant/dashboard/insights/generate")
                written = reply.json().get("insights") if reply.status_code == 200 else None
                done = {"answered_by": "model" if written and written.get("notes") else ""}
            elif path == "try_change":
                client.cookies.set("clm_session", SUPPORT_SESSION)
                reply = client.post(
                    f"/assistant/knowledge/conversations/{conversation}/try",
                    json=turn["change"],
                )
                done = reply.json() if reply.status_code == 200 else {}
            else:
                raise ValueError(f"unknown hosted path: {path}")
            results.append(
                PathTurn(
                    key=key,
                    path=path,
                    status=reply.status_code,
                    answered_by=str(done.get("answered_by") or ""),
                    cut_short=_cut(done.get("notice")),
                )
            )
    return results


def _ended_conversation(setup: TestClient, case: CaseInputs, turn: dict[str, Any]) -> str:
    # The RM's rated conversation the change is tried on, made without any model call.
    with setup:
        setup.cookies.set("clm_session", SESSION)
        asked = setup.post(
            f"/assistant/cases/{case.case_id}/chat", json={"message": turn["setup_question"]}
        )
        asked.raise_for_status()
        conversation = asked.json().get("conversation_id")
        if not conversation:
            raise RuntimeError("the setup conversation was not recorded")
        ended = setup.post(
            f"/assistant/conversations/{conversation}/end",
            json={"resolved": False, "satisfaction": "unsatisfied", "comment": "Needs more."},
        )
        ended.raise_for_status()
    return str(conversation)
