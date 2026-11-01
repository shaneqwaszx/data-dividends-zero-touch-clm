"""Claude API model benchmark (evaluation only; synthetic Phase B questions; owner-authorised).

The benchmark asks the 17 reviewed Phase B questions through the real service, exactly as the
GPT-OSS runs did: the harness serves only the saved synthetic Garden fixtures from its mock
CLM backend, and every answer passes the unchanged prompt builder, exact-line guard and
deterministic fallbacks. Only the chat model differs: ``ClaudeBenchModel`` calls the native
Anthropic Messages API. Nothing here is a runtime profile: the service never imports this
package, and no Claude model is selectable in AI Models.

Fail-closed controls, all before the first byte is sent:

- approved models: code records with prices read from the public pricing page on the
  evidence date; settings cannot add a model, URL or price;
- destination: ``https://api.anthropic.com`` pinned, no proxy, no environment base URL or
  auth token, no SDK retries, no server-side model fallback (a refusal is recorded as a
  failure, never answered by another model);
- credential: ``AI_ASSISTANT_ANTHROPIC_API_KEY`` from the process environment only, read
  lazily per call, never logged, stored or put in an artifact;
- prompt: every message passes the D-094 synthetic text check, and the exact prompt was
  approved in the offline ``prompts`` dry run and counted in the free preflight;
- money: a local SQLite ledger of its own (never the OpenRouter ledger) reserves the
  worst case (counted input at 1.25x plus every allowed output token) inside one
  ``BEGIN IMMEDIATE`` transaction, against a run cap, a per-call ceiling and a call limit;
  one call at a time; anything that cannot be settled from reported usage is charged its
  full reservation; a model, tier, geography or cost discrepancy opens the breaker, which
  refuses every later call.
"""

import hashlib
import importlib
import json
import os
import re
import sqlite3
import sys
import time
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from contextlib import closing, suppress
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

import anyio

from ai_assistant.llm import (
    CallBudget,
    LlmUnavailableError,
    ModelAnswer,
    ModelCallError,
    ModelUsage,
    Piece,
)
from ai_assistant.synthetic_boundary import check_messages

API_BASE_URL = "https://api.anthropic.com"
KEY_VARIABLE = "AI_ASSISTANT_ANTHROPIC_API_KEY"
# Anthropic API keys: the older sk-ant-api03-... and the Console's sk-ant-usr-... (seen 2026-10-29).
_KEY_SHAPE = re.compile(r"sk-ant-(?:api\d{2}|usr)-[A-Za-z0-9_-]{20,300}")
# Where scripts/benchmark_claude.py installs the SDK (git-ignored); appended, never prepended,
# so the service's own pinned packages always win.
SDK_DIR = Path(__file__).resolve().parents[1] / "data" / "anthropic-sdk"
SDK_VERSION = "2.3.0"

# Owner limits for this benchmark (US$6 in all, at most US$0.10 reserved per call).
RUN_CAP_CEILING_MICRO_USD = 6_000_000
PER_CALL_CEILING_MICRO_USD = 100_000
CALL_LIMIT_CEILING = 51
# Anthropic bills prompts above this length at a different rate on Haiku 5.5; refused here.
MAX_INPUT_TOKENS = 100_000
TIMEOUT_SECONDS = 90.0
# An anomalous call (fast speed 2x, US-only geography 1.1x, Haiku's long-prompt card 5x) is
# charged at least this multiple of its standard-price cost.
ANOMALY_PRICE_MULTIPLIER = 5
EFFORTS = ("low", "medium", "high")
_MILLION = Decimal(1_000_000)
_MICRO = Decimal("0.000001")


@dataclass(frozen=True)
class ClaudeModel:
    """One approved Claude API model, with its published standard (global) prices."""

    model_id: str
    label: str
    role: str
    input_usd_per_mtok: Decimal
    output_usd_per_mtok: Decimal
    cache_read_usd_per_mtok: Decimal
    # The ways this model accepts to turn thinking off (empty: it cannot be turned off).
    thinking_off: str | None
    evidence: str


_EVIDENCE = "platform.claude.com/docs/en/about-claude/pricing and models/overview, read 2026-10-29"
APPROVED_MODELS: Mapping[str, ClaudeModel] = MappingProxyType(
    {
        "haiku": ClaudeModel(
            "claude-haiku-5-5",
            "Claude Haiku 5.5",
            "latency candidate",
            Decimal("0.10"),
            Decimal("0.50"),
            Decimal("0.01"),
            "disabled",
            _EVIDENCE + " (prompts up to 100,000 tokens)",
        ),
        "sonnet": ClaudeModel(
            "claude-sonnet-5-5",
            "Claude Sonnet 5.5",
            "balanced candidate",
            Decimal("2"),
            Decimal("10"),
            Decimal("0.10"),
            "between_tools",
            _EVIDENCE,
        ),
        "opus": ClaudeModel(
            "claude-opus-5-5",
            "Claude Opus 5.5",
            "quality reference",
            Decimal("4"),
            Decimal("20"),
            Decimal("0.20"),
            None,
            _EVIDENCE,
        ),
    }
)


