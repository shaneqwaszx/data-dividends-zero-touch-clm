"""Server-side daily budget for GoldTier Sandbox reads (ST-7, standing read).

A read is claimed before any request leaves the backend. The budget never authorises
anything: writes stay governed by the D-137 window, and the budget does not count them,
because a refusal after the ledger has marked a write would burn the operation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Protocol


def budget_day(now: datetime) -> str:
    """The UTC calendar day a read is counted against."""

    if now.tzinfo is None:
        raise ValueError("budget time must be time-zoned")
    return now.astimezone(UTC).date().isoformat()


class GoldTierReadBudget(Protocol):
    @property
    def limit(self) -> int | None: ...

    def claim(self, now: datetime) -> bool:
        """Count one read for `now`'s UTC day; False when the day's limit is reached."""

    def used(self, now: datetime) -> int:
        """Reads already counted for `now`'s UTC day."""


class UnlimitedGoldTierReadBudget:
    """Outside staging, and with no limit configured, reads are not counted."""

    limit: int | None = None

    def claim(self, now: datetime) -> bool:
        return True

    def used(self, now: datetime) -> int:
        return 0


class InMemoryGoldTierReadBudget:
    """Memory persistence mode and tests. Process-local by design."""

    def __init__(self, limit: int) -> None:
        if limit < 0:
            raise ValueError("limit must not be negative")
        self._limit = limit
        self._counts: dict[str, int] = {}
        self._guard = Lock()

    @property
    def limit(self) -> int | None:
        return self._limit

    def claim(self, now: datetime) -> bool:
        day = budget_day(now)
        with self._guard:
            count = self._counts.get(day, 0)
            if count >= self._limit:
                return False
            self._counts[day] = count + 1
            return True

    def used(self, now: datetime) -> int:
        with self._guard:
            return self._counts.get(budget_day(now), 0)
