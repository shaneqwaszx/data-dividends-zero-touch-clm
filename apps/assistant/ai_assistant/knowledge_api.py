"""Feedback and review endpoints for the knowledge loop.

    RM / Client Onboarder  POST /assistant/cases/{id}/feedback      "Solved it" / "Not helpful"
    Director (POLICY_APPROVE)   review queue, edit, approve/reject, retire, re-index, stats
    HR (POLICY_MUTATE)          propose new guidance or a new version of guidance

Who someone is, and what they may do, always comes from the CLM backend (/api/auth/me with
their own session); nothing in a request body can grant a permission. Nobody who wrote or
edited an entry can approve or reject it, and a decision applies only to the exact content
the reviewer was shown (both enforced by the store). Every review or guidance change asks
the backend again inside its write transaction, so a role, team or session withdrawn since
the request began stops it.

Team scope: approved past resolutions are visible only to the team they came from. A Director,
whom the CLM backend scopes globally (a Director has no team), sees, edits and decides every
team's drafts and gaps, and their stats count every team. Any other caller keeps the team
rule: anything outside their team is answered as "not found", and stats count only their
team's entries and feedback. Guidance proposed by HR keeps the visibility HR set. An edit can
narrow team and role visibility, never widen it.

Retiring an approved entry (official guidance included) takes two reviewers: the first POST
to /retire records the request, a different reviewer's POST confirms it.
"""

import re
from collections import Counter
from collections.abc import Callable
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .clm_client import SESSION_COOKIE_NAME, CaseSnapshot, ClmBackendClient, ClmBackendError
from .context import build_case_facts
from .knowledge.drafting import draft_resolution
from .knowledge.models import Entry, EntryKind, EntryStatus, Visibility
from .knowledge.redaction import Redactor, case_parties
from .knowledge.retrieval import case_context
from .knowledge.service import KnowledgeBase
from .knowledge.store import (
    KnowledgeError,
    KnowledgeRuleError,
    MakerCheckerError,
    SecondReviewerError,
)

APPROVE = "POLICY_APPROVE"
MUTATE = "POLICY_MUTATE"
_HASH = r"^[0-9a-f]{64}$"
GUIDANCE_ID = r"^guidance\.[a-z0-9-]{3,80}$"


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpful: bool
    note: str = Field(default="", max_length=1000)
    # The browser sends the conversation; only the RM's own questions are used (an
    # "assistant" turn here is not proof of what the assistant said).
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
        "revises": entry.revises,
        "author": entry.author,
        "approver": entry.approver,
        "approved_at": entry.approved_at,
        "created_at": entry.created_at,
        "source_ref": entry.source_ref,
        "illustrative": entry.illustrative,
        "content_hash": entry.content_hash(),
    }


