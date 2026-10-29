# AI Assistant model configuration — guide for IT administrators

Decision: D-093 (accepted for the local-only POC scope; ADR-012 Amendment 4). Classification:
`LOCAL`. Nothing here enables a remote or cloud model, except the owner's separately recorded
D-094 local synthetic test mode on a development machine (section 9) and its D-095 development
synthetic mode, OpenRouter key sources and US$1.00 daily cap (section 10).

## What IT configures and what HR does

| Who | Does what | Where |
| --- | --- | --- |
| IT / system administrator | Runs the local model servers (Ollama, LM Studio, vLLM or another OpenAI-compatible server) on the assistant host, writes the model profiles file, sets any model keys in the service environment | Server only |
| HR administrator (`MODEL_CONFIG_MANAGE`) | Tests a configured model, runs its qualification, activates it for everyone, rolls back, reads the audit history | CLM → **AI Models** |

HR cannot type a URL, model name, key or parameter into the browser: the page only names a
profile IT configured. RM, Client Onboarder and Director users do not see the page and the
service refuses them (`403`, audited).

## 1. Keep the baseline

The model set by `AI_ASSISTANT_LLM_BASE_URL`, `AI_ASSISTANT_LLM_MODEL` and the other
`AI_ASSISTANT_LLM_*` settings stays the **environment baseline**. It is always listed, needs
no qualification, and is what the service uses whenever anything about a chosen model is
wrong. `AI_ASSISTANT_LLM_ENABLED=false` switches every model off (answers come from case data
only) and management cannot activate anything.

## 2. Write the profiles file

Copy `apps/assistant/model_profiles.example.json` to a server path outside Git, for example
`apps/assistant/data/models/profiles.json` (`data/` is git-ignored), and set:

```
AI_ASSISTANT_MODEL_PROFILES_FILE=data/models/profiles.json
```

Relative paths are under `apps/assistant`. Without this setting model management is off and
the service behaves exactly as before (no state file is created).

Each profile (unknown fields are refused, so a key cannot be written into the file):

| Field | Rule |
| --- | --- |
| `profile_id` | `a-z`, `0-9`, `_`, `-`; 3–48 characters; unique; not `env_default` or a code-defined id |
| `display_name` | What HR sees (1–80 printable characters) |
| `deployment` | `ollama`, `lm_studio`, `vllm` or `openai_compatible` |
| `base_url` | The server's OpenAI-compatible `/v1` URL. **Must be a literal loopback address** (`http://127.0.0.1:<port>/v1` or `http://[::1]:<port>/v1`); `localhost`, other hosts and remote services are listed as *Unavailable* |
| `model_id` | The id the server expects (as `GET /v1/models` lists it) |
| `model_version` | Optional label (quantisation, build) |
| `context_window_tokens` | The window the server really runs with (2,048–1,048,576). Qualification checks it against the server's own token counts and fails if the server truncates (see 4) |
| `max_answer_tokens` | 16–4,000 (default 600) |
| `temperature` | 0–1 (default 0.2) |
| `timeout_seconds` | Up to 600 (default 90) |
| `streaming` | Must be `true` (the chat panel streams) |
| `credential_env` | Optional. One of `AI_ASSISTANT_MODEL_KEY_OLLAMA`, `AI_ASSISTANT_MODEL_KEY_LM_STUDIO`, `AI_ASSISTANT_MODEL_KEY_VLLM`, `AI_ASSISTANT_MODEL_KEY_LOCAL` — nothing else |
| `enabled` | `false` hides a profile from use without deleting it |

A file that is missing, larger than 64 KiB or invalid lists no IT profile at all; the page
names only the fields to fix, never their values. At most 20 profiles.

## 3. Keys

Local servers usually need none. If one does, set the allowlisted variable in the **service
process environment** (not in the profiles file and not in Git), for example in PowerShell
before starting the service:

```
$env:AI_ASSISTANT_MODEL_KEY_LM_STUDIO = "<your LM Studio API key>"
```

