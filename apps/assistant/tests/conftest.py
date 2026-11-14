"""Disable owner dotenv/model configuration before AI Assistant test-module composition.

The whole suite also runs offline: no test may reach a host that is not this machine, and a
real OpenRouter key in the developer's environment is removed (never read) before any test.

B0 storage isolation, set up here because pytest imports this file before any test module
(and ``ai_assistant.main`` builds its app, opening the knowledge store, at import time):
the developer's store settings are removed, the knowledge store goes to a session temporary
folder, and opening any SQLite or Chroma file under a live runtime root is refused (within
the limits listed in docs/integration/AI_MODEL_CONFIGURATION.md section 7.1).
"""

import asyncio
import os
import shutil
import socket
import sqlite3
import tempfile
import threading
import urllib.parse
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
STORE_VARIABLES = (
    "AI_ASSISTANT_DATA_DIR",
    "AI_ASSISTANT_BUDGET_LEDGER_PATH",
    "AI_ASSISTANT_ANTHROPIC_LEDGER_PATH",
    "AI_ASSISTANT_MODEL_ADMIN_DB_PATH",
    "AI_ASSISTANT_MODEL_PROFILES_FILE",
    "AI_ASSISTANT_KNOWLEDGE_DATA_DIR",
)


def _live_roots() -> tuple[str, ...]:
    # The package-relative runtime folder, the documented per-user data roots and any store
    # the developer's environment names (read before those variables are removed below).
    roots = [ASSISTANT_DIR / "data", Path.home() / "Library/Application Support/DataDividendsCLM"]
    if os.environ.get("LOCALAPPDATA"):
        roots.append(Path(os.environ["LOCALAPPDATA"]) / "DataDividendsCLM")
    for name in STORE_VARIABLES:
        value = os.environ.get(name, "").strip()
        if value and Path(value).expanduser().is_absolute():
            roots.append(Path(value).expanduser())
    return tuple(os.path.normcase(os.path.abspath(root)) for root in roots)


LIVE_ROOTS = _live_roots()
for _name in STORE_VARIABLES:
    os.environ.pop(_name, None)
os.environ.pop("AI_ASSISTANT_ANTHROPIC_API_KEY", None)
TEST_DATA_ROOT = Path(tempfile.mkdtemp(prefix="assistant-tests-"))
# Stores a test may reach through the defaults: the knowledge store (ai_assistant.main at
# import), the Claude ledger and the model state database. A test passing its own path still
# wins. The GPT-OSS ledger keeps its package-relative default (test_model_factory pins it);
# like every store, it is refused under a live root (below; see the documented limits).
SESSION_STORES = {
    "AI_ASSISTANT_KNOWLEDGE_DATA_DIR": TEST_DATA_ROOT / "knowledge",
    "AI_ASSISTANT_ANTHROPIC_LEDGER_PATH": TEST_DATA_ROOT / "budget" / "anthropic_ledger.sqlite3",
    "AI_ASSISTANT_MODEL_ADMIN_DB_PATH": TEST_DATA_ROOT / "models" / "model_admin.sqlite3",
}
for _name, _path in SESSION_STORES.items():
    os.environ[_name] = str(_path)


def is_live_storage(path: str | os.PathLike[str]) -> bool:
    """True for a live root itself, anything under it, or a file root's SQLite sidecars."""

    target = os.path.normcase(os.path.abspath(path))
    return any(
        target == root or target.startswith(root + os.sep) or target.startswith(root + "-")
        for root in LIVE_ROOTS
    )


def _sqlite_target(database: object, uri: bool) -> str | None:
    if isinstance(database, bytes):
        database = database.decode("utf-8", "replace")
    text = database if isinstance(database, str) else os.fspath(database)  # type: ignore[call-overload]
    if not uri and not text.startswith("file:"):
        return None if text in ("", ":memory:") else text
    parsed = urllib.parse.urlparse(text)
    if "mode=memory" in parsed.query:
        return None
    path = urllib.parse.unquote(parsed.path)
    if len(path) > 2 and path[0] == "/" and path[2] == ":":  # file:///C:/...
        path = path[1:]
    return None if path in ("", ":memory:") else path


