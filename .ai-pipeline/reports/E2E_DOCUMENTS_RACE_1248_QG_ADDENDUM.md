# QG Addendum: E2E selector `authenticated-zero-touch.e2e.ts:1248`

Reviewer: independent, read-only Quality Gate run (did not implement or remediate this candidate).
Date: 2026-10-25. Scope: one browser E2E failure in the D-085/D-086 integrated candidate.
This addendum gives a verdict on that failure only. It does not re-review the whole candidate.

## 1. Identity

| Item | Value |
|---|---|
| Candidate worktree | `C:\Users\shane\Desktop\claude-worktrees\generalized-poc-acceptance-int-20261025` |
| Branch | `feat/generalized-poc-acceptance-multilayer-20261025-int` |
| HEAD = origin/main | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c` |
| Candidate tree, BEFORE runs | `1b4b382ea294cf828d323818c8924bb78e0dd7bb` (scratch index + `candidate_paths_int5.txt`, 48 paths) |
| Candidate tree, AFTER runs | `1b4b382ea294cf828d323818c8924bb78e0dd7bb` (fresh scratch index copy) |
| `git status --short` line count | 49 before, 49 after. The real index was not touched (`git diff --cached` is empty). |
| Main review worktree | `C:\Users\shane\Desktop\claude-worktrees\qg-e2e-1248-main-5de7f24`, detached HEAD `5de7f24c2dbf678bbb9de02ad627be777bc2f28c`, status 0 lines before and after |
| Main frontend dependencies | Directory **junction** `apps/frontend/node_modules` pointing to the candidate's `apps/frontend/node_modules`. It is gitignored (`.gitignore:34:node_modules/`). `package.json` and `package-lock.json` are byte-identical (`cmp`). `npm ci` was not used. The junction is still in place. |
| Mongo | Task-owned `mongo:7` container `qg1248-mongo` on `127.0.0.1:27131`, with tmpfs data. Stopped (`--rm`) at the end. Other containers were not touched. |
| Runtime | Windows 11, Git Bash, Node v22.23.3, `@playwright/test` 1.56.1 (chromium, `retries: 0`, `trace: off`), repo `.venv` Python, Tesseract on PATH, `CLM_E2E_SYNTHETIC_MONGO_PORT=27131` |
| Command (both revisions) | `timeout 400 $PY scripts/run_e2e.py --timeout-seconds 60 --selectors-file qg-e2e-1248/selector.txt --results-json qg-e2e-1248/res_<R>_<n>.json` |
| Registry mode | Default guarded local Mock. The test has no `slice-b-*` tag, so the hybrid / five-layer lane is not enabled for this selector (`scripts/run_e2e.py:447-451`). |

Run logs are in `qg-e2e-1248/log_<C|M>_<n>.log`, results JSON in `qg-e2e-1248/res_<C|M>_<n>.json`, and the summary is `qg-e2e-1248/runs.txt` (all in the session scratchpad).

## 2. Run table

The runs were strictly serial and interleaved on the same machine, one at a time, with the same Mongo and ports. Series 1 ran C first (C, M, C, M ...). Series 2 ran M first, to cancel out any order effect.

| # | Candidate (C, tree 1b4b382) | Main (M, 5de7f24) |
|---|---|---|
| 1 | PASS | FAIL |
| 2 | FAIL | FAIL |
| 3 | FAIL | FAIL |
| 4 | FAIL | PASS |
| 5 | FAIL | PASS |
| 6 | FAIL | FAIL |
| 7 | PASS | PASS |
| 8 | PASS | FAIL |
| 9 | PASS | FAIL |
| 10 | FAIL | FAIL |
| 11 | PASS | FAIL |
| 12 | FAIL | FAIL |
| 13 | FAIL | FAIL |
| 14 | PASS | FAIL |
| 15 | FAIL | PASS |
| 16 | FAIL | PASS |
| **Total** | **6 / 16 pass (37.5%)** | **5 / 16 pass (31.3%)** |

- **Error signature:** all 21 failures (10 C, 11 M) are identical: `Error: response.json: Protocol error (Network.getResponseBody): No resource with given identifier found` at `authenticated-zero-touch.e2e.ts:1273:43`. No other failure mode appeared.
- **Duration:** each lifecycle took about 9–19 s. Passing tests took about 3.2–3.5 s inside Playwright.
- **Statistics:** the difference between revisions is not significant (6/16 vs 5/16; a two-sided Fisher exact test gives p ≈ 1.0).
- **Prior candidate full suite:** `e2e_final.log` shows this selector as the only failure of 115, with the same signature. That fits a pass rate of about one in three.
- **Historical runs (do not count):** older logs `alt_baseline_1-4`, `alt_candidate_1-4`, `base_1248_1-3` and `e2e_1248_1-3` used old main `7cd2bd9` and the pre-integration candidate. They show the same signature and the same flipping. They are consistent with the result above, but none of them is used as evidence.

**Judgement:** the test is nondeterministic. It flips on the same revision (C passes 6 times and fails 10; M passes 5 times and fails 11). It also fails at about the same rate on untouched main `5de7f24`. The failure is pre-existing and not introduced by the candidate.

## 3. Root-cause analysis

The test code is in `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` and is identical in both revisions.

1. Lines 1250-1259: the test creates the case through the UI. The browser is left on `/cases/{caseId}`, where the `CaseDetail` page is mounted and live.
2. Lines 1260-1264: `expect.poll` uses `page.request` (a separate API context) until the case status is `WAITING_FOR_REVIEW`.
3. Lines 1266-1269: `page.waitForResponse(...)` is registered. Its predicate checks only `GET` and pathname `/api/onboarding/cases/{caseId}/documents`. It does **not** require the response to belong to the document loaded by the next `goto`.
4. Line 1270: `page.goto('/cases/{caseId}')` does a full navigation to the same URL.
5. Lines 1271-1273: the test awaits the captured response, then calls `response.json()`. That call fails with `Network.getResponseBody: No resource with given identifier found`.

The old page is still making the same request when the predicate is armed:

- `apps/frontend/src/pages/CaseDetail.tsx:218` mounts `useQuery(documentQueryOptions(...))`, which issues `GET /api/onboarding/cases/{id}/documents` (`apps/frontend/src/caseQueries.ts:167-175`, `apps/frontend/src/api.ts:894-902`).
- `CaseDetail.tsx:508-530`: while the status is `RUNNING` or `RESUMING` (`apps/frontend/src/shared.ts:81-83`), `startAutomationPolling` polls about every 1 s (`apps/frontend/src/automationPolling.ts:18-58`). On every update, including the last one, which sees `WAITING_FOR_REVIEW`, it calls `queryClient.fetchQuery(documentQueryOptions(...), staleTime: 0)`. `onUpdate` runs before the `shouldContinue` check (`automationPolling.ts:38-40`), so the last poll always fires one more documents fetch.

The test's own poll and the page's own poll watch for the same status change at about the same time. When the old page's last documents request is still in flight, or has only just received its headers, as `waitForResponse` is armed:

- The old page's response matches the predicate first. Playwright resolves `waitForResponse` when the response headers arrive (`Network.responseReceived`).
- `page.goto` then commits a new document. Chromium removes the outgoing document's network resources from its DevTools buffer, or cancels the old fetch on unload.
- The later `Network.getResponseBody` call, made by `response.json()`, no longer has that request ID, so it fails with "No resource with given identifier found".

When the old page has already finished its last fetch before the predicate is armed, the first match is the new page's mount fetch, and the test passes. This explains the roughly 1-in-3 pass rate on both revisions.

**Classification:** test-harness race (an ambiguous response predicate around a navigation) combined with Chromium/Playwright response-body lifetime behaviour. It is not an application defect:

- The backend returns status 200. `expect(response.status()).toBe(200)` at line 1272 passes in every failing run. The failure happens only when the body is read.
- The test's real UI assertions (lines 1288-1289) are never reached in failing runs.
- Nothing shows the app returning wrong document data.

## 4. Delta relevance

Exact delta checked: `git diff 5de7f24` (45 tracked files) plus the two untracked tests `apps/backend/tests/test_opq_garden_sim_lim_scenario.py` and `test_simulation_calculation_status.py`.

**Files on the race path have no diff** (`git diff 5de7f24 --quiet`):
- `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
- `apps/frontend/src/pages/CaseDetail.tsx`, `automationPolling.ts`, `caseQueries.ts`, `api.ts`, `shared.ts`
- `apps/frontend/playwright.config.ts`
- `scripts/run_e2e.py`

