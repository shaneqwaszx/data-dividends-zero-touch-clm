"""The hosted service's provider modes: a small closed set of provider adapters.

    anthropic    R2.2 (D-129 proposed): Claude through Anthropic. Unchanged by D-134.

Neither mode starts while config.HOSTED_TRANSMISSION_DECISION is None (TRANSMISSION_DECISION_
REQUIRED): the owner's acceptance of D-129 must be recorded in the code first.
    openrouter   D-134 (PROPOSED, NOT ACTIVE): GPT-OSS 120B through OpenRouter, case chat only.
                 Not a known mode at all while config.HOSTED_OPENROUTER_DECISION is None (the
                 name refuses the start as PROVIDER_MODE_INVALID, as before D-134). D-138 A1
                 (proposed): its egress is the exact-host proxy, never an address pin.

Off unless ``ASSISTANT_HOSTING_PROVIDER`` names one mode, or both separated by a comma. Any other
value, a repeated name or an empty part refuses the start. Naming both modes never joins them:
each model keeps its own adapter, key, ledger, limits and qualification, the administrator
selects exactly one active model in AI Models, and a failed, refused or exhausted model is
answered from the case data. Nothing here falls back from one provider to the other.

Every Stage A refusal still applies. A model is set up only by an HR administrator in AI Models,
with the key held in memory for that HR session (D-106). This module adds what a mode needs on
top.

Anthropic mode:

    the owner's hosted lifetime ceiling   required, 1 to the D-102 US$30.00 ceiling; the hosted
                                          ledger counts only this deployment's calls
    exactly one HTTPS browser origin      the origin the Claude runtime is registered for
    the pinned provider address           api.anthropic.com must resolve, inside the container,
                                          only to Anthropic's published inbound IPv4 ranges (the
                                          E1 hosts-file pin); never DNS, never IPv6

OpenRouter mode (each one required; a missing one refuses the start):

    the owner's decision in the code      config.HOSTED_OPENROUTER_DECISION (None today, so
                                          the mode's name itself is refused)
    OpenRouter's transmission decision    D-138 A1: config.HOSTED_OPENROUTER_TRANSMISSION_
                                          DECISION (None today), on top of D-129's
                                          HOSTED_TRANSMISSION_DECISION, which covers Anthropic
                                          only (OPENROUTER_TRANSMISSION_DECISION_REQUIRED)
    the owner's hosted daily ceiling      1 micro-USD to US$3.00 a Singapore day; registered in
                                          the ledger module, so no HR value or caller admits more
    exactly one HTTPS browser origin      the origin the GPT-OSS runtime is registered for
    the remote profile, fully named       the D-091, D-092 and D-094 decision names, the owner's
                                          two attestations, the approved endpoint and valid
                                          reasoning settings (remote_test.readiness); nothing
                                          else in the remote settings
    the exact-host egress proxy           D-138 A1 (proposed). OpenRouter publishes no fixed
                                          address range, so nothing is pinned. Instead
                                          ASSISTANT_HOSTING_OPENROUTER_PROXY must be exactly
                                          http://<IPv4>:4750, the address inside the reviewed
                                          internal network (OPENROUTER_PROXY_REQUIRED); the
                                          kernel must reach it directly from that network, not
                                          through a gateway (OPENROUTER_PROXY_NOT_INTERNAL);
                                          and openrouter.ai must not resolve inside the
                                          container at all, so nothing reaches it except
                                          through the proxy (OPENROUTER_DIRECT_PATH_REFUSED).
                                          The proxy (CONNECT openrouter.ai:443 only) and the
                                          host table inet clm_r22o enforce the rest outside
                                          this process (deploy/egress/README.md)

The registration happens before ai_assistant.main is imported, so a restart restores an active
configuration under the same conditions. Refusal codes are closed; no value is printed.
"""

import ipaddress
import os
import socket
from collections.abc import Callable, Mapping, Sequence

from ai_assistant import anthropic_runtime, openrouter, remote_test
from ai_assistant import config as assistant_config
from ai_assistant.budget import GPT_OSS_DAILY_CEILING_MICRO_USD
from ai_assistant.config import AiAssistantSettings