class BenchConfigError(ValueError):
    """A benchmark setting is refused (the message names the setting, never a secret)."""


@dataclass(frozen=True)
class BenchConfig:
    """What one model is asked with. Everything sent besides the messages comes from here."""

    alias: str
    effort: str = "medium"
    thinking: str = "adaptive"
    max_tokens: int = 3000

    def __post_init__(self) -> None:
        if self.alias not in APPROVED_MODELS:
            raise BenchConfigError("model is not an approved benchmark model")
        if self.effort not in EFFORTS:
            raise BenchConfigError("effort must be low, medium or high")
        if self.thinking not in ("adaptive", "off"):
            raise BenchConfigError("thinking must be adaptive or off")
        if self.thinking == "off" and self.model.thinking_off is None:
            raise BenchConfigError(f"{self.model.label} cannot turn thinking off")
        if not 256 <= self.max_tokens <= 4000:
            raise BenchConfigError("max_tokens must be 256 to 4000")

    @property
    def model(self) -> ClaudeModel:
        return APPROVED_MODELS[self.alias]

    def request_fields(self) -> dict[str, Any]:
        """The request fields besides the model, system and messages (no sampling fields,
        tools, metadata, fallbacks, service tier, speed or inference geography)."""

        if self.thinking == "off":
            thinking: dict[str, str] = {"type": str(self.model.thinking_off)}
        else:
            thinking = {"type": "adaptive"}
        return {
            "max_tokens": self.max_tokens,
            "thinking": thinking,
            "output_config": {"effort": self.effort},
        }

    def describe(self) -> dict[str, Any]:
        return {
            "alias": self.alias,
            "model_id": self.model.model_id,
            "effort": self.effort,
            "thinking": self.thinking,
            "max_tokens": self.max_tokens,
            "request_fields": self.request_fields(),
            "base_url": API_BASE_URL,
            "sdk": f"anthropic {SDK_VERSION}",
            "retries": 0,
            "server_side_fallback": "off",
            "timeout_seconds": TIMEOUT_SECONDS,
        }

    def fingerprint(self) -> str:
        text = json.dumps(self.describe(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --- money ---------------------------------------------------------------------------------


def to_micro(usd: Decimal) -> int:
    """USD to whole micro-USD, rounded up (never under-counts)."""

    return int((usd / _MICRO).to_integral_value(rounding=ROUND_CEILING))


def reservation_micro(model: ClaudeModel, input_tokens: int, max_tokens: int) -> int:
    """Worst case for one call: every counted input token as a cache write (1.25x), which
    this benchmark never requests, plus every allowed output token (thinking included)."""

    usd = (
        Decimal(input_tokens) * model.input_usd_per_mtok * Decimal("1.25")
        + Decimal(max_tokens) * model.output_usd_per_mtok
    ) / _MILLION
    return to_micro(usd)


@dataclass(frozen=True)
class Usage:
    """Token counts the API reported for one call, and the routing fields that change price."""

    input_tokens: int
    output_tokens: int
    cache_creation_5m: int = 0
    cache_creation_1h: int = 0
    cache_read: int = 0
    service_tier: str | None = None
    inference_geo: str | None = None
    speed: str | None = None

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens + self.cache_creation_5m + self.cache_creation_1h + self.cache_read


def cost_micro(model: ClaudeModel, usage: Usage) -> int:
    usd = (
        Decimal(usage.input_tokens) * model.input_usd_per_mtok
        + Decimal(usage.cache_creation_5m) * model.input_usd_per_mtok * Decimal("1.25")
        + Decimal(usage.cache_creation_1h) * model.input_usd_per_mtok * Decimal("2")
        + Decimal(usage.cache_read) * model.cache_read_usd_per_mtok
        + Decimal(usage.output_tokens) * model.output_usd_per_mtok
    ) / _MILLION
    return to_micro(usd)


def price_anomalies(usage: Usage) -> list[str]:
    """Reported usage that the standard price card does not cover, or that this benchmark
    never requests (prompt caching), or that cannot be priced (no input tokens)."""

    found = []
    if usage.input_tokens <= 0:
        found.append("usage_missing")
    if usage.cache_creation_5m or usage.cache_creation_1h or usage.cache_read:
        found.append("unrequested_cache")
    found += routing_anomalies(usage)
    if usage.prompt_tokens > MAX_INPUT_TOKENS:
        found.append("long_prompt")
    return found


def routing_anomalies(usage: Usage) -> list[str]:
    """A tier, geography or speed that the standard price card does not cover."""

    found = []
    if usage.service_tier not in (None, "standard"):
        found.append("service_tier")
    if usage.inference_geo not in (None, "global", "not_available"):
        found.append("inference_geo")
    if usage.speed not in (None, "standard"):
        found.append("speed")
    return found


# --- prompts -------------------------------------------------------------------------------


class UnsupportedPromptError(ValueError):
    """The service's messages cannot be sent without changing their roles or order."""


def to_anthropic(
    messages: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """The service's leading system messages become the top-level ``system`` text blocks, in
    order and unchanged; the rest must be a user/assistant conversation that starts and ends
    with the user. A system message after the conversation has started (the service's
    knowledge and topic messages after history) has no faithful place in the Messages API,
    so it is refused rather than moved or re-labelled (none of the 17 questions has history)."""

    system: list[dict[str, str]] = []
    index = 0
    while index < len(messages) and messages[index].get("role") == "system":
        system.append({"type": "text", "text": str(messages[index].get("content") or "")})
        index += 1
    rest = [dict(message) for message in messages[index:]]
    if not system or not rest:
        raise UnsupportedPromptError("no system prompt or no question")
    if any(message.get("role") not in ("user", "assistant") for message in rest):
        raise UnsupportedPromptError("system message after the conversation started")
    if rest[0]["role"] != "user" or rest[-1]["role"] != "user":
        raise UnsupportedPromptError("the conversation must start and end with the user")
    if any(a["role"] == b["role"] for a, b in zip(rest, rest[1:], strict=False)):
        raise UnsupportedPromptError("turns must alternate")
    return system, [{"role": m["role"], "content": str(m.get("content") or "")} for m in rest]


def prompt_sha(messages: Sequence[Mapping[str, str]]) -> str:
    """The whole outgoing prompt (every message, in order), hashed."""

    text = json.dumps([dict(m) for m in messages], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- ledger --------------------------------------------------------------------------------


class LedgerRefusedError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LedgerStatus:
    cap_micro_usd: int
    per_call_micro_usd: int
    call_limit: int
    calls: int
    open_calls: int
    committed_micro_usd: int
    settled_micro_usd: int
    conservative_micro_usd: int
    breaker_open: bool
    breaker_code: str | None
    provider_reported_micro_usd: int | None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cap_micro_usd INTEGER NOT NULL CHECK (cap_micro_usd > 0 AND cap_micro_usd <= 6000000),
    per_call_micro_usd INTEGER NOT NULL
        CHECK (per_call_micro_usd > 0 AND per_call_micro_usd <= 100000),
    call_limit INTEGER NOT NULL CHECK (call_limit > 0),
    created_at TEXT NOT NULL,
    breaker_code TEXT,
    provider_reported_micro_usd INTEGER
);
CREATE TABLE IF NOT EXISTS calls (
    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_label TEXT NOT NULL,
    turn TEXT NOT NULL,
    model_id TEXT NOT NULL,
    config_fingerprint TEXT NOT NULL,
    prompt_sha TEXT NOT NULL,
    reserved_micro_usd INTEGER NOT NULL CHECK (reserved_micro_usd > 0),
    state TEXT NOT NULL CHECK (state IN ('open', 'settled', 'charged_reservation')),
    charged_micro_usd INTEGER,
    response_model TEXT,
    message_id TEXT,
    stop_reason TEXT,
    error_class TEXT,
    usage_json TEXT,
    timings_json TEXT,
    anomalies TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class ClaudeLedger:
    """The benchmark's own spending ledger (one SQLite file; never the OpenRouter ledger)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        if not self.path.exists():
            raise LedgerRefusedError("ledger_missing")
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    @classmethod
    def create(
        cls, path: Path, *, cap_micro_usd: int, per_call_micro_usd: int, call_limit: int
    ) -> "ClaudeLedger":
        if path.exists():
            raise LedgerRefusedError("ledger_exists")
        if not 0 < cap_micro_usd <= RUN_CAP_CEILING_MICRO_USD:
            raise LedgerRefusedError("cap_out_of_range")
        if not 0 < per_call_micro_usd <= PER_CALL_CEILING_MICRO_USD:
            raise LedgerRefusedError("per_call_out_of_range")
        if not 0 < call_limit <= CALL_LIMIT_CEILING:
            raise LedgerRefusedError("call_limit_out_of_range")
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, isolation_level=None)) as db:
            db.executescript(_SCHEMA)
            db.execute(
                "INSERT INTO meta (id, cap_micro_usd, per_call_micro_usd, call_limit, created_at)"
                " VALUES (1, ?, ?, ?, ?)",
                (cap_micro_usd, per_call_micro_usd, call_limit, _now()),
            )
            db.execute(
                "INSERT INTO events (at, kind, detail) VALUES (?, 'created', ?)",
                (_now(), f"cap {cap_micro_usd} per_call {per_call_micro_usd} calls {call_limit}"),
            )
        return cls(path)

    def status(self) -> LedgerStatus:
        with closing(self._connect()) as db:
            meta = db.execute("SELECT * FROM meta WHERE id = 1").fetchone()
            if meta is None:
                raise LedgerRefusedError("ledger_unreadable")
            row = db.execute(
                "SELECT COUNT(*) AS n,"
                " COALESCE(SUM(state = 'open'), 0) AS open_calls,"
                " COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd"
                "  ELSE charged_micro_usd END), 0) AS committed,"
                " COALESCE(SUM(CASE WHEN state = 'settled' THEN charged_micro_usd END), 0)"
                "  AS settled,"
                " COALESCE(SUM(CASE WHEN state = 'charged_reservation' THEN charged_micro_usd"
                "  END), 0) AS conservative"
                " FROM calls"
            ).fetchone()
        return LedgerStatus(
            cap_micro_usd=int(meta["cap_micro_usd"]),
            per_call_micro_usd=int(meta["per_call_micro_usd"]),
            call_limit=int(meta["call_limit"]),
            calls=int(row["n"]),
            open_calls=int(row["open_calls"]),
            committed_micro_usd=int(row["committed"]),
            settled_micro_usd=int(row["settled"]),
            conservative_micro_usd=int(row["conservative"]),
            breaker_open=meta["breaker_code"] is not None,
            breaker_code=meta["breaker_code"],
            provider_reported_micro_usd=meta["provider_reported_micro_usd"],
        )

    def reserve(
        self,
        *,
        run_label: str,
        turn: str,
        model_id: str,
        config_fingerprint: str,
        prompt: str,
        reserved_micro_usd: int,
    ) -> int:
        """Admit one call, atomically, or refuse it (closed codes)."""

        if reserved_micro_usd <= 0:
            raise LedgerRefusedError("reservation_invalid")
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                meta = db.execute("SELECT * FROM meta WHERE id = 1").fetchone()
                if meta is None:
                    raise LedgerRefusedError("ledger_unreadable")
                if meta["breaker_code"] is not None:
                    raise LedgerRefusedError("breaker_open")
                if reserved_micro_usd > int(meta["per_call_micro_usd"]):
                    raise LedgerRefusedError("per_call_ceiling")
                row = db.execute(
                    "SELECT COUNT(*) AS n, COALESCE(SUM(state = 'open'), 0) AS open_calls,"
                    " COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd"
                    "  ELSE charged_micro_usd END), 0) AS committed FROM calls"
                ).fetchone()
                if int(row["open_calls"]):
                    raise LedgerRefusedError("call_open")
                if int(row["n"]) >= int(meta["call_limit"]):
                    raise LedgerRefusedError("call_limit")
                if int(row["committed"]) + reserved_micro_usd > int(meta["cap_micro_usd"]):
                    raise LedgerRefusedError("run_cap")
                cursor = db.execute(
                    "INSERT INTO calls (run_label, turn, model_id, config_fingerprint,"
                    " prompt_sha, reserved_micro_usd, state, started_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, 'open', ?)",
                    (
                        run_label,
                        turn,
                        model_id,
                        config_fingerprint,
                        prompt,
                        reserved_micro_usd,
                        _now(),
                    ),
                )
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return int(cursor.lastrowid or 0)

    def close_call(
        self,
        call_id: int,
        *,
        charged_micro_usd: int | None,
        response_model: str | None,
        message_id: str | None,
        stop_reason: str | None,
        error_class: str | None,
        usage: Usage | None,
        timings: Mapping[str, int | None],
        anomalies: Sequence[str],
    ) -> int:
        """Close an open call. Without a reported cost the full reservation is charged. Any
        anomaly, or a cost above the reservation, opens the breaker; an anomalous call is
        charged conservatively (the larger of its reservation and its standard-price cost
        times ``ANOMALY_PRICE_MULTIPLIER``), never at the standard price. Returns the charge."""

        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                call = db.execute(
                    "SELECT * FROM calls WHERE call_id = ? AND state = 'open'", (call_id,)
                ).fetchone()
                if call is None:
                    raise LedgerRefusedError("call_not_open")
                reserved = int(call["reserved_micro_usd"])
                found = list(anomalies)
                if charged_micro_usd is not None and charged_micro_usd > reserved:
                    found.append("cost_above_reservation")
                if charged_micro_usd is None:
                    state, charge = "charged_reservation", reserved
                elif found:
                    state = "charged_reservation"
                    charge = max(reserved, charged_micro_usd * ANOMALY_PRICE_MULTIPLIER)
                else:
                    state, charge = "settled", charged_micro_usd
                db.execute(
                    "UPDATE calls SET state = ?, charged_micro_usd = ?, response_model = ?,"
                    " message_id = ?, stop_reason = ?, error_class = ?, usage_json = ?,"
                    " timings_json = ?, anomalies = ?, ended_at = ? WHERE call_id = ?",
                    (
                        state,
                        charge,
                        response_model,
                        message_id,
                        stop_reason,
                        error_class,
                        json.dumps(asdict(usage)) if usage else None,
                        json.dumps(dict(timings)),
                        ",".join(found) or None,
                        _now(),
                        call_id,
                    ),
                )
                if found:
                    self._open_breaker(db, found[0], f"call {call_id}: {','.join(found)}")
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return charge

    @staticmethod
    def _open_breaker(db: sqlite3.Connection, code: str, detail: str) -> None:
        db.execute("UPDATE meta SET breaker_code = COALESCE(breaker_code, ?) WHERE id = 1", (code,))
        db.execute(
            "INSERT INTO events (at, kind, detail) VALUES (?, 'breaker_opened', ?)",
            (_now(), f"{code}: {detail}"),
        )

    def open_breaker(self, code: str, detail: str) -> None:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                self._open_breaker(db, code, detail)
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise

    def record_provider_usage(self, reported_micro_usd: int, tolerance_micro_usd: int) -> str:
        """The owner's reading of the Console's usage for this ledger's calls (US$), compared
        with the ledger: a provider figure above what the ledger committed opens the breaker.
        Unrelated usage on the same key must be left out of the figure, not reconciled."""

        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                committed, settled = db.execute(
                    "SELECT COALESCE(SUM(CASE WHEN state = 'open' THEN reserved_micro_usd"
                    "  ELSE charged_micro_usd END), 0),"
                    " COALESCE(SUM(CASE WHEN state = 'settled' THEN charged_micro_usd END), 0)"
                    " FROM calls"
                ).fetchone()
                db.execute(
                    "UPDATE meta SET provider_reported_micro_usd = ? WHERE id = 1",
                    (reported_micro_usd,),
                )
                verdict = (
                    "within_ledger"
                    if reported_micro_usd <= int(committed) + tolerance_micro_usd
                    else "above_ledger"
                )
                db.execute(
                    "INSERT INTO events (at, kind, detail) VALUES (?, 'provider_usage', ?)",
                    (
                        _now(),
                        f"{verdict}: reported {reported_micro_usd} ledger {committed}"
                        f" settled {settled}",
                    ),
                )
                if verdict == "above_ledger":
                    self._open_breaker(db, "provider_discrepancy", "console usage above ledger")
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        return verdict

    def calls(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM calls ORDER BY call_id")]

    def events(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as db:
            return [dict(row) for row in db.execute("SELECT * FROM events ORDER BY event_id")]


# --- SDK and credential --------------------------------------------------------------------


def load_sdk() -> Any:
    """The official Anthropic SDK: installed in the environment, or in ``SDK_DIR``."""

    try:
        return importlib.import_module("anthropic")
    except ImportError:
        if str(SDK_DIR) not in sys.path and SDK_DIR.is_dir():
            sys.path.append(str(SDK_DIR))
        return importlib.import_module("anthropic")


def read_key(environ: Mapping[str, str]) -> str:
    """The benchmark key, from its own variable only (never ``ANTHROPIC_API_KEY``, which
    other local tools also use). A missing or malformed value refuses the call."""

    key = environ.get(KEY_VARIABLE, "").strip()
    if not _KEY_SHAPE.fullmatch(key):
        raise LedgerRefusedError("credential_missing_or_malformed")
    return key


def key_problem(environ: Mapping[str, str]) -> str | None:
    """Why the benchmark key is refused, without any part of its value: the public prefix
    family, the length, and whether it holds whitespace or other characters."""

    raw = environ.get(KEY_VARIABLE, "")
    key = raw.strip()
    if not key:
        return "missing"
    if _KEY_SHAPE.fullmatch(key):
        return None
    if key.startswith("sk-ant-admin"):
        family = "an Admin API key (sk-ant-admin...), not an API key"
    elif key.startswith("sk-ant-oat"):
        family = "an OAuth token (sk-ant-oat...), not an API key"
    elif key.startswith("sk-ant-sid"):
        family = "a claude.ai session value (sk-ant-sid...), never an API key: do not use it"
    elif key.startswith("sk-or-"):
        family = "an OpenRouter key (sk-or-...), not an Anthropic key"
    elif re.match(r"sk-ant-(?:api\d{2}|usr)-", key):
        family = "API-key prefix as expected"
    else:
        # Only where the public marker sits, never what surrounds it.
        marker = key.find("ant-")
        family = (
            "not an sk-ant-api..- or sk-ant-usr- API-key prefix; starts with 'sk-' "
            f"{key.startswith('sk-')}; public marker 'ant-' "
            + (f"at position {marker} (expected 3)" if marker >= 0 else "absent")
        )
    whitespace = any(char.isspace() for char in key)
    other = sum(1 for char in key if not (char.isalnum() and char.isascii()) and char not in "_-")
    return (
        f"{family}; {len(key)} characters after trimming; inner whitespace {whitespace};"
        f" {other} character(s) outside letters, digits, '_' and '-'"
    )


# SDK settings read from the process environment that an explicit argument cannot cancel:
# extra request headers, and debug logging of requests.
SDK_ENVIRONMENT_REFUSED = ("ANTHROPIC_CUSTOM_HEADERS", "ANTHROPIC_LOG")


def sdk_environment_refusal(environ: Mapping[str, str]) -> str | None:
    if any(environ.get(name) for name in SDK_ENVIRONMENT_REFUSED):
        return "sdk_environment"
    return None


def _client_options(transport: Any | None, *, asynchronous: bool) -> dict[str, Any]:
    """HTTP client options. A transport is always given explicitly: without one the SDK's
    default clients mount proxies from ``getproxies()`` (environment variables and, on
    Windows, the system proxy) even with ``trust_env=False``. The default here is a direct
    transport that reads no proxy setting."""

    if sdk_environment_refusal(os.environ) is not None:
        raise LedgerRefusedError("sdk_environment")
    if transport is None:
        load_sdk()
        httpx2 = importlib.import_module("httpx2")
        kind = httpx2.AsyncHTTPTransport if asynchronous else httpx2.HTTPTransport
        transport = kind(trust_env=False)
    return {"trust_env": False, "follow_redirects": False, "transport": transport}


def make_async_client(key: str, transport: Any | None = None) -> Any:
    """A client pinned to the public API: explicit base URL and key (the SDK then consults
    no environment credential, base URL or profile), a direct transport (no proxy), no
    retries, no tracing export."""

    sdk = load_sdk()
    return sdk.AsyncAnthropic(
        api_key=key,
        base_url=API_BASE_URL,
        max_retries=0,
        timeout=TIMEOUT_SECONDS,
        open_telemetry=False,
        http_client=sdk.DefaultAsyncHttpxClient(**_client_options(transport, asynchronous=True)),
    )


def make_client(key: str, transport: Any | None = None) -> Any:
    sdk = load_sdk()
    return sdk.Anthropic(
        api_key=key,
        base_url=API_BASE_URL,
        max_retries=0,
        timeout=TIMEOUT_SECONDS,
        open_telemetry=False,
        http_client=sdk.DefaultHttpxClient(**_client_options(transport, asynchronous=False)),
    )


def error_class(error: BaseException) -> tuple[str, bool]:
    """(closed error class, whether it must stop the run)."""

    sdk = load_sdk()
    table: list[tuple[str, str, bool]] = [
        ("AuthenticationError", "auth", True),
        ("PermissionDeniedError", "forbidden", True),
        ("NotFoundError", "not_allowed", True),
        ("RequestTooLargeError", "prompt_too_large", True),
        ("BadRequestError", "bad_request", True),
        ("UnprocessableEntityError", "bad_request", True),
        ("RateLimitError", "rate_limited", False),
        ("APITimeoutError", "timeout", False),
        ("APIConnectionError", "transport", False),
        ("APIStatusError", "upstream", False),
    ]
    for name, code, stop in table:
        kind = getattr(sdk, name, None)
        if isinstance(kind, type) and isinstance(error, kind):
            return code, stop
    if isinstance(error, TimeoutError):
        return "timeout", False
    return "protocol", True


def usage_of(raw: Any) -> Usage:
    def count(name: str) -> int:
        value = getattr(raw, name, None)
        return int(value) if isinstance(value, int) and value >= 0 else 0

    creation = getattr(raw, "cache_creation", None)
    five = getattr(creation, "ephemeral_5m_input_tokens", None) if creation else None
    hour = getattr(creation, "ephemeral_1h_input_tokens", None) if creation else None
    total_creation = count("cache_creation_input_tokens")
    if not isinstance(five, int) or not isinstance(hour, int):
        five, hour = total_creation, 0

    def text(name: str) -> str | None:
        value = getattr(raw, name, None)
        return value if isinstance(value, str) else None

    return Usage(
        input_tokens=count("input_tokens"),
        output_tokens=count("output_tokens"),
        cache_creation_5m=five,
        cache_creation_1h=hour,
        cache_read=count("cache_read_input_tokens"),
        service_tier=text("service_tier"),
        inference_geo=text("inference_geo"),
        speed=text("speed"),
    )


# --- the model -----------------------------------------------------------------------------


@dataclass
class CallRecord:
    """Content-free facts about one call (also kept in the ledger)."""

    turn: str
    model_id: str
    call_id: int | None = None
    refused: str | None = None
    response_model: str | None = None
    stop_reason: str | None = None
    error_class: str | None = None
    reserved_micro_usd: int = 0
    charged_micro_usd: int | None = None
    usage: dict[str, Any] | None = None
    timings_ms: dict[str, int | None] = field(default_factory=dict)
    anomalies: list[str] = field(default_factory=list)


class ClaudeBenchModel:
    """A ``ChatModel`` over the Anthropic Messages API, for the harness only."""

    def __init__(
        self,
        config: BenchConfig,
        ledger: ClaudeLedger,
        *,
        counted: Mapping[str, int],
        run_label: str,
        environ: Mapping[str, str],
        transport: Any | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # ``counted``: prompt sha -> input tokens the preflight counted for this model.
        self._config = config
        self._ledger = ledger
        self._counted = dict(counted)
        self._run_label = run_label
        self._environ = environ
        self._transport = transport
        self._clock = clock
        self._turn = ""
        self.records: list[CallRecord] = []

    @property
    def name(self) -> str:
        return self._config.model.model_id

    def begin(self, key: str, rep: int) -> None:
        self._turn = f"{key}@{rep}"

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        raise LlmUnavailableError("the benchmark model only streams")

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None

    def _refuse(self, record: CallRecord, code: str, error: str) -> ModelCallError:
        """A refusal before anything is sent is a privacy or spending-control failure: it
        opens the breaker, so the run stops instead of asking the remaining questions."""

        record.refused = code
        self.records.append(record)
        # Without a usable ledger every later reservation is refused anyway.
        if code != "breaker_open":
            with suppress(LedgerRefusedError):
                self._ledger.open_breaker(f"refused_{code}", f"{record.turn} {record.model_id}")
        return ModelCallError(error)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        config = self._config
        model = config.model
        record = CallRecord(turn=self._turn, model_id=model.model_id)
        # Privacy first: the D-094 synthetic text check, then the dry-run approval.
        if check_messages(messages) is not None:
            raise self._refuse(record, "synthetic_text", "not_allowed")
        try:
            system, conversation = to_anthropic(messages)
        except UnsupportedPromptError:
            raise self._refuse(record, "prompt_shape", "not_allowed") from None
        sha = prompt_sha(messages)
        counted = self._counted.get(sha)
        if counted is None:
            raise self._refuse(record, "prompt_not_approved", "not_allowed")
        if counted > MAX_INPUT_TOKENS:
            raise self._refuse(record, "long_prompt", "prompt_too_large")
        reserved = reservation_micro(model, counted, config.max_tokens)
        record.reserved_micro_usd = reserved
        if sdk_environment_refusal(os.environ) is not None:
            raise self._refuse(record, "sdk_environment", "not_allowed")
        try:
            key = read_key(self._environ)
            call_id = self._ledger.reserve(
                run_label=self._run_label,
                turn=self._turn,
                model_id=model.model_id,
                config_fingerprint=config.fingerprint(),
                prompt=sha,
                reserved_micro_usd=reserved,
            )
        except LedgerRefusedError as refused:
            raise self._refuse(record, refused.code, "budget_refused") from None
        record.call_id = call_id
        self.records.append(record)

        start = self._clock()
        timings: dict[str, int | None] = {
            "message_start": None,
            "first_block": None,
            "first_text": None,
            "total": None,
        }

        def mark(name: str) -> None:
            if timings[name] is None:
                timings[name] = int((self._clock() - start) * 1000)

        usage: Usage | None = None
        # The tier, geography and speed as reported at message_start (the final usage may not
        # repeat them); both are checked.
        opening_usage: Usage | None = None
        stop_reason: str | None = None
        message_id: str | None = None
        failure: str | None = None
        stop_run = False
        # One deadline for the whole call, applied to each await separately: a timeout scope
        # must never be open across a ``yield`` (its cancellation would land in the caller).
        deadline = time.monotonic() + TIMEOUT_SECONDS

        def remaining() -> float:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError
            return left

        try:
            client = make_async_client(key, self._transport)
            manager: Any = None
            try:
                with anyio.fail_after(remaining()):
                    opening = client.messages.stream(
                        model=model.model_id,
                        system=system,
                        messages=conversation,
                        **config.request_fields(),
                    )
                    stream = await opening.__aenter__()
                    manager = opening
                events = stream.__aiter__()
                while True:
                    with anyio.fail_after(remaining()):
                        try:
                            event = await events.__anext__()
                        except StopAsyncIteration:
                            break
                    kind = getattr(event, "type", "")
                    if kind == "message_start":
                        mark("message_start")
                        message = event.message
                        record.response_model = str(getattr(message, "model", ""))
                        message_id = str(getattr(message, "id", "")) or None
                        opening_usage = usage_of(getattr(message, "usage", None))
                        if record.response_model != model.model_id:
                            record.anomalies.append("model_mismatch")
                            raise ModelCallError("protocol")
                    elif kind == "content_block_start":
                        mark("first_block")
                    elif kind == "text" and event.text:
                        mark("first_text")
                        yield Piece(event.text)
                with anyio.fail_after(remaining()):
                    final = await stream.get_final_message()
            finally:
                # Release the response and the connection whatever happened (bounded).
                with anyio.move_on_after(5, shield=True):
                    if manager is not None:
                        await manager.__aexit__(None, None, None)
                    await client.close()
            mark("total")
            usage = usage_of(final.usage)
            stop_reason = final.stop_reason
            found = price_anomalies(usage)
            if opening_usage is not None:
                found += routing_anomalies(opening_usage)
            record.anomalies.extend(dict.fromkeys(found))
            if str(final.model) != model.model_id and "model_mismatch" not in record.anomalies:
                record.anomalies.append("model_mismatch")
        except ModelCallError as error:
            failure, stop_run = error.error_class, True
        except Exception as error:  # noqa: BLE001 - mapped to a closed class
            failure, stop_run = error_class(error)
        finally:
            mark("total")
            charged = None
            if failure is None and usage is not None:
                charged = cost_micro(model, usage)
            elif failure is None:
                # Closed early (the reply was abandoned): what it cost is not known.
                failure = "upstream_midstream"
            if stop_run and not record.anomalies:
                record.anomalies.append(f"stop_{failure}")
            record.error_class = failure
            record.stop_reason = stop_reason
            record.usage = asdict(usage) if usage else None
            record.timings_ms = dict(timings)
            with anyio.CancelScope(shield=True):
                record.charged_micro_usd = self._ledger.close_call(
                    call_id,
                    charged_micro_usd=charged,
                    response_model=record.response_model,
                    message_id=message_id,
                    stop_reason=stop_reason,
                    error_class=failure,
                    usage=usage,
                    timings=timings,
                    anomalies=record.anomalies,
                )
        if failure is not None:
            raise ModelCallError(failure)
        if stop_reason == "refusal":
            raise ModelCallError("content_filter")
        if stop_reason not in ("end_turn", "max_tokens"):
            raise ModelCallError("protocol")
        cut_short = stop_reason == "max_tokens"
        assert usage is not None
        yield Piece(
            cut_short=cut_short,
            usage=ModelUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.output_tokens,
                cached_tokens=usage.cache_read,
                cost=Decimal(record.charged_micro_usd or 0) * _MICRO,
            ),
            finish_reason="length" if cut_short else "stop",
            budget=CallBudget(
                "settled", reserved_micro_usd=reserved, charged_micro_usd=record.charged_micro_usd
            ),
        )


class PromptRecorder:
    """A ``ChatModel`` for the offline dry run: keeps every outgoing prompt, sends nothing,
    and selects nothing (each answer falls back to the case data)."""

    name = "prompt-recorder"

    def __init__(self) -> None:
        self._turn = ""
        self.prompts: dict[str, list[dict[str, str]]] = {}

    def begin(self, key: str, rep: int) -> None:
        self._turn = key

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self.prompts[self._turn] = [dict(m) for m in messages]
        return ModelAnswer("")

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self.prompts[self._turn] = [dict(m) for m in messages]
        yield Piece(cut_short=False)

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None
