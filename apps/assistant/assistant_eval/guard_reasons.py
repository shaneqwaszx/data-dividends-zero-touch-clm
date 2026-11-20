"""G-6 diagnostics (R0, evaluation harness only): why the guard left sentences out.

G-6 is kept / written model sentences. A failed G-6 said how many sentences were left out but
not which CopilotGuard rule removed them, so a failure could not be diagnosed. While a
qualification asks its questions, ``recording()`` observes, without changing, two existing
service results:

- each ``copilot.CopilotGuard.finish()`` result's ``left_out`` list (the closed reason code of
  every sentence it removed: ``unsupported_name``, ``ubo_determination``, ...);
- each D-142 restore line that ``privacy_boundary.Protected.restore_line`` dropped (these
  lines never reach the guard and are not part of G-6; recorded so the two are not confused).

Only counts and closed codes are kept: no sentence, answer or case text. The wrapped methods
return exactly what the originals return, and both are put back when the block ends. This
module is not part of the qualification basis (``model_qualification.BASIS_FILES``): it
observes the answers, it does not shape them.
"""

from __future__ import annotations

import re
import threading
from collections import Counter
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from ai_assistant import copilot, privacy_boundary

# A reason code is a short closed identifier; anything else is counted, never kept.
_CODE = re.compile(r"[a-z][a-z0-9_]{0,47}")
OTHER = "other"
# Left-out lines with no recorded code (an exact-lines answer, which has a single closed code
# of its own, or a check outside the copilot guard).
UNATTRIBUTED = "unattributed"


class GuardReasons:
    """What the guard and the restore step reported since the last ``take()``."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reasons: Counter[str] = Counter()
        self._dropped = 0

    def add_reasons(self, codes: Iterable[str]) -> None:
        with self._lock:
            for code in codes:
                closed = isinstance(code, str) and _CODE.fullmatch(code)
                self._reasons[code if closed else OTHER] += 1

    def add_dropped(self) -> None:
        with self._lock:
            self._dropped += 1

    def take(self) -> tuple[dict[str, int], int]:
        """The reason counts and restore-dropped lines so far, and start again from zero."""

        with self._lock:
            reasons, dropped = dict(sorted(self._reasons.items())), self._dropped
            self._reasons, self._dropped = Counter(), 0
        return reasons, dropped


_active: GuardReasons | None = None
_patch_lock = threading.Lock()


def active() -> GuardReasons | None:
    """The recorder of the qualification now asking its questions, if any."""

    return _active


@contextmanager
def recording() -> Iterator[GuardReasons]:
    """Record guard reason codes and restore drops for the duration of the block."""

    global _active
    with _patch_lock:
        if _active is not None:
            raise RuntimeError("guard reasons are already being recorded")
        recorder = GuardReasons()
        guard_finish = copilot.CopilotGuard.finish
        restore_line = privacy_boundary.Protected.restore_line

        def finish(self: copilot.CopilotGuard) -> copilot.CopilotCheck:
            check = guard_finish(self)
            recorder.add_reasons(check.left_out)
            return check

        def restore(self: privacy_boundary.Protected, line: str) -> str | None:
            restored = restore_line(self, line)
            if restored is None:
                recorder.add_dropped()
            return restored

        copilot.CopilotGuard.finish = finish  # type: ignore[method-assign]
        privacy_boundary.Protected.restore_line = restore  # type: ignore[method-assign]
        _active = recorder
    try:
        yield recorder
    finally:
        with _patch_lock:
            copilot.CopilotGuard.finish = guard_finish  # type: ignore[method-assign]
            privacy_boundary.Protected.restore_line = restore_line  # type: ignore[method-assign]
            _active = None


def reason_breakdown(turns: list[Any]) -> dict[str, Any]:
    """Closed reason codes of the left-out sentences, in total and by turn key, and the lines
    the D-142 restore dropped (not part of G-6). A turn's left-out sentences with no recorded
    code are counted as ``unattributed``, so each turn's codes add up to its left-out count."""

    total: Counter[str] = Counter()
    by_turn: dict[str, dict[str, int]] = {}
    dropped = 0
    for turn in turns:
        reasons = Counter(getattr(turn, "left_out_reasons", None) or {})
        missing = int(turn.metrics["left_out_lines"]) - sum(reasons.values())
        if missing > 0:
            reasons[UNATTRIBUTED] += missing
        dropped += int(getattr(turn, "restore_dropped_lines", 0) or 0)
        if reasons:
            key = f"{turn.key}@{turn.rep}" if getattr(turn, "rep", 0) else str(turn.key)
            by_turn[key] = dict(sorted(reasons.items()))
            total.update(reasons)
    return {
        "left_out_reasons": dict(sorted(total.items())),
        "left_out_reasons_by_turn": by_turn,
        "restore_dropped_lines": dropped,
    }
