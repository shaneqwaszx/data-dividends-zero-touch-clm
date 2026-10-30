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
from app.connectors.registry import (
    BusinessProfileEvidenceProvider,
    RegistryProvider,
    ShareholderEvidenceProvider,
)
from app.domain.models import (
    BUSINESS_PROFILE_EVIDENCE_CONTRACT_VERSION,
    SHAREHOLDER_EVIDENCE_CONTRACT_VERSION,
    RegistryAcquisitionBundle,
    RegistryAcquisitionStatus,
    RegistryBusinessProfileEvidence,
    RegistryCacheKey,
    RegistryEvidenceBinding,
    RegistryEvidenceDisposition,
    RegistryFreshnessPolicy,
    RegistryOperation,
    RegistryOperationStatus,
    RegistryProviderIdentity,
    RegistryShareholderEvidence,
    RegistrySnapshotEntry,
    SourceEnvironment,
)
from app.domain.policy import RegistryPolicySnapshot
from app.domain.registry_dataset import LOCAL_SYNTHETIC_REGISTRY_DATASET
from app.domain.registry_legal_form import RegistryLegalForm, classify_registry_legal_form
from app.services.registry_cache_repository import (
    RegistrySnapshotRepository,
    RegistrySnapshotRepositoryConflictError,
    RegistrySnapshotRepositoryInvalidError,
    RegistrySnapshotRepositoryUnavailableError,
)


def registry_cache_window_is_fresh(expires_at: datetime, evaluation_now: datetime) -> bool:
    """Shared exclusive expiry predicate; caller retains normalized-input ownership."""
    return evaluation_now < expires_at


def _usable_partial_local_seed(acquisition: RegistryAcquisitionBundle) -> bool:
    """A PARTIAL local seed with a complete identity for a form without a share graph."""
    entity = acquisition.entity_profile
    address = entity.registered_address
    return (
        acquisition.status == RegistryAcquisitionStatus.PARTIAL
        and acquisition.operation_results[0].status == RegistryOperationStatus.COMPLETE
        and bool((entity.legal_name or "").strip())
        and bool(entity.registration_number.strip())
        and address is not None
        and bool(address.address_line_1.strip())
        and bool(address.postal_code.strip())
        and classify_registry_legal_form(entity.party_type)
        in {RegistryLegalForm.BUSINESS_PARTNERSHIP, RegistryLegalForm.GOVERNMENT}
    )


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
    # In-memory observations only: a fresh definitive NOT_FOUND served from the cache,
    # or an incomplete result whose entity profile came from a fresh cached prefix.
    negative_cache_hit: bool = False
    entity_profile_reused: bool = False


@dataclass(frozen=True)
class SubsidiaryRegistryEvidence:
    """Read-only issuer evidence for ownership discovery; never bound to a case.

    `provider_backed` is false only for a committed fresh cache hit (including the
    approved local seed and a fresh definitive NOT_FOUND). A miss, stale entry,
    uncached lane or incomplete result used the configured provider and counts toward
    any business call budget, even when its entity profile came from a cached prefix.
    """

    identifier: str
    acquisition: RegistryAcquisitionBundle | None
    disposition: RegistryEvidenceDisposition | None
    provider_backed: bool
    negative_cache_hit: bool = False
    entity_profile_reused: bool = False


@dataclass(frozen=True)
class RegistryShareholderAcquisitionResult:
    """D-079 issuer shareholder evidence; `cache_hit` means no provider call was made."""

    evidence: RegistryShareholderEvidence
    cache_hit: bool


@dataclass(frozen=True)
class SubsidiaryShareholderEvidence:
    """Read-only D-079 shareholder evidence for one corporate holder; never case-bound."""

    identifier: str
    evidence: RegistryShareholderEvidence
    provider_backed: bool


@dataclass(frozen=True)
class RegistryBusinessProfileAcquisitionResult:
    """D-088 business profile evidence; `cache_hit` means no provider call was made."""

    evidence: RegistryBusinessProfileEvidence
    cache_hit: bool


