"""Build the messages sent to the model. The case facts are the only source it may use.

Speed matters on a small local model: every token in the prompt has to be read and every
token in the answer has to be written. So the model gets a short, plain view of the case
(not the full fact sheet), and messages are ordered so the start of the prompt stays the
same between questions. The model server can then reuse its earlier reading of that part
(prompt caching) and only read what is new:

    1. rules            - same for every case and question
    2. case facts       - same for every question about this case, until the case changes
    3. chat history     - grows by one turn per question
    4. knowledge        - allowed lines from retrieved guidance and past cases (tagged)
    5. question topic   - the question's topic (a difference, the document review, ownership,
                          readiness, approval, who to contact) and its allowed lines to give
                          first
    6. page terms       - only the glossary entries this question asks about
    7. the question
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from .briefing import (
    APPROVE,
    BLOCKERS,
    CONTACT,
    DIFFERENCE,
    DOCUMENT_REVIEW,
    OWNERSHIP,
    READINESS,
    _named,
    question_topic,
)
from .context import readable_time as when
from .guardrails import (
    allowed_guidance,
    compact_facts,
    officer_record_lines,
    officers_line,
    registry_source_line,
    ubo_completion_not_offered,
    who_resolves_lines,
)
from .guide import (
    ANY_DIFFERENCE,
    APPROVAL_NOT_OFFERED,
    DIRECTOR_DIFFERENCE_CHECK,
    DIRECTOR_DIFFERENCE_REASONS,
    DIRECTORS_NOT_READ,
    ENTITY_STATUS_LIVE,
    FIELD_DIFFERENCE,
    MOCK_NOT_LIVE,
    NO_CONTACT,
    NOT_READY,
    READINESS_EXPLANATIONS,
    READINESS_NEEDS,
    SEND_BEFORE_SUBMISSION,
    SENDING_IS_NOT_APPROVAL,
    SUBMISSION_RESULT_KEPT,
    UBO_CHECK_NOT_RUN,
    UBO_COMPLETION_NOT_OFFERED,
    UEN_MEANING,
    difference_line,
    is_topic_only,
)
from .instructions import system_prompt
from .privacy_boundary import trusted_text as _privacy_trusted

# The rules live in instructions/persona_and_rules.md so they can be edited as plain text.
SYSTEM_PROMPT = system_prompt()

MAX_TIMELINE_FOR_MODEL = 5
MAX_HISTORY_CHARS = 2400
MAX_HISTORY_TURN_CHARS = 700
_WORD = re.compile(r"[a-z]+")


_COMPARISON = {
    "MATCH": "matches ACRA",
    "MISMATCH": "differs from ACRA",
    "CONFLICT": "differs from ACRA",
}


def _field_line(field: dict[str, Any]) -> str:
    comparison = str(field.get("compared_with_registry") or "")
    details = [
        _COMPARISON.get(comparison, comparison.lower() or None),
        str(field["review_status"]).lower() if field.get("review_status") else None,
        f"score {field['confidence']}" if field.get("confidence") is not None else None,
    ]
    shown = ", ".join(part for part in details if part)
    value = field.get("value_read_from_document") or "(nothing read)"
    return f"{field.get('field')}: {value}" + (f" ({shown})" if shown else "")


def _steps_for_model(steps: list[dict[str, Any]]) -> dict[str, Any]:
    done = [step["step"] for step in steps if step.get("status") == "done"]
    others = [
        f"{step['step']}: {step.get('status')}"
        + (f" ({step['result']})" if step.get("result") else "")
        for step in steps
        if step.get("status") != "done"
    ]
    return {"done": done, "not_done": others}


def _blocker_for_model(blocker: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """The blocker, without what is already an allowed line (its explanation, difference values)."""

    explanation = blocker.get("plain_explanation") or blocker.get("app_explanation")
    view = {
        "title": blocker.get("title"),
        "stage": blocker.get("stage"),
        "explanation": None if explanation in allowed else explanation,
        "what_is_needed": blocker.get("what_is_needed"),
        "actions_available_to_this_user": blocker.get("actions_available_to_this_user"),
        "screens_to_open": blocker.get("screens_to_open"),
        "why_no_action": blocker.get("why_no_action"),
        "who_resolves": blocker.get("who_resolves"),
        "next_step": blocker.get("expected_next_step") or blocker.get("resolution_condition"),
        "differences": [
            {
                "field": row.get("field"),
                "acra_value": row.get("registry_value"),
                "document_value": row.get("document_value"),
            }
            for row in blocker.get("differences") or []
            if difference_line(row) not in allowed
        ],
    }
    return view


def _discrepancy_for_model(item: dict[str, Any]) -> dict[str, Any]:
    by_value: dict[str, list[str]] = {}
    for observation in item.get("values") or []:
        value = str(observation.get("value"))
        by_value.setdefault(value, []).append(str(observation.get("from")))
    return {
        "field": item.get("field"),
        "status": item.get("status"),
        "values": [f"{value} (from {', '.join(sources)})" for value, sources in by_value.items()],
        "decision": item.get("decision"),
        "decided_value": item.get("decided_value"),
    }


def _document_review_for_model(review: dict[str, Any] | None) -> dict[str, Any] | None:
    """The document-review choices, said once, with one short line per field to review."""

    if not review:
        return None
    choices: list[str] = []
    by_field: dict[str, list[str]] = {}
    for row in review.get("fields") or []:
        for choice in row.get("choices") or []:
            if choice not in choices:
                choices.append(choice)
        by_field.setdefault(
            f"{row.get('field')}: document says {row.get('document_value') or '(nothing read)'}",
            [],
        ).append(str(row.get("document")))
    return {
        "where": review.get("where"),
        "what_it_decides": review.get("what_it_decides"),
        "not_the_same_as": review.get("not_the_same_as"),
        "choices": {
            choice: (review.get("choice_meanings") or {}).get(choice) for choice in choices
        },
        "fields_to_review": [f"{line} (in {', '.join(docs)})" for line, docs in by_field.items()],
    }


def facts_for_model(facts: dict[str, Any]) -> dict[str, Any]:
    """A short view of the case facts for the model; nothing new, only less. Facts that are
    already word for word in an allowed line are not repeated."""

    readiness = facts.get("readiness") or {}
    guidance = allowed_guidance(facts)
    allowed = set(guidance)
    view = {
        # Topic-only lines stay allowed but are shown only in their QUESTION TOPIC message.
        "allowed_guidance": [line for line in guidance if not is_topic_only(line)],
        "viewer": facts.get("viewer"),
        "company": facts.get("company"),
        "overall": {
            key: value
            for key, value in (facts.get("overall") or {}).items()
            if key != "current_stage"
        },
        "steps": _steps_for_model(facts.get("steps") or []),
        "blockers": [
            _blocker_for_model(blocker, allowed) for blocker in facts.get("blockers") or []
        ],
        "still_needed_before_goldtier": [
            need
            for need in facts.get("still_needed_before_goldtier") or []
            if f"{need.get('what')} (section: {need.get('where_on_the_case_page')})" not in allowed
        ],
        "system_problem": facts.get("system_problem"),
        "readiness_sections": readiness.get("sections"),
        "discrepancies": [
            _discrepancy_for_model(item) for item in facts.get("discrepancies") or []
        ],
        "documents": [
            {
                "name": document.get("name"),
                "type": document.get("detected_type"),
                "state": document.get("state"),
                "values_read": [_field_line(field) for field in document.get("fields") or []],
            }
            for document in facts.get("documents") or []
        ],
        "document_field_review": _document_review_for_model(facts.get("document_field_review")),
        "goldtier": facts.get("goldtier"),
        "recent_events": [
            f"{when(event.get('when'))}: {event.get('what')}"
            for event in (facts.get("timeline") or [])[-MAX_TIMELINE_FOR_MODEL:]
        ],
        "case_page_sections": [
            section
            for section in facts.get("case_page_sections") or []
            if _open_section(section) not in allowed
        ],
    }
    compacted: dict[str, Any] = compact_facts(view)
    return compacted


def case_facts_message(facts: dict[str, Any]) -> str:
    return "CASE FACTS (current, from the onboarding app):\n" + json.dumps(
        facts_for_model(facts), ensure_ascii=False, default=str, separators=(",", ":")
    )


def terms_for_question(facts: dict[str, Any], question: str) -> dict[str, str]:
    """The glossary entries this question is about (a small keyword retrieval step)."""

    text = question.lower()
    words = {word for word in _WORD.findall(text) if len(word) >= 5}
    found: dict[str, str] = {}
    for term, meaning in (facts.get("case_page_terms") or {}).items():
        term_words = set(_WORD.findall(term))
        if term in text or (words & term_words):
            found[term] = meaning
    return found


def _open_section(where: object) -> str:
    return f'Open the "{where}" section to inspect the current case evidence.'


def _offered(blocker: dict[str, Any]) -> list[str]:
    return [
        f'The current case offers "{action.get("label")}".'
        for action in blocker.get("actions_available_to_this_user") or []
    ]


def _correction_line(facts: dict[str, Any], field: str) -> str | None:
    """The "Record correction" line, when the RM is offered it for this field."""

    for row in (facts.get("document_field_review") or {}).get("fields") or []:
        if row.get("field") == field and "Record correction" in (row.get("choices") or []):
            return (
                'Document verification offers "Record correction" to review the extracted '
                "field; this does not decide registry/document precedence."
            )
    return None


def _difference_topic(facts: dict[str, Any], differences: list[Any]) -> tuple[list[str], list[str]]:
    """Per difference: the values, one "why" line (the field's own when there is one), one
    "check" line, one general line, the offered actions, and where to act. Required: the
    values, the "why" and "check" lines, the offered actions and the Record correction line."""

    general_why, _ = ANY_DIFFERENCE[0]
    general_check, not_verification = ANY_DIFFERENCE[1]
    wanted: list[str] = []
    required: list[str] = []
    for blocker, row in differences:
        field = str(row["field"])
        reasons, checks = FIELD_DIFFERENCE.get(field, ((), ()))
        correction = _correction_line(facts, field)
        must = [
            difference_line(row),
            reasons[0] if reasons else general_why,
            checks[0] if checks else general_check,
        ]
        actions = [*_offered(blocker), *([correction] if correction else [])]
        wanted.extend([*must, not_verification, *actions])
        if not correction:
            wanted.append(_open_section(blocker.get("where_on_the_case_page")))
        required.extend([*must, *actions])
    return wanted, required


def _blocker_topic(facts: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Each blocker, what this RM can do about it and where; then what else is needed.
    Required: one line per blocker."""

    wanted: list[str] = []
    required: list[str] = []
    for blocker in facts.get("blockers") or []:
        if blocker.get("plain_explanation"):
            wanted.append(str(blocker["plain_explanation"]))
            required.append(str(blocker["plain_explanation"]))
        wanted.extend(_offered(blocker))
        if blocker.get("why_no_action"):
            wanted.append("No action is currently available to you for this blocker.")
        wanted.append(_open_section(blocker.get("where_on_the_case_page")))
    wanted.extend(_still_needed_lines(facts))  # repeats are dropped in topic_plan
    return wanted, required


def _still_needed_lines(facts: dict[str, Any]) -> list[str]:
    lines = [
        str(blocker["plain_explanation"])
        for blocker in facts.get("blockers") or []
        if blocker.get("plain_explanation")
    ]
    lines.extend(
        f"{need.get('what')} (section: {need.get('where_on_the_case_page')})"
        for need in facts.get("still_needed_before_goldtier") or []
    )
    return lines


def _topic_lines(
    kind: str, differences: list[Any], facts: dict[str, Any]
) -> tuple[str, list[str], list[str]]:
    """(what the question is about, the topic's lines in order, the lines an answer needs)."""

    if kind == DIFFERENCE:
        fields = list(dict.fromkeys(str(row["field"]) for _, row in differences))
        about = " and ".join(f"the {field} difference" for field in fields)
        return about, *_difference_topic(facts, differences)
    if kind in (READINESS, APPROVE):
        first = NOT_READY if kind == READINESS else APPROVAL_NOT_OFFERED
        lines = [first, *_still_needed_lines(facts)]
        about = "whether the case is ready or approved" if kind == READINESS else "approving it"
        return about, lines, lines
    if kind == CONTACT:
        owners = who_resolves_lines(facts)
        return "who to contact", [*owners, NO_CONTACT], owners[:MAX_CONTACT_LINES]
    if kind == BLOCKERS:
        return "what is blocking the case and what to do", *_blocker_topic(facts)
    what, where = READINESS_NEEDS[kind]
    about = "the document review" if kind == DOCUMENT_REVIEW else "ownership evidence"
    explanations = READINESS_EXPLANATIONS[kind]
    required = list(explanations[:1]) if kind == DOCUMENT_REVIEW else []
    return about, [f"{what} (section: {where})", *explanations, _open_section(where)], required


# At most this many "this is for ..." lines are required in an answer about contacts.
MAX_CONTACT_LINES = 3


@dataclass(frozen=True)
class TopicPlan:
    """The question's topic: its allowed lines in order, and those an answer must contain."""

    about: str
    lines: tuple[str, ...]
    required: tuple[str, ...]


# Two question kinds no readiness topic covers (Phase B, D-092 proposed): which registry the
# company details came from and whether it is live, and who the UBOs are. They steer the model
# only (the case-data answer is unchanged) and require no line, so a bare "can't answer" is
# never padded with one (rule 17).
_REGISTRY_WORD = re.compile(r"\b(?:registry|acra)\b")
_REGISTRY_STATUS_WORD = re.compile(r"\b(?:live|mock|sandbox|used|real)\b")
_OWNERS_QUESTION = re.compile(
    r"\b(?:who|which)\b[^?]*\b(?:ubos?|beneficial owners?|shareholders?)\b"
)
# A request to complete the UBO check ("mark the UBO check as complete", "complete the UBO
# check"), not a question about its status ("is the UBO check complete?").
_UBO_COMPLETION_REQUEST = re.compile(
    r"\b(?:mark|set|flag|tick|make|sign off)\b[^?]*\b(?:ubos?|ownership)\b[^?]*"
    r"\b(?:complete|completed|done|finished|closed|passed)\b"
    r"|\b(?:complete|finish|close|sign off)\b\s+(?:the\s+|this\s+)?(?:ubos?|ownership)\b"
)


# Phase B answer quality (D-092 P12 to P14, proposed): company directors, the UEN, the entity
# status and the GoldTier handoff. Like the plans above they steer the model only.
# A question about the company's directors or officers, not the app's Director role (Directors
# approve knowledge and handle enhancement requests).
_COMPANY_DIRECTORS = re.compile(
    r"\bboard of directors\b"
    r"|\b(?:directors?|officers?)\b[^?]{0,60}\b(?:of|appoint\w*|resign\w*|named|listed"
    r"|differ\w*|mismatch\w*|acra|registry|record|document)\b"
    r"|\b(?:appoint\w*|resign\w*|named|listed|acra|registry|record|document|company'?s?)\b"
    r"[^?]{0,60}\b(?:directors?|officers?)\b"
)
# The app's Director role, and staff roles named "officer" (a compliance officer is not one of
# the company's officers).
_DIRECTOR_ROLE = re.compile(
    r"\bdirectors?(?:'s)?\b[^?]{0,40}\b(?:approv\w*|publish\w*|knowledge|enhancement|queue"
    r"|escalat\w*|permission\w*|role|overrid\w*)\b"
    r"|\b(?:ask|tell|contact|escalate to)\s+(?:a\s+|the\s+|my\s+|your\s+)?directors?\b"
    r"|\b(?:compliance|onboarding|relationship|kyc|aml|case|credit|risk|review\w*|security"
    r"|operations|data protection)\s+officers?\b"
)
# A director question about a difference, rather than asking who the directors are.
_DIRECTOR_DIFFERENCE = re.compile(
    r"\bdiffer\w*|\bmismatch\w*|\bconflict\w*|\bnot (?:in|on|listed)\b|\bmissing\b|\bnamed\b"
    r"|\bdocument\b|\breconcil\w*"
)
_UEN_QUESTION = re.compile(r"\buen\b|\bunique entity number\b")
_ENTITY_STATUS_QUESTION = re.compile(r"\bstatus\b[^?]*\blive\b|\blive\b[^?]*\bstatus\b")
_HANDOFF_QUESTION = re.compile(
    r"\b(?:hand(?:ed|s|ing)?[ -]?off|handoff|happens|after)\b[^?]*\bgoldtier\b"
    r"|\bgoldtier\b[^?]*\b(?:hand(?:ed|s|ing)?[ -]?off|handoff|happens)\b"
)


def _company_directors_question(text: str) -> bool:
    return bool(_COMPANY_DIRECTORS.search(text)) and not _DIRECTOR_ROLE.search(text)


def _director_lines(facts: dict[str, Any], text: str) -> tuple[str, list[str]]:
    """Who the directors are: the officer lookup line. A difference: also what the app does not
    compare, the general (conditional) check and reasons, and where to look."""

    officers = officers_line(facts)
    lookup = [
        *officer_record_lines(facts),
        *([officers] if officers else []),
        _open_section("Registry verification"),
    ]
    if not _DIRECTOR_DIFFERENCE.search(text):
        return "who the company's directors are", lookup
    return "a difference in the company's directors", [
        DIRECTORS_NOT_READ,
        *lookup[:-1],
        DIRECTOR_DIFFERENCE_CHECK,
        DIRECTOR_DIFFERENCE_REASONS,
        _open_section("Registry verification"),
        _open_section("Document verification"),
    ]


def _director_question_first(topic: tuple[str, list[Any]] | None, text: str) -> bool:
    """A company-director question goes to the director plan, not to the generic "what is
    blocking" or readiness topics, nor to a difference topic it reached only through words like
    "differ" (a field such as the address, named in the question, keeps its difference topic)."""

    if not _company_directors_question(text):
        return False
    if topic is None or topic[0] in (BLOCKERS, READINESS):
        return True
    if topic[0] == DIFFERENCE:
        return not any(_named(str(row["field"]), text) for _, row in topic[1])
    return False


def _ownership_required(facts: dict[str, Any]) -> bool:
    """The backend readiness check lists missing ownership evidence for this case."""

    needs = facts.get("still_needed_before_goldtier") or []
    return any(need.get("code") == OWNERSHIP for need in needs)


def _source_or_owners_lines(facts: dict[str, Any], question: str) -> tuple[str, list[str]] | None:
    text = question.lower()
    if _UBO_COMPLETION_REQUEST.search(text) and ubo_completion_not_offered(facts):
        # The refusal, then why: no UBO result yet and the ownership item still open.
        ownership_needs = [
            f"{need.get('what')} (section: {need.get('where_on_the_case_page')})"
            for need in facts.get("still_needed_before_goldtier") or []
            if str(need.get("code", "")).startswith("OWNERSHIP")
        ]
        return "a request to mark the UBO check as complete", [
            UBO_COMPLETION_NOT_OFFERED,
            UBO_CHECK_NOT_RUN,
            *ownership_needs,
            _open_section("Ownership & UBO"),
        ]
    if _REGISTRY_WORD.search(text) and _REGISTRY_STATUS_WORD.search(text):
        source = registry_source_line(facts, acra_only=True)
        if source is not None:
            return "which registry the company details came from and whether it is live", [
                source,
                ENTITY_STATUS_LIVE,
                MOCK_NOT_LIVE,
            ]
    if _OWNERS_QUESTION.search(text) and _ownership_required(facts):
        _, lines, _ = _topic_lines(OWNERSHIP, [], facts)
        # The direct answer first; topic_plan keeps it only where it is an allowed line.
        return "who the ultimate beneficial owners are", [UBO_CHECK_NOT_RUN, *lines]
    source = registry_source_line(facts, acra_only=True)
    if _UEN_QUESTION.search(text):
        return "what the UEN is and where the company details came from", [
            UEN_MEANING,
            *([source] if source else []),
            _open_section("Registry verification"),
        ]
    if _ENTITY_STATUS_QUESTION.search(text):
        return "the company's entity status", [ENTITY_STATUS_LIVE, *([source] if source else [])]
    if _HANDOFF_QUESTION.search(text):
        return "what happens when the case is sent to GoldTier", [
            NOT_READY,
            SEND_BEFORE_SUBMISSION,
            SUBMISSION_RESULT_KEPT,
            SENDING_IS_NOT_APPROVAL,
            _open_section("GoldTier Details & Status"),
        ]
    return None


def topic_plan(facts: dict[str, Any], question: str) -> TopicPlan | None:
    """The plan for the question's topic (see briefing.question_topic), or None.

    Only lines already in allowed_guidance are used; which lines are allowed is unchanged.
    """

    topic = question_topic(question, facts)
    allowed = set(allowed_guidance(facts))
    text = question.lower()
    if _director_question_first(topic, text):
        about, wanted = _director_lines(facts, text)
        lines = tuple(line for line in dict.fromkeys(wanted) if line in allowed)
        return TopicPlan(about, lines, ()) if lines else None
    if topic is None:
        extra = _source_or_owners_lines(facts, question)
        if extra is None:
            return None
        about, wanted = extra
        lines = tuple(line for line in dict.fromkeys(wanted) if line in allowed)
        return TopicPlan(about, lines, ()) if lines else None
    about, wanted, required = _topic_lines(*topic, facts)
    lines = tuple(line for line in dict.fromkeys(wanted) if line in allowed)
    if not lines:
        return None
    return TopicPlan(about, lines, tuple(line for line in dict.fromkeys(required) if line in lines))


def topic_message(facts: dict[str, Any], question: str) -> str | None:
    """Steer the model to the topic's allowed lines. None when no topic matches (rule 17 then
    covers questions the case data cannot answer)."""

    plan = topic_plan(facts, question)
    if plan is None:
        return None
    return (
        f"QUESTION TOPIC: {plan.about}. Answer with the allowed lines below, copied exactly, one "
        "per line, in this order. Leave out only a line that does not answer the question.\n"
        + "\n".join(plan.lines)
    )


def trim_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the most recent turns that fit the history budget; shorten very long turns."""

    kept: list[dict[str, str]] = []
    used = 0
    for turn in reversed(history):
        content = turn["content"]
        if len(content) > MAX_HISTORY_TURN_CHARS:
            content = content[:MAX_HISTORY_TURN_CHARS].rsplit(" ", 1)[0] + " …"
        if used + len(content) > MAX_HISTORY_CHARS:
            break
        kept.append({"role": turn["role"], "content": content})
        used += len(content)
    kept.reverse()
    # A conversation sent to the model should start with the user's turn.
    while kept and kept[0]["role"] != "user":
        kept.pop(0)
    return kept


def prefix_messages(facts: dict[str, Any]) -> list[dict[str, str]]:
    """The part of every prompt about this case that does not change between questions."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": case_facts_message(facts)},
    ]


def build_messages(
    facts: dict[str, Any],
    history: list[dict[str, str]],
    question: str,
    *,
    knowledge: str | None = None,
) -> list[dict[str, str]]:
    messages = prefix_messages(facts)
    messages.extend(trim_history(history))
    if knowledge:
        # After the history: it changes with every question, so the cached start stays put.
        messages.append({"role": "system", "content": knowledge})
    topic = topic_message(facts, question)
    if topic:
        messages.append({"role": "system", "content": topic})
    terms = terms_for_question(facts, question)
    if terms:
        messages.append(
            {
                "role": "system",
                "content": "CASE PAGE TERMS (what these labels mean):\n"
                + json.dumps(terms, ensure_ascii=False, separators=(",", ":")),
            }
        )
    messages.append({"role": "user", "content": question})
    return messages


# D-142 R3: the service's fixed wording, trusted by origin where it is defined (a system
# role alone never makes text trusted: privacy_boundary.trusted_text).
_privacy_trusted(SYSTEM_PROMPT)
