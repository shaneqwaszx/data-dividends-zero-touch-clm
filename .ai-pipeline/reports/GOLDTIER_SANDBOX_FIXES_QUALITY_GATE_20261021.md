# GoldTier Sandbox fixes — independent Quality Gate (2026-10-21)

Procedure: `fyp-quality-gate`, adapted from its report template for a bounded
integration and fix change. The `integration-security-review` checklist and
`external-provider-integration` were also applied. The reviewer did not write this
change. During the review it changed nothing except this report.

## 1. Outcome

**Verdict: PASS.** No required fix remains.

- Recovery is faithful. F1 is correct, fail-closed and within scope. The teammate
  frontend is preserved.
- No path turns a failure into `NO_MATCH` or success.
- No raw body, header, `user_id` or PII reaches the browser, persistence, events or logs.
- Section 5 lists four advisory notes. None of them is a defect.
- This verdict does not authorize commit, push, PR or merge.

## 2. Reviewed identity (frozen)

- Worktree: `C:/Users/shane/Desktop/FYP-Integration/goldtier-sandbox-fixes-20261021`.
- Branch: `integration/goldtier-sandbox-fixes-20261021`.
- HEAD: `f140d90767306519c56d088e3fd7e76027d5021e`.
- Tree: `3770aadbb99bf27e03360c4cab36b23341ec2a7f`.
- The working tree was clean at the start and at the end.
- Base: `origin/main` = `59e9e75bc8ac2ace73a43b8098732d3030a4ac8c`. `git ls-remote` confirms the
  remote main is the same commit. HEAD is ahead 1 and behind 0.
- Reviewed diff: `git diff 59e9e75..f140d90`, exactly 9 files:
  - the integration report (A);
  - `api_provider_sandbox.py`, `connectors/goldtier_xpi.py`, `services/clm_orchestration.py`
    and `services/onboarding.py`;
  - `tests/test_goldtier_sandbox_diagnostics.py` (A);
  - `GoldTierSandbox.test.tsx` and `pages/GoldTierSandbox.tsx`;
  - `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md`.

## 3. Criteria

| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Faithful recovery of `d676966` | PASS | `api_provider_sandbox.py`, `GoldTierSandbox.tsx` and its test have blobs identical to `d676966`. `goldtier_xpi.py`, `onboarding.py`, the test and the doc equal `d676966` plus exactly the F1 delta (`git diff d676966 f140d90`). Main left all 8 code/doc paths unchanged between `245f8c9` and `59e9e75`. `d676966`'s `.ai-pipeline` files were not carried. |
| 2 | `4fd0ad4` excluded; teammate frontend preserved | PASS | `4fd0ad4` is not an ancestor of HEAD or of `d676966`. The only frontend changes are the HR console page and its test. Stages, navigation, Submission Readiness, the package view and Review & Send are untouched. |
| 3 | F1 safe, in scope and consistent | PASS | See §4. |
| 4 | Line endings preserved in `clm_orchestration.py` | PASS | Base: 1,363 CRLF and 498 LF lines. HEAD: 1,371 CRLF and 498 LF lines. All 14 changed lines (+11/−3) are CRLF. There is no line-ending churn. |
| 5 | Investigation claims (spot check) | PASS | FAILED disposition → "GoldTier Search failed. This does not mean the customer does not exist" (`api_models.py:1977-1982`); NO_MATCH branch → `SKIPPED`. `ReviewAndSend.tsx:244-250`: non-match/non-exact → "Target match requires review". `dc2dd75`/`6b68ae1` are not ancestors of main (squash merge), but their content is on main: `e2e_backend_server.py` and `pr95-dashboard.e2e.ts` blobs are identical, and `test_run_e2e.py` carries the change with later counts. "Already on main" holds by content only. |
| 6 | No Live/Sandbox overclaim | PASS | The doc says local injected transports only, "no GoldTier request was made", `SANDBOX_PARTIAL`, and that the 18–19 Oct HTTP 500 is unexplained. Project state and provider classification are unchanged. |
| 7 | No false success | PASS | Every exception path keeps FAILED/FAILED and the `GOLDTIER_SEARCH_FAILED` blocker. Readiness depends on checkpoint status (`clm_orchestration.py:1657-1669`), never on `status_code`. A JSON 400/5xx stays a FAILURE result, and the console projects `NOT_ASSESSED`. |
| 8 | Safe diagnostics | PASS | Fixed trusted codes and messages only. `observed_goldtier_xpi_search_status` bounds statuses to 200–599, matching the checkpoint's `ge=200`; 1xx falls back to 503. Codes match `SafeTargetErrorCode`. The changed modules have no logging. Tests assert that `PRIVATE_MARKER` and `BACKEND_USER` are absent from the CLM record and events and from API bodies. |
| 9 | Mutation, ledger and no-replay unchanged | PASS | The ledger `_run_required_stage` still uses `public_connector_error`, so it records `CONNECTOR_FAILURE` with the infrastructure flag. Mutation decode and too-large errors stay `MutationOutcomeUncertain`. Only GET calls are observed. |
| 10 | Mock vs Sandbox | PASS | Non-XPI and Mock `ConnectorError` falls back to `public_connector_error`, giving `CONNECTOR_FAILURE`/503; the `untrusted-connector-error` case covers this. Classification is unchanged. |
| 11 | Tests meaningful | PASS | Run against `d676966` code (`app` resolved inside that worktree), the new and updated case-level selection gives 11 failed and 2 passed. The 2 passes are the intended baselines (controlled JSON 500 and untrusted `ConnectorError`). |

