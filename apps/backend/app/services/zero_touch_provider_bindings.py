"""Process-local opaque ownership-provider bindings for one automation journey."""

from collections.abc import Callable
from hashlib import sha256
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.connectors.mock_ownership import MockOwnershipProvider, MockOwnershipScenario
from app.connectors.ownership import OwnershipProvider
from app.connectors.registry_ownership import RegistryAcquisitionOwnershipProvider

ProviderFactory = Callable[[], OwnershipProvider]


class OwnershipProviderBindingResolver(Protocol):
    @property
    def default_binding_id(self) -> str: ...

    def register(self, factory: ProviderFactory) -> str: ...

    def resolve(self, binding_id: str) -> OwnershipProvider | None: ...


class InMemoryOwnershipProviderBindingResolver:
    """Keep provider factories outside persisted automation records."""

    def __init__(self, default_factory: ProviderFactory) -> None:
        self._factories: dict[str, ProviderFactory] = {}
        self._lock = RLock()
        self._default_binding_id = self.register(default_factory)

    @property
    def default_binding_id(self) -> str:
        return self._default_binding_id

    def register(self, factory: ProviderFactory) -> str:
        binding_id = uuid4().hex
        with self._lock:
            self._factories[binding_id] = factory
        return binding_id

    def resolve(self, binding_id: str) -> OwnershipProvider | None:
        with self._lock:
            factory = self._factories.get(binding_id)
        return factory() if factory is not None else None


class DurableOwnershipProviderBindingResolver:
    """Reconstruct only approved deterministic providers from stable opaque IDs."""

    _REGISTRY_PROFILE = "REGISTRY_ACQUISITION"

    def __init__(self, default_factory: ProviderFactory) -> None:
        self._default_factory = default_factory
        self._default_binding_id = self._binding_id(self._REGISTRY_PROFILE)

    @property
    def default_binding_id(self) -> str:
        return self._default_binding_id

    def register(self, factory: ProviderFactory) -> str:
        provider = factory()
        if isinstance(provider, RegistryAcquisitionOwnershipProvider):
            return self._default_binding_id
        if isinstance(provider, MockOwnershipProvider):
            return self._binding_id(f"MOCK:{provider.scenario.value}")
        raise ValueError("ownership provider is not restart-reconstructible")

    def resolve(self, binding_id: str) -> OwnershipProvider | None:
        if binding_id == self._default_binding_id:
            return self._default_factory()
        for scenario in MockOwnershipScenario:
            if binding_id == self._binding_id(f"MOCK:{scenario.value}"):
                return MockOwnershipProvider(scenario)
        return None

    @staticmethod
    def _binding_id(profile: str) -> str:
        return sha256(f"phase12:{profile}".encode()).hexdigest()
