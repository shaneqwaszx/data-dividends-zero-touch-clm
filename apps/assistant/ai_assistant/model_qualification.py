"""Connection test and technical qualification of a local model (D-093).

Nothing here sends case, customer or sponsor data: the connection test and the capacity
check use fixed synthetic text, and the qualification asks the repository's synthetic
scenarios through the offline evaluation harness, in its own process
(``scripts/qualify_model.py``: a mock CLM backend, the real service, the real guardrails), so
the dev-only harness is never loaded into the service. Only counts, rates, timings and
closed codes are kept.

Qualification is **technical**: it shows the model connects, its output passes the existing
guardrails, it stays available and its context window holds the prompts. It is not evidence
of answer quality. Answer quality is ``NOT_SCORED`` while the owner gold labels are not
locked (A-6), and is only reported, never gated, when they are.

Gates (owner decision 4, D-093; provisional technical gates):

    G-1  connection test passed (model listed when the server lists models; one plain and
         one streamed completion through the service's own parsers)
    G-2  every scenario turn returned a final answer
    G-3  no displayed line that is not an allowed line (unsafe display = 0)
    G-4  turns where the model was unavailable or stopped mid-answer <= 5 %
    G-5  REPORTED ONLY: turns where no allowed line was selected
    G-6  kept / written model lines >= 0.70, with at least one written line
    G-7  context capacity verified from the server's own token counts, every qualification
         prompt inside the verified bound, and cut-short answers <= 10 %
"""

import hashlib
import json
import math
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
from pathlib import Path
from typing import Any
from uuid import uuid4

import anyio

from .llm import (
    ChatModel,
    LlmUnavailableError,
    ModelAnswer,
    ModelCallError,
    OpenAICompatibleChatModel,
    Piece,
    message_bytes,
)
from .model_catalog import MESSAGE_OVERHEAD_TOKENS
from .model_factory import ASSISTANT_DIR

HARNESS_VERSION = "model-qualification/1"
PACKAGE_DIR = Path(__file__).resolve().parent
EVAL_FIXTURES = ASSISTANT_DIR / "tests" / "fixtures" / "eval"
# What a model's answers depend on besides the model: a change to any of these makes an
# earlier qualification out of date (the model must be qualified again before activation).
BASIS_FILES = (
    "main.py",
    "llm.py",
    "prompts.py",
    "guardrails.py",
    "guide.py",
    "briefing.py",
    "context.py",
    "knowledge_answers.py",
    "small_talk.py",
    "instructions.py",
    "answer_records.py",
    "knowledge/retrieval.py",
    "knowledge/redaction.py",
    # D-094: the remote test model's gate and its synthetic boundary.
    "remote_test.py",
    "remote_checks.py",
    "synthetic_boundary.py",
    "synthetic_boundary.json",
    # D-095: the development eligibility gate, its manifest and the key sources.
    "synthetic_eligibility.py",
    "synthetic_eligibility.json",
    "key_sources.py",
    "budget.py",
    # D-099 Option B: the Claude adapter, its configurations and its gated runtime.
    "anthropic_chat.py",
    "anthropic_profiles.py",
    "anthropic_runtime.py",
    # D-104: the data access policy's gate for local and IT-configured models.
    "data_access.py",
    # D-115 (proposed): copilot answers and the chat contexts whose turns are the history.
    "copilot.py",
    "case_contexts.py",
    # D-115 refinement 2: copilot evidence and structured claim checks (local model only).
    "claims.py",
    "evidence.py",
    # D-130: Support's chat, now answered by hosted Claude too; the decision and its paths
    # (config, QG N1); what of the user a Claude-bound prompt may carry (OD-G8).
    "support_chat.py",
    "config.py",
    "provider_payload.py",
    # D-130 amendment draft: the fifth hosted path's prompt and derived findings.
    "hosted_insights.py",
    "dashboard_insights.py",
)
BASIS_GLOBS = ("instructions/*.md", "knowledge/guidance/*.md")
BASIS_FIXTURES = (
    "scenarios.json",
    "snapshots.json",
    "gold.json",
    "gold.lock.json",
    "phase_b_questions.json",
    # D-130: the hosted chat paths' qualification turns.
    "hosted_paths.json",
)
# D-130 (QG N1): every fixture a qualification prompt is built from (the qualification
# harness's case inputs), relative to the assistant directory. The image keeps the same layout
# (deploy/assistant.Dockerfile), so a hosted basis equals a development checkout's.
BASIS_HARNESS = (
    "tests/fixtures/garden_address_conflict_summary.json",
    "tests/fixtures/garden_documents.json",
    "tests/fixtures/garden_waiting_for_documents_summary.json",
    "tests/fixtures/me_client_onboarder.json",
    "../backend/tests/fixtures/uat/garden-business-clean-onboarding-profile.pdf",
)

