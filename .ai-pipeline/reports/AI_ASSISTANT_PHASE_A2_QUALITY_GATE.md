# AI Assistant Phase A2 — Independent Quality Gate (WP3 + WP4)

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Role | Independent Stage 3 Quality Gate. The reviewer did not write or fix any of the reviewed content. Skills applied: `fyp-quality-gate`, `integration-security-review`, `persistence-schema-change`, `architecture-change-review` |
| Reviewed commit | `5245bbe80e5fe9a64c479b758abc6a400df88bd0` on local branch `feat/assistant-phase-a2-20261026-int` (no upstream) |
| Reviewed tree | `a1e139217aa27eec782613974afa39dfc205fee7` (matches the expected tree) |
| Base | `7d6a31aa196cff23c0b5b1fd4e5e31cf9bce0efc` = `origin/main` = sole parent = merge-base. PR #114 content is not present |
| Review snapshot | Detached worktree owned by the reviewer: `C:\Users\shane\Desktop\claude-worktrees\qg-a2-5245bbe` (HEAD and tree checked). Base comparison: detached `C:\Users\shane\Desktop\claude-worktrees\qg-a2-base-7d6a31a`. The implementing worktree, its branch, primary `main` and teammate branches were not used or changed |
| Remote activity / spend | **Zero** OpenRouter or other non-loopback requests. **US$0.00** spent. `OPENROUTER_API_KEY` was never read or printed (only environment variable *names* were listed: the variable is not set in this shell) |

## 1. Executive result

**PASS** for the frozen commit `5245bbe` (tree `a1e13921`).

All four dormant locks, the S1–S3 safeguards, the adapter, the budget ledger model
(`K = B + L + O`, INV-1 to INV-9) and default-behaviour parity were checked by reading the
code and running tests and probes that the reviewer wrote. No critical, high or medium
defect was found. Six low-severity findings and some informational notes are recorded
(section 9). None affects the default profile, and none can cause a remote request or
spending in this build. They are recommended fixes before any Phase B activation. They are
not required to merge the dormant A2 code.

One required matrix lane was only partly run: the POC lifecycle/regression through
`scripts/run_e2e.py`. This machine has no Tesseract and the Docker daemon is not running.
The assistant-surface spec (`e2e/assistant-streaming.e2e.ts:10`) **was** run directly with
Playwright (real Chromium, real HTTP) and passed 1/1. See section 7.

## 2. Identity checks (all passed before review)

| Check | Result |
|---|---|
| Full SHA | `5245bbe80e5fe9a64c479b758abc6a400df88bd0`; local branch tip equals it |
| Tree | `a1e139217aa27eec782613974afa39dfc205fee7` = expected |
| Parent / merge-base / `origin/main` | all `7d6a31aa196cff23c0b5b1fd4e5e31cf9bce0efc` |
| Upstream | none (`fatal: no upstream configured`), as reported |
| Changed files | 28 (`git diff --name-status 7d6a31a 5245bbe`): 15 added, 13 modified; +6,821 / −19. Matches the reported 28-file inventory |
| Implementing worktree | HEAD `5245bbe`, nothing tracked or untracked changed. Ignored only: `apps/assistant/.mypy_cache`, `.ruff_cache`, `apps/assistant/data/` (contains only `knowledge/`: `chroma`, `knowledge.sqlite3`), `apps/frontend/dist`, plus `apps/backend/.mypy_cache` and `.ruff_cache`. The backend caches were not in the expected list, but they are ignored tool caches. No `data/budget` exists |
| `.ai-pipeline/.../AI_ASSISTANT_PHASE_A2_GOVERNANCE_AND_IMPLEMENTATION_PLAN.md` in the commit | byte-identical to the untracked copy in the primary checkout |

Reviewed inventory: planner (new), A1 planner note, implementation handoff (new),
`apps/assistant/.env.example`, `README.md`, `ai_assistant/{budget,model_factory,model_profiles,openrouter}.py`
(new), `ai_assistant/{config,llm,main,telemetry}.py`, `scripts/budget_ledger.py` (new),
`tests/conftest.py`, `tests/remote_fixtures.py` and six new test files, `tests/test_telemetry.py`,
`docs/ARCHITECTURE.md`, `ADR-012`, `DECISION_LOG.md`, `scripts/check_secrets.py`,
`tests/test_check_secrets.py`. No backend or frontend file changed (`git diff --stat` for
`apps/backend` and `apps/frontend` is empty).

