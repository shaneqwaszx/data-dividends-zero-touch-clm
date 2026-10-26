# AI Assistant Phase A2 — Remediation R1 — Independent re-Quality Gate

> **Publication note (2026-10-26, owner-authorised):** Two example credential lines in this report (the F-5 row of section 4 and the N-2 row of section 5) were reworded from literal test inputs into descriptions, because the repository secret scanner correctly flags those literal shapes. No finding, severity, evidence result or verdict was changed.

| Item | Value |
|---|---|
| Date | 2026-10-26 |
| Role | Fresh independent Stage 3 re-Quality Gate. This reviewer did not implement A2, did not write R1 and did not run the first gate. Skills applied: `fyp-quality-gate`, `integration-security-review`, `persistence-schema-change`, `architecture-change-review` |
| Reviewed commit | `ee8a658cbc82401cb24e81396ee134794c92e5db` (local branch `feat/assistant-phase-a2-20261026-int`, no upstream) |
| Reviewed tree | `177645d00811cb8c79744367de2baecdbb87b639` = expected |
| Parent | `5245bbe80e5fe9a64c479b758abc6a400df88bd0` (tree `a1e139217aa27eec782613974afa39dfc205fee7` = expected; first-gated commit) |
| Base | `7d6a31aa196cff23c0b5b1fd4e5e31cf9bce0efc` = `origin/main` = merge-base. PR #114 content not present |
| Review snapshot | Reviewer-owned `git clone --shared` copies in reviewer scratch (`scratchpad\reqg\snap` detached at `ee8a658`; `scratchpad\reqg\base` detached at `7d6a31a`; `scratchpad\reqg\mid` = `git archive 5245bbe apps/assistant` for differential probes). No worktree was added. The implementing worktree, its branch, primary `main` and teammate branches were not used for review and were not changed |
| Remote activity / spend | **Zero** OpenRouter or other non-loopback inference/API requests. **US$0.00**. `OPENROUTER_API_KEY` never read or printed (names-only environment check: not set; every run also unset it) |

## 1. Verdict

**PASS** for `ee8a658` (tree `177645d0`).

All six first-gate findings F-1 to F-6 are closed by the change, and each was confirmed by
the reviewer's own probes as well as the new tests. Everything the first gate passed still
holds: locks L1–L4, S1–S3, INV-1 to INV-9, byte-identical default-behaviour parity with
`7d6a31a`, `evaluate_answers.py check`, E0 self-tests, and governance. The full assistant suite
has the same 12 environment failures (Windows `Errno 24`) as the exact base, plus the guard
self-test, which hits the same limit. All 13 pass when run alone. There are no regressions in
the suite.

R1 itself introduces **two new low-severity findings** (N-1, N-2). Neither can cause a remote
request or spending in this build, and neither affects the default profile. Both are
recommended before Phase B. Under the first gate's own standard, neither blocks merging the
dormant code. If the owner wants them fixed first, that delta needs another fresh independent
review.

## 2. Identity checks (all passed before review)

| Check | Result |
|---|---|
| Full SHA / branch tip | `ee8a658cbc82401cb24e81396ee134794c92e5db`; `feat/assistant-phase-a2-20261026-int` resolves to it (checked at start and end) |
| Tree | `177645d00811cb8c79744367de2baecdbb87b639` ✓ |
| Parent / parent tree | `5245bbe8…` / `a1e13921…` ✓ |
| Base / merge-base / `origin/main` | all `7d6a31aa…` ✓ |
| Upstream | none (`fatal: no upstream configured`) ✓ |
| `5245bbe..ee8a658` | exactly the 12 expected files (all `M`): handoff report, `apps/assistant/README.md`, `ai_assistant/{budget,model_factory,openrouter}.py`, `scripts/budget_ledger.py`, `tests/test_{budget_cli,budget_guard,model_factory,openrouter_adapter}.py`, `scripts/check_secrets.py`, `tests/test_check_secrets.py`. +368/−26 |
| Implementing worktree | HEAD `ee8a658`; zero tracked or untracked changes. Ignored only: `.ruff_cache`, `apps/assistant/{.mypy_cache,.ruff_cache,data/}` (`data/` holds only `knowledge`), `apps/backend/{.mypy_cache,.ruff_cache}`, `apps/frontend/dist`. Backend caches are ignored tool caches. No `data/budget` |
| Snapshots | `snap` HEAD/tree checked, `git status` clean before and after; imports resolve to the snapshot (`ai_assistant.__file__` printed for every run) |

