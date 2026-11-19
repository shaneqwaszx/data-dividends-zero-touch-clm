"""Chat contexts: the memory of one chat, for one user and one case (or the general chat).

D-115 (proposed) case memory lifecycle:

- Opening a case's chat opens a context bound to that user and that case; the general chat
  (no case) has its own. A context never holds another case's turns.
- The turns are kept in this process's memory only (never written to disk) and are the only
  history a question may use when it names its context: the browser's history text is not.
- Leaving the case, closing the tab or signing out closes the context and drops its turns.
  A context idle for ``idle_seconds``, or older than ``max_seconds``, is dropped as a backstop
  when no close arrives. A restart drops every context.
- An answer still being written when its context closes is not added to any context: every
  turn is added under the context's generation, which closing ends.

The redacted answer records of D-105 (feedback and History) are a separate store with their own
retention and are not deleted here (see the D-115 owner decision on retention).
"""

from __future__ import annotations

import secrets
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

GENERAL = "general"
CONTEXT_ID = r"^[0-9a-f]{32}$"

Scope = Literal["case", "general"]


class ContextRefused(Exception):
    """A context cannot be used as asked (closed code)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class _Context:
    context_id: str
    user_id: str
    case_id: str | None
    opened: float
    used: float
    turns: deque[dict[str, str]] = field(default_factory=deque)
    generation: int = 0
    reasoning_turns: int = 0
    reasoning_basis: str | None = None

    @property
    def scope(self) -> Scope:
        return "general" if self.case_id is None else "case"


@dataclass(frozen=True)
class Ticket:
    """What a question may use: the context's turns as they were, and the generation under
    which its answer may be added."""

    context_id: str
    generation: int
    history: tuple[dict[str, str], ...]
    reasoning_history: tuple[dict[str, str], ...] = ()
    reasoning_basis: str | None = None


class ContextStore:
    def __init__(
        self,
        *,
        idle_seconds: int,
        max_seconds: int,
        max_turns: int,
        max_per_user: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._idle = idle_seconds
        self._max = max_seconds
        self._max_turns = max_turns
        self._per_user = max_per_user
        self._clock = clock
        self._lock = threading.Lock()
        self._contexts: dict[str, _Context] = {}

    # --- lifecycle -----------------------------------------------------------------------

    def open(self, user_id: str, case_id: str | None) -> str:
        """A new, empty context for this user on this case (None: the general chat). The
        user's oldest context is closed when they already hold the most allowed."""

        with self._lock:
            self._sweep()
            mine = sorted(
                (c for c in self._contexts.values() if c.user_id == user_id),
                key=lambda c: c.used,
            )
            for old in mine[: max(0, len(mine) - self._per_user + 1)]:
                self._drop(old.context_id)
            now = self._clock()
            context_id = secrets.token_hex(16)
            self._contexts[context_id] = _Context(context_id, user_id, case_id, now, now)
            return context_id

    def close(self, context_id: str, user_id: str | None = None) -> bool:
        """Drop the context and its turns. With ``user_id``, only that user's context."""

        with self._lock:
            context = self._contexts.get(context_id)
            if context is None or (user_id is not None and context.user_id != user_id):
                return False
            self._drop(context_id)
            return True

    def close_user(self, user_id: str, *, case_id: str | None = None) -> int:
        """Drop every context of this user (on this case only, when given)."""

        with self._lock:
            found = [
                c.context_id
                for c in self._contexts.values()
                if c.user_id == user_id and (case_id is None or c.case_id == case_id)
            ]
            for context_id in found:
                self._drop(context_id)
            return len(found)

    # --- use -----------------------------------------------------------------------------

    def ticket(self, context_id: str, user_id: str, case_id: str | None) -> Ticket:
        """The context's turns for a question by this user about this case (None: general).
        Any mismatch refuses, and a context of another user is reported as unknown."""

        with self._lock:
            self._sweep()
            context = self._contexts.get(context_id)
            if context is None or context.user_id != user_id:
                raise ContextRefused("CONTEXT_UNKNOWN")
            if context.case_id != case_id:
                raise ContextRefused("CONTEXT_SCOPE_MISMATCH")
            context.used = self._clock()
            history = tuple(dict(t) for t in context.turns)
            return Ticket(
                context_id,
                context.generation,
                history,
                history[-context.reasoning_turns :] if context.reasoning_turns else (),
                context.reasoning_basis,
            )

    def add(
        self,
        ticket: Ticket,
        question: str,
        answer: str,
        *,
        verified_reasoning: bool = False,
        reasoning_basis: str | None = None,
    ) -> bool:
        """Add one exchange, only while the context is open under the ticket's generation
        (so a late answer never lands in a context that was closed or reopened)."""

        with self._lock:
            context = self._contexts.get(ticket.context_id)
            if context is None or context.generation != ticket.generation:
                return False
            if context.reasoning_basis != reasoning_basis:
                context.reasoning_turns = 0
            context.reasoning_basis = reasoning_basis if verified_reasoning else None
            context.turns.append({"role": "user", "content": question})
            context.turns.append({"role": "assistant", "content": answer})
            while len(context.turns) > self._max_turns:
                context.turns.popleft()
            # Only a contiguous suffix of verified-synthetic, model-answered exchanges may
            # become external context. Older local, fallback or staff-derived answers reset it.
            context.reasoning_turns = (
                min(context.reasoning_turns + 2, len(context.turns)) if verified_reasoning else 0
            )
            context.used = self._clock()
            return True

    # --- inspection (tests, metrics) -----------------------------------------------------

    def count(self) -> int:
        with self._lock:
            self._sweep()
            return len(self._contexts)

    def turns(self, context_id: str) -> int:
        with self._lock:
            context = self._contexts.get(context_id)
            return 0 if context is None else len(context.turns)

    # --- internal ------------------------------------------------------------------------

    def _drop(self, context_id: str) -> None:
        context = self._contexts.pop(context_id, None)
        if context is not None:
            context.generation += 1
            context.turns.clear()

    def _sweep(self) -> None:
        now = self._clock()
        expired = [
            c.context_id
            for c in self._contexts.values()
            if now - c.used > self._idle or now - c.opened > self._max
        ]
        for context_id in expired:
            self._drop(context_id)
