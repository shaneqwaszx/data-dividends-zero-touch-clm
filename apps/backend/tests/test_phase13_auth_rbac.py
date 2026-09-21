from __future__ import annotations

import secrets
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from phase13_test_clients import RawTestClient
from phase13_test_credentials import build_test_authentication_service
from phase13_test_settings import ordinary_test_settings
from starlette.routing import BaseRoute

import app.services.authentication as authentication_module
from app.composition import build_authentication_service
from app.config import Settings
from app.domain.access import (
    SYNTHETIC_USER_PROFILES,
    TEAM_BY_ID,
    Role,
    TeamId,
)
from app.main import create_app
from app.services.admin_repository import (
    InMemoryProfileRepository,
    InMemoryTeamRepository,
    bootstrap_administration,
)
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
        "maya-lim",
        "ethan-tan",
        "sophia-ng",
        "ryan-lee",
        "olivia-koh",
    ]
    assert [profile.display_name for profile in SYNTHETIC_USER_PROFILES] == [
        "Maya Lim",
        "Ethan Tan",
        "Sophia Ng",
        "Ryan Lee",
        "Olivia Koh",
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
        "Alpha",
        "Alpha",
        "Beta",
        "Beta",
        "Global / cross-team",
    ]
    assert TEAM_BY_ID[TeamId.TEAM_A].model_dump() == {
        "team_id": TeamId.TEAM_A,
        "display_name": "Alpha",
        "team_type": "Corporate Client Onboarding",
        "client_scope_label": "Alpha",
    }
    assert TEAM_BY_ID[TeamId.TEAM_A].description == (
        "Type: Corporate Client Onboarding | Client coverage: Alpha"
    )
    assert TEAM_BY_ID[TeamId.TEAM_B].model_dump() == {
        "team_id": TeamId.TEAM_B,
        "display_name": "Beta",
        "team_type": "Corporate Client Onboarding",
        "client_scope_label": "Beta",
    }
    assert TEAM_BY_ID[TeamId.TEAM_B].description == (
        "Type: Corporate Client Onboarding | Client coverage: Beta"
    )


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
    service = build_test_authentication_service(hashes)

    for profile in SYNTHETIC_USER_PROFILES:
        issued = service.login(profile.user_id, password)
        assert service.authenticate_session(issued.token).actor.profile == profile

    assert service.active_session_count() == 5


def test_bad_password_and_unknown_user_use_same_failure(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    service = build_test_authentication_service(hashes)

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
    service = build_test_authentication_service(hashes)
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
    service = build_test_authentication_service(hashes)
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
                lambda _: service.login("maya-lim", password),
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
    service = build_test_authentication_service(hashes, clock=clock)
    issued = service.login(SYNTHETIC_USER_PROFILES[0].user_id, password)

    clock.now += SESSION_TTL - timedelta(microseconds=1)
    assert service.authenticate_session(issued.token).actor.profile.team_id == TeamId.TEAM_A

    clock.now += timedelta(microseconds=1)
    with pytest.raises(AuthenticationError):
        service.authenticate_session(issued.token)
    assert service.active_session_count() == 0


def _raw_client(hashes: dict[str, str]) -> tuple[RawTestClient, AuthenticationService]:
    service = build_test_authentication_service(hashes)
    application = create_app(
        ordinary_test_settings(demo_controls_enabled=True),
        authentication_service=service,
    )
    return RawTestClient(application), service


def _login(client: RawTestClient, user_id: str, credential: str) -> str:
    response = client.post("/api/auth/login", json={"user_id": user_id, "password": credential})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _production_raw_client(hashes: dict[str, str]) -> RawTestClient:
    application = create_app(
        Settings(
            _env_file=None,
            app_env="production",
            clm_persistence_mode="memory",
            mongo_uri=None,
            phase13_browser_origin="https://clm.example",
            phase13_cookie_secure=True,
        ),
        authentication_service=build_test_authentication_service(hashes),
    )
    return RawTestClient(application, base_url="https://clm.example")


def _assert_csrf_rejection(response: httpx.Response) -> None:
    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "CSRF_VALIDATION_FAILED",
            "message": "The request could not be validated.",
        }
    }


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


