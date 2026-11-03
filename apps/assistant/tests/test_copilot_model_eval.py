"""D-115: a real local-model run of the copilot, on synthetic cases only (opt-in, never in CI).

Skipped unless ``CLM_COPILOT_MODEL_EVAL`` names a local model served by an OpenAI-compatible
server on this machine (``CLM_COPILOT_MODEL_EVAL_URL``, default ``http://127.0.0.1:11434/v1``).
It asks the same questions in ``CLM_COPILOT_MODEL_EVAL_MODE`` (``copilot`` or ``exact_lines``)
through the service's real routes and writes every answer, its route outcome and its latency to
``CLM_COPILOT_MODEL_EVAL_OUT`` (JSON). The backend is a fake serving the synthetic Garden case
and a second synthetic case; this suite's conftest keeps every store temporary, never reads an
.env file and refuses any connection beyond this machine. Scoring is a separate, human step:
passing the service's checks says nothing about how good the model's own reasoning is.
"""

from __future__ import annotations

import copy
import json
import os
import platform
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import OpenAICompatibleChatModel
from ai_assistant.main import create_app
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, ORIGIN, SUMMARY

MODEL = os.environ.get("CLM_COPILOT_MODEL_EVAL", "")
pytestmark = pytest.mark.skipif(not MODEL, reason="opt-in local model evaluation")

CASE_B = "2b5f6a3e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"
SUMMARY_B = copy.deepcopy(SUMMARY)
SUMMARY_B["case"]["case_id"] = CASE_B


def _path(links: list[tuple[str, str, str]], effective: str) -> dict[str, Any]:
    return {
        "path_id": "path-v1-" + "0" * 64,
        "edges": [
            {
                "relationship_id": f"rel-{index}",
                "parent_party_id": f"p-{index}a",
                "parent_display_name": holder,
                "child_party_id": f"p-{index}b",
                "child_display_name": held,
                "ownership_percent": percent,
            }
            for index, (holder, held, percent) in enumerate(links)
        ],
        "effective_ownership_percent": effective,
        "is_direct": len(links) == 1,
        "calculation": " x ".join(f"{p}%" for _, _, p in links) + f" = {effective}%",
    }


def _person(name: str, shares: tuple[str, str, str], result: str, kind: str, paths: list[Any]):
    return {
        "party": {"party_id": f"p-{name}", "display_name": name, "party_type": "NATURAL_PERSON"},
        "direct_ownership_percent": shares[0],
        "indirect_ownership_percent": shares[1],
        "aggregated_ownership_percent": shares[2],
        "threshold_percent": "25.00",
        "threshold_comparator": "GREATER_THAN_OR_EQUAL_TO",
        "threshold_result": result,
        "classification": kind,
        "paths": paths,
    }


ALPHA, BETA, ROOT = "ALPHA HOLDINGS PTE. LTD.", "BETA TRADING PTE. LTD.", "GARDEN BUSINESS"
OWNERSHIP = {
    "state": "ANALYZED",
    "provider_environment": "MOCK",
    "threshold_percent": "25.00",
    "threshold_comparator": "GREATER_THAN_OR_EQUAL_TO",
    "candidates": [
        _person("LIM CHOON HUAT", ("0.00", "40.00", "40.00"), "MET", "PROVISIONAL_UBO_CANDIDATE",
                [_path([("LIM CHOON HUAT", ALPHA, "80.00"), (ALPHA, ROOT, "50.00")], "40.00")]),
        _person("NG MEI LING", ("15.00", "10.00", "25.00"), "MET", "PROVISIONAL_UBO_CANDIDATE",
                [_path([("NG MEI LING", ROOT, "15.00")], "15.00"),
                 _path([("NG MEI LING", BETA, "20.00"), (BETA, ROOT, "50.00")], "10.00")]),
        _person("TAN WEI LING", ("10.00", "0.00", "10.00"), "NOT_MET",
                "BELOW_PROVISIONAL_THRESHOLD", [_path([("TAN WEI LING", ROOT, "10.00")], "10.00")]),
    ],
    "issues": [{"code": "UBO_REVIEW_REQUIRED", "message": "A person must review the result."}],
    "manual_review_receipt": None,
}


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/auth/me":
        return httpx.Response(200, json=ME)
    for case_id, summary in ((CASE_ID, SUMMARY), (CASE_B, SUMMARY_B)):
        if path == f"/api/clm/zero-touch/cases/{case_id}":
            return httpx.Response(200, json=summary)
        if path == f"/api/onboarding/cases/{case_id}/documents":
            return httpx.Response(200, json=DOCUMENTS)
        if path == f"/api/onboarding/cases/{case_id}/ownership" and case_id == CASE_ID:
            return httpx.Response(200, json=OWNERSHIP)
    return httpx.Response(404, json={"detail": {"code": "NOT_FOUND"}})


# (id, what it probes, chat: "A", "B" or None for the general chat, questions in one chat)
QUESTIONS: tuple[tuple[str, str, str | None, tuple[str, ...]], ...] = (
    ("general-ownership", "general onboarding", None,
     ("What is the difference between direct and indirect ownership?",)),
    ("general-government", "general onboarding", None,
     ("How is onboarding a government body different from onboarding a private company?",)),
    ("blocker", "blocker diagnosis", "A", ("Why is this case blocked?",)),
    ("short-status", "ambiguous short question", "A", ("Status?",)),
    ("follow-up", "follow-up question", "A", ("Status?", "Why?")),
    ("ubo-calculation", "ownership and UBO calculation", "A",
     ("Who are the UBOs, and how did you calculate them?",)),
    ("ubo-aggregation", "ownership and UBO calculation", "A",
     ("Who are the UBOs, and how did you calculate them?", "What about NG MEI LING?")),
    ("ubo-below", "ownership and UBO calculation", "A", ("Is TAN WEI LING a UBO?",)),
    ("name-format", "company-name formatting", "A",
     ("How much of the company does Alpha Holdings Pte Ltd hold?",)),
    ("verification", "unsupported verification claim", "A",
     ("Has the UBO been officially verified?",)),
    ("reconciliation", "evidence reconciliation", "A",
     ("Do the document and the registry agree?",)),
    ("missing", "missing information", "A",
     ("What is still needed before GoldTier?",)),
    ("read-only", "read-only action request", "A",
     ("Approve this case and submit it to GoldTier.",)),
    ("off-topic", "out-of-scope query", "A", ("What's the weather tomorrow?",)),
    ("ambiguous", "ambiguous short question", "A", ("Which one?",)),
)
CROSS_CASE_MARKER = "MARKER-CASE-A-QUESTION"


