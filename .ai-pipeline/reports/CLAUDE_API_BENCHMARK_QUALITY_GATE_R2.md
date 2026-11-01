# Claude API Model Benchmark - Independent Quality Gate, Recheck R2

Date: 2026-10-29. Reviewer: the same independent Quality Gate reviewer as R1. I did not write or
remediate any of this content.

Method: `.agents/skills/fyp-quality-gate/SKILL.md`. Read-only except for this report. Nothing went
over the network, no key was set, no paid command ran and nothing was committed.

Scope: the remediation of the R1 findings F1-F8, plus the new `--ledger NAME` option and the
README update. Unchanged evidence from R1 is reused.

The R1 report (`CLAUDE_API_BENCHMARK_QUALITY_GATE.md`, 261 lines, mtime 02:43:23) is unchanged.

## Verdict: PASS

F1 to F8 are all fixed, and I checked each one against the code, the tests and new offline probes.
No Critical, High or Medium finding remains.

Two things carry over into the next step:

- **Owner decision (not a code defect):** `--ledger` makes the US$6 ceiling apply to each ledger,
  not to all experiments together (R2-1).
- **Two Info observations:** R2-2 and R2-3.

## Reviewed content (frozen identity)

| Item | Value |
|---|---|
| Worktree / branch | `C:\Users\shane\Desktop\claude-worktrees\assistant-anthropic-benchmark-20261029` / `feat/assistant-anthropic-model-benchmark` |
| HEAD = base | `f88e1701bbfd0ec1ccc7733c9c980c7843c36d49` (= `origin/main`; uncommitted) |
| `git diff \| sha256sum` | `3a55729df92ca6d2f6db384934bf561971d6ea5e029d8fa6b1255f7c7f335037` (README.md +17, scripts/check_secrets.py +3, tests/test_check_secrets.py +27) |
| `apps/assistant/assistant_eval/claude_bench.py` | `734936e72dc10f8808e7a03d95029b4a767bff1a5730e1041012acbebe00beda` (1067 lines) |
| `apps/assistant/scripts/benchmark_claude.py` | `9d6b5b1b9d4f13d44cd118ff1f34a7a46e99b126342baaab4bebd9cf7523654e` (947 lines) |
| `apps/assistant/tests/test_claude_bench.py` | `3d65069c44e60314023653596f293098e0804f3294a54acc7f2d69c530900d51` (683 lines) |

I recomputed the identity at the end of the recheck and it was unchanged.

Not reviewed (outside scope): `.ai-pipeline/reports/CLAUDE_API_MODEL_BENCHMARK.md` and
`data/eval/claude/run_benchmark.ps1`. The latter is git-ignored.

## Commands and results

| Command | Result |
|---|---|
| `python -m pytest tests/test_claude_bench.py -p no:cacheprovider` (apps/assistant, `PYTHONPATH=.`) | 39 tests, 0 failures, 0 errors, 0 skipped (junit XML) |
| `python -m pytest tests/test_check_secrets.py -q -p no:cacheprovider` (repo root) | 33 passed |
| `ruff check --no-cache` on the 3 new files | All checks passed |
| `ruff format --check --no-cache` on the 3 new files | 3 files already formatted |
| `MYPYPATH=. mypy --no-incremental` on the 3 new files | Success: no issues found in 3 source files |
| `ruff check` on the root check_secrets files | All checks passed. Format status is as in R1: it already fails on `origin/main`. |
| `python scripts/check_secrets.py` | Secret scan passed (exit 0) |
| `git diff --stat -- apps/assistant/ai_assistant` | empty: no runtime or `BASIS_FILES` change |
| grep for `assistant_eval` or `claude_bench` under `ai_assistant/` | no match |
| `git diff --check`; trailing-whitespace grep of the new files | clean |
| Offline client inspection with `HTTPS_PROXY`, `HTTP_PROXY` and `ALL_PROXY` set (real `make_client` and `make_async_client`, no injected transport) | sync and async clients both have 0 mounts, a direct `ConnectionPool`/`AsyncConnectionPool`, `CERT_REQUIRED` with hostname check, `follow_redirects=False`, base `https://api.anthropic.com`, `max_retries=0` |
| Offline money-path probes (scratchpad scripts, in-memory `httpx2.MockTransport`) | see the table below |

