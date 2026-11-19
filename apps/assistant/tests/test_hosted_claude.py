"""R2.2 (D-129 proposed): Claude Sonnet 5.5 through Anthropic on the hosted service.

The real create_app behind harden(), registered as the hosted deployment (provider.install),
with the R2.1 case gate, the hosted guard and the HR-entered key (D-106). Anthropic is a mock
transport and the CLM backend is the hosted tests' mock, which enforces per-team case access.
No network, no paid call, no real key: every key here is a sentinel.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import anthropic_runtime, hosted_insights, model_admin
from ai_assistant.anthropic_profiles import BALANCED, FAST
from ai_assistant.anthropic_runtime import HOSTED_ANSWERED
from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.main import FALLBACK_NOTICE, create_app
from assistant_eval.qualification import run_job
from assistant_hosting import harden as harden_module
from assistant_hosting import profile, provider
from assistant_hosting.guard import ADMIN_PREFIX, CLAUDE_CHANGES
from assistant_hosting.harden import harden
from tests import test_hosting
from tests.test_claude_runtime import WORKSPACE, Claude
from tests.test_conversational_external import SCRIPT, scripted  # noqa: F401 (fixture)
from tests.test_hosting import (
    BACKEND,
    CASE_ID,
    ELIGIBLE,
    ORIGIN,
    actor,
    hosted_settings,
    knowledge,
    no_files,
    session,
)
from tests.test_model_management import ThreadRun

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
DEPLOY = ASSISTANT_DIR / "deploy"
EGRESS = DEPLOY / "egress"
KEY = "sk-" + "ant-" + "api03-" + "HostedSessionSentinel" * 3
OPENROUTER_KEY = "sk-" + "or-" + "v1-" + "a" * 40
OTHER_KEY = "sk-" + "ant-" + "api03-" + "HostedSecondSentinel" * 3
CEILING = 2_000_000
PIN = "160.79.104.10"
CLAUDE_ENV = {
    **ELIGIBLE,
    provider.PROVIDER_VARIABLE: "anthropic",
    provider.CEILING_VARIABLE: str(CEILING),
}
CONFIRMATIONS = sorted(anthropic_runtime.OWNER_ATTESTATIONS)
QUESTION = "Why is Garden Business blocked?"
# D-130 (OD-G6): the two case-chat questions. D-142 R4 (Option A): the general, Support and Try
# paths no longer go to Claude, so the run asks no turn on them.
# C11 P-B: the 2 approved manifest questions plus the dashboard insights turn (H-D1).
QUALIFICATION_CALLS = 3
# What the mock Claude writes on a general-chat prompt (no case is open).
GENERAL_REPLY = (
    "Onboarding usually needs the company's registry record and documents that show its "
    "registered address and its ownership."
)


def _allowed_lines(text: str) -> list[str]:
    return text.split("ALLOWED LINES:\n", 1)[1].splitlines()


@pytest.fixture
def hosted_replies(monkeypatch: pytest.MonkeyPatch, scripted: list[str]) -> list[str]:  # noqa: F811
    """The mock Claude also answers the D-130 prompts: Support's exact-line prompt with its
    first allowed line, the general chat with GENERAL_REPLY; anything else as before."""

    from tests import test_claude_runtime

    earlier = test_claude_runtime._lines

    def lines(body: dict[str, Any]) -> str:
        system = [block["text"] for block in body.get("system", [])]
        # C11 P-B: the dashboard insights prompt (enabled in the code, asked by every hosted
        # qualification as H-D1) gets a well-formed reply copying the first finding's number.
        for text in system:
            if text.startswith(hosted_insights.FINDINGS_HEADER):
                data = json.loads(text[len(hosted_insights.FINDINGS_HEADER) :])
                first = (data.get("findings") or [{}])[0]
                numbers = [str(v) for v in first.get("facts", {}).values() if isinstance(v, int)]
                note = "There are " + (numbers[0] if numbers else "no") + " open cases to watch."
                reply = {
                    "summary": "The cases are moving.",
                    "notes": [{"id": first.get("id", "F1"), "text": note}],
                    "actions": [],
                }
                return json.dumps(reply) + "\n"
        for text in system:
            if text.startswith("SOURCES (titles of the retrieved approved entries):"):
                return _allowed_lines(text)[0] + "\n"
        if any(text.startswith("NO CASE IS OPEN.") for text in system):
            return GENERAL_REPLY + "\n"
        return earlier(body)

    monkeypatch.setattr(test_claude_runtime, "_lines", lines)
    return scripted


def pinned(host: str) -> list[str]:
    assert host == provider.PROVIDER_HOST
    return [PIN]


def post_headers(token: str) -> dict[str, str]:
    return session(token, origin=ORIGIN)


class HostedClm(test_hosting.Clm):
    """The hosted mock backend, plus Support and an HR session that can end."""

    def __init__(self) -> None:
        super().__init__()
        self.ended: set[str] = set()

    def handler(self, request: httpx.Request) -> httpx.Response:
        token = request.headers.get("cookie", "").removeprefix("clm_session=")
        if token in self.ended:
            self.requests.append(request)
            return httpx.Response(401, json={"detail": "session ended"})
        if token == "support":
            self.requests.append(request)
            if request.url.path == "/api/auth/me":
                return httpx.Response(
                    200, json=actor("sam-support", "SUPPORT", "", "KNOWLEDGE_REVIEW")
                )
            if request.url.path == "/api/policies":
                return httpx.Response(200, json={"policies": []})
            return httpx.Response(404, json={"detail": "not found"})
        return super().handler(request)


class Hosted:
    """One hosted service in Claude mode, as assistant_hosting.app builds it."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch, clm: HostedClm) -> None:
        monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", "D-122")
        monkeypatch.setattr(model_admin, "SUPERVISE_SECONDS", 0.05)
        settings = hosted_settings(root)
        assert profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned) == []
        assert provider.install(settings, CLAUDE_ENV) is True
        kb = knowledge(settings)
        ingest_guidance(kb)
        transport = httpx.MockTransport(clm.handler)
        app = create_app(settings, clm_transport=transport, knowledge=kb)
        harden(app, settings, environ=CLAUDE_ENV, transport=transport)
        self.settings = settings
        self.clm = clm
        self.claude = Claude()
        selector = app.state.model_selector
        selector.environ = None  # the service's own resolution: the HR session key (D-106)
        selector.transport = self.claude.transport()

        def launch(qualification_id: str) -> ThreadRun:
            return ThreadRun(
                lambda: run_job(
                    qualification_id,
                    selector.settings,
                    environ=selector.environ,
                    transport=selector.transport,
                )
            )

        selector.launch = launch
        # As a restarted process does: the activation restored with this process's transport.
        selector._active = selector._restore()  # noqa: SLF001 - test seam (test_d118_fresh_setup)
        self.selector = selector
        self.client = TestClient(
            app, base_url="http://clm-assistant-proxy:8100", raise_server_exceptions=False
        )

    # --- HR, through the hosted guard ----------------------------------------------------

    def hr(self, method: str, tail: str, body: Any = None) -> httpx.Response:
        headers = session("hr") if method == "GET" else post_headers("hr")
        return self.client.request(method, ADMIN_PREFIX + tail, headers=headers, json=body)

    def setup_claude(self, key: str = KEY) -> dict[str, Any]:
        saved = self.hr("PUT", "/credential/anthropic", {"api_key": key})
        assert saved.status_code == 200, saved.text
        read = self.hr("POST", "/provider/anthropic/workspace-read")
        assert read.status_code == 200 and read.json()["workspace_id"] == WORKSPACE, read.text
        setup = self.hr("GET", "").json()["anthropic_setup"]
        revision = setup["record"]["revision"] if setup["record"] else 0
        enabled = self.hr(
            "PUT",
            "/provider/anthropic",
            {
                "expected_revision": revision,
                "enabled": True,
                "workspace_id": WORKSPACE,
                "workspace_limit_micro_usd": 5_000_000,
                "confirmations": CONFIRMATIONS,
            },
        )
        assert enabled.status_code == 200, enabled.text
        return dict(enabled.json())

    def qualify_and_activate(self, profile_id: str = BALANCED.profile_id) -> dict[str, Any]:
        test = self.hr("POST", f"/{profile_id}/connection-test")
        assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text
        started = self.hr(
            "POST",
            f"/{profile_id}/qualifications",
            {"confirm_paid_calls": QUALIFICATION_CALLS},
        )
        assert started.status_code == 202, started.text
        result = self.wait(started.json()["qualification_id"])
        assert result["status"] == "passed", result
        revision = self.hr("GET", "").json()["revision"]
        applied = self.hr(
            "POST",
            f"/{profile_id}/activate",
            {"expected_revision": revision, "acknowledge_quality_unscored": True},
        )
        assert applied.status_code == 200, applied.text
        return result

    def wait(self, qualification_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            item = self.hr("GET", f"/qualifications/{qualification_id}").json()
            if item["status"] != "running":
                return dict(item)
            time.sleep(0.2)
        raise AssertionError("qualification did not finish")

    # --- an RM ---------------------------------------------------------------------------

    def ask(
        self, message: str = QUESTION, token: str = "rm-a", case_id: UUID = CASE_ID
    ) -> tuple[int, list[dict[str, Any]]]:
        reply = self.client.post(
            f"/assistant/cases/{case_id}/chat/stream",
            headers=post_headers(token),
            json={"message": message},
        )
        if reply.status_code != 200:
            return reply.status_code, [reply.json()]
        return 200, [json.loads(line) for line in reply.text.splitlines() if line.strip()]


def done(events: list[dict[str, Any]]) -> dict[str, Any]:
    return next(event for event in events if event.get("type") == "done")


@pytest.fixture
def hosted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hosted_replies: list[str]) -> Hosted:
    return Hosted(tmp_path, monkeypatch, HostedClm())


