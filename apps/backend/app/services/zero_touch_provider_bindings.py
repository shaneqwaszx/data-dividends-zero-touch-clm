"""Process-local opaque ownership-provider bindings for one automation journey."""

from collections.abc import Callable
from threading import RLock
from typing import Protocol
from uuid import uuid4

from app.connectors.ownership import OwnershipProvider

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
