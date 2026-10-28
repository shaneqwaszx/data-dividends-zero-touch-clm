"""D-094 local synthetic test mode: GPT-OSS 120B via OpenRouter in the CLM chat, offline.

A mock OpenRouter (chat, key and generation metadata), a fake public listing, a synthetic
ledger and the fake CLM backend serving the synthetic Garden fixture. Nothing reaches a
network or spends; the suite guard (conftest.py) refuses any non-local connection."""

import copy
import dataclasses
import json
import threading
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import model_admin, remote_test
from ai_assistant.budget import BudgetLedger
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.config import AiAssistantSettings
from ai_assistant.context import build_case_facts
from ai_assistant.knowledge.ingest import GUIDANCE_DIR, parse_guidance
from ai_assistant.llm import ModelCallError
from ai_assistant.main import REMOTE_BOUNDARY_NOTICE, REMOTE_NOTICE, create_app
from ai_assistant.model_admin import ModelSelector
from ai_assistant.model_catalog import load_catalogue
from ai_assistant.model_profiles import OPENROUTER_MODEL_ID, OPENROUTER_PROFILE_ID
from ai_assistant.prompts import build_messages
from ai_assistant.synthetic_boundary import BOUNDARY_FILE, check
from assistant_eval.qualification import run_job
from tests.remote_fixtures import completion, happy_stream
from tests.test_model_management import (
    API,
    CASE_ID,
    DOCUMENTS,
    ME,
    ORIGIN,
    SUMMARY,
    USERS,
    Backend,
    Baseline,
    ModelServer,
    ThreadRun,
    profile,
    wait_for,
    write_profiles,
)

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
SENTINEL = "test_sentinel_openrouter_key_5d2e8a41"
ALLOWED = 'The current case offers "Keep registry value".'
D094 = {
    "local_api_test_decision": "D-094",
    "remote_inference_decision": "D-091",
    "remote_live_decision": "D-092",
    "openrouter_endpoint": "deepinfra/bf16",
    "llm_reasoning_effort": "medium",
    "llm_reasoning_allowance_tokens": 1400,
    "local_api_test_owner_attests": "auto_topup_off,prompt_logging_off",
    "local_api_test_qualification_questions": "P01#1,P02#0",
    "local_api_test_qualification_count": 2,
}


def config(tmp_path: Path, profiles_file: Path | None = None, **extra: Any) -> AiAssistantSettings:
    values: dict[str, Any] = {
        "clm_backend_url": "http://127.0.0.1:8000",
        "llm_enabled": True,
        "llm_base_url": "http://127.0.0.1:11435/v1",
        "llm_model": "ministral-3:8b",
        "knowledge_enabled": False,
        "llm_warm_up": False,
        "model_profiles_file": str(profiles_file or ""),
        "model_admin_db_path": str(tmp_path / "state" / "admin.sqlite3"),
        "budget_ledger_path": str(tmp_path / "budget" / "ledger.sqlite3"),
        **D094,
    }
    values.update(extra)
    return AiAssistantSettings(_env_file=None, **values)


