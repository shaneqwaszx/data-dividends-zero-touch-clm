# UI Enhancement v1 Integration — Independent Stage 3 Re-Quality Gate (F-1 remediation)

## 1. Executive result

**Verdict: FAIL**

The delta `fb7d4bc..d5e5864` resolves F-1 for **mouse** input: a click on the visible
sliver of a control mostly under a stuck section header now lands, and the page does not
move. Keyboard and programmatic focus keep the approved D2 alignment. Nothing that uses
`StageDisclosure` regressed in any check this gate ran.

F-1 is **not resolved for touch** input, which the finding names explicitly ("mouse/touch
click") and which the commit message says is fixed ("a mouse press or tap"). On a touch
tap the browser fires `pointerup` *before* the compatibility `mousedown`/focus. The new
`pointerPressed` mark is therefore already clear when focus arrives, the alignment
scrolls the page, and `mouseup`/`click` land on the surrounding element. The tap is lost
exactly as before (finding R-1). Neither the new unit test nor the new browser check uses
touch, so the remediation's evidence cannot detect this.

Severity stays **Low** and fail-safe: no action fires, nothing falsely succeeds, the user
taps again. On touch, `d5e5864` behaves exactly like the already-gated `fb7d4bc`, and it
is strictly better for mouse. The verdict is FAIL because the remediation's acceptance
criterion (resolve F-1, including touch) is unmet and the delta claims a tap fix that
does not exist. It is not FAIL because of a safety regression. The owner can either send
the touch path back to bounded remediation, or explicitly accept touch as a residual
limitation and correct the claim. That decision belongs to the owner, not this gate.

This verdict covers only the content below. It authorizes no push, PR or merge.

## 2. Reviewed content identity

| Item | Value |
|---|---|
| Commit | `d5e5864d0ed2bc24a2ebfad584d830813835d9c6` (verified) |
| Tree | `8f4e7c6d8191d5064c1cc92ad7565c5d0dfe40ff` (verified) |
| Parent | `fb7d4bc5a77ab8865f8bd504faaac59890af6331` (verified; previously gated PASS + Low F-1) |
| Integration branch | `integration/ui-enhancement-v1-main-20261023` → `d5e5864` (verified) |
| Base `origin/main` | `98b08d5c42e6850a66275c5c470112a9fea3c47e` (local ref and `git ls-remote origin refs/heads/main` both; unchanged during the gate) |
| Gate checkout | worktree branch `claude/reqg-ui-enhancement-v1-d5e5864-72f917`, HEAD/tree identical, clean |
| Delta | 1 commit, 3 files, +52/−1: `apps/frontend/src/pages/StageDisclosure.tsx`, `apps/frontend/src/pages/StageDisclosure.test.tsx`, `apps/frontend/e2e/blocker-review-performance.e2e.ts` |
| Range diff identity | `sha256(git diff 98b08d5..d5e5864)` prefix `46431d4cf2c1738c` |

Read: `AGENTS.md`, `apps/frontend/AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md` (change-class
matrix, evidence reuse/invalidation), `.agents/skills/fyp-quality-gate/SKILL.md`, the prior
gate report on `fb7d4bc`, the full `StageDisclosure.tsx`, both changed tests, and every
`onPointerDown`/`onMouseDown`/`preventScroll` site under `apps/frontend/src`. Change class:
`FRONTEND_UI`. The shared notes folder was empty.

## 3. Acceptance checklist

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | F-1 resolved for mouse: sliver click on a control under the stuck header registers, page does not jump | PASS | Probe (§7): new code at 390/1280 px, 10 px and 30 px slivers → `clicked: 1`, `scrollMoved: 0`. Old code → `clicked: 0`, page jumps −42/−22 px. Event order with the fix: `pointerdown → mousedown → focusin → pointerup → mouseup → click`, all on the target. Official browser check `blocker-review-performance:168` PASS on clean `d5e5864`. |
| 2 | F-1 resolved for touch (F-1 title and failure scenario say "mouse/touch"; commit claims "press or tap") | **FAIL** — R-1 | Probe: new code with `hasTouch` at 390 and 1280 px, 10/30 px slivers → `clicked: 0`, page jumps −42/−22 px, identical to old code. Event order: `pointerdown → pointerup → mousedown → focusin → mouseup:DIV → click:DIV`. |
| 3 | D2 kept: keyboard focus under the header aligned just below it | PASS | Probe Shift+Tab: old and new both `aligned: true` (control top 133 px vs header bottom 121 px). Existing Shift+Tab browser check (`:168`) PASS. |
| 4 | D2 kept: programmatic focus, including focus from a later click handler ("Focus editable KYC and segment" pattern) | PASS | Probe `programmatic-focus` and `click-handler-focus` (mouse click on a visible button whose `onClick` focuses a covered input) → `aligned: true` in both versions. The window-capture `pointerup` release runs before `click`, so click-handler focus is aligned. |
| 5 | Press lifecycle: release outside the section, `pointercancel`, multiple presses, unmount | PASS (note N-3) | Probe: press inside, release outside, then focus → aligned. Synthetic `pointercancel` → aligned. Multiple presses: every registered `release` runs on the first `pointerup`, and each removes its own listener pair (same `capture: true`), so nothing accumulates. Unmount mid-press: the listener pair stays until the next `pointerup` and touches only a ref (no state update, no error). A press that never ends leaves alignment off until the next release anywhere (N-3). |
| 6 | Header/toggle focus paths (scope reset, print restore, toggle restore) unaffected | PASS | Those focus targets are inside `h2`; `header.contains(target)` already skipped them, and the new guard only adds a skip. `restoreFocus` targets a `summary` that the press itself already focused. |
| 7 | New tests genuinely discriminate | PASS for mouse, no touch coverage (R-1) | Unit test: without the guard the first `focus()` scrolls (`scrolls === 1`, expected 0), and the second half proves release re-enables alignment. It dispatches `pointerdown` before `focus()`, which is mouse ordering only. Browser check: even where the radio still gets checked without the fix (as in the probe), the `scrollY` equality assertion fails, so it discriminates. Reused `f1-without-fix.json` records `ASSERTION_FAILURE` on `:168` (no assertion text recorded; corroborated by the probe). `page.mouse.click` only, no touch. |
| 8 | No regression in other `StageDisclosure` consumers | PASS (focused) | Full Vitest 1043/1043, typecheck, build, and 19-selector official browser run (§7). |
| 9 | Hygiene, secrets, scope | PASS | `git diff --check` clean for the delta and for `98b08d5..d5e5864`; LF in index for all 3 files; no secret-pattern hits in added lines; no out-of-scope change. |

## 4. Findings (most severe first)

### R-1 — Low — F-1 persists for touch taps; the remediation claims a tap fix it does not deliver

- **Where:** `apps/frontend/src/pages/StageDisclosure.tsx:152-162` (`trackPointerPress`
  clears the mark on `pointerup`) together with `:147-151` and `:168` (alignment on focus).
  The comment at `:145-146` and the commit message state that tap/pointer-press focus is
  left alone.
- **Defect:** under touch, the Pointer Events/compatibility model dispatches
  `pointerdown`, then `pointerup`, and only then the compatibility `mousedown`, during
  which focus moves, then `mouseup` and `click`. The mark is cleared on `pointerup`, so
  the focus that follows is treated as non-pointer focus and aligned. The instant scroll
  moves the control out from under the finger, Chromium hit-tests `mouseup` again, and
  `click` goes to the common ancestor.
- **Failure scenario:** on a phone (390 px), a reviewer scrolls so that "Save target
  classification" (or any button) sits mostly under the stuck "Document verification"
  header and taps its visible 10–30 px sliver. The page jumps 22–42 px and the button's
  click does not fire. Reproduced with the real `d5e5864` `StageDisclosure` and app CSS,
  Chromium 141, Playwright `touchscreen.tap`, at 390 and 1280 px (§7). Same outcome on
  `fb7d4bc`.
- **Impact:** fail-safe (lost tap, no false action), identical to the accepted-as-Low F-1
  on touch, no worse than `fb7d4bc`. It does leave a stated remediation goal unmet, and
  the commit and comment claim behavior the code lacks.
- **Remediation direction (not implemented by this gate):** keep the mark for non-mouse
  pointers until the compatibility `click`/`mouseup` (or a short bounded window) has
  passed, for example by recording `event.pointerType` and releasing touch/pen presses
  on `click` capture instead of `pointerup`, with a bounded fallback. Add a touch case to
  the unit test (pointerdown → pointerup → focus) and a `hasTouch` tap variant of the
  sliver browser check. Pen was not exercised by this gate (its compatibility ordering is
  platform-dependent), so any fix should cover it by `pointerType` rather than assume
  mouse ordering.

### N-3 — Informational — a press whose release is never delivered suppresses alignment until the next release

If neither `pointerup` nor `pointercancel` reaches the window (for example a context menu
that swallows the release on some platforms, or a blocking dialog during the press),
keyboard and programmatic focus in that section are left at the browser default until
the next pointer release anywhere. Probe `lost-release-then-focus`: new → `aligned: false`,
old → `aligned: true`. It fails safe (pre-D2 browser behavior, never a lost action),
clears itself on the next release, and its listener pair is then removed.

### N-4 — Informational — focus that arrives via a label still aligns, after the click

Tapping or clicking the label text of a covered radio focuses the input during the
label's activation, after `pointerup`, so the page still jumps (−29 px in both versions).
The activation is not lost (`checked: true`), because the synthetic click targets the
input directly. This is cosmetic only, but it is a second case where the comment's "focus
from a pointer press is left alone" does not hold.

Prior N-1/N-2 (on `fb7d4bc`) are unchanged by this delta and not re-litigated.

No Critical, High or Medium findings.

## 5. Code and architecture review

- The change is local to `PersistentStageDisclosure`: one ref, one capture handler, and
  window listeners scoped to a single press. No new state owner, query, cache, mutation or
  navigation path. `LegacyStageDisclosure` is untouched.
- Listener hygiene is correct for mouse: add and remove use the same function and
  `capture: true`, both events are removed together, and a release outside the section or
  window-level `pointercancel` is handled.
- Focus stealing on `pointerdown`/`mousedown` exists nowhere else in `apps/frontend/src`.
  `CaseDetail`'s `recordOwnershipInteraction` capture handlers only record interaction
  and do not interact with the mark.
- `focusActionControl`/`focusProcessingNode` run from click or keyboard handlers after
  release, so their alignment and own final scroll are unchanged.

## 6. Security review

Presentation and focus only. No auth/RBAC, session, CSRF, logging, provider, TLS,
persistence, URL or browser-storage change. Added lines contain no credentials, tokens,
URIs, payloads or KYC data.

## 7. Evidence: reused vs rerun

**Reused (identity checked):**
- `f1-without-fix.json`: dirty scratch `85fdd5b`/`d82f1f6`, 1 selected
  (`blocker-review-performance:168`), `ASSERTION_FAILURE`. Discrimination evidence only;
  the failing assertion is not recorded, and my probe corroborates the mechanism.
- `f1-with-fix-results.json`: `fb7d4bc`/`50db1a9` `dirty: true`, origin `98b08d5`, 16/16
  PASS, `complete: true`, `keep_going: true`. Recorded on the uncommitted fix; superseded
  for this gate by my own clean run below, so treated as history.
- `stage2b-e2e-results-fb7d4bc.json` (113/113 on `fb7d4bc`): does **not** cover `d5e5864`
  and is not counted as evidence for it.

**Rerun independently on the clean `d5e5864` checkout** (`npm ci` into ignored
`node_modules`; build output to scratch):

| Check | Result |
|---|---|
| `npm run typecheck` | PASS (exit 0) |
| `vitest run src/pages/StageDisclosure.test.tsx` | 22/22 PASS |
| `vitest run` (full) | 62 files / **1043 passed** (1042 on `fb7d4bc` + 1 new) |
| `vite build --outDir <scratch>` | PASS (existing >500 kB chunk warning only) |
| `git diff --check` (delta and full range) | clean |
| Official `run_e2e.py --selectors-file`, 19 selectors, ports 18971/15971, `--keep-going` | **19/19 PASS**, `complete: true`, 305 s, identity `d5e5864`/`8f4e7c6`/`98b08d5`, `dirty: false`; selectors: `authenticated-zero-touch` :242/:864/:1044/:1294, `blocker-review-performance` :156/:160/:164/:168, `ux-refinement:45`, `slice-c-recovery` :123/:156, `s1-workspace-session:123`, `s3-sandbox-submission` :254/:257, `blocker-simulation:386`, `responsive-layout:807`, `am-wave1:167`, `garden-happy-path:218`, `performance-browser:137`; results sha256 prefix `7115758500963db4` (`reqg-e2e-results-d5e5864.json` in this gate's scratchpad) |
| Standalone Chromium probe: real `StageDisclosure` from `fb7d4bc` vs `d5e5864` bundled with esbuild + `design-system.css` (only the Google Fonts `@import` removed), Chromium 141.0.7390.37, mouse and `hasTouch` contexts at 390×844 and 1280×900 | 56 scenario results: mouse F-1 fixed; touch F-1 persists (R-1); keyboard, programmatic and click-handler alignment kept; N-3/N-4 observed |

Probe artefacts (outside the repo):
`C:\Users\shane\AppData\Local\Temp\claude\C--Users-shane-Desktop-FYP-data-dividends-zero-touch-clm--claude-worktrees-reqg-ui-enhancement-v1-d5e5864-72f917\6335854c-915d-462d-b5eb-e200335f65bb\scratchpad\probe\results.json`
(driver `run.cjs`, entry `entry.tsx`, bundles `out-old`/`out-new`).

Not run: complete 113-selector suite (excluded by assignment), backend pytest, physical
Mongo (no backend or persistence change), `pre_pr_check.py` (reserved).

**Is a renewed complete official browser run required?** Yes, before the next
publication candidate. `StageDisclosure` is a shared owner that renders every case-page
stage section, and every Playwright click inside a section now takes the changed path (no
alignment scroll during the press). Under the workflow's invalidation rule ("rerun the
complete applicable set when it touches a shared owner … or its impact cannot be safely
bounded"), the 113/113 `fb7d4bc` run no longer covers the candidate. The focused 19-selector
run here bounds the most likely consumers but does not replace that run. Run it once, on
the final candidate after R-1 is remediated or explicitly accepted, not on `d5e5864`
alone.

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
| Runtime behavior | Yes, frontend only: focus received during a pointer press inside a stage section is no longer aligned below the sticky header (effective for mouse; not for touch, R-1). Test-only additions in Vitest and E2E. |

## 9. Readiness

Not ready for Stage 4 on this gate. Next authorized action belongs to the owner: either
(a) bounded remediation of R-1 (touch/pen path plus touch test coverage, and correct the
comment), followed by a fresh independent re-QG of that delta and one renewed complete
official browser run on the final candidate; or (b) explicitly accept touch as a residual
Low limitation, correct the inaccurate "tap" claim, and then re-gate that change. Live
ACRA and real GoldTier readiness are unaffected and not claimed.

## 10. Git status

Gate worktree on `claude/reqg-ui-enhancement-v1-d5e5864-72f917` at `d5e5864`, with no
staged or tracked modifications. The only file written in the repository is this report
(untracked). Ignored local artefacts from the checks: `apps/frontend/node_modules`
(`npm ci`) and any runner temp output. No fix, commit, push, PR, merge, rebase, reset,
clean or stash was performed. No Mongo, `clm_poc` or `.env` access. No other worktree was
modified.
