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
import re
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import aclosing
from dataclasses import dataclass, field
from dataclasses import replace as replaced
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from . import copilot, hosted_insights
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
from .anthropic_runtime import NOTICES as CLAUDE_NOTICES
from .anthropic_runtime import Notices, hosted_chat, hosted_deployment
from .briefing import fallback_answer, opening_message, suggested_questions
from .case_contexts import CONTEXT_ID, ContextRefused, ContextStore, Ticket
from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .config import AiAssistantSettings, external_conversational
from .config import conversational as config_conversational
from .context import build_case_facts
from .dashboard_insights import (
    DashboardInsights,
    InsightFinding,
    InsightsRejected,
    InsightsRequest,
    InsightsResponse,
    InsightsUnavailable,
    check_reply,
)
from .data_access import REFUSAL_NOTICES as POLICY_REFUSALS
from .guardrails import (
    LEFT_OUT_REASON,
    StreamingGuard,
    Validation,
    allowed_guidance,
    validate_answer,
    with_required_lines,
)
from .knowledge.models import Entry, EntryKind, EntryStatus
from .knowledge.redaction import Redactor, case_parties
from .knowledge.retrieval import Hit, Retriever, case_context, settings_from
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
    collect_stream,
    is_local_model_url,
    micro_usd,
)
from .model_admin import Active, model_admin_router, open_selector
from .model_factory import build_chat_model
from .prompts import TopicPlan, build_messages, prefix_messages, topic_plan
from .provider_payload import (
    anthropic_bound,
    identities,
    provider_bound,
    provider_facts,
    scrub,
    scrub_text,
)
from .remote_test import hosted_deployment as gptoss_hosted_deployment
from .remote_test import is_remote_test_model
from .request_rate import MINUTE_LIMIT, UserRate, hourly_limit
from .small_talk import small_talk_reply
from .support_chat import answer_support_question
from .synthetic_boundary import approved_entry
from .synthetic_boundary import check as synthetic_boundary_check
from .synthetic_eligibility import approve as synthetic_eligibility_approve
from .synthetic_eligibility import check as synthetic_eligibility_check
from .synthetic_eligibility import mode as synthetic_dev_mode
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
    # The conversation this question continues (D-105). Kept only when it is this user's open
    # conversation on this case; otherwise the answer starts a new one.
    conversation_id: str | None = Field(default=None, pattern=ANSWER_ID)
    # D-115: the chat context this question belongs to. When given, its server-held turns are
    # the only history used (the browser's history text is ignored), and it must be this
    # user's context on this case.
    context_id: str | None = Field(default=None, pattern=CONTEXT_ID)


class ContextOpenRequest(BaseModel):
    """D-115: open a chat context on a case, or (case_id left out) the general chat."""

    model_config = ConfigDict(extra="forbid")

    case_id: UUID | None = None


class ContextResponse(BaseModel):
    context_id: str
    scope: Literal["case", "general"]
    case_id: str | None
    idle_seconds: int


class GeneralChatRequest(BaseModel):
    """D-115: a question in the general onboarding chat (no case), within its context."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    context_id: str = Field(pattern=CONTEXT_ID)


class SupportChatRequest(BaseModel):
    """Support's question without a case (D-105): only the question and the chat so far."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


