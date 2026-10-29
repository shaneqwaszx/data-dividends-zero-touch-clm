# D-099 Option B: Anthropic-specific spending safeguards (implementation report)

Date: 2026-10-29. Branch `feat/assistant-claude-sonnet-console` (draft PR #130, kept draft).
Base: PR #130 head `541b10f` (main `8c7ea99` merged in `5d70ceb`). Authority: the owner's
explicit approval of D-099 Option B and P-1 to P-7 (implement offline; fresh independent QG;
latest-main integration; final gate and pre-PR; local commit only, no push).

**Not authorised and not done:** paid inference, paid qualification, real-data transmission,
runtime activation, automatic provider switching, push, PR merge, production deployment. No
organisation Admin key is introduced into the runtime. No frontend file changed (D-100 UI
isolation). Evidence class: **Mock/offline only** — no Live, Sandbox or provider-status claim.

## 1. Policy as implemented (not equivalent to OpenRouter)

| Approved policy item | Where enforced |
| --- | --- |
| Dedicated non-default workspace; workspace-scoped non-admin inference key | owner attestations `dedicated_workspace`, `inference_key_only`; workspace id format `wrkspc_…` (refuses `default`); key shape `sk-ant-api..-` / `sk-ant-usr-` only, `sk-ant-admin…` refused as `CREDENTIAL_ADMIN_REFUSED`, OAuth/session tokens invalid (`anthropic_runtime.resolve_key`) |
| Workspace monthly cap ≤ US$5, owner-attested | `AI_ASSISTANT_ANTHROPIC_WORKSPACE_LIMIT_MICRO_USD` 1..5,000,000 (pydantic bound and run-time re-check), attestation `workspace_limit_set` |
| Separate Anthropic ledger, non-resetting US$5 lifetime ceiling | profile `anthropic_claude_sonnet_5_5` in its own file; ledger cap must be ≤ min(US$5, attested workspace limit) and above its opening usage on every preflight; CLI `--anthropic init` and cap raises refuse above US$5 |
| US$1 daily cap; 20 calls per activation | `AI_ASSISTANT_ANTHROPIC_DAILY_CAP_MICRO_USD` ≤ 1,000,000 and `AI_ASSISTANT_ANTHROPIC_MAX_CALLS` ≤ 20 (settings bounds and run-time re-check); the daily cap is enforced inside the ledger's admission transaction |
| Conservative full-reservation accounting on uncertain billing | unchanged `budget.settle`: no complete usage ⇒ charged at the full reservation; in-band verification quarantines every unsettled or anomalous call and opens the breaker |
| Verify workspace ID, requested model, routing metadata | every reply: `anthropic-workspace-id` header = attested id before the body is read; `message_start` model = `claude-sonnet-5-5` before any text; non-standard tier, geography or speed ⇒ routing anomaly; a second `message_start` ⇒ protocol error, cost dropped (QG F1); the free preflight checks the workspace header and the model on `GET /v1/models/claude-sonnet-5-5` |
| Manual reconciliation ≤ 24 h before paid qualification, activation, limit raises; ≤ 7 days for chat | `ledger.reconciled_recently` check: 7 days for chat calls and connection tests; 24 hours for the paid-qualification estimate and start, the qualification process, the activation/rollback probe and CLI cap raises |
| Fail closed on stale reconciliation, provider mismatch, missing billing evidence | never reconciled or stale ⇒ refused before any request; mismatch ⇒ quarantine + breaker; missing ledger/usage ⇒ refused or charged in full + breaker; qualification start maps `RECONCILIATION_STALE`/`LEDGER_PROFILE_MISMATCH` to `QUALIFICATION_BILLING_UNRECONCILED` |
| No automatic Claude-to-GPT-OSS switching | a refused or failed Claude call gives the deterministic case-data answer; an unusable stored Claude activation becomes *AI unavailable* (R6 extended); tests assert zero OpenRouter and baseline calls |
| Revoke the inference key at the end of the FYP | owner attestation `key_revoked_at_fyp_end` (an owner action; recorded in D-099 C6) |

**Scope:** verified synthetic development cases only, the same cases GPT-OSS may answer: the
chat applies the unchanged D-094 boundary / D-095 eligibility to a Claude model
(`requires_synthetic_boundary`), and the model re-checks admission per call; the adapter decides
again for the very messages it sends (QG F2). Development machines only, behind the D-094,
D-091 and D-092 interlock plus D-099. Never real data.

**Residual billing risks (owner-accepted, D-099 C9):** the workspace limit and dedication are
attested, not read; reply usage is Anthropic's own claim (no separate per-call record);
Console usage is reconciled by hand, so drift can persist up to the window, bounded by the
daily cap, the ledger ceiling and the workspace limit Anthropic enforces.

## 2. Exact changes (P-1 to P-7 and the enablement prerequisites)

| File | Change |
| --- | --- |
| `ai_assistant/anthropic_chat.py` | F1 second `message_start` ⇒ `protocol`, `usage_repeated`, cost dropped; F2 per-call `admit` callable (default: D-094 text check); Claude-only `LIVE_NETWORK` marker (requires the attested workspace); `anthropic-workspace-id` check before the body (`provider_mismatch`); wrapper properties for the unchanged `BudgetedChatModel` (`profile_id` = ledger profile, `endpoint`, `endpoint_slug`, `max_tokens`, `max_prompt_bytes`); `build()` removed |
| `ai_assistant/anthropic_profiles.py` | `LEDGER_PROFILE_ID`, `ENDPOINT` (US$2/US$10, `max_tokens` 3,000 includes thinking, no request price); `availability()` delegates to `anthropic_runtime.readiness` (selectable only when ready); header rewritten for Option B |
| `ai_assistant/anthropic_runtime.py` (new) | readiness; key resolution (environment, then `.env`); ledger checks; in-band `verify_calls`; reconciliation window; `check_cap_change`; free preflight; `connection_check`; read-only `budget_status`; `ClaudeTestModel` (per-call admission, prompt-shape check before reservation, key pinning, call limit, preflight reuse, verification after each call, Claude notices) |
| `ai_assistant/budget.py` | `PROFILES += (anthropic_claude_sonnet_5_5,)`; `reserve(profile_id=…)` refuses a reservation for another profile inside the admission transaction (`refused_ledger`) and `BudgetedChatModel` always passes its adapter's profile; read-only `last_reconciled_ms()`. OpenRouter semantics otherwise unchanged; existing ledgers keep their CHECK and work (tested) |
| `ai_assistant/config.py` | `anthropic_owner_attests`, `anthropic_workspace_id`, `anthropic_workspace_limit_micro_usd` (≤ 5,000,000), `anthropic_ledger_path`, `anthropic_daily_cap_micro_usd` (≤ 1,000,000), `anthropic_max_calls` (≤ 20) |
| `ai_assistant/model_catalog.py` | Claude entries selectable when ready; scope = GPT-OSS's (`APPROVED_SYNTHETIC_CASE` / `VERIFIED_SYNTHETIC_CASES`) |
| `ai_assistant/model_admin.py` | routing by `deployment == "anthropic"`: stored build (`ClaudeTestModel`, HR controls never applied), connection test (7 days), paid estimate (Anthropic `budget_status`, 24 h), qualification refusal mapping, activation/rollback probe (24 h), interrupted-run billing check on the Anthropic ledger, `calls_used`; Claude ids join `REMOTE_PROFILE_IDS` (R6) |
| `ai_assistant/main.py` | lead notices from the model (`notices`); GPT-OSS strings byte-identical; Claude refusal notices recognised |
| `ai_assistant/telemetry.py` | Claude profile ids (and the ledger profile for the bare adapter) are valid metric codes |
| `ai_assistant/model_qualification.py` | `BASIS_FILES` += `anthropic_chat.py`, `anthropic_profiles.py`, `anthropic_runtime.py` |
| `assistant_eval/qualification.py` | Claude runs via `ClaudeTestModel` (24 h reconciliation) with its own connection check and G-8 rule; GPT-OSS path unchanged |
| `scripts/budget_ledger.py` | `--anthropic` (path and profile); init refuses a cap above US$5; on an Anthropic ledger (by its profile, whatever path) cap changes are compare-and-set, never above US$5, and raises need a reconcile within 24 h; status shows profile and last reconciliation |
| `ai_assistant/synthetic_boundary.json` | regenerated with the existing generator: `code_vocabulary` + `ant`, `usr`, `wrkspc` |
| tests | `test_claude_runtime.py` (new, 57 cases), `test_claude_console.py` (updated + new adapter cases; 50 cases), `test_budget_ledger.py` (API-surface list), `test_phase_b_live.py` (L4 live-marker allowlist extended by exactly `anthropic_chat.py` and `anthropic_runtime.py`; the OpenRouter entries unchanged — a guard-test change flagged for the gate) |
| docs | `DECISION_LOG.md` D-099 C6–C9, `AI_MODEL_CONFIGURATION.md` §13, `PROJECT_STATE.md` |

Deferred (documented, not built): HR in-memory Claude key entry and HR-editable Claude limits
(P-5 UI) — frontend work kept out until the D-100 UI phase is ready for integration.

## 3. Boundary regeneration (P-7) and qualification basis

Generator `scripts/build_synthetic_boundary.py` unchanged. Diff against the PR #130 file:
`code_vocabulary` +3 (`ant`, `usr`, `wrkspc`); nothing removed; `conversation_vocabulary`,
`prompt_vocabulary`, company, documents, viewers, values and knowledge **unchanged**. Two
further candidate words (`hours`, `revoke`) were removed by rewording before acceptance. Each
remaining word is an identifier fragment of an approved format check (inference-key prefix
`sk-ant-api..`/`sk-ant-usr-`, Admin-key refusal `sk-ant-admin`, workspace id `wrkspc_…`). They
admit nothing in a question or assistant history (tested), and no eligible-case or client-data
rule changed. **Owner acknowledgement of these three words is requested before publication.**

Qualification basis: `235030035ccc…` (PR #130) → `72b681dc85e83ee435a07b7e35cb7f6e6b5e4a03b65ffaf2d0eb428408b9b30e`
(recomputed after the final edits; see §4). Every GPT-OSS qualification is out of date once
merged; Claude configurations need their own paid qualification (separately authorised).

## 4. Evidence (offline, pre-gate)

- Focused and regression modules (Claude runtime and console, Phase B live guards, budget
  ledger/CLI/guard/daily, model factory, telemetry, eligibility, GPT-OSS remote test mode,
  reasoning configurations, model management): **595 passed, 0 failed** on the final content.
- Full assistant suite (run before the last two edits: the Claude attestation code and the L4
  allowlist): 2,764 tests, 15 failures — 14 Windows `Errno 24` (too many open files) in
  `test_model_factory`, `test_required_p2`, `test_streaming_resources`, all passing when re-run
  in isolation, plus the L4 allowlist test, since updated and passing.
- `ruff check`, `ruff format --check`, `mypy` on all 15 touched Python files: clean.
  `scripts/check_secrets.py`: pass. `build_synthetic_boundary.py --check`: current.
  `git diff --check`: clean; EOL churn checked (`--stat` equals `--ignore-cr-at-eol`).
- Qualification basis at that point: `e8d149ade8f8…` (superseded by the remediation; see 4a).
- A late fix found during testing: the service's follow-up prompts put knowledge/topic system
  messages after history, which the adapter refuses by design; under the runtime that refusal
  would have come after reservation and opened the breaker. The runtime now refuses such a
  prompt before anything is reserved (no spend, no breaker). All 17 Phase B qualification
  prompts have a valid shape.
- A label fix: Claude's attestation refusal is its own code (`ANTHROPIC_ATTESTATION_MISSING`), so
  the page never shows GPT-OSS's "auto top-up and prompt logging" text for it. New Claude
  reason codes have no page labels yet (shown as codes; UI deferred with D-100).

## 4a. Remediation after the first independent gate (FAIL, `D099_OPTION_B_QUALITY_GATE.md`)

Reviewed commit `778b468` (tree `fcdb0d6d`). Fixed in the remediation commit:

- **M-1 (Medium):** ledger isolation now covers recovery and verification, not only admission.
  The Claude preflight checks the ledger profile before `recover()`/`verify_calls()` and stops on
  a mismatch; `verify_calls` refuses a non-Anthropic ledger; Claude readiness refuses when the
  two ledger paths resolve to one file (`LEDGER_PATH_SHARED`); the GPT-OSS preflight
  (`remote_checks.run_preflight`) refuses a non-OpenRouter ledger before recovering or verifying
  it (`ledger.healthy` refused `LEDGER_PROFILE_MISMATCH`); the HR lifetime-cap endpoint refuses a
  non-OpenRouter ledger (`LEDGER_UNAVAILABLE`). These only add refusals to GPT-OSS paths.
- **L-1:** Claude check names classified for HR (billing: `ledger.profile`,
  `ledger.reconciled_recently`; configuration: `anthropic.ready`, `anthropic.inference_key`,
  `anthropic.workspace_matches`, `anthropic.model_available`, `ledger.cap_within_ceiling`).
- **L-2:** the remembered preflight records its key marker; the spending view ignores another
  key's result, and a key change clears it.
- **L-3:** tests added for the D-095 ticket path (used once; no effect without D-095 mode) and
  both isolation directions, the shared path, the HR cap refusal, the key-tied preflight and
  the diagnosis.

Evidence on the remediated tree: 815 passed / 0 failed across the Claude, Phase B live, budget,
model factory, telemetry, eligibility, GPT-OSS remote test, reasoning, model management,
spending controls, D-098 recovery and OpenRouter adapter modules; boundary current (no new
word); ruff, format, mypy clean. Basis `72b681dc85e8…`.

## 5. Unresolved / for the owner

1. Acknowledge the three new `code_vocabulary` words (`ant`, `usr`, `wrkspc`).
2. Acknowledge the L4 guard-test allowlist extension (two Claude modules).
3. Claude answers first questions only in practice (follow-ups with history fall back to case
   data) until a separately approved prompt-shape change.
4. Call-limit check and reservation are not one transaction (same as GPT-OSS): a narrow race
   could allow one call above 20 if two requests interleave exactly; the ledger's single
   in-flight call and the money caps still hold.
5. HR key entry and HR-editable Claude limits, and page labels for the new codes, deferred
   (D-100 UI isolation).
6. Paid qualification, activation and the first live preflight (which must confirm the
   `anthropic-workspace-id` header and the workspace-id format on the real API) remain
   unauthorised.

Gates: fresh independent QG, latest-main integration, final gate and pre-PR are recorded in
their own reports.
