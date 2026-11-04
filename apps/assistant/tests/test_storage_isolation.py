"""B0: the optional data root, and test isolation from live runtime storage."""

import importlib.util
import os
import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import chromadb
import pytest
from pydantic import ValidationError

from ai_assistant import anthropic_runtime
from ai_assistant.config import AiAssistantSettings
from ai_assistant.knowledge.factory import data_dir as knowledge_dir
from ai_assistant.model_admin import store_file
from ai_assistant.model_catalog import profiles_path
from ai_assistant.model_factory import ASSISTANT_DIR, ledger_path
from tests import conftest

SCRIPT = ASSISTANT_DIR / "scripts" / "budget_ledger.py"
STORE_PATH_FIELDS = (
    "budget_ledger_path",
    "anthropic_ledger_path",
    "model_admin_db_path",
    "model_profiles_file",
    "knowledge_data_dir",
)


def _settings(**values: object) -> AiAssistantSettings:
    return AiAssistantSettings(_env_file=None, **values)  # type: ignore[arg-type]


# --- test isolation -------------------------------------------------------------------------


@pytest.mark.session_environment
def test_the_module_level_app_uses_the_session_knowledge_store() -> None:
    import ai_assistant.main as main

    folder = Path(main._settings.knowledge_data_dir)
    assert folder.is_relative_to(conftest.TEST_DATA_ROOT)
    assert not conftest.is_live_storage(knowledge_dir(main._settings))
    for name in conftest.STORE_VARIABLES:
        if name not in conftest.SESSION_STORES:
            assert name not in os.environ
    for name, path in conftest.SESSION_STORES.items():
        assert os.environ[name] == str(path)
        assert Path(path).is_relative_to(conftest.TEST_DATA_ROOT)


@pytest.mark.parametrize(
    "target",
    [
        lambda: str(ASSISTANT_DIR / "data" / "knowledge" / "knowledge.sqlite3"),
        lambda: (ASSISTANT_DIR / "data" / "budget" / "probe.sqlite3").as_uri() + "?mode=rw",
        lambda: "file:" + (ASSISTANT_DIR / "data" / "models" / "x.sqlite3").as_posix(),
    ],
)
def test_opening_a_live_sqlite_store_is_refused_before_anything_is_created(
    target: Callable[[], str],
) -> None:
    path = target()
    with pytest.raises(PermissionError, match="live runtime storage"):
        sqlite3.connect(path, uri=path.startswith("file:"))
    assert not (ASSISTANT_DIR / "data" / "budget" / "probe.sqlite3").exists()


def test_opening_a_live_chroma_store_is_refused() -> None:
    with pytest.raises(PermissionError, match="live runtime storage"):
        chromadb.PersistentClient(path=str(ASSISTANT_DIR / "data" / "knowledge" / "chroma"))


def test_a_documented_user_data_root_and_its_sidecars_are_live(tmp_path: Path) -> None:
    if os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "DataDividendsCLM" / "assistant"
        assert conftest.is_live_storage(root / "budget" / "ledger.sqlite3")
    assert conftest.is_live_storage(str(ASSISTANT_DIR / "data") + "-journal")
    assert not conftest.is_live_storage(tmp_path / "ledger.sqlite3")
    assert not conftest.is_live_storage(tmp_path)


def test_temporary_stores_still_open() -> None:
    connection = sqlite3.connect(":memory:")
    connection.close()


# --- the optional data root -----------------------------------------------------------------


