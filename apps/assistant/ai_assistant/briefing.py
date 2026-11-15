"""Answers built straight from the case facts, with no AI model.

Used for the opening message (so it is instant and always correct) and as the fallback
when the model is switched off, not installed, or too slow.
"""

import re
from typing import Any

from .guardrails import approval_not_offered, who_resolves_lines
from .guide import (
    APPROVAL_NOT_OFFERED,
    NO_CONTACT,
    OWNERSHIP_REVIEW_ADVISED,
    READINESS_EXPLANATIONS,
    SAME_ISSUE,
    SCREEN_TERMS,
    difference_explanations,
    difference_line,
    sentence_case,
)


def _difference_lines(blocker: dict[str, Any]) -> list[str]:
    lines = []
    for row in blocker.get("differences") or []:
        if row.get("registry_value") or row.get("document_value"):
            lines.append(f"   - {difference_line(row)}")
    return lines


def _blocker_line(blocker: dict[str, Any]) -> str:
    return str(
        blocker.get("plain_explanation") or blocker.get("app_explanation") or blocker.get("title")
    )


def _next_step_lines(blocker: dict[str, Any]) -> list[str]:
    actions = blocker.get("actions_available_to_this_user") or []
    if actions:
        labels = ", ".join(f'"{a["label"]}"' for a in actions if a.get("label"))
        return [f"   You can: {labels}."]
    if blocker.get("why_no_action"):
        who = blocker.get("who_resolves")
        suffix = f" This is for {who}." if who else ""
        return [f"   No action is available to you here: {blocker['why_no_action']}{suffix}"]
    if blocker.get("who_resolves"):
        return [f"   This needs {blocker['who_resolves']}."]
    return []


def _need_lines(needs: list[dict[str, str]]) -> list[str]:
    lines = []
    for need in needs:
        where = need.get("where_on_the_case_page")
        lines.append(f"- {need['what']}" + (f" (section: {where})" if where else ""))
    return lines


def _needs_beyond_blockers(facts: dict[str, Any]) -> list[dict[str, str]]:
    """Readiness items that are not the same issue as an open blocker (told once only)."""

    codes = {str(blocker.get("code")) for blocker in facts["blockers"]}
    same = set(codes)
    for group in SAME_ISSUE:
        if group & codes:
            same |= group
    return [
        need
        for need in facts.get("still_needed_before_goldtier") or []
        if need.get("code") not in same
    ]


def _still_needed_answer(facts: dict[str, Any], explain: str | None = None) -> str:
    """What is left; with ``explain`` (a readiness code), that item's explanation sentences."""

    if facts["overall"]["status"] == "completed":
        return "Nothing. The case completed and there are no open issues."
    lines: list[str] = []
    if facts["blockers"]:
        lines.append("First resolve these:")
        lines.extend(f"- {_blocker_line(b)}" for b in facts["blockers"])
    needs = facts.get("still_needed_before_goldtier") or []
    if needs:
        lines.append("Before the case can go to GoldTier, the app still needs:")
        for need in needs:
            lines.extend(_need_lines([need]))
            if explain and need.get("code") == explain:
                lines.extend(f"   {line}" for line in READINESS_EXPLANATIONS.get(explain, ()))
    if not lines:
        pending = next_pending_step(facts)
        if pending:
            return f"Next step: {pending}. " + progress_line(facts)
        return "The app shows nothing else outstanding right now. " + progress_line(facts)
    return "\n".join(lines)


def progress_line(facts: dict[str, Any]) -> str:
    overall = facts["overall"]
    return (
        f"{overall['steps_done']} of {overall['steps_total']} onboarding steps are done. "
        f"The case is {overall['status']}."
    )


def next_pending_step(facts: dict[str, Any]) -> str | None:
    for step in facts["steps"]:
        if step["status"] not in {"done", "skipped", "nothing to process"}:
            return str(step["step"])
    return None


def ownership_advised(facts: dict[str, Any]) -> bool:
    """D-137: ownership is complete for readiness only because its review is advisory."""

    sections = (facts.get("readiness") or {}).get("sections") or {}
    return sections.get("ownership") == "REVIEW_ADVISED"


