"""Feedback and review endpoints for the knowledge loop.

    RM / Client Onboarder  POST /assistant/cases/{id}/feedback      "Solved it" / "Not helpful"
    Director (POLICY_APPROVE)   review queue, edit, approve/reject, retire, re-index, stats
    HR (POLICY_MUTATE)          propose new guidance or a new version of guidance

Who someone is, and what they may do, always comes from the CLM backend (/api/auth/me with
their own session); nothing in a request body can grant a permission. The author of an entry
can never approve or reject it (enforced by the store).
"""

from collections.abc import Callable
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .context import build_case_facts
from .knowledge.drafting import draft_resolution
from .knowledge.models import Entry, EntryKind, EntryStatus, Visibility
from .knowledge.redaction import Redactor
from .knowledge.retrieval import case_context
from .knowledge.service import KnowledgeBase
from .knowledge.store import KnowledgeError, MakerCheckerError

APPROVE = "POLICY_APPROVE"
MUTATE = "POLICY_MUTATE"


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpful: bool
    note: str = Field(default="", max_length=1000)
    turns: list[Turn] = Field(default_factory=list, max_length=40)


class FeedbackResponse(BaseModel):
    feedback_id: int
    draft_entry_id: str | None
    message: str


class VisibilityBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    roles: list[str] = Field(default_factory=list, max_length=10)
    teams: list[str] = Field(default_factory=list, max_length=20)


class EditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    notes: str = Field(default="", max_length=1000)


class RetireRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str = Field(min_length=3, max_length=1000)


class GuidanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry_id: str | None = Field(default=None, pattern=r"^guidance\.[a-z0-9-]{3,80}$")
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=4000)
    source_ref: str = Field(min_length=3, max_length=300)
    blocker_codes: list[str] = Field(default_factory=list, max_length=20)
    fields: list[str] = Field(default_factory=list, max_length=20)
    stages: list[str] = Field(default_factory=list, max_length=20)
    visibility: VisibilityBody = Field(default_factory=VisibilityBody)
    illustrative: bool = False


def entry_view(entry: Entry) -> dict[str, Any]:
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
        "author": entry.author,
        "approver": entry.approver,
        "approved_at": entry.approved_at,
        "created_at": entry.created_at,
        "source_ref": entry.source_ref,
        "illustrative": entry.illustrative,
    }


AUTHOR_MESSAGE = "You cannot approve or reject an entry you wrote."
CHANGED_MESSAGE = "This entry has changed or was already decided. Refresh and try again."


