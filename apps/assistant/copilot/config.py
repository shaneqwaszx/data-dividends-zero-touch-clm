"""Copilot settings, read from COPILOT_* environment variables or apps/assistant/.env."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CopilotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COPILOT_", env_file=".env", extra="ignore")

    # The CLM backend the copilot reads from. The RM's own session is forwarded, so the
    # backend still decides what this user may see.
    clm_backend_url: str = "http://127.0.0.1:8000"
    backend_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    # Any OpenAI-compatible chat API: Ollama locally by default, or a cloud provider later.
    llm_enabled: bool = True
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "ministral-3:8b"
    llm_api_key: SecretStr = SecretStr("ollama")
    llm_timeout_seconds: float = Field(default=90.0, gt=0, le=600)
    llm_temperature: float = Field(default=0.2, ge=0, le=1)

    # Browser pages allowed to call the copilot (the Vite dev server by default).
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    max_history_messages: int = Field(default=8, ge=0, le=20)
    max_question_chars: int = Field(default=600, ge=20, le=4000)
