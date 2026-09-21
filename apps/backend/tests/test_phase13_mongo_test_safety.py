"""Unit proofs for allowlisted, retried, redacted physical Mongo cleanup."""

from __future__ import annotations

import pytest
from scripts.mongo_test_safety import (
    MongoCleanupFailure,
    cleanup_ephemeral_mongo_database,
    generate_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)


class FakeCleanupClient:
    def __init__(self, failures: int = 0, *, remains: bool = False) -> None:
        self.failures = failures
        self.remains = remains
        self.calls = 0
        self.database = "clm_p13_0123456789abcdef01234567"

    def drop_database(self, name: str) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("mongodb://sensitive-host.invalid/private")
        if not self.remains:
            self.database = ""

    def list_database_names(self) -> list[str]:
        return [self.database] if self.database else []


def test_generated_physical_database_names_are_narrowly_allowlisted() -> None:
    for phase in ("p12", "p13", "p14", "p145", "p16", "p17", "p18", "p19"):
        database = generate_ephemeral_mongo_database(phase)
        assert require_ephemeral_mongo_database(database) == database


@pytest.mark.parametrize(
    "database",
    [
        "clm_poc",
        "clm_p13_test",
        "clm_p14_short",
        "clm_p16_short",
        "clm_p17_short",
        "clm_p18_short",
        "clm_p19_short",
        "",
        "clm_p13_../x",
    ],
)
def test_cleanup_rejects_shared_or_arbitrary_database_names(database: str) -> None:
    client = FakeCleanupClient()
    with pytest.raises(ValueError):
        cleanup_ephemeral_mongo_database(client, database)
    assert client.calls == 0


def test_cleanup_retries_and_verifies_absence() -> None:
    client = FakeCleanupClient(failures=2)
    sleeps: list[float] = []
    cleanup_ephemeral_mongo_database(
        client,
        client.database,
        attempts=3,
        backoff_seconds=0.01,
        sleep=sleeps.append,
    )
    assert client.calls == 3
    assert sleeps == [0.01, 0.02]


def test_cleanup_failure_redacts_driver_connection_details() -> None:
    client = FakeCleanupClient(failures=3)
    with pytest.raises(MongoCleanupFailure) as caught:
        cleanup_ephemeral_mongo_database(client, client.database, sleep=lambda _: None)
    message = str(caught.value)
    assert "RuntimeError" in message
    assert "sensitive-host" not in message
    assert "mongodb" not in message.lower()
