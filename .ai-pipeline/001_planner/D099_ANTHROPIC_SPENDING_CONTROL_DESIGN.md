# D-099 follow-up: Anthropic spending-control design (Option B) and integration sequence

Status: **DESIGN FOR OWNER DECISION**. No code, guardrail, budget protection, key or Console
setting has been changed, no paid request has been made, and nothing is authorised by this
document. Date 2026-10-29 (SGT). It relates to draft PR #130 (D-099, Claude Sonnet 5.5
Balanced and Fast listed but not usable).

## 1. What the owner asked for

Option B, synthetic-only FYP development:

- a dedicated, non-default Anthropic workspace;
- a dedicated, non-admin inference API key in that workspace;
- a Console-enforced monthly workspace spend limit;
- a separate application ledger with conservative per-call reservations, settlement, a daily
  allowance and a lifetime cap;
- manual Console reconciliation with recorded owner attestation;
- fail-closed behaviour on incomplete requests, unknown usage, unexplained spending and
  provider mismatches.

Design targets: workspace US$5 per month, application lifetime US$5, daily allowance US$1,
20 calls per activation. No organisation Admin key in the chatbot runtime.

## 2. Control-by-control comparison with today's GPT-OSS (OpenRouter) protections

| # | GPT-OSS control today (decision) | Option B counterpart | Can the application verify it? | Gap |
|---|---|---|---|---|
| 1 | Provider-side key limit that is set, finite and never resets, read through `GET /key` before every paid start and raise (D-098 R8 `key.limit_finite`, R13) | Console workspace spend limit, enforced by Anthropic (requests over it get HTTP 400 "specified workspace API usage limits"); it **resets monthly** | **No.** A workspace API key cannot read the limit, the remaining amount or the reset date | Owner attestation replaces a machine check; the limit resets monthly, so it does not bound lifetime spend |
| 2 | Per-call verification from an independent provider record of serving provider, model and cost (generation metadata, D-092 P4, D-094 T3) | In-band only: the response's `model`, `usage` (tokens, `service_tier`, `inference_geo`, `speed`), plus the `anthropic-workspace-id` response header | Partly. Model, routing and **workspace** can be checked on every call; cost cannot (the application computes it from tokens times the published price) | No independent per-request cost record. A wrong price card or a billing error is caught only at manual reconciliation |
| 3 | Ledger anchored on, and reconciled against, the key's provider-reported cumulative usage (D-091 X5, D-098 R11, W3) | Ledger anchored at zero for a new dedicated key; owner-entered Console usage for that key and workspace, recorded as a reconciliation | No; the owner reads the Console | Reconciliation is manual and periodic, not automatic. The Console figure is rounded to cents and appears about 5 minutes after use |
| 4 | Pinned endpoint, no fallbacks, ZDR and data-collection deny, `max_price` (D-091 X4, D-092 P1) | Pinned `api.anthropic.com`, pinned model ID, explicit API version, no server-side model fallback, no `speed`, `service_tier` or `inference_geo` sent; any non-standard tier, geography or speed received is an anomaly | Yes (in-band) | No `max_price` equivalent: a price change is invisible until reconciliation. ZDR is not assumed, so the data stays synthetic-only |
| 5 | Breaker on anomaly, abandoned call, cost above reservation, routing mismatch; operator reconcile and reset (D-091 X5) | Same breaker codes in the application ledger, plus "workspace mismatch" and "reconciliation overdue" | Yes | — |
| 6 | Daily allowance and lifetime cap checked in one `BEGIN IMMEDIATE` admission (D-095 V7, D-096 W1, D-098 R8) | The same mechanism in the Claude ledger | Yes | — |
| 7 | Calls per activation (D-096 W2) | The same | Yes | — |
| 8 | Owner attestations: auto top-up off, prompt logging off (D-092 P3) | Owner attestations: auto-reload off, workspace limit value, dedicated non-default workspace, non-admin key, workspace ID | No (attested) | — |
| 9 | Synthetic boundary and eligibility tickets (D-094 T4, D-095 V2 to V5) | Unchanged; the Claude adapter already enforces them before sending | Yes | — |

**Strongest new control available to Option B.** Every Anthropic response carries
`anthropic-workspace-id`. The application can require it to equal the owner-attested
dedicated workspace ID on every call, and in a free preflight call (Models API). A key moved
to, or created in, the default or another workspace is then refused as a provider mismatch.
This verifies **which** workspace pays, though not its limit.

## 3. Sufficiency verdict

**Not equivalent.** Option B lacks two of the three provider-side controls that GPT-OSS relies
on:

1. a machine-verified, never-resetting provider limit;
2. an independent per-request cost record.

It replaces them with owner attestation, in-band checks and manual reconciliation. It must not
be described as equivalent.

**Sufficient for synthetic-only, owner-operated FYP development, subject to these
conditions.** The money at risk is bounded twice:

- by the application ledger, which is non-resetting and reservation-based;
- by Anthropic's own enforcement of the workspace monthly limit.

