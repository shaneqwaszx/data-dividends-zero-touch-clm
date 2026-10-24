# UI Enhancement v1 Integration — Independent Stage 3 Re-Quality Gate 2 (R-1 remediation)

## 1. Executive result

**Verdict: PASS**

The delta `d5e5864..9151807` resolves R-1. On a touch tap, the press now ends on the
tap's `click` (window capture) instead of on `pointerup`. The compatibility
`mousedown`/focus therefore still sees the press, the page does not move, and the tap
lands. The mouse fix is unchanged: a mouse press still ends on `pointerup`. Keyboard,
programmatic and click-handler focus keep the approved D2 alignment, because the
window-capture release runs before React's click handlers. N-3 is resolved by the
1000 ms fallback. Unmounting during a press now removes its listeners and timer, which
`d5e5864` did not do. N-4 is now stated accurately in the comment.

No Critical, High, Medium or Low findings. There are three informational notes
(N-5 to N-7, §4). None requires a fix before publication.

This verdict covers only the content in §2. It does not authorize a push, PR or merge.
A renewed complete official browser run on `9151807` is still required before
publication (§7).

## 2. Reviewed content identity

| Item | Value |
|---|---|
| Commit | `91518076889a3b06daadbe21d35b64d3f773ec4b` (verified) |
| Tree | `ce8254d878ad49380d01e48746f7fe2f4a9fce32` (verified) |
| Parent | `d5e5864d0ed2bc24a2ebfad584d830813835d9c6` (verified; previously gated FAIL, Low R-1) |
| Integration branch | `integration/ui-enhancement-v1-main-20261023` → `9151807` (verified) |
| Base `origin/main` | `98b08d5c42e6850a66275c5c470112a9fea3c47e`, from both the local ref and `git ls-remote origin refs/heads/main`; unchanged during the gate |
| Gate checkout | worktree branch `claude/reqg2-ui-enhancement-v1-9151807-972b7c`; HEAD and tree identical; clean |
| Delta | 1 commit, 3 files, +112/−26: `apps/frontend/src/pages/StageDisclosure.tsx`, `apps/frontend/src/pages/StageDisclosure.test.tsx`, `apps/frontend/e2e/blocker-review-performance.e2e.ts` |
| Diff identity | `sha256(git diff d5e5864 9151807)` prefix `47b19d318a21338d`; `sha256(git diff 98b08d5 9151807)` prefix `644bf1abc671bab4` |

Read for this gate: `AGENTS.md`, `apps/frontend/AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`
(the evidence reuse and invalidation rules), `.agents/skills/fyp-quality-gate/SKILL.md`,
the previous re-QG on `d5e5864` (FAIL, R-1, N-3, N-4), the full delta and commit
message, and the complete `PersistentStageDisclosure`. I also searched
`apps/frontend/src` for other pointer-press handling. The only other one is
`CaseDetail.tsx:1386` `recordOwnershipInteraction`, which records interaction only and
does not touch the press mark. There are 8 non-test `<StageDisclosure` render sites.
Change class: `FRONTEND_UI`. The shared notes folder was empty.

