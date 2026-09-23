# PR #52 E2E Remediation — Fresh Independent Quality Gate

Date: 2026-09-23

## Executive Result

**FAIL**

The accumulated PR #52 E2E remediation is not publication-ready. The code, test,
lifecycle, diagnostic, security, and coverage-preservation review found no source-level
critical or high-severity defect in the changed implementation. The final
Cases/Representative Routes workload isolation is coherent: the representative-routes
selector uses one completed case, the review-specific assertions retain an independent
owner, and a focused real two-case selector preserves the retained-case-to-new-case
route identity invariant without retry, reload, skip, timeout increase, or assertion
weakening.

However, the fresh independent configured E2E run failed selector 2/14 on the exact
frozen candidate. The unchanged Singapore clean-fixture selector timed out waiting for
the browser to receive the expected
`GET /api/clm/zero-touch/case-portfolio` response after `page.reload()`. One
subsequent isolated diagnostic execution of that exact selector passed, so the current
evidence establishes an intermittent unresolved full-suite acceptance failure rather
than a deterministic product defect or missing infrastructure. Under the repository
quality-gate rule, a failed required browser lane cannot be converted into a pass by
implementer evidence or one passing focused rerun.

This verdict applies only to the frozen reviewed content below. It states governance
and publication readiness only; it grants no phase, provider, merge, or product
authority.

## Frozen Reviewed-Content Identity

| Identity | Reviewed value |
|---|---|
| Branch | `integration/acra-teammate-reconciliation` |
| Committed HEAD / published parent | `5ad738af2a07c6fc28ed379104079abeb2fa91a3` |
| Current local `origin/main` | `ef338c9b7926a298e8987acb975fd93c96ed2bfb` |
| Merge base | `ef338c9b7926a298e8987acb975fd93c96ed2bfb` |
| Ahead / behind | 4 ahead / 0 behind |
| Frozen tracked candidate state | exactly 12 unstaged modified paths; no staged paths; no untracked path was reported |
| Binary diff SHA-256, all 12 candidate paths | `57edf559705d0b5f39a624891c3578f2b639b3a7bc3243d3e44cbaaba2437d88` |
| Binary diff SHA-256, 11 non-report paths | `3a8898f4d5b6eb199e22d8df74717d1c77f466a645a96120e0d935b1c093c6ad` |
| Remediation report SHA-256 | `b06ee37c367955a03e3713ed3555b050fa286a24af07f315bbdd44b256764da4` |

Frozen candidate paths:

1. `.ai-pipeline/reports/PR52_E2E_PORT_RELEASE_REMEDIATION.md`
2. `apps/backend/app/main.py`
3. `apps/backend/tests/test_document_api.py`
4. `apps/frontend/e2e/authenticated-zero-touch.e2e.ts`
5. `apps/frontend/e2e/responsive-layout.e2e.ts`
6. `apps/frontend/src/Phase15CNavigation.test.tsx`
7. `apps/frontend/src/api.ts`
8. `apps/frontend/src/pages/CaseDetail.tsx`
9. `apps/frontend/vite.config.ts`
10. `scripts/e2e_backend_server.py`
11. `scripts/run_e2e.py`
12. `tests/test_run_e2e.py`

The hashes were reproduced before execution and again after the fresh runtime checks.
The only additional tracked modification made by this reviewer is this assigned gate
report. Git emitted access-denied warnings for pre-existing pytest-cache directories
while attempting exhaustive untracked traversal; it reported no untracked path, and the
tracked candidate identity remained exact.

## Capability and Resource Preflight