def knowledge_router(
    *,
    kb: KnowledgeBase,
    backend: ClmBackendClient,
    check_origin: Callable[[Request], None],
    load_case: Callable[..., CaseSnapshot],
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

    def found(entry: Entry | None) -> Entry:
        if entry is None:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "No such entry."})
        return entry

    def refused(exc: KnowledgeError) -> HTTPException:
        # Fixed messages only: the browser shows nothing else (apps/frontend aiAssistant.ts).
        if isinstance(exc, MakerCheckerError):
            return HTTPException(403, detail={"code": "MAKER_CHECKER", "message": AUTHOR_MESSAGE})
        return HTTPException(409, detail={"code": "NOT_ALLOWED", "message": CHANGED_MESSAGE})

    # --- RM feedback ----------------------------------------------------------------

    @router.post("/assistant/cases/{case_id}/feedback", response_model=FeedbackResponse)
    def feedback(case_id: UUID, body: FeedbackRequest, snapshot: Snapshot) -> FeedbackResponse:
        profile = snapshot.actor.get("profile") or {}
        facts = build_case_facts(snapshot)
        ctx = case_context(facts)
        turns = [turn.model_dump() for turn in body.turns]
        note = Redactor(facts).redact(body.note)
        draft_id: str | None = None
        if body.helpful:
            draft = kb.propose(draft_resolution(facts, turns, body.note, author=user_id(profile)))
            draft_id = draft.entry_id
        feedback_id = kb.store.add_feedback(
            case_id=str(case_id),
            user_id=user_id(profile),
            role=profile.get("role"),
            team=profile.get("team_id"),
            helpful=body.helpful,
            note=note,
            blocker_codes=ctx.blocker_codes,
            fields=ctx.fields,
            stages=ctx.stages,
            entry_id=draft_id,
        )
        return FeedbackResponse(
            feedback_id=feedback_id,
            draft_entry_id=draft_id,
            message=(
                # The RM only needs a short thanks; the Director review behind it is not
                # their concern (and a one-click "Yes, helpful" should not feel like a task).
                "Thanks for your feedback."
                if body.helpful
                else "Thanks. This has been flagged so the answer can be improved."
            ),
        )

    # --- who may do what (for the UI; the endpoints check again) --------------------

    @router.get("/assistant/knowledge/me")
    def me(profile: Actor) -> dict[str, Any]:
        return {
            "user_id": profile.get("user_id"),
            "can_review": can(profile, APPROVE),
            "can_edit_guidance": can(profile, MUTATE),
        }

    # --- Director review ------------------------------------------------------------

    @router.get("/assistant/knowledge/reviews")
    def reviews(profile: Actor) -> dict[str, Any]:
        require(profile, APPROVE)
        return {
            "pending": [entry_view(e) for e in kb.store.entries(status=EntryStatus.PENDING_REVIEW)],
            "gaps": kb.store.feedback(status="open"),
        }

    @router.get("/assistant/knowledge/entries")
    def entries(profile: Actor, kind: EntryKind | None = None) -> list[dict[str, Any]]:
        require(profile, APPROVE, MUTATE)
        return [entry_view(e) for e in kb.store.entries(status=EntryStatus.APPROVED, kind=kind)]

    @router.get("/assistant/knowledge/entries/{entry_id}")
    def entry(entry_id: str, profile: Actor) -> dict[str, Any]:
        versions = kb.store.versions(entry_id)
        if not versions:
            found(None)
        is_author = any(v.author == profile.get("user_id") for v in versions)
        if not is_author:
            require(profile, APPROVE, MUTATE)
        return {
            "versions": [entry_view(v) for v in versions],
            "reviews": kb.store.reviews(entry_id),
        }

    @router.post("/assistant/knowledge/entries/{entry_id}/versions/{version}/edit")
    def edit(entry_id: str, version: int, body: EditRequest, profile: Actor) -> dict[str, Any]:
        require(profile, APPROVE)
        changes: dict[str, Any] = {}
        for name in ("title", "body", "replaces"):
            value = getattr(body, name)
            if value is not None:
                changes[name] = value
        for name in ("follow_ups", "blocker_codes", "fields", "stages"):
            value = getattr(body, name)
            if value is not None:
                changes[name] = tuple(value)
        if body.visibility is not None:
            changes["visibility"] = Visibility(
                roles=tuple(body.visibility.roles), teams=tuple(body.visibility.teams)
            )
        if body.replaces is not None:
            found(kb.store.current(body.replaces))
        try:
            revised = kb.store.revise_pending(entry_id, version, editor=user_id(profile), **changes)
        except KnowledgeError as exc:
            raise refused(exc) from None
        return entry_view(revised)

    @router.post("/assistant/knowledge/entries/{entry_id}/versions/{version}/decision")
    def decide(
        entry_id: str, version: int, body: DecisionRequest, profile: Actor
    ) -> dict[str, Any]:
        require(profile, APPROVE)
        found(kb.store.get(entry_id, version))
        try:
            decided = kb.decide(
                entry_id,
                version,
                reviewer=user_id(profile),
                approve=body.approve,
                notes=body.notes,
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return entry_view(decided)

    @router.post("/assistant/knowledge/entries/{entry_id}/retire")
    def retire(entry_id: str, body: RetireRequest, profile: Actor) -> dict[str, Any]:
        require(profile, APPROVE)
        retired = found(kb.retire(entry_id, by=user_id(profile), notes=body.notes))
        return entry_view(retired)

    @router.post("/assistant/knowledge/feedback/{feedback_id}/close")
    def close(feedback_id: int, profile: Actor) -> dict[str, str]:
        require(profile, APPROVE)
        try:
            kb.store.close_feedback(feedback_id, by=user_id(profile))
        except KnowledgeError:
            raise HTTPException(404, detail={"code": "NOT_FOUND"}) from None
        return {"status": "closed"}

    @router.post("/assistant/knowledge/reindex")
    def reindex(profile: Actor) -> dict[str, int]:
        require(profile, APPROVE)
        report = kb.reconcile()
        return {"indexed": report.indexed, "removed": report.removed, "waiting": report.failed}

    @router.get("/assistant/knowledge/stats")
    def stats(profile: Actor) -> dict[str, Any]:
        require(profile, APPROVE)
        feedback_rows = kb.store.feedback()
        helpful = sum(1 for row in feedback_rows if row["helpful"])
        return {
            "entries": kb.status(),
            "feedback": {
                "total": len(feedback_rows),
                "helpful": helpful,
                "not_helpful": len(feedback_rows) - helpful,
                "helpful_rate": round(helpful / len(feedback_rows), 3) if feedback_rows else None,
                "open_gaps": sum(1 for row in feedback_rows if row["status"] == "open"),
            },
        }

    # --- HR guidance changes --------------------------------------------------------

    @router.post("/assistant/knowledge/guidance")
    def propose_guidance(body: GuidanceRequest, profile: Actor) -> dict[str, Any]:
        require(profile, MUTATE)
        entry_id = (
            body.entry_id
            or "guidance."
            + "-".join("".join(ch if ch.isalnum() else " " for ch in body.title.lower()).split())[
                :80
            ]
        )
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
            )
        )
        return entry_view(proposed)

    return router
