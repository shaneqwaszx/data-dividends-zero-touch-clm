"""Milestone 1: the reviewed knowledge store (SQLite + ChromaDB), without the model."""

import hashlib
import json
import math
import re
import shutil
from pathlib import Path

import httpx
import pytest

from ai_assistant.knowledge.embeddings import EmbeddingUnavailableError, OllamaEmbedder
from ai_assistant.knowledge.ingest import (
    DECISION_APPROVER,
    GUIDANCE_DIR,
    GuidanceFileError,
    ingest_guidance,
    ingest_synthetic_resolutions,
    parse_guidance,
)
from ai_assistant.knowledge.models import Entry, EntryKind, EntryStatus, Visibility
from ai_assistant.knowledge.service import KnowledgeBase
from ai_assistant.knowledge.store import KnowledgeError, KnowledgeStore, MakerCheckerError
from ai_assistant.knowledge.vector_index import VectorIndex


class HashEmbedder:
    """Deterministic stand-in for the embedding model: a bag of hashed words."""

    name = "hash-test"
    DIM = 64

    def __init__(self) -> None:
        self.down = False

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.DIM
        for word in re.findall(r"[a-z0-9_]+", text.lower()):
            slot = int(hashlib.sha256(word.encode()).hexdigest(), 16) % self.DIM
            vector[slot] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.down:
            raise EmbeddingUnavailableError("down")
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.down:
            raise EmbeddingUnavailableError("down")
        return self._vector(text)


def _kb(tmp_path: Path) -> KnowledgeBase:
    return KnowledgeBase(
        store=KnowledgeStore(tmp_path / "knowledge.sqlite3"),
        index=VectorIndex(tmp_path / "chroma"),
        embedder=HashEmbedder(),
    )


def _resolution(entry_id: str = "resolution.one", **changes: object) -> Entry:
    entry = Entry(
        entry_id=entry_id,
        kind=EntryKind.RESOLUTION,
        title="Address differs from ACRA",
        body="The RM kept the registry value after checking the document.",
        blocker_codes=("DOCUMENT_SOURCE_CONFLICT",),
        fields=("registered_address",),
        author="maya-lim",
    )
    return entry.with_changes(**changes) if changes else entry


# --- versions and maker-checker ---------------------------------------------------------