| Resource | Fresh observation | Gate consequence |
|---|---|---|
| Python | 3.12.10 | Runner, backend, Ruff, and governance checks available |
| Node / npm | Node 22.23.2; npm 10.9.8 | Frontend checks available |
| Browser toolchain | repository-pinned Playwright 1.56.1, Vite 7.1.11, TypeScript 5.9.3 | Configured browser execution available |
| Frontend cache owner | TanStack Query 5.102.8 | Installed version matched inspected source/tests |
| Restricted process sandbox | blocked the first Vitest attempt with `esbuild spawn EPERM` | Classified as missing infrastructure for that attempt; the identical permitted rerun passed |
| Permitted local process execution | Vite, Chromium, backend, and task-owned cleanup ran | Required real browser/process evidence available |
| Browser ports | configured suite used deterministic pairs from 8765/4173; focused diagnostic used 9401/4801 | No shared pair reuse or cleanup failure was reported |
| Mongo / external providers | not required by this bounded change | No persistence or provider claim depends on unavailable infrastructure |

No external connector, plugin, remote service, database, credential, or protected
artefact was used.

## Acceptance Checklist

| Assigned criterion | Result | Independent evidence |
|---|---|---|
| Review the entire accumulated 12-path candidate | **PASS** | Full diffs, current owning source/tests, architecture, contracts, decision/open-question context, remediation chronology, and the prior stale gate were inspected. |
| Representative-routes selector uses one completed case | **PASS** | `responsive cases and representative routes preserve tables, priorities, and policy visibility` creates one clean case, waits for `COMPLETED`, and uses that ID for `/cases/{id}` and `/onboarded/{id}`. |
| Removed second case does not remove review coverage | **PASS** | `responsive review case exposes only supported authoritative review controls` independently creates a low-confidence case, waits for `WAITING_FOR_REVIEW`, validates the authoritative current document, and retains Accept/unsupported-control/containment assertions. |
| Real two-case route-transition invariant retained | **PASS** | `starting a fresh onboarding after a retained case binds the new case route` creates case A through the real UI, explicitly enters the fresh route, creates case B through the real UI, proves the new retained route, and proves distinct IDs. |
| No masking | **PASS** | Diff inspection found no added Playwright retry, reload recovery, arbitrary browser sleep, skip, catch-and-continue, assertion removal, or raised timeout. The existing 240-second test timeout value and runner 240-second suite limit were not increased. POSIX sleep is bounded condition polling for owned-group absence. |
| Lifecycle/process ownership remains fail-closed | **PASS** | Deterministic unique port allocation, strict pre-start bind checks, reverse cleanup, exact POSIX group signaling/proof, exact Windows PID-tree command, and cleanup-failure override were inspected; fresh runner tests passed 32/32. No broad process enumeration or port-owner kill was added. |
| Diagnostic boundary remains explicit and payload-minimal | **PASS** | Diagnostic environment is opt-in; request IDs are UUID-v4-shaped; emitted fields are fixed route family, opaque case/request IDs, status/count/timing/PID/port metadata. No document values, filenames, bytes, credentials, cookies, CSRF values, provider payloads, or response bodies are emitted. Focused backend and runner tests passed. |
| React Query authoritative refresh correction is covered | **PASS** | Exact actor/case queries are cancelled before direct authoritative refresh; results publish independently under the existing case/action generation guard. Fresh focused frontend tests passed 51/51, including stale-query overwrite and unrelated-ownership head-of-line cases. |
| Product freeze and authority boundaries | **PASS** | No schema, persistence owner, provider/connector mode, mapping, business rule, RBAC authority, target-ledger rule, sponsor policy, or Phase 22 behavior was added. Diagnostic hooks are development-only and default-off. |
| Causal claims remain bounded | **PASS** | The report classifies `MULTI_CASE_RESPONSIVE_TEST_COUPLING` only at test workload/ownership level and explicitly leaves historical lower browser/runtime mechanisms unknown. The fresh failure does not falsify that narrow claim, but it invalidates publication readiness. |
| Required full configured E2E evidence on the reviewed candidate | **FAIL** | Fresh `python scripts/run_e2e.py` passed selector 1/14, then selector 2/14 timed out after 120 seconds at `authenticated-zero-touch.e2e.ts:231` waiting for the portfolio response after reload. One isolated reproduction passed; the intermittent full-suite failure remains unresolved. |

