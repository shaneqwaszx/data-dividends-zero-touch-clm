# AI Assistant Model Management (D-093) - Independent Quality Gate, Re-gate R2

## 1. Outcome

**PASS.**

The delta fixes all three smoke-test findings (S-1, S-2 and S-3). The hooks are correct and the new tests are meaningful: each one fails when its fix is removed. The delta adds no server, API, permission or guardrail behaviour. The full frontend suite passes, 1,121 of 1,121 tests. One low, non-blocking observation is recorded (O-1). It needs no fix before the owner's merge decision.

## 2. Reviewed identity

| Item | Value |
| --- | --- |
| Worktree | `C:/Users/shane/Desktop/claude-worktrees/assistant-model-management-20261027` |
| Branch | `feat/assistant-model-management-20261027` (pushed; Draft PR #121) |
| Reviewed HEAD | `555deb1f110a1e2f0651b06c9e21eeffea44351d` |
| Reviewed tree | `ecb7aada76c2fd5441425337899d2e77cdcf4436` |
| Delta reviewed | `git diff aea87b9 555deb1`: `apps/frontend/src/pages/AiModelManagement.tsx` (+23/-5) and `apps/frontend/src/pages/AiModelManagement.test.tsx` (+73/-2) |
| Since R1-reviewed content | `git diff ffeeddf 555deb1 --stat`: the 2 files above plus `.ai-pipeline/reports/AI_ASSISTANT_MODEL_MANAGEMENT_QUALITY_GATE_R1.md` (added in `aea87b9`). Nothing else changed. |
| Previous gate | R1 on `ffeeddf`, PASS |
| `origin/main` | `23c45a7` |
| Blob identity | `AiModelManagement.tsx` = `3ba29f2`, `AiModelManagement.test.tsx` = `e090cab`. The working copy matched HEAD at the end of the review. |

HEAD and the tree were the same at the start and at the end of the review. The working tree was clean apart from this report.

## 3. Findings re-checked

### S-1: the audit table did not refresh after a background qualification. **FIXED**

- **Fix, part 1** (`AiModelManagement.tsx:144-151`)
  - `runningId` is taken from `overviewQuery.data?.running?.qualification_id`.
  - A `useRef` holds the run the page last followed.
  - An effect calls `invalidateQueries({ queryKey: modelManagementQueryKeys.audit(actor.user_id), exact: true })` when a followed run (non-null ref) changes or ends.
- **Fix, part 2** (`AiModelManagement.tsx:140`): the audit query gets `refetchInterval: AUDIT_REFRESH_MS` (15,000 ms).
- **Transitions traced:**

| Transition | Result |
| --- | --- |
| Mount | No invalidation: the ref starts `null`. |
| Cached overview shows a run | Ref is set and nothing is invalidated. |
| Run ends (`id` to `null`) | Invalidated. |
| Run A replaced by run B | Invalidated. |
| A new run starts (`null` to `id`) | Not invalidated by the effect. The start mutation's `onSettled` already invalidates `root`. |
| StrictMode double effect | The second run sees ref equal to `runningId`, so there is no spurious invalidation. |

- **Hook correctness**
  - The dependency array `[runningId, queryClient, actor.user_id]` is complete. `modelManagementQueryKeys` is a module constant and the ref is stable.
  - Invalidating the audit query cannot change `runningId`, so there is no render or effect loop.
  - The effect creates no subscription or timer, so there is nothing to clean up.
  - React Query clears the interval when the observer unsubscribes on unmount (`#clearRefetchInterval`).
- **Cache scoping**
  - Both keys are still `["auth", userId, "assistant-models", ...]`.
  - `clearSessionQueries` (`queryClient.tsx:22-27`: `cancelQueries` then `clear`) still removes them on logout or a 401.
  - The existing logout or identity-change test, which checks that the sentinel is removed from the cache, still passes.
- **Polling bound**, checked in the installed `@tanstack/query-core` 5.102.8 (`build/modern/queryObserver.js:158-164`)
  - The interval runs only when `refetchIntervalInBackground || focusManager.isFocused()`.
  - `isFocused()` is `document.visibilityState !== "hidden"` (`focusManager.js:48-50`).
  - No app code sets `refetchIntervalInBackground`, so polling pauses in hidden tabs.
  - The query has `retry: false`.
  - The load is one GET every 15 s per visible open page. A successful `GET /assistant/admin/models/audit` writes no audit row (`model_admin.py:577-581`).
  - This is bounded and acceptable.
- **Test** (`AiModelManagement.test.tsx:254-288`)
  - It uses fake timers (`shouldAdvanceTime`), restored in a `finally` block.
  - The first overview returns `running`; the next one does not.
  - After `RUNNING_REFRESH_MS + 100` the audit count must be 2. That is well before 15 s, so only the invalidation can satisfy it.
  - After `AUDIT_REFRESH_MS + 100` the count must be 3, which needs the interval.
- **Reviewer mutation checks**: the source was temporarily changed, then restored byte for byte, and the blob hash was confirmed equal to HEAD.
  - Invalidation removed: the S-1 test fails with `expected 1 to be 2`.
  - `refetchInterval` removed: the S-1 test fails with `expected 2 to be 3`.

  Both halves of the fix are therefore covered independently.

### S-2: the rollback heading read "Roll back Environment baseline?". **FIXED**

- `AiModelManagement.tsx:225` now renders `Roll back to ${name}?` for a rollback and `Activate ${name}?` for an activation.
- `name` is `overview.last_good.display_name`, set by the rollback button (line 216).
- The test (`:290-300`) checks the exact `#confirm-heading` text.
- **Mutation check:** going back to the old wording fails the test with `expected 'Roll back Environment baseline?' to be 'Roll back to Environment baseline?'`.

### S-3: "GATES_FAILED:G-7" was shown as "Gates failed:g-7". **FIXED**

- **Fix:** `readable()` (`AiModelManagement.tsx:51-58`) now handles the `GATES_FAILED:` prefix before the lower-casing fallback. It shows `Gates failed: ` followed by the ids, joined with `", "`, with their spelling kept.
- **Producer:** the only source is `assistant_eval/qualification.py:212-216`. It emits `GATES_FAILED:` plus the comma-joined failed gating ids, and only when at least one gating gate failed, so the list is never empty.
- **Where the codes appear:** the qualification detail (`:81`) and the audit "Code" column (`:306`) both use `readable()`, so they show the same text.
- **Other codes:** the `REASON_TEXT` mapping and the generic fallback are unchanged; `QUALIFICATION_BUSY` still reads "Qualification busy".
- **Rendering safety:** values are rendered as React text, so there is no markup injection.
- **Test** (`:302-318`): it checks `readable()` directly and the rendered detail after clicking "Failed".
- **Mutation check:** bypassing the prefix branch fails the test with `expected 'Gates failed:g-6,g-7' to be 'Gates failed: G-6, G-7'`.

## 4. Regression and scope

- **Unchanged earlier page behaviour:** acknowledgement gating (`:227-234`), disabled actions for remote or unusable rows (`:255`, `:267-272`) and `safeError` (`:64-66`). The 8 earlier page tests still pass.
- **Exports:** `readable`, `RUNNING_REFRESH_MS` and `AUDIT_REFRESH_MS` are new exports from the page module. The module already exported `modelManagementQueryKeys`, so this adds no new pattern.
- **No change to:** the server, assistant, backend, API or types, schemas, permissions or capabilities, guardrails, configuration, or the Mongo or persistence layer.
- **Durable docs:** no durable document describes the page's refresh timing, so none is made stale.

## 5. New findings

| ID | Severity | Finding |
| --- | --- | --- |
| O-1 | LOW, observation, non-blocking | **Where:** `AiModelManagement.tsx:140`. **Issue:** the 15 s audit interval keeps running while the query is in an error state. In 5.102.8 the interval callback does not check the query status.<br>**Scenario:** an HR user's `MODEL_CONFIG_MANAGE` capability is removed while the page stays open in a visible tab. Each poll then gets a 403, and `admin()` writes an `ACCESS_REFUSED` row (`model_admin.py:391-395`). That is about 4 rows a minute for that tab.<br>**Why the impact is small:** refused rows have their own cap (`MAX_REFUSED_EVENTS = 1000`, `model_admin_store.py:30`). They cannot evict change outcomes, which are never pruned. They can, however, push useful rows out of the newest-100 window that `GET /audit` returns by default. A 401 still ends the session through the existing transport handler.<br>**Optional later hardening:** make the interval conditional, for example `(q) => (q.state.status === "error" ? false : AUDIT_REFRESH_MS)`. This is not required for the owner's merge decision. |

No other defects were found.

## 6. Commands and counts

All commands ran in this session against `555deb1`.

| Command (location) | Result |
| --- | --- |
| `git rev-parse HEAD HEAD^{tree} origin/main` (root) | `555deb1…` / `ecb7aada…` / `23c45a7…` |
| `git diff ffeeddf 555deb1 --stat` (root) | 3 files: the 2 frontend files plus the R1 report |
| `git diff aea87b9 555deb1 --stat` (root) | 2 files, +98/-5 |
| `npx tsc -b --pretty false` (apps/frontend) | exit 0. Repo status unchanged afterwards. |
| `npx vitest run src/pages/AiModelManagement.test.tsx` (apps/frontend) | 1 file, 11 passed |
| `npx vitest run src/pages/AiModelManagement.test.tsx -t "S-1"` with the invalidation removed (temporary, restored) | S-1 failed (`expected 1 to be 2`) |
| `npx vitest run src/pages/AiModelManagement.test.tsx -t "S-"` with the interval removed, the S-3 branch bypassed and the S-2 wording reverted (temporary, restored) | 3 of 3 S-tests failed with the messages in section 3 |
| `git hash-object` vs `git rev-parse HEAD:<path>` for both files after restoring | Equal (`3ba29f2`, `e090cab`). `git status --short` was clean. |
| `npx vitest run` (apps/frontend, full) | 65 files, 1,121 passed. The R1-reused baseline was 1,118; the delta adds 3 tests. |
| `git diff --check aea87b9 555deb1` (root) | exit 0, no output |
| CR count in the HEAD and `aea87b9` blobs of both files | 0 and 0. Both files are LF-only before and after, so there is no EOL churn. |

**Backend and assistant: not rerun.**

- `git diff ffeeddf 555deb1` touches no backend or assistant path.
- The R1 evidence on `ffeeddf` is therefore still valid and is reused:
  - assistant: 727 passed;
  - ruff, format and mypy: clean;
  - backend capability and auth tests: 73 passed;
  - secret scan: passed.
- The secret scan was not rerun. The delta is TypeScript UI text, hooks and tests and adds no credential-like content (inspected by hand).

## 7. Limitations

- I did not rerun a live browser or Playwright check. The S-1 to S-3 claims rest on code inspection, unit tests with timer control, and reviewer mutation checks. The owner's developer smoke test is the browser-level evidence for the original symptoms. I did not repeat it against `555deb1`.
- I did not observe the hidden-tab pause at runtime. It was established from the installed library source.
- There is no ESLint (`react-hooks`) configuration in `apps/frontend`. The hook dependencies were checked by hand.

## 8. Readiness

- This gate's verdict, **PASS**, covers exactly `555deb1` (tree `ecb7aada`).
- Together with the R1 PASS on the unchanged backend and assistant content, the branch is ready for the owner's merge decision on PR #121. Publication is already authorised; the merge is the owner's.
- If content changes after this review, a fresh review of the changed scope is required.
- O-1 is optional later hardening.
- This report is the only file the reviewer wrote. Nothing was staged, committed or pushed.
