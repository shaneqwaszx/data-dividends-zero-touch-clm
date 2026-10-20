"""Sentence checks: factual claims, action permissions and disclosures.

They decide which approved knowledge sentences become allowed lines
(guardrails.knowledge_lines). Model text itself is never repaired or partly kept: only whole
allowed lines are shown (see the whole-answer tests at the end).
"""

import json

import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import (
    allowed_guidance,
    knowledge_lines,
    sentence_problem,
    validate_answer,
)
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, SUMMARY, FakeBackend, FakeModel, _client
from tests.test_document_review_choices import _facts as facts_with_document_review

FACTS = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=DOCUMENTS, actor=ME))
OFFERED = 'The current case offers "Keep registry value".'
OPEN_OWNERSHIP = 'Open the "Ownership & UBO" section to inspect the current case evidence.'


def _reasons(sentence: str, facts: dict[str, object] = FACTS) -> tuple[str, ...]:
    reason = sentence_problem(sentence, facts)
    return (reason,) if reason else ()


# 1. Grounding: factual claims ---------------------------------------------------------


@pytest.mark.parametrize(
    "sentence",
    [
        "The UEN is 11111999A.",
        "The document says 18 GARDEN WALK, #01-01, 018919, SG.",
        "Each value has an evidence score of 0.97.",
        "5 of 12 onboarding steps are done.",
    ],
)
def test_values_that_are_in_the_case_facts_are_kept(sentence: str) -> None:
    assert _reasons(sentence) == ()


@pytest.mark.parametrize(
    ("sentence", "reason"),
    [
        ("The UEN is 202400001A.", "unsupported_value"),
        ("ACRA lists the postal code 048547.", "unsupported_value"),
        ("The unit is #04-01.", "unsupported_value"),
        ("The evidence score is 0.85.", "unsupported_value"),
        ("6 of 12 onboarding steps are done.", "wrong_step_count"),
        ("Ask the compliance team.", "invented_contact"),
        ('Click "Approve now".', "invented_label"),
        ("Upload it (section: Upload centre).", "unknown_section"),
        ("As the other entry says [G2].", "invented_source"),
        # QG_PR99_c2c391c K2: letter-prefixed identifiers, e-mail and web addresses.
        ("The UEN is T08LL1234A.", "unsupported_value"),
        ("The director's NRIC is S1234567D.", "unsupported_value"),
        ("The FIN is G1234567X.", "unsupported_value"),
        ("Email kyc-help@example.com for help.", "invented_contact"),
        ("Upload it at https://files.example.com/upload.", "invented_contact"),
        ("See www.example.com for the form.", "invented_contact"),
        # Characters outside the conservative set: tab, look-alike and invisible letters.
        ("Keep\tthe registry value.", "unsupported_character"),
        ("\u0410pprove the case now.", "unsupported_character"),
        ("Approve\u2800the case now.", "unsupported_character"),
        ("App\u034frove the case now.", "unsupported_character"),
        ("Re\u2011send it now.", "unsupported_character"),
    ],
)
def test_values_that_are_not_in_the_case_facts_are_left_out(sentence: str, reason: str) -> None:
    assert _reasons(sentence) == (reason,)


def test_a_real_case_page_section_is_allowed() -> None:
    assert _reasons("Upload ownership evidence (section: Ownership & UBO).") == ()


def test_identifiers_and_addresses_from_the_case_and_typographic_marks_are_allowed() -> None:
    facts = {"contact": "ops@example.com", "id": "T08LL1234A", "nric": "S1234567D"}
    assert _reasons("The UEN is T08LL1234A and the NRIC is S1234567D.", facts) == ()
    assert _reasons("Email ops@example.com.", facts) == ()
    assert _reasons("The document\u2019s address differs \u2013 check it\u2026") == ()
    assert _reasons("A very long word " + "a" * 5000 + " stays a word.") == ()


# 2. Policy: action permissions ----------------------------------------------------------


def test_an_action_the_rm_is_allowed_is_kept() -> None:
    assert _reasons('Click "Keep registry value" to keep the ACRA address.') == ()


@pytest.mark.parametrize(
    "sentence",
    [
        "You can also reject the document if it is wrong.",
        "Use the document address instead.",
        "Then approve the case.",
        "After that, submit it to GoldTier.",
    ],
)
def test_an_action_the_rm_is_not_offered_is_left_out(sentence: str) -> None:
    assert _reasons(sentence) == ("action_not_allowed",)


def test_saying_an_action_is_not_available_is_fine() -> None:
    assert _reasons("You cannot use the document value for the address.") == ()
    assert _reasons("You can't approve the case from here.") == ()


