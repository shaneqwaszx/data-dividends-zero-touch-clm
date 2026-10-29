# D-099 (proposed): Claude Sonnet 5.5 Balanced and Fast on AI Models (listed, not usable)

Date: 2026-10-29 (SGT). Worktree
`C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029`, branch
`feat/assistant-claude-sonnet-console`, base = PR #129 head `c2630cd` (re-verified before
starting; PR #129 untouched). Assignment: "Claude Sonnet 5.5 Balanced/Fast Integration"
(bounded development, offline verification only; no paid call, activation, guardrail change,
PR merge). Evidence class: mock and offline only.

**Status.**
- The bounded integration keeps both profiles visible but unusable.
- **Blocker B2 is resolved:** the owner approved the boundary regeneration on 2026-10-29 with
  conditions (section 3).
- **Blocker B1 stays open:** the Anthropic spending-control design. Until the owner approves and
  verifies it, Sonnet Balanced and Fast remain unavailable.
- The qualification basis is now `235030035ccc27e28320f35c4b887cdd04735f02692feb88ad0745666cfe1927`
  (was `b4049047884e…`).
- **GPT-OSS impact:** every previously qualified GPT-OSS configuration (Balanced and Fast) needs
  requalification after this merges.

## 1. Verified configurations

Both are configurations of one model, `claude-sonnet-5-5`. Fast is not a separate model.

| | Balanced (recommended) | Fast |
|---|---|---|
| Profile id | `anthropic_claude_sonnet_5_5_medium` | `anthropic_claude_sonnet_5_5_low` |
| Request | `thinking: {type: adaptive}`, `output_config.effort: medium` | `thinking: {type: between_tools}`, `output_config.effort: low` |
| Shared | `https://api.anthropic.com/v1/messages`, `anthropic-version: 2026-10-21`, `max_tokens` 3,000, 90 s; no sampling parameters, tools, metadata, service tier, speed, inference geography or server-side fallback | same |
| Price | US$2 input / US$10 output per million tokens; thinking billed as output | same |
| Evidence | Benchmark run 1 (51 calls), speed round (34 calls), owner scores (both 2.75) | same |

Sources:
- the benchmark configurations (`CLAUDE_API_MODEL_BENCHMARK.md` sections 9 and 10; local
  commits `7fd0e43`, `cb9b996`, `5964ea2`, not part of this branch);
- the Models API preflight (id, 1M context, 128K output; `between_tools` reported supported);
- the pricing page read 2026-10-29;
- the SDK 2.3.0 API version.

Each configuration's fingerprint covers provider, base URL, API version, every request field,
timeout and prices. The two fingerprints differ from each other and from GPT-OSS's.

## 2. Provider and spending compatibility verdict: NOT EQUIVALENT

| Control GPT-OSS relies on (OpenRouter) | Direct Anthropic API key | Verdict |
|---|---|---|
| A readable key limit: `GET /key` must show a finite limit that never resets (D-098 R8 `key.limit_finite`), and calls must fit within it | Organisation and workspace monthly spend limits are set in the Console and enforced by Anthropic (HTTP 400 `invalid_request_error` or 429 `enforced_spend_limit_reached`), but **no API exposes them to a normal key** | Missing; only owner attestation is possible |
| Per-call verification from a separate provider record of model and cost (D-092 P4: generation metadata) | Only in-band data: `message.model` and `usage` tokens. No per-call cost record | Missing: the model can be pinned in-band, but cost is computed locally from tokens × published price |
| Ledger anchored on, and reconciled against, provider-reported cumulative usage (D-091 X5) | Usage and cost only through the **Usage & Cost Admin API**, which needs an organisation Admin key (`sk-ant-admin…`, which can also manage keys and members). Data arrives after about 5 minutes; cost is reported per day only | Missing with a normal key; possible only with an Admin credential |
| Breaker and reconciliation tooling | `BudgetLedger` accepts only `openrouter_gpt_oss_120b` (`PROFILES`) and needs provider usage | Reuse would change `budget.py`, a budget protection and basis file: approval needed |

