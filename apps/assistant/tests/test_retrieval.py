"""Milestone 2: retrieval (filters, permissions, hybrid search, rerank, threshold, fallback)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_assistant.clm_client import CaseSnapshot
from ai_assistant.context import build_case_facts
from ai_assistant.knowledge.evaluation import evaluate, load_labelled
from ai_assistant.knowledge.ingest import ingest_guidance, ingest_synthetic_resolutions
from ai_assistant.knowledge.models import Entry, EntryKind, Visibility
from ai_assistant.knowledge.retrieval import CaseContext, Retriever, case_context
from ai_assistant.knowledge.service import KnowledgeBase
from tests.test_ai_assistant import DOCUMENTS, ME, SUMMARY
from tests.test_knowledge_store import _kb

LABELLED = Path(__file__).parent / "fixtures" / "knowledge_eval.json"
ADDRESS = CaseContext(
    blocker_codes=("DOCUMENT_SOURCE_CONFLICT",),
    fields=("registered_address",),
    stages=("Document verification",),
)
RM = {"role": "RELATIONSHIP_MANAGER", "team": "TEAM_A"}


@pytest.fixture
def kb(tmp_path: Path) -> KnowledgeBase:
    knowledge = _kb(tmp_path)
    ingest_guidance(knowledge)
    ingest_synthetic_resolutions(knowledge)
    return knowledge


def _approve(kb: KnowledgeBase, entry: Entry) -> Entry:
    proposed = kb.propose(entry)
    return kb.decide(proposed.entry_id, proposed.version, reviewer="director-dan", approve=True)


def _resolution(entry_id: str, **changes: object) -> Entry:
    return Entry(
        entry_id=entry_id,
        kind=EntryKind.RESOLUTION,
        title="Address differs from ACRA after an office move",
        body="Kept the registry value; the client updated ACRA later.",
        blocker_codes=("DOCUMENT_SOURCE_CONFLICT",),
        fields=("registered_address",),
        author="maya-lim",
    ).with_changes(**changes)


def test_labelled_questions_find_the_right_entries_and_nothing_for_off_topic(
    kb: KnowledgeBase,
) -> None:
    result = evaluate(Retriever(kb), load_labelled(LABELLED))
    assert result.questions >= 20
    assert result.recall_at_k >= 0.9, result.misses
    assert result.correct_nothing_rate == 1.0, result.misses


def test_the_case_context_comes_from_the_live_case_facts() -> None:
    facts = build_case_facts(CaseSnapshot(summary=SUMMARY, documents=DOCUMENTS, actor=ME))
    ctx = case_context(facts)
    assert "DOCUMENT_SOURCE_CONFLICT" in ctx.blocker_codes
    assert "registered_address" in ctx.fields
    assert "Document verification" in ctx.stages


def test_an_entry_the_user_may_not_see_is_never_retrieved(kb: KnowledgeBase) -> None:
    _approve(kb, _resolution("resolution.team-b-only", visibility=Visibility(teams=("TEAM_B",))))
    question = "the client moved office and the address differs"
    seen_by_a = Retriever(kb).retrieve(question, ADDRESS, **RM)
    seen_by_b = Retriever(kb).retrieve(
        question, ADDRESS, role="RELATIONSHIP_MANAGER", team="TEAM_B"
    )
    assert "resolution.team-b-only" not in [h.entry.entry_id for h in seen_by_a.hits]
    assert "resolution.team-b-only" in [h.entry.entry_id for h in seen_by_b.hits]


def test_a_past_case_about_a_different_problem_is_never_reused(kb: KnowledgeBase) -> None:
    result = Retriever(kb).retrieve("what ownership evidence did they upload?", ADDRESS, **RM)
    ids = [h.entry.entry_id for h in result.resolutions]
    assert "resolution.synthetic-missing-shareholder-register" not in ids


def test_retired_entries_are_never_retrieved(kb: KnowledgeBase) -> None:
    kb.retire("guidance.address-mismatch", by="director-dan", notes="policy changed")
    result = Retriever(kb).retrieve("can I use the document address?", ADDRESS, **RM)
    assert "guidance.address-mismatch" not in [h.entry.entry_id for h in result.hits]


def test_a_newer_approved_resolution_ranks_above_an_older_one(tmp_path: Path) -> None:
    times = iter(["2025-01-01T00:00:00+00:00"] * 3 + ["2026-10-01T00:00:00+00:00"] * 3)
    knowledge = _kb(tmp_path)
    knowledge.store._clock = lambda: next(times)  # type: ignore[method-assign]
    _approve(knowledge, _resolution("resolution.older"))
    _approve(knowledge, _resolution("resolution.newer"))
    retriever = Retriever(knowledge, clock=lambda: datetime(2026, 10, 20, tzinfo=UTC))
    result = retriever.retrieve("client moved office, address differs", ADDRESS, **RM)
    assert [h.entry.entry_id for h in result.resolutions][:2] == [
        "resolution.newer",
        "resolution.older",
    ]


def test_without_the_embedding_model_keywords_and_context_still_work(kb: KnowledgeBase) -> None:
    kb.embedder.down = True  # type: ignore[attr-defined]
    result = Retriever(kb).retrieve("Can I keep the registry value?", ADDRESS, **RM)
    assert result.degraded
    assert result.guidance[0].entry.entry_id == "guidance.address-mismatch"


def test_when_nothing_specific_passes_stage_guidance_is_a_marked_fallback(
    kb: KnowledgeBase,
) -> None:
    final_review = CaseContext(stages=("Final review & send",))
    result = Retriever(kb).retrieve("anything else?", final_review, **RM)
    assert result.confidence in {"high", "low"}
    assert result.guidance and result.guidance[0].entry.entry_id == "guidance.review-and-send"
    if result.confidence == "low":
        assert result.guidance[0].fallback


def test_off_topic_questions_without_context_retrieve_nothing(kb: KnowledgeBase) -> None:
    result = Retriever(kb).retrieve("What is the weather today?", CaseContext(), **RM)
    assert result.confidence == "none" and result.hits == ()


def test_confirmed_guidance_ranks_above_placeholder_guidance(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    ingest_guidance(kb)
    ctx = CaseContext(
        blocker_codes=("DOCUMENT_REQUIRED", "DOCUMENT_REVIEW_INCOMPLETE"),
        fields=("registration_number", "legal_name"),
        stages=("Document verification",),
    )
    hits = (
        Retriever(kb)
        .retrieve("Which document shows the UEN and legal name?", ctx, role=None, team=None)
        .guidance
    )
    flags = [hit.entry.illustrative for hit in hits]
    assert True in flags and False in flags, [hit.entry.entry_id for hit in hits]
    assert flags == sorted(flags)  # every confirmed entry first, the placeholder after
