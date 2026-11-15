"""D-134 (PROPOSED, NOT ACTIVE): GPT-OSS 120B through OpenRouter as a second hosted model.

The real create_app behind harden(), with the OpenRouter provider mode registered as
assistant_hosting.app would register it. The mode does not exist in the shipped code (the
owner's decision is None), so every test that needs it sets the decision in the test process
only, and stands in for the D-138 A1 egress check: the container's route to the proxy is a
stub that answers from inside the internal network, and openrouter.ai does not resolve.
OpenRouter and Anthropic are mock transports, the CLM backend is the hosted tests' mock. No
network, no paid call, no real key: every key here is a sentinel.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from ai_assistant import (
    anthropic_runtime,
    budget,
    model_admin,
    openrouter,
    remote_test,
    request_rate,
)
from ai_assistant import config as assistant_config
from ai_assistant.anthropic_profiles import BALANCED
from ai_assistant.budget import GPT_OSS_DAILY_CEILING_MICRO_USD, BudgetLedger
from ai_assistant.knowledge.ingest import ingest_guidance
from ai_assistant.main import FALLBACK_NOTICE, create_app
from ai_assistant.model_admin_store import (
    CLAUDE_DAILY_CAP_RANGE,
    SpendingControls,
    apply_claude_controls,
    apply_controls,
)
from ai_assistant.model_profiles import OPENROUTER_MODEL_ID, OPENROUTER_PROFILE_ID
from ai_assistant.remote_test import HOSTED_ANSWERED
from assistant_eval.qualification import run_job
from assistant_hosting import profile, provider
from assistant_hosting.guard import ADMIN_PREFIX, CLAUDE_CHANGES, OPENROUTER_CHANGES
from assistant_hosting.harden import harden
from tests import conftest, test_hosting
from tests.test_claude_runtime import Claude
from tests.test_conversational_external import SCRIPT, scripted  # noqa: F401 (fixture)
from tests.test_hosted_claude import CEILING as CLAUDE_CEILING
from tests.test_hosted_claude import KEY as CLAUDE_KEY
from tests.test_hosted_claude import PIN as CLAUDE_PIN
from tests.test_hosted_claude import (  # noqa: F401 (hosted_replies is a fixture)
    QUESTION,
    Hosted,
    HostedClm,
    done,
    hosted_replies,
    post_headers,
)
from tests.test_hosting import (
    BACKEND,
    ELIGIBLE,
    ORIGIN,
    actor,
    hosted_settings,
    knowledge,
    no_files,
    session,
)
from tests.test_model_management import ThreadRun
from tests.test_remote_test import D094, OpenRouter, _settle_verification, listing

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
DEPLOY = ASSISTANT_DIR / "deploy"
OR_KEY = "sk-or-" + "HostedGptOssSentinel" * 2
DAILY = GPT_OSS_DAILY_CEILING_MICRO_USD
# TEST-NET-3 (RFC 5737): a documentation address, never a real provider address.
OR_PIN = "203.0.113.10"
# D-138 A1: the reviewed proxy address, and the assistant's own address on that network.
PROXY = "http://172.30.246.2:4750"
ASSISTANT_CTL = "172.30.246.3"
# The remote profile exactly as the OpenRouter mode needs it named (test_remote_test.D094).
OR_SETTINGS: dict[str, Any] = {
    name: D094[name]
    for name in (
        "local_api_test_decision",
        "remote_inference_decision",
        "remote_live_decision",
        "openrouter_endpoint",
        "llm_reasoning_effort",
        "llm_reasoning_allowance_tokens",
        "local_api_test_owner_attests",
    )
}
GPTOSS_ENV = {
    **ELIGIBLE,
    provider.PROVIDER_VARIABLE: "openrouter",
    provider.DAILY_CAP_VARIABLE: str(DAILY),
    provider.PROXY_VARIABLE: PROXY,
}
BOTH_ENV = {
    **GPTOSS_ENV,
    provider.PROVIDER_VARIABLE: "anthropic,openrouter",
    provider.CEILING_VARIABLE: str(CLAUDE_CEILING),
}


def resolve(host: str) -> list[str]:
    # openrouter.ai does not resolve inside the container: the proxy is the only way to it.
    return {provider.PROVIDER_HOST: [CLAUDE_PIN], provider.OPENROUTER_HOST: []}[host]


def on_internal_network(address: str, port: int) -> str | None:
    # The kernel reaches the proxy directly from the assistant's own internal address.
    return ASSISTANT_CTL if address == "172.30.246.2" else None


@pytest.fixture
def approved(monkeypatch: pytest.MonkeyPatch) -> None:
    """What a reviewed activation change would add: the decision, and (in place of the host)
    a route to the proxy on the internal network. Test only."""

    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_DECISION", "D-134-TEST-ONLY")
    monkeypatch.setattr(provider, "system_local_source", on_internal_network)


def refusals(tmp_path: Path, env: dict[str, str], **overrides: Any) -> list[str]:
    settings = hosted_settings(tmp_path, **{**OR_SETTINGS, **overrides})
    return profile.refusals(settings, env, env_files=no_files(), resolve=resolve)


class Site(Hosted):
    """One hosted service in the OpenRouter mode (or both modes), built as app.py builds it."""

    def __init__(
        self,
        root: Path,
        monkeypatch: pytest.MonkeyPatch,
        clm: HostedClm,
        env: dict[str, str] = GPTOSS_ENV,
        **overrides: Any,
    ) -> None:
        monkeypatch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", "D-122")
        monkeypatch.setattr(model_admin, "SUPERVISE_SECONDS", 0.05)
        monkeypatch.setattr(remote_test, "fetch_public", listing)
        settings = hosted_settings(root, **{**OR_SETTINGS, **overrides})
        assert profile.refusals(settings, env, env_files=no_files(), resolve=resolve) == []
        assert provider.install(settings, env) is True
        kb = knowledge(settings)
        ingest_guidance(kb)
        transport = httpx.MockTransport(clm.handler)
        app = create_app(settings, clm_transport=transport, knowledge=kb)
        harden(app, settings, environ=env, transport=transport)
        self.settings = settings
        self.clm = clm
        self.claude = Claude()
        self.openrouter = OpenRouter()

        def route(request: httpx.Request) -> httpx.Response:
            if request.url.host == provider.PROVIDER_HOST:
                return self.claude.handler(request)
            assert request.url.host == provider.OPENROUTER_HOST, request.url.host
            return self.openrouter.handler(request)

        selector = app.state.model_selector
        selector.environ = None  # the service's own resolution: the HR session key (D-106)
        selector.transport = httpx.MockTransport(route)
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
        selector._active = selector._restore()  # noqa: SLF001 - as a restarted process does
        self.selector = selector
        self.client = TestClient(
            app, base_url="http://clm-assistant-proxy:8100", raise_server_exceptions=False
        )

    def setup_gptoss(self) -> None:
        saved = self.hr("PUT", "/credential", {"api_key": OR_KEY})
        assert saved.status_code == 200, saved.text
        test = self.hr("POST", f"/{OPENROUTER_PROFILE_ID}/connection-test")
        assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text

    def qualify_gptoss(self) -> dict[str, Any]:
        started = self.hr(
            "POST", f"/{OPENROUTER_PROFILE_ID}/qualifications", {"confirm_paid_calls": 2}
        )
        assert started.status_code == 202, started.text
        result = self.wait(started.json()["qualification_id"])
        assert result["status"] == "passed", result
        return result

    def activate_gptoss(self) -> httpx.Response:
        revision = self.hr("GET", "").json()["revision"]
        return self.hr(
            "POST",
            f"/{OPENROUTER_PROFILE_ID}/activate",
            {"expected_revision": revision, "acknowledge_quality_unscored": True},
        )

    def go_live(self) -> None:
        self.setup_gptoss()
        self.qualify_gptoss()
        applied = self.activate_gptoss()
        assert applied.status_code == 200, applied.text

    def chats(self) -> int:
        return len(self.openrouter.chats)

    def active(self) -> str:
        return str(self.hr("GET", "").json()["active"]["profile_id"])

    def budget(self) -> dict[str, Any]:
        view = self.hr("GET", "/budget")
        assert view.status_code == 200, view.text
        return dict(view.json())

    def controls(self, daily: int, calls: int = 20, **extra: Any) -> httpx.Response:
        revision = self.budget()["controls"]["revision"]
        body = {
            "expected_revision": revision,
            "daily_cap_micro_usd": daily,
            "max_calls": calls,
            **extra,
        }
        return self.hr("PUT", "/budget/controls", body)


@pytest.fixture
def site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved: None,
    scripted: list[str],  # noqa: F811
) -> Site:
    return Site(tmp_path, monkeypatch, HostedClm())


@pytest.fixture
def live(site: Site) -> Site:
    site.go_live()
    return site


@pytest.fixture
def both(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved: None,
    hosted_replies: list[str],  # noqa: F811
) -> Site:
    return Site(tmp_path, monkeypatch, HostedClm(), BOTH_ENV)


# --- the mode does not exist in the shipped code ---------------------------------------------


def test_the_decisions_are_absent_and_no_address_range_pins_openrouter() -> None:
    assert assistant_config.HOSTED_OPENROUTER_DECISION is None
    assert assistant_config.HOSTED_OPENROUTER_TRANSMISSION_DECISION is None or (
        conftest.SHIPPED_OPENROUTER_TRANSMISSION_DECISION is None
    )
    # D-138 A1: the empty pin is gone; the proxy check replaces it (no Cloudflare range).
    assert not hasattr(provider, "OPENROUTER_INBOUND_V4")
    assert provider.known_modes() == ("anthropic",)


@pytest.mark.parametrize("value", ["openrouter", "anthropic,openrouter", "openrouter,anthropic"])
def test_naming_the_openrouter_mode_stops_the_service_by_default(
    tmp_path: Path, value: str
) -> None:
    env = {**BOTH_ENV, provider.PROVIDER_VARIABLE: value}
    found = refusals(tmp_path, env)
    assert "PROVIDER_MODE_INVALID" in found
    # Its settings are remote settings like any other while the mode does not exist.
    assert "REMOTE_SETTING_REFUSED" in found
    with pytest.raises(ValueError):
        provider.install(hosted_settings(tmp_path, **OR_SETTINGS), env)
    assert remote_test.hosted_deployment() is None
    assert anthropic_runtime.hosted_deployment() is None
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY  # standing ceiling


def test_the_runtime_refuses_a_hosted_registration_by_default(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        remote_test.register_hosted_deployment(ORIGIN, DAILY)
    assert remote_test.hosted_deployment() is None
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY  # standing ceiling
    # So a hosted configuration is still not a place GPT-OSS may run.
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    assert remote_test.readiness(settings) == "NOT_DEVELOPMENT_ENVIRONMENT"


@pytest.mark.parametrize("addresses", [[OR_PIN], ["104.18.2.115"], [CLAUDE_PIN], []])
def test_with_the_decision_alone_off_the_internal_network_the_mode_cannot_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, addresses: list[str]
) -> None:
    # A machine with no route to the proxy (as any host off the internal network).
    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_DECISION", "D-134-TEST-ONLY")
    monkeypatch.setattr(provider, "system_local_source", lambda address, port: None)
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    found = profile.refusals(
        settings, GPTOSS_ENV, env_files=no_files(), resolve=lambda _: addresses
    )
    expected = ["OPENROUTER_PROXY_NOT_INTERNAL"]
    if addresses:
        expected.insert(0, "OPENROUTER_DIRECT_PATH_REFUSED")
    assert found == expected


# --- start-up refusals when the mode exists ---------------------------------------------------


def test_a_fully_configured_openrouter_mode_may_start(tmp_path: Path, approved: None) -> None:
    assert refusals(tmp_path, GPTOSS_ENV) == []
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    assert provider.install(settings, GPTOSS_ENV) is True
    assert remote_test.hosted_deployment() == (ORIGIN, DAILY)
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY
    assert remote_test.readiness(settings) is None
    # Only the named mode: Claude is not registered and its ceiling is D-102's own.
    assert anthropic_runtime.hosted_deployment() is None
    assert anthropic_runtime.lifetime_ceiling() == anthropic_runtime.LIFETIME_CEILING_MICRO_USD


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({provider.DAILY_CAP_VARIABLE: ""}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.DAILY_CAP_VARIABLE: "0"}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.DAILY_CAP_VARIABLE: "3000001"}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.DAILY_CAP_VARIABLE: "5000000"}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.DAILY_CAP_VARIABLE: "3.0"}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.DAILY_CAP_VARIABLE: "-1"}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.DAILY_CAP_VARIABLE: "٣000000"}, "HOSTED_DAILY_CAP_REQUIRED"),
        ({provider.PROVIDER_VARIABLE: "OpenRouter"}, "PROVIDER_MODE_INVALID"),
        ({provider.PROVIDER_VARIABLE: "openrouter,openrouter"}, "PROVIDER_MODE_INVALID"),
        ({provider.PROVIDER_VARIABLE: "openrouter,"}, "PROVIDER_MODE_INVALID"),
        ({provider.PROVIDER_VARIABLE: "openrouter anthropic"}, "PROVIDER_MODE_INVALID"),
        ({provider.PROVIDER_VARIABLE: "openrouter,deepinfra"}, "PROVIDER_MODE_INVALID"),
        ({provider.CEILING_VARIABLE: "1000"}, "PROVIDER_SETTING_WITHOUT_MODE"),
        ({"OPENROUTER_API_KEY": OR_KEY}, "PROVIDER_KEY_REFUSED"),
        ({"AI_ASSISTANT_ANTHROPIC_API_KEY": CLAUDE_KEY}, "PROVIDER_KEY_REFUSED"),
        ({"HTTPS_PROXY": "http://proxy.invalid:3128"}, "PROXY_SETTING_REFUSED"),
    ],
)
def test_a_wrong_or_unsafe_openrouter_mode_stops_the_service(
    tmp_path: Path, approved: None, change: dict[str, str], code: str
) -> None:
    found = refusals(tmp_path, {**GPTOSS_ENV, **change})
    assert code in found
    assert OR_KEY not in " ".join(found) and CLAUDE_KEY not in " ".join(found)


@pytest.mark.parametrize(
    "overrides",
    [
        {"local_api_test_decision": ""},
        {"local_api_test_decision": "D-095"},
        {"remote_inference_decision": ""},
        {"remote_live_decision": ""},
        {"remote_live_decision": "D-091"},
        {"openrouter_endpoint": ""},
        {"openrouter_endpoint": "groq"},
        {"openrouter_endpoint": "openai/gpt-oss-120b"},
        {"local_api_test_owner_attests": ""},
        {"local_api_test_owner_attests": "auto_topup_off"},
        {"llm_reasoning_effort": ""},
        {"llm_reasoning_effort": "extreme"},
        {"llm_reasoning_allowance_tokens": 0},
        {"llm_reasoning_allowance_tokens": 3999},
    ],
)
def test_the_mode_needs_the_whole_remote_profile_named_exactly(
    tmp_path: Path, approved: None, overrides: dict[str, Any]
) -> None:
    assert refusals(tmp_path, GPTOSS_ENV, **overrides) == ["OPENROUTER_SETTINGS_REQUIRED"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"anthropic_decision": "D-099"},
        {"anthropic_owner_attests": "dedicated_workspace"},
        {"anthropic_workspace_id": "wrkspc_1"},
        {"anthropic_workspace_limit_micro_usd": 1},
        {"synthetic_dev_decision": "D-095"},
        {"remote_low_reasoning_profile_enabled": True},
    ],
)
def test_the_mode_accepts_no_other_remote_setting(
    tmp_path: Path, approved: None, overrides: dict[str, Any]
) -> None:
    assert "REMOTE_SETTING_REFUSED" in refusals(tmp_path, GPTOSS_ENV, **overrides)


@pytest.mark.parametrize("env", [ELIGIBLE, {**ELIGIBLE, provider.PROVIDER_VARIABLE: "anthropic"}])
def test_the_remote_profile_is_refused_wherever_the_mode_is_not_named(
    tmp_path: Path, approved: None, env: dict[str, str]
) -> None:
    for name, value in OR_SETTINGS.items():
        if name.startswith("llm_"):
            continue  # reasoning settings alone open nothing
        settings = hosted_settings(tmp_path, **{name: value})
        found = profile.refusals(settings, env, env_files=no_files(), resolve=resolve)
        assert "REMOTE_SETTING_REFUSED" in found, name


def test_a_daily_ceiling_without_the_mode_is_refused(tmp_path: Path, approved: None) -> None:
    env = {**ELIGIBLE, provider.DAILY_CAP_VARIABLE: "1000"}
    settings = hosted_settings(tmp_path)
    found = profile.refusals(settings, env, env_files=no_files(), resolve=resolve)
    assert found == ["PROVIDER_SETTING_WITHOUT_MODE"]


def test_the_mode_needs_exactly_one_origin(tmp_path: Path, approved: None) -> None:
    found = refusals(tmp_path, GPTOSS_ENV, allowed_origins=[ORIGIN, "https://other.example.test"])
    assert found == ["ONE_ORIGIN_REQUIRED"]


@pytest.mark.parametrize(
    "addresses",
    [
        [],
        ["104.18.2.115"],  # a CDN address outside the recorded range
        [CLAUDE_PIN],  # Anthropic's range never pins OpenRouter
        ["2001:db8::10"],  # IPv6: the uplink is IPv4 only
        [OR_PIN, "1.1.1.1"],
        ["not-an-address"],
    ],
)
def test_any_direct_path_to_openrouter_stops_the_mode(
    tmp_path: Path, approved: None, addresses: list[str]
) -> None:
    # D-138 A1: whatever openrouter.ai resolves to inside the container (a hosts-file pin,
    # a working DNS path), the mode refuses: only the proxy may reach it.
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    found = profile.refusals(
        settings,
        {**GPTOSS_ENV},
        env_files=no_files(),
        resolve=lambda h: addresses if h == provider.OPENROUTER_HOST else [CLAUDE_PIN],
    )
    if addresses:
        assert found == ["OPENROUTER_DIRECT_PATH_REFUSED"]
    else:
        assert found == []


def test_the_anthropic_pin_is_unchanged(approved: None) -> None:
    assert not provider.pinned([OR_PIN])
    assert provider.pinned([CLAUDE_PIN])


def test_both_modes_are_checked_separately_and_registered_separately(
    tmp_path: Path, approved: None
) -> None:
    assert refusals(tmp_path, BOTH_ENV) == []
    # Each mode's own fault is reported; neither covers for the other.
    assert refusals(tmp_path, {**BOTH_ENV, provider.CEILING_VARIABLE: ""}) == [
        "HOSTED_CEILING_REQUIRED"
    ]
    assert refusals(tmp_path, {**BOTH_ENV, provider.DAILY_CAP_VARIABLE: ""}) == [
        "HOSTED_DAILY_CAP_REQUIRED"
    ]
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    only_openrouter = profile.refusals(
        settings,
        BOTH_ENV,
        env_files=no_files(),
        resolve=lambda host: [],
    )
    assert only_openrouter == ["PROVIDER_PIN_REQUIRED"]
    assert provider.install(settings, BOTH_ENV) is True
    assert anthropic_runtime.hosted_deployment() == (ORIGIN, CLAUDE_CEILING)
    assert remote_test.hosted_deployment() == (ORIGIN, DAILY)
    assert openrouter.hosted_proxy() == PROXY


# --- the runtime registration -------------------------------------------------------------


@pytest.mark.parametrize(
    ("origin", "daily"),
    [
        ("http://clm.example.test", DAILY),
        ("https://127.0.0.1", DAILY),
        ("https://localhost", DAILY),
        ("https://clm.example.test/app", DAILY),
        ("https://clm.example.test/", DAILY),
        ("https://", DAILY),
        (ORIGIN, 0),
        (ORIGIN, DAILY + 1),
    ],
)
def test_registration_refuses_anything_but_one_https_origin_and_a_bounded_ceiling(
    approved: None, origin: str, daily: int
) -> None:
    with pytest.raises(ValueError):
        remote_test.register_hosted_deployment(origin, daily)
    assert remote_test.hosted_deployment() is None
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY  # standing ceiling


def test_registration_happens_once_with_the_same_values_only(approved: None) -> None:
    remote_test.register_hosted_deployment(ORIGIN, 2_000_000)
    remote_test.register_hosted_deployment(ORIGIN, 2_000_000)  # repeatable
    for other in (("https://other.example.test", 2_000_000), (ORIGIN, DAILY), (ORIGIN, 1)):
        with pytest.raises(ValueError):
            remote_test.register_hosted_deployment(*other)
    assert remote_test.hosted_deployment() == (ORIGIN, 2_000_000)
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == 2_000_000


def test_the_hosted_deployment_is_the_one_origin_and_never_loopback(
    tmp_path: Path, approved: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    remote_test.register_hosted_deployment(ORIGIN, DAILY)
    assert remote_test.readiness(hosted_settings(tmp_path, **OR_SETTINGS)) is None
    for overrides in (
        {"allowed_origins": ["https://other.example.test"]},
        {"allowed_origins": [ORIGIN, "https://other.example.test"]},
        {"clm_backend_url": "http://127.0.0.1:8000"},
        {"clm_backend_url": "http://localhost:8000"},
        # A development machine's values never pass in a registered hosted process.
        {
            "clm_backend_url": "http://127.0.0.1:8000",
            "allowed_origins": ["http://127.0.0.1:5173"],
        },
    ):
        settings = hosted_settings(tmp_path, **{**OR_SETTINGS, **overrides})
        assert remote_test.readiness(settings) == "NOT_DEVELOPMENT_ENVIRONMENT", overrides
    assert remote_test.readiness(hosted_settings(tmp_path, **OR_SETTINGS, llm_enabled=False)) == (
        "MODEL_DISABLED_BY_ENVIRONMENT"
    )
    # The decision leaving the code closes a registered deployment too.
    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_DECISION", None)
    assert remote_test.readiness(hosted_settings(tmp_path, **OR_SETTINGS)) == (
        "NOT_DEVELOPMENT_ENVIRONMENT"
    )


def test_a_development_machine_is_unchanged_when_nothing_is_registered(tmp_path: Path) -> None:
    local = hosted_settings(
        tmp_path,
        **OR_SETTINGS,
        clm_backend_url="http://127.0.0.1:8000",
        allowed_origins=["http://127.0.0.1:5173"],
    )
    assert remote_test.readiness(local) is None
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY  # standing ceiling


def test_harden_refuses_a_half_configured_openrouter_mode(tmp_path: Path, approved: None) -> None:
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    transport = httpx.MockTransport(HostedClm().handler)
    app = create_app(settings, clm_transport=transport, knowledge=knowledge(settings))
    with pytest.raises(ValueError):  # the mode named, the runtime not registered
        harden(app, settings, environ=GPTOSS_ENV, transport=transport)
    remote_test.register_hosted_deployment(ORIGIN, DAILY - 1)
    with pytest.raises(ValueError):  # registered with another ceiling
        harden(app, settings, environ=GPTOSS_ENV, transport=transport)
    with pytest.raises(ValueError):  # registered, the mode not named
        harden(app, settings, environ=ELIGIBLE, transport=transport)


def test_the_qualification_process_registers_itself_in_the_openrouter_mode(
    tmp_path: Path, approved: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "qualify_model", ASSISTANT_DIR / "scripts" / "qualify_model.py"
    )
    assert spec is not None and spec.loader is not None
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    values = {
        **GPTOSS_ENV,
        "AI_ASSISTANT_DATA_DIR": str(tmp_path),
        "AI_ASSISTANT_CLM_BACKEND_URL": BACKEND,
        "AI_ASSISTANT_ALLOWED_ORIGINS": json.dumps([ORIGIN]),
        "AI_ASSISTANT_LLM_ENABLED": "true",
        "AI_ASSISTANT_LLM_BASE_URL": profile.NO_MODEL_URL,
        "AI_ASSISTANT_LLM_MODEL": profile.NO_MODEL_NAME,
        "AI_ASSISTANT_LLM_WARM_UP": "false",
        "AI_ASSISTANT_MODEL_PROFILES_FILE": str(DEPLOY / "model_profiles.hosted.json"),
        **{f"AI_ASSISTANT_{name.upper()}": str(value) for name, value in OR_SETTINGS.items()},
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(provider, "system_resolver", resolve)
    monkeypatch.chdir(tmp_path)
    assert script.hosted_ready() is True
    assert remote_test.hosted_deployment() == (ORIGIN, DAILY)
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY
    # A refused configuration stops the run before anything is called.
    monkeypatch.setattr(remote_test, "_hosted", None)
    monkeypatch.setenv("OPENROUTER_API_KEY", OR_KEY)
    assert script.hosted_ready() is False
    assert remote_test.hosted_deployment() is None


# --- the guard ---------------------------------------------------------------------------------


def test_every_openrouter_route_the_guard_allows_is_a_real_route(site: Site) -> None:
    app: Any = site.client.app
    routes = {
        (method.upper(), re.sub(r"\{[^}]+\}", "{x}", path[len(ADMIN_PREFIX) :]))
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(ADMIN_PREFIX + "/")
        for method in operations
    }
    for verb, shape in OPENROUTER_CHANGES:
        if OPENROUTER_PROFILE_ID in shape.pattern:
            assert (verb, "/{x}/qualifications") in routes
            continue
        assert (verb, shape.pattern.replace("[^/]+", "{x}")) in routes, shape.pattern


@pytest.mark.parametrize(
    ("method", "tail"),
    [
        ("PUT", "/credential/anthropic"),
        ("DELETE", "/credential/anthropic"),
        ("PUT", "/provider/anthropic"),
        ("POST", "/provider/anthropic/workspace-read"),
        ("PUT", "/budget/claude/controls"),
        ("PUT", "/budget/claude/lifetime-cap"),
        ("POST", f"/{BALANCED.profile_id}/qualifications"),
        ("POST", "/openrouter_gpt_oss_120b_low/qualifications"),
        ("POST", "/lmstudio_qwen3_8b/qualifications"),
        ("POST", "/budget/claude/reconciliation/apply"),
        ("POST", "/a-route-added-later"),
    ],
)
def test_claude_and_unreviewed_changes_stay_refused_in_the_openrouter_mode(
    site: Site, method: str, tail: str
) -> None:
    response = site.client.request(
        method, ADMIN_PREFIX + tail, headers=post_headers("hr"), json={"api_key": CLAUDE_KEY}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "HOSTED_REMOTE_DISABLED"
    assert CLAUDE_KEY not in site.hr("GET", "/audit").text


def test_the_claude_route_list_is_unchanged_by_the_openrouter_mode() -> None:
    assert len(CLAUDE_CHANGES) == 11
    claude_only = {(verb, shape.pattern) for verb, shape in CLAUDE_CHANGES}
    assert ("PUT", "/credential") not in claude_only
    assert ("PUT", "/budget/controls") not in claude_only


def test_an_rm_cannot_enter_a_key_or_change_the_limits(site: Site) -> None:
    for method, tail, body in (
        ("PUT", "/credential", {"api_key": OR_KEY}),
        ("PUT", "/budget/controls", {"expected_revision": 0, "daily_cap_micro_usd": 1}),
    ):
        response = site.client.request(
            method, ADMIN_PREFIX + tail, headers=post_headers("rm-a"), json=body
        )
        assert response.status_code in (403, 404), response.text
    assert OR_KEY not in site.hr("GET", "/audit").text


# --- registry and routing: only a qualified model, never another one ---------------------------


def test_an_unqualified_gpt_oss_cannot_be_activated_and_answers_nothing(site: Site) -> None:
    site.setup_gptoss()
    refused = site.activate_gptoss()
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"]["code"] == "NOT_QUALIFIED"
    assert site.active() != OPENROUTER_PROFILE_ID
    status, events = site.ask()
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert site.chats() == 0


def test_hr_sets_up_gpt_oss_and_an_rm_gets_a_streamed_answer(live: Site) -> None:
    site = live
    assert site.chats() == 2  # the two approved qualification questions
    assert site.active() == OPENROUTER_PROFILE_ID
    status, events = site.ask()
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "model" and answer["model"] == OPENROUTER_MODEL_ID
    assert answer["notice"].startswith(HOSTED_ANSWERED)
    assert SCRIPT[QUESTION].split(",")[0] in answer["answer"]
    assert site.chats() == 3
    _settle_verification()
    # Every request went to OpenRouter with the HR key, for the one approved endpoint, and
    # nothing reached Anthropic.
    posts = [r for r in site.openrouter.requests if r.method == "POST"]
    assert posts and all(r.headers["authorization"] == f"Bearer {OR_KEY}" for r in posts)
    assert {r.url.host for r in site.openrouter.requests} == {provider.OPENROUTER_HOST}
    assert {body["model"] for body in site.openrouter.chats} == {OPENROUTER_MODEL_ID}
    assert {body["provider"]["only"][0] for body in site.openrouter.chats} == {"deepinfra/bf16"}
    assert site.claude.requests == []
    # The key never shows in what HR or the RM can read.
    for text in (
        site.hr("GET", "").text,
        site.hr("GET", "/audit").text,
        site.hr("GET", "/budget").text,
        json.dumps(events),
    ):
        assert OR_KEY not in text


def test_the_hosted_prompt_names_the_role_and_never_the_user(live: Site) -> None:
    site = live
    status, _ = site.ask()
    assert status == 200
    sent = json.dumps(site.openrouter.chats[-1])
    for identifier in ("maya-lim", "Maya Lim", "maya lim"):
        assert identifier.lower() not in sent.lower()
    # The viewer is there as a role only.
    assert re.search(r"viewer\W+role\W+RM\W*}", sent.replace("\\", "")), sent[:400]


def test_a_qualification_for_another_fingerprint_never_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, live: Site
) -> None:
    # The same data root restarted with another reasoning allowance: another configuration.
    listed = live.hr("GET", "").json()["profiles"]
    old = next(p for p in listed if p["profile_id"] == OPENROUTER_PROFILE_ID)["fingerprint"]
    again = Site(tmp_path, monkeypatch, HostedClm(), llm_reasoning_allowance_tokens=1500)
    overview = again.hr("GET", "").json()
    entry = next(p for p in overview["profiles"] if p["profile_id"] == OPENROUTER_PROFILE_ID)
    assert entry["fingerprint"] != old
    assert overview["active"]["profile_id"] != OPENROUTER_PROFILE_ID
    assert entry["activation_blockers"] == ["NOT_QUALIFIED"]
    again.hr("PUT", "/credential", {"api_key": OR_KEY})
    refused = again.activate_gptoss()
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "NOT_QUALIFIED"
    status, events = again.ask()
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert again.chats() == 0
    reverted = [e for e in again.hr("GET", "/audit").json()["events"] if e["outcome"] == "reverted"]
    assert reverted and reverted[0]["code"] == "PROFILE_CHANGED"


def test_a_qualification_on_another_basis_never_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, live: Site
) -> None:
    # The answering code changed since the run (another basis hash): out of date at restart.
    monkeypatch.setattr(model_admin, "qualification_basis", lambda: "f" * 64)
    again = Site(tmp_path, monkeypatch, HostedClm())
    assert again.active() != OPENROUTER_PROFILE_ID
    again.hr("PUT", "/credential", {"api_key": OR_KEY})
    refused = again.activate_gptoss()
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "NOT_QUALIFIED"
    status, events = again.ask()
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert again.chats() == 0


def test_a_provider_failure_gives_the_case_data_answer_and_no_other_model(live: Site) -> None:
    site = live
    before = site.chats()
    site.openrouter.fail = True
    status, events = site.ask()
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data" and answer["model"] is None
    assert (answer["notice"] or "").startswith(FALLBACK_NOTICE.split(".")[0])
    assert HOSTED_ANSWERED not in (answer["notice"] or "")
    assert site.chats() == before + 1  # one attempt, no retry
    assert site.claude.requests == []
    assert site.active() == OPENROUTER_PROFILE_ID  # never switched to another model


def test_gpt_oss_never_falls_back_to_claude(both: Site) -> None:
    site = both
    # Claude is fully set up and qualified, then GPT-OSS is made the active model.
    site.setup_claude()
    site.qualify_and_activate()
    site.go_live()
    assert site.active() == OPENROUTER_PROFILE_ID
    claude_posts = site.claude.posts
    site.openrouter.fail = True
    status, events = site.ask()
    assert status == 200 and done(events)["answered_by"] == "case_data"
    assert site.claude.posts == claude_posts
    assert site.active() == OPENROUTER_PROFILE_ID


def test_claude_never_falls_back_to_gpt_oss(both: Site) -> None:
    site = both
    # GPT-OSS is fully set up and qualified, then Claude is made the active model.
    site.go_live()
    site.setup_claude()
    site.qualify_and_activate()
    assert site.active() == BALANCED.profile_id
    chats = site.chats()
    status, events = site.ask()
    assert status == 200 and done(events)["model"] == "claude-sonnet-5-5"
    site.claude.status = 529  # the provider is overloaded
    status, events = site.ask()
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data" and answer["model"] is None
    assert site.chats() == chats  # GPT-OSS was not asked, whatever Claude did
    assert site.active() == BALANCED.profile_id


def test_gpt_oss_answers_the_case_chat_only(live: Site) -> None:
    site = live
    chats = site.chats()
    opened = site.client.post("/assistant/contexts", headers=post_headers("rm-a"), json={})
    assert opened.status_code == 200, opened.text
    general = site.client.post(
        "/assistant/general/chat/stream",
        headers=post_headers("rm-a"),
        json={"message": "What is a UBO check?", "context_id": opened.json()["context_id"]},
    )
    assert general.status_code == 200, general.text
    reply = done([json.loads(line) for line in general.text.splitlines() if line.strip()])
    assert reply["answered_by"] == "case_data" and reply["model"] is None
    support = site.client.post(
        "/assistant/support/chat",
        headers=post_headers("support"),
        json={"message": "What is the UBO threshold?"},
    )
    assert support.status_code == 200, support.text
    assert support.json()["answered_by"] == "case_data"
    insights = site.client.get("/assistant/dashboard/insights", headers=session("rm-a"))
    assert insights.status_code == 503
    assert site.chats() == chats


def test_another_team_and_an_unlisted_case_send_nothing(live: Site) -> None:
    site = live
    chats = site.chats()
    status, _ = site.ask(token="rm-b")
    assert status == 404
    status, _ = site.ask(case_id=UUID("00000000-0000-4000-8000-00000000abcd"))
    assert status in (403, 404)
    assert site.chats() == chats


# --- money: the hard daily ceiling and the console ---------------------------------------------


def test_hr_may_lower_the_daily_limit_but_never_raise_it_above_the_ceiling(live: Site) -> None:
    site = live
    controls = site.budget()["controls"]
    assert controls["daily_cap_max_micro_usd"] == DAILY
    assert controls["daily_ceiling_micro_usd"] == DAILY
    # The environment default (US$5.00) is already held to the ceiling.
    assert controls["daily_cap_micro_usd"] == DAILY
    for above in (DAILY + 1, 5_000_000, 10**12):
        refused = site.controls(above, confirm_daily_cap_micro_usd=above)
        assert refused.status_code == 400, refused.text
        assert refused.json()["detail"]["code"] == "DAILY_CEILING_EXCEEDED"
    assert site.budget()["controls"]["daily_cap_micro_usd"] == DAILY
    lowered = site.controls(1_000_000)
    assert lowered.status_code == 200, lowered.text
    assert lowered.json()["controls"]["daily_cap_micro_usd"] == 1_000_000
    assert lowered.json()["daily"]["cap_micro_usd"] == 1_000_000
    events = site.hr("GET", "/audit").json()["events"]
    refusals_logged = [e for e in events if e["code"] == "DAILY_CEILING_EXCEEDED"]
    assert len(refusals_logged) == 3


def test_a_stored_value_above_the_ceiling_is_never_applied(live: Site) -> None:
    # A value stored before the ceiling existed (written straight into the state database).
    stored = SpendingControls(7, 9_000_000, 20, None, None)
    assert apply_controls(live.settings, stored).budget_daily_cap_micro_usd == DAILY
    assert apply_controls(live.settings, None).budget_daily_cap_micro_usd == 0  # fail closed
    lower = SpendingControls(8, 400_000, 20, None, None)
    assert apply_controls(live.settings, lower).budget_daily_cap_micro_usd == 400_000


def test_the_console_shows_spent_reserved_remaining_and_the_reset_time(live: Site) -> None:
    site = live
    status, _ = site.ask()
    assert status == 200
    _settle_verification()
    view = site.budget()
    daily = view["daily"]
    ledger = BudgetLedger.open(Path(site.settings.budget_ledger_path))
    charged = sum(call.charged_micro_usd for call in ledger.closed_calls_after(0))
    assert charged > 0 and daily["settled_today_micro_usd"] == charged
    assert daily["in_flight_micro_usd"] == 0 and daily["in_flight_calls"] == 0
    assert daily["cap_micro_usd"] == DAILY and daily["ceiling_micro_usd"] == DAILY
    assert daily["remaining_micro_usd"] == DAILY - charged
    assert daily["exhausted"] is False
    assert view["timezone"] == "Asia/Singapore"
    assert view["next_reset_at"].endswith("T16:00:00Z")  # 00:00 in Singapore
    assert view["hosted"] is True and view["daily_ceiling_micro_usd"] == DAILY


def test_an_exhausted_day_is_shown_and_answered_from_the_case_data(live: Site) -> None:
    site = live
    lowered = site.controls(2_000)  # below today's spend plus one more reservation
    assert lowered.status_code == 200, lowered.text
    view = site.budget()
    assert view["daily"]["exhausted"] is True
    assert view["refusal"] == "DAILY_ALLOWANCE_EXHAUSTED"
    assert view["effective_remaining_micro_usd"] == view["daily"]["remaining_micro_usd"]
    chats = site.chats()
    status, events = site.ask()
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data" and answer["model"] is None
    assert site.chats() == chats  # refused before anything was sent
    assert site.claude.requests == []
    assert site.active() == OPENROUTER_PROFILE_ID


def test_the_session_call_count_is_not_applied_on_the_hosted_deployment(live: Site) -> None:
    site = live
    one = site.controls(DAILY, calls=1)
    assert one.status_code == 200, one.text
    controls = one.json()["controls"]
    assert controls["max_calls"] == 1 and controls["max_calls_applies"] is False
    chats = site.chats()
    for _ in range(3):
        status, events = site.ask()
        assert status == 200 and done(events)["answered_by"] == "model"
    assert site.chats() == chats + 3


def test_claudes_limits_are_untouched_by_the_openrouter_ceiling(both: Site) -> None:
    site = both
    assert budget.daily_ceiling(OPENROUTER_PROFILE_ID) == DAILY
    assert anthropic_runtime.LIFETIME_CEILING_MICRO_USD == 30_000_000
    assert anthropic_runtime.DAILY_CEILING_MICRO_USD == 5_000_000
    assert anthropic_runtime.MAX_CALLS_CEILING == 20
    assert CLAUDE_DAILY_CAP_RANGE == (1, 5_000_000)
    assert anthropic_runtime.lifetime_ceiling() == CLAUDE_CEILING
    claude = SpendingControls(3, 5_000_000, 20, None, None)
    applied = apply_claude_controls(site.settings, claude)
    assert applied.anthropic_daily_cap_micro_usd == 5_000_000
    assert applied.anthropic_max_calls == 20
    view = site.budget()["claude"]["controls"]
    assert view["daily_cap_range"] == [1, 5_000_000]


# --- the per-user request rate -----------------------------------------------------------------


def test_one_user_over_the_rate_gets_the_case_data_answer_and_nothing_is_sent(
    live: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = live
    monkeypatch.setitem(
        test_hosting.SESSIONS, "rm-c", actor("noah-tan", "RM", "team-a", "CASE_ACCESS")
    )
    chats = site.chats()
    for _ in range(request_rate.MINUTE_LIMIT):
        status, events = site.ask()
        assert status == 200 and done(events)["answered_by"] == "model"
    assert site.chats() == chats + request_rate.MINUTE_LIMIT
    reserved = site.budget()["daily"]["settled_today_micro_usd"]
    status, events = site.ask()
    assert status == 200
    answer = done(events)
    assert answer["answered_by"] == "case_data" and answer["model"] is None
    assert (answer["notice"] or "").startswith(FALLBACK_NOTICE.split(".")[0])
    assert site.chats() == chats + request_rate.MINUTE_LIMIT
    _settle_verification()
    assert site.budget()["daily"]["settled_today_micro_usd"] == reserved  # nothing reserved
    # Another signed-in user of the same team is not held back by the first one.
    status, events = site.ask(token="rm-c")
    assert status == 200 and done(events)["answered_by"] == "model"


def test_the_rate_windows_slide_and_the_hourly_share_follows_the_reservation() -> None:
    now = [1000.0]
    rate = request_rate.UserRate(clock=lambda: now[0])
    assert all(rate.admit("a", per_minute=2, per_hour=3) for _ in range(2))
    assert not rate.admit("a", per_minute=2, per_hour=3)  # the minute is full
    assert rate.admit("b", per_minute=2, per_hour=3)  # per user
    now[0] += 60
    assert rate.admit("a", per_minute=2, per_hour=3)
    assert not rate.admit("a", per_minute=2, per_hour=3)  # the hour is full (3)
    now[0] += 3540
    assert rate.admit("a", per_minute=2, per_hour=3)  # the first two left the hour
    # A share of the calls a worst-case day admits; never zero.
    assert request_rate.hourly_limit(3_000_000, 21_277) == 3_000_000 // 21_277 // 4 == 35
    assert request_rate.hourly_limit(3_000_000, 3_000_000) == 1
    assert request_rate.hourly_limit(1, 21_277) == 1
    assert request_rate.hourly_limit(0, 0) == 1


def test_the_rate_never_applies_off_the_hosted_gpt_oss_deployment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hosted_replies: list[str],  # noqa: F811
) -> None:
    # Hosted Claude only: more requests than the minute limit are all answered by Claude.
    hosted = Hosted(tmp_path, monkeypatch, HostedClm())
    hosted.setup_claude()
    hosted.qualify_and_activate()
    assert remote_test.hosted_deployment() is None
    for _ in range(request_rate.MINUTE_LIMIT + 2):
        status, events = hosted.ask()
        assert status == 200 and done(events)["answered_by"] == "model"


# D-139: these tests treat the fixture case as verified synthetic (the seam in conftest);
# test_hosted_case_policy.py runs the real provenance check.
pytestmark = pytest.mark.usefixtures("hosted_case_eligible")