So the profiles stay **unavailable** (section 3, B1), and no Claude budget ledger, key source
or HR key entry was added.

## 3. Blockers and the smallest changes needing approval

- **B1. Provider spending controls.** Choose one of:
  - **(a)** An organisation Admin key held server-side, used only for the Usage API (per key,
    1-minute buckets) to verify each call's tokens and model after about 5 minutes, and the
    Cost API for daily reconciliation. Strongest, but a highly privileged credential.
  - **(b)** A dedicated Console workspace with a spend limit the owner attests, a local
    Claude ledger capped at that attested limit, and manual Console reconciliation (as done
    in the benchmark). Simpler, but the limit is not machine-verified.
  - **(c)** Both.

  Any of these needs a Claude ledger: either a new module, or `budget.py`'s `PROFILES` widened
  (a basis change, so requalification).
- **B2. Synthetic boundary regeneration (RESOLVED: owner-approved 2026-10-29, applied).**
  `scripts/build_synthetic_boundary.py` turns every
  string constant in `ai_assistant/` into allowed system-message vocabulary, and a test requires
  the file to be current.
  - I cut the change to the unavoidable minimum:
    - the new modules' docstrings are written as comments;
    - the ids name the effort (the page shows "Balanced" and "Fast", as D-097 Y2 does for
      GPT-OSS);
    - incidental words were removed.
  - What remains: **seven words added to `code_vocabulary`, none removed, no other section
    changed**: `adaptive`, `anthropic`, `claude`, `com`, `geo`, `sonnet`, `thinking`.
  - Regenerating is a boundary and qualification-basis change. A GPT-OSS requalification made
    on PR #129's basis (`b4049047884e…`) would be out of date once this merges.
  - Applied under the owner's conditions:
    - the existing generator was used, with no manual edit;
    - the diff is exactly these seven lines added to `code_vocabulary`;
    - nothing was removed;
    - schema, note, company, documents, viewers, values, knowledge, `conversation_vocabulary`,
      `prompt_vocabulary`, the generator and `synthetic_boundary.py` are unchanged;
    - `--check` reports the file current.
  - New basis: `235030035ccc…`.

Remaining: decide B1 as a separate task. It is the real enabling decision; no Anthropic runtime,
spending-control change, provider call or paid qualification is authorised.

## 4. Implemented (uncommitted) and reused

New:
- **`ai_assistant/anthropic_profiles.py`:** the two configuration records, `identity()` for
  fingerprints, and `availability()`. Without the decision the status is
  `pending_authorisation` (`ANTHROPIC_NOT_AUTHORISED`); with `AI_ASSISTANT_ANTHROPIC_DECISION=D-099`
  it is `unavailable` (`ANTHROPIC_PROVIDER_CONTROLS_MISSING`). It is never selectable.
- **`ai_assistant/anthropic_chat.py` (dormant adapter):**
  - accepts only an in-memory mock transport; `build()` always refuses;
  - checks the D-095 V5 ticket or the D-094 text check before sending;
  - sends the leading system messages as system blocks unchanged, and refuses a system message
    after history;
  - enforces a prompt byte bound;
  - pins the model at `message_start`, before any text;
  - treats a non-standard tier, geography or speed as `provider_mismatch` (routing anomaly);
  - treats cache tokens or missing counts as malformed or missing usage, with the cost dropped;
  - computes cost as tokens × published price;
  - maps a refusal to `content_filter` and `max_tokens` to cut short; an unfinished stream is
    `upstream_midstream` with no cost;
  - maps spend limits to `payment_key_limit`; other errors to closed classes, with no retry;
  - never yields thinking;
  - provides `reservation_micro_usd()`, using the same bound as `budget.reservation_for`.
- **`model_catalog._claude_entries`:** the two entries (deployment `anthropic`, closed-code
  details). The Claude ids are reserved against IT profiles files.
