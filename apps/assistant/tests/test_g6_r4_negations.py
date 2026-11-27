"""G-6 R4: the correct answer to "is that registry live?" is kept, in closed forms only.

Hosted runs 9faf4d9e and 70443157 (and offline replays) lost a correct "not Live" sentence on
P01#1 as ``live_claim``, and the service's own approved sentence (guide.MOCK_NOT_LIVE) as
``authority_claim``. R4 adds three whole-sentence forms to claims.negated_sentence; anything
added to such a sentence (another clause, a reversal, an authority word) is still removed.

The shared ``live_claim`` check (guardrails._check) is unchanged. Its blanket exemption for a
sentence that mentions "status" is a known gap ("The registry is live, as the entity status is
LIVE." is kept); narrowing it also removed an approved catalog line, so it is a separate
follow-up, not part of R4.
"""

from __future__ import annotations

import pytest

from ai_assistant import copilot
from ai_assistant.claims import negated_sentence
from ai_assistant.guide import MOCK_NOT_LIVE

NO_OWNERSHIP = {"ownership": {"available": False, "note": "No ownership analysis is available."}}

KEPT_NEGATIONS = (
    "That ACRA data is Mock data, not a Live integration.",
    "It is Mock data, not a live ACRA registry.",
    "The registry is Sandbox, not a live connection.",
    "No, it is not a live registry.",
    "The registry data is not from a Live integration.",
    "The data is marked Mock, so it is not from a Live integration.",
    "It isn't a live ACRA connection.",
    MOCK_NOT_LIVE,
)

STILL_REMOVED = (
    # Another clause after a closed form.
    "It is Mock data, not a Live integration, and the UBO is verified.",
    "That data is Mock, not a Live integration and it is final.",
    "It is not a live registry but it is approved.",
    # Reversals.
    "It is not Mock data; it is a live integration.",
    "The registry is not mock, it is a live integration.",
    # A Live denial outside the closed forms (kept removed; RULES 7 steers away from it).
    "The registry used is ACRA (MOCK), which is not a Live integration.",
    "The data comes from a Mock ACRA source, not a live ACRA connection.",
    # An open subject is not one of the closed subjects.
    "The GoldTier submission is Mock, not a live integration.",
    # The approved sentence with anything added.
    MOCK_NOT_LIVE.rstrip(".") + ", and the UBO is approved.",
)


@pytest.mark.parametrize("sentence", KEPT_NEGATIONS)
def test_a_closed_not_live_sentence_is_kept(sentence: str) -> None:
    assert negated_sentence(sentence)
    check = copilot.check_answer(sentence, NO_OWNERSHIP)
    assert (check.kept, check.left_out) == (1, [])


@pytest.mark.parametrize("sentence", STILL_REMOVED)
def test_anything_beyond_a_closed_form_is_still_removed(sentence: str) -> None:
    assert not negated_sentence(sentence)
    check = copilot.check_answer(sentence, NO_OWNERSHIP)
    assert check.kept == 0 and len(check.left_out) == 1
    assert check.left_out[0] in {"live_claim", "authority_claim"}


def test_a_typographic_copy_matches_the_closed_form() -> None:
    # Quotation marks around exactly an environment label dropped, and a spaced dash read as a
    # comma. (Alone, the quoted "Mock" is an invented label to check_answer; the full
    # qualification replay of this style keeps it, see test_g6_guard_reasons.py "typography".)
    assert negated_sentence("That ACRA data is “Mock” data — not a Live integration.")
    assert negated_sentence('That ACRA data is "Mock" data, not a Live integration.')
    assert negated_sentence("It is Mock data – not a live registry.")
    assert not negated_sentence("It is Mock data — not a live registry — and approved.")


@pytest.mark.parametrize(
    "sentence",
    [
        # QG H-1: quotation marks anywhere but around a bare label fail closed, so a scare-quoted
        # "not", "live" or authority word never reads as a negation (new or pre-existing form).
        'It is "not" a live registry.',
        "It is “not” a live registry.",
        'The UBO has "not" been officially verified.',
        "The UBO has “not” been officially verified.",
        'It is Mock data, not a "live" registry.',
        'It is "Mock data, not a Live integration".',
        '"It is Mock data, not a Live integration."',
        'That ACRA data is "Mock" data, not a "Live" integration.',
        "That ACRA data is “Mock data” — not a Live integration.",
        'The UBO has not been officially "verified".',
        'That data is "Mock", not a Live integration "and approved".',
    ],
)
def test_other_quotation_marks_never_match_a_closed_form(sentence: str) -> None:
    assert not negated_sentence(sentence)
    # Without the quotation marks a pre-existing form still matches (unchanged from main).
    assert negated_sentence("The UBO has not been officially verified.")


def test_live_claims_without_a_negation_are_still_removed() -> None:
    for sentence in ("This is real ACRA data.", "The registry is live.", "It is a live registry."):
        assert copilot.check_answer(sentence, NO_OWNERSHIP).left_out == ["live_claim"]