Data exposure is limited by the unchanged synthetic boundary. Under these conditions:

- **C-1.** A dedicated, non-default workspace; a key created in it; and no other key in that
  workspace. The owner records the workspace ID.
- **C-2.** The workspace monthly limit is at most US$5, the application lifetime cap is at most
  that limit, and auto-reload is off. All three are attested by the owner and recorded with a
  date.
- **C-3.** Every call checks `anthropic-workspace-id` against the attested ID, plus the pinned
  model, standard tier, global geography and standard speed. Any mismatch is charged
  conservatively and opens the breaker.
- **C-4.** Reconciliation gate: no qualification, activation or limit raise unless the last
  owner-recorded Console reconciliation is no more than 24 hours old (proposed) and within
  US$0.01 of the ledger. Chat calls stop when reconciliation is more than 7 days old
  (proposed). A Console figure above the ledger opens the breaker.
- **C-5.** Fail closed: unknown or missing usage, an incomplete stream, a timeout or a transport
  error after send are all charged at the full reservation.
- **C-6.** Revoke the key, and set the workspace limit to zero, when FYP development ends.
- **Residual risk the owner accepts:** a billing or price-card error is detected only at
  reconciliation.
  - Worst case per month if every application control failed: the workspace limit (US$5), plus
    any enforcement overshoot Anthropic allows (not documented).
  - Worst case over the project: the ledger's lifetime cap.

## 4. The proposed limits

The worst-case reservation per call is the prompt byte bound (up to `remote_max_prompt_bytes`
32,768 plus allowances, about 33,900 tokens at US$2/M, about US$0.068) plus 3,000 output tokens
at US$10/M (US$0.03). That is **about US$0.098**, under a US$0.10 per-call ceiling. The Phase B
prompts reserve about US$0.061. The measured actual cost per answer is about US$0.011 (Sonnet
Fast US$0.0106, Balanced US$0.0113; benchmark, Console-reconciled).

| Limit | Target | Effect |
|---|---|---|
| Workspace monthly (Console) | US$5 | Provider backstop. Resets monthly, so it is not a lifetime bound |
| Application lifetime cap | US$5 | Non-resetting. About 450 answers at measured cost; at least 50 even at full reservation |
| Daily allowance | US$1 | Open reservations count, one call at a time, so about 85 answers a day at measured cost |
| Calls per activation | 20 | 20 answers at about US$0.22 actual |
| Per-call reservation ceiling | US$0.10 (proposed) | Refuses a prompt that would reserve more |

The targets are internally consistent. **Recommendation:** keep the lifetime cap no greater than
the workspace limit. Raise the lifetime cap only after a reconciliation, and never above the
attested workspace limit.

## 5. Provider-specific policy changes that need the owner's approval

None of these is made yet. Each would be recorded as a new decision amending the named one.

