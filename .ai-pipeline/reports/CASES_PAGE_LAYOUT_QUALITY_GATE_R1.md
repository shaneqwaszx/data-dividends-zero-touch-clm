# Cases page layout + `progress` filter: Independent Quality Gate, re-review R1

## Outcome

**PASS.** The R0 blocker (F1, "Zero-touch" shown on unfinished cases) is fixed. It is the
only place in the frontend that shows the label, and a new test covers every unfinished
status the reviewer checked. The AttentionQueue edit is now a justified correction that
makes the test stricter. The docs match the code. The d90ab6a merge is clean and shares no
code with this branch. The affected E2E selectors pass on the clean frozen tree (the
reviewer reran them because the implementer's run was on a dirty tree).

One owner-authority item remains, and it is not a code or test defect. No decision-log
entry records the removal of the Onboarded and ClientDetail pages. It must be listed in
the PR body for Shane to record or waive before merge (see O1).

The reviewer did not write or fix this content. The gate was read-only. The only file
written in the repository is this report. Scratch output is in
`/private/tmp/claude-501/-Users-tasha-Documents-GitHub-data-dividends-zero-touch-clm/0bb30124-5a31-4c17-956f-11d822f760ca/scratchpad/qg-r1/`.

## Reviewed identity

| Item | Value |
|---|---|
| Worktree | `/Users/tasha/Documents/GitHub/dd-clm-cases-page` |
| Branch | `feat/cases-page-layout` |
| HEAD | `710da28659844c1c2baf4798cc75f4eca389d030` (verified) |
| Tree | `02d66461925bc800f1851008ea66c49049d59fbd` (verified) |
| Working tree | Clean at the start and end of the gate, apart from this report |
| `origin/main` | `d90ab6a` after `git fetch` (unchanged). It is an ancestor of HEAD through merge `949ef6f`. |
| Prior gate | R0 on `34aa3e5`: FAIL (`CASES_PAGE_LAYOUT_QUALITY_GATE.md`) |
| Branch diff vs main | 43 files, +1121 / −963 (`git diff origin/main...HEAD`) |
| Remediation delta (`34aa3e5..710da28` minus main content) | `CaseQueue.tsx` (status cell), `CasesPageLayout.test.tsx`, `AttentionQueue.test.tsx`, `authenticated-zero-touch.e2e.ts` (+3), `ARCHITECTURE.md`, `PROJECT_STATE.md`, `CASE_PORTFOLIO_QUERY_PROFILE.md`, R0 report committed. No backend or script file changed. |
| Merge `949ef6f` | Every file #132 touched is byte-identical to `d90ab6a` on HEAD, except `docs/PROJECT_STATE.md`. That file auto-merged two separate hunks: this branch's line-227 edit and main's appended D-100 section. No conflict resolution was needed. The branch and main share no code file. |
| `949ef6f..710da28` | Only the e2e file. The reload-based check was replaced by a server read. |

## R0 finding dispositions

| R0 finding | Disposition | Evidence |
|---|---|---|
| F1 HIGH: false-success "Zero-touch" | **Closed** | `CaseQueue.tsx:413-418`: shows `N manual step(s)` when N > 0, bold `Zero-touch` only when `status === "COMPLETED"` and N = 0, and otherwise plain `No manual steps yet`. This matches the owner's chosen wording and the backend's COMPLETED-only meaning (`services/dashboard.py` `_delay_note` / `_zero_touch_rate`). A search of `apps/frontend/src` and `e2e` finds no other Cases or list surface that shows "Zero-touch". The Dashboard "Zero-touch rate" KPI already says "Completed cases…". Other `human_interventions` displays are plain counts in case detail. `RESUMING` is not in the new test but goes through the same non-COMPLETED branch. COMPLETED is the only successful terminal `AutomationStatus`. |
| F1 test gap | **Closed** | `CasesPageLayout.test.tsx:172-182` renders RUNNING, WAITING_FOR_REVIEW, RECOVERY_PENDING, TECHNICAL_FAILURE and PENDING_INPUTS with 0 steps. For each one it asserts "No manual steps yet", the absence of "Zero-touch" and that no `<strong>` is present. It also asserts that a COMPLETED 0-step row shows a bold "Zero-touch". The R0 code (`=== 0 → Zero-touch`) would fail this test, and so would a version without the COMPLETED check. |
| T2: AttentionQueue teammate assertion | **Closed (justified, stricter)** | `AttentionQueue.test.tsx:256-259`. Its rows are WAITING_FOR_REVIEW and RECOVERY_PENDING. The test now asserts "No manual steps yet" and **not** "Zero-touch", and still asserts not "3 open · 0 human". That old label was removed by the owner-approved layout, so the original assertion can't be restored. The new assertions check the correct, truthful outcome and catch the R0 regression. List it in the PR as a superseded teammate assertion (reason: approved Cases cell wording plus the R0 F1 fix). |
| F2 MEDIUM: docs | **Closed (docs)** / owner item **O1** | The contract now documents `progress` (values, intersection with `status`, 422, memory/Mongo parity after scope). This matches `main.py` `Literal`, `case_management.py` and `mongo_case_store.py`. The frontend paragraph matches `CaseQueue.tsx:127-153`: the Onboarded view shows Status as COMPLETED but sends only `progress=onboarded`, which is what "fixes Status to COMPLETED" describes. `ARCHITECTURE.md:800-801` and `PROJECT_STATE.md:227-228` now describe the Onboarded view in Cases. The remaining "Onboarded" mentions (`CASE_ACCESS_AND_PRIORITY_PROFILE.md:28,37`, `PROJECT_CONTEXT.md:404,431`, historical decision rows) still hold, because the Onboarded view is still a Director-filterable portfolio read (INFO). The decision entry is still missing: see O1. |
| F3 LOW: e2e priority read local state | **Closed** | `authenticated-zero-touch.e2e.ts:1660-1662` makes a fresh `GET /api/clm/zero-touch/cases/{id}` (same session) and asserts `case.priority === 5`. That is server truth that the control can't satisfy on its own. A non-JSON or 404 response would fail the test, not pass it. |
| F4 LOW: not integrated with d90ab6a | **Closed** | `949ef6f` merges `d90ab6a`, and `origin/main` is still `d90ab6a`. Full Vitest, typecheck and build were rerun on the integrated tree (below). |

## Evidence matrix

| Check | Result | Identity | Reused / rerun |
|---|---|---|---|
| Frontend typecheck `tsc -b` | PASS (exit 0) | 710da28 clean | **Rerun** |
| Focused Vitest (CasesPageLayout, AttentionQueue, Phase18, Phase19) | 4 files, 36/36 pass | 710da28 clean | **Rerun** |
| Full Vitest | 1211/1212. The only failure is `ViteHistoryFallback.test.ts` (a documented macOS-only quirk, the same as R0 and the implementer's `cases-vitest-949ef6f.log`). | 710da28 clean | **Rerun** (`qg-r1/vitest-full.log`) |
| Frontend build | PASS (`vite build` to a scratch outDir, so nothing was written to the repo; `tsc -b` covered above) | 710da28 clean | **Rerun** (`qg-r1/build.log`) |
| Affected E2E (8 selectors: authenticated-zero-touch 242/1169/1646/1782, responsive-layout 385, garden-happy-path 179/261, s1-workspace-session 314; line IDs confirmed with `playwright test --list`) | **PASS 8/8**, complete, `identity.head=710da28`, `tree=02d6646`, `dirty=false`, `origin_main=d90ab6a` | 710da28 clean | **Rerun**: `qg-r1/e2e-affected-710da28.json` / `.log`. The implementer's `cases-e2e-affected-r2.json` has `head=949ef6f`, `dirty=true`, so it is not bound to the frozen tree and was not relied on. |
| Full E2E keep-going | 107/116. The 9 failures match clean main `90115e4` (the same tests and first failing assertions, verified at R0). | 34aa3e5 | **Reused.** Since then the code changes are one table-cell branch (no e2e asserts the cell text) and #132's AI Model Console files, which no e2e covers (grep). The impact is bounded, and the rerun affected selectors cover the changed Cases and e2e code. Under the workflow reuse rule ("rerun focused checks plus the affected change-class rows"; the full set is needed only for a shared owner, hotspot, or impact that can't be bounded), a new full run is not required for this gate. The full suite runs once at final acceptance if Shane wants it with the PR. |
| Full backend pytest | 3199 pass / 181 skip / 6 fail (`test_s2_local_ocr` macOS font, pre-existing) | 34aa3e5 backend | **Reused.** `git diff 34aa3e5 710da28 -- apps/backend scripts` is empty, and #132 has no backend files. |
| Ruff / mypy | Clean | 34aa3e5 | Reused (no Python change) |
| Physical Mongo | 176/176 (full) + focused rerun at R0 | 34aa3e5 | Reused (no backend change) |
| `check_project_state` / `check_architecture` | PASS / PASS | 710da28 | **Rerun** |
| Line endings | `git diff origin/main...HEAD --numstat` is identical to `--ignore-cr-at-eol --numstat` (43 rows) | 710da28 | **Rerun** |
| `git diff --check` | Clean | 710da28 | **Rerun** |
| `pre_pr_check.py` | Not run by the gate (Stage 4, on a clean committed tree) | — | — |

## New findings

No new HIGH, MEDIUM or LOW defect.

### O1: owner authority (not a gate defect): decision record for the page removal

The Onboarded page and the ClientDetail page (with its disabled Risk/Export/Review
disclosures) were removed with product-owner approval. `/onboarded` routes redirect, and
the docs now say so. `docs/decisions/DECISION_LOG.md` has no entry for this. The
workflow's ADR criteria mention "intentionally retires a supported surface". Whether a
UI page counts is for the repository owner to decide, and per AGENTS.md the reviewer must
not invent that decision. This is unresolved owner authority, kept separate from defects
as the gate skill requires. It does not block this gate because the behavior is truthful,
documented and compatible (old links redirect). It **must** be listed in the PR body as
"decision record for removing the Onboarded page: Shane to record or waive", and it must
be resolved before merge. The implementer may instead add a PROPOSED decision-log entry.
That would be a docs-only delta needing only a docs recheck.

### INFO

- The new test has no `RESUMING` row. The code path is the same `else` branch, so this is not a gap in behavior.
- Teammate-test list for the PR: carry over R0's T1–T14 table, with T2 updated to the corrected assertion above.

## Security review

The delta has no auth, RBAC, session, CSRF, secret or logging change. The e2e server read
uses the existing authenticated GET and the same session. No security finding.

## Readiness

The gate is satisfied for publication preparation (Stage 4: `pre_pr_check.py` on the clean
committed tree, PR body listing O1 and the changed teammate assertions, and the manual-CI
exception for Shane). This is a UI/governance-scope change, so the gate makes no claim
about phase readiness or live ACRA/GoldTier readiness. Local evidence is not hosted CI.

## Git status

Branch `feat/cases-page-layout`, HEAD `710da28`, tree `02d6646`, unchanged during the gate.
No tracked file was modified and nothing was staged. The only new untracked file is this
report. No commit, push, merge, rebase, reset or stash.

VERDICT: PASS