PROVIDER_VARIABLE = "ASSISTANT_HOSTING_PROVIDER"
CEILING_VARIABLE = "ASSISTANT_HOSTING_CLAUDE_LIFETIME_CAP_MICRO_USD"
DAILY_CAP_VARIABLE = "ASSISTANT_HOSTING_GPTOSS_DAILY_CAP_MICRO_USD"
PROXY_VARIABLE = "ASSISTANT_HOSTING_OPENROUTER_PROXY"
ANTHROPIC = "anthropic"
OPENROUTER = "openrouter"
MODES = (ANTHROPIC, OPENROUTER)
PROVIDER_HOST = "api.anthropic.com"
OPENROUTER_HOST = "openrouter.ai"
# Anthropic's published inbound API ranges (platform.claude.com/docs/en/api/ip-addresses, read
# 2026-11-13: fixed, "will not change without notice"). IPv6 2607:6bc0::/48 is deliberately not
# used: the assistant's uplink network has IPv6 disabled.
ANTHROPIC_INBOUND_V4 = (
    ipaddress.ip_network("160.79.104.0/23"),
    ipaddress.ip_network("153.61.224.0/22"),
)
# D-138 A1 replaces D-134's empty OPENROUTER_INBOUND_V4 pin: OpenRouter publishes no fixed
# inbound range, and Cloudflare's ranges would admit any Cloudflare-fronted site, so the
# OpenRouter mode's egress is the exact-host proxy instead (see the header).
# The remote settings the OpenRouter mode needs named (profile.py refuses them in every other
# configuration). Their values are checked by remote_test.readiness, never accepted as given.
OPENROUTER_SETTINGS = frozenset(
    {
        "remote_inference_decision",
        "remote_live_decision",
        "openrouter_endpoint",
        "local_api_test_decision",
        "local_api_test_owner_attests",
    }
)

Resolver = Callable[[str], Sequence[str]]
# The source address the kernel would use to reach (address, port), or None.
LocalSource = Callable[[str, int], str | None]
Networks = Sequence[ipaddress.IPv4Network | ipaddress.IPv6Network]


