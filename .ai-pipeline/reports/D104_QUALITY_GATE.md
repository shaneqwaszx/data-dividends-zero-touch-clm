# D-104 Data Access Policy - Independent Quality Gate

Date: 2026-10-30. Stage 3 independent review (reviewer did not author or remediate the
content). Read-only apart from this report. No network, no paid call, no `.env` read, no Git
mutation.

## 1. Frozen reviewed identity

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-data-access-policy-20261030` |
| Branch | `feat/assistant-data-access-policy` (all changes uncommitted) |
| HEAD = base = `origin/main` | `0c6a6325e8ad9bdc650c72824124a4d0f2fc863f` |
| Reviewed paths (12) | `.ai-pipeline/reports/D104_DATA_ACCESS_POLICY.md`, `apps/assistant/ai_assistant/data_access.py` (new), `apps/assistant/ai_assistant/model_admin.py`, `apps/assistant/ai_assistant/model_admin_store.py`, `apps/assistant/tests/test_data_access_policy.py` (new), `apps/frontend/src/aiAssistant.ts`, `apps/frontend/src/pages/AiModelManagement.test.tsx`, `apps/frontend/src/pages/AiModelManagement.tsx`, `apps/frontend/src/pages/aiModels/ConsoleShell.tsx`, `docs/PROJECT_STATE.md`, `docs/decisions/DECISION_LOG.md`, `docs/integration/AI_MODEL_CONFIGURATION.md` |
| Content-id at start | `b6440a5f999c8cf6b8830f3443724ac7b3d87ce0e8b3cc9cf49e10e6b99bace8` |
| Content-id at end (before this report was written) | `b6440a5f999c8cf6b8830f3443724ac7b3d87ce0e8b3cc9cf49e10e6b99bace8` (unchanged) |

Content-id method: sha256 over sorted `{git diff --name-only} U {git ls-files --others
--exclude-standard}`, each `path + \0 + content(CRLF->LF) + \0`. This report file is not part
of the reviewed content; adding it changes the untracked set, so recompute excluding it.

## 2. Checks run (this session, frozen content)

| Check | Result |
| --- | --- |
| `pytest tests/test_data_access_policy.py` | 24 passed |
| Focused regression: test_data_access_policy, test_claude_console, test_claude_hr_spending, test_claude_runtime, test_guardrails, test_guardrails_dropped, test_model_management, test_remote_test, test_spending_controls, test_streaming_resources, test_synthetic_eligibility, test_warm_up_security | 746 collected; run completed with no failure or error output (all passed) |
| `qualification_basis()` on candidate | `65f22e46c509b2f4e0540f8412e9940e5c1d9c49c85e6eb28c94f0e0b1479328` |
| `qualification_basis()` on primary checkout at `0c6a632` (main, no tracked assistant changes) | `65f22e46c509b2f4e0540f8412e9940e5c1d9c49c85e6eb28c94f0e0b1479328` (identical) |
| `BASIS_FILES` entries in the diff | None (diff touches only `data_access.py`, `model_admin.py`, `model_admin_store.py` in `ai_assistant`) |
| `scripts/build_synthetic_boundary.py --check` | "synthetic boundary is current", exit 0 |
| `ruff check --no-cache`, `ruff format --check --no-cache` (4 changed Python files) | Pass |
| `mypy ai_assistant` (cache in scratchpad) | Success, 46 files |
| Frontend `npx tsc -b --pretty false` | Exit 0 (buildinfo goes to gitignored `node_modules/.tmp`) |
| Frontend `npx vitest run src/pages/AiModelManagement.test.tsx` | 97 passed |
| `git diff --check`; trailing whitespace in the 3 untracked files | Clean |
| EOL churn (`--stat` vs `--ignore-cr-at-eol --stat`) | Identical (519+/7-) |
| Test deletions/weakening | None: frontend diff removes only one import line (re-added with `ModelDataAccess`); 5 new frontend tests; 24 new backend tests; no existing assertion changed |

Not run (and not claimed): full assistant suite (known Windows `Errno 24` environment
failures), backend suite (no backend change), E2E/Playwright (no live browser claim made),
`pre_pr_check.py` (Stage 2, needs committed state).

## 3. Review against the assignment

| Criterion | Assessment |
| --- | --- |
| HR-only control (MODEL_CONFIG_MANAGE) | `GET/PUT /data-access` use the existing `Admin` dependency; capability re-checked inside `change_lock` (`recheck`). Tested for RM/CO/Director (403). Verified |
| Server-side validation independent of browser | `DataAccessRequest`: `extra="forbid"`, `StrictInt ge=0`, `StrictBool` for all flags; widening derived from the stored row, not the client. Tested (`"false"`, `0`, `-1`, extra field, missing field -> 422). Verified |
| Explicit confirmation for broadening | `stored.local_restricted and not restrict_local` needs `confirm_widen`, else 400 `WIDEN_CONFIRMATION_REQUIRED` (audited). Verified |
| Persisted config with revisions, restart stability | One-row `data_access_policy` table with CHECKs; CAS in `set_data_access_policy` (revision-checked UPDATE inside `_write`); restart test re-creates the app and sees the wrapper. Verified |
| Audit actor/time/old->new, content-free | `events` row with actor, role, `at`, closed code `LOCAL_<old>_TO_<new>`, revision; refusals audited with codes only. No case data. Verified |
| Safe concurrency | Process lock + recheck + revision compare + store CAS (`RevisionConflict` -> 409). Verified by inspection; stale-view test |
| Clear refusal codes | Four fixed messages, mirrored verbatim in the frontend safe-message allowlist. Verified |
| Fail closed on missing/corrupt policy | Any store exception or out-of-domain row -> `None` -> local restricted, status `unavailable`, PUT refused. Missing row = revision 0 default (D-093 behaviour, as specified). Tested with a CHECK-less tampered table. Verified |
| External models checked and locked | `restrict_external:false` refused 409 before any write; `view()` hard-codes both external classes restricted+locked; selector never wraps or relaxes `RemoteTestModel`/`ClaudeTestModel` (they return before the policy is read). Frontend hard-codes `restrict_external: true`; external checkboxes disabled. Verified |
| Wrapper cannot be bypassed | All chat-path callers (`health`, `brief`->`warm_up`, `chat`, `chat_stream`, overview) use `selector.current()`, which applies `_with_data_access`. `_current()` is only used inside the selector (`current`, `revalidate`). Wrapper sets `requires_synthetic_boundary`, so `prepare(remote=True)` and `remote_gate` apply the shared D-095/D-094 gate; wrapper re-admits per call (single-use ticket or D-094 text check) for `complete` and `stream`; `warm` is a no-op. `sync_controls` and telemetry `getattr`s are unaffected. Verified |
| Classification | `RemoteTestModel` -> openrouter, `ClaudeTestModel` -> anthropic, `None` -> no class (not wrapped), `BoundedPromptModel` (loopback-only file profiles, `model_catalog.py:403`) and the environment baseline -> local_internal. A remote environment baseline cannot run live in the service (`model_factory._live_or_mock` refuses without `allow_live_network`); with a mock transport it is offline only. Non-loopback IT baseline is labelled on the page. Verified |
| No D-094/D-095/guardrail/budget/ledger weakening; no provider switching; Claude runtime/basis unchanged | No basis file changed; basis identical to main; boundary file current; guardrail, eligibility, remote, Claude and spending suites pass unchanged. Verified |
| D-095 <-> OpenRouter-readiness decoupling proposed only | D-104 A1 recorded as PROPOSED, not implemented; characterisation test documents current coupling. Verified |
| No-network live Garden `v1` reproduction | Tests show D-094 refuses only because of `v1`, D-095 admits the genuinely eligible prompt and still refuses tampered/missing digests, real cases and typed identifiers. Verified |
| Overview display-only Claude fix | Claude's own tiles replace GPT-OSS's when the active profile is Anthropic; GPT-OSS tiles otherwise unchanged. Verified (with L2 below) |
| Frontend honesty | Section renders the server's `data_access` view (status, active class, verification in force, unavailable/not-managed states); local checkbox disabled when locked/unavailable; draft reset on revision change. Verified |

## 4. Findings

No Critical, High or Medium findings.

| # | Severity | Finding | Concrete scenario | Location |
| --- | --- | --- | --- | --- |
| L1 | Low (documented limitation) | A restricted local model's refusal lead (`LOCAL_NOTICES.boundary/eligibility`) is never shown, because `_REMOTE_REFUSALS` lists only GPT-OSS/Claude notices; the RM gets the generic "AI model is not available" notice and telemetry records `model_disabled` instead of `remote_boundary`. Nothing is sent; fixing it needs `main.py` (basis file). | HR restricts the local model; an RM asks on a real case; answer is case data with the generic notice, audit/metrics show `model_disabled`. | `apps/assistant/ai_assistant/main.py:728-732`, `:814-818`; `apps/assistant/ai_assistant/data_access.py:37-50` |
| L2 | Low | Claude Overview tiles require the GPT-OSS budget view to be present and `configured` (`overview.budget` is only built when `local_api_test_decision` is set). With Claude active and GPT-OSS not configured, no spending tiles appear (no false figures, just absent). | Owner runs Claude only, no D-094 decision: Overview shows no Claude "Available now" tile. | `apps/frontend/src/pages/AiModelManagement.tsx:1343,1353`; `apps/assistant/ai_assistant/model_admin.py:1518` |
| L3 | Low (advisory) | The PUT shares the per-administrator spending rate-limit bucket; when exceeded it returns `BUDGET_RATE_LIMITED` with "Too many spending changes...", which mis-describes a data-access change. Still bounded and audited. | HR toggles the policy plus several limit edits within the window; the privacy section shows a spending wording. | `apps/assistant/ai_assistant/model_admin.py:198`, `:2150-2169`, `:2502` |
| L4 | Low (pre-existing pattern) | The "applied" audit row is written after, and outside, the policy write transaction; if the audit insert fails the policy is changed but the request errors with no audit row. Same pattern as the existing spending/limit routes. | SQLite write failure between the two statements. | `apps/assistant/ai_assistant/model_admin.py:2521-2533` |
| L5 | Low (test depth) | Not directly tested: Claude active with local restricted (not wrapped), `/brief` warm-up end to end under restriction (wrapper `warm` no-op is unit-tested), unmanaged service untouched by the policy, and a true concurrent CAS race (only a stale revision). Inspection confirms each path. | Future refactor of `model_class` or `_with_data_access` could regress unnoticed for Claude. | `apps/assistant/tests/test_data_access_policy.py` |

None of L1-L5 is a required fix for this scope: none sends data, weakens a safeguard, or
shows a false-success state. L3 is the one cheap wording improvement if the owner wants it.

## 5. Change statement (as reviewed)

API/type: added (`GET/PUT /assistant/admin/models/data-access`, overview `data_access`,
frontend `ModelDataAccess`). Schema: additive SQLite table in the model state DB. Connector,
mapping, business rule, configuration: unchanged. Auth/security: new HR-only route under
existing RBAC/Origin/rate limit; external restriction unchanged and locked. Architecture: one
module inside the model-management owner. Provider status: unchanged. Runtime: unchanged by
default; narrows a local model only when HR restricts it or the policy is unreadable.
Qualification basis: unchanged (`65f22e46c509...`).

## 6. Verdict

**PASS** for the frozen content `b6440a5f999c8cf6b8830f3443724ac7b3d87ce0e8b3cc9cf49e10e6b99bace8`.

Readiness: ready for Stage 2/4 progression (commit, integration acceptance and
`pre_pr_check.py`) only on owner authorisation; any change to the reviewed content requires a
fresh review of the changed scope. D-104 remains PROPOSED (owner decision on Z1-Z6); A1
(provider-neutral D-095) remains unimplemented and would invalidate every current
qualification. Evidence class: Mock/Local offline only; no Live claim. Hosted CI and E2E
were not executed in this gate.