Reviewed inventory: the full `5245bbe..ee8a658` diff (12 files) line by line, the surrounding
code those lines depend on (`BudgetedChatModel`, `OpenRouterChatModel.stream/_error_body/_status_class`,
`TRIP_ERROR_CLASSES`, `AiAssistantSettings` field bounds, scanner evaluation loop), the first QG
report, handoff §10 and the commit message.

## 3. Scope and regression check — PASS

- Only F-1 to F-6 changed. `git diff --stat 5245bbe ee8a658` is empty for `apps/backend`,
  `apps/frontend`, `docs/`, `e2e`, `prompts.py`, `main.py`, `guardrails.py`, `knowledge/`,
  `answer_records.py` and `llm.py`. No prompt, retrieval, catalog, guard, route, notice,
  answer-record or frontend change.
- I-1 to I-6 are untouched: the transport type check (I-1), the import boundary (I-2: `model_factory`
  adds only `import math`), read-only ledger behaviour (I-3), `settle` on abandoned rows (I-4), the
  `http_other` mapping (I-5) and test file layout (I-6) are unchanged.
- `git diff --check 5245bbe ee8a658` clean. `--numstat` equals `--numstat --ignore-cr-at-eol`
  (368/26): no EOL churn. No new untracked Markdown (the handoff is committed).

## 4. Disposition of F-1 to F-6

