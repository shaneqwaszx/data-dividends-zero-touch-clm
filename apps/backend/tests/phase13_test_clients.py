"""Clients that authenticate legacy API regressions with runtime-only credentials."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi.testclient import TestClient as FastApiTestClient
from phase13_test_credentials import TEST_PASSWORD

RawAsyncClient = httpx.AsyncClient
RawTestClient = FastApiTestClient


class AuthenticatedAsyncClient(httpx.AsyncClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._phase13_authenticated = False
        self._phase13_csrf: str | None = None

    async def request(self, method: str, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        path = httpx.URL(url).path
        if path.startswith("/api") and path != "/api/auth/login":
            await self._phase13_login()
            if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                headers = dict(kwargs.pop("headers", {}) or {})
                headers.setdefault("X-CSRF-Token", self._phase13_csrf or "")
                kwargs["headers"] = headers
        response = await super().request(method, url, **kwargs)
        if response.status_code == 401:
            self._phase13_authenticated = False
            self._phase13_csrf = None
        if path == "/api/auth/logout" and response.is_success:
            self._phase13_authenticated = False
            self._phase13_csrf = None
        return response

    async def _phase13_login(self) -> None:
        if self._phase13_authenticated:
            return
        response = await super().request(
            "POST",
            "/api/auth/login",
            json={"user_id": "maya-lim", "password": TEST_PASSWORD},
        )
        response.raise_for_status()
        self._phase13_csrf = response.json()["csrf_token"]
        self._phase13_authenticated = True


class AuthenticatedTestClient(FastApiTestClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._phase13_authenticated = False
        self._phase13_csrf: str | None = None

    def request(self, method: str, url: httpx.URL | str, **kwargs: Any) -> httpx.Response:
        path = httpx.URL(url).path
        if path.startswith("/api") and path != "/api/auth/login":
            self._phase13_login()
            if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                headers = dict(kwargs.pop("headers", {}) or {})
                headers.setdefault("X-CSRF-Token", self._phase13_csrf or "")
                kwargs["headers"] = headers
        response = super().request(method, url, **kwargs)
        if response.status_code == 401:
            self._phase13_authenticated = False
            self._phase13_csrf = None
        if path == "/api/auth/logout" and response.is_success:
            self._phase13_authenticated = False
            self._phase13_csrf = None
        return response

    def _phase13_login(self) -> None:
        if self._phase13_authenticated:
            return
        response = super().request(
            "POST",
            "/api/auth/login",
            json={"user_id": "maya-lim", "password": TEST_PASSWORD},
        )
        response.raise_for_status()
        self._phase13_csrf = response.json()["csrf_token"]
        self._phase13_authenticated = True