G4_MAX_UNAVAILABLE = 0.05
G6_MIN_LINE_VALIDITY = 0.70
G7_MAX_CUT_SHORT = 0.10
# The capacity check probes at most this many prompt tokens (a larger declared window is
# verified only this far, and the prompt bound follows the verified figure).
CAPACITY_CAP_TOKENS = 32768
CAPACITY_CALIBRATION_BYTES = 4096
# Room kept below the verified figure for chat templates and the answer's first tokens.
CAPACITY_MARGIN_TOKENS = 256
CAPACITY_PROBE_HEADROOM = 64
# The probed count may fall this far short of the expected count (tokenizers merge text
# differently at different lengths); a truncating server falls much further short.
CAPACITY_LINEARITY = 0.97

PROBE = [
    {
        "role": "system",
        "content": "This is a connection test with no case data. Reply with the word READY.",
    },
    {"role": "user", "content": "Connection test."},
]


def qualification_basis() -> str:
    """Which code and fixtures a qualification ran against (prompt, catalog, guardrails,
    answer assembly, scenarios, gold), hashed."""

    digest = hashlib.sha256(HARNESS_VERSION.encode("utf-8"))
    paths = [PACKAGE_DIR / name for name in BASIS_FILES]
    for pattern in BASIS_GLOBS:
        paths.extend(sorted(PACKAGE_DIR.glob(pattern)))
    paths.extend(EVAL_FIXTURES / name for name in BASIS_FIXTURES)
    named = [(path.relative_to(ASSISTANT_DIR).as_posix(), path) for path in paths]
    named.extend((name, ASSISTANT_DIR / name) for name in BASIS_HARNESS)
    for name, path in named:
        digest.update(b"\0" + name.encode("utf-8") + b"\0")
        try:
            data = path.read_bytes()
            digest.update(data if path.suffix == ".pdf" else data.replace(b"\r\n", b"\n"))
        except OSError:
            digest.update(b"missing")
    return digest.hexdigest()


def error_code(error: LlmUnavailableError) -> str:
    """A closed code for a failed model call (never the server's own text)."""

    if isinstance(error, ModelCallError):
        return error.error_class.upper()
    text = str(error)
    if text.startswith("model returned "):
        status = text.removeprefix("model returned ")
        return f"HTTP_{status}" if status.isdigit() and len(status) == 3 else "HTTP_ERROR"
    return {
        "model unreachable": "UNREACHABLE",
        "model too slow": "TIMEOUT",
        "empty model reply": "EMPTY_REPLY",
        "model stream ended early": "STREAM_INCOMPLETE",
        "model response limit exceeded": "RESPONSE_TOO_LARGE",
        "model frame limit exceeded": "RESPONSE_TOO_LARGE",
        "unsupported model completion": "UNSUPPORTED_COMPLETION",
        "unsupported model encoding": "UNSUPPORTED_ENCODING",
    }.get(text, "PROTOCOL")


