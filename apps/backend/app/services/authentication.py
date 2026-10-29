"""POC-only scrypt credential verification and opaque server sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from app.domain.access import AuthenticatedActor, UserProfile
from app.services.admin_repository import ProfileRepository, TeamRepository

SCRYPT_N = 16_384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_SALT_BYTES = 16
SCRYPT_MAXMEM = 64 * 1024 * 1024
SESSION_TTL = timedelta(hours=8)
SESSION_TOKEN_BYTES = 32
MAX_SESSION_TOKEN_LENGTH = 128


class AuthenticationError(Exception):
    """Fixed authentication failure with no credential or identity detail.

    ``reason`` (D-098) says only why a presented session no longer works, as a closed code:
    it never names the user, the token or the other session."""

    def __init__(self, reason: str = "SESSION_UNKNOWN") -> None:
        super().__init__()  # the exception itself stays detail-free
        self.reason = reason


# D-098: why a session token stopped working. A token this process never issued (for example
# after a backend restart, since sessions live in process memory) reads as SESSION_UNKNOWN.
SESSION_END_REASONS = (
    "SESSION_EXPIRED",
    "SESSION_REPLACED",
    "SESSION_REVOKED",
    "SIGNED_OUT",
    "SESSION_UNKNOWN",
)
# How many ended sessions are remembered (by digest only), and for how long.
MAX_ENDED_SESSIONS = 1024


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
    user_id: str
    security_version: int
    issued_at: datetime
    expires_at: datetime
    csrf_token: str


@dataclass(frozen=True)
class AuthenticatedSession:
    record: SessionRecord
    actor: AuthenticatedActor

    @property
    def digest(self) -> str:
        return self.record.digest

    @property
    def user_id(self) -> str:
        return self.record.user_id

    @property
    def security_version(self) -> int:
        return self.record.security_version

    @property
    def issued_at(self) -> datetime:
        return self.record.issued_at

    @property
    def expires_at(self) -> datetime:
        return self.record.expires_at

    @property
    def csrf_token(self) -> str:
        return self.record.csrf_token


@dataclass(frozen=True)
class IssuedSession:
    token: str
    record: AuthenticatedSession


def generate_scrypt_password_hash(credential: str) -> str:
    """Generate a portable hash string without retaining or printing plaintext."""

    if not isinstance(credential, str) or not credential:
        raise ValueError("password must be a non-empty string")
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = _derive(credential, salt)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_encode(salt)}${_encode(digest)}"


def parse_scrypt_password_hash(encoded: str) -> ScryptPasswordHash:
    """Accept only the fixed bounded Phase 13 scrypt encoding."""

    try:
        algorithm, n, r, p, salt_value, digest_value = encoded.split("$")
        if algorithm != "scrypt" or int(n) != SCRYPT_N or int(r) != SCRYPT_R or int(p) != SCRYPT_P:
            raise ValueError
        salt = _decode(salt_value)
        digest = _decode(digest_value)
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid scrypt password hash") from None
    if len(salt) != SCRYPT_SALT_BYTES or len(digest) != SCRYPT_DKLEN:
        raise ValueError("invalid scrypt password hash")
    return ScryptPasswordHash(salt=salt, digest=digest)


class AuthenticationService:
    """Authenticate repository accounts and own bounded process-local sessions."""

    def __init__(
        self,
        profiles: ProfileRepository,
        teams: TeamRepository,
        *,
        max_active_sessions: int = 256,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not 1 <= max_active_sessions <= 1000:
            raise ValueError("active session capacity must be between 1 and 1000")
        self._clock = clock or (lambda: datetime.now(UTC))
        self._profiles = profiles
        self._teams = teams
        self._max_active_sessions = max_active_sessions
        self._dummy = parse_scrypt_password_hash(
            generate_scrypt_password_hash(secrets.token_urlsafe(32))
        )
        self._sessions: dict[str, SessionRecord] = {}
        self._session_by_user: dict[str, str] = {}
        # Digest -> (reason, when it ended); bounded, oldest first, nothing else kept.
        self._ended: OrderedDict[str, tuple[str, datetime]] = OrderedDict()
        self._session_lock = RLock()

    def login(self, user_id: str, credential: str) -> IssuedSession:
        now = _as_utc(self._clock())
        account = self._profiles.get(user_id) if isinstance(user_id, str) else None
        password_hash = self._dummy
        if account is not None and account.user_id == user_id:
            try:
                password_hash = parse_scrypt_password_hash(
                    account.credential_hash.get_secret_value()
                )
            except ValueError:
                raise AuthenticationError from None
        candidate = _derive(credential, password_hash.salt)
        if (
            account is None
            or account.user_id != user_id
            or not hmac.compare_digest(candidate, password_hash.digest)
        ):
            raise AuthenticationError

        actor = self._actor_for_account(account)

        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        digest = _session_digest(token)
        record = SessionRecord(
            digest=digest,
            user_id=account.user_id,
            security_version=account.security_version,
            issued_at=now,
            expires_at=now + SESSION_TTL,
            csrf_token=secrets.token_urlsafe(SESSION_TOKEN_BYTES),
        )
        with self._session_lock:
            self._purge_expired(now)
            previous_digest = self._session_by_user.pop(account.user_id, None)
            if (
                previous_digest is not None
                and self._sessions.pop(previous_digest, None) is not None
            ):
                self._remember_end(previous_digest, "SESSION_REPLACED", now)
            if len(self._sessions) >= self._max_active_sessions:
                raise SessionCapacityError
            self._sessions[digest] = record
            self._session_by_user[account.user_id] = digest
        return IssuedSession(token=token, record=AuthenticatedSession(record=record, actor=actor))

    def authenticate_session(self, token: str | None) -> AuthenticatedSession:
        now = _as_utc(self._clock())
        if (
            not isinstance(token, str)
            or not token
            or len(token) > MAX_SESSION_TOKEN_LENGTH
            or any(character.isspace() for character in token)
        ):
            # No usable token was presented: nothing ended, so no end reason is given.
            raise AuthenticationError("NO_SESSION")
        with self._session_lock:
            self._purge_expired(now)
            digest = _session_digest(token)
            record = self._sessions.get(digest)
            if record is None or record.expires_at <= now:
                raise AuthenticationError(self._end_reason(digest, now))
            account = self._profiles.get(record.user_id)
            if account is None or account.security_version != record.security_version:
                self._remove_session(record, "SESSION_REVOKED", now)
                raise AuthenticationError("SESSION_REVOKED")
            try:
                actor = self._actor_for_account(account)
            except AuthenticationError:
                self._remove_session(record, "SESSION_REVOKED", now)
                raise AuthenticationError("SESSION_REVOKED") from None
            return AuthenticatedSession(record=record, actor=actor)

    def verify_csrf(self, record: AuthenticatedSession, token: str | None) -> bool:
        return isinstance(token, str) and hmac.compare_digest(record.csrf_token, token)

    def logout(self, token: str | None) -> None:
        with self._session_lock:
            record = self.authenticate_session(token)
            self._sessions.pop(record.digest, None)
            self._remember_end(record.digest, "SIGNED_OUT", _as_utc(self._clock()))
            current = self._session_by_user.get(record.user_id)
            if current == record.digest:
                self._session_by_user.pop(record.user_id, None)

    def revoke_user_sessions(self, user_id: str) -> None:
        with self._session_lock:
            digest = self._session_by_user.pop(user_id, None)
            if digest is not None and self._sessions.pop(digest, None) is not None:
                self._remember_end(digest, "SESSION_REVOKED", _as_utc(self._clock()))

    def active_session_count(self) -> int:
        with self._session_lock:
            self._purge_expired(_as_utc(self._clock()))
            return len(self._sessions)

    def _purge_expired(self, now: datetime) -> None:
        expired = [digest for digest, record in self._sessions.items() if record.expires_at <= now]
        for digest in expired:
            record = self._sessions.pop(digest)
            self._remember_end(digest, "SESSION_EXPIRED", now)
            if self._session_by_user.get(record.user_id) == digest:
                self._session_by_user.pop(record.user_id, None)

    def _remove_session(self, record: SessionRecord, reason: str, now: datetime) -> None:
        self._sessions.pop(record.digest, None)
        self._remember_end(record.digest, reason, now)
        if self._session_by_user.get(record.user_id) == record.digest:
            self._session_by_user.pop(record.user_id, None)

    def _remember_end(self, digest: str, reason: str, now: datetime) -> None:
        """Keep why a session ended (digest only), bounded in count and in time."""

        self._ended.pop(digest, None)
        self._ended[digest] = (reason, now)
        while len(self._ended) > MAX_ENDED_SESSIONS:
            self._ended.popitem(last=False)

    def _end_reason(self, digest: str, now: datetime) -> str:
        ended = self._ended.get(digest)
        if ended is None or now - ended[1] > SESSION_TTL:
            return "SESSION_UNKNOWN"
        return ended[0]

    def _actor_for_account(self, account: object) -> AuthenticatedActor:
        from app.domain.administration import UserAccountRecord

        current = UserAccountRecord.model_validate(account)
        if current.team_id is not None:
            team = self._teams.get(current.team_id)
            if team is None or not team.active:
                raise AuthenticationError
        return AuthenticatedActor(
            profile=UserProfile(
                user_id=current.user_id,
                display_name=current.display_name,
                role=current.role,
                team_id=current.team_id,
            )
        )


def credential_setting_key(user_id: str) -> str:
    if user_id == "hr-admin":
        return "PHASE14_5_HR_ADMIN_PASSWORD_HASH"
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
