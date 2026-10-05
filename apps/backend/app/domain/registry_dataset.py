"""Explicit approved local synthetic dataset identity; no provider HTTP acquisition."""

from app.domain.models import RegistryProviderIdentity, SourceEnvironment, SourceSystem

LOCAL_SYNTHETIC_REGISTRY_DATASET = "LOCAL_SYNTHETIC_UAT_V1"


def local_synthetic_registry_identity() -> RegistryProviderIdentity:
    return RegistryProviderIdentity(
        provider=SourceSystem.ACRA,
        environment=SourceEnvironment.MOCK,
        acquisition_contract_version="PHASE10_ACQUISITION_V1",
        dataset_namespace=LOCAL_SYNTHETIC_REGISTRY_DATASET,
    )
