"""Bound local child processes without collecting unbounded stdout or private stderr."""

import subprocess
import sys
from collections.abc import Mapping, Sequence
from threading import Event, Thread

from app.connectors.idp import LocalDocumentProcessingError


def run_bounded_process(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    output_limit: int,
    unavailable_code: str,
    timeout_code: str,
    failed_code: str,
    failed_codes: Mapping[int, str] | None = None,
) -> bytes:
    """Arguments are constructed by backend adapters; no shell or user filenames.

    ``failed_codes`` maps a child's fixed exit code to an application-owned error code;
    any other non-zero exit (including signals, which are negative) uses ``failed_code``.
    """

    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=(
                int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if sys.platform == "win32" else 0
            ),
        )
    except OSError:
        raise LocalDocumentProcessingError(unavailable_code) from None
    output = bytearray()
    exceeded = Event()

    def consume() -> None:
        assert process.stdout is not None
        try:
            while chunk := process.stdout.read(16384):
                if len(output) + len(chunk) > output_limit:
                    exceeded.set()
                    process.kill()
                    break
                output.extend(chunk)
        except OSError:
            exceeded.set()
        finally:
            process.stdout.close()

    reader = Thread(target=consume, daemon=True)
    reader.start()
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        reader.join(timeout=2)
        raise LocalDocumentProcessingError(timeout_code) from None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    reader.join(timeout=2)
    if exceeded.is_set() or reader.is_alive():
        raise LocalDocumentProcessingError("DOCUMENT_OUTPUT_LIMIT_EXCEEDED")
    if process.returncode != 0:
        raise LocalDocumentProcessingError(
            (failed_codes or {}).get(process.returncode, failed_code)
        )
    return bytes(output)
