"""Fail-closed database naming and cleanup for opt-in physical Mongo tests."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

EPHEMERAL_MONGO_DATABASE_PATTERN = re.compile(
    r"^clm_p(?:12|13|14|145|16|17|18)_[0-9a-f]{24}$"
)


class MongoCleanupClient(Protocol):
    def drop_database(self, name: str) -> object: ...

    def list_database_names(self) -> list[str]: ...


class MongoCleanupFailure(RuntimeError):
    """Safe terminal cleanup failure with no underlying connection detail."""


def generate_ephemeral_mongo_database(phase: str) -> str:
    if phase not in {"p12", "p13", "p14", "p145", "p16", "p17", "p18"}:
        raise ValueError("unsupported physical-test phase")
    return f"clm_{phase}_{uuid4().hex[:24]}"


def require_ephemeral_mongo_database(database: str) -> str:
    if not EPHEMERAL_MONGO_DATABASE_PATTERN.fullmatch(database):
        raise ValueError("physical Mongo operations require an isolated test database")
    return database


def cleanup_ephemeral_mongo_database(
    client: MongoCleanupClient,
    database: str,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.1,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Drop and verify an allowlisted test database, retrying transient failures."""

    require_ephemeral_mongo_database(database)
    if attempts < 1:
        raise ValueError("cleanup attempts must be positive")
    failure_type = "DatabaseStillPresent"
    for attempt in range(attempts):
        try:
            client.drop_database(database)
            if database not in client.list_database_names():
                return
            failure_type = "DatabaseStillPresent"
        except Exception as exc:  # noqa: BLE001 - redacted boundary for driver errors
            failure_type = type(exc).__name__
        if attempt + 1 < attempts:
            sleep(backoff_seconds * (attempt + 1))
    raise MongoCleanupFailure(
        f"isolated Mongo test database cleanup failed after {attempts} attempts "
        f"({failure_type})"
    )
