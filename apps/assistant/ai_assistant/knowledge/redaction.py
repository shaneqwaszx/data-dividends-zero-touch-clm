"""Remove client details before anything from a case becomes a reusable entry.

Past resolutions are shared across clients, so a draft must not carry who the client is.
Two passes:

1. Exact values known from the case: the company's legal name, UEN and addresses (from ACRA
   and from documents), the signed-in user's name, and the parties the CLM case summary
   lists, found by shape (see ``case_parties``): objects with a ``party_type`` (ownership
   parties), entries of person lists such as ``officers`` and ``shareholders`` (the CLM's
   registry officers carry no ``party_type``), and person-name fields. Natural persons
   become [PERSON], other entities [COMPANY], their identifiers [ID]. A known value matches
   regardless of letter case and of how much whitespace separates its words.
2. Patterns for what the case data may not list: Singapore UEN and NRIC/FIN formats,
   postal codes, unit numbers, email addresses and phone numbers.

Names that appear nowhere in the case data (for example a person the RM mentions from
memory), or are spelled differently, are not recognised. The Director still checks every
draft before approving it; this is a first pass, not a guarantee.
"""

import re
from collections.abc import Sequence
from typing import Any

PLACEHOLDERS = (
    "[COMPANY]",
    "[UEN]",
    "[ADDRESS]",
    "[PERSON]",
    "[ID]",
    "[EMAIL]",
    "[PHONE]",
    "[POSTAL]",
    "[UNIT]",
    "[DOCUMENT]",
)

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    (re.compile(r"(?<!\w)(?:\+65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\w)"), "[PHONE]"),
    # NRIC/FIN: S/T/F/G/M + 7 digits + letter.
    (re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE), "[ID]"),
    # UEN: 8-9 digits + letter (businesses, local companies), or T/S/R + 2 digits + 2 letters
    # + 4 digits + letter (other entities).
    (re.compile(r"\b\d{8,9}[A-Z]\b", re.IGNORECASE), "[UEN]"),
    (re.compile(r"\b[TSR]\d{2}[A-Z]{2}\d{4}[A-Z]\b", re.IGNORECASE), "[UEN]"),
    (re.compile(r"#\d{1,3}-\d{1,5}"), "[UNIT]"),
    (re.compile(r"(?<!\d)\d{6}(?!\d)"), "[POSTAL]"),
)


_NAME_KEYS = ("name", "display_name", "legal_name", "full_name")
_ID_KEYS = (
    "party_id",
    "officer_id",
    "registration_identifier",
    "registration_number",
    "id_number",
)
_PERSON_TYPES = frozenset({"NATURAL_PERSON", "INDIVIDUAL", "PERSON"})
# Lists whose entries are people unless their own party_type says otherwise. Registry
# officers (CLM ``BrowserRegistryOfficer``: officer_id, name, role) have no party_type.
_PERSON_LISTS = frozenset(
    {
        "officers",
        "shareholders",
        "directors",
        "partners",
        "members",
        "owners",
        "beneficial_owners",
        "persons",
        "people",
        "signatories",
        "authorised_representatives",
        "authorized_representatives",
    }
)
# Fields that name a person wherever they appear.
_PERSON_NAME_KEYS = ("person_name", "officer_name", "holder_name", "individual_name", "owner_name")
_MAX_PARTY_DEPTH = 12


