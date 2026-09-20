"""Repository boundary for complete shared registry snapshots."""

from __future__ import annotations

from threading import RLock
from typing import Protocol

from app.domain.models import RegistryCacheKey, RegistrySnapshotEntry


class RegistrySnapshotRepositoryError(RuntimeError):
    """Base safe repository failure."""


class RegistrySnapshotRepositoryUnavailableError(RegistrySnapshotRepositoryError):
    """The configured snapshot store could not complete an operation."""


class RegistrySnapshotRepositoryConflictError(RegistrySnapshotRepositoryError):
    """Insert or expected-revision replacement lost ownership."""


class RegistrySnapshotRepositoryInvalidError(RegistrySnapshotRepositoryError):
    """Persisted snapshot data failed strict validation."""


class RegistrySnapshotRepository(Protocol):
    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None: ...

    def create(self, entry: RegistrySnapshotEntry) -> RegistrySnapshotEntry: ...

    def replace(
        self,
        entry: RegistrySnapshotEntry,
        *,
        expected_revision: int,
    ) -> RegistrySnapshotEntry: ...


class InMemoryRegistrySnapshotRepository:
    """Defensive process-local implementation with insert/update separation."""

    def __init__(self) -> None:
        self._entries: dict[str, RegistrySnapshotEntry] = {}
        self._lock = RLock()

    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        with self._lock:
            entry = self._entries.get(key.digest)
            return entry.model_copy(deep=True) if entry is not None else None

    def create(self, entry: RegistrySnapshotEntry) -> RegistrySnapshotEntry:
        candidate = RegistrySnapshotEntry.model_validate(entry)
        if candidate.revision != 0:
            raise RegistrySnapshotRepositoryInvalidError
        with self._lock:
            if candidate.cache_id in self._entries:
                raise RegistrySnapshotRepositoryConflictError
            self._entries[candidate.cache_id] = candidate.model_copy(deep=True)
            return candidate.model_copy(deep=True)

    def replace(
        self,
        entry: RegistrySnapshotEntry,
        *,
        expected_revision: int,
    ) -> RegistrySnapshotEntry:
        candidate = RegistrySnapshotEntry.model_validate(entry)
        if candidate.cache_id != entry.key.digest or candidate.revision != expected_revision:
            raise RegistrySnapshotRepositoryInvalidError
        with self._lock:
            current = self._entries.get(candidate.cache_id)
            if current is None or current.revision != expected_revision:
                raise RegistrySnapshotRepositoryConflictError
            persisted = candidate.model_copy(
                update={"revision": expected_revision + 1},
                deep=True,
            )
            self._entries[candidate.cache_id] = persisted
            return persisted.model_copy(deep=True)
