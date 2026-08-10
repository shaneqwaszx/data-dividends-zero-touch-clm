"""FastAPI application and Phase 02 application-facing endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.api_models import OnboardingCaseResponse
from app.composition import (
    build_acra_connector as build_acra_connector,
)
from app.composition import (
    build_onboarding_service,
)
from app.config import Settings, get_settings
from app.demo.scenarios import (
    MockScenarioCatalogue,
    MockScenarioDiscovery,
    Phase01MockScenarioCatalogue,
)
from app.services.errors import OnboardingInfrastructureError
from app.services.onboarding import OnboardingService


class HealthResponse(BaseModel):
    """Public, non-sensitive service health response."""

    status: Literal["ok"]
    service: str
    environment: str


class StartOnboardingRequest(BaseModel):
    """Small application-facing input; external target DTOs stay behind connectors."""

    uen: Annotated[str, Field(min_length=10, max_length=10, pattern=r"^[0-9]{9}[A-Z]$")]

    @field_validator("uen", mode="before")
    @classmethod
    def normalize_uen(cls, value: object) -> object:
        """Apply Phase 01 demo normalization before validation and case creation."""

        if isinstance(value, str):
            normalized = value.strip().upper()
            if not normalized:
                raise ValueError("UEN must not be blank")
            return normalized
        return value


class InfrastructureFailureDetail(BaseModel):
    """Safe retrievable-case metadata returned for unexpected stage failures."""

    code: str
    message: str
    case_id: UUID
    correlation_id: UUID


def create_app(
    settings: Settings | None = None,
    onboarding_service: OnboardingService | None = None,
    scenario_catalogue: MockScenarioCatalogue | None = None,
) -> FastAPI:
    """Build the application with injectable settings for deterministic tests."""

    active_settings = settings or get_settings()
    application = FastAPI(title=active_settings.app_name, version="0.1.0")
    catalogue = scenario_catalogue or Phase01MockScenarioCatalogue()
    service = onboarding_service or build_onboarding_service(catalogue, active_settings)

    def get_onboarding_service() -> OnboardingService:
        return service

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=active_settings.app_name,
            environment=active_settings.app_env,
        )

    @application.get(
        "/api/onboarding/mock-scenarios",
        response_model=MockScenarioDiscovery,
        tags=["onboarding"],
    )
    def mock_scenarios() -> MockScenarioDiscovery:
        registry_environment: Literal["MOCK", "SANDBOX"] = (
            "MOCK" if active_settings.acra_connector_mode == "mock" else "SANDBOX"
        )
        return catalogue.discovery(registry_environment)

    @application.post(
        "/api/onboarding/cases",
        response_model=OnboardingCaseResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["onboarding"],
    )
    def create_onboarding_case(
        request: StartOnboardingRequest,
        active_service: Annotated[OnboardingService, Depends(get_onboarding_service)],
    ) -> OnboardingCaseResponse:
        try:
            return OnboardingCaseResponse.from_domain(active_service.create_case(request.uen))
        except OnboardingInfrastructureError as exc:
            detail = InfrastructureFailureDetail(
                code=exc.code,
                message=exc.public_message,
                case_id=exc.case_id,
                correlation_id=exc.correlation_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail.model_dump(mode="json"),
            ) from None

    @application.get(
        "/api/onboarding/cases/{case_id}",
        response_model=OnboardingCaseResponse,
        tags=["onboarding"],
    )
    def get_onboarding_case(
        case_id: UUID,
        active_service: Annotated[OnboardingService, Depends(get_onboarding_service)],
    ) -> OnboardingCaseResponse:
        case = active_service.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Onboarding case not found")
        return OnboardingCaseResponse.from_domain(case)

    return application


app = create_app()
