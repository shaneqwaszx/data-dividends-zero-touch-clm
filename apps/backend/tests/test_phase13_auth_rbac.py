from __future__ import annotations

import secrets
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from phase13_test_clients import RawTestClient
from starlette.routing import BaseRoute

import app.services.authentication as authentication_module
from app.config import Settings
from app.domain.access import (
    SYNTHETIC_USER_PROFILES,
    Role,
    TeamId,
)
from app.main import create_app
from app.services.authentication import (
    SESSION_TTL,
    AuthenticationConfigurationError,
    AuthenticationError,
    AuthenticationService,
    generate_scrypt_password_hash,
    parse_scrypt_password_hash,
)
from app.services.authorization import ROUTE_POLICIES, RouteAccess, route_inventory


def _collect_application_route_inventory(
    application: FastAPI,
) -> set[tuple[str, str]]:
    """Flatten current FastAPI routes, including deferred included-router nodes."""

    pending: list[BaseRoute] = list(application.routes)
    visited: set[int] = set()
    actual: set[tuple[str, str]] = set()
    while pending:
        route = pending.pop()
        if id(route) in visited:
            continue
        visited.add(id(route))
        if isinstance(route, APIRoute):
            if route.path == "/health" or route.path.startswith("/api"):
                actual.update((method, route.path) for method in route.methods)
            continue
        nested_routes = getattr(route, "routes", None)
        if isinstance(nested_routes, Iterable):
            pending.extend(nested_routes)
        original_router = getattr(route, "original_router", None)
        original_routes = getattr(original_router, "routes", None)
        if isinstance(original_routes, Iterable):
            pending.extend(original_routes)
    return actual


class MutableClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 7, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def runtime_credentials() -> tuple[str, dict[str, str]]:
    credential = secrets.token_urlsafe(24)
    return credential, {
        profile.user_id: generate_scrypt_password_hash(credential)
        for profile in SYNTHETIC_USER_PROFILES
    }


def test_exact_five_profiles_are_typed_and_team_scoped() -> None:
    assert [profile.user_id for profile in SYNTHETIC_USER_PROFILES] == [
        "team-a-onboarder",
        "team-a-rm",
        "team-b-onboarder",
        "team-b-rm",
        "director",
    ]
    assert [profile.team_id for profile in SYNTHETIC_USER_PROFILES] == [
        TeamId.TEAM_A,
        TeamId.TEAM_A,
        TeamId.TEAM_B,
        TeamId.TEAM_B,
        None,
    ]
    assert [profile.role for profile in SYNTHETIC_USER_PROFILES] == [
        Role.CLIENT_ONBOARDER,
        Role.RELATIONSHIP_MANAGER,
        Role.CLIENT_ONBOARDER,
        Role.RELATIONSHIP_MANAGER,
        Role.DIRECTOR,
    ]
    assert [profile.client_scope_label for profile in SYNTHETIC_USER_PROFILES] == [
        "DBS",
        "DBS",
        "OCBC",
        "OCBC",
        "All demo scopes",
    ]


def test_scrypt_hash_round_trip_uses_random_salt() -> None:
    credential = secrets.token_urlsafe(24)
    first = generate_scrypt_password_hash(credential)
    second = generate_scrypt_password_hash(credential)

    assert first != second
    assert parse_scrypt_password_hash(first).digest != parse_scrypt_password_hash(second).digest