AUTHOR_MESSAGE = "You cannot approve or reject an entry you wrote or edited."
CHANGED_MESSAGE = "This entry has changed or was already decided. Refresh and try again."
RULE_MESSAGE = "This change is not allowed."
NOT_FOUND_MESSAGE = "No such entry."
SECOND_REVIEWER_MESSAGE = "A different reviewer must confirm this."


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
        """A Director, whom the CLM backend scopes globally (a Director has no team), reviews
        every team's entries and gaps; anyone else keeps the team rule."""

        return profile.get("role") == "DIRECTOR" and team(profile) is None

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

    def team_feedback(profile: dict[str, Any], status: str | None = None) -> list[dict[str, Any]]:
        return [
            row
            for row in kb.store.feedback(status=status)
            if global_reviewer(profile) or row["team"] == team(profile)
        ]

    # --- RM feedback ----------------------------------------------------------------

    @router.post("/assistant/cases/{case_id}/feedback", response_model=FeedbackResponse)
    def feedback(case_id: UUID, body: FeedbackRequest, snapshot: Snapshot) -> FeedbackResponse:
        profile = snapshot.actor.get("profile") or {}
        facts = build_case_facts(snapshot)
        parties = case_parties(snapshot.summary)
        ctx = case_context(facts)
        turns = [turn.model_dump() for turn in body.turns]
        note = Redactor(facts, parties=parties).redact(body.note)
        draft_id: str | None = None
        if body.helpful:
            draft = kb.propose(
                draft_resolution(
                    facts,
                    turns,
                    body.note,
                    author=user_id(profile),
                    team=team(profile),
                    parties=parties,
                )
            )
            draft_id = draft.entry_id
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
            "pending": [
                entry_view(e)
                for e in kb.store.entries(status=EntryStatus.PENDING_REVIEW)
                if in_scope(e, profile)
            ],
            "gaps": team_feedback(profile, "open"),
        }

    @router.get("/assistant/knowledge/entries")
    def entries(profile: Actor, kind: EntryKind | None = None) -> list[dict[str, Any]]:
        require(profile, APPROVE, MUTATE)
        return [
            entry_view(e)
            for e in kb.store.entries(status=EntryStatus.APPROVED, kind=kind)
            if in_scope(e, profile)
        ]

    @router.get("/assistant/knowledge/entries/{entry_id}")
    def entry(entry_id: str, profile: Actor) -> dict[str, Any]:
        versions = kb.store.versions(entry_id)
        if not versions:
            raise not_found()
        reviewer = can(profile, APPROVE) or can(profile, MUTATE)
        if reviewer and in_scope(versions[-1], profile):
            return {
                "versions": [entry_view(v) for v in versions],
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
        require(profile, APPROVE, MUTATE)
        raise not_found()

    @router.post("/assistant/knowledge/entries/{entry_id}/versions/{version}/edit")
    def edit(
        entry_id: str, version: int, body: EditRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        def reach(who: dict[str, Any]) -> None:
            found(kb.store.get(entry_id, version), who)
            if body.replaces is not None:
                found(kb.store.current(body.replaces), who)

        require(profile, APPROVE)
        reach(profile)
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
                authorize=recheck(request, profile, APPROVE, reach),
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

        require(profile, APPROVE)
        reach(profile)
        try:
            decided = kb.decide(
                entry_id,
                version,
                reviewer=user_id(profile),
                approve=body.approve,
                notes=body.notes,
                expected_hash=body.content_hash,
                authorize=recheck(request, profile, APPROVE, reach),
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return entry_view(decided)

    @router.post("/assistant/knowledge/entries/{entry_id}/retire")
    def retire(
        entry_id: str, body: RetireRequest, profile: Actor, request: Request
    ) -> dict[str, Any]:
        def reach(who: dict[str, Any]) -> None:
            found(kb.store.current(entry_id), who)

        require(profile, APPROVE)
        reach(profile)
        # Two people: the first call asks for the retirement, a different reviewer confirms.
        try:
            current, retired = kb.request_retirement(
                entry_id,
                by=user_id(profile),
                notes=body.notes,
                authorize=recheck(request, profile, APPROVE, reach),
            )
        except KnowledgeError as exc:
            raise refused(exc) from None
        return {
            "retirement": "done" if retired else "requested",
            "entry": entry_view(current),
        }

    @router.post("/assistant/knowledge/feedback/{feedback_id}/close")
    def close(feedback_id: int, profile: Actor, request: Request) -> dict[str, str]:
        def reach(who: dict[str, Any]) -> None:
            if not any(row["id"] == feedback_id for row in team_feedback(who)):
                raise HTTPException(404, detail={"code": "NOT_FOUND"})

        require(profile, APPROVE)
        reach(profile)
        try:
            kb.store.close_feedback(
                feedback_id,
                by=user_id(profile),
                authorize=recheck(request, profile, APPROVE, reach),
            )
        except KnowledgeError:
            raise HTTPException(404, detail={"code": "NOT_FOUND"}) from None
        return {"status": "closed"}

    @router.post("/assistant/knowledge/reindex")
    def reindex(profile: Actor, request: Request) -> dict[str, int]:
        require(profile, APPROVE)
        # Re-embeds every current approved version, so a changed embedding model takes effect.
        report = kb.rebuild(authorize=recheck(request, profile, APPROVE))
        return {"indexed": report.indexed, "removed": report.removed, "waiting": report.failed}

    @router.get("/assistant/knowledge/stats")
    def stats(profile: Actor) -> dict[str, Any]:
        require(profile, APPROVE)
        feedback_rows = team_feedback(profile)
        helpful = sum(1 for row in feedback_rows if row["helpful"])
        return {
            "entries": team_entry_counts(profile),
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
