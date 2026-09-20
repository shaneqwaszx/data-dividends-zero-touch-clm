"""Focused tests for the optional MongoDB connectivity diagnostic."""

from unittest.mock import MagicMock

import pytest
from pymongo.errors import ServerSelectionTimeoutError
from scripts import check_mongodb

from app import mongo
from app.config import Settings


def settings_without_mongo() -> Settings:
    return Settings(_env_file=None, mongo_uri=None)


def test_create_mongo_client_requires_optional_configuration() -> None:
    with pytest.raises(ValueError, match="MONGO_URI is not configured"):
        mongo.create_mongo_client(settings_without_mongo())


def test_ping_mongodb_closes_client_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(mongo, "create_mongo_client", lambda settings: client)

    mongo.ping_mongodb(settings_without_mongo())

    client.admin.command.assert_called_once_with("ping")
    client.close.assert_called_once_with()


def test_ping_mongodb_closes_client_after_server_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.admin.command.side_effect = ServerSelectionTimeoutError("private server detail")
    monkeypatch.setattr(mongo, "create_mongo_client", lambda settings: client)

    with pytest.raises(ServerSelectionTimeoutError):
        mongo.ping_mongodb(settings_without_mongo())

    client.close.assert_called_once_with()


def test_count_users_pings_reads_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    collection = client.__getitem__.return_value.__getitem__.return_value
    collection.count_documents.return_value = 3
    monkeypatch.setattr(mongo, "create_mongo_client", lambda settings: client)

    assert mongo.count_users(settings_without_mongo()) == 3

    client.admin.command.assert_called_once_with("ping")
    client.__getitem__.assert_called_once_with("FYP")
    client.__getitem__.return_value.__getitem__.assert_called_once_with("users")
    collection.count_documents.assert_called_once_with({})
    client.close.assert_called_once_with()


def test_check_script_reports_only_safe_failure_class(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable(settings: Settings) -> None:
        del settings
        raise ServerSelectionTimeoutError("mongodb://secret-host.example")

    monkeypatch.setenv("MONGO_URI", "mongodb://secret-host.example")
    monkeypatch.setattr(check_mongodb, "ping_mongodb", unavailable)

    assert check_mongodb.main() == 1
    assert capsys.readouterr().out == "MongoDB check failed: ServerSelectionTimeoutError\n"


def test_check_script_reports_connectivity_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: list[Settings] = []
    monkeypatch.setenv("MONGO_URI", "mongodb://configured-but-not-printed.example")
    monkeypatch.setattr(check_mongodb, "ping_mongodb", observed.append)

    assert check_mongodb.main() == 0
    assert capsys.readouterr().out == "MongoDB connectivity check successful.\n"
    assert len(observed) == 1
    assert observed[0].mongo_uri is not None


def test_check_script_does_not_load_dotenv_or_read_database_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[object] = []

    class ExplicitSettings:
        def __init__(self, **kwargs: object) -> None:
            calls.append(kwargs)

    monkeypatch.setenv("MONGO_URI", "mongodb://explicit.example")
    monkeypatch.setattr(check_mongodb, "Settings", ExplicitSettings)
    monkeypatch.setattr(check_mongodb, "ping_mongodb", calls.append)

    assert check_mongodb.main() == 0
    assert calls[0] == {
        "_env_file": None,
        "mongo_uri": "mongodb://explicit.example",
    }


def test_check_script_requires_explicit_process_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setattr(
        check_mongodb,
        "ping_mongodb",
        lambda settings: pytest.fail(f"unexpected ping: {settings!r}"),
    )

    assert check_mongodb.main() == 1
    assert capsys.readouterr().out == "MongoDB check failed: MONGO_URI_UNAVAILABLE\n"
