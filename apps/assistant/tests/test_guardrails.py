"""The code-level safety net on model answers."""

import json
from pathlib import Path

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.guardrails import compact_facts, guard_answer

FIXTURES = Path(__file__).parent / "fixtures"


def _facts(summary: str, documents: str | None = None) -> dict[str, object]:
    load = lambda name: json.loads((FIXTURES / name).read_text())  # noqa: E731
    return build_case_facts(
        CaseSnapshot(
            load(summary), load(documents) if documents else [], load("me_client_onboarder.json")
        )
    )


WAITING = _facts("garden_waiting_for_documents_summary.json")
CONFLICT = _facts("garden_address_conflict_summary.json", "garden_documents.json")

# A real answer from ministral-3:8b that broke the prompt rules.
BAD = """Next steps:

1. Open the Document verification tab and click "Upload Document" (or similar).
2. Ensure the file is a valid company document (e.g., ACRA certificate, business license).
3. Verify the file appears in the Documents section after upload.

You can try refreshing the page or contact the Onboarding Support Team (who_resolves)."""


def test_invented_buttons_contacts_and_field_names_are_removed() -> None:
    answer = guard_answer(BAD, WAITING)

    assert "Upload Document" not in answer
    assert "Support Team" not in answer
    assert "who_resolves" not in answer
    assert "e.g." not in answer
    assert answer.splitlines()[2].startswith("1. Ensure the file is a valid company document.")
    assert answer.splitlines()[3].startswith("2. Verify the file appears")


def test_real_labels_and_facts_are_kept() -> None:
    good = 'Use "Keep registry value" in the Document verification section (from ACRA).'

    assert guard_answer(good, CONFLICT) == good


def test_snake_case_names_are_stripped_from_otherwise_good_sentences() -> None:
    answer = guard_answer("The next step is listed in actions_available_to_this_user.", CONFLICT)

    assert answer == "The next step is listed in."


def test_empty_values_are_not_sent_to_the_model() -> None:
    compact = compact_facts(
        {"a": None, "b": "", "c": [], "d": {"e": None}, "f": [{"g": ""}, 1], "h": 0}
    )

    assert compact == {"f": [1], "h": 0}


def test_an_explanation_between_steps_does_not_restart_numbering() -> None:
    from ai_assistant.guardrails import validate_answer

    answer = "Two things are missing:\n\n1. A decision.\n\nIt is about the address.\n\n2. Evidence."
    text = validate_answer(answer, {}).text
    assert "1. A decision." in text and "2. Evidence." in text
    restarted = validate_answer("Steps:\n1. One.\n2. Two.\nAlso:\n1. Three.", {}).text
    assert restarted.endswith("Also:\n1. Three.")