## Contract and Integration Findings

No contract, mapping, provider, sponsor-authority, persistence, or architecture blocker
was found in the changed implementation. The candidate preserves the existing
Mock/Local/Partial/Dormant classifications and does not claim Live ACRA, GoldTier,
PingFed, production OCR, production SSO, or Ready-for-Approval.

The browser diagnostic header and milestone chain are active only when the task-owned
launcher enables diagnostics. Normal product requests do not emit the milestones. The
document upload remains a bounded raw-body request through the existing backend route
and document service; the diagnostic seam does not authorize a new API contract.

Current sponsor questions Q-001 through Q-018 remain later dependencies and do not
explain or waive the present E2E blocker.

## Tester and Adversarial Findings

### High-severity current blocker

**PR52-QG-001 — the exact candidate failed the fresh required configured browser suite.**

- Command: `python scripts/run_e2e.py`
- Result: exit 1; selector 1/14 passed; selector 2/14 failed.
- Failing selector: `Singapore clean fixture completes the truthful Mock target path`.
- Exact boundary: `page.waitForResponse` at
  `apps/frontend/e2e/authenticated-zero-touch.e2e.ts:231` timed out after
  `page.reload()` while awaiting
  `GET /api/clm/zero-touch/case-portfolio`.
- Lifecycle evidence: no allocation, bind, process-cleanup, or old-port-reuse failure
  was emitted.
- Bounded classification run:
  `python scripts/run_e2e.py --backend-port 9401 --frontend-port 4801 --grep
  "Singapore clean fixture completes the truthful Mock target path"` passed 1/1 in
  12.4 seconds.
- Classification: unresolved intermittent browser/query/test synchronization failure,
  not a deterministic defect yet and not missing infrastructure.
- Consequence: the required full-browser lane is not independently green; earlier
  implementer 14/14 passes cannot supply this reviewer's required fresh acceptance.

### Fresh independent checks

| Command | Result |
|---|---|
| `python scripts/dev_context.py` | PASS; branch, HEAD, base, provider truth, and 12-path candidate matched |
| `python -m unittest tests.test_run_e2e -v` | PASS — 32/32 |
| `python -m pytest tests/test_document_api.py -q` from `apps/backend` | PASS — 22/22 |
| Restricted focused Vitest attempt | unavailable — `esbuild spawn EPERM` before test startup |
| Permitted `npm.cmd test -- --run src/pages/DocumentEvidencePanel.test.tsx src/Phase15CNavigation.test.tsx` | PASS — 2 files, 51/51 |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd run build` | PASS — 112 modules transformed |
| `python -m ruff check apps/backend scripts tests` | PASS; filesystem access warnings were emitted for pre-existing inaccessible pytest-cache directories |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/check_tooling_config.py` | PASS |
| `python scripts/check_secrets.py` | PASS |
| `npm.cmd ls --all` | PASS; only expected optional cross-platform packages were unmet |
| Candidate-scoped `git diff --check` | PASS; only informational LF-to-CRLF notices |
| Full `python scripts/run_e2e.py` | **FAIL** — 1/14 passed, selector 2/14 timed out |
| One isolated exact-selector diagnostic execution | PASS — 1/1 |

The implementer-reported 5-consecutive one-case selector passes, focused two-case 5/5,
responsive 21/21 plus two 7/7 sequences, document-review 3/3, two complete 14/14
suites, Windows lifecycle 23/23, full frontend 274, and full backend 1129 passed / 28
skipped were inspected as implementer evidence. They were not relabelled as fresh
independent evidence. Full backend/frontend and Windows lifecycle were not repeated
after the decisive fresh browser failure because passing them could not close
PR52-QG-001.

## Code and Architecture Review

