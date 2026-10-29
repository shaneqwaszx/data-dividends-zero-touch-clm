# D-099 Option B: independent Quality Gate

Date: 2026-10-29. Reviewer: independent QG agent (did not author or remediate this change).
Read-only review; this report is the only file written. No staging, commit, push, network
call, paid call or `.env` read.

## Verdict: FAIL (one required bounded fix, M-1)

Everything else in scope was verified and is sound: the GPT-OSS/OpenRouter path is unchanged
for correctly configured ledgers, admission isolation holds, the Anthropic runtime fails closed
on every listed condition, F1 and F2 are fixed, the boundary diff is exactly the three
`code_vocabulary` words, the basis value reproduces, no secret is tracked, and no Live claim is
made. The FAIL is for M-1: the profile-isolation guarantee is enforced at reservation only, and
the Claude preflight writes verification state to a ledger *before* checking that it is the
Anthropic one. If the two ledger paths name the same file (a configuration error), a Claude
connection test marks GPT-OSS calls `verified` under Claude's in-band rule. That bypasses the
GPT-OSS generation-metadata verification (D-092 P4). The owner's approval explicitly excludes
any weakening of GPT-OSS protections, so this cannot pass as a minor fix even though it needs a
misconfiguration and the fix is small.

## Reviewed content (frozen identity)

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-sonnet-console-20261029` |
| Branch | `feat/assistant-claude-sonnet-console` (draft PR #130) |
| Reviewed commit | `778b4683f26b5c26e65f3e1b8a4e7215f0e0b6f2` (HEAD at review; clean status, no untracked files) |
| Reviewed tree | `fcdb0d6d149ba28f1c8cc1e8abec203acfe1c470` |
| Base of review diff | `541b10f` (PR #130 head before Option B); 2 commits: `badaace` (docs), `778b468` (implementation) |
| Paths | 23 files, +2,721/-135: the Anthropic adapter, profiles and new runtime, `budget.py`, `config.py`, `main.py`, `model_admin.py`, `model_catalog.py`, `model_qualification.py`, `synthetic_boundary.json`, `telemetry.py`, `assistant_eval/qualification.py`, `scripts/budget_ledger.py`, 4 test files, 3 docs, 3 `.ai-pipeline` reports/design |
| Frontend/backend | no file changed outside `apps/assistant`, `docs`, `.ai-pipeline` (D-100 isolation holds) |

## Evidence I collected (this session, offline, on the reviewed tree)

| Check | Result |
| --- | --- |
| `test_claude_runtime`, `test_claude_console`, `test_budget_ledger`, `test_budget_cli`, `test_budget_guard`, `test_budget_daily` | **215 passed** |
| `test_remote_test`, `test_reasoning_configurations`, `test_model_management`, `test_telemetry`, `test_phase_b_live` | **257 passed** |
| `test_model_factory`, `test_synthetic_eligibility`, `test_streaming_resources` | **203 passed** |
| Reviewer ad hoc tests (scratchpad only, not in the repo): the D-095 ticket path through `ClaudeTestModel` (single use, reaches the provider once, refused without a ticket or without D-095 mode); Admin, OAuth (`oat`) and session (`sid`) keys and a trailing newline refused | 4 passed |
| Reviewer ad hoc cross-ledger reproduction (M-1) | reproduced (see M-1) |
| `scripts/build_synthetic_boundary.py --check` | current; generator unchanged in the diff |
| Boundary diff vs `541b10f` | only `code_vocabulary` +`ant`,`usr`,`wrkspc`; nothing removed; `conversation_vocabulary`, `prompt_vocabulary`, company, documents, viewers, values, knowledge unchanged; `code_vocabulary` feeds only the system-message vocabulary (`synthetic_boundary.py:198`) |
| `qualification_basis()` | `e8d149ade8f8ec2506c8ab9ba58e58dc477d60dbefb58c6b39eeafe4503685bf` (matches the author) |
| `ruff check` / `ruff format --check` (16 touched .py) | clean |
| `mypy` (16 touched .py, cache outside repo) | 1 error, `tests/test_budget_ledger.py:572` unused `type: ignore`: pre-existing (`63cb662`), not introduced here |
| `scripts/check_secrets.py`; `git diff --check 541b10f 778b468` | pass; clean |

Not run: the full assistant suite (Windows stall risk, per the brief). The author's full-suite
figure (2,764 tests, 14 `Errno 24` failures) was taken **before** the last two edits, so it is
stale for this tree. I record it as unverified, not passing. The 14 focused modules above cover
every module this change touches.

## Findings

### M-1 (Medium, required): profile isolation is not enforced before ledger writes in verification paths

- `apps/assistant/ai_assistant/anthropic_runtime.py:296-310`: `check_ledger` opens the ledger
  named by `AI_ASSISTANT_ANTHROPIC_LEDGER_PATH`. It calls `ledger.recover()` and
  `verify_calls(ledger)` (lines 297-299), which write `verified`/`quarantined` and may open the
  breaker. Only then does it add the `ledger.profile` check (lines 306-310). `verify_calls`
  (lines 249-261) never checks the profile either.
- **Reproduced.** I created a GPT-OSS ledger with one settled, unverified OpenRouter call (the
  M1 "interrupted run" state). Then I ran `anthropic_runtime.preflight(network=False)` with the
  Anthropic ledger path set to that file. The report correctly fails `ledger.profile`, but the
  OpenRouter call is now `verified`. The GPT-OSS `verify_earlier_calls`
  (`remote_checks.py:423-442`) only looks at unverified calls, so that call never gets its
  OpenRouter generation-metadata check. It also counts towards a GPT-OSS G-8 `verified` total.
  The same write happens on an HR connection test, an activation probe and the qualification's
  connection check.
- **Reverse direction (fail closed, same root cause).** `BudgetLedger.verify` checks columns
  only, and `remote_checks.run_preflight` (`remote_checks.py:492-503`) has no profile check. A
  GPT-OSS preflight on an Anthropic-profile ledger would therefore report it "healthy" and run
  OpenRouter generation lookups on Claude calls (sending a content-free Claude message
  reference to OpenRouter), then quarantine them and open the Claude breaker.
  `budget.reserve` still refuses the GPT-OSS call (`refused_ledger`).
- **Operator writes.** The HR lifetime-cap endpoint (`model_admin.py:2033-2072`) acts on
  whatever file the GPT-OSS path names, without a profile check. So it could raise an
  Anthropic ledger above US$5.00 without `check_cap_change`. The Claude runtime would then refuse
  every call (`ledger.cap_within_ceiling`), so no money is at risk. The CLI does follow the
  ledger's own profile.
- **Precondition.** Both settings resolve to one file. The defaults differ
  (`data/budget/ledger.sqlite3` and `data/budget/anthropic_ledger.sqlite3`). The code clearly
  means to defend against this case (profile checks in `ClaudeTestModel.__init__`, in the
  preflight report and in `reserve`), but the preflight's refusal comes after its side effect.
- **Why it matters.** Brief focus #1/#2 and the owner's condition. C8 P-3 and the `budget.py`
  comment (lines 69-72) say neither provider's calls can be "counted in (or admitted by)" the
  other's ledger. Admission is true; verification state is not.
- **Bounded fix.** In `check_ledger`, check `status.profile_id == LEDGER_PROFILE_ID` right after
  `open` and before `recover`/`verify_calls`, and refuse otherwise. Also guard `verify_calls`
  itself (or `ClaudeTestModel.verify_now`). Make Claude `readiness` refuse when
  `anthropic_runtime.ledger_file(settings)` resolves to the same file as
  `remote_test.ledger_file(settings)`: this closes both directions without touching GPT-OSS
  code. Add a test that a Claude preflight on an OpenRouter ledger leaves its rows unchanged.

### L-1 (Low): connection-failure diagnosis does not know the Claude check names

`model_admin.py:782-807, 895-906`. `_BILLING_CHECKS`, `_CONFIGURATION_CHECKS` and
`_BUDGET_CHECKS` list only GPT-OSS check names. When a Claude qualification fails its
connection check with `ledger.reconciled_recently`, `ledger.profile`,
`ledger.cap_within_ceiling`, `anthropic.ready`, `anthropic.inference_key`,
`anthropic.workspace_matches` or `anthropic.model_available`, it is diagnosed as
`technical / PROVIDER_UNAVAILABLE / TEST_CONNECTION, retryable`. For a stale reconciliation it
should be `billing_uncertain / ESCALATE_OPERATOR`; for a workspace mismatch or a missing
attestation it should be `configuration / ESCALATE_IT`. HR is told the wrong cause and action.
This is not truthful status, but no spend or supersession follows, because the estimate gate
already refuses a stale reconciliation before a run starts.

### L-2 (Low): the last-preflight record is not tied to the key

`anthropic_runtime.py:383-427` and `524-526`. `_last` is kept process-wide and never cleared
when the key changes. GPT-OSS clears its counterpart on a key change (`forget_provider`,
`remote_test.py:392`). After a key rotation, the paid-qualification estimate can pass its
"provider checked" condition on the previous key's preflight. No unchecked call results: the
qualification process runs its own 24-hour connection check, and `ClaudeTestModel` re-preflights
on a key change before any call.

### L-3 (Low): test gaps on two stated prerequisites

- No repository test drives the D-095 ticket path through `ClaudeTestModel`. That is the F2
  claim of no double ticket consumption with admission re-checked in the adapter.
  `test_admission_is_decided_on_every_call` covers only the bare adapter's callable. My ad hoc
  tests show the behaviour is correct.
- No test covers verification isolation across ledgers (M-1).

### Info

- I-1: `ClaudeTestModel.stream` runs `_verify_after` (SQLite verification) synchronously in its
  `finally` on the event loop (`anthropic_runtime.py:730-734, 747-748`). GPT-OSS uses a
  background thread. The blocking is brief.
- I-2 (author-disclosed, accepted): the call-limit check and the reservation are separate
  transactions, so a narrow race could allow a 21st call while the money caps still hold. The
  existence of the `anthropic-workspace-id` header and the workspace-id format are unverified
  on the real API; if they are absent, every call fails closed with a protocol error and the
  breaker opens. Follow-up prompts with system lines after history are refused before
  reservation. HR labels for the new codes are deferred (D-100).
- I-3: the L4 live-marker guard allowlist gains exactly `anthropic_chat.py` and
  `anthropic_runtime.py`, and the OpenRouter entries are unchanged. I confirmed that
  `LIVE_NETWORK` is passed only by `ClaudeTestModel._build_inner`, and that the OpenRouter
  marker is refused by the Anthropic adapter (`require_offline_transport`). Owner
  acknowledgement is requested, as are the three vocabulary words.
- I-4: the CLI `status` output for OpenRouter ledgers gains two lines (`profile`,
  `last reconciled`). The change is additive; `set-cap` and `init` behave as before on
  OpenRouter ledgers (`expected=None`, OpenRouter profile).
- I-5: operator procedure. Reconciliation must use the workspace's **cumulative** Console cost.
  A monthly figure that resets would be refused (`provider usage cannot decrease`), which fails
  closed. The documents say "cumulative", which is accurate.

## Review focus results

1. **GPT-OSS protections.** No weakening in the correctly configured path (M-1 is the
   misconfiguration exception).
   - `budget.py`: `reserve(profile_id=…)` is an extra refusal; `BudgetedChatModel` passes the
     adapter's profile, and both OpenRouter adapters report `openrouter_gpt_oss_120b`.
   - `verify()` does not compare DDL, so ledgers created with the narrower CHECK still verify
     and work (tested).
   - `remote_test.py` and `remote_checks.py` are unchanged.
   - In `model_admin.py`, the GPT-OSS branches are untouched apart from routing by
     `deployment`. `sync_controls` skips Claude, and `_paid_call_uncertain()` defaults to the
     GPT-OSS ledger.
   - The `main.py` GPT-OSS notice strings are byte-identical, and `RemoteTestModel` has no
     `notices`, so it falls back to `REMOTE_NOTICES`.
2. **Ledger isolation.**
   - Admission: isolated (tested both directions, including the guarded Claude adapter on an
     OpenRouter ledger).
   - Settlement: isolated, because reservation ids are per ledger.
   - `ClaudeTestModel` refuses a non-Anthropic ledger at construction.
   - Verification and operator writes: **not isolated** (M-1).
3. **Anthropic runtime fails closed.** Verified: readiness (decision, interlock, development
   machine, exact attestations, `wrkspc_` id, limit 1..5,000,000, policy ceilings re-checked
   against `model_construct`).
   - Key: environment first, then `.env`. The first source with a value decides, and nothing
     falls through. Admin keys get `CREDENTIAL_ADMIN_REFUSED`; OAuth and session keys are
     invalid.
   - Reconciliation windows: 7 days for chat and the connection test; 24 hours for the paid
     estimate (`budget_status` default), the qualification process (`within_seconds=paid` for
     the model and its connection check), the activate/rollback probe (`change()`) and CLI
     raises. A reconciliation timestamp in the future is refused.
   - Cap: the ceiling is `min(US$5, workspace limit)`, and the cap must be above the opening
     usage. The daily cap is checked both in the preflight and inside the admission
     transaction. The call limit counts open calls.
   - Preflight reuse runs only after a passing network preflight, and is reset on a key change.
     In-band verification counts a call only when it is `settled` with no anomaly; anything
     else is quarantined and opens the breaker.
   - A prompt-shape refusal happens before reservation (tested: no reservation, no breaker).
4. **Adapter.**
   - F1: a second `message_start` raises `usage_repeated` with the cost dropped.
   - F2: admission is a per-call callable, and the runtime pops its own digest record, so the
     D-095 ticket is consumed once (in `_ready`). The mode is re-evaluated, although it is
     derived from immutable settings.
   - The live marker requires an attested workspace.
   - The workspace header is checked after the status and encoding checks and before any frame.
   - Thinking and signature deltas are skipped, and text is accepted only from text blocks.
   - The cost is `None` whenever any anomaly is present.
5. **Scope.** Claude goes through the same `main.py` path via `requires_synthetic_boundary`:
   the D-094 boundary, or D-095 eligibility only when `synthetic_eligibility.mode` holds
   (which needs the full GPT-OSS readiness), so it is never broader. A refusal or failure gives
   the case-data answer, and an unusable stored activation becomes *AI unavailable*
   (`REMOTE_PROFILE_IDS` includes the Claude ids). There is no automatic switch (tested: zero
   OpenRouter and baseline calls).
6. **Boundary.** Only `code_vocabulary` changed (+3); the generator is unchanged and the basis
   value matches.
7. **Secrets.**
   - No key-shaped literal is tracked: tests build the sentinel at run time, and the secret
     scan passes.
   - The key is never logged: refusals log reason words only, the preflight detail is
     "present (not shown)", HTTP errors log the class name only, and the credential view
     carries no marker.
   - Journey tests search the API and audit text for the sentinel.
   - No organisation Admin key path exists, and no `AI_ASSISTANT_*` settings field holds the
     key.
8. **Tests.** Broad and adversarial: 57 runtime cases, plus console cases and HR journeys.
   Gaps are noted in L-3. All the requested modules pass on the reviewed tree.
9. **Docs.** `DECISION_LOG` D-099 C6–C9, `AI_MODEL_CONFIGURATION` §13, `PROJECT_STATE` and the
   implementation report all state "not equivalent", the residual risks (C9), synthetic-only
   scope and development machines only. Provider status is Mock only, not activated, with no
   Live claim. The basis and the worst-case reservation (US$0.096134) are accurate. The
   exception is the P-3 wording, which overstates isolation until M-1 is fixed.

## Change classification (this diff)

| Area | Changed? |
| --- | --- |
| API/type | yes: catalogue status `selectable` for Claude; new spending view and refusal codes (assistant service only) |
| Schema | the ledger CHECK set gains a profile for new ledgers; existing ledgers are unchanged; no Mongo change |
| Connector | yes: Anthropic Messages API adapter can be composed behind the D-099 gate (Mock-evidenced only) |
| Configuration | yes: seven `AI_ASSISTANT_ANTHROPIC_*` settings |
| Business rule / mapping | no CLM business rule or ACRA/GoldTier mapping change |
| Auth/security | key handling and attestations for Claude; RBAC unchanged |
| Architecture | a second ledger and a provider runtime; no new persistence owner for case data |
| Provider status | Anthropic is Mock only; GPT-OSS is unchanged |
| Runtime behaviour | none unless D-099 and every safeguard are configured; not activated |

## Readiness

Governance/publication only: **not ready**. M-1 must be remediated in a bounded run, with a
re-review of the corrected delta. L-1 to L-3 are recommended in the same run and are not
blocking on their own. The stale full-suite evidence must be refreshed on the integrated
candidate. Owner acknowledgements are still required for the three vocabulary words and the
L4 allowlist extension. Paid inference, paid qualification, activation, push and merge remain
unauthorised.
