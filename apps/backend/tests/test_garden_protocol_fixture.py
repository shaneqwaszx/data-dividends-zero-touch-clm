from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from pydantic import SecretStr
from pypdf import PdfReader
from scripts.garden_protocol_fixture import OfflineGardenProtocolTransport

from app.composition import build_acra_connector
from app.config import Settings
from app.connectors.registry import AcraRegistryProviderAdapter
from app.domain.models import RegistryOperationStatus
from app.main import create_app


def fixture_settings() -> Settings:
    # D-112: these legacy Garden fixture flows explicitly opt in to the labelled local
    # supplement; Garden's normal happy path is the reviewed creator declaration
    # (tests/test_declared_ownership_discovery.py).
    return Settings(
        _env_file=None, app_env="test", clm_persistence_mode="memory",
        acra_connector_mode="api_marketplace_mock", goldtier_connector_mode="mock",
        garden_supplement_enabled=True,
        acra_api_marketplace_mock_client_id=SecretStr(secrets.token_urlsafe(32)),
        acra_api_marketplace_mock_secret_key=SecretStr(secrets.token_urlsafe(32)),
    )


def test_offline_protocol_exercises_real_decoder_and_keeps_missing_ownership() -> None:
    settings = fixture_settings()
    transport = OfflineGardenProtocolTransport()
    connector = build_acra_connector(
        settings, transport=transport, marketplace_token_transport=transport,
    )
    bundle = AcraRegistryProviderAdapter(connector).retrieve_acquisition("11111999A")
    assert bundle is not None
    assert bundle.entity_profile.legal_name == "GARDEN BUSINESS"
    assert bundle.ownership_parties == ()
    assert bundle.relationships == ()
    assert bundle.operation_results[2].status == RegistryOperationStatus.EMPTY
    assert bundle.operation_results[3].status == RegistryOperationStatus.UNSUPPORTED
    assert bundle.operation_results[3].provenance is None
    assert transport.calls == ["TOKEN", "ENTITY_PROFILE", "ENTITY_PROFILE", "SHAREHOLDERS"]


def test_offline_protocol_unknown_identity_and_operation_fail_without_fallback() -> None:
    transport = OfflineGardenProtocolTransport()
    with pytest.raises(ValueError, match="allowlist"):
        transport.get("https://unapproved.invalid/lookup", headers={}, timeout_seconds=1)
    assert transport.calls == []


def test_offline_profile_requires_explicit_test_memory_injection() -> None:
    with pytest.raises(ValueError, match="injected test/memory"):
        create_app(settings=fixture_settings(), e2e_acra_protocol_fixture=True)


@pytest.mark.parametrize("variant", ["clean", "conflicting"])
def test_synthetic_client_pdfs_are_labelled_and_extract_supported_fields(variant: str) -> None:
    fixture = Path(__file__).parent / "fixtures/uat" / (
        f"garden-business-{variant}-onboarding-profile.pdf"
    )
    reader = PdfReader(fixture)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "SYNTHETIC TEST / CLIENT-SUPPLIED DEMO EVIDENCE" in text
    assert "not an ACRA extract" in text
    for label in ("Legal Name:", "UEN:", "Registered Address:", "Country:"):
        assert label in text
    expected_identifier = "11111999A" if variant == "clean" else "11111998B"
    assert f"UEN: {expected_identifier}" in text
