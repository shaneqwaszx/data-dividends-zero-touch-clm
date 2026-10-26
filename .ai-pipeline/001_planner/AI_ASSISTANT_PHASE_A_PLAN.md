# AI Assistant Phase A — Observability, Offline Evaluation, Dormant Remote Profile and Budget Guard — Planner Handoff

Status: **A1 AUTHORISED; A2 NOT AUTHORISED.** Phase A spends US$0 and makes no call to any
remote model or to OpenRouter.

Owner decisions recorded 2026-10-26 (owner authorisation for Phase A1):

- Phase A is approved as the overall roadmap; **A-1 approves A1 only** (WP1 and WP2, their
  documentation, tests, checks, independent QG and A1 publication; never merge).
- **A-3:** telemetry stays off by default with the 6.3 allow-list, restricted further: **no
  `case_id`** in any record and **no `facts_sha256_12`**; every retrieval identifier and
  categorisation value is validated as content-free; the sentinel privacy test is kept; no
  content, secret, customer information or model response in a record.
- **A-6:** gold labels are owner/team-owned. The harness provides scenarios, frozen
  snapshots, label stubs, scoring and synthetic evaluator self-tests only; self-test results
  are kept apart from model-performance results.
- **A-7:** no local model is installed during the initial A1 implementation (E1 deferred).
- A-2, A-4, A-5 and A-8 (A2 scope) remain deferred. A2 needs a separate owner authorisation
  covering D-090, ADR-012, the OpenRouter security boundary and the lifetime budget guard.
- **A2 follow-up F-A2-1:** the owner provisioned the OpenRouter key as `OPENROUTER_API_KEY`
  (workspace `FYP - AI Assistant`, key `CLM - AI Assistant`; credential provisioning only,
  not authorisation to call or spend). The settings loader reads only `AI_ASSISTANT_*`
  variables, so that variable is ignored today. WP3 (section 8.2) must decide how the
  dormant `openrouter` profile obtains its key (for example, read `OPENROUTER_API_KEY` only
  when that profile is selected) and must never send it to the default local model.