**Backend documents endpoint:** `GET /api/onboarding/cases/{case_id}/documents` (`apps/backend/app/main.py:3214`, `:3294`) is not modified. The only `main.py` hunks (`@@ -3154`, `@@ -3180`) add `simulation_calculated` and `entity_effective_interests` to the two **ownership** responses. No backend document service or repository file is in the delta.

**`api_models.py`:** the only changes are to `OwnershipAnalysisResponse`, the new `BrowserEntityEffectiveInterest`, and `BrowserOwnershipProvenance`. These are fields of the ownership API, not the documents API.

**Orchestration message** (`zero_touch_orchestration.py:3209-3213`): this is wording only ("…accepted by D-082" changed to "…the scenario's declared POC basis was accepted by D-085"). It appears only in the `poc_accepted` branch, which needs the opt-in hybrid lane. That lane is off for this Mock selector. No state transition, ordering or timing changes.

**Hybrid overlay, POC scenario selection and officer roles:**
- Files: `hybrid_ownership_overlay.py`, `composition.py`, `config.py`, `ownership_discovery.py`.
- These run only when the hybrid / POC lane is configured. That lane is not active for this selector.

**Persistence envelope 14 → 15** (`persistence/models.py`, `mongo_case_store.py`):
- Each case write now validates and serialises against a newer model.
- This applies equally to every save. Its effect is a few microseconds and has no direction relative to the race. It does not change the documents response.