## 3. Acceptance checklist

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | R-1 resolved for touch: a sliver tap on a control under the stuck header lands and the page does not move | PASS | Probe (§6), touch at 390 and 1280 px. `d5e5864`: 10 and 30 px button slivers → `clicked: 0`, page moves −42/−22 px; 6 px radio → page moves −19 px. `9151807`: `clicked: 1` and `scrollMoved: 0` in every case. Event order with the fix: `pointerdown → pointerup → mousedown → focusin → mouseup → click`, all on the target. Official browser test `blocker-review-performance:286` (`hasTouch`, 390/1280 px) passes on clean `9151807`. |
| 2 | Pen: the press ends on `click` | PASS (note N-6) | Pen through CDP (`pointerType: "pen"`) at 390/1280 px: clicked, no page movement. Chromium dispatches pen in mouse order (`mousedown`/focus before `pointerup`), and ending on `click` is correct for both orders. Unit tests cover pen in touch order. |
| 3 | Mouse fix kept: the press ends on `pointerup` | PASS | Mouse button and radio slivers at 390/1280 px: clicked, `scrollMoved: 0` in both versions. A 1.3 s mouse hold on a sliver still lands, because focus happens at `mousedown`, before the fallback fires. |
| 4 | D2 kept for keyboard, programmatic and click-handler focus | PASS | `shift-tab`, `programmatic-focus`, and `click-handler-focus` (mouse **and touch** taps on a visible button whose `onClick` focuses a covered input) → `aligned: true` in all contexts. This shows the window-capture `click` release runs before React's `onClick`. A tap on plain text that focuses nothing, followed by programmatic focus → aligned, with no listener or timer left behind. |
| 5 | N-3 handled by the bounded 1000 ms fallback | PASS (resolved) | A synthetic press with no release (`mouse`/`touch`/`pen`): focus is not aligned inside the window, and is aligned after 1100 ms. Window listeners return to baseline (`d5e5864`: still unaligned, with listeners left registered). Unit test with fake timers: 999 ms not aligned, 1000 ms aligned. |
| 6 | No listener or timer leak; a new press ends the previous one; unmount mid-press | PASS | Using CDP `DOMDebugger.getEventListeners(window)` and a counter of pending 1000 ms timers: after every completed press, listeners are back at baseline and no fallback timer is pending. With three presses in a row, only one listener set and one timer are live (`d5e5864`: three sets), and all are gone after release. Unmount mid-press: listeners back to baseline and no timer pending (`d5e5864`: listeners left registered). The `release` closure refers to `fallback` only after it is initialised; it is never called before `trackPointerPress` returns. |
| 7 | Taps that never produce a click | PASS (note N-5) | A touch scroll gesture that starts on the covered control produces `pointerdown → pointercancel`. The press ends, the listeners and timer are released, and later programmatic focus is aligned. A press whose click never arrives is bounded at 1 s. No `contextmenu` was observed in emulation. A touch hold of 1 s or longer: see N-5. |
| 8 | Comment accuracy, including N-4 | PASS (note N-6) | The label sentence matches the observed behavior: a label-text tap or click is still aligned (−29 px) and the activation is not lost. The constant's doc comment and the unmount comment are accurate. The pen ordering clause overgeneralizes (N-6). |
| 9 | New tests discriminate | PASS | Unit: the new `StageDisclosure.test.tsx` was run against the `d5e5864` component (exported scratch copy, blob `ae74459` verified). The touch, pen and fallback cases **fail** (3 failures: `expected 1 to be +0`, `expected 1 to be +0`, `expected +0 to be 1`). The mouse case passes on both versions, as it should. Browser: the reused `r1-without-fix.json` shows `:286` failing with `ASSERTION_FAILURE` on the `d5e5864` StageDisclosure. My probe confirms the mechanism: on `d5e5864` a touch tap on a radio sliver still checks the radio but moves the page −19 px, so the test's `scrollY` assertion fails. |
| 10 | No regression in other `StageDisclosure` consumers | PASS (focused) | Full Vitest 62 files / 1046 passed, typecheck, and a 20-selector official browser run with 20/20 PASS (§6). |
| 11 | Hygiene, secrets, scope | PASS | `git diff --check` is clean for the delta and the full range. All 3 files are LF in the index. The only credential-like added lines use `process.env.CLM_E2E_PASSWORD` and the response `csrf_token`, the same pattern as the existing login. No out-of-scope change. |

## 4. Findings and prior-finding dispositions

### Prior findings

| ID | Origin | Disposition |
|---|---|---|
| F-1 | `fb7d4bc` gate (Low): sticky alignment ran for pointer-initiated focus and lost clicks | **Resolved** for mouse (`d5e5864`, unchanged here) and for touch and pen (`9151807`). |
| R-1 | `d5e5864` re-QG (Low): touch taps still lost because `pointerup` comes before the compatibility `mousedown`/focus | **Resolved.** Touch and pen presses end on window-capture `click`. Shown by the probe, by the unit tests (which fail on `d5e5864`), and by the browser test `:286`. |
| N-3 | `d5e5864` re-QG (Info): a press whose release never arrives suppressed alignment indefinitely | **Resolved.** The suppression now lasts at most 1000 ms from `pointerdown`. Unit test and probe. |
| N-4 | `d5e5864` re-QG (Info): focus passed on by a label is still aligned | **Accepted and documented.** Behavior unchanged (−29 px, activation not lost). The comment now states it accurately. |

