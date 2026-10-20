"""AI Assistant settings, read from AI_ASSISTANT_* environment variables or apps/assistant/.env."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiAssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_ASSISTANT_", env_file=".env", extra="ignore")

    # The CLM backend the AI assistant reads from. The RM's own session is forwarded, so the
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
    # Safety limit on answer length, well above a normal answer: it only stops a runaway
    # reply. If an answer reaches it, the RM is told the answer was cut short.
    llm_max_answer_tokens: int = Field(default=600, ge=16, le=4000)

    # Browser pages allowed to call the AI assistant (the Vite dev server by default).
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    # Opening the panel has the model read the rules and case facts in the background, so the
    # first question is quicker. The same case is not re-read more often than this.
    llm_warm_up: bool = True
    llm_warm_up_interval_seconds: float = Field(default=120.0, ge=0, le=3600)

    # Reviewed knowledge (official guidance + approved past resolutions), stored locally in
    # SQLite and ChromaDB under knowledge_data_dir (relative to apps/assistant; not in Git).
    knowledge_enabled: bool = True
    knowledge_data_dir: str = "data/knowledge"
    # Local embedding model for knowledge search (Ollama's own API, not the /v1 path).
    embed_base_url: str = "http://127.0.0.1:11434"
    embed_model: str = "nomic-embed-text"
    embed_timeout_seconds: float = Field(default=30.0, gt=0, le=300)

    max_history_messages: int = Field(default=8, ge=0, le=20)
    max_question_chars: int = Field(default=600, ge=20, le=4000)
