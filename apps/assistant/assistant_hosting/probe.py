"""The container health check, with recovery from a hung worker.

Docker marks a failing container unhealthy but does not restart it. After enough consecutive
failures this ends the worker, so the restart policy brings it back. SQLite recovers from its
own journal on the next open, and the only state lost is what is already memory-only: chat
contexts and tickets.
"""

import contextlib
import os
import signal
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .run import PID_FILE

URL = "http://127.0.0.1:8100/internal/live"
COUNTER = Path("/tmp/assistant.probe")  # noqa: S108 (a private tmpfs in the container)
FAILURES_BEFORE_RESTART = 9
# SIGKILL: a hung worker will not answer SIGTERM. (The fallback only lets tests import this.)
HARD_STOP = getattr(signal, "SIGKILL", signal.SIGTERM)


def alive(url: str = URL, timeout: float = 3.0) -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=timeout) as response:
            return bool(response.status == 200)
    except (urllib.error.URLError, OSError):
        return False


def failures(counter: Path = COUNTER) -> int:
    try:
        return int(counter.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return 0


def check(
    *,
    healthy: bool,
    counter: Path = COUNTER,
    pid_file: Path = PID_FILE,
    limit: int = FAILURES_BEFORE_RESTART,
) -> int:
    if healthy:
        counter.unlink(missing_ok=True)
        return 0
    # Before the worker starts there is no pid file: bootstrap time is never counted.
    if not pid_file.is_file():
        return 1
    count = failures(counter) + 1
    if count < limit:
        counter.write_text(str(count), encoding="ascii")
        return 1
    counter.unlink(missing_ok=True)
    with contextlib.suppress(OSError, ValueError):
        os.kill(int(pid_file.read_text(encoding="ascii")), HARD_STOP)
    return 1


if __name__ == "__main__":
    sys.exit(check(healthy=alive()))
