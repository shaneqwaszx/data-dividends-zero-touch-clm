# QG Report: E2E documents-response race fix (`authenticated-zero-touch.e2e.ts:1248`)

Reviewer: independent, read-only Quality Gate run. I did not write or remediate this change.
Date: 2026-10-25. Scope: one test-only Playwright harness change.
Change class: test harness for the browser suite (closest row: `CI_TOOLING`, test orchestration). There is no product, configuration, contract or docs change.

## 1. Identity

| Item | Value |
|---|---|
| Worktree | `C:\Users\shane\Desktop\claude-worktrees\e2e-documents-race-20261025` |
| Branch | `fix/e2e-documents-response-race-20261025` |
| HEAD = origin/main | `5de7f24c2dbf678bbb9de02ad627be777bc2f28c` (checked with `git rev-parse HEAD origin/main`) |
| Status | One line: ` M apps/frontend/e2e/authenticated-zero-touch.e2e.ts`. There are no untracked non-ignored files. `apps/frontend/node_modules` is ignored (`!!`) and is not part of the change. |
| Reviewed tree | `1e5466237a4d87f50d550ef6a4e7df190bc2d405`. I copied the real index to a scratch file, then ran `GIT_INDEX_FILE=<copy> git add <path>` and `git write-tree`. The result matches the claim. The real index was not touched. |
| Reviewed blob | `ed09aac06d06d759c859ec139b60a8a2576102a5`. `git hash-object` matches the claim and was the same before and after my runs. The scratch-index entry shows the CRLF-normalised index blob `72caa41`, which is the `index 0f1f024..72caa41` in the diff. |
| File mtime | `2026-10-25 16:42:28 +0800`. This is earlier than every implementer log and has not changed since. |
| Mongo | Task-owned container `e2e-race-fix-mongo` on `127.0.0.1:27132`. I only read its status (Up); I did not change it. |

## 2. Diff review

- `git diff --stat` and `git diff --stat --ignore-cr-at-eol` both report `1 file changed, 3 insertions(+)`, so there is no line-ending churn.
- `git diff | cat -A` shows that all three added lines end in `^M$`, matching the CRLF of the lines around them.
- `git diff --check` exits 0. No task-owned untracked Markdown exists in the worktree.
- The hunk is `@@ -1263,6 +1263,9 @@`. It inserts the lines below just before `const documentsResponse = page.waitForResponse(...)`, and changes nothing else:

```ts
  // Leave the case page first: its own documents fetch would otherwise satisfy this wait
  // and lose its body when the navigation below discards that document.
  await page.goto("about:blank");
```

- **The comment is accurate.** It describes exactly the root cause in the prior addendum.
- **Selector stability.**
  - The test starts at line 1248 and the insertion is inside it, so selector `:1248` does not change.
  - The tests after it move down by 3 lines; for example `:1294` becomes `:1297`, as `full.log` shows.
  - Discovery is dynamic (`playwright --list`, 115 discovered).
  - `git grep` finds no active script, CI or test file that pins line numbers in this file. The only hits are historical `.ai-pipeline` reports, which were already stale, and synthetic fixture strings in `tests/test_run_e2e.py`.
- **Scope.** There are no diffs in `apps/frontend/src`, `playwright.config.ts`, `scripts` or `docs`.
  - E2E files are outside `tsc -b`: `tsconfig.app.json` includes only `src`, and `tsconfig.node.json` includes only `vite.config.ts`. So frontend typecheck, build and vitest are not affected. Playwright's own transpile is exercised by the runs.

## 3. Determinism analysis

### 3.1 Can an old-document response reach a predicate armed after `goto("about:blank")` resolves?

No.

- **What `goto` waits for.** `page.goto("about:blank")` resolves at the default `load` lifecycle of the new about:blank document. That happens after Chromium commits the navigation (`Page.frameNavigated`).
- **The old fetches are dead.** At commit, the outgoing CaseDetail document is unloaded and its in-flight subresource fetches are cancelled with the document. The URLLoaders are torn down, so no further `Network.responseReceived` can be produced for them.
- **Ordering.** CDP events for one target session reach the Playwright client in order. Any `responseReceived` the old document produced before commit was therefore dispatched as a Page `response` event before the `goto` promise resolved.
- **Listener timing.** `page.waitForResponse` attaches its listener only when it is called, after the `await`, and only sees later `response` events.
- **Nothing to replace them.** about:blank runs no app script and starts no network requests. It is not routed through `page.route`, because a network request never happens.
- **Other request sources.** No other page exists in the context (single page, `workers: 1`, `serviceWorkers: "block"`). `page.request` (APIRequestContext) traffic does not emit Page `response` events.

The test's own `expect.poll` uses `page.request`, so it cannot match either.

### 3.2 Does the first matching response now come from the newly loaded case page?

Yes.

