"""Mongo persistence for global teams, profiles, and the singleton policy catalogue."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from threading import RLock
from typing import Any
from uuid import UUID

from pydantic import BaseModel, SecretStr, ValidationError
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.domain.access import Role, TeamId
from app.domain.administration import (
    CredentialOperation,
    TeamRecord,
    UserAccountRecord,
    audit_is_prefix,
)
from app.domain.policy import PolicyCatalogue
from app.persistence.errors import PersistenceDataInvalidError, PersistenceUnavailableError
from app.persistence.mongo_case_store import _reject_unknown_model_fields
from app.services.admin_repository import (
    AdministrationAuthorityInvariantError,
    AdministrationConflictError,
    build_credential_reset_candidate,
    build_profile_authority_candidate,
    check_credential_replacement_actor,
)


class MongoAdminStore:
    def __init__(
        self,
        client: MongoClient[dict[str, Any]],
        *,
        database: str,
        teams_collection: str,
        profiles_collection: str,
        policies_collection: str,
    ) -> None:
        db = client[database]
        self._client = client
        self.teams: Collection[dict[str, Any]] = db[teams_collection]
        self.profiles: Collection[dict[str, Any]] = db[profiles_collection]
        self.policies: Collection[dict[str, Any]] = db[policies_collection]
        self.lock = RLock()

    def initialize(self) -> None:
        try:
            self._client.admin.command("ping")
            for raw in self.teams.find({}):
                _decode(raw, TeamRecord)
            for raw in self.profiles.find({}):
                _decode(raw, UserAccountRecord)
            for raw in self.policies.find({}):
                _decode(raw, PolicyCatalogue)
            self.teams.create_index(
                [("normalized_display_name", ASCENDING)],
                unique=True,
                name="normalized_display_name_unique",
            )
            self.teams.create_index(
                [("normalized_client_scope_label", ASCENDING)],
                unique=True,
                name="normalized_client_scope_label_unique",
            )
            self.teams.create_index(
                [("active", ASCENDING), ("display_name", ASCENDING)],
                name="active_display_name",
            )
            self.profiles.create_index(
                [("role", ASCENDING), ("team_id", ASCENDING)], name="role_team"
            )
        except PersistenceDataInvalidError:
            raise
        except PyMongoError:
            raise PersistenceUnavailableError from None


class MongoTeamRepository:
    def __init__(self, store: MongoAdminStore) -> None:
        self._store = store

    def list(self) -> list[TeamRecord]:
        try:
            raw = list(self._store.teams.find({}).sort([("active", -1), ("display_name", 1)]))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [_decode(item, TeamRecord) for item in raw]

    def get(self, team_id: TeamId) -> TeamRecord | None:
        try:
            raw = self._store.teams.find_one({"_id": str(team_id)})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return _decode(raw, TeamRecord) if raw is not None else None

    def create(self, record: TeamRecord) -> TeamRecord:
        candidate = TeamRecord.model_validate(record)
        try:
            self._store.teams.insert_one(_encode(candidate, str(candidate.team_id)))
        except DuplicateKeyError:
            raise AdministrationConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return candidate.model_copy(deep=True)

    def update(self, record: TeamRecord, *, expected_version: int) -> TeamRecord:
        candidate = TeamRecord.model_validate(record)
        current = self.get(candidate.team_id)
        if current is None or not audit_is_prefix(current.audit_events, candidate.audit_events):
            raise AdministrationConflictError
        try:
            result = self._store.teams.replace_one(
                {"_id": str(candidate.team_id), "version": expected_version},
                _encode(candidate, str(candidate.team_id)),
            )
        except DuplicateKeyError:
            raise AdministrationConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.modified_count != 1:
            raise AdministrationConflictError
        return candidate.model_copy(deep=True)


class MongoProfileRepository:
    def __init__(self, store: MongoAdminStore) -> None:
        self._store = store

    def list(self) -> list[UserAccountRecord]:
        try:
            raw = list(self._store.profiles.find({}).sort([("user_id", ASCENDING)]))
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return [_decode(item, UserAccountRecord) for item in raw]

    def get(self, user_id: str) -> UserAccountRecord | None:
        try:
            raw = self._store.profiles.find_one({"_id": user_id.casefold()})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return _decode(raw, UserAccountRecord) if raw is not None else None

    def create(self, record: UserAccountRecord) -> UserAccountRecord:
        candidate = UserAccountRecord.model_validate(record)
        try:
            self._store.profiles.insert_one(_encode(candidate, candidate.user_id))
        except DuplicateKeyError:
            raise AdministrationConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return candidate.model_copy(deep=True)

    def update(self, record: UserAccountRecord, *, expected_version: int) -> UserAccountRecord:
        candidate = UserAccountRecord.model_validate(record)
        current = self.get(candidate.user_id)
        if current is None or not audit_is_prefix(current.audit_events, candidate.audit_events):
            raise AdministrationConflictError
        if (
            candidate.credential_hash.get_secret_value()
            != current.credential_hash.get_secret_value()
        ):
            raise AdministrationConflictError
        try:
            result = self._store.profiles.replace_one(
                {"_id": candidate.user_id, "version": expected_version},
                _encode(candidate, candidate.user_id),
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.modified_count != 1:
            raise AdministrationConflictError
        return candidate.model_copy(deep=True)

    def mutate_authority(
        self,
        *,
        actor_user_id: str,
        user_id: str,
        expected_version: int,
        display_name: str,
        role: Role,
        team_id: TeamId | None,
        updated_at: datetime,
    ) -> UserAccountRecord:
        """Provide the supported single-process last-HR atomicity boundary plus Mongo CAS."""

        with self._store.lock:
            current = self.get(user_id)
            if current is None or current.version != expected_version:
                raise AdministrationConflictError
            if actor_user_id == user_id and current.role == Role.HR and role != Role.HR:
                raise AdministrationAuthorityInvariantError
            if current.role == Role.HR and role != Role.HR:
                try:
                    hr_count = self._store.profiles.count_documents({"role": Role.HR.value})
                except PyMongoError:
                    raise PersistenceUnavailableError from None
                if hr_count <= 1:
                    raise AdministrationAuthorityInvariantError
            candidate = build_profile_authority_candidate(
                current,
                actor_user_id=actor_user_id,
                display_name=display_name,
                role=role,
                team_id=team_id,
                updated_at=updated_at,
            )
            try:
                result = self._store.profiles.replace_one(
                    {"_id": candidate.user_id, "version": expected_version},
                    _encode(candidate, candidate.user_id),
                )
            except PyMongoError:
                raise PersistenceUnavailableError from None
            if result.modified_count != 1:
                raise AdministrationConflictError
            return candidate.model_copy(deep=True)

    def replace_credential(
        self,
        *,
        actor_user_id: str,
        user_id: str,
        expected_version: int,
        credential_hash: SecretStr,
        operation: CredentialOperation,
        updated_at: datetime,
        expected_actor_security_version: int | None = None,
    ) -> UserAccountRecord:
        """D-140: reauthorize the actor, then version-CAS the credential-only replacement."""

        with self._store.lock:
            actor = self.get(actor_user_id)
            check_credential_replacement_actor(actor, operation, expected_actor_security_version)
            current = actor if user_id == actor_user_id else self.get(user_id)
            if current is None or current.version != expected_version:
                raise AdministrationConflictError
            candidate = build_credential_reset_candidate(
                current,
                actor_user_id=actor_user_id,
                credential_hash=credential_hash,
                operation=operation,
                updated_at=updated_at,
            )
            try:
                result = self._store.profiles.replace_one(
                    {
                        "_id": candidate.user_id,
                        "version": expected_version,
                        "security_version": current.security_version,
                    },
                    _encode(candidate, candidate.user_id),
                )
            except PyMongoError:
                raise PersistenceUnavailableError from None
            if result.modified_count != 1:
                raise AdministrationConflictError
            return candidate.model_copy(deep=True)


class MongoPolicyRepository:
    ID = "GLOBAL_POLICY_CATALOGUE"

    def __init__(self, store: MongoAdminStore) -> None:
        self._store = store

    def get(self) -> PolicyCatalogue | None:
        try:
            raw = self._store.policies.find_one({"_id": self.ID})
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return _decode(raw, PolicyCatalogue) if raw is not None else None

    def create(self, catalogue: PolicyCatalogue) -> PolicyCatalogue:
        candidate = PolicyCatalogue.model_validate(catalogue)
        try:
            self._store.policies.insert_one(_encode(candidate, self.ID))
        except DuplicateKeyError:
            raise AdministrationConflictError from None
        except PyMongoError:
            raise PersistenceUnavailableError from None
        return candidate.model_copy(deep=True)

    def update(self, catalogue: PolicyCatalogue, *, expected_version: int) -> PolicyCatalogue:
        candidate = PolicyCatalogue.model_validate(catalogue)
        current = self.get()
        if (
            current is None
            or current.version != expected_version
            or candidate.version != expected_version + 1
            or candidate.created_at != current.created_at
            or len(candidate.audit_events) != len(current.audit_events) + 1
            or candidate.audit_events[: len(current.audit_events)] != current.audit_events
        ):
            raise AdministrationConflictError
        try:
            result = self._store.policies.replace_one(
                {"_id": self.ID, "version": expected_version}, _encode(candidate, self.ID)
            )
        except PyMongoError:
            raise PersistenceUnavailableError from None
        if result.modified_count != 1:
            raise AdministrationConflictError
        return candidate.model_copy(deep=True)


def _encode(model: BaseModel, mongo_id: str) -> dict[str, Any]:
    raw = _value(model)
    if not isinstance(raw, dict):
        raise PersistenceDataInvalidError
    raw["_id"] = mongo_id
    return raw


def _decode(raw: dict[str, Any], model_type: type[BaseModel]) -> Any:
    mongo_id = raw.get("_id")
    if not isinstance(mongo_id, str):
        raise PersistenceDataInvalidError
    value = dict(raw)
    value.pop("_id", None)
    try:
        parsed = model_type.model_validate(value)
        _reject_unknown_model_fields(value, parsed)
    except (ValidationError, TypeError, ValueError):
        raise PersistenceDataInvalidError from None
    if isinstance(parsed, TeamRecord):
        expected_id = str(parsed.team_id)
    elif isinstance(parsed, UserAccountRecord):
        expected_id = parsed.user_id
    elif isinstance(parsed, PolicyCatalogue):
        expected_id = parsed.catalogue_id
    else:
        raise PersistenceDataInvalidError
    if expected_id != mongo_id:
        raise PersistenceDataInvalidError
    return parsed


def _value(value: object) -> Any:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, BaseModel):
        return {name: _value(getattr(value, name)) for name in type(value).model_fields}
    if isinstance(value, dict):
        return {str(key): _value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return value
