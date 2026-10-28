"""The approved synthetic boundary for the D-094 local test mode (remote_test.py).

A question goes to the remote model only when everything it would send is inside the
boundary. The backend's own answer about the case is the evidence (read server-side with the
RM's session); nothing the browser says about the case is trusted. Any doubt fails closed:
the RM gets the deterministic case-data answer and nothing is sent.

    case        the company is the fictional GARDEN BUSINESS (UEN 11111999A) and its registry
                details came from ACRA in MOCK mode
    documents   the document list was read, and every document on the case, and every
                document the case summary names, has an approved synthetic fixture file name
    values      every company, document, discrepancy, review, GoldTier and viewer value is one
                the approved synthetic fixtures produce (times and ids aside)
    knowledge   every knowledge entry used is repository guidance or the synthetic seed,
                unchanged (id and content hash)
    text        every message holds only printable ASCII, line breaks, tabs and a few named
                typographic marks, and every word of it is in the approved vocabulary. The
                question and user history are taken as written (nothing left out, no free
                numbers, at most three number groups across the user turns, never two side by
                side) and may use only words the synthetic questions, guidance, seed,
                instructions, fixture values and the app's own screen terms use. Assistant
                history may also use the synthetic prompts' wording (no run of more than three
                number groups); the service's own system messages (times and ids left out)
                also the application's alphabetic code strings.

The text check guards against accidental entry of client details, not deliberate encoding: it
cannot recognise a real name made of ordinary English words, numbers spelled out as words or
written as punctuation, or a hand-built history; and its number cap applies per request. The
owner must still not type real customer details.

The boundary file (``synthetic_boundary.json``) is generated from the repository's synthetic
fixtures by ``scripts/build_synthetic_boundary.py`` and reviewed like code; a test checks
that it is current.
"""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .clm_client import CaseSnapshot
from .knowledge.models import Entry

BOUNDARY_FILE = Path(__file__).with_name("synthetic_boundary.json")
SCHEMA = "clm-assistant-synthetic-boundary/1"

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_ISO = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
)
# context.readable_time: "12 Oct 2026, 18:08 UTC".
_READABLE = re.compile(
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}"
    r"(?:, \d{2}:\d{2}(?: UTC)?)?"
)
# Full timestamps only (a time of day is required), as the service's own case-data answers
# write them; a bare date such as a birth date is never left out of what a person sent.
_TIMESTAMP = re.compile(
    r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}, \d{2}:\d{2}(?: UTC)?"
    r"|\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?"
)
_TOKEN = re.compile(r"[a-z0-9]+")
# In the service's own system messages, short counts (steps done, lines, percentages) are not
# identifying on their own. Nothing a person wrote gets this allowance.
_MAX_FREE_DIGITS = 2
# The user's turns in one request (the question and the user history) may hold at most this
# many number groups between them, never two side by side (an identifier split into pieces
# needs more), and each must be a number the synthetic sources use.
_MAX_NUMBER_GROUPS = 3
# Assistant history (which the browser sends) may not hold longer runs of number groups side
# by side; a real answer's address has at most three ("#01-01, 018919").
_MAX_ASSISTANT_NUMBER_RUN = 3
# The only characters any message may contain: printable ASCII, line breaks and tabs, and this
# short list of typographic punctuation. Everything else (other scripts, full-width forms,
# symbols, emoji, invisible tag or format characters, private-use characters) is refused,
# because the word check could not see it.
_TYPOGRAPHIC = frozenset("‘’“”–—…·•")


def normalize(text: str) -> str:
    """Times and ids left out, spacing folded: what a value is compared as."""

    for pattern in (_UUID, _ISO, _READABLE):
        text = pattern.sub("<t>", text)
    return " ".join(text.split())


def tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(normalize(text).replace("<t>", " ").lower()))


def _unchecked_characters(text: str) -> bool:
    """Any character the word check cannot see: only printable ASCII, line breaks, tabs and
    ``_TYPOGRAPHIC`` are allowed."""

    return any(
        not (" " <= char <= "~" or char in "\n\r\t" or char in _TYPOGRAPHIC) for char in text
    )