async def connection_test(model: OpenAICompatibleChatModel, model_id: str) -> dict[str, Any]:
    """Reachability and interface compatibility, with fixed synthetic text only."""

    result: dict[str, Any] = {
        "outcome": "failed",
        "code": None,
        "listed": None,
        "complete_ms": None,
        "stream_ms": None,
        "first_piece_ms": None,
    }
    try:
        listed = await anyio.to_thread.run_sync(model.listed_models)
        if listed:
            result["listed"] = model_id in listed
            if not result["listed"]:
                result["code"] = "MODEL_NOT_LISTED"
                return result
        started = time.monotonic()
        await anyio.to_thread.run_sync(model.complete, PROBE)
        result["complete_ms"] = round((time.monotonic() - started) * 1000)
        started = time.monotonic()
        text = 0
        async with aclosing(model.stream(PROBE)) as pieces:
            async for piece in pieces:
                if piece.text:
                    if result["first_piece_ms"] is None:
                        result["first_piece_ms"] = round((time.monotonic() - started) * 1000)
                    text += len(piece.text)
        result["stream_ms"] = round((time.monotonic() - started) * 1000)
        if not text:
            result["code"] = "EMPTY_STREAM"
            return result
    except LlmUnavailableError as exc:
        result["code"] = error_code(exc)
        return result
    result["outcome"] = "passed"
    return result


def _filler(size: int) -> str:
    """Deterministic synthetic text of exactly ``size`` bytes (ASCII)."""

    lines: list[str] = []
    total = 0
    number = 0
    while total < size:
        number += 1
        line = f"Synthetic capacity line {number:06d}: plain check text with no meaning.\n"
        lines.append(line)
        total += len(line)
    return "".join(lines)[:size]


def _fresh(extra: list[dict[str, str]]) -> list[dict[str, str]]:
    """A unique first message, so a server's prompt cache cannot shorten the count."""

    return [
        {
            "role": "system",
            "content": f"Capacity check {uuid4().hex}. Synthetic text only; reply with one word.",
        },
        *extra,
    ]


def verify_capacity(
    model: OpenAICompatibleChatModel,
    *,
    declared_tokens: int,
    max_answer_tokens: int,
    largest_prompt: list[dict[str, str]] | None,
    stop: Callable[[], None] = lambda: None,
) -> dict[str, Any]:
    """Check from the server's own prompt-token counts that it holds the declared window
    (up to ``CAPACITY_CAP_TOKENS``) without truncating, and that UTF-8 bytes bound its token
    count on the largest qualification prompt. Returns the prompt bound (``prompt_limit``,
    in bytes plus per-message overhead) that the activated model will enforce."""

    target = min(declared_tokens, CAPACITY_CAP_TOKENS)
    result: dict[str, Any] = {
        "status": "unverified",
        "code": None,
        "declared_tokens": declared_tokens,
        "target_tokens": target,
        "probed_tokens": None,
        "prompt_limit": None,
    }

    def count(messages: list[dict[str, str]]) -> int:
        stop()
        tokens = model.prompt_tokens(messages)
        if tokens is None:
            raise _Unverified("USAGE_NOT_REPORTED")
        return tokens

    try:
        base = count(_fresh([{"role": "user", "content": "."}]))
        if largest_prompt:
            real = count(_fresh(largest_prompt))
            bound = (
                base + message_bytes(largest_prompt) + MESSAGE_OVERHEAD_TOKENS * len(largest_prompt)
            )
            if real > bound:
                raise _Unverified("TOKENIZER_BOUND_NOT_CONFIRMED")
        calibration = count(
            _fresh([{"role": "user", "content": _filler(CAPACITY_CALIBRATION_BYTES)}])
        )
        rate = (calibration - base) / CAPACITY_CALIBRATION_BYTES
        if rate <= 0:
            raise _Unverified("USAGE_UNRELIABLE")
        # Fill the window, leaving room only for the one output token the probe asks for.
        aim = target - CAPACITY_PROBE_HEADROOM
        size = math.floor((aim - base) / rate)
        if size <= CAPACITY_CALIBRATION_BYTES:
            raise _Unverified("WINDOW_TOO_SMALL")
        probed = count(_fresh([{"role": "user", "content": _filler(size)}]))
        result["probed_tokens"] = probed
        expected = base + rate * size
        if probed < CAPACITY_LINEARITY * expected:
            # A server that keeps fewer tokens than it was sent has truncated the prompt.
            raise _Unverified("TRUNCATION_DETECTED")
    except _Unverified as exc:
        result["code"] = exc.code
        return result
    except LlmUnavailableError as exc:
        # A server that refuses the probe (for example HTTP 400 for too long a prompt) does
        # not hold the declared window.
        result["status"] = "failed"
        result["code"] = "CAPACITY_" + error_code(exc)
        return result
    # The answer must fit beside the prompt in what the server was shown to hold.
    limit = probed - base - max_answer_tokens - CAPACITY_MARGIN_TOKENS
    if limit <= 0:
        result["code"] = "WINDOW_TOO_SMALL"
        return result
    result.update(status="verified", prompt_limit=limit)
    return result


