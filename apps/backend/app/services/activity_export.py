"""Safe, bounded CSV projection for already-authorized case activity pages."""

from __future__ import annotations

import csv
import io
import unicodedata
from datetime import UTC

from app.domain.case_management import CaseActivityPage

_COLUMNS = (
    "case_id",
    "sequence",
    "timestamp_utc",
    "event_type",
    "status",
    "stage",
    "outcome",
    "code",
    "message",
    "current_priority",
    "current_client_scope_label",
)
_FORMULA_PREFIXES = frozenset("=+-@")


def _formula_significant_text(text: str) -> str:
    index = 0
    while index < len(text):
        character = text[index]
        if not character.isspace() and not unicodedata.category(character).startswith("C"):
            break
        index += 1
    return text[index:]


def _safe_cell(value: object | None) -> str:
    if value is None:
        return ""
    text = str(value)
    significant = _formula_significant_text(text)
    if significant and significant[0] in _FORMULA_PREFIXES:
        return f"'{text}"
    return text


def render_case_activity_csv(page: CaseActivityPage) -> str:
    """Render only the bounded page supplied by the authorized query service."""

    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(_COLUMNS)
    for item in page.items:
        timestamp = item.timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
        writer.writerow(
            (
                _safe_cell(item.case_id),
                item.sequence,
                timestamp,
                _safe_cell(item.event_type.value),
                _safe_cell(item.status.value),
                _safe_cell(item.stage.value),
                _safe_cell(item.outcome.value),
                _safe_cell(item.code),
                _safe_cell(item.message),
                _safe_cell(item.current_priority),
                _safe_cell(item.current_client_scope_label),
            )
        )
    return stream.getvalue()
