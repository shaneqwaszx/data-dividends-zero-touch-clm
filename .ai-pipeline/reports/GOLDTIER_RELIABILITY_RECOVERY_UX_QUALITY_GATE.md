# GoldTier reliability/recovery UX independent quality gate

Date: 2026-10-07 (Asia/Singapore). Current independent re-gate: **PASS**.

The repaired frozen candidate satisfies the assigned bounded reliability/recovery
criteria. All initial findings were remediated and independently re-probed, with no
remaining required fix. Final affected broad, browser and physical evidence is complete.
The initial FAIL and its exact identity/findings are preserved verbatim below.

## Current reviewed identity

- Worktree: C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm.
- Branch: codex/goldtier-submission-reliability-recovery-ux.
- Base, HEAD, inspected origin/main and merge base:
  5c54c9af896585764d1e4ed809056d1deb576629.
- Reviewed/tested content: that commit plus the uncommitted task delta, 23 paths.
- Exact normalized identity:
  f628a31fbc3cee3ac035ff7b0ddcd0527ec3d10fbe58dfbdafcdd50f8ed22dae.
- Manifest: GOLDTIER_RELIABILITY_RECOVERY_UX_MANIFEST.json, in this reports directory.
  Sorted path + NUL + CRLF-normalized bytes + NUL; cumulative SHA256, with per-path SHA256.
- Identity/per-path hashes matched at re-review entry, before verdict/report writing and
  after the report-only write. Reports/manifest/diagnostic receipts are excluded as
  explicitly listed in the manifest. They cannot change accepted source authority.
- Reviewed path set is the complete 22-path initial list below plus
  apps/backend/tests/test_policy_provider_recovery.py (newly changed in remediation).
  The unchanged filenames in that initial list identify the current 23-path scope;
  current file content/hashes belong only to the new manifest.
- Staged diff empty. Seventeen task-owned tracked paths modified; task-owned new
  source/planner/runbook/report files are untracked. No commit, push, PR, merge or
  next phase occurred. Reviewer changed only this assigned report.
- Classes remain FRONTEND_UI, FRONTEND_STATE_CACHE, BACKEND_DOMAIN, BACKEND_API,
  AUTH_RBAC_SECURITY, PERSISTENCE (existing recovery behavior), CI_TOOLING.
- Evaluation measurement coordination was affirmatively cleared before broad checks.
  Existing evaluation/camunda checkouts, artifacts and resources were preserved.

## Remediation verification and code findings

| Finding | Current disposition and independent evidence |
|---|---|
| QG-01: legacy request bypass | CLOSED. Every accepted request shape now checks retained snapshot currentness and original valid confirmation under the case lock. Wrong supplied UUID still rejects before provider calls. Eight legacy/minimal regressions cover document, ownership, policy and confirmation drift. Original document-drift probe now returns 422 for both requests, leaves uncertainty/automation unchanged and makes no provider call. |
| QG-02: truncated successful JSON | CLOSED. Confirmation-specific loss classifier includes SyntaxError. Native HTTP200 truncated JSON probe now enters observation; component regressions execute one POST and authoritative GET, show success and suppress private decoder text. Actual aborted and truncated-response Playwright cases each pass with one confirmation and unchanged mutation counts. |
| QG-03: unrelated-failure eligibility/UI | CLOSED. Existing zero-touch matching-failure predicate is shared by eligibility and mutation owners. The original unrelated-failure probe now projects no recovery operation and recovery_available=false, rejects POST422 and makes zero extra calls. Component test preserves the unrelated failure explanation. |
| QG-04: static/identity/hygiene | CLOSED. Shell owner explicitly rejects missing canonical name/country before normalize/strip. Focused independent Ruff and diff hygiene pass; coordinator configured mypy passes all 126 source files. Task-owned Markdown and this report have no trailing whitespace. |
| Additional broad existing-customer regression | CLOSED. The initial retained Search-only guard mistakenly equated the original confirmation CLM version with later read-only progress versions. Retained intent now checks current snapshot and original confirmation digest; absent-ledger dispatch retains exact version checking. Independent exact-existing-customer CLM test and final full suite pass, with existing call sequence preserved. No assertion or timeout was weakened. |
| Native Policy selector label | CLOSED. Explicit label/for binding preserves the native select's accessible name. Final component, browser, full frontend, typecheck and build evidence follows this delta. |

