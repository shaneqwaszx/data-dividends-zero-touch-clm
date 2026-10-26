"""AI Assistant API (Phase 1: read-only).

    Browser chat panel -> this service (/assistant/...) -> existing CLM APIs (GET only)
                                                       -> chat model (OpenAI-compatible)

Every request re-reads the case, so answers reflect the case as it is now. The RM's own
session is forwarded to the CLM backend, which stays the authority for access.

Opening the panel (/brief) may pre-warm a literal loopback model in the background; the chat panel
uses /chat/stream so the answer appears while it is written (see README "Speed").

With the knowledge store on, every answer except small talk is saved as an answer record
(answer_records.py) and its ``answer_id`` returned, so "Not helpful" can point at it.
"""

import hashlib
import json
import logging
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import aclosing
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .answer_records import (
    ANSWER_ID,
    AnswerRecorder,
    allowed_lines,
    capped_dropped,
    case_snapshot,
    knowledge_used,
    new_answer_id,
)
from .answer_records import FallbackReason as RecordReason
from .briefing import fallback_answer, opening_message, suggested_questions
from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .context import build_case_facts
from .guardrails import (
    LEFT_OUT_REASON,
    StreamingGuard,
    Validation,
    allowed_guidance,
    validate_answer,
)
from .knowledge.redaction import Redactor, case_parties
from .knowledge.retrieval import Retriever, case_context, settings_from
from .knowledge.service import KnowledgeBase
from .knowledge_answers import (
    ShownKnowledge,
    TaggedHit,
    approved_knowledge,
    guidance_summary,
    knowledge_message,
    shown_knowledge,
    sources_for,
    tag_hits,
)
from .llm import (
    CallBudget,
    ChatModel,
    LlmUnavailableError,
    ModelAnswer,
    ModelCallError,
    ModelUsage,
    OpenAICompatibleChatModel,
    Piece,
    is_local_model_url,
    micro_usd,
)
from .model_factory import build_chat_model
from .prompts import build_messages, prefix_messages
from .small_talk import small_talk_reply
from .telemetry import (
    PARTS,
    AnsweredBy,
    AnswerMetrics,
    BudgetMetrics,
    FallbackReason,
    MetricsRecorder,
    MetricsSink,
    RetrievalMetrics,
    RetrievedEntry,
    Route,
    UsageMetrics,
    describe_messages,
    entry_ref,
    prompt_version,
    sink_for,
)


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    # The answer records of the earlier answers in this chat. Only ids are taken from the
    # browser, and only the server's own records of this user on this case are kept.
    earlier_answer_ids: list[Annotated[str, Field(pattern=ANSWER_ID)]] = Field(
        default_factory=list, max_length=40
    )


class BriefResponse(BaseModel):
    company: str | None
    message: str
    suggested_questions: list[str]
    blocker_count: int
    steps_done: int
    steps_total: int


class AnswerChecks(BaseModel):
    """What the output policy did to a model answer (reason codes only, never the text)."""

    # "not_an_allowed_line" when any model line was not an allowed line and was left out.
    removed: list[str]
    disclosures: list[str]


class KnowledgeSource(BaseModel):
    """A retrieved knowledge entry the answer could use (cited = the answer names its tag).

    Only checked or fixed-form fields: the title is checked or a neutral label, and the
    entry's id and free-text source reference are not sent to the RM's browser.
    """

    tag: str
    kind: Literal["guidance", "resolution"]
    version: int
    title: str
    approved_at: str | None
    illustrative: bool
    fallback: bool
    cited: bool


class KnowledgeUse(BaseModel):
    # high: specific entries matched; low: only general stage guidance; none.
    confidence: Literal["high", "low", "none"]
    # The embedding model was down, so only keywords and case context were used.
    degraded: bool