**Frontend ownership changes:** `types.ts`, `OwnershipStructure.tsx`, `UboSummary.tsx` and `OwnershipPathExplorer.tsx` are presentation only. They do not affect the document query, polling, or navigation used by this test.

**Regression impact:**
- No change in the delta plausibly alters the documents request's body.
- The only possible timing influence is indirect. The modified ownership analysis runs in the same pipeline, and the old page fetches ownership next to documents (`CaseDetail.tsx:524-526`). That could shift absolute timing slightly. It cannot create or remove the race, which depends on the test's poll and the page's poll seeing the same transition.
- The data agrees: C passed 37.5% and M passed 31.3%, with an identical signature. The candidate does not cause or worsen the failure.

## 5. Policy analysis

The relevant rules are quoted below. All are in `docs/DEVELOPMENT_WORKFLOW.md` in the candidate tree unless marked otherwise.

- **Stop conditions** (lines 312-328):
  - "Stop the dependent work and record the reason when: … a checker cannot be narrow, deterministic and baseline-green; required evidence fails, is unavailable, or is narrower than the completion claim".
  - "Do not disable tests, add fallback behavior, loosen security, use fake success, or call Mock/Sandbox evidence Live to cross a stop condition."
  - This selector is a checker that is neither deterministic nor baseline-green on `5de7f24` (5/16). The full-suite evidence also failed (114/115). Both conditions apply.
- **Evidence-failure taxonomy** (lines 240-249): "reproducible defect", "missing infrastructure", "stale evidence", "unresolved sponsor authority". There is **no category** for a pre-existing nondeterministic failure in an unrelated test, and there is no waiver for one. Line 249 says "Required missing evidence blocks its dependent acceptance claim, not unrelated lanes". That limits how far the block reaches. It does not turn a failing required check into a pass.
- **Browser requirement** (lines 214-225):
  - "Browser behavior requires the configured Playwright path plus real HTTP/process evidence when that behavior is affected."
  - "The required `e2e` aggregate succeeds only when both shard jobs succeed. Failure, cancellation or a skipped shard cannot pass it. Local execution without `--shard` remains the complete unfiltered suite."
  - The delta affects browser behaviour (ownership pages and `e2e/five-layer-hybrid.e2e.ts`), so the browser suite is required. The complete unfiltered suite did not succeed.