@pytest.fixture(autouse=True)
def _defaults_only(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    # The settings-rule tests read the plain defaults, without the session's store settings;
    # only the test marked session_environment keeps it (it may import ai_assistant.main).
    if request.node.get_closest_marker("session_environment") is None:
        for name in conftest.SESSION_STORES:
            monkeypatch.delenv(name, raising=False)


def test_without_a_data_root_the_package_relative_defaults_are_unchanged() -> None:
    settings = _settings()
    assert settings.data_dir == ""
    assert (
        ledger_path(settings)
        == ASSISTANT_DIR / "data" / "budget" / "sessions" / "openrouter.sqlite3"
    )
    assert anthropic_runtime.ledger_file(settings) == (
        ASSISTANT_DIR / "data" / "budget" / "sessions" / "anthropic.sqlite3"
    )
    assert store_file(settings) == ASSISTANT_DIR / "data" / "models" / "model_admin.sqlite3"
    assert knowledge_dir(settings) == ASSISTANT_DIR / "data" / "knowledge"
    assert profiles_path(settings) is None


def test_a_blank_data_root_is_unset() -> None:
    assert _settings(data_dir="   ").data_dir == ""


def test_relative_store_paths_resolve_under_the_data_root(tmp_path: Path) -> None:
    settings = _settings(
        data_dir=str(tmp_path),
        anthropic_ledger_path="budget/anthropic_fyp_ledger.sqlite3",
        model_profiles_file="models/profiles.json",
    )
    root = tmp_path.resolve()
    assert settings.data_dir == str(root)
    assert ledger_path(settings) == root / "budget" / "sessions" / "openrouter.sqlite3"
    fyp = root / "budget" / "anthropic_fyp_ledger.sqlite3"
    assert anthropic_runtime.ledger_file(settings) == fyp
    assert store_file(settings) == root / "models" / "model_admin.sqlite3"
    assert profiles_path(settings) == root / "models" / "profiles.json"
    assert knowledge_dir(settings) == root / "knowledge"
    for name in STORE_PATH_FIELDS:
        assert Path(getattr(settings, name)).is_absolute()
    assert not any(root.iterdir())  # nothing is created by resolving paths


def test_absolute_store_paths_take_precedence_over_the_data_root(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere" / "state.sqlite3"
    (tmp_path / "root").mkdir()
    settings = _settings(data_dir=str(tmp_path / "root"), model_admin_db_path=str(elsewhere))
    assert store_file(settings) == elsewhere
    assert (
        ledger_path(settings)
        == (tmp_path / "root").resolve() / "budget" / "sessions" / "openrouter.sqlite3"
    )


def test_the_environment_variable_sets_the_data_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_ASSISTANT_DATA_DIR", str(tmp_path))
    assert (
        ledger_path(_settings())
        == tmp_path.resolve() / "budget" / "sessions" / "openrouter.sqlite3"
    )


@pytest.mark.parametrize(
    "root",
    [
        lambda tmp: "relative/root",
        lambda tmp: str(tmp / "missing"),
        lambda tmp: str(tmp / "a-file"),
    ],
)
def test_an_invalid_data_root_is_refused_and_never_created(
    root: Callable[[Path], str], tmp_path: Path
) -> None:
    (tmp_path / "a-file").write_text("not a folder")
    with pytest.raises(ValidationError, match="data root"):
        _settings(data_dir=root(tmp_path))
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize(
    "value", ["../escape.sqlite3", "budget/../../x.sqlite3", "data", "C:x.sqlite3", "\\x.sqlite3"]
)
def test_a_store_path_that_could_leave_the_data_root_is_refused(value: str, tmp_path: Path) -> None:
    if os.name != "nt" and value in ("C:x.sqlite3", "\\x.sqlite3"):
        pytest.skip("drive and root-relative forms are Windows path syntax")
    with pytest.raises(ValidationError, match="data root"):
        _settings(data_dir=str(tmp_path), budget_ledger_path=value)


def test_the_two_ledgers_may_still_never_share_a_file_under_a_data_root(tmp_path: Path) -> None:
    settings = _settings(
        data_dir=str(tmp_path), anthropic_ledger_path="budget/sessions/openrouter.sqlite3"
    )
    assert anthropic_runtime.ledger_file(settings) == ledger_path(settings)
    assert anthropic_runtime._limits_problem(settings) == "LEDGER_PATH_SHARED"


# --- the budget-ledger CLI ------------------------------------------------------------------


def _cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("budget_ledger_cli_b0", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CLI = _cli()


def test_the_cli_resolves_the_ledger_under_data_dir_and_prints_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert CLI.main(["--data-dir", str(tmp_path), "status"]) == 2
    err = capsys.readouterr().err
    assert f"ledger: {tmp_path.resolve() / 'budget' / 'sessions' / 'openrouter.sqlite3'}" in err
    assert "LEDGER_MISSING" in err
    assert not (tmp_path / "budget").exists()  # a missing ledger is never created


def test_the_cli_anthropic_ledger_follows_the_data_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert CLI.main(["--data-dir", str(tmp_path), "--anthropic", "status"]) == 2
    expected = tmp_path.resolve() / "budget" / "sessions" / "anthropic.sqlite3"
    assert f"ledger: {expected}" in capsys.readouterr().err


def test_the_cli_honours_the_environment_and_ledger_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AI_ASSISTANT_DATA_DIR", str(tmp_path))
    CLI.main(["status"])
    assert (
        f"ledger: {tmp_path.resolve() / 'budget' / 'sessions' / 'openrouter.sqlite3'}"
        in capsys.readouterr().err
    )
    explicit = tmp_path / "explicit.sqlite3"
    CLI.main(["--data-dir", str(tmp_path), "--ledger", str(explicit), "status"])
    assert f"ledger: {explicit}" in capsys.readouterr().err


def test_the_cli_refuses_an_invalid_data_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert CLI.main(["--data-dir", str(tmp_path / "missing"), "status"]) == 2
    assert "DATA_DIR_INVALID" in capsys.readouterr().err
    assert not (tmp_path / "missing").exists()


def test_the_cli_names_other_invalid_settings_without_their_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AI_ASSISTANT_TELEMETRY", "not-a-mode")
    assert CLI.main(["--data-dir", str(tmp_path), "status"]) == 2
    err = capsys.readouterr().err
    assert "SETTINGS_INVALID" in err and "telemetry" in err
    assert "not-a-mode" not in err and "DATA_DIR_INVALID" not in err