def test_each_change_is_a_new_version_and_nothing_is_overwritten(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    first = kb.propose(_resolution())
    second = kb.propose(_resolution(body="A clearer summary."))
    assert (first.version, second.version) == (1, 2)
    assert [v.body for v in kb.store.versions("resolution.one")] == [
        "The RM kept the registry value after checking the document.",
        "A clearer summary.",
    ]


def test_the_author_can_never_approve_or_reject_their_own_entry(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    entry = kb.propose(_resolution())
    for approve in (True, False):
        with pytest.raises(MakerCheckerError):
            kb.decide(entry.entry_id, entry.version, reviewer="maya-lim", approve=approve)
    assert kb.store.get(entry.entry_id).status == EntryStatus.PENDING_REVIEW


def test_approving_makes_it_searchable_and_records_the_review(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    entry = kb.propose(_resolution())
    approved = kb.decide(entry.entry_id, 1, reviewer="director-dan", approve=True, notes="ok")
    assert approved.status == EntryStatus.APPROVED and approved.approver == "director-dan"
    assert kb.index.keys(EntryKind.RESOLUTION) == {"resolution.one@v1"}
    assert [hit[0] for hit in kb.store.keyword_search("DOCUMENT_SOURCE_CONFLICT")] == [
        "resolution.one@v1"
    ]
    assert kb.store.reviews("resolution.one")[0]["decision"] == "approve"


def test_a_rejected_entry_is_never_searchable(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    entry = kb.propose(_resolution())
    kb.decide(entry.entry_id, 1, reviewer="director-dan", approve=False, notes="wrong")
    assert kb.index.keys(EntryKind.RESOLUTION) == set()
    assert kb.store.keyword_search("registry") == []
    with pytest.raises(KnowledgeError):
        kb.decide(entry.entry_id, 1, reviewer="director-dan", approve=True)


def test_a_new_approved_version_replaces_the_old_one_in_search(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    kb.decide(kb.propose(_resolution()).entry_id, 1, reviewer="director-dan", approve=True)
    kb.propose(_resolution(body="Updated: the client also updated ACRA later."))
    kb.decide("resolution.one", 2, reviewer="director-dan", approve=True)
    assert [v.status for v in kb.store.versions("resolution.one")] == [
        EntryStatus.RETIRED,
        EntryStatus.APPROVED,
    ]
    assert kb.index.keys(EntryKind.RESOLUTION) == {"resolution.one@v2"}
    assert [key for key, _ in kb.store.keyword_search("updated")] == ["resolution.one@v2"]
    assert kb.store.keyword_search("checking") == []  # words only in the retired version


def test_an_entry_can_replace_a_different_older_entry(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    kb.decide(kb.propose(_resolution("resolution.old")).entry_id, 1, reviewer="d", approve=True)
    newer = kb.propose(_resolution("resolution.new", replaces="resolution.old"))
    kb.decide(newer.entry_id, 1, reviewer="d", approve=True)
    assert kb.store.current("resolution.old") is None
    assert kb.index.keys(EntryKind.RESOLUTION) == {"resolution.new@v1"}


def test_retiring_takes_an_entry_out_of_search(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    kb.decide(kb.propose(_resolution()).entry_id, 1, reviewer="d", approve=True)
    kb.retire("resolution.one", by="director-dan", notes="policy changed")
    assert kb.index.keys(EntryKind.RESOLUTION) == set()
    assert kb.store.keyword_search("registry") == []
    assert kb.store.reviews("resolution.one")[-1]["decision"] == "retire"


# --- keeping SQLite and ChromaDB in step ------------------------------------------------


def test_when_the_embedding_model_is_down_the_entry_waits_and_is_indexed_later(
    tmp_path: Path,
) -> None:
    kb = _kb(tmp_path)
    kb.embedder.down = True  # type: ignore[attr-defined]
    kb.decide(kb.propose(_resolution()).entry_id, 1, reviewer="d", approve=True)
    assert kb.index.keys(EntryKind.RESOLUTION) == set()
    assert kb.store.index_tasks()[0]["attempts"] == 1
    kb.embedder.down = False  # type: ignore[attr-defined]
    assert kb.sync().indexed == 1
    assert kb.index.keys(EntryKind.RESOLUTION) == {"resolution.one@v1"}
    assert kb.store.index_tasks() == []


def test_reconcile_removes_stray_vectors_and_restores_missing_ones(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    kb.decide(kb.propose(_resolution()).entry_id, 1, reviewer="d", approve=True)
    stray = _resolution("resolution.stray").with_changes(version=1)
    kb.index.upsert(stray, HashEmbedder().embed_documents(["stray"])[0])
    kb.index.remove(EntryKind.RESOLUTION, "resolution.one@v1")
    kb.reconcile()
    assert kb.index.keys(EntryKind.RESOLUTION) == {"resolution.one@v1"}


def test_everything_survives_a_restart(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    kb.decide(kb.propose(_resolution()).entry_id, 1, reviewer="d", approve=True)
    reopened = _kb(tmp_path)
    assert reopened.store.current("resolution.one").approver == "d"
    assert reopened.index.keys(EntryKind.RESOLUTION) == {"resolution.one@v1"}
    hits = reopened.index.search(
        EntryKind.RESOLUTION, HashEmbedder().embed_query("kept the registry value"), limit=3
    )
    assert hits[0][0] == "resolution.one@v1" and hits[0][2]["blocker_codes"] == (
        "|DOCUMENT_SOURCE_CONFLICT|"
    )


# --- official guidance from markdown ----------------------------------------------------


def test_every_guidance_file_loads_with_a_recorded_source(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    report = ingest_guidance(kb)
    files = sorted(GUIDANCE_DIR.glob("*.md"))
    assert len(report.added) == len(files) >= 8
    for entry in kb.store.entries(kind=EntryKind.GUIDANCE):
        assert entry.status == EntryStatus.APPROVED
        assert entry.source_ref and entry.approver == DECISION_APPROVER
        assert not entry.illustrative
    assert kb.index.count(EntryKind.GUIDANCE) == len(files)


def test_address_guidance_says_only_keep_registry_value_is_offered(tmp_path: Path) -> None:
    entry = parse_guidance(GUIDANCE_DIR / "address-mismatch.md")
    assert entry.blocker_codes == ("DOCUMENT_SOURCE_CONFLICT", "SOURCE_CONFLICT_REQUIRES_POLICY")
    assert "D-030" in (entry.source_ref or "")
    assert '"Use document value" is not offered for addresses' in entry.body


def test_reingesting_skips_unchanged_versions_changes_and_retires_removed(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "guidance"
    shutil.copytree(GUIDANCE_DIR, folder)
    kb = _kb(tmp_path / "data")
    ingest_guidance(kb, folder)
    again = ingest_guidance(kb, folder)
    assert again.added == again.updated == again.retired == [] and again.unchanged

    address = folder / "address-mismatch.md"
    address.write_text(address.read_text() + "\nAn extra sentence.\n")
    (folder / "environments.md").unlink()
    changed = ingest_guidance(kb, folder)
    assert changed.updated == ["guidance.address-mismatch"]
    assert changed.retired == ["guidance.environments"]
    assert kb.store.current("guidance.address-mismatch").version == 2
    assert kb.store.current("guidance.environments") is None
    assert "guidance.environments@v1" not in kb.index.keys(EntryKind.GUIDANCE)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("no header here", "missing the --- header ---"),
        ("---\nid: x\ntitle: t\n---\nbody", "needs 'source'"),
        ("---\nid: x\ntitle: t\nsource: s\nweird: 1\n---\nbody", "unknown header keys"),
        ("---\nid: x\ntitle: t\nsource: s\n---\n", "no guidance text"),
    ],
)
def test_a_badly_written_guidance_file_is_refused(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "bad.md"
    path.write_text(text)
    with pytest.raises(GuidanceFileError, match=message):
        parse_guidance(path)


def test_synthetic_resolutions_are_labelled_illustrative(tmp_path: Path) -> None:
    kb = _kb(tmp_path)
    report = ingest_synthetic_resolutions(kb)
    assert len(report.added) == 3
    for entry in kb.store.entries(kind=EntryKind.RESOLUTION):
        assert entry.illustrative and entry.title.startswith("Illustrative")
        assert entry.status == EntryStatus.APPROVED and entry.follow_ups


# --- permissions --------------------------------------------------------------------------


def test_visibility_limits_by_role_and_team() -> None:
    anyone = Visibility()
    directors_in_alpha = Visibility(roles=("DIRECTOR",), teams=("TEAM_A",))
    assert anyone.allows("CLIENT_ONBOARDER", "TEAM_B")
    assert directors_in_alpha.allows("DIRECTOR", "TEAM_A")
    assert not directors_in_alpha.allows("DIRECTOR", "TEAM_B")
    assert not directors_in_alpha.allows("RELATIONSHIP_MANAGER", "TEAM_A")


# --- the local embedding client -----------------------------------------------------------


def test_ollama_embedder_sends_documents_and_queries_with_their_prefixes() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"url": str(request.url), **body})
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2] for _ in body["input"]]})

    embedder = OllamaEmbedder(
        base_url="http://127.0.0.1:11434/",
        model="nomic-embed-text",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    assert embedder.embed_documents(["a", "b"]) == [[0.1, 0.2], [0.1, 0.2]]
    assert embedder.embed_query("why?") == [0.1, 0.2]
    assert seen[0]["url"] == "http://127.0.0.1:11434/api/embed"
    assert seen[0]["input"] == ["search_document: a", "search_document: b"]
    assert seen[1]["input"] == ["search_query: why?"]


@pytest.mark.parametrize(
    "reply",
    [
        httpx.Response(500),
        httpx.Response(200, json={"embeddings": []}),
        httpx.Response(200, text="not json"),
    ],
)
def test_ollama_embedder_reports_bad_replies_as_unavailable(reply: httpx.Response) -> None:
    embedder = OllamaEmbedder(
        base_url="http://model.invalid",
        model="m",
        timeout_seconds=5,
        transport=httpx.MockTransport(lambda request: reply),
    )
    with pytest.raises(EmbeddingUnavailableError):
        embedder.embed_query("hi")
