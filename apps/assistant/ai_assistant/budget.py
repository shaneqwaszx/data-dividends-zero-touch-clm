"""Lifetime budget guard for the remote profile (D-091, proposed; dormant in Phase A2).

A local SQLite ledger (git-ignored, one instance) counts the cumulative usage of ONE
OpenRouter API key in integer micro-USD, including what that key had used before the
ledger existed. Nothing resets by date. The provider's own non-resetting key limit stays an
independent protection; this ledger only stops first.

    C   cap: the most this key may ever have used (its cumulative usage, not "new" spend)
    U0  the key's usage when the ledger was created (entered by the operator)
    B   provider-anchored baseline, covering every call with id <= H
    L   charges of closed calls with id > H (never includes U0)
    O   reservations of open calls
    K   committed usage = B + L + O; a call is admitted only if K + r <= C

The reservation r is a LABELLED bound, not a proven maximum: content tokens are bounded by
UTF-8 bytes (byte-level BPE); envelope/template tokens by an engineering allowance; prices
and output by the endpoint record. Calls that cost more than reserved, report more tokens
than bounded, lack usage, look misrouted, or end with a provider refusal open a breaker
that only an operator can close after reconciling (scripts/budget_ledger.py). Anything
uncertain is charged at its full reservation. The ledger never creates itself, never
repairs itself and refuses when missing, corrupt, newer or inconsistent.

Daily allowance (D-095). On top of the lifetime cap, every admission also needs

    D   today's spend: charges of closed calls reserved since the last Singapore midnight
        (Asia/Singapore, UTC+8, no daylight saving) plus the reservations of ALL open calls
        (an open call from yesterday still counts today)
    D + r <= daily cap (DEFAULT_DAILY_CAP_MICRO_USD, US$1.00, unless set otherwise; D-098:
             a default, not a ceiling)

It is worked out from the call rows in the same ``BEGIN IMMEDIATE`` transaction as the
lifetime check, so it holds across threads, processes and restarts, survives reconciliation
(which never deletes a call) and needs no schema change: the "reset" at midnight is only the
window moving on; no row, total or event is erased. It does not depend on which key is used.
"""

import secrets
import sqlite3
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing, closing, suppress
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any

import anyio

from .llm import (
    MODEL_ANOMALIES,
    MODEL_ERROR_CLASSES,
    ROUTING_ANOMALIES,
    CallBudget,
    ModelAnswer,
    ModelCallError,
    ModelUsage,
    Piece,
    message_bytes,
    micro_usd,
)
from .model_profiles import ENDPOINT_SLUG, OPENROUTER_PROFILE_ID, ApprovedEndpoint

SCHEMA_VERSION = 1
# Approved opaque operator identifiers for a key (S3). A label never holds a name or case.
KEY_ALIASES = ("key-01", "key-02", "key-03", "key-04")
PROFILES = (OPENROUTER_PROFILE_ID,)
# Engineering allowances for tokens the chat template adds (not documented; Phase B checks).
PER_MESSAGE_OVERHEAD = 16
TEMPLATE_OVERHEAD = 1024
LEASE_GRACE_SECONDS = 60
# A provider usage above the ledger by more than this opens the breaker.
RECONCILE_TOLERANCE_MICRO_USD = 50_000
MAX_MICRO_USD = 10**12
# D-095: the most the remote profile may reserve plus spend in one Singapore calendar day
# when nothing else is set. D-098: the default, not a ceiling; the setting
# (AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD) or HR may set any amount up to MAX_MICRO_USD.
DEFAULT_DAILY_CAP_MICRO_USD = 1_000_000
SINGAPORE = timezone(timedelta(hours=8), "Asia/Singapore")
_MILLION = Decimal(1_000_000)

# Provider refusals that would repeat on the next call: stop and let an operator look.
TRIP_ERROR_CLASSES = frozenset(
    {
        "bad_request",
        "auth",
        "payment",
        "payment_key_limit",
        "forbidden",
        "not_allowed",
        "no_provider",
    }
)
BREAKER_CODES = (
    "usage_missing",
    "cost_above_reservation",
    "token_bound_exceeded",
    "routing_anomaly",
    "provider_error",
    "abandoned_call",
    "reconcile_drift",
    "ledger_write_failed",
)
EVENTS = (
    "init",
    "cap_lowered",
    "cap_raised",
    "reconciled",
    "released",
    "breaker_opened",
    "breaker_reset",
)
CALL_ANOMALIES = (*sorted(MODEL_ANOMALIES), "cost_above_reservation", "token_bound_exceeded")
ANOMALY_BITS = {code: 1 << index for index, code in enumerate(CALL_ANOMALIES)}