No new actionable defect was found in re-review. Existing owners and lock/CAS boundaries
remain authoritative. No ledger reset, second target intent, recovered-write replay,
frontend success authority, role grant, provider transport or mapping change is introduced.

## Current acceptance and twelve falsification attempts

| Criterion | Result / direct evidence |
|---|---|
| Fresh success / false-positive protection | PASS: S3 success and current regression suites; sanitized diagnostic success has FINALIZED ledger, COMPLETED automation, SUBMISSION_CONFIRMED, Shell1/Policy1/Amend0/Readback1. |
| 1. Uncertain Shell replay | PASS: attempted SEARCH/SHELL remains definitive SEARCH through recovery; fresh exact provider validation retains separate Shell proof. Resume retains the same UUID/confirmation with Shell1 and only remaining Policy/readback. New tests, real interrupted-Shell retained/physical regressions, actual Director browser flow. |
| 2. Uncertain Policy replay | PASS: customer Search does not resolve Policy; separate Requested evidence is validated/retained without provider HTTP. Original uncertainty remains distinct from lifecycle resolution. Resume uses same immutable intent/confirmation and Policy count stays1. |
| 3. Duplicate Review & Send | PASS: double activation/lost-response tests and actual browser paths retain one confirmation; recovery/explicit continuation create no second confirmation. |
| 4. Stale recovery | PASS: wrong UUID409 with no provider calls; eight drift/contract tests reject422 and preserve ledger/automation/calls; independent original stale-document probe rejects both contracts. |
| 5. RM / least privilege | PASS: RM permitted status information and direct check; no mutation control. Server403 for unauthorized recovery; existing HR404/case isolation and RBAC tests remain passing. |
| 6. Browser identity overrides backend | PASS: minimal request derives frozen identity; supplied conflicting identity rejects without calls. Legacy requests receive the same currentness/confirmation guard. |
| 7. Ambiguous provider accepted | PASS: fresh ambiguous/no-match/conflicting Shell observations reject recovery, preserve uncertainty and do not dispatch writes. Candidate choice requires current exact observation and checkbox; backend searches freshly again. |
| 8. Client timeout second confirmation | PASS: bounded GET-only observation on timeout, network/gateway and successful JSON decoding loss; one POST asserted in component and actual aborted/truncated browser tests. |
| 9. Historical uncertainty cleared | PASS for compatible retained contract: existing restart/read/no-rewrite and interrupted-Shell evidence preserves uncertainty and prefixes; no reset/migration/replay. Incompatible/missing historical or unsupported Amend evidence remains blocked. No original protected screenshot case was accessed or retrospectively classified. |
| 10. Successful cases degraded | PASS: final full backend/frontend, normal/failure/existing-customer browser paths and existing finalization tests; Search-only version regression repaired without removing freshness checks. |
| 11. Browser resolves without backend proof | PASS: POST recovery then authoritative GET only, supported eligibility, no optimistic finalization, explicit RECOVERY_PENDING continuation, retained original confirmation/UUID. Unrelated failure stays visible and rejects recovery. |
| 12. Offline external calls | PASS: injected synthetic transports, guarded offline browser fixture; every executed browser selection asserts external_calls=0. Reviewer made no provider HTTP request. Mock/Sandbox-partial classifications are unchanged. |
| Pre-dispatch availability guard | PASS: existing forced Search reused; failed preflight retains NOT_SUBMITTED/no confirmation/no intent/no attempted write. Version-bound explicit read-only availability recheck is resumable and creates no uncertainty/write. |
| Cancellation / session / stale publication | PASS: abort/current case-action generation after reads; scoped QueryClient and auth/session clearing; stale case/submission/actor results discarded, StrictMode no automatic duplicate check, no mutation retry or durable browser storage. Focused cancellation/stale tests plus full frontend. |
| Package recovery UX | PASS: direct prominent panel, plain language, affected and completed/resolved prefixes, no RM disabled mutation, exact Shell candidate, Director Requested form, technical details secondary, loading/double activation, keyboard, reload and 320/720/1280 layout exercised. |

