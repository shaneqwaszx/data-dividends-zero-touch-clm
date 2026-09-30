"""HR-only read-only ACRA diagnostic routes without case or ledger access."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.domain.jurisdiction import is_eligible_singapore_uen
from app.services.acra_diagnostics import (
    AcraDiagnosticOperation,
    AcraDiagnosticResult,
    AcraDiagnosticService,
    AcraDiagnosticStatus,
)


class AcraDiagnosticLookupRequest(BaseModel):
    """Bounded operation and Singapore identifier; provider location is server-owned."""

    model_config = ConfigDict(extra="forbid")

    uen: Annotated[str, Field(min_length=9, max_length=10, pattern=r"^[A-Z0-9]+$")]
    operation: AcraDiagnosticOperation

    @field_validator("uen", mode="before")
    @classmethod
    def normalize_uen(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("uen")
    @classmethod
    def require_supported_singapore_identifier(cls, value: str) -> str:
        if not is_eligible_singapore_uen(value):
            raise ValueError("A valid Singapore UEN is required")
        return value


def build_acra_diagnostic_router(service: AcraDiagnosticService) -> APIRouter:
    """Expose safe diagnostics with capability enforcement at the route boundary."""

    router = APIRouter(prefix="/api/admin/acra", tags=["provider-sandbox"])

    @router.get("/status", response_model=AcraDiagnosticStatus)
    def diagnostic_status(request: Request) -> AcraDiagnosticStatus:
        _require_provider_sandbox_test(request)
        try:
            return service.status()
        except Exception:
            raise _safe_diagnostic_failure() from None

    @router.post("/lookup", response_model=AcraDiagnosticResult)
    def diagnostic_lookup(
        body: AcraDiagnosticLookupRequest,
        request: Request,
    ) -> AcraDiagnosticResult:
        _require_provider_sandbox_test(request)
        try:
            return service.run(body.uen, body.operation)
        except Exception:
            raise _safe_diagnostic_failure() from None

    return router


def _require_provider_sandbox_test(request: Request) -> AuthenticatedActor:
    actor = getattr(request.state, "actor", None)
    if not isinstance(actor, AuthenticatedActor):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_REQUIRED",
                "message": "A valid authenticated session is required.",
            },
        )
    if Capability.PROVIDER_SANDBOX_TEST not in ROLE_CAPABILITIES[actor.profile.role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PROVIDER_SANDBOX_TEST_FORBIDDEN",
                "message": "Provider sandbox testing is not permitted.",
            },
        )
    return actor


def _safe_diagnostic_failure() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "ACRA_DIAGNOSTIC_UNAVAILABLE",
            "message": "The ACRA diagnostic could not be completed.",
        },
    )
