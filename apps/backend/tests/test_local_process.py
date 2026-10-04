"""Focused platform-flag contract for the bounded local process owner."""

from io import BytesIO
from types import SimpleNamespace

import pytest

from app.connectors import local_process


@pytest.mark.parametrize(
    ("platform", "constant_available", "expected_flags"),
    [
        ("win32", True, 0x08000000),
        ("win32", False, 0),
        ("linux", True, 0),
        ("linux", False, 0),
        ("darwin", True, 0),
        ("darwin", False, 0),
    ],
)
def test_platform_creation_flags_preserve_bounded_process_contract(
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    constant_available: bool,
    expected_flags: int,
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    waits: list[float | None] = []

    class SuccessfulProcess:
        def __init__(self, command: list[str], **kwargs: object) -> None:
            calls.append((command, kwargs))
            self.stdout = BytesIO(b"bounded result")
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            waits.append(timeout)
            return self.returncode

        def poll(self) -> int:
            return self.returncode

        def kill(self) -> None:
            pytest.fail("A successful bounded process must not be killed")

    process_module = SimpleNamespace(
        Popen=SuccessfulProcess,
        PIPE=local_process.subprocess.PIPE,
        DEVNULL=local_process.subprocess.DEVNULL,
        TimeoutExpired=local_process.subprocess.TimeoutExpired,
    )
    if constant_available:
        process_module.CREATE_NO_WINDOW = 0x08000000
    monkeypatch.setattr(local_process, "subprocess", process_module)
    monkeypatch.setattr(local_process, "sys", SimpleNamespace(platform=platform))

    result = local_process.run_bounded_process(
        ("synthetic-engine", "--safe-argument"),
        timeout_seconds=3.5,
        output_limit=32,
        unavailable_code="UNAVAILABLE",
        timeout_code="TIMEOUT",
        failed_code="FAILED",
    )

    assert result == b"bounded result"
    assert waits == [3.5]
    assert calls == [
        (
            ["synthetic-engine", "--safe-argument"],
            {
                "stdin": process_module.DEVNULL,
                "stdout": process_module.PIPE,
                "stderr": process_module.DEVNULL,
                "shell": False,
                "creationflags": expected_flags,
            },
        )
    ]