### New notes (informational; no fix required for this gate)

**N-5 — Info — the fallback is timed from `pointerdown`, so a touch tap held for 1 s or longer behaves as before the fix.**
`StageDisclosure.tsx:173` starts the 1000 ms timer at `pointerdown`. Under touch, focus
arrives only after `pointerup`. In a hold sweep in emulated Chromium (390 px, 10 px
sliver, a fresh context per hold), holds of 100, 300, 450, 600, 800 and 950 ms all land
with no page movement. Holds of 1100, 1300 and 2000 ms are aligned: the page moves
−42 px and the click goes to the ancestor, exactly as on `d5e5864`. This fails safe: the
tap is lost, nothing false happens, and it is no worse than the parent. Real devices
usually turn a hold this long into a long-press gesture with no `click`. A possible
later refinement is to restart the fallback at `pointerup` for non-mouse presses. One
anomaly: in the main probe, a 600 ms hold run in a context *reused* after a scroll
gesture produced no `click` at all, and the press stayed bounded by the fallback. The
fresh-context sweep did not reproduce that, and I treat it as emulator gesture state.

**N-6 — Info — the comment's pen ordering is platform-dependent.**
`StageDisclosure.tsx:163-165` says touch and pen move focus with the compatibility
`mousedown` that follows `pointerup`. Chromium dispatches CDP pen input in mouse order
(`pointerdown → mousedown → focusin → pointerup → mouseup → click`). The behavior is
correct either way, because `click` follows both orders. Only the wording
overgeneralizes, and the pen unit test exercises only the touch-like order.

**N-7 — Info — some lifecycle paths are covered by the probe only.**
No unit or browser test covers a new press replacing an earlier one, unmount during a
press, or `pointercancel` on a touch press. This gate's probe verifies all three (§3
rows 6 and 7). This is optional coverage, not a defect.

## 5. Code, architecture and security review

- The change is local to `PersistentStageDisclosure`: one module constant, one ref
  (`endPointerPress`), one unmount effect, and a per-press listener set chosen by
  `pointerType`. There is no new state owner, query, cache, mutation, navigation, or
  persisted or URL state. `LegacyStageDisclosure` is untouched.
- Add and remove use the same function, the same `ends` array and `capture: true`, and
  `release` also clears the timer and the ref, so it is idempotent. A new press first
  ends any earlier press in the same section. Sections track presses independently.
- An unknown or empty `pointerType` falls to the click path, which is bounded by the
  fallback.
- Security: this is presentation and focus only. Nothing changes in auth/RBAC, session,
  CSRF, logging, providers, TLS, persistence, URLs or browser storage. Added lines contain
  no credentials, URIs, payloads or KYC data.

## 6. Evidence: reused vs rerun

**Reused (identity checked):**
- `r1-without-fix.json`: dirty scratch `85fdd5b`/`d82f1f6`, `origin_main: null`, 1
  selected (`blocker-review-performance:286`), `ASSERTION_FAILURE`, `complete: false`.
  Used as discrimination evidence only. The failing assertion text is not recorded, and
  my probe and the unit discrimination below corroborate it.
- `r1-with-fix-results.json` (18/18 PASS) and `r1-with-fix-s3.json` (2/2 PASS): recorded
  on `d5e5864`/`8f4e7c6` with `dirty: true`. I cannot bind them to tree `ce8254d`, so
  they are treated as history and replaced by my clean run below.
- The previous gate's probe harness (`run.cjs`, `entry.tsx`) was adapted, not reused as
  evidence.

**Rerun independently on the clean `9151807` checkout** (`npm ci` into the ignored
`node_modules`; probe and discrimination output in scratch):

