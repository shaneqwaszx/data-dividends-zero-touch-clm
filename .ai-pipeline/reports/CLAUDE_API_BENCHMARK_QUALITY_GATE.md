# Claude API Model Benchmark - Independent Quality Gate

Date: 2026-10-29. Reviewer: an independent Quality Gate session that did not write or fix this content.
Method: `.agents/skills/fyp-quality-gate/SKILL.md`. Review only: no source, test or config file was
edited, nothing was sent over the network, no money was spent, and the key variable was never set.

## Verdict: FAIL

Most controls are sound. Admission goes through the ledger, the model check runs before any text
is shown, the code never reads a credential from the SDK environment, no runtime file changed, and
the static checks pass. The gate still fails for four reasons:

- the "no proxy" destination control is not enforced, and a test claims that it is;
- the ledger records too little for a pricing anomaly or a malformed usage report;
- a refusal before sending (privacy or spending control) does not stop the run, and the run can
  still exit 0;
- the free preflight sends prompt text without running the D-094 check.

All four are bounded fixes. None of them affected the paid run that has already been made (see the
run observation below).

## Reviewed content (frozen identity)

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-anthropic-benchmark-20261029` |
| Branch / HEAD | `feat/assistant-anthropic-model-benchmark` / `f88e1701bbfd0ec1ccc7733c9c980c7843c36d49` (= `origin/main`; all changes uncommitted) |
| `git diff \| sha256sum` | `cfe3428ad638d7178c76a6277e0844798e86de6007607dcdf49fc11d39fe00ea` (README.md, scripts/check_secrets.py, tests/test_check_secrets.py; +45 lines) |
| `apps/assistant/assistant_eval/claude_bench.py` | `abe0136f16aeb634d888f0ec29be7a3dc24f0aea222dd9025497b9536464da26` |
| `apps/assistant/scripts/benchmark_claude.py` | `d9a91f4aa7c346f618cdf3c8a897ccce8a37433f4adb6d8f247581f4ae9608c3` |
| `apps/assistant/tests/test_claude_bench.py` | `5b9c85941b1ae1e746ab42600bc040f59a3fbfebed386fddc650853c65b2d436` |

Not reviewed: `.ai-pipeline/reports/CLAUDE_API_MODEL_BENCHMARK.md`. It appeared during the gate
(mtime 02:36) as an untracked file and is outside the assigned scope. The code files under review
were last modified between 02:19 and 02:24 and did not change during the gate.

## Commands and results

| Command | Result |
|---|---|
| `python -m pytest tests/test_claude_bench.py -q -p no:cacheprovider` (apps/assistant, `PYTHONPATH=.`) | 29 passed |
| `python -m pytest tests/test_check_secrets.py -q -p no:cacheprovider` (repo root) | 33 passed |
| `ruff check --no-cache` on the 3 new files | All checks passed |
| `ruff format --check --no-cache` on the 3 new files | 3 files already formatted |
| `MYPYPATH=. mypy --no-incremental` on the 3 new files | Success: no issues found in 3 source files |
| `ruff check` on scripts/check_secrets.py and tests/test_check_secrets.py | All checks passed |
| `ruff format --check` on the same 2 root files | Would reformat both. This is **not a regression**: the `origin/main` versions fail the same check, because no root ruff config exists. |
| `python scripts/check_secrets.py` (repo root) | Secret scan passed (exit 0) |
| `git diff --stat -- apps/assistant/ai_assistant` | empty: no runtime file changed, so no file in `BASIS_FILES` changed |
| `grep assistant_eval\|claude_bench apps/assistant/ai_assistant` | no match: the runtime does not import the evaluation package |
| `git diff --check`; trailing-whitespace grep of the new files | clean |
| `git check-ignore` on `data/eval/claude/ledger.sqlite3` and `data/anthropic-sdk` | both ignored (`.gitignore:55`) |
| Offline adversarial probes (scratchpad scripts using the suite's in-memory `httpx2.MockTransport`) | results under Findings |

## Acceptance check against the owner requirements

| Requirement | Status |
|---|---|
| Synthetic-only data; `check_messages` gates every send | **Partial.** The paid stream checks first (`claude_bench.py:830`). The preflight `count_tokens` does not (F4). |
| Prompts approved by SHA in the offline dry run | Met. `cmd_prompts` refuses on any boundary or shape failure, and `stream` refuses an uncounted SHA. |
| At most US$6 in total; at most US$0.10 reserved per call; at most 51 calls; one call open at a time | Met. The ledger enforces these in Python and in the SQLite `CHECK` constraints. `BEGIN IMMEDIATE` makes admission atomic. |
| Reservation formula vs. published prices | Input x 1.25 plus `max_tokens` x output price is correct for standard pricing. Thinking is billed inside `max_tokens`. The Haiku tier above 100K tokens is refused. **Gaps in F2 and F3.** |
| One request per model and question; no automatic retries | Met. `max_retries=0`, there are no fallbacks, and tests assert a single request per error. The runner streams once per turn. |
| Stop all remaining requests on an unexpected charge, a provider discrepancy, a privacy violation or a spending-control failure | **Partial.** The breaker covers model, tier, geography, speed, cost above reservation and the Console reconcile. Pre-send privacy and spending refusals do not stop the run (F3). |
| Key never in tracked files, logs, reports, artifacts or the ledger | Met. Records hold codes only. `CallRecord` and `LedgerStatus` contain no key. A sentinel test checks the ledger and records. No key-shaped value was found in `data/eval/claude/`; the only hit is an instruction line in `run_benchmark.ps1`. |
| Not routed through the OpenRouter ledger or profile system | Met. The benchmark has its own SQLite ledger and imports only `ai_assistant.llm` types and `synthetic_boundary`. |
| Runtime does not import `assistant_eval`; basis files unchanged | Met. |
| Ordering and meaning of system messages preserved | Met. Leading system messages become `system` blocks in order. Any other shape is refused rather than rewritten. |
| Exact-line guard (answers go through the real service) | Met. `assistant_eval.runner.run` sends answers through `main.py` and `StreamingGuard`. The through-service test shows that free prose is withheld. |
| SDK environment cannot redirect the request or add headers | **Partial.** The code passes the base URL and key explicitly and refuses `ANTHROPIC_CUSTOM_HEADERS` and `ANTHROPIC_LOG`. Environment and registry **proxies still apply** (F1). |

## Findings (by severity)

### F1 - Medium (security control not enforced; the test gives false confidence): proxy settings are honoured despite `trust_env=False`

- **Where:** `claude_bench.py:671-705` (`_client_options`, `make_async_client`, `make_client`); the
  claims at `claude_bench.py:14` and `:681-683`; the test at `tests/test_claude_bench.py:360`.
- **SDK source:** `anthropic/_base_client.py` lines 1022 and 1773. When no `transport` is given,
  `DefaultHttpxClient` and `DefaultAsyncHttpxClient` build proxy mounts from
  `get_environment_proxies()`, which calls `urllib.request.getproxies()`. That reads
  `HTTPS_PROXY`/`ALL_PROXY` and, on Windows, the registry proxy. It does this whatever
  `trust_env` is set to.
- **Reproduced offline:** with `HTTPS_PROXY=http://127.0.0.1:9`, `make_async_client(...)._client`
  has an `https://` mount, and the transport it picks for `https://api.anthropic.com/v1/messages`
  is `AsyncHTTPProxy`.