| ID | Disposition | Evidence (reviewer probes in `scratchpad\reqg\probes\test_reqg_probes.py` unless noted, plus the new tests) |
|---|---|---|
| F-1 | **CLOSED** | `BudgetedChatModel._reserve` (`budget.py:853-856`) checks `message_bytes(messages) > inner.max_prompt_bytes` before `reservation_for`/`reserve`. In both `complete()` and `stream()`, `_reserve` runs before the `try`, so nothing is settled. Boundary probe at limit 2048, both routes: limit−1 and limit compose a request and write 1 row; limit+1 raises `prompt_too_large` with `budget is None`, **0 requests, 0 `calls` rows**, `committed = open_calls = local_charged = 0`. Multibyte prompt (600 chars / 1,200 bytes > 1024) refused the same way. Through `create_app`, `/chat` and `/chat/stream` give today's `case_data` fallback, 0 requests, 0 rows, and one metrics record with `provider_error_class="prompt_too_large"` and `budget=None` (record kept, not dropped). The adapter's own `_check_size` remains as a second check |
| F-2 | **CLOSED** | Ledger (`budget.py:764-767`) refuses `-1`, `-1e-9`, NaN, ±inf, `86400.5`, `86401`, `"600"`, `None` with `INVALID_INPUT`. CLI `_settle_lag` (`budget_ledger.py:113-123`) reads `AI_ASSISTANT_BUDGET_SETTLE_LAG_SECONDS` through `AiAssistantSettings(_env_file=None)` (no `.env`). 11-case CLI matrix: default 600 → refused; flags `-1/0/599.999` under the default → `RECONCILE_REFUSED`; configured 0 → reconciles; configured 0 with `-1` → refused; `nan`/`inf`/`86401` → `INVALID_INPUT`; configured 30 with `29` → refused. The ledger is unchanged after every refusal (`last_provider_usage` stays 3,000,000). Notes: I-R2, I-R4 |
| F-3 | **CLOSED** (one new low finding on the error path: N-1; precision note I-R3) | `complete()` (`openrouter.py:301-339`) now uses `send(stream=True)`, `Accept-Encoding: identity`, one `deadline = monotonic() + timeout`, `_bounded_body` reads `iter_raw()` under the deadline, refuses non-identity `Content-Encoding` on 200, closes the response in `finally`, and refuses again if the deadline passed before parsing. Probes: 4 MiB offered → `protocol` after pulling ≤ 1 MiB + one chunk; a 10 MiB 500 body → `upstream` after pulling ≤ 16 KiB + one chunk; `gzip/br/deflate/zstd/GZIP` → `protocol`; `Identity` accepted; slow drip (8-byte pieces every 50 ms, timeout 0.3 s) → `timeout` in < 1 s; headers later than the deadline with an in-memory body → `timeout` (no answer accepted). Exactly one request each. Golden test shows the default adapter still sends `gzip, deflate`; `llm.py` is unchanged since `5245bbe` |
| F-4 | **CLOSED** (note I-R2) | `_within_declared_bounds` (`model_factory.py:52-82`) re-checks the 7 bounded settings against their pydantic `Field` metadata, after L1 and before L3 and the credential. 17 extra probe cases, all refused `SETTING_OUT_OF_BOUNDS` with an environment mapping that fails on any access, so the credential is never read: in-flight 50/5/1.0, prompt bytes 1023/262145/`"32768"`, temperature −0.0001/−inf/`"0.2"`, timeout −1/600.0001/`True`, answer tokens 15/4001, allowance 4001, lag 86401/1.5. The message holds only the setting name. Valid `model_construct` settings still compose. The default profile ignores the check (`model_construct(budget_max_in_flight=50)` → local adapter) |
| F-5 | **CLOSED** for (a) and (b) (but see the new finding N-2) | (a) detected: a quoted literal assigned through an `os.environ[...]` subscript (double quotes, single quotes, spaced subscript), through a TypeScript `process.env[...]` subscript, and through a `settings[...]` subscript naming `AI_ASSISTANT_LLM_API_KEY`; the value is absent from the findings. (b) accepted: `K=<your key>`, `K: "<paste the key here>"`, `os.environ["K"] = "<your openrouter key>"`, `K=`, `AI_ASSISTANT_LLM_API_KEY="ollama"`. Runtime references (`= settings.remote_key`, `= SENTINEL_KEY`, reads) are not flagged. `main()` prints only path, line and rule (code read; existing `test_main_never_prints_an_assistant_credential_value` passes). **Repository:** the old (`5245bbe`) and new scanners were both run over all 2,343 tracked files of the snapshot: 0 findings each, so no new false positive. `check_secrets.py` exit 0. `tests/test_check_secrets.py`: 20 passed |
| F-6 | **CLOSED** (minor note I-R5) | README L1 row and adapter docstring now say the check is on the transport object's type and that a mock handler is not inspected. That matches I-1. The handoff header no longer says "uncommitted" and §9/§10 are current |

## 5. New findings (R1 delta)

No critical, high or medium findings.

