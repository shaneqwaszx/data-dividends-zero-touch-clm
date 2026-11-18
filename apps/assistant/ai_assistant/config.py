"""AI Assistant settings, read from AI_ASSISTANT_* environment variables or apps/assistant/.env."""

import os
from pathlib import Path, PurePath
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def under_data_root(root: Path, value: str) -> str:
    # A relative store path resolved under the data root. A leading "data" segment (the
    # package-relative defaults' folder) is dropped, so "data/budget/ledger.sqlite3" becomes
    # "<root>/budget/ledger.sqlite3". A path that would leave the root is refused. (Comments,
    # not a docstring: string constants here feed the D-094 boundary vocabulary.)
    pure = PurePath(value)
    if pure.drive or pure.root:  # drive- or root-relative (e.g. "C:x", "\\x"): ambiguous
        raise ValueError("a store path in the data root must be relative or absolute")
    parts = pure.parts
    if parts and parts[0] == "data":
        parts = parts[1:]
    if not parts or any(part in ("..", ".") for part in parts):
        raise ValueError("a store path must stay inside the data root")
    return os.path.normpath(root.joinpath(*parts))


# D-092 P10 and D-107 Q1: the approved paid qualification questions and their number. Changing
# them needs owner approval (D-111 Q6 proposes four; not approved).
APPROVED_QUALIFICATION_QUESTIONS = "P01#1,P02#0"
APPROVED_QUALIFICATION_COUNT = 2


# Owner approval of conversational (free-text) answers, including external models on any case
# (D-115 conversational contract, widened by D-122). Scope, context, RAG and the sentence
# checks still bound every answer. Set only in a reviewed change, never by a teammate.
CONVERSATIONAL_DECISION: str | None = "D-122"

# D-130 (OD-G, owner-approved 2026-11-13): on the registered hosted Claude deployment only
# (anthropic_runtime.hosted_deployment), the general chat, Support's chat and "Try with this
# change" may use the activated Claude configuration, under every control the case chat has
# (D-106 key, D-107, qualification, D-102/D-118 limits, the per-call ticket). It amends D-115
# and D-105 for that deployment only: local models, development machines and every other
# provider keep them unchanged. Set only in a reviewed change, never by a setting.
HOSTED_CHAT_DECISION: str | None = "D-130"
HOSTED_CHAT_PATHS: frozenset[str] = frozenset({"general", "support", "try_change"})
# D-130 amendment (DRAFT, owner-directed 2026-11-14 for local preparation only): dashboard AI
# insights as a fifth hosted Claude path (hosted_insights.py). DISABLED: None keeps the hosted
# service refusing every insights route. Set only in a reviewed change, after the D-129
# privacy amendment, the notice, the QG, egress, qualification and the owner's activation.
HOSTED_INSIGHTS_DECISION: str | None = None
# D-134 (PROPOSED, not active): GPT-OSS 120B through OpenRouter as a second hosted model, on
# the case chat only. DISABLED: None keeps the hosted service refusing the OpenRouter provider
# mode at start-up and keeps remote_test refusing a hosted registration. Set only in a reviewed
# change, after the owner approved the recipients, the egress restriction, the key handling and
# the paid requalification (outputs/gptoss-registry-20261114).
# D-134 ACCEPTED (owner, see OPENROUTER_OWNER_DECISION.md): the OpenRouter mode exists.
HOSTED_OPENROUTER_DECISION: str | None = "D-134"
# D-129 (ACCEPTED 2026-11-15, Anthropic only): what the hosted service may send to an external
# model provider (the exact payloads, the OD-G8 identity rule, synthetic-only input and the
# caps). DISABLED: None keeps every hosted provider mode (Anthropic and OpenRouter) refusing
# the start (TRANSMISSION_DECISION_REQUIRED) and both hosted runtimes refusing a registration,
# so no case content can leave the hosted service. Set only in a reviewed change that records
# the owner's acceptance of D-129, never by a setting. A development machine is governed by
# D-104 and D-095 instead (owner attestations plus the verified-synthetic eligibility check).
# Anthropic: D-129. OpenRouter: its own amendment, D-129A, recorded below.
HOSTED_TRANSMISSION_DECISION: str | None = "D-129"
# D-138 A1 (PROPOSED): the transmission gate is provider-scoped. The owner accepted D-129 for
# Anthropic only (2026-11-15); OpenRouter needs its own accepted transmission decision (a D-129
# amendment for OpenRouter). DISABLED: None keeps the OpenRouter mode refusing the start
# (OPENROUTER_TRANSMISSION_DECISION_REQUIRED) and its runtime refusing a hosted registration and
# an egress proxy, whatever HOSTED_TRANSMISSION_DECISION says. Set only in a reviewed change.
# D-129A ACCEPTED (owner): OpenRouter transmission and the A1-R3 residual. The mode still
# starts only with its daily cap, proxy, settings and egress install in place.
HOSTED_OPENROUTER_TRANSMISSION_DECISION: str | None = "D-129A"
# D-142 (proposed): the pseudonymised data policy (privacy_boundary.py) on a hosted provider.
# None until the owner adopts D-142; a service set to that policy then refuses to start
# (PRIVACY_DECISION_REQUIRED). The privacy boundary itself applies to every external call
# whatever this says. Set only in a reviewed change.
HOSTED_PRIVACY_DECISION: str | None = None


