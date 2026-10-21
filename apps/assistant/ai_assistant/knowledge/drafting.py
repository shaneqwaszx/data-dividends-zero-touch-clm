"""Turn an RM's "Solved it" into a draft past resolution for a Director to review.

Only what the RM wrote is used: their note, the questions they asked in the conversation
they marked as having solved it, and the case context (blocker codes, fields, stages). The
assistant's side of that conversation is not copied: the browser sends it, so it is not
proof of what the assistant said, and an approved draft must not carry text the RM could
have made up in the assistant's name. Client details are removed first. The questions the RM
asked after the first become the entry's follow-up questions, so next time the assistant can
answer them up front.

A draft is visible only to the RM's own team (for review and, once approved, for search);
Directors, whom the CLM backend scopes globally, review every team's drafts.
"""

import secrets
from collections.abc import Sequence
from typing import Any

from .models import Entry, EntryKind, EntryStatus, Visibility
from .redaction import Redactor
from .retrieval import case_context

MAX_FOLLOW_UPS = 5
# A draft from someone the CLM backend reports without a team is visible to no team.
NO_TEAM = "NO_TEAM"


def draft_resolution(
    facts: dict[str, Any],
    turns: list[dict[str, str]],
    note: str,
    *,
    author: str,
    team: str | None = None,
    parties: Sequence[tuple[str, str]] = (),
) -> Entry:
    redact = Redactor(facts, parties=parties).redact
    ctx = case_context(facts)
    blockers = facts.get("blockers") or []
    problem = ""
    if blockers:
        first = blockers[0]
        problem = str(
            first.get("plain_explanation") or first.get("app_explanation") or first.get("title")
        )
    questions = [t["content"] for t in turns if t.get("role") == "user" and t.get("content")]

    parts = []
    if problem:
        parts.append(f"Problem: {problem}")
    if questions:
        parts.append(f"The RM asked: {questions[0]}")
    if note.strip():
        parts.append(f"What resolved it (RM's note): {note.strip()}")
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
        visibility=Visibility(teams=(team or NO_TEAM,)),
        follow_ups=tuple(follow_ups[:MAX_FOLLOW_UPS]),
        author=author,
        source_ref="RM feedback",
    )