| ID | Severity | Location | Reproduction | Expected vs actual | Impact | Remediation | On base / `5245bbe`? |
|---|---|---|---|---|---|---|---|
| N-1 | Low | `apps/assistant/ai_assistant/openrouter.py:286-299` (`_bounded_body`), `:321-326` | `probes/slow_error_body.py`, `probes/slow_error_guard.py`: mock 401/402/403/429 whose error body arrives after the 0.3 s deadline | Expected (as the stream path does in `_error_body`, `:369-383`): a failed error-body read keeps the **status** class. Actual in `complete()`: `timeout` for 401/402/403/429. Through the guard, `/chat` (complete) gives `class=timeout, breaker_open=False`, while `/chat/stream` gives `class=payment, breaker_open=True`. A read error in the same place would give `transport` | Trip-class refusals (`auth`, `payment`, `forbidden`, …, see `TRIP_ERROR_CLASSES`) on the non-stream route do not open the breaker when the error body is slow or broken, so the next call is admitted instead of stopping for an operator. Spending stays bounded: each call is still charged its reservation (`unsettled`). Dormant: no real transport can be composed in A2 | In `complete()`, read the error body like `_error_body`: swallow `timeout`/`httpx` errors during the bounded error-body read and classify by status; add a test for slow 401/402 bodies on `complete()`. Before Phase B | Introduced by R1. On `5245bbe` the same mock probe gives `auth/payment/forbidden/rate_limited`. With a real transport, `5245bbe` would also give `timeout` if a single read exceeded the per-read timeout. Not on base (no remote adapter) |
| N-2 | Low | `scripts/check_secrets.py:41` (`CREDENTIAL_VALUE`) with `is_placeholder` `:135-140` | Probe `test_f5_angle_prefix_then_literal_old_vs_new` (value built at run time): `OPENROUTER_API_KEY` set to an angle-bracket placeholder immediately followed by a literal, in bare `=`, double-quoted `=` and YAML `:` forms | Expected: a literal after a placeholder is still flagged, as on `5245bbe` (`assistant-credential-assignment` / `-mapping`). Actual on `ee8a658`: **not flagged**. The new alternation captures only the leading `<…>`, which `is_placeholder` accepts, so the trailing literal is never inspected | A small detection gap that R1 introduced in exchange for the F-5(b) fix. It needs an unusual "placeholder glued to a value" form. A real OpenRouter key (`sk-or-…`) on that line is still caught by the independent `openrouter-key` rule. No repository file is affected | Only accept the placeholder alternative when it is followed by an end of value, for example `(<[^<>\n]{1,64}>(?=["'\s#]|$)|[^"'\s#]*)`; add a test for `<x>literal`. Owner decision / before Phase B | Introduced by R1 (`5245bbe` detects it). Not on base |

Informational (no action required for merge):

- **I-R1 (scanner, fail-safe).** The new subscript rule flags some synthetic source shapes that
  are not assignments of a literal: `assert environ["K"] == expected`, `assert environ["K"] == "x"`
  and `os.environ["K"] = os.environ.get("OTHER", "")`. None occurs in the repository (0 findings).
  These fail safe.
- **I-R2 (edge inputs).** `model_construct(remote_max_prompt_bytes=10**400)` raises a bare
  `OverflowError` from `math.isfinite` instead of `SETTING_OUT_OF_BOUNDS`. Composition still
  fails closed, and the error holds no value. `BudgetLedger.reconcile(settle_lag_seconds=True)` is
  treated as 1 s (bool is an int). The CLI's `float` flag cannot produce this.
- **I-R3 (deadline precision).** In the sync `complete()` the whole-request deadline is
  cooperative. It is checked between body chunks and before parsing; it does not cancel a
  blocking phase as the async path's `anyio.fail_after` does. Each blocking phase (connect,
  write, response headers, one chunk read) is still bounded by httpx's per-phase timeout, and no
  answer is accepted after the deadline. The previously unbounded slow-drip case is closed.
  Revisit if Phase B needs a hard wall-clock bound.
- **I-R4 (CLI).** An invalid configured lag (`abc`, `-5`, `86401`) makes `reconcile` raise an
  uncaught pydantic `ValidationError` (non-zero exit, ledger unchanged), not a coded `refused (…)`
  line. `_path()` already used the same settings construction when `--ledger` is absent. The
  error shows only the invalid setting's input, which is not a secret.
- **I-R5 (docs).** Handoff §10 says the re-verification run is "recorded in the commit message",
  but the commit message records only the parity claim, not the test counts. Handoff §6 still
  shows the pre-R1 counts. Wording only.
- **I-R6 (test hygiene).** `test_the_settle_lag_cannot_be_shortened_below_the_configured_lag[0]`
  assumes `AI_ASSISTANT_BUDGET_SETTLE_LAG_SECONDS` is unset. `tests/conftest.py` does not clear it.
  A developer who exports 0 would see a false failure. The test is not wrong for CI.

