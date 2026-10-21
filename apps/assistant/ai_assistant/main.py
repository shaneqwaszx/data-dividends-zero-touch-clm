"""AI Assistant API (Phase 1: read-only).

    Browser chat panel -> this service (/assistant/...) -> existing CLM APIs (GET only)
                                                       -> chat model (OpenAI-compatible)

Every request re-reads the case, so answers reflect the case as it is now. The RM's own
session is forwarded to the CLM backend, which stays the authority for access.

Opening the panel (/brief) may pre-warm a literal loopback model in the background; the chat panel
uses /chat/stream so the answer appears while it is written (see README "Speed").
"""

import hashlib
import json
import logging
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal
from uuid import UUID

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .briefing import fallback_answer, opening_message, suggested_questions
from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .context import build_case_facts
from .guardrails import LEFT_OUT_REASON, StreamingGuard, Validation, validate_answer
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
from .llm import ChatModel, LlmUnavailableError, OpenAICompatibleChatModel, is_local_model_url
from .prompts import build_messages, prefix_messages
from .small_talk import small_talk_reply


class ChatTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


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

    def sources(self, answer: str) -> list[KnowledgeSource]:
        return [
            KnowledgeSource(**source) for source in sources_for(self.tagged, answer, self.shown)
        ]


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
) -> FastAPI:
    config = settings or AiAssistantSettings()
    retriever = (
        Retriever(knowledge, settings_from(config))
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
        model = OpenAICompatibleChatModel(
            base_url=config.llm_base_url,
            model=config.llm_model,
            credential=config.llm_api_key.get_secret_value(),
            timeout_seconds=config.llm_timeout_seconds,
            temperature=config.llm_temperature,
            max_answer_tokens=config.llm_max_answer_tokens,
        )

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

    def prepare(body: ChatRequest, snapshot: CaseSnapshot, question: str) -> Prepared:
        facts = build_case_facts(snapshot)
        tagged: list[TaggedHit] = []
        use: KnowledgeUse | None = None
        profile = snapshot.actor.get("profile") or {}
        role, team = profile.get("role"), profile.get("team_id")
        if retriever is not None:
            try:
                retrieval = retriever.retrieve(question, case_context(facts), role=role, team=team)
                tagged = approved_knowledge(tag_hits(retrieval), role=role, team=team)
                use = KnowledgeUse(confidence=retrieval.confidence, degraded=retrieval.degraded)
            except Exception:  # knowledge is optional: never let it break an answer
                log.exception("knowledge retrieval failed")
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
        return Prepared(
            facts=facts,
            messages=build_messages(
                facts, history_of(body), question, knowledge=knowledge_message(tagged, shown)
            ),
            fallback=fallback,
            suggestions=suggestions[:6],
            tagged=tagged,
            knowledge=use,
            shown=shown,
        )

    def answer_with_model(prep: Prepared) -> ChatResponse:
        notice = FALLBACK_NOTICE
        if model is not None:
            try:
                reply = model.complete(prep.messages)
                validation = validate_answer(
                    reply.text, prep.facts, knowledge_lines=prep.shown.lines
                )
                if not validation.text:
                    notice = POLICY_NOTICE
                    raise LlmUnavailableError("no allowed line in the model reply")
                return _model_reply(
                    validation, prep, model_name=model.name, cut_short=reply.cut_short
                )
            except LlmUnavailableError:
                pass
        return _fallback_reply(prep, notice=notice)

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

    async def stream_answer(prep: Prepared) -> AsyncIterator[str]:
        """The answer as newline-delimited JSON: "text" updates while the model writes,
        then one "done" with the final answer (the same fields as the /chat reply)."""

        def line(event: dict[str, object]) -> str:
            return json.dumps(event, ensure_ascii=False) + "\n"

        def done(response: ChatResponse) -> str:
            return line({"type": "done", **response.model_dump()})

        notice = FALLBACK_NOTICE
        if model is not None:
            guard = StreamingGuard(prep.facts, knowledge_lines=prep.shown.lines)
            cut_short = False
            try:
                async with aclosing(model.stream(prep.messages)) as source:
                    async for piece in source:
                        cut_short = cut_short or piece.cut_short
                        shown = guard.feed(piece.text) if piece.text else None
                        if shown is not None:
                            yield line({"type": "text", "text": shown})
                guard.finish()
                validation = guard.validation()
                if not validation.text:
                    notice = POLICY_NOTICE
                if validation.text:
                    yield done(
                        _model_reply(validation, prep, model_name=model.name, cut_short=cut_short)
                    )
                    return
            except LlmUnavailableError:
                # Only lines completed before the failure; an unfinished line is not shown.
                partial = guard.validation()
                if partial.text:
                    # Keep what the RM has already read, and say it stopped early.
                    yield done(_model_reply(partial, prep, model_name=model.name, cut_short=True))
                    return
        yield done(_fallback_reply(prep, notice=notice))

    if knowledge is not None and config.knowledge_enabled:
        from .knowledge_api import knowledge_router

        app.include_router(
            knowledge_router(
                kb=knowledge,
                backend=backend,
                check_origin=check_origin,
                load_case=load_case,
                single_reviewer=config.knowledge_single_reviewer,
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
    def chat(body: ChatRequest, snapshot: Snapshot) -> ChatResponse:
        facts = build_case_facts(snapshot)
        question = body.message.strip()[: config.max_question_chars]
        quick = small_talk_reply(question, facts)
        if quick is not None:
            # Greetings and thanks get an instant reply; the model is not called.
            return ChatResponse(
                answer=quick,
                answered_by="case_data",
                model=None,
                notice=None,
                suggested_questions=suggested_questions(facts),
            )
        return answer_with_model(prepare(body, snapshot, question))

    @app.post("/assistant/cases/{case_id}/chat/stream")
    def chat_stream(body: ChatRequest, snapshot: Snapshot) -> StreamingResponse:
        """Like /chat, but the answer appears while the model is still writing it."""

        facts = build_case_facts(snapshot)
        question = body.message.strip()[: config.max_question_chars]
        suggestions = suggested_questions(facts)
        quick = small_talk_reply(question, facts)
        if quick is not None:
            reply = ChatResponse(
                answer=quick,
                answered_by="case_data",
                model=None,
                notice=None,
                suggested_questions=suggestions,
            )
            events: Iterator[str] | AsyncIterator[str] = iter(
                [json.dumps({"type": "done", **reply.model_dump()}, ensure_ascii=False) + "\n"]
            )
        else:
            events = stream_answer(prepare(body, snapshot, question))
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