## 4. F1 assessment (case-level CLM early Search)

- **Consumers.**
  - `blocker_decision_policy` maps neither `CONNECTOR_FAILURE` nor `GT_XPI_*`, so its
    classification is unchanged. FAILED creates no exception blocker code.
  - Zero-touch `_technical_failure` uses `checkpoint.code` for display and events only. The
    only keyed code is `CLM_TARGET_OUTCOME_UNCERTAIN` (`zero_touch_orchestration.py:722`).
  - `api_models` projects the trusted code as `blocker_code`. Its text depends on
    disposition.
  - `CaseDetail.tsx:1353-1356` and the assistant `context.py` show the code and status
    verbatim.
  - No tracked consumer depends on `CONNECTOR_FAILURE`; a `git grep` finds only
    `errors.py`, the new test and the docs.
- **Domain.** `GoldTierSearchCheckpoint.status_code` (200–599) and `SafeTargetErrorCode`
  are satisfied. `_materially_equivalent_search` compares `status_code`. A varying
  observed status therefore makes a confirmation-time FAILED→FAILED recheck return for
  review, which is the more conservative direction.
- **Scope and blast radius.** The preflight on `d676966` limited the trusted projection to
  the console. F1 extends it only to the CLM early checkpoint's code, message and status,
  which are diagnostic. Ledger, read-back, verification, recovery and mutations keep
  `public_connector_error`. This matches the assigned "case-level Search failure detail"
  and creates no new owner, schema or policy.
- **Initial Search.** Both `_initial_search_failure(exc.code, …)` sites pass the observed
  status. The `SEARCH_*` codes and the blocker policy are unchanged.
- **Architecture.** `clm_orchestration.py` and `onboarding.py` now import helpers from
  `app.connectors.goldtier_xpi`. Services already import concrete connector modules
  (`mock_ownership`, `acra`, `registry_ownership`, `local_document_runtime`). There is no
  import cycle, and `check_architecture.py` passes.

## 5. Findings (ranked; none blocking)

- **QG-1 LOW (test gap):** the repair/recheck initial-Search site has no committed
  regression test (`onboarding.py:1012-1014`, in `_run_initial_identity_search` via
  `repair_initial_identity_and_recheck`). Only the `create_staged_case` site
  (`onboarding.py:1744-1746`) is tested.
  - This gate verified the site with a read-only scratch probe using injected transports.
    On HEAD, the recheck retains 500 (non-JSON 500), 401, 504 (timeout table value) and
    200 (malformed 200).
    - On `d676966` the same cases retain 503, 503, 504 and 502.
    - Disposition is FAILED in every case, and only GET calls are made.
  - A committed test would be good hardening, but nothing requires it.
- **QG-2 INFO (diagnostic coherence):** a malformed HTTP-200 Search now retains
  `status_code` 200 on FAILED evidence. This is documented as "observed 200-599".
  - On initial Search, the pre-existing double re-map (`onboarding.py:1025-1026` and
    `1756-1760`) shows that as `SEARCH_SERVICE_UNAVAILABLE` with status 200 in the case
    technical details.
  - A retained 503 can be observed or synthesized, and the field does not say which.
  - It is truthful and not a false success, because disposition, status, readiness and
    blockers are all FAILED. The double re-map is pre-existing and out of scope (`d676966`
    gate F-6).
