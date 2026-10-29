# Cases page layout + `progress` filter: Independent Quality Gate

## Outcome

**FAIL.** Most of the change is sound. The backend `progress` filter has memory/Mongo
parity for every `AutomationStatus`, keeps scope, and returns 422 on bad values. The
query key, redirects, priority save-on-change and accessibility were verified. One
current defect blocks PASS: the Cases table labels **every** row with
`human_interventions == 0` as **"Zero-touch"**, whatever its status. A case that is
`WAITING_FOR_REVIEW` with open exceptions, `RECOVERY_PENDING`, `TECHNICAL_FAILURE`,
`RUNNING` or `PENDING_INPUTS` is shown in bold accent as "Zero-touch". The backend
already defines that label as COMPLETED-only. This is an untruthful, success-sounding
status on the main operational list. The gate rules make a false-success claim a FAIL,
not a minor fix. A teammate's test (AttentionQueue) was changed to assert this wrong
label (see T2).

The reviewer did not author or remediate this content. The gate was read-only. The only
file written in the repository is this report. Scratch output went to
`/private/tmp/claude-501/-Users-tasha-Documents-GitHub-data-dividends-zero-touch-clm/0bb30124-5a31-4c17-956f-11d822f760ca/scratchpad/qg/`.

## Reviewed identity

