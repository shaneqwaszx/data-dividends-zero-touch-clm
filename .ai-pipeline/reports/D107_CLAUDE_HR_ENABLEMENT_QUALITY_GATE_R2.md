# D-107 Claude HR Enablement - Independent Quality Gate, Round 2

- Date: 2026-10-30
- Reviewer: fresh independent QG agent (did not author, remediate or review round 1)
- Verdict: **PASS**

## Frozen identity

| Item | Value |
| --- | --- |
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\assistant-claude-hr-enablement-20261030` |
| Branch | `feat/assistant-claude-hr-enablement` |
| HEAD = origin/main | `7e5653d51cbaf3cde5a7eff35789ede7260cca55` |
| `git diff --cached --binary HEAD \| git hash-object --stdin` (start) | `5562ba595e1a80ab229386bddcc338e0423a295a` |
| Same (end) | ``5562ba595e1a80ab229386bddcc338e0423a295a` (unchanged)` |
| Unstaged `git diff` | empty at start and end |
| Staged paths | 13 (same set as round 1) |

The reviewer wrote only this report. No index or tracked-tree change was made. The adversarial probes were in the session scratchpad only. No `.env` file was read, and no network or paid calls were made.

## Evidence (executed in this session against the frozen content)

| Check | Command (summary) | Result |
| --- | --- | --- |
| Targeted assistant suites (12 files: claude_hr_enablement, claude_runtime, claude_console, claude_hr_spending, credentials, session_credentials, data_access_policy, model_management, d098_recovery, synthetic_eligibility, remote_test, model_factory) | `python -m pytest -p no:cacheprovider -q` from `apps/assistant`, PYTHONPATH = worktree `apps/assistant` | **582 passed** (582 collected; 0 failed; exit 0), matching the author. The new file has 25 tests (21 in round 1) |
| Reviewer R2 probes (scratchpad, 5 tests) | `pytest -p no:cacheprovider -p tests.conftest <scratch>/qg2/test_qg2_d107_probe.py` | **5 passed** (see below) |
| mypy strict | `mypy --strict ai_assistant` (cache in scratchpad) | Success: no issues found in 47 source files |
| ruff | `ruff check --no-cache` and `ruff format --check --no-cache` on the 7 changed .py files | All checks passed / 7 already formatted |
| Synthetic boundary | `scripts/build_synthetic_boundary.py --check` | current |
| Qualification basis | `model_qualification.qualification_basis()` | `80448c6d7d61d500…`, which matches D-107 Q1 and PROJECT_STATE |
| Frontend | `npm run typecheck`; `npx vitest run` | clean; **69 files, 1273/1273 passed** |
| Whitespace | `git diff --cached --check HEAD` | clean |
| Docs bytes | HEAD blob vs staged blob, compared byte by byte | `PROJECT_STATE.md`: main's 106054 bytes are an exact prefix of the staged 107300, and the appended tail is CRLF (18/18 lines), matching the file's trailing CRLF region. `DECISION_LOG.md`: main's bytes are an exact prefix and the tail is LF. The new basis appears once in each, and the old candidate basis `6e7b5bb2fcac` appears zero times. |

### Reviewer probes (R2, all passed)

1. **Environment disable, then re-enable.**
   - Setup: D-099 env fully configured, and no record.
   - `PUT enabled=false, expected_revision=0` returns 200. It creates a record with revision 1, `enabled=false`, and the server's workspace.
   - After that, `configured`, `synthetic_mode`, `workspace_id` and `workspace_limit` are all closed (False / False / "" / 0).
   - A second disable returns 409 `NOT_ENABLED`, and no extra row is written.
   - Re-enabling without a workspace read returns 409 `WORKSPACE_NOT_READ`.
   - Re-enabling with three of the four confirmations returns 400.
   - After a read with the key in force, the normal enable returns 200 with readiness `None`. Both audit actions are recorded.
2. **Environment disable is refused when the configuration is incomplete.** With no D-099 decision, an invalid env workspace, or an env limit of 0, the request returns 409 `NOT_ENABLED` and no record is created. A limit above 30,000,000 is already rejected by `AiAssistantSettings`.
3. **A disabled record pins the env workspace.** A key that now reports a different workspace cannot re-enable: the request returns 409 (`WORKSPACE_CHANGE_REFUSED`/`WORKSPACE_MISMATCH`). Readiness stays `ANTHROPIC_NOT_ENABLED`, so the system fails closed.
4. **Standing mismatch.** HR-enabled and activated Claude, with a server workspace that differs, fails closed everywhere:
   - `readiness`: `WORKSPACE_MISMATCH`.
   - Catalogue: `availability` is `unavailable/WORKSPACE_MISMATCH`, the entry scope is `PROVIDER_CONTROLS_MISSING`, and `VERIFIED_SYNTHETIC_CASES` is absent.
   - Spending view: `refusal=WORKSPACE_MISMATCH`.
   - Calls: the `ClaudeTestModel` constructor raises `ProfileConfigError(WORKSPACE_MISMATCH)`. This is what both `Selector` activation (`model_admin.py:864`) and the qualification child construct.
   - `preflight` fails on its first check, `anthropic.ready`.
   - Zero additional Claude posts.
5. **No secrets in responses or audit.** The overview, the audit events and the disable response never contain the session key.

## Remediation verification

| R1 item | Verified | Notes |
| --- | --- | --- |
| L1 | Yes | The setup steps render whenever `!record?.enabled` (`AiModelManagement.tsx:776`), and Disable renders whenever `setup.enabled` (`:812`). The backend env-disable branch (`model_admin.py:2813-2824`) always writes `enabled=False`, because `body.enabled` is False on that branch. It can only pin the env workspace when `valid_workspace` holds and the D-099 decision is named. Re-enabling then goes through the unchanged enable branch: local deployment, four exact confirmations, a bounded limit, a fresh read with the same key identity whose workspace equals the body, and a body workspace equal to the record workspace and to any env workspace. The env-pinned workspace was never key-reported, but it can only be re-enabled after the key reports that same workspace. It cannot enable anything by itself. |
| L2 | Yes | `providerState` (`AiModelManagement.tsx:1433-1446`) branches on `setup.source`. A frontend test covers it. |
| L3 | Yes | `:1103` now reads "owner-confirmed, not read from Anthropic" / "Not confirmed yet". |
| L4 | Yes | `anthropic_runtime.readiness` (HR branch) returns `WORKSPACE_MISMATCH` whenever a server workspace is set and differs. Every gate inherits it: catalogue, constructor, `_ready` per call, preflight, spending refusal, and the D-102 raise guard (`require_claude_raise`). The qualification child reads the same record, because `qualify_model.py:63` sets `model_admin_db_path=args.db`. E4 is updated. `REASON_TEXT` is added. |
| T1 | Yes | `test_every_d095_check_still_applies_to_hr_enabled_claude` (tampered and missing digest, `case_data`, no posts). The 8-thread CAS test has 1 winner, 7 conflicts and 1 audit row. The env-disable and standing-mismatch tests are present and pass. |

The round 1 properties still hold:
- **Off without HR or legacy, or off the local deployment.** No record and no D-099 gives `ANTHROPIC_NOT_AUTHORISED`. HR enable and read require `local_deployment`.
- **Record decides.** A disabled record wins over D-099 env (probe 1). An unreadable record fails closed.
- **Workspace pin.** The pin is immutable from the page.
- **CAS.** The audit row is written in one transaction.
- **No key or marker leakage.**
- **D-095 checks.** All of them stay enforced (T1 test).
- **GPT-OSS.** `mode()` and its data-access classes are unchanged.

## Findings

| # | Severity | Location | Finding |
| --- | --- | --- | --- |
| I1 | Info (UX text) | `AiModelManagement.tsx:763`, `:1438`; `model_admin.py:2716` | `anthropic_setup.enabled` is `configured()`, which means "switched on", not "ready". Under a standing `WORKSPACE_MISMATCH` (or any other HR-branch readiness failure), the heading still says "Enabled for verified synthetic cases" and Data Access says "Enabled by HR". The readiness line in the same card does show the mismatch reason. Every call path is closed (probe 4). Consider "Enabled (not ready: …)" in a later pass. |
| I2 | Info (scope) | `anthropic_runtime.py:232-238` | Under an HR record, `synthetic_mode` does not consult readiness, so `data_access.verification_mode` can report `D-095` for Claude while readiness is failing (for example on a mismatch). This is not reachable as a call, because `_ready` re-checks readiness under the lock before every call, and the catalogue scope comes from `availability` first. It is display only. |
| I3 | Info (UX edge) | `AiModelManagement.tsx:812`; `model_admin.py:2819-2823` | When the source is environment with an invalid env workspace or limit, `enabled` is still true, because `configured()` checks only the decision name. Disable is therefore offered, but it returns "Claude is not enabled, so there is nothing to disable." Claude is already not ready in that state, so this is safe, but the message is slightly confusing. An operator must fix or clear the env configuration. |

No Critical, High, Medium or Low findings. No secret, key, marker or protected data is newly tracked.

## Change classification

- **API/type:** yes. It adds `PUT /provider/anthropic` and `POST .../workspace-read`, `anthropic_setup` in the overview, and the `AnthropicSetup` TS type. The env-disable branch is new in R2.
- **Schema:** yes, the SQLite `anthropic_enablement` table (unchanged since R1).
- **Configuration:** no new setting.
- **Auth/security:** yes. HR only, Origin, rate limit, and a recheck under the lock.
- **Business rule:** yes. Claude enablement source (D-107), and the standing workspace equality (E4).
- **Mapping/connector:** no.
- **Architecture:** no new owner.
- **Provider status:** Claude remains Local/Mock-evidenced here. No Live claim is made.
- **Runtime behaviour:** yes. Claude readiness, and the D-095 mode under HR enablement.
- **Qualification basis:** moves to `80448c6d7d61…` (an owner-authorised re-qualification after merge).

## Readiness

The reviewed content (`5562ba59…`) is acceptable for the next lifecycle stage. Publication still needs `pre_pr_check.py` on the committed state, with the committed tree equal to this reviewed content, and explicit owner authorisation. Claude Balanced re-qualification on basis `80448c6d7d61…` remains an owner-authorised step after merge. The Info items need no change before publication.
