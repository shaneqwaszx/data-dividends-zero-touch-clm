"""Which identity evidence a target accepts, decided by provenance and never by entity type."""

from dataclasses import dataclass

from app.domain.models import CanonicalLegalEntity, SourceEnvironment, SourceSystem


@dataclass(frozen=True)
class AcceptedIdentitySource:
    """One reviewed provider contract whose canonical identity a target may rely on."""

    source_system: SourceSystem
    environment: SourceEnvironment
    reference_prefix: str

    def __post_init__(self) -> None:
        if not self.reference_prefix.endswith("/"):
            raise ValueError("An accepted source reference must end at a path boundary.")

    def provided(self, entity: CanonicalLegalEntity) -> bool:
        source = entity.source
        return (
            source.source_system == self.source_system
            and source.environment == self.environment
            and source.registry_source_link.startswith(self.reference_prefix)
        )


@dataclass(frozen=True)
class TargetIdentityEvidencePolicy:
    """Add a source only with its own reviewed contract; no source means nothing is accepted."""

    accepted_sources: tuple[AcceptedIdentitySource, ...]

    def accepts(self, entity: CanonicalLegalEntity | None) -> bool:
        return entity is not None and any(
            source.provided(entity) for source in self.accepted_sources
        )