| Item | Value |
|---|---|
| Worktree | `/Users/tasha/Documents/GitHub/dd-clm-cases-page` |
| Branch | `feat/cases-page-layout` |
| HEAD | `34aa3e5746b146f2ec52535e9c3e9fb24b2f50dc` (verified) |
| Tree | `9cdd21c17c555e2d4d1897cec9f3d44605e26b56` (verified) |
| Working tree | Clean (`git status --porcelain` empty), at the start and at the end of the gate |
| Integrated base | `90115e4` (ancestor of HEAD, through merge `781df5b`) |
| Current `origin/main` | **`d90ab6a`** (#132 D-100 Phases 2–4). Main has moved one commit past the integrated base. #132 touches no file in this diff (intersection is empty). It does change frontend files (`AiModelManagement*`, `aiAssistant.ts`), so the full frontend evidence is pre-integration for Stage 4 (see F4). |
| `781df5b..34aa3e5` | Only `apps/backend/tests/test_case_portfolio_progress_real_mongo.py` (+66) and `scripts/run_physical_mongo_tests.py` (+1). Confirmed, so the Vitest/build evidence from 781df5b still applies to the frontend content. |
| Diff | 39 files, +873 / −958 (`git diff 90115e4...HEAD --stat`) |
| Change classes | FRONTEND_UI, FRONTEND_STATE_CACHE, BACKEND_DOMAIN, BACKEND_API, PERSISTENCE (read predicate only). Small CI_TOOLING touch: one suite added to `scripts/run_physical_mongo_tests.py`. |

## Mandatory-check matrix

| Check | Required by | Result | Evidence | Reused / rerun |
|---|---|---|---|---|
| Focused backend tests | all | PASS, 29 passed (`test_case_portfolio_progress.py` + `test_phase18_case_portfolio.py`) | local, on the frozen tree, `PYTHONPATH` set to the worktree (`app.__file__` confirmed in the worktree) | **Rerun** |
| Full backend pytest | DOMAIN/API/PERSISTENCE | 3199 passed, 181 skipped, 6 failed. All 6 are `test_s2_local_ocr.py::test_real_local_ocr_acceptance[*]` (`OSError: cannot open resource`, a macOS font path issue unrelated to this diff) | `cases-backend-full.log`. The log has no SHA, but the only backend change after it would be the added physical test, which skips without a URI. | Reused (accepted, unrelated failures noted) |
| Ruff `apps/backend scripts` | DOMAIN/API/PERSISTENCE | PASS (`All checks passed!`, `--no-cache`) | local | **Rerun** |
| mypy `app` | DOMAIN/API/PERSISTENCE | PASS (129 files, cache outside the repo) | local | **Rerun** |
| Physical Mongo | PERSISTENCE | PASS: new `test_case_portfolio_progress_real_mongo.py` + `test_phase18_case_portfolio_real_mongo.py`, 4 passed against the throwaway mongod :27188 (generated ephemeral DB, cleaned up) | local. The implementer's full run (`PHYSICAL_MONGO_RESULT=PASSED; SUITES=27; COLLECTED=176; PASSED=176`) is in `cases-physical.log`. | Focused **rerun** + full reused |
| Contract tests | API | No automated contract test for this profile. **Contract document not updated** (F2). | inspection | n/a |
| Focused frontend tests | UI/STATE | PASS: 10 files, 205 tests (CasesPageLayout, AttentionQueue, Phase15CNavigation, Phase18, Phase19, S1CreatedDateFilters, UiV2Integration, App, Phase14, UboSummary) | local | **Rerun** |
| Full frontend Vitest | UI/STATE | 1185/1186. The only failure is `ViteHistoryFallback.test.ts`, a documented macOS-only quirk. | `cases-vitest-full.log` (on 781df5b, identical frontend content) | Reused |
| Frontend typecheck | UI/STATE | PASS (`tsc -b --pretty false`, exit 0) | local | **Rerun** |
| Frontend build | UI/STATE | PASS | `cases-build.log` | Reused |
| E2E (affected + full keep-going) | browser behaviour | 107/116 pass. The 9 failures match a clean `90115e4` checkout: same selectors and same first failing assertion (see below). | `cases-e2e-full-34aa3e5-r2.json` (identity head/tree = frozen, dirty=false), `main-90115e4-known9.json` | Reused, equivalence **verified by reviewer** |
| `check_project_state` / `check_architecture` | A | PASS / PASS | local (`python -B`) | **Rerun** |
| Line endings | repo hygiene | PASS: `--numstat` equals `--ignore-cr-at-eol --numstat`; `git diff --check` clean | local | **Rerun** |
| `pre_pr_check.py` | all | Not run (it runs after the gate, on a clean committed tree) | — | — |
| Independent QG | STATE/DOMAIN/API/PERSISTENCE | This report | — | — |

### E2E equivalence check (reviewer)

The failing sets match: database-classification 191/196/201/206, onboarding-recovery:6,
s3-sandbox-submission 232/752, slice-c-recovery:294 and responsive-layout (567 on the
branch, 565 on main; the branch deleted 2 lines above it). The first failing assertion
locations also match: database-classification 37/38/136, onboarding-recovery:84,
s3-sandbox 99/169/502, slice-c 253. The responsive-layout failure is the same statement
on both: branch line 504 = main line 506, `expect(noTextDocument.error.code).toBe("OCR_RUNTIME_UNAVAILABLE")`,
which received `OCR_PROCESSING_FAILED`. That is a local OCR environment issue, not Cases
layout. The edited responsive test ("responsive cases and representative routes",
line ~360) and the edited garden/s1/authenticated-zero-touch tests all **pass** on the
branch.

## Requirement verification

| Requirement | Result | Evidence |
|---|---|---|
| `progress` memory matcher | Met | `case_management.py:395-398`: `(status==COMPLETED) != (progress=="onboarded")`. Parametrised over every `AutomationStatus` (test_case_portfolio_progress.py:26). |
| Mongo clause, parity | Met | `mongo_case_store.py:1549-1552`. `onboarded` uses `automation.status == COMPLETED`; `in_progress` uses `$ne COMPLETED`. The row `$match` runs after the strict `valid_candidate` facet match, so a missing or invalid status cannot reach the `$ne` branch. Physical test proves both splits for every status (rerun). |
| Composition with explicit status | Met | Separate `$and` clauses. Onboarded+WAITING gives an empty set; in_progress+WAITING gives that case only (memory + physical). |
| Cannot widen scope | Met | Team/unassigned scope is in the first `$match` stage (`candidate_match`, line 304-308), before and separate from `_portfolio_row_match`. The memory path keeps the scope check unchanged. `_resolve_scope` runs first in `CaseQueryService.list_portfolio`. |
| 422 on other values | Met | `Literal[...]` in `main.py:1984` and the domain model. API test asserts 422 for `archived`. |
| Query key includes progress | Met | `caseQueries.ts:51`. Prefix invalidation (`priorityMutationEffect`, `caseDeletedEffect`) still covers it. |
| Onboarded view's forced COMPLETED doesn't leak | Met | `CaseQueue.tsx:128-130` derives status. The view button resets `presentation.status` to `""` when entering Onboarded (and when entering In progress if it was COMPLETED). Onboarded sends `progress=onboarded` with no `status`. Offset resets through `updatePresentation`. |
| Priority save-on-change, revert, no double submit | Met | `PriorityControl.tsx`: the select is `disabled` while busy and sends one PATCH (test asserts one call). On failure it restores `priority` (test asserts value `""` plus the error text). |
| `/onboarded`, `/onboarded/:id` redirects | Met | `navigation.tsx:285-289`, `Navigate replace` inside `caseAccess` + `CaseParamRoute` (malformed IDs still handled). Test "redirects the retired Onboarded routes into Cases". No remaining imports of `OnboardedClients`/`ClientDetail`/`paths.onboarded*`/`OnboardedRowView`/`ClientDetailView` (grep). |
| Accessibility | Met | The toggle group has `aria-labelledby`, and each button has `aria-pressed`. Every filter has a `<label htmlFor>` (test checks the targets exist). The dates sit in a labelled group with sr-only names. Copy uses `aria-label="Copy GoldTier ID for <company>"`. The tooltip duplicate is `aria-hidden` and the ID is in the text. The search SVG is `aria-hidden`. The Saving status is `role=status`. |
| "Zero-touch" / "N manual steps" | **Not met: false status** | F1 |
| No permission recheck / maker-checker weakened | Met | No backend mutation, RBAC or permission code in the diff. Priority still goes through the existing PATCH path. Delete is unchanged. |

## Findings (ranked)

### F1: HIGH, false-success status label (blocker)

`apps/frontend/src/pages/CaseQueue.tsx:413-415`

```tsx
{item.human_interventions === 0
  ? <strong className="cell-note zero-touch-note">Zero-touch</strong>
  : <span className="cell-note">{manualStepsLabel(item.human_interventions)}</span>}
```

`human_interventions` only goes up when a human resolves something
(`zero_touch_orchestration.py:1082/1264/1547`). Every new or in-flight case therefore
has 0, including one that is blocked waiting for a human. Such a case is shown as
"Zero-touch" next to its `WAITING FOR REVIEW` / `TECHNICAL FAILURE` / `RECOVERY PENDING`
tag. In the new **In progress** view, every case that hasn't had a human step yet is
labelled "Zero-touch". The backend's own owner of this label limits it to completed
cases: `services/dashboard.py:516` (`_delay_note`: COMPLETED and 0 → "Zero-touch") and
`_zero_touch_rate` (completed only). The UI now claims an outcome the backend has not
earned. AGENTS.md requires truthful user-visible status. The owner's approval was for
"Zero-touch when human_interventions == 0", shown on completed fixtures. Nothing shows
the in-progress case was considered, and an approval of wording does not authorise a
false status.

Smallest fix (not applied by the gate): show "Zero-touch" only when
`status === "COMPLETED" && human_interventions === 0`. For a case not yet completed with
0 steps, show nothing or a neutral note (wording is the owner's call, e.g. "No manual
steps yet"). Keep "N manual steps" for any status when N > 0. Add a test where a
WAITING_FOR_REVIEW (and a TECHNICAL_FAILURE) row with 0 interventions does **not** show
"Zero-touch". Restore the AttentionQueue assertion (T2) to match.

### F2: MEDIUM, API contract document not updated

`docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md` ("Request" table) is the
project-defined contract for `GET /api/clm/zero-touch/case-portfolio`. The diff adds a
new public query parameter `progress` (`in_progress` | `onboarded`, 422 otherwise,
intersects with `status`) but leaves this table out of date. AGENTS.md completion
requires affected durable documentation to be current. Related stale prose:
`docs/ARCHITECTURE.md:801` ("Both Cases and Onboarded use…") and
`docs/PROJECT_STATE.md:227` ("Cases and Onboarded offer…") still describe the removed
Onboarded page. Removing a product surface (the Onboarded page and the ClientDetail page
with its disabled Risk/Export/Review disclosures) has owner approval in the brief, but
there is no decision-log entry. Record one, or confirm that the owner does not want one.

### F3: LOW, E2E priority assertion now checks local state instead of server-refreshed state

`apps/frontend/e2e/authenticated-zero-touch.e2e.ts:1656-1659`. The old test asserted
the refreshed `.priority-badge` text ("Medium"), which came from the refetched
server row. The new test asserts `select.priority-select` has value "5". The user has
just chosen that value, so the check passes no matter what the refetch returns. The
PATCH 200 is still asserted. Suggested: also check the refreshed row, for example wait
for the follow-up portfolio GET and assert the value afterwards, or reload and
re-search. This is not blocking, because the request and response are still verified.

### F4: LOW / process, not integrated with current `origin/main`

`origin/main` is now `d90ab6a` (#132), one commit past the integrated base `90115e4`.
The files don't overlap. The commit does change frontend files, so after merging main
(Stage 2/4 integration, when authorised) rerun the full frontend Vitest, typecheck and
build. Backend and physical evidence aren't affected (#132 has no backend files).

### F5: INFO

- The "Total results are not calculated" disclosure was removed (Phase18 test now
  asserts it is absent). This is not untruthful: the page shows "Showing X–Y" and
  "Page N" and never shows a total. It is accepted as part of the approved layout.
- The "GoldTier ID" row label shows `mock_goldtier_party_id` with no Mock qualifier.
  This matches the existing precedent on the removed Onboarded page ("GoldTier party
  ID") and in `CompletedOverview`. It is not a regression, but the owner may want the
  provider mode visible.
- The `scripts/run_physical_mongo_tests.py` one-line suite addition makes this lightly
  CI_TOOLING. The full physical runner passed with it (27 suites).

## Changed test assertions (all 18 existing files)

| # | File | Change | Judgement |
|---|---|---|---|
| T1 | `e2e/authenticated-zero-touch.e2e.ts` | Labels `Search cases`→`Search`, `Jurisdiction filter`→`Jurisdiction`, `Priority filter`→`Priority`, `Priority sort`→`Sort`, `Open business exception type`→`Needs attention` (all `exact`). `Showing 1–50 on page 1`→`^Showing 1–50$`. `Timing observed at`→`^Updated (just now\|… ago)$` (still `toHaveCount(1)`). The Set-button click was removed, and the `.priority-badge` "Medium" check became the select value "5". | Superseded (approved wording/labels, save-on-change). Priority persistence check is weaker: **F3**. |
| T2 | `src/AttentionQueue.test.tsx` | `"Open business exceptions"`→`"Needs attention"`. **`"3 open · 0 human"` → `toContain("Zero-touch")`** on a fixture whose only rows are WAITING_FOR_REVIEW (3 open exceptions) and RECOVERY_PENDING. `"No open business exceptions recorded"`→ attention cell `"—"`. Label lookup changed to `htmlFor`. | Header, dash and lookup are superseded. **The Zero-touch assertion is an unjustified redefinition: it encodes the F1 false status. It must change with F1.** |
| T3 | `e2e/garden-happy-path.e2e.ts` (2 places) | The Onboarded tab link + `/onboarded/<id>` link became the Onboarded view button + `/cases/<id>` link. | Superseded (page removal); the completed case still appears in the onboarded view. |
| T4 | `e2e/responsive-layout.e2e.ts` | The `/onboarded` and `/onboarded/<id>` route steps and the `/onboarded` scroller condition were removed. Search label changed. | Superseded (routes now redirect; the redirect is covered by the Phase15C unit test). Passes on the branch. |
| T5 | `e2e/s1-workspace-session.e2e.ts` | Onboarded heading became `aria-pressed=true` on the button. The wait for `GET /cases?status=COMPLETED` became `GET /case-portfolio?progress=onboarded` (same created_from/to checks). | Superseded; equivalent server-side date-filter proof. |
| T6 | `src/App.test.tsx` | `toContain("Onboarded")` became `not.toContain('href="/onboarded"')`. | Superseded (tab removed). |
| T7 | `src/Phase15CNavigation.test.tsx` | Onboarded entries removed from the canonical route table. The test "shows every accessible completed case… Onboarded filters" (client-side filtering on OnboardedClients) was deleted. `onViewOnboarded` props removed. A new redirect test was added. `/onboarded` literals were kept in the intake-safety route list. | Superseded. The deleted test covered a removed page's client-side filters; Cases filters are server-side and covered elsewhere (Phase18, e2e). |
| T8 | `src/Phase14CaseManagementPerformance.test.tsx` | Deleted "loads Onboarded with one completed-list request and no detail fan-out". | Superseded. The Onboarded view uses the same single bounded portfolio page as Cases (CasesPageLayout asserts `progress=onboarded`; the e2e asserts no detail fan-out on Cases). |
| T9 | `src/Phase18CasePortfolio.test.tsx` | `Showing 1–1 on page 1`→`Showing 1–1`; `Total results are not calculated` is now asserted **absent**; `Showing 51–51 on page 2`→`Showing 51–51` + `Page 2`. | Superseded (approved copy). The disclosure removal is not false (F5). |
| T10 | `src/Phase19Timing.test.tsx` | `Timing observed at` / `Refresh to obtain a new observation` became the `Updated …` element with a non-empty full-time `title` + a Refresh button. | Superseded; it still proves an observation time is shown and refresh exists. The new CasesPageLayout test checks that Refresh issues exactly one request. |
| T11 | `src/S1CreatedDateFilters.test.tsx` | Deleted "Onboarded filters by case creation… blocks a reversed range". `it.each(["Cases","Onboarded"])` became `["Cases"]` only. | Superseded. The reversed-range and late-response checks still run for Cases, which now also hosts the Onboarded view (the same component and code path). |
| T12 | `src/UiV2Integration.test.tsx` | Navigation label `Onboarded` removed (+ no `/onboarded` href). `mapCompletedCaseToOnboardedRow` checks became `mapZeroTouchCaseToCaseRow().goldtier_party_id`/`completed_at`. Deleted: the disabled Risk/Export/Review disclosures test, the Onboarded action-column header test, and the "routes an onboarded client back to the case controls" test. | Superseded (page and mapper removal approved). The disabled-disclosure surfaces no longer exist. |
| T13 | `src/pages/UboSummary.test.tsx` | Deleted D-081 "never adds assumed-basis matches to the client-detail owners" (`mapZeroTouchCaseToClientDetail`). | Superseded: the mapper and its only consumer (ClientDetail) were removed. The D-081 split itself is still tested in the same file through `OwnershipPathExplorer`. Listed because it is a D-081 assertion. |
| T14 | `src/EvidenceWorkbenchIsolation.test.tsx`, `Phase13AuthPriority.test.tsx`, `Phase15ASponsorRebaseline.test.tsx`, `pages/AM03SearchStage.test.tsx`, `pages/S3SubmissionStatus.test.tsx` | Only the removed `onViewOnboarded` prop was dropped. | Mechanical; no assertion change. |

New tests: `src/CasesPageLayout.test.tsx` (frontend),
`apps/backend/tests/test_case_portfolio_progress.py` and
`test_case_portfolio_progress_real_mongo.py`. Their quality is good, except that
there is no not-completed row with 0 interventions (which would have caught F1).

## Security review

No change to auth, RBAC, session, CSRF, secrets, logging or provider code. Scope comes
from the server before `progress` applies, and the parameter is a closed `Literal`, so
nothing can be injected into Mongo (a fixed clause is built, never from user text).
The clipboard write only copies a value the user can already see. No security finding.

## Required fixes (current)

1. **F1**: only show "Zero-touch" for `COMPLETED` cases with 0 manual steps. Add the
   adverse test. Correct the AttentionQueue assertion (T2).
2. **F2**: add `progress` to `docs/contracts/CASE_PORTFOLIO_QUERY_PROFILE.md`. Update
   the Onboarded references in `ARCHITECTURE.md:801` / `PROJECT_STATE.md:227`. Record or
   waive a decision entry for the Onboarded page removal (owner).

Recommended, not blocking: F3 (assert server-refreshed priority in e2e). Before Stage 4:
F4 (merge `d90ab6a`, rerun full frontend Vitest/typecheck/build).

Recheck scope after remediation: the CaseQueue status cell plus its tests (focused
Vitest, typecheck, the affected e2e `authenticated-zero-touch` Cases selectors) and the
docs diff. Backend, physical Mongo and the unrelated E2E evidence stay valid unless
their files change.

## Readiness

Not ready for PR publication. This is a UI/governance change, so this gate makes no
claim about phase or live ACRA/GoldTier readiness.

## Git status

Branch `feat/cases-page-layout`, HEAD `34aa3e5`, tree `9cdd21c`, unchanged during the
gate. No tracked file was modified and nothing was staged. The only new untracked file
is this report. No commit, push, merge, rebase, reset or stash, and no implementation
fix. The reviewer ran `tsc -b` (its build info goes to an ignored path), and
`git status --porcelain` stayed empty apart from this report.

VERDICT: FAIL
