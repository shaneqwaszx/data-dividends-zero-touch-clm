"""Start the hosted service: check, lock, verify the stores, load guidance, then run uvicorn.

Exit codes tell an operator what happened without printing any value:

    78  the configuration was refused
    75  another writer holds this data root
    70  a store failed its integrity check (it is never repaired or recreated here)
"""

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from ai_assistant.config import AiAssistantSettings

from .profile import refusals

LOCK_NAME = ".assistant.lock"
PID_FILE = Path("/tmp/assistant.pid")  # noqa: S108 (a private tmpfs in the container)
EXIT_CONFIG = 78
EXIT_LOCKED = 75
EXIT_CORRUPT = 70
SERVER_ARGUMENTS = (
    "-m",
    "uvicorn",
    "assistant_hosting.app:app",
    "--host",
    "0.0.0.0",  # noqa: S104 (reachable only on the internal network; no port is published)
    "--port",
    "8100",
    # One worker: chat contexts, tickets and the SQLite writers belong to one process.
    "--workers",
    "1",
    # Peers are never trusted for forwarded addresses: /internal must see the real peer.
    "--no-proxy-headers",
    "--no-server-header",
    "--no-access-log",
    "--timeout-graceful-shutdown",
    "20",
    "--timeout-keep-alive",
    "30",
    "--limit-concurrency",
    "32",
    "--backlog",
    "64",
)


def hold_lock(root: Path) -> int | None:
    """An exclusive lock on the data root, kept across exec. None when another writer has it."""

    if sys.platform == "win32":  # the service runs in a Linux container
        raise OSError("file locks need Linux")
    import fcntl

    descriptor = os.open(root / LOCK_NAME, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(descriptor)
        return None
    os.set_inheritable(descriptor, True)
    return descriptor


def stores(root: Path) -> list[Path]:
    return sorted(root.rglob("*.sqlite3"))


def damaged(root: Path) -> list[str]:
    """Names of stores that fail SQLite's own check, relative to the root."""

    found: list[str] = []
    for path in stores(root):
        try:
            connection = sqlite3.connect(path, timeout=5)
            try:
                result = connection.execute("PRAGMA quick_check").fetchone()
            finally:
                connection.close()
        except sqlite3.Error:
            found.append(path.relative_to(root).as_posix())
            continue
        if result is None or result[0] != "ok":
            found.append(path.relative_to(root).as_posix())
    return found


def load_guidance(settings: AiAssistantSettings, *, seed: bool) -> dict[str, Any]:
    """Repeatable: unchanged guidance is skipped, and an app-approved edit is kept."""

    from ai_assistant.knowledge.factory import build_knowledge_base
    from ai_assistant.knowledge.ingest import ingest_guidance, ingest_synthetic_resolutions

    kb = build_knowledge_base(settings)
    report = ingest_guidance(kb)
    counts: dict[str, Any] = {
        "guidance_added": len(report.added),
        "guidance_unchanged": len(report.unchanged),
    }
    if seed:
        counts["seed_added"] = len(ingest_synthetic_resolutions(kb).added)
    return counts


def main() -> int:
    settings = AiAssistantSettings()
    codes = refusals(settings)
    if codes:
        print("REFUSED " + ",".join(codes), flush=True)
        return EXIT_CONFIG
    root = Path(settings.data_dir)
    if hold_lock(root) is None:
        print("REFUSED DATA_ROOT_IN_USE", flush=True)
        return EXIT_LOCKED
    bad = damaged(root)
    if bad:
        print("REFUSED STORE_DAMAGED " + ",".join(bad), flush=True)
        return EXIT_CORRUPT
    seed = os.environ.get("ASSISTANT_HOSTING_SEED_SYNTHETIC", "false") == "true"
    print(f"BOOTSTRAP {load_guidance(settings, seed=seed)}", flush=True)
    PID_FILE.write_text(str(os.getpid()), encoding="ascii")
    os.execv(sys.executable, [sys.executable, *SERVER_ARGUMENTS])  # noqa: S606


if __name__ == "__main__":
    sys.exit(main())