## 1. Identity and authority

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`.
- Planning baseline: `main` = `origin/main` = `1d039865bf5197a76add7f733128829bb05019ac`
  (2026-10-26). The implementer re-fetches and records `BASE_SHA` at task start.
- Implementation location (proposed): a new worktree created through `worktree-task`, for
  example `C:\Users\shane\Desktop\claude-worktrees\assistant-phase-a-20261026`, on
  `feat/assistant-phase-a-20261026` from `origin/main`. Never develop on `main`.
- Input evidence (Tier 2, read on demand):
  `.ai-pipeline/reports/AI_ASSISTANT_OPENROUTER_120B_INVESTIGATION_20261026.md`
  (sections 4, 6.3, 6.5, 7, 8, 12, 14).
- Governing authority: `AGENTS.md`; `docs/DEVELOPMENT_WORKFLOW.md`; ADR-012 (section C
  accepted via D-074; revisit condition "any non-local embedding or model endpoint");
  D-075; D-083 and D-084 (both PROPOSED); Q-013/Q-014 (open).
- Change classes (conservative):

  | Package | Classes |
  |---|---|
  | WP1 Observability | `AUTH_RBAC_SECURITY` (logging/redaction), `ARCHITECTURE_REFACTOR` (new sink seam) |
  | WP2 Evaluation harness | `CI_TOOLING` (repository scripts), `ARCHITECTURE_REFACTOR` (new package) |
  | WP3 Adapter hardening | `EXTERNAL_PROVIDER`, `AUTH_RBAC_SECURITY` (secret, remote trust boundary) |
  | WP4 Budget guard | `PERSISTENCE` (local ledger), `ARCHITECTURE_REFACTOR` (new owner), `AUTH_RBAC_SECURITY` |
  | Docs in each package | `DOCS_ONLY` |

  Not affected (and must stay unaffected): `BACKEND_API`, `FRONTEND_UI`,
  `FRONTEND_STATE_CACHE`, CLM backend `BACKEND_DOMAIN`, Mongo.
- Skills: `fyp-phase-execution`, `worktree-task`, `external-provider-integration`,
  `integration-security-review`, `persistence-schema-change`,
  `architecture-change-review`; then `fyp-quality-gate` (independent) and
  `integration-safe-development` (pre-PR).
- Run `python scripts/dev_context.py` once per class above at task start.

## 2. Goal

Make the AI Assistant measurable and ready for a controlled, budget-capped model
comparison **without changing any user-visible behaviour**:

1. content-free per-answer metrics (WP1);
2. a deterministic offline evaluation harness with frozen scenarios and gold labels
   (WP2);
3. an OpenRouter-capable adapter profile that is dormant by default and fail-closed when
   enabled (WP3);
4. an application-side lifetime budget guard with reservations (WP4).

## 3. Invariants (acceptance gate for every package)

1. All existing assistant tests, the backend integration test
   `apps/backend/tests/test_ai_assistant_main_integration.py`, the frontend assistant
   Vitest files and `apps/frontend/e2e/assistant-streaming.e2e.ts` pass unchanged.
2. `BriefResponse`, `ChatResponse`, `KnowledgeSource`, `HealthResponse`, feedback and
   review bodies, status codes and notice strings are unchanged. No new route.
3. With every new setting at its default, the model request is **byte-identical** to today
   (`llm.py:108-117` payload, headers, URL) and no new file, log line or network call
   appears.
4. The exact-line catalog and `StreamingGuard` remain the only route to displayed model
   text; deterministic fallback semantics (`answered_by`, notices) are unchanged.
5. GET-only CLM access with the user's session; warm-up and embeddings stay
   loopback-only.
6. No question text, history, answer text, allowed lines, titles, notes, names, document
   or registry values, user ids, raw provider bodies, headers or keys are logged, stored by
   the new code, or placed in exceptions.
7. Phase A code and tests make no call to a non-loopback host (enforced by tests).

## 4. Prerequisite owner decisions

| ID | Decision | Recommendation | Blocks |
|---|---|---|---|
| A-1 | Approve this plan for implementation | — | everything |
| A-2 | Where the budget ledger lives | Separate SQLite file `apps/assistant/data/budget/ledger.sqlite3` (git-ignored), not a knowledge-store table: D-084 already reserves knowledge schema v5 | WP4 |
| A-3 | Telemetry default and field list (section 6.3) | Default `off`; `log` emits one content-free JSON line per answer; harness uses an in-memory sink | WP1 |
| A-4 | Governance record | New `D-090` (PROPOSED) plus ADR-012 Amendment 2 (PROPOSED): dormant evaluation-only remote profile and budget ledger; no runtime enablement before Phase B authorisation | WP3/WP4 merge |
| A-5 | Remote-profile interlock | Require `AI_ASSISTANT_REMOTE_INFERENCE_DECISION` to equal the recorded decision id before the `openrouter` profile can start | WP3 |
| A-6 | Who writes and freezes gold labels | Owner/team label; implementer only generates stubs; labels frozen by hash before any model run | WP2 scoring, E1 |
| A-7 (optional) | Install `ministral-3:8b` and `nomic-embed-text` locally to run the E1 baseline and the deferred D-075 retrieval evaluation | Yes, inside Phase A, local only | E1 only |
| A-8 | Project-state record | Record the remote profile as `DORMANT` only if `scripts/check_project_state.py` accepts it; otherwise prose in `ARCHITECTURE.md` | docs |

Phase B decisions (O1 data to OpenRouter, O3/O4 spend and budget semantics, O5 ADR
revisit outcome) are **not** needed for Phase A and must not be assumed by it.

## 5. Delivery shape and sequencing

Two publications, implemented by one writer in one worktree:

| Publication | Packages | Why separate |
|---|---|---|
| **A1** | WP1 + WP2 | Useful on its own; no external-provider surface; smaller security review |
| **A2** | WP3 + WP4 (on top of A1) | Carries the external-provider, secret and persistence surfaces; needs A-4 accepted before merge |

Order: WP1 → WP2 → WP3 → WP4, each with focused tests; Stage 2 acceptance and an
independent QG per publication. After WP1's sink interface is fixed, WP2 and WP3 touch
disjoint files and could run as two writers in separate worktrees if the owner wants
speed; README/`.env.example`/doc edits then move to the integration step to avoid overlap.

Relative size (not a time estimate): WP1 S, WP2 L, WP3 M, WP4 M.

## 6. WP1 — Content-free observability

### 6.1 Files

| File | Change |
|---|---|
| `apps/assistant/ai_assistant/telemetry.py` (new) | `AnswerMetrics` (frozen dataclass), `MetricsSink` protocol, `NullSink`, `LogSink` (logger `ai_assistant.metrics`, one JSON line at INFO), `MemorySink` (tests/harness). Sink errors are swallowed and counted, never raised |
| `apps/assistant/ai_assistant/prompts.py` | `PROMPT_BUILDER_VERSION` constant; `prompt_version()` = SHA-256 of rules text + terms file + builder version; `describe_messages(messages)` returning character counts per part (rules, facts, history, knowledge, terms, question) by the existing message markers. `build_messages` unchanged |
| `apps/assistant/ai_assistant/main.py` | `create_app(..., metrics: MetricsSink \| None = None)`; build one `AnswerMetrics` per `/chat` and `/chat/stream` request (including small talk and every fallback), timings via `time.monotonic()`. Response objects untouched |
| `apps/assistant/ai_assistant/config.py` | `telemetry: Literal["off", "log"] = "off"` |
| `apps/assistant/tests/test_telemetry.py` (new) | Tests in 6.4 |
| `apps/assistant/README.md` | "Observability" section |

### 6.2 Fallback reason enum

`small_talk`, `model_disabled`, `model_unavailable` (transport/timeout/HTTP/protocol),
`policy_no_allowed_line`, `stream_partial` (kept lines before failure),
`budget_refused` and `provider_budget` (reserved for WP4), `none`.

### 6.3 Field list (allow-list; anything else is forbidden)

`request_id` (uuid4), `route`, `case_id` (UUID, a safe identifier), `answered_by`,
`fallback_reason`, `model`, `profile`, `prompt_version`, `part_chars{…}`,
`history_turns`, `retrieval{confidence, degraded, entries[{key, kind, score}]}`,
`allowed_catalog_lines`, `allowed_knowledge_lines`, `kept_lines`, `left_out_lines`,
`cited_tags`, `finish_reason`, `cut_short`, `empty_content`, `timings_ms{backend,
retrieval, first_model_byte, first_displayed_line, total}`, `usage{…}` (null until WP3),
`budget{…}` (null until WP4). Optional, owner-gated (A-3): `facts_sha256_12`.

### 6.4 Tests

1. One record per request for: model answer (chat and stream), model down, unverifiable
   reply, small talk, cut short, stream failure with kept lines.
2. **No-content property:** with sentinel strings planted in the question, history,
   fixture company name/UEN/address, document values, viewer name and the model reply,
   the serialised metrics contain none of them.
3. Default `off`: no log records, no files. `log`: exactly one JSON-parseable line per
   answer.
4. Responses are byte-identical with `NullSink` and `MemorySink`.
5. A sink that raises never changes the response.

## 7. WP2 — Offline evaluation harness (US$0)

### 7.1 Package and files

New top-level package `apps/assistant/assistant_eval/` (kept out of the runtime
`ai_assistant` import graph; added to setuptools discovery and to the mypy command).

| File | Responsibility |
|---|---|
| `assistant_eval/scenarios.py` | Pydantic (`extra="forbid"`) scenario schema: id, description, base fixtures, variant transforms, actor, turns, tags (`normal`, `ambiguous`, `missing_evidence`, `conflicting_evidence`, `adversarial`, `multi_turn`), knowledge profile (`guidance`, `guidance+seed`, `guidance+seed+fix`) |
| `assistant_eval/variants.py` | Named, documented pure transforms over the existing Garden fixtures (for example `no_documents`, `completed`, `legal_name_conflict`, `goldtier_uncertain`, `ownership_required`, `instruction_in_document_value`). Labelled "synthetic fixture variant, not backend-generated" |
| `assistant_eval/snapshot.py` | Per-turn frozen snapshot: model messages, allowed lines with **stable ids** (catalog `C:<sha8>`, knowledge `K:<entry_id>@v<version>#<sentence>` plus the tag used), retrieval result, `prompt_version`, content hash |
| `assistant_eval/gold.py` | Gold schema per turn: `relevant`, `primary`, `must_not`, `expect_fallback`; labelling helper that prints lines with ids and writes stubs; `gold.lock.json` (hash of gold + snapshots) |
| `assistant_eval/runners.py` | Drives the real `create_app` through an `httpx.MockTransport` CLM backend and a temporary knowledge base (degraded `NoEmbedder` or local Ollama embedder). Models: `PerfectSelector`, `RandomSelector(seed)`, `ProseModel`, `InjectionFollower`, `ReplayModel`, and the existing `OpenAICompatibleChatModel` **restricted to literal loopback URLs** (`is_local_model_url`); any other URL is refused in Phase A |
| `assistant_eval/scoring.py` | Deterministic metrics (report 12.2): line validity, fallback rate, precision/recall/F1 vs gold, primary hit, `must_not` violations, citation correctness, unsafe display (independent recomputation; must be 0), cut-short and empty-content rates, latency from `MemorySink`, multi-turn Jaccard; aggregation by tag; repetition variance |
| `assistant_eval/report.py` | JSON + Markdown output with a run manifest (Git SHA, `prompt_version`, gold lock hash, model, embedder mode, settings subset) |
| `apps/assistant/scripts/evaluate_answers.py` | CLI: `snapshot`, `label`, `run`, `score`, `report`; default output `apps/assistant/data/eval/` (git-ignored) |
| `apps/assistant/tests/fixtures/eval/scenarios.json` | ≥15 synthetic scenarios × 4 questions plus ≥5 four-turn conversations; ≥5 adversarial items |
| `apps/assistant/tests/fixtures/eval/snapshots/*.json` | Frozen synthetic snapshots (tracked) |
| `apps/assistant/tests/fixtures/eval/gold.json`, `gold.lock.json` | Owner/team labels (A-6) |
| `apps/assistant/tests/test_eval_harness.py` | Tests in 7.3 |

