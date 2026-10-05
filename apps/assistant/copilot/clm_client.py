"""Read-only client for the existing CLM backend APIs.

The copilot never holds its own credentials. It forwards the RM's session cookie, so the
backend keeps deciding what this person may see (RBAC, team scope, safe 404s). Only GET
requests are made: Phase 1 never changes a case.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

SESSION_COOKIE_NAME = "clm_session"


class ClmBackendError(Exception):
    """A safe, user-presentable failure to read from the CLM backend."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CaseSnapshot:
    """Everything the copilot read for one question, fetched together."""

    summary: dict[str, Any]
    documents: list[dict[str, Any]]
    actor: dict[str, Any]


class ClmBackendClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._transport = transport

    def _get(self, client: httpx.Client, path: str) -> Any:
        try:
            response = client.get(path)
        except httpx.HTTPError:
            raise ClmBackendError(
                502, "CLM_BACKEND_UNREACHABLE", "The onboarding app could not be reached."
            ) from None
        if response.status_code == 401:
            raise ClmBackendError(401, "AUTHENTICATION_REQUIRED", "Please sign in again.")
        if response.status_code in {403, 404}:
            raise ClmBackendError(404, "CASE_NOT_FOUND", "This case was not found.")
        if response.status_code != 200:
            raise ClmBackendError(
                502, "CLM_BACKEND_ERROR", "The onboarding app could not provide this case."
            )
        try:
            return response.json()
        except ValueError:
            raise ClmBackendError(
                502, "CLM_BACKEND_ERROR", "The onboarding app returned an unreadable reply."
            ) from None

    def _client(self, session_token: str | None) -> httpx.Client:
        if not session_token:
            raise ClmBackendError(401, "AUTHENTICATION_REQUIRED", "Please sign in again.")
        return httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout,
            cookies={SESSION_COOKIE_NAME: session_token},
            transport=self._transport,
            headers={"Accept": "application/json"},
        )

    def load_case(self, case_id: UUID, session_token: str | None) -> CaseSnapshot:
        with self._client(session_token) as client:
            actor = self._get(client, "/api/auth/me")
            summary = self._get(client, f"/api/clm/zero-touch/cases/{case_id}")
            try:
                documents = self._get(client, f"/api/onboarding/cases/{case_id}/documents")
            except ClmBackendError as exc:
                if exc.code == "AUTHENTICATION_REQUIRED":
                    raise
                documents = []
        if not isinstance(summary, dict) or not isinstance(actor, dict):
            raise ClmBackendError(
                502, "CLM_BACKEND_ERROR", "The onboarding app returned an unexpected reply."
            )
        return CaseSnapshot(
            summary=summary,
            documents=[item for item in documents if isinstance(item, dict)]
            if isinstance(documents, list)
            else [],
            actor=actor,
        )