## 3. Scope verdict — PASS

| Area | Verdict | Evidence |
|---|---|---|
| Registry / factory | In scope | `model_profiles.py`, `model_factory.py`. One composition point: `main.py:370` is the only production caller of `build_chat_model`, and no production caller passes a transport |
| Dormant OpenRouter adapter | In scope | `openrouter.py`. The only URL is `OPENROUTER_BASE_URL + "/chat/completions"` (`openrouter.py:189`). A code search finds no `/generation`, `/key` or `/endpoints/zdr` path outside a test's forbidden list |
| Additive usage / finish handling | In scope | `llm.py`: new types and fields with defaults. The body of `OpenAICompatibleChatModel` is unchanged |
| Telemetry v2 | In scope | `telemetry.py`: `METRICS_VERSION = 2`, closed-code validation, no `generation_ref`; default `off` |
| Separate SQLite ledger and offline CLI | In scope | `budget.py`, `scripts/budget_ledger.py`. Separate from the knowledge store; no knowledge-schema change |
| Scanner hardening | In scope | Only `scripts/check_secrets.py` and `tests/test_check_secrets.py`; candidate selection unchanged |
| Docs / tests | In scope | — |
| Unchanged surfaces | Confirmed | No diff in `prompts.py`, retrieval, catalog, `guardrails.py`/`StreamingGuard`, fallbacks, notices, routes, feedback governance, answer-record schema, frontend or backend. The `main.py` diff is limited to composition, metrics fields and the `record_reason()` mapping (`main.py:255-256`) |
| Integration change to #113 code | Acceptable | `budget_refused` is recorded as the existing `model_unavailable` reason; no answer-record schema change |

## 4. Locks L1–L4 (each verified independently) — PASS

Evidence: the implementer's `test_model_factory.py` (49/50 passed in the full run; the one
failure is Errno 24, see 6.2, and it passes alone) plus reviewer probes
(`scratchpad/qg/probes/test_qg_probes.py`).

| Scenario | Result |
|---|---|
| Default start-up | Returns `OpenAICompatibleChatModel` whose `vars()` equal a reference built with today's arguments. An environment mapping that fails on *any* access is never touched (reviewer probe `NoKey`) |
| Dummy credential present, default profile | The local request still carries the local `ollama` placeholder; the sentinel key is absent from the adapter state and the outgoing request (golden test, reviewer probe) |
| Remote profile selected through **environment settings** + `create_app` | Start-up refused with `PROFILE_DORMANT`; the message holds no sentinel (reviewer probe) |
| Shipped registry + `MockTransport` + valid ledger + interlock | `ENDPOINT_NOT_APPROVED`: `APPROVED_PROFILES["openrouter_gpt_oss_120b"].endpoints == ()` (L2 cannot open) |
| L1: `None`, `httpx.HTTPTransport()`, `httpx.AsyncHTTPTransport()`, a `MockTransport` subclass | `PROFILE_DORMANT` / `TRANSPORT_NOT_ALLOWED` in the factory and again in the adapter constructor (`openrouter.py:72-81,174`) |
| L2: missing record, base slug, invalid slug, record without uniqueness evidence | `ENDPOINT_NOT_APPROVED` / `ENDPOINT_SLUG_INVALID` / `ENDPOINT_NOT_UNIQUE` |
| L3: empty, `d-091`, `" D-091"` | `DECISION_INTERLOCK` (exact match) |
| L4: missing ledger | `LEDGER_UNAVAILABLE`, and neither the file nor its parent directory is created. Garbage, truncated, newer `user_version`, tampered totals: refused, never repaired (reviewer probe). Ledger for another profile: refused |
| `model_construct` settings (validators skipped) | The lock and capability checks still apply (`DECISION_INTERLOCK`, `REASONING_EFFORT_INVALID` for `none`, `MAX_TOKENS_TOO_LARGE`, `PROFILE_UNKNOWN`). Some numeric bounds are not re-checked: see F-4 |
| Order of checks | L1 → base URL/model override → L3 → L2 → effort/allowance/max tokens → L4 → credential (`model_factory.py:82-143`). The credential is read last. A spy test (T3-20) and the reviewer's `NoKey` probe agree |
| Missing or malformed key once all locks are open | `CREDENTIAL_MISSING` for absent, empty, containing whitespace, or over 256 characters; fixed message |
| A remote model is always wrapped | `type(model) is BudgetedChatModel` (reviewer probe; `model_factory.py:156`) |