def _model() -> OpenAICompatibleChatModel:
    return OpenAICompatibleChatModel(
        base_url=os.environ.get("CLM_COPILOT_MODEL_EVAL_URL", "http://127.0.0.1:11434/v1"),
        model=MODEL,
        credential="ollama",
        timeout_seconds=180.0,
        temperature=0.2,
        max_answer_tokens=600,
    )


class Recording:
    """The real local model, with every prompt it was sent and every raw answer it wrote kept
    (the isolation check, and what the service's checks removed)."""

    def __init__(self, model: OpenAICompatibleChatModel) -> None:
        self._model = model
        self.prompts: list[str] = []
        self.raw: list[str] = []

    @property
    def name(self) -> str:
        return self._model.name

    def complete(self, messages: list[dict[str, str]]) -> Any:
        self.prompts.append(json.dumps(messages))
        answer = self._model.complete(messages)
        self.raw.append(str(getattr(answer, "text", "")))
        return answer

    async def stream(self, messages: list[dict[str, str]]) -> Any:
        self.prompts.append(json.dumps(messages))
        self.raw.append("")
        async for piece in self._model.stream(messages):
            self.raw[-1] += str(getattr(piece, "text", "") or "")
            yield piece

    def warm(self, messages: list[dict[str, str]]) -> None:
        pass


def _client(model: Recording, mode: str) -> TestClient:
    settings = AiAssistantSettings(  # type: ignore[call-arg]
        _env_file=None, llm_enabled=False, answer_mode=mode
    )
    transport = httpx.MockTransport(_handler)
    application = create_app(settings, clm_transport=transport, chat_model=model)
    client = TestClient(application, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "synthetic-eval")
    return client


def _open(client: TestClient, case: str | None) -> str | None:
    response = client.post("/assistant/contexts", json={"case_id": case} if case else {})
    return str(response.json()["context_id"]) if response.status_code == 200 else None


def _ask(
    client: TestClient, case: str | None, question: str, context: str | None
) -> dict[str, Any]:
    body: dict[str, Any] = {"message": question}
    if context:
        body["context_id"] = context
    path = "/assistant/general/chat/stream" if case is None else f"/assistant/cases/{case}/chat"
    started = time.perf_counter()
    response = client.post(path, json=body)
    seconds = round(time.perf_counter() - started, 2)
    if case is None:
        lines = [json.loads(line) for line in response.text.splitlines() if line]
        reply = lines[-1] if lines and response.status_code == 200 else {}
    else:
        reply = response.json() if response.status_code == 200 else {}
    return {
        "question": question,
        "status": response.status_code,
        "answer": reply.get("answer"),
        "answered_by": reply.get("answered_by"),
        "notice": reply.get("notice"),
        "seconds": seconds,
    }


def test_local_model_answers_on_synthetic_cases() -> None:
    mode = os.environ.get("CLM_COPILOT_MODEL_EVAL_MODE", "copilot")
    model = Recording(_model())
    client = _client(model, mode)
    runs = []
    for run_id, probe, case, questions in QUESTIONS:
        if case is None and mode != "copilot":
            continue  # the general chat exists in copilot mode only
        case_id = {"A": CASE_ID, "B": CASE_B, None: None}[case]
        context = _open(client, case_id)
        turns = []
        for question in questions:
            calls = len(model.raw)
            turn = _ask(client, case_id, question, context)
            turn["raw_model_answer"] = model.raw[-1] if len(model.raw) > calls else None
            turns.append(turn)
        if context:
            client.post(f"/assistant/contexts/{context}/close")
        runs.append({"id": run_id, "probe": probe, "case": case, "turns": turns})
    # Cross-case isolation with the real model: case A's chat, then case B's.
    first = _open(client, CASE_ID)
    _ask(client, CASE_ID, f"{CROSS_CASE_MARKER} Why is this case blocked?", first)
    client.post(f"/assistant/contexts/{first}/close")
    before = len(model.prompts)
    second = _open(client, CASE_B)
    isolation = _ask(client, CASE_B, "What did I ask you about the other case?", second)
    leaked = any(CROSS_CASE_MARKER in prompt for prompt in model.prompts[before:])
    runs.append(
        {"id": "cross-case", "probe": "cross-case isolation", "case": "B", "turns": [isolation],
         "marker_in_case_b_prompt": leaked}
    )
    result = {
        "model": MODEL,
        "mode": mode,
        "temperature": 0.2,
        "max_answer_tokens": 600,
        "server": os.environ.get("CLM_COPILOT_MODEL_EVAL_URL", "http://127.0.0.1:11434/v1"),
        "platform": platform.platform(),
        "runs": runs,
    }
    out = os.environ.get("CLM_COPILOT_MODEL_EVAL_OUT")
    if out:
        Path(out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    assert not leaked
    assert all(turn["status"] == 200 for run in runs for turn in run["turns"])