Do not use the untracked repository-root `evaluation/` directory.

### 7.2 Design rules

- Gold labels reference stable line ids, not tags, so they survive retrieval reordering
  and RAG variants; a gold line missing from a variant's allowed set counts as a recall
  loss attributable to retrieval.
- Multi-turn snapshots freeze facts and retrieval per turn; history is built at run time
  from the model's own previous answers, exactly as in production.
- Scenario questions and answers are synthetic and may appear in harness output; no
  non-synthetic data is ever loaded.

### 7.3 Tests (E0 self-test is the WP2 acceptance)

1. `PerfectSelector`: F1 = 1.0, validity 1.0, fallback 0.
2. `RandomSelector`: F1 clearly below 1.0 and reproducible for a fixed seed.
3. `ProseModel`: validity 0, fallback 100%, unsafe display 0.
4. `InjectionFollower`: unsafe display 0 (guard holds); `must_not` violations measured.
5. Snapshot determinism: identical inputs → identical hashes.
6. Gold ids stable when tags are reordered.
7. Runner refuses a non-loopback base URL before any request; a socket guard fails the
   test on any non-loopback connection attempt.
8. Import boundary: `ai_assistant` never imports `assistant_eval`.

### 7.4 Optional E1 baseline (requires A-6 and A-7)

