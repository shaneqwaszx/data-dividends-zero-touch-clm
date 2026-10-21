"""Find the knowledge entries that apply to this question on this case.

A similar-sounding entry is not necessarily the right one, so the case context and the
user's permissions decide what may be used, and similarity only ranks what is left:

1. Context: blocker codes, fields and stages taken from the live case facts.
2. Hard filters: approved and current only; the user's role and team must be allowed;
   a past resolution must share a blocker code or field with the case (when the case has
   any), so a case about a different problem is never reused.
3. Hybrid search: vector similarity (meaning) plus keyword search (exact codes and labels);
   entries that match the case's blocker codes are always considered.
4. Rerank: one relevance score from meaning, keywords and case-context match; recency then
   breaks ties (newer approved entries rank higher) but never makes an entry relevant.
   Weights are settings, tuned on the labelled set.
5. Threshold: entries below the minimum score are not used.
6. Fallback: if no guidance passes, the best stage-level guidance is used, marked as such.

If the embedding model is down, retrieval still works on keywords and context (degraded).
"""

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from ..guide import FIELD_LABEL
from .embeddings import EmbeddingUnavailableError
from .models import Entry, EntryKind, EntryStatus
from .service import KnowledgeBase

_LABEL_TO_FIELD = {label: key for key, label in FIELD_LABEL.items()}


@dataclass(frozen=True)
class CaseContext:
    blocker_codes: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not (self.blocker_codes or self.fields or self.stages)


def _field_key(label: Any) -> str | None:
    if not label:
        return None
    text = str(label)
    return _LABEL_TO_FIELD.get(text, text.replace(" ", "_").lower())


def case_context(facts: dict[str, Any]) -> CaseContext:
    """Blocker codes, fields and case page sections the case is currently stuck on."""

    codes: list[str] = []
    fields: list[str] = []
    stages: list[str] = []

    def add(bucket: list[str], value: Any) -> None:
        if value and str(value) not in bucket:
            bucket.append(str(value))

    for blocker in facts.get("blockers") or []:
        add(codes, blocker.get("code"))
        for row in blocker.get("differences") or []:
            add(fields, _field_key(row.get("field")))
    for code in (facts.get("readiness") or {}).get("blockers") or []:
        add(codes, code)
    for item in facts.get("discrepancies") or []:
        add(fields, _field_key(item.get("field")))
    for row in (facts.get("document_field_review") or {}).get("fields") or []:
        add(fields, _field_key(row.get("field")))
    for need in facts.get("still_needed_before_goldtier") or []:
        add(stages, need.get("where_on_the_case_page"))
    for step in facts.get("steps") or []:
        if step.get("status") not in {"done", "skipped", "not reached yet"}:
            add(stages, step.get("step"))
    return CaseContext(tuple(codes), tuple(fields), tuple(stages))


@dataclass(frozen=True)
class Weights:
    semantic: float = 0.45
    keyword: float = 0.2
    context: float = 0.3
    recency: float = 0.05


@dataclass(frozen=True)
class RetrievalSettings:
    weights: Weights = field(default_factory=Weights)
    min_score_guidance: float = 0.3
    min_score_resolution: float = 0.4
    max_guidance: int = 3
    max_resolutions: int = 3
    candidates: int = 20
    # BM25 score at which a keyword match counts as half of a perfect match.
    keyword_half_score: float = 3.0
    # Days for the recency score to halve (newer approved entries rank a little higher).
    recency_half_life_days: float = 180.0


@dataclass(frozen=True)
class Hit:
    entry: Entry
    score: float
    parts: dict[str, float]
    # True when used only because nothing better passed (stage-level guidance).
    fallback: bool = False


@dataclass(frozen=True)
class Retrieval:
    guidance: tuple[Hit, ...] = ()
    resolutions: tuple[Hit, ...] = ()
    # high: a specific entry passed the threshold; low: only fallback guidance; none.
    confidence: Literal["high", "low", "none"] = "none"
    # The embedding model was not available, so only keywords and context were used.
    degraded: bool = False

    @property
    def hits(self) -> tuple[Hit, ...]:
        return self.guidance + self.resolutions


