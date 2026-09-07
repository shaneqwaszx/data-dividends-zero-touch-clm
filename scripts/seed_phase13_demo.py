"""Seed the Phase 13 synthetic team portfolios through authenticated application APIs."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

SEED_UENS = (
    "202400001A",
    "202400002B",
    "202400007G",
    "202400008H",
    "202400009I",
)
SEED_PRIORITIES: tuple[int | None, ...] = (10, 8, 5, 1, None)
TEAMS = ("TEAM_A", "TEAM_B")


class SeedApi(Protocol):
    def login(self, credential: str) -> None: ...

    def list_cases(self) -> list[dict[str, Any]]: ...

    def create_case(self, team_id: str, uen: str) -> str: ...

    def set_priority(self, case_id: str, priority: int | None) -> None: ...

    def logout(self) -> None: ...


@dataclass(frozen=True)
class SeedResult:
    created: int
    reused: int
    prioritised: int


class HttpSeedApi:
    def __init__(self, base_url: str) -> None:
        parsed = urlsplit(base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Base URL must be an absolute HTTP(S) URL.")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Plain HTTP is allowed only for the loopback POC.")
        self._base_url = base_url.rstrip("/")
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._csrf_token: str | None = None

    def login(self, credential: str) -> None:
        response = self._json_request(
            "POST",
            "/api/auth/login",
            {"user_id": "director", "password": credential},
            authenticated=False,
        )
        token = response.get("csrf_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Authentication did not return the required CSRF token.")
        self._csrf_token = token

    def list_cases(self) -> list[dict[str, Any]]:
        response = self._json_request("GET", "/api/clm/zero-touch/cases")
        if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
            raise RuntimeError("The case list response was invalid.")
        return response

    def create_case(self, team_id: str, uen: str) -> str:
        response = self._json_request(
            "POST",
            "/api/demo/clm/zero-touch/cases",
            {"uen": uen, "team_id": team_id, "scenario": "STRAIGHT_THROUGH"},
        )
        case = response.get("case")
        case_id = case.get("case_id") if isinstance(case, dict) else None
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Case creation did not return a case identifier.")
        return case_id

    def set_priority(self, case_id: str, priority: int | None) -> None:
        self._json_request(
            "PATCH",
            f"/api/clm/zero-touch/cases/{case_id}/priority",
            {"priority": priority},
        )

    def logout(self) -> None:
        self._json_request("POST", "/api/auth/logout")
        self._csrf_token = None

    def _json_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated and method in {"POST", "PUT", "PATCH", "DELETE"}:
            if self._csrf_token is None:
                raise RuntimeError("Authentication is required before an unsafe request.")
            headers["X-CSRF-Token"] = self._csrf_token
        request = Request(self._base_url + path, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=15) as response:
                raw = response.read(1_048_577)
        except HTTPError as exc:
            raise RuntimeError(
                f"The Phase 13 API rejected the request with HTTP {exc.code}."
            ) from None
        except URLError:
            raise RuntimeError("The Phase 13 API could not be reached.") from None
        if len(raw) > 1_048_576:
            raise RuntimeError("The Phase 13 API response exceeded the safe local limit.")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            raise RuntimeError("The Phase 13 API returned invalid JSON.") from None


def seed_demo(api: SeedApi, credential: str) -> SeedResult:
    api.login(credential)
    created = 0
    reused = 0
    prioritised = 0
    try:
        existing = {
            (item.get("team_id"), item.get("requested_uen")): item.get("case_id")
            for item in api.list_cases()
        }
        for team_id in TEAMS:
            for uen, priority in zip(SEED_UENS, SEED_PRIORITIES, strict=True):
                current = existing.get((team_id, uen))
                if isinstance(current, str) and current:
                    case_id = current
                    reused += 1
                else:
                    case_id = api.create_case(team_id, uen)
                    created += 1
                api.set_priority(case_id, priority)
                prioritised += 1
    finally:
        api.logout()
    return SeedResult(created=created, reused=reused, prioritised=prioritised)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    credential = getpass.getpass("Director POC credential: ")
    if not credential:
        print("A Director password is required.", file=sys.stderr)
        return 1
    try:
        result = seed_demo(HttpSeedApi(args.base_url), credential)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Phase 13 synthetic seed complete: {result.created} created, "
        f"{result.reused} reused, {result.prioritised} priorities applied."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
