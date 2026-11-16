"""D-140: HR resets a non-HR account password; sessions are revoked and audit is secret-free."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import UTC, datetime
from typing import Any

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import TEST_PASSWORD
from phase13_test_settings import ordinary_test_settings
from pydantic import SecretStr

from app.domain.access import AuthenticatedActor, Role, UserProfile
from app.domain.administration import (
    AdministrationAuditEvent,
    UserAccountRecord,
    sign_in_disabled,
)
from app.main import create_app
from app.persistence.mongo_admin_store import MongoProfileRepository, _encode
from app.services.admin_repository import (
    AdministrationActorNotAuthorizedError,
    AdministrationConflictError,
    AdministrationCredentialTargetRefusedError,
    InMemoryProfileRepository,
    InMemoryTeamRepository,
    bootstrap_administration,
    new_event_id,
)
from app.services.administration import (
    AdministrationForbiddenError,
    AdministrationNotFoundError,
    AdministrationService,
    AdministrationValidationError,
)
from app.services.authentication import (
    generate_scrypt_password_hash,
    parse_scrypt_password_hash,
)
from app.services.login_admission import SOURCE_BURST, LoginAdmission

SELF_CHANGE_PATH = "/api/admin/me/password"
RESET_PATH = "/api/admin/profiles/{user_id}/password"
SEEDED = (
    "maya-lim",
    "ethan-tan",
    "sophia-ng",
    "ryan-lee",
    "olivia-koh",
    "hr-admin",
    "support-user",
)


def _login(client: RawTestClient, user_id: str, password: str = TEST_PASSWORD) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": password})
    assert response.status_code == 200, response.status_code
    return str(response.json()["csrf_token"])


def _login_status(client: RawTestClient, user_id: str, password: str) -> int:
    return client.post(
        "/api/auth/login", json={"user_id": user_id, "password": password}
    ).status_code


def _version(client: RawTestClient, user_id: str) -> int:
    profiles = client.get("/api/admin/profiles").json()
    return int(next(item["version"] for item in profiles if item["user_id"] == user_id))


def _hr_actor(user_id: str = "hr-admin") -> AuthenticatedActor:
    return AuthenticatedActor(
        profile=UserProfile(user_id=user_id, display_name="HR Actor", role=Role.HR, team_id=None)
    )


def _repositories() -> tuple[InMemoryTeamRepository, InMemoryProfileRepository]:
    teams = InMemoryTeamRepository()
    profiles = InMemoryProfileRepository()
    encoded = SecretStr(generate_scrypt_password_hash(TEST_PASSWORD))
    bootstrap_administration(teams, profiles, {user_id: encoded for user_id in SEEDED})
    return teams, profiles


def test_hr_changes_own_password_and_must_sign_in_again(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    new_password = secrets.token_urlsafe(24)
    body = {"current_password": TEST_PASSWORD, "new_password": new_password}
    assert client.post(SELF_CHANGE_PATH, json=body).status_code == 403
    response = client.post(SELF_CHANGE_PATH, headers={"X-CSRF-Token": csrf}, json=body)
    assert response.status_code == 204
    assert not response.content
    assert client.get("/api/auth/me").status_code == 401
    assert _login_status(client, "hr-admin", TEST_PASSWORD) == 401
    assert _login_status(client, "hr-admin", new_password) == 200
    assert new_password not in caplog.text


def test_self_change_refuses_bad_proof_without_signing_out_or_echoing_input() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    headers = {"X-CSRF-Token": csrf}
    wrong = secrets.token_urlsafe(24)
    replacement = secrets.token_urlsafe(24)
    body = {"current_password": wrong, "new_password": replacement}
    failure = client.post(SELF_CHANGE_PATH, headers=headers, json=body)
    assert failure.status_code == 400
    assert failure.json() == {"detail": {
        "code": "CREDENTIAL_VERIFICATION_FAILED",
        "message": "The password change could not be verified.",
    }}
    invalid = client.post(SELF_CHANGE_PATH, headers=headers, json={**body, "user_id": "other"})
    assert invalid.status_code == 422
    assert wrong not in invalid.text and replacement not in invalid.text
    assert client.get("/api/auth/me").status_code == 200
    assert _login_status(client, "hr-admin", TEST_PASSWORD) == 200


def test_self_change_reuses_login_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.main.LoginAdmission", lambda: LoginAdmission(lambda: 0))
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    headers = {"X-CSRF-Token": csrf}
    body = {
        "current_password": secrets.token_urlsafe(24),
        "new_password": secrets.token_urlsafe(24),
    }
    for _ in range(SOURCE_BURST):
        assert client.post(SELF_CHANGE_PATH, headers=headers, json=body).status_code == 400
    limited = client.post(SELF_CHANGE_PATH, headers=headers, json=body)
    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "LOGIN_RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) > 0
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize("actor_id", ["maya-lim", "ethan-tan", "olivia-koh", "support-user"])
def test_self_change_requires_hr(actor_id: str) -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, actor_id)
    response = client.post(
        SELF_CHANGE_PATH,
        headers={"X-CSRF-Token": csrf},
        json={"current_password": TEST_PASSWORD, "new_password": secrets.token_urlsafe(24)},
    )
    assert response.status_code == 403


def test_hr_resets_password_revokes_old_session_and_new_password_logs_in(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    target = RawTestClient(create_app(ordinary_test_settings()))
    _login(target, "ethan-tan")
    assert target.get("/api/auth/me").status_code == 200

    hr = RawTestClient(target.app)
    csrf = _login(hr, "hr-admin")
    before = _version(hr, "ethan-tan")
    new_password = secrets.token_urlsafe(24)

    response = hr.post(
        RESET_PATH.format(user_id="ethan-tan"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": before, "new_password": new_password},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "ethan-tan"
    assert body["version"] == before + 1
    assert body["updated_by"] == "hr-admin"
    assert body["role"] == "RELATIONSHIP_MANAGER" and body["team_id"] == "TEAM_A"
    assert new_password not in response.text
    assert "credential" not in response.text and "password" not in response.text
    # The pre-reset session is revoked; only the new password authenticates.
    assert target.get("/api/auth/me").status_code == 401
    fresh = RawTestClient(target.app)
    assert _login_status(fresh, "ethan-tan", TEST_PASSWORD) == 401
    assert _login_status(fresh, "ethan-tan", new_password) == 200
    assert fresh.get("/api/auth/me").json()["profile"]["team_id"] == "TEAM_A"
    # The HR session itself is unaffected, and HR still has no case or dashboard access.
    assert hr.get("/api/auth/me").status_code == 200
    assert hr.get("/api/clm/zero-touch/cases").status_code == 403
    assert hr.get("/api/clm/zero-touch/dashboard").status_code == 403
    assert new_password not in caplog.text


@pytest.mark.parametrize("actor_id", ["maya-lim", "ethan-tan", "olivia-koh", "support-user"])
def test_non_hr_roles_are_forbidden_and_target_is_unchanged(actor_id: str) -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    hr = RawTestClient(client.app)
    _login(hr, "hr-admin")
    before = _version(hr, "sophia-ng")
    csrf = _login(client, actor_id)
    attempted = secrets.token_urlsafe(24)

    response = client.post(
        RESET_PATH.format(user_id="sophia-ng"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": before, "new_password": attempted},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ADMINISTRATION_FORBIDDEN"
    assert attempted not in response.text
    assert _version(hr, "sophia-ng") == before
    probe = RawTestClient(client.app)
    assert _login_status(probe, "sophia-ng", attempted) == 401
    assert _login_status(probe, "sophia-ng", TEST_PASSWORD) == 200


def test_unauthenticated_and_missing_csrf_are_refused() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    body = {"expected_version": 1, "new_password": secrets.token_urlsafe(24)}
    assert client.post(RESET_PATH.format(user_id="maya-lim"), json=body).status_code == 401
    _login(client, "hr-admin")
    assert client.post(RESET_PATH.format(user_id="maya-lim"), json=body).status_code == 403


def test_hr_targets_including_self_are_refused() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    created = client.post(
        "/api/admin/profiles",
        headers={"X-CSRF-Token": csrf},
        json={
            "user_id": "hr-second",
            "display_name": "Second HR",
            "role": "HR",
            "team_id": None,
            "password": TEST_PASSWORD,
        },
    )
    assert created.status_code == 201

    for target in ("hr-admin", "hr-second"):
        attempted = secrets.token_urlsafe(24)
        response = client.post(
            RESET_PATH.format(user_id=target),
            headers={"X-CSRF-Token": csrf},
            json={"expected_version": _version(client, target), "new_password": attempted},
        )
        assert response.status_code == 403, target
        assert response.json()["detail"]["code"] == "ADMINISTRATION_FORBIDDEN"
        probe = RawTestClient(client.app)
        assert _login_status(probe, target, attempted) == 401
        if target != "hr-admin":  # a fresh hr-admin login would replace the acting session
            assert _login_status(probe, target, TEST_PASSWORD) == 200
    assert client.get("/api/auth/me").status_code == 200


def test_stale_version_conflicts_and_keeps_the_old_credential() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    current = _version(client, "maya-lim")
    first = secrets.token_urlsafe(24)
    assert (
        client.post(
            RESET_PATH.format(user_id="maya-lim"),
            headers={"X-CSRF-Token": csrf},
            json={"expected_version": current, "new_password": first},
        ).status_code
        == 200
    )

    stale = secrets.token_urlsafe(24)
    response = client.post(
        RESET_PATH.format(user_id="maya-lim"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": current, "new_password": stale},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ADMINISTRATION_CONFLICT"
    probe = RawTestClient(client.app)
    assert _login_status(probe, "maya-lim", stale) == 401
    assert _login_status(probe, "maya-lim", first) == 200


@pytest.mark.parametrize(
    "body",
    [
        {"expected_version": 1, "new_password": "short-pass"},
        {"expected_version": 1, "new_password": "x" * 129},
        {"expected_version": "1", "new_password": "a-valid-length-password"},
        {"expected_version": 1},
        {"expected_version": 1, "new_password": "a-valid-length-password", "role": "HR"},
    ],
)
def test_invalid_bodies_are_rejected_without_echoing_input(body: dict[str, Any]) -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")

    response = client.post(
        RESET_PATH.format(user_id="maya-lim"), headers={"X-CSRF-Token": csrf}, json=body
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ADMINISTRATION_REQUEST_INVALID"
    if "new_password" in body:
        assert body["new_password"] not in response.text
    assert _login_status(RawTestClient(client.app), "maya-lim", TEST_PASSWORD) == 200


def test_unknown_target_is_not_found() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    response = client.post(
        RESET_PATH.format(user_id="no-such-user"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": 1, "new_password": secrets.token_urlsafe(24)},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ADMINISTRATION_RECORD_NOT_FOUND"


def test_audit_event_records_actor_target_versions_and_no_secret() -> None:
    teams, profiles = _repositories()
    revoked: list[str] = []
    service = AdministrationService(teams, profiles, revoke_sessions=revoked.append)
    before = profiles.get("ryan-lee")
    assert before is not None
    new_password = secrets.token_urlsafe(24)

    after = service.reset_password(
        _hr_actor(),
        "ryan-lee",
        expected_version=before.version,
        new_password=SecretStr(new_password),
    )

    assert revoked == ["ryan-lee"]
    assert after.version == before.version + 1
    assert after.security_version == before.security_version + 1
    assert (after.role, after.team_id, after.display_name) == (
        before.role,
        before.team_id,
        before.display_name,
    )
    assert after.created_at == before.created_at and after.created_by == before.created_by
    new_hash = after.credential_hash.get_secret_value()
    assert new_hash != before.credential_hash.get_secret_value()
    parse_scrypt_password_hash(new_hash)
    assert after.audit_events[:-1] == before.audit_events
    event = after.audit_events[-1]
    # Rollback-safe: an existing action tagged by operation, no new action or field.
    assert event.action == "PROFILE_UPDATED"
    assert event.actor_user_id == "hr-admin"
    assert event.target_id == "ryan-lee"
    assert event.resulting_version == after.version
    assert event.metadata == {
        "operation": "PASSWORD_RESET",
        "previous_version": before.version,
        "resulting_access_epoch": after.security_version,
    }
    serialized = event.model_dump_json()
    assert new_password not in serialized and new_hash not in serialized
    assert new_password not in repr(after) and new_hash not in repr(after)
    assert profiles.get("ryan-lee") == after


def test_service_rejects_bad_password_and_missing_target_before_hashing() -> None:
    teams, profiles = _repositories()
    service = AdministrationService(teams, profiles)
    current = profiles.get("maya-lim")
    assert current is not None
    for bad in ("x" * 11, "x" * 129):
        with pytest.raises(AdministrationValidationError):
            service.reset_password(
                _hr_actor(), "maya-lim", expected_version=1, new_password=SecretStr(bad)
            )
    with pytest.raises(AdministrationNotFoundError):
        service.reset_password(
            _hr_actor(), "absent-user", expected_version=1, new_password=SecretStr("x" * 12)
        )
    assert profiles.get("maya-lim") == current


def test_actor_is_reauthorized_inside_the_lock() -> None:
    teams, profiles = _repositories()
    service = AdministrationService(teams, profiles)
    service.create_profile(
        _hr_actor(),
        user_id="hr-second",
        display_name="Second HR",
        role=Role.HR,
        team_id=None,
        password=TEST_PASSWORD,
    )
    second = profiles.get("hr-second")
    assert second is not None
    # The second HR is demoted after their request was authenticated (stale actor object).
    profiles.mutate_authority(
        actor_user_id="hr-admin",
        user_id="hr-second",
        expected_version=second.version,
        display_name=second.display_name,
        role=Role.DIRECTOR,
        team_id=None,
        updated_at=datetime.now(UTC),
    )
    target = profiles.get("maya-lim")
    assert target is not None

    with pytest.raises(AdministrationForbiddenError):
        service.reset_password(
            _hr_actor("hr-second"),
            "maya-lim",
            expected_version=target.version,
            new_password=SecretStr(secrets.token_urlsafe(24)),
        )
    with pytest.raises(AdministrationActorNotAuthorizedError):
        profiles.replace_credential(
            actor_user_id="absent-actor",
            user_id="maya-lim",
            expected_version=target.version,
            credential_hash=SecretStr(generate_scrypt_password_hash("x" * 12)),
            operation="PASSWORD_RESET",
            updated_at=datetime.now(UTC),
        )
    assert profiles.get("maya-lim") == target


def test_repository_refuses_hr_target_even_when_called_directly() -> None:
    _, profiles = _repositories()
    current = profiles.get("hr-admin")
    assert current is not None
    with pytest.raises(AdministrationCredentialTargetRefusedError):
        profiles.replace_credential(
            actor_user_id="hr-admin",
            user_id="hr-admin",
            expected_version=current.version,
            credential_hash=SecretStr(generate_scrypt_password_hash("x" * 12)),
            operation="PASSWORD_RESET",
            updated_at=datetime.now(UTC),
        )
    assert profiles.get("hr-admin") == current


def test_existing_update_credential_guard_is_unchanged() -> None:
    _, profiles = _repositories()
    current = profiles.get("maya-lim")
    assert current is not None
    event = AdministrationAuditEvent(
        event_id=new_event_id(),
        action="PROFILE_UPDATED",
        actor_user_id="hr-admin",
        target_id="maya-lim",
        timestamp=datetime.now(UTC),
        resulting_version=current.version + 1,
    )
    candidate = current.model_copy(
        update={
            "credential_hash": SecretStr(generate_scrypt_password_hash("x" * 12)),
            "version": current.version + 1,
            "audit_events": (*current.audit_events, event),
        }
    )
    assert UserAccountRecord.model_validate(candidate) == candidate
    with pytest.raises(AdministrationConflictError):
        profiles.update(candidate, expected_version=current.version)
    # Only the credential change is refused: the same candidate with the old hash applies.
    unchanged = candidate.model_copy(update={"credential_hash": current.credential_hash})
    assert profiles.update(unchanged, expected_version=current.version).version == (
        current.version + 1
    )


class _FakeResult:
    def __init__(self, modified: int) -> None:
        self.modified_count = modified


class _FakeProfiles:
    """Minimal ``_id``/field-equality collection for MongoProfileRepository parity."""

    def __init__(self, records: list[UserAccountRecord]) -> None:
        self.documents = {record.user_id: _encode(record, record.user_id) for record in records}
        self.filters: list[dict[str, Any]] = []

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        document = self.documents.get(query["_id"])
        return dict(document) if document is not None else None

    def replace_one(self, query: dict[str, Any], document: dict[str, Any]) -> _FakeResult:
        self.filters.append(dict(query))
        current = self.documents.get(query["_id"])
        if current is None or any(current.get(key) != value for key, value in query.items()):
            return _FakeResult(0)
        self.documents[query["_id"]] = dict(document)
        return _FakeResult(1)


class _FakeStore:
    def __init__(self, profiles: _FakeProfiles) -> None:
        from threading import RLock

        self.profiles = profiles
        self.lock = RLock()


def test_self_change_memory_mongo_parity_and_secret_free_audit() -> None:
    teams, memory = _repositories()
    fake = _FakeProfiles(memory.list())
    mongo = MongoProfileRepository(_FakeStore(fake))  # type: ignore[arg-type]
    current = memory.get("hr-admin")
    assert current is not None
    new_password = secrets.token_urlsafe(24)
    for repository in (memory, mongo):
        service = AdministrationService(teams, repository)
        service.change_own_password(
            _hr_actor(),
            session_security_version=current.security_version,
            current_password=SecretStr(TEST_PASSWORD),
            new_password=SecretStr(new_password),
        )
        persisted = repository.get("hr-admin")
        assert persisted is not None
        assert persisted.version == current.version + 1
        assert persisted.security_version == current.security_version + 1
        event = persisted.audit_events[-1]
        assert event.action == "PROFILE_UPDATED"
        assert event.actor_user_id == event.target_id == "hr-admin"
        assert event.metadata == {
            "operation": "PASSWORD_CHANGED_SELF",
            "previous_version": current.version,
            "resulting_access_epoch": current.security_version + 1,
        }
        assert new_password not in event.model_dump_json()
        assert TEST_PASSWORD not in event.model_dump_json()
        assert persisted.credential_hash.get_secret_value() not in event.model_dump_json()
        with pytest.raises(AdministrationActorNotAuthorizedError):
            repository.replace_credential(
                actor_user_id="hr-admin",
                user_id="hr-admin",
                expected_version=persisted.version,
                credential_hash=current.credential_hash,
                operation="PASSWORD_CHANGED_SELF",
                updated_at=datetime.now(UTC),
                expected_actor_security_version=current.security_version,
            )
    assert fake.filters == [{
        "_id": "hr-admin",
        "version": current.version,
        "security_version": current.security_version,
    }]


def test_mongo_store_parity_with_memory_store() -> None:
    _, memory = _repositories()
    fake = _FakeProfiles(memory.list())
    mongo = MongoProfileRepository(_FakeStore(fake))  # type: ignore[arg-type]
    current = memory.get("olivia-koh")
    assert current is not None
    hashed = SecretStr(generate_scrypt_password_hash(secrets.token_urlsafe(24)))
    now = datetime.now(UTC)

    results = [
        repository.replace_credential(
            actor_user_id="hr-admin",
            user_id="olivia-koh",
            expected_version=current.version,
            credential_hash=hashed,
            operation="PASSWORD_RESET",
            updated_at=now,
        )
        for repository in (memory, mongo)
    ]

    memory_result, mongo_result = results
    assert mongo_result.model_dump(exclude={"audit_events"}) == memory_result.model_dump(
        exclude={"audit_events"}
    )
    assert [event.action for event in mongo_result.audit_events] == [
        event.action for event in memory_result.audit_events
    ]
    assert mongo.get("olivia-koh") == mongo_result
    assert fake.filters[-1] == {
        "_id": "olivia-koh",
        "version": current.version,
        "security_version": current.security_version,
    }
    for repository in (memory, mongo):
        with pytest.raises(AdministrationConflictError):
            repository.replace_credential(
                actor_user_id="hr-admin",
                user_id="olivia-koh",
                expected_version=current.version,
                credential_hash=hashed,
                operation="PASSWORD_RESET",
                updated_at=now,
            )
        with pytest.raises(AdministrationCredentialTargetRefusedError):
            hr = repository.get("hr-admin")
            assert hr is not None
            repository.replace_credential(
                actor_user_id="hr-admin",
                user_id="hr-admin",
                expected_version=hr.version,
                credential_hash=hashed,
                operation="PASSWORD_RESET",
                updated_at=now,
            )
        with pytest.raises(AdministrationActorNotAuthorizedError):
            repository.replace_credential(
                actor_user_id="maya-lim",
                user_id="olivia-koh",
                expected_version=current.version + 1,
                credential_hash=hashed,
                operation="PASSWORD_RESET",
                updated_at=now,
            )
    # A concurrent writer that moved the version between read and CAS is refused.
    racing = mongo.get("ethan-tan")
    assert racing is not None
    fake.documents["ethan-tan"]["version"] = racing.version + 7
    original_find = fake.find_one
    fake.find_one = lambda query: (  # type: ignore[method-assign]
        _encode(racing, racing.user_id) if query["_id"] == "ethan-tan" else original_find(query)
    )
    with pytest.raises(AdministrationConflictError):
        mongo.replace_credential(
            actor_user_id="hr-admin",
            user_id="ethan-tan",
            expected_version=racing.version,
            credential_hash=hashed,
            operation="PASSWORD_RESET",
            updated_at=now,
        )


@pytest.mark.skipif(
    not os.environ.get("PHASE12_MONGO_URI"), reason="PHASE12_MONGO_URI is not configured"
)
def test_physical_mongo_reset_revokes_session_persists_across_restart_and_audits() -> None:
    from pymongo import MongoClient
    from scripts.mongo_test_safety import (
        cleanup_ephemeral_mongo_database,
        generate_ephemeral_mongo_database,
    )

    from app.config import Settings

    uri = os.environ["PHASE12_MONGO_URI"]
    database = generate_ephemeral_mongo_database("p145")
    settings = Settings(
        _env_file=None,
        app_env="test",
        clm_persistence_mode="mongo",
        mongo_uri=uri,
        mongo_database=database,
    )
    cleanup: MongoClient[dict[str, Any]] = MongoClient(uri)
    new_password = secrets.token_urlsafe(24)
    new_hr_password = secrets.token_urlsafe(24)
    try:
        with RawTestClient(create_app(settings)) as first:
            target = RawTestClient(first.app)
            _login(target, "maya-lim")
            hr = RawTestClient(first.app)
            csrf = _login(hr, "hr-admin")
            before = _version(hr, "maya-lim")
            stale_body = {"expected_version": before, "new_password": new_password}
            reset = hr.post(
                RESET_PATH.format(user_id="maya-lim"),
                headers={"X-CSRF-Token": csrf},
                json=stale_body,
            )
            assert reset.status_code == 200 and reset.json()["version"] == before + 1
            assert target.get("/api/auth/me").status_code == 401
            assert (
                hr.post(
                    RESET_PATH.format(user_id="maya-lim"),
                    headers={"X-CSRF-Token": csrf},
                    json=stale_body,
                ).status_code
                == 409
            )
            assert (
                hr.post(
                    RESET_PATH.format(user_id="hr-admin"),
                    headers={"X-CSRF-Token": csrf},
                    json={
                        "expected_version": _version(hr, "hr-admin"),
                        "new_password": new_password,
                    },
                ).status_code
                == 403
            )

        with RawTestClient(create_app(settings)) as restarted:
            probe = RawTestClient(restarted.app)
            assert _login_status(probe, "maya-lim", TEST_PASSWORD) == 401
            assert _login_status(probe, "maya-lim", new_password) == 200

        raw = cleanup[database][settings.mongo_admin_profiles_collection].find_one(
            {"_id": "maya-lim"}
        )
        assert raw is not None
        assert raw["version"] == before + 1 and raw["security_version"] == 2
        event = raw["audit_events"][-1]
        assert event["action"] == "PROFILE_UPDATED"
        assert event["metadata"]["operation"] == "PASSWORD_RESET"
        assert "sign_in_disabled" not in raw
        assert event["actor_user_id"] == "hr-admin" and event["target_id"] == "maya-lim"
        assert new_password not in str(raw["audit_events"])
        assert raw["credential_hash"] not in str(raw["audit_events"])
        assert new_password not in str(raw)

        with RawTestClient(create_app(settings)) as second:
            target = RawTestClient(second.app)
            _login(target, "maya-lim", new_password)
            csrf = _login(second, "hr-admin")
            disabled = second.post(
                DISABLE_PATH.format(user_id="maya-lim"),
                headers={"X-CSRF-Token": csrf},
                json={"expected_version": before + 1},
            )
            assert disabled.status_code == 200 and disabled.json()["sign_in_disabled"] is True
            assert target.get("/api/auth/me").status_code == 401

        with RawTestClient(create_app(settings)) as restarted:
            assert _login_status(restarted, "maya-lim", new_password) == 401
            csrf = _login(restarted, "hr-admin")
            profiles = restarted.get("/api/admin/profiles").json()
            target_profile = next(
                profile for profile in profiles if profile["user_id"] == "maya-lim"
            )
            assert target_profile["sign_in_disabled"] is True
            changed = restarted.post(
                SELF_CHANGE_PATH,
                headers={"X-CSRF-Token": csrf},
                json={"current_password": TEST_PASSWORD, "new_password": new_hr_password},
            )
            assert changed.status_code == 204
            assert restarted.get("/api/auth/me").status_code == 401

        with RawTestClient(create_app(settings)) as restarted:
            assert _login_status(restarted, "hr-admin", TEST_PASSWORD) == 401
            assert _login_status(restarted, "hr-admin", new_hr_password) == 200

        hr = cleanup[database][settings.mongo_admin_profiles_collection].find_one(
            {"_id": "hr-admin"}
        )
        assert hr is not None
        assert hr["security_version"] == 2
        event = hr["audit_events"][-1]
        assert event["action"] == "PROFILE_UPDATED"
        assert event["metadata"]["operation"] == "PASSWORD_CHANGED_SELF"
        assert new_hr_password not in str(event)
        assert hr["credential_hash"] not in str(event)
    finally:
        try:
            cleanup_ephemeral_mongo_database(cleanup, database)
        finally:
            cleanup.close()


DISABLE_PATH = "/api/admin/profiles/{user_id}/disable"


def test_hr_disables_sign_in_revokes_session_and_reset_re_enables() -> None:
    target = RawTestClient(create_app(ordinary_test_settings()))
    _login(target, "sophia-ng")
    hr = RawTestClient(target.app)
    csrf = _login(hr, "hr-admin")
    before = _version(hr, "sophia-ng")

    disabled = hr.post(
        DISABLE_PATH.format(user_id="sophia-ng"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": before},
    )

    assert disabled.status_code == 200
    assert disabled.json()["sign_in_disabled"] is True
    assert disabled.json()["version"] == before + 1
    assert target.get("/api/auth/me").status_code == 401
    probe = RawTestClient(target.app)
    assert _login_status(probe, "sophia-ng", TEST_PASSWORD) == 401
    listed = next(
        item for item in hr.get("/api/admin/profiles").json() if item["user_id"] == "sophia-ng"
    )
    assert listed["sign_in_disabled"] is True
    assert "credential" not in disabled.text

    new_password = secrets.token_urlsafe(24)
    enabled = hr.post(
        RESET_PATH.format(user_id="sophia-ng"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": before + 1, "new_password": new_password},
    )
    assert enabled.status_code == 200 and enabled.json()["sign_in_disabled"] is False
    assert _login_status(probe, "sophia-ng", new_password) == 200
    # Later non-credential updates keep the derived state.
    renamed = hr.patch(
        "/api/admin/profiles/sophia-ng",
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": before + 2, "display_name": "Sophia Renamed"},
    )
    assert renamed.status_code == 200 and renamed.json()["sign_in_disabled"] is False


def test_disabled_state_survives_a_later_profile_update() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    current = _version(client, "ryan-lee")
    assert (
        client.post(
            DISABLE_PATH.format(user_id="ryan-lee"),
            headers={"X-CSRF-Token": csrf},
            json={"expected_version": current},
        ).status_code
        == 200
    )
    renamed = client.patch(
        "/api/admin/profiles/ryan-lee",
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": current + 1, "display_name": "Ryan Renamed"},
    )
    assert renamed.status_code == 200 and renamed.json()["sign_in_disabled"] is True
    assert _login_status(RawTestClient(client.app), "ryan-lee", TEST_PASSWORD) == 401


def test_disabled_account_must_be_reset_before_it_can_become_hr() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    headers = {"X-CSRF-Token": csrf}
    before = _version(client, "ryan-lee")
    assert (
        client.post(
            DISABLE_PATH.format(user_id="ryan-lee"),
            headers=headers,
            json={"expected_version": before},
        ).status_code
        == 200
    )
    profile_path = "/api/admin/profiles/ryan-lee"
    assert (
        client.patch(
            profile_path,
            headers=headers,
            json={"expected_version": before + 1, "role": "HR", "team_id": None},
        ).status_code
        == 422
    )
    assert _version(client, "ryan-lee") == before + 1
    assert (
        client.post(
            RESET_PATH.format(user_id="ryan-lee"),
            headers=headers,
            json={"expected_version": before + 1, "new_password": secrets.token_urlsafe(24)},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            profile_path,
            headers=headers,
            json={"expected_version": before + 2, "role": "HR", "team_id": None},
        ).status_code
        == 200
    )


@pytest.mark.parametrize("actor_id", ["maya-lim", "olivia-koh", "support-user"])
def test_disable_is_forbidden_for_non_hr(actor_id: str) -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, actor_id)
    response = client.post(
        DISABLE_PATH.format(user_id="ethan-tan"),
        headers={"X-CSRF-Token": csrf},
        json={"expected_version": 1},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ADMINISTRATION_FORBIDDEN"
    assert _login_status(RawTestClient(client.app), "ethan-tan", TEST_PASSWORD) == 200


def test_disable_refuses_hr_targets_stale_versions_and_bad_bodies() -> None:
    client = RawTestClient(create_app(ordinary_test_settings()))
    csrf = _login(client, "hr-admin")
    headers = {"X-CSRF-Token": csrf}
    hr_version = _version(client, "hr-admin")
    assert (
        client.post(
            DISABLE_PATH.format(user_id="hr-admin"),
            headers=headers,
            json={"expected_version": hr_version},
        ).status_code
        == 403
    )
    current = _version(client, "ryan-lee")
    assert (
        client.post(
            DISABLE_PATH.format(user_id="ryan-lee"),
            headers=headers,
            json={"expected_version": current + 1},
        ).status_code
        == 409
    )
    for body in ({}, {"expected_version": "1"}, {"expected_version": current, "x": 1}):
        assert (
            client.post(
                DISABLE_PATH.format(user_id="ryan-lee"), headers=headers, json=body
            ).status_code
            == 422
        )
    assert (
        client.post(
            DISABLE_PATH.format(user_id="absent-user"),
            headers=headers,
            json={"expected_version": 1},
        ).status_code
        == 404
    )
    assert _version(client, "ryan-lee") == current
    assert client.get("/api/auth/me").status_code == 200


def test_disable_audit_is_secret_free_and_credential_is_replaced() -> None:
    teams, profiles = _repositories()
    revoked: list[str] = []
    service = AdministrationService(teams, profiles, revoke_sessions=revoked.append)
    before = profiles.get("maya-lim")
    assert before is not None

    after = service.disable_sign_in(_hr_actor(), "maya-lim", expected_version=before.version)

    assert revoked == ["maya-lim"]
    assert after.security_version == before.security_version + 1
    new_hash = after.credential_hash.get_secret_value()
    assert new_hash != before.credential_hash.get_secret_value()
    parse_scrypt_password_hash(new_hash)
    event = after.audit_events[-1]
    assert event.action == "PROFILE_UPDATED"
    assert event.metadata["operation"] == "SIGN_IN_DISABLED"
    assert new_hash not in event.model_dump_json()
    assert sign_in_disabled(after) is True and sign_in_disabled(before) is False


def test_d140_records_decode_with_the_pre_d140_audit_schema() -> None:
    """Rollback safety: the pre-D-140 action set and fields are unchanged."""

    teams, profiles = _repositories()
    service = AdministrationService(teams, profiles)
    current = profiles.get("ethan-tan")
    assert current is not None
    after = service.reset_password(
        _hr_actor(),
        "ethan-tan",
        expected_version=current.version,
        new_password=SecretStr(secrets.token_urlsafe(24)),
    )
    after = service.disable_sign_in(_hr_actor(), "ethan-tan", expected_version=after.version)
    pre_d140_actions = {
        "TEAM_CREATED",
        "TEAM_UPDATED",
        "PROFILE_CREATED",
        "PROFILE_UPDATED",
        "PROFILE_AUTHORITY_UPDATED",
    }
    annotation = AdministrationAuditEvent.model_fields["action"].annotation
    assert set(getattr(annotation, "__args__", ())) == pre_d140_actions
    raw = _encode(after, after.user_id)
    assert set(raw) == set(UserAccountRecord.model_fields) | {"_id"}
    assert {event["action"] for event in raw["audit_events"]} <= pre_d140_actions
