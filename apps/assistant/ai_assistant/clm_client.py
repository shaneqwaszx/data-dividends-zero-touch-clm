"""Read-only client for the existing CLM backend APIs.

The AI assistant never holds its own credentials. It forwards the RM's session cookie, so the
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
    """Everything the AI assistant read for one question, fetched together."""

    summary: dict[str, Any]
    documents: list[dict[str, Any]]
    actor: dict[str, Any]
    # False when the document list could not be read (it is then empty). Answers carry on
    # without documents; the D-094 synthetic boundary refuses remote use.
    documents_loaded: bool = True
    # D-142 R2: the case as external inference may receive it under the pseudonymised policy
    # (synthetic_eligibility.PocView: unverified uploads withheld), set by the hosted service
    # when it is read; None otherwise. Memory only.
    poc_view: Any = None


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

    def load_actor(self, session_token: str | None) -> dict[str, Any]:
        """Who is signed in (role, team, capabilities), as the backend reports it."""

        with self._client(session_token) as client:
            actor = self._get(client, "/api/auth/me")
        if not isinstance(actor, dict) or not isinstance(actor.get("profile"), dict):
            raise ClmBackendError(
                502, "CLM_BACKEND_ERROR", "The onboarding app returned an unexpected reply."
            )
        return actor

    def list_cases(self, session_token: str | None) -> list[Any]:
        """The cases this user may see in the portfolio list, as the backend reports them (GET
        only, the user's own session). Used only for hosted dashboard insights, which keep the
        R2.1-eligible ones."""

        with self._client(session_token) as client:
            cases = self._get(client, "/api/clm/zero-touch/cases")
        return cases if isinstance(cases, list) else []

    def load_policies(self, session_token: str | None) -> dict[str, Any] | None:
        """D-105: the active policy catalogue as the backend shows it to this user (GET only),
        or None when it cannot be read."""

        try:
            with self._client(session_token) as client:
                catalogue = self._get(client, "/api/policies")
        except ClmBackendError as exc:
            if exc.code == "AUTHENTICATION_REQUIRED":
                raise
            return None
        return catalogue if isinstance(catalogue, dict) else None

    def load_document_digests(
        self, case_id: UUID, session_token: str | None
    ) -> list[dict[str, Any]] | None:
        """D-095: the SHA-256 the backend computed from each document's uploaded bytes (its
        case-scoped document-digests route), or None when it cannot be read. Read only for
        the remote model's synthetic eligibility check, never shown or sent anywhere."""

        try:
            with self._client(session_token) as client:
                digests = self._get(client, f"/api/onboarding/cases/{case_id}/document-digests")
        except ClmBackendError:
            return None
        if not isinstance(digests, list) or not all(isinstance(item, dict) for item in digests):
            return None
        return digests

    def load_ownership(self, case_id: UUID, session_token: str | None) -> dict[str, Any] | None:
        """D-115: the application's ownership analysis of this case, through the backend's
        case-scoped ownership route with this user's session (GET only), or None when there is
        none or it cannot be read. Read for copilot answers with a local model only."""

        try:
            with self._client(session_token) as client:
                analysis = self._get(client, f"/api/onboarding/cases/{case_id}/ownership")
        except ClmBackendError as exc:
            if exc.code == "AUTHENTICATION_REQUIRED":
                raise
            return None
        return analysis if isinstance(analysis, dict) else None

    def load_case(self, case_id: UUID, session_token: str | None) -> CaseSnapshot:
        with self._client(session_token) as client:
            actor = self._get(client, "/api/auth/me")
            summary = self._get(client, f"/api/clm/zero-touch/cases/{case_id}")
            loaded = True
            try:
                documents = self._get(client, f"/api/onboarding/cases/{case_id}/documents")
            except ClmBackendError as exc:
                if exc.code == "AUTHENTICATION_REQUIRED":
                    raise
                documents, loaded = [], False
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
            documents_loaded=loaded and isinstance(documents, list),
        )
