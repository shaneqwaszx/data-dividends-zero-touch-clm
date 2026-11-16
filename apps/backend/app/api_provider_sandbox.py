"""HR-only, standalone GoldTier sandbox diagnostics without case access."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import RLock
from time import perf_counter
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import Settings
from app.connectors.errors import ConnectorError
from app.connectors.goldtier_models import GoldTierSearchCandidate, GoldTierSearchOutcome
from app.connectors.goldtier_xpi import (
    XPI_SEARCH_FAILURE_CODES,
    GoldTierXpiObservedStatusError,
    public_goldtier_xpi_search_error,
)
from app.connectors.goldtier_xpi_models import XpiCustomerSearchRequest
from app.domain.access import ROLE_CAPABILITIES, AuthenticatedActor, Capability
from app.domain.onboarding_intelligence import EntityResolutionOutcome
from app.domain.policy import (
    GOLDTIER_CLIENT_SEGMENT_VALUES,
    GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
    GOLDTIER_VOCABULARY_VERSION,
    AuthorityLabelledTargetValue,
    GoldTierTargetPolicySnapshot,
    PolicyAuthority,
)
from app.domain.target_preparation import GoldTierOperationPreview
from app.domain.target_submission import (
    GoldTierIdempotencyBindings,
    GoldTierProviderMode,
    GoldTierSubmissionInput,
    SubmissionCanonicalEntity,
    SubmissionRegisteredAddress,
)
from app.mappers.goldtier_xpi import GoldTierXpiRequestMapper
from app.services.errors import TargetRegistryProvenanceError
from app.services.onboarding import OnboardingService
from app.services.target_response_validation import InvalidTargetResponseError

_DIAGNOSTIC_CODE_PATTERN = r"^[A-Z0-9_]{3,64}$"
_SEARCH_FAILED_CODE = "GOLDTIER_SANDBOX_SEARCH_FAILED"
_SEARCH_FAILED_MESSAGE = "GoldTier sandbox Search could not be completed."


class SandboxDiagnosticEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: UUID
    action: Literal["STATUS", "SEARCH", "DRY_RUN", "WRITE_BLOCKED"]
    outcome: Literal["SUCCEEDED", "FAILED", "BLOCKED"]
    code: Annotated[str, Field(pattern=_DIAGNOSTIC_CODE_PATTERN)]
    occurred_at: datetime


class GoldTierSandboxStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    configured: bool
    mode: Literal["MOCK", "SANDBOX"]
    classification: Literal["MOCK", "SANDBOX_PARTIAL"]
    safe_host: str | None
    writes_enabled: bool
    daily_read_limit: int | None = Field(
        default=None, description="Configured Sandbox with null has no application read limit."
    )
    reads_used_today: int | None = None
    timeout_seconds: float
    max_response_bytes: int
    last_diagnostic_at: datetime | None
    blocker: str | None
    customer_operations: Literal["AVAILABLE", "PARTIAL"] = "PARTIAL"
    related_party_operations: Literal["BLOCKED_CONTRACT"] = "BLOCKED_CONTRACT"
    blocker_code: Literal["BLOCKED_CHILD_ID_LIFECYCLE"] = "BLOCKED_CHILD_ID_LIFECYCLE"
    required_authority: Literal["SPONSOR_CONFIRMATION"] = "SPONSOR_CONFIRMATION"
    related_party_blocker: Literal["BLOCKED_CHILD_ID_LIFECYCLE"] = "BLOCKED_CHILD_ID_LIFECYCLE"
    timeline: tuple[SandboxDiagnosticEvent, ...]
    vocabulary_version: str
    kyc_customer_types: tuple[str, ...]
    client_segments: tuple[str, ...]


class SandboxSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goldtier_id: Annotated[str | None, Field(default=None, min_length=1, max_length=96)]
    legal_name: Annotated[str | None, Field(default=None, min_length=1, max_length=240)]
    group_company_name: Annotated[str | None, Field(default=None, min_length=1, max_length=240)]
    country_of_incorporation: Annotated[str | None, Field(default=None, pattern=r"^[A-Za-z]{2}$")]


class SandboxSearchResponse(BaseModel):
    """Provider retrieval kept separate from the advisory identity assessment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    count: int = Field(ge=0, le=25)
    candidates: tuple[GoldTierSearchCandidate, ...] = Field(max_length=25)
    elapsed_ms: int = Field(ge=0)
    entity_resolution: EntityResolutionOutcome | Literal["NOT_ASSESSED"]
    error_code: Annotated[str, Field(pattern=_DIAGNOSTIC_CODE_PATTERN)] | None = None
    upstream_status: Annotated[int, Field(ge=100, le=599)] | None = None
    correlation_id: UUID


class SandboxTestValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kyc_customer_type: Annotated[str, Field(min_length=1, max_length=160)]
    client_segment: Annotated[str, Field(min_length=1, max_length=160)]
    customer_external_system: Literal["DSD"] = "DSD"
    registration_type: Literal["ACRA"] = "ACRA"
    policy: Literal["Singapore"] = "Singapore"
    booking_entity: Literal["ANZBGL (Singapore Branch)"] = "ANZBGL (Singapore Branch)"
    account_entity_type: Annotated[str, Field(max_length=160)] = ""
    product_type: Annotated[str, Field(max_length=160)] = ""

    @field_validator("kyc_customer_type")
    @classmethod
    def current_kyc_vocabulary(cls, value: str) -> str:
        if value not in GOLDTIER_KYC_CUSTOMER_TYPE_VALUES:
            raise ValueError("KYC customer type is not in the current vocabulary")
        return value

    @field_validator("client_segment")
    @classmethod
    def current_segment_vocabulary(cls, value: str) -> str:
        if value not in GOLDTIER_CLIENT_SEGMENT_VALUES:
            raise ValueError("Client segment is not in the current vocabulary")
        return value


class SandboxDryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search: SandboxSearchRequest
    test_values: SandboxTestValues


class SandboxDryRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operations: tuple[GoldTierOperationPreview, ...]
    dispatch_ready: bool
    blocker: str | None


class SandboxWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: Literal["SANDBOX_TEST_ONLY"]


