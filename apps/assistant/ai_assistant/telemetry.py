"""Content-free metrics for each explicit question (off by default).

One record per /chat or /chat/stream request, small talk and every fallback included, so the
AI Assistant can be measured before anything about it is optimised. A record holds only
counts, sizes, timings, closed-vocabulary codes and opaque references. It never holds the
question, the history, the answer, an allowed line, a title or note, a person's or company's
name, a case or document value, a user id or a case id.

Every field is checked when a record is built. A value that is not content-free is refused:
the record is dropped and counted, and the refusal message names the field only, never the
value. A sink that fails never changes the answer.

    AI_ASSISTANT_TELEMETRY=off   no record is built (the default)
    AI_ASSISTANT_TELEMETRY=log   one JSON line per answer on the ``ai_assistant.metrics`` logger

Tests and the offline evaluation harness pass their own sink to ``create_app``.
"""

import hashlib
import inspect
import json
import logging
import math
import re
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from functools import cache
from typing import Any, Literal, Protocol

from . import anthropic_profiles, prompts
from .instructions import case_page_terms
from .llm import BUDGET_OUTCOMES, MODEL_ERROR_CLASSES
from .model_profiles import ENDPOINT_SLUG, LOCAL_PROFILE_ID, PROFILE_IDS

# Version 2 (Phase A2, D-091 proposed) adds the model profile, the requested endpoint,
# provider usage counts and cost, the budget outcome and the provider error class.
METRICS_VERSION = 2
# D-099 Option B: the Claude configurations are recorded by their own profile ids (the bare
# adapter, as the evaluation harness uses it, by its ledger profile).
RECORDED_PROFILE_IDS = (
    PROFILE_IDS | anthropic_profiles.PROFILE_IDS | {anthropic_profiles.LEDGER_PROFILE_ID}
)
LOGGER_NAME = "ai_assistant.metrics"

Route = Literal["chat", "stream"]
AnsweredBy = Literal["model", "case_data"]
FallbackReason = Literal[
    "none",
    "small_talk",
    "model_disabled",
    "model_unavailable",
    "policy_no_allowed_line",
    "stream_partial",
    "budget_refused",
    # D-094: the remote test model was active, but the question was outside the synthetic
    # boundary, so nothing was sent.
    "remote_boundary",
    # D-115 copilot mode: a question outside corporate onboarding; the model is not called.
    "off_domain",
]
Confidence = Literal["high", "low", "none"]
Kind = Literal["guidance", "resolution"]

ROUTES = frozenset({"chat", "stream"})
ANSWERED_BY = frozenset({"model", "case_data"})
FALLBACK_REASONS = frozenset(
    {
        "none",
        "small_talk",
        "model_disabled",
        "model_unavailable",
        "policy_no_allowed_line",
        "stream_partial",
        "budget_refused",
        "remote_boundary",
        # Was missing here, so every off-domain record was dropped as invalid (D-115).
        "off_domain",
    }
)
FINISH_REASONS = frozenset({"stop", "length"})
CONFIDENCES = frozenset({"high", "low", "none"})
KINDS = frozenset({"guidance", "resolution"})
PARTS = ("rules", "facts", "history", "knowledge", "terms", "question", "other")
TIMINGS = ("retrieval", "first_model_piece", "first_displayed_line", "total")

_HEX16 = re.compile(r"[0-9a-f]{16}")
_HEX32 = re.compile(r"[0-9a-f]{32}")
# A configured model name ("ministral-3:8b", "openai/gpt-oss-120b"): set by the operator, not
# by a user or a case. Anything else is refused.
_MODEL_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,99}")
_MAX_COUNT = 10**9


class MetricsValidationError(ValueError):
    """A metrics field was not content-free. The message names the field, never the value."""


def _count(name: str, value: object) -> int:
    if type(value) is not int or not 0 <= value < _MAX_COUNT:
        raise MetricsValidationError(f"{name} must be a non-negative count")
    return value


