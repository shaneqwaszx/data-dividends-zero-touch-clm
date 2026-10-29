# D-100 Phase 1 — AI Model Console redesign: Independent Quality Gate re-review

## Outcome

**PASS** for tree `e786c8bdea54aeb31cbcd5bdbf1714d907e9b188`.

The remediation closes M1, M2 and M3 from the first gate (tree `405cc6d`) and also resolves
debt item D1. It introduces no regression in the API, contract, query or refresh behaviour, the
paid-run confirmation, the acknowledgement gate, RBAC or the D-099 merge. No required fix
remains.

Debt items D2 to D4 remain as recorded. Two observations from this review are added as debt and
do not block: D5 and D6.

The reviewer did not author or remediate this content. The review was read-only: the only file
written in the worktree is this report. Scratch files went to the session scratchpad, and
screenshots to the git-ignored `.playwright-mcp/d100/reqg/`.

## Reviewed identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\d100-ai-console-phase1-20261029` |
| Branch | `feat/d100-ai-console-phase1` |
| HEAD = base = origin/main | `8c7ea99cfb134a6edf2313f907fb913c4c21a1d6` (no commits) |
| Candidate (index) `git write-tree` | `e786c8bdea54aeb31cbcd5bdbf1714d907e9b188`. Checked at the start, after the build and before the verdict; it did not change. |
| Working tree vs index | Equal. Only the 5 staged paths, plus the untracked first-gate report. |
| Paths | `apps/frontend/src/pages/AiModelManagement.tsx` (M), `AiModelManagement.test.tsx` (M), `aiModels/ConsoleShell.tsx` (A), `aiModels/aiModelConsole.css` (A), `docs/integration/AI_MODEL_CONFIGURATION.md` (M) |
| Remediation delta | `git diff 405cc6d e786c8b`: 4 files, +139/−21. The doc did not change. |
| Change class | FRONTEND_UI |
| D-099 reference | `origin/feat/assistant-claude-sonnet-console` = `541b10f08961777e54447d995a1e90e66e93a269` |

## Per-finding verification

### M1: dialog focus return. Closed.

**Implementation.** `ConsoleShell.tsx:102-142`:

- The opener is read once into a ref.
- On cleanup, the restore is deferred with `setTimeout(0)` and goes through `restoreFocus`. That function uses the opener when it is connected and not `:disabled`; otherwise it uses the first usable fallback id.
- A re-run of the effect (StrictMode) cancels the pending timer.
- A backdrop `mousedown` calls `preventDefault()` only when `target === currentTarget`.
- Both dialogs pass `FOCUS_FALLBACKS = ["inspector-heading", "model-management-heading"]` (`AiModelManagement.tsx:858`). Both headings now have `tabIndex={-1}`, with no outline on focus.

**Browser evidence.** Vite dev server at 127.0.0.1:5179 (StrictMode), 1440×900, DSF 1, all `/api/**` mocked, and every non-GET left unanswered. This is MOCK evidence only.

| Scenario | Result |
|---|---|
| Paid dialog opened by keyboard, focus after 150 ms | the dialog |
| Escape | the opener ("Run qualification…") |
| Escape, then Enter immediately (no wait) | the dialog reopened and holds focus |
| Open and Cancel 3 times by mouse, then open | the dialog holds focus |
| Cancel click | the opener |
| Two dialogs in a row (paid Cancel, then Activate on another tile) | the activation dialog holds focus |
| Text selection inside the dialog | drag-select 110 chars and the label 213 chars; dialog stays open; label drag does not toggle the checkbox; checkbox click works |
| Backdrop press on the activation dialog | the opener ("Activate") |
| Activation Confirm (mouse), POST pending | opener disabled; focus `H2#inspector-heading` |
| Rollback Confirm by keyboard (Enter), POST pending | opener disabled; focus `H2#inspector-heading` |
| Paid Start from the inspector, POST pending | opener disabled; focus `H2#inspector-heading` |
| Paid Start from Qualifications & Recovery (no inspector), POST pending | opener disabled; focus `H1#model-management-heading` |
| `<body>` focused after a close | never |

Writes were exactly one deliberate POST per confirm step (`activate`, `rollback`, and `…/qualifications` twice). Escape, Cancel and backdrop sent none. There were no page errors.

The only unmatched GET is `/api/system/execution-profile`, a mock gap in the header badge.

**Adversarial.** A synthetic case closes and reopens the dialog in the same JS task (Escape `dispatchEvent`, then `opener.focus(); opener.click()`). The first dialog's deferred restore then moves focus to the opener behind the newly opened dialog. Because the key handler is on the dialog, Escape then does not close it.

