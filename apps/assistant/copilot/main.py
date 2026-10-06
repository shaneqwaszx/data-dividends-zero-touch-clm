"""Onboarding Copilot API (Phase 1: read-only).

    Browser chat panel -> this service (/assistant/...) -> existing CLM APIs (GET only)
                                                       -> chat model (OpenAI-compatible)

Every request re-reads the case, so answers reflect the case as it is now. The RM's own
session is forwarded to the CLM backend, which stays the authority for access.
"""

from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .briefing import fallback_answer, opening_message, suggested_questions
from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .config import CopilotSettings
from .context import build_case_facts
from .guardrails import guard_answer
from .llm import ChatModel, LlmUnavailableError, OpenAICompatibleChatModel
from .prompts import build_messages


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


class ChatResponse(BaseModel):
    answer: str
    answered_by: Literal["model", "case_data"]
    model: str | None
    notice: str | None
    suggested_questions: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    llm_enabled: bool
    model: str | None


FALLBACK_NOTICE = "The AI model is not available, so this answer comes straight from the case data."


def create_app(
    settings: CopilotSettings | None = None,
    *,
    clm_transport: httpx.BaseTransport | None = None,
    chat_model: ChatModel | None = None,
) -> FastAPI:
    config = settings or CopilotSettings()
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
        )

    app = FastAPI(title="Onboarding Copilot", version="0.1.0")

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
                answer = guard_answer(model.complete(messages), facts)
                if not answer:
                    raise LlmUnavailableError("nothing left after guardrails")
                return ChatResponse(
                    answer=answer,
                    answered_by="model",
                    model=model.name,
                    notice=None,
                    suggested_questions=suggestions,
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

    @app.get("/assistant/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            llm_enabled=model is not None,
            model=model.name if model is not None else None,
        )

    @app.get("/assistant/cases/{case_id}/brief", response_model=BriefResponse)
    def brief(snapshot: Snapshot) -> BriefResponse:
        facts = build_case_facts(snapshot)
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
        return answer_with_model(
            build_messages(facts, history_of(body), question),
            fallback_answer(question, facts),
            suggested_questions(facts),
            facts,
        )

    return app


app = create_app()
