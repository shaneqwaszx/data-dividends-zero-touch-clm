"""Answer records (ADR-012 Amendment 1, D-084, proposed): what the server produced for one
answer, so a Director can see why the AI said what it said.

A record holds only what this request produced or received: the question as the server used
it, the ids of earlier answers it checked belong to the same user and case, the case state,
the knowledge retrieved, the allowed lines, the lines kept, the lines left out (redacted with
the case Redactor and capped), and how the answer was made. Browser-sent history text is
never stored. Records are never put into a prompt and never copied into knowledge.
"""

import hashlib
import json
import logging
import secrets
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any, Literal

from .knowledge.retrieval import case_context
from .knowledge.store import KnowledgeStore
from .knowledge_answers import TaggedHit

# A random, unguessable id (128 bits, URL-safe base64 without padding).
ANSWER_ID = r"^[A-Za-z0-9_-]{22}$"
MAX_DROPPED_BYTES = 8 * 1024
PURGE_INTERVAL_SECONDS = 3600.0

FallbackReason = Literal["model_unavailable", "nothing_allowed", "cut_short"]

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


def knowledge_used(
    tagged: Sequence[TaggedHit], *, confidence: str | None, degraded: bool | None
) -> dict[str, Any]:
    return {
        "confidence": confidence,
        "degraded": degraded,
        "entries": [
            {
                "tag": item.tag,
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
