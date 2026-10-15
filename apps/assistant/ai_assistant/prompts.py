"""Build the messages sent to the model. The case facts are the only source it may use.

Speed matters on a small local model: every token in the prompt has to be read and every
token in the answer has to be written. So the model gets a short, plain view of the case
(not the full fact sheet), and messages are ordered so the start of the prompt stays the
same between questions. The model server can then reuse its earlier reading of that part
(prompt caching) and only read what is new:

    1. rules            - same for every case and question
    2. case facts       - same for every question about this case, until the case changes
    3. chat history     - grows by one turn per question
    4. page terms       - only the glossary entries this question asks about
    5. the question
"""

import json
import re
from typing import Any

from .context import readable_time as when
from .guardrails import compact_facts
from .instructions import system_prompt

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


def _blocker_for_model(blocker: dict[str, Any]) -> dict[str, Any]:
    view = {
        "title": blocker.get("title"),
        "stage": blocker.get("stage"),
        "explanation": blocker.get("plain_explanation") or blocker.get("app_explanation"),
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
    """A short view of the case facts for the model; nothing new, only less."""

    readiness = facts.get("readiness") or {}
    view = {
        "viewer": facts.get("viewer"),
        "company": facts.get("company"),
        "overall": {
            key: value
            for key, value in (facts.get("overall") or {}).items()
            if key != "current_stage"
        },
        "steps": _steps_for_model(facts.get("steps") or []),
        "blockers": [_blocker_for_model(blocker) for blocker in facts.get("blockers") or []],
        "still_needed_before_goldtier": facts.get("still_needed_before_goldtier"),
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
        "case_page_sections": facts.get("case_page_sections"),
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
    facts: dict[str, Any], history: list[dict[str, str]], question: str
) -> list[dict[str, str]]:
    messages = prefix_messages(facts)
    messages.extend(trim_history(history))
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