def opening_message(facts: dict[str, Any]) -> str:
    company = facts["company"].get("legal_name") or "this company"
    blockers = facts["blockers"]
    problem = facts.get("system_problem")
    lines: list[str] = []
    if blockers:
        count = len(blockers)
        noun = "issue" if count == 1 else "issues"
        lines.append(f"I found {count} {noun} stopping the onboarding of {company}:")
        for number, blocker in enumerate(blockers, start=1):
            where = blocker.get("where_on_the_case_page")
            lines.append(
                f"{number}. {_blocker_line(blocker)}" + (f" (section: {where})" if where else "")
            )
            lines.extend(_difference_lines(blocker))
            lines.extend(_next_step_lines(blocker))
        review = facts.get("document_field_review")
        if review:
            choices = []
            for row in review["fields"]:
                for choice in row["choices"]:
                    if choice not in choices:
                        choices.append(choice)
            fields = ", ".join(sorted({row["field"] for row in review["fields"]}))
            labels = ", ".join(f'"{choice}"' for choice in choices)
            lines.append(
                f"   You can also check what was read from the document ({fields}) under "
                f'"Review extracted document fields": {labels}.'
            )
        later = _needs_beyond_blockers(facts)
        if later:
            lines.append("")
            lines.append("Also still needed before GoldTier submission:")
            lines.extend(_need_lines(later))
        lines.append("")
        lines.append(
            "I can explain any of these in more detail."
            if count + len(later) > 1
            else "I can explain this in more detail."
        )
    elif problem:
        lines.append(f"Onboarding of {company} stopped safely because of a system problem.")
        if problem.get("message"):
            lines.append(f"The app says: {problem['message']}")
    elif facts["overall"]["status"] == "completed":
        lines.append(f"Onboarding of {company} is complete. There are no open issues.")
    else:
        needs = facts.get("still_needed_before_goldtier") or []
        if needs:
            lines.append(f"Onboarding of {company} is waiting for inputs. Still needed:")
            lines.extend(_need_lines(needs))
        else:
            lines.append(f"There are no blockers on {company} right now.")
            pending = next_pending_step(facts)
            if pending:
                lines.append(f"Next step: {pending}.")
    if ownership_advised(facts):
        lines.append(OWNERSHIP_REVIEW_ADVISED)
    lines.append("")
    lines.append(progress_line(facts))
    return "\n".join(lines).strip()


def suggested_questions(facts: dict[str, Any]) -> list[str]:
    questions: list[str] = []
    if facts["blockers"] or facts.get("system_problem"):
        questions.append("Why is this case blocked?")
    for blocker in facts["blockers"]:
        for row in blocker.get("differences") or []:
            questions.append(f"Explain the {row['field']} difference")
    questions.append("What should I do next?")
    questions.append("Where are we now?")
    if facts["company"].get("source", "").startswith("ACRA"):
        questions.append("What did ACRA return?")
    if facts["documents"]:
        questions.append("What was read from the documents?")
    questions.append("Is this case ready for GoldTier?")
    unique: list[str] = []
    for question in questions:
        if question not in unique:
            unique.append(question)
    return unique[:6]


def _company_answer(facts: dict[str, Any]) -> str:
    company = facts["company"]
    lines = [f"From {company['source']}:"]
    for label, key in (
        ("Legal name", "legal_name"),
        ("UEN", "uen"),
        ("Country", "country"),
        ("Company status", "entity_status"),
        ("Registered address", "registered_address"),
    ):
        if company.get(key):
            lines.append(f"- {label}: {company[key]}")
    return "\n".join(lines)


def _documents_answer(facts: dict[str, Any]) -> str:
    if not facts["documents"]:
        return "No documents have been uploaded for this case yet."
    lines = []
    for document in facts["documents"]:
        lines.append(f"{document['name']} ({document['state']}):")
        for field in document["fields"]:
            lines.append(
                f"- {sentence_case(field['field'])}: {field['value_read_from_document']} "
                f"(compared with registry: {field['compared_with_registry']})"
            )
    return "\n".join(lines)


def _readiness_answer(facts: dict[str, Any]) -> str:
    readiness = facts["readiness"]
    if facts["overall"]["status"] == "completed":
        return "Yes. The case completed and there are no open issues."
    if not readiness["blockers"] and not facts["blockers"]:
        return "There are no readiness blockers recorded right now."
    return "Not yet.\n" + _still_needed_answer(facts)


# Other words a question may use for a field (field labels are matched as whole words).
_FIELD_ALIASES = {"registered address": ("address",), "legal name": ("company name",)}


def _named(field: str, text: str) -> bool:
    names = (field.lower(), *_FIELD_ALIASES.get(field, ()))
    return any(re.search(rf"\b{re.escape(name)}\b", text) for name in names)


DIFFERENCE = "difference"
DOCUMENT_REVIEW = "DOCUMENT_REVIEW_INCOMPLETE"
OWNERSHIP = "OWNERSHIP_REQUIRED"
APPROVE = "approve"
CONTACT = "contact"
READINESS = "readiness"
BLOCKERS = "blockers"
_BLOCKERS_QUESTION = re.compile(r"\bwhy\b|\bblock|\bstuck\b|\bnext\b|\bshould i\b|\bfix\b")
_APPROVE_QUESTION = re.compile(r"\bapprov(?:e|ing)\b")
_CONTACT_QUESTION = re.compile(
    r"\bwho (?:should|do|can|to|will|handles|resolves)\b|\bcontact\b|\bcall\b|\bescalat"
    r"|\b(?:speak|talk) to\b"
)
_READINESS_QUESTION = re.compile(r"\bapproved\b|\bready\b|\bsubmit\b")
Difference = tuple[dict[str, Any], dict[str, Any]]  # (blocker, difference row)


