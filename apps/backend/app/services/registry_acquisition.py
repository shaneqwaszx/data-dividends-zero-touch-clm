"""Single owner for Mock registry cache decisions and process-local single-flight."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock, RLock
from time import monotonic

from pydantic import ValidationError

from app.connectors.errors import ConnectorError
from app.connectors.registry import RegistryProvider
from app.domain.models import (
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryCacheKey,
    RegistryEvidenceBinding,
    RegistryEvidenceDisposition,
    RegistryFreshnessPolicy,
    RegistryOperation,
    RegistryOperationStatus,
    RegistrySnapshotEntry,
    SourceEnvironment,
)
from app.domain.policy import RegistryPolicySnapshot
from app.services.registry_cache_repository import (
    RegistrySnapshotRepository,
    RegistrySnapshotRepositoryConflictError,
    RegistrySnapshotRepositoryInvalidError,
    RegistrySnapshotRepositoryUnavailableError,
)


def registry_cache_window_is_fresh(expires_at: datetime, evaluation_now: datetime) -> bool:
    """Shared exclusive expiry predicate; caller retains normalized-input ownership."""
    return evaluation_now < expires_at


def registry_negative_cache_is_fresh(
    anchor: datetime, evaluation_now: datetime, ttl_seconds: int
) -> bool:
    """Definitive NOT_FOUND window; never applies to uncertain provider failures."""
    return registry_cache_window_is_fresh(anchor + timedelta(seconds=ttl_seconds), evaluation_now)


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


class RegistryAcquisitionBusyError(RegistryCacheError):
    code = "REGISTRY_ACQUISITION_BUSY"
    public_message = "Registry acquisition is busy; retry with a new request."


@dataclass(frozen=True)
class RegistryAcquisitionResult:
    acquisition: RegistryAcquisitionBundle | None
    binding: RegistryEvidenceBinding | None


@dataclass
class _KeyLockState:
    lock: RLock
    users: int = 0
    shared_result: RegistryAcquisitionResult | None = None
    failure: type[ConnectorError] | type[RegistryCacheError] | None = None


class RegistryAcquisitionCoordinator:
    """Coordinate exact-key reads, refreshes, writes, and case-bound evidence copies."""

    def __init__(
        self,
        repository: RegistrySnapshotRepository,
        policy: RegistryFreshnessPolicy,
        *,
        clock: Callable[[], datetime] | None = None,
        max_active_keys: int = 256,
        max_users_per_key: int = 64,
        wait_timeout_seconds: float = 45.0,
    ) -> None:
        if (
            not 1 <= max_active_keys <= 1024
            or not 1 <= max_users_per_key <= 128
            or not 0 < wait_timeout_seconds <= 120
        ):
            raise ValueError("registry acquisition bounds are invalid")
        self._max_active_keys = max_active_keys
        self._max_users_per_key = max_users_per_key
        self._wait_timeout_seconds = wait_timeout_seconds
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
        *,
        case_policy: RegistryPolicySnapshot | None = None,
        policy_version: int = 0,
        cancelled: Callable[[], bool] | None = None,
    ) -> RegistryAcquisitionResult:
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        identity = getattr(provider, "cache_identity", None)
        if identity is None:
            return RegistryAcquisitionResult(
                acquisition=provider.retrieve_acquisition(identifier), binding=None
            )
        if identity.environment != SourceEnvironment.MOCK:
            raise RegistryCacheInvalidError
        policy = (
            self._policy
            if case_policy is None
            else RegistryFreshnessPolicy(
                policy_id="MOCK_ACRA_APPROVED_POLICY",
                version=policy_version,
                duration_seconds=case_policy.freshness_seconds,
            )
        )
        negative_seconds = case_policy.negative_seconds if case_policy is not None else 600
        key = RegistryCacheKey(
            provider_identity=identity, normalized_identifier=identifier.strip().upper()
        )
        with self._key_lock(key.digest, cancelled=cancelled) as flight:
            if flight.failure is not None:
                raise flight.failure() from None
            if flight.shared_result is not None:
                result = flight.shared_result
                now = self._utc_now()
                acquisition = result.acquisition
                if acquisition is not None:
                    self._validate_bundle_times(acquisition, now)
                    successful = tuple(
                        operation.provenance
                        for operation in acquisition.operation_results
                        if operation.status
                        in {RegistryOperationStatus.COMPLETE, RegistryOperationStatus.EMPTY}
                        and operation.provenance is not None
                    )
                    if successful and all(
                        registry_cache_window_is_fresh(policy.expires_at(p.retrieved_at), now)
                        for p in successful
                    ):
                        return RegistryAcquisitionResult(
                            acquisition=acquisition.model_copy(deep=True), binding=None
                        )
                flight.shared_result = None
            try:
                result = self._acquire_locked(provider, key, policy, negative_seconds, cancelled)
            except (ConnectorError, RegistryCacheError) as error:
                flight.failure = type(error)
                raise
            except BaseException:
                flight.failure = RegistryAcquisitionBusyError
                raise
            # Share incomplete/error outcomes within this active cohort only. They
            # are not negative cache hits and never outlive registered callers.
            if result.binding is None and result.acquisition is not None:
                flight.shared_result = result
            return result

    def _acquire_locked(
        self,
        provider: RegistryProvider,
        key: RegistryCacheKey,
        policy: RegistryFreshnessPolicy,
        negative_seconds: int,
        cancelled: Callable[[], bool] | None,
    ) -> RegistryAcquisitionResult:
        now = self._utc_now()
        entry = self._read(key)
        reusable: set[RegistryOperation] = set()
        reuse: RegistryAcquisitionBundle | None = None
        if entry is not None:
            self._validate_entry_for_use(entry, key, now)
            if entry.negative_result == "NOT_FOUND":
                if registry_negative_cache_is_fresh(entry.freshness_anchor, now, negative_seconds):
                    return RegistryAcquisitionResult(acquisition=None, binding=None)
            elif entry.acquisition is not None:
                reuse = entry.acquisition
                if (
                    reuse.status == RegistryAcquisitionStatus.COMPLETE
                    and registry_cache_window_is_fresh(
                        policy.expires_at(entry.freshness_anchor), now
                    )
                ):
                    return self._bound_result(
                        entry,
                        disposition=RegistryEvidenceDisposition.CACHE_HIT,
                        bound_at=now,
                        policy=policy,
                    )
                reusable = {
                    operation.operation
                    for operation in reuse.operation_results
                    if operation.status == RegistryOperationStatus.COMPLETE
                    and operation.provenance is not None
                    and registry_cache_window_is_fresh(
                        policy.expires_at(operation.provenance.retrieved_at), now
                    )
                }
                # EMPTY officers are a successful optional operation. Empty required
                # ownership/relationships remain missing and must be reacquired.
                officer = next(
                    r for r in reuse.operation_results if r.operation == RegistryOperation.OFFICERS
                )
                if (
                    officer.status == RegistryOperationStatus.EMPTY
                    and officer.provenance is not None
                    and registry_cache_window_is_fresh(
                        policy.expires_at(officer.provenance.retrieved_at), now
                    )
                ):
                    reusable.add(RegistryOperation.OFFICERS)
                if RegistryOperation.ENTITY_PROFILE not in reusable:
                    reusable.clear()
                if RegistryOperation.OWNERSHIP_PARTIES not in reusable:
                    reusable.discard(RegistryOperation.RELATIONSHIPS)
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        acquisition = (
            provider.retrieve_acquisition(
                key.normalized_identifier, reuse=reuse, reuse_operations=frozenset(reusable)
            )
            if reusable
            else provider.retrieve_acquisition(key.normalized_identifier)
        )
        bound_at = self._utc_now()
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        if acquisition is None:
            candidate = RegistrySnapshotEntry(
                cache_schema_version=2,
                cache_id=key.digest,
                key=key,
                revision=entry.revision if entry is not None else 0,
                acquisition=None,
                negative_result="NOT_FOUND",
                freshness_anchor=bound_at,
                written_at=bound_at,
            )
            self._write(candidate, current=entry)
            return RegistryAcquisitionResult(acquisition=None, binding=None)
        self._validate_bundle_times(acquisition, bound_at)
        provenances = tuple(
            r.provenance
            for r in acquisition.operation_results
            if r.status in {RegistryOperationStatus.COMPLETE, RegistryOperationStatus.EMPTY}
            and r.provenance is not None
        )
        if not provenances:
            raise RegistryCacheInvalidError
        candidate = RegistrySnapshotEntry(
            cache_schema_version=2,
            cache_id=key.digest,
            key=key,
            revision=entry.revision if entry is not None else 0,
            acquisition=acquisition,
            freshness_anchor=min(p.retrieved_at for p in provenances),
            written_at=bound_at,
        )
        if (
            acquisition.status == RegistryAcquisitionStatus.COMPLETE
            and bound_at >= policy.expires_at(candidate.freshness_anchor)
        ):
            raise RegistryCacheInvalidError
        persisted = self._write(candidate, current=entry)
        if acquisition.status != RegistryAcquisitionStatus.COMPLETE:
            return RegistryAcquisitionResult(
                acquisition=acquisition.model_copy(deep=True), binding=None
            )
        return self._bound_result(
            persisted,
            disposition=RegistryEvidenceDisposition.PROVIDER_FETCH,
            bound_at=bound_at,
            policy=policy,
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
        expected = candidate.model_copy(update={"revision": expected_revision})
        if persisted != expected:
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
        if entry.acquisition is not None:
            self._validate_bundle_times(entry.acquisition, evaluation_now)
        if entry.freshness_anchor > evaluation_now or entry.written_at > evaluation_now:
            raise RegistryCacheInvalidError
        if entry.provider_effective_at is not None and entry.provider_effective_at > evaluation_now:
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
        policy: RegistryFreshnessPolicy | None = None,
    ) -> RegistryAcquisitionResult:
        if (
            entry.acquisition is None
            or entry.acquisition.status != RegistryAcquisitionStatus.COMPLETE
        ):
            raise RegistryCacheInvalidError
        policy = policy or self._policy
        binding = RegistryEvidenceBinding(
            disposition=disposition,
            cache_id=entry.cache_id,
            cache_key=entry.key,
            cache_revision=entry.revision,
            freshness_anchor=entry.freshness_anchor,
            bundle_retrieved_at=entry.acquisition.retrieved_at,
            cache_written_at=entry.written_at,
            bound_to_case_at=bound_at,
            expires_at=policy.expires_at(entry.freshness_anchor),
            freshness_policy=policy,
            freshness_policy_fingerprint=policy.fingerprint,
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
    def _key_lock(
        self, digest: str, *, cancelled: Callable[[], bool] | None = None
    ) -> Iterator[_KeyLockState]:
        with self._locks_guard:
            state = self._locks.get(digest)
            if state is None:
                if len(self._locks) >= self._max_active_keys:
                    raise RegistryAcquisitionBusyError
                state = _KeyLockState(lock=RLock())
                self._locks[digest] = state
            if state.users >= self._max_users_per_key:
                raise RegistryAcquisitionBusyError
            state.users += 1
        acquired = False
        deadline = monotonic() + self._wait_timeout_seconds
        try:
            while not acquired:
                if cancelled is not None and cancelled():
                    raise RegistryAcquisitionBusyError
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise RegistryAcquisitionBusyError
                acquired = state.lock.acquire(timeout=min(0.05, remaining))
            yield state
        finally:
            if acquired:
                state.lock.release()
            with self._locks_guard:
                state.users -= 1
                if state.users == 0 and self._locks.get(digest) is state:
                    del self._locks[digest]
