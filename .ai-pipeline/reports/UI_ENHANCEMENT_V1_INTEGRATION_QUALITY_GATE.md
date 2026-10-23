# UI Enhancement v1 Integration — Independent Stage 3 Quality Gate

## 1. Executive result

**Verdict: PASS**

The frozen candidate implements the owner-approved teammate redesign (single
"GoldTier Details & Status" section, 10-step visual rail over the 12 unchanged backend
stages) with safeguards A–C, the approved removal of the case-explanation panel and its
dependent E2E steps, and remediation D1–D3. Every focus area was verified in code and
tests and by execution. No backend, API, schema, authorization or runtime-provider change
exists. One Low, non-blocking side effect of D2 was found and reproduced (F-1): it fails
safe (a lost click, never a false action) and does not affect the keyboard/programmatic
focus behavior D2 was approved for. Two informational test-coverage notes are recorded.
No required fix remains.

This verdict applies only to the reviewed content below. It does not authorize push, PR or
merge; publication needs separate owner authorization, and humans merge.

## 2. Reviewed content identity

| Item | Value |
|---|---|
| Commit | `fb7d4bc5a77ab8865f8bd504faaac59890af6331` |
| Tree | `50db1a9f3a48d75a9a2c781ae86d553514ca7212` |
| Integration branch | `integration/ui-enhancement-v1-main-20261023` → `fb7d4bc` (verified) |
| Gate checkout | worktree branch `claude/qg-ui-enhancement-v1-fb7d4bc-91a9ba`, HEAD/tree identical, clean |
| Base `origin/main` | `98b08d5c42e6850a66275c5c470112a9fea3c47e` (unchanged during the gate) |
| Range | `98b08d5..fb7d4bc`, 9 commits, 64 paths, +2072/−601 |
| Range diff identity | `sha256(git diff 98b08d5..fb7d4bc)` prefix `a260370a90d8c460` |