def case_parties(summary: Any) -> list[tuple[str, str]]:
    """(value, placeholder) for every party named in the CLM case summary.

    Found by shape, not by a fixed path: an object with a ``party_type`` (registry ownership
    parties, ownership-analysis parties), an entry of a person list such as ``officers`` or
    ``shareholders``, and any person-name field. A natural person's name becomes [PERSON],
    another entity's name [COMPANY], and identifiers [ID].
    """

    found: list[tuple[str, str]] = []

    def collect(item: dict[str, Any], placeholder: str) -> None:
        for key in _NAME_KEYS:
            if isinstance(item.get(key), str):
                found.append((item[key], placeholder))
        for key in _ID_KEYS:
            if isinstance(item.get(key), str):
                found.append((item[key], "[ID]"))

    def placeholder_for(item: dict[str, Any], default: str) -> str:
        party_type = item.get("party_type")
        if not isinstance(party_type, str):
            return default
        return "[PERSON]" if party_type.upper() in _PERSON_TYPES else "[COMPANY]"

    def walk(value: Any, depth: int) -> None:
        if depth > _MAX_PARTY_DEPTH:
            return
        if isinstance(value, dict):
            if isinstance(value.get("party_type"), str):
                collect(value, placeholder_for(value, "[COMPANY]"))
            for key in _PERSON_NAME_KEYS:
                if isinstance(value.get(key), str):
                    found.append((value[key], "[PERSON]"))
            for key, item in value.items():
                if str(key).lower() in _PERSON_LISTS and isinstance(item, list):
                    for person in item:
                        if isinstance(person, dict):
                            collect(person, placeholder_for(person, "[PERSON]"))
                walk(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                walk(item, depth + 1)

    walk(summary, 0)
    return found


def _known_values(
    facts: dict[str, Any], parties: Sequence[tuple[str, str]] = ()
) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []

    def add(value: Any, placeholder: str) -> None:
        text = " ".join(str(value or "").split())
        if len(text) >= 3:
            values.append((text, placeholder))

    company = facts.get("company") or {}
    add(company.get("legal_name"), "[COMPANY]")
    add(company.get("uen"), "[UEN]")
    add(company.get("registered_address"), "[ADDRESS]")
    viewer = facts.get("viewer") or {}
    add(viewer.get("name"), "[PERSON]")
    for blocker in facts.get("blockers") or []:
        for row in blocker.get("differences") or []:
            placeholder = "[ADDRESS]" if "address" in str(row.get("field")) else "[COMPANY]"
            if row.get("field") == "UEN":
                placeholder = "[UEN]"
            add(row.get("registry_value"), placeholder)
            add(row.get("document_value"), placeholder)
    for document in facts.get("documents") or []:
        add(document.get("name"), "[DOCUMENT]")
        for field in document.get("fields") or []:
            label = str(field.get("field") or "")
            if label in {"registered address"}:
                add(field.get("value_read_from_document"), "[ADDRESS]")
            elif label in {"legal name"}:
                add(field.get("value_read_from_document"), "[COMPANY]")
            elif label == "UEN":
                add(field.get("value_read_from_document"), "[UEN]")
    for item in facts.get("discrepancies") or []:
        for value in item.get("values") or []:
            placeholder = "[ADDRESS]" if "address" in str(item.get("field")) else "[COMPANY]"
            add(value.get("value"), placeholder)
    # Parties last: a value the case facts already name keeps its more specific placeholder.
    known = {text.lower() for text, _ in values}
    for value, placeholder in parties:
        if " ".join(str(value).split()).lower() not in known:
            add(value, placeholder)
    # Longest first, so a full address is replaced before a part of it.
    return sorted(values, key=lambda pair: -len(pair[0]))


def _flexible(value: str) -> re.Pattern[str]:
    """``value`` with any amount of whitespace between its words, in any letter case."""

    return re.compile(r"\s+".join(re.escape(word) for word in value.split()), re.IGNORECASE)


class Redactor:
    def __init__(self, facts: dict[str, Any], *, parties: Sequence[tuple[str, str]] = ()) -> None:
        self._known = [
            (_flexible(value), placeholder) for value, placeholder in _known_values(facts, parties)
        ]

    def redact(self, text: str) -> str:
        out = text
        for pattern, placeholder in self._known:
            out = pattern.sub(placeholder, out)
        for pattern, placeholder in _PATTERNS:
            out = pattern.sub(placeholder, out)
        return out