class _Unverified(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class QualificationStopped(Exception):
    """The run was cancelled or reached its time limit (not a model failure: it propagates
    through the service unchanged and ends the run)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class WatchedModel:
    """The candidate model as the harness sees it: counts turns, keeps the largest prompt
    (synthetic) for the capacity check, and stops the run when asked."""

    def __init__(
        self,
        inner: ChatModel,
        stop: Callable[[int], None],
        *,
        synthetic: bool = False,
        development: Callable[[], bool] | None = None,
    ) -> None:
        self.inner = inner
        self._stop = stop
        if synthetic:
            # Conversational answers: the service checks every prompt as it does in the chat
            # (the synthetic boundary or the D-095 eligibility check, with its ticket), so the
            # harness model shows itself as the external model it wraps.
            self.requires_synthetic_boundary = getattr(inner, "requires_synthetic_boundary", False)
            for name in ("development_mode", "notices", "hosted_claude", "anthropic_bound"):
                if hasattr(inner, name):
                    setattr(self, name, getattr(inner, name))
            if not hasattr(self, "development_mode") and development is not None:
                # GPT-OSS: D-095 mode is the service's own decision (its OpenRouter-ready
                # settings), not the harness's.
                self.development_mode = development
        self.turns = 0
        self.largest: list[dict[str, str]] = []
        self.largest_bound = 0

    @property
    def name(self) -> str:
        return self.inner.name

    def begin(self, key: str, rep: int) -> None:
        self._stop(self.turns)
        self.turns += 1
        begin = getattr(self.inner, "begin", None)
        if callable(begin):
            begin(key, rep)

    def _seen(self, messages: list[dict[str, str]]) -> None:
        bound = message_bytes(messages) + MESSAGE_OVERHEAD_TOKENS * len(messages)
        if bound > self.largest_bound:
            self.largest_bound = bound
            self.largest = [dict(item) for item in messages]

    def complete(self, messages: list[dict[str, str]]) -> ModelAnswer:
        self._seen(messages)
        return self.inner.complete(messages)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Piece, None]:
        self._seen(messages)
        async with aclosing(self.inner.stream(messages)) as source:
            async for piece in source:
                yield piece

    def warm(self, messages: list[dict[str, str]]) -> None:
        return None


def quality_state() -> tuple[str, str | None]:
    """Whether answer quality can be scored: owner gold must be fully labelled and locked
    (A-6). Read without the harness; the qualification process verifies the lock itself and
    records the verified state with its result, which is what activation relies on."""

    gold_file = EVAL_FIXTURES / "gold.json"
    if not gold_file.exists():
        return "NOT_SCORED", "OWNER_GOLD_MISSING"
    try:
        gold = json.loads(gold_file.read_text(encoding="utf-8"))
        turns = gold.get("turns") or {}
        labelled = (
            gold.get("kind") == "owner"
            and bool(turns)
            and all(
                isinstance(turn, dict) and turn.get("status") == "labelled"
                for turn in turns.values()
            )
        )
    except (OSError, ValueError, AttributeError):
        return "NOT_SCORED", "OWNER_GOLD_UNREADABLE"
    if not labelled:
        return "NOT_SCORED", "OWNER_GOLD_NOT_LABELLED"
    if not (EVAL_FIXTURES / "gold.lock.json").exists():
        return "NOT_SCORED", "OWNER_GOLD_NOT_LOCKED"
    return "SCORED", None


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def _gate(
    gate: str, rule: str, value: object, passed: bool, *, gating: bool = True
) -> dict[str, Any]:
    return {"gate": gate, "rule": rule, "value": value, "passed": passed, "gating": gating}


def gates(
    *,
    connection: dict[str, Any],
    completed: bool,
    turns: list[Any],
    expected_turns: int,
    overall: dict[str, Any],
    capacity: dict[str, Any] | None,
    largest_bound: int,
) -> list[dict[str, Any]]:
    answers = len(turns)
    reasons = overall.get("fallback_reasons") or {}
    unavailable = int(reasons.get("model_unavailable", 0)) + int(reasons.get("stream_partial", 0))
    no_line = int(reasons.get("policy_no_allowed_line", 0))
    kept = sum(int(turn.metrics["kept_lines"]) for turn in turns)
    written = kept + sum(int(turn.metrics["left_out_lines"]) for turn in turns)
    validity = _rate(kept, written)
    cut_short = overall.get("cut_short_rate")
    limit = capacity.get("prompt_limit") if capacity else None
    capacity_ok = (
        capacity is not None
        and capacity.get("status") == "verified"
        and isinstance(limit, int)
        and largest_bound <= limit
    )
    return [
        _gate(
            "G-1",
            "connection test passed",
            connection.get("outcome"),
            connection.get("outcome") == "passed",
        ),
        _gate(
            "G-2",
            "every turn returned a final answer",
            f"{answers}/{expected_turns}",
            completed and answers == expected_turns,
        ),
        _gate(
            "G-3",
            "unsafe displayed lines = 0",
            overall.get("unsafe_display"),
            completed and overall.get("unsafe_display") == 0,
        ),
        _gate(
            "G-4",
            "model unavailable or stopped mid-answer <= 5% of turns",
            _rate(unavailable, answers),
            completed and answers > 0 and unavailable / answers <= G4_MAX_UNAVAILABLE,
        ),
        _gate(
            "G-5",
            "no allowed line selected (reported only)",
            _rate(no_line, answers),
            True,
            gating=False,
        ),
        # A zero denominator (the model wrote no line at all) can never pass.
        _gate(
            "G-6",
            "kept / written model lines >= 0.70",
            validity,
            completed and written > 0 and kept / written >= G6_MIN_LINE_VALIDITY,
        ),
        _gate(
            "G-7",
            "context capacity verified, prompts inside it, cut short <= 10%",
            {
                "capacity": capacity.get("status") if capacity else None,
                "largest_prompt_bound": largest_bound,
                "prompt_limit": limit,
                "cut_short_rate": cut_short,
            },
            completed
            and capacity_ok
            and isinstance(cut_short, float | int)
            and cut_short <= G7_MAX_CUT_SHORT,
        ),
    ]


def line_breakdown(turns: list[Any]) -> dict[str, int]:
    """Model-selected, guard-withheld and application-required lines, and fallbacks, kept
    apart (required lines the service adds are never counted as the model's selection)."""

    selected = withheld = required = 0
    for turn in turns:
        withheld += int(turn.metrics["left_out_lines"])
        if turn.answered_by != "model":
            continue
        shown = len(turn.shown)
        lines = sum(1 for line in turn.answer_text.splitlines() if line.strip())
        selected += shown
        required += max(0, lines - shown - turn.unmapped)
    return {
        "model_selected_lines": selected,
        "guard_withheld_lines": withheld,
        "application_required_lines": required,
        "model_answers": sum(1 for turn in turns if turn.answered_by == "model"),
        "deterministic_fallbacks": sum(1 for turn in turns if turn.answered_by != "model"),
    }