## 5. Safeguards S1–S3 — PASS

- **S1 exact endpoint.** `ApprovedEndpoint.slug` uses the full-slug pattern
  (`model_profiles.py:38`). `slug_unique_for_model` is required (`model_factory.py:113`). The
  slug goes into `provider.order` and `provider.only` with `allow_fallbacks: false`
  (`openrouter.py:221-233`). No endpoint is approved. Uniqueness cannot be shown offline and
  is correctly left as a Phase B prerequisite (handoff section 7.5, ADR Amendment 3
  "Revisit before Phase B").
- **S2 transport containment.** `type(t) is httpx.MockTransport` is checked in the factory and
  in the adapter (`trust_env=False`, `follow_redirects=False`). The only production
  composition (`main.py:370`) passes no transport, so it is refused at start-up. The
  suite-wide guard (`tests/conftest.py`) blocks non-loopback `connect`, `connect_ex`,
  `getaddrinfo` and asyncio `create_connection`, and asserts zero attempts at session end.
  The candidate full run had no teardown error. Its self-test failed in the full run with
  Errno 24 only (see 6.2) and passes alone. Precision note: see I-1.
- **S3 ledger identifier privacy.** `key_alias` must be one of `key-01` to `key-04`, checked
  in code and by a CHECK constraint. All tables are `STRICT`. Every TEXT column is a closed
  code (CHECK IN) or a pattern-checked opaque value (hex32, endpoint slug, generation
  reference). Amounts and timestamps are INTEGER, and anomalies are an integer bitmask. All
  eight write paths (`initialise`, `reserve`, `settle`, `_abandon_expired`, `set_cap`,
  `reconcile`, `reset_breaker`, `_open_breaker`/`_event`) write only closed or validated
  values. Reviewer probe: after a call whose prompt and answer held a UEN, a company name and
  "director", the raw ledger bytes contain none of them, nor the answer text or the sentinel
  key. An alias such as `"Shane laptop key"` is refused and no file is created.

## 6. Tests and checks (exact counts)

### 6.1 Commands run by the reviewer on the frozen snapshot