## 6. Tests and checks (exact counts, all run by this reviewer on the frozen snapshots)

Interpreter: the primary checkout's `.venv` (Python 3.12.10, pytest 8.4.2, httpx 0.28.1,
chromadb 1.5.9, ruff 0.16.2, mypy 1.20.2), used read-only with `PYTHONPATH` pinned to each
snapshot. System Python lacks chromadb, so the first attempt failed at collection (27/23 import
errors) and was discarded.

| Check | Result |
|---|---|
| Full assistant pytest, **base** `7d6a31a` (JUnit) | 1,574 collected: **1,562 passed, 12 failed, 0 skipped, 0 errors** (399 s) |
| Full assistant pytest, **candidate** `ee8a658` (JUnit) | 1,831 collected: **1,818 passed, 13 failed, 0 skipped, 0 errors** (465 s). +257 vs base (236 from `5245bbe` + 21 from R1), 0 removed. This matches the implementer's 1,818/13 claim |
| Failure classification (JUnit, test by test) | 12 × `OSError: [Errno 24] Too many open files`: `test_required_p2::test_real_http_sse_framing[5]`, `test_streaming_resources::test_loopback_total_deadline[5]`, `::test_real_chunked_http_enforces_budgets[oversized, many-frames]`. These are **identical on base and candidate** (environment blocker). The 13th, `test_model_factory::test_the_suite_guard_blocks_remote_connections` (candidate only), has the same Errno 24 cause and passes alone. **Isolated rerun of those three files plus the self-test on the candidate: 148/148 passed.** New regressions: 0 |
| All A2 test files alone (`test_budget_cli` 17, `test_budget_guard` 18, `test_budget_ledger` 60, `test_default_request_golden` 6, `test_model_factory` 61, `test_openrouter_adapter` 95, `test_telemetry` 50) | **307/307 passed**. R1-related tests in the full run: 27/27 passed |
| Reviewer probes `test_reqg_probes.py` | **90/90 passed**: 89 checks plus the snapshot-identity check, including the observations reported in §5. Separate scripts: `slow_error_body.py` (on `5245bbe` and `ee8a658`), `slow_error_guard.py`, `locks_probe.py` |
| `ruff check` (`ai_assistant assistant_eval scripts tests`) | All checks passed |
| `ruff format --check` | 92 files already formatted |
| `mypy --strict` (`ai_assistant`, `assistant_eval`, `scripts/budget_ledger.py`, `scripts/evaluate_answers.py`) | Success: no issues in 43 source files |
| `tests/test_check_secrets.py` (repo root) | 20 passed |
| `check_secrets.py` | exit 0 (PASS) |
| `check_architecture`, `check_external_provider_readiness`, `check_policy_authority`, `check_project_state`, `check_tooling_config` | all exit 0 (PASS) |
| `check_mongodb.py` | exit 1 `MONGO_URI_UNAVAILABLE` (no URI in the environment; no connection attempted). **Not applicable**: there is no Mongo surface, so physical Mongo is N/A. This is not reported as a pass |
| Backend `apps/backend/tests/test_ai_assistant_main_integration.py` (snapshot backend + snapshot assistant) | **2 passed** (`[mock]`, `[sandbox]`) |
| `evaluate_answers.py check` | base and candidate both: `snapshots are current (84 turns, sha256 9341411d512d3beb)` |
| E0 self-tests `run --model self-test-{perfect,random,prose,injection,empty}`, base vs candidate | all 10 exit 0. Reports differ only in `generated_at`, `manifest.git_head` and latency p50/p95 fields |
| Assistant-streaming E2E `apps/frontend/e2e/assistant-streaming.e2e.ts:10`, direct Playwright | **1/1 passed** (3.3 s; real Chromium; `CLM_E2E_BACKEND_ORIGIN=http://127.0.0.1:59871`, an unused loopback origin; output under the scratch clone). `node_modules` came from a temporary junction to the primary checkout. Its `apps/frontend/package.json` and lock are byte-identical to the snapshot. The junction was removed afterwards and its target is intact |
| `run_e2e.py` harness / POC lifecycle | **NOT EXECUTED**: `tesseract` is not on PATH and there is no disposable Mongo. The reviewer did not start services |
| Full backend pytest, frontend Vitest/typecheck/build | **Not rerun (reused by reference).** Backend and frontend files are byte-identical between `5245bbe` and `ee8a658` (empty diff), so the first gate's results apply unchanged: backend 3,173 passed / 177 skipped / 0 failed; frontend assistant Vitest 108/108. Disclosed as reuse, not as evidence produced here |
| Hosted CI | Not executed (nothing pushed) |