def new_ledger(settings: AiAssistantSettings) -> Path:
    path = Path(settings.budget_ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    BudgetLedger.initialise(
        path, cap_micro_usd=1_000_000, opening_usage_micro_usd=0, key_alias="key-01"
    )
    return path


def listing(path: str) -> Any:
    """The public listing and ZDR list as recorded for the approved endpoint (no network)."""

    if path.endswith("/endpoints/zdr"):
        return {"data": [{"tag": "deepinfra/bf16", "model_id": OPENROUTER_MODEL_ID}]}
    row = {
        "tag": "deepinfra/bf16",
        "model_id": OPENROUTER_MODEL_ID,
        "provider_name": "DeepInfra",
        "quantization": "bf16",
        "max_completion_tokens": 117964,
        "pricing": {"prompt": "0.000000037", "completion": "0.00000017", "discount": 0},
        "supported_parameters": ["reasoning", "max_tokens", "temperature"],
    }
    return {"data": {"endpoints": [row, {"tag": "groq"}]}}


def _reply_lines(body: dict[str, Any]) -> str:
    """Allowed lines from the prompt itself (the topic lines, else the first allowed line)."""

    for message in body["messages"]:
        content = message["content"]
        if message["role"] == "system" and content.startswith("QUESTION TOPIC:"):
            return "\n".join(content.splitlines()[1:]) + "\n"
    for message in body["messages"]:
        content = message["content"]
        if content.startswith("CASE FACTS"):
            facts = json.loads(content.split("\n", 1)[1])
            return str(facts["allowed_guidance"][0]) + "\n"
    return ALLOWED + "\n"


class _EitherChunks(httpx.SyncByteStream, httpx.AsyncByteStream):
    """SSE chunks for the streamed (async) and the plain /chat (sync) adapter paths."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def __iter__(self) -> Iterator[bytes]:
        yield from self._chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


class OpenRouter:
    """A mock OpenRouter: streamed chat completions, /key and /generation."""

    def __init__(self, *, fail: bool = False, provider: str = "DeepInfra") -> None:
        self.fail = fail
        self.provider = provider
        self.chats: list[dict[str, Any]] = []
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/key"):
            data: dict[str, Any] = {
                "limit": 1.0,
                "limit_reset": None,
                "limit_remaining": 1.0,
                "usage": 0,
            }
            return httpx.Response(200, json={"data": data})
        if path.endswith("/generation"):
            data = {
                "id": "gen-1761-test",
                "model": OPENROUTER_MODEL_ID,
                "provider_name": self.provider,
                "total_cost": 0.00072,
                "cancelled": False,
            }
            return httpx.Response(200, json={"data": data})
        body = json.loads(request.content)
        self.chats.append(body)
        if self.fail:
            return httpx.Response(502, json={"error": {"message": "upstream"}})
        if not body["stream"]:  # the plain /chat route
            return httpx.Response(200, json=completion(_reply_lines(body).rstrip("\n")))
        return httpx.Response(
            200,
            stream=_EitherChunks(happy_stream(text=_reply_lines(body))),
            headers={"content-type": "text/event-stream"},
        )

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def _snapshot(summary: dict[str, Any] = SUMMARY, documents: Any = DOCUMENTS) -> CaseSnapshot:
    return CaseSnapshot(summary=summary, documents=documents, actor=ME)


def _boundary(snapshot: CaseSnapshot, question: str, history: Any = ()) -> str | None:
    facts = build_case_facts(snapshot)
    return check(snapshot, facts, build_messages(facts, list(history), question), [])


# --- readiness and the catalogue -----------------------------------------------------------


def test_the_mode_is_off_by_default_and_the_remote_entry_is_unchanged(tmp_path: Path) -> None:
    plain = AiAssistantSettings(_env_file=None)
    assert remote_test.readiness(plain) == "REMOTE_NOT_AUTHORISED"
    entry = load_catalogue(plain).get(OPENROUTER_PROFILE_ID)
    assert entry is not None and entry.status == "pending_authorisation"
    assert entry.reason == "REMOTE_NOT_AUTHORISED" and entry.deployment == "remote"
    with pytest.raises(Exception, match="not ready"):
        remote_test.RemoteTestModel(plain)


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"remote_live_decision": ""}, "DECISION_INTERLOCK"),
        ({"remote_inference_decision": "D-092"}, "DECISION_INTERLOCK"),
        ({"clm_backend_url": "http://clm.example.com:8000"}, "NOT_DEVELOPMENT_ENVIRONMENT"),
        ({"allowed_origins": ["https://clm.example.com"]}, "NOT_DEVELOPMENT_ENVIRONMENT"),
        ({"local_api_test_owner_attests": "auto_topup_off"}, "OWNER_ATTESTATION_MISSING"),
        ({"openrouter_endpoint": "deepinfra"}, "ENDPOINT_NOT_APPROVED"),
        ({"llm_reasoning_effort": ""}, "REMOTE_SETTINGS_INVALID"),
        ({"llm_enabled": False}, "MODEL_DISABLED_BY_ENVIRONMENT"),
    ],
)
def test_every_condition_is_required(tmp_path: Path, changes: dict[str, Any], code: str) -> None:
    settings = config(tmp_path, **changes)
    assert remote_test.readiness(settings) == code
    entry = load_catalogue(settings).get(OPENROUTER_PROFILE_ID)
    assert entry is not None and entry.status == "unavailable" and entry.reason == code


def test_a_ready_mode_lists_a_selectable_remote_entry(tmp_path: Path) -> None:
    settings = config(tmp_path)
    assert remote_test.readiness(settings) is None
    entry = load_catalogue(settings).get(OPENROUTER_PROFILE_ID)
    assert entry is not None and entry.status == "selectable" and entry.source == "code"
    assert entry.deployment == "openrouter" and entry.model_id == OPENROUTER_MODEL_ID
    assert entry.endpoint == "openrouter.ai · deepinfra/bf16"
    assert SENTINEL not in json.dumps(entry.view())


@pytest.mark.parametrize(
    ("questions", "count", "ok"),
    [
        ("P01#1,P02#0", 2, True),
        ("P01#1,P02#0", 3, False),
        ("P01#1,P01#1", 2, False),
        ("", 0, False),
    ],
)
def test_the_paid_qualification_needs_a_counted_manifest(
    tmp_path: Path, questions: str, count: int, ok: bool
) -> None:
    settings = config(
        tmp_path,
        local_api_test_qualification_questions=questions,
        local_api_test_qualification_count=count,
    )
    assert (remote_test.qualification_manifest(settings) is not None) is ok


# --- the synthetic boundary ----------------------------------------------------------------


def test_the_boundary_file_is_current() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/build_synthetic_boundary.py", "--check"],
        cwd=ASSISTANT_DIR,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(ASSISTANT_DIR)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(BOUNDARY_FILE.read_text(encoding="utf-8"))["company"]["uen"] == "11111999A"


def test_the_garden_case_and_a_normal_question_are_inside() -> None:
    assert _boundary(_snapshot(), "What should I do next?") is None
    history = [
        {"role": "user", "content": "Who are the directors of this company?"},
        {"role": "assistant", "content": ALLOWED},
    ]
    assert _boundary(_snapshot(), "What does this case's UEN tell me?", history) is None


def _with_entity(**changes: Any) -> dict[str, Any]:
    summary: dict[str, Any] = copy.deepcopy(SUMMARY)
    summary["case"]["entity"].update(changes)
    return summary


@pytest.mark.parametrize(
    ("snapshot", "code"),
    [
        (
            _snapshot(_with_entity(registration_number="201511222D", legal_name="OPQ PTE. LTD.")),
            "SYNTHETIC_CASE_NOT_APPROVED",
        ),
        (
            _snapshot(_with_entity(legal_name="GARDEN BUSINESS PTE LTD")),
            "SYNTHETIC_CASE_NOT_APPROVED",
        ),
        (
            _snapshot(_with_entity(source={"source_system": "ACRA", "environment": "SANDBOX"})),
            "SYNTHETIC_CASE_NOT_APPROVED",
        ),
        (
            _snapshot(documents=[{**DOCUMENTS[0], "display_name": "client-passport.pdf"}]),
            "SYNTHETIC_DOCUMENT_NOT_APPROVED",
        ),
        (
            _snapshot(
                _with_entity(
                    registered_address={
                        "address_line_1": "1 RAFFLES PLACE",
                        "postal_code": "048616",
                        "country_code": "SG",
                    }
                )
            ),
            "SYNTHETIC_VALUE_NOT_APPROVED",
        ),
    ],
)
def test_anything_outside_the_synthetic_case_is_refused(snapshot: CaseSnapshot, code: str) -> None:
    assert _boundary(snapshot, "What should I do next?") == code


def test_a_viewer_who_is_not_a_seeded_poc_user_is_refused() -> None:
    actor = copy.deepcopy(ME)
    actor["profile"]["display_name"] = "Jane Real-Person"
    snapshot = CaseSnapshot(SUMMARY, DOCUMENTS, actor)
    assert _boundary(snapshot, "What should I do next?") == "SYNTHETIC_VIEWER_NOT_APPROVED"


QG_PROBE = "客户陈伟明 身份证 Ｓ１２３４５６７Ｄ 出生 What should I do next? 1985-03-12"


@pytest.mark.parametrize(
    "question",
    [
        "Is Tan Ah Kow, NRIC S1234567D, a director of this company?",
        "Compare this with SIM LIM SQUARE PTE LTD please",
        "Email the summary to someone@bank.example",
        # QG F-1: other scripts, full-width forms, dates, ids and split numbers.
        QG_PROBE,
        "Ｓ１２３４５６７Ｄ What should I do next?",
        "What should I do next? Клиент Иванов",
        "What should I do next? 1985-03-12",
        "What should I do next? 12 Oct 1985",
        "What should I do next? 4f1c2a9e-8b7d-4c3e-9f21-0a1b2c3d4e5f",
        "What should I do next? S 12 34 56 7",
        "Is Lee a director of this company?",
    ],
)
def test_a_question_with_words_outside_the_vocabulary_is_refused(question: str) -> None:
    assert _boundary(_snapshot(), question) == "SYNTHETIC_TEXT_NOT_APPROVED"


def test_history_is_checked_like_the_question() -> None:
    for history in (
        [{"role": "user", "content": "Our client Tan Ah Kow called about this."}],
        [
            {"role": "user", "content": "What should I do next?"},
            {"role": "assistant", "content": "陈伟明"},
        ],
        [
            {"role": "user", "content": "What should I do next?"},
            {"role": "assistant", "content": "1985-03-12"},
        ],
    ):
        assert _boundary(_snapshot(), "What should I do next?", history) == (
            "SYNTHETIC_TEXT_NOT_APPROVED"
        )


def test_a_live_case_observation_from_the_case_creation_form_is_inside() -> None:
    """Found in the real-stack browser run: a Garden case made in the CLM has an observation
    from the case creation form, whose "from" is only the backend's source label."""

    summary: dict[str, Any] = copy.deepcopy(SUMMARY)
    observation = {
        "normalized_value": "11111999A",
        "source_kind": "USER_INPUT",
        "source_system": "ONBOARDING_REQUEST",
        "environment": None,
        "confidence": None,
    }
    summary["reconciliation"]["discrepancies"][0]["observations"].append(observation)
    assert _boundary(_snapshot(summary), "What should I do next?") is None
    # A value that is not synthetic is still refused, whatever its source kind.
    summary["reconciliation"]["discrepancies"][0]["observations"].append(
        {**observation, "normalized_value": "ACME HOLDINGS PTE LTD"}
    )
    assert _boundary(_snapshot(summary), "What should I do next?") == (
        "SYNTHETIC_VALUE_NOT_APPROVED"
    )


def test_an_unreadable_document_list_or_an_unapproved_name_in_the_summary_is_refused() -> None:
    """QG R4-1: an empty list after a failed read proves nothing about the documents, and the
    case summary can still name a document (reconciliation observations, the timeline)."""

    failed = CaseSnapshot(SUMMARY, [], ME, documents_loaded=False)
    assert _boundary(failed, "What should I do next?") == "SYNTHETIC_DOCUMENTS_UNAVAILABLE"
    summary: dict[str, Any] = copy.deepcopy(SUMMARY)
    summary["reconciliation"]["discrepancies"][0]["observations"][0]["document_display_name"] = (
        "Tan Wei Lee.pdf"
    )
    assert _boundary(_snapshot(summary), "What should I do next?") == (
        "SYNTHETIC_DOCUMENT_NOT_APPROVED"
    )


def test_the_client_marks_a_document_list_it_could_not_read() -> None:
    from uuid import UUID

    from ai_assistant.clm_client import ClmBackendClient

    def backend(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/documents"):
            return httpx.Response(500, json={"detail": "down"})
        if request.url.path == "/api/auth/me":
            return httpx.Response(200, json=ME)
        return httpx.Response(200, json=SUMMARY)

    client = ClmBackendClient(
        "http://127.0.0.1:8000", timeout_seconds=5, transport=httpx.MockTransport(backend)
    )
    snapshot = client.load_case(UUID(CASE_ID), "session")
    assert snapshot.documents == [] and snapshot.documents_loaded is False


def test_a_case_data_answer_with_its_timestamp_can_be_sent_back_as_history() -> None:
    """QG R3-A2: one fallback must not end model use for the whole thread; a bare date in a
    hand-built assistant turn is still refused."""

    asked = {"role": "user", "content": "Which registry was used for this company?"}
    answer = "Registry data in this case comes from ACRA (MOCK), retrieved 28 Oct 2026, 01:21 UTC."
    assert (
        _boundary(
            _snapshot(), "What should I do next?", [asked, {"role": "assistant", "content": answer}]
        )
        is None
    )
    forged = {"role": "assistant", "content": "The director was born 12 Mar 1985."}
    assert _boundary(_snapshot(), "What should I do next?", [asked, forged]) == (
        "SYNTHETIC_TEXT_NOT_APPROVED"
    )


def test_a_question_using_approved_values_and_few_numbers_is_inside() -> None:
    assert _boundary(_snapshot(), "What does UEN 11111999A tell me about this company?") is None


def _tagged(text: str) -> str:
    """Invisible Unicode tag characters carrying a hidden ASCII copy of ``text``."""

    return "".join(chr(0xE0000 + ord(char)) for char in text)


def _circled(text: str) -> str:
    return "".join(chr(0x24B6 + ord(char) - ord("A")) if char.isupper() else char for char in text)


# QG R2-1: characters the word check cannot see.
HIDDEN = [
    "What should I do next?" + _tagged("TAN AH KOW S1234567D"),
    "What should I do next? " + _circled("TAN AH KOW"),
    "What should I do next? Ⓢ①②③",  # circled S, 1, 2, 3
    "What should I do next? ⠁⠃⠉",  # Braille
    "What should I do next? \U0001f1f8\U0001f1ec",  # regional indicators
    "What should I do next? ",  # private use
    "What should I do next? \U0001f600",  # emoji
    "What should I do next?​‍",  # zero-width format characters
]


@pytest.mark.parametrize("question", HIDDEN)
def test_characters_the_word_check_cannot_see_are_refused(question: str) -> None:
    assert _boundary(_snapshot(), question) == "SYNTHETIC_TEXT_NOT_APPROVED"


def test_split_numbers_are_refused_within_and_across_user_turns() -> None:
    """QG R2-2: never two number groups side by side, at most three across the user turns."""

    assert _boundary(_snapshot(), "What should I do next? s 123456 7") is not None
    history = [
        {"role": "user", "content": "What does UEN 11111999A tell me?"},
        {"role": "assistant", "content": ALLOWED},
        {"role": "user", "content": "What does 18 and 01 mean here?"},
        {"role": "assistant", "content": ALLOWED},
    ]
    assert _boundary(_snapshot(), "And what about 25?", history) == "SYNTHETIC_TEXT_NOT_APPROVED"


@pytest.mark.parametrize(
    "answer",
    ["Ryan Tan and Olivia Koh are the directors.", "The number is S 8 5 1 2 3 4 5 A."],
)
def test_a_forged_assistant_turn_cannot_carry_names_or_split_numbers(answer: str) -> None:
    """QG R2-3: assistant history may not use the application's code strings (seeded user
    names) or long runs of number groups."""

    history = [
        {"role": "user", "content": "Who are the directors of this company?"},
        {"role": "assistant", "content": answer},
    ]
    assert _boundary(_snapshot(), "What should I do next?", history) == (
        "SYNTHETIC_TEXT_NOT_APPROVED"
    )


@pytest.mark.parametrize(
    "question",
    [
        "Who are the directors of this company?",
        "What should I do next?",
        "Which registry was used for this company, and is that registry live?",
        "What documents are still missing before this case can move on?",
        "What is the status of this case?",  # QG R2-4: no longer over-blocked
        "Can you summarise the discrepancy, please?",
    ],
)
def test_ordinary_synthetic_questions_are_inside(question: str) -> None:
    assert _boundary(_snapshot(), question) is None


def _settle_verification() -> None:
    """Wait for every background verification a chat call started."""

    for thread in threading.enumerate():
        if thread.name == "remote-verification":
            thread.join(30)
            assert not thread.is_alive()


def _model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, provider: "OpenRouter") -> Any:
    settings = config(tmp_path)
    new_ledger(settings)
    return remote_test.RemoteTestModel(
        settings,
        environ={"OPENROUTER_API_KEY": SENTINEL},
        transport=provider.transport(),
        fetch=listing,
        background=False,
    )


def test_the_model_itself_refuses_text_outside_the_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defence in depth (QG A-1): a caller that skipped the chat's check still sends nothing."""

    provider = OpenRouter()
    model = _model(tmp_path, monkeypatch, provider)
    messages = [{"role": "system", "content": "Rules."}, {"role": "user", "content": QG_PROBE}]
    with pytest.raises(ModelCallError):
        model.complete(messages)

    async def drain() -> None:
        async for _ in model.stream(messages):
            pass

    with pytest.raises(ModelCallError):
        anyio.run(drain)
    assert provider.requests == []


def test_the_stream_runs_its_blocking_checks_off_the_event_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG F-3: the preflight and the metadata wait must not stall the service's event loop."""

    provider = OpenRouter()
    model = _model(tmp_path, monkeypatch, provider)
    seen: dict[str, int] = {}

    def ready(messages: Any) -> None:
        seen["ready"] = threading.get_ident()
        raise ModelCallError("budget_refused")

    monkeypatch.setattr(model, "_ready", ready)

    async def drain() -> None:
        seen["loop"] = threading.get_ident()
        async for _ in model.stream([{"role": "user", "content": "What should I do next?"}]):
            pass

    with pytest.raises(ModelCallError):
        anyio.run(drain)
    assert seen["ready"] != seen["loop"]


def test_only_unchanged_repository_knowledge_is_inside() -> None:
    entry = parse_guidance(sorted(GUIDANCE_DIR.glob("*.md"))[0])
    facts = build_case_facts(_snapshot())
    messages = build_messages(facts, [], "What should I do next?")
    assert check(_snapshot(), facts, messages, [entry]) is None
    edited = dataclasses.replace(entry, body=entry.body + " Edited in the app.")
    assert check(_snapshot(), facts, messages, [edited]) == "SYNTHETIC_KNOWLEDGE_NOT_APPROVED"


# --- the whole journey: AI Models page -> RM chat -> roll back -------------------------------


class Journey:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **extra: Any) -> None:
        self.settings = config(
            tmp_path, write_profiles(tmp_path / "profiles.json", profile()), **extra
        )
        new_ledger(self.settings)
        self.openrouter = OpenRouter()
        self.local = ModelServer()
        self.backend = Backend()
        self.baseline = Baseline()
        monkeypatch.setattr("ai_assistant.main.build_chat_model", lambda *a, **k: self.baseline)
        monkeypatch.setattr(model_admin, "SUPERVISE_SECONDS", 0.05)
        monkeypatch.setattr(remote_test, "fetch_public", listing)
        self.app = create_app(
            # Looked up per request, so a test can swap the backend's handler.
            self.settings,
            clm_transport=httpx.MockTransport(lambda request: self.backend.handler(request)),
        )
        selector: ModelSelector = self.app.state.model_selector
        selector.environ = {"OPENROUTER_API_KEY": SENTINEL}
        selector.transport = self.openrouter.transport()
        selector.fetch = listing
        selector.launch = self._launcher(selector)
        self.selector = selector
        self.client = TestClient(self.app, headers={"Origin": ORIGIN})
        self.client.cookies.set("clm_session", "hr-session")

    @staticmethod
    def _launcher(selector: ModelSelector) -> Any:
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

        return launch

    def ask(self, message: str = "What should I do next?", stream: bool = False) -> Any:
        self.client.cookies.set("clm_session", "rm-session")
        try:
            path = f"/assistant/cases/{CASE_ID}/chat" + ("/stream" if stream else "")
            reply = self.client.post(path, json={"message": message})
        finally:
            self.client.cookies.set("clm_session", "hr-session")
        assert reply.status_code == 200, reply.text
        if stream:
            events = [json.loads(line) for line in reply.text.splitlines() if line.strip()]
            return next(event for event in events if event["type"] == "done")
        return reply.json()

    def start_qualification(self, profile_id: str = OPENROUTER_PROFILE_ID) -> Any:
        """D-098: a paid run starts only with its number of calls confirmed."""

        return self.client.post(
            f"{API}/{profile_id}/qualifications",
            json={"confirm_paid_calls": self.settings.local_api_test_qualification_count},
        )

    def activate_remote(self) -> dict[str, Any]:
        test = self.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
        assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text
        started = self.start_qualification()
        assert started.status_code == 202, started.text
        result = wait_for(self.client, started.json()["qualification_id"])
        assert result["status"] == "passed", result
        revision = self.client.get(API).json()["revision"]
        applied = self.client.post(
            f"{API}/{OPENROUTER_PROFILE_ID}/activate",
            json={"expected_revision": revision, "acknowledge_quality_unscored": True},
        )
        assert applied.status_code == 200, applied.text
        return result


