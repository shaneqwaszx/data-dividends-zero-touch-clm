"""Phase B answer quality (D-092 P11 to P14, proposed).

Owner-approved, topic-only catalog lines for questions the owner's Phase B scoring rejected or
marked incomplete: company directors (P00#0, P01#2, P01#3), the entity status versus a live
registry connection (P01#1), the UEN (P01#0) and the GoldTier handoff (P04#1). Each line is
allowed only under its backend-derived condition and is shown to the model only in the
QUESTION TOPIC message, so the everyday prompt does not change. The registry officer lookup is
projected as a status only (P11): never names, roles, ids or counts.
"""

import copy
import json
from typing import Any

import pytest

from ai_assistant.briefing import CONTACT, DIFFERENCE, question_topic
from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import SELECTION_ONLY_FACTS, build_case_facts
from ai_assistant.guardrails import (
    Context,
    allowed_guidance,
    knowledge_lines,
    officers_line,
    sentence_problem,
    validate_answer,
    with_required_lines,
)
from ai_assistant.guide import (
    DIRECTOR_DIFFERENCE_CHECK,
    DIRECTOR_DIFFERENCE_REASONS,
    DIRECTORS_NOT_READ,
    ENTITY_STATUS_LIVE,
    MOCK_NOT_LIVE,
    NOT_READY,
    OFFICERS_NOT_RETRIEVED,
    OUT_OF_SCOPE,
    SEND_BEFORE_SUBMISSION,
    SENDING_IS_NOT_APPROVAL,
    SUBMISSION_RESULT_KEPT,
    UBO_CHECK_NOT_RUN,
    UBO_COMPLETION_NOT_OFFERED,
    UEN_MEANING,
    is_topic_only,
    officers_empty_line,
)
from ai_assistant.prompts import (
    build_messages,
    case_facts_message,
    facts_for_model,
    topic_message,
    topic_plan,
)
from assistant_eval.variants import base_inputs
from tests.test_source_and_owner_topics import _Fixed, _phase_b

MOCK_SOURCE = "Registry data in this case comes from ACRA (MOCK), not the live ACRA service."
OFFICERS_EMPTY_MOCK = (
    "The ACRA (MOCK) result for this case has no officer (director) records; this does not show "
    "that the company has no directors."
)
REGISTRY_SECTION = 'Open the "Registry verification" section to inspect the current case evidence.'
DOCUMENT_SECTION = 'Open the "Document verification" section to inspect the current case evidence.'
GOLDTIER_SECTION = (
    'Open the "GoldTier Details & Status" section to inspect the current case evidence.'
)
NEW_FIXED_LINES = (
    DIRECTORS_NOT_READ,
    OFFICERS_NOT_RETRIEVED,
    DIRECTOR_DIFFERENCE_CHECK,
    DIRECTOR_DIFFERENCE_REASONS,
    ENTITY_STATUS_LIVE,
    UEN_MEANING,
    SEND_BEFORE_SUBMISSION,
    SUBMISSION_RESULT_KEPT,
    SENDING_IS_NOT_APPROVAL,
)


def _inputs() -> Any:
    return base_inputs("garden_address_conflict")


