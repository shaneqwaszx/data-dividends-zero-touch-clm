from typing import Any

import pytest
from scripts import acra_sandbox_smoke

from app.config import Settings


class SuccessfulSmokeConnector:
    def fetch_company(self, uen: str) -> object:
        del uen
        return object()


def test_disabled_smoke_guard_runs_before_settings_or_composition(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ACRA_LIVE_SMOKE_ENABLED", raising=False)
    monkeypatch.setattr(
        acra_sandbox_smoke,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("settings must not load")),
    )

    result = acra_sandbox_smoke.main()
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == "NOT EXECUTED: ACRA sandbox smoke verification is not enabled.\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    "settings",
    [
        Settings(app_env="test", acra_connector_mode="sandbox"),
        Settings(
            app_env="test",
            acra_connector_mode="sandbox",
            acra_base_url="http://insecure.synthetic-acra.example",
            acra_company_path_template="/business-profile/{uen}",
        ),
    ],
    ids=["missing", "invalid"],
)
def test_enabled_smoke_with_bad_configuration_is_status_only(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_sentinel = "PRIVATE-SMOKE-CONFIG-9f3a"
    monkeypatch.setenv("ACRA_LIVE_SMOKE_ENABLED", "true")
    monkeypatch.setenv("ACRA_SMOKE_UEN", "202400001A")
    monkeypatch.setattr(acra_sandbox_smoke, "get_settings", lambda: settings)
    monkeypatch.setenv("ACRA_AUTH_HEADER_VALUE", private_sentinel)

    result = acra_sandbox_smoke.main()
    captured = capsys.readouterr()

    assert result == 1
    assert captured.out.startswith("FAILED:")
    assert "traceback" not in (captured.out + captured.err).lower()
    assert private_sentinel not in captured.out + captured.err
    assert "202400001A" not in captured.out + captured.err
    assert captured.err == ""


def test_enabled_smoke_safe_fake_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = Settings(
        app_env="test",
        acra_connector_mode="sandbox",
        acra_base_url="https://sandbox.synthetic-acra.example",
        acra_company_path_template="/business-profile/{uen}",
    )
    monkeypatch.setenv("ACRA_LIVE_SMOKE_ENABLED", "true")
    monkeypatch.setenv("ACRA_SMOKE_UEN", "202400001A")
    monkeypatch.setattr(acra_sandbox_smoke, "get_settings", lambda: settings)

    def fake_builder(active_settings: Settings, **kwargs: Any) -> SuccessfulSmokeConnector:
        del active_settings, kwargs
        return SuccessfulSmokeConnector()

    monkeypatch.setattr(acra_sandbox_smoke, "build_acra_connector", fake_builder)

    result = acra_sandbox_smoke.main()
    captured = capsys.readouterr()

    assert result == 0
    assert captured.out == (
        "EXECUTED: ACRA returned a response that passed the configured source decoder.\n"
    )
    assert "202400001A" not in captured.out
    assert captured.err == ""