## 7. Re-check of what the first gate passed — all still hold

- **Locks L1–L4** (`locks_probe.py` on the shipped registry): shipped
  `APPROVED_PROFILES["openrouter_gpt_oss_120b"].endpoints == ()`. No transport → `PROFILE_DORMANT`;
  `HTTPTransport()` and a `MockTransport` subclass → `TRANSPORT_NOT_ALLOWED`; shipped registry →
  `ENDPOINT_NOT_APPROVED`; `d-091` → `DECISION_INTERLOCK`; missing ledger → `LEDGER_UNAVAILABLE`, with
  no parent directory created; all locks open with the test registry → composes `BudgetedChatModel`;
  no key → `CREDENTIAL_MISSING`. Importing `ai_assistant.main` with environment settings that
  select the remote profile refuses start-up with `PROFILE_DORMANT`, and the message holds no value.
  R1 inserted only the bounds check after L1; L2–L4 code is unchanged.
- **S1–S3**: `model_profiles.py` is unchanged; `provider.order/only/allow_fallbacks:false` is
  unchanged (adapter request-policy test passes). The transport check is unchanged (I-1 still
  applies). Ledger schema, columns and write paths are unchanged. R1 adds only an input check in
  `reconcile` and a pre-reservation refusal that writes nothing.
- **INV-1 to INV-9**: unchanged ledger arithmetic. INV-9 is tightened (lag bounded 0–86,400 s; the
  CLI cannot shorten the configured lag). `test_budget_ledger.py` 60/60, including the seeded
  randomised sequences and the two-process test.
