"""G-6 diagnostics (R0) and the offline G-6 regression.

A qualification summary now says which CopilotGuard rule left each sentence out (closed codes
and counts only) and how many model lines the D-142 restore dropped. The regression replays
SYNTHETIC answers written in the styles observed in hosted GPT-OSS answers (no stored GPT-OSS
answer exists: the harness keeps no answer text) through the real qualification path: the
mock OpenRouter API, the privacy boundary (the answers use the placeholders the model is sent),
the copilot guard and the G-6 gate. No network, no paid call, no real key.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from ai_assistant import copilot, model_qualification, privacy_boundary
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from assistant_eval import guard_reasons
from tests import test_remote_test
from tests.test_conversational_external import _conversational_prompt, _last_user, approve
from tests.test_model_management import API
from tests.test_remote_test import Journey, wait_for
from tests.test_synthetic_eligibility import D095, GARDEN, serve

REGISTRY = "Which registry did the company details come from, and is it live?"
OWNERS = "Who are the ultimate beneficial owners?"

# --- unit -------------------------------------------------------------------------------------


def test_recording_observes_and_puts_the_methods_back() -> None:
    finish = copilot.CopilotGuard.finish
    restore = privacy_boundary.Protected.restore_line
    with guard_reasons.recording() as recorder:
        assert guard_reasons.active() is recorder
        check = copilot.check_answer("I have approved the case. The review is open.", None)
        assert check.left_out == ["assistant_action_claim"]  # the result itself is unchanged
        assert recorder.take() == ({"assistant_action_claim": 1}, 0)
        assert recorder.take() == ({}, 0)
    assert guard_reasons.active() is None
    assert copilot.CopilotGuard.finish is finish
    assert privacy_boundary.Protected.restore_line is restore


def test_recording_cannot_be_nested_and_is_put_back_after_an_error() -> None:
    finish = copilot.CopilotGuard.finish
    with pytest.raises(ValueError), guard_reasons.recording():
        with pytest.raises(RuntimeError), guard_reasons.recording():
            pass
        raise ValueError
    assert copilot.CopilotGuard.finish is finish and guard_reasons.active() is None


def test_only_closed_codes_are_kept() -> None:
    recorder = guard_reasons.GuardReasons()
    recorder.add_reasons(["unsupported_name", "The UBO is LIM.", "x" * 60, ""])
    assert recorder.take() == ({"other": 3, "unsupported_name": 1}, 0)


def _turn(key: str, left_out: int, reasons: dict[str, int], dropped: int = 0) -> Any:
    return SimpleNamespace(
        key=key,
        rep=0,
        metrics={"left_out_lines": left_out},
        left_out_reasons=reasons,
        restore_dropped_lines=dropped,
    )


def test_each_turns_codes_add_up_to_its_left_out_count() -> None:
    result = guard_reasons.reason_breakdown(
        [
            _turn("P01#1", 2, {"live_claim": 1, "authority_claim": 1}, dropped=1),
            _turn("P02#0", 1, {}),  # e.g. an exact-lines answer: no copilot code
            _turn("P03#0", 0, {}),
        ]
    )
    assert result == {
        "left_out_reasons": {"authority_claim": 1, "live_claim": 1, "unattributed": 1},
        "left_out_reasons_by_turn": {
            "P01#1": {"authority_claim": 1, "live_claim": 1},
            "P02#0": {"unattributed": 1},
        },
        "restore_dropped_lines": 1,
    }


def test_r0_does_not_change_the_qualification_basis() -> None:
    # R0 lives in the evaluation harness only: Claude's and GPT-OSS's qualifications stay current.
    for name in ("guard_reasons.py", "runner.py", "qualification.py"):
        assert name not in model_qualification.BASIS_FILES
    assert model_qualification.HARNESS_VERSION == "model-qualification/1"


# --- offline G-6 regression (SYNTHETIC answers) ---------------------------------------------------

# Synthetic answers in the observed GPT-OSS styles, as the model would write them (placeholders
# as sent). Expected values are the guard's behaviour at release c5a1c7f4.
SYNTHETIC: dict[str, dict[str, Any]] = {
    "plain": {
        REGISTRY: (
            "The company details come from the ACRA record for [COMPANY-A] (UEN [ID-B]).\n"
            "That ACRA data is Mock data, not a Live integration.\n"
            "The entity status shown in the record is LIVE, which describes the company's "
            "registration, not the data connection.\n"
            "Mock, Local and Sandbox evidence do not establish Live integration or KYC approval."
        ),
        OWNERS: (
            "The ultimate beneficial owners cannot be identified yet.\n"
            "No ownership analysis is available for this case, because the ownership "
            "(shareholder) evidence has not been provided.\n"
            "Once the shareholder register is uploaded, the application runs the UBO check and "
            "lists any provisional UBO candidates.\n"
            "Ownership and UBO analysis is provisional; it does not establish legal verification."
        ),
        "g6": 0.75,
        "reasons": {"authority_claim": 1, "live_claim": 1},
    },
    "typography": {
        REGISTRY: (
            "The company details come from the ACRA record for [COMPANY-A] (UEN  [ID-B]).\n"
            "That ACRA data is “Mock” data — not a Live integration.\n"
            "The entity status shown in the record is “LIVE”, which describes the "
            "company’s registration — not the data connection.\n"
            "Mock, Local and Sandbox evidence do not establish Live integration or KYC approval."
        ),
        OWNERS: (
            "The ultimate beneficial owners can’t be identified yet.\n"
            "No ownership analysis is available for this case – because the ownership "
            "(shareholder) evidence hasn’t been provided.\n"
            "Once the shareholder register is uploaded, the application runs the UBO check and "
            "lists any provisional UBO candidates.\n"
            "Ownership and UBO analysis is provisional; it does not establish legal verification."
        ),
        # G-6 R1: the narrow no-break space no longer removes a correct sentence.
        "g6": 0.75,
        "reasons": {"authority_claim": 1, "live_claim": 1},
    },
    "markdown_mixed": {
        REGISTRY: (
            "**Registry:** ACRA — the Singapore Accounting and Corporate Regulatory "
            "Authority.\n"
            "**Is it live?** No. The record is “ACRA (MOCK)”, i.e. a mock‑up, not "
            "a live connection.\n"
            "The company’s entity status is LIVE, but that is the company’s registration "
            "status, not the integration."
        ),
        OWNERS: (
            "**Answer:** The UBOs can’t be determined yet.\n"
            "- No ownership analysis is available – the shareholder evidence is still "
            "missing.\n"
            "- When it is uploaded, the app will calculate who holds 25% or more and flag "
            "provisional UBO candidates.\n"
            "- Until then, no one is a confirmed UBO."
        ),
        # G-6 R1: the hyphen is mapped, and the sentence is then checked (and left out) for
        # its Live wording, so this style still fails G-6 (see G6_REMEDIATION_REPORT.md).
        "g6": 0.625,
        "reasons": {"authority_claim": 1, "live_claim": 1, "unsupported_value": 1},
    },
}


def _qualify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answers: dict[str, Any]) -> Any:
    approve(monkeypatch)
    lines = test_remote_test._reply_lines

    def reply(body: dict[str, Any]) -> str:
        if not _conversational_prompt(json.dumps(body["messages"])):
            return lines(body)
        return str(answers[_last_user(body["messages"])]) + "\n"

    monkeypatch.setattr(test_remote_test, "_reply_lines", reply)
    journey = Journey(tmp_path, monkeypatch, **D095)
    serve(monkeypatch, GARDEN)
    test = journey.client.post(f"{API}/{OPENROUTER_PROFILE_ID}/connection-test")
    assert test.status_code == 200 and test.json()["outcome"] == "passed", test.text
    started = journey.start_qualification()
    assert started.status_code == 202, started.text
    return wait_for(journey.client, started.json()["qualification_id"])


@pytest.mark.parametrize("style", sorted(SYNTHETIC))
def test_offline_g6_regression_names_the_rules_that_removed_sentences(
    style: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = SYNTHETIC[style]
    result = _qualify(tmp_path, monkeypatch, case)
    g6 = next(gate for gate in result["gates"] if gate["gate"] == "G-6")
    lines = result["lines"]
    assert g6["value"] == case["g6"]
    assert g6["passed"] is (case["g6"] >= model_qualification.G6_MIN_LINE_VALIDITY)
    assert lines["left_out_reasons"] == case["reasons"]
    assert sum(lines["left_out_reasons"].values()) == lines["guard_withheld_lines"]
    assert set(lines["left_out_reasons_by_turn"]) <= {"P01#1", "P02#0"}
    assert lines["restore_dropped_lines"] == 0
    # Counts and closed codes only: no answer or case text is kept in the summary.
    stored = json.dumps(result)
    for sentence in ("Mock data", "GARDEN BUSINESS", "11111999A", "shareholder register"):
        assert sentence not in stored
