"""D-099 (proposed): Claude Sonnet 5.5 Balanced and Fast on AI Models, listed but never usable.

Offline: the dormant adapter accepts only an in-memory ``httpx.MockTransport`` and the suite's
socket guard (conftest) refuses any real connection. The key is a sentinel searched for in
every output.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from pydantic import SecretStr

from ai_assistant import anthropic_chat, anthropic_profiles, model_catalog
from ai_assistant.anthropic_chat import AnthropicChatModel
from ai_assistant.anthropic_profiles import BALANCED, FAST
from ai_assistant.config import AiAssistantSettings
from ai_assistant.llm import ModelCallError, Piece
from ai_assistant.model_admin import UNAVAILABLE_ID, eligible_run
from ai_assistant.model_admin_store import Choice, ModelAdminStore
from ai_assistant.model_catalog import load_catalogue
from ai_assistant.model_profiles import ProfileConfigError
from ai_assistant.model_qualification import qualification_basis
from ai_assistant.openrouter import LIVE_NETWORK
from ai_assistant.remote_test import remote_fingerprint
from assistant_eval.runner import Workspace, run
from assistant_eval.scenarios import EVAL_FIXTURES, load_scenarios
from assistant_eval.snapshot import offered_lines
from tests.remote_fixtures import Chunks
from tests.test_model_management import (
    API,
    USERS,
    Backend,
    ModelServer,
    build_app,
    profile,
    settings,
    write_profiles,
)

# Built at run time so the secret scanner never sees a key-shaped literal.
SENTINEL = "sk-" + "ant-" + "api03-" + "ClaudeConsoleSentinel" * 3
SYSTEM = [{"role": "system", "content": "RULES"}, {"role": "system", "content": "CASE FACTS"}]
MESSAGES = [*SYSTEM, {"role": "user", "content": "Is this case ready for review?"}]
CLAUDE = (BALANCED.profile_id, FAST.profile_id)


@pytest.fixture
def server() -> ModelServer:
    return ModelServer()


@pytest.fixture
def backend() -> Backend:
    return Backend()


def _profiles(client: Any) -> dict[str, dict[str, Any]]:
    reply = client.get(API)
    assert reply.status_code == 200
    return {item["profile_id"]: item for item in reply.json()["profiles"]}


def _client(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: Any, **extra: Any
) -> Any:
    if extra:
        original = settings

        def configured(
            path: Path, profiles_file: Path | None = None, **more: Any
        ) -> AiAssistantSettings:
            return original(path, profiles_file, **{**extra, **more})

        monkeypatch.setattr("tests.test_model_management.settings", configured)
    return build_app(tmp_path, backend, server, monkeypatch)


# --- AI Models: listed, accurate, never usable ------------------------------------------------


def test_both_configurations_are_listed_with_accurate_details_and_not_authorised(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, backend, server, monkeypatch)
    profiles = _profiles(client)
    balanced, fast = profiles[BALANCED.profile_id], profiles[FAST.profile_id]
    for item, effort, thinking in (
        (balanced, "medium", "adaptive"),
        (fast, "low", "between_tools"),
    ):
        assert item["status"] == "pending_authorisation"
        assert item["reason"] == "ANTHROPIC_NOT_AUTHORISED"
        assert item["deployment"] == "anthropic" and item["source"] == "code"
        assert item["model_id"] == "claude-sonnet-5-5" and item["model_version"] == effort
        assert item["endpoint"] == "api.anthropic.com · claude-sonnet-5-5"
        assert item["details"] == {
            "model": "Claude Sonnet 5.5",
            "provider": "ANTHROPIC",
            "scope": "NOT_AUTHORISED",
            "reasoning_effort": effort,
            "thinking": thinking,
            "decision": "D-099",
        }
        assert item["activation_blockers"] == ["ANTHROPIC_NOT_AUTHORISED"]
        assert not item.get("active")
    # GPT-OSS is listed exactly as before, beside them.
    assert profiles["openrouter_gpt_oss_120b"]["status"] == "pending_authorisation"


def test_naming_the_decision_only_changes_the_reason_never_the_availability(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, backend, server, monkeypatch, anthropic_decision="D-099")
    profiles = _profiles(client)
    for profile_id in CLAUDE:
        item = profiles[profile_id]
        assert item["status"] == "unavailable"
        assert item["reason"] == "ANTHROPIC_PROVIDER_CONTROLS_MISSING"
        assert item["details"]["scope"] == "PROVIDER_CONTROLS_MISSING"


@pytest.mark.parametrize(
    ("decision", "code"), [("", "REMOTE_NOT_AUTHORISED"), ("D-099", "PROFILE_NOT_SELECTABLE")]
)
def test_every_action_is_refused_before_any_network_call_and_audited(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    decision: str,
    code: str,
) -> None:
    client = _client(tmp_path, backend, server, monkeypatch, anthropic_decision=decision)
    for profile_id in CLAUDE:
        calls = [
            client.post(f"{API}/{profile_id}/connection-test"),
            client.post(f"{API}/{profile_id}/qualifications", json={"confirm_paid_calls": 2}),
            client.post(
                f"{API}/{profile_id}/activate",
                json={"expected_revision": 0, "acknowledge_quality_unscored": True},
            ),
        ]
        assert {reply.status_code for reply in calls} == {409}
        assert {reply.json()["detail"]["code"] for reply in calls} == {code}
    assert server.requests == []
    events = client.get(f"{API}/audit").json()["events"]
    refused = [e for e in events if e.get("profile_id") in CLAUDE and e["outcome"] == "refused"]
    assert len(refused) == 6
    assert {e["code"] for e in refused} == {code}
    assert {e["actor"] for e in refused} == {"hr-admin"}
    # Nothing became active and no qualification was recorded for either configuration.
    overview = client.get(API).json()
    assert overview["active"]["profile_id"] not in CLAUDE
    assert all(not _profiles(client)[p].get("qualification") for p in CLAUDE)


@pytest.mark.parametrize("session", ["rm-session", "co-session", "director-session"])
def test_only_hr_may_act_on_them(
    tmp_path: Path,
    backend: Backend,
    server: ModelServer,
    monkeypatch: pytest.MonkeyPatch,
    session: str,
) -> None:
    client = _client(tmp_path, backend, server, monkeypatch)
    client.cookies.set("clm_session", session)
    calls = [
        client.post(f"{API}/{BALANCED.profile_id}/activate", json={"expected_revision": 0}),
        client.post(f"{API}/{FAST.profile_id}/qualifications"),
    ]
    assert {reply.status_code for reply in calls} == {403}
    assert {reply.json()["detail"]["code"] for reply in calls} == {"MODEL_CONFIG_FORBIDDEN"}
    client.cookies.set("clm_session", "hr-session")
    refused = [
        e for e in client.get(f"{API}/audit").json()["events"] if e["action"] == "ACCESS_REFUSED"
    ]
    assert {e["actor"] for e in refused} == {USERS[session][0]}


def test_fingerprints_are_distinct_stable_and_never_gpt_oss(tmp_path: Path) -> None:
    config = settings(tmp_path)
    entries = {entry.profile_id: entry for entry in load_catalogue(config).entries}
    balanced, fast = entries[BALANCED.profile_id], entries[FAST.profile_id]
    assert balanced.fingerprint != fast.fingerprint
    assert balanced.fingerprint == model_catalog.fingerprint(BALANCED.identity())
    again = load_catalogue(config).get(BALANCED.profile_id)
    assert again is not None and again.fingerprint == balanced.fingerprint
    assert remote_fingerprint(config) not in {balanced.fingerprint, fast.fingerprint}
    # Every request parameter is part of the identity.
    assert BALANCED.identity()["request"] == {
        "model": "claude-sonnet-5-5",
        "max_tokens": 3000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "medium"},
    }
    assert FAST.identity()["request"]["thinking"] == {"type": "between_tools"}
    assert FAST.identity()["request"]["output_config"] == {"effort": "low"}


def test_a_pass_of_one_configuration_never_counts_for_another(tmp_path: Path) -> None:
    config = settings(tmp_path)
    entries = {entry.profile_id: entry for entry in load_catalogue(config).entries}
    store = ModelAdminStore(tmp_path / "state" / "admin.sqlite3")
    basis = qualification_basis()
    balanced = entries[BALANCED.profile_id]
    run_id = store.begin_qualification(
        balanced.profile_id, balanced.fingerprint, basis, "hr-admin", 2
    )
    store.finish_qualification(run_id, "passed", None, {"gates": {}})
    assert eligible_run(store, balanced.profile_id, balanced.fingerprint, basis)[0] is not None
    fast = entries[FAST.profile_id]
    assert eligible_run(store, fast.profile_id, fast.fingerprint, basis) == (None, "NOT_QUALIFIED")
    gpt = entries["openrouter_gpt_oss_120b"]
    assert eligible_run(store, gpt.profile_id, gpt.fingerprint, basis) == (None, "NOT_QUALIFIED")
    # Not even under the other configuration's fingerprint or profile id.
    assert eligible_run(store, fast.profile_id, balanced.fingerprint, basis) == (
        None,
        "NOT_QUALIFIED",
    )
    assert eligible_run(store, balanced.profile_id, fast.fingerprint, basis) == (
        None,
        "NOT_QUALIFIED",
    )


def test_a_stored_claude_activation_is_never_served_and_switches_to_nothing(
    tmp_path: Path, backend: Backend, server: ModelServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Unreachable through AI Models (activation is refused); a tampered state database must
    # still never serve Claude nor switch to another model: D-098 "AI unavailable".
    store = ModelAdminStore(tmp_path / "state" / "admin.sqlite3")
    entry = load_catalogue(settings(tmp_path)).get(BALANCED.profile_id)
    assert entry is not None
    store.activate(
        store.revision(), Choice(entry.profile_id, entry.fingerprint, "0" * 32, 9000), None, "x"
    )
    client = _client(tmp_path, backend, server, monkeypatch)
    active = client.app.state.model_selector.current()
    assert active.model is None and active.profile_id == UNAVAILABLE_ID
    assert server.requests == []


def test_an_it_profiles_file_cannot_take_a_claude_profile_id(tmp_path: Path) -> None:
    path = write_profiles(tmp_path / "profiles.json", profile(profile_id=BALANCED.profile_id))
    catalogue = load_catalogue(settings(tmp_path, path))
    assert catalogue.file_status == "invalid"


def test_the_service_never_composes_the_adapter(tmp_path: Path) -> None:
    for decision in ("", "D-099"):
        with pytest.raises(ProfileConfigError) as error:
            anthropic_chat.build(
                BALANCED.profile_id, settings(tmp_path, anthropic_decision=decision)
            )
        assert error.value.code in {
            "ANTHROPIC_NOT_AUTHORISED",
            "ANTHROPIC_PROVIDER_CONTROLS_MISSING",
        }
    runtime = Path(anthropic_chat.__file__).parent
    users = [
        p.name
        for p in runtime.rglob("*.py")
        if "anthropic_chat" in p.read_text(encoding="utf-8") and p.name != "anthropic_chat.py"
    ]
    assert users == []  # no automatic or manual path builds it in the service


# --- the dormant adapter ------------------------------------------------------------------------


def _sse(*events: dict[str, Any]) -> bytes:
    return b"".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n".encode() for e in events)


def _reply(
    text: str = "Line one.",
    *,
    model: str = "claude-sonnet-5-5",
    stop: str = "end_turn",
    start_usage: dict[str, Any] | None = None,
    end_usage: dict[str, Any] | None = None,
    finished: bool = True,
) -> bytes:
    events: list[dict[str, Any]] = [
        {
            "type": "message_start",
            "message": {
                "id": "msg_test01",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "usage": start_usage
                if start_usage is not None
                else {"input_tokens": 4000, "output_tokens": 1},
            },
        },
        {"type": "ping"},
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "SECRET THOUGHT"},
        },
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": text}},
        {"type": "content_block_stop", "index": 1},
        {
            "type": "message_delta",
            "delta": {"stop_reason": stop},
            "usage": end_usage if end_usage is not None else {"output_tokens": 500},
        },
    ]
    if finished:
        events.append({"type": "message_stop"})
    return _sse(*events)


class Api:
    def __init__(self, *replies: tuple[int, bytes]) -> None:
        self.replies = list(replies)
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            status, body = self.replies.pop(0)
            kind = "text/event-stream" if status == 200 else "application/json"
            return httpx.Response(status, stream=Chunks([body]), headers={"content-type": kind})

        return httpx.MockTransport(handler)


def _model(
    api: Api, configuration: Any = BALANCED, max_prompt_bytes: int = 30000
) -> AnthropicChatModel:
    return AnthropicChatModel(
        configuration=configuration,
        credential=SecretStr(SENTINEL),
        max_prompt_bytes=max_prompt_bytes,
        transport=api.transport(),
    )


def _collect(
    model: AnthropicChatModel, messages: list[dict[str, str]] = MESSAGES
) -> tuple[list[Piece], ModelCallError | None]:
    pieces: list[Piece] = []

    async def gather() -> ModelCallError | None:
        try:
            async for piece in model.stream(messages):
                pieces.append(piece)
        except ModelCallError as error:
            return error
        return None

    return pieces, anyio.run(gather)


@pytest.mark.parametrize("transport", [LIVE_NETWORK, httpx.AsyncHTTPTransport(), None])
def test_only_an_in_memory_transport_is_accepted(transport: object) -> None:
    with pytest.raises(ProfileConfigError) as error:
        AnthropicChatModel(
            configuration=BALANCED,
            credential=SecretStr(SENTINEL),
            max_prompt_bytes=1,
            transport=transport,
        )
    assert error.value.code == "TRANSPORT_NOT_ALLOWED"


@pytest.mark.parametrize("configuration", [BALANCED, FAST])
def test_the_request_is_pinned_and_carries_only_the_configuration(configuration: Any) -> None:
    api = Api((200, _reply()))
    pieces, error = _collect(_model(api, configuration))
    assert error is None and "".join(p.text for p in pieces) == "Line one."
    request = api.requests[0]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == SENTINEL
    assert request.headers["anthropic-version"] == "2026-10-21"
    body = json.loads(request.content)
    assert body == {
        "model": "claude-sonnet-5-5",
        "max_tokens": 3000,
        "thinking": {"type": configuration.thinking},
        "output_config": {"effort": configuration.effort},
        "system": [{"type": "text", "text": "RULES"}, {"type": "text", "text": "CASE FACTS"}],
        "messages": [{"role": "user", "content": "Is this case ready for review?"}],
        "stream": True,
    }


def test_usage_is_settled_at_the_published_price_and_thinking_is_never_shown() -> None:
    pieces, error = _collect(_model(Api((200, _reply()))))
    assert error is None
    assert all("SECRET THOUGHT" not in p.text for p in pieces)
    last = pieces[-1]
    assert last.finish_reason == "stop" and not last.cut_short
    assert last.usage is not None
    # 4,000 x US$2/M + 500 x US$10/M = US$0.013
    assert last.usage.cost == Decimal("0.013")
    assert (last.usage.prompt_tokens, last.usage.completion_tokens) == (4000, 500)
    assert last.usage.generation_ref == "msg_test01" and last.usage.anomalies == ()
    assert SENTINEL not in repr(_model(Api()))


def test_another_model_answering_stops_before_any_text() -> None:
    pieces, error = _collect(_model(Api((200, _reply(model="claude-opus-5-5")))))
    assert pieces == [] and error is not None and error.error_class == "protocol"
    assert error.usage is not None and "model_mismatch" in error.usage.anomalies
    assert error.usage.cost is None


@pytest.mark.parametrize(
    ("start", "end", "anomaly"),
    [
        ({"input_tokens": 4000, "output_tokens": 1, "speed": "fast"}, None, "provider_mismatch"),
        (
            {"input_tokens": 4000, "output_tokens": 1, "service_tier": "priority"},
            None,
            "provider_mismatch",
        ),
        (
            {"input_tokens": 4000, "output_tokens": 1, "inference_geo": "us"},
            None,
            "provider_mismatch",
        ),
        (
            {"input_tokens": 4000, "output_tokens": 1, "cache_read_input_tokens": 100},
            None,
            "usage_malformed",
        ),
        ({"output_tokens": 1}, None, "usage_missing"),
        (None, {}, "usage_missing"),
    ],
)
def test_billing_uncertainty_drops_the_cost(start: Any, end: Any, anomaly: str) -> None:
    pieces, error = _collect(_model(Api((200, _reply(start_usage=start, end_usage=end)))))
    assert error is None
    usage = pieces[-1].usage
    assert usage is not None and anomaly in usage.anomalies and usage.cost is None


def test_refusal_truncation_and_an_unfinished_stream() -> None:
    _, refused = _collect(_model(Api((200, _reply(stop="refusal")))))
    assert refused is not None and refused.error_class == "content_filter"
    pieces, error = _collect(_model(Api((200, _reply(stop="max_tokens")))))
    assert error is None and pieces[-1].cut_short and pieces[-1].finish_reason == "length"
    _, cut = _collect(_model(Api((200, _reply(finished=False)))))
    assert cut is not None and cut.error_class == "upstream_midstream"
    assert cut.usage is not None and cut.usage.cost is None  # uncertain: never settled


@pytest.mark.parametrize(
    ("status", "body", "error_class"),
    [
        (401, {}, "auth"),
        (403, {}, "forbidden"),
        (400, {"error": {"type": "invalid_request_error", "message": "bad"}}, "bad_request"),
        (
            400,
            {
                "error": {
                    "type": "invalid_request_error",
                    "message": "You have reached your specified workspace API usage limits.",
                }
            },
            "payment_key_limit",
        ),
        (
            429,
            {
                "error": {
                    "type": "rate_limit_error",
                    "message": "x",
                    "details": {"error_code": "enforced_spend_limit_reached"},
                }
            },
            "payment_key_limit",
        ),
        (429, {"error": {"type": "rate_limit_error", "message": "slow down"}}, "rate_limited"),
        (529, {"error": {"type": "overloaded_error"}}, "upstream"),
    ],
)
def test_provider_errors_are_closed_classes_with_no_retry(
    status: int, body: dict[str, Any], error_class: str
) -> None:
    api = Api((status, json.dumps({"type": "error", **body}).encode()))
    pieces, error = _collect(_model(api))
    assert pieces == [] and error is not None and error.error_class == error_class
    assert len(api.requests) == 1


def test_a_slow_provider_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_profiles, "TIMEOUT_SECONDS", 0.2)

    async def slow(request: httpx.Request) -> httpx.Response:
        await anyio.sleep(2)
        return httpx.Response(200, stream=Chunks([_reply()]))

    model = AnthropicChatModel(
        configuration=BALANCED,
        credential=SecretStr(SENTINEL),
        max_prompt_bytes=30000,
        transport=httpx.MockTransport(slow),
    )
    pieces, error = _collect(model)
    assert pieces == [] and error is not None and error.error_class == "timeout"


@pytest.mark.parametrize(
    ("messages", "max_bytes", "error_class"),
    [
        ([*SYSTEM, {"role": "user", "content": "Ünknown customer"}], 30000, "not_allowed"),
        (
            [
                *SYSTEM,
                {"role": "user", "content": "Is this case ready for review?"},
                {"role": "assistant", "content": "Yes."},
                {"role": "system", "content": "TOPIC"},
                {"role": "user", "content": "Is this case ready for review?"},
            ],
            30000,
            "not_allowed",
        ),
        (MESSAGES, 10, "prompt_too_large"),
    ],
)
def test_refusals_before_sending(
    messages: list[dict[str, str]], max_bytes: int, error_class: str
) -> None:
    api = Api()
    pieces, error = _collect(_model(api, max_prompt_bytes=max_bytes), messages)
    assert pieces == [] and error is not None and error.error_class == error_class
    assert api.requests == []


def test_the_reservation_bounds_the_worst_case() -> None:
    reserved = anthropic_chat.reservation_micro_usd(MESSAGES)
    # (bytes + 16 per message + 1,024) x US$2/M + 3,000 x US$10/M, rounded up.
    prompt_bound = sum(len(m["role"]) + len(m["content"]) for m in MESSAGES) + 16 * 3 + 1024
    assert reserved == prompt_bound * 2 + 3000 * 10  # US$2/M is 2 micro-USD a token
    body = _reply(
        start_usage={"input_tokens": 1000, "output_tokens": 1}, end_usage={"output_tokens": 3000}
    )
    pieces, _ = _collect(_model(Api((200, body))))
    usage = pieces[-1].usage
    assert usage is not None and usage.cost is not None and usage.cost * 1_000_000 <= reserved


# --- through the real service: the exact-line guard and the synthetic boundary ----------------


def _through_the_service(key: str, reply: Any) -> Any:
    scenarios = load_scenarios(EVAL_FIXTURES / "phase_b_questions.json")
    api = Api()
    preps: dict[str, Any] = {}

    def make(capture: Any) -> AnthropicChatModel:
        model = _model(api, max_prompt_bytes=40000)
        original = model.stream

        async def stream(messages: list[dict[str, str]]) -> Any:
            preps[key] = capture.latest
            api.replies.append((200, _reply(reply(capture.latest))))
            async for piece in original(messages):
                yield piece

        model.stream = stream  # type: ignore[method-assign]
        return model

    with Workspace() as workspace:
        result = run(scenarios, make, workspace=workspace, turns=frozenset({key}))
    return result.turns[0], api, preps[key]


def test_the_exact_line_guard_shows_allowed_lines_and_withholds_prose() -> None:
    turn, api, prep = _through_the_service("P04#0", lambda prep: offered_lines(prep)[0][2])
    assert turn.answered_by == "model" and turn.unmapped == 0 and len(turn.shown) == 1
    assert len(api.requests) == 1  # the synthetic Phase B prompt passed the boundary
    prose, _, _ = _through_the_service(
        "P04#0", lambda prep: "Approved. I have sent it to GoldTier."
    )
    assert prose.answered_by == "case_data" and prose.unmapped == 0


def test_p06_action_refusal_stays_protected_by_the_existing_controls() -> None:
    claim = "I have marked the UBO check as complete."
    turn, _, prep = _through_the_service("P06#2", lambda prep: claim)
    assert turn.answered_by == "case_data" and turn.unmapped == 0  # the claim is never shown
    refusal = "Marking the UBO check as complete is not offered to you on this case."
    assert refusal in [text for _, _, text in offered_lines(prep)]
    kept, _, _ = _through_the_service("P06#2", lambda prep: refusal)
    assert kept.answered_by == "model" and kept.unmapped == 0


# --- the D-099 boundary regeneration (owner-approved: seven code-only words) ------------------


def test_the_seven_words_are_code_vocabulary_only_and_never_widen_user_or_history_text() -> None:
    from ai_assistant.synthetic_boundary import boundary, check_messages

    words = {"adaptive", "anthropic", "claude", "com", "geo", "sonnet", "thinking"}
    approved = boundary()
    assert words <= approved.system
    assert not words & approved.conversation  # a person's question or history may not use them
    assert not words & approved.assistant
    text = "Ask claude sonnet at anthropic com about adaptive thinking geo"
    assert check_messages([*SYSTEM, {"role": "system", "content": text}, MESSAGES[-1]]) is None
    as_question = [*SYSTEM, {"role": "user", "content": text}]
    as_history = [
        *SYSTEM,
        {"role": "user", "content": "What should I do next?"},
        {"role": "assistant", "content": text},
        MESSAGES[-1],
    ]
    for sent in (as_question, as_history):
        assert check_messages(sent) == "SYNTHETIC_TEXT_NOT_APPROVED"