def test_authenticated_profile_projects_canonical_team_metadata(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    team_client, service = _raw_client(hashes)
    team_profile = team_client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": password},
    ).json()["profile"]

    assert team_profile["team_display_name"] == "Alpha"
    assert team_profile["team_type"] == "Corporate Client Onboarding"
    assert team_profile["team_description"] == (
        "Type: Corporate Client Onboarding | Client coverage: Alpha"
    )
    assert team_profile["capabilities"] == ["CASE_ACCESS", "POLICY_VIEW"]

    director_client = RawTestClient(team_client.app)
    director_profile = director_client.post(
        "/api/auth/login",
        json={"user_id": "olivia-koh", "password": password},
    ).json()["profile"]
    assert director_profile["team_id"] is None
    assert director_profile["team_display_name"] is None
    assert director_profile["team_type"] is None
    assert director_profile["team_description"] == "Global / cross-team access"
    assert director_profile["capabilities"] == [
        "CASE_ACCESS",
        "CASE_GLOBAL",
        "POLICY_MUTATE",
        "POLICY_VIEW",
    ]


def test_bad_password_unknown_user_and_invalid_login_body_are_safe_and_equal(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    wrong_password = secrets.token_urlsafe(24)
    unknown_user = secrets.token_urlsafe(12)

    bad = client.post(
        "/api/auth/login",
        json={"user_id": "maya-lim", "password": wrong_password},
    )
    unknown = client.post("/api/auth/login", json={"user_id": unknown_user, "password": password})
    malformed = client.post("/api/auth/login", json={"user_id": "maya-lim", "password": []})

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
            ordinary_test_settings(demo_controls_enabled=True),
            authentication_service=service,
        )
    )
    _login(first, "maya-lim", password)
    old_cookie = first.cookies.get("clm_session")
    _login(second, "maya-lim", password)

    assert old_cookie
    first.cookies.set("clm_session", old_cookie, path="/api")
    assert first.get("/api/auth/me").status_code == 401
    assert second.get("/api/auth/me").status_code == 200


