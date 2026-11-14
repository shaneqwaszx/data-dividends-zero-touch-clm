"""R2.2 (D-129 proposed): the hosted service's one provider mode, Claude through Anthropic.

Off unless ``ASSISTANT_HOSTING_PROVIDER`` names it. Every Stage A refusal still applies (no
decision setting, no provider key, proxy or profile in the environment): Claude is set up only
by an HR administrator in AI Models (D-107), with the key held in memory for that HR session
(D-106). This module adds what the hosted mode needs on top:

    the owner's hosted lifetime ceiling   required, 1 to the D-102 US$30.00 ceiling; the hosted
                                          ledger counts only this deployment's calls
    exactly one HTTPS browser origin      the origin the Claude runtime is registered for
    the pinned provider address           api.anthropic.com must resolve, inside the container,
                                          only to Anthropic's published inbound IPv4 ranges (the
                                          E1 hosts-file pin); never DNS, never IPv6

The registration happens before ai_assistant.main is imported, so a restart restores an active
Claude configuration under the same conditions. Refusal codes are closed; no value is printed.
"""

import ipaddress
import os
import socket
from collections.abc import Callable, Mapping, Sequence

from ai_assistant import anthropic_runtime
from ai_assistant.config import AiAssistantSettings

PROVIDER_VARIABLE = "ASSISTANT_HOSTING_PROVIDER"
CEILING_VARIABLE = "ASSISTANT_HOSTING_CLAUDE_LIFETIME_CAP_MICRO_USD"
ANTHROPIC = "anthropic"
PROVIDER_HOST = "api.anthropic.com"
# Anthropic's published inbound API ranges (platform.claude.com/docs/en/api/ip-addresses, read
# 2026-11-13: fixed, "will not change without notice"). IPv6 2607:6bc0::/48 is deliberately not
# used: the assistant's uplink network has IPv6 disabled.
ANTHROPIC_INBOUND_V4 = (
    ipaddress.ip_network("160.79.104.0/23"),
    ipaddress.ip_network("153.61.224.0/22"),
)

Resolver = Callable[[str], Sequence[str]]


def mode(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    return env.get(PROVIDER_VARIABLE, "").strip()


def enabled(environ: Mapping[str, str] | None = None) -> bool:
    return mode(environ) == ANTHROPIC


def system_resolver(host: str) -> list[str]:
    # What the process itself would connect to (the hosts file first, as httpx does).
    try:
        found = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return []
    return sorted({str(item[4][0]) for item in found})


def pinned(addresses: Sequence[str]) -> bool:
    if not addresses:
        return False
    for text in addresses:
        try:
            address = ipaddress.ip_address(text)
        except ValueError:
            return False
        if address.version != 4 or not any(address in net for net in ANTHROPIC_INBOUND_V4):
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


def config_codes(
    settings: AiAssistantSettings,
    environ: Mapping[str, str] | None = None,
    *,
    resolve: Resolver | None = None,
) -> list[str]:
    """Why the provider mode may not start (empty: off, or it may)."""

    env = os.environ if environ is None else environ
    name = mode(env)
    if not name:
        return [] if CEILING_VARIABLE not in env else ["PROVIDER_SETTING_WITHOUT_MODE"]
    if name != ANTHROPIC:
        return ["PROVIDER_MODE_INVALID"]
    found: list[str] = []
    if ceiling(env) is None:
        found.append("HOSTED_CEILING_REQUIRED")
    if len(settings.allowed_origins) != 1:
        found.append("ONE_ORIGIN_REQUIRED")
    if not pinned((resolve or system_resolver)(PROVIDER_HOST)):
        found.append("PROVIDER_PIN_REQUIRED")
    return found


def install(settings: AiAssistantSettings, environ: Mapping[str, str] | None = None) -> bool:
    """Register the hosted deployment with the Claude runtime (True), or do nothing when the
    mode is off (False). Call only after refusals() returned nothing; raises otherwise."""

    env = os.environ if environ is None else environ
    if not enabled(env):
        return False
    value = ceiling(env)
    if value is None or len(settings.allowed_origins) != 1:
        raise ValueError("provider mode not configured")
    anthropic_runtime.register_hosted_deployment(settings.allowed_origins[0].rstrip("/"), value)
    return True
