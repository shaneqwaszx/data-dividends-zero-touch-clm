# D-107 Claude HR Enablement - Independent Quality Gate

- Date: 2026-10-30
- Reviewer: independent QG agent (did not author or remediate this content)
- Verdict: **PASS WITH MINOR FIXES**

## Frozen identity

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-hr-enablement-20261030` |
| Branch | `feat/assistant-claude-hr-enablement` |
| HEAD = origin/main | `7e5653d51cbaf3cde5a7eff35789ede7260cca55` |
| `git diff --cached --binary HEAD \| git hash-object --stdin` (start) | `f9cb94dbd89dcc55b3cae6369724ed57ad8d0d4d` |
| Same (end) | `f9cb94dbd89dcc55b3cae6369724ed57ad8d0d4d` (unchanged) |
| Unstaged `git diff` | empty at start and end |
| Reviewed paths | 13 staged files (6 assistant modules, `synthetic_boundary.json`, new `tests/test_claude_hr_enablement.py`, `aiAssistant.ts`, `AiModelManagement.tsx` + test, `PROJECT_STATE.md`, `DECISION_LOG.md`) |

The reviewer wrote only this report. No index or tracked-tree change was made; adversarial probes lived in the session scratchpad only. No `.env` read, and no network or paid calls were made.

## Evidence (executed in this session against the frozen content)

| Check | Command (summary) | Result |
| --- | --- | --- |
| Targeted assistant suites (12 files: claude_hr_enablement, claude_runtime, claude_console, claude_hr_spending, credentials, session_credentials, data_access_policy, model_management, d098_recovery, synthetic_eligibility, remote_test, model_factory) | `python -m pytest -p no:cacheprovider` from `apps/assistant`, PYTHONPATH pinned to the worktree | **578 passed**, 0 failed, exit 0 (matches author) |
| New test file | included above | 21 tests (7 functions incl. parametrised), all pass |
| Reviewer adversarial probes (scratchpad, 6 tests) | `pytest -p tests.conftest <scratch>/test_qg_d107_probe.py` | **6 passed** (see below) |
| mypy strict | `mypy --strict ai_assistant` (cache in scratchpad) | Success: no issues in 47 files |
| ruff check / format check | `ruff check --no-cache` and `ruff format --check --no-cache` on the 7 changed .py files | clean / 7 already formatted |
| Synthetic boundary | `scripts/build_synthetic_boundary.py --check` | current |
| Qualification basis | `model_qualification.qualification_basis()` | `6e7b5bb2fcaca22b...` = documented `6e7b5bb2fcac...` |
| Frontend | `npm run typecheck`; `npx vitest run` | clean; **69 files, 1271/1271 passed** |
| Whitespace | `git diff --cached --check HEAD` | clean |

Reviewer probes (all passed):
1. HR mode, a tampered GARDEN document digest, and then an empty digest list: the RM gets `case_data`, with no Claude POST.
2. `verification_mode`: anthropic=D-095 under HR mode. openrouter and local_internal stay D-094 (GPT-OSS is unaffected by Claude's record).
3. Legacy D-099 env fully configured, plus an HR record that is then disabled: readiness `ANTHROPIC_NOT_ENABLED`, connection-test 409 `REMOTE_NOT_AUTHORISED`, 0 Claude posts. The legacy path cannot bypass the disable.
4. 8-thread CAS race on `set_anthropic_enablement(0, ...)`: exactly 1 winner and 7 `RevisionConflict`, with exactly one `ANTHROPIC_ENABLED` audit row.
5. Overview, audit, workspace-read responses and captured logs never contain the key or its HMAC identity marker.
6. Re-enable while enabled (same workspace) can lower the owner-confirmed limit. The revision increments, and the ledger is untouched.

## Adversarial focus results

- **Claude without HR or legacy, or off the local deployment.** Not possible. With no record and no D-099, readiness returns `ANTHROPIC_NOT_AUTHORISED`. On the HR path, readiness requires `llm_enabled` plus a literal loopback backend and local origins (`anthropic_runtime.py:187`, `:238`). `_ready` re-checks readiness before every call. `read_workspace` refuses off-deployment (`anthropic_runtime.py:564`).
- **Disabled or unreadable record.** When a record exists it decides, and the env path is never consulted. An unreadable DB or a malformed row gives `ANTHROPIC_ENABLEMENT_UNREADABLE`, and `configured`/`workspace_id`/`workspace_limit`/`synthetic_mode` all return closed values. A missing table or file falls back to legacy env, as designed and documented.
- **Workspace pinning.** Enabling requires the workspace from a passed read made with the same key identity within 3600 s. The workspace cannot change once a record exists, even after a disable. It must equal any env workspace at enable time. At runtime, the preflight and the in-band reply check use the HR workspace, and live adapter construction refuses an empty workspace (`anthropic_chat.py:310`).
- **CAS and audit atomicity.** `BEGIN IMMEDIATE`, a revision compare, the row write and `_insert_event` all run in one transaction. The route re-reads under `change_lock` with `recheck` (RBAC). Refusals are audited separately.
- **Key leakage.** `read_workspace` returns the marker only to the route, which keeps it in process memory and never returns or audits it. This was confirmed by probe 5.
- **D-095 under `synthetic_mode`.** `main.py` still runs `synthetic_eligibility.check` (provenance, SHA-256 digests, viewer, grounding, text) and issues the one-use ticket. `_ready` and the adapter `_admit_in_adapter` still re-check it. GPT-OSS `mode()` and the data-access classes for openrouter and local are unchanged.
- **Overview budget without D-094.** The frontend gates every GPT-OSS use on `budget?.configured` (`AiModelManagement.tsx:963, 1219, 1534, 2024`). `remoteNotice` receives `mode` undefined, which is the same as before. No GPT-OSS view regression.

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| L1 | Low (user-visible status) | `apps/frontend/src/pages/AiModelManagement.tsx:766`, `:775`, `:811` | With the legacy D-099 env configuration (`source: "environment"`), `setup.enabled` is true. The setup steps are therefore hidden, and the Disable button is hidden too because there is no record. The panel nevertheless says "Setting it up here replaces that configuration". HR is offered an action the page does not provide, and cannot disable an env-configured Claude from the console. Fix: show the setup steps when `source !== "hr"`, or change the wording to say an operator must remove the D-099 settings. |
| L2 | Low (user-visible status) | `AiModelManagement.tsx:1436` | On Data Access & Privacy, `providerState` labels Claude "Enabled by HR (Providers → Anthropic)" whenever `setup.enabled`, including when the source is the environment. Use `setup.source` to choose the label. |
| L3 | Low (stale wording) | `AiModelManagement.tsx:1102` | The Spending view still shows "Not attested on the server" when there is no limit. Under D-107 the limit comes from HR's owner confirmation. Wording only; it never claims verification. |
| L4 | Low (doc vs code) | `model_admin.py:2804`, `DECISION_LOG.md` D-107 E4 | The env workspace equality is checked only at enable time. If an operator later sets a different `AI_ASSISTANT_ANTHROPIC_WORKSPACE_ID`, the HR record still silently wins at runtime. This is fail-safe, because replies must still name the HR workspace, but E4 reads as a standing invariant. Clarify E4 ("at enable time"), or report a mismatch in readiness or the setup view. |
| I1 | Info (scope) | `anthropic_runtime.py:228`, D-107 E6, `PROJECT_STATE.md` | Under HR enablement, Claude's D-095 mode no longer needs the D-095 decision name (`synthetic_dev_decision`). The owner summary listed D-091/D-092/D-094. Dropping the D-095 name is consistent with the owner's "Verified synthetic cases only" requirement, all D-095 checks remain enforced (probe 1), and the change is documented in E6 and PROJECT_STATE. Owner awareness is recommended; this is not a defect. |
| I2 | Info (UX text) | `AiModelManagement.tsx:1498` | The external-provider data-access text always describes the D-095 checks. When a provider is in D-094 mode (only the fixed fixture case), the real restriction is stricter than stated. This is not unsafe. |
| T1 | Low (test depth) | `apps/assistant/tests/test_claude_hr_enablement.py` | There are no adverse D-095 tests under HR mode (a tampered or missing digest) and no store-level CAS race test. The reviewer's probes 1 and 4 cover both and pass. Consider adding equivalents. |

No Critical, High or Medium findings. No secret, key, marker or protected data is newly tracked. GPT-OSS behaviour and the teammate chatbot guardrails are unchanged in the reviewed diff.

## Change classification

API/type: yes (2 new admin routes, `anthropic_setup` in the overview, and `budget` becoming non-null without D-094). Schema: yes (new SQLite table `anthropic_enablement`). Configuration: no new environment setting. Auth/security: yes (HR-only, origin, rate limit, recheck under lock). Business rule: Claude enablement source (D-107). Runtime behaviour: yes (Claude readiness and D-095 mode under the HR record). Provider status: unchanged (offline mock/local evidence only; nothing Live). Mapping/connector/architecture ownership: unchanged.

## Readiness

The content is acceptable for publication once L1 and L2 (and optionally L3, L4 and T1) are fixed. Any fix changes the reviewed content and needs a fresh independent review of the changed scope. Then `pre_pr_check.py` must pass on the committed state and the owner must authorise publication. The Claude Balanced re-qualification on basis `6e7b5bb2fcac...` remains an owner-authorised post-merge step.