- **TESTING role** (line 33): it must not "report stale/partial/skipped as pass". AGENTS.md says: "Never report stale, skipped, unavailable, or unexecuted evidence as passing."
- **Responsibilities** (line 37): the OWNER owns "sponsor/product decisions, risk/CI exceptions". A risk exception is the owner's decision. It is not a QG disposition.
- **Hosted CI exception** (lines 384-388): this exists only for billing or infrastructure non-execution. It says: "Never report it as passed, waive a required check or bypass branch protection."
- **`fyp-quality-gate` SKILL.md:**
  - "PASS: all current acceptance criteria verified; no required fix remains."
  - "FAIL: any … unverified required criterion … remains."
  - "Classify accepted technical debt only when the planner/gate explicitly permits the limitation and current acceptance remains satisfied."
  - No planner or gate document I was given permits this limitation. The skill also forbids the gate from fixing the test.

**Conclusion:**
- The rules allow no QG disposition that turns a required, failing, nondeterministic check into a PASS. The two available routes are (a) an explicit OWNER risk exception, or (b) a separately assigned remediation that makes the checker deterministic, followed by its own QG.
- The candidate is not at fault (section 4), so FAIL would misattribute the cause.
- The fitting outcome is BLOCKED by a stop condition.

## 6. Verdict

**BLOCKED**

- **Not FAIL.** The candidate does not cause or worsen the failure:
  - pass rates are the same (C 6/16, M 5/16);
  - the signature is identical and appears only at line 1273;
  - none of the test, page, query, polling or documents-endpoint code is in the delta;
  - the root cause is a harness race present on untouched main `5de7f24`.
- **Not PASS.**
  - The full browser suite is required evidence for this change, and it did not pass on the candidate.
  - The checker is not baseline-green, which is a named stop condition.
  - The workflow and QG skill provide no waiver or "known flaky" disposition. Only the OWNER can grant a risk exception, and none is recorded.
  - Rerunning until the test passes would be selective reporting of a nondeterministic required check, so it is not a basis for PASS either.
- **What still stands.** The block applies only to the "full E2E suite green" claim and to whatever depends on it (Stage 3 PASS and publication). Other verified evidence for the candidate is not invalidated. The reviewed tree is unchanged at `1b4b382`.

## 7. Recommended follow-up

1. **Owner decision** (Stage 5 authority), choose one:
   - (a) record an explicit risk exception for selector `authenticated-zero-touch.e2e.ts:1248`, citing this addendum (pre-existing on `5de7f24`, about 31% pass rate, unrelated to D-085/D-086); or
   - (b) authorise a separate, bounded harness-remediation task.
   Either way, a fresh independent gate decision is needed afterwards. This addendum does not grant the exception.
2. **Remediation direction** for a separately assigned CI_TOOLING / test task, not done here:
   - Bind the captured response to the post-navigation document. Options:
     - arm `waitForResponse` only after the navigation has committed, for example by also waiting for `page.waitForURL` or a navigation `'commit'`;
     - check that `response.request().frame()` belongs to the new document; or
     - read the documents through `page.request.get(...)` for the data assertions and keep the browser response only for the "rendered after load" check.
   - Do not weaken the field or state assertions at lines 1273-1289.
   - The same pattern (`waitForResponse` armed before `goto`/`reload` while the previous page may make the same request) also appears at lines 1212-1228 for `case-portfolio`. Audit that site in the same task.
3. If the task lands on main first, re-integrate it into this candidate. Then rerun the full E2E suite (or at least this selector, about 20 times, plus the full suite once) on the new tree, followed by a fresh independent QG.
4. Hosted CI remains billing-blocked. Hosted CI would not resolve this anyway, because the CI `e2e` aggregate also cannot pass with a failing selector.