## Revision-specific execution evidence

Independent reviewer execution on the final exact 23-path identity:

- Python environment: existing read-only primary interpreter; PYTHONDONTWRITEBYTECODE=1;
  PYTHONPATH points to this worktree's apps/backend and root; pytest cache disabled.
- Command:
  python -m pytest apps/backend/tests/test_target_reliability_recovery_ux.py
  apps/backend/tests/test_s3_submission_status.py
  apps/backend/tests/test_policy_provider_recovery.py::test_policy_recovery_cannot_clear_an_unrelated_technical_failure
  apps/backend/tests/test_clm_orchestration.py::test_exact_match_skips_shell_and_policy_then_amends_existing_party
  -q -p no:cacheprovider:
  **32 passed**, no skips, one inherited StarletteDeprecationWarning.
- From apps/frontend:
  node node_modules/vitest/vitest.mjs run src/pages/S3SubmissionStatus.test.tsx
  src/submissionObservation.test.ts --maxWorkers=1 --no-file-parallelism --no-cache:
  **48 passed**, 2 files (41 + 7), no skips.
- Focused no-cache Ruff across changed backend/app/test/harness paths: **PASS**.
- git diff --check and explicit task-owned Markdown whitespace: **PASS**.
- Three original independent probes rerun: stale minimal/legacy both422 with no state/call
  change; unrelated failure ineligible/POST422/no calls; native decoding-loss classifier
  now true. Process-local synthetic memory only, no reviewed-file edit.
- Final current Git identity, manifest and sanitized diagnostic receipt inspected.

Coordinator-run final broad receipts, supplied for this exact unchanged content:

| Required lane | Actual result |
|---|---|
| Full backend pytest | Exit0; 2,521 passed, 131 skipped, 4 warnings; 832.14 seconds |
| Final full frontend | 557 passed across 47 files |
| Frontend typecheck/build | PASS after final native-label delta; inherited Vite >500kB chunk warning |
| Configured strict backend mypy | PASS; 126 source files |
| Ruff | PASS |
| Contract tests | 44 passed |
| Governance/harness unit tests | 174 passed |
| State/architecture/tooling/policy/provider-readiness validators and secret scans | PASS |
| Affected actual Playwright execution | Eight passed: normal success; existing-customer reuse; definitive Policy failure; read-only uncertain Policy; Director uncertain Shell; Director uncertain Policy; aborted response; truncated successful response |
| Browser inventory | 76 discovered only; no claim that all76 executed |
| Prescribed physical Mongo | scripts/run_physical_mongo_tests.py:19 suites,125 collected/passed,0 failed/errors/skipped |
| Physical safety/cleanup | Newly generated allowlisted disposable DBs removed; exact task-owned container ID/owner label verified before removing only that container. No URI printed/persisted, no protected DB access. |
| Dependency consistency/hygiene | PASS |

The final ordinary backend's **131 skips** are accounted for, not presented as executed:

- **125 physical cases** skipped because the ordinary suite lacks physical configuration;
  all125 were actually executed and passed in the separate prescribed real-driver/server
  run above, with cleanup proof.