def test_csrf_and_origin_checks_fail_closed(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    csrf = _login(client, "maya-lim", password)
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


def test_documented_vite_origin_reaches_login_credential_verification(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    application = create_app(
        ordinary_test_settings(),
        authentication_service=build_test_authentication_service(hashes),
    )
    client = RawTestClient(application, base_url="http://127.0.0.1:8000")
    headers = {"Origin": "http://127.0.0.1:5173"}

    accepted = client.post(
        "/api/auth/login",
        headers=headers,
        json={"user_id": "maya-lim", "password": password},
    )
    wrong_password = client.post(
        "/api/auth/login",
        headers=headers,
        json={"user_id": "maya-lim", "password": secrets.token_urlsafe(24)},
    )

    assert accepted.status_code == 200
    assert accepted.json()["profile"]["user_id"] == "maya-lim"
    assert wrong_password.status_code == 401
    assert wrong_password.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"


def test_login_rejects_foreign_origin_and_referer(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    application = create_app(
        ordinary_test_settings(),
        authentication_service=build_test_authentication_service(hashes),
    )
    client = RawTestClient(application, base_url="http://127.0.0.1:8000")
    body = {"user_id": "maya-lim", "password": password}

    foreign_origin = client.post(
        "/api/auth/login",
        headers={"Origin": "https://foreign.invalid"},
        json=body,
    )
    foreign_referer = client.post(
        "/api/auth/login",
        headers={"Referer": "https://foreign.invalid/sign-in"},
        json=body,
    )

    assert foreign_origin.status_code == foreign_referer.status_code == 403
    assert foreign_origin.json() == foreign_referer.json()
    assert foreign_origin.json()["detail"]["code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.parametrize(
    "header,value",
    [
        ("Origin", "http://testserver/"),
        ("Origin", "http://testserver/path"),
        ("Origin", "http://testserver?query=1"),
        ("Origin", "http://testserver#fragment"),
        ("Origin", "http://user@testserver"),
        ("Origin", "http://testserver:invalid"),
        ("Origin", "null"),
        ("Origin", "http://testserver,https://foreign.invalid"),
        ("Referer", "https://foreign.invalid/path?query=1"),
        ("Referer", "http://user@testserver/path"),
    ],
)
def test_login_rejects_malformed_or_foreign_browser_source_headers(
    runtime_credentials: tuple[str, dict[str, str]],
    header: str,
    value: str,
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)

    response = client.post(
        "/api/auth/login",
        headers={header: value},
        json={"user_id": "maya-lim", "password": password},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "CSRF_VALIDATION_FAILED"


def test_valid_same_origin_referer_may_include_path_and_query(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)

    response = client.post(
        "/api/auth/login",
        headers={"Referer": "http://testserver/sign-in?return=%2Fcases"},
        json={"user_id": "maya-lim", "password": password},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("header_value", "expected_status"),
    [
        ("https://clm.example", 200),
        ("https://foreign.invalid", 403),
    ],
    ids=["trusted", "foreign"],
)
def test_production_login_origin_single_field_contract(
    runtime_credentials: tuple[str, dict[str, str]],
    header_value: str,
    expected_status: int,
) -> None:
    password, hashes = runtime_credentials
    response = _production_raw_client(hashes).post(
        "/api/auth/login",
        headers=[("Origin", header_value)],
        json={"user_id": "maya-lim", "password": password},
    )

    assert response.status_code == expected_status
    if expected_status == 403:
        _assert_csrf_rejection(response)


@pytest.mark.parametrize(
    "headers",
    [
        [("Origin", "https://clm.example"), ("origin", "https://foreign.invalid")],
        [("ORIGIN", "https://foreign.invalid"), ("Origin", "https://clm.example")],
        [("origin", "https://clm.example"), ("Origin", "https://clm.example")],
        [("Origin", "https://foreign.invalid"), ("ORIGIN", "https://foreign.invalid")],
    ],
    ids=["trusted-foreign", "foreign-trusted", "trusted-trusted", "foreign-foreign"],
)
def test_production_login_rejects_duplicate_origin_fields(
    runtime_credentials: tuple[str, dict[str, str]],
    headers: list[tuple[str, str]],
) -> None:
    password, hashes = runtime_credentials
    response = _production_raw_client(hashes).post(
        "/api/auth/login",
        headers=headers,
        json={"user_id": "maya-lim", "password": password},
    )

    _assert_csrf_rejection(response)


@pytest.mark.parametrize(
    ("header_value", "expected_status"),
    [
        ("https://clm.example", 200),
        ("https://clm.example/cases/ABC?tab=1", 200),
        ("https://foreign.invalid/sign-in", 403),
        ("https://clm.example/cases/ABC#section", 403),
    ],
    ids=["trusted", "trusted-path-query", "foreign", "fragment"],
)
def test_production_login_referer_single_field_contract(
    runtime_credentials: tuple[str, dict[str, str]],
    header_value: str,
    expected_status: int,
) -> None:
    password, hashes = runtime_credentials
    response = _production_raw_client(hashes).post(
        "/api/auth/login",
        headers=[("Referer", header_value)],
        json={"user_id": "maya-lim", "password": password},
    )

    assert response.status_code == expected_status
    if expected_status == 403:
        _assert_csrf_rejection(response)


@pytest.mark.parametrize(
    "headers",
    [
        [
            ("Referer", "https://clm.example/sign-in"),
            ("referer", "https://foreign.invalid/sign-in"),
        ],
        [
            ("REFERER", "https://foreign.invalid/sign-in"),
            ("Referer", "https://clm.example/sign-in"),
        ],
        [
            ("referer", "https://clm.example/sign-in"),
            ("Referer", "https://clm.example/sign-in"),
        ],
        [
            ("Referer", "https://foreign.invalid/sign-in"),
            ("REFERER", "https://foreign.invalid/sign-in"),
        ],
    ],
    ids=["trusted-foreign", "foreign-trusted", "trusted-trusted", "foreign-foreign"],
)
def test_production_login_rejects_duplicate_referer_fields(
    runtime_credentials: tuple[str, dict[str, str]],
    headers: list[tuple[str, str]],
) -> None:
    password, hashes = runtime_credentials
    response = _production_raw_client(hashes).post(
        "/api/auth/login",
        headers=headers,
        json={"user_id": "maya-lim", "password": password},
    )

    _assert_csrf_rejection(response)


@pytest.mark.parametrize(
    "browser_source_headers",
    [
        [("Origin", "https://clm.example")],
        [("Origin", "https://clm.example"), ("origin", "https://foreign.invalid")],
        [("ORIGIN", "https://foreign.invalid"), ("Origin", "https://clm.example")],
        [("origin", "https://clm.example"), ("Origin", "https://clm.example")],
        [
            ("Referer", "https://clm.example/cases"),
            ("referer", "https://foreign.invalid/cases"),
        ],
        [
            ("Origin", "https://clm.example"),
            ("Referer", "https://clm.example/cases"),
            ("referer", "https://foreign.invalid/cases"),
        ],
        [
            ("Origin", "https://clm.example"),
            ("origin", "https://foreign.invalid"),
            ("Referer", "https://clm.example/cases"),
        ],
    ],
    ids=[
        "single-trusted-origin",
        "duplicate-origin-trusted-foreign",
        "duplicate-origin-foreign-trusted",
        "duplicate-origin-trusted-trusted",
        "duplicate-referer",
        "single-origin-duplicate-referer",
        "duplicate-origin-single-referer",
    ],
)
def test_production_unsafe_mutation_browser_source_cardinality(
    runtime_credentials: tuple[str, dict[str, str]],
    browser_source_headers: list[tuple[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client = _production_raw_client(hashes)
    csrf = _login(client, "maya-lim", password)
    response = client.post(
        "/api/clm/zero-touch/cases",
        headers=[("X-CSRF-Token", csrf), *browser_source_headers],
        json={"uen": "202400001A"},
    )

    if len(browser_source_headers) == 1:
        assert response.status_code == 201
    else:
        _assert_csrf_rejection(response)


def test_request_host_cannot_expand_the_configured_origin_allowlist(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)

    response = client.post(
        "/api/auth/login",
        headers={"Host": "foreign.invalid", "Origin": "http://foreign.invalid"},
        json={"user_id": "maya-lim", "password": password},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "CSRF_VALIDATION_FAILED"


def test_vite_origin_does_not_bypass_authenticated_csrf_token(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    application = create_app(
        ordinary_test_settings(demo_controls_enabled=True),
        authentication_service=build_test_authentication_service(hashes),
    )
    client = RawTestClient(application, base_url="http://127.0.0.1:8000")
    origin = {"Origin": "http://127.0.0.1:5173"}
    login = client.post(
        "/api/auth/login",
        headers=origin,
        json={"user_id": "maya-lim", "password": password},
    )
    assert login.status_code == 200

    missing_csrf = client.post(
        "/api/clm/zero-touch/cases",
        headers=origin,
        json={"uen": "202400001A"},
    )

    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["detail"]["code"] == "CSRF_VALIDATION_FAILED"


def test_production_does_not_trust_the_development_vite_origin(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    application = create_app(
        Settings(
            _env_file=None,
            app_env="production",
            clm_persistence_mode="memory",
            mongo_uri=None,
            phase13_browser_origin="https://clm.example",
            phase13_cookie_secure=True,
        ),
        authentication_service=build_test_authentication_service(hashes),
    )
    client = RawTestClient(application, base_url="https://clm.example")

    response = client.post(
        "/api/auth/login",
        headers={"Origin": "http://127.0.0.1:5173"},
        json={"user_id": "maya-lim", "password": password},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "CSRF_VALIDATION_FAILED"


@pytest.mark.parametrize(
    "configured_origin",
    [None, "http://clm.example", "https://clm.example/path", "not-an-origin"],
)
def test_production_origin_configuration_fails_closed_before_persistence(
    configured_origin: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persistence_initialized = False

    def persistence_probe(settings: Settings) -> object:
        nonlocal persistence_initialized
        persistence_initialized = True
        raise AssertionError(settings.app_env)

    monkeypatch.setattr("app.main.build_persistence_bundle", persistence_probe)
    settings = Settings(
        _env_file=None,
        app_env="production",
        clm_persistence_mode="memory",
        mongo_uri=None,
        phase13_browser_origin=configured_origin,
        phase13_cookie_secure=True,
    )

    with pytest.raises(ValueError):
        create_app(settings)
    assert not persistence_initialized


def test_server_profile_ignores_spoofed_role_team_and_query_claims(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    _login(client, "maya-lim", password)

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
    team_csrf = _login(team_client, "maya-lim", password)

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
            ordinary_test_settings(demo_controls_enabled=True),
            authentication_service=service,
        )
    )
    director_csrf = _login(director, "olivia-koh", password)
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
    team_a_csrf = _login(team_a, "maya-lim", password)
    created = team_a.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": team_a_csrf},
    )
    case_id = created.json()["case"]["case_id"]

    team_b = RawTestClient(team_a.app)
    _login(team_b, "sophia-ng", password)
    inaccessible = team_b.get(f"/api/clm/zero-touch/cases/{case_id}")
    nonexistent = team_b.get("/api/clm/zero-touch/cases/00000000-0000-4000-8000-000000000000")

    assert inaccessible.status_code == nonexistent.status_code == 404
    assert inaccessible.json() == nonexistent.json()


def test_shared_store_portfolios_and_representative_mutations_follow_team_scope(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    maya, _ = _raw_client(hashes)
    ethan = RawTestClient(maya.app)
    sophia = RawTestClient(maya.app)
    ryan = RawTestClient(maya.app)
    olivia = RawTestClient(maya.app)
    csrf_maya = _login(maya, "maya-lim", password)
    csrf_ethan = _login(ethan, "ethan-tan", password)
    csrf_sophia = _login(sophia, "sophia-ng", password)
    csrf_ryan = _login(ryan, "ryan-lee", password)
    _login(olivia, "olivia-koh", password)

    case_a = maya.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A", "priority": 10},
        headers={"X-CSRF-Token": csrf_maya},
    ).json()["case"]["case_id"]
    case_b = sophia.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400002B", "priority": 8},
        headers={"X-CSRF-Token": csrf_sophia},
    ).json()["case"]["case_id"]

    assert [item["case_id"] for item in maya.get("/api/clm/zero-touch/cases").json()] == [case_a]
    assert [item["case_id"] for item in ethan.get("/api/clm/zero-touch/cases").json()] == [case_a]
    assert [item["case_id"] for item in sophia.get("/api/clm/zero-touch/cases").json()] == [case_b]
    assert [item["case_id"] for item in ryan.get("/api/clm/zero-touch/cases").json()] == [case_b]
    assert {item["case_id"] for item in olivia.get("/api/clm/zero-touch/cases").json()} == {
        case_a,
        case_b,
    }

    assert (
        ethan.patch(
            f"/api/clm/zero-touch/cases/{case_a}/priority",
            json={"priority": 9},
            headers={"X-CSRF-Token": csrf_ethan},
        ).status_code
        == 200
    )
    assert (
        ryan.patch(
            f"/api/clm/zero-touch/cases/{case_b}/priority",
            json={"priority": 7},
            headers={"X-CSRF-Token": csrf_ryan},
        ).status_code
        == 200
    )

    absent_id = "00000000-0000-4000-8000-000000000000"
    for client, csrf, foreign_id in (
        (maya, csrf_maya, case_b),
        (sophia, csrf_sophia, case_a),
    ):
        foreign_get = client.get(f"/api/clm/zero-touch/cases/{foreign_id}")
        absent_get = client.get(f"/api/clm/zero-touch/cases/{absent_id}")
        foreign_patch = client.patch(
            f"/api/clm/zero-touch/cases/{foreign_id}/priority",
            json={"priority": 1},
            headers={"X-CSRF-Token": csrf},
        )
        absent_patch = client.patch(
            f"/api/clm/zero-touch/cases/{absent_id}/priority",
            json={"priority": 1},
            headers={"X-CSRF-Token": csrf},
        )
        assert foreign_get.status_code == absent_get.status_code == 404
        assert foreign_get.json() == absent_get.json()
        assert foreign_patch.status_code == absent_patch.status_code == 404
        assert foreign_patch.json() == absent_patch.json()


def test_every_case_route_family_has_identical_cross_team_and_absent_behavior(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    password, hashes = runtime_credentials
    team_a, _ = _raw_client(hashes)
    csrf_a = _login(team_a, "maya-lim", password)
    created = team_a.post(
        "/api/clm/zero-touch/cases",
        json={"uen": "202400001A"},
        headers={"X-CSRF-Token": csrf_a},
    )
    case_id = created.json()["case"]["case_id"]

    team_b = RawTestClient(team_a.app)
    csrf_b = _login(team_b, "sophia-ng", password)
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


@pytest.mark.parametrize(("mode", "expected_status"), [("revoked", 401), ("cross_team", 404)])
def test_review_reauthorizes_inside_case_lock_before_mutation(
    runtime_credentials: tuple[str, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    expected_status: int,
) -> None:
    password, hashes = runtime_credentials
    client, authentication = _raw_client(hashes)
    csrf = _login(client, "maya-lim", password)
    created = client.post(
        "/api/demo/clm/zero-touch/cases",
        json={"uen": "202400001A", "scenario": "DOCUMENT_DISCREPANCY"},
        headers={"X-CSRF-Token": csrf},
    )
    case_id = created.json()["case"]["case_id"]
    paused = client.post(
        f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
        content=b"synthetic review evidence",
        headers={
            "Content-Type": "text/plain",
            "X-Document-Name": "review.txt",
            "X-CSRF-Token": csrf,
        },
    )
    document = client.get(f"/api/onboarding/cases/{case_id}/documents").json()[0]
    original_authenticate = authentication.authenticate_session
    cross_team_session = (
        authentication.login("sophia-ng", password).record if mode == "cross_team" else None
    )
    calls = 0

    def authenticate_with_mid_request_change(token: str | None):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_authenticate(token)
        if cross_team_session is not None:
            return cross_team_session
        raise AuthenticationError

    monkeypatch.setattr(
        authentication, "authenticate_session", authenticate_with_mid_request_change
    )
    denied = client.post(
        f"/api/onboarding/cases/{case_id}/documents/{document['document_id']}/reviews",
        json={"field_key": "legal_name", "decision": "ACCEPTED"},
        headers={"X-CSRF-Token": csrf},
    )
    monkeypatch.setattr(authentication, "authenticate_session", original_authenticate)
    after_document = client.get(f"/api/onboarding/cases/{case_id}/documents").json()[0]
    after_automation = client.get(f"/api/clm/zero-touch/cases/{case_id}").json()

    assert denied.status_code == expected_status
    assert denied.json()["detail"]["code"] == (
        "AUTHENTICATION_REQUIRED" if mode == "revoked" else "CASE_NOT_FOUND"
    )
    assert len(after_document["events"]) == len(document["events"])
    assert after_automation["version"] == paused.json()["version"]


def test_every_current_application_route_is_deliberately_classified(
    runtime_credentials: tuple[str, dict[str, str]],
) -> None:
    _, hashes = runtime_credentials
    client, _ = _raw_client(hashes)
    actual = _collect_application_route_inventory(client.app)
    expected = route_inventory()
    counts = Counter(policy.access for policy in ROUTE_POLICIES)

    assert actual == expected
    assert len(expected) == len(ROUTE_POLICIES) == 59
    assert counts == {
        RouteAccess.PUBLIC: 2,
        RouteAccess.ACTOR_ONLY: 17,
        RouteAccess.CASE_CREATION: 4,
        RouteAccess.CASE_PORTFOLIO: 4,
        RouteAccess.CASE_SCOPED: 32,
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
    service = build_test_authentication_service(hashes)
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
        build_test_authentication_service(missing)
    assert missing_error.value.setting_key == "PHASE13_OLIVIA_KOH_PASSWORD_HASH"

    malformed = dict(hashes)
    malformed[missing_user] = secrets.token_urlsafe(32)
    with pytest.raises(AuthenticationConfigurationError) as malformed_error:
        build_test_authentication_service(malformed)
    assert malformed_error.value.setting_key == "PHASE13_OLIVIA_KOH_PASSWORD_HASH"


def test_authentication_composition_uses_new_synthetic_profile_settings() -> None:
    credential = secrets.token_urlsafe(24)
    encoded = generate_scrypt_password_hash(credential)
    settings = Settings(
        _env_file=None,
        phase13_maya_lim_password_hash=encoded,
        phase13_ethan_tan_password_hash=encoded,
        phase13_sophia_ng_password_hash=encoded,
        phase13_ryan_lee_password_hash=encoded,
        phase13_olivia_koh_password_hash=encoded,
        phase14_5_hr_admin_password_hash=encoded,
    )
    teams = InMemoryTeamRepository()
    profiles = InMemoryProfileRepository()
    bootstrap_administration(
        teams,
        profiles,
        {
            **{profile.user_id: encoded for profile in SYNTHETIC_USER_PROFILES},
            "hr-admin": encoded,
        },
    )
    service = build_authentication_service(settings, profiles, teams)

    assert service.login("maya-lim", credential).record.actor.profile.display_name == "Maya Lim"
    assert service.login("olivia-koh", credential).record.actor.profile.role == Role.DIRECTOR


def test_authentication_values_are_not_logged(
    runtime_credentials: tuple[str, dict[str, str]], caplog: pytest.LogCaptureFixture
) -> None:
    password, hashes = runtime_credentials
    service = build_test_authentication_service(hashes)
    issued = service.login(SYNTHETIC_USER_PROFILES[0].user_id, password)
    service.authenticate_session(issued.token)
    service.logout(issued.token)

    logged = caplog.text
    assert password not in logged
    assert issued.token not in logged
    assert issued.record.csrf_token not in logged
    assert all(encoded not in logged for encoded in hashes.values())
