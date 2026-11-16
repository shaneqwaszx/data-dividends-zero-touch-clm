"""Mongo-backed daily GoldTier Sandbox read budget (ST-7).

One document per UTC day, claimed with a single conditional update, so the limit holds
across processes and restarts. An unavailable store refuses the read (fail closed).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import MongoClient, ReturnDocument
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.connectors.goldtier_read_budget import budget_day
from app.persistence.errors import PersistenceUnavailableError


class MongoGoldTierReadBudget:
    def __init__(
        self,
        client: MongoClient[dict[str, Any]],
        *,
        database: str,
        collection: str,
        limit: int,
    ) -> None:
        if limit < 0:
            raise ValueError("limit must not be negative")
        self._client = client
        self._collection: Collection[dict[str, Any]] = client[database][collection]
        self._limit = limit

    @property
    def limit(self) -> int | None:
        return self._limit

    def initialize(self) -> None:
        try:
            self._client.admin.command("ping")
        except PyMongoError:
            raise PersistenceUnavailableError from None

    def close(self) -> None:
        self._client.close()

    def claim(self, now: datetime) -> bool:
        if self._limit <= 0:
            return False
        under_limit = {"_id": budget_day(now), "count": {"$lt": self._limit}}
        increment = {"$inc": {"count": 1}}
        try:
            try:
                # Matches only while the day is under its limit; with no document yet the
                # upsert creates it at 1.
                self._collection.find_one_and_update(
                    under_limit, increment, upsert=True, return_document=ReturnDocument.AFTER
                )
            except DuplicateKeyError:
                # The day's document exists and is at its limit, or another process created
                # it at the same moment. Retry once without upsert: None means exhausted.
                return (
                    self._collection.find_one_and_update(
                        under_limit, increment, return_document=ReturnDocument.AFTER
                    )
                    is not None
                )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return True

    def used(self, now: datetime) -> int:
        try:
            raw = self._collection.find_one({"_id": budget_day(now)})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        count = (raw or {}).get("count", 0)
        return count if isinstance(count, int) and not isinstance(count, bool) else 0
