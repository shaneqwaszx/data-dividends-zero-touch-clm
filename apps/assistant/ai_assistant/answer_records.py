"""Answer records (ADR-012 Amendment 1, D-084, proposed): what the server produced for one
answer, so a Director can see why the AI said what it said.

A record holds only what this request produced or received: the question as the server used
it, the ids of earlier answers it checked belong to the same user and case, the case state,
the knowledge retrieved (with the score thresholds), the allowed lines tagged by where they
come from, the lines kept, the answer as the RM saw it (a case-data answer redacted), the lines
left out (redacted with the case Redactor and capped), and how the answer was made.
Browser-sent history text is never stored. Records are never put into a prompt and never
copied into knowledge.
"""

import hashlib
import json
import logging
import re
import secrets
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any, Literal

from .guardrails import allowed_guidance
from .guide import NO_CONTACT
from .knowledge.retrieval import case_context
from .knowledge.store import KnowledgeStore
from .knowledge_answers import TaggedHit

# A random, unguessable id (128 bits, URL-safe base64 without padding).
ANSWER_ID = r"^[A-Za-z0-9_-]{22}$"
MAX_DROPPED_BYTES = 8 * 1024
PURGE_INTERVAL_SECONDS = 3600.0

FallbackReason = Literal["model_unavailable", "nothing_allowed", "cut_short"]
LineSource = Literal["policy", "case", "knowledge"]

# The catalog's fixed lines (the same on every case): what it gives with no case facts, except
# "no contact named", which is offered only when the case names no owner (D-090).
POLICY_LINES = frozenset(allowed_guidance({})) - {NO_CONTACT}

log = logging.getLogger("ai_assistant")


def new_answer_id() -> str:
    return secrets.token_urlsafe(16)


def case_snapshot(facts: dict[str, Any]) -> dict[str, Any]:
    """The case at the moment of the answer: blocker codes, stage, steps and a facts hash."""

    overall = facts.get("overall") or {}
    return {
        "blocker_codes": list(case_context(facts).blocker_codes),
        "stage": overall.get("current_stage"),
        "steps_done": overall.get("steps_done"),
        "steps_total": overall.get("steps_total"),
        "facts_hash": hashlib.sha256(
            json.dumps(facts, sort_keys=True, default=str).encode()
        ).hexdigest(),
    }


def allowed_lines(
    facts: dict[str, Any],
    knowledge_lines: Sequence[str],
    redact: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    """The allowed lines of this answer, each tagged by where it comes from: a fixed catalog
    line (policy), a catalog line that depends on this case (case), or approved knowledge.

    With ``redact``, every line except the fixed policy lines is stored redacted: since D-090
    some catalog lines carry ACRA and document values, which a record may not keep (ADR-012
    section A, D-084). The record's chosen lines and shown answer are redacted the same way,
    so they still match these lines.
    """

    knowledge = set(knowledge_lines)
    lines = dict.fromkeys([*allowed_guidance(facts), *knowledge_lines])
    sources: list[dict[str, str]] = []
    for line in lines:
        source: LineSource = (
            "knowledge" if line in knowledge else "policy" if line in POLICY_LINES else "case"
        )
        text = redact(line) if redact is not None and source != "policy" else line
        sources.append({"text": text, "source": source})
    return sources


def knowledge_used(
    tagged: Sequence[TaggedHit],
    *,
    confidence: str | None,
    degraded: bool | None,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    return {
        "confidence": confidence,
        "degraded": degraded,
        # The minimum score an entry of each kind needs to be used.
        "thresholds": thresholds,
        "entries": [
            {
                "tag": item.tag,
                "kind": item.hit.entry.kind.value,
                "entry_id": item.hit.entry.entry_id,
                "version": item.hit.entry.version,
                "score": round(item.hit.score, 4),
                "parts": {name: round(value, 4) for name, value in item.hit.parts.items()},
                "fallback": item.hit.fallback,
            }
            for item in tagged
        ],
    }


def capped_dropped(lines: Sequence[str], redact: Callable[[str], str]) -> list[str]:
    """The left-out model lines, redacted, keeping whole lines up to MAX_DROPPED_BYTES."""

    kept: list[str] = []
    size = 0
    for line in lines:
        text = redact(line)
        length = len(text.encode("utf-8"))
        if size + length > MAX_DROPPED_BYTES:
            break
        kept.append(text)
        size += length
    return kept


# Where one sentence ends and the next starts, and a list marker the model put before a line.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_LIST_MARKER = re.compile(r"^(?:[-*•]|\d{1,3}[.)])\s+")


def fix_title(blocker_codes: Sequence[str]) -> str:
    """A starting title for a Director's fix: the request's first blocker type, in words."""

    code = next((str(code) for code in blocker_codes if code), "")
    return code.replace("_", " ").strip().capitalize() or "General"


def fix_start_lines(record: dict[str, Any], redact: Callable[[str], str]) -> list[str]:
    """What a Director's fix can start from: the lines the AI wrote that were left out, and
    any shown model line that is not an allowed line, one sentence per line, redacted.

    Notices and the catalog's fixed disclaimers (policy lines) are left out: they are the
    app's wording, not something the AI knew. Nothing is generated; it is the record's text.
    """

    allowed = {
        line["text"] if isinstance(line, dict) else str(line)
        for line in record.get("allowed_lines") or []
    }
    written = [
        *(record.get("dropped_lines") or []),
        *(line for line in record.get("chosen_lines") or [] if line not in allowed),
    ]
    skip = {*POLICY_LINES, *((record.get("result") or {}).get("notices") or [])}
    lines: list[str] = []
    for text in written:
        if str(text).strip() in skip:
            continue
        # Redact the whole line before splitting it: a name such as "... PTE. LTD." would
        # otherwise be cut at its full stop and escape the Redactor.
        for sentence in _SENTENCE_END.split(redact(str(text).strip())):
            sentence = _LIST_MARKER.sub("", sentence.strip())
            if not sentence or sentence in skip:
                continue
            cleaned = redact(sentence)
            if cleaned not in lines:
                lines.append(cleaned)
    return lines


class AnswerRecorder:
    """Writes answer records and deletes expired ones (on start-up, then at most hourly)."""

    def __init__(
        self,
        store: KnowledgeStore,
        *,
        unrated_days: int,
        closed_days: int,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.store = store
        self.unrated_days = unrated_days
        self.closed_days = closed_days
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._last_purge: float | None = None

    def purge(self) -> None:
        self.store.purge_answer_records(
            unrated_days=self.unrated_days, closed_days=self.closed_days
        )
        with self._lock:
            self._last_purge = self._monotonic()

    def _purge_due(self) -> bool:
        with self._lock:
            now = self._monotonic()
            if self._last_purge is not None and now - self._last_purge < PURGE_INTERVAL_SECONDS:
                return False
            self._last_purge = now
            return True

    def save(self, record: dict[str, Any]) -> str | None:
        """Store the record; its id, or None when it could not be stored (the answer is
        still given, it just cannot be rated)."""

        days = (self.unrated_days, self.closed_days) if self._purge_due() else None
        try:
            self.store.add_answer_record(record, purge_days=days)
        except Exception:  # an answer record must never break the answer itself
            log.exception("answer record not stored")
            return None
        return str(record["id"])