class ChatResponse(BaseModel):
    answer: str
    answered_by: Literal["model", "case_data"]
    model: str | None
    notice: str | None
    suggested_questions: list[str]
    # Set for model answers: why sentences were left out, and the disclosures added.
    checks: AnswerChecks | None = None
    # Retrieved guidance and past cases, and how confident retrieval was.
    sources: list[KnowledgeSource] = Field(default_factory=list)
    knowledge: KnowledgeUse | None = None
    # The server's record of this answer (none for small talk, or with the knowledge store
    # off); "Not helpful" sends it back.
    answer_id: str | None = None
    # A fixed small-talk reply: it never has a record, so a missing answer_id is expected.
    small_talk: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok"]
    llm_enabled: bool
    model: str | None


FALLBACK_NOTICE = "The AI model is not available, so this answer comes straight from the case data."
POLICY_NOTICE = "The model response could not be verified, so this answer comes from the case data."
CUT_SHORT_NOTICE = "This answer was cut short. Ask me to continue for the rest."


log = logging.getLogger("ai_assistant")


@dataclass
class Prepared:
    """Everything one question needs, worked out once (used by /chat and /chat/stream)."""

    facts: dict[str, Any]
    messages: list[dict[str, str]]
    fallback: str
    suggestions: list[str]
    tagged: list[TaggedHit] = field(default_factory=list)
    knowledge: KnowledgeUse | None = None
    # The checked knowledge text the RM may see: lines the model may select, titles and
    # follow-up questions (knowledge_answers.shown_knowledge).
    shown: ShownKnowledge = field(default_factory=ShownKnowledge)
    # How long knowledge retrieval took (metrics only).
    retrieval_ms: int | None = None
    # The question as the model got it (after the max_question_chars cut), and when work on
    # it started (time.monotonic), for the answer record.
    question: str = ""
    started: float = 0.0

    def sources(self, answer: str) -> list[KnowledgeSource]:
        return [
            KnowledgeSource(**source) for source in sources_for(self.tagged, answer, self.shown)
        ]


@dataclass
class _Outcome:
    """What happened to one answer, kept only for its content-free metrics (telemetry.py)."""

    answered_by: AnsweredBy = "case_data"
    fallback_reason: FallbackReason = "none"
    kept_lines: int = 0
    left_out_lines: int = 0
    cited_sources: int = 0
    cut_short: bool = False
    cancelled: bool = False
    first_piece_at: float | None = None
    first_line_at: float | None = None
    # The check of the model's text, if it got one (the answer record keeps its left-out
    # lines); never part of the metrics.
    validation: Validation | None = None
    # Reported only by adapters that report them (never by the local adapter).
    usage: ModelUsage | None = None
    finish_reason: str | None = None
    empty_content: bool = False
    provider_error_class: str | None = None
    budget: CallBudget | None = None

    def answered(self, response: "ChatResponse") -> "ChatResponse":
        self.answered_by = response.answered_by
        self.cited_sources = sum(1 for source in response.sources if source.cited)
        return response

    def selected(self, validation: Validation) -> None:
        self.kept_lines = len(validation.text.splitlines())
        self.left_out_lines = validation.left_out
        self.validation = validation

    def record_reason(self) -> RecordReason | None:
        """Why the answer is not a full model answer, as the answer record says it."""

        # A budget refusal (D-091, proposed) is recorded like any other answer without a model.
        if self.fallback_reason in ("model_disabled", "model_unavailable", "budget_refused"):
            return "model_unavailable"
        if self.fallback_reason == "policy_no_allowed_line":
            return "nothing_allowed"
        if self.fallback_reason == "stream_partial" or self.cut_short:
            return "cut_short"
        return None

    def reported(self, answer: ModelAnswer | Piece) -> None:
        self.usage = answer.usage or self.usage
        self.finish_reason = answer.finish_reason or self.finish_reason
        self.budget = answer.budget or self.budget

    def failed(self, error: LlmUnavailableError) -> None:
        """The closed class of a failed call; a budget refusal is its own fallback reason."""

        if not isinstance(error, ModelCallError):
            return
        self.provider_error_class = error.error_class
        self.usage = error.usage or self.usage
        self.budget = error.budget or self.budget
        self.empty_content = self.empty_content or error.error_class == "empty_content"
        if error.error_class == "budget_refused" and self.fallback_reason == "none":
            self.fallback_reason = "budget_refused"