def conversational(settings: "AiAssistantSettings") -> bool:
    """True when answers are written in the model's own words (checked sentence by sentence)."""

    mode = settings.answer_mode
    return mode == "copilot" or (mode == "auto" and CONVERSATIONAL_DECISION is not None)


def external_conversational(settings: "AiAssistantSettings") -> bool:
    """True when an external model (Claude, GPT-OSS) may answer in its own words: the owner's
    recorded decision, never a setting alone (``answer_mode=copilot`` keeps external models on
    exact lines, as before D-115 X2), and not the exact-line rollback."""

    return CONVERSATIONAL_DECISION is not None and conversational(settings)


class AiAssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_ASSISTANT_", env_file=".env", extra="ignore")

    # B0: optional root for the assistant's runtime stores (state DB, ledgers, profiles file,
    # knowledge). Empty keeps the package-relative defaults (apps/assistant/data). When set it
    # must be an existing absolute directory (never created here); relative store paths are
    # then resolved under it and absolute ones are kept, so nothing falls back elsewhere.
    data_dir: str = ""

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
    # apps/assistant, not in Git). The cap lives in the ledger, never in settings. D-118
    # amendment P2: by default a fresh session store, never the earlier design's ledger.
    budget_ledger_path: str = "data/budget/sessions/openrouter.sqlite3"
    budget_max_in_flight: int = Field(default=1, ge=1, le=4)
    budget_settle_lag_seconds: int = Field(default=600, ge=0, le=86400)
    # D-095: the most reserved plus settled remote spend per Singapore calendar day, in
    # micro-USD. It applies to every remote call: qualification and chat. D-096: the default
    # until an HR administrator sets the daily limit on AI Models. D-098: US$1.00 by default,
    # with no US$1 ceiling (budget.MAX_MICRO_USD is only a technical bound); the lifetime cap
    # and the key's own verified limit still apply, and the strictest wins. D-118: US$5.00 by
    # default, so one US$5.00 paid session fits in a day (a stored HR value still wins).
    budget_daily_cap_micro_usd: int = Field(default=5_000_000, ge=0, le=10**12)

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
    # The paid qualification: Phase B question ids (P01#1,...) and their count. The default is
    # the approved set (D-092 P10, D-107 Q1: two questions, two paid calls); a launcher or .env
    # that leaves both blank (the example file's empty values) gets it too (D-118 usability).
    local_api_test_qualification_questions: str = APPROVED_QUALIFICATION_QUESTIONS
    local_api_test_qualification_count: int = Field(
        default=APPROVED_QUALIFICATION_COUNT, ge=0, le=17
    )
    # D-095 development synthetic mode (off unless named, and only on top of a ready D-094
    # mode): the chat may then use the remote model on any verified synthetic development case
    # (synthetic_eligibility.py), not only the one D-094 fixture case. Never for real data.
    synthetic_dev_decision: str = ""
    # D-099 Option B (proposed): Claude Sonnet 5.5 Balanced and Fast on AI Models, under
    # Anthropic-specific spending safeguards that are NOT equivalent to OpenRouter's
    # (anthropic_runtime.py). Off unless D-099 is named, the D-094 local test interlock holds
    # and the owner attests the workspace controls below.
    anthropic_decision: str = ""
    # Comma-separated owner attestations (anthropic_runtime.OWNER_ATTESTATIONS): a dedicated,
    # non-default workspace; its monthly spend limit set in the Console; a workspace inference
    # key (never an organisation Admin key); the key revoked at the end of the FYP.
    anthropic_owner_attests: str = ""
    # The dedicated workspace's id; every response must name it (``anthropic-workspace-id``).
    anthropic_workspace_id: str = ""
    # The monthly spend limit the owner set on that workspace (not readable with an API key;
    # owner-attested). At most US$30.00 (D-102); 0 means not set, which refuses.
    anthropic_workspace_limit_micro_usd: int = Field(default=0, ge=0, le=30_000_000)
    # The separate Anthropic ledger (relative to apps/assistant; git-ignored data/). D-118
    # amendment P2: by default a fresh session store, never the earlier design's ledger.
    anthropic_ledger_path: str = "data/budget/sessions/anthropic.sqlite3"
    # Defaults until an HR administrator sets them (D-102): US$5.00 a Singapore day (D-118;
    # the ceiling) and 20 chat calls per paid session (ceiling 20; D-118: counted per session).
    anthropic_daily_cap_micro_usd: int = Field(default=5_000_000, ge=0, le=5_000_000)
    anthropic_max_calls: int = Field(default=20, ge=1, le=20)

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

    # How answers are written. "auto" (the default): exact lines until the owner approves
    # conversational answers (CONVERSATIONAL_DECISION), then conversational answers for every
    # model, external ones on verified synthetic cases only. "exact_lines" is the rollback;
    # "copilot" forces conversational answers (development and tests).
    answer_mode: Literal["auto", "exact_lines", "copilot"] = "auto"
    # Chat contexts (D-115 case memory): the turns of one chat are held in memory only, for
    # one user and one case (or the general chat), and dropped when the chat is left, after
    # this idle time, or at the latest after the absolute time (the backend's session lifetime).
    context_idle_seconds: int = Field(default=1800, ge=60, le=28800)
    context_max_seconds: int = Field(default=28800, ge=300, le=28800)
    context_max_turns: int = Field(default=16, ge=2, le=40)
    context_max_per_user: int = Field(default=8, ge=1, le=32)

    # Content-free metrics for each explicit question (telemetry.py): off by default; "log"
    # writes one JSON line per answer with counts, sizes, timings and codes only.
    telemetry: Literal["off", "log"] = "off"

    @model_validator(mode="after")
    def _approved_qualification_when_unset(self) -> Self:
        # Both left blank (empty list, count 0) means "not set": the approved set applies. A
        # list or count set on its own is kept as given, so a wrong value is still refused by
        # name (REMOTE_MANIFEST_MISSING) and never silently replaced.
        if (
            not self.local_api_test_qualification_questions.strip()
            and self.local_api_test_qualification_count == 0
        ):
            self.local_api_test_qualification_questions = APPROVED_QUALIFICATION_QUESTIONS
            self.local_api_test_qualification_count = APPROVED_QUALIFICATION_COUNT
        return self

    @model_validator(mode="after")
    def _place_stores_under_data_root(self) -> Self:
        # B0: an invalid root refuses the settings (the service does not start) instead of
        # silently using the package-relative stores or creating an empty root.
        raw = self.data_dir.strip()
        if not raw:
            self.data_dir = ""
            return self
        root = Path(raw).expanduser()
        if not root.is_absolute():
            raise ValueError("the data root must be an absolute path")
        if not root.is_dir():
            raise ValueError("the data root must be an existing path")
        root = root.resolve(strict=True)
        self.data_dir = str(root)

        def place(value: str) -> str:
            # Relative stores go under the root; absolute ones (and an empty profiles file)
            # are kept as they are.
            if value and not Path(value).is_absolute():
                return under_data_root(root, value)
            return value

        self.budget_ledger_path = place(self.budget_ledger_path)
        self.anthropic_ledger_path = place(self.anthropic_ledger_path)
        self.model_admin_db_path = place(self.model_admin_db_path)
        self.model_profiles_file = place(self.model_profiles_file)
        self.knowledge_data_dir = place(self.knowledge_data_dir)
        return self
