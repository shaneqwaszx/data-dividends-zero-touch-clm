"""AI Assistant API (Phase 1: read-only).

    Browser chat panel -> this service (/assistant/...) -> existing CLM APIs (GET only)
                                                       -> chat model (OpenAI-compatible)

Every request re-reads the case, so answers reflect the case as it is now. The RM's own
session is forwarded to the CLM backend, which stays the authority for access.

Opening the panel (/brief) also pre-warms the model in the background, and the chat panel
uses /chat/stream so the answer appears while it is written (see README "Speed").
"""

import hashlib
import json
import threading
import time
from collections.abc import Iterator
from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .briefing import fallback_answer, opening_message, suggested_questions
from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings
from .context import build_case_facts
from .guardrails import StreamingGuard, Validation, validate_answer
from .llm import ChatModel, LlmUnavailableError, OpenAICompatibleChatModel
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
    """What grounding and policy validation did to a model answer (reason codes only)."""

    removed: list[str]
    disclosures: list[str]


class ChatResponse(BaseModel):
    answer: str
    answered_by: Literal["model", "case_data"]
    model: str | None
    notice: str | None
    suggested_questions: list[str]
    # Set for model answers: why sentences were left out, and the disclosures added.
    checks: AnswerChecks | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    llm_enabled: bool
    model: str | None


FALLBACK_NOTICE = "The AI model is not available, so this answer comes straight from the case data."
CUT_SHORT_NOTICE = "This answer was cut short. Ask me to continue for the rest."


def _model_reply(
    validation: Validation, *, model_name: str, cut_short: bool, suggestions: list[str]
) -> "ChatResponse":
    notices = [n for n in (validation.notice(), CUT_SHORT_NOTICE if cut_short else None) if n]
    return ChatResponse(
        answer=validation.text,
        answered_by="model",
        model=model_name,
        notice=" ".join(notices) or None,
        suggested_questions=suggestions,
        checks=AnswerChecks(
            removed=list(validation.removed), disclosures=list(validation.disclosures)
        ),
    )


def create_app(
    settings: AiAssistantSettings | None = None,
    *,
    clm_transport: httpx.BaseTransport | None = None,
    chat_model: ChatModel | None = None,
) -> FastAPI:
    config = settings or AiAssistantSettings()
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

    def answer_with_model(
        messages: list[dict[str, str]],
        fallback: str,
        suggestions: list[str],
        facts: dict[str, object],
    ) -> ChatResponse:
        if model is not None:
            try:
                reply = model.complete(messages)
                validation = validate_answer(reply.text, facts)
                if not validation.text:
                    raise LlmUnavailableError("nothing left after validation")
                return _model_reply(
                    validation,
                    model_name=model.name,
                    cut_short=reply.cut_short,
                    suggestions=suggestions,
                )
            except LlmUnavailableError:
                pass
        return ChatResponse(
            answer=fallback,
            answered_by="case_data",
            model=None,
            notice=FALLBACK_NOTICE,
            suggested_questions=suggestions,
        )

    warmed: dict[str, float] = {}
    warm_lock = threading.Lock()

    def warm_up(facts: dict[str, object]) -> None:
        """Have the model read the rules and this case's facts before the first question.

        Runs after the brief has been sent, so the RM never waits for it. Skipped when the
        same facts were read recently (the model server still has them cached).
        """

        if model is None or not config.llm_warm_up:
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

    def stream_answer(
        messages: list[dict[str, str]],
        fallback: str,
        suggestions: list[str],
        facts: dict[str, object],
    ) -> Iterator[str]:
        """The answer as newline-delimited JSON: "text" updates while the model writes,
        then one "done" with the final answer (the same fields as the /chat reply)."""

        def line(event: dict[str, object]) -> str:
            return json.dumps(event, ensure_ascii=False) + "\n"

        def done(response: ChatResponse) -> str:
            return line({"type": "done", **response.model_dump()})

        if model is not None:
            guard = StreamingGuard(facts)
            cut_short = False
            try:
                for piece in model.stream(messages):
                    cut_short = cut_short or piece.cut_short
                    shown = guard.feed(piece.text) if piece.text else None
                    if shown is not None:
                        yield line({"type": "text", "text": shown})
                validation = guard.finish()
                if validation.text:
                    yield done(
                        _model_reply(
                            validation,
                            model_name=model.name,
                            cut_short=cut_short,
                            suggestions=suggestions,
                        )
                    )
                    return
            except LlmUnavailableError:
                partial = guard.finish()
                if partial.text:
                    # Keep what the RM has already read, and say it stopped early.
                    yield done(
                        _model_reply(
                            partial, model_name=model.name, cut_short=True, suggestions=suggestions
                        )
                    )
                    return
        yield done(
            ChatResponse(
                answer=fallback,
                answered_by="case_data",
                model=None,
                notice=FALLBACK_NOTICE,
                suggested_questions=suggestions,
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
        return answer_with_model(
            build_messages(facts, history_of(body), question),
            fallback_answer(question, facts),
            suggested_questions(facts),
            facts,
        )

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
            events: Iterator[str] = iter(
                [json.dumps({"type": "done", **reply.model_dump()}, ensure_ascii=False) + "\n"]
            )
        else:
            events = stream_answer(
                build_messages(facts, history_of(body), question),
                fallback_answer(question, facts),
                suggestions,
                facts,
            )
        return StreamingResponse(
            events,
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
