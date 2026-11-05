"""Deterministic labelled-value lookup for workflow field suggestions (D-121).

Text passed here is transient: only a matched value is ever kept, and only as an
unconfirmed suggestion for a person to check.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

_DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y")
_MAX_VALUE_LENGTH = 512
_PLAIN_NUMBER = re.compile(r"^-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$")
# 1.000 is one in some documents and a thousand in others, so a person decides.
_AMBIGUOUS_NUMBER = re.compile(r"^-?\d{1,3}\.\d{3}$")


@dataclass(frozen=True)
class LabelledValue:
    value: str = ""
    page_number: int = 1


def _value_after_label(line: str, wanted: str) -> str | None:
    """Read one line in linear time, as document text can be long and hostile."""

    text = line.strip(" \t")
    if text[: len(wanted)].casefold() != wanted:
        return None
    rest = text[len(wanted) :].lstrip(" \t")
    return rest[1:].strip(" \t") if rest[:1] in {":", "-"} else None


def find_labelled_value(pages: Sequence[str], label: str) -> LabelledValue | None:
    """Return the one value on a ``label: value`` line; none or conflicting gives None."""

    wanted = label.strip().casefold()
    found: dict[str, int] = {}
    for page_number, text in enumerate(pages, start=1):
        for line in text.splitlines():
            value = _value_after_label(line, wanted)
            if value and len(value) <= _MAX_VALUE_LENGTH and value.isprintable():
                found.setdefault(value, page_number)
    if len(found) != 1:
        return None
    value, page_number = next(iter(found.items()))
    return LabelledValue(value=value, page_number=page_number)


def normalize_number(value: str) -> str | None:
    """Return a plain number; currency, percentages and unclear values give None."""

    text = value.strip()
    if not _PLAIN_NUMBER.fullmatch(text) or _AMBIGUOUS_NUMBER.fullmatch(text):
        return None
    return text.replace(",", "")


def match_option(value: str, options: Sequence[str]) -> str | None:
    """Return the option the value exactly matches, ignoring case, else None."""

    wanted = value.strip().casefold()
    return next((option for option in options if option.casefold() == wanted), None)


def normalize_date(value: str) -> str | None:
    """Return an ISO date for a recognised unambiguous day-first format, else None."""

    for date_format in _DATE_FORMATS:
        try:
            parsed: date = datetime.strptime(value.strip(), date_format).date()
        except ValueError:
            continue
        return parsed.isoformat()
    return None