class LedgerError(Exception):
    """The ledger refused an operation. The code is closed; the message never holds data."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class BudgetRefusedError(ModelCallError):
    """The guard refused the call before any request was made."""

    def __init__(self, outcome: str, reserved_micro_usd: int = 0) -> None:
        super().__init__(
            "budget_refused",
            budget=CallBudget(outcome=outcome, reserved_micro_usd=reserved_micro_usd),
        )


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


_HEX32 = "length({0}) = 32 AND {0} NOT GLOB '*[^0-9a-f]*'"
SCHEMA = f"""
CREATE TABLE ledger_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    schema_version INTEGER NOT NULL CHECK (schema_version = {SCHEMA_VERSION}),
    ledger_id TEXT NOT NULL CHECK ({_HEX32.format("ledger_id")}),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    profile_id TEXT NOT NULL CHECK ({_in("profile_id", PROFILES)}),
    key_alias TEXT NOT NULL CHECK ({_in("key_alias", KEY_ALIASES)}),
    cap_micro_usd INTEGER NOT NULL CHECK (cap_micro_usd BETWEEN 0 AND {MAX_MICRO_USD}),
    opening_usage_micro_usd INTEGER NOT NULL CHECK (opening_usage_micro_usd >= 0),
    baseline_micro_usd INTEGER NOT NULL CHECK (baseline_micro_usd >= 0),
    baseline_high_water_call_id INTEGER NOT NULL CHECK (baseline_high_water_call_id >= 0),
    last_provider_usage_micro_usd INTEGER NOT NULL CHECK (last_provider_usage_micro_usd >= 0),
    local_charged_micro_usd INTEGER NOT NULL CHECK (local_charged_micro_usd >= 0),
    open_reserved_micro_usd INTEGER NOT NULL CHECK (open_reserved_micro_usd >= 0),
    breaker_open INTEGER NOT NULL CHECK (breaker_open IN (0, 1)),
    breaker_code TEXT CHECK (breaker_code IS NULL OR {_in("breaker_code", BREAKER_CODES)}),
    breaker_opened_at INTEGER,
    last_reconciled_at INTEGER,
    CHECK ((breaker_open = 1) = (breaker_code IS NOT NULL))
) STRICT;
CREATE TABLE calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id TEXT NOT NULL UNIQUE CHECK ({_HEX32.format("reservation_id")}),
    instance_id TEXT NOT NULL CHECK ({_HEX32.format("instance_id")}),
    created_at INTEGER NOT NULL,
    lease_expires_at INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('open', 'settled', 'unsettled', 'abandoned')),
    reserved_micro_usd INTEGER NOT NULL CHECK (reserved_micro_usd > 0),
    charged_micro_usd INTEGER CHECK (charged_micro_usd IS NULL OR charged_micro_usd >= 0),
    prompt_bound_tokens INTEGER NOT NULL CHECK (prompt_bound_tokens > 0),
    output_bound_tokens INTEGER NOT NULL CHECK (output_bound_tokens > 0),
    prompt_tokens INTEGER CHECK (prompt_tokens IS NULL OR prompt_tokens >= 0),
    completion_tokens INTEGER CHECK (completion_tokens IS NULL OR completion_tokens >= 0),
    reasoning_tokens INTEGER CHECK (reasoning_tokens IS NULL OR reasoning_tokens >= 0),
    cached_tokens INTEGER CHECK (cached_tokens IS NULL OR cached_tokens >= 0),
    requested_endpoint TEXT NOT NULL CHECK (
        length(requested_endpoint) BETWEEN 1 AND 200
        AND requested_endpoint NOT GLOB '*[^a-z0-9./_-]*'
    ),
    generation_ref TEXT CHECK (
        generation_ref IS NULL OR (
            length(generation_ref) BETWEEN 1 AND 80
            AND generation_ref NOT GLOB '*[^A-Za-z0-9_-]*'
        )
    ),
    verification TEXT NOT NULL CHECK (verification IN ('unverified', 'verified', 'quarantined')),
    error_class TEXT CHECK (
        error_class IS NULL OR {_in("error_class", tuple(sorted(MODEL_ERROR_CLASSES)))}
    ),
    anomaly_bits INTEGER NOT NULL CHECK (anomaly_bits BETWEEN 0 AND {2 ** len(CALL_ANOMALIES) - 1}),
    closed_at INTEGER,
    CHECK ((state = 'open') = (charged_micro_usd IS NULL)),
    CHECK ((state = 'open') = (closed_at IS NULL))
) STRICT;
CREATE TABLE operator_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    event TEXT NOT NULL CHECK ({_in("event", EVENTS)}),
    amount_micro_usd INTEGER CHECK (amount_micro_usd IS NULL OR amount_micro_usd >= 0),
    code TEXT CHECK (code IS NULL OR {_in("code", BREAKER_CODES)})
) STRICT;
"""
META_COLUMNS = (
    "id",
    "schema_version",
    "ledger_id",
    "created_at",
    "profile_id",
    "key_alias",
    "cap_micro_usd",
    "opening_usage_micro_usd",
    "baseline_micro_usd",
    "baseline_high_water_call_id",
    "last_provider_usage_micro_usd",
    "local_charged_micro_usd",
    "open_reserved_micro_usd",
    "breaker_open",
    "breaker_code",
    "breaker_opened_at",
    "last_reconciled_at",
)
CALL_COLUMNS = (
    "id",
    "reservation_id",
    "instance_id",
    "created_at",
    "lease_expires_at",
    "state",
    "reserved_micro_usd",
    "charged_micro_usd",
    "prompt_bound_tokens",
    "output_bound_tokens",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "cached_tokens",
    "requested_endpoint",
    "generation_ref",
    "verification",
    "error_class",
    "anomaly_bits",
    "closed_at",
)
EVENT_COLUMNS = ("id", "created_at", "event", "amount_micro_usd", "code")


# --- the reservation ---------------------------------------------------------------------


@dataclass(frozen=True)
class Reservation:
    prompt_bound_tokens: int
    output_bound_tokens: int
    micro_usd: int


def reservation_for(
    messages: list[dict[str, str]], endpoint: ApprovedEndpoint, max_tokens: int
) -> Reservation:
    """The labelled worst case for one call (see the module docstring and plan section 8.2).

    Output is bounded by ``max_tokens`` only where the endpoint record documents that it
    also bounds reasoning; otherwise by the endpoint's documented maximum completion."""

    prompt_bound = message_bytes(messages) + PER_MESSAGE_OVERHEAD * len(messages)
    prompt_bound += TEMPLATE_OVERHEAD
    output_bound = (
        max_tokens if endpoint.max_tokens_includes_reasoning else endpoint.max_completion_tokens
    )
    cost = (
        Decimal(prompt_bound) * endpoint.input_price_per_m / _MILLION
        + Decimal(output_bound) * endpoint.output_price_per_m / _MILLION
        + endpoint.request_price
    )
    return Reservation(prompt_bound, output_bound, max(1, micro_usd(cost)))


