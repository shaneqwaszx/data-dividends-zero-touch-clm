"""B2-0: retrieval in the degraded mode (no embedding model running), as the service uses it on a
machine without Ollama. A regression gate at the measured baseline (2026-10-31: recall@3 0.96
with the synthetic past cases, every off-topic question retrieving nothing confident)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ai_assistant.config import AiAssistantSettings

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "scripts"))

import evaluate_retrieval  # noqa: E402


@pytest.mark.parametrize("role", ["RELATIONSHIP_MANAGER", "HR", "SUPPORT"])
def test_degraded_retrieval_holds_the_measured_baseline(tmp_path: Path, role: str) -> None:
    result = evaluate_retrieval.measure(
        AiAssistantSettings(_env_file=None),
        resolutions=True,
        degraded=True,
        role=role,
        team="TEAM_A",
        directory=tmp_path,
    )
    assert result.recall_at_k >= 0.95
    assert result.correct_nothing_rate == 1.0