def _overlap(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    if not a or not b:
        return 0.0
    return 1.0 if set(a) & set(b) else 0.0


def context_score(entry: Entry, ctx: CaseContext) -> float:
    """How well an entry fits the case: same blocker code 0.6, same field 0.3, same stage 0.1."""

    return (
        0.6 * _overlap(entry.blocker_codes, ctx.blocker_codes)
        + 0.3 * _overlap(entry.fields, ctx.fields)
        + 0.1 * _overlap(entry.stages, ctx.stages)
    )


def _recency(entry: Entry, now: datetime, half_life: float) -> float:
    if not entry.approved_at:
        return 0.0
    try:
        approved = datetime.fromisoformat(entry.approved_at)
    except ValueError:
        return 0.0
    if approved.tzinfo is None:
        approved = approved.replace(tzinfo=UTC)
    days = max(0.0, (now - approved).total_seconds() / 86400)
    return math.pow(0.5, days / half_life)


class Retriever:
    def __init__(
        self,
        kb: KnowledgeBase,
        settings: RetrievalSettings | None = None,
        *,
        clock: Any = None,
    ) -> None:
        self.kb = kb
        self.settings = settings or RetrievalSettings()
        self._clock = clock or (lambda: datetime.now(UTC))

    def retrieve(
        self,
        question: str,
        ctx: CaseContext,
        *,
        role: str | None,
        team: str | None,
    ) -> Retrieval:
        degraded = False
        try:
            query_vector: list[float] | None = self.kb.embedder.embed_query(question)
        except EmbeddingUnavailableError:
            query_vector, degraded = None, True
        guidance = self._rank(EntryKind.GUIDANCE, question, query_vector, ctx, role, team)
        resolutions = self._rank(EntryKind.RESOLUTION, question, query_vector, ctx, role, team)
        s = self.settings
        # The most relevant entries are chosen by score; among them, confirmed guidance is
        # listed before placeholder (illustrative) guidance, the same order of authority the
        # model is told (case facts, then rules, then examples).
        good_guidance = [h for h in guidance if h.score >= s.min_score_guidance][: s.max_guidance]
        good_guidance.sort(key=lambda h: h.entry.illustrative)  # stable within each group
        good_resolutions = [h for h in resolutions if h.score >= s.min_score_resolution][
            : s.max_resolutions
        ]
        confidence: Literal["high", "low", "none"] = (
            "high" if good_guidance or good_resolutions else "none"
        )
        if not good_guidance:
            stage_level = [h for h in guidance if h.parts["context"] > 0]
            if stage_level:
                best = stage_level[0]
                good_guidance = [Hit(best.entry, best.score, best.parts, fallback=True)]
                if confidence == "none":
                    confidence = "low"
        return Retrieval(
            guidance=tuple(good_guidance),
            resolutions=tuple(good_resolutions),
            confidence=confidence,
            degraded=degraded,
        )

    # --- one kind -------------------------------------------------------------------

    def _rank(
        self,
        kind: EntryKind,
        question: str,
        query_vector: list[float] | None,
        ctx: CaseContext,
        role: str | None,
        team: str | None,
    ) -> list[Hit]:
        s = self.settings
        semantic: dict[str, float] = {}
        if query_vector is not None:
            for key, similarity, _meta in self.kb.index.search(
                kind, query_vector, limit=s.candidates
            ):
                semantic[key] = max(0.0, similarity)
        keyword_raw = dict(
            self.kb.store.keyword_search(question, kinds=(kind,), limit=s.candidates)
        )
        top_keyword = max(keyword_raw.values(), default=0.0)
        keyword = {k: (v / top_keyword if top_keyword > 0 else 0.0) for k, v in keyword_raw.items()}

        # Entries for the case's own blocker codes are always candidates.
        candidates: dict[str, Entry] = {}
        for entry in self.kb.store.entries(status=EntryStatus.APPROVED, kind=kind):
            if entry.key in semantic or entry.key in keyword or context_score(entry, ctx) > 0:
                candidates[entry.key] = entry

        now = self._clock()
        w = s.weights
        hits: list[Hit] = []
        for key, entry in candidates.items():
            if not entry.visibility.allows(role, team):
                continue
            ctx_score = context_score(entry, ctx)
            if kind == EntryKind.RESOLUTION and (ctx.blocker_codes or ctx.fields):
                same_problem = _overlap(entry.blocker_codes, ctx.blocker_codes) or _overlap(
                    entry.fields, ctx.fields
                )
                if not same_problem:
                    continue
            parts = {
                "semantic": semantic.get(key, 0.0),
                "keyword": keyword.get(key, 0.0),
                "context": ctx_score,
                "recency": _recency(entry, now, s.recency_half_life_days),
            }
            if query_vector is None:
                # Without meaning scores, their weight is shared by keywords and context.
                total = (w.keyword + w.context) or 1.0
                relevance = (parts["keyword"] * w.keyword + parts["context"] * w.context) / total
            else:
                total = (w.semantic + w.keyword + w.context) or 1.0
                relevance = (
                    parts["semantic"] * w.semantic
                    + parts["keyword"] * w.keyword
                    + parts["context"] * w.context
                ) / total
            # Recency only breaks ties between relevant entries; it never makes one relevant.
            score = relevance * (1 - w.recency + w.recency * parts["recency"])
            hits.append(Hit(entry=entry, score=round(score, 4), parts=parts))
        hits.sort(key=lambda h: (-h.score, h.entry.entry_id))
        return hits


def settings_from(config: Any) -> RetrievalSettings:
    return RetrievalSettings(
        weights=Weights(
            semantic=config.retrieval_weight_semantic,
            keyword=config.retrieval_weight_keyword,
            context=config.retrieval_weight_context,
            recency=config.retrieval_weight_recency,
        ),
        min_score_guidance=config.retrieval_min_score_guidance,
        min_score_resolution=config.retrieval_min_score_resolution,
        max_guidance=config.retrieval_max_guidance,
        max_resolutions=config.retrieval_max_resolutions,
    )