@pytest.fixture
def live(hosted: Hosted) -> Hosted:
    hosted.setup_claude()
    hosted.qualify_and_activate()
    return hosted


# --- configuration: off by default, fail closed when named ------------------------------------


def test_without_the_mode_stage_a_is_unchanged(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    assert profile.refusals(settings, ELIGIBLE, env_files=no_files(), resolve=pinned) == []
    assert provider.install(settings, ELIGIBLE) is False
    assert anthropic_runtime.hosted_deployment() is None
    assert anthropic_runtime.lifetime_ceiling() == anthropic_runtime.LIFETIME_CEILING_MICRO_USD
    assert not anthropic_runtime.local_deployment(settings)


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({provider.PROVIDER_VARIABLE: "open-router"}, "PROVIDER_MODE_INVALID"),
        ({provider.PROVIDER_VARIABLE: "Anthropic"}, "PROVIDER_MODE_INVALID"),
        ({provider.CEILING_VARIABLE: ""}, "HOSTED_CEILING_REQUIRED"),
        ({provider.CEILING_VARIABLE: "0"}, "HOSTED_CEILING_REQUIRED"),
        ({provider.CEILING_VARIABLE: "30000001"}, "HOSTED_CEILING_REQUIRED"),
        ({provider.CEILING_VARIABLE: "1.5"}, "HOSTED_CEILING_REQUIRED"),
        ({provider.CEILING_VARIABLE: "-5"}, "HOSTED_CEILING_REQUIRED"),
        ({"AI_ASSISTANT_ANTHROPIC_API_KEY": KEY}, "PROVIDER_KEY_REFUSED"),
        ({"OPENROUTER_API_KEY": OPENROUTER_KEY}, "PROVIDER_KEY_REFUSED"),
        ({"HTTPS_PROXY": "http://proxy.invalid:3128"}, "PROXY_SETTING_REFUSED"),
    ],
)
def test_a_wrong_or_unsafe_claude_mode_stops_the_service(
    tmp_path: Path, change: dict[str, str], code: str
) -> None:
    env = {**CLAUDE_ENV, **change}
    found = profile.refusals(hosted_settings(tmp_path), env, env_files=no_files(), resolve=pinned)
    assert code in found
    assert KEY not in " ".join(found)


