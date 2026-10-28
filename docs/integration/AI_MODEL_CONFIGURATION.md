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
and only when every condition holds, the OpenRouter profile is listed as **GPT-OSS 120B via
OpenRouter (synthetic test only, D-094)** and HR can test, qualify, activate and roll it back
like a local model:

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
- every document on the case is a synthetic fixture the repository tracks: same file name,
  media type and exact byte size as a file under `apps/backend/tests/fixtures/uat/` (or a D-094
  Garden fixture document). Any other upload makes the whole case ineligible;
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
| Daily allowance | the ledger, checked on every call | At most US$1.00 reserved plus settled per Asia/Singapore calendar day, for qualification and chat together. `AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD` (default 1000000) may only lower it. Resets at Singapore midnight without erasing anything. |
| Lifetime cap | the ledger (`scripts/budget_ledger.py`) | Unchanged. The preflight still allows at most US$1.00 above the ledger's opening usage (D-092 P3). |
| Key limit | OpenRouter | Unchanged: a non-resetting limit with at most US$1.00 plus one reservation remaining. |

The strictest applies. AI Models shows today's settled spend, in-flight reservations, today's
remaining allowance, lifetime headroom, the key limit as last checked, the next reset and why
calls are refused. `scripts/budget_ledger.py status` shows the same daily figures. Nothing
raises a cap or a key limit automatically, and auto top-up must stay off.
