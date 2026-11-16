"""D-138 A1 (PROPOSED, NOT ACTIVE): the hosted GPT-OSS egress controls.

- the client: one code-fixed exact-host proxy, only once the hosted deployment registered it;
  every other proxy source ignored; TLS verified for openrouter.ai; no retries;
- the start-up check that replaces D-134's empty address pin, and OpenRouter's own
  transmission decision (D-129 covers Anthropic only);
- the guard's backend-reported external AI data for the browser notice;
- the deployment files: the proxy guard, the host table, the watcher, the units and the
  overlay, checked statically against each other and against R3's and E1's reviewed files.

No provider, no key, no network beyond a loopback stand-in for the proxy; synthetic values only.
"""

# ruff: noqa: F811 - the fixtures imported from test_hosted_gptoss are used as parameters

from __future__ import annotations

import importlib.util
import ipaddress
import re
import socket
import ssl
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import anyio
import httpx
import pytest
import yaml

from ai_assistant import anthropic_runtime, openrouter, remote_checks, remote_test
from ai_assistant import config as assistant_config
from ai_assistant.openrouter import LIVE_NETWORK
from ai_assistant.openrouter_account import OpenRouterAccount
from assistant_hosting import profile, provider
from assistant_hosting.harden import harden
from tests import conftest
from tests.remote_fixtures import ENDPOINT
from tests.test_conversational_external import scripted  # noqa: F401 (fixture)
from tests.test_hosted_claude import CEILING as CLAUDE_CEILING
from tests.test_hosted_claude import CLAUDE_ENV
from tests.test_hosted_gptoss import (  # noqa: F401 (approved and site are fixtures)
    BOTH_ENV,
    DAILY,
    GPTOSS_ENV,
    OR_SETTINGS,
    PROXY,
    Site,
    approved,
    on_internal_network,
    resolve,
    site,
)
from tests.test_hosting import CASE_ID, ORIGIN, hosted_settings, no_files, session

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
REPO = ASSISTANT_DIR.parents[1]
DEPLOY = ASSISTANT_DIR / "deploy"
EGRESS = DEPLOY / "egress"
R3 = REPO / "deploy" / "egress"


def refusals(tmp_path: Path, env: dict[str, str], **kwargs: Any) -> list[str]:
    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    return profile.refusals(settings, env, env_files=no_files(), resolve=resolve, **kwargs)


# --- the client's proxy ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "http://172.30.246.2:4750",
        "http://172.30.246.4:4750",
        "http://172.30.246.6:4750",
    ],
)
def test_the_proxy_setting_accepts_one_spelling_inside_the_internal_network(text: str) -> None:
    assert openrouter.parse_hosted_proxy(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "172.30.246.2:4750",  # no scheme
        "https://172.30.246.2:4750",  # a TLS proxy is not the reviewed one
        "http://172.30.246.2",  # no port
        "http://172.30.246.2:4751",  # another port
        "http://172.30.246.2:04750",
        "http://172.30.246.2:4750/",  # a path
        "http://user@172.30.246.2:4750",  # userinfo
        "http://clm-openrouter-egress:4750",  # a name: it would need DNS
        "http://172.30.246.0:4750",  # the network address
        "http://172.30.246.1:4750",  # the gateway
        "http://172.30.246.7:4750",  # the broadcast address
        "http://172.30.246.8:4750",  # outside the /29
        "http://172.30.247.2:4750",  # the uplink, never the control network
        "http://172.030.244.2:4750",  # a leading zero
        "http://[::1]:4750",
        " http://172.30.246.2:4750",
        "http://172.30.246.2:4750\n",
    ],
)
def test_the_proxy_setting_refuses_every_other_value(text: str) -> None:
    assert openrouter.parse_hosted_proxy(text) is None


def test_the_shipped_code_has_no_proxy_until_one_is_registered() -> None:
    assert openrouter.hosted_proxy() is None
    assert openrouter.live_transport() is None and openrouter.live_async_transport() is None
    # D-134 and D-129A accepted (owner): the decisions ship recorded; a proxy is still only
    # ever registered by the hosted OpenRouter mode with its reviewed egress in place.
    assert assistant_config.HOSTED_OPENROUTER_DECISION == "D-134"
    assert conftest.SHIPPED_OPENROUTER_TRANSMISSION_DECISION == "D-129A"


@pytest.mark.parametrize(
    "decision",
    [
        "HOSTED_OPENROUTER_DECISION",
        "HOSTED_TRANSMISSION_DECISION",
        "HOSTED_OPENROUTER_TRANSMISSION_DECISION",
    ],
)
def test_the_proxy_registers_only_with_every_decision_in_the_code(
    approved: None, monkeypatch: pytest.MonkeyPatch, decision: str
) -> None:
    monkeypatch.setattr(assistant_config, decision, None)
    with pytest.raises(ValueError):
        openrouter.register_hosted_proxy(PROXY)
    assert openrouter.hosted_proxy() is None


