# D-099 Option B: independent Quality Gate, round 2 (remediation re-review)

Date: 2026-10-29. Reviewer: fresh independent QG agent. I did not write or remediate this
change. This was a read-only review and this report is the only file I wrote. I did not stage,
commit or push anything, made no network or paid call, and did not read any `.env` file.

## Verdict: PASS WITH FINDINGS

- **M-1 is resolved.** Neither provider's preflight can now write verification state
  (`verified`/`quarantined`) to the other provider's ledger. Neither can run the other's
  verification rules against it. The HR lifetime-cap endpoint refuses the Anthropic ledger.
  Claude readiness refuses when both ledger paths name the same file.
- **L-1, L-2 and L-3 are resolved.**
- **No OpenRouter/GPT-OSS protection is weakened.** Every GPT-OSS change only adds a refusal.
- **One new Low finding (L-4), documentation accuracy.** The code comments, DECISION_LOG C8 P-3,
  report §4a and two test names say the other provider's ledger is "never recovered". That is
  wrong: `BudgetLedger.open()` itself runs `recover()` before the profile is read. The effect
  only fails closed, uses the same provider-neutral lease rule, and verifies nothing. It is not
  a GPT-OSS weakening, but the claim is broader than the code.

## Reviewed content (frozen identity)

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029` |
| Branch | `feat/assistant-claude-sonnet-console` (draft PR #130) |
| Reviewed commit | `6196c20ab527889df10e0601a2e891f8e1f70110` (HEAD; clean status before this report) |
| Reviewed tree | `d4e74b5a28a81c6ffad1b9fc806a83ad06082690` |
| Remediation delta | `git diff 778b468 6196c20`: 9 files, +459/-15. `8b902d3` adds only the round-1 report (241 lines). `6196c20` changes `anthropic_runtime.py`, `model_admin.py`, `remote_checks.py`, `tests/test_claude_runtime.py`, DECISION_LOG, AI_MODEL_CONFIGURATION, PROJECT_STATE and the implementation report |
| Scope | No path outside `apps/assistant`, `docs` or `.ai-pipeline` changed since `541b10f` |

## Prior findings

| Finding | Status | Verification |
| --- | --- | --- |
| **M-1** (Medium): profile isolation not enforced before verification writes | **Resolved** (see L-4 for the recovery wording) | Details below |
| **L-1** (Low): Claude check names misdiagnosed | **Resolved** | Details below |
| **L-2** (Low): the last-preflight record is not tied to the key | **Resolved** | Details below |
| **L-3** (Low): test gaps (D-095 ticket path, cross-ledger isolation) | **Resolved** | Details below |

**M-1, what changed and how I checked it**

- `anthropic_runtime.check_ledger` (`anthropic_runtime.py:302-315`) reads `profile_id` straight
  after `open`. On a mismatch it records the `ledger.profile` failure and returns before
  `recover()` and `verify_calls()`.
- `verify_calls` itself raises `LedgerError` on a non-Anthropic ledger (`:257-259`). This also
  covers `ClaudeTestModel.verify_now`/`_verify_after` (`:730`).
- `readiness` returns `LEDGER_PATH_SHARED` when `ledger_file(settings).resolve() ==
  model_factory.ledger_path(settings).resolve()` (`:185-187`).
  - The comparison is equivalent to `remote_test.ledger_file`, because `remote_settings` does
    not touch `budget_ledger_path`.
  - `preflight` calls `readiness` before it opens any ledger (`:417-420`), so a shared file is
    never opened by the Claude path.
- GPT-OSS `run_preflight` (`remote_checks.py:493-496`) refuses a non-OpenRouter ledger before
  `recover()` and `verify_earlier_calls`. The result is `ledger.healthy` refused with
  `LEDGER_PROFILE_MISMATCH`, so no OpenRouter generation lookups run on Claude calls.
- The HR lifetime-cap endpoint (`model_admin.py:2042-2049`) refuses a non-OpenRouter ledger with
  `LEDGER_UNAVAILABLE`, audited, before any range, confirmation or `set_cap` logic.
- Tests cover both directions, the shared path and the HR cap. Together they reproduce the
  round-1 failure scenario (OpenRouter ledger, one settled unverified call, Claude preflight):
  - the call stays unverified;
  - the breaker stays closed;
  - no request is made;
  - `verify_calls` raises.

**L-1**

- `_BILLING_CHECKS` gains `ledger.profile` and `ledger.reconciled_recently`.
- `_CONFIGURATION_CHECKS` gains `anthropic.ready`, `anthropic.inference_key`,
  `anthropic.workspace_matches`, `anthropic.model_available` and `ledger.cap_within_ceiling`
  (`model_admin.py:788-816`).
- No GPT-OSS check emits any of these names (I grepped all emitters), so GPT-OSS diagnosis is
  unchanged.
- A parametrised test covers six names, including `anthropic.models_reachable`, which is still
  classed as technical.

**L-2**

- `_last` now records `key=key_sources.identity(key)`, a process-local HMAC (`:436-443`).
- `budget_status` discards a record from a different key or when no key is present (`:488-489`),
  so `PROVIDER_LIMIT_NOT_CHECKED` applies.
- `ClaudeTestModel` clears `_last` whenever it rebuilds for a new key marker (`:695-696`). It
  also clears it on the first build, which is conservative: its own network preflight
  repopulates it.
- A test covers key rotation.

**L-3**

- New test `test_a_d095_ticket_admits_its_messages_once_and_only_in_development_mode` runs the
  ticket path end to end through `ClaudeTestModel`:
  - the ticket admits once;
  - a second use is `budget_refused` with no extra POST;
  - a ticket outside D-095 mode sends nothing.
- Isolation tests were added in both directions, plus the shared-path, HR-cap, key-tied
  preflight and diagnosis tests.

## New findings

### L-4 (Low, documentation accuracy): "never recovered" is not true; `BudgetLedger.open` recovers before the profile is read

- **Where.** `apps/assistant/ai_assistant/budget.py:476-486`: `BudgetLedger.open()` runs
  `ledger.verify()` and then `ledger.recover()`. The new profile checks all come after an
  `open()`:
  - `anthropic_runtime.py:303-304`, check at `:308-315`;
  - `remote_checks.py:493-496`;
  - `model_admin.py:2042-2046`.
- **Claims that overstate this:**
  - `anthropic_runtime.py:308`: "another provider's ledger is never recovered or verified";
  - `remote_checks.py:494`: "never recovered or verified here";
  - DECISION_LOG D-099 C8 P-3 (`docs/decisions/DECISION_LOG.md:1501`): "neither provider's
    preflight recovers or verifies the other's ledger";
  - `D099_OPTION_B_IMPLEMENTATION.md` §4a: "checks the ledger profile before
    `recover()`/`verify_calls()`" and "refuses a non-OpenRouter ledger before recovering or
    verifying it";
  - test names `test_a_claude_preflight_never_recovers_or_verifies_the_openrouter_ledger` and
    `test_a_gpt_oss_preflight_never_recovers_or_verifies_the_anthropic_ledger`. Both tests use
    an already settled call, so they never exercise recovery.
- **Reproduced (ad hoc, scratchpad only).**
  - Setup: an OpenRouter-profile ledger at the Claude ledger path (a different file from the
    GPT-OSS path, so readiness passes), holding one open call whose lease expired an hour ago.
  - I then ran `anthropic_runtime.preflight(settings, network=False)`.
  - The report correctly fails only `ledger.profile`.
  - However, the call is now `abandoned` and charged its full reservation, and the breaker is
    open with code `abandoned_call`.
  - The GPT-OSS preflight and the HR cap endpoint follow the same pattern.
- **Why this is Low, not Medium.**
  - `_abandon_expired` is provider-neutral lease housekeeping. It only charges in full and opens
    the breaker, which fails closed, and it never writes `verified`.
  - It is the same thing the owning provider's next `open()` or `reserve()` does: `reserve`
    calls `_abandon_expired` before its own profile check (`budget.py:718` and `:729`).
  - A live lease is untouched.
  - It needs a misconfiguration, and the same-file case is already refused by readiness first.
  - No OpenRouter/GPT-OSS protection is weakened. The M-1 harm (cross-provider verification
    state) is closed.
- **The problem is the wording.** It records a guarantee the code does not provide, in a
  governance record (C8) that the owner relies on.
- **Bounded fix, either one:**
  - (a) reword the comments, C8 P-3, §4a and the two test names to say "never verified or
    quarantined under the other provider's rules (generic lease expiry still applies on open)";
    or
  - (b) read the profile through a non-recovering handle (`BudgetLedger(path)` plus `verify()`,
    as `calls_used` already does) before `open()` in the three places, and add an
    expired-lease test.
- Either change alters reviewed content and needs a fresh narrow review.

### Info

- **I-1.** AI_MODEL_CONFIGURATION §13 and PROJECT_STATE only update the basis. Neither tells
  the operator that the two ledger paths must differ (`LEDGER_PATH_SHARED`). This is not
  inaccurate, only incomplete. C8 and §4a do record it.
- **I-2.** `Path.resolve()` in `readiness` raises `ValueError` for a path containing NUL, so a
  NUL in the configured path would raise in readiness rather than return a refusal code. Before
  this change, such a path failed closed later as `LEDGER_MISSING`. A process environment
  cannot carry NUL, so this is contrived.
- **I-3.** `LEDGER_PATH_SHARED` compares resolved paths. A hard link or an alias that
  `resolve()` does not canonicalise is not detected. In that case the new profile checks still
  stop verification writes in both directions (residual effect as in L-4).
- **I-4.** A Claude failure on `ledger.daily_room_for_one_call` is diagnosed `budget /
  REVIEW_SPENDING, retryable`. HR spending controls do not apply to Claude (P-5), but waiting
  for the daily reset does resolve it. This existed before and was not part of round-1 L-1.
- **I-5.** Round-1 Info items I-1 to I-5 (synchronous `_verify_after` in `stream`, the
  call-limit race, the unverified real-API workspace header, owner acknowledgement of the three
  words and the L4 allowlist, CLI status lines, the cumulative reconciliation procedure) are
  unchanged by this delta. The owner acknowledgements are still outstanding.

## OpenRouter/GPT-OSS protections

The delta only adds refusals. No GPT-OSS check, cap, verification, breaker or key rule is
removed, relaxed or bypassed.

- **`remote_checks.run_preflight`:** an extra refusal on a non-OpenRouter ledger. A
  correctly configured OpenRouter ledger behaves exactly as before, because `profile_id` is a
  required column set at `initialise`, and pre-D-099 ledgers carry `openrouter_gpt_oss_120b`.
- **HR lifetime-cap endpoint:** an extra refusal. All existing checks (range,
  `CONTROLS_CONFLICT`, confirmation, `RECONCILIATION_REQUIRED`, in-transaction `expected`) are
  unchanged and still run.
- **`_BILLING_CHECKS` and `_CONFIGURATION_CHECKS`:** these only gain names that GPT-OSS never
  emits.
- **Claude-only code:** `readiness` and `LEDGER_PATH_SHARED` live in Claude code. GPT-OSS
  readiness and model building are unchanged.
- **Tests:** the existing GPT-OSS suites pass: `test_remote_test`, `test_spending_controls`,
  `test_d098_recovery`, `test_model_management`, `test_openrouter_adapter` and
  `test_budget_ledger`.

## Boundary and basis (re-confirmed on this tree)

- **Boundary.** Diff `git diff 541b10f 6196c20 -- apps/assistant/ai_assistant/synthetic_boundary.json`:
  +3/-0. A section-level JSON comparison shows only `code_vocabulary` changed, adding exactly
  `ant`, `usr` and `wrkspc`. Nothing was removed, no other key changed, and the remediation
  delta does not touch the file. `scripts/build_synthetic_boundary.py --check` reports
  "synthetic boundary is current".
- **Basis.** `model_qualification.qualification_basis()` gives
  `72b681dc85e83ee435a07b7e35cb7f6e6b5e4a03b65ffaf2d0eb428408b9b30e`, which matches the author.
  DECISION_LOG C8, AI_MODEL_CONFIGURATION §13, PROJECT_STATE and §4a all cite `72b681dc85e8…`.
  §4 marks `e8d149ade8f8…` as superseded.

## Docs

| Document | Status |
| --- | --- |
| DECISION_LOG C8 | Accurately records the profile-first preflights, the HR cap restriction, `LEDGER_PATH_SHARED` and the new basis. The exception is the "recovers" wording (L-4) |
| AI_MODEL_CONFIGURATION §13 and PROJECT_STATE | Basis updated, with no new isolation claim; accurate (I-1) |
| §4a | Accurate on M-1, L-1, L-2 and L-3, except the "before recovering" wording (L-4). Its figure of 815 passed is the author's own and covers more modules than I ran; I did not reproduce it |

None of these documents claims Live or provider status. Paid use, activation, push and merge
are still unauthorised.

## Evidence I ran (this session, offline, reviewed tree)

| Check | Result |
| --- | --- |
| `pytest`, run from `apps/assistant` with `PYTHONPATH=.` (conftest blocks sockets), on the nine modules in the brief (`test_claude_runtime`, `test_claude_console`, `test_remote_test`, `test_spending_controls`, `test_d098_recovery`, `test_model_management`, `test_synthetic_eligibility`, `test_openrouter_adapter`, `test_budget_ledger`) | **568 passed, 0 failed, 0 errors, 0 skipped** (junit total 568; 294 s; exit 0) |
| `ruff check` (4 changed .py) | All checks passed |
| `ruff format --check` (4 changed .py) | 4 files already formatted |
| `mypy` (4 changed .py, cache in scratchpad) | Success: no issues found in 4 source files |
| `scripts/check_secrets.py` | passed |
| `git diff --check 778b468 6196c20` | clean |
| EOL check | `--stat` equals `--ignore-cr-at-eol` (9 files, +459/-15) |
| Boundary section diff vs `541b10f`; `build_synthetic_boundary.py --check` | `code_vocabulary` +`ant`,`usr`,`wrkspc` only; current |
| `qualification_basis()` | `72b681dc85e83ee435a07b7e35cb7f6e6b5e4a03b65ffaf2d0eb428408b9b30e` |
| Ad hoc expired-lease cross-ledger check (scratchpad script) | Reproduces L-4: the call is abandoned and the breaker opens (`abandoned_call`); only `ledger.profile` fails |

**Not run:** the whole assistant suite (excluded by the brief because of the Windows stall
risk). Any full-suite figure on this tree is the author's, not mine.

## Change classification (remediation delta)

| Area | Changed? |
| --- | --- |
| API/type | No new endpoint or field. A new readiness code, `LEDGER_PATH_SHARED`. The HR cap endpoint returns its existing `LEDGER_UNAVAILABLE` for an Anthropic ledger |
| Schema | No |
| Connector | No |
| Configuration | No new settings. Equal ledger paths are now refused for Claude |
| Business rule / mapping | No |
| Auth/security | Additive ledger-isolation refusals. RBAC is unchanged |
| Architecture | No |
| Provider status | Unchanged: Anthropic Mock only, GPT-OSS unchanged, no Live claim |
| Runtime behaviour | Refusals only, under misconfiguration. The correctly configured paths are unchanged |

## Readiness

The remediation closes M-1 and L-1 to L-3 without weakening GPT-OSS. L-4 is a non-blocking,
documentation-accuracy finding that I recommend correcting, either by rewording or with the
small non-recovering read, in a bounded run with a fresh narrow review. Alternatively the owner
can record it as accepted.

These items remain open:

- the owner acknowledgements (three vocabulary words, the L4 allowlist extension);
- the integrated full-suite evidence;
- `pre_pr_check.py` on the committed candidate.

Paid inference, paid qualification, activation, push and merge remain unauthorised.