def test_hr_activates_gpt_oss_and_the_rm_chat_uses_it_then_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    overview = journey.client.get(API).json()
    remote = next(p for p in overview["profiles"] if p["profile_id"] == OPENROUTER_PROFILE_ID)
    assert remote["status"] == "selectable" and remote["activation_blockers"] == ["NOT_QUALIFIED"]

    result = journey.activate_remote()
    # The paid qualification asked only the two manifest questions, each verified (G-8).
    gates = {gate["gate"]: gate for gate in result["gates"]}
    assert gates["G-8"]["passed"] and gates["G-8"]["value"] == "2/2"
    assert result["total_turns"] == 2 and len(journey.openrouter.chats) == 2
    assert result["done_turns"] == 2  # the page showed "1/2 turns" for a finished run
    assert journey.client.get(API).json()["active"]["model_id"] == OPENROUTER_MODEL_ID

    for stream in (False, True):
        reply = journey.ask(stream=stream)
        assert reply["answered_by"] == "model" and reply["model"] == OPENROUTER_MODEL_ID
        assert reply["notice"].startswith(REMOTE_NOTICE)
    assert len(journey.openrouter.chats) == 4 and journey.baseline.calls == 0
    _settle_verification()  # QG F-4: verification after a chat call runs in the background
    ledger = BudgetLedger.open(Path(journey.settings.budget_ledger_path))
    assert [c.verification for c in ledger.closed_calls_after(0)] == ["verified"] * 4

    # Back to the local baseline from the same page.
    revision = journey.client.get(API).json()["revision"]
    back = journey.client.post(f"{API}/rollback", json={"expected_revision": revision})
    assert back.status_code == 200, back.text
    reply = journey.ask()
    assert reply["answered_by"] == "model" and reply["model"] == "ministral-3:8b"
    assert len(journey.openrouter.chats) == 4 and journey.baseline.calls == 1