def _usage_metrics(usage: ModelUsage | None) -> UsageMetrics | None:
    if usage is None:
        return None
    return UsageMetrics(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        reasoning_tokens=usage.reasoning_tokens,
        cached_tokens=usage.cached_tokens,
        cost_micro_usd=None if usage.cost is None else micro_usd(usage.cost),
    )


def _budget_metrics(budget: CallBudget | None) -> BudgetMetrics | None:
    if budget is None:
        return None
    return BudgetMetrics(
        outcome=budget.outcome,
        reserved_micro_usd=budget.reserved_micro_usd,
        charged_micro_usd=budget.charged_micro_usd,
    )


def _model_reply(
    validation: Validation, prep: Prepared, *, model_name: str, cut_short: bool
) -> "ChatResponse":
    notices = [n for n in (validation.notice(), CUT_SHORT_NOTICE if cut_short else None) if n]
    return ChatResponse(
        answer=validation.text,
        answered_by="model",
        model=model_name,
        notice=" ".join(notices) or None,
        suggested_questions=prep.suggestions,
        checks=AnswerChecks(
            removed=[LEFT_OUT_REASON] if validation.left_out else [],
            disclosures=list(validation.disclosures),
        ),
        sources=prep.sources(validation.text),
        knowledge=prep.knowledge,
    )


def _fallback_reply(prep: Prepared, *, notice: str = FALLBACK_NOTICE) -> "ChatResponse":
    return ChatResponse(
        answer=prep.fallback,
        answered_by="case_data",
        model=None,
        notice=notice,
        suggested_questions=prep.suggestions,
        sources=prep.sources(prep.fallback),
        knowledge=prep.knowledge,
    )