def _facts(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    case = _inputs()
    return build_case_facts(CaseSnapshot(summary or case.summary, case.documents, case.actor))


FACTS = _facts()


def _summary() -> dict[str, Any]:
    return copy.deepcopy(_inputs().summary)


def _officer_result(summary: dict[str, Any]) -> dict[str, Any]:
    acquisition = summary["case"]["registry_acquisition"]
    (result,) = [r for r in acquisition["operation_results"] if r["operation"] == "OFFICERS"]
    return dict(result)


def _with(facts: dict[str, Any], **changes: Any) -> dict[str, Any]:
    facts = copy.deepcopy(facts)
    for key, value in changes.items():
        facts[key] = value
    return facts


# --- the approved wording ------------------------------------------------------------------------


def test_the_wording_is_the_owner_approved_wording() -> None:
    assert DIRECTORS_NOT_READ == (
        "The app does not read directors from uploaded documents, so it does not compare "
        "directors between a document and ACRA."
    )
    assert OFFICERS_NOT_RETRIEVED == (
        "Officer (director) records were not retrieved from the registry for this case."
    )
    assert DIRECTOR_DIFFERENCE_CHECK == (
        "If a document and the registry differ on directors, check the document's type, date "
        "and which company it is for."
    )
    assert DIRECTOR_DIFFERENCE_REASONS == (
        "A director difference can come from a recent appointment or resignation, or from an "
        "out-of-date document."
    )
    assert officers_empty_line("MOCK") == OFFICERS_EMPTY_MOCK
    assert ENTITY_STATUS_LIVE == (
        'The entity status "LIVE" is the company\'s registration status in the registry record, '
        "not a live connection to ACRA."
    )
    assert UEN_MEANING == (
        "A UEN (Unique Entity Number) identifies an entity registered in Singapore. The number "
        "alone does not confirm its legal name, address or other company details."
    )
    assert SEND_BEFORE_SUBMISSION == (
        'A person must confirm Send in "Final review & send" before the final GoldTier '
        "submission; the app may search GoldTier for an existing customer earlier."
    )
    assert SUBMISSION_RESULT_KEPT == (
        "When a GoldTier submission is confirmed, the app retains the submission result and "
        'required customer readback. The result is shown in "GoldTier Details & Status".'
    )
    assert SENDING_IS_NOT_APPROVAL == (
        "Sending a case does not mean GoldTier has approved the customer or that KYC is "
        "complete. Those outcomes are not confirmed by this application."
    )


@pytest.mark.parametrize("line", [*NEW_FIXED_LINES, OFFICERS_EMPTY_MOCK])
def test_every_new_line_passes_the_unchanged_sentence_checks(line: str) -> None:
    assert sentence_problem(line, FACTS) is None


@pytest.mark.parametrize(
    "g4",
    [
        "This case is configured for Mock GoldTier or GoldTier Sandbox in the POC, not "
        "production GoldTier.",
        "This case is configured for Mock GoldTier in the POC, not production GoldTier.",
        "This case is configured for GoldTier Sandbox in the POC, not production GoldTier.",
    ],
)
def test_the_held_g4_wording_still_fails_the_live_claim_check(g4: str) -> None:
    # G4 was held, not added: the existing live-claim check refuses "production GoldTier".
    assert sentence_problem(g4, FACTS) == "live_claim"
    assert g4 not in allowed_guidance(FACTS)


# --- P11: the officer lookup status --------------------------------------------------------------


def test_the_projection_is_the_status_only() -> None:
    assert FACTS["registry_officers"] == "EMPTY"
    summary = _summary()
    acquisition = summary["case"]["registry_acquisition"]
    acquisition["officers"] = [
        {"officer_id": "OFF-SYN-1", "name": "SYNTHETIC OFFICER ONE", "role": "DIRECTOR"}
    ]
    for result in acquisition["operation_results"]:
        if result["operation"] == "OFFICERS":
            result.update(status="COMPLETE", record_count=1)
    facts = _facts(summary)
    assert facts["registry_officers"] == "COMPLETE"
    dumped = json.dumps(facts) + json.dumps(build_messages(facts, [], "Who are the directors?"))
    for value in ("SYNTHETIC OFFICER ONE", "OFF-SYN-1"):
        assert value not in dumped


def _officers_from(change: dict[str, Any], acquisition_change: dict[str, Any] | None = None) -> Any:
    summary = _summary()
    acquisition = summary["case"]["registry_acquisition"]
    acquisition.update(acquisition_change or {})
    for result in acquisition["operation_results"]:
        if result["operation"] == "OFFICERS":
            result.update(change)
    return _facts(summary)["registry_officers"]


@pytest.mark.parametrize("status", ["FAILED", "NOT_ATTEMPTED", "UNSUPPORTED", "COMPLETE"])
def test_other_lookup_statuses_are_passed_through(status: str) -> None:
    assert _officers_from({"status": status}) == status


@pytest.mark.parametrize(
    ("change", "acquisition_change"),
    [
        ({}, {"status": "FAILED"}),  # a failed acquisition never yields "no records"
        ({"record_count": 1}, None),
        ({}, {"officers": [{"officer_id": "x", "name": "y", "role": "z"}]}),
        ({"error": {"code": "TIMEOUT"}}, None),
        ({"provenance": {"provider": "ACRA", "environment": "SANDBOX"}}, None),
        ({"provenance": {"provider": "OTHER", "environment": "MOCK"}}, None),
        ({"provenance": None}, None),
        ({}, {"requested_identifier": "22222999B"}),  # another company's lookup
        ({"status": "SOMETHING_NEW"}, None),
    ],
)
def test_empty_is_never_inferred(change: dict[str, Any], acquisition_change: Any) -> None:
    assert _officers_from(change, acquisition_change) is None


def test_a_missing_or_duplicated_lookup_gives_no_status() -> None:
    summary = _summary()
    del summary["case"]["registry_acquisition"]
    assert _facts(summary)["registry_officers"] is None
    summary = _summary()
    acquisition = summary["case"]["registry_acquisition"]
    acquisition["operation_results"] = [
        r for r in acquisition["operation_results"] if r["operation"] != "OFFICERS"
    ]
    assert _facts(summary)["registry_officers"] is None
    summary = _summary()
    acquisition = summary["case"]["registry_acquisition"]
    acquisition["operation_results"].append(_officer_result(summary))
    assert _facts(summary)["registry_officers"] is None


# --- conditions ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "line"),
    [
        ("EMPTY", OFFICERS_EMPTY_MOCK),
        ("FAILED", OFFICERS_NOT_RETRIEVED),
        ("NOT_ATTEMPTED", OFFICERS_NOT_RETRIEVED),
        ("UNSUPPORTED", OFFICERS_NOT_RETRIEVED),
        ("COMPLETE", None),
        (None, None),
    ],
)
def test_the_officer_line_follows_the_lookup_status(status: str | None, line: str | None) -> None:
    facts = _with(FACTS, registry_officers=status)
    assert officers_line(facts) == line
    guidance = allowed_guidance(facts)
    for other in (OFFICERS_EMPTY_MOCK, OFFICERS_NOT_RETRIEVED):
        assert (other in guidance) == (other == line)