def test_a_case_outside_the_boundary_sends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    before = len(journey.openrouter.chats)
    real = _with_entity(registration_number="201511222D", legal_name="OPQ PTE. LTD.")
    monkeypatch.setattr("tests.test_model_management.SUMMARY", real)
    for stream in (False, True):
        reply = journey.ask(stream=stream)
        assert reply["answered_by"] == "case_data"
        assert reply["notice"] == f"{REMOTE_BOUNDARY_NOTICE} Reason: SYNTHETIC_CASE_NOT_APPROVED."
    monkeypatch.setattr("tests.test_model_management.SUMMARY", SUMMARY)
    reply = journey.ask("Is Tan Ah Kow, NRIC S1234567D, a director here?")
    assert reply["answered_by"] == "case_data"
    assert reply["notice"].endswith("Reason: SYNTHETIC_TEXT_NOT_APPROVED.")
    assert "Tan" not in reply["notice"] and "S1234567D" not in reply["notice"]
    # QG F-1 and R2-1: the probes that used to reach OpenRouter, on both routes.
    for probe in (QG_PROBE, HIDDEN[0], HIDDEN[1]):
        for stream in (False, True):
            reply = journey.ask(probe, stream=stream)
            assert reply["answered_by"] == "case_data"
            assert reply["notice"].endswith("Reason: SYNTHETIC_TEXT_NOT_APPROVED.")
    assert len(journey.openrouter.chats) == before and journey.baseline.calls == 0


