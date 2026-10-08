"""Shared-loop responsiveness, case serialization and queued authorization safety."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID

import anyio.to_thread
import httpx
import pytest
from phase13_test_clients import RawAsyncClient
from scripts.performance_optimization import application
from test_phase13_auth_rbac import _login, _raw_client
from test_phase13_auth_rbac import runtime_credentials as runtime_credentials

from app.api_auth import build_case_reauthorizer
from app.connectors.local_pdf_idp import LocalPdfTextIdpProvider
from app.services.authentication import AuthenticationError
from app.services.zero_touch_errors import ZeroTouchRequestError
from app.services.zero_touch_orchestration import ZeroTouchOrchestrator

PDF = (Path(__file__).parent / "fixtures/uat/clean-company-profile.pdf").read_bytes()
HEADERS = {"Content-Type": "application/pdf", "X-Document-Name": "clean-company-profile.pdf"}


def create(client):
    response = client.post("/api/clm/zero-touch/cases", json={"uen": "202400001A"})
    assert response.status_code == 201
    return response.json()["case"]["case_id"]


def upload(client, case_id):
    return client.post(
        f"/api/clm/zero-touch/cases/{case_id}/intake/documents", content=PDF, headers=HEADERS
    )


def assert_paused(client, target, case_id):
    response = client.get(f"/api/clm/zero-touch/cases/{case_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_INPUTS"
    assert response.json()["target_submission"]["state"] == "NOT_SUBMITTED"
    assert not target.calls


def test_native_intake_reauthorizes_in_worker_case_lock_and_leaves_shared_loop_responsive(
    monkeypatch,
):
    entered, release = threading.Event(), threading.Event()
    original = LocalPdfTextIdpProvider.process
    checks = []

    def builder(request, auth, access, cases, case_id, *args, **kwargs):
        callback = build_case_reauthorizer(request, auth, access, cases, case_id, *args, **kwargs)

        def check():
            assert cases.case_lock(case_id)._is_owned()
            with pytest.raises(RuntimeError):
                asyncio.get_running_loop()
            checks.append(threading.get_ident())
            callback()

        return check

    def blocked(provider, document):
        assert checks[-1] == threading.get_ident()
        entered.set()
        assert release.wait(5)
        return original(provider, document)

    with application("memory", None) as (client, _bundle, target, _registry):
        case_id = create(client)
        target.calls.clear()
        monkeypatch.setattr("app.main.build_case_reauthorizer", builder)
        monkeypatch.setattr(LocalPdfTextIdpProvider, "process", blocked)
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = pool.submit(upload, client, case_id)
            try:
                assert entered.wait(5)
                health = pool.submit(client.get, "/health").result(timeout=1)
                assert health.status_code == 200
            finally:
                release.set()
            response = pending.result(timeout=5)
        assert response.status_code == 201 and response.json()["state"] == "REVIEWED"
        assert len(checks) == 1
        assert_paused(client, target, case_id)


def test_same_case_parallel_intakes_remain_serial_and_keep_both_documents(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = LocalPdfTextIdpProvider.process
    active = peak = calls = 0
    counter_lock = threading.Lock()

    def blocked(provider, document):
        nonlocal active, peak, calls
        with counter_lock:
            active += 1
            calls += 1
            peak = max(peak, active)
            first = calls == 1
        try:
            if first:
                entered.set()
                assert release.wait(5)
            return original(provider, document)
        finally:
            with counter_lock:
                active -= 1

    with application("memory", None) as (client, bundle, target, _registry):
        case_id = create(client)
        target.calls.clear()
        monkeypatch.setattr(LocalPdfTextIdpProvider, "process", blocked)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(upload, client, case_id)
            try:
                assert entered.wait(5)
                second = pool.submit(upload, client, case_id)
                assert client.get("/health").status_code == 200
            finally:
                release.set()
            responses = [first.result(timeout=5), second.result(timeout=5)]
        assert all(r.status_code == 201 and r.json()["state"] == "REVIEWED" for r in responses)
        documents = bundle.documents.list_for_case(UUID(case_id))
        assert len(documents) == 2 and len({d.document_id for d in documents}) == 2
        assert calls == 2 and peak == 1 and active == 0
        assert_paused(client, target, case_id)


@pytest.mark.parametrize(("mode", "expected"), [("revoked", 401), ("cross_team", 404)])
def test_intake_rechecks_current_session_and_scope_before_writes(
    runtime_credentials, monkeypatch, mode, expected
):
    credential, hashes = runtime_credentials
    client, authentication = _raw_client(hashes)
    with client:
        csrf = _login(client, "maya-lim", credential)
        response = client.post(
            "/api/clm/zero-touch/cases",
            json={"uen": "202400001A"},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 201
        case_id = response.json()["case"]["case_id"]
        original = authentication.authenticate_session
        cross_team = (
            authentication.login("sophia-ng", credential).record if mode == "cross_team" else None
        )
        calls = 0

        def changed(token):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(token)
            if cross_team is not None:
                return cross_team
            raise AuthenticationError

        monkeypatch.setattr(authentication, "authenticate_session", changed)
        denied = client.post(
            f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
            content=PDF,
            headers={**HEADERS, "X-CSRF-Token": csrf},
        )
        monkeypatch.setattr(authentication, "authenticate_session", original)
        assert denied.status_code == expected and calls == 2
        assert denied.json()["detail"]["code"] == (
            "AUTHENTICATION_REQUIRED" if mode == "revoked" else "CASE_NOT_FOUND"
        )
        assert client.get(f"/api/onboarding/cases/{case_id}/documents").json() == []
        assert (
            client.get(f"/api/clm/zero-touch/cases/{case_id}").json()["status"] == "PENDING_INPUTS"
        )


def portal_upload(client, case_id):
    csrf = client.get("/api/auth/me").json()["csrf_token"]

    async def request():
        async with RawAsyncClient(
            transport=httpx.ASGITransport(app=client.app),
            base_url="http://testserver",
            cookies=client.cookies.jar,
        ) as requester:
            return await requester.post(
                f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
                content=PDF,
                headers={**HEADERS, "X-CSRF-Token": csrf},
            )

    assert client.portal is not None
    return client.portal.start_task_soon(request)


def test_started_request_cancellation_finishes_one_owned_intake_without_dispatch(monkeypatch):
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    original_provider = LocalPdfTextIdpProvider.process
    original_intake = ZeroTouchOrchestrator.intake_document

    def blocked(provider, document):
        entered.set()
        assert release.wait(5)
        return original_provider(provider, document)

    def intake(zero, **kwargs):
        try:
            return original_intake(zero, **kwargs)
        finally:
            finished.set()

    with application("memory", None) as (client, bundle, target, _registry):
        case_id = create(client)
        target.calls.clear()
        monkeypatch.setattr(LocalPdfTextIdpProvider, "process", blocked)
        monkeypatch.setattr(ZeroTouchOrchestrator, "intake_document", intake)
        pending = portal_upload(client, case_id)
        try:
            assert entered.wait(5)
            assert pending.cancel()
        finally:
            release.set()
        assert finished.wait(5)
        documents = bundle.documents.list_for_case(UUID(case_id))
        assert len(documents) == 1 and documents[0].state.value == "REVIEWED"
        assert_paused(client, target, case_id)


def test_cancelled_queued_intake_never_enters_worker_or_creates_document(monkeypatch):
    from fastapi.concurrency import run_in_threadpool

    entered, release, queued = threading.Event(), threading.Event(), threading.Event()
    original = LocalPdfTextIdpProvider.process
    dependency_calls = 0

    def blocked(provider, document):
        entered.set()
        assert release.wait(5)
        return original(provider, document)

    async def observed(function, *args, **kwargs):
        nonlocal dependency_calls
        if function.__name__ == "get_zero_touch_orchestrator":
            dependency_calls += 1
            if dependency_calls == 2:
                queued.set()
        return await run_in_threadpool(function, *args, **kwargs)

    async def capacity(tokens):
        limiter = anyio.to_thread.current_default_thread_limiter()
        previous = limiter.total_tokens
        limiter.total_tokens = tokens
        return previous

    with application("memory", None) as (client, bundle, target, _registry):
        first_id, second_id = create(client), create(client)
        target.calls.clear()
        monkeypatch.setattr(LocalPdfTextIdpProvider, "process", blocked)
        monkeypatch.setattr("fastapi.dependencies.utils.run_in_threadpool", observed)
        assert client.portal is not None
        # Obtain each task credential before restricting the shared pool.
        # With one occupied token, a second request queues at its sync dependency,
        # before it can enter the handler or native intake worker.
        csrf = client.get("/api/auth/me").json()["csrf_token"]

        async def request(case_id):
            async with RawAsyncClient(
                transport=httpx.ASGITransport(app=client.app),
                base_url="http://testserver",
                cookies=client.cookies.jar,
            ) as requester:
                return await requester.post(
                    f"/api/clm/zero-touch/cases/{case_id}/intake/documents",
                    content=PDF,
                    headers={**HEADERS, "X-CSRF-Token": csrf},
                )

        previous = client.portal.call(capacity, 1)
        first = client.portal.start_task_soon(request, first_id)
        try:
            assert entered.wait(5)
            second = client.portal.start_task_soon(request, second_id)
            assert queued.wait(5)
            assert second.cancel()
        finally:
            release.set()
            client.portal.call(capacity, previous)
        assert first.result(timeout=5).status_code == 201
        assert bundle.documents.list_for_case(UUID(second_id)) == []
        assert dependency_calls == 2
        assert_paused(client, target, second_id)


def test_worker_exception_keeps_existing_safe_http_projection(monkeypatch):
    def missing(_zero, **_kwargs):
        raise ZeroTouchRequestError(
            code="ZERO_TOUCH_CASE_NOT_FOUND",
            message="The zero-touch onboarding case was not found.",
        )

    with application("memory", None) as (client, bundle, target, _registry):
        case_id = create(client)
        target.calls.clear()
        monkeypatch.setattr(ZeroTouchOrchestrator, "intake_document", missing)
        response = upload(client, case_id)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "ZERO_TOUCH_CASE_NOT_FOUND"
        assert bundle.documents.list_for_case(UUID(case_id)) == []
        assert_paused(client, target, case_id)
