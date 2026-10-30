"""Feedback and review endpoints for the knowledge loop.

    RM / Client Onboarder  POST /assistant/cases/{id}/feedback      "Yes, helpful" / "Not helpful"
    Support (KNOWLEDGE_REVIEW)  review queue, edit, approve/reject, retire, re-index, stats,
                                write the fix for or close an enhancement request
    HR (POLICY_MUTATE)          propose new guidance or a new version of guidance

Who someone is, and what they may do, always comes from the CLM backend (/api/auth/me with
their own session); nothing in a request body can grant a permission. Nobody who wrote or
edited an entry can approve or reject it, and a decision applies only to the exact content
the reviewer was shown (both enforced by the store). The POC's single-reviewer setting
(``knowledge_single_reviewer``, D-083, proposed; it relaxes D-074's two-person control
because the synthetic users have one Support reviewer) lets a reviewer decide an entry they wrote or
edited: an approval needs ``confirm_single_reviewer`` and is recorded as single-reviewer.
Every review or guidance change asks the backend again inside its write transaction, so a
role, team or session withdrawn since the request began stops it.

"Yes, helpful" only records the rating with the case context (it counts towards confidence by
topic in the stats); it drafts nothing. "Not helpful" needs a note and is an enhancement
request, which a Support reviewer handles end to end: either writes the fix as a past
resolution or a guidance change linked to the request (pending review like any other entry;
approving it resolves the request, rejecting it opens the request again) or closes it with a
reason.

Team scope: approved past resolutions are visible only to the team they came from. A Support
reviewer, whom the CLM backend gives no team (D-099), sees, edits and decides every
team's drafts and enhancement requests (called gaps here), and their stats count every team.
Any other caller keeps the team rule: anything outside their team is answered as "not found",
and stats count only their team's entries and feedback. Guidance proposed by HR keeps the
visibility HR set. An edit can narrow team and role visibility, never widen it.

Retiring an approved entry (official guidance included) takes two reviewers: the first POST
to /retire records the request, a different reviewer's POST confirms it.

Answer records (D-084, proposed): feedback names the answer it rates (``answer_id``) when
the answer has a record; "Not helpful" without one is still accepted (only the note reaches
the Director). A named record must be the caller's own, on the same case, unrated and not
expired; any refusal is the same "not found". The RM who asked can open their record
(GET /assistant/answers/{id}); a Director opens it from the enhancement request it is linked
to, with the earlier answers of that chat. HR is refused, anyone else gets "not found", and
every view is logged.
"""

import re
from collections import Counter
from collections.abc import Callable
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .answer_records import ANSWER_ID, fix_start_lines, fix_title
from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .context import build_case_facts
from .knowledge.drafting import resolution_from_request
from .knowledge.models import Entry, EntryKind, EntryStatus, Visibility
from .knowledge.redaction import Redactor, case_parties
from .knowledge.retrieval import case_context
from .knowledge.service import KnowledgeBase
from .knowledge.store import (
    REVIEW_STATUSES,
    AnswerNotFoundError,
    ConfirmationRequiredError,
    ContentChangedError,
    KnowledgeError,
    KnowledgeRuleError,
    MakerCheckerError,
    SecondReviewerError,
    earlier_shown,
)

REVIEW = "KNOWLEDGE_REVIEW"
MUTATE = "POLICY_MUTATE"
_HASH = r"^[0-9a-f]{64}$"
GUIDANCE_ID = r"^guidance\.[a-z0-9-]{3,80}$"


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpful: bool
    note: str = Field(default="", max_length=1000)
    # The answer being rated, when it has a record. Without one (the record could not be
    # saved) "Not helpful" is still accepted: the Director then sees only the note.
    answer_id: str | None = Field(default=None, pattern=ANSWER_ID)

    @model_validator(mode="after")
    def _not_helpful_says_what_was_missing(self) -> "FeedbackRequest":
        if not self.helpful and not self.note.strip():
            raise ValueError("say what was missing")
        return self


# --- conversation feedback (D-100) ------------------------------------------------------

Satisfaction = Literal["very_satisfied", "satisfied", "neutral", "unsatisfied", "very_unsatisfied"]
# What the form offers after "Was this issue resolved?": Yes or No.
SATISFACTION_IF_RESOLVED = ("very_satisfied", "satisfied", "neutral")
SATISFACTION_IF_NOT_RESOLVED = ("neutral", "unsatisfied", "very_unsatisfied")
# A rating with a priority is reviewed by Support; satisfied or better needs no review.
PRIORITY = {"neutral": "low", "unsatisfied": "medium", "very_unsatisfied": "high"}
CONVERSATION_PAGE_SIZE = 10
CONVERSATION_NOT_FOUND_MESSAGE = "No such conversation."


class EndConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resolved: bool
    satisfaction: Satisfaction
    # "Additional comments" when resolved (optional); "How should it be improved" when not
    # (required).
    comment: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _fits_the_form(self) -> "EndConversationRequest":
        offered = SATISFACTION_IF_RESOLVED if self.resolved else SATISFACTION_IF_NOT_RESOLVED
        if self.satisfaction not in offered:
            raise ValueError("this rating is not offered for that answer to 'resolved'")
        if not self.resolved and not self.comment.strip():
            raise ValueError("say how it should be improved")
        return self


