"""D-138 R4: the hosted deployment checks each named provider's spending store before it starts.

Read-only: a check never creates, recovers, migrates, resets or deletes a store, and every code
has a recovery that needs no database edit. Synthetic values only; no provider, key or network.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ai_assistant import anthropic_runtime
from ai_assistant.anthropic_profiles import LEDGER_PROFILE_ID as ANTHROPIC_PROFILE_ID
from ai_assistant.budget import BudgetLedger
from ai_assistant.model_factory import ledger_path
from ai_assistant.model_profiles import OPENROUTER_PROFILE_ID
from assistant_hosting import ledger_health, profile
from tests.test_budget_ledger import _corrupt
from tests.test_hosted_claude import CLAUDE_ENV, pinned
from tests.test_hosting import ELIGIBLE, hosted_settings, no_files

ASSISTANT_DIR = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _store(path: Path, profile_id: str = ANTHROPIC_PROFILE_ID) -> BudgetLedger:
    return BudgetLedger.initialise(
        path,
        cap_micro_usd=5_000_000,
        opening_usage_micro_usd=0,
        key_alias="key-01",
        profile_id=profile_id,
        opening_basis="session_store",
    )


def _claude_store(tmp_path: Path) -> Path:
    return anthropic_runtime.ledger_file(hosted_settings(tmp_path))


def test_the_hosted_stores_are_the_session_stores_inside_the_data_volume(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    stores = ledger_health.stores(settings)
    root = tmp_path.resolve()
    for path, _profile in stores.values():
        assert path.resolve().is_relative_to(root)
        assert path.parent.name == "sessions"
    assert stores["anthropic"][0] == anthropic_runtime.ledger_file(settings)
    assert stores["openrouter"][0] == ledger_path(settings)


def test_a_genuine_first_start_is_not_refused_and_creates_nothing(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    found = profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned)
    assert found == []
    [item] = ledger_health.report(settings, CLAUDE_ENV)
    assert (item.state, item.blocking, item.warnings) == (
        "absent",
        None,
        ("LEDGER_CREATED_AT_SETUP",),
    )
    assert not _claude_store(tmp_path).exists()


def test_the_model_free_service_checks_no_store(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    assert ledger_health.report(settings, ELIGIBLE) == []
    assert ledger_health.config_codes(settings, ELIGIBLE) == []


def test_a_healthy_store_passes_unchanged_and_survives_a_restart(tmp_path: Path) -> None:
    path = _claude_store(tmp_path)
    ledger = _store(path)
    before = (_digest(path), ledger.status())
    settings = hosted_settings(tmp_path)
    assert profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned) == []
    [item] = ledger_health.report(settings, CLAUDE_ENV)
    assert (item.state, item.blocking, item.warnings) == ("present", None, ())
    # Read-only, and a new process (a restart or a new image on the same volume) sees the same
    # store and the same record.
    assert _digest(path) == before[0]
    assert BudgetLedger(path).status() == before[1]


@pytest.mark.parametrize(
    ("how", "code"),
    [
        ("format_1", "LEGACY_STORE"),
        ("garbage", "LEDGER_CORRUPT"),
        ("truncated", "LEDGER_CORRUPT"),
        ("newer", "LEDGER_SCHEMA_UNSUPPORTED"),
        ("dropped_fence", "LEDGER_SCHEMA_UNSUPPORTED"),
        ("baseline_below_provider", "LEDGER_INCONSISTENT"),
    ],
)
def test_an_unusable_store_refuses_the_start_and_is_never_changed(
    tmp_path: Path, how: str, code: str
) -> None:
    path = _claude_store(tmp_path)
    _store(path)
    _corrupt(path, how)
    before = _digest(path)
    settings = hosted_settings(tmp_path)
    found = profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned)
    assert code in found
    assert _digest(path) == before
    assert code in ledger_health.ACTIONS


def test_another_providers_store_at_the_claude_path_is_refused(tmp_path: Path) -> None:
    path = _claude_store(tmp_path)
    _store(path, OPENROUTER_PROFILE_ID)
    settings = hosted_settings(tmp_path)
    assert ledger_health.config_codes(settings, CLAUDE_ENV) == ["LEDGER_PROFILE_MISMATCH"]


def test_a_folder_the_service_cannot_write_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ledger_health.os, "access", lambda *_args, **_kw: False)
    settings = hosted_settings(tmp_path)
    assert ledger_health.config_codes(settings, CLAUDE_ENV) == ["LEDGER_DIR_NOT_WRITABLE"]
    _store(_claude_store(tmp_path))
    assert ledger_health.config_codes(settings, CLAUDE_ENV) == ["LEDGER_NOT_WRITABLE"]


def test_interrupted_work_is_reported_and_never_blocks(tmp_path: Path) -> None:
    path = _claude_store(tmp_path)
    ledger = _store(path)
    ledger.open_breaker("abandoned_call")
    path.with_name(path.name + ".reconcile.intent").write_text("{}", "utf-8")
    settings = hosted_settings(tmp_path)
    [item] = ledger_health.report(settings, CLAUDE_ENV)
    assert item.blocking is None
    assert set(item.warnings) == {"BREAKER_OPEN", "RECONCILE_INTENT_PRESENT"}
    assert profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned) == []


def test_the_operator_report_names_codes_and_actions_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _claude_store(tmp_path)
    _store(path)
    _corrupt(path, "format_1")
    settings = hosted_settings(tmp_path)
    monkeypatch.setattr(ledger_health, "AiAssistantSettings", lambda: settings)
    for name, value in CLAUDE_ENV.items():
        monkeypatch.setenv(name, value)
    assert ledger_health.main() == 1
    out = capsys.readouterr().out
    assert "BLOCKING LEGACY_STORE" in out and "backup_stores.py" in out
    assert "$" not in out and "5000000" not in out and str(tmp_path) not in out


def test_every_blocking_code_has_a_documented_recovery() -> None:
    readme = (ASSISTANT_DIR / "deploy" / "LEDGER_RECOVERY.md").read_text("utf-8")
    for code in (*ledger_health.ACTIONS, *ledger_health.WARNINGS):
        assert f"`{code}`" in readme
    assert "never edit" in readme.lower()


def _audit(settings_path: Path, profile_id: str, outcome: str = "passed") -> None:
    import sqlite3

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings_path) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT,"
            " actor TEXT, role TEXT, action TEXT, profile_id TEXT, fingerprint TEXT,"
            " outcome TEXT, code TEXT, revision INTEGER)"
        )
        db.execute(
            "INSERT INTO events (at, actor, action, profile_id, outcome) VALUES"
            " ('2026-11-15T00:00:00+00:00', 'biz-ops', 'CONNECTION_TEST', ?, ?)",
            (profile_id, outcome),
        )


def test_a_store_that_vanished_after_use_is_never_treated_as_a_first_start(
    tmp_path: Path,
) -> None:
    settings = hosted_settings(tmp_path)
    audit = Path(settings.model_admin_db_path)
    # A failed test proves nothing: still a first start.
    _audit(audit, "anthropic_claude_sonnet_5_5_medium", "failed")
    assert ledger_health.config_codes(settings, CLAUDE_ENV) == []
    _audit(audit, "anthropic_claude_sonnet_5_5_medium")
    found = profile.refusals(settings, CLAUDE_ENV, env_files=no_files(), resolve=pinned)
    assert found == ["LEDGER_MISSING_AFTER_USE"]
    assert not _claude_store(tmp_path).exists()
    # The GPT-OSS store is judged on GPT-OSS's own history only.
    openrouter = ledger_path(settings)
    item = ledger_health.check("openrouter", openrouter, OPENROUTER_PROFILE_ID, settings=settings)
    assert item.blocking is None
    _audit(audit, OPENROUTER_PROFILE_ID)
    item = ledger_health.check("openrouter", openrouter, OPENROUTER_PROFILE_ID, settings=settings)
    assert item.blocking == "LEDGER_MISSING_AFTER_USE"


def test_an_unreadable_audit_cannot_prove_a_first_start(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    audit = Path(settings.model_admin_db_path)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_bytes(b"\x00not a database" * 64)
    assert ledger_health.config_codes(settings, CLAUDE_ENV) == ["LEDGER_AUDIT_UNREADABLE"]


def test_the_gpt_oss_store_is_checked_with_its_own_profile(tmp_path: Path) -> None:
    settings = hosted_settings(tmp_path)
    path = ledger_path(settings)
    _store(path, OPENROUTER_PROFILE_ID)
    before = _digest(path)
    item = ledger_health.check("openrouter", path, OPENROUTER_PROFILE_ID, settings=settings)
    assert (item.state, item.blocking) == ("present", None)
    wrong = ledger_health.check("openrouter", path, ANTHROPIC_PROFILE_ID, settings=settings)
    assert wrong.blocking == "LEDGER_PROFILE_MISMATCH"
    assert _digest(path) == before


def test_the_operator_report_refuses_an_invalid_provider_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = hosted_settings(tmp_path)
    monkeypatch.setattr(ledger_health, "AiAssistantSettings", lambda: settings)
    monkeypatch.setenv("ASSISTANT_HOSTING_PROVIDER", "anthropic,anthropic")
    assert ledger_health.main() == 1
    assert "PROVIDER_MODE_INVALID" in capsys.readouterr().out
