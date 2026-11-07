import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from phase13_test_credentials import build_test_authentication_service
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import app.services.login_admission as admission_module
from app.api_auth import build_auth_router
from app.domain.access import SYNTHETIC_USER_PROFILES
from app.services.admin_repository import InMemoryTeamRepository
from app.services.administration import TeamDirectoryService
from app.services.authentication import AuthenticationError, generate_scrypt_password_hash
from app.services.login_admission import LoginAdmission, LoginAdmissionDenied


def test_source_window_and_ipv4_mapped_addresses():
    now = 0.0
    admission = LoginAdmission(lambda: now)
    for _ in range(10):
        with admission.admit("192.0.2.10"):
            pass
    with pytest.raises(LoginAdmissionDenied) as denied, admission.admit("::ffff:192.0.2.10"):
        pytest.fail("mapped address bypassed the source limit")
    assert denied.value.retry_after == 6
    now = 5.5
    with pytest.raises(LoginAdmissionDenied) as denied, admission.admit("192.0.2.10"):
        pytest.fail("source refilled too early")
    assert denied.value.retry_after == 1
    now = 6
    with admission.admit("192.0.2.10"):
        pass


def test_rotating_addresses_hit_aggregate_budget():
    now = 0.0
    admission = LoginAdmission(lambda: now)
    for i in range(20):
        with admission.admit(f"192.0.2.{i}"):
            pass
    for i in range(20, 255):
        with pytest.raises(LoginAdmissionDenied) as denied, admission.admit(f"192.0.2.{i}"):
            pytest.fail("new address bypassed the aggregate budget")
        assert denied.value.retry_after == 1
    now = 1
    with admission.admit("2001:db8::1"):
        pass


def test_full_source_table_denies_new_keys_until_expiry(monkeypatch):
    monkeypatch.setattr(admission_module, "MAX_SOURCES", 2)
    now = 0.0
    admission = LoginAdmission(lambda: now)
    for host in ("192.0.2.1", "192.0.2.2"):
        with admission.admit(host):
            pass
    with pytest.raises(LoginAdmissionDenied) as denied, admission.admit("192.0.2.3"):
        pytest.fail("unexpired source was evicted")
    assert denied.value.retry_after == 60
    now = 60
    with admission.admit("192.0.2.3"):
        pass


def test_concurrency_gate_releases_on_failure():
    admission = LoginAdmission(lambda: 0)
    ready = Barrier(3, timeout=5)
    release = Event()

    def attempt(host):
        with pytest.raises(AuthenticationError), admission.admit(host):
            ready.wait()
            assert release.wait(5)
            raise AuthenticationError

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt, "192.0.2.1")
        second = pool.submit(attempt, "192.0.2.2")
        try:
            ready.wait()
            with pytest.raises(LoginAdmissionDenied) as denied, admission.admit("192.0.2.3"):
                pytest.fail("third verification started")
            assert denied.value.retry_after == 1
        finally:
            release.set()
        first.result()
        second.result()
    with admission.admit("192.0.2.3"):
        pass


def test_only_trusted_proxy_can_change_login_source():
    class Auth:
        calls = 0

        def login(self, user_id, credential):
            self.calls += 1
            raise AuthenticationError

    auth = Auth()
    app = FastAPI()
    app.include_router(
        build_auth_router(auth, None, cookie_secure=True, login_admission=LoginAdmission(lambda: 0))
    )
    proxy_app = ProxyHeadersMiddleware(app, trusted_hosts="192.0.2.2")
    body = {"user_id": "synthetic-user", "password": secrets.token_urlsafe(24)}
    with TestClient(proxy_app, client=("192.0.2.3", 12345)) as client:
        for i in range(10):
            response = client.post(
                "/api/auth/login", json=body, headers={"X-Forwarded-For": f"198.51.100.{i}"}
            )
            assert response.status_code == 401
        response = client.post(
            "/api/auth/login", json=body, headers={"X-Forwarded-For": "198.51.100.10"}
        )
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "6"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.json()["detail"]["code"] == "LOGIN_RATE_LIMITED"
        assert auth.calls == 10
    with TestClient(proxy_app, client=("192.0.2.2", 12345)) as client:
        for host in ("192.0.2.3", "192.0.2.4"):
            response = client.post("/api/auth/login", json=body, headers={"X-Forwarded-For": host})
            assert response.status_code == (429 if host == "192.0.2.3" else 401)
    assert auth.calls == 11


def test_five_synthetic_users_can_login_and_retry_from_one_address():
    users = ("ethan-tan", "ryan-lee", "olivia-koh", "hr-admin", "support-user")
    credential = secrets.token_urlsafe(24)
    password_hash = generate_scrypt_password_hash(credential)
    auth = build_test_authentication_service(
        {profile.user_id: password_hash for profile in SYNTHETIC_USER_PROFILES}
    )
    app = FastAPI()
    app.include_router(
        build_auth_router(
            auth,
            TeamDirectoryService(InMemoryTeamRepository()),
            cookie_secure=True,
            login_admission=LoginAdmission(lambda: 0),
        )
    )
    with TestClient(app, base_url="https://clm.example", client=("192.0.2.3", 12345)) as client:
        for user_id in users * 2:
            response = client.post(
                "/api/auth/login", json={"user_id": user_id, "password": credential}
            )
            assert response.status_code == 200
            assert response.json()["profile"]["user_id"] == user_id
            assert "Secure" in response.headers["Set-Cookie"]
        response = client.post(
            "/api/auth/login", json={"user_id": users[0], "password": credential}
        )
        assert response.status_code == 429


def test_shared_network_can_starve_until_rotating_sources_stop():
    now = 0
    admission = LoginAdmission(lambda: now)
    shared = "198.51.100.1"
    attackers = [f"192.0.2.{i}" for i in range(1, 7)]
    for i in range(20):
        with admission.admit(attackers[i % 6]):
            pass

    for now in range(1, 121):
        with admission.admit(attackers[(now - 1) % 6]):
            pass
        with pytest.raises(LoginAdmissionDenied) as denied, admission.admit(shared):
            pytest.fail("aggregate limit allowed excess verification")
        assert denied.value.retry_after == 1

    now = 125
    for _ in range(5):
        with admission.admit(shared):
            pass