Local `ministral-3:8b`, frozen snapshots, 3 repetitions, temperature 0.2, `max_tokens`
600, degraded and (if installed) semantic retrieval. Recorded as `LOCAL` evidence in a
report under `.ai-pipeline/reports/`; never presented as Live. Also run the deferred
D-075 real-embedding retrieval evaluation if `nomic-embed-text` is installed.

## 8. WP3 — Adapter hardening, dormant by default

### 8.1 Files

| File | Change |
|---|---|
| `apps/assistant/ai_assistant/llm.py` | `ModelUsage` dataclass; optional `usage` and `finish_reason` on `ModelAnswer` and the last `Piece` (defaults keep existing constructors valid); profile-aware payload; usage read-through; strict usage parsing |
| `apps/assistant/ai_assistant/config.py` | New settings (8.2) with fail-closed validation |
| `apps/assistant/ai_assistant/main.py` | Composition only: pass profile options to the adapter; copy `usage`/`finish_reason` into metrics |
| `apps/assistant/.env.example` | Documented new keys with empty values and a "never commit a key" note |
| `apps/assistant/tests/test_llm_openrouter_profile.py` (new) | Tests in 8.5 |
| `apps/assistant/README.md` | "Remote model profile (dormant)" section |

### 8.2 Settings

| Setting | Default | `openrouter` profile rule |
|---|---|---|
| `llm_profile` | `openai_compatible` | `openrouter` enables everything below |
| `remote_inference_decision` | empty | must equal the recorded decision id (A-5) |
| `llm_base_url` | unchanged | must be exactly `https://openrouter.ai/api/v1` |
| `llm_api_key` | unchanged | must be set and not the Ollama placeholder; never logged |
| `llm_openrouter_providers` | empty | non-empty allow-list → `provider.only` |
| `llm_max_price_prompt_per_m`, `llm_max_price_completion_per_m` | empty | required → `provider.max_price`; also the WP4 price ceiling |
| `llm_reasoning_effort` | empty | required (`none`/`minimal`/`low`/`medium`/`high`) → `reasoning.effort` |
| `llm_reasoning_allowance_tokens` | 0 | > 0 unless effort is `none`; `max_tokens` = answer cap + allowance, bounded |
| `llm_capture_usage` | `false` | forced `true` |

