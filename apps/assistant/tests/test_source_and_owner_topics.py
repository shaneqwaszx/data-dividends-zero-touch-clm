"""Source-aware partial answers (Phase B, D-092 proposed).

Two questions the readiness topics do not cover were answered with a bare "can't answer" once
rule 17 made that line exclusive: which registry the company details came from (and whether
it is live), and who the UBOs are. The source line is an allowed line only when the
backend's own company source is ACRA in an environment that is not live; the UBO question is
steered to the existing ownership-evidence lines only when the backend readiness check lists
missing ownership evidence. Neither topic requires a line, so a bare decline is never padded.
The synthetic Merlion case comes from tests/test_explanations.py.
"""

import copy
from typing import Any

import pytest

from ai_assistant.briefing import fallback_answer, question_topic
from ai_assistant.guardrails import (
    allowed_guidance,
    registry_source_line,
    validate_answer,
    with_required_lines,
)
from ai_assistant.guide import MOCK_NOT_LIVE, OUT_OF_SCOPE
from ai_assistant.prompts import topic_message, topic_plan
from tests.test_explanations import FACTS

MOCK_SOURCE = "Registry data in this case comes from ACRA (MOCK), not the live ACRA service."
OWNERSHIP_NEED = (
    "Ownership (shareholder) evidence is needed before the UBO check can run. "
    "(section: Ownership & UBO)"
)
REGISTRY_QUESTION = "Which registry was used for this company, and is that registry live?"
UBO_QUESTION = "Who are the ultimate beneficial owners of this company?"


def _with_source(source: str) -> dict[str, Any]:
    facts = copy.deepcopy(FACTS)
    facts["company"]["source"] = source
    return facts


def _without_ownership_need() -> dict[str, Any]:
    facts = copy.deepcopy(FACTS)
    facts["still_needed_before_goldtier"] = [
        need
        for need in facts["still_needed_before_goldtier"]
        if need["code"] != "OWNERSHIP_REQUIRED"
    ]
    return facts


# --- the registry source line -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("ACRA (MOCK), retrieved 5 Oct 2026, 04:02 UTC", MOCK_SOURCE),
        (
            "ACRA (SANDBOX)",
            "Registry data in this case comes from ACRA (SANDBOX), not the live ACRA service.",
        ),
        ("ACRA (LIVE), retrieved 5 Oct 2026, 04:02 UTC", None),
        ("ACRA, retrieved 5 Oct 2026, 04:02 UTC", None),
        ("Details entered when the case was created", None),
        ("OTHER REGISTRY (MOCK)", None),
    ],
)
def test_the_source_line_is_allowed_only_for_a_non_live_acra_source(
    source: str, line: str | None
) -> None:
    facts = _with_source(source)
    assert registry_source_line(facts, acra_only=True) == line
    offered = [entry for entry in allowed_guidance(facts) if entry.startswith("Registry data")]
    assert offered == ([line] if line else [])


def test_the_source_disclosure_is_unchanged_and_not_duplicated() -> None:
    address = next(line for line in allowed_guidance(FACTS) if line.startswith("Registered"))
    # An answer that relies on ACRA data still gets the notice, as before.
    assert validate_answer(address, FACTS).disclosures == (MOCK_SOURCE,)
    # An answer that already shows the source line gets no second copy.
    shown = validate_answer(MOCK_SOURCE, FACTS)
    assert shown.text == MOCK_SOURCE and shown.disclosures == ()
    # A non-ACRA non-live source keeps its notice (the allowed line is not offered there).
    other = _with_source("OTHER REGISTRY (MOCK)")
    assert registry_source_line(other) == MOCK_SOURCE
    assert validate_answer(address, other).disclosures == (MOCK_SOURCE,)


def test_a_paraphrased_source_claim_is_still_withheld() -> None:
    result = validate_answer("The registry is a mock copy of ACRA.\n" + MOCK_SOURCE, FACTS)
    assert result.text == MOCK_SOURCE and result.left_out == 1


# --- topic routing ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question", [REGISTRY_QUESTION, "Is the ACRA data live?", "Is this registry a mock?"]
)
def test_a_registry_status_question_is_steered_to_the_source_line(question: str) -> None:
    plan = topic_plan(FACTS, question)
    assert plan is not None
    assert plan.lines == (MOCK_SOURCE, MOCK_NOT_LIVE) and plan.required == ()
    message = topic_message(FACTS, question)
    assert message is not None and MOCK_SOURCE in message


def test_no_source_steering_without_a_non_live_acra_source() -> None:
    for source in ("ACRA (LIVE)", "Details entered when the case was created"):
        assert topic_plan(_with_source(source), REGISTRY_QUESTION) is None


@pytest.mark.parametrize(
    "question", [UBO_QUESTION, "Who are the UBOs?", "Which shareholders count as UBOs?"]
)
def test_a_ubo_question_is_steered_to_the_missing_ownership_evidence(question: str) -> None:
    plan = topic_plan(FACTS, question)
    assert plan is not None and plan.required == ()
    assert plan.lines[0] == OWNERSHIP_NEED
    allowed = set(allowed_guidance(FACTS))
    assert all(line in allowed for line in plan.lines)
    # No owner is named and nothing says there are no UBOs.
    assert not any(
        "no ubo" in line.lower() or "there are no" in line.lower() for line in plan.lines
    )


def test_no_ubo_steering_when_ownership_evidence_is_not_missing() -> None:
    assert topic_plan(_without_ownership_need(), UBO_QUESTION) is None


@pytest.mark.parametrize(
    "question",
    [
        "What ownership percentage makes someone a UBO here?",  # threshold guidance, unchanged
        "Who are the directors of this company according to ACRA?",
        "What is the weather in Singapore today?",
        "Write me a Python script that downloads company records from ACRA.",
        "What does this case's UEN tell me, and where did the company details come from?",
    ],
)
def test_other_questions_are_not_routed_to_the_new_topics(question: str) -> None:
    assert topic_plan(FACTS, question) is None


def test_existing_topics_take_precedence() -> None:
    plan = topic_plan(
        FACTS, "The registered address in the document differs from ACRA. Which one is used?"
    )
    assert plan is not None and plan.about == "the registered address difference"
    plan = topic_plan(FACTS, "What ownership evidence is needed?")
    assert plan is not None and plan.about == "ownership evidence"


def test_the_case_data_answer_is_unchanged() -> None:
    """The routing steers the model only; the no-model answer keeps its own topics."""

    assert question_topic(REGISTRY_QUESTION, FACTS) is None
    assert question_topic(UBO_QUESTION, FACTS) is None
    assert fallback_answer(REGISTRY_QUESTION, FACTS).startswith("From ACRA (MOCK), retrieved")
    assert MOCK_SOURCE not in fallback_answer(UBO_QUESTION, FACTS)


# --- rule 17: no mixed decline ---------------------------------------------------------------


@pytest.mark.parametrize("question", [REGISTRY_QUESTION, UBO_QUESTION])
def test_a_bare_decline_is_never_padded_by_the_new_topics(question: str) -> None:
    plan = topic_plan(FACTS, question)
    assert plan is not None
    decline = validate_answer(OUT_OF_SCOPE, FACTS)
    padded = with_required_lines(decline, FACTS, order=plan.lines, required=plan.required)
    assert padded.text == OUT_OF_SCOPE


def test_the_rule_17_wording_is_kept() -> None:
    from ai_assistant.instructions import system_prompt

    assert f'\n17. Use "{OUT_OF_SCOPE}" only on its own' in system_prompt()