- **6 unchanged real local-OCR acceptance cases** (PNG, JPEG, TIFF, SCAN_PDF,
  MIXED_PDF, POOR_PNG) skipped because Tesseract is unavailable on PATH. The exact
  test_s2_local_ocr.py::test_real_local_ocr_acceptance node was separately checked
  with -rs: six skips, exit0. OCR behavior is not changed by this task; no real OCR
  acceptance or unavailable-runtime result is claimed passing.

The four full-backend warnings are one inherited FastAPI/Starlette httpx deprecation
and three Pydantic serialization warnings in preexisting deliberate-malformation
test_phase06_provider_conformance cases EXACT_TRAILING_LF_FULL_FLOW_BYPASS,
MALFORMED_ADDRESS and MALFORMED_TIMESTAMP. They are not new candidate defects.

Initial full-suite failures, browser helper/label failures and the abandoned native
diagnostic crash remain historical unsuccessful evidence. Two introduced existing-customer
failures were fixed. The local HTTP seeder timeout passed isolated baseline/candidate
runs and the final full run (6.32 seconds), without assertion/timeout changes. Only
final unchanged-content successful receipts supply current broad acceptance.

## Diagnostics, contract, architecture and security

GOLDTIER_RELIABILITY_RECOVERY_UX_DIAGNOSTICS.json was inspected. It contains synthetic
case/submission UUIDs, actual attempted/definitive/lifecycle prefixes, ledger/automation/
target states, public TIMEOUT category and call counts. Recovery keeps UUIDs, definitive
facts and one mutation per Shell/Policy while adding only lifecycle resolution; resume
reaches retained verified success. Customer status checks remain read-only and cannot
prove Policy. Response-loss browser receipt retains one confirmation and zero external
calls. The original screenshot's specific cause is correctly UNKNOWN because its
retained case was never inspected.

The current scope uses the existing target ledger, service/repository, authorization,
immutable policy/snapshot and query/session owners. Stable trusted error projections keep
untrusted decoder/provider details out of browser messages; no newly tracked secret/confidential provider
artifact is introduced in the inspected task delta. Settings/fixtures remain offline.
No new schema, migration, repository/CAS strategy, provider adapter, readiness engine,
target mapping or architecture ownership/dependency is created.

Surface declaration: API/types, request currentness/auth safeguards and runtime/browser
recovery behavior changed. Durable schema/repository/CAS, connector transport,
configuration/provider timeout, business-policy vocabulary, target mapping, capability
grants, owner/dependency architecture and provider classification did not change.

Production auth/RBAC, Live ACRA/GoldTier interoperability, general Policy provider APIs,
uncertain Amend recovery, related parties and autonomous/final approval remain outside
the assigned scope. Local/mock/offline tests and partial Sandbox shapes do not establish
Live access or sponsor approval.

## Readiness and next authorized action

**PASS for the exact bounded implementation above; ready for owner review.** No required
implementation fix remains. No next phase is assigned or authorized. Real provider/
Production/Live readiness is not claimed.

This intentionally uncommitted handoff is not PR/publication readiness: pre_pr_check
was appropriately not run. Commit, push, PR, merge and further phase work still require
explicit owner authorization and the applicable integration/publication workflow.
Any later change to reviewed source/instructions requires a fresh independent review.

## Preserved initial gate history

The following initial report is retained verbatim. Its FAIL applies only to the earlier
22-path identity and must not be read as the current repaired-content verdict.


# GoldTier reliability/recovery UX independent quality gate

Date: 2026-10-07 (Asia/Singapore). Result: **FAIL**.

The frozen candidate improves the supported recovery presentation and preserves write
counts in focused offline checks. It cannot be accepted: legacy recovery requests bypass
the new currentness guard, a successful response with invalid/truncated JSON can leave
confirmation enabled without authoritative observation, and eligibility can advertise a
recovery that the backend rejects for an unrelated failure. Ruff, strict mypy and tracked
whitespace also require remediation. Required broad verification is unfinished at this
initial failing gate; no PASS or publication readiness is implied.

## Reviewed identity and boundary

