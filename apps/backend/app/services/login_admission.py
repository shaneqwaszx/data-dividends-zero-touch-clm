"""Process-local admission control for the single staging login worker."""

from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from ipaddress import IPv6Address, ip_address
from math import ceil
from threading import Lock
from time import monotonic

SOURCE_BURST = 10
SOURCE_INTERVAL = 6
AGGREGATE_BURST = 20
AGGREGATE_INTERVAL = 1
MAX_CONCURRENT = 2
MAX_SOURCES = 256
SOURCE_IDLE = SOURCE_BURST * SOURCE_INTERVAL


class LoginAdmissionDenied(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


@dataclass
class _Bucket:
    tokens: float
    updated_at: float

    def available(self, now: float, capacity: int, interval: int) -> float:
        return min(capacity, self.tokens + (now - self.updated_at) / interval)


def _source_key(host: str | None) -> str:
    if host is None:
        return "unknown"
    try:
        address = ip_address(host)
    except ValueError:
        return "unknown"
    if isinstance(address, IPv6Address) and address.ipv4_mapped is not None:
        return str(address.ipv4_mapped)
    return str(address)


class LoginAdmission:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._lock = Lock()
        self._active = 0
        self._aggregate = _Bucket(AGGREGATE_BURST, clock())
        self._sources: OrderedDict[str, _Bucket] = OrderedDict()

    @contextmanager
    def admit(self, host: str | None) -> Iterator[None]:
        source = _source_key(host)
        with self._lock:
            self._reserve(source)
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1

    def _reserve(self, source: str) -> None:
        now = self._clock()
        while self._sources:
            oldest = next(iter(self._sources.values()))
            if now - oldest.updated_at < SOURCE_IDLE:
                break
            self._sources.popitem(last=False)

        bucket = self._sources.get(source)
        if bucket is None and len(self._sources) >= MAX_SOURCES:
            # Never evict a source whose budget has yet to refill.
            oldest = next(iter(self._sources.values()))
            raise LoginAdmissionDenied(ceil(oldest.updated_at + SOURCE_IDLE - now))

        available = bucket.available(now, SOURCE_BURST, SOURCE_INTERVAL) if bucket else SOURCE_BURST
        aggregate = self._aggregate.available(now, AGGREGATE_BURST, AGGREGATE_INTERVAL)
        if available < 1 or aggregate < 1 or self._active >= MAX_CONCURRENT:
            raise LoginAdmissionDenied(
                max(
                    1,
                    ceil((1 - available) * SOURCE_INTERVAL),
                    ceil((1 - aggregate) * AGGREGATE_INTERVAL),
                )
            )

        self._sources[source] = _Bucket(available - 1, now)
        self._sources.move_to_end(source)
        self._aggregate = _Bucket(aggregate - 1, now)
        self._active += 1