def test_the_proxy_registers_once_with_the_same_value_only(approved: None) -> None:
    with pytest.raises(ValueError):
        openrouter.register_hosted_proxy("http://172.30.246.9:4750")
    openrouter.register_hosted_proxy(PROXY)
    openrouter.register_hosted_proxy(PROXY)
    with pytest.raises(ValueError):
        openrouter.register_hosted_proxy("http://172.30.246.4:4750")
    assert openrouter.hosted_proxy() == PROXY


def _pool(transport: httpx.HTTPTransport | httpx.AsyncHTTPTransport) -> Any:
    return transport._pool  # noqa: SLF001 - the transport's own connection pool


def test_the_live_transport_uses_only_the_registered_proxy_and_verifies_tls(
    approved: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every other proxy and certificate source is present, and none is read.
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("ALL_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("SSL_CERT_FILE", str(ASSISTANT_DIR / "does-not-exist.pem"))
    monkeypatch.setenv("SSL_CERT_DIR", str(ASSISTANT_DIR / "does-not-exist"))
    openrouter.register_hosted_proxy(PROXY)
    for transport in (openrouter.live_transport(), openrouter.live_async_transport()):
        assert transport is not None
        pool = _pool(transport)
        assert type(pool).__name__ in {"HTTPProxy", "AsyncHTTPProxy"}
        url = pool._proxy_url  # noqa: SLF001
        assert (url.scheme, url.host, url.port) == (b"http", b"172.30.246.2", 4750)
        assert pool._proxy_ssl_context is None  # noqa: SLF001 - a plain proxy hop
        context = pool._ssl_context  # noqa: SLF001
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        assert pool._retries == 0  # noqa: SLF001


class FakeProxy:
    """A loopback stand-in for the egress proxy: it records the first request head and refuses,
    as the real gate does for anything it does not admit (nothing goes further)."""

    def __init__(self) -> None:
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(4)
        self.port = self.server.getsockname()[1]
        self.heads: list[bytes] = []
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self.server.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(5)
                head = b""
                while b"\r\n\r\n" not in head and len(head) < 4096:
                    chunk = conn.recv(512)
                    if not chunk:
                        break
                    head += chunk
                self.heads.append(head)
                conn.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")

    def close(self) -> None:
        self.server.close()


def r3_gate(head: bytes, authority: str) -> str:
    """A transcription of checkHead in deploy/egress/smokescreen-main/main.go ("" = admitted)."""

    allowed = {"host", "accept", "user-agent", "proxy-connection", "connection"}
    if any(b not in (13, 10) and not 0x20 <= b <= 0x7E for b in head):
        return "non_ascii_or_control_byte"
    if not head.endswith(b"\r\n\r\n"):
        return "incomplete_head"
    lines = head[:-4].decode("ascii").split("\r\n")
    if lines[0] != f"CONNECT {authority} HTTP/1.1":
        return "request_line_not_exact_connect"
    hosts = 0
    for line in lines[1:]:
        name, sep, value = line.partition(":")
        if not sep or not name or " " in name or "\t" in name:
            return "malformed_header"
        if name.lower() not in allowed:
            return "header_not_allowed"
        if name.lower() == "host":
            hosts += 1
            if value.lstrip(" ") != authority:
                return "host_header_not_exact"
    return "" if hosts == 1 else "host_header_count"


@pytest.fixture
def fake_proxy(monkeypatch: pytest.MonkeyPatch) -> Any:
    proxy = FakeProxy()
    # The stand-in listens on loopback; the registered value is set directly (test only).
    monkeypatch.setattr(openrouter, "_hosted_proxy", f"http://127.0.0.1:{proxy.port}")
    real = socket.getaddrinfo

    def no_direct_lookup(host: Any, *args: Any, **kwargs: Any) -> Any:
        # The client never resolves openrouter.ai itself: only the proxy does.
        assert host != "openrouter.ai", "the client resolved openrouter.ai directly"
        return real(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", no_direct_lookup)
    yield proxy
    proxy.close()


def _model() -> openrouter.OpenRouterChatModel:
    return openrouter.OpenRouterChatModel(
        endpoint=ENDPOINT,
        credential=__import__("pydantic").SecretStr("sk-or-" + "ProxySentinel" * 3),
        timeout_seconds=5,
        temperature=0.2,
        answer_tokens=400,
        reasoning_effort="low",
        reasoning_allowance_tokens=1400,
        max_prompt_bytes=200_000,
        transport=LIVE_NETWORK,
    )


MESSAGES = [{"role": "system", "content": "Connection test."}, {"role": "user", "content": "Hi."}]


def test_a_live_chat_call_tunnels_through_the_proxy_with_the_exact_connect_head(
    fake_proxy: FakeProxy,
) -> None:
    with pytest.raises(openrouter.ModelCallError):
        _model().complete(MESSAGES)
    assert len(fake_proxy.heads) == 1  # no retry
    head = fake_proxy.heads[0]
    assert r3_gate(head, "openrouter.ai:443") == ""
    # The key and the prompt never reach the proxy: they travel inside TLS only.
    assert b"ProxySentinel" not in head and b"Connection test" not in head


def test_a_live_streamed_call_tunnels_through_the_proxy(fake_proxy: FakeProxy) -> None:
    async def drain() -> None:
        async for _ in _model().stream(MESSAGES):
            pass

    with pytest.raises(openrouter.ModelCallError):
        anyio.run(drain)
    assert len(fake_proxy.heads) == 1
    assert r3_gate(fake_proxy.heads[0], "openrouter.ai:443") == ""


def test_the_account_checks_tunnel_through_the_proxy(fake_proxy: FakeProxy) -> None:
    account = OpenRouterAccount(
        __import__("pydantic").SecretStr("sk-or-" + "ProxySentinel" * 3), transport=LIVE_NETWORK
    )
    with pytest.raises(Exception):  # noqa: B017 - the closed AccountCheckError("transport")
        account.key_status()
    assert fake_proxy.heads and r3_gate(fake_proxy.heads[0], "openrouter.ai:443") == ""
    assert b"ProxySentinel" not in fake_proxy.heads[0]


def test_the_public_listing_tunnels_through_the_proxy(fake_proxy: FakeProxy) -> None:
    with pytest.raises(httpx.HTTPError):
        remote_checks.fetch_public("/models/openai/gpt-oss-120b/endpoints")
    assert len(fake_proxy.heads) == 1
    assert r3_gate(fake_proxy.heads[0], "openrouter.ai:443") == ""


def test_a_mock_transport_is_never_replaced_by_the_proxy(approved: None) -> None:
    openrouter.register_hosted_proxy(PROXY)
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(500)

    model = openrouter.OpenRouterChatModel(
        endpoint=ENDPOINT,
        credential=__import__("pydantic").SecretStr("sk-or-" + "MockSentinel" * 3),
        timeout_seconds=5,
        temperature=0.2,
        answer_tokens=400,
        reasoning_effort="low",
        reasoning_allowance_tokens=1400,
        max_prompt_bytes=200_000,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(openrouter.ModelCallError):
        model.complete(MESSAGES)
    assert seen == ["https://openrouter.ai/api/v1/chat/completions"]


def test_the_r3_gate_transcription_refuses_what_main_go_refuses() -> None:
    good = b"CONNECT openrouter.ai:443 HTTP/1.1\r\nHost: openrouter.ai:443\r\n\r\n"
    assert r3_gate(good, "openrouter.ai:443") == ""
    for bad in (
        b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n",
        b"GET http://openrouter.ai/ HTTP/1.1\r\nHost: openrouter.ai\r\n\r\n",
        b"CONNECT openrouter.ai:443 HTTP/1.1\r\nHost: openrouter.ai:443\r\nX-A: 1\r\n\r\n",
        b"CONNECT openrouter.ai:443 HTTP/1.1\r\n\r\n",
    ):
        assert r3_gate(bad, "openrouter.ai:443") != ""


# --- the start-up check ----------------------------------------------------------------------


def test_a_fully_configured_mode_passes_and_registers_the_proxy_first(
    tmp_path: Path, approved: None
) -> None:
    assert refusals(tmp_path, GPTOSS_ENV) == []
    assert provider.install(hosted_settings(tmp_path, **OR_SETTINGS), GPTOSS_ENV) is True
    assert openrouter.hosted_proxy() == PROXY
    assert remote_test.hosted_deployment() == (ORIGIN, DAILY)


@pytest.mark.parametrize("value", ["", "http://172.30.246.1:4750", "http://10.0.0.2:4750"])
def test_a_missing_or_wrong_proxy_setting_stops_the_mode(
    tmp_path: Path, approved: None, value: str
) -> None:
    env = {**GPTOSS_ENV, provider.PROXY_VARIABLE: value}
    assert refusals(tmp_path, env) == ["OPENROUTER_PROXY_REQUIRED"]
    without = {k: v for k, v in GPTOSS_ENV.items() if k != provider.PROXY_VARIABLE}
    assert refusals(tmp_path, without) == ["OPENROUTER_PROXY_REQUIRED"]
    with pytest.raises(ValueError):
        provider.install(hosted_settings(tmp_path, **OR_SETTINGS), env)
    assert remote_test.hosted_deployment() is None and openrouter.hosted_proxy() is None


@pytest.mark.parametrize(
    "source",
    [
        None,  # no route at all
        "172.30.243.2",  # through E1's uplink and its gateway
        "192.168.1.20",  # through any other interface
        "172.30.246.2",  # the proxy's own address (a loop, not the assistant)
        "172.30.246.1",  # the gateway's address
        "not-an-address",
        "::1",
    ],
)
def test_the_proxy_must_be_reached_directly_on_the_internal_network(
    tmp_path: Path, approved: None, source: str | None
) -> None:
    found = refusals(tmp_path, GPTOSS_ENV, local_source=lambda address, port: source)
    assert found == ["OPENROUTER_PROXY_NOT_INTERNAL"]


def test_the_route_probe_asks_for_the_configured_address_and_port(
    tmp_path: Path, approved: None
) -> None:
    asked: list[tuple[str, int]] = []

    def probe(address: str, port: int) -> str:
        asked.append((address, port))
        return "172.30.246.3"

    assert refusals(tmp_path, GPTOSS_ENV, local_source=probe) == []
    assert asked == [("172.30.246.2", 4750)]


def test_the_system_route_probe_answers_the_kernels_source_address() -> None:
    # A UDP connect sends nothing. The suite blocks every remote address, so loopback only.
    assert provider.system_local_source("127.0.0.1", 9) == "127.0.0.1"
    assert not provider.proxy_internal(PROXY, lambda address, port: "127.0.0.1")


def test_a_proxy_setting_without_the_mode_is_refused(tmp_path: Path, approved: None) -> None:
    env = {**CLAUDE_ENV, provider.PROXY_VARIABLE: PROXY}
    found = profile.refusals(hosted_settings(tmp_path), env, env_files=no_files(), resolve=resolve)
    assert found == ["PROVIDER_SETTING_WITHOUT_MODE"]


def test_openrouter_needs_its_own_transmission_decision_even_with_d129_recorded(
    tmp_path: Path, approved: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant_config, "HOSTED_TRANSMISSION_DECISION", "D-129")
    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_TRANSMISSION_DECISION", None)
    assert refusals(tmp_path, GPTOSS_ENV) == ["OPENROUTER_TRANSMISSION_DECISION_REQUIRED"]
    assert refusals(tmp_path, BOTH_ENV) == ["OPENROUTER_TRANSMISSION_DECISION_REQUIRED"]
    with pytest.raises(ValueError):
        provider.install(hosted_settings(tmp_path, **OR_SETTINGS), GPTOSS_ENV)
    with pytest.raises(ValueError):
        remote_test.register_hosted_deployment(ORIGIN, DAILY)
    assert remote_test.hosted_deployment() is None and openrouter.hosted_proxy() is None
    # The Anthropic mode with D-129 recorded is unchanged by it.
    plain = hosted_settings(tmp_path)
    assert profile.refusals(plain, CLAUDE_ENV, env_files=no_files(), resolve=resolve) == []
    assert provider.install(plain, CLAUDE_ENV) is True
    assert anthropic_runtime.hosted_deployment() == (ORIGIN, CLAUDE_CEILING)


def test_without_any_transmission_decision_both_codes_are_reported(
    tmp_path: Path, approved: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant_config, "HOSTED_TRANSMISSION_DECISION", None)
    monkeypatch.setattr(assistant_config, "HOSTED_OPENROUTER_TRANSMISSION_DECISION", None)
    assert refusals(tmp_path, GPTOSS_ENV) == [
        "OPENROUTER_TRANSMISSION_DECISION_REQUIRED",
        "TRANSMISSION_DECISION_REQUIRED",
    ]
    plain = hosted_settings(tmp_path)
    found = profile.refusals(plain, CLAUDE_ENV, env_files=no_files(), resolve=resolve)
    assert found == ["TRANSMISSION_DECISION_REQUIRED"]


def test_no_refusal_prints_a_value(tmp_path: Path, approved: None) -> None:
    found = refusals(tmp_path, {**GPTOSS_ENV, provider.PROXY_VARIABLE: "http://10.9.8.7:4750"})
    assert "10.9.8.7" not in " ".join(found)


def test_harden_refuses_a_proxy_registration_that_does_not_match(
    tmp_path: Path, approved: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai_assistant.main import create_app

    settings = hosted_settings(tmp_path, **OR_SETTINGS)
    assert provider.install(settings, GPTOSS_ENV) is True
    app = create_app(settings, clm_transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    monkeypatch.setattr(openrouter, "_hosted_proxy", "http://172.30.246.4:4750")
    with pytest.raises(ValueError):
        harden(app, settings, environ=GPTOSS_ENV)
    monkeypatch.setattr(openrouter, "_hosted_proxy", None)
    with pytest.raises(ValueError):
        harden(app, settings, environ=GPTOSS_ENV)


# --- the backend-reported external AI data (browser notice) ----------------------------------


def test_health_reports_the_registered_provider_and_the_active_one(site: Site) -> None:
    before = site.client.get("/assistant/health", headers=session("rm-a")).json()
    assert before["external_ai"] == {
        "providers": ["openrouter"],
        "active": None,
        "surfaces": {"openrouter": ["case"]},
    }
    site.go_live()
    after = site.client.get("/assistant/health", headers=session("rm-a")).json()
    assert after["external_ai"]["active"] == "openrouter"


def test_a_successful_brief_carries_the_data_and_a_refusal_passes_unchanged(site: Site) -> None:
    site.go_live()
    brief = site.client.get(f"/assistant/cases/{CASE_ID}/brief", headers=session("rm-a"))
    assert brief.status_code == 200, brief.text
    body = brief.json()
    assert body["external_ai"]["active"] == "openrouter"
    assert body["company"]  # the brief itself is unchanged
    assert int(brief.headers["content-length"]) == len(brief.content)
    other = site.client.get(f"/assistant/cases/{uuid4()}/brief", headers=session("rm-a"))
    assert other.status_code == 404
    assert "external_ai" not in other.text


@pytest.fixture
def both_site(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    approved: None,
) -> Site:
    from tests.test_hosted_claude import HostedClm

    return Site(tmp_path, monkeypatch, HostedClm(), BOTH_ENV)


def test_both_modes_report_each_providers_surfaces(both_site: Site) -> None:
    data = both_site.client.get("/assistant/health", headers=session("rm-a")).json()["external_ai"]
    assert data["providers"] == ["anthropic", "openrouter"]
    assert data["surfaces"]["openrouter"] == ["case"]
    # Claude's surfaces follow D-130's hosted chat paths; insights only with their decision.
    assert data["surfaces"]["anthropic"] == ["case", "general", "support", "try"]
    assert data["active"] is None


def test_without_a_provider_mode_nothing_external_is_reported(tmp_path: Path) -> None:
    from assistant_hosting.guard import HostedGuard

    class Selector:
        def current(self) -> Any:
            raise RuntimeError

    guard = HostedGuard(None, allowed_origins=frozenset({ORIGIN}), selector=Selector())  # type: ignore[arg-type]
    assert guard._external_ai() == {"providers": [], "active": None, "surfaces": {}}  # noqa: SLF001


# --- the deployment files ----------------------------------------------------------------------


def _load_guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "openrouter_egress_guard", EGRESS / "openrouter_egress_guard.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["openrouter_egress_guard"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard() -> ModuleType:
    return _load_guard()


def _vars(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text("utf-8").splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            out[key] = value
    return out


@pytest.mark.parametrize(
    ("env", "code"),
    [
        ({"CLM_EGRESS_ROLE": "proxy"}, "fqdn_invalid"),
        ({"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "example.com"}, "fqdn_not_openrouter"),
        (
            {"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "api.openrouter.ai"},
            "fqdn_not_openrouter",
        ),
        ({"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "OPENROUTER.AI"}, "fqdn_invalid"),
        ({"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "openrouter.ai."}, "fqdn_invalid"),
        ({"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "1.2.3.4"}, "fqdn_invalid"),
        ({"CLM_EGRESS_ROLE": "other", "CLM_EGRESS_FQDN": "openrouter.ai"}, "role_invalid"),
        (
            {
                "CLM_EGRESS_ROLE": "proxy",
                "CLM_EGRESS_FQDN": "openrouter.ai",
                "CLM_EGRESS_DST_V4": "",
            },
            "dst_v4_not_supported",
        ),
    ],
)
def test_the_guard_refuses_any_other_environment(
    guard: ModuleType, env: dict[str, str], code: str
) -> None:
    with pytest.raises(guard.GuardError) as caught:
        guard.validate_env(env)
    assert str(caught.value) == code


def test_the_guard_renders_one_domain_and_the_exact_name_resolver(guard: ModuleType) -> None:
    cfg = guard.validate_env({"CLM_EGRESS_ROLE": "proxy", "CLM_EGRESS_FQDN": "openrouter.ai"})
    acl = yaml.safe_load(guard.render_acl(cfg.fqdn))
    assert acl["services"] == [
        {
            "name": "goldtier-backend",
            "project": "r22o",
            "action": "enforce",
            "allowed_domains": ["openrouter.ai"],
        }
    ]
    assert "allowed_domains" not in acl["default"]
    # R3's entrypoint fixes the role name; the ACL must match it.
    assert f'backendRole  = "{guard.ENTRYPOINT_ROLE}"' in (
        R3 / "smokescreen-main" / "main.go"
    ).read_text("utf-8")
    corefile = guard.render_corefile("openrouter.ai", (R3 / "Corefile.template").read_text("utf-8"))
    assert "name() == 'openrouter.ai.' && type() == 'A'" in corefile
    assert f"bind {guard.RESOLVER_CTL_IP}" in corefile
    assert f"forward . {guard.VPC_RESOLVER_IP}:53" in corefile
    argv = guard.smokescreen_argv(cfg)
    assert argv[argv.index("--listen-ip") + 1] == guard.PROXY_CTL_IP
    denied = [argv[i + 1] for i, a in enumerate(argv) if a == "--deny-range"]
    assert set(denied) == set(guard.NO_EGRESS_V4) | {"::/0"}
    assert not any(a.startswith("--unsafe") for a in argv)
    assert guard.child_env(cfg) == {"PATH": guard.CHILD_PATH, "R3_EGRESS_FQDN": "openrouter.ai"}


def test_the_proxy_layer_n_admits_only_the_assistant_and_tcp_443_out(guard: ModuleType) -> None:
    table = guard.render_layer_n("proxy", "eth0", "eth1")
    assert "policy drop" in table and table.count("counter accept") == 5
    assert (
        'iifname "eth0" ip saddr 172.30.246.3 ip daddr 172.30.246.2 tcp dport 4750 ct state new'
        in table
    )
    assert (
        'oifname "eth1" ip saddr 172.30.247.2 ip daddr != @no_egress_v4 tcp dport 443 ct state new'
        in table
    )
    assert 'oifname "eth0" ip saddr 172.30.246.2 ip daddr 172.30.246.4' in table
    assert "dport 80" not in table and "goldtier" not in table
    resolver = guard.render_layer_n("resolver", "eth0", "eth1")
    assert 'oifname "eth1" ip saddr 172.30.247.3 ip daddr 172.26.0.2' in resolver
    assert "dport 443" not in resolver
    with pytest.raises(guard.GuardError):
        guard.render_layer_n("proxy", "eth0;drop", "eth1")


def test_the_guard_differs_from_r3s_only_where_its_header_says(guard: ModuleType) -> None:
    r3 = (R3 / "goldtier_egress_guard.py").read_text("utf-8")
    mine = (EGRESS / "openrouter_egress_guard.py").read_text("utf-8")
    for shared in (
        "def normalised_ruleset_hash",
        "def drop_guard_privileges",
        "def setpriv_prefix",
    ):
        body_r3 = r3[r3.index(shared) :].split("\n\n\n")[0]
        body_mine = mine[mine.index(shared) :].split("\n\n\n")[0]
        assert body_r3 == body_mine, shared
    assert guard.SMOKESCREEN_DENY_RANGES == guard.NO_EGRESS_V4 + ("::/0",)


def test_the_host_table_matches_the_vars_and_the_guard(guard: ModuleType) -> None:
    values = _vars(EGRESS / "clm_r22o.vars")
    raw = (EGRESS / "clm_r22o.nft").read_text("utf-8")
    table = "\n".join(line for line in raw.splitlines() if not line.lstrip().startswith("#"))
    assert table.count("table inet clm_r22o {}") == 1 and "delete table inet clm_r22o" in table
    assert "flush ruleset" not in table and "clm_r22 " not in table and "clm_r3" not in table
    assert values["PROXY_UPLINK_IP"] == guard.PROXY_UP_IP
    assert values["RESOLVER_UPLINK_IP"] == guard.RESOLVER_UP_IP
    assert values["VPC_RESOLVER_IP"] == guard.VPC_RESOLVER_IP
    rules = [
        line.strip()
        for line in table.splitlines()
        if ("accept" in line or "masquerade" in line) and "policy" not in line
    ]
    assert rules == [
        'oifname "clm-ao-up" ct state established,related counter accept',
        f'iifname "clm-ao-up" ip saddr {values["RESOLVER_UPLINK_IP"]} ip daddr '
        f"{values['VPC_RESOLVER_IP']} meta l4proto {{ udp, tcp }} th dport 53 oifname "
        f'"{values["UPLINK_IF"]}" counter accept',
        f'iifname "clm-ao-up" ip saddr {values["PROXY_UPLINK_IP"]} oifname "{values["UPLINK_IF"]}" '
        "tcp dport 443 counter accept",
        'iifname { "clm-ao-up", "clm-ao-ctl" } ct state established,related counter accept',
        f"ip saddr {values['PROXY_UPLINK_IP']} ip daddr != @no_egress_v4 oifname "
        f'"{values["UPLINK_IF"]}" tcp dport 443 counter masquerade',
        f"ip saddr {values['RESOLVER_UPLINK_IP']} ip daddr {values['VPC_RESOLVER_IP']} oifname "
        f'"{values["UPLINK_IF"]}" meta l4proto {{ udp, tcp }} th dport 53 counter masquerade',
    ]
    # The control bridge forwards nothing; the no-egress set equals the guard's.
    assert 'iifname "clm-ao-ctl" counter drop' in table
    assert 'oifname "clm-ao-ctl" counter drop' in table
    elements = re.search(r"elements = \{([^}]*)\}", table)
    assert elements
    assert [e.strip() for e in elements.group(1).split(",")] == list(guard.NO_EGRESS_V4)
    # The DNS drop for the resolver comes before the public-range drop and the 443 accept.
    order = [
        table.index(x)
        for x in (
            "ip saddr 172.30.247.3 counter drop",
            "@no_egress_v4 counter drop",
            "tcp dport 443 counter accept",
        )
    ]
    assert order == sorted(order)


def test_the_e1_and_r3_tables_are_untouched_by_this_lane() -> None:
    e1 = (EGRESS / "clm_r22.nft").read_text("utf-8")
    r3 = (R3 / "host" / "clm_r3.nft").read_text("utf-8")
    for other in (e1, r3):
        assert "clm-ao-" not in other and "172.30.246." not in other and "172.30.247." not in other


def test_the_watcher_is_e1s_with_only_the_table_containers_and_events_renamed() -> None:
    def norm(text: str) -> list[str]:
        body = text.replace("\r\n", "\n").split('"""', 2)[2]  # the code after the docstring
        return body.split("\n")

    e1 = norm((EGRESS / "clm_r22_watch.py").read_text("utf-8"))
    mine = norm((EGRESS / "clm_r22o_watch.py").read_text("utf-8"))
    renamed = [
        line.replace("clm_r22", "clm_r22o")
        .replace("CLM_R22_", "CLM_R22O_")
        .replace(
            "only clm-r22-assistant.service starts it", "only clm-r22o-egress.service starts them"
        )
        for line in e1
    ]
    assert mine == renamed


def test_the_units_start_the_egress_only_behind_the_verified_table() -> None:
    gate = (EGRESS / "clm-r22o-egress.service").read_text("utf-8")
    assert "--check-only" in gate and "is-active -q clm-r22o-firewall-watch.service" in gate
    assert "BindsTo=clm-r22o-egress-firewall.service" in gate
    assert gate.index("--check-only") < gate.index("ExecStart=/usr/bin/docker start")
    assert "docker start clm-staging-openrouter-dns clm-staging-openrouter-egress" in gate
    firewall = (EGRESS / "clm-r22o-egress-firewall.service").read_text("utf-8")
    assert firewall.index("clm_r22o_stop_egress.sh") < firewall.index(
        "nft delete table inet clm_r22o"
    )
    assert "Before=docker.service" in firewall
    watch = (EGRESS / "clm-r22o-firewall-watch.service").read_text("utf-8")
    assert "Restart=always" in watch and "StartLimitIntervalSec=0" in watch
    assert "ExecStopPost=/usr/local/lib/clm-r22o/clm_r22o_stop_egress.sh" in watch
    stop = (EGRESS / "clm_r22o_stop_egress.sh").read_text("utf-8")
    assert "docker stop --time 0 clm-staging-openrouter-egress clm-staging-openrouter-dns" in stop
    containers = _vars(EGRESS / "clm_r22o.vars")["R22O_CONTAINERS"]
    for unit in (gate, watch):
        assert f"--containers {containers}" in unit


def test_the_overlay_matches_the_guard_the_client_and_the_table(guard: ModuleType) -> None:
    overlay = yaml.safe_load(
        (ASSISTANT_DIR / "deploy" / "compose.assistant-openrouter.yml").read_text("utf-8")
    )
    assistant = overlay["services"]["assistant"]
    env = assistant["environment"]
    assert env["ASSISTANT_HOSTING_PROVIDER"] == "openrouter"
    assert env["ASSISTANT_HOSTING_OPENROUTER_PROXY"] == PROXY
    assert openrouter.parse_hosted_proxy(env["ASSISTANT_HOSTING_OPENROUTER_PROXY"]) == PROXY
    assert f"http://{guard.PROXY_CTL_IP}:{guard.PROXY_PORT}" == PROXY
    assert assistant["networks"] == {"openrouter-control": {"ipv4_address": guard.CLIENT_CTL_IP}}
    assert assistant["dns"] == ["192.0.2.53"]
    assert not any("KEY" in name for name in env)
    nets = overlay["networks"]
    assert nets["openrouter-control"]["internal"] is True
    assert nets["openrouter-control"]["ipam"]["config"][0]["subnet"] == str(
        openrouter.HOSTED_PROXY_NETWORK
    )
    up = nets["openrouter-uplink"]
    assert up["driver_opts"]["com.docker.network.bridge.enable_ip_masquerade"] == "false"
    assert (
        up["driver_opts"]["com.docker.network.bridge.name"]
        == _vars(EGRESS / "clm_r22o.vars")["UPLINK_BRIDGE"]
    )
    assert (
        nets["openrouter-control"]["driver_opts"]["com.docker.network.bridge.name"] == "clm-ao-ctl"
    )
    for name, role, ctl, upl in (
        ("openrouter-egress", "proxy", guard.PROXY_CTL_IP, guard.PROXY_UP_IP),
        ("openrouter-dns", "resolver", guard.RESOLVER_CTL_IP, guard.RESOLVER_UP_IP),
    ):
        service = overlay["services"][name]
        assert service["restart"] == "no"
        assert service["environment"] == {
            "CLM_EGRESS_ROLE": role,
            "CLM_EGRESS_FQDN": "openrouter.ai",
        }
        assert service["networks"]["openrouter-control"]["ipv4_address"] == ctl
        assert service["networks"]["openrouter-uplink"]["ipv4_address"] == upl
        assert service["dns"] == [guard.RESOLVER_CTL_IP]
        assert service["cap_drop"] == ["ALL"] and service["read_only"] is True
        assert "ports" not in service
    names = _vars(EGRESS / "clm_r22o.vars")["R22O_CONTAINERS"].split(",")
    assert sorted(
        overlay["services"][n]["container_name"] for n in ("openrouter-egress", "openrouter-dns")
    ) == sorted(names)
    both = yaml.safe_load(
        (ASSISTANT_DIR / "deploy" / "compose.assistant-both.yml").read_text("utf-8")
    )
    assert both["services"]["assistant"]["environment"] == {
        "ASSISTANT_HOSTING_PROVIDER": "anthropic,openrouter"
    }


def test_the_image_reuses_r3s_pins_and_entrypoint() -> None:
    mine = (EGRESS / "openrouter-egress.Dockerfile").read_text("utf-8")
    r3 = (R3 / "Dockerfile").read_text("utf-8")
    pins = re.compile(
        r"(?:@sha256:[0-9a-f]{64}|smokescreen\.git#[0-9a-f]{40}"
        r"|--checksum=sha256:[0-9a-f]{64}|nftables=[^ \n]+)"
    )
    assert set(pins.findall(mine)) == set(pins.findall(r3)) and len(set(pins.findall(mine))) == 5
    assert "COPY --from=r3 smokescreen-main/main.go smokescreen-main/main_test.go" in mine
    assert "go test -count=1 ./r3egress" in mine
    assert "openrouter_egress_guard.py" in mine and "goldtier_egress_guard.py" not in mine
    assert "--unsafe" not in mine


# --- OI-1 (2026-11-15): the A1 networks overlap no other deployment network -------------------

# Networks declared outside this repository on the staging host (recorded, not discoverable from
# the code): the ACRA window lane's acra-uplink and acra-control (D2 package), the R2.2 Claude
# uplink, the main overlay's proxy networks and the Lightsail VPC.
RECORDED_HOST_NETWORKS = (
    "172.30.244.0/29",  # ACRA acra-uplink (D2)
    "172.30.245.0/29",  # ACRA acra-control (D2)
    "172.30.243.0/29",  # R2.2 assistant-uplink (clm-as-up)
    "172.30.249.0/29",  # A6 W-1b probe bridge (temporary, window-only)
    "172.26.0.0/16",  # Lightsail VPC (resolver 172.26.0.2)
)


def _declared_subnets(text: str) -> list[ipaddress.IPv4Network]:
    found = re.findall(r"subnet:\s*\"?(\d+\.\d+\.\d+\.\d+/\d+)", text)
    return [ipaddress.IPv4Network(item) for item in found]


def test_the_a1_networks_overlap_no_other_deployment_network() -> None:
    ours = _declared_subnets((DEPLOY / "compose.assistant-openrouter.yml").read_text("utf-8"))
    assert {str(n) for n in ours} == {"172.30.246.0/29", "172.30.247.0/29"}
    assert str(openrouter.HOSTED_PROXY_NETWORK) == "172.30.246.0/29"
    others: list[ipaddress.IPv4Network] = [ipaddress.IPv4Network(n) for n in RECORDED_HOST_NETWORKS]
    for path in [*REPO.joinpath("deploy").glob("compose*.yml"), *DEPLOY.glob("compose*.yml")]:
        if path.name not in ("compose.assistant-openrouter.yml", "compose.assistant-both.yml"):
            others.extend(_declared_subnets(path.read_text("utf-8")))
    assert others, "no other network found to compare with"
    for mine in ours:
        for other in others:
            assert not mine.overlaps(other), f"{mine} overlaps {other}"


# --- run 2eda4185 (2026-11-16): GPT-OSS gets a usable timeout only in its own overlay ----------


def _environment(name: str) -> dict[str, str]:
    data = yaml.safe_load((DEPLOY / name).read_text("utf-8"))
    return {str(k): str(v) for k, v in data["services"]["assistant"]["environment"].items()}


def test_the_openrouter_overlay_gives_gpt_oss_a_usable_timeout_and_the_baseline_keeps_2_s() -> None:
    # The base overlay's 2 s is for the model-free baseline (the discard port fails at once).
    assert _environment("compose.assistant.yml")["AI_ASSISTANT_LLM_TIMEOUT_SECONDS"] == "2"
    # GPT-OSS needs about 17 s, so its overlay sets the config default it was qualified with.
    assert (
        _environment("compose.assistant-openrouter.yml")["AI_ASSISTANT_LLM_TIMEOUT_SECONDS"] == "90"
    )
    # Claude's overlay leaves it alone (Claude uses anthropic_profiles.TIMEOUT_SECONDS).
    assert "AI_ASSISTANT_LLM_TIMEOUT_SECONDS" not in _environment("compose.assistant-provider.yml")
    # The timeout is part of the GPT-OSS profile identity, so the hosted run must be requalified.
    longer = assistant_config.AiAssistantSettings(_env_file=None, llm_timeout_seconds=90)  # type: ignore[call-arg]
    shorter = assistant_config.AiAssistantSettings(_env_file=None, llm_timeout_seconds=2)  # type: ignore[call-arg]
    assert remote_test.remote_fingerprint(longer) != remote_test.remote_fingerprint(shorter)
