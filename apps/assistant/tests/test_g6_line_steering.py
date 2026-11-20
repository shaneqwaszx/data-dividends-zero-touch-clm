"""G-6 line validity: the two recurring GPT-OSS drops and the RULES steering that avoids them.

Live run 70443157 (basis 59e726e13919) failed G-6 at 0.60 on the two-question manifest. Its
closed reason codes were ``live_claim`` on P01#1 (occasional) and ``unsupported_value`` on
P02#0 (every model answer). Both rules are correct and stay unchanged:

- ``live_claim``: Live wording about a source ("not a live ACRA connection") is removed unless
  the whole sentence is one of the closed negated forms (claims.negated_sentence);
- ``unsupported_value``: a percentage must be in the case facts. The Garden case has no
  ownership analysis, so the approved guidance's UBO threshold figure is not grounding.

The fix steers the model (copilot.RULES 4 and 7): environments by their label, no Live wording
even to deny it, and no threshold figure the OWNERSHIP FACTS do not give. The answers below are
SYNTHETIC, written in the observed GPT-OSS styles (the harness keeps no answer text), replayed
through the real qualification path: mock OpenRouter API, privacy boundary, copilot guard and
the G-6 gate. No network, no paid call, no real key.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ai_assistant import copilot, model_qualification
from tests import test_g6_guard_reasons as g6_guard_reasons
from tests.test_conversational_external import _conversational_prompt
from tests.test_g6_guard_reasons import OWNERS, REGISTRY, _qualify

NO_OWNERSHIP = {"ownership": {"available": False, "note": "No ownership analysis is available."}}

# Observed styles before the fix: a correct answer with a Live denial and the guidance's figure.
BEFORE: dict[str, Any] = {
    REGISTRY: (
        "The company details come from the ACRA record for [COMPANY-A] (UEN [ID-B]).\n"
        "The registry used is ACRA (MOCK), which is not a Live integration.\n"
        "The data comes from a Mock ACRA source, not a live ACRA connection.\n"
        "The entity status in the record describes the company's registration."
    ),
    OWNERS: (
        "The ultimate beneficial owners cannot be identified yet.\n"
        "No ownership analysis is available for this case.\n"
        "A UBO is anyone who holds 25% or more of the company."
    ),
}

# The same content written as RULES 4 and 7 now ask.
STEERED: dict[str, Any] = {
    REGISTRY: (
        "The company details come from the ACRA record for [COMPANY-A] (UEN [ID-B]).\n"
        "No, it is the Mock registry: the source is ACRA (MOCK).\n"
        "The entity status in the record describes the company's registration."
    ),
    OWNERS: (
        "The ultimate beneficial owners cannot be identified yet.\n"
        "No ownership analysis is available for this case.\n"
        "Once the ownership evidence is provided, the application compares each person's "
        "aggregated interest with the UBO threshold and lists any provisional UBO candidates."
    ),
}


def _g(result: dict[str, Any], gate: str) -> dict[str, Any]:
    return next(item for item in result["gates"] if item["gate"] == gate)


def test_the_guard_rules_behind_the_drops_are_unchanged() -> None:
    # live_claim: a Live denial outside the closed negated forms is still removed.
    for sentence in (
        "The data comes from a Mock ACRA source, not a live ACRA connection.",
        "The registry used is ACRA (MOCK), which is not a Live integration.",
        "This is real ACRA data.",
    ):
        assert copilot.check_answer(sentence, NO_OWNERSHIP).left_out == ["live_claim"]
    # unsupported_value: a figure the case facts do not hold is still removed.
    check = copilot.check_answer("A UBO is anyone who holds 25% or more.", NO_OWNERSHIP)
    assert check.left_out == ["unsupported_value"]
    # ... and a figure the facts do hold is still kept.
    held = {"ownership": {"available": True, "threshold_percent": 25}}
    assert copilot.check_answer("The threshold is 25%.", held).left_out == []


def test_the_rules_examples_pass_the_guard() -> None:
    for sentence in ("No, it is the Mock registry.", "The source is ACRA (MOCK)."):
        check = copilot.check_answer(sentence, NO_OWNERSHIP)
        assert (check.kept, check.left_out) == (1, [])


def test_rules_steer_away_from_live_wording_and_unheld_figures() -> None:
    rule4 = copilot.RULES.split("\n4. ")[1].split("\n5. ")[0]
    rule7 = copilot.RULES.split("\n7. ")[1].split("\n8. ")[0]
    assert "only by its label in the EVIDENCE" in rule7
    assert "not even to deny it" in rule7
    assert "Never say anything was officially verified or approved." in rule7
    assert "State a percentage or threshold only as the OWNERSHIP FACTS give it" in rule4
    assert "not even one from KNOWLEDGE" in rule4


def test_the_steering_reaches_the_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # _qualify's mock model reads the question with _last_user, for conversational prompts only.
    sent: list[str] = []
    last_user = g6_guard_reasons._last_user

    def spy(messages: list[dict[str, Any]]) -> str:
        assert _conversational_prompt(json.dumps(messages))
        sent.append(str(messages[0]["content"]))
        return str(last_user(messages))

    monkeypatch.setattr(g6_guard_reasons, "_last_user", spy)
    _qualify(tmp_path, monkeypatch, STEERED)
    assert sent and all("not even to deny it" in prompt for prompt in sent)
    assert all("not even one from KNOWLEDGE" in prompt for prompt in sent)


@pytest.mark.parametrize(
    ("answers", "g6", "reasons"),
    [
        (BEFORE, 0.5714, {"P01#1": {"live_claim": 2}, "P02#0": {"unsupported_value": 1}}),
        (STEERED, 1.0, {}),
    ],
    ids=["before_fix", "steered"],
)
def test_offline_g6_before_and_after_the_steering(
    answers: dict[str, Any],
    g6: float,
    reasons: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _qualify(tmp_path, monkeypatch, answers)
    gate = _g(result, "G-6")
    assert gate["value"] == g6
    assert gate["passed"] is (g6 >= model_qualification.G6_MIN_LINE_VALIDITY)
    assert model_qualification.G6_MIN_LINE_VALIDITY == 0.70
    assert result["lines"]["left_out_reasons_by_turn"] == reasons
    assert result["lines"]["restore_dropped_lines"] == 0
    # The longer RULES stay inside the verified prompt bound (G-7).
    assert _g(result, "G-7")["passed"] is True
    if not reasons:
        assert _g(result, "G-5")["value"] == 0.0
        assert result["lines"]["deterministic_fallbacks"] == 0
    stored = json.dumps(result)
    for text in ("Mock registry", "GARDEN BUSINESS", "11111999A", "25%"):
        assert text not in stored
