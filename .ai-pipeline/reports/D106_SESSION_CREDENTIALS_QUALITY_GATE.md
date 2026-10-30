# D-106 HR Session Credentials and Qualification Progress - Independent Quality Gate

Date: 2026-10-30
Reviewer: independent QG (did not author or remediate this content)
Verdict: **FAIL** (one bounded Medium credential-policy defect; the rest is Low/Info)

## Frozen reviewed content

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-session-credentials-20261030` |
| Branch | `feat/assistant-session-credentials` |
| HEAD / base | `582ad666031c` (all changes uncommitted; `apps/assistant/tests/test_session_credentials.py` intent-to-add) |
| Local `origin/main` ref | `1c6ec4fde9ed` (moved past base since branch creation; not integrated, not assessed here) |
| Identity `git diff --binary HEAD \| git hash-object --stdin` | start `8a3444c029c22043df51865473b1bcd840b697f8`, end `8a3444c029c22043df51865473b1bcd840b697f8` (unchanged) |
| Paths (15) | `apps/assistant/ai_assistant/{key_sources.py, anthropic_runtime.py, model_admin.py, remote_test.py, synthetic_boundary.json}`, `apps/assistant/scripts/qualify_model.py`, `apps/assistant/tests/{conftest.py, test_credentials.py, test_session_credentials.py}`, `apps/frontend/src/{aiAssistant.ts, pages/AiModelManagement.tsx, pages/AiModelManagement.test.tsx, pages/aiModels/aiModelConsole.css}`, `docs/decisions/DECISION_LOG.md`, `docs/PROJECT_STATE.md` |

Authority: D-106 (OWNER-APPROVED, `USER_AUTHORIZED_POC / PROJECT_DEFINED_PROVISIONAL`), read at the end of `docs/decisions/DECISION_LOG.md`.

## Evidence (this session, against the frozen identity)

| Check | Command (from `apps/assistant`, `PYTHONPATH` = worktree `apps/assistant`, venv python) | Result |
| --- | --- | --- |
| Import path | `python -c "import ai_assistant; print(ai_assistant.__file__)"` | worktree checkout confirmed |
| Credential tests | `pytest -p no:cacheprovider tests/test_session_credentials.py tests/test_credentials.py` | 44 passed (author reported 45; 44 is the count for these two files) |
| Targeted regression | `pytest -p no:cacheprovider` on test_session_credentials, test_credentials, test_claude_runtime, test_claude_console, test_claude_hr_spending, test_remote_test, test_spending_controls, test_d098_recovery, test_data_access_policy, test_model_management, test_phase_b_quality, test_model_factory | 640 collected, 640 passed, 0 failed |
| Lint/format | `ruff check --no-cache` / `ruff format --no-cache --check` on the 8 changed Python files | clean / 8 already formatted |
| Types | `mypy --strict ai_assistant scripts/qualify_model.py` | no issues in 47 source files |
| Boundary | `python scripts/build_synthetic_boundary.py --check` | "synthetic boundary is current" |
| Basis | `model_qualification.qualification_basis()[:12]` | `ab3786b82292` (matches D-106 Q1) |
| Frontend types | `npm run typecheck` (apps/frontend) | exit 0 |
| Frontend tests | `npx vitest run` | 69 files, 1259/1259 passed |
| Hygiene | `git diff --check HEAD`; trailing-whitespace grep and final-newline check on the new test file | clean; LF-terminated |
| Adversarial probe | scratchpad script (outside the repo): HR Anthropic key set, session check answers `None`, then `model_admin.qualification_handoff()` | payload `{}`, generations `{}`, store `held=True`: confirms M1 |

Not run: the full assistant suite (instructed not to; author's 2926-test run, with 14 known Windows `Errno 24` failures plus one test fixed afterwards, is not verified here), E2E/Playwright, any live provider call (none allowed; none made).

## Acceptance review

1. **Separate HR key entry (OpenRouter, Anthropic shared by Balanced/Fast)**: met. `ProviderKey` renders for both providers; the masked input shows even when a server/.env key exists (the old `CREDENTIAL_ENVIRONMENT_MANAGED` refusal is removed); Save for Session, Clear Session Key, Test Connection, source/status/expiry/fallback are shown. Routes `/credential` and `/credential/anthropic` are HR-only, Origin-checked, strict JSON, rate limited and audited with `profile_id` only (`model_admin.py:2083-2153`). Admin keys are refused (`anthropic_runtime.py:121-123`).
2. **Priority and session binding**: implemented in `key_sources.resolve_from` / `HrCredential.current` (`key_sources.py:138-165, 203-240`). Per-call resolution uses `max_age=0` for both Claude (`anthropic_runtime.py:709`) and GPT-OSS (`remote_test.py:328`), so the active model cannot keep using a revoked key (test `test_the_rm_cannot_keep_using_a_revoked_hr_key`). The session check uses the HR session's own stored cookie (`model_admin.py:1362-1377`; test asserts the cookie header). A key change rebuilds the adapter and re-runs the full preflight (Claude `_ready` marker compare; remote `_pinned`). **Exception: M1 (qualification launch falls through while the HR key is held).**
3. **Protection**: no key in responses, audit, logs or SQLite was found on inspection; tests assert the key is absent from overview/audit/budget/credential responses. The frontend keeps the key only in component state, clears it in `finally`, and uses no browser storage (grep: no `localStorage`/`sessionStorage`/`indexedDB` in the changed frontend files). Child process: no `env=`, key only through `stdin=PIPE`, written once then closed; on write failure the child is killed and waited (`model_admin.py:381-412`). The child validates size, JSON shape, provider names and key shape before storing (`qualify_model.py:34-50`).
4. **Qualification progress UI**: met. Spinner, a `<progress>` from server `done_turns/total_turns` (indeterminate without a total), provider, server stage (running / cancel requested), started, active model, final passed/failed/cancelled/interrupted/stopped with recovery text; it reuses the existing `RUNNING_REFRESH_MS` (3 s); no ETA. Cancellation, reservation and state logic unchanged.
5. **Preservation**: guardrails, D-094/D-095/D-104 admission paths, ledger/budget checks, provider authorization and the no-switch rule are untouched in the diff; boundary current; basis moves to `ab3786b82292` as recorded.

### Race review of `HrCredential.current`
The check runs outside the lock on a snapshot; the answer is applied only if `generation` is unchanged, otherwise the loop re-decides on the newer entry (test `test_a_check_racing_a_change_never_drops_the_newer_key`). A `True` answer returns the snapshot key, which equals the current key because the generation matched. Concurrent callers may duplicate checks, which is harmless. No defect found. `session=None` (trusted handoff) is reachable only from `scripts/qualify_model.py:49`; the only service caller, `set_credential`, always passes the request cookie and refuses with 401 when it is missing (`model_admin.py:2107-2112`). Every production caller of `key_sources.resolve`, `anthropic_runtime.resolve_key`, `HR_STORE` and `ANTHROPIC_STORE` was enumerated. Model calls use `max_age=0`. Views, preflight, connection tests and spending estimates use the 10 s reuse.

## Findings

| ID | Severity | Location | Finding | Required fix |
| --- | --- | --- | --- | --- |
| M1 | Medium (credential policy; blocks PASS) | `apps/assistant/ai_assistant/model_admin.py:923-936` (with `:381-412`, `:1648-1654`) | `qualification_handoff()` hands over only keys whose entry has `key is not None`. If an HR key is **held** (`unverified`, the backend cannot answer at the `max_age=0` check), it is silently left out: the payload is `{}` and generations are `{}`. The child inherits the service environment, so it resolves the **server** key. The supervisor has nothing to watch, so the run is never stopped. This breaks D-106 K2 ("If the backend cannot answer, the key is held back ... and nothing falls through to a server key"). It is reachable because the paid-start gate (`paid_estimate` -> `budget_status`) reuses a check up to 10 s old, while the handoff re-checks. A backend blip in that window starts a paid run on a different billing key than the one HR confirmed. The child's own preflight still enforces workspace, ledger and key limit, so the impact is bounded. Reproduced by probe. | Refuse the launch (for example `ProfileConfigError("CREDENTIAL_SESSION_UNVERIFIED")`, already mapped to `QUALIFICATION_UNAVAILABLE`) when any needed provider's entry is `held`. Add a test. |
| L1 | Low | `model_admin.py:923-936`, `:939-947` | The handoff passes **every** provider's HR key to every qualification, including local and other-provider runs. The supervisor then ends, for example, a local or GPT-OSS run with `CREDENTIAL_REVOKED` when an unrelated Anthropic key is cleared. This is over-sharing (least privilege) and causes unnecessary kills. | Hand over and watch only the key of the provider being qualified (`entry.deployment`). |
| L2 | Low | `apps/assistant/ai_assistant/remote_test.py:238-260` | The OpenRouter key-limit cache `_provider` is not keyed by key identity, unlike Claude's `_last` (QG L-2). It is cleared only on an explicit set/clear or when a model call notices a new key. When an HR session ends and the key is dropped automatically, the spending view and the paid-start estimate keep showing the previous HR key's own limit for the server key. Per-call preflight still enforces the real limit. | Store and compare `key_sources.identity(key)` in `_provider`, or forget it when `current()` drops a key. |
| L3 | Low (docs) | `docs/decisions/DECISION_LOG.md:1656` (K2) | K2 says the session is asked "before each ... connection test and qualification start". The connection test (`connection_check`/`preflight` -> `resolve_key` default) and the paid-start estimate reuse a check up to 10 s old. Only model calls and the stdin handoff use `max_age=0`. | Align the text, or pass `max_age=0` in those paths. |
| L4 | Low (docs) | `docs/decisions/DECISION_LOG.md:1665` | The residual-risk text says a revoked run "is closed like a cancelled one". The code closes it as `status=error`, `code=CREDENTIAL_REVOKED`, like `DEADLINE`. K5 also omits that the supervisor ends a run when the session merely cannot be checked (`handoff_revoked` treats `held` as revoked), so a transient backend outage kills a paid run. That is fail-closed, but undocumented in the decision. | Correct the wording and record the unverified case. |
| I1 | Info | `AiModelManagement.tsx:65, 777` | `REASON_TEXT.CREDENTIAL_MISSING` still says "Its server-side key is not set". `ANTHROPIC_KEY_CODES` omits `CREDENTIAL_SESSION_UNVERIFIED`, so the summary row shows generic text (the key card itself is correct). The OpenRouter refusal `CREDENTIAL_UNVERIFIED` has no dedicated text and falls back to a humanised code. | Optional wording. |
| I2 | Info | tests | No test covers the real `_launch_process` write-failure path (kill and wait), and no frontend test asserts that browser storage is untouched. Both behaviours were confirmed by inspection. | Optional. |
| I3 | Info | `aiModelConsole.css` | Under `prefers-reduced-motion` the spinner still rotates (only slower). | Optional. |

## Classification

- Current blocker: M1. It is a D-106 K2 fail-open in the qualification path, so it is a security/contract item and does not qualify for PASS WITH MINOR FIXES.
- Not blockers: L1-L4, I1-I3.
- Later sponsor/owner dependencies (unchanged): the paid Claude Balanced requalification on the merged basis, activation and Garden RM verification. Evidence class: Mock/Local only; nothing here is Live.

## Change declaration (observed)

API: new `/credential/anthropic` GET/PUT/DELETE; credential view gains `expires_at`, `verified_at`, `fallback`, status `unverified`, source `hr_session` (replaces `hr_memory`). Schema/SQLite: none. Connector/runtime: key resolution order and session binding; qualification child stdin handoff; new `CREDENTIAL_REVOKED` code. Configuration: none. Auth/security: yes (HR key entry is now allowed for both providers, with session binding). Business rules/mapping/architecture/provider status: unchanged. Qualification basis: `598cfe14753d` -> `ab3786b82292`.

## Readiness

Not ready for publication. Remediate M1 (recommended together with L1-L4) and run a fresh independent review of the corrected delta. Unchanged evidence (frontend 1259/1259, typecheck, boundary) may be reused if the frontend and boundary are untouched. Pre-PR check, owner publication authorisation and owner merge remain open. No commit, push or fix was made by this gate.
