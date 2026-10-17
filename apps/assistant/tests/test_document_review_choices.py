"""The AI Assistant offers the same document-review choices the case page shows."""

import copy
from typing import Any

from ai_assistant.briefing import opening_message
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import guard_answer
from ai_assistant.prompts import build_messages
from tests.test_ai_assistant import DOCUMENTS, ME, SUMMARY

CHOICES = ["Accept document suggestion", "Reject document suggestion", "Record correction"]


def _facts(*, fingerprint: bool = True, authorized: bool = True) -> dict[str, Any]:
    documents = copy.deepcopy(DOCUMENTS if isinstance(DOCUMENTS, list) else DOCUMENTS["documents"])
    for document in documents:
        document["review_source_fingerprint"] = "fp-1" if fingerprint else None
    summary = {**SUMMARY, "evidence_decision_authorized": authorized}
    return build_case_facts(CaseSnapshot(summary=summary, documents=documents, actor=ME))


def test_pending_document_fields_list_the_review_choices_shown_on_the_page() -> None:
    review = _facts()["document_field_review"]
    assert review["where"] == (
        'Review blocker decisions panel, decision group "Review extracted document fields"'
    )
    address = [row for row in review["fields"] if row["field"] == "registered address"]
    assert address and address[0]["choices"] == CHOICES
    assert address[0]["document_value"] == "18 GARDEN WALK, #01-01, 018919, SG"
    assert "Keep registry value" in review["not_the_same_as"]


def test_no_review_choices_when_the_page_would_not_offer_them() -> None:
    assert _facts(fingerprint=False)["document_field_review"] is None
    assert _facts(authorized=False)["document_field_review"] is None


def test_both_decision_groups_reach_the_model_and_the_opening_summary() -> None:
    facts = _facts()
    prompt = build_messages(facts, [], "What options do I have?")[1]["content"]
    assert "Keep registry value" in prompt
    assert all(choice in prompt for choice in CHOICES)
    summary = opening_message(facts)
    assert '"Keep registry value"' in summary
    assert '"Review extracted document fields"' in summary and '"Record correction"' in summary


def test_guardrails_keep_an_answer_that_names_the_review_choices() -> None:
    answer = "\n".join(
        f'Document verification offers "{choice}" to review the extracted field; '
        "this does not decide registry/document precedence."
        for choice in CHOICES
    )
    assert guard_answer(answer, _facts()) == answer
    assert guard_answer(answer, _facts(authorized=False)) == ""