class ConversationDraft(BaseModel):
    """Support's unsaved fix for a conversation's request; every field may still be empty."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["resolution", "guidance"] = "resolution"
    title: str = Field(default="", max_length=200)
    body: str = Field(default="", max_length=4000)
    follow_ups: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=10
    )
    entry_id: str | None = Field(default=None, max_length=90)
    source_ref: str = Field(default="", max_length=300)
    blocker_codes: list[Annotated[str, Field(max_length=80)]] = Field(
        default_factory=list, max_length=20
    )
    fields: list[Annotated[str, Field(max_length=80)]] = Field(default_factory=list, max_length=20)
    stages: list[Annotated[str, Field(max_length=80)]] = Field(default_factory=list, max_length=20)


class FeedbackResponse(BaseModel):
    feedback_id: int
    message: str


class VisibilityBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    roles: list[str] = Field(default_factory=list, max_length=10)
    teams: list[str] = Field(default_factory=list, max_length=20)


class EditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # The content the editor was shown; the edit is refused if the version changed since.
    content_hash: str = Field(pattern=_HASH)
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body: str | None = Field(default=None, min_length=10, max_length=4000)
    follow_ups: list[str] | None = Field(default=None, max_length=10)
    blocker_codes: list[str] | None = Field(default=None, max_length=20)
    fields: list[str] | None = Field(default=None, max_length=20)
    stages: list[str] | None = Field(default=None, max_length=20)
    visibility: VisibilityBody | None = None
    replaces: str | None = Field(default=None, max_length=120)


class DecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool
    # The content the reviewer was shown; the decision is refused if the version differs.
    content_hash: str = Field(pattern=_HASH)
    notes: str = Field(default="", max_length=1000)
    # Single-reviewer mode only: the reviewer confirmed publishing an entry they wrote or
    # edited, after being shown its final text. Ignored when someone else wrote it.
    confirm_single_reviewer: bool = False


class FixRequest(BaseModel):
    """A Director's fix for an enhancement request: a past resolution or a guidance change."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal["resolution", "guidance"]
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=4000)
    follow_ups: list[str] = Field(default_factory=list, max_length=10)
    # Guidance only: a new version of this guidance entry (a new entry when left out), where
    # the rule comes from, and who sees it. Codes, fields and stages default to the
    # request's; visibility to the current version's when changing existing guidance.
    entry_id: str | None = Field(default=None, pattern=GUIDANCE_ID)
    source_ref: str | None = Field(default=None, min_length=3, max_length=300)
    blocker_codes: list[str] | None = Field(default=None, max_length=20)
    fields: list[str] | None = Field(default=None, max_length=20)
    stages: list[str] | None = Field(default=None, max_length=20)
    visibility: VisibilityBody | None = None
    # The Director started from the request's answer record (the fix-start lines). Recorded
    # on the saved version only when the request has a record.
    started_from_answer: bool = False

    @model_validator(mode="after")
    def _fits_its_kind(self) -> "FixRequest":
        if self.kind == "guidance" and self.source_ref is None:
            raise ValueError("guidance needs a source reference")
        if self.kind == "guidance" and self.follow_ups:
            raise ValueError("follow-up questions belong to past resolutions")
        if self.kind == "resolution" and (
            self.entry_id is not None
            or self.source_ref is not None
            or self.visibility is not None
            or self.blocker_codes is not None
            or self.fields is not None
            or self.stages is not None
        ):
            raise ValueError("a past resolution takes its context from the request")
        return self


class CloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(max_length=1000)

    @model_validator(mode="after")
    def _has_a_reason(self) -> "CloseRequest":
        if not self.reason.strip():
            raise ValueError("give a reason")
        return self


class RetireRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str = Field(min_length=3, max_length=1000)


class GuidanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_id: str | None = Field(default=None, pattern=GUIDANCE_ID)
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=4000)
    source_ref: str = Field(min_length=3, max_length=300)
    blocker_codes: list[str] = Field(default_factory=list, max_length=20)
    fields: list[str] = Field(default_factory=list, max_length=20)
    stages: list[str] = Field(default_factory=list, max_length=20)
    visibility: VisibilityBody = Field(default_factory=VisibilityBody)
    illustrative: bool = False


def entry_view(entry: Entry, *, single_reviewer: bool = False) -> dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "key": entry.key,
        "version": entry.version,
        "kind": entry.kind.value,
        "status": entry.status.value,
        "title": entry.title,
        "body": entry.body,
        "blocker_codes": list(entry.blocker_codes),
        "fields": list(entry.fields),
        "stages": list(entry.stages),
        "follow_ups": list(entry.follow_ups),
        "visibility": {
            "roles": list(entry.visibility.roles),
            "teams": list(entry.visibility.teams),
        },
        "replaces": entry.replaces,
        "revises": entry.revises,
        "author": entry.author,
        "approver": entry.approver,
        "approved_at": entry.approved_at,
        "created_at": entry.created_at,
        "source_ref": entry.source_ref,
        "illustrative": entry.illustrative,
        "started_from_answer": entry.started_from_answer,
        "content_hash": entry.content_hash(),
        # This version was approved by someone who wrote or edited it (single-reviewer mode).
        "single_reviewer": single_reviewer,
    }


AUTHOR_MESSAGE = "You cannot approve or reject an entry you wrote or edited."
CHANGED_MESSAGE = "This entry has changed or was already decided. Refresh and try again."
RULE_MESSAGE = "This change is not allowed."
NOT_FOUND_MESSAGE = "No such entry."
SECOND_REVIEWER_MESSAGE = "A different reviewer must confirm this."
CONFIRM_MESSAGE = "Confirm that you are publishing this entry as its only reviewer."
REQUEST_NOT_FOUND_MESSAGE = "No such enhancement request."
# A redaction placeholder such as [ADDRESS] or [COMPANY] (any [UPPERCASE] token the Redactor
# makes; knowledge tags like [G1] have digits and do not match).
PLACEHOLDER = re.compile(r"\[[A-Z][A-Z_]*\]")


def placeholders_left(*texts: str) -> list[str]:
    """The redaction placeholders still in a Director's fix, in order, each once."""

    return list(dict.fromkeys(m.group(0) for text in texts for m in PLACEHOLDER.finditer(text)))