# --- the ledger --------------------------------------------------------------------------


@dataclass(frozen=True)
class LedgerStatus:
    profile_id: str
    key_alias: str
    cap: int
    opening_usage: int
    baseline: int
    high_water: int
    local_charged: int
    open_reserved: int
    open_calls: int
    last_provider_usage: int
    breaker_open: bool
    breaker_code: str | None

    @property
    def committed(self) -> int:
        return self.baseline + self.local_charged + self.open_reserved

    @property
    def headroom(self) -> int:
        return self.cap - self.committed


@dataclass(frozen=True)
class ClosedCall:
    """One closed call, content-free (Phase B verification and evaluation reports)."""

    call_id: int
    state: str
    reserved_micro_usd: int
    charged_micro_usd: int
    prompt_tokens: int | None
    completion_tokens: int | None
    reasoning_tokens: int | None
    generation_ref: str | None
    verification: str
    error_class: str | None
    anomaly_bits: int


def singapore_day_start_ms(now_ms: int) -> int:
    """The last Singapore midnight at or before ``now_ms`` (epoch milliseconds)."""

    moment = datetime.fromtimestamp(now_ms / 1000, SINGAPORE)
    midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp() * 1000)


def next_singapore_reset_ms(now_ms: int) -> int:
    start = datetime.fromtimestamp(singapore_day_start_ms(now_ms) / 1000, SINGAPORE)
    return int((start + timedelta(days=1)).timestamp() * 1000)


def daily_cap_for(setting: int | None) -> int | None:
    """The daily cap to enforce: the default, or the configured value; None when the
    setting is not a micro-USD count within 0..MAX_MICRO_USD (the caller refuses)."""

    if setting is None:
        return DEFAULT_DAILY_CAP_MICRO_USD
    if type(setting) is not int or not 0 <= setting <= MAX_MICRO_USD:
        return None
    return setting


@dataclass(frozen=True)
class DailyStatus:
    """Today's allowance (D-095), content-free. Times are epoch milliseconds."""

    cap: int
    settled_today: int
    open_reserved: int
    open_calls: int
    day_started_at: int
    next_reset_at: int

    @property
    def committed(self) -> int:
        return self.settled_today + self.open_reserved

    @property
    def remaining(self) -> int:
        return max(0, self.cap - self.committed)


def _daily_committed(connection: sqlite3.Connection, day_start: int) -> tuple[int, int, int]:
    """(closed charges reserved today, reservations of all open calls, open calls)."""

    settled, reserved, open_calls = connection.execute(
        "SELECT"
        " COALESCE(SUM(CASE WHEN state != 'open' AND created_at >= ?"
        " THEN charged_micro_usd END), 0),"
        " COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd END), 0),"
        " COALESCE(SUM(state = 'open'), 0)"
        " FROM calls",
        (day_start,),
    ).fetchone()
    return int(settled), int(reserved), int(open_calls)


def _hex32() -> str:
    return secrets.token_hex(16)