_real_sqlite_connect: Callable[..., sqlite3.Connection] = sqlite3.connect


def _guarded_sqlite_connect(database: Any, *args: Any, **kwargs: Any) -> sqlite3.Connection:
    uri = bool(kwargs.get("uri", args[6] if len(args) > 6 else False))
    target = _sqlite_target(database, uri)
    if target is not None and is_live_storage(target):
        raise PermissionError(f"a test tried to open live runtime storage: {target}")
    return _real_sqlite_connect(database, *args, **kwargs)


sqlite3.connect = _guarded_sqlite_connect  # type: ignore[assignment]

import chromadb  # noqa: E402 (after the guard; vector_index imports it anyway)

_real_persistent_client = chromadb.PersistentClient


def _guarded_persistent_client(path: Any = "./chroma", *args: Any, **kwargs: Any) -> Any:
    if is_live_storage(os.fspath(path)):
        raise PermissionError(f"a test tried to open live runtime storage: {path}")
    return _real_persistent_client(path, *args, **kwargs)


chromadb.PersistentClient = _guarded_persistent_client


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "session_environment: keep the session's isolated store settings"
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    shutil.rmtree(TEST_DATA_ROOT, ignore_errors=True)


from ai_assistant import (  # noqa: E402
    anthropic_runtime,
    key_sources,
    remote_test,
    synthetic_eligibility,
)
from ai_assistant.config import AiAssistantSettings  # noqa: E402

AiAssistantSettings.model_config = {**AiAssistantSettings.model_config, "env_file": None}
os.environ["AI_ASSISTANT_LLM_ENABLED"] = "false"
os.environ["AI_ASSISTANT_CLM_BACKEND_URL"] = "http://127.0.0.1:1"
# Phase A2 (D-091, proposed): tests use sentinel keys passed explicitly, never this variable.
os.environ.pop("OPENROUTER_API_KEY", None)
# D-095 addendum: the owner's apps/assistant/.env is never read by a test (it may hold a key).
key_sources.ENV_FILE = key_sources.ENV_FILE.with_name(".env.test-suite-never-read")


@pytest.fixture(scope="session", autouse=True)
def exact_lines_unless_a_test_opts_in() -> Iterator[None]:
    """D-122 turned conversational answers on. Tests of the exact-line rollback run without
    it; a test of conversational answers sets the decision itself."""

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("ai_assistant.config.CONVERSATIONAL_DECISION", None)
        yield


@pytest.fixture(autouse=True)
def fresh_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Every test starts with no .env key, empty HR key stores and no HR session check."""

    monkeypatch.setattr(key_sources, "ENV_FILE", tmp_path / "no-such.env")
    monkeypatch.setattr(key_sources, "HR_STORE", key_sources.HrCredential())
    monkeypatch.setattr(key_sources, "ANTHROPIC_STORE", key_sources.HrCredential())
    monkeypatch.setattr(key_sources, "_SESSION_CHECK", None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    synthetic_eligibility._tickets.clear()  # D-095 tickets never carry over between tests
    # R2.2: no test starts as a registered hosted deployment (a fresh process starts none).
    monkeypatch.setattr(anthropic_runtime, "_hosted", None)


@pytest.fixture(autouse=True)
def no_carried_over_runs() -> None:
    """A qualification an earlier test started and did not wait for must not touch this one.

    Its background thread can finish during the next test and change a process-wide provider
    reading (OpenRouter's remote_test._provider, Claude's anthropic_runtime._last), so a test
    saw a reading present or cleared that it did not make (hosted CI, intermittently). Wait for
    such threads, bounded, then start from empty readings, as a fresh process would.
    """

    for thread in threading.enumerate():
        if thread.name == "model-qualification":
            thread.join(30)
            if thread.is_alive():
                warnings.warn(
                    "a model-qualification thread from an earlier test is still running",
                    stacklevel=1,
                )
    remote_test.forget_provider()
    with anthropic_runtime._last_lock:
        anthropic_runtime._last.clear()


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