def test_a_ceiling_without_the_mode_is_refused(tmp_path: Path) -> None:
    env = {**ELIGIBLE, provider.CEILING_VARIABLE: "1000"}
    found = profile.refusals(hosted_settings(tmp_path), env, env_files=no_files(), resolve=pinned)
    assert found == ["PROVIDER_SETTING_WITHOUT_MODE"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"anthropic_decision": "D-099"},
        {"anthropic_owner_attests": "dedicated_workspace"},
        {"anthropic_workspace_id": "wrkspc_1"},
        {"anthropic_workspace_limit_micro_usd": 1},
        {"remote_inference_decision": "D-091"},
        {"local_api_test_decision": "D-094"},
        {"synthetic_dev_decision": "D-095"},
        {"openrouter_endpoint": "openai/gpt-oss-120b"},
    ],
)
def test_the_mode_never_accepts_a_decision_or_attestation_setting(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    settings = hosted_settings(tmp_path, **overrides)
    found = profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned)
    assert "REMOTE_SETTING_REFUSED" in found


def test_the_mode_needs_exactly_one_origin(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path, allowed_origins=[ORIGIN, "https://other.example.test"])
    found = profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned)
    assert found == ["ONE_ORIGIN_REQUIRED"]


@pytest.mark.parametrize(
    "addresses",
    [
        [],  # no hosts-file pin and no DNS: nothing resolves
        ["104.18.32.47"],  # a CDN address, not Anthropic's
        ["160.79.106.1"],  # just outside 160.79.104.0/23
        ["2607:6bc0::10"],  # Anthropic's IPv6, but the uplink is IPv4 only
        [PIN, "1.1.1.1"],  # one good and one other address
        ["not-an-address"],
    ],
)
def test_the_provider_name_must_resolve_only_to_a_pinned_anthropic_ipv4(
    tmp_path: Path, addresses: list[str]
) -> None:
    found = profile.refusals(
        hosted_settings(tmp_path), CLAUDE_ENV, env_files=no_files(), resolve=lambda _: addresses
    )
    assert found == ["PROVIDER_PIN_REQUIRED"]


@pytest.mark.parametrize("address", ["160.79.104.10", "160.79.105.255", "153.61.227.1"])
def test_addresses_inside_the_published_ranges_are_accepted(address: str) -> None:
    assert provider.pinned([address])


# --- the runtime registration -------------------------------------------------------------