A human cannot reach this: each input is a separate task, and the 0 ms timer fires first, which the "Escape then Enter immediately" case confirms. It is recorded as debt D5.

### M2: help text. Closed.

- `AiModelManagement.tsx:1065`: the Providers banner drops "Local models need no key". The remaining sentence is accurate, because `OpenRouterKey` renders only when `budget.configured`.
- `AiModelManagement.tsx:709`: "{n} listed by IT" became "{n} in total". `profiles.length` counts all configurations, including the environment baseline and the code-defined profiles, so "in total" is accurate.
- Neither old phrase remains in the code or in the doc.

### M3: badge accessible name. Closed.

**Implementation.** `ConsoleShell.tsx:80-84`. The visible text is `aria-hidden`, and a `.sr-only` element (defined globally in `design-system.css:486` and `styles.css:880`) carries ", label".

**Browser accessibility snapshot** (`ariaSnapshot()` of the nav list):

| Badge variant | Accessible name |
|---|---|
| No key | `Providers , no OpenRouter key is set` |
| Key invalid | `Providers , the OpenRouter key is not valid` |
| Stopped | `Spending & Limits , paid calls are stopped until an operator reconciles` |
| Calls refused | `Spending & Limits , paid calls are refused now` |
| Running | `Qualifications & Recovery , a qualification is running` |
| Count 1 | `Qualifications & Recovery , 1 needs attention` |
| Count 2 | `Qualifications & Recovery , 2 need attention` |
| No badge | `Models & Overview`, `Audit History` (plain) |

Each label matches the existing panel semantics:

- "Stopped" matches "(an operator must reconcile)" at `:388`.
- The credential statuses are `configured | missing | invalid` (`aiAssistant.ts:696`).

The stray space before the comma comes from the span boundary. It is cosmetic and harmless for speech.

### D1: inspector off-screen on desktop. Resolved.

**Implementation.** `aiModelConsole.css:158-160`: at `min-width: 901px` the inspector gets `position: sticky; top: 16px; max-height: calc(100vh - 32px); overflow-y: auto`. The page scroller is the document.

| Viewport | Measured |
|---|---|
| 1440×900 | Not internally scrollable (714 = 714). Tab through the inspector: all 4 actions focused and visible. After a wheel scroll and at the page end, the inspector is at 137..852 with all actions in the viewport. |
| 1440×700 | Scrollable (714/666). Tab: each focused action is visible, and Activate auto-scrolls into view at 558..595. A wheel over the inspector scrolls it (scrollTop 48). At the page end all 4 actions are in the viewport (273..547). |
| 1440×560 | Scrollable (714/526). Tab reaches and shows all 4 actions. A wheel scrolls the inspector to its maximum (187 of 188). At the page end all actions are visible. |
| 901×700 | Sticky; the same behaviour (Tab/wheel reach everything). |
| 900×700 and 360×740 | `position: static; max-height: none; overflow-y: visible`, so there is no effect at ≤900px. The existing scroll-into-view still applies. |

At the page end, the containing block pushes the inspector top to −16px. Only 16 of its 20 px top padding is hidden; content and actions are not clipped. This is cosmetic.

**360×740 overflow.** With badges present (No key / Stopped / 1) and the section menu open, `scrollWidth == 360` in all 5 sections. The first gate's broader 360 evidence (long names, expanded details, history traversal) concerns content the delta did not change, so it stays valid.

## Test quality (item 4)

The new test file was run against the pre-remediation sources: the 405cc6d versions of `AiModelManagement.tsx`, `ConsoleShell.tsx` and the CSS were extracted into a temp copy outside the repository, with a `node_modules` junction. The new tests behave as follows:

| Test | Against the 405cc6d sources | Notes |
|---|---|---|
| "moves focus to the inspector when a confirmed activation leaves its opener disabled (QG M1)" | **fails** | expected `''` to be `inspector-heading` |
| "cancels from the backdrop … keeps focus on the opener (QG M1)" | **fails** | `defaultPrevented` false |
| "gives each section badge words a screen reader can say (QG M3)" | **fails** | no aria-hidden/sr-only parts |
| "keeps focus in a dialog opened under StrictMode …" | passes | Expected: the 405cc6d restore was synchronous, so it had no StrictMode race. This test guards the new deferred design. |

To show that the StrictMode test is meaningful, a naive deferred variant was built (capture the opener on every effect run, no timer cancel). The StrictMode test **fails** against it and all others pass. So it catches exactly the regression that the remediation describes.

The Escape test's change from a synchronous `expect` to `await waitFor(() => expect(document.activeElement).toBe(activate))` is required by the deferred restore. It still asserts the exact element, so it is not weakened.

