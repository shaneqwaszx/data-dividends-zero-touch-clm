# AI Assistant model configuration — guide for IT administrators

Decision: D-093 (accepted for the local-only POC scope; ADR-012 Amendment 4). Classification:
`LOCAL`. Nothing here enables a remote or cloud model.

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
`OPENROUTER_API_KEY` can never be named. The secret scanner flags any literal assignment to
these names.

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
  approval.

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