No critical, high, medium, or low source-code finding was identified beyond the
runtime acceptance blocker.

- `scripts/run_e2e.py` keeps one lifecycle owner, derives non-overlapping deterministic
  pairs, validates bounds/collisions, runs the strict bind proof before each lifecycle,
  and fails closed on cleanup errors.
- POSIX cleanup acts on the task-created group ID and proves absence before returning;
  Windows retains exact owned-PID tree termination. No broad host-process discovery was
  added.
- Diagnostic hooks are bounded to the existing upload path and do not move document or
  workflow ownership into the runner, proxy, browser, or route.
- `CaseDetail` remains the existing mutation/query-cache owner. The change does not
  introduce a second QueryClient, query key, authorization owner, or persistence
  surface.
- Responsive decomposition creates independent selector state and keeps mutable case
  IDs selector-local. Coverage formerly coupled in one monolithic lifecycle remains
  represented by the seven selectors.
- The final one-case workload isolation removes redundant setup rather than a product
  assertion; review behavior and two-case route identity each retain a narrower owner.

The accumulated delta is large because it preserves a chronological diagnostic report
and explicit safe instrumentation, but it does not create a new product architecture
owner or require an ADR.

## Security Review

No security defect was identified.

- Environment propagation remains allowlisted and generated E2E credentials remain
  ephemeral.
- Browser network policy remains loopback-only; diagnostics add no external endpoint.
- Diagnostic output is opt-in and excludes raw document content, filenames, field
  values, response bodies, credentials, session/cookie/CSRF values, provider payloads,
  and private exceptions.
- Backend diagnostic logging requires both the E2E mode and a UUID-v4-shaped request
  identifier; normal execution is silent.
- Upload bytes remain transient, bounded, and owned by the existing document-processing
  path.
- The runner retains bounded capture and sanitization. No secret-bearing artifact,
  recording, trace, screenshot, broad process scan, or unrelated kill path was added.
- Fresh secret scanning passed.

## Required Fixes

1. Diagnose PR52-QG-001 at the browser reload / auth restore / Cases query boundary
   without adding a retry, reload recovery, sleep, timeout increase, skip, or weaker
   assertion. Establish whether the failed reload did not dispatch the portfolio
   request, dispatched it without completion, lost the response listener, or failed to
   commit the authenticated Cases view.
2. Add only the smallest regression evidence supported by that diagnosis, if a code or
   test defect is proved. Do not make a product change when the evidence identifies
   only harness or infrastructure ownership.
3. Rerun the affected focused selector and the unchanged complete configured E2E suite
   on the remediated frozen candidate. The complete suite must be green without
   retries/masking, followed by a fresh independent re-quality gate.

No other implementation, contract, security, architecture, provider, persistence, or
product-policy fix is required by this review.

## Readiness

Governance/publication readiness: **NOT READY**.

The frozen candidate must not be committed/pushed as an accepted remediation on the
basis of this gate. A fresh independent re-QG is required after PR52-QG-001 is
resolved or conclusively classified with evidence that restores the required full
configured browser acceptance.

This result does not authorize Phase 22, a provider activation, a PR mutation, push,
merge, or any product-phase claim.

## Git Status and Reviewer Boundary

At final report write:

- branch remained `integration/acra-teammate-reconciliation`;
- HEAD remained `5ad738af2a07c6fc28ed379104079abeb2fa91a3`;
- local `origin/main` and merge base remained
  `ef338c9b7926a298e8987acb975fd93c96ed2bfb`;
- the frozen 12 candidate paths remained byte/diff-identical to the reviewed hashes;
- no staged path was introduced;
- the only tracked path changed beyond the frozen 12 is this assigned quality-gate
  report;
- no implementation, test, configuration, remediation report, ordinary documentation,
  Git index, commit, branch, remote, PR, CI, merge, or Phase 22 state was modified by
  this reviewer.

## Final Verdict

FAIL
