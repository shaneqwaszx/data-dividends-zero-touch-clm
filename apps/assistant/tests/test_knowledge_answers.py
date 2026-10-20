"""Milestone 3: retrieved knowledge in answers (prompt, citations, sources, fallback)."""

import json
import re
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.ingest import ingest_guidance, ingest_synthetic_resolutions
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.main import create_app
from tests.test_ai_assistant import CASE_ID, ORIGIN, FakeBackend, FakeModel
from tests.test_knowledge_store import _kb

CHAT = f"/assistant/cases/{CASE_ID}/chat"
STREAM = f"/assistant/cases/{CASE_ID}/chat/stream"


@pytest.fixture
def kb(tmp_path: Path) -> KnowledgeBase:
    knowledge = _kb(tmp_path)
    ingest_guidance(knowledge)
    ingest_synthetic_resolutions(knowledge)
    return knowledge


def _client(model: FakeModel | None, kb: KnowledgeBase | None) -> TestClient:
    settings = AiAssistantSettings(_env_file=None, llm_enabled=False)  # type: ignore[call-arg]
    app = create_app(
        settings,
        clm_transport=httpx.MockTransport(FakeBackend().handler),
        chat_model=model,
        knowledge=kb,
    )
    client = TestClient(app, headers={"Origin": ORIGIN})
    client.cookies.set("clm_session", "valid-session")
    return client


def test_retrieved_guidance_and_past_cases_reach_the_prompt_after_the_history(
    kb: KnowledgeBase,
) -> None:
    model = FakeModel()
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello"}]
    _client(model, kb).post(
        CHAT, json={"message": "Can I use the document address instead?", "history": history}
    )
    messages = model.calls[0]
    knowledge = next(m["content"] for m in messages if m["content"].startswith("KNOWLEDGE"))
    # Tag numbers follow the ranking; the address rule must be among the guidance sent.
    assert re.search(r"\[G\d\] Registered address in a document differs from ACRA", knowledge)
    assert "[P1]" in knowledge and "ILLUSTRATIVE" in knowledge
    assert messages.index(next(m for m in messages if m["content"] == "Hello")) < messages.index(
        next(m for m in messages if m["content"].startswith("KNOWLEDGE"))
    )
    assert messages[-1]["content"] == "Can I use the document address instead?"


def test_the_reply_lists_sources_and_marks_which_were_cited(kb: KnowledgeBase) -> None:
    model = FakeModel(answer="Only Keep registry value is offered for the address [G1].")
    body = _client(model, kb).post(CHAT, json={"message": "Can I use the document address?"}).json()
    assert body["answer"].endswith("[G1].")
    first = body["sources"][0]
    assert first["tag"] == "G1" and first["entry_id"] == "guidance.address-mismatch"
    assert first["cited"] is True and first["source_ref"].startswith("docs/decisions")
    assert body["knowledge"] == {"confidence": "high", "degraded": False}


def test_a_sentence_citing_an_entry_that_was_not_retrieved_is_left_out(kb: KnowledgeBase) -> None:
    model = FakeModel(answer="Keep the registry value [G1]. A past case allowed more [P9].")
    body = _client(model, kb).post(CHAT, json={"message": "Can I use the document address?"}).json()
    assert body["answer"] == "Keep the registry value [G1]."
    assert body["checks"]["removed"] == ["invented_source"]


def test_a_past_case_cannot_add_an_action_the_case_does_not_offer(kb: KnowledgeBase) -> None:
    model = FakeModel(answer="In a past case they used the document value instead [P1].")
    body = _client(model, kb).post(CHAT, json={"message": "What did others do?"}).json()
    assert "action_not_allowed" in (body["checks"] or {}).get("removed", []) or (
        body["answered_by"] == "case_data"
    )


def test_values_quoted_from_guidance_are_accepted(kb: KnowledgeBase) -> None:
    model = FakeModel(answer="The policy default for continuing is 0.85 [G1].")
    body = _client(model, kb).post(CHAT, json={"message": "What does evidence score mean?"}).json()
    assert "0.85" in body["answer"] and body["checks"]["removed"] == []


def test_follow_up_questions_from_past_cases_become_suggestions(kb: KnowledgeBase) -> None:
    body = _client(FakeModel(), kb).post(CHAT, json={"message": "Client moved office?"}).json()
    assert "What do I need for the ownership step next?" in body["suggested_questions"]


def test_without_the_model_the_answer_adds_the_matching_guidance(kb: KnowledgeBase) -> None:
    body = _client(None, kb).post(CHAT, json={"message": "Can I use the document address?"}).json()
    assert body["answered_by"] == "case_data"
    assert (
        "From the guidance [G1] Registered address in a document differs from ACRA"
        in (body["answer"])
    )


def test_streaming_carries_sources_in_the_final_event(kb: KnowledgeBase) -> None:
    model = FakeModel(answer="Keep the registry value [G1].")
    response = _client(model, kb).post(STREAM, json={"message": "Can I use the document address?"})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[-1]["type"] == "done" and events[-1]["sources"][0]["cited"] is True


def test_without_a_knowledge_base_answers_work_as_before() -> None:
    body = _client(FakeModel(), None).post(CHAT, json={"message": "What next?"}).json()
    assert body["answered_by"] == "model" and body["sources"] == [] and body["knowledge"] is None
