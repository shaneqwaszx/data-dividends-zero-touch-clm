"""Application configuration loaded from environment variables."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.ownership import OwnershipPercent

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPOSITORY_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings, including backend-only ACRA connector selection."""

    app_name: str = "Zero-Touch CLM API"
    app_env: Literal["development", "test", "production"] = "development"
    acra_connector_mode: Literal["mock", "sandbox"] = "mock"
    goldtier_connector_mode: Literal["mock"] = "mock"
    idp_connector_mode: Literal["mock"] = "mock"
    ownership_connector_mode: Literal["mock"] = "mock"
    demo_controls_enabled: bool = False
    zero_touch_max_transitions_per_run: int = Field(default=12, ge=1, le=32)
    idp_max_upload_bytes: int = Field(default=5 * 1024 * 1024, gt=0, le=20 * 1024 * 1024)
    idp_review_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    ubo_ownership_threshold_percent: OwnershipPercent = Decimal("25")
    ownership_max_parties: int = Field(default=100, gt=0, le=1000)
    ownership_max_relationships: int = Field(default=200, gt=0, le=2000)
    ownership_max_depth: int = Field(default=8, gt=0, le=64)
    ownership_max_paths_per_candidate: int = Field(default=64, gt=0, le=1000)
    ownership_max_total_paths: int = Field(default=256, gt=0, le=5000)
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
