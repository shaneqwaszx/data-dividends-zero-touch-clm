# Per-user request rate for hosted GPT-OSS case chat (D-134, proposed, not active).
#
# The money limit is the ledger's (budget.py): a hard daily ceiling, checked with every open
# reservation inside one transaction, durable across restarts. This module is only a rate: it
# stops one signed-in user from taking the site's whole day, or from sending requests faster
# than answers can be read. It holds no money figure of its own. Its two bounds are:
#
#     per minute   MINUTE_LIMIT requests per user (an engineering figure, not a cost figure)
#     per hour     a share of the worst-case day: the registered daily ceiling divided by the
#                  existing worst-case reservation of one call
#                  (remote_checks.typical_reservation) is how many calls the day admits if
#                  every call cost its whole reservation; one user may make at most
#                  1/WORST_CASE_DAY_SHARE of that number in any hour
#
# The windows are kept in process memory (a restart clears them; nothing about money depends
# on them). A refused request is answered from the case data, as when no model is available;
# nothing is sent to the provider and nothing is reserved.
#
# Comments, not docstrings, in this module: string constants in this package feed the D-094
# boundary vocabulary (scripts/build_synthetic_boundary.py), which this must not widen.

import threading
import time
from collections import deque
from collections.abc import Callable

MINUTE_LIMIT = 6
WORST_CASE_DAY_SHARE = 4
MINUTE_SECONDS = 60.0
HOUR_SECONDS = 3600.0
# Users tracked at once; the oldest idle one is dropped first (bounded memory).
MAX_USERS = 4096


def hourly_limit(daily_ceiling_micro_usd: int, reservation_micro_usd: int) -> int:
    # One user's requests per hour: a share of the calls a worst-case day admits (never 0).
    if daily_ceiling_micro_usd <= 0 or reservation_micro_usd <= 0:
        return 1
    return max(1, daily_ceiling_micro_usd // reservation_micro_usd // WORST_CASE_DAY_SHARE)


class UserRate:
    # Sliding windows per user. ``admit`` records the request only when it is admitted.

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._seen: dict[str, deque[float]] = {}

    def admit(self, user: str, *, per_minute: int, per_hour: int) -> bool:
        now = self._clock()
        with self._lock:
            times = self._seen.get(user)
            if times is None:
                if len(self._seen) >= MAX_USERS:
                    oldest = min(self._seen, key=lambda name: self._seen[name][-1])
                    del self._seen[oldest]
                times = self._seen[user] = deque()
            while times and now - times[0] >= HOUR_SECONDS:
                times.popleft()
            in_minute = sum(1 for at in times if now - at < MINUTE_SECONDS)
            if in_minute >= per_minute or len(times) >= per_hour:
                if not times:
                    del self._seen[user]
                return False
            times.append(now)
            return True