Count: 46 → 50 `it` blocks. No existing assertion was removed.

Coverage gap: the unit test covers only the count badge. The other variants are verified only in the browser (see above). This is acceptable; see D6.

## Regression re-check

| Item | Result |
|---|---|
| `aiAssistant.ts`, `navigation.tsx`, `App.tsx` | Not in the candidate diff (`git diff --cached --name-only`: the same 5 paths). |
| Query keys, `refetchInterval`, audit interval and invalidation, `retry:false` | The delta does not touch them (its hunks are imports, the summary note, the inspector heading, the fallback constant, badges, the h1, the banner and the dialog props). |
| Paid-run confirmation | Still only from `startPaid`; the browser shows no write until "Start paid qualification". |
| Acknowledgement gate | The Confirm disabled predicate is unchanged; the unit tests pass. |
| RBAC | Access tests pass unchanged; no route change. |
| Section URL / SPA traversal | Not touched by the delta. The first gate's evidence (0 writes on traversal) stays valid. |
| Contrast | No colour change in the delta. The first gate's evidence stays valid. |
| Security | No key value is rendered. No storage. The URL carries only the section enum. The badge labels are fixed strings. |

## Commands and results (tree e786c8b)

| Command | Result |
|---|---|
| `git write-tree` (start, after build, before verdict) | `e786c8bdea54…` each time |
| `npx vitest run src/pages/AiModelManagement.test.tsx` | 1 file, **50 passed** |
| `npm run typecheck` | exit 0 |
| `npm test` | **66 files / 1168 tests passed** |
| `npm run build` | exit 0. Pre-existing warning: one chunk is 1,144 kB, over 500 kB. Tracked status is unchanged afterwards. |
| `git diff --cached --check` | clean (the new files are staged, so they are covered) |
| `python -I scripts/check_secrets.py` | PASS |
| `python -I scripts/check_architecture.py` | PASS |
| `python -I scripts/check_project_state.py` | PASS |
| New tests vs 405cc6d sources (temp copy) | 3 failed (M1 ×2, M3), 47 passed |
| New tests vs naive deferred variant (temp copy) | 1 failed (StrictMode), 49 passed |
| Independent Playwright 1.56.1 script `reqg_browser.cjs`, plus `select_check.cjs` (both in the session scratchpad `reqg\`) | as above (MOCK only) |
| `pre_pr_check.py` | NOT run (no PR authorised) |

I inspected the implementer's `console_browser_check.cjs`: it uses the same mocks and its results are consistent with mine. I reused only its fixture data; every check in this report is my own.

## D-099 (#130) merge re-assessment

The three shared files were extracted as raw blobs with `git show`: base `8c7ea99`, candidate `e786c8b` and D-099 `541b10f`. `git merge-file` reported **0 conflicts** for:

- `AiModelManagement.tsx`
- `AiModelManagement.test.tsx`
- `AI_MODEL_CONFIGURATION.md`

A first attempt that used `git archive` output for "ours" showed spurious conflicts. They came from CRLF smudging, not from content; the raw blobs merge cleanly.

The merged files were placed in a temp copy of `apps/frontend` (a `git archive` of e786c8b plus a `node_modules` junction):

- Vitest: **52 passed** (50 + D-099's 2).
- `tsc -p tsconfig.app.json --noEmit`: exit 0.

D-099 does not touch `ConsoleShell.tsx` or the CSS.

Residual risk is low. Whichever PR lands second must re-run the focused test. D2 still applies to D-099's provider/thinking line.

## Remaining debt (not blocking)

- **D2** (open): RemoteDetails for non-active remote configurations appears only in the folded technical-details table.
- **D3** (open): no `inert` or scroll lock behind the `aria-modal` dialog.
- **D4** (open): "D-100" has no DECISION_LOG or planner entry. Record or reserve it before publication.
- **D5** (new, low): a deferred restore from a dialog that closed in the same task as another dialog opened can move focus out of the new dialog (`ConsoleShell.tsx:136-141`). It is not reachable by human input (verified above). A cheap guard would be to restore only when `document.activeElement` is `body`/null or was inside the closed dialog.
- **D6** (new, low): the unit tests cover only the count badge. Key, spending and Running labels are verified in the browser only.

## Verdict

**PASS** for tree `e786c8bdea54aeb31cbcd5bdbf1714d907e9b188`.

M1 to M3 are closed and D1 is resolved. No required fix remains. If the content changes, this verdict lapses.

This gate authorises no commit, push or PR. Publication still requires explicit owner authorisation and the pre-PR gate on a committed state.