def _longest_number_run(words: list[str]) -> int:
    longest = run = 0
    for word in words:
        run = run + 1 if any(char.isdigit() for char in word) else 0
        longest = max(longest, run)
    return longest


def check_messages(messages: list[dict[str, str]]) -> str | None:
    """The text part of the boundary, for every message that would be sent. Also run by the
    remote model itself before any call (remote_test.py), whoever the caller is.

    Every message: only printable ASCII, line breaks, tabs and a few typographic marks.
    System messages are the service's own (rules, case facts, knowledge): times and ids are
    left out and short counts allowed; words from all the approved vocabularies. What a
    person wrote, or the browser sent as history, is taken as written, with no free numbers:
    user turns use the conversation vocabulary only, hold at most ``_MAX_NUMBER_GROUPS``
    number groups between them and never two side by side; assistant turns may also use the
    synthetic prompts' wording (not the application's code strings), keep the service's own
    full timestamps out of the check, and hold no run longer than
    ``_MAX_ASSISTANT_NUMBER_RUN``."""

    try:
        approved = boundary()
    except (OSError, ValueError, KeyError, TypeError):
        return "SYNTHETIC_BOUNDARY_UNAVAILABLE"
    user_numbers = 0
    for message in messages:
        role = message.get("role")
        content = message.get("content") or ""
        if _unchecked_characters(content):
            return "SYNTHETIC_TEXT_NOT_APPROVED"
        if role == "system":
            for token in tokens(content):
                if token in approved.system:
                    continue
                if token.isdigit() and len(token) <= _MAX_FREE_DIGITS:
                    continue
                return "SYNTHETIC_TEXT_NOT_APPROVED"
            continue
        if role == "assistant":
            # An earlier case-data answer may hold the service's own timestamps.
            content = _TIMESTAMP.sub(" ", content)
        words = _TOKEN.findall(content.lower())
        if role == "assistant":
            if any(word not in approved.assistant for word in words):
                return "SYNTHETIC_TEXT_NOT_APPROVED"
            if _longest_number_run(words) > _MAX_ASSISTANT_NUMBER_RUN:
                return "SYNTHETIC_TEXT_NOT_APPROVED"
            continue
        if any(word not in approved.conversation for word in words):
            return "SYNTHETIC_TEXT_NOT_APPROVED"
        user_numbers += sum(1 for word in words if any(char.isdigit() for char in word))
        if user_numbers > _MAX_NUMBER_GROUPS or _longest_number_run(words) > 1:
            return "SYNTHETIC_TEXT_NOT_APPROVED"
    return None


@dataclass(frozen=True)
class Boundary:
    uen: str
    legal_name: str
    source_system: str
    environments: frozenset[str]
    documents: frozenset[str]
    viewers: frozenset[str]
    values: frozenset[str]
    knowledge: frozenset[tuple[str, str]]
    # Words a question may use; assistant history may also use the synthetic prompts'
    # wording; system messages also the application's own code strings.
    conversation: frozenset[str]
    assistant: frozenset[str]
    system: frozenset[str]