def build_provider_sandbox_router(
    onboarding: OnboardingService,
    settings: Settings,
) -> APIRouter:
    """Build a capability-gated diagnostics router with bounded process-local history."""

    router = APIRouter(prefix="/api/admin/goldtier-sandbox", tags=["provider-sandbox"])
    timeline: deque[SandboxDiagnosticEvent] = deque(maxlen=25)
    timeline_guard = RLock()

    def record(
        action: Literal["STATUS", "SEARCH", "DRY_RUN", "WRITE_BLOCKED"],
        outcome: Literal["SUCCEEDED", "FAILED", "BLOCKED"],
        code: str,
    ) -> None:
        with timeline_guard:
            timeline.append(
                SandboxDiagnosticEvent(
                    event_id=uuid4(),
                    action=action,
                    outcome=outcome,
                    code=code,
                    occurred_at=datetime.now(UTC),
                )
            )

    def snapshot() -> tuple[SandboxDiagnosticEvent, ...]:
        with timeline_guard:
            return tuple(item.model_copy(deep=True) for item in timeline)

    @router.get("/status", response_model=GoldTierSandboxStatusResponse)
    def sandbox_status(request: Request) -> GoldTierSandboxStatusResponse:
        _require_provider_sandbox_test(request)
        configured = (
            settings.goldtier_connector_mode == "sandbox"
            and onboarding.target_provider_mode == GoldTierProviderMode.SANDBOX
        )
        writes_open = settings.goldtier_sandbox_write_policy().open_at(datetime.now(UTC))
        blocker = (
            "GOLDTIER_SANDBOX_NOT_CONFIGURED"
            if not configured
            else "GOLDTIER_SANDBOX_WRITES_DISABLED"
            # D-137: reports the live write window, so an ended window reads as disabled.
            if not writes_open
            else "GOLDTIER_SANDBOX_WRITE_REQUIRES_CASE_LEDGER"
        )
        current = snapshot()
        read_limit, reads_used = (
            onboarding.target_read_budget_usage(datetime.now(UTC)) if configured else (None, None)
        )
        return GoldTierSandboxStatusResponse(
            configured=configured,
            mode="SANDBOX" if configured else "MOCK",
            classification="SANDBOX_PARTIAL" if configured else "MOCK",
            safe_host=(
                urlsplit(settings.goldtier_sandbox_base_url).hostname if configured else None
            ),
            writes_enabled=configured and writes_open,
            daily_read_limit=read_limit,
            reads_used_today=reads_used,
            timeout_seconds=settings.goldtier_sandbox_timeout_seconds,
            max_response_bytes=settings.goldtier_sandbox_max_response_bytes,
            last_diagnostic_at=(current[-1].occurred_at if current else None),
            blocker=blocker,
            timeline=current,
            vocabulary_version=GOLDTIER_VOCABULARY_VERSION,
            kyc_customer_types=GOLDTIER_KYC_CUSTOMER_TYPE_VALUES,
            client_segments=GOLDTIER_CLIENT_SEGMENT_VALUES,
        )

    @router.post("/search", response_model=SandboxSearchResponse)
    def sandbox_search(body: SandboxSearchRequest, request: Request) -> SandboxSearchResponse:
        _require_provider_sandbox_test(request)
        if settings.goldtier_connector_mode != "sandbox":
            record("SEARCH", "BLOCKED", "GOLDTIER_SANDBOX_NOT_CONFIGURED")
            _raise_conflict(
                "GOLDTIER_SANDBOX_NOT_CONFIGURED",
                "GoldTier sandbox Search is not configured.",
            )
        try:
            criteria = XpiCustomerSearchRequest.model_validate(body.model_dump())
        except ValueError:
            record("SEARCH", "FAILED", "GOLDTIER_SANDBOX_SEARCH_INVALID")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "GOLDTIER_SANDBOX_SEARCH_INVALID",
                    "message": "At least one valid bounded Search criterion is required.",
                },
            ) from None
        correlation_id = uuid4()
        started = perf_counter()

        def search_failure(
            code: str, message: str, upstream_status: int | None = None
        ) -> HTTPException:
            record("SEARCH", "FAILED", code)
            detail: dict[str, object] = {
                "code": code,
                "message": message,
                "correlation_id": str(correlation_id),
                "elapsed_ms": _elapsed_ms(started),
            }
            if upstream_status is not None:
                detail["upstream_status"] = upstream_status
            return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

        try:
            evidence = onboarding.search_sandbox_target(criteria, correlation_id=correlation_id)
        except TargetRegistryProvenanceError as exc:
            record("SEARCH", "BLOCKED", "GOLDTIER_SANDBOX_SEARCH_IDENTITY_UNVERIFIED")
            _raise_conflict("GOLDTIER_SANDBOX_SEARCH_IDENTITY_UNVERIFIED", exc.public_message)
            raise
        except ConnectorError as exc:
            public = public_goldtier_xpi_search_error(exc)
            observed = (
                exc.upstream_status if isinstance(exc, GoldTierXpiObservedStatusError) else None
            )
            raise search_failure(public.code, public.message, observed) from None
        except InvalidTargetResponseError:
            raise search_failure(
                "GT_XPI_MALFORMED_RESPONSE",
                "The GoldTier sandbox returned an unexpected response.",
            ) from None
        except Exception:
            raise search_failure(_SEARCH_FAILED_CODE, _SEARCH_FAILED_MESSAGE) from None
        result = evidence.result
        failed = result.outcome == GoldTierSearchOutcome.FAILURE
        error_code: str | None = None
        if failed:
            # Only the connector's fixed controlled-failure codes are projected.
            error_code = (
                result.error_code
                if result.error_code in XPI_SEARCH_FAILURE_CODES
                else _SEARCH_FAILED_CODE
            )
            record("SEARCH", "FAILED", error_code)
        else:
            record("SEARCH", "SUCCEEDED", f"GOLDTIER_SANDBOX_SEARCH_{result.outcome.value}")
        resolution = None if failed else evidence.resolution
        return SandboxSearchResponse(
            status=result.outcome.value,
            count=len(result.candidates),
            candidates=result.candidates,
            elapsed_ms=_elapsed_ms(started),
            entity_resolution="NOT_ASSESSED" if resolution is None else resolution.outcome,
            error_code=error_code,
            upstream_status=result.status_code,
            correlation_id=correlation_id,
        )

    @router.post("/dry-run", response_model=SandboxDryRunResponse)
    def sandbox_dry_run(body: SandboxDryRunRequest, request: Request) -> SandboxDryRunResponse:
        _require_provider_sandbox_test(request)
        if body.search.legal_name is None or body.search.country_of_incorporation is None:
            record("DRY_RUN", "FAILED", "GOLDTIER_SANDBOX_DRY_RUN_INVALID")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "GOLDTIER_SANDBOX_DRY_RUN_INVALID",
                    "message": "Dry-run requires legal name and country of incorporation.",
                },
            )
        preview = GoldTierXpiRequestMapper().build_preview(_submission_for(body))
        record("DRY_RUN", "SUCCEEDED", "GOLDTIER_SANDBOX_DRY_RUN_READY")
        return SandboxDryRunResponse(
            operations=preview.operations,
            dispatch_ready=preview.dispatch_ready,
            blocker=None if preview.dispatch_ready else "GOLDTIER_SANDBOX_VALUES_INCOMPLETE",
        )

    @router.post("/write", status_code=status.HTTP_409_CONFLICT)
    def sandbox_write(body: SandboxWriteRequest, request: Request) -> None:
        del body
        _require_provider_sandbox_test(request)
        record("WRITE_BLOCKED", "BLOCKED", "GOLDTIER_SANDBOX_WRITE_REQUIRES_CASE_LEDGER")
        _raise_conflict(
            "GOLDTIER_SANDBOX_WRITE_REQUIRES_CASE_LEDGER",
            "Standalone sandbox writes are blocked until a case-bound durable ledger is available.",
        )

    return router


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


