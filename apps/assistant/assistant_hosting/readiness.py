"""Liveness and readiness for the hosted service. Closed codes only, never a path or value."""

import os
import shutil
import sqlite3
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from ai_assistant.config import AiAssistantSettings

from .profile import Limits

USAGE_CACHE_SECONDS = 60.0


def data_usage(root: Path) -> int:
    total = 0
    for folder, _, files in os.walk(root):
        for name in files:
            try:
                total += os.lstat(os.path.join(folder, name)).st_size
            except OSError:
                continue
    return total


def _read_store(path: Path) -> str:
    if not path.is_file():
        return "missing"
    try:
        connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=2)
        try:
            connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        finally:
            connection.close()
    except sqlite3.Error:
        return "unreadable"
    return "ok"


def _write_probe(root: Path) -> str:
    probe = root / f".ready-{uuid.uuid4().hex}"
    try:
        with probe.open("wb") as handle:
            handle.write(b"ready")
            handle.flush()
            os.fsync(handle.fileno())
        probe.unlink()
    except OSError:
        return "not_writable"
    return "ok"


class Readiness:
    def __init__(
        self,
        settings: AiAssistantSettings,
        bounds: Limits,
        *,
        knowledge_open: Callable[[], bool],
        model_state: Callable[[], int],
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._bounds = bounds
        self._root = Path(settings.data_dir)
        self._knowledge_open = knowledge_open
        self._model_state = model_state
        self._transport = transport
        self._usage: tuple[float, int] | None = None

    def _cached_usage(self) -> int:
        now = time.monotonic()
        if self._usage is None or now - self._usage[0] > USAGE_CACHE_SECONDS:
            self._usage = (now, data_usage(self._root))
        return self._usage[1]

    def _backend(self) -> str:
        try:
            with httpx.Client(
                base_url=self._settings.clm_backend_url,
                timeout=2.0,
                transport=self._transport,
                trust_env=False,
            ) as client:
                response = client.get("/health")
        except httpx.HTTPError:
            return "unreachable"
        return "ok" if response.status_code == 200 else "unhealthy"

    def _model_store(self) -> str:
        try:
            self._model_state()
        except Exception:  # noqa: BLE001 - any failure to read is the same closed state
            return "unreadable"
        return "ok"

    def report(self) -> dict[str, Any]:
        knowledge = Path(self._settings.knowledge_data_dir)
        checks = {
            "data_root": _write_probe(self._root),
            "disk_free": "ok"
            if shutil.disk_usage(self._root).free >= self._bounds.min_free_bytes
            else "low",
            "data_quota": "ok"
            if self._cached_usage() <= self._bounds.data_quota_bytes
            else "exceeded",
            "knowledge_store": _read_store(knowledge / "knowledge.sqlite3"),
            "vector_index": _read_store(knowledge / "chroma" / "chroma.sqlite3"),
            "knowledge_service": "ok" if self._knowledge_open() else "unavailable",
            "model_state": self._model_store(),
            "clm_backend": self._backend(),
        }
        ready = all(value == "ok" for value in checks.values())
        return {"status": "ready" if ready else "not_ready", "checks": checks}