def test_a_document_list_that_fails_to_load_sends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QG R4-1 end to end: the backend's document list fails, so nothing goes to OpenRouter."""

    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    before = len(journey.openrouter.chats)
    handler = journey.backend.handler

    def failing(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/documents"):
            return httpx.Response(500, json={"detail": "down"})
        return handler(request)

    monkeypatch.setattr(journey.backend, "handler", failing)
    for stream in (False, True):
        reply = journey.ask(stream=stream)
        assert reply["answered_by"] == "case_data"
        assert reply["notice"].endswith("Reason: SYNTHETIC_DOCUMENTS_UNAVAILABLE.")
    assert len(journey.openrouter.chats) == before


def test_a_failed_api_call_gives_the_case_data_answer_and_stops_later_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    journey.openrouter.fail = True
    reply = journey.ask()
    assert reply["answered_by"] == "case_data" and reply["answer"]
    # The failed call has no generation id: quarantined, breaker open, nothing else is sent.
    ledger = BudgetLedger.open(Path(journey.settings.budget_ledger_path))
    _settle_verification()
    assert ledger.status().breaker_open
    sent = len(journey.openrouter.chats)
    journey.openrouter.fail = False
    assert journey.ask()["answered_by"] == "case_data"
    assert len(journey.openrouter.chats) == sent


def test_a_wrong_provider_quarantines_and_stops_later_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch)
    journey.activate_remote()
    journey.openrouter.provider = "Some Other Provider"
    assert journey.ask()["answered_by"] == "model"
    _settle_verification()
    sent = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "case_data"
    assert len(journey.openrouter.chats) == sent
    assert BudgetLedger.open(Path(journey.settings.budget_ledger_path)).status().breaker_open


