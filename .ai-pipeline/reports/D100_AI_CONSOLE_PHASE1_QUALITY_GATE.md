# D-100 Phase 1 — AI Model Console redesign: Independent Quality Gate

## Outcome

**PASS WITH MINOR FIXES.** All Phase 1 acceptance criteria were verified on the frozen tree.
No API, contract, query-key, refresh, mutation-retry, RBAC/route, session or safeguard
behaviour changed. Three bounded minor fixes remain (M1 to M3: focus return, two inaccurate
help strings, badge accessible name). None of them touches security, the contract or a
false-success claim. The debt items (D1 to D4) are recorded and do not block.

The reviewer did not author or remediate this content. The gate was read-only: the only file
written is this report. Scratch files and screenshots went outside the repository, or into the
git-ignored `.playwright-mcp/d100/qg/`.

## Reviewed identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\d100-ai-console-phase1-20261029` |
| Branch | `feat/d100-ai-console-phase1` |
| HEAD = base = origin/main | `8c7ea99cfb134a6edf2313f907fb913c4c21a1d6` (no commits) |
| Candidate (index) `git write-tree` | `405cc6d4ce0f23ac050ee2c73169a931eae0569d`. Confirmed at the start and again before the verdict, unchanged. |
| Paths | `apps/frontend/src/pages/AiModelManagement.tsx` (M), `apps/frontend/src/pages/AiModelManagement.test.tsx` (M), `apps/frontend/src/pages/aiModels/ConsoleShell.tsx` (A), `apps/frontend/src/pages/aiModels/aiModelConsole.css` (A), `docs/integration/AI_MODEL_CONFIGURATION.md` (M) |
| Change class | FRONTEND_UI |
| Working tree | equals index; `git status` shows only the 5 staged paths before and after the gate (build output `dist/` is ignored) |

## Requirement verification

| Requirement | Result | Evidence |
|---|---|---|
| ConsoleShell + responsive section nav | Met | `ConsoleShell.tsx`. Links use `to={{search}}` and keep the pathname. At ≤900px the nav folds behind a toggle with `aria-expanded`/`aria-controls`; the target id exists, and the menu closes when a link is clicked. Browser check at 360 px: list hidden, then visible after toggle, `aria-expanded=true`. |
| Section in the URL (`?section=`), unknown → overview, no mutation | Met | `consoleSection` falls back to overview. Browser: `?section=bogus` gave h1 "Models & Overview" with aria-current set. SPA clicks through all 5 sections, Back ×2, Forward and Reload sent **0 non-GET requests**, and the section was restored each time. This matches ARCHITECTURE §14 (the location is the page identity; traversal triggers no mutation) and frontend AGENTS (only a closed enum goes in the URL, nothing sensitive). |
| Models & Overview (active band, summaries, configuration grid) | Met | `ActiveModelBand`, `OverviewSummary`, `configurationGroups`/`ConfigurationTile`. Every value comes from existing `ModelOverview`/`ModelProfileView` fields; typecheck passes and no new type fields were added. "AI unavailable" cannot read as active: the backend sets `active.profile_id="ai_unavailable"` (model_admin.py:1250/1285), so no profile is `active` and the band shows "No model answers / AI unavailable". |
| Inspector wired to the existing actions | Met | The inspector's Test/Run/Activate buttons call the same handlers (`testModelConnection`, `runQualification`, `setConfirming`). The disabled predicates are byte-equivalent to the old table row: `!usable‖busy`, `…‖!item.endpoint`, `…‖item.active‖blockers>0`. |
| Legacy sections unchanged in behaviour | Met | `OpenRouterKey`, `SpendingLimits`, `RecoveryCard`, `QualificationDetail` and the audit table are unchanged apart from two strings and the `#spending-heading` anchor becoming a `?section=spending` Link. Their tests pass unchanged, with only the mount section added. |
| No API/contract/query/refresh/retry/RBAC change | Met | `aiAssistant.ts`, `navigation.tsx` and `App.tsx` are not in the diff. Query keys, `refetchInterval` (RUNNING_REFRESH_MS), audit `AUDIT_REFRESH_MS`, the run-ended audit invalidation and `retry:false` are untouched (diff hunks start after them). The audit query still runs in every section, as before. |
| Paid-run confirmation, not-scored ack, rollback, spending, key handling | Met | `runQualification` still routes remote runs to the dialog, and `confirm_paid_calls` is sent only from `startPaid` (test line 741). Browser check: the paid dialog sent 0 writes; Activate Confirm stayed disabled until the acknowledgement was ticked, then sent exactly one `POST …/activate`. Key/spending components are unchanged. |
| Exports and test ids preserved | Met | `modelManagementQueryKeys`, `profileName`, `readable`, `toMicroUsd`, `amountText`, `escalationSummary`, `REASONING_LABEL`, `RUNNING_REFRESH_MS`, `AUDIT_REFRESH_MS` and the `recovery-*`, `paid-confirm`, `daily-raise-confirm`, `key-owner-action`, `ai-unavailable` ids are all still present. |
| Test adaptation did not weaken coverage | Met | 39 → 46 `it` blocks; 207 → 251 `expect(` calls. Only 4 `expect` lines were removed, each replaced by an equivalent: Access refused (moved after `go(Audit)`), two spending-anchor href assertions (new href), and an Activate-disabled check (moved after Cancel + `go(Overview)`). The `button()` helper is stricter than before: it throws when a row is missing, where the old version fell back to the whole view. |
| Dialog accessibility | Met, with M1 | `role=dialog`, `aria-modal`, `aria-labelledby`; focus moves into the dialog. Tab and Shift+Tab ×5 each stayed inside (independent browser check); Escape cancels (unit test plus implementer check). Focus returns on Escape/Cancel. **It does not return** after Confirm or after a backdrop click (M1). |
| No horizontal overflow at 360; bottom sheet ≤640 | Met | `documentElement.scrollWidth == 360` in every section, after history traversal, and with the technical-details table expanded plus a pathological long unbroken profile name. Paid dialog at 360×740: x=0, width 360, bottom=740 (bottom sheet). |
| Contrast | Met | Computed WCAG ratios of the rendered console text (chips, labels, notes, nav, band, primary button); the lowest was 5.97:1. |
| Phase 2 not started | Met | No new API usage, no editing surfaces, and legacy sections are embedded unchanged. |

