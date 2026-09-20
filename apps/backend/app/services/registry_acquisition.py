"""Single owner for Mock registry cache decisions and process-local single-flight."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock, RLock

from pydantic import ValidationError

from app.connectors.registry import RegistryProvider
from app.domain.models import (
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryCacheKey,
    RegistryEvidenceBinding,
    RegistryEvidenceDisposition,
    RegistryFreshnessPolicy,
    RegistrySnapshotEntry,
    SourceEnvironment,
)
from app.services.registry_cache_repository import (
    RegistrySnapshotRepository,
    RegistrySnapshotRepositoryConflictError,
    RegistrySnapshotRepositoryInvalidError,
    RegistrySnapshotRepositoryUnavailableError,
)


class RegistryCacheError(RuntimeError):
    code = "REGISTRY_CACHE_FAILURE"
    public_message = "Registry evidence could not be prepared safely."


class RegistryCacheReadError(RegistryCacheError):
    code = "REGISTRY_CACHE_READ_FAILED"
    public_message = "Registry evidence could not be read safely."


class RegistryCacheWriteError(RegistryCacheError):
    code = "REGISTRY_CACHE_WRITE_FAILED"
    public_message = "Registry evidence could not be stored safely."


class RegistryCacheConflictError(RegistryCacheError):
    code = "REGISTRY_CACHE_CONFLICT"
    public_message = "Registry evidence changed concurrently; retry with a new request."


class RegistryCacheInvalidError(RegistryCacheError):
    code = "REGISTRY_CACHE_INVALID"
    public_message = "Registry evidence could not be validated safely."


@dataclass(frozen=True)
class RegistryAcquisitionResult:
    acquisition: RegistryAcquisitionBundle | None
    binding: RegistryEvidenceBinding | None


@dataclass
class _KeyLockState:
    lock: RLock
    users: int = 0


class RegistryAcquisitionCoordinator:
    """Coordinate exact-key reads, refreshes, writes, and case-bound evidence copies."""

    def __init__(
        self,
        repository: RegistrySnapshotRepository,
        policy: RegistryFreshnessPolicy,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy
        self._clock = clock or (lambda: datetime.now(UTC))
        self._locks: dict[str, _KeyLockState] = {}
        self._locks_guard = Lock()

    @property
    def active_lock_count(self) -> int:
        with self._locks_guard:
            return len(self._locks)

    def acquire(
        self,
        provider: RegistryProvider,
        identifier: str,
    ) -> RegistryAcquisitionResult:
        identity = getattr(provider, "cache_identity", None)
        if identity is None:
            return RegistryAcquisitionResult(
                acquisition=provider.retrieve_acquisition(identifier),
                binding=None,
            )
        if identity.environment != SourceEnvironment.MOCK:
            raise RegistryCacheInvalidError
        key = RegistryCacheKey(
            provider_identity=identity,
            normalized_identifier=identifier,
        )
        with self._key_lock(key.digest):
            evaluation_now = self._utc_now()
            entry = self._read(key)
            if entry is not None:
                self._validate_entry_for_use(entry, key, evaluation_now)
                if evaluation_now < self._policy.expires_at(entry.freshness_anchor):
                    return self._bound_result(
                        entry,
                        disposition=RegistryEvidenceDisposition.CACHE_HIT,
                        bound_at=evaluation_now,
                    )

            acquisition = provider.retrieve_acquisition(identifier)
            if acquisition is None:
                return RegistryAcquisitionResult(acquisition=None, binding=None)
            bound_at = self._utc_now()
            self._validate_bundle_times(acquisition, bound_at)
            if acquisition.status != RegistryAcquisitionStatus.COMPLETE:
                return RegistryAcquisitionResult(
                    acquisition=acquisition.model_copy(deep=True),
                    binding=None,
                )

            complete_provenances = tuple(
                result.provenance for result in acquisition.operation_results
            )
            if any(provenance is None for provenance in complete_provenances):
                raise RegistryCacheInvalidError from None
            freshness_anchor = min(
                provenance.retrieved_at
                for provenance in complete_provenances
                if provenance is not None
            )
            candidate = RegistrySnapshotEntry(
                cache_id=key.digest,
                key=key,
                revision=entry.revision if entry is not None else 0,
                acquisition=acquisition,
                freshness_anchor=freshness_anchor,
                written_at=bound_at,
            )
            persisted = self._write(candidate, current=entry)
            return self._bound_result(
                persisted,
                disposition=RegistryEvidenceDisposition.PROVIDER_FETCH,
                bound_at=bound_at,
            )

    def _read(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        try:
            raw = self._repository.get(key)
        except RegistrySnapshotRepositoryInvalidError:
            raise RegistryCacheInvalidError from None
        except RegistrySnapshotRepositoryUnavailableError:
            raise RegistryCacheReadError from None
        except Exception:
            raise RegistryCacheReadError from None
        if raw is None:
            return None
        try:
            entry = RegistrySnapshotEntry.model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            raise RegistryCacheInvalidError from None
        if entry.key != key or entry.cache_id != key.digest:
            raise RegistryCacheInvalidError from None
        return entry

    def _write(
        self,
        candidate: RegistrySnapshotEntry,
        *,
        current: RegistrySnapshotEntry | None,
    ) -> RegistrySnapshotEntry:
        try:
            if current is None:
                raw_persisted = self._repository.create(candidate)
                expected_revision = 0
            else:
                raw_persisted = self._repository.replace(
                    candidate,
                    expected_revision=current.revision,
                )
                expected_revision = current.revision + 1
        except RegistrySnapshotRepositoryConflictError:
            raise RegistryCacheConflictError from None
        except RegistrySnapshotRepositoryInvalidError:
            raise RegistryCacheInvalidError from None
        except RegistrySnapshotRepositoryUnavailableError:
            raise RegistryCacheWriteError from None
        except Exception:
            raise RegistryCacheWriteError from None
        try:
            persisted = RegistrySnapshotEntry.model_validate(raw_persisted)
        except (ValidationError, ValueError, TypeError):
            raise RegistryCacheInvalidError from None
        if (
            persisted.key != candidate.key
            or persisted.cache_id != candidate.cache_id
            or persisted.acquisition != candidate.acquisition
            or persisted.revision != expected_revision
        ):
            raise RegistryCacheInvalidError
        return persisted

    def _validate_entry_for_use(
        self,
        entry: RegistrySnapshotEntry,
        key: RegistryCacheKey,
        evaluation_now: datetime,
    ) -> None:
        if entry.key != key or entry.cache_id != key.digest:
            raise RegistryCacheInvalidError
        self._validate_bundle_times(entry.acquisition, evaluation_now)
        if entry.freshness_anchor > evaluation_now or entry.written_at > evaluation_now:
            raise RegistryCacheInvalidError
        if (
            entry.provider_effective_at is not None
            and entry.provider_effective_at > evaluation_now
        ):
            raise RegistryCacheInvalidError

    @staticmethod
    def _validate_bundle_times(
        acquisition: RegistryAcquisitionBundle,
        evaluation_now: datetime,
    ) -> None:
        if acquisition.retrieved_at > evaluation_now:
            raise RegistryCacheInvalidError
        for result in acquisition.operation_results:
            provenance = result.provenance
            if provenance is not None and provenance.retrieved_at > evaluation_now:
                raise RegistryCacheInvalidError

    def _bound_result(
        self,
        entry: RegistrySnapshotEntry,
        *,
        disposition: RegistryEvidenceDisposition,
        bound_at: datetime,
    ) -> RegistryAcquisitionResult:
        binding = RegistryEvidenceBinding(
            disposition=disposition,
            cache_id=entry.cache_id,
            cache_key=entry.key,
            cache_revision=entry.revision,
            freshness_anchor=entry.freshness_anchor,
            bundle_retrieved_at=entry.acquisition.retrieved_at,
            cache_written_at=entry.written_at,
            bound_to_case_at=bound_at,
            expires_at=self._policy.expires_at(entry.freshness_anchor),
            freshness_policy=self._policy,
            freshness_policy_fingerprint=self._policy.fingerprint,
        )
        return RegistryAcquisitionResult(
            acquisition=entry.acquisition.model_copy(deep=True),
            binding=binding.model_copy(deep=True),
        )

    def _utc_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() != UTC.utcoffset(now):
            raise RegistryCacheInvalidError
        return now.astimezone(UTC)

    @contextmanager
    def _key_lock(self, digest: str) -> Iterator[None]:
        with self._locks_guard:
            state = self._locks.get(digest)
            if state is None:
                state = _KeyLockState(lock=RLock())
                self._locks[digest] = state
            state.users += 1
        state.lock.acquire()
        try:
            yield
        finally:
            state.lock.release()
            with self._locks_guard:
                state.users -= 1
                if state.users == 0 and self._locks.get(digest) is state:
                    del self._locks[digest]
