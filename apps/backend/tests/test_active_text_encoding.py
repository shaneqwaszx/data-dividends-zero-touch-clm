"""Guard only tracked application text and the current automation-policy contract."""

import subprocess
from pathlib import Path

import pytest
from test_zero_touch_orchestration import build_system, start_demo

ACTIVE_PATHS = (
    "apps/backend/app",
    "apps/frontend/src",
    "docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md",
)
CORRUPT_CODEPOINTS = (
    (0xE2, 0x20AC, 0x201D),
    (0xE2, 0x20AC, 0xA2),
    (0xC2, 0xB7),
    (0xEF, 0xBF, 0xBD),
    (0xFFFD,),
)


def encoding_faults(payload: bytes) -> list[int]:
    """Return corrupt line numbers; never expose the source text in diagnostics."""
    text = payload.decode("utf-8", errors="strict")
    patterns = tuple("".join(map(chr, points)) for points in CORRUPT_CODEPOINTS)
    return [
        index
        for index, line in enumerate(text.splitlines(), start=1)
        if any(pattern in line for pattern in patterns)
    ]


def test_tracked_active_text_has_no_demonstrated_encoding_corruption() -> None:
    root = Path(__file__).resolve().parents[3]
    paths = (
        subprocess.check_output(["git", "ls-files", "-z", "--", *ACTIVE_PATHS], cwd=root)
        .decode("utf-8")
        .split("\0")
    )
    assert any(path.endswith("api_models.py") for path in paths)
    assert "docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md" in paths
    faults = []
    for path in filter(None, paths):
        try:
            faults.extend(f"{path}:{line}" for line in encoding_faults((root / path).read_bytes()))
        except UnicodeDecodeError:
            faults.append(f"{path}:invalid-utf8")
    assert not faults, "Active encoding corruption: " + ", ".join(faults)


@pytest.mark.parametrize("points", CORRUPT_CODEPOINTS)
def test_encoding_guard_rejects_each_demonstrated_sequence(points: tuple[int, ...]) -> None:
    assert encoding_faults(("safe\n" + "".join(map(chr, points))).encode()) == [2]


def test_encoding_guard_accepts_valid_unicode_and_rejects_invalid_utf8() -> None:
    assert encoding_faults("Ownership and UBO — needs input · Singapore 中文".encode()) == []
    with pytest.raises(UnicodeDecodeError):
        encoding_faults(bytes([0xFF]))


def test_decoded_ownership_intervention_has_intended_punctuation() -> None:
    client, *_ = build_system()
    result = start_demo(client, "OWNERSHIP_INCOMPLETE")
    intervention = next(
        item for item in result["interventions"] if item["owning_stage"] == "OWNERSHIP"
    )
    assert intervention["title"] == "Ownership and UBO — needs input"