@pytest.mark.parametrize(
    ("origin", "ceiling"),
    [
        ("http://clm.example.test", CEILING),
        ("https://127.0.0.1", CEILING),
        ("https://clm.example.test/app", CEILING),
        ("https://clm.example.test/", CEILING),
        ("https://", CEILING),
        (ORIGIN, 0),
        (ORIGIN, anthropic_runtime.LIFETIME_CEILING_MICRO_USD + 1),
    ],
)
def test_registration_refuses_anything_but_one_https_origin_and_a_bounded_ceiling(
    origin: str, ceiling: int
) -> None:
    with pytest.raises(ValueError):
        anthropic_runtime.register_hosted_deployment(origin, ceiling)
    assert anthropic_runtime.hosted_deployment() is None


def test_registration_happens_once_with_the_same_values_only() -> None:
    anthropic_runtime.register_hosted_deployment(ORIGIN, CEILING)
    anthropic_runtime.register_hosted_deployment(ORIGIN, CEILING)  # repeatable
    for other in (("https://other.example.test", CEILING), (ORIGIN, CEILING + 1)):
        with pytest.raises(ValueError):
            anthropic_runtime.register_hosted_deployment(*other)
    assert anthropic_runtime.hosted_deployment() == (ORIGIN, CEILING)
    assert anthropic_runtime.lifetime_ceiling() == CEILING


def test_the_hosted_deployment_is_the_one_origin_and_never_loopback(tmp_path: Path) -> None:
    anthropic_runtime.register_hosted_deployment(ORIGIN, CEILING)
    assert anthropic_runtime.local_deployment(hosted_settings(tmp_path))
    for overrides in (
        {"allowed_origins": ["https://other.example.test"]},
        {"allowed_origins": [ORIGIN, "https://other.example.test"]},
        {"clm_backend_url": "http://127.0.0.1:8000"},
        {"clm_backend_url": "http://localhost:8000"},
        {"llm_enabled": False},
    ):
        assert not anthropic_runtime.local_deployment(hosted_settings(tmp_path, **overrides))


def test_a_development_machine_is_unchanged_when_nothing_is_registered(tmp_path: Path) -> None:
    local = hosted_settings(
        tmp_path, clm_backend_url="http://127.0.0.1:8000", allowed_origins=["http://127.0.0.1:5173"]
    )
    assert anthropic_runtime.local_deployment(local)
    assert not anthropic_runtime.local_deployment(hosted_settings(tmp_path))


