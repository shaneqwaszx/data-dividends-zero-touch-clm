"""D-115 answer-side checks (extracted from refinement 3): application-status claims, the
evidence-aware fallback, the off-domain telemetry fix and the evaluation runner's refused turn.

Main's scope check (copilot.in_domain) and the ungated exact-line path are unchanged here.
Synthetic cases and scripted models only; no network, no paid call.
"""

from __future__ import annotations

import httpx
import pytest

from ai_assistant import copilot
from ai_assistant.claims import goldtier_status, status_problem
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.config import AiAssistantSettings
from ai_assistant.context import build_case_facts
from ai_assistant.main import create_app
from ai_assistant.telemetry import MemorySink
from tests.test_ai_assistant import CASE_ID, DOCUMENTS, ME, SUMMARY
from tests.test_copilot import Backend, Scripted, app, browser, open_context, stream

# The synthetic Garden case: GoldTier NOT_SUBMITTED, stage DOCUMENT, one open blocker, an open
# registered-address discrepancy, readiness BLOCKED.
FACTS = build_case_facts(CaseSnapshot(SUMMARY, DOCUMENTS, ME))
SUBMITTED = {**FACTS, "goldtier": {"state": "SUBMISSION_CONFIRMED", "goldtier_id": "GT-1"}}
FAILED = {**FACTS, "goldtier": {"state": "SUBMISSION_FAILED", "goldtier_id": None}}


# --- status claims the facts do not show are removed --------------------------------------------


@pytest.mark.parametrize(
    "sentence",
    [
        # Invented GoldTier outcomes.
        "GoldTier rejected the case because of the address mismatch.",
        "GoldTier accepted the customer.",
        "The submission went through.",
        "The client is now live in GoldTier.",
        "The client record now exists in GoldTier.",
        # Wrong stage, completion and readiness.
        "The case is currently in the GoldTier stage.",
        "The case is in the final approval stage.",
        "The onboarding is completed.",
        "The case is ready for GoldTier.",
        # Cleared blockers.
        "All blockers have been resolved.",
        "There are no remaining blockers.",
        "All open items are closed.",
        "The discrepancy is not open any more; it was settled.",
        # Decisions and sign-offs nobody recorded.
        "The document address is correct.",
        "The registry address wins here.",
        "The reviewer chose the document address.",
        "The chain was verified by compliance.",
        "Approval has been granted by compliance.",
        "Compliance has signed this off.",
        # A negation elsewhere never flips a claim.
        "Don't worry, the blockers have been resolved.",
        "No worries, all blockers are resolved.",
        "It is not hard: all blockers have been resolved.",
        "The blockers, not the warnings, have been resolved.",
        "Without any doubt, the case is ready for GoldTier.",
        # QG9: a time word after the claim, or in another clause, leaves it a claim.
        "The blockers were resolved before the review.",
        "When I checked, all blockers had been resolved.",
        "The case is ready for GoldTier once the review is done.",
        "The current stage is ownership review.",
        # QG10: a negation inside a longer claim, and pseudo-conditions, leave it a claim.
        "The blockers that could not be cleared earlier are now resolved.",
        "If you ask me the case is ready for GoldTier.",
        "When you open the case you will see it is ready for GoldTier.",
        "Before lunch the blockers were all resolved.",
        # Owner-blocking delta QG notes: a condition far from the claim, and a past-tense claim.
        "When you open the case you will see it is ready for GoldTier, so submit it.",
        "The case moved on once it was ready for GoldTier.",
        "The case was ready for GoldTier.",
        "The case moved on after the blockers were resolved.",
        "Once the blockers were resolved, the case moved on.",
    ],
)
def test_status_claims_the_facts_do_not_show_are_removed(sentence: str) -> None:
    assert status_problem(sentence, FACTS) == "unsupported_status", sentence
    assert copilot.check_answer(sentence, FACTS).kept == 0, sentence


@pytest.mark.parametrize(
    "sentence",
    [
        "The current stage is DOCUMENT.",
        "The document review is not finished.",
        "The blockers are not resolved yet.",
        "The case is not ready for GoldTier.",
        "The GoldTier section is blocked until the document review is finished.",
        "If the registry is right, you can choose Keep registry value on the case page.",
        "The address mismatch is still open.",
        # QG9: conditions and time clauses describe what has to happen, not what happened.
        "Once the blockers are resolved, the case can go to GoldTier.",
        "After the document review is completed, the RM can continue.",
        "It can move on when the case is ready for GoldTier.",
        "Until the discrepancy is resolved, GoldTier stays blocked.",
        "The blockers have not yet been resolved.",
        # Still hypothetical: a perfect-tense condition and a supposition.
        "Once the blockers have been resolved, the case can go to GoldTier.",
        "If the blockers were resolved, the case could go to GoldTier.",
        "If it were ready for GoldTier, the RM could submit it.",
        "The case was not ready for GoldTier.",
        # QG9: another stage named as the next one.
        "The next stage is ownership review.",
    ],
)
def test_grounded_status_statements_stay_visible(sentence: str) -> None:
    assert status_problem(sentence, FACTS) is None, sentence
    assert copilot.check_answer(sentence, FACTS).kept == 1, sentence


