# AI Assistant Model Management — architecture assessment and proposed design

Status: **APPROVED by the owner on 2026-10-27** (decisions 1, 2, 3 and 5 approved; decision 4
conditionally approved), recorded as **D-093** and **ADR-012 Amendment 4**. Not sponsor policy.

Owner conditions and implementation deltas from the proposal below:

- G-5 is reported only (not a gate) until owner-approved answerability labels exist; G-4, G-6
  and G-7 are provisional technical gates; zero unsafe displayed lines is mandatory; a zero
  denominator never passes G-6; G-7 uses capacity verified from the server's own token
  counts; answer quality shows `NOT_SCORED`; activation needs an explicit acknowledgement.
- Key references use the reviewed allowlist `AI_ASSISTANT_MODEL_KEY_{OLLAMA,LM_STUDIO,VLLM,LOCAL}`.
- A failed baseline fails safe to case-data answers.
- Qualification runs the harness in its own process (`scripts/qualify_model.py`): the runtime
  package keeps the Phase A1 invariant that it never imports `assistant_eval`
  (`test_the_runtime_package_never_imports_the_harness`).
- Session 2 owns prompts, the response catalog and topic routing; this work does not change them.

| Identity | Value |
| --- | --- |
| Worktree | `C:/Users/shane/Desktop/claude-worktrees/assistant-model-management-20261027` |
| Branch | `feat/assistant-model-management-20261027` |
| `BASE_SHA` = HEAD = `origin/main` | `23c45a7` (PR #120 closeout, after #118/#119) |
| Change classes | `AUTH_RBAC_SECURITY`, `PERSISTENCE`, `EXTERNAL_PROVIDER` (model endpoints), API/type, frontend state/cache |

## 1. Assessment (current `origin/main`)

### Reusable as is

| Area | What exists | Reuse |
| --- | --- | --- |
| Model port | `llm.ChatModel` (`name`, `complete`, `stream`, `warm`) | Unchanged |
| Local adapter | `OpenAICompatibleChatModel`: bounded SSE, no redirects, closed errors, cancellation | Unchanged; one instance per profile |
| Loopback rule | `llm.is_local_model_url` (literal loopback only) | Selectability gate for admin profiles |
| Proxy refusal | `assistant_eval.models.local_model` refuses env and system proxies | Moved into `model_factory` (one owner) and called by both |
| Registry/factory | `model_profiles.APPROVED_PROFILES`, `model_factory.build_chat_model` with closed `ProfileConfigError` codes that never echo values | Extended, not duplicated |
| Remote profile | `openrouter_gpt_oss_120b`, dormant (D-091), live only via harness (D-092 proposed) | Displayed as pending authorisation; never selectable |
| Qualification | `assistant_eval.runner.run` serves 21 synthetic scenarios / 84 turns from a mock CLM backend through the real `create_app`; `scoring.label_free` gives fallback rate/reasons, line validity, unsafe display, cut-short, latency, prompt size | Called in-process with the candidate `ChatModel` |
| Guardrails | `validate_answer`, `StreamingGuard`, required lines, catalog | Untouched |
| Authorisation pattern | `knowledge_api`: backend `/api/auth/me` capabilities with the user's own session, re-check inside the write | Same pattern for admin endpoints |
| Capability precedent | `PROVIDER_SANDBOX_TEST`: HR-only, no `CASE_ACCESS`, nav + `CapabilityRoute` + server 403 | Same shape for `MODEL_CONFIG_MANAGE` |
| Admin page pattern | `AcraDiagnostics.tsx`: react-query keys under `["auth", userId, ...]`, safe error text | Same shape |

### Limitations that block the feature

1. **Model is fixed at process start.** `create_app` builds one `model` and closes over it in
   `answer_with_model`, `stream_answer`, `warm_up` and `/health`. Switching needs a holder.
2. **One local profile only**, configured by `AI_ASSISTANT_LLM_*`. Its base URL may be any
   URL (operator choice); there is no list of alternative models.
3. **D-091 and ADR-012 Amendment 3 say "no user model selection"**: this feature needs a new
   owner decision (D-093) that narrows that statement for admin-selected loopback profiles.
4. **Owner gold is a stub** (`tests/fixtures/eval/gold.json`: 0 labelled turns, A-6 open) and
   **acceptance thresholds were never set** (O8 open). Selection accuracy, relevance,
   completeness and grounding against labels therefore **cannot be scored today**; only
   label-free measures can. No threshold exists apart from "unsafe display must be 0".
5. Telemetry validates `profile` against the closed `PROFILE_IDS`; admin profile ids need a
   pattern rule.
6. `warm_up` checks `config.llm_base_url`, not the active model's URL.

Regression baselines confirmed on `23c45a7`: `test_guardrail_negation.UNSAFE` = **154**
sentences, `KNOWLEDGE_FILTER_LIMITS` = **46**; both stay unchanged and must pass.

## 2. Proposed design

### 2.1 Where things live (smallest safe change)

All model management is in the **assistant service** (it owns the model, the harness and
its own local data, ADR-012 A). The **CLM backend** changes only its capability matrix. The
frontend reaches the assistant at `/api/assistant/...` as today. No route-to-Mongo access,
no backend persistence change, no new provider adapter.

### 2.2 Permissions (RBAC)

- New backend capability **`MODEL_CONFIG_MANAGE`**, assigned to **HR only** for the POC.
  RM, Client Onboarder and Director do not get it; Director's `POLICY_APPROVE` and HR's
  `POLICY_MUTATE` are unchanged and independent of it.
- HR still has no `CASE_ACCESS`; the admin API never reads cases or answer records, and the
  qualification uses only the repository's synthetic fixtures.
- Every model-management endpoint: origin check, then `/api/auth/me` with the caller's own
  session, then `MODEL_CONFIG_MANAGE` (403 `MODEL_CONFIG_FORBIDDEN`). Mutations re-ask the
  backend **inside** the activation lock, same user, same capability (as `knowledge_api`).
- Refusals for a signed-in user (403) are audited with user id and role; 401 is not (no
  identity), and the frontend clears state on 401 as elsewhere.
- Frontend gating (nav item, `CapabilityRoute`) is presentation only.

### 2.3 Model profiles (configuration and credentials)

Two sources, merged into one read-only catalogue:

1. **Environment default** (`env_default`): exactly today's `AI_ASSISTANT_LLM_*` profile,
   unchanged behaviour. Always present, the baseline and the last-resort rollback target;
   it needs no qualification (it is what runs today).
2. **Server-managed allowlist file** owned by IT: `AI_ASSISTANT_MODEL_PROFILES_FILE`
   (JSON, git-ignored; a tracked `model_profiles.example.json` documents it). Strict schema
   (`extra="forbid"`), per entry:
   `profile_id` (`^[a-z0-9][a-z0-9_-]{2,47}$`), `display_name`, `deployment`
   (`ollama` | `lm_studio` | `vllm` | `openai_compatible`), `base_url`, `model_id`,
   `model_version` (optional), `context_window_tokens`, `max_answer_tokens` (16–4000),
   `temperature` (0–1), `timeout_seconds` (≤ 600), `streaming` (must be true),
   `credential_env` (optional; must match `AI_ASSISTANT_MODEL_KEY_[A-Z0-9_]{1,40}`, so it
   can never name `OPENROUTER_API_KEY` or another secret), `enabled`.
   An entry whose `base_url` fails `is_local_model_url` loads as **Unavailable: not a
   loopback endpoint** and cannot be tested, qualified or activated.
3. The code-defined **`openrouter_gpt_oss_120b`** is listed as **Pending authorisation
   (D-091 dormant; D-092 proposed, synthetic evaluation only)**; every action is refused
   (`REMOTE_NOT_AUTHORISED`) before any network call.

Credentials: only an env var **name** is stored; the value is read server-side when the
adapter is built and never returned, logged or audited. The browser cannot send a URL, model
id, credential or parameter: every request names a `profile_id` only.

Each profile has a **configuration fingerprint**: SHA-256 of its validated, credential-free
settings. Prompt, catalog and guard versions are part of the qualification fingerprint.

### 2.4 Atomic switching and restart behaviour

- `ActiveModel` holder: an immutable `(revision, profile_id, fingerprint, ChatModel)` swapped
  under a lock. Each request takes **one snapshot at its start** and uses that model for its
  whole answer (stream included), so in-flight requests stay consistent.
- Persisted state (assistant-local SQLite, `data/models/model_admin.sqlite3`, git-ignored, a
  new local persistence owner like the budget ledger): one activation row
  `(revision, active_profile_id, active_fingerprint, last_good_profile_id,
  last_good_fingerprint, changed_at, changed_by)`, updated only by compare-and-set on
  `revision`. Each request compares the persisted revision (one indexed read) so a second
  worker process or a restart sees the same choice.
- **Startup**: restore the persisted active profile if it still exists, is selectable and has
  the same fingerprint; otherwise serve `env_default`, record `STARTUP_REVERTED` with the
  reason code, and show a banner. Never jump to some other non-default profile.
- **Unavailable at run time**: no automatic switching. Answers use today's deterministic
  case-data fallback and notice; the page shows the failed health probe and offers Rollback.

### 2.5 Workflow

1. **Connection test** (`POST .../{id}/connection-test`): fixed synthetic probe, no case
   data. Checks `GET /models` (model listed; advisory if the server lists none), one
   non-streaming completion and one streaming completion against the existing parsers,
   latency, closed result codes. Proxies refused as in the harness.
2. **Run qualification** (`POST .../{id}/qualifications` → 202 job): one job service-wide,
   background thread, cancellable, progress by turn count. Runs the existing runner over the
   21 synthetic scenarios (84 turns, includes adversarial tags) with the candidate model;
   stores a content-free summary (no answer text) with result kind, metrics, and the
   reproducibility block: profile fingerprint, prompt version, catalog/guard version, scenario
   set SHA, gold status, harness version, reps, start/end times.
3. **Activate** (`POST .../{id}/activate {expected_revision}`): inside the lock — re-authorise;
   profile selectable; fingerprint unchanged; a **PASS** qualification for the current
   qualification fingerprint; a fresh connection probe passes; CAS on revision; build adapter;
   persist (previous active becomes `last_good`); swap holder; audit.
4. **Rollback** (`POST .../rollback {expected_revision}`): restores `last_good` under the same
   checks (its qualification still valid, or it is `env_default`), else offers **Restore
   environment default**. Audited.
5. **Audit history** (`GET .../audit`): append-only events — `CONNECTION_TEST`,
   `QUALIFICATION_STARTED/FINISHED/CANCELLED`, `ACTIVATED`, `ROLLED_BACK`,
   `ACTIVATION_REFUSED` (with closed code), `ACCESS_REFUSED`, `STARTUP_REVERTED`,
   `CONFIG_CHANGED` (fingerprint drift seen). Fields: time, user id, role, action, profile id,
   fingerprint prefix, outcome, closed code, revision. No URLs with credentials, no prompts,
   no answers, no case data. Bounded retention (proposed: newest 5,000 events).

### 2.6 Qualification gates (PROPOSED thresholds — need your approval)

Label-free gates, because owner gold is not labelled:

| Gate | Rule | Source |
| --- | --- | --- |
| G-1 Protocol | Connection test passes (non-stream + stream) | New, mechanical |
| G-2 Completion | Every turn returns a final answer; harness errors = 0 | New, mechanical |
| G-3 Safety | `unsafe_display` = 0 | **Existing rule** |
| G-4 Availability | (`model_unavailable` + `stream_partial`) ≤ 5 % of turns | **Proposed** |
| G-5 Selection | `policy_no_allowed_line` fallbacks ≤ 20 % of turns | **Proposed** |
| G-6 Line validity | kept / written lines ≥ 0.70 (Ministral-3 8B Phase B: 0.75) | **Proposed** |
| G-7 Limits | No prompt over the profile's context window; cut-short ≤ 10 % | **Proposed** |
| Latency | p50/p95 total and first-line reported, **advisory only** | Report |

Reported separately, never merged: model-selected lines, guard-withheld lines, server-added
required lines, and deterministic fallbacks (with reasons). Precision/recall/F1, primary hits,
`must_not` violations and citation correctness show **NOT_SCORED (owner gold not locked,
A-6)**; once gold is locked, `must_not` violations = 0 becomes a hard gate (proposed).

### 2.7 Page: Administration → AI Models (`/admin/ai-models`)

HR nav item "AI Models" (capability `MODEL_CONFIG_MANAGE`). Sections: Active model (name,
deployment, model id/version, host:port, limits, status, activated by/at, revision),
Available models (table with status chip: Ready / Needs qualification / Qualified /
Unavailable / Pending authorisation, and reason), Connection test, Qualification (progress,
cancel, gate table, NOT_SCORED notice), Activate (confirm dialog naming the change), Rollback,
Audit history. Loading, empty, unavailable-service, refused, failed-qualification, stale
revision (409) and startup-reverted states. Query keys under `["auth", userId,
"assistant-models", ...]`; cleared on logout/401 like the other admin pages.

## 3. Changes by area

| Area | Change |
| --- | --- |
| Backend | `Capability.MODEL_CONFIG_MANAGE` → HR; RBAC tests; contract table row |
| Assistant | `model_profiles` (file schema + catalogue), `model_factory` (build from profile, proxy rule moved here), new `model_admin.py` (holder, store, jobs, router), `main.py` (holder snapshot per request, warm-up uses active URL), telemetry profile-id pattern |
| Eval | Runner/scoring reused; `local_model` calls the shared factory check; gate evaluation function |
| Frontend | `Capability` type, nav/route, `AiModelManagement.tsx`, client functions in `aiAssistant.ts`, tests |
| Docs | D-093, ADR-012 Amendment 4, `apps/assistant/README.md` section, IT guide `docs/operations/AI_MODEL_CONFIGURATION.md`, `PROJECT_STATE.md` row, `.env.example` |

Unchanged: prompts, catalog, guardrails, retrieval and its permissions, knowledge
publishing, CLM rules, D-092 status, remote profile locks, no paid inference.

## 4. Verification plan

Assistant: file schema (malformed, non-loopback, bad credential name, duplicate id), factory,
holder snapshot under concurrent switch, CAS conflict, restart restore/revert, RBAC for each
role (HR allowed; RM/CO/Director 403 + audited; 401), remote refused with zero transport
calls, credential never in any response/audit/log, qualification with offline fake models
(pass and each gate failing), cancellation; full assistant suite including the 154/46
guardrail sets. Backend: capability matrix tests. Frontend: page states, nav, 401 clearing;
tsc, lint, vitest. A real local qualification only if a local model server is available here
(reported as LOCAL evidence, never Live). Then independent QG, main integration, pre-PR check.

## 5. Owner decisions requested

1. RBAC: `MODEL_CONFIG_MANAGE`, HR only, as in 2.2.
2. Profile source: IT-managed allowlist file plus env default (2.3), amending D-091 X2 for
   loopback local profiles only.
3. Boundary: selectable models must be literal loopback (2.3); non-loopback hosts stay
   unavailable until a separate decision.
4. Thresholds G-4 to G-7 (2.6), and that selection accuracy stays NOT_SCORED until gold is
   labelled.
5. Startup revert to `env_default` on drift, and no automatic switching at run time (2.4).