def _submission_for(body: SandboxDryRunRequest) -> GoldTierSubmissionInput:
    generated = tuple(uuid4() for _ in range(7))
    authority = PolicyAuthority.SANDBOX_TEST_ONLY
    labelled = {
        name: AuthorityLabelledTargetValue(
            value=value or "TBD_SPONSOR",
            authority=authority,
        )
        for name, value in body.test_values.model_dump().items()
    }
    country = body.search.country_of_incorporation
    legal_name = body.search.legal_name
    if country is None or legal_name is None:
        raise ValueError("Dry-run identity is incomplete")
    return GoldTierSubmissionInput(
        submission_id=generated[0],
        case_id=generated[1],
        source_case_id="SANDBOX-CONSOLE",
        correlation_id=generated[2],
        accepted_at=datetime.now(UTC),
        provider_mode=GoldTierProviderMode.SANDBOX,
        policy_catalogue_version=0,
        target_external_key="SANDBOX-TEST-0001",
        target_policy=GoldTierTargetPolicySnapshot(**labelled),
        canonical_entity=SubmissionCanonicalEntity(
            registration_number="SANDBOX-TEST-0001",
            legal_name=legal_name,
            country_of_incorporation=country.upper(),
            party_type="ORGANISATION",
            registered_address=SubmissionRegisteredAddress(
                address_line_1="1 TEST STREET",
                postal_code="000000",
                country_code=country.upper(),
            ),
        ),
        idempotency=GoldTierIdempotencyBindings(
            search=generated[3],
            shell=generated[4],
            policy=generated[5],
            amend=generated[6],
        ),
    )


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


def _raise_conflict(code: str, message: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": code, "message": message},
    )
