"""Strict Mongo adapter for the independent registry snapshot collection."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ValidationError
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.domain.models import RegistryCacheKey, RegistrySnapshotEntry
from app.services.registry_cache_repository import (
    RegistrySnapshotRepositoryConflictError,
    RegistrySnapshotRepositoryInvalidError,
    RegistrySnapshotRepositoryUnavailableError,
)


class MongoRegistryCacheStore:
    """Persist lossless ISO-serialized complete snapshots with strict CAS."""

    def __init__(
        self,
        client: MongoClient[dict[str, Any]],
        *,
        database: str,
        collection: str,
    ) -> None:
        self._client = client
        self._collection: Collection[dict[str, Any]] = client[database][collection]

    def initialize(self) -> None:
        try:
            self._client.admin.command("ping")
            self._collection.create_index(
                [("cache_id", ASCENDING)], unique=True, name="cache_id_unique"
            )
            self._collection.create_index(
                [
                    ("key.provider_identity.provider", ASCENDING),
                    ("key.provider_identity.environment", ASCENDING),
                    ("key.provider_identity.acquisition_contract_version", ASCENDING),
                    ("key.provider_identity.dataset_namespace", ASCENDING),
                    ("key.normalized_identifier", ASCENDING),
                ],
                unique=True,
                name="registry_cache_exact_key_unique",
            )
            for raw in self._collection.find({}):
                self._decode(raw)
        except RegistrySnapshotRepositoryInvalidError:
            raise
        except PyMongoError:
            raise RegistrySnapshotRepositoryUnavailableError from None

    def get(self, key: RegistryCacheKey) -> RegistrySnapshotEntry | None:
        try:
            raw = self._collection.find_one({"_id": key.digest})
        except PyMongoError:
            raise RegistrySnapshotRepositoryUnavailableError from None
        return self._decode(raw) if raw is not None else None

    def create(self, entry: RegistrySnapshotEntry) -> RegistrySnapshotEntry:
        candidate = RegistrySnapshotEntry.model_validate(entry)
        if candidate.revision != 0:
            raise RegistrySnapshotRepositoryInvalidError
        try:
            self._collection.insert_one(self._encode(candidate))
        except DuplicateKeyError:
            raise RegistrySnapshotRepositoryConflictError from None
        except PyMongoError:
            raise RegistrySnapshotRepositoryUnavailableError from None
        return candidate.model_copy(deep=True)

    def replace(
        self,
        entry: RegistrySnapshotEntry,
        *,
        expected_revision: int,
    ) -> RegistrySnapshotEntry:
        candidate = RegistrySnapshotEntry.model_validate(entry)
        if candidate.revision != expected_revision:
            raise RegistrySnapshotRepositoryInvalidError
        persisted = candidate.model_copy(
            update={"revision": expected_revision + 1}, deep=True
        )
        try:
            result = self._collection.replace_one(
                {"_id": candidate.cache_id, "revision": expected_revision},
                self._encode(persisted),
            )
        except PyMongoError:
            raise RegistrySnapshotRepositoryUnavailableError from None
        if result.modified_count != 1:
            raise RegistrySnapshotRepositoryConflictError
        return persisted.model_copy(deep=True)

    @staticmethod
    def _encode(entry: RegistrySnapshotEntry) -> dict[str, Any]:
        raw = entry.model_dump(mode="json")
        raw["_id"] = entry.cache_id
        return raw

    @staticmethod
    def _decode(raw: dict[str, Any]) -> RegistrySnapshotEntry:
        mongo_id = raw.get("_id")
        if not isinstance(mongo_id, str):
            raise RegistrySnapshotRepositoryInvalidError
        value = dict(raw)
        value.pop("_id")
        try:
            entry = RegistrySnapshotEntry.model_validate(value)
            _reject_unknown_model_fields(value, entry)
        except RegistrySnapshotRepositoryInvalidError:
            raise
        except (ValidationError, ValueError, TypeError):
            raise RegistrySnapshotRepositoryInvalidError from None
        if mongo_id != entry.cache_id or mongo_id != entry.key.digest:
            raise RegistrySnapshotRepositoryInvalidError
        return entry


def _reject_unknown_model_fields(raw: object, parsed: object) -> None:
    if isinstance(parsed, BaseModel):
        if not isinstance(raw, dict):
            raise RegistrySnapshotRepositoryInvalidError
        allowed = set(type(parsed).model_fields)
        if set(raw) - allowed:
            raise RegistrySnapshotRepositoryInvalidError
        for name in allowed.intersection(raw):
            _reject_unknown_model_fields(raw[name], getattr(parsed, name))
        return
    if isinstance(parsed, (list, tuple)):
        if not isinstance(raw, list) or len(raw) != len(parsed):
            raise RegistrySnapshotRepositoryInvalidError
        for raw_item, parsed_item in zip(raw, parsed, strict=True):
            _reject_unknown_model_fields(raw_item, parsed_item)
        return
    if isinstance(parsed, dict):
        expected = {str(key.value if isinstance(key, Enum) else key) for key in parsed}
        if not isinstance(raw, dict) or set(raw) != expected:
            raise RegistrySnapshotRepositoryInvalidError
        for key, parsed_item in parsed.items():
            raw_key = str(key.value if isinstance(key, Enum) else key)
            _reject_unknown_model_fields(raw[raw_key], parsed_item)