class BudgetLedger:
    """One key's lifetime ledger. Every operation is one ``BEGIN IMMEDIATE`` transaction on
    its own connection, so threads and processes on this machine are serialised."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], float] = time.time,
        busy_timeout: float = 2.0,
        durable: bool = True,
    ) -> None:
        self._path = path
        self._clock = clock
        self._busy_timeout = busy_timeout
        # Every commit is synced to disk; only invariant tests that never reopen after a
        # power loss turn this off for speed.
        self._synchronous = "FULL" if durable else "OFF"
        self.instance_id = _hex32()

    # -- lifecycle --

    @classmethod
    def initialise(
        cls,
        path: Path,
        *,
        cap_micro_usd: int,
        opening_usage_micro_usd: int,
        key_alias: str,
        profile_id: str = OPENROUTER_PROFILE_ID,
        clock: Callable[[], float] = time.time,
    ) -> "BudgetLedger":
        """Create a ledger only where none exists. The opening usage is the key's current
        cumulative usage, so a new ledger never resets what the key already spent."""

        if key_alias not in KEY_ALIASES:
            raise LedgerError("INVALID_INPUT", "the key alias is not an approved identifier")
        if profile_id not in PROFILES:
            raise LedgerError("INVALID_INPUT", "the profile does not use a budget ledger")
        for value in (cap_micro_usd, opening_usage_micro_usd):
            if type(value) is not int or not 0 <= value <= MAX_MICRO_USD:
                raise LedgerError("INVALID_INPUT", "amounts must be micro-USD counts")
        if path.exists():
            raise LedgerError("LEDGER_EXISTS", "a budget ledger already exists at this path")
        path.parent.mkdir(parents=True, exist_ok=True)
        ledger = cls(path, clock=clock)
        now = ledger._now()
        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=rwc", uri=True, isolation_level=None
        )
        with closing(connection):
            connection.execute("BEGIN IMMEDIATE")
            try:
                for statement in SCHEMA.split(";"):
                    if statement.strip():
                        connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.execute(
                    "INSERT INTO ledger_meta VALUES"
                    " (1, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0, 0, NULL, NULL, NULL)",
                    (
                        SCHEMA_VERSION,
                        _hex32(),
                        now,
                        profile_id,
                        key_alias,
                        cap_micro_usd,
                        opening_usage_micro_usd,
                        opening_usage_micro_usd,
                        opening_usage_micro_usd,
                    ),
                )
                ledger._event(connection, "init", cap_micro_usd)
                connection.execute("COMMIT")
            except BaseException:
                with suppress(sqlite3.Error):
                    connection.execute("ROLLBACK")
                raise
        ledger.verify()
        return ledger

    @classmethod
    def open(
        cls,
        path: Path,
        *,
        clock: Callable[[], float] = time.time,
        busy_timeout: float = 2.0,
        durable: bool = True,
    ) -> "BudgetLedger":
        """Open an existing ledger, check it fully and abandon expired calls."""

        ledger = cls(path, clock=clock, busy_timeout=busy_timeout, durable=durable)
        ledger.verify()
        ledger.recover()
        return ledger

    def _now(self) -> int:
        return int(self._clock() * 1000)

    def _connect(self) -> sqlite3.Connection:
        if not self._path.is_file():
            raise LedgerError("LEDGER_MISSING", "the budget ledger does not exist")
        try:
            connection = sqlite3.connect(
                f"{self._path.resolve().as_uri()}?mode=rw",
                uri=True,
                timeout=self._busy_timeout,
                isolation_level=None,
            )
            connection.execute(f"PRAGMA synchronous = {self._synchronous}")
        except sqlite3.OperationalError as error:
            if "locked" in str(error) or "busy" in str(error):
                raise LedgerError("LEDGER_BUSY", "the budget ledger is busy") from None
            raise LedgerError("LEDGER_CORRUPT", "the budget ledger cannot be opened") from None
        except sqlite3.DatabaseError:
            raise LedgerError("LEDGER_CORRUPT", "the budget ledger cannot be opened") from None
        return connection

    def _transaction(self, work: Callable[[sqlite3.Connection], Any]) -> Any:
        connection = self._connect()
        with closing(connection):
            try:
                connection.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as error:
                if "locked" in str(error) or "busy" in str(error):
                    raise LedgerError("LEDGER_BUSY", "the budget ledger is busy") from None
                raise LedgerError(
                    "LEDGER_UNAVAILABLE", "the budget ledger is not writable"
                ) from None
            except sqlite3.DatabaseError:
                raise LedgerError("LEDGER_CORRUPT", "the budget ledger is not readable") from None
            try:
                result = work(connection)
                connection.execute("COMMIT")
                return result
            except BaseException:
                with suppress(sqlite3.Error):
                    connection.execute("ROLLBACK")
                raise

    def _event(
        self,
        connection: sqlite3.Connection,
        event: str,
        amount: int | None,
        code: str | None = None,
    ) -> None:
        connection.execute(
            "INSERT INTO operator_events (created_at, event, amount_micro_usd, code)"
            " VALUES (?, ?, ?, ?)",
            (self._now(), event, amount, code),
        )

    @staticmethod
    def _meta(connection: sqlite3.Connection) -> sqlite3.Row:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM ledger_meta").fetchall()
        if len(rows) != 1:
            raise LedgerError("LEDGER_INCONSISTENT", "the budget ledger has no single header")
        row: sqlite3.Row = rows[0]
        return row

    # -- integrity --

    def verify(self) -> None:
        """Refuse a corrupt, newer, altered or inconsistent ledger. Never repairs it."""

        def check(connection: sqlite3.Connection) -> None:
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise LedgerError("LEDGER_CORRUPT", "the budget ledger failed its integrity check")
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise LedgerError("LEDGER_SCHEMA_UNSUPPORTED", "the ledger schema is not supported")
            for table, expected in (
                ("ledger_meta", META_COLUMNS),
                ("calls", CALL_COLUMNS),
                ("operator_events", EVENT_COLUMNS),
            ):
                found = tuple(row[1] for row in connection.execute(f"PRAGMA table_info({table})"))
                if found != expected:
                    raise LedgerError("LEDGER_SCHEMA_UNSUPPORTED", "the ledger tables are not v1")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                    " AND name NOT LIKE 'sqlite_%'"
                )
            }
            if tables != {"ledger_meta", "calls", "operator_events"}:
                raise LedgerError("LEDGER_SCHEMA_UNSUPPORTED", "the ledger tables are not v1")
            meta = self._meta(connection)
            if meta["schema_version"] != SCHEMA_VERSION:
                raise LedgerError("LEDGER_SCHEMA_UNSUPPORTED", "the ledger schema is not supported")
            local, reserved = connection.execute(
                "SELECT"
                " COALESCE(SUM(CASE WHEN state != 'open' AND id > ?"
                " THEN charged_micro_usd END), 0),"
                " COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd END), 0)"
                " FROM calls",
                (meta["baseline_high_water_call_id"],),
            ).fetchone()
            if (local, reserved) != (
                meta["local_charged_micro_usd"],
                meta["open_reserved_micro_usd"],
            ):
                raise LedgerError("LEDGER_INCONSISTENT", "the ledger totals do not match its calls")
            if meta["baseline_micro_usd"] < meta["last_provider_usage_micro_usd"]:
                raise LedgerError(
                    "LEDGER_INCONSISTENT", "the ledger baseline is below the provider"
                )

        try:
            self._transaction(check)
        except sqlite3.DatabaseError:
            raise LedgerError("LEDGER_CORRUPT", "the budget ledger is not readable") from None

    def status(self) -> LedgerStatus:
        def read(connection: sqlite3.Connection) -> LedgerStatus:
            meta = self._meta(connection)
            open_calls = connection.execute(
                "SELECT COUNT(*) FROM calls WHERE state = 'open'"
            ).fetchone()[0]
            return LedgerStatus(
                profile_id=meta["profile_id"],
                key_alias=meta["key_alias"],
                cap=meta["cap_micro_usd"],
                opening_usage=meta["opening_usage_micro_usd"],
                baseline=meta["baseline_micro_usd"],
                high_water=meta["baseline_high_water_call_id"],
                local_charged=meta["local_charged_micro_usd"],
                open_reserved=meta["open_reserved_micro_usd"],
                open_calls=open_calls,
                last_provider_usage=meta["last_provider_usage_micro_usd"],
                breaker_open=bool(meta["breaker_open"]),
                breaker_code=meta["breaker_code"],
            )

        result: LedgerStatus = self._transaction(read)
        return result

    def daily_status(self, daily_cap_micro_usd: int | None = None) -> DailyStatus:
        """Today's allowance, read-only (an invalid configured cap reads as no allowance)."""

        cap = daily_cap_for(daily_cap_micro_usd)

        def read(connection: sqlite3.Connection) -> DailyStatus:
            now = self._now()
            start = singapore_day_start_ms(now)
            settled, reserved, open_calls = _daily_committed(connection, start)
            return DailyStatus(
                cap=0 if cap is None else cap,
                settled_today=settled,
                open_reserved=reserved,
                open_calls=open_calls,
                day_started_at=start,
                next_reset_at=next_singapore_reset_ms(now),
            )

        result: DailyStatus = self._transaction(read)
        return result

    # -- calls --

    def _open_breaker(self, connection: sqlite3.Connection, code: str) -> None:
        meta = self._meta(connection)
        if meta["breaker_open"]:
            return
        connection.execute(
            "UPDATE ledger_meta SET breaker_open = 1, breaker_code = ?, breaker_opened_at = ?",
            (code, self._now()),
        )
        self._event(connection, "breaker_opened", None, code)

    def _abandon_expired(self, connection: sqlite3.Connection) -> int:
        """An open call whose lease ran out belongs to a process that stopped: charge its
        full reservation and open the breaker. A live lease (maybe another process) stays."""

        now = self._now()
        rows = connection.execute(
            "SELECT id, reserved_micro_usd FROM calls"
            " WHERE state = 'open' AND lease_expires_at < ?",
            (now,),
        ).fetchall()
        for call_id, reserved in rows:
            connection.execute(
                "UPDATE calls SET state = 'abandoned', charged_micro_usd = reserved_micro_usd,"
                " closed_at = ? WHERE id = ?",
                (now, call_id),
            )
            connection.execute(
                "UPDATE ledger_meta SET open_reserved_micro_usd = open_reserved_micro_usd - ?,"
                " local_charged_micro_usd = local_charged_micro_usd + ?",
                (reserved, reserved),
            )
        if rows:
            self._open_breaker(connection, "abandoned_call")
        return len(rows)

    def recover(self) -> int:
        count: int = self._transaction(self._abandon_expired)
        return count

    def open_breaker(self, code: str) -> None:
        self._transaction(lambda connection: self._open_breaker(connection, code))

    def reserve(
        self,
        reservation: Reservation,
        *,
        endpoint_slug: str,
        max_in_flight: int,
        lease_seconds: float,
        daily_cap_micro_usd: int | None = None,
    ) -> str:
        """Admit one call atomically, or raise ``BudgetRefusedError`` with a closed outcome.
        The daily allowance (D-095) always applies: ``daily_cap_micro_usd`` replaces the
        default (D-098: not a ceiling); a value outside 0..MAX_MICRO_USD refuses."""

        daily_cap = daily_cap_for(daily_cap_micro_usd)
        if daily_cap is None:
            raise BudgetRefusedError("refused_daily_cap", reservation.micro_usd)
        if not ENDPOINT_SLUG.fullmatch(endpoint_slug) or reservation.micro_usd <= 0:
            raise BudgetRefusedError("refused_reservation")

        def admit(connection: sqlite3.Connection) -> str:
            self._abandon_expired(connection)
            meta = self._meta(connection)
            refused = None
            open_calls = connection.execute(
                "SELECT COUNT(*) FROM calls WHERE state = 'open'"
            ).fetchone()[0]
            committed = (
                meta["baseline_micro_usd"]
                + meta["local_charged_micro_usd"]
                + meta["open_reserved_micro_usd"]
            )
            if meta["breaker_open"]:
                refused = "refused_breaker"
            elif open_calls >= max_in_flight:
                refused = "refused_busy"
            elif committed + reservation.micro_usd > meta["cap_micro_usd"]:
                refused = "refused_cap"
            else:
                settled, reserved, _ = _daily_committed(
                    connection, singapore_day_start_ms(self._now())
                )
                if settled + reserved + reservation.micro_usd > daily_cap:
                    refused = "refused_daily_cap"
            if refused is not None:
                # Commit any abandonment above, then refuse.
                return refused
            reservation_id = _hex32()
            now = self._now()
            connection.execute(
                "INSERT INTO calls (reservation_id, instance_id, created_at, lease_expires_at,"
                " state, reserved_micro_usd, prompt_bound_tokens, output_bound_tokens,"
                " requested_endpoint, verification, anomaly_bits)"
                " VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, 'unverified', 0)",
                (
                    reservation_id,
                    self.instance_id,
                    now,
                    now + int(lease_seconds * 1000),
                    reservation.micro_usd,
                    reservation.prompt_bound_tokens,
                    reservation.output_bound_tokens,
                    endpoint_slug,
                ),
            )
            connection.execute(
                "UPDATE ledger_meta SET open_reserved_micro_usd = open_reserved_micro_usd + ?",
                (reservation.micro_usd,),
            )
            return "admitted:" + reservation_id

        try:
            outcome: str = self._transaction(admit)
        except LedgerError as error:
            refusal = "refused_busy" if error.code == "LEDGER_BUSY" else "refused_ledger"
            raise BudgetRefusedError(refusal, reservation.micro_usd) from None
        except sqlite3.Error:
            raise BudgetRefusedError("refused_ledger", reservation.micro_usd) from None
        if not outcome.startswith("admitted:"):
            raise BudgetRefusedError(outcome, reservation.micro_usd)
        return outcome.removeprefix("admitted:")

    def settle(
        self,
        reservation_id: str,
        *,
        usage: ModelUsage | None,
        error_class: str | None,
        cancelled: bool = False,
    ) -> CallBudget:
        """Close one call once. Uncertainty is charged at the full reservation."""

        def close(connection: sqlite3.Connection) -> CallBudget:
            row = connection.execute(
                "SELECT id, state, reserved_micro_usd, charged_micro_usd, prompt_bound_tokens,"
                " output_bound_tokens FROM calls WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
            if row is None:
                raise LedgerError("INVALID_INPUT", "unknown reservation")
            call_id, state, reserved, charged, prompt_bound, output_bound = row
            if state != "open":  # already closed (for example abandoned): never count twice
                return CallBudget(
                    outcome=state, reserved_micro_usd=reserved, charged_micro_usd=charged
                )
            anomalies = set(usage.anomalies if usage is not None else ()) & MODEL_ANOMALIES
            trip: str | None = None
            verification = "unverified"
            if anomalies & ROUTING_ANOMALIES:
                verification, trip = "quarantined", "routing_anomaly"
            if usage is not None and usage.cost is not None:
                charge, new_state = micro_usd(usage.cost), "settled"
                if charge > MAX_MICRO_USD:
                    charge, new_state = reserved, "unsettled"
                    trip = trip or "usage_missing"
                if charge > reserved:
                    anomalies.add("cost_above_reservation")
                    trip = trip or "cost_above_reservation"
                if (usage.prompt_tokens or 0) > prompt_bound or (
                    usage.completion_tokens or 0
                ) > output_bound:
                    anomalies.add("token_bound_exceeded")
                    trip = trip or "token_bound_exceeded"
            else:
                charge, new_state = reserved, "unsettled"
                if error_class is None and not cancelled:
                    trip = trip or "usage_missing"
            if error_class in TRIP_ERROR_CLASSES:
                trip = trip or "provider_error"
            generation_ref = usage.generation_ref if usage is not None else None
            bits = sum(ANOMALY_BITS[code] for code in anomalies)
            connection.execute(
                "UPDATE calls SET state = ?, charged_micro_usd = ?, prompt_tokens = ?,"
                " completion_tokens = ?, reasoning_tokens = ?, cached_tokens = ?,"
                " generation_ref = ?, verification = ?, error_class = ?, anomaly_bits = ?,"
                " closed_at = ? WHERE id = ?",
                (
                    new_state,
                    charge,
                    usage.prompt_tokens if usage else None,
                    usage.completion_tokens if usage else None,
                    usage.reasoning_tokens if usage else None,
                    usage.cached_tokens if usage else None,
                    generation_ref,
                    verification,
                    error_class,
                    bits,
                    self._now(),
                    call_id,
                ),
            )
            connection.execute(
                "UPDATE ledger_meta SET open_reserved_micro_usd = open_reserved_micro_usd - ?,"
                " local_charged_micro_usd = local_charged_micro_usd + ?",
                (reserved, charge),
            )
            if trip is not None:
                self._open_breaker(connection, trip)
            return CallBudget(
                outcome=new_state, reserved_micro_usd=reserved, charged_micro_usd=charge
            )

        result: CallBudget = self._transaction(close)
        return result

    # -- Phase B serving-provider verification (D-092, proposed) --

    def closed_calls_after(self, call_id: int) -> list[ClosedCall]:
        """Closed calls with an id above ``call_id``, oldest first."""

        def read(connection: sqlite3.Connection) -> list[ClosedCall]:
            rows = connection.execute(
                "SELECT id, state, reserved_micro_usd, charged_micro_usd, prompt_tokens,"
                " completion_tokens, reasoning_tokens, generation_ref, verification,"
                " error_class, anomaly_bits FROM calls WHERE id > ? AND state != 'open'"
                " ORDER BY id",
                (call_id,),
            ).fetchall()
            return [ClosedCall(*row) for row in rows]

        result: list[ClosedCall] = self._transaction(read)
        return result

    def unverified_closed_calls(self) -> list[ClosedCall]:
        """Closed calls never verified (for example from an interrupted run), oldest first."""

        def read(connection: sqlite3.Connection) -> list[ClosedCall]:
            rows = connection.execute(
                "SELECT id, state, reserved_micro_usd, charged_micro_usd, prompt_tokens,"
                " completion_tokens, reasoning_tokens, generation_ref, verification,"
                " error_class, anomaly_bits FROM calls WHERE state != 'open'"
                " AND verification = 'unverified' ORDER BY id",
            ).fetchall()
            return [ClosedCall(*row) for row in rows]

        result: list[ClosedCall] = self._transaction(read)
        return result

    def last_call_id(self) -> int:
        def read(connection: sqlite3.Connection) -> int:
            value = connection.execute("SELECT COALESCE(MAX(id), 0) FROM calls").fetchone()[0]
            return int(value)

        result: int = self._transaction(read)
        return result

    def record_verification(self, call_id: int, *, verified: bool, breaker_code: str) -> None:
        """Move one closed, unverified call to ``verified`` or ``quarantined``. Quarantine
        opens the breaker with ``breaker_code`` (an existing code, so the schema is unchanged).
        A call is verified at most once; anything else is refused."""

        if breaker_code not in ("routing_anomaly", "reconcile_drift"):
            raise LedgerError("INVALID_INPUT", "unknown verification breaker code")

        def mark(connection: sqlite3.Connection) -> None:
            row = connection.execute(
                "SELECT state, verification FROM calls WHERE id = ?", (call_id,)
            ).fetchone()
            if row is None or row[0] == "open" or row[1] != "unverified":
                raise LedgerError("INVALID_INPUT", "the call cannot be verified")
            state = "verified" if verified else "quarantined"
            connection.execute("UPDATE calls SET verification = ? WHERE id = ?", (state, call_id))
            if not verified:
                self._open_breaker(connection, breaker_code)

        self._transaction(mark)

    # -- operator actions (scripts/budget_ledger.py) --

    def set_cap(
        self, cap_micro_usd: int, *, allow_raise: bool = False, confirm: int | None = None
    ) -> None:
        if type(cap_micro_usd) is not int or not 0 <= cap_micro_usd <= MAX_MICRO_USD:
            raise LedgerError("INVALID_INPUT", "the cap must be a micro-USD count")

        def change(connection: sqlite3.Connection) -> None:
            current = self._meta(connection)["cap_micro_usd"]
            if cap_micro_usd > current and not (allow_raise and confirm == cap_micro_usd):
                raise LedgerError(
                    "CAP_RAISE_REFUSED", "raising the cap needs explicit confirmation"
                )
            if cap_micro_usd != current:
                connection.execute("UPDATE ledger_meta SET cap_micro_usd = ?", (cap_micro_usd,))
                event = "cap_raised" if cap_micro_usd > current else "cap_lowered"
                self._event(connection, event, cap_micro_usd)

        self._transaction(change)

    def reconcile(
        self,
        provider_usage_micro_usd: int,
        *,
        release: bool = False,
        settle_lag_seconds: float = 600,
    ) -> int:
        """Anchor the ledger on the provider's cumulative usage of the key. Returns the drift
        (provider minus ledger). Only when no call is open and the last close is old enough;
        a provider value may never fall. Undercounts are adopted; over-counts are kept unless
        ``release`` is given."""

        provider = provider_usage_micro_usd
        if type(provider) is not int or not 0 <= provider <= MAX_MICRO_USD:
            raise LedgerError("INVALID_INPUT", "the provider usage must be a micro-USD count")
        if not isinstance(settle_lag_seconds, int | float) or not (
            0 <= settle_lag_seconds <= 86_400
        ):
            raise LedgerError("INVALID_INPUT", "the settle lag must be 0 to 86400 seconds")

        def anchor(connection: sqlite3.Connection) -> int:
            meta = self._meta(connection)
            open_calls, last_close, last_id = connection.execute(
                "SELECT SUM(state = 'open'), MAX(closed_at), MAX(id) FROM calls"
            ).fetchone()
            if open_calls:
                raise LedgerError("RECONCILE_REFUSED", "a call is still open")
            if last_close is not None and last_close > self._now() - int(settle_lag_seconds * 1000):
                raise LedgerError("RECONCILE_REFUSED", "the last call closed too recently")
            if provider < meta["last_provider_usage_micro_usd"]:
                raise LedgerError("RECONCILE_REFUSED", "provider usage cannot decrease")
            estimate: int = meta["baseline_micro_usd"] + meta["local_charged_micro_usd"]
            drift = provider - estimate
            baseline = provider if drift >= 0 or release else estimate
            connection.execute(
                "UPDATE ledger_meta SET baseline_micro_usd = ?, baseline_high_water_call_id = ?,"
                " local_charged_micro_usd = 0, last_provider_usage_micro_usd = ?,"
                " last_reconciled_at = ?",
                (baseline, last_id or meta["baseline_high_water_call_id"], provider, self._now()),
            )
            self._event(connection, "reconciled", provider)
            if drift < 0 and release:
                self._event(connection, "released", -drift)
            if drift > RECONCILE_TOLERANCE_MICRO_USD:
                self._open_breaker(connection, "reconcile_drift")
            return drift

        result: int = self._transaction(anchor)
        return result

    def reset_breaker(self, code: str) -> None:
        def reset(connection: sqlite3.Connection) -> None:
            meta = self._meta(connection)
            if not meta["breaker_open"] or meta["breaker_code"] != code:
                raise LedgerError("BREAKER_RESET_REFUSED", "the breaker is not open with that code")
            reconciled, opened = meta["last_reconciled_at"], meta["breaker_opened_at"]
            if reconciled is None or opened is None or reconciled <= opened:
                raise LedgerError("BREAKER_RESET_REFUSED", "reconcile before resetting the breaker")
            connection.execute(
                "UPDATE ledger_meta SET breaker_open = 0, breaker_code = NULL,"
                " breaker_opened_at = NULL"
            )
            self._event(connection, "breaker_reset", None, code)

        self._transaction(reset)


# --- the guarded model -------------------------------------------------------------------


class BudgetedChatModel:
    """Wraps the remote adapter: reserve before the request, settle once after it."""

    def __init__(
        self,
        inner: Any,
        ledger: BudgetLedger,
        *,
        max_in_flight: int,
        lease_seconds: float,
        daily_cap_micro_usd: int | None = None,
    ) -> None:
        self._inner = inner
        self._ledger = ledger
        self._max_in_flight = max_in_flight
        self._lease_seconds = lease_seconds
        self._daily_cap = daily_cap_micro_usd

    def __repr__(self) -> str:
        return f"BudgetedChatModel({self._inner!r})"

    @property
    def name(self) -> str:
        name: str = self._inner.name
        return name

    @property
    def profile_id(self) -> str:
        profile: str = self._inner.profile_id
        return profile

    @property
    def endpoint_slug(self) -> str:
        slug: str = self._inner.endpoint_slug
        return slug

    def _reserve(self, messages: list[dict[str, str]]) -> tuple[str, Reservation]:
        # A prompt the adapter would refuse is refused here, before anything is reserved.
        if message_bytes(messages) > self._inner.max_prompt_bytes:
            raise ModelCallError("prompt_too_large")
        reservation = reservation_for(messages, self._inner.endpoint, self._inner.max_tokens)
        reservation_id = self._ledger.reserve(
            reservation,
            endpoint_slug=self.endpoint_slug,
            max_in_flight=self._max_in_flight,
            lease_seconds=self._lease_seconds,
            daily_cap_micro_usd=self._daily_cap,
        )
        return reservation_id, reservation

    def _settle(
        self,
        reservation_id: str,
        reservation: Reservation,
        *,
        usage: ModelUsage | None,
        error_class: str | None,
        cancelled: bool = False,
    ) -> CallBudget:
        try:
            return self._ledger.settle(
                reservation_id, usage=usage, error_class=error_class, cancelled=cancelled
            )
        except (LedgerError, sqlite3.Error):
            # The row stays open, so the next admission waits for its lease and then charges
            # it in full; open the breaker now if the ledger can still be written.
            with suppress(LedgerError, sqlite3.Error):
                self._ledger.open_breaker("ledger_write_failed")
            return CallBudget(outcome="unsettled", reserved_micro_usd=reservation.micro_usd)

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        reservation_id, reservation = self._reserve(messages)
        try:
            answer: ModelAnswer = self._inner.complete(messages)
        except ModelCallError as error:
            budget = self._settle(
                reservation_id, reservation, usage=error.usage, error_class=error.error_class
            )
            raise ModelCallError(error.error_class, usage=error.usage, budget=budget) from None
        except BaseException:
            self._settle(reservation_id, reservation, usage=None, error_class=None, cancelled=True)
            raise
        budget = self._settle(reservation_id, reservation, usage=answer.usage, error_class=None)
        return replace(answer, budget=budget)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        reservation_id, reservation = await anyio.to_thread.run_sync(self._reserve, messages)
        settled = False
        try:
            async with aclosing(self._inner.stream(messages)) as source:
                async for piece in source:
                    if piece.finish_reason is None and piece.usage is None:
                        yield piece
                        continue
                    settle = partial(
                        self._settle,
                        reservation_id,
                        reservation,
                        usage=piece.usage,
                        error_class=None,
                    )
                    budget = await anyio.to_thread.run_sync(settle)
                    settled = True
                    yield replace(piece, budget=budget)
        except ModelCallError as error:
            settle = partial(
                self._settle,
                reservation_id,
                reservation,
                usage=error.usage,
                error_class=error.error_class,
            )
            budget = await anyio.to_thread.run_sync(settle)
            settled = True
            raise ModelCallError(error.error_class, usage=error.usage, budget=budget) from None
        finally:
            if not settled:
                # Cancelled or interrupted: charge the full reservation, even while cancelling.
                settle = partial(
                    self._settle,
                    reservation_id,
                    reservation,
                    usage=None,
                    error_class=None,
                    cancelled=True,
                )
                with anyio.CancelScope(shield=True):
                    await anyio.to_thread.run_sync(settle)

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None
