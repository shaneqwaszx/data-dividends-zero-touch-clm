"""Grounding and policy validation: factual claims, action permissions and disclosures."""

import json

import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import validate_answer
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, SUMMARY, FakeBackend, FakeModel, _client
from tests.test_document_review_choices import _facts as facts_with_document_review

FACTS = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=DOCUMENTS, actor=ME))


def _reasons(answer: str, facts: dict[str, object] = FACTS) -> tuple[str, ...]:
    return validate_answer(answer, facts).removed


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
    ],
)
def test_values_that_are_not_in_the_case_facts_are_left_out(sentence: str, reason: str) -> None:
    assert _reasons(sentence) == (reason,)


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
    validation = validate_answer("ACRA has the UEN 11111999A.", FACTS)
    assert validation.disclosures == (
        "Registry data in this case comes from ACRA (MOCK), not the live ACRA service.",
    )
    assert validate_answer('Click "Keep registry value".', FACTS).disclosures == ()


# Whole answers ---------------------------------------------------------------------------


def test_only_failing_sentences_are_removed_and_the_rm_is_told() -> None:
    answer = (
        "1. Keep the registry value in Document verification.\n"
        "2. You can also reject the document if it is wrong.\n"
        "3. Then upload ownership evidence in Ownership & UBO."
    )
    validation = validate_answer(answer, FACTS)
    assert validation.text == (
        "1. Keep the registry value in Document verification.\n"
        "2. Then upload ownership evidence in Ownership & UBO."
    )
    assert validation.removed == ("action_not_allowed",)
    assert validation.notice() == (
        "I left out 1 statement that I could not check against the case data."
    )


def test_chat_reply_reports_the_checks_and_tells_the_rm() -> None:
    model = FakeModel(answer="Keep the registry value. Then approve the case.")
    reply = _client(FakeBackend(), model).post(
        f"/assistant/cases/{CASE_ID}/chat", json={"message": "What next?"}
    )
    body = reply.json()
    assert body["answer"] == "Keep the registry value."
    assert body["checks"] == {"removed": ["action_not_allowed"], "disclosures": []}
    assert "I left out 1 statement" in body["notice"]


def test_a_streamed_sentence_that_fails_a_check_is_never_shown() -> None:
    model = FakeModel(
        answer="Keep the registry value. Then approve the case. Upload ownership evidence."
    )
    response = _client(FakeBackend(), model).post(
        f"/assistant/cases/{CASE_ID}/chat/stream", json={"message": "What next?"}
    )
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert all("approve" not in json.dumps(event).lower() for event in events[:-1])
    assert events[-1]["answer"] == "Keep the registry value. Upload ownership evidence."
    assert events[-1]["checks"]["removed"] == ["action_not_allowed"]


def test_an_answer_with_nothing_left_falls_back_to_case_data() -> None:
    model = FakeModel(answer="Approve the case. The UEN is 202400001A.")
    body = (
        _client(FakeBackend(), model)
        .post(f"/assistant/cases/{CASE_ID}/chat", json={"message": "What next?"})
        .json()
    )
    assert body["answered_by"] == "case_data"