- **Settings:** `AI_ASSISTANT_ANTHROPIC_DECISION`.
- **AI Models page:** provider "Anthropic API", the thinking mode, two reason texts and a
  scope label.
- **Secret scanner:** the Anthropic key shapes and the two variable names (ported from the
  benchmark).
- **Documentation:** D-099 (PROPOSED) and `AI_MODEL_CONFIGURATION.md` section 13.

Reused unchanged: `require_offline_transport` (D-091 L1), the bounded SSE reader
(`OpenAICompatibleChatModel._sse_frames`), the strict JSON and count helpers and
`MAX_ERROR_BODY_BYTES` from `openrouter.py`, `check_messages` (D-094),
`synthetic_eligibility.admitted` (D-095), `budget.PER_MESSAGE_OVERHEAD` / `TEMPLATE_OVERHEAD`,
and the model-management status gate. `entry_for` refuses every action on a non-selectable
entry and audits it; `_build_stored` never builds one; `is_remote()` sends an unbuildable stored
code entry to *AI unavailable* (D-098 R6), never to another model. **No change to
`model_admin.py`, `budget.py`, `remote_test.py`, guardrails, prompts, catalog lines or any basis
file.**

Prerequisites before Claude could ever be enabled, recorded rather than built:
- route model management's code-entry branches (connection test, paid qualification, activation
  probe, interrupted-run billing) by provider;
- add the Claude ids to telemetry `PROFILE_IDS`;
- implement a Claude key source and ledger;
- add the adapter to `BASIS_FILES`;
- fix QG F1 (reject a second `message_start`, drop the cost) and F2 (check
  `synthetic_eligibility.mode(settings)` on every call, as `remote_test.py` does).

## 5. Tests (offline)

- `tests/test_claude_console.py`: 41 tests.
  - **Console behaviour:** both configurations listed with accurate details; the decision
    changes only the reason; every action refused before any network call and audited (6
    refusals); RM, Client Onboarder and Director forbidden; distinct and stable fingerprints,
    never GPT-OSS's; a pass of one configuration never counts for the other or for GPT-OSS; a
    tampered stored activation becomes AI unavailable; IT files cannot take the ids; the service
    never composes the adapter.
  - **Adapter:** transport lock; pinned request for both configurations; settled cost; model
    mismatch stops before any text; six billing-uncertainty cases drop the cost; refusal,
    truncation and an unfinished stream; seven provider-error classes with no retry; timeout;
    three refusals before sending; the reservation bound.
  - **Through the real service:** the exact-line guard shows an allowed line and withholds
    prose; the P06#2 completion claim is withheld, and the offered refusal line is kept when
    selected.
- Updated existing tests (composition only, assertions not loosened):
  - `test_model_management` lists the two Claude entries explicitly;
  - `test_reasoning_configurations` selects GPT-OSS by deployment or id instead of "the only
    code entry".
- Frontend: `AiModelManagement.test.tsx` 41 of 41 (2 new); `tsc -b` clean.
- ruff, format and strict mypy clean on the new and changed files. The remaining mypy errors
  are on unchanged lines of two existing test modules this work imports (`remote_fixtures.py`
  and `test_model_management.py`, whose only edit here is the composition assertion); the same
  `test_model_management.py` errors occur on base `c2630cd`.
- Secret-scanner tests 33 of 33; repository scan clean.
- Before B2: the regression set (17 suites) ran 798 tests, with 797 passed. The one failure was
  the boundary-currency test.
- After the owner-approved B2 regeneration (final candidate):
  - the 108 boundary and eligibility tests pass, including the currency test and every refusal
    category;
  - a new test shows the seven words never widen question or history text;
  - the **full assistant suite** ran 2,698 tests, with 14 failures, all
    `OSError: [Errno 24] Too many open files`;
  - the Errno 24 failures are the known Windows file-handle limit in a long run. Their four test
    files, re-run on their own, pass 289 of 289;
  - frontend 41 of 41, `tsc -b` clean, secret-scanner tests 33 of 33, repository scan clean.