- **QG-3 INFO (architecture):** an XPI-specific projection helper is imported into
  provider-neutral services. This has precedent and the checker accepts it. A future
  change could move the trusted XPI table beside `errors.py`.
- **QG-4 INFO (report precision):** the integration report's heading "Recovered from
  d676966 (byte-identical paths)" is broader than the facts. Only 3 of the 7 paths are
  verbatim at HEAD; the other 4 equal `d676966` plus F1. The report also says "services
  import one XPI projection helper", but CLM imports two. Neither point is in the code.

## 6. Checks run by this gate (on HEAD `f140d90` unless noted)

| Check | Result |
|---|---|
| Interpreter check: `app.__file__` resolves inside the worktree | confirmed (Python 3.12.10) |
| pytest on the 7 focused files: `goldtier_sandbox_diagnostics`, `goldtier_xpi_sandbox`, `provider_sandbox_api`, `clm_orchestration`, `zero_touch_orchestration`, `onboarding_resilience`, `blocker_decision_policy` | **394 passed**, 0 failed, 0 skipped (289 s) |
| XPI ledger/recovery regression, 11 files: `garden_uen_partial_resume`, `policy_provider_recovery`, `s3_*` ×5, `slice_d_mock_goldtier`, `target_reliability_recovery_ux`, `zero_touch_database_happy_path`, `slice_c_real_mongo` | 179 collected: **175 passed**, 4 skipped (physical Mongo not configured), 0 failed |
| Falsification on `d676966` (`-k "case_level or observed_search_status"`, test file from HEAD) | 11 failed, 2 passed (baselines), as expected |
| Repair-site probe (scratchpad, both trees) | see QG-1 |
| `ruff check . --no-cache` / `mypy app` (scratch cache) | pass / no issues (127 files) |
| Frontend `npm run typecheck` / `npx vitest run` | pass / **58 files, 991 tests passed** |
| `tsc -b` and `vite build` (output to scratchpad) | pass (existing >500 kB chunk warning) |
| `check_project_state`, `check_architecture`, `check_secrets`, `check_external_provider_readiness`, `check_tooling_config`, `check_policy_authority` | all PASS |
| `scripts/pre_pr_check.py` (clean committed tree) | SUMMARY: PASS (0 unsafe, 0 warnings) |
| `git diff --check 59e9e75..f140d90` (includes both new files) | clean |
| Focused E2E: `run_e2e.py --grep "S1 logout and interactive role changes"`, ports 18765/14273, Mock, no Mongo; opens the GoldTier Sandbox page | **1 passed** |

**Not run by this gate.** These remain implementer-reported and were not independently
verified:

- full backend pytest (reported 2,850 passed, 171 skipped);
- full E2E (reported 112/112 with a disposable `mongo:7`);
- the 165 physical-Mongo tests. They are not required, because there is no persistence
  or schema change.

No E2E spec exercises console Search failures. Browser-side diagnostics evidence is
therefore the jsdom component tests plus the in-process HTTP API tests. The real GoldTier
Sandbox was not contacted.

## 7. Security summary

- Output is limited to trusted codes and messages, a bounded integer status, the
  server-generated `correlation_id` (also sent as `X-Correlation-Id`) and `elapsed_ms`.
- The console 503 detail has exactly that key set. No `Retry-After` or `WWW-Authenticate`
  header is forwarded, and the frontend renders values as escaped text.
- The real transport still enforces TLS 1.3 and certificate verification, follows no
  redirects and bounds reads.
- The worktree contains no `.env` file, and none was read. No secrets were found.

## 8. Readiness

- **Publication:** eligible at exact `PASS` with this frozen content (HEAD `f140d90`,
  tree `3770aad`). It still needs explicit owner authorization. Committing this report
  is report-only and must leave the 9 reviewed files unchanged.
- **Real GoldTier and Live:** not verified, and the classification stays
  `SANDBOX_PARTIAL`. XPI 401/403/404/429 Search semantics remain project-defined (Q-011).

## 9. Git status

- HEAD `f140d90` on `integration/goldtier-sandbox-fixes-20261021`. Nothing is staged.
- The only change is this new untracked report.
- No fix, commit, push, reset, stash, branch change or merge was made. The other
  worktrees, `pr98-e2e-mongo-20261021` and `clm_poc` were not touched.
