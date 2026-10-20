"""A negation only cancels the action or claim it is attached to (independent QG finding G1).

Before this check, any negation word in a clause exempted the whole clause, so "Do not wait,
approve the case now." was shown. These sentences must be left out, also while streaming;
real statements that an action is not available, or that something is not an approval,
must still pass.
"""

import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import StreamingGuard, guard_answer, validate_answer
from tests.test_ai_assistant import ME, SUMMARY

FACTS = build_case_facts(CaseSnapshot(SUMMARY, [], ME))
NO_ACTIONS: dict[str, object] = {"blockers": [], "overall": {"steps_done": 3, "steps_total": 12}}

BYPASSES = [
    "Do not wait, approve the case now.",
    "No need to wait: approve the case.",
    "There is no reason not to resend it now.",
    "There is no doubt the UBOs are verified.",
    "Nothing is missing and KYC approval is not in doubt.",
    "No need to wait: resend it to GoldTier.",
    "Do not hesitate to approve the case.",
    "Never mind the review, the UBOs are confirmed.",
]

LEGITIMATE = [
    "You cannot approve the case from the chat.",
    "This does not mean KYC approval.",
    "You can't approve the case from here.",
    "Successful mock submission does not establish GoldTier-internal or regulatory/KYC approval.",
    "Never resend an uncertain GoldTier submission from the chat.",
    "The UBOs are not verified yet.",
]


@pytest.mark.parametrize("facts", [FACTS, NO_ACTIONS], ids=["case", "no-actions"])
@pytest.mark.parametrize("sentence", BYPASSES)
def test_a_negation_elsewhere_in_the_clause_does_not_exempt_the_action(
    sentence: str, facts: dict[str, object]
) -> None:
    validation = validate_answer(sentence, facts)
    assert validation.text == ""
    assert validation.removed and validation.removed[0] in {"action_not_allowed", "authority_claim"}


@pytest.mark.parametrize("sentence", BYPASSES)
def test_a_negation_bypass_is_never_shown_while_streaming(sentence: str) -> None:
    for chunk_size in (1, 3, 7, len(sentence)):
        guard = StreamingGuard(NO_ACTIONS)
        shown = [
            guard.feed(sentence[i : i + chunk_size]) for i in range(0, len(sentence), chunk_size)
        ]
        shown.append(guard.feed(" And then upload ownership evidence."))
        assert all(not text or sentence not in text for text in shown)
        final = guard.finish()
        assert sentence not in final.text
        assert final.text == "And then upload ownership evidence."


@pytest.mark.parametrize("sentence", LEGITIMATE)
def test_a_negation_attached_to_the_action_or_claim_still_passes(sentence: str) -> None:
    assert guard_answer(sentence, FACTS) == sentence


def test_saying_an_offered_label_is_unavailable_after_naming_it_passes() -> None:
    sentence = "Approving the case is not possible from the chat."
    assert guard_answer(sentence, NO_ACTIONS) == sentence


def test_only_the_negated_clause_is_exempt_in_a_mixed_sentence() -> None:
    answer = "You cannot approve the case here, but do not wait, approve the case anyway."
    assert guard_answer(answer, NO_ACTIONS) == ""