def test_every_profile_can_login_with_runtime_credentials(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    service = AuthenticationService(hashes)

    for profile in SYNTHETIC_USER_PROFILES:
        issued = service.login(profile.user_id, password)
        assert service.authenticate_session(issued.token).actor.profile == profile

    assert service.active_session_count() == 5


def test_bad_password_and_unknown_user_use_same_failure(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    service = AuthenticationService(hashes)

    failures = []
    for user_id, candidate in (
        (SYNTHETIC_USER_PROFILES[0].user_id, secrets.token_urlsafe(24)),
        (secrets.token_urlsafe(12), password),
    ):
        with pytest.raises(AuthenticationError) as caught:
            service.login(user_id, candidate)
        failures.append((type(caught.value), caught.value.args))

    assert failures[0] == failures[1] == (AuthenticationError, ())
    assert service.active_session_count() == 0


def test_login_rotates_previous_session(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    service = AuthenticationService(hashes)
    user_id = SYNTHETIC_USER_PROFILES[0].user_id

    first = service.login(user_id, password)
    second = service.login(user_id, password)

    assert first.token != second.token
    with pytest.raises(AuthenticationError):
        service.authenticate_session(first.token)
    assert service.authenticate_session(second.token).actor.profile.user_id == user_id
    assert service.active_session_count() == 1


def test_concurrent_login_keeps_exactly_one_active_session(
    runtime_credentials: tuple[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    password, hashes = runtime_credentials
    service = AuthenticationService(hashes)
    workers = 4
    barrier = Barrier(workers)
    original_token_urlsafe = authentication_module.secrets.token_urlsafe

    def synchronized_token(size: int) -> str:
        barrier.wait()
        return original_token_urlsafe(size)

    monkeypatch.setattr(authentication_module.secrets, "token_urlsafe", synchronized_token)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        issued = list(
            executor.map(
                lambda _: service.login("team-a-onboarder", password),
                range(workers),
            )
        )

    active = 0
    for candidate in issued:
        try:
            service.authenticate_session(candidate.token)
        except AuthenticationError:
            continue
        active += 1
    assert active == 1
    assert service.active_session_count() == 1


def test_session_uses_absolute_eight_hour_expiry(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    clock = MutableClock()
    service = AuthenticationService(hashes, clock=clock)
    issued = service.login(SYNTHETIC_USER_PROFILES[0].user_id, password)

    clock.now += SESSION_TTL - timedelta(microseconds=1)
    assert service.authenticate_session(issued.token).actor.profile.team_id == TeamId.TEAM_A

    clock.now += timedelta(microseconds=1)
    with pytest.raises(AuthenticationError):
        service.authenticate_session(issued.token)
    assert service.active_session_count() == 0


def _raw_client(hashes: dict[str, str]) -> tuple[RawTestClient, AuthenticationService]:
    service = AuthenticationService(hashes)
    application = create_app(
        Settings(app_env="test", demo_controls_enabled=True),
        authentication_service=service,
    )
    return RawTestClient(application), service


def _login(client: RawTestClient, user_id: str, credential: str) -> str:
    response = client.post(
        "/api/auth/login", json={"user_id": user_id, "password": credential}
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_auth_http_login_me_logout_and_cookie_contract_for_all_profiles(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    for profile in SYNTHETIC_USER_PROFILES:
        client, _ = _raw_client(hashes)
        csrf = _login(client, profile.user_id, password)
        cookie = client.cookies.get("clm_session")
        assert cookie
        set_cookie = client.post(
            "/api/auth/login", json={"user_id": profile.user_id, "password": password}
        ).headers["set-cookie"]
        assert "HttpOnly" in set_cookie
        assert "SameSite=strict" in set_cookie
        assert "Path=/api" in set_cookie
        assert "Domain=" not in set_cookie

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["profile"]["user_id"] == profile.user_id
        assert me.json()["profile"]["role"] == profile.role
        assert me.json()["profile"]["team_id"] == profile.team_id
        csrf = me.json()["csrf_token"]

        logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 204
        assert client.get("/api/auth/me").status_code == 401


def test_bad_password_unknown_user_and_invalid_login_body_are_safe_and_equal(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    wrong_password = secrets.token_urlsafe(24)
    unknown_user = secrets.token_urlsafe(12)

    bad = client.post(
        "/api/auth/login",
        json={"user_id": "team-a-onboarder", "password": wrong_password},
    )
    unknown = client.post(
        "/api/auth/login", json={"user_id": unknown_user, "password": password}
    )
    malformed = client.post(
        "/api/auth/login", json={"user_id": "team-a-onboarder", "password": []}
    )

    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert malformed.status_code == 422
    assert wrong_password not in malformed.text
    assert unknown_user not in unknown.text


def test_protected_api_rejects_missing_and_malformed_sessions(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    _, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    expected = {
        "detail": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "A valid authenticated session is required.",
        }
    }

    missing = client.get("/api/system/execution-profile")
    client.cookies.set("clm_session", "malformed token", path="/api")
    malformed = client.get("/api/system/execution-profile")

    assert missing.status_code == malformed.status_code == 401
    assert missing.json() == malformed.json() == expected
    assert client.get("/health").status_code == 200


def test_http_login_rotation_revokes_old_cookie(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    first, service = _raw_client(hashes)
    second = RawTestClient(
        create_app(
            Settings(app_env="test", demo_controls_enabled=True),
            authentication_service=service,
        )
    )
    _login(first, "team-a-onboarder", password)
    old_cookie = first.cookies.get("clm_session")
    _login(second, "team-a-onboarder", password)

    assert old_cookie
    first.cookies.set("clm_session", old_cookie, path="/api")
    assert first.get("/api/auth/me").status_code == 401
    assert second.get("/api/auth/me").status_code == 200


def test_csrf_and_origin_checks_fail_closed(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    csrf = _login(client, "team-a-onboarder", password)
    body = {"uen": "202400001A"}

    missing = client.post("/api/clm/zero-touch/cases", json=body)
    wrong = client.post(
        "/api/clm/zero-touch/cases",
        json=body,
        headers={"X-CSRF-Token": secrets.token_urlsafe(24)},
    )
    cross_origin = client.post(
        "/api/clm/zero-touch/cases",
        json=body,
        headers={"X-CSRF-Token": csrf, "Origin": "https://untrusted.invalid"},
    )
    accepted = client.post(
        "/api/clm/zero-touch/cases",
        json=body,
        headers={"X-CSRF-Token": csrf, "Origin": "http://testserver"},
    )

    assert missing.status_code == wrong.status_code == cross_origin.status_code == 403
    assert missing.json() == wrong.json() == cross_origin.json()
    assert accepted.status_code == 201


def test_server_profile_ignores_spoofed_role_team_and_query_claims(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    _login(client, "team-a-onboarder", password)

    response = client.get(
        "/api/auth/me?team=TEAM_B&role=DIRECTOR",
        headers={"X-Team": "TEAM_B", "X-Role": "DIRECTOR"},
    )

    assert response.status_code == 200
    assert response.json()["profile"]["team_id"] == "TEAM_A"
    assert response.json()["profile"]["role"] == "CLIENT_ONBOARDER"


def test_team_creation_is_server_assigned_and_director_must_select_team(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    team_client, service = _raw_client(hashes)
    team_csrf = _login(team_client, "team-a-onboarder", password)

    normal = team_client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": team_csrf},
    )
    spoof = team_client.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "team_id": "TEAM_B"},
        headers={"X-CSRF-Token": team_csrf},
    )
    assert normal.status_code == 201
    assert normal.json()["case"]["team_id"] == "TEAM_A"
    assert spoof.status_code == 422

    director = RawTestClient(
        create_app(
            Settings(app_env="test", demo_controls_enabled=True),
            authentication_service=service,
        )
    )
    director_csrf = _login(director, "director", password)
    omitted = director.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": director_csrf},
    )
    selected = director.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "team_id": "TEAM_B"},
        headers={"X-CSRF-Token": director_csrf},
    )
    assert omitted.status_code == 422
    assert selected.status_code == 201
    assert selected.json()["case"]["team_id"] == "TEAM_B"


def test_cross_team_case_id_and_nonexistent_case_share_safe_404(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    team_a, _ = _raw_client(hashes)
    team_a_csrf = _login(team_a, "team-a-onboarder", password)
    created = team_a.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": team_a_csrf},
    )
    case_id = created.json()["case"]["case_id"]

    team_b = RawTestClient(team_a.app)
    _login(team_b, "team-b-onboarder", password)
    inaccessible = team_b.get(f"/api/clm/zero-touch/cases/{case_id}")
    nonexistent = team_b.get(
        "/api/clm/zero-touch/cases/00000000-0000-4000-8000-000000000000"
    )

    assert inaccessible.status_code == nonexistent.status_code == 404
    assert inaccessible.json() == nonexistent.json()


def test_every_case_route_family_has_identical_cross_team_and_absent_behavior(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    team_a, _ = _raw_client(hashes)
    csrf_a = _login(team_a, "team-a-onboarder", password)
    created = team_a.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": csrf_a},
    )
    case_id = created.json()["case"]["case_id"]

    team_b = RawTestClient(team_a.app)
    csrf_b = _login(team_b, "team-b-onboarder", password)
    opaque = "00000000-0000-4000-8000-000000000099"
    for policy in ROUTE_POLICIES:
        if policy.access != RouteAccess.CASE_SCOPED:
            continue
        values = {
            "case_id": case_id,
            "document_id": opaque,
            "failed_document_id": opaque,
            "exception_id": opaque,
            "discrepancy_id": opaque,
        }
        absent_values = {**values, "case_id": "00000000-0000-4000-8000-000000000000"}
        headers = {"X-CSRF-Token": csrf_b} if policy.method != "GET" else {}
        inaccessible = team_b.request(
            policy.method,
            policy.path.format(**values),
            headers=headers,
            json={},
        )
        absent = team_b.request(
            policy.method,
            policy.path.format(**absent_values),
            headers=headers,
            json={},
        )
        assert inaccessible.status_code == absent.status_code == 404, policy
        assert inaccessible.json() == absent.json(), policy


def test_every_current_application_route_is_deliberately_classified(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    _, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    actual = _collect_application_route_inventory(client.app)
    expected = route_inventory()
    counts = Counter(policy.access for policy in ROUTE_POLICIES)

    assert actual == expected
    assert len(expected) == len(ROUTE_POLICIES) == 42
    assert counts == {
        RouteAccess.PUBLIC: 2,
        RouteAccess.ACTOR_ONLY: 5,
        RouteAccess.CASE_CREATION: 4,
        RouteAccess.CASE_SCOPED: 31,
    }


def test_route_inventory_rejects_an_unclassified_included_router(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    _, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    unclassified = APIRouter()

    @unclassified.get("/api/test-only-unclassified-route")
    def test_only_route() -> dict[str, bool]:
        return {"ok": True}

    client.app.include_router(unclassified)
    actual = _collect_application_route_inventory(client.app)

    assert ("GET", "/api/test-only-unclassified-route") in actual
    assert actual != route_inventory()


def test_logout_invalidates_server_session_before_reuse(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    service = AuthenticationService(hashes)
    issued = service.login(SYNTHETIC_USER_PROFILES[0].user_id, password)

    service.logout(issued.token)

    with pytest.raises(AuthenticationError):
        service.authenticate_session(issued.token)
    assert service.active_session_count() == 0


def test_missing_or_malformed_credential_configuration_fails_safely(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    _, hashes = runtime_credentials
    missing_user = SYNTHETIC_USER_PROFILES[-1].user_id
    missing = dict(hashes)
    missing.pop(missing_user)

    with pytest.raises(AuthenticationConfigurationError) as missing_error:
        AuthenticationService(missing)
    assert missing_error.value.setting_key == "PHASE13_DIRECTOR_PASSWORD_HASH"

    malformed = dict(hashes)
    malformed[missing_user] = secrets.token_urlsafe(32)
    with pytest.raises(AuthenticationConfigurationError) as malformed_error:
        AuthenticationService(malformed)
    assert malformed_error.value.setting_key == "PHASE13_DIRECTOR_PASSWORD_HASH"


def test_authentication_values_are_not_logged(
    runtime_credentials: tuple[str, dict[str, str]], caplog: pytest.LogCaptureFixture
) -> None:
    password, hashes = runtime_credentials
    service = AuthenticationService(hashes)
    issued = service.login(SYNTHETIC_USER_PROFILES[0].user_id, password)
    service.authenticate_session(issued.token)
    service.logout(issued.token)

    logged = caplog.text
    assert password not in logged
    assert issued.token not in logged
    assert issued.record.csrf_token not in logged
    assert all(encoded not in logged for encoded in hashes.values())