- After the predicate is armed, the only document that can issue `GET /api/onboarding/cases/{id}/documents` is the one `page.goto('/cases/{id}')` loads.
- That page fetches documents on mount through `useQuery(documentQueryOptions(...))` (`CaseDetail.tsx:218`).
- The case is already `WAITING_FOR_REVIEW`, so `shouldPollAutomation` is false. The live-status polling effect (`CaseDetail.tsx:508-530`) therefore does not start, and no second polling-driven documents fetch competes.
- **StrictMode double mount.** I checked one remaining case: `main.tsx` uses `StrictMode`, and a dev double-mount can cancel and reissue a signal-consuming query.
  - The cancel happens in the same synchronous effect pass, before any network response can arrive. So a cancelled first attempt never emits a `response` event.
  - The matched response always belongs to the live new document.
  - This was already true for the original test's passing runs.

### 3.3 Can the new page re-navigate before `response.json()`?

No.

- `apps/frontend/src` contains no `window.location`, `location.assign`, `location.replace`, `location.reload` or `href =` assignment.
- In-app routing uses React Router (history API). Same-document navigation does not discard the document's network resources.
- The auth `clearSession` path only does a router `navigate("/")`, again same-document, and only on `401`/logout. None occurs here, and the test then asserts status 200.
- So the matched response's body stays retrievable for the lifetime of the document. The test reads it immediately after awaiting the response.

### 3.4 Authentication across the detour

- The session is a cookie held in the browser context's cookie jar.
  - `api.ts:74` uses `credentials: "include"`.
  - Bootstrap reads `/api/auth/me` (`api.ts:98`).
  - The frontend keeps no auth state in `localStorage` or `sessionStorage`; grep finds no use of either.
- There are no `unload`, `pagehide`, `beforeunload` or `visibilitychange` handlers that could log out.
- Visiting about:blank does not clear the context's cookies. When the app loads again at `/cases/{id}`, it re-bootstraps the session from the cookie, exactly as the original same-URL full navigation already had to do.
- Runtime evidence agrees: the heading and `input[data-review-field]` assertions pass in all runs.

### Determinism conclusion

The change removes the only ambiguous match source, the outgoing case page, and no new one appears. In the old failure mode, the old page's poll and the test's poll both observed the same status transition. That cannot happen now, because the old page no longer exists when the wait is armed.

## 4. Assertion-preservation check

- **Every assertion is unchanged.** Apart from the three inserted lines, the test body is byte-identical (the diff hunk has only `+` lines). That includes:
  - the predicate (GET plus exact pathname);
  - `page.goto('/cases/${caseId}')`;
  - `expect(response.status()).toBe(200)`;
  - the current-document `find`, `state === "REVIEW_REQUIRED"`, the ordered `[field_key, review_status]` list, and `comparison_status === "MATCH"`;
  - `confidence === 0.9` and the `original_extracted_value !== null` check;
  - the visible heading "Document evidence" and `input[data-review-field]` assertions.
- **Nothing was loosened.** No `retry`, `timeout`, `try/catch`, `.catch`, `test.fixme/skip` or soft assertion was added. Config still has `retries: 0`, `trace: "off"`, `timeout: 120_000` and expect `15_000`, all unchanged.
- **Same user-visible scenario.** The test still does a full document load of `/cases/{id}` with a fresh JS/QueryClient state, as before, and still asserts the rendered review UI.
  - The only difference is the referrer document: about:blank instead of the same URL.
  - Nothing in the app depends on the previous document, because SPA state does not survive a full navigation in either case.
- **Harness guards still hold.**
  - `guardLocalNetwork` (`authenticated-zero-touch.e2e.ts:56-71`) routes `**/*` through `handleBrowserRoute` (`playwright.config.ts`).
  - about:blank produces no routed request, so it cannot be classified `BLOCKED_*` and cannot add a violation. `afterEach` `assertNoViolations()` passed in every run.
  - The relative `goto('/cases/...')` resolves against the configured `baseURL`, not against about:blank.
  - `scripts/run_e2e.py` has no navigation or URL guard that about:blank could trip. It only assigns owned origins: `PLAYWRIGHT_BASE_URL`, `CLM_E2E_BACKEND_ORIGIN` and the proxy target.

## 5. The `:1212` audit (`case-portfolio` waitForResponse/reload, lines 1213-1228, unchanged)

I agree with the implementer's claim that there is no race of this kind at this site.

- **No polling.**
  - `casePortfolioQueryOptions` (`caseQueries.ts:147-155`) has no `refetchInterval`, and no `refetchInterval` exists anywhere in `src`.
  - The defaults in `queryClient.tsx` set `refetchOnWindowFocus: false`.
  - `CaseQueue.tsx` has only a 300 ms search debounce. The search is empty at that point, so the debounce produces no fetch.
  - There is no `fetchQuery` polling loop for the portfolio, unlike documents in CaseDetail.
- **The old page is quiescent before the first reload.**
  - The test asserts that the row for the newly created case shows "GoldTier target submitted", "Case duration:" and "Last updated:".
  - List caches are only invalidated, never `setQueryData`-populated with the new case (`caseCreatedEffect` and `caseSummaryMutationEffect` in `caseQueries.ts`). The login-time prefetch (`auth.tsx:91`) predates the case.
  - So the visible row proves that the post-mount portfolio fetch has completed.
  - CaseDetail's polling is cleaned up when it unmounts on the SPA navigation to Cases. Nothing else invalidates lists while CaseQueue is mounted.
