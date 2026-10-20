"""Turn an RM's "Solved it" into a draft past resolution for a Director to review.

Only what the RM chose to send is used: their note, the conversation they marked as having
solved it, and the case context (blocker codes, fields, stages). Client details are removed
first. The questions the RM asked after the first become the entry's follow-up questions, so
next time the assistant can answer them up front.
"""

import re
import secrets
from typing import Any

from .models import Entry, EntryKind, EntryStatus
from .redaction import Redactor
from .retrieval import case_context

MAX_FOLLOW_UPS = 5
_TAGS = re.compile(r"\s*\[(?:G|P)\d+\]")


def _first_sentences(text: str, count: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return " ".join(sentences[:count])


def draft_resolution(
    facts: dict[str, Any],
    turns: list[dict[str, str]],
    note: str,
    *,
    author: str,
) -> Entry:
    redact = Redactor(facts).redact
    ctx = case_context(facts)
    blockers = facts.get("blockers") or []
    problem = ""
    if blockers:
        first = blockers[0]
        problem = str(
            first.get("plain_explanation") or first.get("app_explanation") or first.get("title")
        )
    questions = [t["content"] for t in turns if t.get("role") == "user" and t.get("content")]
    answers = [t["content"] for t in turns if t.get("role") == "assistant" and t.get("content")]
    last_answer = _TAGS.sub("", answers[-1]) if answers else ""

    parts = []
    if problem:
        parts.append(f"Problem: {problem}")
    if questions:
        parts.append(f"The RM asked: {questions[0]}")
    if note.strip():
        parts.append(f"What resolved it (RM's note): {note.strip()}")
    if last_answer:
        parts.append(f"Guidance the assistant gave: {_first_sentences(last_answer, 4)}")
    body = redact("\n".join(parts)) or "No details were given."

    title_source = (blockers[0].get("title") if blockers else None) or "Resolved case"
    follow_ups: list[str] = []
    for question in questions[1:]:
        cleaned = redact(" ".join(question.split()))
        if cleaned and cleaned not in follow_ups:
            follow_ups.append(cleaned)
    return Entry(
        entry_id=f"resolution.{secrets.token_hex(6)}",
        kind=EntryKind.RESOLUTION,
        status=EntryStatus.PENDING_REVIEW,
        title=redact(f"Draft: {title_source}"),
        body=body,
        blocker_codes=ctx.blocker_codes,
        fields=ctx.fields,
        stages=ctx.stages,
        follow_ups=tuple(follow_ups[:MAX_FOLLOW_UPS]),
        author=author,
        source_ref="RM feedback",
    )