def test_nothing_negates_a_submission_claim() -> None:
    # QG9 (the sentence itself stays under main's submission-sentence check).
    assert goldtier_status("Nothing has been submitted to GoldTier yet.", FACTS) is True
    assert status_problem("Nothing has been submitted to GoldTier yet.", FACTS) is None
    assert status_problem("Nothing has been submitted to GoldTier yet.", SUBMITTED) is not None


def test_submission_claims_follow_the_recorded_state() -> None:
    assert goldtier_status("The GoldTier submission failed.", FAILED) is True
    assert goldtier_status("GoldTier accepted the submission.", FAILED) is False
    assert goldtier_status("The GoldTier submission failed.", FACTS) is False
    assert goldtier_status("It was submitted to GoldTier.", SUBMITTED) is True
    sending = {**FACTS, "goldtier": {"state": "SENDING", "goldtier_id": None}}
    assert goldtier_status("It has not been submitted to GoldTier yet.", sending) is False


@pytest.mark.parametrize(
    ("sentence", "facts"),
    [
        ("It has not been submitted to GoldTier yet.", FACTS),
        ("It was submitted to GoldTier.", SUBMITTED),
    ],
)
def test_submission_sentences_stay_under_mains_action_check(
    sentence: str, facts: dict[str, object]
) -> None:
    # No exemption: a correct sentence naming the submit step is removed as on main.
    assert copilot.check_answer(sentence, facts).left_out == ["action_not_allowed"]


# --- the evidence-aware fallback ----------------------------------------------------------------


def test_usable_needs_kept_sentences_and_no_more_left_out_than_kept() -> None:
    mostly = copilot.check_answer(
        "All blockers have been resolved. The case is ready for GoldTier. The document review "
        "is not finished.",
        FACTS,
    )
    assert (mostly.kept, len(mostly.left_out), mostly.usable) == (1, 2, False)
    half = copilot.check_answer(
        "All blockers have been resolved. The document review is not finished.", FACTS
    )
    assert (half.kept, len(half.left_out), half.usable) == (1, 1, True)


MOSTLY_UNSUPPORTED = (
    "GoldTier accepted the customer. All blockers have been resolved. The chain was verified "
    "by compliance. The document review is not finished."
)


@pytest.mark.parametrize("route", ["chat", "stream"])
def test_a_mostly_unsupported_answer_shows_the_case_data_answer(route: str) -> None:
    model = Scripted(MOSTLY_UNSUPPORTED)
    client = browser(app(model, Backend()), "rm-a")
    context = open_context(client, CASE_ID)
    body = {"message": "Why is this case paused?", "context_id": context}
    if route == "stream":
        done = stream(client, f"/assistant/cases/{CASE_ID}/chat/stream", body)
    else:
        done = client.post(f"/assistant/cases/{CASE_ID}/chat", json=body).json()
    assert model.calls  # the model was asked; its answer was mostly unsupported
    assert done["answered_by"] == "case_data"
    for claim in ("GoldTier accepted", "blockers have been resolved", "verified by compliance"):
        assert claim not in done["answer"]


def test_a_mostly_supported_answer_is_shown() -> None:
    model = Scripted(
        "This case is paused for a document review. The document review is not finished. "
        "All blockers have been resolved."
    )
    client = browser(app(model, Backend()), "rm-a")
    context = open_context(client, CASE_ID)
    done = stream(
        client,
        f"/assistant/cases/{CASE_ID}/chat/stream",
        {"message": "Why is this case paused?", "context_id": context},
    )
    assert done["answered_by"] == "model"
    assert "The document review is not finished." in done["answer"]
    assert "All blockers have been resolved." not in done["answer"]


# --- telemetry and the evaluation runner --------------------------------------------------------


def test_an_off_domain_question_is_recorded_in_telemetry() -> None:
    sink = MemorySink()
    model = Scripted("anything")
    settings = AiAssistantSettings(  # type: ignore[call-arg]
        _env_file=None, llm_enabled=False, answer_mode="copilot", telemetry="log"
    )
    application = create_app(
        settings,
        clm_transport=httpx.MockTransport(Backend().handler),
        chat_model=model,
        metrics=sink,
    )
    client = browser(application, "rm-a")
    context = open_context(client, CASE_ID)
    stream(
        client,
        f"/assistant/cases/{CASE_ID}/chat/stream",
        {"message": "What is the weather tomorrow?", "context_id": context},
    )
    assert model.calls == []
    assert [record.fallback_reason for record in sink.records] == ["off_domain"]


def test_the_runner_records_a_refused_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    from assistant_eval import runner
    from assistant_eval.scenarios import EVAL_FIXTURES, load_scenarios

    original = runner.settings
    monkeypatch.setattr(
        runner, "settings", lambda: original().model_copy(update={"answer_mode": "copilot"})
    )
    scenarios = load_scenarios(EVAL_FIXTURES / "phase_b_questions.json")
    model = Scripted("anything")
    with runner.Workspace() as workspace:
        result = runner.run(
            scenarios, lambda capture: model, workspace=workspace, turns=frozenset({"P07#0"})
        )
    (turn,) = result.turns
    assert (turn.key, turn.fallback_reason, turn.answered_by) == (
        "P07#0",
        "off_domain",
        "case_data",
    )
    assert turn.offered == () and model.calls == []
