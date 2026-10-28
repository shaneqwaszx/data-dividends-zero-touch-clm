"""Disable owner dotenv/model configuration before AI Assistant test-module composition.

The whole suite also runs offline: no test may reach a host that is not this machine, and a
real OpenRouter key in the developer's environment is removed (never read) before any test.
"""

import asyncio
import os
import socket
from collections.abc import Iterator
from typing import Any

import pytest

from ai_assistant import key_sources, synthetic_eligibility
from ai_assistant.config import AiAssistantSettings

AiAssistantSettings.model_config = {**AiAssistantSettings.model_config, "env_file": None}
os.environ["AI_ASSISTANT_LLM_ENABLED"] = "false"
os.environ["AI_ASSISTANT_CLM_BACKEND_URL"] = "http://127.0.0.1:1"
# Phase A2 (D-091, proposed): tests use sentinel keys passed explicitly, never this variable.
os.environ.pop("OPENROUTER_API_KEY", None)
# D-095 addendum: the owner's apps/assistant/.env is never read by a test (it may hold a key).
key_sources.ENV_FILE = key_sources.ENV_FILE.with_name(".env.test-suite-never-read")


@pytest.fixture(autouse=True)
def fresh_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Every test starts with no .env key and an empty HR key store."""

    monkeypatch.setattr(key_sources, "ENV_FILE", tmp_path / "no-such.env")
    monkeypatch.setattr(key_sources, "HR_STORE", key_sources.HrCredential())
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    synthetic_eligibility._tickets.clear()  # D-095 tickets never carry over between tests


LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class SuiteRemoteConnectionBlocked(AssertionError):
    """A test tried to reach a host that is not this machine."""


@pytest.fixture(scope="session", autouse=True)
def no_remote_connections() -> Iterator[list[str]]:
    """Fail on any attempt to reach a non-loopback host: blocking and non-blocking sockets,
    asyncio connections (the async HTTP client) and name lookups. Only the kind of attempt
    is kept, never the address."""

    attempts: list[str] = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo
    real_create_connection = asyncio.base_events.BaseEventLoop.create_connection

    def check(host: object, kind: str) -> None:
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host is not None and host not in LOOPBACK_HOSTS:
            attempts.append(kind)
            raise SuiteRemoteConnectionBlocked("a test tried to reach a remote host")

    def connect(self: socket.socket, address: Any) -> None:
        check(address[0] if isinstance(address, tuple) else None, "connect")
        real_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        check(address[0] if isinstance(address, tuple) else None, "connect_ex")
        return real_connect_ex(self, address)

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        check(host, "getaddrinfo")
        return real_getaddrinfo(host, *args, **kwargs)

    async def create_connection(self: Any, *args: Any, **kwargs: Any) -> Any:
        check(kwargs.get("host", args[1] if len(args) > 1 else None), "create_connection")
        return await real_create_connection(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, "connect", connect)
        patch.setattr(socket.socket, "connect_ex", connect_ex)
        patch.setattr(socket, "getaddrinfo", getaddrinfo)
        patch.setattr(asyncio.base_events.BaseEventLoop, "create_connection", create_connection)
        yield attempts
    assert attempts == [], "a test tried to reach a remote host"
