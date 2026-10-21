"""Turn an enhancement request (an RM's "Not helpful" with a note) into a draft past
resolution, written by the reviewer who drafts it and reviewed by a different one.

Only the request is used: the RM's note, redacted of client details when it was stored, and
its case context (blocker codes, fields, stages). The note passes the pattern redaction again
(UEN, NRIC/FIN, postal and unit numbers, emails, phone numbers); the case values it was first
redacted against are not kept with the request. Nothing from the conversation is copied: the
assistant's side of it would not be proof of what the assistant said.

A draft is visible only to the team the request came from (for review and, once approved,
for search); Directors, whom the CLM backend scopes globally, review every team's drafts.
"""

import secrets
from typing import Any

from .models import Entry, EntryKind, EntryStatus, Visibility
from .redaction import Redactor

# A draft from a request with no team is visible to no team.
NO_TEAM = "NO_TEAM"


def draft_from_request(request: dict[str, Any], *, author: str) -> Entry:
    redact = Redactor({}).redact
    codes = tuple(request.get("blocker_codes") or ())
    note = redact(" ".join(str(request.get("note") or "").split()))
    body = f"What was missing (RM's note): {note}" if note else "No details were given."
    return Entry(
        entry_id=f"resolution.{secrets.token_hex(6)}",
        kind=EntryKind.RESOLUTION,
        status=EntryStatus.PENDING_REVIEW,
        title=f"Draft: {codes[0] if codes else 'enhancement request'}",
        body=body,
        blocker_codes=codes,
        fields=tuple(request.get("fields") or ()),
        stages=tuple(request.get("stages") or ()),
        visibility=Visibility(teams=(request.get("team") or NO_TEAM,)),
        author=author,
        source_ref=f"Enhancement request {request['id']}",
    )