def test_the_process_call_limit_holds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    journey = Journey(tmp_path, monkeypatch, local_api_test_max_calls=3)
    journey.activate_remote()  # 2 qualification calls in their own (here: in-test) model
    assert journey.ask()["answered_by"] == "model"
    assert journey.ask()["answered_by"] == "model"
    assert journey.ask()["answered_by"] == "model"
    sent = len(journey.openrouter.chats)
    assert journey.ask()["answered_by"] == "case_data"
    assert len(journey.openrouter.chats) == sent


def test_qualification_needs_the_manifest_and_the_key_never_leaves_the_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, local_api_test_qualification_questions="")
    refused = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/qualifications")
    assert (
        refused.status_code == 409 and refused.json()["detail"]["code"] == "REMOTE_MANIFEST_MISSING"
    )
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    texts = [test.text, journey.client.get(API).text, journey.client.get(f"{API}/audit").text]
    assert all(SENTINEL not in text for text in texts)
    # The preflight makes no inference request.
    assert journey.openrouter.chats == []


def test_without_the_decision_the_remote_profile_is_refused_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journey = Journey(tmp_path, monkeypatch, local_api_test_decision="")
    for path in ("connection-test", "qualifications"):
        refused = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/{path}")
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "REMOTE_NOT_AUTHORISED"
    assert journey.openrouter.requests == []
    assert set(USERS) >= {"hr-session", "rm-session"}
