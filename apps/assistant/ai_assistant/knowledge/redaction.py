"""Remove client details before anything from a case becomes a reusable entry.

Past resolutions are shared across clients, so a draft must not carry who the client is.
Two passes:

1. Exact values known from the case: the company's legal name, UEN and addresses (from ACRA
   and from documents), names of people on the case, and the signed-in user's name.
2. Patterns for what the case data may not list: Singapore UEN and NRIC/FIN formats,
   postal codes, unit numbers, email addresses and phone numbers.

The Director still checks every draft before approving it; this is a first pass, not a
guarantee.
"""

import re
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


def _known_values(facts: dict[str, Any]) -> list[tuple[str, str]]:
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
    # Longest first, so a full address is replaced before a part of it.
    return sorted(values, key=lambda pair: -len(pair[0]))


class Redactor:
    def __init__(self, facts: dict[str, Any]) -> None:
        self._known = _known_values(facts)

    def redact(self, text: str) -> str:
        out = text
        for value, placeholder in self._known:
            out = re.sub(re.escape(value), placeholder, out, flags=re.IGNORECASE)
        for pattern, placeholder in _PATTERNS:
            out = pattern.sub(placeholder, out)
        return out