- **Failure scenario:** a proxy that is set system-wide, or by antivirus or corporate software,
  routes the paid requests through it. On Windows, httpcore2 verifies TLS with `truststore`, which
  uses the OS trust store. So a TLS-inspecting proxy with an OS-trusted root sees the bearer key
  and the prompts.
- **Why the test gives false confidence:** `test_a_call_is_pinned_settled_and_content_free` sets
  `HTTPS_PROXY` but injects a `MockTransport`. That skips the proxy-mount code entirely, so the
  test cannot detect the problem.
- **Fix:** do either of the following:
  - pass an explicit `transport=httpx2.AsyncHTTPTransport(...)` (sync: `HTTPTransport`) so the
    SDK builds no proxy mounts;
  - or refuse, before reserving, when `urllib.request.getproxies()` is non-empty, in the same way
    as `sdk_environment_refusal`.

  Then add a test that builds the real client without an injected transport and asserts that no
  proxy mount exists.

### F2 - Medium (money accounting): a pricing anomaly is settled at the standard price

- **Where:** `claude_bench.py:909` and `:919-920` (`cost_micro` with standard prices whenever
  `failure is None`); `:516-521`.
- **Probe:** usage reporting `speed: "fast"` closes the call as `settled`, charged 650 micro-US$
  (Haiku) or 26,000 micro-US$ (Opus), which is the standard price. The breaker does open
  (`speed`). Opus 5.5 fast mode is billed at 2x ($8/$40).