- Worktree: C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm.
- Branch: codex/goldtier-submission-reliability-recovery-ux.
- Base, HEAD and inspected origin/main: 5c54c9af896585764d1e4ed809056d1deb576629.
- Reviewed source: that commit plus the frozen uncommitted candidate below.
- Normalized SHA256 identity: 4b2473c9cb7b4180d2fa2143a383590cd432620e0ca16220bbfeb56ef7c6a70c.
- Manifest: GOLDTIER_RELIABILITY_RECOVERY_UX_MANIFEST.json in this reports directory.
  Algorithm: sorted path, NUL, CRLF-normalized file bytes, NUL; SHA256.
- All 22 per-path hashes and the cumulative identity matched at review entry and before
  report writing and after the report-only write; no reviewed path changed.
- Reviewer wrote only this report. No source/test/doc fix, Git mutation, installation,
  provider call, protected-database access, evaluation-artifact access or process stop.
- Git status: 16 unstaged tracked paths and 7 pre-report untracked paths (including the
  manifest); staged diff empty. Of these, 22 paths are reviewed implementation/instruction
  content. Manifest and this report are excluded from that content identity.
- Classes assessed: FRONTEND_UI, FRONTEND_STATE_CACHE, BACKEND_DOMAIN, BACKEND_API,
  AUTH_RBAC_SECURITY, PERSISTENCE (existing recovery behavior), CI_TOOLING.
- Current-session tools: PowerShell, existing primary-checkout Python interpreter,
  worktree-owned Node dependencies, scoped read-only Git (sandbox escalation required).
  Auth/session/query owners and existing ledger/CAS owners remain controlling.
- Concurrent measurements were initially pending, so only source inspection and
  lightweight checks ran. The coordinator subsequently reported the evaluation chat
  completed and idle at revision 8. Broad checks are owned serially by the coordinator;
  no reviewer heavy suite was started.

Complete reviewed path set:

1. .ai-pipeline/001_planner/GOLDTIER_RELIABILITY_RECOVERY_UX_PLAN.md
2. apps/backend/app/api_models.py
3. apps/backend/app/main.py
4. apps/backend/app/services/clm_orchestration.py
5. apps/backend/app/services/onboarding.py
6. apps/backend/app/services/zero_touch_orchestration.py
7. apps/backend/tests/test_target_reliability_recovery_ux.py
8. apps/frontend/e2e/s3-sandbox-submission.e2e.ts
9. apps/frontend/src/api.ts
10. apps/frontend/src/pages/CaseDetail.tsx
11. apps/frontend/src/pages/S3SubmissionStatus.test.tsx
12. apps/frontend/src/pages/TargetRecoveryPanel.tsx
13. apps/frontend/src/styles.css
14. apps/frontend/src/submissionObservation.test.ts
15. apps/frontend/src/submissionObservation.ts
16. apps/frontend/src/types.ts
17. docs/ARCHITECTURE.md
18. docs/PROJECT_STATE.md
19. docs/integration/GOLDTIER_POLICY_PROVIDER_RECOVERY.md
20. docs/integration/GOLDTIER_RELIABILITY_RECOVERY_UX.md
21. scripts/run_e2e.py
22. scripts/s3_sandbox_fixture.py

## Acceptance and twelve independent falsification attempts

