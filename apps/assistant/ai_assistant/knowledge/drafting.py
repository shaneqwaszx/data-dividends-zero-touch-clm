"""A Director's fix for an enhancement request (an RM's "Not helpful" with a note), written as
a past resolution linked to the request (D-080, proposed).

The Director writes the title, body and any follow-up questions; the request supplies the
case context (blocker codes, fields, stages) and the team. The Director's text is redacted
(``redact``: the request's own case values and parties, then the UEN, NRIC/FIN, postal, unit,
email and phone patterns) before it is stored: past resolutions are shared across clients.
The RM's note was already redacted when the request was stored. Nothing from the
conversation is used.

A resolution is visible only to the team the request came from (for review and, once
approved, for search); Directors, whom the CLM backend scopes globally, review every team's
drafts.
"""

import secrets
from collections.abc import Callable, Sequence
from typing import Any

from .models import Entry, EntryKind, EntryStatus, Visibility

MAX_FOLLOW_UPS = 5
# A resolution from a request with no team is visible to no team.
NO_TEAM = "NO_TEAM"


def resolution_from_request(
    request: dict[str, Any],
    *,
    author: str,
    title: str,
    body: str,
    redact: Callable[[str], str],
    follow_ups: Sequence[str] = (),
) -> Entry:
    cleaned: list[str] = []
    for question in follow_ups:
        text = redact(" ".join(question.split()))
        if text and text not in cleaned:
            cleaned.append(text)
    return Entry(
        entry_id=f"resolution.{secrets.token_hex(6)}",
        kind=EntryKind.RESOLUTION,
        status=EntryStatus.PENDING_REVIEW,
        title=redact(" ".join(title.split())),
        body=redact(body.strip()),
        blocker_codes=tuple(request.get("blocker_codes") or ()),
        fields=tuple(request.get("fields") or ()),
        stages=tuple(request.get("stages") or ()),
        visibility=Visibility(teams=(request.get("team") or NO_TEAM,)),
        follow_ups=tuple(cleaned[:MAX_FOLLOW_UPS]),
        author=author,
        source_ref=f"Enhancement request {request['id']}",
    )
