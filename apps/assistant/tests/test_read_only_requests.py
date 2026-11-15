"""D-134 (proposed): a request to be told something is not a request to change something.

The fixed read-only reply ("I can't make that change ...") is kept for every request that the
assistant change, approve, submit or record anything. It is no longer added in front of an
informational request that merely starts with the same verb. Deterministic text only: no model
is called here.
"""

import pytest

from ai_assistant import copilot


@pytest.mark.parametrize(
    "question",
    [
        "Update me on this case",
        "Please update us about the blockers",
        "Can you update me on where the document review stands?",
        "Confirm whether the UBO check has run",
        "Confirm which documents are still missing",
        "Could you confirm if the registry data is Mock or Live?",
        "Verify whether the registered address matches ACRA",
        "OK, verify which party is below the threshold",
        "Record what is still outstanding",
        "Clear up why the case is paused",
        "Set out what happens after the document review",
        "Mark out which blockers are mine",
    ],
)
def test_a_request_to_be_told_something_gets_no_read_only_line(question: str) -> None:
    assert copilot.read_only_line(question) is None
    assert not copilot.asks_for_change(question)


@pytest.mark.parametrize(
    "question",
    [
        # Every change request the earlier tests name, unchanged.
        "Change the UEN to 12345678Z",
        "Can you approve this case?",
        "please mark the UBO verification complete",
        "Submit it to GoldTier for me",
        "Confirm the partner shares",
        "Approve this case and send it to GoldTier for me.",
        "Change the registered address to the one in the document.",
        "Can you mark the UBO check as complete?",
        # The same verbs without a question word are still change requests.
        "Update the address to the ACRA one",
        "Update my case",
        "Confirm the registry value",
        "Confirm that the address matches",
        "Verify the documents",
        "Record the correction",
        "Clear the blocker",
        "Set the risk rating to low",
        "Mark the review complete",
        # An informational opening never carries a change request in behind it.
        "Confirm whether it is approved and approve it if not",
        "Update me on the case, then submit it to GoldTier",
        "Verify whether the address matches and fix it",
        "Confirm which documents are missing and upload them for me",
        "Confirm whether you can do this on my behalf",
        "Update me on the case and mark the UBO check complete",
        "Clear up why it is paused and resolve it",
        # Kept on the safe side: a change verb used as a noun after the opening still counts.
        "Could you confirm if the registry record is Mock or Live?",
    ],
)
def test_a_request_to_change_something_still_gets_the_read_only_line(question: str) -> None:
    assert copilot.read_only_line(question) == copilot.READ_ONLY_LINE


@pytest.mark.parametrize(
    "question",
    [
        "How do I change the registered address?",
        "Why can't this case be submitted?",
        "Who can approve the UBO check?",
        "What should I do next?",
    ],
)
def test_ordinary_questions_are_unchanged(question: str) -> None:
    assert copilot.read_only_line(question) is None