Fixed in the `openrouter` profile (not configurable): `provider.allow_fallbacks=false`,
`provider.zdr=true`, `provider.data_collection="deny"`,
`provider.require_parameters=true`, `reasoning.exclude=true`. Any validation failure
stops start-up with a sanitised message that never echoes the key.

### 8.3 Stream and response handling

- **Read-through** (only when capture is on): after the first terminal `finish_reason`,
  keep reading until `[DONE]`, EOF, byte limit or deadline. Accept a usage chunk with one
  empty-delta choice repeating the finish reason, or with `choices: []`. Ignore and flag
  any content after finish. A failure during read-through keeps the already-validated
  answer and records `usage = null`.
- Reasoning fields (`delta.reasoning`, `reasoning_details`) are never displayed, logged
  or stored.
- `finish_reason: "length"` with no content sets `empty_content` in metrics; the
  user-visible notice stays exactly as today (UX change deferred).
- Non-stream: parse `usage`, `id`, `provider` when present; a top-level `error` on HTTP 200
  remains `LlmUnavailableError`.
- No retries anywhere; one POST per question for every outcome.

### 8.4 External-provider matrix (for the handoff report)

| Outcome | Call count | Behaviour |
|---|---|---|
| Success with usage | 1 | Answer + usage |
| Success without usage | 1 | Answer; usage null (WP4 trips its breaker) |
| 401/402/403/429/5xx before stream | 1 | `LlmUnavailableError` → existing fallback; status class in metrics only |
| Mid-stream `finish_reason: "error"` | 1 | Existing partial-lines/fallback behaviour |
| Error as only event on 200 | 1 | Failure, not success |
| Empty content + `length` | 1 | Existing fallback; `empty_content` flagged |
| Timeout / byte limit | 1 | Existing behaviour |

### 8.5 Tests

1. **Golden default payload:** default settings produce exactly today's URL, headers and
   JSON body.
2. `openrouter` payload contains the fixed provider object, reasoning, max price and the
   summed `max_tokens`; no `stream_options`.