def _flag(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise MetricsValidationError(f"{name} must be true or false")
    return value


def _code(name: str, value: object, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise MetricsValidationError(f"{name} is not a known code")
    return value


def _pattern(name: str, value: object, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise MetricsValidationError(f"{name} is not a content-free identifier")
    return value


def entry_ref(entry_id: str) -> str:
    """An opaque reference to a knowledge entry (its id can carry title words, so it is
    never recorded as written). The evaluation harness recomputes it from the store."""

    return hashlib.sha256(entry_id.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RetrievedEntry:
    # A ``Kind`` value; checked below.
    kind: str
    ref: str
    version: int
    score: float
    fallback: bool

    def __post_init__(self) -> None:
        _code("retrieval.kind", self.kind, KINDS)
        _pattern("retrieval.ref", self.ref, _HEX16)
        _count("retrieval.version", self.version)
        if type(self.score) is not float or not math.isfinite(self.score):
            raise MetricsValidationError("retrieval.score must be a finite number")
        _flag("retrieval.fallback", self.fallback)


@dataclass(frozen=True)
class RetrievalMetrics:
    # A ``Confidence`` value; checked below.
    confidence: str
    degraded: bool
    entries: tuple[RetrievedEntry, ...] = ()

    def __post_init__(self) -> None:
        _code("retrieval.confidence", self.confidence, CONFIDENCES)
        _flag("retrieval.degraded", self.degraded)
        if not isinstance(self.entries, tuple) or not all(
            isinstance(entry, RetrievedEntry) for entry in self.entries
        ):
            raise MetricsValidationError("retrieval.entries must be retrieved entries")


@dataclass(frozen=True)
class UsageMetrics:
    """Provider-reported counts and cost (micro-USD), when the adapter reports them."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    cached_tokens: int | None = None
    cost_micro_usd: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "cached_tokens",
            "cost_micro_usd",
        ):
            value = getattr(self, name)
            if value is not None:
                _count(f"usage.{name}", value)


@dataclass(frozen=True)
class BudgetMetrics:
    """What the budget guard did (remote profile only), in micro-USD."""

    outcome: str
    reserved_micro_usd: int
    charged_micro_usd: int | None = None

    def __post_init__(self) -> None:
        _code("budget.outcome", self.outcome, BUDGET_OUTCOMES)
        _count("budget.reserved_micro_usd", self.reserved_micro_usd)
        if self.charged_micro_usd is not None:
            _count("budget.charged_micro_usd", self.charged_micro_usd)


@dataclass(frozen=True)
class AnswerMetrics:
    request_id: str
    route: Route
    answered_by: AnsweredBy
    fallback_reason: FallbackReason
    model: str | None
    prompt_version: str
    part_chars: Mapping[str, int]
    message_count: int
    history_turns: int
    retrieval: RetrievalMetrics | None
    allowed_catalog_lines: int
    allowed_knowledge_lines: int
    kept_lines: int
    left_out_lines: int
    cited_sources: int
    cut_short: bool
    cancelled: bool
    timings_ms: Mapping[str, int | None]
    # Version 2. The endpoint is the requested one: the response does not say which provider
    # served it, so provider_verified stays false until a verified source exists (Phase B).
    profile: str = LOCAL_PROFILE_ID
    requested_endpoint: str | None = None
    provider_verified: bool = False
    usage: UsageMetrics | None = None
    finish_reason: str | None = None
    empty_content: bool = False
    provider_error_class: str | None = None
    budget: BudgetMetrics | None = None
    metrics_version: int = field(default=METRICS_VERSION)

    def __post_init__(self) -> None:
        _pattern("request_id", self.request_id, _HEX32)
        _code("route", self.route, ROUTES)
        _code("answered_by", self.answered_by, ANSWERED_BY)
        _code("fallback_reason", self.fallback_reason, FALLBACK_REASONS)
        if self.model is not None:
            _pattern("model", self.model, _MODEL_NAME)
        _pattern("prompt_version", self.prompt_version, _HEX16)
        if not isinstance(self.part_chars, Mapping) or set(self.part_chars) != set(PARTS):
            raise MetricsValidationError("part_chars must name exactly the known parts")
        for name, value in self.part_chars.items():
            _count(f"part_chars.{name}", value)
        for name in (
            "message_count",
            "history_turns",
            "allowed_catalog_lines",
            "allowed_knowledge_lines",
            "kept_lines",
            "left_out_lines",
            "cited_sources",
        ):
            _count(name, getattr(self, name))
        if self.retrieval is not None and not isinstance(self.retrieval, RetrievalMetrics):
            raise MetricsValidationError("retrieval must be retrieval metrics")
        _flag("cut_short", self.cut_short)
        _flag("cancelled", self.cancelled)
        if not isinstance(self.timings_ms, Mapping) or set(self.timings_ms) != set(TIMINGS):
            raise MetricsValidationError("timings_ms must name exactly the known timings")
        for name, timing in self.timings_ms.items():
            if timing is not None:
                _count(f"timings_ms.{name}", timing)
        _code("profile", self.profile, RECORDED_PROFILE_IDS)
        if self.requested_endpoint is not None:
            _pattern("requested_endpoint", self.requested_endpoint, ENDPOINT_SLUG)
        _flag("provider_verified", self.provider_verified)
        if self.usage is not None and not isinstance(self.usage, UsageMetrics):
            raise MetricsValidationError("usage must be usage metrics")
        if self.finish_reason is not None:
            _code("finish_reason", self.finish_reason, FINISH_REASONS)
        _flag("empty_content", self.empty_content)
        if self.provider_error_class is not None:
            _code("provider_error_class", self.provider_error_class, MODEL_ERROR_CLASSES)
        if self.budget is not None and not isinstance(self.budget, BudgetMetrics):
            raise MetricsValidationError("budget must be budget metrics")
        if self.metrics_version != METRICS_VERSION:
            raise MetricsValidationError("metrics_version is not supported")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["part_chars"] = dict(self.part_chars)
        data["timings_ms"] = dict(self.timings_ms)
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


# --- prompt description ------------------------------------------------------------------


@cache
def prompt_version() -> str:
    """Which prompt produced a request: the prompt builder's source, the rules and the page
    terms, hashed. Any edit to them gives a new version (an editor note included)."""

    digest = hashlib.sha256()
    try:
        digest.update(inspect.getsource(prompts).encode("utf-8"))
    except (OSError, TypeError):
        digest.update(b"prompt-builder-source-unavailable")
    digest.update(b"\0" + prompts.SYSTEM_PROMPT.encode("utf-8"))
    digest.update(b"\0" + json.dumps(case_page_terms(), sort_keys=True).encode("utf-8"))
    return digest.hexdigest()[:16]


def describe_messages(messages: Sequence[Mapping[str, str]]) -> tuple[dict[str, int], int]:
    """Characters per prompt part, and how many history turns were sent.

    Parts are recognised by role and by the markers ``prompts.py`` writes; the first system
    message is the rules. Only lengths leave this function.
    """

    parts = dict.fromkeys(PARTS, 0)
    history = 0
    last = len(messages) - 1
    for index, message in enumerate(messages):
        role = message.get("role")
        content = message.get("content") or ""
        if index == 0 and role == "system":
            part = "rules"
        elif role == "system" and content.startswith("CASE FACTS"):
            part = "facts"
        elif role == "system" and content.startswith("KNOWLEDGE"):
            part = "knowledge"
        elif role == "system" and content.startswith("CASE PAGE TERMS"):
            part = "terms"
        elif index == last and role == "user":
            part = "question"
        elif role in ("user", "assistant"):
            part = "history"
            history += 1
        else:
            part = "other"
        parts[part] += len(content)
    return parts, history


# --- sinks ---------------------------------------------------------------------------------


class MetricsSink(Protocol):
    def record(self, metrics: AnswerMetrics) -> None: ...


class NullSink:
    """Telemetry off: nothing is built or kept."""

    def record(self, metrics: AnswerMetrics) -> None:
        return None


class MemorySink:
    """Keeps records in memory (tests and the offline evaluation harness)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: list[AnswerMetrics] = []

    def record(self, metrics: AnswerMetrics) -> None:
        with self._lock:
            self._records.append(metrics)

    @property
    def records(self) -> list[AnswerMetrics]:
        with self._lock:
            return list(self._records)


class LogSink:
    """One JSON line per answer on the ``ai_assistant.metrics`` logger.

    Without a logger of its own, it writes plain lines to standard error, so the records are
    visible under uvicorn without changing any other logging.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        if logger is None:
            logger = logging.getLogger(LOGGER_NAME)
            if not logger.handlers:
                handler = logging.StreamHandler(sys.stderr)
                handler.setFormatter(logging.Formatter("%(message)s"))
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
                logger.propagate = False
        self._logger = logger

    def record(self, metrics: AnswerMetrics) -> None:
        self._logger.info(metrics.to_json())


def sink_for(mode: str) -> MetricsSink:
    if mode == "log":
        return LogSink()
    return NullSink()


class MetricsRecorder:
    """Builds and records one answer's metrics, never letting a failure reach the answer.

    The record is built only when a sink other than ``NullSink`` is in use. Refused or failed
    records are counted, not logged: their error could quote a value.
    """

    def __init__(self, sink: MetricsSink) -> None:
        self._sink = sink
        self._lock = threading.Lock()
        self.dropped = 0

    @property
    def enabled(self) -> bool:
        return not isinstance(self._sink, NullSink)

    def record(self, build: Callable[[], AnswerMetrics]) -> None:
        if not self.enabled:
            return
        try:
            self._sink.record(build())
        except Exception:  # metrics are optional: never let them break an answer
            with self._lock:
                self.dropped += 1