def test_no_records_needs_a_ready_registry_and_a_named_non_live_acra_source() -> None:
    sandbox = copy.deepcopy(FACTS)
    sandbox["company"]["source"] = "ACRA (SANDBOX), retrieved 5 Oct 2026, 04:02 UTC"
    assert officers_line(sandbox) == officers_empty_line("SANDBOX")
    for source in ("ACRA (LIVE)", "ACRA", "Details entered when the case was created"):
        facts = copy.deepcopy(FACTS)
        facts["company"]["source"] = source
        assert officers_line(facts) is None
    for status in ("REVIEW_REQUIRED", "BLOCKED", "FAILED", None):
        facts = copy.deepcopy(FACTS)
        facts["readiness"]["sections"]["registry"] = status
        assert officers_line(facts) is None


@pytest.mark.parametrize(
    ("status", "source", "offered"),
    [
        ("LIVE", "ACRA (MOCK), retrieved 5 Oct 2026, 04:02 UTC", True),
        ("LIVE", "ACRA (SANDBOX)", True),
        ("LIVE", "ACRA (LIVE)", False),
        ("LIVE", "Details entered when the case was created", False),
        ("STRUCK OFF", "ACRA (MOCK)", False),
        ("live", "ACRA (MOCK)", False),
        (None, "ACRA (MOCK)", False),
    ],
)
def test_the_entity_status_line_needs_live_status_and_a_non_live_source(
    status: str | None, source: str, offered: bool
) -> None:
    facts = copy.deepcopy(FACTS)
    facts["company"].update(entity_status=status, source=source)
    assert (ENTITY_STATUS_LIVE in allowed_guidance(facts)) == offered


@pytest.mark.parametrize(
    ("uen", "country", "offered"),
    [("11111999A", "SG", True), ("11111999A", "MY", False), (None, "SG", False), ("", "SG", False)],
)
def test_the_uen_line_needs_a_singapore_uen(uen: str | None, country: str, offered: bool) -> None:
    facts = copy.deepcopy(FACTS)
    facts["company"].update(uen=uen, country=country)
    assert (UEN_MEANING in allowed_guidance(facts)) == offered


def _target(state: str, readback: str | None) -> dict[str, Any]:
    summary = _summary()
    summary["target_submission"]["state"] = state
    operations = [op for op in summary["target_operations"] if op["operation"] != "READBACK"]
    if readback is not None:
        operations.append({"operation": "READBACK", "status": readback})
    summary["target_operations"] = operations
    return _facts(summary)