The key is read only when the model is built and is never returned to the browser, logged or
written to the audit history. A missing key refuses the model (`CREDENTIAL_MISSING`).
`OPENROUTER_API_KEY` can never be named in the profiles file. The secret scanner flags any
literal assignment to these names. (The OpenRouter key for the D-094/D-095 remote profile is
configured as described in section 10.)

## 4. Context windows (Ollama in particular)

Ollama and some other servers silently cut a prompt that is longer than the context they were
started with (Ollama's default is small). The qualification therefore asks the server how many
prompt tokens it read for synthetic probes of growing size and **fails G-7
(`TRUNCATION_DETECTED`)** when the counts stop growing. Start the server with the window you
declare (for Ollama, `OLLAMA_CONTEXT_LENGTH` or the model's `num_ctx`; for LM Studio, the
loaded context length). A server that does not report usage cannot be verified
(`USAGE_NOT_REPORTED`). The probe goes up to 32,768 tokens; the activated model then refuses
any longer prompt (the RM gets the case-data answer instead).

## 5. Network rules

- Only literal loopback URLs; no proxy may be configured (`HTTP(S)_PROXY`, `ALL_PROXY` or a
  system proxy), otherwise testing and qualification are refused (`PROXY_CONFIGURED`).
- Remote models are not usable from the CLM. The code-defined OpenRouter profile is shown as
  *Pending authorisation* (D-091 dormant; D-092 proposed, synthetic evaluation only). Any
  remote activation needs separate privacy, security, provider, budget and governance
  approval. The one exception is the owner's D-094 local synthetic test mode (section 9).

## 6. What HR sees and does

1. **Test connection** — `GET /v1/models` (the model must be listed if the server lists any),
   one plain and one streamed completion of a fixed synthetic message. No case data.
2. **Run qualification** — about 84 synthetic questions through the real assistant with the
   candidate model (mock CLM data only), then the context check. One run at a time; HR can
   cancel. The run is limited by `AI_ASSISTANT_MODEL_QUALIFICATION_MAX_SECONDS` (default
   3,600). It runs in a separate process (`apps/assistant/scripts/qualify_model.py`) started
   by the service from `apps/assistant`; the repository's `tests/fixtures/eval` and
   `assistant_eval` must be present.
3. **Gates** (provisional, D-093): G-1 connection; G-2 every question answered; G-3 zero unsafe
   displayed lines; G-4 model unavailable or stopped mid-answer ≤ 5 %; G-6 kept/written model
   lines ≥ 0.70; G-7 context verified, prompts inside it and cut-short ≤ 10 %. G-5 (no allowed
   line selected) is shown but does not block. **Answer quality is NOT SCORED** until the owner
   labels and locks the gold set; a pass is technical only.
4. **Activate** — needs a passing qualification for the profile's current settings and the
   current assistant code, a fresh connection test, and HR's acknowledgement that answer
   quality is unscored. Answers already being written finish with the old model.
5. **Roll back** — returns to the previously active model if it is still valid, otherwise HR
   activates the environment baseline.

**Where these are on the page (D-100 Phase 1, presentation only).** AI Models is the *AI Model
Console*: a section menu (one folding button on narrow screens) over Models & Overview,
Providers, Spending & Limits, Qualifications & Recovery and Audit History. The section is part
of the address (`/admin/ai-models?section=spending`); opening a section sends no change.
Models & Overview shows the active model with its availability, technical qualification,
answer quality and activation side by side, summary counts, and every configuration as a tile
(configurations of one model family together, Balanced before Fast). Selecting a tile shows its
readiness and the existing Test connection, Run qualification and Activate actions; activation,
rollback and paid runs are confirmed in a dialog (a bottom sheet on a phone) that Escape
cancels. The full technical record of every configuration is folded below the tiles. Providers,
Spending & Limits, Qualifications & Recovery and Audit History keep the existing D-095 to D-098
controls unchanged for now. Nothing about qualification, gating, limits, keys, permissions or
the API changed.

**Claude in the console (D-099 with D-100, PR #131).** Claude Sonnet 5.5 Balanced
and Fast appear as one model family (provider *Anthropic API*); the inspector names the
provider, reasoning and thinking setting and Claude's own fixed safeguards. Run qualification
on a Claude configuration opens the same paid-run confirmation (calls, worst-case reservation,
what the strictest Claude limit leaves) worded for the Anthropic API and Claude's separate
ledger, and activation warns that it is an external, paid API with no automatic switch.
Spending & Limits says its controls apply to GPT-OSS only. Refusal codes are named in
provider terms (for Claude, *Test connection* is a free model read of the attested workspace),
and the service's Anthropic-specific *Run Test connection first* refusal (D-099-FU2) is shown
as written. HR key entry and HR-editable Claude limits are not part of Phase 1.

**The other four sections (D-100 Phases 2 to 4, presentation only).** *Providers* has one card
per provider (OpenRouter, Anthropic API, local models) listing its configurations with their
availability and last connection test, and who manages what: HR on this page, an operator on
the server, the key or workspace owner at the provider. The OpenRouter key form stays where
the server allows HR entry; Claude's inference key is set on the server only, and the page
says that the server does not send its status. *Spending & Limits* keeps the HR-editable
GPT-OSS limits and shows Claude's fixed limits read-only, with only the server's
paid-qualification figures (Claude's usage, headroom and reconciliation time are not sent).
*Qualifications & Recovery* shows technical qualification, answer quality and availability
apart for every external configuration, including those not yet qualified, with the server's
raw codes, the latest run's gates and provider-specific troubleshooting; a first or repeated
paid run still opens the confirmation. *Audit History* searches and filters only the events
the page loaded (the server's most recent 100) and says so; nothing is searched on the server.

## 7. Restarts, changes and failures

- The active model survives restarts (`AI_ASSISTANT_MODEL_ADMIN_DB_PATH`, default
  `data/models/model_admin.sqlite3`).
- If, at start, the active profile was removed, edited, disabled, made unselectable, its key
  or loopback/proxy rule fails, or the assistant's answer code changed since it was qualified,
  the service starts on the baseline and records `STARTUP_REVERTED` with the reason. Editing
  a profile therefore means qualifying it again.
- A model that stops answering is never switched automatically: RMs get the case-data answer
  and HR decides (roll back or activate another model).
- Run one service process per state database, or several sharing it: every request checks the
  stored choice, so all processes use the same model.

## 8. Audit history

Each test, qualification start/finish/cancel, activation, rollback, refusal (with the user and
role) and start-up revert is recorded with time, user, role, action, profile, settings
fingerprint prefix, outcome and a closed code. No URL, key, prompt, answer or case data.
Applied activations, rollbacks, undone activations and start-up reverts are always kept;
refused access by users without the permission keeps its newest 1,000 rows and other activity
its newest 5,000, so a flood of refused requests cannot push model changes out of the history.

## 9. D-094 local synthetic test mode (development machines only)

Off unless the service environment names `AI_ASSISTANT_LOCAL_API_TEST_DECISION=D-094`. Then,
and only when every condition holds, the OpenRouter profile is listed as **GPT-OSS 120B —
Balanced** (with reasoning effort medium; the page names the configured effort) and HR can
test, qualify, activate and roll it back like a local model (naming: section 11):

| Condition | Setting or check |
| --- | --- |
| Decisions | `AI_ASSISTANT_REMOTE_INFERENCE_DECISION=D-091`, `AI_ASSISTANT_REMOTE_LIVE_DECISION=D-092` |
| Endpoint | `AI_ASSISTANT_OPENROUTER_ENDPOINT=deepinfra/bf16` (the approved one), `AI_ASSISTANT_LLM_REASONING_EFFORT`, `AI_ASSISTANT_LLM_REASONING_ALLOWANCE_TOKENS` (at least 256) |
| Development machine | the CLM backend URL is a literal loopback address and every allowed browser origin is a local `http` origin |
| Owner attestation | `AI_ASSISTANT_LOCAL_API_TEST_OWNER_ATTESTS=auto_topup_off,prompt_logging_off` |
| Key and budget | `OPENROUTER_API_KEY` (process environment, `apps/assistant/.env` or HR entry: section 10); an initialised budget ledger (`scripts/budget_ledger.py`) |

Otherwise the page says which condition is missing. What each action does:

- **Test connection**: the Phase B preflight. It checks the public listing and ZDR list, the
  key limit, the ledger and earlier calls, and makes **no inference call**.
- **Run qualification**: a **paid** run of only the Phase B questions listed in
  `AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS`. Their number must equal
  `AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_COUNT`, or the run is refused. The gates are those
  above plus G-8, which requires every call to be verified from its generation metadata
  (serving provider, model and cost). G-7 uses the adapter's enforced prompt byte limit.
- **Activate** / **Roll back**: the same as for local models.

The active GPT-OSS model answers a chat question only when the whole prompt is inside the
generated synthetic boundary (`apps/assistant/ai_assistant/synthetic_boundary.json`):

- the case is GARDEN BUSINESS (UEN 11111999A) with registry details from ACRA MOCK;
- the document list was read, and every document on the case or named in its summary has an
  approved fixture file name;
- every client value is a fixture value;
- the viewer is a seeded POC user;
- only unchanged repository guidance and the synthetic seed are used;
- the text passes the word screen:
  - Every message may contain only printable ASCII, line breaks, tabs and a few named
    typographic marks.
  - The question and user history are taken as written. Words must come from the synthetic
    questions, guidance, fixture values, screen terms or a reviewed list of everyday words.
    Numbers get no free pass: at most three number groups across the user turns, never two
    side by side.
  - Assistant history may also use the synthetic prompts' wording (not the app's code
    strings), with no run of more than three number groups.

Otherwise nothing is sent and the RM gets the case-data answer, with a notice naming the
reason code. The screen guards against accidental entry, not deliberate encoding. It cannot
recognise a real name made of ordinary English words or numbers spelled out as words, and
its number cap is per request. So do not type real customer details.

Each call:

- reuses the preflight, refreshed every `AI_ASSISTANT_LOCAL_API_TEST_PREFLIGHT_SECONDS`;
- verifies earlier calls first, and is verified itself after it ends. A mismatch or a failed
  call opens the ledger breaker, which stops every later call.

The activated model makes at most `AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS` calls (open ones
included) until it is activated again or the service restarts; the ledger cap bounds the
spend. Model answers say "Answered by GPT-OSS 120B through OpenRouter (D-094 local synthetic
test mode)."

## 10. D-095 development synthetic mode, OpenRouter key and daily cap

D-095 is an owner-directed, local-development-only extension of section 9. Without
`AI_ASSISTANT_SYNTHETIC_DEV_DECISION=D-095` the D-094 mode above is unchanged.

### 10.1 Which cases GPT-OSS may answer

With the flag set (and every section 9 condition holding), the chat uses the remote model on
any **verified synthetic development case**, decided from the backend's own reply:

- the company's UEN and legal name are an approved synthetic company in the generated manifest
  `apps/assistant/ai_assistant/synthetic_eligibility.json` (the backend Mock ACRA fixtures and
  the project's synthetic company packs), its registry details came from ACRA in MOCK mode,
  and the requested UEN and registry acquisition are for that company;
- every document on the case is a synthetic fixture the repository tracks, by content: the
  SHA-256 the backend computed from the uploaded bytes must be the digest of a file under
  `apps/backend/tests/fixtures/uat/` (with its media type and size). Any other upload, one
  altered byte, or a document uploaded before the backend kept digests makes the whole case
  ineligible (upload the fixture again);
- typed values (case-creation input, manual decisions) equal a value from the Mock registry
  record or a verified document; a GoldTier id is a Mock GoldTier id (`GT-MOCK-...`);
- the viewer is a seeded POC user, and only unchanged repository guidance and the synthetic
  seed are used;
- the question and history may use any words, but no e-mail address, NRIC/FIN- or UEN-shaped
  id, date, or run of five or more digits that the case does not already hold.

Anything else gets the case-data answer with "GPT-OSS 120B through OpenRouter is used only on
verified synthetic development cases, so this answer comes straight from the case data.
Reason: `<code>`." and nothing is sent. Regenerate the manifest after adding a synthetic
company or fixture document (`scripts/build_synthetic_eligibility.py`; a test checks it is
current). Director questions can now name officers that the case's own Mock ACRA officer
lookup returned. Do not type real customer details: the screen cannot recognise a name.

### 10.2 The OpenRouter key

The service uses the first of:

1. `OPENROUTER_API_KEY` in the process environment;
2. `OPENROUTER_API_KEY=<key>` in `apps/assistant/.env` (git-ignored; only that line is read);
3. a key an HR administrator enters on **AI Models → OpenRouter API Key**.

A key from 1 or 2 is used automatically and cannot be changed or cleared from the page. When
none is set, the page shows **OpenRouter API Key — Not Configured** with a masked input,
**Save Key**, **Clear Key**, **Test Connection** and the status. An HR-entered key is kept in
the service's memory only (never on disk, in the browser, in logs or in the audit history) and
must be entered again after the assistant restarts; until then the activated GPT-OSS model is
replaced by the baseline at start (`CREDENTIAL_MISSING`) and HR activates it again. Key
changes need the AI Models page's origin and are limited to 5 attempts per administrator in 10
minutes. Changing the key re-runs the full preflight (the new key's own limit and usage
against the ledger) before the next call; if its usage does not reconcile with the ledger,
reconcile with `scripts/budget_ledger.py` first.

### 10.3 Spending limits

| Limit | Where | Notes |
| --- | --- | --- |
| Daily allowance | the ledger, checked on every call | Reserved plus settled spend per Asia/Singapore calendar day, for qualification and chat together. US$1.00 by default; D-098: HR may set it higher or lower on AI Models (no US$1 ceiling; a raise needs the amount confirmed and a finite OpenRouter key limit verified at that moment); until then `AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD` (default 1000000) applies. Resets at Singapore midnight without erasing anything; lowering it never resets today's spend. |
| Calls per activation | the active model, counted from the ledger | HR sets 1 to 200 on AI Models (D-096); until then `AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS` (default 20). Counted from activation or service start; a change applies at once and never resets the count. The paid qualification keeps the environment value. |
| Lifetime cap | the ledger | HR may set it on AI Models at or above the ledger's opening usage (D-098: no US$1 allocation ceiling); a raise needs the amount confirmed, a finite OpenRouter key limit and passing reconciliation checks against OpenRouter's reported usage. `scripts/budget_ledger.py set-cap` still works for the operator. |
| Key limit | OpenRouter | Never changed by the CLM. D-098: it must be set, never reset and be finite (`key.limit_finite`); without one, every call is refused and no app limit can be raised. There is no longer a US$1.00 bound on it for the CLM's own use (the Phase B harness keeps its D-092 allocation). AI Models can re-read it ("Refresh OpenRouter Limits"). |

The strictest applies. AI Models shows today's settled spend, in-flight reservations, today's
remaining allowance, lifetime headroom, the key limit as last checked, the available allowance
(the strictest of the three), calls used and remaining, the next reset and why calls are
refused. HR changes are stored in the model state database (shared by every service process),
audited and applied without a restart, a new activation or a new qualification (the
qualification basis does not include them). `scripts/budget_ledger.py status` shows the
environment daily figure, not an HR value. Nothing raises a cap or a key limit automatically,
and auto top-up must stay off.

## 11. GPT-OSS 120B naming, the optional Fast configuration and answer progress (D-097)

**Naming.** AI Models shows the remote model as *GPT-OSS 120B — Balanced* (reasoning effort
medium) and, beside it, Model: GPT-OSS 120B · Provider: OpenRouter / DeepInfra · Framework:
Case-grounded Assistant · Reasoning: Medium · External inference: Verified synthetic cases
only (D-095), or *The approved synthetic test case only (D-094)* in D-094 mode. The profile id
(`openrouter_gpt_oss_120b`), its fingerprint and its qualification are unchanged; D-094 and
D-095 remain the authorisation identifiers. Balanced and Fast are reasoning settings of one
model, not separate model releases. There is no "GPT-OSS 120B Instant" model.

**Optional Fast configuration (off by default).** With
`AI_ASSISTANT_REMOTE_LOW_REASONING_PROFILE_ENABLED=true` a second entry, *GPT-OSS 120B — Fast*
(profile id `openrouter_gpt_oss_120b_low`, reasoning effort low), is listed when the configured
effort is not already low. It uses the same model, endpoint, provider pinning, key, ledger,
daily and lifetime limits, call limit, synthetic eligibility and exact-line guard. It has its
own fingerprint, so:

- it is **not qualified** until HR runs its own qualification (paid calls, at reasoning effort
  low; Balanced's qualification never counts), and it cannot be activated before that;
- nothing switches to it automatically; HR activates it, and rolls back like any model;
- if the setting is removed while Fast is active, the service reverts to the baseline at the
  next start (audited `STARTUP_REVERTED`, `PROFILE_MISSING`).

Its speed and answer quality on this task are **not established**: no paid comparison has been
run (see the D-097 record for the evidence and the proposed A/B run).

**Answer progress (chat).** The panel shows the stages it actually observes: *Preparing case
information* (until the service starts its reply, which it does after reading the case and
running its checks), *Checking model readiness and waiting for the answer* (until the first
line that passed the exact-line check), *Showing lines that passed the check*, and the elapsed
time. No percentage, estimate or model reasoning is shown. After an answer, *What this answer
used* says whether the model or the case data produced it, the model name, the number of
cited sources and the time measured in the browser.

## 12. Qualification recovery, flexible limits and "AI unavailable" (D-098)

**Why a sign-in ended.** The backend keeps sessions in its own memory, one per account, for
8 hours from sign-in (unchanged). After a 401 the sign-in page now says why: the 8-hour limit,
the same account signed in elsewhere (another browser, the in-app pane, an agent), access
changed, signed out, or a session the backend no longer knows (it was restarted). A
qualification is never stopped, repeated or restarted by a sign-out; sign in again to follow it.

**Interrupted runs.** The service stamps a running qualification every second. A run with no
stamp for 30 seconds (the assistant service stopped or restarted) is closed as `INTERRUPTED`,
or `INTERRUPTED_BILLING_UNCERTAIN` when a paid call may have been open; it is never restarted.
An uncertain call stays in the ledger (its lease expires, it is charged at its reservation and
the breaker opens) until an operator reconciles with `scripts/budget_ledger.py`.

**Model health and recovery (AI Models).** Each configuration shows what its latest run means:
technical, budget or limit, server configuration, answer quality or billing not reconciled,
with the failed gates, a plain-English cause, whether a retry is worthwhile, whether an earlier
pass still counts, the paid calls a retry may make against the strictest limit, and the
recommended action or an escalation summary. HR cannot lower a gate, bypass a guardrail,
override verification, reset spend or activate an unqualified configuration.

| Outcome | Earlier pass | HR can | Otherwise |
| --- | --- | --- | --- |
| Technical (interrupted, provider unavailable, timeout, rate limit, a provider failure mid-answer) | kept | retry (paid runs confirmed) | operator when OpenRouter refused the key, payment or routing (the breaker stops calls) |
| Budget or limit (calls refused before sending) | kept | raise or wait for the limits, then retry | — |
| Server configuration (settings, attestations, key limit, question list) | kept (unverified context capacity, or a prompt above the verified or enforced bound: superseded) | — | IT |
| Billing not reconciled (breaker, unverified calls) | kept | — | operator |
| Answer quality (unsafe line, line validity, answers cut short by the token limits) | **superseded** | — | developer or IT; the same configuration cannot be run again until it changes |
| Qualification out of date (a pass for an earlier configuration or answer code) | not activatable | run a new qualification (paid runs confirmed, every limit applies) | — |

A quality failure takes precedence in the advice: whatever else the run shows (a provider
outage, refused calls), its recommended action is the escalation, because the same
configuration cannot be run again; an unreconciled ledger is still sent to the operator first.
Answers cut short count by whole answers, after setting aside those a provider failure cut
short. Owner decision (2026-10-29): a local model's context-capacity probe that fails for any
reason, including the local server being unreachable or slow during the probe, counts as
unverified capacity and supersedes that profile's pass (fail safe); IT changes the profile or
fixes the server, and the changed configuration is qualified again. GPT-OSS capacity is the
enforced prompt-byte limit and is not probed.

A paid run starts only after HR confirms its number of calls in a dialog showing the estimate
and the available amount, and only if every call fits the strictest limit; nothing is retried
automatically.

**Decision 6a and "AI unavailable".** Activation, rollback, the active model, the check made
after every run and start-up use one rule: the newest passing run for the current fingerprint
and answer code, unless a genuine quality failure came after it. When a GPT-OSS configuration
stops being usable (its pass superseded or out of date, its setting removed), the service
stores **AI unavailable** instead of switching to the local baseline or another model
(audited); this supersedes the D-097 note that a removed Fast setting reverts to the baseline.
Onboarding users then get answers labelled *Case-data guidance, not AI-generated*. HR
activates a qualified configuration, or the baseline, by hand. A local (D-093) profile still
reverts to the baseline.

**Flexible limits.** See the table in section 10.3: US$1.00 is the daily default, not a ceiling;
the lifetime cap has no US$1 allocation ceiling; the key's own finite limit is required and is
a backstop; at every call the strictest of the three applies. Raising a limit is confirmed and
checked against OpenRouter first; lowering is not. Existing model state databases keep their
spending controls (the table is rebuilt once without the US$1 check).

**Lifetime-cap changes are compare-and-set.** HR's change carries the cap the page showed and
is checked again inside the ledger's write: if the operator (`scripts/budget_ledger.py
set-cap`) or another process changed the cap in between, HR's change is refused and the
operator's value stands.

**Start-up never stands in another model.** If the state database cannot be read, or a
GPT-OSS revert cannot be stored, there is no model (case-data guidance only) until it can;
the revert and its audit entry are written as soon as the database accepts writes, and HR
can still activate a model meanwhile.

**The key's own limit.** AI Models shows the key's limit, usage and whether it resets; account
credits are not read. An exhausted key limit can only be raised by the key's owner at
OpenRouter; HR's spending controls cannot change it. IT may set the environment daily default
above US$1.00 (`AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD`) as a privileged deployment setting;
the lifetime cap and the key's own limit still apply.

**Requalification.** D-098 changes qualification-basis files (`budget.py`, `remote_checks.py`,
`remote_test.py`, `synthetic_boundary.json`), so every earlier GPT-OSS qualification is out of
date on this code: at start-up an active GPT-OSS configuration becomes *AI unavailable* until
HR runs a new (paid) qualification and activates it. Historical runs are kept.

## 13. Claude Sonnet 5.5 Balanced and Fast (D-099 Option B, proposed)

AI Models lists two configurations of one model, `claude-sonnet-5-5` on the Anthropic Messages
API: *Claude Sonnet 5.5 — Balanced* (effort medium, adaptive thinking; recommended) and
*Claude Sonnet 5.5 — Fast* (effort low, thinking between tool calls only). Each has its own
fingerprint and qualification history. They are selectable only on a development machine
where every Option B safeguard below is configured; otherwise they are listed and refused
before any network call (`ANTHROPIC_NOT_AUTHORISED` without the decision; `DECISION_INTERLOCK`,
`NOT_DEVELOPMENT_ENVIRONMENT`, `ANTHROPIC_ATTESTATION_MISSING`, `WORKSPACE_NOT_ATTESTED`,
`WORKSPACE_LIMIT_NOT_ATTESTED` or `ANTHROPIC_SETTINGS_INVALID` with it).

**Not equivalent to GPT-OSS through OpenRouter.** A direct Anthropic key cannot read its spend
limit, has no per-call cost record and cannot read usage without an organisation Admin key
(never used here). The owner-approved substitutes are attested limits, in-band checks of every
reply and manual reconciliation; see D-099 C6 to C9 for the residual risks. Synthetic
development cases only, the same cases GPT-OSS may answer. Never real data.

| Setting (environment; `.env` for the key only) | Rule |
| --- | --- |
| `AI_ASSISTANT_ANTHROPIC_DECISION=D-099` | plus the D-094 interlock GPT-OSS needs (`AI_ASSISTANT_LOCAL_API_TEST_DECISION`, D-091, D-092) |
| `AI_ASSISTANT_ANTHROPIC_OWNER_ATTESTS` | exactly `dedicated_workspace,workspace_limit_set,inference_key_only,key_revoked_at_fyp_end` |
| `AI_ASSISTANT_ANTHROPIC_WORKSPACE_ID` | the dedicated, non-default workspace's id (`wrkspc_…`); every reply must name it |
| `AI_ASSISTANT_ANTHROPIC_WORKSPACE_LIMIT_MICRO_USD` | the monthly limit set on that workspace in the Console, 1 to 5,000,000 (US$5.00) |
| `AI_ASSISTANT_ANTHROPIC_DAILY_CAP_MICRO_USD` | default and ceiling 1,000,000 (US$1.00 per Singapore day) |
| `AI_ASSISTANT_ANTHROPIC_MAX_CALLS` | default and ceiling 20 per activation or restart |
| `AI_ASSISTANT_ANTHROPIC_LEDGER_PATH` | default `data/budget/anthropic_ledger.sqlite3` (git-ignored); must be a different file from the GPT-OSS ledger (`LEDGER_PATH_SHARED` otherwise) |
| `AI_ASSISTANT_ANTHROPIC_API_KEY` | a workspace inference key (`sk-ant-api…` or `sk-ant-usr-…`); an Admin key, OAuth or session token is refused |

Operator steps (offline; the script never contacts Anthropic):

1. Create the ledger with the workspace's cumulative Console cost as its opening usage and a cap
   no higher than US$5.00 or the workspace limit:
   `scripts/budget_ledger.py --anthropic init --cap 5.00 --opening-provider-usage 0.00 --key-alias key-01`.
2. Reconcile against the Console's workspace cost (cumulative, in USD) before use: within 24
   hours before a paid qualification, an activation or a cap raise; at least every 7 days for
   chat: `scripts/budget_ledger.py --anthropic reconcile --provider-usage 0.42`.
3. A quarantined call (wrong workspace, model or route, unfinished stream, missing usage) or a
   provider refusal opens the breaker; reconcile, then `reset-breaker --code <code>`.

Each call then needs: the synthetic boundary (or a D-095 ticket, re-checked in the adapter), a
valid key, the ledger's own profile with a closed breaker and no open call, every earlier call
verified, room for one worst-case reservation (about US$0.096) in the ledger and today's
allowance, the reconciliation window, and a free `GET /v1/models/claude-sonnet-5-5` naming the
attested workspace (reused for `AI_ASSISTANT_LOCAL_API_TEST_PREFLIGHT_SECONDS`). Claude answers
in the streamed chat only. Follow-up questions are sent too (D-099-FU1): the service's own
knowledge, topic and case page terms messages after the history become top-level system
blocks after its leading ones, unchanged and in order, and any other prompt shape is refused
before anything is reserved. The paid
qualification's G-8 gate verifies Claude calls in-band. The GPT-OSS HR spending controls and
HR key entry never apply to Claude (HR controls for Claude are deferred). Nothing switches to or
from Claude automatically.

**Requalification.** D-099 regenerates `synthetic_boundary.json` (owner-approved seven words,
plus three Option B identifier fragments `ant`, `usr`, `wrkspc`, all system-message vocabulary
only) and adds the Claude modules to the qualification basis, so the basis moves from
`b4049047884e…` (D-098) to `adec795f61bd…`, and D-099-FU1 (the Claude adapter's multi-turn
conversion) to `33f602653de7…`. Every earlier GPT-OSS qualification is out of date
once this merges: an active GPT-OSS configuration becomes *AI unavailable* at start-up until HR
runs a new (paid, separately approved) qualification and activates it. Historical runs are
kept.