@pytest.mark.parametrize(
    "sentence",
    [
        # The real slip from the demo: an option that this case does not offer.
        "The app only lets you keep the registry value (ACRA's address) or reject the document "
        "(if it's wrong).",
        "You cannot use the document value, but you can reject the document.",
    ],
)
def test_an_unoffered_action_is_caught_even_beside_a_negation_or_an_allowed_one(
    sentence: str,
) -> None:
    assert _reasons(sentence) == ("action_not_allowed",)


def test_apostrophes_are_not_mistaken_for_quoted_labels() -> None:
    assert _reasons("The document's address and ACRA's address differ.") == ()


def test_document_review_choices_are_allowed_when_the_page_offers_them() -> None:
    sentence = "You can also reject the document suggestion if it was read wrongly."
    assert _reasons(sentence) == ("action_not_allowed",)
    assert _reasons(sentence, facts_with_document_review()) == ()


# 3. Disclosures ------------------------------------------------------------------------


def test_a_mock_registry_is_never_called_live() -> None:
    assert _reasons("The live ACRA registry returned this address.") == ("live_claim",)
    assert _reasons("The company's ACRA entity status is LIVE.") == ()


def test_a_document_value_that_differs_from_acra_is_not_presented_as_confirmed() -> None:
    sentence = "The address 18 GARDEN WALK, #01-01, 018919, SG is confirmed."
    assert _reasons(sentence) == ("document_value_as_fact",)
    assert _reasons("The document says 18 GARDEN WALK, #01-01, 018919, SG.") == ()
    comparison = (
        "The document says 18 GARDEN WALK, #01-01, 018919, SG, but ACRA's official record says "
        "18 OFFICIAL MOCK STREET, #01-01, 123456, SG."
    )
    assert _reasons(comparison) == ()


def test_registry_data_from_a_mock_registry_comes_with_a_notice() -> None:
    lines = knowledge_lines(FACTS, [("G1", "ACRA has the UEN 11111999A.")])
    assert lines == ["ACRA has the UEN 11111999A. [G1]"]
    validation = validate_answer(lines[0], FACTS, knowledge_lines=lines)
    assert validation.disclosures == (
        "Registry data in this case comes from ACRA (MOCK), not the live ACRA service.",
    )
    assert validate_answer(OFFERED, FACTS).disclosures == ()


# Whole answers ---------------------------------------------------------------------------


def test_only_allowed_lines_are_kept_and_the_rm_is_told() -> None:
    assert {OFFERED, OPEN_OWNERSHIP} <= set(allowed_guidance(FACTS))
    answer = f"{OFFERED}\nYou can also reject the document if it is wrong.\n{OPEN_OWNERSHIP}"
    validation = validate_answer(answer, FACTS)
    assert validation.text == f"{OFFERED}\n{OPEN_OWNERSHIP}"
    assert validation.left_out == 1
    assert validation.notice() == (
        "I left out 1 statement that I could not check against the case data."
    )


def test_free_prose_is_never_shown_even_when_every_fact_in_it_is_true() -> None:
    # Each of these passes the sentence checks, but model prose is not an allowed line.
    for answer in ("Keep the registry value.", "The UEN is 11111999A.", OFFERED[:-1]):
        assert validate_answer(answer, FACTS).text == ""


def test_chat_reply_reports_the_checks_and_tells_the_rm() -> None:
    model = FakeModel(answer=f"{OFFERED}\nThen approve the case.")
    reply = _client(FakeBackend(), model).post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": "What next?"}
    )
    body = reply.json()
    assert body["answer"] == OFFERED
    assert body["checks"] == {"removed": ["not_an_allowed_line"], "disclosures": []}
    assert "I left out 1 statement" in body["notice"]


def test_a_streamed_line_that_is_not_allowed_is_never_shown() -> None:
    model = FakeModel(answer=f"{OFFERED}\nThen approve the case.\n{OPEN_OWNERSHIP}")
    response = _client(FakeBackend(), model).post(
        f"/assistant/cases/{CASE_ID}/chat/stream", json={"message": "What next?"}
    )
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert all("approve" not in json.dumps(event).lower() for event in events[:-1])
    assert events[-1]["answer"] == f"{OFFERED}\n{OPEN_OWNERSHIP}"
    assert events[-1]["checks"]["removed"] == ["not_an_allowed_line"]


def test_an_answer_with_nothing_left_falls_back_to_case_data() -> None:
    model = FakeModel(answer="Keep the registry value. The UEN is 11111999A.")
    body = (
        _client(FakeBackend(), model)
        .post(f"/assistant/cases/{CASE_ID}/chat", json={"message": "What next?"})
        .json()
    )
    assert body["answered_by"] == "case_data"
    assert body["notice"].startswith("The model response could not be verified")