- **Independent QG: PASS** on the exact candidate (`D099_CLAUDE_SONNET_CONSOLE_QUALITY_GATE.md`;
  diff SHA-256 `c5b20254…`). It found no Critical, High or Medium issue. Its findings:
  - **F1 (Low):** a repeated `message_start` is not rejected.
  - **F2 (Low):** the eligibility-ticket mode is fixed at construction rather than checked on
    every call.
  - F3 to F5 (Info): see the QG report.

  F1 and F2 cannot be reached while the adapter is dormant. They are recorded as enablement
  prerequisites (section 4) and were not changed, so the reviewed content stays identical.
- **Integration:** PR #129 was squash-merged to `main` as `8c7ea99` during this work, with a tree
  identical to `c2630cd`. The reviewed commit `1c515e8` was merged with `origin/main` (merge
  `5d70ceb`). Three documentation conflicts arose only because the squash shares no history with
  `c2630cd`. In each, `main`'s file is byte-identical to `c2630cd`'s, so our side was kept. The
  merged tree equals the reviewed tree (`750cac42…`).

## 6. Catalog issues (inspection only; nothing changed)

| Gap | Evidence | Recommended additive change (owner wording needed) | Affects |
|---|---|---|---|
| P06#1: no refusal of a registered-address change | Only `APPROVAL_NOT_OFFERED` and `UBO_COMPLETION_NOT_OFFERED` exist (`guide.py`) | An "is not offered" line for changing a registered address, pointing to the Document verification decision; an action topic in `prompts.topic_plan` that offers it, marked **required** | `guide.py`, `guardrails.allowed_guidance`, `prompts.py` |
| P01#0: no line with the case's UEN | `UEN_MEANING` is generic; the UEN is in the case facts but no allowed line carries it | A case-value line (for example `The UEN on this case is <uen>, from <registry source>.`) allowed only for a registry-sourced UEN, on the P11 provenance pattern | `guide.py`, `guardrails.py`, `context.py`; the boundary values may change |
| P04#0: review versus submission readiness | The READINESS topic leads with `NOT_READY` ("not ready for GoldTier submission") | A line separating "waiting for a person's review" from "ready for GoldTier submission", routed for "ready for review" questions | `guide.py`, `guardrails.py`, `prompts.py` |
| Deterministic action refusals | `APPROVE` topics already make `APPROVAL_NOT_OFFERED` required (D-090 `with_required_lines`). The UBO-completion topic is steer-only (its plan requires no line), which is why fast Sonnet could omit it | Make `UBO_COMPLETION_NOT_OFFERED` (and the new address line) **required** in their topic plans, using the existing D-090 mechanism; no new mechanism | `prompts.py` |

**Fingerprint and basis impact of any of these:**
- they change basis files (`guide.py`, `guardrails.py`, `prompts.py`, `context.py`);
- they also change the basis fixtures (`snapshots.json` must be rebuilt, and gold or lock files
  where present);
- `synthetic_boundary.json` may change (new words);
- so **every** qualification would be out of date: GPT-OSS Balanced and Fast, and any future
  Claude configuration;
- the prompt-size bound in `test_speed` (9,250 characters) needs checking.

B2 has been applied on its own. Any of these changes moves the basis again. If they are
authorised, schedule them before the GPT-OSS requalification so it happens once.

## 7. Change statement

- **Changed:**
  - API: overview lists two more entries;
  - configuration: one new optional setting;
  - frontend labels;
  - secret-scanner rules.
- **Unchanged:**
  - schema;
  - connector;
  - business rules;
  - mapping;
  - authentication, RBAC and security controls;
  - GPT-OSS behaviour, prompts, settings and qualification;
  - budget protections;
  - guardrails and the catalog;
  - provider status (no Live claim);
  - runtime answer behaviour (no Claude answer can be served).
