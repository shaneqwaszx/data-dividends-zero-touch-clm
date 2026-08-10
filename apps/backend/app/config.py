"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPOSITORY_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings, including backend-only ACRA connector selection."""

    app_name: str = "Zero-Touch CLM API"
    app_env: Literal["development", "test", "production"] = "development"
    acra_connector_mode: Literal["mock", "sandbox"] = "mock"
    goldtier_connector_mode: Literal["mock"] = "mock"
    idp_connector_mode: Literal["mock"] = "mock"
    idp_max_upload_bytes: int = Field(default=5 * 1024 * 1024, gt=0, le=20 * 1024 * 1024)
    idp_review_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    acra_base_url: str = ""
    acra_company_path_template: str = ""
    acra_timeout_seconds: float = 10.0
    acra_auth_header_name: str = ""
    acra_auth_header_value: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()