- **Default-behaviour parity** (reviewer-written `probes/parity_probe.py`, independent of the first
  gate's probe): service default composition (`create_app` builds the model from settings), a
  loopback fake OpenAI-compatible server recording path, all headers except `Host`, and body; 7
  modes (ok, prose/guard-invalid, length, empty, HTTP 500, malformed JSON, stream EOF before
  finish) × 10 questions × 2 histories × `/chat` and `/chat/stream`, plus `/brief` and `/health`.

  | Run | Responses | Model requests | SHA-256 |
  |---|---|---|---|
  | Base `7d6a31a` run 1 / run 2 | 282 / 282 | 253 / 253 | `95bd00d6a9d4f933ccbdef259b5d028e8f706063005d871db813d81c0146ce29` (both) |
  | Candidate `ee8a658` run 1 / run 2 | 282 / 282 | 253 / 253 | `95bd00d6a9d4f933ccbdef259b5d028e8f706063005d871db813d81c0146ce29` (both) |
  | Control (base, temperature 0.21) | 282 | 253 | `a8123a6d…f368a` (differs, so the probe is sensitive) |

  Base and candidate transcripts are **byte-identical** (`cmp`). The transcript mixes model answers
  (`answered_by: model` in the ok/length/eof-chat modes) with every fallback mode. Limitation: the
  probe's `ai_assistant` log capture recorded 0 lines on both trees, so log parity is covered only
  by the first gate's probe. No `data/budget` was created in either tree (only `data/knowledge`).
- **`evaluate_answers.py check` and E0**: see §6.
- **Governance**: R1 changes no `docs/` file. D-091 (`DECISION_LOG.md:1110`) and ADR-012
  Amendment 3 (`ADR-012…:507`) are both **PROPOSED**. `7d6a31a..ee8a658` under `docs/` is
  additions only (76 lines, 0 deletions), so D-090 and Amendment 2 are untouched (D-091 states they
  are reserved by PR #114). Phase B is stated as unauthorised, and Q-013 is required beyond
  synthetic data. `PROJECT_STATE.md` is unchanged. No `refs/remotes/origin/*` ref contains `D-091`
  or `Amendment 3 -` under `docs/decisions`. This used the local refs as they are; the reviewer
  did not fetch.

## 8. Architecture / persistence / security review

- **Architecture: PROCEED.** No new owner, port or dependency edge. The `budget → llm.message_bytes`
  import already existed. `model_factory` adds only `math`. The guard and the adapter now both
  enforce the prompt bound (defence in depth).
- **Persistence: PASS.** No schema, migration or `user_version` change. The pre-reservation refusal
  writes nothing. The `reconcile` input check runs before any transaction. The CLI still never
  creates a ledger.
- **Integration security: PASS with N-1.** The single endpoint path, credential handling (read
  last; never in errors or logs) and request policy are unchanged. The non-stream read is now
  byte- and deadline-bounded with identity encoding. N-1 is a breaker-classification gap, not a
  disclosure or a request-count issue (one request, no retry).

## 9. Zero remote activity and spend

- Every remote behaviour used `httpx.MockTransport` with a fictional endpoint and a sentinel key.
  The candidate suite ran under its own session socket guard (no teardown error). The reviewer
  probes installed a non-loopback `connect`/`getaddrinfo` guard and recorded **0 blocked
  attempts**. The parity probe's guard also recorded 0 (`"blocked": []` in all five runs). The only
  sockets opened were loopback (the parity fake server, the E2E's own Node server, the suite's
  loopback tests).
- `OPENROUTER_API_KEY`: names-only check showed it is not set; every Python run used
  `env -u OPENROUTER_API_KEY`. No `.env` was read or changed. `check_mongodb.py` reads only the
  process environment.
- No real ledger: `apps/assistant/data/budget` is absent in both snapshots and in the implementing
  worktree. Spend: **US$0.00**.

## 10. Readiness

- **`pre_pr_check.py`: READY** to run on the committed, clean state `ee8a658`, followed by its
  checklist. This gate did not run it.
- **Publication** still needs explicit owner authorisation and the owner's decision on D-091
  X1–X9 / Amendment 3. N-1 and N-2 are Low and are recommended before Phase B. If either is fixed
  before merge, the changed content needs a fresh independent review of that delta.
- **Optional owner action:** run the `run_e2e.py` harness for `e2e/assistant-streaming.e2e.ts:10`
  on a machine with Docker and Tesseract.
- **Phase B: BLOCKED** (no endpoint record; S1 uniqueness and the plan §15 prerequisites remain
  open). This gate authorises no remote activity.

## 11. Git status and writes

- No commit, amend, rebase, reset, stash, push, PR or merge. The candidate branch is still
  `ee8a658`, and the implementing worktree has zero changes. Primary `main` is at `1d03986` with the
  same 11 untracked entries as at the start. No teammate branch was touched. No worktree was added
  or removed. No cache or `dist` was deleted. No process was stopped.
- Reviewer-owned writes are all under
  `C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane-Desktop-FYP-data-dividends-zero-touch-clm\16d2f37d-4e02-4147-a009-7acd402e2a26\scratchpad\reqg\`:
  the clones `snap`, `base` and the archive `mid` (each with git-ignored test artefacts such as
  `apps/assistant/data/knowledge` and `tmp/browser-evidence`), `probes\` (probe sources), `out\`
  (JUnit `junit-{base,snap,isolated,a2,probes}.xml`, logs, parity transcripts, E0 reports, E2E log)
  and this report. The temporary `node_modules` junction was created and removed (link only).