@pytest.mark.parametrize(
    ("state", "readback", "offered"),
    [
        ("SUBMISSION_CONFIRMED", "SUCCESS", True),
        ("SUBMISSION_CONFIRMED", None, False),
        ("SUBMISSION_CONFIRMED", "NOT_ATTEMPTED", False),
        ("SUBMISSION_CONFIRMED", "FAILED", False),
        ("FINALIZATION_PENDING", "SUCCESS", False),
        ("SUBMISSION_OUTCOME_UNCERTAIN", "SUCCESS", False),
        ("SENDING", "SUCCESS", False),
        ("NOT_SUBMITTED", "SUCCESS", False),
    ],
)
def test_the_submission_result_line_needs_a_confirmed_submission_and_readback(
    state: str, readback: str | None, offered: bool
) -> None:
    facts = _target(state, readback)
    assert facts["goldtier_readback"] == readback
    assert (SUBMISSION_RESULT_KEPT in allowed_guidance(facts)) == offered


def test_the_always_true_lines_are_allowed_on_the_phase_b_case() -> None:
    guidance = allowed_guidance(FACTS)
    for line in (
        DIRECTORS_NOT_READ,
        DIRECTOR_DIFFERENCE_CHECK,
        DIRECTOR_DIFFERENCE_REASONS,
        SEND_BEFORE_SUBMISSION,
        SENDING_IS_NOT_APPROVAL,
        OFFICERS_EMPTY_MOCK,
        ENTITY_STATUS_LIVE,
        UEN_MEANING,
    ):
        assert line in guidance
    assert SUBMISSION_RESULT_KEPT not in guidance  # not submitted


# --- topic-only ----------------------------------------------------------------------------------


def test_every_new_line_is_topic_only() -> None:
    confirmed = _target("SUBMISSION_CONFIRMED", "SUCCESS")
    for facts in (FACTS, confirmed):
        shown = facts_for_model(facts)["allowed_guidance"]
        message = case_facts_message(facts)
        for line in [*NEW_FIXED_LINES, OFFICERS_EMPTY_MOCK]:
            assert is_topic_only(line)
            assert line not in shown and line not in message
    for sent in build_messages(FACTS, [], "What should I do next?"):
        assert not any(line in sent["content"] for line in NEW_FIXED_LINES)
        assert OFFICERS_EMPTY_MOCK not in sent["content"]


@pytest.mark.parametrize(
    "body",
    [
        'Open the "Officers" tab to see who the directors are.',
        'Press "Readback" to refresh the lookup.',
        'Choose "Empty" when no officer is listed.',
        'A "Success" banner means the readback finished.',
        'Check "registry_officers" before answering.',
        'Check "goldtier_readback" before sending.',
    ],
)
def test_selection_only_facts_never_ground_knowledge_text(body: str) -> None:
    # QG R1 H1: the two selection-only values must not let a quoted label pass the sentence
    # checks; the result must match the case without them.
    confirmed = _target("SUBMISSION_CONFIRMED", "SUCCESS")
    for facts in (FACTS, confirmed, _with(FACTS, registry_officers="FAILED")):
        plain = copy.deepcopy(facts)
        for key in SELECTION_ONLY_FACTS:
            plain.pop(key)
        assert sentence_problem(body, facts) == sentence_problem(body, plain) == "invented_label"
        assert knowledge_lines(facts, [("G1", body)]) == []
        result = validate_answer(f"{body} [G1]", facts)
        assert result.text == "" and result.left_out == 1


def test_selection_only_facts_are_the_two_new_keys() -> None:
    # D-095 adds the officer records, which choose officer lines only.
    assert set(SELECTION_ONLY_FACTS) == {
        "registry_officers",
        "goldtier_readback",
        "registry_officer_records",
    }
    known = Context(FACTS).known
    assert all(key not in known for key in SELECTION_ONLY_FACTS)


def test_the_everyday_prompt_is_unchanged_by_the_new_facts() -> None:
    plain = copy.deepcopy(FACTS)
    plain.pop("registry_officers")
    plain.pop("goldtier_readback")
    assert facts_for_model(FACTS) == facts_for_model(plain)


# --- routing -------------------------------------------------------------------------------------