## Findings

### Minor (bounded fixes requested)

- **M1: dialog focus is not returned after Confirm or a backdrop click.**
  - Where: `apps/frontend/src/pages/aiModels/ConsoleShell.tsx:103-107` and `:130`.
  - Scenario: HR presses Confirm on activation. The mutation makes `busy` true, so the Activate trigger is disabled when the dialog unmounts. `previous.focus()` then has no effect and focus lands on `<body>` (browser: `activeElement=BODY`).
  - Scenario: a backdrop `mousedown` closes the dialog, then the browser's default mousedown action moves focus to body, so focus is not back on the trigger.
  - Fix:
    - Fall back to a stable target (the inspector heading or section `h1` with `tabIndex=-1`) when the trigger is disabled or removed.
    - Call `preventDefault()` on backdrop mousedown.
  - The old inline dialog had no focus management at all, so this is not a regression. It is a gap against the stated a11y requirement.
- **M2: two inaccurate help strings.**
  - `AiModelManagement.tsx:1056` says "Local models need no key." Local IT profiles can declare a server-side `credential_env` (model_catalog.py:418-431, reason `CREDENTIAL_MISSING`), so the sentence is untrue for those profiles. Suggested wording: "Local model keys are set by IT on the server."
  - `AiModelManagement.tsx:709` says "{n} listed by IT", but `profiles.length` also counts the environment baseline and code-defined GPT-OSS profiles. Suggested wording: "{n} configurations listed".
- **M3: the nav badge has no accessible context.**
  - Where: `ConsoleShell.tsx:77`.
  - The link's accessible name reads "Qualifications & Recovery1" (observed in the browser). A screen-reader user gets a bare number.
  - Fix: add sr-only text such as "(1 needs attention)", or put an `aria-label` on the badge.

### Debt (recorded, not blocking)

- **D1: inspector off-screen on desktop.** `inspect()` (`AiModelManagement.tsx:947-951`) scrolls only at ≤900px. At 1440 px, after selecting a lower tile (with details expanded), the inspector top was at −191px. Consider a sticky inspector or a scroll on desktop as well.
- **D2: RemoteDetails hidden for non-active remote configurations.** RemoteDetails (provider, external-inference scope, decision) now appears only in the active band and the folded "Technical details" table. The inspector omits it. D-099's provider/thinking text would be visible only after expanding details. The group subtitle shows the provider label.
- **D3: background not inert under the modal.** `aria-modal` is set, but the background is not `inert` and has no scroll lock. The backdrop z-index 80 sits above the assistant panel (60), so pointer access is blocked.
- **D4: "D-100" has no decision record.** "D-100" is cited in the tracked doc and code comments, but there is no DECISION_LOG or planner entry on main or on the D-099 branch. That is acceptable for a presentation-only task label, but it should be recorded (or reserved) before publication to avoid an ID collision.

