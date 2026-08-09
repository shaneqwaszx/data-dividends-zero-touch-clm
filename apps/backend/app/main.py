"""FastAPI application entry point."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import Settings, get_settings


class HealthResponse(BaseModel):
    """Public, non-sensitive service health response."""

    status: Literal["ok"]
    service: str
    environment: str


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application with injectable settings for deterministic tests."""

    active_settings = settings or get_settings()
    application = FastAPI(title=active_settings.app_name, version="0.1.0")

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=active_settings.app_name,
            environment=active_settings.app_env,
        )

    return application


app = create_app()
