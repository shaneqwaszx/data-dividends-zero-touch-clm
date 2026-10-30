# D-106 HR Session Credentials and Qualification Progress - Independent Quality Gate, Round 2

Date: 2026-10-30
Reviewer: independent QG, round 2. I did not author or remediate this content, and I did not perform round 1.
Verdict: **PASS**. Two non-blocking residuals are recorded below: one Low and one Info. Neither is a required fix.

## Frozen reviewed content

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-session-credentials-int-20261030` |
| Branch | `feat/assistant-session-credentials-int` |
| HEAD = `origin/main` | `1c6ec4fde9ed` (includes merged PR #138) |
| State | The candidate is entirely staged and uncommitted (15 paths). `git diff --name-only` (unstaged) returns 0 paths. The only untracked file is the round 1 report. |
| Identity `git diff --cached --binary origin/main \| git hash-object --stdin` | start `1c93362ab40bcd5d72ce28dab3b318ae2e9c960b`, end `1c93362ab40bcd5d72ce28dab3b318ae2e9c960b` (unchanged) |
| Paths (15) | `apps/assistant/ai_assistant/{anthropic_runtime.py, key_sources.py, model_admin.py, remote_test.py, synthetic_boundary.json}`, `apps/assistant/scripts/qualify_model.py`, `apps/assistant/tests/{conftest.py, test_credentials.py, test_session_credentials.py (A)}`, `apps/frontend/src/{aiAssistant.ts, pages/AiModelManagement.tsx, pages/AiModelManagement.test.tsx, pages/aiModels/aiModelConsole.css}`, `docs/PROJECT_STATE.md`, `docs/decisions/DECISION_LOG.md` |

Authority: D-106 (OWNER-APPROVED, `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`), read at the end of `docs/decisions/DECISION_LOG.md`. Round 1 report: `.ai-pipeline/reports/D106_SESSION_CREDENTIALS_QUALITY_GATE.md` (FAIL on M1).

## Evidence (this session, against the frozen identity)

All Python commands ran from `apps/assistant` with `PYTHONPATH` set to this worktree's `apps/assistant`, `PYTHONDONTWRITEBYTECODE=1`, the repo venv, and `-p no:cacheprovider`. JUnit output went to the scratchpad.

| Check | Result |
| --- | --- |
| Import path | `ai_assistant` resolves to this worktree |
| Targeted D-106 / model suites: test_session_credentials, test_credentials, test_claude_runtime, test_claude_console, test_claude_hr_spending, test_claude_multi_turn, test_remote_test, test_spending_controls, test_d098_recovery, test_data_access_policy, test_model_management, test_model_factory, test_synthetic_eligibility, test_phase_b_quality | **774 tests, 0 failures, 0 errors, 0 skipped** (exit 0) |
| #138 interaction suites: test_answer_records, test_conversations, test_knowledge_review, test_knowledge_review_recheck, test_knowledge_review_safety, test_knowledge_review_scope, test_knowledge_single_reviewer | **204 tests, 0 failures** (exit 0) |
| `ruff check --no-cache` on the 8 changed Python files | All checks passed |
| `ruff format --no-cache --check` on the 8 changed Python files | 8 already formatted |
| `ruff format --check .` (whole `apps/assistant`) | 4 would be reformatted: `ai_assistant/main.py`, `ai_assistant/support_chat.py`, `tests/test_conversations.py`, `tests/test_knowledge_review.py`. None is in the candidate (`git diff --cached --quiet origin/main` on them confirms they are identical to main), and each `origin/main` blob also fails `ruff format --check` (exit 1). This is pre-existing from #138 and not attributable to this change. |
| `mypy --strict ai_assistant scripts/qualify_model.py` | no issues in 48 source files |
| `python scripts/build_synthetic_boundary.py --check` | "synthetic boundary is current" |
| `model_qualification.qualification_basis()[:12]` | `7e386b8a69e1` (matches D-106 Q1 and PROJECT_STATE) |
| Frontend `npm run typecheck` | exit 0 |
| Frontend `npx vitest run` | **69 files, 1267/1267 passed** (round 1 had 1259; the remediation added 8) |
| Hygiene | `git diff --cached --check origin/main` clean. The new test file is part of the staged diff. |
| Docs integrity | For `docs/PROJECT_STATE.md` and `docs/decisions/DECISION_LOG.md`, main's blob is an exact byte prefix of the staged blob (104591 and 215578 bytes). The appended blocks contain no CR, so main's mixed EOL is preserved untouched. |
| #138 preservation | In `aiAssistant.ts`, every removed line in the staged diff vs `origin/main` is a D-106 line: the two credential messages and the credential type/fetchers. DECISION_LOG is additions only. In the boundary, the only removals are `command` and `inherited`, and the builder `--check` passes on the merged tree. The #138 suites pass (204/204). |
| Adversarial probe | I wrote a scratchpad script outside the repo. It ran offline, with no network or provider calls. Results are under "Remediation verification". |

Not run: the full assistant suite (instructed; the author is running it), E2E/Playwright, `pre_pr_check.py` (needs a commit), and any live provider call (none allowed, none made).

## Remediation verification

| R1 finding | Status | Evidence |
| --- | --- | --- |
| **M1** held key let a qualification start on the server key | **Fixed** | Start route `model_admin.py:1779-1782`: `handoff_provider(entry)` plus `hr_store(provider).current(max_age=0).held` refuses with `CREDENTIAL_SESSION_UNVERIFIED` before `paid_estimate`, the manifest checks and reservation. Launch `model_admin.py:387-389` -> `qualification_handoff` (`:940-955`) re-checks at `max_age=0` and raises on `held`. The launch failure is recorded and audited under that code (`:1834-1855`), and `handoff_providers` is popped on failure. `HrCredential.current` sets `_verified_at = None` on an unanswerable check (`key_sources.py:166-168`). Probe P1: after an earlier successful check, one unanswerable check gives `held=True`; a later default-age (10 s) view is still held (the earlier check does not vouch for it); the handoff is refused with `CREDENTIAL_SESSION_UNVERIFIED`. Tests: `test_a_held_back_key_refuses_the_handoff_never_a_server_key`, `test_a_held_back_key_refuses_the_qualification_start` (no launch), `test_the_launch_refuses_a_key_held_after_the_start_checks` (start check passes, launch-time check held -> 409 + audit). |
| L1 every provider's key handed to every run | Fixed | `handoff_provider`: anthropic deployment -> `anthropic`; other `source=="code"` (deployments `remote`/`openrouter`, `model_catalog.py`) -> `openrouter`; `file` (local) -> None, which hands over `b"{}"`. Only that provider's generation is watched. Probe P3 and test `test_only_the_qualified_providers_key_is_handed_over_and_watched`. |
| L2 OpenRouter key-limit reading not tied to its key | Fixed for the reported case; narrow residual race (see L2-R) | `_remember_provider(..., identity)` (`remote_test.py:233`), and `budget_status` drops another key's reading (`:510-517`). Test `test_a_key_limit_reading_holds_for_its_key_only`. |
| L3 / L4 DECISION_LOG wording | Fixed | K2 now says model calls and qualification launches check fresh, and that views, the connection test and the paid-start estimate reuse a check for up to 10 s. This matches the code: the start route itself checks at `max_age=0` first. K5 records `error` / `CREDENTIAL_REVOKED` and the "cannot be checked" kill. This matches `supervise` (`model_admin.py:1667-1673`, kill then `finish_qualification("error", ended)`). The residual-risk text matches. |
| I1 stale frontend texts | Fixed (one Info residual, I1-R) | `CREDENTIAL_MISSING` text updated; `CREDENTIAL_SESSION_UNVERIFIED` texts added for both providers and to `ANTHROPIC_KEY_CODES` (`AiModelManagement.tsx:66,108,778`); `CREDENTIAL_REVOKED` cause text added. |
| I2 missing tests | Fixed | `test_a_failed_handoff_write_ends_the_process` (kill + wait, no handoff recorded), plus the M1/L1/L2 tests above. |
| I3 reduced motion | Fixed | `aiModelConsole.css`: `@media (prefers-reduced-motion: reduce) { .console-spinner { animation: none; ... } }`. |

### New race / bypass review of the remediation
- **Start check passes, session ends before launch** (probe P2): the handoff gets `entry.key is None, held False`, so the payload is `{}` and the child resolves the server key. D-106 allows this ("only a session that has ended releases the next source"). It is still gated by the child's own full preflight (workspace / usage reconciliation / key limit / ledger). This is not a bypass.
- **Start check passes, check is unanswerable at launch**: refused and recorded (test above). A key **set** between the start and the launch is handed over with its generation and watched. This is correct.
- **Concurrent `current()` callers**: answers apply only when `generation` is unchanged. A `None` answer clears `verified_at`, so a concurrent stale `True` can at most re-vouch for the same generation, which was itself just verified. This is harmless.
- **`session=None` trusted path**: still reachable only from `scripts/qualify_model.py` (`take_handoff`). The service's `set_credential` always passes the request cookie or refuses with 401.
- **Supervisor**: `handoff_revoked` treats held, dropped or replaced as revoked. The run is killed and recorded as `CREDENTIAL_REVOKED`, which is fail-closed. A supervisor exception still kills the run (`SUPERVISOR_FAILED`).
- **Child**: no `env=` (it inherits the service env; `.env` is never copied into it), the key arrives only on stdin, and the payload is size-, JSON- and shape-validated before storage.

### Round 1 "confirmed sound" items, rechecked
- The order and session binding are unchanged in substance. Per-call `max_age=0` remains for Claude (`anthropic_runtime.py:709`) and GPT-OSS (`remote_test.py:330`).
- The session check uses the entering HR session's cookie (`hr_session_live`, `model_admin.py:1381-1396`). 401/403/404 drop the key. Other errors and unexpected replies hold it.
- Credential routes remain HR-only, Origin-checked, strict-JSON and rate limited. They are audited with `profile_id` = provider only. Admin keys are refused.
- No browser storage in the changed frontend files (grep). No added log line carries key material (grep of added `log.`/`print(` lines).
- Guardrails, D-094/D-095/D-104 admission, ledger/budget checks, provider authorization and the no-auto-switch rule are untouched in the diff.

## Findings

| ID | Severity | Location | Finding | Disposition |
| --- | --- | --- | --- | --- |
| L2-R | Low (display/estimate only; non-blocking) | `apps/assistant/ai_assistant/remote_test.py:233` | The reading is tagged by resolving the key **again after** `run_preflight` returns, not with the key the account client actually used. If the key changes while a preflight is in flight (HR set/clear, or the session drops), key A's limit reading is tagged with key B's identity. `set_credential`'s `forget_provider()` runs before the stale write, so it does not help. Reproduced by probe P4 ("reading of key A tagged as: B (new key)"). Claude's equivalent (`anthropic_runtime.py:443,459`) resolves once and is not affected. Impact: the spending view and the paid-start estimate may show the previous key's own limit until the next preflight. Every model call's per-call preflight still enforces the real key's limit. | Optional: resolve the key once before `run_preflight` and pass that identity. Not required for PASS. |
| I1-R | Info | `apps/assistant/ai_assistant/model_factory.py:99-103`; `apps/frontend/src/pages/AiModelManagement.tsx:65` | A held OpenRouter session key makes `resolve_remote_credential` refuse with `CREDENTIAL_MISSING`, whose text now reads "no session key was entered and the server has none". In that case the text is misleading. The Providers key card itself correctly shows "Session Not Verified" and the reason. The refusal stays fail-closed. | Optional wording or code split. |

There are no Critical, High or Medium findings.

## Classification

- Current blockers: none. M1 is fixed and verified by code inspection, three tests and an independent probe.
- Non-blocking residuals: L2-R and I1-R.
- Later owner dependencies (unchanged): owner commit/publication authorisation, `pre_pr_check.py` on the commit, owner merge, then the separately authorised Claude Balanced technical qualification on basis `7e386b8a69e1`, activation and a Garden RM verification. Evidence class: Mock/Local only. Nothing here is Live.

## Change declaration (observed)

- API: `/credential/anthropic` GET/PUT/DELETE; the credential view adds `expires_at`, `verified_at`, `fallback`, status `unverified` and source `hr_session` (which replaces `hr_memory`); new refusal `CREDENTIAL_SESSION_UNVERIFIED` (start/launch); new run code `CREDENTIAL_REVOKED`; Claude budget view adds `credential`.
- Schema/SQLite: none.
- Connector/runtime: key order, session binding, and the stdin-only handoff of the qualified provider's key.
- Configuration: none.
- Auth/security: yes (HR key entry for both providers, bound to the session).
- Business rules, mapping, architecture and provider status: unchanged.
- Qualification basis: `2c9d72cf0ae4` -> `7e386b8a69e1`.

## Readiness

The frozen identity `1c93362ab40bcd5d72ce28dab3b318ae2e9c960b` passes the independent gate. Any change to the staged content needs a fresh review of the changed delta. This gate made no commit, push, stage or fix. Publication still requires the owner's authorisation and `pre_pr_check.py` on the committed state.
