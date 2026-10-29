"""AI Assistant settings, read from AI_ASSISTANT_* environment variables or apps/assistant/.env."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiAssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_ASSISTANT_", env_file=".env", extra="ignore")

    # The CLM backend the AI assistant reads from. The RM's own session is forwarded, so the
    # backend still decides what this user may see.
    clm_backend_url: str = "http://127.0.0.1:8000"
    backend_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    # Explicit chat uses an OpenAI-compatible API; deployment data handling is separate.
    llm_enabled: bool = True
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "ministral-3:8b"
    llm_api_key: SecretStr = SecretStr("ollama")
    llm_timeout_seconds: float = Field(default=90.0, gt=0, le=600)
    llm_temperature: float = Field(default=0.2, ge=0, le=1)
    # Safety limit on answer length, well above a normal answer: it only stops a runaway
    # reply. If an answer reaches it, the RM is told the answer was cut short.
    llm_max_answer_tokens: int = Field(default=600, ge=16, le=4000)

    # Model profile (model_profiles.py). The default is the adapter above, unchanged. The
    # remote profile (D-091) is dormant in the service: it refuses to start against a real
    # network whatever is set here, and it never reads AI_ASSISTANT_LLM_API_KEY. Only the
    # evaluation harness may open the Phase B live gate (D-092, proposed), for synthetic cases.
    llm_profile: str = "local_openai_compatible"
    # Remote profile only: the decision id that must be named, one approved endpoint slug,
    # the reasoning effort and its token allowance, and the largest prompt it may send.
    remote_inference_decision: str = ""
    # Phase B only: must name the live decision as well, and the caller must be the harness.
    remote_live_decision: str = ""
    openrouter_endpoint: str = ""
    llm_reasoning_effort: str = ""
    llm_reasoning_allowance_tokens: int = Field(default=0, ge=0, le=4000)
    remote_max_prompt_bytes: int = Field(default=32768, ge=1024, le=262144)
    # Remote profile only: the lifetime budget ledger (budget.py; path relative to
    # apps/assistant, not in Git). The cap lives in the ledger, never in settings.
    budget_ledger_path: str = "data/budget/ledger.sqlite3"
    budget_max_in_flight: int = Field(default=1, ge=1, le=4)
    budget_settle_lag_seconds: int = Field(default=600, ge=0, le=86400)
    # D-095: the most reserved plus settled remote spend per Singapore calendar day, in
    # micro-USD. It applies to every remote call: qualification and chat. D-096: the default
    # until an HR administrator sets the daily limit on AI Models. D-098: US$1.00 by default,
    # with no US$1 ceiling (budget.MAX_MICRO_USD is only a technical bound); the lifetime cap
    # and the key's own verified limit still apply, and the strictest wins.
    budget_daily_cap_micro_usd: int = Field(default=1_000_000, ge=0, le=10**12)

    # D-094 local synthetic test mode (off unless named): an HR administrator may then select
    # the remote profile in model management, and the chat uses it only on the approved
    # synthetic test case (synthetic_boundary.py). Needs the D-091 and D-092 values above,
    # loopback-only CLM backend and browser origins, and the owner's attestations.
    local_api_test_decision: str = ""
    # "auto_topup_off,prompt_logging_off": neither is readable through the provider's API.
    local_api_test_owner_attests: str = ""
    # The most remote calls the activated model makes before the next activation or restart
    # (open calls included; the ledger cap bounds the spend across restarts). D-096: the
    # default until an HR administrator sets the call limit on AI Models (1 to 200).
    local_api_test_max_calls: int = Field(default=20, ge=1, le=200)
    # A passing preflight is reused for this long before the next call checks again.
    local_api_test_preflight_seconds: int = Field(default=300, ge=0, le=3600)
    # Optional GPT-OSS 120B Fast configuration (reasoning effort low) listed beside the
    # configured one on AI Models (off by default). It is the same model, endpoint, key, ledger
    # and limits with its own configuration identity: it needs its own passing (paid)
    # qualification before HR can activate it; another setting's qualification never counts.
    remote_low_reasoning_profile_enabled: bool = False
    # The paid qualification: Phase B question ids (P01#1,...) and their count.
    local_api_test_qualification_questions: str = ""
    local_api_test_qualification_count: int = Field(default=0, ge=0, le=17)
    # D-095 development synthetic mode (off unless named, and only on top of a ready D-094
    # mode): the chat may then use the remote model on any verified synthetic development case
    # (synthetic_eligibility.py), not only the one D-094 fixture case. Never for real data.
    synthetic_dev_decision: str = ""
    # D-099 (proposed): Claude Sonnet 5.5 Balanced and Fast are listed on AI Models but never
    # usable (anthropic_profiles.py: the provider-side spending controls the remote profile
    # relies on are missing for a direct Anthropic key). Naming D-099 only changes the reason.
    anthropic_decision: str = ""

    # Model management (D-093, local loopback models only): off unless IT names a profiles file
    # (model_catalog.py). Then an HR administrator (MODEL_CONFIG_MANAGE) may test, qualify,
    # activate and roll back the file's models; the choice is kept in the state database
    # (relative to apps/assistant; not in Git). The models above stay the baseline.
    model_profiles_file: str = ""
    model_admin_db_path: str = "data/models/model_admin.sqlite3"
    # The longest a qualification run may take before it is stopped.
    model_qualification_max_seconds: int = Field(default=3600, ge=60, le=14400)

    # Browser pages allowed to call the AI assistant (the Vite dev server by default).
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )

    # Optional case-fact warm-up is restricted at the transport to literal loopback URLs.
    # Enabling this never authorizes remote disclosure. The same case is throttled below.
    llm_warm_up: bool = True
    llm_warm_up_interval_seconds: float = Field(default=120.0, ge=0, le=3600)

    # Reviewed knowledge (official guidance + approved past resolutions), stored locally in
    # SQLite and ChromaDB under knowledge_data_dir (relative to apps/assistant; not in Git).
    knowledge_enabled: bool = True
    knowledge_data_dir: str = "data/knowledge"
    # POC only (D-083, proposed; relaxes D-074's two-person control): the synthetic users have
    # one Director, so when true a reviewer may approve or reject an entry they wrote or
    # edited, after confirming it, and the decision is recorded as single-reviewer. False keeps
    # the two-person rule. Retiring an entry always takes two reviewers.
    knowledge_single_reviewer: bool = True
    # Answer records (D-084, proposed): one per answer, kept so a Director can see why the AI
    # said what it said. A record not linked to an enhancement request (unrated, or rated "Yes,
    # helpful") is deleted this many days after the answer; a linked one this many days after
    # its request was resolved or closed.
    answer_record_unrated_days: int = Field(default=7, ge=1, le=365)
    answer_record_closed_days: int = Field(default=30, ge=1, le=365)
    # Local embedding model for knowledge search (Ollama's own API, not the /v1 path).
    embed_base_url: str = "http://127.0.0.1:11434"
    embed_model: str = "nomic-embed-text"
    embed_timeout_seconds: float = Field(default=30.0, gt=0, le=300)

    # Retrieval: how the final score is made (weights) and how good a match must be.
    # Tuned on the labelled set (scripts/evaluate_retrieval.py), not assumed.
    retrieval_weight_semantic: float = Field(default=0.45, ge=0, le=1)
    retrieval_weight_keyword: float = Field(default=0.2, ge=0, le=1)
    retrieval_weight_context: float = Field(default=0.3, ge=0, le=1)
    retrieval_weight_recency: float = Field(default=0.05, ge=0, le=1)
    retrieval_min_score_guidance: float = Field(default=0.3, ge=0, le=1)
    retrieval_min_score_resolution: float = Field(default=0.4, ge=0, le=1)
    retrieval_max_guidance: int = Field(default=3, ge=0, le=10)
    retrieval_max_resolutions: int = Field(default=3, ge=0, le=10)

    max_history_messages: int = Field(default=8, ge=0, le=20)
    max_question_chars: int = Field(default=600, ge=20, le=4000)

    # Content-free metrics for each explicit question (telemetry.py): off by default; "log"
    # writes one JSON line per answer with counts, sizes, timings and codes only.
    telemetry: Literal["off", "log"] = "off"