Commits `a62b4a4`…`c94785e` were already independently gated (commit `0333ac8` records
resolution of that gate's findings on `52b631d`). This gate reviewed the whole range for
integration and regression risk and concentrated on the post-gate delta: `0333ac8`,
`ec59972`, `1568913` (both superseded in net effect by `53ce015`), `53ce015` and `fb7d4bc`.

Read: `AGENTS.md`, `apps/frontend/AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`,
`.agents/skills/fyp-quality-gate` (+ report template), `docs/integration/FRONTEND_UX_REFINEMENT.md`,
all changed source/tests in the focus areas, and the relevant backend projection
(`apps/backend/app/api_models.py` `project_human_interventions`, `INITIAL_IDENTITY` node).
Change classes: `FRONTEND_UI` (primary), assistant text/test, `DOCS_ONLY`; D3 is an E2E
methodology change.

## 3. Acceptance checklist

| # | Requirement | Result | Evidence |
|---|---|---|---|
| 1 | Case-explanation panel removed without concealed functional loss | PASS | Backend projects one intervention per active exception except `TARGET_CONFIRMATION_REQUIRED` (`api_models.py:902-905`), so every exception explanation and decision detail still renders in Action required (`HumanInterventionPanel`); historical exceptions keep their own list; readiness blockers/warnings, policy version and target operations remain in the section's More/Technical details; technical failure keeps its banner (`CaseDetail.tsx:1392`); party ID remains (`CaseDetail.tsx:1754`, `CompletedOverview`); "not approval" disclaimer remains in the section note. `#case-evidence-recovery` now wraps the status tiles; recovery navigation still prefers `#case-target-recovery` (`CaseDetail.tsx:931`). |
| 1a | Removed "Focus registry evidence" E2E steps | PASS (coverage note N-1) | Steps only exercised the removed panel's buttons. Document decision step now reached through the rail with `focusPipelineAction(page, "DOCUMENT_IDP", …)` — a stronger check (visible, enabled, focused, in viewport, unobscured, zero mutations). |
| 2 | Changed E2E/unit assertions match the 10/11-step contract | PASS | 10 steps normal (`s1` stage list, `performance-browser` `ready`), 11 with identity exception (`ux-refinement` + `data-node-id` checks), backend still 12 (`ux-refinement`, `slice-c-recovery`, `performance-browser`); `slice-c-recovery` progress recomputed from the step mapping and asserted on both `aria-valuenow` and "N of M stages done"; `s3`/`slice-c` rebind via `GOLDTIER_DETAILS`; problem-pipeline grouped step still expects `#case-target-blocker` (READINESS not attention, GOLDTIER_TARGET BLOCKED → single member → `processingNodeFocusTarget` → `case-target-blocker`). Remaining E2E edits are mechanical section renames. |
| 3 | Safeguard A — Initial identity visible whenever it needs attention | PASS | `businessStagePipeline` keeps it unless done and no retained `INITIAL_IDENTITY_*` code (`CaseStatePanels.tsx:71-72`); `identityIssueRetained` checks exceptions, interventions and `case.error.code` (`:106-111`). Backend codes are exactly `INITIAL_IDENTITY_INCOMPLETE`/`_NOT_ELIGIBLE`; `NOT_ELIGIBLE` is a terminal `case.error` (`onboarding.py:1720`) — covered by unit test and by `blocker-simulation.e2e.ts:386` (rail → identity UEN). Backend `NOT_REACHED` identity on a completed case is not done → shown. Retained non-OPEN identity codes over-show (safe direction). |
| 4 | Safeguard B — grouped step | PASS | Lead = attention › IN_PROGRESS › not done › first (`:74-77`); done only when both done; progress counts shown steps; per-member `h4` + facts; differing statuses named; attention items mapped by `businessStageIdFor` (`CaseAttentionSummary.tsx:114-118`); the only hidden node (`INITIAL_IDENTITY`) carries no `backend_stage`, so no item can land on a hidden step. |
| 4a | Safeguard C — navigation | PASS | `focusProcessingNode` (`CaseDetail.tsx:1074-1083`): one attention member → its route; two → member with a specific authorized control (`readinessAction()` / `#case-target-recovery`), else falls to `case-target-blocker`; settled → section. The section renders unconditionally (`:1623`), so "details are not available" cannot be reached for the grouped step; unit test asserts it. |
| 5 | D2 sticky focus | PASS with Low finding F-1 | Logic correct for keyboard and programmatic focus; header/toggle focus skipped (scope reset, print, toggle restore unaffected); `focusActionControl` / `focusProcessingNode` still issue their own final scroll, so their end position is unchanged. Shift+Tab browser test discriminates (failed without the fix, `kbd-without-fix.json`). |
| 6 | D3 benchmark precondition | PASS | `awaitSettledResources`: GET-only via `page.request` (outside `page.route` and the per-sample `attempts` listener), 30 s finite deadline with diagnostic error, before the untimed 500 ms settle and the sample loop; 22×2 iterations, 2 warm-ups, strict 2xx/CANCELLED assertion, entries/records accounting, layout, egress `violations`, `targetWrites === 0` and export unchanged; export adds `method_revision` and `precondition`. |
| 7 | No backend/API/schema/auth/runtime change; docs accurate; no secrets | PASS | Non-frontend changes are assistant section-name constants, two guidance front-matter `stages:` lines, assistant/backend tests. Doc section matches implemented behavior. Secret grep of added lines: none. |

## 4. Findings (most severe first)

### F-1 — Low — D2 focus scroll can swallow a mouse/touch click on a control mostly under the sticky header

- **Where:** `apps/frontend/src/pages/StageDisclosure.tsx:144-153` (`keepFocusBelowHeader` on
  `onFocusCapture`).
- **Defect:** the handler runs for every focus, including focus caused by `mousedown`/tap.
  When the control's top is under the sticky header, the page scrolls instantly between
  `mousedown` and `mouseup`, moving the control out from under the pointer; the click is
  then dispatched elsewhere.
- **Failure scenario:** a reviewer scrolls so that a button (for example "Save target
  classification") sits mostly beneath the stuck section header and clicks its visible
  sliver within ~12 px below the header edge. The page jumps and the button's click does
  not fire. Clicks lower on a partly covered control still register, but the page jumps.
- **Evidence:** standalone Chromium probe reproducing the same CSS (sticky header,
  `scroll-margin-top` formula) and the identical handler, mouse click 8 px above the
  button's bottom: 50 px covered → `clicks: 0` with the handler vs `clicks: 1` without;
  30 px/10 px covered → click registers, page jumps. Not reproduced inside the full app
  (mechanism identical).
- **Impact:** fail-safe (no action, no false success, user re-clicks); outside D2's approved
  scope (keyboard/programmatic focus), which works correctly.
- **Recommended follow-up (not required for this gate):** apply the alignment only to
  non-pointer focus (for example skip when a `pointerdown` inside the section preceded the
  focus).

### N-1 — Informational — settled-case registry focus lost its browser coverage

The approved removal of the two "Focus registry evidence" steps leaves no browser test
that focuses `#case-evidence-registry` in a settled case (unit coverage of
`processingNodeFocusTarget` remains). The no-request window those steps guarded in the
clean Mock path and in `garden-happy-path` now covers only disclosure toggles. A future
`focusPipelineAction(page, "ACRA_REGISTRY", …)` step on a settled case would restore it.

### N-2 — Informational — weak replacement assertions

Three replaced checks (`authenticated-zero-touch.e2e.ts:1127-1128`, `:1565-1566`, and the
480 px check) assert `.goldtier-status` visible after opening Technical details; that
element lives in the section's main content, so the assertion does not test the
Technical details. Not a regression of product behavior.

No Critical, High or Medium findings.

## 5. Code and architecture review

- Grouping is display-only: the backend pipeline is never mutated; `processing_pipeline`
  remains the source for members, counts and attention mapping. No new state owner,
  query key, cache or mutation path in `53ce015`/`fb7d4bc`.
- `findBusinessStage` keeps `?focus=READINESS`/`GOLDTIER_TARGET` entry links working by
  falling back to the backend node.
- `GOLDTIER_DETAILS` starts with `GOLDTIER_`; the fall-through
  `startsWith("GOLDTIER_") && #case-target-recovery` branch is reachable only when no
  member was chosen, and then routes to recovery or the section — consistent with C.
- Earlier-range note (previously gated, not re-litigated): `queryClient.clearSessionQueries`
  now also clears in-memory review source intents at session boundaries (correct
  direction); "Use registry value" submits `ACCEPTED` for the document field and pre-selects
  `KEEP_REGISTRY_VALUE` for explicit confirmation (`8039d87`, owner decision).

## 6. Security review

No auth/RBAC, CSRF, session, logging, provider, TLS or persistence change. No browser
storage or URL exposure added. D3's polling is read-only GETs with the same session. Added
lines contain no credentials, tokens, URIs, payloads or KYC data. No sponsor artefact
tracked.

## 7. Evidence: reused vs rerun

**Reused (identity verified):**
- `stage2b-e2e-results-fb7d4bc.json` — official `run_e2e.py` full run, `complete: true`,
  `keep_going: false`, 113 discovered / 113 selected / **113 PASS**, identity
  `fb7d4bc`/`50db1a9`/`98b08d5`, `dirty: false`; sha256 prefix `e2edb7fa5a1c0866` matches.
- `kbd-without-fix.json` (dirty `85fdd5b`): Shift+Tab test fails without D2 — discrimination
  evidence only.
- Focused D1/D2/D3 runs (`d1-results-1.json` 3 PASS/2 FAIL, `d2-results-1.json` 17 PASS,
  `d3-fix-ci60-results.json` 2 PASS) were on a dirty `53ce015` working tree; treated as
  history, superseded by the full run.

**Rerun independently by this gate on the clean `fb7d4bc` checkout:**

| Check | Result |
|---|---|
| `npm run typecheck` | PASS (exit 0) |
| `vitest run` | 62 files / **1042 passed** |
| `vite build` (output to scratch dir) | PASS (existing >500 kB chunk warning only) |
| `pytest apps/assistant/tests apps/backend/tests/test_ai_assistant_main_integration.py` (worktree `PYTHONPATH`, `app.__file__` verified) | **1149 passed**, 0 failed/skipped (not in Stage 2 evidence) |
| `scripts/check_project_state.py` | PASS |
| `scripts/check_architecture.py` | PASS |
| `git diff --check 98b08d5..fb7d4bc` | clean |
| Focused browser rerun (`run_e2e.py --selectors-file`, 13 selectors: `authenticated-zero-touch` :242/:864/:1044/:1294, `blocker-review-performance:168`, `blocker-simulation:386`, `ux-refinement:45`, `slice-c-recovery` :123/:156, `s3-sandbox-submission:254`, `s1-workspace-session:123`, `garden-happy-path:218`, `performance-browser:137`) | **13/13 PASS**, `complete: true`, 206 s, identity `fb7d4bc`/`50db1a9`/`98b08d5`; `dirty: true` solely because this untracked report existed during the run (no tracked change); results sha256 prefix `d1a0e1bea3685835` |
| D2 click probe (standalone Chromium) | see F-1 |

Not run: full backend pytest, physical Mongo, `pre_pr_check.py` (reserved; no backend or
persistence change makes the first two applicable).

## 8. Change statements

| Area | Changed? |
|---|---|
| API / browser types | No (frontend presentation constants only) |
| Schema / persistence | No |
| Connectors / providers / provider status | No |
| Configuration | No |
| Business rules | No (display grouping only; backend stages, statuses, lifecycle unchanged) |
| Mappings (source → canonical → target) | No |
| Auth / security | No |
| Architecture / owners | No |
| Runtime behavior | Frontend presentation and focus/navigation only; AI Assistant section-name text; E2E benchmark methodology (`settled-resource-precondition-v1`) |

## 9. Readiness

Publication readiness: the content is ready for Stage 4 **only with explicit owner
authorization**; this gate grants none. F-1 is a recommended follow-up, not a condition.
Live ACRA and real GoldTier integration readiness are unaffected and not claimed.

## 10. Git status

Gate worktree on `claude/qg-ui-enhancement-v1-fb7d4bc-91a9ba` at `fb7d4bc`, no staged or
tracked modifications. The only file written is this report (untracked). Ignored local
artefacts created by checks: `apps/frontend/node_modules` (`npm ci`) and
`apps/assistant/data/` (pytest). No implementation fix, commit, push, PR, merge, rebase,
reset or clean was performed; no Mongo, `clm_poc` or `.env` access; no other worktree was
modified.
