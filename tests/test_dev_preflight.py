from __future__ import annotations

from pydantic import SecretStr

from scripts import dev_preflight


def _settings(**overrides: object):
    values: dict[str, object] = {
        "app_env": "test",
        "clm_persistence_mode": "memory",
        "acra_connector_mode": "api_marketplace_mock",
        "acra_api_marketplace_mock_client_id": SecretStr("client-id"),
        "acra_api_marketplace_mock_secret_key": SecretStr("secret-key"),
        "goldtier_connector_mode": "mock",
    }
    values.update(overrides)
    return dev_preflight.Settings(_env_file=None, **values)


def test_memory_profile_never_checks_or_requires_mongo() -> None:
    mongo_calls = 0

    def mongo_ping(_settings: object) -> None:
        nonlocal mongo_calls
        mongo_calls += 1

    result = dev_preflight.inspect_runtime(
        _settings(),
        connector_builder=lambda _settings: object(),
        mongo_ping=mongo_ping,
    )

    assert result.exit_code == 0
    assert result.facts["Mongo required"] == "no"
    assert result.facts["Mongo reachable"] == "not-required"
    assert mongo_calls == 0


def test_mongo_profile_reports_unreachable_without_connection_details() -> None:
    settings = _settings(
        clm_persistence_mode="mongo",
        mongo_uri=SecretStr("mongodb://private-host.example"),
    )

    result = dev_preflight.inspect_runtime(
        settings,
        connector_builder=lambda _settings: object(),
        mongo_ping=lambda _settings: (_ for _ in ()).throw(RuntimeError("private-host.example")),
    )
    rendered = result.render()

    assert result.exit_code == 1
    assert result.facts["Mongo reachable"] == "no"
    assert "Mongo persistence is configured but Mongo is unreachable." in rendered
    assert "private-host.example" not in rendered


def test_missing_official_mock_credential_names_are_reported_without_values() -> None:
    settings = _settings(acra_api_marketplace_mock_secret_key=None)

    result = dev_preflight.inspect_runtime(
        settings,
        connector_builder=lambda _settings: (_ for _ in ()).throw(RuntimeError("secret-value")),
        mongo_ping=lambda _settings: None,
    )
    rendered = result.render()

    assert result.exit_code == 1
    assert "ACRA_API_MARKETPLACE_MOCK_SECRET_KEY" in rendered
    assert "secret-value" not in rendered
    assert result.facts["ACRA client id present"] == "yes"
    assert result.facts["ACRA secret present"] == "no"
