"""POC-only scrypt credential verification and opaque server sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from pydantic import SecretStr

from app.domain.access import (
    SYNTHETIC_PROFILE_BY_ID,
    AuthenticatedActor,
)

SCRYPT_N = 16_384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_SALT_BYTES = 16
SCRYPT_MAXMEM = 64 * 1024 * 1024
SESSION_TTL = timedelta(hours=8)
SESSION_TOKEN_BYTES = 32
MAX_SESSION_TOKEN_LENGTH = 128
MAX_ACTIVE_SESSIONS = len(SYNTHETIC_PROFILE_BY_ID)


class AuthenticationError(Exception):
    """Fixed authentication failure with no credential or identity detail."""


class AuthenticationConfigurationError(Exception):
    """Fail-closed credential configuration error naming only its setting key."""

    def __init__(self, setting_key: str) -> None:
        super().__init__(f"Invalid or missing authentication setting: {setting_key}")
        self.setting_key = setting_key


class SessionCapacityError(Exception):
    """Bounded process-local session storage cannot accept another session."""


@dataclass(frozen=True)
class ScryptPasswordHash:
    salt: bytes
    digest: bytes


@dataclass(frozen=True)
class SessionRecord:
    digest: str
    actor: AuthenticatedActor
    issued_at: datetime
    expires_at: datetime
    csrf_token: str


@dataclass(frozen=True)
class IssuedSession:
    token: str
    record: SessionRecord


def generate_scrypt_password_hash(credential: str) -> str:
    """Generate a portable hash string without retaining or printing plaintext."""

    if not isinstance(credential, str) or not credential:
        raise ValueError("password must be a non-empty string")
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = _derive(credential, salt)
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}"
        f"${_encode(salt)}${_encode(digest)}"
    )


def parse_scrypt_password_hash(encoded: str) -> ScryptPasswordHash:
    """Accept only the fixed bounded Phase 13 scrypt encoding."""

    try:
        algorithm, n, r, p, salt_value, digest_value = encoded.split("$")
        if (
            algorithm != "scrypt"
            or int(n) != SCRYPT_N
            or int(r) != SCRYPT_R
            or int(p) != SCRYPT_P
        ):
            raise ValueError
        salt = _decode(salt_value)
        digest = _decode(digest_value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid scrypt password hash") from None
    if len(salt) != SCRYPT_SALT_BYTES or len(digest) != SCRYPT_DKLEN:
        raise ValueError("invalid scrypt password hash")
    return ScryptPasswordHash(salt=salt, digest=digest)


class AuthenticationService:
    """Authenticate the fixed POC profiles and own bounded process-local sessions."""

    def __init__(
        self,
        credential_hashes: Mapping[str, SecretStr | str | None],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._credentials: dict[str, ScryptPasswordHash] = {}
        for user_id in SYNTHETIC_PROFILE_BY_ID:
            setting_key = credential_setting_key(user_id)
            secret = credential_hashes.get(user_id)
            if secret is None:
                raise AuthenticationConfigurationError(setting_key)
            encoded = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
            try:
                self._credentials[user_id] = parse_scrypt_password_hash(encoded)
            except ValueError:
                raise AuthenticationConfigurationError(setting_key) from None
        self._dummy = parse_scrypt_password_hash(
            generate_scrypt_password_hash(secrets.token_urlsafe(32))
        )
        self._sessions: dict[str, SessionRecord] = {}
        self._session_by_user: dict[str, str] = {}
        self._session_lock = RLock()

    def login(self, user_id: str, credential: str) -> IssuedSession:
        now = _as_utc(self._clock())
        profile = SYNTHETIC_PROFILE_BY_ID.get(user_id)
        password_hash = self._credentials.get(user_id, self._dummy)
        candidate = _derive(credential, password_hash.salt)
        if profile is None or not hmac.compare_digest(candidate, password_hash.digest):
            raise AuthenticationError

        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        digest = _session_digest(token)
        record = SessionRecord(
            digest=digest,
            actor=AuthenticatedActor(profile=profile),
            issued_at=now,
            expires_at=now + SESSION_TTL,
            csrf_token=secrets.token_urlsafe(SESSION_TOKEN_BYTES),
        )
        with self._session_lock:
            self._purge_expired(now)
            previous_digest = self._session_by_user.pop(profile.user_id, None)
            if previous_digest is not None:
                self._sessions.pop(previous_digest, None)
            if len(self._sessions) >= MAX_ACTIVE_SESSIONS:
                raise SessionCapacityError
            self._sessions[digest] = record
            self._session_by_user[profile.user_id] = digest
        return IssuedSession(token=token, record=record)

    def authenticate_session(self, token: str | None) -> SessionRecord:
        now = _as_utc(self._clock())
        if (
            not isinstance(token, str)
            or not token
            or len(token) > MAX_SESSION_TOKEN_LENGTH
            or any(character.isspace() for character in token)
        ):
            raise AuthenticationError
        with self._session_lock:
            self._purge_expired(now)
            record = self._sessions.get(_session_digest(token))
            if record is None or record.expires_at <= now:
                raise AuthenticationError
            return record

    def verify_csrf(self, record: SessionRecord, token: str | None) -> bool:
        return isinstance(token, str) and hmac.compare_digest(record.csrf_token, token)

    def logout(self, token: str | None) -> None:
        with self._session_lock:
            record = self.authenticate_session(token)
            self._sessions.pop(record.digest, None)
            current = self._session_by_user.get(record.actor.profile.user_id)
            if current == record.digest:
                self._session_by_user.pop(record.actor.profile.user_id, None)

    def active_session_count(self) -> int:
        with self._session_lock:
            self._purge_expired(_as_utc(self._clock()))
            return len(self._sessions)

    def _purge_expired(self, now: datetime) -> None:
        expired = [
            digest for digest, record in self._sessions.items() if record.expires_at <= now
        ]
        for digest in expired:
            record = self._sessions.pop(digest)
            if self._session_by_user.get(record.actor.profile.user_id) == digest:
                self._session_by_user.pop(record.actor.profile.user_id, None)


def credential_setting_key(user_id: str) -> str:
    return f"PHASE13_{user_id.replace('-', '_').upper()}_PASSWORD_HASH"


def _derive(credential: str, salt: bytes) -> bytes:
    if not isinstance(credential, str):
        credential = ""
    return hashlib.scrypt(
        credential.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
        maxmem=SCRYPT_MAXMEM,
    )


def _session_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    if not value or len(value) > 128:
        raise ValueError
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding, altchars=b"-_", validate=True)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("authentication clock must return a timezone-aware value")
    return value.astimezone(UTC)