@dataclass(frozen=True)
class SubsidiaryBusinessProfileEvidence:
    """Read-only D-088 business profile evidence for one corporate holder."""

    identifier: str
    evidence: RegistryBusinessProfileEvidence
    provider_backed: bool


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
        local_seed_identity: RegistryProviderIdentity | None = None,
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
        if local_seed_identity is not None:
            from app.domain.registry_dataset import local_synthetic_registry_identity

            if local_seed_identity != local_synthetic_registry_identity():
                raise ValueError("unapproved local registry dataset identity")
        self._local_seed_identity = local_seed_identity
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
        if (
            self._local_seed_identity is not None
            and identity.provider == self._local_seed_identity.provider
            and identity.acquisition_contract_version
            == self._local_seed_identity.acquisition_contract_version
            and identity.dataset_namespace
            in {"MOCK_ACRA_SYNTHETIC_V2", "ACRA_API_MARKETPLACE_MOCK_V1"}
        ):
            seed_key = RegistryCacheKey(
                provider_identity=self._local_seed_identity,
                normalized_identifier=key.normalized_identifier,
            )
            # A separate approved dataset, never a provider alias or partial prefix.
            seed = self._read(seed_key)
            if seed is not None:
                now = self._utc_now()
                self._validate_entry_for_use(seed, seed_key, now)
                if (
                    seed.acquisition is not None
                    and seed.acquisition.status == RegistryAcquisitionStatus.COMPLETE
                    and registry_cache_window_is_fresh(
                        policy.expires_at(seed.freshness_anchor), now
                    )
                ):
                    if cancelled is not None and cancelled():
                        raise RegistryAcquisitionBusyError
                    return self._bound_result(
                        seed, disposition=RegistryEvidenceDisposition.CACHE_HIT,
                        bound_at=now, policy=policy,
                    )
                # D-101: a partnership or Government seed has no registry ownership graph.
                # It is returned like a PARTIAL provider fetch: never bound, never a hit.
                if (
                    seed.acquisition is not None
                    and seed_key.provider_identity.dataset_namespace
                    == LOCAL_SYNTHETIC_REGISTRY_DATASET
                    and _usable_partial_local_seed(seed.acquisition)
                    and registry_cache_window_is_fresh(
                        policy.expires_at(seed.freshness_anchor), now
                    )
                ):
                    if cancelled is not None and cancelled():
                        raise RegistryAcquisitionBusyError
                    return RegistryAcquisitionResult(
                        acquisition=seed.acquisition.model_copy(deep=True), binding=None
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

    def acquire_shareholder_evidence(
        self,
        provider: ShareholderEvidenceProvider,
        identifier: str,
        *,
        case_policy: RegistryPolicySnapshot | None = None,
        policy_version: int = 0,
        cancelled: Callable[[], bool] | None = None,
    ) -> RegistryShareholderAcquisitionResult:
        """Cache-first D-079 shareholder evidence under its own contract key.

        It shares this owner's repository, key locks and CAS writes. Fresh COMPLETE
        evidence follows the freshness policy and fresh EMPTY evidence the definitive
        negative TTL; a failed operation is returned but never cached. D-080 entries
        (schema 4) use the V2 key, so D-079 V1 entries without share class are not reused.
        """
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        identity = provider.cache_identity
        if identity is None:
            return RegistryShareholderAcquisitionResult(
                evidence=provider.retrieve_shareholder_evidence(identifier), cache_hit=False
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
            provider_identity=RegistryProviderIdentity(
                provider=identity.provider,
                environment=identity.environment,
                acquisition_contract_version=SHAREHOLDER_EVIDENCE_CONTRACT_VERSION,
                dataset_namespace=identity.dataset_namespace,
            ),
            normalized_identifier=identifier.strip().upper(),
        )
        with self._key_lock(key.digest, cancelled=cancelled) as flight:
            if flight.failure is not None:
                raise flight.failure() from None
            try:
                return self._acquire_shareholders_locked(
                    provider, key, policy, negative_seconds, cancelled
                )
            except (ConnectorError, RegistryCacheError) as error:
                flight.failure = type(error)
                raise
            except BaseException:
                flight.failure = RegistryAcquisitionBusyError
                raise

    def acquire_business_profile_evidence(
        self,
        provider: BusinessProfileEvidenceProvider,
        identifier: str,
        *,
        case_policy: RegistryPolicySnapshot | None = None,
        policy_version: int = 0,
        cancelled: Callable[[], bool] | None = None,
    ) -> RegistryBusinessProfileAcquisitionResult:
        """Cache-first D-088 business profile evidence under its own contract key.

        The same repository, key locks and CAS writes as the shareholder contract: fresh
        COMPLETE evidence follows the freshness policy, fresh EMPTY evidence the
        definitive negative TTL, and a failed read is returned but never cached.
        """
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        identity = provider.cache_identity
        if identity is None:
            return RegistryBusinessProfileAcquisitionResult(
                evidence=provider.retrieve_business_profile_evidence(identifier),
                cache_hit=False,
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
            provider_identity=RegistryProviderIdentity(
                provider=identity.provider,
                environment=identity.environment,
                acquisition_contract_version=BUSINESS_PROFILE_EVIDENCE_CONTRACT_VERSION,
                dataset_namespace=identity.dataset_namespace,
            ),
            normalized_identifier=identifier.strip().upper(),
        )
        with self._key_lock(key.digest, cancelled=cancelled) as flight:
            if flight.failure is not None:
                raise flight.failure() from None
            try:
                return self._acquire_business_profile_locked(
                    provider, key, policy, negative_seconds, cancelled
                )
            except (ConnectorError, RegistryCacheError) as error:
                flight.failure = type(error)
                raise
            except BaseException:
                flight.failure = RegistryAcquisitionBusyError
                raise

    def _acquire_business_profile_locked(
        self,
        provider: BusinessProfileEvidenceProvider,
        key: RegistryCacheKey,
        policy: RegistryFreshnessPolicy,
        negative_seconds: int,
        cancelled: Callable[[], bool] | None,
    ) -> RegistryBusinessProfileAcquisitionResult:
        now = self._utc_now()
        entry = self._read(key)
        if entry is not None:
            self._validate_entry_for_use(entry, key, now)
            cached = entry.business_profile_evidence
            if cached is None:
                raise RegistryCacheInvalidError
            fresh = (
                registry_negative_cache_is_fresh(entry.freshness_anchor, now, negative_seconds)
                if cached.status == "EMPTY"
                else registry_cache_window_is_fresh(
                    policy.expires_at(entry.freshness_anchor), now
                )
            )
            if fresh:
                return RegistryBusinessProfileAcquisitionResult(
                    evidence=cached.model_copy(deep=True), cache_hit=True
                )
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        evidence = provider.retrieve_business_profile_evidence(key.normalized_identifier)
        bound_at = self._utc_now()
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        if (
            evidence.requested_identifier != key.normalized_identifier
            or evidence.retrieved_at > bound_at
        ):
            raise RegistryCacheInvalidError
        if evidence.status != "FAILED":
            if evidence.status == "COMPLETE" and bound_at >= policy.expires_at(
                evidence.retrieved_at
            ):
                raise RegistryCacheInvalidError
            self._write(
                RegistrySnapshotEntry(
                    cache_schema_version=5,
                    cache_id=key.digest,
                    key=key,
                    revision=entry.revision if entry is not None else 0,
                    acquisition=None,
                    business_profile_evidence=evidence,
                    freshness_anchor=evidence.retrieved_at,
                    written_at=bound_at,
                ),
                current=entry,
            )
        return RegistryBusinessProfileAcquisitionResult(
            evidence=evidence.model_copy(deep=True), cache_hit=False
        )

    def _acquire_shareholders_locked(
        self,
        provider: ShareholderEvidenceProvider,
        key: RegistryCacheKey,
        policy: RegistryFreshnessPolicy,
        negative_seconds: int,
        cancelled: Callable[[], bool] | None,
    ) -> RegistryShareholderAcquisitionResult:
        now = self._utc_now()
        entry = self._read(key)
        if entry is not None:
            self._validate_entry_for_use(entry, key, now)
            cached = entry.shareholder_evidence
            if cached is None:
                raise RegistryCacheInvalidError
            fresh = (
                registry_negative_cache_is_fresh(entry.freshness_anchor, now, negative_seconds)
                if cached.operation_result.status == RegistryOperationStatus.EMPTY
                else registry_cache_window_is_fresh(
                    policy.expires_at(entry.freshness_anchor), now
                )
            )
            if fresh:
                return RegistryShareholderAcquisitionResult(
                    evidence=cached.model_copy(deep=True), cache_hit=True
                )
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        evidence = provider.retrieve_shareholder_evidence(key.normalized_identifier)
        bound_at = self._utc_now()
        if cancelled is not None and cancelled():
            raise RegistryAcquisitionBusyError
        provenance = evidence.operation_result.provenance
        if evidence.requested_identifier != key.normalized_identifier or (
            provenance is not None and provenance.retrieved_at > bound_at
        ):
            raise RegistryCacheInvalidError
        if evidence.operation_result.status != RegistryOperationStatus.FAILED:
            if provenance is None or (
                evidence.operation_result.status == RegistryOperationStatus.COMPLETE
                and bound_at >= policy.expires_at(provenance.retrieved_at)
            ):
                raise RegistryCacheInvalidError
            self._write(
                RegistrySnapshotEntry(
                    cache_schema_version=4,
                    cache_id=key.digest,
                    key=key,
                    revision=entry.revision if entry is not None else 0,
                    acquisition=None,
                    shareholder_evidence=evidence,
                    freshness_anchor=provenance.retrieved_at,
                    written_at=bound_at,
                ),
                current=entry,
            )
        return RegistryShareholderAcquisitionResult(
            evidence=evidence.model_copy(deep=True), cache_hit=False
        )

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
                    return RegistryAcquisitionResult(
                        acquisition=None, binding=None, negative_cache_hit=True
                    )
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
                acquisition=acquisition.model_copy(deep=True),
                binding=None,
                entity_profile_reused=RegistryOperation.ENTITY_PROFILE in reusable,
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