- **Failure scenario:** a priority, fast or regional-geography call is recorded at roughly half
  of, or below, its real cost. "Committed" then understates real spend, so the US$6 cap and
  `reconcile` are computed from too small a number. `cost_above_reservation` also cannot fire for
  that call, because the cost is computed at standard rates.
- **Fix:** when `price_anomalies` is non-empty (or `final.model` mismatches), charge
  `max(reservation, cost x the known multiplier)`, or simply the full reservation, and record the
  call as `charged_reservation` (conservative).

### F3 - Medium (requirement deviation and false success): a refusal before sending does not stop the run, and the run can exit 0

- **Where:** `claude_bench.py:820-823` and `:830-857` (`_refuse` never opens the breaker);
  `benchmark_claude.py:513-515` (the only stop check is `breaker_open`) and `:598-599`
  (`asked` counts service turns, not calls made).
- **Probe:** a `synthetic_text` refusal leaves the breaker closed.
- **Failure scenario:** any of the following causes refusals while the remaining calls still go
  out:
  - a prompt that drifts after preflight (`prompt_not_approved`);
  - a boundary failure (`synthetic_text`);
  - `sdk_environment`;
  - the credential being removed mid-run;
  - a ledger refusal such as `per_call_ceiling`.

  The turn falls back to case data, `asked == planned`, the breaker stays closed, and `cmd_run`
  returns 0. This contradicts the owner requirement to stop all remaining requests on a privacy
  violation or a spending-control failure, and it reports success falsely.
- **Fix:**
  - For `synthetic_text`, `prompt_shape`, `prompt_not_approved`, `sdk_environment` and the ledger
    refusal codes other than `breaker_open`, open the ledger breaker, or have `cmd_run` stop on
    any record whose `refused` is set.
  - Make the exit code require one settled call per planned turn, with no refusals.
  - Test this through `cmd_run`.

### F4 - Medium (requirement deviation, low practical risk): preflight `count_tokens` sends prompt text without `check_messages`

- **Where:** `benchmark_claude.py:365-378`.
- **What happens now:** prompts are matched by SHA to the approval file, but the approval only
  records that the check passed when `prompts` ran. `prompt_version()`
  (`ai_assistant/telemetry.py:287`) does not hash `synthetic_boundary.py` or its vocabularies.
- **Failure scenario:** the boundary is made stricter after approval. The preflight then still
  sends text that the current boundary would refuse, to `/v1/messages/count_tokens`.
- **Fix:** call `check_messages(messages)` and `cb.to_anthropic` immediately before each
  `count_tokens` call, and record a failed check (do not send) when the check fails.

### F5 - Low (defensive accounting): malformed or missing usage counts as zero, and cache tokens that were never requested are not anomalies

- **Where:** `claude_bench.py:733-758` (`count()` returns 0 for missing or non-int values);
  `:243-255` (no cache check); `:113` (Sonnet cache-read price US$0.10/MTok).
- **Probes:**
  - With `input_tokens` absent from usage, the call is settled at 250 micro-US$ (output only),
    with no anomaly.
  - 3,990 `cache_read` tokens were settled, with no anomaly.
- **Pricing discrepancy:** the bundled Claude API reference (cached 2026-10-06) lists Sonnet 5.5
  cache reads at US$0.20/MTok. Opus 5.5 is listed at US$0.20, which matches the code. The code's
  evidence line says the pricing page was read on 2026-10-29. I could not confirm the live page
  offline, so the owner should re-verify this.
- **Practical impact:** none in this benchmark, because caching is never requested.
- **Fix:**
  - Treat a missing or invalid `input_tokens`/`output_tokens` as unknown: charge the reservation
    and add an anomaly.
  - Treat any non-zero cache creation or cache read as a `cache_unrequested` anomaly.
  - Re-verify the Sonnet cache-read price.

### F6 - Low (robustness): `yield` inside an `anyio.fail_after` cancel scope in an async generator

- **Where:** `claude_bench.py:881-904`.
- **The problem:** if the deadline fires while the generator is suspended at `yield`, the
  cancellation lands in the consumer's code rather than inside the scope. anyio and PEP 789
  document this hazard. The repository's own pattern (`openrouter.py:416-450`, `llm.py:403`)
  wraps only the awaits and checks a deadline instead.
