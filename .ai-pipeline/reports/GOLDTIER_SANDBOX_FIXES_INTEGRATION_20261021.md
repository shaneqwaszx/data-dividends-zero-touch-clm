# GoldTier Sandbox fixes — integration report (2026-10-21)

**Outcome:** GoldTier-only candidate on `integration/goldtier-sandbox-fixes-20261021`,
based on `origin/main` `59e9e75` (PR #98). Frontend consolidation is excluded. This is
implementer evidence only; the independent verdict lives in the separate Quality Gate
report.

## Identity and scope

- Worktree: `C:/Users/shane/Desktop/FYP-Integration/goldtier-sandbox-fixes-20261021`.
- `BASE_SHA` = `origin/main` = `59e9e75bc8ac2ace73a43b8098732d3030a4ac8c`.
- Change classes: `EXTERNAL_PROVIDER`, `BACKEND_DOMAIN`, `BACKEND_API`, `FRONTEND_UI`.
- Preserved, unmodified: `integration/onboarding-goldtier-20261020` (`5e550bc`) and the
  source branches `claude/goldtier-sandbox-diagnostics-20261019` (`d676966`),
  `codex/onboarding-goldtier-consolidation` (`4fd0ad4`) and
  `claude/priceless-goldwasser-38faa0` (`6b68ae1`).

## Recovered from `d676966` (byte-identical paths)

Main did not change any of these paths between `d676966`'s base `245f8c9` and `59e9e75`.
The trial merge was clean.

- `apps/backend/app/connectors/goldtier_xpi.py`: Search status classification; a
  non-JSON 5xx becomes `GT_XPI_SERVICE_UNAVAILABLE`, 401/403 becomes
  `GT_XPI_AUTHORIZATION_FAILED`, and 429 becomes `GT_XPI_RATE_LIMITED`. These failures
  retain only a bounded `upstream_status`. Mutation handling is unchanged.
- `apps/backend/app/services/onboarding.py` (`search_sandbox_target` only): a failed
  Search is never resolved into `NO_MATCH`. A Search with no comparable feature is
  `NOT_ASSESSED`.
- `apps/backend/app/api_provider_sandbox.py`: the HR console Search reports a
  controlled `FAILURE` as a `FAILED` timeline entry. Responses carry trusted
  `error_code`, `upstream_status`, `correlation_id` and `elapsed_ms`.
- `apps/frontend/src/pages/GoldTierSandbox.tsx` and its test: the console separates
  retrieval from advisory resolution and never shows a failed Search as no match.
- `apps/backend/tests/test_goldtier_sandbox_diagnostics.py`, plus one reconciliation
  section in `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md`.

Not carried: the five historical `d676966` `.ai-pipeline` reports, which stay on the
preserved branch, and `4fd0ad4` in full.

## Newly fixed defect

**F1 — case-level Search lost the GoldTier failure category and observed status.**
This is the same defect class as GT-FIX-03, which `d676966` fixed only for the console.

- Before: the CLM early Search projected every XPI `ConnectorError` through
  `public_connector_error`, whose trusted table holds only ACRA families. A GoldTier
  timeout, a non-JSON 500, a 401/403/429, a 404 or a malformed 200 therefore surfaced
  in the case Search stage and technical failure as `CONNECTOR_FAILURE` with a
  synthesized status 503.
- Before (initial pre-registry Search): the path likewise dropped an observed status. A
  non-JSON 500 retained 503, while a JSON-bodied 500 retained 500.
- Fix: the CLM path uses the existing trusted XPI projection,
  `public_goldtier_xpi_search_error`. Both paths retain an observed status only when it
  is 200–599, via the new helper `observed_goldtier_xpi_search_status`. Otherwise they
  keep the prior synthesized value.
- Unchanged: non-XPI and Mock errors (`CONNECTOR_FAILURE`), the initial-Search
  `SEARCH_*` codes, blocker policy, ledger/read-back/verification paths and mutations.
- The outcome stays `FAILED` and every target mutation stays blocked.
- Reproduced: 10 of the new cases fail against the `d676966` code. Six CLM cases
  recorded `CONNECTOR_FAILURE`, and four initial-Search cases recorded 503 instead of
  401/403/429/502. The two baseline CLM cases (a controlled JSON 500 and an untrusted
  connector error) pass both before and after.
- Regression tests:
  `test_case_level_early_search_failure_keeps_trusted_category_and_observed_status`
  (8 cases), `test_observed_search_status_is_retained_only_for_trusted_retainable_statuses`,
  and the updated `test_case_level_initial_search_failure_stays_failed_without_mutation`.

`clm_orchestration.py` has mixed line endings at `HEAD` (1,363 CRLF and 498 LF). The
original endings were preserved, so the diff is limited to the 14 semantic lines.

## Investigated, no defect found

- Case Search UI after PR #97/#98. A FAILED checkpoint shows as a `FAILED` node, with a
  stage badge in the attention tone. The text says a failed Search does not prove
  absence. The recheck entry depends on checkpoint status, not code, and Review & Send
  shows "Target match requires review", never "New customer".
- Shell/Policy/Amend mapping, ordering, no-replay and uncertain outcomes are covered by
  the existing suites; no changes were made there.
- Harness fixes `dc2dd75` and `6b68ae1` are already on main via PR #98, with identical
  content, so they are not carried.

## Verification (worktree, uncommitted candidate before freeze)

All runs used Windows 11, Python 3.12 from the repo `.venv` with `app` pinned to this
worktree, and Node 22.23.3 with an isolated `npm ci`.

| Check | Result |
|---|---|
| Focused GoldTier + CLM + zero-touch + resilience + blocker-policy pytest | 447 passed |
| New/updated case-level Search regressions | 13 passed (10 fail on `d676966` code) |
| Full backend `pytest` | 2,850 passed, 171 skipped, 0 failed (3,021 collected; 24 min 29 s) |
| `ruff check .` / `mypy app` (strict) | pass / no issues (127 files) |
| Frontend `typecheck` / `npm test` / `build` | pass / 58 files, 991 tests passed / pass |
| `check_project_state`, `check_architecture`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness`, `check_secrets` | all PASS |
| CI tooling unittests (dev_context/state/architecture 55; secrets 8; provider readiness 19; policy authority 14; pre-PR 64) | all OK |
| `git diff --check` (staged and unstaged, including the new test file) | clean |
| Full canonical E2E (`run_e2e.py --timeout-seconds 60`, unfiltered, isolated lifecycles) | **112/112 passed** in 26 min; slowest `performance-browser.e2e.ts:98` 55.2 s |

The first E2E attempt stopped at lifecycle 30/112 with `database-classification.e2e.ts:96`
(missing infrastructure). No Mongo server was listening, and the fixture raised
`ServerSelectionTimeoutError`. The rerun reproduced CI's prerequisites:

- a task-owned disposable `mongo:7` container on 127.0.0.1:27392 (tmpfs, auto-remove,
  no mounts) through the harness's `CLM_E2E_SYNTHETIC_MONGO_PORT`;
- Tesseract prefixed on PATH.

Assertions, deadlines and selectors were unchanged. The container was removed after
the run.

Of the backend skips, 165 are gated physical-Mongo tests (no disposable Mongo is
configured) and 6 are local Tesseract OCR tests. This change touches no persistence or
OCR semantics, so neither lane is required by the change-class matrix.

## Limitations and remaining issues

- **Real Sandbox: NOT EXECUTED.** No GoldTier request was made. The process has no
  Sandbox settings, and the only configured source is the primary checkout's
  secret-bearing `.env`, which this task may not open. No repository record authorizes
  new external Sandbox calls. Every result above uses local injected transports, Mock,
  or the offline XPI protocol fixtures. Classification stays `SANDBOX_PARTIAL`.
- The 18–19 October real-Sandbox HTTP 500 remains **unexplained**. No sanitized body
  or diagnostic evidence survives, and its provider-side cause is undetermined. The fix
  improves future diagnosis: the case checkpoint now records the observed status and
  trusted category, and the console records the correlation ID.
- XPI 401/403/404/429 Search semantics are project-defined, not sponsor-confirmed
  (Q-011).
- Ledger, read-back and completed-verification paths still project XPI failures as
  `CONNECTOR_FAILURE`. This was intentionally left unchanged, as a candidate for a
  separate change.
- PR #99 (draft, AI Assistant) touches `caseSections.ts` and shares no path with this
  candidate.

## Change declaration

- API/type: additive console response fields recovered from `d676966`.
- Durable schema: none.
- Connector: Search classification only.
- Configuration: none.
- Business rule, mapping, auth/security: none.
- Architecture: services import one XPI projection helper.
- Provider status: unchanged.
- Runtime: case Search failure code/status and console diagnostics, as above.
