"""AI Assistant behaviour against a fake CLM backend and a fake model (no network)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import LlmUnavailableError, ModelAnswer, OpenAICompatibleChatModel, Piece
from ai_assistant.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"
SUMMARY = json.loads((FIXTURES / "garden_address_conflict_summary.json").read_text())
DOCUMENTS = json.loads((FIXTURES / "garden_documents.json").read_text())
ME = json.loads((FIXTURES / "me_client_onboarder.json").read_text())
CASE_ID = SUMMARY["case"]["case_id"]
ORIGIN = "http://127.0.0.1:5173"


def _session(request: httpx.Request) -> str | None:
    for part in request.headers.get("cookie", "").split(";"):
        name, _, value = part.strip().partition("=")
        if name == "clm_session":
            return value
    return None


class FakeBackend:
    """Serves the recorded CLM responses and records every request made to it."""

    def __init__(
        self, *, case_status: int = 200, cases: list[dict[str, Any]] | None = None
    ) -> None:
        self.requests: list[httpx.Request] = []
        self.case_status = case_status

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if _session(request) != "valid-session":
            return httpx.Response(401, json={"detail": "auth"})
        path = request.url.path
        if path == "/api/auth/me":
            return httpx.Response(200, json=ME)
        if path == f"/api/clm/zero-touch/cases/{CASE_ID}":
            return httpx.Response(self.case_status, json=SUMMARY)
        if path == f"/api/onboarding/cases/{CASE_ID}/documents":
            return httpx.Response(200, json=DOCUMENTS)
        return httpx.Response(404, json={"detail": "not found"})


class FakeModel:
    name = "fake-model"
    ANSWER = 'The current case offers "Keep registry value".'

    def __init__(
        self, *, fail: bool = False, answer: str | None = None, cut_short: bool = False
    ) -> None:
        self.fail = fail
        self.answer = answer or self.ANSWER
        self.cut_short = cut_short
        self.calls: list[list[dict[str, str]]] = []
        self.warmed: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.calls.append(messages)
        if self.fail:
            raise LlmUnavailableError("down")
        return ModelAnswer(self.answer, cut_short=self.cut_short)

    def stream(self, messages: list[dict[str, str]]) -> Iterator[Piece]:
        self.calls.append(messages)
        if self.fail:
            raise LlmUnavailableError("down")
        for word in self.answer.split(" "):
            yield Piece(word + " ")
        yield Piece(cut_short=self.cut_short)

    def warm(self, messages: list[dict[str, str]]) -> None:
        self.warmed.append(messages)


def _client(
    backend: FakeBackend, model: FakeModel | None, *, cookie: str | None = "valid-session"
) -> TestClient:
    settings = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]
    app = create_app(settings, clm_transport=httpx.MockTransport(backend.handler), chat_model=model)
    client = TestClient(app, headers={"Origin": ORIGIN})
    if cookie:
        client.cookies.set("clm_session", cookie)
    return client


def test_brief_names_the_blocker_the_difference_and_the_allowed_action() -> None:
    backend = FakeBackend()
    response = _client(backend, None).get(f"/assistant/cases/{CASE_ID}/brief")

    assert response.status_code == 200
    body = response.json()
    assert body["blocker_count"] == 1
    assert body["company"] == "GARDEN BUSINESS"
    assert body["message"].startswith("I found 1 issue stopping the onboarding of GARDEN BUSINESS")
    assert "18 OFFICIAL MOCK STREET" in body["message"]
    assert "18 GARDEN WALK" in body["message"]
    assert '"Keep registry value"' in body["message"]
    assert f"{body['steps_done']} of {body['steps_total']}" in body["message"]
    assert "Explain the registered address difference" in body["suggested_questions"]


def test_ai_assistant_only_reads_and_forwards_the_users_own_session() -> None:
    backend = FakeBackend()
    client = _client(backend, FakeModel())
    client.get(f"/assistant/cases/{CASE_ID}/brief")
    client.post(f"/assistant/cases/{CASE_ID}/chat", json={"message": "Why am I stuck?"})

    assert backend.requests
    assert {request.method for request in backend.requests} == {"GET"}
    assert all(_session(r) == "valid-session" for r in backend.requests)


def test_chat_uses_the_model_with_rules_and_current_case_facts() -> None:
    model = FakeModel()
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    response = _client(FakeBackend(), model).post(
        f"/assistant/cases/{CASE_ID}/chat",
        json={"message": "Why is this case blocked?", "history": history},
    )

    assert response.status_code == 200
    assert response.json()["answered_by"] == "model"
    messages = model.calls[0]
    assert messages[0]["role"] == "system" and "Use ONLY the CASE FACTS" in messages[0]["content"]
    facts = json.loads(messages[1]["content"].split("\n", 1)[1])
    assert facts["company"]["uen"] == "11111999A"
    assert facts["blockers"][0]["actions_available_to_this_user"][0]["label"] == (
        "Keep registry value"
    )
    assert "csrf" not in messages[1]["content"].lower()
    assert messages[2:] == [*history, {"role": "user", "content": "Why is this case blocked?"}]


def test_chat_falls_back_to_case_data_when_the_model_is_down() -> None:
    response = _client(FakeBackend(), FakeModel(fail=True)).post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": "What did ACRA return?"}
    )

    body = response.json()
    assert body["answered_by"] == "case_data"
    assert body["notice"]
    assert "From ACRA (MOCK)" in body["answer"]
    assert "18 OFFICIAL MOCK STREET" in body["answer"]


def test_no_model_configured_still_answers_from_case_data() -> None:
    response = _client(FakeBackend(), None).post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": "Where are we now?"}
    )

    body = response.json()
    assert body["answered_by"] == "case_data"
    assert "onboarding steps are done" in body["answer"]


@pytest.mark.parametrize(
    ("cookie", "case_status", "expected"),
    [(None, 200, 401), ("expired", 200, 401), ("valid-session", 404, 404)],
)
def test_access_is_decided_by_the_clm_backend(
    cookie: str | None, case_status: int, expected: int
) -> None:
    model = FakeModel()
    response = _client(FakeBackend(case_status=case_status), model, cookie=cookie).post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": "Who are the directors?"}
    )

    assert response.status_code == expected
    assert model.calls == []


def test_requests_from_other_websites_are_refused() -> None:
    backend = FakeBackend()
    client = _client(backend, FakeModel())
    response = client.get(
        f"/assistant/cases/{CASE_ID}/brief", headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert backend.requests == []


def test_openai_compatible_client_sends_a_standard_chat_request() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": " Hello "}}]})

    model = OpenAICompatibleChatModel(
        base_url="http://127.0.0.1:11434/v1/",
        model="ministral-3:8b",
        credential="test_ollama_key",
        timeout_seconds=5,
        temperature=0.2,
        max_answer_tokens=300,
        transport=httpx.MockTransport(handler),
    )

    assert model.complete([{"role": "user", "content": "hi"}]) == ModelAnswer("Hello")
    assert seen["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert seen["body"]["model"] == "ministral-3:8b"
    assert seen["body"]["stream"] is False
    assert seen["body"]["max_tokens"] == 300


@pytest.mark.parametrize(
    "reply",
    [httpx.Response(500), httpx.Response(200, json={"choices": []}), httpx.Response(200, text="x")],
)
def test_openai_compatible_client_reports_bad_replies_as_unavailable(
    reply: httpx.Response,
) -> None:
    model = OpenAICompatibleChatModel(
        base_url="http://model.invalid/v1",
        model="m",
        credential="test_key",
        timeout_seconds=5,
        temperature=0,
        transport=httpx.MockTransport(lambda request: reply),
    )

    with pytest.raises(LlmUnavailableError):
        model.complete([{"role": "user", "content": "hi"}])


def test_waiting_case_lists_what_is_still_needed_and_where() -> None:
    from ai_assistant.briefing import fallback_answer, opening_message
    from ai_assistant.clm_client import CaseSnapshot
    from ai_assistant.context import build_case_facts
    from ai_assistant.prompts import build_messages

    waiting = json.loads((FIXTURES / "garden_waiting_for_documents_summary.json").read_text())
    facts = build_case_facts(CaseSnapshot(waiting, [], ME))

    brief = opening_message(facts)
    assert "waiting for inputs" in brief
    assert "No supporting company document has been uploaded yet" in brief
    assert "(section: Document verification)" in brief
    assert "(section: Ownership & UBO)" in brief
    answer = fallback_answer("What more do I have to do to get a successful submission?", facts)
    assert "Before the case can go to GoldTier" in answer
    system = build_messages(facts, [], "hi")[0]["content"]
    assert "Never mention the field names" in system
    assert "Never guess who to contact" in system