| Requirement / attack | Assessment and evidence on frozen content |
|---|---|
| Fresh success / earlier empty-intent false uncertainty | Focused S3 and new backend tests pass. Search-only retained intent rechecks changed document evidence before first write; no attempted mutation or false uncertainty. Broader regression remains unfinished. |
| Uncertain Shell replay | New offline parameterized test retains one Shell attempt; status checking is GET-only; fresh singleton recovery followed by explicit resume retains the same intent/confirmation and does not repeat Shell. |
| Uncertain Policy replay | New offline test retains one Policy attempt, recovers without HTTP calls, and resumes the same UUID/confirmation with Policy count still one. Search alone leaves uncertainty intact. |
| Duplicate Review & Send | Supported timeout/component double-click path passes; recovery continuation retains original confirmation. The response-decoding gap below permits a second confirmation click after a completed server result. |
| Stale submission recovery | Wrong expected UUID rejects before provider calls. Document drift rejects minimal UUID requests, but complete legacy requests bypass currentness: finding QG-01. |
| RM recovery / HR access | New RM request is 403 with unchanged counts; no RM mutation control is rendered. Existing server capability/case-access owners are unchanged. Full RBAC evidence remains part of broad verification. |
| Browser identity overrides frozen identity | New minimal contract sources retained identity. Supplied conflicting legal name is rejected without calls. Legacy currentness bypass remains a separate defect. |
| Ambiguous fresh provider match accepted | New ambiguous/no-match/conflicting response variants reject Shell recovery and preserve uncertainty. Exact recovery requires fresh singleton/same-ID/name proof and validates supplied identity fields through the existing owner. |
| Client timeout makes second confirmation | Timeout-to-success component test executes one POST and one authoritative GET. Truncated successful JSON does not enter observation: QG-02. |
| Historical uncertainty silently cleared | No ledger reset or schema migration is added. Preserved compatible uncertain ledgers use the panel; missing/unsupported evidence cannot establish success. QG-01 nevertheless clears a stale retained uncertainty via the legacy route. Historical browser and physical restart evidence are unfinished. |
| Normal successful cases degraded | Focused S3 success/failure/finalization tests and observation helper tests pass. Whole-suite/build/browser checks remain required. |
| Browser claims resolution without backend proof | UI does not optimistically finalize: recovery POST then GET publishes backend state, with UUID and case/action generation guards. Policy requires separate Requested attestation. Eligibility incorrectly permits an unrelated technical failure: QG-03. |
| Offline task makes external provider calls | Focused backend transport is injected and asserts the synthetic host and one mutation per operation; fixture Settings disable dotenv. Browser harness extension reuses the offline transport. No real ACRA/GoldTier requests were made by this reviewer. Configured browser execution is still required. |
| Direct panel / accessibility / reload / responsive UX | The package auto-opens on uncertainty; panel has direct status check, live status, enabled/disabled controls, labelled inputs, secondary technical details and backend continuation. Component evidence passes; authored keyboard/reload/responsive Playwright coverage is not execution evidence yet. |
| Backend recovery eligibility reflects actual predicates | UUID/snapshot, confirmation, provider mode, ledger prefix and capability are projected. Automation matching-failure predicate is omitted; the reproduced unrelated failure advertises eligibility but rejects mutation: QG-03. |
| Observation cancellation/session clearing | Focused cancellation/StrictMode/stale-case/submission/session tests pass. Helper checks abort/current action after reads; AuthProvider remounts children by session generation and clears QueryClient. No mutation retry or browser durable storage is introduced. |
| Safe preflight failure and recheck | Forced confirmation Search is reused; failure leaves NOT_SUBMITTED, no confirmation, no submission ID, no write marker or target calls. Version-bound read-only recheck succeeds without dispatch in the new backend test. |

## Findings and required fixes

### QG-01 — P1: legacy recovery request bypasses current evidence and confirmation

Evidence: apps/backend/app/main.py:2553. Both
retained_submission_is_current and has_valid_target_dispatch_confirmation are inside
the optional expected_submission_id branch. The validator intentionally admits a complete
legacy identity attestation without that UUID, so the request reaches the same mutation
owner without either new guard.

Independent in-memory probe on genuine uncertain Policy:

1. Prepare/confirm using the existing offline fixture; retain one Shell and one Policy.
2. Advance the current document updated_at by one second through its memory repository.
3. Director GET reports recovery_available=false.
4. Minimal UUID-bound recovery returns 422 / TARGET_RECOVERY_REJECTED.
5. The otherwise identical request omitting UUID and supplying retained legal name/UEN/
   country returns 200. Automation becomes RECOVERY_PENDING and target projection becomes
   FINALIZATION_PENDING, despite stale submission evidence. No extra provider writes occur.