No bug-class findings. No security findings: no key value is rendered or stored, the URL carries only the section enum, and there are no new storage writes.

## Commands run (on tree 405cc6d)

| Command | Result |
|---|---|
| `git write-tree` (start / end) | `405cc6d4ce0f…` / `405cc6d4ce0f…` |
| `npx vitest run src/pages/AiModelManagement.test.tsx` | 1 file, **46 passed**. Its stderr has only the pre-existing `useLayoutEffect` SSR warning, from the unchanged `renderToStaticMarkup` access test. |
| `npm run typecheck` | exit 0 |
| `npm test` | **66 files / 1164 tests passed** |
| `npm run build` | exit 0. Pre-existing warning: one chunk is over 500 kB (1,143 kB). |
| `git diff --cached --check` | clean. The new files are staged, so they are covered. |
| `python -I scripts/check_architecture.py` | PASS |
| `python -I scripts/check_project_state.py` | PASS |
| `python -I scripts/check_secrets.py` | PASS |
| Independent Playwright check against Vite at 127.0.0.1:5179, 1440×900 and 360×740, DSF 1, all `/api/**` mocked | See the browser evidence section |
| `pre_pr_check.py` | NOT run (no PR authorised; not required for this handoff) |

Script: `C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane--claude-spares-spare-s08WXT\9275bfac-4623-4922-8ae2-a68fd03245c1\scratchpad\qg_d100\qg_browser.cjs`. The independent check covered:

- SPA navigation via the nav links (mobile menu included)
- Back, Forward and Reload
- unknown section
- expanded details with a long unbroken name
- paid dialog Shift+Tab/Tab trap
- backdrop cancel
- acknowledge → Confirm
- computed contrast
- write log

### Browser evidence (MOCK only)

This is **MOCK evidence only**: every `/api/**` request was answered by `page.route`, and no backend, assistant service or provider was contacted. The only unmatched request was `GET /api/system/execution-profile`; it produced the header "Loading profile…" badge and 404 console errors, and is a mock gap. Screenshots are in `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.playwright-mcp\d100\qg\`.

I also inspected the implementer's script (`console_browser_check.cjs`). It is consistent with my results, but it reaches the sections by `page.goto` rather than by UI navigation; my check covers SPA navigation.

## D-099 (PR #130) conflict assessment

The files were extracted with `git show` (base `8c7ea99`, candidate index, `origin/feat/assistant-claude-sonnet-console`) into a temporary directory outside every checkout. `git merge-file` reported **0 conflicts** on all three shared files:

- `AiModelManagement.tsx`
- `AiModelManagement.test.tsx`
- `AI_MODEL_CONFIGURATION.md`

D-099's hunks (REASON_TEXT, PROVIDER_LABEL/THINKING_LABEL, RemoteDetails, a new `describe` block, doc §13) do not overlap the candidate's hunks.

The merged page and test were run in a temp copy of `apps/frontend` (`git archive` of tree 405cc6d plus a `node_modules` junction):

- Vitest: **48 passed** (46 + D-099's 2).
- `tsc -p tsconfig.app.json --noEmit`: exit 0.

D-099's `button(view, "Activate", row)` works through the new tile+inspector helper; tile text contains "Claude Sonnet 5.5 — Balanced/Fast". Its RemoteDetails and reason assertions are satisfied by `view.textContent`: RemoteDetails is in the folded details table and the reason is in the inspector/tile.

Residual risk is low. Note D2: the D-099 provider/thinking line is visible to users only after they expand the details. Semantic merge order is neutral, but whichever PR lands second must re-run the focused test.

## Verdict

**PASS WITH MINOR FIXES.** The required fixes are M1 (focus fallback after Confirm and on backdrop close), M2 (two help strings) and M3 (badge accessible text). The remediation delta needs a focused re-review: page/shell tests, typecheck, and a re-run of the dialog focus browser check. The other evidence stays valid if only those lines change. The verdict applies only to tree `405cc6d4ce0f23ac050ee2c73169a931eae0569d`. No commit, push or PR is authorised by this gate.
