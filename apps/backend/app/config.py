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
PHASE13_LOCAL_BROWSER_ORIGINS = frozenset({"http://127.0.0.1:8000", "http://127.0.0.1:5173"})


class Settings(BaseSettings):
    """Application settings, including backend-only ACRA connector selection."""

    app_name: str = "Zero-Touch CLM API"
    app_env: Literal["development", "test", "production"] = "development"
    acra_connector_mode: Literal["mock", "sandbox", "bizfile_mock"] = "mock"
    goldtier_connector_mode: Literal["mock"] = "mock"
    idp_connector_mode: Literal["mock", "local_pdf_text"] = "local_pdf_text"
    ownership_connector_mode: Literal["mock"] = "mock"
    demo_controls_enabled: bool = False
    zero_touch_max_transitions_per_run: int = Field(default=12, ge=1, le=32)
    idp_max_upload_bytes: int = Field(default=5 * 1024 * 1024, gt=0, le=20 * 1024 * 1024)
    idp_max_files_per_case: int = Field(default=20, ge=1, le=20)
    idp_max_total_intake_bytes: int = Field(default=25 * 1024 * 1024, gt=0, le=100 * 1024 * 1024)
    idp_review_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    ubo_ownership_threshold_percent: OwnershipPercent = Decimal("25")
    ownership_max_parties: int = Field(default=100, gt=0, le=1000)
    ownership_max_relationships: int = Field(default=200, gt=0, le=2000)
    ownership_max_depth: int = Field(default=8, gt=0, le=64)
    ownership_max_paths_per_candidate: int = Field(default=64, gt=0, le=1000)
    ownership_max_total_paths: int = Field(default=256, gt=0, le=5000)
    clm_persistence_mode: Literal["memory", "mongo"] = "memory"
    acra_base_url: str = ""
    acra_company_path_template: str = ""
    acra_timeout_seconds: float = 10.0
    acra_auth_header_name: str = ""
    acra_auth_header_value: SecretStr | None = None
    mongo_uri: SecretStr | None = None
    mongo_database: str = Field(
        default="clm_poc", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )
    mongo_case_collection: str = Field(
        default="clm_case_snapshots",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    mongo_admin_teams_collection: str = Field(
        default="clm_admin_teams",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    mongo_admin_profiles_collection: str = Field(
        default="clm_admin_profiles",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    mongo_admin_policies_collection: str = Field(
        default="clm_admin_policies",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    phase13_maya_lim_password_hash: SecretStr | None = None
    phase13_ethan_tan_password_hash: SecretStr | None = None
    phase13_sophia_ng_password_hash: SecretStr | None = None
    phase13_ryan_lee_password_hash: SecretStr | None = None
    phase13_olivia_koh_password_hash: SecretStr | None = None
    phase14_5_hr_admin_password_hash: SecretStr | None = None
    phase14_5_max_active_sessions: int = Field(default=256, ge=1, le=1000)
    phase13_cookie_secure: bool | None = None
    phase13_browser_origin: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def phase13_trusted_browser_origins(self) -> frozenset[str]:
        """Return configured browser origins without consulting request metadata."""

        if self.app_env in {"development", "test"}:
            configured = (
                frozenset({self.phase13_browser_origin})
                if self.phase13_browser_origin is not None
                else frozenset()
            )
            return PHASE13_LOCAL_BROWSER_ORIGINS | configured
        if self.phase13_browser_origin is None:
            raise ValueError("PHASE13_BROWSER_ORIGIN is required in the production environment")
        return frozenset({self.phase13_browser_origin})


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""

    return Settings()