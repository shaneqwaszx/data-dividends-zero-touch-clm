"""Fail-closed negation handling (independent QG findings G1 on ad4661c and on 79621fe).

At ad4661c any negation word in a clause exempted the whole clause, so "Do not wait, approve
the case now." was shown. At 79621fe a word-window rule still let ordinary phrasings through
("Never forget to resend it."). Now an action or claim is left out unless a negation
directly governs it. Every sentence below must be left out, also while streaming in any
chunking; real statements that an action is not available, or that something is not an
approval, must still pass.
"""

import random

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
    # The second independent gate's variants (QG_PR99_79621fe.md section 4.1).
    "Don't hesitate to approve the case.",
    "Never forget to resend it.",
    "No reason to wait — the UBOs are verified.",
    "Do not forget to approve the case.",
    "Do not wait to approve the case.",
    "Never hesitate to approve the case.",
    "Don’t hesitate to approve the case.",
    "There are no blockers so you can approve the case.",
    "There are no blockers, so you can approve the case.",
    "No issues remain and the UBOs are verified.",
    "There is no reason to doubt that the UBOs are verified.",
    "No reason to wait as the UBOs are verified.",
    "I see no problem with you approving the case.",
    "There's no reason you shouldn't resend it.",
    "Approve the case now because waiting is not allowed.",
    "Resend it now as delay is not possible.",
    "The UBOs are verified since a manual check is not available.",
    "It is not too early to approve the case.",
    "Not a problem: approve the case.",
    "With no blockers left approve the case.",
    "Nothing blocks you so approve the case.",
]

LEGITIMATE = [
    "You cannot approve the case from the chat.",
    "This does not mean KYC approval.",
    "You can't approve the case from here.",
    "Successful mock submission does not establish GoldTier-internal or regulatory/KYC approval.",
    "Never resend an uncertain GoldTier submission from the chat.",
    "The UBOs are not verified yet.",
    "You cannot approve the case.",
    "You can't approve the case in the chat.",
    "The AI Assistant does not approve the case.",
    "Keep registry value is not available here.",
    "Do not resend it.",
    "You should never resend it from the chat.",
    "Ownership is not confirmed until a person reviews it.",
    "This is not KYC approval.",
]


@pytest.mark.parametrize("facts", [FACTS, NO_ACTIONS], ids=["case", "no-actions"])
@pytest.mark.parametrize("sentence", BYPASSES)
def test_a_negation_elsewhere_in_the_clause_does_not_exempt_the_action(
    sentence: str, facts: dict[str, object]
) -> None:
    validation = validate_answer(sentence, facts)
    assert validation.text == ""
    assert validation.removed and validation.removed[0] in {"action_not_allowed", "authority_claim"}


def _chunks(text: str, sizes: list[int]) -> list[str]:
    out, position, index = [], 0, 0
    while position < len(text):
        size = sizes[index % len(sizes)]
        out.append(text[position : position + size])
        position, index = position + size, index + 1
    return out


@pytest.mark.parametrize("sentence", BYPASSES)
def test_a_negation_bypass_is_never_shown_while_streaming(sentence: str) -> None:
    rng = random.Random(sentence)
    splits = [[1], [2], [3], [5], [7], [len(sentence)], [rng.randint(1, 6) for _ in range(40)]]
    for sizes in splits:
        guard = StreamingGuard(NO_ACTIONS)
        shown = [guard.feed(chunk) for chunk in _chunks(sentence, sizes)]
        shown.append(guard.feed(" And then upload ownership evidence."))
        assert all(not text or sentence not in text for text in shown)
        final = guard.finish()
        assert sentence not in final.text
        assert final.text == "And then upload ownership evidence."


@pytest.mark.parametrize("facts", [FACTS, NO_ACTIONS], ids=["case", "no-actions"])
@pytest.mark.parametrize("sentence", LEGITIMATE)
def test_a_negation_attached_to_the_action_or_claim_still_passes(
    sentence: str, facts: dict[str, object]
) -> None:
    assert guard_answer(sentence, facts) == sentence
    guard = StreamingGuard(facts)
    for chunk in _chunks(sentence, [3]):
        guard.feed(chunk)
    assert guard.finish().text == sentence


def test_fail_closed_over_drops_rather_than_letting_advice_through() -> None:
    # The reviewer's over-drop: the second clause's "a person approves the case" is not
    # governed by a negation, so it is left out. That errs on the safe side by design.
    assert (
        guard_answer("Approval is never offered here; a person approves the case.", NO_ACTIONS)
        == ""
    )


def test_saying_an_offered_label_is_unavailable_after_naming_it_passes() -> None:
    sentence = "Approving the case is not possible from the chat."
    assert guard_answer(sentence, NO_ACTIONS) == sentence


def test_only_the_negated_clause_is_exempt_in_a_mixed_sentence() -> None:
    answer = "You cannot approve the case here, but do not wait, approve the case anyway."
    assert guard_answer(answer, NO_ACTIONS) == ""
