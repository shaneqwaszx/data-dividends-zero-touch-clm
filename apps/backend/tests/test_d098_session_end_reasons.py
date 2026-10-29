"""D-098: a 401 for a presented session says why it ended, as a closed code only.

Session lifetime, one session per user and the 401 body are unchanged; the reason is a header
with no identity, token or session detail, and a request with no session gets no reason.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import pytest
from phase13_test_clients import RawTestClient
from phase13_test_credentials import build_test_authentication_service
from phase13_test_settings import ordinary_test_settings

from app.api_auth import SESSION_END_REASON_HEADER
from app.domain.access import SYNTHETIC_USER_PROFILES
from app.main import create_app
from app.services.authentication import (
    MAX_ENDED_SESSIONS,
    SESSION_TTL,
    AuthenticationError,
    generate_scrypt_password_hash,
)

EXPECTED_BODY = {
    "detail": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "A valid authenticated session is required.",
    }
}


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 28, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def credentials() -> tuple[str, dict[str, str]]:
    credential = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(credential)
    return credential, {profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES}


def _reason(service: object, token: str) -> str:
    with pytest.raises(AuthenticationError) as raised:
        service.authenticate_session(token)  # type: ignore[attr-defined]
    return raised.value.reason


def test_service_names_why_each_session_ended(credentials: tuple[str, dict[str, str]]) -> None:
    password, hashes = credentials
    clock = MutableClock()
    service = build_test_authentication_service(hashes, clock=clock)
    user = SYNTHETIC_USER_PROFILES[0].user_id
    other = SYNTHETIC_USER_PROFILES[1].user_id

    replaced = service.login(user, password).token
    current = service.login(user, password).token  # the same account signs in elsewhere
    assert _reason(service, replaced) == "SESSION_REPLACED"

    service.login(other, password)  # another account never ends this one
    assert service.authenticate_session(current).actor.profile.user_id == user

    service.logout(current)
    assert _reason(service, current) == "SIGNED_OUT"

    revoked = service.login(user, password).token
    service.revoke_user_sessions(user)
    assert _reason(service, revoked) == "SESSION_REVOKED"

    expired = service.login(user, password).token
    clock.now += SESSION_TTL  # the absolute limit is unchanged and never extended
    assert _reason(service, expired) == "SESSION_EXPIRED"

    # A restarted backend (a new service, no shared memory) does not know the token.
    restarted = build_test_authentication_service(hashes, clock=clock)
    assert _reason(restarted, service.login(user, password).token) == "SESSION_UNKNOWN"
    assert _reason(restarted, secrets.token_urlsafe(32)) == "SESSION_UNKNOWN"


def test_ended_sessions_are_remembered_bounded_and_for_one_ttl_only(
    credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = credentials
    clock = MutableClock()
    service = build_test_authentication_service(hashes, clock=clock)
    user = SYNTHETIC_USER_PROFILES[0].user_id

    first = service.login(user, password).token
    for _ in range(MAX_ENDED_SESSIONS + 1):
        service.login(user, password)
    assert _reason(service, first) == "SESSION_UNKNOWN"  # pushed out of the bounded memory
    assert len(service._ended) == MAX_ENDED_SESSIONS  # noqa: SLF001

    recent = service.login(user, password).token
    service.login(user, password)
    clock.now += SESSION_TTL + timedelta(seconds=1)
    assert _reason(service, recent) == "SESSION_UNKNOWN"


def test_http_401_carries_only_a_closed_reason_header(
    credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = credentials
    service = build_test_authentication_service(hashes)
    first = RawTestClient(
        create_app(
            ordinary_test_settings(demo_controls_enabled=True), authentication_service=service
        )
    )
    second = RawTestClient(first.app)

    missing = first.get("/api/auth/me")
    assert missing.status_code == 401
    assert missing.json() == EXPECTED_BODY
    assert SESSION_END_REASON_HEADER not in missing.headers  # nothing ended: no reason

    first.post("/api/auth/login", json={"user_id": "maya-lim", "password": password})
    second.post("/api/auth/login", json={"user_id": "maya-lim", "password": password})
    replaced = first.get("/api/auth/me")
    assert replaced.status_code == 401
    assert replaced.json() == EXPECTED_BODY  # the body is unchanged
    assert replaced.headers[SESSION_END_REASON_HEADER] == "SESSION_REPLACED"
    assert "maya-lim" not in str(replaced.headers)
    assert second.get("/api/auth/me").status_code == 200

    stranger = RawTestClient(first.app)
    stranger.cookies.set("clm_session", secrets.token_urlsafe(32), path="/api")
    unknown = stranger.get("/api/system/execution-profile")
    assert unknown.headers[SESSION_END_REASON_HEADER] == "SESSION_UNKNOWN"