def create_app(
    settings: AiAssistantSettings | None = None,
    *,
    clm_transport: httpx.BaseTransport | None = None,
    chat_model: ChatModel | None = None,
    knowledge: KnowledgeBase | None = None,
    metrics: MetricsSink | None = None,
    on_prepared: Callable[[Prepared], None] | None = None,
    retrieval_clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """``metrics`` overrides the ``telemetry`` setting (tests, offline evaluation).

    ``on_prepared`` and ``retrieval_clock`` are in-process seams for the offline evaluation
    harness only, never set from settings. ``on_prepared`` sees each question's case facts,
    prompt and allowed lines, so it must not be given anything that keeps non-synthetic
    data. ``retrieval_clock`` fixes "now" for knowledge recency so a frozen evaluation does
    not change with the date; left out, retrieval uses the current time as before.
    """

    config = settings or AiAssistantSettings()
    recorder = MetricsRecorder(metrics if metrics is not None else sink_for(config.telemetry))
    retriever = (
        Retriever(knowledge, settings_from(config), clock=retrieval_clock)
        if knowledge is not None and config.knowledge_enabled
        else None
    )
    backend = ClmBackendClient(
        config.clm_backend_url,
        timeout_seconds=config.backend_timeout_seconds,
        transport=clm_transport,
    )
    model: ChatModel | None = chat_model
    if model is None and config.llm_enabled:
        # The default profile builds the same adapter as before; the remote profile is
        # dormant and refuses to start here (model_factory.py).
        model = build_chat_model(config, local_adapter=OpenAICompatibleChatModel)

    app = FastAPI(title="AI Assistant", version="0.1.0")

    allowed_origins = {origin.rstrip("/") for origin in config.allowed_origins}

    def check_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if origin is not None and origin.rstrip("/") not in allowed_origins:
            raise HTTPException(
                status_code=403,
                detail={"code": "ORIGIN_NOT_ALLOWED", "message": "Request origin not allowed."},
            )

    def backend_error(exc: ClmBackendError) -> HTTPException:
        return HTTPException(
            status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}
        )

    def load_case(case_id: UUID, request: Request) -> CaseSnapshot:
        check_origin(request)
        try:
            return backend.load_case(case_id, request.cookies.get(SESSION_COOKIE_NAME))
        except ClmBackendError as exc:
            raise backend_error(exc) from None

    Snapshot = Annotated[CaseSnapshot, Depends(load_case)]

    def history_of(body: ChatRequest) -> list[dict[str, str]]:
        if not config.max_history_messages:
            return []
        return [
            {"role": turn.role, "content": turn.content}
            for turn in body.history[-config.max_history_messages :]
        ]

    answers = (
        AnswerRecorder(
            knowledge.store,
            unrated_days=config.answer_record_unrated_days,
            closed_days=config.answer_record_closed_days,
        )
        if knowledge is not None and config.knowledge_enabled
        else None
    )
    if answers is not None:
        try:
            answers.purge()  # expired answer records go on start-up
        except Exception:
            log.exception("answer record purge failed")

    def record(
        case_id: UUID,
        snapshot: CaseSnapshot,
        body: ChatRequest,
        prep: Prepared,
        response: ChatResponse,
        outcome: _Outcome,
    ) -> ChatResponse:
        """Save the answer record and put its id on the reply. Only what this request
        produced is saved: the browser's history text never is, and of the earlier answer
        ids it sent only this user's records on this case are kept."""

        if answers is None:
            return response
        profile = snapshot.actor.get("profile") or {}
        user = profile.get("user_id")
        if not user:
            return response
        validation = outcome.validation
        try:
            limit = config.max_history_messages
            earlier = answers.store.owned_answers(
                body.earlier_answer_ids[-limit:] if limit else [],
                user_id=str(user),
                case_id=str(case_id),
            )
            redact = Redactor(prep.facts, parties=case_parties(snapshot.summary)).redact
            answer_id = answers.save(
                {
                    "id": new_answer_id(),
                    "case_id": str(case_id),
                    "user_id": str(user),
                    "team": profile.get("team_id"),
                    "question": prep.question,
                    "earlier_answer_ids": earlier,
                    "case_snapshot": case_snapshot(prep.facts),
                    "knowledge": knowledge_used(
                        prep.tagged,
                        confidence=prep.knowledge.confidence if prep.knowledge else None,
                        degraded=prep.knowledge.degraded if prep.knowledge else None,
                        thresholds={
                            "guidance": config.retrieval_min_score_guidance,
                            "resolution": config.retrieval_min_score_resolution,
                        },
                    ),
                    "allowed_lines": allowed_lines(prep.facts, prep.shown.lines),
                    # Model answers only: the checked lines the RM was shown.
                    "chosen_lines": (
                        response.answer.splitlines() if response.answered_by == "model" else []
                    ),
                    # The answer as the RM saw it: a model answer is its checked lines; a
                    # case-data answer is fixed wording filled from the case, so it is redacted.
                    "shown_answer": (
                        response.answer
                        if response.answered_by == "model"
                        else redact(response.answer)
                    ),
                    "dropped_lines": (
                        capped_dropped(validation.dropped, redact) if validation else []
                    ),
                    "result": {
                        "answered_by": response.answered_by,
                        "notices": [response.notice] if response.notice else [],
                        "fallback_reason": outcome.record_reason(),
                        "left_out": validation.left_out if validation else 0,
                        "model": model.name if model is not None else None,
                        "elapsed_ms": round((time.monotonic() - prep.started) * 1000),
                    },
                }
            )
        except Exception:  # a record must never break the answer
            log.exception("answer record failed")
            return response
        return response.model_copy(update={"answer_id": answer_id})

    def prepare(body: ChatRequest, snapshot: CaseSnapshot, question: str) -> Prepared:
        started = time.monotonic()
        facts = build_case_facts(snapshot)
        tagged: list[TaggedHit] = []
        use: KnowledgeUse | None = None
        profile = snapshot.actor.get("profile") or {}
        role, team = profile.get("role"), profile.get("team_id")
        retrieval_ms: int | None = None
        if retriever is not None:
            began = time.monotonic()
            try:
                retrieval = retriever.retrieve(question, case_context(facts), role=role, team=team)
                tagged = approved_knowledge(tag_hits(retrieval), role=role, team=team)
                use = KnowledgeUse(confidence=retrieval.confidence, degraded=retrieval.degraded)
            except Exception:  # knowledge is optional: never let it break an answer
                log.exception("knowledge retrieval failed")
            retrieval_ms = round((time.monotonic() - began) * 1000)
        shown = shown_knowledge(tagged, facts)
        fallback = fallback_answer(question, facts)
        summary = guidance_summary(tagged, shown)
        if summary:
            fallback += "\n\n" + summary
        base = suggested_questions(facts)
        # Questions people with the same problem asked next come right after the top three.
        suggestions = base[:3]
        for suggestion in [*shown.follow_ups, *base[3:]]:
            if suggestion not in suggestions:
                suggestions.append(suggestion)
        prepared = Prepared(
            facts=facts,
            messages=build_messages(
                facts, history_of(body), question, knowledge=knowledge_message(tagged, shown)
            ),
            fallback=fallback,
            suggestions=suggestions[:6],
            tagged=tagged,
            knowledge=use,
            shown=shown,
            retrieval_ms=retrieval_ms,
            question=question,
            started=started,
        )
        if on_prepared is not None:
            on_prepared(prepared)
        return prepared

    def emit(route: Route, started: float, outcome: _Outcome, prep: Prepared | None) -> None:
        """Record this answer's content-free metrics (only built when telemetry is on)."""

        def build() -> AnswerMetrics:
            def since(moment: float | None) -> int | None:
                return None if moment is None else max(0, round((moment - started) * 1000))

            parts, history = (
                describe_messages(prep.messages) if prep else (dict.fromkeys(PARTS, 0), 0)
            )
            retrieval = None
            if prep is not None and prep.knowledge is not None:
                retrieval = RetrievalMetrics(
                    confidence=prep.knowledge.confidence,
                    degraded=prep.knowledge.degraded,
                    entries=tuple(
                        RetrievedEntry(
                            kind=item.hit.entry.kind.value,
                            ref=entry_ref(item.hit.entry.entry_id),
                            version=item.hit.entry.version,
                            score=float(item.hit.score),
                            fallback=item.hit.fallback,
                        )
                        for item in prep.tagged
                    ),
                )
            return AnswerMetrics(
                request_id=uuid4().hex,
                route=route,
                answered_by=outcome.answered_by,
                fallback_reason=outcome.fallback_reason,
                model=model.name
                if model is not None and outcome.fallback_reason != "small_talk"
                else None,
                prompt_version=prompt_version(),
                part_chars=parts,
                message_count=len(prep.messages) if prep else 0,
                history_turns=history,
                retrieval=retrieval,
                allowed_catalog_lines=len(allowed_guidance(prep.facts)) if prep else 0,
                allowed_knowledge_lines=len(prep.shown.lines) if prep else 0,
                kept_lines=outcome.kept_lines,
                left_out_lines=outcome.left_out_lines,
                cited_sources=outcome.cited_sources,
                cut_short=outcome.cut_short,
                cancelled=outcome.cancelled,
                timings_ms={
                    "retrieval": prep.retrieval_ms if prep else None,
                    "first_model_piece": since(outcome.first_piece_at),
                    "first_displayed_line": since(outcome.first_line_at),
                    "total": since(time.monotonic()),
                },
                profile=getattr(model, "profile_id", config.llm_profile),
                requested_endpoint=getattr(model, "endpoint_slug", None),
                usage=_usage_metrics(outcome.usage),
                finish_reason=outcome.finish_reason,
                empty_content=outcome.empty_content,
                provider_error_class=outcome.provider_error_class,
                budget=_budget_metrics(outcome.budget),
            )

        recorder.record(build)

    def answer_with_model(prep: Prepared, outcome: _Outcome) -> ChatResponse:
        notice = FALLBACK_NOTICE
        if model is None:
            outcome.fallback_reason = "model_disabled"
        else:
            try:
                reply = model.complete(prep.messages)
                outcome.reported(reply)
                validation = validate_answer(
                    reply.text, prep.facts, knowledge_lines=prep.shown.lines
                )
                outcome.selected(validation)
                if not validation.text:
                    notice = POLICY_NOTICE
                    outcome.fallback_reason = "policy_no_allowed_line"
                    raise LlmUnavailableError("no allowed line in the model reply")
                outcome.cut_short = reply.cut_short
                return outcome.answered(
                    _model_reply(validation, prep, model_name=model.name, cut_short=reply.cut_short)
                )
            except LlmUnavailableError as error:
                outcome.failed(error)
                if outcome.fallback_reason == "none":
                    outcome.fallback_reason = "model_unavailable"
        return outcome.answered(_fallback_reply(prep, notice=notice))

    warmed: dict[str, float] = {}
    warm_lock = threading.Lock()

    def warm_up(facts: dict[str, object]) -> None:
        """Have the model read the rules and this case's facts before the first question.

        Runs after the brief has been sent, so the RM never waits for it. Skipped when the
        same facts were read recently (the model server still has them cached).
        """

        if model is None or not config.llm_warm_up or not is_local_model_url(config.llm_base_url):
            return
        messages = prefix_messages(facts)
        key = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
        now = time.monotonic()
        with warm_lock:
            last = warmed.get(key)
            if last is not None and now - last < config.llm_warm_up_interval_seconds:
                return
            warmed[key] = now
            for old in [k for k, t in warmed.items() if now - t > 3600]:
                del warmed[old]
        model.warm(messages)

    async def stream_answer(
        prep: Prepared,
        started: float,
        finish: Callable[[ChatResponse, _Outcome], ChatResponse],
    ) -> AsyncIterator[str]:
        """The answer as newline-delimited JSON: "text" updates while the model writes,
        then one "done" with the final answer (the same fields as the /chat reply).
        ``finish`` records the answer (only the guard's checked lines) before "done"."""

        def line(event: dict[str, object]) -> str:
            return json.dumps(event, ensure_ascii=False) + "\n"

        def done(response: ChatResponse) -> str:
            # The first answer text the RM sees: a streamed line, else this final answer.
            if outcome.first_line_at is None:
                outcome.first_line_at = time.monotonic()
            return line(
                {"type": "done", **finish(outcome.answered(response), outcome).model_dump()}
            )

        outcome = _Outcome()
        # Set only after the final event was taken by the client; otherwise it disconnected.
        delivered = False
        try:
            notice = FALLBACK_NOTICE
            if model is None:
                outcome.fallback_reason = "model_disabled"
            else:
                guard = StreamingGuard(prep.facts, knowledge_lines=prep.shown.lines)
                cut_short = False
                try:
                    async with aclosing(model.stream(prep.messages)) as source:
                        async for piece in source:
                            if piece.text and outcome.first_piece_at is None:
                                outcome.first_piece_at = time.monotonic()
                            cut_short = cut_short or piece.cut_short
                            outcome.reported(piece)
                            shown = guard.feed(piece.text) if piece.text else None
                            if shown is not None:
                                if outcome.first_line_at is None:
                                    outcome.first_line_at = time.monotonic()
                                yield line({"type": "text", "text": shown})
                    # The length limit reached before any text (reasoning used it all).
                    outcome.empty_content = (
                        outcome.finish_reason == "length" and outcome.first_piece_at is None
                    )
                    guard.finish()
                    validation = guard.validation()
                    outcome.selected(validation)
                    if not validation.text:
                        notice = POLICY_NOTICE
                        outcome.fallback_reason = "policy_no_allowed_line"
                    if validation.text:
                        outcome.cut_short = cut_short
                        yield done(
                            _model_reply(
                                validation, prep, model_name=model.name, cut_short=cut_short
                            )
                        )
                        delivered = True
                        return
                except LlmUnavailableError as error:
                    outcome.failed(error)
                    # Only lines completed before the failure; an unfinished line is not shown.
                    partial = guard.validation()
                    outcome.selected(partial)
                    if partial.text:
                        # Keep what the RM has already read, and say it stopped early.
                        outcome.fallback_reason = "stream_partial"
                        outcome.cut_short = True
                        yield done(
                            _model_reply(partial, prep, model_name=model.name, cut_short=True)
                        )
                        delivered = True
                        return
                    if outcome.fallback_reason == "none":
                        outcome.fallback_reason = "model_unavailable"
            yield done(_fallback_reply(prep, notice=notice))
            delivered = True
        finally:
            outcome.cancelled = not delivered
            emit("stream", started, outcome, prep)

    if knowledge is not None and config.knowledge_enabled:
        from .knowledge_api import knowledge_router

        app.include_router(
            knowledge_router(
                kb=knowledge,
                backend=backend,
                check_origin=check_origin,
                load_case=load_case,
                single_reviewer=config.knowledge_single_reviewer,
                answer_days=config.answer_record_unrated_days,
            )
        )

    @app.get("/assistant/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            llm_enabled=model is not None,
            model=model.name if model is not None else None,
        )

    @app.get("/assistant/cases/{case_id}/brief", response_model=BriefResponse)
    def brief(snapshot: Snapshot, background: BackgroundTasks) -> BriefResponse:
        facts = build_case_facts(snapshot)
        background.add_task(warm_up, facts)
        return BriefResponse(
            company=facts["company"].get("legal_name") or facts["company"].get("uen"),
            message=opening_message(facts),
            suggested_questions=suggested_questions(facts),
            blocker_count=len(facts["blockers"]),
            steps_done=facts["overall"]["steps_done"],
            steps_total=facts["overall"]["steps_total"],
        )

    @app.post("/assistant/cases/{case_id}/chat", response_model=ChatResponse)
    def chat(case_id: UUID, body: ChatRequest, snapshot: Snapshot) -> ChatResponse:
        started = time.monotonic()
        facts = build_case_facts(snapshot)
        question = body.message.strip()[: config.max_question_chars]
        quick = small_talk_reply(question, facts)
        if quick is not None:
            # Greetings and thanks get an instant reply; the model is not called.
            emit("chat", started, _Outcome(fallback_reason="small_talk"), None)
            return ChatResponse(
                answer=quick,
                answered_by="case_data",
                model=None,
                notice=None,
                suggested_questions=suggested_questions(facts),
                small_talk=True,
            )
        prep = prepare(body, snapshot, question)
        outcome = _Outcome()
        response = record(case_id, snapshot, body, prep, answer_with_model(prep, outcome), outcome)
        emit("chat", started, outcome, prep)
        return response

    @app.post("/assistant/cases/{case_id}/chat/stream")
    def chat_stream(case_id: UUID, body: ChatRequest, snapshot: Snapshot) -> StreamingResponse:
        """Like /chat, but the answer appears while the model is still writing it."""

        started = time.monotonic()
        facts = build_case_facts(snapshot)
        question = body.message.strip()[: config.max_question_chars]
        suggestions = suggested_questions(facts)
        quick = small_talk_reply(question, facts)
        if quick is not None:
            emit("stream", started, _Outcome(fallback_reason="small_talk"), None)
            reply = ChatResponse(
                answer=quick,
                answered_by="case_data",
                model=None,
                notice=None,
                suggested_questions=suggestions,
                small_talk=True,
            )
            events: Iterator[str] | AsyncIterator[str] = iter(
                [json.dumps({"type": "done", **reply.model_dump()}, ensure_ascii=False) + "\n"]
            )
        else:
            prep = prepare(body, snapshot, question)

            def finish(response: ChatResponse, outcome: _Outcome) -> ChatResponse:
                return record(case_id, snapshot, body, prep, response, outcome)

            events = stream_answer(prep, started, finish)
        return StreamingResponse(
            events,
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    return app


def _default_knowledge(settings: AiAssistantSettings) -> KnowledgeBase | None:
    """The local knowledge base, or None if it is switched off or cannot be opened."""

    if not settings.knowledge_enabled:
        return None
    try:
        from .knowledge.factory import build_knowledge_base

        kb = build_knowledge_base(settings)
        kb.reconcile()  # index anything approved while the service was down
        return kb
    except Exception:
        log.exception("knowledge base unavailable; answering from case data only")
        return None


_settings = AiAssistantSettings()
app = create_app(_settings, knowledge=_default_knowledge(_settings))