| Check | Result |
|---|---|
| `npm run typecheck` | PASS (exit 0) |
| `vitest run src/pages/StageDisclosure.test.tsx` | 25/25 PASS |
| `vitest run` (full suite) | 62 files / **1046 passed** (1043 on `d5e5864` + 3 net new) |
| Unit discrimination: `9151807` test file against the `d5e5864` component | 22 passed, **3 failed** (touch, pen, fallback), as expected |
| `git diff --check` (delta and full range) | clean |
| Official `run_e2e.py --selectors-file`, 20 selectors, ports 18991+/15991+, `--keep-going` | **20/20 PASS**, `complete: true`, 307.8 s, identity `9151807`/`ce8254d`/`98b08d5`, `dirty: false`, 114 discovered. Selectors: `authenticated-zero-touch` :242/:864/:1044/:1294, `blocker-review-performance` :167/:171/:175/:179/:286, `ux-refinement:45`, `slice-c-recovery` :123/:156, `s1-workspace-session:123`, `s3-sandbox-submission` :254/:257, `blocker-simulation:386`, `responsive-layout:807`, `am-wave1:167`, `garden-happy-path:218`, `performance-browser:137`. Results file sha256 prefix `c07032ab84e6e3a1` (`reqg2-e2e-results-9151807.json` in this gate's scratchpad) |
| Standalone Chromium probe: the real `StageDisclosure` from `d5e5864` vs `9151807`, bundled with esbuild + `src/design-system.css` (only the Google Fonts `@import` removed); Chromium 141.0.7390.37; mouse and `hasTouch` contexts at 390×844 and 1280×900; CDP listener and timer accounting | 180 scenario results (90 per version); outcomes in §3 |
| Touch hold sweep, 9 holds × 2 versions, fresh context each | Fix lands for holds under 1 s and is lost at 1.1 s or more; `d5e5864` is lost at every hold (N-5) |

Probe artefacts (outside the repo), under
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane-Desktop-FYP-data-dividends-zero-touch-clm--claude-worktrees-reqg2-ui-enhancement-v1-9151807-972b7c\6ba75994-df22-40f5-80b5-efd869100e1a\scratchpad\probe\`:
`results.json`, `sweep.json`, drivers `run.cjs` and `sweep.cjs`, `entry.tsx`, and bundles
`out-prev`/`out-fix`.

Not run: the complete 114-selector suite (excluded by the assignment), backend pytest,
physical Mongo (no backend or persistence change), and `pre_pr_check.py` (reserved).

## 7. Is a renewed complete official browser run required before publication?

**Yes.** `StageDisclosure` is a shared owner that renders every case-page stage section,
and every pointer interaction inside a section goes through the changed press path. The
last complete run (113/113 on `fb7d4bc`) does not cover `d5e5864` or `9151807`, and the
suite now discovers 114 selectors. Under the workflow's invalidation rule, the complete
applicable set must be rerun once on `9151807` (or on the final candidate, if anything
else changes) before Stage 4. That run is execution evidence for the content reviewed
here, not a new review, unless it forces a change.

## 8. Change statements

| Area | Changed? |
|---|---|
| API / browser types | No |
| Schema / persistence | No |
| Connectors / providers / provider status | No |
| Configuration | No |
| Business rules | No |
| Mappings | No |
| Auth / security | No |
| Architecture / owners | No |
| Runtime behavior | Yes, frontend only. Inside a stage section, focus that a touch or pen press gives a control is no longer aligned below the sticky header until the tap's `click`. Mouse presses still end on `pointerup`. Any press also ends on `pointercancel`, after 1000 ms, when a new press starts, or on unmount. Test-only additions in Vitest and E2E. |

## 9. Readiness

The UI integration content at `9151807` passes Stage 3. Before Stage 4 publication:
(1) one renewed complete official browser run on `9151807` (§7); then (2) the
`integration-safe-development` pre-PR checks on that exact committed state; and (3)
explicit owner authorization for any push or PR. Humans merge. N-5 and N-6 are optional
follow-ups that the owner may take or decline. Live ACRA and real GoldTier readiness are
unaffected and not claimed.

## 10. Git status

The gate worktree is on `claude/reqg2-ui-enhancement-v1-9151807-972b7c` at `9151807`, with
no staged or tracked modifications. The only file written in the repository is this
report (untracked). The only ignored local artefact is `apps/frontend/node_modules`
(`npm ci`). The discrimination copy lives in scratch, with a junction to that
`node_modules`. No fix, commit, push, PR, merge, rebase, reset, clean or stash was
performed. No Mongo, `clm_poc` or `.env` access. No other worktree was modified.