3. Start-up refusal for each invalid configuration in 8.2 (wrong host, `http`, userinfo,
   query, missing providers, missing price, default key, missing decision id, missing
   effort); the key never appears in the error.
4. SSE shapes: `: OPENROUTER PROCESSING` comments; reasoning deltas; content → finish →
   usage chunk with duplicated finish → `[DONE]` (text once, usage parsed); usage with
   `choices: []`; missing and malformed usage; content after finish ignored; mid-stream
   error chunk; error-only 200 stream; empty content + `length`; deadline and byte limit
   during read-through.
5. Non-stream equivalents.
6. Call counts: exactly one request and zero retries for every row in 8.4; warm-up count
   0 for the remote profile.
7. Secret hygiene: a sentinel key appears only in the outgoing `Authorization` header —
   never in exceptions, metrics, logs or `HealthResponse`.
8. Socket guard: no non-loopback connection in the whole suite.

`integration-security-review` is mandatory for WP3.

## 9. WP4 — Application budget guard

### 9.1 Files

| File | Change |
|---|---|
| `apps/assistant/ai_assistant/budget.py` (new) | `BudgetLedger` (SQLite, `BEGIN IMMEDIATE`), `BudgetedChatModel` (wraps any `ChatModel`), worst-case cost estimator |
| `apps/assistant/ai_assistant/config.py` | `budget_cap_usd`, `budget_ledger_path` (default `data/budget/ledger.sqlite3`), `budget_max_in_flight` (default 1), `budget_max_calls` |
| `apps/assistant/ai_assistant/main.py` | Wrap the model in `BudgetedChatModel` when the profile is `openrouter`; the remote profile refuses to start without a ledger and a cap > 0 |
| `apps/assistant/scripts/budget_ledger.py` (new) | Offline `status`, `reset-breaker`, `set-cap`; a `reconcile` command whose OpenRouter `GET /api/v1/key` fetch is implemented behind an injected transport and **exercised only with mocks in Phase A** |
| `apps/assistant/tests/test_budget_guard.py` (new) | Tests in 9.3 |
| `apps/assistant/README.md` | "Budget guard" section |

### 9.2 Rules

- **Reservation before every remote call:** prompt tokens are bounded by the prompt's
  UTF-8 byte count plus a fixed per-message overhead (a provable upper bound); output by
  `max_tokens`. `reserve = in_bound × max_prompt_price + max_tokens × max_completion_price`,
  using `Decimal`.
- Refuse when `settled + open_reservations + reserve > cap`. Refusal raises
  `LlmUnavailableError` → existing fallback and notice; metrics `budget_refused`.
- **Settle** with the provider's `usage.cost`. Missing or malformed cost → settle at the
  reservation, mark `unsettled`, **trip the accounting breaker** (all later calls refused
  until an operator reconciles and resets it). Cancellation or exception → settle at the
  reservation, `unsettled`.
- The cap is lifetime: no date-based reset. Raising it needs the CLI with an explicit flag.
- In-flight limit enforced in process; ledger writes serialised by SQLite.
- Ledger rows are content-free: id, amounts, status, token counts, provider, generation
  id, timestamps, anomaly code. A missing directory is created; a corrupt or
  newer-schema ledger fails closed (refuse every call) and is never recreated silently.
- Default profile: no guard and no ledger file (local model, zero marginal cost).

### 9.3 Tests

1. Reservation arithmetic and the byte upper bound; boundary at exactly the cap.
2. Concurrent reservations (threads) never exceed the cap.
3. Settlement with cost; missing usage trips the breaker and blocks the next call with
   zero inner calls.
4. Cancellation settles conservatively.
5. Persistence across reopen; lifetime cap unaffected by moving the clock forward months.
6. Refusal produces the existing case-data fallback and notice.
7. Corrupt and future-schema ledgers fail closed.
8. Default profile creates no ledger file and behaves byte-identically.
9. Ledger schema contains no text columns that could hold content.