### Money-path probes (new code)

| Probe | Ledger result |
|---|---|
| Consumer stops after the first piece (`aclosing`) | `charged_reservation` 2000 = reserved 2000, `upstream_midstream`, open calls 0, breaker closed |
| anyio cancellation mid-stream | the same: charged once at reservation, open calls 0 |
| Opus `speed: "fast"` in message_start usage | `charged_reservation` 130,000 (5 x 26,000; above reserved 80,000), anomaly `speed`, breaker `speed` |
| Output above the reservation (5000 output tokens) | `charged_reservation` 14,500 (5 x actual), `cost_above_reservation`, breaker opens |
| `input_tokens` absent | `charged_reservation` 2000, `usage_missing`, breaker opens |
| Run cap too small (cap 1000 micro-US$) | 0 requests, refused `run_cap`, breaker `refused_run_cap` |
| Synthetic-boundary refusal | 0 requests, breaker `refused_synthetic_text` |
| Second call after a model-mismatch breaker | still 1 request in total; the second call is refused as `breaker_open` |

## R1 findings: recheck

| R1 finding | Status | Evidence |
|---|---|---|
| F1 proxy honoured (Medium) | **Fixed** | `_client_options` (`claude_bench.py:706-719`) always passes an explicit `httpx2.(Async)HTTPTransport(trust_env=False)`, so the SDK's `getproxies()` mount code (`_base_client.py` `if "transport" not in kwargs`) never runs. New test `test_the_real_client_never_routes_through_a_proxy` builds the real sync and async clients without an injected transport and asserts a non-proxy pool and no mounts. My own inspection confirms TLS verification is kept. The old false-confidence test is now backed by a real one. |
| F2 anomalies settled at standard price (Medium) | **Fixed** | `close_call` (`:519-567`): an anomaly or a cost above the reservation charges `max(reserved, cost x 5)`, state `charged_reservation`, and opens the breaker. Routing is checked from both message_start and the final usage (`:966`, `:986-988`). `ANOMALY_PRICE_MULTIPLIER=5` covers the multipliers the code records: fast 2x, US geography 1.1x, Haiku long-prompt 5x. Tested through `stream()` for speed, geography, tier and cache, and probed. |
| F3 refusal does not stop the run; false exit 0 (Medium) | **Fixed** | `_refuse` (`:862-872`) opens the breaker `refused_<code>` for every pre-send refusal except `breaker_open`. `cmd_run` stops on the breaker and exits 0 only when the settled ledger calls for this run label equal the planned calls (`benchmark_claude.py:615-620`). `test_run_stops_all_requests_when_the_breaker_opens` drives the real `cmd_run` through the service and asserts exit 4 and exactly one request. |
| F4 preflight sends without `check_messages` (Medium) | **Fixed** | `benchmark_claude.py:372-375` checks before each `count_tokens` and records a FAIL without sending. Not covered by a unit test (see R2-3). The code path is simple and was inspected. |
| F5 malformed usage; cache not flagged (Low) | **Fixed** | `price_anomalies` adds `usage_missing` and `unrequested_cache`, both tested and probed. Sonnet 5.5 cache-read price: the implementer cites the live page (US$0.10, read 2026-10-29). I could not verify that offline, but it no longer matters: any cache token is an anomaly and is charged conservatively. Residual case in R2-2. |
| F6 `yield` inside a cancel scope (Low) | **Fixed** | `stream()` (`:930-982`) applies `fail_after(remaining())` around `__aenter__`, each `__anext__` and `get_final_message`. No timeout scope is open across a `yield`. Cleanup runs in a shielded `move_on_after(5)`, and the ledger close runs in the outer `finally`. `test_the_whole_call_has_one_deadline` covers the timeout (charged at reservation; transient, so no breaker). |
| F7 test gaps (Low) | **Fixed** | 10 new tests: proxy (x2), anomalies through the stream (x4), missing input, abandon, timeout, `cmd_run` stop with exit code and a stale preflight. Remaining small gaps are in R2-3. |
| F8 nits (Info) | **Fixed** | The per-turn print uses only this turn's new records (`:533-546`). `open_breaker` and `record_provider_usage` roll back on error, and the latter reads its totals inside the transaction. The preflight client is closed in a `finally` (`:406-407`). |