@lru_cache(maxsize=1)
def boundary(path: Path = BOUNDARY_FILE) -> Boundary:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError("unknown synthetic boundary schema")
    company = data["company"]
    conversation = set(data["conversation_vocabulary"])
    prompt = set(data["prompt_vocabulary"])
    return Boundary(
        uen=company["uen"],
        legal_name=company["legal_name"],
        source_system=company["source_system"],
        environments=frozenset(company["environments"]),
        documents=frozenset(data["documents"]),
        viewers=frozenset(data["viewers"]),
        values=frozenset(data["values"]),
        knowledge=frozenset((item["entry_id"], item["content_hash"]) for item in data["knowledge"]),
        conversation=frozenset(conversation),
        assistant=frozenset(conversation | prompt),
        system=frozenset(conversation | prompt | set(data["code_vocabulary"])),
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def data_values(facts: dict[str, Any]) -> list[str]:
    """The case facts that can carry client data (not system wording), as text. The viewer's
    name is checked on its own (``Boundary.viewers``)."""

    found: list[Any] = []
    company = _dict(facts.get("company"))
    found += [
        company.get(key)
        for key in (
            "legal_name",
            "uen",
            "country",
            "entity_status",
            "registration_date",
            "registered_address",
            "source",
        )
    ]
    for document in _list(facts.get("documents")):
        found.append(_dict(document).get("name"))
        found += [
            _dict(field).get("value_read_from_document")
            for field in _list(_dict(document).get("fields"))
        ]
    for item in _list(facts.get("discrepancies")):
        data = _dict(item)
        found.append(data.get("decided_value"))
        # Not "from": it is a document's display name (every document on the case must have
        # an approved name, checked in ``check``) or a backend source label such as
        # "ACRA MOCK" or ONBOARDING_REQUEST; its words are checked in the system messages.
        found += [_dict(observed).get("value") for observed in _list(data.get("values"))]
    for blocker in _list(facts.get("blockers")):
        for difference in _list(_dict(blocker).get("differences")):
            found += [
                _dict(difference).get("registry_value"),
                _dict(difference).get("document_value"),
            ]
    for field in _list(_dict(facts.get("document_field_review")).get("fields")):
        data = _dict(field)
        found += [data.get("document"), data.get("document_value"), data.get("acra_value")]
    found.append(_dict(facts.get("goldtier")).get("goldtier_id"))
    return [normalize(str(value)) for value in found if value not in (None, "")]


def approved_entry(entry: Entry) -> bool:
    return (entry.entry_id, entry.content_hash()) in boundary().knowledge


def check(
    snapshot: CaseSnapshot,
    facts: dict[str, Any],
    messages: list[dict[str, str]],
    entries: Iterable[Entry],
) -> str | None:
    """None when the question may go to the remote model; otherwise a closed reason."""

    try:
        approved = boundary()
    except (OSError, ValueError, KeyError, TypeError):
        return "SYNTHETIC_BOUNDARY_UNAVAILABLE"
    case = _dict(snapshot.summary.get("case"))
    entity = _dict(case.get("entity"))
    source = _dict(entity.get("source"))
    requested = case.get("requested_uen")
    if (
        str(entity.get("registration_number") or "") != approved.uen
        or str(entity.get("legal_name") or "") != approved.legal_name
        or (requested is not None and str(requested) != approved.uen)
        or source.get("source_system") != approved.source_system
        or source.get("environment") not in approved.environments
    ):
        return "SYNTHETIC_CASE_NOT_APPROVED"
    # Without the document list nothing proves the case's documents are the fixture files
    # (the case summary can still name them, for example in its timeline).
    if not snapshot.documents_loaded:
        return "SYNTHETIC_DOCUMENTS_UNAVAILABLE"
    if any(
        str(_dict(document).get("display_name") or "") not in approved.documents
        for document in snapshot.documents
    ):
        return "SYNTHETIC_DOCUMENT_NOT_APPROVED"
    # Document names the case summary itself carries (reconciliation observations).
    if any(
        _dict(observation).get("document_display_name") not in (None, "")
        and str(_dict(observation).get("document_display_name")) not in approved.documents
        for item in _list(_dict(snapshot.summary.get("reconciliation")).get("discrepancies"))
        for observation in _list(_dict(item).get("observations"))
    ):
        return "SYNTHETIC_DOCUMENT_NOT_APPROVED"
    if str(_dict(facts.get("viewer")).get("name") or "") not in approved.viewers:
        return "SYNTHETIC_VIEWER_NOT_APPROVED"
    if any(value not in approved.values for value in data_values(facts)):
        return "SYNTHETIC_VALUE_NOT_APPROVED"
    if any(not approved_entry(entry) for entry in entries):
        return "SYNTHETIC_KNOWLEDGE_NOT_APPROVED"
    return check_messages(messages)