This is a guard bypass and stale lifecycle-resolution defect, not a target replay.
Apply shared currentness and original-valid-confirmation validation to every accepted
request shape before provider calls or recovery retention. Preserve legacy shape
compatibility if required. Add adverse tests for legacy and minimal requests with changed
document/ownership/classification/confirmation evidence and unchanged ledger/automation.

### QG-02 — P1: successful response decoding loss leaves a second confirmation available

Evidence: apps/frontend/src/api.ts:124; submissionObservation.ts:40;
CaseDetail.tsx:440 and :448. Successful responses call response.json directly.
Invalid/truncated JSON raises SyntaxError. confirmationResponseMayBeLost excludes that
error, and shouldRefreshAfterMutationError excludes it as well.

Independent memory-only Node probe using the frozen helper and installed TypeScript
transpilation: HTTP 200 with an incomplete JSON body raises SyntaxError; the helper returns
false. Static continuation then publishes the exception message, clears busy state and
leaves the prior NOT_SUBMITTED/final-review summary and enabled confirmation control.
A user can send a second confirmation while the first server action has completed.

Treat successful confirmation response decoding loss as an unknown outcome, start bounded
GET-only observation, suppress further confirmation and project a fixed safe message.
Add a regression exercising malformed/truncated successful confirmation JSON with
authoritative confirmed GET, exactly one confirmation and no target replay. Browser
error.message must not become the primary projection of untrusted response text.

### QG-03 — P2: eligibility and presentation omit the unrelated-failure predicate

Evidence: apps/backend/app/main.py:1162;
services/zero_touch_orchestration.py:718 and :751;
frontend/pages/CaseDetail.tsx:1079. The mutators correctly reject a current
TECHNICAL_FAILURE unless it is at MOCK_GOLDTIER with CLM_TARGET_OUTCOME_UNCERTAIN.
The recovery projection does not use that predicate. The frontend hides every current
technical_failure banner when target_submission is uncertain.

Independent probe reuses the existing unrelated-failure fixture: genuine uncertain Policy
plus controlled ZERO_TOUCH_UNEXPECTED_FAILURE. Director GET projects POLICY and
recovery_available=true; UUID recovery returns 422 with zero extra provider calls.
The UI therefore offers an action already known to be unavailable and hides the distinct
failure explanation.

Share the existing matching-failure predicate between mutation eligibility and projection,
and preserve an unrelated technical failure explanation. Add projection/UI coverage and
retain rejection/no-call behavior.

### QG-04 — P2: mandatory static and hygiene checks fail

- Independent focused Ruff reproduces E501, apps/backend/app/main.py:2616,
  102 characters against the configured 100-character limit.
- Coordinator strict mypy evidence (same frozen tree): command python -m mypy app
  from apps/backend, exit 1, 126 source files checked, two new errors at
  services/onboarding.py:3634 and :3637. Optional canonical identity values reach
  normalize/strip without a guard. Source inspection confirms the optional-value issue.
  Guard missing identity safely; do not weaken configured mypy.
- Independent git diff --check reports eight added CRLF lines as trailing whitespace
  in clm_orchestration.py at lines 4, 5, 8, 23, 24, 33, 34 and 58.
  Manifest normalization preserves semantic identity but does not waive Git hygiene.
- Explicit normalized inspection of all task-owned Markdown in the manifest found no
  trailing whitespace. Post-write inspection found no trailing whitespace in the assigned report.

## Executed evidence and unfinished verification

Independent execution on identity 4b2473c9cb7b4180d2fa2143a383590cd432620e0ca16220bbfeb56ef7c6a70c:

- Primary read-only interpreter, PYTHONDONTWRITEBYTECODE=1, PYTHONPATH bound to this
  worktree's apps/backend and root; no pytest cache:
  python -m pytest apps/backend/tests/test_target_reliability_recovery_ux.py
  apps/backend/tests/test_s3_submission_status.py -q -p no:cacheprovider:
  **22 passed**, one inherited StarletteDeprecationWarning, no skip.
- From apps/frontend:
  node node_modules/vitest/vitest.mjs run src/pages/S3SubmissionStatus.test.tsx
  src/submissionObservation.test.ts --maxWorkers=1 --no-file-parallelism --no-cache:
  **46 passed**, 2 files (39 + 7), no skip.
- Focused no-cache Ruff: **FAIL**, one E501.
- Scoped git diff --check: **FAIL**, eight CRLF whitespace diagnostics.
- Entry/pre-report normalized hash check: **MATCH**, 22 paths, no mismatch.
- Three adversarial probes described above: legacy/currentness bypass, response-decoding
  classifier gap, and unrelated-failure eligibility mismatch all reproduced.
  They modified only process-local synthetic memory, never reviewed files.
- Initial focused backend invocation yielded before its terminal summary; it is not
  counted as separate completed evidence. The complete later run supplies the 22-pass result.

Coordinator-reported evidence, not reviewer-executed:

- Strict mypy: FAIL as above.
- Contracts: 44 passed.
- Project-state, architecture, development-tooling, policy governance,
  provider-readiness and secret checks: reported PASS on the frozen identity.
- Previously reported frontend app no-emit tsc: passed.
- Full backend suite is still running at report creation; failures have been observed,
  but final count and causal details are not yet available. Do not classify or waive them
  from this partial progress.
- Broad frontend/build, configured Playwright normal/recovery/lost-response paths,
  applicable POC/lifecycle, and guarded physical-Mongo recovery/restart evidence remain
  unfinished/unexecuted in this gate. No skipped physical check is treated as passing.
  The measurement coordination gate is now cleared; these are unfinished required lanes,
  not an ongoing measurement prohibition or invented missing-tool claim.
- No pre_pr_check was run: this is an intentionally uncommitted implementation handoff,
  not publication readiness.

Changed backend recovery coordination can affect persisted case/ledger/automation
checkpoints despite no schema change. The applicable guarded physical-Mongo lane and
cleanup proof remain necessary after remediation. Use only the existing newly generated
allowlisted disposable database harness; never inspect a protected database.

## Contract, architecture and security assessment

The delta extends existing CLM/onboarding/zero-touch owners and extracts a focused view.
It does not add a persistence owner, readiness engine, provider adapter, direct
route-to-Mongo access, classification mapping, role grant or target-ledger bypass.
Search remains read-only; Policy Requested attestation remains operator evidence, not
completed KYC/approval. Shell recovery preserves original uncertainty and separate fresh
provider proof. No sponsor/Live claim is supported or added.

API/types change additively; runtime/UI behavior and request currentness/security checks
change. Durable schema, connector transport, configuration/timeouts, business-rule
vocabulary, target mappings, architecture ownership/dependencies and provider status do
not change. The optional identity guard and unsafe successful-response exception
projection require repair. The explicit offline fixtures and safe error text otherwise
introduce no secret/raw-provider payload in the inspected delta.

Existing production/sponsor dependencies remain separate: Live interoperability,
production auth/RBAC, general Policy evidence APIs, uncertain Amend recovery, related
parties and final approval are outside this task. They do not excuse current defects.

## Readiness and next authorized action

**Not implementation-complete, not accepted, not PR/publication-ready.** No next phase or
real ACRA/GoldTier readiness is claimed.

Return to the coordinator for one bounded remediation run covering QG-01 through QG-04,
then finish all affected required verification and obtain a fresh independent re-gate
on a new exact manifest. This report remains the initial FAIL for its frozen identity;
later repaired content cannot inherit this verdict or its evidence. No commit, push,
PR, merge or other phase is authorized.