def _asked_differences(text: str, facts: dict[str, Any]) -> list[Difference]:
    """The differences a question is about: the fields it names, or every one when it asks to
    explain or mentions a difference. Empty when the case has none or the question is not
    about them."""

    rows = [
        (blocker, row)
        for blocker in facts["blockers"]
        for row in blocker.get("differences") or []
        if row.get("registry_value") or row.get("document_value")
    ]
    named = [(blocker, row) for blocker, row in rows if _named(str(row["field"]), text)]
    asks = any(word in text for word in ("explain", "differen", "mismatch"))
    return named or (rows if asks else [])


def question_topic(question: str, facts: dict[str, Any]) -> tuple[str, list[Difference]] | None:
    """What the question is about, for the case-data answer and to steer the model:
    (DIFFERENCE, the differences asked about), or (kind, []) for APPROVE, CONTACT,
    DOCUMENT_REVIEW, OWNERSHIP, READINESS and BLOCKERS (why blocked, what next); None when no
    topic matches.
    """

    text = question.lower()
    if _APPROVE_QUESTION.search(text):
        return APPROVE, []
    if _CONTACT_QUESTION.search(text):
        return CONTACT, []
    if "document review" in text:
        return DOCUMENT_REVIEW, []
    if "ownership" in text and any(word in text for word in ("evidence", "need")):
        return OWNERSHIP, []
    differences = _asked_differences(text, facts)
    if differences:
        return DIFFERENCE, differences
    if _READINESS_QUESTION.search(text):
        return READINESS, []
    if facts["blockers"] and _BLOCKERS_QUESTION.search(text):
        return BLOCKERS, []
    return None


def _topic_answer(kind: str, differences: list[Difference], facts: dict[str, Any]) -> str:
    if kind == DIFFERENCE:
        return _difference_answer(differences)
    if kind == READINESS:
        return _readiness_answer(facts)
    if kind == BLOCKERS:
        return opening_message(facts)
    if kind == CONTACT:
        return "\n".join(who_resolves_lines(facts) or [NO_CONTACT])
    if kind == APPROVE:
        rest = _still_needed_answer(facts)
        return f"{APPROVAL_NOT_OFFERED}\n{rest}" if approval_not_offered(facts) else rest
    return _still_needed_answer(facts, explain=kind)


def _difference_answer(differences: list[Difference]) -> str:
    """Explain the asked-about document/ACRA differences on this case.

    Shows both values, the reviewed explanation sentences, the choices this RM is offered and
    where on the page. It never says which value is right.
    """

    lines: list[str] = []
    for blocker, row in differences:
        field = str(row["field"])
        where = blocker.get("where_on_the_case_page")
        if lines:
            lines.append("")
        lines.append(
            f"The {field} on the document is different from ACRA"
            + (f" (section: {where}):" if where else ":")
        )
        lines.extend(_difference_lines({"differences": [row]}))
        reasons, checks = difference_explanations(field)
        lines.append("Why it can differ:")
        lines.extend(f"- {line}" for line in reasons)
        lines.append("What to check:")
        lines.extend(f"- {line}" for line in checks)
        lines.extend(line.strip() for line in _next_step_lines(blocker))
    return "\n".join(lines)


def _terms_answer(text: str) -> str | None:
    """Explain case page labels the question mentions, e.g. "canonical"."""

    found = [term for term in SCREEN_TERMS if term in text]
    if not found:
        return None
    # "record correction" also contains no other term; avoid repeating overlapping words.
    found = [t for t in found if not any(t != o and t in o for o in found)]
    lines = [f"- {sentence_case(term)}: {SCREEN_TERMS[term]}." for term in found]
    return "On the case page:\n" + "\n".join(lines)


def fallback_answer(question: str, facts: dict[str, Any]) -> str:
    """Answer from the facts by topic. Clearly limited, never invented."""

    text = question.lower()
    terms = _terms_answer(text)
    if terms is not None:
        return terms
    if any(
        phrase in text
        for phrase in (
            "need to do",
            "have to do",
            "still need",
            "what more",
            "submission",
            "submit",
            "what's left",
            "whats left",
            "outstanding",
        )
    ):
        answer = _still_needed_answer(facts)
    elif (topic := question_topic(question, facts)) is not None:
        answer = _topic_answer(*topic, facts)
    elif any(
        word in text
        for word in ("why", "block", "stuck", "differen", "mismatch", "next", "should i", "fix")
    ):
        answer = opening_message(facts)
    elif any(word in text for word in ("acra", "registry", "address", "uen", "registered")):
        answer = _company_answer(facts)
    elif "document" in text or "extract" in text:
        answer = _documents_answer(facts)
    elif "ready" in text or "goldtier" in text:
        answer = _readiness_answer(facts)
    elif any(word in text for word in ("where", "status", "progress", "stage")):
        answer = progress_line(facts)
        pending = next_pending_step(facts)
        if pending:
            answer += f" The next step is {pending}."
    else:
        answer = opening_message(facts)
    return answer