def test_harden_refuses_a_half_configured_mode(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    transport = httpx.MockTransport(HostedClm().handler)
    app = create_app(settings, clm_transport=transport, knowledge=knowledge(settings))
    with pytest.raises(ValueError):  # the mode named, the runtime not registered
        harden(app, settings, environ=CLAUDE_ENV, transport=transport)
    anthropic_runtime.register_hosted_deployment(ORIGIN, CEILING + 1)
    with pytest.raises(ValueError):  # registered with another ceiling
        harden(app, settings, environ=CLAUDE_ENV, transport=transport)
    with pytest.raises(ValueError):  # registered, the mode not named
        harden(app, settings, environ=ELIGIBLE, transport=transport)


def test_the_entry_point_registers_before_the_service_is_imported() -> None:
    source = (ASSISTANT_DIR / "assistant_hosting" / "app.py").read_text(encoding="utf-8")
    assert source.index("provider.install(settings)") < source.index("from ai_assistant.main")
    assert "provider" in harden_module.__dict__


# --- the guard ----------------------------------------------------------------------------


def test_every_claude_route_the_guard_allows_is_a_real_route(hosted: Hosted) -> None:
    app: Any = hosted.client.app
    routes = {
        (method.upper(), re.sub(r"\{[^}]+\}", "{x}", path[len(ADMIN_PREFIX) :]))
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(ADMIN_PREFIX + "/")
        for method in operations
    }
    for verb, shape in CLAUDE_CHANGES:
        if "(?:medium|low)" in shape.pattern:
            for profile_id in (BALANCED.profile_id, FAST.profile_id):
                assert re.fullmatch(shape, f"/{profile_id}/qualifications")
            assert (verb, "/{x}/qualifications") in routes
            continue
        assert (verb, shape.pattern.replace("[^/]+", "{x}")) in routes, shape.pattern


@pytest.mark.parametrize(
    ("method", "tail"),
    [
        ("PUT", "/credential"),
        ("DELETE", "/credential"),
        ("PUT", "/budget/controls"),
        ("PUT", "/budget/lifetime-cap"),
        ("POST", "/budget/provider-refresh"),
        ("POST", "/openrouter_gpt_oss_120b/qualifications"),
        ("POST", "/lmstudio_qwen3_8b/qualifications"),
        ("POST", "/budget/claude/reconciliation/preview"),
        ("POST", "/budget/claude/reconciliation/apply"),
        ("POST", "/a-route-added-later"),
    ],
)
def test_openrouter_and_unreviewed_changes_stay_refused_in_the_claude_mode(
    hosted: Hosted, method: str, tail: str
) -> None:
    secret = "sk-or-v1-" + "c" * 40
    response = hosted.client.request(
        method, ADMIN_PREFIX + tail, headers=post_headers("hr"), json={"api_key": secret}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "HOSTED_REMOTE_DISABLED"
    assert secret not in hosted.hr("GET", "/audit").text


def test_an_rm_cannot_enter_a_key_or_enable_claude(hosted: Hosted) -> None:
    for method, tail, body in (
        ("PUT", "/credential/anthropic", {"api_key": KEY}),
        ("PUT", "/provider/anthropic", {"expected_revision": 0, "enabled": True}),
        ("POST", f"/{BALANCED.profile_id}/qualifications", {"confirm_paid_calls": 2}),
    ):
        response = hosted.client.request(
            method, ADMIN_PREFIX + tail, headers=post_headers("rm-a"), json=body
        )
        assert response.status_code == 403, (tail, response.text)
    assert hosted.claude.requests == []


def test_a_claude_change_from_another_origin_is_refused_before_the_service(
    hosted: Hosted,
) -> None:
    response = hosted.client.put(
        ADMIN_PREFIX + "/credential/anthropic",
        headers=session("hr", origin="https://evil.example.test"),
        json={"api_key": KEY},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ORIGIN_NOT_ALLOWED"


# --- the whole journey: HR sets up, qualifies and activates; the RM gets Claude's answer ----


def test_hr_sets_up_claude_and_an_rm_gets_a_streamed_claude_answer(live: Hosted) -> None:
    hosted = live
    # The two approved case-chat questions and one turn per hosted chat path (D-130).
    assert hosted.claude.posts == QUALIFICATION_CALLS
    overview = hosted.hr("GET", "").json()
    assert overview["active"]["profile_id"] == BALANCED.profile_id
    status, events = hosted.ask()
    assert status == 200
    texts = [event for event in events if event["type"] == "text"]
    answer = done(events)
    assert texts, "the answer streamed in parts"
    assert answer["answered_by"] == "model" and answer["model"] == "claude-sonnet-5-5"
    assert answer["notice"].startswith(HOSTED_ANSWERED)
    assert SCRIPT[QUESTION].split(",")[0] in answer["answer"]
    assert answer["answer_id"] and answer["conversation_id"]
    assert hosted.claude.posts == QUALIFICATION_CALLS + 1
    # Every request carried the HR key and named nothing but Sonnet 5.5.
    posts = [r for r in hosted.claude.requests if r.method == "POST"]
    assert all(r.headers["x-api-key"] == KEY for r in posts)
    assert {body["model"] for body in hosted.claude.messages} == {"claude-sonnet-5-5"}
    # The key never shows in what HR or the RM can read.
    for text in (
        hosted.hr("GET", "").text,
        hosted.hr("GET", "/audit").text,
        hosted.hr("GET", "/budget").text,
        json.dumps(events),
    ):
        assert KEY not in text


def test_the_requests_fit_sonnet_5_5_for_both_configurations(hosted: Hosted) -> None:
    hosted.setup_claude()
    hosted.qualify_and_activate(BALANCED.profile_id)
    hosted.qualify_and_activate(FAST.profile_id)
    hosted.ask()
    assert len(hosted.claude.messages) == 2 * QUALIFICATION_CALLS + 1
    for body in hosted.claude.messages:
        # Sonnet 5.5: no sampling parameters, no tools or forced tool choice, no prefill.
        assert not {"temperature", "top_p", "top_k", "tools", "tool_choice"} & set(body)
        assert body["model"] == "claude-sonnet-5-5" and body["stream"] is True
        assert body["messages"][-1]["role"] == "user"
        assert set(body) <= {
            "model",
            "max_tokens",
            "thinking",
            "output_config",
            "system",
            "messages",
            "stream",
        }
        effort, thinking = body["output_config"]["effort"], body["thinking"]
        # Thinking cannot be "disabled" on Sonnet 5.5; Fast uses between_tools, alone and at
        # an effort of high or below. Balanced is adaptive.
        assert thinking in ({"type": "adaptive"}, {"type": "between_tools"})
        assert thinking == ({"type": "between_tools"} if effort == "low" else {"type": "adaptive"})
        assert effort in ("low", "medium")
    versions = {r.headers["anthropic-version"] for r in hosted.claude.requests}
    assert versions == {"2026-10-21"}


def test_the_conversation_is_kept_rated_and_listed_for_its_owner_only(live: Hosted) -> None:
    hosted = live
    _, events = hosted.ask()
    answer = done(events)
    conversation = answer["conversation_id"]
    mine = hosted.client.get("/assistant/conversations", headers=session("rm-a"))
    assert mine.status_code == 200 and conversation in mine.text
    one = hosted.client.get(f"/assistant/conversations/{conversation}", headers=session("rm-a"))
    assert one.status_code == 200 and QUESTION in one.text
    other = hosted.client.get(f"/assistant/conversations/{conversation}", headers=session("rm-b"))
    assert other.status_code == 404
    rated = hosted.client.post(
        f"/assistant/cases/{CASE_ID}/feedback",
        headers=post_headers("rm-a"),
        json={"answer_id": answer["answer_id"], "helpful": True},
    )
    assert rated.status_code in (200, 201), rated.text
    # A follow-up in the same chat is answered; D-142 R3 (OD-3): the earlier turns are kept
    # for the conversation record but never sent to the external model.
    follow = hosted.client.post(
        f"/assistant/cases/{CASE_ID}/chat/stream",
        headers=post_headers("rm-a"),
        json={
            # D-142 R4 (complete-question admission): a supported BLOCKERS question.
            "message": "What should I do next?",
            "history": [
                {"role": "user", "content": QUESTION},
                {"role": "assistant", "content": answer["answer"]},
            ],
            "earlier_answer_ids": [answer["answer_id"]],
            "conversation_id": conversation,
        },
    )
    assert follow.status_code == 200
    final = done([json.loads(line) for line in follow.text.splitlines() if line.strip()])
    assert final["answered_by"] == "model" and final["conversation_id"] == conversation
    sent = hosted.claude.messages[-1]["messages"]
    assert [m["role"] for m in sent] == ["user"]
    # D-142 R4 (R3-1): the follow-up's intent goes as its canonical question, never as typed.
    assert sent[0]["content"] == "Why is this case blocked, and what should be done next?"


# --- failures are labelled and never claimed as Claude's ------------------------------------


@pytest.mark.parametrize(
    "fault",
    [
        {"status": 500},
        {"status": 429},
        {"status": 529},
        {"reply_model": "claude-opus-5-5"},  # another model answered: never shown
        {"workspace": "wrkspc_SomeoneElse01"},  # another workspace paid: never shown
    ],
)
def test_a_provider_failure_gives_the_labelled_case_data_answer(
    live: Hosted, fault: dict[str, Any]
) -> None:
    hosted = live
    for name, value in fault.items():
        setattr(hosted.claude, name, value)
    status, events = hosted.ask()
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data" and answer["model"] is None
    assert HOSTED_ANSWERED not in (answer["notice"] or "")
    assert "Claude" not in (answer["notice"] or "")
    assert (answer["notice"] or "").startswith(FALLBACK_NOTICE.split(".")[0])
    assert (
        hosted.client.get(ADMIN_PREFIX, headers=session("hr")).json()["active"]["profile_id"]
        == BALANCED.profile_id
    )  # never switched to another model


def test_a_stream_that_breaks_off_keeps_only_checked_claude_text_and_says_so(
    live: Hosted,
) -> None:
    # Sentences that passed their checks before the break are Claude's own words: shown as
    # Claude's, marked cut short (D-115). Nothing else is added in their place.
    from ai_assistant.main import CUT_SHORT_NOTICE

    hosted = live
    hosted.claude.finished = False
    status, events = hosted.ask()
    answer = done(events)
    assert status == 200 and answer["answered_by"] == "model"
    assert answer["notice"].startswith(HOSTED_ANSWERED) and CUT_SHORT_NOTICE in answer["notice"]


def test_hr_signing_out_drops_the_key_and_answers_fall_back(live: Hosted) -> None:
    hosted = live
    posts = hosted.claude.posts
    hosted.clm.ended.add("hr")
    status, events = hosted.ask()
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert hosted.claude.posts == posts  # nothing was sent without a live HR session


def test_a_restart_keeps_claude_active_but_needs_the_key_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: list[str],
) -> None:
    from ai_assistant import key_sources

    first = Hosted(tmp_path, monkeypatch, HostedClm())
    first.setup_claude()
    first.qualify_and_activate()
    assert done(first.ask()[1])["answered_by"] == "model"
    first.client.close()
    # A new process: the key was only in memory; the stores on the volume remain.
    monkeypatch.setattr(key_sources, "ANTHROPIC_STORE", key_sources.HrCredential())
    with anthropic_runtime._last_lock:
        anthropic_runtime._last.clear()
    second = Hosted(tmp_path, monkeypatch, HostedClm())
    assert second.hr("GET", "").json()["active"]["profile_id"] == BALANCED.profile_id
    assert done(second.ask()[1])["answered_by"] == "case_data"
    assert second.claude.posts == 0
    assert second.hr("PUT", "/credential/anthropic", {"api_key": OTHER_KEY}).status_code == 200
    assert second.hr("POST", f"/{BALANCED.profile_id}/connection-test").json()["outcome"] == (
        "passed"
    )
    again = done(second.ask()[1])
    assert again["answered_by"] == "model" and again["notice"].startswith(HOSTED_ANSWERED)


# --- access and R2.1 eligibility are unchanged ------------------------------------------------


def test_another_team_gets_the_safe_404_and_nothing_is_sent(live: Hosted) -> None:
    hosted = live
    posts = hosted.claude.posts
    status, body = hosted.ask(token="rm-b")
    assert status == 404
    assert hosted.claude.posts == posts


def test_a_case_outside_the_approved_list_is_refused_and_nothing_is_sent(live: Hosted) -> None:
    hosted = live
    posts = hosted.claude.posts
    status, body = hosted.ask(case_id=uuid4())
    assert status in (403, 404)
    assert hosted.claude.posts == posts


def test_without_a_session_nothing_reaches_the_service(live: Hosted) -> None:
    hosted = live
    reply = hosted.client.post(
        f"/assistant/cases/{CASE_ID}/chat/stream", headers={"origin": ORIGIN}, json={"message": "x"}
    )
    assert reply.status_code == 401


# --- without the D-130 decision the other chats stay without Claude (D-115, D-105) -------------


def test_general_and_support_chats_stay_without_claude_and_say_so(
    live: Hosted, monkeypatch: pytest.MonkeyPatch
) -> None:
    hosted = live
    monkeypatch.setattr("ai_assistant.config.HOSTED_CHAT_DECISION", None)
    posts = hosted.claude.posts
    opened = hosted.client.post("/assistant/contexts", headers=post_headers("rm-a"), json={})
    assert opened.status_code == 200, opened.text
    general = hosted.client.post(
        "/assistant/general/chat/stream",
        headers=post_headers("rm-a"),
        json={"message": "What is a UBO check?", "context_id": opened.json()["context_id"]},
    )
    assert general.status_code == 200, general.text
    reply = done([json.loads(line) for line in general.text.splitlines() if line.strip()])
    assert reply["answered_by"] == "case_data" and reply["model"] is None
    support = hosted.client.post(
        "/assistant/support/chat",
        headers=post_headers("support"),
        json={"message": "What is the UBO threshold?"},
    )
    assert support.status_code == 200, support.text
    assert support.json()["answered_by"] == "case_data"
    assert hosted.claude.posts == posts


# --- money: the hosted ceiling bounds the hosted ledger (D-102) --------------------------------


def test_the_hosted_ledger_opens_at_the_hosted_ceiling_and_cannot_go_above_it(
    hosted: Hosted,
) -> None:
    hosted.setup_claude()
    ledger = anthropic_runtime.open_own(anthropic_runtime.ledger_file(hosted.settings))
    status = ledger.status()
    assert status.cap == CEILING  # min(hosted ceiling, workspace limit 5,000,000)
    ledger_path = Path(anthropic_runtime.ledger_file(hosted.settings))
    assert ledger_path.is_relative_to(hosted.settings.data_dir)  # on the volume
    budget = hosted.hr("GET", "/budget").json()
    assert budget["claude"]["lifetime_ceiling_micro_usd"] == CEILING
    raised = hosted.hr(
        "PUT",
        "/budget/claude/lifetime-cap",
        {"cap_micro_usd": CEILING + 1, "expected_cap_micro_usd": CEILING},
    )
    assert raised.status_code in (400, 409), raised.text
    assert ledger.status().cap == CEILING


def test_the_qualification_process_registers_itself_in_the_claude_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "qualify_model", ASSISTANT_DIR / "scripts" / "qualify_model.py"
    )
    assert spec is not None and spec.loader is not None
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    # Off: a development checkout is unchanged.
    for name in (provider.PROVIDER_VARIABLE, provider.CEILING_VARIABLE):
        monkeypatch.delenv(name, raising=False)
    assert script.hosted_ready() is True and anthropic_runtime.hosted_deployment() is None
    # On, with the service's own settings: registered after the same refusals.
    for name, value in {**CLAUDE_ENV}.items():
        monkeypatch.setenv(name, value)
    values = {
        "AI_ASSISTANT_DATA_DIR": str(tmp_path),
        "AI_ASSISTANT_CLM_BACKEND_URL": BACKEND,
        "AI_ASSISTANT_ALLOWED_ORIGINS": json.dumps([ORIGIN]),
        "AI_ASSISTANT_LLM_ENABLED": "true",
        "AI_ASSISTANT_LLM_BASE_URL": profile.NO_MODEL_URL,
        "AI_ASSISTANT_LLM_MODEL": profile.NO_MODEL_NAME,
        "AI_ASSISTANT_LLM_WARM_UP": "false",
        "AI_ASSISTANT_MODEL_PROFILES_FILE": str(DEPLOY / "model_profiles.hosted.json"),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(provider, "system_resolver", pinned)
    monkeypatch.chdir(tmp_path)
    assert script.hosted_ready() is True
    assert anthropic_runtime.hosted_deployment() == (ORIGIN, CEILING)
    # A refused configuration stops the run before anything is called.
    monkeypatch.setattr(anthropic_runtime, "_hosted", None)
    monkeypatch.setenv("AI_ASSISTANT_ANTHROPIC_API_KEY", KEY)
    assert script.hosted_ready() is False
    assert anthropic_runtime.hosted_deployment() is None


# --- deployment files ------------------------------------------------------------------------


def _vars() -> dict[str, str]:
    lines = (EGRESS / "clm_r22.vars").read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))