| # | Change | Amends | Effect on existing protections |
|---|---|---|---|
| P-1 | For the Claude provider only, accept an owner-attested workspace limit in place of D-098 R8's machine-verified, never-resetting key limit | D-098 R8, R13; D-092 P3 | GPT-OSS keeps R8 unchanged |
| P-2 | For Claude only, accept in-band verification (model, routing, workspace) plus manual reconciliation in place of D-092 P4 generation-metadata verification (the G-8 equivalent) | D-092 P4; D-094 T2/T3 | GPT-OSS unchanged |
| P-3 | One ledger engine, two ledgers. Extend `budget.BudgetLedger` with a provider column or mode: Claude is anchored at zero for a new key and reconciled from owner-entered Console usage. One SQLite file per provider; never a shared ledger | D-091 X5 (`PROFILES`), D-095 V7, D-096 W1 to W3, D-098 R8/R11 | `budget.py` is a budget protection and basis file. The OpenRouter path must stay byte-identical in behaviour (proven by its existing tests) |
| P-4 | Claude key sources: `AI_ASSISTANT_ANTHROPIC_API_KEY` from the environment, the git-ignored `.env` and HR in-memory entry (as D-095 V8/V9). Accept only `sk-ant-api…`/`sk-ant-usr…`; refuse `sk-ant-admin…`, `oat` and `sid` | D-095 V8/V9, `key_sources.py` | Basis file. OpenRouter key handling unchanged |
| P-5 | HR spending controls per provider: daily, calls and lifetime (W1 to W5). A lifetime raise needs the reconciliation gate (C-4) in place of the `/key` check | D-096 W3, W5; D-098 R8, R11 | GPT-OSS controls unchanged |
| P-6 | Extend D-098 R6 ("GPT-OSS-only": a remote model that cannot serve becomes *AI unavailable*, never another model) explicitly to Claude, and confirm no automatic switching between providers | D-098 R6, R14 | Already true in code (`is_remote`); recorded as policy |
| P-7 | Synthetic boundary regeneration for the new strings these modules add (as approved for PR #130's seven words) | D-094 T4 data | Basis change |

Not proposed:
- an organisation Admin key anywhere in the chatbot runtime (or in the repository);
- automatic Console scraping;
- any change to GPT-OSS limits, preflight, verification or eligibility.

An optional owner-run, offline reconciliation helper using an Admin key is possible later. It
is not recommended now: manual Console entry is enough at these amounts.

## 6. Future enablement plan (implementation work, after P-1 to P-7 are approved)

1. **Adapter (`anthropic_chat.py`):**
   - QG **F1**: reject a second `message_start` as a protocol error and drop the cost;
   - QG **F2**: check `synthetic_eligibility.mode(settings)` on every call, as `remote_test.py`
     does;
   - check `anthropic-workspace-id` against the attested ID;
   - add `profile_id`/`endpoint_slug` once telemetry accepts them.
2. **Ledger (P-3):**
   - a provider-aware `BudgetLedger`;
   - a Claude ledger file;
   - reservation with `anthropic_chat.reservation_micro_usd`;
   - settlement from usage;
   - breaker codes `workspace_mismatch` and `reconcile_overdue`;
   - a `budget_ledger.py reconcile --provider anthropic --console-usage-usd` command with an
     owner attestation record.
3. **Credentials (P-4):** key sources and HR key entry for Anthropic, with admin, `oat` and
   `sid` shapes refused.
4. **Preflight and connection test (free):**
   - Models API (id, limits, `between_tools` support);
   - the workspace header;
   - token counting for the qualification manifest;
   - owner attestations;
   - reconciliation freshness;
   - ledger health and room.
5. **Model management (QG F3):**
   - route the code-entry branches (connection test, paid qualification and its confirmation,
     activation probe, interrupted-run billing) by provider;
   - no Claude entry may reach `remote_test.RemoteTestModel`.
6. **Qualification:**
   - D-094 T2 manifest with G-1 to G-7;
   - a Claude G-8 (every call settled from usage, with model, routing and workspace verified);
   - tied to each configuration's fingerprint;
   - decision 6a unchanged.
7. **Telemetry:** add the Claude profile ids to `PROFILE_IDS`, a provider code and the requested
   endpoint.
8. **`model_qualification.BASIS_FILES`:** add `anthropic_chat.py`, `anthropic_profiles.py` and
   the ledger and key modules.
9. **Frontend:**
   - an Anthropic key card and spending card;
   - the attested workspace and reconciliation age;
   - reconcile and attest actions (HR only, Origin required, audited).
10. **Catalog gaps** (only if authorised separately):
    - P06#1 address-change refusal;
    - P01#0 case UEN line;
    - P04#0 review versus submission;
    - the UBO-completion refusal as a required line.
11. **Tests and gates:**
    - offline tests for every item above;
    - the OpenRouter regression unchanged;
    - an independent QG;
    - then one owner-approved paid qualification per configuration to be offered.

## 7. Avoiding repeated paid GPT-OSS requalification

Facts:
- The qualification basis hashes the answer code, the guardrail and boundary files and the
  evaluation fixtures.
- Any change to them makes every qualification out of date.
- At start-up an active GPT-OSS configuration then becomes *AI unavailable* until it is
  requalified (a paid run with its own approval).
- This check must not be bypassed.

GPT-OSS Balanced was requalified on basis `b4049047884e…` (PR #129's code). PR #130 moves the
basis to `235030035ccc…`. The enablement work in section 6 moves it again (items 1 to 4 and 8
are basis files), and so would any catalog change (item 10).

**Recommended sequence (fewest paid requalifications, no check bypassed):**

1. **Keep PR #130 a draft; do not merge it on its own.** Merging it now would cost one GPT-OSS
   requalification just to list two configurations that cannot be used.
2. Decide P-1 to P-7 (and whether the catalog gaps are in scope).
3. Build the enablement on the PR #130 branch (or a branch stacked on it) as one change set:
   adapter fixes, ledger, keys, preflight, routing, telemetry, `BASIS_FILES`, the catalog lines
   if authorised, and one final boundary regeneration.
4. Integrate with the latest `main` once, then run one independent QG and the pre-PR check.
5. Merge once. The basis changes once.
6. Then run, under one approval, the paid requalifications in one session:
   - GPT-OSS Balanced (and Fast if used): about 3 calls, roughly US$0.07, per the #129
     procedure;
   - Claude Balanced and Fast.

That gives **one** GPT-OSS requalification in place of two or three.

- **If the Claude enablement is not wanted soon:** keep #130 a draft until the next change that
  moves the basis anyway, and merge them together.
- **If the owner wants the listing on `main` now:** merging #130 alone is safe, but costs one
  extra GPT-OSS requalification.

## 8. Open questions for the owner

1. Approve Option B with conditions C-1 to C-6 and the limits in section 4, accepting the
   residual risk stated in section 3?
2. Approve policy changes P-1 to P-7 (each as a new decision), or which of them?
3. Reconciliation cadence: 24 hours before paid starts and raises, and 7 days for chat?
4. Are the catalog gaps in the same change set, so GPT-OSS is requalified once?
5. Keep PR #130 a draft until the enablement is ready (recommended)?