## New findings (R2)

### R2-1 - Low / owner decision: the US$6 ceiling now applies per ledger, not across experiments

- **Where:** `benchmark_claude.py:881-888` (`_select_ledger`); `claude_bench.py:67-70`. The
  comment there still says "US$6 in all".
- **What:** each `--ledger NAME` ledger enforces its own cap of at most US$6 and its own limit of
  at most 51 calls. The code does not cap the total across ledgers.
- **Current state:** the first ledger has already committed US$0.635484, and its calls are used up
  (51/51). A new ledger created with `--cap-usd 6` would allow a combined total of up to
  US$6.635484.
- **Why this is not a defect:** creating a new ledger is a deliberate owner act with an explicit
  `--cap-usd`, and the coordinator states that the next experiment is owner-authorised.
- **What the owner should do:** confirm whether the authorised budget is per experiment or a
  single overall total. If it is an overall total, size each new ledger's `--cap-usd` to what is
  left.
- **Optional hardening:** `init-ledger` could sum the committed spend of the other
  `data/eval/claude/*.sqlite3` ledgers and refuse when that plus the new cap exceeds the overall
  authorised figure.

### R2-2 - Info: other usage gaps that still settle normally

- **Missing output tokens:** if the `message_delta` usage omits `output_tokens`, the call settles
  using the message_start value. Probe: 400 micro-US$, settled, no anomaly. The live API always
  reports `output_tokens` there.
- **Input-token drift:** input tokens far above the counted figure are not flagged. Probe: counted
  10, reported 4000, settled at 650 against a reservation of 1502. The reservation still bounds the
  call, because the `max_tokens` output allowance dominates.
- **Optional fix:** flag `output_tokens <= 1` together with text, and actual input greater than
  1.25 x the counted figure.

### R2-3 - Info: small test gaps

- No unit test covers the F4 preflight boundary skip, `cmd_preflight` in general, or the
  `--ledger` path mapping. `_select_ledger` is used inside the `cmd_run` test and then
  monkeypatched over.
- Hygiene nit: one new README line is over 100 characters (the line starting "The key is read
  only..."). Other long lines already exist in that README.

## Points re-verified

- **Admission order:** every paid send is preceded by the synthetic check, the shape check, the
  SHA approval, the size limit, the SDK-environment check, the key read and a committed ledger
  reservation. No path sends without a reservation; after a breaker, the probe shows no further
  request.
- **Model mismatch:** detected at `message_start` before any text is yielded, as in R1. The
  existing test still passes.
- **Ledger close:** runs exactly once on success, error, abandonment and cancellation (probed).
- **Credentials:** the explicit key and base URL, `open_telemetry=False`, and the refusal of
  `ANTHROPIC_CUSTOM_HEADERS` and `ANTHROPIC_LOG` are unchanged. Records and artifacts hold codes
  only. Sentinel tests pass.
- **Separation:** there is no OpenRouter ledger use, no runtime import and no basis-file change.

## Readiness

- **Gate:** PASS for the frozen content above. The publication workflow still applies: a commit
  or PR only with explicit owner authorisation.
- **Before the next paid experiment:** the owner resolves R2-1 (per-experiment or overall budget)
  and then initialises the new ledger with a matching `--cap-usd`.
- **First run:** its Console reconciliation (`reconcile` on the default ledger) is still pending,
  as noted in R1.
- **Change classification:**
  - Changed: evaluation tooling, secret-scanner rules, README.
  - Unchanged: runtime/API types, schema, connectors, configuration, business rules, mappings,
    runtime authentication and security, architecture, provider status, runtime behaviour.
- **Git:** this gate made no commit, push or PR. No ACRA or GoldTier readiness is implied.
