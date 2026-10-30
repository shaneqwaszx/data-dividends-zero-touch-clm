# D-100 Phase 1 final integration with merged D-099 (PR #130) - independent Quality Gate

Date: 2026-10-29. Reviewer: independent QG (did not implement). Read-only review; the only
file written is this report. No network or paid call, no `.env` access, no Git mutation.

## Reviewed content identity

| Item | Value |
| --- | --- |
| Worktree / branch | `claude-worktrees/d100-ai-console-phase1-20261029` / `feat/d100-ai-console-phase1` |
| HEAD | `d5ae27a70bf09b447520351cea90ed5fa05ef7f6` |
| HEAD tree | `44e5ddbbca88d58a1c9d881050a7b7dcaf6315df` |
| origin/main | `d949edba03439ee56e6b907bc79dbc57a35537c1` (PR #130, parent `8c7ea99`) |
| Uncommitted `.ai-pipeline/reports/D099_D100_INTEGRATION.md` | sha256 `497b14c3ecf3beeff7fc172cdff8b808b1869a7405c76bb66ab80e4aedf1a20d` (matches) |
| Uncommitted `docs/PROJECT_STATE.md` | sha256 `f46d81e20e8d0b42550d708456d8ce22f62f4a86dbf06ef17f70a349d54d7c52` (matches) |
| Uncommitted `docs/integration/AI_MODEL_CONFIGURATION.md` | sha256 `6933e8b77796aaa6316662307be4b91e2768605057ee6124ada423e1f90e4c93` (matches) |

`git status` shows only those three modified files; nothing else untracked or staged.

## History verification

- `dda1968` is a two-parent merge: `45ae602` (PR #131 head) + `d949edb` (origin/main).
- `518f4e1` and `d5ae27a` are faithful cherry-picks: the patch `dda1968..518f4e1` equals
  `9b97737..53f12ee`, and `518f4e1..d5ae27a` equals `53f12ee..ef9f5c0` (compared with `index`
  lines and hunk offsets stripped; identical hashes).
- `git diff 9b97737 dda1968`, `git diff ef9f5c0 d5ae27a` and `git diff 32263b9 d949edb` are the
  same patch (same normalised hash): FU2 only (`model_admin.py`, `test_claude_runtime.py`,
  `aiAssistant.ts`, one `AiModelManagement.test.tsx` test, two FU2 reports). The earlier
  integration's D-099 side `bfb8c904` has the same tree as `32263b9`. Claim confirmed.
- `git diff --stat d949edb d5ae27a`: frontend console files, reports and docs only; no file under
  `apps/assistant` or any backend, API, spending-control, key or config file. The D-100
  `ConsoleShell.tsx` and `aiModelConsole.css` are byte-identical to `45ae602`.
- Test titles: every `it(...)` in `AiModelManagement.test.tsx` at `45ae602` and at `d949edb` is
  present at HEAD (0 missing); 8 integration tests added. No test line from `45ae602` was removed;
  lines removed relative to `d949edb` are D-100's own already-reviewed harness refactor
  (`mount`, `act`), not assertions dropped.

## Checks run

| Check | Result |
| --- | --- |
| `npx vitest run src/pages/AiModelManagement.test.tsx src/aiAssistant.test.ts` | 2 files, 63 passed (61 + 2); React `useLayoutEffect` SSR warnings only |
| `npm run typecheck` (`tsc -b`) | clean |
| `pytest tests/test_claude_runtime.py tests/test_claude_console.py` | 121 passed |
| `pytest tests/test_claude_multi_turn.py` | 66 passed |
| Qualification basis | `33f602653de73f372a787a9d4403daedcd589140aae02b86a4796cd994e87513` (unchanged) |
| `check_secrets`, `check_project_state`, `check_policy_authority`, `check_architecture`, `check_tooling_config` | all PASS |
| `git diff --check d949edb HEAD`, `git diff --check` | clean |
| Trailing whitespace in the three uncommitted Markdown files | none; index EOL LF (PROJECT_STATE pre-existing mixed), `--ignore-cr-at-eol` numstat identical |

Not rerun by this QG (implementer claims, not independently verified): full frontend
`vitest run` (1,179), the 622-test assistant focused set, `test_remote_test.py`, the MOCK
browser run (38/38), `vite build`. Full backend, OCR, Mongo and E2E suites not run (out of scope).

## Review by scope item

1. Integration fidelity: confirmed above; no D-099 change duplicated or dropped, no D-100
   change lost.
2. Overlapping frontend files: D-099 hunks (`ANTHROPIC_NOT_AUTHORISED`,
   `ANTHROPIC_PROVIDER_CONTROLS_MISSING`, Anthropic `PROVIDER_LABEL`, `THINKING_LABEL`,
   `PROVIDER_CONTROLS_MISSING` scope, Thinking in `RemoteDetails`) are present
   (`AiModelManagement.tsx:64-65,276-298`); all D-099, D-100, integration and FU2 tests present.
3. FU2: backend `model_admin.py:220-223` message concatenates to exactly the string in
   `aiAssistant.ts:152` and the test `AiModelManagement.test.tsx:744`; selection at
   `model_admin.py:1513-1519` only for `PROVIDER_LIMIT_NOT_CHECKED` on the `anthropic`
   deployment; backend tests assert both the Claude text and the GPT-OSS text byte-for-byte
   (`test_claude_runtime.py:893-920`).
4. Paid run / activation: `runQualification` always routes `openrouter` and `anthropic` to the
   dialog (`AiModelManagement.tsx:984-991`); Start is disabled when busy or
   `!sufficient` (`:1225`); `startPaid` sends the confirmed call count only; backend still
   refuses `PAID_CONFIRMATION_REQUIRED` without it (`model_admin.py:1543-1546`). Activation keeps
   the unscored acknowledgement gate for both providers and shows a Claude-specific warning.
5. Provider-specific UI: inspector shows provider/reasoning/thinking (`:831`); Claude refusal,
   Recovery cause/action/escalation wording via `CLAUDE_REASON_TEXT`, `CLAUDE_CAUSE_TEXT`,
   `CLAUDE_ACTION_TEXT`; banner generalised (`:1067`); overview figures suffixed "(GPT-OSS)"
   when Claude is listed and Spending & Limits states GPT-OSS only (`:740-755`, `:1126-1131`).
   Residual gaps in M-1 / M-2.
6. GPT-OSS regression: OpenRouter texts are unchanged and selected whenever the deployment is
   not `anthropic`; tests keep the GPT-OSS wording.
7. Accessibility/responsive: `ConsoleDialog` (unchanged from reviewed `45ae602`) has
   `role="dialog"`, `aria-modal`, `aria-labelledby`, Escape, focus trap and focus restore; the
   integration only adds text inside existing containers. Layout CSS unchanged. No own browser
   run.
8. Docs: D-099 remains PROPOSED, D-100 entry retained (`DECISION_LOG.md:1463,1505`); no Live,
   activation or sponsor claim; PR #130 merge status is real. One stale passage (M-3).

## Findings

| ID | Severity | File:line | Finding |
| --- | --- | --- | --- |
| M-1 | Minor | `apps/frontend/src/pages/AiModelManagement.tsx:228,567,1067,1074,1170` | `readable()` called without the deployment for a Recovery card's `run.code`, `QualificationDetail` code, the AI-unavailable / start-up `reverted` code and audit codes. For a Claude profile a code such as `CREDENTIAL_INVALID`, `PROVIDER_CHECK_FAILED` or `PROVIDER_LIMIT_NOT_CHECKED` would show OpenRouter wording. Carried unchanged from reviewed `ef9f5c0`; reachability depends on backend codes. Follow-up recommended, not blocking. |
| M-2 | Minor | `apps/frontend/src/pages/AiModelManagement.tsx:1220` | Insufficient-funds banner in the paid dialog says "Review the spending controls" for Claude too, although Claude's limits are not on that page. Wording follow-up, not blocking. |
| M-3 | Minor | `docs/PROJECT_STATE.md:1291-1292,1315` | The D-099 section heading now says "PR #130, merged to main `d949edb`", but the body still says "(draft PR #130). Delta only; nothing here is merged" and the stale "Open: fresh independent QG, latest-main integration and final gate" line; the appended status update corrects it but the section is self-contradictory. Required docs-only fix (e.g. "merged; not activated or Live"). |
| I-1 | Info | `apps/frontend/src/pages/AiModelManagement.tsx:1001` | `recoverable` lists an unqualified remote profile only for `openrouter`; an unqualified Claude profile is not shown in Recovery (same as `ef9f5c0`). |
| I-2 | Info | `docs/decisions/DECISION_LOG.md:1518` | D-100 update still says "on the integration candidate"; kept unchanged deliberately per the report; acceptable. |
| I-3 | Info | `.ai-pipeline/reports/D099_D100_INTEGRATION.md:136-149` | Evidence counts (1,179 frontend, 622 assistant, 38/38 browser) not rerun here; the focused subsets rerun here pass. |

No Blocker or Major findings. No backend/API/schema/spending-control/key/configuration/
business-rule/mapping/auth change on the D-100 side; no secret newly tracked; basis unchanged.

## Verdict

**PASS WITH MINOR FIXES.** Required: M-3 (docs-only correction of the D-099 section in
`docs/PROJECT_STATE.md`). Recommended follow-ups (not required for this gate): M-1, M-2.