| Check | Result |
|---|---|
| Full assistant pytest, **base** `7d6a31a` (detached worktree, JUnit) | 1,574 collected: **1,562 passed, 12 failed, 0 skipped, 0 errors** (262 s) |
| Full assistant pytest, **candidate** `5245bbe` (detached worktree, JUnit) | 1,810 collected: **1,797 passed, 13 failed, 0 skipped, 0 errors** (351 s). +236 new tests, 0 removed |
| A2 focused tests (in the candidate JUnit) | golden 6/6; factory 49 passed + 1 Errno 24 (passes alone); adapter 92/92; ledger and invariants 60/60 (including 1,000 seeded sequences and a two-process test); guard 16/16; CLI 12/12; telemetry 50/50. All 236 A2 tests also pass in one separate run (exit 0), with no growth in open CRT file descriptors (5 → 5) |
| Reviewer adversarial probes (29) | 28 passed. The 29th was the reviewer's own wrong expectation: a read-only ledger passes L4 composition, but every admission is then refused `refused_ledger` (implementer's T4-12), so it still fails closed (I-3) |
| Ruff (`ai_assistant`, `assistant_eval`, `scripts`, `tests`) | All checks passed |
| `ruff format --check` | 92 files already formatted |
| mypy strict (`ai_assistant`, `assistant_eval`, `scripts/budget_ledger.py`, `scripts/evaluate_answers.py`) | Success: no issues in 43 source files |
| `tests/test_check_secrets.py` (repo root) | 17 passed |
| `check_secrets.py` (hardened, full tracked set) | PASS, exit 0 (SC-8: no unowned tracked file is flagged) |
| `check_architecture`, `check_project_state`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness` | all PASS |
| Backend `tests/test_ai_assistant_main_integration.py` (candidate assistant on the path) | 2 passed (`[mock]`, `[sandbox]`) |
| Full backend pytest (candidate tree; backend files identical to base) | 3,350 collected: **3,173 passed, 177 skipped, 0 failed, 0 errors**, exit 0 (1,111 s; JUnit). The 177 skips are the backend's own physical-Mongo and optional lanes. This matches the implementer's claim |
| Frontend assistant Vitest (6 files: `aiAssistant*.test.ts`, `aiAssistantContext.test.ts`, `AiAssistantPanel.test.tsx`, `KnowledgeReview.test.tsx`) | 6 files, **108/108 passed** (`--no-cache`; `node_modules` linked read-only from the primary checkout, whose `package.json`/lock are identical to base; link removed afterwards) |
| `assistant-streaming` E2E (`e2e/assistant-streaming.e2e.ts:10`), direct Playwright | **1/1 passed** (real Chromium, real HTTP; `CLM_E2E_BACKEND_ORIGIN` set to an unused loopback origin; output to scratch). Not through `run_e2e.py` (section 7) |
| `evaluate_answers.py check` | base and candidate both: "snapshots are current (84 turns, sha256 9341411d512d3beb)" |
| E0 self-tests (`self-test-perfect`, `-random`, `-prose`, `-injection`), base vs candidate | all exit 0. JSON reports are identical except `generated_at`, `manifest.git_head` and latency percentiles |
| `git diff --check 7d6a31a 5245bbe` | clean. `--numstat` equals `--numstat --ignore-cr-at-eol` (6,821/19): no EOL churn. The new `ARCHITECTURE.md` lines are CRLF, like the surrounding file. Every new Markdown file is committed, so `diff --check` covers it |
| Physical Mongo | N/A: no Mongo surface (the ledger is assistant-local SQLite; workflow "Physical Mongo is required only when a change can affect Mongo …") |
| Hosted CI | Not executed (nothing pushed) |

### 6.2 Failure classification (candidate vs base, JUnit compared test by test)

| Failure | Classification |
|---|---|
| 12 × `OSError: [Errno 24] Too many open files`: `test_required_p2.py::test_real_http_sse_framing[5 params]`, `test_streaming_resources.py::test_loopback_total_deadline[5 params]`, `::test_real_chunked_http_enforces_budgets[oversized, many-frames]` | **Reproduced baseline / environment blocker.** Identical on base and candidate. All 148 tests in those files (plus the guard self-test) pass when run alone on the candidate |
| `test_model_factory.py::test_the_suite_guard_blocks_remote_connections` (candidate only) | **Environment blocker, not a regression.** Same Errno 24 class. It runs a real socket late in the single-process run, and passes alone. The 236 A2 tests leak no CRT file descriptors (5 → 5) |
| `test_knowledge_answers.py::test_streaming_shows_the_knowledge_line_and_carries_sources` (reported 1-in-8 flake) | Not seen in this run (passed on both trees); the implementer's flake claim is neither confirmed nor refuted |

New regressions: **0**. Unresolved: **0**.

## 7. E2E / POC lifecycle disposition

- **Required lane:** `POC lifecycle/regression` is `R` for `AUTH_RBAC_SECURITY`, `PERSISTENCE`,
  `EXTERNAL_PROVIDER` and `ARCHITECTURE_REFACTOR` (`docs/DEVELOPMENT_WORKFLOW.md` matrix). The
  A2 planner (section 11) names `assistant-streaming` as the assistant surface's POC regression.
- **Executed:** the spec itself, directly with Playwright: 1/1 PASS. It renders the unchanged
  frontend panel against its own Node synthetic server (`assistant-streaming.e2e.ts:1-60`) and
  does not call the Python assistant service. A2 changes no frontend or backend file, so this
  evidence is unaffected by A2.
- **Not executed:** the configured harness run,
  `python scripts/run_e2e.py --selectors-file <file containing e2e/assistant-streaming.e2e.ts:10> --results-json <path>`.
  Reason: `tesseract` is not on PATH, and the Docker daemon is not running
  (`dockerDesktopLinuxEngine` pipe absent), so there is no disposable Mongo
  (`CLM_E2E_SYNTHETIC_MONGO_PORT`). The reviewer did not start services.
- **Merge impact:** none expected. The assistant's default HTTP behaviour is byte-identical
  (section 8), and the harness exercises only unchanged frontend/backend code plus that
  behaviour. **Owner action (optional, recommended before publication):** run the command
  above on a machine with Docker and Tesseract and attach the results JSON.

## 8. Default-behaviour parity — PASS

Reviewer-written differential probe (`scratchpad/qg/parity/parity_probe.py`), run separately
on each detached tree. It uses the service's own default composition (`create_app` builds the
model from settings), a **loopback** fake OpenAI-compatible server that records every
outgoing request (path, all headers except `Host`, body bytes), the recorded Garden CLM
fixtures, 7 model modes (ok, guard-invalid, length, empty, early EOF, HTTP 500, malformed
JSON) × 12 questions × 2 histories × `/chat` and `/chat/stream`, plus `/health` and `/brief`
(warm-up), with all `ai_assistant` log lines captured. The probe confirmed it imported the tree under test.

| Run | Responses | Outgoing model requests | SHA-256 of canonical transcript |
|---|---|---|---|
| Base `7d6a31a` | 338 | 281 | `69fb5bba1d78e0c549c9e1b41beaef31f85845437c1898115a3e96a01cdf17a8` |
| Candidate `5245bbe` | 338 | 281 | `69fb5bba1d78e0c549c9e1b41beaef31f85845437c1898115a3e96a01cdf17a8` |
| Control (base, temperature 0.21) | 338 | 281 | `9be24db4…f83e` (differs: the probe is sensitive) |

The transcript includes model answers, guard drops, cut-short notices, early-EOF partials and
every fallback. Both trees created no budget directory and no new data files. Telemetry stays
`off` by default. After the full suite and all probes, the reviewer worktree's
`apps/assistant/data` holds only the pre-existing `knowledge/` (same as base), and no
`data/budget`. The golden test (T3-01) pins URL, sorted headers, body bytes and SHA-256 for
`complete`, `stream` and `warm`.

## 9. Findings by severity

No critical, high or medium findings.

| ID | Severity | Location | Reproduction | Expected vs actual | Impact | Remediation / owner decision | On base? |
|---|---|---|---|---|---|---|---|
| F-1 | Low | `budget.py:879-882`, `:895`; `openrouter.py:249-251,282,349` | Reviewer probe `test_prompt_too_large_is_charged_after_reservation`: guard with `remote_max_prompt_bytes=1024`, 5 KB prompt | Plan section 6.5: "refuses larger prompts **before reservation**". Actual: the guard reserves first, the adapter then raises `prompt_too_large` without sending a request, and the call is charged its **full reservation** (`unsettled`, no breaker). T3-21's "before any request" holds | Spending is over-counted for a call that never ran (≈US$0.07 per refusal at the test record's 117,964-token ceiling). The error is in the safe direction and can be released with `reconcile --release`, but repeated refusals can use up the cap without real spend. Not listed among the handoff's deviations; the only test is adapter-level | Check `message_bytes` against `max_prompt_bytes` in `BudgetedChatModel` (or the factory-built wrapper) before `reserve`; add a guard-level test. Before Phase B | No (new code) |
| F-2 | Low | `scripts/budget_ledger.py:148`; `config.py:43`; `budget.py:772` | Reviewer CLI probe: settle a call, then `reconcile --provider-usage 0.01 --settle-lag-seconds -1` → "reconciled" (exit 0); with the default lag → `RECONCILE_REFUSED` | The plan's `T_lag` comes from `budget_settle_lag_seconds` (default 600, `ge=0`). Actual: that setting (and `.env.example`'s `AI_ASSISTANT_BUDGET_SETTLE_LAG_SECONDS`) is never read. The CLI takes its own unbounded float flag, so a negative or zero value skips the quiescence lag | An operator input does not fail closed; a configured lag is silently ignored. Operator-only path; the ledger is documented as not tamper-proof against the operator | Have the CLI default to the setting and reject values below 0 (or below the setting); add a CLI test. Before Phase B | No |
| F-3 | Low | `openrouter.py:285-302` | Code reading | Plan section 6.1: whole-request deadline and the 1 MiB response bound. Actual (non-stream `complete()`): `client.post` reads the whole body before the `> MAX_STREAM_BYTES` check, and httpx's `timeout` is per operation, not a whole-request deadline. The error-status path also reads the whole body. The stream path is correctly bounded | No effect in A2 (mock transport only). With a live provider, a slow or very large non-stream reply could exceed the deadline or memory bound. The local adapter's `complete()` behaves the same on base | Use `client.stream(...)` with a byte-bounded read under `anyio.fail_after` for the remote `complete()`. Phase B prerequisite | Same pattern in the local adapter on base |
| F-4 | Low | `model_factory.py:74-161` | Reviewer probe: `model_construct(..., budget_max_in_flight=50, remote_max_prompt_bytes=10**9)` composes, and `_max_in_flight == 50` | Docstring: "Validation runs here, not only in pydantic, because some callers build settings without validators". Actual: locks and capabilities are re-checked, but `budget_max_in_flight` (1..4), `remote_max_prompt_bytes`, `llm_timeout_seconds`, `llm_temperature` and `llm_max_answer_tokens` are not. A non-finite temperature would raise a non-`LlmUnavailableError` from `httpx` JSON encoding (charged at reservation by the guard's `BaseException` path, then a 500) | Only for callers that bypass validation. `assistant_eval` refuses remote models, so it is not reachable in A2 | Re-check those bounds in `_remote()`. Before Phase B | No |
| F-5 | Low | `scripts/check_secrets.py:83-95` | Reviewer scanner probe (synthetic values built at run time) | SC-1 forms are all detected (`.env`, YAML, PowerShell `$env:`, `export`, `set`, quoted, JSON key), as is SC-2. Gaps: (a) `os.environ["OPENROUTER_API_KEY"] = "<literal>"` in Python is **not** detected (not one of the SC-1 forms); (b) `OPENROUTER_API_KEY=<your key>` (a placeholder containing a space) is a false positive | (a) is a small detection gap for one source-code form; (b) fails safe | Optionally add the subscript-assignment form and allow whitespace inside angle-bracket placeholders. Owner decision | No |
| F-6 | Low (docs) | `.ai-pipeline/reports/AI_ASSISTANT_PHASE_A2_IMPLEMENTATION.md:8,17-18`; `apps/assistant/README.md` (L1 row); `openrouter.py:3-5` | Reading | The handoff header still says the candidate is "**uncommitted**" (it is now `5245bbe`). README/adapter wording says a "wrapped" transport is refused and that the adapter "cannot open a network connection, whatever is injected". That holds for every configuration and every *transport* object, but see I-1 | Wording precision only | Refresh the handoff header at publication; soften "whatever is injected" to "whatever is configured" | No |

Informational (no action required for merge):

- **I-1 (S2 precision).** Containment is a type check: a `MockTransport` handler is arbitrary
  code and could itself forward a request. Reaching it requires a code-level injection into
  `build_chat_model(transport=...)`. No production caller passes one, and the test suite's
  socket guard would catch any network attempt. S2 holds for configuration, environment and
  every transport object.
- **I-2 (import boundary).** The default path imports `budget.py` (and so `sqlite3`) through
  `model_factory`, but never opens or creates a ledger, and the import has no side effects. The
  plan's wording "the default branch never imports … the ledger" is met in effect (no side
  effect), not literally. The CLI imports `httpx` indirectly (through `model_factory` →
  `openrouter`) but makes no request.
- **I-3.** A read-only ledger passes L4 at composition, because SQLite opens it read-only and
  `verify`/`recover` need no write. Every admission is then refused `refused_ledger`, so it
  still fails closed.
- **I-4.** `settle()` on an already abandoned call returns `CallBudget(outcome="abandoned")`,
  which is not in `BUDGET_OUTCOMES`. The metrics record for that rare answer is dropped and
  counted (it never breaks the answer). No double counting (reviewer probe).
- **I-5.** Status codes outside the matrix (`http_other`, for example 409/422) settle at the
  reservation without opening the breaker. The plan's "other unroutable response → breaker"
  row applies only to 503 here.
- **I-6.** The plan's `test_model_profiles.py` and `test_budget_invariants.py` were merged into
  other files (declared deviation 8). Coverage is present.

## 10. Adapter and secret-security results — PASS

- Request builder: fixed URL, model, `provider{order, only, allow_fallbacks:false,
  require_parameters:true, data_collection:"deny", zdr:true, max_price from the record,
  quantizations}`, `reasoning{effort, exclude:true}`, `max_tokens = answer + allowance ≤
  min(4000, endpoint max)`. There are no `user`, `session_id`, `tools`, `plugins` or
  attribution headers. Prices must be exact as JSON numbers (`model_profiles.py:51-60`).
- Stream state machine (`openrouter.py:348-474`) and non-stream parsing (`:281-330`) match
  plan sections 6.2/6.3. Reasoning deltas are never yielded. Content after the finish is
  ignored and flagged. EOF before the finish is `protocol`. A mid-stream error is
  `upstream_midstream`. Read-through problems keep the validated answer
  (`read_through_incomplete`, declared deviation 7). Frames go through the existing
  64 KiB/1 MiB `_sse_frames`. Compressed encoding is refused. The connection is closed in a
  shielded `finally`. Exactly one request, no retries; `warm()` is a no-op. Usage is parsed
  strictly (`parse_float=Decimal`, NaN/Infinity rejected, booleans rejected, counts
  `0 ≤ n < 1e9`, cost `0 ≤ c ≤ 1000`).
- Reviewer secret probe: for 400/401/402/403/404/429/500/503 replies whose body *echoes the
  sentinel*, exactly one request was sent, the sentinel appears only in the outgoing
  `Authorization` header, and it is absent from `str`/`repr` of the error, the guard's
  `repr`, all DEBUG logs (`caplog` at DEBUG) and the ledger bytes. Provider error text is
  never kept.
- Telemetry v2: closed codes and counts only; `profile` is a closed set;
  `requested_endpoint` is pattern-checked; `provider_verified` is always false;
  `generation_ref` is never emitted; invalid records are dropped and counted.

## 11. Budget model and invariants — PASS (labelled bound, OD-6 respected)

State transitions and transaction boundaries were checked in `budget.py`. Every operation is
one `BEGIN IMMEDIATE` transaction on a new connection with a 2 s busy timeout, and lock
contention is refused (`refused_busy`).

| Item | Result |
|---|---|
| `K = B + L + O`; admit only if breaker closed, open calls `< N`, `K + r ≤ C` (`:596-606`) | Verified; boundary equality admitted, +1 µUSD refused (reviewer probe, and across a restart) |
| INV-1 frame | `C`, `U0`, `B`, `P` are all in the key's cumulative frame; `init` sets `B = P_last = U0`, `L = O = 0` (`:349-363`) |
| INV-2 single counting | settle and abandon move `r` out of `O` and `c` into `L` in one transaction; `settle` on a non-open row returns without counting (`:664-667`); `verify` recomputes `L`/`O` from rows. `AUTOINCREMENT` keeps new ids above `H` |
| INV-3 | Checked on admission; randomised test asserts after every admission |
| INV-4 | Cost above the reservation is charged at the actual cost, flagged with an anomaly, breaker opened (reviewer probe: charged 5,000,000 µUSD, breaker `cost_above_reservation`) |
| INV-5 / INV-6 | `reconcile`: `P ≥ P_last`, baseline is `P` (undercount or `--release`) or the estimate (over-count kept); never below `P_last`; `verify` refuses `B < P_last` |
| INV-7 | No date-based term; only lease expiry uses the clock, and it can only increase `L` and open the breaker |
| INV-8 | `init` refuses an existing file, requires `U0` and an approved alias; `K` starts at `U0`; CLI re-init refused (`LEDGER_EXISTS`) |
| INV-9 | Reconcile refused with any open call or within the lag (see F-2 for the CLI flag); `H := max(id)` |
| 15 adversarial cases | Non-zero opening usage ✓; cap boundary ✓; settlement without double counting ✓; missing/malformed usage → `unsettled` at the reservation + breaker, next call refused with **zero** requests ✓; cost above the reservation ✓; crash/abandon (expired lease abandoned, live lease of another instance left alone, late settle not double-counted) ✓; concurrency: 8 threads with `N=1` → exactly 1 admitted; **3 spawned processes × 20 attempts on a cap of 3 reservations → exactly 3 admitted, `K ≤ C`** ✓ (and the implementer's two-process test); async stream cancellation (`aclosing` early exit and task `cancel()`) → shielded settlement at the reservation, no breaker ✓; stale/lower/higher reconcile ✓; release ✓; corrupt/absent/newer/tampered ledger ✓; restart ✓; no date reset ✓; CLI safety (no network request, refusals exit 2 with code-only messages, missing ledger not created) ✓ except F-2; no silent recreation ✓ |
| Fail-closed inputs | Endpoint record validates prices, request price and maximum completion; `reserve` refuses a non-positive reservation or an invalid slug; CHECK constraints refuse non-positive bounds |
| Labelling | Docstrings, README, D-091 X5 and the handoff call the reservation a "labelled (not proven)" bound. No added line calls it proven or globally enforced |

## 12. Architecture review — PROCEED

- One new local persistence owner (the ledger), distinct from the knowledge store. No CLM
  backend write target. No second model router: `ChatModel` stays the only application port,
  and `build_chat_model` is the only composition point. Provider-side limits are documented
  as external controls. Business logic does not branch on provider (`main.py` only reads
  optional `profile_id`/`endpoint_slug` with `getattr` for metrics).
- Dependency direction: `telemetry → llm, model_profiles`; `model_factory → budget, openrouter,
  llm, config`; `main → model_factory`. There are no cycles, and `check_architecture.py` passes.
- Retirement/rollback: removing the profile entry keeps the default path; the default never
  touches the ledger.

## 13. Governance — PASS

- D-091 (`DECISION_LOG.md`) and ADR-012 Amendment 3 are both **PROPOSED**, state everything
  A2 does not do, and reserve D-090/Amendment 2 for PR #114. D-090 and Amendment 2 text are
  untouched (only cross-references were added).
- Numbering: none of the 111 `origin/*` refs contains `D-091` or `Amendment 3` under
  `docs/decisions`.
- Phase B is stated as unauthorised everywhere. Sponsor governance (Q-013) is required for
  non-synthetic data. The budget is described as per key and per instance, not global (D-091
  X8, README). `PROJECT_STATE.md` is unchanged (the remote profile is not a provider row), and
  `check_project_state.py` passes.

## 14. Readiness

- **`pre_pr_check.py`: READY** to run on the committed state `5245bbe` (clean tree), followed
  by its checklist. Not run by this gate.
- **Publication** still needs explicit owner authorisation and an owner decision on D-091 X1–X9
  and Amendment 3 (accept, or merge as PROPOSED with the dormant guarantees; plan section 10.4).
  F-1 to F-6 are recommended before Phase B and are not merge blockers for the dormant code.
  If the owner wants any of them fixed before merge, the changed content needs a fresh
  independent review of that delta.
- **Phase B: BLOCKED** (plan section 15: no endpoint record, BP-2/BP-4/BP-6 and S1 uniqueness
  unverified, O1/O3/O4/O5 open). This gate does not authorise any remote activity.

## 15. Evidence reuse and limits

- Not reused: every result above was produced by the reviewer in this session on the frozen
  snapshots.
- Not executed: `run_e2e.py` harness (section 7); hosted CI; physical Mongo (N/A). Frontend
  typecheck, build and the full frontend suite were not run (the frontend is unchanged and
  the matrix marks them `A`). The implementer's 1,109/1,109 is a claim about identical
  frontend content and was not reproduced.
- The implementer's flake claim for `test_knowledge_answers.py` was not reproduced (that test
  passed on both trees here).

## 16. Zero remote activity and spend

- No command contacted OpenRouter or any non-loopback host. The candidate suite ran under its
  own session socket guard (no teardown error). Reviewer probes and the parity probe each
  installed their own non-loopback connect/lookup guard (zero blocked attempts recorded). All
  OpenRouter behaviour used `httpx.MockTransport` with a fictional endpoint and a sentinel
  key.
- `OPENROUTER_API_KEY`: not set in the reviewer shell (names-only check); each runner also
  unset it without reading it. No `.env` was read or changed.
- No real ledger was created (`apps/assistant/data/budget` is absent in every worktree checked).
  Spend: **US$0.00**.

## 17. Git status and writes

- No commit, amend, rebase, reset, push, PR or merge. The candidate branch, the implementing
  worktree, primary `main` and teammate branches are unchanged.
- Reviewer-owned writes: two detached worktrees (`qg-a2-5245bbe`, `qg-a2-base-7d6a31a`). Inside
  them there are only git-ignored test artefacts (`apps/assistant/data/knowledge`,
  `scripts/__pycache__` in the candidate snapshot). A temporary `apps/frontend/node_modules`
  junction was created and removed (link only; target intact). Everything else is in
  reviewer scratch storage: this report, JUnit files, logs, probes, parity transcripts and
  self-test reports, under
  `C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane-Desktop-FYP-data-dividends-zero-touch-clm\a4779214-d501-4b78-a687-71383149bf20\scratchpad\qg\`.
- The reviewer worktrees were left in place for audit; removing them is an owner choice.