DIRECTOR_DIFFERENCE_PLAN = (
    DIRECTORS_NOT_READ,
    OFFICERS_EMPTY_MOCK,
    DIRECTOR_DIFFERENCE_CHECK,
    DIRECTOR_DIFFERENCE_REASONS,
    REGISTRY_SECTION,
    DOCUMENT_SECTION,
)
ROUTED = {
    "What information should a Relationship Manager review when onboarding a Singapore company "
    "whose directors differ between a document and registry evidence?": DIRECTOR_DIFFERENCE_PLAN,
    "What does this case's UEN tell me, and where did the company details come from?": (
        UEN_MEANING,
        MOCK_SOURCE,
        REGISTRY_SECTION,
    ),
    "Which registry was used for this company, and is that registry live?": (
        MOCK_SOURCE,
        ENTITY_STATUS_LIVE,
        MOCK_NOT_LIVE,
    ),
    "Who are the directors of this company according to ACRA?": (
        OFFICERS_EMPTY_MOCK,
        REGISTRY_SECTION,
    ),
    "A director named in the uploaded document is not in the ACRA record. What should I do?": (
        DIRECTOR_DIFFERENCE_PLAN
    ),
    "What happens when the case is handed off to GoldTier?": (
        NOT_READY,
        SEND_BEFORE_SUBMISSION,
        SENDING_IS_NOT_APPROVAL,
        GOLDTIER_SECTION,
    ),
    "Does the LIVE status mean the registry is live?": (
        MOCK_SOURCE,
        ENTITY_STATUS_LIVE,
        MOCK_NOT_LIVE,
    ),
    "What does the LIVE status mean?": (ENTITY_STATUS_LIVE, MOCK_SOURCE),
}


@pytest.mark.parametrize("question", list(ROUTED))
def test_phase_b_questions_are_routed_to_the_approved_lines(question: str) -> None:
    plan = topic_plan(FACTS, question)
    assert plan is not None
    assert plan.lines == ROUTED[question] and plan.required == ()
    message = topic_message(FACTS, question)
    assert message is not None and all(line in message for line in plan.lines)


def test_the_handoff_plan_adds_the_result_line_after_a_confirmed_submission() -> None:
    facts = _target("SUBMISSION_CONFIRMED", "SUCCESS")
    plan = topic_plan(facts, "What happens when the case is handed off to GoldTier?")
    assert plan is not None and SUBMISSION_RESULT_KEPT in plan.lines


def test_a_director_question_without_a_lookup_status_is_still_explained() -> None:
    facts = _with(FACTS, registry_officers=None)
    plan = topic_plan(facts, "Who are the directors of this company according to ACRA?")
    assert plan is not None and plan.lines == (REGISTRY_SECTION,)
    failed = _with(FACTS, registry_officers="FAILED")
    plan = topic_plan(failed, "Who are the directors of this company according to ACRA?")
    assert plan is not None and plan.lines == (OFFICERS_NOT_RETRIEVED, REGISTRY_SECTION)


@pytest.mark.parametrize(
    "question",
    [
        # The app's Director role, not the company's directors.
        "Which Director approves knowledge for this company?",
        "Ask a Director to review the document.",
        "Can a Director publish this enhancement for the registry?",
        "Does the Director role have permission to see this document?",
        "Escalate to the Director about the ACRA record.",
        "Could a Director override the ACRA record?",  # QG R1 L1
        # Staff roles named "officer", not the company's officers (QG R1 L1).
        "Who is the compliance officer for this case?",
        "Which onboarding officer handles this case?",
        "Who is the compliance officer of this company?",
        "Is there a KYC officer named on the document?",
        # Unrelated.
        "What is the weather in Singapore today?",
        "Write me a Python script that downloads company records from ACRA.",
        "What ownership percentage makes someone a UBO here?",
    ],
)
def test_other_questions_get_no_director_plan(question: str) -> None:
    plan = topic_plan(FACTS, question)
    assert plan is None or not ({DIRECTORS_NOT_READ, OFFICERS_EMPTY_MOCK} & set(plan.lines))


@pytest.mark.parametrize(
    "question",
    ["Which officers does ACRA list for this company?", "Who are the officers of this company?"],
)
def test_company_officer_questions_get_the_lookup_plan(question: str) -> None:
    plan = topic_plan(FACTS, question)
    assert plan is not None and plan.lines == (OFFICERS_EMPTY_MOCK, REGISTRY_SECTION)


def test_contact_and_named_field_topics_keep_precedence_over_directors() -> None:
    assert question_topic("Who should I contact about a director mismatch?", FACTS) is not None
    contact = question_topic("Who should I contact about a director mismatch?", FACTS)
    assert contact is not None and contact[0] == CONTACT
    plan = topic_plan(FACTS, "Who should I contact about a director mismatch?")
    assert plan is None or DIRECTORS_NOT_READ not in plan.lines
    question = "The directors and the registered address differ in the document. Which is right?"
    topic = question_topic(question, FACTS)
    assert topic is not None and topic[0] == DIFFERENCE
    plan = topic_plan(FACTS, question)
    assert plan is not None and DIRECTORS_NOT_READ not in plan.lines


