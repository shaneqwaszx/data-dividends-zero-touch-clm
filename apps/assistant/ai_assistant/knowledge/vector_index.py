"""ChromaDB index of the current approved entries, one collection per kind.

The index holds only what may be searched: approved, current versions. SQLite stays the
source of truth; the index can always be rebuilt from it. Vectors are supplied by our own
embedder (no model is downloaded by ChromaDB). Filters (kind, codes, roles, teams) are
stored as metadata so they can be applied inside the search.
"""

from pathlib import Path
from typing import Any

import chromadb

from .models import Entry, EntryKind

COLLECTIONS = {
    EntryKind.GUIDANCE: "official_guidance",
    EntryKind.RESOLUTION: "past_resolutions",
}


def _tags(values: tuple[str, ...]) -> str:
    """'|A|B|' so a filter can test membership with a substring match."""

    return "|" + "|".join(values) + "|" if values else ""


def document_text(entry: Entry) -> str:
    """What gets embedded: the title, the body, and the case context it applies to."""

    context = ", ".join([*entry.blocker_codes, *entry.fields, *entry.stages])
    return f"{entry.title}\n{entry.body}" + (f"\nApplies to: {context}" if context else "")


def metadata(entry: Entry) -> dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "version": entry.version,
        "kind": entry.kind.value,
        "blocker_codes": _tags(entry.blocker_codes),
        "fields": _tags(entry.fields),
        "stages": _tags(entry.stages),
        "roles": _tags(entry.visibility.roles),
        "teams": _tags(entry.visibility.teams),
        "approved_at": entry.approved_at or "",
        "illustrative": entry.illustrative,
    }


class VectorIndex:
    def __init__(self, path: Path | str | None) -> None:
        if path is None:
            self._client = chromadb.EphemeralClient()
        else:
            Path(path).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(path))
        self._collections = {
            kind: self._client.get_or_create_collection(
                name, embedding_function=None, metadata={"hnsw:space": "cosine"}
            )
            for kind, name in COLLECTIONS.items()
        }

    def upsert(self, entry: Entry, vector: list[float]) -> None:
        self._collections[entry.kind].upsert(
            ids=[entry.key],
            embeddings=[vector],  # type: ignore[arg-type]
            documents=[document_text(entry)],
            metadatas=[metadata(entry)],
        )

    def remove(self, kind: EntryKind, key: str) -> None:
        self._collections[kind].delete(ids=[key])

    def keys(self, kind: EntryKind) -> set[str]:
        return set(self._collections[kind].get(include=[])["ids"])

    def count(self, kind: EntryKind) -> int:
        return self._collections[kind].count()

    def search(
        self, kind: EntryKind, vector: list[float], *, limit: int
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Nearest entries: (version key, similarity 0..1, metadata), most similar first."""

        collection = self._collections[kind]
        if collection.count() == 0:
            return []
        result = collection.query(
            query_embeddings=[vector],  # type: ignore[arg-type]
            n_results=min(limit, collection.count()),
            include=["distances", "metadatas"],
        )
        ids = result["ids"][0]
        distances = (result.get("distances") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        return [
            (key, 1.0 - float(distance), dict(meta or {}))
            for key, distance, meta in zip(ids, distances, metadatas, strict=True)
        ]
