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
    "202400007G",
    "202400008H",
    "202400009I",
    "202400010J",
)
SEED_PRIORITIES: tuple[int | None, ...] = (10, 8, 5, 1, None)
TEAMS = ("TEAM_A", "TEAM_B")
DIRECTOR_USER_ID = "olivia-koh"
SUCCESS_STATUS = "COMPLETED"
SUCCESS_TARGET_STATUS = "MOCK_GOLDTIER_SUBMITTED"


class SeedApi(Protocol):
    def login(self, credential: str) -> None: ...

    def list_cases(self) -> list[dict[str, Any]]: ...

    def create_case(self, team_id: str, uen: str, priority: int | None) -> str: ...

    def complete_case(self, case_id: str) -> None: ...

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
        if parsed.scheme == "http" and parsed.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }:
            raise ValueError("Plain HTTP is allowed only for the loopback POC.")
        self._base_url = base_url.rstrip("/")
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._csrf_token: str | None = None

    def login(self, credential: str) -> None:
        response = self._json_request(
            "POST",
            "/api/auth/login",
            {"user_id": DIRECTOR_USER_ID, "password": credential},
            authenticated=False,
        )
        token = response.get("csrf_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("Authentication did not return the required CSRF token.")
        self._csrf_token = token

    def list_cases(self) -> list[dict[str, Any]]:
        response = self._json_request("GET", "/api/clm/zero-touch/cases")
        if not isinstance(response, list) or not all(
            isinstance(item, dict) for item in response
        ):
            raise RuntimeError("The case list response was invalid.")
        return response

    def create_case(self, team_id: str, uen: str, priority: int | None) -> str:
        response = self._json_request(
            "POST",
            "/api/demo/clm/zero-touch/cases",
            {
                "uen": uen,
                "team_id": team_id,
                "priority": priority,
                "scenario": "STRAIGHT_THROUGH",
            },
        )
        case = response.get("case")
        case_id = case.get("case_id") if isinstance(case, dict) else None
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Case creation did not return a case identifier.")
        if case.get("team_id") != team_id or case.get("priority") != priority:
            raise RuntimeError(
                "Case creation did not retain the requested team and priority."
            )
        return case_id

    def complete_case(self, case_id: str) -> None:
        response = self._request(
            "POST",
            f"/api/demo/clm/zero-touch/cases/{case_id}/documents",
            data=_synthetic_pdf(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/pdf",
                "X-Document-Name": "phase13-synthetic-profile.pdf",
            },
        )
        clm = response.get("clm")
        if (
            response.get("status") != SUCCESS_STATUS
            or not isinstance(clm, dict)
            or clm.get("status") != SUCCESS_TARGET_STATUS
        ):
            raise RuntimeError(
                "The supported straight-through workflow did not complete."
            )

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
        return self._request(
            method,
            path,
            data=data,
            headers=headers,
            authenticated=authenticated,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None,
        headers: dict[str, str],
        authenticated: bool = True,
    ) -> Any:
        headers = dict(headers)
        if authenticated and method in {"POST", "PUT", "PATCH", "DELETE"}:
            if self._csrf_token is None:
                raise RuntimeError(
                    "Authentication is required before an unsafe request."
                )
            headers["X-CSRF-Token"] = self._csrf_token
        request = Request(
            self._base_url + path, data=data, headers=headers, method=method
        )
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
            raise RuntimeError(
                "The Phase 13 API response exceeded the safe local limit."
            )
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            raise RuntimeError("The Phase 13 API returned invalid JSON.") from None


def _synthetic_pdf() -> bytes:
    """Build one small valid fictional PDF used only by the supported demo workflow."""

    operations = "BT /F1 12 Tf 72 720 Td (SYNTHETIC PHASE 13 DEMO DATA) Tj ET"
    objects = (
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(operations)} >>\nstream\n{operations}\nendstream",
    )
    output = "%PDF-1.4\n"
    offsets: list[int] = []
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output.encode("latin-1")))
        output += f"{index} 0 obj\n{item}\nendobj\n"
    xref = len(output.encode("latin-1"))
    output += "xref\n0 6\n0000000000 65535 f \n"
    output += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    output += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return output.encode("latin-1")


def seed_demo(api: SeedApi, credential: str) -> SeedResult:
    api.login(credential)
    created = 0
    reused = 0
    prioritised = 0
    try:
        existing_items = api.list_cases()
        existing: dict[tuple[object, object], list[dict[str, Any]]] = {}
        for item in existing_items:
            existing.setdefault(
                (item.get("team_id"), item.get("requested_uen")), []
            ).append(item)
        for team_id in TEAMS:
            for uen, priority in zip(SEED_UENS, SEED_PRIORITIES, strict=True):
                candidates = existing.get((team_id, uen), [])
                current = next(
                    (
                        item
                        for item in candidates
                        if item.get("priority") == priority
                        and item.get("status") == SUCCESS_STATUS
                        and item.get("final_outcome") == SUCCESS_TARGET_STATUS
                    ),
                    candidates[0] if candidates else None,
                )
                current_id = (
                    current.get("case_id") if isinstance(current, dict) else None
                )
                if isinstance(current_id, str) and current_id:
                    case_id = current_id
                    reused += 1
                    if current.get("priority") != priority:
                        api.set_priority(case_id, priority)
                else:
                    case_id = api.create_case(team_id, uen, priority)
                    created += 1
                if (
                    not isinstance(current, dict)
                    or current.get("status") != SUCCESS_STATUS
                ):
                    api.complete_case(case_id)
                prioritised += 1
        _verify_portfolio(api.list_cases())
    finally:
        api.logout()
    return SeedResult(created=created, reused=reused, prioritised=prioritised)


def _verify_portfolio(items: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[object, object], list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault((item.get("team_id"), item.get("requested_uen")), []).append(
            item
        )
    for team_id in TEAMS:
        for uen, priority in zip(SEED_UENS, SEED_PRIORITIES, strict=True):
            matches = [
                item
                for item in grouped.get((team_id, uen), [])
                if item.get("priority") == priority
                and item.get("status") == SUCCESS_STATUS
                and item.get("final_outcome") == SUCCESS_TARGET_STATUS
            ]
            if not matches:
                raise RuntimeError(
                    "Phase 13 seed verification found a missing or incomplete showcase case."
                )


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
