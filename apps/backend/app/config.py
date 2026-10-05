"""Application configuration loaded from environment variables."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.ownership import OwnershipPercent

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPOSITORY_ROOT / ".env"
PHASE13_LOCAL_BROWSER_ORIGINS = frozenset({"http://127.0.0.1:8000", "http://127.0.0.1:5173"})


class Settings(BaseSettings):
    """Application settings, including backend-only ACRA connector selection."""

    app_name: str = "Zero-Touch CLM API"
    app_env: Literal["development", "test", "production"] = "development"
    acra_connector_mode: Literal["mock", "api_marketplace_mock", "sandbox"] = "mock"
    goldtier_connector_mode: Literal["mock", "sandbox"] = "mock"
    idp_connector_mode: Literal["mock", "local_pdf_text"] = "local_pdf_text"
    local_ocr_executable: str | None = Field(default=None, max_length=512)
    local_ocr_timeout_seconds: float = Field(default=12.0, gt=0, le=20.0)
    garden_supplement_enabled: bool = False
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
    registry_cache_mode: Literal["auto", "disabled", "mock"] = "auto"
    registry_cache_freshness_seconds: int | None = None
    acra_base_url: str = ""
    acra_company_path_template: str = ""
    acra_timeout_seconds: float = Field(default=10.0, gt=0, le=30.0)
    acra_auth_header_name: str = ""
    acra_auth_header_value: SecretStr | None = None
    acra_api_marketplace_mock_client_id: SecretStr | None = None
    acra_api_marketplace_mock_secret_key: SecretStr | None = None
    goldtier_sandbox_base_url: str = ""
    goldtier_sandbox_environment: str = Field(
        default="", pattern=r"^(?:|[A-Za-z0-9][A-Za-z0-9_-]{0,31})$"
    )
    goldtier_sandbox_user_id: SecretStr | None = None
    goldtier_sandbox_timeout_seconds: float = Field(default=10.0, gt=0, le=30.0)
    goldtier_sandbox_max_response_bytes: int = Field(default=128 * 1024, ge=1024, le=1024 * 1024)
    goldtier_sandbox_allow_writes: bool = False
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
    mongo_registry_cache_collection: str = Field(
        default="clm_registry_snapshots",
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

    @field_validator("local_ocr_executable")
    @classmethod
    def validate_local_ocr_executable(cls, value: str | None) -> str | None:
        if value is None:
            return None
        path = Path(value)
        if (
            not path.is_absolute()
            or path.name.casefold() not in {"tesseract", "tesseract.exe"}
            or value.startswith(("\\\\", "//"))
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError("Local OCR requires an absolute local Tesseract executable path.")
        return value

    @model_validator(mode="after")
    def validate_garden_supplement(self) -> "Settings":
        if self.garden_supplement_enabled and self.acra_connector_mode != "api_marketplace_mock":
            raise ValueError(
                "Garden supplement requires the explicit official Marketplace Mock lane."
            )
        return self

    @field_validator("acra_connector_mode", mode="before")
    @classmethod
    def validate_acra_connector_mode(cls, value: object) -> object:
        supported = {"mock", "api_marketplace_mock", "sandbox"}
        if not isinstance(value, str) or value not in supported:
            raise ValueError(
                "Unsupported ACRA connector mode. Current supported modes include "
                "api_marketplace_mock for the official Marketplace Mock."
            )
        return value

    @property
    def registry_cache_enabled(self) -> bool:
        return self.registry_cache_mode == "mock" or (
            self.registry_cache_mode == "auto"
            and self.app_env != "production"
            and self.acra_connector_mode in {"mock", "api_marketplace_mock"}
        )

    @model_validator(mode="after")
    def validate_registry_cache(self) -> "Settings":
        if self.registry_cache_mode == "mock":
            if self.acra_connector_mode not in {"mock", "api_marketplace_mock"}:
                raise ValueError("registry cache is supported only for explicit Mock ACRA lanes")
            if self.registry_cache_freshness_seconds != 7_776_000:
                raise ValueError("enabled Mock registry cache requires 7,776,000 freshness seconds")
        if self.registry_cache_enabled:
            if self.registry_cache_freshness_seconds not in {None, 7_776_000}:
                raise ValueError("Mock registry cache baseline requires 7,776,000 seconds")
            collections = {
                self.mongo_case_collection,
                self.mongo_admin_teams_collection,
                self.mongo_admin_profiles_collection,
                self.mongo_admin_policies_collection,
                self.mongo_registry_cache_collection,
            }
            if len(collections) != 5:
                raise ValueError("registry cache collection must be distinct")
        if self.goldtier_connector_mode == "sandbox":
            parsed = urlsplit(self.goldtier_sandbox_base_url)
            valid_base = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.path in {"", "/"}
                and not parsed.query
                and not parsed.fragment
            )
            user_id = (
                self.goldtier_sandbox_user_id.get_secret_value()
                if self.goldtier_sandbox_user_id is not None
                else ""
            )
            if (
                self.app_env == "production"
                or not valid_base
                or not self.goldtier_sandbox_environment
                or not user_id
                or len(user_id) > 160
                or any(ord(character) < 32 for character in user_id)
            ):
                raise ValueError("GoldTier sandbox configuration is incomplete or unsafe")
        if self.acra_connector_mode == "api_marketplace_mock" and self.app_env == "production":
            raise ValueError("ACRA API Marketplace Mock is non-production only")
        return self

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