`persistence-schema-change` and `architecture-change-review` (existence check: the
knowledge store is a different aggregate with v5 reserved by D-084; the CLM backend is
forbidden as an assistant write target; OpenRouter key limits are external, not an
application control) are mandatory for WP4.

## 10. Documentation (in the publication that introduces each surface)

- `apps/assistant/README.md`: Observability, Evaluation harness, Remote model profile
  (dormant), Budget guard; settings table updated.
- `docs/decisions/DECISION_LOG.md`: `D-090` (PROPOSED) for A2; A1 needs no new decision
  unless the QG asks for one.
- `docs/decisions/ADR-012_AI_ASSISTANT_KNOWLEDGE_LOOP.md`: Amendment 2 (PROPOSED) noting
  the dormant evaluation-only remote profile, the ledger and that no remote inference is
  enabled.
- `docs/ARCHITECTURE.md`: dated entry for A1 and A2.
- `docs/PROJECT_STATE.md`: only per A-8.
- Untracked Markdown whitespace checked explicitly.

## 11. Verification

| Stage | Commands / evidence |
|---|---|
| Stage 1 (per package) | New focused tests; `apps/assistant`: `python -m pytest`, `python -m ruff check ai_assistant assistant_eval tests`, `python -m ruff format --check …`, `python -m mypy ai_assistant assistant_eval` |
| Stage 2 (per publication, once) | Full assistant suite; `apps/backend/tests/test_ai_assistant_main_integration.py`; frontend `aiAssistant*.test.ts`, `AiAssistantPanel.test.tsx`, `KnowledgeReview.test.tsx`; `assistant-streaming` E2E; `python scripts/check_secrets.py`; `python scripts/check_architecture.py`; `python scripts/check_project_state.py`; `git diff --check` plus explicit whitespace check of untracked Markdown |
| Gates | `integration-security-review` (A1 for logging, A2 full); independent `fyp-quality-gate` per publication |
| Pre-PR | `integration-safe-development`; `python scripts/pre_pr_check.py` on the committed state. Note: it does not run assistant tests, so Stage 2 assistant evidence is attached explicitly |
| Proof of US$0 | No OpenRouter key in the test environment (`conftest.py` disables the model); socket guard; no live command in the evidence |

Hosted CI does not run assistant tests (and is billing-blocked); adding an assistant CI
job is a separate `CI_TOOLING` task (report O9), not part of Phase A.

## 12. Non-goals

Prompt, retrieval or data-view optimisation (report WP5); any remote or paid call,
including OpenRouter `GET /api/v1/key`; enabling the remote profile in any running
environment; line-ID output; deterministic intent routing; UX wording changes (including
the empty-content notice); answer records and request lifecycle (D-084); feedback rate
limiting; tools/function calling; remote embeddings; new databases or services beyond the
local ledger file; CI changes; frontend changes; CLM backend changes.

## 13. Stop conditions

- Any requirement to reach a non-loopback host during Phase A.
- Any change to an API schema, notice string or the exact-line guard becomes necessary.
- The byte-identical default payload cannot be preserved.
- A provable worst-case cost bound cannot be built (stop WP4).
- `check_project_state.py` rejects the provider record (keep prose; do not edit the
  checker without a `CI_TOOLING` assignment).
- Gold labels unavailable: deliver the harness and E0; defer E1 scoring.
- Two unsuccessful repair cycles on the same design problem.

## 14. Exit criteria (evidence handed to the Phase B authorisation)

1. A1 and A2 each have a Stage 2 acceptance record and an independent QG PASS on the exact
   content (merge is the owner's).
2. E0 self-test passes; gold labels frozen with `gold.lock.json`; optional E1 baseline
   recorded as LOCAL evidence.
3. Offline demonstration with mocks: the `openrouter` profile refuses invalid
   configuration, reads usage through `[DONE]`, and the ledger refuses at the cap and on
   missing usage.
4. Acceptance thresholds (report 12.5) confirmed by the owner.
5. Phase B still requires O1, O3, O4 and O5 (report section 16) before any spend.
