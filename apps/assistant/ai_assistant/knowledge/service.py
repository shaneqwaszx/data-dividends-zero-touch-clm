"""Keeps SQLite (the source of truth) and ChromaDB (the search index) in step.

Every approve, replace or retire in the store leaves an index task. ``sync`` carries the
tasks out; a task that fails (for example the embedding model is not running) stays queued
and is retried on the next sync, so an approved entry is never silently missing from search
and a retired one never lingers. ``reconcile`` compares the two stores and queues whatever
differs, so the index can always be rebuilt from SQLite.
"""

from dataclasses import dataclass

from .embeddings import Embedder, EmbeddingUnavailableError
from .models import Entry, EntryKind, EntryStatus
from .store import KnowledgeStore
from .vector_index import VectorIndex, document_text


@dataclass(frozen=True)
class SyncReport:
    indexed: int = 0
    removed: int = 0
    failed: int = 0


class KnowledgeBase:
    def __init__(self, store: KnowledgeStore, index: VectorIndex, embedder: Embedder) -> None:
        self.store = store
        self.index = index
        self.embedder = embedder

    # --- changes --------------------------------------------------------------------

    def propose(self, entry: Entry) -> Entry:
        return self.store.add_version(entry, status=EntryStatus.PENDING_REVIEW)

    def decide(
        self,
        entry_id: str,
        version: int,
        *,
        reviewer: str,
        approve: bool,
        notes: str = "",
        expected_hash: str | None = None,
    ) -> Entry:
        decided = self.store.decide(
            entry_id,
            version,
            reviewer=reviewer,
            approve=approve,
            notes=notes,
            expected_hash=expected_hash,
        )
        self.sync()
        return decided

    def retire(self, entry_id: str, *, by: str, notes: str) -> Entry | None:
        retired = self.store.retire(entry_id, by=by, notes=notes)
        self.sync()
        return retired

    # --- keeping the index in step --------------------------------------------------

    def sync(self) -> SyncReport:
        indexed = removed = failed = 0
        for task in self.store.index_tasks():
            kind = EntryKind(task["kind"])
            key = task["key"]
            if task["action"] == "remove":
                self.index.remove(kind, key)
                self.store.finish_task(key)
                removed += 1
                continue
            entry = self.store.get(task["entry_id"], task["version"])
            if entry is None or entry.status != EntryStatus.APPROVED:
                # Retired or replaced since the task was queued: make sure it is not searchable.
                self.index.remove(kind, key)
                self.store.finish_task(key)
                removed += 1
                continue
            try:
                vector = self.embedder.embed_documents([document_text(entry)])[0]
            except EmbeddingUnavailableError as exc:
                self.store.fail_task(key, str(exc))
                failed += 1
                continue
            self.index.upsert(entry, vector)
            self.store.finish_task(key)
            indexed += 1
        return SyncReport(indexed=indexed, removed=removed, failed=failed)

    def reconcile(self) -> SyncReport:
        """Make the index hold exactly the current approved versions, then sync."""

        for kind in EntryKind:
            current = {
                entry.key for entry in self.store.entries(status=EntryStatus.APPROVED, kind=kind)
            }
            for stale in self.index.keys(kind) - current:
                self.index.remove(kind, stale)
            missing = current - self.index.keys(kind)
            if missing:
                self.store.queue_full_reindex()
        return self.sync()

    def rebuild(self) -> SyncReport:
        """Re-embed every current approved version (e.g. after changing the embedding model)."""

        for kind in EntryKind:
            for key in self.index.keys(kind):
                self.index.remove(kind, key)
        self.store.queue_full_reindex()
        return self.sync()

    def status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.store.entries():
            name = f"{entry.kind.value}_{entry.status.value}"
            counts[name] = counts.get(name, 0) + 1
        for kind in EntryKind:
            counts[f"{kind.value}_indexed"] = self.index.count(kind)
        counts["index_tasks_waiting"] = len(self.store.index_tasks())
        return counts