def mode(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return env.get(PROVIDER_VARIABLE, "").strip()


def known_modes() -> tuple[str, ...]:
    # The OpenRouter mode exists only while the owner's decision is in the code.
    if assistant_config.HOSTED_OPENROUTER_DECISION is None:
        return (ANTHROPIC,)
    return MODES


def modes(environ: Mapping[str, str] | None = None) -> tuple[str, ...] | None:
    """The named modes in a fixed order; () when off; None when the value is not exactly one or
    more distinct known names."""

    raw = mode(environ)
    if not raw:
        return ()
    known = known_modes()
    names = [part.strip() for part in raw.split(",")]
    if len(set(names)) != len(names) or not all(name in known for name in names):
        return None
    return tuple(name for name in known if name in names)


def enabled(environ: Mapping[str, str] | None = None) -> bool:
    return ANTHROPIC in (modes(environ) or ())


def openrouter_enabled(environ: Mapping[str, str] | None = None) -> bool:
    return OPENROUTER in (modes(environ) or ())


def system_resolver(host: str) -> list[str]:
    # What the process itself would connect to (the hosts file first, as httpx does).
    try:
        found = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return []
    return sorted({str(item[4][0]) for item in found})


def system_local_source(address: str, port: int) -> str | None:
    # A UDP connect sends nothing; it only asks the kernel which route and source it would use.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((address, port))
            return str(probe.getsockname()[0])
    except OSError:
        return None


def openrouter_proxy(environ: Mapping[str, str]) -> str | None:
    """The hosted OpenRouter egress proxy URL in its one accepted spelling, or None."""

    return openrouter.parse_hosted_proxy(environ.get(PROXY_VARIABLE, ""))


def proxy_internal(url: str, local_source: LocalSource) -> bool:
    """True when the kernel reaches the proxy directly from another address on the same
    internal network; a route through a gateway or any other interface is refused."""

    address, port = url.removeprefix("http://").rsplit(":", 1)
    source = local_source(address, int(port))
    if source is None:
        return False
    try:
        mine = ipaddress.ip_address(source)
    except ValueError:
        return False
    network = openrouter.HOSTED_PROXY_NETWORK
    return (
        mine.version == 4
        and mine in network
        and str(mine) != address
        and mine not in (network.network_address, network.network_address + 1)
        and mine != network.broadcast_address
    )


def pinned(addresses: Sequence[str], networks: Networks = ANTHROPIC_INBOUND_V4) -> bool:
    if not addresses:
        return False
    for text in addresses:
        try:
            address = ipaddress.ip_address(text)
        except ValueError:
            return False
        if address.version != 4 or not any(address in net for net in networks):
            return False
    return True


def ceiling(environ: Mapping[str, str]) -> int | None:
    raw = environ.get(CEILING_VARIABLE, "").strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    if not 1 <= value <= anthropic_runtime.LIFETIME_CEILING_MICRO_USD:
        return None
    return value


def daily_cap(environ: Mapping[str, str]) -> int | None:
    """The owner's hosted GPT-OSS daily ceiling: 1 micro-USD to US$3.00, or None."""

    raw = environ.get(DAILY_CAP_VARIABLE, "").strip()
    if not raw.isascii() or not raw.isdigit():
        return None
    value = int(raw)
    if not 1 <= value <= GPT_OSS_DAILY_CEILING_MICRO_USD:
        return None
    return value


def _anthropic_codes(
    settings: AiAssistantSettings, env: Mapping[str, str], resolve: Resolver
) -> list[str]:
    found: list[str] = []
    if ceiling(env) is None:
        found.append("HOSTED_CEILING_REQUIRED")
    if len(settings.allowed_origins) != 1:
        found.append("ONE_ORIGIN_REQUIRED")
    if not pinned(resolve(PROVIDER_HOST)):
        found.append("PROVIDER_PIN_REQUIRED")
    return found


def _openrouter_codes(
    settings: AiAssistantSettings,
    env: Mapping[str, str],
    resolve: Resolver,
    local_source: LocalSource,
) -> list[str]:
    found: list[str] = []
    if daily_cap(env) is None:
        found.append("HOSTED_DAILY_CAP_REQUIRED")
    if len(settings.allowed_origins) != 1:
        found.append("ONE_ORIGIN_REQUIRED")
    if remote_test.readiness(settings, environment=False) is not None:
        found.append("OPENROUTER_SETTINGS_REQUIRED")
    # D-138 A1: the exact-host proxy is the only way out, and it is on the internal network.
    proxy = openrouter_proxy(env)
    if proxy is None:
        found.append("OPENROUTER_PROXY_REQUIRED")
    elif not proxy_internal(proxy, local_source):
        found.append("OPENROUTER_PROXY_NOT_INTERNAL")
    if resolve(OPENROUTER_HOST):
        found.append("OPENROUTER_DIRECT_PATH_REFUSED")
    return found


def config_codes(
    settings: AiAssistantSettings,
    environ: Mapping[str, str] | None = None,
    *,
    resolve: Resolver | None = None,
    local_source: LocalSource | None = None,
) -> list[str]:
    """Why the provider modes may not start (empty: off, or they may)."""

    env = os.environ if environ is None else environ
    names = modes(env)
    if names is None:
        return ["PROVIDER_MODE_INVALID"]
    resolver = resolve or system_resolver
    found: list[str] = []
    # D-129: no provider mode starts until the owner's acceptance is recorded in the code.
    if names and assistant_config.HOSTED_TRANSMISSION_DECISION is None:
        found.append("TRANSMISSION_DECISION_REQUIRED")
    if ANTHROPIC in names:
        found.extend(_anthropic_codes(settings, env, resolver))
    elif CEILING_VARIABLE in env:
        found.append("PROVIDER_SETTING_WITHOUT_MODE")
    if OPENROUTER in names:
        # D-138 A1: OpenRouter's own transmission decision; D-129 covers Anthropic only.
        if assistant_config.HOSTED_OPENROUTER_TRANSMISSION_DECISION is None:
            found.append("OPENROUTER_TRANSMISSION_DECISION_REQUIRED")
        source = local_source or system_local_source
        found.extend(_openrouter_codes(settings, env, resolver, source))
    elif DAILY_CAP_VARIABLE in env or PROXY_VARIABLE in env:
        found.append("PROVIDER_SETTING_WITHOUT_MODE")
    return found


def install(settings: AiAssistantSettings, environ: Mapping[str, str] | None = None) -> bool:
    """Register the hosted deployment with each named mode's runtime (True), or do nothing when
    no mode is named (False). Call only after refusals() returned nothing; raises otherwise."""

    env = os.environ if environ is None else environ
    names = modes(env)
    if names is None:
        raise ValueError("provider mode not configured")
    if not names:
        return False
    if len(settings.allowed_origins) != 1:
        raise ValueError("provider mode not configured")
    origin = settings.allowed_origins[0].rstrip("/")
    if ANTHROPIC in names:
        value = ceiling(env)
        if value is None:
            raise ValueError("provider mode not configured")
        anthropic_runtime.register_hosted_deployment(origin, value)
    if OPENROUTER in names:
        daily = daily_cap(env)
        proxy = openrouter_proxy(env)
        if daily is None or proxy is None:
            raise ValueError("provider mode not configured")
        # D-138 A1: the egress proxy first, so the deployment is never registered without it.
        openrouter.register_hosted_proxy(proxy)
        remote_test.register_hosted_deployment(origin, daily)
    return True