class TryChangeRequest(BaseModel):
    """An unsaved rule change to preview on a rated conversation's question (D-105)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["guidance", "resolution"] = "guidance"
    title: str = Field(default="", max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    entry_id: str | None = Field(default=None, max_length=90)
    blocker_codes: list[Annotated[str, Field(max_length=80)]] | None = Field(
        default=None, max_length=20
    )
    fields: list[Annotated[str, Field(max_length=80)]] | None = Field(default=None, max_length=20)
    stages: list[Annotated[str, Field(max_length=80)]] | None = Field(default=None, max_length=20)
    # Another question to try; the conversation's first question when left out.
    question: str | None = Field(default=None, max_length=600)


# Support's chat without a case reads the approved rules and the policy (D-105).
SUPPORT_CHAT_CAPABILITY = "KNOWLEDGE_REVIEW"


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
    # Positions (0-based) of answer lines the service added as the topic's required lines,
    # not chosen by the model (D-090). Positions only, never text.
    added_lines: list[int] = Field(default_factory=list)
    # The server's record of this answer (none for small talk, or with the knowledge store
    # off); "Not helpful" sends it back.
    answer_id: str | None = None
    # The conversation the answer record joined (D-105); "End conversation" rates it.
    conversation_id: str | None = None
    # A fixed small-talk reply: it never has a record, so a missing answer_id is expected.
    small_talk: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok"]
    llm_enabled: bool
    model: str | None
    # D-115: how answers are written, and whether the general (no case) chat is offered.
    answer_mode: Literal["exact_lines", "copilot"] = "exact_lines"
    general_chat: bool = False


FALLBACK_NOTICE = "The AI model is not available, so this answer comes straight from the case data."
POLICY_NOTICE = "The model response could not be verified, so this answer comes from the case data."
CUT_SHORT_NOTICE = "This answer was cut short. Ask me to continue for the rest."
# D-094 local synthetic test mode (remote_test.py): which model answered, or why it did not.
REMOTE_NOTICE = "Answered by GPT-OSS 120B through OpenRouter (D-094 local synthetic test mode)."
REMOTE_BOUNDARY_NOTICE = (
    "GPT-OSS 120B through OpenRouter is used only on the approved synthetic test case, so this "
    "answer comes straight from the case data."
)
# D-095 development synthetic mode (synthetic_eligibility.py).
REMOTE_DEV_NOTICE = (
    "Answered by GPT-OSS 120B through OpenRouter (D-095 development mode, verified synthetic case)."
)
REMOTE_ELIGIBILITY_NOTICE = (
    "GPT-OSS 120B through OpenRouter is used only on verified synthetic development cases, so "
    "this answer comes straight from the case data."
)
# D-099 Option B: a Claude configuration brings its own notices (anthropic_runtime.NOTICES).
REMOTE_NOTICES = Notices(
    answered=REMOTE_NOTICE,
    boundary=REMOTE_BOUNDARY_NOTICE,
    dev_answered=REMOTE_DEV_NOTICE,
    eligibility=REMOTE_ELIGIBILITY_NOTICE,
)
# D-139: on the hosted service a case's content goes to an external provider only when its data
# is verified synthetic by provenance; otherwise the answer comes from the case data.
HOSTED_ELIGIBILITY_NOTICES = {
    "anthropic": (
        "Claude Sonnet 5.5 through Anthropic is used only on cases whose data is verified "
        "synthetic, so this answer comes straight from the case data."
    ),
    "openrouter": (
        "GPT-OSS 120B through OpenRouter is used only on cases whose data is verified "
        "synthetic, so this answer comes straight from the case data."
    ),
}
_REMOTE_REFUSALS = (
    *HOSTED_ELIGIBILITY_NOTICES.values(),
    REMOTE_BOUNDARY_NOTICE,
    REMOTE_ELIGIBILITY_NOTICE,
    CLAUDE_NOTICES.boundary,
    CLAUDE_NOTICES.eligibility,
    # D-104: a local or IT-configured model under the data access policy says so (QG L1).
    *POLICY_REFUSALS,
)


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
    # The question's topic: model answers always include its required lines (D-090).
    plan: TopicPlan | None = None
    # How long knowledge retrieval took (metrics only).
    retrieval_ms: int | None = None
    # The question as the model got it (after the max_question_chars cut), and when work on
    # it started (time.monotonic), for the answer record.
    question: str = ""
    started: float = 0.0
    # Written in the model's own words and checked sentence by sentence (copilot), not
    # selected from offered lines.
    conversational: bool = False
    # D-130 OD-G8: the identifiers kept out of a Claude-bound prompt (None: not Claude-bound).
    provider_names: tuple[str, ...] | None = None

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
    # The model this answer uses: one snapshot of the active model, taken when the request
    # starts and kept to the end (model management, D-093, may switch it between requests).
    model: ChatModel | None = None

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
        if self.fallback_reason in (
            "model_disabled",
            "model_unavailable",
            "budget_refused",
            "remote_boundary",
        ):
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
    validation: Validation,
    prep: Prepared,
    *,
    model_name: str,
    cut_short: bool,
    streamed: str = "",
    lead_notice: str | None = None,
) -> "ChatResponse":
    """The model's answer; ``streamed`` is the answer text the RM has already been shown;
    ``lead_notice`` names the model when the RM must be told (D-094)."""

    chosen = set(validation.text.splitlines())
    if prep.plan is not None:
        validation = with_required_lines(
            validation,
            prep.facts,
            order=prep.plan.lines,
            required=prep.plan.required,
            streamed=streamed.splitlines(),
        )
    notices = [
        n for n in (lead_notice, validation.notice(), CUT_SHORT_NOTICE if cut_short else None) if n
    ]
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
        added_lines=[
            index for index, line in enumerate(validation.text.splitlines()) if line not in chosen
        ],
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
    baseline: ChatModel | None = chat_model
    if baseline is None and config.llm_enabled:
        # The default profile builds the same adapter as before; the remote profile is
        # dormant and refuses to start here (model_factory.py).
        baseline = build_chat_model(config, local_adapter=OpenAICompatibleChatModel)
    # One application-wide active model (D-093). Fixed to the baseline unless IT configured
    # model management; a model passed in (tests, the evaluation harness) is always fixed.
    selector = open_selector(config, baseline, injected=chat_model is not None)

    app = FastAPI(title="AI Assistant", version="0.1.0")
    app.state.model_selector = selector
    # D-115: chat memory, per user and case, in this process only.
    contexts = ContextStore(
        idle_seconds=config.context_idle_seconds,
        max_seconds=config.context_max_seconds,
        max_turns=config.context_max_turns,
        max_per_user=config.context_max_per_user,
    )
    app.state.contexts = contexts

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
            snapshot = backend.load_case(case_id, request.cookies.get(SESSION_COOKIE_NAME))
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        # D-139: model-free guidance serves every case the backend let this user read (its 401,
        # 403 and safe 404 above decide). Whether this case's content may go to an external
        # model is decided separately, per answer, before any call (hosted_refusal).
        return snapshot

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
        # D-105: Support's investigation chat on a review page (no CASE_ACCESS, only the
        # read-only redaction access) is not a user conversation: nothing is recorded.
        if "CASE_ACCESS" not in (profile.get("capabilities") or []):
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
            saved = answers.save(
                {
                    "id": new_answer_id(),
                    "case_id": str(case_id),
                    "user_id": str(user),
                    "team": profile.get("team_id"),
                    "role": profile.get("role"),
                    "conversation_id": body.conversation_id,
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
                    # Redacted: since D-090 catalog lines can carry ACRA and document values
                    # (ADR-012 section A allows a record no case values beyond the snapshot).
                    "allowed_lines": allowed_lines(prep.facts, prep.shown.lines, redact),
                    # Model answers only: the checked lines the RM was shown, redacted alike.
                    "chosen_lines": (
                        [redact(line) for line in response.answer.splitlines()]
                        if response.answered_by == "model"
                        else []
                    ),
                    # The answer as the RM saw it, redacted: a case-data answer is filled from
                    # the case, and a model answer's catalog lines can be too.
                    "shown_answer": redact(response.answer),
                    "dropped_lines": (
                        capped_dropped(validation.dropped, redact) if validation else []
                    ),
                    "result": {
                        "answered_by": response.answered_by,
                        "notices": [response.notice] if response.notice else [],
                        "fallback_reason": outcome.record_reason(),
                        "left_out": validation.left_out if validation else 0,
                        "model": outcome.model.name if outcome.model is not None else None,
                        "elapsed_ms": round((time.monotonic() - prep.started) * 1000),
                    },
                }
            )
        except Exception:  # a record must never break the answer
            log.exception("answer record failed")
            return response
        if saved is None:
            return response
        answer_id, conversation_id = saved
        return response.model_copy(
            update={"answer_id": answer_id, "conversation_id": conversation_id}
        )

    def prepare(
        body: ChatRequest,
        snapshot: CaseSnapshot,
        question: str,
        *,
        remote: bool = False,
        trial: Entry | None = None,
        history: list[dict[str, str]] | None = None,
        names: tuple[str, ...] | None = None,
    ) -> Prepared:
        """``remote``: the active model is the D-094 remote test model, so only repository
        guidance and the synthetic seed, unchanged, may be used (synthetic_boundary.py).
        ``names``: D-130 OD-G8, the prompt goes to Anthropic, so it carries the viewer's role
        only and none of these identifiers (provider_payload)."""

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
                found = approved_knowledge(tag_hits(retrieval), role=role, team=team)
                if remote:
                    # Filtered before it is kept: a failing check leaves no knowledge at all.
                    found = [item for item in found if approved_entry(item.hit.entry)]
                tagged = found
                use = KnowledgeUse(confidence=retrieval.confidence, degraded=retrieval.degraded)
            except Exception:  # knowledge is optional: never let it break an answer
                log.exception("knowledge retrieval failed")
            retrieval_ms = round((time.monotonic() - began) * 1000)
        if trial is not None:
            # D-105 "Try with this change": Support's unsaved rule, offered as if approved,
            # first, in place of the version it would replace; for this preview only.
            tagged = [item for item in tagged if item.hit.entry.entry_id != trial.entry_id]
            letter = "G" if trial.kind == EntryKind.GUIDANCE else "P"
            taken = {item.tag for item in tagged}
            number = 1
            while f"{letter}{number}" in taken:
                number += 1
            hit = Hit(entry=trial, score=1.0, parts={})
            tagged = [TaggedHit(f"{letter}{number}", hit), *tagged]
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
        messages = build_messages(
            facts if names is None else provider_facts(facts, names),
            history_of(body) if history is None else history,
            question,
            knowledge=knowledge_message(tagged, shown),
        )
        prepared = Prepared(
            facts=facts,
            messages=messages if names is None else scrub(messages, names),
            fallback=fallback,
            suggestions=suggestions[:6],
            tagged=tagged,
            knowledge=use,
            shown=shown,
            plan=topic_plan(facts, question),
            retrieval_ms=retrieval_ms,
            question=question,
            started=started,
            provider_names=names,
        )
        if on_prepared is not None:
            on_prepared(prepared)
        return prepared

    def names_for(model: ChatModel | None, *profiles: Any, extra: tuple[Any, ...] = ()) -> (
        tuple[str, ...] | None
    ):
        # D-130 OD-G8: the identifiers to keep out of this model's prompt, if it is Claude-bound
        # (D-134: or GPT-OSS on its registered hosted deployment).
        if not provider_bound(model):
            return None
        return identities(*profiles, extra=extra)

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
                model=outcome.model.name
                if outcome.model is not None and outcome.fallback_reason != "small_talk"
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
                profile=getattr(outcome.model, "profile_id", config.llm_profile),
                requested_endpoint=getattr(outcome.model, "endpoint_slug", None),
                usage=_usage_metrics(outcome.usage),
                finish_reason=outcome.finish_reason,
                empty_content=outcome.empty_content,
                provider_error_class=outcome.provider_error_class,
                budget=_budget_metrics(outcome.budget),
            )

        recorder.record(build)

    gptoss_rate = UserRate()

    def gptoss_rate_refused(model: ChatModel | None, user: str) -> bool:
        # D-134 (proposed): hosted GPT-OSS only. Claude, local models and a development machine
        # are never rate-limited here.
        hosted = gptoss_hosted_deployment()
        reservation = getattr(model, "worst_case_reservation", None)
        if hosted is None or reservation is None:
            return False
        return not gptoss_rate.admit(
            user,
            per_minute=MINUTE_LIMIT,
            per_hour=hourly_limit(hosted.daily_ceiling_micro_usd, reservation()),
        )

    def hosted_refusal(
        model: ChatModel | None,
        snapshot: CaseSnapshot,
        prep: Prepared,
        case_id: UUID,
        session: str | None,
        *,
        trial: Entry | None = None,
    ) -> str | None:
        """D-139: None when this case's exact messages may go to the hosted external model (they
        then hold a ticket); otherwise the lead notice, ending in the closed reason code. The
        document digests are read only here, with the user's own session."""

        try:
            digests = backend.load_document_digests(case_id, session) if snapshot.documents else []
        except ClmBackendError:
            digests = None
        # Try with this change: Support's unsaved rule is governed by D-130's redaction and
        # exact-line rules, not by the approved-knowledge list; everything else is checked.
        entries = [item.hit.entry for item in prep.tagged if item.hit.entry is not trial]
        refusal = synthetic_eligibility_check(
            snapshot, prep.facts, prep.messages, entries, digests=digests, viewer=trial is None
        )
        if refusal is None:
            return None
        record = getattr(app.state.case_gate, "record", None)
        if callable(record):
            record(case_id, refusal)
        else:
            log.info("external inference not used: %s", refusal)
        provider = "anthropic" if anthropic_bound(model) else "openrouter"
        return f"{HOSTED_ELIGIBILITY_NOTICES[provider]} Reason: {refusal}."

    def remote_gate(
        active: Active,
        snapshot: CaseSnapshot,
        prep: Prepared,
        case_id: UUID,
        session: str | None,
    ) -> tuple[ChatModel | None, str | None]:
        """The model this answer may use, and the lead notice. The D-094 remote test model is
        used only when the whole prompt is inside the synthetic boundary (D-095 mode: the case
        is a verified synthetic development case); otherwise nothing is sent and the RM gets
        the case-data answer (notice REMOTE_BOUNDARY_NOTICE or REMOTE_ELIGIBILITY_NOTICE,
        followed by the closed reason code, never a value)."""

        if not is_remote_test_model(active.model):
            return active.model, None
        if gptoss_rate_refused(active.model, user_of(snapshot)):
            # D-134: over this user's request rate. Nothing is sent or reserved; the answer is
            # the case-data one, as when no model is available.
            log.info("hosted GPT-OSS not used: request rate")
            return None, None
        notices: Notices = getattr(active.model, "notices", REMOTE_NOTICES)
        if getattr(app.state, "case_gate", None) is not None:
            # D-139: the hosted service sends this case only when its data is verified synthetic
            # (the D-095 check, which issues the per-call ticket for these exact messages).
            refusal = hosted_refusal(active.model, snapshot, prep, case_id, session)
            if refusal is not None:
                return None, refusal
            return active.model, getattr(active.model, "attribution", None)
        if external_conversational(config):
            # D-122: any case. The per-call ticket stays, so only these exact messages go.
            synthetic_eligibility_approve(prep.messages)
            # R2.2: a hosted Claude answer names its model (only on what the model wrote).
            return active.model, getattr(active.model, "attribution", None)
        entries = [item.hit.entry for item in prep.tagged]
        # D-104 A1: a model that decides D-095 mode itself (Claude, a policy-restricted model)
        # does so on the shared interlocks; GPT-OSS keeps the OpenRouter-ready mode.
        development = getattr(active.model, "development_mode", None)
        if development() if development is not None else synthetic_dev_mode(config):
            # D-095: any verified synthetic development case, by provenance. The document
            # digests are read only here, with the RM's own session.
            digests = backend.load_document_digests(case_id, session) if snapshot.documents else []
            refusal = synthetic_eligibility_check(
                snapshot, prep.facts, prep.messages, entries, digests=digests
            )
            if refusal is not None:
                log.info("remote test model not used: %s", refusal)
                return None, f"{notices.eligibility} Reason: {refusal}."
            return active.model, notices.dev_answered
        refusal = synthetic_boundary_check(snapshot, prep.facts, prep.messages, entries)
        if refusal is not None:
            log.info("remote test model not used: %s", refusal)
            return None, f"{notices.boundary} Reason: {refusal}."
        return active.model, notices.answered

    def answer_with_model(
        prep: Prepared, outcome: _Outcome, lead: str | None = None, *, collect: bool = False
    ) -> ChatResponse:
        """``collect``: D-130, the model is streaming only (hosted Claude), so its whole
        streamed answer is taken (llm.collect_stream) and checked exactly like a reply."""

        notice = FALLBACK_NOTICE
        model = outcome.model
        if model is None and lead is not None and lead.startswith(_REMOTE_REFUSALS):
            notice = lead
            outcome.fallback_reason = "remote_boundary"
        elif model is None:
            outcome.fallback_reason = "model_disabled"
        else:
            try:
                reply = (
                    collect_stream(model, prep.messages)
                    if collect
                    else model.complete(prep.messages)
                )
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
                    _model_reply(
                        validation,
                        prep,
                        model_name=model.name,
                        cut_short=reply.cut_short,
                        lead_notice=lead,
                    )
                )
            except LlmUnavailableError as error:
                outcome.failed(error)
                if outcome.fallback_reason == "none":
                    outcome.fallback_reason = "model_unavailable"
        return outcome.answered(_fallback_reply(prep, notice=notice))

    warmed: dict[str, float] = {}
    warm_lock = threading.Lock()

    def warm_up(facts: dict[str, object], active: Active) -> None:
        """Have the model read the rules and this case's facts before the first question.

        Runs after the brief has been sent, so the RM never waits for it. Skipped when the
        same facts were read recently (the model server still has them cached).
        """

        model = active.model
        if model is None or not config.llm_warm_up or not is_local_model_url(active.base_url or ""):
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
        model: ChatModel | None,
        lead: str | None = None,
    ) -> AsyncIterator[str]:
        """The answer as newline-delimited JSON: "text" updates while the model writes,
        then one "done" with the final answer (the same fields as the /chat reply).
        ``finish`` records the answer (only the guard's checked lines) before "done".
        ``lead``: the D-094 notice (``remote_gate``)."""

        def line(event: dict[str, object]) -> str:
            return json.dumps(event, ensure_ascii=False) + "\n"

        def done(response: ChatResponse) -> str:
            # The first answer text the RM sees: a streamed line, else this final answer.
            if outcome.first_line_at is None:
                outcome.first_line_at = time.monotonic()
            return line(
                {"type": "done", **finish(outcome.answered(response), outcome).model_dump()}
            )

        outcome = _Outcome(model=model)
        # Set only after the final event was taken by the client; otherwise it disconnected.
        delivered = False
        try:
            notice = FALLBACK_NOTICE
            if model is None and lead is not None and lead.startswith(_REMOTE_REFUSALS):
                notice = lead
                outcome.fallback_reason = "remote_boundary"
            elif model is None:
                outcome.fallback_reason = "model_disabled"
            else:
                guard = StreamingGuard(prep.facts, knowledge_lines=prep.shown.lines)
                cut_short = False
                streamed = ""  # what the RM has been shown so far
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
                                streamed = shown
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
                                validation,
                                prep,
                                model_name=model.name,
                                cut_short=cut_short,
                                streamed=streamed,
                                lead_notice=lead,
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
                            _model_reply(
                                partial,
                                prep,
                                model_name=model.name,
                                cut_short=True,
                                streamed=streamed,
                                lead_notice=lead,
                            )
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

    # --- D-115 copilot answers and chat contexts ---------------------------------------------

    def synthetic_only_conversation(active: Active) -> bool:
        # An external or policy-restricted model answers in its own words only in D-095 mode:
        # each question is re-checked as a verified synthetic development case (remote_gate,
        # synthetic_eligibility) before anything is sent. In D-094 mode it keeps exact lines.
        development = getattr(active.model, "development_mode", None)
        return bool(development() if development is not None else synthetic_dev_mode(config))

    def copilot_for(active: Active) -> bool:
        """Conversational answers when approved (config.conversational): any model on any
        case it may read (D-122), with exact lines otherwise."""

        if not config_conversational(config) or active.model is None:
            return False
        if not is_remote_test_model(active.model):
            return True
        return external_conversational(config)

    def context_refused(refused: ContextRefused) -> HTTPException:
        return HTTPException(
            409,
            detail={
                "code": refused.code,
                "message": "This chat has ended. Start a new chat to continue.",
            },
        )

    def ticket_for(context_id: str | None, user: str, case_id: str | None) -> Ticket | None:
        if context_id is None:
            return None
        try:
            return contexts.ticket(context_id, user, case_id)
        except ContextRefused as refused:
            raise context_refused(refused) from None

    def user_of(snapshot: CaseSnapshot) -> str:
        return str((snapshot.actor.get("profile") or {}).get("user_id") or "")

    def history_for(body: ChatRequest, ticket: Ticket | None) -> list[dict[str, str]]:
        if ticket is None:
            return history_of(body)
        limit = config.max_history_messages
        return [dict(turn) for turn in ticket.history][-limit:] if limit else []

    def off_domain(suggestions: list[str]) -> ChatResponse:
        return ChatResponse(
            answer=copilot.OFF_DOMAIN_REPLY,
            answered_by="case_data",
            model=None,
            notice=None,
            suggested_questions=suggestions,
        )

    def with_ownership(prep: Prepared, case_id: UUID, request: Request) -> Prepared:
        """Conversational answers only: the application's ownership analysis joins the case
        facts, read with the user's own session (the backend decides access). Without it, the
        ownership figures are reported as not available and no percentage is grounded."""

        analysis = backend.load_ownership(case_id, request.cookies.get(SESSION_COOKIE_NAME))
        return replaced(prep, facts={**prep.facts, "ownership": copilot.ownership_facts(analysis)})

    def local_ownership(
        prep: Prepared, case_id: UUID, request: Request, remote: bool
    ) -> Prepared:
        # D-115 X2: without D-122 an external model never gets the ownership analysis.
        if remote and not external_conversational(config):
            return prep
        return with_ownership(prep, case_id, request)

    def refused_outcome(lead: str | None) -> _Outcome:
        # The case-data answer when no model may be used, with the reason recorded as in the
        # exact-line path (answer_with_model): the external boundary, or no model.
        refused = lead is not None and lead.startswith(_REMOTE_REFUSALS)
        return _Outcome(fallback_reason="remote_boundary" if refused else "model_disabled")

    def copilot_prep(prep: Prepared, history: list[dict[str, str]]) -> tuple[Prepared, list[str]]:
        names = prep.provider_names
        messages = copilot.build_messages(
            prep.facts if names is None else provider_facts(prep.facts, names),
            history,
            prep.question,
            knowledge=copilot.knowledge_message(prep.tagged, prep.shown),
        )
        if names is not None:
            messages = scrub(messages, names)
        line = copilot.read_only_line(prep.question)
        prepared = replaced(prep, messages=messages, plan=None, conversational=True)
        if on_prepared is not None:
            on_prepared(prepared)  # the evaluation harness sees the prompt actually sent
        return prepared, [line] if line else []

    def copilot_reply(
        check: copilot.CopilotCheck,
        prep: Prepared,
        outcome: _Outcome,
        *,
        model_name: str,
        cut_short: bool,
        required: list[str],
        lead: str | None = None,
    ) -> ChatResponse:
        outcome.kept_lines = check.kept
        outcome.left_out_lines = len(check.left_out)
        outcome.cut_short = cut_short
        notices = [
            lead,
            copilot.REMOVED_NOTICE.format(count=len(check.left_out)) if check.left_out else None,
            CUT_SHORT_NOTICE if cut_short else None,
        ]
        return outcome.answered(
            ChatResponse(
                answer=check.text,
                answered_by="model",
                model=model_name,
                notice=" ".join(n for n in notices if n) or None,
                suggested_questions=prep.suggestions,
                checks=AnswerChecks(removed=sorted(set(check.left_out)), disclosures=[]),
                sources=prep.sources(check.text),
                knowledge=prep.knowledge,
                added_lines=[0] if required else [],
            )
        )

    def copilot_fallback(
        prep: Prepared, outcome: _Outcome, required: list[str], notice: str
    ) -> ChatResponse:
        reply = _fallback_reply(prep, notice=notice)
        if required:
            reply = reply.model_copy(
                update={"answer": "\n\n".join([*required, reply.answer]), "added_lines": [0]}
            )
        return outcome.answered(reply)

    def copilot_complete(
        prep: Prepared,
        model: ChatModel,
        required: list[str],
        outcome: _Outcome,
        lead: str | None = None,
    ) -> ChatResponse:
        try:
            reply = model.complete(prep.messages)
            outcome.reported(reply)
            check = copilot.check_answer(
                reply.text,
                prep.facts,
                knowledge_tags=[item.tag for item in prep.tagged],
                required=required,
            )
            if check.usable:
                return copilot_reply(
                    check,
                    prep,
                    outcome,
                    model_name=model.name,
                    cut_short=reply.cut_short,
                    required=required,
                    lead=lead,
                )
            # Nothing, or mostly fragments, passed the checks: the case-data answer instead.
            outcome.kept_lines = check.kept
            outcome.left_out_lines = len(check.left_out)
            outcome.fallback_reason = "policy_no_allowed_line"
            return copilot_fallback(prep, outcome, required, POLICY_NOTICE)
        except LlmUnavailableError as error:
            outcome.failed(error)
            if outcome.fallback_reason == "none":
                outcome.fallback_reason = "model_unavailable"
            return copilot_fallback(prep, outcome, required, FALLBACK_NOTICE)

    async def copilot_stream(
        prep: Prepared,
        started: float,
        finish: Callable[[ChatResponse, _Outcome], ChatResponse],
        model: ChatModel,
        required: list[str],
        lead: str | None = None,
    ) -> AsyncIterator[str]:
        """Like stream_answer, with each sentence checked as soon as it is complete."""

        def line(event: dict[str, object]) -> str:
            return json.dumps(event, ensure_ascii=False) + "\n"

        outcome = _Outcome(model=model)
        delivered = False
        guard = copilot.CopilotGuard(
            prep.facts, knowledge_tags=[item.tag for item in prep.tagged], required=required
        )
        cut_short = False
        try:
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
                check = guard.finish()
                if check.usable:
                    response = copilot_reply(
                        check,
                        prep,
                        outcome,
                        model_name=model.name,
                        cut_short=cut_short,
                        required=required,
                        lead=lead,
                    )
                else:
                    # The final answer replaces what was streamed (each streamed sentence had
                    # passed its checks; together they were mostly fragments).
                    outcome.kept_lines = check.kept
                    outcome.left_out_lines = len(check.left_out)
                    outcome.fallback_reason = "policy_no_allowed_line"
                    response = copilot_fallback(prep, outcome, required, POLICY_NOTICE)
            except LlmUnavailableError as error:
                outcome.failed(error)
                check = guard.finish()
                if check.kept:
                    outcome.fallback_reason = "stream_partial"
                    response = copilot_reply(
                        check,
                        prep,
                        outcome,
                        model_name=model.name,
                        cut_short=True,
                        required=required,
                        lead=lead,
                    )
                else:
                    if outcome.fallback_reason == "none":
                        outcome.fallback_reason = "model_unavailable"
                    response = copilot_fallback(prep, outcome, required, FALLBACK_NOTICE)
            if outcome.first_line_at is None:
                outcome.first_line_at = time.monotonic()
            yield line({"type": "done", **finish(response, outcome).model_dump()})
            delivered = True
        finally:
            outcome.cancelled = not delivered
            emit("stream", started, outcome, prep)

    def single(response: ChatResponse) -> Iterator[str]:
        event = json.dumps({"type": "done", **response.model_dump()}, ensure_ascii=False)
        return iter([event + "\n"])

    def stream_of(events: Iterator[str] | AsyncIterator[str]) -> StreamingResponse:
        return StreamingResponse(
            events,
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    def general_profile(request: Request) -> dict[str, Any]:
        try:
            profile = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))["profile"]
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        capabilities = profile.get("capabilities") or []
        if "CASE_ACCESS" not in capabilities and SUPPORT_CHAT_CAPABILITY not in capabilities:
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."}
            )
        return dict(profile)

    def general_chat_off() -> HTTPException:
        return HTTPException(404, detail={"code": "GENERAL_CHAT_OFF", "message": "Not available."})

    @app.post("/assistant/contexts", response_model=ContextResponse)
    def open_context(body: ContextOpenRequest, request: Request) -> ContextResponse:
        """Open a chat context: on a case the user may read now (the backend decides, with
        their own session), or the general chat. Nothing of any earlier chat is carried in."""

        check_origin(request)
        if body.case_id is not None:
            profile = load_case(body.case_id, request).actor.get("profile") or {}
        else:
            if not config_conversational(config):
                raise general_chat_off()
            profile = general_profile(request)
        user = profile.get("user_id")
        if not user:
            raise HTTPException(
                401, detail={"code": "UNAUTHENTICATED", "message": "Please sign in again."}
            )
        case = str(body.case_id) if body.case_id is not None else None
        return ContextResponse(
            context_id=contexts.open(str(user), case),
            scope="case" if case else "general",
            case_id=case,
            idle_seconds=config.context_idle_seconds,
        )

    @app.post("/assistant/contexts/{context_id}/close", status_code=204)
    def close_context(context_id: str, request: Request) -> Response:
        """Close a chat context and drop its turns (leaving a case, closing the tab, signing
        out). Always 204: nothing tells a caller whether an id existed. A signed-in caller
        closes only their own; after sign-out the 128-bit id alone closes it."""

        check_origin(request)
        if re.fullmatch(CONTEXT_ID, context_id):
            owner: str | None
            try:
                actor = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))
                owner = str(actor["profile"].get("user_id") or "") or None
            except ClmBackendError:
                owner = None
            contexts.close(context_id, owner)
        return Response(status_code=204)

    @app.post("/assistant/general/chat/stream")
    def general_chat_stream(body: GeneralChatRequest, request: Request) -> StreamingResponse:
        """D-115: the general onboarding chat. No case is read and none is remembered: the
        answer uses approved knowledge and the model's general reasoning, with the local model
        only. Nothing is recorded as an answer record.

        D-130: on the registered hosted Claude deployment the activated Claude configuration
        answers too, with boundary-approved repository knowledge only and the per-call ticket
        for the exact messages (as the hosted case chat, D-122)."""

        started = time.monotonic()
        check_origin(request)
        if not config_conversational(config):
            raise general_chat_off()
        profile = general_profile(request)
        role, team = profile.get("role"), profile.get("team_id")
        try:
            ticket = contexts.ticket(body.context_id, str(profile.get("user_id") or ""), None)
        except ContextRefused as refused:
            raise context_refused(refused) from None
        question = body.message.strip()[: config.max_question_chars]
        limit = config.max_history_messages
        history = [dict(turn) for turn in ticket.history][-limit:] if limit else []
        active = selector.current()

        def remember(response: ChatResponse, outcome: _Outcome) -> ChatResponse:
            contexts.add(ticket, question, response.answer)
            return response

        if not copilot.in_domain(question, ongoing=bool(history)):
            emit("stream", started, _Outcome(fallback_reason="off_domain"), None)
            # An unrelated question is not kept in the chat (as in a case chat).
            return stream_of(single(off_domain([])))
        hosted = (
            copilot_for(active)
            and active.model is not None
            and hosted_chat(active.model, "general")
        )
        tagged: list[TaggedHit] = []
        use: KnowledgeUse | None = None
        if retriever is not None:
            try:
                retrieval = retriever.retrieve(question, case_context({}), role=role, team=team)
                found = approved_knowledge(tag_hits(retrieval), role=role, team=team)
                if hosted:
                    # Filtered before it is kept: a failing check leaves no knowledge at all.
                    found = [item for item in found if approved_entry(item.hit.entry)]
                tagged = found
                use = KnowledgeUse(confidence=retrieval.confidence, degraded=retrieval.degraded)
            except Exception:  # knowledge is optional: never let it break an answer
                log.exception("knowledge retrieval failed")
        shown = shown_knowledge(tagged, {})
        messages = copilot.build_messages(
            None, history, question, knowledge=copilot.knowledge_message(tagged, shown)
        )
        names = names_for(active.model, profile) if hosted else None
        prep = Prepared(
            facts={},
            messages=messages if names is None else scrub(messages, names),
            fallback=guidance_summary(tagged, shown) or copilot.GENERAL_FALLBACK,
            suggestions=[],
            tagged=tagged,
            knowledge=use,
            shown=shown,
            question=question,
            started=started,
        )
        line = copilot.read_only_line(question)
        required = [line] if line else []
        if hosted and active.model is not None:
            # D-130: only these exact messages may go (the model admits them by this ticket).
            synthetic_eligibility_approve(prep.messages)
            lead = getattr(active.model, "attribution", None)
            return stream_of(
                copilot_stream(prep, started, remember, active.model, required, lead=lead)
            )
        if (
            copilot_for(active)
            and active.model is not None
            and not is_remote_test_model(active.model)
        ):
            # No case, so no synthetic check: the general chat stays with a local model.
            return stream_of(copilot_stream(prep, started, remember, active.model, required))
        outcome = _Outcome(fallback_reason="model_disabled")
        reply = copilot_fallback(prep, outcome, required, copilot.GENERAL_LOCAL_ONLY_NOTICE)
        emit("stream", started, outcome, prep)
        return stream_of(single(remember(reply, outcome)))

    @app.post("/assistant/knowledge/conversations/{conversation_id}/try")
    def try_change(
        conversation_id: str, body: TryChangeRequest, request: Request
    ) -> dict[str, Any]:
        """D-105: Support previews how the user's question would be answered with an unsaved
        rule change. Nothing is saved or published, no record is kept, and only the local
        model is used (the remote test model's gates admit only approved repository text).

        D-130: on the registered hosted Claude deployment the activated Claude configuration
        answers too, on a case the R2.1 gate admitted (load_case), with boundary-approved
        repository knowledge plus the redacted unsaved change, and the per-call ticket."""

        check_origin(request)
        session = request.cookies.get(SESSION_COOKIE_NAME)
        try:
            profile = backend.load_actor(session)["profile"]
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        if SUPPORT_CHAT_CAPABILITY not in (profile.get("capabilities") or []):
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."}
            )
        row = (
            knowledge.store.conversation(conversation_id)
            if knowledge is not None and re.fullmatch(ANSWER_ID, conversation_id)
            else None
        )
        everywhere = profile.get("role") == "SUPPORT" and not profile.get("team_id")
        if (
            row is None
            or row["ended_at"] is None
            or not (everywhere or row["team"] == profile.get("team_id"))
        ):
            raise HTTPException(
                404, detail={"code": "NOT_FOUND", "message": "No such conversation."}
            )
        snapshot = load_case(UUID(row["case_id"]), request)
        facts = build_case_facts(snapshot)
        ctx = case_context(facts)
        redact = Redactor(facts, parties=case_parties(snapshot.summary)).redact
        trial = Entry(
            entry_id=body.entry_id or "trial.unsaved-change",
            kind=EntryKind(body.kind),
            title=redact(" ".join(body.title.split())) or "Unsaved change",
            body=redact(body.body.strip()),
            status=EntryStatus.APPROVED,
            blocker_codes=tuple(body.blocker_codes or ctx.blocker_codes),
            fields=tuple(body.fields or ctx.fields),
            stages=tuple(body.stages or ctx.stages),
            author=str(profile.get("user_id") or ""),
        )
        question = (body.question or row["title"]).strip()[: config.max_question_chars]
        active = selector.current()
        # D-130 also needs the hosted case gate in place (it admitted this case in load_case).
        hosted = (
            active.model is not None
            and hosted_chat(active.model, "try_change")
            and getattr(request.app.state, "case_gate", None) is not None
        )
        # D-130 OD-G8: neither Support nor the conversation's owner is named to Anthropic, not
        # in the case facts, the stored question or Support's unsaved rule.
        names = names_for(active.model, profile, extra=(row["user_id"],)) if hosted else None
        if names is not None:
            trial = replaced(
                trial, title=scrub_text(trial.title, names), body=scrub_text(trial.body, names)
            )
        prep = prepare(
            ChatRequest(message=question),
            snapshot,
            question,
            trial=trial,
            remote=hosted,
            names=names,
        )
        lead: str | None = None
        refused = (
            hosted_refusal(active.model, snapshot, prep, UUID(row["case_id"]), session, trial=trial)
            if hosted and active.model is not None
            else None
        )
        if hosted and refused is None:
            # D-139: the D-095 check passed and issued the ticket for these exact messages.
            model = active.model
            lead = getattr(model, "attribution", None)
        elif refused is not None:
            model, lead = None, refused
        else:
            model = None if is_remote_test_model(active.model) else active.model
        reply = answer_with_model(prep, _Outcome(model=model), lead, collect=hosted)
        tag = prep.tagged[0].tag if prep.tagged else None
        offered = [line for line in prep.shown.lines if tag and line.endswith(f" [{tag}]")]
        return {
            "question": question,
            "answer": reply.answer,
            "answered_by": reply.answered_by,
            "notice": reply.notice,
            "tag": tag,
            # Sentences of the change the AI may use on this case (they passed the checks),
            # and whether the answer used any of them.
            "offered_lines": offered,
            "used": bool(tag) and f"[{tag}]" in reply.answer,
        }

    @app.post("/assistant/support/chat", response_model=ChatResponse)
    def support_chat(body: SupportChatRequest, request: Request) -> ChatResponse:
        """D-105: Support asks about the approved rules and the active policy, no case."""

        check_origin(request)
        session = request.cookies.get(SESSION_COOKIE_NAME)
        try:
            profile = backend.load_actor(session)["profile"]
            if SUPPORT_CHAT_CAPABILITY not in (profile.get("capabilities") or []):
                raise HTTPException(
                    403,
                    detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."},
                )
            catalogue = backend.load_policies(session)
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        question = body.message.strip()[: config.max_question_chars]
        history = [
            {"role": turn.role, "content": turn.content}
            for turn in body.history[-config.max_history_messages :]
        ] if config.max_history_messages else []
        model = selector.current().model
        # D-130: hosted Claude answers Support too; every other remote model stays refused.
        hosted = model is not None and hosted_chat(model, "support")
        reply = answer_support_question(
            question,
            history,
            role=profile.get("role"),
            team=profile.get("team_id"),
            retriever=retriever,
            catalogue=catalogue,
            model=model,
            hosted=hosted,
            lead=getattr(model, "attribution", None) if hosted else None,
            names=names_for(model, profile) if hosted else None,
        )
        return ChatResponse(
            answer=reply.answer,
            answered_by="model" if reply.answered_by == "model" else "case_data",
            model=reply.model,
            notice=reply.notice,
            suggested_questions=[],
            checks=AnswerChecks(
                removed=[LEFT_OUT_REASON] if reply.left_out else [], disclosures=[]
            )
            if reply.answered_by == "model"
            else None,
            sources=[KnowledgeSource(**source) for source in reply.sources],
        )

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

    if chat_model is None:
        app.include_router(
            model_admin_router(selector=selector, backend=backend, check_origin=check_origin)
        )

    dashboard_insights = DashboardInsights()
    INSIGHTS_UNAVAILABLE = "AI insights are unavailable."  # noqa: N806 - fixed reply text

    @app.post("/assistant/dashboard/insights", response_model=InsightsResponse)
    def dashboard_insights_route(body: InsightsRequest, request: Request) -> InsightsResponse:
        """ADR-015: word the dashboard's own findings with the active model (an API-key model
        under D-122, with the local model as fallback, D-128 I7). Read-only: no case is read,
        nothing is stored, and the browser hides the panel on any refusal."""

        # The hosted service's hardening sets this: refused before the origin,
        # the session or any model is looked at, so no model is ever reached there.
        if getattr(request.app.state, "dashboard_insights_disabled", False):
            raise HTTPException(
                503,
                detail={"code": "DASHBOARD_INSIGHTS_UNAVAILABLE", "message": INSIGHTS_UNAVAILABLE},
            )
        check_origin(request)
        try:
            profile = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))["profile"]
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        if "CASE_ACCESS" not in (profile.get("capabilities") or []):
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."}
            )
        active = selector.current()
        fallback = selector.local_fallback()
        try:
            return dashboard_insights.write(
                str(profile.get("user_id") or ""),
                body,
                active.model,
                active.base_url,
                fallback=(fallback.model, fallback.base_url),
                # Integration with R2.2/D-130: on the registered hosted deployment no paid model
                # writes dashboard insights. Hosted Claude is approved only for the four chat paths
                # (D-130 HOSTED_CHAT_PATHS, D-129 payloads), so this path stays off it there.
                external=external_conversational(config) and hosted_deployment() is None,
            )
        except InsightsUnavailable:
            raise HTTPException(
                503,
                detail={"code": "DASHBOARD_INSIGHTS_UNAVAILABLE", "message": INSIGHTS_UNAVAILABLE},
            ) from None
        except InsightsRejected:
            raise HTTPException(
                502,
                detail={"code": "DASHBOARD_INSIGHTS_REJECTED", "message": INSIGHTS_UNAVAILABLE},
            ) from None

    # --- the fifth hosted Claude path: dashboard AI insights (D-130 amendment draft) ----------
    # Only on the hosted service (the hardening flag), only with the owner's decision in the code
    # (config.HOSTED_INSIGHTS_DECISION, None by default), only for hosted Claude, and only
    # after an explicit "Generate" request. Everywhere else PR #178's route above is unchanged.

    insights_limits: list[hosted_insights.DailyLimits] = []
    insights_cache: dict[tuple[str, str], tuple[float, InsightsResponse]] = {}
    insights_lock = threading.Lock()

    def daily_limits() -> hosted_insights.DailyLimits:
        with insights_lock:
            if not insights_limits:
                folder = Path(config.model_admin_db_path).parent
                store = folder / "dashboard_insights_limits.sqlite3"
                insights_limits.append(hosted_insights.DailyLimits(store))
            return insights_limits[0]

    def insights_profile(request: Request) -> dict[str, Any]:
        try:
            profile = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))["profile"]
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        if "CASE_ACCESS" not in (profile.get("capabilities") or []):
            raise HTTPException(
                403, detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."}
            )
        return dict(profile)

    def hosted_insights_model(request: Request) -> ChatModel | None:
        # Hosted service + decision + hosted Claude active + the case gate in place.
        active = selector.current()
        if (
            getattr(request.app.state, "dashboard_insights_disabled", False)
            and getattr(request.app.state, "case_gate", None) is not None
            and active.model is not None
            and hosted_chat(active.model, "dashboard_insights")
        ):
            return active.model
        return None

    def insights_unavailable() -> HTTPException:
        return HTTPException(
            503, detail={"code": "DASHBOARD_INSIGHTS_UNAVAILABLE", "message": INSIGHTS_UNAVAILABLE}
        )

    class InsightsMode(BaseModel):
        model_config = ConfigDict(extra="forbid")

        # auto: PR #178's automatic panel; generate: hosted, an explicit action; off: hidden.
        mode: Literal["auto", "generate", "off"]
        remaining_user: int | None = None
        remaining_site: int | None = None

    class HostedInsights(BaseModel):
        model_config = ConfigDict(extra="forbid")

        insights: InsightsResponse
        findings: tuple[InsightFinding, ...]

    @app.get("/assistant/dashboard/insights/mode", response_model=InsightsMode)
    def dashboard_insights_mode(request: Request) -> InsightsMode:
        """How the dashboard offers AI insights here (no model is called)."""

        if not getattr(request.app.state, "dashboard_insights_disabled", False):
            return InsightsMode(mode="auto")
        profile = insights_profile(request)
        if hosted_insights_model(request) is None:
            return InsightsMode(mode="off")
        used_user, used_site = daily_limits().used(str(profile.get("user_id") or ""))
        return InsightsMode(
            mode="generate",
            remaining_user=max(0, hosted_insights.USER_DAILY_LIMIT - used_user),
            remaining_site=max(0, hosted_insights.SITE_DAILY_LIMIT - used_site),
        )

    @app.post("/assistant/dashboard/insights/generate", response_model=HostedInsights)
    def dashboard_insights_generate(request: Request) -> HostedInsights:
        """The fifth hosted path: findings derived on the server from the user's R2.1-eligible
        cases (labels and counts only), written by hosted Claude after an explicit request."""

        if not getattr(request.app.state, "dashboard_insights_disabled", False):
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Not found."})
        check_origin(request)
        profile = insights_profile(request)
        model = hosted_insights_model(request)
        if model is None:
            raise insights_unavailable()
        user = str(profile.get("user_id") or "")
        session = request.cookies.get(SESSION_COOKIE_NAME)
        gate = request.app.state.case_gate
        try:
            listed = backend.list_cases(session)
        except ClmBackendError as exc:
            raise backend_error(exc) from None
        eligible = hosted_insights.eligible_items(
            listed,
            gate,
            frozenset(getattr(gate, "refs", frozenset())),
            lambda case_id: backend.load_case(case_id, session).summary,
        )
        findings = hosted_insights.derive(eligible, datetime.now(UTC))
        if findings is None:
            raise insights_unavailable()
        messages = hosted_insights.build_messages(findings)
        key = (user, hashlib.sha256(json.dumps(messages).encode("utf-8")).hexdigest())
        now = time.monotonic()
        with insights_lock:
            cached = insights_cache.get(key)
        if cached is not None and now - cached[0] < hosted_insights.CACHE_SECONDS:
            return HostedInsights(insights=cached[1], findings=findings.findings)
        try:
            daily_limits().reserve(user)
        except hosted_insights.LimitReached as reached:
            raise HTTPException(
                429,
                detail={
                    "code": "DASHBOARD_INSIGHTS_LIMIT",
                    "message": "The daily limit for AI insights is reached."
                    if reached.scope == "user"
                    else "The site's daily limit for AI insights is reached.",
                },
            ) from None
        # Only these exact messages may go (the model admits them by this ticket); one attempt.
        synthetic_eligibility_approve(messages)
        try:
            answer = collect_stream(model, messages)
            insights = check_reply(findings, answer.text, model.name)
        except (LlmUnavailableError, InsightsRejected):
            raise insights_unavailable() from None
        with insights_lock:
            insights_cache[key] = (now, insights)
            for stale in [k for k, (at, _) in insights_cache.items() if now - at > 3600]:
                del insights_cache[stale]
        return HostedInsights(insights=insights, findings=findings.findings)


    @app.get("/assistant/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        model = selector.current().model
        return HealthResponse(
            status="ok",
            llm_enabled=model is not None,
            model=model.name if model is not None else None,
            answer_mode="copilot" if config_conversational(config) else "exact_lines",
            general_chat=config_conversational(config),
        )

    @app.get("/assistant/cases/{case_id}/brief", response_model=BriefResponse)
    def brief(snapshot: Snapshot, background: BackgroundTasks) -> BriefResponse:
        facts = build_case_facts(snapshot)
        background.add_task(warm_up, facts, selector.current())
        return BriefResponse(
            company=facts["company"].get("legal_name") or facts["company"].get("uen"),
            message=opening_message(facts),
            suggested_questions=suggested_questions(facts),
            blocker_count=len(facts["blockers"]),
            steps_done=facts["overall"]["steps_done"],
            steps_total=facts["overall"]["steps_total"],
        )

    @app.post("/assistant/cases/{case_id}/chat", response_model=ChatResponse)
    def chat(
        case_id: UUID, body: ChatRequest, snapshot: Snapshot, request: Request
    ) -> ChatResponse:
        started = time.monotonic()
        active = selector.current()
        facts = build_case_facts(snapshot)
        question = body.message.strip()[: config.max_question_chars]
        ticket = ticket_for(body.context_id, user_of(snapshot), str(case_id))
        history = history_for(body, ticket)
        quick = small_talk_reply(question, facts)
        if quick is not None:
            # Greetings and thanks get an instant reply; the model is not called.
            emit("chat", started, _Outcome(fallback_reason="small_talk", model=active.model), None)
            return ChatResponse(
                answer=quick,
                answered_by="case_data",
                model=None,
                notice=None,
                suggested_questions=suggested_questions(facts),
                small_talk=True,
            )
        # D-122: scope is judged whichever model answers, so no case data follows "1+1".
        if copilot_for(active) and not copilot.in_domain(
            question, ongoing=bool(ticket and ticket.history), case_open=True
        ):
            emit("chat", started, _Outcome(fallback_reason="off_domain"), None)
            return off_domain(suggested_questions(facts))
        if copilot_for(active) and active.model is not None:
            remote = is_remote_test_model(active.model)
            prepared = prepare(
                body,
                snapshot,
                question,
                remote=remote,
                history=history,
                names=names_for(active.model, snapshot.actor.get("profile")),
            )
            owned = local_ownership(prepared, case_id, request, remote)
            prep, required = copilot_prep(owned, history)
            # The exact prompt is checked (D-095) before any external call, as in exact lines.
            model, lead = remote_gate(
                active, snapshot, prep, case_id, request.cookies.get(SESSION_COOKIE_NAME)
            )
            outcome = _Outcome(model=model) if model is not None else refused_outcome(lead)
            reply = (
                copilot_complete(prep, model, required, outcome, lead=lead)
                if model is not None
                else copilot_fallback(prep, outcome, required, lead or FALLBACK_NOTICE)
            )
            response = record(case_id, snapshot, body, prep, reply, outcome)
        else:
            prep = prepare(
                body,
                snapshot,
                question,
                remote=is_remote_test_model(active.model),
                history=history,
                names=names_for(active.model, snapshot.actor.get("profile")),
            )
            model, lead = remote_gate(
                active, snapshot, prep, case_id, request.cookies.get(SESSION_COOKIE_NAME)
            )
            outcome = _Outcome(model=model)
            response = record(
                case_id, snapshot, body, prep, answer_with_model(prep, outcome, lead), outcome
            )
        if ticket is not None:
            contexts.add(ticket, question, response.answer)
        emit("chat", started, outcome, prep)
        return response

    @app.post("/assistant/cases/{case_id}/chat/stream")
    def chat_stream(
        case_id: UUID, body: ChatRequest, snapshot: Snapshot, request: Request
    ) -> StreamingResponse:
        """Like /chat, but the answer appears while the model is still writing it."""

        started = time.monotonic()
        active = selector.current()
        facts = build_case_facts(snapshot)
        question = body.message.strip()[: config.max_question_chars]
        suggestions = suggested_questions(facts)
        ticket = ticket_for(body.context_id, user_of(snapshot), str(case_id))
        history = history_for(body, ticket)

        def finish(response: ChatResponse, outcome: _Outcome) -> ChatResponse:
            # Recorded, and added to the chat context only while it is still open (a late
            # answer never lands in a context that was closed when its case was left).
            response = record(case_id, snapshot, body, prep, response, outcome)
            if ticket is not None:
                contexts.add(ticket, question, response.answer)
            return response

        quick = small_talk_reply(question, facts)
        if quick is not None:
            emit(
                "stream", started, _Outcome(fallback_reason="small_talk", model=active.model), None
            )
            return stream_of(
                single(
                    ChatResponse(
                        answer=quick,
                        answered_by="case_data",
                        model=None,
                        notice=None,
                        suggested_questions=suggestions,
                        small_talk=True,
                    )
                )
            )
        if copilot_for(active) and not copilot.in_domain(
            question, ongoing=bool(ticket and ticket.history), case_open=True
        ):
            emit("stream", started, _Outcome(fallback_reason="off_domain"), None)
            return stream_of(single(off_domain(suggestions)))
        if copilot_for(active) and active.model is not None:
            remote = is_remote_test_model(active.model)
            prepared = prepare(
                body,
                snapshot,
                question,
                remote=remote,
                history=history,
                names=names_for(active.model, snapshot.actor.get("profile")),
            )
            owned = local_ownership(prepared, case_id, request, remote)
            prep, required = copilot_prep(owned, history)
            model, lead = remote_gate(
                active, snapshot, prep, case_id, request.cookies.get(SESSION_COOKIE_NAME)
            )
            if model is None:
                outcome = refused_outcome(lead)
                reply = finish(
                    copilot_fallback(prep, outcome, required, lead or FALLBACK_NOTICE), outcome
                )
                emit("stream", started, outcome, prep)
                return stream_of(single(reply))
            return stream_of(copilot_stream(prep, started, finish, model, required, lead=lead))
        prep = prepare(
            body,
            snapshot,
            question,
            remote=is_remote_test_model(active.model),
            history=history,
            names=names_for(active.model, snapshot.actor.get("profile")),
        )
        model, lead = remote_gate(
            active, snapshot, prep, case_id, request.cookies.get(SESSION_COOKIE_NAME)
        )
        return stream_of(stream_answer(prep, started, finish, model, lead))

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