- **Before the second reload,** the test itself asserts `portfolioRequests` did not grow over 750 ms. That proves no new portfolio request started in that window.
- **Residual (P3, informational, no action required).** The 750 ms check counts request starts, not completions. If a reload issues two portfolio requests (the prefetch key and the CaseQueue key, which the test's `<= +2` bound allows) and one were still in flight more than 750 ms later, the second wait could match it. That straggler would belong to the outgoing document, so the reload would discard it and the failure would carry the same `getResponseBody` signature. In practice this is not reachable: local loopback portfolio responses take milliseconds, far inside 750 ms. There is no observed occurrence:
  - the test containing this site (selector `:1044`) passed in the full suite (lifecycle 13/115);
  - it never failed in the prior addendum's full-suite evidence.

  An implementation run is not required for this. The same `about:blank` technique could be applied there later if it ever flakes.

## 6. Evidence verification

**Implementer's isolated runs (`race-fix\run_1.log` … `run_20.log`):**
- I read all 20. Each shows `E2E SELECTOR FILE: discovered=115; selected=1`, `1 passed (3.1s–3.6s)` and `E2E SUITE PASS: 1 configured selectors passed in isolated lifecycles`. There are no failures.
- **Timing.** The runs are serial, about 9 s apart, between 16:43:01 and 16:45:56. All are later than the file's mtime (16:42:28), which has not changed since.
- **Limitation.** The logs do not embed a content identity, so for these runs content binding rests on the mtime. My own runs below are bound by blob hash.

**Implementer's full suite (`race-fix\full.log`, `full_results.json`):**
- `full_results.json`: `status: PASS`, `complete: true`, `mode: full`, `discovered_count: 115`, `selected_count: 115`, `counts: {PASS: 115}`. All 115 lifecycles have `result: PASS` and `exit_code: 0`. It started at `2026-10-25T08:46:08Z` (16:46:08 local, after the mtime) and took 1555.7 s.
- `full.log` ends with `E2E SUITE PASS: 115 configured selectors passed in isolated lifecycles.`
- Lifecycle 14 is `:1248` (`1 passed (3.2s)`).
- **This proves the run used the changed file.** The selectors after it appear shifted by +3 (`:1297`, `:1445`, `:1573`, `:1685`).
- Every "failed"/"retry" text match in the log is a test title, not a result.

**My independent reproduction:** in the same worktree and Mongo port, strictly serial, with the command from the brief:
- Blob `ed09aac…` was confirmed before and after the runs.
- Result: **8/8 PASS**. Results are in `qg-race-fix\res_1..8.json` (each `status: PASS`, `counts {PASS: 1}`) and logs in `qg-race-fix\qg_run_1..8.log`.
- Playwright time was 3.2–3.4 s, except one run at 13.8 s. That run's case took longer to reach `WAITING_FOR_REVIEW` inside `expect.poll`; it was not a retry.
- `git status` was unchanged afterwards.

**Combined:**
- Fixed tree: **28/28** isolated passes (20 by the implementer plus 8 by me), and the full suite passed 115/115.
- Untouched main had 5/16 and the other candidate 6/16 in the prior addendum, with an identical failure signature at the `response.json()` line.
- If the old pass rate (about 0.34) still applied, the chance of 28 consecutive passes would be about 10^-13. The race is eliminated, not merely made less likely.

**Not run, and not required for this class or scope:**
- backend pytest, Ruff, mypy, vitest, typecheck and build. E2E files are outside those tools, and no `src` or backend file changed.
- `pre_pr_check.py`. This is an uncommitted implementation handoff, not publication.
- Hosted CI. Not observed here.

## 7. Verdict

**PASS**

Findings:

| ID | Grade | Finding |
|---|---|---|
| — | P0–P2 | None. |
| F1 | P3 (informational) | The implementer's 20 isolated-run logs carry no embedded content identity. Binding rests on the file mtime. The full-suite log (line shift) and this gate's 8 blob-bound runs do bind the content. No action required; future logs could record `git hash-object` output. |
| F2 | P3 (informational) | The `:1212` portfolio site has a theoretical residual: the 750 ms quiescence counts request starts, not completions (section 5). It has no practical reach and no observed failure. No action required. |

Statements:
- **Changed:** test-harness behaviour only.
- **Unchanged:** API/types, schema, connectors, configuration, business rules, mappings, auth/security, architecture, provider status, and product runtime behaviour.
- **Determinism:** the fix is deterministic by construction (section 3), and no assertion is weakened (section 4).
- **What this verdict covers:** only tree `1e5466237a4d87f50d550ef6a4e7df190bc2d405` / blob `ed09aac06d06d759c859ec139b60a8a2576102a5`. Any content change needs a fresh review.
- **Next authorized actions** (owner):
  - commit and publish under the five-stage workflow, with explicit owner authorisation;
  - then re-integrate into the D-085/D-086 candidate and rerun the browser evidence the prior addendum blocked.
- This gate does not commit, push or publish.