def placeholder_refused(left: list[str]) -> HTTPException:
    return HTTPException(
        422,
        detail={
            "code": "PLACEHOLDER_NOT_REWRITTEN",
            "message": f"Rewrite {', '.join(left)} in general terms before saving.",
        },
    )


REQUEST_CHANGED_MESSAGE = "This request was already handled. Refresh and try again."
ANSWER_NOT_FOUND_MESSAGE = "No such answer."


def answer_view(record: dict[str, Any], *, director: bool = False) -> dict[str, Any]:
    """An answer record as the RM who asked, or a Director, sees it. A Director sees only
    the earlier answers kept with the request (``earlier_shown``)."""

    earlier = record["earlier_answer_ids"]
    return {
        "answer_id": record["id"],
        "case_id": record["case_id"],
        "created_at": record["created_at"],
        "question": record["question"],
        "earlier_answer_ids": earlier_shown(earlier) if director else earlier,
        "case_snapshot": record["case_snapshot"],
        "knowledge": record["knowledge"],
        "allowed_lines": record["allowed_lines"],
        "chosen_lines": record["chosen_lines"],
        "dropped_lines": record["dropped_lines"],
        "result": record["result"],
        "shown_answer": record["shown_answer"],
        "rated": record["rated_at"] is not None,
    }


def guidance_id(title: str) -> str:
    """The id for new guidance named only by its title: its ASCII letters and digits, with
    words joined by "-" (it must still match GUIDANCE_ID)."""

    return "guidance." + "-".join(re.findall(r"[a-z0-9]+", title.lower()))[:80]


def in_team(entry: Entry, team: str | None) -> bool:
    """An entry with no team restriction is organisation-wide; otherwise the team must match."""

    return not entry.visibility.teams or team in entry.visibility.teams