def test_the_image_carries_the_qualification_harness() -> None:
    dockerfile = (DEPLOY / "assistant.Dockerfile").read_text(encoding="utf-8")
    ignore = (DEPLOY / "assistant.Dockerfile.dockerignore").read_text(encoding="utf-8")
    assert "COPY apps/assistant/assistant_eval assistant_eval" in dockerfile
    assert "COPY apps/assistant/scripts/qualify_model.py scripts/qualify_model.py" in dockerfile
    assert "!apps/assistant/assistant_eval/*.py" in ignore
    assert "!apps/assistant/scripts/qualify_model.py" in ignore
    # The harness's Phase B questions run on the synthetic Garden fixtures (variants.py).
    from assistant_eval import variants

    needed = {name for pair in variants.BASES.values() for name in pair if name}
    needed |= {variants.ACTOR}
    for name in needed:
        assert f"apps/assistant/tests/fixtures/{name}" in dockerfile, name
        assert f"!apps/assistant/tests/fixtures/{name}" in ignore, name
    pdf = f"apps/backend/tests/fixtures/uat/{variants.VERIFIED_GARDEN_DOCUMENT}"
    assert f"COPY {pdf} /opt/backend/tests/fixtures/uat/" in dockerfile and f"!{pdf}" in ignore
    assert model_admin.QUALIFY_SCRIPT.relative_to(ASSISTANT_DIR).as_posix() == (
        "scripts/qualify_model.py"
    )