- **Money impact:** none. The `finally` still closes the ledger, and an orphaned `open` call blocks
  later calls.
- **Fix:** use a deadline with `fail_after` around each `anext()` rather than around the `yield`.

### F7 - Low (test adequacy)

These paths have no tests:

- consumer abandonment or cancellation mid-stream (the probe confirms the right behaviour:
  `charged_reservation`, error `upstream_midstream`, a single close);
- a price anomaly or `cost_above_reservation` arriving through `stream()`;
- the timeout and transport-error paths;
- the `final.model` mismatch path;
- `cmd_run`, `cmd_preflight`, `_usable_preflight` (age, fingerprint and prompt-version
  refusals) and the exit codes.

F1 is the false-confidence case.

### F8 - Info / nit

- `benchmark_claude.py:523-529` prints `models[...].records[-1]`. For a turn that made no call,
  that record belongs to the previous turn. For a refused record it prints `None` rather than the
  refusal code.
- `ClaudeLedger.open_breaker` (`claude_bench.py:556-560`) has no rollback on error.
- `record_provider_usage` reads status outside its transaction (`:566`).
- The preflight's sync client (`benchmark_claude.py:322`) is never closed.
- The preflight still sends token counts after an earlier check has failed. This is harmless,
  but it is avoidable.

## Points verified as correct

- **Admission before sending:** the synthetic check, prompt shape, SHA approval, input-size
  limit, SDK-environment refusal and key read all happen before `reserve`. Network I/O starts only
  after a committed reservation. `make_client` is used only for the free Models and count-tokens
  endpoints.
- **Model mismatch:** this is detected at `message_start` before any text is yielded (tested and
  re-probed). The call is charged at its reservation and the breaker opens.
- **Generator close and cancellation:** `finally` always runs `close_call` once (there is no
  second close path), and an abandoned stream is charged at its full reservation. The
  `CancelScope(shield=True)` around a synchronous call has no effect, but it does no harm.
- **Credentials:** the explicit `api_key` and `base_url` mean the SDK skips `ANTHROPIC_API_KEY`,
  `ANTHROPIC_AUTH_TOKEN`, profiles and federation (`_client.py:229-246`). `open_telemetry=False`
  disables spans. Trace-context propagation stays at its default, but no span means nothing is
  injected. Exceptions are reduced to closed codes or class names. Artifacts from
  `record.__dict__` and `status.__dict__` contain no key.
- **Ledger:** the `CHECK` constraints repeat the owner ceilings, so a hand-edited ledger cannot
  exceed them. `committed` counts open reservations plus charges.
- **Preflight to run (TOCTOU):** the run requires a passing preflight under 12 hours old with the
  same prompt version and config fingerprint, and the stream refuses any prompt SHA that was not
  counted. The trust root is the local preflight file, which is acceptable for an owner-operated
  tool. The run does not re-check the attested credit balance; the per-call ledger cap still
  applies.

## Observation: a paid run already exists

The local, git-ignored ledger holds a completed paid run. I read it locally only.

| Item | Value |
|---|---|
| Run | `runs/20261028T182558Z-initial` |
| Calls | 51/51 |
| Settled | US$0.635484 |
| Charged at reservation | US$0 |
| Breaker | closed |
| Call outcomes | every call `end_turn`, no refusals, no anomalies |
| Usage | all `standard`/`global`, zero cache tokens |
| Console reconciliation | not done yet (`console usage n/a`) |

So F1 to F5 were latent in that run, as far as the content-free records show. F1 cannot be
excluded after the fact if a system proxy was active. The run predates this gate. This verdict
covers the code identity above, not that run's readiness for acceptance.

## Readiness

- **Next step:** bounded remediation of F1-F4. F5-F7 are recommended in the same pass. After that,
  a fresh independent recheck of the changed delta. Reuse the unchanged evidence above.
- **Before quoting the run's cost as final:** the owner should run `benchmark_claude.py reconcile`
  with the Console usage figure.
- **Change classification:**
  - Changed: evaluation tooling, secret-scanner rules, README.
  - Unchanged: runtime/API types, schema, connectors, configuration, business rules, mappings,
    runtime authentication and security, architecture, provider status, runtime behaviour.
- **Git:** nothing was committed, pushed or published by this gate. No ACRA or GoldTier readiness
  is implied.