def test_the_ubo_completion_refusal_is_unchanged() -> None:
    plan = topic_plan(FACTS, "Can you mark the UBO check as complete?")
    assert plan is not None and plan.required == ()
    assert plan.lines == (
        UBO_COMPLETION_NOT_OFFERED,
        UBO_CHECK_NOT_RUN,
        "Ownership (shareholder) evidence is needed before the UBO check can run. "
        "(section: Ownership & UBO)",
        'Open the "Ownership & UBO" section to inspect the current case evidence.',
    )


@pytest.mark.parametrize(
    "question",
    [
        "What ownership percentage makes someone a UBO here?",
        "What documents are still missing before this case can move on?",
        "What is the weather in Singapore today?",
        "Write me a Python script that downloads company records from ACRA.",
    ],
)
def test_unrelated_phase_b_questions_stay_unrouted(question: str) -> None:
    assert topic_plan(FACTS, question) is None


# --- the guard -----------------------------------------------------------------------------------


@pytest.mark.parametrize("line", [*NEW_FIXED_LINES, OFFICERS_EMPTY_MOCK])
def test_new_lines_are_shown_verbatim_only_where_allowed(line: str) -> None:
    facts = _target("SUBMISSION_CONFIRMED", "SUCCESS")
    if line == OFFICERS_NOT_RETRIEVED:
        facts = _with(facts, registry_officers="FAILED")
    result = validate_answer(line.upper(), facts)
    assert result.text == line and result.left_out == 0


def test_conditional_lines_are_withheld_where_not_allowed() -> None:
    no = copy.deepcopy(FACTS)
    no["company"].update(entity_status="STRUCK OFF", country="MY")
    no["registry_officers"] = "COMPLETE"
    for line in (OFFICERS_EMPTY_MOCK, OFFICERS_NOT_RETRIEVED, ENTITY_STATUS_LIVE, UEN_MEANING):
        result = validate_answer(line, no)
        assert result.text == "" and result.left_out == 1
    result = validate_answer(SUBMISSION_RESULT_KEPT, FACTS)
    assert result.text == "" and result.left_out == 1


@pytest.mark.parametrize(
    "claim",
    [
        "The company has no directors.",
        "ACRA shows that this company has no directors.",
        "The director in the document is wrong.",
        "The directors differ between the document and ACRA on this case.",
        "The registry connection is live.",
        "ACRA is live for this case.",
        "The UEN confirms the company's legal name and address.",
        "A UEN (Unique Entity Number) identifies an entity registered in Singapore.",
        "GoldTier has approved the customer.",
        "KYC is complete.",
        "The case was sent to GoldTier.",
        "I have sent the case to GoldTier.",
    ],
)
def test_unsupported_claims_and_partial_lines_are_withheld(claim: str) -> None:
    facts = _target("SUBMISSION_CONFIRMED", "SUCCESS")
    result = validate_answer(claim, facts)
    assert result.text == "" and result.left_out == 1


def test_a_bare_decline_on_the_new_topics_is_not_padded() -> None:
    decline = validate_answer(OUT_OF_SCOPE, FACTS)
    for question in ROUTED:
        plan = topic_plan(FACTS, question)
        assert plan is not None
        padded = with_required_lines(decline, FACTS, order=plan.lines, required=plan.required)
        assert padded.text == OUT_OF_SCOPE


# --- through the service on the Phase B case -----------------------------------------------------


@pytest.mark.parametrize(
    ("key", "answer"),
    [
        ("P00#0", "\n".join(DIRECTOR_DIFFERENCE_PLAN[:4])),
        ("P01#0", f"{UEN_MEANING}\n{MOCK_SOURCE}"),
        ("P01#1", f"{MOCK_SOURCE}\n{ENTITY_STATUS_LIVE}"),
        ("P01#2", OFFICERS_EMPTY_MOCK),
        ("P04#1", f"{NOT_READY}\n{SEND_BEFORE_SUBMISSION}\n{SENDING_IS_NOT_APPROVAL}"),
    ],
)
def test_phase_b_turns_show_the_new_lines_verbatim(key: str, answer: str) -> None:
    (turn,) = _phase_b(_Fixed(answer), frozenset({key}))
    assert turn.key == key and turn.answered_by == "model" and turn.unmapped == 0
    assert turn.answer_text == answer