def test_the_provider_overlay_holds_no_secret_and_has_no_fallback_values() -> None:
    text = (DEPLOY / "compose.assistant-provider.yml").read_text(encoding="utf-8")
    assert "ASSISTANT_HOSTING_PROVIDER: anthropic" in text
    assert "${ASSISTANT_CLAUDE_LIFETIME_CAP_MICRO_USD:?" in text
    assert '"api.anthropic.com:${ASSISTANT_ANTHROPIC_PINNED_V4:?' in text
    assert ":-" not in text  # no default for any value
    for forbidden in ("API_KEY", "sk-ant", "DECISION", "ATTESTS", "WORKSPACE", "PROXY"):
        assert forbidden not in text
    assert "dns: [192.0.2.53]" in text  # TEST-NET-1, dropped by the host table
    assert "enable_ipv6: false" in text
    assert "com.docker.network.bridge.name: clm-as-up" in text
    assert "ipv4_address: 172.30.243.2" in text
    assert "internal:" not in text.split("networks:\n  assistant-uplink:")[1]


def test_the_host_table_allows_only_the_assistant_to_the_pin_on_443() -> None:
    values = _vars()
    table = (EGRESS / "clm_r22.nft").read_text(encoding="utf-8")
    assert provider.pinned([values["ANTHROPIC_DST_V4"]])
    assert f"elements = {{ {values['ANTHROPIC_DST_V4']} }}" in table
    rules = [line.strip() for line in table.splitlines() if line.strip().startswith(("iif", "oif"))]
    accepts = [rule for rule in rules if rule.endswith("accept")]
    assert accepts == [
        'oifname "clm-as-up" ct state established,related counter accept',
        f'iifname "clm-as-up" ip saddr {values["ASSISTANT_UPLINK_IP"]} ip daddr '
        f'@anthropic_dst_v4 oifname "{values["UPLINK_IF"]}" tcp dport 443 counter accept',
        'iifname "clm-as-up" ct state established,related counter accept',
    ]
    # Each chain ends in a drop for the bridge; IPv6 and invalid packets are dropped first.
    assert rules[-1] == 'iifname "clm-as-up" counter drop'
    assert 'iifname "clm-as-up" meta nfproto ipv6 counter drop' in rules
    code = " ".join(line for line in table.splitlines() if not line.lstrip().startswith("#"))
    assert "flush" not in code and "clm_r3" not in code
    assert table.count("table inet clm_r22") == 3
    assert values["UPLINK_BRIDGE"] == "clm-as-up"


def test_the_watcher_and_units_name_only_the_assistant_table() -> None:
    watcher = (EGRESS / "clm_r22_watch.py").read_text(encoding="utf-8")
    assert 'TABLE = ("inet", "clm_r22")' in watcher
    firewall = (EGRESS / "clm-r22-assistant-firewall.service").read_text(encoding="utf-8")
    assert (
        "Before=docker.service" in firewall
        and "nftables.service" not in firewall.split("[Service]")[1]
    )
    assert "ExecStart=/usr/sbin/nft -f /etc/clm/r22/clm_r22.nft" in firewall
    watch = (EGRESS / "clm-r22-firewall-watch.service").read_text(encoding="utf-8")
    assert "--containers clm-staging-assistant" in watch
    stop = (EGRESS / "clm_r22_stop_assistant.sh").read_text(encoding="utf-8")
    assert "docker stop --time 0 clm-staging-assistant" in stop


# D-139: these tests treat the fixture case as verified synthetic (the seam in conftest);
# test_hosted_case_policy.py runs the real provenance check.
pytestmark = pytest.mark.usefixtures("hosted_case_eligible")
