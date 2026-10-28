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
| Daily allowance | the ledger, checked on every call | Reserved plus settled spend per Asia/Singapore calendar day, for qualification and chat together. HR sets it on AI Models (US$0.00 up; D-098: US$1.00 is the default, not a ceiling; a raise is confirmed and provider-verified, section 12); until then `AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD` (default 1000000) applies. Resets at Singapore midnight without erasing anything; lowering it never resets today's spend. |
| Calls per activation | the active model, counted from the ledger | HR sets 1 to 200 on AI Models (D-096); until then `AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS` (default 20). Counted from activation or service start; a change applies at once and never resets the count. The paid qualification keeps the environment value. |
| Lifetime cap | the ledger | HR may set it on AI Models from the ledger's opening usage up (D-098 removed the US$1.00-above-opening bound); a raise needs the amount confirmed, a finite non-resetting key limit and passing reconciliation checks against OpenRouter's reported usage. `scripts/budget_ledger.py set-cap` still works for the operator. |
| Key limit | OpenRouter | Never changed by the CLM: a finite limit that never resets (D-098: its size is the owner's; the former "at most US$1.00 plus one reservation remaining" check is removed). AI Models shows its limit, remaining, usage and reset and can re-read it ("Refresh OpenRouter Limits"). Account credits are not readable with this key and are shown as not available. |

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
- if the setting is removed while Fast is active, the service reverts at the next start to no
  AI model (case-data answers only; D-098: never to another model; audited `STARTUP_REVERTED`,
  `PROFILE_MISSING`).

Its speed and answer quality on this task are **not established**: no paid comparison has been
run (see the D-097 record for the evidence and the proposed A/B run).

**Answer progress (chat).** The panel shows the stages it actually observes: *Preparing case
information* (until the service starts its reply, which it does after reading the case and
running its checks), *Checking model readiness and waiting for the answer* (until the first
line that passed the exact-line check), *Showing lines that passed the check*, and the elapsed
time. No percentage, estimate or model reasoning is shown. After an answer, *What this answer
used* says whether the model or the case data produced it, the model name, the number of
cited sources and the time measured in the browser.

## 12. Recovery, paid-qualification confirmation and flexible limits (D-098)

**Recovery panel.** *AI model status and recovery* on AI Models classifies what stops the
model, from closed server codes, as one of: **Healthy**, **Qualification required**,
**Recoverable by HR**, **Temporarily unavailable**, **Operator intervention required** or
**Security/policy blocked**. It shows the active model, whether an external model is in use,
the next action, the last failed qualification or connection test, any other qualified
configuration, and each GPT-OSS 120B configuration with its state, whether an earlier pass is
still valid, and why its last qualification failed, gate by gate (retryable or not, whether HR
can resolve it, what to do next). Actions: Refresh Limits and Test Connection (free, no model
call), Review Budget, and Retry Qualification. Nothing on it shows a key, prompt, reasoning,
unverified answer or case data.

| Gate | Meaning for HR | Retry |
| --- | --- | --- |
| G-1 connection | the free preflight failed; the failed checks are listed (provider down, limits, ledger) | per check |
| G-2 completion | not every question was answered in time | yes |
| G-3 unsafe display | a safety result: contact IT | no |
| G-4 availability | too many questions had no model answer (limits, outage) | yes |
| G-6 answer validity, G-7 capacity | a model-quality or capacity result: contact IT | no |
| G-8 provider verification | a call did not match OpenRouter's record: the owner reconciles | no |

HR cannot change thresholds, safety filters, gates or model settings; a non-retryable result
is never retried away: after a G-3, G-6, G-7 or G-8 failure the server refuses any new run of
that configuration and code (`ESCALATION_REQUIRED`, decided when the run would start) until IT
changes its settings or the code changes. Other non-retryable results (ledger, policy) need
the operator or IT first; the run can then be repeated. An earlier pass shown beside a later failed run keeps an existing activation, but
the configuration cannot be activated again until a new run passes.

**Paid qualification.** A remote qualification is started only after HR confirms its number of
paid calls (the server requires `confirm_paid_calls` to equal the configured manifest count;
the page shows the count, the reservation each call holds, the worst case and the allowance
available now). It is refused before it starts when the limits leave no room for one call or
the call limit is below the count. One run at a time (`QUALIFICATION_BUSY`); a failed,
cancelled or interrupted run is never repeated automatically, and a failed run never replaces
the active model.

**Sessions.** A qualification runs in its own server process. HR may leave the page, refresh
or sign in again and see the same run; a session that ends (expiry, the backend's
one-session-per-account rule when the same account signs in elsewhere, a backend restart)
does not cancel, restart or repeat it. A session refused while a run is in progress is logged
and audited as `SESSION_REFUSED` (codes only, at most once a minute).

**Flexible limits.** US$1.00 is the default daily limit, not a maximum. HR may lower either
limit at any time; raising the daily limit or the lifetime cap needs the amount confirmed and a
fresh free preflight in the change lock: the OpenRouter key must have its own finite limit that
never resets (`key.limit_set`, `key.limit_never_resets`), and the ledger must be reconciled
(breaker closed, no open call, usage accounted for). The page's view must be current (the controls' revision; for the lifetime cap, the cap it
showed), otherwise the change is refused (`CONTROLS_CONFLICT`). The environment default
(`AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD`) is IT's and has no such check; every call's
preflight still requires the key's own finite, non-resetting limit. Otherwise the raise is refused
(`PROVIDER_LIMIT_REQUIRED`, `RECONCILIATION_REQUIRED`, `PROVIDER_CHECK_FAILED`). The bound for
both is the ledger's own (US$1,000,000). Every call is still admitted against the lowest of
today's allowance, the lifetime headroom and the key's remaining limit. A D-096 state database
is migrated in place on first open (its controls row kept). Changing these files changes the
qualification basis: GPT-OSS 120B Balanced (and Fast) need a new paid qualification before use.

**GPT-OSS only.** When a GPT-OSS activation can no longer be used (qualification out of date,
profile changed, missing or unavailable), the service reverts to **no AI model**: every answer
is the case-data answer, the page says so and that nothing was substituted, and the state is
kept across restarts until HR activates a qualified model (or chooses the environment
baseline by hand). Local IT profiles still revert to the environment baseline. Nothing switches
between Fast and Balanced automatically (owner decision: not approved). An activation in use
keeps the passing run it was activated with; a later failed run does not end it, but the
configuration cannot be activated again until a new run passes ("Activation still valid" on
the page).

**Lifetime cap changes** carry the cap the page showed; the ledger compares it again in its own
write transaction, so an operator's `budget_ledger.py set-cap` made in between is never
overwritten (`CONTROLS_CONFLICT`). Requalification plan: `.ai-pipeline/reports/D098_REQUALIFICATION_PLAN_WINDOWS.md`.