def knowledge_router(
    *,
    kb: KnowledgeBase,
    backend: ClmBackendClient,
    check_origin: Callable[[Request], None],
    load_case: Callable[..., CaseSnapshot],
    single_reviewer: bool = False,
    answer_days: int = 7,
) -> APIRouter:
    router = APIRouter()

    def actor(request: Request) -> dict[str, Any]:
        check_origin(request)
        try:
            profile = backend.load_actor(request.cookies.get(SESSION_COOKIE_NAME))["profile"]
        except ClmBackendError as exc:
            raise HTTPException(
                exc.status_code, detail={"code": exc.code, "message": exc.message}
            ) from None
        return dict(profile)

    Actor = Annotated[dict[str, Any], Depends(actor)]
    Snapshot = Annotated[CaseSnapshot, Depends(load_case)]

    def can(profile: dict[str, Any], capability: str) -> bool:
        return capability in (profile.get("capabilities") or [])

    def require(profile: dict[str, Any], *capabilities: str) -> None:
        if not any(can(profile, c) for c in capabilities):
            raise HTTPException(
                403,
                detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."},
            )

    def user_id(profile: dict[str, Any]) -> str:
        value = profile.get("user_id")
        if not value:
            raise HTTPException(401, detail={"code": "AUTHENTICATION_REQUIRED"})
        return str(value)

    def team(profile: dict[str, Any]) -> str | None:
        value = profile.get("team_id")
        return str(value) if value else None

    def global_reviewer(profile: dict[str, Any]) -> bool:
        """A Support reviewer, whom the CLM backend gives no team (D-099), reviews every
        team's entries and gaps; anyone else keeps the team rule."""

        return profile.get("role") == "SUPPORT" and team(profile) is None

    def in_scope(entry: Entry, profile: dict[str, Any]) -> bool:
        return global_reviewer(profile) or in_team(entry, team(profile))

    def not_found() -> HTTPException:
        return HTTPException(404, detail={"code": "NOT_FOUND", "message": NOT_FOUND_MESSAGE})

    def found(entry: Entry | None, profile: dict[str, Any]) -> Entry:
        """The entry, or "not found" when it is missing or outside the caller's review scope."""

        if entry is None or not in_scope(entry, profile):
            raise not_found()
        return entry

    def recheck(
        request: Request,
        profile: dict[str, Any],
        capability: str,
        reach: Callable[[dict[str, Any]], None] | None = None,
    ) -> Callable[[], None]:
        """The checks above again, for the store to run inside the change's write transaction:
        the caller is reloaded from the CLM backend with the same session and must still be the
        same user, with ``capability`` and the target in ``reach``. Fails closed with the same
        401/403/404, or the backend's own error."""

        def authorize() -> None:
            current = actor(request)
            if user_id(current) != user_id(profile):
                raise HTTPException(401, detail={"code": "AUTHENTICATION_REQUIRED"})
            require(current, capability)
            if reach is not None:
                reach(current)

        return authorize

    def refused(exc: KnowledgeError) -> HTTPException:
        # Fixed messages only: the browser shows nothing else (apps/frontend aiAssistant.ts).
        if isinstance(exc, SecondReviewerError):
            return HTTPException(
                403, detail={"code": "SECOND_REVIEWER", "message": SECOND_REVIEWER_MESSAGE}
            )
        if isinstance(exc, ConfirmationRequiredError):
            return HTTPException(
                403, detail={"code": "CONFIRM_SINGLE_REVIEWER", "message": CONFIRM_MESSAGE}
            )
        if isinstance(exc, MakerCheckerError):
            return HTTPException(403, detail={"code": "MAKER_CHECKER", "message": AUTHOR_MESSAGE})
        if isinstance(exc, KnowledgeRuleError):
            return HTTPException(409, detail={"code": "NOT_ALLOWED", "message": RULE_MESSAGE})
        return HTTPException(409, detail={"code": "CHANGED", "message": CHANGED_MESSAGE})

    def team_entry_counts(profile: dict[str, Any]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in kb.store.entries():
            if in_scope(item, profile):
                name = f"{item.kind.value}_{item.status.value}"
                counts[name] = counts.get(name, 0) + 1
        return counts

    def team_feedback(
        profile: dict[str, Any], status: str | None = None, helpful: bool | None = None
    ) -> list[dict[str, Any]]:
        return [
            row
            for row in kb.store.feedback(status=status, helpful=helpful)
            if global_reviewer(profile) or row["team"] == team(profile)
        ]

    def request_in_scope(feedback_id: int) -> Callable[[dict[str, Any]], None]:
        """An enhancement request ("Not helpful" feedback) the caller may handle, else 404."""

        def reach(who: dict[str, Any]) -> None:
            if not any(row["id"] == feedback_id for row in team_feedback(who, helpful=False)):
                raise HTTPException(
                    404, detail={"code": "NOT_FOUND", "message": REQUEST_NOT_FOUND_MESSAGE}
                )

        return reach

    def answer_not_found() -> HTTPException:
        return HTTPException(404, detail={"code": "NOT_FOUND", "message": ANSWER_NOT_FOUND_MESSAGE})

    def same_user(request: Request, profile: dict[str, Any]) -> Callable[[], None]:
        """For the store, inside the write: the caller is still the same signed-in user."""

        def authorize() -> None:
            if user_id(actor(request)) != user_id(profile):
                raise HTTPException(401, detail={"code": "AUTHENTICATION_REQUIRED"})

        return authorize

    def request_refused(exc: KnowledgeError) -> HTTPException:
        if isinstance(exc, ContentChangedError):
            return HTTPException(
                409, detail={"code": "CHANGED", "message": REQUEST_CHANGED_MESSAGE}
            )
        return HTTPException(
            404, detail={"code": "NOT_FOUND", "message": REQUEST_NOT_FOUND_MESSAGE}
        )

    # --- RM feedback ----------------------------------------------------------------

    @router.post("/assistant/cases/{case_id}/feedback", response_model=FeedbackResponse)
    def feedback(case_id: UUID, body: FeedbackRequest, snapshot: Snapshot) -> FeedbackResponse:
        profile = snapshot.actor.get("profile") or {}
        facts = build_case_facts(snapshot)
        parties = case_parties(snapshot.summary)
        ctx = case_context(facts)
        # Redacted before it is stored: a Director reads the note of an enhancement request.
        note = Redactor(facts, parties=parties).redact(body.note.strip())
        try:
            feedback_id = kb.store.add_feedback(
                case_id=str(case_id),
                user_id=user_id(profile),
                role=profile.get("role"),
                team=team(profile),
                helpful=body.helpful,
                note=note,
                blocker_codes=ctx.blocker_codes,
                fields=ctx.fields,
                stages=ctx.stages,
                entry_id=None,
                answer_id=body.answer_id,
                answer_days=answer_days,
            )
        except AnswerNotFoundError:
            # Someone else's, another case's, expired, already rated or made up: all alike.
            raise answer_not_found() from None
        return FeedbackResponse(
            feedback_id=feedback_id,
            message=(
                # The RM only needs a short thanks; the Director review behind it is not
                # their concern (and a one-click "Yes, helpful" should not feel like a task).
                "Thanks for your feedback."
                if body.helpful
                else "Thanks. This has been flagged so the answer can be improved."
            ),
        )

    # --- conversations (D-100) ---------------------------------------------------------

    def find_conversation(conversation_id: str) -> dict[str, Any] | None:
        if not re.fullmatch(ANSWER_ID, conversation_id):
            return None
        return kb.store.conversation(conversation_id)

    def conversation_not_found() -> HTTPException:
        return HTTPException(
            404, detail={"code": "NOT_FOUND", "message": CONVERSATION_NOT_FOUND_MESSAGE}
        )

    def conversation_view(row: dict[str, Any]) -> dict[str, Any]:
        """A conversation as a list row: no comment, no draft text."""

        return {
            "conversation_id": row["id"],
            "case_id": row["case_id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "ended_at": row["ended_at"],
            "resolved": row["resolved"],
            "satisfaction": row["satisfaction"],
            "priority": row["priority"],
            "review_status": row["review_status"],
            "answers": row["answers"],
            "team": row["team"],
            "user_id": row["user_id"],
        }

    def transcript(
        conversation_id: str, viewer: str, request: Request, profile: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """The conversation's questions and answers as shown (redacted); each view logged."""

        turns = []
        for record in kb.store.conversation_records(conversation_id):
            try:
                viewed = kb.store.view_answer(
                    record["id"],
                    viewer=viewer,
                    allow=lambda row: row.get("conversation_id") == conversation_id,
                    authorize=same_user(request, profile),
                )
            except AnswerNotFoundError:
                continue  # removed meanwhile
            turns.append(
                {
                    "answer_id": viewed["id"],
                    "created_at": viewed["created_at"],
                    "question": viewed["question"],
                    "answer": viewed["shown_answer"],
                    "notices": viewed["result"].get("notices", []),
                    "answered_by": viewed["result"].get("answered_by"),
                }
            )
        return turns

    @router.post("/assistant/conversations/{conversation_id}/end")
    def end_conversation(
        conversation_id: str, body: EndConversationRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        """The user rates their own open conversation (End conversation), once."""

        me = user_id(profile)
        row = find_conversation(conversation_id)
        if row is None or row["user_id"] != me or row["ended_at"] is not None:
            raise conversation_not_found()
        # The case must still be theirs to open; its values are redacted from the comment.
        snapshot = load_case(UUID(row["case_id"]), request)
        facts = build_case_facts(snapshot)
        ctx = case_context(facts)
        comment = Redactor(facts, parties=case_parties(snapshot.summary)).redact(
            body.comment.strip()
        )
        try:
            ended = kb.store.end_conversation(
                conversation_id,
                user_id=me,
                resolved=body.resolved,
                satisfaction=body.satisfaction,
                priority=PRIORITY.get(body.satisfaction),
                comment=comment,
                blocker_codes=ctx.blocker_codes,
                fields=ctx.fields,
                stages=ctx.stages,
            )
        except AnswerNotFoundError:
            raise conversation_not_found() from None
        return {
            "conversation_id": ended["id"],
            "message": "Thanks for your feedback."
            if PRIORITY.get(body.satisfaction) is None
            else "Thanks. Your feedback has been sent so the answers can be improved.",
        }

    @router.get("/assistant/conversations")
    def my_conversations(profile: Actor, page: int = 1) -> dict[str, Any]:
        """The user's own chats (history), newest first, 10 per page."""

        page = max(1, page)
        rows, total = kb.store.conversations(
            user_id=user_id(profile),
            limit=CONVERSATION_PAGE_SIZE,
            offset=(page - 1) * CONVERSATION_PAGE_SIZE,
        )
        return {
            "items": [conversation_view(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": CONVERSATION_PAGE_SIZE,
        }

    @router.get("/assistant/conversations/{conversation_id}")
    def my_conversation(conversation_id: str, profile: Actor, request: Request) -> dict[str, Any]:
        """One of the user's own chats: what they asked and were shown (views logged)."""

        me = user_id(profile)
        row = find_conversation(conversation_id)
        if row is None or row["user_id"] != me:
            raise conversation_not_found()
        load_case(UUID(row["case_id"]), request)  # still theirs to open
        return {
            **conversation_view(row),
            "comment": row["comment"],
            "turns": transcript(conversation_id, me, request, profile),
        }

    def with_request(conversation_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        """A rated conversation with a priority (so with a request), in scope, else 404."""

        row = reviewable(conversation_id, profile)
        if row["priority"] is None:
            raise conversation_not_found()
        return row

    def reviewable(conversation_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        """A rated conversation in the reviewer's scope, else 404."""

        row = find_conversation(conversation_id)
        if row is None or row["ended_at"] is None:
            raise conversation_not_found()
        if not (global_reviewer(profile) or row["team"] == team(profile)):
            raise conversation_not_found()
        return row

    @router.get("/assistant/knowledge/conversations")
    def review_list(
        profile: Actor,
        page: int = 1,
        resolved: bool | None = None,
        satisfaction: Satisfaction | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Rated conversations for Support: high, medium, low, then no priority; 10 a page."""

        require(profile, REVIEW)
        if status is not None and status not in REVIEW_STATUSES:
            raise HTTPException(
                422, detail={"code": "INVALID_STATUS", "message": "Unknown status."}
            )
        page = max(1, page)
        rows, total = kb.store.conversations(
            team=team(profile),
            all_teams=global_reviewer(profile),
            rated_only=True,
            resolved=resolved,
            satisfaction=satisfaction,
            review_status=status,
            limit=CONVERSATION_PAGE_SIZE,
            offset=(page - 1) * CONVERSATION_PAGE_SIZE,
        )
        return {
            "items": [conversation_view(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": CONVERSATION_PAGE_SIZE,
        }

    @router.get("/assistant/knowledge/conversations/{conversation_id}")
    def review_conversation(
        conversation_id: str, profile: Actor, request: Request
    ) -> dict[str, Any]:
        """A rated conversation for Support: rating, comment, the whole chat (views logged),
        its enhancement request when it has a priority, and the saved draft."""

        require(profile, REVIEW)
        row = reviewable(conversation_id, profile)
        gap = next(
            (
                item
                for item in team_feedback(profile, helpful=False)
                if item["id"] == row["feedback_id"]
            ),
            None,
        )
        return {
            **conversation_view(row),
            "comment": row["comment"],
            "close_reason": row["close_reason"],
            "request": gap,
            "draft": row["draft"],
            "draft_by": row["draft_by"],
            "draft_at": row["draft_at"],
            "turns": transcript(conversation_id, user_id(profile), request, profile),
        }

    @router.put("/assistant/knowledge/conversations/{conversation_id}/draft")
    def save_draft(
        conversation_id: str, body: ConversationDraft, profile: Actor, request: Request
    ) -> dict[str, Any]:
        """Save Support's fix as a draft (not knowledge yet): redacted against the case."""

        require(profile, REVIEW)
        row = with_request(conversation_id, profile)
        snapshot = load_case(UUID(row["case_id"]), request)
        redact = Redactor(build_case_facts(snapshot), parties=case_parties(snapshot.summary)).redact
        draft = {
            "kind": body.kind,
            "title": redact(body.title),
            "body": redact(body.body),
            "follow_ups": [redact(item) for item in body.follow_ups],
            "entry_id": body.entry_id,
            "source_ref": body.source_ref,
            "blocker_codes": body.blocker_codes,
            "fields": body.fields,
            "stages": body.stages,
        }

        def still_reviewer() -> None:
            fresh = actor(request)
            if user_id(fresh) != user_id(profile) or not can(fresh, REVIEW):
                raise HTTPException(
                    403, detail={"code": "FORBIDDEN", "message": "You are not allowed to do this."}
                )

        try:
            kb.store.save_conversation_draft(
                conversation_id, draft, by=user_id(profile), authorize=still_reviewer
            )
        except AnswerNotFoundError:
            raise request_refused(ContentChangedError("not open")) from None
        return {"status": "draft", "draft": draft}

    @router.delete("/assistant/knowledge/conversations/{conversation_id}/draft")
    def discard_draft(conversation_id: str, profile: Actor) -> dict[str, Any]:
        require(profile, REVIEW)
        with_request(conversation_id, profile)
        try:
            kb.store.save_conversation_draft(conversation_id, None, by=user_id(profile))
        except AnswerNotFoundError:
            raise request_refused(ContentChangedError("not open")) from None
        return {"status": "not_reviewed"}

    # --- answer records ---------------------------------------------------------------

    @router.get("/assistant/answers/{answer_id}")
    def own_answer(answer_id: str, profile: Actor, request: Request) -> dict[str, Any]:
        """The RM's own record of an answer they were given (the view is logged)."""

        if profile.get("role") == "HR":
            require(profile, "CASE_ACCESS")  # HR has no case access: 403
        me_id = user_id(profile)
        record = kb.store.answer_record(answer_id) if re.fullmatch(ANSWER_ID, answer_id) else None
        if record is None or record["user_id"] != me_id:
            raise answer_not_found()
        # The case must still be theirs to open (their own session; GET only).
        load_case(UUID(record["case_id"]), request)
        try:
            viewed = kb.store.view_answer(
                answer_id,
                viewer=me_id,
                allow=lambda row: row["user_id"] == me_id,
                authorize=same_user(request, profile),
            )
        except AnswerNotFoundError:
            raise answer_not_found() from None
        return answer_view(viewed)

    def request_answer(
        feedback_id: int, answer_id: str | None, profile: Actor, request: Request
    ) -> dict[str, Any]:
        """A Director's view of the record linked to an open request, or of one of the
        earlier answers it names (``answer_id``). Logged; "not found" otherwise."""

        return answer_view(request_record(feedback_id, answer_id, profile, request), director=True)

    def request_record(
        feedback_id: int, answer_id: str | None, profile: Actor, request: Request
    ) -> dict[str, Any]:
        """The record behind ``request_answer``, with the view logged."""

        reach = request_in_scope(feedback_id)
        require(profile, REVIEW)
        reach(profile)
        linked = next(
            (
                row["answer_id"]
                for row in team_feedback(profile, helpful=False)
                if row["id"] == feedback_id
            ),
            None,
        )
        if linked is None:
            raise answer_not_found()
        wanted = linked if answer_id is None else answer_id

        def allow(row: dict[str, Any]) -> bool:
            if row["id"] == linked:
                return True
            head = kb.store.answer_record(linked)
            return (
                head is not None
                and row["id"] in earlier_shown(head["earlier_answer_ids"])
                and (row["user_id"], row["case_id"]) == (head["user_id"], head["case_id"])
            )

        try:
            viewed = kb.store.view_answer(
                wanted,
                viewer=user_id(profile),
                allow=allow,
                authorize=recheck(request, profile, REVIEW, reach),
            )
        except AnswerNotFoundError:
            raise answer_not_found() from None
        return viewed

    @router.get("/assistant/knowledge/feedback/{feedback_id}/answer")
    def linked_answer(feedback_id: int, profile: Actor, request: Request) -> dict[str, Any]:
        return request_answer(feedback_id, None, profile, request)

    @router.get("/assistant/knowledge/feedback/{feedback_id}/fix-start")
    def fix_start(feedback_id: int, profile: Actor, request: Request) -> dict[str, Any]:
        """Where a Director's fix can start: a title from the blocker type and the lines the
        AI wrote that were left out (or shown though not allowed), redacted against the
        request's case loaded with this Director's own session. Reading the record is a
        logged view; a request without one is "not found" (the form starts empty). No model
        is called and nothing is saved: the fix is saved, and checked, only on Save."""

        reach = request_in_scope(feedback_id)
        require(profile, REVIEW)
        reach(profile)
        row = next(row for row in team_feedback(profile, helpful=False) if row["id"] == feedback_id)
        if row["answer_id"] is None:
            raise answer_not_found()
        # The case first: if this Director cannot load it, nothing is read or logged.
        snapshot = load_case(UUID(row["case_id"]), request)
        redact = Redactor(build_case_facts(snapshot), parties=case_parties(snapshot.summary)).redact
        record = request_record(feedback_id, None, profile, request)
        return {
            "title": fix_title(row["blocker_codes"]),
            "lines": fix_start_lines(record, redact),
        }

    @router.get("/assistant/knowledge/feedback/{feedback_id}/answers/{answer_id}")
    def earlier_answer(
        feedback_id: int, answer_id: str, profile: Actor, request: Request
    ) -> dict[str, Any]:
        if not re.fullmatch(ANSWER_ID, answer_id):
            raise answer_not_found()
        return request_answer(feedback_id, answer_id, profile, request)

    # --- who may do what (for the UI; the endpoints check again) --------------------

    @router.get("/assistant/knowledge/me")
    def me(profile: Actor) -> dict[str, Any]:
        return {
            "user_id": profile.get("user_id"),
            "can_review": can(profile, REVIEW),
            "can_edit_guidance": can(profile, MUTATE),
            "single_reviewer": single_reviewer,
        }

    # --- Director review ------------------------------------------------------------

    @router.get("/assistant/knowledge/reviews")
    def reviews(profile: Actor) -> dict[str, Any]:
        require(profile, REVIEW)
        return {
            "pending": [
                entry_view(e)
                for e in kb.store.entries(status=EntryStatus.PENDING_REVIEW)
                if in_scope(e, profile)
            ],
            # Open enhancement requests ("Enhancement requests" in the review window).
            "gaps": team_feedback(profile, "open", helpful=False),
        }

    @router.get("/assistant/knowledge/entries")
    def entries(profile: Actor, kind: EntryKind | None = None) -> list[dict[str, Any]]:
        require(profile, REVIEW, MUTATE)
        single = kb.store.single_reviewer_approvals()
        return [
            entry_view(e, single_reviewer=e.key in single)
            for e in kb.store.entries(status=EntryStatus.APPROVED, kind=kind)
            if in_scope(e, profile)
        ]

    @router.get("/assistant/knowledge/entries/{entry_id}")
    def entry(entry_id: str, profile: Actor) -> dict[str, Any]:
        versions = kb.store.versions(entry_id)
        if not versions:
            raise not_found()
        reviewer = can(profile, REVIEW) or can(profile, MUTATE)
        if reviewer and in_scope(versions[-1], profile):
            single = kb.store.single_reviewer_approvals()
            return {
                "versions": [entry_view(v, single_reviewer=v.key in single) for v in versions],
                "reviews": kb.store.reviews(entry_id),
            }
        # Anyone else sees only the versions they wrote: not a reviewer's edited version or
        # anyone's review notes.
        user = profile.get("user_id")
        own = [v for v in versions if v.author == user]
        if own:
            # Since schema v3 an edit is a new version that revises the old one, which stays
            # as written: each 'edit' row on a version is paired with one version revising it.
            # A store from before v3 edited a pending version in place, keeping its author and
            # adding only an 'edit' row. So a version with someone else's 'edit' row and more
            # 'edit' rows than versions revising it is left out, also when its in-place text is
            # the author's own and someone else then edited it normally (the safe side).
            edits: Counter[int] = Counter()
            foreign: set[int] = set()
            for row in kb.store.reviews(entry_id):
                if row["decision"] == "edit":
                    edits[row["version"]] += 1
                    if row["reviewer"] != user:
                        foreign.add(row["version"])
            revising = Counter(v.revises for v in versions if v.revises is not None)
            edited_in_place = {version for version in foreign if edits[version] > revising[version]}
            return {
                "versions": [entry_view(v) for v in own if v.version not in edited_in_place],
                "reviews": [],
            }
        require(profile, REVIEW, MUTATE)
        raise not_found()

    @router.post("/assistant/knowledge/entries/{entry_id}/versions/{version}/edit")
    def edit(
        entry_id: str, version: int, body: EditRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        def reach(who: dict[str, Any]) -> None:
            found(kb.store.get(entry_id, version), who)
            if body.replaces is not None:
                found(kb.store.current(body.replaces), who)

        require(profile, REVIEW)
        reach(profile)
        # A fix started from the AI's answer may not gain a placeholder in an edit either
        # (one left by redaction on save stays the reviewer's to judge). Other entries keep
        # main's behaviour, where a reviewer may add one (e.g. a follow-up about "[UEN]").
        shown = kb.store.get(entry_id, version)
        if shown is not None and shown.started_from_answer:
            had = set(placeholders_left(shown.title, shown.body, *shown.follow_ups))
            added = [
                token
                for token in placeholders_left(
                    body.title or "", body.body or "", *(body.follow_ups or ())
                )
                if token not in had
            ]
            if added:
                raise placeholder_refused(added)
        changes: dict[str, Any] = {}
        for name in ("title", "body", "replaces"):
            value = getattr(body, name)
            if value is not None:
                changes[name] = value
        if body.replaces is None and "replaces" in body.model_fields_set:
            # An explicit null clears what the version replaces; leaving it out keeps it.
            changes["replaces"] = None
        for name in ("follow_ups", "blocker_codes", "fields", "stages"):
            value = getattr(body, name)
            if value is not None:
                changes[name] = tuple(value)
        if body.visibility is not None:
            changes["visibility"] = Visibility(
                roles=tuple(body.visibility.roles), teams=tuple(body.visibility.teams)
            )
        try:
            revised = kb.store.revise_pending(
                entry_id,
                version,
                editor=user_id(profile),
                expected_hash=body.content_hash,
                authorize=recheck(request, profile, REVIEW, reach),
                **changes,
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return entry_view(revised)

    @router.post("/assistant/knowledge/entries/{entry_id}/versions/{version}/decision")
    def decide(
        entry_id: str, version: int, body: DecisionRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        def reach(who: dict[str, Any]) -> None:
            found(kb.store.get(entry_id, version), who)

        require(profile, REVIEW)
        reach(profile)
        try:
            decided = kb.decide(
                entry_id,
                version,
                reviewer=user_id(profile),
                approve=body.approve,
                notes=body.notes,
                expected_hash=body.content_hash,
                authorize=recheck(request, profile, REVIEW, reach),
                single_reviewer=single_reviewer,
                confirmed=body.confirm_single_reviewer,
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return entry_view(
            decided,
            single_reviewer=decided.status == EntryStatus.APPROVED
            and decided.key in kb.store.single_reviewer_approvals(),
        )

    @router.post("/assistant/knowledge/entries/{entry_id}/retire")
    def retire(
        entry_id: str, body: RetireRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        def reach(who: dict[str, Any]) -> None:
            found(kb.store.current(entry_id), who)

        require(profile, REVIEW)
        reach(profile)
        # Two people: the first call asks for the retirement, a different reviewer confirms.
        try:
            current, retired = kb.request_retirement(
                entry_id,
                by=user_id(profile),
                notes=body.notes,
                authorize=recheck(request, profile, REVIEW, reach),
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return {
            "retirement": "done" if retired else "requested",
            "entry": entry_view(current),
        }

    @router.post("/assistant/knowledge/feedback/{feedback_id}/draft")
    def draft(
        feedback_id: int, body: FixRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        # A Director writes the fix for an open request: a past resolution or a guidance
        # change, linked to the request and pending review like any other entry. Approving it
        # resolves the request; rejecting it opens the request again.
        target: str | None = None
        if body.kind == "guidance":
            target = body.entry_id or guidance_id(body.title)
            if not re.fullmatch(GUIDANCE_ID, target):
                raise HTTPException(
                    422,
                    detail={
                        "code": "INVALID_ENTRY_ID",
                        "message": "Give this guidance an entry id.",
                    },
                )
        in_request = request_in_scope(feedback_id)

        def reach(who: dict[str, Any]) -> None:
            # Changing existing guidance needs its current approved version in scope (or, with
            # none approved yet, its latest version).
            in_request(who)
            existing = (kb.store.current(target) or kb.store.get(target)) if target else None
            if existing is not None:
                found(existing, who)

        require(profile, REVIEW)
        reach(profile)
        # A fix started from the AI's answer must not keep its placeholders: they stand for
        # this client's details and would read as a rule about "[ADDRESS]".
        left = placeholders_left(body.title, body.body, *body.follow_ups)
        if left:
            raise placeholder_refused(left)
        author = user_id(profile)
        # The fix is written from a client's case: redact it against that case's values and
        # parties (loaded with this Director's own session; a case they cannot load stops the
        # change), then the identifier patterns. The reviewer sees the result before it can go
        # live.
        request_row = next(
            row for row in team_feedback(profile, helpful=False) if row["id"] == feedback_id
        )
        # Only a request with an answer record can have a fix started from it.
        started = body.started_from_answer and request_row["answer_id"] is not None
        snapshot = load_case(UUID(request_row["case_id"]), request)
        redact = Redactor(build_case_facts(snapshot), parties=case_parties(snapshot.summary)).redact

        def build(row: dict[str, Any]) -> Entry:
            if body.kind == "resolution":
                return resolution_from_request(
                    row,
                    author=author,
                    title=body.title,
                    body=body.body,
                    redact=redact,
                    follow_ups=body.follow_ups,
                ).with_changes(started_from_answer=started)
            assert target is not None
            current = kb.store.current(target)
            visibility = (
                Visibility(roles=tuple(body.visibility.roles), teams=tuple(body.visibility.teams))
                if body.visibility is not None
                else current.visibility
                if current is not None
                else Visibility()
            )

            def context(given: list[str] | None, name: str) -> tuple[str, ...]:
                return tuple(given) if given is not None else tuple(row[name])

            return Entry(
                entry_id=target,
                kind=EntryKind.GUIDANCE,
                title=redact(" ".join(body.title.split())),
                body=redact(body.body.strip()),
                blocker_codes=context(body.blocker_codes, "blocker_codes"),
                fields=context(body.fields, "fields"),
                stages=context(body.stages, "stages"),
                visibility=visibility,
                source_ref=body.source_ref,
                author=author,
                started_from_answer=started,
            )

        try:
            drafted = kb.store.draft_request(
                feedback_id, build, authorize=recheck(request, profile, REVIEW, reach)
            )
        except KnowledgeError as exc:
            if isinstance(exc, KnowledgeRuleError):
                raise refused(exc) from None
            raise request_refused(exc) from None
        return entry_view(drafted)

    @router.post("/assistant/knowledge/feedback/{feedback_id}/close")
    def close(
        feedback_id: int, body: CloseRequest, profile: Actor, request: Request
    ) -> dict[str, str]:
        reach = request_in_scope(feedback_id)
        require(profile, REVIEW)
        reach(profile)
        try:
            kb.store.close_feedback(
                feedback_id,
                by=user_id(profile),
                reason=body.reason,
                authorize=recheck(request, profile, REVIEW, reach),
            )
        except KnowledgeError as exc:
            raise request_refused(exc) from None
        return {"status": "closed"}

    @router.post("/assistant/knowledge/reindex")
    def reindex(profile: Actor, request: Request) -> dict[str, int]:
        require(profile, REVIEW)
        # Re-embeds every current approved version, so a changed embedding model takes effect.
        report = kb.rebuild(authorize=recheck(request, profile, REVIEW))
        return {"indexed": report.indexed, "removed": report.removed, "waiting": report.failed}

    @router.get("/assistant/knowledge/stats")
    def stats(profile: Actor) -> dict[str, Any]:
        require(profile, REVIEW)
        feedback_rows = team_feedback(profile)
        helpful = sum(1 for row in feedback_rows if row["helpful"])
        # Confidence by topic: the ratings given on cases with each blocker code (a rating on
        # a case with no blocker code counts only in the totals).
        by_topic: dict[str, dict[str, int]] = {}
        for row in feedback_rows:
            for code in dict.fromkeys(row["blocker_codes"]):
                counts = by_topic.setdefault(code, {"helpful": 0, "not_helpful": 0})
                counts["helpful" if row["helpful"] else "not_helpful"] += 1
        return {
            "entries": team_entry_counts(profile),
            "feedback": {
                "total": len(feedback_rows),
                "helpful": helpful,
                "not_helpful": len(feedback_rows) - helpful,
                "helpful_rate": round(helpful / len(feedback_rows), 3) if feedback_rows else None,
                "open_gaps": sum(
                    1 for row in feedback_rows if not row["helpful"] and row["status"] == "open"
                ),
            },
            "by_topic": dict(sorted(by_topic.items())),
        }

    # --- HR guidance changes --------------------------------------------------------

    @router.post("/assistant/knowledge/guidance")
    def propose_guidance(body: GuidanceRequest, profile: Actor, request: Request) -> dict[str, Any]:
        require(profile, MUTATE)
        entry_id = body.entry_id or guidance_id(body.title)
        if not re.fullmatch(GUIDANCE_ID, entry_id):
            raise HTTPException(
                422,
                detail={"code": "INVALID_ENTRY_ID", "message": "Give this guidance an entry id."},
            )
        try:
            proposed = kb.propose(
                Entry(
                    entry_id=entry_id,
                    kind=EntryKind.GUIDANCE,
                    title=body.title,
                    body=body.body,
                    blocker_codes=tuple(body.blocker_codes),
                    fields=tuple(body.fields),
                    stages=tuple(body.stages),
                    visibility=Visibility(
                        roles=tuple(body.visibility.roles), teams=tuple(body.visibility.teams)
                    ),
                    source_ref=body.source_ref,
                    illustrative=body.illustrative,
                    author=user_id(profile),
                ),
                authorize=recheck(request, profile, MUTATE),
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return entry_view(proposed)

    return router
