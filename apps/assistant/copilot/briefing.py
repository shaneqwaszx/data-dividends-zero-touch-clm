"""Answers built straight from the case facts, with no AI model.

Used for the opening message (so it is instant and always correct) and as the fallback
when the model is switched off, not installed, or too slow.
"""

from typing import Any

from .guide import SCREEN_TERMS, sentence_case


def _difference_lines(blocker: dict[str, Any]) -> list[str]:
    lines = []
    for row in blocker.get("differences") or []:
        registry = row.get("registry_value")
        document = row.get("document_value")
        if registry or document:
            lines.append(
                f'   - {sentence_case(row["field"])}: ACRA says "{registry}", '
                f'the document says "{document}".'
            )
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


def _still_needed_answer(facts: dict[str, Any]) -> str:
    if facts["overall"]["status"] == "completed":
        return "Nothing. The case completed and there are no open issues."
    lines: list[str] = []
    if facts["blockers"]:
        lines.append("First resolve these:")
        lines.extend(f"- {_blocker_line(b)}" for b in facts["blockers"])
    needs = facts.get("still_needed_before_goldtier") or []
    if needs:
        lines.append("Before the case can go to GoldTier, the app still needs:")
        lines.extend(_need_lines(needs))
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
            lines.append(f"{number}. {_blocker_line(blocker)}")
            lines.extend(_difference_lines(blocker))
            lines.extend(_next_step_lines(blocker))
        lines.append("")
        lines.append(
            "I can explain any of these in more detail."
            if count > 1
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
